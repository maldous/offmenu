import argparse
import ast
import fcntl
import hashlib
import json
import os
import pathlib
import pwd
import shlex
import stat
import subprocess
import sys
import uuid

BASE = '/var/lib/offmenu-wm'
SHELL = BASE + '/offmenu-wm-shell'
CONFIG = BASE + '/launcher.json'
DATA = '/home/user/src/offmenu-data/'
DEST = '/offmenu-corpus/'
UID, GID = 985, 977
ENV = {'PATH': '/usr/sbin:/usr/bin:/sbin:/bin', 'LANG': 'C'}
ORIGINAL_SHA = '93a8e8eeb65666d775caf45235d39d2d9695c33d25285948aeb4dff7be52b1c2'
EXISTING_DIRECTORIES = (
 'common-data-reviewed-package-20261014',
 'common-reference-delivery-final-20261014',
 'common-national-semantic-final-20261014',
 'measurement-terminology-final-qualified-20261014',
 'recipe-expansion-final-qualified-20261014/common-graph',
 'historical-recipe-quality-final-corrected-20261014',
 'common-bulk-food-semantic-final-20261014',
 'common-places-semantic-final-20261014.partial',
)
EXISTING_FILES = ('common-ready-six-package-global-20261014.json', 'custody-positive-quiescence-20261014.json')
DIRECTORIES = ('common-bulk-food-20261014', 'curated-expanded-country-search-20261013/blobs')
OPTIONAL_FILES = (
 'common-places-semantic-final-20261014.checkpoint.sqlite',
 'common-places-semantic-final-20261014.checkpoint.sqlite-journal',
 'common-places-semantic-final-20261014.checkpoint.sqlite-wal',
 'common-places-semantic-final-20261014.checkpoint.sqlite-shm',
 'common-places-semantic-final-20261014.alignment.lock',
 'common-bulk-food-semantic-final-20261014.repair.lock',
)
FILES = ()
class Stop(RuntimeError): pass

def digest(data): return hashlib.sha256(data).hexdigest()

def root_safe(path, regular=False):
    for part in reversed((pathlib.Path(path),) + tuple(pathlib.Path(path).parents)):
        st = os.lstat(part)
        if stat.S_ISLNK(st.st_mode) or st.st_uid != 0 or st.st_mode & 0o022:
            raise Stop('Root control path ownership or permissions differ; stopped')
    if regular and (not stat.S_ISREG(st.st_mode) or st.st_nlink != 1):
        raise Stop('Control file must be a singly linked regular file')

def read_control(path):
    root_safe(path, True)
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC)
    with os.fdopen(fd, 'rb') as f:
        data = f.read(131073)
    if len(data) > 131072: raise Stop('Control file exceeds bound')
    return data

def fsync_dir(path):
    fd = os.open(path, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try: os.fsync(fd)
    finally: os.close(fd)

def newfile(path, data, mode):
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, mode)
    with os.fdopen(fd, 'wb') as f:
        os.fchmod(f.fileno(), mode)
        f.write(data); f.flush(); os.fsync(f.fileno())
    fsync_dir(os.path.dirname(path))

def atomic_replace(expected, replacement):
    if read_control(SHELL) != expected: raise Stop('Launcher changed concurrently; not overwritten')
    temporary = BASE + '/.corpus-launcher-' + uuid.uuid4().hex
    newfile(temporary, replacement, 0o755)
    if read_control(SHELL) != expected:
        os.unlink(temporary)
        raise Stop('Launcher changed concurrently; not overwritten')
    os.replace(temporary, SHELL); fsync_dir(BASE)

def run_as_account(code, timeout=30):
    result = subprocess.run(['/usr/sbin/runuser', '-u', 'offmenu-wm', '--',
                             '/usr/bin/python3', '-I', '-c', code],
                            env=ENV, input=b'', stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                            timeout=timeout, close_fds=True)
    if result.returncode: raise Stop('Restricted-account access verification failed; inspect rollback result')
    return result.stdout

def collect_mounts():
    mounts = []
    missing = []
    for name in DIRECTORIES + FILES:
        source = DATA + name
        kind = 'directory' if name in DIRECTORIES else 'file'
        try:
            for part in reversed((pathlib.Path(source),) + tuple(pathlib.Path(source).parents)):
                st = os.lstat(part)
                if stat.S_ISLNK(st.st_mode): raise Stop('Allowlisted path has a symlink component: ' + name)
            wanted = stat.S_IFDIR if kind == 'directory' else stat.S_IFREG
            if stat.S_IFMT(st.st_mode) != wanted: raise Stop('Allowlisted object has unexpected type: ' + name)
            item={'source': source, 'destination': DEST + name, 'kind':kind,
                  'identity': [st.st_dev, st.st_ino, stat.S_IFMT(st.st_mode)]}
            if name in OPTIONAL_FILES:item['optional']=True
            mounts.append(item)
        except FileNotFoundError:
            missing.append(name)
    if missing:
        print(json.dumps({'missing_allowlisted_paths':missing, 'changed':False}))
        raise Stop('Historical paths absent; not created and no mounts installed')
    # Do not inherit unrelated nested bind mounts from the host.
    with open('/proc/self/mountinfo') as f:
        mounted = [line.split()[4].replace('\\040',' ').replace('\\011','\t').replace('\\134','\\') for line in f]
    for item in mounts:
        if any(mp == item['source'] or mp.startswith(item['source'] + '/') for mp in mounted):
            raise Stop('Allowlisted path is or contains a host mount; requires specific review')
    return mounts

def make_launcher(mounts):
    result = LAUNCHER_TEMPLATE.replace('__CORPUS_MOUNTS__', repr(mounts))
    if '__CORPUS_MOUNTS__' in result: raise Stop('Template substitution failed')
    compile(result, SHELL, 'exec')
    return result.encode()

def verify_account_paths(mounts):
    # Same fd-pinned path checks as the final launcher, run as restricted account.
    code = 'import os,stat\nOPTIONAL_CORPUS_NAMES='+repr(OPTIONAL_FILES)+'\nCORPUS_MOUNTS=' + repr(mounts) + '\n'
    helper = LAUNCHER_TEMPLATE.split('def open_corpus_mounts():',1)[1].split('\ndef main():',1)[0]
    code += 'def fail(): raise RuntimeError("path access refused")\ndef open_corpus_mounts():' + helper
    code += '\nfds=open_corpus_mounts()\nfor fd,_ in fds: os.close(fd)\n'
    run_as_account(code)

def smoke(mounts):
    # Read mount flags and object metadata only. Do not write probe files to corpus.
    code = '''import os,json,stat,socket,glob
items=ITEMS
mounts={}
for line in open('/proc/self/mountinfo'):
    a=line.split(); mounts[a[4]]=a[5].split(',')
omitted=[];checked=0
for item in items:
    p=item['destination']
    if item.get('optional') is True and not os.path.lexists(p):
        omitted.append(p);continue
    s=os.stat(p);checked+=1
    assert [s.st_dev,s.st_ino,stat.S_IFMT(s.st_mode)]==item['identity']
    assert 'ro' in mounts[p], 'corpus mount not read-only'
    assert os.statvfs(p).f_flag & os.ST_RDONLY
    assert all('ro' in flags for path, flags in mounts.items() if path == p or path.startswith(p+'/'))
    assert os.access(p,os.R_OK | (os.X_OK if item['kind']=='directory' else 0))
assert not os.path.exists('/home/user')
assert not os.path.exists('/run/docker.sock')
assert os.getcwd()=='/offmenu'
assert os.access('/offmenu',os.W_OK)
assert set(name for _,name in socket.if_nameindex()) <= {'lo'}
for fdpath in glob.glob('/proc/[0-9]*/fd/*'):
    try: target=os.readlink(fdpath)
    except (FileNotFoundError,ProcessLookupError): continue
    assert not target.startswith('/home/user/src/offmenu-data/'), 'host corpus descriptor leaked'
print(json.dumps({'mounts_verified':checked,'optional_mounts_omitted':omitted,'read_only':True,'private_home_absent':True,'docker_socket_absent':True,'project_writable':True}))
'''.replace('ITEMS', repr(mounts))
    command = '/usr/bin/python3 -I -c ' + shlex.quote(code)
    env = dict(ENV, SSH_ORIGINAL_COMMAND='offmenu-exec-v1')
    result = subprocess.run(['/usr/sbin/runuser','-u','offmenu-wm','--',SHELL,'-c','offmenu-wm-sandbox-v1'],
        input=json.dumps({'command':command}).encode(), stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        timeout=60, env=env, close_fds=True)
    if result.returncode: raise Stop('New launcher sandbox smoke failed; details suppressed')
    parsed=json.loads(result.stdout)
    expected_keys={'mounts_verified','optional_mounts_omitted','read_only','private_home_absent','docker_socket_absent','project_writable'}
    allowed_omitted={item['destination'] for item in mounts if item.get('optional') is True}
    if set(parsed)!=expected_keys or type(parsed['mounts_verified']) is not int or not isinstance(parsed['optional_mounts_omitted'],list):
        raise Stop('Sandbox smoke response did not match')
    omitted=parsed['optional_mounts_omitted']
    if len(set(omitted))!=len(omitted) or not set(omitted)<=allowed_omitted or parsed['mounts_verified']+len(omitted)!=len(mounts):
        raise Stop('Sandbox optional omission report invalid')
    if not all(parsed[k] is True for k in ('read_only','private_home_absent','docker_socket_absent','project_writable')):
        raise Stop('Sandbox confinement smoke failed')
    return parsed

def canonical(text): return ACLM['render'](ACLM['parse'](text))

def open_pinned(path, identity=None):
    fd=os.open('/',os.O_RDONLY|os.O_DIRECTORY|os.O_CLOEXEC)
    try:
        parts=[part for part in path.strip('/').split('/') if part]
        for index,part in enumerate(parts):
            flags=os.O_NOFOLLOW|os.O_CLOEXEC
            flags |= os.O_PATH|os.O_DIRECTORY if index<len(parts)-1 else os.O_RDONLY|os.O_NONBLOCK
            nxt=os.open(part,flags,dir_fd=fd);os.close(fd);fd=nxt
        s=os.fstat(fd)
        if not (stat.S_ISREG(s.st_mode) or stat.S_ISDIR(s.st_mode)):
            raise Stop('Special or symlink source object refused')
        if identity is not None and [s.st_dev,s.st_ino]!=identity:
            raise Stop('Source inode identity changed')
        result=fd;fd=None
        return result,s
    finally:
        if fd is not None:os.close(fd)

def verify_ancestors(acl):
    seen=set()
    for relative in DIRECTORIES+FILES:
        source=DATA+relative
        for ancestor in pathlib.Path(source).parents:
            path=str(ancestor)
            if path in seen:continue
            seen.add(path)
            fd,s=open_pinned(path)
            try:
                access,_=ACLM['parse'](acl.get(fd,True))
                rights=ACLM['effective_for_identity'](access,owner=s.st_uid,group=s.st_gid)
                if rights & 2 or not rights & 1:
                    raise Stop('Outside-scope ancestor access unsafe or traversal missing; not changed: '+path)
            finally:os.close(fd)

def verify_aliases(item, *, ctime=False):
    for path in item['aliases']:
        fd,s=open_pinned(path,item['inode'])
        os.close(fd)
        if (s.st_uid,s.st_gid,s.st_nlink,stat.S_IFMT(s.st_mode)) != (item['owner'],item['group'],item['nlink'],item['type']):
            raise Stop('Source ownership/type/link topology changed; not overwritten')
        if ctime and s.st_ctime_ns!=item['ctime_ns']:
            raise Stop('Source changed after metadata snapshot; not overwritten')

def snapshot_acl_plan(acl):
    items=[];index={}
    def take(path):
        s=os.lstat(path)
        if not (stat.S_ISDIR(s.st_mode) or stat.S_ISREG(s.st_mode)):
            raise Stop('Symlink or special object in approved subtree; stopped: '+path)
        identity=(s.st_dev,s.st_ino)
        if identity in index:
            if path not in index[identity]['aliases']:index[identity]['aliases'].append(path)
            return
        fd,s=open_pinned(path,list(identity))
        try:
            is_dir=stat.S_ISDIR(s.st_mode)
            before=canonical(acl.get(fd,is_dir))
            try:
                after,change=ACLM['readonly_plan'](before,owner=s.st_uid,group=s.st_gid,is_dir=is_dir)
            except ACLM['ACLPlanError'] as error:
                raise Stop(str(error)+': '+path) from None
            item={'path':path,'aliases':[path],'inode':list(identity),'owner':s.st_uid,'group':s.st_gid,
                  'nlink':s.st_nlink,'type':stat.S_IFMT(s.st_mode),'mode':stat.S_IMODE(s.st_mode),
                  'ctime_ns':s.st_ctime_ns,'dir':is_dir,'before':before,'after':after,'change':change}
            index[identity]=item;items.append(item)
        finally:os.close(fd)
        if len(items)%10000==0:print(json.dumps({'inventory_inodes':len(items),'changes_started':False}),flush=True)
    def traversal_error(e):raise Stop('Approved-tree metadata traversal failed; no partial plan accepted')
    for relative in DIRECTORIES:
        root=DATA+relative
        for directory,dirs,files in os.walk(root,followlinks=False,onerror=traversal_error):
            take(directory)
            for name in dirs:
                if stat.S_ISLNK(os.lstat(os.path.join(directory,name)).st_mode):
                    raise Stop('Symlink directory in approved subtree; stopped')
            for name in files:take(os.path.join(directory,name))
    for relative in FILES:take(DATA+relative)
    shared=0
    for item in items:
        verify_aliases(item,ctime=True)
        if not item['dir']:
            if item['nlink']<len(item['aliases']):raise Stop('Hardlink topology changed during census')
            external=item['nlink']>len(item['aliases'])
            if external and item['change']:
                raise Stop('Unreadable inode has links outside approved scope; no ACL changed: '+item['path'])
            if external:shared+=1
        fd,_=open_pinned(item['path'],item['inode'])
        try:
            if canonical(acl.get(fd,item['dir']))!=item['before']:
                raise Stop('ACL changed during inventory')
        finally:os.close(fd)
    return items,shared

def set_access_only(acl,fd,text):
    # Never call ACLIO.put(): it writes default ACLs too. Only access is changed.
    access,_=ACLM['parse'](text)
    acl._set(fd,ACLM['render']([access,{}]))

def sync_journal(fd,record):
    data=(json.dumps(record,sort_keys=True)+'\n').encode()
    while data:
        written=os.write(fd,data)
        if written<=0:raise Stop('Journal write failed')
        data=data[written:]
    os.fsync(fd)

def apply_acl_plan(acl,items,journal_fd,touched):
    for i,item in enumerate(items):
        verify_aliases(item,ctime=True)
        fd,s=open_pinned(item['path'],item['inode'])
        try:
            if canonical(acl.get(fd,item['dir']))!=item['before']:
                raise Stop('ACL changed since snapshot; not overwritten')
            if not item['change']:continue
            sync_journal(journal_fd,{'intent':'grant_readonly','plan_index':i,'inode':item['inode']})
            touched.append(item)  # Before syscall: outcome may be uncertain on error.
            set_access_only(acl,fd,item['after'])
            os.fsync(fd)
            if canonical(acl.get(fd,item['dir']))!=item['after']:
                raise Stop('Access ACL or unchanged default did not verify')
            current=os.fstat(fd)
            if current.st_mode & 0o7000 != item['mode'] & 0o7000:
                raise Stop('Special permission bits changed unexpectedly')
            sync_journal(journal_fd,{'verified':'grant_readonly','plan_index':i,'inode':item['inode']})
        finally:os.close(fd)

def rollback_acls(acl,touched,journal_fd):
    failures=[]
    for item in reversed(touched):
        try:
            verify_aliases(item)
            fd,s=open_pinned(item['path'],item['inode'])
            try:
                current=canonical(acl.get(fd,item['dir']))
                if current not in (item['before'],item['after']):
                    raise Stop('Concurrent ACL/default change; automatic restore refused')
                if current==item['after']:
                    set_access_only(acl,fd,item['before']);os.fsync(fd)
                if canonical(acl.get(fd,item['dir']))!=item['before'] or stat.S_IMODE(os.fstat(fd).st_mode)!=item['mode']:
                    raise Stop('ACL rollback did not verify')
            finally:os.close(fd)
            try:sync_journal(journal_fd,{'rollback_verified':True,'inode':item['inode']})
            except OSError:pass  # Restore continues even if journal storage failed.
        except Exception as e:
            failures.append({'path':item['path'],'reason':str(e) if isinstance(e,Stop) else type(e).__name__})
    return failures

def verify_tree_access(items):
    paths=[DATA+x for x in DIRECTORIES]
    files=[DATA+x for x in FILES]
    code='''import os,stat,json
roots=ROOTS
receipts=RECEIPTS
count=0
def check(p):
    s=os.lstat(p)
    assert stat.S_ISDIR(s.st_mode) or stat.S_ISREG(s.st_mode)
    assert os.access(p,os.R_OK|(os.X_OK if stat.S_ISDIR(s.st_mode) else 0),effective_ids=True)
    assert not os.access(p,os.W_OK,effective_ids=True)
def err(e):raise RuntimeError('traversal failed')
for root in roots:
    for d,dirs,files in os.walk(root,followlinks=False,onerror=err):
        check(d);count+=1
        for n in dirs:assert not os.path.islink(os.path.join(d,n))
        for n in files:check(os.path.join(d,n));count+=1
for p in receipts:check(p);count+=1
print(json.dumps({'read_only_access_paths':count}))
'''.replace('ROOTS',repr(paths)).replace('RECEIPTS',repr(files))
    result=run_as_account(code,timeout=600)
    if json.loads(result)!= {'read_only_access_paths':sum(len(x['aliases']) for x in items)}:
        raise Stop('Post-grant access inventory differs; concurrent tree changes require review')


def parse_existing_mounts(old):
    if digest(old)!=ORIGINAL_SHA:
        raise Stop('Installed launcher does not match approved current hash')
    nodes=[node for node in ast.parse(old.decode()).body if isinstance(node,ast.Assign)
           and any(isinstance(target,ast.Name) and target.id=='CORPUS_MOUNTS' for target in node.targets)]
    if len(nodes)!=1:raise Stop('Installed mount literal not unique')
    mounts=ast.literal_eval(nodes[0].value)
    if not isinstance(mounts,list) or len(mounts)!=10:
        raise Stop('Installed mount count differs from approved existing ten')
    for item,name in zip(mounts,EXISTING_DIRECTORIES+EXISTING_FILES):
        kind='directory' if name in EXISTING_DIRECTORIES else 'file'
        if not isinstance(item,dict) or set(item)!={'source','destination','kind','identity'}:
            raise Stop('Installed mount schema differs')
        if (item['source'],item['destination'],item['kind'])!=(DATA+name,DEST+name,kind):
            raise Stop('Installed mount path/order differs from original approved scope')
        identity=item['identity']
        if not isinstance(identity,list) or len(identity)!=3 or any(type(x) is not int for x in identity):
            raise Stop('Installed mount identity is invalid')
        if identity[0]<0 or identity[1]<=0 or identity[2]!=(stat.S_IFDIR if kind=='directory' else stat.S_IFREG):
            raise Stop('Installed mount identity type is invalid')
    # Literal parsing is not code execution. Reconstruct the entire reviewed
    # template to reject any unrelated launcher difference, even with valid pins.
    if ORIGINAL_LAUNCHER_TEMPLATE.replace('__CORPUS_MOUNTS__',repr(mounts)).encode()!=old:
        raise Stop('Installed launcher differs from reviewed template')
    return mounts

def select_optional_files():
    present=[];absent=[]
    for name in OPTIONAL_FILES:
        try:os.lstat(DATA+name)
        except FileNotFoundError:absent.append(name)
        else:present.append(name)
    return tuple(present),tuple(absent)

def main():
    global FILES
    parser=argparse.ArgumentParser(description='Add two approved input directories and existing optional files without changing original corpus mounts.')
    parser.add_argument('--apply',action='store_true',help='Apply after complete metadata preflight; default plan only')
    args=parser.parse_args();os.umask(0o077)
    if os.getuid()!=0 or os.geteuid()!=0:raise Stop('Run with sudo /usr/bin/python3 -I')
    root_safe(BASE)
    lockfd=os.open(BASE,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW)
    fcntl.flock(lockfd,fcntl.LOCK_EX|fcntl.LOCK_NB)
    account=pwd.getpwnam('offmenu-wm')
    if (account.pw_uid,account.pw_gid,account.pw_dir,account.pw_shell)!=(UID,GID,BASE,SHELL) or set(os.getgrouplist(account.pw_name,GID))!={GID}:
        raise Stop('Existing restricted account differs; not changed')
    old=read_control(SHELL)
    existing_mounts=parse_existing_mounts(old)
    before_config=read_control(CONFIG);config=json.loads(before_config)
    if set(config)!={'enabled','project'} or config['enabled'] is not True or set(config['project'])!={'dev','ino'}:
        raise Stop('Launcher configuration differs; not changed')
    s=os.stat('/home/user/src/offmenu',follow_symlinks=False)
    if (s.st_dev,s.st_ino)!=(config['project']['dev'],config['project']['ino']):raise Stop('Project identity differs')
    acl=ACLIO_MOD['ACLIO']()
    FILES,absent_optional=select_optional_files()
    added_mounts=collect_mounts();verify_ancestors(acl)
    mounts=existing_mounts+added_mounts
    items,shared=snapshot_acl_plan(acl)
    mounts_after=collect_mounts()
    if mounts_after!=added_mounts:raise Stop('Source-root identity changed during census')
    new=make_launcher(mounts)
    changes=sum(x['change'] for x in items)
    print(json.dumps({'preflight':'passed','apply_requested':args.apply,'inodes_checked':len(items),
                      'access_acl_changes':changes,'external_shared_inodes_untouched':shared,
                      'default_acl_changes':False,'owner_changes':False,'write_grants':False,
                      'existing_mounts_preserved':10,'new_required_directories':2,
                      'optional_files_present':list(FILES),'optional_files_absent_skipped':list(absent_optional)}),flush=True)
    if not args.apply:return
    backup=BASE+'/input-readonly-acl-backup-'+uuid.uuid4().hex
    os.mkdir(backup,0o700);fsync_dir(BASE)
    newfile(backup+'/original-launcher',old,0o600)
    newfile(backup+'/acl-plan.json',json.dumps({'schema':1,'items':items,'mounts':mounts,'existing_mounts':existing_mounts,'absent_optional_files':absent_optional},sort_keys=True).encode(),0o600)
    journal_path=backup+'/journal.jsonl'
    journal_fd=os.open(journal_path,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
    os.fsync(journal_fd);fsync_dir(backup)
    touched=[];launcher_attempted=False
    try:
        apply_acl_plan(acl,items,journal_fd,touched)
        verify_account_paths(mounts);verify_tree_access(items)
        if collect_mounts()!=added_mounts:raise Stop('Source roots/mounts changed before launcher installation')
        launcher_attempted=True
        atomic_replace(old,new)
        verified=smoke(mounts)
        if read_control(CONFIG)!=before_config or read_control(SHELL)!=new:
            raise Stop('Control files changed concurrently')
        sync_journal(journal_fd,{'installed':True,'launcher_sha256':digest(new),'access_acl_changes':changes})
        print(json.dumps({'installed':True,'backup':backup,'launcher_sha256':digest(new),
                          'existing_mounts_preserved':10,'new_read_only_directories':2,
                          'new_optional_files_pinned':list(FILES),
                          'new_optional_files_mounted_at_smoke':[name for name in FILES if DEST+name not in verified['optional_mounts_omitted']],
                          'optional_files_absent_skipped':list(absent_optional),
                          'access_acl_changes':changes,
                          'defaults_unchanged':True,'external_shared_inodes_untouched':shared,
                          'verification':verified,'mount_root':DEST.rstrip('/'),
                          'windmill_worker_verification_pending':True}),flush=True)
    except BaseException as error:
        launcher_restored=True
        if launcher_attempted:
            try:
                current=read_control(SHELL)
                if current==new:atomic_replace(new,old)
                elif current!=old:raise Stop('Concurrent launcher change; rollback refused')
                if read_control(SHELL)!=old:raise Stop('Launcher rollback did not verify')
            except Exception:launcher_restored=False
        failures=rollback_acls(acl,touched,journal_fd)
        print(json.dumps({'installed':False,'launcher_restored':launcher_restored,
                          'acl_rollback_verified':not failures,'rollback_failures':failures,
                          'backup':backup,'reason':str(error) if isinstance(error,Stop) else type(error).__name__}),flush=True)
        raise Stop('Update stopped; see verified rollback status and retained backup') from None
    finally:
        os.close(journal_fd);os.close(lockfd)

if __name__=='__main__':
    try:main()
    except (Stop,OSError,ValueError,KeyError,TypeError,subprocess.TimeoutExpired,ACLIO_MOD['ACLIOError']) as exc:
        print('STOP: '+(str(exc) if isinstance(exc,Stop) else type(exc).__name__+' during verification; details suppressed'),file=sys.stderr)
        sys.exit(1)
