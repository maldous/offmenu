import hashlib
import unittest

from offmenu.refresh.product_label_sections import extract_label_sections, extract_ingredient_components
from offmenu.refresh.core import RefreshError


class ProductLabelSectionTests(unittest.TestCase):
    def test_marketing_punctuation_preserves_decimals_and_adjacent_sections(self):
        cases = [('No Artificial Colours.', 'Keep refrigerated.', 'storage'),
                 ('Source of 1.5 g fibre!', 'Unrelated trailing sentence.', 'unclassified'),
                 ('Suitable for 豆 lovers?', 'Keep frozen.', 'storage')]
        for claim, following, category in cases:
            with self.subTest(claim=claim):
                text = claim + ' ' + following; result = extract_label_sections(text)
                spans = result['sections']
                self.assertEqual([s['text'] for s in spans if s['category'] == 'marketing'], [claim])
                self.assertTrue(any(s['category'] == category and following in s['text'] for s in spans))
                self.assertEqual(''.join(s['text'] for s in spans), text)
                for span in spans:
                    self.assertEqual(text[span['start']:span['end']], span['text'])
                    self.assertEqual(text.encode()[span['utf8Start']:span['utf8End']].decode(), span['text'])
        text = 'No Artificial Colours Source of 1.5 g fibre Suitable for 豆 lovers 12BATCHCODE9'
        spans = extract_label_sections(text)['sections']
        self.assertEqual([s['text'] for s in spans if s['category'] == 'marketing'],
            ['No Artificial Colours', 'Source of 1.5 g fibre', 'Suitable for 豆 lovers'])
        self.assertTrue(any('12BATCHCODE9' in s['text'] for s in spans if s['category'] == 'unclassified'))
        self.assertEqual(''.join(s['text'] for s in spans), text)

    def test_unpunctuated_explicit_sections_end_at_line_breaks(self):
        for newline in ('\n', '\r\n', '\r'):
            with self.subTest(newline=repr(newline)):
                lines = ['Ingredients: 豆 Oil, Water', 'CONTAINS MILK', 'Keep refrigerated',
                         'Contributes to daily intake', 'No Artificial Colours', 'Unexplained code 123']
                text = newline.join(lines); result = extract_label_sections(text)
                spans = result['sections']
                explicit = [(s['category'], s['text']) for s in spans if s['category'] != 'unclassified']
                self.assertEqual(explicit, [('ingredient_list', lines[0]), ('allergen_statement', lines[1]),
                    ('storage', lines[2]), ('marketing', lines[3]), ('marketing', lines[4])])
                self.assertEqual(''.join(s['text'] for s in spans), text)
                for span in spans:
                    self.assertEqual(text[span['start']:span['end']], span['text'])
                    self.assertEqual(text.encode()[span['utf8Start']:span['utf8End']].decode(), span['text'])

    def test_sections_keep_every_character_and_unicode_byte_offsets(self):
        text = '豆 Oil, Water, Flavour. CONTAINS SESAME. Keep refrigerated. Store below 4.5 °C. Made in France from at least 70% French ingredients No Artificial Colours 12BATCHCODE9'
        result = extract_label_sections(text); spans = result['sections']
        self.assertEqual(''.join(s['text'] for s in spans), text)
        self.assertEqual(result['rawTextSHA256'], hashlib.sha256(text.encode()).hexdigest())
        for span in spans:
            self.assertEqual(text[span['start']:span['end']], span['text'])
            self.assertEqual(text.encode()[span['utf8Start']:span['utf8End']].decode(), span['text'])
        by_category = {}
        for span in spans: by_category.setdefault(span['category'], []).append(span['text'])
        self.assertEqual(by_category['ingredient_list'], ['豆 Oil, Water, Flavour.'])
        self.assertEqual(by_category['allergen_statement'], ['CONTAINS SESAME.'])
        self.assertEqual(by_category['storage'], ['Keep refrigerated.', 'Store below 4.5 °C.'])
        self.assertEqual(by_category['origin_claim'], ['Made in France from at least 70% French ingredients'])
        self.assertTrue(any('12BATCHCODE9' in s for s in by_category['unclassified']))
        self.assertIsNone(result['canonicalMapping'])

    def test_no_marker_does_not_invent_ingredient_or_origin_section(self):
        result = extract_label_sections('An unclear label, with unexplained text')
        self.assertEqual([s['category'] for s in result['sections']], ['unclassified'])
        self.assertIsNone(result['certification'])

    def test_limits_are_errors_not_silent_truncation(self):
        with self.assertRaisesRegex(RefreshError, 'input-bound'): extract_label_sections('豆', max_text_bytes=1)
        with self.assertRaisesRegex(RefreshError, 'count-bound'):
            extract_label_sections('Oil, Water. CONTAINS SOY. Keep frozen.', max_sections=1)

    def test_nested_components_percentages_codes_and_source_offsets(self):
        text = '豆 Oil (Palm, Seed), Sunflower Oil (27%), Emulsifier [322 (Bean), 471], Vitamins (A, D). CONTAINS BEAN.'
        end = text.index(' CONTAINS')
        result = extract_ingredient_components(text, start=0, end=end)
        nodes = result['components']; self.assertEqual(len(nodes), 4)
        self.assertEqual([c['text'] for c in nodes[0]['children']], ['Palm', 'Seed'])
        self.assertEqual([(q['valueLexeme'], q['unitLexeme'], q['interpretedValue']) for q in nodes[1]['quantities']], [('27', '%', None)])
        self.assertEqual(nodes[1]['children'], [])
        self.assertEqual([c['text'] for c in nodes[2]['children']], ['322 (Bean)', '471'])
        self.assertEqual(nodes[2]['children'][0]['children'][0]['text'], 'Bean')
        self.assertEqual(nodes[2]['children'][1]['quantities'], [])
        def check(node):
            self.assertEqual(text[node['start']:node['end']], node['text'])
            self.assertEqual(text.encode()[node['utf8Start']:node['utf8End']].decode(), node['text'])
            self.assertIsNone(node['canonicalConceptId'])
            for child in node['children']:
                self.assertEqual(child['parentComponentId'], node['componentId']); check(child)
        for node in nodes: check(node)
        self.assertNotIn('CONTAINS', result['ingredientSpan']['text'])

    def test_unclosed_group_uncertainty_and_node_bounds(self):
        text = 'Blend (Oil, Water'
        result = extract_ingredient_components(text, start=0, end=len(text))
        self.assertTrue(result['uncertainty'])
        self.assertEqual(result['components'][0]['text'], text)
        with self.assertRaisesRegex(RefreshError, 'node-bound'):
            extract_ingredient_components('A, B', start=0, end=4, max_nodes=1)


if __name__ == '__main__': unittest.main()
