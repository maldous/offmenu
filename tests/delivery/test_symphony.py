"""Focused checks for native OffMenu admission; no credentials or model calls."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from dev.delivery import symphony_launch as launch
from dev.delivery import symphony_workspace as workspace


class NativeAdmission(unittest.TestCase):
    def payload(self):
        return {'data': {'issue': {'id': launch.ISSUE_ID, 'identifier': 'UIF-90', 'project': {'id': launch.PROJECT_ID, 'slugId': launch.NATIVE_SLUG_ID}, 'team': {'id': '53f584e7-70a1-4b1e-b982-b815210e47d4'}, 'state': {'name': 'In Progress'}, 'labels': {'nodes': [{'name': launch.LABEL}]}}, 'issues': {'nodes': [{'id': launch.ISSUE_ID}]}}}

    def check_payload(self, payload):
        import io
        with patch('urllib.request.urlopen') as request:
            request.return_value.__enter__.return_value = io.BytesIO(json.dumps(payload).encode())
            return launch.tracker_preflight({'OFFMENU_LINEAR_API_KEY': 'test-not-a-real-key'})

    def test_exact_issue_scope(self):
        self.assertEqual(self.check_payload(self.payload())['candidate_count'], 1)

    def test_wrong_project_fails(self):
        payload = self.payload()
        payload['data']['issue']['project']['id'] = 'another-project'
        with self.assertRaises(RuntimeError):
            self.check_payload(payload)

    def test_second_issue_fails(self):
        payload = self.payload()
        payload['data']['issues']['nodes'].append({'id': 'other'})
        with self.assertRaises(RuntimeError):
            self.check_payload(payload)

    def test_missing_credential_route_fails(self):
        with self.assertRaises(RuntimeError):
            launch.credential({})

    def test_dirty_source_prevents_prepare(self):
        with tempfile.TemporaryDirectory() as directory:
            with patch.object(launch, 'prerequisite', return_value={'source_branch': launch.BRANCH, 'tracked_source_clean': False}):
                with self.assertRaises(RuntimeError):
                    launch.prepare(Path(directory), 'gpt-6.1-sol')
            self.assertFalse((Path(directory)/'WORKFLOW.md').exists())

    def test_wrong_workspace_is_never_admitted(self):
        with patch('sys.argv', ['hook', 'admit', '--source', '/tmp/source', '--head', 'a'*40]), patch.object(Path, 'cwd', return_value=Path('/tmp/UIF-89')):
            with self.assertRaises(SystemExit):
                workspace.main()


if __name__ == '__main__':
    unittest.main()
