"""Acquisition orchestration tests; no live network or country acceptance."""
from dataclasses import asdict, replace
from datetime import timedelta
import json
from pathlib import Path
import tempfile
import unittest
import subprocess
import sys
from unittest.mock import Mock, patch

from offmenu.refresh.acquisition import collect_registry
from offmenu.refresh.core import RefreshError, canonical, sha
from test_refresh_acquisition import SPEC, NOW, Response, Transport


class CollectionRunnerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.evidence = self.root / 'review.json'
        self.evidence.write_bytes(b'{"fixtureReview":true}')
        self.pin = {'path': str(self.evidence), 'sha256': sha(self.evidence.read_bytes())}
        self.registry = {
            'schemaVersion': 'offmenu-acquisition-selection/1',
            'resources': {'storageRoot': str(self.root / 'cache'), 'maxTransferBytes': 1024,
                          'minimumFreeBytes': 0, 'maxSeconds': 30},
            'sources': [self.entry(SPEC)],
            'bindings': [self.binding(SPEC.source_key, 'AU', 'foods'),
                         self.binding(SPEC.source_key, 'BE', 'foods'),
                         self.binding(SPEC.source_key, 'AU', 'nutrients')],
            'evidence': [self.pin]}

    def tearDown(self):
        self.temp.cleanup()

    def entry(self, spec):
        return {'spec': asdict(spec), 'operation': 'https-refresh', 'retained': None,
                'claim': {'owner': 0, 'state': 'selected', 'evidence': self.pin}, 'holds': []}

    def binding(self, key, country, kind):
        return {'sourceKey': key, 'country': country, 'type': kind, 'evidence': self.pin}

    def run_batch(self, transport, now=NOW):
        path = self.root / 'registry.json'
        path.write_bytes(canonical(self.registry))
        return collect_registry(path, sha(path.read_bytes()), self.root / 'reports',
                                transport=transport, now=now)

    def retained(self):
        body = self.root / 'original.csv'
        body.write_bytes(b'original untouched bytes\n')
        self.registry['sources'][0].update(operation='retained-copy', retained={
            'path': str(body), 'sha256': sha(body.read_bytes()), 'bytes': body.stat().st_size,
            'originalAcquiredAt': NOW.isoformat(), 'headers': {'etag': 'validator-not-checksum'},
            'evidence': self.pin})
        return body

    def test_many_to_many_once_then_repeat_zero_network(self):
        t = Transport(Response())
        first = self.run_batch(t)
        second = self.run_batch(t, NOW + timedelta(days=29))
        self.assertEqual(len(t.calls), 1)
        self.assertEqual(first['network'], {'requests': 1, 'bodyBytesRead': 7})
        self.assertEqual(second['network'], {'requests': 0, 'bodyBytesRead': 0})
        self.assertEqual(len(second['sources'][0]['bindings']), 3)
        self.assertFalse(second['countryComplete'])
        self.assertEqual(second['normalized'], 0)

    def test_due_conditional_refresh_preserves_original(self):
        t = Transport(Response(headers={'etag': 'version'}), Response(304))
        self.run_batch(t)
        result = self.run_batch(t, NOW + timedelta(days=30))
        self.assertEqual(t.calls[-1][1]['If-None-Match'], 'version')
        self.assertEqual(result['sources'][0]['provenance']['originalAcquiredAt'], NOW.isoformat())
        self.assertEqual(result['network']['bodyBytesRead'], 0)

    def test_exact_reviewed_public_query_and_read_only_post_contracts(self):
        query = replace(SPEC, url='https://publisher.example/api?id=foods', query_keys=['id'])
        query.validate()
        self.assertEqual(query.identity()['queryKeys'], ['id'])
        for bad in (replace(query, query_keys=[]),
                    replace(query, url='https://publisher.example/api?token=secret', query_keys=['token']),
                    replace(query, url='https://publisher.example/api?id=1&id=2'),
                    replace(query, url='https://publisher.example/api?id=%0A')):
            with self.assertRaises((RefreshError, ValueError)):
                bad.validate()
        body = canonical({'query': [], 'response': {'format': 'JSON-stat2'}}).decode()
        post = replace(SPEC, request_method='POST', request_body=body, public_read_only_post=True)
        post.validate()
        self.assertEqual(post.identity()['request']['body'], body)
        self.assertNotEqual(post.identity(), SPEC.identity())
        for bad in (replace(post, public_read_only_post=False),
                    replace(post, request_body='{"password":"never"}'),
                    replace(post, request_body='{"query": []}'), replace(post, request_method='DELETE')):
            with self.assertRaises(RefreshError):
                bad.validate()

    def test_transport_sends_exact_query_and_post_body_without_credentials(self):
        from offmenu.refresh.acquisition import HTTPSFileTransport
        query = replace(SPEC, url='https://publisher.example/api?id=foods', query_keys=['id'])
        body = canonical({'query': [], 'response': {'format': 'JSON-stat2'}}).decode()
        post = replace(query, request_method='POST', request_body=body, public_read_only_post=True)
        for spec in (query, post):
            conn = Mock()
            conn.getresponse.return_value.getheaders.return_value = []
            conn.getresponse.return_value.status = 200
            with patch('offmenu.refresh.acquisition.http.client.HTTPSConnection', return_value=conn):
                response = HTTPSFileTransport()(spec, {'Accept-Encoding': 'identity'})
                response.close()
            args, kwargs = conn.request.call_args
            self.assertEqual(args, (spec.request_method, '/api?id=foods'))
            if spec.request_method == 'POST':
                self.assertEqual(kwargs['body'], body.encode())
                self.assertEqual(kwargs['headers']['Content-Type'], 'application/json')
            self.assertNotIn('Authorization', kwargs['headers'])

    def test_held_source_isolated_and_not_requested(self):
        self.registry['sources'][0]['holds'] = ['source-use restriction']
        other = replace(SPEC, source_key='z-independent', url='https://publisher.example/other')
        self.registry['sources'].append(self.entry(other))
        self.registry['bindings'].append(self.binding(other.source_key, 'LY', 'prices'))
        t = Transport(Response())
        result = self.run_batch(t)
        self.assertEqual(result['failedSources'], 1)
        self.assertEqual(result['verifiedSources'], 1)
        self.assertEqual(t.calls[0][0].source_key, 'z-independent')

    def test_forbidden_not_retried_and_remaining_source_runs(self):
        other = replace(SPEC, source_key='z-independent', url='https://publisher.example/other')
        self.registry['sources'].append(self.entry(other))
        self.registry['bindings'].append(self.binding(other.source_key, 'LY', 'prices'))
        t = Transport(Response(403), Response())
        result = self.run_batch(t)
        self.assertEqual(len(t.calls), 2)
        self.assertEqual(result['failedSources'], 1)
        self.assertEqual(result['verifiedSources'], 1)

    def test_retained_import_repeat_preserves_original_and_evidence(self):
        original = self.retained()
        before = original.read_bytes(), original.stat().st_mtime_ns
        t = Transport()
        first = self.run_batch(t)
        cached = Path(first['sources'][0]['path'])
        mtime = cached.stat().st_mtime_ns
        repeat = self.run_batch(t, NOW + timedelta(days=1))
        self.assertEqual(t.calls, [])
        self.assertEqual(cached.stat().st_mtime_ns, mtime)
        self.assertEqual((original.read_bytes(), original.stat().st_mtime_ns), before)
        provenance = repeat['sources'][0]['provenance']
        self.assertEqual(provenance['result'], 'retained-import')
        self.assertEqual(provenance['originalAcquiredAt'], NOW.isoformat())
        self.assertEqual(provenance['checkedAt'], NOW.isoformat())
        self.assertEqual(provenance['retainedOrigin']['evidence'], self.pin)

    def test_corrupt_original_and_corrupt_cache_fail_closed(self):
        original = self.retained()
        original.write_bytes(b'changed')
        bad = self.run_batch(Transport())
        self.assertEqual(bad['sources'][0]['error'], 'retained-original-mismatch')
        original.write_bytes(b'original untouched bytes\n')
        good = self.run_batch(Transport())
        Path(good['sources'][0]['path']).write_bytes(b'corrupt')
        again = self.run_batch(Transport())
        self.assertEqual(again['sources'][0]['error'], 'cached-body-corrupt')

    def test_missing_or_other_owner_claim_blocks_without_network(self):
        self.registry['sources'][0]['claim']['owner'] = 22
        t = Transport()
        self.assertEqual(self.run_batch(t)['sources'][0]['error'], 'collection-claim-not-selected')
        self.assertEqual(t.calls, [])

    def catalog(self):
        self.registry['schemaVersion'] = 'offmenu-acquisition-selection/2'
        self.registry['assetCatalog'] = {'version': 'test-v1', 'qualification': 'fixture metadata only',
            'evidence': [self.pin], 'requirements': [
                {'country': 'AU', 'type': 'foods', 'assetIds': ['known'], 'status': 'partial',
                 'coverageQualification': 'selected test scope only', 'evidence': self.pin},
                {'country': 'BE', 'type': 'recipes', 'assetIds': [], 'status': 'unknown',
                 'coverageQualification': 'missing input', 'evidence': self.pin}],
            'assets': [{'assetId': 'known', 'kind': 'declared-raw-original',
                'publisherCitation': None, 'request': {'url': SPEC.url, 'method': 'GET'}, 'release': SPEC.release,
                'datatype': 'test', 'format': None, 'destination': self.registry['resources']['storageRoot'], 'integrity': None,
                'budget': self.registry['resources'], 'holds': [], 'reuse': {'minimumDays': 30}, 'purpose': None,
                'actualScope': {'complete': False}, 'localEvidence': None, 'provenance': [self.pin],
                'sourceKeys': [SPEC.source_key], 'unresolved': ['publisher-citation']} ]}

    def test_v2_metadata_counts_preserve_missing_coverage_and_never_read_raw(self):
        from offmenu.refresh.acquisition import describe_collection_registry
        self.catalog()
        import offmenu.refresh.acquisition as acquisition
        original_digest = acquisition.digest
        def evidence_only(path, **kwargs):
            self.assertEqual(Path(path), self.evidence)
            return original_digest(path, **kwargs)
        with patch.object(acquisition, 'digest', side_effect=evidence_only):
            report = describe_collection_registry(self.registry)
        self.assertEqual(report['countriesRepresented'], 2)
        self.assertEqual(report['requirementsWithoutDeclaredAssetEdges'], 1)
        self.assertEqual(report['unresolvedDescriptors'], 1)
        self.assertFalse(report['mappingComplete'])
        self.assertFalse(report['countryComplete'])

    def test_v2_catalog_does_not_enable_unselected_sources(self):
        import copy
        self.catalog()
        desired = copy.deepcopy(self.registry['assetCatalog']['assets'][0])
        desired.update(assetId='desired', kind='desired-source-citation', sourceKeys=[])
        self.registry['assetCatalog']['assets'].append(desired)
        t = Transport(Response())
        report = self.run_batch(t)
        self.assertEqual(len(t.calls), 1)
        self.assertEqual(report['verifiedSources'], 1)
        self.assertEqual(report['assetCatalogSummary']['desiredSourceCitations'], 1)
        self.assertEqual(report['assetCatalogSummary']['selectedExecutableSources'], 1)

    def test_v2_unmapped_executable_source_fails_before_request(self):
        self.catalog()
        self.registry['assetCatalog']['assets'][0]['sourceKeys'] = []
        with self.assertRaisesRegex(RefreshError, 'selected-asset-binding-mismatch'):
            self.run_batch(Transport())

    def country_index(self):
        self.catalog()
        self.registry['schemaVersion'] = 'offmenu-acquisition-selection/3'
        asset = self.registry['assetCatalog']['assets'][0]
        asset['localEvidence'] = {'declaredPath': '/fixture/original.zip',
                                  'existenceState': 'held-locally-with-evidence'}
        unknown = {'assetId': None, 'state': 'unknown-notyetfound', 'owner': None,
                   'citation': None, 'release': None, 'localPointer': None, 'receipt': None,
                   'receiptDate': None, 'nextAction': 'Existing owner locates exact source evidence',
                   'pointerScope': 'unknown', 'rights': {'status': 'unknown'},
                   'coverage': {'status': 'unknown'}, 'blockedReason': None}
        import copy
        for row in self.registry['assetCatalog']['requirements']:
            row['bindings'] = [copy.deepcopy(unknown)]
        held = self.registry['assetCatalog']['requirements'][0]['bindings'][0]
        held.update(assetId='known', state='held-locally-with-evidence', owner=27,
                    citation={'publisher': 'fixture'}, release='fixture-release',
                    localPointer='/fixture/original.zip', receipt=self.pin, pointerScope='shared')
        return held

    def test_country_lookup_keeps_known_file_held_with_unknown_clock_rights_coverage(self):
        from offmenu.refresh.acquisition import lookup_country_sources
        self.country_index()
        import offmenu.refresh.acquisition as acquisition
        original_digest = acquisition.digest
        def metadata_only(path, **kwargs):
            self.assertEqual(Path(path), self.evidence)
            return original_digest(path, **kwargs)
        with patch('offmenu.refresh.acquisition.digest', side_effect=metadata_only):
            report = lookup_country_sources(self.registry, 'AU', 'foods')
        row = report['requirements'][0]['bindings'][0]
        self.assertEqual(row['state'], 'held-locally-with-evidence')
        self.assertEqual(row['localPointer'], '/fixture/original.zip')
        self.assertIsNone(row['receiptDate'])
        self.assertEqual(row['rights']['status'], 'unknown')
        self.assertFalse(report['acquisitionEnabledByLookup'])
        self.assertFalse(report['countryComplete'])

    def test_country_lookup_unknown_is_explicit_not_missing_or_not_applicable(self):
        from offmenu.refresh.acquisition import lookup_country_sources
        self.country_index()
        report = lookup_country_sources(self.registry, 'BE')
        self.assertEqual(report['requirements'][0]['bindings'][0]['state'], 'unknown-notyetfound')
        with self.assertRaisesRegex(RefreshError, 'not-indexed'):
            lookup_country_sources(self.registry, 'BE', 'unknown-type')

    def test_country_lookup_rejects_downgrade_and_wrong_shared_pointer(self):
        from offmenu.refresh.acquisition import lookup_country_sources
        held = self.country_index()
        held['state'] = 'unknown-notyetfound'
        with self.assertRaisesRegex(RefreshError, 'must-not-be-downgraded'):
            lookup_country_sources(self.registry, 'AU')
        held['state'] = 'held-locally-with-evidence'
        held['localPointer'] = '/unrelated/file'
        with self.assertRaisesRegex(RefreshError, 'local-pointer-required'):
            lookup_country_sources(self.registry, 'AU')

    def test_country_lookup_requires_exact_blocker_and_real_evidence_for_active_states(self):
        from offmenu.refresh.acquisition import lookup_country_sources
        self.country_index()
        row = self.registry['assetCatalog']['requirements'][1]
        row['assetIds'] = ['known']
        self.registry['assetCatalog']['assets'][0]['localEvidence'] = None
        # Lookup now validates the complete metadata catalogue. Keep the other
        # fixture row consistent when this test removes its shared local proof.
        other = self.registry['assetCatalog']['requirements'][0]['bindings'][0]
        other.update(state='unknown-notyetfound', localPointer=None)
        blocked = row['bindings'][0]
        blocked.update(assetId='known', state='found-blocked-exactreason', receipt=self.pin)
        with self.assertRaisesRegex(RefreshError, 'exact-country-binding-blocker'):
            lookup_country_sources(self.registry, 'BE')
        blocked['blockedReason'] = {'category': 'access', 'detail': 'Exact fixture source403; stop requests'}
        report = lookup_country_sources(self.registry, 'BE')
        self.assertEqual(report['requirements'][0]['bindings'][0]['blockedReason']['category'], 'access')
        blocked.update(state='queued-downloading-partial', blockedReason=None, receipt=None)
        with self.assertRaisesRegex(RefreshError, 'evidence-required'):
            lookup_country_sources(self.registry, 'BE')

    def test_country_lookup_not_applicable_requires_specific_justification(self):
        from offmenu.refresh.acquisition import lookup_country_sources
        self.country_index()
        binding = self.registry['assetCatalog']['requirements'][1]['bindings'][0]
        binding['coverage']['applicability'] = 'not-applicable'
        with self.assertRaisesRegex(RefreshError, 'explicit-justification'):
            lookup_country_sources(self.registry, 'BE')
        binding['coverage']['notApplicableJustification'] = {
            'detail': 'Synthetic reviewed scope excludes this requirement', 'evidence': self.pin}
        result = lookup_country_sources(self.registry, 'BE')
        self.assertEqual(result['requirements'][0]['bindings'][0]['coverage']['applicability'], 'not-applicable')

    def lookup_cli(self, label='lookup-regression'):
        path = self.root / 'lookup-registry.json'
        path.write_bytes(canonical(self.registry))
        output = self.root / label
        command = [sys.executable, '-B', str(Path(__file__).resolve().parents[1] /
                   'scripts/collect-source-access.py'), str(output), '--collection-registry',
                   str(path), '--registry-sha256', sha(path.read_bytes()), '--country', 'AU']
        return subprocess.run(command, capture_output=True, text=True), output

    def test_declared_held_edge_cannot_be_hidden_by_null_unknown_api(self):
        import copy
        from offmenu.refresh.acquisition import lookup_country_sources, describe_collection_registry
        self.country_index()
        row = self.registry['assetCatalog']['requirements'][0]
        row['bindings'] = [copy.deepcopy(self.registry['assetCatalog']['requirements'][1]['bindings'][0])]
        self.assertEqual(row['assetIds'], ['known'])
        with self.assertRaisesRegex(RefreshError, 'declared-asset-edge'):
            describe_collection_registry(self.registry)
        with self.assertRaisesRegex(RefreshError, 'declared-asset-edge'):
            lookup_country_sources(self.registry, 'AU')

    def test_declared_held_edge_cannot_be_hidden_by_null_unknown_cli(self):
        import copy
        self.country_index()
        self.registry['assetCatalog']['requirements'][0]['bindings'] = [copy.deepcopy(
            self.registry['assetCatalog']['requirements'][1]['bindings'][0])]
        result, output = self.lookup_cli()
        self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
        self.assertIn('declared-asset-edge', result.stdout)
        self.assertFalse((output / 'country-AU-sources.json').exists())

    def test_declared_held_edge_survives_separate_unknown_binding(self):
        import copy
        from offmenu.refresh.acquisition import lookup_country_sources
        self.country_index()
        row = self.registry['assetCatalog']['requirements'][0]
        row['bindings'].append(copy.deepcopy(self.registry['assetCatalog']['requirements'][1]['bindings'][0]))
        result = lookup_country_sources(self.registry, 'AU')
        held = result['requirements'][0]['bindings'][0]
        self.assertEqual(held['assetId'], 'known')
        self.assertEqual(held['state'], 'held-locally-with-evidence')
        self.assertEqual(held['localPointer'], '/fixture/original.zip')
        self.assertIsNone(held['receiptDate'])
        self.assertEqual(result['requirements'][0]['bindings'][1]['state'], 'unknown-notyetfound')

    def assert_unverified_country_pin_rejected(self, label):
        from offmenu.refresh.acquisition import lookup_country_sources
        with self.subTest(boundary='API'):
            with self.assertRaises(RefreshError):
                lookup_country_sources(self.registry, 'AU')
        with self.subTest(boundary='pinned CLI'):
            result, output = self.lookup_cli(label)
            self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
            self.assertFalse((output / 'country-AU-sources.json').exists())

    def test_qualified_pin_missing_receipt_is_rejected_api_and_cli(self):
        held = self.country_index()
        held['receipt'] = {'path': str(self.root / 'never-existed.json'), 'sha256': '0' * 64}
        self.assert_unverified_country_pin_rejected('missing-receipt')

    def test_qualified_pin_wrong_receipt_hash_is_rejected_api_and_cli(self):
        held = self.country_index()
        path = self.root / 'changed-receipt.json'
        path.write_bytes(b'{"metadata":"actual bytes differ"}')
        held['receipt'] = {'path': str(path), 'sha256': '0' * 64}
        self.assert_unverified_country_pin_rejected('wrong-receipt')

    def test_qualified_pin_unlisted_receipt_is_not_read_as_payload(self):
        held = self.country_index()
        path = self.root / 'unregistered-payload.bin'
        path.write_bytes(b'Fixture body must not be opened as country evidence')
        held['receipt'] = {'path': str(path), 'sha256': sha(path.read_bytes())}
        self.assert_unverified_country_pin_rejected('unlisted-receipt')

    def test_qualified_pin_bad_catalogue_hash_is_rejected_api_and_cli(self):
        held = self.country_index()
        path = self.root / 'declared-metadata.json'
        path.write_bytes(b'{"metadata":"changed"}')
        held['receipt'] = {'path': str(path), 'sha256': '0' * 64}
        self.registry['assetCatalog']['evidence'].append(held['receipt'])
        self.assert_unverified_country_pin_rejected('bad-catalogue-hash')

    def test_qualified_pin_empty_na_evidence_is_rejected_api_and_cli(self):
        held = self.country_index()
        held['coverage'].update(applicability='not-applicable', notApplicableJustification={
            'detail': 'Specific scope exclusion needs real evidence',
            'evidence': {'path': '', 'sha256': '0' * 64}})
        self.assert_unverified_country_pin_rejected('empty-na-evidence')

    def test_qualified_pin_unlisted_na_evidence_is_rejected_api_and_cli(self):
        held = self.country_index()
        path = self.root / 'unlisted-na-evidence.json'
        path.write_bytes(b'{"metadata":"unreviewed scope"}')
        held['coverage'].update(applicability='not-applicable', notApplicableJustification={
            'detail': 'Specific scope exclusion needs registered metadata evidence',
            'evidence': {'path': str(path), 'sha256': sha(path.read_bytes())}})
        self.assert_unverified_country_pin_rejected('unlisted-na-evidence')

    def test_registry_and_binding_evidence_fail_before_source_request(self):
        path = self.root / 'registry.json'
        path.write_bytes(canonical(self.registry))
        with self.assertRaisesRegex(RefreshError, 'registry-pin-mismatch'):
            collect_registry(path, '0' * 64, self.root / 'reports', transport=Transport(), now=NOW)
        self.evidence.write_bytes(b'changed review')
        with self.assertRaisesRegex(RefreshError, 'evidence-pin-mismatch'):
            self.run_batch(Transport())

    def test_duplicate_release_must_use_bindings_not_alias_download(self):
        self.registry['sources'].append(self.entry(replace(SPEC, source_key='alias')))
        with self.assertRaisesRegex(RefreshError, 'duplicate-source-release'):
            self.run_batch(Transport())

    def test_stale_retained_does_not_reset_age_or_download(self):
        self.retained()
        t = Transport()
        result = self.run_batch(t, NOW + timedelta(days=30))
        self.assertEqual(result['sources'][0]['error'], 'cache-stale')
        self.assertEqual(t.calls, [])

    def test_interrupted_copy_is_restarted_not_appended(self):
        self.retained()
        from offmenu.refresh.acquisition import SourceSpec
        identity = SourceSpec(**self.registry['sources'][0]['spec']).identity()
        directory = self.root / 'cache' / 'requests' / sha(canonical(identity))
        directory.mkdir(parents=True)
        (directory / 'body.partial').write_bytes(b'never append this')
        result = self.run_batch(Transport())
        self.assertEqual(result['verifiedSources'], 1)
        self.assertEqual(Path(result['sources'][0]['path']).read_bytes(), b'original untouched bytes\n')
        self.assertFalse((directory / 'body.partial').exists())

    def test_cumulative_batch_budget_counts_discarded_and_success_bytes(self):
        self.registry['resources']['maxTransferBytes'] = 128
        other = replace(SPEC, source_key='z-independent', url='https://publisher.example/other')
        self.registry['sources'].append(self.entry(other))
        self.registry['bindings'].append(self.binding(other.source_key, 'LY', 'prices'))
        t = Transport(Response(body=b'a' * 100), Response(body=b'b' * 40))
        result = self.run_batch(t)
        self.assertEqual(result['verifiedSources'], 1)
        self.assertEqual(result['sources'][1]['error'], 'batch-transfer-budget-exceeded')
        self.assertEqual(result['network']['bodyBytesRead'], 128)


if __name__ == '__main__':
    unittest.main()
