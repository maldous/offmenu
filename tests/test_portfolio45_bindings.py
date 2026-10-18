"""Authored metadata only; no retained source bodies or production acceptance."""
import copy
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from offmenu.refresh.portfolio45 import assess, assess_many, catalog, template
from offmenu.refresh.acceptance import (Asset, SourceContract, canonical,
                                        fingerprint, ids_digest, qualify)
from offmenu.refresh.field_provenance import field_origin_errors


class Portfolio45Tests(unittest.TestCase):
    def setUp(self):
        evidence = Path(__file__).parent / 'fixtures/portfolio45/evidence.json'
        raw = evidence.read_bytes()
        self.binding = {
            'id': 'fixture45', 'country': 'JE', 'dataType': 'authored-metadata',
            'sourceId': 'authored.fixture45', 'releaseId': 'fixture-v1',
            'manifest': {'sha256': hashlib.sha256(raw).hexdigest()},
            'input': {'sha256': hashlib.sha256(b'authored-input-reference').hexdigest()},
            'metadataValues': json.loads(raw),
            'selectors': {'count': '/count', 'unit': '/unit'},
            'nativeUnit': 'authored-index', 'nativeBasis': 'fixture only',
            'originalAcquiredAt': '2026-10-01T00:00:00Z',
            'holds': [], 'unknowns': []}
        self.descriptor = template(self.binding)
        self.now = '2026-10-18T00:00:00Z'

    def test_valid_fixture_deterministic_zero_download_never_dataset_acceptance(self):
        result = assess(self.binding, self.descriptor, as_of=self.now)
        self.assertEqual(result['status'], 'valid')
        self.assertTrue(result['bindingReady'])
        self.assertFalse(result['datasetAccepted'])
        self.assertFalse(result['assetBytesVerified'])
        self.assertEqual(result['networkRequests'], 0)
        self.assertEqual(result['cache']['minimumReuseDays'], 30)
        self.assertEqual(result['cache']['acquisitionAgeDays'], 17)
        self.assertEqual(result, assess(self.binding, self.descriptor, as_of=self.now))

    def test_missing_original_acquisition_not_replaced_by_validation(self):
        binding = copy.deepcopy(self.binding)
        binding['originalAcquiredAt'] = None
        row = template(binding)
        row['validatedAt'] = self.now
        result = assess(binding, row, as_of=self.now)
        self.assertEqual(result['status'], 'missing')
        self.assertIsNone(result['cache']['acquisitionAgeDays'])
        self.assertIn('original-acquisition-time-unknown', result['diagnostics'])

    def test_held_even_with_valid_metadata_and_fresh_cache(self):
        binding = copy.deepcopy(self.binding)
        binding['holds'] = ['written-grant-required']
        result = assess(binding, self.descriptor, as_of=self.now)
        self.assertEqual(result['status'], 'held')
        self.assertFalse(result['bindingReady'])
        self.assertIn('written-grant-required', result['holds'])
        bad = dict(self.descriptor, holds=[])
        self.assertEqual(assess(binding, bad, as_of=self.now)['status'], 'malformed')

    def test_malformed_identity_hash_and_coordinates_accumulate(self):
        row = copy.deepcopy(self.descriptor)
        row['inputSha256'] = 'a' * 64
        row['row']['provenance']['fieldOrigins']['/data/count']['sourceField'] = '/wrong'
        row['row']['provenance']['fieldOrigins']['/data/unit']['inputSha256'] = 'b' * 64
        result = assess(self.binding, row, as_of=self.now)
        self.assertEqual(result['status'], 'malformed')
        self.assertIn('mismatch-inputSha256', result['diagnostics'])
        self.assertIn('metadata-selector-or-identity-mismatch', result['diagnostics'])
        self.assertIn('field-origin-input-pin-mismatch', result['diagnostics'])

    def test_stale_manifest_recent_validation_does_not_replace_pin(self):
        row = copy.deepcopy(self.descriptor)
        row['manifestSha256'] = 'a' * 64
        row['validatedAt'] = '2026-11-01T00:00:00Z'
        result = assess(self.binding, row, as_of='2026-11-01T00:00:00Z')
        self.assertEqual(result['status'], 'stale')
        self.assertEqual(result['cache']['acquisitionAgeDays'], 31)
        self.assertEqual(result['validationAgeDays'], 0)
        self.assertEqual(result['networkRequests'], 0)

    def test_metadata_numeric_type_and_manifest_pin_are_not_coerced(self):
        row = copy.deepcopy(self.descriptor)
        row['row']['data']['count'] = 2.0
        row['manifestSha256'] = '0' * 64
        result = assess(self.binding, row, as_of=self.now)
        self.assertIn('metadata-value-mismatch', result['diagnostics'])
        self.assertIn('stale-manifest-pin', result['diagnostics'])

    def test_thirty_day_ages_do_not_invent_planner_or_download(self):
        before = assess(self.binding, self.descriptor, as_of='2026-10-30T23:59:59Z')
        after = assess(self.binding, self.descriptor, as_of='2026-10-31T00:00:00Z')
        self.assertEqual(before['status'], 'valid')
        self.assertEqual(after['status'], 'valid')
        self.assertEqual(before['cache']['acquisitionAgeDays'], 29)
        self.assertEqual(after['cache']['acquisitionAgeDays'], 30)
        self.assertEqual(before['cache']['decision'], after['cache']['decision'])
        self.assertFalse(after['cachePlannerSupported'])
        self.assertFalse(after['stagingReady'])
        row = copy.deepcopy(self.descriptor)
        row['validatedAt'] = '2027-01-01T00:00:00Z'
        self.assertEqual(assess(self.binding, row, as_of=self.now)['status'], 'malformed')

    def test_noop_excludes_validation_age_not_content_identity(self):
        first = assess(self.binding, self.descriptor, as_of=self.now)
        row = copy.deepcopy(self.descriptor)
        row['priorReplayKey'] = first['replayKey']
        row['validatedAt'] = self.now
        replay = assess(self.binding, row, as_of=self.now)
        self.assertEqual(replay['decision'], 'no-op')
        self.assertEqual(replay['replayKey'], first['replayKey'])
        changed = copy.deepcopy(self.binding)
        changed['unknowns'] = ['new-contract-concern']
        self.assertNotEqual(assess(changed, row, as_of=self.now)['replayKey'], first['replayKey'])

    def test_isolated_diagnostics_keep_peer_valid_and_inputs_immutable(self):
        descriptors = [None, {'bindingId': 'not-registered'},
                       dict(self.descriptor, row=None), self.descriptor]
        before = copy.deepcopy(descriptors)
        result = assess_many(descriptors, as_of=self.now, bindings=[self.binding])
        self.assertEqual([r['status'] for r in result], ['missing', 'missing', 'malformed', 'valid'])
        self.assertEqual(descriptors, before)
        self.assertEqual(self.binding['metadataValues'], {'count': 2, 'unit': 'authored-index'})

    def test_real_catalog_fail_closed_and_has_exact_portfolio(self):
        bindings = catalog()['bindings']
        self.assertEqual({b['country'] for b in bindings}, {'IT', 'IS', 'JE', 'JM'})
        results = assess_many([template(b) for b in bindings], as_of=self.now)
        self.assertTrue(all(r['status'] == 'held' for r in results))
        self.assertFalse(any(r['bindingReady'] or r['datasetAccepted'] for r in results))
        self.assertTrue(all(r['cache']['acquisitionAgeDays'] is None for r in results))

    def test_cli_rejects_duplicate_keys_and_symlinks_without_body_access(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'metadata.json'
            path.write_text('[{"bindingId":"je-rpi","bindingId":"je-survey"}]')
            command = [sys.executable, '-B', '-m', 'offmenu.refresh.portfolio45',
                       '--input', str(path), '--as-of', self.now]
            run = subprocess.run(command, capture_output=True, text=True)
            self.assertEqual(run.returncode, 2)
            self.assertEqual(run.stdout, '')
            path.unlink()
            path.symlink_to('/intentionally-unavailable-source-body')
            self.assertEqual(subprocess.run(command, capture_output=True).returncode, 2)


    def test_authored_metadata_contract_uses_shared_qualification(self):
        # An actual fixture contract, never a production source/registry alias.
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            bundle = root / 'bundle'
            bundle.mkdir()
            assets = []
            authored = {'evidence.json': b'{"count":2,"unit":"authored-index"}\n',
                        'rights.json': b'authored fixture retain parse transform',
                        'scope.json': b'one authored metadata record fixture45'}
            for name, raw in authored.items():
                (bundle / name).write_bytes(raw)
                assets.append(Asset(name, len(raw), hashlib.sha256(raw).hexdigest()))
            row = copy.deepcopy(self.descriptor['row'])
            row.update(id='fixture45', kind='metadataReference', schemaVersion='1.0')
            row['provenance']['fetchedAt'] = self.binding['originalAcquiredAt']
            schemas = {'metadataReference': {
                'type': 'object', 'required': ['id', 'kind', 'schemaVersion', 'data', 'provenance'],
                'properties': {'kind': {'const': 'metadataReference'},
                               'data': {'const': self.binding['metadataValues']}}}}
            contract = SourceContract(
                self.binding['sourceId'], self.binding['releaseId'], 'authored-metadata-only',
                self.binding['originalAcquiredAt'], tuple(assets), 1, ids_digest(['fixture45']),
                schemas, fingerprint(schemas),
                lambda record: field_origin_errors(record, {'evidence.json': assets[0].sha256}),
                'b' * 64, assets[1], assets[2],
                frozenset(('retain', 'parse', 'transform')), fixture=True)
            raw = canonical([row]) + b'\n'
            candidate = root / 'candidate.jsonl'
            candidate.write_bytes(raw)
            manifest = {'sourceId': contract.source_id, 'releaseId': contract.release_id,
                        'acquiredAt': contract.acquired_at, 'normalizedRecords': 1,
                        'candidateSha256': hashlib.sha256(raw).hexdigest(), 'candidateBytes': len(raw),
                        'rightsEvidenceSha256': assets[1].sha256,
                        'scopeEvidenceSha256': assets[2].sha256,
                        'inputFiles': [vars(a) for a in assets]}
            result = qualify(contract, bundle, candidate, manifest)
            self.assertTrue(result['qualified'], result['errors'])
            self.assertTrue(result['fixture'])
            manifest['inputFiles'][0]['sha256'] = '0' * 64
            self.assertFalse(qualify(contract, bundle, candidate, manifest)['qualified'])


if __name__ == '__main__':
    unittest.main()
