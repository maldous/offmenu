"""Read-only evidence view across actual local LangGraph execution boundaries."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import copy
import unittest
from unittest.mock import patch

from test_engine import DeliveryFixture
from offmenu.delivery.engine import DeliveryError, writer
from offmenu.delivery.status import inspect_task, project_native_handoff


class StatusTests(DeliveryFixture):
    def snapshot(self):
        return {str(path.relative_to(self.root)): hashlib.sha256(path.read_bytes()).hexdigest()
                for path in self.root.rglob('*') if path.is_file()}

    def inspect(self):
        before = self.snapshot()
        result = inspect_task(self.root, self.task)
        self.assertEqual(self.snapshot(), before)
        self.assertEqual(result['schema_version'], 1)
        self.assertEqual(result['authority'], 'observation_only')
        self.assertFalse(result['source_and_execution_evidence_verified'])
        return result

    def test_unknown_task_creates_no_state(self):
        result = self.inspect()
        self.assertEqual(result['recorded_status'], 'not_found')
        self.assertEqual(result['reasons'], ['binding_not_found'])
        self.assertFalse((self.root / '.delivery').exists())

    def test_accepted_receipt_and_current_bytes_are_distinct_without_reexecution(self):
        self.run_engine()
        accepted = self.record('accepted.json').read_bytes()
        result = self.inspect()
        self.assertEqual(result['recorded_status'], 'accepted')
        self.assertTrue(result['outputs_match'])
        self.assertTrue(result['identity_matches'])
        self.assertTrue(result['checkpoint_available'])
        (self.root / 'result.txt').write_text('changed after acceptance')
        result = self.inspect()
        self.assertEqual(result['recorded_status'], 'accepted')
        self.assertFalse(result['outputs_match'])
        self.assertIn('output_drift', result['reasons'])
        self.assertNotEqual(result['outputs']['result.txt']['actual'],
                            result['outputs']['result.txt']['expected'])
        self.assertEqual(self.record('accepted.json').read_bytes(), accepted)
        self.assertEqual((self.root / 'counter.txt').read_text(), '1')

    def test_missing_output_and_revision_or_branch_drift_are_reported(self):
        self.run_engine()
        (self.root / 'result.txt').unlink()
        self.git('switch', '-qc', 'develop')
        self.git('commit', '--allow-empty', '-qm', 'Changed head')
        result = self.inspect()
        self.assertIsNone(result['outputs']['result.txt']['actual'])
        self.assertFalse(result['identity_matches'])
        self.assertIn('revision_or_branch_changed', result['reasons'])

    def test_paused_and_uncertain_checks_are_observed_while_writer_is_owned(self):
        self.run_engine('standards')
        self.assertEqual(self.inspect()['checks'], [{'id': 'counter', 'status': 'not_started'}])
        for status in ('running', 'uncertain', 'timed_out', 'cancelled'):
            self.record().write_text(json.dumps({'status': status, 'attempt': 1}))
            self.record('cancel.json').write_text('{"requested":true}')
            with writer(self.root, reconciliation=True):
                result = self.inspect()
            self.assertEqual(result['reconciliation_required'], ['counter'])
            self.assertTrue(result['cancellation_requested'])
            self.assertTrue(result['checkpoint_available'])
            self.assertFalse(result['acceptance_record_present'])
        self.assertFalse((self.root / 'counter.txt').exists())

    def test_binding_and_acceptance_conflicts_fail_closed_without_writes(self):
        self.run_engine()
        for filename, key in [('binding.json', 'task_sha256'), ('accepted.json', 'owner')]:
            path = self.record(filename)
            original = path.read_bytes()
            value = json.loads(original)
            value[key] = 'different'
            path.write_text(json.dumps(value))
            before = self.snapshot()
            with self.assertRaisesRegex(DeliveryError, 'binding mismatch'):
                inspect_task(self.root, self.task)
            self.assertEqual(self.snapshot(), before)
            path.write_bytes(original)

    def test_outside_checkpoint_or_output_is_not_followed(self):
        self.run_engine()
        for path in (self.record('graph.sqlite'), self.root / 'result.txt'):
            original = path.read_bytes()
            path.unlink()
            path.symlink_to(Path(__file__).resolve())
            with self.assertRaisesRegex(DeliveryError, 'outside checkout'):
                inspect_task(self.root, self.task)
            path.unlink()
            path.write_bytes(original)

    def test_malformed_record_is_not_treated_as_missing(self):
        self.run_engine('standards')
        self.record().write_text('[]')
        with self.assertRaisesRegex(DeliveryError, 'must be an object'):
            inspect_task(self.root, self.task)

    def test_cli_inspect_is_additive_to_historical_status(self):
        self.run_engine()
        (self.root / 'result.txt').write_text('drifted')
        task_path = self.root / '.delivery/task.json'
        task_path.write_text(json.dumps(self.task))
        env = {**os.environ, 'PYTHONPATH': str(Path(__file__).resolve().parents[2] / 'src')}
        def cli(action):
            result = subprocess.run([sys.executable, '-m', 'offmenu.delivery', '--root',
                                     str(self.root), action, str(task_path)],
                                    env=env, capture_output=True, text=True, timeout=10)
            self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
            return json.loads(result.stdout)
        before = self.snapshot()
        self.assertEqual(cli('status')['status'], 'accepted')
        result = cli('inspect')
        self.assertFalse(result['outputs_match'])
        self.assertEqual(result['recorded_status'], 'accepted')
        self.assertEqual(before, self.snapshot())


class NativeObservationTests(unittest.TestCase):
    def setUp(self):
        from native_harness_contract import fingerprint, load_release_policy
        self.policy = load_release_policy(Path(__file__).resolve().parents[2]
                                          / 'config/delivery-release-policy.json')
        self.receipt = dict(origin='native-coding', attempt='attempt-1', lease='lease-1',
                            source_head='b' * 40, requested_model='requested-model',
                            requested_effort='medium', provider_route='codex-chatgpt',
                            resolved_model='actual-model', resolution_status='observed',
                            turn_completed=True, declared_resources={'cpu_millis': 1000},
                            observed_resources={'peak_rss_bytes': 0, 'peak_processes': 0},
                            resource_sample_count=0, prompt='PRIVATE', cost_usd=0)
        raw = json.dumps(self.receipt).encode()
        self.ref = dict(path='.delivery/original/receipt.json',
                        sha256=hashlib.sha256(raw).hexdigest())
        self.value = dict(version=1, kind='delivery-handoff-v1',
                          issue_id='12345678-1234-1234-1234-123456789abc',
                          project_id='ffb6c7d9-4eff-46eb-a805-99f0cc2edfa0', owner='owner',
                          origin=dict(kind='native-coding-v1', evidence=self.ref),
                          source=dict(repository='maldous/offmenu', branch='feature/fixture',
                                      base='b' * 40, head='c' * 40, tree='d' * 40,
                                      target='develop', policy_sha256=fingerprint(self.policy)),
                          outputs=[], evidence=[self.ref],
                          attempt=dict(id='attempt-1', lease_id='lease-1', admission=self.ref))

    def project(self, receipt=False):
        raw = json.dumps(self.receipt).encode() if receipt else None
        return project_native_handoff(self.value, self.policy, native_receipt_bytes=raw)

    def pin_receipt(self):
        self.ref['sha256'] = hashlib.sha256(json.dumps(self.receipt).encode()).hexdigest()

    def test_missing_facts_remain_unknown_without_following_references(self):
        before = copy.deepcopy(self.value)
        with patch.object(Path, 'open', side_effect=AssertionError('no evidence I/O')):
            result = self.project()
        self.assertEqual(before, self.value)
        self.assertEqual(result['next_pickup']['status'], 'unknown')
        self.assertIsNone(result['cost_usd'])
        self.assertIsNone(result['execution']['requested']['model'])
        self.assertIsNone(result['execution']['observed']['model'])
        self.assertEqual(result['source_acceptance']['integration'], 'unknown')
        self.assertEqual(result['runtime_readback'], 'unknown')
        self.assertEqual(result['effect']['status'], 'unknown')
        self.assertFalse(result['references_verified'])
        result['origin']['evidence']['path'] = 'changed'
        self.assertEqual(self.value, before)

    def test_pinned_native_requests_and_actual_resolution_are_separate(self):
        result = self.project(receipt=True)
        execution = result['execution']
        self.assertEqual(execution['requested']['model'], 'requested-model')
        self.assertEqual(execution['observed']['model'], 'actual-model')
        self.assertEqual(execution['declared_resources']['cpu_millis'], 1000)
        self.assertIsNone(execution['sampled_resources']['peak_rss_bytes'])
        self.assertIsNone(result['cost_usd'])
        self.assertNotIn('PRIVATE', json.dumps(result))
        self.receipt['resolution_status'] = 'unknown'
        self.pin_receipt()
        self.assertIsNone(self.project(True)['execution']['observed']['model'])
        self.receipt['resolution_status'] = 'observed'
        self.receipt['resource_sample_count'] = 1
        self.pin_receipt()
        self.assertEqual(self.project(True)['execution']['sampled_resources']['peak_rss_bytes'], 0)

    def test_changed_pin_and_original_identity_fail_closed(self):
        self.receipt['lease'] = 'other'
        with self.assertRaisesRegex(DeliveryError, 'pin mismatch'):
            self.project(True)
        self.pin_receipt()
        with self.assertRaisesRegex(DeliveryError, 'identity mismatch'):
            self.project(True)
        for field in ('attempt', 'source_head', 'origin'):
            self.setUp()
            self.receipt[field] = 'other'
            self.pin_receipt()
            with self.subTest(field=field), self.assertRaises(DeliveryError):
                self.project(True)

    def test_unknown_effect_routes_to_same_owner_record_without_retry(self):
        self.value['operation'] = dict(id='original-operation', backend='windmill',
            job_id='original-job', status='unknown', command_sha256='1' * 64,
            runner_sha256='2' * 64, policy_sha256='3' * 64, receipt=self.ref)
        self.value['effect'] = dict(operation_id='original-operation', status='unknown')
        result = self.project()
        self.assertTrue(result['recovery']['reconciliation_required'])
        self.assertEqual(result['recovery']['operation_id'], 'original-operation')
        self.assertEqual(result['recovery']['owner_record'], self.ref)
        self.value['operation']['status'] = 'succeeded'
        self.value['effect']['status'] = 'verified'
        result = self.project()
        self.assertFalse(result['recovery']['reconciliation_required'])
        self.assertEqual(result['source_acceptance']['integration'], 'unknown')
        self.assertEqual(result['next_pickup']['status'], 'unknown')

    def test_review_and_noncoding_origin_do_not_fabricate_execution_or_integration(self):
        from native_harness_contract import fingerprint
        self.value['origin']['kind'] = 'reviewed-source-v1'
        del self.value['attempt']
        self.value['review'] = dict(reviewer='independent', author='owner', verdict='accept',
            source_sha256=fingerprint(self.value['source']),
            outputs_sha256=fingerprint(self.value['outputs']), evidence=self.ref)
        result = self.project()
        self.assertIsNone(result['attempt'])
        self.assertEqual(result['source_acceptance']['recorded_review']['verdict'], 'accept')
        self.assertEqual(result['source_acceptance']['integration'], 'unknown')
        self.assertIsNone(result['execution']['observed']['model'])
        with self.assertRaises(DeliveryError):
            self.project(True)
        self.value['source']['head'] = 'e' * 40
        with self.assertRaisesRegex(ValueError, 'review_source'):
            self.project()

    def test_cli_reads_explicit_files_only_and_does_not_create_runtime(self):
        import tempfile
        tool = Path(__file__).resolve().parents[2] / 'tools/delivery/native_observations.py'
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            handoff = root / 'handoff.json'
            receipt = root / 'receipt.json'
            handoff.write_text(json.dumps(self.value))
            receipt.write_text(json.dumps(self.receipt))
            before = {p.name: p.read_bytes() for p in root.iterdir()}
            policy = tool.parents[2] / 'config/delivery-release-policy.json'
            command = [sys.executable, str(tool), str(handoff), '--policy', str(policy),
                       '--native-receipt', str(receipt)]
            env = {**os.environ, 'PYTHONPATH': os.pathsep.join((
                str(tool.parents[2] / 'src'), str(tool.parent)))}
            result = subprocess.run(command, cwd=root, env=env,
                                    capture_output=True, text=True, timeout=10)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(json.loads(result.stdout)['authority'], 'observation_only')
            self.assertEqual(before, {p.name: p.read_bytes() for p in root.iterdir()})
            receipt.write_bytes(b'PRIVATE invalid JSON')
            result = subprocess.run(command, cwd=root, env=env,
                                    capture_output=True, text=True, timeout=10)
            self.assertEqual(result.returncode, 2)
            self.assertEqual(result.stderr, 'native observation input rejected\n')
            self.assertEqual(result.stdout, '')
