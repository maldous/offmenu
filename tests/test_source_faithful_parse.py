import hashlib
import importlib.util
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


if __name__ == '__main__':
    unittest.main()
