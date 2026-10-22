"""Synthetic-only offline relational provisioning and exact-join tests."""
import copy
import fcntl
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import sys
import tempfile
import unittest
from unittest.mock import patch
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from ingest_api import DOMAINS
from ingest_store import DomainStore
import ingest_relational_targets as rt


class Targets(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.state = self.root / 'state'
        self.source = self.root / 'source.json'
        self.source.write_text('{}')
        self.selections = []
        for domain in DOMAINS:
            with DomainStore(domain, self.state): pass

    def add(self, domain, records, *, provider='fixture', source_id='one', adapter=1, file=None):
        descriptor = {'id':source_id, 'path':str(file or self.source), 'provider':provider, 'format':'json', 'adapter_version':adapter}
        with DomainStore(domain, self.state) as store:
            result = store.ingest(descriptor, iter(records))
        self.selections.append({'domain':domain, 'source_key':result['source_key'], 'source_version':result['source_version'], 'status':result['status']})
        return result

    def build(self, **kw):
        result = rt.materialize_relational_targets(self.state, self.selections, **kw)
        self.assertNotEqual(result['summary']['status'], 'blocked', result)
        db = sqlite3.connect(result['manifest']['path'])
        self.addCleanup(db.close)
        return result, db

    def test_exact_recipe_mentions_menu_citations_and_schema_only(self):
        self.add('recipes', [
            {'id':'recipe:r', 'kind':'recipe','title':'Synthetic', 'relations':[
                {'kind':'has_ingredient_mention','target_domain':'ingredients','target_id':'mention:1'},
                {'kind':'cites','target_domain':'citations','target_id':'citation:c'}]},
            {'id':'menu:m','kind':'menu','relations':[{'kind':'contains_menu_entry','target_domain':'recipes','target_id':'item:i'}]},
            {'id':'item:i','kind':'menu_item','relations':[{'kind':'item_of','target_domain':'recipes','target_id':'menu:m'}]},
        ])
        self.add('ingredients',[{'id':'mention:1','kind':'ingredient_mention','recipe_id':'recipe:r','ordinal':0,
            'relations':[{'kind':'ingredient_of','target_domain':'recipes','target_id':'recipe:r'}]}])
        self.add('citations',[{'id':'citation:c','record_type':'source_citation','reference':{'url':'https://example.invalid/'},
            'relations':[{'kind':'cites_record','target_domain':'recipes','target_id':'recipe:r'}]}])
        before = {d:rt._identity(rt._store(self.state,d)) for d in DOMAINS}
        result, db = self.build()
        self.assertEqual(result['summary']['relations']['resolved'],6)
        self.assertEqual(result['summary']['relations']['reciprocal_mismatches'],0)
        self.assertEqual(db.execute('SELECT COUNT(*) FROM recipe_ingredient_links').fetchone()[0],1)
        self.assertEqual(db.execute('SELECT COUNT(*) FROM citation_links').fetchone()[0],1)
        self.assertEqual(db.execute('SELECT COUNT(*) FROM menu_member_links').fetchone()[0],1)
        self.assertEqual(result['summary']['schema_only_private_domains'],2)
        self.assertEqual(before,{d:rt._identity(rt._store(self.state,d)) for d in DOMAINS})
        self.assertEqual(db.execute('PRAGMA foreign_key_check').fetchall(),[])
        again = rt.materialize_relational_targets(self.state,self.selections)
        self.assertEqual(again['summary']['status'],'reused')

    def test_supplier_native_ids_not_hashed_record_ids_and_ambiguity(self):
        self.add('suppliers',[
            {'id':'hashed-owner','entity_id':'Q1','type':'organization','relations':[{'kind':'owned_by','target_domain':'suppliers','target_id':'Q2'}]},
            {'id':'hashed-target-a','entity_id':'Q2','type':'organization'},
            {'id':'hashed-target-b','entity_id':'Q2','type':'organization'},
        ],provider='wikidata')
        result, db = self.build()
        self.assertEqual(result['summary']['relations']['ambiguous'],1)
        self.assertEqual(db.execute('SELECT COUNT(*) FROM relation_candidates').fetchone()[0],2)
        self.assertEqual(db.execute('SELECT COUNT(*) FROM supplier_ownership_links').fetchone()[0],0)

    def test_supplier_assertions_are_not_entity_targets(self):
        self.add('suppliers',[
            {'id':'owner','entity_id':'Q1','type':'organization'},
            {'id':'target','entity_id':'Q2','type':'organization'},
            {'id':'meta','entity_id':'Q2','type':'source_metadata'},
            {'id':'assertion','entity_id':'Q1','type':'company_ownership','relations':[{'kind':'owned_by','target_domain':'suppliers','target_id':'Q2','subject_id':'Q1'}]},
        ],provider='wikidata')
        result,db=self.build()
        self.assertEqual(result['summary']['relations']['resolved'],2)
        self.assertEqual(result['summary']['domains']['suppliers']['untyped_records'],1)
        self.assertEqual(db.execute('SELECT COUNT(*) FROM identifier_claims').fetchone()[0],2)
        self.assertEqual(db.execute('SELECT COUNT(*) FROM supplier_assertions').fetchone()[0],1)
        self.assertEqual(db.execute('SELECT COUNT(*) FROM supplier_ownership_links').fetchone()[0],1)

    def test_product_hash_joins_exact_lexical_off_code_not_hash(self):
        self.add('barcodes',[{'id':'row-id-not-code','code':'00123'}],provider='off',adapter=1)
        self.add('ingredients',[{'id':'mention','kind':'ingredient_label_mention','relations':[
            {'kind':'ingredient_of_product','target_domain':'barcodes','target_id':'source-product:hash','source_native_product_id':'00123'}]}],provider='off',adapter='recipe/1')
        result, db = self.build()
        self.assertEqual(result['summary']['relations']['resolved'],1)
        target = db.execute('SELECT record_id FROM source_records WHERE uid=(SELECT target_uid FROM resolved_links)').fetchone()[0]
        self.assertEqual(target,'row-id-not-code')

    def test_numeric_id_does_not_equal_leading_zero_string(self):
        self.add('barcodes',[{'id':'p','code':'00123'}],provider='off')
        self.add('ingredients',[{'id':'i','kind':'ingredient_label_mention','relations':[
            {'kind':'ingredient_of_product','target_domain':'barcodes','source_native_product_id':123}]}],provider='off')
        result, _ = self.build()
        self.assertEqual(result['summary']['relations']['missing'],1)

    def test_same_ids_different_source_not_joined(self):
        self.add('recipes',[{'id':'r','kind':'recipe','relations':[{'kind':'has_ingredient_mention','target_domain':'ingredients','target_id':'i'}]}],source_id='a')
        self.add('ingredients',[{'id':'i','kind':'ingredient_mention'}],source_id='b')
        result, _ = self.build()
        self.assertEqual(result['summary']['relations']['missing'],1)

    def test_dietary_exact_native_id_and_no_nutrient_conversion(self):
        self.add('ingredients',[{'id':'ingredient','kind':'ingredient_source_entity','source_native_id':101,'raw_source':{'fdcId':101}}],provider='usda',adapter=1)
        self.add('dietary',[{'id':'fact','record_type':'nutrientprofile','source_fields':{'fdcId':101,'basis':'per 100 mL','nutrient':'0.0100'},'source_numeric_lexemes':{'/nutrient':'0.0100'}}],provider='usda',adapter=2)
        result, db = self.build()
        self.assertEqual(result['summary']['relations']['resolved'],1)
        self.assertIn('per 100 mL',db.execute('SELECT facts_json FROM dietary_assertions').fetchone()[0])

    def test_private_profiles_never_cross_households(self):
        self.add('user_profiles',[{'id':'profile','namespace':'local','household_id':'a','user_id':'u'}])
        self.add('inventory',[{'id':'lot','namespace':'local','household_id':'b','user_id':'u','quantity':2}])
        result, db = self.build()
        self.assertEqual(result['summary']['relations']['missing'],1)
        self.assertTrue(str(result['manifest']['path']).startswith(str(self.state/'private-household')))
        self.assertEqual(result['summary']['schema_only_private_domains'],0)

    def test_private_scoped_join_and_missing_scope(self):
        self.add('user_profiles',[{'id':'profile','namespace':'local','household_id':'a','user_id':'u'}])
        self.add('inventory',[{'id':'lot','namespace':'local','household_id':'a','user_id':'u'}, {'id':'bad','household_id':'a','user_id':'u'}])
        result, _ = self.build()
        self.assertEqual(result['summary']['relations']['resolved'],1)
        self.assertEqual(result['summary']['relations']['deferred'],1)

    def test_selected_family_scope_cross_artifact_and_missing_scope(self):
        self.add('recipes',[{'id':'item','kind':'menu_item','source_family':'fr_begles_menus','source_scope':['a','b'],'relations':[
            {'kind':'source_dish_reference','target_domain':'recipes','target_id':'dish','target_identity_kind':'acquired_scoped_id','target_source_policy':'selected_family','target_adapter':'fr_begles_menus','target_scope':['a','b'],'target_native_id':42}]}],source_id='menu')
        self.add('recipes',[{'id':'dish','kind':'dish_composition','source_family':'fr_begles_menus','source_scope':['a','b'],'source_native_id':42}],source_id='dishes')
        result, _ = self.build()
        self.assertEqual(result['summary']['relations']['resolved'],1)

    def test_incremental_budget_resume_does_not_accept_partial_candidates(self):
        self.add('recipes',[{'id':'r'+str(i),'kind':'recipe'} for i in range(3)])
        result, db = self.build(max_records=1)
        self.assertEqual(result['summary']['status'],'partial')
        self.assertEqual(result['summary']['domains']['recipes']['records'],1)
        result, db = self.build(max_records=1)
        self.assertEqual(result['summary']['domains']['recipes']['records'],2)
        result, db = self.build(max_records=1)
        self.assertEqual(result['summary']['domains']['recipes']['records'],3)
        self.assertEqual(result['summary']['status'],'complete')

    def test_writer_and_wal_refused_without_source_changes(self):
        path=rt._store(self.state,'recipes')
        fd=os.open(path.with_suffix('.writer.lock'),os.O_RDWR)
        try:
            fcntl.flock(fd,fcntl.LOCK_EX|fcntl.LOCK_NB)
            result=rt.materialize_relational_targets(self.state,[])
            self.assertIn('source_writer_active',result['summary']['blockers'])
        finally: os.close(fd)
        Path(str(path)+'-wal').write_bytes(b'nonempty-synthetic-wal')
        result=rt.materialize_relational_targets(self.state,[])
        self.assertIn('source_wal_present',result['summary']['blockers'])

    def test_zero_byte_wal_is_ignored_without_mutation_under_writer_lock(self):
        self.add('recipes',[{'id':'r','kind':'recipe'}])
        path=Path(str(rt._store(self.state,'recipes'))+'-wal')
        path.write_bytes(b'')
        before=rt._identity(path)
        result, _ = self.build()
        self.assertEqual(result['summary']['status'],'complete')
        self.assertEqual(before,rt._identity(path))

    def test_pending_read_empty_wal_churn_reuses_logical_snapshot(self):
        from ingest_pending import _read_store
        self.add('recipes',[{'id':'r','kind':'recipe'}])
        _read_store(rt._store(self.state,'recipes'),'recipes',[])
        result,_=self.build()
        self.add('recipes',[{'id':'r','kind':'recipe'}])
        _read_store(rt._store(self.state,'recipes'),'recipes',[])
        again,_=self.build()
        self.assertEqual(again['summary']['status'],'reused')
        self.assertEqual(again['manifest']['snapshot'],result['manifest']['snapshot'])

    def test_generic_metadata_is_retained_but_not_typed_food_data(self):
        self.add('barcodes',[{'id':'doc','kind':'source_metadata','code':'manifest-release'}],provider='off')
        self.add('dietary',[{'id':'doc','record_type':'source_metadata','source_fields':{'record_count':1000}}])
        result, db=self.build()
        self.assertEqual(result['summary']['domains']['barcodes']['typed_records'],0)
        self.assertEqual(result['summary']['domains']['dietary']['typed_records'],0)
        self.assertEqual(db.execute('SELECT COUNT(*) FROM source_records').fetchone()[0],2)

    def test_metadata_entity_admission_is_rejected_across_domains(self):
        cases=[
            ('barcodes','off',{'id':'metadata-product','kind':'source_metadata','code':'00123'}),
            ('ingredients','usda',{'id':'metadata-food','kind':'source_metadata','source_native_id':101,'raw_source':{'fdcId':101}}),
            ('suppliers','wikidata',{'id':'metadata-company','type':'source_metadata','entity_id':'Q2'}),
            ('dietary','usda',{'id':'metadata-nutrient','record_type':'source_metadata','source_fields':{'fdcId':101,'nutrients':[]}}),
        ]
        for domain,provider,payload in cases:
            self.add(domain,[payload],provider=provider)
        result,db=self.build()
        for domain,_,_ in cases:
            with self.subTest(domain=domain):
                self.assertEqual(result['summary']['domains'][domain]['typed_records'],0)
                self.assertEqual(result['summary']['domains'][domain]['untyped_records'],1)
        self.assertEqual(db.execute('SELECT COUNT(*) FROM identifier_claims').fetchone()[0],0)

    def test_exact_ids_cannot_link_semantic_edges_to_untyped_wrappers(self):
        self.add('recipes',[
            {'id':'r','kind':'recipe','relations':[{'kind':'has_ingredient_mention','target_domain':'ingredients','target_id':'i'}]},
            {'id':'m','kind':'menu','relations':[{'kind':'contains_menu_entry','target_domain':'recipes','target_id':'doc'}]},
            {'id':'doc','kind':'source_metadata'},
        ])
        self.add('ingredients',[{'id':'i','kind':'source_metadata'}])
        result,_=self.build()
        self.assertEqual(result['summary']['relations']['resolved'],0)
        self.assertEqual(result['summary']['relations']['missing'],2)

    def test_metadata_and_mentions_cannot_supply_food_entity_identifiers(self):
        self.add('ingredients',[
            {'id':'metadata','kind':'source_metadata','source_native_id':101,'raw_source':{'fdcId':101}},
            {'id':'mention','kind':'ingredient_mention','source_native_id':101,'raw_source':{'fdcId':101}},
        ],provider='usda')
        self.add('dietary',[{'id':'fact','record_type':'nutrientprofile','source_fields':{'fdcId':101,'nutrients':[]}}],provider='usda')
        result,db=self.build()
        self.assertEqual(result['summary']['relations']['resolved'],0)
        self.assertEqual(result['summary']['relations']['missing'],1)
        self.assertEqual(db.execute('SELECT COUNT(*) FROM identifier_claims').fetchone()[0],0)

    def test_sanitizer_has_no_payload_path_identity_or_free_text(self):
        result=rt.sanitize_relational_summary({'path':'SECRET','relations':{'total':True,'resolved':2**64}, 'blockers':['SECRET'], 'domains':{'inventory':{'records':-1,'path':'SECRET'}}})
        self.assertNotIn('SECRET',json.dumps(result))
        self.assertEqual(result['relations']['total'],0)
        self.assertEqual(result['relations']['resolved'],0)

    def test_completed_domain_reopen_does_not_invalidate_snapshot(self):
        self.add('recipes',[{'id':'r','kind':'recipe'}])
        result, _ = self.build()
        before = rt._identity(rt._store(self.state,'recipes'))
        self.add('recipes',[{'id':'r','kind':'recipe'}])
        self.assertEqual(before,rt._identity(rt._store(self.state,'recipes')))
        again=rt.materialize_relational_targets(self.state,self.selections)
        self.assertEqual(again['summary']['status'],'reused')

    def test_output_tampering_blocks_reuse(self):
        self.add('recipes',[{'id':'r','kind':'recipe'}])
        result, db = self.build()
        db.execute("UPDATE recipe_headers SET title_json='\"altered\"'"); db.commit()
        again=rt.materialize_relational_targets(self.state,self.selections)
        self.assertIn('derived_target_invalid',again['summary']['blockers'])

    def test_completion_cache_checks_derived_output_and_manifests(self):
        result,db=self.build()
        receipt=self.state/'relational-targets.private.json'
        receipt.write_text(json.dumps(result['manifest']))
        self.assertTrue(rt.relational_outputs_available(self.state))
        target=Path(result['manifest']['path'])
        manifest=target.with_suffix('.manifest.json')
        text=manifest.read_text(); manifest.unlink()
        self.assertFalse(rt.relational_outputs_available(self.state))
        manifest.write_text(text)
        self.assertTrue(rt.relational_outputs_available(self.state))
        db.close(); target.unlink()
        self.assertFalse(rt.relational_outputs_available(self.state))
        target.write_bytes(b'replaced')
        self.assertFalse(rt.relational_outputs_available(self.state))

    def test_completion_cache_refuses_unowned_path_or_missing_receipt(self):
        self.assertFalse(rt.relational_outputs_available(self.state))
        result,_=self.build()
        result['manifest']['path']='/unowned/database.sqlite3'
        (self.state/'relational-targets.private.json').write_text(json.dumps(result['manifest']))
        self.assertFalse(rt.relational_outputs_available(self.state))

    def test_unmatched_native_reference_never_matches_reference_wrapper(self):
        self.add('barcodes',[{'id':'wrapper','kind':'readonly_source_reference','tables':[{'table':'products','rows':100}]}],provider='off',adapter=1)
        self.add('ingredients',[{'id':'i','kind':'ingredient_label_mention','relations':[
            {'kind':'ingredient_of_product','target_domain':'barcodes','source_native_product_id':'00123'}]}],provider='off',adapter=2)
        result, db = self.build()
        self.assertEqual(result['summary']['relations']['resolved'],0)
        self.assertEqual(db.execute('SELECT reason FROM unresolved_links').fetchone()[0],'retained_store_lookup_adapter_required')

    def test_toulouse_null_scope_is_explicit_family_namespace(self):
        self.add('recipes',[{'id':'item','kind':'menu_item','source_family':'fr_toulouse_menus','relations':[
            {'kind':'source_dish_reference','target_domain':'recipes','target_id':'dish','target_identity_kind':'acquired_scoped_id','target_source_policy':'selected_family','target_adapter':'fr_toulouse_menus','target_scope':None,'target_native_id':'001'}]}],source_id='menu')
        self.add('recipes',[{'id':'dish','kind':'dish_composition','source_family':'fr_toulouse_menus','source_scope':None,'source_native_id':'001'}],source_id='dishes')
        result, _ = self.build()
        self.assertEqual(result['summary']['relations']['resolved'],1)

    def test_native_family_join_does_not_coerce_id_types(self):
        self.add('recipes',[{'id':'item','kind':'menu_item','source_family':'fr_toulouse_menus','relations':[
            {'kind':'source_dish_reference','target_domain':'recipes','target_id':'dish','target_identity_kind':'acquired_scoped_id','target_source_policy':'selected_family','target_adapter':'fr_toulouse_menus','target_scope':None,'target_native_id':1}]}],source_id='menu')
        self.add('recipes',[{'id':'dish','kind':'dish_composition','source_family':'fr_toulouse_menus','source_scope':None,'source_native_id':'1'}],source_id='dishes')
        result, _ = self.build()
        self.assertEqual(result['summary']['relations']['missing'],1)

    def test_missing_selected_source_is_not_reported_as_ingested(self):
        self.selections=[{'domain':'recipes','source_key':'missing','source_version':'missing','status':'partial'}]
        result, _ = self.build()
        self.assertEqual(result['summary']['status'],'partial')
        self.assertIn('source_selection_missing',result['summary']['blockers'])

    def test_derived_permissions_are_private(self):
        result, _ = self.build()
        self.assertEqual(os.stat(result['manifest']['path']).st_mode & 0o777,0o600)
        self.assertEqual(os.stat(Path(result['manifest']['path']).with_suffix('.manifest.json')).st_mode & 0o777,0o600)
        self.assertEqual(os.stat(Path(result['manifest']['path']).parent.parent).st_mode & 0o777,0o700)

    def test_source_payload_hash_mismatch_fails_closed(self):
        self.add('recipes',[{'id':'r','kind':'recipe'}])
        db=sqlite3.connect(rt._store(self.state,'recipes'))
        db.execute("UPDATE records SET content_sha256='invalid'"); db.commit(); db.close()
        result=rt.materialize_relational_targets(self.state,self.selections)
        self.assertIn('payload_hash_mismatch',result['summary']['blockers'])

    def test_disk_reserve_stops_and_resumes_without_losing_rows(self):
        self.add('recipes',[{'id':'r'+str(i),'kind':'recipe'} for i in range(3)])
        high, low = SimpleNamespace(free=10**12), SimpleNamespace(free=0)
        with patch.object(rt.shutil,'disk_usage',side_effect=[high,high,high,low]):
            result, _ = self.build()
        self.assertEqual(result['summary']['status'],'partial')
        self.assertIn('disk_reserve',result['summary']['blockers'])
        self.assertEqual(result['summary']['domains']['recipes']['records'],1)
        again, _ = self.build()
        self.assertEqual(again['summary']['domains']['recipes']['records'],3)
        self.assertEqual(again['summary']['status'],'complete')

    def test_disk_reserve_before_write_creates_no_target(self):
        with patch.object(rt.shutil,'disk_usage',return_value=SimpleNamespace(free=0)):
            result=rt.materialize_relational_targets(self.state,[])
        self.assertEqual(result['summary']['status'],'partial')
        self.assertIn('disk_reserve',result['summary']['blockers'])
        self.assertFalse((self.state/'private-household'/'relational-targets').exists())

    def test_interrupted_manifest_publication_recovers_owned_cursor(self):
        self.add('recipes',[{'id':'r'+str(i),'kind':'recipe'} for i in range(3)])
        self.build(max_records=1)
        original=rt._write_manifest
        count=0
        def interrupted(path,value):
            nonlocal count
            count+=1
            if count == 2: raise OSError('synthetic interruption after commit')
            return original(path,value)
        with patch.object(rt,'_write_manifest',side_effect=interrupted):
            result=rt.materialize_relational_targets(self.state,self.selections,max_records=1)
        self.assertEqual(result['summary']['status'],'blocked')
        recovered, _ = self.build(max_records=1)
        self.assertEqual(recovered['summary']['domains']['recipes']['records'],3)
        self.assertEqual(recovered['summary']['status'],'complete')

    def test_progress_is_sanitized_partial_and_callback_failure_isolated(self):
        self.add('recipes',[{'id':'SECRET-r','kind':'recipe','title':'SECRET title'}])
        progress=[]
        def callback(value):
            progress.append(value)
            raise RuntimeError('synthetic report delivery failure')
        result, _ = self.build(progress_callback=callback,progress_interval=0)
        self.assertEqual(result['summary']['status'],'complete')
        self.assertTrue(progress)
        self.assertEqual(progress[0]['status'],'partial')
        self.assertNotIn('SECRET',json.dumps(progress))

    def test_partial_progress_blockers_do_not_contaminate_final_resolved_counts(self):
        self.add('recipes',[{'id':'r','kind':'recipe','relations':[{'kind':'has_ingredient_mention','target_domain':'ingredients','target_id':'i'}]}])
        self.add('ingredients',[{'id':'i','kind':'ingredient_mention','relations':[{'kind':'ingredient_of','target_domain':'recipes','target_id':'r'}]}])
        result,_=self.build(progress_callback=lambda _:None,progress_interval=0)
        self.assertEqual(result['summary']['relations']['resolved'],2)
        self.assertNotIn('unresolved_relations',result['summary']['blockers'])


if __name__ == '__main__': unittest.main()
