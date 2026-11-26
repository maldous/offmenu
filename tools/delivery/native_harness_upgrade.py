"""Explicit owner-only sealed-closure upgrade; no CLI, service start or retry.

Production admission must come from the sole owner after independent review and
mandatory host approval. Python capability objects are not JSON authority. The
private _synthetic root seam is for disposable /tmp tests only. First-install
receipts are neither consumed nor changed. Partial effects never auto-roll back.
"""
from contextlib import ExitStack, contextmanager
import ctypes
from dataclasses import asdict, dataclass
import fcntl
import hashlib
import json
import os
import re
from pathlib import Path
import stat
import subprocess
import time

from native_harness_adoption import TARGETS, fields, require, sha, identifier
from native_harness_contract import fingerprint
import protected_owner_install as protected


STATE = '/var/lib/offmenu-publisher'
SERVICE = 'offmenu-stokowski-current.service'
PUBLISHER_KEY = 'github-app-private-key.pem'
PUBLIC_CA_PATHS = {
    'owner_venv': 'lib/python3.12/site-packages/certifi/cacert.pem',
    'publisher': 'venv/lib/python3.12/site-packages/certifi/cacert.pem',
}
MAX_FILES = 50000
MAX_FILE = 64 * 1024 * 1024
MAX_TOTAL = 1024 * 1024 * 1024
RUNTIME_FILES = ('capacity-policy.json', 'current-owner.json')
RUNTIME_LIMIT = 8 * 1024 * 1024


@dataclass(frozen=True)
class OwnerAdmission:
    """Trusted out-of-band exact-source permission; never load from worker JSON."""
    owner: str
    plan_sha256: str
    upgrade_sha256: str
    host_confirmation_sha256: str
    expires_at: float
    lock_custody_sha256: str | None = None
    publisher_config_custody_sha256: str | None = None
    public_ca_pins_sha256: str | None = None


@dataclass(frozen=True)
class PublicCARecordPin:
    """Owner-selected PUBLICRECORD/blob association, never inferred from payload."""
    role: str
    closure_sha256: str
    path: str
    blob_sha256: str
    public_record_sha256: str


@dataclass(frozen=True)
class PublisherConfigCustody:
    """Fixed directory/key metadata only. Never a key payload or path selector."""
    directory: 'NodeIdentity'
    key: 'NodeIdentity'
    key_size: int
    key_mtime_ns: int
    key_ctime_ns: int
    qualification_sha256: str
    observed_at: float


@dataclass(frozen=True)
class NodeIdentity:
    dev: int
    ino: int
    uid: int
    gid: int
    mode: int
    nlink: int


@dataclass(frozen=True)
class ParentCustody:
    path: str
    identity: NodeIdentity


@dataclass(frozen=True)
class LockRecord:
    role: str
    path: str
    parents: tuple[ParentCustody, ...]
    identity: NodeIdentity
    policy: str
    permitted_writers: tuple[str, ...]


@dataclass(frozen=True)
class LockCustody:
    """Root-qualified metadata, not worker-issued path or permission authority.

    Bindings and every permitted writer's quiescence must be qualified by the
    existing owner. Missing/denied metadata is never synthesized by this module.
    """
    runtime: str
    runtime_root: str
    config_manifest_sha256: str
    protected_binding_evidence_sha256: str
    writers_quiescence_sha256: str
    observed_at: float
    locks: tuple[LockRecord, ...]


def identity(info):
    return NodeIdentity(info.st_dev, info.st_ino, info.st_uid, info.st_gid,
                        stat.S_IMODE(info.st_mode), info.st_nlink)


@dataclass(frozen=True)
class Quiescence:
    """Owner-qualified native inflight observation under existing owner locks.

    The caller must obtain this from the actual native owners, not a status
    string in a coding receipt. This module cannot census arbitrary live jobs.
    """
    snapshot_sha256: str
    evidence_sha256: str
    observed_at: float
    inflight: int
    children_gone: bool
    unresolved_operation_ids: tuple


@dataclass(frozen=True)
class MutationWindow:
    admission: OwnerAdmission
    quiescence: Quiescence
    locks: LockCustody
    publisher: PublisherConfigCustody


def pure_mutation_time(window):
    """Final time-only gate: no filesystem/service reads or callbacks."""
    require(type(window) is MutationWindow, 'mutation_window_required')
    now = time.time()
    require(now < window.admission.expires_at, 'admission_expired')
    require(fresh(window.quiescence.observed_at, now), 'native_quiescence_required')
    require(fresh(window.locks.observed_at, now), 'lock_custody_stale')
    require(fresh(window.publisher.observed_at, now), 'publisher_custody_stale')


def upgrade_digest(value):
    raw = protected.encoded(value)
    require(len(raw) <= 32 * 1024 * 1024, 'upgrade_manifest_bound')
    return protected.sha(raw)


def fresh(value, now, seconds=300):
    return type(value) in (int, float) and 0 <= now - value <= seconds


def qualify_lock_custody(custody, admission, plan, observation, host, now):
    """Qualify only exact root-admitted existing metadata, never acquire it."""
    require(type(custody) is LockCustody and type(custody.locks) is tuple,
            'lock_custody_required')
    sha(admission.lock_custody_sha256)
    require(upgrade_digest(asdict(custody)) == admission.lock_custody_sha256,
            'lock_custody_admission')
    for pin in (custody.config_manifest_sha256, custody.protected_binding_evidence_sha256,
                custody.writers_quiescence_sha256):
        sha(pin)
    require(custody.runtime == plan['legacy_snapshot']['runtime_path']
            and custody.config_manifest_sha256 == plan['legacy_snapshot']['config_sha256']
            and type(observation) is Quiescence
            and custody.writers_quiescence_sha256 == observation.evidence_sha256
            and fresh(custody.observed_at, now), 'lock_custody_binding')
    for path in (custody.runtime, custody.runtime_root):
        require(type(path) is str and path.startswith('/') and len(path) <= 1024, 'lock_runtime')
        protected.relative(path[1:])
    require(Path(custody.runtime_root).name == 'stokowski'
            and Path(custody.runtime_root).parent.name == '.delivery'
            and custody.runtime.startswith(custody.runtime_root + '/'), 'shared_runtime_root')
    roles = ('runtime-coordinator', 'shared-root-coordinator', 'publisher-repository')
    paths = (custody.runtime + '/coordinator.lock', custody.runtime_root + '/coordinator.lock',
             STATE + '/integration/repository-owner.lock')
    require(len(custody.locks) == 3, 'three_existing_locks_required')
    file_ids, parents_seen = set(), {}

    def node(value, directory=False):
        require(type(value) is NodeIdentity and all(type(item) is int and item >= 0
                for item in asdict(value).values()) and value.ino > 0
                and value.mode <= 0o777 and not value.mode & 0o002
                and (value.nlink >= 1 if directory else value.nlink == 1), 'lock_metadata')

    for record, role, path in zip(custody.locks, roles, paths):
        require(type(record) is LockRecord and record.role == role and record.path == path
                and type(record.parents) is tuple and len(record.parents) <= 64,
                'fixed_lock_role')
        expected_parents = tuple(reversed([str(parent) for parent in Path(path).parents]))
        require(tuple(parent.path for parent in record.parents
                      if type(parent) is ParentCustody) == expected_parents, 'lock_parent_chain')
        publisher = role == 'publisher-repository'
        uid = host.uid if host.synthetic else (984 if publisher else 1000)
        gid = os.getegid() if host.synthetic else (976 if publisher else 1000)
        node(record.identity)
        require((record.identity.uid, record.identity.gid) == (uid, gid), 'lock_owner')
        historical = not publisher and record.policy == 'caller-historical-0664-v1'
        policy = 'publisher-existing-v1' if publisher else 'caller-private-v1'
        require(record.policy == policy or historical, 'lock_policy')
        require(record.identity.mode == (0o664 if historical else 0o600), 'lock_mode')
        writers = ('uid:' + str(uid), 'gid:' + str(gid)) if historical else ('uid:' + str(uid),)
        require(type(record.permitted_writers) is tuple and record.permitted_writers == writers,
                'lock_permitted_writers')
        key = (record.identity.dev, record.identity.ino)
        require(key not in file_ids, 'aliased_lock')
        file_ids.add(key)
        for parent in record.parents:
            node(parent.identity, True)
            previous = parents_seen.setdefault(parent.path, parent.identity)
            require(previous == parent.identity, 'conflicting_parent_pin')
            info = parent.identity
            require(info.mode & 0o100, 'lock_parent_access')
            if host.synthetic:
                require(info.uid == host.uid and not info.mode & 0o022, 'synthetic_parent')
            elif parent.path == '/':
                require(info.uid == 0 and not info.mode & 0o022, 'root_parent_custody')
            elif publisher and parent.path == STATE + '/integration':
                require((info.uid, info.gid, info.mode) == (984, 976, 0o700), 'publisher_state_custody')
            elif info.uid == 0:
                require(not info.mode & 0o022, 'root_parent_custody')
            else:
                require(not publisher and (info.uid, info.gid) == (1000, 1000)
                        and info.mode in ((0o700, 0o750, 0o755, 0o770, 0o775)
                                         if historical else (0o700, 0o750, 0o755)),
                        'caller_parent_custody')


def qualify_publisher_custody(custody, expected_sha256, host, now, *, require_fresh=True):
    require(type(custody) is PublisherConfigCustody, 'publisher_config_custody_required')
    sha(expected_sha256)
    sha(custody.qualification_sha256)
    require(upgrade_digest(asdict(custody)) == expected_sha256
            and type(custody.observed_at) in (int, float) and 0 <= custody.observed_at <= now
            and (not require_fresh or fresh(custody.observed_at, now)), 'publisher_config_custody_binding')
    uid, gid = (host.uid, os.getegid()) if host.synthetic else (0, 976)
    for node in (custody.directory, custody.key):
        require(type(node) is NodeIdentity and all(type(value) is int and value >= 0
                for value in asdict(node).values()) and node.ino > 0, 'publisher_metadata')
    require((custody.directory.uid, custody.directory.gid, custody.directory.mode)
            == (uid, gid, 0o750) and custody.directory.nlink >= 1, 'publisher_directory_metadata')
    require((custody.key.uid, custody.key.gid, custody.key.mode, custody.key.nlink)
            == (uid, gid, 0o440, 1), 'publisher_key_metadata')
    require(type(custody.key_size) is int and 0 < custody.key_size <= 65536
            and type(custody.key_mtime_ns) is int and custody.key_mtime_ns >= 0
            and type(custody.key_ctime_ns) is int and custody.key_ctime_ns >= 0,
            'publisher_key_metadata')


def qualify_public_ca_pins(pins, expected_sha256, upgrade):
    expected = {}
    for role, path in PUBLIC_CA_PATHS.items():
        closure = upgrade['new'][role]
        if path in closure['files']:
            expected[(role, upgrade_digest(closure), path)] = closure['files'][path]['sha256']
    if not expected:
        require(pins is None and expected_sha256 is None, 'unused_public_ca_authority')
        return
    require(type(pins) is tuple and 1 <= len(pins) <= 2
            and all(type(pin) is PublicCARecordPin for pin in pins), 'selected_public_ca_pins_required')
    sha(expected_sha256)
    require(upgrade_digest([asdict(pin) for pin in pins]) == expected_sha256, 'public_ca_admission')
    selected = {}
    for pin in pins:
        for value in (pin.closure_sha256, pin.blob_sha256, pin.public_record_sha256):
            sha(value)
        require(pin.role in PUBLIC_CA_PATHS and pin.path == PUBLIC_CA_PATHS[pin.role],
                'public_ca_fixed_role_path')
        key = (pin.role, pin.closure_sha256, pin.path)
        require(key not in selected and key in expected
                and expected[key] == pin.blob_sha256, 'public_ca_selected_blob')
        selected[key] = pin.blob_sha256
    require(selected == expected, 'public_ca_complete_selection')


class Host:
    def __init__(self, *, _synthetic=None):
        self.root = Path('/') if _synthetic is None else Path(_synthetic).resolve(strict=True)
        self.synthetic = _synthetic is not None
        require(not self.synthetic or (self.root.is_relative_to('/tmp')
                and self.root != Path('/tmp') and os.geteuid() != 0), 'synthetic_root')
        require(self.synthetic or (os.getuid(), os.geteuid()) == (0, 0), 'root_owner_required')
        self.uid = os.geteuid()

    def path(self, absolute):
        require(type(absolute) is str and absolute.startswith('/'), 'host_path')
        protected.relative(absolute[1:])
        path = self.root / absolute[1:]
        for parent in (path.parent, *path.parent.parents):
            if not parent.is_relative_to(self.root):
                continue
            info = parent.lstat()
            require(stat.S_ISDIR(info.st_mode) and info.st_uid == self.uid
                    and not info.st_mode & 0o022, 'host_parent_custody')
        return path

    @contextmanager
    def mutation_window(self, window):
        require(type(window) is MutationWindow and getattr(self, '_mutation_window', None) is None,
                'mutation_window_required')
        self._mutation_window = window
        try:
            yield
        finally:
            self._mutation_window = None

    def check_mutation_time(self):
        pure_mutation_time(getattr(self, '_mutation_window', None))

    def service_state(self):
        # Fixed read-only command; JSON cannot select a unit, command or flags.
        run = subprocess.run(['/usr/bin/systemctl', 'show', SERVICE,
            '--property=ActiveState,SubState,MainPID'], capture_output=True,
            text=True, timeout=10, check=True, env={'PATH': '/usr/bin:/bin', 'LC_ALL': 'C'})
        require(len(run.stdout) <= 4096, 'service_readback_bound')
        state = dict(line.split('=', 1) for line in run.stdout.splitlines())
        require(set(state) == {'ActiveState', 'SubState', 'MainPID'}, 'service_readback')
        return state

    def process_bound(self, pid, runtime):
        # PID comes from the fixed service readback, never from request JSON.
        require(type(pid) is int and pid > 0, 'service_pid')
        executable = os.readlink('/proc/' + str(pid) + '/exe')
        with open('/proc/' + str(pid) + '/cmdline', 'rb') as stream:
            raw = stream.read(16385)
        require(len(raw) <= 16384, 'process_readback_bound')
        # Match the maintained service launch contract, not script/flag tokens
        # appearing as data for another Python entrypoint or -c/-m invocation.
        interpreter = TARGETS['owner_venv'] + '/bin/python'
        script = TARGETS['owner_source'] + '/tools/delivery/stokowski_adapter.py'
        require(type(runtime) is str and runtime.startswith('/'), 'process_runtime')
        protected.relative(runtime[1:])
        expected = [os.fsencode(value) for value in
                    (interpreter, script, '--current', '--runtime', runtime)]
        return (executable == interpreter and raw.endswith(b'\0')
                and raw.split(b'\0') == expected + [b''])

    def verify_locks(self):
        require(getattr(self, '_held_locks', None) is not None, 'locks_not_held')
        require(fresh(self._lock_custody.observed_at, time.time()), 'lock_custody_stale')
        for parent, name, fd, expected, directory in self._held_locks:
            info = os.fstat(fd)
            require(identity(info) == expected and
                    (stat.S_ISDIR(info.st_mode) if directory else stat.S_ISREG(info.st_mode)),
                    'lock_descriptor_drift')
            linked = (self.root.lstat() if parent is None
                      else os.stat(name, dir_fd=parent, follow_symlinks=False))
            require(identity(linked) == expected and stat.S_IFMT(linked.st_mode)
                    == stat.S_IFMT(info.st_mode), 'lock_name_identity_drift')

    def verify_publisher_custody(self):
        custody = getattr(self, '_publisher_custody', None)
        require(type(custody) is PublisherConfigCustody, 'publisher_config_custody_required')
        info = os.fstat(self._publisher_fd)
        path = self.path(TARGETS['publisher_config'] + '/config.json').parent
        require(stat.S_ISDIR(info.st_mode) and identity(info) == custody.directory
                and identity(path.lstat()) == custody.directory, 'publisher_directory_drift')
        # Metadata only. In particular, never open/read/hash the key or enumerate
        # this credential-bearing directory, even when checking installed bytes.
        key = os.stat(PUBLISHER_KEY, dir_fd=self._publisher_fd, follow_symlinks=False)
        require(stat.S_ISREG(key.st_mode) and identity(key) == custody.key
                and (key.st_size, key.st_mtime_ns, key.st_ctime_ns)
                == (custody.key_size, custody.key_mtime_ns, custody.key_ctime_ns),
                'publisher_key_drift')

    @contextmanager
    def publisher_config(self, custody):
        require(type(custody) is PublisherConfigCustody, 'publisher_config_custody_required')
        if getattr(self, '_publisher_fd', None) is not None:
            require(custody == self._publisher_custody, 'publisher_nested_custody')
            self.verify_publisher_custody()
            yield
            return
        path = self.path(TARGETS['publisher_config'] + '/config.json').parent
        fd = os.open(path, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        self._publisher_fd, self._publisher_custody = fd, custody
        try:
            self.verify_publisher_custody()
            yield
        finally:
            self._publisher_fd = self._publisher_custody = None
            os.close(fd)

    def verify_role(self, role, absolute, closure):
        if type(closure) is dict and closure.get('kind') == 'retained-directory-v1':
            require(role in TARGETS and role != 'publisher_config', 'retained_directory_role')
            fields(closure, 'kind dev ino uid gid mode')
            require(all(type(closure[key]) is int and closure[key] >= 0
                        for key in ('dev','ino','uid','gid','mode'))
                    and closure['ino'] > 0 and closure['uid'] == self.uid
                    and closure['mode'] <= 0o777 and not closure['mode'] & 0o022,
                    'retained_directory_custody')
            path = self.path(absolute)
            fd = os.open(path, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
            try:
                info = os.fstat(fd)
                expected = {key:closure[key] for key in ('dev','ino','uid','gid','mode')}
                actual = {key:getattr(info,'st_'+key) for key in ('dev','ino','uid','gid')}
                actual['mode'] = stat.S_IMODE(info.st_mode)
                named = os.stat(path, follow_symlinks=False)
                need_named = (named.st_dev,named.st_ino,named.st_uid,named.st_gid,stat.S_IMODE(named.st_mode))
                require(stat.S_ISDIR(info.st_mode) and stat.S_ISDIR(named.st_mode)
                        and actual == expected and need_named == tuple(expected[key]
                            for key in ('dev','ino','uid','gid','mode')), 'retained_directory_identity')
            finally:
                os.close(fd)
            return upgrade_digest(closure)
        if role != 'publisher_config':
            return self.verify(absolute, closure, role=role)
        fields(closure, 'directories files')
        require(type(closure['directories']) is dict and set(closure['directories']) == {''}
                and type(closure['files']) is dict and set(closure['files']) == {'config.json'},
                'publisher_config_file_only')
        directory, item = closure['directories'][''], closure['files']['config.json']
        fields(directory, 'mode uid gid')
        fields(item, 'mode uid gid size sha256')
        self.verify_publisher_custody()
        custody = self._publisher_custody
        expected = dict(mode=custody.directory.mode, uid=custody.directory.uid, gid=custody.directory.gid)
        require(all(type(value) is int for value in directory.values())
                and directory == expected, 'publisher_directory_binding')
        uid, gid = (self.uid, os.getegid()) if self.synthetic else (0, 976)
        require(type(item['mode']) is int and type(item['uid']) is int and type(item['gid']) is int
                and (item['mode'], item['uid'], item['gid']) == (0o440, uid, gid)
                and type(item['size']) is int and 0 < item['size'] <= 1048576,
                'publisher_config_file_metadata')
        sha(item['sha256'])
        path = Path(absolute)
        require(str(path.parent) == TARGETS['publisher_config'] and
                (path.name == 'config.json' or re.fullmatch(
                    r'\.native-upgrade-[0-9a-f]{64}-publisher_config\.(?:new|old)\.json', path.name)),
                'publisher_config_fixed_path')
        before = os.stat(path.name, dir_fd=self._publisher_fd, follow_symlinks=False)
        require(stat.S_ISREG(before.st_mode) and before.st_nlink == 1
                and (stat.S_IMODE(before.st_mode), before.st_uid, before.st_gid, before.st_size)
                == (item['mode'], item['uid'], item['gid'], item['size']), 'publisher_config_file_readback')
        raw = protected.regular(path.name, 1048576, dir_fd=self._publisher_fd)
        after = os.stat(path.name, dir_fd=self._publisher_fd, follow_symlinks=False)
        require(protected.sha(raw) == item['sha256'] and identity(before) == identity(after)
                and (before.st_size, before.st_mtime_ns, before.st_ctime_ns)
                == (after.st_size, after.st_mtime_ns, after.st_ctime_ns), 'publisher_config_file_drift')
        self.verify_publisher_custody()
        return upgrade_digest(closure)

    @contextmanager
    def locks(self, custody):
        """Lock-only traversal. Never return relaxed paths to mutation methods."""
        require(getattr(self, '_held_locks', None) is None, 'nested_lock_custody')
        with ExitStack() as stack:
            held = []
            runtime_fd = None
            for record in custody.locks:
                fd = os.open(self.root, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
                stack.callback(os.close, fd)
                require(identity(os.fstat(fd)) == record.parents[0].identity, 'lock_parent_drift')
                held.append((None, None, fd, record.parents[0].identity, True))
                for parent in record.parents[1:]:
                    name = Path(parent.path).name
                    child = os.open(name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=fd)
                    stack.callback(os.close, child)
                    require(identity(os.fstat(child)) == parent.identity, 'lock_parent_drift')
                    held.append((fd, name, child, parent.identity, True))
                    fd = child
                if record.role == 'runtime-coordinator':
                    runtime_fd = fd
                name = Path(record.path).name
                lock = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=fd)
                stack.callback(os.close, lock)
                info = os.fstat(lock)
                require(stat.S_ISREG(info.st_mode) and identity(info) == record.identity,
                        'existing_lock_drift')
                held.append((fd, name, lock, record.identity, False))
                # No create/append/write, chmod, chown or replacement. Exclusive
                # Linux flock serializes the same existing inode as its owner.
                fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            self._held_locks, self._lock_custody = held, custody
            self._runtime_fd = runtime_fd
            try:
                self.verify_locks()
                yield
            finally:
                self._held_locks = self._lock_custody = self._runtime_fd = None

    def runtime_fd(self, runtime):
        self.verify_locks()
        require(self._lock_custody.runtime == runtime and self._runtime_fd is not None,
                'runtime_transition_lock_binding')
        return self._runtime_fd

    @contextmanager
    def runtime_observation(self, runtime, expected):
        # Read only from the exact directory inode retained in the root intent.
        # The owner can move a private directory, so walk no-follow from the
        # root and revalidate the complete open chain after the read.
        require(type(runtime) is str and runtime.startswith('/'), 'runtime_observation_path')
        parts = protected.relative(runtime[1:]).parts
        with ExitStack() as stack:
            fd = os.open(self.root, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
            stack.callback(os.close, fd)
            edges = []
            for part in parts:
                child = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=fd)
                stack.callback(os.close, child)
                edges.append((fd, part, child))
                fd = child
            def named():
                for parent, name, child in edges:
                    require(identity(os.fstat(child)) == identity(
                        os.stat(name, dir_fd=parent, follow_symlinks=False)),
                        'runtime_observation_path_drift')
                require(asdict(identity(os.fstat(fd))) == expected, 'runtime_observation_identity')
            named()
            yield fd
            named()

    def create(self, absolute, value):
        path = self.path(absolute)
        raw = protected.encoded(value)
        flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW
        self.check_mutation_time()  # No blocking preparation after this gate.
        fd = os.open(path, flags, 0o600)
        try:
            self.check_mutation_time()
            os.fchmod(fd, 0o600)
            remaining = memoryview(raw)
            while remaining:
                self.check_mutation_time()
                written = os.write(fd, remaining)
                require(written > 0, 'intent_write_progress')
                remaining = remaining[written:]
        finally:
            # Persist/close any already-authorized partial intent. This cleanup
            # grants no additional content write, mode change or rename.
            try:
                os.fsync(fd)
            finally:
                os.close(fd)
                protected.sync_dir(path.parent)

    def move(self, old, new):
        require(TARGETS['publisher_config'] not in (old, new), 'publisher_directory_not_swappable')
        source, target = self.path(old), self.path(new)
        # Linux create-only rename, including directory targets; no check/rename
        # overwrite race. Unsupported platforms hold rather than use os.rename.
        libc = ctypes.CDLL(None, use_errno=True)
        rename = getattr(libc, 'renameat2', None)
        require(rename is not None, 'rename_noreplace_unavailable')
        publisher_file = (str(Path(old).parent) == str(Path(new).parent) == TARGETS['publisher_config'])
        if publisher_file:
            require(fresh(self._publisher_custody.observed_at, time.time()), 'publisher_custody_stale')
            pattern = r'\.native-upgrade-[0-9a-f]{64}-publisher_config\.%s\.json'
            require((source.name == 'config.json' and re.fullmatch(pattern % 'old', target.name))
                    or (target.name == 'config.json' and re.fullmatch(pattern % 'new', source.name)),
                    'publisher_config_fixed_move')
            self.verify_publisher_custody()
            # Operate inside the retained original directory, never rename it.
            arguments = (self._publisher_fd, os.fsencode(source.name),
                         self._publisher_fd, os.fsencode(target.name), 1)
        else:
            arguments = (-100, os.fsencode(source), -100, os.fsencode(target), 1)
        self.check_mutation_time()  # Includes publisher move's own custody I/O.
        result = rename(*arguments)
        if result != 0:
            raise OSError(ctypes.get_errno(), 'upgrade rename refused')
        protected.sync_dir(source.parent)
        if target.parent != source.parent:
            protected.sync_dir(target.parent)
        if publisher_file:
            os.fsync(self._publisher_fd)
            self.verify_publisher_custody()

    def verify(self, absolute, closure, *, role=None):
        """Read exact selected files/metadata; refuse links and extra entries.

        No commands/imports run from staged code. JSON never selects modes to
        apply: modes/UID/GID are observed, compared and never changed here.
        """
        fields(closure, 'directories files')
        require(type(closure['directories']) is dict and '' in closure['directories']
                and type(closure['files']) is dict
                and 0 < len(closure['files']) <= MAX_FILES
                and len(closure['directories']) <= MAX_FILES, 'closure_bounds')
        expected = {}
        for kind in ('directories', 'files'):
            for name, item in closure[kind].items():
                require(name not in expected, 'closure_duplicate')
                if name:
                    protected.relative(name)
                else:
                    require(kind == 'directories', 'closure_root')
                fields(item, 'mode uid gid' if kind == 'directories' else 'mode uid gid size sha256')
                require(type(item['mode']) is int and 0 <= item['mode'] <= 0o777
                        and not item['mode'] & 0o022 and item['uid'] == self.uid
                        and type(item['uid']) is int and type(item['gid']) is int
                        and 0 <= item['gid'] <= 65535, 'closure_custody')
                if kind == 'files':
                    require(type(item['size']) is int and 0 <= item['size'] <= MAX_FILE, 'file_size')
                    sha(item['sha256'])
                    parts = Path(name).parts
                    public_ca = (role in PUBLIC_CA_PATHS and name == PUBLIC_CA_PATHS[role]
                        and any(pin.role == role and pin.path == name
                                and pin.closure_sha256 == upgrade_digest(closure)
                                and pin.blob_sha256 == item['sha256']
                                for pin in (getattr(self, '_public_ca_pins', None) or ())))
                    require(not any(p.startswith('.env') or p in ('credentials', 'auth.json', 'credentials.json')
                            or p.endswith(('.key', '.log')) or (p.endswith('.pem') and not public_ca)
                            for p in parts), 'secret_or_log_path')
                expected[name] = (kind, item)
        for name in expected:
            if name:
                parent = str(Path(name).parent)
                require(('' if parent == '.' else parent) in closure['directories'], 'missing_directory')
        root = self.path(absolute)
        fd = os.open(root, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        seen, total = set(), 0
        def walk(directory, prefix):
            nonlocal total
            require(prefix in closure['directories'], 'unexpected_directory')
            info = os.fstat(directory)
            item = closure['directories'][prefix]
            require((stat.S_IMODE(info.st_mode), info.st_uid, info.st_gid)
                    == (item['mode'], item['uid'], item['gid']), 'directory_readback')
            seen.add(prefix)
            for child in os.listdir(directory):
                name = prefix + '/' + child if prefix else child
                require(name in expected, 'unexpected_entry')
                kind, item = expected[name]
                if kind == 'directories':
                    sub = os.open(child, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=directory)
                    try:
                        walk(sub, name)
                    finally:
                        os.close(sub)
                else:
                    sub = os.open(child, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=directory)
                    try:
                        info = os.fstat(sub)
                        require(stat.S_ISREG(info.st_mode) and info.st_nlink == 1
                                and (stat.S_IMODE(info.st_mode), info.st_uid, info.st_gid, info.st_size)
                                == (item['mode'], item['uid'], item['gid'], item['size']), 'file_readback')
                        value = hashlib.sha256()
                        with os.fdopen(sub, 'rb', closefd=False) as stream:
                            while block := stream.read(1048576):
                                total += len(block)
                                require(total <= MAX_TOTAL, 'closure_total')
                                value.update(block)
                        after = os.fstat(sub)
                        require(value.hexdigest() == item['sha256']
                                and (info.st_size, info.st_mtime_ns, info.st_ctime_ns)
                                == (after.st_size, after.st_mtime_ns, after.st_ctime_ns), 'file_drift')
                    finally:
                        os.close(sub)
                    seen.add(name)
        try:
            walk(fd, '')
            require(seen == set(expected), 'missing_entry')
        finally:
            os.close(fd)
        return upgrade_digest(closure)


def locations(role, operation):
    if role == 'publisher_config':
        parent = TARGETS[role]
        stem = parent + '/.native-upgrade-' + operation + '-publisher_config'
        return parent + '/config.json', stem + '.new.json', stem + '.old.json'
    target = TARGETS[role]
    parent = str(Path(target).parent)
    return target, parent + '/.native-upgrade-' + operation + '-' + role + '.new', parent + '/.native-upgrade-' + operation + '-' + role + '.old'


def runtime_transition(plan, upgrade, *, old_config, new_config, old_policy,
                       reviewed_policy, saved_state, old_binding, new_binding,
                       old_catalog, new_catalog, old_python_sha256, new_python_sha256):
    """Derive the two permitted fixed-file replacements, without host effects.

    Caller must read selected runtime and old/new package roles while the
    existing stopped-owner mutation locks are held. Input bytes never enter
    the original journal; the admission-bound digest map covers them.
    """
    pins = upgrade['runtime_transition']
    fields(pins, 'old_config_sha256 new_config_sha256 old_policy_sha256 '
           'new_policy_sha256 old_state_sha256 new_state_sha256')
    for value in pins.values():
        sha(value)
    require(all(type(raw) is bytes and 0 < len(raw) <= 8*1024*1024 for raw in
                (old_config, new_config, old_policy, reviewed_policy, saved_state,
                 old_binding, new_binding)), 'runtime_transition_bounds')
    before, after = map(protected.record, (old_config, new_config))
    previous, successor = map(protected.record, (old_binding, new_binding))
    runtime = plan['legacy_snapshot']['runtime_path']
    target = plan['request']['target']
    for binding, config, raw, key, catalog, python_pin in (
            (previous, before, old_config, 'old_config_sha256', old_catalog, old_python_sha256),
            (successor, after, new_config, 'new_config_sha256', new_catalog, new_python_sha256)):
        sha(python_pin)
        require(binding == dict(schema='protected-current-owner-v1', runtime=runtime,
                source_root=TARGETS['owner_source'], config_sha256=protected.sha(raw),
                catalog_sha256=protected.sha(catalog), python_sha256=python_pin)
                and binding['config_sha256'] == pins[key]
                and config.get('owner') == plan['request']['owner'],
                'runtime_transition_owner_binding')
    changed = {'source_head', 'source_sha256', 'policy_sha256'}
    require({k:v for k,v in before.items() if k not in changed}
            == {k:v for k,v in after.items() if k not in changed}
            and before.get('source_head') == plan['legacy_snapshot']['source_head']
            and after.get('source_head') == target['source_head']
            and old_catalog == new_catalog
            and old_python_sha256 == new_python_sha256,
            'runtime_transition_fixed_context')
    exact_source_pin = upgrade['new']['owner_source']['files'].get(
        'tools/delivery/capacity-policy.json', {}).get('sha256')
    require(protected.sha(old_policy) == before['policy_sha256'] == pins['old_policy_sha256']
            and protected.sha(reviewed_policy) == after['policy_sha256']
                == pins['new_policy_sha256'] == exact_source_pin,
            'runtime_transition_policy')
    retained = protected.record(saved_state)
    require(protected.sha(saved_state) == pins['old_state_sha256']
            and retained.get('owner') == before['owner']
            and retained.get('config_sha256') == pins['old_config_sha256']
            and type(retained.get('bindings')) is dict and type(retained.get('tasks')) is dict,
            'runtime_transition_saved_state')
    # Preserve every nested field and unknown historical field. Do not
    # recalculate historical task/attempt policy evidence or clear holds.
    next_state = protected.encoded(dict(retained, config_sha256=pins['new_config_sha256']))
    require(protected.sha(next_state) == pins['new_state_sha256'],
            'runtime_transition_new_state_pin')
    return {'capacity-policy.json': reviewed_policy, 'current-owner.json': next_state}


def qualify(plan_bytes, upgrade, admission, now):
    require(type(plan_bytes) is bytes and len(plan_bytes) <= 262144, 'plan_bytes')
    plan = protected.record(plan_bytes)
    require(type(admission) is OwnerAdmission, 'owner_admission_required')
    identifier(admission.owner)
    for pin in (admission.plan_sha256, admission.upgrade_sha256, admission.host_confirmation_sha256):
        sha(pin)
    require(admission.plan_sha256 == protected.sha(plan_bytes)
            and admission.upgrade_sha256 == upgrade_digest(upgrade)
            and type(admission.expires_at) in (int, float) and now < admission.expires_at <= now + 300,
            'owner_admission_binding')
    require(plan.get('kind') == 'native-harness-adoption-plan-v1'
            and plan['request']['owner'] == admission.owner
            and plan['milestones']['source_ready'] is True
            and plan['milestones']['coherent_validation_accepted'] is True
            and plan['stop_witness_qualified'] is True and not plan['unresolved_effects']
            and plan['holds'] == ['REVIEWED_TYPED_UPGRADE_ROUTE_REQUIRED',
                                  'ACTUAL_HOST_CONFIRMATIONS_AND_READBACK_REQUIRED'], 'preflight_not_qualified')
    manifest_keys = 'version kind operation_id preflight_sha256 old new legacy_receipts'
    if 'runtime_transition' in upgrade:
        manifest_keys += ' runtime_transition'
        pins = upgrade['runtime_transition']
        fields(pins, 'old_config_sha256 new_config_sha256 old_policy_sha256 '
               'new_policy_sha256 old_state_sha256 new_state_sha256')
        for pin in pins.values():
            sha(pin)
        require(pins['old_config_sha256'] != pins['new_config_sha256']
                and pins['old_policy_sha256'] != pins['new_policy_sha256']
                and pins['old_state_sha256'] != pins['new_state_sha256'],
                'runtime_transition_distinct_images')
    fields(upgrade, manifest_keys)
    require(type(upgrade['version']) is int and upgrade['version'] == 1
            and upgrade['kind'] == 'native-harness-upgrade-v1', 'upgrade_version')
    sha(upgrade['operation_id'])
    require(upgrade['preflight_sha256'] == admission.plan_sha256, 'upgrade_plan')
    fields(upgrade['old'], ' '.join(TARGETS))
    fields(upgrade['new'], ' '.join(TARGETS))
    for role in TARGETS:
        fields(upgrade['new'][role], 'directories files')
        if role != 'publisher_config':
            fields(upgrade['old'][role], 'kind dev ino uid gid mode')
            require(upgrade['old'][role]['kind'] == 'retained-directory-v1', 'opaque_old_directory_required')
        else:
            fields(upgrade['old'][role], 'directories files')
    for role, key in (('owner_source', 'source_sha256'), ('owner_venv', 'runtime_sha256'),
                      ('owner_config', 'config_sha256')):
        require(upgrade_digest(upgrade['old'][role]) == plan['legacy_snapshot'][key], 'old_snapshot_closure')
    target = plan['request']['target']
    require(upgrade_digest(upgrade['new']['owner_venv']) == target['dependencies']['sha256']
            and upgrade_digest(upgrade['new']['owner_config']) == target['config']['sha256'], 'new_config_dependency_closure')
    for ref in target['files']:
        require(upgrade['new']['owner_source']['files'].get(ref['path'], {}).get('sha256')
                == ref['sha256'], 'new_source_artifact')
    require(upgrade['new']['owner_source']['files'].get('.git/HEAD', {}).get('sha256')
            == protected.sha((target['source_head'] + '\n').encode()), 'source_head_readback')
    # Old source/tree/config headers remain declared owner evidence; opaque old
    # descriptor pins assert retained root custody, never old content coverage.
    require(type(upgrade['legacy_receipts']) is dict and set(upgrade['legacy_receipts']) == {
        str(protected.RECEIPT), STATE + '/publisher-install.jsonl'}, 'legacy_receipts')
    for pin in upgrade['legacy_receipts'].values():
        sha(pin)
    return plan


def stopped(host, plan, observation, now):
    require(type(observation) is Quiescence and fresh(observation.observed_at, now)
            and observation.snapshot_sha256 == plan['request']['legacy_snapshot']['sha256']
            and type(observation.inflight) is int and observation.inflight == 0
            and observation.children_gone is True
            and observation.unresolved_operation_ids == (), 'native_quiescence_required')
    sha(observation.evidence_sha256)
    require(host.service_state() == dict(ActiveState='inactive', SubState='dead', MainPID='0'),
            'actual_service_not_stopped')


def mutation_guard(host, plan, observation, admission):
    """Recheck after potentially slow verification, at each write/move boundary.

    Service readback can itself take time, so expiry/freshness are checked on
    both sides of it. Existing locks retain serialization; no host action occurs.
    """
    now = time.time()
    require(now < admission.expires_at, 'admission_expired')
    host.verify_locks()
    require(fresh(host._publisher_custody.observed_at, now), 'publisher_custody_stale')
    host.verify_publisher_custody()
    stopped(host, plan, observation, now)
    now = time.time()
    require(now < admission.expires_at, 'admission_expired')
    require(fresh(observation.observed_at, now), 'native_quiescence_required')
    host.verify_locks()
    require(fresh(host._publisher_custody.observed_at, now), 'publisher_custody_stale')
    host.verify_publisher_custody()
    host.check_mutation_time()  # Final pure gate AFTER all guard I/O.


def runtime_read(fd, name):
    before = os.stat(name, dir_fd=fd, follow_symlinks=False)
    require(stat.S_ISREG(before.st_mode) and before.st_nlink == 1
            and not stat.S_IMODE(before.st_mode) & 0o7022
            and 0 < before.st_size <= RUNTIME_LIMIT, 'runtime_file_custody')
    raw = protected.regular(name, RUNTIME_LIMIT, dir_fd=fd)
    after = os.stat(name, dir_fd=fd, follow_symlinks=False)
    require(identity(before) == identity(after)
            and (before.st_size, before.st_ctime_ns, before.st_mtime_ns)
            == (after.st_size, after.st_ctime_ns, after.st_mtime_ns),
            'runtime_file_drift')
    return raw, before


def runtime_side(operation, name):
    sha(operation)
    require(name in RUNTIME_FILES, 'runtime_fixed_file')
    return '.native-upgrade-' + operation + '-' + name


def runtime_stage(host, plan, upgrade, operation):
    runtime = plan['legacy_snapshot']['runtime_path']
    fd = host.runtime_fd(runtime)
    current, stage, _ = locations('owner_config', operation)
    _, new_source, _ = locations('owner_source', operation)

    def sealed(directory, relative, max_bytes):
        parent = host.path(directory + '/' + relative)
        st = parent.lstat()
        require(stat.S_ISREG(st.st_mode) and st.st_uid == host.uid
                and not st.st_mode & 0o222, 'runtime_sealed_input_custody')
        return protected.regular(parent, max_bytes)

    catalog = 'catalog.json'
    old_policy, p_stat = runtime_read(fd, RUNTIME_FILES[0])
    saved_state, s_stat = runtime_read(fd, RUNTIME_FILES[1])
    runtime_owner = ((host.uid, os.getegid()) if host.synthetic else (1000,1000))
    for st in (p_stat, s_stat):
        require((st.st_uid,st.st_gid) == runtime_owner, 'runtime_file_owner')
    for name in RUNTIME_FILES:
        try:
            os.stat(runtime_side(operation, name), dir_fd=fd, follow_symlinks=False)
        except FileNotFoundError:
            continue
        raise ValueError('runtime_transition_side_exists')
    old_binding = sealed(current, 'binding.json', RUNTIME_LIMIT)
    # The retained older venv is explicitly opaque in the established protocol.
    # Reuse its root-sealed declared interpreter pin, without reopening or
    # executing an old venv file that may be owned by the runtime user.
    new = runtime_transition(plan, upgrade,
        old_config=sealed(current, 'current.json', RUNTIME_LIMIT),
        new_config=sealed(stage, 'current.json', RUNTIME_LIMIT),
        old_policy=old_policy,
        reviewed_policy=sealed(new_source, 'tools/delivery/capacity-policy.json', RUNTIME_LIMIT),
        saved_state=saved_state,
        old_binding=old_binding,
        new_binding=sealed(stage, 'binding.json', RUNTIME_LIMIT),
        old_catalog=sealed(current, catalog, RUNTIME_LIMIT),
        new_catalog=sealed(stage, catalog, RUNTIME_LIMIT),
        old_python_sha256=protected.record(old_binding)['python_sha256'],
        new_python_sha256=upgrade['new']['owner_venv']['files']['bin/python']['sha256'])
    return fd, new, dict(directory=asdict(identity(os.fstat(fd))), owner=plan['request']['owner'],
        files={name:dict(uid=st.st_uid,gid=st.st_gid,mode=stat.S_IMODE(st.st_mode))
                for name,st in zip(RUNTIME_FILES,(p_stat,s_stat))})


def runtime_match(fd, name, expected, metadata):
    raw, st = runtime_read(fd, name)
    require(protected.sha(raw) == expected and
            metadata == dict(uid=st.st_uid,gid=st.st_gid,mode=stat.S_IMODE(st.st_mode)),
            'runtime_exact_image')
    return raw


def prepare_runtime_side(host, fd, operation, name, raw, metadata, guard):
    side = runtime_side(operation, name)
    guard()
    tmp = os.open(side, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
                  0o600, dir_fd=fd)
    try:
        if not host.synthetic:
            guard()
            os.fchown(tmp, metadata['uid'], metadata['gid'])
        rest = memoryview(raw)
        while rest:
            guard()
            size = os.write(tmp, rest)
            require(size > 0, 'runtime_stage_write')
            rest = rest[size:]
        guard()
        os.fchmod(tmp, metadata['mode'])
    finally:
        try:
            os.fsync(tmp)
        finally:
            os.close(tmp)
            os.fsync(fd)


def exchange_runtime(host, fd, operation, name, old, new, metadata, guard):
    side = runtime_side(operation, name)
    rename = getattr(ctypes.CDLL(None, use_errno=True), 'renameat2', None)
    require(rename is not None, 'runtime_exchange_unavailable')
    runtime_match(fd, name, old, metadata)
    runtime_match(fd, side, new, metadata)
    guard()
    # The fixed names are under cooperative custody; do not trust a snapshot
    # taken before the service/lock guard's I/O. Fail before replacement if
    # either name was changed during that guard; recheck the pure deadline
    # after the last evidence reads.
    runtime_match(fd, name, old, metadata)
    runtime_match(fd, side, new, metadata)
    host.check_mutation_time()
    if rename(fd, os.fsencode(side), fd, os.fsencode(name), 2) != 0:
        raise OSError(ctypes.get_errno(), 'runtime atomic exchange refused')
    os.fsync(fd)
    runtime_match(fd, name, new, metadata)
    runtime_match(fd, side, old, metadata)


def runtime_pins(upgrade, name):
    stem = 'policy' if name == RUNTIME_FILES[0] else 'state'
    pins = upgrade['runtime_transition']
    return pins['old_'+stem+'_sha256'], pins['new_'+stem+'_sha256']


def execute(plan_bytes, upgrade, *, admission, quiescence, lock_custody=None,
            publisher_config_custody=None, public_ca_pins=None, host=None):
    """One admitted attempt; never start services, retire legacy or auto-rollback.

    All staged slots already exist, sealed by the owner. Four old directories
    move opaque and intact to create-only sibling custody slots, without any
    old child enumeration/read/hash. Publisher config
    swaps only its fixed JSON file, retaining the original directory/key in place.
    A permanent intent precedes all moves. Any failure/unknown effect requires
    observe() and explicit owner reconciliation; execute() always refuses replay.
    """
    upgrade = protected.record(protected.encoded(upgrade))
    now = time.time()
    plan = qualify(plan_bytes, upgrade, admission, now)
    host = host or Host()
    qualify_lock_custody(lock_custody, admission, plan, quiescence, host, now)
    qualify_publisher_custody(publisher_config_custody,
                              admission.publisher_config_custody_sha256, host, now)
    qualify_public_ca_pins(public_ca_pins, admission.public_ca_pins_sha256, upgrade)
    operation = upgrade['operation_id']
    receipt = STATE + '/native-upgrade-' + operation + '.intent.json'
    result_path = STATE + '/native-upgrade-' + operation + '.installed.json'
    old_fence = STATE + '/native-upgrade-from-' + upgrade_digest(upgrade['old']) + '.intent.json'
    host._public_ca_pins = public_ca_pins
    window = MutationWindow(admission, quiescence, lock_custody, publisher_config_custody)
    with host.locks(lock_custody), host.publisher_config(publisher_config_custody), host.mutation_window(window):
        require(not os.path.lexists(host.path(receipt))
                and not os.path.lexists(host.path(result_path))
                and not os.path.lexists(host.path(old_fence)), 'prior_upgrade_no_replay')
        stopped(host, plan, quiescence, time.time())
        for path, pin in upgrade['legacy_receipts'].items():
            require(protected.sha(protected.regular(host.path(path), 8*1024*1024)) == pin, 'legacy_receipt_drift')
        for role in TARGETS:
            target, stage, backup = locations(role, operation)
            require(not os.path.lexists(host.path(backup)), 'rollback_slot_exists')
            host.verify_role(role, target, upgrade['old'][role])
            host.verify_role(role, stage, upgrade['new'][role])
        require(time.time() < admission.expires_at, 'admission_expired')
        intent = dict(kind='native-upgrade-intent-v1', upgrade=upgrade,
            plan_sha256=admission.plan_sha256, quiescence_sha256=quiescence.evidence_sha256,
            host_confirmation_sha256=admission.host_confirmation_sha256,
            lock_custody_sha256=admission.lock_custody_sha256,
            publisher_config_custody_sha256=admission.publisher_config_custody_sha256,
            public_ca_pins_sha256=admission.public_ca_pins_sha256,
            host_scope='synthetic' if host.synthetic else 'production',
            runtime_path=plan['legacy_snapshot']['runtime_path'])
        transition = None
        if 'runtime_transition' in upgrade:
            transition = runtime_stage(host, plan, upgrade, operation)
            intent['runtime_transition_custody'] = transition[2]
        # Old-closure fence precedes the operation fence. A crash between them
        # still suppresses a new ID/preflight attempting the same old closure.
        mutation_guard(host, plan, quiescence, admission)
        host.create(old_fence, intent)
        mutation_guard(host, plan, quiescence, admission)
        host.create(receipt, intent)
        def guard():
            mutation_guard(host, plan, quiescence, admission)
        if transition:
            fd, inputs, metadata = transition
            for name in RUNTIME_FILES:
                prepare_runtime_side(host, fd, operation, name, inputs[name],
                                     metadata['files'][name], guard)
        for role in TARGETS:
            require(time.time() < admission.expires_at, 'admission_expired')
            stopped(host, plan, quiescence, time.time())
            target, stage, backup = locations(role, operation)
            host.verify_role(role, target, upgrade['old'][role])
            host.verify_role(role, stage, upgrade['new'][role])
            mutation_guard(host, plan, quiescence, admission)
            host.move(target, backup)
            mutation_guard(host, plan, quiescence, admission)
            host.move(stage, target)
        if transition:
            for name in RUNTIME_FILES:
                old, new = runtime_pins(upgrade, name)
                exchange_runtime(host, fd, operation, name, old, new,
                                 metadata['files'][name], guard)
        readback = observe(upgrade, host=host, publisher_config_custody=publisher_config_custody,
                           public_ca_pins=public_ca_pins, _cutover=transition is not None)
        require(readback['installed_verified'] and readback['rollback_verified'], 'installed_readback_mismatch')
        mutation_guard(host, plan, quiescence, admission)
        host.create(result_path, dict(kind='native-upgrade-installed-v1', upgrade_sha256=upgrade_digest(upgrade),
                                     readback=readback, active_observed=False, legacy_retired=False))
        return readback


def runtime_readback(host, upgrade, intent, *, moving=False, active=False):
    operation = upgrade['operation_id']
    unknown = dict.fromkeys(RUNTIME_FILES, 'unknown-or-mismatch')
    custody = intent['runtime_transition_custody']
    fields(custody, 'directory files owner')
    fields(custody['files'], ' '.join(RUNTIME_FILES))
    phases = dict(unknown)
    with host.runtime_observation(intent['runtime_path'], custody['directory']) as fd:
        for name in RUNTIME_FILES:
            old, new = runtime_pins(upgrade, name)
            side = runtime_side(operation, name)
            metadata = custody['files'][name]
            try:
                if active and name == RUNTIME_FILES[1]:
                    raw, st = runtime_read(fd, name)
                    require(metadata == dict(uid=st.st_uid,gid=st.st_gid,mode=stat.S_IMODE(st.st_mode)),
                            'runtime_active_metadata')
                    state = protected.record(raw)
                    require(state.get('owner') == custody['owner']
                            and state.get('config_sha256') == upgrade['runtime_transition']['new_config_sha256']
                            and type(state.get('bindings')) is dict and type(state.get('tasks')) is dict,
                            'runtime_active_binding')
                else:
                    runtime_match(fd, name, new, metadata)
                runtime_match(fd, side, old, metadata)
                phases[name] = 'applied'
                continue
            except (OSError, ValueError, TypeError, KeyError):
                pass
            try:
                runtime_match(fd, name, old, metadata)
                try:
                    runtime_match(fd, side, new, metadata)
                except FileNotFoundError:
                    pass
                phases[name] = 'not-applied'
            except (OSError, ValueError, TypeError, KeyError):
                pass
    if phases[RUNTIME_FILES[1]] == 'applied' and phases[RUNTIME_FILES[0]] != 'applied':
        phases = unknown
    canonical = False
    if not moving:
        try:
            receipt = protected.record(protected.regular(host.path(
                STATE + '/native-upgrade-' + operation + '.installed.json'), 32*1024*1024))
            readback = receipt['readback']
            canonical = (receipt['kind'] == 'native-upgrade-installed-v1'
                    and receipt['upgrade_sha256'] == upgrade_digest(upgrade)
                    and readback['operation_id'] == operation
                    and readback['upgrade_sha256'] == receipt['upgrade_sha256']
                    and readback['runtime_transition']['files'] == dict.fromkeys(RUNTIME_FILES, 'applied')
                    and readback['installed_verified'] is True and readback['rollback_verified'] is True)
        except (OSError, ValueError, TypeError, KeyError):
            pass
    return dict(files=phases, canonical_cutover_receipt_verified=canonical,
                verified=(moving or canonical) and all(v == 'applied' for v in phases.values()))


def observe(upgrade, *, publisher_config_custody=None, public_ca_pins=None, host=None,
            _cutover=False, _active=False):
    """Read-only same-operation reconciliation. Never clear receipts or retry."""
    host = host or Host()
    operation = upgrade['operation_id']
    sha(operation)
    intent_ok = False
    try:
        intent = protected.record(protected.regular(host.path(
            STATE + '/native-upgrade-' + operation + '.intent.json'), 32*1024*1024))
        old_fence = protected.record(protected.regular(host.path(
            STATE + '/native-upgrade-from-' + upgrade_digest(upgrade['old']) + '.intent.json'), 32*1024*1024))
        intent_ok = (intent.get('kind') == 'native-upgrade-intent-v1'
                     and intent.get('upgrade') == upgrade and old_fence == intent)
    except (OSError, ValueError):
        pass
    results = {}
    public_ca_ok = False
    try:
        require(intent_ok, 'public_ca_intent_required')
        qualify_public_ca_pins(public_ca_pins, intent.get('public_ca_pins_sha256'), upgrade)
        public_ca_ok = True
    except (ValueError, TypeError, KeyError):
        pass
    host._public_ca_pins = public_ca_pins if public_ca_ok else None
    publisher_ok = False
    try:
        require(intent_ok, 'publisher_intent_required')
        qualify_publisher_custody(publisher_config_custody,
            intent.get('publisher_config_custody_sha256'), host, time.time(), require_fresh=False)
        with host.publisher_config(publisher_config_custody):
            publisher_ok = True
    except (OSError, ValueError):
        pass
    receipts_ok = True
    for path, pin in upgrade['legacy_receipts'].items():
        try:
            receipts_ok = receipts_ok and protected.sha(protected.regular(
                host.path(path), 8*1024*1024)) == pin
        except (OSError, ValueError):
            receipts_ok = False
    for role in TARGETS:
        target, stage, backup = locations(role, operation)
        axes = {}
        for name, path, closure in (('installed', target, upgrade['new'][role]),
                                    ('rollback', backup, upgrade['old'][role]),
                                    ('staged', stage, upgrade['new'][role])):
            try:
                if name == 'rollback' and role != 'publisher_config':
                    require(type(closure) is dict and closure.get('kind') == 'retained-directory-v1',
                            'old_coverage_unknown')
                if role == 'publisher_config':
                    require(publisher_ok, 'publisher_config_custody_required')
                    with host.publisher_config(publisher_config_custody):
                        host.verify_role(role, path, closure)
                else:
                    host.verify_role(role, path, closure)
                axes[name] = ('retained-identity' if name == 'rollback'
                              and role != 'publisher_config' else 'verified')
            except (OSError, ValueError):
                axes[name] = 'unknown-or-mismatch'
        results[role] = axes
    if publisher_ok:
        try:
            with host.publisher_config(publisher_config_custody):
                pass
        except (OSError, ValueError):
            publisher_ok = False
    transition = None
    if 'runtime_transition' in upgrade:
        try:
            require(intent_ok, 'runtime_transition_intent_required')
            transition = runtime_readback(host, upgrade, intent, moving=_cutover, active=_active)
        except (OSError, ValueError, TypeError, KeyError):
            transition = dict(files=dict.fromkeys(RUNTIME_FILES, 'unknown-or-mismatch'),
                              canonical_cutover_receipt_verified=False, verified=False)
    runtime_ok = transition is None or transition['verified']
    return dict(operation_id=operation, upgrade_sha256=upgrade_digest(upgrade), closures=results,
        **({} if transition is None else {'runtime_transition': transition}),
        host_scope='synthetic' if host.synthetic else 'production',
        intent_verified=intent_ok,
        legacy_receipts_verified=receipts_ok,
        publisher_custody_verified=publisher_ok,
        public_ca_selection_verified=public_ca_ok,
        publisher_observed_at=time.time() if publisher_ok else None,
        old_custody_coverage='directory-root-identity-only; publisher-old-config-file-hash',
        installed_verified=runtime_ok and intent_ok and receipts_ok and publisher_ok and public_ca_ok and all(row['installed'] == 'verified' for row in results.values()),
        rollback_verified=runtime_ok and intent_ok and publisher_ok and public_ca_ok and all(
            row['rollback'] == ('verified' if role == 'publisher_config' else 'retained-identity')
            for role,row in results.items()),
        active_observed=False, legacy_retired=False, replay_authorized=False)


def verify_active(upgrade, *, publisher_config_custody=None, public_ca_pins=None, host=None):
    """Separate actual service observation after owner-managed activation.

    This never starts a service or claims product/functional/legacy retirement
    acceptance. Full NEW installed bytes and OLD root custody are checked both
    sides of service readback, not a restored/audited legacy environment.
    """
    host = host or Host()
    before = observe(upgrade, host=host, publisher_config_custody=publisher_config_custody,
                     public_ca_pins=public_ca_pins, _active='runtime_transition' in upgrade)
    require(before['installed_verified'] and before['rollback_verified'], 'active_closure_mismatch')
    intent = protected.record(protected.regular(host.path(
        STATE + '/native-upgrade-' + upgrade['operation_id'] + '.intent.json'), 32*1024*1024))
    runtime = intent.get('runtime_path')
    require(type(runtime) is str and runtime.startswith('/'), 'active_runtime_binding')
    state = host.service_state()
    require(state.get('ActiveState') == 'active' and state.get('SubState') == 'running'
            and state.get('MainPID', '').isdigit() and int(state['MainPID']) > 0, 'service_not_active')
    require(host.process_bound(int(state['MainPID']), runtime), 'active_process_binding')
    after = observe(upgrade, host=host, publisher_config_custody=publisher_config_custody,
                    public_ca_pins=public_ca_pins, _active='runtime_transition' in upgrade)
    require(after['installed_verified'] and after['rollback_verified'], 'active_readback_drift')
    require(host.service_state() == state and host.process_bound(int(state['MainPID']), runtime),
            'active_process_changed')
    return dict(after, active_observed=True, service=state)
