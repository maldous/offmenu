"""Finite public receipt protocol for bounded, candidate-only reconciliation.

No source keys, identifiers, paths, source/reviewer text, or exception text can
enter this protocol. Cache exhaustion is not global semantic or gold completion.
"""
from __future__ import annotations

from normalization_receipts import (
    DOMAINS, STAMP, canonical, _exact, _count, _hex, progress_digest,
)

COUNTS = ('scanned', 'indexed_new', 'indexed_reused', 'quarantined', 'quarantine_retries')
STOPS = (None, 'disk_reserve', 'wall_time_cap', 'cancelled', 'row_cap',
         'output_cap', 'capacity_limit', 'snapshot_changed', 'store_unavailable',
         'resource_failure')
OUTCOMES = {'running': 'running', 'partial': 'partial',
            'cache_complete': 'completed', 'failed': 'blocked'}


def validate_report(value):
    _exact(value, ('schema', 'input_sha256', 'policy_sha256', 'status', 'stop_reason',
        'selection', 'integrity_reads', 'review_status', 'gold_status',
        'entity_merges', 'domains', 'resources', 'capacity'))
    if (value['schema'] != 'offmenu-db-reconciliation-report/1'
            or value['status'] not in OUTCOMES
            or value['stop_reason'] not in STOPS
            or value['selection'] != 'committed_compact_cache_keys'
            or value['integrity_reads'] != 'fixed_staging_database_payload_and_projection_validation'
            or value['review_status'] != 'pending_approved_route'
            or value['gold_status'] != 'blocked'
            or type(value['entity_merges']) is not int or value['entity_merges'] != 0):
        raise ValueError('invalid_reconciliation_public_status')
    _hex(value['input_sha256']); _hex(value['policy_sha256'])
    _exact(value['domains'], DOMAINS)
    for row in value['domains'].values():
        _exact(row, ('status', 'selected_keys', *COUNTS, 'exhausted', 'checkpoint_sha256'))
        if (row['status'] not in ('pending', 'running', 'partial', 'cache_complete', 'unavailable')
                or row['selected_keys'] is not None or type(row['exhausted']) is not bool):
            raise ValueError('invalid_reconciliation_domain_status')
        for key in COUNTS:
            _count(row[key])
        _hex(row['checkpoint_sha256'], nullable=True)
        if (row['scanned'] != row['indexed_new'] + row['indexed_reused'] + row['quarantined']
                or row['quarantine_retries'] > row['scanned']):
            raise ValueError('inconsistent_reconciliation_public_counts')
        if row['status'] == 'cache_complete' and (not row['exhausted'] or row['quarantined']):
            raise ValueError('unfinished_reconciliation_domain_refused')
    if value['status'] == 'cache_complete' and (value['stop_reason'] is not None
            or any(row['status'] != 'cache_complete' for row in value['domains'].values())):
        raise ValueError('unfinished_reconciliation_completion_refused')
    resources = value['resources']
    _exact(resources, ('free_disk_bytes', 'elapsed_seconds', 'workers',
                       'invocation_rows', 'output_logical_bytes'))
    _count(resources['free_disk_bytes'], nullable=True)
    for key in ('elapsed_seconds', 'invocation_rows', 'output_logical_bytes'):
        _count(resources[key])
    if type(resources['workers']) is not int or resources['workers'] != 1:
        raise ValueError('invalid_reconciliation_worker_count')
    capacity = value['capacity']
    _exact(capacity, ('status', 'sample_rows', 'sample_output_bytes',
        'bytes_per_row_ceiling', 'admitted_rows', 'max_rows', 'max_output_bytes'))
    if capacity['status'] not in ('sampling', 'admitted', 'insufficient', 'not_needed', 'unavailable'):
        raise ValueError('invalid_reconciliation_capacity_status')
    for key in ('sample_rows', 'sample_output_bytes', 'admitted_rows', 'max_rows', 'max_output_bytes'):
        _count(capacity[key])
    _count(capacity['bytes_per_row_ceiling'], nullable=True)
    if (not 1 <= capacity['max_rows'] <= 10**6
            or not 1 <= capacity['max_output_bytes'] <= 1024**3
            or resources['invocation_rows'] > capacity['max_rows']
            or capacity['admitted_rows'] > capacity['max_rows']
            or capacity['sample_rows'] > resources['invocation_rows']):
        raise ValueError('invalid_reconciliation_capacity_bound')
    if len(canonical(value)) > 32768:
        raise ValueError('reconciliation_public_size_limit')
    return value


def build_summary(report, evidence_ref=None):
    result = {'binding': 'reconciliation_candidates_not_verified_merges_or_gold',
              'report': validate_report(report)}
    if evidence_ref is not None:
        result['evidence_ref'] = evidence_ref
    result['progress_sha256'] = progress_digest(result)
    return result


def validate_receipt(value):
    _exact(value, ('schema', 'job_id', 'job_version', 'operation', 'job_key',
        'implementation_sha256', 'input_sha256', 'observed_at', 'outcome', 'reconciliation'))
    if (value['schema'] != 'offmenu-run-receipt/4'
            or value['job_id'] != 'retained-six-domain-reconciliation'
            or value['operation'] != 'reconcile_normalized_cache'
            or type(value['job_version']) is not int or not 1 <= value['job_version'] <= 1000000
            or value['outcome'] not in OUTCOMES.values()
            or not isinstance(value['observed_at'], str) or not STAMP.fullmatch(value['observed_at'])):
        raise ValueError('invalid_reconciliation_receipt')
    for key in ('job_key', 'implementation_sha256', 'input_sha256'):
        _hex(value[key])
    summary = value['reconciliation']
    _exact(summary, ('binding', 'report', 'progress_sha256'), ('evidence_ref',))
    if summary['binding'] != 'reconciliation_candidates_not_verified_merges_or_gold':
        raise ValueError('invalid_reconciliation_binding')
    report = validate_report(summary['report'])
    if report['input_sha256'] != value['input_sha256']:
        raise ValueError('reconciliation_input_binding_mismatch')
    if 'evidence_ref' in summary:
        ref = summary['evidence_ref']
        _exact(ref, ('schema', 'sha256', 'bytes'))
        _hex(ref['sha256'])
        if ref['schema'] != 'offmenu-ingest-evidence-ref/1' or type(ref['bytes']) is not int or not 1 <= ref['bytes'] <= 65536:
            raise ValueError('invalid_reconciliation_evidence_reference')
    if summary['progress_sha256'] != progress_digest(summary):
        raise ValueError('invalid_reconciliation_progress_digest')
    if value['outcome'] != OUTCOMES[report['status']]:
        raise ValueError('invalid_reconciliation_stage_outcome')
    if len(canonical({'sha256': '0' * 64, 'receipt': value})) > 65536:
        raise ValueError('reconciliation_receipt_size_limit')
    return value
