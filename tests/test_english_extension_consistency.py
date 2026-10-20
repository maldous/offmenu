"""Otherwise valid affirmative witnesses cannot override inconsistent claims."""
import copy
import unittest

from offmenu.refresh.english_extension import ReviewedWitness
import test_english_extension as fixtures
import test_english_extension_variants as variants
from test_english_extension import encode


class RelationshipConsistencyTests(unittest.TestCase):
    def setUp(self):
        variants.ReviewedVariantTests.setUp(self)
        self.witness_calls = []
        def relationship(key):
            self.witness_calls.append(key)
            return self.f.relationships.get(key)
        self.f.relationship = relationship

    check = fixtures.ReviewedRelationshipTest.check
    version = fixtures.ReviewedRelationshipTest.version
    witness = fixtures.ReviewedRelationshipTest.witness
    bind_relation = fixtures.ReviewedRelationshipTest.bind_relation
    variant = variants.ReviewedVariantTests.variant

    def bind_variant(self, assertion):
        variants.ReviewedVariantTests.bind(self, assertion)
        old = self.f.relationships[assertion['assertionId']]
        scope = copy.deepcopy(old.scope)
        native, external = scope['sourceRecords']
        scope['sourceRecords'] = [copy.deepcopy(native if key == 'native-recipe' else external)
                                  for key in assertion['sourceRecordRefs']]
        self.f.relationships[assertion['assertionId']] = ReviewedWitness(
            self.f.pin('variant-consistency-review.json', encode(scope)), scope, old.authority)

    def test_reviewed_product_unresolved_relation_rejected_before_valid_witness(self):
        self.f.product_link(); assertion = self.f.ext['productIngredientLinks'][0]
        assertion.update(state='reviewed', relation='unresolved')
        self.bind_relation(assertion)
        self.check(('english-product-state-inconsistent',))
        self.assertEqual(self.witness_calls, [])

    def test_distinct_known_product_relations_with_valid_witness_are_preserved(self):
        for relation in ('declares-ingredient', 'refers-to-ingredient'):
            with self.subTest(relation=relation):
                self.f.product_link(); assertion = self.f.ext['productIngredientLinks'][0]
                assertion.update(state='reviewed', relation=relation)
                self.bind_relation(assertion); self.check()
        self.assertTrue(self.witness_calls)

    def test_product_state_relation_combinations_remain_consistent(self):
        self.f.product_link(); assertion = self.f.ext['productIngredientLinks'][0]
        assertion.update(state='unresolved', relation='unresolved'); self.check()
        self.assertEqual(self.witness_calls, [])
        for state, relation in [('unresolved', 'declares-ingredient'), ('proposed', 'unresolved'), ('rejected', 'unresolved')]:
            with self.subTest(state=state, relation=relation):
                assertion.update(state=state, relation=relation)
                self.bind_relation(assertion)
                self.check(('english-product-state-inconsistent',))
        self.assertEqual(self.witness_calls, [])

    def test_duplicate_native_refs_all_variants_rejected_before_valid_witness(self):
        for relation in variants.RELATIONS:
            with self.subTest(relation=relation):
                assertion = self.variant(relation)
                assertion['sourceRecordRefs'] = ['native-recipe', 'native-recipe']
                self.bind_variant(assertion)
                self.check(('english-variant-record-duplicate',))
        self.assertEqual(self.witness_calls, [])

    def test_duplicate_external_or_mixed_variant_refs_rejected(self):
        for refs in (['R', 'R'], ['native-recipe', 'R', 'R']):
            with self.subTest(refs=refs):
                assertion = self.variant(); assertion['sourceRecordRefs'] = refs
                self.bind_variant(assertion)
                self.check(('english-variant-record-duplicate',))
        self.assertEqual(self.witness_calls, [])

    def test_distinct_variant_refs_all_relations_with_valid_witness_are_preserved(self):
        for relation in variants.RELATIONS:
            with self.subTest(relation=relation):
                assertion = self.variant(relation)
                self.bind_variant(assertion); self.check()
                self.assertFalse(assertion['mergePerformed'])
        self.assertTrue(self.witness_calls)


if __name__ == '__main__':
    unittest.main()
