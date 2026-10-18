"""Small authored fixtures only; no retained source bodies or network access."""
from copy import deepcopy
from dataclasses import replace
import hashlib
from io import BytesIO, StringIO
import subprocess
import sys
import json
from pathlib import Path
import tempfile
import unittest

from offmenu.refresh import acceptance as q
from offmenu.refresh import worker46_bindings as b

NOW = '2026-10-18T00:00:00Z'


def rw_row(ordinal=1):
    values = dict.fromkeys(b.RW_HEADERS, '')
    values.update(Column='AUTHORED_EXAMPLE', description_abstract=' Fixture text\n')
    return {'sourceRecordId': f'codebook-data-record:{ordinal}', 'values': values}


def th_row(row=3, col=2):
    nutrient, unit = b.TH_ROWS[row-3]
    return {'sourceRecordId': f'table-1:tr{row}:td{col}', 'values': {
        'sampleCodeLiteral': 'ABCDE'[col-2], 'nutrientLabelLiteral': nutrient,
        'unitAndBasisLiteral': unit, 'sourceCellTextLiteral': '0.00 ± 0.01a',
        'meanLexeme': '0.00', 'standardDeviationLexeme': '0.01',
        'significanceGroupLiteral': 'a', 'noteMarkerLiteral': None}}


def materialize(root, fixture):
    bundle = root/'bundle'; bundle.mkdir()
    for name, raw in fixture['contents'].items():
        (bundle/name).write_bytes(raw)
    candidate = root/'candidate.jsonl'; candidate.write_bytes(fixture['candidate'])
    return bundle, candidate


class MetadataBindingTests(unittest.TestCase):
    def test_cli_catalog_and_assess_are_deterministic_metadata_only(self):
        catalog = StringIO()
        self.assertEqual(b.main(['catalog'], stdout=catalog), 0)
        metadata = json.loads(catalog.getvalue())
        output = StringIO()
        self.assertEqual(b.main(['assess', '--now', NOW],
            stdin=StringIO(catalog.getvalue()), stdout=output), 0)
        self.assertEqual(json.loads(output.getvalue()), b.assess_portfolio(metadata, now=NOW))
        self.assertEqual(json.loads(output.getvalue())['us-recipes']['status'], 'held')

    def test_cli_rejects_duplicate_keys_nonfinite_extra_sources_and_large_metadata(self):
        for raw in ('{"rw-codebook":null,"rw-codebook":null}',
                    '{"rw-codebook":NaN}', '{"unselected-source":null}', '[]', ' '*65537):
            with self.subTest(raw=raw[:30]):
                output = StringIO()
                self.assertEqual(b.main(['assess', '--now', NOW],
                    stdin=StringIO(raw), stdout=output), 2)
                self.assertEqual(json.loads(output.getvalue()), {'error': 'portfolio-metadata-invalid'})

    def test_exact_retained_pins_are_review_input_not_admission(self):
        for key in ('rw-codebook', 'th-table1'):
            with self.subTest(key=key):
                result = b.assess_input(key, b.metadata_template(key), now=NOW)
                self.assertEqual(result['status'], 'ready-for-binding-review')
                self.assertFalse(result['realExecutionAuthorized'])
                self.assertFalse(result['countryComplete'])
                self.assertEqual(result['networkRequests'], 0)

    def test_missing_held_and_primary_absence_are_distinct(self):
        self.assertEqual(b.assess_input('rw-codebook', None, now=NOW)['errors'],
                         ['input-metadata-missing'])
        self.assertEqual(b.assess_input('vn-composition', {}, now=NOW)['errors'],
                         ['qualified-primary-input-not-held'])
        for key in ('rw-participants', 'rw-recipes', 'us-recipes'):
            self.assertEqual(b.assess_input(key, None, now=NOW)['status'], 'held')
            with self.assertRaises(b.BindingError):
                b.authored_fixture(key, [rw_row()])

    def test_drift_and_untrusted_extra_metadata_fail_closed(self):
        for field, value in [('inputSha256', '0'*64), ('inputPath', '../private.csv'),
                             ('originalAcquiredAt', '2026-10-17T00:00:00Z'),
                             ('rightsEvidenceSha256', None)]:
            meta = b.metadata_template('rw-codebook'); meta[field] = value
            result = b.assess_input('rw-codebook', meta, now=NOW)
            self.assertEqual(result['status'], 'malformed-input')
        meta = b.metadata_template('th-table1'); meta['force'] = True
        self.assertEqual(b.assess_input('th-table1', meta, now=NOW)['errors'],
                         ['metadata-shape-invalid'])

    def test_current_validation_does_not_reset_original_age(self):
        meta = b.metadata_template('rw-codebook', validated_at='2026-11-20T00:00:00Z')
        result = b.assess_input('rw-codebook', meta, now='2026-11-20T00:00:00Z')
        self.assertEqual(result['status'], 'stale-input')
        self.assertGreater(result['originalAcquisitionAgeSeconds'], 30*86400)
        self.assertEqual(result['validationAgeSeconds'], 0)
        self.assertEqual(result['networkRequests'], 0)

    def test_exact_30day_boundary(self):
        acquired = b.SPECS['rw-codebook'].acquired_at
        from datetime import timedelta
        end = b.timestamp(acquired) + timedelta(days=30)
        self.assertEqual(b.assess_input('rw-codebook', b.metadata_template('rw-codebook'),
            now=(end-timedelta(microseconds=1)).isoformat())['status'], 'ready-for-binding-review')
        self.assertEqual(b.assess_input('rw-codebook', b.metadata_template('rw-codebook'),
            now=end.isoformat())['status'], 'stale-input')

    def test_noop_identity_ignores_validation_age_and_all_modes_stay_offline(self):
        meta = b.metadata_template('th-table1', validated_at='2026-10-17T00:00:00Z')
        identity = b.replay_intent('th-table1', meta, now=NOW)['identitySha256']
        meta['validatedAt'] = NOW
        for mode in ('reuse', 'refresh', 'revalidate', 'force-download'):
            result = b.replay_intent('th-table1', meta, now=NOW,
                                     previous_identity=identity, mode=mode)
            self.assertEqual(result['identitySha256'], identity)
            self.assertEqual(result['cacheIntent'], 'unchanged-binding-no-op')
            self.assertEqual(result['networkRequests'], 0)
            self.assertFalse(result['bytesVerifiedByThisPlan'])

    def test_timestamps_holds_and_errors_are_isolated_and_sanitized(self):
        meta = b.metadata_template('rw-codebook', validated_at='2099-01-01T00:00:00Z')
        results = b.assess_portfolio({'rw-codebook': meta,
            'th-table1': b.metadata_template('th-table1')}, now=NOW)
        self.assertEqual(results['rw-codebook']['errors'], ['evidence-time-invalid'])
        self.assertEqual(results['th-table1']['status'], 'ready-for-binding-review')
        held = b.metadata_template('th-table1'); held['activeHolds'] = ['SECRET_SOURCE_DETAIL']
        result = b.assess_input('th-table1', held, now=NOW)
        self.assertEqual(result['errors'], ['source-held'])
        self.assertNotIn('SECRET_SOURCE_DETAIL', json.dumps(result))
        self.assertEqual(b.assess_input('unknown', {}, now=NOW)['errors'], ['binding-unknown'])


class CliIngressRegressionTests(unittest.TestCase):
    def cli(self, raw):
        return subprocess.run([sys.executable, '-B', '-m',
            'offmenu.refresh.worker46_bindings', 'assess', '--now', NOW],
            input=raw, capture_output=True, timeout=5,
            cwd=Path(b.__file__).resolve().parents[2])

    def assert_invalid(self, result):
        self.assertEqual(result.returncode, 2, result.stderr)
        self.assertEqual(json.loads(result.stdout), {'error': 'portfolio-metadata-invalid'})
        self.assertEqual(result.stderr, b'')

    def test_sub64k_deep_json_returns_fixed_diagnostic(self):
        for depth in (10000, 30000):
            raw = b'{"rw-codebook":' + b'['*depth + b'0' + b']'*depth + b'}'
            self.assertLess(len(raw), 65536)
            with self.subTest(depth=depth):
                self.assert_invalid(self.cli(raw))

    def test_utf8_byte_budget_and_ascii_control(self):
        meta = {'rw-codebook': b.metadata_template('rw-codebook')}
        meta['rw-codebook']['validatedAt'] = '界'*24000
        text = json.dumps(meta, ensure_ascii=False)
        self.assertLess(len(text), 65536)
        self.assertGreater(len(text.encode('utf-8')), 65536)
        self.assert_invalid(self.cli(text.encode('utf-8')))
        # Encoded limits also apply to embedded callers using decoded text.
        output = StringIO()
        self.assertEqual(b.main(['assess', '--now', NOW],
            stdin=StringIO(text), stdout=output), 2)
        self.assertEqual(json.loads(output.getvalue()), {'error': 'portfolio-metadata-invalid'})
        meta['rw-codebook']['validatedAt'] = 'a'*60000
        control = self.cli(json.dumps(meta).encode())
        self.assertEqual(control.returncode, 0, control.stderr)
        self.assertEqual(json.loads(control.stdout)['rw-codebook']['errors'], ['evidence-time-invalid'])

    def test_exact_byte_boundary_and_invalid_utf8(self):
        at_limit = b'{}' + b' ' * 65534
        self.assertEqual(self.cli(at_limit).returncode, 0)
        self.assert_invalid(self.cli(at_limit + b' '))
        self.assert_invalid(self.cli(b'\xff'))
        output = StringIO()
        self.assertEqual(b.main(['assess', '--now', NOW],
            stdin=BytesIO(b'{}'), stdout=output), 0)


class SharedQualificationTests(unittest.TestCase):
    def test_rw_th_use_shared_qualification_without_promoting_real_scope(self):
        for key, rows in [('rw-codebook', [rw_row(1), rw_row(2)]),
                          ('th-table1', [th_row(), th_row(9, 6)])]:
            with self.subTest(key=key), tempfile.TemporaryDirectory() as directory:
                f = b.authored_fixture(key, rows)
                bundle, candidate = materialize(Path(directory), f)
                result = q.accept(f['contract'], bundle, candidate, f['manifest'])
                self.assertTrue(result['accepted'], result['errors'])
                self.assertEqual(result['status'], 'accepted-fixture-scope')
                self.assertFalse(result['productionAccepted'])
                self.assertFalse(result['countryCoverageComplete'])
                self.assertEqual(b.authored_fixture(key, rows)['candidate'], f['candidate'])
                self.assertEqual(rows[0], (rw_row(1) if key == 'rw-codebook' else th_row()))

    def test_all_scalars_include_source_or_policy_origin(self):
        f = b.authored_fixture('th-table1', [th_row(9, 6)])
        row = f['rows'][0]
        self.assertEqual(set(b.datum_pointers(row['data'])),
                         set(row['provenance']['fieldOrigins']))
        origins = row['provenance']['fieldOrigins']
        self.assertEqual(origins['/data/wetDryEdibleBasis']['kind'], 'constant')
        self.assertEqual(origins['/data/values/unitAndBasisLiteral']['kind'], 'derived')
        self.assertEqual(origins['/data/values/sampleCodeLiteral']['sourceField'],
                         '#table-1/thead/tr:2/th:5')
        self.assertEqual(origins['/data/values/meanLexeme']['inputs'][0]['sourceField'],
                         '#table-1/tbody/tr:7/td:6')
        self.assertEqual(row['data']['values']['unitAndBasisLiteral'], 'mg/kg')
        self.assertEqual(row['data']['values']['meanLexeme'], '0.00')
        self.assertIsNone(row['data']['values']['noteMarkerLiteral'])

    def test_missing_origin_and_semantic_unit_drift_both_report(self):
        f = b.authored_fixture('th-table1', [th_row()])
        row = deepcopy(f['rows'][0]); del row['provenance']['fieldOrigins']['/data/values/meanLexeme']
        row['data']['values']['unitAndBasisLiteral'] = 'mg/100 g'
        issues = f['contract'].semantic_validator(row)
        self.assertIn('field-origin-missing', issues)
        self.assertIn('portfolio-source-field-fidelity-mismatch', issues)

    def test_input_tampering_and_missing_assets_fail_generic_custody(self):
        for missing in (True, False):
            with self.subTest(missing=missing), tempfile.TemporaryDirectory() as directory:
                f = b.authored_fixture('rw-codebook', [rw_row()])
                bundle, candidate = materialize(Path(directory), f)
                if missing: (bundle/'rights.json').unlink()
                else: (bundle/'authored-input.json').write_bytes(b'corrupt')
                result = q.qualify(f['contract'], bundle, candidate, f['manifest'])
                self.assertFalse(result['qualified'])
                self.assertIn('input-custody-mismatch', result['errors'])

    def test_shared_operation_gate_is_not_bypassed_by_binding(self):
        with tempfile.TemporaryDirectory() as directory:
            f = b.authored_fixture('rw-codebook', [rw_row()])
            bundle, candidate = materialize(Path(directory), f)
            held = replace(f['contract'], holds=('authored-held-scope',))
            result = q.qualify(held, bundle, candidate, f['manifest'])
            self.assertFalse(result['qualified'])
            self.assertIn('source-held', result['errors'])

    def test_malformed_role_or_lexeme_is_not_silently_repaired(self):
        wrong = th_row(); wrong['values']['sampleCodeLiteral'] = 'B'
        with self.assertRaisesRegex(b.BindingError, '^table-row-column-role-mismatch$'):
            b.authored_fixture('th-table1', [wrong])
        wrong = th_row(); wrong['values']['meanLexeme'] = '99.00'
        with self.assertRaisesRegex(b.BindingError, '^table-cell-lexical-components-mismatch$'):
            b.authored_fixture('th-table1', [wrong])
        wrong = rw_row(); wrong['values']['Measurement'] = None
        with self.assertRaisesRegex(b.BindingError, '^source-field-shape-invalid$'):
            b.authored_fixture('rw-codebook', [wrong])

    def test_mutating_caller_fixture_cannot_change_contract_evidence(self):
        rows = [rw_row()]; f = b.authored_fixture('rw-codebook', rows)
        rows[0]['values']['Column'] = 'CHANGED_AFTER_BUILD'
        self.assertEqual(f['contract'].semantic_validator(f['rows'][0]), [])
        self.assertNotIn(b'CHANGED_AFTER_BUILD', f['contents']['authored-input.json'])


if __name__ == '__main__':
    unittest.main()
