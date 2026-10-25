"""Generated dictionaries only: no retained inputs, DB, normalizer or network."""
from copy import deepcopy
from dataclasses import replace
import unittest

from offmenu.refresh.product_adapters import (
    OFF_CATEGORY_FIELD_VERSION, ProductContext, ProductLimits, _off, _product_contract,
)


class ProductCategoryPreservationTest(unittest.TestCase):
    def setUp(self):
        self.context = ProductContext('off', 'generated-category-release',
            '2026-10-25T00:00:00Z', 'synthetic terms', 'synthetic publisher', 'a'*64, 'b'*64)

    def project(self, **fields):
        return list(_off(self.context, {'code': '001234', 'product_name': 'Generated item',
            'nutriments': {'proteins_100g': 2.3}, **fields}))

    def test_exact_original_fields_and_multiple_paths_survive(self):
        source = {
            'categories': ' CATÉGORIE brute, Other / unknown ',
            'categories_tags': ['fr:Exemple', 'en:Synthetic', 'fr:Exemple'],
            'categories_hierarchy': [['fr:Parent', 'fr:Leaf'], ['en:Other', 'fr:Leaf']],
            'categories_properties': {'source-code': '0007', 'unknown': None},
            'categories_properties_tags': ['categories-unknown'],
            'category_properties': {'publisher': {'original': False}},
            'food_groups': 'en:synthetic-group',
            'food_groups_tags': ['en:synthetic-group', 'fr:Autre'],
            'food_groups_hierarchy': ['en:ancestor', 'en:synthetic-group'],
            'categories_lc': 'fr', 'lang': 'fr', 'lc': 'en',
            'languages_codes': {'fr': 2, 'en': 1},
        }
        product, profile = self.project(**source)
        self.assertEqual(product['data']['sourceCategoryFields'], source)
        evidence = product['provenance']['sourceCategoryFields']
        for key in source:
            self.assertEqual(evidence['fields'][key], {'state': 'present', 'sourcePointer': '/' + key})
        self.assertEqual(product['data']['identifiers'], [{'system': 'barcode', 'value': '001234'}])
        self.assertEqual(profile['data']['nutrients']['protein']['sourceAmount'], 2.3)

    def test_missing_null_empty_and_unknown_are_distinct(self):
        product, _ = self.project(categories=None, categories_tags=[], food_groups='unknown',
                                  categories_properties={}, lang='und')
        values = product['data']['sourceCategoryFields']
        states = product['provenance']['sourceCategoryFields']['fields']
        self.assertNotIn('categories_hierarchy', values)
        self.assertEqual(states['categories_hierarchy'], {'state': 'missing', 'sourcePointer': None})
        self.assertIsNone(values['categories'])
        self.assertEqual(states['categories']['state'], 'null')
        self.assertEqual(values['categories_tags'], [])
        self.assertEqual(states['categories_tags']['state'], 'present')
        self.assertEqual(values['food_groups'], 'unknown')
        self.assertEqual(states['food_groups']['state'], 'present')
        self.assertEqual(values['categories_properties'], {})
        self.assertEqual(values['lang'], 'und')

    def test_versions_remain_source_keys_not_adapter_or_taxonomy_inference(self):
        # Synthetic optional keys test preservation, not actual OFF availability.
        product, _ = self.project(categories_taxonomy_version=None, taxonomy_version='Unknown/2026',
                                  food_groups_version={'original': 'v0'})
        values = product['data']['sourceCategoryFields']
        evidence = product['provenance']['sourceCategoryFields']
        self.assertEqual(values['taxonomy_version'], 'Unknown/2026')
        self.assertIsNone(values['categories_taxonomy_version'])
        self.assertEqual(evidence['fields']['categories_taxonomy_version']['state'], 'null')
        self.assertEqual(values['food_groups_version'], {'original': 'v0'})
        self.assertEqual(evidence['projectionVersion'], OFF_CATEGORY_FIELD_VERSION)
        self.assertEqual(evidence['sourceTaxonomyVersionStatus'], 'unverified-source-assertions')
        self.assertEqual(evidence['sourceVersionKeys'],
            ['categories_taxonomy_version', 'food_groups_version', 'taxonomy_version'])
        absent, _ = self.project()
        self.assertEqual(absent['provenance']['sourceCategoryFields']['sourceVersionKeys'], [])
        self.assertEqual(absent['provenance']['sourceCategoryFields']['sourceTaxonomyVersionStatus'], 'unknown')

    def test_no_unrelated_payload_or_semantic_mapping_is_promoted(self):
        product, _ = self.project(categories='not a composition',
            categories_contributor_email='DO NOT PROJECT', image_url='DO NOT PROJECT',
            owner='DO NOT PROJECT', canonicalIngredient='DO NOT PROMOTE',
            record_disposition='DO NOT PROMOTE')
        self.assertEqual(product['data']['sourceCategoryFields'], {'categories': 'not a composition'})
        for key in ['categories_contributor_email', 'image_url', 'owner',
                    'canonicalIngredient', 'record_disposition', 'ingredients']:
            self.assertNotIn(key, product['data'])
        self.assertEqual(product['data']['qualificationStatus'], 'unverified-source-assertions')
        self.assertEqual(product['provenance']['releaseId'], 'generated-category-release')
        self.assertEqual(product['provenance']['recordId'], '001234')
        self.assertEqual(product['provenance']['rightsEvidenceSha256'], 'a'*64)
        self.assertEqual(product['provenance']['scopeEvidenceSha256'], 'b'*64)

    def test_projection_does_not_mutate_or_share_source_category_containers(self):
        source = {'code': '001234', 'categories_tags': ['fr:Original'],
                  'categories_properties': {'nested': [None, False, '0001']}}
        before = deepcopy(source)
        product, _ = list(_off(self.context, source))
        self.assertEqual(source, before)
        product['data']['sourceCategoryFields']['categories_properties']['nested'].append('changed')
        product['data']['sourceCategoryFields']['categories_tags'].append('en:changed')
        self.assertEqual(source, before)

    def test_off_cache_contract_changes_without_changing_other_source_contracts(self):
        files = [{'role': 'products', 'sha256': 'c'*64}]
        contract = _product_contract(self.context, ProductLimits(), files)
        self.assertEqual(contract['offCategoryFieldProjectionVersion'], OFF_CATEGORY_FIELD_VERSION)
        legacy = dict(contract)
        del legacy['offCategoryFieldProjectionVersion']
        self.assertNotEqual(contract, legacy)  # existing exact-contract retry rejects stale OFF output
        for source_id in ['prices', 'usda-files']:
            other = _product_contract(replace(self.context, source_id=source_id), ProductLimits(), files)
            self.assertNotIn('offCategoryFieldProjectionVersion', other)
            self.assertEqual(set(other), set(legacy))


if __name__ == '__main__':
    unittest.main()
