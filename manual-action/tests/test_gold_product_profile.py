"""Generated nonsensitive product fixtures; SQLite only in memory."""
import copy
import importlib.util
import json
from pathlib import Path
import sqlite3
import sys
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import gold_product_profile as profile
from gold_builder import digest,TABLE_COLUMNS,INSERT_ORDER
PIN='a'*64

def fixture():
    payload={'code':'0000000000001','product_name':'Generated English product',
             'nutrition_data_per':'100g','serving_size':'25 g',
             'nutriments':{'proteins_value':8,'proteins_unit':'g','proteins_100g':8},
             'ingredients':[{'id':'en:sugar','text':'Sugar'}],
             'unknown_upstream_attribute':{'keep':'private custody only'},
             'private_debug_path':'/example-private-custody/not-app-output'}
    source={'domain':'barcodes','source_key':'generated-off-source','source_version':'generated-release',
            'record_id':payload['code'],'content_sha256':digest(payload),
            'normalized_artifact_sha256':PIN,'committed_watermark':'generated-commit-1'}
    packet={'schema_version':'offmenu.product-profile-input/1','data_class':'synthetic',
            'source':source,'payload':payload,'payload_sha256':digest(payload),
            'citations':[{'citation_id':'generated-curator-citation','source_binding':copy.deepcopy(source),
                          'url':None,'attribution':'Open Food Facts'}]}
    q={'schema_version':'offmenu.product-profile-qualification/1','packet_sha256':digest(packet),
       'payload_sha256':packet['payload_sha256'],'selected_source':copy.deepcopy(source),
       'facts_review_sha256':PIN,'english_name_language':'en',
       'field_proofs':[{'pointer':p,'value_sha256':digest(profile._pointer(payload,p)),
                        'citation_id':'generated-curator-citation','evidence_sha256':PIN,
                        'source_binding':copy.deepcopy(source)} for p in profile.FACT_POINTERS],
       'rights':{'state':'permitted','operation':'private-local-product-profile',
                 'source_binding':copy.deepcopy(source),'scope':copy.deepcopy(profile.RIGHTS_SCOPE),
                 'terms_url':profile.OFFICIAL_TERMS_URL,'licence_notices':copy.deepcopy(profile.LICENCE_NOTICES),'purpose_limits':copy.deepcopy(profile.PURPOSE_LIMITS),
                 'terms_evidence_sha256':PIN,'operation_evidence_sha256':PIN}}
    return packet,q

def bind(packet,q):
    packet['payload_sha256']=digest(packet['payload'])
    q['payload_sha256']=packet['payload_sha256'];q['packet_sha256']=digest(packet)
    for proof in q['field_proofs']:proof['value_sha256']=digest(profile._pointer(packet['payload'],proof['pointer']))
    return profile.build_product_profile(packet,qualification=q)

def database(proposal):
    db=sqlite3.connect(':memory:');db.executescript((ROOT/'gold.schema.sql').read_text())
    for table in INSERT_ORDER:
        for row in proposal['rows'][table]:
            cols=TABLE_COLUMNS[table]
            db.execute('INSERT INTO '+table+' ('+','.join(cols)+') VALUES ('+','.join('?' for _ in cols)+')',[row[k] for k in cols])
    return db

class ProductProfileTests(unittest.TestCase):
    def test_generated_connected_queries_and_foreign_keys(self):
        p,q=fixture();r=profile.build_product_profile(p,qualification=q)
        self.assertEqual('qualified-candidate',r['status'])
        with database(r) as db:
            self.assertEqual([],db.execute('PRAGMA foreign_key_check').fetchall())
            rows=db.execute(profile.QUERIES['product_nutrition_citations']).fetchall()
            self.assertTrue(rows);self.assertEqual(1,len({row[2] for row in rows}))
            self.assertEqual(1,len(db.execute(profile.QUERIES['product_source_lineage']).fetchall()))
            self.assertEqual([],db.execute(profile.QUERIES['holds']).fetchall())
        self.assertEqual(1,r['counts']['qualifiedProducts']);self.assertEqual(0,r['counts']['actualGoldAdmitted'])
    def test_source_binding_and_payload_hash_mismatches_fail(self):
        for field in ('record_id','source_version','content_sha256','committed_watermark'):
            p,q=fixture();p['source'][field]='changed';q['packet_sha256']=digest(p)
            with self.assertRaises(ValueError):profile.build_product_profile(p,qualification=q)
        p,q=fixture();p['payload']['product_name']='changed';q['packet_sha256']=digest(p)
        with self.assertRaisesRegex(ValueError,'payload hash'):profile.build_product_profile(p,qualification=q)
    def test_field_citation_or_record_mismatch_fails(self):
        for key,value in [('citation_id','missing'),('value_sha256','b'*64),('source_binding',{})]:
            p,q=fixture();q['field_proofs'][0][key]=value
            with self.assertRaises(ValueError):profile.build_product_profile(p,qualification=q)
        p,q=fixture();p['citations'][0]['source_binding']={};q['packet_sha256']=digest(p)
        with self.assertRaises(ValueError):profile.build_product_profile(p,qualification=q)
    def test_missing_rights_or_review_or_field_proof_held(self):
        for mode in ('rights','review','proof','name-language'):
            p,q=fixture()
            if mode=='rights':q['rights']['state']='held'
            elif mode=='review':q.pop('facts_review_sha256')
            elif mode=='proof':q['field_proofs'].pop()
            else:q['english_name_language']='fr'
            r=profile.build_product_profile(p,qualification=q)
            self.assertEqual('held',r['status']);self.assertIsNone(r['dto']['product'])
            self.assertEqual([],r['dto']['nutrientObservations']);self.assertEqual(0,r['counts']['qualifiedProducts'])
            for table in ('gold_entities','gold_occurrences','gold_claims','gold_metrics','gold_observations'):
                self.assertTrue(all(row['state']=='held' for row in r['rows'][table]))
    def test_wrong_rights_scope_or_terms_cannot_qualify(self):
        for change in ('scope','source','terms','operation'):
            p,q=fixture()
            if change=='scope':q['rights']['scope']['target_locale']='fr'
            elif change=='source':q['rights']['source_binding']={}
            elif change=='terms':q['rights']['terms_url']='https://openfoodfacts.org.invalid/terms'
            else:q['rights']['operation']='public-publication'
            self.assertEqual('held',profile.build_product_profile(p,qualification=q)['status'])
    def test_bad_serving_or_inconsistent_basis_held_without_repair(self):
        for mode in ('serving','per100g','value-type'):
            p,q=fixture()
            if mode=='serving':p['payload']['nutrition_data_per']='serving'
            elif mode=='per100g':p['payload']['nutriments']['proteins_100g']=32
            else:p['payload']['nutriments']['proteins_value']='8'
            r=bind(p,q);self.assertEqual('held',r['status'])
            self.assertEqual(p['payload'],r['privateCustodyOriginal'])
    def test_one_measurement_and_native_unit_basis_retained(self):
        p,q=fixture();r=profile.build_product_profile(p,qualification=q)
        self.assertEqual(1,len(r['rows']['gold_observations']))
        original=json.loads(r['rows']['gold_observations'][0]['original_json'])
        self.assertEqual({'value':8,'unit':'g','basis':'100g','source_per100g_alias':8,'reported_value_count':1,'independent_measurement_count':None},original)
        self.assertIsNone(json.loads(r['rows']['gold_observations'][0]['comparable_json']))
    def test_no_canonical_recipe_safety_manufacturer_or_translation_guess(self):
        p,q=fixture();r=profile.build_product_profile(p,qualification=q);d=r['dto']
        self.assertEqual([],r['rows']['gold_edges'])
        self.assertIsNone(d['product']['sourceIngredientTags'][0]['canonicalIngredientId'])
        self.assertEqual('open-food-facts/product.ingredients.id',d['product']['sourceIngredientTags'][0]['namespace'])
        self.assertEqual('NOT_CHECKED',d['extensions']['recallCoverage'])
        for key in ('manufacturer','parent','retailer','brandLabel'):self.assertIsNone(d['extensions'][key])
        self.assertEqual('HELD_NOT_QUALIFIED',d['extensions']['recipe'])
        self.assertEqual(p['payload']['product_name'],d['product']['nameEn'])
    def test_dto_allowlist_unknown_custody_and_input_immutability(self):
        p,q=fixture();before=copy.deepcopy((p,q));r=profile.build_product_profile(p,qualification=q)
        self.assertEqual(before,(p,q));self.assertEqual(p['payload'],r['privateCustodyOriginal'])
        self.assertNotIn('private_debug_path',json.dumps(r['dto']));self.assertNotIn('/example-private',json.dumps(r['dto']))
        self.assertNotIn('unknown_upstream_attribute',json.dumps(r['dto']))
    def test_dto_schema_required_fields_and_no_extensions(self):
        import jsonschema
        p,q=fixture();d=profile.build_product_profile(p,qualification=q)['dto'];schema=json.loads((ROOT/'gold-product-profile.schema.json').read_text())
        validator=jsonschema.Draft202012Validator(schema);validator.validate(d)
        broken=copy.deepcopy(d);broken['secret']='unallowed'
        self.assertTrue(list(validator.iter_errors(broken)))
        broken=copy.deepcopy(d);broken.pop('source');self.assertTrue(list(validator.iter_errors(broken)))
        q['rights']['state']='held';validator.validate(profile.build_product_profile(p,qualification=q)['dto'])
    def test_stable_ids_independent_of_source_key_order(self):
        p,q=fixture();r=profile.build_product_profile(p,qualification=q)
        p['source']=dict(reversed(list(p['source'].items())))
        r2=profile.build_product_profile(p,qualification=q)
        self.assertEqual(r,r2)
    def test_multiple_citations_and_unused_custody_disposition(self):
        p,q=fixture();c=copy.deepcopy(p['citations'][0]);c['citation_id']='second';p['citations'].append(c)
        for proof in list(q['field_proofs']):
            added=copy.deepcopy(proof);added['citation_id']='second';q['field_proofs'].append(added)
        extra=copy.deepcopy(c);extra['citation_id']='unused';p['citations'].append(extra);q['packet_sha256']=digest(p)
        r=profile.build_product_profile(p,qualification=q)
        self.assertEqual(2,r['counts']['usableCitations']);self.assertEqual(1,r['counts']['heldCitations'])
        self.assertEqual('qualified-candidate',r['status']);self.assertTrue(any(h['target_kind']=='citation' and h['target_id']=='unused' for h in r['rows']['gold_holds']))
    def test_url_credentials_and_nonselected_real_product_rejected(self):
        p,q=fixture();p['citations'][0]['url']='https://user:password@example.invalid/product';q['packet_sha256']=digest(p)
        with self.assertRaises(ValueError):profile.build_product_profile(p,qualification=q)
        p,q=fixture();p['data_class']='real-qualified';q['packet_sha256']=digest(p)
        with self.assertRaisesRegex(ValueError,'outside selected'):profile.build_product_profile(p,qualification=q)
    def test_exact_selected_official_notice_only(self):
        p,q=fixture();self.assertEqual('qualified-candidate',profile.build_product_profile(p,qualification=q)['status'])
        for url in ('https://openfoodfacts.github.io/unselected-path/',
                    'https://other.github.io/documentation/docs/Product-Opener/api/tutorials/license-be-on-the-legal-side/',
                    'https://world.openfoodfacts.org/terms-of-use',
                    profile.OFFICIAL_TERMS_URL+'?token=unqualified'):
            q['rights']['terms_url']=url
            self.assertEqual('held',profile.build_product_profile(p,qualification=q)['status'])
    def test_product_id_stable_over_readstamp_and_normalizer_artifact(self):
        p,q=fixture();first=profile.build_product_profile(p,qualification=q)
        p['source']['committed_watermark']='generated-stamp-2'
        p['source']['normalized_artifact_sha256']='b'*64
        q['selected_source']=copy.deepcopy(p['source']);q['rights']['source_binding']=copy.deepcopy(p['source'])
        for c in p['citations']:c['source_binding']=copy.deepcopy(p['source'])
        for proof in q['field_proofs']:proof['source_binding']=copy.deepcopy(p['source'])
        q['packet_sha256']=digest(p);second=profile.build_product_profile(p,qualification=q)
        self.assertEqual(first['dto']['product']['id'],second['dto']['product']['id'])
        self.assertEqual(first['rows']['gold_observations'][0]['observation_id'],second['rows']['gold_observations'][0]['observation_id'])
        self.assertNotEqual(first['rows']['gold_occurrences'][0]['occurrence_id'],second['rows']['gold_occurrences'][0]['occurrence_id'])
        self.assertNotEqual(first['rows']['gold_runs'][0]['run_id'],second['rows']['gold_runs'][0]['run_id'])
    def test_reported_value_count_does_not_claim_measured_independence(self):
        p,q=fixture();r=profile.build_product_profile(p,qualification=q)
        original=json.loads(r['rows']['gold_observations'][0]['original_json'])
        self.assertEqual(1,original['reported_value_count']);self.assertIsNone(original['independent_measurement_count'])
        self.assertNotIn('independent_measurements',original)
        obs=r['dto']['nutrientObservations'][0]
        self.assertEqual(1,obs['reportedValueCount']);self.assertIsNone(obs['independentMeasurementCount'])
        self.assertFalse(obs['sourcePer100gIsIndependentMeasurement'])
    def test_required_licence_notices_and_private_limits_preserved(self):
        p,q=fixture();r=profile.build_product_profile(p,qualification=q)
        self.assertEqual(profile.LICENCE_NOTICES,r['dto']['rights']['licenceNotices'])
        self.assertEqual(profile.PURPOSE_LIMITS,r['dto']['rights']['purposeLimits'])
        self.assertFalse(r['dto']['rights']['legalComplianceClaim'])
        for key in ('licence_notices','purpose_limits'):
            p,q=fixture();q['rights'].pop(key)
            self.assertEqual('held',profile.build_product_profile(p,qualification=q)['status'])
    def test_bounded_native_json_and_nonfinite(self):
        p,q=fixture();p['extra']='x'*1048577
        with self.assertRaises(ValueError):profile.build_product_profile(p,qualification=q)
        p,q=fixture();p['payload']['nutriments']['proteins_value']=float('nan')
        with self.assertRaises(ValueError):profile.build_product_profile(p,qualification=q)

if __name__=='__main__':unittest.main()
