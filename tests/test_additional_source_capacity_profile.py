import importlib.util
from pathlib import Path
import unittest
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('capacity_dispatch_tests', ROOT / 'scripts/dispatch-foo-job.py')
jobs = importlib.util.module_from_spec(spec)
spec.loader.exec_module(jobs)


class CapacityProfileTests(unittest.TestCase):
    def setUp(self):
        jobs.CANCEL_EVENT.clear()

    def request(self):
        return {'schemaVersion': 1, 'jobId': 'additional-source-capacity-test-001', 'profile': 'additional-source-capacity'}

    def child(self, status='complete', exit_code=0):
        return {'status': 'passed' if exit_code == 0 else 'failed', 'exitCode': exit_code,
                'durationSeconds': 0.01, 'evidence': {'additionalSourceCapacity': {'status': status}}}

    def test_exact_fixed_graph(self):
        self.assertEqual(jobs.parse_request(jobs.canonical(self.request())), self.request())
        steps = jobs.profile_steps('additional-source-capacity', ROOT)
        self.assertEqual([s[:2] for s in steps], [('readiness', []),
            ('additional-source-capacity-tests', ['readiness']),
            ('additional-source-capacity', ['readiness', 'additional-source-capacity-tests'])])
        self.assertEqual(steps[1][2], [jobs.sys.executable, '-I', '-B', '-m', 'unittest', 'discover',
                                     '-s', 'manual-action/tests', '-p', 'test_fetch_capacity.py'])
        self.assertEqual(steps[2][2], [jobs.sys.executable, '-I', '-B', 'manual-action/fetch_capacity.py'])
        self.assertNotIn('fetch_sources.py', repr(steps))
        for extra in ({'path': '/home/user'}, {'command': 'shell'}, {'ref': 'arbitrary'}, {'acquire': True}):
            with self.assertRaises(jobs.JobError):
                jobs.parse_request(jobs.canonical(self.request() | extra))

    def test_capacity_timeout_and_status_binding(self):
        for status, exit_code, expected in [('complete', 0, 'passed'), ('blocked', 2, 'blocked'),
            ('complete', 2, 'failed'), ('blocked', 0, 'failed'), ('invalid', 0, 'failed'),
            (None, 0, 'failed'), ('partial', 2, 'failed')]:
            with self.subTest(status=status, exit_code=exit_code), patch.object(jobs, 'run_child', return_value=self.child(status, exit_code)) as run:
                result = jobs.run_step('additional-source-capacity', ['fixed'], ROOT)
                run.assert_called_once_with(['fixed'], ROOT, timeout=30)
                self.assertEqual(result['status'], expected)
                if expected == 'failed':
                    self.assertEqual(result['exitCode'], 3)

    def test_report_limits_unchanged_and_no_acquisition_claim(self):
        with patch.object(jobs, 'run_child', return_value=self.child()):
            report = jobs.run_profile(self.request(), 'a' * 40, ROOT, '123', '1')
        self.assertEqual(report['status'], 'passed')
        self.assertEqual(report['diagnosticScope'], 'fixed-runner-output-capacity-only')
        for key in ('sourceContentsUploaded', 'databaseWritesEnabled', 'networkAcquisitionEnabled',
                    'existingIngestAccessEnabled', 'homeFilesystemObserved', 'corpusAcceptanceEstablished'):
            self.assertIs(report[key], False)
        self.assertEqual(report['maximumParallelChildren'], 1)
        self.assertEqual(jobs.MAX_REQUEST, 1024)
        self.assertEqual(jobs.MAX_REPORT, 32768)
        self.assertEqual(jobs.MAX_DIAGNOSTIC_EVIDENCE, 12 * 1024)

    def test_tests_failure_prevents_capacity_process(self):
        def child(command, code, **kwargs):
            return self.child(None, 1) if 'unittest' in command else self.child()
        with patch.object(jobs, 'run_child', side_effect=child) as run:
            report = jobs.run_profile(self.request(), 'a' * 40, ROOT, '123', '1')
        self.assertEqual(run.call_count, 2)
        self.assertEqual(report['steps'][-1]['status'], 'skipped')

    def test_unknown_or_contradictory_schema_is_fail_closed(self):
        raw = jobs.canonical({'schemaVersion': 'offmenu-additional-source-capacity/1',
                              'status': 'complete', 'homeFilesystemObserved': True})
        evidence = jobs.safe_evidence(raw)
        self.assertNotIn('additionalSourceCapacity', evidence)
        self.assertEqual(evidence['diagnosticEvidenceError'], 'invalid-diagnostic-schema')

    def test_actual_capacity_sanitizer_binding_does_not_claim_acquisition(self):
        row = {'status': 'observed', 'errorCode': 'none', 'totalBytes': 21475098624,
               'freeBytes': 10737549305, 'availableBytes': 10737549305,
               'totalInodes': 1000, 'freeInodes': 500, 'availableInodes': 490,
               'initialDeficitBytes': 7, 'readOnly': False, 'reserveSatisfied': False}
        report = {'schema': 'offmenu-additional-source-capacity/1', 'schemaVersion': 'offmenu-additional-source-capacity/1',
                  'executionHost': 'Foo', 'status': 'complete', 'scope': 'runner-outputs-only',
                  'observedAt': '2026-10-22T00:00:00Z', 'reserveBytes': 10737418240,
                  'safetyBufferBytes': 131072, 'initialMinimumAvailableBytes': 10737549312,
                  'outputs': dict(row), 'sourceCache': dict(row), 'sameFilesystem': True,
                  'homeFilesystemObserved': False, 'acquisitions': 0, 'downloads': 0, 'sourceWrites': 0,
                  'dbWrites': 0, 'networkRequests': 0, 'directoryListings': 0, 'fileBodyReads': 0}
        evidence = jobs.safe_evidence(jobs.canonical(report))
        self.assertEqual(evidence['additionalSourceCapacity'], report)
        self.assertEqual(evidence['additionalSourceCapacity']['sourceCache']['initialDeficitBytes'], 7)
        report['sourceCache']['path'] = '/private'
        evidence = jobs.safe_evidence(jobs.canonical(report))
        self.assertNotIn('additionalSourceCapacity', evidence)
        self.assertNotIn('/private', jobs.canonical(evidence).decode())


if __name__ == '__main__':
    unittest.main()
