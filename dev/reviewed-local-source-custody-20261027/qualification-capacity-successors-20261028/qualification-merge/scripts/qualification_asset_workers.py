"""Disposable exact-validator asset fingerprints; sole parent merges global proof.

Worker DBs are NOT qualification evidence, never reused between invocations, and
need no crash durability. Parent's FULL rollback-journal transaction remains the
only admission boundary. All original validation functions execute unchanged.
"""
from collections import Counter
from concurrent.futures import ProcessPoolExecutor, TimeoutError as FutureTimeout
import gzip
import hashlib
import importlib.util
import json
import multiprocessing
import os
from pathlib import Path
import resource
import sqlite3
import time

QPATH=Path(__file__).with_name('qualify-common-expansion.py')
SPEC=importlib.util.spec_from_file_location('worker_original_qualification',QPATH)
q=importlib.util.module_from_spec(SPEC); SPEC.loader.exec_module(q)
SCHEMA=None
TYPES=None


def initialize(schema_bytes,contract_bytes,memory_bytes):
    global SCHEMA,TYPES
    if memory_bytes:
        resource.setrlimit(resource.RLIMIT_AS,(memory_bytes,memory_bytes))
    SCHEMA=q.jsonschema_rs.Draft202012Validator(json.loads(schema_bytes),validate_formats=True)
    TYPES={v['id'] for v in json.loads(contract_bytes)['types'].values()}


def checked_time(deadline):
    if time.monotonic()>=deadline: raise TimeoutError('asset worker invocation deadline')


def work_inner(task):
    path,entry,db_path,deadline,per_asset_budget=task
    path=Path(path); db_path=Path(db_path)
    # Exclusive path reservation ensures no unknown prior file is overwritten.
    fd=os.open(db_path,os.O_CREAT|os.O_EXCL|os.O_WRONLY,0o600); os.close(fd)
    db=q.Database(db_path,per_asset_budget)
    db.connection.execute('PRAGMA cache_size=-8192')
    page_size=db.connection.execute('PRAGMA page_size').fetchone()[0]
    db.connection.execute(f'PRAGMA max_page_count={per_asset_budget//page_size}')
    observed,stats=Counter(),Counter()
    try:
        with gzip.open(path,'rt',encoding='utf-8') as f:
            for lineno,line in enumerate(f,1):
                checked_time(deadline)
                if not line.strip(): continue
                try: packet=json.loads(line)
                except json.JSONDecodeError as error: q.fail(f'{path}:{lineno}: invalid JSON: {error}')
                q.validate_packet(packet,f'{path.name}:{lineno}',SCHEMA,TYPES,db,stats)
                observed.update(q.packet_counts(packet))
                db.commit_if_needed()
        if observed['packets']!=entry['packets']:
            q.fail(f'{path}: observed {observed["packets"]} packets, manifest declares {entry["packets"]}')
        db.connection.commit(); db.check_budget()
    finally:
        db.connection.close()
    checked_time(deadline)
    return {'path':str(db_path),'sha256':q.sha_file(db_path),'bytes':db_path.stat().st_size,
            'observed':dict(observed),'aggregate':dict(stats)}


def work(task):
    try: return work_inner(task)
    except Exception as error: return {"error": str(error), "errorType":type(error).__name__}


def prepare_merge(connection):
    """Connection-local guards for single-pass identity-preserving UPSERTs.

The successful duplicate case performs no UPDATE. A conflicting duplicate takes
the UPDATE branch, where a TEMP trigger aborts the statement before any change.
These guards neither change the durable schema nor weaken the caller's atomic
asset/checkpoint transaction.
"""
    for table,field,message in (
        ('texts','identity_sha256','repeated text id has different language/value/hash/citations'),
        ('citations','canonical_sha256','repeated citation id has different canonical content'),
    ):
        connection.execute(f'''CREATE TEMP TRIGGER qualification_{table}_conflict
            BEFORE UPDATE OF {field} ON main.{table}
            WHEN NEW.{field} != OLD.{field}
            BEGIN SELECT RAISE(ABORT, '{message}'); END''')


def merge(connection,result):
    """Attach closed worker DB, reject all global conflicts, merge inside parent tx.

Caller must begin/commit (including progress marker) and detach after commit or
rollback. No independent shard can resolve cross-asset references; final original
reference/translation scans are still mandatory.
"""
    path=Path(result['path'])
    if path.stat().st_size!=result['bytes'] or q.sha_file(path)!=result['sha256']:
        q.fail('disposable asset fingerprint bytes changed before merge')
    connection.execute('ATTACH DATABASE ? AS asset',(path.resolve().as_uri()+'?mode=ro',))
    connection.execute('BEGIN IMMEDIATE')
    for table,field in [('texts','identity_sha256'),('citations','canonical_sha256')]:
        try:
            # WHERE 1 disambiguates SELECT's JOIN-ON from UPSERT's ON CONFLICT.
            connection.execute(f'''INSERT INTO main.{table}
                SELECT * FROM asset.{table} WHERE 1 ORDER BY id_sha256
                ON CONFLICT(id_sha256) DO UPDATE SET {field}=excluded.{field}
                WHERE {table}.{field} != excluded.{field}''')
        except sqlite3.IntegrityError as error:
            # RAISE(ABORT) rolls back this whole statement; the caller owns the
            # rollback of earlier statements and the checkpoint in this asset.
            if error.sqlite_errorcode != sqlite3.SQLITE_CONSTRAINT_TRIGGER:
                raise
            q.fail(str(error))
    try:
        connection.execute('INSERT INTO main.ids SELECT * FROM asset.ids ORDER BY kind,id_sha256')
    except sqlite3.IntegrityError as error:
        # Successful assets need only one PK probe per ID. This diagnostic join
        # is needed only after INSERT has already rejected a duplicate.
        if error.sqlite_errorcode != sqlite3.SQLITE_CONSTRAINT_PRIMARYKEY:
            raise
        duplicate=connection.execute('SELECT kind FROM asset.ids s JOIN main.ids t USING(kind,id_sha256) LIMIT 1').fetchone()
        if duplicate: q.fail(f'duplicate global {duplicate[0]} id')
        raise
    for table in ('references_pending','translation_sources'):
        connection.execute(f'INSERT OR IGNORE INTO main.{table} SELECT * FROM asset.{table}')


class Pipeline:
    def __init__(self,root,entries,schema_bytes,contract_bytes,deadline,workers,memory_bytes,asset_budget,spool_budget):
        self.root=Path(root); self.entries=iter(entries); self.deadline=deadline
        self.asset_budget,self.spool_budget=asset_budget,spool_budget
        self.pending=[]; self.counter=0; self.worker_count=workers
        self.pool=ProcessPoolExecutor(max_workers=workers,mp_context=multiprocessing.get_context('spawn'),
                                     initializer=initialize,initargs=(schema_bytes,contract_bytes,memory_bytes))
        try:
            for _ in range(workers): self.refill()
        except BaseException:
            self.close(); raise
    def refill(self):
        try: path,entry=next(self.entries)
        except StopIteration: return
        # Bound worst-case pending shard scratch before submitting; known output
        # budget, not worker count, determines whether a candidate is admissible.
        if (len(self.pending)+1)*self.asset_budget>self.spool_budget:
            raise RuntimeError('worker fingerprint reservation exceeds spool budget')
        self.counter+=1
        dest=self.root/f'asset-{self.counter:08d}.sqlite'
        task=(str(path),entry,str(dest),self.deadline,self.asset_budget)
        self.pending.append(self.pool.submit(work,task))
    def take(self,clock):
        result=self.pending.pop(0)
        while True:
            clock.check()
            try: return result.result(timeout=0.25)
            except FutureTimeout: continue
    def consumed(self,result):
        # Only delete a current invocation-generated, checked closed shard after
        # its exact contents AND checkpoint have durably entered global DB.
        p=Path(result['path'])
        if p.parent!=self.root or q.sha_file(p)!=result['sha256']:
            q.fail('refusing to clean changed or foreign disposable asset fingerprint')
        p.unlink()
        self.refill()
    def close(self):
        # Python3.11 lacks public terminate_workers(); runtime is pinned. Capture
        # exactly this executor's child handles, terminate, then join through its
        # manager. No pgrep/global process killing and no initializer respawn loop.
        processes=list((self.pool._processes or {}).values())
        for process in processes:
            if process.is_alive(): process.terminate()
        self.pool.shutdown(wait=True,cancel_futures=True)
        for process in processes: process.join()
