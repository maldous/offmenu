"""Synthetic, retained-format fixtures; no downloads or admissions."""
from dataclasses import replace
import json
import sqlite3
import unittest
from unittest.mock import patch

import test_product_adapters as fixtures
from offmenu.refresh.core import RefreshError, canonical
from offmenu.refresh.field_provenance import field_origin_errors
from offmenu.refresh.product_adapters import normalize_products, ProductLimits
from offmenu.refresh.product_field_origins import ProductOriginEmitter


class ProductFieldOriginsTest(unittest.TestCase):
    def setUp(self):
        self.fixture = fixtures.ProductAdaptersTest()
        self.fixture.setUp()
        self.addCleanup(self.fixture.tearDown)

    def prepare(self, source='off', inputs=None, members=None, **kwargs):
        f = self.fixture
        context = replace(f.context, source_id=source)
        inputs = inputs or {'products': f.off(**kwargs)}
        manifest = normalize_products(context, inputs, f.root / 'output')
        db = sqlite3.connect(f.root / 'output/source.sqlite')
        self.addCleanup(db.close)
        pins = {i['role']: {'path': 'retained/' + i['path'], 'sha256': i['sha256']} for i in manifest['inputFiles']}
        emitter = ProductOriginEmitter(context, db, pins, members=members)
        return emitter, f.records()

    def assert_covered(self, e, rows):
        results = [e.emit(row) for row in rows]
        for row in results:
            self.assertEqual(field_origin_errors(row, e.pins, policy_pins=[e.policy]), [])
        return results

    def test_off_complete_replay_and_preserved_raw_pointers(self):
        e, rows = self.prepare(nutriments={'proteins_100g': 0, 'a/b~c': {'x': [None, 2]}})
        result = self.assert_covered(e, rows)
        self.assertEqual(canonical(result), canonical([e.emit(row) for row in rows]))
        origin = result[0]['provenance']['fieldOrigins']['/data/rawNutriments/a~1b~0c/x/0']
        self.assertEqual(origin['sourceField'], '/nutriments/a~1b~0c/x/0')
        self.assertEqual(origin['line'], 1)
        self.assertEqual(origin['inputPath'], 'retained/products.gz')
        self.assertNotIn('fieldOrigins', rows[0]['provenance'])

    def test_off_missing_nulls_are_constants_not_fake_cells(self):
        e, rows = self.prepare()
        origins = self.assert_covered(e, rows)[0]['provenance']['fieldOrigins']
        self.assertEqual(origins['/data/brand']['kind'], 'constant')
        self.assertNotIn('sourceField', origins['/data/brand'])
        self.assertEqual(origins['/data/qualificationStatus']['kind'], 'constant')

    def test_off_explicit_null_is_source(self):
        e, rows = self.prepare(brands=None)
        self.assertEqual(self.assert_covered(e, rows)[0]['provenance']['fieldOrigins']['/data/brand']['kind'], 'source')

    def test_off_category_present_null_missing_and_nested_source_pointers(self):
        e, rows = self.prepare(categories=None, categories_tags=['fr:Original', 'en:Other'],
            categories_properties={'a/b~c': {'values': [None, False, '0007']}},
            lang='fr', categories_taxonomy_version='source-v0',
            categories_contributor_email='DO NOT PROJECT')
        product = self.assert_covered(e, rows)[0]
        values = product['data']['sourceCategoryFields']
        origins = product['provenance']['fieldOrigins']
        self.assertIsNone(values['categories'])
        self.assertNotIn('food_groups', values)
        self.assertNotIn('categories_contributor_email', values)
        self.assertEqual(origins['/data/sourceCategoryFields/categories']['sourceField'], '/categories')
        self.assertEqual(origins['/data/sourceCategoryFields/categories']['kind'], 'source')
        self.assertEqual(origins['/data/sourceCategoryFields/categories_tags/1']['sourceField'], '/categories_tags/1')
        for index in range(3):
            pointer = '/data/sourceCategoryFields/categories_properties/a~1b~0c/values/' + str(index)
            self.assertEqual(origins[pointer]['sourceField'], '/categories_properties/a~1b~0c/values/' + str(index))
            self.assertEqual(origins[pointer]['line'], 1)
        self.assertEqual(origins['/data/sourceCategoryFields/categories_taxonomy_version']['sourceField'],
                         '/categories_taxonomy_version')
        self.assertFalse(any(p.startswith('/data/sourceCategoryFields/food_groups') for p in origins))
        evidence = product['provenance']['sourceCategoryFields']['fields']
        self.assertEqual(evidence['categories']['state'], 'null')
        self.assertEqual(evidence['food_groups'], {'state': 'missing', 'sourcePointer': None})

    def test_off_forged_category_values_or_provenance_cannot_gain_origins(self):
        e, rows = self.prepare(categories_tags=['fr:Original'])
        rows[0]['data']['sourceCategoryFields']['categories_contributor_profile'] = 'DO NOT PROJECT'
        with self.assertRaisesRegex(RefreshError, 'projection-mismatch'):
            e.emit(rows[0])
        del rows[0]['data']['sourceCategoryFields']['categories_contributor_profile']
        rows[0]['provenance']['sourceCategoryFields']['fields']['categories_tags']['sourcePointer'] = '/owner'
        with self.assertRaisesRegex(RefreshError, 'category-evidence-mismatch'):
            e.emit(rows[0])

    def test_adapter_pin_check_remains_fail_closed(self):
        e, _ = self.prepare()
        with patch('offmenu.refresh.product_field_origins.ADAPTER_SHA256', '0'*64):
            with self.assertRaisesRegex(RefreshError, 'adapter-pin-mismatch'):
                ProductOriginEmitter(e.context, e.db, e.inputs)

    def test_off_name_barcode_fallback_and_ml_basis(self):
        e, rows = self.prepare(product_name='', nutrition_data_per='100ml')
        result = self.assert_covered(e, rows)
        self.assertEqual(result[0]['provenance']['fieldOrigins']['/data/name']['kind'], 'derived')
        self.assertEqual(result[1]['data']['basis']['unit'], 'ml')

    def test_prices_complete_join_and_no_proof_private_fields(self):
        e, rows = self.prepare('prices', self.fixture.prices())
        out = self.assert_covered(e, rows)[0]
        origin = out['provenance']['fieldOrigins']['/data/retailer/name']
        self.assertEqual([v.get('sourceField') for v in origin['inputs']], ['/location_id', '/id', '/osm_name'])
        self.assertEqual(origin['inputs'][2]['inputPath'], 'retained/locations.gz')
        self.assertNotIn('PRIVATE', json.dumps(out))
        self.assertEqual(out['provenance']['fieldOrigins']['/data/proofId']['sourceField'], '/proof_id')

    def test_prices_no_location_and_invalid_promotion(self):
        e, rows = self.prepare('prices', self.fixture.prices(location_id=None, price_is_discounted='yes'))
        out = self.assert_covered(e, rows)[0]
        self.assertIsNone(out['data']['promotion'])
        self.assertEqual(out['provenance']['fieldOrigins']['/data/retailer/name']['inputs'][-1]['kind'], 'constant')

    def usda(self, **kwargs):
        return self.prepare('usda-files', {'archive': self.fixture.archive(**kwargs)},
            members={table: 'FoodData_Central/' + table + '.csv' for table in ['food','branded_food','food_nutrient','nutrient']})

    def test_usda_complete_all_join_coordinates_and_duplicate_observations(self):
        e, rows = self.usda()
        out = self.assert_covered(e, rows)[1]
        origins = out['provenance']['fieldOrigins']
        origin = origins['/data/nutrients/protein/value']
        self.assertEqual([v['table'] for v in origin['inputs']], ['food','food_nutrient','food_nutrient','nutrient','food_nutrient'])
        unit = origins['/data/nutrients/protein/unit']['inputs'][-1]
        self.assertEqual(unit['archiveMember'], 'FoodData_Central/nutrient.csv')
        self.assertEqual(unit['sourceField'], '/unit_name')
        duplicate = origins['/data/nutrients/protein:observation:12/sourceRowId']['inputs'][-1]
        self.assertEqual(duplicate['row'], 2)
        self.assertEqual(duplicate['sourceRecordId'], 'FoodData_Central/food_nutrient.csv:row:2')

    def test_usda_multiline_cell_uses_logical_rows(self):
        e, rows = self.usda(overrides={'food': [['fdc_id','description','data_type'], ['1','line one\nline two','branded_food']]})
        origin = self.assert_covered(e, rows)[0]['provenance']['fieldOrigins']['/data/name']
        self.assertEqual(origin['row'], 1)
        self.assertEqual(origin['coordinateSystem'], 'csv-logical-data-row')
        self.assertNotIn('line', origin)

    def test_usda_missing_member_is_explicit_error(self):
        e, rows = self.usda()
        e.members = {}
        with self.assertRaisesRegex(RefreshError, 'archive-member-required'):
            e.emit(rows[0])

    def test_unsupported_or_changed_fields_fail_closed(self):
        e, rows = self.prepare()
        rows[0]['data']['newField'] = 1
        with self.assertRaisesRegex(RefreshError, 'projection-mismatch'):
            e.emit(rows[0])

    def test_wrong_context_rejected(self):
        e, rows = self.prepare()
        rows[0]['provenance']['releaseId'] = 'other'
        with self.assertRaisesRegex(RefreshError, 'context-mismatch'):
            e.emit(rows[0])

    def test_source_database_drift_rejected(self):
        e, rows = self.prepare()
        e.db.execute("UPDATE raw SET body=replace(body, 'Example', 'Changed') WHERE tab='products'")
        with self.assertRaisesRegex(RefreshError, 'projection-mismatch'):
            e.emit(rows[0])

    def test_origin_expansion_bound(self):
        e, rows = self.prepare()
        e.limits = replace(ProductLimits(), max_line_bytes=1000)
        with self.assertRaisesRegex(RefreshError, 'output-bound'):
            e.emit(rows[0])

    def test_unknown_kind_rejected(self):
        e, rows = self.prepare()
        rows[0]['kind'] = 'unknown'
        with self.assertRaisesRegex(RefreshError, 'unsupported-kind'):
            e.emit(rows[0])

    def test_unsafe_input_pin_rejected(self):
        e, rows = self.prepare()
        with self.assertRaisesRegex(RefreshError, 'input-contract-invalid'):
            ProductOriginEmitter(e.context, e.db, {'products': {'path': '../products.gz', 'sha256': 'a'*64}})

    def test_nutrient_bounds_fail_closed(self):
        e, rows = self.usda()
        e.limits = replace(ProductLimits(), max_nutrients_per_food=1)
        with self.assertRaisesRegex(RefreshError, 'nutrient-bound'):
            e.emit(rows[1])


if __name__ == '__main__':
    unittest.main()
