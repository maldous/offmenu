"""Finite consumer with real local Git/LinearClient and CurrentWork.save.

Original native/Journal/review readers and protected UID984 writer/readback are
synthetic boundaries here. Their original validators and live composition are
not certified by this fixture. No protected store or external service is used.
"""
import asyncio
import copy
from dataclasses import asdict, replace
import hashlib
import json
import os
from pathlib import Path
import subprocess
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import httpx
from stokowski.linear import LinearClient
from stokowski_adapter import CurrentWork, read_record
from native_harness_runtime import OwnerBinding
from native_harness_contract import fingerprint, load_release_policy
import native_harness_linear as module

ISSUE = 'b346f68a-7f0d-4544-b7a5-252341ee2db3'
PROJECT = 'ce60c1ab-a732-4a71-8471-14c9dc393886'
TEAM = '53f584e7-70a1-4b1e-b982-b815210e47d4'
PERSON = 'ba297b04-d7be-4b25-b9ae-27cecdf3d411'
DONE = 'a346f68a-7f0d-4544-b7a5-252341ee2db3'


class OutcomeTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.repo = self.root / 'repo'
        self.repo.mkdir()
        self.git('init', '-q')
        self.git('config', 'user.name', 'Synthetic')
        self.git('config', 'user.email', 'synthetic@example.test')
        (self.repo / 'unit.py').write_text('base\n')
        self.git('add', 'unit.py'); self.git('commit', '-qm', 'base')
        self.base = self.git('rev-parse', 'HEAD')
        self.seed_tree = self.git('rev-parse', 'HEAD^{tree}')
        self.git('checkout', '-qb', 'bugfix/synthetic')
        (self.repo / 'unit.py').write_text('source correction\n')
        self.git('commit', '-qam', 'correction')
        self.candidate = self.git('rev-parse', 'HEAD')
        self.git('checkout', '-qb', 'develop', self.base)
        self.git('merge', '--no-ff', '-qm', 'normal merge', 'bugfix/synthetic')
        self.head = self.git('rev-parse', 'HEAD')
        self.tree = self.git('rev-parse', 'HEAD^{tree}')
        self.runtime = self.root / 'current'; self.runtime.mkdir()
        self.publisher = self.root / 'accepted-sources'; self.publisher.mkdir(mode=0o755)
        (self.publisher / 'by-commit').mkdir(mode=0o755)
        (self.publisher / 'by-operation').mkdir(mode=0o755)
        self.published = False
        self.native = self.root / 'native'; (self.native / 'requests').mkdir(parents=True)
        (self.native / 'requests/UIF-138.json').write_text('{"synthetic":"original request"}\n')
        self.current = CurrentWork.__new__(CurrentWork)
        c = self.current
        c.runtime = self.runtime; c.root = self.root
        c.owner_custody = {'schema': 'synthetic fixture; real guard replaced only in test'}
        c.read_only = c.stopping = False
        import native_harness_runtime
        c.config = {'owner': 'root-owner', 'source_sha256': {
            'tools/delivery/native_harness_runtime.py': hashlib.sha256(Path(native_harness_runtime.__file__).read_bytes()).hexdigest(),
            'tools/delivery/native_harness_linear.py': hashlib.sha256(Path(module.__file__).read_bytes()).hexdigest()}}
        c.state = {'owner': 'root-owner', 'accepted_delivery': False}
        c.entries = {'UIF-138': {'issue': 'UIF-138', 'issue_id': ISSUE}}
        c.state_path = self.runtime / 'current-owner.json'
        c.guard = lambda: None
        c.private = lambda value: Path(value)
        c._private_pin = lambda ref: self.read_pin(ref)
        self.issue = SimpleNamespace(id=ISSUE, identifier='UIF-138')
        self.contract = {'acceptance': ['exact source correction and synthetic proof'], 'allowed_paths': ['unit.py']}
        self.manifest = {'tasks': {'UIF-138': copy.deepcopy(self.contract)}}
        self.unit = {'original': 'native unit'}
        c.context = lambda *a, **k: (self.native, self.manifest, None)
        c.gate_binding = lambda *a, **k: copy.deepcopy(self.unit)
        c._check_unit_review = lambda review: copy.deepcopy(self.unit)
        self.native_reads = []
        c._completed_native_evidence = lambda *args: self.native_reads.append(args)
        self.policy = {'owner': 'root-owner', 'coordinator_runtime': str(self.runtime), 'expires_at': 9999999999,
            'project_source': {'repository': 'maldous/offmenu', 'branch': 'develop',
                'origin': 'git@github.com:maldous/offmenu.git', 'source_repository': str(self.repo),
                'seed': {'head': self.base, 'tree': self.seed_tree},
                'accepted_facts_path': str(self.publisher / 'latest.json')},
            'contracts': {'UIF-138': {'issue_id': ISSUE, 'project_id': PROJECT, 'assignee_id': PERSON,
                'dependencies': [], 'scope': self.contract['allowed_paths'], 'acceptance': self.contract['acceptance'],
                'source_outcome': {'team_id': TEAM, 'description_sha256': hashlib.sha256(b'Full synthetic source-only requirement').hexdigest(),
                    'full_issue_contract': True, 'done_state_id': DONE}}}}
        c.config['owner_intake_policy'] = self.pin('policy.json', self.policy)
        self.binding = OwnerBinding(ISSUE, PROJECT, 'root-owner', 'b'*64, 'c'*64,
                                    'integration', fingerprint(self.unit))
        canonical = {'repository': 'maldous/offmenu', 'branch': 'develop', 'head': self.head,
            'tree': self.tree, 'parents': [self.base, self.candidate], 'base': self.base,
            'candidate_head': self.candidate, 'pr_url': 'https://github.com/maldous/offmenu/pull/999',
            'operation_id': self.binding.operation_id}
        helper = self.pin('helper.json', {'operation_id': self.binding.operation_id,
            'status': 'verified', 'child_tree_gone': True, 'canonical': copy.deepcopy(canonical)})
        self.outcome = {'effect': {'operation_id': self.binding.operation_id, 'status': 'verified',
            'child_tree_gone': True}, 'review': self.pin('review.json', {'independent': 'accepted exact native review'}),
            'handoff': {'source': {'head': self.candidate, 'base': self.base}},
            'canonical': {**canonical, 'helper_receipt': helper}}
        release_policy = load_release_policy(Path(__file__).resolve().parents[2] / 'config/delivery-release-policy.json')
        self.outcome['handoff'] = {'version': 1, 'kind': 'delivery-handoff-v1',
            'issue_id': ISSUE, 'project_id': PROJECT, 'owner': 'root-owner',
            'origin': {'kind': 'reviewed-source-v1', 'evidence': {'path': '.delivery/synthetic.json', 'sha256': 'a'*64}},
            'source': {'repository': 'maldous/offmenu', 'branch': 'bugfix/synthetic', 'base': self.base,
                'head': self.candidate, 'tree': self.tree, 'target': 'develop', 'policy_sha256': fingerprint(release_policy)},
            'outputs': [{'path': 'unit.py', 'sha256': hashlib.sha256((self.repo / 'unit.py').read_bytes()).hexdigest()}],
            'evidence': [{'path': '.delivery/synthetic.json', 'sha256': 'a'*64}]}
        packet = {'policy': release_policy, 'handoff': self.outcome['handoff'], 'candidate': None,
                  'linear': {}, 'release': None}
        self.binding = replace(self.binding, packet_sha256=fingerprint(packet))
        packet_ref = self.pin('packet.json', packet)
        c._native_harness_selection = lambda identifier: {'binding': asdict(self.binding), 'packet': packet_ref}
        self.canonical_fact = {**canonical, 'schema': 'offmenu-accepted-project-source/1',
            'unit_sha256': self.binding.unit_sha256, 'packet_sha256': self.binding.packet_sha256,
            'policy_sha256': fingerprint(release_policy),
            'helper_receipt': {'path': '/var/lib/offmenu-publisher/synthetic-receipt.json', 'sha256': 'd'*64},
            'previous': {'schema': 'offmenu-accepted-project-source-seed/1',
                         **self.policy['project_source']['seed'],
                         'policy_sha256': fingerprint(self.policy['project_source'])}, 'observed_at': 1793577600}
        self.outcome['canonical'] = self.publish_fact(self.canonical_fact)
        self.comments = []; self.writes = []; self.mode = 'normal'
        self.remote_state = {'id': 'backlog', 'type': 'backlog'}
        self.client = LinearClient(endpoint='https://linear.invalid/graphql', api_key='synthetic-only')
        await self.client._client.aclose()
        self.client._client = httpx.AsyncClient(transport=httpx.MockTransport(self.transport))
        self.addAsyncCleanup(self.client.close)
        self.enterContext(patch.object(module, 'SOURCE_REPOSITORY', str(self.repo)))
        self.enterContext(patch.object(module, 'PUBLISHER_SOURCE_ROOT', str(self.publisher)))
        self.enterContext(patch.object(module, 'PUBLISHER_UID', os.getuid()))
        self.enterContext(patch('stokowski_prepare.owner_intake_policy',
            side_effect=lambda config: self.read_pin(config['owner_intake_policy']), create=True))
        self.enterContext(patch('stokowski_prepare.owner_policy_contract',
            side_effect=lambda config, policy, name: policy['contracts'][name], create=True))
        self.journal = self.enterContext(patch('native_harness_runtime.native_journal_acceptance',
            return_value={'origin': 'native-journal-v1', 'operation_id': 'original-validated-op'}))
        async def canonical_reader(*args):
            return {'fact': copy.deepcopy(self.canonical_fact), 'evidence': self.readonly_ref()}
        self.enterContext(patch('native_harness_runtime.verified_canonical_source',
            new=canonical_reader, create=True))
        self.coverage = self.enterContext(patch('native_harness_runtime.review_coverage', return_value={}))

    def git(self, *args):
        return subprocess.check_output(['git', '-C', str(self.repo), *args], stderr=subprocess.DEVNULL, text=True).strip()

    def pin(self, name, value):
        p = self.runtime / name; p.write_text(json.dumps(value) + '\n')
        return {'path': str(p), 'sha256': hashlib.sha256(p.read_bytes()).hexdigest()}

    def read_pin(self, ref):
        p = Path(ref['path'])
        self.assertTrue(p.is_relative_to(self.root))
        self.assertEqual(hashlib.sha256(p.read_bytes()).hexdigest(), ref['sha256'])
        return read_record(p)

    def transport(self, request):
        data = json.loads(request.content); query = data['query']; variables = data['variables']
        if query.startswith('mutation'):
            disk = read_record(self.current.state_path)
            self.assertEqual(len(disk[module.SOURCE_OUTCOMES]), 1)
            record = next(iter(disk[module.SOURCE_OUTCOMES].values()))
            stage = 'comment' if 'commentCreate' in query else 'completion'
            self.assertEqual(record[stage], 'pending')
            self.writes.append(data)
            if self.mode == 'denied':
                return httpx.Response(403, json={'errors': [{'message': 'synthetic denied'}]})
            if self.mode == 'unknown-no-effect':
                raise httpx.ReadTimeout('synthetic uncertain metadata', request=request)
            if stage == 'comment':
                self.comments.append({'id': 'native-comment', 'body': variables['input']['body']})
            else:
                self.assertEqual(variables, {'id': ISSUE, 'input': {'stateId': DONE}})
                self.remote_state = {'id': DONE, 'type': 'completed'}
            if self.mode == 'lost-reply':
                raise httpx.ReadTimeout('synthetic lost reply', request=request)
            return httpx.Response(200, json={'data': {'success': True}})
        remote = {'id': ISSUE, 'identifier': 'UIF-138', 'description': 'Full synthetic source-only requirement',
            'project': {'id': PROJECT}, 'team': {'id': TEAM, 'states': {'nodes': [{'id': DONE, 'type': 'completed'}]}},
            'assignee': {'id': PERSON}, 'delegate': None, 'state': self.remote_state,
            'inverseRelations': {'nodes': [], 'pageInfo': {'hasNextPage': False}},
            'comments': {'nodes': self.comments, 'pageInfo': {'hasNextPage': False}}}
        if self.mode == 'changed-owner': remote['assignee'] = None
        if self.mode == 'cancelled': remote['state'] = {'id': 'cancelled', 'type': 'canceled'}
        return httpx.Response(200, json={'data': {'issue': remote}})

    def readonly_ref(self):
        p = self.publisher / 'by-commit' / (self.head + '.json')
        return {'path': str(p), 'sha256': hashlib.sha256(p.read_bytes()).hexdigest()}

    def publish_fact(self, fact):
        p = self.publisher / 'by-commit' / (fact['head'] + '.json')
        p.write_text(json.dumps(fact) + '\n'); p.chmod(0o444)
        return {'path': str(p), 'sha256': hashlib.sha256(p.read_bytes()).hexdigest()}

    async def run_outcome(self):
        if not self.published:
            p = self.publisher / 'latest.json'
            p.write_text(json.dumps({'schema': 'offmenu-accepted-project-source-pointer/1',
                'latest': self.outcome['canonical']}) + '\n'); p.chmod(0o444)
            self.published = True
        return await module.finalize_source_outcome(self.current, self.issue, self.binding,
            policy=self.policy, outcome=self.outcome, linear_client=self.client)

    async def test_complete_normal_consumer_facts_and_metadata_reopen_dedup(self):
        seed = module.accepted_project_source(self.current, PROJECT)
        self.assertEqual(seed['head'], self.base)
        result = await self.run_outcome()
        self.assertEqual(result['status'], 'verified', result)
        self.assertTrue(result['closed']); self.assertTrue(result['refill_eligible'])
        self.assertFalse(result['accepted_delivery'])
        self.assertEqual(len(self.writes), 2)
        self.assertEqual(module.accepted_project_source(self.current, PROJECT)['head'], self.head)
        self.current.state = read_record(self.current.state_path)
        self.assertEqual((await self.run_outcome())['status'], 'verified')
        self.assertEqual(len(self.writes), 2)
        self.assertTrue(self.native_reads); self.assertTrue(self.journal.called); self.assertTrue(self.coverage.called)
        # Removing a previously verified effect is a hold, not a refill permit or replay.
        self.comments.clear()
        withdrawn = await self.run_outcome()
        self.assertEqual(withdrawn['status'], 'unknown')
        self.assertFalse(withdrawn['refill_eligible'])
        self.assertEqual(len(self.writes), 2)

    async def test_uncertain_absence_is_readback_only_not_metadata_or_merge_replay(self):
        self.mode = 'unknown-no-effect'
        self.assertEqual((await self.run_outcome())['status'], 'unknown')
        self.mode = 'normal'
        self.current.state = read_record(self.current.state_path)
        self.assertEqual((await self.run_outcome())['status'], 'unknown')
        self.assertEqual(len(self.writes), 1)
        self.assertEqual(module.accepted_project_source(self.current, PROJECT)['head'], self.head)

    async def test_lost_reply_with_exact_native_readback_finishes_without_duplicate(self):
        self.mode = 'lost-reply'
        self.assertEqual((await self.run_outcome())['status'], 'verified')
        self.assertEqual(len(self.writes), 2)
        self.assertEqual((await self.run_outcome())['status'], 'verified')
        self.assertEqual(len(self.writes), 2)

    async def test_changed_owner_cancellation_or_full_contract_drift_holds(self):
        for mode in ('changed-owner', 'cancelled'):
            self.mode = mode
            self.assertEqual((await self.run_outcome())['status'], 'held')
        self.assertEqual(self.writes, [])
        self.assertFalse((self.runtime / 'accepted-project-source.json').exists())
        self.mode = 'normal'
        self.manifest['tasks']['UIF-138']['acceptance'] = ['changed contract']
        self.assertEqual((await self.run_outcome())['status'], 'held')
        self.assertEqual(self.writes, [])

    async def test_canonical_drift_and_missing_facts_never_use_seed_fallback(self):
        original_ref = copy.deepcopy(self.outcome['canonical'])
        self.outcome['canonical']['sha256'] = 'e' * 64
        self.assertEqual((await self.run_outcome())['status'], 'held')
        self.assertEqual(self.writes, [])
        self.outcome['canonical'] = original_ref
        (self.publisher / 'latest.json').unlink(); self.published = False
        self.assertEqual((await self.run_outcome())['status'], 'verified')
        (self.publisher / 'latest.json').unlink()
        with self.assertRaisesRegex(module.LinearEffectHold, 'accepted_source_missing_facts'):
            module.accepted_project_source(self.current, PROJECT)

    async def test_legacy_disabled_does_not_close(self):
        issued = self.policy['contracts']['UIF-138']
        for identifier in ('UIF-102', 'UIF-130'):
            with patch('stokowski_prepare.owner_policy_contract', return_value=issued, create=True):
                with self.assertRaisesRegex(module.LinearEffectHold, 'source_outcome_done_state'):
                    module._source_grant(self.current, self.policy,
                        SimpleNamespace(id=ISSUE, identifier=identifier),
                        {'tasks': {identifier: copy.deepcopy(self.contract)}})
        del self.current.config['owner_intake_policy']
        self.assertEqual((await self.run_outcome())['status'], 'held')
        self.assertEqual(self.writes, [])

    async def test_explicit_milestone_only_never_updates_workflow_state(self):
        self.policy['contracts']['UIF-138']['source_outcome']['full_issue_contract'] = False
        self.policy['contracts']['UIF-138']['source_outcome']['done_state_id'] = None
        self.current.config['owner_intake_policy'] = self.pin('policy.json', self.policy)
        result = await self.run_outcome()
        self.assertEqual(result['status'], 'verified', result)
        self.assertFalse(result['closed'])
        self.assertEqual(len(self.writes), 1)
        self.assertIn('commentCreate', self.writes[0]['query'])
        self.assertFalse(self.current.state['accepted_delivery'])

    async def test_untrusted_custody_and_symlink_never_certify_source(self):
        p = Path(self.outcome['canonical']['path'])
        p.chmod(0o644)
        self.assertEqual((await self.run_outcome())['status'], 'held')
        self.assertEqual(self.writes, [])
        p.chmod(0o444)
        with patch.object(module, 'PUBLISHER_UID', os.getuid() + 10000):
            self.assertEqual((await self.run_outcome())['status'], 'held')
        target = self.publisher / 'body.json'
        p.rename(target); p.symlink_to(target)
        self.assertEqual((await self.run_outcome())['status'], 'held')
        self.assertEqual(self.writes, [])

    async def test_denied_metadata_hold_survives_readback_and_reopen(self):
        self.mode = 'denied'
        first = await self.run_outcome()
        self.assertEqual(first['status'], 'denied', first)
        self.assertFalse(first['refill_eligible'])
        self.mode = 'normal'
        self.current.state = read_record(self.current.state_path)
        again = await self.run_outcome()
        self.assertEqual(again['status'], 'denied', again)
        self.assertEqual(len(self.writes), 1)
