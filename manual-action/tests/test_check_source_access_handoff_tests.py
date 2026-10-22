"""Private synthetic CLI transcripts/processes only; never ACL application."""
import contextlib
import importlib.util
import io
import json
import subprocess
import sys
from pathlib import Path
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location('source_access_test_wrapper',
    Path(__file__).resolve().parents[1] / 'check_source_access_handoff_tests.py')
wrapper = importlib.util.module_from_spec(spec)
spec.loader.exec_module(wrapper)
IDS = sorted(wrapper.EXPECTED_TEST_IDS)
SECRET = 'SYNTHETIC_PRIVATE_PATH:/fixture/not-public:acl:user:123:rwx'


def captured(stderr, exit_code=0, stdout=b''):
    return {'error_code': 'none', 'capture_status': 'completed', 'child_exit_code': exit_code,
            'stdout': stdout, 'stderr': stderr.encode()}


def transcript(headers=(), footer='OK', ran=38):
    return '.' * 38 + '\n' + '\n'.join(headers) + '\n' + SECRET + '\n' + '-' * 70 + f'\nRan {ran} tests in 0.001s\n\n{footer}\n'


def header(name, kind='FAIL', suffix=''):
    return f'{kind}: {name.rsplit(".", 1)[1]} ({name}){suffix}'


class ExactCLIWrapperTests(unittest.TestCase):
    def test_fixed_command_and_original_popen_inheritance(self):
        self.assertEqual(wrapper.fixed_command(), [sys.executable, '-I', '-B', '-m', 'unittest', 'discover',
            '-s', 'manual-action/tests', '-p', 'test_grant_acquired_read_access.py'])
        with patch.object(wrapper.subprocess, 'Popen', side_effect=OSError(SECRET)) as launch:
            result = wrapper.capture_original_cli()
        launch.assert_called_once_with(wrapper.fixed_command(), cwd=wrapper.ROOT,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, close_fds=True)
        self.assertEqual(result['error_code'], 'child_launch_failed')
        self.assertEqual(result['capture_status'], 'not_started')
        self.assertNotIn(SECRET, json.dumps(wrapper.parse_original_cli(result)))

    def test_suite_identity_is_bound_without_import_or_execution(self):
        self.assertEqual(len(IDS), 38)
        self.assertTrue(wrapper.verify_suite_identity())
        with patch.object(wrapper, 'verify_suite_identity', return_value=False), patch.object(wrapper, 'capture_original_cli') as launch:
            report = wrapper.run_fixed_suite()
        launch.assert_not_called()
        self.assertEqual(report['error_code'], 'test_suite_mismatch')
        self.assertIs(report['suite_identity_verified'], False)

    def test_valid_success_and_unattributed_skips(self):
        for footer, skipped in (('OK', 0), ('OK (skipped=1)', 1)):
            report = wrapper.parse_original_cli(captured(transcript(footer=footer), stdout=SECRET.encode()))
            self.assertEqual((report['status'], report['tests_run']), ('passed', 38))
            self.assertEqual((report['skipped'], report['unattributed_skips'], report['skipped_test_ids']), (skipped, skipped, []))
            self.assertNotIn(SECRET, json.dumps(report))

    def test_known_failure_error_and_subtest_parameters_are_projected_only_as_static_ids(self):
        headers = [header(IDS[0], suffix=' (private=' + SECRET + ')'), header(IDS[1], 'ERROR')]
        report = wrapper.parse_original_cli(captured(transcript(headers, 'FAILED (failures=1, errors=1, skipped=1)'), 1))
        self.assertEqual(report['failed_test_ids'], [IDS[0]])
        self.assertEqual(report['error_test_ids'], [IDS[1]])
        self.assertEqual((report['status'], report['error_code']), ('failed', 'test_failures'))
        self.assertNotIn(SECRET, json.dumps(report))

    def test_repeated_subtest_headers_reconcile_events_not_unique_ids(self):
        report = wrapper.parse_original_cli(captured(transcript([header(IDS[0], suffix=' (a=1)'),
            header(IDS[0], suffix=' (a=2)')], 'FAILED (failures=2)'), 1))
        self.assertEqual((report['failures'], report['failure_events']), (1, 2))
        self.assertEqual(report['failed_test_ids'], [IDS[0]])

    def test_legacy_parent_class_header_is_known(self):
        name = IDS[0]
        text = f'FAIL: {name.rsplit(".",1)[1]} ({name.rsplit(".",1)[0]})'
        report = wrapper.parse_original_cli(captured(transcript([text], 'FAILED (failures=1)'), 1))
        self.assertEqual(report['failed_test_ids'], [name])

    def test_unknown_setup_loader_or_private_header_fails_closed_without_echo(self):
        for text in ('ERROR: setUpClass (test_grant_acquired_read_access.NarrowACLTests)',
                'ERROR: test_broken (unittest.loader._FailedTest.test_broken)',
                'FAIL: test_private (' + SECRET + ')'):
            report = wrapper.parse_original_cli(captured(transcript([text], 'FAILED (errors=1)'), 1))
            self.assertEqual(report['error_code'], 'unknown_test_id')
            self.assertEqual(report['failed_test_ids'] + report['error_test_ids'], [])
            self.assertNotIn(SECRET, json.dumps(report))

    def test_summary_run_count_exit_duplicate_footer_and_header_mismatch_fail_closed(self):
        cases = ((transcript(footer='OK'), 1), (transcript(ran=37), 0),
            (transcript() + 'OK\n', 0), (transcript().replace('OK\n', 'OK\nFAILED (failures=1)\n'), 1),
            (transcript().replace('Ran 38 tests', 'Ran 38 tests in 0.001s\nRan 38 tests'), 0),
            (transcript([header(IDS[0])], 'FAILED (failures=2)'), 1),
            (transcript([], 'FAILED (errors=1)'), 1),
            (transcript([header(IDS[0])], 'FAILED (failures=1, failures=1)'), 1),
            (transcript([], 'OK (skipped=39)'), 0),
            (transcript([], 'FAILED (unexpected successes=1)'), 1),
            (transcript() + SECRET, 0))
        for text, exit_code in cases:
            with self.subTest(exit_code=exit_code):
                report = wrapper.parse_original_cli(captured(text, exit_code))
                self.assertEqual(report['status'], 'failed')
                self.assertEqual(report['error_code'], 'parser_error')

    def test_private_child_capture_has_combined_bound_and_kill_wait(self):
        command = [sys.executable, '-I', '-B', '-c', 'import os;os.write(1,b"x"*40);os.write(2,b"y"*40)']
        with patch.object(wrapper, 'fixed_command', return_value=command), patch.object(wrapper, 'MAX_CAPTURE_BYTES', 64):
            result = wrapper.capture_original_cli()
        self.assertEqual(result['error_code'], 'output_limit')
        self.assertLessEqual(len(result['stdout']) + len(result['stderr']), 64)
        self.assertIsNotNone(result['child_exit_code'])
        report = wrapper.parse_original_cli(result)
        self.assertEqual((report['status'], report['capture_status']), ('failed', 'output_limit'))

    def test_private_child_timeout_kills_and_reaps(self):
        command = [sys.executable, '-I', '-B', '-c', 'import time;time.sleep(10)']
        with patch.object(wrapper, 'fixed_command', return_value=command), patch.object(wrapper, 'WALL_SECONDS', 0.05):
            result = wrapper.capture_original_cli()
        self.assertEqual(result['error_code'], 'timeout')
        self.assertLess(result['child_exit_code'], 0)
        self.assertEqual(wrapper.parse_original_cli(result)['capture_status'], 'timeout')

    def test_strict_projection_rejects_false_success_counts_and_unknown_data(self):
        report = wrapper.parse_original_cli(captured(transcript()))
        self.assertNotIn('private', wrapper.sanitize_report({**report, 'private': SECRET}))
        for update in ({'child_exit_code': True}, {'child_exit_code': 1}, {'reporter_mode': 'custom'},
                {'capture_status': 'timeout'}, {'tests_run': 37}, {'tests_expected': 39},
                {'suite_identity_verified': False}, {'expected_test_suite_sha256': '0'*64},
                {'failed_test_ids': [SECRET], 'failures': 1}, {'failure_events': 1},
                {'unattributed_skips': 1}, {'skipped_test_ids': [IDS[0]], 'skipped': 1}):
            with self.subTest(keys=sorted(update)), self.assertRaises(ValueError):
                wrapper.sanitize_report({**report, **update})

    def test_main_only_emits_safe_json_exit_and_rejects_all_arguments(self):
        for args, exit_code, text in (([], 0, transcript()), ([], 1, transcript([header(IDS[0])], 'FAILED (failures=1)')),
                                     ([SECRET], 1, transcript()), (['--apply'], 1, transcript())):
            stdout, stderr = io.StringIO(), io.StringIO()
            with patch.object(wrapper, 'capture_original_cli', return_value=captured(text, exit_code if not args else 0)) as launch, \
                    contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
                code = wrapper.main(args)
            self.assertEqual(code, exit_code)
            self.assertEqual(stderr.getvalue(), '')
            self.assertNotIn(SECRET, stdout.getvalue())
            wrapper.sanitize_report(json.loads(stdout.getvalue()))
            if args: launch.assert_not_called()


if __name__ == '__main__':
    unittest.main()
