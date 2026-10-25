"""The two observed PR136 provider regressions; generated records only."""
import hashlib
import json
from pathlib import Path
import sqlite3
import unittest
from jsonschema import Draft202012Validator
from offmenu.refresh import product_adapters as adapters
from offmenu.refresh import barcode_validation as validation
from offmenu.refresh import usda_product_contract as policy


def generated_usda_fixture():
    db=sqlite3.connect(':memory:')
    db.execute('CREATE TABLE raw(tab TEXT,ordinal INTEGER,identity TEXT,parent TEXT,body TEXT)')
    food={'fdc_id':'1','description':'Generated fixture food','data_type':'Branded','publication_date':'2026-04-30'}
    brand={'fdc_id':'1','gtin_upc':'012345678905','brand_owner':'Generated brand','ingredients':'Generated source declaration',
           'market_country':'United States','serving_size':'30','serving_size_unit':'g','household_serving_fulltext':'Generated serving'}
    nutrient={'id':'1003','name':'Protein','unit_name':'G'}
    observation={'id':'fixture-observation','fdc_id':'1','nutrient_id':'1003','amount':'2.50'}
    for table,key,parent,row in [('food','1',None,food),('branded_food','1',None,brand),
                                 ('nutrient','1003',None,nutrient),('food_nutrient','fixture-observation','1',observation)]:
        db.execute('INSERT INTO raw VALUES (?,?,?,?,?)',(table,1,key,parent,json.dumps(row)))
    return db,food,observation


class ProviderRegressionTests(unittest.TestCase):
    def test_shared_adapter_binding_and_generated_USDA_semantics(self):
        self.assertEqual(policy.ADAPTER_SHA256,hashlib.sha256(Path(adapters.__file__).read_bytes()).hexdigest())
        self.assertEqual(len(policy.policy_sha256()),64)
        context=adapters.ProductContext('usda-files',policy.RELEASE,None,policy.LICENSE,policy.ATTRIBUTION,
            policy.RIGHTS.sha256,'2'*64,acquisition_clock_status='unknown-retained',clock_evidence_sha256='3'*64)
        context.validate()
        db,food,observation=generated_usda_fixture()
        try:
            rows=list(adapters._food(context,db,food,adapters.ProductLimits()))
            self.assertEqual([row['kind'] for row in rows],['product','nutrientProfile'])
            for row in rows:
                row['provenance'].update(sourceRow=1,inputSha256={'archive':policy.SOURCE.sha256})
                self.assertEqual(list(Draft202012Validator(policy.native_schemas()[row['kind']]).iter_errors(row)),[])
                self.assertEqual(policy.native_semantic_errors(row,scope_sha256='2'*64,clock_sha256='3'*64,
                    source_rows=[(1,observation)]),[])
        finally:db.close()

    def test_explicit_native_name_language_survives_projection(self):
        context=adapters.ProductContext('off','generated','2026-10-25T00:00:00Z','generated','generated','1'*64,'2'*64)
        raw={'code':'012345678905','product_name':'Bonjour','lang':'fr','nutriments':{}}
        native=next(adapters._off(context,raw))
        self.assertEqual(native['data']['nameLanguage'],'fr')
        self.assertEqual(validation.normalize_record(native,'/generated')['nameLanguage'],'fr')
        self.assertEqual(validation.normalize_record(raw,'/generated-raw')['nameLanguage'],'fr')


if __name__=='__main__':unittest.main()
