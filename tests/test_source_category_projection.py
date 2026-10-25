import unittest
from offmenu.refresh.product_detail_query import _fields


class SourceCategoryProjectionTests(unittest.TestCase):
    def test_supplied_claims_and_unknown_extensions_survive_without_canonical_mapping(self):
        claims = {'schema': 'offmenu-source-category-claims/1',
                  'fields': {'categories': 'Pâtisserie, 菓子', 'categories_tags': None,
                             'categories_hierarchy': ['en:foods', 'fr:pâtisseries'],
                             'categories_taxonomy_version': 'fixture-v3',
                             'lang': 'fr', 'unknown/extension': {'original': ['A', 'A']}},
                  'mappingState': 'unmapped', 'ingredientCompositionAsserted': False}
        fields = _fields([{'data': {'sourceCategoryClaims': claims}, 'provenance': {}}],
                         'off-legacy-paired-gzip')
        result = fields['sourceCategoryClaims']
        self.assertEqual(result['state'], 'present')
        self.assertEqual(result['value'], claims)
        self.assertEqual(result['fieldPointer'], '/0/data/sourceCategoryClaims')
        self.assertEqual(result['valueOrigin'], 'upstream-projection')
        self.assertEqual(result['sourceFieldState'], 'unknown')

    def test_old_projection_omission_does_not_claim_original_source_absence(self):
        result = _fields([{'data': {}, 'provenance': {}}], 'off-legacy-paired-gzip')['sourceCategoryClaims']
        self.assertEqual(result['state'], 'missing')
        self.assertEqual(result['reasonCode'], 'projection-field-absent')
        self.assertEqual(result['sourceFieldState'], 'unknown')
        self.assertIsNone(result['value'])

    def test_an_unselected_representation_is_explicitly_not_loaded(self):
        result = _fields([{'data': {'sourceCategoryClaims': {'unqualified': True}}, 'provenance': {}}],
                         'usda-native-jsonl')['sourceCategoryClaims']
        self.assertEqual(result['state'], 'not-loaded')
        self.assertIsNone(result['value'])
        self.assertIsNone(result['evidenceSha256'])


if __name__ == '__main__':
    unittest.main()
