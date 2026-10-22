"""Generated schema fixtures only: no raw acquired corpus, network or source code."""
import csv
import io
import json
from pathlib import Path
import sys
import tempfile
import threading
import time
import unittest
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import ingest_acquired_menus as adapter
from ingest_store import DomainStore
from ingest_engine import IngestContext


def begles_menu(**extra):
    return dict(menucollsiret='00011122233344',menuetablissementsiret='00011122233355',
                menurestaurantidtype='local',menurestaurantid='001',menudate='2026-10-22',
                menurepastype='midi',menurestaurantconvive='primaire',menuplattype='entrée',
                menuplatnom='Salade générée',menuplatcode='007',menuplatprix='3,50',
                menuplatallergene=None,**extra)


def begles_dish(**extra):
    return dict(platcollsiret='00011122233344',platetablissementsiret='00011122233355',
                platcode='007',platnom='Salade générée',platproduitnom='pois, lait',
                platproduitnutriment='énergie: 123',platproduitallergene='lait',**extra)


def toulouse_menu(**extra):
    row=dict(code_plat='007P',libelle_plat='Plat généré',datemenu='2026-10-22',
             libelle_repas='midi',ordre_plat=2,libelle_ordre_plat='plat',
             libelle_population_cible='primaire')
    row.update(extra)
    return row


def cnous_xml():
    # Independently generated values, structure from pinned ESUP primary mapping.
    return '''<?xml version="1.0" encoding="UTF-8"?><root><menu id="m001" restaurant="r007" date="2026-10-22"><repas nom="midi"><plats nom="Entrées"><plat id="p01"><nom>Soupe &amp; pois</nom><ingredients>pois, lait</ingredients><code valeur="lait"/></plat><plat><nom>Crudités</nom></plat></plats><plats nom="Desserts"><plat><nom>Fruit</nom></plat></plats></repas></menu><menu id="m002" restaurant="r007" date="2026-10-23"><repas nom="midi"><plats nom="Plats"><plat><nom>Suite</nom></plat></plats></repas></menu></root>'''


class AcquiredMenuTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)
        self.config={'reserve_bytes':0,'batch_size':2,'max_record_bytes':16*1024*1024}

    def source(self,name,content,family='fr_begles_menus',role='menu',**extra):
        path=self.root/name
        path.write_bytes(content if isinstance(content,bytes) else content.encode('utf-8'))
        return {'id':name,'artifact_name':name,'path':str(path),'format':path.suffix[1:],
                'provider':family,'acquired_adapter':family,'acquired_role':role,
                'license':'generated license','disposition':'candidate',
                'metadata':{'acquisition':{'verified':True}},**extra}

    def run_sources(self,domain,sources,config=None):
        config={**self.config,**(config or {})}
        context=IngestContext(domain,self.root,config,threading.Event(),lambda *a:None,time.monotonic())
        with DomainStore(domain,self.root,config) as store:
            context.store=store
            result=adapter.run_domain(domain,sources,context)
            rows=[json.loads(v[0]) for v in store.db.execute('SELECT payload_json FROM records ORDER BY row_number')]
            links=store.db.execute('SELECT kind,target_domain,target_id FROM relations').fetchall()
        return result,rows,links

    def test_begles_cost_null_allergens_citations_and_no_recipe_inference(self):
        row=begles_menu()
        source=self.source('menu.json',json.dumps([row],ensure_ascii=False))
        result,records,links=self.run_sources('recipes',[source])
        self.assertEqual(result['status'],'complete')
        self.assertEqual([x['kind'] for x in records],['menu','menu_section','menu_item'])
        item=records[-1]
        self.assertEqual(item['source_native_id'],'007')
        self.assertIsNone(item['recipe_id'])
        self.assertIsNone(item['steps'])
        self.assertIsNone(item['price'])
        self.assertEqual(item['price_observations'][0]['kind'],'theoretical_production_cost')
        self.assertEqual(item['price_observations'][0]['amount'],'3,50')
        self.assertIsNone(item['source_assertions']['menuplatallergene'])
        self.assertEqual(item['raw_source'],row)
        _,citations,_=self.run_sources('citations',[source])
        self.assertEqual(len(citations),1)
        self.assertIn(('cites','citations',citations[0]['id']),links)
        self.assertIn(item['id'],[r['target_id'] for r in citations[0]['relations']])

    def test_begles_exact_scoped_join_and_ingredient_basis_not_inferred(self):
        menu=self.source('menu.json',json.dumps([begles_menu()]))
        dishes=self.source('dish.json',json.dumps([begles_dish()]),role='dish')
        _,records,_=self.run_sources('recipes',[menu,dishes])
        item=next(x for x in records if x['kind']=='menu_item')
        dish=next(x for x in records if x['kind']=='dish_composition')
        relation=next(x for x in item['relations'] if x['kind']=='source_dish_reference')
        self.assertEqual(relation['target_id'],dish['id'])
        self.assertEqual(relation['target_identity_kind'],'acquired_scoped_id')
        self.assertEqual(relation['target_scope'],dish['source_scope'])
        self.assertEqual(relation['target_adapter'],dish['source_family'])
        _,ingredients,_=self.run_sources('ingredients',[dishes])
        self.assertEqual(ingredients[0]['raw_text'],'pois, lait')
        self.assertIsNone(ingredients[0]['nutrition']['basis'])
        self.assertIsNone(ingredients[0]['quantity'])
        self.assertIsNone(ingredients[0]['normalized_ingredient_id'])

    def test_begles_missing_scope_preserves_row_but_does_not_guess(self):
        row=begles_menu()
        del row['menuetablissementsiret']
        source=self.source('menu.json',json.dumps([row]))
        result,records,_=self.run_sources('recipes',[source])
        item=next(x for x in records if x['kind']=='menu_item')
        self.assertFalse(any(x['kind']=='source_dish_reference' for x in item['relations']))
        self.assertEqual(result['sources'][0]['diagnostics']['schema_needs'],{'acquired_menu_ambiguous_join_scope':1})

    def test_toulouse_audience_course_and_order_never_collapsed(self):
        rows=[toulouse_menu(),toulouse_menu(libelle_population_cible='maternelle'),
              toulouse_menu(datemenu='2026-10-23'),toulouse_menu()]
        source=self.source('menus.json',json.dumps(rows),family='fr_toulouse_menus')
        _,records,_=self.run_sources('recipes',[source])
        self.assertEqual(sum(r['kind']=='menu' for r in records),3)
        self.assertEqual(sum(r['kind']=='menu_item' for r in records),4)
        self.assertEqual(sum(r['kind']=='menu_section' for r in records),3)
        self.assertEqual({r['ordinal'] for r in records if r['kind']=='menu_section'},{2})

    def test_toulouse_no_suffix_stripping_and_no_name_link(self):
        menu=self.source('menus.json',json.dumps([toulouse_menu()]),family='fr_toulouse_menus')
        dish=self.source('dishes.json',json.dumps([{'code_plat':'007','libelle_plat':'Plat généré',
            'code_recette':'R01','libelle_recette':'Générée','numero':'001'}]),family='fr_toulouse_menus',role='dish')
        _,records,_=self.run_sources('recipes',[menu,dish])
        item=next(x for x in records if x['kind']=='menu_item')
        anchor=next(x for x in records if x['kind']=='dish_composition')
        link=next(x for x in item['relations'] if x['kind']=='source_dish_reference')
        self.assertNotEqual(link['target_id'],anchor['id'])
        self.assertFalse(any(x['kind']=='recipe' for x in records))

    def test_toulouse_ingredient_composition_and_technical_sheet_exact_links(self):
        dish=self.source('dishes.json',json.dumps([{'code_plat':'007P','libelle_plat':'Generated',
            'code_recette':'R01'}]),family='fr_toulouse_menus',role='dish')
        ingredient=self.source('ingredients.json',json.dumps([{'code_denree':'D01','libelle_denree':'Lait',
            'code_recette':'R01','lait':True,'gluten':None,'soja':'0','url':'https://example.test/no-fetch.pdf'}]),
            family='fr_toulouse_menus',role='ingredient')
        tech=self.source('sheets.json',json.dumps([{'code_denree':'D01','description':'Generated metadata',
            'filename':'https://example.test/no-fetch.pdf'}]),family='fr_toulouse_menus',role='technical_sheet_reference')
        _,recipe_rows,_=self.run_sources('recipes',[dish])
        _,ingredient_rows,_=self.run_sources('ingredients',[ingredient])
        _,citation_rows,_=self.run_sources('citations',[tech])
        composition=next(x for x in recipe_rows if x['kind']=='composition_reference')
        anchor=next(x for x in ingredient_rows if x['kind']=='ingredient_source_entity')
        observation=next(x for x in ingredient_rows if x['kind']=='ingredient_source_observation')
        reference=next(x for x in citation_rows if x['kind']=='technical_sheet_reference')
        self.assertIn(composition['id'],[x['target_id'] for x in observation['relations']])
        self.assertIn(anchor['id'],[x['target_id'] for x in reference['relations']])
        self.assertEqual(observation['allergens'],{'lait':True,'gluten':None,'soja':'0'})
        self.assertFalse(reference['content_available'])
        self.assertFalse(observation['linked_documents_fetched'])

    def test_provider_native_type_and_scope_are_not_coerced(self):
        source={'id':'a','acquired_adapter':'fr_toulouse_menus'}
        other={'id':'b','acquired_adapter':'fr_begles_menus'}
        self.assertNotEqual(adapter.entity_id(source,'dish',1),adapter.entity_id(source,'dish','1'))
        self.assertNotEqual(adapter.entity_id(source,'dish','001'),adapter.entity_id(source,'dish','1'))
        self.assertNotEqual(adapter.entity_id(source,'dish','1'),adapter.entity_id(other,'dish','1'))
        self.assertNotEqual(adapter.entity_id(other,'dish','1',['a']),adapter.entity_id(other,'dish','1',['b']))

    def test_bad_rows_isolated_unknown_schema_sanitized_and_rerun_idempotent(self):
        rows=[begles_menu(),12,{'secret_fixture_payload':'do not report'},begles_menu()]
        source=self.source('menu.json',json.dumps(rows))
        result,records,_=self.run_sources('recipes',[source])
        self.assertEqual(sum(x['kind']=='menu_item' for x in records),2)
        self.assertEqual(result['status'],'partial')
        self.assertEqual(result['errors'],2)
        public=json.dumps(result)
        self.assertNotIn('secret_fixture_payload',public)
        self.assertNotIn(str(self.root),public)
        result2,records2,_=self.run_sources('recipes',[source])
        self.assertEqual(result2['written'],0)
        self.assertEqual(result2['status'],'partial')
        self.assertEqual(len(records2),len(records))

    def test_jsonl_malformed_line_does_not_drop_next_row(self):
        source=self.source('menu.jsonl',json.dumps(begles_menu())+'\n{broken\n'+json.dumps(begles_menu())+'\n')
        result,records,_=self.run_sources('recipes',[source])
        self.assertEqual(sum(x['kind']=='menu_item' for x in records),2)
        self.assertEqual(result['errors'],1)

    def test_duplicate_json_key_and_nonfinite_member_do_not_drop_siblings(self):
        good=json.dumps(begles_menu())
        source=self.source('menu.json','['+good+',{"menudate":"a","menudate":"b"},'+good+',{"x":NaN},'+good+']')
        result,records,_=self.run_sources('recipes',[source])
        self.assertEqual(sum(x['kind']=='menu_item' for x in records),3)
        self.assertEqual(result['errors'],2)
        self.assertEqual(result['sources'][0]['diagnostics']['reason_counts'],{'acquired_menu_json_record_invalid':2})

    def test_csv_semicolon_bom_multiline_and_decimal_comma(self):
        row=begles_menu()
        row['menuplatnom']='Soupe\naux légumes'
        row['menuplatallergene']='null'
        buf=io.StringIO()
        writer=csv.DictWriter(buf,fieldnames=list(row),delimiter=';')
        writer.writeheader();writer.writerow(row)
        source=self.source('menu.csv',('\ufeff'+buf.getvalue()).encode('utf-8'))
        result,records,_=self.run_sources('recipes',[source])
        self.assertEqual(result['errors'],0)
        item=next(x for x in records if x['kind']=='menu_item')
        self.assertEqual(item['title'],'Soupe\naux légumes')
        self.assertEqual(item['source_native_id'],'007')
        self.assertEqual(item['source_assertions']['menuplatallergene'],'null')
        self.assertEqual(item['price_observations'][0]['amount'],'3,50')

    def test_csv_declared_encoding_and_width_error_isolation(self):
        row=begles_menu();buf=io.StringIO()
        writer=csv.DictWriter(buf,fieldnames=list(row),delimiter=';')
        writer.writeheader();writer.writerow(row)
        buf.write('bad;row\n');writer.writerow(row)
        source=self.source('menu.csv',buf.getvalue().encode('cp1252'),encoding='cp1252')
        result,records,_=self.run_sources('recipes',[source])
        self.assertEqual(sum(x['kind']=='menu_item' for x in records),2)
        self.assertEqual(result['sources'][0]['diagnostics']['reason_counts']['acquired_menu_csv_row_width'],1)

    def test_csv_duplicate_headers_refused(self):
        source=self.source('menu.csv','menudate;menudate\na;b\n')
        result,records,_=self.run_sources('recipes',[source])
        self.assertFalse(records)
        self.assertEqual(result['sources'][0]['diagnostics']['reason_counts'],{'acquired_menu_csv_duplicate_header':1})

    def test_cnous_documented_hierarchy_ingredients_and_source_codes(self):
        source=self.source('region.xml',cnous_xml(),family='fr_cnous_menus')
        result,records,links=self.run_sources('recipes',[source])
        self.assertEqual(result['errors'],0)
        self.assertEqual(result['sources'][0]['diagnostics']['schema_needs'],{})
        self.assertEqual(sum(x['kind']=='menu' for x in records),2)
        self.assertEqual(sum(x['kind']=='menu_section' for x in records),5)
        items=[x for x in records if x['kind']=='menu_item']
        self.assertEqual([x['title'] for x in items],['Soupe & pois','Crudités','Fruit','Suite'])
        self.assertEqual(items[0]['source_codes'],['lait'])
        self.assertTrue(any(k=='contains_menu_entry' for k,_,_ in links))
        _,ingredients,_=self.run_sources('ingredients',[source])
        self.assertEqual(len(ingredients),1)
        self.assertEqual(ingredients[0]['raw_text'],'pois, lait')
        self.assertIsNone(ingredients[0]['quantity'])
        self.assertIsNone(ingredients[0]['recipe_id'])
        self.assertEqual(items[0]['ingredient_statement'],'pois, lait')

    def test_cnous_nested_restaurant_namespaces_and_unicode(self):
        xml='<x:root xmlns:x="urn:test"><x:restaurant id="0007"><x:nom>Généré</x:nom><x:menu date="2026-10-22"><x:repas nom="soir"><x:plats nom="Plats"><x:plat><x:nom>Crème</x:nom></x:plat></x:plats></x:repas></x:menu></x:restaurant></x:root>'
        source=self.source('region.xml',xml,family='fr_cnous_menus')
        result,records,_=self.run_sources('recipes',[source])
        self.assertEqual(result['errors'],0)
        menu=next(x for x in records if x['kind']=='menu')
        self.assertEqual(menu['venue_native_id'],'0007')
        self.assertEqual(menu['xml_context'][-1]['content'][0]['content'],['Généré'])

    def test_cnous_dtd_external_entity_and_utf16_refused(self):
        for n,raw in enumerate([
            '<!DOCTYPE root [<!ENTITY x SYSTEM "file:///not-to-read">]><root><menu>&x;</menu></root>',
            '<!DOCTYPE root SYSTEM "https://example.test/never-fetch"><root/>',
            '<?xml version="1.0" encoding="UTF-16"?><!DOCTYPE root [<!ENTITY x "boom">]><root/>'.encode('utf-16')]):
            source=self.source(str(n)+'.xml',raw,family='fr_cnous_menus')
            result,records,_=self.run_sources('recipes',[source])
            self.assertFalse(records)
            self.assertEqual(result['sources'][0]['diagnostics']['reason_counts'],{'acquired_menu_xml_dtd_forbidden':1})

    def test_cnous_bad_tail_retains_complete_prior_menu(self):
        source=self.source('region.xml',cnous_xml().replace('</root>','<broken>'),family='fr_cnous_menus')
        result,records,_=self.run_sources('recipes',[source])
        self.assertEqual(sum(x['kind']=='menu' for x in records),2)
        self.assertEqual(result['status'],'partial')
        self.assertEqual(result['sources'][0]['diagnostics']['reason_counts'],{'acquired_menu_xml_invalid':1})

    def test_cnous_empty_directory_not_claimed_as_menu(self):
        source=self.source('region.xml','<root><restaurant id="7"/></root>',family='fr_cnous_menus')
        result,records,_=self.run_sources('recipes',[source])
        self.assertFalse(records)
        self.assertEqual(result['sources'][0]['diagnostics']['reason_counts'],{'acquired_menu_xml_no_menu_nodes':1})

    def test_cnous_size_cap_and_depth_are_bounded(self):
        source=self.source('size.xml',cnous_xml(),family='fr_cnous_menus',max_expanded_bytes=20)
        result,records,_=self.run_sources('recipes',[source])
        self.assertFalse(records)
        self.assertEqual(result['sources'][0]['diagnostics']['reason_counts'],{'acquired_menu_source_size_cap':1})
        deep=self.source('deep.xml','<root>'+'<a>'*70+'</a>'*70+'</root>',family='fr_cnous_menus')
        result,_,_=self.run_sources('recipes',[deep])
        self.assertEqual(result['sources'][0]['diagnostics']['reason_counts'],{'acquired_menu_xml_depth_cap':1})

    def test_restricted_unverified_loaded_and_non_candidate_not_read(self):
        sources=[self.source(str(i)+'.json',json.dumps([begles_menu()]),**kwargs) for i,kwargs in enumerate([
            {'restricted':True},{'loaded':True},{'metadata':{'acquisition':{'verified':False}}},
            {'disposition':'metadata-only'}])]
        with patch.object(adapter,'_json_rows',side_effect=AssertionError('must not open')):
            result,records,_=self.run_sources('recipes',sources)
        self.assertFalse(records)
        self.assertEqual(result['skipped'],4)

    def test_unsupported_descriptor_reports_fixed_reason_not_only_class(self):
        source=self.source('menu.bin','generated',format='binary')
        result,records,_=self.run_sources('recipes',[source])
        self.assertFalse(records)
        self.assertEqual(result['errors'],1)
        self.assertEqual(result['sources'][0]['diagnostics']['reason_counts'],{'acquired_menu_unsupported_format':1})

    def test_resource_cap_resume_uses_same_projection_order(self):
        source=self.source('menu.json',json.dumps([begles_menu(),begles_menu(),begles_menu()]))
        first,records,_=self.run_sources('recipes',[source],{'max_rows_per_source':2})
        self.assertEqual(first['status'],'partial')
        self.assertEqual(len(records),2)
        second,records,_=self.run_sources('recipes',[source])
        self.assertEqual(second['status'],'complete')
        self.assertEqual(len(records),5)
        third,_,_=self.run_sources('recipes',[source])
        self.assertEqual(third['written'],0)

    def test_same_native_code_multiple_observations_not_overwritten(self):
        rows=[begles_dish(),dict(begles_dish(),platproduitnom='Second source ingredient')]
        source=self.source('dishes.json',json.dumps(rows),role='dish')
        _,records,_=self.run_sources('recipes',[source])
        self.assertEqual(sum(x['kind']=='dish_composition' for x in records),1)
        self.assertEqual(sum(x['kind']=='dish_composition_observation' for x in records),2)
        _,ingredients,_=self.run_sources('ingredients',[source])
        self.assertEqual(len(ingredients),2)


if __name__=='__main__':
    unittest.main()
