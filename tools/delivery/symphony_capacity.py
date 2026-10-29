"""Durable, cooperative host admission for bounded native coding sessions."""
from contextlib import contextmanager
import fcntl
import hashlib
import json
import math
import os
from pathlib import Path, PurePosixPath
import re
import sqlite3
import time

POLICY_PATH = Path(__file__).with_name('capacity-policy.json')
BRANCH = 'feature/langgraph-delivery-standardization'


class AdmissionError(RuntimeError):
    pass


def digest(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':')).encode()).hexdigest()


def positive(value, name, zero=False):
    if type(value) is not int or value < (0 if zero else 1):
        raise AdmissionError('invalid_'+name)
    return value


def scope(value):
    if (not isinstance(value,str) or not value or value.startswith('/') or '\\' in value
        or any(x in value for x in ['*','?','[','\x00','\n'])
        or any(x in ('','.','..') for x in value.split('/'))
        or value.split('/')[0] in ('.git','.delivery','data','output','node_modules','.cache')):
        raise AdmissionError('invalid_write_scope')
    return value


def overlap(a,b):
    return a==b or a.startswith(b+'/') or b.startswith(a+'/')


def host_snapshot(path):
    values={}
    for line in Path('/proc/meminfo').read_text().splitlines():
        if line.startswith('MemAvailable:'):values['available_memory_bytes']=int(line.split()[1])*1024
    fs=os.statvfs(path)
    return dict(values,cpu_millis=len(os.sched_getaffinity(0))*1000,
                available_disk_bytes=fs.f_bavail*fs.f_frsize)


class Pool:
    def __init__(self,path,policy=None):
        self.path=Path(path)
        self.policy=policy or json.loads(POLICY_PATH.read_text())
        for p in (self.path,*self.path.parents):
            if p.is_symlink():raise AdmissionError('symlink_pool')
        self.path.mkdir(parents=True,exist_ok=True,mode=0o700)
        for name in ('state.sqlite','pool.lock'):
            if (self.path/name).is_symlink():raise AdmissionError('symlink_pool')
        with self._transaction() as db:
            db.execute('CREATE TABLE IF NOT EXISTS leases (id TEXT PRIMARY KEY, binding TEXT NOT NULL, fingerprint TEXT NOT NULL, status TEXT NOT NULL, outcome TEXT, created REAL NOT NULL)')
            db.execute('CREATE TABLE IF NOT EXISTS events (sequence INTEGER PRIMARY KEY, id TEXT NOT NULL, event TEXT NOT NULL, at REAL NOT NULL)')

    @contextmanager
    def _transaction(self):
        fd=os.open(self.path/'pool.lock',os.O_CREAT|os.O_RDWR|os.O_NOFOLLOW,0o600)
        fcntl.flock(fd,fcntl.LOCK_EX)
        db=sqlite3.connect(self.path/'state.sqlite',timeout=30)
        os.chmod(self.path/'state.sqlite',0o600)
        try:
            db.execute('BEGIN IMMEDIATE');yield db;db.commit()
        except BaseException:
            db.rollback();raise
        finally:
            db.close();os.close(fd)

    def _event(self,db,task,event):
        db.execute('INSERT INTO events(id,event,at) VALUES(?,?,?)',(task,event,time.time()))

    def _rows(self,db):
        return [{'id':r[0],'binding':json.loads(r[1]),'fingerprint':r[2],'status':r[3],'outcome':r[4]}
                for r in db.execute('SELECT id,binding,fingerprint,status,outcome FROM leases ORDER BY id')]

    def status(self):
        with self._transaction() as db:return self._rows(db)

    def admit(self,task_id,binding,provider,host):
        if not isinstance(task_id,str) or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_-]{0,79}',task_id):raise AdmissionError('invalid_task_id')
        if set(binding)!={'branch','head','owner','write_roots','resources','task_sha256'}:raise AdmissionError('invalid_binding_fields')
        if binding['branch']!=BRANCH or not re.fullmatch(r'[0-9a-f]{40}',str(binding['head'])):raise AdmissionError('invalid_source_identity')
        if not isinstance(binding['owner'],str) or not binding['owner'].strip():raise AdmissionError('invalid_owner')
        paths=binding['write_roots']
        if not isinstance(paths,list) or not paths or len(paths)>64 or len(set(paths))!=len(paths):raise AdmissionError('invalid_write_scope')
        for p in paths:scope(p)
        resources=binding['resources']
        if not isinstance(resources,dict) or set(resources)!={'cpu_millis','memory_bytes','io_slots','output_bytes'}:raise AdmissionError('invalid_resources')
        for k,v in resources.items():positive(v,k,k=='output_bytes')
        if not isinstance(binding['task_sha256'],str) or not re.fullmatch(r'[0-9a-f]{64}',binding['task_sha256']):raise AdmissionError('invalid_task_digest')
        fingerprint=digest(binding)
        now=time.time();ttl=self.policy['symphony']['provider_proof_ttl_seconds']
        checked=provider.get('checked_at')
        if (provider.get('route')!='codex-chatgpt' or provider.get('available') is not True
            or type(checked) not in (int,float) or not math.isfinite(checked)
            or checked>now+5 or now-checked>ttl):raise AdmissionError('provider_unavailable_or_stale')
        slots=positive(provider.get('session_ceiling'),'provider_sessions')
        with self._transaction() as db:
            rows=self._rows(db);previous=next((r for r in rows if r['id']==task_id),None)
            if previous:
                if previous['fingerprint']!=fingerprint:raise AdmissionError('immutable_binding_conflict')
                if previous['status']!='running':raise AdmissionError('reconcile_or_new_task_required')
                return dict(previous,reused=True)
            active=[r for r in rows if r['status'] in ('running','cancel_requested','uncertain')]
            if len(active)>=min(self.policy['symphony']['max_concurrent_agents'],self.policy['symphony']['provider_session_ceiling'],slots):raise AdmissionError('capacity_sessions')
            for r in active:
                if any(overlap(a,b) for a in paths for b in r['binding']['write_roots']):raise AdmissionError('ownership_conflict')
            demands=[r['binding']['resources'] for r in active]+[resources]
            h=self.policy['host']
            ceilings={'cpu_millis':min(self.policy['symphony']['cpu_budget_millis'],max(0,positive(host.get('cpu_millis'),'host_cpu')-h['cpu_reserve']*1000)),
                      'memory_bytes':min(self.policy['symphony']['memory_budget_bytes'],positive(host.get('available_memory_bytes'),'host_memory')-h['memory_reserve_bytes']),
                      'io_slots':self.policy['symphony']['io_slots'],
                      'output_bytes':positive(host.get('available_disk_bytes'),'host_disk')-h['disk_reserve_bytes']}
            for key,limit in ceilings.items():
                if sum(r[key] for r in demands)>limit:raise AdmissionError('capacity_'+key)
            db.execute('INSERT INTO leases VALUES(?,?,?,?,?,?)',(task_id,json.dumps(binding,sort_keys=True),fingerprint,'running',None,now))
            self._event(db,task_id,'admitted')
            return {'id':task_id,'binding':binding,'fingerprint':fingerprint,'status':'running','reused':False}

    def cancel(self,task_id):
        with self._transaction() as db:
            row=db.execute('SELECT status FROM leases WHERE id=?',(task_id,)).fetchone()
            if not row:raise AdmissionError('unknown_task')
            if row[0] not in ('finished','failed'):
                db.execute('UPDATE leases SET status=? WHERE id=?',('cancel_requested',task_id));self._event(db,task_id,'cancel_requested')

    def finish(self,task_id,process_tree_gone,outcome):
        if process_tree_gone is not True or outcome not in ('succeeded','failed','cancelled','stopped'):raise AdmissionError('process_reconciliation_required')
        with self._transaction() as db:
            row=db.execute('SELECT status,outcome FROM leases WHERE id=?',(task_id,)).fetchone()
            if not row:raise AdmissionError('unknown_task')
            if row[0] in ('finished','failed'):
                if row[1]!=outcome:raise AdmissionError('terminal_outcome_conflict')
                return
            if row[0]=='cancel_requested' and outcome=='succeeded':raise AdmissionError('cancelled_task_cannot_succeed')
            db.execute('UPDATE leases SET status=?,outcome=? WHERE id=?',('finished' if outcome in ('succeeded','stopped') else 'failed',outcome,task_id))
            self._event(db,task_id,'reconciled_'+outcome)
