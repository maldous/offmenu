"""Generated contracts; never instantiate the reader or open a source snapshot."""
import importlib.util
from pathlib import Path
import unittest

spec = importlib.util.spec_from_file_location(
    "private_source_lookup_contract", Path(__file__).parents[1] / "integrations/staged/private-product-lookup" / "lookup.py")
lookup = importlib.util.module_from_spec(spec)
spec.loader.exec_module(lookup)


class PrivateSourceLookupContract(unittest.TestCase):
    def test_lexical_barcode_is_preserved_without_numeric_or_unicode_aliases(self):
        self.assertEqual(lookup.exact_barcode("0000123456789"), "0000123456789")
        for value in (123456789, " 123", "123 ", "١٢٣", "1' OR 1=1", "1" * 65, ""):
            with self.subTest(value=value), self.assertRaises(lookup.LookupError):
                lookup.exact_barcode(value)

    def test_count_does_not_invent_total_beyond_the_selected_window(self):
        exact = lookup.bounded_count(list(range(8)), 8)
        limited = lookup.bounded_count(list(range(9)), 8)
        self.assertEqual(exact["total"], 8)
        self.assertEqual(limited["returned"], 8)
        self.assertIsNone(limited["total"])
        self.assertEqual(limited["totalState"], "unknown-beyond-bound")

    def test_bounded_child_references_reject_truncation_and_expansion(self):
        self.assertEqual(lookup.unpack(bytes([0, 1, 128, 1])), [0, 1, 128])
        for value in (bytes([128]), bytes([128] * 10), bytes([0] * 129), bytes([0] * 2049)):
            with self.subTest(length=len(value)), self.assertRaises(lookup.LookupError):
                lookup.unpack(value)


if __name__ == "__main__":
    unittest.main()
