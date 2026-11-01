"""Offline, one-shot producer for the fixed publisher; no executable entrypoint.

The trusted host owner supplies already-qualified config bytes and independent
config/closure/prepare pins. These checks establish byte association and custody,
not review, admission, authentication or application acceptance. Preparation runs
unprivileged; installation is a separate explicit trusted-owner call. Neither
call imports or executes the copied source/interpreter, reads a key, or repairs
an earlier attempt. An intent (including a partial one) permanently holds replay.
"""
from contextlib import contextmanager
import hashlib
import json
import os
from pathlib import PurePosixPath
import re
import stat
from uuid import UUID

SOURCE = '/opt/offmenu-stokowski-current/source'
# Publisher needs the delivery graph packages, not the coordinator-only venv.
# This separately qualified, sealed dependency input must exist before prepare.
VENV = '/opt/offmenu-publisher-dependencies'
TARGET = '/opt/offmenu-publisher'
CONFIG_DIR = '/etc/offmenu-publisher'
STATE = '/var/lib/offmenu-publisher'
RECEIPT = 'publisher-install.jsonl'
SOURCE_HEAD = 'bf9bd13fef1bad2f5994b54ae7eafbe1ff4d78d5'
REQUIRED = (
    'tools/delivery/github-app-publisher.mjs',
    'tools/delivery/github-app-adapter.mjs',
    'tools/delivery/integration-gateway.mjs',
    'src/offmenu/delivery/integration.py', 'src/offmenu/delivery/engine.py',
    'src/offmenu/__init__.py', 'src/offmenu/delivery/__init__.py',
)
# engine imports standards at module load; it is part of the sealed code closure.
SOURCE_FILES = REQUIRED + ('src/offmenu/delivery/standards.py',)
RELEASE_REQUIRED = REQUIRED + ('tools/delivery/native_harness_contract.py',
    'contracts/schemas/delivery-handoff-v1.schema.json', 'tools/delivery/release_qualification.py')
RELEASE_SOURCE_FILES = RELEASE_REQUIRED + ('src/offmenu/delivery/standards.py',)
MAX_JSON = 1048576
MAX_MANIFEST = 16 * MAX_JSON
MAX_FILE = 32 * MAX_JSON
MAX_TOTAL = 512 * MAX_JSON
MAX_ENTRIES = 50000


class InstallError(ValueError):
    """Held input or filesystem; no automatic recovery is safe."""


def _check(condition, message='Publisher install held'):
    if not condition:
        raise InstallError(message)


def _hash(data):
    return hashlib.sha256(data).hexdigest()


def _wire(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()


def _hex(value, length=64):
    return isinstance(value, str) and re.fullmatch('[0-9a-f]{%d}' % length, value) is not None


def _path(value):
    return (isinstance(value, str) and len(value) <= 512
            and re.fullmatch(r'[a-zA-Z0-9_.@+/-]+', value) is not None
            and not value.startswith('/')
            and all(p not in ('', '.', '..', '.git') for p in value.split('/'))
            and not value.startswith('.github/workflows/'))


def _parse(raw, limit=MAX_JSON):
    _check(type(raw) is bytes and 0 < len(raw) <= limit, 'Bounded JSON bytes required')
    def pairs(items):
        result = {}
        for key, value in items:
            _check(key not in result, 'Duplicate JSON key')
            result[key] = value
        return result
    def integer(value):
        number = int(value)
        _check(abs(number) <= 2**53 - 1)
        return number
    def invalid(_):
        raise InstallError('Only integer JSON numbers supported')
    try:
        return json.loads(raw.decode('utf-8'), object_pairs_hook=pairs,
                          parse_int=integer, parse_float=invalid, parse_constant=invalid)
    except (ValueError, UnicodeError, RecursionError) as exc:
        raise InstallError('Invalid JSON') from exc


def _config(raw, expected_hash, source_pins, dependency_pins):
    _check(type(raw) is bytes and 0 < len(raw) <= MAX_JSON
           and _hex(expected_hash) and _hash(raw) == expected_hash,
           'Independent config pin mismatch')
    c = _parse(raw)
    try:
        optional = ({k for k in ('integration_admission','nativeContinuation') if k in c}
                    if c.get('version') == 1 else set())
        _check(set(c) == {'version', 'appId', 'installationId', 'repositoryId',
            'publisherUid', 'publisherGid', 'logicalOwner', 'sourceHead', 'codePins',
            'pythonSha256', 'binding', 'snapshot', 'plan', 'workspace'} | optional)
        _check(type(c['version']) is int and c['version'] in (1, 2))
        for key, value in dict(appId=5554359, installationId=177187048,
                               repositoryId=1416253963, publisherUid=984, publisherGid=976).items():
            _check(type(c[key]) is int and c[key] == value, 'Fixed identity mismatch')
        _check(c['sourceHead'] == SOURCE_HEAD)
        required = RELEASE_REQUIRED if c['version'] == 2 else REQUIRED
        source_files = RELEASE_SOURCE_FILES if c['version'] == 2 else SOURCE_FILES
        if c['version'] == 1 and 'source_projection' in c['binding']:
            required += ('src/offmenu/delivery/identity_source_projection.py',)
            source_files += ('src/offmenu/delivery/identity_source_projection.py',)
        _check(type(source_pins) is dict and set(source_pins) == set(source_files)
               and all(_hex(h) for h in source_pins.values())
               and c['codePins'] == {name: source_pins[name] for name in required})
        _check(type(dependency_pins) is dict and dependency_pins
               and len(dependency_pins) <= MAX_ENTRIES
               and all(_path(p) and _hex(h) for p, h in dependency_pins.items()))
        _check({'bin/python', 'pyvenv.cfg'} <= dependency_pins.keys()
               and _hex(c['pythonSha256']) and c['pythonSha256'] == dependency_pins['bin/python'])
        workspace = c['workspace']
        _check(isinstance(workspace, str) and workspace.startswith('/') and workspace != '/'
               and str(PurePosixPath(workspace)) == workspace and '..' not in workspace.split('/'))
        if c['version'] == 2:
            _release_config(c)
            return c
        b, plan, snapshot = c['binding'], c['plan'], c['snapshot']
        fields = {'version', 'repository', 'pr_number', 'issue_id', 'owner', 'head', 'base', 'tree',
                  'policy_sha256', 'capacity_policy_sha256', 'validation_operation_key',
                  'outputs', 'head_branch', 'publication'}
        optional = {'source_projection'} if 'source_projection' in b else set()
        _check(set(b) in (fields | optional, fields | optional | {'project_id', 'full_issue_acceptance_sha256'})
               and type(b['version']) is int and b['version'] == 2 and b['pr_number'] is None
               and b['repository'] == 'maldous/offmenu' and isinstance(c['logicalOwner'], str)
               and c['logicalOwner'] and b['owner'] == c['logicalOwner'])
        _check(str(UUID(b['issue_id'])) == b['issue_id'])
        if 'project_id' in b:
            _check(str(UUID(b['project_id'])) == b['project_id'] and _hex(b['full_issue_acceptance_sha256']))
        for key in ('head', 'base', 'tree', 'policy_sha256', 'capacity_policy_sha256', 'validation_operation_key'):
            _check(_hex(b[key], 40 if key in ('head', 'base', 'tree') else 64))
        branch = b['head_branch']
        _check(isinstance(branch, str) and re.fullmatch(r'(feature|bugfix)/[a-z0-9][a-z0-9/-]{0,159}', branch)
               and '//' not in branch and not branch.endswith('/'))
        _check(type(b['outputs']) is dict and b['outputs']
               and all(_path(p) and _hex(h) for p, h in b['outputs'].items()))
        _check(set(plan) == {'operations', 'changedFiles'} and type(plan['operations']) is list
               and 2 <= len(plan['operations']) <= 128 and type(plan['changedFiles']) is dict
               and plan['changedFiles'] and all(_path(p) and _hex(h) for p, h in plan['changedFiles'].items())
               and all(plan['changedFiles'].get(p) == h for p, h in b['outputs'].items())
               and ('source_projection' not in b or plan['changedFiles'] == b['outputs']))
        _check(b['publication'] == {'plan_sha256': _hash(_wire(plan)),
                                    'qualification_sha256': _hash(_wire(snapshot))})
        _plan(plan['operations'], b)
        # Association only: semantic review/validation authority remains with the
        # independently qualified owner and the existing fixed consumers.
        _check(type(snapshot) is dict and snapshot['publisher_owner'] == b['owner']
               and snapshot['source_tree'] == b['tree'])
        for key in ('policy_sha256', 'capacity_policy_sha256'):
            _check(snapshot[key] == b[key])
        validation, review = snapshot['validation'], snapshot['review']
        source_base = _source_projection(b, snapshot)
        _check(validation['head'] == review['head'] == b['head']
               and validation['base'] == review['base'] == source_base
               and validation['outputs'] == b['outputs']
               and validation['operation_key'] == b['validation_operation_key']
               and validation['capacity_policy_sha256'] == b['capacity_policy_sha256']
               and validation['status'] == 'succeeded' and validation['child_tree_gone'] is True
               and validation['reconcile_required'] is False and review['independent'] is True
               and isinstance(review['evidence_id'], str) and review['evidence_id']
               and review['verdict'] == 'accept' and review['findings'] == []
               and snapshot['unresolved_findings'] == [] and snapshot['source_clean'] is True
               and snapshot['publication_triggers_actions'] is False and not snapshot.get('cancel_requested'))
        _integration_metadata(c)
    except (KeyError, TypeError, AttributeError, ValueError, RecursionError) as exc:
        raise InstallError('Invalid config association') from exc
    return c


def _integration_metadata(c):
    """Finite sealed association; permission and terminal custody stay owner-qualified."""
    if not any(k in c for k in ('integration_admission','nativeContinuation')):
        return
    b, s = c['binding'], c['snapshot']
    _check(c['version'] == 1 and 'source_projection' in b)
    _source_projection(b, s)
    p, n = b['source_projection'], s['native_runtime']
    if 'integration_admission' in c:
        a = c['integration_admission']
        _check(type(a) is dict and set(a) == {'version','kind','binding_sha256','unit_sha256',
            'review_sha256','permission_sha256','automatic_integration_enabled'}
            and type(a['version']) is int and a['version'] == 1
            and a['kind'] == 'native-reviewed-integration-v1'
            and a['binding_sha256'] == _hash(_wire(b)) and a['unit_sha256'] == n['unit_sha256']
            and a['review_sha256'] == p['review_sha256'] == s['review']['evidence_source']['sha256']
            and _hex(a['permission_sha256']) and a['automatic_integration_enabled'] is True)
    if 'nativeContinuation' in c:
        a = c['nativeContinuation']
        _check(type(a) is dict and set(a) == {'version','operation_id','unit_sha256','packet_sha256',
            'claim_sha256','previous_selection_sha256','previous_capability','previous_record_sha256','receipts'}
            and type(a['version']) is int and a['version'] == 1
            and a['operation_id'] == _hash(_wire(b)) and a['unit_sha256'] == n['unit_sha256']
            and a['packet_sha256'] == n['packet_sha256']
            and all(_hex(a[k]) for k in ('operation_id','unit_sha256','packet_sha256',
                'claim_sha256','previous_selection_sha256','previous_record_sha256')))
        cap, receipts = a['previous_capability'], a['receipts']
        _check(type(cap) is dict and set(cap) == {'version','closure_sha256','host_confirmation_sha256'}
            and type(cap['version']) is int and cap['version'] == 1
            and _hex(cap['closure_sha256']) and _hex(cap['host_confirmation_sha256'])
            and type(receipts) is list and 1 <= len(receipts) <= 128)
        for r in receipts:
            _check(type(r) is dict and set(r) == {'invocation_id','closure_sha256','receipt_sha256'}
                and isinstance(r['invocation_id'], str) and str(UUID(r['invocation_id'])) == r['invocation_id']
                and _hex(r['closure_sha256']) and _hex(r['receipt_sha256']))
        _check(len({r['invocation_id'] for r in receipts}) == len(receipts))


def _source_projection(b, snapshot):
    """Protected DATA association only; owner independently qualifies Git/unit proof."""
    if 'source_projection' not in b:
        return b['base']
    p = b['source_projection']
    _check(type(p) is dict and set(p) == {'version','profile','source','target','merge_tree',
        'outputs','unit_sha256','operation_key','receipt','review_sha256'}
        and type(p['version']) is int and p['version'] == 1 and p['profile'] == 'identity-client-focused')
    s, t, receipt = p['source'], p['target'], p['receipt']
    _check(type(s) is dict and set(s) == {'head','base','tree','branch'}
        and type(t) is dict and set(t) == {'base','tree'}
        and all(_hex(s[k], 40) for k in ('head','base','tree'))
        and all(_hex(t[k], 40) for k in ('base','tree')) and _hex(p['merge_tree'], 40)
        and s['head'] == b['head'] and s['tree'] == b['tree'] and s['branch'] == b['head_branch']
        and t['base'] == b['base'] and p['outputs'] == b['outputs']
        and not any(name.startswith(('docs/development/','tools/delivery/','tests/delivery/',
                                    'src/offmenu/delivery/')) for name in p['outputs'])
        and p['operation_key'] == b['validation_operation_key']
        and all(_hex(p[k]) for k in ('unit_sha256','operation_key','review_sha256'))
        and type(receipt) is dict and set(receipt) == {'path','sha256'} and _hex(receipt['sha256'])
        and isinstance(receipt['path'], str) and receipt['path'].startswith('/')
        and str(PurePosixPath(receipt['path'])) == receipt['path'] and '..' not in receipt['path'].split('/'))
    n = snapshot['native_runtime']
    _check(n['unit_sha256'] == p['unit_sha256'] and all(n['source'][k] == s[k]
        for k in ('head','base','tree','branch')))
    return s['base']


def _release_config(c):
    """Protected-byte association only. Runtime invokes the shared validators.

    Preparation never imports copied source or reads candidate evidence bodies.
    This does not approve a release or upgrade a historical installed closure.
    """
    b, snapshot = c['binding'], c['snapshot']
    _check(set(b) == {'version','kind','repository','owner','candidate','policy','qualification',
                      'authority','pr_number','main_base','tag','issue_id','project_id'}
           and type(b['version']) is int and b['version'] == 3
           and b['kind'] == 'release-promotion-v1' and b['repository'] == 'maldous/offmenu'
           and b['owner'] == c['logicalOwner'] and isinstance(b['owner'], str) and b['owner']
           and type(b['pr_number']) is int and b['pr_number'] > 0 and _hex(b['main_base'],40)
           and re.fullmatch(r'release/[a-z0-9][a-z0-9.-]{0,79}',b['tag'])
           and c['plan'] == {'kind':'release-promotion-v1'})
    for key in ('issue_id','project_id'):
        _check(str(UUID(b[key])) == b[key])
    candidate_hash, qualification_hash = _hash(_wire(b['candidate'])), _hash(_wire(b['qualification']))
    _check(b['authority'] == dict(version=1,kind='release-promotion-authority-v1',owner=b['owner'],
        issue_id=b['issue_id'],project_id=b['project_id'],candidate_sha256=candidate_hash,
        qualification_sha256=qualification_hash,pr_number=b['pr_number'],main_base=b['main_base'],tag=b['tag']))
    _check(snapshot['publisher_owner'] == b['owner']
           and snapshot['qualification_sha256'] == qualification_hash
           and snapshot['publication_triggers_actions'] is False
           and snapshot['unresolved_findings'] == [] and not snapshot.get('cancel_requested'))
    review = snapshot['review']
    _check(review['head'] == b['candidate']['source']['head'] and review['base'] == b['main_base']
           and review['independent'] is True and review['verdict'] == 'accept'
           and isinstance(review['evidence_id'],str) and review['evidence_id'] and review['findings'] == [])


def _plan(operations, binding):
    """Check fixed routes and candidate association; consumers qualify Git objects."""
    root = '/repos/maldous/offmenu'
    branch, head = binding['head_branch'], binding['head']
    kinds = [op['kind'] for op in operations]
    tail = 3 if kinds[-1] == 'update-pr' else 2
    _check(kinds[-tail:] == ['ref', 'create-pr'] + (['update-pr'] if tail == 3 else [])
           and kinds[:-tail] and kinds[-tail-1] == 'commit'
           and all(k in ('blob', 'tree') for k in kinds[:-tail-1]))
    for op in operations:
        _check(set(op) == {'kind', 'method', 'path', 'body', 'readPath', 'expected'}
               and type(op['body']) is dict)
        kind, body = op['kind'], op['body']
        if kind in ('blob', 'tree', 'commit'):
            route = root + '/git/' + {'blob': 'blobs', 'tree': 'trees', 'commit': 'commits'}[kind]
            _check(op['method'] == 'POST' and op['path'] == route and _hex(op['expected'], 40)
                   and op['readPath'] == route + '/' + op['expected'])
            if kind == 'commit':
                _check(op['expected'] == head and body['tree'] == binding['tree']
                       and body['parents'] == [binding.get('source_projection', {}).get('source', {}).get('base', binding['base'])])
        elif kind == 'ref':
            _check(op['method'] == 'POST' and op['path'] == root + '/git/refs'
                   and op['expected'] is None and body == {'ref': 'refs/heads/' + branch, 'sha': head}
                   and op['readPath'] == root + '/git/ref/heads/' + branch)
        else:
            create = kind == 'create-pr'
            route = root + ('/pulls' if create else '/pulls/{canonical}')
            _check(op['method'] == ('POST' if create else 'PATCH') and op['path'] == route
                   and op['readPath'] == (root + '/pulls?state=all&head=maldous:' + branch
                                          + '&base=develop' if create else route)
                   and op['expected'] == head and body['base'] == 'develop'
                   and set(body) == ({'title', 'body', 'base', 'head'} if create else {'title', 'body', 'base'})
                   and isinstance(body['title'], str) and 0 < len(body['title']) <= 256
                   and isinstance(body['body'], str) and len(body['body']) <= 65536
                   and (not create or body['head'] == branch))


class _Host:
    """Fixed host filesystem. Private injection is solely for synthetic tests."""
    def identity(self):
        return os.getuid(), os.geteuid()

    def metadata(self, fd):
        return os.fstat(fd)

    def owner(self, fd, uid, gid):
        os.fchown(fd, uid, gid)

    @contextmanager
    def directory(self, path):
        _check(path.startswith('/') and str(PurePosixPath(path)) == path
               and '..' not in path.split('/'))
        fd = os.open('/', os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        try:
            self.controlled(fd)
            for part in PurePosixPath(path).parts[1:]:
                new = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=fd)
                os.close(fd)
                fd = new
                self.controlled(fd)
            yield fd
        finally:
            os.close(fd)

    def controlled(self, fd):
        s = self.metadata(fd)
        _check(stat.S_ISDIR(s.st_mode) and s.st_uid == 0 and not s.st_mode & 0o022,
               'Root-controlled directory required')


def _read(host, directory, name):
    fd = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=directory)
    try:
        before = host.metadata(fd)
        _check(stat.S_ISREG(before.st_mode) and before.st_uid == 0 and before.st_nlink == 1
               and not before.st_mode & 0o7222 and before.st_size <= MAX_FILE,
               'Unsafe source file')
        raw = bytearray()
        while len(raw) <= MAX_FILE:
            chunk = os.read(fd, min(1048576, MAX_FILE + 1 - len(raw)))
            if not chunk:
                break
            raw.extend(chunk)
        after = host.metadata(fd)
        stable = ('st_dev', 'st_ino', 'st_mode', 'st_uid', 'st_gid', 'st_nlink',
                  'st_size', 'st_mtime_ns', 'st_ctime_ns')
        _check(all(getattr(before, k) == getattr(after, k) for k in stable)
               and len(raw) == before.st_size and len(raw) <= MAX_FILE,
               'Source changed during capture')
        return bytes(raw), 0o555 if before.st_mode & 0o111 else 0o444
    finally:
        os.close(fd)


def _capture(host, source_pins, dependency_pins):
    files, directories = {}, set()
    total = 0
    def add(directory, name, target, pin):
        nonlocal total
        data, mode = _read(host, directory, name)
        total += len(data)
        _check(total <= MAX_TOTAL and _hash(data) == pin, 'Closure pin/size mismatch')
        files[target] = (data, mode)
    with host.directory(SOURCE) as source:
        for path, pin in sorted(source_pins.items()):
            # All intermediate components are pinned nofollow directory descriptors.
            fd = os.dup(source)
            try:
                for part in path.split('/')[:-1]:
                    new = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=fd)
                    os.close(fd)
                    fd = new
                    host.controlled(fd)
                add(fd, path.split('/')[-1], path, pin)
                _check(0 < len(files[path][0]) <= MAX_JSON)
                # The fixed consumer requires all seven source files at 0444.
                files[path] = (files[path][0], 0o444)
            finally:
                os.close(fd)
    seen = set()
    entries = 0
    def walk(fd, prefix='', depth=0):
        nonlocal entries
        _check(depth < 20)
        for name in sorted(os.listdir(fd)):
            entries += 1
            _check(entries <= MAX_ENTRIES)
            path = prefix + name
            _check(_path(path))
            s = os.stat(name, dir_fd=fd, follow_symlinks=False)
            if stat.S_ISDIR(s.st_mode):
                child = os.open(name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=fd)
                try:
                    host.controlled(child)
                    directories.add('venv/' + path)
                    walk(child, path + '/', depth + 1)
                finally:
                    os.close(child)
            else:
                _check(path in dependency_pins, 'Unpinned dependency')
                add(fd, name, 'venv/' + path, dependency_pins[path])
                seen.add(path)
    with host.directory(VENV) as venv:
        directories.add('venv')
        walk(venv)
    _check(seen == set(dependency_pins), 'Missing dependency')
    _check(files['venv/bin/python'][0] and files['venv/bin/python'][1] == 0o555,
           'Interpreter must be nonempty and executable')
    # Preserve original pyvenv.cfg. The external stdlib/interpreter home must be
    # an existing canonical root-controlled system directory, never the candidate.
    cfg = files['venv/pyvenv.cfg'][0].decode('utf-8')
    homes = [line.split('=', 1)[1].strip() for line in cfg.splitlines()
             if line.split('=', 1)[0].strip() == 'home' and '=' in line]
    _check(len(homes) == 1 and homes[0].startswith(('/usr/', '/lib/')))
    with host.directory(homes[0]):
        pass
    for path in files:
        parent = PurePosixPath(path).parent
        while str(parent) != '.':
            directories.add(str(parent))
            parent = parent.parent
    manifest = {'version': 1, 'sourceHead': SOURCE_HEAD, 'source': SOURCE, 'dependencies': VENV,
                'directories': sorted(directories), 'files': {
                    p: {'sha256': _hash(data), 'mode': mode, 'size': len(data)}
                    for p, (data, mode) in sorted(files.items())}}
    return manifest, files


def prepare(config_bytes, *, config_sha256, source_pins, dependency_pins, _host=None):
    """Return canonical manifest bytes; caller retains its independently passed digest.

    No UID, config field or returned manifest asserts owner review/admission.
    Inputs must already have been qualified outside this module.
    """
    host = _host or _Host()
    _check(all(uid != 0 for uid in host.identity()), 'Prepare must be unprivileged')
    _config(config_bytes, config_sha256, source_pins, dependency_pins)
    manifest, _ = _capture(host, source_pins, dependency_pins)
    manifest['configSha256'] = config_sha256
    raw = _wire(manifest)
    _check(len(raw) <= MAX_MANIFEST)
    return raw


def _absent(fd, name):
    try:
        os.stat(name, dir_fd=fd, follow_symlinks=False)
    except FileNotFoundError:
        return
    raise InstallError('Existing target or receipt; preserve and reconcile')


def _write(host, fd, name, data, mode, gid=0):
    out = os.open(name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
                  0o600, dir_fd=fd)
    try:
        with os.fdopen(out, 'wb', closefd=False) as stream:
            stream.write(data)
            stream.flush()
            host.owner(out, 0, gid)
            os.fchmod(out, mode)
            os.fsync(out)
    finally:
        os.close(out)
    os.fsync(fd)


def _mkdir(host, fd, name, mode=0o755, uid=0, gid=0):
    os.mkdir(name, 0o700, dir_fd=fd)
    child = os.open(name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=fd)
    try:
        host.controlled(child)
        host.owner(child, uid, gid)
        os.fchmod(child, mode)
        os.fsync(child)
    finally:
        os.close(child)
    os.fsync(fd)


def install(prepared_manifest, *, prepared_sha256, config_bytes, config_sha256,
            source_pins, dependency_pins, _host=None):
    """One trusted-owner invocation. No overwrite, rollback, repair or replay.

    All source bytes are captured and revalidated before intent. A crash retains
    intent/partial targets for operator reconciliation, never a successful claim.
    No Controller state, binding, repository claim or lock is initialized here.
    """
    host = _host or _Host()
    _check(host.identity() == (0, 0), 'Root owner required')
    _check(_hex(prepared_sha256) and type(prepared_manifest) is bytes
           and 0 < len(prepared_manifest) <= MAX_MANIFEST
           and _hash(prepared_manifest) == prepared_sha256, 'Independent prepare pin required')
    _parse(prepared_manifest, MAX_MANIFEST)
    _config(config_bytes, config_sha256, source_pins, dependency_pins)
    manifest, files = _capture(host, source_pins, dependency_pins)
    manifest['configSha256'] = config_sha256
    _check(_wire(manifest) == prepared_manifest, 'Prepared closure changed')
    with host.directory('/opt') as opt, host.directory(CONFIG_DIR) as config, host.directory(STATE) as state:
        s = host.metadata(config)
        _check(s.st_uid == 0 and s.st_gid == 976 and stat.S_IMODE(s.st_mode) == 0o750)
        _absent(opt, 'offmenu-publisher')
        _absent(config, 'config.json')
        _absent(state, RECEIPT)
        # Existing dedicated state may be accepted only if pristine and exact.
        claim = None
        try:
            try:
                claim = os.open('integration', os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=state)
            except FileNotFoundError:
                pass
            if claim is not None:
                _pristine(host, claim, {'current'})
                if os.listdir(claim):
                    current = os.open('current', os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=claim)
                    try:
                        _pristine(host, current, set())
                    finally:
                        os.close(current)
            intent = _wire({'version': 1, 'effect': 'intent', 'preparedSha256': prepared_sha256,
                            'configSha256': config_sha256}) + b'\n'
            _write(host, state, RECEIPT, intent, 0o600)
            _mkdir(host, opt, 'offmenu-publisher')
            with host.directory(TARGET):
                for path in sorted(manifest['directories'], key=lambda p: (p.count('/'), p)):
                    parent, name = str(PurePosixPath(path).parent), PurePosixPath(path).name
                    with host.directory(TARGET + ('' if parent == '.' else '/' + parent)) as fd:
                        _mkdir(host, fd, name)
                for path, (data, mode) in sorted(files.items()):
                    with host.directory(TARGET + '/' + str(PurePosixPath(path).parent)) as fd:
                        _write(host, fd, PurePosixPath(path).name, data, mode)
            _write(host, config, 'config.json', config_bytes, 0o440, 976)
            if claim is None:
                _mkdir(host, state, 'integration', 0o700, 984, 976)
                claim = os.open('integration', os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=state)
            if not os.listdir(claim):
                _mkdir(host, claim, 'current', 0o700, 984, 976)
            # Receipt deliberately remains an intent. Installed bytes are not BAU
            # acceptance, and any later call is refused, including after success.
            return {'preparedSha256': prepared_sha256, 'effect': 'files-installed'}
        finally:
            if claim is not None:
                os.close(claim)


def _pristine(host, fd, allowed):
    s = host.metadata(fd)
    _check(stat.S_ISDIR(s.st_mode) and s.st_uid == 984 and s.st_gid == 976
           and stat.S_IMODE(s.st_mode) == 0o700 and set(os.listdir(fd)) <= allowed,
           'Existing publisher state held')
