import hashlib
import unittest

from offmenu.refresh.product_label_sections import extract_label_sections, extract_ingredient_components
from offmenu.refresh.core import RefreshError


class ProductLabelSectionTests(unittest.TestCase):
    def test_opening_ingredient_fallback_stops_before_unclassified_later_lines(self):
        for newline in ('\n', '\r\n', '\r'):
            for first, tail in (('Ingredients: Water, Salt', ['BATCH 1234', 'Use within 3 days']),
                                ('Water, Salt', ['BATCH 1234', 'CONTAINS MILK.'])):
                with self.subTest(newline=repr(newline), first=first):
                    text = newline.join([first] + tail); result = extract_label_sections(text); spans = result['sections']
                    self.assertEqual([s['text'] for s in spans if s['category'] == 'ingredient_list'], [first])
                    self.assertTrue(any('BATCH 1234' in s['text'] for s in spans if s['category'] == 'unclassified'))
                    self.assertEqual(''.join(s['text'] for s in spans), text)
                    self.assertEqual(result['rawTextSHA256'], hashlib.sha256(text.encode()).hexdigest())
                    cursor = 0
                    for span in spans:
                        self.assertEqual(span['start'], cursor); cursor = span['end']
                        self.assertEqual(text[span['start']:span['end']], span['text'])
                        self.assertEqual(text.encode()[span['utf8Start']:span['utf8End']].decode(), span['text'])
                        self.assertEqual(span['textSHA256'], hashlib.sha256(span['text'].encode()).hexdigest())

    def test_line_prefixes_cannot_absorb_preceding_ingredient_line(self):
        for newline in ('\n', '\r\n', '\r'):
            for statement, category in (('Our quality specifications guarantee freshness', 'marketing'),
                                        ('Brand is a registered trademark', 'company_address')):
                with self.subTest(newline=repr(newline), statement=statement):
                    lines = ['Ingredients: Water, Salt', statement, 'No Artificial Colours.', 'Keep refrigerated.']
                    text = newline.join(lines); result = extract_label_sections(text); spans = result['sections']
                    self.assertEqual([(s['category'], s['text']) for s in spans if s['category'] != 'unclassified'],
                        [('ingredient_list', lines[0]), (category, lines[1]), ('marketing', lines[2]), ('storage', lines[3])])
                    self.assertEqual(''.join(s['text'] for s in spans), text)
                    self.assertEqual(result['rawTextSHA256'], hashlib.sha256(text.encode()).hexdigest())
                    cursor = 0
                    for span in spans:
                        self.assertEqual(span['start'], cursor); cursor = span['end']
                        self.assertEqual(text[span['start']:span['end']], span['text'])
                        self.assertEqual(text.encode()[span['utf8Start']:span['utf8End']].decode(), span['text'])
                        self.assertEqual(span['textSHA256'], hashlib.sha256(span['text'].encode()).hexdigest())

    def test_address_text_prefix_cannot_cross_a_line_to_postcode(self):
        for newline in ('\n', '\r\n', '\r'):
            with self.subTest(newline=repr(newline)):
                text = 'ACME FOODS, 42 Road' + newline + '1234'
                spans = extract_label_sections(text)['sections']
                self.assertFalse(any(s['category'] == 'company_address' for s in spans))
                self.assertEqual(''.join(s['text'] for s in spans), text)

    def test_marketing_punctuation_preserves_decimals_and_adjacent_sections(self):
        cases = [('No Artificial Colours.', 'Keep refrigerated.', 'storage'),
                 ('Source of 1.5 g fibre!', 'Unrelated trailing sentence.', 'unclassified'),
                 ('Suitable for 豆 lovers?', 'Keep frozen.', 'storage'),
                 ('No Artificial Colours.', 'CONTAINS MILK.', 'allergen_statement')]
        for claim, following, category in cases:
            with self.subTest(claim=claim):
                text = claim + ' ' + following; result = extract_label_sections(text)
                spans = result['sections']
                self.assertEqual([s['text'] for s in spans if s['category'] == 'marketing'], [claim])
                self.assertTrue(any(s['category'] == category and following in s['text'] for s in spans))
                self.assertEqual(''.join(s['text'] for s in spans), text)
                self.assertEqual(result['rawTextSHA256'], hashlib.sha256(text.encode()).hexdigest())
                self.assertEqual([(s['end'], t['start']) for s, t in zip(spans, spans[1:])],
                    [(s['end'], s['end']) for s in spans[:-1]])
                for span in spans:
                    self.assertEqual(text[span['start']:span['end']], span['text'])
                    self.assertEqual(text.encode()[span['utf8Start']:span['utf8End']].decode(), span['text'])
                    self.assertEqual(span['textSHA256'], hashlib.sha256(span['text'].encode()).hexdigest())
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

    def test_decimal_commas_with_recognized_quantity_units_are_not_separators(self):
        cases = [('Sugar 1,5%, Salt', '1,5', '%'),
                 ('Sugar 1.5%, Salt', '1.5', '%'),
                 ('Sugar 1,5–2,5%, Salt', '1,5–2,5', '%'),
                 ('Sugar 0,75 g; Salt', '0,75', 'g')]
        for text, value, unit in cases:
            with self.subTest(text=text):
                result = extract_ingredient_components(text, start=0, end=len(text))
                nodes = result['components']
                self.assertEqual(len(nodes), 2)
                self.assertEqual(nodes[0]['text'], text[:text.rindex('Salt')].rstrip(',; '))
                self.assertEqual(nodes[1]['text'], 'Salt')
                self.assertEqual([(q['valueLexeme'], q['unitLexeme']) for q in nodes[0]['quantities']],
                                 [(value, unit)])
                self.assertEqual(nodes[0]['text'] + result['separators'][0]['text'] + nodes[1]['text'], text)

    def test_unitless_numeric_commas_remain_component_separators(self):
        text = 'Sugar 1,5, Salt'
        result = extract_ingredient_components(text, start=0, end=len(text))
        self.assertEqual([node['text'] for node in result['components']], ['Sugar 1', '5', 'Salt'])
        self.assertTrue(all(not node['quantities'] for node in result['components']))

    def test_nested_decimal_commas_preserve_all_source_spans_hashes_and_limits(self):
        text = 'Préfixe 👩‍🍳: Blend (豆 Sugar 1,5%, Seed (2,5 g)), Salt; Water'
        start = text.index('Blend')
        result = extract_ingredient_components(text, start=start, end=len(text))
        nodes = result['components']
        self.assertEqual([node['text'] for node in nodes],
                         ['Blend (豆 Sugar 1,5%, Seed (2,5 g))', 'Salt', 'Water'])
        children = nodes[0]['children']
        self.assertEqual([node['text'] for node in children], ['豆 Sugar 1,5%', 'Seed (2,5 g)'])
        self.assertEqual(children[0]['quantities'][0]['valueLexeme'], '1,5')
        self.assertEqual(children[1]['quantities'][0]['valueLexeme'], '2,5')
        self.assertEqual(result['rawTextSHA256'], hashlib.sha256(text.encode()).hexdigest())
        def check(value):
            if isinstance(value, dict):
                if {'text', 'start', 'end', 'utf8Start', 'utf8End', 'textSHA256'} <= value.keys():
                    self.assertEqual(text[value['start']:value['end']], value['text'])
                    self.assertEqual(text.encode()[value['utf8Start']:value['utf8End']].decode(), value['text'])
                    self.assertEqual(hashlib.sha256(value['text'].encode()).hexdigest(), value['textSHA256'])
                for child in value.values(): check(child)
            elif isinstance(value, list):
                for child in value: check(child)
        check(result)
        for parent in [nodes[0]]:
            self.assertTrue(all(child['parentComponentId'] == parent['componentId'] for child in parent['children']))
        with self.assertRaisesRegex(RefreshError, 'depth-bound'):
            extract_ingredient_components(text, start=start, end=len(text), max_depth=1)
        with self.assertRaisesRegex(RefreshError, 'node-bound'):
            extract_ingredient_components(text, start=start, end=len(text), max_nodes=1)

    def test_unclosed_group_uncertainty_and_node_bounds(self):
        text = 'Blend (Oil, Water'
        result = extract_ingredient_components(text, start=0, end=len(text))
        self.assertTrue(result['uncertainty'])
        self.assertEqual(result['components'][0]['text'], text)
        with self.assertRaisesRegex(RefreshError, 'node-bound'):
            extract_ingredient_components('A, B', start=0, end=4, max_nodes=1)


if __name__ == '__main__': unittest.main()
