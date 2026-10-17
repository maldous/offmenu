import json
import tempfile
import unittest
from pathlib import Path
from offmenu.core import connect, import_products, import_recipes, map_product, add_inventory, meals

class MatchingTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db = connect(str(Path(self.tmp.name) / 'test.sqlite'))
        self.db.execute("INSERT INTO products VALUES('001','Rice',NULL,NULL)")
        self.db.commit()
        map_product(self.db, '001', 'rice')

    def tearDown(self):
        self.db.close()
        self.tmp.cleanup()

    def recipe(self, ingredients):
        path = Path(self.tmp.name) / 'recipes.json'
        path.write_text(json.dumps([{'id': 'r', 'title': 'Rice', 'servings': 2, 'source': 'test', 'license': 'CC0', 'ingredients': ingredients}]))
        import_recipes(self.db, path)

    def test_quantity_scaling(self):
        add_inventory(self.db, '001', 100, 'g')
        self.recipe([{'ingredient': 'rice', 'quantity': 100, 'unit': 'g'}])
        self.assertEqual(meals(self.db)[0]['status'], 'ready')
        self.assertEqual(meals(self.db, servings=4)[0]['missing'][0]['quantity'], 100)

    def test_repeated_requirements_cannot_reuse_same_stock(self):
        add_inventory(self.db, '001', 100, 'g')
        self.recipe([{'ingredient': 'rice', 'quantity': 75, 'unit': 'g'}]*2)
        self.assertEqual(meals(self.db)[0]['missing'][0]['quantity'], 50)

    def test_expired_inventory_excluded(self):
        add_inventory(self.db, '001', 100, 'g', '2020-01-01')
        self.recipe([{'ingredient': 'rice', 'quantity': 100, 'unit': 'g'}])
        self.assertEqual(meals(self.db, as_of='2026-10-12')[0]['status'], 'missing')

    def test_unknown_and_incompatible_units_never_ready(self):
        add_inventory(self.db, '001', 100, 'g')
        self.recipe([{'ingredient': 'rice'}])
        self.assertEqual(meals(self.db)[0]['status'], 'needs_review')
        self.recipe([{'ingredient': 'rice', 'quantity': 100, 'unit': 'ml'}])
        self.assertEqual(meals(self.db)[0]['status'], 'missing')

    def test_bad_import_rolls_back_and_preserves_barcode(self):
        path = Path(self.tmp.name) / 'products.jsonl'
        path.write_text('{"code":"0002","product_name":"Milk"}\n{"code":123}\n')
        with self.assertRaises(ValueError):
            import_products(self.db, path)
        self.assertEqual(self.db.execute('SELECT COUNT(*) FROM products').fetchone()[0], 1)

    def test_negative_and_nonfinite_quantity_rejected(self):
        for quantity in (-1, float('nan'), float('inf')):
            with self.assertRaises(ValueError):
                add_inventory(self.db, '001', quantity, 'g')

if __name__ == '__main__':
    unittest.main()
