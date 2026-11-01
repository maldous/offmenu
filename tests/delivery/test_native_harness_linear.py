"""Actual pinned LinearClient/HTTP transport, durable CurrentWork.save, no network."""
import asyncio
from dataclasses import dataclass, replace
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import httpx
from stokowski.linear import LinearClient
from stokowski_adapter import CurrentWork
from native_harness_contract import fingerprint
from native_harness_linear import LinearEffectHold, NativeLinearAdapter, STORE, milestone_body
from linear_delivery import plan_delivery
import test_linear_delivery as planner_fixtures

ISSUE, PROJECT, SECOND = planner_fixtures.ISSUE, planner_fixtures.PROJECT, planner_fixtures.SECOND


@dataclass(frozen=True)
class Binding:
    issue_id: str
    project_id: str
    owner: str
    packet_sha256: str
    operation_id: str
    phase: str
    unit_sha256: str


class CurrentFixture:
    """Use the ORIGINAL CurrentWork.save and its atomic/fsynced file custody."""
    save = CurrentWork.save

    def __init__(self, path):
        self.state_path = path
        self.state = json.loads(path.read_text()) if path.exists() else {'owner': 'root-owner'}
        self.read_only = False
        self.stopping = False
        self.config = {'owner': 'root-owner'}
        self.route = {'project_id': PROJECT}
        self.entries = {'UIF-123': {'issue_id': ISSUE}}
        self.guard_failure = False

    def guard(self):
        if self.guard_failure:
            raise LinearEffectHold('fixture_owner_drift')


class NativeLinearTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / 'current-owner.json'
        self.current = CurrentFixture(self.path)
        fixture = planner_fixtures.LinearDeliveryTests()
        fixture.setUp()
        self.fixture = fixture
        self.actions = plan_delivery(fixture.request, fixture.policy)['actions']
        self.link = next(a for a in self.actions if a['kind'] == 'linear-link-pr')
        self.milestone = next(a for a in self.actions if a['kind'] == 'linear-record-source-milestone')
        self.nodes = []
        self.calls = []
        self.writes = []
        self.mode = 'normal'
        self.identity = {'id': ISSUE, 'project': {'id': PROJECT}}
        self.page_count = 0
        self.client = LinearClient(endpoint='https://linear.invalid/graphql', api_key='synthetic-test-only')
        await self.client._client.aclose()
        self.client._client = httpx.AsyncClient(transport=httpx.MockTransport(self.transport))
        self.addAsyncCleanup(self.client.close)
        self.adapter = NativeLinearAdapter(self.client)

    def binding(self, action=None):
        action = action or self.link
        return Binding(ISSUE, PROJECT, 'root-owner', 'a' * 64,
                       action['action_id'], 'linear', 'b' * 64)

    def transport(self, request):
        content = json.loads(request.content)
        self.calls.append(content)
        query, variables = content['query'], content['variables']
        if query.startswith('mutation'):
            # Assert intent reached durable ORIGINAL owner custody before request.
            disk = json.loads(self.path.read_text())
            operation = self.binding(self.active_action).operation_id
            assert disk[STORE][operation]['status'] == 'pending'
            self.writes.append(content)
            payload = variables['input']
            if 'attachmentCreate' in query:
                assert payload == {'issueId': ISSUE, 'url': self.link['url'], 'title': 'OffMenu source PR'}
                self.nodes.append({'id': 'attachment-id', 'url': payload['url']})
                key = 'attachmentCreate'
            elif 'issueRelationCreate' in query:
                assert payload == {'issueId': SECOND, 'relatedIssueId': ISSUE, 'type': 'blocks'}
                self.nodes.append({'id': 'relation-id', 'type': 'blocks',
                                   'issue': {'id': SECOND, 'state': {'type': 'started'}},
                                   'relatedIssue': {'id': ISSUE}})
                key = 'issueRelationCreate'
            else:
                assert 'commentCreate' in query and payload['issueId'] == ISSUE
                assert 'issueUpdate' not in query and 'stateId' not in payload
                self.nodes.append({'id': 'comment-id', 'body': payload['body']})
                key = 'commentCreate'
            if self.mode == 'cancel-after-effect':
                raise asyncio.CancelledError()
            if self.mode == 'lost-reply':
                raise httpx.ReadTimeout('synthetic lost response', request=request)
            if self.mode in ('unknown-no-effect', 'denied'):
                self.nodes.clear()
                if self.mode == 'denied':
                    return httpx.Response(403, json={'errors': [{'message': 'not allowed'}]})
                raise httpx.ReadTimeout('synthetic uncertain transport', request=request)
            if self.mode == 'false-success':
                self.nodes.clear()
                return httpx.Response(200, json={'data': {key: {'success': False}}})
            return httpx.Response(200, json={'data': {key: {'success': True}}})
        field = ('attachments' if 'attachments(' in query else
                 'inverseRelations' if 'inverseRelations(' in query else 'comments')
        if self.mode == 'stop-after-read':
            self.current.stopping = True
        if self.mode == 'read-error':
            return httpx.Response(200, json={'errors': [{'message': 'synthetic read failure'}]})
        if self.mode == 'paged':
            self.page_count += 1
            after = variables['after']
            nodes = [] if after is None else self.nodes
            info = {'hasNextPage': after is None, 'endCursor': 'cursor-1'}
        elif self.mode == 'cursor-loop':
            nodes, info = [], {'hasNextPage': True, 'endCursor': 'same-cursor'}
        else:
            nodes, info = self.nodes, {'hasNextPage': False, 'endCursor': None}
        connection = {'nodes': nodes, 'pageInfo': info}
        if self.mode == 'missing-pagination':
            del connection['pageInfo']
        return httpx.Response(200, json={'data': {'issue': {**self.identity, field: connection}}})

    async def step(self, action=None, binding=None):
        self.active_action = action or self.link
        return await self.adapter.step(self.current, binding or self.binding(self.active_action), self.active_action)

    def reopen(self):
        self.current = CurrentFixture(self.path)
        self.adapter = NativeLinearAdapter(self.client)

    async def test_attachment_one_write_with_intent_and_fresh_readback_reopen(self):
        result = await self.step()
        self.assertEqual(result, {'operation_id': self.link['action_id'], 'status': 'verified', 'child_tree_gone': True})
        self.reopen()
        self.assertEqual((await self.step())['status'], 'verified')
        self.assertEqual(len(self.writes), 1)
        self.assertEqual(self.current.state[STORE][self.link['action_id']]['evidence']['native_ids'], ['attachment-id'])

    async def test_read_only_observe_ready_then_native_noop_requires_no_write(self):
        binding = self.binding()
        self.assertEqual((await self.adapter.observe(self.current, binding, self.link))['status'], 'ready')
        self.assertFalse(self.path.exists())
        self.nodes = [{'id': 'existing', 'url': self.link['url']}]
        self.assertEqual((await self.step())['status'], 'verified')
        self.assertEqual(self.writes, [])

    async def test_lost_mutation_reply_reconciles_native_effect_without_retry(self):
        self.mode = 'lost-reply'
        self.assertEqual((await self.step())['status'], 'verified')
        self.reopen()
        self.assertEqual((await self.step())['status'], 'verified')
        self.assertEqual(len(self.writes), 1)

    async def test_unknown_absence_never_retries_after_persisted_reentry(self):
        self.mode = 'unknown-no-effect'
        self.assertEqual((await self.step())['status'], 'unknown')
        self.reopen()
        self.mode = 'normal'
        self.assertEqual((await self.step())['status'], 'unknown')
        self.assertEqual(len(self.writes), 1)
        self.nodes = [{'id': 'late-effect', 'url': self.link['url']}]
        self.assertEqual((await self.step())['status'], 'verified')
        self.assertEqual(len(self.writes), 1)

    async def test_cancellation_after_effect_retains_pending_intent(self):
        self.mode = 'cancel-after-effect'
        with self.assertRaises(asyncio.CancelledError):
            await self.step()
        self.assertEqual(json.loads(self.path.read_text())[STORE][self.link['action_id']]['status'], 'pending')
        self.reopen()
        self.assertEqual((await self.step())['status'], 'verified')
        self.assertEqual(len(self.writes), 1)

    async def test_save_failure_prevents_every_external_mutation(self):
        with patch.object(self.current, 'save', side_effect=OSError('synthetic fsync failure')):
            with self.assertRaises(OSError):
                await self.step()
        self.assertEqual(self.writes, [])

    async def test_read_failure_and_incomplete_pagination_never_authorize_write(self):
        for mode in ('read-error', 'missing-pagination', 'cursor-loop'):
            self.mode = mode
            self.assertEqual((await self.step())['status'], 'unknown')
        self.assertEqual(self.writes, [])
        self.assertFalse(self.path.exists())

    async def test_readback_scans_next_page_before_noop(self):
        self.mode = 'paged'
        self.nodes = [{'id': 'existing-page-two', 'url': self.link['url']}]
        self.assertEqual((await self.step())['status'], 'verified')
        self.assertEqual(self.page_count, 2)
        self.assertEqual(self.writes, [])

    async def test_scope_and_action_fingerprint_drift_fail_before_transport(self):
        for bound in (replace(self.binding(), owner='other'),
                      replace(self.binding(), project_id=SECOND),
                      replace(self.binding(), issue_id=SECOND),
                      replace(self.binding(), operation_id='f' * 64)):
            with self.assertRaises(LinearEffectHold):
                await self.step(binding=bound)
        self.assertEqual(self.calls, [])
        broken = {**self.link, 'url': self.link['url'] + '9'}
        with self.assertRaises(LinearEffectHold):
            await self.step(action=broken)
        self.assertEqual(self.calls, [])

    async def test_same_operation_cannot_rebind_owner_packet_on_restart(self):
        self.mode = 'unknown-no-effect'
        await self.step()
        self.reopen()
        with self.assertRaisesRegex(LinearEffectHold, 'custody_conflict'):
            await self.step(binding=replace(self.binding(), packet_sha256='f' * 64))
        self.assertEqual(len(self.writes), 1)

    async def test_dependency_direction_readback_is_not_completion(self):
        body = {'version': 1, 'kind': 'linear-ensure-dependency', 'issue_id': ISSUE,
                'project_id': PROJECT, 'blocked_by_id': SECOND}
        action = {**body, 'action_id': fingerprint(body)}
        self.assertEqual((await self.step(action))['status'], 'verified')
        evidence = self.current.state[STORE][action['action_id']]['evidence']
        self.assertEqual(evidence['blocker_state_type'], 'started')
        self.assertNotIn('dependencies_satisfied', evidence)
        self.reopen()
        self.assertEqual((await self.step(action))['status'], 'verified')
        self.assertEqual(len(self.writes), 1)

    async def test_milestone_exact_marker_and_structured_content_no_done(self):
        self.assertEqual((await self.step(self.milestone))['status'], 'verified')
        self.assertEqual(self.nodes[0]['body'], milestone_body(self.milestone))
        self.assertNotIn('Done', self.nodes[0]['body'])
        self.reopen()
        self.assertEqual((await self.step(self.milestone))['status'], 'verified')
        self.assertEqual(len(self.writes), 1)

    async def test_marker_alone_or_conflicting_content_cannot_qualify_or_duplicate(self):
        marker = 'native-source-milestone:' + self.milestone['milestone_id']
        for body in (marker, milestone_body(self.milestone) + '\nforged tail'):
            self.nodes = [{'id': 'conflicting', 'body': body}]
            self.assertEqual((await self.step(self.milestone))['status'], 'unknown')
        self.assertEqual(self.writes, [])

    async def test_verified_effect_removed_later_cannot_replay(self):
        await self.step()
        self.nodes.clear()
        self.reopen()
        self.assertEqual((await self.step())['status'], 'unknown')
        self.assertEqual(len(self.writes), 1)

    async def test_native_project_drift_on_readback_blocks_write(self):
        self.identity['project']['id'] = SECOND
        self.assertEqual((await self.step())['status'], 'unknown')
        self.assertEqual(self.writes, [])

    async def test_explicit_failure_is_not_permission_to_retry(self):
        self.mode = 'false-success'
        self.assertEqual((await self.step())['status'], 'failed')
        self.reopen()
        self.mode = 'normal'
        self.assertEqual((await self.step())['status'], 'failed')
        self.assertEqual(len(self.writes), 1)

    async def test_mutation_http_denial_never_replayed(self):
        self.mode = 'denied'
        self.assertEqual((await self.step())['status'], 'denied')
        self.reopen()
        self.mode = 'normal'
        self.assertEqual((await self.step())['status'], 'denied')
        self.assertEqual(len(self.writes), 1)
        self.mode = 'read-error'
        self.assertEqual((await self.step())['status'], 'denied')
        self.assertEqual(len(self.writes), 1)

    async def test_pending_intent_before_mutation_is_not_absence_permission(self):
        binding = self.binding()
        from dataclasses import asdict
        self.current.state[STORE] = {binding.operation_id: {
            'version': 1, 'binding': asdict(binding), 'action': self.link,
            'status': 'pending', 'evidence': None}}
        self.current.save()
        self.reopen()
        self.assertEqual((await self.step())['status'], 'unknown')
        self.assertEqual(self.writes, [])

    async def test_owner_stop_during_native_read_prevents_mutation(self):
        self.mode = 'stop-after-read'
        with self.assertRaisesRegex(LinearEffectHold, 'owner_stopped'):
            await self.step()
        self.assertEqual(self.writes, [])
        self.assertFalse(self.path.exists())

    async def test_duplicate_matching_milestone_is_a_hold_not_verified(self):
        self.nodes = [{'id': name, 'body': milestone_body(self.milestone)} for name in ('one', 'two')]
        self.assertEqual((await self.step(self.milestone))['status'], 'unknown')
        self.assertEqual(self.writes, [])
