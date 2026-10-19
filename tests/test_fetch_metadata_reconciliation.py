"""Offline tests: approved metadata inventories and synthetic local JSON only."""
from contextlib import ExitStack
from dataclasses import replace
import fcntl
import hashlib
import json
import os
from pathlib import Path
import signal
import socket
import tempfile
import time
from types import SimpleNamespace
import unittest
from unittest import mock

from offmenu.refresh import fetch_metadata_reconciliation as m

BASE = Path('/workspace/shared/offmenu-fetch-parse-split/composed')
REVIEW = Path('/workspace/shared/offmenu-fetch-closure-20261019T003600Z')


def read_reviewed_inventory():
    return m.build_inventory(
        closure_raw=(REVIEW / 'all-4753-fetch-closure-input.json').read_bytes(),
        runtime_manifest_raw=(BASE / 'docs/collection-selections/global-comprehensive-manifest.json').read_bytes(),
        owner_config_raw=(BASE / 'docs/collection-selections/owner-comprehensive-runtime.json').read_bytes(),
        owner_selection_raw=(BASE / 'docs/collection-selections/global-comprehensive-selection.json').read_bytes(),
        dispatch_hold_raw=(BASE / 'docs/operations/global-comprehensive-manual-handoff-20261018.json').read_bytes())


class MetadataTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.inventory = read_reviewed_inventory()
        cls.proposal = (REVIEW / 'owner-metadata-reconciliation-proposal.json').read_bytes()
        cls.asset = next(iter(cls.inventory.asset_ids - cls.inventory.held_asset_ids))
        cls.identity = next((h, n, ids) for h, n, ids in cls.inventory.identities
                            if not set(ids) & cls.inventory.held_asset_ids)

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.addCleanup(self.temp.cleanup)

    def target(self, value=None, raw=None):
        raw = raw if raw is not None else m.canonical(value)
        path = self.root / 'source.json'
        path.write_bytes(raw)
        return m.Target('synthetic', str(path), m._sha(raw), len(raw), True), raw

    def sanitize(self, value, *, inventory=None, objects=10000, nodes=500000, output=4*1024*1024):
        target, raw = self.target(value)
        return m._sanitize(raw, target, inventory or self.inventory, time.monotonic()+5, output, objects, nodes)

    def assert_code(self, code, function, *args):
        with self.assertRaises(m.MetadataError) as caught:
            function(*args)
        self.assertEqual(str(caught.exception), code)

    def fixture(self, value=None, *, raw=None):
        target, payload = self.target(value if value is not None else {'assetId': self.asset}, raw=raw)
        old = m._strict(self.proposal)
        candidate = dict(old['targets'][0])
        candidate.update(targetId=target.target_id, path=target.path,
            expectedMetadataSHA256=target.sha256, observedMetadataBytes=target.extent,
            proposedMaximumReadBytes=target.extent)
        native = next(x for x in old['targets'] if x['targetId'] == 'native-events')
        proposal = m.canonical({'targets': [candidate, native]})
        work = self.root / 'owner' / 'collection'
        work.mkdir(parents=True)
        os.chmod(work.parent, 0o700)
        os.chmod(work, 0o700)
        fd = os.open(work / 'fixed-selection.lock', os.O_CREAT | os.O_RDWR, 0o600)
        fcntl.flock(fd, fcntl.LOCK_EX)
        self.addCleanup(os.close, fd)
        config = m._strict(self.inventory.config)
        runtime = SimpleNamespace(uid=os.getuid(), root=work.parent,
            native=config['nativeClaimsRoot'], runner_work='/srv/offmenu-refresh/outputs/collection',
            runner_cache='/srv/offmenu-refresh/cache', config=config,
            selected=m._strict(self.inventory.selection), provenance=lambda: {
                'handoffId': m.HANDOFF_ID, 'runtimeConfigSHA256': m.INVENTORY_PINS['owner_config_raw'][0],
                'dispatchHoldSHA256': m.INVENTORY_PINS['dispatch_hold_raw'][0],
                'executionContext': 'owner-manual-foo', 'runnerResumeRequiresOutcomeImport': True})
        selection = {'schemaVersion': m.SELECTION_SCHEMA, 'proposalSHA256': m._sha(proposal),
            'readerSHA256': m._sha(Path(m.__file__).read_bytes()), 'handoffId': m.HANDOFF_ID,
            'ownerConfigSHA256': m.INVENTORY_PINS['owner_config_raw'][0],
            'targets': [target.binding()], 'withheldTargetIds': [], 'clearanceEvidenceSHA256': 'a'*64}
        deadline = time.monotonic()+5
        def clearance(binding):
            return {'schemaVersion': m.CLEARANCE_SCHEMA, 'target': binding,
                'evidenceSHA256': 'a'*64, 'checkedMonotonic': time.monotonic(),
                'expiresMonotonic': deadline, 'decision': 'clear'}
        patches = ExitStack()
        for key, value in {'PROPOSAL_SHA256': m._sha(proposal), 'TARGET_COUNT': 2,
            'CANDIDATE_COUNT': 1, 'MAX_READ': target.extent,
            'OWNER_ROOT': str(work.parent), 'EXPECTED_UID': os.getuid()}.items():
            patches.enter_context(mock.patch.object(m, key, value))
        self.addCleanup(patches.close)
        kwargs = dict(parent_selection=selection, inventory=self.inventory, owner_runtime=runtime,
            lease_fd=fd, current_read_holds=clearance, absolute_deadline=deadline)
        return target, proposal, kwargs

    def test_exact_reviewed_93_92_and_caps(self):
        targets = m.inspect_proposal(self.proposal)
        self.assertEqual(len(targets), 93)
        self.assertEqual(sum(t.candidate for t in targets), 92)
        self.assertEqual(sum(t.extent for t in targets if t.candidate), 16493475)
        self.assertEqual(max(t.extent for t in targets if t.candidate), 14588360)
        self.assertEqual([t.target_id for t in targets if not t.candidate], ['native-events'])

    def test_inactive_has_93_outcomes_and_no_filesystem_or_network(self):
        with mock.patch.object(os, 'open', side_effect=AssertionError('unexpected filesystem access')), \
             mock.patch.object(socket, 'socket', side_effect=AssertionError('unexpected network')):
            report = m.reconcile_metadata(self.proposal)
        self.assertEqual(len(report['outcomes']), 93)
        self.assertEqual(report['metadataBytesRead'], 0)
        self.assertEqual(report['status'], 'inactive')
        self.assertEqual(report['outcomes'][next(i for i,t in enumerate(m.inspect_proposal(self.proposal)) if t.target_id=='native-events')]['code'], 'unselected')

    def test_pin_rejects_mutation(self):
        self.assert_code('selection-mismatch', m.inspect_proposal, self.proposal+b' ')

    def test_inventory_pins_reject_mutation(self):
        with self.assertRaisesRegex(m.MetadataError, 'inventory-mismatch'):
            m.build_inventory(closure_raw=b'{}', runtime_manifest_raw=b'', owner_config_raw=b'',
                              owner_selection_raw=b'', dispatch_hold_raw=b'')

    def test_same_object_exact_identity_and_pointer(self):
        digest, size, ids = self.identity
        data = {'records': [{'originalSHA256': digest, 'originalBytes': size,
                            'originalPath': '/home/user/src/offmenu-data/originals/a/original.pdf'}]}
        row = self.sanitize(data)['rows'][0]
        self.assertEqual(row['sourceObjectJSONPointer'], '/records/0')
        self.assertEqual(row['payloadIdentityProposal']['existingAssetIds'], list(ids))
        self.assertEqual(row['custodyStatus'], 'unresolved')
        self.assertFalse(row['usableOriginal'])
        self.assertFalse(row['countryTypeComplete'])
        self.assertEqual(row['originalPath'], data['records'][0]['originalPath'])

    def test_no_sibling_or_parent_child_join(self):
        digest, size, _ = self.identity
        result = self.sanitize({'records': [{'originalSHA256': digest}, {'originalBytes': size}]})
        self.assertEqual(result['rows'], [])
        result = self.sanitize({'originalSHA256': digest, 'record': {'originalBytes': size}})
        self.assertEqual(result['rows'], [])

    def test_unknown_identity_not_promoted_and_hash_extent_retained(self):
        rows = self.sanitize({'assetId': self.asset, 'originalSHA256': 'f'*64, 'originalBytes': 9})['rows']
        self.assertEqual(rows[0]['payloadIdentityProposal']['existingAssetIds'], [])
        self.assertEqual(rows[0]['payloadIdentityProposal']['bytes'], 9)
        self.assertEqual(rows[0]['custodyStatus'], 'unresolved')

    def test_unknown_ids_not_emitted(self):
        self.assertEqual(self.sanitize({'assetId': 'new-secret-id', 'country': 'XX'})['rows'], [])

    def test_secrets_headers_text_urls_and_classifications(self):
        inventory = replace(self.inventory, origins=frozenset({'https://example.test'}))
        value = {'assetId': self.asset, 'title': 'SECRET-TITLE', 'purpose': 'SECRET-PURPOSE',
            'release': 'SECRET-RELEASE', 'headers': {'Authorization': 'Bearer SECRET-HEADER'},
            'cookies': 'SECRET-COOKIE', 'body': 'SECRET-BODY', 'requestBody': 'SECRET-REQUEST',
            'url': 'https://example.test/SECRET-PATH/file?token=SECRET-TOKEN&SECRET-KEY=SECRET-VALUE&id=SECRET-ID'}
        result = self.sanitize(value, inventory=inventory)
        encoded = m.canonical(result)
        self.assertNotIn(b'SECRET', encoded)
        url = result['rows'][0]['urls']['url']
        self.assertEqual(url['queryKeys'], ['id', 'token'])
        self.assertTrue(url['unknownQueryKeysWithheld'])
        self.assertEqual(url['pathShape'], '/{segment}/{segment}')
        self.assertEqual(url['exactURLSHA256'], m._sha(value['url'].encode()))
        self.assertEqual(result['rows'][0]['classifications']['purpose']['classification'], 'unresolved')

    def test_credential_url_and_unknown_origin_omitted(self):
        inventory = replace(self.inventory, origins=frozenset({'https://example.test'}))
        for url in ['https://user:password@example.test/x', 'https://unreviewed.test/x',
                    'https://example.test/x#SECRET']:
            self.assertEqual(self.sanitize({'assetId': self.asset, 'url': url}, inventory=inventory)['rows'][0]['urls'], {})

    def test_secret_pointer_is_not_published(self):
        self.assertEqual(self.sanitize({'SECRET-KEY': {'assetId': self.asset}})['rows'], [])

    def test_nested_restrictions_exclude_without_sibling_leak(self):
        for restriction in [{'noRead': True}, {'permissions': {'read': False}},
                            {'privacy': 'private'}, {'minors': True}, {'holds': ['unknown-hold']},
                            {'sourceRestrictions': {'effectiveReadHolds': ['no-read']}}]:
            value = {'records': [dict(assetId=self.asset, details=restriction), {'assetId': self.asset}]}
            rows = self.sanitize(value)['rows']
            self.assertEqual([x['sourceObjectJSONPointer'] for x in rows], ['/records/1'])

    def test_ancestor_restriction_cannot_be_shed(self):
        self.assertEqual(self.sanitize({'noRead': True, 'records': [{'assetId': self.asset}]})['rows'], [])

    def test_known_held_asset_not_published(self):
        held = next(iter(self.inventory.held_asset_ids))
        self.assertEqual(self.sanitize({'assetId': held})['rows'], [])

    def test_path_never_opened_and_unsafe_paths_suppressed(self):
        digest, size, _ = self.identity
        for path in ['/etc/passwd', '/home/user/src/offmenu-data/originals/../secret',
                     '/home/user/src/offmenu-data/originals/secret-token',
                     '/home/user/src/offmenu-data/originals/file?token=foo']:
            self.assertIsNone(self.sanitize({'originalSHA256': digest, 'originalBytes': size, 'originalPath': path})['rows'][0]['originalPath'])

    def test_duplicate_key_and_nonfinite_rejected(self):
        for raw, code in [(b'{"assetId":"a","assetId":"b"}', 'duplicate-json-key'),
                          (b'{"x":NaN}', 'invalid-json'), (b'{"x":Infinity}', 'invalid-json')]:
            self.assert_code(code, m._strict, raw)

    def test_depth_node_object_and_output_limits(self):
        self.assert_code('depth-limit', m._lexical_bounds, b'['*65+b'0'+b']'*65, time.monotonic()+5)
        self.assert_code('node-limit', m._lexical_bounds, b'[1,2,3,4,5]', time.monotonic()+5, 3)
        with self.assertRaisesRegex(m.MetadataError, 'object-limit'):
            self.sanitize({'records': [{'assetId': self.asset}, {'assetId': self.asset}]}, objects=1)
        with self.assertRaisesRegex(m.MetadataError, 'output-limit'):
            self.sanitize({'assetId': self.asset}, output=10)

    def test_braces_inside_strings_do_not_count_as_depth(self):
        self.assertEqual(self.sanitize({'assetId': self.asset, 'body': '['*1000})['rows'][0]['identifiers']['assetId'], self.asset)

    def test_exact_reader_and_changed_extent_or_hash(self):
        target, raw = self.target({'assetId': self.asset})
        self.assertEqual(m._read_target(target, time.monotonic()+5, [0]), raw)
        Path(target.path).write_bytes(raw+b' ')
        self.assert_code('extent-mismatch', m._read_target, target, time.monotonic()+5, [0])
        Path(target.path).write_bytes(b' '*len(raw))
        self.assert_code('digest-mismatch', m._read_target, target, time.monotonic()+5, [0])

    def test_symlink_final_and_ancestor_rejected(self):
        target, raw = self.target({'assetId': self.asset})
        path = Path(target.path)
        saved = path.with_name('saved.json')
        path.rename(saved)
        path.symlink_to(saved)
        with self.assertRaises(OSError):
            m._read_target(target, time.monotonic()+5, [0])
        alias = self.root / 'alias'
        alias.symlink_to(self.root, target_is_directory=True)
        with self.assertRaises(OSError):
            m._read_target(replace(target, path=str(alias/'saved.json')), time.monotonic()+5, [0])

    def test_fifo_does_not_block(self):
        target, raw = self.target({'assetId': self.asset})
        Path(target.path).unlink()
        os.mkfifo(target.path)
        start = time.monotonic()
        self.assert_code('not-regular', m._read_target, target, start+1, [0])
        self.assertLess(time.monotonic()-start, .5)

    def test_renamed_parent_even_same_file_inode_rejected(self):
        parent = self.root / 'folder'
        parent.mkdir()
        raw = m.canonical({'assetId': self.asset})
        path = parent / 'source.json'
        path.write_bytes(raw)
        target = m.Target('t', str(path), m._sha(raw), len(raw), True)
        real_read = os.read
        replaced = []
        def read(fd, count):
            data = real_read(fd, count)
            if not replaced:
                old = self.root / 'old'
                parent.rename(old)
                parent.mkdir()
                os.link(old/'source.json', path)
                replaced.append(True)
            return data
        with mock.patch.object(os, 'read', read):
            self.assert_code('path-changed', m._read_target, target, time.monotonic()+5, [0])

    def test_live_lease_required_and_same_description_proven(self):
        target, proposal, kwargs = self.fixture()
        report = m.reconcile_metadata(proposal, **kwargs)
        self.assertEqual(report['status'], 'metadata-proposals-only', report)
        self.assertEqual(report['metadataBytesRead'], target.extent)
        self.assertEqual(report['uncertainReadBytesUpperBound'], 0)
        self.assertEqual(report['recoveredObjectCount'], 1)
        independent = os.open(self.root/'owner/collection/fixed-selection.lock', os.O_RDWR)
        self.addCleanup(os.close, independent)
        kwargs['lease_fd'] = independent
        self.assertEqual(m.reconcile_metadata(proposal, **kwargs)['errorCode'], 'lease-unverified')

    def test_unlocked_descriptor_and_owner_mismatch_zero_read(self):
        _, proposal, kwargs = self.fixture()
        fcntl.flock(kwargs['lease_fd'], fcntl.LOCK_UN)
        report = m.reconcile_metadata(proposal, **kwargs)
        self.assertEqual(report['errorCode'], 'lease-unverified')
        self.assertEqual(report['metadataBytesRead'], 0)
        kwargs['owner_runtime'].uid = os.getuid()+1
        self.assertEqual(m.reconcile_metadata(proposal, **kwargs)['errorCode'], 'owner-context-mismatch')

    def test_source_hold_zero_target_read(self):
        _, proposal, kwargs = self.fixture()
        prior = kwargs['current_read_holds']
        kwargs['current_read_holds'] = lambda binding: dict(prior(binding), decision='held')
        with mock.patch.object(m, '_isolated', side_effect=AssertionError('held target read')):
            report = m.reconcile_metadata(proposal, **kwargs)
        self.assertEqual(report['outcomes'][0]['code'], 'read-held')
        self.assertEqual(report['outcomes'][0]['readBytesUpperBound'], 0)

    def test_post_read_hold_discards_rows(self):
        _, proposal, kwargs = self.fixture()
        prior = kwargs['current_read_holds']
        calls = []
        def clearance(binding):
            calls.append(True)
            return dict(prior(binding), decision='clear' if len(calls)==1 else 'held')
        kwargs['current_read_holds'] = clearance
        report = m.reconcile_metadata(proposal, **kwargs)
        self.assertEqual(report['outcomes'][0]['code'], 'read-held')
        self.assertEqual(report['rows'], [])

    def test_missing_inaccessible_outcomes_no_raw_exception(self):
        target, proposal, kwargs = self.fixture()
        Path(target.path).unlink()
        report = m.reconcile_metadata(proposal, **kwargs)
        self.assertEqual(report['outcomes'][0]['code'], 'missing')
        self.assertEqual(report['outcomes'][0]['bytesRead'], 0)
        with mock.patch.object(m, '_read_target', side_effect=PermissionError('SECRET-EXCEPTION')):
            report = m.reconcile_metadata(proposal, **kwargs)
        self.assertEqual(report['outcomes'][0]['code'], 'inaccessible')
        self.assertNotIn(b'SECRET', m.canonical(report))

    def test_duplicate_selection_and_jsonl_not_selectable(self):
        _, proposal, kwargs = self.fixture()
        kwargs['parent_selection']['targets'] *= 2
        self.assertEqual(m.reconcile_metadata(proposal, **kwargs)['errorCode'], 'selection-mismatch')
        native = m.inspect_proposal(proposal)[1]
        kwargs['parent_selection']['targets'] = [native.binding()]
        self.assertEqual(m.reconcile_metadata(proposal, **kwargs)['errorCode'], 'selection-mismatch')

    def test_withheld_complete_accounting(self):
        target, proposal, kwargs = self.fixture()
        kwargs['parent_selection']['targets'] = []
        kwargs['parent_selection']['withheldTargetIds'] = [target.target_id]
        report = m.reconcile_metadata(proposal, **kwargs)
        self.assertEqual([o['code'] for o in report['outcomes']], ['withheld', 'unselected'])
        self.assertEqual(report['metadataBytesRead'], 0)

    def test_changed_selection_extent_zero_read(self):
        _, proposal, kwargs = self.fixture()
        kwargs['parent_selection']['targets'][0]['metadataBytes'] += 1
        report = m.reconcile_metadata(proposal, **kwargs)
        self.assertEqual(report['errorCode'], 'selection-mismatch')
        self.assertEqual(report['metadataBytesRead'], 0)

    def test_deadline_blocked_read_bounded_and_lease_survives(self):
        target, proposal, kwargs = self.fixture()
        deadline = time.monotonic()+.15
        kwargs['absolute_deadline'] = deadline
        prior = kwargs['current_read_holds']
        kwargs['current_read_holds'] = lambda binding: dict(prior(binding), expiresMonotonic=deadline)
        def blocked(*args):
            time.sleep(5)
        start = time.monotonic()
        with mock.patch.object(m, '_read_target', blocked):
            report = m.reconcile_metadata(proposal, **kwargs)
        self.assertLess(time.monotonic()-start, 1)
        self.assertEqual(report['errorCode'], 'deadline')
        self.assertEqual(report['uncertainReadBytesUpperBound'], target.extent)
        self.assertEqual(report['rows'], [])
        work = os.open(self.root/'owner/collection', os.O_RDONLY|os.O_DIRECTORY)
        try:
            m._verify_lease(kwargs['lease_fd'], work)
        finally:
            os.close(work)

    def test_blocked_clearance_callback_bounded_zero_read(self):
        _, proposal, kwargs = self.fixture()
        kwargs['absolute_deadline'] = time.monotonic()+.1
        kwargs['current_read_holds'] = lambda binding: time.sleep(5)
        start = time.monotonic()
        report = m.reconcile_metadata(proposal, **kwargs)
        self.assertLess(time.monotonic()-start, 1)
        self.assertEqual(report['errorCode'], 'deadline')
        self.assertEqual(report['metadataBytesRead'], 0)

    def test_six_fao_existing_exact_identity_only(self):
        raw = (REVIEW/'six-fao-reported-custody-supplement-v2.json').read_bytes()
        self.assertEqual(m._sha(raw), '5d6fa920a3b64cccbbca5dbaf417ce29df466539b003f417e313fd52b80c1bb4')
        records = m._strict(raw)['records']
        synthetic = [{'originalSHA256': x['reportedOriginalIdentity']['sha256'],
                      'originalBytes': x['reportedOriginalIdentity']['bytes']} for x in records]
        rows = self.sanitize({'records': synthetic})['rows']
        self.assertEqual(len(rows), 6)
        for source, row in zip(records, rows):
            self.assertIn(source['currentAssetId'], row['payloadIdentityProposal']['existingAssetIds'])
            self.assertIn(source['currentAssetId'], self.inventory.asset_ids)
            self.assertEqual(row['custodyStatus'], 'unresolved')
            self.assertFalse(row['usableOriginal'])
        self.assertEqual(sum(x['reportedOriginalIdentity']['bytes'] for x in records), 16524612)

    def test_no_network_even_active(self):
        _, proposal, kwargs = self.fixture()
        with mock.patch.object(socket, 'socket', side_effect=AssertionError('network not permitted')):
            report = m.reconcile_metadata(proposal, **kwargs)
        self.assertEqual(report['recoveredObjectCount'], 1)
        self.assertEqual(report['networkRequests'], 0)
        self.assertEqual(report['originalsOpened'], 0)


    def test_closed_report_rejects_injected_fields_urls_ids_and_counters(self):
        _, proposal, kwargs = self.fixture()
        report = m.reconcile_metadata(proposal, **kwargs)
        validate = lambda value: m.sanitize_report(value, proposal, inventory=self.inventory,
                                                    parent_selection=kwargs['parent_selection'])
        self.assertIs(validate(report), report)
        mutations = [
            lambda r: r.update(rawException='SECRET'),
            lambda r: r.update(metadataBytesRead=r['metadataBytesRead']+1),
            lambda r: r['outcomes'].pop(),
            lambda r: r['outcomes'][0].update(metadataSHA256='0'*64),
            lambda r: r['rows'][0].update(sourceUrl='https://example.test/?token=SECRET'),
            lambda r: r['rows'][0]['identifiers'].update(assetId='new-asset'),
            lambda r: r['rows'][0].update(sourceObjectJSONPointer='/SECRET'),
            lambda r: r['rows'][0].update(usableOriginal=True),
            lambda r: r['rows'][0].update(custodyStatus='absent'),
            lambda r: r['rows'].append(dict(r['rows'][0])),
            lambda r: r.update(parentSelectionSHA256='0'*64),
            lambda r: r['rows'][0].update(originalPath='/etc/passwd'),
        ]
        for mutate in mutations:
            value = json.loads(json.dumps(report))
            mutate(value)
            with self.assertRaisesRegex(ValueError, 'invalid-metadata-report'):
                validate(value)

    def test_current_read_clearance_wrong_binding_or_stale_rejected(self):
        target, proposal, kwargs = self.fixture()
        prior = kwargs['current_read_holds']
        for change in [{'evidenceSHA256': 'b'*64}, {'target': dict(target.binding(), metadataBytes=1)},
                       {'checkedMonotonic': time.monotonic()-10}, {'decision': True}]:
            kwargs['current_read_holds'] = lambda binding, c=change: dict(prior(binding), **c)
            report = m.reconcile_metadata(proposal, **kwargs)
            self.assertEqual(report['outcomes'][0]['code'], 'clearance-unavailable')
            self.assertEqual(report['metadataBytesRead'], 0)

    def test_exact_all_93_outcomes_for_owner_blocker(self):
        with mock.patch.object(m, '_selection', return_value=(frozenset(), frozenset())):
            report = m.reconcile_metadata(self.proposal, parent_selection={}, inventory=self.inventory,
                                          absolute_deadline=time.monotonic()+1)
        self.assertEqual(report['errorCode'], 'owner-context-mismatch')
        self.assertEqual(len(report['outcomes']), 93)
        self.assertEqual(report['metadataBytesRead'], 0)

    def test_root_read_false_is_restriction(self):
        self.assertEqual(self.sanitize({'read': False, 'records': [{'assetId': self.asset}]})['rows'], [])

    def test_numeric_object_keys_are_not_array_pointers(self):
        result = self.sanitize({'12345678': {'assetId': self.asset}})
        self.assertEqual(result['rows'], [])
        self.assertEqual(result['unresolvedObjects'], 1)

    def test_url_only_evidence_remains_unresolved(self):
        result = self.sanitize({'records': [{'url': 'https://example.test/file'}]})
        self.assertEqual(result['rows'], [])
        self.assertEqual(result['unresolvedObjects'], 1)

    def test_explicit_unknown_held_object_counted_without_emission(self):
        result = self.sanitize({'assetId': 'unknown', 'privacy': 'private'})
        self.assertEqual(result['rows'], [])
        self.assertEqual(result['excludedObjects'], 1)

    def test_parse_failures_account_for_visited_nodes(self):
        target, raw = self.target(raw=b'{"x": 1, "x": 2}')
        result = m._worker(target, self.inventory, time.monotonic()+1, 100000, 100, 100)
        self.assertEqual(result['code'], 'duplicate-json-key')
        self.assertGreater(result['visitedNodes'], 0)
        self.assertEqual(result['bytesRead'], len(raw))


    def two_target_fixture(self, *, raw=None):
        target, proposal, kwargs = self.fixture(raw=raw)
        document = m._strict(proposal)
        second = dict(document['targets'][0], targetId='synthetic-2', path=str(self.root/'second.json'))
        Path(second['path']).write_bytes(Path(target.path).read_bytes())
        document['targets'].insert(1, second)
        proposal = m.canonical(document)
        kwargs['parent_selection']['proposalSHA256'] = m._sha(proposal)
        kwargs['parent_selection']['targets'].append(dict(target.binding(), targetId='synthetic-2', path=second['path']))
        patch = mock.patch.multiple(m, PROPOSAL_SHA256=m._sha(proposal), TARGET_COUNT=3,
                                    CANDIDATE_COUNT=2, MAX_READ=target.extent*2)
        patch.start()
        self.addCleanup(patch.stop)
        return target, proposal, kwargs

    def post_read_gate(self, kwargs, decision):
        prior = kwargs['current_read_holds']
        calls = {}
        def gate(binding):
            key = binding['targetId']
            calls[key] = calls.get(key, 0)+1
            value = prior(binding)
            if key == 'synthetic' and calls[key] == 2:
                if decision == 'exception':
                    raise RuntimeError('private callback failure')
                value['decision'] = decision
            return value
        kwargs['current_read_holds'] = gate
        return calls

    def test_cap_four_charged_before_held_unknown_or_failing_postcheck(self):
        target, proposal, kwargs = self.two_target_fixture()
        original = kwargs['current_read_holds']
        for decision in ('held', 'unknown', 'exception'):
            kwargs['current_read_holds'] = original
            calls = self.post_read_gate(kwargs, decision)
            with mock.patch.object(m, 'MAX_NODES', 4):
                report = m.reconcile_metadata(proposal, **kwargs)
            self.assertEqual(report['visitedNodes'], 4)
            self.assertEqual([o['visitedNodes'] for o in report['outcomes']], [3, 1, 0])
            self.assertEqual(report['errorCode'], 'node-limit')
            self.assertEqual(report['outcomes'][1]['code'], 'node-limit')
            self.assertEqual(report['outcomes'][0]['code'], 'clearance-unavailable' if decision=='exception' else 'read-held')
            self.assertEqual(calls, {'synthetic': 2, 'synthetic-2': 1})
            self.assertEqual(report['rows'], [])
            self.assertEqual(report['metadataBytesRead'], target.extent*2)
            self.assertEqual(report['sanitizedObjectsProduced'], 1)

    def test_cap_four_parse_failure_still_consumes_nodes_before_postcheck(self):
        target, proposal, kwargs = self.two_target_fixture(raw=b'{"x":NaN}')
        calls = self.post_read_gate(kwargs, 'held')
        with mock.patch.object(m, 'MAX_NODES', 4):
            report = m.reconcile_metadata(proposal, **kwargs)
        self.assertEqual(report['visitedNodes'], 4)
        self.assertEqual(report['errorCode'], 'node-limit')
        self.assertEqual(report['sanitizedObjectsProduced'], 0)
        self.assertEqual(calls, {'synthetic': 2, 'synthetic-2': 1})
        self.assertEqual(report['metadataBytesRead'], target.extent*2)

    def test_node_limit_cannot_be_masked_by_post_read_hold(self):
        _, proposal, kwargs = self.fixture()
        calls = self.post_read_gate(kwargs, 'held')
        with mock.patch.object(m, 'MAX_NODES', 2):
            report = m.reconcile_metadata(proposal, **kwargs)
        self.assertEqual(report['errorCode'], 'node-limit')
        self.assertEqual(report['visitedNodes'], 2)
        self.assertEqual(calls, {'synthetic': 1})

    def test_object_limit_cannot_be_masked_by_post_read_hold(self):
        _, proposal, kwargs = self.fixture({'records': [{'assetId': self.asset}, {'assetId': self.asset}]})
        calls = self.post_read_gate(kwargs, 'held')
        with mock.patch.object(m, 'MAX_OBJECTS', 1):
            report = m.reconcile_metadata(proposal, **kwargs)
        self.assertEqual(report['errorCode'], 'object-limit')
        self.assertEqual(report['sanitizedObjectsProduced'], 1)
        self.assertGreater(report['sanitizedRowBytesProduced'], 0)
        self.assertEqual(report['recoveredObjectCount'], 0)
        self.assertEqual(calls, {'synthetic': 1})

    def test_output_limit_cannot_be_masked_by_post_read_hold(self):
        _, proposal, kwargs = self.fixture()
        calls = self.post_read_gate(kwargs, 'held')
        with mock.patch.object(m, 'MAX_OUTPUT', m.REPORT_RESERVE+1):
            report = m.reconcile_metadata(proposal, **kwargs)
        self.assertEqual(report['errorCode'], 'output-limit')
        self.assertEqual(report['visitedNodes'], 3)
        self.assertEqual(calls, {'synthetic': 1})

    def test_post_read_timeout_preserves_worker_counters_and_stops_next_target(self):
        target, proposal, kwargs = self.two_target_fixture()
        prior = kwargs['current_read_holds']
        calls = {}
        def gate(binding):
            key = binding['targetId']
            calls[key] = calls.get(key, 0)+1
            if key == 'synthetic' and calls[key] == 2:
                time.sleep(5)
            return prior(binding)
        kwargs['current_read_holds'] = gate
        kwargs['absolute_deadline'] = time.monotonic()+.2
        start = time.monotonic()
        report = m.reconcile_metadata(proposal, **kwargs)
        self.assertLess(time.monotonic()-start, 1)
        self.assertEqual(report['errorCode'], 'deadline')
        self.assertEqual(report['visitedNodes'], 3)
        self.assertEqual(report['sanitizedObjectsProduced'], 1)
        self.assertGreater(report['sanitizedRowBytesProduced'], 0)
        self.assertEqual(report['metadataBytesRead'], target.extent)
        self.assertEqual(report['outcomes'][1]['readBytesUpperBound'], 0)
        self.assertEqual(report['rows'], [])
        self.assertEqual(calls, {'synthetic': 2})

    def test_suppressed_rows_do_not_reset_cumulative_object_budget(self):
        _, proposal, kwargs = self.two_target_fixture()
        calls = self.post_read_gate(kwargs, 'held')
        with mock.patch.object(m, 'MAX_OBJECTS', 1):
            report = m.reconcile_metadata(proposal, **kwargs)
        self.assertEqual(report['errorCode'], 'object-limit')
        self.assertEqual(report['sanitizedObjectsProduced'], 1)
        self.assertEqual(report['outcomes'][1]['sanitizedObjectsProduced'], 0)
        self.assertEqual(report['rows'], [])
        self.assertEqual(calls, {'synthetic': 2, 'synthetic-2': 1})

    def test_suppressed_rows_do_not_reset_cumulative_output_budget(self):
        target, proposal, kwargs = self.two_target_fixture()
        first = m._worker(target, self.inventory, time.monotonic()+2, m.MAX_OUTPUT, m.MAX_OBJECTS, m.MAX_NODES)
        first_bytes = first['sanitizedRowBytesProduced']
        calls = self.post_read_gate(kwargs, 'unknown')
        with mock.patch.object(m, 'MAX_OUTPUT', m.REPORT_RESERVE+first_bytes+10):
            report = m.reconcile_metadata(proposal, **kwargs)
        self.assertEqual(report['errorCode'], 'output-limit')
        self.assertEqual(report['sanitizedRowBytesProduced'], first_bytes)
        self.assertEqual(report['sanitizedObjectsProduced'], 1)
        self.assertEqual(report['rows'], [])
        self.assertEqual(calls, {'synthetic': 2, 'synthetic-2': 1})

    def test_publisher_rejects_consumption_counter_tampering(self):
        _, proposal, kwargs = self.fixture()
        report = m.reconcile_metadata(proposal, **kwargs)
        for key in ('visitedNodes', 'sanitizedObjectsProduced', 'sanitizedRowBytesProduced'):
            tampered = json.loads(json.dumps(report))
            tampered[key] += 1
            with self.assertRaisesRegex(ValueError, 'invalid-metadata-report'):
                m.sanitize_report(tampered, proposal, inventory=self.inventory,
                                  parent_selection=kwargs['parent_selection'])

    def test_depth_failure_preserves_reserved_node_consumption(self):
        raw = b'['*65+b'0'+b']'*65
        target, _ = self.target(raw=raw)
        result = m._worker(target, self.inventory, time.monotonic()+1, 100000, 100, 100)
        self.assertEqual(result['code'], 'depth-limit')
        self.assertEqual(result['visitedNodes'], 65)

    def test_lexical_budget_is_reserved_before_next_token(self):
        progress = [0]
        with self.assertRaisesRegex(m.MetadataError, 'node-limit'):
            m._lexical_bounds(b'[1,2,3]', time.monotonic()+1, 2, progress)
        self.assertEqual(progress[0], 2)


if __name__ == '__main__':
    unittest.main()
