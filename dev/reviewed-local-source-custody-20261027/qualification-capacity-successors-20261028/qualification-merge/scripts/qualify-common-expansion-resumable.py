#!/usr/bin/env python3
"""Bounded, transactional orchestration of the unchanged common expansion proof.

No final evidence exists until every original check passes. One process owns the
SQLite coordinator. Reinvoke with --resume after a paused receipt (exit 75).
"""
import argparse
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
import fcntl
import gzip
import hashlib
import importlib.metadata
import importlib.util
import json
import os
from pathlib import Path
import signal
import sqlite3
import sys
import tempfile
sys.path.insert(0,str(Path(__file__).parent))
import qualification_asset_workers as workers
import time

BASE = Path(__file__).with_name('qualify-common-expansion.py')
BASE_SHA = '37aa195b0bbf798eb361be9ee1803ed185c5e74fa38b79c3c4efe8a6dfcc6965'
if hashlib.sha256(BASE.read_bytes()).hexdigest() != BASE_SHA:
    raise RuntimeError('original qualification implementation pin mismatch')
spec = importlib.util.spec_from_file_location('original_qualification', BASE)
q = importlib.util.module_from_spec(spec)
spec.loader.exec_module(q)

class Paused(Exception):
    pass

class Clock:
    def __init__(self, seconds):
        self.end = time.monotonic() + seconds
        self.cancelled = False
    def check(self):
        if self.cancelled or time.monotonic() >= self.end:
            raise Paused()
    def sql(self):
        return int(self.cancelled or time.monotonic() >= self.end)

class Database(q.Database):
    def __init__(self, path, budget, fresh):
        if fresh:
            super().__init__(path, budget)
            self.connection.close()
        self.path, self.scratch_budget_bytes, self.pending = path, budget, 0
        self.connection = sqlite3.connect(path, timeout=0, uri=True)
        self.connection.execute('PRAGMA journal_mode=DELETE')
        self.connection.execute('PRAGMA synchronous=FULL')
        self.connection.execute('PRAGMA temp_store=FILE')
        self.connection.execute('PRAGMA cache_size=-65536')
        if fresh:
            self.connection.execute('CREATE TABLE checkpoint (id INTEGER PRIMARY KEY CHECK(id=1), value TEXT NOT NULL)')
            self.connection.execute('CREATE TABLE run_pins (id INTEGER PRIMARY KEY CHECK(id=1), value TEXT NOT NULL)')
            self.connection.commit()
        workers.prepare_merge(self.connection)
    def commit_if_needed(self):
        # A packet asset and its checkpoint MUST commit together, never mid-asset.
        if self.pending >= q.COMMIT_EVERY:
            self.check_budget()
            self.pending = 0
    def check_budget(self):
        used = getattr(self, "spool_reserved_bytes", 0) + sum(p.stat().st_size for p in (self.path, Path(str(self.path)+'-journal'),
                    Path(str(self.path)+'-wal'), Path(str(self.path)+'-shm')) if p.exists())
        # Old invocation shards are retained, never silently deleted or forgotten.
        for directory in self.path.parent.glob(self.path.name+'.shards-*'):
            if directory==getattr(self,'spool_root',None): continue
            used += sum(p.stat().st_size for p in directory.glob('*') if p.is_file())
        if used > self.scratch_budget_bytes:
            q.fail('SQLite qualification scratch including journal exceeded its configured budget')
        if q.shutil.disk_usage(self.path.parent).free < q.MINIMUM_FREE_BYTES:
            q.fail('less than 10 GiB free during SQLite qualification')

def stat_pin(path):
    s = path.stat()
    return [s.st_dev, s.st_ino, s.st_size, s.st_mtime_ns, s.st_ctime_ns]

def digest(path, clock):
    h = hashlib.sha256()
    with path.open('rb') as f:
        while True:
            clock.check()
            b = f.read(1024*1024)
            if not b: break
            h.update(b)
    return h.hexdigest()

def checked_asset(item, clock):
    path, entry, pin = item
    clock.check()
    if stat_pin(path) != pin or pin[2] != entry['bytes'] or digest(path, clock) != entry['sha256'] or stat_pin(path) != pin:
        q.fail(f'{path}: byte length or SHA-256 does not match manifest or input changed')

def inventory(dirs, clock):
    packages, pins = [], []
    for directory in dirs:
        clock.check()
        directory = directory.resolve()
        mp = directory / 'manifest.json'
        raw = mp.read_bytes()
        mh = hashlib.sha256(raw).hexdigest()
        manifest = json.loads(raw)
        admission = q.admission_check(directory, manifest, mh)
        assets, files = q.listed_assets(directory, manifest)
        source_records = q.admitted_source_records(directory, manifest, admission['grandfathered'])
        apins = []
        for entry in assets:
            clock.check()
            path = directory / entry['key']
            if not path.is_file(): q.fail(f'missing manifest-listed file: {path}')
            apins.append(stat_pin(path))
        extra = directory / 'foodon-source-manifest.json'
        pins.append({'directory': str(directory), 'manifest': mh, 'assets': apins,
                     'grandfatherSource': digest(extra, clock) if admission['grandfathered'] else None})
        packages.append((directory, manifest, mh, admission, assets, files, source_records, apins))
    return packages, pins

def save(db, state):
    db.check_budget()
    db.connection.execute('INSERT OR REPLACE INTO checkpoint VALUES (1,?)', (q.canonical(state),))
    db.connection.commit()
    db.check_budget()

def finish_package(info, state):
    directory, manifest, mh, admission, assets, files, sources, _ = info
    observed = Counter(state['observed'])
    if observed['packets'] != sum(e['packets'] for e in files):
        q.fail(f'{directory}: total packet count does not equal manifest file metadata')
    if not admission['grandfathered']:
        for key, value in observed.items():
            for field in ('expectedCounts', 'observedCounts'):
                if manifest[field].get(key) != value:
                    q.fail(f'{directory}: {field}.{key}={manifest[field].get(key)}; streamed {value}')
        coverage = manifest['partitionCoverage']
        if coverage['observedFiles'] != len(files) or coverage['observedPackets'] != observed['packets']:
            q.fail(f'{directory}: partition coverage does not equal streamed files/packets')
    for key, value in observed.items():
        if manifest['counts'].get(key) != value:
            q.fail(f'{directory}: counts.{key}={manifest["counts"].get(key)}; streamed {value}')
    state['packages'].append({'directory': str(directory), 'releaseId': manifest.get('releaseId'),
        'manifestByteSha256': mh, 'grandfathered': admission['grandfathered'],
        'packetFiles': len(files), 'observedCounts': dict(observed), 'admittedSourceRecords': sources})
    aggregate = Counter(state['aggregate']); aggregate.update(observed)
    state.update(aggregate=dict(aggregate), observed={}, package=state['package']+1, asset=0, phase='hash')

def page(db, state, limit, clock):
    """Keyset pages execute precisely the original joins/counts, without OFFSET scans."""
    tables = ['references_pending','translation_sources','ids','texts','citations']
    table = tables[state['table']]
    keys = {'references_pending':['target_kind','id_sha256'], 'translation_sources':['text_id_sha256','source_sha256'],
            'ids':['kind','id_sha256'], 'texts':['id_sha256'], 'citations':['id_sha256']}[table]
    cursor = state['cursor']
    params = []
    where = ''
    if cursor is not None:
        params = [bytes.fromhex(x['hex']) if isinstance(x,dict) else x for x in cursor]
        where = ' WHERE ('+','.join(keys)+') > ('+','.join('?' for _ in keys)+')'
    selected = ','.join(keys + (['source_sha256'] if table == 'texts' else []))
    rows = db.connection.execute(f'SELECT {selected} FROM {table}{where} ORDER BY '+','.join(keys)+' LIMIT ?', params+[limit]).fetchall()
    if not rows:
        if table == 'references_pending' and state['bad']:
            q.fail(f'{state["bad"]} internal resource/assertion references do not resolve globally')
        if table == 'translation_sources' and state['bad']:
            q.fail(f'{state["bad"]} translations do not reference the correct original text hash')
        state['database']['referencesRecorded' if table=='references_pending' else table] = state['count']
        state.update(table=state['table']+1, cursor=None, count=0, bad=0)
        if state['table']==len(tables): state['phase']='final-hash'; state['package']=0; state['asset']=0
        return
    if table == 'references_pending':
        for kind, ident in rows:
            clock.check()
            if db.connection.execute('SELECT 1 FROM ids WHERE kind=? AND id_sha256=?', (kind,ident)).fetchone() is None:
                state['bad']+=1
    elif table == 'translation_sources':
        for ident, source in rows:
            clock.check()
            found = db.connection.execute('SELECT source_sha256 FROM texts WHERE id_sha256=?',(ident,)).fetchone()
            if found is None or found[0]!=source: state['bad']+=1
    state['cursor']=[{'hex':x.hex()} if isinstance(x,bytes) else x for x in rows[-1][:len(keys)]]
    state['count']+=len(rows)

def qualify(evidence, scratch, dirs, budget_gib=60, resume=False, max_seconds=1500,
            hash_workers=256, page_rows=10000, max_steps=None, packet_workers=256,
            worker_memory_bytes=128*1024**2, shard_budget_bytes=64*1024**2):
    if budget_gib<=0 or max_seconds<=0 or hash_workers<1 or page_rows<1 or packet_workers<1 or shard_budget_bytes<4096 or worker_memory_bytes<0: q.fail('invalid bounded-run arguments')
    clock = Clock(max_seconds)
    old = {}
    for sig in (signal.SIGTERM, signal.SIGINT):
        old[sig] = signal.signal(sig, lambda *_: setattr(clock,'cancelled',True))
    scratch.parent.mkdir(parents=True, exist_ok=True)
    lock = open(str(scratch)+'.lock','a+')
    db = None
    pipeline = None
    try:
        try: fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError: q.fail('another qualification coordinator owns scratch')
        fresh = not scratch.exists()
        if not fresh and not resume: q.fail(f'scratch SQLite path already exists: {scratch}')
        if fresh and evidence.exists(): q.fail(f'evidence output already exists: {evidence}')
        packages, package_pins = inventory(dirs, clock)
        sb = (q.ROOT/'corpus/common-data.schema.json').read_bytes()
        cb = (q.ROOT/'corpus/common-data-contract.json').read_bytes()
        schema, contract = json.loads(sb), json.loads(cb)
        pins = {'version':1, 'original':BASE_SHA, 'orchestrator':q.sha_file(Path(__file__)), 'workerHelper':q.sha_file(Path(workers.__file__)),
                'schema':hashlib.sha256(sb).hexdigest(), 'contract':hashlib.sha256(cb).hexdigest(),
                'packages':package_pins, 'budget':int(budget_gib*1024**3), 'evidence':str(evidence.resolve()),
                'python':sys.version, 'sqlite':sqlite3.sqlite_version,
                'validator':importlib.metadata.version('jsonschema-rs')}
        db = Database(scratch,pins['budget'],fresh)
        db.check_budget()
        if fresh:
            db.connection.execute('INSERT INTO run_pins VALUES (1,?)',(q.canonical(pins),))
            state = dict(started=time.time(), phase='hash', package=0, asset=0,
                         aggregate={},observed={},packages=[],database={},table=0,cursor=None,count=0,bad=0)
            save(db,state)
        else:
            row=db.connection.execute('SELECT value FROM checkpoint WHERE id=1').fetchone()
            if row is None: q.fail('scratch lacks initialized checkpoint; preserve and use a new path')
            state=json.loads(row[0])
            stored=db.connection.execute('SELECT value FROM run_pins WHERE id=1').fetchone()
            if stored is None or json.loads(stored[0])!=pins: q.fail('immutable qualification input/code/runtime pins changed')
        db.connection.set_progress_handler(clock.sql,10000)
        validator=q.jsonschema_rs.Draft202012Validator(schema,validate_formats=True)
        types={v['id'] for v in contract['types'].values()}
        steps=0
        while state['phase']!='done':
            clock.check()
            if max_steps is not None and steps>=max_steps: raise Paused()
            if state['phase'] in ('hash','final-hash'):
                if state['package']==len(packages):
                    state['phase']='global' if state['phase']=='hash' else 'evidence'
                else:
                    info=packages[state['package']]
                    directory,manifest,mh,admission,assets,files,sources,apins=info
                    n=state['asset']; group=assets[n:n+hash_workers]
                    if group:
                        items=[(directory/e['key'],e,apins[n+i]) for i,e in enumerate(group)]
                        with ThreadPoolExecutor(max_workers=min(hash_workers,len(items))) as pool:
                            list(pool.map(lambda item:checked_asset(item,clock),items))
                        state['asset']+=len(group)
                        if state['phase']=='hash':
                            state['aggregate']['assets']=state['aggregate'].get('assets',0)+len(group)
                    elif state['phase']=='hash': state.update(phase='packets',asset=0)
                    else: state.update(package=state['package']+1,asset=0)
            elif state['phase']=='packets':
                info=packages[state['package']]
                directory,manifest,mh,admission,assets,files,sources,apins=info
                if state['asset']==len(files):
                    if pipeline is not None:
                        pipeline.close(); pipeline=None; db.spool_reserved_bytes=0; db.spool_root=None
                    finish_package(info,state)
                else:
                    entry=files[state['asset']]; path=directory/entry['key']
                    if pipeline is None:
                        actual_workers=min(packet_workers,len(files)-state['asset'])
                        spool=Path(tempfile.mkdtemp(prefix=scratch.name+'.shards-',dir=scratch.parent))
                        # Reservation is within existing60GiB scratch; not extra capacity.
                        db.spool_root=spool
                        db.spool_reserved_bytes=actual_workers*shard_budget_bytes
                        db.check_budget()
                        remaining=[(directory/e['key'],e) for e in files[state['asset']:]]
                        pipeline=workers.Pipeline(spool,remaining,sb,cb,clock.end,actual_workers,
                                                  worker_memory_bytes,shard_budget_bytes,db.spool_reserved_bytes)
                    shard=pipeline.take(clock)
                    clock.check()
                    if "error" in shard: q.fail(f'asset worker {shard["errorType"]}: {shard["error"]}')
                    try: workers.merge(db.connection,shard)
                    except workers.q.QualificationError as error: q.fail(str(error))
                    aggregate=Counter(state['aggregate']); aggregate.update(shard['aggregate'])
                    observed=Counter(state['observed']); observed.update(shard['observed'])
                    state.update(aggregate=dict(aggregate),observed=dict(observed),asset=state['asset']+1)
            elif state['phase']=='global': page(db,state,page_rows,clock)
            elif state['phase']=='evidence':
                # Re-read manifests/stat pins immediately before creating immutable evidence.
                if inventory(dirs,clock)[1]!=package_pins: q.fail('inputs changed before evidence')
                state['result']={'schemaVersion':'offmenu-common-expansion-qualification/1',
                    'status':'all-packages-streamed-global-identities-references-and-provenance-checked',
                    'schemaByteSha256':pins['schema'],'contractByteSha256':pins['contract'],
                    'contractVersion':contract['schemaVersion'],'schemaId':schema.get('$id'),
                    'packageCount':len(state['packages']),'packages':state['packages'],
                    'aggregateObservedCounts':state['aggregate'],'database':state['database'],
                    'diskGuardBytes':q.MINIMUM_FREE_BYTES,'scratchBudgetBytes':pins['budget'],
                    'seconds':round(time.time()-state['started'],3),'contractTextIdentityRule':contract['textIdentityRule']}
                state['phase']='done'
            save(db,state); steps+=1
            if 'shard' in locals() and shard is not None:
                db.connection.execute('DETACH DATABASE asset')
                pipeline.consumed(shard); shard=None
        result=state['result']; raw=json.dumps(result,ensure_ascii=False,indent=2,sort_keys=True)+'\n'
        evidence.parent.mkdir(parents=True,exist_ok=True)
        if evidence.exists():
            if evidence.read_text()!=raw: q.fail('existing evidence differs from committed result')
        else:
            with tempfile.NamedTemporaryFile(mode='w', prefix=evidence.name+'.pending-',
                                             dir=evidence.parent, delete=False) as f:
                tmp=Path(f.name)
                f.write(raw); f.flush(); os.fsync(f.fileno())
            # No replace of unrelated existing evidence, including races.
            os.link(tmp,evidence); tmp.unlink()
            fd=os.open(evidence.parent,os.O_DIRECTORY); os.fsync(fd); os.close(fd)
        return result
    except (Paused,sqlite3.OperationalError) as error:
        if isinstance(error,sqlite3.OperationalError) and not clock.sql(): raise
        if db: db.connection.rollback()
        return {'status':'qualification-paused','scratch':str(scratch),'evidenceWritten':False}
    finally:
        if pipeline: pipeline.close()
        if db: db.connection.close()
        lock.close()
        for sig,handler in old.items(): signal.signal(sig,handler)

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('evidence',type=Path); p.add_argument('scratch',type=Path)
    p.add_argument('--scratch-budget-gib',type=float,default=60)
    p.add_argument('--resume',action='store_true'); p.add_argument('--max-seconds',type=float,default=1500)
    p.add_argument('--hash-workers',type=int,default=256); p.add_argument('--page-rows',type=int,default=10000)
    p.add_argument('--packet-workers',type=int,default=256)
    p.add_argument('--worker-memory-mib',type=int,default=128)
    p.add_argument('--shard-budget-mib',type=int,default=64)
    p.add_argument('packages',nargs='+',type=Path)
    a=p.parse_args()
    try:
        result=qualify(a.evidence,a.scratch,a.packages,a.scratch_budget_gib,a.resume,a.max_seconds,a.hash_workers,a.page_rows,packet_workers=a.packet_workers,
                       worker_memory_bytes=a.worker_memory_mib*1024**2,shard_budget_bytes=a.shard_budget_mib*1024**2)
        print(json.dumps(result,ensure_ascii=False)); return 75 if result.get('status')=='qualification-paused' else 0
    except q.QualificationError as e:
        print(json.dumps({'status':'qualification-failed','error':str(e)}),file=sys.stderr); return 2
if __name__=='__main__': sys.exit(main())
