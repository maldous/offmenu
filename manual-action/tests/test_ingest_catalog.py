import importlib.util
import json
import os
from pathlib import Path
import sqlite3
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from ingest_catalog import discover_sources, KNOWN_FULL_IDENTIFIER_DB


class CatalogTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='offmenu-catalog-test-')
        self.root = Path(self.tmp.name) / 'retained'
        self.root.mkdir()

    def tearDown(self):
        self.tmp.cleanup()

    def put(self, name, body):
        target = self.root / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(body)
        return target

    def discover(self, **kw):
        return discover_sources({'roots': [str(self.root)], 'project_reports': [], **kw})

    def byname(self, result):
        return {Path(x['path']).name: x for x in result['sources']}

    def test_multiple_formats_and_provider_domains(self):
        self.put('world-recipes-common-input-20261014/manifest.json', json.dumps({'sourceId': 'world-recipes', 'license': 'CC BY-SA 4.0'}))
        self.put('world-recipes-common-input-20261014/recipes.jsonl', '{"id":"r1","data":{"ingredients":["egg"],"directions":["mix"]}}\n')
        self.put('usda-2026-04/foods.csv', 'fdc_id,description\n1,egg\n')
        self.put('fineli-20.0/nutrients.tsv', 'food_id\tnutrient_name\n1\tprotein\n')
        self.put('overture-food-places-2026-09-23.1/part.zstd.parquet', 'PAR1')
        self.put('recipe-wikis-20261013/page.html', '<html><script type="application/ld+json">{"@type":"Recipe"}</script></html>')
        self.put('recipe-wikis-20261013/book.pdf', '%PDF-1.7')
        self.put('foodon/foodon.ttl', '@prefix')
        result = self.discover()
        got = self.byname(result)
        self.assertFalse(result['truncated'])
        self.assertEqual(got['recipes.jsonl']['license'], 'CC BY-SA 4.0')
        self.assertIn('recipes', got['recipes.jsonl']['domains'])
        self.assertIn('barcodes', got['foods.csv']['domains'])
        self.assertEqual(got['part.zstd.parquet']['provider'], 'overture')
        self.assertEqual(got['part.zstd.parquet']['format'], 'parquet')
        self.assertEqual(got['page.html']['disposition'], 'candidate')
        self.assertEqual(got['book.pdf']['format'], 'pdf')
        self.assertEqual(got['manifest.json']['disposition'], 'metadata-only')
        self.assertEqual(set(result['domain_summary']), {'barcodes','ingredients','recipes','dietary','user_profiles','inventory','suppliers','citations'})

    def test_unknown_license_not_global_gate(self):
        self.put('recipes.jsonl', '{"id":"a","recipeIngredient":["egg"]}\n')
        got = self.byname(self.discover())['recipes.jsonl']
        self.assertIsNone(got['license'])
        self.assertEqual(got['disposition'], 'candidate')

    def test_manifest_reference_inside_root_and_trusted_external(self):
        outside = Path(self.tmp.name) / 'existing-retained'
        outside.mkdir()
        (outside / 'recipes.jsonl').write_text('{"recipeIngredient":["egg"]}\n')
        report = Path(self.tmp.name) / 'trusted-report.json'
        report.write_text(json.dumps({'assets': [{'path': str(outside), 'sourceId': 'unitools'}]}))
        result = self.discover(project_reports=[str(report)], allowed_report_roots=[str(outside)])
        got = self.byname(result)
        self.assertEqual(got['recipes.jsonl']['provider'], 'unitools')
        # Ordinary data manifests cannot widen the selected scope themselves.
        self.put('manifest.json', json.dumps({'assets': [{'path': str(outside)}]}))
        result = self.discover()
        self.assertNotIn('recipes.jsonl', self.byname(result))
        self.assertTrue(any(e['code'] == 'manifest_reference_outside_selected_scope' for e in result['errors']))

    def test_manifest_references_metadata_chain(self):
        child = self.put('reports/asset-inventory.json', json.dumps({'files': [{'path': str(self.root / 'data' / 'source.jsonl'), 'sourceId': 'unitools'}]}))
        self.put('data/source.jsonl', '{"recipeIngredient":["egg"]}\n')
        self.put('manifest.json', json.dumps({'inventoryPath': str(child)}))
        result = self.discover()
        self.assertTrue(result['complete'])
        self.assertEqual(sum(Path(x['path']).name == 'source.jsonl' for x in result['sources']), 1)

    def test_path_inode_and_small_checksum_duplicates(self):
        a = self.put('recipes/a.jsonl', '{"recipeIngredient":["egg"]}\n')
        os.link(a, a.with_name('b.jsonl'))
        self.put('recipes/c.jsonl', a.read_text())
        self.put('manifest.json', json.dumps({'files': [{'path': str(a)}, {'path': str(a)}]}))
        result = self.discover()
        self.assertEqual(sum(x['disposition'] == 'duplicate' for x in result['sources']), 2)
        self.assertGreaterEqual(result['counts']['duplicate_paths'], 2)
        for source in result['sources']:
            if source['disposition'] == 'duplicate':
                self.assertIn('duplicate_of', source)

    def test_no_huge_hash_or_source_body_read_for_sqlite_parquet_pdf(self):
        self.put('recipes/book.pdf', '%PDF')
        self.put('overture/places.parquet', 'PAR1')
        db = self.root / 'usda-2026-04' / 'source.sqlite'
        db.parent.mkdir()
        with sqlite3.connect(db) as conn:
            conn.execute('CREATE TABLE foods(id)')
        with patch('ingest_catalog._read_prefix', side_effect=AssertionError('should not read')):
            got = self.byname(self.discover(hash_max_bytes=0))
        self.assertTrue(got['source.sqlite']['existing_store'])
        self.assertEqual(got['source.sqlite']['disposition'], 'existing-store')
        self.assertIn('barcodes', got['source.sqlite']['domains'])
        self.assertNotIn('sha256', got['source.sqlite'])

    def test_symlink_leaf_parent_and_secret_exclusion(self):
        outside = Path(self.tmp.name) / 'outside'
        outside.mkdir()
        (outside / 'secret.jsonl').write_text('sensitive')
        (self.root / 'link').symlink_to(outside, target_is_directory=True)
        self.put('.env', 'API_KEY=neverread')
        self.put('.ssh/id_rsa', 'neverread')
        result = self.discover()
        got = self.byname(result)
        self.assertEqual(got['link']['reason'], 'symlink_not_followed')
        self.assertNotIn('secret.jsonl', got)
        self.assertNotIn('id_rsa', got)
        self.assertEqual(got['.env']['reason'], 'credential_or_code_cache_path')
        result = discover_sources({'roots': [str(self.root / 'link' / 'subdir')], 'project_reports': []})
        self.assertFalse(any(x['disposition'] == 'candidate' for x in result['sources']))

    def test_private_partial_and_known_restricted_not_candidates(self):
        self.put('household/profiles.json', '{"name":"private"}')
        self.put('osm/planet.osm.pbf.part', 'partial')
        self.put('parsed-source-faithful-20261020/recipes.jsonl', '{"id":"private-research"}\n')
        self.put('recipes/manifest.json', '{"license":"noncommercial research only"}')
        self.put('recipes/held.jsonl', '{"recipeIngredient":["egg"]}\n')
        got = self.byname(self.discover())
        self.assertTrue(got['profiles.json']['restricted'])
        self.assertEqual(got['planet.osm.pbf.part']['disposition'], 'incomplete-hold')
        self.assertTrue(got['recipes.jsonl']['restricted'])
        self.assertTrue(got['held.jsonl']['restricted'])

    def test_code_docs_vs_datasets_and_metadata(self):
        self.put('recipes/parse.py', 'raise RuntimeError("never execute")')
        self.put('recipes/README.md', 'description, not food')
        self.put('recipes/manifest.json', '{"sourceId":"unitools"}')
        self.put('mystery.json', '{"unrelated":"value"}')
        got = self.byname(self.discover())
        self.assertEqual(got['parse.py']['disposition'], 'documentation')
        self.assertEqual(got['README.md']['disposition'], 'documentation')
        self.assertEqual(got['manifest.json']['domains'], ['citations'])
        self.assertEqual(got['mystery.json']['disposition'], 'unclassified')

    def test_more_than_one_thousand_files_and_resumable_cursor(self):
        for index in range(1105):
            self.put(f'recipes/{index}.jsonl', json.dumps({'id': index, 'recipeIngredient': ['egg']}) + '\n')
        result = self.discover(max_files=150, hash_max_bytes=0)
        pages, seen = 1, {s['id'] for s in result['sources']}
        self.assertTrue(result['truncated'])
        while result['truncated']:
            result = self.discover(max_files=150, hash_max_bytes=0, resume_cursor=result['resume_cursor'])
            for source in result['sources']:
                self.assertNotIn(source['id'], seen)
                seen.add(source['id'])
            pages += 1
            self.assertLess(pages, 20)
        self.assertEqual(len(seen), 1105)
        self.assertGreater(pages, 1)

    def test_independent_errors_do_not_stop_other_files(self):
        self.put('broken/manifest.json', '{')
        self.put('recipes/okay.jsonl', '{"recipeIngredient":["egg"]}\n')
        self.put('manifest.json', json.dumps({'files': [{'path': str(self.root / 'missing.jsonl')}]}))
        result = self.discover()
        self.assertIn('okay.jsonl', self.byname(result))
        self.assertGreaterEqual(result['counts']['errors'], 2)
        self.assertIn('JSONDecodeError', {e['code'] for e in result['errors']})
        self.assertIn('not_found', {e['code'] for e in result['errors']})

    def test_state_directory_never_reingested(self):
        self.put('recipes/source.jsonl', '{"recipeIngredient":["egg"]}\n')
        state = self.root / 'local-run'
        self.put('local-run/recipes.sqlite', 'SQLite data')
        self.put('local-run/catalog.private.json', '{"sourceId":"world-recipes"}')
        got = self.byname(self.discover(state_dir=str(state)))
        self.assertNotIn('recipes.sqlite', got)
        self.assertNotIn('catalog.private.json', got)
        self.assertEqual(got['local-run']['reason'], 'own_state_directory')

    def test_depth_limit_is_resumable_with_larger_bound(self):
        self.put('deep/recipes/a.jsonl', '{"recipeIngredient":["egg"]}\n')
        result = self.discover(max_depth=1)
        self.assertTrue(result['truncated'])
        self.assertEqual(result['stop_reason'], 'max_depth')
        result = self.discover(max_depth=5, resume_cursor=result['resume_cursor'])
        self.assertFalse(result['truncated'])
        self.assertIn('a.jsonl', self.byname(result))

    def test_inventory_tsv_paths_and_inherited_metadata(self):
        other = Path(self.tmp.name) / 'additional-retained'
        other.mkdir()
        (other / 'recipe.jsonl').write_text('{"recipeIngredient":["egg"]}\n')
        report = Path(self.tmp.name) / 'asset-inventory.tsv'
        report.write_text('path\tsource_id\tlicense\n' + str(other / 'recipe.jsonl') + '\tunitools\tCC BY-SA 4.0\n')
        result = self.discover(project_reports=[str(report)], allowed_report_roots=[str(other)])
        source = self.byname(result)['recipe.jsonl']
        self.assertEqual(source['provider'], 'unitools')
        self.assertEqual(source['license'], 'CC BY-SA 4.0')

    def test_sqlite_sidecars_and_no_unfounded_loaded_claim(self):
        self.put('random/source.sqlite', 'SQLite')
        self.put('random/source.sqlite-wal', 'wal')
        source = self.byname(self.discover())['source.sqlite']
        self.assertFalse(source['loaded'])
        self.assertNotIn('barcodes', source['domains'])
        self.assertEqual(source['sidecars']['-wal']['bytes'], 3)
        self.assertIsNone(source['sidecars']['-shm'])
        self.assertEqual(source['identity']['sidecars'], source['sidecars'])

    def test_large_file_digest_is_not_requested(self):
        source = self.root / 'recipes.jsonl'
        with source.open('wb') as stream:
            stream.write(b'{"recipeIngredient":["egg"]}\n')
            stream.seek(2 * 1024 * 1024)
            stream.write(b'\n')
        got = self.byname(self.discover(hash_max_bytes=1024))['recipes.jsonl']
        self.assertNotIn('sha256', got)
        self.assertEqual(got['disposition'], 'candidate')

    def test_known_rights_hold_propagates_to_cheap_copy_alias(self):
        self.put('recipes.jsonl', '{"recipeIngredient":["egg"]}\n')
        self.put('AdamBouhmad--open-recipe-archive/collections/work/recipes.jsonl', '{"recipeIngredient":["egg"]}\n')
        result = self.discover()
        payloads = [s for s in result['sources'] if s['format'] == 'jsonl']
        self.assertEqual(len(payloads), 2)
        self.assertTrue(all(s['restricted'] for s in payloads))
        self.assertTrue(result['restriction_updates'])

    def test_hold_on_later_page_reports_previous_alias_update(self):
        alias = self.put('recipes.jsonl', '{"recipeIngredient":["egg"]}\n')
        self.put('AdamBouhmad--open-recipe-archive/recipes.jsonl', alias.read_text())
        roots = [str(alias), str(self.root / 'AdamBouhmad--open-recipe-archive')]
        first = discover_sources({'roots': roots, 'project_reports': [], 'max_files': 1})
        alias_id = self.byname(first)['recipes.jsonl']['id']
        second = discover_sources({'roots': roots, 'project_reports': [], 'resume_cursor': first['resume_cursor']})
        self.assertIn(alias_id, {x['id'] for x in second['restriction_updates']})

    def test_hardlink_private_scope_cannot_be_aliased(self):
        alias = self.put('recipes.jsonl', '{"recipeIngredient":["private"]}\n')
        private = self.root / 'household' / 'records.jsonl'
        private.parent.mkdir()
        os.link(alias, private)
        result = self.discover()
        self.assertTrue(self.byname(result)['recipes.jsonl']['restricted'])

    def test_broad_roots_refused(self):
        result = discover_sources({'roots': ['/home/user'], 'project_reports': []})
        self.assertEqual(result['roots'][0]['status'], 'refused')
        self.assertFalse(result['sources'])


if __name__ == '__main__':
    unittest.main()
