import importlib.util
import unittest
from pathlib import Path

spec = importlib.util.spec_from_file_location('overture', Path(__file__).parents[1] / 'scripts/collect-overture.py')
collector = importlib.util.module_from_spec(spec)
spec.loader.exec_module(collector)

class OvertureCollectionTests(unittest.TestCase):
    def row(self, hierarchy):
        return {'id': 'gers:001', 'names': {'primary': 'Food shop', 'common': [('fr', 'Épicerie')]},
                'taxonomy': {'hierarchy': hierarchy, 'primary': hierarchy[-1]},
                'sources': [{'dataset': 'meta', 'license': 'CDLA-Permissive-2.0', 'record_id': 'provider-id', 'update_time': '2026-09-01'}],
                'addresses': [{'country': 'AU', 'locality': 'Town', 'freeform': 'Street address'}],
                'phones': ['contact'], 'emails': ['contact@example.org'], 'operating_status': 'open'}

    def test_food_selection_excludes_tobacco_and_unrelated_categories(self):
        self.assertTrue(collector.eligible(self.row(['shopping', 'food_and_beverage_store', 'grocery_store'])))
        self.assertTrue(collector.eligible(self.row(['food_and_drink', 'restaurant'])))
        self.assertFalse(collector.eligible(self.row(['shopping', 'food_and_beverage_store', 'tobacco_shop'])))
        self.assertFalse(collector.eligible(self.row(['health_care', 'hospital'])))

    def test_open_place_never_implies_inventory_and_contacts_stay_out(self):
        result = collector.normalize(self.row(['shopping', 'food_and_beverage_store', 'grocery_store']), 'release', 'hash', 'now')
        self.assertEqual(result['countries'], ['AU'])
        self.assertEqual(result['data']['inventoryAvailability'], 'unknown')
        self.assertFalse(result['data']['ownershipVerified'])
        self.assertNotIn('phones', result['data'])
        self.assertNotIn('emails', result['data'])
        self.assertNotIn('freeform', result['data']['locations'][0])
        self.assertEqual(result['data']['names']['fr'], 'Épicerie')

    def test_unknown_country_is_not_inferred_and_unreviewed_licence_rejected(self):
        row = self.row(['food_and_drink', 'restaurant'])
        row['addresses'] = [{'locality': 'Unknown country'}]
        self.assertEqual(collector.normalize(row, 'release', 'hash', 'now')['countries'], [])
        row['sources'][0]['license'] = 'proprietary'
        with self.assertRaisesRegex(ValueError, 'licence'):
            collector.normalize(row, 'release', 'hash', 'now')
