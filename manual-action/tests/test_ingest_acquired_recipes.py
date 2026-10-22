"""Generated source-shaped fixtures only. No remote, retained, or actual recipe data."""
import gzip
import io
import json
from pathlib import Path
import sys
import tarfile
import tempfile
import threading
import time
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import ingest_acquired_recipes as adapter
from ingest_engine import IngestContext
from ingest_store import DomainStore


def foodista(title='Generated soup', url='https://www.foodista.com/recipe/SYNTHETIC/soup', **changes):
    value = {'id': 'synthetic', 'source': 'foodista', 'added': '2020-01-01T12:00:00',
             'created': '2010-01-01T00:00:00',
             'metadata': {'url': url, 'authors': ['Recipe author', 'Comment author'], 'license': 'CC-BY-3.0'},
             'text': title + '\nBy: Recipe author\nPublished: January 1, 2010\n\nIngredients\n1 cup beans\nsalt, to taste\n\nPreparation\n1\nStir.\n2\nServe.\n\nAbout\nSource note.\n\nComments:\nComment author\nNever a recipe step.\n'}
    return dict(value, **changes)


def fork(title='Generated ratio soup'):
    return '''export default {repoId: 'synthetic_repo', parentRepoId: 'synthetic_parent',
        title: %s, slug: 'synthetic', author: 'Generated Author', license: 'CC-BY-SA',
        ratioSystem: 'parts', activeTime: '5 min', totalTime: '10 min',
        ingredients: [{ingId:'one', name:'beans', ratioValue:1.00e+2, defaultUnit:'parts', role:'Base'},
                      {ingId:'two', name:'salt', ratioValue:1, defaultUnit:'parts'}],
        processNodes:[{nodeId:'step_1', action:'Mix', inputs:['one','two'], instructions:'Stir.',
                       visualCue: {primaryTarget:'Source cue.', spectrum:[]}},
                      {nodeId:'step_2', action:'Serve', instructions:'Serve.'}],
        };''' % json.dumps(title)


def medline(title='Generated berry dish', language='en', heading=True, groups=True):
    ih = '<h3>Ingredients</h3>' if language == 'en' else '<h3>Ingredientes</h3>'
    dh = 'Directions' if language == 'en' else 'Direcciones'
    ingredients = '<p><strong>For the base:</strong></p><ul><li>1 cup <em>berries</em></li></ul><p>For the top:</p><ul><li>2 spoonfuls oats</li></ul>' if groups else '<ul><li>1 cup berries</li><li>2 spoonfuls oats</li></ul>'
    return '<html><nav><ul><li>Not an ingredient</li></ul></nav><main><h1>' + title + '</h1><p>Servings: 2</p>' + (ih if heading else '') + ingredients + '<h3>' + dh + '</h3><ol><li>Stir <strong>slowly</strong>.</li><li>Serve.</li></ol><p>Notes:</p><ul><li>Not a step.</li></ul><p>Find more recipes at <a href="https://foodhero.org/">FoodHero.org</a></p><h2>Nutrition Information</h2><p>Unparsed source nutrition.</p></main><script>throw "never executed";</script></html>'


class AcquiredRecipesTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.config = {'reserve_bytes': 0, 'batch_size': 2, 'max_record_bytes': 16 * 1024 * 1024}

    def source(self, name, payload, family, **extra):
        path = self.root / name
        path.write_bytes(payload if isinstance(payload, bytes) else payload.encode())
        return {'id': name, 'path': str(path), 'format': 'archive' if family == 'forkrecipe' else 'jsonl' if family == 'foodista_common_pile' else 'html',
                'provider': family, 'acquired_adapter': family, 'domains': ['recipes', 'ingredients', 'citations'],
                'metadata': {'acquisition': {'verified': True, 'revision': 'synthetic-revision',
                    'attribution': 'Generated Attribution', 'license_evidence': ['https://example.invalid/license']}},
                'license': 'CC-BY-4.0-current-site-not-snapshot' if family == 'foodista_common_pile' else 'synthetic-license', **extra}

    def food_source(self, rows, name='foodista.jsonl.gz', **extra):
        raw = ''.join((json.dumps(r) if not isinstance(r, str) else r) + '\n' for r in rows)
        return self.source(name, gzip.compress(raw.encode()), 'foodista_common_pile', compression='gz', **extra)

    def archive_source(self, entries, **extra):
        buffer = io.BytesIO()
        with tarfile.open(fileobj=buffer, mode='w:gz') as archive:
            for name, value in entries:
                member = tarfile.TarInfo(name)
                if value is None:
                    member.type, member.linkname = tarfile.SYMTYPE, '../../outside'
                    archive.addfile(member)
                else:
                    raw = value if isinstance(value, bytes) else value.encode()
                    member.size = len(raw)
                    archive.addfile(member, io.BytesIO(raw))
        return self.source('forkrecipe.tar.gz', buffer.getvalue(), 'forkrecipe', **extra)

    def run_source(self, domain, sources):
        context = IngestContext(domain, self.root, self.config, threading.Event(), lambda *args: None, time.monotonic())
        with DomainStore(domain, self.root, self.config) as store:
            context.store = store
            result = adapter.run_domain(domain, sources, context)
            rows = [json.loads(r[0]) for r in store.db.execute('SELECT payload_json FROM records ORDER BY row_number')]
            relations = store.db.execute('SELECT record_id,kind,target_domain,target_id FROM relations').fetchall()
            errors = store.db.execute('SELECT error_class FROM source_errors').fetchall()
        return result, rows, relations, errors

    def test_foodista_mixed_documents_comments_rights_and_original(self):
        original = foodista()
        source = self.food_source([foodista(url='https://www.foodista.com/blog/synthetic'), original])
        result, rows, links, errors = self.run_source('recipes', [source])
        self.assertEqual(result['status'], 'complete')
        self.assertEqual(len(rows), 1)
        self.assertEqual(result['sources'][0]['record_kinds']['documents_examined'], 2)
        self.assertEqual(result['sources'][0]['record_kinds']['non_recipe_documents'], 1)
        self.assertEqual(rows[0]['raw_source']['source_payload'], original)
        self.assertEqual(rows[0]['ingredient_count'], 2)
        self.assertEqual([s['raw_text'] for s in rows[0]['steps']], ['1 Stir.', '2 Serve.'])
        self.assertEqual(rows[0]['provenance']['rights']['source_license'], 'CC-BY-3.0')
        self.assertEqual(rows[0]['provenance']['rights']['authors'], ['Recipe author', 'Comment author'])
        self.assertEqual(rows[0]['raw_source']['recipe']['published_author_text'], 'Recipe author')
        self.assertFalse(rows[0]['gold_review_performed'])
        self.assertFalse(rows[0]['automaticPlanningEligible'])
        self.assertEqual(errors, [])

    def test_cross_domain_exact_ids_and_metadata_only_citations(self):
        source = self.food_source([foodista()])
        _, recipes, recipe_links, _ = self.run_source('recipes', [source])
        _, mentions, mention_links, _ = self.run_source('ingredients', [source])
        _, citations, citation_links, _ = self.run_source('citations', [source])
        self.assertEqual([r['id'] for r in mentions], [r['id'] for r in recipes[0]['ingredients']])
        self.assertIn((recipes[0]['id'], 'cites', 'citations', citations[0]['id']), recipe_links)
        self.assertIn((citations[0]['id'], 'cites_record', 'recipes', recipes[0]['id']), citation_links)
        self.assertTrue(all(r['recipe_id'] == recipes[0]['id'] for r in mentions))
        self.assertNotIn('Never a recipe step', json.dumps(citations))
        self.assertEqual(citations[0]['reference']['license'], 'CC-BY-3.0')

    def test_foodista_broken_line_and_sections_are_isolated_and_durable(self):
        bad = foodista(text='Title\nIngredients\nbeans\nPreparation\n1\nComments:\nNever a step')
        source = self.food_source(['{broken}', bad, foodista()])
        result, rows, _, errors = self.run_source('recipes', [source])
        self.assertEqual(len(rows), 1)
        self.assertEqual(result['errors'], 2)
        self.assertEqual(result['status'], 'partial')
        self.assertEqual(len(errors), 2)
        repeat, again, _, _ = self.run_source('recipes', [source])
        self.assertEqual(repeat['written'], 0)
        self.assertEqual(repeat['errors'], 2)
        self.assertEqual(len(again), 1)

    def test_foodista_dates_not_repaired_or_falsely_reviewed(self):
        source = self.food_source([foodista(created=None, added='bad-date')])
        _, rows, _, _ = self.run_source('recipes', [source])
        self.assertIn('unparseable_or_missing_created_date', rows[0]['review_flags'])
        self.assertIsNone(rows[0]['raw_source']['source_payload']['created'])
        self.assertEqual(rows[0]['qualification_status'], 'unreviewed')

    def test_foodista_oversized_line_drained_then_next_record(self):
        source = self.food_source(['x' * 1500, foodista()])
        with patch.object(adapter, 'MAX_RECORD', 1000):
            result, rows, _, _ = self.run_source('recipes', [source])
        self.assertEqual(len(rows), 1)
        self.assertEqual(result['errors'], 1)

    def test_gzip_expansion_budget_does_not_stop_next_source(self):
        bad = self.food_source([foodista()], max_expanded_bytes=20)
        good = self.food_source([foodista('Later', url='https://www.foodista.com/recipe/LATER/later')], name='later.jsonl.gz')
        result, rows, _, _ = self.run_source('recipes', [bad, good])
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]['title'], 'Later')
        self.assertEqual(result['status'], 'partial')

    def test_checkpoint_resume_exact_and_duplicate_identity(self):
        source = self.food_source([foodista(str(n)) for n in range(7)])
        self.config['max_rows_per_source'] = 2
        first, rows, _, _ = self.run_source('recipes', [source])
        self.assertEqual(len(rows), 2)
        self.assertEqual(first['status'], 'partial')
        self.config['max_rows_per_source'] = 0
        last, rows, _, _ = self.run_source('recipes', [source])
        self.assertEqual(len(rows), 7)
        self.assertEqual(last['written'], 5)
        self.assertEqual(last['status'], 'complete')
        repeat, _, _, _ = self.run_source('recipes', [source])
        self.assertEqual(repeat['written'], 0)

    def test_fork_ratio_process_nodes_credits_and_no_evaluation(self):
        source = self.archive_source([('root/recipes/good.js', fork()), ('root/NOTICE', 'Generated notice'),
            ('root/LICENSE', 'Generated license'), ('root/data/users.js', 'import forbidden from "never-run";')])
        result, rows, _, _ = self.run_source('recipes', [source])
        self.assertEqual(result['status'], 'complete')
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]['step_count'], 2)
        self.assertEqual(rows[0]['steps'][0]['source_section'], 'Mix')
        self.assertEqual(rows[0]['ingredients'][0]['source_ratio_value'], 100)
        self.assertEqual(rows[0]['ingredients'][0]['source_default_unit'], 'parts')
        self.assertIsNone(rows[0]['ingredients'][0]['quantity'])
        self.assertIsNone(rows[0]['yield'])
        self.assertIn('1.00e+2', rows[0]['raw_source']['source_javascript'])
        notices = rows[0]['provenance']['container_metadata']['archive_notices']
        self.assertEqual(notices['NOTICE']['source_text'], 'Generated notice')
        self.assertIn('import forbidden', notices['data/users.js']['source_text'])
        _, citations, _, _ = self.run_source('citations', [source])
        self.assertNotIn('import forbidden', json.dumps(citations))
        self.assertIn('data/users.js', citations[0]['parent_reference']['archive_notice_sha256'])

    def test_fork_bad_member_template_unsafe_paths_and_symlinks_isolated(self):
        source = self.archive_source([('root/recipes/_template.js', fork()),
            ('root/recipes/bad.js', 'export default { title: stealSecrets() };'),
            ('../escaped.js', fork()), ('/absolute.js', fork()),
            ('root/recipes/link.js', None), ('root/recipes/good.js', fork())])
        result, rows, _, _ = self.run_source('recipes', [source])
        self.assertEqual(len(rows), 1)
        self.assertEqual(result['errors'], 4)
        self.assertEqual(result['sources'][0]['record_kinds']['template_members'], 1)
        self.assertFalse((self.root / 'escaped.js').exists())
        self.assertEqual(result['status'], 'partial')

    def test_fork_bad_notice_does_not_discard_recipe(self):
        source = self.archive_source([('root/LICENSE', b'\xff'), ('root/recipes/good.js', fork())])
        result, rows, _, _ = self.run_source('recipes', [source])
        self.assertEqual(len(rows), 1)
        self.assertEqual(result['status'], 'partial')
        self.assertEqual(result['errors'], 1)

    def test_fork_duplicate_member_names_quarantined(self):
        source = self.archive_source([('root/recipes/good.js', fork()), ('root/recipes/good.js', fork('Different'))])
        result, rows, _, _ = self.run_source('recipes', [source])
        self.assertEqual(len(rows), 1)
        self.assertEqual(result['errors'], 1)

    def test_html_inline_spaces_not_silently_joined(self):
        source = self.source('inline.html', medline().replace('1 cup <em>berries</em>', '1 <span>cup </span>berries'),
            'medlineplus_healthy_recipes', source_url='https://medlineplus.gov/recipes/generated/')
        _, rows, _, _ = self.run_source('recipes', [source])
        self.assertEqual(rows[0]['ingredients'][0]['raw_text'], '1 cup berries')

    def test_medline_grouped_ingredients_directions_and_notes(self):
        source = self.source('medline.html', medline(), 'medlineplus_healthy_recipes',
            source_url='https://medlineplus.gov/recipes/generated/', language='en')
        result, rows, _, _ = self.run_source('recipes', [source])
        self.assertEqual(result['status'], 'complete')
        self.assertEqual(rows[0]['ingredient_count'], 2)
        self.assertEqual(rows[0]['source_ingredient_groups'], ['For the base:', 'For the top:'])
        self.assertEqual([i['source_section'] for i in rows[0]['ingredients']], ['For the base:', 'For the top:'])
        self.assertEqual([s['raw_text'] for s in rows[0]['steps']], ['Stir slowly.', 'Serve.'])
        self.assertIsNone(rows[0]['nutrition'])
        self.assertIn('Unparsed source nutrition', rows[0]['raw_source']['source_payload']['source_document_html'])
        self.assertEqual(rows[0]['raw_source']['recipe']['source_time_yield_assertions'], ['Servings: 2'])

    def test_medline_known_headingless_toast_exception_not_generic_guessing(self):
        html = medline(language='es', heading=False, groups=False)
        source = self.source('toast.html', html, 'medlineplus_healthy_recipes',
            source_url='https://medlineplus.gov' + adapter.TOAST_PATH, language='es')
        result, rows, _, _ = self.run_source('recipes', [source])
        self.assertEqual(result['status'], 'complete')
        self.assertEqual(rows[0]['language'], 'es')
        self.assertEqual(rows[0]['ingredient_count'], 2)
        bad = self.source('unknown.html', html, 'medlineplus_healthy_recipes',
            source_url='https://medlineplus.gov/spanish/recetas/unknown/', language='es')
        failure, _, _, _ = self.run_source('recipes', [bad])
        self.assertEqual(failure['errors'], 1)

    def test_medline_variant_quantities_preserved_without_equivalence(self):
        en = self.source('en.html', medline('Generated waffle').replace('1 cup', '2 cups'),
            'medlineplus_healthy_recipes', language='en', source_url='https://medlineplus.gov/recipes/waffles/',
            work_id='synthetic-work', counterpart_url='https://medlineplus.gov/spanish/recetas/waffles/')
        es = self.source('es.html', medline('Waffle generado', language='es'),
            'medlineplus_healthy_recipes', language='es', source_url='https://medlineplus.gov/spanish/recetas/waffles/',
            work_id='synthetic-work', counterpart_url='https://medlineplus.gov/recipes/waffles/')
        _, rows, _, _ = self.run_source('recipes', [en, es])
        self.assertEqual(len(rows), 2)
        self.assertNotEqual(rows[0]['id'], rows[1]['id'])
        self.assertNotEqual(rows[0]['ingredients'][0]['raw_text'], rows[1]['ingredients'][0]['raw_text'])
        for row in rows:
            self.assertFalse(row['raw_source']['recipe']['counterpart_equivalence_established'])
            self.assertIn('publisher_variant_quantity_mismatch_requires_review', row['review_flags'])
            self.assertFalse(row['translation_performed'])

    def test_medline_ambiguous_headingless_multiple_lists_rejected(self):
        html = medline(language='es', heading=False, groups=True)
        source = self.source('ambiguous.html', html, 'medlineplus_healthy_recipes',
            source_url='https://medlineplus.gov' + adapter.TOAST_PATH)
        result, rows, _, _ = self.run_source('recipes', [source])
        self.assertEqual(rows, [])
        self.assertEqual(result['status'], 'partial')

    def test_restricted_missing_source_is_never_read(self):
        source = {'id': 'held', 'path': str(self.root / 'missing'), 'restricted': True,
                  'acquired_adapter': 'foodista_common_pile'}
        result, rows, _, _ = self.run_source('recipes', [source])
        self.assertEqual(result['skipped'], 1)
        self.assertEqual(result['errors'], 0)
        self.assertEqual(rows, [])

    def test_unverified_receipt_never_parses(self):
        source = self.food_source([foodista()])
        source['metadata']['acquisition']['verified'] = False
        result, rows, _, _ = self.run_source('recipes', [source])
        self.assertEqual(rows, [])
        self.assertEqual(result['errors'], 1)

    def test_symlink_read_refused_and_next_source_survives(self):
        target = self.food_source([foodista()], name='target.gz')
        link = self.root / 'link.gz'
        link.symlink_to(target['path'])
        source = dict(target, id='symlink', path=str(link))
        result, rows, _, _ = self.run_source('recipes', [source, target])
        self.assertEqual(len(rows), 1)
        self.assertEqual(result['status'], 'partial')

    def test_duplicate_identical_files_keep_entity_ids_and_custody(self):
        one = self.food_source([foodista()], name='a.gz')
        two = self.food_source([foodista()], name='b.gz')
        _, rows, _, _ = self.run_source('recipes', [one, two])
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0]['id'], rows[1]['id'])
        self.assertNotEqual(rows[0]['provenance']['catalog_source_id'], rows[1]['provenance']['catalog_source_id'])

    def test_foodista_structural_caps_isolate_whole_record(self):
        excessive = foodista(text='Large\nIngredients\n' + 'x\n' * 3 + 'Preparation\nStir.\n')
        excessive_steps = foodista(text='Large\nIngredients\nx\nPreparation\n' + 'Stir.\n' * 3)
        source = self.food_source([excessive, excessive_steps, foodista()])
        with patch.object(adapter, 'MAX_INGREDIENTS', 2), patch.object(adapter, 'MAX_STEPS', 2):
            result, rows, _, errors = self.run_source('recipes', [source])
        self.assertEqual([r['title'] for r in rows], ['Generated soup'])
        self.assertEqual(result['errors'], 2)
        self.assertEqual(len(errors), 2)
        self.assertEqual(result['sources'][0]['diagnostics']['reason_counts'], {
            'acquired_recipe_ingredient_count_cap': 1, 'acquired_recipe_step_count_cap': 1})

    def test_fork_process_and_total_step_caps_not_silent_truncation(self):
        source = self.archive_source([('root/recipes/bad.js', fork()),
            ('root/recipes/good.js', fork('Later').replace(
                "{nodeId:'step_2', action:'Serve', instructions:'Serve.'}", ''))])
        with patch.object(adapter, 'MAX_PROCESS_NODES', 1):
            result, rows, _, _ = self.run_source('recipes', [source])
        self.assertEqual([r['title'] for r in rows], ['Later'])
        self.assertEqual(result['errors'], 1)
        source = self.archive_source([('root/recipes/bad.js', fork().replace(
            "instructions:'Stir.'", "instructions:['Stir.', 'Pause.']")),
            ('root/recipes/good.js', fork('Latest'))])
        with patch.object(adapter, 'MAX_STEPS', 2):
            result, rows, _, _ = self.run_source('recipes', [source])
        self.assertEqual({r['title'] for r in rows}, {'Later', 'Latest'})
        self.assertEqual(result['written'], 1)
        self.assertEqual(result['errors'], 1)

    def test_medline_ingredient_and_step_caps(self):
        source = {'source_url': 'https://medlineplus.gov/recipes/generated/'}
        with patch.object(adapter, 'MAX_INGREDIENTS', 1):
            with self.assertRaisesRegex(adapter.MalformedAcquiredRecipe, 'ingredient_count_cap'):
                adapter._medline_html(medline(), source)
        with patch.object(adapter, 'MAX_STEPS', 1):
            with self.assertRaisesRegex(adapter.MalformedAcquiredRecipe, 'step_count_cap'):
                adapter._medline_html(medline(), source)

    def test_aggregate_bound_precedes_identity_expansion_and_matches_domains(self):
        large = foodista(text='Large\nIngredients\n' + 'x' * 20000 + '\nPreparation\nStir.\n')
        source = self.food_source([large, foodista()])
        for domain in ('recipes', 'ingredients', 'citations'):
            with patch.object(adapter, 'MAX_PROJECTION_BYTES', 16384):
                result, rows, _, _ = self.run_source(domain, [source])
            self.assertEqual(result['errors'], 1)
            self.assertEqual(len(rows), 2 if domain == 'ingredients' else 1)
            self.assertEqual(result['sources'][0]['diagnostics']['reason_counts'], {
                'acquired_recipe_projection_size_cap': 1})
        with patch.object(adapter, 'MAX_PROJECTION_BYTES', 1024), \
                patch.object(adapter.retained, '_recipe', side_effect=AssertionError('must not expand')):
            with self.assertRaisesRegex(adapter.MalformedAcquiredRecipe, 'projection_size_cap'):
                adapter._project(adapter._foodista_sections(large), large, '/line/1',
                                 json.dumps(large), {}, source)

    def test_notice_and_rights_context_not_repeated_in_mentions(self):
        notice = 'Generated notice ' * 4000
        source = self.archive_source([('root/recipes/good.js', fork()), ('root/NOTICE', notice)])
        _, rows, _, _ = self.run_source('recipes', [source])
        recipe = rows[0]
        self.assertEqual(recipe['provenance']['container_metadata']['archive_notices']['NOTICE']['source_text'], notice)
        for mention in recipe['ingredients']:
            self.assertNotIn('container_metadata', mention['provenance'])
            self.assertNotIn('rights', mention['provenance'])
            self.assertEqual(mention['provenance']['recipe_id'], recipe['id'])
            self.assertEqual(mention['provenance']['recipe_provenance_sha256'],
                             adapter.retained._hash(recipe['provenance']))
            self.assertEqual(mention['raw_source']['name'], mention['source_name_text'])
        self.assertEqual(json.dumps(recipe).count(notice), 1)

    def test_reason_histogram_never_contains_exception_text(self):
        stats = adapter._stats()
        adapter._note_reason(stats, ValueError('private-source-text-and-path'))
        adapter._note_reason(stats, adapter.MalformedAcquiredRecipe('medline_title_ambiguous'))
        self.assertEqual(stats['reason_counts'], {'acquired_recipe_source_error': 1,
                                                'medline_title_ambiguous': 1})
        self.assertNotIn('private-source-text', json.dumps(stats))


if __name__ == '__main__':
    unittest.main()
