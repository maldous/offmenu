import json
from pathlib import Path
import sqlite3
import sys
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'tools/delivery'))
from stokowski_cloudflare_budget import BudgetRefused, ProjectAccountRouter
from stokowski_cloudflare_client import MODEL, REQUEST_MAXIMUM, WorkersAIClient, WorkersAIRequestError
from stokowski_cloudflare_turn import Attempt, run_turn


class WorkersAIClientTests(unittest.TestCase):
    def setUp(self):
        directory = TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.database = Path(directory.name) / 'budget.sqlite'
        self.accounts = dict(zip(('UIF', 'OffMenu', 'ANQR', 'CIX', 'CQ'),
                                 (digit * 32 for digit in 'abcde')))
        self.router = ProjectAccountRouter(self.database, self.accounts)
        self.client = WorkersAIClient(self.router, lambda account: 'test-' + account)
        self.request = dict(project='OffMenu', attempt_id='candidate', request_id='candidate/one',
                            active_projects={'OffMenu'}, messages=[{'role': 'user', 'content': 'test'}],
                            tools=[], timeout=1)

    def usage_record(self):
        with sqlite3.connect(self.database) as db:
            return db.execute('SELECT amount, settled FROM requests').fetchone()

    @patch('stokowski_cloudflare_client.HTTPSConnection')
    def test_selected_account_is_used_and_reported_usage_is_rounded_up(self, connection):
        conn = connection.return_value
        response = conn.getresponse.return_value
        response.status = 200
        response.read.return_value = b'{"success":true,"result":{"usage":{"neurons":1.0001}}}'
        conn.request.side_effect = lambda *args, **kwargs: self.assertEqual(
            self.usage_record(), (REQUEST_MAXIMUM, 0))
        self.client.complete(**self.request)
        self.assertEqual(self.usage_record(), (1001, 1))
        connection.assert_called_once_with('api.cloudflare.com', timeout=1)
        (method, path), kwargs = conn.request.call_args
        account = self.accounts['OffMenu']
        self.assertEqual((method, path), ('POST', f'/client/v4/accounts/{account}/ai/run/{MODEL}'))
        self.assertEqual(kwargs['headers']['Authorization'], f'Bearer test-{account}')
        self.assertEqual(json.loads(kwargs['body'])['max_tokens'], 2048)

    @patch('stokowski_cloudflare_client.HTTPSConnection')
    def test_timeout_retains_reservation_and_blocks_redispatch(self, connection):
        connection.return_value.getresponse.side_effect = TimeoutError
        with self.assertRaises(WorkersAIRequestError):
            self.client.complete(**self.request)
        self.assertEqual(self.usage_record(), (REQUEST_MAXIMUM, 0))
        with self.assertRaises(BudgetRefused):
            self.client.complete(**self.request)
        connection.assert_called_once()

    @patch('stokowski_cloudflare_client.HTTPSConnection')
    def test_no_credential_means_no_request(self, connection):
        client = WorkersAIClient(self.router, lambda account: None)
        with self.assertRaises(WorkersAIRequestError):
            client.complete(**self.request)
        connection.assert_not_called()
        self.assertEqual(self.usage_record(), (0, 1))

    @patch('stokowski_cloudflare_client.HTTPSConnection')
    def test_provider_refusal_hides_response_body_and_retains_reservation(self, connection):
        credential = 'test-private-token'
        client = WorkersAIClient(self.router, lambda account: credential)
        response = connection.return_value.getresponse.return_value
        response.status = 429
        response.read.return_value = credential.encode()
        with self.assertRaisesRegex(WorkersAIRequestError, r'^Workers AI refused request \(HTTP 429\)$'):
            client.complete(**self.request)
        response.read.assert_not_called()
        self.assertEqual(self.usage_record(), (REQUEST_MAXIMUM, 0))

    @patch('stokowski_cloudflare_client.HTTPSConnection')
    @patch('subprocess.Popen', side_effect=FileNotFoundError('No process launcher available'))
    def test_turn_works_without_codex_and_stays_on_one_account(self, popen, connection):
        conn = connection.return_value
        response = conn.getresponse.return_value
        response.status = 200
        response.read.side_effect = [
            b'{"success":true,"result":{"tool_calls":[{"id":"edit","type":"function",'
            b'"function":{"name":"replace_line","arguments":{"line":"new"}}}],'
            b'"usage":{"neurons":1}}}',
            b'{"success":true,"result":{"response":"Patch prepared","usage":{"neurons":2}}}',
        ]
        target = self.database.parent / 'fixture.txt'
        target.write_text('old')

        def edit(name, arguments, remaining):
            self.assertEqual(name, 'replace_line')
            self.assertGreater(remaining, 0)
            target.write_text(arguments['line'])
            return 'Edited fixture'

        result = run_turn(self.client, Attempt('OffMenu', 'author'), 'Fix fixture',
                          tools=[{'type': 'function', 'function': {'name': 'replace_line'}}],
                          execute_tool=edit, active_projects=lambda: {'OffMenu'},
                          cancelled=lambda: False, timeout=5)
        self.assertEqual((result, target.read_text()), ('Patch prepared', 'new'))
        popen.assert_not_called()
        requests = conn.request.call_args_list
        self.assertEqual(len(requests), 2)
        self.assertEqual(requests[0].args[1], requests[1].args[1])
        self.assertEqual(json.loads(requests[1].kwargs['body'])['messages'][-1],
                         {'role': 'tool', 'tool_call_id': 'edit', 'content': 'Edited fixture'})
