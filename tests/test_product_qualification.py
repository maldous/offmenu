"""Product/acceptance bridge contracts use independently declared tiny inventories."""
from dataclasses import replace
import gzip
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from offmenu.refresh.acceptance import Asset, SourceContract, fingerprint, ids_digest
from offmenu.refresh.core import RefreshError
from offmenu.refresh.product_qualification import qualify_product_candidate


class ProductQualificationTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.bundle = self.root/'bundle'
        self.bundle.mkdir()
        (self.bundle/'data').mkdir()
        self.source = self.bundle/'data/products.gz'
        with gzip.open(self.source, 'wt') as f:
            f.write(json.dumps({'code': '1234', 'product_name': 'Fixture', 'nutrition_data_per': '100g', 'nutriments': {'proteins_100g': 2}})+'\n')
        (self.bundle/'rights.txt').write_text('Synthetic fixture permit: retain parse transform; no public export')
        (self.bundle/'scope.txt').write_text('Exactly product:1234 and nutrientProfile:1234, two output records')
        def asset(name):
            p = self.bundle/name
            return Asset(name, p.stat().st_size, hashlib.sha256(p.read_bytes()).hexdigest())
        self.assets = tuple(asset(name) for name in ('data/products.gz','rights.txt','scope.txt'))
        schema = {'type':'object','required':['id','kind','schemaVersion','data','provenance','countries'],
                  'additionalProperties':False, 'properties': {
                      'id': {'type':'string'}, 'kind': {'enum':['product','nutrientProfile']},
                      'schemaVersion': {'const':'1.0'}, 'data': {'type':'object'},
                      'provenance': {'type':'object'}, 'countries': {'type':'array','items':{'type':'string'}}}}
        schemas = {kind: schema for kind in ('product','nutrientProfile')}
        # This intentionally tiny fixture-specific semantic contract is NOT a
        # production source schema or admission.
        def semantic(row):
            if row['kind'] == 'nutrientProfile':
                value = row['data']['nutrients']['protein']
                if value['unit'] != 'g' or value['basis']['amount'] != 100:
                    return ['fixture-nutrient-invalid']
            return []
        self.contract = SourceContract('off','synthetic','two-fixture-records','2026-10-12T00:00:00Z',
            self.assets, 2, ids_digest(['off:product:1234','off:nutrientProfile:1234']),
            schemas, fingerprint(schemas), semantic, 'c'*64, self.assets[1], self.assets[2],
            frozenset(('retain','parse','transform')), fixture=True)

    def tearDown(self):
        self.temp.cleanup()

    def run_bridge(self, contract=None):
        return qualify_product_candidate(contract or self.contract, self.bundle,
            {'products':'data/products.gz'}, self.root/'output', license='fixture terms', attribution='fixture source')

    def test_pinned_nested_bundle_qualifies_without_acceptance(self):
        result = self.run_bridge()
        self.assertTrue(result['qualification']['qualified'], result['qualification']['errors'])
        self.assertFalse(result['manifest']['accepted'])
        original = json.loads((self.root/'output/manifest.json').read_text())
        qualification = json.loads((self.root/'output/qualification-manifest.json').read_text())
        self.assertEqual(len(original['inputFiles']), 1)
        self.assertEqual(len(qualification['inputFiles']), 3)
        self.assertEqual(qualification['inputRoleMap'], {'products':'data/products.gz'})
        self.assertEqual(self.run_bridge()['qualification'], result['qualification'])

    def test_changed_evidence_blocks_before_normalization(self):
        (self.bundle/'rights.txt').write_text('changed')
        with self.assertRaisesRegex(RefreshError, 'input-pin-mismatch'):
            self.run_bridge()
        self.assertFalse((self.root/'output').exists())

    def test_missing_rights_blocks_before_normalization(self):
        with self.assertRaisesRegex(RefreshError, 'operation-rights-missing'):
            self.run_bridge(replace(self.contract, permitted_operations=frozenset(('retain',))))
        self.assertFalse((self.root/'output').exists())

    def test_held_source_blocks_before_normalization(self):
        with self.assertRaisesRegex(RefreshError, 'source-held'):
            self.run_bridge(replace(self.contract, holds=('legal-review',)))

    def test_scope_expectation_cannot_be_promoted_by_parser_success(self):
        result = self.run_bridge(replace(self.contract, expected_records=3))
        self.assertFalse(result['qualification']['qualified'])
        self.assertIn('expected-record-count-mismatch', result['qualification']['errors'])
        self.assertFalse(result['manifest']['accepted'])

    def test_extra_bundle_file_rejected(self):
        (self.bundle/'extra').write_text('unexpected')
        with self.assertRaisesRegex(RefreshError, 'bundle-set-mismatch'):
            self.run_bridge()

    def test_curated_scope_not_created_by_native_adapter(self):
        with self.assertRaisesRegex(RefreshError, 'native-contract-required'):
            self.run_bridge(replace(self.contract, output_scope='curated'))

    def test_unpinned_empty_directory_rejected_before_parse(self):
        (self.bundle/'extra-directory').mkdir()
        with self.assertRaises(RefreshError):
            self.run_bridge()
        self.assertFalse((self.root/'output').exists())

    def test_public_native_contract_is_not_private_projection(self):
        with self.assertRaisesRegex(RefreshError, 'native-contract-required'):
            self.run_bridge(replace(self.contract, output_visibility='public'))


if __name__ == '__main__':
    unittest.main()
