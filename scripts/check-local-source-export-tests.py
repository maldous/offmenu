#!/usr/bin/env python3
"""Exact export-test CLI diagnostic; reuse the reviewed bounded private capture."""
import importlib.util
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location('fixed_existing_test_reporter', ROOT / 'manual-action/check_source_access_handoff_tests.py')
BASE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(BASE)
SCHEMA = 'offmenu-local-source-tests/1'
BASE.SCHEMA = SCHEMA
BASE.TEST_DIRECTORY = ROOT / 'tests'
BASE.TEST_PATTERN = 'test_local_source_export.py'
BASE.TEST_SUITE_SHA = 'c226da285026cd7f226b099260a48a09df864e58cc167bb2ea15fcc42d464512'
BASE.EXPECTED_TEST_IDS = frozenset(('test_local_source_export.InventorySizeAccounting.test_metadata_totals_can_exceed_selected_transfer_cap', 'test_local_source_export.SourceExport.test_boolean_is_not_an_integer_in_schema', 'test_local_source_export.SourceExport.test_bounded_read_rejects_oversized_file', 'test_local_source_export.SourceExport.test_chunk_boundary_secret_is_rejected_before_packet_creation', 'test_local_source_export.SourceExport.test_chunking_preserves_utf8_bytes_across_split_boundary', 'test_local_source_export.SourceExport.test_complete_packet_set_accepts_exact_reassembly_in_any_packet_order', 'test_local_source_export.SourceExport.test_complete_packet_set_rejects_chunk_digest_rewritten_but_whole_digest_wrong', 'test_local_source_export.SourceExport.test_complete_packet_set_rejects_cross_packet_duplicate_chunk', 'test_local_source_export.SourceExport.test_complete_packet_set_rejects_invalid_utf8_across_whole_source', 'test_local_source_export.SourceExport.test_complete_packet_set_rejects_missing_duplicate_or_mixed_packet', 'test_local_source_export.SourceExport.test_complete_packet_set_scans_secret_across_chunk_boundaries', 'test_local_source_export.SourceExport.test_duplicate_selection_source_or_destination_rejected', 'test_local_source_export.SourceExport.test_empty_source_has_one_explicit_empty_part', 'test_local_source_export.SourceExport.test_fifo_rejected_without_blocking', 'test_local_source_export.SourceExport.test_file_change_during_read_rejected', 'test_local_source_export.SourceExport.test_final_symlink_rejected', 'test_local_source_export.SourceExport.test_hardlink_rejected', 'test_local_source_export.SourceExport.test_inventory_complete_set_detects_omission_or_rewritten_totals', 'test_local_source_export.SourceExport.test_inventory_does_not_traverse_excluded_or_symlink_directories', 'test_local_source_export.SourceExport.test_inventory_includes_eligible_untracked_hidden_allowed_roots', 'test_local_source_export.SourceExport.test_inventory_limit_fails_instead_of_silent_omission', 'test_local_source_export.SourceExport.test_json_duplicate_keys_and_nonfinite_rejected', 'test_local_source_export.SourceExport.test_known_secret_signatures_rejected_without_disclosure', 'test_local_source_export.SourceExport.test_metadata_commands_do_not_execute_filters_or_fsmonitor_or_write_index', 'test_local_source_export.SourceExport.test_non_utf8_and_nul_text_rejected', 'test_local_source_export.SourceExport.test_packet_rejects_empty_trailing_chunk_for_nonempty_source', 'test_local_source_export.SourceExport.test_packet_strict_identity_and_unknown_fields', 'test_local_source_export.SourceExport.test_private_output_is_exclusive_and_manifest_covers_each_packet', 'test_local_source_export.SourceExport.test_private_output_rejects_incomplete_set_before_writing_directory', 'test_local_source_export.SourceExport.test_receive_artifact_no_overwrite_or_symlink', 'test_local_source_export.SourceExport.test_receive_projects_exact_artifact_and_content_free_summary', 'test_local_source_export.SourceExport.test_receive_requires_root_approved_readonly_packet', 'test_local_source_export.SourceExport.test_relative_paths_reject_traversal_hidden_secrets_and_runtime', 'test_local_source_export.SourceExport.test_selected_pin_mismatch_rejected', 'test_local_source_export.SourceExport.test_source_path_requires_exact_selected_root_prefix', 'test_local_source_export.SourceExport.test_stage_requires_explicit_root_invocation', 'test_local_source_export.SourceExport.test_summary_closed_schema_never_contains_source_content', 'test_local_source_export.SourceExport.test_symlink_ancestor_rejected', 'test_local_source_export.SourceExport.test_tampered_content_digest_rejected'))
BASE.EXPECTED_COUNT = 39
BASE.fixed_command = lambda: [sys.executable, '-I', '-B', '-m', 'unittest', 'discover', '-s', 'tests', '-p', BASE.TEST_PATTERN]
EXCEPTIONS = frozenset(('AssertionError', 'ModuleNotFoundError', 'ImportError', 'PermissionError', 'FileNotFoundError', 'OSError', 'RuntimeError', 'ValueError', 'TypeError', 'KeyError', 'Rejected', 'CalledProcessError'))
MODULE = re.compile(r'[A-Za-z_][A-Za-z0-9_]*(?:\.[A-Za-z_][A-Za-z0-9_]*){0,15}')


def sanitize_report(value):
    base = dict(value)
    kinds = base.pop('exceptionClasses', None)
    modules = base.pop('missingModuleIdentifiers', None)
    clean = BASE.sanitize_report(base)
    if (type(kinds) is not list or kinds != sorted(set(kinds)) or len(kinds) > len(EXCEPTIONS)
            or any(type(x) is not str or x not in EXCEPTIONS for x in kinds)):
        raise ValueError('invalid_diagnostic_projection')
    if (type(modules) is not list or modules != sorted(set(modules)) or len(modules) > 16
            or any(type(x) is not str or len(x) > 128 or not MODULE.fullmatch(x) for x in modules)
            or modules and 'ModuleNotFoundError' not in kinds):
        raise ValueError('invalid_diagnostic_projection')
    clean.update(exceptionClasses=kinds, missingModuleIdentifiers=modules)
    return clean


def project(captured):
    report = BASE.parse_original_cli(captured)
    kinds, modules = set(), set()
    for line in captured['stderr'].decode('utf-8', errors='replace').splitlines():
        match = re.fullmatch(r'(?:[A-Za-z_][A-Za-z0-9_]*\.)*([A-Za-z_][A-Za-z0-9_]*):.*', line)
        if match and match[1] in EXCEPTIONS:
            kinds.add(match[1])
        missing = re.fullmatch(r"ModuleNotFoundError: No module named '([A-Za-z_][A-Za-z0-9_.]*)'", line)
        if missing and len(missing[1]) <= 128 and MODULE.fullmatch(missing[1]):
            modules.add(missing[1])
    report.update(exceptionClasses=sorted(kinds), missingModuleIdentifiers=sorted(modules))
    return sanitize_report(report)


def main(argv=None):
    args = sys.argv[1:] if argv is None else argv
    try:
        if args or not BASE.verify_suite_identity():
            report = BASE.base_report(); report['error_code'] = 'test_suite_mismatch'
            report.update(exceptionClasses=[], missingModuleIdentifiers=[])
        else:
            report = project(BASE.capture_original_cli())
        report = sanitize_report(report)
    except BaseException:
        report = BASE.base_report(); report['error_code'] = 'test_runner_failed'
        report.update(exceptionClasses=[], missingModuleIdentifiers=[])
    print(json.dumps(report, sort_keys=True), flush=True)
    return 0 if report['status'] == 'passed' else 1


if __name__ == '__main__':
    raise SystemExit(main())
