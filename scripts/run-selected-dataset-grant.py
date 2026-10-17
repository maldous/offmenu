#!/usr/bin/env python3
"""Owner-operated pinned grant and independent inventory; one sanitized PR30 report."""
import argparse
import ast
import hashlib
import errno
import json
import math
import os
from pathlib import Path
import pwd
import re
import selectors
import stat
import subprocess
import sys
import tempfile
import time

SCHEMA='offmenu-owner-dataset-batch/1'
PINS={
 'scripts/grant-selected-dataset-view-v1.py':'3f65422cf97f7bf40b7d48d8b9b6a40a65358f6593bf148a35f0f7602a7d4db6',
 'scripts/inspect-selected-datasets.py':'0b329be72f49dc83d7fda7aba6155344ed56a2818b8ccdc5b1da8dfce7326c60',
 'scripts/offmenu_projector_inventory.py':'937a6069068f46af6266f27fc4e636a268eda3ecc0a1c6879cd8f9f4b6856124',
}
HELPER,INSPECTOR,PROJECTOR=tuple(PINS)
SELF='scripts/run-selected-dataset-grant.py'
MAX_CAPTURE=65536
MAX_PAYLOAD=256*1024*1024+5*65536
HEX40=re.compile(r'[0-9a-f]{40}')
ASSETS={'NO_EN_FOODS','NO_NB_FOODS','NO_EN_NUTRIENTS','NO_EN_SOURCES','FR_WORKBOOK','FR_IDENTITIES','NATIONAL_ACQUISITION','NO_PRIOR_MANIFEST','FR_PRIOR_MANIFEST','FI_ACQUISITION','FI_PRIOR_MANIFEST'}
# Executed by root in isolated Python: the bytes that pass this hash check are
# exactly those executed. The helper independently pins its only code dependency.
ROOT_LOADER=r'''
import hashlib,os,signal,stat,sys
path,expected=sys.argv[1:3]
arguments=sys.argv[3:]
fd=os.open(path,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK)
try:
 s=os.fstat(fd)
 if not stat.S_ISREG(s.st_mode) or s.st_nlink!=1 or s.st_size>65536:raise ValueError('invalid-helper')
 body=os.read(fd,65537)
 if len(body)!=s.st_size or hashlib.sha256(body).hexdigest()!=expected:raise ValueError('invalid-helper')
finally:os.close(fd)
def deadline(*unused):raise KeyboardInterrupt()
signal.signal(signal.SIGALRM,deadline);signal.alarm(900)
sys.argv=[path,*arguments]
exec(compile(body,path,'exec'),{'__name__':'__main__','__file__':path})
'''


PROJECTOR_LOADER='import resource\nresource.setrlimit(resource.RLIMIT_AS,(256*1024*1024,256*1024*1024))\nresource.setrlimit(resource.RLIMIT_CPU,(60,60))\n'+ROOT_LOADER


GH_CANDIDATES=('/usr/bin/gh','/usr/local/bin/gh')
ERROR_CODES={
    'invalid-arguments','invalid-commit','normal-user-isolated-python-required',
    'artifact-invalid','artifact-pin-mismatch','checkout-mismatch','checkout-bytes-mismatch',
    'invalid-json','invalid-grant-report','projector-unverified','owner-auth-unavailable',
    'owner-auth-mismatch','interactive-sudo-required','sudo-auth-unavailable',
    'git-unavailable','python-unavailable','sudo-unavailable','gh-unavailable','gh-unsafe',
    'tool-missing','tool-unsafe','tool-not-executable','tool-io-error',
    'command-launch-failed','command-timeout','command-interrupted','capture-io-error',
    'output-limit-exceeded','command-exit-failed','publication-unverified',
    'grant-blocked','batch-report-limit','local-report-write-failed','local-records-unavailable',
    'io-error','interrupted','batch-unverified',
}


class Invalid(Exception):
    def __init__(self,code,number=None):
        super().__init__(code)
        self.errno=number


def safe_errno(value):
    return value if type(value) is int and 0<=value<=4096 else None


def diagnostic(phase,exc=None,code=None,recovery='correct-blocker-and-rerun-batch'):
    if code is None:
        if isinstance(exc,Invalid) and exc.args and type(exc.args[0]) is str and exc.args[0] in ERROR_CODES:code=exc.args[0]
        elif isinstance(exc,OSError):code='io-error'
        elif isinstance(exc,KeyboardInterrupt):code='interrupted'
        else:code='batch-unverified'
    if code not in ERROR_CODES:code='batch-unverified'
    return {'phase':phase,'errorCode':code,'errno':safe_errno(getattr(exc,'errno',None)),
            'recovery':recovery}


def verify_gh(path):
    """Only two root-controlled, nonsymlink executable locations may receive auth."""
    if path not in GH_CANDIDATES:raise Invalid('gh-unsafe')
    candidate=Path(path)
    for part in [*reversed(candidate.parents),candidate]:
        info=part.lstat()
        if info.st_uid!=0 or info.st_mode&0o022 or stat.S_ISLNK(info.st_mode):raise Invalid('tool-unsafe')
        if part!=candidate:
            if not stat.S_ISDIR(info.st_mode):raise Invalid('tool-unsafe')
        elif not stat.S_ISREG(info.st_mode) or info.st_mode&0o6000 or info.st_nlink!=1:
            raise Invalid('tool-unsafe')
    if not info.st_mode&0o111 or not os.access(path,os.X_OK):raise Invalid('tool-not-executable')
    return path


def tool_preflight():
    """Fixed order and paths; never search PATH or execute a discovery command."""
    result={}
    for name,path in (('git','/usr/bin/git'),('python','/usr/bin/python3'),('sudo','/usr/bin/sudo')):
        try:
            info=os.stat(path)
            if not stat.S_ISREG(info.st_mode) or not os.access(path,os.X_OK):raise Invalid('tool-not-executable')
            result[name]={'status':'ready','path':path}
        except (OSError,Invalid) as exc:
            code='tool-missing' if isinstance(exc,FileNotFoundError) else 'tool-io-error'
            if isinstance(exc,Invalid):code=exc.args[0]
            result[name]={'status':'blocked','path':path,'errorCode':code,'errno':safe_errno(getattr(exc,'errno',None))}
    candidates=[];selected=None
    for path in GH_CANDIDATES:
        try:
            verify_gh(path)
            candidates.append({'path':path,'status':'ready'})
            if selected is None:selected=path
        except (OSError,Invalid) as exc:
            code='tool-missing' if isinstance(exc,FileNotFoundError) else 'tool-io-error'
            if isinstance(exc,Invalid):code=exc.args[0]
            candidates.append({'path':path,'status':'blocked','errorCode':code,'errno':safe_errno(getattr(exc,'errno',None))})
    result['gh']={'status':'ready' if selected else 'blocked','path':selected,'candidates':candidates}
    return result


def require_tool(preflight,name):
    item=preflight[name]
    if item['status']!='ready':
        number=item.get('errno')
        if name=='gh':
            number=next((x.get('errno') for x in item['candidates'] if x.get('errno') is not None),None)
        raise Invalid(name+'-unavailable',number)
    return item['path']


def strict_json(body):
    def pairs(items):
        result={}
        for key,value in items:
            if key in result:raise Invalid('invalid-json')
            result[key]=value
        return result
    def finite(value):
        number=float(value)
        if not math.isfinite(number):raise Invalid('invalid-json')
        return number
    try:return json.loads(body,object_pairs_hook=pairs,parse_float=finite,parse_constant=lambda _:(_ for _ in ()).throw(Invalid('invalid-json')))
    except (ValueError,UnicodeError,RecursionError):raise Invalid('invalid-json') from None


def read_file(path,cap=65536):
    fd=os.open(path,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK)
    try:
        info=os.fstat(fd)
        if not stat.S_ISREG(info.st_mode) or info.st_nlink!=1 or info.st_size>cap:raise Invalid('artifact-invalid')
        body=os.read(fd,cap+1)
        if len(body)!=info.st_size:raise Invalid('artifact-invalid')
        return body
    finally:os.close(fd)


def environment(for_github=False):
    # Reuse bootstrap auth only for the fixed gh executable, never other children.
    result= {'PATH':'/usr/bin:/bin','HOME':pwd.getpwuid(os.getuid()).pw_dir,
            'LANG':'C.UTF-8','GH_HOST':'github.com','GH_PROMPT_DISABLED':'1',
            'GH_PAGER':'cat','GIT_CONFIG_NOSYSTEM':'1','GIT_CONFIG_GLOBAL':'/dev/null'}
    if for_github:
        for key in ('GH_CONFIG_DIR','XDG_CONFIG_HOME','GH_TOKEN','GITHUB_TOKEN'):
            if os.environ.get(key):result[key]=os.environ[key]
    return result


def capture(args,directory,label,cap=MAX_CAPTURE,timeout=90,privileged=False):
    """Bounded private capture with launch state; never claim to kill a root child."""
    stdout=directory/(label+'.stdout');stderr=directory/(label+'.stderr')
    is_github=args[0] in GH_CANDIDATES
    fds=[None,None];proc=None;selector=None;chunks=[bytearray(),bytearray()]
    process_options={'start_new_session':not privileged}
    if privileged:
        if sys.version_info >= (3,11):process_options['process_group']=0
        else:process_options['preexec_fn']=os.setpgrp
    overflow=False;unknown=False;launch_attempted=False;failure=None;number=None;deadline=time.monotonic()+timeout
    try:
        # Recheck the complete trusted ancestry immediately before passing credentials.
        if is_github:verify_gh(args[0])
        else:
            for index,path in enumerate((stdout,stderr)):
                fds[index]=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
        selector=selectors.DefaultSelector()
        launch_attempted=True
        proc=subprocess.Popen(args,stdin=subprocess.DEVNULL,stdout=subprocess.PIPE,stderr=subprocess.PIPE,
                              env=environment(for_github=is_github),**process_options)
        selector.register(proc.stdout,selectors.EVENT_READ,0);selector.register(proc.stderr,selectors.EVENT_READ,1)
        while selector.get_map():
            left=deadline-time.monotonic()
            if left<=0:unknown=True;failure='command-timeout';break
            for key,_ in selector.select(min(left,1)):
                part=os.read(key.fileobj.fileno(),8192)
                if not part:selector.unregister(key.fileobj);continue
                index=key.data;allowed=max(0,cap-len(chunks[index]));kept=part[:allowed]
                chunks[index].extend(kept)
                if kept and fds[index] is not None:
                    if os.write(fds[index],kept)!=len(kept):raise OSError(errno.EIO,'short-write')
                if len(kept)!=len(part):overflow=True
        if not unknown:
            try:proc.wait(timeout=max(0.01,deadline-time.monotonic()))
            except subprocess.TimeoutExpired:unknown=True;failure='command-timeout'
    except (KeyboardInterrupt,OSError,Invalid) as exc:
        # Popen can be interrupted after fork/exec but before returning a handle.
        # Only its explicit missing/denied executable errors prove no launch.
        unknown=proc is not None or (launch_attempted and not isinstance(exc,(FileNotFoundError,PermissionError)))
        number=safe_errno(getattr(exc,'errno',None))
        if isinstance(exc,Invalid):failure=diagnostic('capture',exc)['errorCode']
        elif isinstance(exc,KeyboardInterrupt):failure='command-interrupted'
        else:failure='capture-io-error' if unknown else 'command-launch-failed'
    finally:
        if selector is not None:
            try:selector.close()
            except OSError as exc:
                unknown=unknown or proc is not None;failure=failure or 'capture-io-error';number=number or safe_errno(exc.errno)
        for fd in fds:
            if fd is None:continue
            try:os.close(fd)
            except OSError as exc:unknown=unknown or proc is not None;failure=failure or 'capture-io-error';number=number or safe_errno(exc.errno)
        if proc is not None:
            try:
                if unknown and not privileged and proc.poll() is None:
                    proc.kill();proc.wait()
            except OSError as exc:
                unknown=True;failure=failure or 'capture-io-error';number=number or safe_errno(exc.errno)
            for pipe in (proc.stdout,proc.stderr):
                if pipe is not None:
                    try:pipe.close()
                    except OSError as exc:unknown=True;failure=failure or 'capture-io-error';number=number or safe_errno(exc.errno)
    if overflow and failure is None:failure='output-limit-exceeded'
    return {'exitCode':None if unknown or proc is None else proc.returncode,'stdout':bytes(chunks[0]),
            'overflow':overflow,'outcome':'unknown' if unknown else 'not-started' if proc is None else 'finished',
            'launched':True if proc is not None else None if unknown else False,'errorCode':failure,'errno':number}


def command_failure(result,default):
    return Invalid(result.get('errorCode') or default,result.get('errno'))


def git(root,*args):
    return ['/usr/bin/git','--no-optional-locks','-c','core.fsmonitor=false','-c','core.hooksPath=/dev/null','-C',str(root),*args]


def verify_checkout(root,commit,directory):
    result=capture(git(root,'rev-parse','--verify','HEAD'),directory,'git-head')
    if result['exitCode']!=0 or result['overflow']:raise command_failure(result,'checkout-mismatch')
    if result['stdout'].decode('ascii','strict').strip()!=commit:raise Invalid('checkout-mismatch')
    bodies={}
    for index,relative in enumerate([SELF,*PINS]):
        body=read_file(root/relative)
        if relative in PINS and hashlib.sha256(body).hexdigest()!=PINS[relative]:raise Invalid('artifact-pin-mismatch')
        result=capture(git(root,'show',commit+':'+relative),directory,'git-file-'+str(index))
        if result['exitCode']!=0 or result['overflow']:raise command_failure(result,'checkout-bytes-mismatch')
        if result['stdout']!=body:raise Invalid('checkout-bytes-mismatch')
        bodies[relative]=body
    return bodies


def namespace(body,path):
    result={'__name__':'offmenu_verified_dependency','__file__':str(path)}
    exec(compile(body,str(path),'exec'),result)
    return result


def grant_error_codes(helper):
    values={'grant-failed','report-limit-exceeded'}
    for node in ast.walk(ast.parse(helper)):
        if isinstance(node,ast.Call) and isinstance(node.func,ast.Name) and node.func.id=='block' and len(node.args)==1 and isinstance(node.args[0],ast.Constant) and isinstance(node.args[0].value,str):values.add(node.args[0].value)
    return values


SERVICE_CHECK_NAMES={'User','Group','NoNewPrivileges','ProtectSystem','ProtectHome','PrivateTmp','PrivateDevices','CapabilityBoundingSet','AmbientCapabilities','BindPaths','FragmentPath','ReadWritePaths','ControlGroup','BindReadOnlyPaths','DropInPaths'}
SERVICE_STATE_VALUES={
 'ActiveState':{'active','activating','inactive','deactivating','failed','reloading','maintenance','refreshing','unknown'},
 'SubState':{'running','start','start-pre','start-post','auto-restart','dead','failed','exited','stop','stop-sigterm','stop-sigkill','stop-post','final-sigterm','final-sigkill','reload','reload-signal','reload-notify','cleaning','condition','unknown'},
 'Result':{'success','resources','protocol','timeout','exit-code','signal','core-dump','watchdog','start-limit-hit','oom-kill','exec-condition','skip-condition','unknown'},
}
SERVICE_PATH_NAMES={'BindPaths','FragmentPath','ReadWritePaths','ControlGroup','BindReadOnlyPaths','DropInPaths'}
SERVICE_NUMBER_NAMES={'MainPID','ExecMainPID','ExecMainCode','ExecMainStatus','StatusErrno'}


def sanitize_service_diagnostics(value,errors):
    snapshots={'before','after','failure','rollback'}
    if type(value) is not dict or set(value)-snapshots-{'afterAttempts','rollbackAttempts','afterLastPending','rollbackLastPending','afterErrno','rollbackErrno','failureDetail','rollbackDetail','failureSample','rollbackSample','failureSampleDetail','rollbackSampleDetail'}:raise Invalid('invalid-grant-report')
    for phase,record in value.items():
        if phase in snapshots:
            if type(record) is not dict or set(record)!={'properties','unexpectedValueSha256','states','numbers'}:raise Invalid('invalid-grant-report')
            checks=record['properties']
            if type(checks) is not dict or set(checks)!=SERVICE_CHECK_NAMES:raise Invalid('invalid-grant-report')
            for entry in checks.values():
                if type(entry) is not dict or set(entry)!={'present','match'} or any(type(x) is not bool for x in entry.values()) or (entry['match'] and not entry['present']):raise Invalid('invalid-grant-report')
            hashes=record['unexpectedValueSha256']
            if type(hashes) is not dict or set(hashes)!={k for k,v in checks.items() if k in SERVICE_PATH_NAMES and v['present'] and not v['match']} or any(type(x) is not str or re.fullmatch(r'[0-9a-f]{64}',x) is None for x in hashes.values()):raise Invalid('invalid-grant-report')
            states=record['states'];numbers=record['numbers']
            if type(states) is not dict or set(states)!=set(SERVICE_STATE_VALUES) or any(type(v) is not str or v not in SERVICE_STATE_VALUES[k] for k,v in states.items()):raise Invalid('invalid-grant-report')
            if type(numbers) is not dict or set(numbers)!=SERVICE_NUMBER_NAMES or any(x is not None and (type(x) is not int or not 0<=x<=2147483647) for x in numbers.values()):raise Invalid('invalid-grant-report')
        elif phase.endswith('Sample'):
            if type(record) is not str or record not in {'fresh','last-observed','unavailable'}:raise Invalid('invalid-grant-report')
            name=phase[:-6]
            if (record=='unavailable')!=(name not in value):raise Invalid('invalid-grant-report')
        elif phase.endswith('LastPending'):
            if type(record) is not str or record not in {'runtime-activation','process-not-present','service-process-starting','read-only-mount-verification-failed','process-changed'}:raise Invalid('invalid-grant-report')
        elif phase.endswith('Errno'):
            if record is not None and (type(record) is not int or not 0<=record<=4096):raise Invalid('invalid-grant-report')
        elif phase.endswith('Attempts'):
            if type(record) is not int or not 1<=record<=128:raise Invalid('invalid-grant-report')
        else:
            if type(record) is not dict or set(record)!={'errorCode','errno','command'} or type(record['errorCode']) is not str or record['errorCode'] not in errors:raise Invalid('invalid-grant-report')
            if record['errno'] is not None and (type(record['errno']) is not int or not 0<=record['errno']<=4096):raise Invalid('invalid-grant-report')
            command=record['command']
            if command is not None:
                if type(command) is not dict or set(command)!={'operation','exitCode','errno','timedOut'} or command['operation'] not in {'show','stop','start','daemon-reload','verify','other'} or type(command['timedOut']) is not bool:raise Invalid('invalid-grant-report')
                if command['exitCode'] is not None and (type(command['exitCode']) is not int or not -255<=command['exitCode']<=255):raise Invalid('invalid-grant-report')
                if command['errno'] is not None and (type(command['errno']) is not int or not 0<=command['errno']<=4096):raise Invalid('invalid-grant-report')
    return json.loads(json.dumps(value))


def sanitize_grant(value,inspector,errors):
    base={'schemaVersion','reportKind','grantVersion','status','applied','sourceBytesRead','sourceBytesWritten','snapshotBytesWritten','snapshotVerified','sourcePermissionsChanged','credentialsRead','selectedAssets','assets','sources','serviceReady','serviceRestarted','effectiveMountAssets','readOnlyMountsVerified','rollbackAttempted','rollbackRestored'}
    if not isinstance(value,dict) or not base<=set(value) or set(value)-base-{'errorCode','snapshotEvidence','serviceDiagnostics'}:raise Invalid('invalid-grant-report')
    if value['schemaVersion']!='offmenu-selected-data-grant/1' or value['reportKind']!='dataset-view-grant' or type(value['grantVersion']) is not int or value['grantVersion']!=1:raise Invalid('invalid-grant-report')
    if value['status'] not in {'validated','applied','already-applied','blocked'}:raise Invalid('invalid-grant-report')
    out={k:value[k] for k in ('schemaVersion','reportKind','grantVersion','status')}
    for k in ('applied','snapshotVerified','sourcePermissionsChanged','credentialsRead','serviceReady','serviceRestarted','readOnlyMountsVerified','rollbackAttempted'):
        if type(value[k]) is not bool or (k in {'sourcePermissionsChanged','credentialsRead'} and value[k]):raise Invalid('invalid-grant-report')
        out[k]=value[k]
    if value['rollbackRestored'] is not None and type(value['rollbackRestored']) is not bool:raise Invalid('invalid-grant-report')
    out['rollbackRestored']=value['rollbackRestored']
    for k in ('sourceBytesRead','sourceBytesWritten','snapshotBytesWritten'):
        if type(value[k]) is not int or not 0<=value[k]<=MAX_PAYLOAD or (k=='sourceBytesWritten' and value[k]!=0):raise Invalid('invalid-grant-report')
        out[k]=value[k]
    if out['snapshotBytesWritten']>out['sourceBytesRead']:raise Invalid('invalid-grant-report')
    for k in ('selectedAssets','effectiveMountAssets'):
        items=value[k]
        if not isinstance(items,list) or len(items)>len(ASSETS) or any(type(x) is not str or x not in ASSETS for x in items) or len(set(items))!=len(items):raise Invalid('invalid-grant-report')
        out[k]=sorted(items)
    states={'validated','missing','unsafe-path','unsafe-file','oversized','acl-requires-review','access-unverified','runner-read-denied','selected-source-changed','aggregate-limit','evidence-blocked'}
    if not isinstance(value['assets'],dict) or not set(value['assets'])<=ASSETS or any(type(v) is not str or v not in states for v in value['assets'].values()):raise Invalid('invalid-grant-report')
    out['assets']=dict(value['assets'])
    if not isinstance(value['sources'],dict) or set(value['sources'])!={'NO','FR','FI'} or any(type(v) is not str or v not in {'not-checked','blocked','validated','view-granted','metadata-view-granted'} for v in value['sources'].values()):raise Invalid('invalid-grant-report')
    out['sources']=dict(value['sources'])
    if 'errorCode' in value:
        if type(value['errorCode']) is not str or value['errorCode'] not in errors:raise Invalid('invalid-grant-report')
        out['errorCode']=value['errorCode']
    if 'snapshotEvidence' in value:out['snapshotEvidence']=inspector['sanitize_report'](value['snapshotEvidence'])
    if 'serviceDiagnostics' in value:out['serviceDiagnostics']=sanitize_service_diagnostics(value['serviceDiagnostics'],errors)
    if value['status'] in {'applied','already-applied'} and not all(value[k] for k in ('applied','serviceReady','snapshotVerified','readOnlyMountsVerified')):raise Invalid('invalid-grant-report')
    if set(out['effectiveMountAssets'])-set(out['selectedAssets']):raise Invalid('invalid-grant-report')
    if len(json.dumps(out).encode())>16384:raise Invalid('invalid-grant-report')
    return out


def verified_owner(directory,gh='/usr/bin/gh'):
    result=capture([gh,'api','--hostname','github.com','user','--jq','{login: .login, id: .id}'],directory,'github-owner',cap=4096)
    if result['exitCode']!=0 or result['overflow']:raise command_failure(result,'owner-auth-unavailable')
    value=strict_json(result['stdout'])
    if value!={'login':'maldous','id':6347545}:raise Invalid('owner-auth-mismatch')


def report_bytes(report):
    body=json.dumps(report,sort_keys=True,separators=(',',':')).encode()
    if len(body)>32768:raise Invalid('batch-report-limit')
    return body


def persist_report(report,directory):
    """Atomic private snapshot, independent of authentication and publication."""
    body=report_bytes(report)
    fd=None;temporary=None
    try:
        fd,name=tempfile.mkstemp(prefix='.report-',dir=directory);temporary=Path(name)
        with os.fdopen(fd,'wb') as stream:
            fd=None;stream.write(body+b'\n');stream.flush();os.fsync(stream.fileno())
        os.replace(temporary,directory/'sanitized-report.json');temporary=None
    finally:
        if fd is not None:os.close(fd)
        if temporary is not None:temporary.unlink(missing_ok=True)


def publish(report,directory,gh='/usr/bin/gh'):
    body=report_bytes(report)
    path=directory/'sanitized-report.md'
    fd=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
    with os.fdopen(fd,'wb') as stream:stream.write(b'OffMenu owner dataset batch\n\n```json\n'+body+b'\n```\n')
    # One attempt only. A timeout or failed response may have posted successfully.
    try:
        result=capture([gh,'pr','comment','30','--repo','https://github.com/maldous/offmenu','--body-file',str(path)],directory,'github-comment')
        if result.get('outcome')=='not-started':
            return {'status':'not-attempted','diagnostic':diagnostic('publication',command_failure(result,'publication-unverified'))}
        if result['exitCode']==0 and not result['overflow']:return {'status':'posted'}
        exc=command_failure(result,'publication-unverified')
    except (Exception,KeyboardInterrupt) as error:exc=error
    return {'status':'uncertain-no-retry','diagnostic':diagnostic('publication',exc,recovery='check-pr30-before-retrying-publication')}



def inspect_projector(root,bodies,directory):
    try:
        projector=namespace(bodies[PROJECTOR],root/PROJECTOR)
        observed=capture(['/usr/bin/python3','-I','-S','-B','-c',PROJECTOR_LOADER,str(root/PROJECTOR),PINS[PROJECTOR]],directory,'projector',cap=16384,timeout=90)
        if observed['exitCode'] not in (0,2) or observed['overflow']:raise command_failure(observed,'projector-unverified')
        evidence=projector['sanitize_report'](strict_json(observed['stdout']))
        if observed['exitCode']!=(0 if evidence['status']=='complete' else 2):raise Invalid('projector-unverified')
        return {'status':'reported','exitCode':observed['exitCode'],'report':evidence}
    except (Exception,KeyboardInterrupt) as exc:
        return {'status':'unverified','diagnostic':diagnostic('projector',exc,recovery='review-projector-evidence')}


def run(commit,argument_error=False):
    valid_commit=type(commit) is str and HEX40.fullmatch(commit) is not None
    report={'schemaVersion':SCHEMA,'reportKind':'owner-dataset-grant-batch','batchVersion':1,
            'expectedCommit':commit if valid_commit else None,'artifactSha256':dict(PINS),
            'grant':{'status':'not-started'},'projector':{'status':'not-started'},
            'publication':{'status':'not-attempted'},'localReportStatus':'pending'}
    authenticated=False;exitcode=2;directory=None;phase='local-records';gh=None
    try:
        directory=Path(tempfile.mkdtemp(prefix='offmenu-owner-batch-',dir='/tmp'));directory.chmod(0o700)
        phase='local-report';persist_report(report,directory)
        phase='runtime'
        report['runtime']={'normalUser':os.geteuid()!=0,'isolatedPython':bool(sys.flags.isolated),
                           'interactiveTerminal':bool(sys.stdin.isatty())}
        if argument_error:raise Invalid('invalid-arguments')
        if not valid_commit:raise Invalid('invalid-commit')
        if not report['runtime']['normalUser'] or not report['runtime']['isolatedPython']:raise Invalid('normal-user-isolated-python-required')
        root=Path(__file__).resolve().parents[1]
        phase='tool-preflight';report['tools']=tool_preflight()
        require_tool(report['tools'],'git')
        phase='checkout';bodies=verify_checkout(root,commit,directory)
        inspector=namespace(bodies[INSPECTOR],root/INSPECTOR)
        # This independent unprivileged result survives missing gh/auth and sudo.
        phase='projector'
        if report['tools']['python']['status']=='ready':report['projector']=inspect_projector(root,bodies,directory)
        else:report['projector']={'status':'not-started','diagnostic':diagnostic(phase,code='python-unavailable',recovery='restore-standard-python-and-rerun-batch')}
        if report['projector'].get('diagnostic',{}).get('errorCode') in {'interrupted','command-interrupted'}:
            raise Invalid('interrupted')
        phase='github-owner';gh=require_tool(report['tools'],'gh')
        verified_owner(directory,gh);authenticated=True
        phase='sudo-auth'
        require_tool(report['tools'],'python');require_tool(report['tools'],'sudo')
        if not report['runtime']['interactiveTerminal']:raise Invalid('interactive-sudo-required')
        # Save completed independent evidence before any privilege or changes.
        phase='local-report';persist_report(report,directory)
        phase='sudo-auth'
        auth=subprocess.run(['/usr/bin/sudo','-v'],env=environment(),check=False)
        if auth.returncode:raise Invalid('sudo-auth-unavailable')
        phase='grant'
        # Any unexpected post-launch failure must stay conservative.
        report['grant']={'status':'unknown-outcome','exitCode':124};exitcode=124
        result=capture(['/usr/bin/sudo','-n','/usr/bin/python3','-I','-B','-c',ROOT_LOADER,str(root/HELPER),PINS[HELPER],'--apply'],directory,'grant',cap=MAX_CAPTURE,timeout=1200,privileged=True)
        if result['outcome']=='not-started':
            report['grant']={'status':'not-started'};exitcode=2
            raise command_failure(result,'command-launch-failed')
        exitcode=result['exitCode'] if result['exitCode'] is not None else 124
        if exitcode<0:exitcode=128-exitcode
        report['grant']={'status':'unknown-outcome' if result['outcome']=='unknown' else 'unverified','exitCode':exitcode}
        if result['outcome']=='unknown':raise command_failure(result,'batch-unverified')
        if result['overflow'] or len(result['stdout'])>16384:raise Invalid('invalid-grant-report')
        try:
            evidence=sanitize_grant(strict_json(result['stdout']),inspector,grant_error_codes(bodies[HELPER]))
            expected=2 if evidence['status']=='blocked' else 0
            if result['exitCode']!=expected:raise Invalid('invalid-grant-report')
        except (Exception,KeyboardInterrupt):raise Invalid('invalid-grant-report') from None
        report['grant']={'status':'reported','exitCode':exitcode,'report':evidence}
        if evidence['status']=='blocked':
            report['diagnostic']=diagnostic('grant',code='grant-blocked',recovery='review-grant-blocker-before-retry')
        phase='complete'
    except (Exception,KeyboardInterrupt) as exc:
        recovery='keep-queue-quiet-review-before-retry' if report['grant']['status'] in {'unknown-outcome','unverified'} else 'correct-blocker-and-rerun-batch'
        code='local-records-unavailable' if phase=='local-records' else 'local-report-write-failed' if phase=='local-report' else None
        report['diagnostic']=diagnostic(phase,exc,code,recovery)
        report['batchBlocker']=report['diagnostic']['errorCode']
    # This local snapshot exists before any remote attempt; publication is optional.
    try:
        if directory is None:raise Invalid('local-records-unavailable')
        report['localReportStatus']='saved';persist_report(report,directory)
    except (Exception,KeyboardInterrupt) as exc:
        report['localReportStatus']='write-failed'
        report['localReportDiagnostic']=diagnostic('local-report',exc,'local-report-write-failed',recovery='retain-terminal-outcome-and-review-local-storage')
    if authenticated:
        try:report['publication']=publish(report,directory,gh)
        except (Exception,KeyboardInterrupt) as exc:
            # Exceptions outside capture occur while preparing the body, before launch.
            report['publication']={'status':'not-attempted','diagnostic':diagnostic('publication',exc,recovery='retain-local-report-and-review-publication')}
    # Include the final publication outcome in the private JSON, even on failure.
    if directory is not None:
        try:
            report['localReportStatus']='saved';report.pop('localReportDiagnostic',None)
            persist_report(report,directory)
        except (Exception,KeyboardInterrupt) as exc:
            report['localReportStatus']='write-failed'
            report['localReportDiagnostic']=diagnostic('local-report',exc,'local-report-write-failed',recovery='retain-terminal-outcome-and-review-local-storage')
    diag=report.get('diagnostic') or report.get('localReportDiagnostic') or report['publication'].get('diagnostic')
    if diag is None:
        recovery='review-grant-receipt-before-queue' if report['grant']['status']=='reported' else 'correct-blocker-and-rerun-batch'
        diag={'phase':'complete','errorCode':None,'errno':None,'recovery':recovery}
    outcome={'schemaVersion':SCHEMA,'reportKind':'owner-batch-outcome',**diag,
             'grantStatus':report['grant']['status'],'projectorStatus':report['projector']['status'],
             'helperExitCode':exitcode,'publication':report['publication']['status'],
             'localReportStatus':report['localReportStatus'],'privateLogsRetained':directory is not None,
             'batchBlocker':report.get('batchBlocker')}
    if 'tools' in report:outcome['tools']=report['tools']
    if 'runtime' in report:outcome['runtime']=report['runtime']
    outcome['helperReportStatus']=report['grant'].get('report',{}).get('status')
    outcome['helperErrorCode']=report['grant'].get('report',{}).get('errorCode')
    if 'diagnostic' in report['projector']:outcome['projectorDiagnostic']=report['projector']['diagnostic']
    if report['localReportStatus']=='write-failed':outcome['sanitizedReport']=report
    if 'diagnostic' in report['publication']:outcome['publicationDiagnostic']=report['publication']['diagnostic']
    if 'localReportDiagnostic' in report:outcome['localReportDiagnostic']=report['localReportDiagnostic']
    print(json.dumps(outcome,sort_keys=True))
    if directory is not None:print('Private batch records: '+str(directory),file=sys.stderr)
    if report['grant']['status'] in {'unknown-outcome','unverified'}:
        print('Grant evidence needs review. Keep the job queue quiet and request review before retrying.',file=sys.stderr)
    return exitcode


class Arguments(argparse.ArgumentParser):
    def error(self,message):raise Invalid('invalid-arguments')


def main():
    parser=Arguments(description=__doc__)
    parser.add_argument('--expected-commit',required=True)
    try:args=parser.parse_args()
    except Invalid:return run(None,argument_error=True)
    return run(args.expected_commit)


if __name__=='__main__':sys.exit(main())
