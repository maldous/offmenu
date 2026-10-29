#!/usr/bin/env python3
"""One normal-owner metadata collection and one PR30 receipt publication attempt.

No administrator access, new login, mounts, service changes, or Actions signal.
"""
import argparse
import hashlib
import json
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
import uuid

COLLECTOR = 'collect_owner_manifest_metadata.py'
COLLECTOR_SHA256 = '456e32de0c97fc66e2bea2dcc090d89c850d5538d126a18af7662acd37c0d293'
REPO = 'maldous/offmenu'
COMMENT = 'repos/maldous/offmenu/issues/30/comments'
CAP = 65536

class Blocked(Exception): pass

def fail(code): raise Blocked(code)

def environment():
    env = {'PATH':'/usr/local/bin:/usr/bin:/bin', 'HOME':pwd.getpwuid(os.getuid()).pw_dir,
           'LANG':'C.UTF-8', 'GH_HOST':'github.com', 'GH_PROMPT_DISABLED':'1',
           'GH_PAGER':'cat', 'GIT_CONFIG_NOSYSTEM':'1','GIT_CONFIG_GLOBAL':'/dev/null'}
    for key in ('GH_CONFIG_DIR','XDG_CONFIG_HOME','GH_TOKEN','GITHUB_TOKEN'):
        if os.environ.get(key): env[key]=os.environ[key]
    return env

def discover_gh():
    for candidate in (Path('/usr/local/bin/gh'), Path('/usr/bin/gh')):
        try:
            path = candidate.resolve(strict=True)
            for parent in path.parents:
                s=parent.stat()
                if s.st_uid != 0 or s.st_mode & 0o022 or not stat.S_ISDIR(s.st_mode): fail('gh-path-unsafe')
            s=path.stat()
            if s.st_uid != 0 or s.st_mode & 0o022 or not stat.S_ISREG(s.st_mode) or not s.st_mode & 0o111: fail('gh-path-unsafe')
            return str(path)
        except FileNotFoundError: continue
    fail('gh-unavailable')

def capture(args, timeout=90, cap=CAP):
    """Bounded in-memory stdout; raw stderr and credential values are never saved."""
    proc=None; selector=selectors.DefaultSelector(); chunks=bytearray(); count=[0,0]
    outcome='finished'; overflow=False; error_number=None; deadline=time.monotonic()+timeout
    try:
        proc=subprocess.Popen(args,stdin=subprocess.DEVNULL,stdout=subprocess.PIPE,stderr=subprocess.PIPE,
                              env=environment(),start_new_session=True)
        selector.register(proc.stdout,selectors.EVENT_READ,0); selector.register(proc.stderr,selectors.EVENT_READ,1)
        while selector.get_map():
            remaining=deadline-time.monotonic()
            if remaining<=0: outcome='unknown'; break
            for key,_ in selector.select(min(remaining,1)):
                part=os.read(key.fileobj.fileno(),8192)
                if not part: selector.unregister(key.fileobj); continue
                index=key.data; count[index]+=len(part)
                if index==0: chunks.extend(part[:max(0,cap-len(chunks))])
                if count[index]>cap: overflow=True; outcome='unknown'; break
            if overflow: break
        if outcome=='finished':
            try: proc.wait(timeout=max(0.01,deadline-time.monotonic()))
            except subprocess.TimeoutExpired: outcome='unknown'
    except (OSError,KeyboardInterrupt) as exc:
        outcome='unknown'; error_number=getattr(exc,'errno',None)
    finally:
        selector.close()
        if proc is not None:
            if proc.poll() is None: proc.kill(); proc.wait()
            for stream in (proc.stdout,proc.stderr):
                if stream is not None: stream.close()
    return {'exitCode':None if outcome=='unknown' or proc is None else proc.returncode,
            'outcome':outcome,'overflow':overflow,'errno':error_number,'stdout':bytes(chunks)}

def summarize(result):
    return {key:result[key] for key in ('exitCode','outcome','overflow','errno')}

def query(gh, endpoint, expression, label, diagnostics):
    result=capture([gh,'api','--hostname','github.com',endpoint,'--jq',expression],cap=4096)
    diagnostics[label]=summarize(result)
    if result['exitCode']!=0 or result['overflow'] or result['outcome']!='finished': fail(label+'-unavailable')
    try: return json.loads(result['stdout'])
    except (ValueError,UnicodeError): fail(label+'-invalid')

def read_collector():
    path=Path(__file__).resolve().parent/COLLECTOR
    fd=os.open(path,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK)
    try:
        s=os.fstat(fd)
        if not stat.S_ISREG(s.st_mode) or s.st_nlink!=1 or s.st_size>32768: fail('collector-file-invalid')
        body=os.read(fd,32769)
        if len(body)!=s.st_size or hashlib.sha256(body).hexdigest()!=COLLECTOR_SHA256: fail('collector-pin-mismatch')
    finally: os.close(fd)
    namespace={'__name__':'owner_metadata_collector','__file__':str(path)}
    exec(compile(body,str(path),'exec'),namespace)
    return namespace['run']

def write_new(path, body):
    fd=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
    with os.fdopen(fd,'wb') as stream:
        stream.write(body); stream.flush(); os.fsync(stream.fileno())

def encode(value): return json.dumps(value,sort_keys=True,separators=(',',':')).encode()

def run(commit):
    if not re.fullmatch(r'[0-9a-f]{40}',commit): fail('invalid-reviewed-commit')
    owner=pwd.getpwnam('user')
    if os.getuid()!=owner.pw_uid or os.geteuid()!=owner.pw_uid or owner.pw_uid==0 or not sys.flags.isolated: fail('normal-owner-isolated-python-required')
    directory=Path(tempfile.mkdtemp(prefix='offmenu-owner-metadata-')); directory.chmod(0o700)
    report={'schemaVersion':'offmenu-owner-metadata-batch/1','reportId':uuid.uuid4().hex,
            'reportKind':'owner-metadata-receipt','reviewedCommit':commit,
            'collectorSha256':COLLECTOR_SHA256,'actionsCompletionSignal':False,
            'publication':{'status':'not-attempted','destination':'https://github.com/maldous/offmenu/pull/30'},
            'commands':{},'collection':{'status':'not-started'}}
    try:
        report['collection']=read_collector()()
        report['collectionExitCode']=0 if report['collection'].get('status')=='collected' else 2
        # Preserve useful collection even when authentication/publication fails.
        write_new(directory/'collection.json',encode(report['collection'])+b'\n')
        gh=discover_gh()
        # Both token and stored gh auth are handled by gh itself; no auth token output.
        user=query(gh,'user','{login: .login, id: .id}','owner',report['commands'])
        if user!={'login':'maldous','id':6347545}: fail('owner-auth-mismatch')
        repo=query(gh,'repos/'+REPO,'{full_name: .full_name, private: .private}','repository',report['commands'])
        if repo!={'full_name':REPO,'private':True}: fail('repository-identity-mismatch')
        report['publication']['status']='attempting-once'
        body=encode(report)
        if len(body)>60000: fail('publication-size-limit')
        payload={'body':'OffMenu owner metadata receipt. This is not a Foo Actions completion signal.\n\n```json\n'+body.decode()+'\n```'}
        write_new(directory/'publication.json',encode(payload))
        # One attempt only: a missing/failed response can still mean it posted.
        result=capture([gh,'api','--hostname','github.com',COMMENT,'--method','POST','--input',str(directory/'publication.json'),'--jq','{id: .id, html_url: .html_url}'],cap=4096)
        report['commands']['publication']=summarize(result)
        report['publication']['status']='uncertain-no-retry'
        if result['exitCode']==0 and result['outcome']=='finished' and not result['overflow']:
            try:
                response=json.loads(result['stdout'])
                url=response.get('html_url',''); cid=response.get('id')
                if (type(cid) is int and cid>0 and isinstance(url,str)
                    and re.fullmatch(r'https://github\.com/maldous/offmenu/(?:pull|issues)/30#issuecomment-[0-9]+',url)):
                    report['publication'].update(status='posted',commentId=cid,url=url)
            except (ValueError,UnicodeError,AttributeError): pass
    except (Exception,KeyboardInterrupt) as exc:
        report['errorCode']=str(exc) if isinstance(exc,Blocked) else 'owner-batch-failed'
    write_new(directory/'receipt.json',encode(report)+b'\n')
    return report,directory

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--commit',required=True)
    args=parser.parse_args()
    try:
        report,directory=run(args.commit)
        print(json.dumps({'reportId':report['reportId'],'collectionStatus':report['collection']['status'],
                          'publication':report['publication'],'receiptDirectory':str(directory),
                          'errorCode':report.get('errorCode')},sort_keys=True))
        return 0 if report['publication']['status']=='posted' else 2
    except (Exception,KeyboardInterrupt) as exc:
        print(json.dumps({'status':'blocked','errorCode':str(exc) if isinstance(exc,Blocked) else 'owner-batch-failed'}))
        return 2

if __name__=='__main__': sys.exit(main())
