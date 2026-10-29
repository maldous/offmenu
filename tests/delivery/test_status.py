"""Read-only evidence view across actual local LangGraph execution boundaries."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

from test_engine import DeliveryFixture
from offmenu.delivery.engine import DeliveryError, writer
from offmenu.delivery.status import inspect_task


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
