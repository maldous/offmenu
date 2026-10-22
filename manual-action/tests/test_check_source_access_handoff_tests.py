"""Generated wrapper tests; never invoke source ACL application or Foo."""
import contextlib
import copy
import importlib.util
import io
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location('source_access_test_wrapper',
    Path(__file__).resolve().parents[1] / 'check_source_access_handoff_tests.py')
wrapper = importlib.util.module_from_spec(spec)
spec.loader.exec_module(wrapper)
IDS = sorted(wrapper.EXPECTED_TEST_IDS)
SECRET = 'SYNTHETIC_PRIVATE_MESSAGE:/fixture/not-public:acl:user:123:rwx'


class GeneratedCase(unittest.TestCase):
    __test__ = False
    def __init__(self, name, behavior='pass'):
        super().__init__('runTest')
        self.name, self.behavior = name, behavior
    def id(self):
        return self.name
    def runTest(self):
        if self.behavior == 'failure':
            self.fail(SECRET)
        if self.behavior == 'error':
            raise RuntimeError(SECRET)
        if self.behavior == 'skip':
            self.skipTest(SECRET)
        if self.behavior == 'subtest':
            with self.subTest(private_value=SECRET):
                self.fail(SECRET)
        if self.behavior == 'noise':
            print(SECRET)
            print(SECRET, file=sys.stderr)
            os.write(1, SECRET.encode())
            os.write(2, SECRET.encode())
        if self.behavior == 'unknown':
            self.name = SECRET
            self.fail(SECRET)


def suite(changes=None):
    changes = changes or {}
    return unittest.TestSuite(GeneratedCase(name, changes.get(name, 'pass')) for name in IDS)


class SafeWrapperTests(unittest.TestCase):
    def run_suite(self, changes=None):
        with patch.object(wrapper, 'load_fixed_suite', return_value=suite(changes)):
            return wrapper.run_fixed_suite()

    def test_static_manifest_has_exact_38_ids_and_matches_unchanged_suite(self):
        self.assertEqual(len(IDS), 38)
        # Loading the reviewed fixture module is allowed; no tests or ACL setters run.
        loaded = wrapper.load_fixed_suite()
        self.assertEqual(sorted(t.id() for t in wrapper.flatten(loaded)), IDS)

    def test_all_pass_has_complete_counts_and_sanitized_only_keys(self):
        result = self.run_suite()
        self.assertEqual((result['status'], result['tests_run'], result['error_code']), ('passed', 38, 'none'))
        self.assertEqual(set(result), {'schemaVersion', 'status', 'tests_run', 'tests_expected',
            'error_code', 'failures', 'errors', 'skipped', 'failed_test_ids', 'error_test_ids', 'skipped_test_ids',
            'expected_test_suite_sha256', 'suite_identity_verified'})

    def test_fail_error_skip_and_subtest_have_static_base_ids_only(self):
        result = self.run_suite({IDS[0]: 'failure', IDS[1]: 'error', IDS[2]: 'skip', IDS[3]: 'subtest'})
        self.assertEqual(result['failed_test_ids'], [IDS[0], IDS[3]])
        self.assertEqual(result['error_test_ids'], [IDS[1]])
        self.assertEqual(result['skipped_test_ids'], [IDS[2]])
        self.assertEqual(result['status'], 'failed')
        self.assertNotIn(SECRET, json.dumps(result))

    def test_loader_and_native_python_output_are_suppressed(self):
        real_loader = lambda: suite({IDS[0]: 'noise'})
        def loader():
            print(SECRET)
            os.write(2, SECRET.encode())
            return real_loader()
        saved = {fd: os.dup(fd) for fd in (1, 2)}
        try:
            with tempfile.TemporaryFile() as captured:
                for fd in (1, 2): os.dup2(captured.fileno(), fd)
                with patch.object(wrapper, 'load_fixed_suite', side_effect=loader):
                    result = wrapper.run_fixed_suite()
                captured.seek(0)
                emitted = captured.read()
        finally:
            for fd, original in saved.items():
                os.dup2(original, fd); os.close(original)
        self.assertEqual(emitted, b'')
        self.assertEqual(result['status'], 'passed')

    def test_suite_hash_mismatch_prevents_import_and_execution(self):
        with patch.object(wrapper, 'verify_suite_identity', return_value=False), patch.object(wrapper, 'load_fixed_suite') as loader:
            result = wrapper.run_fixed_suite()
        loader.assert_not_called()
        self.assertEqual((result['status'], result['error_code'], result['suite_identity_verified']),
            ('failed', 'test_suite_mismatch', False))

    def test_suite_missing_duplicate_or_unknown_id_never_runs(self):
        for cases in ([GeneratedCase(n) for n in IDS[:-1]],
                      [GeneratedCase(n) for n in IDS[:-1]] + [GeneratedCase(IDS[0])],
                      [GeneratedCase(n) for n in IDS[:-1]] + [GeneratedCase(SECRET)]):
            with self.subTest(count=len(cases)), patch.object(wrapper, 'load_fixed_suite', return_value=unittest.TestSuite(cases)):
                result = wrapper.run_fixed_suite()
                self.assertEqual((result['error_code'], result['tests_run']), ('test_suite_mismatch', 0))
                self.assertNotIn(SECRET, json.dumps(result))

    def test_id_changes_during_test_fail_closed_without_echo(self):
        result = self.run_suite({IDS[0]: 'unknown'})
        self.assertEqual(result['error_code'], 'unknown_test_id')
        self.assertNotIn(SECRET, json.dumps(result))

    def test_unexpected_loader_exception_never_emits_details(self):
        with patch.object(wrapper, 'load_fixed_suite', side_effect=RuntimeError(SECRET)):
            result = wrapper.run_fixed_suite()
        self.assertEqual(result['error_code'], 'test_runner_failed')
        self.assertNotIn(SECRET, json.dumps(result))

    def test_skip_reason_not_published_and_is_not_failure(self):
        result = self.run_suite({IDS[0]: 'skip'})
        self.assertEqual((result['status'], result['skipped'], result['skipped_test_ids']), ('passed', 1, [IDS[0]]))
        self.assertNotIn(SECRET, json.dumps(result))

    def test_sanitizer_rejects_conflicting_counts_unknown_ids_and_false_success(self):
        good = self.run_suite()
        self.assertNotIn('private_path', wrapper.sanitize_report({**good, 'private_path': SECRET}))
        bad_values = ({'tests_expected': 39}, {'tests_run': True}, {'tests_run': 37},
            {'failed_test_ids': [SECRET], 'failures': 1}, {'errors': 1},
            {'skipped_test_ids': [IDS[0], IDS[0]], 'skipped': 2},
            {'failed_test_ids': [IDS[0]], 'failures': 1}, {'error_code': SECRET},
            {'expected_test_suite_sha256': '0' * 64}, {'suite_identity_verified': False})
        for bad in bad_values:
            with self.subTest(keys=sorted(bad)), self.assertRaises(ValueError):
                wrapper.sanitize_report({**good, **bad})

    def test_cli_pass_failure_and_argument_refusal_exit_contract(self):
        for args, changes, expected in (([], {}, 0), ([], {IDS[0]: 'failure'}, 1), ([SECRET], {}, 1)):
            output = io.StringIO()
            with patch.object(wrapper, 'load_fixed_suite', return_value=suite(changes)) as loader, contextlib.redirect_stdout(output):
                code = wrapper.main(args)
            self.assertEqual(code, expected)
            self.assertNotIn(SECRET, output.getvalue())
            wrapper.sanitize_report(json.loads(output.getvalue()))
            if args: loader.assert_not_called()


def load_tests(loader, standard_tests, pattern):
    # The generated case factory is a helper, not an extra wrapper test.
    return loader.loadTestsFromTestCase(SafeWrapperTests)


if __name__ == '__main__':
    unittest.main()
