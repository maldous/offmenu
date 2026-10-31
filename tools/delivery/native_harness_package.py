"""Unprivileged exact package producer and separately admitted fixed-slot copier.

No CLI, payload imports, service operation, credential or first-install action.
The package digest is content identity, never independent review or permission.
"""
import ast
import base64
import csv
from dataclasses import dataclass
from email.parser import BytesParser
import hashlib
import io
import json
import os
from pathlib import Path, PurePosixPath
import re
import stat
import sys
import time

from packaging.requirements import Requirement
from packaging.utils import canonicalize_name
import protected_owner_install as protected

ROLES = ('owner_source', 'owner_venv', 'owner_config', 'publisher', 'publisher_config')
TARGETS = {'owner_source': '/opt/offmenu-stokowski-current/source',
           'owner_venv': '/opt/offmenu-stokowski-current/venv',
           'owner_config': '/etc/offmenu-stokowski-current',
           'publisher': '/opt/offmenu-publisher',
           'publisher_config': '/etc/offmenu-publisher/config.json'}
MAX_FILES = 50000
MAX_TOTAL = 1024**3
PYTHON = 'lib/python3.12/site-packages/'
ROOT_DISTRIBUTIONS = ('stokowski', 'langgraph', 'langgraph-checkpoint-sqlite', 'jsonschema')


def require(ok, reason):
    if not ok:
        raise ValueError(reason)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def pin(value):
    require(type(value) is str and re.fullmatch('[0-9a-f]{64}', value), 'sha256')
    return value


def bounded(raw, limit=protected.MAX_FILE):
    require(type(raw) is bytes and len(raw) <= limit, 'byte_bound')
    return raw


def path_name(name):
    require(type(name) is str and len(name) <= 1024 and '\\' not in name, 'relative_path')
    protected.relative(name)
    require(not any(p.startswith('.env') or p in ('credentials', 'auth.json', 'credentials.json')
                    or p.endswith(('.key', '.log')) or p.endswith('.pem') and name not in
                    ('certifi/cacert.pem', PYTHON + 'certifi/cacert.pem',
                     'venv/' + PYTHON + 'certifi/cacert.pem') for p in name.split('/')), 'private_path')
    return name


def nofollow(root, name):
    """Read immutable-looking bounded regular bytes without following any link."""
    path_name(name)
    fd = os.open(root, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        for part in name.split('/')[:-1]:
            child = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=fd)
            os.close(fd)
            fd = child
        return protected.regular(name.split('/')[-1], dir_fd=fd)
    finally:
        os.close(fd)


def excluded_record(name):
    parts = PurePosixPath(name).parts
    return (not name or name.startswith('/') or '\\' in name or '..' in parts
            or name.endswith(('.pth', '.egg-link', '.pyc', '.pyo'))
            or '__pycache__' in parts)


def selected_distribution_files(site, *, lock_bytes, upstream, metadata_pins):
    """RECORD-selected existing bytes. Pins are independently supplied, not learned.

    metadata_pins covers every selected METADATA, RECORD and unhashed metadata
    entry. RECORD hashes are additional integrity checks, not upstream authority.
    Stokowski upstream is {version, source_revision, files:{site-relative:sha256}}.
    No executable/bootstrap .pth or scripts outside site-packages enter output.
    """
    require(type(lock_bytes) is list and 1 <= len(lock_bytes) <= 4, 'locks')
    locks = {}
    for raw in lock_bytes:
        for line in bounded(raw, 1024*1024).decode().splitlines():
            if not line.strip() or line.startswith('#'):
                continue
            require(re.fullmatch(r'[A-Za-z0-9_.-]+==[A-Za-z0-9_.+-]+', line), 'lock_line')
            name, version = line.split('==')
            name = canonicalize_name(name)
            require(name not in locks or locks[name] == version, 'lock_conflict')
            locks[name] = version
    require(type(upstream) is dict and set(upstream) == {'version', 'source_revision', 'files'}
            and upstream['version'] == '1.1.0'
            and re.fullmatch('[0-9a-f]{40}', upstream['source_revision'])
            and type(upstream['files']) is dict and upstream['files'], 'upstream_pin')
    locks['stokowski'] = upstream['version']
    site = Path(site)
    require(site == site.resolve(strict=True), 'site_link')
    require(type(metadata_pins) is dict and len(metadata_pins) <= MAX_FILES, 'metadata_pins')
    installed = {}
    # Read only independently pinned distribution metadata, never arbitrary files.
    for name in sorted(metadata_pins):
        path_name(name)
        pin(metadata_pins[name])
        if not name.endswith('.dist-info/METADATA'):
            continue
        raw = nofollow(site, name)
        require(sha(raw) == metadata_pins[name], 'metadata_drift')
        meta = BytesParser().parsebytes(raw)
        distribution = canonicalize_name(meta['Name'] or '')
        require(distribution and distribution not in installed, 'distribution_collision')
        installed[distribution] = (name.rsplit('/', 1)[0], meta)
    queue, selected, output, records, omitted = list(ROOT_DISTRIBUTIONS), {}, {}, {}, []
    total = 0
    used_pins = set()
    while queue:
        name = canonicalize_name(queue.pop())
        if name in selected:
            continue
        require(name in locks and name in installed, 'unqualified_dependency')
        directory, meta = installed[name]
        require(meta['Version'] == locks[name], 'version_pin')
        selected[name] = locks[name]
        used_pins.add(directory + '/METADATA')
        for raw in meta.get_all('Requires-Dist', []):
            requirement = Requirement(raw)
            if requirement.marker and not requirement.marker.evaluate({'extra': ''}):
                continue
            require(not requirement.url and not requirement.extras, 'dependency_extras_or_url')
            dep = canonicalize_name(requirement.name)
            require(dep in locks and locks[dep] in requirement.specifier, 'dependency_constraint')
            queue.append(dep)
        record_name = directory + '/RECORD'
        require(record_name in metadata_pins, 'record_pin_required')
        record = nofollow(site, record_name)
        require(sha(record) == metadata_pins[record_name], 'record_drift')
        used_pins.add(record_name)
        records[name] = {'path': record_name, 'sha256': sha(record)}
        row_names = set()
        for row in csv.reader(io.StringIO(record.decode())):
            require(len(row) == 3, 'record_row')
            relative, digest, size = row
            require(relative not in row_names, 'record_duplicate')
            row_names.add(relative)
            if excluded_record(relative):
                omitted.append({'distribution': name, 'path': relative})
                continue
            path_name(relative)
            raw = nofollow(site, relative)
            if digest:
                require(digest.startswith('sha256='), 'record_hash_algorithm')
                expected = base64.urlsafe_b64encode(hashlib.sha256(raw).digest()).decode().rstrip('=')
                require(digest[7:] == expected and size.isdecimal() and int(size) == len(raw), 'record_hash_size')
            else:
                require(relative.startswith(directory + '/') and relative in metadata_pins
                        and sha(raw) == metadata_pins[relative], 'unhashed_record_pin')
                require(not size or (size.isdecimal() and int(size) == len(raw)), 'record_size')
                used_pins.add(relative)
            # A namespace may be shared, but conflicting bytes are never overwritten.
            target = PYTHON + relative
            require(target not in output or output[target] == raw, 'distribution_file_collision')
            if target not in output:
                total += len(raw)
                output[target] = raw
            require(len(output) <= MAX_FILES and total <= MAX_TOTAL, 'dependency_bounds')
        require(directory + '/METADATA' in row_names and record_name in row_names, 'incomplete_record')
    for name, expected in upstream['files'].items():
        path_name(name)
        require(name.startswith('stokowski/') and PYTHON + name in output
                and sha(output[PYTHON + name]) == pin(expected), 'upstream_source_drift')
    actual_stokowski = {p[len(PYTHON):] for p in output if p.startswith(PYTHON + 'stokowski/')}
    require(actual_stokowski == set(upstream['files']), 'upstream_source_closure')
    return output, {'versions': dict(sorted(selected.items())), 'records': records,
                    'omitted': omitted, 'metadata_pins': {n: metadata_pins[n] for n in sorted(used_pins)},
                    'lock_sha256': [sha(raw) for raw in lock_bytes], 'upstream': upstream}


def publisher_sources(source):
    """Finite delivery import closure; no execution or legacy eleven-file shortcut.

    Include every maintained delivery Python module to cover fixed RPC strings
    and lifecycle hooks, then resolve their static local imports. Unknown dynamic
    imports require an explicit source change/review rather than assumed closure.
    """
    roots = {p for p in source if (p.startswith('tools/delivery/') and p.endswith('.py'))
             or (p.startswith('src/offmenu/delivery/') and p.endswith('.py'))}
    roots |= {'src/offmenu/__init__.py', 'tools/delivery/github-app-publisher.mjs',
              'tools/delivery/github-app-adapter.mjs', 'tools/delivery/integration-gateway.mjs',
              'contracts/schemas/delivery-handoff-v1.schema.json',
              'config/delivery-release-policy.json', 'config/release-validation-profile.json',
              'tools/delivery/capacity-policy.json'}
    require(roots <= set(source), 'publisher_root_missing')
    found, queue = {}, list(roots)
    while queue:
        name = queue.pop()
        if name in found:
            continue
        raw = source[name]
        found[name] = raw
        if name.endswith('.py'):
            tree = ast.parse(raw, filename=name)
            package = name[:-3].split('/')
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    modules = [n.name for n in node.names]
                elif isinstance(node, ast.ImportFrom):
                    prefix = package[:-node.level] if node.level else []
                    modules = ['.'.join(prefix + ([node.module] if node.module else []))]
                    if node.level and node.module is None:
                        modules += ['.'.join(prefix + [n.name]) for n in node.names]
                elif isinstance(node, ast.Call) and (isinstance(node.func, ast.Name) and node.func.id == '__import__'
                        or isinstance(node.func, ast.Attribute) and node.func.attr == 'import_module'):
                    require(node.args and isinstance(node.args[0], ast.Constant)
                            and type(node.args[0].value) is str, 'unknown_dynamic_import')
                    modules = [node.args[0].value]
                else:
                    continue
                for module in modules:
                    base = module.replace('.', '/')
                    candidates = [base + '.py', base + '/__init__.py',
                                  'src/' + base + '.py', 'src/' + base + '/__init__.py',
                                  'tools/delivery/' + base + '.py']
                    internal = (isinstance(node, ast.ImportFrom) and node.level
                                or module.startswith(('offmenu.', 'native_', 'stokowski_', 'symphony_', 'windmill_')))
                    require(not internal or any(t in source for t in candidates), 'internal_import_missing')
                    for target in candidates:
                        if target in source and target not in found:
                            queue.append(target)
        elif name.endswith('.mjs'):
            text = raw.decode()
            require(not re.search(r'\bimport\(\s*[^\s\'\"]', text), 'dynamic_js_import')
            for local in re.findall(r'(?:from\s*|import\(\s*)[\'\"](\.[^\'\"]+)[\'\"]', text):
                relative = PurePosixPath(name).parent / local
                require('..' not in relative.parts, 'js_import_escape')
                target = str(relative)
                require(target in source, 'local_js_import_missing')
                queue.append(target)
    return found


def publisher_descriptor(files, *, head, tree, node_sha256):
    """Shared UIF122 descriptor; byte digest domain, never shared fingerprint."""
    required = {'tools/delivery/native_publisher_invocation.py',
                'tools/delivery/windmill_runner.py', 'tools/delivery/capacity-policy.json',
                'tools/delivery/protected_owner_install.py', 'venv/bin/python'}
    require(type(files) is dict and required <= set(files) and len(files) <= 50000
            and 'native-harness-closure.json' not in files, 'publisher_descriptor_closure')
    require(type(head) is str and re.fullmatch('[0-9a-f]{40}', head)
            and type(tree) is str and re.fullmatch('[0-9a-f]{40}', tree), 'descriptor_source')
    pins = {}
    for name, raw in sorted(files.items()):
        path_name(name)
        pins[name] = sha(bounded(raw))
    value = dict(version=1, kind='native-publisher-closure-v1', source_head=head,
                 source_tree=tree, node_sha256=pin(node_sha256), files=pins)
    raw = protected.encoded(value)
    require(len(raw) <= 16*1024*1024, 'descriptor_bound')
    return raw


@dataclass(frozen=True)
class PackageAcceptance:
    """Owner context supplied after independent source review, never worker JSON."""
    owner: str
    head: str
    tree: str
    review: dict


def file_policy(role, name):
    path_name(name)
    if role == 'publisher_config':
        require(name == 'config.json', 'publisher_config_file_only')
        return 0o440, 0, 976
    if role in ('owner_venv', 'publisher') and (role == 'owner_venv' or name.startswith('venv/')):
        relative = name if role == 'owner_venv' else name[5:]
        require(relative in ('bin/python', 'pyvenv.cfg') or relative.startswith(PYTHON)
                and not excluded_record(relative), 'dependency_role_path')
    if role == 'owner_config':
        require(name in ('current.json', 'catalog.json', 'binding.json'), 'owner_config_file')
    return (0o555 if (role == 'owner_venv' and name == 'bin/python')
            or (role == 'publisher' and name == 'venv/bin/python') else 0o444), 0, 0


def closure(role, files):
    require(role in ROLES and type(files) is dict and files, 'fixed_role')
    directories, entries = {}, {}
    for name, raw in sorted(files.items()):
        bounded(raw)
        mode, uid, gid = file_policy(role, name)
        entries[name] = dict(mode=mode, uid=uid, gid=gid, size=len(raw), sha256=sha(raw))
        if role == 'publisher_config':
            continue
        parent = PurePosixPath(name).parent
        while True:
            key = '' if str(parent) == '.' else str(parent)
            require(key not in entries, 'file_directory_collision')
            directories[key] = dict(mode=0o755, uid=0, gid=0)
            if not key:
                break
            parent = parent.parent
    require(not set(directories) & set(entries), 'file_directory_collision')
    return dict(directories=directories, files=entries)


def prepare_coherent_package(stage, *, git_dir, head, tree, dependencies,
                             dependency_evidence, dependency_sha256, runtime, interpreter, interpreter_sha256,
                             interpreter_custody, node_sha256, node_custody, pyvenv_cfg, owner_current, owner_catalog,
                             publisher_config, config_pins, acceptance):
    """Build only actor-owned private content-addressed payload; no /opt reads."""
    require(os.getuid() != 0 and os.geteuid() != 0, 'nonroot_producer')
    require(type(acceptance) is PackageAcceptance and acceptance.owner.strip()
            and (acceptance.head, acceptance.tree) == (head, tree), 'source_acceptance')
    require(set(acceptance.review) == {'path', 'sha256'}, 'review_reference')
    path_name(acceptance.review['path']); pin(acceptance.review['sha256'])
    require(type(interpreter_custody) is dict and set(interpreter_custody) == {'path', 'sha256'}, 'custody_reference')
    path_name(interpreter_custody['path']); pin(interpreter_custody['sha256'])
    pin(node_sha256)
    require(type(node_custody) is dict and set(node_custody) == {'path', 'sha256'}, 'node_custody_reference')
    path_name(node_custody['path']); pin(node_custody['sha256'])
    require(sha(bounded(interpreter)) == pin(interpreter_sha256), 'interpreter_pin')
    cfg = dict(line.split('=', 1) for line in bounded(pyvenv_cfg, 65536).decode().splitlines() if '=' in line)
    cfg = {k.strip(): v.strip() for k, v in cfg.items()}
    require(cfg.get('include-system-site-packages') == 'false' and cfg.get('version', '').startswith('3.12.')
            and cfg.get('home') in ('/bin', '/usr/bin'), 'qualified_python_cfg')
    actual_tree, source_pairs, metadata = protected.git_closure(git_dir, head)
    require(actual_tree == tree, 'source_tree')
    source = {name: raw for name, (raw, _) in dict(source_pairs, **metadata).items()}
    protected.validate_git_payload({str(protected.SOURCE / n): raw for n, raw in source.items()},
                                   dict(head=head, tree=tree))
    require(type(dependencies) is dict and dependencies, 'dependencies')
    require(sha(protected.encoded({n: sha(raw) for n, raw in sorted(dependencies.items())}))
            == pin(dependency_sha256), 'dependency_projection_pin')
    for name, raw in dependencies.items():
        require(name.startswith(PYTHON) and not excluded_record(name), 'dependency_path')
        bounded(raw); path_name(name)
    require(set(config_pins) == {'owner_current', 'owner_catalog', 'publisher_config'}, 'config_pins')
    for key, raw in [('owner_current', owner_current), ('owner_catalog', owner_catalog), ('publisher_config', publisher_config)]:
        require(sha(bounded(raw, 1024*1024)) == pin(config_pins[key]), 'config_input_pin')
    current, catalog, publisher = [protected.record(raw) for raw in (owner_current, owner_catalog, publisher_config)]
    require(current.get('source_head') == head and current.get('catalog') == '/etc/offmenu-stokowski-current/catalog.json'
            and publisher.get('sourceHead') == head and publisher.get('publisherUid') == 984
            and publisher.get('publisherGid') == 976 and publisher.get('repositoryId') == 1416253963,
            'coherent_config_identity')
    for config, key in ((current, 'source_sha256'), (publisher, 'codePins')):
        require(type(config.get(key)) is dict and config[key], 'config_source_pins')
        for name, expected in config[key].items():
            require(name in source and sha(source[name]) == pin(expected), 'config_source_drift')
    require(publisher.get('pythonSha256') == interpreter_sha256, 'publisher_python')
    require(set(catalog) == {'version', 'entries'} and catalog['version'] == 1
            and type(catalog['entries']) is list, 'catalog')
    require(type(runtime) is str and runtime.startswith('/') and '..' not in Path(runtime).parts
            and str(Path(runtime)) == runtime and type(current.get('runtime_root')) is str
            and Path(runtime).is_relative_to(current['runtime_root'])
            and Path(runtime) != Path(current['runtime_root']), 'runtime_binding')
    binding = dict(schema='protected-current-owner-v1', runtime=runtime,
                   config_sha256=sha(owner_current), catalog_sha256=sha(owner_catalog),
                   source_root=str(protected.SOURCE), python_sha256=interpreter_sha256)
    env = dict(dependencies, **{'bin/python': interpreter, 'pyvenv.cfg': pyvenv_cfg})
    publisher_source = publisher_sources(source)
    require(set(publisher['codePins']) <= set(publisher_source), 'publisher_pin_closure')
    roles = {'owner_source': source, 'owner_venv': env,
             'owner_config': {'current.json': owner_current, 'catalog.json': owner_catalog,
                              'binding.json': protected.encoded(binding)},
             'publisher': dict(publisher_source, **{'venv/' + n: raw for n, raw in env.items()}),
             'publisher_config': {'config.json': publisher_config}}
    roles['publisher']['native-harness-closure.json'] = publisher_descriptor(
        roles['publisher'], head=head, tree=tree, node_sha256=node_sha256)
    all_files = sum(len(f) for f in roles.values())
    total = sum(len(raw) for files in roles.values() for raw in files.values())
    require(all_files <= MAX_FILES and total <= MAX_TOTAL, 'package_bounds')
    manifest = dict(version=1, kind='native-harness-package-v1', owner=acceptance.owner,
                    head=head, tree=tree, review=acceptance.review,
                    interpreter_custody=interpreter_custody, node_custody=node_custody,
                    dependency_evidence=dependency_evidence,
                    roles={role: closure(role, files) for role, files in roles.items()})
    raw = protected.encoded(manifest)
    require(len(raw) <= 32*1024*1024, 'package_manifest_bound')
    stage = Path(stage)
    require(stage.parent == stage.parent.resolve(strict=True), 'stage_parent')
    info = stage.parent.stat()
    require(info.st_uid == os.getuid() and info.st_mode & 0o077 == 0, 'private_stage_parent')
    stage.mkdir(mode=0o700)  # create-only; interrupted output is retained, never reused
    (stage / 'payload').mkdir(mode=0o700)
    written = set()
    for files in roles.values():
        for content in files.values():
            key = sha(content)
            if key not in written:
                protected.write_new(stage / 'payload' / key, content, 0o400)
                written.add(key)
    protected.sync_dir(stage / 'payload')
    protected.write_new(stage / 'manifest.json', raw, 0o400)
    protected.sync_dir(stage)
    return {'path': str(stage), 'sha256': sha(raw), 'roles': manifest['roles']}


@dataclass(frozen=True)
class MaterializeAdmission:
    """Sole root-owner loader supplies this after review and actual host approval.

    This capability is never constructed from package/request JSON by this module.
    """
    owner: str
    package_sha256: str
    operation_id: str
    host_confirmation_sha256: str
    expires_at: float


def slots(operation):
    pin(operation)
    result = {}
    for role, target in TARGETS.items():
        parent = str(Path(target).parent)
        suffix = '.new.json' if role == 'publisher_config' else '.new'
        result[role] = parent + '/.native-upgrade-' + operation + '-' + role + suffix
    return result


class MaterializeHost:
    """No payload commands. The private /tmp mapping is disposable test-only."""
    def __init__(self, *, _synthetic=None):
        self.synthetic = _synthetic is not None
        self.root = Path(_synthetic).resolve(strict=True) if self.synthetic else Path('/')
        require((self.synthetic and self.root.is_relative_to('/tmp') and self.root != Path('/tmp')
                 and os.geteuid() != 0) or (not self.synthetic and os.getuid() == os.geteuid() == 0),
                'actual_root_owner_required')

    def path(self, absolute):
        require(type(absolute) is str and absolute.startswith('/'), 'fixed_absolute')
        protected.relative(absolute[1:])
        result = self.root / absolute[1:]
        for directory in (result.parent, *result.parent.parents):
            if not directory.is_relative_to(self.root):
                continue
            info = directory.lstat()
            require(stat.S_ISDIR(info.st_mode) and info.st_uid == (os.getuid() if self.synthetic else 0)
                    and not info.st_mode & 0o022, 'root_parent_custody')
        return result

    def uid_gid(self, uid, gid):
        return (os.getuid(), os.getgid()) if self.synthetic else (uid, gid)

    def write(self, absolute, raw, mode, uid=0, gid=0):
        target = self.path(absolute)
        protected.write_new(target, raw, mode)
        actual_uid, actual_gid = self.uid_gid(uid, gid)
        if not self.synthetic:
            os.chown(target, actual_uid, actual_gid, follow_symlinks=False)
        os.chmod(target, mode, follow_symlinks=False)
        fd = os.open(target, os.O_RDONLY | os.O_NOFOLLOW)
        try:
            os.fsync(fd)
        finally:
            os.close(fd)
        protected.sync_dir(target.parent)

    def mkdir(self, absolute):
        target = self.path(absolute)
        target.mkdir(mode=0o755)
        os.chmod(target, 0o755)
        protected.sync_dir(target.parent)

    def verify(self, absolute, role, expected):
        root = self.path(absolute)
        if role == 'publisher_config':
            actual = {'config.json': protected.regular(root)}
        else:
            require(root.is_dir() and not root.is_symlink(), 'stage_directory')
            actual = {}
            seen_dirs = {''}
            for path in root.rglob('*'):
                name = path.relative_to(root).as_posix()
                info = path.lstat()
                require(not stat.S_ISLNK(info.st_mode), 'stage_link')
                if stat.S_ISDIR(info.st_mode):
                    seen_dirs.add(name)
                else:
                    actual[name] = nofollow(root, name)
            require(seen_dirs == set(expected['directories']), 'stage_directories')
            for name, item in expected['directories'].items():
                info = (root / name).lstat()
                uid, gid = self.uid_gid(item['uid'], item['gid'])
                require((stat.S_IMODE(info.st_mode), info.st_uid, info.st_gid)
                        == (item['mode'], uid, gid), 'stage_directory_metadata')
        require(set(actual) == set(expected['files']), 'stage_file_set')
        for name, raw in actual.items():
            item = expected['files'][name]
            path = root if role == 'publisher_config' else root / name
            info = path.lstat()
            uid, gid = self.uid_gid(item['uid'], item['gid'])
            require(sha(raw) == item['sha256'] and len(raw) == item['size']
                    and (stat.S_IMODE(info.st_mode), info.st_uid, info.st_gid)
                    == (item['mode'], uid, gid), 'stage_file_metadata')


def read_package(package, expected_sha256):
    """Bound every payload before privileged intent; extras and links fail closed."""
    package = Path(package)
    require(package == package.resolve(strict=True), 'package_root_link')
    raw = nofollow(package, 'manifest.json')
    require(len(raw) <= 32*1024*1024, 'package_manifest_bound')
    require(sha(raw) == pin(expected_sha256), 'reviewed_package_pin')
    manifest = protected.record(raw)
    require(set(manifest) == {'version', 'kind', 'owner', 'head', 'tree', 'review',
                            'interpreter_custody', 'node_custody', 'dependency_evidence', 'roles'}
            and type(manifest['version']) is int and manifest['version'] == 1
            and manifest['kind'] == 'native-harness-package-v1'
            and type(manifest['owner']) is str and manifest['owner'].strip()
            and set(manifest['roles']) == set(ROLES), 'package_schema')
    content, payload_keys, total = {}, set(), 0
    for role in ROLES:
        value = manifest['roles'][role]
        require(type(value) is dict and set(value) == {'directories', 'files'}
                and type(value['files']) is dict and 0 < len(value['files']) <= MAX_FILES, 'role_closure')
        files = {}
        for name, item in value['files'].items():
            path_name(name)
            require(set(item) == {'mode', 'uid', 'gid', 'size', 'sha256'}, 'file_fields')
            key = pin(item['sha256'])
            raw = nofollow(package, 'payload/' + key)
            require(sha(raw) == key and type(item['size']) is int and len(raw) == item['size'], 'payload_pin')
            files[name] = raw
            payload_keys.add(key)
            total += len(raw)
            require(total <= MAX_TOTAL, 'package_total')
        require(protected.encoded(value) == protected.encoded(closure(role, files)), 'fixed_role_metadata')
        content[role] = files
    require(sum(len(f) for f in content.values()) <= MAX_FILES, 'package_file_count')
    require(set(os.listdir(package)) == {'manifest.json', 'payload'}
            and set(os.listdir(package / 'payload')) == payload_keys, 'package_extra_entry')
    require(type(manifest['head']) is str and re.fullmatch('[0-9a-f]{40}', manifest['head'])
            and type(manifest['tree']) is str and re.fullmatch('[0-9a-f]{40}', manifest['tree']), 'git_pins')
    protected.validate_git_payload({str(protected.SOURCE / n): raw for n, raw in content['owner_source'].items()},
                                   {'head': manifest['head'], 'tree': manifest['tree']})
    # Source/dependency/config bytes may not diverge across the two installed roles.
    selected = publisher_sources(content['owner_source'])
    expected = dict(selected, **{'venv/' + n: raw for n, raw in content['owner_venv'].items()})
    require('native-harness-closure.json' in content['publisher'], 'publisher_descriptor_missing')
    descriptor = protected.record(content['publisher']['native-harness-closure.json'])
    expected['native-harness-closure.json'] = publisher_descriptor(
        expected, head=manifest['head'], tree=manifest['tree'], node_sha256=descriptor.get('node_sha256'))
    require(content['publisher'] == expected, 'publisher_closure_mismatch')
    return manifest, content


def materialize(package, *, expected_sha256, admission, _host=None):
    """One create-only fixed-slot copy; partial effects require owner reconciliation.

    Does not install, swap current targets, execute payload, read old config/key,
    start a service, or create permission from worker JSON. Never replay an intent.
    """
    require(type(admission) is MaterializeAdmission, 'typed_root_admission_required')
    now = time.time()
    require(type(admission.expires_at) in (int, float) and now < admission.expires_at <= now + 300,
            'fresh_admission')
    require(admission.package_sha256 == pin(expected_sha256), 'admission_package')
    pin(admission.host_confirmation_sha256)
    positions = slots(admission.operation_id)
    manifest, content = read_package(package, expected_sha256)
    require(admission.owner == manifest['owner'], 'admission_owner')
    host = _host or MaterializeHost()
    require(type(host) is MaterializeHost, 'fixed_materialize_host')
    intent = '/var/lib/offmenu-publisher/native-package-' + admission.operation_id + '.intent.json'
    # No mutation until every input, parent and destination is qualified.
    require(not os.path.lexists(host.path(intent)), 'prior_materialization_no_replay')
    for destination in positions.values():
        require(not os.path.lexists(host.path(destination)), 'stage_slot_exists')
    host.write(intent, protected.encoded({'kind': 'native-package-materialize-intent-v1',
               'package_sha256': expected_sha256, 'operation_id': admission.operation_id,
               'host_confirmation_sha256': admission.host_confirmation_sha256}), 0o600)
    for role, destination in positions.items():
        require(time.time() < admission.expires_at, 'admission_expired')
        if role == 'publisher_config':
            host.write(destination, content[role]['config.json'], 0o440, 0, 976)
        else:
            host.mkdir(destination)
            for name in sorted(manifest['roles'][role]['directories'], key=lambda n: (n.count('/'), n)):
                if name:
                    host.mkdir(destination + '/' + name)
            for name, raw in content[role].items():
                mode, uid, gid = file_policy(role, name)
                host.write(destination + '/' + name, raw, mode, uid, gid)
        host.verify(destination, role, manifest['roles'][role])
    return {'kind': 'native-package-materialized-v1', 'package_sha256': expected_sha256,
            'operation_id': admission.operation_id, 'stages': positions, 'activated': False}
