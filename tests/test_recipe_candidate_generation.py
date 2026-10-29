"""Generated examples only; no retained recipe bodies or stores are read."""
import copy
import json
from pathlib import Path
import unittest

import jsonschema
from offmenu.refresh.recipe_candidate_generation import build_generated_fixture, canonical, digest, NS

CONTRACT_ROOT = Path(__file__).resolve().parents[1] / 'contracts' / 'corpus'
CONTRACT = (CONTRACT_ROOT / 'common-data-contract.json').read_bytes()
SCHEMA = (CONTRACT_ROOT / 'common-data.schema.json').read_bytes()


def fixture(number=1):
    raw = {'text': '2 spoonfuls chopped sample leaves', 'quantity': {'value': '2',
           'unit': 'spoonfuls', 'basis': None}, 'preparation': 'chopped',
           'aliases': ['sample leaves'], 'uncertainty': [], 'alternatives': None}
    return {'sourceId': 'urn:offmenu:generated:recipe-test', 'recordId': str(number),
            'revision': 'fixture-v1', 'contentSha256': digest(canonical(raw)),
            'pointer': '/recipes/' + str(number), 'mentions': [dict(raw,
            pointer='/recipes/' + str(number) + '/ingredients/0')]}


class AdapterTests(unittest.TestCase):
    def build(self, rows=None, contract=CONTRACT, schema=SCHEMA):
        return build_generated_fixture(rows or [fixture()], contract, schema,
                                       actor='worker13-generated-tests')

    def test_matches_exact_shared_schema(self):
        packet = self.build()
        jsonschema.Draft202012Validator(json.loads(SCHEMA),
            format_checker=jsonschema.FormatChecker()).validate(packet)
        self.assertEqual(len(packet['resources']), 2)
        self.assertEqual(len(packet['citations']), 1)
        self.assertTrue(all(x['id'].startswith(NS) for key in
            ('resources', 'assertions', 'relations', 'citations') for x in packet[key]))

    def test_deterministic_and_order_independent(self):
        self.assertEqual(canonical(self.build([fixture(1), fixture(2)])),
                         canonical(self.build([fixture(2), fixture(1)])))

    def test_same_label_keeps_occurrence_identity(self):
        packet = self.build([fixture(1), fixture(2)])
        mentions = [x for x in packet['resources'] if x['type'].endswith(':IngredientMention')]
        self.assertEqual(len({x['id'] for x in mentions}), 2)
        self.assertTrue(all(x['identityStatus'] == 'source-scoped' for x in mentions))

    def test_no_canonical_matches_or_food_classes(self):
        packet = self.build()
        self.assertEqual({x['predicateId'] for x in packet['relations']},
                         {'urn:offmenu:relation:mentionsIngredient'})
        self.assertFalse(any(x['type'].endswith(':FoodIngredient') for x in packet['resources']))
        self.assertEqual(packet['translations'], [])

    def test_preserves_raw_null_empty_and_lexical_quantity(self):
        packet = self.build()
        values = [a['value'] for a in packet['assertions']]
        quantity = next(v for v in values if v['kind'] == 'structure')
        self.assertEqual(quantity['fields']['value']['value'], '2')
        self.assertEqual(quantity['fields']['unit']['value'], 'spoonfuls')
        self.assertEqual(quantity['fields']['basis'], {'kind': 'null', 'value': None})
        self.assertIn({'kind': 'list', 'items': []}, values)
        self.assertIn({'kind': 'null', 'value': None}, values)
        self.assertTrue(all(n['language'] == 'und' for r in packet['resources'] for n in r['names']))

    def test_absent_differs_from_explicit_null(self):
        a = fixture(); b = copy.deepcopy(a)
        del b['mentions'][0]['alternatives']
        self.assertNotEqual(canonical(self.build([a])), canonical(self.build([b])))

    def test_actual_source_and_first_assets_rejected(self):
        row = fixture(); row['sourceId'] = 'wikibooks:recipe:held'
        with self.assertRaisesRegex(ValueError, 'not admitted'): self.build([row])
        row = fixture(); row['assetPath'] = 'apps/web/assets/recipe-ingredient-aliases.json'
        with self.assertRaisesRegex(ValueError, 'excluded'): self.build([row])

    def test_duplicate_and_foreign_occurrence_rejected(self):
        with self.assertRaisesRegex(ValueError, 'duplicate'): self.build([fixture(), fixture()])
        row = fixture(); row['mentions'][0]['pointer'] = '/other/0'
        with self.assertRaisesRegex(ValueError, 'pointer'): self.build([row])
        row = fixture(); row['mentions'] *= 2
        with self.assertRaisesRegex(ValueError, 'unique'): self.build([row])

    def test_pins_reject_even_valid_other_contract(self):
        with self.assertRaisesRegex(ValueError, 'pin mismatch'): self.build(contract=CONTRACT + b' ')
        with self.assertRaisesRegex(ValueError, 'pin mismatch'): self.build(schema=SCHEMA + b' ')

    def test_bounds_and_nonfinite_numbers(self):
        with self.assertRaisesRegex(ValueError, 'eight'): self.build([fixture(i) for i in range(9)])
        row = fixture(); row['mentions'][0]['text'] = 'x' * 65536
        with self.assertRaisesRegex(ValueError, '64KiB'): self.build([row])
        row = fixture(); row['mentions'][0]['quantity'] = float('nan')
        with self.assertRaises(ValueError): self.build([row])
        row = fixture(); row['mentions'][0]['uncertainty'] = [[[[[[[[[[None]]]]]]]]]]
        with self.assertRaisesRegex(ValueError, 'nesting'): self.build([row])

    def test_input_not_mutated(self):
        row = fixture(); before = copy.deepcopy(row)
        self.build([row]); self.assertEqual(row, before)

    def test_invalid_language_and_missing_evidence_rejected(self):
        row = fixture(); row['language'] = None
        with self.assertRaisesRegex(ValueError, 'language'): self.build([row])
        row = fixture(); row['contentSha256'] = 'unknown'
        with self.assertRaisesRegex(ValueError, 'hash'): self.build([row])

    def test_unknown_recipe_fields_retained_without_new_semantics(self):
        row = fixture(); row['yield'] = None; row['note'] = 'generated uncertain yield'
        packet = self.build([row])
        prop = 'urn:offmenu:property:source-field:recipe-envelope-' + 'yield'.encode().hex()
        assertion = next(a for a in packet['assertions'] if a['propertyId'] == prop)
        self.assertEqual(assertion['value'], {'kind': 'null', 'value': None})
        self.assertEqual(assertion['status'], 'candidate')

    def test_mention_limit(self):
        row = fixture()
        row['mentions'] = [dict(row['mentions'][0], pointer='/recipes/1/ingredients/' + str(i))
                           for i in range(33)]
        with self.assertRaisesRegex(ValueError, '32 mentions'): self.build([row])

    def test_explicit_occurrence_language_over_envelope(self):
        row = fixture(); row['language'] = 'en'
        row['mentions'][0].update(language='fr', text='lait')
        packet = self.build([row])
        mention = next(r for r in packet['resources'] if r['type'].endswith(':IngredientMention'))
        statement = next(a for a in packet['assertions']
                         if a['propertyId'].endswith(':originalIngredientStatement'))
        self.assertEqual(mention['names'][0]['language'], 'fr')
        self.assertEqual(statement['value'], mention['names'][0])
        raw_language = next(a for a in packet['assertions']
            if a['propertyId'].endswith('recipe-' + 'language'.encode().hex()))
        self.assertEqual(raw_language['value']['value'], 'fr')
        jsonschema.Draft202012Validator(json.loads(SCHEMA)).validate(packet)

    def test_unknown_occurrence_language_does_not_inherit_edition(self):
        row = fixture(); row['language'] = 'en'
        packet = self.build([row])
        mention = next(r for r in packet['resources'] if r['type'].endswith(':IngredientMention'))
        self.assertEqual(mention['names'][0]['language'], 'und')
        row['mentions'][0]['language'] = 'und'
        self.assertEqual(next(r for r in self.build([row])['resources']
            if r['type'].endswith(':IngredientMention'))['names'][0]['language'], 'und')

    def test_invalid_occurrence_language_rejected(self):
        for value in (None, '', 'English language', 1):
            row = fixture(); row['mentions'][0]['language'] = value
            with self.assertRaisesRegex(ValueError, 'language'): self.build([row])


if __name__ == '__main__':
    unittest.main()
