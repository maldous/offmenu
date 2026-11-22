import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

from offmenu.refresh import barcode_validation as v


class ValidationTests(unittest.TestCase):
    def product(self, code='012345678905', **data):
        return {'id':'generated:product:1', 'kind':'product',
                'data':{'identifiers':[{'system':'barcode','value':code}], **data},
                'provenance':{'sourceId':'generated', 'releaseId':'fixture', 'recordId':'1'}}

    def test_leading_zero_and_typed_alias(self):
        result = v.identifier('012345678905', symbology='UPC-A')
        self.assertEqual(result['state'], 'valid')
        self.assertEqual(result['originalLexicalValue'], '012345678905')
        self.assertEqual(result['aliases'][0]['value'], '0012345678905')
        self.assertFalse(result['physicalIdentityEstablished'])

    def test_checksum_invalid_and_numeric_identifier_not_coerced(self):
        self.assertEqual(v.identifier('012345678906')['state'], 'invalid')
        self.assertEqual(v.identifier(12345678905)['reason'], 'identifier-not-lexical-string')

    def test_upce_is_explicit_and_ambiguous_eight_digits_not_expanded(self):
        # Generated valid UPC-E: expanded 012000003455, check digit5.
        result = v.identifier('01234505', symbology='UPC-E')
        self.assertEqual(result['state'], 'valid')
        self.assertEqual(result['aliases'][0]['value'], '012000003455')
        self.assertFalse(any(a['derivation']=='explicit-upc-e-to-upc-a'
                             for a in v.identifier('01234505')['aliases']))

    def test_package_and_edition_types_do_not_merge(self):
        for value, kind in [('10012345678902','ITF-14'), ('0306406152','ISBN-10'), ('9780306406157','ISBN-13')]:
            self.assertEqual(v.identifier(value, symbology=kind)['state'], 'valid')
            self.assertEqual(v.identifier(value, symbology=kind)['aliases'], [])
        self.assertEqual(v.identifier('012345678905', symbology='EAN-13')['state'], 'invalid')

    def test_reference_namespace_excluded_and_unknown_unresolved(self):
        self.assertEqual(v.identifier('123', 'USDA-FDC')['state'], 'excluded-reference-namespace')
        self.assertEqual(v.identifier('opaque-code')['state'], 'unresolved')

    def test_trace_malformed_negative_nonfinite_and_unknown_basis(self):
        basis = {'amount':100, 'unit':'g'}
        for raw, reason in [('Tr','trace-not-quantified'), ('x','invalid-numeric-amount'), (-1,'invalid-numeric-amount'), ('NaN','invalid-numeric-amount'), (True,'invalid-amount-type')]:
            result = v.nutrient(raw, 'g', basis)
            self.assertEqual(result['reason'], reason)
            self.assertEqual(result['sourceAmount'], raw)
            self.assertIsNone(result['value'])
        self.assertEqual(v.nutrient(0, 'g', basis)['value'], '0')
        self.assertEqual(v.nutrient(1, 'g', None)['state'], 'unknown')

    def test_trace_does_not_suppress_product_and_no_raw_mutation(self):
        row = self.product(nutriments={'proteins_100g':'Tr', 'fat_100g':'3.5'}, nutrition_data_per='100g')
        before = copy.deepcopy(row)
        result = v.normalize_record(row, '/fixture/0')
        self.assertEqual(result['state'], 'lookup-visible')
        self.assertEqual(result['nutrients']['proteins_100g']['state'], 'unknown')
        self.assertEqual(result['nutrients']['fat_100g']['value'], '3.5')
        self.assertEqual(row, before)

    def test_names_source_categories_nonfood_and_unknown_mapping_survive(self):
        row = self.product(product_name_fr='Chaussure', categories_tags=['fr:chaussures'], lang='fr')
        result = v.normalize_record(row, '/fixture')
        self.assertEqual(result['names'], {'fr':'Chaussure'})
        self.assertEqual(result['sourceCategories']['categories_tags'], ['fr:chaussures'])
        self.assertEqual(result['state'], 'lookup-visible')
        self.assertEqual(result['foodApplicability']['state'], 'unknown')
        self.assertEqual(result['ingredientMapping']['state'], 'unknown')
        self.assertFalse(result['goldAdmitted'])

    def test_assertion_rows_are_not_missing_source_detail_evidence(self):
        result = v.normalize_record({'lexical_value':'012345678905','namespace':'barcode'}, '/assertion/1')
        self.assertEqual(result['state'], 'lookup-visible')
        self.assertEqual(result['name']['state'], 'not-projected')
        self.assertEqual(result['name']['reason'], 'source-absence-not-established')

    def test_collisions_preserve_both_observations_without_physical_merge(self):
        rows, counts = v.validate_records([('/a', self.product()),('/b', self.product())])
        self.assertEqual(counts['records'], 2)
        self.assertTrue(all(r['collisionDisposition']['observationCount']==2 for r in rows))
        self.assertTrue(all(r['collisionDisposition']['physicalMerge'] is False for r in rows))

    def test_unqualified_image_is_not_copied_or_fetched(self):
        result = v.normalize_record(self.product(image_url='https://invalid.example/image.jpg'), '/fixture')
        self.assertEqual(result['images'], [])
        self.assertEqual(result['imageAvailability'], 'not-projected-or-not-qualified')

    def operation(self, root, record=None):
        row = record or self.product()
        document = {'lookup':{'matches':[{'nativeProductId':row['id'], 'sourceRecordId':'1','record':row}]}}
        raw = v.canonical(document)
        path = root/'selected-fixture.json'
        path.write_bytes(raw)
        return {'version':v.VERSION, 'format':'private-native-lookup-json',
                'selectionReference':'generated-fixture-only', 'sourceId':'generated','releaseId':'fixture',
                'source':{'path':str(path),'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()},
                'expectedRecords':1, 'limits':{'maxInputBytes':1000000,'maxRecords':1000,'maxOutputBytes':1000000,'maxSeconds':30}}

    def test_repeat_is_idempotent_and_output_digest_guarded(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); op=self.operation(root)
            first=v.execute(op, root/'output'); second=v.execute(op, root/'output')
            self.assertEqual(first['generation'], second['generation'])
            self.assertTrue(second['reused'])
            self.assertFalse(first['allHeldInventoryComplete'])
            (root/'output'/first['generation']/'projection.jsonl').write_text('corrupt')
            with self.assertRaisesRegex(ValueError, 'existing-projection-digest-mismatch'):
                v.execute(op, root/'output')

    def test_missing_selection_hash_drift_wrong_binding_and_budget_fail_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);op=self.operation(root)
            bad=copy.deepcopy(op);bad['selectionReference']=None
            with self.assertRaisesRegex(ValueError,'selection-required'):v.execute(bad,root/'out1')
            bad=copy.deepcopy(op);bad['source']['sha256']='0'*64
            with self.assertRaisesRegex(ValueError,'digest-mismatch'):v.execute(bad,root/'out2')
            bad=copy.deepcopy(op);bad['sourceId']='wrong'
            with self.assertRaisesRegex(ValueError,'source-binding-mismatch'):v.execute(bad,root/'out3')
            bad=copy.deepcopy(op);bad['limits']['maxOutputBytes']=1
            with self.assertRaisesRegex(ValueError,'budget-exceeded'):v.execute(bad,root/'out4')


if __name__ == '__main__':
    unittest.main()
