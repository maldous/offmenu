import contextlib
import importlib.util
import json
import os
from pathlib import Path
import tempfile
import threading
import time
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('delivery_dispatch', ROOT / 'tools/operations/dispatch_foo_job.py')
jobs = importlib.util.module_from_spec(spec)
spec.loader.exec_module(jobs)


class DeliveryDiagnosticsTests(unittest.TestCase):
    def setUp(self):
        jobs.CANCEL_EVENT.clear()

    def tearDown(self):
        jobs.CANCEL_EVENT.clear()

    def request(self, job_id='delivery-diagnostics-test-001'):
        return {'schemaVersion': 1, 'jobId': job_id, 'profile': 'delivery-diagnostics'}

    def result(self, status='passed', exit_code=0, evidence=None):
        return {'status': status, 'exitCode': exit_code, 'durationSeconds': 0.01, 'evidence': evidence or {}}

    def complete_child(self, command, code, timeout=240):
        if 'tools/operations/offmenu_ledger_audit.py' in command:
            return self.result(evidence={'ledgerAudit': {'schemaVersion': 'offmenu-ledger-structural-audit/1', 'status': 'complete'}})
        if 'tools/operations/inspect_selected_datasets.py' in command:
            return self.result('failed', 2, {'selectedDataInventory': {'schemaVersion': 'offmenu-selected-data-inventory/1', 'status': 'incomplete'}})
        return self.result(evidence={'resultAction': 'verified-no-op'})

    def report(self, fake=None):
        with patch.object(jobs, 'run_child', side_effect=fake or self.complete_child):
            return jobs.run_profile(self.request(), 'a' * 40, ROOT, '123', '1')

    def test_new_profile_is_exact_allowlist_and_fixed_graph(self):
        self.assertEqual(jobs.parse_request(json.dumps(self.request()).encode()), self.request())
        steps = jobs.profile_steps('delivery-diagnostics', ROOT)
        graph = {step_id: deps for step_id, deps, _ in steps}
        self.assertEqual(graph['ledger-audit'], ['readiness', 'ledger-tests'])
        self.assertEqual(graph['selected-data-inventory'], ['readiness', 'dataset-tests'])
        self.assertEqual(graph['replay-idempotency'], ['offline-replay'])
        self.assertEqual(len(steps), 9)
        self.assertNotIn('selected-data-inventory', graph['ledger-audit'])

    def test_missing_dataset_does_not_suppress_ledger_or_replay(self):
        report = self.report()
        steps = {s['stepId']: s for s in report['steps']}
        self.assertEqual(report['status'], 'incomplete')
        self.assertEqual(steps['selected-data-inventory']['status'], 'blocked')
        self.assertEqual(steps['ledger-audit']['status'], 'passed')
        self.assertEqual(steps['replay-idempotency']['status'], 'passed')
        self.assertFalse(report['corpusAcceptanceEstablished'])
        self.assertEqual(report['manifestCommitSha'], '8c25c6d76088c958d17f7adc4a3c0af7aab5c298')

    def test_actual_failure_is_never_relabelled_incomplete(self):
        def fake(command, code, timeout=240):
            if 'tools/operations/offmenu_ledger_audit.py' in command:
                return self.result('failed', 1, {'ledgerAudit': {'status': 'failed'}})
            return self.complete_child(command, code, timeout)
        report = self.report(fake)
        self.assertEqual(report['status'], 'failed')
        self.assertEqual(next(x for x in report['steps'] if x['stepId'] == 'selected-data-inventory')['status'], 'blocked')

    def test_empty_or_invalid_evidence_never_claims_diagnostic_success(self):
        for step in ('ledger-audit', 'selected-data-inventory'):
            with self.subTest(step=step), patch.object(jobs, 'run_child', return_value=self.result()):
                result = jobs.run_step(step, [], ROOT)
                self.assertEqual(result['status'], 'failed')
                self.assertEqual(result['errorCode'], 'diagnostic-result-not-established')
        with patch.object(jobs, 'run_child', return_value=self.result('failed', 2)):
            self.assertEqual(jobs.run_step('selected-data-inventory', [], ROOT)['status'], 'failed')

    def test_parallel_children_never_exceed_two_and_replay_is_serial(self):
        lock = threading.Lock()
        running, peak, active_commands = 0, 0, []
        intervals = []
        def fake(command, code, timeout=240):
            nonlocal running, peak
            with lock:
                running += 1
                peak = max(peak, running)
                active_commands.append(command)
                self.assertLessEqual(sum('replay' in cmd for cmd in active_commands), 1)
            time.sleep(0.025)
            result = self.complete_child(command, code, timeout)
            with lock:
                running -= 1
                active_commands.remove(command)
            return result
        report = self.report(fake)
        self.assertEqual(peak, 2)
        self.assertEqual(report['status'], 'incomplete')

    def test_parallel_cancellation_reaps_running_children_and_skips_pending(self):
        commands = [('first', [], [os.sys.executable, '-c', 'import time; time.sleep(10)']),
                    ('second', [], [os.sys.executable, '-c', 'import time; time.sleep(10)']),
                    ('third', ['first'], [os.sys.executable, '-c', 'raise SystemExit(99)'])]
        timer = threading.Timer(0.1, jobs.CANCEL_EVENT.set)
        with tempfile.TemporaryDirectory() as tmp, patch.object(jobs, 'OUTPUT', Path(tmp)):
            (Path(tmp) / 'tmp').mkdir()
            timer.start()
            try:
                results, cancelled = jobs.parallel_diagnostics(commands, ROOT)
            finally:
                timer.join()
        self.assertTrue(cancelled)
        self.assertEqual(results['first']['status'], 'cancelled')
        self.assertEqual(results['second']['status'], 'cancelled')
        self.assertEqual(results['third']['status'], 'skipped')

    def test_incomplete_receipt_reuses_identity_without_execution(self):
        with tempfile.TemporaryDirectory() as tmp, patch.object(jobs, 'OUTPUT', Path(tmp)):
            with patch.object(jobs, 'run_profile', return_value={'status': 'incomplete', 'steps': []}) as run:
                jobs.execute(self.request(), 'a' * 40, ROOT, '123', '1')
                report = jobs.execute(self.request(), 'a' * 40, ROOT, '124', '1')
                self.assertEqual(run.call_count, 1)
            self.assertEqual(report['delivery'], 'existing-receipt-no-execution')
            with self.assertRaises(jobs.JobError):
                jobs.execute(self.request(), 'b' * 40, ROOT, '125', '1')

    def test_maximum_evidence_budgets_fit_final_report(self):
        def fake(command, code, timeout=240):
            result = self.complete_child(command, code, timeout)
            for key in ('ledgerAudit', 'selectedDataInventory'):
                if key in result['evidence']:
                    report = result['evidence'][key]
                    report['budgetFixture'] = 'x' * (jobs.MAX_DIAGNOSTIC_EVIDENCE - len(jobs.canonical(report)) - 30)
                    self.assertLessEqual(len(jobs.canonical(report)), jobs.MAX_DIAGNOSTIC_EVIDENCE)
            return result
        report = self.report(fake)
        report['requestIdentity'] = 'a' * 64
        report['delivery'] = 'existing-receipt-no-execution'
        self.assertLess(len(jobs.canonical(report)) + 1, jobs.MAX_REPORT)

    def test_duplicate_or_nonfinite_child_evidence_is_discarded(self):
        for raw in (b'{"status":"complete","status":"failed"}', b'{"status":"complete","value":NaN}', b'{"status":"complete","value":Infinity}', b'{"status":"complete","value":1e9999}', b'{"status":"complete","value":-1e9999}'):
            self.assertEqual(set(jobs.safe_evidence(raw)), {'stdoutBytes', 'stdoutSha256'})

    def test_workflow_only_input_checkout_can_continue_after_failure(self):
        workflow = (ROOT / '.github/workflows/foo-runner.yml').read_text()
        self.assertEqual(workflow.count('continue-on-error: true'), 1)
        self.assertIn('path: ledger-source', workflow)
        self.assertIn('ref: 8c25c6d76088c958d17f7adc4a3c0af7aab5c298', workflow)
        self.assertIn('sparse-checkout-cone-mode: false', workflow)
        self.assertNotIn('schedule:', workflow)
        self.assertNotIn('pull_request:', workflow)
        self.assertIn("github.actor_id == '6347545'", workflow)
        self.assertEqual(workflow.count('persist-credentials: false'), 3)

    def test_live_smoke_receipt_remains_unchanged_and_honestly_scoped(self):
        receipt = json.loads((ROOT / 'tests/fixtures/foo-runner/prior-smoke-receipt.json').read_text())
        report = receipt['report']
        self.assertEqual(report['githubRunId'], '39043749665')
        self.assertEqual(report['trustedCodeSha'], '5722ca925e0c8543a8dc58f40d94e7f1768f475b')
        self.assertEqual(report['status'], 'passed')
        inventory = next(s for s in report['steps'] if s['stepId'] == 'inventory')['evidence']
        self.assertFalse(inventory['coverageEstablished'])
        self.assertFalse(inventory['assetHashesVerified'])


    def test_real_sanitizers_reject_or_drop_unrecognized_content(self):
        spec = importlib.util.spec_from_file_location('dataset_boundary', ROOT / 'tools/operations/inspect_selected_datasets.py')
        data = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(data)
        with tempfile.TemporaryDirectory() as tmp:
            report = data.inspect(tmp)
        report['private'] = 'DO-NOT-EMIT-SECRET'
        report['assets']['NO_EN_FOODS']['url'] = 'https://private.invalid/DO-NOT-EMIT-SECRET'
        evidence = jobs.safe_evidence(json.dumps(report).encode())
        self.assertIn('selectedDataInventory', evidence)
        self.assertNotIn('DO-NOT-EMIT-SECRET', json.dumps(evidence))
        report['assets']['NO_EN_FOODS']['status'] = 'DO-NOT-EMIT-SECRET'
        evidence = jobs.safe_evidence(json.dumps(report).encode())
        self.assertNotIn('selectedDataInventory', evidence)
        self.assertEqual(evidence['diagnosticEvidenceError'], 'invalid-diagnostic-schema')
        self.assertNotIn('DO-NOT-EMIT-SECRET', json.dumps(evidence))
        evidence = jobs.safe_evidence(json.dumps({'schemaVersion':'offmenu-ledger-structural-audit/1', 'status':'complete', 'private':'DO-NOT-EMIT-SECRET'}).encode())
        self.assertNotIn('ledgerAudit', evidence)
        self.assertEqual(evidence['diagnosticEvidenceError'], 'invalid-diagnostic-schema')

    def test_dispatcher_kernel_lock_refuses_concurrent_coordinator(self):
        with tempfile.TemporaryDirectory() as tmp, patch.object(jobs, 'OUTPUT', Path(tmp)):
            lock_dir = Path(tmp) / 'locks'
            lock_dir.mkdir()
            with (lock_dir / 'dispatcher.lock').open('w') as lock:
                jobs.fcntl.flock(lock, jobs.fcntl.LOCK_EX | jobs.fcntl.LOCK_NB)
                with self.assertRaisesRegex(jobs.JobError, 'another-job-is-running-retry-later'):
                    jobs.execute(self.request(), 'a' * 40, ROOT, '123', '1')


if __name__ == '__main__':
    unittest.main()
