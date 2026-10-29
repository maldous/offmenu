"""Focused real parsed-input and negative controls; no existing store or model."""
from copy import deepcopy
from hashlib import sha256
import json
import os
from pathlib import Path
import tempfile
import unittest

from offmenu.refresh.ingredient_vocabulary_generation import (
    AFCD, ALIAS, PHOTO, PINS, HISTORICAL_PINS, VERSION, build_generation, canonical, digest,
    inspect_generation, persist_new_generation, propose_revision,
)


class IngredientVocabularyGenerationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = Path(os.environ.get('OFFMENU_VOCABULARY_TEST_ASSET_ROOT', Path(__file__).resolve().parents[1]))
        cls.assets = {path: (cls.root / path).read_bytes() for path in PINS}
        cls.contract = (cls.root / 'contracts/corpus/common-data-contract.json').read_bytes()

    def generate(self, **changes):
        return build_generation(changes.get('assets', self.assets), changes.get('contract', self.contract),
                                generation_version=changes.get('version', 'review-v1'),
                                actor_reference='generated-test-actor')

    def test_old_layout_asset_selection_is_not_implicitly_requalified(self):
        self.assertEqual(VERSION, 'offmenu.ingredient-vocabulary-generation/2')
        self.assertEqual(HISTORICAL_PINS['public/off-photo-catalogue.js'][0],
                         'f7e0b953c0f3c6609f8d72597de576d050df90ec16a65e99df84c4b936707e8b')
        historical = dict(zip(HISTORICAL_PINS, self.assets.values()))
        with self.assertRaisesRegex(ValueError, 'exact three selected assets required'):
            self.generate(assets=historical)

    def test_real_three_asset_pins_and_bounded_populated_counts(self):
        result = self.generate()
        counts = result['curation']['counts']
        self.assertEqual(counts['foundAssets'], 3)
        self.assertEqual(counts['ingredientConceptCandidates'], 12)
        self.assertEqual(counts['nutrientDefinitionCandidates'], 8)
        self.assertGreater(counts['selectedLexicalObservations'], 60)
        self.assertLessEqual(counts['selectedLexicalObservations'], 128)
        self.assertLessEqual(counts['normalizedCandidateResources'], 64)
        self.assertLessEqual(len(result['common']['relations']), 256)
        self.assertLess(len(canonical(result)), 16 * 1024 * 1024)
        self.assertEqual(counts['rootAdmitted'], 0)

    def test_wrong_missing_oversize_asset_or_contract_refused(self):
        for assets in [{}, {**self.assets, ALIAS: self.assets[ALIAS] + b' '},
                       {**self.assets, AFCD: b' ' * 131073}]:
            with self.assertRaises(ValueError):
                self.generate(assets=assets)
        with self.assertRaises(ValueError):
            self.generate(contract=self.contract + b' ')

    def test_source_alias_to_typed_english_family_real_join_retains_und(self):
        result = self.generate()
        joined = inspect_generation(result, alias='lait')
        self.assertEqual(len(joined['sourceAliases']), 1)
        row = joined['sourceAliases'][0]
        self.assertEqual(row['pointer'], '/milk/1')
        self.assertEqual(row['sourceSHA256'], PINS[ALIAS][0])
        self.assertEqual(row['language'], 'und')
        self.assertEqual(joined['concepts'][0]['type'], 'FoodConcept')
        self.assertIn('Milk family', joined['concepts'][0]['preferredEnglish'])
        self.assertFalse(joined['actualProductFit'])
        self.assertIn('proposed', row['mappingState'])

    def test_milk_cow_coconut_and_cooked_rice_not_flattened(self):
        result = self.generate()
        ids = {row['id'] for row in result['curation']['concepts'] if row['id'].split(':')[-1] in ['i03', 'i04', 'i07', 'i08', 'i11']}
        self.assertEqual(len(ids), 5)
        cow = inspect_generation(result, alias='cow milk')
        self.assertIn('i08', cow['concepts'][0]['id'])
        self.assertEqual(len(cow['familyRelations']), 1)
        self.assertIn('i07', cow['familyRelations'][0]['objectId'])
        self.assertTrue(any('whole/low-fat' in item for item in result['curation']['unpopulatedRequirements']))
        self.assertFalse(any(r['predicateId'].endswith('exactMatch') for r in result['common']['relations']))

    def test_scientific_definition_row_cells_method_unit_and_basis_preserved(self):
        result = self.generate()
        identifier = 'urn:offmenu:vocabulary:nutrient-definition:afcd-r3-proximates-row-6'
        joined = inspect_generation(result, definition_id=identifier)
        row = joined['definitions'][0]
        actual = json.loads(self.assets[AFCD])['definitions']['Proximates'][6]
        self.assertEqual(row['row'], actual)
        self.assertEqual(row['cells'][8]['pointer'], '/definitions/Proximates/6/8')
        self.assertEqual(row['unitId'], 'urn:offmenu:unit:g')
        self.assertEqual(row['basisScope'], 'reporting limit only')
        self.assertFalse(row['foodMeasurement'])
        self.assertNotEqual(result['curation']['definitions'][0]['conceptId'], result['curation']['definitions'][1]['conceptId'])
        self.assertIn('countryNotice', result['curation']['afcdNotices'])

    def test_publisher_metadata_not_brand_manufacturer_composition_or_image_access(self):
        result = self.generate()
        self.assertEqual(len(result['curation']['products']), 2)
        for row in result['curation']['products']:
            self.assertIsNone(row['brand'])
            self.assertIsNone(row['manufacturer'])
            self.assertEqual(row['componentIngredientIds'], [])
            self.assertEqual(row['mappingState'], 'unknown')
            self.assertFalse(row['imageBytesRead'])
            self.assertEqual(row['retainedSnapshotMembership'], 'unverified')
            self.assertTrue(row['sourceCode'].isdigit())

    def test_deterministic_versioned_outputs_stable_ids_and_no_model_cache_claim(self):
        one, two = self.generate(), self.generate(version='review-v2')
        self.assertEqual(one['common'], two['common'])
        self.assertEqual(one['curation']['interpretationKey'], two['curation']['interpretationKey'])
        self.assertEqual(one['curation']['externalModelCalls'], 0)
        self.assertEqual(one['curation']['modelVersion'], 'UNAVAILABLE')
        self.assertFalse(one['curation']['portableExactModelCacheQualified'])
        self.assertEqual(self.generate(), one)

    def test_packet_reference_closure_uses_existing_common_shape(self):
        result = self.generate()
        packet = result['common']
        self.assertEqual(set(packet), {'schemaVersion', 'resources', 'assertions', 'relations', 'citations', 'translations'})
        resources = {r['id'] for r in packet['resources']}
        citations = {r['id'] for r in packet['citations']}
        texts = {t['id'] for r in packet['resources'] for t in r['names']}
        for row in packet['relations']:
            self.assertIn(row['subjectId'], resources)
            self.assertIn(row['objectId'], resources)
            self.assertLessEqual(set(row['citationIds']), citations)
        for row in packet['translations']:
            self.assertIn(row['textId'], texts)
            self.assertLessEqual(set(row['terminologyResourceIds']), resources)
        self.assertEqual(len(resources), len(packet['resources']))

    def test_explicit_incremental_revision_is_unactivated_and_preserves_old(self):
        result = self.generate()
        before = deepcopy(result)
        decision = {'decisionId': 'review-correction-1', 'action': 'split',
                    'sourceIds': ['urn:offmenu:vocabulary:ingredient:i07'],
                    'reason': 'Future source may identify distinct fat-level variants',
                    'evidenceReference': 'pending-selected-source'}
        revision = propose_revision(result, version='review-v2', decisions=[decision])
        self.assertTrue(revision['requiresIndependentReviewAnd00Adoption'])
        self.assertEqual(revision['decisions'][0]['state'], 'review-candidate-not-activated')
        self.assertEqual(result, before)
        with self.assertRaises(ValueError):
            propose_revision(result, version='review-v1', decisions=[])
        with self.assertRaises(ValueError):
            propose_revision(result, version='review-v2', decisions=[{**decision, 'sourceIds': ['unknown']}])

    def test_exclusive_owned_persistence_and_inspection_tamper_guard(self):
        result = self.generate()
        with tempfile.TemporaryDirectory() as root:
            directory = Path(root) / 'new-generation'
            manifest = persist_new_generation(directory, result)
            raw = (directory / 'generation.json').read_bytes()
            self.assertEqual(sha256(raw).hexdigest(), manifest['generationSHA256'])
            persisted = json.loads(raw)
            self.assertEqual(len(inspect_generation(persisted, alias='riz cuit')['sourceAliases']), 1)
            with self.assertRaises(FileExistsError):
                persist_new_generation(directory, result)
        changed = deepcopy(result)
        changed['common']['resources'][0]['names'][0]['value'] = 'changed'
        with self.assertRaises(ValueError):
            inspect_generation(changed, alias='lait')


if __name__ == '__main__':
    unittest.main()
