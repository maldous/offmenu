import hashlib
import unittest

from offmenu.refresh.product_label_sections import extract_label_sections
from offmenu.refresh.core import RefreshError


class ProductLabelSectionTests(unittest.TestCase):
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


if __name__ == '__main__': unittest.main()
