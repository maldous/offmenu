#!/usr/bin/env python3
"""Journal an exact existing checkpoint's implementation-only pin transition.
Run ONLY after the active coordinator and all its children are verified stopped.
No graph rows, asset cursors, counters, manifests, schema or runtime pins change.
"""
import argparse
import fcntl
import hashlib
import importlib.util
import json
from pathlib import Path
import sqlite3
import time
import uuid

OLD='b7745a9d699fe742fe9858ab173b5604faec153075ad473c10572c02fb1b80b0'
NEW=Path(__file__).with_name('qualify-common-expansion-resumable.py')
def migrate(scratch,apply=False,expected_wrapper=None,expected_helper=None):
    with open(str(scratch)+'.lock','a+') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        if not scratch.is_file(): raise ValueError('existing scratch required')
        db=sqlite3.connect(scratch,timeout=0)
        try:
            db.execute('PRAGMA journal_mode=DELETE'); db.execute('PRAGMA synchronous=FULL')
            db.execute('BEGIN IMMEDIATE')
            raw=db.execute('SELECT value FROM run_pins WHERE id=1').fetchone()[0]
            progress=db.execute('SELECT value FROM checkpoint WHERE id=1').fetchone()[0]
            before=json.loads(raw); state=json.loads(progress)
            if before['orchestrator']!=OLD or 'workerHelper' in before:
                raise ValueError('not the exact reviewed sequential checkpoint implementation')
            if state['phase']=='done' or Path(before['evidence']).exists():
                raise ValueError('completed proof must not be migrated')
            for name,key in [('qualify-common-expansion.py','original')]:
                if hashlib.sha256(NEW.with_name(name).read_bytes()).hexdigest()!=before[key]:
                    raise ValueError('original validation implementation changed')
            for filename,key in [('common-data.schema.json','schema'),('common-data-contract.json','contract')]:
                if hashlib.sha256((NEW.parent.parent/'corpus'/filename).read_bytes()).hexdigest()!=before[key]:
                    raise ValueError('schema/contract changed')
            after=dict(before)
            after['orchestrator']=hashlib.sha256(NEW.read_bytes()).hexdigest()
            after['workerHelper']=hashlib.sha256(NEW.with_name('qualification_asset_workers.py').read_bytes()).hexdigest()
            if apply and (after['orchestrator']!=expected_wrapper or after['workerHelper']!=expected_helper):
                raise ValueError('explicit approved target wrapper/helper hashes required and must match')
            record={'id':uuid.uuid4().hex,'timestamp':time.time(),'priorPins':before,'nextPins':after,
                    'checkpointSha256':hashlib.sha256(progress.encode()).hexdigest(),
                    'semanticChange':False,'graphRowsChanged':False,'progressChanged':False}
            if apply:
                db.execute('CREATE TABLE IF NOT EXISTS implementation_migrations (id TEXT PRIMARY KEY, value TEXT NOT NULL)')
                db.execute('INSERT INTO implementation_migrations VALUES (?,?)',(record['id'],json.dumps(record,sort_keys=True)))
                db.execute('UPDATE run_pins SET value=? WHERE id=1',(json.dumps(after,sort_keys=True,separators=(',',':')),))
                db.commit()
            else: db.rollback()
            return {'applied':apply,'migrationId':record['id'],'priorCode':OLD,'nextCode':after['orchestrator'],
                    'helperCode':after['workerHelper'],'checkpointUnchanged':True,'phase':state['phase'],
                    'package':state['package'],'asset':state['asset']}
        finally: db.close()
if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__); parser.add_argument('scratch',type=Path)
    parser.add_argument('--apply',action='store_true')
    parser.add_argument('--expected-wrapper'); parser.add_argument('--expected-helper'); args=parser.parse_args()
    print(json.dumps(migrate(args.scratch,args.apply,args.expected_wrapper,args.expected_helper)))
