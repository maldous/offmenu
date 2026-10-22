#!/usr/bin/env python3
"""Run only the fixed source-access fixture suite; emit no exception details."""
from __future__ import annotations

import contextlib
import hashlib
import json
import os
from pathlib import Path
import sys
import stat
import unittest

SCHEMA = 'offmenu-source-access-tests/1'
TEST_DIRECTORY = Path(__file__).resolve().parent / 'tests'
TEST_PATTERN = 'test_grant_acquired_read_access.py'
TEST_SUITE_SHA = '3f418e0e27be6c21c63d3d33f4750e18aed85fe572ec91b6ca58c0e7d50a5520'
EXPECTED_TEST_IDS = frozenset((
    'test_grant_acquired_read_access.NarrowACLTests.test_actor_must_existing_nonroot_dedicated_account',
    'test_grant_acquired_read_access.NarrowACLTests.test_actual_system_libacl_read_is_valid_on_synthetic_temp_only',
    'test_grant_acquired_read_access.NarrowACLTests.test_apply_failure_rolls_back_only_our_exact_still_matching_changes',
    'test_grant_acquired_read_access.NarrowACLTests.test_default_acl_race_blocks_without_writing_default_acl',
    'test_grant_acquired_read_access.NarrowACLTests.test_default_cli_is_nonmutating_plan',
    'test_grant_acquired_read_access.NarrowACLTests.test_directory_grant_is_traversal_not_listing_or_write',
    'test_grant_acquired_read_access.NarrowACLTests.test_durable_snapshot_precedes_any_acl_write_and_default_acl_untouched',
    'test_grant_acquired_read_access.NarrowACLTests.test_existing_same_target_grant_is_idempotent',
    'test_grant_acquired_read_access.NarrowACLTests.test_external_acl_change_is_not_overwritten_during_rollback',
    'test_grant_acquired_read_access.NarrowACLTests.test_fixed_manifest_scope_and_canonical_pin',
    'test_grant_acquired_read_access.NarrowACLTests.test_full_ctime_guard_detects_same_size_mtime_restored_edit',
    'test_grant_acquired_read_access.NarrowACLTests.test_libacl_absence_blocks_instead_of_installing',
    'test_grant_acquired_read_access.NarrowACLTests.test_libacl_load_does_not_spawn_lookup_commands',
    'test_grant_acquired_read_access.NarrowACLTests.test_libacl_native_numeric_qualifier_roundtrip_without_filesystem_write',
    'test_grant_acquired_read_access.NarrowACLTests.test_mask_expansion_that_would_expose_latent_group_rights_is_blocked',
    'test_grant_acquired_read_access.NarrowACLTests.test_mask_expansion_that_would_expose_latent_named_user_rights_is_blocked',
    'test_grant_acquired_read_access.NarrowACLTests.test_multiple_group_entries_union_effective_permissions',
    'test_grant_acquired_read_access.NarrowACLTests.test_named_user_precedes_group_and_other_rights',
    'test_grant_acquired_read_access.NarrowACLTests.test_no_default_acl_or_unknown_tag_in_serialization',
    'test_grant_acquired_read_access.NarrowACLTests.test_preexisting_directory_read_cannot_be_combined_with_new_traverse',
    'test_grant_acquired_read_access.NarrowACLTests.test_preexisting_effective_masked_principals_are_unchanged',
    'test_grant_acquired_read_access.NarrowACLTests.test_private_file_named_read_only_no_effective_group_world_grant',
    'test_grant_acquired_read_access.NarrowACLTests.test_rollback_failure_is_partial_never_success',
    'test_grant_acquired_read_access.NarrowACLTests.test_sanitizer_drops_private_acl_paths_and_requires_applied_mode',
    'test_grant_acquired_read_access.NarrowACLTests.test_snapshot_failure_never_changes_any_acl',
    'test_grant_acquired_read_access.NarrowACLTests.test_symlink_parent_or_leaf_is_rejected',
    'test_grant_acquired_read_access.NarrowACLTests.test_target_existing_write_or_file_execute_permission_blocks',
    'test_grant_acquired_read_access.ScopePlanTests.test_changed_cache_digest_blocks_before_grant',
    'test_grant_acquired_read_access.ScopePlanTests.test_closed_50_plus_50_plus_9_scope_is_verified_readonly',
    'test_grant_acquired_read_access.ScopePlanTests.test_edited_source_and_receipt_cannot_replace_pinned_acquired_bytes',
    'test_grant_acquired_read_access.ScopePlanTests.test_fixture_under_private_tmpdir_parent_models_only_outside_traversal',
    'test_grant_acquired_read_access.ScopePlanTests.test_hardlinked_artifact_blocks_before_any_acl_write',
    'test_grant_acquired_read_access.ScopePlanTests.test_new_traversal_cannot_expose_unselected_readable_sibling',
    'test_grant_acquired_read_access.ScopePlanTests.test_opaque_extra_receipt_payload_is_not_shared',
    'test_grant_acquired_read_access.ScopePlanTests.test_production_guard_refuses_one_unauthorized_outside_ancestor_without_writes',
    'test_grant_acquired_read_access.ScopePlanTests.test_unselected_private_sibling_is_metadata_checked_without_body_read',
    'test_grant_acquired_read_access.ScopePlanTests.test_unselected_symlink_is_conservatively_refused',
    'test_grant_acquired_read_access.ScopePlanTests.test_unselected_traversable_directory_blocks_without_recursion',
))
EXPECTED_COUNT = 38
ERROR_CODES = frozenset(('none', 'test_suite_mismatch', 'test_runner_failed',
                         'unknown_test_id', 'test_failures'))


def sanitize_report(value):
    """Validate fixed enums/counts/IDs; never project error strings or paths."""
    if not isinstance(value, dict) or value.get('schemaVersion') != SCHEMA:
        raise ValueError('invalid_test_report')
    if value.get('status') not in {'passed', 'failed'} or value.get('error_code') not in ERROR_CODES:
        raise ValueError('invalid_test_report')
    if type(value.get('tests_expected')) is not int or value['tests_expected'] != EXPECTED_COUNT:
        raise ValueError('invalid_test_report')
    if type(value.get('tests_run')) is not int or not 0 <= value['tests_run'] <= EXPECTED_COUNT:
        raise ValueError('invalid_test_report')
    if value.get('expected_test_suite_sha256') != TEST_SUITE_SHA or type(value.get('suite_identity_verified')) is not bool:
        raise ValueError('invalid_test_report')
    result = {key: value[key] for key in ('schemaVersion', 'status', 'error_code', 'tests_expected', 'tests_run',
                                         'expected_test_suite_sha256', 'suite_identity_verified')}
    for count_key, ids_key in (('failures', 'failed_test_ids'), ('errors', 'error_test_ids'), ('skipped', 'skipped_test_ids')):
        ids = value.get(ids_key)
        if (not isinstance(ids, list) or len(ids) > EXPECTED_COUNT
                or any(type(item) is not str or item not in EXPECTED_TEST_IDS for item in ids)
                or ids != sorted(set(ids)) or type(value.get(count_key)) is not int
                or value[count_key] != len(ids)):
            raise ValueError('invalid_test_report')
        result[ids_key], result[count_key] = list(ids), len(ids)
    outcomes = set(result['failed_test_ids']) | set(result['error_test_ids']) | set(result['skipped_test_ids'])
    if not value['suite_identity_verified'] and value['tests_run']:
        raise ValueError('invalid_test_report')
    if len(outcomes) > value['tests_run']:
        raise ValueError('invalid_test_report')
    if value['error_code'] == 'test_failures' and not (result['failures'] or result['errors']):
        raise ValueError('invalid_test_report')
    if value['status'] == 'passed':
        if (value['error_code'] != 'none' or not value['suite_identity_verified'] or value['tests_run'] != EXPECTED_COUNT
                or result['failures'] or result['errors']):
            raise ValueError('invalid_test_report')
    elif value['error_code'] == 'none':
        raise ValueError('invalid_test_report')
    return result


class SafeResult(unittest.TestResult):
    """Do not format, retain or print exception values or traceback objects."""
    def __init__(self):
        super().__init__()
        self.failed_ids, self.error_ids, self.skipped_ids, self.started_ids = set(), set(), set(), set()
        self.unknown_id = False

    def known_id(self, test):
        # Subtest IDs may include repr(parameters); only the static parent is used.
        parent = test.test_case if isinstance(test, unittest.case._SubTest) else test
        try:
            name = parent.id()
        except BaseException:
            self.unknown_id = True
            return None
        if type(name) is not str or name not in EXPECTED_TEST_IDS:
            self.unknown_id = True
            return None
        return name

    def startTest(self, test):
        name = self.known_id(test)
        if name in self.started_ids or self.testsRun >= EXPECTED_COUNT:
            self.unknown_id = True
            self.stop()
            return
        if name is not None:
            self.started_ids.add(name)
        self.testsRun += 1

    def addSuccess(self, test):
        self.known_id(test)

    def addFailure(self, test, err):
        name = self.known_id(test)
        if name is not None:
            self.failed_ids.add(name)

    def addError(self, test, err):
        name = self.known_id(test)
        if name is not None:
            self.error_ids.add(name)

    def addSkip(self, test, reason):
        name = self.known_id(test)
        if name is not None:
            self.skipped_ids.add(name)

    def addExpectedFailure(self, test, err):
        # The fixed suite has no expected failures; never relabel one as success.
        self.addError(test, err)

    def addUnexpectedSuccess(self, test):
        self.addFailure(test, None)

    def addSubTest(self, test, subtest, err):
        if err is not None:
            if issubclass(err[0], test.failureException):
                self.addFailure(test, err)
            else:
                self.addError(test, err)

    def wasSuccessful(self):
        return not (self.unknown_id or self.failed_ids or self.error_ids)


@contextlib.contextmanager
def silence_test_output():
    # FD suppression includes os.write and native library diagnostics; Python
    # redirects also silence normal unittest/import prints and warnings.
    saved = {}
    with open(os.devnull, 'w', encoding='utf-8') as sink:
        try:
            for fd in (1, 2):
                saved[fd] = os.dup(fd)
                os.dup2(sink.fileno(), fd)
            with contextlib.redirect_stdout(sink), contextlib.redirect_stderr(sink):
                yield
        finally:
            for fd, original in saved.items():
                os.dup2(original, fd)
                os.close(original)


def flatten(suite):
    for test in suite:
        if isinstance(test, unittest.TestSuite):
            yield from flatten(test)
        else:
            yield test


def verify_suite_identity():
    fd = os.open(TEST_DIRECTORY / TEST_PATTERN, os.O_RDONLY | os.O_NOFOLLOW)
    try:
        before = os.fstat(fd)
        if not stat.S_ISREG(before.st_mode) or not 0 < before.st_size <= 128 * 1024:
            return False
        chunks = []
        total = 0
        while total <= 128 * 1024:
            chunk = os.read(fd, min(65536, 128 * 1024 + 1 - total))
            if not chunk:
                break
            chunks.append(chunk)
            total += len(chunk)
        after = os.fstat(fd)
        identity = lambda info: (info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns, info.st_ctime_ns)
        return (identity(before) == identity(after) and total == before.st_size
            and hashlib.sha256(b''.join(chunks)).hexdigest() == TEST_SUITE_SHA)
    finally:
        os.close(fd)


def load_fixed_suite():
    return unittest.TestLoader().discover(str(TEST_DIRECTORY), pattern=TEST_PATTERN,
                                         top_level_dir=str(TEST_DIRECTORY))


def run_fixed_suite():
    result = SafeResult()
    code = 'none'
    verified = False
    try:
        with silence_test_output():
            verified = verify_suite_identity()
            if not verified:
                code = 'test_suite_mismatch'
                suite = unittest.TestSuite()
            else:
                suite = load_fixed_suite()
            identities = [test.id() for test in flatten(suite)]
            if (len(identities) != EXPECTED_COUNT or any(type(item) is not str for item in identities)
                    or set(identities) != EXPECTED_TEST_IDS):
                code = 'test_suite_mismatch'
            else:
                suite.run(result)
                if result.unknown_id:
                    code = 'unknown_test_id'
                elif result.testsRun != EXPECTED_COUNT or result.started_ids != EXPECTED_TEST_IDS:
                    code = 'test_suite_mismatch'
                elif result.failed_ids or result.error_ids:
                    code = 'test_failures'
    except BaseException:
        code = 'test_runner_failed'
    value = {'schemaVersion': SCHEMA, 'status': 'passed' if code == 'none' else 'failed',
        'error_code': code, 'tests_expected': EXPECTED_COUNT, 'tests_run': min(result.testsRun, EXPECTED_COUNT),
        'expected_test_suite_sha256': TEST_SUITE_SHA, 'suite_identity_verified': verified,
        'failed_test_ids': sorted(result.failed_ids), 'error_test_ids': sorted(result.error_ids),
        'skipped_test_ids': sorted(result.skipped_ids), 'failures': len(result.failed_ids),
        'errors': len(result.error_ids), 'skipped': len(result.skipped_ids)}
    return sanitize_report(value)


def main(argv=None):
    args = sys.argv[1:] if argv is None else argv
    if args:
        # No argument value is echoed, parsed as a path, or used for discovery.
        report = {'schemaVersion': SCHEMA, 'status': 'failed', 'error_code': 'test_suite_mismatch',
            'tests_expected': EXPECTED_COUNT, 'tests_run': 0, 'expected_test_suite_sha256': TEST_SUITE_SHA,
            'suite_identity_verified': False, 'failed_test_ids': [],
            'error_test_ids': [], 'skipped_test_ids': [], 'failures': 0, 'errors': 0, 'skipped': 0}
    else:
        report = run_fixed_suite()
    print(json.dumps(sanitize_report(report), sort_keys=True), flush=True)
    return 0 if report['status'] == 'passed' else 1


if __name__ == '__main__':
    raise SystemExit(main())
