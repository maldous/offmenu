import copy
import importlib.util
from pathlib import Path
import unittest
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('handoff_dispatch_tests', ROOT / 'scripts/dispatch-foo-job.py')
jobs = importlib.util.module_from_spec(spec)
spec.loader.exec_module(jobs)


class HandoffProfileTests(unittest.TestCase):
    def setUp(self):
        jobs.CANCEL_EVENT.clear()

    def request(self):
        return {'schemaVersion': 1, 'jobId': 'public-source-read-handoff-test-001', 'profile': 'public-source-read-handoff'}

    def child(self, status='complete', exit_code=0):
        return {'status': 'passed' if exit_code == 0 else 'failed', 'exitCode': exit_code,
                'durationSeconds': 0.01, 'evidence': {'sourceAccessHandoff': {'status': status, 'mode': 'apply'}}}

    def test_exact_fixed_graph_and_apply_command(self):
        self.assertEqual(jobs.parse_request(jobs.canonical(self.request())), self.request())
        steps = jobs.profile_steps('public-source-read-handoff', ROOT)
        self.assertEqual([s[:2] for s in steps], [('readiness', []),
            ('public-source-read-handoff-tests', ['readiness']),
            ('public-source-read-handoff', ['readiness', 'public-source-read-handoff-tests'])])
        self.assertEqual(steps[1][2], [jobs.sys.executable, '-I', '-B', '-m', 'unittest', 'discover',
                                     '-s', 'manual-action/tests', '-p', 'test_grant_acquired_read_access.py'])
        self.assertEqual(steps[2][2], [jobs.sys.executable, '-I', '-B', 'manual-action/grant_acquired_read_access.py', '--apply'])
        for forbidden in ('fetch_sources.py', 'ingest', 'chmod', 'sudo', 'bash', 'setfacl'):
            self.assertNotIn(forbidden, repr(steps))
        for extra in ({'path': '/home/user'}, {'command': 'shell'}, {'ref': 'arbitrary'}, {'targetUser': 'other'}, {'uid': 0}, {'apply': False}):
            with self.assertRaises(jobs.JobError):
                jobs.parse_request(jobs.canonical(self.request() | extra))

    def test_bounded_child_and_status_binding(self):
        for status, exit_code, expected in [('complete', 0, 'passed'), ('blocked', 2, 'blocked'),
            ('partial', 2, 'failed'), ('failed', 2, 'failed'), ('complete', 2, 'failed'),
            ('blocked', 0, 'failed'), ('invalid', 0, 'failed'), (None, 0, 'failed'), ('partial', 0, 'failed')]:
            with self.subTest(status=status, exit_code=exit_code), patch.object(jobs, 'run_child', return_value=self.child(status, exit_code)) as run:
                result = jobs.run_step('public-source-read-handoff', ['fixed'], ROOT)
                run.assert_called_once_with(['fixed'], ROOT)
                self.assertEqual(result['status'], expected)
        for status, code in [('timeout', 124), ('cancelled', 130), ('output-limit', 125)]:
            child = self.child(None, code);child['status'] = status
            with patch.object(jobs, 'run_child', return_value=child):
                result = jobs.run_step('public-source-read-handoff', ['fixed'], ROOT)
                self.assertEqual((result['status'], result['exitCode']), (status, code))

    def test_no_ingestion_acquisition_or_corpus_claim(self):
        with patch.object(jobs, 'run_child', return_value=self.child()):
            report = jobs.run_profile(self.request(), 'a' * 40, ROOT, '123', '1')
        self.assertEqual(report['status'], 'passed')
        self.assertEqual(report['diagnosticScope'], 'exact-public-artifact-read-access-handoff')
        for key in ('sourceContentsUploaded', 'databaseWritesEnabled', 'networkAcquisitionEnabled',
                    'existingIngestAccessEnabled', 'corpusAcceptanceEstablished'):
            self.assertIs(report[key], False)
        self.assertIs(report['aclHandoffEnabled'], True)
        self.assertEqual(report['maximumParallelChildren'], 1)
        self.assertEqual(jobs.MAX_REQUEST, 1024)
        self.assertEqual(jobs.MAX_REPORT, 32768)
        self.assertEqual(jobs.MAX_DIAGNOSTIC_EVIDENCE, 12 * 1024)

    def test_complete_plan_is_not_completed_acl_application(self):
        for mode in ('plan', None, 'unrecognized'):
            child = self.child()
            child['evidence']['sourceAccessHandoff']['mode'] = mode
            with self.subTest(mode=mode), patch.object(jobs, 'run_child', return_value=child):
                result = jobs.run_step('public-source-read-handoff', ['fixed'], ROOT)
                self.assertEqual((result['status'], result['exitCode']), ('failed', 3))

    def test_fixture_failure_never_launches_acl_application(self):
        def child(command, code, **kwargs):
            return self.child(None, 1) if 'unittest' in command else self.child()
        with patch.object(jobs, 'run_child', side_effect=child) as run:
            report = jobs.run_profile(self.request(), 'a' * 40, ROOT, '123', '1')
        self.assertEqual(run.call_count, 2)
        self.assertEqual(report['steps'][-1]['status'], 'skipped')

    def test_partial_acl_or_rollback_failure_is_never_success(self):
        def child(command, code, **kwargs):
            return self.child('partial', 2) if '--apply' in command else self.child()
        with patch.object(jobs, 'run_child', side_effect=child):
            report = jobs.run_profile(self.request(), 'a' * 40, ROOT, '123', '1')
        self.assertEqual(report['status'], 'failed')
        self.assertEqual(report['steps'][-1]['status'], 'failed')

    def test_unknown_or_incomplete_schema_is_fail_closed(self):
        raw = jobs.canonical({'schemaVersion': 'offmenu-source-access-handoff/1',
                              'status': 'complete', 'arbitraryPath': '/private'})
        evidence = jobs.safe_evidence(raw)
        self.assertNotIn('sourceAccessHandoff', evidence)
        self.assertEqual(evidence['diagnosticEvidenceError'], 'invalid-diagnostic-schema')
        self.assertNotIn('/private', jobs.canonical(evidence).decode())

    def completed_fixture(self):
        return {'schemaVersion': 'offmenu-source-access-handoff/1', 'status': 'complete',
                'mode': 'apply', 'target_account': 'user',
                'manifest_sha256': '637bfeba82177e44a87080ca6be217c475cc02917848730762d9f1949e69ebec',
                'scope_plan_sha256': 'c9b2a39a54b5131b207c224fbfdea5803f6f08154688925f541ebc12947411e9',
                'outcome': 'applied', 'error_code': 'none', 'source_artifacts': 50,
                'provenance_receipts': 50, 'traversal_directories': 9, 'changed_acls': 109,
                'source_bytes_verified': 108318002, 'source_artifacts_verified': 50,
                'provenance_receipts_verified': 50, 'traversal_directories_verified': 9,
                'read_only_scope_verified': True, 'other_effective_permissions_preserved': True,
                'rollback_complete': False, 'raw_data_uploaded': False,
                'source_bytes_modified': False, 'default_acls_modified': False}

    def test_actual_sanitizer_projection_binds_complete_scope(self):
        value = self.completed_fixture()
        value['private_snapshot_path'] = '/private/never-publish'
        value['raw_acl'] = 'DO_NOT_PUBLISH'
        evidence = jobs.safe_evidence(jobs.canonical(value))
        self.assertEqual(evidence['sourceAccessHandoff'], self.completed_fixture())
        self.assertNotIn('/private', jobs.canonical(evidence).decode())
        self.assertNotIn('DO_NOT_PUBLISH', jobs.canonical(evidence).decode())

    def test_actual_sanitizer_rejects_success_boundary_contradictions(self):
        for change in [{'target_account': 'other'}, {'manifest_sha256': 'b' * 64}, {'scope_plan_sha256': 'c' * 64},
                       {'source_artifacts': 51}, {'provenance_receipts': 49},
                       {'traversal_directories': 10}, {'changed_acls': 110},
                       {'changed_acls': True}, {'source_bytes_verified': 0},
                       {'raw_data_uploaded': 'true'}, {'source_bytes_modified': True},
                       {'default_acls_modified': 'false'}, {'mode': 'plan'},
                       {'read_only_scope_verified': False}]:
            value = self.completed_fixture() | change
            with self.subTest(change=change):
                evidence = jobs.safe_evidence(jobs.canonical(value))
                self.assertNotIn('sourceAccessHandoff', evidence)
                self.assertEqual(evidence['diagnosticEvidenceError'], 'invalid-diagnostic-schema')
        for key in ('target_account', 'manifest_sha256', 'scope_plan_sha256', 'raw_data_uploaded',
                    'source_bytes_modified', 'default_acls_modified'):
            value = copy.deepcopy(self.completed_fixture());del value[key]
            with self.subTest(missing=key):
                self.assertNotIn('sourceAccessHandoff', jobs.safe_evidence(jobs.canonical(value)))


if __name__ == '__main__':
    unittest.main()
