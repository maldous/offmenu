"""Synthetic owner-runtime tests only; no Foo, publisher, or original body I/O."""
from contextlib import ExitStack
from copy import deepcopy
from datetime import datetime, timezone
import fcntl
import hashlib
import importlib.util
import json
import multiprocessing
import socket
import subprocess
import os
from pathlib import Path
import signal
import threading
import time
from types import SimpleNamespace
import unittest
from unittest.mock import patch
import test_retained_taiwan_recovery as recovery_fixture

ROOT = Path(__file__).resolve().parents[1]


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, ROOT / path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


w = load('taiwan_acceptance_writer_test', 'scripts/accept-retained-taiwan.py')
g = load('taiwan_acceptance_owner_test', 'scripts/collect-fixed-global.py')


def spawn_descriptor_check(connection, root, uid, entries, pins, manifest_raw,
                           manifest_sha, descriptor, source, body, path, contract):
    """Only synthetic local data is transferred into this spawned worker."""
    original_read = w._repo_bytes
    def read_repo(name, maximum=8 * 1024 * 1024):
        return manifest_raw if name == w.MANIFEST_PATH else original_read(name, maximum)
    try:
        with ExitStack() as stack:
            stack.enter_context(patch.object(w.r.d, 'OUTPUT_ROOT', Path(root)))
            stack.enter_context(patch.object(w.r.d, 'EXPECTED_UID', uid))
            stack.enter_context(patch.object(w.r.d, 'ENTRIES', entries))
            stack.enter_context(patch.object(w.r, 'PINS', pins))
            stack.enter_context(patch.object(w, 'MANIFEST_SHA256', manifest_sha))
            stack.enter_context(patch.object(w, '_repo_bytes', side_effect=read_repo))
            stack.enter_context(patch.object(w.r, 'validate_selected', side_effect=AssertionError('no worker parser')))
            stack.enter_context(patch.object(subprocess, 'Popen', side_effect=AssertionError('no subprocess')))
            stack.enter_context(patch.object(socket, 'socket', side_effect=AssertionError('no network')))
            result = w.verify_worker_descriptor(descriptor, source, body, path, contract,
                                                absolute_deadline=time.monotonic() + 20)
        connection.send(('ok', result, os.getpid()))
    except BaseException as error:
        connection.send(('error', repr(error), os.getpid()))
    finally:
        connection.close()


class AcceptanceWriterTests(unittest.TestCase):
    def setUp(self):
        self.fixture = recovery_fixture.RecoveryTests()
        self.fixture.setUp()
        self.stack = ExitStack()
        self.stack.enter_context(patch.object(w, 'r', recovery_fixture.r))
        self.stack.enter_context(patch.object(g, 'OWNER_PIN',
            ('docs/collection-selections/owner-comprehensive-runtime.json',
             '28acbde120ac7d457f24af8cd2e3203927bb770137b8ce414c0d7a082e63b4ba')))
        self.stack.enter_context(patch.object(w.os, 'fstatvfs',
            return_value=SimpleNamespace(f_bavail=1024**3, f_frsize=4096)))
        self.root = self.fixture.fixture.root
        self.work = self.root / 'collection'
        self.owner = g.OwnerRuntime.__new__(g.OwnerRuntime)
        self.owner.root = self.root
        self.owner.uid = os.getuid()
        self.owner.config = json.loads((ROOT / 'docs/collection-selections/owner-comprehensive-runtime.json').read_bytes())
        self.owner.selected = json.loads((ROOT / 'docs/collection-selections/global-comprehensive-selection.json').read_bytes())
        self.owner.native = self.root / 'native-claims'
        self.owner.native.mkdir(mode=0o700)
        self.owner.runner_work = self.root / 'historical-work'
        self.owner.runner_cache = self.root / 'historical-cache'
        # The real API requires the fixed production paths. Redirect only this
        # path-policy seam to named synthetic roots; use the real live scanner.
        expected_paths = (self.owner.native, self.owner.runner_work, self.owner.runner_cache)
        def synthetic_runtime_paths(owner, config):
            w._require((owner.native, owner.runner_work, owner.runner_cache) == expected_paths,
                       'acceptance-owner-context-mismatch')
        self.stack.enter_context(patch.object(w, '_check_runtime_paths', side_effect=synthetic_runtime_paths))
        manifest = json.loads((ROOT / w.MANIFEST_PATH).read_bytes())
        for index, row in enumerate(manifest['items']):
            fresh = self.fixture.validate(index)
            self.assertEqual(fresh['status'], 'validated-proposal')
            row['validationProposal'] = fresh
            row['validationProposalCanonicalSHA256'] = w.p.sha(w.p.canonical(fresh))
            ref = row['proposedCustodyReference']
            ref.update(fresh['proposedDisposition'])
            ref['runtimeRoot'] = str(self.root)
            ref['expectedOwnerUID'] = os.getuid()
            ref['oldFailedIntent']['sha256'] = fresh['oldFailedIntentSHA256']
            ref['oldFailedDetail']['sha256'] = fresh['priorFailedDetailSHA256']
            ref['oldFailedDetail']['relativePath'] = 'collection/private-original-result-' + fresh['priorFailedDetailSHA256'] + '.json'
        self.manifest = manifest
        self.raw = w.p.canonical(manifest)
        self.stack.enter_context(patch.object(w, 'MANIFEST_SHA256', w.p.sha(self.raw)))
        self.original_repo_read = w._repo_bytes
        def read_repo(name, maximum=8 * 1024 * 1024):
            return self.raw if name == w.MANIFEST_PATH else self.original_repo_read(name, maximum)
        self.stack.enter_context(patch.object(w, '_repo_bytes', side_effect=read_repo))
        self.selection = {'schemaVersion': w.SELECTION_SCHEMA,
            'acceptanceManifestSHA256': w.MANIFEST_SHA256,
            'reviewedWriterSHA256': w.p.sha((ROOT / 'scripts/accept-retained-taiwan.py').read_bytes()),
            'handoffId': 'owner-local-comprehensive-20261018-002',
            'scope': 'exact-three-unchanged-retained-reference-acceptance',
            'preparationSelected': False}
        self.lease = self.stack.enter_context(g.a.writer_lock(self.work / 'fixed-selection.lock'))
        self.evidence = []
        self.before = self.original_snapshot()

    def tearDown(self):
        self.stack.close()
        self.fixture.tearDown()

    def original_snapshot(self):
        fixture = self.fixture.fixture
        paths = fixture.details + [folder / name for folder in fixture.folders
                                    for name in ['original.partial', 'successor-intent.json']]
        return {str(path): (path.read_bytes(), w.r.d.identity(path.stat())) for path in paths}

    def invoke(self, fetch=False, **overrides):
        kwargs = {'parent_selection': self.selection, 'owner_runtime': self.owner,
                  'lease_fd': self.lease, 'current_adverse_evidence': lambda: self.evidence,
                  'absolute_deadline': time.monotonic() + 40}
        kwargs.update(overrides)
        return (w.fetch_accepted_references if fetch else w.accept_selected)(self.raw, **kwargs)

    def folder(self):
        return self.work / 'retained-taiwan-acceptance' / w.MANIFEST_SHA256

    def assert_blocked(self, code=None, **kwargs):
        with self.assertRaises(w.AcceptanceError) as raised:
            self.invoke(**kwargs)
        if code:
            self.assertEqual(str(raised.exception), code)

    def test_accepts_exact_three_without_any_original_or_failed_record_change(self):
        start = datetime.now(timezone.utc)
        result, capability = self.invoke()
        self.assertEqual(result['status'], 'accepted-retained-reference')
        self.assertTrue(result['dispositionApplied'])
        self.assertIsNone(result['originalAcquiredAt'])
        self.assertGreaterEqual(datetime.fromisoformat(result['acceptedAtUTC']), start)
        self.assertEqual(result['networkRequests'], 0)
        self.assertEqual(self.original_snapshot(), self.before)
        files = sorted(self.folder().iterdir())
        self.assertEqual(len(files), 2)
        for path in files:
            self.assertEqual(path.stat().st_mode & 0o777, 0o600)
            self.assertEqual(path.stat().st_nlink, 1)
        refs = capability.references()
        self.assertEqual(len(refs['items']), 3)
        self.assertEqual(refs['receiptSHA256'], result['receiptSHA256'])
        self.assertTrue(all(row['reference']['relativePath'].endswith('/original.partial') for row in refs['items']))
        self.assertEqual([row['downstreamHolds'] for row in refs['items']], [w.p.HOLDS] * 3)

    def test_repeated_acceptance_and_readonly_fetch_do_not_write_new_receipts(self):
        first, _ = self.invoke()
        snapshot = {p.name: (p.read_bytes(), w.r.d.identity(p.stat())) for p in self.folder().iterdir()}
        for fetch in [False, True]:
            result, capability = self.invoke(fetch=fetch)
            self.assertEqual(result['status'], 'reused-accepted-reference')
            self.assertFalse(result['dispositionApplied'])
            self.assertEqual(result['acceptedAtUTC'], first['acceptedAtUTC'])
            self.assertEqual(result['receiptSHA256'], first['receiptSHA256'])
            self.assertEqual(capability.references()['receiptSHA256'], first['receiptSHA256'])
        self.assertEqual(snapshot, {p.name: (p.read_bytes(), w.r.d.identity(p.stat())) for p in self.folder().iterdir()})
        self.assertEqual(self.original_snapshot(), self.before)

    def test_fetch_without_receipt_is_readonly_and_fails(self):
        self.assert_blocked('acceptance-receipt-absent', fetch=True)
        self.assertFalse((self.work / 'retained-taiwan-acceptance').exists())
        self.assertEqual(self.original_snapshot(), self.before)

    def test_no_selection_no_owner_io(self):
        with patch.object(w, '_context', side_effect=AssertionError('must not inspect owner')):
            self.assert_blocked('acceptance-inactive', parent_selection=None)
        for key, value in [('acceptanceManifestSHA256', '0' * 64),
                           ('reviewedWriterSHA256', '0' * 64), ('preparationSelected', True),
                           ('handoffId', 'replacement')]:
            selection = deepcopy(self.selection)
            selection[key] = value
            self.assert_blocked('acceptance-selection-mismatch', parent_selection=selection)

    def test_requires_main_thread(self):
        errors = []
        def target():
            try:
                self.invoke()
            except Exception as error:
                errors.append(str(error))
        thread = threading.Thread(target=target)
        thread.start()
        thread.join()
        self.assertEqual(errors, ['acceptance-main-thread-required'])
        self.assertFalse(self.folder().exists())

    def test_unheld_or_different_open_description_is_not_a_writer_lease(self):
        fd = os.open(self.work / 'fixed-selection.lock', os.O_RDWR | os.O_NOFOLLOW)
        try:
            self.assert_blocked('acceptance-lease-unverified', lease_fd=fd)
        finally:
            os.close(fd)
        fcntl.flock(self.lease, fcntl.LOCK_UN)
        try:
            self.assert_blocked('acceptance-lease-unverified')
        finally:
            fcntl.flock(self.lease, fcntl.LOCK_EX | fcntl.LOCK_NB)
        self.assertFalse(self.folder().exists())

    def test_replaced_lease_path_is_rejected(self):
        path = self.work / 'fixed-selection.lock'
        path.rename(path.with_name('old-lock'))
        path.write_bytes(b'{}')
        path.chmod(0o600)
        self.assert_blocked('acceptance-lease-unverified')
        self.assertFalse(self.folder().exists())

    def test_current_native_claim_and_adverse_evidence_block(self):
        source = self.manifest['items'][0]['sourceContract']
        self.evidence = [{'sourceKey': source['sourceKey']}]
        self.assert_blocked('acceptance-current-conflict')
        self.evidence = []
        claim = self.owner.native / (w.p.sha(source['url'].encode()) + '.json')
        claim.write_bytes(b'{}')
        self.assert_blocked('acceptance-admission-unavailable')
        self.assertFalse(self.folder().exists())

    def test_missing_native_claim_root_is_not_an_empty_claim_catalogue(self):
        self.owner.native.rmdir()
        self.assert_blocked('acceptance-admission-unavailable')
        self.assertFalse(self.folder().exists())

    def test_changed_runtime_or_source_hold_blocks(self):
        self.owner.config['handoffId'] = 'replacement'
        self.assert_blocked('acceptance-owner-context-mismatch')
        self.owner.config = json.loads((ROOT / 'docs/collection-selections/owner-comprehensive-runtime.json').read_bytes())
        self.owner.selected['sources'][0]['sourceAcquisitionHeld'] = True
        self.assert_blocked('acceptance-owner-context-mismatch')

    def test_changed_body_or_intent_and_parser_failure_block_without_receipts(self):
        real = w.r.validate_selected
        def blocked(*args, **kwargs):
            value = real(*args, **kwargs)
            value['parser']['diagnosticBytes'] = 1
            return value
        with patch.object(w.r, 'validate_selected', side_effect=blocked):
            self.assert_blocked('acceptance-fresh-validation-failed')
        self.assertFalse(self.folder().exists())
        body = self.fixture.fixture.folders[0] / 'original.partial'
        raw = body.read_bytes()
        body.write_bytes(raw.replace(b'Synthetic', b'Different'))
        self.assert_blocked('acceptance-fresh-validation-failed')
        self.assertFalse(self.folder().exists())

    def test_reuse_still_runs_fresh_validator(self):
        self.invoke()
        with patch.object(w.r, 'validate_selected', side_effect=AssertionError('fresh gate reached')):
            with self.assertRaises(AssertionError):
                self.invoke(fetch=True)
        with patch.object(w.r, 'validate_selected', return_value={'status': 'blocked'}):
            self.assert_blocked('acceptance-fresh-validation-failed', fetch=True)

    def test_original_path_replaced_after_validation_blocks(self):
        real = w.r.validate_selected
        count = 0
        def swapped(*args, **kwargs):
            nonlocal count
            result = real(*args, **kwargs)
            count += 1
            if count == 3:
                path = self.fixture.fixture.folders[0] / 'original.partial'
                raw = path.read_bytes()
                path.rename(path.with_name('unselected-original'))
                path.write_bytes(raw)
                path.chmod(0o600)
            return result
        with patch.object(w.r, 'validate_selected', side_effect=swapped):
            self.assert_blocked('acceptance-custody-changed')
        self.assertFalse(self.folder().exists())

    def test_new_claim_during_validation_blocks(self):
        calls = 0
        def current():
            nonlocal calls
            calls += 1
            return [] if calls == 1 else [{'sourceKey': self.manifest['items'][1]['sourceKey']}]
        self.assert_blocked('acceptance-current-conflict', current_adverse_evidence=current)
        self.assertFalse(self.folder().exists())

    def test_symlink_or_conflicting_receipt_location_is_rejected(self):
        (self.work / 'retained-taiwan-acceptance').symlink_to(self.owner.native, target_is_directory=True)
        self.assert_blocked()
        self.assertEqual(list(self.owner.native.iterdir()), [])

    def test_partial_write_is_retained_and_never_retried_or_reused(self):
        real = w.os.write
        calls = 0
        def interrupted(fd, data):
            nonlocal calls
            if '/retained-taiwan-acceptance/' not in os.readlink('/proc/self/fd/' + str(fd)):
                return real(fd, data)
            calls += 1
            if calls == 1:
                return real(fd, data[:17])
            raise OSError('synthetic interrupted receipt write')
        with patch.object(w.os, 'write', side_effect=interrupted):
            self.assert_blocked('acceptance-write-uncertain')
        paths = list(self.folder().iterdir())
        self.assertEqual(len(paths), 1)
        before = paths[0].read_bytes()
        self.assertEqual(len(before), 17)
        self.assert_blocked('acceptance-write-uncertain')
        self.assertEqual(paths[0].read_bytes(), before)
        self.assertEqual(self.original_snapshot(), self.before)

    def test_complete_receipt_without_commit_is_uncertain(self):
        real = w._write_exclusive
        def stop(snapshot, folder, name, *args):
            if name.startswith('committed-'):
                raise OSError('before commit')
            return real(snapshot, folder, name, *args)
        with patch.object(w, '_write_exclusive', side_effect=stop):
            self.assert_blocked('acceptance-write-uncertain')
        self.assertEqual(len(list(self.folder().iterdir())), 1)
        self.assert_blocked('acceptance-write-uncertain', fetch=True)
        self.assertEqual(self.original_snapshot(), self.before)

    def test_sigterm_during_receipt_write_preserves_uncertain_state_and_restores_handler(self):
        original_handler = signal.getsignal(signal.SIGTERM)
        delivered = []
        handler = lambda signum, frame: delivered.append(signum)
        signal.signal(signal.SIGTERM, handler)
        real = w.os.write
        sent = False
        def signaled(fd, data):
            nonlocal sent
            written = real(fd, data)
            if not sent and '/retained-taiwan-acceptance/' in os.readlink('/proc/self/fd/' + str(fd)):
                sent = True
                os.kill(os.getpid(), signal.SIGTERM)
            return written
        try:
            with patch.object(w.os, 'write', side_effect=signaled):
                self.assert_blocked('acceptance-write-uncertain')
            self.assertIs(signal.getsignal(signal.SIGTERM), handler)
            self.assertEqual(delivered, [signal.SIGTERM])
        finally:
            signal.signal(signal.SIGTERM, original_handler)
        self.assertTrue(sent)
        self.assertEqual(len(list(self.folder().glob('receipt-*.json'))), 1)
        self.assertEqual(len(list(self.folder().glob('committed-*.json'))), 0)
        self.assert_blocked('acceptance-write-uncertain')
        self.assertEqual(self.original_snapshot(), self.before)

    def test_changed_failed_intent_after_validation_prevents_commit(self):
        calls = 0
        def current():
            nonlocal calls
            calls += 1
            if calls == 3:
                path = self.fixture.fixture.folders[0] / 'successor-intent.json'
                path.write_bytes(path.read_bytes() + b' ')
            return []
        self.assert_blocked('acceptance-custody-changed', current_adverse_evidence=current)
        self.assertEqual(len(list(self.folder().glob('receipt-*.json'))), 1)
        self.assertEqual(len(list(self.folder().glob('committed-*.json'))), 0)

    def test_conflicting_second_receipt_never_replaces_committed_custody(self):
        self.invoke()
        originals = {path.name: path.read_bytes() for path in self.folder().iterdir()}
        extra = self.folder() / ('receipt-' + '0' * 64 + '.json')
        extra.write_bytes(b'{}')
        extra.chmod(0o600)
        self.assert_blocked('acceptance-state-conflict')
        for name, raw in originals.items():
            self.assertEqual((self.folder() / name).read_bytes(), raw)
        self.assertEqual(self.original_snapshot(), self.before)

    def test_low_capacity_does_not_write_receipt(self):
        with patch.object(w.os, 'fstatvfs', return_value=SimpleNamespace(f_bavail=0, f_frsize=4096)):
            self.assert_blocked('acceptance-capacity-held')
        self.assertEqual(list(self.folder().iterdir()), [])

    def test_committed_receipt_or_marker_tampering_is_rejected(self):
        self.invoke()
        marker = next(self.folder().glob('committed-*.json'))
        original = marker.read_bytes()
        marker.write_bytes(b'{}\n')
        self.assert_blocked('acceptance-state-conflict', fetch=True)
        marker.write_bytes(original)
        receipt = next(self.folder().glob('receipt-*.json'))
        receipt.write_bytes(receipt.read_bytes().replace(b'accepted-retained-references', b'changed--retained-references'))
        self.assert_blocked(fetch=True)

    def test_exact_bom_gate_requires_verified_capability_and_exact_source_and_bytes(self):
        _, capability = self.invoke()
        source = self.manifest['items'][0]['sourceContract']
        body = (self.fixture.fixture.folders[0] / 'original.partial').read_bytes()
        self.assertTrue(w.exact_accepted_bom_identity(source, body, capability))
        self.assertFalse(w.exact_accepted_bom_identity(source, body, None))
        self.assertFalse(w.exact_accepted_bom_identity(source, body[3:], capability))
        self.assertFalse(w.exact_accepted_bom_identity(source, body.replace(b'Synthetic', b'Different'), capability))
        changed = deepcopy(source)
        changed['url'] += '&other=1'
        self.assertFalse(w.exact_accepted_bom_identity(changed, body, capability))
        self.assertEqual(self.original_snapshot(), self.before)

    def test_verified_capability_is_immutable_and_bounded_to_the_transaction(self):
        _, capability = self.invoke()
        with self.assertRaises(AttributeError):
            capability._receipt_raw = b'{}'
        source = self.manifest['items'][0]['sourceContract']
        body = (self.fixture.fixture.folders[0] / 'original.partial').read_bytes()
        with patch.object(w.time, 'monotonic', return_value=capability._expires + 1):
            self.assertFalse(w.exact_accepted_bom_identity(source, body, capability))
            with self.assertRaises(w.AcceptanceError):
                capability.references()

    def descriptor(self):
        _, capability = self.invoke()
        row = self.manifest['items'][0]
        source = row['sourceContract']
        contract = w._expected_preparation(row)
        body_path = self.root / row['proposedCustodyReference']['relativePath']
        descriptor = w.make_preparation_descriptor(capability, source, contract, lease_fd=self.lease)
        return descriptor, source, body_path.read_bytes(), body_path, contract

    def test_serializable_worker_descriptor_reads_and_hashes_without_parser_or_writes(self):
        descriptor, source, body, body_path, contract = self.descriptor()
        descriptor = json.loads(json.dumps(descriptor))
        before = self.fixture.fixture.snapshot()
        with patch.object(w.r, 'validate_selected', side_effect=AssertionError('no worker parser')):
            result = w.verify_worker_descriptor(descriptor, source, body, body_path, contract,
                                                absolute_deadline=time.monotonic() + 20)
        self.assertEqual(result['status'], 'verified-exact-retained-bom-identity')
        self.assertFalse(result['parserExecuted'])
        self.assertEqual(before, self.fixture.fixture.snapshot())
        self.assertLess(len(w.p.canonical(descriptor)), w.MAX_DESCRIPTOR_BYTES)

    def test_spawn_worker_verifies_exact_descriptor_under_live_parent_lease(self):
        descriptor, source, body, body_path, contract = self.descriptor()
        context = multiprocessing.get_context('spawn')
        parent, child = context.Pipe(duplex=False)
        process = context.Process(target=spawn_descriptor_check, args=(child, str(self.root),
            os.getuid(), w.r.d.ENTRIES, w.r.PINS, self.raw, w.MANIFEST_SHA256,
            descriptor, source, body, str(body_path), contract))
        process.start()
        child.close()
        try:
            self.assertTrue(parent.poll(20), 'spawn worker timed out')
            status, result, pid = parent.recv()
            self.assertEqual(status, 'ok', result)
            self.assertNotEqual(pid, os.getpid())
            self.assertEqual(result['status'], 'verified-exact-retained-bom-identity')
        finally:
            parent.close()
            process.join(10)
            if process.is_alive():
                process.terminate()
                process.join(10)
        self.assertEqual(process.exitcode, 0)
        self.assertEqual(self.original_snapshot(), self.before)

    def test_worker_rejects_unheld_parent_lease_and_changed_descriptor_or_permissions(self):
        descriptor, source, body, body_path, contract = self.descriptor()
        def verify(value=descriptor, data=body, preparation=contract):
            return w.verify_worker_descriptor(value, source, data, body_path, preparation,
                                               absolute_deadline=time.monotonic() + 20)
        for key, replacement in [('receiptSHA256', '0' * 64), ('sourceKey', 'unselected'),
                                 ('originalBytes', 1), ('originalRelativePath', '../other'),
                                 ('expiresMonotonic', time.monotonic() - 1)]:
            value = deepcopy(descriptor)
            value[key] = replacement
            with self.subTest(key=key), self.assertRaises(w.AcceptanceError):
                verify(value)
        altered = deepcopy(contract)
        altered['holds'] = ['extract']
        with self.assertRaises(w.AcceptanceError):
            verify(preparation=altered)
        with self.assertRaises(w.AcceptanceError):
            verify(data=body[3:])
        fcntl.flock(self.lease, fcntl.LOCK_UN)
        try:
            with self.assertRaises(w.AcceptanceError):
                verify()
        finally:
            fcntl.flock(self.lease, fcntl.LOCK_EX | fcntl.LOCK_NB)

    def test_worker_rejects_current_original_mutation_and_missing_commit(self):
        descriptor, source, body, body_path, contract = self.descriptor()
        body_path.write_bytes(body.replace(b'Synthetic', b'Different'))
        with self.assertRaises(w.AcceptanceError):
            w.verify_worker_descriptor(descriptor, source, body, body_path, contract,
                                       absolute_deadline=time.monotonic() + 20)
        body_path.write_bytes(body)
        marker = next(self.folder().glob('committed-*.json'))
        marker.rename(marker.with_suffix('.interrupted'))
        with self.assertRaises(w.AcceptanceError):
            w.verify_worker_descriptor(descriptor, source, body, body_path, contract,
                                       absolute_deadline=time.monotonic() + 20)

    def test_deadline_blocks_before_custody_writes(self):
        self.assert_blocked('acceptance-deadline-exceeded', absolute_deadline=time.monotonic() - 1)
        self.assertFalse(self.folder().exists())


if __name__ == '__main__':
    unittest.main()
