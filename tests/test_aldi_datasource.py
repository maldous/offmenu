import unittest
import hashlib
import json
import tempfile
from pathlib import Path
from unittest.mock import patch

from offmenu.aldi_datasource import normalize, graph_packet, read_page, import_snapshot, register_snapshot


class AldiDatasourceTests(unittest.TestCase):
    def setUp(self):
        self.raw = {
            'source_store_id': '34925514', 'source_item_id': '000123',
            'market': 'AU', 'currency': 'AUD', 'name': 'Tomatoes',
            'price_amount_aud': .91, 'price_display_raw': 'A$0.91 per each',
            'price_basis': 'each', 'pack_size_raw': 'Estimated 0.14 kg • A$6.49/kg',
            'estimated_weight_price': True, 'stock_status': 'not_stated',
            'availability_badges_raw': [], 'store_address_public': '313 Victoria Street',
            'source_category_urls': ['https://www.doordash.com/convenience/store/34925514/category/produce-964'],
            'categories': ['Produce'], 'category_scope': 'food_or_beverage',
            'last_observed_at': '2026-10-16T01:33:00Z',
        }
        self.manifest = {'sourceStoreId': '34925514', 'releaseId': 'snapshot-1',
                         'upstreamManifestSha256': 'a' * 64, 'upstreamInventorySha256': 'b' * 64}

    def test_source_identity_and_unknowns_are_preserved(self):
        product, price = normalize(self.raw, self.manifest, 17)
        self.assertTrue(product['id'].endswith(':34925514:000123'))
        self.assertEqual(product['data']['identifiers'], [{'system': 'DoorDash-store-item', 'value': '34925514:000123'}])
        self.assertIsNone(product['data']['nutritionId'])
        self.assertIsNone(product['data']['allergens'])
        self.assertEqual(product['data']['ingredientMappingStatus'], 'unresolved')
        self.assertEqual(price['data']['productId'], product['id'])
        self.assertEqual(price['provenance']['originalRecord']['line'], 17)
        self.assertEqual(price['provenance']['visibility'], 'local-restricted')

    def test_estimated_each_price_is_not_per_kg(self):
        product, price = normalize(self.raw, self.manifest, 1)
        self.assertEqual(price['data']['amount'], .91)
        self.assertEqual(price['data']['basis']['per'], 'each')
        self.assertTrue(price['data']['basis']['estimatedWeight'])
        self.assertIsNone(price['data']['unitPrice'])
        self.assertIsNone(product['data']['pack']['unit'])
        self.assertEqual(product['data']['pack']['label'], self.raw['pack_size_raw'])

    def test_unknown_and_out_of_stock_stay_distinct(self):
        self.assertEqual(normalize(self.raw, self.manifest, 1)[1]['data']['availability'], 'unknown')
        raw = {**self.raw, 'stock_status': 'out_of_stock'}
        self.assertEqual(normalize(raw, self.manifest, 1)[1]['data']['availability'], 'out-of-stock')

    def test_recapture_keeps_product_identity_but_versions_price(self):
        old = normalize(self.raw, self.manifest, 1)
        new = normalize(self.raw, {**self.manifest, 'releaseId': 'snapshot-2'}, 1)
        self.assertEqual(old[0]['id'], new[0]['id'])
        self.assertNotEqual(old[1]['id'], new[1]['id'])

    def test_invalid_market_and_price_fail(self):
        for change in ({'market': 'US'}, {'price_amount_aud': float('nan')}, {'price_amount_aud': True}):
            with self.assertRaises(ValueError): normalize({**self.raw, **change}, self.manifest, 1)

    def test_graph_preserves_identifier_type_and_local_scope(self):
        product = normalize(self.raw, self.manifest, 1)[0]
        packet = graph_packet(product)
        self.assertEqual(packet['resources'][0]['identityStatus'], 'source-scoped')
        self.assertEqual(packet['citations'][0]['scope']['visibility'], 'local-restricted')
        identity = next(a for a in packet['assertions'] if a['sourcePath'] == 'id')
        self.assertEqual(identity['value'], {'kind': 'identifier', 'value': product['id']})

    def test_page_bound_is_checked_before_io(self):
        for offset, limit in ((-1, 25), (0, 26), (0, 0)):
            with self.assertRaises(ValueError): read_page('/does/not/exist', offset=offset, limit=limit)

    def capture_fixture(self, root, rows=None):
        capture = root / 'capture'
        capture.mkdir()
        rows = rows or [self.raw]
        (capture / 'inventory.jsonl').write_text(''.join(json.dumps(r) + '\n' for r in rows))
        (capture / 'category-coverage.json').write_text(json.dumps([{'name': 'Produce', 'displayed_result_counts': [len(rows)]}]))
        meta = {'source_store_id': '34925514', 'products': len(rows), 'capture_ended_utc': self.raw['last_observed_at'],
                'files': {name: {'sha256': hashlib.sha256((capture / name).read_bytes()).hexdigest()}
                          for name in ('inventory.jsonl', 'category-coverage.json')}}
        (capture / 'manifest.json').write_text(json.dumps(meta))
        return capture

    def test_import_register_lookup_and_tamper_detection(self):
        with tempfile.TemporaryDirectory() as tmp, patch.dict('os.environ', {'OFFMENU_DATA_ROOT': tmp}):
            root = Path(tmp)
            capture = self.capture_fixture(root)
            output = root / 'normalized'
            manifest = import_snapshot(capture, output)
            self.assertEqual(manifest['counts'], {'product': 1, 'priceObservation': 1, 'retailer': 1})
            register_snapshot(output)
            self.assertEqual(read_page('aldi-doordash-au', query='tomato')['pagination']['total'], 1)
            self.assertEqual(read_page('aldi-doordash-au', kind='priceObservation', food_only=True)['pagination']['total'], 1)
            self.assertEqual(read_page('aldi-doordash-au', offset=1)['records'], [])
            with (output / 'records.sqlite').open('ab') as f: f.write(b'changed')
            with self.assertRaisesRegex(ValueError, 'snapshot changed'): read_page('aldi-doordash-au')

    def test_changed_capture_fails_before_creating_output(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); capture = self.capture_fixture(root); output = root / 'normalized'
            with (capture / 'inventory.jsonl').open('a') as f: f.write('\n')
            with self.assertRaisesRegex(ValueError, 'checksum mismatch'): import_snapshot(capture, output)
            self.assertFalse(output.exists())

    def test_duplicate_source_identity_fails_before_creating_output(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); capture = self.capture_fixture(root, [self.raw, self.raw]); output = root / 'normalized'
            with self.assertRaisesRegex(ValueError, 'Duplicate capture source identity'): import_snapshot(capture, output)
            self.assertFalse(output.exists())


if __name__ == '__main__':
    unittest.main()
