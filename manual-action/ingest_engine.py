"""Bounded parallel best-effort ingestion with serialized sanitized reporting.

Only this coordinating module invokes report_callback. Domain workers never run
Git or transmit anything. Public counts describe source rows, not distinct entities.
"""
from __future__ import annotations
from concurrent.futures import ThreadPoolExecutor, wait, FIRST_COMPLETED
import hashlib
import importlib
import json
import os
from pathlib import Path
import shutil
import threading
import time
import uuid
from ingest_api import DOMAINS, COUNTERS, BudgetExceeded, source_key
from ingest_store import DomainStore
from ingest_errors import (ERROR_CLASSES, classify_error, collect_error_snapshot,
                           sanitize_error_telemetry)
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
        return Path(state_dir) / ('private-household' if domain in ('user_profiles', 'inventory') else '.') / 'staging' / (domain + '.sqlite3')

    def dashboard(summary):
        return '[pending] reporting metadata unavailable; remaining reads/writes unknown'


ADAPTERS = {'barcodes':'ingest_existing','ingredients':'ingest_recipes',
    'recipes':'ingest_recipes','dietary':'ingest_misc','user_profiles':'ingest_existing',
    'inventory':'ingest_existing','suppliers':'ingest_suppliers','citations':'ingest_misc'}
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
        if 'error_telemetry' in row:
            safe['domains'][domain]['error_telemetry'] = sanitize_error_telemetry(row['error_telemetry'])
    for key in ('catalog_sha256',):
        value = report.get(key)
        if isinstance(value,str) and re.fullmatch('[a-f0-9]{64}',value):
            safe[key]=value
    safe['catalog_truncated'] = report.get('catalog_truncated') is True
    safe['report_delivery_errors'] = _nonnegative(report.get('report_delivery_errors',0))
    if 'pending_work' in report:
        safe['pending_work'] = sanitize_pending_work(report['pending_work'])
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


def _pending_snapshot(sources, config, results=None, adapters=None, persist=True):
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

    def __getitem__(self, key):
        return getattr(self,key)

    def get(self,key,default=None):
        return getattr(self,key,default)

    def check_budget(self):
        if self.cancelled.is_set():
            raise BudgetExceeded('cancelled')
        seconds = float(self.config.get('max_seconds',0))
        if seconds > 0 and time.monotonic() - self.started >= seconds:
            raise BudgetExceeded('wall_time_cap')
        reserve = int(self.config.get('reserve_bytes', 2 * 1024**3))
        if shutil.disk_usage(self.state_dir).free < reserve:
            raise BudgetExceeded('disk_reserve')

    def progress(self, **counts):
        self._progress_callback(self.domain, counts)

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
        result=self.store.ingest(source,records)
        self.source_summaries.append(result)
        return result


def _matches(source, domain):
    domains = source.get('domains', source.get('domain', []))
    if isinstance(domains,str):
        domains = [domains]
    return domain in domains


def _run_domain(domain, sources, config, cancelled, progress, started, adapters=None):
    context = IngestContext(domain,config['state_dir'],config,cancelled,progress,started)
    try:
        with DomainStore(domain, context.state_dir, config, context.check_budget, context.progress) as store:
            context.store=store
            if not sources:
                result = {'status':'awaiting_user_input' if domain in ('user_profiles','inventory') else 'missing', 'sources':[]}
            else:
                handler = (adapters or {}).get(domain)
                if handler is None:
                    handler = importlib.import_module(ADAPTERS[domain]).run_domain
                result = handler(domain,sources,context)
                if not isinstance(result,dict):
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
            for key in ('reused_rows','reused_stores'):
                result[key]=max(_nonnegative(result.get(key,0)),sum(_nonnegative(s.get(key,0)) for s in source_results if isinstance(s,dict)))
            result['binding']='additive_staging_not_app_bound'
            result['binding_status']='unresolved_current_application_binding'
            result['target']=str(store.path)
            result['stored_records']=int(store.db.execute("SELECT value FROM ingest_meta WHERE key='record_count'").fetchone()[0])
            result['database_id']=store.db.execute("SELECT value FROM ingest_meta WHERE key='database_id'").fetchone()[0]
            result['adapter_errors']=context.private_errors
            return result
    except Exception as exc:
        return {'status':'partial' if isinstance(exc,BudgetExceeded) else 'failed',
                **{k:sum(_nonnegative(s.get(k,0)) for s in context.source_summaries) for k in COUNTERS},
                'errors':max(1,context.adapter_errors),'sources_total':len(sources),'error_class':type(exc).__name__,
                'error_codes':[type(exc).__name__] if type(exc).__name__ in ERROR_CODES else ['source_error'],
                'binding':'additive_staging_not_app_bound','sources':context.source_summaries}


def run_ingest(sources, config=None, report_callback=None, adapters=None):
    """Ingest descriptors concurrently; callback is ALWAYS on the caller's thread.

    ``adapters`` is dependency injection for fixture tests, not an arbitrary config
    plugin path. Runtime adapters are the fixed modules in ADAPTERS.
    """
    sources=list(sources)
    config=dict(config or {})
    config.setdefault('state_dir',str(Path(__file__).parent / '.local-results' / 'ingest'))
    state_dir=Path(config['state_dir']).absolute()
    if any(p.is_symlink() for p in (state_dir,*state_dir.parents)):
        raise ValueError('symlink_state_dir_refused')
    state_dir.mkdir(mode=0o700,parents=True,exist_ok=True)
    os.chmod(state_dir,0o700)
    config['state_dir']=str(state_dir)
    workers=worker_limit(config.get('workers',8))
    started=time.monotonic()
    lock=threading.Lock()
    cancelled=threading.Event()
    source_progress={domain:{} for domain in DOMAINS}
    observed_errors={domain:{} for domain in DOMAINS}
    report={'schema':REPORT_SCHEMA,'run_id':uuid.uuid4().hex,'status':'running',
            'started_at':_utc(),'updated_at':_utc(),'workers':workers,'elapsed_seconds':0,
            'domains':{d:{'status':'pending', **{k:0 for k in PUBLIC_COUNTERS}} for d in DOMAINS},
            'catalog_sha256':config.get('catalog_sha256'),
            'catalog_truncated':bool(config.get('catalog_truncated',False)), 'report_delivery_errors':0}
    private_results={}
    last_private_write=[0.0]

    def progress(domain,event):
        with lock:
            current=report['domains'][domain]
            current['status']='running'
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
        # Reader snapshots use separate read-only SQLite connections; workers
        # continue committing independently. No callback ever runs on a worker.
        pending_work = _pending_snapshot(sources, config, private_results, adapters)
        with lock:
            observed = {domain: dict(rows) for domain, rows in observed_errors.items()}
        try:
            errors = collect_error_snapshot(state_dir, observed)
            atomic_json(state_dir/'source-errors.private.json', errors)
        except Exception:
            # Optional diagnostics must never stop authorized ingestion.
            errors = {'summary': {domain: sanitize_error_telemetry({}) for domain in DOMAINS}}
        with lock:
            report['pending_work'] = pending_work
            for domain, telemetry in errors['summary'].items():
                # Callbacks may have arrived during the read-only SQLite query.
                telemetry['reason_counts'] = {}
                for (_, _, reason), count in observed_errors[domain].items():
                    telemetry['reason_counts'][reason] = telemetry['reason_counts'].get(reason, 0) + count
                report['domains'][domain]['error_telemetry'] = telemetry
                report['domains'][domain]['error_codes'] = sorted(
                    set(report['domains'][domain].get('error_codes', [])) | set(telemetry['class_counts']))
            report['updated_at']=_utc()
            report['elapsed_seconds']=int(time.monotonic()-started)
            clean=sanitize_report(report)
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
    restrictions={u['id']:u for u in catalog.get('restriction_updates',[]) if isinstance(u,dict) and 'id' in u}
    for source in sources:
        if source.get('id') in restrictions:
            source.update(restricted=True,disposition='restricted',reason=restrictions[source['id']].get('reason','restricted_alias'))
        ds=source.get('domains',[])
        if isinstance(ds,list) and 'recipes' in ds and 'ingredients' not in ds:
            source['domains']=[*ds,'ingredients']
    # Metadata-only identity: no raw dataset scan/hash needed for a job key.
    identity=json.dumps(sources,sort_keys=True,ensure_ascii=True,separators=(',',':')).encode()
    sha=hashlib.sha256(identity).hexdigest()
    config={**options,'state_dir':str(state_dir),'catalog_sha256':sha,
            'catalog_truncated':bool(catalog.get('truncated',False) or catalog.get('complete') is False)}
    atomic_json(Path(state_dir)/'catalog.private.json',catalog)
    return {'sources':sources,'config':config,'catalog':catalog,'catalog_sha256':sha}


def run_prepared(prepared, report_callback=None):
    return run_ingest(prepared['sources'],prepared['config'],report_callback)


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
    state=Path(prepared['config']['state_dir']).absolute()
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
            path=state/('private-household' if domain in ('user_profiles','inventory') else '.')/'staging'/(domain+'.sqlite3')
            if path.is_symlink() or not path.is_file():
                return False
            expected=private.get('domains',{}).get(domain,{})
            # Metadata identity catches deletion/replacement or modification even
            # when a copied database retains the same ID and stale row counter.
            if output_identity(path) != private.get('output_identities', {}).get(domain):
                return False
            with sqlite3.connect(path.as_uri()+'?mode=ro',uri=True,timeout=2) as db:
                meta=dict(db.execute('SELECT key,value FROM ingest_meta'))
            if meta.get('domain')!=domain or meta.get('binding')!='additive_staging_not_app_bound' or meta.get('database_id')!=expected.get('database_id') or int(meta.get('record_count',-1))!=expected.get('stored_records'):
                return False
        if prepared.get('sources') is not None:
            snapshot = pending_snapshot(prepared, persist=False)
            if snapshot['status'] != 'available' or not snapshot['catalog_complete']:
                return False
            if any(snapshot['totals'][k] for k in ('not_yet_read', 'partial', 'failed', 'unsupported', 'unknown')):
                return False
        return True
    except (OSError,ValueError,KeyError,TypeError,sqlite3.Error):
        return False
