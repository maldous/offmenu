import importlib.util
import tempfile
import unittest
from pathlib import Path
import openpyxl

spec = importlib.util.spec_from_file_location('afcd', Path(__file__).parents[1] / 'scripts/import-afcd.py')
afcd = importlib.util.module_from_spec(spec)
spec.loader.exec_module(afcd)

class AFCDImportTests(unittest.TestCase):
    def test_mass_volume_and_non_food_bases_remain_distinct(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            details = openpyxl.Workbook()
            sheet = details.active
            sheet.title = 'Food details'
            sheet.append(['Public Food Key', 'Classification', 'Derivation', 'Food Name', 'Food Description', 'Sampling Details', 'Nitrogen Factor', 'Fat Factor', 'Specific Gravity', 'Analysed Portion', 'Unanalysed Portion'])
            sheet.append(['F000001', 1, 'Analysed', 'Milk', 'Sample', 'Laboratory', 6.25, 1, 1.03, '100%', '0%'])
            details.save(root / 'Food-Details.xlsx')
            profiles = openpyxl.Workbook()
            profiles.remove(profiles.active)
            for name, value in [('All solids & liquids per 100 g', 3), ('Liquids only per 100 mL', 3.09)]:
                sheet = profiles.create_sheet(name)
                sheet.append(['Public Food Key', 'Classification', 'Derivation', 'Food Name', 'Protein (g)', 'C4 (%T)', 'Alanine (mg/gN)', 'Vitamin C (mg)'])
                sheet.append(['F000001', 1, 'Analysed', 'Milk', value, 4, 20, None])
            profiles.save(root / 'Nutrient-profiles.xlsx')
            mass, volume = afcd.records(root)
            self.assertNotEqual(mass['id'], volume['id'])
            self.assertEqual(mass['data']['basis']['unit'], 'g')
            self.assertEqual(volume['data']['basis']['unit'], 'ml')
            self.assertEqual(volume['data']['nutrients']['protein']['value'], 3.09)
            self.assertIsNone(mass['data']['nutrients']['vitaminC']['value'])
            self.assertEqual(mass['data']['nutrients']['afcd:column:6']['basis']['unit'], 'g-total-fatty-acids')
            self.assertEqual(mass['data']['nutrients']['afcd:column:7']['basis']['amount'], 1)
            self.assertIn('FSANZ', mass['provenance']['license'])
            self.assertIn('Australian', mass['provenance']['countryNotice'])
