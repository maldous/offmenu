"""Bounded parallel best-effort ingestion with serialized sanitized reporting.

Only this coordinating module invokes report_callback. Domain workers never run
Git or transmit anything. Public counts describe source rows, not distinct entities.
"""
from __future__ import annotations
from runner_paths import resolve_layout
from concurrent.futures import ThreadPoolExecutor, wait, FIRST_COMPLETED
import hashlib
from contextlib import closing
import importlib
import json
import os
from pathlib import Path
import shutil
import threading
import time
import uuid
from ingest_api import (DOMAINS, APP_MANAGED_DOMAINS, COUNTERS, BudgetExceeded, source_key,
                        GLOBAL_BUDGET_DEFAULTS, sanitize_budget_stop)
from ingest_store import DomainStore
from ingest_errors import (ERROR_CLASSES, classify_error, collect_error_snapshot,
                           sanitize_error_telemetry)
try:
    from ingest_evidence import EvidenceCollector, sanitize_evidence, summarize_diagnostics
except Exception:
    EvidenceCollector = None
    sanitize_evidence = None
    summarize_diagnostics = None
try:
    from ingest_pending import collect_pending_work, sanitize_pending_work, dashboard, output_identity, store_path
except Exception:
    # Reporting is optional visibility, never a prerequisite for loading data.
    # Keep the fallback fixed-schema and independent of the failed helper module.
    def sanitize_pending_work(value):
        fields = ('assignments_total', 'completed', 'reused', 'not_yet_read', 'partial',
            'failed', 'unsupported', 'held', 'unqualified', 'awaiting_input', 'unknown',
            'files_remaining', 'source_bytes_known', 'source_bytes_unknown',
            'records_remaining_known', 'records_remaining_unknown')
        def row():
            return {**dict.fromkeys(fields, 0), 'records_remaining': None,
                    'records_to_write': None, 'processed_bytes': None}
        return {'schema': 'offmenu-pending-work/1', 'status': 'unknown',
            'binding': 'additive_staging_not_app_bound', 'catalog_complete': False,
            'catalog_sources': 0, 'unassigned_sources': 0, 'awaiting_input_domains': [],
            'domains': {d: row() for d in DOMAINS}, 'totals': row()}

    def collect_pending_work(*args, **kwargs):
        raise ValueError('report_metadata_unavailable')

    def output_identity(path):
        raise ValueError('report_metadata_unavailable')

    def store_path(state_dir, domain):
        return resolve_layout(state_dir).domain_path(domain)

    def dashboard(summary):
        return '[pending] reporting metadata unavailable; remaining reads/writes unknown'


ADAPTERS = {'barcodes':'ingest_existing','ingredients':'ingest_recipes',
    'recipes':'ingest_recipes','dietary':'ingest_misc','user_profiles':'ingest_existing',
    'inventory':'ingest_existing','suppliers':'ingest_suppliers','citations':'ingest_misc'}
ACQUIRED_ADAPTERS = {
    'foodista_common_pile': 'ingest_acquired_recipes',
    'forkrecipe': 'ingest_acquired_recipes',
    'medlineplus_healthy_recipes': 'ingest_acquired_recipes',
    'fr_cnous_menus': 'ingest_acquired_menus',
    'fr_begles_menus': 'ingest_acquired_menus',
    'fr_toulouse_menus': 'ingest_acquired_menus',
}
REPORT_SCHEMA = 'offmenu-ingest-report/1'
DOMAIN_STATUSES = frozenset(('pending','running','complete','partial','failed','missing',
    'not_applicable','existing_loaded','schema_only','reused','imported','unavailable','awaiting_user_input'))
PUBLIC_COUNTERS = (*COUNTERS, 'sources_total','sources_complete','sources_partial','sources_skipped','reused_rows','reused_stores')
ERROR_CODES = frozenset(('ValueError','TypeError','RuntimeError','OSError','FileNotFoundError',
    'PermissionError','UnicodeDecodeError','JSONDecodeError','OperationalError','DatabaseError',
    'IntegrityError','SourceChanged','BudgetExceeded','UnsupportedSource','MalformedSupplierRow',
    'schema_uncertain','awaiting_user_input','no_recognized_sources','resource_cap','restricted_input',
    'unsupported_format','catalog_skip','source_error','partial_source','missing','unreadable',
    'already_loaded','existing_binding_reused','incomplete_source','unsupported_supplier_format','unsupported_text_compression',
    'parquet_dependency_unavailable','resource_budget','UnsupportedSupplierSource','DuplicateField'))
ERROR_CODES = ERROR_CODES | ERROR_CLASSES



def _utc():
    return time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())


def atomic_json(path, value):
    resolve_layout(Path(path).parent)
    path = Path(path)
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    if path.is_symlink() or path.parent.is_symlink():
        raise ValueError('symlink_output_refused')
    temporary = path.with_name('.' + path.name + '.' + uuid.uuid4().hex + '.tmp')
    fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as out:
            json.dump(value, out, ensure_ascii=True, sort_keys=True, indent=2, allow_nan=False)
            out.write('\n')
            out.flush()
            os.fsync(out.fileno())
        os.replace(temporary, path)
    finally:
        if temporary.exists():
            temporary.unlink()


def worker_limit(requested=8):
    limit = min(8, max(1, int(requested)), os.cpu_count() or 1)
    # Avoid starting eight parsers on a small-memory host; no dependency needed.
    try:
        with open('/proc/meminfo', encoding='ascii') as f:
            available = next(int(x.split()[1]) * 1024 for x in f if x.startswith('MemAvailable:'))
        limit = min(limit, max(1, available // (256 * 1024 * 1024)))
    except (OSError, StopIteration, ValueError):
        pass
    return limit


def _nonnegative(value):
    return value if type(value) is int and value >= 0 else 0


def sanitize_report(report):
    """Construct an allowlisted payload; free text, paths and source data cannot pass."""
    state = report.get('status')
    safe = {'schema': REPORT_SCHEMA,
        'run_id': str(report.get('run_id','')) if str(report.get('run_id','')).isalnum() else '',
        'status': state if state in ('running','complete','partial','failed') else 'partial',
        'started_at': report.get('started_at',''), 'updated_at': report.get('updated_at',''),
        'elapsed_seconds': _nonnegative(report.get('elapsed_seconds',0)),
        'workers': min(8,_nonnegative(report.get('workers',0))),
        'binding': 'additive_staging_not_app_bound',
        'records_are': 'source_provenance_rows_not_distinct_entities',
        'domains': {}}
    # Dates originate only from engine clock; validate again for external callers.
    import re
    for field in ('started_at','updated_at'):
        if not isinstance(safe[field],str) or not re.fullmatch(r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z', safe[field]):
            safe[field] = '1970-01-01T00:00:00Z'
    for domain in DOMAINS:
        row = report.get('domains',{}).get(domain,{})
        safe['domains'][domain] = {'status': row.get('status') if row.get('status') in DOMAIN_STATUSES else 'pending',
            **{key:_nonnegative(row.get(key,0)) for key in PUBLIC_COUNTERS},
            'error_codes': sorted(set(row.get('error_codes',[])) & ERROR_CODES) if isinstance(row.get('error_codes',[]),list) and all(isinstance(x,str) for x in row.get('error_codes',[])) else []}
        if domain in APP_MANAGED_DOMAINS:
            safe['domains'][domain]['scope'] = 'app_managed'
        # Unknown is not zero before the owning writer has opened the store.
        for key in ('stored_records_before', 'stored_records'):
            value = row.get(key)
            safe['domains'][domain][key] = value if type(value) is int and 0 <= value <= 10**15 else None
        if isinstance(row.get('timing'), dict):
            safe['domains'][domain]['timing'] = {key: (value if type(value) is int and 0 <= value <= 10**15 else None)
                for key in ('elapsed_ms','active_source_elapsed_ms','since_last_progress_ms','active_source_bytes','sources_timed','completed_source_elapsed_ms')
                for value in [row['timing'].get(key)]}
        if 'error_telemetry' in row:
            safe['domains'][domain]['error_telemetry'] = sanitize_error_telemetry(row['error_telemetry'])
        if 'budget_stop' in row:
            safe['domains'][domain]['budget_stop'] = sanitize_budget_stop(row['budget_stop'])
    known = [row for row in safe['domains'].values() if row['stored_records'] is not None]
    before = [row for row in safe['domains'].values() if row['stored_records_before'] is not None]
    safe['stored_totals'] = {
        'scope': 'committed_staging_source_version_rows_excludes_external_reuse',
        'snapshot_scope': 'independent_domain_checkpoints_not_atomic',
        'domains_known': len(known), 'domains_total': len(DOMAINS),
        'stored_records': sum(row['stored_records'] for row in known) if len(known) == len(DOMAINS) else None,
        'stored_records_before': sum(row['stored_records_before'] for row in before) if len(before) == len(DOMAINS) else None}
    for key in ('catalog_sha256',):
        value = report.get(key)
        if isinstance(value,str) and re.fullmatch('[a-f0-9]{64}',value):
            safe[key]=value
    safe['catalog_truncated'] = report.get('catalog_truncated') is True
    safe['report_delivery_errors'] = _nonnegative(report.get('report_delivery_errors',0))
    if 'pending_work' in report:
        safe['pending_work'] = sanitize_pending_work(report['pending_work'])
    if 'storage_sizes' in report:
        try:
            from ingest_storage_sizes import validate_storage_sizes
            safe['storage_sizes'] = validate_storage_sizes(report['storage_sizes'])
        except Exception:
            pass
    if 'relational_targets' in report:
        try:
            from ingest_relational_targets import sanitize_relational_summary
            safe['relational_targets'] = sanitize_relational_summary(report['relational_targets'])
        except Exception:
            pass
    if 'ingest_evidence' in report and sanitize_evidence is not None:
        try:
            safe['ingest_evidence'] = sanitize_evidence(report['ingest_evidence'])
        except Exception:
            pass
    return safe


def _adapter_versions(adapters=None):
    versions = {}
    for domain in DOMAINS:
        if adapters and domain in adapters:
            versions[domain] = 1
        else:
            module = importlib.import_module(ADAPTERS[domain])
            versions[domain] = getattr(module, 'ADAPTER_VERSION', getattr(module, 'VERSION', 1))
    return versions


def _pending_snapshot(sources, config, results=None, adapters=None, persist=True, private_sink=None):
    """Report metadata failures as unknown; never turn reporting into an ingest gate."""
    try:
        state = Path(config['state_dir'])
        previous = []
        path = state / 'pending-work.private.json'
        if path.is_file() and not path.is_symlink():
            try:
                with path.open(encoding='utf-8') as stream:
                    previous = json.load(stream).get('sources', [])
            except (OSError, ValueError, AttributeError):
                pass
        snapshot = collect_pending_work(sources, state, results=results,
            catalog_complete=not config.get('catalog_truncated', False),
            adapter_versions=_adapter_versions(adapters), previous=previous)
        if private_sink is not None:
            private_sink.update(snapshot)
        if persist:
            atomic_json(path, snapshot)
            atomic_json(state / 'pending-work.json', snapshot['summary'])
        return snapshot['summary']
    except Exception:
        return sanitize_pending_work({'status': 'unknown'})


def pending_snapshot(prepared, persist=True):
    """Read-only pre-load/unchanged-plan dashboard API; never starts a worker."""
    return _pending_snapshot(prepared.get('sources', []), prepared['config'], persist=persist)


class IngestContext:
    def __init__(self, domain, state_dir, config, cancelled, progress_callback, started):
        self.domain = domain
        self.state_dir = Path(state_dir)
        self.config = config
        self.cancelled = cancelled
        self.started = started
        self._progress_callback = progress_callback
        self.adapter_errors = 0
        self.private_errors = []
        self.error_classes = set()
        self.source_summaries = []
        self.store = None
        self.active_source = None
        self.budget_stop = None

    def __getitem__(self, key):
        return getattr(self,key)

    def get(self,key,default=None):
        return getattr(self,key,default)

    def check_budget(self):
        if self.budget_stop is not None:
            raise BudgetExceeded(self.budget_stop['reason'])
        seconds = float(self.config.get('max_seconds', GLOBAL_BUDGET_DEFAULTS['max_seconds']))
        reserve = int(self.config.get('reserve_bytes', GLOBAL_BUDGET_DEFAULTS['reserve_bytes']))
        elapsed = max(0, time.monotonic() - self.started)
        reason = 'cancelled' if self.cancelled.is_set() else 'wall_time_cap' if seconds > 0 and elapsed >= seconds else None
        free = None
        if reason is None:
            free = shutil.disk_usage(self.state_dir).free
            if free < reserve:
                reason = 'disk_reserve'
        if reason is not None:
            if free is None:
                try:
                    free = shutil.disk_usage(self.state_dir).free
                except OSError:
                    pass
            # Latch the first observation: a transient recovery must not let a
            # stopped domain open thousands of later sources in this invocation.
            self.budget_stop = sanitize_budget_stop({'reason': reason,
                'elapsed_ms': int(elapsed * 1000), 'disk_free_bytes': free,
                'reserve_bytes': reserve, 'max_seconds': seconds,
                'max_rows_per_source': max(0, int(self.config.get('max_rows_per_source', 0)))})
            raise BudgetExceeded(reason)

    def progress(self, **counts):
        if counts.get('event') == 'source_started' and self.active_source is not None:
            size = self.active_source.get('bytes')
            counts['source_bytes'] = size if type(size) is int and size >= 0 else None
        self._progress_callback(self.domain, counts)

    def report_skip(self, source):
        """Expected adapter skip: preserve legacy callback slots, not errors.

        Adapter-owned skipped/reason counters are attached to the source summary.
        Do not emit one coordinator event or perform SQLite I/O per lead record.
        """
        if self.store is not None:
            self.store.reserve_adapter_error_slot(source)

    def report_error(self, source, exc):
        self.adapter_errors += 1
        error_class, reason = classify_error(exc)
        self.error_classes.add(error_class)
        error = {'source_key':source_key(source),'error_class':error_class,'reason_code':reason}
        self.private_errors.append(error)
        # Keep diagnostics bounded even for large damaged files.
        if len(self.private_errors) > 1000:
            self.private_errors.pop(0)
        if self.store is not None:
            try:
                self.store.record_error(source,exc)
            except (OSError,ValueError):
                pass
        # The source key is private coordinator metadata, never a public field.
        # Do not present a domain-wide callback count as one source's row count.
        self.progress(event='adapter_error', **error)
        return error

    def ingest(self, source, records):
        # A latched global stop must not fingerprint/open/register the next
        # source, including custom handlers without their own boundary check.
        # Store-owned per-source row caps do not latch this global budget.
        self.check_budget()
        source_started = time.monotonic()
        self.active_source = source
        try:
            result=self.store.ingest(source,records)
            result['elapsed_ms'] = max(0, int((time.monotonic()-source_started)*1000))
            size = source.get('bytes')
            result['source_bytes'] = size if type(size) is int and size >= 0 else None
            self.source_summaries.append(result)
            self.progress(event='source_timed', elapsed_ms=result['elapsed_ms'])
            return result
        finally:
            self.active_source = None


def _matches(source, domain):
    domains = source.get('domains', source.get('domain', []))
    if isinstance(domains,str):
        domains = [domains]
    return domain in domains


def _run_domain(domain, sources, config, cancelled, progress, started, adapters=None):
    context = IngestContext(domain,config['state_dir'],config,cancelled,progress,started)
    progress(domain, {'event': 'domain_started'})
    try:
        with DomainStore(domain, context.state_dir, config, context.check_budget, context.progress) as store:
            context.store=store
            if domain in APP_MANAGED_DOMAINS:
                # Keep existing staging schemas/rows/counts; no external or
                # historically scoped household source is an ingest requirement.
                result = {'status': 'schema_only', 'scope': 'app_managed', 'sources': []}
            elif not sources:
                result = {'status': 'missing', 'sources': []}
            else:
                handler = (adapters or {}).get(domain)
                if handler is not None:
                    try:
                        context.check_budget()
                        result = handler(domain, sources, context)
                    except BudgetExceeded:
                        result = {'status': 'partial', 'sources': context.source_summaries,
                                  'error_codes': ['BudgetExceeded']}
                else:
                    # Each fixed adapter group is isolated. A broken acquired
                    # format cannot suppress a successful retained domain.
                    context.check_budget()
                    groups = {}
                    source_results = []
                    budget_interrupted = False
                    for source in sources:
                        acquired = source.get('acquired_source') or source.get('acquired_adapter') or isinstance(source.get('metadata'), dict) and 'acquisition' in source['metadata']
                        if acquired and source.get('disposition') in ('missing', 'unreadable'):
                            # Do not manufacture source-error bookkeeping after
                            # a global stop, even during metadata grouping.
                            context.check_budget()
                            reason = source.get('reason')
                            exc = PermissionError('acquired_cache_read_permission_denied') if reason in ('read_permission_denied', 'PermissionError') else FileNotFoundError('acquired_cache_file_missing') if source.get('disposition') == 'missing' else OSError('acquired_cache_unreadable')
                            context.report_error(source, exc)
                            source_results.append({'source_key': source_key(source), 'status': 'failed',
                                'errors': 1, 'error_class': type(exc).__name__})
                            continue
                        if acquired and source.get('acquired_adapter') not in ACQUIRED_ADAPTERS:
                            source_results.append({'source_key': source_key(source), 'status': 'unsupported',
                                'skipped': 1, 'reason': 'unsupported_format'})
                            continue
                        module = ACQUIRED_ADAPTERS.get(source.get('acquired_adapter'), ADAPTERS[domain])
                        groups.setdefault(module, []).append(source)
                    group_results = []
                    # The bounded newly acquired cohort must not wait behind
                    # a retained catalog containing hundreds of thousands of
                    # assignments. Keep one writer; preserve source identities.
                    priorities = {'ingest_acquired_menus': 0, 'ingest_acquired_recipes': 1}
                    for module_name in sorted(groups, key=lambda name: priorities.get(name, 2)):
                        selected = groups[module_name]
                        before = len(context.source_summaries)
                        try:
                            context.check_budget()
                            handler = importlib.import_module(module_name).run_domain
                            group = handler(domain, selected, context)
                            if not isinstance(group, dict):
                                raise TypeError('adapter_result_not_mapping')
                            group_results.append(group)
                            source_results.extend(group.get('sources', []))
                            # Finished acquired groups become visible while the
                            # retained tail runs. Only bounded fixed-code counts
                            # cross this callback, never rows or source paths.
                            if summarize_diagnostics is not None:
                                try:
                                    snapshot = summarize_diagnostics({domain: group},
                                        min(10000, max(1, int(config.get('evidence_max_items', 2000)))),
                                        time.monotonic() + min(.25, max(.001, float(config.get('evidence_max_seconds', .05)))))
                                    context.progress(event='adapter_group_finished',
                                        group=module_name, diagnostics=snapshot)
                                except Exception:
                                    pass
                        except BudgetExceeded:
                            # A global resource stop is not a source failure.
                            # Keep committed/partial summaries and leave every
                            # untouched descriptor and later group untouched.
                            source_results.extend(context.source_summaries[before:])
                            budget_interrupted = True
                            break
                        except Exception as exc:
                            # Durable completed sources from a failed adapter
                            # stay visible and are not counted again as failed.
                            accepted = context.source_summaries[before:]
                            source_results.extend(accepted)
                            done = {row.get('source_key') for row in accepted}
                            for source in selected:
                                if source_key(source) not in done:
                                    context.report_error(source, exc)
                                    source_results.append({'source_key': source_key(source),
                                        'status': 'failed', 'errors': 1,
                                        'error_class': type(exc).__name__})
                    result = {'sources': source_results,
                        **({'status': 'partial', 'error_codes': ['BudgetExceeded']} if budget_interrupted else {}),
                        **{key: sum(_nonnegative(g.get(key)) for g in group_results)
                           for key in (*COUNTERS, 'reused_rows', 'reused_stores')}}
                if not isinstance(result, dict):
                    raise TypeError('adapter_result_not_mapping')
            result.setdefault('sources',[])
            # Allow domain-specific counters but never expose them blindly.
            source_results = result['sources']
            if not isinstance(source_results,list):
                source_results=[]
            totals = {key:sum(_nonnegative(s.get(key,0)) for s in source_results if isinstance(s,dict)) for key in COUNTERS}
            for key,value in totals.items():
                result[key]=max(value,_nonnegative(result.get(key,0)))
            result['errors']=max(result['errors'],context.adapter_errors)
            result['sources_total']=len(sources)
            result['sources_complete']=sum(s.get('status') in ('complete','imported','reused') for s in source_results if isinstance(s,dict))
            result['sources_partial']=sum(s.get('status') in ('partial','failed') for s in source_results if isinstance(s,dict))
            result['sources_skipped']=sum(s.get('status') in ('skipped','unsupported','unavailable') for s in source_results if isinstance(s,dict))
            if result.get('status') not in DOMAIN_STATUSES:
                result['status']='partial' if result['errors'] or result['sources_partial'] or result['sources_skipped'] else ('complete' if sources else 'missing')
            if (result['errors'] or result['sources_partial'] or result['sources_skipped']) and result['status'] in ('complete','imported','reused'):
                result['status']='partial'
            result['error_codes']=sorted({code for source_result in [result,*source_results,*context.private_errors] if isinstance(source_result,dict) for code in [source_result.get('error_class'),source_result.get('reason'),*source_result.get('error_codes',[])] if isinstance(code,str) and code in ERROR_CODES})
            result['error_codes']=sorted(set(result['error_codes']) | context.error_classes)
            if context.budget_stop is not None:
                result['budget_stop'] = context.budget_stop
                result['status'] = 'partial'
                result['error_codes'] = sorted(set(result['error_codes']) | {'BudgetExceeded'})
            for key in ('reused_rows','reused_stores'):
                result[key]=max(_nonnegative(result.get(key,0)),sum(_nonnegative(s.get(key,0)) for s in source_results if isinstance(s,dict)))
            result['binding']='additive_staging_not_app_bound'
            result['binding_status']='unresolved_current_application_binding'
            result['target']=str(store.path)
            result.update(store.stored_totals())
            result['database_id']=store.db.execute("SELECT value FROM ingest_meta WHERE key='database_id'").fetchone()[0]
            result['adapter_errors']=context.private_errors
            return result
    except Exception as exc:
        return {'status':'partial' if isinstance(exc,BudgetExceeded) else 'failed',
                **{k:sum(_nonnegative(s.get(k,0)) for s in context.source_summaries) for k in COUNTERS},
                'errors':max(0 if isinstance(exc, BudgetExceeded) else 1, context.adapter_errors),
                **({'budget_stop': context.budget_stop} if context.budget_stop is not None else {}),
                'sources_total':len(sources),'error_class':type(exc).__name__,
                'error_codes':[type(exc).__name__] if type(exc).__name__ in ERROR_CODES else ['source_error'],
                'binding':'additive_staging_not_app_bound','sources':context.source_summaries,
                **(context.store.stored_totals() if context.store is not None else {})}


def run_ingest(sources, config=None, report_callback=None, adapters=None, catalog=None):
    """Ingest descriptors concurrently; callback is ALWAYS on the caller's thread.

    ``adapters`` is dependency injection for fixture tests, not an arbitrary config
    plugin path. Runtime adapters are the fixed modules in ADAPTERS.
    """
    sources=list(sources)
    config=dict(config or {})
    for key, value in GLOBAL_BUDGET_DEFAULTS.items():
        config.setdefault(key, value)
    config.setdefault('state_dir',str(Path(__file__).parent / '.local-results' / 'ingest'))
    layout=resolve_layout(config['state_dir'])
    state_dir=layout.ingest
    if any(p.is_symlink() for p in (state_dir,*state_dir.parents)):
        raise ValueError('symlink_state_dir_refused')
    state_dir.mkdir(mode=0o700,parents=True,exist_ok=True)
    if layout.legacy:
        os.chmod(state_dir,0o700)
    config['state_dir']=str(state_dir)
    workers=worker_limit(config.get('workers',8))
    started=time.monotonic()
    lock=threading.Lock()
    cancelled=threading.Event()
    source_progress={domain:{} for domain in DOMAINS}
    observed_errors={domain:{} for domain in DOMAINS}
    timings={d: {'started':None, 'finished':None, 'last_progress':None, 'active':None, 'active_bytes':None, 'sources_timed':0, 'completed_ms':0} for d in DOMAINS}
    report={'schema':REPORT_SCHEMA,'run_id':uuid.uuid4().hex,'status':'running',
            'started_at':_utc(),'updated_at':_utc(),'workers':workers,'elapsed_seconds':0,
            'domains':{d:{'status':'pending', **{k:0 for k in PUBLIC_COUNTERS}} for d in DOMAINS},
            'catalog_sha256':config.get('catalog_sha256'),
            'catalog_truncated':bool(config.get('catalog_truncated',False)), 'report_delivery_errors':0}
    private_results={}
    live_diagnostics={d: {} for d in DOMAINS}
    last_private_write=[0.0]
    evidence = None
    if EvidenceCollector is not None:
        try:
            evidence = EvidenceCollector(sources, config, catalog=catalog)
        except Exception:
            pass
    published_once = False

    def timing_snapshot(domain, now):
        t=timings[domain]
        elapsed=lambda value: max(0,int(((t['finished'] or now)-value)*1000)) if value is not None else None
        return {'elapsed_ms':elapsed(t['started']), 'active_source_elapsed_ms':elapsed(t['active']),
            'since_last_progress_ms':elapsed(t['last_progress']), 'active_source_bytes':t['active_bytes'],
            'sources_timed':t['sources_timed'], 'completed_source_elapsed_ms':t['completed_ms']}

    def progress(domain,event):
        with lock:
            now=time.monotonic();t=timings[domain];kind=event.get('event')
            t['last_progress']=now
            if kind == 'domain_started': t['started']=now
            elif kind == 'source_started': t['active']=now;t['active_bytes']=event.get('source_bytes')
            elif kind == 'source_finished': t['active']=None;t['active_bytes']=None
            elif kind == 'source_timed':
                t['sources_timed']+=1;t['completed_ms']+=_nonnegative(event.get('elapsed_ms'))
            current=report['domains'][domain]
            current['status']='running'
            current['timing']=timing_snapshot(domain,now)
            for count in ('stored_records_before', 'stored_records'):
                if type(event.get(count)) is int and 0 <= event[count] <= 10**15:
                    current[count] = event[count]
            if kind == 'adapter_group_finished':
                live_diagnostics[domain][event['group']] = event['diagnostics']
            key=event.get('source_key')
            if event.get('event') == 'adapter_error':
                identity = (key, event['error_class'], event['reason_code'])
                observed_errors[domain][identity] = observed_errors[domain].get(identity, 0) + 1
                current['error_codes'] = sorted(set(current.get('error_codes', [])) | {event['error_class']})
                telemetry = sanitize_error_telemetry(current.get('error_telemetry'))
                reason = event['reason_code']
                telemetry['reason_counts'][reason] = telemetry['reason_counts'].get(reason, 0) + 1
                current['error_telemetry'] = telemetry
            elif key:
                source_progress[domain][key]={**source_progress[domain].get(key,{}),**event}
                for k in COUNTERS:
                    current[k]=sum(_nonnegative(p.get(k,0)) for p in source_progress[domain].values())
            # Private live progress is sanitized too; raw descriptor catalog is separate.
            now=time.monotonic()
            if now-last_private_write[0]>=1:
                report['updated_at']=_utc()
                report['elapsed_seconds']=int(now-started)
                atomic_json(state_dir/'progress.json',sanitize_report(report))
                last_private_write[0]=now

    def publish():
        nonlocal published_once
        # Reader snapshots use separate read-only SQLite connections; workers
        # continue committing independently. No callback ever runs on a worker.
        pending_private = {}
        pending_work = _pending_snapshot(sources, config, private_results, adapters,
                                         private_sink=pending_private)
        with lock:
            observed = {domain: dict(rows) for domain, rows in observed_errors.items()}
        try:
            errors = collect_error_snapshot(state_dir, observed)
            atomic_json(state_dir/'source-errors.private.json', errors)
        except Exception:
            # Optional diagnostics must never stop authorized ingestion.
            errors = {'summary': {domain: sanitize_error_telemetry({}) for domain in DOMAINS}}
        storage_sizes = None
        try:
            from ingest_storage_sizes import capture_storage_sizes, unknown_storage_sizes
            storage_sizes = unknown_storage_sizes()
            storage_sizes = capture_storage_sizes(state_dir)
        except Exception:
            pass  # Optional metadata visibility never gates source ingestion.
        with lock:
            if storage_sizes is not None:
                report['storage_sizes'] = storage_sizes
            report['pending_work'] = pending_work
            for domain, telemetry in errors['summary'].items():
                # Callbacks may have arrived during the read-only SQLite query.
                telemetry['reason_counts'] = {}
                for (_, _, reason), count in observed_errors[domain].items():
                    telemetry['reason_counts'][reason] = telemetry['reason_counts'].get(reason, 0) + count
                report['domains'][domain]['error_telemetry'] = telemetry
                report['domains'][domain]['error_codes'] = sorted(
                    set(report['domains'][domain].get('error_codes', [])) | set(telemetry['class_counts']))
            now=time.monotonic()
            for domain in DOMAINS:
                report['domains'][domain]['timing']=timing_snapshot(domain,now)
            report['updated_at']=_utc()
            report['elapsed_seconds']=int(now-started)
            observed_report = sanitize_report(report)
            # Replace live group summaries with terminal results, never add both.
            observed_results = {**{d: {'completed_group_diagnostics': tuple(groups.values())}
                for d, groups in live_diagnostics.items() if groups}, **private_results}
        if evidence is not None:
            try:
                phase = 'pre' if not published_once else 'checkpoint' if report['status'] == 'running' else 'post'
                captured = evidence.capture(phase, observed_report,
                    results=observed_results, pending_private=pending_private)
                with lock:
                    report['ingest_evidence'] = captured
            except Exception:
                pass
        with lock:
            clean=sanitize_report(report)
        published_once = True
        atomic_json(state_dir/'progress.json',clean)
        report_path=config.get('report_path')
        if report_path:
            atomic_json(report_path,clean)
        if report_callback:
            try:
                report_callback(clean)
            except Exception:
                # Report transport failure must not discard successful local writes.
                report['report_delivery_errors']+=1
        if config.get('terminal_progress',True):
            counts=' '.join(d+':'+clean['domains'][d]['status']+'/'+str(clean['domains'][d]['written']) for d in DOMAINS)
            print('[ingest] '+counts,flush=True)
            print(dashboard(clean['pending_work']),flush=True)

    for domain in DOMAINS:
        report['domains'][domain]['sources_total'] = sum(_matches(source, domain) for source in sources)
    interval=max(1.0,float(config.get('report_interval',60)))
    publish()
    next_report=time.monotonic()+interval
    with ThreadPoolExecutor(max_workers=workers,thread_name_prefix='offmenu-ingest') as pool:
        futures={}
        for domain in DOMAINS:
            selected=[s for s in sources if _matches(s,domain)]
            report['domains'][domain]['sources_total']=len(selected)
            futures[pool.submit(_run_domain,domain,selected,config,cancelled,progress,started,adapters)]=domain
        pending=set(futures)
        try:
            while pending:
                completed,pending=wait(pending,timeout=min(1.0,max(0.01,next_report-time.monotonic())),return_when=FIRST_COMPLETED)
                for future in completed:
                    domain=futures[future]
                    result=future.result()
                    private_results[domain]=result
                    with lock:
                        timings[domain]['finished']=time.monotonic()
                        timings[domain]['active']=None;timings[domain]['active_bytes']=None
                        result['timing']=timing_snapshot(domain,timings[domain]['finished'])
                        report['domains'][domain]=result
                    atomic_json(state_dir/(domain+'.private.json'),result)
                if time.monotonic()>=next_report:
                    publish()
                    next_report=time.monotonic()+interval
        except KeyboardInterrupt:
            cancelled.set()
            # Cooperatively stop at the next batch, preserving every committed batch.
            for future,domain in futures.items():
                result=future.result()
                private_results[domain]=result
                report['domains'][domain]=result
    statuses=[row['status'] for row in report['domains'].values()]
    report['status']='complete' if all(s in ('complete','imported','reused','existing_loaded','not_applicable','awaiting_user_input','schema_only') for s in statuses) and not report['catalog_truncated'] else 'partial'
    if all(s=='failed' for s in statuses):
        report['status']='failed'
    if config.get('materialize_relational_targets', False):
        # All staging writer contexts have closed before exact cross-domain
        # projection. This is productive derived loading, not an app acceptance
        # claim and never a reason to withhold successful source writes.
        source_phase_status = report['status']
        report['status'] = 'running'
        if config.get('terminal_progress', True):
            print('[relational] Source writers closed; materializing exact derived targets (not application-bound).', flush=True)
        publish()
        def relational_progress(summary):
            report['relational_targets'] = summary
            publish()
        try:
            from ingest_relational_targets import materialize_relational_targets
            terminal_pending = {}
            _pending_snapshot(sources, config, private_results, adapters, private_sink=terminal_pending)
            selections = [row for row in terminal_pending.get('sources', [])
                if row.get('status') in ('completed', 'reused', 'partial')
                and row.get('stored_source_key') and row.get('stored_source_version')]
            derived = materialize_relational_targets(state_dir, selections,
                catalog_complete=not report['catalog_truncated'],
                max_records=config.get('relational_max_records', 100000000),
                max_seconds=config.get('relational_max_seconds', 3600),
                reserve_bytes=config.get('reserve_bytes', 2 * 1024**3),
                progress_callback=relational_progress,
                progress_interval=config.get('report_interval', 60))
            report['status'] = source_phase_status
            report['relational_targets'] = derived['summary']
            atomic_json(state_dir / 'relational-targets.private.json', derived['manifest'])
            if derived['summary'].get('status') not in ('complete', 'reused') and report['status'] == 'complete':
                report['status'] = 'partial'
        except Exception as exc:
            report['status'] = source_phase_status
            try:
                from ingest_relational_targets import sanitize_relational_summary
                report['relational_targets'] = sanitize_relational_summary({'status': 'blocked', 'blockers': ['derived_target_invalid']})
            except Exception:
                pass
            atomic_json(state_dir / 'relational-targets.private.json', {'status': 'blocked', 'error_class': type(exc).__name__})
            if report['status'] == 'complete':
                report['status'] = 'partial'
    publish()
    outputs = {}
    for domain in DOMAINS:
        try:
            outputs[domain] = output_identity(store_path(state_dir, domain))
        except (OSError, ValueError):
            pass
    atomic_json(state_dir/'last-run.private.json',{'report':sanitize_report(report),'domains':private_results,'output_identities':outputs})
    final=sanitize_report(report)
    atomic_json(state_dir/'last-report.json',final)
    return final


def prepare_default(state_dir, options=None):
    from ingest_catalog import discover_sources
    options=dict(options or {})
    state_dir=resolve_layout(state_dir).ingest
    options['state_dir']=str(state_dir)
    prior_path=Path(state_dir)/'catalog.private.json'
    prior={}
    try:
        if prior_path.exists() and not prior_path.is_symlink():
            with prior_path.open(encoding='utf-8') as stream:
                prior=json.load(stream)
    except (OSError,ValueError):
        prior={}
    # Resume bounded discovery before declaring the retained inventory complete.
    if prior.get('resume_cursor') and 'resume_cursor' not in options:
        options['resume_cursor']=prior['resume_cursor']
    catalog=discover_sources(options)
    sources=catalog.get('sources',[])
    if options.get('resume_cursor'):
        merged={s['id']:s for s in prior.get('sources',[]) if isinstance(s,dict) and 'id' in s}
        merged.update({s['id']:s for s in sources if isinstance(s,dict) and 'id' in s})
        sources=list(merged.values())
        catalog['sources']=sources
    if options.get('include_acquired', True):
        try:
            from ingest_acquired_catalog import discover_acquired_sources, merge_acquired_sources
            acquired_options = dict(options)
            if prior.get('acquired_resume_cursor') and 'acquired_resume_cursor' not in acquired_options:
                acquired_options['acquired_resume_cursor'] = prior['acquired_resume_cursor']
            acquired = discover_acquired_sources(acquired_options,
                                                existing_sources=[*sources, *prior.get('sources', [])])
            if acquired_options.get('acquired_resume_cursor'):
                prior_acquired = [row for row in prior.get('sources', []) if row.get('acquired_source') or row.get('acquired_adapter')]
                sources = merge_acquired_sources(sources, {'sources': prior_acquired})
            sources = merge_acquired_sources(sources, acquired)
            catalog['acquired'] = {key: value for key, value in acquired.items() if key != 'sources'}
            catalog['acquired_resume_cursor'] = acquired.get('resume_cursor')
            catalog['errors'].extend(acquired.get('errors', []))
            catalog['restriction_updates'].extend(acquired.get('restriction_updates', []))
            catalog['complete'] = catalog.get('complete', False) and acquired.get('complete', False)
            catalog['truncated'] = catalog.get('truncated', False) or acquired.get('truncated', False)
        except Exception as exc:
            # Newly acquired input is not a gate for readable retained sources.
            catalog.setdefault('errors', []).append({'operation': 'acquired_catalog', 'code': type(exc).__name__})
            catalog['complete'] = False
            catalog['acquired'] = {'status': 'unavailable', 'error_class': type(exc).__name__}
    catalog['sources'] = sources
    restrictions={u['id']:u for u in catalog.get('restriction_updates',[]) if isinstance(u,dict) and 'id' in u}
    for source in sources:
        if source.get('id') in restrictions:
            source.update(restricted=True,disposition='restricted',reason=restrictions[source['id']].get('reason','restricted_alias'))
        if source.get('acquired_adapter') in ACQUIRED_ADAPTERS:
            try:
                module = importlib.import_module(ACQUIRED_ADAPTERS[source['acquired_adapter']])
                source['adapter_version'] = getattr(module, 'ADAPTER_VERSION', getattr(module, 'VERSION', 1))
            except Exception:
                pass
        ds=source.get('domains',[])
        if not source.get('acquired_adapter') and isinstance(ds,list) and 'recipes' in ds and 'ingredients' not in ds:
            source['domains']=[*ds,'ingredients']
    # Metadata-only identity: no raw dataset scan/hash needed for a job key.
    identity=json.dumps(sources,sort_keys=True,ensure_ascii=True,separators=(',',':')).encode()
    sha=hashlib.sha256(identity).hexdigest()
    config={**options,'state_dir':str(state_dir),'catalog_sha256':sha,
            'catalog_truncated':bool(catalog.get('truncated',False) or catalog.get('complete') is False)}
    atomic_json(Path(state_dir)/'catalog.private.json',catalog)
    return {'sources':sources,'config':config,'catalog':catalog,'catalog_sha256':sha}


def run_prepared(prepared, report_callback=None):
    return run_ingest(prepared['sources'],prepared['config'],report_callback, catalog=prepared.get('catalog'))


def run_default(state_dir, workers=8, report_callback=None, options=None):
    options={**(options or {}),'workers':workers}
    return run_prepared(prepare_default(state_dir,options),report_callback)


def completed_outputs_available(prepared):
    """Read-only ownership/count marker check before trusting an unchanged receipt.

    Does not run a full DB integrity scan or equate these additive staging stores
    with canonical application bindings. Deleting/replacing an output invalidates
    the completed plan even when the retained input catalog is unchanged.
    """
    import sqlite3
    state=resolve_layout(prepared['config']['state_dir']).ingest
    try:
        if any(p.is_symlink() for p in (state,*state.parents)):
            return False
        with (state/'last-report.json').open(encoding='utf-8') as stream:
            report=json.load(stream)
        with (state/'last-run.private.json').open(encoding='utf-8') as stream:
            private=json.load(stream)
        if report.get('status')!='complete' or report.get('catalog_sha256')!=prepared.get('catalog_sha256') or report.get('run_id')!=private.get('report',{}).get('run_id'):
            return False
        for domain in DOMAINS:
            path=resolve_layout(state).domain_path(domain)
            if path.is_symlink() or not path.is_file():
                return False
            expected=private.get('domains',{}).get(domain,{})
            # Metadata identity catches deletion/replacement or modification even
            # when a copied database retains the same ID and stale row counter.
            if output_identity(path) != private.get('output_identities', {}).get(domain):
                return False
            with closing(sqlite3.connect(path.as_uri()+'?mode=ro',uri=True,timeout=2)) as db:
                meta=dict(db.execute('SELECT key,value FROM ingest_meta'))
            if meta.get('domain')!=domain or meta.get('binding')!='additive_staging_not_app_bound' or meta.get('database_id')!=expected.get('database_id') or int(meta.get('record_count',-1))!=expected.get('stored_records'):
                return False
        if prepared.get('config', {}).get('materialize_relational_targets'):
            from ingest_relational_targets import relational_outputs_available
            if not relational_outputs_available(state):
                return False
        if prepared.get('sources') is not None:
            snapshot = pending_snapshot(prepared, persist=False)
            if snapshot['status'] != 'available' or not snapshot['catalog_complete']:
                return False
            if any(snapshot['totals'][k] for k in ('not_yet_read', 'partial', 'failed', 'unsupported', 'unknown')):
                return False
        return True
    except (ImportError,OSError,ValueError,KeyError,TypeError,sqlite3.Error):
        return False
