"""Canonical driver flags, owned128MiB tracker, and exact reviewed pause mapping."""
import hashlib,json,runpy,sys,os,resource
import multiprocessing.resource_tracker as resource_tracker
from pathlib import Path
QUALIFIER=Path('/offmenu/data/.offmenu-platform/corpus-recovery-20261028-v1/qualification-code-v3/scripts/qualify-common-expansion-resumable.py')
PIN='9fea04504b33581140a6c05c3a23a17681047208ad11313ae1e647f9993cd816'
MIB=1024**2
def bound_tracker(memory_bytes):
    """Bound this interpreter's own Linux spawn tracker, never an arbitrary PID.

    The parent owns/reaps this child; no wait/reap occurs between identity check
    and prlimit, so an exited tracker remains a zombie rather than a reused PID.
    Private Python tracker PID API is deliberately checked and fails closed.
    """
    if type(memory_bytes) is not int or memory_bytes != 128*1024**2:
        raise ValueError('tracker memory must be exactly128MiB')
    resource_tracker.ensure_running()
    pid = getattr(resource_tracker._resource_tracker, '_pid', None)
    if type(pid) is not int or pid <= 0 or pid == os.getpid():
        raise ValueError('resource tracker ownership unavailable')
    def identity():
        with open(f'/proc/{pid}/status', 'r', encoding='ascii') as stream:
            raw = stream.read(65537)
        if len(raw)>65536:
            raise ValueError('tracker status exceeds bound')
        fields = dict(line.split(':',1) for line in raw.splitlines() if ':' in line)
        if int(fields.get('PPid','-1')) != os.getpid() or fields.get('State','').lstrip().startswith('Z'):
            raise ValueError('tracker is not a live direct child')
        value = fields.get('VmSize','').split()
        if len(value)!=2 or value[1]!='kB' or int(value[0])*1024 >= memory_bytes:
            raise ValueError('tracker virtual memory exceeds approved cap')
        return int(value[0])*1024
    vm_size = identity()
    soft,hard = resource.prlimit(pid,resource.RLIMIT_AS)
    target = min([memory_bytes]+[v for v in (soft,hard) if v != resource.RLIM_INFINITY])
    resource.prlimit(pid,resource.RLIMIT_AS,(target,target))
    identity()
    if resource.prlimit(pid,resource.RLIMIT_AS)!=(target,target):
        raise ValueError('tracker memory cap not enforced')
    return {'pid':pid,'memory_bytes':target,'vm_bytes_before':vm_size}

def translate(args):
    required=('--workers','--worker-memory-bytes','--tracker-memory-bytes')
    forbidden=('--packet-workers','--worker-memory-mib')
    values={};remaining=[];index=0
    while index<len(args):
        arg=args[index]
        if arg in required:
            if arg in values or index+1>=len(args) or not args[index+1].isdigit():
                raise ValueError('unique canonical resource arguments with integer values required')
            values[arg]=int(args[index+1]);index+=2;continue
        if arg.startswith('--'):
            stem=arg.split('=')[0]
            if any(name==stem or name.startswith(stem) for name in required+forbidden):
                raise ValueError('resource aliases, equals syntax and translated flags forbidden')
        remaining.append(arg);index+=1
    if set(values)!=set(required):raise ValueError('explicit worker and tracker budgets required')
    n=values['--workers'];memory=values['--worker-memory-bytes'];tracker=values['--tracker-memory-bytes']
    if not 1<=n<=256 or memory<128*MIB or memory%(MIB)!=0 or tracker!=128*MIB:
        raise ValueError('invalid reviewed worker/tracker resource bounds')
    return remaining+['--packet-workers',str(n),'--worker-memory-mib',str(memory//MIB)],tracker

def execute(path,pin,args,tracker_guard=bound_tracker):
    if path.is_symlink() or hashlib.sha256(path.read_bytes()).hexdigest()!=pin:
        raise ValueError('reviewed qualifier source pin mismatch')
    translated,tracker_memory=translate(args)
    receipt=tracker_guard(tracker_memory)
    print(json.dumps({'adapterStatus':'TRACKER_BOUNDED','tracker':receipt}),flush=True)
    before=sys.argv;sys.argv=[str(path),*translated]
    try:
        try:runpy.run_path(str(path),run_name='__main__')
        except SystemExit as error:
            if type(error.code) is int and error.code==75:
                print(json.dumps({'adapterStatus':'EXPECTED_PAUSE','originalExitCode':75,'qualificationComplete':False}),flush=True)
                return 0
            raise
        return 0
    finally:sys.argv=before
if __name__=='__main__':sys.exit(execute(QUALIFIER,PIN,sys.argv[1:]))
