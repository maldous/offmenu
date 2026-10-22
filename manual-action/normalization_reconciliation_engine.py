"""Bounded reconciliation of committed public normalization-cache keys only.

Cache/source snapshots pin each discovery pass. Changed snapshots restart indexed
key discovery (new hashes may sort below the old cursor); graph receipts avoid
replaying successful keys. This is not a change feed or a full-corpus estimate.
Selected, previously unindexed keys are rehydrated from fixed staging databases
and their rules projection is validated by the reviewed component, not dispatched
to normalization workers. No raw files, AI, translation, or entity merges occur.
"""
from __future__ import annotations
from contextlib import closing
import copy
import json
import math
import re
from pathlib import Path
import shutil
import sqlite3
import time

from normalization_api import NormalizationError
from normalization_core import CompactNormalizationStore, canonical_json, digest
from normalization_engine import _identity, _metadata, _safe_path
from normalization_reconciliation import (PUBLIC_DOMAINS, DEFAULT_REGISTRY, VERSION,
    ReconciliationStore, _readonly, backfill_page, ingest_cache_keys)

SCHEMA = 'offmenu-db-reconciliation-report/1'
ENGINE_VERSION = 'bounded-reconciliation-orchestrator/1'
COUNTS = ('scanned', 'indexed_new', 'indexed_reused', 'quarantined', 'quarantine_retries')
DEFAULTS = {'batch_rows': 128, 'sample_rows': 32, 'max_rows': 50000,
    'max_output_bytes': 128 * 1024**2, 'max_seconds': 1800,
    'disk_reserve_bytes': 2 * 1024**3, 'report_interval': 60, 'retry_generation': 0}
HEX = re.compile(r'[0-9a-f]{64}\Z')
_ENGINE_SQL = '''
CREATE TABLE IF NOT EXISTS engine_meta(key TEXT PRIMARY KEY,value TEXT NOT NULL) WITHOUT ROWID;
CREATE TABLE IF NOT EXISTS engine_progress(domain TEXT NOT NULL,snapshot_key TEXT NOT NULL,
 cursor TEXT,counters_json TEXT NOT NULL,complete INTEGER NOT NULL,
 PRIMARY KEY(domain,snapshot_key)) WITHOUT ROWID;
CREATE TABLE IF NOT EXISTS engine_quarantine(domain TEXT NOT NULL,snapshot_key TEXT NOT NULL,
 cache_key TEXT NOT NULL,reason TEXT NOT NULL,attempts INTEGER NOT NULL CHECK(attempts=1),
 PRIMARY KEY(domain,snapshot_key,cache_key)) WITHOUT ROWID;
CREATE INDEX IF NOT EXISTS engine_quarantine_retry ON engine_quarantine(domain,cache_key);
'''


class _Stop(RuntimeError):
    pass


class _BadKey(Exception):
    pass


def _config(config):
    raw = dict(config or {})
    if set(raw) - set(DEFAULTS) - {'cancelled'}:
        raise ValueError('unknown_reconciliation_option')
    result = {**DEFAULTS, **raw}
    for key, low, high in (('batch_rows',1,128),('sample_rows',1,128),
            ('max_rows',1,10**6),('max_output_bytes',1024**2,1024**3),
            ('disk_reserve_bytes',0,10**15),('retry_generation',0,10**6)):
        if type(result[key]) is not int or not low <= result[key] <= high:
            raise ValueError('invalid_reconciliation_option')
    for key, high in (('max_seconds',1800),('report_interval',3600)):
        if type(result[key]) not in (int,float) or not math.isfinite(result[key]) or not 0 < result[key] <= high:
            raise ValueError('invalid_reconciliation_option')
    event = result.get('cancelled')
    if event is not None and not callable(getattr(event, 'is_set', None)):
        raise ValueError('invalid_cancellation_event')
    return result


def _files(state, domain):
    return {'cache': _identity(state/'normalization-private'/('compact-'+domain+'.sqlite3')),
            'source': _identity(state/'staging'/(domain+'.sqlite3'))}


def _snapshot(state, domain):
    before = _files(state, domain)
    if any(value['database'] is None for value in before.values()):
        raise NormalizationError('missing_reconciliation_input')
    with closing(_readonly(state/'normalization-private'/('compact-'+domain+'.sqlite3'), private=True)) as cache, closing(_readonly(state/'staging'/(domain+'.sqlite3'))) as source:
        cache.execute('BEGIN'); source.execute('BEGIN')
        if cache.execute("SELECT value FROM compact_meta WHERE key='binding'").fetchone() != (CompactNormalizationStore.BINDING,):
            raise NormalizationError('non_owned_compact_cache')
        metadata = _metadata(source, domain)
        after = _files(state, domain)
        if before != after:
            raise NormalizationError('snapshot_changed')
    return {'files': after, 'source_metadata': metadata}


def prepare_default(state_dir, config=None):
    """Fixed metadata-only admission; selected cache cardinalities stay unknown."""
    state = _safe_path(state_dir); options = _config(config)
    policy = digest(DEFAULT_REGISTRY)
    pins = {'engine': ENGINE_VERSION, 'component': VERSION, 'policy': policy,
            'retry_generation': options['retry_generation']}
    domains = {}
    for domain in PUBLIC_DOMAINS:
        item = {'status':'unavailable', 'snapshot':None}
        try:
            item.update(snapshot=_snapshot(state, domain), status='pending')
        except (OSError, sqlite3.Error, NormalizationError):
            pass
        item['snapshot_key'] = digest({'domain':domain, 'snapshot':item['snapshot'], 'pins':pins})
        domains[domain] = item
    return {'state_dir':state, 'config':options, 'domains':domains, 'policy_sha256':policy,
        'output_path':state/'normalization-private'/('reconciliation-'+policy+'.sqlite3'),
        'input_sha256':digest({'pins':pins,'domains':{d:v['snapshot_key'] for d,v in domains.items()}})}


def _progress(db, domain, snapshot):
    row = db.execute('SELECT cursor,counters_json,complete FROM engine_progress WHERE domain=? AND snapshot_key=?', (domain,snapshot)).fetchone()
    if row is None:
        return None
    cursor, raw, complete = row
    counts = json.loads(raw)
    if (cursor is not None and (not isinstance(cursor,str) or not HEX.fullmatch(cursor))
            or not isinstance(counts,dict) or set(counts) != set(COUNTS)
            or any(type(n) is not int or not 0 <= n <= 10**15 for n in counts.values())
            or complete not in (0,1)
            or counts['scanned'] != counts['indexed_new']+counts['indexed_reused']+counts['quarantined']
            or counts['quarantine_retries'] > counts['scanned']):
        raise NormalizationError('invalid_reconciliation_checkpoint')
    return cursor, counts, bool(complete)


def _public_progress(row, snapshot, cursor, counts, complete):
    row.update(counts)
    row['exhausted'] = complete
    row['status'] = 'cache_complete' if complete and not counts['quarantined'] else 'partial'
    row['checkpoint_sha256'] = digest({'snapshot':snapshot,'cursor':cursor,'counts':counts,'complete':complete})


def _pages(db):
    return db.execute('PRAGMA page_count').fetchone()[0] * db.execute('PRAGMA page_size').fetchone()[0]


class _Budget:
    def __init__(self, prepared):
        self.options=prepared['config']; self.state=prepared['state_dir']; self.started=time.monotonic()
        self.reason=None; self.free=None; self.rows=0; self.start_bytes=0; self.output_bytes=0
        self.sample_rows=0; self.sample_bytes=0; self.per_row=None; self.admitted=0
        self.capacity='sampling'; self.sampled=-math.inf

    def stop(self, reason):
        if self.reason is None: self.reason=reason
        raise _Stop(self.reason)

    def space(self, needed=0):
        try: self.free=shutil.disk_usage(self.state).free
        except OSError: self.stop('store_unavailable')
        self.sampled=time.monotonic()
        if self.free < self.options['disk_reserve_bytes']+needed: self.stop('disk_reserve')

    def check(self):
        if self.reason: raise _Stop(self.reason)
        event=self.options.get('cancelled')
        if event is not None and event.is_set(): self.stop('cancelled')
        if time.monotonic()-self.started >= self.options['max_seconds']: self.stop('wall_time_cap')
        if self.rows >= self.options['max_rows']: self.stop('row_cap')
        if self.capacity == 'admitted' and self.rows >= self.admitted: self.stop('capacity_limit')
        if self.capacity == 'insufficient': self.stop('capacity_limit')
        if time.monotonic()-self.sampled >= 1: self.space()

    def committed(self, rows, inserted, output_bytes):
        self.rows += rows; self.output_bytes=output_bytes
        if self.capacity == 'sampling':
            self.sample_rows += inserted
            self.sample_bytes = max(0,output_bytes-self.start_bytes)
            if self.sample_rows >= min(self.options['sample_rows'], self.options['max_rows']):
                self.admit()

    def admit(self):
        if not self.sample_rows:
            self.capacity='not_needed'; self.admitted=self.options['max_rows']; return
        # Four times the observed sample average, at least one SQLite page/key.
        # This admits only a bounded invocation, never predicts corpus capacity.
        self.per_row=max(4096,4*((self.sample_bytes+self.sample_rows-1)//self.sample_rows))
        self.space()
        remaining=min(self.options['max_output_bytes']-max(0,self.output_bytes-self.start_bytes),
                      max(0,self.free-self.options['disk_reserve_bytes']-2*1024**2))
        self.admitted=min(self.options['max_rows'],self.rows+max(0,remaining)//self.per_row)
        self.capacity='admitted' if self.admitted>self.rows else 'insufficient'

    def resources(self):
        return {'free_disk_bytes':self.free,'elapsed_seconds':max(0,int(time.monotonic()-self.started)),
            'workers':1,'invocation_rows':self.rows,'output_logical_bytes':self.output_bytes}

    def capacity_report(self):
        return {'status':self.capacity,'sample_rows':self.sample_rows,'sample_output_bytes':self.sample_bytes,
            'bytes_per_row_ceiling':self.per_row,'admitted_rows':self.admitted,
            'max_rows':self.options['max_rows'],'max_output_bytes':self.options['max_output_bytes']}


def run_prepared(prepared, report_callback=None):
    options=prepared['config']; budget=_Budget(prepared); state=prepared['state_dir']
    report={'schema':SCHEMA,'input_sha256':prepared['input_sha256'],'policy_sha256':prepared['policy_sha256'],
        'status':'running','stop_reason':None,'selection':'committed_compact_cache_keys',
        'integrity_reads':'fixed_staging_database_payload_and_projection_validation',
        'review_status':'pending_approved_route','gold_status':'blocked','entity_merges':0,
        'domains':{d:{'status':item['status'],'selected_keys':None,**dict.fromkeys(COUNTS,0),
            'exhausted':False,'checkpoint_sha256':None} for d,item in prepared['domains'].items()},
        'resources':budget.resources(),'capacity':budget.capacity_report()}
    last_emit=-math.inf
    def emit(force=False):
        nonlocal last_emit
        report['resources']=budget.resources();report['capacity']=budget.capacity_report()
        now=time.monotonic()
        if report_callback is not None and (force or now-last_emit>=options['report_interval']):
            report_callback(copy.deepcopy(report));last_emit=now

    def verify_prepared():
        for domain,item in prepared['domains'].items():
            if item['snapshot'] is not None and _files(state,domain)!=item['snapshot']['files']:
                report['domains'][domain].update(status='partial',exhausted=False)
                budget.stop('snapshot_changed')

    output=None
    try:
        path=prepared['output_path']
        # Durable counters remain readable even when capacity prevents any writes.
        if path.exists():
            with closing(_readonly(path,private=True)) as db:
                if (db.execute("SELECT value FROM reconciliation_meta WHERE key='binding'").fetchone() != (ReconciliationStore.BINDING,)
                        or db.execute("SELECT value FROM reconciliation_meta WHERE key='policy_sha256'").fetchone() != (prepared['policy_sha256'],)):
                    raise NormalizationError('reconciliation_policy_mismatch')
                budget.start_bytes=budget.output_bytes=_pages(db)
                if db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='engine_progress'").fetchone():
                    if db.execute("SELECT value FROM engine_meta WHERE key='binding'").fetchone() != (ENGINE_VERSION,):
                        raise NormalizationError('reconciliation_engine_binding_mismatch')
                    for domain,item in prepared['domains'].items():
                        saved=_progress(db,domain,item['snapshot_key'])
                        if saved: _public_progress(report['domains'][domain],item['snapshot_key'],*saved)
        emit(True)
        verify_prepared()
        if all(row['exhausted'] for row in report['domains'].values()):
            budget.capacity='not_needed';budget.admitted=options['max_rows']
        else:
            budget.check();budget.space(2*1024**2)
            output=ReconciliationStore(path,disk_reserve_bytes=options['disk_reserve_bytes'])
            output.db.executescript(_ENGINE_SQL)
            output.db.execute('INSERT OR IGNORE INTO engine_meta VALUES(?,?)',('binding',ENGINE_VERSION));output.db.commit()
            if output.db.execute("SELECT value FROM engine_meta WHERE key='binding'").fetchone() != (ENGINE_VERSION,):
                raise NormalizationError('reconciliation_engine_binding_mismatch')
            page_size=output.db.execute('PRAGMA page_size').fetchone()[0]
            max_pages=(budget.start_bytes+options['max_output_bytes'])//page_size
            if _pages(output.db)>max_pages*page_size:budget.stop('output_cap')
            output.db.execute('PRAGMA max_page_count='+str(max_pages))
            budget.output_bytes=_pages(output.db)
            def sql_progress():
                try:budget.check();return 0
                except _Stop:return 1
            output.db.set_progress_handler(sql_progress,1000)

            for domain,item in prepared['domains'].items():
                public=report['domains'][domain]
                if item['status']=='unavailable' or public['exhausted']:continue
                cursor,counts,complete=_progress(output.db,domain,item['snapshot_key']) or (None,dict.fromkeys(COUNTS,0),False)
                public['status']='running'
                def check_snapshot():
                    if _files(state,domain)!=item['snapshot']['files']:budget.stop('snapshot_changed')
                def commit(keys,complete,quarantine=False):
                    nonlocal cursor,counts
                    budget.check();check_snapshot();budget.space(2*1024**2)
                    pending=output.pending_keys(keys)
                    retries=sum(bool(output.db.execute('SELECT 1 FROM engine_quarantine WHERE domain=? AND cache_key=? AND snapshot_key<>? LIMIT 1',
                        (domain,key,item['snapshot_key'])).fetchone()) for key in pending)
                    staged=None;next_cursor=keys[-1] if keys else cursor;logical=None;callback_started=False
                    def before_commit(db,result):
                        nonlocal staged,logical,callback_started
                        callback_started=True
                        budget.check();check_snapshot()
                        staged=dict(counts);staged['scanned']+=len(keys)
                        staged['indexed_new']+=result['new'];staged['indexed_reused']+=len(keys)-len(pending)+result['reused']
                        staged['quarantined']+=int(quarantine);staged['quarantine_retries']+=retries
                        if quarantine:
                            db.execute('INSERT INTO engine_quarantine VALUES(?,?,?,?,1)',
                                (domain,item['snapshot_key'],keys[0],'invalid_cache_or_source'))
                        db.execute('INSERT INTO engine_progress VALUES(?,?,?,?,?) ON CONFLICT(domain,snapshot_key) DO UPDATE SET cursor=excluded.cursor,counters_json=excluded.counters_json,complete=excluded.complete',
                            (domain,item['snapshot_key'],next_cursor,canonical_json(staged),int(complete)))
                        logical=_pages(db)
                        if logical-budget.start_bytes>options['max_output_bytes']:budget.stop('output_cap')
                        budget.space(max(1024**2,4*max(0,logical-budget.output_bytes)))
                    try:
                        if quarantine or not pending:output.ingest_artifacts([],before_commit=before_commit)
                        else:ingest_cache_keys(state,domain,pending,output,before_commit=before_commit)
                    except (NormalizationError,ValueError,TypeError,KeyError,OverflowError,RecursionError) as exc:
                        if callback_started:raise
                        if isinstance(exc,NormalizationError) and str(exc)=='reconciliation_disk_reserve':budget.stop('disk_reserve')
                        raise _BadKey() from exc
                    previous_new=counts['indexed_new']
                    cursor,counts=next_cursor,staged
                    _public_progress(public,item['snapshot_key'],cursor,counts,complete)
                    budget.committed(len(keys),staged['indexed_new']-previous_new,logical);emit()
                def process(keys,complete):
                    try:commit(keys,complete)
                    except _Stop:raise
                    except (MemoryError,OSError,sqlite3.Error):raise
                    except _BadKey:
                        check_snapshot()
                        if len(keys)>1:
                            middle=len(keys)//2;process(keys[:middle],False);process(keys[middle:],complete)
                        elif keys:commit(keys,complete,quarantine=True)
                        else:raise
                while not public['exhausted']:
                    budget.check();check_snapshot()
                    limit=min(options['batch_rows'],options['max_rows']-budget.rows)
                    if budget.capacity=='sampling':limit=min(limit,max(1,options['sample_rows']-budget.sample_rows))
                    elif budget.capacity=='admitted':limit=min(limit,budget.admitted-budget.rows)
                    keys=backfill_page(state,domain,after=cursor,limit=limit)
                    if any(not isinstance(key,str) or not HEX.fullmatch(key) for key in keys):
                        raise NormalizationError('invalid_committed_cache_key')
                    process(keys,len(keys)<limit)
            verify_prepared()
            if budget.capacity=='sampling':budget.admit()
    except _Stop:
        pass
    except (MemoryError,OSError):
        budget.reason=budget.reason or 'resource_failure'
    except sqlite3.Error as exc:
        budget.reason=budget.reason or ('output_cap' if getattr(exc,'sqlite_errorcode',None)==sqlite3.SQLITE_FULL else 'resource_failure')
    except (NormalizationError,ValueError,TypeError,KeyError,OverflowError,RecursionError):
        budget.reason=budget.reason or 'store_unavailable'
    finally:
        if output is not None:
            output.db.set_progress_handler(None,0);output.close()
    for row in report['domains'].values():
        if row['status']=='running':row['status']='partial'
    complete=all(row['status']=='cache_complete' for row in report['domains'].values())
    report['status']='cache_complete' if complete and budget.reason is None else 'partial'
    report['stop_reason']=budget.reason
    if not any(item['status']!='unavailable' for item in prepared['domains'].values()):
        report['status']='failed';budget.capacity='unavailable'
    emit(True)
    return report


def run_reconciliation(state_dir, config=None, report_callback=None):
    return run_prepared(prepare_default(state_dir,config),report_callback)
