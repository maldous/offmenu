"""No HTTP or owner-runtime access: exact-five guards use synthetic private trees."""
from contextlib import ExitStack
from copy import deepcopy
import fcntl
import json
import os
from pathlib import Path
import socket
import tempfile
import time
import unittest
from unittest.mock import patch

from offmenu.refresh import owner_head_diagnostic as d
from offmenu.refresh import owner_head_metadata as m
from offmenu.refresh.core import RefreshError, canonical, sha
from offmenu.refresh import fetch_reconciliation_runtime as integrated

def setUpModule():
    global _reviewed_dependencies
    _reviewed_dependencies=integrated.reviewed_head_dependencies()
    _reviewed_dependencies.__enter__()
def tearDownModule():
    _reviewed_dependencies.__exit__(None,None,None)



class Fixture:
    def __init__(self, case):
        self.stack = ExitStack(); case.addCleanup(self.stack.close)
        self.temp = self.stack.enter_context(tempfile.TemporaryDirectory())
        self.root = Path(self.temp) / 'owner'; self.root.mkdir(mode=0o700)
        self.manifest, self.sources, self.selected, self.config = deepcopy(d.load_bundle())
        self.uid = os.getuid()
        self.manifest.update(ownerUID=self.uid, outputRoot=str(self.root))
        self.calls, self.admits = [], []
        self.deny = False
        for item in self.sources:
            e, source = item['entry'], item['contract']
            folder = 'collection/private-originals/' + e['sourceContractSHA256']
            intent = {'schemaVersion': 'offmenu-private-original-successor/1', 'sourceKey': e['sourceKey'],
                'url': source['url'], 'sourceContractSHA256': e['sourceContractSHA256'],
                'predecessor': None, 'diagnosticReportSHA256': self.manifest['failedIntentDiagnosticReportSHA256'], 'owner': self.uid,
                'ownerHandover': self.manifest['ownerHandover'], 'state': 'failed-no-retry',
                'errorCode': e['priorErrorCode'], 'network': {'requests': 1, 'bodyBytesRead': 0},
                'privateSaveState': 'none', 'localBodyBytes': 0}
            e['expectedIntentSHA256'] = sha(canonical(intent))
            self.write(folder + '/successor-intent.json', intent)
            for key, status, code, requests in (
                    ('priorDetailSHA256', 'failed', e['priorErrorCode'], 1),
                    ('freshFetchDetailSHA256', 'blocked', 'private-save-intent-uncertain', 0)):
                value = {'schemaVersion': 'offmenu-private-media-original-save-detail/1',
                    'sourceKey': e['sourceKey'], 'selectionSHA256': e['sourceContractSHA256'],
                    'status': status, 'errorCode': code, 'network': {'requests': requests, 'bodyBytesRead': 0},
                    'privateSaveState': 'none', 'localBodyBytes': 0, 'receiptPersistence': 'written',
                    'downstreamHolds': source['downstreamHolds'], 'responseMetadata': None,
                    'responsePolicy': None}
                e[key] = sha(canonical(value))
                self.write('collection/private-original-result-' + e[key] + '.json', value)
            e['priorResponseMetadataSHA256'] = e['priorResponsePolicySHA256'] = sha(canonical(None))
        self.write('collection/fixed-selection.lock', b'existing writer lease\n')
        digest = self.manifest['fetchResultSHA256']
        self.write('collection/manual-results/latest-fetch.json', {'schemaVersion': 'offmenu-manual-result-pointer/1', 'resultFilename': 'result-' + digest + '.json', 'resultSHA256': digest})
        self.write('collection/manual-results/result-' + digest + '.json', (d.ROOT / self.manifest['inputs']['fetch-summary.json']['path']).read_bytes())
        # This test account may be root; inject a non-root UID solely at the authorization check.
        self.stack.enter_context(patch.object(d, 'load_bundle', return_value=(self.manifest, self.sources, self.selected, self.config)))
        self.stack.enter_context(patch.object(d, 'ACTIVATION_SHA256', 'f' * 64))
        self.stack.enter_context(patch.object(d, 'activation', return_value={'selected': True}))
        self.stack.enter_context(patch.object(d, 'collector_module', return_value=None))
        self.stack.enter_context(patch.object(d, 'current_runtime', side_effect=lambda *args: self))
        if self.uid == 0:
            self.manifest['ownerUID'] = 12345
            # SafeTree ownership is real; only runtime UID authorization is synthetic.
            self.stack.enter_context(patch.object(d.os, 'getuid', return_value=12345))
            self.stack.enter_context(patch.object(d.os, 'geteuid', return_value=12345))
            real_tree = d.SafeTree
            self.stack.enter_context(patch.object(d, 'SafeTree', side_effect=lambda root, uid: real_tree(root, 0)))
            for item in self.sources:
                e = item['entry']; p = self.intent_path(item)
                intent = json.loads(p.read_bytes()); intent['owner'] = 12345
                self.write(p.relative_to(self.root), intent); e['expectedIntentSHA256'] = sha(canonical(intent))

    def write(self, relative, value):
        path = self.root / relative
        path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        # pathlib parents already created with private default umask here; enforce fixture privacy.
        cursor = path.parent
        while cursor != self.root:
            cursor.chmod(0o700); cursor = cursor.parent
        path.write_bytes(value if type(value) is bytes else canonical(value)); path.chmod(0o600)
        return path

    def intent_path(self, item=None):
        item = item or self.sources[0]
        return self.root / ('collection/private-originals/' + item['entry']['sourceContractSHA256'] + '/successor-intent.json')

    def admit(self, *args):
        self.admits.append(args)
        if self.deny:
            raise RefreshError('known-exact-source-alternate-cache')
        return {'metadataFilesRead': 1}

    def observe(self, source, *, absolute_deadline, sanitizer):
        self.calls.append(source['entry']['sourceKey'])
        headers = [('Content-Type', source['contract']['expectedResponse']['content-type']),
            ('Content-Length', '12'), ('Vary', 'Cookie')]
        return {'ok': True, 'requestAttempted': True,
            'observation': sanitizer(source, 200, headers, 512)}

    def run(self, observer=None, seconds=20):
        return d.execute_owner(deadline=time.monotonic() + seconds, observer=observer or self.observe)


class GuardTests(unittest.TestCase):
    def setUp(self):
        self.stack = ExitStack(); self.addCleanup(self.stack.close)
        for name in ('socket', 'create_connection', 'getaddrinfo'):
            self.stack.enter_context(patch.object(socket, name, side_effect=AssertionError('live network forbidden')))

    def test_inactive_blocks_before_any_local_or_network_access(self):
        with patch.object(d, 'ACTIVATION_SHA256', None), patch.object(d, 'load_bundle', side_effect=AssertionError):
            result = d.execute_owner(deadline=time.monotonic() + 1)
        self.assertEqual(result['code'], 'diagnostic-inactive')
        self.assertEqual(result['sourceAttemptsConsumed'], 0)
        d.validate_report(result)

    def test_exact_five_pass_and_second_run_cannot_dispatch(self):
        f = Fixture(self)
        before = {str(p.relative_to(f.root)): (p.read_bytes(), p.stat().st_ino, p.stat().st_mtime_ns)
            for p in (f.root / 'collection').rglob('*') if p.is_file()}
        result = f.run()
        self.assertEqual(result['status'], 'complete', result)
        self.assertEqual(len(f.calls), 5); self.assertEqual(len(f.admits), 15)
        self.assertEqual(result['sourceAttemptsConsumed'], 5)
        self.assertEqual(result['requestAttemptedCount'], 5)
        d.validate_report(result, sources=f.sources)
        for item in result['items']:
            self.assertTrue(item['observation']['headerFacts']['unsupportedVary'])
        after = {str(p.relative_to(f.root)): (p.read_bytes(), p.stat().st_ino, p.stat().st_mtime_ns)
            for p in (f.root / 'collection').rglob('*') if p.is_file()}
        self.assertEqual(before, after)
        ledger = f.root / 'head-observations'
        stored = ledger / (d.MANIFEST_SHA256 + '.result.json')
        self.assertEqual(sha(stored.read_bytes()), result['ledgerResultSHA256'])
        self.assertEqual(json.loads(stored.read_bytes())['ledgerResultSHA256'], None)
        self.assertEqual(f.run()['code'], 'diagnostic-already-attempted')
        self.assertEqual(len(f.calls), 5)

    def test_changed_latest_fetch_pointer_blocks_all(self):
        f = Fixture(self)
        f.write('collection/manual-results/latest-fetch.json', {'resultSHA256': 'a' * 64})
        self.assertEqual(f.run()['code'], 'diagnostic-pin-mismatch'); self.assertFalse(f.calls)

    def test_live_fetch_envelope_digest_must_match_exact_verified_report(self):
        f = Fixture(self)
        p = f.root / ('collection/manual-results/result-' + f.manifest['fetchResultSHA256'] + '.json')
        p.write_bytes(p.read_bytes() + b' ')
        self.assertEqual(f.run()['code'], 'diagnostic-pin-mismatch'); self.assertFalse(f.calls)

    def test_missing_prior_or_fresh_result_blocks_all(self):
        for which in ('priorDetailSHA256', 'freshFetchDetailSHA256'):
            with self.subTest(which=which):
                f = Fixture(self); e = f.sources[4]['entry']
                (f.root / ('collection/private-original-result-' + e[which] + '.json')).unlink()
                result = f.run(); self.assertEqual(result['status'], 'blocked'); self.assertFalse(f.calls)

    def test_mismatched_failed_intent_never_dispatches(self):
        f = Fixture(self); p = f.intent_path(); value = json.loads(p.read_bytes()); value['state'] = 'saving'
        f.write(p.relative_to(f.root), value)
        self.assertEqual(f.run()['code'], 'diagnostic-pin-mismatch'); self.assertFalse(f.calls)

    def test_pinned_but_wrong_intent_semantics_block(self):
        f = Fixture(self); p = f.intent_path(); value = json.loads(p.read_bytes()); value['ownerHandover']['handoffId'] += '-other'
        f.write(p.relative_to(f.root), value); f.sources[0]['entry']['expectedIntentSHA256'] = sha(canonical(value))
        self.assertEqual(f.run()['code'], 'diagnostic-intent-mismatch'); self.assertFalse(f.calls)

    def test_current_claim_denial_blocks_without_creating_ledger(self):
        f = Fixture(self); f.deny = True
        self.assertEqual(f.run()['code'], 'diagnostic-current-claims-blocked'); self.assertFalse(f.calls)
        self.assertFalse((f.root / 'head-observations').exists())

    def test_any_existing_custody_artifact_blocks(self):
        for name in ('original.csv', 'original.json', 'original.docx', 'original.pdf', 'original.partial', 'provenance.json', 'reservation.bin'):
            with self.subTest(name=name):
                f = Fixture(self); f.write(f.intent_path().parent.relative_to(f.root) / name, b'do not read body')
                self.assertEqual(f.run()['code'], 'diagnostic-custody-conflict'); self.assertFalse(f.calls)

    def test_existing_lease_contention_blocks_without_replacing_lock(self):
        f = Fixture(self); lock = f.root / 'collection/fixed-selection.lock'; before = lock.read_bytes()
        with lock.open('rb') as stream:
            fcntl.flock(stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
            self.assertEqual(f.run()['code'], 'diagnostic-lease-held'); self.assertFalse(f.calls)
        self.assertEqual(lock.read_bytes(), before)

    def test_lease_rechecks_current_collection_ancestor_not_detached_fd(self):
        f = Fixture(self)
        tree = d.SafeTree(f.root, f.manifest['ownerUID'])
        try:
            with self.assertRaisesRegex(ValueError, '^diagnostic-lease-changed$'):
                with tree.existing_lease() as check:
                    collection = f.root / 'collection'
                    collection.rename(f.root / 'old-collection')
                    f.write('collection/fixed-selection.lock', b'replacement lease')
                    check()
        finally:
            tree.close()
        self.assertFalse(f.calls)

    def test_missing_lock_does_not_create_replacement(self):
        f = Fixture(self); lock = f.root / 'collection/fixed-selection.lock'; lock.unlink()
        self.assertEqual(f.run()['status'], 'blocked'); self.assertFalse(lock.exists()); self.assertFalse(f.calls)

    def test_symlinked_intent_is_rejected(self):
        f = Fixture(self); p = f.intent_path(); other = p.with_name('renamed.json'); p.rename(other); p.symlink_to(other.name)
        self.assertEqual(f.run()['status'], 'blocked'); self.assertFalse(f.calls)

    def test_hardlinked_intent_is_rejected(self):
        f = Fixture(self); p = f.intent_path(); os.link(p, p.with_name('linked.json'))
        self.assertEqual(f.run()['code'], 'diagnostic-unsafe-metadata'); self.assertFalse(f.calls)

    def test_world_readable_intent_is_rejected(self):
        f = Fixture(self); f.intent_path().chmod(0o644)
        self.assertEqual(f.run()['code'], 'diagnostic-unsafe-metadata'); self.assertFalse(f.calls)

    def test_attempt_record_fsync_failure_consumes_pass_without_request(self):
        f = Fixture(self); (f.root / 'head-observations').mkdir(mode=0o700)
        with patch.object(d.os, 'fsync', side_effect=OSError('secret exception')):
            result = f.run()
        self.assertEqual(result['status'], 'incomplete-consumed'); self.assertFalse(f.calls)
        self.assertTrue((f.root / 'head-observations' / (d.MANIFEST_SHA256 + '.attempt.json')).exists())
        self.assertEqual(f.run()['code'], 'diagnostic-already-attempted'); self.assertFalse(f.calls)
        self.assertNotIn('secret', canonical(result).decode())

    def test_partial_crash_attempt_is_never_replaced(self):
        f = Fixture(self); f.write('head-observations/' + d.MANIFEST_SHA256 + '.attempt.json', b'{')
        self.assertEqual(f.run()['code'], 'diagnostic-already-attempted'); self.assertFalse(f.calls)

    def test_post_request_intent_race_stops_remaining_four(self):
        f = Fixture(self)
        def observer(*args, **kwargs):
            result = f.observe(*args, **kwargs)
            p = f.intent_path(); p.write_bytes(p.read_bytes() + b' ')
            return result
        result = f.run(observer)
        self.assertEqual(len(f.calls), 1); self.assertEqual(result['status'], 'incomplete-consumed')
        self.assertFalse(result['items']); self.assertFalse(result['sourceMetadataUnchanged'])
        self.assertNotEqual(result['code'], None)

    def test_post_request_lease_swap_stops_remaining_four(self):
        f = Fixture(self)
        def observer(*args, **kwargs):
            result = f.observe(*args, **kwargs)
            p = f.root / 'collection/fixed-selection.lock'; p.rename(p.with_suffix('.old'))
            f.write('collection/fixed-selection.lock', b'replaced')
            return result
        result = f.run(observer)
        self.assertEqual(result['code'], 'diagnostic-lease-changed'); self.assertEqual(len(f.calls), 1)

    def test_post_request_ledger_swap_stops_remaining_four(self):
        f = Fixture(self)
        def observer(*args, **kwargs):
            result = f.observe(*args, **kwargs)
            p = f.root / 'head-observations'; p.rename(p.with_name('renamed-ledger')); p.mkdir(mode=0o700)
            return result
        result = f.run(observer)
        self.assertEqual(result['code'], 'diagnostic-metadata-changed'); self.assertEqual(len(f.calls), 1)

    def test_transport_errors_and_unknown_attempts_use_closed_codes(self):
        f = Fixture(self)
        result = f.run(lambda *args, **kwargs: {'ok': False, 'requestAttempted': 'unknown', 'transport_error': 'head-worker-failed'})
        self.assertEqual(result['status'], 'complete-with-errors'); self.assertEqual(result['requestAttemptUnknownCount'], 5)
        d.validate_report(result, sources=f.sources)

    def test_raw_child_payload_is_rejected_before_parent_report(self):
        f = Fixture(self)
        def observer(*args, **kwargs):
            result = f.observe(*args, **kwargs); result['observation']['secretCookie'] = 'do-not-output'
            return result
        result = f.run(observer)
        self.assertEqual(result['code'], 'diagnostic-result-invalid'); self.assertNotIn('do-not-output', canonical(result).decode())
        self.assertEqual(len(f.calls), 1)

    def test_bool_integer_confusion_rejected(self):
        f = Fixture(self)
        result = f.run(lambda *a, **kw: {'ok': False, 'requestAttempted': 1, 'transport_error': 'head-worker-failed'})
        self.assertEqual(result['code'], 'diagnostic-result-invalid'); self.assertEqual(result['requestAttemptedCount'], 0)

    def test_expired_aggregate_deadline_blocks_before_any_request(self):
        f = Fixture(self); result = f.run(seconds=-1)
        self.assertEqual(result['code'], 'diagnostic-deadline'); self.assertFalse(f.calls)


class PinAndProjectionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.manifest, cls.sources, _, _ = d.load_bundle()

    def test_pinned_bundle_is_inactive_exact_five_with_unchanged_002(self):
        self.assertEqual(len(self.sources), 5); self.assertIsNone(d.ACTIVATION_SHA256)
        self.assertFalse(self.manifest['authority']['selected'])
        self.assertEqual(self.manifest['ownerHandover']['handoffId'], 'owner-local-comprehensive-20261018-002')
        self.assertEqual(self.manifest['fetchResultSHA256'], '2471124b16b770c9bbebee536a2b0bf4a809f5338c2ab523b58cbd97ba780816')
        self.assertEqual(self.manifest['bounds']['maximumRequests'], 5)

    def test_expected_intents_preserve_original_execution_diagnostic_pin(self):
        _, sources, selected, _ = d.load_bundle()
        inherited = selected['privateOriginalDownload']['diagnosticReportPin']['sha256']
        self.assertEqual(inherited, self.manifest['failedIntentDiagnosticReportSHA256'])
        self.assertEqual(inherited, '4be1b7b1703617e29a67e4cc7d4265452ef30d990101200679ac2a01eae96f4b')
        for source in sources:
            e = source['entry']
            expected = {'schemaVersion': 'offmenu-private-original-successor/1', 'sourceKey': e['sourceKey'],
                'url': source.exact_url, 'sourceContractSHA256': e['sourceContractSHA256'], 'predecessor': None,
                'diagnosticReportSHA256': inherited, 'owner': 1000, 'ownerHandover': self.manifest['ownerHandover'],
                'state': 'failed-no-retry', 'errorCode': e['priorErrorCode'], 'network': {'requests': 1, 'bodyBytesRead': 0},
                'privateSaveState': 'none', 'localBodyBytes': 0}
            self.assertEqual(sha(canonical(expected)), e['expectedIntentSHA256'])

    def test_inactive_selection_file_cannot_activate_by_merely_pinning_it(self):
        value=json.loads((d.ROOT / d.ACTIVATION_PATH).read_bytes());value['selected']=False;value['diagnosticLedgerWriteApproved']=False
        raw=canonical(value);digest=sha(raw)
        with patch.object(d,'repository_bytes',return_value=raw),patch.object(d, 'ACTIVATION_SHA256', digest), self.assertRaisesRegex(ValueError, '^diagnostic-inactive$'):
            d.activation(d.ROOT, self.manifest)

    def test_wrong_pin_and_symlink_repository_inputs_block(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); p = root / 'plain'; p.write_bytes(b'hello')
            with self.assertRaises(ValueError): d.repository_bytes(root, 'plain', 'a' * 64)
            link = root / 'link'; link.symlink_to('plain')
            with self.assertRaises(OSError): d.repository_bytes(root, 'link', sha(b'hello'))

    def test_public_host_signed_path_and_query_values_are_never_emitted(self):
        headers = [('Location', 'https://storage.googleapis.com/private-secret/path-signed-token?X-Goog-Signature=raw-signature&private-key-name=raw-query'),
            ('Set-Cookie', 'session=raw-cookie'), ('Set-Cookie', 'different=secret'), ('X-Secret-Header-Name', 'raw-header')]
        result = m.sanitize_response(self.sources[0], 302, headers, 1024)
        m.validate_observation(result, self.sources[0]); raw = canonical(result).decode()
        for secret in ('private-secret', 'path-signed-token', 'raw-signature', 'private-key-name', 'raw-query', 'raw-cookie', 'X-Secret-Header-Name', 'raw-header'):
            self.assertNotIn(secret, raw)
        redirect = result['headerFacts']['redirect']; self.assertEqual(redirect['publicHost'], 'storage.googleapis.com')
        self.assertEqual(redirect['queryNameCounts']['X-Goog-Signature'], 1)
        self.assertFalse(result['headerFacts']['duplicateNonignoredNames'])

    def test_unknown_hosts_and_query_keys_are_hashed(self):
        shape = m.redirect_shape(['https://private-host.example/hidden?unknown_key=value'], self.sources[0].exact_url)
        self.assertIsNone(shape['publicHost']); self.assertEqual(shape['unreviewedHostSHA256'], sha(b'private-host.example'))
        self.assertNotIn('unknown_key', canonical(shape).decode())

    def test_critical_duplicates_and_lengths_are_visible_without_values(self):
        headers = [('Content-Type', 'application/json'), ('Content-Length', '12'),
            ('Content-Length', '13'), ('X-Unknown', 'x' * 8193)]
        result = m.sanitize_response(self.sources[1], 200, headers, 8500)
        m.validate_observation(result, self.sources[1]); facts = result['headerFacts']
        self.assertEqual(facts['duplicateNonignoredNames'], ['content-length'])
        self.assertEqual(facts['oversizedNames'], ['sha256:' + sha(b'x-unknown')])
        self.assertEqual(facts['currentGETValidatorOnHEADHeaders'], 'invalid-response-headers')

    def test_access_rate_method_denials_remain_held(self):
        for status, code in ((403, 'head-access-denied-held'), (429, 'head-rate-limited-held'), (405, 'head-method-unsupported-held')):
            result = m.sanitize_response(self.sources[0], status, [], 32)
            m.validate_observation(result, self.sources[0]); self.assertEqual(result['code'], code)
            self.assertFalse(result['acquisitionEnabled']); self.assertTrue(result['sourceAccessAndRateHoldsPreserved'])

    def test_observation_schema_rejects_injected_strings_everywhere(self):
        result = m.sanitize_response(self.sources[0], 302, [('Location', 'https://data.humdata.org/public?id=x')], 128)
        for key, value in (('code', 'raw-secret'), ('method', 'GET'), ('httpStatus', True), ('sourceKey', 'other-source')):
            candidate = deepcopy(result); candidate[key] = value
            with self.subTest(key=key), self.assertRaises(ValueError): m.validate_observation(candidate, self.sources[0])
        candidate = deepcopy(result); candidate['headerFacts']['redirect']['publicHost'] = 'secret-host'
        with self.assertRaises(ValueError): m.validate_observation(candidate, self.sources[0])

    def test_report_boundary_rejects_raw_fields(self):
        report = d.report_template('diagnostic-inactive'); report['raw'] = 'secret'
        with self.assertRaises(ValueError): d.validate_report(report)


if __name__ == '__main__':
    unittest.main()
