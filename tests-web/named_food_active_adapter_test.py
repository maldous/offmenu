"""Generated contexts only; no retained corpus packet or native source reads."""
from copy import deepcopy
import hashlib
import importlib.util
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('active_named', ROOT / 'corpus/named_food_active_adapter.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
INPUT = Path('/home/user/src/offmenu-data/runtime/layout-migration/english-relationship-layer-20261026/accepted-named-food-active-policy-input-20261027/accepted-input.json')
INPUT_SHA = '8aad9e57b13389165f4dfae83251c8a981f1a883a1e1999941187d0aadd2dc35'


def generated(barcode='12178162'):
    binding = dict(sourceId='off', releaseId='2026-10-12', recordId='generated-' + barcode,
                   nativeRecordId='off:generated:' + barcode,
                   sourceObservationSha256='1' * 64, sourceDocumentSha256='2' * 64,
                   inputDatabaseSha256='3' * 64,
                   sourceQualificationSha256='96a192c8d7ec08e4116b9c7b1c8fb77da452a22820656fa43ceef1200c96cfc0')
    stage = {'stageRecordId': 'offmenu:generated:' + barcode, 'stageRecordWireSha256': '4' * 64}
    fields, secondary, originals = {}, {}, {}
    for role, suffix, state, value in [('name', 'name', 'present', 'Sliced Beetroot'),
                                      ('names', 'names', 'present', {'en': 'Sliced Beetroot'}),
                                      ('ingredientDeclaration', 'ingredientsText', 'null', None),
                                      ('categories', 'categories', 'empty', [])]:
        raw = module.canonical(value)
        fields[role] = {'state': state, 'originalValue': value, 'sourcePointer': '/data/' + suffix,
                        'valueSha256': hashlib.sha256(raw).hexdigest(), 'evidenceBytes': len(raw),
                        'evidenceEncoding': 'typed-exact-decimal-json/1; not an original byte-span hash'}
        secondary[role] = {'state': state, 'pointer': fields[role]['sourcePointer'],
                           'parsedValueEvidenceSha256': fields[role]['valueSha256'], 'evidenceBytes': len(raw)}
        originals[suffix] = value
    supplemental = {}
    for name in ('dataType', 'sourceCategoryFields'):
        fields[name] = {'state': 'not-projected', 'sourcePointer': '/data/' + name,
                        'originalValue': None, 'valueSha256': None, 'evidenceBytes': None,
                        'evidenceEncoding': None, 'originalSourceAbsenceEstablished': False,
                        'projectedValueCommitmentVerified': False}
        supplemental[name] = {'state': 'not-projected', 'pointer': '/data/' + name,
                              'originalSourceAbsenceEstablished': False}
    provenance = {**binding, 'visibility': 'source-staging'}
    originals['identifiers'] = [{'system': 'barcode', 'value': barcode}]
    inner = {'sourceBinding': {**binding, **stage}, 'identifiers': deepcopy(originals['identifiers']), 'sourceProductContext': {
        'schema': 'offmenu-source-product-context/1', 'sourceEvidence': {**binding, **stage},
        'fields': fields}, 'sourceTermAssertions': [],
        'fieldEvidence': {'name': secondary['name'], 'languages': {'names': secondary['names']},
                          'ingredientDeclaration': secondary['ingredientDeclaration'],
                          'categories': {'categories': secondary['categories'], **supplemental}}}
    record = {'sourceBinding': {**binding, **stage}, **stage, 'originalFields': originals,
              'evidenceSource': {'recordWireSha256': stage['stageRecordWireSha256']},
              'sourceProvenance': provenance, 'sourceAdapterInput': inner,
              'nativeRecordId': 'off:generated:' + barcode}
    identity = {**stage, 'sourceBinding': binding, 'barcode': barcode,
                'nativeRecordId': record['nativeRecordId'], 'exactSourceKeys': [barcode],
                'qualifiedGtinKeys': [barcode]}
    return record, identity


class ActivePolicyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.adapter = module.NamedFoodActiveAdapter(INPUT, INPUT_SHA)

    def test_generic_source_subjects_and_explicit_known_unknown_states(self):
        for barcode in ('12178162', '20026103'):
            record, identity = generated(barcode)
            original = deepcopy(record)
            out = self.adapter.project(record, identity)
            self.assertEqual(out['status'], 'projected-derived-food-policy-candidate')
            self.assertEqual(record, original)
            candidate = out['candidate']
            self.assertEqual(candidate['identity']['sourceBinding'], identity['sourceBinding'])
            self.assertEqual(candidate['type']['conceptId'], 'urn:offmenu:type:sliced-beetroot')
            self.assertEqual(candidate['parameters']['form']['evidenceKind'], 'source-name-declared')
            self.assertEqual(sum(v['state'] == 'unknown' for v in candidate['parameters'].values()), 23)
            self.assertFalse(out['matcherResult']['classificationAccepted'])
            self.assertFalse(out['foundationQualified'])
            self.assertNotEqual(candidate['classification']['independentReviewSha256'],
                                'f4a0068bf79cd93c5e198a3ae94cc1a0ef11d14c9843bdb1a47bfa00ae5e7efd')

    def test_barcode_does_not_override_name_or_richer_context(self):
        for change in ('name', 'composition', 'supplemental', 'outer-conflict'):
            record, identity = generated()
            fields = record['sourceAdapterInput']['sourceProductContext']['fields']
            if change == 'name':
                fields['name']['originalValue'] = 'Different food'
            elif change == 'composition':
                fields['ingredientDeclaration']['originalValue'] = 'Beetroot, vinegar'
            elif change == 'supplemental':
                fields['dataType']['originalValue'] = 'nonfood'
            else:
                record['originalFields']['categories'] = ['nonfood']
            self.assertIsNone(self.adapter.project(record, identity)['candidate'])

    def test_every_source_visibility_view_remains_guarded(self):
        for change in ('outer-private', 'inner-private', 'conflict'):
            record, identity = generated()
            if change == 'outer-private':
                record['sourceProvenance']['visibility'] = 'private'
            else:
                record['sourceAdapterInput']['sourceProvenance'] = {
                    'visibility': 'private' if change == 'inner-private' else 'public'}
            self.assertIsNone(self.adapter.project(record, identity)['candidate'])

    def test_identity_and_stage_readback_must_match(self):
        for field in ('recordId', 'stageRecordWireSha256', 'nativeRecordId', 'barcode'):
            record, identity = generated()
            if field == 'recordId':
                identity['sourceBinding'][field] = 'wrong'
            elif field == 'stageRecordWireSha256':
                identity[field] = '0' * 64
            else:
                identity[field] = 'wrong'
            with self.assertRaises(ValueError):
                self.adapter.project(record, identity)

    def test_context_binding_and_field_commitments_fail_closed(self):
        for change in ('binding', 'field'):
            record, identity = generated()
            if change == 'binding':
                record['sourceBinding']['recordId'] = 'wrong'
            else:
                record['sourceAdapterInput']['sourceProductContext']['fields']['name']['valueSha256'] = '0' * 64
            self.assertIsNone(self.adapter.project(record, identity)['candidate'])

    def test_native_barcode_and_wire_views_cannot_disagree(self):
        for change in ('native', 'barcode', 'wire'):
            record, identity = generated()
            if change == 'native':
                record['sourceAdapterInput']['sourceBinding']['nativeRecordId'] = 'wrong'
            elif change == 'barcode':
                record['originalFields']['identifiers'][0]['value'] = '20026103'
            else:
                record['evidenceSource']['recordWireSha256'] = '0' * 64
            try:
                out = self.adapter.project(record, identity)
            except ValueError:
                continue
            self.assertIsNone(out['candidate'])

    def test_missing_exact_barcode_evidence_and_wrong_input_pin_fail(self):
        record, identity = generated()
        identity['qualifiedGtinKeys'] = []
        with self.assertRaises(ValueError):
            self.adapter.project(record, identity)
        with self.assertRaises(ValueError):
            module.NamedFoodActiveAdapter(INPUT, '0' * 64)

    def test_standalone_node_fixture_equals_actual_generated_projection(self):
        fixture = json.loads((ROOT / 'tests-web/fixtures/named-food-active-generated.json').read_text())
        record, identity = generated()
        out = self.adapter.project(record, identity)
        self.assertEqual(fixture['candidate'], out['candidate'])
        self.assertEqual(fixture['policyJson'], self.adapter.policy_bytes.decode())
        self.assertEqual(fixture['matcherResult'], out['matcherResult'])

    def test_nested_stage_record_id_conflict_is_rejected(self):
        record, identity = generated()
        identity['sourceBinding']['stageRecordId'] = 'conflicting-nested-stage'
        with self.assertRaises(ValueError):
            self.adapter.project(record, identity)
        identity['sourceBinding']['stageRecordId'] = identity['stageRecordId']
        candidate = self.adapter.project(record, identity)['candidate']
        self.assertEqual(candidate['identity']['sourceBinding']['stageRecordId'], identity['stageRecordId'])

    def test_nested_stage_wire_conflict_is_rejected(self):
        record, identity = generated()
        identity['sourceBinding']['stageRecordWireSha256'] = '0' * 64
        with self.assertRaises(ValueError):
            self.adapter.project(record, identity)
        identity['sourceBinding']['stageRecordWireSha256'] = identity['stageRecordWireSha256']
        candidate = self.adapter.project(record, identity)['candidate']
        self.assertEqual(candidate['identity']['sourceBinding']['stageRecordWireSha256'], identity['stageRecordWireSha256'])


if __name__ == '__main__':
    unittest.main()
