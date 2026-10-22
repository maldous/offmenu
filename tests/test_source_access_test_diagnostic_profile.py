import importlib.util
from pathlib import Path
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('access_tests_dispatch', ROOT / 'scripts/dispatch-foo-job.py')
jobs = importlib.util.module_from_spec(spec)
spec.loader.exec_module(jobs)


class AccessTestDiagnosticProfileTests(unittest.TestCase):
    def setUp(self):
        jobs.CANCEL_EVENT.clear()

    def request(self):
        return {'schemaVersion': 1, 'jobId': 'source-access-test-diagnostic-test-001', 'profile': 'source-access-test-diagnostic'}

    def child(self, status='passed', code=0):
        return {'status': 'passed' if code == 0 else 'failed', 'exitCode': code,
                'durationSeconds': 0.1, 'evidence': {'sourceAccessTests': {'status': status}}}

    def test_exact_test_only_graph_never_applies(self):
        self.assertEqual(jobs.parse_request(jobs.canonical(self.request())), self.request())
        steps = jobs.profile_steps('source-access-test-diagnostic', ROOT)
        self.assertEqual([s[:2] for s in steps], [('readiness', []),
            ('source-access-test-reporter-tests', ['readiness']),
            ('source-access-test-diagnostic', ['readiness', 'source-access-test-reporter-tests'])])
        self.assertEqual(steps[1][2], [jobs.sys.executable, '-I', '-B', '-m', 'unittest', 'discover',
            '-s', 'manual-action/tests', '-p', 'test_check_source_access_handoff_tests.py'])
        self.assertEqual(steps[2][2], [jobs.sys.executable, '-I', '-B', 'manual-action/check_source_access_handoff_tests.py'])
        for forbidden in ('--apply', 'grant_acquired_read_access.py', 'fetch_sources.py', 'ingest', 'sudo', 'bash'):
            self.assertNotIn(forbidden, repr(steps))
        for extra in ({'command': 'shell'}, {'test': 'arbitrary'}, {'path': '/home/user'}, {'apply': True}):
            with self.assertRaises(jobs.JobError):
                jobs.parse_request(jobs.canonical(self.request() | extra))

    def test_report_exit_binding_and_existing_timeout_unchanged(self):
        for status, code, expected_code in [('passed', 0, 0), ('failed', 1, 1),
                ('failed', 0, 3), ('passed', 1, 3), (None, 0, 3), ('complete', 0, 3)]:
            with self.subTest(status=status, code=code), patch.object(jobs, 'run_child', return_value=self.child(status, code)) as run:
                result = jobs.run_step('source-access-test-diagnostic', ['fixed'], ROOT)
                run.assert_called_once_with(['fixed'], ROOT)
                self.assertEqual(result['exitCode'], expected_code)
        for status, code in [('timeout', 124), ('cancelled', 130), ('output-limit', 125)]:
            child = self.child(None, code); child['status'] = status
            with patch.object(jobs, 'run_child', return_value=child):
                result = jobs.run_step('source-access-test-diagnostic', ['fixed'], ROOT)
                self.assertEqual((result['status'], result['exitCode']), (status, code))

    def test_reporter_tests_gate_fixed_diagnostic(self):
        with patch.object(jobs, 'run_child', side_effect=[self.child(), self.child('failed', 1)]) as run:
            report = jobs.run_profile(self.request(), 'a' * 40, ROOT, '123', '1')
        self.assertEqual(run.call_count, 2)
        self.assertEqual(report['steps'][-1]['status'], 'skipped')

    def test_no_access_or_source_work_claim(self):
        with patch.object(jobs, 'run_child', return_value=self.child()):
            report = jobs.run_profile(self.request(), 'a' * 40, ROOT, '123', '1')
        self.assertEqual(report['status'], 'passed')
        self.assertEqual(report['diagnosticScope'], 'synthetic-handoff-tests-only')
        self.assertEqual(report['maximumParallelChildren'], 1)
        for key in ('aclHandoffEnabled', 'sourceContentsUploaded', 'databaseWritesEnabled',
                    'networkAcquisitionEnabled', 'existingIngestAccessEnabled', 'corpusAcceptanceEstablished'):
            self.assertIs(report[key], False)

    def test_incomplete_diagnostic_cannot_claim_success(self):
        evidence = jobs.safe_evidence(jobs.canonical({'schemaVersion': 'offmenu-source-access-tests/1',
            'status': 'passed', 'private_path': '/private/never-upload'}))
        self.assertNotIn('sourceAccessTests', evidence)
        self.assertEqual(evidence['diagnosticEvidenceError'], 'invalid-diagnostic-schema')
        self.assertNotIn('/private', repr(evidence))

    def test_real_sanitizer_projects_complete_fixed_report_only(self):
        value = {'schemaVersion': 'offmenu-source-access-tests/1', 'status': 'passed',
                 'reporter_mode': 'original_cli', 'child_exit_code': 0, 'unattributed_skips': 0,
                 'capture_status': 'completed', 'failure_events': 0, 'error_events': 0,
                 'expected_test_suite_sha256': '3f418e0e27be6c21c63d3d33f4750e18aed85fe572ec91b6ca58c0e7d50a5520',
                 'suite_identity_verified': True,
                 'tests_expected': 38, 'tests_run': 38, 'failures': 0, 'errors': 0, 'skipped': 0,
                 'failed_test_ids': [], 'error_test_ids': [], 'skipped_test_ids': [], 'error_code': 'none'}
        evidence = jobs.safe_evidence(jobs.canonical(value | {'private_stderr': '/private/raw'}))
        self.assertEqual(evidence['sourceAccessTests'], value)
        self.assertNotIn('/private', repr(evidence))
        for bad in ({'tests_run': 37}, {'tests_expected': 37}, {'failures': 1},
                    {'failed_test_ids': ['arbitrary.private.test']}, {'tests_run': True},
                    {'expected_test_suite_sha256': 'a' * 64}, {'suite_identity_verified': False},
                    {'reporter_mode': 'other'}, {'child_exit_code': 1}, {'child_exit_code': True},
                    {'unattributed_skips': 1}, {'capture_status': 'timeout'}, {'failure_events': 1}):
            with self.subTest(bad=bad):
                rejected = jobs.safe_evidence(jobs.canonical(value | bad))
                self.assertNotIn('sourceAccessTests', rejected)
                self.assertEqual(rejected['diagnosticEvidenceError'], 'invalid-diagnostic-schema')


if __name__ == '__main__':
    unittest.main()
