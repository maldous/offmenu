from dataclasses import replace
import json
from pathlib import Path
import tempfile
import unittest

from offmenu.refresh.core import RefreshError, canonical, sha, strict_json
from offmenu.refresh.field_provenance import field_origin_errors
from offmenu.refresh.owner49_staging import (
    InputPin, MetadataBinding, assess_metadata, assess_portfolio, retained_diagnostics,
    stage_authored_fixture,
)

FIXTURES = Path(__file__).parent / 'fixtures' / 'owner49_staging'
NOW = '2026-10-18T00:00:00Z'


class Owner49StagingTests(unittest.TestCase):
    def setUp(self):
        self.cells = (FIXTURES / 'cells.json').read_bytes()
        self.raw = (FIXTURES / 'manifest.json').read_bytes()
        self.binding = MetadataBinding(
            source_id='owner49-authored-fixture', release_id='fixture-1', country='FI',
            record_kind='reference', manifest_sha256=sha(self.raw),
            inputs=(InputPin('cells.json', sha(self.cells), len(self.cells)),),
            selectors=(('/data/amount', 'amount'), ('/data/unit', 'unit'),
                       ('/data/basis', 'basis'),
                       ('/data/unknown', 'unknown')),
            native_units=('g',), basis='authored-per-100g',
            unknowns=('unknown remains null',), fixture=True)

    def assess(self, **kwargs):
        return assess_metadata(self.binding, self.raw, validated_at=NOW, **kwargs)

    def test_metadata_valid_and_zero_null_origins_survive_serialization(self):
        self.assertEqual(self.assess()['status'], 'valid')
        output = stage_authored_fixture(self.binding, self.raw, self.cells, validated_at=NOW)
        row = strict_json(output)[0]
        self.assertIsNone(row['data']['unknown'])
        self.assertEqual(row['data']['amount'], 0)
        self.assertEqual(field_origin_errors(row, {'cells.json': sha(self.cells)}), [])
        self.assertEqual(row['provenance']['fieldOrigins']['/data/unknown']['sourceField'], 'unknown')
        self.assertEqual(output, stage_authored_fixture(self.binding, self.raw, self.cells,
                                                      validated_at=NOW))
        self.assertFalse(self.assess()['admitted'])

    def test_replay_no_op_and_validation_cannot_extend_original_age(self):
        first = self.assess()
        replay = assess_metadata(self.binding, self.raw, validated_at='2026-10-20T00:00:00Z',
                                 previous_key=first['replayKey'])
        self.assertEqual(replay['status'], 'no-op')
        self.assertEqual(first['replayKey'], replay['replayKey'])
        self.assertEqual(replay['originalAcquiredAt'], '2026-10-01T00:00:00Z')
        self.assertGreater(replay['ageSeconds'], first['ageSeconds'])
        for now, expected in [('2026-10-30T23:59:59Z', 'valid'),
                              ('2026-10-31T00:00:00Z', 'stale-input')]:
            self.assertEqual(assess_metadata(self.binding, self.raw, validated_at=now,
                                            previous_key=first['replayKey'])['status'],
                             'no-op' if expected == 'valid' else expected)

    def test_missing_and_held_do_not_open_paths_or_parse_bodies(self):
        missing = assess_metadata(self.binding, None, validated_at=NOW)
        self.assertEqual(missing['status'], 'missing')
        held = replace(self.binding, holds=('fineli-source-processing-held',), fixture=False)
        self.assertEqual(assess_metadata(held, b'invalid', validated_at=NOW)['status'], 'held')
        with self.assertRaisesRegex(RefreshError, 'authored-fixture-required'):
            stage_authored_fixture(held, self.raw, self.cells, validated_at=NOW)

    def test_original_acquisition_unknown_is_not_validation_time(self):
        value = strict_json(self.raw)
        value['originalAcquiredAt'] = None
        raw = canonical(value)
        binding = replace(self.binding, manifest_sha256=sha(raw))
        result = assess_metadata(binding, raw, validated_at=NOW)
        self.assertEqual(result['code'], 'original-acquisition-missing')
        self.assertIsNone(result['replayKey'])

    def test_malformed_mismatched_and_sensitive_errors_are_isolated(self):
        cases = [b'{"secret":"token-value", "secret":0}', b'[1]', b'not json',
                 b'{"n":NaN}', self.raw + b' ', b'x' * 65537]
        for raw in cases:
            r = assess_metadata(self.binding, raw, validated_at=NOW)
            self.assertEqual(r['status'], 'malformed')
            self.assertNotIn('token-value', json.dumps(r))
        requests = {'valid': (self.binding, self.raw, None),
                    'invalid-binding': (replace(self.binding, inputs=(None,)), self.raw, None),
                    'malformed': (self.binding, cases[0], None),
                    'missing': (self.binding, None, None),
                    'held': (replace(self.binding, holds=('source-use-hold',)), None, None)}
        result = assess_portfolio(requests, validated_at=NOW)
        self.assertEqual({k: v['status'] for k, v in result.items()},
                         {'valid': 'valid', 'malformed': 'malformed',
                          'missing': 'missing', 'held': 'held', 'invalid-binding': 'malformed'})

    def test_time_contract_and_identity_pins_fail_closed(self):
        for now in ['2026-09-30T00:00:00Z', '2026-10-18', '2026-10-18T11:00:00+11:00']:
            self.assertEqual(assess_metadata(self.binding, self.raw, validated_at=now)['status'],
                             'malformed')
        for field, value in [('releaseId', 'wrong'), ('country', 'JP'),
                             ('recordKind', 'nutrition'), ('inputFiles', [])]:
            manifest = strict_json(self.raw)
            manifest[field] = value
            raw = canonical(manifest)
            self.assertEqual(assess_metadata(replace(self.binding, manifest_sha256=sha(raw)),
                                            raw, validated_at=NOW)['status'], 'malformed')
        changed = replace(self.binding, basis='different native basis')
        self.assertNotEqual(self.assess()['replayKey'],
                            assess_metadata(changed, self.raw, validated_at=NOW)['replayKey'])

    def test_fixture_rejects_wrong_source_hash_and_selector(self):
        with self.assertRaisesRegex(RefreshError, 'fixture-input-pin-mismatch'):
            stage_authored_fixture(self.binding, self.raw, self.cells + b' ', validated_at=NOW)
        changed = replace(self.binding, selectors=(('/data/amount', 'absent'),))
        with self.assertRaisesRegex(RefreshError, 'fixture-selector-invalid'):
            stage_authored_fixture(changed, self.raw, self.cells, validated_at=NOW)

    def test_catalog_is_complete_but_no_real_source_is_admitted(self):
        path = Path(__file__).parents[1] / 'docs/operations/owner49-staging-catalog.json'
        catalog = json.loads(path.read_text())
        self.assertEqual({v['country'] for v in catalog['sources']}, {'FI', 'JP', 'KE', 'KG'})
        for source in catalog['sources']:
            self.assertFalse(source['admitted'])
            self.assertTrue(source['blockers'])
            self.assertTrue(source['evidence'])
        first = retained_diagnostics(path.read_bytes())
        self.assertEqual(first, retained_diagnostics(path.read_bytes()))
        self.assertEqual(strict_json(first)['sources']['FI']['status'], 'held')
        self.assertEqual(strict_json(first)['sources']['KG']['status'], 'missing-original')
        catalog['sources'][0]['admitted'] = True
        with self.assertRaisesRegex(RefreshError, 'portfolio-catalog-invalid'):
            retained_diagnostics(canonical(catalog))

    def test_fixture_semantics_are_checked_beyond_origin_coverage(self):
        for field, value in [('unit', 'kg'), ('basis', 'per-serving')]:
            cells = strict_json(self.cells)
            cells[field] = value
            raw = canonical(cells)
            binding = replace(self.binding, inputs=(InputPin('cells.json', sha(raw), len(raw)),))
            manifest = strict_json(self.raw)
            manifest['inputFiles'] = [vars(binding.inputs[0])]
            manifest_raw = canonical(manifest)
            binding = replace(binding, manifest_sha256=sha(manifest_raw))
            with self.assertRaisesRegex(RefreshError, 'fixture-native-semantics-mismatch'):
                stage_authored_fixture(binding, manifest_raw, raw, validated_at=NOW)

    def test_authored_candidate_uses_shared_qualification_contract(self):
        from offmenu.refresh.acceptance import Asset, SourceContract, fingerprint, ids_digest, qualify
        output = stage_authored_fixture(self.binding, self.raw, self.cells, validated_at=NOW)
        schemas = {'reference': {
            'type': 'object', 'required': ['id', 'kind', 'schemaVersion', 'data', 'provenance'],
            'properties': {'kind': {'const': 'reference'}, 'schemaVersion': {'const': '1.0'},
                           'data': {'type': 'object',
                                    'required': ['amount', 'unit', 'basis', 'unknown'],
                                    'properties': {'amount': {'const': 0},
                                                   'unit': {'const': 'g'},
                                                   'basis': {'const': 'authored-per-100g'},
                                                   'unknown': {'type': 'null'}}}}}}
        pins = []
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            bundle = root / 'authored-bundle'
            bundle.mkdir()
            for name, body in [('cells.json', self.cells),
                               ('rights.txt', b'Authored fixture only; retain parse transform'),
                               ('scope.txt', b'One authored identity: authored-001')]:
                (bundle / name).write_bytes(body)
                pins.append(Asset(name, len(body), sha(body)))
            contract = SourceContract(
                self.binding.source_id, self.binding.release_id, 'authored-fixture-only',
                '2026-10-01T00:00:00Z', tuple(pins), 1, ids_digest(['authored-001']),
                schemas, fingerprint(schemas),
                lambda row: field_origin_errors(row, {'cells.json': sha(self.cells)}),
                sha(b'authored fixture policy'), pins[1], pins[2],
                frozenset(('retain', 'parse', 'transform')), fixture=True)
            candidate = root / 'candidate.jsonl'
            candidate.write_bytes(output)
            manifest = {'sourceId': contract.source_id, 'releaseId': contract.release_id,
                        'acquiredAt': contract.acquired_at, 'normalizedRecords': 1,
                        'candidateSha256': sha(output), 'candidateBytes': len(output),
                        'rightsEvidenceSha256': pins[1].sha256,
                        'scopeEvidenceSha256': pins[2].sha256,
                        'inputFiles': [vars(pin) for pin in pins]}
            result = qualify(contract, bundle, candidate, manifest)
            self.assertTrue(result['qualified'], result['errors'])
            self.assertTrue(result['fixture'])


if __name__ == '__main__':
    unittest.main()
