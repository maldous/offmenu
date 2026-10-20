"""Generated sources only; no retained corpus or environment-bound witness reads."""
from copy import deepcopy
from dataclasses import asdict, replace
import hashlib
import json
import unittest
from unittest.mock import patch

from jsonschema import Draft202012Validator
import test_product_adapters as fixtures
from offmenu.refresh import usda_product_contract as binding
from offmenu.refresh.acceptance import canonical, fingerprint
from offmenu.refresh.product_adapters import ProductContext, ProductLimits, normalize_products
from offmenu.refresh.product_clock import validate_contract_clock


class UsdaProductContractTest(unittest.TestCase):
    def setUp(self):
        self.f = fixtures.ProductAdaptersTest()
        self.f.setUp()
        self.addCleanup(self.f.tearDown)
        # Synthetic test envelope only, never an actual output-capacity selection.
        self.limits = ProductLimits(max_input_bytes=1024**3, max_expanded_bytes=4*1024**3,
                                    max_rows=binding.RAW_ROWS)
        self.contract = binding.usda_20260430_contract(limits=self.limits)
        self.docs = binding.evidence_documents()
        c = self.contract
        context = ProductContext(c.source_id, c.release_id, c.acquired_at,
            binding.LICENSE, binding.ATTRIBUTION, c.rights_evidence.sha256,
            c.scope_evidence.sha256, acquisition_clock_status=c.acquisition_clock_status,
            clock_evidence_sha256=c.clock_evidence.sha256)
        self.context = context
        normalize_products(context, {'archive': self.f.archive()}, self.f.root/'output')
        self.records = self.f.records()
        # Model fixed-source provenance in generated record fixtures. The actual
        # archive pin is checked by the bridge, never claimed for this tiny ZIP.
        for row in self.records:
            row['provenance']['inputSha256'] = {'archive': binding.SOURCE.sha256}

    def errors(self, row):
        return (list(Draft202012Validator(self.contract.schemas[row['kind']]).iter_errors(row)),
                self.contract.semantic_validator(row))

    def test_all_generated_projector_records_pass_complete_schema_and_semantics(self):
        for row in self.records:
            with self.subTest(kind=row['kind']):
                schema, semantic = self.errors(row)
                self.assertEqual(schema, [])
                self.assertEqual(semantic, [])
        nutrients = self.records[1]['data']['nutrients']
        self.assertEqual(nutrients['protein']['sourceAmount'], '2.30')
        self.assertEqual(nutrients['protein:observation:12']['value'], 2.4)
        self.assertEqual(self.records[0]['data']['identifiers'][1]['value'], '00012345')

    def test_factory_pins_actual_independent_native_scope_not_raw_or_gtin_counts(self):
        c = self.contract
        self.assertEqual(c.expected_records, 4202558)
        self.assertEqual(c.expected_ids_sha256,
                         '2d5be06c4e3be042b4bed583a5ada885066188b901aa3b23f7a9dc48a1472f0f')
        self.assertNotEqual(c.expected_records, binding.RAW_ROWS)
        self.assertNotEqual(c.expected_records, 1999950)
        self.assertEqual(c.max_records, c.expected_records)
        self.assertFalse(c.fixture)
        self.assertEqual(c.output_scope, 'native')
        self.assertEqual(c.output_visibility, 'private')
        self.assertIsNone(c.acquired_at)
        self.assertEqual(c.acquisition_clock_status, 'unknown-retained')
        self.assertEqual(c.inputs[0], binding.SOURCE)
        self.assertEqual(c.permitted_operations, frozenset(('retain', 'parse', 'transform')))
        with self.assertRaises(TypeError):
            binding.usda_20260430_contract(limits=self.limits, expected_records=2)

    def test_deterministic_evidence_hashes_and_clock_binding_without_source_body(self):
        bundle = self.f.root/'evidence'
        bundle.mkdir()
        for name, doc in self.docs.items():
            (bundle/name).write_bytes(canonical(doc))
        self.assertEqual(self.docs, binding.evidence_documents())
        for a in (self.contract.scope_evidence, self.contract.clock_evidence):
            raw = (bundle/a.path).read_bytes()
            self.assertEqual((len(raw), hashlib.sha256(raw).hexdigest()), (a.bytes, a.sha256))
        # Clock validator reads only clock/scope; no original/evidence materialization.
        validate_contract_clock(self.contract, bundle)
        scope = self.docs['usda-product-scope.json']
        self.assertEqual(scope['independentWitnessSha256'], binding.WITNESS_SHA256)
        self.assertEqual(scope['independentReviewSha256'], binding.WITNESS_REVIEW_SHA256)
        self.assertEqual(scope['schemasSha256'], self.contract.schemas_sha256)
        self.assertEqual(scope['semanticPolicySha256'], self.contract.policy_sha256)
        self.assertFalse(scope['goldAdmitted'])

    def test_full_source_limits_are_required_and_not_chosen_implicitly(self):
        with self.assertRaises(TypeError):
            binding.usda_20260430_contract()
        with self.assertRaises(ValueError):
            binding.usda_20260430_contract(limits=None)
        for change in [dict(max_rows=binding.RAW_ROWS-1), dict(max_expanded_bytes=binding.EXPANDED_BYTES-1),
                       dict(max_input_bytes=binding.SOURCE.bytes)]:
            with self.subTest(change=change):
                with self.assertRaisesRegex(ValueError, 'limits-too-small'):
                    binding.usda_20260430_contract(limits=replace(self.limits, **change))

    def test_schema_requires_every_projected_field_and_rejects_unselected_extras(self):
        for original in self.records:
            for field in original['data']:
                row = deepcopy(original)
                del row['data'][field]
                with self.subTest(kind=row['kind'], missing=field):
                    self.assertTrue(self.errors(row)[0])
            row = deepcopy(original)
            row['data']['inventedCanonicalMeaning'] = 'not selected'
            self.assertTrue(self.errors(row)[0])

    def test_identity_and_fdc_nutrition_reference_are_not_gtin_identity(self):
        for kind, field, value in [('product','id','usda-files:product:00012345'),
                                    ('product','nutritionId','usda-files:nutrientProfile:wrong')]:
            row = deepcopy(self.records[0])
            if field == 'id':
                row[field] = value
            else:
                row['data'][field] = value
            self.assertTrue(self.errors(row)[1])
        row = deepcopy(self.records[0])
        row['data']['identifiers'][0]['value'] = '00012345'
        self.assertIn('usda-native-identifiers', self.errors(row)[1])

    def test_rights_scope_release_acquisition_and_transform_cannot_drift(self):
        for key, value in [('rightsEvidenceSha256','f'*64), ('scopeEvidenceSha256','f'*64),
                           ('fetchedAt','2026-04-30T00:00:00Z'), ('releaseId','2026-04'),
                           ('transform','other'), ('visibility','public'),
                           ('inputSha256',{'archive':'f'*64}), ('sourceRow',0)]:
            row = deepcopy(self.records[0]);row['provenance'][key] = value
            with self.subTest(key=key):
                self.assertTrue(any(self.errors(row)))
        row = deepcopy(self.records[0])
        row['provenance']['acquisitionClock']['evidenceSha256'] = 'f'*64
        self.assertIn('usda-native-provenance', self.errors(row)[1])

    def test_source_amount_numeric_view_units_and_raw_lineage_must_match(self):
        for field, value in [('value',99), ('sourceAmount','99'), ('unit','mg'),
                             ('sourceRowId','wrong'), ('sourceNutrientId','1004')]:
            row = deepcopy(self.records[1]);row['data']['nutrients']['protein'][field] = value
            with self.subTest(field=field):
                self.assertTrue(self.errors(row)[1])
        row = deepcopy(self.records[1]);row['data']['nutrients']['protein']['rawFields']['fdc_id'] = 'other'
        self.assertIn('usda-native-observation-lineage', self.errors(row)[1])

    def test_blank_is_null_zero_is_zero_and_nonfinite_is_rejected(self):
        for amount, expected in [('',None), ('0',0.0), ('-0.25',-0.25)]:
            row = deepcopy(self.records[1]);n = row['data']['nutrients']['protein']
            n['sourceAmount'] = n['rawFields']['amount'] = amount;n['value'] = expected
            self.assertEqual(self.errors(row)[1], [])
        for amount in ['NaN','Infinity','not numeric']:
            row = deepcopy(self.records[1]);n = row['data']['nutrients']['protein']
            n['sourceAmount'] = n['rawFields']['amount'] = amount;n['value'] = None
            self.assertTrue(self.errors(row)[1])
        row = deepcopy(self.records[1]);row['data']['nutrients']['protein']['value'] = True
        self.assertTrue(any(self.errors(row)))

    def test_duplicate_observations_preserved_and_duplicate_source_rows_rejected(self):
        row = deepcopy(self.records[1]);n = row['data']['nutrients']['protein:observation:12']
        n['sourceRowId'] = n['rawFields']['id'] = '11'
        self.assertIn('usda-native-observation-identity', self.errors(row)[1])

    def test_unknown_units_and_unknown_nutrients_remain_source_assertions(self):
        row = deepcopy(self.records[1]);n = row['data']['nutrients'].pop('protein')
        n['sourceNutrientId'] = n['rawFields']['nutrient_id'] = '999999'
        n['sourceUnit'] = 'SOURCE_UNRESOLVED';n['unit'] = 'source_unresolved'
        row['data']['nutrients']['usda:999999'] = n
        self.assertEqual(self.errors(row), ([], []))

    def test_changed_basis_or_added_clinical_interpretation_is_rejected(self):
        row = deepcopy(self.records[1]);row['data']['basis']['amount'] = 1
        self.assertTrue(any(self.errors(row)))
        row = deepcopy(self.records[1]);row['data']['nutrients']['protein']['clinicalSafe'] = True
        self.assertTrue(self.errors(row)[0])

    def test_origin_schema_allows_only_later_wrapper_to_verify_origin_values(self):
        row = deepcopy(self.records[0]);row['provenance']['fieldOrigins'] = {}
        self.assertEqual(self.errors(row), ([], []))
        # Empty origins are not established complete by native schema/policy.
        from offmenu.refresh.field_provenance import field_origin_errors
        self.assertTrue(field_origin_errors(row, {}))

    def test_adapter_pin_drift_blocks_contract_construction(self):
        with patch.object(binding, 'ADAPTER_SHA256', 'f'*64):
            with self.assertRaisesRegex(ValueError, 'adapter-pin-mismatch'):
                binding.usda_20260430_contract(limits=self.limits)

    def test_bad_structure_returns_fixed_diagnostics_without_source_values(self):
        self.assertEqual(self.contract.semantic_validator({'private': 'SECRET'}), ['usda-native-record-invalid'])
        self.assertEqual(fingerprint(self.contract.schemas), self.contract.schemas_sha256)


if __name__ == '__main__':
    unittest.main()
