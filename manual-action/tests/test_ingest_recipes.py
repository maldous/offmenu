"""Generated fixtures only; no retained-source, network or runtime execution."""
import csv
import gzip
import hashlib
import io
import json
from pathlib import Path
import sqlite3
import sys
import tempfile
import threading
import time
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import ingest_recipes as adapter
from ingest_store import DomainStore
from ingest_engine import IngestContext


def recipe(title='Generated soup', **extra):
    return {'name': title, 'ingredients': ['1 cup beans', 'salt, to taste'],
            'instructions': ['Mix.', 'Serve.'], **extra}


class AdapterTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.config = {'reserve_bytes': 0, 'batch_size': 2, 'max_record_bytes': 16*1024*1024}

    def source(self, name, content, fmt=None, **extra):
        path = self.root / name
        path.write_bytes(content if isinstance(content, bytes) else content.encode())
        return {'id': name, 'path': str(path), 'format': fmt or path.suffix[1:],
                'provider': 'generated', 'domains': ['recipes', 'ingredients'], **extra}

    def run_source(self, domain, sources):
        context = IngestContext(domain, self.root, self.config, threading.Event(), lambda *args: None, time.monotonic())
        with DomainStore(domain, self.root, self.config) as store:
            context.store = store
            summary = adapter.run_domain(domain, sources, context)
            rows = [json.loads(row[0]) for row in store.db.execute('SELECT payload_json FROM records ORDER BY row_number')]
            links = store.db.execute('SELECT kind,target_domain,target_id FROM relations').fetchall()
        return summary, rows, links

    def test_json_array_multiprovider_duplicate_bad_record_and_rerun(self):
        source = self.source('recipes.json', json.dumps([recipe(), recipe(), 9,
            {'@type':'Recipe','name':'Second','recipeIngredient':['2 g salt'],
             'recipeInstructions':[{'@type':'HowToSection','name':'Mixing','itemListElement':[{'@type':'HowToStep','text':'Mix slowly.'}]}]}]))
        result, rows, links = self.run_source('recipes', [source])
        self.assertEqual(len(rows), 2)
        self.assertEqual(result['errors'], 1)
        self.assertEqual(result['skipped'], 1)
        self.assertEqual(rows[1]['steps'][0]['source_section'], 'Mixing')
        self.assertEqual(len(links), 3)
        result2, rows2, _ = self.run_source('recipes', [source])
        self.assertEqual(len(rows2), 2)
        self.assertEqual(result2['written'], 0)
        self.assertGreater(result2['errors'], 0)

    def test_native_unitools_language_maps_and_exact_number_lexeme(self):
        raw = '{"attribution":"Generated author","recipes":[{"slug":"native","name":{"en":"Soup","ru":"Суп"},"baseServings":4.00,"ingredients":[{"name":{"en":"beans","ru":"фасоль"},"quantity":1.00e+2,"unit":"g"}],"steps":[{"text":{"en":"Stir.","ru":"Мешать."}}]}]}'
        source = self.source('native.json', raw)
        _, rows, _ = self.run_source('recipes', [source])
        record = rows[0]
        self.assertEqual(record['title_languages']['ru'], 'Суп')
        self.assertIn('1.00e+2', record['raw_source_json'])
        self.assertEqual(record['ingredients'][0]['quantity_lexeme'], '1.00e+2')
        self.assertEqual(record['provenance']['container_metadata']['attribution'], 'Generated author')
        self.assertFalse(record['translation_performed'])
        _, mentions, links = self.run_source('ingredients', [source])
        self.assertEqual(mentions[0]['id'], record['ingredients'][0]['id'])
        self.assertEqual(mentions[0]['normalized_ingredient_id'], None)
        self.assertIn(('ingredient_of','recipes',record['id']), links)

    def test_historical_normalized_packet_keeps_outer_identity_and_provenance(self):
        envelope = {'schemaVersion':'1.0','kind':'recipe','id':'source-native-id','countries':['ZZ'],
                    'provenance':{'source':'generated-repository','license':'generated-license'},
                    'data':{'recipeSchema':'offmenu-recipe/1','name':'Generated historical recipe',
                            'languages':['en'],'yield':{'value':2,'unit':'portion'},
                            'ingredients':[{'name':'beans','ingredientId':'source-candidate:beans', 'amount':100,'unit':'g',
                                            'originalText':'one source cup of beans','foodMatchStatus':'candidate-alias',
                                            'sourceQuantity':{'value':1,'unit':'cup','status':'parsed'}}],'directions':['Stir.'],
                            'qualificationStatus':'unknown','automaticPlanningEligible':False}}
        source = self.source('normalized.jsonl.gz', gzip.compress((json.dumps([envelope])+'\n').encode()), fmt='jsonl', compression='gzip')
        _, rows, _ = self.run_source('recipes', [source])
        self.assertEqual(rows[0]['title'], 'Generated historical recipe')
        self.assertEqual(rows[0]['raw_source'], envelope)
        self.assertEqual(rows[0]['provenance']['source_provenance'], envelope['provenance'])
        self.assertEqual(rows[0]['source_country_assertions'], ['ZZ'])
        self.assertEqual(rows[0]['language'], 'en')
        mention = rows[0]['ingredients'][0]
        self.assertEqual(mention['raw_text'], 'one source cup of beans')
        self.assertEqual(mention['unit'], 'cup')
        self.assertEqual(mention['source_normalized_assertions']['unit'], 'g')
        self.assertEqual(mention['reported_food_identity'], 'source-candidate:beans')
        self.assertIsNone(mention['normalized_ingredient_id'])

    def test_jsonl_invalid_line_keeps_following_record(self):
        source = self.source('partial.jsonl', json.dumps(recipe())+'\n{bad}\n'+json.dumps(recipe('Later'))+'\n')
        result, rows, _ = self.run_source('recipes', [source])
        self.assertEqual(len(rows), 2)
        self.assertEqual(result['errors'], 1)
        self.assertEqual(result['status'], 'partial')

    def test_csv_json_array_fields_and_raw_quantity_not_inferred(self):
        buffer = io.StringIO()
        writer = csv.DictWriter(buffer, fieldnames=['title','ingredients','directions'])
        writer.writeheader()
        writer.writerow({'title':'CSV soup','ingredients':json.dumps(['one pinch salt, optional']), 'directions':json.dumps(['Stir.'])})
        source = self.source('recipes.csv', buffer.getvalue())
        _, rows, _ = self.run_source('recipes', [source])
        self.assertEqual(rows[0]['ingredients'][0]['raw_text'], 'one pinch salt, optional')
        self.assertIsNone(rows[0]['ingredients'][0]['quantity'])
        self.assertIsNone(rows[0]['ingredients'][0]['unit'])

    def test_gzip_jsonl(self):
        source = self.source('recipes.jsonl.gz', gzip.compress((json.dumps(recipe())+'\n').encode()), fmt='jsonl', compression='gzip')
        _, rows, _ = self.run_source('recipes', [source])
        self.assertEqual(len(rows), 1)

    def test_html_multiple_jsonld_graph_and_bad_script_isolated(self):
        graph = {'@graph':[{'@type':'WebPage','name':'Page'}, dict(recipe('First'), **{'@type':'Recipe'}), dict(recipe('Second'), **{'@type':'Recipe'})]}
        source = self.source('cached.html', '<script type="application/ld+json">{bad}</script><script type="application/ld+json">'+json.dumps(graph)+'</script>')
        result, rows, _ = self.run_source('recipes', [source])
        self.assertEqual(len(rows), 2)
        self.assertEqual(result['errors'], 1)
        self.assertEqual(rows[0]['provenance']['container_metadata']['representation'], 'html-jsonld-source-script')

    def test_menu_nested_relationships_and_prices_are_raw(self):
        menu = {'@type':'Menu','name':'Fixture menu','hasMenuSection':[{'@type':'MenuSection','name':'Lunch','hasMenuItem':[{'@type':'MenuItem','name':'Soup','offers':{'price':'3,50','priceCurrency':'EUR'}}]}]}
        source = self.source('menu.json', json.dumps(menu))
        _, rows, links = self.run_source('recipes', [source])
        self.assertEqual(len(rows), 3)
        self.assertEqual(len(links), 2)
        self.assertEqual(rows[-1]['price']['price'], '3,50')

    def test_partial_pdf_cache_does_not_invent_ingredients_or_steps(self):
        row = {'cacheVersion':adapter.CACHE_VERSION, 'recordId':'cache-one', 'importReady':False,
               'ingredientLines':None,'orderedSteps':None,'quantityInterpretations':None,
               'sourceDocumentLanguage':'en','sections':[{'kind':'title','text':'Exact raw title\n'},
               {'kind':'ingredients-section','text':'Unsegmented two-column ingredients'},
               {'kind':'method-section','text':'Raw method'}]}
        source = self.source('cache.jsonl', json.dumps(row)+'\n')
        _, rows, links = self.run_source('recipes', [source])
        self.assertEqual(rows[0]['title'], 'Exact raw title\n')
        self.assertIsNone(rows[0]['ingredient_count'])
        self.assertIsNone(rows[0]['step_count'])
        self.assertEqual(links, [])
        ingredient_result, ingredients, _ = self.run_source('ingredients', [source])
        self.assertEqual(ingredients, [])
        self.assertEqual(ingredient_result['status'], 'partial')
        self.assertGreater(ingredient_result['skipped'], 0)

    def test_unsupported_pdf_does_not_block_next_source(self):
        bad = self.source('raw.pdf', b'%PDF-1.4\nsynthetic')
        good = self.source('good.json', json.dumps(recipe()))
        result, rows, _ = self.run_source('recipes', [bad, good])
        self.assertEqual(len(rows), 1)
        self.assertEqual(result['status'], 'partial')
        self.assertGreater(result['errors'], 0)

    def test_restricted_missing_file_is_not_opened(self):
        source = {'id':'held','path':str(self.root/'absent.json'),'format':'json','restricted':True}
        result, rows, _ = self.run_source('recipes', [source])
        self.assertEqual(result['skipped'], 1)
        self.assertEqual(rows, [])

    def test_loaded_flag_never_overrides_incomplete_product_hold(self):
        source = {'id':'held-off','path':str(self.root/'missing.sqlite'),'format':'sqlite',
                  'provider':'openfoodfacts','loaded':True,'disposition':'incomplete-hold',
                  'domains':['barcodes','ingredients']}
        result, rows, _ = self.run_source('ingredients', [source])
        self.assertEqual(result['skipped'], 1)
        self.assertEqual(result['errors'], 0)
        self.assertEqual(rows, [])

    def test_direct_food_entities_remain_distinct_from_mentions(self):
        source = self.source('foods.json', json.dumps({'foods':[{'fdcId':42,'description':'Beans','foodNutrients':[{'nutrient':{'name':'Protein'},'amount':7}]}]}), domains=['ingredients'])
        _, rows, _ = self.run_source('ingredients', [source])
        self.assertEqual(rows[0]['kind'], 'ingredient_source_entity')
        self.assertIsNone(rows[0]['normalized_ingredient_id'])
        self.assertEqual(rows[0]['nutrition'][0]['amount'], 7)

    def test_recipe_leads_are_not_ingredient_entities(self):
        source = self.source('leads.jsonl', json.dumps({'name':'Recipe lead','url':'https://example.invalid/recipe'})+'\n')
        result, rows, _ = self.run_source('ingredients', [source])
        self.assertEqual(rows, [])
        self.assertEqual(result['skipped'], 1)

    def test_wikitext_explicit_sections_preserve_raw_lines(self):
        source = self.source('wiki.jsonl', json.dumps({'title':'Wiki soup','wikitext':'== Ingredients ==\n* 2 cups beans\n== Procedure ==\n# Stir slowly.\n'})+'\n')
        _, rows, _ = self.run_source('recipes', [source])
        self.assertEqual(rows[0]['ingredients'][0]['raw_text'], '* 2 cups beans')
        self.assertEqual(rows[0]['steps'][0]['raw_text'], '# Stir slowly.')

    def test_wikimedia_pages_slots_and_notes_not_mislabelled_steps(self):
        value = {'query':{'pages':{'123':{'title':'Cached wiki soup','revisions':[{'slots':{'main':{'*':'== Ingredients ==\n* beans\n== Procedure ==\n# Stir.\n== Notes ==\nNot a step.'}}}]}}}}
        source = self.source('wikimedia.json', json.dumps(value))
        _, rows, _ = self.run_source('recipes', [source])
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]['steps'], [{'ordinal':0,'raw_text':'# Stir.','source_section':None,'raw_source':'# Stir.'}])

    def test_markdown_explicit_recipe_sections(self):
        source = self.source('recipe.md', '# Generated bean soup\n\nSource note.\n\n## Ingredients\n- beans\n\n## Instructions\n1. Stir.\n\n## Notes\nNot a step.\n', fmt='markdown')
        _, rows, _ = self.run_source('recipes', [source])
        self.assertEqual(rows[0]['title'], 'Generated bean soup')
        self.assertEqual(rows[0]['steps'][0]['raw_text'], '1. Stir.')
        self.assertEqual(rows[0]['step_count'], 1)

    def test_csv_python_literal_lists_not_executed(self):
        buffer = io.StringIO()
        writer = csv.DictWriter(buffer, fieldnames=['name','ingredients','steps'])
        writer.writeheader(); writer.writerow({'name':'Generated soup','ingredients':"['beans', 'salt']",'steps':"['Mix.', 'Serve.']"})
        source = self.source('python-lists.csv', buffer.getvalue())
        _, rows, _ = self.run_source('recipes', [source])
        self.assertEqual(rows[0]['ingredient_count'], 2)
        self.assertEqual(rows[0]['step_count'], 2)

    def test_bad_nested_wrapper_record_does_not_drop_later_sibling(self):
        source = self.source('nested.jsonl', json.dumps({'records':[recipe(), False, recipe('Last')]})+'\n')
        result, rows, _ = self.run_source('recipes', [source])
        self.assertEqual(len(rows), 2)
        self.assertGreater(result['errors'], 0)

    def test_readonly_sqlite_payload_source(self):
        path = self.root/'retained.sqlite'
        db = sqlite3.connect(path)
        db.execute('CREATE TABLE recipes(id TEXT, payload_json TEXT)')
        db.execute('INSERT INTO recipes VALUES(?,?)', ('one', json.dumps(recipe())))
        db.commit(); db.close()
        before = hashlib.sha256(path.read_bytes()).hexdigest()
        source = {'id':'retained','path':str(path),'format':'sqlite','provider':'generated'}
        _, rows, _ = self.run_source('recipes', [source])
        self.assertEqual(len(rows), 1)
        self.assertEqual(before, hashlib.sha256(path.read_bytes()).hexdigest())

    def test_duplicate_files_have_same_entity_id_and_source_provenance(self):
        a = self.source('first.json', json.dumps([recipe()]))
        b = self.source('copy.json', json.dumps([recipe()]))
        _, rows, _ = self.run_source('recipes', [a,b])
        self.assertEqual(len({r['id'] for r in rows}), 1)
        self.assertEqual({r['provenance']['catalog_source_id'] for r in rows}, {'first.json','copy.json'})

    def test_vendor_parser_and_schema_pins(self):
        root = Path(adapter.__file__).with_name('reviewed_recipe_sources')
        for name, digest in [('source_faithful_parse.py', adapter.HTML_PARSER_SHA256),('source_recipe_template.schema.json',adapter.HTML_SCHEMA_SHA256)]:
            self.assertEqual(hashlib.sha256((root/name).read_bytes()).hexdigest(), digest)

    def test_root_metadata_after_array_is_preserved(self):
        source = self.source('trailing.json', json.dumps({'recipes':[recipe()], 'licenseUrl':'https://example.invalid/license', 'attribution':'Generated source author'}))
        _, rows, _ = self.run_source('recipes', [source])
        metadata = [r for r in rows if r['kind'] == 'source_metadata']
        self.assertEqual(metadata[0]['raw_source']['attribution'], 'Generated source author')

    def test_loaded_off_sqlite_derives_labels_and_assertions_readonly(self):
        path = self.root/'off.sqlite'
        db = sqlite3.connect(path)
        db.execute('CREATE TABLE products(code TEXT, raw_json TEXT)')
        product = {'code':'123','product_name':'Generated cereal','ingredients_text':'oats, salt (trace)',
                   'ingredients':[{'id':'en:oats','text':'oats','percent_estimate':98}]}
        db.execute('INSERT INTO products VALUES(?,?)', ('123',json.dumps(product)))
        db.commit(); db.close()
        before = hashlib.sha256(path.read_bytes()).hexdigest()
        source = {'id':'off-existing','path':str(path),'format':'sqlite','provider':'openfoodfacts',
                  'loaded':True,'existing_store':True,'disposition':'existing-store','domains':['barcodes','ingredients']}
        _, rows, links = self.run_source('ingredients', [source])
        self.assertEqual({r['kind'] for r in rows}, {'ingredient_label_mention','ingredient_source_assertion'})
        self.assertEqual(rows[0]['raw_text'], 'oats, salt (trace)')
        self.assertEqual(rows[1]['source_asserted_ingredient_id'], 'en:oats')
        self.assertIsNone(rows[1]['normalized_ingredient_id'])
        self.assertEqual(len(links), 2)
        self.assertEqual(before, hashlib.sha256(path.read_bytes()).hexdigest())
        repeat, again, _ = self.run_source('ingredients', [source])
        self.assertEqual(repeat['written'], 0)
        self.assertEqual(len(again), 2)

    def test_usda_label_is_not_comma_split(self):
        source = self.source('usda.jsonl', json.dumps({'fdcId':53,'description':'Generated food','ingredients':'water, salt, spice blend (cumin, pepper)'})+'\n', provider='usda', domains=['barcodes','ingredients'])
        _, rows, _ = self.run_source('ingredients', [source])
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]['kind'], 'ingredient_label_mention')
        self.assertEqual(rows[0]['raw_text'], 'water, salt, spice blend (cumin, pepper)')

    def test_stream_multiple_chunks_and_resume_batches(self):
        # Significantly exceeds the 64 KiB reader chunk. No bulk fixture on disk.
        source = self.source('many.json', json.dumps([recipe('Generated '+str(i)) for i in range(1200)]))
        self.config['max_rows_per_source'] = 3
        first, rows, _ = self.run_source('recipes', [source])
        self.assertEqual(len(rows), 3)
        self.assertEqual(first['status'], 'partial')
        self.config['max_rows_per_source'] = 0
        final, rows, _ = self.run_source('recipes', [source])
        self.assertEqual(len(rows), 1200)
        self.assertEqual(final['written'], 1197)
        self.assertEqual(final['status'], 'complete')

    def test_bounded_duplicate_cache_still_sqlite_idempotent(self):
        self.config['dedup_cache_entries'] = 2
        source = self.source('duplicates.json', json.dumps([recipe('A'),recipe('B'),recipe('C'),recipe('A')]))
        _, rows, _ = self.run_source('recipes', [source])
        self.assertEqual(len(rows), 3)


if __name__ == '__main__':
    unittest.main()
