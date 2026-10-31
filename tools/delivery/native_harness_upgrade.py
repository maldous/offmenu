"""Explicit owner-only sealed-directory upgrade; no CLI, service start or retry.

Production admission must come from the sole owner after independent review and
mandatory host approval. Python capability objects are not JSON authority. The
private _synthetic root seam is for disposable /tmp tests only. First-install
receipts are neither consumed nor changed. Partial effects never auto-roll back.
"""
from contextlib import ExitStack, contextmanager
import ctypes
from dataclasses import dataclass
import fcntl
import hashlib
import json
import os
from pathlib import Path
import stat
import subprocess
import time

from native_harness_adoption import TARGETS, fields, require, sha, identifier
from native_harness_contract import fingerprint
import protected_owner_install as protected


STATE = '/var/lib/offmenu-publisher'
SERVICE = 'offmenu-stokowski-current.service'
MAX_FILES = 50000
MAX_FILE = 64 * 1024 * 1024
MAX_TOTAL = 1024 * 1024 * 1024


@dataclass(frozen=True)
class OwnerAdmission:
    """Trusted out-of-band exact-source permission; never load from worker JSON."""
    owner: str
    plan_sha256: str
    upgrade_sha256: str
    host_confirmation_sha256: str
    expires_at: float


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


def upgrade_digest(value):
    raw = protected.encoded(value)
    require(len(raw) <= 32 * 1024 * 1024, 'upgrade_manifest_bound')
    return protected.sha(raw)


def fresh(value, now, seconds=300):
    return type(value) in (int, float) and 0 <= now - value <= seconds


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

    @contextmanager
    def locks(self, runtime):
        with ExitStack() as stack:
            for name in (runtime + '/coordinator.lock', STATE + '/integration/repository-owner.lock'):
                path = self.path(name)
                fd = os.open(path, os.O_RDWR | os.O_NOFOLLOW | os.O_NONBLOCK)
                stack.callback(os.close, fd)
                info = os.fstat(fd)
                require(stat.S_ISREG(info.st_mode) and info.st_nlink == 1
                        and info.st_uid == self.uid and not info.st_mode & 0o022, 'existing_lock')
                fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            yield

    def create(self, absolute, value):
        path = self.path(absolute)
        protected.write_new(path, protected.encoded(value), 0o600)
        protected.sync_dir(path.parent)

    def move(self, old, new):
        source, target = self.path(old), self.path(new)
        # Linux create-only rename, including directory targets; no check/rename
        # overwrite race. Unsupported platforms hold rather than use os.rename.
        libc = ctypes.CDLL(None, use_errno=True)
        rename = getattr(libc, 'renameat2', None)
        require(rename is not None, 'rename_noreplace_unavailable')
        result = rename(-100, os.fsencode(source), -100, os.fsencode(target), 1)
        if result != 0:
            raise OSError(ctypes.get_errno(), 'upgrade rename refused')
        protected.sync_dir(source.parent)
        if target.parent != source.parent:
            protected.sync_dir(target.parent)

    def verify(self, absolute, closure):
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
                    require(not any(p.startswith('.env') or p in ('credentials', 'auth.json', 'credentials.json')
                            or p.endswith(('.key', '.pem', '.log')) for p in Path(name).parts), 'secret_or_log_path')
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
    target = TARGETS[role]
    parent = str(Path(target).parent)
    return target, parent + '/.native-upgrade-' + operation + '-' + role + '.new', parent + '/.native-upgrade-' + operation + '-' + role + '.old'


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
    fields(upgrade, 'version kind operation_id preflight_sha256 old new legacy_receipts')
    require(type(upgrade['version']) is int and upgrade['version'] == 1
            and upgrade['kind'] == 'native-harness-upgrade-v1', 'upgrade_version')
    sha(upgrade['operation_id'])
    require(upgrade['preflight_sha256'] == admission.plan_sha256, 'upgrade_plan')
    fields(upgrade['old'], ' '.join(TARGETS))
    fields(upgrade['new'], ' '.join(TARGETS))
    for role, key in (('owner_source', 'source_sha256'), ('owner_venv', 'runtime_sha256'),
                      ('owner_config', 'config_sha256')):
        require(upgrade_digest(upgrade['old'][role]) == plan['legacy_snapshot'][key], 'old_snapshot_closure')
    target = plan['request']['target']
    require(upgrade_digest(upgrade['new']['owner_venv']) == target['dependencies']['sha256']
            and upgrade_digest(upgrade['new']['owner_config']) == target['config']['sha256'], 'new_config_dependency_closure')
    for ref in target['files']:
        require(upgrade['new']['owner_source']['files'].get(ref['path'], {}).get('sha256')
                == ref['sha256'], 'new_source_artifact')
    for side, head in (('old', plan['legacy_snapshot']['source_head']),
                       ('new', target['source_head'])):
        require(upgrade[side]['owner_source']['files'].get('.git/HEAD', {}).get('sha256')
                == protected.sha((head + '\n').encode()), 'source_head_readback')
    # Old/new full closure manifests must be independently qualified in the
    # admitted upgrade digest, not inferred from an installer's legacy manifest.
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
    stopped(host, plan, observation, now)
    now = time.time()
    require(now < admission.expires_at, 'admission_expired')
    require(fresh(observation.observed_at, now), 'native_quiescence_required')


def execute(plan_bytes, upgrade, *, admission, quiescence, host=None):
    """One admitted attempt; never start services, retire legacy or auto-rollback.

    All staged slots already exist, sealed by the owner. Every old closure moves
    intact to a create-only sibling custody slot before its new closure moves.
    A permanent intent precedes all moves. Any failure/unknown effect requires
    observe() and explicit owner reconciliation; execute() always refuses replay.
    """
    upgrade = protected.record(protected.encoded(upgrade))
    now = time.time()
    plan = qualify(plan_bytes, upgrade, admission, now)
    host = host or Host()
    operation = upgrade['operation_id']
    receipt = STATE + '/native-upgrade-' + operation + '.intent.json'
    result_path = STATE + '/native-upgrade-' + operation + '.installed.json'
    old_fence = STATE + '/native-upgrade-from-' + upgrade_digest(upgrade['old']) + '.intent.json'
    with host.locks(plan['legacy_snapshot']['runtime_path']):
        require(not os.path.lexists(host.path(receipt))
                and not os.path.lexists(host.path(result_path))
                and not os.path.lexists(host.path(old_fence)), 'prior_upgrade_no_replay')
        stopped(host, plan, quiescence, time.time())
        for path, pin in upgrade['legacy_receipts'].items():
            require(protected.sha(protected.regular(host.path(path), 8*1024*1024)) == pin, 'legacy_receipt_drift')
        for role in TARGETS:
            target, stage, backup = locations(role, operation)
            require(not os.path.lexists(host.path(backup)), 'rollback_slot_exists')
            host.verify(target, upgrade['old'][role])
            host.verify(stage, upgrade['new'][role])
        require(time.time() < admission.expires_at, 'admission_expired')
        intent = dict(kind='native-upgrade-intent-v1', upgrade=upgrade,
            plan_sha256=admission.plan_sha256, quiescence_sha256=quiescence.evidence_sha256,
            host_confirmation_sha256=admission.host_confirmation_sha256,
            runtime_path=plan['legacy_snapshot']['runtime_path'])
        # Old-closure fence precedes the operation fence. A crash between them
        # still suppresses a new ID/preflight attempting the same old closure.
        mutation_guard(host, plan, quiescence, admission)
        host.create(old_fence, intent)
        mutation_guard(host, plan, quiescence, admission)
        host.create(receipt, intent)
        for role in TARGETS:
            require(time.time() < admission.expires_at, 'admission_expired')
            stopped(host, plan, quiescence, time.time())
            target, stage, backup = locations(role, operation)
            host.verify(target, upgrade['old'][role])
            host.verify(stage, upgrade['new'][role])
            mutation_guard(host, plan, quiescence, admission)
            host.move(target, backup)
            mutation_guard(host, plan, quiescence, admission)
            host.move(stage, target)
        readback = observe(upgrade, host=host)
        require(readback['installed_verified'] and readback['rollback_verified'], 'installed_readback_mismatch')
        mutation_guard(host, plan, quiescence, admission)
        host.create(result_path, dict(kind='native-upgrade-installed-v1', upgrade_sha256=upgrade_digest(upgrade),
                                     readback=readback, active_observed=False, legacy_retired=False))
        return readback


def observe(upgrade, *, host=None):
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
                host.verify(path, closure)
                axes[name] = 'verified'
            except (OSError, ValueError):
                axes[name] = 'unknown-or-mismatch'
        results[role] = axes
    return dict(operation_id=operation, upgrade_sha256=upgrade_digest(upgrade), closures=results,
        intent_verified=intent_ok,
        legacy_receipts_verified=receipts_ok,
        installed_verified=intent_ok and receipts_ok and all(row['installed'] == 'verified' for row in results.values()),
        rollback_verified=intent_ok and all(row['rollback'] == 'verified' for row in results.values()),
        active_observed=False, legacy_retired=False, replay_authorized=False)


def verify_active(upgrade, *, host=None):
    """Separate actual service observation after owner-managed activation.

    This never starts a service or claims product/functional/legacy retirement
    acceptance. Exact installed bytes are checked both sides of service readback.
    """
    host = host or Host()
    before = observe(upgrade, host=host)
    require(before['installed_verified'] and before['rollback_verified'], 'active_closure_mismatch')
    intent = protected.record(protected.regular(host.path(
        STATE + '/native-upgrade-' + upgrade['operation_id'] + '.intent.json'), 32*1024*1024))
    runtime = intent.get('runtime_path')
    require(type(runtime) is str and runtime.startswith('/'), 'active_runtime_binding')
    state = host.service_state()
    require(state.get('ActiveState') == 'active' and state.get('SubState') == 'running'
            and state.get('MainPID', '').isdigit() and int(state['MainPID']) > 0, 'service_not_active')
    require(host.process_bound(int(state['MainPID']), runtime), 'active_process_binding')
    after = observe(upgrade, host=host)
    require(after['installed_verified'] and after['rollback_verified'], 'active_readback_drift')
    require(host.service_state() == state and host.process_bound(int(state['MainPID']), runtime),
            'active_process_changed')
    return dict(after, active_observed=True, service=state)
