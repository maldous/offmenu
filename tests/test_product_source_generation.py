"""Generated fixtures only: no real source asset, DB, source reader or runtime."""
from copy import deepcopy
import json
import math
import unittest
import tempfile
from pathlib import Path

import jsonschema
from offmenu.refresh import product_source_generation as adapter

PROTECTED = ('urn:offmenu:vocabulary:ingredient:i07', 'urn:offmenu:fixture:protected')


def fixture(record_id='fixture-product-a', name='Same source label'):
    return {'sourceId': 'synthetic-worker57', 'sourceVersion': 'fixture-v1',
        'sourceRecordId': record_id, 'assetSha256': 'a' * 64,
        'originalUrl': 'urn:offmenu:fixture:worker57', 'license': 'Synthetic fixture only',
        'attribution': 'Worker57 generated test fixture', 'sourcePath': '/products/' + record_id,
        'names': [{'value': name, 'language': 'en'}],
        'fields': {'categories': None, 'ingredientClassification': 'unknown',
                   'declared': {'original': 'Leche / milk', 'known': True}},
        'components': [{'text': 'milk', 'language': 'und',
                        'sourcePath': '/products/' + record_id + '/components/0'}],
        'crosswalks': []}


def build(rows, **kwargs):
    return adapter.build_product_generation(rows, generation_version='fixture-code-cut-0001',
        actor_reference='worker57-generated-fixtures', operation_reference='synthetic-fixture-only', protected_ids=PROTECTED, **kwargs)


class ProductGenerationTests(unittest.TestCase):
    def test_same_schema_and_no_first56_definitions(self):
        packet = build([fixture()])
        receipt, _, _, schema = adapter.load_shared_contract(protected_ids=PROTECTED)
        jsonschema.Draft202012Validator(schema).validate(packet['common'])
        defined = {x['id'] for kind in ['resources', 'citations', 'assertions', 'relations'] for x in packet['common'][kind]}
        self.assertFalse(defined.intersection(receipt['allGeneration1ObjectIdsExcludedFromMutation']))
        self.assertEqual(packet['common']['schemaVersion'], 'offmenu-common/1')

    def test_same_label_does_not_merge_source_identity(self):
        packet = build([fixture('a'), fixture('b')])
        products = [r for r in packet['common']['resources'] if ':product-observation:' in r['id']]
        self.assertEqual(len({r['id'] for r in products}), 2)
        self.assertTrue(all(r['type'].endswith(':SourceRecord') for r in products))

    def test_disjoint_candidate_namespace_is_not_accepted_vocabulary(self):
        packet = build([fixture()])
        self.assertTrue(all(r['id'].startswith('urn:offmenu:candidate:generation2:worker57:') for r in packet['common']['resources']))
        self.assertFalse(packet['curation']['accepted'])

    def test_language_and_original_text_preserved(self):
        row = fixture()
        row['names'] = [{'value': '牛乳 / lait', 'language': 'und'}]
        name = build([row])['common']['resources'][0]['names'][0]
        self.assertEqual((name['value'], name['language']), ('牛乳 / lait', 'und'))

    def test_blank_source_value_is_preserved_distinct_from_null(self):
        row = fixture()
        row['fields']['blank'] = ''
        packet = build([row])
        blank = next(a['value'] for a in packet['common']['assertions'] if a['propertyId'].endswith(':blank'))
        self.assertEqual((blank['kind'], blank['value']), ('text', ''))

    def test_null_and_missing_are_distinct_without_nonfood_inference(self):
        a, b = fixture('a'), fixture('b')
        del b['fields']['categories']
        packet = build([a, b])
        categories = [x for x in packet['common']['assertions'] if x['propertyId'].endswith(':categories')]
        self.assertEqual(len(categories), 1)
        self.assertEqual(categories[0]['value'], {'kind': 'null', 'value': None})
        self.assertTrue(all(x['state'] == 'ambiguous-unknown' for x in packet['curation']['categoryDispositions']))

    def test_component_is_only_candidate_part_of_source_record(self):
        packet = build([fixture()])
        relation = packet['common']['relations'][0]
        self.assertTrue(relation['predicateId'].endswith(':partOf'))
        self.assertEqual(relation['status'], 'candidate')
        self.assertEqual(packet['curation']['counts']['canonicalConceptsMinted'], 0)

    def test_no_input_canonical_class_or_fraction_shortcut(self):
        row = fixture()
        row['components'][0]['canonicalId'] = 'urn:offmenu:vocabulary:ingredient:i07'
        with self.assertRaises(ValueError):
            build([row])

    def test_reference_only_crosswalk_never_becomes_exact_match(self):
        row = fixture()
        target = 'urn:offmenu:vocabulary:ingredient:i07'
        row['crosswalks'] = [{'targetId': target, 'sourcePath': row['sourcePath'] + '/components/0', 'subjectSourcePath': row['sourcePath'] + '/components/0', 'reason': 'Synthetic proposal only'}]
        with self.assertRaises(ValueError):
            build([row])
        packet = build([row], reference_ids=[target])
        relations = [r for r in packet['common']['relations'] if r['objectId'] == target]
        self.assertEqual(relations[0]['predicateId'], 'urn:offmenu:relation:candidateMatch')
        self.assertEqual(relations[0]['status'], 'candidate')
        self.assertNotIn(target, {r['id'] for r in packet['common']['resources']})

    def test_conflicting_same_source_key_rejected(self):
        a, b = fixture(), fixture()
        b['fields']['categories'] = 'incompatible source payload at same key'
        with self.assertRaisesRegex(ValueError, 'conflicting repeated'):
            build([a, b])

    def test_duplicate_crosswalk_evidence_rejected(self):
        row = fixture()
        target = 'urn:offmenu:vocabulary:ingredient:i07'
        p = {'targetId': target, 'sourcePath': row['sourcePath'], 'subjectSourcePath': row['sourcePath'], 'reason': 'Fixture'}
        row['crosswalks'] = [p, deepcopy(p)]
        with self.assertRaisesRegex(ValueError, 'duplicate crosswalk'):
            build([row], reference_ids=[target])

    def test_readback_rejects_admission_flag_relabeling(self):
        packet = build([fixture()])
        packet['curation']['accepted'] = True
        with self.assertRaisesRegex(ValueError, 'admission'):
            adapter.inspect_product_generation(packet, protected_ids=PROTECTED)

    def test_exact_duplicate_is_counted_without_duplicate_objects(self):
        packet = build([fixture(), fixture()])
        self.assertEqual(packet['curation']['counts']['uniqueSourceRecords'], 1)
        self.assertEqual(packet['curation']['counts']['duplicateSourceRecords'], 1)

    def test_source_pointer_cannot_escape_selected_record(self):
        row = fixture()
        row['components'][0]['sourcePath'] = '/some-other-record/component'
        with self.assertRaisesRegex(ValueError, 'outside'):
            build([row])

    def test_bounds_and_nonfinite_values_rejected(self):
        with self.assertRaisesRegex(ValueError, 'record bound'):
            build([fixture(str(i)) for i in range(65)])
        row = fixture()
        row['fields']['value'] = math.nan
        with self.assertRaises(ValueError):
            build([row])

    def test_deterministic_and_input_immutable(self):
        row = fixture()
        original = deepcopy(row)
        self.assertEqual(build([row]), build([row]))
        self.assertEqual(row, original)

    def test_readback_detects_tampering_and_preserves_no_fit(self):
        packet = build([fixture()])
        result = adapter.inspect_product_generation(packet, 'fixture-product-a', protected_ids=PROTECTED)
        self.assertFalse(result['actualProductFit'])
        self.assertEqual(result['acceptedSemanticMappings'], 0)
        packet['common']['resources'][0]['names'][0]['value'] = 'changed'
        with self.assertRaisesRegex(ValueError, 'changed'):
            adapter.inspect_product_generation(packet, protected_ids=PROTECTED)

    def test_fixture_counts_are_not_real_data_or_gold(self):
        counts = build([fixture()])['curation']['counts']
        self.assertEqual((counts['syntheticFixtureRecords'], counts['realSourceRows'], counts['goldAdmitted']), (1, 0, 0))

    def test_output_name_cannot_target_shared_or_first_generation(self):
        with self.assertRaises(ValueError):
            adapter.persist_owned_candidate(str(Path.cwd()), '../worker56', build([fixture()]), protected_ids=PROTECTED)

    def test_f02_component_local_crosswalk_uses_component_not_product(self):
        row = fixture()
        pointer = row['sourcePath'] + '/components/0'
        target = PROTECTED[0]
        row['crosswalks'] = [{'targetId': target, 'sourcePath': pointer,
                              'subjectSourcePath': pointer, 'reason': 'Fixture component only'}]
        packet = build([row], reference_ids=[target])
        relation = next(r for r in packet['common']['relations'] if r['objectId'] == target)
        component = next(r for r in packet['common']['resources'] if ':component-observation:' in r['id'])
        product = next(r for r in packet['common']['resources'] if ':product-observation:' in r['id'])
        self.assertEqual(relation['subjectId'], component['id'])
        self.assertNotEqual(relation['subjectId'], product['id'])
        self.assertEqual(packet['curation']['proposedCrosswalks'][0]['sourceResourceId'], component['id'])
        self.assertEqual(packet['curation']['proposedCrosswalks'][0]['productResourceId'], product['id'])

    def test_f02_explicit_whole_product_proposal_is_distinct(self):
        row = fixture()
        target = PROTECTED[0]
        row['crosswalks'] = [{'targetId': target, 'sourcePath': row['sourcePath'],
                              'subjectSourcePath': row['sourcePath'], 'reason': 'Fixture whole record'}]
        packet = build([row], reference_ids=[target])
        product = next(r for r in packet['common']['resources'] if ':product-observation:' in r['id'])
        relation = next(r for r in packet['common']['relations'] if r['objectId'] == target)
        self.assertEqual(relation['subjectId'], product['id'])

    def test_f02_legacy_ambiguous_component_proposal_rejected(self):
        row = fixture()
        row['crosswalks'] = [{'targetId': PROTECTED[0], 'sourcePath': row['sourcePath'] + '/components/0',
                              'reason': 'No explicit subject supplied'}]
        with self.assertRaisesRegex(ValueError, 'subjectSourcePath'):
            build([row], reference_ids=[PROTECTED[0]])

    def test_f02_component_subject_cannot_borrow_other_occurrence_evidence(self):
        row = fixture()
        row['crosswalks'] = [{'targetId': PROTECTED[0], 'sourcePath': row['sourcePath'] + '/names/0',
                              'subjectSourcePath': row['sourcePath'] + '/components/0', 'reason': 'Wrong occurrence'}]
        with self.assertRaisesRegex(ValueError, 'outside selected subject'):
            build([row], reference_ids=[PROTECTED[0]])

    def test_f04_contract_and_protection_can_be_injected_without_runtime_tree(self):
        contract = (adapter.REPO_ROOT / 'contracts/corpus/common-data-contract.json').read_bytes()
        schema = (adapter.REPO_ROOT / 'contracts/corpus/common-data.schema.json').read_bytes()
        packet = build([fixture()], contract_raw=contract, schema_raw=schema)
        self.assertEqual(packet['curation']['sharedContractSha256'], adapter.CONTRACT_SHA)
        self.assertEqual(packet['curation']['protectedDefinitionCount'], len(PROTECTED))
        self.assertNotIn('allGeneration1ObjectIdsExcludedFromMutation', packet['curation'])

    def test_f04_changed_protection_snapshot_rejected(self):
        packet = build([fixture()])
        with self.assertRaisesRegex(ValueError, 'admission'):
            adapter.inspect_product_generation(packet, protected_ids=[])

    def test_f04_owned_persistence_is_portable_and_idempotent(self):
        packet = build([fixture()])
        with tempfile.TemporaryDirectory(prefix='worker57-portable-fixture-', dir=Path(__file__).resolve().parent) as temp:
            root = str(Path(temp).resolve())
            first = adapter.persist_owned_candidate(root, 'fixture-portable', packet, protected_ids=PROTECTED)
            second = adapter.persist_owned_candidate(root, 'fixture-portable', packet, protected_ids=PROTECTED)
            self.assertFalse(first['reusedIdenticalOwnedOutput'])
            self.assertTrue(second['reusedIdenticalOwnedOutput'])

    def test_f02_explicit_product_subject_cannot_relabel_component_evidence(self):
        row = fixture()
        row['crosswalks'] = [{'targetId': PROTECTED[0], 'sourcePath': row['sourcePath'] + '/components/0',
                              'subjectSourcePath': row['sourcePath'], 'reason': 'Incorrect part-to-whole'}]
        with self.assertRaisesRegex(ValueError, 'component-local evidence'):
            build([row], reference_ids=[PROTECTED[0]])


if __name__ == '__main__':
    unittest.main()
