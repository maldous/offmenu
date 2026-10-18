"""Authored metadata/selector fixtures only; no retained source body is read."""
import copy
import json
from pathlib import Path
import subprocess
import sys
import unittest
from unittest.mock import patch

from offmenu.refresh.acceptance import fingerprint
from offmenu.refresh.core import canonical
from offmenu.refresh import portfolio52 as binding

NOW = '2026-10-18T00:00:00Z'


def observation(country):
    spec = binding.catalogue()[country]
    path = spec['originalInput']['path'].split('/')[-1]
    if country == 'MX':
        data = {'labelLiteral': 'SYNTHETIC GROUP', 'durabilityLiteral': None, 'weightLiteral': '0.00'}
        record = 'Table 1!row:3'
        selectors = {'labelLiteral': 'xl/worksheets/sheet1.xml!A3',
                     'durabilityLiteral': 'xl/worksheets/sheet1.xml!B3',
                     'weightLiteral': 'xl/worksheets/sheet1.xml!C3'}
        coordinate = {'sourceRow': 3, 'sourceRole': 'source-classification-group'}
    else:
        data = {'seriesLiteral': 'SYNTHETIC TYPE', 'yearLiteral': '1993', 'valueLiteral': 'na'}
        record = '/result/records/0'
        selectors = {'seriesLiteral': record + '/DataSeries', 'valueLiteral': record + '/1993'}
        coordinate = {'sourceRecordIndex0': 0}
    origins = {'/data/' + k: {'kind': 'source', 'sourceId': spec['sourceId'],
                            'releaseId': spec['releaseId'], 'inputPath': path,
                            'inputSha256': spec['originalInput']['sha256'],
                            'sourceRecordId': record, 'sourceField': v}
               for k, v in selectors.items()}
    if country == 'SG':
        origins['/data/yearLiteral'] = {'kind': 'derived',
            'policySha256': binding.observation_policy(country),
            'transform': 'json-object-member-name', 'inputs': [dict(origins['/data/valueLiteral'])]}
    return {'id': 'authored-fixture-only', 'schemaVersion': '1.0', 'kind': spec['kind'],
            'countries': [country], 'data': data,
            'provenance': {'sourceId': spec['sourceId'], 'releaseId': spec['releaseId'],
                           'fetchedAt': spec['originalAcquiredAt'], 'fieldOrigins': origins,
                           'retainedProjection': copy.deepcopy(spec['retainedArtifacts'][0]), **coordinate}}


class Portfolio52Tests(unittest.TestCase):
    def setUp(self):
        self.inputs = binding.catalogue()

    def test_valid_metadata_is_not_source_acceptance(self):
        result = binding.plan('MX', self.inputs['MX'], now=NOW)
        self.assertEqual(result['status'], 'binding-ready-pending-review')
        self.assertEqual(result['cache']['minimumReuseDays'], 30)
        self.assertFalse(result['accepted'])
        self.assertFalse(result['datasetExecutionAllowed'])
        self.assertFalse(result['sourceBytesVerified'])
        self.assertIn('independent-staging-scope-review-required', result['executionHolds'])

    def test_deterministic_replay_and_validation_clock_independent_key(self):
        a = binding.plan('SG', self.inputs['SG'], now=NOW)
        self.assertEqual(canonical(a), canonical(binding.plan('SG', self.inputs['SG'], now=NOW)))
        b = binding.plan('SG', self.inputs['SG'], now='2026-10-19T00:00:00Z', previous_key=a['bindingKey'])
        self.assertEqual(b['bindingKey'], a['bindingKey'])
        self.assertEqual(b['replay'], 'no-op')
        self.assertNotEqual(a['cache']['acquisitionAgeDays'], b['cache']['acquisitionAgeDays'])

    def test_reviewed_credit_change_invalidates_proposal_key(self):
        a = binding.plan('MX', self.inputs['MX'], now=NOW)
        changed = copy.deepcopy(self.inputs['MX']); changed['credit'] += ' amended review notice'
        with patch.dict(binding.BINDINGS, {'MX': changed}):
            b = binding.plan('MX', changed, now=NOW, previous_key=a['bindingKey'])
        self.assertNotEqual(a['bindingKey'], b['bindingKey'])
        self.assertEqual(b['replay'], 'emit-metadata-proposal')

    def test_small_authored_outcome_fixture(self):
        cases = json.loads((Path(__file__).parent / 'fixtures/portfolio52/cases.json').read_text())
        for case in cases:
            with self.subTest(case=case['name']):
                metadata = copy.deepcopy(self.inputs[case['country']])
                if case['input'] == 'absent':
                    metadata = None
                elif case['input'] == 'wrong-release':
                    metadata['releaseId'] = 'SYNTHETIC WRONG RELEASE'
                result = binding.plan(case['country'], metadata, now=case['now'])
                self.assertEqual(result['status'], case['expected'])

    def test_exact_thirty_day_boundary_stale_without_download(self):
        for now, status in [('2026-11-13T22:11:16.842446Z', 'binding-ready-pending-review'),
                            ('2026-11-13T22:11:16.842447Z', 'stale-input')]:
            p = binding.plan('MX', self.inputs['MX'], now=now)
            self.assertEqual(p['status'], status)
            self.assertEqual(p['networkRequests'], 0)
        self.assertFalse(p['cache']['revalidationResetsAcquisitionAge'])

    def test_validation_timestamp_cannot_refresh_original_acquisition(self):
        value = self.inputs['MX']
        value['lastValidatedAt'] = '2026-11-13T22:11:16.842447Z'
        p = binding.plan('MX', value, now='2026-11-14T00:00:00Z')
        self.assertEqual(p['status'], 'malformed-input')
        self.assertIn('metadata-binding-mismatch', p['errors'])
        # A newly forged acquiredAt cannot establish freshness either.
        value['originalAcquiredAt'] = value['lastValidatedAt']
        self.assertEqual(binding.plan('MX', value, now='2026-11-14T00:00:00Z')['status'], 'malformed-input')

    def test_missing_held_and_malformed_are_isolated(self):
        del self.inputs['SG']
        self.inputs['MX']['originalInput']['sha256'] = 'a' * 64
        report = binding.plan_portfolio(self.inputs, now=NOW)
        self.assertEqual([x['status'] for x in report['sources']],
                         ['malformed-input', 'missing-input', 'held', 'held'])
        self.assertTrue(all(x['replay'] == 'blocked' for x in report['sources']))

    def test_hold_cannot_be_removed_by_input(self):
        for country in ['RS', 'SS']:
            self.assertEqual(binding.plan(country, self.inputs[country], now=NOW)['status'], 'held')
            self.inputs[country]['metadataHold'] = False
            self.inputs[country]['executionHolds'] = []
            self.assertEqual(binding.plan(country, self.inputs[country], now=NOW)['status'], 'malformed-input')

    def test_no_repins_or_wrong_types(self):
        for field, value in [('releaseId', 'new'), ('sourceId', 'foreign'),
                             ('sourceReceipt', None), ('metadataHold', 0)]:
            bad = copy.deepcopy(self.inputs['SG']); bad[field] = value
            self.assertEqual(binding.plan('SG', bad, now=NOW)['status'], 'malformed-input')
        self.assertEqual(binding.plan('MX', [], now=NOW)['status'], 'malformed-input')
        self.assertEqual(binding.plan('MX', self.inputs['MX'], now=NOW, previous_key=[] )['status'], 'malformed-input')

    def test_invalid_clock_and_unsupported_country(self):
        for now in ['no-date', '2026-10-18', '2020-01-01T00:00:00Z', '2026-10-18T11:00:00+11:00']:
            self.assertEqual(binding.plan('MX', self.inputs['MX'], now=now)['status'], 'malformed-input')
        self.assertEqual(binding.plan('FI', {}, now=NOW)['status'], 'unsupported')

    def test_planning_has_no_path_access_or_network(self):
        before = copy.deepcopy(self.inputs)
        with patch.object(Path, 'open', side_effect=AssertionError('must not open paths')), \
             patch('socket.socket', side_effect=AssertionError('must not use network')):
            binding.plan_portfolio(self.inputs, now=NOW)
        self.assertEqual(before, self.inputs)

    def test_all_origin_fields_and_null_zero_preserved(self):
        for country in ['MX', 'SG']:
            row = observation(country); before = copy.deepcopy(row)
            self.assertEqual(binding.observation_errors(country, row), [])
            self.assertEqual(row, before)
        row = observation('SG'); row['data']['valueLiteral'] = '0'
        self.assertEqual(binding.observation_errors('SG', row), [])

    def test_shared_origin_coverage_and_selector_drift(self):
        row = observation('MX')
        del row['provenance']['fieldOrigins']['/data/weightLiteral']
        errors = binding.observation_errors('MX', row)
        self.assertIn('field-origin-inventory-mismatch', errors)
        self.assertIn('field-origin-missing', errors)
        row = observation('MX')
        row['provenance']['fieldOrigins']['/data/labelLiteral']['sourceField'] = 'xl/worksheets/sheet1.xml!A4'
        self.assertIn('source-selector-mismatch', binding.observation_errors('MX', row))

    def test_release_pin_and_unknown_semantics_rejected(self):
        row = observation('SG')
        row['provenance']['releaseId'] = 'foreign'
        row['provenance']['fieldOrigins']['/data/seriesLiteral']['inputSha256'] = 'b'*64
        row['data']['valueLiteral'] = 0
        errors = binding.observation_errors('SG', row)
        self.assertIn('observation-identity-mismatch', errors)
        self.assertIn('field-origin-source-mismatch', errors)
        self.assertIn('field-origin-input-pin-mismatch', errors)
        self.assertIn('sg-count-lexeme-invalid', errors)

    def test_year_key_requires_derived_origin(self):
        row = observation('SG')
        row['provenance']['fieldOrigins']['/data/yearLiteral'] = dict(row['provenance']['fieldOrigins']['/data/valueLiteral'])
        self.assertIn('sg-year-key-origin-invalid', binding.observation_errors('SG', row))

    def test_no_header_totals_or_nonfinite_weights(self):
        for n in [True, 1, 2, 448, None]:
            row = observation('MX'); row['provenance']['sourceRow'] = n
            self.assertIn('mx-row-selector-invalid', binding.observation_errors('MX', row))
        for w in ['NaN', '-1', '100.1', 0, True]:
            row = observation('MX'); row['data']['weightLiteral'] = w
            self.assertIn('mx-weight-lexeme-invalid', binding.observation_errors('MX', row))
        self.assertEqual(binding.observation_errors('SS', observation('MX')), ['source-operation-held'])

    def test_literal_missingness_and_bad_structures(self):
        for row in [None, [], {}, {'data': []}, {'data': {}, 'provenance': []}]:
            self.assertEqual(binding.observation_errors('SG', row), ['observation-malformed'])
        row = observation('SG'); row['data']['nutrient'] = 'invented'
        self.assertIn('observation-fields-mismatch', binding.observation_errors('SG', row))

    def test_non_json_metadata_cannot_stop_peer_diagnostics(self):
        self.inputs['MX']['credit'] = float('nan')
        report = binding.plan_portfolio(self.inputs, now=NOW)
        self.assertEqual(report['sources'][0]['status'], 'malformed-input')
        self.assertEqual(report['sources'][1]['status'], 'binding-ready-pending-review')

    def literal(self, country):
        spec = binding.catalogue()[country]
        if country == 'MX':
            return {'schema': 'offmenu-source-literal-row/1', 'country': 'MX', 'sourceRow': 3,
                    'worksheet': 'Table 1', 'worksheetPart': 'xl/worksheets/sheet1.xml',
                    'sourceRole': 'source-classification-group', 'lineage': spec['originalInput'],
                    'cells': [{'address': 'A3', 'textLiteral': 'SYNTHETIC GROUP', 'formulaLiteral': None},
                              {'address': 'B3', 'textLiteral': None, 'formulaLiteral': None},
                              {'address': 'C3', 'textLiteral': '0.00', 'formulaLiteral': None}]}
        return {'schema': 'offmenu-source-aggregate-observation/1', 'country': 'SG',
                'sourceRole': 'aggregate-establishment-type-count', 'lineage': spec['originalInput'],
                'datasetId': 'd_a9e81ab29216b10b69e23e7957b680b9',
                'sourcePointer': '/result/records/0/1993', 'sourceSeriesLiteral': 'SYNTHETIC TYPE',
                'yearLiteral': '1993', 'valueLiteral': 'na'}

    def test_pure_literal_projection_and_full_shared_schema(self):
        from jsonschema import Draft202012Validator
        for country in ['MX', 'SG']:
            literal = self.literal(country); before = copy.deepcopy(literal)
            row = binding.bind_literal(country, literal)
            schema = binding.observation_schema(country)
            Draft202012Validator.check_schema(schema)
            self.assertEqual(list(Draft202012Validator(schema).iter_errors(row)), [])
            self.assertEqual(binding.observation_errors(country, row), [])
            self.assertEqual(literal, before)
            self.assertEqual(row, binding.bind_literal(country, literal))
        self.assertEqual(row['data']['valueLiteral'], 'na')
        row['provenance']['retainedProjection']['sha256'] = 'b' * 64
        self.assertIn('observation-identity-mismatch', binding.observation_errors('SG', row))

    def test_projection_refuses_bad_lineage_coordinate_formula_and_hold(self):
        from offmenu.refresh.core import RefreshError
        for country in ['RS', 'SS']:
            with self.assertRaisesRegex(RefreshError, 'source-operation-held'):
                binding.bind_literal(country, {})
        for country in ['MX', 'SG']:
            literal = self.literal(country); literal['lineage']['sha256'] = 'a'*64
            with self.assertRaisesRegex(RefreshError, 'literal-source-binding-mismatch'):
                binding.bind_literal(country, literal)
        literal = self.literal('MX'); literal['cells'].append(copy.deepcopy(literal['cells'][0]))
        with self.assertRaisesRegex(RefreshError, 'mx-literal-cells-invalid'):
            binding.bind_literal('MX', literal)
        literal = self.literal('MX'); literal['cells'][2]['formulaLiteral'] = '=1+1'
        with self.assertRaisesRegex(RefreshError, 'mx-literal-cells-invalid'):
            binding.bind_literal('MX', literal)
        literal = self.literal('SG'); literal['yearLiteral'] = '1994'
        with self.assertRaisesRegex(RefreshError, 'sg-literal-selector-invalid'):
            binding.bind_literal('SG', literal)

    def test_shared_source_contract_qualifies_only_authored_fixture_scope(self):
        from dataclasses import replace
        from functools import partial
        import hashlib
        import tempfile
        from offmenu.refresh.acceptance import Asset, SourceContract, qualify, accept, ids_digest
        from offmenu.refresh.serialization import encode_records

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); bundle = root / 'bundle'; bundle.mkdir()
            # An authored cell witness, not a workbook or retained country input.
            witness = {'A3': 'SYNTHETIC GROUP', 'B3': None, 'C3': '0.00'}
            raw = canonical(witness)
            spec = copy.deepcopy(self.inputs['MX'])
            spec.update(sourceId='fixture-portfolio52-mx', releaseId='authored-fixture-v1',
                        originalInput={'path': '/AUTHORED-ONLY/cells.json', 'bytes': len(raw),
                                       'sha256': hashlib.sha256(raw).hexdigest()})
            with patch.dict(binding.BINDINGS, {'MX': spec}):
                literal = self.literal('MX')
                projection = canonical(literal)
                spec['retainedArtifacts'] = [{'path': '/AUTHORED-ONLY/projection.json',
                    'bytes': len(projection), 'sha256': hashlib.sha256(projection).hexdigest()}]
                assets = []
                for name, body in [('cells.json', raw), ('projection.json', projection),
                                   ('rights.txt', b'Authored fixture retain/parse/transform only'),
                                   ('scope.txt', b'Authored fixture one row, no country acceptance')]:
                    (bundle / name).write_bytes(body)
                    assets.append(Asset(name, len(body), hashlib.sha256(body).hexdigest()))
                row = binding.bind_literal('MX', literal)
                self.assertEqual(list(row['data'].values()), list(witness.values()))
                candidate = root / 'candidate.jsonl'; encoded = encode_records([row])
                candidate.write_bytes(encoded)
                schemas = {row['kind']: binding.observation_schema('MX')}
                contract = SourceContract(spec['sourceId'], spec['releaseId'], 'authored-literal-fixture',
                    spec['originalAcquiredAt'], tuple(assets), 1, ids_digest([row['id']]),
                    schemas, fingerprint(schemas), partial(binding.observation_errors, 'MX'),
                    binding.observation_policy('MX'), assets[2], assets[3],
                    frozenset(('retain', 'parse', 'transform')), fixture=True)
                manifest = {'sourceId': contract.source_id, 'releaseId': contract.release_id,
                            'acquiredAt': contract.acquired_at, 'normalizedRecords': 1,
                            'candidateSha256': hashlib.sha256(encoded).hexdigest(),
                            'candidateBytes': len(encoded), 'rightsEvidenceSha256': assets[2].sha256,
                            'scopeEvidenceSha256': assets[3].sha256,
                            'inputFiles': [vars(a) for a in assets]}
                q = qualify(contract, bundle, candidate, manifest)
                self.assertTrue(q['qualified'], q['errors'])
                result = accept(contract, bundle, candidate, manifest)
                self.assertEqual(result['status'], 'accepted-fixture-scope')
                self.assertFalse(result['productionAccepted'])
                held = qualify(replace(contract, holds=('source-held',)), bundle, candidate, manifest)
                self.assertFalse(held['qualified'])
                self.assertIn('source-held', held['errors'])
                (bundle / 'projection.json').unlink()
                missing = qualify(contract, bundle, candidate, manifest)
                self.assertFalse(missing['qualified'])
                self.assertIn('input-custody-mismatch', missing['errors'])

    def cli(self, raw):
        return subprocess.run([sys.executable, '-m', 'offmenu.refresh.portfolio52', '--stdin', '--now', NOW],
                              input=raw, capture_output=True, timeout=20)

    def test_cli_is_deterministic_and_reports_all_four_sources(self):
        raw = canonical({'inputs': self.inputs})
        a, b = self.cli(raw), self.cli(raw)
        self.assertEqual(a.stdout, b.stdout)
        self.assertEqual(a.returncode, 2)  # RS/SS held, not an all-source success.
        self.assertEqual(a.stderr, b'')
        report = json.loads(a.stdout)
        self.assertEqual([s['country'] for s in report['sources']], ['MX', 'SG', 'RS', 'SS'])

    def test_cli_malformed_duplicate_nonfinite_and_oversize(self):
        for raw in [b'{', b'{"inputs":{},"inputs":{}}', b'{"inputs":{"MX":NaN}}',
                    b'x' * (binding.MAX_METADATA_BYTES+1), b'{"inputs":{},"force":true}',
                    b'{"inputs":{},"previousKeys":[]}']:
            p = self.cli(raw)
            self.assertEqual(p.returncode, 2)
            self.assertEqual(json.loads(p.stdout)['status'], 'malformed-input')
            self.assertEqual(p.stderr, b'')

    def test_generic_serializer_accepts_authored_proposal_envelopes(self):
        from offmenu.refresh.serialization import encode_records, compress
        rows = [observation('MX'), observation('SG')]
        self.assertEqual(encode_records(rows), b''.join(canonical([r]) for r in rows))
        self.assertEqual(compress(encode_records(rows)), compress(encode_records(rows)))
        self.assertEqual(fingerprint(rows), fingerprint(copy.deepcopy(rows)))


if __name__ == '__main__':
    unittest.main()
