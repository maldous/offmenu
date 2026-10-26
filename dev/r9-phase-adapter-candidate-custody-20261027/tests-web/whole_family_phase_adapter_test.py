"""Generated fixtures only; no operational corpus, source account or service."""
from copy import deepcopy
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('whole_family_phase', ROOT / 'corpus/whole_family_phase_adapter.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
H = lambda c: c * 64


class WholeFamilyProjectionTests(unittest.TestCase):
    FAMILY_COUNT = 3
    RULE_KEY = 'newFamilyRuleIds'
    GATE_KEY = 'qualifiedGateMandatoryForNewThreeFamilies'
    TYPE_VERDICT = 'ACCEPTED_EXACT_SIXTEEN_CONDITIONAL_PRODUCT_TYPE_RELATIONS_AND_ONE_NEW_TYPE_DEFINITION_R8_R4_WITH_QUALIFIED_GATE_R3_ONLY'

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.directory = Path(self.tmp.name)
        self.scope = {'sourceId': 'off', 'releaseId': 'generated', 'sourceQualificationSha256': H('4')}
        self.cut = {}

        def put(key, value):
            raw = module.canonical(value) if isinstance(value, dict) else value.encode()
            path = self.directory / (key + '.json')
            path.write_bytes(raw)
            self.cut[key] = {'path': str(path), 'sha256': hashlib.sha256(raw).hexdigest()}
            return self.cut[key]

        put('engine', 'generated-code-not-executed')
        put(self.GATE_KEY, 'generated-gate-not-executed')
        ids = ['generated:family:' + str(i) for i in range(self.FAMILY_COUNT)]
        self.rules = [{'ruleId': key, 'target': {'entityKind': 'ingredient',
                       'conceptId': 'generated:base:' + str(i), 'canonicalEnglishKey': 'base' + str(i),
                       'canonicalEnglishLabel': 'Generated food ' + str(i)},
                       'sourceScope': deepcopy(self.scope), 'variantAssertions': [], 'sourceAttributeClaims': [],
                       'requiredContextFields': ['name', 'names', 'categories'],
                       'sourceFieldPointers': {'name': '/data/name', 'names': '/data/names', 'categories': '/data/categories'}}
                      for i, key in enumerate(ids)]
        put('registry', {'rules': self.rules})
        put('typeRelations', {'generated': 'candidate type definitions'})
        put('realAcceptedRuleReceipt', {
            'schema': 'offmenu-independent-derived-context-rule-acceptance/1',
            'verdict': 'ACCEPTED_EXACT_DERIVED_PRODUCT_CONTEXT_RULES_SCOPE',
            'engineSha256': self.cut['engine']['sha256'], 'registrySha256': self.cut['registry']['sha256'],
            'acceptedRuleIds': ids, 'newlyAcceptedRuleIds': ids, 'newlyAcceptedVariantAssertionIds': []})
        self.relations = [{
            'sourceRuleId': key, 'sourceScope': deepcopy(self.scope),
            'baseConceptId': 'generated:base:' + str(i), 'canonicalEnglishBaseKey': 'base' + str(i),
            'meaningfulTypeId': 'generated:type:' + str(i), 'meaningfulTypeKey': 'generated-food-type' + str(i),
            'relation': 'exact-matched-source-product-is-a-food-type',
            'parameterDisposition': 'no-new-controlled-parameter-assertions',
            'requiredAcceptedPair': {'engineSha256': self.cut['engine']['sha256'],
                                    'registry': deepcopy(self.cut['registry']),
                                    'realAcceptedRuleReceipt': deepcopy(self.cut['realAcceptedRuleReceipt']),
                                    'requiredActualRuleStatus': 'accepted-classification',
                                    'requiredActualEntityKind': 'ingredient'},
            'requiredQualifiedGate': {'gate': deepcopy(self.cut[self.GATE_KEY]),
                                      'forRuleIds': ids, 'requiredQualifiedState': 'passed',
                                      'bareEngineBypassAccepted': False, 'callerIntegrationMustEnforce': True}}
            for i, key in enumerate(ids)]
        put('separateAcceptedTypeReceipt', {
            'schema': 'offmenu-reviewed-conditional-food-type-relations/1',
            'verdict': self.TYPE_VERDICT,
            'sourceCandidate': deepcopy(self.cut['typeRelations']),
            'acceptedTypeDefinitions': [{'typeId': 'generated:type:' + str(i),
                'meaningfulTypeKey': 'generated-food-type' + str(i),
                'canonicalEnglishTypeLabel': 'Generated type ' + str(i)} for i in range(self.FAMILY_COUNT)],
            'acceptedConditionalRelations': self.relations})
        entry = {'schema': 'offmenu-accepted-coherent-whole-family-input/1',
                 'requiredCut': self.cut, 'scope': {self.RULE_KEY: ids}}
        self.entry = self.directory / 'accepted-input.json'
        self.entry.write_bytes(module.canonical(entry))
        self.entry_sha = hashlib.sha256(self.entry.read_bytes()).hexdigest()
        self.adapter = module.WholeFamilyPhaseAdapter(self.entry, self.entry_sha)

    def fixture(self, index=0):
        binding = {**self.scope, 'recordId': 'generated-source-record',
                   'sourceObservationSha256': H('1'), 'sourceDocumentSha256': H('2'),
                   'inputDatabaseSha256': H('3')}
        stage = {**binding, 'stageRecordId': 'generated-stage', 'stageRecordWireSha256': H('5')}
        rule = self.rules[index]
        fields = [{'field': f, 'sourcePointer': '/data/' + f, 'valueSha256': H('6')}
                  for f in ['name', 'names', 'categories']]
        context = {'status': 'accepted-classification', 'entityKind': 'ingredient',
                   'classificationAccepted': True, 'productTypeAccepted': True, 'normalizationComplete': False,
                   'mappingRevision': self.cut['registry']['sha256'],
                   **{k: rule['target'][k] for k in ['conceptId', 'canonicalEnglishKey', 'canonicalEnglishLabel']},
                   'candidateTargets': [{'ruleId': rule['ruleId'], 'semanticAccepted': True, 'target': deepcopy(rule['target'])}],
                   'evidenceRefs': [{'ruleId': rule['ruleId'], 'sourceBinding': deepcopy(binding), 'fieldEvidence': fields}],
                   'variantAssertions': [{'generated': 'legacy assertion retained separately'}],
                   'sourceAttributeClaims': [{'generated': 'source claim retained separately'}]}
        hook = {'sourceBinding': binding, 'stageAssertionBinding': stage, 'normalizationComplete': False,
                'wholeProductContextResolution': context,
                'qualifiedWholeFamilyResolution': {'schema': 'offmenu-qualified-whole-family-resolution/1',
                    'status': 'eligible-staged-resolution', 'qualification': 'passed', 'reasons': [],
                    'foundationQualified': False, 'engineResolution': deepcopy(context)},
                'qualifiedWholeFamilyTypeRelations': [{'relation': deepcopy(self.relations[index]),
                    'acceptedTypeReceiptSha256': self.cut['separateAcceptedTypeReceipt']['sha256'],
                    'sourceBinding': deepcopy(binding), 'stageAssertionBinding': deepcopy(stage), 'foundationQualified': False}]}
        identity = {'barcode': '0036000291452', 'nativeRecordId': 'generated-native',
                    'stageRecordId': stage['stageRecordId'], 'stageRecordWireSha256': stage['stageRecordWireSha256'],
                    'sourceBinding': deepcopy(binding), 'exactSourceKeys': ['0036000291452'],
                    'qualifiedGtinKeys': ['0036000291452'],
                    'identifierEvidenceByView': {k: [{'system': 'barcode', 'value': '0036000291452'}]
                        for k in ['sourceAdapterInput', 'originalFields']}}
        return hook, identity

    def synchronize_gate(self, hook):
        hook['qualifiedWholeFamilyResolution']['engineResolution'] = deepcopy(hook['wholeProductContextResolution'])

    def test_generic_targets_keep_twenty_four_unknown_axes_and_sidecars(self):
        rows = []
        for i in range(self.FAMILY_COUNT):
            hook, identity = self.fixture(i)
            before = deepcopy((hook, identity))
            result = self.adapter.project(hook, identity)
            candidate = result['candidate']
            self.assertEqual(len(candidate['parameters']), 24)
            self.assertTrue(all(v['state'] == 'unknown' and 'value' not in v for v in candidate['parameters'].values()))
            self.assertEqual(result['retainedContextVariantAssertions'], hook['wholeProductContextResolution']['variantAssertions'])
            self.assertEqual(result['retainedSourceAttributeClaims'], hook['wholeProductContextResolution']['sourceAttributeClaims'])
            self.assertEqual((hook, identity), before)
            for name in ['foundationQualified', 'normalizationComplete', 'goldAdmitted', 'publicationAccepted']:
                self.assertIs(result[name], False)
            self.assertTrue(result['requiresActualSourceIdentityRightsReadback'])
            rows.append(candidate)
        # Verify interoperability with the unchanged production-independent v2 assessor.
        payload = {'policy': self.adapter.policy, 'candidates': rows}
        script = "import {assessFoundation} from './corpus/foundation-phase-contract-v2.mjs';import{readFileSync}from'node:fs';const x=JSON.parse(readFileSync(0,'utf8'));process.stdout.write(JSON.stringify(x.candidates.map(c=>assessFoundation(c,x.policy))));"
        run = subprocess.run(['node', '--input-type=module', '-e', script], input=json.dumps(payload),
                             text=True, cwd=ROOT, capture_output=True, check=True)
        assessments = json.loads(run.stdout)
        self.assertTrue(all(a['foundationComplete'] and len(a['parameters']['unknown']) == 24 and
                            not a['goldAdmitted'] and not a['publicationAccepted'] for a in assessments))

    def test_every_subject_key_native_and_stage_binding_must_agree(self):
        for key in module.SUBJECT:
            hook, identity = self.fixture()
            identity['sourceBinding'][key] = 'different'
            with self.subTest(key=key), self.assertRaises(ValueError):
                self.adapter.project(hook, identity)
        for key in ['nativeRecordId', 'stageRecordId', 'stageRecordWireSha256']:
            hook, identity = self.fixture()
            hook['stageAssertionBinding'][key] = 'conflict'
            with self.subTest(key=key), self.assertRaises(ValueError):
                self.adapter.project(hook, identity)
        hook, identity = self.fixture()
        del identity['nativeRecordId']
        with self.assertRaises(ValueError): self.adapter.project(hook, identity)

    def test_no_barcode_alias_checksum_or_dual_view_shortcuts(self):
        mutations = [lambda i: i.update(barcode='036000291452'),
                     lambda i: i.update(barcode='0036000291453'),
                     lambda i: i.update(qualifiedGtinKeys=[]),
                     lambda i: i['identifierEvidenceByView'].update(originalFields=[])]
        for mutate in mutations:
            hook, identity = self.fixture(); mutate(identity)
            with self.assertRaises(ValueError): self.adapter.project(hook, identity)

    def test_gate_failure_suppression_or_bare_context_cannot_project(self):
        mutations = [lambda h: h.pop('qualifiedWholeFamilyResolution'),
                     lambda h: h['qualifiedWholeFamilyResolution'].update(qualification='failed'),
                     lambda h: h['qualifiedWholeFamilyResolution'].update(status='whole-context-conflict-abstain'),
                     lambda h: h['qualifiedWholeFamilyResolution'].update(suppressedCandidates=[{'generated': 'conflict'}]),
                     lambda h: h['qualifiedWholeFamilyResolution'].update(engineResolution={}),
                     lambda h: h['qualifiedWholeFamilyResolution'].update(foundationQualified=True)]
        for mutate in mutations:
            hook, identity = self.fixture(); mutate(hook)
            with self.assertRaises(ValueError): self.adapter.project(hook, identity)

    def test_exact_rule_target_type_receipt_and_field_commitments_are_required(self):
        mutations = [lambda h: h['wholeProductContextResolution']['candidateTargets'][0].update(semanticAccepted=False),
                     lambda h: h['wholeProductContextResolution']['candidateTargets'][0]['target'].update(conceptId='other'),
                     lambda h: h['qualifiedWholeFamilyTypeRelations'][0].update(acceptedTypeReceiptSha256=H('f')),
                     lambda h: h['qualifiedWholeFamilyTypeRelations'][0]['stageAssertionBinding'].update(stageRecordId='other'),
                     lambda h: h['wholeProductContextResolution']['evidenceRefs'][0]['fieldEvidence'][0].update(valueSha256='not-a-hash'),
                     lambda h: h['wholeProductContextResolution']['evidenceRefs'][0]['fieldEvidence'][0].update(sourcePointer='/other/name'),
                     lambda h: h['wholeProductContextResolution']['evidenceRefs'][0]['fieldEvidence'].pop()]
        for mutate in mutations:
            hook, identity = self.fixture(); mutate(hook); self.synchronize_gate(hook)
            with self.assertRaises(ValueError): self.adapter.project(hook, identity)
        hook, identity = self.fixture()
        other = deepcopy(hook['wholeProductContextResolution']['candidateTargets'][0])
        other['ruleId'] = 'generated:legacy'; other['target']['conceptId'] = 'generated:conflict'
        hook['wholeProductContextResolution']['candidateTargets'].append(other); self.synchronize_gate(hook)
        with self.assertRaises(ValueError): self.adapter.project(hook, identity)

    def test_construction_pin_drift_fails_closed_and_instances_snapshot_verified_cut(self):
        hook, identity = self.fixture()
        Path(self.cut['registry']['path']).write_text('{}')
        self.assertEqual(self.adapter.project(hook, identity)['status'], 'projected-review-required')
        with self.assertRaises(ValueError):
            module.WholeFamilyPhaseAdapter(self.entry, self.entry_sha)


    def test_missing_or_aliased_input_layout_and_wrong_type_verdict_fail_closed(self):
        original = json.loads(self.entry.read_text())
        cases = []
        missing = deepcopy(original); missing['scope'].pop(self.RULE_KEY); cases.append(missing)
        aliased = deepcopy(original)
        other_rule = 'newWholeFamilyRuleIds' if self.RULE_KEY == 'newFamilyRuleIds' else 'newFamilyRuleIds'
        aliased['scope'][other_rule] = list(original['scope'][self.RULE_KEY]); cases.append(aliased)
        gate_alias = deepcopy(original)
        other_gate = 'qualifiedGateMandatoryForFiveWholeFamilies' if self.GATE_KEY == 'qualifiedGateMandatoryForNewThreeFamilies' else 'qualifiedGateMandatoryForNewThreeFamilies'
        gate_alias['requiredCut'][other_gate] = deepcopy(self.cut[self.GATE_KEY]); cases.append(gate_alias)
        for value in cases:
            self.entry.write_bytes(module.canonical(value))
            with self.assertRaises(ValueError):
                module.WholeFamilyPhaseAdapter(self.entry, hashlib.sha256(self.entry.read_bytes()).hexdigest())
        types = json.loads(Path(self.cut['separateAcceptedTypeReceipt']['path']).read_text())
        types['verdict'] = 'unsupported-review'
        raw = module.canonical(types)
        Path(self.cut['separateAcceptedTypeReceipt']['path']).write_bytes(raw)
        original['requiredCut']['separateAcceptedTypeReceipt']['sha256'] = hashlib.sha256(raw).hexdigest()
        self.entry.write_bytes(module.canonical(original))
        with self.assertRaises(ValueError):
            module.WholeFamilyPhaseAdapter(self.entry, hashlib.sha256(self.entry.read_bytes()).hexdigest())


class R9WholeFamilyProjectionTests(WholeFamilyProjectionTests):
    FAMILY_COUNT = 2
    RULE_KEY = 'newWholeFamilyRuleIds'
    GATE_KEY = 'qualifiedGateMandatoryForFiveWholeFamilies'
    TYPE_VERDICT = 'ACCEPTED_EXACT_EIGHTEEN_CONDITIONAL_PRODUCT_TYPE_RELATIONS_AND_NO_NEW_TYPE_DEFINITIONS_R9_R2_WITH_QUALIFIED_GATE_ONLY'



if __name__ == '__main__':
    unittest.main()
