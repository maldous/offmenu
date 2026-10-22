"""Bounded database-only rules normalization; no source files, fetch or AI route.

All retained public source versions are selected, independently of row order.
Only owned staging DB JSON/provenance is read. A changed DB/WAL snapshot starts
that domain's new bounded PK pass with exact cache reuse; an unchanged snapshot
resumes its atomic cursor without replaying the historical prefix. This first
version does not claim change-feed incremental selection after DB mutations.
"""
from __future__ import annotations
from contextlib import closing
import copy
import hashlib
import json
import math
import os
import re
from normalization_parallel import RulesWorkerError
from pathlib import Path
import shutil
import sqlite3
import stat
import time
from normalization_api import MAX_JSON_BYTES, NormalizationError, Versions
from normalization_core import CompactNormalizationStore, canonical_json, digest, rule_cache_key
from ingest_api import DOMAINS, APP_MANAGED_DOMAINS

PUBLIC_DOMAINS = tuple(domain for domain in DOMAINS if domain not in APP_MANAGED_DOMAINS)
SCHEMA = 'offmenu-db-normalization-report/1'
COUNTERS = ('scanned', 'rules_new', 'rules_reused', 'pendingreview', 'accepted',
            'rejected', 'needs_changes', 'unresolved', 'failed')
DEFAULTS = {'workers': 16, 'batch_rows': 128, 'batch_bytes': 4 * 1024**2,
            'disk_reserve_bytes': 2 * 1024**3, 'max_seconds': 3600,
            'max_rows': 0, 'report_interval': 60}


class _Stop(RuntimeError):
    pass


def _config(config):
    raw = dict(config or {})
    if set(raw) - set(DEFAULTS) - {'versions', 'cancelled'}:
        raise ValueError('unknown_normalization_option')
    result = {**DEFAULTS, **raw}
    for key, minimum, maximum in (('workers', 1, 22), ('batch_rows', 1, 128),
            ('batch_bytes', 16384, 16 * 1024**2), ('disk_reserve_bytes', 0, 10**15),
            ('max_rows', 0, 10**15)):
        if type(result[key]) is not int or not minimum <= result[key] <= maximum:
            raise ValueError('invalid_normalization_option')
    for key, low, high in (('max_seconds', 0, 86400 * 7), ('report_interval', 0, 3600)):
        value = result[key]
        if type(value) not in (int, float) or not math.isfinite(value) or not low < value <= high:
            raise ValueError('invalid_normalization_option')
    versions = result.get('versions') or Versions()
    if isinstance(versions, dict):
        versions = Versions(**versions)
    if not isinstance(versions, Versions):
        raise ValueError('invalid_normalization_versions')
    if any(not re.fullmatch(r'[A-Za-z0-9._/+:-]{1,256}', value) for value in versions.as_dict().values()):
        raise ValueError('invalid_normalization_versions')
    result['versions'] = versions
    cancelled = result.get('cancelled')
    if cancelled is not None and not callable(getattr(cancelled, 'is_set', None)):
        raise ValueError('invalid_cancellation_event')
    return result


def _safe_path(path):
    path = Path(os.path.abspath(path))
    if any(parent.is_symlink() for parent in (path, *path.parents)):
        raise NormalizationError('symlink_staging_refused')
    return path


def _file_identity(path):
    try:
        info = path.lstat()
    except FileNotFoundError:
        return None
    if not stat.S_ISREG(info.st_mode):
        raise NormalizationError('non_regular_staging_refused')
    return [info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns, info.st_ctime_ns]


def _identity(path):
    _safe_path(path)
    # SHM is intentionally excluded: SQLite readers may legitimately update it.
    for suffix in ('-wal', '-shm', '-journal'):
        sibling = Path(str(path) + suffix)
        if sibling.is_symlink():
            raise NormalizationError('symlink_staging_refused')
    return {'database': _file_identity(path), 'wal': _file_identity(Path(str(path) + '-wal'))}


def _metadata(db, domain):
    meta = dict(db.execute("SELECT key,value FROM ingest_meta WHERE key IN ('binding','schema_version','domain','database_id','record_count')"))
    if meta.get('binding') != 'additive_staging_not_app_bound' or meta.get('schema_version') != '1' or meta.get('domain') != domain:
        raise NormalizationError('incompatible_staging')
    count = meta.get('record_count')
    meta['record_count'] = int(count) if isinstance(count, str) and count.isascii() and count.isdigit() and len(count) <= 16 and int(count) <= 10**15 else None
    if meta.get('database_id') is not None and (not isinstance(meta['database_id'], str) or len(meta['database_id']) > 256):
        raise NormalizationError('invalid_owned_database_id')
    return meta


def _open_source(path):
    db = sqlite3.connect(path.as_uri() + '?mode=ro', uri=True, timeout=2)
    db.execute('PRAGMA query_only=ON')
    db.execute('PRAGMA cache_size=-4096')
    db.execute('BEGIN')
    return db


def prepare_default(state_dir, config=None):
    """Read only six fixed DB metadata bindings, never COUNT/source paths.

    The returned object is private/opaque except input_sha256. The caller holds
    the runner lease. Admission also checks a stable SQLite read transaction;
    run_prepared rechecks the exact content-bearing snapshot on every batch.
    """
    state = _safe_path(state_dir)
    options = _config(config)
    import normalization_domains
    import normalize_recipes
    pins = {'versions': options['versions'].as_dict(), 'domain_rules': normalization_domains.RULE_VERSION,
            'recipe_rules': normalize_recipes.VERSION, 'engine_selection': 'all_retained_source_versions/1',
            'admission_bytes': options['batch_bytes']}
    domains = {}
    for domain in PUBLIC_DOMAINS:
        path = state / 'staging' / (domain + '.sqlite3')
        item = {'path': path, 'status': 'unavailable', 'selected_rows': None, 'snapshot': None}
        try:
            before = _identity(path)
            if before['database'] is not None:
                with closing(_open_source(path)) as db:
                    meta = _metadata(db, domain)
                    after = _identity(path)
                    if before != after:
                        raise NormalizationError('snapshot_changed')
                item.update(status='pending', selected_rows=meta['record_count'], snapshot={'files': after, 'metadata': meta})
        except (OSError, sqlite3.Error, NormalizationError):
            pass
        item['snapshot_key'] = digest({'domain': domain, 'snapshot': item['snapshot'], 'pins': pins})
        domains[domain] = item
    return {'state_dir': state, 'config': options, 'domains': domains,
            'input_sha256': digest({'selection': pins, 'domains': {domain: item['snapshot_key'] for domain, item in domains.items()}})}


class _Budget:
    def __init__(self, prepared):
        self.options = prepared['config']
        self.path = prepared['state_dir']
        self.started = time.monotonic()
        self.reason = None
        self.free = None
        self.sampled = -float('inf')
        self.rows = 0
        self.workers = 0

    def latch(self, reason):
        if self.reason is None:
            self.reason = reason

    def space(self, required=0, *, enforce=True):
        try:
            self.free = shutil.disk_usage(self.path).free
            self.sampled = time.monotonic()
        except OSError:
            self.free = None
        if self.free is None:
            if enforce:
                self.latch('store_unavailable')
            return False
        if self.free < self.options['disk_reserve_bytes'] + required:
            if enforce:
                self.latch('disk_reserve')
            return False
        return True

    def check(self):
        if self.reason is not None:
            raise _Stop(self.reason)
        event = self.options.get('cancelled')
        if event is not None and event.is_set():
            self.latch('cancelled')
        elif time.monotonic() - self.started >= self.options['max_seconds']:
            self.latch('wall_time_cap')
        elif self.options['max_rows'] and self.rows >= self.options['max_rows']:
            self.latch('row_cap')
        elif time.monotonic() - self.sampled >= 1:
            self.space()
        if self.reason is not None:
            raise _Stop(self.reason)

    def resources(self):
        return {'free_disk_bytes': self.free, 'elapsed_seconds': max(0, int(time.monotonic() - self.started)), 'workers': self.workers}


def _empty_row(item):
    return {'status': item['status'], 'selected_rows': item['selected_rows'],
            **dict.fromkeys(COUNTERS, 0), 'checkpoint_sha256': None}


def _checkpoint(row, key, cursor, counters, complete):
    row.update(counters)
    row['checkpoint_sha256'] = digest({'snapshot': key, 'cursor': cursor, 'counters': counters, 'complete': complete})
    row['status'] = ('rules_complete' if not counters['failed'] and (row['selected_rows'] is None or row['selected_rows'] == counters['scanned']) else 'partial') if complete else 'partial'


def _record(row, domain):
    key, version, rid, content, payload_text, number, source_exists, license_text, provider, custody_text = row
    if payload_text is None:
        raise NormalizationError('database_payload_size_cap')
    payload = json.loads(payload_text)
    custody = json.loads(custody_text) if custody_text else None
    missing = not source_exists or not license_text or not provider or not custody
    envelope = {'domain': domain, 'source_key': key, 'source_version': version,
        'record_id': rid, 'content_sha256': content, 'payload': payload, 'row_number': number,
        'provenance': {'license': license_text, 'provider': provider, 'custody': custody,
                       'rights_status': 'unverified'}}
    if not source_exists:
        envelope['provenance']['source_metadata_status'] = 'missing'
    return envelope, missing


_QUERY = '''SELECT r.source_key,r.source_version,r.record_id,r.content_sha256,
 CASE WHEN length(CAST(r.payload_json AS BLOB))<=? THEN r.payload_json ELSE NULL END,r.row_number,
 s.source_key,CASE WHEN length(s.license)<=4096 THEN s.license ELSE NULL END,
 CASE WHEN length(s.provider)<=4096 THEN s.provider ELSE NULL END,
 CASE WHEN length(CAST(s.custody_json AS BLOB))<=? THEN s.custody_json ELSE NULL END
 FROM records r LEFT JOIN sources s ON r.source_key=s.source_key AND r.source_version=s.version
 WHERE (r.source_key,r.source_version,r.record_id) > (?,?,?)
 ORDER BY r.source_key,r.source_version,r.record_id LIMIT ?'''


def run_prepared(prepared, report_callback=None):
    """Rules-only cached progress; review never becomes optional or automatic."""
    options = prepared['config']
    budget = _Budget(prepared)
    report = {'schema': SCHEMA, 'input_sha256': prepared['input_sha256'], 'status': 'running',
        'stop_reason': None, 'selection': 'all_retained_source_versions',
        'source_originals': 'database_payload_only', 'selected_rows_scope': 'owned_metadata_counter',
        'review_status': 'pending_approved_route', 'gold_status': 'blocked',
        'versions': options['versions'].as_dict(),
        'domains': {domain: _empty_row(item) for domain, item in prepared['domains'].items()},
        'resources': budget.resources()}
    saved_complete = {}
    # Reading six owned progress rows does not require output space or create a DB.
    # A reserve stop must not erase already committed progress from the report.
    for domain, item in prepared['domains'].items():
        if item['status'] != 'unavailable':
            try:
                saved = CompactNormalizationStore.peek_checkpoint(prepared['state_dir'], domain, item['snapshot_key'])
                if saved is not None:
                    _checkpoint(report['domains'][domain], item['snapshot_key'], *saved)
                    saved_complete[domain] = saved[2]
            except (OSError, sqlite3.Error, NormalizationError, ValueError, TypeError):
                report['domains'][domain]['status'] = 'unavailable'
    last_report = -float('inf')
    def emit(force=False):
        nonlocal last_report
        report['resources'] = budget.resources()
        report['stop_reason'] = budget.reason
        if report_callback is not None and (force or time.monotonic() - last_report >= options['report_interval']):
            report_callback(copy.deepcopy(report))
            last_report = time.monotonic()
    pool = None
    try:
        budget.space(enforce=False)
        emit(True)
        for domain in PUBLIC_DOMAINS:
            item, public = prepared['domains'][domain], report['domains'][domain]
            if item['status'] == 'unavailable':
                continue
            try:
                if saved_complete.get(domain):
                    if _identity(item['path']) != item['snapshot']['files']:
                        budget.latch('snapshot_changed')
                        raise _Stop('snapshot_changed')
                    continue
                budget.check()
                if _identity(item['path']) != item['snapshot']['files']:
                    budget.latch('snapshot_changed')
                    raise _Stop('snapshot_changed')
                if not budget.space(1024**2):
                    raise _Stop(budget.reason)
                with closing(_open_source(item['path'])) as source, CompactNormalizationStore(prepared['state_dir'], domain) as store:
                    if _metadata(source, domain) != item['snapshot']['metadata'] or _identity(item['path']) != item['snapshot']['files']:
                        budget.latch('snapshot_changed')
                        raise _Stop('snapshot_changed')
                    source.set_progress_handler(lambda: int(budget.reason is not None or time.monotonic() - budget.started >= options['max_seconds'] or bool(options.get('cancelled') and options['cancelled'].is_set())), 10000)
                    cursor, counters, complete = store.checkpoint(item['snapshot_key']) or (None, dict.fromkeys(COUNTERS, 0), False)
                    _checkpoint(public, item['snapshot_key'], cursor, counters, complete)
                    if complete:
                        continue
                    work_limit = options['batch_rows']
                    while True:
                        budget.check()
                        if _identity(item['path']) != item['snapshot']['files']:
                            budget.latch('snapshot_changed')
                            raise _Stop('snapshot_changed')
                        limit = work_limit
                        if options['max_rows']:
                            limit = min(limit, options['max_rows'] - budget.rows)
                        sql = _QUERY if cursor is not None else _QUERY.replace(' WHERE (r.source_key,r.source_version,r.record_id) > (?,?,?)', '')
                        args = (min(MAX_JSON_BYTES, options['batch_bytes']), 65536, *(cursor or []), limit)
                        query = source.execute(sql, args)
                        candidates, records, entries, failures = [], [], [], []
                        staged = dict(counters)
                        read_bytes = 0
                        next_cursor = cursor
                        exhausted = True
                        for raw in query:
                            budget.check()
                            envelope = None
                            size = sum(len(value.encode('utf-8')) for value in raw if isinstance(value, str))
                            if candidates and read_bytes + size > options['batch_bytes']:
                                exhausted = False
                                break
                            read_bytes += size
                            next_cursor = list(raw[:3])
                            reference = [raw[0], raw[1], raw[2], raw[3]]
                            staged['scanned'] += 1
                            candidates.append(reference)
                            try:
                                envelope, missing = _record(raw, domain)
                                key = rule_cache_key(envelope, options['versions'])
                                cached = store.get_compact(key)
                                if cached is not None:
                                    compact, artifact_sha = cached
                                    staged['rules_reused'] += 1
                                    staged['pendingreview'] += 1
                                    staged['unresolved'] += int(missing or bool(compact['issues'] or compact['uncertainty']))
                                else:
                                    records.append((envelope, missing, key, reference))
                            except (ValueError, TypeError, KeyError, OverflowError, RecursionError):
                                staged['failed'] += 1
                                staged['unresolved'] += 1
                                failures.append((reference, 'database_record_unresolved'))
                        query.close()
                        if candidates:
                            # A LIMIT-sized response is not proof of exhaustion.
                            exhausted = exhausted and len(candidates) < limit
                        if records:
                            if pool is None:
                                from normalization_parallel import RulesExecutor
                                pool = RulesExecutor(workers=options['workers'], max_input_bytes=options['batch_bytes'],
                                    max_output_bytes=options['batch_bytes'], check_cancel=budget.check)
                                pool.__enter__()
                            from normalization_parallel import RulesBatchLimitError
                            try:
                                results = pool.run_batch([record[0] for record in records], versions=options['versions'])
                            except RulesBatchLimitError:
                                if work_limit > 1:
                                    work_limit = max(1, work_limit // 2)
                                    continue  # No writes/cursor advance; retry a smaller PK page.
                                envelope = records[0][0]
                                results = [{'source': {key: envelope[key] for key in ('domain','source_key','source_version','record_id','content_sha256')}, 'artifact': None, 'artifact_sha256': None, 'error_code': 'rules_output_limit'}]
                            budget.workers = max(budget.workers, pool.actual_workers)
                            if len(results) != len(records):
                                raise NormalizationError('rules_worker_contract')
                            for (envelope, missing, key, reference), result in zip(records, results):
                                expected = {field: envelope[field] for field in ('domain','source_key','source_version','record_id','content_sha256')}
                                if result['source'] != expected:
                                    raise NormalizationError('rules_worker_contract')
                                compact = result.get('artifact')
                                if result.get('error_code') is not None:
                                    staged['failed'] += 1
                                    staged['unresolved'] += 1
                                    failures.append((reference, 'rules_projection_unresolved'))
                                    continue
                                if compact['cache_key'] != key or compact['source'] != expected:
                                    raise NormalizationError('rules_worker_contract')
                                entries.append(CompactNormalizationStore.encode_compact(compact, result['artifact_sha256']))
                                staged['rules_new'] += 1
                                staged['pendingreview'] += 1
                                staged['unresolved'] += int(missing or bool(compact['issues'] or compact['uncertainty']))
                        budget.check()
                        if _identity(item['path']) != item['snapshot']['files']:
                            budget.latch('snapshot_changed')
                            raise _Stop('snapshot_changed')
                        # Reserve includes a conservative bounded transaction margin,
                        # not an assertion of exclusive/physical disk attribution.
                        reference_bytes = sum(len(canonical_json([reference, reason]).encode('utf-8')) + 1024
                            for reference, reason in failures)
                        cursor_bytes = len(CompactNormalizationStore._cursor_json(next_cursor).encode('utf-8'))
                        required = 1024**2 + 4 * (sum(len(entry[3]) + 1024 for entry in entries)
                            + reference_bytes + cursor_bytes)
                        if not budget.space(required):
                            raise _Stop(budget.reason)
                        store.commit_batch(item['snapshot_key'], entries, failures, next_cursor, staged, complete=exhausted)
                        cursor, counters = next_cursor, staged
                        budget.rows += len(candidates)
                        _checkpoint(public, item['snapshot_key'], cursor, counters, exhausted)
                        emit()
                        if exhausted:
                            break
            except (RulesWorkerError, MemoryError):
                budget.latch('worker_resource_failure')
                public['status'] = 'partial'
                break
            except _Stop:
                public['status'] = 'partial'
                break
            except (OSError, sqlite3.Error, NormalizationError, ValueError, TypeError, RuntimeError):
                # Source/store admission problems are isolated; no error text or
                # source identifiers enter the report and other domains continue.
                public['status'] = 'unavailable' if not public['scanned'] else 'partial'
                if options.get('cancelled') and options['cancelled'].is_set():
                    budget.latch('cancelled')
                elif time.monotonic() - budget.started >= options['max_seconds']:
                    budget.latch('wall_time_cap')
                if budget.reason:
                    break
        report['status'] = 'rules_complete' if budget.reason is None and all(row['status'] == 'rules_complete' for row in report['domains'].values()) else 'partial'
    finally:
        if pool is not None:
            budget.workers = max(budget.workers, pool.actual_workers)
            pool.__exit__(*__import__('sys').exc_info())
        report['resources'] = budget.resources()
        report['stop_reason'] = budget.reason
    emit(True)
    return report


def run_normalization(state_dir, config=None, report_callback=None):
    return run_prepared(prepare_default(state_dir, config), report_callback)
