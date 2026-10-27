import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import textwrap
import types
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT.parent


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


jobs = load('additional_source_dispatch', ROOT / 'scripts/dispatch-foo-job.py')
# Reviewed legacy graph hashes from execution SHA 24b8bb0fa0eb7c7f6632aade4dcb6d8d9ee49793.
LEGACY_GRAPHS = {'batch-recovery-diagnostic': 'e3f94ff72e137b88951ea5fb5ef0852aa4af1d63ed35fabcac0eccb0fded7efb', 'ciqual-source-native': 'fa6aebf37e2fb380f4a4b5bd6a42e58d9de30d7633be0e9a0b661ca24c483ce4', 'collection-prepare': 'f98139830e2d383201080da9b476f35ffa44ef521dd16130656eb1dcaf3b5cde', 'delivery-diagnostics': 'f3ebaec84986f6926d5579ec4049d6a752ca86297f37023ddac26343a9d9c1b1', 'global-collection': 'caa03437c529290b168b400986c71d2e38dd8b6d425f991e27107bc6ce2925d5', 'global-readiness': '82e827818e4655dbe2c7cb0b39564e3b113a136e4b1f7764a89a905721e066a0', 'inventory': '62666e0b75f08e197f1e10e3c386771accf6b1da2116a883f74af5896b9901aa', 'national-schema-survey': 'e31d9f3637ca4a33115d3187d810e0efc9ea2fd36f86634613460b5fb12f570e', 'offline-reconciliation': '0bb9e2840499da366f35b7a85575fbf3223875f268f1af5c08b3780201e62a92', 'offline-replay': '2c94c62254f168f82455b8ff302f65ac787afae112b7039fba4293fd5b0641a7', 'readiness': 'ad6e9c7b48bfb3493adf27ea397cbd587d67cc0b14e19fc6b30e98cf60be3e19', 'selected-original-batch': '057b1e651b42f8a84b6c23628d0b89900a4e4e0f0b01b7eb77fe5bafea7bf070', 'smoke': '149e0c04ef39617475074eee1f8a004d6175e31ec7138f4ab585a352c8d575fd', 'swiss-private-original': 'e8c82f5a4d0056ec4c7a1a5f924c75b4d3bcc8f810ca1d803736afad50aa9039', 'zenodo-private-original': 'fb02138fe8546581231f42ba0e4f062bee02d26cd79c5b94eb2ee069108f96c3', 'zenodo-response-metadata': '56a936079ae9fee6d0f0dde8cc711308db3645ef688d6df12f2ff0a8e2edf766'}


class AdditionalSourceProfileTests(unittest.TestCase):
    def setUp(self):
        jobs.CANCEL_EVENT.clear()

    def tearDown(self):
        jobs.CANCEL_EVENT.clear()

    def request(self):
        return {'schemaVersion': 1, 'jobId': 'additional-public-sources-test-001', 'profile': 'additional-public-sources'}

    def child(self, status='passed', exit_code=0, report_status='complete'):
        evidence = {} if report_status is None else {'additionalPublicSources': {'status': report_status}}
        return {'status': status, 'exitCode': exit_code, 'durationSeconds': 0.01, 'evidence': evidence}

    def test_exact_fixed_command_and_request_shape(self):
        self.assertEqual(jobs.parse_request(jobs.canonical(self.request())), self.request())
        steps = jobs.profile_steps(self.request()['profile'], ROOT)
        self.assertEqual([s[:2] for s in steps], [
            ('readiness', []), ('additional-public-source-tests', ['readiness']),
            ('additional-public-sources', ['readiness', 'additional-public-source-tests'])])
        self.assertEqual(steps[1][2], [jobs.sys.executable, '-I', '-B', '-m', 'unittest', 'discover', '-s', 'manual-action/tests', '-p', 'test_fetch_sources.py'])
        self.assertEqual(steps[2][2], [jobs.sys.executable, '-I', '-B', 'manual-action/fetch_sources.py'])
        for extra in ({'command': 'bash'}, {'ref': 'unreviewed'}, {'cacheRoot': '/home/user'}, {'url': 'https://unreviewed.invalid'}):
            with self.assertRaises(jobs.JobError):
                jobs.parse_request(jobs.canonical(self.request() | extra))
        self.assertEqual(jobs.PROFILES - set(LEGACY_GRAPHS), {'source-access-test-diagnostic', 'additional-public-sources', 'additional-source-capacity', 'public-source-read-handoff', 'local-source-export'})

    def test_existing_profile_graphs_unchanged(self):
        fake = types.ModuleType('offmenu.refresh.native_ciqual')
        fake.selected_output = lambda sha: Path('/synthetic-fixture') / sha
        with patch.dict('sys.modules', {'offmenu.refresh.native_ciqual': fake}), patch.object(jobs.time, 'strftime', return_value='2000-01-01T00:00:00Z'):
            for profile, expected in LEGACY_GRAPHS.items():
                with self.subTest(profile=profile):
                    steps = jobs.profile_steps(profile, ROOT, 'a' * 40)
                    for _, _, command in steps:
                        command[0] = 'PYTHON'
                    self.assertEqual(hashlib.sha256(jobs.canonical(steps)).hexdigest(), expected)
        self.assertEqual(jobs.MAX_REQUEST, 1024)
        self.assertEqual(jobs.MAX_CHILD_OUTPUT, 1024 * 1024)
        self.assertEqual(jobs.MAX_REPORT, 32768)
        self.assertEqual(jobs.MAX_DIAGNOSTIC_EVIDENCE, 12 * 1024)

    def test_bound_timeout_and_unrecognized_success_fails_closed(self):
        with patch.object(jobs, 'run_child', return_value=self.child()) as run:
            result = jobs.run_step('additional-public-sources', ['fixed'], ROOT)
        run.assert_called_once_with(['fixed'], ROOT, timeout=1230)
        self.assertEqual(result['status'], 'passed')
        for report_status in (None, 'partial', 'failed', 'blocked', 'unrecognized'):
            with self.subTest(report_status=report_status), patch.object(jobs, 'run_child', return_value=self.child(report_status=report_status)):
                result = jobs.run_step('additional-public-sources', ['fixed'], ROOT)
                self.assertEqual(result['status'], 'failed')
                self.assertEqual(result['exitCode'], 3)

    def test_status_and_exit_code_binding(self):
        for status, exit_code, expected in [('complete', 2, 'failed'), ('blocked', 2, 'blocked'), ('partial', 2, 'failed'), ('failed', 2, 'failed'), ('partial', 7, 'failed')]:
            with self.subTest(status=status, exit_code=exit_code), patch.object(jobs, 'run_child', return_value=self.child('failed', exit_code, status)):
                self.assertEqual(jobs.run_step('additional-public-sources', ['fixed'], ROOT)['status'], expected)
        for status, code in [('timeout', 124), ('cancelled', 130), ('output-limit', 125)]:
            with patch.object(jobs, 'run_child', return_value=self.child(status, code, None)):
                result = jobs.run_step('additional-public-sources', ['fixed'], ROOT)
                self.assertEqual((result['status'], result['exitCode']), (status, code))

    def test_failed_tests_never_launch_fetch(self):
        calls = []
        def fake(command, code, timeout=240):
            calls.append(command)
            return self.child('failed', 1, None) if 'unittest' in command else self.child()
        with patch.object(jobs, 'run_child', side_effect=fake):
            report = jobs.run_profile(self.request(), 'a' * 40, ROOT, '123', '1')
        self.assertEqual(len(calls), 2)
        self.assertEqual(report['status'], 'failed')
        self.assertEqual(report['steps'][-1]['status'], 'skipped')
        self.assertFalse(report['sourceContentsUploaded'])
        self.assertFalse(report['databaseWritesEnabled'])
        self.assertFalse(report['existingIngestAccessEnabled'])

    def test_blocked_fetch_is_incomplete_not_success(self):
        def fake(command, code, timeout=240):
            return self.child('failed', 2, 'blocked') if 'manual-action/fetch_sources.py' in command else self.child()
        with patch.object(jobs, 'run_child', side_effect=fake):
            report = jobs.run_profile(self.request(), 'a' * 40, ROOT, '123', '1')
        self.assertEqual(report['status'], 'incomplete')
        self.assertEqual(report['steps'][-1]['status'], 'blocked')
        self.assertFalse(report['corpusAcceptanceEstablished'])

    def test_receipt_reuse_no_second_execution_and_conflicting_pin_refused(self):
        with tempfile.TemporaryDirectory() as tmp, patch.object(jobs, 'OUTPUT', Path(tmp)), patch.object(jobs, 'run_profile', return_value={'status': 'passed', 'steps': []}) as run:
            jobs.execute(self.request(), 'a' * 40, ROOT, '123', '1')
            result = jobs.execute(self.request(), 'a' * 40, ROOT, '124', '1')
            self.assertEqual(run.call_count, 1)
            self.assertEqual(result['delivery'], 'existing-receipt-no-execution')
            with self.assertRaises(jobs.JobError):
                jobs.execute(self.request(), 'b' * 40, ROOT, '125', '1')

    def test_existing_kernel_lock_prevents_overlap(self):
        with tempfile.TemporaryDirectory() as tmp, patch.object(jobs, 'OUTPUT', Path(tmp)):
            lock_dir = Path(tmp) / 'locks'
            lock_dir.mkdir()
            with (lock_dir / 'dispatcher.lock').open('w') as lock:
                jobs.fcntl.flock(lock, jobs.fcntl.LOCK_EX | jobs.fcntl.LOCK_NB)
                with self.assertRaisesRegex(jobs.JobError, 'another-job-is-running-retry-later'):
                    jobs.execute(self.request(), 'a' * 40, ROOT, '123', '1')

    def fixture_summary(self):
        return {'schema': 'offmenu-source-fetch-summary/1', 'schemaVersion': 'offmenu-source-fetch-summary/1',
                'execution_host': 'Foo', 'operation': 'acquisition_only', 'manifest_sha256': 'a' * 64,
                'status': 'complete', 'sources': [{'source_id': 'generated-fixture', 'status': 'complete',
                    'files_complete': 1, 'files_reused': 0, 'files_blocked': 0, 'bytes_retained': 3,
                    'sha256': ['b' * 64], 'error_code': 'none'}],
                'database_mutations': 0, 'raw_data_uploaded': False, 'downloaded_code_executed': False,
                'disabled_source_count': 0, 'recipe_or_menu_record_count': None,
                'counts_are': 'files_and_bytes_not_records', 'updated_at': '2026-10-22T00:00:00Z'}

    def test_real_fetch_sanitizer_binding_and_no_paths_or_payloads(self):
        report = self.fixture_summary()
        report['raw_body'] = 'DO_NOT_PROJECT_SOURCE_BODY'
        report['sources'][0]['path'] = '/private/generated-source'
        evidence = jobs.safe_evidence(jobs.canonical(report))
        self.assertIn('additionalPublicSources', evidence)
        self.assertEqual(evidence['additionalPublicSources']['status'], 'complete')
        self.assertNotIn('DO_NOT_PROJECT', json.dumps(evidence))
        self.assertNotIn('/private', json.dumps(evidence))
        self.assertLess(len(jobs.canonical(evidence['additionalPublicSources'])), jobs.MAX_DIAGNOSTIC_EVIDENCE)

    def test_real_fetch_sanitizer_rejects_contradictions(self):
        changes = [{'raw_data_uploaded': True}, {'downloaded_code_executed': True},
                   {'database_mutations': 1}, {'operation': 'ingest'}, {'execution_host': 'other'},
                   {'sources': []}, {'recipe_or_menu_record_count': 1}]
        for change in changes:
            with self.subTest(change=change):
                evidence = jobs.safe_evidence(jobs.canonical(self.fixture_summary() | change))
                self.assertNotIn('additionalPublicSources', evidence)
                self.assertEqual(evidence['diagnosticEvidenceError'], 'invalid-diagnostic-schema')
        report = self.fixture_summary()
        report['sources'][0]['files_blocked'] = 1
        self.assertNotIn('additionalPublicSources', jobs.safe_evidence(jobs.canonical(report)))

    def test_real_fetch_fatal_blocker_has_static_safe_receipt(self):
        report = {'schema': 'offmenu-source-fetch-failure/1', 'schemaVersion': 'offmenu-source-fetch-failure/1',
                  'status': 'blocked', 'error_code': 'disk_reserve', 'database_mutations': 0,
                  'raw_data_uploaded': False, 'raw_error': '/private/generated-source'}
        evidence = jobs.safe_evidence(jobs.canonical(report))
        self.assertEqual(evidence['additionalPublicSources']['error_code'], 'disk_reserve')
        self.assertNotIn('/private', json.dumps(evidence))
        with patch.object(jobs, 'run_child', return_value={'status': 'failed', 'exitCode': 2, 'durationSeconds': 0.1, 'evidence': evidence}):
            self.assertEqual(jobs.run_step('additional-public-sources', ['fixed'], ROOT)['status'], 'blocked')


if __name__ == '__main__':
    unittest.main()

