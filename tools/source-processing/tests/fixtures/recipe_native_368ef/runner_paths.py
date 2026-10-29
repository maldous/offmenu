"""Explicit physical runner storage bindings; never part of logical data identity.

Operational callers need an owner-controlled split configuration and the common
runner lease. Nested paths exist only under explicit synthetic-fixture selection.
Loading/validating this module never creates or chmods state or locks.
"""
from __future__ import annotations

from dataclasses import dataclass
import fcntl
import hashlib
import json
import os
from pathlib import Path
import stat

SCHEMA = 'offmenu-runner-layout/1'
PUBLIC = frozenset(('barcodes', 'ingredients', 'recipes', 'dietary', 'suppliers', 'citations'))
PRIVATE = frozenset(('user_profiles', 'inventory'))


def safe_absolute(value):
    if not isinstance(value, (str, Path)) or not Path(value).is_absolute():
        raise ValueError('runner_layout_absolute_path_required')
    path = Path(os.path.abspath(value))
    for node in (path, *path.parents):
        if node.is_symlink():
            raise ValueError('runner_layout_symlink_refused')
    return path


def private_identity(path, *, directory=False):
    path = safe_absolute(path)
    try:
        info = path.lstat()
    except OSError as error:
        raise ValueError('runner_layout_missing_or_unavailable') from error
    valid_type = stat.S_ISDIR(info.st_mode) if directory else stat.S_ISREG(info.st_mode)
    if not valid_type or info.st_uid != os.getuid() or stat.S_IMODE(info.st_mode) != (0o700 if directory else 0o600):
        raise ValueError('runner_layout_private_owner_required')
    return info.st_dev, info.st_ino


@dataclass(frozen=True)
class StateLayout:
    runtime: Path
    public_staging: Path
    normalization: Path
    household: Path
    lock: Path
    config_path: Path | None = None
    config_digest: str | None = None
    root_identities: tuple = ()
    legacy: bool = False
    legacy_ingest: Path | None = None

    @property
    def ingest(self):
        return self.legacy_ingest if self.legacy else self.runtime / 'ingest'

    def domain_path(self, domain):
        if domain not in PUBLIC | PRIVATE:
            raise ValueError('unknown_domain')
        directory = self.household / 'staging' if domain in PRIVATE else self.public_staging
        return directory / (domain + '.sqlite3')

    def verify(self):
        if self.legacy:
            if os.environ.get('OFFMENU_RUN_LEGACY_FIXTURE') != '1' or os.environ.get('OFFMENU_RUN_LAYOUT'):
                raise ValueError('runner_layout_selection_changed')
            return
        selected = os.environ.get('OFFMENU_RUN_LAYOUT')
        if not selected or safe_absolute(selected) != self.config_path:
            raise ValueError('runner_layout_selection_changed')
        current = _load(self.config_path)
        if current != self:
            raise ValueError('runner_layout_changed')
        expected = os.environ.get('OFFMENU_RUN_LAYOUT_SHA256')
        if expected is not None and expected != self.config_digest:
            raise ValueError('runner_layout_changed')

    def verify_lease(self):
        self.verify()
        if self.legacy:
            return
        if os.environ.get('OFFMENU_RUN_LAYOUT_SHA256') != self.config_digest:
            raise ValueError('runner_layout_admission_required')
        try:
            fd = int(os.environ['OFFMENU_RUN_FD'])
            info = os.fstat(fd)
            if private_identity(self.lock) != (info.st_dev, info.st_ino) or not stat.S_ISREG(info.st_mode):
                raise ValueError('runner_layout_lock_changed')
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            if os.environ.get('OFFMENU_RUN_LAYOUT_BINDING_SHA256') != self.admission_digest(fd):
                raise ValueError('runner_layout_binding_changed')
        except (KeyError, OSError, ValueError) as error:
            raise ValueError('runner_layout_lease_required') from error

    def binding(self, lock_fd=None):
        value = {'schema': SCHEMA, 'config_sha256': self.config_digest,
                 'roots': {name: str(getattr(self, name)) for name in ('runtime', 'public_staging', 'normalization', 'household')},
                 'singleton': {'path': str(self.lock)}}
        value['root_identities'] = dict(zip(('runtime', 'public_staging', 'normalization', 'household'), self.root_identities))
        if lock_fd is not None:
            info = os.fstat(lock_fd)
            if private_identity(self.lock) != (info.st_dev, info.st_ino):
                raise ValueError('runner_layout_lock_changed')
            value['singleton'].update(device=info.st_dev, inode=info.st_ino)
        return value

    def admission_digest(self, fd):
        return hashlib.sha256(json.dumps(self.binding(fd), sort_keys=True).encode()).hexdigest()

    def activate(self, fd):
        """Pin the common lease/layout for this process and its re-exec only."""
        self.verify()
        if self.legacy:
            return
        expected = os.environ.get('OFFMENU_RUN_LAYOUT_BINDING_SHA256')
        actual = self.admission_digest(fd)
        if expected is not None and expected != actual:
            raise ValueError('runner_layout_binding_changed')
        os.environ.update(OFFMENU_RUN_FD=str(fd), OFFMENU_RUN_LAYOUT_SHA256=self.config_digest,
                          OFFMENU_RUN_LAYOUT_BINDING_SHA256=actual)
        self.verify_lease()


def _load(path):
    private_identity(path)
    flags = os.O_RDONLY | os.O_NOFOLLOW
    fd = os.open(path, flags)
    try:
        before = os.fstat(fd)
        if (before.st_dev, before.st_ino) != private_identity(path) or before.st_size > 16384:
            raise ValueError('runner_layout_config_changed')
        raw = os.read(fd, 16385)
        after = os.fstat(fd)
        if (before.st_size, before.st_mtime_ns, before.st_ctime_ns) != (after.st_size, after.st_mtime_ns, after.st_ctime_ns):
            raise ValueError('runner_layout_config_changed')
    finally:
        os.close(fd)
    def unique(pairs):
        value = {}
        for key, item in pairs:
            if key in value:
                raise ValueError('runner_layout_duplicate_key')
            value[key] = item
        return value
    value = json.loads(raw, object_pairs_hook=unique)
    names = ('runtime', 'public_staging', 'normalization', 'household')
    if not isinstance(value, dict) or set(value) != {'schema', 'lock', *names} or value['schema'] != SCHEMA:
        raise ValueError('runner_layout_schema_refused')
    roots = [safe_absolute(value[name]) for name in names]
    if len(set(roots)) != 4 or any(a in b.parents or b in a.parents for i, a in enumerate(roots) for b in roots[i + 1:]):
        raise ValueError('runner_layout_overlapping_roots')
    identities = tuple(private_identity(root, directory=True) for root in roots)
    lock = safe_absolute(value['lock'])
    if any(lock == root or root in lock.parents for root in roots):
        raise ValueError('runner_layout_lock_must_be_external')
    parent = lock.parent.stat()
    if not stat.S_ISDIR(parent.st_mode) or parent.st_uid != os.getuid() or parent.st_mode & 0o022:
        raise ValueError('runner_layout_lock_parent_refused')
    if lock.exists():
        private_identity(lock)
    return StateLayout(*roots, lock, path, hashlib.sha256(raw).hexdigest(), identities)


def resolve_layout(state_dir, *, require_lease=True):
    selected = os.environ.get('OFFMENU_RUN_LAYOUT')
    if selected:
        layout = _load(safe_absolute(selected))
        layout.verify()
        if require_lease:
            layout.verify_lease()
        return layout
    if os.environ.get('OFFMENU_RUN_LEGACY_FIXTURE') != '1':
        raise ValueError('runner_layout_required')
    # Explicit fixtures retain each legacy API's own path/error semantics.
    state = Path(os.path.abspath(state_dir))
    return StateLayout(state.parent, state / 'staging', state / 'normalization-private',
                       state / 'private-household', state.parent.parent / 'offmenu-run.lock',
                       legacy=True, legacy_ingest=state)
