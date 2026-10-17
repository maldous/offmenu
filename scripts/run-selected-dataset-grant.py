#!/usr/bin/env python3
"""Owner-operated pinned grant and independent inventory; one sanitized PR30 report."""
import argparse
import ast
import hashlib
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
 'scripts/grant-selected-dataset-view-v1.py':'3996577fd88e211e845d7b17db3e0e7c3f4420fe530db9b03c2577c30f4b83bf',
 'scripts/inspect-selected-datasets.py':'74ec7d6ad41cdfbb6cdbd789aae43f7d569c1f6e2da9cfa8445ea29a914b43d1',
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


class Invalid(Exception):pass


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
    """Incrementally bounded private capture. Never claim to kill a root child."""
    stdout=directory/(label+'.stdout');stderr=directory/(label+'.stderr')
    # gh may echo auth-related data on error: never persist either raw stream.
    is_github=args[0]=='/usr/bin/gh'
    fds=[None,None] if is_github else [os.open(p,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600) for p in (stdout,stderr)]
    proc=None;selector=selectors.DefaultSelector();chunks=[bytearray(),bytearray()]
    # Reuse bootstrap's same-session/separate-process-group sudo pattern.
    process_options={'start_new_session':not privileged}
    if privileged:
        if sys.version_info >= (3,11):process_options['process_group']=0
        else:process_options['preexec_fn']=os.setpgrp
    overflow=False;unknown=False;deadline=time.monotonic()+timeout
    try:
        proc=subprocess.Popen(args,stdin=subprocess.DEVNULL,stdout=subprocess.PIPE,stderr=subprocess.PIPE,
                              env=environment(for_github=is_github),**process_options)
        selector.register(proc.stdout,selectors.EVENT_READ,0);selector.register(proc.stderr,selectors.EVENT_READ,1)
        while selector.get_map():
            left=deadline-time.monotonic()
            if left<=0:unknown=True;break
            for key,_ in selector.select(min(left,1)):
                part=os.read(key.fileobj.fileno(),8192)
                if not part:selector.unregister(key.fileobj);continue
                index=key.data;allowed=max(0,cap-len(chunks[index]));kept=part[:allowed]
                chunks[index].extend(kept)
                if kept and fds[index] is not None:os.write(fds[index],kept)
                if len(kept)!=len(part):overflow=True
        if not unknown:
            try:proc.wait(timeout=max(0.01,deadline-time.monotonic()))
            except subprocess.TimeoutExpired:unknown=True
    except (KeyboardInterrupt,OSError):
        if proc is None:raise
        unknown=True
    finally:
        selector.close()
        for fd in fds:
            if fd is None:continue
            try:os.close(fd)
            except OSError:unknown=True
        if proc is not None:
            if unknown and not privileged and proc.poll() is None:
                proc.kill();proc.wait()
            for pipe in (proc.stdout,proc.stderr):
                if pipe is not None:
                    try:pipe.close()
                    except OSError:unknown=True
    return {'exitCode':None if unknown else proc.returncode,'stdout':bytes(chunks[0]),
            'overflow':overflow,'outcome':'unknown' if unknown else 'finished'}


def git(root,*args):
    return ['/usr/bin/git','--no-optional-locks','-c','core.fsmonitor=false','-c','core.hooksPath=/dev/null','-C',str(root),*args]


def verify_checkout(root,commit,directory):
    result=capture(git(root,'rev-parse','--verify','HEAD'),directory,'git-head')
    if result['exitCode']!=0 or result['overflow'] or result['stdout'].decode('ascii','strict').strip()!=commit:raise Invalid('checkout-mismatch')
    bodies={}
    for index,relative in enumerate([SELF,*PINS]):
        body=read_file(root/relative)
        if relative in PINS and hashlib.sha256(body).hexdigest()!=PINS[relative]:raise Invalid('artifact-pin-mismatch')
        result=capture(git(root,'show',commit+':'+relative),directory,'git-file-'+str(index))
        if result['exitCode']!=0 or result['overflow'] or result['stdout']!=body:raise Invalid('checkout-bytes-mismatch')
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


def sanitize_grant(value,inspector,errors):
    base={'schemaVersion','reportKind','grantVersion','status','applied','sourceBytesRead','sourceBytesWritten','snapshotBytesWritten','snapshotVerified','sourcePermissionsChanged','credentialsRead','selectedAssets','assets','sources','serviceReady','serviceRestarted','effectiveMountAssets','readOnlyMountsVerified','rollbackAttempted','rollbackRestored'}
    if not isinstance(value,dict) or not base<=set(value) or set(value)-base-{'errorCode','snapshotEvidence'}:raise Invalid('invalid-grant-report')
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
    if value['status'] in {'applied','already-applied'} and not all(value[k] for k in ('applied','serviceReady','snapshotVerified','readOnlyMountsVerified')):raise Invalid('invalid-grant-report')
    if set(out['effectiveMountAssets'])-set(out['selectedAssets']):raise Invalid('invalid-grant-report')
    if len(json.dumps(out).encode())>16384:raise Invalid('invalid-grant-report')
    return out


def verified_owner(directory):
    result=capture(['/usr/bin/gh','api','--hostname','github.com','user','--jq','{login: .login, id: .id}'],directory,'github-owner',cap=4096)
    if result['exitCode']!=0 or result['overflow']:raise Invalid('owner-auth-unavailable')
    value=strict_json(result['stdout'])
    if value!={'login':'maldous','id':6347545}:raise Invalid('owner-auth-mismatch')


def publish(report,directory):
    body=json.dumps(report,sort_keys=True,separators=(',',':'))
    if len(body.encode())>32768:raise Invalid('batch-report-limit')
    path=directory/'sanitized-report.md'
    fd=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
    with os.fdopen(fd,'w') as stream:stream.write('OffMenu owner dataset batch\n\n```json\n'+body+'\n```\n')
    # One attempt only. A timeout or failed response may have posted successfully.
    result=capture(['/usr/bin/gh','pr','comment','30','--repo','https://github.com/maldous/offmenu','--body-file',str(path)],directory,'github-comment')
    return 'posted' if result['exitCode']==0 and not result['overflow'] else 'uncertain-no-retry'


def run(commit):
    if not HEX40.fullmatch(commit):raise Invalid('invalid-commit')
    if os.geteuid()==0 or not sys.flags.isolated:raise Invalid('normal-user-isolated-python-required')
    root=Path(__file__).resolve().parents[1]
    directory=Path(tempfile.mkdtemp(prefix='offmenu-owner-batch-'));directory.chmod(0o700)
    report={'schemaVersion':SCHEMA,'reportKind':'owner-dataset-grant-batch','batchVersion':1,
            'expectedCommit':commit,'artifactSha256':dict(PINS),'grant':{'status':'not-started'},'projector':{'status':'not-started'}}
    authenticated=False;exitcode=2
    try:
        bodies=verify_checkout(root,commit,directory)
        inspector=namespace(bodies[INSPECTOR],root/INSPECTOR)
        projector=namespace(bodies[PROJECTOR],root/PROJECTOR)
        verified_owner(directory);authenticated=True
        # This independent normal-user check still runs when the grant is blocked.
        observed=capture(['/usr/bin/python3','-I','-S','-B','-c',PROJECTOR_LOADER,str(root/PROJECTOR),PINS[PROJECTOR]],directory,'projector',cap=16384,timeout=90)
        try:
            if observed['exitCode'] not in (0,2) or observed['overflow']:raise Invalid('projector-unverified')
            evidence=projector['sanitize_report'](strict_json(observed['stdout']))
            if observed['exitCode']!=(0 if evidence['status']=='complete' else 2):raise Invalid('projector-unverified')
            report['projector']={'status':'reported','exitCode':observed['exitCode'],'report':evidence}
        except (Invalid,ValueError,TypeError,KeyError):report['projector']={'status':'unverified'}
        if not sys.stdin.isatty():raise Invalid('interactive-sudo-required')
        # The password prompt stays on the owner's terminal, never in a log.
        auth=subprocess.run(['/usr/bin/sudo','-v'],env=environment(),check=False)
        if auth.returncode:raise Invalid('sudo-auth-unavailable')
        # Any post-launch capture/cleanup failure leaves conservative state.
        report['grant']={'status':'unknown-outcome','exitCode':124};exitcode=124
        result=capture(['/usr/bin/sudo','-n','/usr/bin/python3','-I','-B','-c',ROOT_LOADER,str(root/HELPER),PINS[HELPER],'--apply'],directory,'grant',cap=MAX_CAPTURE,timeout=1200,privileged=True)
        exitcode=result['exitCode'] if result['exitCode'] is not None else 124
        if exitcode<0:exitcode=128-exitcode
        report['grant']={'status':'unknown-outcome' if result['outcome']=='unknown' else 'unverified','exitCode':exitcode}
        try:
            if result['overflow'] or len(result['stdout'])>16384:raise Invalid('invalid-grant-report')
            evidence=sanitize_grant(strict_json(result['stdout']),inspector,grant_error_codes(bodies[HELPER]))
            expected=2 if evidence['status']=='blocked' else 0
            if result['exitCode']!=expected:raise Invalid('invalid-grant-report')
            report['grant']={'status':'reported','exitCode':exitcode,'report':evidence}
        except (Invalid,ValueError,TypeError,KeyError):pass
    except (Invalid,OSError,UnicodeError,KeyboardInterrupt) as exc:
        # Only locally defined codes are emitted. Never include raw exceptions.
        report['batchBlocker']=str(exc) if isinstance(exc,Invalid) else 'batch-unverified'
    publication='not-attempted'
    if authenticated:
        try:publication=publish(report,directory)
        except (Invalid,OSError,KeyboardInterrupt):publication='uncertain-no-retry'
    print(json.dumps({'schemaVersion':SCHEMA,'reportKind':'owner-batch-outcome','grantStatus':report['grant']['status'],'helperExitCode':exitcode,'publication':publication,'privateLogsRetained':True},sort_keys=True))
    # This private local path is never put into the GitHub receipt.
    print('Private batch records: '+str(directory),file=sys.stderr)
    if report['grant']['status']=='unknown-outcome':print('Grant outcome is unknown. Keep the job queue quiet and request review before retrying.',file=sys.stderr)
    return exitcode


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--expected-commit',required=True)
    args=parser.parse_args()
    try:return run(args.expected_commit)
    except (Invalid,OSError):
        print(json.dumps({'schemaVersion':SCHEMA,'reportKind':'owner-batch-outcome','grantStatus':'not-started','helperExitCode':2,'publication':'not-attempted','privateLogsRetained':False},sort_keys=True))
        return 2


if __name__=='__main__':sys.exit(main())
