#!/usr/bin/env python3
"""Bounded cooperating-lane fanout INSIDE existing job_runner write supervision.
Not an extra sandbox: lane declarations are scheduling contracts for reviewed commands.
The existing outer supervisor owns admission, cancellation and descendant cleanup.
Legacy jobs retain global exclusion. Opt-in v3 jobs validate their own live reservation.
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
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    with os.fdopen(fd) as f:
        if not stat.S_ISREG(os.fstat(f.fileno()).st_mode): raise ValueError('Regular JSON required')
        raw = f.read(131073)
    if len(raw) > 131072: raise ValueError('Plan too large')
    return json.loads(raw)


def declared_memory(lane):
    if 'worker_memory_bytes' not in lane:return lane['memory_bytes']*lane['memory_processes']
    n=int(lane['argv'][lane['argv'].index('--workers')+1])
    return lane['memory_bytes']+n*lane['worker_memory_bytes']+(lane['memory_processes']-n-1)*lane.get('tracker_memory_bytes',lane['memory_bytes'])

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
        if set(lane)-{'worker_memory_bytes','tracker_memory_bytes'} != {'id','argv','output_root','cpu_count','memory_bytes','memory_processes','additional_output_budget_bytes','source_pins'}: raise ValueError('Lane schema')
        if not IDENT.fullmatch(lane['id']) or lane['id'] in ids: raise ValueError('Lane id')
        ids.add(lane['id'])
        d = beneath(lane['output_root'], root)
        if any(d == x or d in x.parents or x in d.parents for x in dirs): raise ValueError('Overlapping output roots')
        dirs.append(d)
        if type(lane['cpu_count']) is not int or not 1 <= lane['cpu_count'] <= 256: raise ValueError('CPU budget')
        if type(lane['memory_bytes']) is not int or not 256*1024**2 <= lane['memory_bytes'] <= 8*GIB: raise ValueError('Memory budget')
        if type(lane['additional_output_budget_bytes']) is not int or not 0 <= lane['additional_output_budget_bytes'] <= 64*GIB: raise ValueError('Lane output budget')
        if type(lane['memory_processes']) is not int or not 1 <= lane['memory_processes'] <= 258: raise ValueError('Declared process budget')
        args = lane['argv']
        if not isinstance(args,list) or not 1 <= len(args) <= 64 or any(not isinstance(a,str) or not a or '\0' in a or len(a)>4096 for a in args): raise ValueError('Argv')
        if args[0] not in ('/usr/bin/python3','/offmenu/.venv/bin/python3') or len(args)<4 or args[1] != '-I': raise ValueError('Reviewed isolated Python command required')
        worker_flags=[a for a in args[3:] if a!='--worker-memory-bytes' and a.startswith('--') and (a.split('=')[0]=='--workers' or '--workers'.startswith(a.split('=')[0]))]
        if worker_flags and worker_flags != ['--workers']: raise ValueError('Canonical unique --workers argument required')
        if '--workers' in args:
            i=args.index('--workers')
            if i+1>=len(args) or not args[i+1].isdigit(): raise ValueError('Explicit worker count required')
            n=int(args[i+1])
            if not 1<=n<=256 or lane['memory_processes'] < (1 if n==1 else n+1): raise ValueError('Parent plus worker memory budget understated')
        elif lane['memory_processes'] != 1: raise ValueError('Multi-process lane requires reviewed explicit worker argument')
        memory_flags=[a for a in args[3:] if a.startswith('--') and (a.split('=')[0]=='--worker-memory-bytes' or '--worker-memory-bytes'.startswith(a.split('=')[0]))]
        # --workers is distinct from --worker-memory-bytes; abbreviations of either are refused.
        if 'worker_memory_bytes' in lane:
            cap=lane['worker_memory_bytes']
            if type(cap) is not int or not 128*1024**2<=cap<=lane['memory_bytes']: raise ValueError('Worker memory cap')
            if memory_flags != ['--worker-memory-bytes'] or '--workers' not in args: raise ValueError('Explicit worker memory argument required')
            i=args.index('--worker-memory-bytes')
            if i+1>=len(args) or args[i+1]!=str(cap): raise ValueError('Worker memory argument mismatch')
            if lane['memory_processes'] not in (int(args[args.index('--workers')+1])+1,int(args[args.index('--workers')+1])+2): raise ValueError('Parent, workers and optional spawn tracker count required')
        elif memory_flags: raise ValueError('Worker memory argument not budgeted')
        tracker_flags=[a for a in args[3:] if a.startswith('--') and (a.split('=')[0]=='--tracker-memory-bytes' or '--tracker-memory-bytes'.startswith(a.split('=')[0]))]
        if 'tracker_memory_bytes' in lane:
            cap=lane['tracker_memory_bytes']
            if type(cap) is not int or cap!=128*1024**2 or 'worker_memory_bytes' not in lane: raise ValueError('Reviewed tracker cap required')
            if tracker_flags != ['--tracker-memory-bytes']: raise ValueError('Explicit tracker memory argument required')
            i=args.index('--tracker-memory-bytes')
            if i+1>=len(args) or args[i+1]!=str(cap): raise ValueError('Tracker memory argument mismatch')
            if lane['memory_processes']!=int(args[args.index('--workers')+1])+2: raise ValueError('Tracker process must be counted')
        elif tracker_flags: raise ValueError('Tracker memory argument not budgeted')
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


def allocation(plan, affinity, memory, capacity_admitted=False):
    cpus=sorted(affinity)
    need=sum(x['cpu_count'] for x in plan['lanes'])
    if need>max(0,len(cpus)-(0 if capacity_admitted else 4)): raise ValueError('CPU reservation or control headroom unavailable')
    if sum(declared_memory(x) for x in plan['lanes'])>memory-8*GIB: raise ValueError('Eight GiB control memory headroom required')
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


def sample_descendants(items):
    """Only known children and their child IDs; never read cmdline/environ."""
    pending=[item['proc'].pid for item in items if item['proc'].poll() is None]
    seen=set();rss=0;observed=0;errors=0;max_vm=0;max_rss=0
    while pending and len(seen)<512:
        pid=pending.pop()
        if pid in seen: continue
        seen.add(pid)
        try:
            raw=Path('/proc',str(pid),'stat').read_text()[:8192]
            fields=raw.rsplit(')',1)[1].split()
            one_rss=max(0,int(fields[21]))*os.sysconf('SC_PAGE_SIZE');rss+=one_rss;observed+=1;max_rss=max(max_rss,one_rss);max_vm=max(max_vm,int(fields[20]))
            children=Path('/proc',str(pid),'task',str(pid),'children').read_text()[:8192]
            pending.extend(int(x) for x in children.split() if x.isdigit())
        except (OSError,ValueError,IndexError): errors+=1
    return {'process_count':observed,'rss_sum_bytes':rss,'read_errors':errors,'truncated':bool(pending),'max_process_virtual_bytes':max_vm,'max_process_rss_bytes':max_rss}


def paths_overlap(a,b):
    a,b=Path(a),Path(b)
    return a==b or a in b.parents or b in a.parents


def covers(roots,path):
    path=Path(path)
    return any(Path(r)==path or Path(r) in path.parents for r in roots)


def outer_reservation(plan, root, outer_job_id=None):
    """Inspect metadata only; v3 owns atomic admission and holds slot through cleanup.
    Explicit ID plus marker/receipt request digest selects this reservation; it is
    not a security credential. Commands remain trusted cooperating participants.
    """
    admission=None
    try:
        if outer_job_id is not None:
            if not isinstance(outer_job_id,str) or not IDENT.fullmatch(outer_job_id): raise ValueError('Outer job identity')
            admission=os.open(root/'locks'/'capacity-admission.lock',os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK)
            if not stat.S_ISREG(os.fstat(admission).st_mode): raise ValueError('Regular admission lock required')
            fcntl.flock(admission,fcntl.LOCK_SH|fcntl.LOCK_NB)
        markers=list((root/'locks').glob('execution-slot-*.inflight.json'))
        if len(markers)>64: raise ValueError('Too many reservations')
        active=[(p,read_json(p)) for p in markers]
        if any(not isinstance(r,dict) for _,r in active): raise ValueError('Invalid reservation')
        if outer_job_id is None:
            if len(active)!=1 or active[0][1].get('mode')!='write' or active[0][1].get('capacity_version') is not None:
                raise ValueError('Exactly one legacy outer writer required')
            own=active[0][1]
        else:
            selected=[(p,r) for p,r in active if r.get('job_id')==outer_job_id]
            if len(selected)!=1: raise ValueError('Unique own reservation required')
            marker,own=selected[0]
            match=re.fullmatch(r'execution-slot-([0-9]+)\.inflight\.json',marker.name)
            if not match or not 0<=int(match[1])<64: raise ValueError('Slot identity')
            if own.get('capacity_version')!=1 or own.get('mode')!='write': raise ValueError('Capacity writer reservation required')
            digest=own.get('request_sha256')
            if not isinstance(digest,str) or not re.fullmatch('[0-9a-f]{64}',digest): raise ValueError('Reservation digest')
            fd=os.open(marker.with_name('execution-slot-'+match[1]+'.lock'),os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK)
            try:
                if not stat.S_ISREG(os.fstat(fd).st_mode): raise ValueError('Regular slot lock required')
                try: fcntl.flock(fd,fcntl.LOCK_EX|fcntl.LOCK_NB)
                except BlockingIOError: pass
                else: raise ValueError('Reservation is not held')
            finally: os.close(fd)
            receipt=read_json(root/'jobs'/outer_job_id/'receipt.json')
            for key in ('job_id','mode','timeout_seconds','request_sha256','resources'):
                if receipt.get(key)!=own.get(key): raise ValueError('Reservation receipt mismatch')
            if receipt.get('version')!=3 or receipt.get('status') not in ('starting','running'): raise ValueError('Outer supervisor inactive')
            resources=own.get('resources')
            if not isinstance(resources,dict): raise ValueError('Resource declaration required')
            for key in ('workers','overhead_processes','cpu_millis','memory_bytes','output_bytes'):
                if type(resources.get(key)) is not int or resources[key]<0: raise ValueError('Resource declaration')
            for key in ('read_roots','write_roots'):
                if not isinstance(resources.get(key),list) or any(not isinstance(x,str) or not Path(x).is_absolute() for x in resources[key]): raise ValueError('Resource roots')
            lanes=plan['lanes']
            workers=sum(int(x['argv'][x['argv'].index('--workers')+1]) if '--workers' in x['argv'] else 1 for x in lanes)
            # Shell + this driver, plus every lane parent/tracker beyond computation workers.
            overhead=2+sum(x['memory_processes'] for x in lanes)-workers
            if resources['workers']<workers or resources['overhead_processes']<overhead: raise ValueError('Outer process budget understated')
            if resources['cpu_millis']<1000*sum(x['cpu_count'] for x in lanes): raise ValueError('Outer CPU budget understated')
            if resources['memory_bytes']<sum(declared_memory(x) for x in lanes)+512*1024**2: raise ValueError('Outer memory budget lacks control allowance')
            if resources['output_bytes']<sum(x['additional_output_budget_bytes'] for x in lanes): raise ValueError('Outer output budget understated')
            for path in [*(x['output_root'] for x in lanes),str(root/'parallel'/plan['run_id'])]:
                if not covers(resources['write_roots'],path): raise ValueError('Outer write scope incomplete')
            for lane in lanes:
                for pin in lane['source_pins']:
                    if not covers(resources['read_roots']+resources['write_roots'],pin['path']): raise ValueError('Outer source read scope incomplete')
            # Fail closed for legacy/malformed peers; v3 admission protects future arrivals.
            for _,other in active:
                if other is own: continue
                if other.get('capacity_version')!=1 or not isinstance(other.get('resources'),dict): raise ValueError('Incompatible outer reservation')
                peer=other['resources']
                if any(paths_overlap(a,b) for a in resources['write_roots'] for b in peer['write_roots']+peer['read_roots']) or any(paths_overlap(a,b) for a in resources['read_roots'] for b in peer['write_roots']):
                    raise ValueError('Overlapping outer reservation')
        timeout=own.get('timeout_seconds')
        if type(timeout) is not int or plan['timeout_seconds']>timeout-20: raise ValueError('Outer deadline headroom required')
        if not isinstance(own.get('job_id'),str) or not IDENT.fullmatch(own['job_id']): raise ValueError('Outer job identity')
        return own
    finally:
        if admission is not None: os.close(admission)


def run(plan, root=PLATFORM, outer_job_id=None):
    global STOP
    STOP=False; validate(plan,root)
    started=time.monotonic(); deadline=started+plan['timeout_seconds']
    usage_start=resource.getrusage(resource.RUSAGE_CHILDREN);disk_start=free_bytes(root)
    telemetry={'samples':0,'peak_sampled_max_process_virtual_bytes':0,'peak_sampled_max_process_rss_bytes':0,'peak_sampled_process_count':0,'peak_sampled_rss_sum_bytes':0,'sample_read_errors':0,'sample_truncated':False,'rss_note':'Sampled descendant RSS sum; shared pages may be double counted; peaks between samples may be missed','cpu_note':'Reaped-child CPU accounting, including descendants accounted by waited parents; not all detached or unreaped work guaranteed','disk_note':'Filesystem free-space delta includes unrelated activity, not exact lane output bytes'}
    outer = outer_reservation(plan, root, outer_job_id)
    outer_id = outer['job_id']
    capacity_admitted = outer.get('capacity_version') == 1
    control=root/'jobs'/outer_id
    plan_bytes=json.dumps(plan,sort_keys=True,separators=(',',':')).encode()
    runroot=root/'parallel'/plan['run_id']
    beneath(str(runroot),root)
    runroot.parent.mkdir(mode=0o700,exist_ok=True)
    runroot.mkdir(mode=0o700) # Existing run requires reconciliation, never replays.
    receipt={'version':1,'run_id':plan['run_id'],'outer_job_id':outer_id,'plan_sha256':hashlib.sha256(plan_bytes).hexdigest(),
             'status':'preflight','lanes':[],'telemetry':telemetry,'output_qualification_established':False,'outer_cleanup_verification_required':True,'capacity_admitted':capacity_admitted,'outer_request_sha256':outer.get('request_sha256')}
    path=runroot/'receipt.json'; atomic(path,receipt)
    locks=[]; items=[]; logs=[]; sel=selectors.DefaultSelector()
    def stop(sig,frame):
        global STOP
        STOP=True
    old={s:signal.signal(s,stop) for s in (signal.SIGTERM,signal.SIGINT,signal.SIGHUP)}
    outcome='preflight_error'
    try:
        groups=allocation(plan,os.sched_getaffinity(0),available_memory(),capacity_admitted)
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
                    'per_process_virtual_memory_limit':lane['memory_bytes'],'declared_python_processes':lane['memory_processes'],'declared_lane_memory_budget':declared_memory(lane),'worker_virtual_memory_limit':lane.get('worker_memory_bytes'),'tracker_virtual_memory_limit':lane.get('tracker_memory_bytes'),'tracker_memory_enforcement':'reviewed producer verifies live child identity and applies prlimit before pool','worker_memory_enforcement':'reviewed producer initializer; inherited parent limit until initializer','log_bytes':{},'output_bytes':{}}
            proc=subprocess.Popen(lane['argv'],cwd='/offmenu',stdin=subprocess.DEVNULL,stdout=subprocess.PIPE,stderr=subprocess.PIPE,
                env={'PATH':'/usr/bin:/bin','LANG':'C','HOME':'/tmp/home','OMP_NUM_THREADS':'1','OPENBLAS_NUM_THREADS':'1','MKL_NUM_THREADS':'1'},
                start_new_session=True,close_fds=True,preexec_fn=lambda c=cpus,m=lane['memory_bytes']:child_setup(c,m))
            item={'proc':proc,'record':record,'started':time.monotonic()};items.append(item);receipt['lanes'].append(record)
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
                if code is not None:
                    item['record'].setdefault('wall_seconds',time.monotonic()-item['started'])
                    item['record'].update(status='exit_zero' if code==0 else 'exit_nonzero',exit_code=code)
            if time.monotonic()-last>=2:
                sample=sample_descendants(items);telemetry['samples']+=1
                telemetry['peak_sampled_max_process_virtual_bytes']=max(telemetry['peak_sampled_max_process_virtual_bytes'],sample['max_process_virtual_bytes'])
                telemetry['peak_sampled_max_process_rss_bytes']=max(telemetry['peak_sampled_max_process_rss_bytes'],sample['max_process_rss_bytes'])
                telemetry['peak_sampled_process_count']=max(telemetry['peak_sampled_process_count'],sample['process_count'])
                telemetry['peak_sampled_rss_sum_bytes']=max(telemetry['peak_sampled_rss_sum_bytes'],sample['rss_sum_bytes'])
                telemetry['sample_read_errors']+=sample['read_errors'];telemetry['sample_truncated']|=sample['truncated']
                atomic(path,receipt);last=time.monotonic()
        if outcome=='running':outcome='commands_exited'
    except Exception as exc:
        receipt['error_class']=type(exc).__name__
        outcome='supervisor_error' if items else 'preflight_error'
    finally:
        terminate(items)
        for item in items:
            code=item['proc'].poll();item['record']['exit_code']=code
            item['record'].setdefault('wall_seconds',time.monotonic()-item['started'])
            if item['record']['status']=='running':item['record']['status']='interrupted' if outcome!='commands_exited' else ('exit_zero' if code==0 else 'exit_nonzero')
            for stream in (item['proc'].stdout,item['proc'].stderr):stream.close()
        for f in logs:f.flush();os.fsync(f.fileno());f.close()
        sel.close()
        for fd in reversed(locks):os.close(fd)
        for sig,handler in old.items():signal.signal(sig,handler)
        usage_end=resource.getrusage(resource.RUSAGE_CHILDREN)
        cpu=max(0,(usage_end.ru_utime+usage_end.ru_stime)-(usage_start.ru_utime+usage_start.ru_stime));wall=time.monotonic()-started
        telemetry.update(wall_seconds=wall,reaped_child_cpu_seconds=cpu,average_accounted_cpu_cores=cpu/wall if wall else None,filesystem_free_bytes_delta=disk_start-free_bytes(root))
        receipt['status']=outcome;receipt['finished_at']=time.time();atomic(path,receipt)
    return receipt


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('plan');p.add_argument('--outer-job-id');args=p.parse_args()
    try:
        result=run(read_json(beneath(args.plan,PLATFORM)),outer_job_id=args.outer_job_id)
        print(json.dumps(result,sort_keys=True))
        return 0 if result['status']=='commands_exited' and all(x.get('exit_code')==0 for x in result['lanes']) else 1
    except Exception as exc:
        print(json.dumps({'status':'request_error','error_class':type(exc).__name__}));return 2

if __name__=='__main__':sys.exit(main())
