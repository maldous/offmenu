"""Inactive, exact-target owner-local metadata reconciliation.

This module never opens an original, performs network I/O, writes custody, or
admits an asset. All reports are proposals. See docs/fetch-metadata-reader.md.
"""
from contextlib import contextmanager
from dataclasses import dataclass
import errno
import hashlib
import json
import math
import os
import re
import select
import signal
import stat
import threading
import time
from urllib.parse import urlsplit, unquote

PROPOSAL_SHA256 = '04581f74008cf471356787d26d239dcfe0f3e41774e2d2015c8d04ef30525168'
INVENTORY_PINS = {
    'closure_raw': ('b80fdb444a4b3107595fea022c439cda9cbd45a3bb47d790f7355f63e9d0842c', 31783525),
    'runtime_manifest_raw': ('7ffa2f5ce688c6fde5019b9252fbb9f96b3037f76337598cc05f76c37ef8754a', 6854787),
    'owner_config_raw': ('28acbde120ac7d457f24af8cd2e3203927bb770137b8ce414c0d7a082e63b4ba', 2994),
    'owner_selection_raw': ('81c0c919644d6df86681b4ef6ee946a25a191f85a0080a66e327c0b20d311a08', 72884),
    'dispatch_hold_raw': ('a78f209e2d1636cadf3ad913514d98472bf3e173b3c08c008ae573cade56ad8b', 13486),
}
SCHEMA = 'offmenu-fetch-metadata-report/1'
SELECTION_SCHEMA = 'offmenu-fetch-metadata-parent-selection/1'
CLEARANCE_SCHEMA = 'offmenu-fetch-metadata-current-clearance/1'
HANDOFF_ID = 'owner-local-comprehensive-20261018-002'
OWNER_ROOT = '/home/user/src/offmenu-data/owner-collection-runtime'
EXPECTED_UID = 1000
MAX_SECONDS = 180
MAX_OUTPUT = 4 * 1024 * 1024
MAX_DEPTH = 64
MAX_NODES = 500000
MAX_OBJECTS = 10000
MAX_READ = 16493475
MAX_SINGLE_READ = 14588360
TARGET_COUNT = 93
CANDIDATE_COUNT = 92
REPORT_RESERVE = 128 * 1024
ORIGINAL_ROOTS = ('/home/user/src/offmenu-data/originals/',
                  OWNER_ROOT + '/collection/private-originals/')
CODES = frozenset({'inactive', 'unselected', 'withheld', 'read-held', 'clearance-unavailable',
    'selection-mismatch', 'inventory-mismatch', 'owner-context-mismatch', 'lease-unverified',
    'main-thread-required', 'deadline', 'missing', 'inaccessible', 'not-regular', 'unsafe-path',
    'path-changed', 'extent-mismatch', 'digest-mismatch', 'invalid-json', 'duplicate-json-key',
    'depth-limit', 'node-limit', 'object-limit', 'output-limit', 'worker-failed',
    'reconciled', 'local-failure'})
_DIGEST = re.compile(r'[0-9a-f]{64}\Z')
_SEAL = object()
POINTER_KEYS = frozenset(('records', 'items', 'assets', 'sources', 'results', 'rows', 'files',
    'originals', 'metadata', 'reconciliation', 'entries', 'data', 'payload', 'evidence',
    'result', 'manifest', 'inventory', 'record', 'source', 'original', 'details',
    'downloads', 'retained', 'artifacts', 'snapshots', 'members', 'documents', 'outputs'))
QUERY_KEYS = frozenset(('id', 'key', 'api_key', 'token', 'signature', 'sig', 'expires',
    'download', 'format', 'lang', 'language', 'page', 'offset', 'limit', 'q', 'query',
    'search', 'filename', 'file', 'version', 'release', 'date', 'X-Amz-Algorithm',
    'X-Amz-Credential', 'X-Amz-Date', 'X-Amz-Expires', 'X-Amz-SignedHeaders',
    'X-Amz-Signature', 'X-Amz-Security-Token', 'access_token', 'auth', 'resourcekey'))
IDENTITY_KEYS = frozenset(('assetId', 'descriptorId', 'sourceKey', 'originalSHA256', 'originalBytes',
    'sha256', 'bytes', 'payloadSHA256', 'payloadBytes', 'originalPath', 'sourceUrl', 'finalUrl', 'url'))
CLASS_FIELDS = ('title', 'purpose', 'release', 'holds', 'sourceRole', 'outcome', 'rights')
CLASS_VALUES = {
    'sourceRole': frozenset(('publisher-reference-document-original', 'publisher-metadata-original',
         'reference-original', 'metadata', 'ancillary', 'unclassified-unit')),
    'outcome': frozenset(('retained', 'unverified', 'held', 'missing-contract', 'error')),
    'purpose': frozenset(('metadata-only', 'reference', 'research')),
    'release': frozenset(), 'title': frozenset(), 'holds': frozenset(), 'rights': frozenset(),
}
RESTRICTION_KEYS = frozenset(('holds', 'readHolds', 'effectiveReadHolds', 'sourceStageHolds',
    'sourceRestrictions', 'restrictions', 'permissions', 'sourcePermissions', 'privacy',
    'minors', 'minor', 'noRead', 'no_read', 'noRetry', 'no_retry', 'quarantine',
    'withheld', 'private', 'readAllowed', 'sourceReadAllowed', 'accessDenied'))
HOLD_WORDS = re.compile(r'no[ -_]?read|no[ -_]?retry|minor|private|privacy|denied|quarantin|withheld|restricted|prohibit|embargo', re.I)


class MetadataError(ValueError):
    """Closed error code only; raw exceptions are never returned."""


def _fail(code):
    raise MetadataError(code)


def _need(condition, code):
    if not condition:
        _fail(code)


def canonical(value):
    return (json.dumps(value, sort_keys=True, ensure_ascii=True, allow_nan=False,
                       separators=(',', ':')) + '\n').encode('ascii')


def _sha(raw):
    return hashlib.sha256(raw).hexdigest()


def _digest(value):
    return type(value) is str and _DIGEST.fullmatch(value) is not None


def _pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            _fail('duplicate-json-key')
        result[key] = value
    return result


def _strict(raw):
    try:
        return json.loads(raw.decode('utf-8'), object_pairs_hook=_pairs,
                          parse_constant=lambda _: _fail('invalid-json'))
    except MetadataError:
        raise
    except (ValueError, UnicodeError, RecursionError):
        _fail('invalid-json')


def _check(deadline):
    _need(time.monotonic() < deadline, 'deadline')


@dataclass(frozen=True)
class Target:
    target_id: str
    path: str
    sha256: str
    extent: int
    candidate: bool

    def binding(self):
        return {'targetId': self.target_id, 'path': self.path,
                'metadataSHA256': self.sha256, 'metadataBytes': self.extent}


@dataclass(frozen=True)
class Inventory:
    """Built only from five immutable reviewed byte strings, never file paths."""
    asset_ids: frozenset
    descriptor_ids: frozenset
    source_keys: frozenset
    countries: frozenset
    types: frozenset
    origins: frozenset
    identities: tuple
    held_asset_ids: frozenset
    held_descriptor_ids: frozenset
    config: bytes
    selection: bytes
    dispatch: bytes
    seal: object


def inspect_proposal(proposal_raw):
    """Validate reviewed inventory; this function never accesses target paths."""
    _need(type(proposal_raw) is bytes and len(proposal_raw) <= 1024 * 1024 and
          _sha(proposal_raw) == PROPOSAL_SHA256, 'selection-mismatch')
    proposal = _strict(proposal_raw)
    targets = []
    for row in proposal['targets']:
        candidate = row['candidateForBoundedOwnerMetadataReconciliation']
        _need(type(candidate) is bool and row['executionEnabled'] is False and
              _digest(row['expectedMetadataSHA256']), 'selection-mismatch')
        extent = row['observedMetadataBytes']
        _need(type(extent) is int and extent > 0, 'selection-mismatch')
        if candidate:
            _need(row['readMode'] == 'json' and row['proposedMaximumReadBytes'] == extent
                  and extent <= MAX_SINGLE_READ, 'selection-mismatch')
        else:
            _need(row['targetId'] == 'native-events' and row['readMode'] == 'jsonl-prefix'
                  and row['proposedMaximumReadBytes'] is None, 'selection-mismatch')
        _need(_safe_absolute(row['path']), 'selection-mismatch')
        targets.append(Target(row['targetId'], row['path'], row['expectedMetadataSHA256'], extent, candidate))
    _need(len(targets) == TARGET_COUNT and len({t.target_id for t in targets}) == TARGET_COUNT
          and len({t.path for t in targets}) == TARGET_COUNT
          and sum(t.candidate for t in targets) == CANDIDATE_COUNT
          and sum(t.extent for t in targets if t.candidate) == MAX_READ,
          'selection-mismatch')
    return tuple(targets)


def _origin(url):
    try:
        if type(url) is not str or len(url.encode('utf-8')) > 16384 or any(ord(c) < 33 for c in url):
            return None
        p = urlsplit(url)
        if p.scheme not in ('http', 'https') or p.username is not None or p.password is not None or not p.hostname:
            return None
        host = p.hostname.encode('idna').decode('ascii').lower()
        if not re.fullmatch(r'[a-z0-9.-]{1,253}', host):
            return None
        port = p.port
        return p.scheme + '://' + host + (':' + str(port) if port and port != (443 if p.scheme == 'https' else 80) else '')
    except (ValueError, UnicodeError):
        return None


def build_inventory(*, closure_raw, runtime_manifest_raw, owner_config_raw,
                    owner_selection_raw, dispatch_hold_raw):
    supplied = locals().copy()
    values = {}
    for key, (digest, extent) in INVENTORY_PINS.items():
        raw = supplied[key]
        _need(type(raw) is bytes and len(raw) == extent and _sha(raw) == digest, 'inventory-mismatch')
        values[key] = _strict(raw)
    closure, runtime = values['closure_raw'], values['runtime_manifest_raw']
    records = closure['records']
    assets = frozenset(r['assetId'] for r in records)
    _need(len(records) == len(assets) == 4753 and assets == frozenset(r['assetId'] for r in runtime['assets']), 'inventory-mismatch')
    descriptors = frozenset(d for r in records for d in r['descriptorIds'])
    identities, held, held_descriptors = {}, set(), set()
    for row in records:
        asset = row['assetId']
        identity = row['originalIdentity']
        pairs = []
        if isinstance(identity, dict) and _digest(identity.get('sha256')) and type(identity.get('bytes')) is int:
            pairs.append((identity['sha256'], identity['bytes']))
        match = re.fullmatch(r'snapshot-sha256:([0-9a-f]{64}):([0-9]+)', asset)
        if match:
            pairs.append((match[1], int(match[2])))
        for pair in pairs:
            identities.setdefault(pair, set()).add(asset)
        restrictions = row['sourceRestrictions']
        if row['fetchBlockedByCurrentHold'] or row['fetchSourceConditionHeld'] or restrictions.get('effectiveReadHolds'):
            held.add(asset)
            held_descriptors.update(row['descriptorIds'])
    config, selection, dispatch = (values[k] for k in ('owner_config_raw', 'owner_selection_raw', 'dispatch_hold_raw'))
    countries = frozenset(c for r in records for c in r['countryHints'])
    # Runtime types/countries are closed catalogues, sometimes objects rather than labels.
    types = frozenset(t if isinstance(t, str) else t.get('typeId', t.get('id', '')) for t in runtime['types'])
    origins = frozenset(o for r in records for u in r['sourceURLs'] if (o := _origin(u)))
    return Inventory(assets, descriptors, frozenset(config['sourceKeys']), countries, types, origins,
        tuple((digest, extent, tuple(sorted(ids))) for (digest, extent), ids in sorted(identities.items())),
        frozenset(held), frozenset(held_descriptors), canonical(config), canonical(selection), canonical(dispatch), _SEAL)


def _safe_absolute(path):
    return (type(path) is str and 1 <= len(path.encode('utf-8')) <= 4096
            and path.startswith('/') and not path.startswith('//')
            and all(part not in ('', '.', '..') for part in path.split('/')[1:])
            and not any(ord(c) < 32 or ord(c) == 127 for c in path) and '\\' not in path)


def _directory_identity(info):
    return (info.st_dev, info.st_ino, info.st_uid, info.st_mode)


def _file_identity(info):
    return _directory_identity(info) + (info.st_size, info.st_mtime_ns, info.st_ctime_ns)


def _open_chain(path, *, directory=False):
    """No-follow every component and retain full ancestor identity until close."""
    _need(_safe_absolute(path), 'unsafe-path')
    fds = []
    try:
        fd = os.open('/', os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC)
        fds.append(fd)
        snapshots = [_directory_identity(os.fstat(fd))]
        parts = path.split('/')[1:]
        for i, part in enumerate(parts):
            is_dir = directory or i < len(parts) - 1
            flags = os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC | os.O_NONBLOCK
            if is_dir:
                flags |= os.O_DIRECTORY
            fd = os.open(part, flags, dir_fd=fds[-1])
            fds.append(fd)
            info = os.fstat(fd)
            _need(stat.S_ISDIR(info.st_mode) if is_dir else stat.S_ISREG(info.st_mode), 'not-regular')
            snapshots.append(_directory_identity(info) if is_dir else _file_identity(info))
        return fds, tuple(snapshots)
    except BaseException:
        for fd in reversed(fds):
            os.close(fd)
        raise


def _close(fds):
    for fd in reversed(fds):
        os.close(fd)


def _verify_chain(path, old_fds, snapshots, *, directory=False):
    current, observed = _open_chain(path, directory=directory)
    try:
        actual = tuple((_directory_identity(os.fstat(fd)) if directory or i < len(old_fds) - 1
                        else _file_identity(os.fstat(fd))) for i, fd in enumerate(old_fds))
        _need(observed == snapshots == actual, 'path-changed')
    finally:
        _close(current)


def _private(info, directory=False):
    _need(info.st_uid == EXPECTED_UID and not info.st_mode & 0o077
          and (stat.S_ISDIR(info.st_mode) if directory else stat.S_ISREG(info.st_mode)), 'owner-context-mismatch')


def _verify_lease(fd, work_fd):
    try:
        _need(type(fd) is int and fd >= 0, 'lease-unverified')
        opened = os.fstat(fd)
        _private(opened)
        named = os.stat('fixed-selection.lock', dir_fd=work_fd, follow_symlinks=False)
        _need(_file_identity(opened) == _file_identity(named), 'lease-unverified')
        # /proc/self is a kernel-owned alias, not a target path. Final fdinfo is
        # opened no-follow and bounded; no lock is acquired or upgraded here.
        info_fd = os.open('/proc/self/fdinfo/' + str(fd), os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC)
        try:
            raw = os.read(info_fd, 16385)
        finally:
            os.close(info_fd)
        _need(len(raw) <= 16384, 'lease-unverified')
        matches = re.findall(rb'^lock:\s+\d+: FLOCK\s+ADVISORY\s+WRITE\s+(\d+)\s+([0-9a-f]+):([0-9a-f]+):(\d+)\s+0 EOF$', raw, re.M)
        expected = (os.getpid(), os.major(opened.st_dev), os.minor(opened.st_dev), opened.st_ino)
        _need(any((int(pid), int(major, 16), int(minor, 16), int(ino)) == expected
                  for pid, major, minor, ino in matches), 'lease-unverified')
    except (OSError, ValueError, TypeError):
        _fail('lease-unverified')


def _owner(owner_runtime, inventory, lease_fd):
    try:
        _need(type(inventory) is Inventory and inventory.seal is _SEAL, 'inventory-mismatch')
        config, dispatch = _strict(inventory.config), _strict(inventory.dispatch)
        expected = {'handoffId': HANDOFF_ID, 'runtimeConfigSHA256': INVENTORY_PINS['owner_config_raw'][0],
            'dispatchHoldSHA256': INVENTORY_PINS['dispatch_hold_raw'][0],
            'executionContext': 'owner-manual-foo', 'runnerResumeRequiresOutcomeImport': True}
        _need(os.getuid() == os.geteuid() == EXPECTED_UID == owner_runtime.uid and
              str(owner_runtime.root) == OWNER_ROOT and str(owner_runtime.native) == config['nativeClaimsRoot']
              and str(owner_runtime.runner_work) == '/srv/offmenu-refresh/outputs/collection'
              and str(owner_runtime.runner_cache) == '/srv/offmenu-refresh/cache'
              and canonical(owner_runtime.config) == inventory.config
              and canonical(owner_runtime.selected) == inventory.selection
              and owner_runtime.provenance() == expected
              and dispatch['handoffId'] == HANDOFF_ID
              and dispatch['overlapHold']['active'] is True
              and dispatch['overlapHold']['automaticRunnerSubmissionPermitted'] is False,
              'owner-context-mismatch')
        fds, snapshots = _open_chain(OWNER_ROOT + '/collection', directory=True)
        try:
            _private(os.fstat(fds[-2]), directory=True)
            _private(os.fstat(fds[-1]), directory=True)
            _verify_lease(lease_fd, fds[-1])
        except BaseException:
            _close(fds)
            raise
        return fds, snapshots
    except MetadataError:
        raise
    except Exception:
        _fail('owner-context-mismatch')


def _selection(selection, targets):
    _need(type(selection) is dict and set(selection) == {'schemaVersion', 'proposalSHA256',
        'readerSHA256', 'handoffId', 'ownerConfigSHA256', 'targets', 'withheldTargetIds',
        'clearanceEvidenceSHA256'}, 'selection-mismatch')
    _need(selection['schemaVersion'] == SELECTION_SCHEMA and selection['proposalSHA256'] == PROPOSAL_SHA256
          and selection['handoffId'] == HANDOFF_ID
          and selection['ownerConfigSHA256'] == INVENTORY_PINS['owner_config_raw'][0]
          and _digest(selection['clearanceEvidenceSHA256']), 'selection-mismatch')
    # The adopter pins exact reviewed source bytes; no activation boolean exists.
    fd = os.open(__file__, os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC)
    try:
        reader_raw = os.read(fd, 128 * 1024 + 1)
    finally:
        os.close(fd)
    _need(len(reader_raw) <= 128 * 1024 and selection['readerSHA256'] == _sha(reader_raw), 'selection-mismatch')
    rows, withheld = selection['targets'], selection['withheldTargetIds']
    _need(type(rows) is list and type(withheld) is list and len(rows) <= CANDIDATE_COUNT
          and all(type(x) is str for x in withheld) and len(set(withheld)) == len(withheld), 'selection-mismatch')
    by_id = {t.target_id: t for t in targets}
    selected_ids = []
    for row in rows:
        _need(type(row) is dict and type(row.get('targetId')) is str and row['targetId'] in by_id,
              'selection-mismatch')
        target = by_id[row['targetId']]
        _need(target.candidate and row == target.binding(), 'selection-mismatch')
        selected_ids.append(target.target_id)
    _need(len(set(selected_ids)) == len(selected_ids) and set(withheld) <= set(by_id)
          and not set(withheld) & set(selected_ids), 'selection-mismatch')
    return frozenset(selected_ids), frozenset(withheld)


def _clearance(callback, target, selection, deadline):
    _check(deadline)
    _need(callable(callback), 'clearance-unavailable')
    try:
        value = callback(target.binding())
        _need(type(value) is dict and set(value) == {'schemaVersion', 'target', 'evidenceSHA256',
            'checkedMonotonic', 'expiresMonotonic', 'decision'}, 'clearance-unavailable')
        _need(value['schemaVersion'] == CLEARANCE_SCHEMA and value['target'] == target.binding()
              and value['evidenceSHA256'] == selection['clearanceEvidenceSHA256']
              and type(value['checkedMonotonic']) in (int, float) and type(value['expiresMonotonic']) in (int, float)
              and math.isfinite(value['checkedMonotonic']) and math.isfinite(value['expiresMonotonic'])
              and value['checkedMonotonic'] <= time.monotonic() < value['expiresMonotonic']
              and time.monotonic() - value['checkedMonotonic'] <= 5
              and value['decision'] in ('clear', 'held', 'withheld', 'unknown'), 'clearance-unavailable')
        _check(deadline)
        _need(value['decision'] == 'clear', 'withheld' if value['decision'] == 'withheld' else 'read-held')
    except MetadataError:
        raise
    except Exception:
        _fail('clearance-unavailable')


@contextmanager
def _deadline_guard(deadline):
    _need(threading.current_thread() is threading.main_thread(), 'main-thread-required')
    old_handler = signal.getsignal(signal.SIGALRM)
    old_timer = signal.getitimer(signal.ITIMER_REAL)
    _need(old_timer == (0.0, 0.0), 'local-failure')
    def expired(signum, frame):
        _fail('deadline')
    signal.signal(signal.SIGALRM, expired)
    try:
        _check(deadline)
        signal.setitimer(signal.ITIMER_REAL, max(0.000001, deadline - time.monotonic()))
        yield
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
        signal.signal(signal.SIGALRM, old_handler)


def _read_target(target, deadline, progress):
    fds, before = _open_chain(target.path)
    try:
        _need(os.fstat(fds[-1]).st_size == target.extent, 'extent-mismatch')
        data = bytearray()
        while len(data) < target.extent:
            _check(deadline)
            block = os.read(fds[-1], min(65536, target.extent - len(data)))
            _need(bool(block), 'extent-mismatch')
            data.extend(block)
            progress[0] += len(block)
        _check(deadline)
        _verify_chain(target.path, fds, before)
        _need(_sha(data) == target.sha256, 'digest-mismatch')
        return bytes(data)
    finally:
        _close(fds)


def _lexical_bounds(raw, deadline, max_nodes=MAX_NODES, progress=None):
    # Count all scalar tokens and containers before json.loads allocates the
    # tree. Keys count too. Strings/escapes cannot fake structural depth.
    depth = nodes = 0
    quoted = escaped = scalar = False
    for index, byte in enumerate(raw):
        if index % 65536 == 0:
            _check(deadline)
        if quoted:
            if escaped:
                escaped = False
            elif byte == 92:
                escaped = True
            elif byte == 34:
                quoted = False
            continue
        if byte == 34:
            quoted = True
            _need(nodes < max_nodes, 'node-limit')
            nodes += 1
            if progress is not None:
                progress[0] = nodes
            scalar = False
        elif byte in (123, 91):
            depth += 1
            _need(nodes < max_nodes, 'node-limit')
            nodes += 1
            if progress is not None:
                progress[0] = nodes
            scalar = False
            _need(depth <= MAX_DEPTH, 'depth-limit')
        elif byte in (125, 93):
            depth -= 1
            scalar = False
        elif byte in (32, 9, 10, 13, 44, 58):
            scalar = False
        elif not scalar:
            _need(nodes < max_nodes, 'node-limit')
            nodes += 1
            if progress is not None:
                progress[0] = nodes
            scalar = True
        _need(nodes <= max_nodes, 'node-limit')
    return nodes


def _restricted(value, key=''):
    if isinstance(value, dict):
        for name, child in value.items():
            if name in ('read', 'copy', 'readAllowed', 'sourceReadAllowed') and child is False:
                return True
            if _restricted(child, name):
                return True
        return False
    if isinstance(value, list):
        return any(_restricted(child, key) for child in value)
    if value is True and key not in ('read', 'copy', 'readAllowed', 'sourceReadAllowed'):
        return True
    if isinstance(value, str):
        # Nonempty unrecognized restrictions remain held, never inferred clear.
        return bool(value) and value not in ('none', 'clear', 'public', 'allowed', 'unrestricted')
    return value not in (None, False, 0)


def _own_restricted(obj):
    if any(obj.get(key) is False for key in ('read', 'readAllowed', 'sourceReadAllowed')):
        return True
    return any(_restricted(value, key) for key, value in obj.items() if key in RESTRICTION_KEYS)


def _safe_pointer(pointer, inventory):
    if len(pointer.encode('utf-8')) > 2048:
        return False
    for part in pointer.split('/')[1:]:
        raw = part.replace('~1', '/').replace('~0', '~')
        if not (raw in POINTER_KEYS or raw in inventory.asset_ids or raw in inventory.descriptor_ids
                or re.fullmatch(r'[0-9]{1,8}', raw)):
            return False
    return True


def _url(value, inventory):
    origin = _origin(value)
    if origin not in inventory.origins:
        return None
    parsed = urlsplit(value)
    if parsed.fragment or len(parsed.path) > 2048 or len(parsed.query) > 8192:
        return None
    segments = parsed.path.split('/')[1:]
    if len(segments) > 32:
        return None
    keys = [unquote(part.partition('=')[0]) for part in parsed.query.split('&') if part]
    if len(keys) > 64:
        return None
    # No literal path component or arbitrary query-key text crosses the boundary.
    return {'origin': origin, 'pathShape': '/' + '/'.join('{segment}' if x else '' for x in segments),
        'queryKeys': sorted({k for k in keys if k in QUERY_KEYS}),
        'unknownQueryKeysWithheld': any(k not in QUERY_KEYS for k in keys),
        'exactURLSHA256': _sha(value.encode('utf-8')), 'requestIdentityStatus': 'unresolved'}


def _original_path(value):
    if not _safe_absolute(value) or len(value.encode('utf-8')) > 2048:
        return None
    if not any(value.startswith(root) for root in ORIGINAL_ROOTS):
        return None
    if not re.fullmatch(r'[A-Za-z0-9_./:+ ()-]+', value) or any(len(p) > 255 for p in value.split('/')):
        return None
    if re.search(r'secret|password|credential|cookie|token|signature|authorization|bearer', value, re.I):
        return None
    return value


def _object_row(obj, pointer, target, inventory, identity_map):
    ids = {}
    for key, allowed in (('assetId', inventory.asset_ids), ('descriptorId', inventory.descriptor_ids),
        ('sourceKey', inventory.source_keys), ('country', inventory.countries), ('type', inventory.types)):
        if type(obj.get(key)) is str and obj[key] in allowed:
            ids[key] = obj[key]
    if ids.get('assetId') in inventory.held_asset_ids or ids.get('descriptorId') in inventory.held_descriptor_ids:
        return None, True
    hashes = {obj[key] for key in ('originalSHA256', 'sha256', 'payloadSHA256') if _digest(obj.get(key))}
    extents = {obj[key] for key in ('originalBytes', 'bytes', 'payloadBytes')
               if type(obj.get(key)) is int and 0 < obj[key] <= 2**63 - 1}
    payload = None
    if len(hashes) == len(extents) == 1:
        digest, extent = next(iter(hashes)), next(iter(extents))
        linked = identity_map.get((digest, extent), ())
        if any(x in inventory.held_asset_ids for x in linked):
            return None, True
        payload = {'sha256': digest, 'bytes': extent, 'existingAssetIds': list(linked),
                   'basis': 'exact-recorded-digest-and-extent-only'}
    if not ids and payload is None:
        return None, False
    if not _safe_pointer(pointer, inventory):
        return None, False
    row = {'targetId': target.target_id, 'metadataSHA256': target.sha256,
        'sourceObjectJSONPointer': pointer, 'sourceObjectSHA256': _sha(canonical(obj)),
        'identifiers': ids, 'payloadIdentityProposal': payload, 'originalPath': None,
        'urls': {}, 'classifications': {}, 'rightsStatus': 'unresolved',
        'requestIdentityStatus': 'unresolved', 'custodyStatus': 'unresolved',
        'usableOriginal': False, 'countryTypeComplete': False}
    if payload:
        path = obj.get('originalPath')
        row['originalPath'] = _original_path(path) if type(path) is str else None
    for field in ('sourceUrl', 'finalUrl', 'url'):
        if field in obj and (clean := _url(obj[field], inventory)) is not None:
            row['urls'][field] = clean
    for key in CLASS_FIELDS:
        if key in obj:
            value = obj[key]
            classification = value if type(value) is str and value in CLASS_VALUES[key] else 'unresolved'
            row['classifications'][key] = {'classification': classification,
                'sourceObjectJSONPointer': pointer, 'sourceObjectSHA256': row['sourceObjectSHA256']}
    return row, False


def _sanitize(raw, target, inventory, deadline, max_output, max_objects, max_nodes=MAX_NODES, node_progress=None, budget_progress=None):
    nodes = _lexical_bounds(raw, deadline, max_nodes, node_progress)
    if node_progress is not None:
        node_progress[0] = nodes
    value = _strict(raw)
    _check(deadline)
    identity_map = {(digest, extent): ids for digest, extent, ids in inventory.identities}
    # Bottom-up restriction summary prevents candidate parents from uploading
    # rows containing nested held material, while independent siblings survive.
    restricted = {}
    stack = [(value, False)]
    while stack:
        obj, visited = stack.pop()
        if not isinstance(obj, (dict, list)):
            continue
        children = list(obj.values()) if isinstance(obj, dict) else obj
        if not visited:
            stack.append((obj, True))
            stack.extend((x, False) for x in reversed(children) if isinstance(x, (dict, list)))
        else:
            restricted[id(obj)] = ((isinstance(obj, dict) and _own_restricted(obj))
                or any(restricted.get(id(child), False) for child in children))
        if len(stack) % 1024 == 0:
            _check(deadline)
    rows, excluded, unresolved, output_bytes = [], 0, 0, 0
    stack = [(value, '', False, True)]
    while stack:
        obj, pointer, inherited, pointer_safe = stack.pop()
        _check(deadline)
        if isinstance(obj, dict):
            own_hold = _own_restricted(obj)
            row, asset_hold = _object_row(obj, pointer, target, inventory, identity_map)
            if not pointer_safe:
                row = None
            originally_unresolved = row is None and not asset_hold
            held = inherited or own_hold or asset_hold
            if row is not None and (held or restricted[id(obj)]):
                excluded += 1
                # A candidate record's descendants cannot shed its restrictions.
                held = True
                row = None
            elif asset_hold:
                excluded += 1
            if originally_unresolved and set(obj) & IDENTITY_KEYS:
                if held or restricted[id(obj)]:
                    excluded += 1
                else:
                    unresolved += 1
            if row is not None:
                _need(len(rows) < max_objects, 'object-limit')
                row_bytes = len(canonical(row))
                _need(output_bytes + row_bytes <= max_output, 'output-limit')
                output_bytes += row_bytes
                rows.append(row)
                if budget_progress is not None:
                    budget_progress[:] = [len(rows), output_bytes]
            for key, child in reversed(tuple(obj.items())):
                if isinstance(child, (dict, list)):
                    escaped = key.replace('~', '~0').replace('/', '~1')
                    safe = pointer_safe and (key in POINTER_KEYS or key in inventory.asset_ids
                                             or key in inventory.descriptor_ids)
                    stack.append((child, pointer + '/' + escaped, held, safe))
        elif isinstance(obj, list):
            stack.extend((child, pointer + '/' + str(index), inherited, pointer_safe)
                         for index, child in reversed(tuple(enumerate(obj))) if isinstance(child, (dict, list)))
    return {'rows': rows, 'visitedNodes': nodes, 'excludedObjects': excluded, 'unresolvedObjects': unresolved, 'sanitizedObjectsProduced': len(rows),
            'sanitizedRowBytesProduced': output_bytes}


def _error_code(error):
    if isinstance(error, MetadataError) and str(error) in CODES:
        return str(error)
    if isinstance(error, FileNotFoundError):
        return 'missing'
    if isinstance(error, PermissionError):
        return 'inaccessible'
    if isinstance(error, OSError) and error.errno in (errno.ELOOP, errno.ENOTDIR):
        return 'unsafe-path'
    return 'local-failure'


def _worker(target, inventory, deadline, max_output, max_objects, max_nodes):
    result = {'code': 'local-failure', 'bytesRead': None, 'rows': [], 'visitedNodes': 0, 'excludedObjects': 0, 'unresolvedObjects': 0,
              'sanitizedObjectsProduced': 0, 'sanitizedRowBytesProduced': 0}
    progress, node_progress, budget_progress = [0], [0], [0, 0]
    try:
        raw = _read_target(target, deadline, progress)
        result['bytesRead'] = len(raw)
        result.update(_sanitize(raw, target, inventory, deadline, max_output, max_objects, max_nodes, node_progress, budget_progress))
        result['code'] = 'reconciled'
    except BaseException as error:
        result['code'] = _error_code(error)
        result['bytesRead'] = progress[0]
        result['visitedNodes'] = node_progress[0]
        result['sanitizedObjectsProduced'], result['sanitizedRowBytesProduced'] = budget_progress
        result['rows'] = []
        if result['code'] == 'node-limit':
            result['visitedNodes'] = max_nodes
        # Before/failed read counters cannot be guessed. Conservative upper
        # bounds account for every potentially consumed byte after launch.
    return result


def _isolated(target, inventory, deadline, lease_fd, owner_fds, max_output, max_objects, max_nodes):
    """A blocked filesystem read cannot hold the caller past its deadline.

    Child emits only bounded sanitized JSON. Parent never performs blocking pipe
    reads/waits and kills only this exact child. In uninterruptible kernel I/O,
    termination remains explicitly unconfirmed; its lease was already closed.
    """
    read_fd, write_fd = os.pipe2(os.O_CLOEXEC | os.O_NONBLOCK)
    pid = None
    try:
        pid = os.fork()
        if pid == 0:
            try:
                os.close(read_fd)
                for fd in set(owner_fds) | {lease_fd}:
                    os.close(fd)
                signal.signal(signal.SIGALRM, signal.SIG_DFL)
                signal.setitimer(signal.ITIMER_REAL, max(0.000001, deadline - time.monotonic()))
                encoded = canonical(_worker(target, inventory, deadline, max_output, max_objects, max_nodes))
                if len(encoded) > MAX_OUTPUT:
                    os._exit(2)
                view = memoryview(encoded)
                while view:
                    _check(deadline)
                    try:
                        count = os.write(write_fd, view)
                        view = view[count:]
                    except BlockingIOError:
                        select.select([], [write_fd], [], max(0, deadline - time.monotonic()))
                os._exit(0)
            except BaseException:
                os._exit(2)
        os.close(write_fd)
        write_fd = None
        data = bytearray()
        while True:
            _check(deadline)
            ready, _, _ = select.select([read_fd], [], [], max(0, deadline - time.monotonic()))
            if not ready:
                _fail('deadline')
            block = os.read(read_fd, min(65536, MAX_OUTPUT + 1 - len(data)))
            if not block:
                break
            data.extend(block)
            _need(len(data) <= MAX_OUTPUT, 'output-limit')
        result = _strict(bytes(data))
        _need(type(result) is dict and set(result) == {'code', 'bytesRead', 'rows', 'visitedNodes', 'excludedObjects', 'unresolvedObjects',
              'sanitizedObjectsProduced', 'sanitizedRowBytesProduced'}
              and result['code'] in CODES, 'worker-failed')
        for key, maximum in (('visitedNodes', max_nodes), ('sanitizedObjectsProduced', max_objects),
                             ('sanitizedRowBytesProduced', max_output), ('bytesRead', target.extent),
                             ('excludedObjects', MAX_NODES), ('unresolvedObjects', MAX_NODES)):
            _need(type(result[key]) is int and 0 <= result[key] <= maximum, 'worker-failed')
        _need(type(result['rows']) is list and len(result['rows']) <= result['sanitizedObjectsProduced']
              and (result['code'] == 'reconciled' or not result['rows']), 'worker-failed')
        while True:
            done, _ = os.waitpid(pid, os.WNOHANG)
            if done:
                pid = None
                break
            _check(deadline)
            time.sleep(min(.001, max(0, deadline - time.monotonic())))
        return result
    finally:
        os.close(read_fd)
        if write_fd is not None:
            os.close(write_fd)
        if pid:
            try:
                done, _ = os.waitpid(pid, os.WNOHANG)
                if not done:
                    os.kill(pid, signal.SIGKILL)
                    # Never block on a task stuck in uninterruptible local I/O.
                    os.waitpid(pid, os.WNOHANG)
            except (ProcessLookupError, ChildProcessError):
                pass


def _base(targets):
    return {'schemaVersion': SCHEMA, 'proposalSHA256': PROPOSAL_SHA256, 'parentSelectionSHA256': None, 'status': 'inactive',
        'errorCode': None, 'targetDenominator': len(targets), 'candidateDenominator': sum(t.candidate for t in targets),
        'maximumMetadataReadBytes': MAX_READ, 'metadataBytesRead': 0,
        'uncertainReadBytesUpperBound': 0, 'recoveredObjectCount': 0, 'visitedNodes': 0,
        'sanitizedObjectsProduced': 0, 'sanitizedRowBytesProduced': 0,
        'outcomes': [{'targetId': t.target_id, 'metadataSHA256': t.sha256,
            'expectedMetadataBytes': t.extent, 'code': 'inactive' if t.candidate else 'unselected',
            'bytesRead': 0, 'readBytesUpperBound': 0, 'recoveredObjects': 0,
            'excludedObjects': 0, 'unresolvedObjects': 0, 'visitedNodes': 0,
            'sanitizedObjectsProduced': 0, 'sanitizedRowBytesProduced': 0} for t in targets], 'rows': [],
        'networkRequests': 0, 'originalsOpened': 0, 'sourceBodiesRead': False,
        'sourceBodiesUploaded': False, 'custodyModified': False, 'rightsGranted': False,
        'usableOriginalPromoted': False, 'countryTypeCompletionPromoted': False,
        'runnerResumeAuthorized': False, 'matchingCoverageExhaustive': False}


def reconcile_metadata(proposal_raw, *, parent_selection=None, inventory=None,
                       owner_runtime=None, lease_fd=None, current_read_holds=None,
                       absolute_deadline=0):
    """Return complete finite target accounting; default selection is inactive.

    current_read_holds(binding) must recompute source/privacy/minor/withheld
    restrictions and return the documented exact evidence-bound clearance. A
    metadata file never provides its own permission. No callback is optional
    after activation. Parent owner/lease/hold checks bracket every child.
    """
    targets = inspect_proposal(proposal_raw)
    report = _base(targets)
    if parent_selection is None:
        return report
    owner_fds = []
    try:
        report['parentSelectionSHA256'] = _sha(canonical(parent_selection))
        _need(type(absolute_deadline) in (int, float) and math.isfinite(absolute_deadline), 'deadline')
        deadline = min(absolute_deadline, time.monotonic() + MAX_SECONDS)
        with _deadline_guard(deadline):
            selected, withheld = _selection(parent_selection, targets)
            _need(type(inventory) is Inventory and inventory.seal is _SEAL, 'inventory-mismatch')
            owner_fds, owner_snapshot = _owner(owner_runtime, inventory, lease_fd)
            for index, target in enumerate(targets):
                outcome = report['outcomes'][index]
                if target.target_id in withheld:
                    outcome['code'] = 'withheld'
                    continue
                if target.target_id not in selected:
                    outcome['code'] = 'unselected'
                    continue
                try:
                    _check(deadline)
                    _verify_chain(OWNER_ROOT + '/collection', owner_fds, owner_snapshot, directory=True)
                    fresh, _ = _owner(owner_runtime, inventory, lease_fd)
                    _close(fresh)
                    _clearance(current_read_holds, target, parent_selection, deadline)
                    remaining_output = MAX_OUTPUT - REPORT_RESERVE - report['sanitizedRowBytesProduced']
                    _need(remaining_output > 0, 'output-limit')
                    outcome['bytesRead'] = None
                    outcome['readBytesUpperBound'] = target.extent
                    result = _isolated(target, inventory, deadline, lease_fd, owner_fds,
                        remaining_output, MAX_OBJECTS - report['sanitizedObjectsProduced'], MAX_NODES - report['visitedNodes'])
                    # Charge irrevocably consumed work before any callback, owner
                    # recheck or deadline check can suppress the target's rows.
                    outcome.update(code=result['code'], bytesRead=result['bytesRead'],
                        excludedObjects=result['excludedObjects'], unresolvedObjects=result['unresolvedObjects'],
                        visitedNodes=result['visitedNodes'],
                        sanitizedObjectsProduced=result['sanitizedObjectsProduced'],
                        sanitizedRowBytesProduced=result['sanitizedRowBytesProduced'])
                    for key, limit, code in (('visitedNodes', MAX_NODES, 'node-limit'),
                            ('sanitizedObjectsProduced', MAX_OBJECTS, 'object-limit'),
                            ('sanitizedRowBytesProduced', MAX_OUTPUT - REPORT_RESERVE, 'output-limit')):
                        _need(report[key] + result[key] <= limit, code)
                        report[key] += result[key]
                    if result['code'] in ('deadline', 'node-limit', 'object-limit', 'output-limit'):
                        _fail(result['code'])
                    _check(deadline)
                    _verify_chain(OWNER_ROOT + '/collection', owner_fds, owner_snapshot, directory=True)
                    fresh, _ = _owner(owner_runtime, inventory, lease_fd)
                    _close(fresh)
                    _clearance(current_read_holds, target, parent_selection, deadline)
                    if result['code'] == 'reconciled':
                        report['rows'].extend(result['rows'])
                        outcome['recoveredObjects'] = len(result['rows'])
                except BaseException as error:
                    code = _error_code(error)
                    outcome['code'] = code
                    outcome['recoveredObjects'] = 0
                    if code in ('deadline', 'owner-context-mismatch', 'lease-unverified', 'path-changed',
                                'output-limit', 'object-limit', 'node-limit'):
                        raise MetadataError(code) from None
            _verify_chain(OWNER_ROOT + '/collection', owner_fds, owner_snapshot, directory=True)
            fresh, _ = _owner(owner_runtime, inventory, lease_fd)
            _close(fresh)
            for target, outcome in zip(targets, report['outcomes']):
                if outcome['recoveredObjects']:
                    _clearance(current_read_holds, target, parent_selection, deadline)
            report['status'] = ('metadata-proposals-only' if all(o['code'] in ('reconciled', 'unselected', 'withheld')
                                for o in report['outcomes']) else 'incomplete')
    except BaseException as error:
        code = _error_code(error)
        report['errorCode'] = code
        report['status'] = 'blocked' if not any(o['readBytesUpperBound'] for o in report['outcomes']) else 'incomplete'
        for index, outcome in enumerate(report['outcomes']):
            if outcome['code'] == 'inactive':
                outcome['code'] = code
        # A final current-owner/hold failure cannot leave earlier rows available
        # for upload. Exact accounting survives, but no partial evidence escapes.
        report['rows'] = []
        for outcome in report['outcomes']:
            outcome['recoveredObjects'] = 0
    finally:
        _close(owner_fds)
    # Reconcile sums from atomically charged per-target records even if an
    # asynchronous deadline interrupted the short parent accounting sequence.
    for key in ('visitedNodes', 'sanitizedObjectsProduced', 'sanitizedRowBytesProduced'):
        report[key] = sum(outcome[key] for outcome in report['outcomes'])
    report['metadataBytesRead'] = sum(o['bytesRead'] or 0 for o in report['outcomes'])
    report['uncertainReadBytesUpperBound'] = sum(o['readBytesUpperBound'] for o in report['outcomes'] if o['bytesRead'] is None)
    report['recoveredObjectCount'] = len(report['rows'])
    if len(canonical(report)) > MAX_OUTPUT:
        report['rows'] = []
        report.update(status='incomplete', errorCode='output-limit', recoveredObjectCount=0)
        for outcome in report['outcomes']:
            outcome['recoveredObjects'] = 0
    return sanitize_report(report, proposal_raw, inventory=inventory, parent_selection=parent_selection)


def sanitize_report(report, proposal_raw, *, inventory=None, parent_selection=None):
    """Reject non-closed or inconsistent publication metadata; never repair it.

    This validates report shape and pinned identities, not permission to fetch.
    A serialized report is not a live owner/lease or absent-custody capability.
    """
    def need(condition):
        if not condition:
            raise ValueError('invalid-metadata-report')
    try:
        targets = inspect_proposal(proposal_raw)
        template = _base(targets)
        need(type(report) is dict and set(report) == set(template))
        need(len(canonical(report)) <= MAX_OUTPUT and report['schemaVersion'] == SCHEMA
             and report['proposalSHA256'] == PROPOSAL_SHA256
             and report['parentSelectionSHA256'] == (None if parent_selection is None else _sha(canonical(parent_selection))))
        need(report['status'] in ('inactive', 'blocked', 'incomplete', 'metadata-proposals-only')
             and report['errorCode'] in (CODES | {None}))
        for key in ('targetDenominator', 'candidateDenominator', 'maximumMetadataReadBytes'):
            need(type(report[key]) is int and report[key] == template[key])
        for key in ('networkRequests', 'originalsOpened'):
            need(type(report[key]) is int and report[key] == 0)
        for key in ('sourceBodiesRead', 'sourceBodiesUploaded', 'custodyModified', 'rightsGranted',
                    'usableOriginalPromoted', 'countryTypeCompletionPromoted', 'runnerResumeAuthorized', 'matchingCoverageExhaustive'):
            need(report[key] is False)
        for key, maximum in (('metadataBytesRead', MAX_READ), ('uncertainReadBytesUpperBound', MAX_READ),
                            ('recoveredObjectCount', MAX_OBJECTS), ('visitedNodes', MAX_NODES),
                            ('sanitizedObjectsProduced', MAX_OBJECTS),
                            ('sanitizedRowBytesProduced', MAX_OUTPUT - REPORT_RESERVE)):
            need(type(report[key]) is int and 0 <= report[key] <= maximum)
        outcomes, rows = report['outcomes'], report['rows']
        need(type(outcomes) is list and len(outcomes) == len(targets)
             and type(rows) is list and len(rows) == report['recoveredObjectCount'])
        by_id = {target.target_id: (target, outcome) for target, outcome in zip(targets, outcomes)}
        for target, outcome, expected in zip(targets, outcomes, template['outcomes']):
            need(type(outcome) is dict and set(outcome) == set(expected))
            for key in ('targetId', 'metadataSHA256', 'expectedMetadataBytes'):
                need(type(outcome[key]) is type(expected[key]) and outcome[key] == expected[key])
            need(outcome['code'] in CODES and (target.candidate or outcome['code'] in ('unselected', 'withheld')))
            count = outcome['bytesRead']
            bound = outcome['readBytesUpperBound']
            need(type(bound) is int and bound in (0, target.extent if target.candidate else 0))
            need(count is None or type(count) is int and 0 <= count <= bound)
            need(count is not None or bound > 0)
            for key in ('recoveredObjects', 'excludedObjects', 'unresolvedObjects'):
                need(type(outcome[key]) is int and 0 <= outcome[key] <= MAX_NODES)
            for key, maximum in (('visitedNodes', MAX_NODES), ('sanitizedObjectsProduced', MAX_OBJECTS),
                                 ('sanitizedRowBytesProduced', MAX_OUTPUT - REPORT_RESERVE)):
                need(type(outcome[key]) is int and 0 <= outcome[key] <= maximum)
            need(outcome['sanitizedObjectsProduced'] >= outcome['recoveredObjects'])
            if outcome['code'] == 'reconciled':
                need(count == bound == target.extent)
            else:
                need(outcome['recoveredObjects'] == 0)
            if outcome['code'] in ('inactive', 'unselected'):
                need(count == bound == 0)
        for key in ('visitedNodes', 'sanitizedObjectsProduced', 'sanitizedRowBytesProduced'):
            need(report[key] == sum(o[key] for o in outcomes))
        need(report['metadataBytesRead'] == sum(o['bytesRead'] or 0 for o in outcomes))
        need(report['uncertainReadBytesUpperBound'] == sum(o['readBytesUpperBound'] for o in outcomes if o['bytesRead'] is None))
        need(report['metadataBytesRead'] + report['uncertainReadBytesUpperBound'] <= MAX_READ)
        if rows:
            need(type(inventory) is Inventory and inventory.seal is _SEAL)
        identities = {(h, n): ids for h, n, ids in inventory.identities} if inventory else {}
        row_keys = {'targetId', 'metadataSHA256', 'sourceObjectJSONPointer', 'sourceObjectSHA256',
            'identifiers', 'payloadIdentityProposal', 'originalPath', 'urls', 'classifications',
            'rightsStatus', 'requestIdentityStatus', 'custodyStatus', 'usableOriginal', 'countryTypeComplete'}
        counts, pointers = {}, set()
        for row in rows:
            need(type(row) is dict and set(row) == row_keys and row['targetId'] in by_id)
            target, outcome = by_id[row['targetId']]
            need(outcome['code'] == 'reconciled' and row['metadataSHA256'] == target.sha256
                 and _digest(row['sourceObjectSHA256']) and type(row['sourceObjectJSONPointer']) is str
                 and _safe_pointer(row['sourceObjectJSONPointer'], inventory))
            pointer_key = (row['targetId'], row['sourceObjectJSONPointer'])
            need(pointer_key not in pointers)
            pointers.add(pointer_key)
            counts[row['targetId']] = counts.get(row['targetId'], 0) + 1
            ids = row['identifiers']
            catalogues = {'assetId': inventory.asset_ids, 'descriptorId': inventory.descriptor_ids,
                'sourceKey': inventory.source_keys, 'country': inventory.countries, 'type': inventory.types}
            need(type(ids) is dict and set(ids) <= set(catalogues)
                 and all(type(v) is str and v in catalogues[k] for k, v in ids.items())
                 and ids.get('assetId') not in inventory.held_asset_ids
                 and ids.get('descriptorId') not in inventory.held_descriptor_ids)
            payload = row['payloadIdentityProposal']
            if payload is not None:
                need(type(payload) is dict and set(payload) == {'sha256', 'bytes', 'existingAssetIds', 'basis'}
                     and _digest(payload['sha256']) and type(payload['bytes']) is int and 0 < payload['bytes'] <= 2**63-1
                     and payload['basis'] == 'exact-recorded-digest-and-extent-only'
                     and payload['existingAssetIds'] == list(identities.get((payload['sha256'], payload['bytes']), ()))
                     and not set(payload['existingAssetIds']) & inventory.held_asset_ids)
            need(bool(ids) or payload is not None)
            need(row['originalPath'] is None or payload is not None and type(row['originalPath']) is str
                 and _original_path(row['originalPath']) == row['originalPath'])
            for key in ('rightsStatus', 'requestIdentityStatus', 'custodyStatus'):
                need(row[key] == 'unresolved')
            need(row['usableOriginal'] is False and row['countryTypeComplete'] is False)
            urls = row['urls']
            need(type(urls) is dict and set(urls) <= {'sourceUrl', 'finalUrl', 'url'})
            for url in urls.values():
                need(type(url) is dict and set(url) == {'origin', 'pathShape', 'queryKeys',
                    'unknownQueryKeysWithheld', 'exactURLSHA256', 'requestIdentityStatus'})
                need(url['origin'] in inventory.origins and _origin(url['origin']) == url['origin']
                     and type(url['pathShape']) is str and len(url['pathShape']) <= 512
                     and re.fullmatch(r'/(?:\{segment\})?(?:/(?:\{segment\})?){0,31}', url['pathShape']) is not None
                     and type(url['queryKeys']) is list and all(type(k) is str and k in QUERY_KEYS for k in url['queryKeys'])
                     and url['queryKeys'] == sorted(set(url['queryKeys']))
                     and type(url['unknownQueryKeysWithheld']) is bool and _digest(url['exactURLSHA256'])
                     and url['requestIdentityStatus'] == 'unresolved')
            classifications = row['classifications']
            need(type(classifications) is dict and set(classifications) <= set(CLASS_FIELDS))
            for key, classification in classifications.items():
                need(type(classification) is dict and set(classification) == {'classification',
                    'sourceObjectJSONPointer', 'sourceObjectSHA256'}
                     and classification['classification'] in CLASS_VALUES[key] | {'unresolved'}
                     and classification['sourceObjectJSONPointer'] == row['sourceObjectJSONPointer']
                     and classification['sourceObjectSHA256'] == row['sourceObjectSHA256'])
        need(all(o['recoveredObjects'] == counts.get(o['targetId'], 0) for o in outcomes))
        if report['status'] == 'inactive':
            need(parent_selection is None and report == template)
        else:
            need(parent_selection is not None)
        if report['status'] == 'metadata-proposals-only':
            selected_ids, withheld_ids = _selection(parent_selection, targets)
            need(all(o['targetId'] in selected_ids for o in outcomes if o['code'] == 'reconciled'))
            need(all(o['targetId'] not in selected_ids | withheld_ids for o in outcomes if o['code'] == 'unselected'))
            need(report['errorCode'] is None and all(o['code'] in ('reconciled', 'unselected', 'withheld') for o in outcomes))
        if report['errorCode'] is not None:
            need(not rows)
        return report
    except (KeyError, TypeError, UnicodeError, OverflowError, MetadataError):
        raise ValueError('invalid-metadata-report') from None


validate_report = sanitize_report
