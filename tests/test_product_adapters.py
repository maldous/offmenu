"""Tiny generated fixtures only; never fetch retained bulk source data."""
from dataclasses import replace
import csv
import gzip
import io
import json
from pathlib import Path
import sqlite3
import struct
import tempfile
import unittest
import zipfile

from offmenu.refresh.core import RefreshError
from offmenu.refresh.product_adapters import ProductContext, ProductLimits, normalize_products


class ProductAdaptersTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.context = ProductContext('off', 'fixture-release', '2026-10-12T00:00:00Z',
                                      'fixture terms', 'fixture publisher', 'a'*64, 'b'*64)

    def tearDown(self):
        self.temp.cleanup()

    def lines(self, name, rows):
        path = self.root / name
        with gzip.open(path, 'wb') as out:
            for row in rows:
                out.write((json.dumps(row) + '\n').encode())
        return path

    def off(self, **extra):
        return self.lines('products.gz', [{'code': '001234', 'product_name': 'Example',
            'countries_tags': ['en:france', 'en:germany'], 'nutrition_data_per': '100g',
            'nutriments': {'proteins_100g': 2.3, 'sodium_100g': 0.1}, **extra}])

    def records(self, dest='output'):
        return [json.loads(s)[0] for s in (self.root / dest / 'candidate.jsonl').read_text().splitlines()]

    def run_off(self, path=None, **kwargs):
        return normalize_products(self.context, {'products': path or self.off()}, self.root / 'output', **kwargs)

    def archive(self, overrides=None):
        tables = {
            'food': [['fdc_id','description','data_type','publication_date'], ['1','Sample','branded_food','2026-04-01']],
            'branded_food': [['fdc_id','gtin_upc','market_country','serving_size','serving_size_unit'], ['1','00012345','US','30','g']],
            'nutrient': [['id','name','unit_name'], ['1003','Protein','G']],
            'food_nutrient': [['id','fdc_id','nutrient_id','amount'], ['11','1','1003','2.30'], ['12','1','1003','2.40']],
            'food_attribute': [['id','fdc_id','value'], ['a','1','original \"quoted\",\nmultiline value']],
        }
        tables.update(overrides or {})
        path = self.root / 'fdc.zip'
        with zipfile.ZipFile(path, 'w', zipfile.ZIP_DEFLATED) as out:
            for table, rows in tables.items():
                s = io.StringIO(newline='')
                csv.writer(s).writerows(rows)
                out.writestr('FoodData_Central/' + table + '.csv', s.getvalue())
            out.writestr('README.txt', 'Synthetic support asset retained in input')
        return path

    def prices(self, **changes):
        row = {'id': 1, 'product_code': '00123', 'price': '2.50', 'currency': 'EUR',
               'date': '2026-10-01', 'location_id': 2, 'proof_id': 3,
               'owner': 'PRIVATE CONTRIBUTOR', **changes}
        return {'prices': self.lines('prices.gz', [row]),
                'locations': self.lines('locations.gz', [{'id': 2, 'osm_name': 'Shop', 'osm_address_country_code': 'fr', 'owner': 'PRIVATE LOCATION'}]),
                'proofs': self.lines('proofs.gz', [{'id': 3, 'image_path': 'PRIVATE IMAGE', 'owner': 'PRIVATE PROOF'}])}

    def test_off_deterministic_and_source_values(self):
        path = self.off()
        first = self.run_off(path)
        second = normalize_products(self.context, {'products': path}, self.root / 'other')
        self.assertEqual(first['candidateSha256'], second['candidateSha256'])
        rows = self.records()
        self.assertEqual(rows[0]['data']['identifiers'][0]['value'], '001234')
        self.assertEqual(rows[0]['data']['sourceCountryTags'], ['en:france', 'en:germany'])
        self.assertEqual(rows[1]['data']['nutrients']['sodium']['sourceAmount'], 0.1)
        self.assertEqual(rows[1]['data']['nutrients']['sodium']['unit'], 'g')
        self.assertEqual(rows[0]['provenance']['license'], 'fixture terms')
        self.assertEqual(first['normalizedRecords'], 2)
        self.assertFalse(first['accepted'])

    def test_retry_and_cross_country_share_one_candidate(self):
        path = self.off()
        first = self.run_off(path)
        # Country selection is intentionally absent from cache/adapter identity.
        again = self.run_off(path)
        self.assertEqual(first, again)
        self.assertEqual(len(list(self.root.glob('output'))), 1)

    def test_changed_retry_contract_fails(self):
        path = self.off()
        self.run_off(path)
        with self.assertRaisesRegex(RefreshError, 'retry-contract'):
            normalize_products(replace(self.context, release_id='changed'), {'products': path}, self.root/'output')

    def test_corrupt_output_fails_retry(self):
        path = self.off()
        self.run_off(path)
        (self.root/'output/candidate.jsonl').write_text('corrupt')
        with self.assertRaisesRegex(RefreshError, 'retry-output'):
            self.run_off(path)

    def test_duplicate_off_ids_fail_atomically(self):
        path = self.lines('dup.gz', [{'code': '1234'}, {'code': '1234'}])
        with self.assertRaises(RefreshError):
            self.run_off(path)
        self.assertFalse((self.root/'output').exists())
        self.assertEqual(list(self.root.glob('.products-*')), [])

    def test_nonfinite_source_fails(self):
        with self.assertRaises(RefreshError):
            self.run_off(self.off(nutriments={'proteins_100g': float('nan')}))

    def test_json_duplicate_keys_rejected(self):
        path = self.root/'bad.gz'
        with gzip.open(path, 'wb') as f:
            f.write(b'{"code":"1234","code":"2345"}\n')
        with self.assertRaises(RefreshError):
            self.run_off(path)

    def test_line_limit(self):
        with self.assertRaisesRegex(RefreshError, 'expanded-limit'):
            self.run_off(limits=replace(ProductLimits(), max_line_bytes=20))

    def test_row_limit(self):
        path = self.lines('two.gz', [{'code':'1234'}, {'code':'2345'}])
        with self.assertRaisesRegex(RefreshError, 'row-limit'):
            self.run_off(path, limits=replace(ProductLimits(), max_rows=1))

    def test_input_limit(self):
        with self.assertRaisesRegex(RefreshError, 'input-limit'):
            self.run_off(limits=replace(ProductLimits(), max_input_bytes=1))

    def test_output_limit(self):
        with self.assertRaisesRegex(RefreshError, 'output-limit'):
            self.run_off(limits=replace(ProductLimits(), max_output_bytes=1))

    def test_database_limit(self):
        with self.assertRaises(RefreshError):
            self.run_off(limits=replace(ProductLimits(), max_database_bytes=4096))

    def test_ttl_and_evidence(self):
        for ctx in (replace(self.context, cache_seconds=29*86400), replace(self.context, rights_evidence_sha256='')):
            with self.assertRaises(RefreshError):
                normalize_products(ctx, {'products': self.off()}, self.root/'output')

    def test_prices_joins_and_private_metadata(self):
        manifest = normalize_products(replace(self.context, source_id='prices'), self.prices(), self.root/'output')
        row, = self.records()
        self.assertEqual(row['data']['amount'], 2.5)
        self.assertEqual(row['data']['sourceAmount'], '2.50')
        self.assertEqual(row['countries'], ['FR'])
        self.assertEqual(manifest['rawRows'], 3)
        self.assertNotIn('PRIVATE', (self.root/'output/candidate.jsonl').read_text())
        with sqlite3.connect(self.root/'output/source.sqlite') as db:
            self.assertIn('PRIVATE PROOF', db.execute('select body from raw where tab="proofs"').fetchone()[0])

    def test_prices_require_full_related_scope(self):
        inputs = self.prices()
        inputs.pop('proofs')
        with self.assertRaisesRegex(RefreshError, 'input-set'):
            normalize_products(replace(self.context, source_id='prices'), inputs, self.root/'output')

    def test_prices_orphan_rejected(self):
        for changes in ({'proof_id': 999}, {'location_id': 999}):
            with self.assertRaisesRegex(RefreshError, 'unresolved-price-reference'):
                normalize_products(replace(self.context, source_id='prices'), self.prices(**changes), self.root/'output')

    def test_prices_duplicate_marker_preserved(self):
        normalize_products(replace(self.context, source_id='prices'), self.prices(duplicate_of=7), self.root/'output')
        self.assertEqual(self.records()[0]['data']['duplicateOf'], 7)

    def test_usda_relational_join_duplicates_and_raw_retention(self):
        manifest = normalize_products(replace(self.context, source_id='usda-files'), {'archive': self.archive()}, self.root/'output')
        product, profile = self.records()
        self.assertEqual(product['data']['identifiers'][1]['value'], '00012345')
        nutrients = profile['data']['nutrients']
        self.assertEqual(nutrients['protein']['sourceAmount'], '2.30')
        self.assertEqual(nutrients['protein:observation:12']['sourceAmount'], '2.40')
        self.assertEqual(manifest['rawRows'], 6)
        with sqlite3.connect(self.root/'output/source.sqlite') as db:
            raw = json.loads(db.execute('SELECT body FROM raw WHERE tab="food_attribute"').fetchone()[0])
            self.assertEqual(raw['value'], 'original "quoted",\nmultiline value')

    def test_usda_orphans(self):
        path = self.archive({'food_nutrient': [['id','fdc_id','nutrient_id','amount'], ['1','999','1003','2']]})
        with self.assertRaisesRegex(RefreshError, 'orphan-food-reference'):
            normalize_products(replace(self.context, source_id='usda-files'), {'archive': path}, self.root/'output')

    def test_usda_unknown_nutrient(self):
        path = self.archive({'food_nutrient': [['id','fdc_id','nutrient_id','amount'], ['1','1','999','2']]})
        with self.assertRaisesRegex(RefreshError, 'unknown-nutrient'):
            normalize_products(replace(self.context, source_id='usda-files'), {'archive': path}, self.root/'output')

    def test_usda_nutrient_limit(self):
        with self.assertRaisesRegex(RefreshError, 'nutrient-limit'):
            normalize_products(replace(self.context, source_id='usda-files'), {'archive': self.archive()}, self.root/'output', limits=replace(ProductLimits(), max_nutrients_per_food=1))

    def test_usda_archive_member_limit(self):
        with self.assertRaisesRegex(RefreshError, 'archive-member-limit'):
            normalize_products(replace(self.context, source_id='usda-files'), {'archive': self.archive()}, self.root/'output', limits=replace(ProductLimits(), max_archive_members=1))

    def test_usda_traversal_member_rejected(self):
        path = self.archive()
        with zipfile.ZipFile(path, 'a') as f:
            f.writestr('../escape.csv', 'id\n1\n')
        with self.assertRaisesRegex(RefreshError, 'unsafe-archive-member'):
            normalize_products(replace(self.context, source_id='usda-files'), {'archive': path}, self.root/'output')

    def test_usda_duplicate_table_rejected(self):
        path = self.archive()
        with zipfile.ZipFile(path, 'a') as f:
            f.writestr('other/food.csv', 'fdc_id,description,data_type\n2,Other,food\n')
        with self.assertRaisesRegex(RefreshError, 'duplicate-or-invalid-table'):
            normalize_products(replace(self.context, source_id='usda-files'), {'archive': path}, self.root/'output')

    def test_truncated_gzip_and_retry(self):
        path = self.off()
        original = path.read_bytes()
        path.write_bytes(original[:-8])
        with self.assertRaises(RefreshError):
            self.run_off(path)
        path.write_bytes(original)
        self.assertEqual(self.run_off(path)['normalizedRecords'], 2)

    def test_symlink_rejected(self):
        path = self.off()
        link = self.root/'link.gz'
        link.symlink_to(path)
        with self.assertRaisesRegex(RefreshError, 'symlink-rejected'):
            self.run_off(link)

    def test_usda_multiline_cell_bound_before_materialization(self):
        path = self.archive({'food_attribute': [['id','fdc_id','value'], ['a','1','tiny\n' * 1000]]})
        with self.assertRaisesRegex(RefreshError, 'csv-record-limit'):
            normalize_products(replace(self.context, source_id='usda-files'), {'archive': path}, self.root/'output', limits=replace(ProductLimits(), max_line_bytes=1024))

    def test_expansion_limit(self):
        with self.assertRaisesRegex(RefreshError, 'expanded-limit'):
            self.run_off(limits=replace(ProductLimits(), max_expanded_bytes=20))

    def test_empty_release_fails(self):
        with self.assertRaisesRegex(RefreshError, 'empty-candidate'):
            self.run_off(self.lines('empty.gz', []))

    def test_source_revision_and_row_provenance(self):
        self.run_off(self.off(rev=42, last_updated_t=123))
        p = self.records()[0]['provenance']
        self.assertEqual((p['sourceRevision'], p['sourceLastUpdated'], p['sourceRow']), (42, 123, 1))
        self.assertEqual(set(p['inputSha256']), {'products'})

    def test_usda_duplicate_headers_rejected(self):
        path = self.archive({'food': [['fdc_id','description','data_type','description'], ['1','x','x','x']]})
        with self.assertRaisesRegex(RefreshError, 'invalid-csv-columns'):
            normalize_products(replace(self.context, source_id='usda-files'), {'archive': path}, self.root/'output')

    def test_private_raw_corruption_prevents_reuse(self):
        path = self.off()
        self.run_off(path)
        with (self.root/'output/source.sqlite').open('ab') as f:
            f.write(b'changed')
        with self.assertRaisesRegex(RefreshError, 'retry-output'):
            self.run_off(path)

    def test_input_content_changes_do_not_reuse(self):
        self.run_off()
        path = self.off(product_name='Changed')
        with self.assertRaisesRegex(RefreshError, 'retry-contract'):
            self.run_off(path)

    def test_country_consumers_do_not_change_shared_source_key(self):
        path = self.off()
        m = self.run_off(path)
        consumers = {country: normalize_products(self.context, {'products': path}, self.root/'output')['sharedSourceKey']
                     for country in ('FR', 'DE', 'US')}
        self.assertEqual(set(consumers.values()), {m['sharedSourceKey']})

    def test_zip64_metadata_rejected_before_archive_load(self):
        path = self.root/'zip64.zip'
        record = struct.pack('<4sQ2H2L4Q', b'PK\x06\x06', 44, 45, 45, 0, 0, 1_000_000, 1_000_000, 0, 0)
        locator = struct.pack('<4sLQL', b'PK\x06\x07', 0, 0, 1)
        end = struct.pack('<4s4H2LH', b'PK\x05\x06', 0, 0, 65535, 65535, 0xffffffff, 0xffffffff, 0)
        path.write_bytes(record + locator + end)
        with self.assertRaisesRegex(RefreshError, 'archive-member-limit'):
            normalize_products(replace(self.context, source_id='usda-files'), {'archive': path}, self.root/'output')

    def test_multiline_utf8_bom_inside_field_preserved(self):
        path = self.archive({'food_attribute': [['id','fdc_id','value'], ['a','1','first\n\ufeffsecond']]})
        normalize_products(replace(self.context, source_id='usda-files'), {'archive': path}, self.root/'output')
        with sqlite3.connect(self.root/'output/source.sqlite') as db:
            raw = json.loads(db.execute('SELECT body FROM raw WHERE tab="food_attribute"').fetchone()[0])
            self.assertEqual(raw['value'], 'first\n\ufeffsecond')

    def test_supporting_usda_table_duplicate_ids_preserved(self):
        path = self.archive({'food_attribute': [['id','fdc_id','value'], ['same','1','A'], ['same','1','B']]})
        normalize_products(replace(self.context, source_id='usda-files'), {'archive': path}, self.root/'output')
        with sqlite3.connect(self.root/'output/source.sqlite') as db:
            self.assertEqual(db.execute('SELECT count(*) FROM raw WHERE tab="food_attribute"').fetchone()[0], 2)

    def test_usda_nutrient_bytes_bounded_before_profile_accumulation(self):
        rows = [['id','fdc_id','nutrient_id','amount','source_note']]
        rows += [[str(i),'1','1003','2','x'*500] for i in range(10)]
        path = self.archive({'food_nutrient': rows})
        with self.assertRaisesRegex(RefreshError, 'nutrient-byte-limit'):
            normalize_products(replace(self.context, source_id='usda-files'), {'archive': path}, self.root/'output', limits=replace(ProductLimits(), max_line_bytes=2000))

    def test_overflow_json_number_has_fixed_error(self):
        path = self.root/'overflow.gz'
        with gzip.open(path, 'wb') as f:
            f.write(b'{"code":"1234","nutriments":{"proteins_100g":1e9999}}\n')
        with self.assertRaisesRegex(RefreshError, '^product-invalid-or-unreadable-release$'):
            self.run_off(path)


    def test_retry_revalidates_complete_candidate_manifest(self):
        source = self.off()
        expected = self.run_off(source)
        manifest_path = self.root/'output/manifest.json'
        originals = {name: (self.root/'output'/name).read_bytes()
                     for name in ('candidate.jsonl', 'source.sqlite')}
        mutations = {'accepted': True, 'status': 'accepted-source-scope',
            'schemaVersion': 'other', 'candidateSha256': 'f'*64,
            'candidateBytes': 0, 'normalizedRecords': 999, 'rawRows': 999,
            'kinds': {}, 'sourceId': 'prices', 'releaseId': 'other',
            'acquiredAt': '2020-01-01T00:00:00Z', 'cacheSeconds': 1,
            'rightsEvidenceSha256': 'f'*64, 'scopeEvidenceSha256': 'f'*64,
            'inputFiles': [], 'sharedSourceKey': 'f'*64,
            'rawStorage': {'visibility': 'public', 'publishable': True},
            'unexpected': 'not part of a candidate manifest'}
        for key, value in [*mutations.items(), ('accepted', 0)]:
            with self.subTest(field=key, value=value):
                changed = {**expected, key: value}
                manifest_path.write_text(json.dumps(changed))
                with self.assertRaisesRegex(RefreshError, 'retry-manifest-mismatch'):
                    self.run_off(source)
        manifest_path.write_text(json.dumps(expected))
        self.assertEqual(self.run_off(source), expected)
        for name, body in originals.items():
            self.assertEqual((self.root/'output'/name).read_bytes(), body)

    def test_valid_unchanged_replay_all_product_sources(self):
        sources = [('off', {'products': self.off()}), ('prices', self.prices()),
                   ('usda-files', {'archive': self.archive()})]
        for source_id, inputs in sources:
            with self.subTest(source=source_id):
                context = replace(self.context, source_id=source_id)
                destination = self.root/('replay-' + source_id)
                first = normalize_products(context, inputs, destination)
                self.assertEqual(normalize_products(context, inputs, destination), first)
                self.assertIs(first['accepted'], False)

if __name__ == '__main__':
    unittest.main()
