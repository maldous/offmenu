from pathlib import Path
import base64, hashlib, zlib
r=Path(__file__).parent
payload=(r/'job_runner.py').read_bytes(); sha=hashlib.sha256(payload).hexdigest()
s='''# Candidate create-only project-scoped installer; no host administration.
import base64, fcntl, hashlib, json, os, stat, uuid, zlib
from pathlib import Path
SOURCE_SHA = %r
OLD_SHA = '81b2918d8384ac3da63397263263c01340dc9b90031672d1fa4baab16aef8c1a'
PAYLOAD = %r
DIRECTORY = Path('/offmenu/scripts/windmill')
DESTINATION = DIRECTORY / 'job_runner_capacity_v3.py'
LOCKS = Path('/offmenu/data/.offmenu-platform/locks')

def check_parents(path):
    for p in (path, *path.parents):
        if p.is_symlink(): raise RuntimeError('SymlinkRefused')

def read_regular(path):
    fd=os.open(path, os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK)
    with os.fdopen(fd,'rb') as f:
        info=os.fstat(f.fileno())
        if not stat.S_ISREG(info.st_mode) or info.st_size>65536: raise RuntimeError('SourceTypeRefused')
        return f.read(65537)

check_parents(DIRECTORY);check_parents(LOCKS)
b = zlib.decompress(base64.b64decode(PAYLOAD, validate=True))
if len(b)>65536 or hashlib.sha256(b).hexdigest()!=SOURCE_SHA:raise RuntimeError('PayloadMismatch')
compile(b,str(DESTINATION),'exec')
if hashlib.sha256(read_regular(DIRECTORY/'job_runner.py')).hexdigest()!=OLD_SHA:raise RuntimeError('LegacyPreimageMismatch')
fds=[];temp=None
try:
    # No install while legacy writers or pooled work are active. Do not delete
    # any stale marker; unresolved ownership requires separate reconciliation.
    for name in ('capacity-admission.lock','execution-access.lock'):
        fd=os.open(LOCKS/name,os.O_RDWR|os.O_CREAT|os.O_NOFOLLOW,0o600);fds.append(fd)
        fcntl.flock(fd,fcntl.LOCK_EX|fcntl.LOCK_NB)
    if any(LOCKS.glob('execution-slot-*.inflight.json')):raise RuntimeError('InflightMarkerPresent')
    if DESTINATION.exists():
        if hashlib.sha256(read_regular(DESTINATION)).hexdigest()!=SOURCE_SHA:raise RuntimeError('ExistingVersionMismatch')
        outcome='already_present_exact'
    else:
        temp=DIRECTORY/('.capacity-v3-'+uuid.uuid4().hex)
        fd=os.open(temp,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o660)
        with os.fdopen(fd,'wb') as f:f.write(b);f.flush();os.fsync(f.fileno())
        os.link(temp,DESTINATION,follow_symlinks=False);temp.unlink();temp=None
        fd=os.open(DIRECTORY,os.O_DIRECTORY)
        try:os.fsync(fd)
        finally:os.close(fd)
        outcome='created_new_version'
    if hashlib.sha256(read_regular(DESTINATION)).hexdigest()!=SOURCE_SHA:raise RuntimeError('ReadbackMismatch')
    print(json.dumps({'status':outcome,'sha256':SOURCE_SHA,'legacy_unchanged':hashlib.sha256(read_regular(DIRECTORY/'job_runner.py')).hexdigest()==OLD_SHA}))
finally:
    if temp is not None and temp.exists():temp.unlink()
    for fd in reversed(fds):os.close(fd)
'''%(sha,base64.b64encode(zlib.compress(payload)).decode())
(r/'install_capacity.py').write_text(s)
