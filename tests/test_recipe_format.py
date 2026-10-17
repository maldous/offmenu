import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parents[1] / 'scripts'))
from recipe_format import ingredient, sections, number

class RecipeFormatTests(unittest.TestCase):
    def test_quantities_preserve_uncertainty(self):
        self.assertEqual(ingredient('1½ kg rice')['amount'], 1500)
        self.assertEqual(ingredient('牛肉300g')['amount'], 300)
        self.assertEqual(ingredient('50 dkg rizs')['amount'],500)
        self.assertEqual(ingredient('| চাল || ২০০ গ্রাম',True)['amount'],200)
        self.assertEqual(ingredient('| গরুর মাংস (হাড়সহ) || ২ কেজি',True)['amount'],2000)
        self.assertEqual(ingredient('٢ eggs')['amount'], 2)
        for line in ['2 cups rice', '2 cloves garlic', '1–2 kg rice', '1,000 g rice']:
            self.assertIsNone(ingredient(line)['amount'], line)
        self.assertEqual(ingredient('1–2 kg rice')['sourceQuantity']['range'], {'min':1,'max':2})
        self.assertEqual(number('0,500'), .5)

    def test_unknown_units_are_not_count_and_indic_marks_survive(self):
        self.assertIsNone(ingredient('2 cups rice')['amount'])
        self.assertIsNone(ingredient('2 pinches turmeric')['amount'])
        self.assertEqual(ingredient('500 mg salt')['amount'], .5)
        self.assertEqual(ingredient('2 eggs')['amount'], 2)
        self.assertEqual(ingredient('২০০ গ্রাম চাল')['ingredientId'], 'rice')

    def test_wiki_numbered_steps_are_directions(self):
        items, steps, servings = sections('== Ingredients ==\n* 200 g rice\n== Preparation ==\n# Wash rice.\n=== Cooking ===\n# Boil rice.', True)
        self.assertEqual(items[0]['amount'],200)
        self.assertEqual(steps, ['Wash rice.', 'Cooking', 'Boil rice.'])
        self.assertIsNone(servings)

    def test_templates_keep_food_names_and_equipment_is_not_directions(self):
        self.assertIn('aubergines',ingredient("2 {{i|'=oui|aubergine}}s coupées",True)['originalText'])
        items, steps, _=sections('== 材料 ==\n* {{ing|鶏もも肉}}: 300g（一口大にカット）\n== 調理器具 ==\n* {{util|包丁}}\n== 作り方 ==\n; 材料の準備\n: 鶏肉を切り水で煮る。',True)
        self.assertEqual(items[0]['amount'],300)
        self.assertNotIn('包丁',' '.join(steps))
        self.assertEqual(len(items),1)

    def test_recipemd_and_unknown_yield(self):
        items, steps, servings = sections('# Rice\n---\n* 200 g rice\n---\nBoil rice.')
        self.assertEqual(items[0]['ingredientId'],'rice')
        self.assertEqual(steps,['Boil rice.'])
        self.assertIsNone(servings)

    def test_hungarian_bold_headings_and_thai_table_rows(self):
        items, steps, _=sections("'''Hozzávalók:''' 4 személyre\n* 8 dl bor\n'''Elkészítés:'''\n:A bort felforraljuk és keverjük.",True)
        self.assertEqual(items[0]['amount'],800)
        self.assertTrue(steps)
        self.assertEqual(ingredient('| ปลาช่อนทอด || 1 || กิโลกรัม',True)['originalText'],'ปลาช่อนทอด 1 กิโลกรัม')

if __name__ == '__main__': unittest.main()
