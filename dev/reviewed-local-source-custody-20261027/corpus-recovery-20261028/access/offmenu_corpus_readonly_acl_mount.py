#!/usr/bin/python3 -I
# Approved exact-scope readonly ACL and mount update.
LAUNCHER_TEMPLATE = '#!/usr/bin/python3 -I\n"""DRAFT login shell. Install root-owned only after host review/tests.\nNo host command text is evaluated. SSH_ORIGINAL_COMMAND runs only in bwrap.\nThreat model: remote UID 985 is untrusted; host owner UID 1000 is trusted.\n"""\nimport json\nimport os\nimport resource\nimport signal\nimport stat\nimport subprocess\nimport sys\n\nCONFIG = \'/var/lib/offmenu-wm/launcher.json\'\nPROJECT = \'/home/user/src/offmenu\'\nUID, GID = 985, 977\nMARKER = \'offmenu-wm-sandbox-v1\'\n\n\ndef fail():\n    print(\'OffMenu SSH request refused; configuration or invocation check failed.\', file=sys.stderr)\n    raise SystemExit(126)\n\n\ndef root_file(path):\n    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC)\n    s = os.fstat(fd)\n    if not stat.S_ISREG(s.st_mode) or s.st_uid != 0 or s.st_mode & 0o022 or s.st_nlink != 1:\n        os.close(fd)\n        fail()\n    return fd\n\n\ndef validate_project(expected):\n    # No symlink components. Root/ancestors cannot be modified by remote UID.\n    # A trusted owner changing the checkout concurrently is outside threat model.\n    fd = os.open(\'/\', os.O_PATH | os.O_DIRECTORY | os.O_CLOEXEC)\n    walked = \'\'\n    try:\n        for part in PROJECT.strip(\'/\').split(\'/\'):\n            walked += \'/\' + part\n            nxt = os.open(part, os.O_PATH | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC,\n                          dir_fd=fd)\n            os.close(fd)\n            fd = nxt\n            if walked != PROJECT and os.access(walked, os.W_OK, effective_ids=True):\n                fail()\n        s = os.fstat(fd)\n        if (s.st_dev, s.st_ino, s.st_uid) != (expected[\'dev\'], expected[\'ino\'], 1000):\n            fail()\n    finally:\n        os.close(fd)\n\n\nCORPUS_MOUNTS = __CORPUS_MOUNTS__\n\ndef open_corpus_mounts():\n    # Root-installed exact path/inode allowlist. Remote request cannot supply mounts.\n    fds = []\n    try:\n        with open(\'/proc/self/mountinfo\') as f:\n            mounted = [line.split()[4] for line in f]\n        for item in CORPUS_MOUNTS:\n            # Fixed approved source paths contain no mountinfo escape characters.\n            if any(mp == item[\'source\'] or mp.startswith(item[\'source\'] + \'/\') for mp in mounted):\n                fail()\n            fd = os.open(\'/\', os.O_PATH | os.O_DIRECTORY | os.O_CLOEXEC)\n            walked = \'\'\n            try:\n                parts = item[\'source\'].strip(\'/\').split(\'/\')\n                for i, part in enumerate(parts):\n                    walked += \'/\' + part\n                    flags = os.O_PATH | os.O_NOFOLLOW | os.O_CLOEXEC\n                    if i < len(parts) - 1 or item[\'kind\'] == \'directory\':\n                        flags |= os.O_DIRECTORY\n                    nxt = os.open(part, flags, dir_fd=fd)\n                    os.close(fd)\n                    fd = nxt\n                    st = os.fstat(fd)\n                    if stat.S_ISLNK(st.st_mode) or os.access(walked, os.W_OK, effective_ids=True):\n                        fail()\n                st = os.fstat(fd)\n                if (st.st_dev, st.st_ino, stat.S_IFMT(st.st_mode)) != tuple(item[\'identity\']):\n                    fail()\n                if not os.access(item[\'source\'], os.R_OK | (os.X_OK if item[\'kind\'] == \'directory\' else 0), effective_ids=True):\n                    fail()\n                fds.append((fd, item[\'destination\']))\n                fd = None\n            finally:\n                if fd is not None:\n                    os.close(fd)\n        return fds\n    except BaseException:\n        for fd, _ in fds:\n            os.close(fd)\n        raise\n\n\ndef main():\n    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))\n    os.umask(0o007)\n    if (os.getuid(), os.geteuid(), os.getgid(), os.getegid()) != (UID, UID, GID, GID):\n        fail()\n    if set(os.getgroups()) - {GID} or sys.argv[1:] != [\'-c\', MARKER]:\n        fail()\n    if os.environ.get(\'SSH_ORIGINAL_COMMAND\', \'\') != \'offmenu-exec-v1\':\n        fail()\n    # Client must close stdin after one bounded JSON request. Do not echo payload.\n    def timed_out(signum, frame):\n        raise TimeoutError(\'protocol deadline\')\n    signal.signal(signal.SIGALRM, timed_out)\n    signal.alarm(15)\n    raw = sys.stdin.buffer.read(65537)\n    if len(raw) > 65536:\n        fail()\n    request = json.loads(raw)\n    signal.alarm(0)\n    if not isinstance(request, dict) or set(request) != {\'command\'}:\n        fail()\n    command = request[\'command\']\n    if not isinstance(command, str) or not command or \'\\x00\' in command:\n        fail()\n    with os.fdopen(root_file(CONFIG), \'r\') as f:\n        config = json.load(f)\n    if config.get(\'enabled\') is not True:\n        fail()\n    validate_project(config[\'project\'])\n    # Runtime bindings are fixed, never taken from request or environment.\n    args = [\'/bin/bwrap\', \'--unshare-all\', \'--unshare-user\', \'--die-with-parent\',\n            \'--new-session\', \'--clearenv\', \'--cap-drop\', \'ALL\']\n    for p in (\'/usr\', \'/bin\', \'/lib\', \'/lib64\'):\n        if os.path.isdir(p):\n            args += [\'--ro-bind\', p, p]\n    for name in (\'passwd\', \'group\', \'nsswitch.conf\'):\n        p = \'/var/lib/offmenu-wm/runtime/\' + name\n        os.close(root_file(p))\n        args += [\'--ro-bind\', p, \'/etc/\' + name]\n    corpus_fds = open_corpus_mounts()\n    # No host-rooted descriptors may enter bwrap or its PID-1 supervisor.\n    for fd, _ in corpus_fds:\n        os.close(fd)\n    # Components were checked non-writable by UID985. As with PROJECT, the\n    # trusted host owner changing paths concurrently is outside this threat model.\n    for item in CORPUS_MOUNTS:\n        args += [\'--ro-bind\', item[\'source\'], item[\'destination\']]\n    args += [\'--proc\', \'/proc\', \'--dev\', \'/dev\', \'--tmpfs\', \'/tmp\', \'--dir\', \'/tmp/home\',\n             \'--bind\', PROJECT, \'/offmenu\', \'--chdir\', \'/offmenu\',\n             \'--setenv\', \'PATH\', \'/usr/bin:/bin\', \'--setenv\', \'HOME\', \'/tmp/home\',\n             \'--setenv\', \'USER\', \'offmenu-wm\', \'--setenv\', \'LOGNAME\', \'offmenu-wm\',\n             \'--setenv\', \'LANG\', \'C\', \'--setenv\', \'GIT_CONFIG_NOSYSTEM\', \'1\',\n             \'--setenv\', \'GIT_CONFIG_COUNT\', \'1\',\n             \'--setenv\', \'GIT_CONFIG_KEY_0\', \'safe.directory\',\n             \'--setenv\', \'GIT_CONFIG_VALUE_0\', \'/offmenu\',\n             \'--\', \'/bin/bash\', \'--noprofile\', \'--norc\', \'-c\', command]\n    # Before launching bwrap, clear loader/shell/Python/Git environment as well.\n    # sshd AcceptEnv itself must disallow loader/Python variables BEFORE this interpreter starts.\n    result = subprocess.run(args, env={\'PATH\': \'/usr/bin:/bin\', \'LANG\': \'C\'},\n                            cwd=\'/\', stdin=subprocess.DEVNULL, close_fds=True, check=False)\n    return result.returncode if result.returncode >= 0 else 128 - result.returncode\n\n\nif __name__ == \'__main__\':\n    try:\n        sys.exit(main())\n    except (OSError, ValueError, KeyError, TypeError, RecursionError, TimeoutError):\n        fail()\n'
ACL_SOURCE = '"""Pure POSIX ACL planner. No filesystem reads or writes.\nInput must be numeric getfacl output for ONE inode; installer owns collision,\nno-follow traversal, inode pinning, backup, application and rollback.\n"""\nimport re\n\nWORKER = 985\nOWNER = 1000\nclass ACLPlanError(ValueError):\n    pass\n\ndef bits(s):\n    if not re.fullmatch(r\'[r-][w-][x-]\', s):\n        raise ACLPlanError(\'Unsupported permissions\')\n    return (4 if s[0] == \'r\' else 0) | (2 if s[1] == \'w\' else 0) | (1 if s[2] == \'x\' else 0)\n\ndef perms(n):\n    return \'\'.join(c if n & b else \'-\' for b, c in ((4, \'r\'), (2, \'w\'), (1, \'x\')))\n\ndef validate(a):\n    if not all(k in a for k in [(\'user\', \'\'), (\'group\', \'\'), (\'other\', \'\')]):\n        raise ACLPlanError(\'Missing base ACL\')\n    named = any(q for _, q in a)\n    if named and (\'mask\', \'\') not in a:\n        raise ACLPlanError(\'Named entries require mask\')\n\ndef parse(text):\n    scopes = [{}, {}]\n    for line in text.splitlines():\n        line = line.split(\'#\', 1)[0].strip()\n        if not line:\n            continue\n        d = line.startswith(\'default:\')\n        if d:\n            line = line[len(\'default:\'):]\n        fields = line.split(\':\')\n        if len(fields) != 3:\n            raise ACLPlanError(\'Unsupported ACL grammar\')\n        kind, qualifier, rights = fields\n        if kind not in (\'user\', \'group\', \'mask\', \'other\'):\n            raise ACLPlanError(\'Unsupported ACL entry\')\n        if qualifier and (kind not in (\'user\', \'group\') or not re.fullmatch(r\'0|[1-9][0-9]*\', qualifier)):\n            raise ACLPlanError(\'Numeric IDs required\')\n        key = kind, qualifier\n        if key in scopes[d]:\n            raise ACLPlanError(\'Duplicate ACL entry\')\n        scopes[d][key] = bits(rights)\n    validate(scopes[0])\n    if scopes[1]:\n        validate(scopes[1])\n    return scopes\n\ndef effective(a, key):\n    value = a[key]\n    if key[0] == \'group\' or (key[0] == \'user\' and key[1]):\n        return value & a.get((\'mask\', \'\'), 7)\n    return value\n\ndef normalize(a):\n    return {k: effective(a, k) for k in a if k != (\'mask\', \'\')}\n\ndef finish(a):\n    result = dict(a)\n    mask = 0\n    for (kind, qualifier), value in a.items():\n        if kind == \'group\' or (kind == \'user\' and qualifier):\n            mask |= value\n    result[\'mask\', \'\'] = mask\n    return result\n\ndef verify_preserved(before, after, exceptions=()):\n    """Verify each old entry\'s effective rights; mask itself isn\'t a principal."""\n    for key in before:\n        if key == (\'mask\', \'\') or key in exceptions:\n            continue\n        if key not in after or effective(before, key) != effective(after, key):\n            raise ACLPlanError(\'Existing effective permission changed\')\n    return True\n\ndef render(scopes):\n    def order(item):\n        (kind, q), _ = item\n        return ({\'user\': 0, \'group\': 1, \'mask\': 2, \'other\': 3}[kind], bool(q), int(q or 0))\n    lines = []\n    for default, scope in enumerate(scopes):\n        for (kind, qualifier), value in sorted(scope.items(), key=order):\n            lines.append((\'default:\' if default else \'\') + f\'{kind}:{qualifier}:{perms(value)}\')\n    return \'\\n\'.join(lines) + \'\\n\'\n\ndef readonly_plan(text, *, owner, group, is_dir):\n    access, default = parse(text)\n    if owner == WORKER:\n        raise ACLPlanError(\'Worker-owned source inode cannot be confined by named ACL\')\n    current = effective_for_identity(access, owner=owner, group=group)\n    if current & 2:\n        raise ACLPlanError(\'Source inode already writable by worker; not changed\')\n    wanted = 5 if is_dir else 4\n    if current & wanted == wanted:\n        return render([access, default]), False\n    result = normalize(access)\n    worker_key = (\'user\', str(WORKER))\n    result[worker_key] = current | wanted\n    result = finish(result)\n    verify_preserved(access, result, exceptions=(worker_key,))\n    if effective_for_identity(result, owner=owner, group=group) & 2:\n        raise ACLPlanError(\'Write bit would be granted\')\n    if effective_for_identity(result, owner=owner, group=group) & wanted != wanted:\n        raise ACLPlanError(\'Required readonly rights not achieved\')\n    return render([result, default]), True\n\n"""Pure POSIX ACL evaluation for preserving externally shared regular inodes.\nNo filesystem operations; caller verifies inode identity, nlink and ACL stability.\n"""\n\ndef effective_for_identity(access, *, owner, group, uid=985, gids=(977,)):\n    if uid == owner:\n        return access[\'user\', \'\']\n    mask=access.get((\'mask\',\'\'),7)\n    named=(\'user\',str(uid))\n    if named in access:\n        return access[named] & mask\n    matching=False\n    granted=0\n    if group in gids:\n        matching=True\n        granted |= access[\'group\',\'\']\n    for gid in gids:\n        key=(\'group\',str(gid))\n        if key in access:\n            matching=True\n            granted |= access[key]\n    # A matching group with no permissions does NOT fall through to other.\n    return granted & mask if matching else access[\'other\',\'\']\n\n'
ACL_IO_SOURCE = '"""Linux libacl inode-pinned metadata I/O. Does not read file contents."""\nimport ctypes as C\nimport os\nimport stat\n\nclass ACLIOError(RuntimeError):\n    pass\n\nclass ACLIO:\n    DEFAULT = 0x4000\n    def __init__(self):\n        self.lib = C.CDLL(\'libacl.so.1\', use_errno=True)\n        signatures = {\n            \'acl_get_fd\': ([C.c_int], C.c_void_p),\n            \'acl_get_file\': ([C.c_char_p, C.c_int], C.c_void_p),\n            \'acl_to_any_text\': ([C.c_void_p, C.c_char_p, C.c_char, C.c_int], C.c_void_p),\n            \'acl_free\': ([C.c_void_p], C.c_int),\n            \'acl_from_text\': ([C.c_char_p], C.c_void_p),\n            \'acl_valid\': ([C.c_void_p], C.c_int),\n            \'acl_set_fd\': ([C.c_int, C.c_void_p], C.c_int),\n            \'acl_set_file\': ([C.c_char_p, C.c_int, C.c_void_p], C.c_int),\n            \'acl_delete_def_file\': ([C.c_char_p], C.c_int),\n        }\n        for name, (args, ret) in signatures.items():\n            f = getattr(self.lib, name)\n            f.argtypes, f.restype = args, ret\n\n    def text(self, acl):\n        if not acl:\n            raise ACLIOError(\'ACL read failed\')\n        p = None\n        try:\n            p = self.lib.acl_to_any_text(acl, None, b\'\\n\', 0x08)\n            if not p:\n                raise ACLIOError(\'ACL serialization failed\')\n            text = C.string_at(p).decode(\'ascii\')\n            return text.rstrip(\'\\n\') + \'\\n\' if text else \'\'\n        finally:\n            if p:\n                self.lib.acl_free(p)\n            self.lib.acl_free(acl)\n\n    def get(self, fd, is_dir):\n        text = self.text(self.lib.acl_get_fd(fd))\n        if is_dir:\n            default = self.text(self.lib.acl_get_file(f\'/proc/self/fd/{fd}\'.encode(), self.DEFAULT))\n            text += \'\'.join(\'default:\' + line + \'\\n\' for line in default.splitlines())\n        return text\n\n    def _set(self, fd, text, default=False):\n        p = self.lib.acl_from_text(text.encode())\n        if not p:\n            raise ACLIOError(\'ACL parse failed\')\n        try:\n            if self.lib.acl_valid(p) != 0:\n                raise ACLIOError(\'ACL validation failed\')\n            if default:\n                r = self.lib.acl_set_file(f\'/proc/self/fd/{fd}\'.encode(), self.DEFAULT, p)\n            else:\n                r = self.lib.acl_set_fd(fd, p)\n            if r != 0:\n                raise ACLIOError(\'ACL write failed\')\n        finally:\n            self.lib.acl_free(p)\n\n    def put(self, fd, text, is_dir):\n        access, default = [], []\n        for line in text.splitlines():\n            if line.startswith(\'default:\'):\n                default.append(line[len(\'default:\'):])\n            else:\n                access.append(line)\n        # Caller has a durable before-record and marks inode touched BEFORE call.\n        # Two ACL types necessarily use separate kernel operations.\n        self._set(fd, \'\\n\'.join(access) + \'\\n\')\n        if default:\n            if not is_dir:\n                raise ACLIOError(\'Default ACL on nondirectory\')\n            self._set(fd, \'\\n\'.join(default) + \'\\n\', default=True)\n        elif is_dir and self.lib.acl_delete_def_file(f\'/proc/self/fd/{fd}\'.encode()) != 0:\n            raise ACLIOError(\'Default ACL removal failed\')\n\n\ndef open_inode(path, expected=None):\n    fd = os.open(path, os.O_RDONLY | os.O_NONBLOCK | os.O_NOFOLLOW | os.O_CLOEXEC)\n    s = os.fstat(fd)\n    if not (stat.S_ISDIR(s.st_mode) or stat.S_ISREG(s.st_mode)):\n        os.close(fd)\n        raise ACLIOError(\'Unsupported inode type\')\n    if expected is not None and (s.st_dev, s.st_ino) != tuple(expected):\n        os.close(fd)\n        raise ACLIOError(\'Inode changed\')\n    return fd, s\n'
ACLM = {}; exec(compile(ACL_SOURCE,"<readonly-acl>","exec"),ACLM)
ACLIO_MOD = {}; exec(compile(ACL_IO_SOURCE,"<acl-io>","exec"),ACLIO_MOD)
import argparse
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
ORIGINAL_SHA = 'e0a2f7eef285aa23ffebea5a777a531bf1ac4b53db88c1f8d1b88ffcb1eba339'
DIRECTORIES = (
 'common-data-reviewed-package-20261014',
 'common-reference-delivery-final-20261014',
 'common-national-semantic-final-20261014',
 'measurement-terminology-final-qualified-20261014',
 'recipe-expansion-final-qualified-20261014/common-graph',
 'historical-recipe-quality-final-corrected-20261014',
 'common-bulk-food-semantic-final-20261014',
 'common-places-semantic-final-20261014.partial',
)
FILES = ('common-ready-six-package-global-20261014.json', 'custody-positive-quiescence-20261014.json')
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
            mounts.append({'source': source, 'destination': DEST + name, 'kind':kind,
                           'identity': [st.st_dev, st.st_ino, stat.S_IFMT(st.st_mode)]})
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
    code = 'import os,stat\nCORPUS_MOUNTS=' + repr(mounts) + '\n'
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
for item in items:
    p=item['destination']; s=os.stat(p)
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
print(json.dumps({'mounts_verified':len(items),'read_only':True,'private_home_absent':True,'docker_socket_absent':True,'project_writable':True}))
'''.replace('ITEMS', repr(mounts))
    command = '/usr/bin/python3 -I -c ' + shlex.quote(code)
    env = dict(ENV, SSH_ORIGINAL_COMMAND='offmenu-exec-v1')
    result = subprocess.run(['/usr/sbin/runuser','-u','offmenu-wm','--',SHELL,'-c','offmenu-wm-sandbox-v1'],
        input=json.dumps({'command':command}).encode(), stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        timeout=60, env=env, close_fds=True)
    if result.returncode: raise Stop('New launcher sandbox smoke failed; details suppressed')
    parsed=json.loads(result.stdout)
    if parsed != {'mounts_verified':10,'read_only':True,'private_home_absent':True,'docker_socket_absent':True,'project_writable':True}:
        raise Stop('Sandbox smoke response did not match')
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

def main():
    parser=argparse.ArgumentParser(description='Grant exact approved UID985 readonly corpus ACLs and install read-only mounts.')
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
    if digest(old)!=ORIGINAL_SHA:raise Stop('Launcher differs from reviewed original; not changed')
    before_config=read_control(CONFIG);config=json.loads(before_config)
    if set(config)!={'enabled','project'} or config['enabled'] is not True or set(config['project'])!={'dev','ino'}:
        raise Stop('Launcher configuration differs; not changed')
    s=os.stat('/home/user/src/offmenu',follow_symlinks=False)
    if (s.st_dev,s.st_ino)!=(config['project']['dev'],config['project']['ino']):raise Stop('Project identity differs')
    acl=ACLIO_MOD['ACLIO']()
    mounts=collect_mounts();verify_ancestors(acl)
    items,shared=snapshot_acl_plan(acl)
    mounts_after=collect_mounts()
    if mounts_after!=mounts:raise Stop('Source-root identity changed during census')
    new=make_launcher(mounts)
    changes=sum(x['change'] for x in items)
    print(json.dumps({'preflight':'passed','apply_requested':args.apply,'inodes_checked':len(items),
                      'access_acl_changes':changes,'external_shared_inodes_untouched':shared,
                      'default_acl_changes':False,'owner_changes':False,'write_grants':False}),flush=True)
    if not args.apply:return
    backup=BASE+'/corpus-readonly-acl-backup-'+uuid.uuid4().hex
    os.mkdir(backup,0o700);fsync_dir(BASE)
    newfile(backup+'/original-launcher',old,0o600)
    newfile(backup+'/acl-plan.json',json.dumps({'schema':1,'items':items,'mounts':mounts},sort_keys=True).encode(),0o600)
    journal_path=backup+'/journal.jsonl'
    journal_fd=os.open(journal_path,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
    os.fsync(journal_fd);fsync_dir(backup)
    touched=[];launcher_attempted=False
    try:
        apply_acl_plan(acl,items,journal_fd,touched)
        verify_account_paths(mounts);verify_tree_access(items)
        if collect_mounts()!=mounts:raise Stop('Source roots/mounts changed before launcher installation')
        launcher_attempted=True
        atomic_replace(old,new)
        verified=smoke(mounts)
        if read_control(CONFIG)!=before_config or read_control(SHELL)!=new:
            raise Stop('Control files changed concurrently')
        sync_journal(journal_fd,{'installed':True,'launcher_sha256':digest(new),'access_acl_changes':changes})
        print(json.dumps({'installed':True,'backup':backup,'launcher_sha256':digest(new),
                          'read_only_directories':8,'read_only_receipts':2,'access_acl_changes':changes,
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
