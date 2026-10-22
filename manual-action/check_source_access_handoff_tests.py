#!/usr/bin/env python3
"""Capture the exact fixed unittest CLI; publish only reviewed IDs and counts."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import re
import selectors
import stat
import subprocess
import sys
import time

SCHEMA = 'offmenu-source-access-tests/1'
ROOT = Path(__file__).resolve().parents[1]
TEST_DIRECTORY = ROOT / 'manual-action' / 'tests'
TEST_PATTERN = 'test_grant_acquired_read_access.py'
TEST_SUITE_SHA = '2ee455945ad453409c2ac40c67db0be46eaf310c64caa075aba3f93ca450d748'
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
MAX_CAPTURE_BYTES = 1024 * 1024  # Combined stdout + stderr, never each separately.
WALL_SECONDS = 180
ERROR_CODES = frozenset(('none', 'test_suite_mismatch', 'unknown_test_id',
    'test_failures', 'parser_error', 'timeout', 'output_limit', 'child_launch_failed',
    'child_cleanup_failed', 'test_runner_failed'))


def base_report(verified=False):
    return {'schemaVersion': SCHEMA, 'reporter_mode': 'original_cli', 'status': 'failed',
        'error_code': 'test_runner_failed', 'tests_expected': EXPECTED_COUNT, 'tests_run': 0,
        'expected_test_suite_sha256': TEST_SUITE_SHA, 'suite_identity_verified': verified,
        'child_exit_code': None, 'capture_status': 'not_started', 'failed_test_ids': [], 'error_test_ids': [], 'skipped_test_ids': [],
        'failures': 0, 'errors': 0, 'skipped': 0, 'unattributed_skips': 0,
        'failure_events': 0, 'error_events': 0}


def sanitize_report(value):
    """Closed projection; no raw child output, parameter repr, path or exception."""
    if not isinstance(value, dict) or value.get('schemaVersion') != SCHEMA:
        raise ValueError('invalid_test_report')
    if (value.get('reporter_mode') != 'original_cli' or value.get('status') not in {'passed', 'failed'}
            or value.get('error_code') not in ERROR_CODES
            or value.get('expected_test_suite_sha256') != TEST_SUITE_SHA
            or type(value.get('suite_identity_verified')) is not bool
            or value.get('capture_status') not in {'completed', 'timeout', 'output_limit', 'not_started', 'failed'}):
        raise ValueError('invalid_test_report')
    result = {key: value[key] for key in ('schemaVersion', 'reporter_mode', 'status', 'error_code',
        'expected_test_suite_sha256', 'suite_identity_verified', 'capture_status')}
    for key, maximum in (('tests_expected', EXPECTED_COUNT), ('tests_run', EXPECTED_COUNT),
            ('failures', EXPECTED_COUNT), ('errors', EXPECTED_COUNT), ('skipped', EXPECTED_COUNT),
            ('unattributed_skips', EXPECTED_COUNT), ('failure_events', 4096), ('error_events', 4096)):
        if type(value.get(key)) is not int or not 0 <= value[key] <= maximum:
            raise ValueError('invalid_test_report')
        result[key] = value[key]
    if result['tests_expected'] != EXPECTED_COUNT:
        raise ValueError('invalid_test_report')
    child = value.get('child_exit_code')
    if child is not None and (type(child) is not int or not -255 <= child <= 255):
        raise ValueError('invalid_test_report')
    result['child_exit_code'] = child
    if ((result['capture_status'] == 'completed' and child is None)
            or (result['capture_status'] == 'not_started' and (child is not None or result['tests_run']))
            or (result['error_code'] in {'timeout', 'output_limit'} and result['capture_status'] != result['error_code'])
            or (result['error_code'] == 'child_launch_failed' and result['capture_status'] != 'not_started')):
        raise ValueError('invalid_test_report')
    for key in ('failed_test_ids', 'error_test_ids', 'skipped_test_ids'):
        values = value.get(key)
        if (not isinstance(values, list) or len(values) > EXPECTED_COUNT
                or any(type(item) is not str or item not in EXPECTED_TEST_IDS for item in values)
                or values != sorted(set(values))):
            raise ValueError('invalid_test_report')
        result[key] = list(values)
    if (result['failures'] != len(result['failed_test_ids']) or result['errors'] != len(result['error_test_ids'])
            or result['skipped'] != len(result['skipped_test_ids']) + result['unattributed_skips']
            or result['skipped_test_ids']  # Original nonverbose CLI never identifies skips.
            or result['failure_events'] < result['failures'] or result['error_events'] < result['errors']
            or bool(result['failure_events']) != bool(result['failures'])
            or bool(result['error_events']) != bool(result['errors'])):
        raise ValueError('invalid_test_report')
    observed = set(result['failed_test_ids']) | set(result['error_test_ids'])
    if len(observed) + result['skipped'] > result['tests_run']:
        raise ValueError('invalid_test_report')
    if not result['suite_identity_verified'] and (result['tests_run'] or child is not None or result['capture_status'] != 'not_started'):
        raise ValueError('invalid_test_report')
    if result['status'] == 'passed':
        if (result['error_code'] != 'none' or result['capture_status'] != 'completed' or not result['suite_identity_verified'] or child != 0
                or result['tests_run'] != EXPECTED_COUNT or result['failure_events'] or result['error_events']):
            raise ValueError('invalid_test_report')
    elif result['error_code'] == 'none':
        raise ValueError('invalid_test_report')
    if result['error_code'] == 'test_failures' and (result['capture_status'] != 'completed' or child != 1 or result['tests_run'] != EXPECTED_COUNT
            or not (result['failure_events'] or result['error_events'])):
        raise ValueError('invalid_test_report')
    return result


def verify_suite_identity():
    fd = os.open(TEST_DIRECTORY / TEST_PATTERN, os.O_RDONLY | os.O_NOFOLLOW)
    try:
        before = os.fstat(fd)
        if not stat.S_ISREG(before.st_mode) or not 0 < before.st_size <= 128 * 1024:
            return False
        chunks, total = [], 0
        while total <= 128 * 1024:
            chunk = os.read(fd, min(65536, 128 * 1024 + 1 - total))
            if not chunk:
                break
            chunks.append(chunk); total += len(chunk)
        after = os.fstat(fd)
        identity = lambda info: (info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns, info.st_ctime_ns)
        return (identity(before) == identity(after) and total == before.st_size
            and hashlib.sha256(b''.join(chunks)).hexdigest() == TEST_SUITE_SHA)
    finally:
        os.close(fd)


def fixed_command():
    return [sys.executable, '-I', '-B', '-m', 'unittest', 'discover', '-s',
            'manual-action/tests', '-p', TEST_PATTERN]


def capture_original_cli():
    """Private bounded capture; inherit dispatcher process group/env/umask."""
    process = None
    selector = selectors.DefaultSelector()
    chunks = {'stdout': [], 'stderr': []}
    total, code = 0, 'none'
    try:
        process = subprocess.Popen(fixed_command(), cwd=ROOT, stdout=subprocess.PIPE,
            stderr=subprocess.PIPE, close_fds=True)
        # No start_new_session, setsid, preexec_fn, replacement env or umask.
        for name, stream in (('stdout', process.stdout), ('stderr', process.stderr)):
            os.set_blocking(stream.fileno(), False)
            selector.register(stream, selectors.EVENT_READ, name)
        deadline = time.monotonic() + WALL_SECONDS
        while selector.get_map():
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                code = 'timeout'; break
            for key, _ in selector.select(min(0.2, remaining)):
                block = os.read(key.fileobj.fileno(), min(65536, MAX_CAPTURE_BYTES - total + 1))
                if not block:
                    selector.unregister(key.fileobj)
                    continue
                total += len(block)
                if total > MAX_CAPTURE_BYTES:
                    code = 'output_limit'; break
                chunks[key.data].append(block)
            if code != 'none':
                break
        if code == 'none':
            try:
                process.wait(timeout=max(0.001, deadline - time.monotonic()))
            except subprocess.TimeoutExpired:
                code = 'timeout'
    except BaseException:
        code = 'child_launch_failed' if process is None else 'test_runner_failed'
    finally:
        selector.close()
        if process is not None:
            if process.poll() is None:
                try:
                    process.kill()
                except ProcessLookupError:
                    pass
                except OSError:
                    code = 'child_cleanup_failed'
            try:
                process.wait(timeout=5)
            except BaseException:
                code = 'child_cleanup_failed'
            for stream in (process.stdout, process.stderr):
                if stream is not None:
                    stream.close()
    return {'error_code': code, 'child_exit_code': process.returncode if process is not None else None,
            'capture_status': ('not_started' if process is None else 'completed' if code == 'none'
                else code if code in {'timeout', 'output_limit'} else 'failed'),
            'stdout': b''.join(chunks['stdout']), 'stderr': b''.join(chunks['stderr'])}


def parse_original_cli(captured):
    result = base_report(True)
    result['child_exit_code'] = captured['child_exit_code']
    result['capture_status'] = captured['capture_status']
    if captured['error_code'] != 'none':
        result['error_code'] = captured['error_code']
        return sanitize_report(result)
    lines = captured['stderr'].decode('utf-8', errors='replace').splitlines()
    runs = [re.fullmatch(r'Ran ([0-9]+) tests? in [0-9.]+s', line) for line in lines]
    runs = [match for match in runs if match]
    endings = [line for line in lines if line.startswith('OK') or line.startswith('FAILED')]
    nonempty = [line for line in lines if line.strip()]
    result['error_code'] = 'parser_error'
    if len(runs) != 1 or int(runs[0][1]) != EXPECTED_COUNT or len(endings) != 1 or not nonempty or nonempty[-1] != endings[0]:
        return sanitize_report(result)
    failed, errors = [], []
    for line in lines:
        if not line.startswith(('FAIL:', 'ERROR:')):
            continue
        header = re.fullmatch(r'(FAIL|ERROR): (test_[A-Za-z0-9_]+) \(([^)\r\n]+)\)(?: .*)?', line)
        if not header:
            result['error_code'] = 'unknown_test_id'; return sanitize_report(result)
        method, parent = header[2], header[3]
        name = parent if parent.endswith('.' + method) else parent + '.' + method
        if name not in EXPECTED_TEST_IDS:
            result['error_code'] = 'unknown_test_id'; return sanitize_report(result)
        (failed if header[1] == 'FAIL' else errors).append(name)
    footer = endings[0]
    counts = {'failures': 0, 'errors': 0, 'skipped': 0}
    ok = re.fullmatch(r'OK(?: \(skipped=([0-9]+)\))?', footer)
    bad = re.fullmatch(r'FAILED \(([^)]*)\)', footer)
    if ok:
        counts['skipped'] = int(ok[1] or 0)
        if failed or errors or captured['child_exit_code'] != 0:
            return sanitize_report(result)
    elif bad:
        seen = set()
        for part in bad[1].split(', '):
            item = re.fullmatch(r'(failures|errors|skipped)=([0-9]+)', part)
            if not item or item[1] in seen:
                return sanitize_report(result)
            seen.add(item[1]); counts[item[1]] = int(item[2])
        if (captured['child_exit_code'] != 1 or not (failed or errors)
                or counts['failures'] != len(failed) or counts['errors'] != len(errors)):
            return sanitize_report(result)
    else:
        return sanitize_report(result)
    if counts['skipped'] > EXPECTED_COUNT or len(failed) > 4096 or len(errors) > 4096:
        return sanitize_report(result)
    result.update(status='passed' if ok else 'failed', error_code='none' if ok else 'test_failures',
        tests_run=EXPECTED_COUNT, failed_test_ids=sorted(set(failed)), error_test_ids=sorted(set(errors)),
        failures=len(set(failed)), errors=len(set(errors)), failure_events=len(failed), error_events=len(errors),
        skipped=counts['skipped'], unattributed_skips=counts['skipped'])
    return sanitize_report(result)


def run_fixed_suite():
    verified, captured = False, None
    try:
        verified = verify_suite_identity()
        if not verified:
            result = base_report(); result['error_code'] = 'test_suite_mismatch'
            return sanitize_report(result)
        captured = capture_original_cli()
        return parse_original_cli(captured)
    except BaseException:
        result = base_report(verified)
        if captured is not None:
            result.update(capture_status='failed', child_exit_code=captured.get('child_exit_code'))
        return sanitize_report(result)


def main(argv=None):
    args = sys.argv[1:] if argv is None else argv
    if args:
        report = base_report(); report['error_code'] = 'test_suite_mismatch'
    else:
        report = run_fixed_suite()
    print(json.dumps(sanitize_report(report), sort_keys=True), flush=True)
    return 0 if report['status'] == 'passed' else 1


if __name__ == '__main__':
    raise SystemExit(main())
