"""Source CSV ordinals, not nutrient IDs/JSON key order, choose primary values."""
from copy import deepcopy
from dataclasses import replace
import hashlib
import json
import sqlite3
import unittest
from unittest.mock import patch

import test_usda_product_contract as fixtures
import test_product_adapters as producer_fixtures
from offmenu.refresh import usda_product_contract as binding
from offmenu.refresh.acceptance import Asset, accept, canonical, ids_digest
from offmenu.refresh.core import RefreshError
from offmenu.refresh.product_adapters import ProductLimits
from offmenu.refresh.product_qualification import qualify_product_candidate
from offmenu.refresh.product_origin_stage import qualify_product_origins


class PrimaryObservationPolicyTest(unittest.TestCase):
    def setUp(self):
        self.f = fixtures.UsdaProductContractTest()
        self.f.setUp()
        self.addCleanup(self.f.doCleanups)
        self.row = deepcopy(self.f.records[1])
        # Deliberately reverse lexical/numeric ID order relative to source order.
        first = self.row['data']['nutrients']['protein']
        first['sourceRowId'] = first['rawFields']['id'] = 'Z99'
        second = self.row['data']['nutrients'].pop('protein:observation:12')
        second['sourceRowId'] = second['rawFields']['id'] = 'A01'
        self.row['data']['nutrients']['protein:observation:A01'] = second
        self.authority = [(7, deepcopy(first['rawFields'])), (42, deepcopy(second['rawFields']))]

    def errors(self, row, authority=None):
        return binding.native_semantic_errors(row,
            scope_sha256=self.f.contract.scope_evidence.sha256,
            clock_sha256=self.f.contract.clock_evidence.sha256,
            source_rows=self.authority if authority is None else authority)

    def test_provider_single_suffixed_rejected(self):
        row = deepcopy(self.row)
        first = row['data']['nutrients']['protein']
        row['data']['nutrients'] = {'protein:observation:Z99': first}
        self.assertTrue(self.errors(row, self.authority[:1]))

    def test_provider_swapped_primary_rejected_without_id_change(self):
        row = deepcopy(self.row)
        nutrients = row['data']['nutrients']
        first, second = nutrients['protein'], nutrients.pop('protein:observation:A01')
        row['data']['nutrients'] = {'protein': second, 'protein:observation:Z99': first}
        self.assertEqual(row['id'], self.row['id'])
        self.assertTrue(self.errors(row))

    def test_valid_source_order_duplicates_pass_in_reversed_json_key_order(self):
        self.assertEqual(self.errors(self.row), [])
        row = deepcopy(self.row)
        row['data']['nutrients'] = dict(reversed(list(row['data']['nutrients'].items())))
        self.assertEqual(self.errors(row), [])

    def test_forged_first_row_identity_with_later_value_rejected(self):
        row = deepcopy(self.row)
        n = row['data']['nutrients']['protein']
        n['value'] = 2.4
        n['sourceAmount'] = n['rawFields']['amount'] = '2.40'
        self.assertTrue(self.errors(row))

    def test_missing_duplicate_and_fabricated_source_order_rejected(self):
        row = deepcopy(self.row)
        del row['data']['nutrients']['protein:observation:A01']
        self.assertTrue(self.errors(row))
        self.assertTrue(self.errors(self.row, list(reversed(self.authority))))

    def test_unbound_fixed_policy_fails_closed_for_observation_authority(self):
        errors = self.f.contract.semantic_validator(self.f.records[1])
        self.assertIn('usda-native-source-order-authority-required', errors)


class PrimaryObservationBindingTest(unittest.TestCase):
    def fixture(self, single=False):
        f = producer_fixtures.ProductAdaptersTest();f.setUp();self.addCleanup(f.tearDown)
        table = [['id','fdc_id','nutrient_id','amount'], ['Z99','1','1003','2.30']]
        if not single:
            table.append(['A01','1','1003','2.40'])
        source_path = f.archive({'food_nutrient': table})
        source = Asset(source_path.name, source_path.stat().st_size,
                       hashlib.sha256(source_path.read_bytes()).hexdigest())
        evidence = f.root/'evidence';evidence.mkdir()
        rights_path = evidence/'rights.json';rights_path.write_text('Synthetic private retain parse transform fixture')
        rights = Asset('rights.json',rights_path.stat().st_size,hashlib.sha256(rights_path.read_bytes()).hexdigest())
        limits = ProductLimits(max_input_bytes=1024**3,max_expanded_bytes=4*1024**3,max_rows=binding.RAW_ROWS)
        # Only synthetic source/evidence pins differ. Real factory counts/IDs are
        # checked independently; fixture=True and two declared IDs never admit data.
        with patch.object(binding,'SOURCE',source),patch.object(binding,'RIGHTS',rights):
            contract = binding.usda_20260430_contract(limits=limits)
            docs = binding.evidence_documents()
        contract = replace(contract, fixture=True, expected_records=2,
            expected_ids_sha256=ids_digest(['usda-files:product:1','usda-files:nutrientProfile:1']))
        for name,doc in docs.items():
            (evidence/name).write_bytes(canonical(doc))
        originals = f.root/'originals';originals.mkdir();source_path.rename(originals/source.path)
        normalized = f.root/'normalized'
        result = qualify_product_candidate(contract,evidence,{'archive':source.path},normalized,
            license=binding.LICENSE,attribution=binding.ATTRIBUTION,limits=limits,input_root=originals)
        self.assertTrue(result['qualification']['qualified'],result['qualification']['errors'])
        return f,contract,evidence,originals,normalized,limits,result

    def test_verified_bridge_and_origin_retry_preserve_source_order(self):
        f,c,e,o,n,l,result = self.fixture()
        first = qualify_product_origins(c,e,{'archive':c.inputs[0].path},n,f.root/'origins',
            license=binding.LICENSE,attribution=binding.ATTRIBUTION,limits=l,input_root=o)
        self.assertTrue(first['qualification']['qualified'],first['qualification']['errors'])
        again = qualify_product_origins(c,e,{'archive':c.inputs[0].path},n,f.root/'origins',
            license=binding.LICENSE,attribution=binding.ATTRIBUTION,limits=l,input_root=o)
        self.assertEqual(first['qualification'],again['qualification'])
        self.assertFalse(first['manifest']['accepted'])
        with binding.bind_normalized_semantics(c,n,result['manifest'],l) as checked:
            row = json.loads(result['candidate'].read_text().splitlines()[1])[0]
            self.assertEqual(checked.semantic_validator(row),[])
            ns = row['data']['nutrients'];primary,later=ns['protein'],ns.pop('protein:observation:A01')
            row['data']['nutrients']={'protein':later,'protein:observation:Z99':primary}
            self.assertIn('usda-native-observation-source-order',checked.semantic_validator(row))

    def test_single_source_observation_cannot_be_suffix_only(self):
        f,c,e,o,n,l,result = self.fixture(single=True)
        with binding.bind_normalized_semantics(c,n,result['manifest'],l) as checked:
            row=json.loads(result['candidate'].read_text().splitlines()[1])[0]
            self.assertEqual(checked.semantic_validator(row),[])
            row['data']['nutrients']={'protein:observation:Z99':row['data']['nutrients']['protein']}
            self.assertIn('usda-native-observation-source-order',checked.semantic_validator(row))

    def test_forged_database_and_producer_pins_rejected_before_sql_open(self):
        f,c,e,o,n,l,result = self.fixture()
        for key in ['database','source','normalization','limits']:
            manifest=deepcopy(result['manifest'])
            if key=='database':manifest['outputHashes']['source.sqlite']='f'*64
            elif key=='source':manifest['contract']['inputFiles'][0]['sha256']='f'*64
            elif key=='normalization':manifest['normalizationManifestSha256']='f'*64
            else:manifest['contract']['limits']['max_rows']+=1
            with self.subTest(key=key),patch.object(binding.sqlite3,'connect') as connect:
                with self.assertRaises(RefreshError):
                    with binding.bind_normalized_semantics(c,n,manifest,l):pass
                connect.assert_not_called()

    def test_order_authority_is_readonly_and_closed(self):
        f,c,e,o,n,l,result = self.fixture()
        original=binding.sqlite3.connect;opened=[]
        def connect(*args,**kwargs):
            db=original(*args,**kwargs);opened.append(db);return db
        with patch.object(binding.sqlite3,'connect',connect):
            with binding.bind_normalized_semantics(c,n,result['manifest'],l):
                with self.assertRaises(sqlite3.OperationalError):opened[0].execute('DELETE FROM raw')
        with self.assertRaises(sqlite3.ProgrammingError):opened[0].execute('SELECT 1')

    def test_database_mutation_during_qualification_is_not_adopted(self):
        f,c,e,o,n,l,result = self.fixture()
        with self.assertRaisesRegex(RefreshError,'authority-changed'):
            with binding.bind_normalized_semantics(c,n,result['manifest'],l):
                db=sqlite3.connect(n/'source.sqlite')
                try:
                    db.execute("UPDATE raw SET body=replace(body,'2.30','9.99') WHERE tab='food_nutrient'")
                    db.commit()
                finally:db.close()

    def test_held_contract_cannot_open_source_order_authority(self):
        f,c,e,o,n,l,result=self.fixture()
        with patch.object(binding.sqlite3,'connect') as connect:
            with self.assertRaisesRegex(RefreshError,'authority-held'):
                with binding.bind_normalized_semantics(replace(c,holds=('actual-hold',)),n,result['manifest'],l):pass
            connect.assert_not_called()

    def test_explicit_accept_requires_live_verified_authority(self):
        f,c,e,o,n,l,result=self.fixture()
        self.assertFalse(accept(c,e,result['candidate'],result['manifest'],input_root=o)['accepted'])
        row=json.loads(result['candidate'].read_text().splitlines()[1])[0]
        with binding.bind_normalized_semantics(c,n,result['manifest'],l) as checked:
            receipt=accept(checked,e,result['candidate'],result['manifest'],input_root=o)
            self.assertEqual(receipt['status'],'accepted-fixture-scope')
            self.assertFalse(receipt['productionAccepted'])
        self.assertIn('usda-native-source-order-invalid',checked.semantic_validator(row))


if __name__ == '__main__':
    unittest.main()
