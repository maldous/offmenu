"""Focused synthetic checks; no retained source bodies opened by this suite."""
from copy import deepcopy
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import query_normalization as q


def decision(value='Milk', domain='ingredient', pointer='/data/name'):
    return {'candidateId': 'synthetic-candidate', 'domain': domain, 'sourcePointer': pointer,
            'sourceValueEvidence': value, 'sourceLanguage': None, 'applicationStatus': 'unresolved',
            'reason': 'no-qualified-context', 'targets': []}


def row(record='synthetic:product:1', decisions=None):
    return {'sourceRecordId': record, 'sourceKind': 'product',
            'originalSource': {'file': '/MUST-NOT-OPEN/original', 'line': 1, 'lineSha256': 'synthetic'},
            'retainedEvidence': {'path': '/MUST-NOT-OPEN/evidence'},
            'decisions': decisions if decisions is not None else [decision()]}


REFS = {'application': {'path': '/synthetic/completed', 'sha256': 'synthetic-sha'}}
REGISTRY = {'mappings': []}


class QueryChecks(unittest.TestCase):
    def test_deterministic_bytes_no_file_dereference(self):
        rows = [row()]
        with patch.object(Path, 'open', side_effect=AssertionError('no source read')):
            a = q.encode(q.query(rows, REGISTRY, REFS, rows[0]['sourceRecordId']))
            b = q.encode(q.query(rows, REGISTRY, REFS, rows[0]['sourceRecordId']))
        self.assertEqual(a, b)

    def test_occurrences_not_merged_or_id_joined(self):
        rows = [row(), row(), row('synthetic:nutrientProfile:1')]
        result = q.query(rows, REGISTRY, REFS, 'synthetic:product:1')
        self.assertEqual(len(result['observations']), 2)
        self.assertNotEqual(result['observations'][0]['observationRef'], result['observations'][1]['observationRef'])
        for item in result['observations']:
            self.assertEqual(item['profileEdges'], [])
            self.assertEqual(item['permittedIngredientEdges'], [])
            self.assertEqual(item['recipeEdges'], [])

    def test_variant_labels_and_language_preserved_not_ingredient_mapping(self):
        data = [decision('Milk'), decision('Soymilk'), decision('cow milk'), decision('lait')]
        data[-1]['sourceLanguage'] = 'fr'
        result = q.query([row(decisions=data)], REGISTRY, REFS, 'synthetic:product:1')['observations'][0]
        self.assertEqual([x['verbatim'] for x in result['fieldEvidence']], ['Milk', 'Soymilk', 'cow milk', 'lait'])
        self.assertEqual([x['sourceLanguage'] for x in result['fieldEvidence']], [None, None, None, 'fr'])
        self.assertTrue(all(x['role'] == 'product-label' for x in result['fieldEvidence']))
        self.assertEqual(result['permittedIngredientEdges'], [])

    def test_exact_micro_sign_only_and_never_original_unit_qualification(self):
        mapping = {'targetId': 'synthetic:microgram', 'originalAlias': 'µg', 'originalLanguage': None}
        reg = {'mappings': [mapping]}
        d = decision('µg', 'unit', '/data/nutrientFields/n/unit/notation')
        d.update(applicationStatus='projected-unit-format-reference', originalSourceUnitQualification=False,
                 targets=[{'id': 'synthetic:microgram', 'mappingPointer': '/mappings/0', 'reviewedMappingVerbatim': deepcopy(mapping)}])
        self.assertEqual(q.scoped_units(d, reg)[0]['reviewedMappingVerbatim']['originalLanguage'], None)
        for spelling in ['ug', 'μg', 'µG']:
            bad = deepcopy(d); bad['sourceValueEvidence'] = spelling
            with self.assertRaises(ValueError): q.scoped_units(bad, reg)
        bad = deepcopy(d); bad['originalSourceUnitQualification'] = True
        with self.assertRaises(ValueError): q.scoped_units(bad, reg)

    def test_opaque_placeholder_is_not_source_absence_or_token_edges(self):
        r = row(decisions=[decision(None, pointer='/data/ingredientsText')])
        declaration = 'SALT, WATER (UNKNOWN VARIANT)'
        retained = {'id': r['sourceRecordId'], 'data': {
            'ingredientsText': declaration, 'names': {'en': 'Label only'},
            'fieldEvidence': {'ingredientDeclaration': {'state': 'present', 'sourceValue': declaration}},
            'nutritionId': None, 'nutritionSourceBasis': 'serving', 'serving': None,
        }, 'provenance': {'sourceId': 'synthetic', 'license': 'fixture-only'}}
        out = q.query([r], REGISTRY, REFS, r['sourceRecordId'], retained)['observations'][0]
        self.assertIsNone(out['decisionsVerbatim'][0]['sourceValueEvidence'])
        self.assertEqual(out['ingredientDeclarations'][0]['verbatim'], declaration)
        self.assertIsNone(out['ingredientDeclarations'][0]['language'])
        self.assertEqual(out['ingredientDeclarations'][0]['termEdges'], [])
        self.assertEqual(out['supportedQuantityValues'], [])
        self.assertEqual(out['supportedNutrientValues'], [])
        self.assertEqual(out['retainedProductFacts']['nutritionSourceBasis'], 'serving')

    def test_nutrient_label_unit_candidate_not_known_amount_or_zero(self):
        r = row(decisions=[decision('salt', 'nutrient', '/data/nutrientFields/salt'),
                           decision('g', 'unit', '/data/nutrientFields/salt/unit')])
        out = q.query([r], REGISTRY, REFS, r['sourceRecordId'])['observations'][0]
        self.assertEqual(out['nutrientFields'][0]['verbatimLabel'], 'salt')
        self.assertIsNone(out['nutrientFields'][0]['amount'])
        self.assertIsNone(out['nutrientFields'][0]['basis'])
        self.assertEqual(out['permittedIngredientEdges'], [])

    def test_unmatched_selector_has_limited_scope(self):
        out = q.query([row()], REGISTRY, REFS, 'not-here')
        self.assertEqual(out['observations'], [])
        self.assertEqual(out['scope']['matchedOccurrences'], 0)
        self.assertIn('no source-wide absence', out['scope']['notFoundMeaning'])
        with self.assertRaises(ValueError):
            q.query([row()], REGISTRY, REFS, 'synthetic:product:1', {'id': 'different'})

    def test_fixed_input_mutation_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            p = Path(directory) / 'owned-disposable-fixture'
            p.write_bytes(b'changed')
            with self.assertRaisesRegex(ValueError, 'input-pin-mismatch'):
                q.read_pinned(p, q.digest(b'original'))
        self.assertIsNone(q.selected_retained(row('not-the-selected-product')))


if __name__ == '__main__':
    unittest.main()
