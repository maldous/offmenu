import copy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from offmenu.portfolios.worker61 import assess, pointer, write_report
from offmenu.refresh.core import strict_json
from offmenu.refresh.acceptance import (Asset, SourceContract, qualify, canonical,
                                       fingerprint, ids_digest)
from offmenu.refresh.field_provenance import field_origin_errors

FIXTURES = Path(__file__).parent / 'fixtures/worker61'
NOW = '2026-10-18T00:00:00Z'


class Worker61BindingsTests(unittest.TestCase):
    def setUp(self):
        self.config = json.loads((FIXTURES / 'valid.json').read_text())

    def run_binding(self, config=None, root=None, now=NOW):
        return assess(self.config if config is None else config,
                      FIXTURES if root is None else root, now=now)

    def test_valid_metadata_origins_and_unknowns_not_food_acceptance(self):
        report = self.run_binding()
        row = report['results'][0]
        self.assertEqual(row['status'], 'metadata-bound')
        self.assertTrue(row['metadataBound'])
        self.assertEqual(row['fields']['title']['selector'], '/title')
        self.assertEqual(row['fields']['title']['manifest'], self.config['sources'][0]['manifest'])
        self.assertIsNone(row['fields']['title']['unit'])
        self.assertIsNone(row['retainedAdapter'])
        self.assertFalse(row['sourceProcessingAuthorized'])
        self.assertFalse(report['countryAccepted'])
        self.assertEqual(report['sourceBodyReads'], 0)
        self.assertEqual(row['fieldOriginErrors'], [])
        self.assertEqual(row['stagingReference']['provenance']['fieldOrigins']
                         ['/data/title/value']['sourceField'], '/title')
        self.assertEqual(row['stagingReference']['provenance']['fieldOrigins']
                         ['/data/title/nativeUnit']['kind'], 'constant')

    def test_origin_tamper_detected_by_shared_validator(self):
        row = self.run_binding()['results'][0]['stagingReference']
        row['provenance']['fieldOrigins']['/data/title/value']['inputSha256'] = 'f' * 64
        self.assertIn('field-origin-input-pin-mismatch', field_origin_errors(row,
            {'receipt.json': self.config['sources'][0]['manifest']['sha256']},
            policy_pins=(fingerprint(self.config['sources'][0]),)))

    def test_missing_held_malformed_stale_isolated_from_valid_peer(self):
        valid = self.config['sources'][0]
        missing, held, stale, malformed = [copy.deepcopy(valid) for _ in range(4)]
        missing.update(sourceId='missing', manifest=None)
        held.update(sourceId='held', holds=['no-body-use'], rightsStatus='held')
        stale.update(sourceId='stale')
        stale['manifest']['sha256'] = '0' * 64
        malformed.update(sourceId='malformed', unexpected=True)
        self.config['sources'] = [missing, held, malformed, stale, valid]
        rows = self.run_binding()['results']
        self.assertEqual([r['status'] for r in rows],
                         ['missing', 'held', 'malformed', 'stale-input', 'metadata-bound'])
        self.assertIn('stale-input-pin', rows[3]['diagnostics'])
        self.assertIn('source-held', rows[1]['diagnostics'])

    def test_only_declared_metadata_is_opened_no_source_path_followed(self):
        # Even if a metadata value is an original path, it remains plain evidence.
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            raw = b'{"acquiredAt":"2026-10-01T00:00:00Z","title":"/never/open/private.pdf","unit":null,"basis":null}'
            (root / 'receipt.json').write_bytes(raw)
            self.config['sources'][0]['manifest'].update(
                bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest())
            with patch('socket.create_connection', side_effect=AssertionError('network')):
                report = self.run_binding(root=root)
            self.assertEqual(report['results'][0]['fields']['title']['value'],
                             '/never/open/private.pdf')

    def test_unsafe_paths_symlinks_nonjson_and_missing_files(self):
        for path in ['../receipt.json', '/receipt.json', 'source.pdf', 'a\\b.json']:
            with self.subTest(path=path):
                self.config['sources'][0]['manifest']['path'] = path
                self.assertEqual(self.run_binding()['results'][0]['status'], 'invalid')
        self.config['sources'][0]['manifest']['path'] = 'missing.json'
        self.assertEqual(self.run_binding()['results'][0]['status'], 'missing')
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / 'receipt.json').symlink_to(FIXTURES / 'receipt.json')
            self.config['sources'][0]['manifest']['path'] = 'receipt.json'
            self.assertEqual(self.run_binding(root=root)['results'][0]['status'], 'invalid')

    def test_cache_age_uses_acquisition_not_recent_validation_or_mtime(self):
        first = self.run_binding()['results'][0]
        stale = self.run_binding(now='2026-11-01T00:00:00Z')['results'][0]
        self.assertEqual(first['cache']['decision'], 'reuse-retained-metadata-no-download')
        self.assertEqual(stale['cache']['decision'], 'revalidation-review-required-no-download')
        self.assertEqual(first['cache']['originalAcquiredAt'], stale['cache']['originalAcquiredAt'])
        self.assertFalse(stale['cache']['revalidationResetsAcquisitionAge'])
        self.assertEqual(stale['cache']['minimumReuseSeconds'], 30 * 86400)
        self.assertEqual(first['bindingKey'], stale['bindingKey'])
        self.assertEqual(stale['cache']['networkRequests'], 0)
        self.assertEqual(first['cache']['validationAgeSeconds'], 86400)

    def test_future_and_naive_times_rejected(self):
        self.assertEqual(self.run_binding(now='2026-09-01T00:00:00Z')['results'][0]['status'], 'invalid')
        with self.assertRaises(ValueError):
            self.run_binding(now='2026-10-18T00:00:00')

    def test_repeatable_output_noop_and_changes_require_successor(self):
        first, second = self.run_binding(), self.run_binding()
        self.assertEqual(first, second)
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'report.json'
            self.assertEqual(write_report(path, first), 'written')
            before = path.stat().st_mtime_ns
            self.assertEqual(write_report(path, second), 'no-op')
            self.assertEqual(path.stat().st_mtime_ns, before)
            with self.assertRaisesRegex(ValueError, 'report-exists'):
                write_report(path, self.run_binding(now='2026-11-01T00:00:00Z'))

    def test_missing_selectors_and_duplicate_bindings(self):
        self.config['sources'][0]['fields']['title']['selector'] = '/absent'
        self.assertIn('field-selector-missing:title', self.run_binding()['results'][0]['diagnostics'])
        self.config['sources'] *= 2
        self.assertIn('duplicate-source-release-binding', self.run_binding()['results'][1]['diagnostics'])
        self.assertEqual(pointer({'a/b': {'~': [4]}}, '/a~1b/~0/0'), 4)
        with self.assertRaises(ValueError):
            pointer({'a': []}, '/a/00')

    def test_shared_strict_parser_rejects_duplicate_and_nonfinite_input(self):
        for raw in [b'{"a":1,"a":2}', b'{"a":NaN}']:
            with self.assertRaises(ValueError):
                strict_json(raw)

    def test_malformed_pinned_metadata_isolated(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            raw = b'{"title":"first","title":"second"}'
            (root / 'receipt.json').write_bytes(raw)
            self.config['sources'][0]['manifest'].update(
                bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest())
            row = self.run_binding(root=root)['results'][0]
            self.assertEqual(row['status'], 'invalid')
            self.assertIn('metadata-invalid', row['diagnostics'])

    def test_rejected_complex_or_oversized_scalar_is_not_echoed(self):
        for value in [{'private': 'do not echo'}, 'x' * 8193]:
            with self.subTest(valueType=type(value).__name__), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                raw = json.dumps({'title': value, 'unit': None, 'basis': None,
                                  'acquiredAt': '2026-10-01T00:00:00Z'}).encode()
                (root / 'receipt.json').write_bytes(raw)
                self.config['sources'][0]['manifest'].update(
                    bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest())
                row = self.run_binding(root=root)['results'][0]
                self.assertIsNone(row['fields']['title']['value'])
                self.assertIn('field-selector-missing:title', row['diagnostics'])
                self.assertNotIn('title', row['stagingReference']['data'])

    def test_malformed_identity_isolated_and_country_does_not_split_source_key(self):
        original = self.run_binding()['results'][0]['metadataSourceKey']
        self.config['sources'][0]['country'] = 'GP'
        self.config['sources'][0]['validatedAt'] = None
        self.assertEqual(original, self.run_binding()['results'][0]['metadataSourceKey'])
        bad = copy.deepcopy(self.config['sources'][0]); bad['sourceId'] = ['invalid']
        self.config['sources'].insert(0, bad)
        self.assertEqual([r['status'] for r in self.run_binding()['results']],
                         ['malformed', 'metadata-bound'])

    def test_authored_metadata_candidate_uses_shared_qualification_only(self):
        # Demonstrates the existing shared contract with authored metadata only.
        # No real portfolio evidence is granted parse/transform rights by this test.
        result = self.run_binding()['results'][0]
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); bundle = root / 'bundle'; bundle.mkdir()
            assets = []
            for name, body in [('receipt.json', (FIXTURES / 'receipt.json').read_bytes()),
                               ('rights.json', b'authored fixture metadata use'),
                               ('scope.json', b'one authored metadata reference')]:
                (bundle / name).write_bytes(body)
                assets.append(Asset(name, len(body), hashlib.sha256(body).hexdigest()))
            row = copy.deepcopy(result['stagingReference'])
            row['id'] = 'fixture-reference'
            row['provenance']['fetchedAt'] = '2026-10-01T00:00:00Z'
            body = canonical([row]) + b'\n'; candidate = root / 'candidate.jsonl'; candidate.write_bytes(body)
            schemas = {'sourceInputBinding': {'type': 'object', 'required': ['id', 'kind', 'data', 'provenance'],
                       'properties': {'data': {'type': 'object', 'required': ['title', 'unit', 'basis']}}}}
            contract = SourceContract('fixture-nu-metadata', 'authored-1', 'authored-metadata-only',
                '2026-10-01T00:00:00Z', tuple(assets), 1, ids_digest(['fixture-reference']),
                schemas, fingerprint(schemas), lambda r: field_origin_errors(r,
                    {'receipt.json': assets[0].sha256}, policy_pins=(result['bindingKey'],)),
                'a' * 64, assets[1], assets[2],
                frozenset(('retain', 'parse', 'transform')), fixture=True)
            manifest = {'sourceId': contract.source_id, 'releaseId': contract.release_id,
                'acquiredAt': contract.acquired_at, 'normalizedRecords': 1,
                'candidateSha256': hashlib.sha256(body).hexdigest(), 'candidateBytes': len(body),
                'rightsEvidenceSha256': assets[1].sha256, 'scopeEvidenceSha256': assets[2].sha256,
                'inputFiles': [vars(a) for a in assets]}
            verdict = qualify(contract, bundle, candidate, manifest)
            self.assertTrue(verdict['qualified'], verdict['errors'])
            self.assertTrue(verdict['fixture'])


if __name__ == '__main__':
    unittest.main()
