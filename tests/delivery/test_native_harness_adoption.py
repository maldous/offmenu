"""Bounded offline adoption, custody drift and same-operation recovery checks."""
import copy
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

import native_harness_adoption as adoption
from native_harness_contract import fingerprint, load_release_policy


ROOT = Path(__file__).resolve().parents[2]


class AdoptionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='offmenu-adoption-')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.policy = load_release_policy(ROOT / 'config/delivery-release-policy.json')
        self.counter = 0
        metadata = self.write({'retained': 'sanitized fixture only'})
        artifact = self.write(b'coherent source artifact', 'source/fixture.py')
        source = dict(repository='maldous/offmenu', branch='develop', target='main',
                      base='a' * 40, head='b' * 40, tree='c' * 40,
                      policy_sha256=fingerprint(self.policy))
        candidate = dict(version=1, kind='release-candidate-v1', source=source,
                         required_profiles=['coherent'], artifacts=[artifact])
        self.validation = dict(version=1, kind='delivery-handoff-v1',
            issue_id='12345678-1234-1234-1234-123456789abc',
            project_id='ffb6c7d9-4eff-46eb-a805-99f0cc2edfa0', owner='root-owner',
            origin=dict(kind='reviewed-source-v1', evidence=metadata), source=source,
            outputs=[artifact], evidence=[metadata],
            review=dict(reviewer='independent-reviewer', author='root-owner', verdict='accept',
                        source_sha256=fingerprint(source), outputs_sha256=fingerprint([artifact]),
                        evidence=metadata),
            operation=dict(id='original-validation', backend='windmill', job_id='original-job',
                           status='succeeded', command_sha256='d' * 64, runner_sha256='e' * 64,
                           policy_sha256='f' * 64, receipt=metadata),
            effect=dict(operation_id='original-validation', status='verified'))
        self.snapshot = dict(version=1, kind='native-legacy-snapshot-v1',
            runtime_path='/private/legacy-runtime', source_head='1' * 40,
            source_tree='2' * 40, config_sha256=metadata['sha256'], runtime_sha256=metadata['sha256'],
            source_sha256=metadata['sha256'], install_receipts=[metadata])
        snapshot_ref = self.write(self.snapshot)
        self.stop = dict(version=1, kind='native-stop-witness-v1',
            snapshot_sha256=snapshot_ref['sha256'], observed_at=1000, stopped=True,
            inflight=0, children_gone=True, operation_ids=[])
        self.rollback = dict(version=1, kind='native-rollback-custody-v1',
            snapshot_sha256=snapshot_ref['sha256'], custodian='existing-owner',
            artifacts=dict(source=metadata, config=metadata, runtime=metadata), verification=metadata)
        target = dict(source_head=source['head'], source_tree=source['tree'],
            policy_sha256=source['policy_sha256'], paths=copy.deepcopy(adoption.TARGETS),
            files=[artifact], dependencies=metadata, config=metadata,
            owner_manifest=metadata, publisher_manifest=metadata)
        self.request = dict(version=1, kind='native-harness-adoption-request-v1', owner='root-owner',
            candidate=self.write(candidate), components={issue:dict(source=metadata, tests=metadata,
            review=metadata) for issue in adoption.COMPONENTS},
            coherent_validation=self.write(self.validation), legacy_snapshot=snapshot_ref,
            stop_witness=self.write(self.stop), rollback=self.write(self.rollback), target=target,
            credential_references=['EXISTING_GITHUB_APP_REFERENCE'], effects=[],
            readback=dict(source_head=source['head'], source_tree=source['tree'],
                          policy_sha256=source['policy_sha256'], closure_sha256=fingerprint(target),
                          config_sha256=metadata['sha256'], dependencies_sha256=metadata['sha256']))
        self.accepted = dict(components=copy.deepcopy(self.request['components']),
                             coherent_validation=copy.deepcopy(self.request['coherent_validation']))

    def write(self, value, name=None):
        self.counter += 1
        name = name or f'evidence-{self.counter}.json'
        raw = value if type(value) is bytes else json.dumps(value, sort_keys=True).encode()
        path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(raw)
        return dict(path=name, sha256=hashlib.sha256(raw).hexdigest())

    def prepare(self, **kwargs):
        options = dict(evidence_root=self.root, accepted=self.accepted, now=1000)
        options.update(kwargs)
        return json.loads(adoption.prepare(self.request, self.policy, **options))

    def disk(self):
        return {str(p.relative_to(self.root)): p.read_bytes()
                for p in self.root.rglob('*') if p.is_file()}

    def test_qualified_offline_plan_is_deterministic_readonly_and_never_host_authority(self):
        before = self.disk()
        request = copy.deepcopy(self.request)
        with patch.object(adoption.owner_install, 'install', side_effect=AssertionError('no install')), \
             patch.object(adoption.publisher_install, 'install', side_effect=AssertionError('no install')), \
             patch.object(adoption.owner_install, 'prepare', side_effect=AssertionError('no stage')):
            raw = adoption.prepare(self.request, self.policy, evidence_root=self.root,
                                   accepted=self.accepted, now=1000)
            self.assertEqual(raw, adoption.prepare(self.request, self.policy, evidence_root=self.root,
                                                  accepted=self.accepted, now=1000))
        result = json.loads(raw)
        self.assertTrue(result['milestones']['source_ready'])
        self.assertTrue(result['milestones']['coherent_validation_accepted'])
        self.assertTrue(result['stop_witness_qualified'])
        self.assertFalse(result['host_mutation_authorized'])
        for milestone in ('released_source', 'installed_adopted', 'active_observed', 'legacy_retired'):
            self.assertEqual(result['milestones'][milestone], 'unknown')
        self.assertEqual(result['holds'], ['REVIEWED_TYPED_UPGRADE_ROUTE_REQUIRED',
                                          'ACTUAL_HOST_CONFIRMATIONS_AND_READBACK_REQUIRED'])
        self.assertTrue(result['installer_constraints']['permanent_no_replay'])
        self.assertEqual(before, self.disk())
        self.assertEqual(request, self.request)

    def test_json_claims_cannot_supply_acceptance_or_waive_upgrade(self):
        result = self.prepare(accepted=None)
        self.assertFalse(result['milestones']['source_ready'])
        self.assertFalse(result['milestones']['coherent_validation_accepted'])
        self.request['host_mutation_authorized'] = True
        with self.assertRaises(adoption.Refused):
            self.prepare()

    def test_latest_component_and_validation_pins_are_required(self):
        for role in ('source', 'tests', 'review'):
            value = copy.deepcopy(self.request)
            self.request['components']['UIF-127'][role] = self.write({'new': role})
            self.assertFalse(self.prepare()['milestones']['source_ready'])
            self.request = value
        self.validation['review']['verdict'] = 'changes-requested'
        self.request['coherent_validation'] = self.write(self.validation)
        self.accepted['coherent_validation'] = copy.deepcopy(self.request['coherent_validation'])
        self.assertFalse(self.prepare()['milestones']['coherent_validation_accepted'])

    def test_coherent_source_and_output_drift_are_rejected(self):
        self.validation['source']['tree'] = '0' * 40
        self.validation['review']['source_sha256'] = fingerprint(self.validation['source'])
        self.request['coherent_validation'] = self.write(self.validation)
        with self.assertRaisesRegex(adoption.Refused, 'coherent_validation_binding'):
            self.prepare()

    def test_unknown_effect_preserves_original_job_and_attempt_without_retry(self):
        self.validation['operation']['status'] = 'unknown'
        self.validation['effect']['status'] = 'unknown'
        self.request['effects'] = [self.write(self.validation)]
        result = self.prepare()
        effect = result['unresolved_effects'][0]
        self.assertEqual(effect['operation']['id'], 'original-validation')
        self.assertEqual(effect['operation']['job_id'], 'original-job')
        self.assertEqual(result['next_action'], 'reconcile-original-effects')
        self.assertIn('RECONCILE_ORIGINAL_EFFECTS_NO_RETRY', result['holds'])
        self.assertIsNone(effect['attempt'])
        self.validation['origin']['kind'] = 'native-coding-v1'
        self.validation['attempt'] = dict(id='original-attempt', lease_id='original-lease',
            admission=self.validation['origin']['evidence'])
        self.request['effects'] = [self.write(self.validation)]
        attempt = self.prepare()['unresolved_effects'][0]['attempt']
        self.assertEqual(attempt['id'], 'original-attempt')
        self.assertEqual(attempt['lease_id'], 'original-lease')

    def test_repinning_different_rollback_bytes_does_not_change_snapshot(self):
        self.rollback['artifacts']['config'] = self.write({'different': 'config backup'})
        self.request['rollback'] = self.write(self.rollback)
        with self.assertRaisesRegex(adoption.Refused, 'rollback_artifact_binding'):
            self.prepare()

    def test_stop_witness_unknown_inflight_stale_future_and_children_hold(self):
        for field, value in (('stopped', None), ('stopped', False), ('children_gone', None),
                             ('children_gone', False), ('inflight', None), ('inflight', 1),
                             ('observed_at', 699), ('observed_at', 1001),
                             ('operation_ids', ['original-operation'])):
            stop = {**self.stop, field: value}
            self.request['stop_witness'] = self.write(stop)
            with self.subTest(field=field, value=value):
                result = self.prepare()
                self.assertFalse(result['stop_witness_qualified'])
                self.assertIn('FRESH_STOPPED_ZERO_INFLIGHT_WITNESS_REQUIRED', result['holds'])
        self.request['stop_witness'] = self.write({**self.stop, 'inflight': False})
        with self.assertRaises(adoption.Refused):
            self.prepare()

    def test_rollback_and_snapshot_binding_drift_fail_closed(self):
        self.rollback['snapshot_sha256'] = '0' * 64
        self.request['rollback'] = self.write(self.rollback)
        with self.assertRaisesRegex(adoption.Refused, 'rollback_snapshot'):
            self.prepare()
        self.request['rollback'] = self.write({**self.rollback,
            'snapshot_sha256': self.request['legacy_snapshot']['sha256']})
        artifact = self.rollback['artifacts']['source']
        (self.root / artifact['path']).write_bytes(b'changed custody')
        with self.assertRaisesRegex(adoption.Refused, 'evidence_pin'):
            self.prepare()

    def test_target_readback_source_and_credential_content_are_rejected(self):
        baseline = copy.deepcopy(self.request)
        for change in ('target', 'readback', 'credential', 'source'):
            self.request = copy.deepcopy(baseline)
            if change == 'target':
                self.request['target']['paths']['owner_source'] = '/tmp/repointed'
            elif change == 'readback':
                self.request['readback']['closure_sha256'] = '0' * 64
            elif change == 'credential':
                self.request['credential_references'] = [{'name': 'TOKEN', 'value': 'PRIVATE'}]
            else:
                self.request['target']['source_head'] = '0' * 40
            with self.subTest(change=change), self.assertRaises(adoption.Refused):
                self.prepare()

    def test_links_hardlinks_path_escape_size_and_duplicate_json_are_rejected(self):
        original = self.request['candidate']
        path = self.root / original['path']
        raw = path.read_bytes()
        path.unlink()
        outside = self.root / 'outside.json'
        outside.write_bytes(raw)
        path.symlink_to(outside)
        with self.assertRaises((OSError, ValueError)):
            self.prepare()
        path.unlink()
        os.link(outside, path)
        with self.assertRaises(ValueError):
            self.prepare()
        path.unlink()
        path.write_bytes(raw)
        for ref in (dict(path='../outside.json', sha256='0'*64),
                    self.write(b'x' * (adoption.LIMIT + 1)),
                    self.write(b'{"version":1,"version":1}')):
            self.request['candidate'] = ref
            with self.subTest(ref=ref['path']), self.assertRaises(ValueError):
                self.prepare()

    def test_cli_is_inspection_only_and_fixed_errors_do_not_echo_content(self):
        request = self.write(self.request, 'request.json')
        env = {**os.environ, 'PYTHONPATH': str(ROOT / 'src') + os.pathsep + str(ROOT / 'tools/delivery')}
        command = [sys.executable, str(ROOT / 'tools/delivery/native_harness_adoption.py'),
                   str(self.root / request['path']), '--policy',
                   str(ROOT / 'config/delivery-release-policy.json'), '--evidence-root', str(self.root)]
        before = self.disk()
        result = subprocess.run(command, env=env, capture_output=True, text=True, timeout=10)
        self.assertEqual(result.returncode, 0, result.stderr)
        packet = json.loads(result.stdout)
        self.assertFalse(packet['milestones']['source_ready'])
        self.assertFalse(packet['host_mutation_authorized'])
        self.assertEqual(before, self.disk())
        (self.root / request['path']).write_text('PRIVATE bad JSON')
        result = subprocess.run(command, env=env, capture_output=True, text=True, timeout=10)
        self.assertEqual(result.returncode, 2)
        self.assertEqual(result.stderr, 'adoption preflight rejected\n')
        self.assertEqual(result.stdout, '')
