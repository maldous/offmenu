"""Strict bounded public counters for the DB-only normalization stage.

No source identities, payloads, paths, review text or credentials are accepted.
Rules completion never represents actual AI review, gold or application binding.
"""
from __future__ import annotations
import hashlib
import json
import re

DOMAINS = ('barcodes', 'ingredients', 'recipes', 'dietary', 'suppliers', 'citations')
COUNTS = ('scanned', 'rules_new', 'rules_reused', 'pendingreview', 'accepted',
          'rejected', 'needs_changes', 'unresolved', 'failed')
VERSION_KEYS = ('rule_version', 'template_version', 'schema_version', 'model_version', 'prompt_version')
HEX = re.compile(r'[0-9a-f]{64}\Z')
STAMP = re.compile(r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z\Z')


def canonical(value):
    return (json.dumps(value, sort_keys=True, indent=2, ensure_ascii=True) + '\n').encode()


def _exact(value, required, optional=()):
    if not isinstance(value, dict) or not set(required) <= set(value) or set(value) - set(required) - set(optional):
        raise ValueError('invalid_normalization_public_schema')


def _count(value, nullable=False):
    if nullable and value is None:
        return
    if type(value) is not int or not 0 <= value <= 10**15:
        raise ValueError('invalid_normalization_public_count')


def _hex(value, nullable=False):
    if nullable and value is None:
        return
    if not isinstance(value, str) or not HEX.fullmatch(value):
        raise ValueError('invalid_normalization_public_digest')


def validate_report(value):
    _exact(value, ('schema', 'input_sha256', 'status', 'stop_reason', 'selection',
        'source_originals', 'review_status', 'gold_status', 'versions', 'domains',
        'selected_rows_scope', 'resources'))
    if (value['schema'] != 'offmenu-db-normalization-report/1'
        or value['status'] not in ('running', 'partial', 'rules_complete', 'failed')
        or value['stop_reason'] not in (None, 'disk_reserve', 'wall_time_cap', 'cancelled',
                                       'row_cap', 'snapshot_changed', 'store_unavailable', 'worker_resource_failure')
        or value['selection'] != 'all_retained_source_versions'
        or value['source_originals'] != 'database_payload_only'
        or value['selected_rows_scope'] != 'owned_metadata_counter'
        or value['review_status'] != 'pending_approved_route'
        or value['gold_status'] != 'blocked'):
        raise ValueError('invalid_normalization_public_status')
    _hex(value['input_sha256'])
    _exact(value['versions'], VERSION_KEYS)
    for version in value['versions'].values():
        if not isinstance(version, str) or not re.fullmatch(r'[A-Za-z0-9._/+:-]{1,256}', version):
            raise ValueError('invalid_normalization_public_version')
    _exact(value['domains'], DOMAINS)
    for row in value['domains'].values():
        _exact(row, ('status', 'selected_rows', *COUNTS, 'checkpoint_sha256'))
        if row['status'] not in ('pending', 'running', 'partial', 'rules_complete', 'unavailable'):
            raise ValueError('invalid_normalization_public_status')
        _count(row['selected_rows'], nullable=True)
        _hex(row['checkpoint_sha256'], nullable=True)
        for key in COUNTS:
            _count(row[key])
        # This release has no actual-review invocation/import route. A counter
        # cannot silently turn a local rules run into a claimed AI acceptance.
        if any(row[key] for key in ('accepted', 'rejected', 'needs_changes')):
            raise ValueError('unconfigured_actual_review_claim_refused')
        if (row['scanned'] != row['rules_new']+row['rules_reused']+row['failed']
                or row['pendingreview'] != row['rules_new']+row['rules_reused']
                or row['unresolved'] > row['scanned']):
            raise ValueError('inconsistent_normalization_public_counts')
        if row['status'] == 'rules_complete' and (row['failed']
                or (row['selected_rows'] is not None and row['scanned'] != row['selected_rows'])):
            raise ValueError('unfinished_normalization_domain_refused')
    if value['status'] == 'rules_complete' and (value['stop_reason'] is not None
            or any(row['status'] != 'rules_complete' for row in value['domains'].values())):
        raise ValueError('unfinished_normalization_completion_refused')
    _exact(value['resources'], ('free_disk_bytes', 'elapsed_seconds', 'workers'))
    _count(value['resources']['free_disk_bytes'], nullable=True)
    _count(value['resources']['elapsed_seconds'])
    if type(value['resources']['workers']) is not int or not 0 <= value['resources']['workers'] <= 24:
        raise ValueError('invalid_normalization_public_workers')
    if len(canonical(value)) > 32768:
        raise ValueError('normalization_public_size_limit')
    return value


def progress_digest(summary):
    return hashlib.sha256(canonical({key: val for key, val in summary.items()
                                    if key != 'progress_sha256'})).hexdigest()


def build_summary(report, evidence_ref=None):
    result = {'binding': 'normalization_sidecars_not_gold_or_app_bound',
              'report': validate_report(report)}
    if evidence_ref is not None:
        result['evidence_ref'] = evidence_ref
    result['progress_sha256'] = progress_digest(result)
    return result


def validate_receipt(value):
    _exact(value, ('schema', 'job_id', 'job_version', 'operation', 'job_key',
        'implementation_sha256', 'input_sha256', 'observed_at', 'outcome', 'normalization'))
    if (value['schema'] != 'offmenu-run-receipt/3'
        or value['job_id'] != 'retained-six-domain-normalization'
        or value['operation'] != 'normalize_staged_databases'
        or type(value['job_version']) is not int or not 1 <= value['job_version'] <= 1000000
        or value['outcome'] not in ('running', 'completed', 'partial', 'blocked')
        or not isinstance(value['observed_at'], str) or not STAMP.fullmatch(value['observed_at'])):
        raise ValueError('invalid_normalization_receipt')
    for key in ('job_key', 'implementation_sha256', 'input_sha256'):
        _hex(value[key])
    summary = value['normalization']
    _exact(summary, ('binding', 'report', 'progress_sha256'), ('evidence_ref',))
    if summary['binding'] != 'normalization_sidecars_not_gold_or_app_bound':
        raise ValueError('invalid_normalization_binding')
    report = validate_report(summary['report'])
    if report['input_sha256'] != value['input_sha256']:
        raise ValueError('normalization_input_binding_mismatch')
    if 'evidence_ref' in summary:
        ref = summary['evidence_ref']
        _exact(ref, ('schema', 'sha256', 'bytes'))
        _hex(ref['sha256'])
        if ref['schema'] != 'offmenu-ingest-evidence-ref/1' or type(ref['bytes']) is not int or not 1 <= ref['bytes'] <= 65536:
            raise ValueError('invalid_normalization_evidence_reference')
    if summary['progress_sha256'] != progress_digest(summary):
        raise ValueError('invalid_normalization_progress_digest')
    expected = {'running': 'running', 'rules_complete': 'completed', 'partial': 'partial', 'failed': 'blocked'}
    if value['outcome'] != expected[report['status']]:
        raise ValueError('invalid_normalization_stage_outcome')
    if len(canonical({'sha256': '0' * 64, 'receipt': value})) > 65536:
        raise ValueError('normalization_receipt_size_limit')
    return value
