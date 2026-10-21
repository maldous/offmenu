"""Generated markup only; no retained source recipes are test fixtures."""
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
import sqlite3

from offmenu.refresh import source_faithful_parse as parser


MS = '''<html><h1>Island history</h1><div class="wpb_wrapper">
<p>Article introduction</p><p><strong><span>Recipe for Fixture stew<br>
Ingredients</span></strong><br>2 cups beans<br>1 spoon oil</p>
<p><strong><span>Method</span></strong><br>Mix. Simmer. Serve.</p></div></html>'''
MQ = '''<html><h1>Holiday article</h1><div class="ParagraphTitleText">
<h2>Les recettes de Noël</h2><div class="text-content">
<p><span class="orange"><strong>Fixture A : </strong></span></p>
<p><strong>Durée</strong> : 15 minutes - Niveau Facile</p>
<p><strong>Ingrédients</strong><br>1 tasse de riz</p><p>sel</p>
<p><strong>Déroulé </strong><br>Cuire le riz.</p><p>Servir.</p>
<p><em>Recette par Fixture Auteur</em></p><p> </p>
<p><span class="orange"><strong>Fixture B : </strong></span></p>
<p><strong>Durée</strong> : 30 minutes<br><br><strong>Ingrédients</strong><br>
<u>Garniture</u></p><p>2 légumes</p><p>Pâte</p>
<p><br><strong>Déroulé :</strong><br><u>Étape 1 : Mélange</u><br>Cuire le riz.</p>
<p>Mélanger.</p><p><u>Étape 2 : Finition</u><br>Servir.</p>
</div></div></html>'''
MR = '''<html><head><script type="application/ld+json">{"@type":"Recipe",
"recipeIngredient":["2 kg vegetables (, diced)"],"recipeInstructions":["Stir."],
"recipeYield":["4","4 people"]}</script></head><body><h1>Article headline</h1>
<p>Fixture pot</p><div class="wprm-recipe-container"><h2 class="wprm-recipe-name">Fixture pot</h2>
<span class="wprm-recipe-servings-with-unit"><span>4</span> <span>people</span></span>
<ul class="wprm-recipe-ingredients"><li class="wprm-recipe-ingredient"><span>2</span>
<span>kg</span> <span>vegetables</span><span>, diced</span></li>
<li class="wprm-recipe-ingredient"><span>Salt</span><span>(optional)</span></li></ul>
<ul class="wprm-recipe-instructions"><li class="wprm-recipe-instruction">
<div class="wprm-recipe-instruction-text">Stir <b>gently</b>.</div></li>
<li class="wprm-recipe-instruction"><div class="wprm-recipe-instruction-text">Serve.</div></li></ul>
</div></body></html>'''


def arguments(raw, adapter):
    return dict(source={'sourceURL': 'https://example.invalid/fixture', 'release': 'generated',
        'originalSHA256': hashlib.sha256(raw).hexdigest(), 'adapter': adapter},
        source_id='TEST', source_record_id='asset', country='ZZ', language='und')


class RetainedRecipeAdaptersTests(unittest.TestCase):
    def parse(self, markup, adapter):
        raw = markup.encode()
        records = parser.parse_html_recipes(raw, **arguments(raw, adapter))
        text = parser.BeautifulSoup(markup, 'html.parser').get_text('\n', strip=False).encode()
        for record in records:
            fields = [(record['originalTitle'], record['sourceLocation'])]
            fields += [(x['originalExpression'], x['location']) for x in record['ingredientLines']]
            fields += [(x['originalText'], x['location']) for x in record['orderedSteps']]
            fields += [(x['originalText'], x['location']) for x in record['sourceNotes']]
            if record['yield']:
                fields.append((record['yield']['rawText'], record['yield']['location']))
            for quote, location in fields:
                start, end = location['utf8ByteRange']
                self.assertEqual(text[start:end].decode(), quote)
                self.assertEqual(hashlib.sha256(text[start:end]).hexdigest(), location['sourceSpanSHA256'])
                self.assertEqual(hashlib.sha256(text).hexdigest(), location['pageTextSHA256'])
            self.assertIsNone(record['identity']['canonicalDishId'])
        return records

    def test_ms_paragraph_breaks_and_unsplit_procedure(self):
        record, = self.parse(MS, 'montserrat-paragraph-recipe-v1')
        self.assertEqual(record['originalTitle'], 'Recipe for Fixture stew')
        self.assertEqual([x['originalExpression'] for x in record['ingredientLines']], ['2 cups beans', '1 spoon oil'])
        self.assertEqual([x['originalText'] for x in record['orderedSteps']], ['Mix. Simmer. Serve.'])

    def test_mq_all_recipes_notes_labels_and_repeated_spans(self):
        records = self.parse(MQ, 'martinique-paragraph-recipes-v1')
        self.assertEqual(len(records), 2)
        self.assertEqual([r['originalTitle'] for r in records], ['Fixture A :', 'Fixture B :'])
        self.assertEqual([len(r['ingredientLines']) for r in records], [2, 2])
        self.assertEqual([len(r['orderedSteps']) for r in records], [2, 3])
        self.assertEqual([r['source']['sourceRecordId'] for r in records], ['asset', 'asset'])
        self.assertNotEqual(records[0]['ingredientLines'][0]['ingredientLineId'], records[1]['ingredientLines'][0]['ingredientLineId'])
        self.assertGreater(records[1]['orderedSteps'][0]['location']['utf8ByteRange'][0],
                           records[0]['orderedSteps'][0]['location']['utf8ByteRange'][1])
        notes = [x['originalText'] for x in records[1]['sourceNotes']]
        self.assertIn('Garniture', notes)
        self.assertIn('Étape 2 : Finition', notes)
        self.assertIn('Recette par Fixture Auteur', [x['originalText'] for x in records[0]['sourceNotes']])

    def test_mr_uses_visible_card_lexemes_not_jsonld_parentheses_or_list_repr(self):
        record, = self.parse(MR, 'wprm-visible-recipe-v1')
        self.assertEqual(record['originalTitle'], 'Fixture pot')
        self.assertNotIn('(,', record['ingredientLines'][0]['originalExpression'])
        self.assertEqual(len(record['orderedSteps']), 2)
        self.assertEqual(record['yield']['rawValueLexeme'], '4')
        self.assertEqual(' '.join(record['yield']['rawText'].split()), '4 people')
        raw = MR.encode()
        args = arguments(raw, 'wprm-visible-recipe-v1');args['source'].pop('adapter')
        with self.assertRaisesRegex(parser.ParseError, 'source-field-not-locatable'):
            parser.parse_html_recipe(raw, **args)

    def test_wprm_quantity_removed_from_name_with_raw_span_and_lexemes_intact(self):
        record, = self.parse(MR, 'wprm-visible-recipe-v1')
        ingredient = record['ingredientLines'][0]
        self.assertTrue(ingredient['sourceNameText'].startswith('vegetables'))
        self.assertEqual(ingredient['quantity']['rawValueLexeme'], '2')
        self.assertEqual(ingredient['quantity']['rawUnitLexeme'], 'kg')
        self.assertEqual(ingredient['quantity']['rawExpression'], '2 kg')
        self.assertTrue(ingredient['originalExpression'].startswith('2\n'))
        self.assertIsNone(ingredient['quantity']['interpretedValue'])
        self.assertIsNone(ingredient['quantity']['interpretedUnit'])
        for original in ('2\u00a0kg vegetables', '1 \n½\tcups vegetables', '1–2\nkg vegetables'):
            with self.subTest(original=original):
                quantity = parser._quantity(original)
                before = dict(quantity)
                self.assertEqual(parser._ingredient_name(original, quantity), 'vegetables')
                self.assertEqual(quantity, before)

    def test_plural_unhashable_or_nonstring_selector_has_fixed_parse_error(self):
        raw = MS.encode()
        for adapter in ({}, [], ['montserrat-paragraph-recipe-v1'], 7, False):
            with self.subTest(adapter=adapter), self.assertRaisesRegex(parser.ParseError, '^recipe-adapter-unselected$'):
                parser.parse_html_recipes(raw, **arguments(raw, adapter))

    def test_singular_api_refuses_multi_recipe_truncation(self):
        raw = MQ.encode()
        with self.assertRaisesRegex(parser.ParseError, 'multiple-recipes-use-plural-api'):
            parser.parse_html_recipe(raw, **arguments(raw, 'martinique-paragraph-recipes-v1'))

    def test_malformed_second_recipe_fails_entire_collection(self):
        raw = MQ.replace('<p>2 légumes</p><p>Pâte</p>', '').encode()
        with self.assertRaises(parser.ParseError):
            parser.parse_html_recipes(raw, **arguments(raw, 'martinique-paragraph-recipes-v1'))

    def test_selected_adapter_rejects_unrecognized_structure(self):
        for markup, adapter in [(MS.replace('Method', 'Unknown'), 'montserrat-paragraph-recipe-v1'),
            (MS.replace('<p><strong><span>Method', '<table><tr><td>Other block</td></tr></table><p><strong><span>Method'), 'montserrat-paragraph-recipe-v1'),
            (MQ.replace('<p>Mélanger.</p>', '<table><tr><td>Mélanger.</td></tr></table>'), 'martinique-paragraph-recipes-v1'),
            (MR.replace('wprm-recipe-instruction-text', 'unknown'), 'wprm-visible-recipe-v1'),
            (MR.replace('class="wprm-recipe-ingredient"', 'class="unknown"', 1), 'wprm-visible-recipe-v1'),
            (MR.replace('Serve.</div>', 'Serve.</div><span>Extra instruction</span>'), 'wprm-visible-recipe-v1'),
            (MR.replace('<h2 class="wprm-recipe-name">', '<div class="wprm-nutrition-label">nutrition</div><h2 class="wprm-recipe-name">'), 'wprm-visible-recipe-v1')]:
            with self.subTest(adapter=adapter), self.assertRaises(parser.ParseError):
                raw = markup.encode();parser.parse_html_recipes(raw, **arguments(raw, adapter))

    def test_unknown_adapter_fails_closed(self):
        raw = MS.encode()
        with self.assertRaisesRegex(parser.ParseError, 'recipe-adapter-unselected'):
            parser.parse_html_recipes(raw, **arguments(raw, 'unknown'))

    def test_singular_rejects_explicit_unknown_and_preserves_generic_selection(self):
        raw = b'<h1>Fixture</h1><div><h2>Ingredients</h2><ul><li>1 cup rice</li></ul><h2>Method</h2><p>Cook rice.</p></div>'
        for adapter in ('unknown', '', 17, {}, []):
            with self.subTest(adapter=adapter), self.assertRaisesRegex(parser.ParseError, 'recipe-adapter-unselected'):
                parser.parse_html_recipe(raw, **arguments(raw, adapter))
        args = arguments(raw, None)
        self.assertEqual(parser.parse_html_recipe(raw, **args)['originalTitle'], 'Fixture')
        args['source'].pop('adapter')
        self.assertEqual(parser.parse_html_recipe(raw, **args)['originalTitle'], 'Fixture')

    def test_atomic_plural_asset_emits_both_and_keeps_coverage_false(self):
        raw = MQ.encode()
        with tempfile.TemporaryDirectory() as directory:
            p = Path(directory) / 'generated.html';p.write_bytes(raw)
            args = arguments(raw, 'martinique-paragraph-recipes-v1')
            result = parser.run_html_asset(input_path=p, output_root=Path(directory) / 'out', kind='recipe', **args)
            self.assertEqual(result['acceptedRecords'], 2)
            self.assertEqual(result['identity']['adapter'], 'martinique-paragraph-recipes-v1')

    def test_plural_records_keep_asset_binding_and_project_as_distinct_ordinals(self):
        from offmenu.refresh import recipe_menu_store as store
        from offmenu.refresh.core import canonical
        raw = MQ.encode()
        asset = {'sourceId': 'TEST', 'sourceRecordId': 'asset', 'recordKind': 'recipe',
            'inputPath': '/generated-not-opened/fixture.html', 'inputBytes': len(raw),
            'inputSHA256': hashlib.sha256(raw).hexdigest(), 'release': 'generated',
            'sourceUseScope': 'generated fixture only'}
        manifest = store.prepare_recipe_menu([asset])
        def callback(selected, module):
            records = module.parse_html_recipes(raw, **arguments(raw, 'martinique-paragraph-recipes-v1'))
            return records, {'inputSHA256': asset['inputSHA256'], 'inputBytes': len(raw),
                'parserVersion': module.PARSER_VERSION, 'EOFFullyVerified': True,
                'bodyPasses': 1, 'records': len(records)}
        db = sqlite3.connect(':memory:')
        try:
            store.ingest_recipe_menu(db, [asset], selection_receipt_sha256='a' * 64,
                input_manifest_sha256=hashlib.sha256(canonical(manifest)).hexdigest(),
                parser_module=parser, parse_asset_once=callback, run_id='generated-plural',
                limits=store.StoreLimits(1048576, 15, 1000, 8388608, 500, 500, 16777216, 33554432, 30))
            self.assertEqual(db.execute('SELECT native_record_id,source_ordinal FROM recipe_source_record ORDER BY source_ordinal').fetchall(), [('asset', 1), ('asset', 2)])
            self.assertEqual(db.execute('SELECT count(*) FROM source_recipe_variant').fetchone()[0], 2)
            self.assertEqual(db.execute('SELECT count(*) FROM recipe_ingredient_line').fetchone()[0], 4)
            self.assertEqual(db.execute('SELECT count(*) FROM recipe_ordered_step').fetchone()[0], 5)
            self.assertEqual(db.execute('PRAGMA foreign_key_check').fetchall(), [])
        finally:
            db.close()


if __name__ == '__main__':
    unittest.main()
