import hashlib
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).parents[1]
SPEC = importlib.util.spec_from_file_location(
    'source_faithful_parse', ROOT / 'offmenu/refresh/source_faithful_parse.py')
PARSER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(PARSER)

RECIPE_HTML = b'''<!doctype html><html><head><title>Test recipe</title></head><body>
<h1>Test coleslaw</h1><div class="field--name-body">
<h2>Ingredients</h2><ul><li>3 cups cabbage, shredded</li><li>1 small green capsicum, seeded and sliced</li></ul>
<h3>Dressing</h3><ul><li>2 tablespoons olive oil</li></ul>
<h2>Method</h2><p>Grate the citrus and combine with cabbage. Serves 4.</p>
<h3>Variation</h3><p>Use pink grapefruit instead of orange.</p>
<table><tr><td></td><td>Quantity per serving</td><td>Quantity per 100g</td></tr>
<tr><td>Serve size: 147g</td></tr><tr><td>Energy</td><td>495.63kj</td><td>336.82kj</td></tr></table>
</div></body></html>'''
MENU_HTML = '''<!doctype html><html><body><div class="menuCategory"><h2>Tapas</h2>
<div class="menuItemBox" id="item-1"><span class="menuItemName">HOUMOUS CITRON &amp; PIMENT DOUX</span>
<span class="menuItemDesc">Pois chiches et citron</span><span>12€</span></div>
</div></body></html>'''.encode('utf-8')


def source(raw, **extra):
    return {'sourceURL': 'https://example.invalid/source',
            'citationUrl': 'https://example.invalid/source',
            'release': 'synthetic-test-fixture',
            'originalSHA256': hashlib.sha256(raw).hexdigest(),
            'attribution': 'synthetic test fixture', **extra}


class SourceFaithfulParseTests(unittest.TestCase):
    def test_jsonld_only_fields_never_claim_unrelated_visible_text(self):
        raw = b'''<html><head><script type="application/ld+json">{"@type":"Recipe",
        "recipeIngredient":["1 cup flour"],"recipeInstructions":["Mix flour."],
        "recipeYield":"4 servings"}</script></head><body><h1>Fixture</h1></body></html>'''
        args = dict(source=source(raw), source_id='TEST', source_record_id='ld', country='ZZ', language='en')
        with self.assertRaisesRegex(PARSER.ParseError, 'source-field-not-locatable'):
            PARSER.parse_html_recipe(raw, **args)
        raw = raw.replace(b'</body>', b'<p>1 cup flour</p><p>Mix flour.</p><p>4 servings</p></body>')
        args['source'] = source(raw)
        record = PARSER.parse_html_recipe(raw, **args)
        text = PARSER.BeautifulSoup(raw, 'html.parser').get_text('\n', strip=False).encode()
        for field, quote in [(record['ingredientLines'][0], '1 cup flour'),
                             (record['orderedSteps'][0], 'Mix flour.'),
                             (record['yield'], '4 servings')]:
            location = field['location']
            start, end = location['utf8ByteRange']
            self.assertEqual(text[start:end].decode(), quote)
            self.assertEqual(hashlib.sha256(text[start:end]).hexdigest(), location['sourceSpanSHA256'])

    def test_recipe_preserves_sections_quantity_steps_yield_and_nutrition(self):
        record = PARSER.parse_html_recipe(RECIPE_HTML, source=source(RECIPE_HTML),
            source_id='TEST-RECIPE', source_record_id='fixture-1', country='ZZ', language='en')
        self.assertEqual(record['originalTitle'], 'Test coleslaw')
        self.assertEqual(len(record['ingredientLines']), 3)
        self.assertEqual([len(x['ingredients']) for x in record['components']], [2, 1])
        cabbage = record['ingredientLines'][0]
        self.assertEqual(cabbage['originalExpression'], '3 cups cabbage, shredded')
        self.assertEqual(cabbage['quantity']['rawValueLexeme'], '3')
        self.assertEqual(cabbage['quantity']['rawUnitLexeme'], 'cups')
        self.assertEqual(cabbage['sourceNameText'], 'cabbage, shredded')
        self.assertIsNone(cabbage['quantity']['interpretedValue'])
        self.assertEqual(record['yield']['rawText'], 'Serves 4')
        self.assertIn('Grate the citrus', record['orderedSteps'][0]['originalText'])
        energy = record['nutritionAssertions'][0]
        self.assertEqual((energy['sourceFieldName'], energy['rawValue'], energy['rawUnit']),
                         ('Energy', '495.63', 'kj'))
        self.assertIn('source serve size 147g', energy['sourceBasis'])
        self.assertIsNone(energy['interpretedValue'])
        self.assertEqual(record['sourceNotes'][0]['sourceSection'], 'Variation')

    def test_menu_adapter_preserves_original_item_price_and_no_identity_guess(self):
        records = PARSER.parse_html_menu(MENU_HTML,
            source=source(MENU_HTML, adapter='calmos-menu-v1', venue='Test Cafe'),
            source_id='TEST-MENU', country='ZZ', language='fr')
        self.assertEqual(len(records), 1)
        record = records[0]
        self.assertEqual(record['originalItemName'], 'HOUMOUS CITRON & PIMENT DOUX')
        self.assertEqual(record['sourceCategory'], 'Tapas')
        self.assertEqual(record['price']['rawValue'], '12')
        self.assertEqual(record['price']['rawCurrency'], '€')
        self.assertEqual(record['recipeCandidates'], [])

    def test_raw_quantity_capture_does_not_convert_ranges_or_culinary_units(self):
        quantity = PARSER._quantity('1–2 cups chopped onions')
        self.assertEqual(quantity['rawValueLexeme'], '1–2')
        self.assertEqual(quantity['rawUnitLexeme'], 'cups')
        self.assertIsNone(quantity['interpretedValue'])
        self.assertIsNone(quantity['interpretedUnit'])

    def test_atomic_output_is_repeat_safe_and_hash_pinned(self):
        with tempfile.TemporaryDirectory() as directory:
            input_path = Path(directory) / 'fixture.html'
            input_path.write_bytes(RECIPE_HTML)
            output = Path(directory) / 'parsed'
            arguments = dict(input_path=input_path, output_root=output,
                source=source(RECIPE_HTML), source_id='TEST-RECIPE', kind='recipe',
                country='ZZ', language='en', source_record_id='fixture-1')
            first = PARSER.run_html_asset(**arguments)
            second = PARSER.run_html_asset(**arguments)
            self.assertEqual(first['runKey'], second['runKey'])
            self.assertEqual(first['inputSHA256'], hashlib.sha256(RECIPE_HTML).hexdigest())
            self.assertEqual(first['artifacts'], second['artifacts'])
            self.assertEqual(first['acceptedRecords'], 1)


    def test_both_menu_adapters_locate_inline_names_without_zero_fallback(self):
        cards = [
            ('calmos-menu-v1', '<div class="menuItemBox"><span class="menuItemName">Fish <b>Cakes</b></span><span>12€</span></div>'),
            ('ocean82-menu-v1', '<li class="food-element"><span class="food-item-title">Fish <b>Cakes</b></span><span>12€</span></li>'),
        ]
        for adapter, card in cards:
            with self.subTest(adapter=adapter):
                raw = ('<html><body><h1>Unrelated prefix</h1>'+card+'</body></html>').encode()
                record = PARSER.parse_html_menu(raw, source=source(raw, adapter=adapter),
                    source_id='MENU', country='ZZ', language='en')[0]
                text = PARSER.BeautifulSoup(raw, 'html.parser').get_text('\n', strip=False).encode()
                start, end = record['location']['utf8ByteRange']
                self.assertGreater(start, 0)
                self.assertEqual(' '.join(text[start:end].decode().split()), 'Fish Cakes')
                self.assertEqual(hashlib.sha256(text[start:end]).hexdigest(), record['location']['sourceSpanSHA256'])

    def jsonld_recipe(self, instructions):
        ld = {'@type': 'Recipe', 'recipeIngredient': ['1 cup flour'],
              'recipeInstructions': instructions}
        return ('<html><head><script type="application/ld+json">'+json.dumps(ld)+
            '</script></head><body><h1>Fixture</h1><p>1 cup flour</p>'+
            '<h2>Base</h2><h3>Finish</h3><p>Mix flour.</p><p>Bake gently.</p><p>Serve warm.</p></body></html>').encode()

    def test_jsonld_sections_preserve_all_nested_steps_in_source_order(self):
        raw = self.jsonld_recipe([{'@type': 'HowToSection', 'name': 'Base', 'itemListElement': [
            {'@type': 'HowToStep', 'text': 'Mix flour.'},
            {'@type': 'HowToSection', 'name': 'Finish', 'itemListElement': [
                {'@type': 'HowToStep', 'text': 'Bake gently.'}]}]}, 'Serve warm.'])
        record = PARSER.parse_html_recipe(raw, source=source(raw), source_id='TEST',
            source_record_id='sections', country='ZZ', language='en')
        self.assertEqual([s['originalText'] for s in record['orderedSteps']],
            ['Mix flour.', 'Bake gently.', 'Serve warm.'])
        self.assertEqual([s['order'] for s in record['orderedSteps']], [1, 2, 3])
        self.assertTrue({'Base','Finish'} <= {n['originalText'] for n in record['sourceNotes']})
        text = PARSER.BeautifulSoup(raw,'html.parser').get_text('\n',strip=False).encode()
        for step in record['orderedSteps']:
            a,b = step['location']['utf8ByteRange']
            self.assertEqual(text[a:b].decode(),step['originalText'])
            self.assertEqual(hashlib.sha256(text[a:b]).hexdigest(),step['location']['sourceSpanSHA256'])

    def test_jsonld_section_without_heading_keeps_children_not_silent_drop(self):
        raw = self.jsonld_recipe([{'@type':'HowToSection','itemListElement':[
            {'@type':'HowToStep','text':'Mix flour.'}]}])
        record = PARSER.parse_html_recipe(raw, source=source(raw),source_id='TEST',
            source_record_id='nameless',country='ZZ',language='en')
        self.assertEqual([s['originalText'] for s in record['orderedSteps']],['Mix flour.'])

    def test_malformed_jsonld_section_is_rejected_instead_of_partial_success(self):
        raw = self.jsonld_recipe(['Mix flour.', {'@type':'HowToSection','name':'Base',
            'itemListElement':{'text':'Bake gently.'}}])
        with self.assertRaisesRegex(PARSER.ParseError,'instruction-section'):
            PARSER.parse_html_recipe(raw,source=source(raw),source_id='TEST',
                source_record_id='bad-section',country='ZZ',language='en')


    def test_jsonld_invisible_section_label_has_no_fabricated_visible_location(self):
        raw = self.jsonld_recipe([{'@type':'HowToSection','name':'Invisible label',
            'itemListElement':[{'@type':'HowToStep','text':'Mix flour.'}]}])
        record = PARSER.parse_html_recipe(raw,source=source(raw),source_id='TEST',
            source_record_id='section-label',country='ZZ',language='en')
        note = next(n for n in record['sourceNotes'] if n['originalText']=='Invisible label')
        self.assertIsNone(note['location'])
        self.assertEqual(note['sourceJSONPointer'],'/recipeInstructions/0/name')
        self.assertEqual([s['originalText'] for s in record['orderedSteps']],['Mix flour.'])

    def test_jsonld_excessive_section_depth_is_an_explicit_hold(self):
        section = {'@type':'HowToStep','text':'Mix flour.'}
        for _ in range(40):
            section = {'@type':'HowToSection','itemListElement':[section]}
        raw = self.jsonld_recipe([section])
        with self.assertRaisesRegex(PARSER.ParseError,'instruction-section-limit'):
            PARSER.parse_html_recipe(raw,source=source(raw),source_id='TEST',
                source_record_id='deep-section',country='ZZ',language='en')


if __name__ == '__main__':
    unittest.main()
