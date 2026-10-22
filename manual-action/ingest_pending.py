"""Metadata-only queue visibility; this module never ingests or opens stores writable.

Counts are source/domain assignments, not eight app-bound databases or entities.
Expected counts must describe adapter-output ordinals for the exact source version.
No historical hints, row COUNT(*), payload scans, or whole-file hashes are used.
"""
from __future__ import annotations
import hashlib
from contextlib import closing
import json
from pathlib import Path
import re
import sqlite3

from ingest_api import DOMAINS, APP_MANAGED_DOMAINS, source_key
from ingest_store import SCHEMA_VERSION, _fingerprint, _json

SCHEMA = 'offmenu-pending-work/1'
BINDING = 'additive_staging_not_app_bound'
STATES = ('completed', 'reused', 'not_yet_read', 'partial', 'failed', 'unsupported',
          'held', 'unqualified', 'awaiting_input', 'unknown')
COUNTS = ('assignments_total', *STATES, 'files_remaining', 'source_bytes_known',
          'source_bytes_unknown', 'records_remaining_known', 'records_remaining_unknown')
NULLABLE = ('records_remaining', 'records_to_write', 'processed_bytes')
REASONS = frozenset(('current_version_complete', 'verified_native_reference', 'not_yet_read',
    'resume_from_cursor', 'failed_source', 'unsupported_source', 'held_by_catalog',
    'unqualified_catalog_entry', 'awaiting_user_input', 'metadata_unavailable',
    'source_version_changed', 'source_missing', 'native_reference_unverified',
    'catalog_loaded_claim_unverified', 'read_complete_errors_need_review', 'domain_failed',
    'domain_resource_cap', 'no_recognized_records'))
ERROR_CODES = frozenset(('ValueError', 'TypeError', 'RuntimeError', 'OSError', 'FileNotFoundError',
    'PermissionError', 'UnicodeDecodeError', 'JSONDecodeError', 'OperationalError', 'DatabaseError',
    'IntegrityError', 'SourceChanged', 'BudgetExceeded', 'UnsupportedSource',
    'UnsupportedSupplierSource', 'metadata_unavailable'))


def _integer(value):
    return value if type(value) is int and value >= 0 else 0


def _nullable(value):
    return value if type(value) is int and value >= 0 else None


def _blank():
    return {**dict.fromkeys(COUNTS, 0), **dict.fromkeys(NULLABLE, None)}


def sanitize_pending_work(value):
    """Fixed keys only: no raw source paths, names, providers or exception text."""
    value = value if isinstance(value, dict) else {}
    result = {'schema': SCHEMA, 'status': 'available' if value.get('status') == 'available' else 'unknown',
        'binding': BINDING, 'catalog_complete': value.get('catalog_complete') is True,
        'catalog_sources': _integer(value.get('catalog_sources')),
        'unassigned_sources': _integer(value.get('unassigned_sources')),
        'awaiting_input_domains': [d for d in ('user_profiles', 'inventory') if isinstance(value.get('awaiting_input_domains'), list) and d in value['awaiting_input_domains']],
        'domains': {}, 'totals': {}}
    raw_domains = value.get('domains') if isinstance(value.get('domains'), dict) else {}
    for key in (*DOMAINS, 'totals'):
        row = value.get('totals') if key == 'totals' else raw_domains.get(key)
        row = row if isinstance(row, dict) else {}
        clean = {**{k: _integer(row.get(k)) for k in COUNTS},
                 **{k: _nullable(row.get(k)) for k in NULLABLE}}
        if key == 'totals':
            result[key] = clean
        else:
            result['domains'][key] = clean
    # Optional extension: historical pending-work/1 values retain exact bytes.
    if 'scope' in value:
        counts = value['scope'].get('app_managed_assignments', {}) if isinstance(value['scope'], dict) else {}
        counts = counts if isinstance(counts, dict) else {}
        result['scope'] = {'policy': 'external_ingest_only',
            'app_managed_assignments': {d: _integer(counts.get(d)) for d in APP_MANAGED_DOMAINS}}
    return result


def store_path(state_dir, domain):
    return Path(state_dir).absolute() / ('private-household' if domain in ('user_profiles', 'inventory') else '.') / 'staging' / (domain + '.sqlite3')


def output_identity(path):
    """Cheap replacement/modification guard, NOT integrity or content verification."""
    path = Path(path).absolute()
    if any(p.is_symlink() for p in (path, *path.parents)):
        raise ValueError('unsafe_output_path')
    def identity(p):
        st = p.stat()
        if not p.is_file():
            raise ValueError('output_not_regular')
        return [st.st_dev, st.st_ino, st.st_size, st.st_mtime_ns]
    result = {'main': identity(path), 'wal': None}
    wal = Path(str(path) + '-wal')
    if wal.is_symlink():
        raise ValueError('unsafe_output_path')
    if wal.exists():
        result['wal'] = identity(wal)
    return result


def _read_store(path, domain, sources):
    """Read source checkpoint rows and tiny native-reference records, not datasets."""
    if any(p.is_symlink() for p in (path, *path.parents)):
        raise ValueError('unsafe_output_path')
    if not path.exists():
        return [], {}, False
    with closing(sqlite3.connect(path.as_uri() + '?mode=ro', uri=True, timeout=.25)) as db:
        db.execute('PRAGMA query_only=ON')
        db.execute('PRAGMA trusted_schema=OFF')
        meta = dict(db.execute('SELECT key,value FROM ingest_meta'))
        if meta.get('domain') != domain or meta.get('binding') != BINDING or meta.get('schema_version') != str(SCHEMA_VERSION):
            raise ValueError('unowned_store')
        db.row_factory = sqlite3.Row
        rows = [dict(row) for row in db.execute('SELECT source_key,version,path,fingerprint_json,status,cursor,written,errors FROM sources')]
        refs = {}
        # Native bridge records have deterministic record IDs and contain only
        # schema/count evidence. Read at most one indexed row for each source.
        if domain == 'barcodes':
            native_ids = {}
            for source in sources:
                if source.get('existing_store') or source.get('format') == 'sqlite':
                    native_ids.setdefault(str(Path(source['path']).absolute()), []).append('existing:' + source_key(source))
            for row in rows:
                if row['status'] != 'complete':
                    continue
                for record_id in native_ids.get(row['path'], []):
                    record = db.execute('SELECT payload_json FROM records WHERE source_key=? AND source_version=? AND record_id=?',
                                        (row['source_key'], row['version'], record_id)).fetchone()
                    if record and len(record[0]) <= 4 * 1024 * 1024:
                        try:
                            value = json.loads(record[0])
                            if value.get('kind') == 'readonly_source_reference':
                                refs[(row['source_key'], row['version'])] = value
                        except (ValueError, TypeError, AttributeError):
                            pass
    return rows, refs, True


def _expected(source, domain, version):
    """Never interpret historical counts, bytes, or raw-row counts as output rows."""
    value = source.get('expected_records')
    if (isinstance(value, dict) and value.get('reliable') is True and
        value.get('unit') == 'adapter_records' and value.get('domain') == domain and
        value.get('source_version') == version and type(value.get('count')) is int and value['count'] >= 0):
        return value['count']
    return None


def _disposition(source, domain):
    disposition = source.get('disposition')
    meta = source.get('metadata') if isinstance(source.get('metadata'), dict) else {}
    if domain in ('user_profiles', 'inventory') and not (meta.get('user_supplied') is True and meta.get('household_scope') is True):
        return 'awaiting_input', 'awaiting_user_input'
    if (source.get('restricted') and domain not in ('user_profiles', 'inventory')) or source.get('incomplete') or disposition in ('restricted', 'restricted-held', 'blocked', 'incomplete-hold', 'skip'):
        return 'held', 'held_by_catalog'
    if disposition in ('documentation', 'metadata-only', 'duplicate', 'excluded', 'historical-demo', 'unclassified', 'deferred'):
        return 'unqualified', 'unqualified_catalog_entry'
    if disposition == 'unsupported':
        return 'unsupported', 'unsupported_source'
    if disposition in ('missing', 'unreadable'):
        return 'failed', 'source_missing' if disposition == 'missing' else 'metadata_unavailable'
    return None


def collect_pending_work(sources, state_dir, *, results=None, catalog_complete=True, adapter_versions=None, previous=None):
    """Return {'summary': allowlisted counters, 'sources': private detail}.

    Failures affect visibility, never ingestion eligibility. Existing sources
    metadata is O(catalog/checkpoints); no COUNT(records) or record scan occurs.
    """
    sources = list(sources)
    results = results or {}
    adapter_versions = adapter_versions or {}
    summary = {'schema': SCHEMA, 'status': 'available', 'binding': BINDING,
        'catalog_complete': bool(catalog_complete), 'catalog_sources': len(sources),
        'unassigned_sources': 0, 'awaiting_input_domains': [], 'domains': {d: _blank() for d in DOMAINS}, 'totals': _blank(),
        'scope': {'policy': 'external_ingest_only', 'app_managed_assignments': dict.fromkeys(APP_MANAGED_DOMAINS, 0)}}
    details = []
    prior_details = {(r.get('domain'), r.get('source_key'), r.get('source_version')): r for r in (previous or []) if isinstance(r, dict) and r.get('source_version')}
    assigned = set()
    for domain in DOMAINS:
        aggregate = summary['domains'][domain]
        selected = []
        for index, source in enumerate(sources):
            domains = source.get('domains', source.get('domain', []))
            if isinstance(domains, str):
                domains = [domains]
            if isinstance(domains, (list, tuple)) and domain in domains:
                selected.append(source)
                assigned.add(index)
        if domain in APP_MANAGED_DOMAINS:
            # Retain every catalog assignment as private custody metadata, but
            # never stat/read its source or count it as missing external work.
            summary['scope']['app_managed_assignments'][domain] = len(selected)
            for source in selected:
                details.append({'source_key': source_key(source), 'domain': domain,
                    'path': source.get('path'), 'provider': source.get('provider'),
                    'disposition': source.get('disposition'), 'status': 'schema_only',
                    'scope': 'app_managed', 'next_reason': 'app_managed',
                    'excluded_from_pending': True, 'source_version': None})
            aggregate['records_remaining'] = 0
            aggregate['records_to_write'] = 0
            continue
        try:
            checkpoints, references, exists = _read_store(store_path(state_dir, domain), domain, selected)
            metadata_error = False
        except (OSError, ValueError, TypeError, sqlite3.Error):
            checkpoints, references, exists, metadata_error = [], {}, False, True
            summary['status'] = 'unknown'
        by_path = {}
        for row in checkpoints:
            by_path.setdefault(row['path'], []).append(row)
        domain_result = results.get(domain, {})
        runtime = {r.get('source_key'): r for r in domain_result.get('sources', []) if isinstance(r, dict)}
        # Verified reusable native providers allow a same-run adapter to report
        # reuse of a raw provider export. A loaded flag alone is never proof.
        verified_providers = set()
        for source in selected:
            if domain != 'barcodes' or not (source.get('existing_store') or source.get('format') == 'sqlite'):
                continue
            try:
                fp = _fingerprint(source)
                version = hashlib.sha256(_json(fp).encode()).hexdigest()
                for row in by_path.get(fp['path'], []):
                    ref = references.get((row['source_key'], row['version']), {})
                    if row['version'] == version and ref.get('binding_status') == 'verified':
                        verified_providers.add(str(source.get('provider') or '').lower())
            except (OSError, ValueError, TypeError, KeyError):
                pass
        for source in selected:
            detail = {'source_key': source_key(source), 'domain': domain,
                'path': source.get('path'), 'provider': source.get('provider'),
                'disposition': source.get('disposition'), 'status': 'not_yet_read',
                'next_reason': 'not_yet_read', 'source_version': None,
                'cursor': None, 'written': None, 'errors': None, 'read_complete': False,
                'source_bytes': None, 'processed_bytes': None,
                'expected_records': None, 'records_remaining': None, 'records_to_write': None,
                'error_codes': []}
            policy = _disposition(source, domain)
            if policy:
                detail['status'], detail['next_reason'] = policy
            row = None
            try:
                descriptor = dict(source, adapter_version=(source.get('adapter_version', 1) if source.get('acquired_adapter') else adapter_versions.get(domain, source.get('adapter_version', 1))))
                fp = _fingerprint(descriptor)
                version = hashlib.sha256(_json(fp).encode()).hexdigest()
                detail.update(source_version=version, source_bytes=fp['size'])
                keys = {source_key(source)}
                if domain == 'ingredients' and source.get('id') is not None:
                    keys.add(source_key(dict(source, id=str(source['id']) + ':ingredient-derivation')))
                candidates = [r for r in by_path.get(fp['path'], []) if r['source_key'] in keys or
                    references.get((r['source_key'], r['version']), {}).get('id') == 'existing:' + source_key(source)]
                current = [r for r in candidates if r['version'] == version]
                row = next((r for r in current if r['source_key'] == source_key(source)), current[-1] if current else None)
                if row:
                    detail.update(stored_source_key=row['source_key'], stored_source_version=row['version'],
                                  cursor=_integer(row['cursor']), written=_integer(row['written']), errors=_integer(row['errors']),
                                  read_complete=row['status'] in ('complete', 'complete_with_errors'))
                if not policy:
                    if metadata_error:
                        detail.update(status='unknown', next_reason='metadata_unavailable')
                    elif row:
                        if row['status'] == 'complete' and not row['errors']:
                            detail.update(status='completed', next_reason='current_version_complete')
                        elif row['status'] == 'complete_with_errors':
                            detail.update(status='partial', next_reason='read_complete_errors_need_review')
                        elif row['status'] == 'failed':
                            detail.update(status='failed', next_reason='failed_source')
                        elif row['cursor'] or row['written']:
                            detail.update(status='partial', next_reason='resume_from_cursor')
                        else:
                            detail.update(status='partial', next_reason='resume_from_cursor')
                        ref = references.get((row['source_key'], row['version']))
                        if ref:
                            if ref.get('binding_status') == 'verified':
                                detail.update(status='reused', next_reason='verified_native_reference')
                            else:
                                detail.update(status='unqualified', next_reason='native_reference_unverified')
                    elif candidates:
                        detail.update(next_reason='source_version_changed')
                    elif source.get('loaded') and not source.get('existing_store') and source.get('format') != 'sqlite':
                        detail.update(status='unqualified', next_reason='catalog_loaded_claim_unverified')
                detail['expected_records'] = _expected(source, domain, version)
            except (OSError, ValueError, TypeError, KeyError) as exc:
                detail['error_codes'] = [type(exc).__name__] if type(exc).__name__ in ERROR_CODES else ['metadata_unavailable']
                if not policy:
                    detail.update(status='failed' if isinstance(exc, FileNotFoundError) else 'unknown',
                                  next_reason='source_missing' if isinstance(exc, FileNotFoundError) else 'metadata_unavailable')
                if detail['status'] == 'unknown':
                    summary['status'] = 'unknown'
            old = prior_details.get((domain, source_key(source), detail['source_version']))
            if old and not policy and old.get('status') == 'reused' and str(source.get('provider') or '').lower() in verified_providers:
                detail.update(status='reused', next_reason='verified_native_reference')
            if old and not policy and old.get('status') in ('unsupported', 'failed', 'unqualified') and (not row or detail['cursor'] == old.get('cursor')):
                detail['status'] = old['status']
                detail['next_reason'] = old.get('next_reason') if old.get('next_reason') in REASONS else 'metadata_unavailable'
            observed = runtime.get(source_key(source))
            if row and row['source_key'] in runtime:
                observed = runtime[row['source_key']]
            if observed and observed.get('source_version') not in (None, detail['source_version']):
                observed = None
            # Current-run results disambiguate EOF-with-no-recognized-output and
            # adapter failures which were not represented by a durable cursor.
            if observed and not policy:
                if observed.get('reason') == 'existing_binding_reused' and str(source.get('provider') or '').lower() in verified_providers:
                    detail.update(status='reused', next_reason='verified_native_reference')
                elif observed.get('status') == 'failed':
                    detail.update(status='failed', next_reason='failed_source')
                elif observed.get('reason') in ('unsupported_source', 'unsupported_format', 'unsupported_supplier_format', 'no_recognized_records') or observed.get('status') == 'unsupported':
                    detail.update(status='unsupported', next_reason='no_recognized_records' if observed.get('reason') == 'no_recognized_records' else 'unsupported_source')
                elif observed.get('status') == 'partial' and detail['status'] not in ('held', 'unqualified', 'awaiting_input'):
                    detail.update(status='partial', next_reason='read_complete_errors_need_review' if detail['read_complete'] else 'resume_from_cursor')
                code = observed.get('error_class')
                if code in ERROR_CODES:
                    detail['error_codes'].append(code)
            elif not row and not policy and domain_result.get('status') == 'failed':
                detail.update(status='failed', next_reason='domain_failed')
            complete = detail['status'] in ('completed', 'reused')
            if complete or detail['read_complete']:
                detail['records_remaining'] = 0
            elif detail['expected_records'] is not None and detail['cursor'] is not None and detail['expected_records'] >= detail['cursor']:
                detail['records_remaining'] = detail['expected_records'] - detail['cursor']
            elif detail['expected_records'] is not None and detail['status'] == 'not_yet_read':
                detail['records_remaining'] = detail['expected_records']
            if complete:
                detail['records_to_write'] = 0
            aggregate['assignments_total'] += 1
            aggregate[detail['status']] += 1
            if detail['status'] not in ('completed', 'reused', 'held', 'unqualified', 'awaiting_input') and not detail['read_complete']:
                aggregate['files_remaining'] += 1
            if detail['source_bytes'] is None:
                aggregate['source_bytes_unknown'] += 1
            else:
                aggregate['source_bytes_known'] += detail['source_bytes']
            if detail['records_remaining'] is None:
                aggregate['records_remaining_unknown'] += 1
            else:
                aggregate['records_remaining_known'] += detail['records_remaining']
            details.append(detail)
        aggregate['records_remaining'] = aggregate['records_remaining_known'] if aggregate['records_remaining_unknown'] == 0 else None
        aggregate['records_to_write'] = 0 if aggregate['assignments_total'] == aggregate['completed'] + aggregate['reused'] else None
    summary['unassigned_sources'] = len(sources) - len(assigned)
    for index, source in enumerate(sources):
        if index not in assigned:
            details.append({'source_key': source_key(source), 'domain': None, 'path': source.get('path'),
                'provider': source.get('provider'), 'disposition': source.get('disposition'),
                'status': (_disposition(source, None) or ('unqualified', 'unqualified_catalog_entry'))[0],
                'next_reason': (_disposition(source, None) or ('unqualified', 'unqualified_catalog_entry'))[1]})
    summary['totals'] = {k: sum(r[k] for r in summary['domains'].values()) for k in COUNTS}
    summary['totals'].update(records_remaining=summary['totals']['records_remaining_known'] if summary['totals']['records_remaining_unknown'] == 0 else None,
                            records_to_write=0 if all(r['records_to_write'] == 0 for r in summary['domains'].values()) else None,
                            processed_bytes=None)
    if not summary['catalog_complete']:
        summary['totals']['records_remaining'] = None
        summary['totals']['records_to_write'] = None
    return {'summary': sanitize_pending_work(summary), 'sources': details,
            'identity_basis': 'metadata_only_not_full_content_verification',
            'records_basis': 'adapter_output_ordinals_not_raw_rows_or_distinct_entities',
            'bytes_basis': 'whole_source_size_not_processed_or_remaining_bytes'}


def dashboard(summary):
    summary = sanitize_pending_work(summary)
    total = summary['totals']
    remaining = 'unknown' if total['records_remaining'] is None else str(total['records_remaining'])
    writes = 'unknown' if total['records_to_write'] is None else str(total['records_to_write'])
    return ('[pending] assignments={assignments_total} complete={completed} reused={reused} '
            'not-read={not_yet_read} partial={partial} failed={failed} unsupported={unsupported} '
            'held={held} unqualified={unqualified} awaiting-input={awaiting_input} unknown={unknown} '
            'files-to-read={files_remaining}').format(**total) + ' adapter-records-to-read=' + remaining + ' records-to-write=' + writes + ' app-managed-domains=' + ','.join(APP_MANAGED_DOMAINS)
