import importlib.util
import unittest
from pathlib import Path

spec = importlib.util.spec_from_file_location('mext', Path(__file__).parents[1] / 'scripts/collect-mext.py')
mext = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mext)


class MextCollectionTests(unittest.TestCase):
    def test_source_parentheses_and_trace_do_not_become_known_quantities(self):
        self.assertEqual(mext.numeric('(11.3)'), {'value': None, 'qualifier': 'source-parenthesized', 'originalText': '(11.3)'})
        self.assertIsNone(mext.numeric('Tr')['value'])
        self.assertEqual(mext.numeric('-')['qualifier'], 'unknown')
        self.assertEqual(mext.numeric('0')['value'], 0)

    def test_main_table_units_are_not_companion_fatty_acid_denominators(self):
        self.assertEqual(mext.unit(6), 'kcal')
        self.assertEqual(mext.unit(9), 'g')
        self.assertEqual(mext.unit(23), 'mg')
        self.assertEqual(mext.unit(43), 'µg')
        self.assertEqual(mext.unit(58), 'mg')
