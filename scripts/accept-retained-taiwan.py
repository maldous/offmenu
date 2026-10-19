#!/usr/bin/env python3
"""Inactive owner-only, append-only acceptance of three exact retained references.

No CLI or collector hookup. Explicit reviewed selection, existing writer lease,
current owner admission, and fresh exact validation are mandatory. Original and
failed acquisition records are never opened for writing. No network operations.
"""
from contextlib import ExitStack
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
import math
import os
from pathlib import Path
import re
import stat
import threading
import time

ROOT = Path(__file__).resolve().parents[1]
IMPORTED_WRITER_SHA256 = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
DEPENDENCY_PINS = {
    'scripts/propose-retained-taiwan-acceptance.py': 'b9db242becccdd5c413bc7367e5e95c928e46aacb309e0b6a41a46915b33b909',
    'scripts/validate-retained-taiwan.py': '36398946beb3e5215f2d8928091283375d706e99980b69ba48e56174320c7b7f',
    'scripts/diagnose-retained-taiwan.py': 'a6f438929bbfa3a16d3678a4c0196fa234f5cc8ef3bb0b4e07db2552341da957',
}
# Pin imported source before executing dependencies, including the diagnostic
# imported internally by the exact validator. The launcher still pins the full
# owner adapter and package closure before any owner execution.
for _path, _digest in DEPENDENCY_PINS.items():
    if hashlib.sha256((ROOT / _path).read_bytes()).hexdigest() != _digest:
        raise ValueError('acceptance-dependency-mismatch')


def _module(name, path):
    spec = importlib.util.spec_from_file_location(name, ROOT / path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


p = _module('taiwan_acceptance_proposal', 'scripts/propose-retained-taiwan-acceptance.py')
r = _module('taiwan_acceptance_validator', 'scripts/validate-retained-taiwan.py')
MANIFEST_SHA256 = '676293ceb7d7f7169ed103f7dd494c8da58f50148572ce1f941850ba476aee5e'
MANIFEST_PATH = 'docs/collection-selections/retained-taiwan-acceptance-proposal.json'
SCHEMA = 'offmenu-retained-taiwan-acceptance-receipt/1'
COMMIT_SCHEMA = 'offmenu-retained-taiwan-acceptance-commit/1'
SELECTION_SCHEMA = 'offmenu-retained-taiwan-parent-selection/1'
MAX_SECONDS = 210
MAX_RECEIPT_BYTES = 64 * 1024
MAX_GATE_BYTES = 1024 * 1024
_SEAL = object()
ERRORS = {'acceptance-inactive', 'acceptance-selection-mismatch',
    'acceptance-owner-context-mismatch', 'acceptance-main-thread-required',
    'acceptance-lease-unverified', 'acceptance-current-conflict',
    'acceptance-admission-unavailable', 'acceptance-fresh-validation-failed',
    'acceptance-custody-changed', 'acceptance-receipt-absent',
    'acceptance-state-conflict', 'acceptance-write-uncertain',
    'acceptance-deadline-exceeded', 'acceptance-capacity-held',
    'acceptance-interrupted', 'acceptance-local-failure'}


class AcceptanceError(ValueError):
    pass


def _require(condition, error):
    if not condition:
        raise AcceptanceError(error)


def _check(deadline, check_signal):
    check_signal()
    _require(time.monotonic() < deadline, 'acceptance-deadline-exceeded')


def _repo_bytes(path, maximum=8 * 1024 * 1024):
    # Only reviewed repository-relative metadata and this source module.
    _require(not Path(path).is_absolute() and '..' not in Path(path).parts,
             'acceptance-owner-context-mismatch')
    with (ROOT / path).open('rb') as stream:
        raw = stream.read(maximum + 1)
    _require(len(raw) <= maximum, 'acceptance-owner-context-mismatch')
    return raw


def _selection(manifest_raw, selection):
    # Run before all owner/custody access. No default selection or apply flag.
    _require(selection is not None, 'acceptance-inactive')
    _require(type(manifest_raw) is bytes and len(manifest_raw) <= 128 * 1024 and
             p.sha(manifest_raw) == MANIFEST_SHA256,
             'acceptance-selection-mismatch')
    manifest = p.strict_json(manifest_raw)
    context = manifest['existingOwnerContextBinding']
    _require(p.sha(_repo_bytes('scripts/accept-retained-taiwan.py')) == IMPORTED_WRITER_SHA256,
             'acceptance-selection-mismatch')
    expected = {'schemaVersion': SELECTION_SCHEMA,
        'acceptanceManifestSHA256': MANIFEST_SHA256,
        'reviewedWriterSHA256': IMPORTED_WRITER_SHA256,
        'handoffId': context['handoffId'],
        'scope': 'exact-three-unchanged-retained-reference-acceptance',
        'preparationSelected': False}
    _require(type(selection) is dict and set(selection) == set(expected) and
             all(type(selection[key]) is type(value) and selection[key] == value
                 for key, value in expected.items()), 'acceptance-selection-mismatch')
    _require(len(manifest['items']) == 3, 'acceptance-selection-mismatch')
    return manifest


def _dir_identity(info):
    # Parent directory mtimes/link counts can change when this writer adds its
    # own receipt directories. Device/inode/owner/mode cannot change.
    return info.st_dev, info.st_ino, info.st_uid, info.st_mode


def _private_fd(fd, directory=False):
    r.d.owned(fd, directory)
    return os.fstat(fd)


def _verify_lease(fd, work_fd):
    """Verify the passed open description already owns an exclusive Linux flock.

    Never acquire/upgrade/unlock a lease here. fdinfo ties the FLOCK to the
    passed descriptor; a different descriptor locked by this PID is insufficient.
    """
    try:
        _require(type(fd) is int, 'acceptance-lease-unverified')
        opened = _private_fd(fd)
        named = os.stat('fixed-selection.lock', dir_fd=work_fd, follow_symlinks=False)
        _require(r.d.identity(opened) == r.d.identity(named), 'acceptance-lease-unverified')
        with open('/proc/self/fdinfo/' + str(fd), 'rb') as stream:
            raw = stream.read(16385)
        _require(len(raw) <= 16384, 'acceptance-lease-unverified')
        locks = re.findall(rb'^lock:\s+\d+: FLOCK\s+ADVISORY\s+WRITE\s+(\d+)\s+([0-9a-f]+):([0-9a-f]+):(\d+)\s+0 EOF$', raw, re.M)
        expected = (os.getpid(), os.major(opened.st_dev), os.minor(opened.st_dev), opened.st_ino)
        _require(any((int(pid), int(major, 16), int(minor, 16), int(ino)) == expected
                     for pid, major, minor, ino in locks), 'acceptance-lease-unverified')
    except (OSError, ValueError, TypeError):
        raise AcceptanceError('acceptance-lease-unverified') from None



def _check_runtime_paths(owner_runtime, config):
    _require(Path(owner_runtime.native) == Path(config['nativeClaimsRoot']) and
             Path(owner_runtime.runner_work) == Path('/srv/offmenu-refresh/outputs/collection') and
             Path(owner_runtime.runner_cache) == Path('/srv/offmenu-refresh/cache'),
             'acceptance-owner-context-mismatch')


def _context(manifest, owner_runtime):
    try:
        _require(p.sha(_repo_bytes('scripts/accept-retained-taiwan.py')) == IMPORTED_WRITER_SHA256,
                 'acceptance-owner-context-mismatch')
        for path, digest in DEPENDENCY_PINS.items():
            _require(p.sha(_repo_bytes(path)) == digest, 'acceptance-owner-context-mismatch')
        context = manifest['existingOwnerContextBinding']
        selection = p.pinned(_repo_bytes(manifest['sourceBaseline']['selectionPath']), p.SELECTION_SHA256)
        assets = p.pinned(_repo_bytes(manifest['sourceBaseline']['assetManifestPath']), p.ASSET_MANIFEST_SHA256)
        config = p.pinned(_repo_bytes(context['runtimeConfigPath']), context['runtimeConfigSHA256'])
        hold = p.pinned(_repo_bytes(context['dispatchHoldPath']), context['dispatchHoldSHA256'])
        _check_runtime_paths(owner_runtime, config)
        expected_provenance = {'handoffId': context['handoffId'],
            'runtimeConfigSHA256': context['runtimeConfigSHA256'],
            'dispatchHoldSHA256': context['dispatchHoldSHA256'],
            'executionContext': 'owner-manual-foo', 'runnerResumeRequiresOutcomeImport': True}
        expected_root = Path(manifest['items'][0]['proposedCustodyReference']['runtimeRoot'])
        _require(os.getuid() == os.geteuid() == r.d.EXPECTED_UID == owner_runtime.uid,
                 'acceptance-owner-context-mismatch')
        _require(Path(owner_runtime.root) == expected_root == r.d.OUTPUT_ROOT and
                 owner_runtime.provenance() == expected_provenance and
                 p.canonical(owner_runtime.config) == p.canonical(config) and
                 p.canonical(owner_runtime.selected) == p.canonical(selection),
                 'acceptance-owner-context-mismatch')
        _require(hold['handoffId'] == context['handoffId'] and
                 hold['overlapHold']['active'] is True and
                 hold['overlapHold']['automaticRunnerSubmissionPermitted'] is False,
                 'acceptance-owner-context-mismatch')
        for row in manifest['items']:
            source = row['sourceContract']
            current = next(s for s in selection['sources'] if s['sourceKey'] == row['sourceKey'])
            asset = assets['assets'][row['assetIndex']]
            prep = next(s for s in selection['preparation'] if s['sourceKey'] == row['sourceKey'])
            _require(current == source and not source['sourceAcquisitionHeld'] and
                     source['privateCustodyApproved'] is True and
                     asset['assetId'] == row['assetId'] and asset['disposition'] == 'eligible' and
                     not asset.get('holds') and not asset.get('sourceStageHolds') and
                     prep == row['existingPreparationSelection'] and not prep['holds'],
                     'acceptance-current-conflict')
        return expected_root
    except AcceptanceError:
        raise
    except Exception:
        raise AcceptanceError('acceptance-owner-context-mismatch') from None


def _admit(manifest, owner_runtime, current_adverse_evidence, deadline, check_signal):
    """Recompute caller's bounded current metadata gate, then existing live scans."""
    _check(deadline, check_signal)
    _context(manifest, owner_runtime)
    try:
        _require(callable(current_adverse_evidence), 'acceptance-admission-unavailable')
        evidence = current_adverse_evidence()
        _require(type(evidence) in (list, tuple) and len(p.canonical(evidence)) <= MAX_GATE_BYTES,
                 'acceptance-admission-unavailable')
        # The existing owner's acquisition adapter supplies its exact matcher
        # and live native/local/historical metadata admission, without a GET.
        admit_function = owner_runtime.admit
        adapter = admit_function.__func__.__globals__.get('a')
        _require(adapter is not None, 'acceptance-admission-unavailable')
        work = Path(owner_runtime.root) / 'collection'
        for row in manifest['items']:
            _check(deadline, check_signal)
            source = row['sourceContract']
            _require(not any(adapter.exact_source_match(e, source) for e in evidence),
                     'acceptance-current-conflict')
            intent = work / 'private-originals' / row['sourceContractSHA256'] / 'successor-intent.json'
            old_claim = work / 'intents' / (p.sha(source['url'].encode()) + '.json')
            coverage = admit_function(work, source, intent, old_claim, None, deadline)
            _require(isinstance(coverage, dict) and coverage.get('nativeCoverageExhaustive') is False,
                     'acceptance-admission-unavailable')
    except AcceptanceError:
        raise
    except Exception:
        raise AcceptanceError('acceptance-admission-unavailable') from None


class _Snapshot:
    def __init__(self, stack, manifest, output_root):
        self.stack, self.manifest = stack, manifest
        self.root = r.d.open_root(stack, output_root)
        self.root_identity = _dir_identity(_private_fd(self.root, True))
        self.work = r.d.open_child(stack, self.root, 'collection', True)
        self.directories = [(self.work, self.root, 'collection',
                             _dir_identity(_private_fd(self.work, True)))]
        self.files = []
        self.bodies = {}
        originals = r.d.open_child(stack, self.work, 'private-originals', True)
        originals_before = r.d.owned(originals, True)
        self.files.append((originals, self.work, 'private-originals', originals_before))
        for row in manifest['items']:
            ref = row['proposedCustodyReference']
            _, _, detail = r.d.read_metadata(stack, self.work,
                Path(ref['oldFailedDetail']['relativePath']).name, ref['oldFailedDetail']['sha256'])
            self.files.append(detail)
            folder = r.d.open_child(stack, originals, row['sourceContractSHA256'], True)
            before = r.d.owned(folder, True)
            self.files.append((folder, originals, row['sourceContractSHA256'], before))
            _, _, intent = r.d.read_metadata(stack, folder, 'successor-intent.json',
                                            ref['oldFailedIntent']['sha256'])
            self.files.append(intent)
            body = r.d.open_child(stack, folder, 'original.partial')
            before = r.d.owned(body)
            _require(before[2] == ref['bytes'], 'acceptance-custody-changed')
            self.files.append((body, folder, 'original.partial', before))
            self.bodies[row['sourceKey']] = body

    def directory(self, parent, name, create):
        if create:
            try:
                os.mkdir(name, 0o700, dir_fd=parent)
                os.fsync(parent)
            except FileExistsError:
                pass
        fd = r.d.open_child(self.stack, parent, name, True)
        identity = _dir_identity(_private_fd(fd, True))
        self.directories.append((fd, parent, name, identity))
        return fd

    def verify(self):
        try:
            for check in self.files:
                r.d.unchanged(*check)
            for fd, parent, name, before in self.directories:
                _require(_dir_identity(_private_fd(fd, True)) == before ==
                         _dir_identity(os.stat(name, dir_fd=parent, follow_symlinks=False)),
                         'acceptance-custody-changed')
            root = r.d.open_root(self.stack, r.d.OUTPUT_ROOT)
            _require(_dir_identity(_private_fd(root, True)) == self.root_identity,
                     'acceptance-custody-changed')
        except (OSError, ValueError):
            raise AcceptanceError('acceptance-custody-changed') from None


def _names(fd):
    names = []
    with os.scandir(fd) as entries:
        for entry in entries:
            names.append(entry.name)
            _require(len(names) <= 3 and not entry.is_symlink(), 'acceptance-state-conflict')
    return set(names)


def _receipt_folder(snapshot, create):
    try:
        parent = snapshot.directory(snapshot.work, 'retained-taiwan-acceptance', create)
        names = _names(parent)
        _require(names <= {MANIFEST_SHA256}, 'acceptance-state-conflict')
        return snapshot.directory(parent, MANIFEST_SHA256, create)
    except FileNotFoundError:
        if not create:
            return None
        raise


def _fresh(manifest, output_root, deadline, check_signal, snapshot, lease_fd):
    reports = []
    for row in manifest['items']:
        _check(deadline, check_signal)
        _verify_lease(lease_fd, snapshot.work)
        result = r.validate_selected(row['sourceContract'], output_root, deadline)
        _require(p.canonical(result) == p.canonical(row['validationProposal']) and
                 result['status'] == 'validated-proposal' and result['dispositionApplied'] is False,
                 'acceptance-fresh-validation-failed')
        reports.append(result)
    snapshot.verify()
    return reports


def _receipt(manifest, selection, reports, accepted_at):
    return {'schemaVersion': SCHEMA, 'status': 'accepted-retained-references',
        'acceptanceManifestSHA256': MANIFEST_SHA256,
        'parentSelectionSHA256': p.sha(p.canonical(selection)),
        'existingOwnerContextBinding': manifest['existingOwnerContextBinding'],
        'publishedEvidence': manifest['publishedEvidence'],
        'acceptedAtUTC': accepted_at, 'originalAcquiredAt': None,
        'scope': 'private-unchanged-original-structural-validation-only',
        'items': [{'sourceKey': row['sourceKey'], 'assetId': row['assetId'],
                   'sourceContractSHA256': row['sourceContractSHA256'],
                   'reference': row['proposedCustodyReference'],
                   'freshValidationSHA256': p.sha(p.canonical(fresh)),
                   'freshValidation': fresh,
                   'downstreamHolds': row['preservedDownstreamHolds']}
                  for row, fresh in zip(manifest['items'], reports)],
        'dispositionApplied': True, 'networkRequests': 0,
        'sourceBodiesModified': False, 'oldFailedRecordsModified': False,
        'preparationPerformed': False, 'semanticOrGoldAdmission': False,
        'runnerResumeAuthorized': False}


def _commit(receipt_raw, selection):
    return {'schemaVersion': COMMIT_SCHEMA, 'acceptanceManifestSHA256': MANIFEST_SHA256,
            'parentSelectionSHA256': p.sha(p.canonical(selection)),
            'receiptSHA256': p.sha(receipt_raw), 'receiptBytes': len(receipt_raw)}


def _read_exact(snapshot, folder, name, expected_sha):
    value, digest, check = r.d.read_metadata(snapshot.stack, folder, name, expected_sha)
    raw = p.canonical(value)
    _require(p.sha(raw) == digest, 'acceptance-state-conflict')
    snapshot.files.append(check)
    return value, raw


def _existing(snapshot, folder, manifest, selection, reports):
    if folder is None:
        return None
    names = _names(folder)
    if not names:
        return None
    matches = [re.fullmatch(r'receipt-([a-f0-9]{64})\.json', name) for name in names]
    receipts = [match for match in matches if match is not None]
    _require(len(receipts) == 1, 'acceptance-state-conflict')
    digest = receipts[0].group(1)
    receipt_name, commit_name = 'receipt-' + digest + '.json', 'committed-' + digest + '.json'
    _require(names == {receipt_name, commit_name}, 'acceptance-write-uncertain')
    value, raw = _read_exact(snapshot, folder, receipt_name, digest)
    try:
        date = datetime.fromisoformat(value['acceptedAtUTC'])
        _require(date.tzinfo == timezone.utc and date <= datetime.now(timezone.utc), 'acceptance-state-conflict')
        expected = _receipt(manifest, selection, reports, value['acceptedAtUTC'])
        _require(raw == p.canonical(expected), 'acceptance-state-conflict')
        committed, committed_raw = _read_exact(snapshot, folder, commit_name, None)
        _require(committed_raw == p.canonical(_commit(raw, selection)), 'acceptance-state-conflict')
    except (KeyError, TypeError, ValueError):
        raise AcceptanceError('acceptance-state-conflict') from None
    return value, raw


def _write_exclusive(snapshot, folder, name, raw, deadline, check_signal, guard_bytes):
    _check(deadline, check_signal)
    _require(len(raw) <= MAX_RECEIPT_BYTES, 'acceptance-state-conflict')
    space = os.fstatvfs(folder)
    _require(space.f_bavail * space.f_frsize >= guard_bytes + 2 * MAX_RECEIPT_BYTES,
             'acceptance-capacity-held')
    fd = os.open(name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW | os.O_CLOEXEC,
                 0o600, dir_fd=folder)
    snapshot.stack.callback(os.close, fd)
    _private_fd(fd)
    offset = 0
    while offset < len(raw):
        _check(deadline, check_signal)
        written = os.write(fd, raw[offset:])
        _require(written > 0, 'acceptance-write-uncertain')
        offset += written
    os.fsync(fd)
    os.fsync(folder)
    # Once created, files are never removed/overwritten, including failed writes.
    _, observed = _read_exact(snapshot, folder, name, p.sha(raw))
    _require(observed == raw, 'acceptance-write-uncertain')


class VerifiedAcceptance:
    """Process-local proof returned only after committed receipt + fresh checks.

    Not a serialization format and not a substitute for a preparation contract.
    A fresh fetch is required in each owner collection transaction.
    """
    __slots__ = ('_receipt_raw', '_seal', '_expires', '_pid')

    def __init__(self, receipt_raw, seal, expires):
        _require(seal is _SEAL, 'acceptance-inactive')
        object.__setattr__(self, '_receipt_raw', receipt_raw)
        object.__setattr__(self, '_seal', seal)
        object.__setattr__(self, '_expires', expires)
        object.__setattr__(self, '_pid', os.getpid())

    def __setattr__(self, name, value):
        raise AttributeError('verified acceptance is immutable')

    def references(self):
        _require(self._seal is _SEAL and self._pid == os.getpid() and
                 time.monotonic() < self._expires, 'acceptance-inactive')
        receipt = p.strict_json(self._receipt_raw)
        return {'receiptSHA256': p.sha(self._receipt_raw),
                'receiptRelativePath': 'collection/retained-taiwan-acceptance/' + MANIFEST_SHA256 + '/receipt-' + p.sha(self._receipt_raw) + '.json',
                'acceptedAtUTC': receipt['acceptedAtUTC'], 'originalAcquiredAt': None,
                'items': [{'sourceKey': row['sourceKey'], 'assetId': row['assetId'],
                           'reference': row['reference'], 'downstreamHolds': row['downstreamHolds']}
                          for row in receipt['items']]}


def exact_accepted_bom_identity(source, data, acceptance):
    """Identity-only later-parse gate. Never strips the BOM or authorizes parsing."""
    if (not isinstance(acceptance, VerifiedAcceptance) or acceptance._seal is not _SEAL or
            acceptance._pid != os.getpid() or time.monotonic() >= acceptance._expires):
        return False
    try:
        receipt = p.strict_json(acceptance._receipt_raw)
        row = next(row for row in receipt['items'] if row['sourceKey'] == source['sourceKey'])
        return (receipt['acceptanceManifestSHA256'] == MANIFEST_SHA256 and
                row['sourceContractSHA256'] == p.sha(p.canonical(source)) and
                row['reference']['bytes'] == len(data) and
                row['reference']['sha256'] == p.sha(data) and
                r.exact_selected_bom_identity(source, data))
    except (KeyError, StopIteration, TypeError, ValueError):
        return False


def _operate(manifest_raw, *, parent_selection, owner_runtime, lease_fd,
             current_adverse_evidence, absolute_deadline, create):
    manifest = _selection(manifest_raw, parent_selection)
    _require(threading.current_thread() is threading.main_thread(), 'acceptance-main-thread-required')
    _require(type(absolute_deadline) in (int, float) and math.isfinite(absolute_deadline),
             'acceptance-deadline-exceeded')
    deadline = min(absolute_deadline, time.monotonic() + MAX_SECONDS)
    write_started = False
    try:
        with r.termination_scope() as check_signal:
            _check(deadline, check_signal)
            output_root = _context(manifest, owner_runtime)
            with ExitStack() as stack:
                snapshot = _Snapshot(stack, manifest, output_root)
                _verify_lease(lease_fd, snapshot.work)
                _admit(manifest, owner_runtime, current_adverse_evidence, deadline, check_signal)
                reports = _fresh(manifest, output_root, deadline, check_signal, snapshot, lease_fd)
                folder = _receipt_folder(snapshot, False)
                existing = _existing(snapshot, folder, manifest, parent_selection, reports)
                _admit(manifest, owner_runtime, current_adverse_evidence, deadline, check_signal)
                snapshot.verify()
                _verify_lease(lease_fd, snapshot.work)
                _check(deadline, check_signal)
                if existing is not None:
                    value, raw = existing
                    return {'status': 'reused-accepted-reference', 'dispositionApplied': False,
                            'receiptSHA256': p.sha(raw), 'acceptedAtUTC': value['acceptedAtUTC'],
                            'originalAcquiredAt': None, 'networkRequests': 0}, VerifiedAcceptance(raw, _SEAL, deadline)
                _require(create, 'acceptance-receipt-absent')
                # No custody metadata creation precedes the two live admission
                # passes and the complete fresh three-source parser validation.
                folder = _receipt_folder(snapshot, True) if folder is None else folder
                _require(not _names(folder), 'acceptance-state-conflict')
                accepted_at = datetime.now(timezone.utc).isoformat(timespec='microseconds')
                raw = p.canonical(_receipt(manifest, parent_selection, reports, accepted_at))
                digest = p.sha(raw)
                selection = p.pinned(_repo_bytes(manifest['sourceBaseline']['selectionPath']), p.SELECTION_SHA256)
                guard = selection['planningGuardBytes']
                _require(type(guard) is int and guard > 0, 'acceptance-capacity-held')
                write_started = True
                _write_exclusive(snapshot, folder, 'receipt-' + digest + '.json', raw,
                                 deadline, check_signal, guard)
                _admit(manifest, owner_runtime, current_adverse_evidence, deadline, check_signal)
                snapshot.verify()
                _verify_lease(lease_fd, snapshot.work)
                _check(deadline, check_signal)
                _write_exclusive(snapshot, folder, 'committed-' + digest + '.json',
                                 p.canonical(_commit(raw, parent_selection)), deadline, check_signal, guard)
                snapshot.verify()
                _verify_lease(lease_fd, snapshot.work)
                _check(deadline, check_signal)
                _require(_existing(snapshot, folder, manifest, parent_selection, reports) is not None,
                         'acceptance-write-uncertain')
                snapshot.verify()
                return {'status': 'accepted-retained-reference', 'dispositionApplied': True,
                        'receiptSHA256': digest, 'acceptedAtUTC': accepted_at,
                        'originalAcquiredAt': None, 'networkRequests': 0}, VerifiedAcceptance(raw, _SEAL, deadline)
    except AcceptanceError:
        raise
    except (OSError, ValueError, TypeError, KeyError):
        raise AcceptanceError('acceptance-write-uncertain' if write_started else 'acceptance-local-failure') from None



DESCRIPTOR_SCHEMA = 'offmenu-retained-taiwan-preparation-descriptor/1'
MAX_DESCRIPTOR_BYTES = 8192


def _process_start(pid):
    with open('/proc/' + str(pid) + '/stat', 'rb') as stream:
        raw = stream.read(8193)
    _require(len(raw) <= 8192, 'acceptance-lease-unverified')
    fields = raw.rsplit(b') ', 1)[1].split()
    # Field 22, after fields 1 and 2 (pid and parenthesized comm).
    return int(fields[19])


def _expected_preparation(row):
    template = row['existingPreparationSelection']
    return {'schemaVersion': 'offmenu-media-preparation-contract/1',
            'assetId': row['assetId'],
            'expectedSHA256': row['proposedCustodyReference']['sha256'],
            'expectedBytes': row['proposedCustodyReference']['bytes'],
            **{key: template[key] for key in ('permissions', 'holds', 'expectedMediaTypes', 'parameters')}}


def _load_manifest():
    raw = _repo_bytes(MANIFEST_PATH, 128 * 1024)
    _require(p.sha(raw) == MANIFEST_SHA256, 'acceptance-selection-mismatch')
    return raw, p.strict_json(raw)


def make_preparation_descriptor(acceptance, source, preparation_contract, *, lease_fd):
    """Export bounded metadata for spawn, under the still-held owner lease.

    The caller must separately have selected this exact preparation contract.
    This API verifies that selection matches the preserved existing permissions;
    it does not activate or perform preparation.
    """
    _require(isinstance(acceptance, VerifiedAcceptance), 'acceptance-inactive')
    acceptance.references()  # Checks immutable local proof, PID and deadline.
    manifest_raw, manifest = _load_manifest()
    row = next((row for row in manifest['items'] if row['sourceKey'] == source.get('sourceKey')), None)
    _require(row is not None and p.canonical(source) == p.canonical(row['sourceContract']) and
             p.canonical(preparation_contract) == p.canonical(_expected_preparation(row)),
             'acceptance-selection-mismatch')
    selection = {'schemaVersion': SELECTION_SCHEMA,
        'acceptanceManifestSHA256': MANIFEST_SHA256,
        'reviewedWriterSHA256': IMPORTED_WRITER_SHA256,
        'handoffId': manifest['existingOwnerContextBinding']['handoffId'],
        'scope': 'exact-three-unchanged-retained-reference-acceptance',
        'preparationSelected': False}
    _selection(manifest_raw, selection)
    receipt = p.strict_json(acceptance._receipt_raw)
    _require(receipt['parentSelectionSHA256'] == p.sha(p.canonical(selection)), 'acceptance-selection-mismatch')
    with ExitStack() as stack:
        root = r.d.open_root(stack, r.d.OUTPUT_ROOT)
        work = r.d.open_child(stack, root, 'collection', True)
        _private_fd(work, True)
        _verify_lease(lease_fd, work)
        info = os.fstat(lease_fd)
        lease = {'pid': os.getpid(), 'fd': lease_fd, 'device': info.st_dev,
                 'inode': info.st_ino, 'processStartTicks': _process_start(os.getpid())}
    ref = row['proposedCustodyReference']
    descriptor = {'schemaVersion': DESCRIPTOR_SCHEMA,
        'acceptanceManifestSHA256': MANIFEST_SHA256,
        'receiptSHA256': p.sha(acceptance._receipt_raw),
        'parentSelection': selection, 'sourceKey': row['sourceKey'],
        'sourceContractSHA256': row['sourceContractSHA256'],
        'originalRelativePath': ref['relativePath'], 'originalSHA256': ref['sha256'],
        'originalBytes': ref['bytes'],
        'preparationContractSHA256': p.sha(p.canonical(preparation_contract)),
        'ownerLease': lease, 'expiresMonotonic': acceptance._expires}
    _require(len(p.canonical(descriptor)) <= MAX_DESCRIPTOR_BYTES, 'acceptance-selection-mismatch')
    return json.loads(p.canonical(descriptor))


def _verify_parent_lease(lease, work_fd):
    _require(isinstance(lease, dict) and set(lease) == {'pid', 'fd', 'device', 'inode', 'processStartTicks'} and
             all(type(value) is int and value >= 0 for value in lease.values()) and
             0 < lease['pid'] <= 2**31 - 1 and lease['fd'] <= 2**20,
             'acceptance-lease-unverified')
    named = os.stat('fixed-selection.lock', dir_fd=work_fd, follow_symlinks=False)
    _require(stat.S_ISREG(named.st_mode) and named.st_uid == r.d.EXPECTED_UID and
             not named.st_mode & 0o077 and named.st_nlink == 1 and
             (named.st_dev, named.st_ino) == (lease['device'], lease['inode']) and
             _process_start(lease['pid']) == lease['processStartTicks'], 'acceptance-lease-unverified')
    with open('/proc/' + str(lease['pid']) + '/fdinfo/' + str(lease['fd']), 'rb') as stream:
        raw = stream.read(16385)
    _require(len(raw) <= 16384, 'acceptance-lease-unverified')
    locks = re.findall(rb'^lock:\s+\d+: FLOCK\s+ADVISORY\s+WRITE\s+(\d+)\s+([0-9a-f]+):([0-9a-f]+):(\d+)\s+0 EOF$', raw, re.M)
    expected = (lease['pid'], os.major(named.st_dev), os.minor(named.st_dev), named.st_ino)
    _require(any((int(pid), int(major, 16), int(minor, 16), int(ino)) == expected
                 for pid, major, minor, ino in locks), 'acceptance-lease-unverified')


def verify_worker_descriptor(descriptor, source, data, original_path, preparation_contract, *, absolute_deadline):
    """Spawn-safe read-only exact BOM gate. No parser, claims writes or output.

    Verify a committed receipt, live parent lease and current unchanged original
    bytes. Call after ordinary media-contract/integrity permission checks and
    before the narrow PDF media identification exception. Return only metadata.
    Current native claims are admitted by the owner before queueing; this worker
    must remain inside that live owner lease and the descriptor deadline.
    """
    try:
        _require(isinstance(descriptor, dict) and len(p.canonical(descriptor)) <= MAX_DESCRIPTOR_BYTES,
                 'acceptance-selection-mismatch')
        keys = {'schemaVersion', 'acceptanceManifestSHA256', 'receiptSHA256', 'parentSelection',
                'sourceKey', 'sourceContractSHA256', 'originalRelativePath', 'originalSHA256',
                'originalBytes', 'preparationContractSHA256', 'ownerLease', 'expiresMonotonic'}
        _require(set(descriptor) == keys and descriptor['schemaVersion'] == DESCRIPTOR_SCHEMA and
                 descriptor['acceptanceManifestSHA256'] == MANIFEST_SHA256 and
                 type(descriptor['expiresMonotonic']) in (int, float) and
                 math.isfinite(descriptor['expiresMonotonic']) and
                 type(absolute_deadline) in (int, float) and math.isfinite(absolute_deadline),
                 'acceptance-selection-mismatch')
        deadline = min(absolute_deadline, descriptor['expiresMonotonic'], time.monotonic() + 30)
        _check(deadline, lambda: None)
        manifest_raw, manifest = _load_manifest()
        _selection(manifest_raw, descriptor['parentSelection'])
        _require(os.getuid() == os.geteuid() == r.d.EXPECTED_UID, 'acceptance-owner-context-mismatch')
        context = manifest['existingOwnerContextBinding']
        for path, digest in [(context['runtimeConfigPath'], context['runtimeConfigSHA256']),
                             (context['dispatchHoldPath'], context['dispatchHoldSHA256']),
                             *DEPENDENCY_PINS.items()]:
            _require(p.sha(_repo_bytes(path)) == digest, 'acceptance-owner-context-mismatch')
        row = next((row for row in manifest['items'] if row['sourceKey'] == descriptor['sourceKey']), None)
        _require(row is not None and p.canonical(source) == p.canonical(row['sourceContract']),
                 'acceptance-selection-mismatch')
        ref = row['proposedCustodyReference']
        expected = {'sourceContractSHA256': row['sourceContractSHA256'],
                    'originalRelativePath': ref['relativePath'], 'originalSHA256': ref['sha256'],
                    'originalBytes': ref['bytes'],
                    'preparationContractSHA256': p.sha(p.canonical(_expected_preparation(row)))}
        _require(all(type(descriptor[key]) is type(value) and descriptor[key] == value
                     for key, value in expected.items()) and
                 p.canonical(preparation_contract) == p.canonical(_expected_preparation(row)) and
                 Path(original_path) == r.d.OUTPUT_ROOT / ref['relativePath'] and
                 type(data) is bytes and len(data) == ref['bytes'] and p.sha(data) == ref['sha256'] and
                 r.exact_selected_bom_identity(source, data), 'acceptance-selection-mismatch')
        with ExitStack() as stack:
            snapshot = _Snapshot(stack, {**manifest, 'items': [row]}, r.d.OUTPUT_ROOT)
            _verify_parent_lease(descriptor['ownerLease'], snapshot.work)
            folder = _receipt_folder(snapshot, False)
            existing = _existing(snapshot, folder, manifest, descriptor['parentSelection'],
                                 [item['validationProposal'] for item in manifest['items']])
            _require(existing is not None and p.sha(existing[1]) == descriptor['receiptSHA256'],
                     'acceptance-state-conflict')
            fd = snapshot.bodies[row['sourceKey']]
            digest, count = hashlib.sha256(), 0
            while count < ref['bytes']:
                _check(deadline, lambda: None)
                block = os.read(fd, min(65536, ref['bytes'] - count))
                _require(bool(block), 'acceptance-custody-changed')
                digest.update(block)
                count += len(block)
            _require(digest.hexdigest() == ref['sha256'], 'acceptance-custody-changed')
            snapshot.verify()
            _verify_parent_lease(descriptor['ownerLease'], snapshot.work)
            _check(deadline, lambda: None)
            return {'status': 'verified-exact-retained-bom-identity',
                    'sourceKey': row['sourceKey'], 'receiptSHA256': descriptor['receiptSHA256'],
                    'originalSHA256': ref['sha256'], 'originalBytes': count,
                    'actualMediaType': 'application/pdf', 'parserExecuted': False,
                    'normalizationPerformed': False, 'networkRequests': 0}
    except AcceptanceError:
        raise
    except (OSError, ValueError, TypeError, KeyError, IndexError):
        raise AcceptanceError('acceptance-local-failure') from None


def accept_selected(manifest_raw, *, parent_selection=None, owner_runtime=None, lease_fd=None,
                    current_adverse_evidence=None, absolute_deadline=0):
    """Explicit owner-only write API. Raises AcceptanceError on every blocked path."""
    return _operate(manifest_raw, parent_selection=parent_selection, owner_runtime=owner_runtime,
        lease_fd=lease_fd, current_adverse_evidence=current_adverse_evidence,
        absolute_deadline=absolute_deadline, create=True)


def fetch_accepted_references(manifest_raw, *, parent_selection=None, owner_runtime=None,
                              lease_fd=None, current_adverse_evidence=None, absolute_deadline=0):
    """Read-only reuse API: requires committed receipt and repeats all live checks."""
    return _operate(manifest_raw, parent_selection=parent_selection, owner_runtime=owner_runtime,
        lease_fd=lease_fd, current_adverse_evidence=current_adverse_evidence,
        absolute_deadline=absolute_deadline, create=False)
