#!/usr/bin/env python3
"""User-operated, versioned read-only file grant for the existing dedicated runner.

Without --apply, validate and report only. No downloads, credentials, ACL/mode
changes to originals, broad source mounts, or corpus activation.
"""
import argparse
import ctypes
import errno
import fcntl
import hashlib
import grp
import json
import os
from pathlib import Path
import pwd
import select
import stat
import subprocess
import sys
import tempfile
import time

SERVICE = 'offmenu-runner.service'
UNIT = Path('/etc/systemd/system') / SERVICE
DROP_DIR = UNIT.parent / (SERVICE + '.d')
DROP_IN = DROP_DIR / '40-selected-datasets-v1.conf'
INSPECTOR_SHA = '74ec7d6ad41cdfbb6cdbd789aae43f7d569c1f6e2da9cfa8445ea29a914b43d1'
BACKUP = Path('/var/lib/offmenu-selected-datasets-v1')
SCAFFOLD = BACKUP / 'snapshot'
STAGING = BACKUP / '.snapshot.staging'
CACHE = '/srv/offmenu-refresh/cache'
ORIGINALS = Path('/home/user/src/offmenu-data')
DISPATCH_LOCK = Path('/srv/offmenu-refresh/outputs/locks/dispatcher.lock')
BOOTSTRAP_BIND = '/srv/offmenu-bootstrap-input:' + CACHE
UNIT_SHA = 'c2fdece08f9af9ea9a99011c9276c706a282c683079d0abe6366ceb77195b268'
HELPERS = {
 '/usr/local/lib/offmenu-runner/runner_host_setup.py':'41f848757c21a171033ce97557292eb3586d334cd1fb026a6b132ddbeb3032a6',
 '/usr/local/lib/offmenu-runner/setup-foo-runner.sh':'71219b99120f774171cbfaf312eb1ec9dd333bde63875a8f73df999ab4fe64a1',
}
# Exact source paths and fixed view paths. This program never walks source siblings.
FILES = {
 'NO_EN_FOODS':('national-originals/norway/en-foods.json','norway/en-foods.json','raw'),
 'NO_NB_FOODS':('national-originals/norway/nb-foods.json','norway/nb-foods.json','raw'),
 'NO_EN_NUTRIENTS':('national-originals/norway/en-nutrients.json','norway/en-nutrients.json','raw'),
 'NO_EN_SOURCES':('national-originals/norway/en-sources.json','norway/en-sources.json','raw'),
 'FR_WORKBOOK':('national-originals/ciqual/Table Ciqual 2025_ENG_2025_11_03.xlsx','ciqual/Table Ciqual 2025_ENG_2025_11_03.xlsx','raw'),
 'FR_IDENTITIES':('national-originals/ciqual/alim_2025_11_03.xml','ciqual/alim_2025_11_03.xml','raw'),
 'NATIONAL_ACQUISITION':('national-originals/acquisition.json','metadata/national-acquisition.json','metadata'),
 'NO_PRIOR_MANIFEST':('matvaretabellen-2026/manifest.json','metadata/no-prior-manifest.json','metadata'),
 'FR_PRIOR_MANIFEST':('ciqual-2025/manifest.json','metadata/fr-prior-manifest.json','metadata'),
 'FI_ACQUISITION':('originals/next-national-20261013/acquisition.json','metadata/fi-acquisition.json','metadata'),
 'FI_PRIOR_MANIFEST':('fineli-20.0/manifest.json','metadata/fi-prior-manifest.json','metadata'),
}
GROUPS = {
 'NO':('NO_EN_FOODS','NO_NB_FOODS','NO_EN_NUTRIENTS','NO_EN_SOURCES','NATIONAL_ACQUISITION','NO_PRIOR_MANIFEST'),
 'FR':('FR_WORKBOOK','FR_IDENTITIES','NATIONAL_ACQUISITION','FR_PRIOR_MANIFEST'),
 'FI':('FI_ACQUISITION','FI_PRIOR_MANIFEST'),
}
MAX_RAW, MAX_META, MAX_TOTAL = 64*1024*1024, 64*1024, 256*1024*1024
BASE_PROPERTIES = {
 'User':'offmenu-runner','Group':'offmenu-runner','NoNewPrivileges':'yes',
 'ProtectSystem':'strict','ProtectHome':'tmpfs','PrivateTmp':'yes','PrivateDevices':'yes',
 'CapabilityBoundingSet':'','AmbientCapabilities':'','BindPaths':'',
 'FragmentPath':str(UNIT),'ReadWritePaths':'/srv/offmenu-runner /srv/offmenu-refresh/outputs',
 'ControlGroup':'/system.slice/'+SERVICE,
}


class Blocked(Exception):
    pass


def block(code):
    raise Blocked(code)


def regular_bytes(path, cap, owner=0):
    safe_parents(path, {0})
    s=path.lstat()
    if not stat.S_ISREG(s.st_mode) or s.st_uid != owner or s.st_mode & 0o022 or s.st_nlink != 1 or s.st_size > cap:
        block('protected-file-invalid')
    fd=os.open(path,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK)
    try:
        if signature(os.fstat(fd)) != signature(s):block('protected-file-changed')
        body=os.read(fd,cap+1)
        if len(body) != s.st_size or signature(os.fstat(fd)) != signature(s):block('protected-file-changed')
        return body
    finally:os.close(fd)


def signature(s):
    return (s.st_dev,s.st_ino,s.st_size,s.st_mtime_ns,s.st_ctime_ns,s.st_mode,s.st_uid,s.st_gid,s.st_nlink)


def safe_parents(path, owners):
    for parent in reversed(path.parents):
        s=parent.lstat()
        if not stat.S_ISDIR(s.st_mode) or s.st_uid not in owners or s.st_mode & 0o022:
            block('unsafe-parent')


def protected_directory(path, mode=0o755, create=False):
    safe_parents(path,{0})
    if create and not path.exists():path.mkdir(mode=mode)
    s=path.lstat()
    if not stat.S_ISDIR(s.st_mode) or s.st_uid != 0 or stat.S_IMODE(s.st_mode) != mode:
        block('protected-directory-conflict')


def account():
    try:
        runner=pwd.getpwnam('offmenu-runner'); owner=pwd.getpwnam('user')
        group=grp.getgrnam('offmenu-runner')
    except KeyError:block('required-account-missing')
    aliases=grp.getgrall(); users=pwd.getpwall()
    if (runner.pw_uid == 0 or runner.pw_gid == 0 or runner.pw_dir != '/srv/offmenu-runner' or runner.pw_shell not in {'/usr/sbin/nologin','/sbin/nologin'}
        or set(os.getgrouplist('offmenu-runner',runner.pw_gid)) != {runner.pw_gid}
        or group.gr_gid != runner.pw_gid or set(group.gr_mem)-{'offmenu-runner'}
        or len(aliases)>4096 or len(users)>4096
        or [g.gr_name for g in aliases if g.gr_gid==runner.pw_gid] != ['offmenu-runner']
        or any(u.pw_gid==runner.pw_gid and u.pw_name!='offmenu-runner' for u in users)):
        block('runner-account-conflict')
    return runner, owner


def anchored_source(asset_id,runner,owner):
    relative,_,kind=FILES[asset_id]
    parts=(ORIGINALS/relative).parts
    parent=os.open('/',os.O_RDONLY|os.O_DIRECTORY)
    fd=None
    try:
        for part in parts[1:-1]:
            nxt=os.open(part,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW,dir_fd=parent)
            os.close(parent);parent=nxt
            info=os.fstat(parent)
            # Sources may be maintained in the owner's primary group. Held
            # descriptors plus immutable content pins prevent substitution from
            # becoming exposed data; world-write/unknown identity still fails.
            primary_groups={0:0,owner.pw_uid:owner.pw_gid}
            if info.st_uid not in primary_groups or info.st_gid!=primary_groups[info.st_uid] or info.st_mode&0o002:block('unsafe-path')
            try:
                os.getxattr(parent,'system.posix_acl_access')
                block('acl-requires-review')
            except OSError as exc:
                if exc.errno not in (errno.ENODATA,errno.ENOTSUP):block('access-unverified')
        before=os.stat(parts[-1],dir_fd=parent,follow_symlinks=False)
        # The same primary-group source policy applies to non-executable leaves.
        # Concurrent changes still cannot pass the private immutable-digest gate.
        primary_groups={0:0,owner.pw_uid:owner.pw_gid}
        if not stat.S_ISREG(before.st_mode) or before.st_nlink!=1 or before.st_uid not in primary_groups or before.st_gid!=primary_groups[before.st_uid] or before.st_mode&0o113:block('unsafe-file')
        if before.st_size>(MAX_RAW if kind=='raw' else MAX_META):block('oversized')
        fd=os.open(parts[-1],os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK,dir_fd=parent)
        info=os.fstat(fd)
        if signature(info)!=signature(before):block('selected-source-changed')
        try:
            os.getxattr(fd,'system.posix_acl_access')
            block('acl-requires-review')
        except OSError as exc:
            if exc.errno not in (errno.ENODATA,errno.ENOTSUP):block('access-unverified')
        read_bit=stat.S_IRUSR if info.st_uid==runner.pw_uid else stat.S_IRGRP if info.st_gid==runner.pw_gid else stat.S_IROTH
        if not info.st_mode&read_bit:block('runner-read-denied')
        result=fd;fd=None
        return result,info
    finally:
        if fd is not None:os.close(fd)
        os.close(parent)


def source_check(asset_id, runner, owner):
    try:
        fd,info=anchored_source(asset_id,runner,owner)
        os.close(fd)
        return 'validated',info
    except FileNotFoundError:return 'missing',None
    except Blocked as exc:return str(exc),None
    except OSError:return 'unsafe-path',None


def preflight_sources(runner,owner):
    statuses={};observations={}
    for key in FILES:
        statuses[key],s=source_check(key,runner,owner)
        if s is not None:observations[key]=s
    if sum(s.st_size for k,s in observations.items() if FILES[k][2]=='raw') > MAX_TOTAL:
        for key in observations:
            if FILES[key][2]=='raw':statuses[key]='aggregate-limit'
    selected=set()
    for country, keys in GROUPS.items():
        if all(statuses[k]=='validated' for k in keys):selected.update(keys)
    # Optional Finland metadata never enables raw files or blocks NO/FR.
    if not any(all(k in selected for k in GROUPS[c]) for c in ('NO','FR')):
        selected.clear()
    return statuses,sorted(selected),observations


def bindings(selected):
    return [str(SCAFFOLD)+':'+CACHE]


def dropin_bytes(selected):
    lines=['[Service]','BindReadOnlyPaths=']
    # All paths are compile-time constants. Quote spaces; percent/backslash/quote are excluded.
    for mapping in bindings(selected):
        if any(c in mapping for c in ('%','\\','"','\n','\r')):block('invalid-fixed-path')
        lines.append('BindReadOnlyPaths="'+mapping+'"')
    return ('\n'.join(lines)+'\n').encode()


def bounded_read(path,cap):
    fd=os.open(path,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK)
    try:
        chunks=[];total=0
        while True:
            part=os.read(fd,min(65536,cap+1-total))
            if not part:break
            total+=len(part)
            if total>cap:block('bounded-read-limit')
            chunks.append(part)
        return b''.join(chunks)
    finally:os.close(fd)


def command(args, capture=False):
    proc=subprocess.Popen(args,stdin=subprocess.DEVNULL,stdout=subprocess.PIPE if capture else subprocess.DEVNULL,
                          stderr=subprocess.DEVNULL,env={'PATH':'/usr/bin:/bin','LANG':'C','SYSTEMD_COLORS':'0'})
    deadline=time.monotonic()+90;parts=[];total=0
    try:
        if capture:
            while True:
                left=deadline-time.monotonic()
                if left<=0:block('system-command-timeout')
                ready,_,_=select.select([proc.stdout],[],[],left)
                if not ready:block('system-command-timeout')
                part=os.read(proc.stdout.fileno(),min(4096,65537-total))
                if not part:break
                total+=len(part)
                if total>65536:block('system-response-oversized')
                parts.append(part)
        if proc.wait(timeout=max(0.01,deadline-time.monotonic())):block('system-command-failed')
        return b''.join(parts).decode('utf-8','strict') if capture else ''
    finally:
        if proc.poll() is None:proc.kill();proc.wait()
        if proc.stdout is not None:proc.stdout.close()


def properties():
    names=list(BASE_PROPERTIES)+['BindReadOnlyPaths','DropInPaths','ActiveState','SubState','MainPID']
    text=command(['/usr/bin/systemctl','show',SERVICE,'--property='+','.join(names)],True)
    values={}
    for line in text.splitlines():
        key,sep,value=line.partition('=')
        if sep and key in names:
            if key in values:block('service-properties-invalid')
            values[key]=value
    return values


def normalize_bind(value):
    return value.replace('\\x20',' ').replace('\\040',' ').replace('"','').replace(':rbind','')


def verify_properties(values,selected=None,active=True):
    if any(values.get(k)!=v for k,v in BASE_PROPERTIES.items()):block('service-sandbox-drift')
    expected=' '.join(bindings(selected)) if selected is not None else BOOTSTRAP_BIND
    if normalize_bind(values.get('BindReadOnlyPaths','')) != expected:block('service-mount-drift')
    if values.get('DropInPaths') != (str(DROP_IN) if selected is not None else ''):block('service-dropin-conflict')
    if active and (values.get('ActiveState')!='active' or values.get('SubState')!='running' or not values.get('MainPID','').isdigit() or int(values['MainPID'])<=1):
        block('service-not-running')


def verify_baseline(selected):
    unit=regular_bytes(UNIT,65536)
    if hashlib.sha256(unit).hexdigest()!=UNIT_SHA:block('base-unit-pin-mismatch')
    for name,pin in HELPERS.items():
        if hashlib.sha256(regular_bytes(Path(name),65536)).hexdigest()!=pin:block('installed-helper-pin-mismatch')
    existing=False
    if DROP_DIR.exists() or DROP_DIR.is_symlink():
        protected_directory(DROP_DIR)
        contents=set()
        with os.scandir(DROP_DIR) as entries:
            for count,entry in enumerate(entries):
                if count>=1:block('unrecognized-dropin')
                contents.add(DROP_DIR/entry.name)
        if contents and contents!={DROP_IN}:block('unrecognized-dropin')
        if contents:
            if regular_bytes(DROP_IN,16384)!=dropin_bytes(selected):block('existing-grant-conflicts')
            existing=True
    verify_properties(properties(),selected if existing else None)
    return unit,existing


def idle_lock(runner):
    # Existing dispatcher lock only: never create/chown a file in runner-owned outputs.
    for p in (DISPATCH_LOCK.parent.parent,DISPATCH_LOCK.parent):
        s=p.lstat()
        if not stat.S_ISDIR(s.st_mode) or s.st_uid!=runner.pw_uid or s.st_mode&0o077:block('dispatcher-lock-parent-unsafe')
    s=DISPATCH_LOCK.lstat()
    if not stat.S_ISREG(s.st_mode) or s.st_uid!=runner.pw_uid or s.st_nlink!=1 or s.st_mode&0o077 or s.st_size>4096:block('dispatcher-lock-unsafe')
    fd=os.open(DISPATCH_LOCK,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK)
    try:
        if signature(os.fstat(fd))!=signature(s):block('dispatcher-lock-changed')
        try:fcntl.flock(fd,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError:block('job-active')
        return fd
    except BaseException:os.close(fd);raise


def assert_idle(runner, existing=False):
    values=properties();verify_properties(values, CURRENT_SELECTION if existing else None)
    root=Path('/sys/fs/cgroup/system.slice')/SERVICE
    if not root.is_dir():block('service-cgroup-unavailable')
    # TasksMax is256. No recursive scan: unknown child cgroups make idleness unproven.
    with os.scandir(root) as entries:
        for count,entry in enumerate(entries):
            if count>=256 or entry.is_dir(follow_symlinks=False):block('service-cgroup-unrecognized')
    raw=bounded_read(root/'cgroup.procs',4096)
    if len(raw)>4096:block('service-process-list-unbounded')
    try:pids=[int(v) for v in raw.split()]
    except ValueError:block('service-process-list-invalid')
    if not pids or len(pids)>256 or int(values['MainPID']) not in pids:block('service-process-identity-invalid')
    for pid in pids:
        try:
            proc=Path('/proc')/str(pid)
            comm=bounded_read(proc/'comm',32).decode().strip()
            status=bounded_read(proc/'status',65536).decode()
            uids=next(line.split()[1:] for line in status.splitlines() if line.startswith('Uid:'))
        except (OSError,StopIteration):block('service-process-unverified')
        if len(status)>65536 or len(comm)>32 or uids!=[str(runner.pw_uid)]*4:block('service-process-owner-invalid')
        if comm=='Runner.Worker':block('job-active')
        if comm not in {'runsvc.sh','node','Runner.Listener','bash','sleep'}:block('service-process-unrecognized')


def ensure_file(path,body,mode=0o644):
    safe_parents(path,{0})
    if path.exists() or path.is_symlink():
        if regular_bytes(path,max(len(body),65536))!=body or stat.S_IMODE(path.lstat().st_mode)!=mode:block('versioned-file-conflict')
        return
    fd,tmp=tempfile.mkstemp(prefix='.grant-v1-',dir=path.parent)
    try:
        os.fchmod(fd,mode)
        with os.fdopen(fd,'wb') as out:out.write(body);out.flush();os.fsync(out.fileno())
        os.replace(tmp,path)
    finally:
        if os.path.exists(tmp):os.unlink(tmp)


def rename_noreplace(source,destination):
    libc=ctypes.CDLL(None,use_errno=True)
    function=getattr(libc,'renameat2',None)
    if function is None:block('atomic-no-clobber-unavailable')
    if function(-100,os.fsencode(source),-100,os.fsencode(destination),1):
        block('snapshot-publish-conflict')


def reference_parser():
    path=Path(__file__).absolute().parent/'inspect-selected-datasets.py'
    body=bounded_read(path,32768)
    if hashlib.sha256(body).hexdigest()!=INSPECTOR_SHA:block('inspector-dependency-pin-mismatch')
    private_code=BACKUP/'approved-inspector.py'
    ensure_file(private_code,body,0o600)
    namespace={'__name__':'offmenu_selected_reference','__file__':str(private_code)}
    exec(compile(body,str(path),'exec'),namespace)
    return namespace


def snapshot_directory(path,runner,create=False,stage=False):
    safe_parents(path,{0})
    mode=0o700 if stage else 0o750
    if create and not path.exists():
        path.mkdir(mode=mode)
        if not stage:os.chown(path,0,runner.pw_gid)
    info=path.lstat()
    if not stat.S_ISDIR(info.st_mode) or info.st_uid!=0 or info.st_gid!=(0 if stage else runner.pw_gid) or stat.S_IMODE(info.st_mode)!=mode:
        block('snapshot-directory-conflict')


def file_inventory(root,selected,runner):
    snapshot_directory(root,runner)
    expected={FILES[k][1] for k in selected};seen=set()
    with os.scandir(root) as entries:
        for count,entry in enumerate(entries):
            if count>=3 or entry.name not in {'norway','ciqual','metadata'} or not entry.is_dir(follow_symlinks=False):block('snapshot-unrecognized-file')
            directory=root/entry.name;snapshot_directory(directory,runner)
            with os.scandir(directory) as children:
                for number,child in enumerate(children):
                    rel=entry.name+'/'+child.name
                    if number>=11 or rel not in expected: block('snapshot-unrecognized-file')
                    info=child.stat(follow_symlinks=False)
                    if not stat.S_ISREG(info.st_mode) or info.st_uid!=0 or info.st_gid!=runner.pw_gid or stat.S_IMODE(info.st_mode)!=0o440 or info.st_nlink!=1:block('snapshot-file-conflict')
                    seen.add(rel)
    if seen!=expected:block('snapshot-selection-mismatch')


def evidence_selection(evidence,selected,reference,report):
    accepted=set()
    for country,keys in GROUPS.items():
        valid=all(k in selected for k in keys)
        for key in keys:
            if key not in selected:continue
            asset=evidence['assets'][key]
            valid=valid and asset['status']=='inspected' and asset['historicalMatch']!='mismatch'
            if FILES[key][2]=='metadata':valid=valid and asset['historicalMatch']=='match'
            else:valid=valid and asset['receiptMatch']=='match' and asset['acquisitionMatch']=='match'
        if country in ('NO','FR') and valid:
            source=evidence['sources'][country]
            valid=source['provenanceVerified'] and source['historicalRightsProfile']==reference['SOURCES'][country][4]
        report.setdefault('sources',{})[country]='validated' if valid else 'blocked'
        if valid:accepted.update(keys)
    if not any(all(k in accepted for k in GROUPS[c]) for c in ('NO','FR')):
        accepted.clear()
    for key in selected:
        if key not in accepted:report.setdefault('assets',{})[key]='evidence-blocked'
    if not accepted:block('snapshot-no-verified-source-group')
    return sorted(accepted)


def verified_snapshot(selected,runner,reference,report):
    file_inventory(SCAFFOLD,selected,runner)
    # Bound size before the inspector opens contents; it will read each selected
    # file once and only parse the small receipts. Read-only mount is checked later.
    total=0
    for key in selected:
        size=(SCAFFOLD/FILES[key][1]).stat().st_size
        if size>(MAX_RAW if FILES[key][2]=='raw' else MAX_META):block('snapshot-file-oversized')
        if FILES[key][2]=='raw':total+=size
    if total>MAX_TOTAL:block('snapshot-total-oversized')
    evidence=reference['inspect'](str(SCAFFOLD))
    report['snapshotEvidence']=evidence
    if evidence_selection(evidence,selected,reference,report)!=selected:block('existing-snapshot-evidence-drift')
    return {k:(SCAFFOLD/FILES[k][1]).stat() for k in selected},evidence


def create_snapshot(selected,runner,owner,observations,report):
    protected_directory(BACKUP,0o700)
    reference=reference_parser()
    if SCAFFOLD.exists() or SCAFFOLD.is_symlink():
        saved=reference['strict_json'](regular_bytes(BACKUP/'selection.json',4096))
        if not isinstance(saved,list) or not saved or any(not isinstance(k,str) or k not in FILES for k in saved) or saved!=sorted(set(saved)) or not set(saved)<=set(selected):block('existing-snapshot-selection-conflict')
        observations,evidence=verified_snapshot(saved,runner,reference,report)
        report['snapshotEvidence']=evidence
        return observations
    if STAGING.exists() or STAGING.is_symlink():block('owned-partial-snapshot-requires-review')
    snapshot_directory(STAGING,runner,create=True,stage=True)
    created=[];created_dirs=[];handles={};published=False
    deadline=time.monotonic()+180
    try:
        total=sum(observations[k].st_size for k in selected)
        if os.statvfs(STAGING).f_bavail*os.statvfs(STAGING).f_frsize<total+16*1024*1024:block('snapshot-disk-insufficient')
        for key in selected:
            fd,info=anchored_source(key,runner,owner)
            handles[key]=fd
            if signature(info)!=signature(observations[key]):block('selected-source-changed')
        for key in selected:
            path=STAGING/FILES[key][1]
            if not path.parent.exists():
                snapshot_directory(path.parent,runner,create=True);created_dirs.append(path.parent)
            out=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600);created.append(path)
            try:
                remaining=observations[key].st_size
                while remaining:
                    if time.monotonic()>deadline:block('snapshot-copy-deadline')
                    chunk=os.read(handles[key],min(65536,remaining))
                    if not chunk:block('selected-source-changed')
                    report['sourceBytesRead']+=len(chunk);remaining-=len(chunk)
                    view=memoryview(chunk)
                    while view:
                        written=os.write(out,view)
                        if not written:block('snapshot-write-failed')
                        report['snapshotBytesWritten']+=written;view=view[written:]
                os.fsync(out);os.fchown(out,0,runner.pw_gid);os.fchmod(out,0o440)
            finally:os.close(out)
        for key,fd in handles.items():
            if signature(os.fstat(fd))!=signature(observations[key]):block('selected-source-changed')
        # Verify all copied bytes/provenance before making the snapshot visible
        # to the runner. Only this root process can traverse the0700 staging root.
        evidence=reference['inspect'](str(STAGING))
        report['snapshotEvidence']=evidence
        accepted=evidence_selection(evidence,selected,reference,report)
        for key in selected:
            if key not in accepted:
                path=STAGING/FILES[key][1];path.unlink();created.remove(path)
        for directory in list(created_dirs):
            if not any(directory.iterdir()):directory.rmdir();created_dirs.remove(directory)
        # The accepted subset is immutable across retries; no implicit scope expansion.
        ensure_file(BACKUP/'selection.json',json.dumps(accepted,separators=(',',':')).encode(),0o600)
        selected=accepted
        os.chown(STAGING,0,runner.pw_gid);os.chmod(STAGING,0o750)
        rename_noreplace(STAGING,SCAFFOLD);published=True
        report['snapshotVerified']=True
        return {k:(SCAFFOLD/FILES[k][1]).stat() for k in selected}
    finally:
        for fd in handles.values():os.close(fd)
        if not published:
            # Only paths created by this invocation are removed. Unknown prior
            # partial snapshots are never removed or overwritten automatically.
            for path in reversed(created):path.unlink()
            for directory in reversed(created_dirs):directory.rmdir()
            STAGING.rmdir()


def verify_mounts(pid,selected,observations):
    with open('/proc/'+str(pid)+'/mountinfo','rb') as inp:body=inp.read(1024*1024+1)
    if len(body)>1024*1024:block('mountinfo-unbounded')
    mounts={}
    for line in body.decode().splitlines():
        fields=line.split()
        if len(fields)>=7:
            target=fields[4].replace('\\040',' ').replace('\\011','\t').replace('\\134','\\')
            mounts[target]=fields[5].split(',')
    targets=[CACHE]
    if any('ro' not in mounts.get(target,[]) for target in targets):block('read-only-mount-verification-failed')
    for key in selected:
        mounted=os.stat('/proc/'+str(pid)+'/root'+CACHE+'/'+FILES[key][1],follow_symlinks=False)
        if signature(mounted)!=signature(observations[key]):block('mounted-file-identity-mismatch')


def administrative_lock():
    # Root-owned lock is separate from the unprivileged dispatcher lock.
    lock_path=Path('/run/offmenu-selected-datasets-v1.lock')
    safe_parents(lock_path,{0})
    fd=os.open(lock_path,os.O_CREAT|os.O_RDWR|os.O_NOFOLLOW,0o600)
    try:
        s=os.fstat(fd)
        if not stat.S_ISREG(s.st_mode) or s.st_uid!=0 or s.st_nlink!=1 or s.st_mode&0o077:block('administrative-lock-unsafe')
        try:fcntl.flock(fd,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError:block('administrative-batch-active')
        return fd
    except BaseException:os.close(fd);raise


def isolated_runtime():
    return bool(sys.flags.isolated)


CURRENT_SELECTION=[]


def run(apply=False):
    global CURRENT_SELECTION
    report={'schemaVersion':'offmenu-selected-data-grant/1','reportKind':'dataset-view-grant','grantVersion':1,'status':'blocked','applied':False,'sourceBytesRead':0,
            'sourceBytesWritten':0,'snapshotBytesWritten':0,'snapshotVerified':False,'sourcePermissionsChanged':False,'credentialsRead':False,
            'selectedAssets':[],'assets':{},'sources':{c:'not-checked' for c in GROUPS},'serviceReady':False,'serviceRestarted':False,'effectiveMountAssets':[],'readOnlyMountsVerified':False,'rollbackAttempted':False,'rollbackRestored':None}
    fd=None;admin_fd=None;added=False;stopped=False;created_drop_dir=False
    try:
        if os.geteuid()!=0:block('local-root-required')
        if not isolated_runtime():block('isolated-python-required')
        runner,owner=account()
        statuses,selected,observations=preflight_sources(runner,owner)
        report['assets']=statuses;report['selectedAssets']=selected;CURRENT_SELECTION=selected
        report['sources']={c:('validated' if all(k in selected for k in keys) else 'blocked') for c,keys in GROUPS.items()}
        unit,existing=verify_baseline(selected)
        if not selected:block('no-complete-source-group')
        fd=idle_lock(runner);assert_idle(runner,existing)
        if not apply:
            report.update(status='validated',serviceReady=True)
            return report
        admin_fd=administrative_lock()
        protected_directory(BACKUP,0o700,create=True)
        snapshot_observations=create_snapshot(selected,runner,owner,observations,report)
        report['snapshotVerified']=True
        selected=sorted(snapshot_observations)
        report['selectedAssets']=selected;CURRENT_SELECTION=selected
        if existing:
            verify_mounts(int(properties()['MainPID']),selected,snapshot_observations)
            report.update(status='already-applied',applied=True,serviceReady=True,readOnlyMountsVerified=True,effectiveMountAssets=selected)
            report['sources']={c:('metadata-view-granted' if c=='FI' else 'view-granted') if v=='validated' else v for c,v in report['sources'].items()}
            return report
        protected_directory(BACKUP,0o700,create=True)
        ensure_file(BACKUP/'original.service',unit,0o600)
        ensure_file(BACKUP/'selection.json',json.dumps(selected,separators=(',',':')).encode(),0o600)
        # Recheck selected paths immediately before changing only this service's view.
        for key in selected:
            state,s=source_check(key,runner,owner)
            if state!='validated' or signature(s)!=signature(observations[key]):block('selected-source-changed')
        assert_idle(runner,existing)
        created_drop_dir=not DROP_DIR.exists()
        protected_directory(DROP_DIR,create=True)
        ensure_file(DROP_IN,dropin_bytes(selected));added=True
        command(['/usr/bin/systemd-analyze','verify',str(UNIT)])
        assert_idle(runner,existing)
        # Queue must be held quiet by the operator. The dispatcher lock is held
        # throughout; the exact service cgroup was checked immediately above.
        command(['/usr/bin/systemctl','stop',SERVICE]);stopped=True
        command(['/usr/bin/systemctl','daemon-reload'])
        command(['/usr/bin/systemctl','start',SERVICE]);report['serviceRestarted']=True
        values=properties();verify_properties(values,selected)
        verify_mounts(int(values['MainPID']),selected,snapshot_observations)
        report.update(status='applied',applied=True,serviceReady=True,readOnlyMountsVerified=True,effectiveMountAssets=selected)
        report['sources']={c:('metadata-view-granted' if c=='FI' else 'view-granted') if v=='validated' else v for c,v in report['sources'].items()}
    except (Exception,KeyboardInterrupt) as exc:
        report['errorCode']=str(exc) if isinstance(exc,Blocked) else 'grant-failed'
        if added:
            report['rollbackAttempted']=True
            try:
                # Remove only bytes installed by this invocation. Never touch other drop-ins.
                if regular_bytes(DROP_IN,16384)!=dropin_bytes(CURRENT_SELECTION):block('rollback-drift')
                DROP_IN.unlink()
                if created_drop_dir:
                    with os.scandir(DROP_DIR) as entries:empty=next(entries,None) is None
                    if empty:DROP_DIR.rmdir()
                if stopped:command(['/usr/bin/systemctl','stop',SERVICE])
                command(['/usr/bin/systemctl','daemon-reload'])
                if stopped:
                    command(['/usr/bin/systemctl','start',SERVICE]);report['serviceRestarted']=True
                verify_properties(properties(),None)
                report['rollbackRestored']=True;report['serviceReady']=True
            except Exception:report['rollbackRestored']=False
    finally:
        if fd is not None:os.close(fd)
        if admin_fd is not None:os.close(admin_fd)
    return report


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--apply',action='store_true')
    args=parser.parse_args()
    result=run(args.apply)
    body=json.dumps(result,sort_keys=True,separators=(',',':'))
    if len(body.encode())>16384:
        print(json.dumps({'schemaVersion':'offmenu-selected-data-grant/1','reportKind':'dataset-view-grant','grantVersion':1,'status':'blocked','errorCode':'report-limit-exceeded'}))
        return 2
    print(body)
    return 0 if result['status'] in {'validated','applied','already-applied'} else 2


if __name__=='__main__':sys.exit(main())
