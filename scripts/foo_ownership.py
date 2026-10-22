"""Local-primary admission for the fixed Foo dispatcher. Never installs state."""
from contextlib import contextmanager
import fcntl
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import stat
import sys
import time


class OwnershipError(ValueError):
    pass


def read_private(path):
    path = Path(path)
    if not path.is_absolute() or any(p.is_symlink() for p in (path, *path.parents)):
        raise OwnershipError('ownership-path-refused')
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    try:
        before = os.fstat(fd)
        if (not stat.S_ISREG(before.st_mode) or before.st_uid != os.getuid()
                or stat.S_IMODE(before.st_mode) != 0o600 or before.st_size > 16384):
            raise OwnershipError('ownership-private-file-required')
        raw = os.read(fd, 16385)
        after = os.fstat(fd)
        named = path.lstat()
        if ((before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns, before.st_ctime_ns)
                != (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns, after.st_ctime_ns)
                or (named.st_dev, named.st_ino) != (before.st_dev, before.st_ino)
                or len(raw) != before.st_size):
            raise OwnershipError('ownership-file-changed')
    finally:
        os.close(fd)
    def unique(pairs):
        value = {}
        for key, item in pairs:
            if key in value:
                raise OwnershipError('ownership-duplicate-key')
            value[key] = item
        return value
    value = json.loads(raw, object_pairs_hook=unique,
                       parse_constant=lambda _: (_ for _ in ()).throw(OwnershipError('ownership-json-refused')))
    return value, hashlib.sha256(raw).hexdigest()


def load_layout(code):
    # This file must be composed with reviewed3478 runner_paths by00, never
    # loaded from an environment-selected Python module or another checkout.
    path = Path(code) / 'manual-action' / 'runner_paths.py'
    if any(p.is_symlink() for p in (path, *path.parents)):
        raise OwnershipError('ownership-layout-module-refused')
    spec = importlib.util.spec_from_file_location('_offmenu_foo_runner_paths', path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module.resolve_layout(Path(code) / '.git' / 'offmenu-runner', require_lease=False)


class Admission:
    def __init__(self, layout, fd, identity, run_id, attempt):
        self.layout, self.fd = layout, fd
        self.identity, self.run_id, self.attempt = identity, run_id, attempt
        self.owner_digest = None
        self.binding_digest = None

    def verify(self):
        self.layout.verify_lease()
        binding, binding_digest = read_private(self.layout.runtime / 'layout-admission.json')
        # JSON arrays represent the tuple root identities in the frozen API.
        expected = json.loads(json.dumps(self.layout.binding(self.fd)))
        if binding != expected or (self.binding_digest is not None and binding_digest != self.binding_digest):
            raise OwnershipError('ownership-layout-binding-changed')
        value, digest = read_private(self.layout.runtime / 'foo-fallback-admission.json')
        keys = {'schema', 'owner', 'boundary', 'native_thread_id', 'handoff_id',
                'handoff_evidence', 'request_identity', 'github_run_id', 'github_run_attempt',
                'config_sha256', 'binding_sha256', 'expires_unix'}
        if not isinstance(value, dict) or set(value) != keys:
            raise OwnershipError('ownership-handoff-schema-refused')
        if (value['schema'] != 'offmenu-foo-fallback/1' or value['owner'] != 'actions-fallback'
                or value['boundary'] != 'safe' or any(not isinstance(value[k], str) or not value[k].strip()
                for k in ('native_thread_id', 'handoff_id', 'handoff_evidence'))):
            raise OwnershipError('native-ownership-or-no-safe-handoff')
        if (value['request_identity'] != self.identity or value['github_run_id'] != self.run_id
                or value['github_run_attempt'] != self.attempt
                or value['config_sha256'] != self.layout.config_digest
                or value['binding_sha256'] != self.layout.admission_digest(self.fd)):
            raise OwnershipError('ownership-handoff-identity-mismatch')
        if type(value['expires_unix']) is not int or not time.time() < value['expires_unix'] <= time.time() + 1800:
            raise OwnershipError('ownership-handoff-expired-or-unbounded')
        if self.owner_digest is not None and digest != self.owner_digest:
            raise OwnershipError('ownership-handoff-changed')
        self.owner_digest, self.binding_digest = digest, binding_digest

    def child_env(self):
        self.verify()
        return {key: os.environ[key] for key in ('OFFMENU_RUN_LAYOUT', 'OFFMENU_RUN_FD',
                'OFFMENU_RUN_LAYOUT_SHA256', 'OFFMENU_RUN_LAYOUT_BINDING_SHA256')}


@contextmanager
def acquire(code, identity, run_id, attempt):
    # No legacy-fixture or free-lock fallback. Even an idle native-owned session
    # remains owner until an exact explicit safe-boundary handoff is supplied.
    if not os.environ.get('OFFMENU_RUN_LAYOUT') or os.environ.get('OFFMENU_RUN_LEGACY_FIXTURE'):
        raise OwnershipError('ownership-selected-layout-required')
    layout = load_layout(code)
    if layout.legacy:
        raise OwnershipError('ownership-operational-layout-required')
    fd = os.open(layout.lock, os.O_RDWR | os.O_NOFOLLOW)  # existing singleton only
    keys = ('OFFMENU_RUN_FD', 'OFFMENU_RUN_LAYOUT_SHA256', 'OFFMENU_RUN_LAYOUT_BINDING_SHA256')
    saved = {key: os.environ.get(key) for key in keys}
    try:
        info = os.fstat(fd)
        if (not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid()
                or stat.S_IMODE(info.st_mode) != 0o600):
            raise OwnershipError('ownership-private-lock-required')
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        layout.activate(fd)
        admission = Admission(layout, fd, identity, run_id, attempt)
        admission.verify()
        yield admission
    finally:
        os.close(fd)  # inherited direct children retain the same flock custody
        for key, value in saved.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value
