"""Offline producer for stokowski_adapter's protected-current-owner-v1 input.

No CLI, service operation, credential handling, privilege transition or rollback
executor is provided. A separately reviewed owner imports install(), supplying
the independently frozen prepare() digest. Never run a workspace copy as root.
The private receipt is a permanent no-replay fence, including after failure.
Rollback is an owner reconciliation decision; this module never removes targets.
"""
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import stat
import subprocess
import tempfile
import zlib
from uuid import UUID


SOURCE = Path('/opt/offmenu-stokowski-current/source')
VENV = Path('/opt/offmenu-stokowski-current/venv')
CONFIG = Path('/etc/offmenu-stokowski-current')
RECEIPT = Path('/var/lib/offmenu-publisher/protected-current-install.json')
MAX_FILE = 64 * 1024 * 1024
MAX_TOTAL = 1024 * 1024 * 1024
MAX_FILES = 50000
SCHEMA = 'protected-current-install-v1'
SYSTEM_PYTHON_HOME_ALIASES = {Path('/bin'): (Path('/usr/bin'), 'usr/bin')}
# Preserve these accepted archival evidence blobs in their original repository;
# the installed coordinator needs their tree references, never their log bodies.
EXCLUDED_ARCHIVAL_EVIDENCE = {
    'archive/migrations/migration-checks.log': 'b191d6ec4fe799cd51691a54c3e7409eb8ef0391',
    'archive/migrations/original-resume-tests.log': '717ae781008e4f1dc8563e48ea9285d69df923c3',
    'docs/reviews/worker16-04-queue-compatibility/results.log': 'ad1f9dc7b2503f5e9c3f9a9f7ce378c820137c7f',
}
REQUIRED = {'version', 'owner', 'runtime_root', 'catalog', 'source_head',
            'source_sha256', 'workflow_sha256', 'policy_sha256', 'installation_sha256'}
OPTIONAL = {'qualified_successor', 'project_route', 'completed_native_validations',
            'normal_intake', 'native_review_policies', 'native_review_template'}
CODE = {'tools/delivery/' + name + '.py' for name in (
    'stokowski_adapter', 'stokowski_worker', 'stokowski_prepare', 'symphony_capacity',
    'symphony_tasks', 'symphony_workspace', 'symphony_codex', 'symphony_protocol',
    'windmill_runner')}
FORBIDDEN = {'.delivery', '.aws', '.codex', '.ssh', '.env', 'credentials',
             '__pycache__', 'node_modules', 'data', 'output', 'logs', '.venv',
             '.venv-delivery', 'workspaces', 'claims'}


class Refused(ValueError):
    pass


def require(condition, reason):
    if not condition:
        raise Refused(reason)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def encoded(value):
    return (json.dumps(value, sort_keys=True, separators=(',', ':'),
                       ensure_ascii=True) + '\n').encode()


def record(raw):
    def unique(pairs):
        out = {}
        for key, value in pairs:
            require(key not in out, 'duplicate key')
            out[key] = value
        return out
    value = json.loads(raw, object_pairs_hook=unique)
    require(isinstance(value, dict), 'object required')
    return value


def relative(name):
    require(isinstance(name, str) and name and '\\' not in name
            and not any(ord(c) < 32 for c in name), 'relative name')
    path = PurePosixPath(name)
    require(bool(path.parts) and not path.is_absolute() and str(path) == name
            and all(p not in ('', '.', '..') for p in path.parts), 'relative name')
    return path


def canonical(path):
    path = Path(path)
    require(path.is_absolute() and path == path.resolve(), 'canonical path')
    return path


class Filesystem:
    """Only metadata/identity injection is needed by offline synthetic tests."""
    def ids(self):
        return os.getuid(), os.geteuid()

    def info(self, path):
        return path.lstat()

    def owned(self, path, mode):
        os.chown(path, 0, 0, follow_symlinks=False)
        os.chmod(path, mode, follow_symlinks=False)


def regular(path, limit=MAX_FILE, *, dir_fd=None):
    """Read through no-follow FD; bound size and reject hardlink custody."""
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=dir_fd)
    try:
        before = os.fstat(fd)
        require(stat.S_ISREG(before.st_mode) and before.st_nlink == 1
                and 0 <= before.st_size <= limit, 'regular bounded single-link file')
        with os.fdopen(fd, 'rb', closefd=False) as stream:
            raw = stream.read(limit + 1)
        after = os.fstat(fd)
        require(len(raw) == before.st_size and
                (before.st_size, before.st_mtime_ns, before.st_ctime_ns) ==
                (after.st_size, after.st_mtime_ns, after.st_ctime_ns), 'file drift')
        return raw
    finally:
        os.close(fd)


def root_parents(path, fs):
    for parent in (path, *path.parents):
        info = fs.info(parent)
        require(stat.S_ISDIR(info.st_mode) and info.st_uid == 0
                and not info.st_mode & 0o022, 'unsafe root parent')


def write_new(path, raw, mode, fs=None):
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    try:
        with os.fdopen(fd, 'wb', closefd=False) as stream:
            stream.write(raw)
            stream.flush()
            os.fsync(fd)
        if fs:
            fs.owned(path, mode)
        else:
            os.chmod(path, mode)
    finally:
        os.close(fd)


def sync_dir(path):
    fd = os.open(path, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def safe_source(name):
    parts = relative(name).parts
    require(not set(parts) & FORBIDDEN and '.git' not in parts
            and not any(p.endswith(('.log', '.pem', '.key')) or
                        p.startswith('.env') or p in ('auth.json', 'credentials.json')
                        for p in parts), 'excluded source path')


def git_closure(git_dir, head):
    """Read local objects using a config/hook/filter-free disposable Git DB.

    Owner supplies the actual git directory (including for linked worktrees).
    Alternates, grafts, replacement refs, shallow and partial clones are refused.
    Only objects are read, never the candidate's config, index or hooks. Output
    contains the selected tree/blob closure and ancestor commits, not historical
    payloads. The source object store is read in place by the nonroot Git reader;
    no packed repository history is copied into the preparation directory.
    """
    git_dir = canonical(git_dir)
    require((git_dir / 'objects').is_dir() and
            git_dir / 'objects' == (git_dir / 'objects').resolve(), 'Git object directory link')
    require(re.fullmatch('[0-9a-f]{40}', head) is not None, 'head pin')
    for name in ('shallow', 'info/grafts', 'objects/info/alternates',
                 'objects/info/http-alternates'):
        require(not os.path.lexists(git_dir / name), 'external or incomplete Git')
    with tempfile.TemporaryDirectory() as temp:
        db = Path(temp) / 'git'
        (db / 'objects').mkdir(parents=True)
        (db / 'refs').mkdir()
        (db / 'HEAD').write_text(head + '\n')
        count = total = 0
        for path in sorted((git_dir / 'objects').rglob('*')):
            info = path.lstat()
            require(stat.S_ISDIR(info.st_mode) or stat.S_ISREG(info.st_mode), 'Git link')
            if path.is_dir():
                continue
            name = path.relative_to(git_dir / 'objects').as_posix()
            if name in ('info/commit-graph', 'info/packs'):
                require(info.st_nlink == 1 and info.st_size <= MAX_FILE,
                        'Git administrative metadata custody')
                continue
            if re.fullmatch(r'pack/pack-[0-9a-f]{40}\.(?:keep|rev)', name):
                require(info.st_nlink == 1 and info.st_size <= 1024 * 1024,
                        'Git sidecar custody')
                for suffix in ('.pack', '.idx'):
                    companion = path.with_suffix(suffix).lstat()
                    require(stat.S_ISREG(companion.st_mode) and companion.st_nlink == 1
                            and companion.st_size <= MAX_FILE, 'Git sidecar pair')
                continue
            require(re.fullmatch(r'(?:[0-9a-f]{2}/[0-9a-f]{38}|pack/pack-[0-9a-f]{40}\.(?:pack|idx))', name),
                    'unknown Git storage')
            require(info.st_nlink == 1 and info.st_size <= MAX_FILE, 'Git storage custody')
            count += 1
            total += info.st_size
            require(count <= MAX_FILES and total <= MAX_TOTAL, 'Git bounds')
        env = {'PATH': '/usr/bin:/bin', 'HOME': temp, 'LC_ALL': 'C',
               'GIT_CONFIG_NOSYSTEM': '1', 'GIT_CONFIG_GLOBAL': '/dev/null',
               'GIT_NO_REPLACE_OBJECTS': '1', 'GIT_TERMINAL_PROMPT': '0',
               'GIT_OBJECT_DIRECTORY': str(git_dir / 'objects')}

        def git(*args):
            result = subprocess.run(['/usr/bin/git', '--git-dir=' + str(db),
                                     '-c', 'core.commitGraph=false', *args],
                                    env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                    timeout=120, check=True)
            require(len(result.stdout) <= MAX_TOTAL, 'Git output bounds')
            return result.stdout

        require(git('cat-file', '-t', head).strip() == b'commit', 'commit pin')
        tree = git('rev-parse', head + '^{tree}').decode().strip()
        source, excluded, required_blobs = {}, set(), set()
        for item in git('ls-tree', '-rz', '--full-tree', head).split(b'\0'):
            if not item:
                continue
            meta, name = item.split(b'\t', 1)
            mode, kind, oid = meta.decode().split()
            name = name.decode('utf-8')
            if name in EXCLUDED_ARCHIVAL_EVIDENCE:
                require(kind == 'blob' and mode == '100644' and
                        oid == EXCLUDED_ARCHIVAL_EVIDENCE[name], 'archival evidence pin')
                excluded.add(oid)
                continue
            safe_source(name)
            require(kind == 'blob' and mode in ('100644', '100755'), 'source link/submodule')
            source[name] = (git('cat-file', 'blob', oid), 0o555 if mode == '100755' else 0o444)
            required_blobs.add(oid)
        # Keep current source objects plus commit-only ancestry for merge-base.
        objects = set(line.split()[0].decode() for line in
                      git('rev-list', '--objects', '--no-walk', head).splitlines())
        objects.update(git('rev-list', head).decode().splitlines())
        objects.difference_update(excluded - required_blobs)
        require(len(objects) <= MAX_FILES, 'Git object count')
        metadata = {'.git/HEAD': ((head + '\n').encode(), 0o444),
                    '.git/refs/heads/accepted': ((head + '\n').encode(), 0o444),
                    '.git/config': (b'[core]\n\trepositoryformatversion = 0\n\tbare = false\n', 0o444)}
        for oid in sorted(objects):
            kind = git('cat-file', '-t', oid).decode().strip()
            raw = git('cat-file', kind, oid)
            obj = kind.encode() + b' ' + str(len(raw)).encode() + b'\0' + raw
            require(hashlib.sha1(obj).hexdigest() == oid, 'Git object drift')
            metadata['.git/objects/' + oid[:2] + '/' + oid[2:]] = (zlib.compress(obj), 0o444)
        return tree, source, metadata


def validate_config(config, runtime):
    require(set(config) - OPTIONAL == REQUIRED, 'current config fields')
    root = canonical(config['runtime_root'])
    require(root.name == 'stokowski' and root.parent.name == '.delivery'
            and runtime.is_relative_to(root) and root.is_dir(), 'runtime binding')
    require(type(config['version']) is int and config['version'] == 1
            and isinstance(config['owner'], str) and config['owner'].strip(), 'current identity')
    require(isinstance(config['source_head'], str) and
            re.fullmatch('[0-9a-f]{40}', config['source_head']), 'source head')
    require(isinstance(config['source_sha256'], dict) and CODE <= set(config['source_sha256']),
            'source pins')
    for name, pin in config['source_sha256'].items():
        safe_source(name)
        require(isinstance(pin, str) and re.fullmatch('[0-9a-f]{64}', pin), 'source digest')
    for field in ('workflow_sha256', 'policy_sha256', 'installation_sha256'):
        require(isinstance(config[field], str) and re.fullmatch('[0-9a-f]{64}', config[field]),
                'current digest')
    canonical(config['catalog'])
    if 'project_route' in config:
        routes = {'ce60c1ab-a732-4a71-8471-14c9dc393886': 'ccd080f4f6f0',
                  'ffb6c7d9-4eff-46eb-a805-99f0cc2edfa0': '21558318e036'}
        route = config['project_route']
        require(isinstance(route, dict) and set(route) == {'project_id', 'project_slug'}
                and route['project_id'] in routes and routes[route['project_id']] == route['project_slug'],
                'project route pair')
    for field in ('completed_native_validations', 'native_review_policies'):
        refs = config.get(field, {})
        require(isinstance(refs, dict), 'current references')
        for issue, ref in refs.items():
            require(re.fullmatch(r'UIF-[1-9][0-9]*', issue) and isinstance(ref, dict)
                    and set(ref) == {'path', 'sha256'} and
                    isinstance(ref['sha256'], str) and re.fullmatch('[0-9a-f]{64}', ref['sha256']),
                    'current reference')
            require(canonical(ref['path']).is_relative_to(root), 'private reference')


def environment_files(venv, python, fs):
    venv, python = canonical(venv), canonical(python)
    require(venv.is_dir(), 'venv directory')
    cfg = regular(venv / 'pyvenv.cfg')
    settings = dict(line.split('=', 1) for line in cfg.decode().splitlines() if '=' in line)
    settings = {k.strip(): v.strip() for k, v in settings.items()}
    require(settings.get('include-system-site-packages', '').lower() == 'false', 'system packages')
    home = Path(settings.get('home', ''))
    if home in SYSTEM_PYTHON_HOME_ALIASES:
        resolved, link_text = SYSTEM_PYTHON_HOME_ALIASES[home]
        alias_info = fs.info(home)
        require(stat.S_ISLNK(alias_info.st_mode) and alias_info.st_uid == alias_info.st_gid == 0
                and os.readlink(home) == link_text and home.resolve() == resolved,
                'system Python home alias')
        root_parents(home.parent, fs)
        home = canonical(resolved)
    else:
        home = canonical(home)
    # Standard library/dynamic-loader custody remains the qualified OS's root
    # boundary, not an actor-owned interpreter home. Never rewrite pyvenv.cfg.
    root_parents(home, fs)
    root_parents(python.parent, fs)
    info = fs.info(python)
    require(info.st_uid == info.st_gid == 0 and not info.st_mode & 0o022, 'base Python custody')
    require((venv / 'bin/python').resolve() == python, 'Python identity')
    result = {}
    for path in sorted(venv.rglob('*')):
        name = path.relative_to(venv).as_posix()
        info = path.lstat()
        if stat.S_ISDIR(info.st_mode):
            continue
        if stat.S_ISLNK(info.st_mode):
            if name == 'lib64':
                require(os.readlink(path) == 'lib' and (venv / 'lib').is_dir(), 'lib64 link')
                continue  # materialized below
            require(name in ('bin/python', 'bin/python3', 'bin/python' + settings.get('version', '').rsplit('.', 1)[0])
                    and path.resolve() == python, 'arbitrary environment link')
            raw = regular(python, 8 * 1024 * 1024)
        else:
            require(stat.S_ISREG(info.st_mode), 'environment special file')
            require(not set(relative(name).parts) & (FORBIDDEN - {'__pycache__'}), 'private environment path')
            raw = regular(path)
        if name.endswith('.pth'):
            # Executable .pth files can conceal references to actor-owned source.
            require(not any(line.strip() and not line.startswith('#') and
                            (line.startswith(('import ', 'import\t')) or Path(line.strip()).is_absolute()
                             or '..' in PurePosixPath(line.strip()).parts)
                            for line in raw.decode().splitlines()), 'external/executable pth')
        require(not name.endswith('.egg-link'), 'editable dependency')
        result[name] = (raw, 0o555 if info.st_mode & 0o111 or name.startswith('bin/python') else 0o444)
    require('bin/python' in result and result['bin/python'][0], 'canonical Python missing')
    if (venv / 'lib64').is_symlink():
        for name, value in list(result.items()):
            if name.startswith('lib/'):
                result['lib64/' + name[4:]] = value
    return result


def prepare(*, stage, source, git_dir, head, tree, venv, python, runtime,
            config_sha256, catalog_sha256, python_sha256, dependency_sha256, fs=None):
    """Nonroot only. All references are explicit nonsecret owner inputs.

    Pin arguments must come from independent qualification, not this function's
    own observation. No candidate Python, hooks, filters or commands execute.
    Stage must be a new directory beneath a private actor-controlled parent.
    """
    fs = fs or Filesystem()
    require(0 not in fs.ids(), 'prepare must be nonroot')
    source, runtime, stage = canonical(source), canonical(runtime), canonical(stage)
    parent = stage.parent.lstat()
    require(parent.st_uid == os.getuid() and not parent.st_mode & 0o077, 'private staging parent')
    original = regular(runtime / 'current.json', 8 * 1024 * 1024)
    require(sha(original) == config_sha256, 'config pin')
    config = record(original)
    validate_config(config, runtime)
    catalog = regular(Path(config['catalog']), 8 * 1024 * 1024)
    require(sha(catalog) == catalog_sha256, 'catalog pin')
    cat = record(catalog)
    require(set(cat) == {'version', 'entries'} and type(cat['version']) is int
            and cat['version'] == 1 and isinstance(cat['entries'], list), 'catalog schema')
    issues, identities, runtimes = set(), set(), set()
    for entry in cat['entries']:
        require(isinstance(entry, dict) and set(entry) ==
                {'issue', 'issue_id', 'runtime', 'admission_sha256'}, 'catalog entry')
        require(isinstance(entry['issue'], str) and re.fullmatch(r'UIF-[1-9][0-9]*', entry['issue'])
                and str(UUID(entry['issue_id'])) == entry['issue_id']
                and re.fullmatch('[0-9a-f]{64}', entry['admission_sha256']), 'catalog identity')
        require(canonical(entry['runtime']).is_relative_to(Path(config['runtime_root'])), 'catalog runtime')
        for seen, value in ((issues, entry['issue']), (identities, entry['issue_id']), (runtimes, entry['runtime'])):
            require(value not in seen, 'duplicate catalog identity')
            seen.add(value)
    actual_tree, files, metadata = git_closure(git_dir, head)
    require(actual_tree == tree and config['source_head'] == head, 'accepted source pin')
    for name, (raw, _) in files.items():
        path = source / name
        require(path == path.resolve() and regular(path) == raw, 'dirty or linked source')
    for name, pin in config['source_sha256'].items():
        require(name in files and sha(files[name][0]) == pin, 'accepted source digest')
    require(sha(files['tools/delivery/capacity-policy.json'][0]) == config['policy_sha256'], 'policy pin')
    env = environment_files(venv, python, fs)
    require(sha(env['bin/python'][0]) == python_sha256 and
            sha(encoded({name: {'sha256': sha(raw), 'mode': mode} for name, (raw, mode) in env.items()}))
            == dependency_sha256, 'qualified environment pin')
    selected = dict(config, catalog=str(CONFIG / 'catalog.json'), source_head=head,
                    source_sha256={name: sha(files[name][0]) for name in config['source_sha256']})
    current = encoded(selected)
    binding = dict(schema='protected-current-owner-v1', runtime=str(runtime),
                   config_sha256=sha(current), catalog_sha256=sha(catalog),
                   source_root=str(SOURCE), python_sha256=sha(env['bin/python'][0]))
    groups = {'source': dict(files, **metadata), 'venv': env,
              'config': {'current.json': (current, 0o444), 'catalog.json': (catalog, 0o444),
                         'binding.json': (encoded(binding), 0o444)}}
    payload = []
    total = 0
    for group, values in groups.items():
        for name, (raw, mode) in sorted(values.items()):
            require(len(raw) <= MAX_FILE, 'payload file bound')
            total += len(raw)
            payload.append(dict(group=group, name=name, size=len(raw), sha256=sha(raw), mode=mode))
    require(len(payload) <= MAX_FILES and total <= MAX_TOTAL, 'payload bounds')
    manifest = dict(schema=SCHEMA, head=head, tree=tree, runtime=str(runtime),
                    runtime_identity={key: getattr(runtime.stat(), 'st_' + key) for key in ('uid', 'gid', 'dev', 'ino')},
                    dependency_sha256=dependency_sha256,
                    original_config_sha256=config_sha256, original_catalog_sha256=catalog_sha256,
                    original_catalog=str(canonical(config['catalog'])),
                    original_config=original.decode('utf-8'),
                    source=str(source), git_dir=str(canonical(git_dir)), venv=str(canonical(venv)),
                    python=str(canonical(python)), payload=payload,
                    rollback={'custody': 'existing owner; reconcile receipt before any manual rollback',
                              'runtime': str(runtime), 'source': str(source), 'venv': str(canonical(venv)),
                              'config': str(runtime / 'current.json'), 'catalog': config['catalog'],
                              'config_sha256': config_sha256, 'catalog_sha256': catalog_sha256})
    stage.mkdir(mode=0o700)
    (stage / 'payload').mkdir(mode=0o700)
    for index, item in enumerate(payload):
        write_new(stage / 'payload' / str(index), groups[item['group']][item['name']][0], 0o400)
    raw = encoded(manifest)
    require(len(raw) <= 8 * 1024 * 1024, 'manifest bound')
    write_new(stage / 'manifest.json', raw, 0o400)
    sync_dir(stage / 'payload')
    sync_dir(stage)
    sync_dir(stage.parent)
    return sha(raw)


def validate_git_payload(content, manifest):
    """Verify the closed Git graph and checkout without invoking Git as root."""
    objects = {}
    checkout = {}
    config = b'[core]\n\trepositoryformatversion = 0\n\tbare = false\n'
    for path, raw in content.items():
        if not Path(path).is_relative_to(SOURCE):
            continue
        name = Path(path).relative_to(SOURCE).as_posix()
        if not name.startswith('.git/'):
            safe_source(name)
            checkout[name] = raw
            continue
        if name in ('.git/HEAD', '.git/refs/heads/accepted'):
            require(raw == (manifest['head'] + '\n').encode(), 'Git head bytes')
        elif name == '.git/config':
            require(raw == config, 'unsafe Git config')
        else:
            require(re.fullmatch(r'\.git/objects/[0-9a-f]{2}/[0-9a-f]{38}', name), 'unsafe Git metadata')
            decompress = zlib.decompressobj()
            obj = decompress.decompress(raw, MAX_FILE + 1)
            require(len(obj) <= MAX_FILE and decompress.eof and not decompress.unused_data, 'Git object bounds')
            oid = name.split('/')[-2] + name.split('/')[-1]
            require(hashlib.sha1(obj).hexdigest() == oid, 'Git object hash')
            header, value = obj.split(b'\0', 1)
            kind, size = header.split(b' ')
            require(size == str(len(value)).encode() and kind in (b'blob', b'tree', b'commit'), 'Git object header')
            objects[oid] = (kind, value)
    visited, active, head_files = set(), set(), {}

    def walk(oid, prefix=None):
        require(oid in objects, 'incomplete Git closure')
        require(oid not in active, 'cyclic Git graph')
        kind, value = objects[oid]
        if oid in visited and prefix is None:
            return
        active.add(oid)
        if kind == b'commit':
            headers = value.split(b'\n\n', 1)[0].splitlines()
            trees = [line[5:].decode() for line in headers if line.startswith(b'tree ')]
            require(len(trees) == 1, 'Git commit tree')
            if oid == manifest['head']:
                require(trees[0] == manifest['tree'], 'Git tree pin')
                walk(trees[0], '')
            for line in headers:
                if line.startswith(b'parent '):
                    parent = line[7:].decode()
                    require(parent in objects and objects[parent][0] == b'commit', 'Git parent commit')
                    walk(parent)
        elif kind == b'tree':
            while value:
                entry, tail = value.split(b'\0', 1)
                mode, name = entry.split(b' ', 1)
                require(len(tail) >= 20 and b'/' not in name, 'Git tree entry')
                child, value = tail[:20].hex(), tail[20:]
                require(mode in (b'40000', b'100644', b'100755'), 'Git historical link/submodule')
                if prefix is not None:
                    path = prefix + name.decode('utf-8')
                    if path in EXCLUDED_ARCHIVAL_EVIDENCE:
                        require(mode == b'100644' and child == EXCLUDED_ARCHIVAL_EVIDENCE[path],
                                'archival evidence pin')
                        continue
                    require(child in objects, 'incomplete Git tree')
                    safe_source(path)
                    if mode != b'40000':
                        require(objects[child][0] == b'blob' and path not in head_files, 'Git blob')
                        head_files[path] = objects[child][1]
                    walk(child, path + '/' if mode == b'40000' else None)
                else:
                    require(child in objects, 'incomplete Git tree')
                    walk(child)
        active.remove(oid)
        visited.add(oid)

    require(manifest['head'] in objects and objects[manifest['head']][0] == b'commit', 'Git commit missing')
    walk(manifest['head'])
    require(set(objects) == visited and checkout == head_files, 'exact source closure')


def install(stage, frozen_digest, *, fs=None):
    """Trusted root operator only; fixed destinations, no commands or replay.

    Tests patch module constants into synthetic roots and inject metadata. Those
    seams are Python test seams, never accepted from a manifest or CLI argument.
    All bytes are frozen in memory before intent or installation writes.
    """
    fs = fs or Filesystem()
    require(fs.ids() == (0, 0), 'root real/effective identity required')
    stage = canonical(stage)
    require(not os.path.lexists(RECEIPT), 'prior receipt; reconcile, never replay')
    # Pin directory descriptors before reading actor-owned staging. In particular
    # a concurrent rename must not redirect a privileged read through a link.
    stage_fd = os.open(stage, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        raw = regular('manifest.json', 8 * 1024 * 1024, dir_fd=stage_fd)
        require(set(os.listdir(stage_fd)) == {'manifest.json', 'payload'}, 'unexpected staging file')
        payload_fd = os.open('payload', os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=stage_fd)
    finally:
        os.close(stage_fd)
    try:
        return _install_frozen(raw, frozen_digest, payload_fd, fs)
    finally:
        os.close(payload_fd)


def _install_frozen(raw, frozen_digest, payload_fd, fs):
    require(sha(raw) == frozen_digest, 'frozen manifest digest')
    manifest = record(raw)
    require(set(manifest) == {'schema', 'head', 'tree', 'runtime', 'original_config_sha256',
                             'original_catalog_sha256', 'original_catalog', 'original_config', 'source', 'git_dir', 'venv', 'python',
                             'runtime_identity', 'dependency_sha256', 'payload', 'rollback'}
            and manifest['schema'] == SCHEMA, 'manifest schema')
    for key in ('head', 'tree'):
        require(isinstance(manifest[key], str) and re.fullmatch('[0-9a-f]{40}', manifest[key]), 'Git pin')
    for key in ('original_config_sha256', 'original_catalog_sha256'):
        require(isinstance(manifest[key], str) and re.fullmatch('[0-9a-f]{64}', manifest[key]), 'original pin')
    for key in ('runtime', 'source', 'git_dir', 'venv', 'python', 'original_catalog'):
        canonical(manifest[key])
    require(manifest['runtime_identity'] == {key: getattr(Path(manifest['runtime']).stat(), 'st_' + key)
                                           for key in ('uid', 'gid', 'dev', 'ino')}, 'runtime identity drift')
    require(isinstance(manifest['rollback'], dict), 'rollback custody')
    items = manifest['payload']
    require(isinstance(items, list) and 0 < len(items) <= MAX_FILES, 'payload count')
    require(set(os.listdir(payload_fd)) == {str(i) for i in range(len(items))},
            'unexpected staging file')
    targets = {'source': SOURCE, 'venv': VENV, 'config': CONFIG}
    frozen, names, total = [], set(), 0
    for index, item in enumerate(items):
        require(isinstance(item, dict) and set(item) == {'group', 'name', 'size', 'sha256', 'mode'}, 'payload schema')
        require(item['group'] in targets and type(item['mode']) is int and item['mode'] in (0o444, 0o555), 'payload destination/mode')
        name = relative(item['name'])
        identity = (item['group'], str(name))
        require(identity not in names, 'duplicate destination')
        names.add(identity)
        require(type(item['size']) is int and 0 <= item['size'] <= MAX_FILE, 'payload size')
        data = regular(str(index), dir_fd=payload_fd)
        require(len(data) == item['size'] and sha(data) == item['sha256'], 'payload digest drift')
        total += len(data)
        require(total <= MAX_TOTAL, 'payload total')
        frozen.append((targets[item['group']] / str(name), data, item['mode']))
    for group, name in names:
        parts = PurePosixPath(name).parts
        require(not any((group, str(PurePosixPath(*parts[:i]))) in names
                        for i in range(1, len(parts))), 'file/directory collision')
    require({name for group, name in names if group == 'config'} ==
            {'current.json', 'catalog.json', 'binding.json'} and
            ('venv', 'bin/python') in names and ('venv', 'pyvenv.cfg') in names and
            ('source', '.git/HEAD') in names, 'closure fields')
    content = {str(path): data for path, data, mode in frozen}
    require(sha(encoded({item['name']: {'sha256': item['sha256'], 'mode': item['mode']}
                         for item in items if item['group'] == 'venv'})) == manifest['dependency_sha256'],
            'dependency closure pin')
    validate_git_payload(content, manifest)
    config = record(content[str(CONFIG / 'current.json')])
    validate_config(config, Path(manifest['runtime']))
    require(isinstance(manifest['original_config'], str) and
            sha(manifest['original_config'].encode()) == manifest['original_config_sha256'], 'original config pin')
    original_config = record(manifest['original_config'].encode())
    require(original_config.get('catalog') == manifest['original_catalog'] and
            config == dict(original_config, catalog=str(CONFIG / 'catalog.json')),
            'only catalog relocation permitted')
    binding = record(content[str(CONFIG / 'binding.json')])
    require(binding == dict(schema='protected-current-owner-v1', runtime=manifest['runtime'],
                           config_sha256=sha(content[str(CONFIG / 'current.json')]),
                           catalog_sha256=sha(content[str(CONFIG / 'catalog.json')]),
                           source_root=str(SOURCE), python_sha256=sha(content[str(VENV / 'bin/python')])),
            'consumer binding')
    require(config['catalog'] == str(CONFIG / 'catalog.json') and config['source_head'] == manifest['head']
            and sha(content[str(CONFIG / 'catalog.json')]) == manifest['original_catalog_sha256']
            and content[str(SOURCE / '.git/HEAD')] == (manifest['head'] + '\n').encode(), 'consumer pins')
    for name, pin in config['source_sha256'].items():
        require(str(SOURCE / name) in content and sha(content[str(SOURCE / name)]) == pin, 'consumer source pin')
    # No existing installation is ever adopted, repaired or overwritten.
    for target in (SOURCE.parent, CONFIG):
        require(not os.path.lexists(target), 'unexpected existing target')
        root_parents(target.parent, fs)
    root_parents(RECEIPT.parent, fs)
    intent = dict(schema=SCHEMA, manifest_sha256=frozen_digest, state='intent',
                  manifest=manifest, rollback=manifest['rollback'], readback={})
    write_new(RECEIPT, encoded(intent), 0o400, fs)
    sync_dir(RECEIPT.parent)
    try:
        directories = {SOURCE.parent, SOURCE, VENV, CONFIG}
        for target, data, mode in frozen:
            parent = target.parent
            while parent not in (SOURCE.parent.parent, CONFIG.parent):
                directories.add(parent)
                parent = parent.parent
        for directory in sorted(directories, key=lambda p: (len(p.parts), str(p))):
            root_parents(directory.parent, fs)
            directory.mkdir(mode=0o755)
            fs.owned(directory, 0o755)
        for target, data, mode in frozen:
            root_parents(target.parent, fs)
            write_new(target, data, mode, fs)
        readback = {}
        for target, data, mode in frozen:
            info = fs.info(target)
            require(stat.S_ISREG(info.st_mode) and info.st_uid == info.st_gid == 0
                    and info.st_nlink == 1 and stat.S_IMODE(info.st_mode) == mode,
                    'installed custody')
            readback[str(target)] = sha(regular(target))
            require(readback[str(target)] == sha(data), 'readback drift')
        for directory in sorted(directories, key=lambda p: -len(p.parts)):
            sync_dir(directory)
        # Intent remains immutable. Completion/failure is a single append to the
        # same private receipt, so a crash can never erase the no-replay fence.
        outcome = dict(state='complete', readback=readback)
    except Exception as exc:
        outcome = dict(state='partial-or-unknown', error=type(exc).__name__,
                       rollback='retain targets and immutable intent; independent owner reconciliation required')
        _append_outcome(outcome, fs)
        raise
    _append_outcome(outcome, fs)
    return outcome


def _append_outcome(outcome, fs):
    # JSON-lines: first line is the immutable intent, second is readback/outcome.
    fd = os.open(RECEIPT, os.O_WRONLY | os.O_APPEND | os.O_NOFOLLOW)
    try:
        info = os.fstat(fd)
        require(stat.S_ISREG(info.st_mode) and info.st_nlink == 1, 'receipt custody')
        raw = encoded(outcome)
        require(os.write(fd, raw) == len(raw), 'incomplete outcome; retain unknown state')
        os.fsync(fd)
    finally:
        os.close(fd)
