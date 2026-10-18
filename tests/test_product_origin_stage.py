"""End-to-end synthetic retained assets -> origins/sidecar -> qualification."""
from dataclasses import replace
import hashlib
import json
from pathlib import Path
import shutil
import unittest

import test_product_adapters as product_fixtures
import test_product_qualification as qualification_fixtures
from offmenu.refresh.acceptance import Asset, fingerprint, ids_digest
from offmenu.refresh.core import RefreshError
from offmenu.refresh.field_provenance import field_origin_errors
from offmenu.refresh.product_adapters import ProductLimits
from offmenu.refresh.product_origin_stage import qualify_product_origins


class ProductOriginStageTest(unittest.TestCase):
    def setUp(self):
        self.f = qualification_fixtures.ProductQualificationTest()
        self.f.setUp()
        self.addCleanup(self.f.tearDown)
        self.contract = self.f.contract
        self.roles = {'products': 'data/products.gz'}

    def run_stage(self, name='enriched', **kwargs):
        return qualify_product_origins(self.contract, self.f.bundle, self.roles,
            self.f.root/'normalized', self.f.root/name, license='fixture terms',
            attribution='fixture source', **kwargs)

    def assert_result(self, result):
        self.assertTrue(result['qualification']['qualified'], result['qualification']['errors'])
        self.assertFalse(result['manifest']['accepted'])
        rows = [json.loads(line)[0] for line in result['candidate'].read_text().splitlines()]
        sidecar = [json.loads(line)[0] for line in result['sidecar'].read_text().splitlines()]
        self.assertEqual(sidecar, [{'id': r['id'], 'fieldOrigins': r['provenance']['fieldOrigins']} for r in rows])
        contract = result['manifest']['originStageContract']
        pins = {v['path']: v['sha256'] for v in contract['inputPins'].values()}
        for row in rows:
            self.assertEqual(field_origin_errors(row, pins, policy_pins=[contract['emitterPolicySha256']]), [])
        return rows

    def configure(self, source):
        f = product_fixtures.ProductAdaptersTest()
        f.setUp()
        self.addCleanup(f.tearDown)
        # Replace only the synthetic fixture assets, before any normalization.
        (self.f.bundle/'data/products.gz').unlink()
        raw = f.prices() if source == 'prices' else {'archive': f.archive()}
        self.roles = {}
        for role, path in raw.items():
            target = self.f.bundle/'data'/path.name
            shutil.copyfile(path, target)
            self.roles[role] = 'data/' + path.name
        kinds = ['priceObservation'] if source == 'prices' else ['product','nutrientProfile']
        schema = next(iter(self.contract.schemas.values()))
        schema = json.loads(json.dumps(schema))
        schema['properties']['kind'] = {'enum': kinds}
        schemas = {k: schema for k in kinds}
        assets = []
        for path in sorted(self.roles.values()):
            p = self.f.bundle/path
            assets.append(Asset(path, p.stat().st_size, hashlib.sha256(p.read_bytes()).hexdigest()))
        scope_path = self.f.bundle/'scope.txt'
        scope_path.write_text('Synthetic independent expected IDs: ' + ', '.join(source + ':' + kind + ':1' for kind in kinds))
        scope_asset = Asset('scope.txt', scope_path.stat().st_size, hashlib.sha256(scope_path.read_bytes()).hexdigest())
        assets.extend([self.contract.rights_evidence, scope_asset])
        def semantic(row):
            if source == 'prices' and row['data']['amount'] != 2.5:
                return ['fixture-price-invalid']
            if source == 'usda-files' and row['kind'] == 'nutrientProfile' and row['data']['nutrients']['protein']['value'] != 2.3:
                return ['fixture-usda-invalid']
            return []
        self.contract = replace(self.contract, source_id=source, inputs=tuple(assets), scope_evidence=scope_asset,
            expected_records=len(kinds), expected_ids_sha256=ids_digest([source + ':' + kind + ':1' for kind in kinds]),
            schemas=schemas, schemas_sha256=fingerprint(schemas), semantic_validator=semantic)

    def test_off_end_to_end_sidecar_and_qualification(self):
        result = self.run_stage()
        self.assert_result(result)
        original = [json.loads(line)[0] for line in (self.f.root/'normalized/candidate.jsonl').read_text().splitlines()]
        self.assertNotIn('fieldOrigins', original[0]['provenance'])
        self.assertNotEqual(result['manifest']['candidateSha256'], result['manifest']['originStageContract']['sourceOutputHashes']['candidate.jsonl'])

    def test_prices_end_to_end_sidecar_and_qualification(self):
        self.configure('prices')
        self.assert_result(self.run_stage())

    def test_usda_end_to_end_exact_members_and_qualification(self):
        self.configure('usda-files')
        result = self.run_stage()
        self.assert_result(result)
        self.assertEqual(result['manifest']['originStageContract']['archiveMembers']['food'], 'FoodData_Central/food.csv')

    def test_retry_deterministic_requalified(self):
        first = self.run_stage()
        second = self.run_stage()
        third = self.run_stage('enriched-again')
        self.assertEqual(first['manifest'], second['manifest'])
        self.assertEqual(first['manifest'], third['manifest'])
        self.assertEqual(first['qualification'], second['qualification'])
        self.assert_result(second)

    def test_corrupt_source_database_rejected(self):
        self.run_stage()
        with (self.f.root/'normalized/source.sqlite').open('ab') as f:
            f.write(b'bad')
        with self.assertRaisesRegex(RefreshError, 'retry-output-mismatch'):
            self.run_stage('another')
        self.assertFalse((self.f.root/'another').exists())

    def test_corrupt_sidecar_rejected(self):
        result = self.run_stage()
        result['sidecar'].write_text('changed')
        with self.assertRaisesRegex(RefreshError, 'stage-output-mismatch'):
            self.run_stage()

    def test_input_change_rejected(self):
        self.run_stage()
        (self.f.bundle/'data/products.gz').write_bytes(b'changed')
        with self.assertRaisesRegex(RefreshError, 'input-pin-mismatch'):
            self.run_stage()

    def test_stage_paths_must_be_separate(self):
        with self.assertRaisesRegex(RefreshError, 'path-overlap'):
            qualify_product_origins(self.contract, self.f.bundle, self.roles, self.f.root/'normalized',
                self.f.root/'normalized/enriched', license='fixture', attribution='fixture')

    def test_semantic_failure_is_never_qualified_or_accepted(self):
        self.contract = replace(self.contract, semantic_validator=lambda row: ['fixture-rejected'])
        result = self.run_stage()
        self.assertFalse(result['qualification']['qualified'])
        self.assertFalse(result['manifest']['accepted'])
        self.assertIn('fixture-rejected', result['qualification']['errors'])

    def test_origin_failure_cleans_only_new_stage(self):
        with self.assertRaisesRegex(RefreshError, 'output-bound'):
            self.run_stage(limits=replace(ProductLimits(), max_line_bytes=2500))
        self.assertTrue((self.f.root/'normalized/manifest.json').exists())
        self.assertFalse((self.f.root/'enriched').exists())
        self.assertEqual(list(self.f.root.glob('.product-origins-*')), [])


if __name__ == '__main__':
    unittest.main()
