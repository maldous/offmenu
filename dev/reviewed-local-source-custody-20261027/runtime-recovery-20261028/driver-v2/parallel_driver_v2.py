#!/usr/bin/env python3
"""Bounded cooperating-lane fanout INSIDE existing job_runner write supervision.
Not an extra sandbox: lane declarations are scheduling contracts for reviewed commands.
The existing outer supervisor owns global exclusion, cancellation and descendant cleanup.
"""
import argparse
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import resource
import selectors
import signal
import stat
import subprocess
import sys
import time
import uuid

PLATFORM = Path('/offmenu/data/.offmenu-platform')
IDENT = re.compile(r'[A-Za-z0-9][A-Za-z0-9_.-]{0,79}\Z')
LOG_LIMIT = 1024 * 1024
GIB = 1024**3
STOP = False


def atomic(path, obj):
    tmp = path.with_name('.' + path.name + '.' + uuid.uuid4().hex)
    fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    try:
        with os.fdopen(fd, 'w') as f:
            json.dump(obj, f, sort_keys=True); f.write('\n'); f.flush(); os.fsync(f.fileno())
        os.replace(tmp, path)
        fd = os.open(path.parent, os.O_DIRECTORY)
        try: os.fsync(fd)
        finally: os.close(fd)
    finally:
        if tmp.exists(): tmp.unlink()


def beneath(path, root):
    p = Path(path)
    if not p.is_absolute() or '..' in p.parts: raise ValueError('Nonabsolute or parent path')
    if p == root or root not in p.parents: raise ValueError('Outside platform scope')
    for cur in (p, *p.parents):
        if cur.is_symlink(): raise ValueError('Symlink path')
    return p


def read_json(path):
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    with os.fdopen(fd) as f:
        raw = f.read(131073)
    if len(raw) > 131072: raise ValueError('Plan too large')
    return json.loads(raw)


def validate(plan, root=PLATFORM):
    if set(plan) != {'version','run_id','timeout_seconds','reserve_bytes','lanes'} or plan['version'] != 1:
        raise ValueError('Plan schema')
    if not IDENT.fullmatch(plan['run_id']): raise ValueError('Run id')
    if type(plan['timeout_seconds']) is not int or not 5 <= plan['timeout_seconds'] <= 1500: raise ValueError('Deadline')
    if type(plan['reserve_bytes']) is not int or plan['reserve_bytes'] < 70*GIB: raise ValueError('Disk reserve')
    lanes = plan['lanes']
    if not isinstance(lanes,list) or not 1 <= len(lanes) <= 6: raise ValueError('Lane count')
    ids, dirs = set(), []
    for lane in lanes:
        if set(lane) != {'id','argv','output_root','cpu_count','memory_bytes','memory_processes','additional_output_budget_bytes','source_pins'}: raise ValueError('Lane schema')
        if not IDENT.fullmatch(lane['id']) or lane['id'] in ids: raise ValueError('Lane id')
        ids.add(lane['id'])
        d = beneath(lane['output_root'], root)
        if any(d == x or d in x.parents or x in d.parents for x in dirs): raise ValueError('Overlapping output roots')
        dirs.append(d)
        if type(lane['cpu_count']) is not int or not 1 <= lane['cpu_count'] <= 16: raise ValueError('CPU budget')
        if type(lane['memory_bytes']) is not int or not GIB <= lane['memory_bytes'] <= 8*GIB: raise ValueError('Memory budget')
        if type(lane['additional_output_budget_bytes']) is not int or not 0 <= lane['additional_output_budget_bytes'] <= 64*GIB: raise ValueError('Lane output budget')
        if type(lane['memory_processes']) is not int or not 1 <= lane['memory_processes'] <= 17: raise ValueError('Declared process budget')
        args = lane['argv']
        if not isinstance(args,list) or not 1 <= len(args) <= 64 or any(not isinstance(a,str) or not a or '\0' in a or len(a)>4096 for a in args): raise ValueError('Argv')
        if args[0] not in ('/usr/bin/python3','/offmenu/.venv/bin/python3') or len(args)<4 or args[1] != '-I': raise ValueError('Reviewed isolated Python command required')
        worker_flags=[a for a in args[3:] if a.startswith('--') and (a.split('=')[0]=='--workers' or '--workers'.startswith(a.split('=')[0]))]
        if worker_flags and worker_flags != ['--workers']: raise ValueError('Canonical unique --workers argument required')
        if '--workers' in args:
            i=args.index('--workers')
            if i+1>=len(args) or not args[i+1].isdigit(): raise ValueError('Explicit worker count required')
            n=int(args[i+1])
            if not 1<=n<=16 or lane['memory_processes'] < (1 if n==1 else n+1): raise ValueError('Parent plus worker memory budget understated')
        elif lane['memory_processes'] != 1: raise ValueError('Multi-process lane requires reviewed explicit worker argument')
        script = beneath(args[2], root)
        pins = lane['source_pins']
        if not isinstance(pins,list) or not 1 <= len(pins) <= 32: raise ValueError('Source pins')
        pinpaths = set()
        for pin in pins:
            if set(pin) != {'path','sha256'} or not re.fullmatch('[0-9a-f]{64}',pin['sha256']): raise ValueError('Source pin')
            path = beneath(pin['path'], root)
            if str(path) in pinpaths: raise ValueError('Duplicate pin')
            pinpaths.add(str(path))
        if str(script) not in pinpaths: raise ValueError('Entrypoint not pinned')
    if sum(x['additional_output_budget_bytes'] for x in lanes)>64*GIB: raise ValueError('Aggregate output budget')
    if sum(x['memory_bytes']*x['memory_processes'] for x in lanes)>32*GIB: raise ValueError('Aggregate declared memory budget')
    return plan


def verify_pins(lanes, deadline=None):
    deadline=min(deadline if deadline is not None else float('inf'),time.monotonic()+5)
    total=0
    for lane in lanes:
        for pin in lane['source_pins']:
            if time.monotonic()>=deadline: raise ValueError('Source preflight deadline')
            p=Path(pin['path'])
            fd=os.open(p,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK)
            with os.fdopen(fd,'rb') as f:
                before=os.fstat(f.fileno())
                if not stat.S_ISREG(before.st_mode) or before.st_size>8*1024**2: raise ValueError('Regular bounded source required')
                total+=before.st_size
                if total>32*1024**2: raise ValueError('Total source pin byte budget')
                h=hashlib.sha256();count=0
                while True:
                    if time.monotonic()>=deadline: raise ValueError('Source preflight deadline')
                    chunk=f.read(65536)
                    if not chunk: break
                    count+=len(chunk)
                    if count>8*1024**2: raise ValueError('Source pin grew past byte budget')
                    h.update(chunk)
                after=os.fstat(f.fileno())
            current=p.stat(follow_symlinks=False)
            identity=lambda st:(st.st_dev,st.st_ino,st.st_size,st.st_mtime_ns,st.st_ctime_ns)
            if identity(before)!=identity(after) or identity(after)!=identity(current) or count!=before.st_size or h.hexdigest()!=pin['sha256']:
                raise ValueError('Source changed or hash mismatch')


def available_memory():
    for line in Path('/proc/meminfo').read_text().splitlines():
        if line.startswith('MemAvailable:'): return int(line.split()[1])*1024
    raise ValueError('Memory availability unknown')


def free_bytes(root):
    s=os.statvfs(root); return s.f_bavail*s.f_frsize


def allocation(plan, affinity, memory):
    cpus=sorted(affinity)
    need=sum(x['cpu_count'] for x in plan['lanes'])
    if need>max(0,len(cpus)-4): raise ValueError('Four control CPUs must remain unassigned')
    if sum(x['memory_bytes']*x['memory_processes'] for x in plan['lanes'])>memory-8*GIB: raise ValueError('Eight GiB control memory headroom required')
    result=[]
    for lane in plan['lanes']:
        result.append(cpus[:lane['cpu_count']]); cpus=cpus[lane['cpu_count']:]
    return result


def child_setup(cpus, memory):
    os.sched_setaffinity(0,cpus)
    resource.setrlimit(resource.RLIMIT_AS,(memory,memory))
    resource.setrlimit(resource.RLIMIT_CORE,(0,0))


def terminate(items):
    # Four-second overall budget, not a per-lane multiplier. Outer supervisor
    # additionally verifies/kills all descendants, including setsid escapees.
    for item in items:
        try: os.killpg(item['proc'].pid,signal.SIGTERM)
        except ProcessLookupError: pass
    end=time.monotonic()+2
    while time.monotonic()<end and any(x['proc'].poll() is None for x in items): time.sleep(.02)
    for item in items:
        try: os.killpg(item['proc'].pid,signal.SIGKILL)
        except ProcessLookupError: pass
    end=time.monotonic()+2
    for item in items:
        try: item['proc'].wait(timeout=max(0,end-time.monotonic()))
        except subprocess.TimeoutExpired: pass


def run(plan, root=PLATFORM):
    global STOP
    STOP=False; validate(plan,root)
    started=time.monotonic(); deadline=started+plan['timeout_seconds']
    # This driver must be launched through the existing outer write supervisor.
    markers=list((root/'locks').glob('execution-slot-*.inflight.json'))
    active=[read_json(p) for p in markers]
    if len(active)!=1 or active[0].get('mode')!='write': raise ValueError('Exactly one outer writer required')
    outer_timeout=active[0].get('timeout_seconds')
    if type(outer_timeout) is not int or plan['timeout_seconds'] > outer_timeout-20: raise ValueError('Outer deadline headroom required')
    outer_id=active[0].get('job_id')
    if not isinstance(outer_id,str) or not IDENT.fullmatch(outer_id): raise ValueError('Outer job identity')
    control=root/'jobs'/outer_id
    plan_bytes=json.dumps(plan,sort_keys=True,separators=(',',':')).encode()
    runroot=root/'parallel'/plan['run_id']
    beneath(str(runroot),root)
    runroot.parent.mkdir(mode=0o700,exist_ok=True)
    runroot.mkdir(mode=0o700) # Existing run requires reconciliation, never replays.
    receipt={'version':1,'run_id':plan['run_id'],'outer_job_id':outer_id,'plan_sha256':hashlib.sha256(plan_bytes).hexdigest(),
             'status':'preflight','lanes':[],'output_qualification_established':False,'outer_cleanup_verification_required':True}
    path=runroot/'receipt.json'; atomic(path,receipt)
    locks=[]; items=[]; logs=[]; sel=selectors.DefaultSelector()
    def stop(sig,frame):
        global STOP
        STOP=True
    old={s:signal.signal(s,stop) for s in (signal.SIGTERM,signal.SIGINT,signal.SIGHUP)}
    outcome='preflight_error'
    try:
        groups=allocation(plan,os.sched_getaffinity(0),available_memory())
        required_free=plan['reserve_bytes']+sum(x['additional_output_budget_bytes'] for x in plan['lanes'])+16*1024**2
        if free_bytes(root)<required_free: raise ValueError('Aggregate output and disk reserve unavailable')
        receipt['disk_admission']={'observed_free_bytes':free_bytes(root),'required_free_bytes':required_free,'shared_reserve_bytes':plan['reserve_bytes'],'declared_additional_output_bytes':sum(x['additional_output_budget_bytes'] for x in plan['lanes']), 'enforcement':'aggregate admission plus monitored free-space stop; producer output ceilings required'}
        verify_pins(plan['lanes'],deadline)
        # Lock ALL lane roots before launching any child. Keep locks through whole fanout.
        for lane in plan['lanes']:
            key=hashlib.sha256(lane['output_root'].encode()).hexdigest()
            fd=os.open(root/'locks'/('lane-'+key+'.lock'),os.O_RDWR|os.O_CREAT|os.O_NOFOLLOW,0o600)
            locks.append(fd); fcntl.flock(fd,fcntl.LOCK_EX|fcntl.LOCK_NB)
        for lane,cpus in zip(plan['lanes'],groups):
            if STOP or (control/'cancel.json').exists(): outcome='cancelled'; break
            if time.monotonic()>=deadline: outcome='deadline'; break
            record={'id':lane['id'],'output_root':lane['output_root'],'status':'running','cpu_affinity':cpus,
                    'per_process_virtual_memory_limit':lane['memory_bytes'],'declared_python_processes':lane['memory_processes'],'declared_lane_memory_budget':lane['memory_bytes']*lane['memory_processes'],'log_bytes':{},'output_bytes':{}}
            proc=subprocess.Popen(lane['argv'],cwd='/offmenu',stdin=subprocess.DEVNULL,stdout=subprocess.PIPE,stderr=subprocess.PIPE,
                env={'PATH':'/usr/bin:/bin','LANG':'C','HOME':'/tmp/home','OMP_NUM_THREADS':'1','OPENBLAS_NUM_THREADS':'1','MKL_NUM_THREADS':'1'},
                start_new_session=True,close_fds=True,preexec_fn=lambda c=cpus,m=lane['memory_bytes']:child_setup(c,m))
            item={'proc':proc,'record':record};items.append(item);receipt['lanes'].append(record)
            for name,stream in (('stdout',proc.stdout),('stderr',proc.stderr)):
                fd=os.open(runroot/(lane['id']+'.'+name+'.log'),os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
                log=os.fdopen(fd,'wb');logs.append(log);record['log_bytes'][name]=0;record['output_bytes'][name]=0
                os.set_blocking(stream.fileno(),False);sel.register(stream,selectors.EVENT_READ,(item,name,log))
        else: outcome='running'
        receipt['status']=outcome;atomic(path,receipt); last=0
        while outcome=='running' and (sel.get_map() or any(x['proc'].poll() is None for x in items)):
            if STOP or (control/'cancel.json').exists(): outcome='cancelled';break
            if time.monotonic()>=deadline: outcome='deadline';break
            if free_bytes(root)<plan['reserve_bytes']: outcome='disk_reserve';break
            for key,_ in sel.select(.1):
                item,name,log=key.data;chunk=os.read(key.fileobj.fileno(),16384)
                if not chunk:sel.unregister(key.fileobj);continue
                r=item['record'];r['output_bytes'][name]+=len(chunk)
                keep=chunk[:max(0,LOG_LIMIT-r['log_bytes'][name])];log.write(keep);r['log_bytes'][name]+=len(keep)
            for item in items:
                code=item['proc'].poll()
                if code is not None:item['record'].update(status='exit_zero' if code==0 else 'exit_nonzero',exit_code=code)
            if time.monotonic()-last>=2: atomic(path,receipt);last=time.monotonic()
        if outcome=='running':outcome='commands_exited'
    except Exception as exc:
        receipt['error_class']=type(exc).__name__
        outcome='supervisor_error' if items else 'preflight_error'
    finally:
        terminate(items)
        for item in items:
            code=item['proc'].poll();item['record']['exit_code']=code
            if item['record']['status']=='running':item['record']['status']='interrupted' if outcome!='commands_exited' else ('exit_zero' if code==0 else 'exit_nonzero')
            for stream in (item['proc'].stdout,item['proc'].stderr):stream.close()
        for f in logs:f.flush();os.fsync(f.fileno());f.close()
        sel.close()
        for fd in reversed(locks):os.close(fd)
        for sig,handler in old.items():signal.signal(sig,handler)
        receipt['status']=outcome;receipt['finished_at']=time.time();atomic(path,receipt)
    return receipt


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('plan');args=p.parse_args()
    try:
        result=run(read_json(beneath(args.plan,PLATFORM)))
        print(json.dumps(result,sort_keys=True))
        return 0 if result['status']=='commands_exited' and all(x.get('exit_code')==0 for x in result['lanes']) else 1
    except Exception as exc:
        print(json.dumps({'status':'request_error','error_class':type(exc).__name__}));return 2

if __name__=='__main__':sys.exit(main())
