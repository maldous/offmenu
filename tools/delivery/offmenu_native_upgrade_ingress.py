"""Fixed Foo owner ingress for one reviewed OffMenu package replacement."""

from contextlib import contextmanager
from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path
import pwd
import re
import stat
import subprocess
import sys
import time
from uuid import UUID

CODE = Path('/usr/local/lib/offmenu-native-upgrade')
STATE = Path('/var/lib/offmenu-publisher/upgrade-ingress')
SIGNERS = Path('/etc/offmenu-native-upgrade/allowed_signers')
NAMESPACE = 'offmenu-foo-native-upgrade-v1'
REPOSITORY = 'maldous/offmenu'
SERVICE = 'offmenu-stokowski-current.service'
TARGET = '/opt/offmenu-publisher'
SMALL = 65536
LARGE = 32 * 1024 * 1024
FENCE = 'publisher-fence'
MAX_OPERATIONS = 4096
RECORDS = ('package-review.json', 'preflight.json', 'upgrade.json', 'custody.json')
OWNER = re.compile(r'[A-Za-z_][A-Za-z0-9_.-]{0,63}')
HEX = re.compile(r'[0-9a-f]{64}')
GIT_OID = re.compile(r'[0-9a-f]{40}')


def require(ok, reason):
    if not ok:
        raise ValueError(reason)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def protected_dirs(path):
    for directory in (*reversed(path.parents), path):
        info = directory.lstat()
        require(stat.S_ISDIR(info.st_mode) and info.st_uid == 0 and not info.st_mode & 0o022,
                'protected_directory_required')


def protected_open(path):
    protected_dirs(path.parent)
    stream = os.fdopen(os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK), 'rb')
    info = os.fstat(stream.fileno())
    if not (stat.S_ISREG(info.st_mode) and info.st_uid == 0 and info.st_nlink == 1
            and not info.st_mode & 0o022):
        stream.close()
        raise ValueError('protected_file_required')
    return stream


def read(path, limit):
    with protected_open(path) as stream:
        raw = stream.read(limit + 1)
    require(0 < len(raw) <= limit, 'record_size')
    return raw


def shape(value, *keys):
    require(type(value) is dict and set(value) == set(keys), 'record_fields')
    return value


def record(raw):
    def pairs(items):
        value = dict(items)
        require(len(value) == len(items), 'duplicate_record_key')
        return value

    def invalid(_value):
        raise ValueError('nonfinite_record')

    value = json.loads(raw.decode('utf-8'), object_pairs_hook=pairs, parse_constant=invalid)
    require(type(value) is dict, 'record_object')
    return value


def encode(value):
    return (json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=True,
                       allow_nan=False) + '\n').encode('ascii')


def request_record(packet, operation, release):
    raw = read(packet / 'request.json', SMALL)
    request = shape(record(raw), 'schema', 'action', 'repository', 'unit', 'target', 'owner',
                    'operation_id', 'package_sha256', 'release_sha256', 'inputs', 'issued_at', 'expires_at')
    require(raw == encode(request), 'noncanonical_request')
    require((request['schema'], request['action'], request['repository'], request['unit'],
             request['target'], request['operation_id']) ==
            ('offmenu.foo-native-upgrade/1', 'replace', REPOSITORY, SERVICE, TARGET, operation),
            'fixed_scope_refused')
    require(request['release_sha256'] == release, 'reviewed_release_mismatch')
    owner = request['owner']
    require(type(owner) is str and OWNER.fullmatch(owner), 'owner_account')
    require(pwd.getpwnam(owner).pw_uid > 0, 'nonroot_owner_account_required')
    for value in [request['package_sha256'], *shape(request['inputs'], *RECORDS).values()]:
        require(type(value) is str and HEX.fullmatch(value), 'digest_required')
    require(type(request['issued_at']) is type(request['expires_at']) is int
            and 0 < request['expires_at'] - request['issued_at'] <= 300, 'request_window')
    return request, raw


def signed_request(packet, operation, release):
    request, raw = request_record(packet, operation, release)
    owner = request['owner']
    with protected_open(SIGNERS) as signers, protected_open(packet / 'request.json.sig') as signature:
        anchor = signers.read(SMALL + 1)
        lines = anchor.strip().splitlines()
        require(0 < len(anchor) <= SMALL and len(lines) == 1, 'one_enrolled_signer_required')
        line = lines[0].split(maxsplit=3)
        require(len(line) >= 3 and line[0] == owner.encode('ascii')
                and line[1].startswith((b'ssh-', b'ecdsa-', b'sk-')), 'enrolled_signer_mismatch')
        signers.seek(0)
        fds = (signers.fileno(), signature.fileno())
        require(0 < os.fstat(fds[1]).st_size <= SMALL, 'signature_size')
        p = subprocess.run(
            ['/usr/bin/ssh-keygen', '-Y', 'verify', '-f', f'/proc/self/fd/{fds[0]}',
             '-I', owner, '-n', NAMESPACE, '-s', f'/proc/self/fd/{fds[1]}'],
            pass_fds=fds, input=raw, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            env={'PATH': '/usr/bin:/bin', 'LC_ALL': 'C'}, timeout=5, check=False)
        require(p.returncode == 0, 'owner_signature_refused')
    return request, raw, anchor


def create(path, value):
    data = encode(value)
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, 'wb') as stream:
        stream.write(data)
        stream.flush()
        os.fsync(stream.fileno())
    parent = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        os.fsync(parent)
    finally:
        os.close(parent)


def original(path):
    try:
        return record(read(path, SMALL))
    except FileNotFoundError:
        return None


def custody_inputs(value, api):
    c = shape(value, 'quiescence', 'locks', 'publisher', 'public_ca_pins')
    q = dict(c['quiescence'])
    q['unresolved_operation_ids'] = tuple(q['unresolved_operation_ids'])
    locks = dict(c['locks'])
    rows = []
    for value in locks['locks']:
        row = dict(value)
        row['identity'] = api.NodeIdentity(**row['identity'])
        row['parents'] = tuple(api.ParentCustody(x['path'], api.NodeIdentity(**x['identity']))
                               for x in row['parents'])
        row['permitted_writers'] = tuple(row['permitted_writers'])
        rows.append(api.LockRecord(**row))
    locks['locks'] = tuple(rows)
    publisher = dict(c['publisher'])
    publisher['directory'] = api.NodeIdentity(**publisher['directory'])
    publisher['key'] = api.NodeIdentity(**publisher['key'])
    return (api.Quiescence(**q), api.LockCustody(**locks), api.PublisherConfigCustody(**publisher),
            None if c['public_ca_pins'] is None else
            tuple(api.PublicCARecordPin(**pin) for pin in c['public_ca_pins']))


def publisher_fence():
    directory = STATE / FENCE
    protected_dirs(directory)
    return directory


def installed_receipt(canonical_state, operation):
    return read(canonical_state / f'native-upgrade-{operation}.installed.json', SMALL)


def operation_status(packet, binding, canonical_state):
    fence = original(publisher_fence() / packet.name)
    prior = original(packet / 'ingress-intent.json')
    completion = original(packet / 'ingress-result.json')
    require(fence is None or fence == binding, 'publisher_intent_conflict')
    require(prior is None or prior == fence == binding, 'original_intent_conflict')
    if completion is not None:
        require(prior == binding and completion == dict(binding, state='installed',
                    installed_receipt_sha256=sha(installed_receipt(canonical_state, packet.name))),
                'original_result_conflict')
    return dict(binding, state='installed' if completion else 'reconcile' if fence else 'not_started')


def operation_names(directory, reserved=None):
    names = set()
    for entry in directory.iterdir():
        if entry == reserved:
            continue
        require(len(names) < MAX_OPERATIONS, 'publisher_fence_bound')
        require(HEX.fullmatch(entry.name), 'publisher_fence_entry')
        names.add(entry.name)
    return names


def check_publisher_fence(canonical_state):
    """Check both immutable journal sides before starting any replacement."""
    fence = publisher_fence()
    packets = operation_names(STATE, reserved=fence)
    intents = operation_names(fence)
    require(intents <= packets, 'publisher_packet_missing')
    for name in sorted(packets):
        packet = STATE / name
        protected_dirs(packet)
        if name not in intents:
            # Prepared packets can lack receipts, but a per-operation receipt
            # with no fixed publisher intent is contradictory.
            require(original(packet / 'ingress-intent.json') is None
                    and original(packet / 'ingress-result.json') is None,
                    'publisher_intent_missing')
            continue
        binding = shape(original(fence / name), 'operation_id', 'confirmation_sha256')
        require(binding['operation_id'] == name
                and type(binding['confirmation_sha256']) is str
                and HEX.fullmatch(binding['confirmation_sha256']), 'publisher_intent_conflict')
        require(operation_status(packet, binding, canonical_state)['state'] == 'installed',
                'publisher_original_requires_reconciliation')


def request_inputs(packet, request):
    inputs = {name: read(packet / name, LARGE if name == 'upgrade.json' else 262144)
              for name in RECORDS}
    require({name: sha(data) for name, data in inputs.items()} == request['inputs'],
            'signed_inputs_changed')
    review = shape(record(inputs['package-review.json']), 'schema', 'owner', 'head', 'tree',
                   'author', 'reviewer', 'verdict')
    require((review['schema'], review['owner'], review['verdict']) ==
            ('offmenu.native-package-review/1', request['owner'], 'accept')
            and all(type(review[key]) is str and OWNER.fullmatch(review[key])
                    for key in ('author', 'reviewer'))
            and review['reviewer'].casefold() not in
            (review['author'].casefold(), request['owner'].casefold()), 'independent_review_required')
    return inputs, review


@dataclass(frozen=True)
class VerifiedFooRun:
    """Facts from the platform's protected current-job authenticator.

    This is a local return type for a qualified adapter, never wire JSON
    accepted from the current SSH session or a runner receipt on stdout.
    """
    workspace: str
    runnable: str
    platform_run_id: str
    platform_actor: str
    owner: str
    operation_id: str
    request_sha256: str
    package_sha256: str
    release_sha256: str
    source_head: str
    source_tree: str
    issued_at: int
    expires_at: int


def audit_runner_request(operation, release, canonical_state, authenticate=None):
    """Read-only receiver boundary. No effect entry is wired to this audit."""
    require(callable(authenticate), 'authenticated_runner_job_provenance_unavailable')
    require(type(operation) is str and HEX.fullmatch(operation), 'operation_id')
    packet = STATE / operation
    request, raw = request_record(packet, operation, release)
    # The adapter resolves the actual current invocation from the host-side
    # authenticated session. No actor, run ID or receipt is passed to it.
    run = authenticate()
    require(type(run) is VerifiedFooRun, 'authenticated_runner_job_provenance_required')
    require(run.workspace == 'foo' and run.runnable == 'u/admin/foo_root_jobs'
            and type(run.platform_actor) is str and 0 < len(run.platform_actor) <= 200
            and run.platform_actor.isprintable(), 'runner_binding_mismatch')
    require(type(run.platform_run_id) is str, 'runner_run_id')
    run_id = UUID(run.platform_run_id)
    require(run_id.int != 0 and str(run_id) == run.platform_run_id, 'runner_run_id')
    require((run.owner, run.operation_id, run.request_sha256, run.package_sha256, run.release_sha256) ==
            (request['owner'], operation, sha(raw), request['package_sha256'], release),
            'runner_request_mismatch')
    require(type(run.issued_at) is type(run.expires_at) is int
            and request['issued_at'] <= run.issued_at <= time.time() < run.expires_at <= request['expires_at'],
            'runner_attestation_window')
    _, review = request_inputs(packet, request)
    manifest_raw = read(packet / 'package' / 'manifest.json', LARGE)
    require(sha(manifest_raw) == run.package_sha256, 'runner_package_pin')
    manifest = record(manifest_raw)
    require(type(run.source_head) is str and GIT_OID.fullmatch(run.source_head)
            and type(run.source_tree) is str and GIT_OID.fullmatch(run.source_tree)
            and (run.owner, run.source_head, run.source_tree) ==
            (manifest.get('owner'), manifest.get('head'), manifest.get('tree')) ==
            (review['owner'], review['head'], review['tree'])
            and manifest.get('review') ==
            {'path': 'package-review.json', 'sha256': request['inputs']['package-review.json']},
            'runner_source_review_binding')
    result = operation_status(packet, dict(operation_id=operation, confirmation_sha256=sha(raw)),
                              canonical_state)
    return dict(result, runner_provenance_verified=True, effect_authorized=False)


def run(action, operation, release, package_api, upgrade_api):
    require(type(operation) is str and HEX.fullmatch(operation), 'operation_id')
    packet = STATE / operation
    request, raw, anchor = signed_request(packet, operation, release)
    binding = dict(operation_id=operation, confirmation_sha256=sha(raw))
    canonical_state = Path(upgrade_api.STATE)
    status = operation_status(packet, binding, canonical_state)
    if action == 'status' or status['state'] == 'installed':
        return status
    require(action == 'replace' and status['state'] == 'not_started', 'original_requires_reconciliation')

    def current():
        require(request['issued_at'] <= time.time() < request['expires_at'], 'owner_confirmation_expired')
        require(read(SIGNERS, SMALL) == anchor and read(packet / 'request.json', SMALL) == raw,
                'owner_confirmation_changed')

    current()
    inputs, review = request_inputs(packet, request)
    acceptance = package_api.PackageAcceptance(
        review['owner'], review['head'], review['tree'],
        {'path': 'package-review.json', 'sha256': sha(inputs['package-review.json'])})
    plan_bytes = inputs['preflight.json']
    upgrade = record(inputs['upgrade.json'])
    package = packet / 'package'
    protected_dirs(package)
    manifest, payload = package_api.read_package(package, request['package_sha256'])
    del payload
    require((manifest['owner'], manifest['head'], manifest['tree'], manifest['review']) ==
            (acceptance.owner, acceptance.head, acceptance.tree, acceptance.review)
            and upgrade['operation_id'] == operation and manifest['roles'] == upgrade['new'],
            'reviewed_closure_mismatch')
    q, locks, publisher, ca = custody_inputs(record(inputs['custody.json']), upgrade_api)
    admission = upgrade_api.OwnerAdmission(
        acceptance.owner, sha(plan_bytes), upgrade_api.upgrade_digest(upgrade), sha(raw),
        request['expires_at'], upgrade_api.upgrade_digest(upgrade_api.asdict(locks)),
        upgrade_api.upgrade_digest(upgrade_api.asdict(publisher)),
        None if ca is None else upgrade_api.upgrade_digest([upgrade_api.asdict(pin) for pin in ca]))
    materialize = package_api.MaterializeAdmission(
        acceptance.owner, request['package_sha256'], operation, sha(raw), request['expires_at'])

    class LockedHost(upgrade_api.Host):
        @contextmanager
        def locks(self, custody):
            require(custody == locks and self._lock_custody == locks, 'existing_lock_binding')
            self.verify_locks()
            current()
            yield

    host = LockedHost()
    now = time.time()
    plan = upgrade_api.qualify(plan_bytes, upgrade, admission, now)
    upgrade_api.qualify_lock_custody(locks, admission, plan, q, host, now)
    upgrade_api.qualify_publisher_custody(publisher, admission.publisher_config_custody_sha256, host, now)
    upgrade_api.qualify_public_ca_pins(ca, admission.public_ca_pins_sha256, upgrade)
    with super(LockedHost, host).locks(locks):
        require(operation_status(packet, binding, canonical_state)['state'] == 'not_started',
                'original_requires_reconciliation')
        check_publisher_fence(canonical_state)
        with host.publisher_config(publisher):
            require(not any(os.path.lexists(host.path(path)) for path in (
                f'{upgrade_api.STATE}/native-upgrade-{operation}.intent.json',
                f'{upgrade_api.STATE}/native-upgrade-{operation}.installed.json',
                f"{upgrade_api.STATE}/native-upgrade-from-{upgrade_api.upgrade_digest(upgrade['old'])}.intent.json",
            )), 'prior_upgrade_no_replay')
            for path, pin in upgrade['legacy_receipts'].items():
                require(sha(upgrade_api.protected.regular(host.path(path), 8 * 1024 * 1024)) == pin,
                        'legacy_receipt_drift')
            for role in upgrade_api.TARGETS:
                target, _, backup = upgrade_api.locations(role, operation)
                require(not os.path.lexists(host.path(backup)), 'rollback_slot_exists')
                host.verify_role(role, target, upgrade['old'][role])
            upgrade_api.stopped(host, plan, q, time.time())
            host.verify_locks()
            host.verify_publisher_custody()
            current()
            create(publisher_fence() / operation, binding)
            create(packet / 'ingress-intent.json', binding)
            current()
            package_api.materialize(package, expected_sha256=request['package_sha256'],
                                    admission=materialize)
        current()
        upgrade_api.execute(plan_bytes, upgrade, admission=admission, quiescence=q,
                            lock_custody=locks, publisher_config_custody=publisher,
                            public_ca_pins=ca, host=host)
        # Persist only the result already recorded by the canonical upgrade.
        receipt = installed_receipt(canonical_state, operation)
        installed = record(receipt)
        require(installed.get('kind') == 'native-upgrade-installed-v1'
                and installed.get('upgrade_sha256') == admission.upgrade_sha256
                and installed.get('readback', {}).get('installed_verified') is True
                and installed['readback'].get('rollback_verified') is True,
                'canonical_result_refused')
        result = dict(binding, state='installed')
        create(packet / 'ingress-result.json', dict(result, installed_receipt_sha256=sha(receipt)))
        return result


def release_digest():
    protected_dirs(CODE)
    files = {}
    total = 0

    def fail(error):
        raise error

    for base, directories, names in os.walk(CODE, followlinks=False, onerror=fail):
        for name in directories:
            protected_dirs(Path(base) / name)
        for name in names:
            path = Path(base) / name
            with protected_open(path) as stream:
                size = os.fstat(stream.fileno()).st_size
                total += size
                require(len(files) < 50000 and size <= 64 * 1024 * 1024
                        and total <= 1024 * 1024 * 1024, 'installed_release_bound')
                files[str(path.relative_to(CODE))] = hashlib.file_digest(stream, 'sha256').hexdigest()
    return sha(encode(files))


def main():
    require(os.getresuid() == (0, 0, 0) and sys.flags.isolated
            and sys.flags.no_site and sys.dont_write_bytecode, 'fixed_root_invocation')
    delivery = CODE / 'tools/delivery'
    require(Path(__file__) == delivery / 'offmenu_native_upgrade_ingress.py', 'fixed_code_path')
    os.umask(0o077)
    release = release_digest()
    if sys.argv[1:] == ['release-id']:
        output = {'release_sha256': release}
    else:
        require(len(sys.argv) == 3 and sys.argv[1] in ('replace', 'status'), 'fixed_command')
        # Only this separately reviewed root-controlled code, never the candidate.
        sys.path.extend((str(delivery), str(CODE / 'deps')))
        import native_harness_package
        import native_harness_upgrade
        output = run(sys.argv[1], sys.argv[2], release, native_harness_package, native_harness_upgrade)
    print(encode(output).decode('ascii'), end='')


if __name__ == '__main__':
    try:
        main()
    except (OSError, ValueError, TypeError, KeyError, RuntimeError, subprocess.SubprocessError):
        sys.stderr.write('offmenu-native-upgrade-held; reconcile the original operation\n')
        sys.exit(2)
