"""Actual observed closed-schema/origin/cache compatibility regressions."""
import json
from pathlib import Path
import sqlite3
import unittest
from offmenu.refresh import product_adapters as a
from offmenu.refresh import off_native_policy as policy
from offmenu.refresh import product_field_origins as origins
from offmenu.refresh.field_provenance import field_origin_errors


class QualificationSmoke(unittest.TestCase):
    def context(self):
        return a.ProductContext('off',policy.RELEASE,None,policy.LICENSE,policy.ATTRIBUTION,
             '1'*64,'2'*64,acquisition_clock_status='unknown-retained',clock_evidence_sha256='3'*64)

    def test_observed_numeric_trace_unknown_basis_and_overflow_routes(self):
        context=self.context()
        for amount,per in [(2,'100g'),('Tr','100g'),(2,'serving'),(10**400,'100g')]:
            with self.subTest(per=per,amountType=type(amount).__name__):
                row={'code':'012345678905','product_name_en':'Generated fixture',
                     'product_name_fr':'Exemple généré','lang':'fr',
                     'nutriments':{'proteins_100g':amount},'nutrition_data_per':per}
                db=sqlite3.connect(':memory:')
                try:
                    db.execute('CREATE TABLE raw(tab TEXT,ordinal INTEGER,identity TEXT,body TEXT)')
                    db.execute('INSERT INTO raw VALUES (?,?,?,?)',('products',1,row['code'],json.dumps(row)))
                    emitter=origins.ProductOriginEmitter(context,db,{'products':{'path':'generated.jsonl.gz','sha256':'4'*64}})
                    for record in a._off(context,row):
                        record['provenance'].update(sourceRow=1,sourceRevision=None,
                            sourceLastModified=None,sourceLastUpdated=None,inputSha256={'products':policy.SOURCE.sha256})
                        self.assertEqual(policy.native_semantic_errors(record,context,source_record=row,source_ordinal=1),[])
                        enriched=emitter.emit(record)
                        self.assertEqual(enriched['data'],record['data'])
                        self.assertEqual(field_origin_errors(enriched,{'generated.jsonl.gz':'4'*64},policy_pins=[emitter.policy]),[])
                finally:db.close()

    def test_changed_OFF_contract_cannot_select_legacy_cache(self):
        fixture=json.loads((Path(__file__).parent/'fixtures/off_optional_projection/legacy-contract.json').read_text())
        context=a.ProductContext(**fixture['context'])
        contract=a._product_contract(context,a.ProductLimits(),fixture['files'])
        self.assertNotEqual(a.canonical(contract),a.canonical(fixture['contract']))
        self.assertEqual(contract['offOptionalNutritionNamesProjectionVersion'],a.OFF_OPTIONAL_PROJECTION_VERSION)
        self.assertEqual(contract,a._product_contract(context,a.ProductLimits(),fixture['files']))


if __name__=='__main__':unittest.main()
