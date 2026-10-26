"""Pure projection of already closed, reviewed whole-family hook results.

No engine evaluation, source acquisition, SQLite access or admission occurs here.
The caller must qualify the exact hook, native identity, dual barcode evidence,
stage wire and permitted operation against the retained source before use.
"""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import re

SUBJECT = ('sourceId', 'releaseId', 'recordId', 'sourceObservationSha256',
           'sourceDocumentSha256', 'inputDatabaseSha256', 'sourceQualificationSha256')
AXES = ('baseMaterial', 'milkBase', 'fatClass', 'sugarStatus', 'saltStatus',
        'lactoseStatus', 'processing', 'form', 'flavour', 'scent', 'colour',
        'material', 'size', 'netAmount', 'packageCount', 'concentration',
        'strength', 'dimensions', 'capacity', 'compatibility', 'finish',
        'grade', 'originVariant', 'otherQualifiedVariant')
CONTRACT = 'offmenu-barcode-foundation-phase/2'


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True,
                      separators=(',', ':'), allow_nan=False).encode()


def require(ok, reason):
    if not ok:
        raise ValueError('WHOLE_FAMILY_PHASE:' + reason)


def sha(value):
    return isinstance(value, str) and re.fullmatch('[a-f0-9]{64}', value) is not None


def text(value):
    return (isinstance(value, str) and 0 < len(value) <= 512 and
            not re.search(r'[\x00-\x1f\x7f]', value))


def same_subject(a, b):
    return (isinstance(a, dict) and isinstance(b, dict) and
            all(text(a.get(k)) and a[k] == b.get(k) for k in SUBJECT) and
            all(sha(a[k]) for k in SUBJECT[3:]))


def gtin(value):
    if not isinstance(value, str) or re.fullmatch(r'(?:[0-9]{8}|[0-9]{12}|[0-9]{13}|[0-9]{14})', value) is None:
        return False
    total = sum(int(c) * (3 if i % 2 == 0 else 1)
                for i, c in enumerate(reversed(value[:-1])))
    return (10 - total % 10) % 10 == int(value[-1])


def pinned(ref):
    require(isinstance(ref, dict) and sha(ref.get('sha256')), 'pin')
    raw = Path(ref['path']).read_bytes()
    require(hashlib.sha256(raw).hexdigest() == ref['sha256'], 'pin-mismatch')
    return raw


class WholeFamilyPhaseAdapter:
    def __init__(self, accepted_input_path, accepted_input_sha256):
        self.input_ref = {'path': str(accepted_input_path), 'sha256': accepted_input_sha256}
        entry = json.loads(pinned(self.input_ref))
        require(entry.get('schema') == 'offmenu-accepted-coherent-whole-family-input/1', 'input-schema')
        # Snapshot all declared cut bytes before decoding; no executable imports.
        cut = entry['requiredCut']
        scope = entry.get('scope')
        require(isinstance(cut, dict) and isinstance(scope, dict), 'input-cut-scope')
        # Supported reviewed input layouts, not food-specific dispatch.
        layouts = [
            ('newFamilyRuleIds', 'qualifiedGateMandatoryForNewThreeFamilies', 3,
             'ACCEPTED_EXACT_SIXTEEN_CONDITIONAL_PRODUCT_TYPE_RELATIONS_AND_ONE_NEW_TYPE_DEFINITION_R8_R4_WITH_QUALIFIED_GATE_R3_ONLY'),
            ('newWholeFamilyRuleIds', 'qualifiedGateMandatoryForFiveWholeFamilies', 2,
             'ACCEPTED_EXACT_EIGHTEEN_CONDITIONAL_PRODUCT_TYPE_RELATIONS_AND_NO_NEW_TYPE_DEFINITIONS_R9_R2_WITH_QUALIFIED_GATE_ONLY')]
        selected = [layout for layout in layouts if layout[0] in scope and layout[1] in cut]
        require(len(selected) == 1 and
                sum(layout[0] in scope for layout in layouts) == 1 and
                sum(layout[1] in cut for layout in layouts) == 1, 'reviewed-input-layout')
        rule_key, self.gate_key, expected_new_count, type_verdict = selected[0]
        snapshots = {key: pinned(value) for key, value in cut.items()}
        rules_receipt = json.loads(snapshots['realAcceptedRuleReceipt'])
        types_receipt = json.loads(snapshots['separateAcceptedTypeReceipt'])
        registry = json.loads(snapshots['registry'])
        require(rules_receipt.get('schema') == 'offmenu-independent-derived-context-rule-acceptance/1' and
                rules_receipt.get('verdict') == 'ACCEPTED_EXACT_DERIVED_PRODUCT_CONTEXT_RULES_SCOPE', 'rules-review')
        require(types_receipt.get('schema') == 'offmenu-reviewed-conditional-food-type-relations/1' and
                types_receipt.get('verdict') == type_verdict, 'types-review')
        require(rules_receipt['engineSha256'] == cut['engine']['sha256'] and
                rules_receipt['registrySha256'] == cut['registry']['sha256'] and
                types_receipt['sourceCandidate'] == cut['typeRelations'], 'review-cut')
        self.new_rules = frozenset(scope[rule_key])
        require(len(self.new_rules) == expected_new_count and self.new_rules <= set(rules_receipt['acceptedRuleIds']) and
                self.new_rules == set(rules_receipt['newlyAcceptedRuleIds']) and
                rules_receipt['newlyAcceptedVariantAssertionIds'] == [], 'new-rule-scope')
        self.cut = deepcopy(cut)
        self.rules = {r['ruleId']: deepcopy(r) for r in registry['rules'] if r['ruleId'] in self.new_rules}
        require(set(self.rules) == self.new_rules, 'registry-rules')
        self.relations = {}
        definitions = {}
        qualifications = {}
        accepted_types = {r['typeId']: r for r in types_receipt['acceptedTypeDefinitions']}
        for relation in types_receipt['acceptedConditionalRelations']:
            rule_id = relation['sourceRuleId']
            if rule_id not in self.new_rules:
                continue
            rule = self.rules[rule_id]
            target, scope = rule['target'], rule['sourceScope']
            pair = relation['requiredAcceptedPair']
            gate = relation['requiredQualifiedGate']
            require(rule_id not in self.relations and relation['sourceScope'] == scope and
                    target['entityKind'] == 'ingredient' and
                    target['conceptId'] == relation['baseConceptId'] and
                    target['canonicalEnglishKey'] == relation['canonicalEnglishBaseKey'] and
                    relation['relation'] == 'exact-matched-source-product-is-a-food-type', 'conditional-relation')
            require(pair['engineSha256'] == cut['engine']['sha256'] and
                    pair['registry'] == cut['registry'] and
                    pair['realAcceptedRuleReceipt'] == cut['realAcceptedRuleReceipt'] and
                    pair['requiredActualRuleStatus'] == 'accepted-classification' and
                    pair['requiredActualEntityKind'] == 'ingredient' and
                    gate['gate'] == cut[self.gate_key] and
                    rule_id in gate['forRuleIds'] and gate['requiredQualifiedState'] == 'passed' and
                    gate['bareEngineBypassAccepted'] is False and gate['callerIntegrationMustEnforce'] is True,
                    'mandatory-pair-gate')
            require(rule['variantAssertions'] == [] and rule['sourceAttributeClaims'] == [] and
                    relation['parameterDisposition'] == 'no-new-controlled-parameter-assertions', 'no-new-parameters')
            typed = accepted_types.get(relation['meaningfulTypeId'])
            require(typed is not None and typed['meaningfulTypeKey'] == relation['meaningfulTypeKey'] and
                    text(typed['canonicalEnglishTypeLabel']), 'accepted-type-definition')
            key = target['canonicalEnglishKey']
            require(key not in definitions, 'ambiguous-base-definition')
            type_relation = {'typeKey': typed['meaningfulTypeKey'],
                             'canonicalEnglishLabel': typed['canonicalEnglishTypeLabel'],
                             'conceptId': typed['typeId'],
                             'relationshipId': rule_id + ':matched-product-type',
                             'relationshipKind': 'is-a', 'subjectConceptId': target['conceptId'],
                             'registrySha256': cut['typeRelations']['sha256'],
                             'independentReviewSha256': cut['separateAcceptedTypeReceipt']['sha256']}
            definitions[key] = {'classification': 'ingredient', 'conceptId': target['conceptId'],
                                'canonicalEnglishLabel': target['canonicalEnglishLabel'],
                                'typeKey': typed['meaningfulTypeKey'], 'typeRelation': type_relation,
                                'parameters': {axis: {'kind': 'string'} for axis in AXES},
                                'allowedRuleIds': [rule_id]}
            qualified = {'releaseId': scope['releaseId'], 'qualificationSha256': scope['sourceQualificationSha256']}
            require(scope['sourceId'] not in qualifications or qualifications[scope['sourceId']] == qualified,
                    'mixed-source-cut')
            qualifications[scope['sourceId']] = qualified
            self.relations[rule_id] = deepcopy(relation)
        require(set(self.relations) == self.new_rules, 'all-new-relations')
        self.policy = {'schema': CONTRACT, 'registrySha256': cut['registry']['sha256'],
                       'independentReviewSha256': cut['realAcceptedRuleReceipt']['sha256'],
                       'sourceQualifications': qualifications, 'definitions': definitions,
                       'derivation': {'kind': 'closed-reviewed-whole-family-projection-policy',
                                      'acceptedInputSha256': accepted_input_sha256,
                                      'ruleReceiptSha256': cut['realAcceptedRuleReceipt']['sha256'],
                                      'typeReceiptSha256': cut['separateAcceptedTypeReceipt']['sha256'],
                                      'requiredQualifiedGateSha256': cut[self.gate_key]['sha256']}}
        self.policy_bytes = canonical(self.policy)
        self.policy_sha256 = hashlib.sha256(self.policy_bytes).hexdigest()

    def project(self, hook, identity):
        require(isinstance(hook, dict) and isinstance(identity, dict), 'input')
        binding = hook.get('sourceBinding')
        stage = hook.get('stageAssertionBinding')
        require(same_subject(binding, binding) and same_subject(binding, stage) and
                same_subject(binding, identity.get('sourceBinding')), 'source-subject')
        require(text(identity.get('nativeRecordId')) and text(identity.get('stageRecordId')) and
                sha(identity.get('stageRecordWireSha256')) and
                all(stage.get(k) == identity[k] for k in ('stageRecordId', 'stageRecordWireSha256')),
                'native-stage-identity')
        for view in (binding, stage, identity['sourceBinding']):
            for key in ('nativeRecordId', 'stageRecordId', 'stageRecordWireSha256'):
                require(key not in view or view[key] == identity[key], 'nested-identity-conflict')
        barcode = identity.get('barcode')
        require(gtin(barcode) and all(isinstance(identity.get(k), list) and barcode in identity[k]
                for k in ('exactSourceKeys', 'qualifiedGtinKeys')), 'exact-identifier')
        views = identity.get('identifierEvidenceByView', {})
        identifiers = views.get('sourceAdapterInput')
        require(isinstance(identifiers, list) and identifiers == views.get('originalFields') and
                any(isinstance(item, dict) and item.get('system') == 'barcode' and item.get('value') == barcode
                    for item in identifiers), 'dual-source-barcode-evidence')
        gate = hook.get('qualifiedWholeFamilyResolution', {})
        context = hook.get('wholeProductContextResolution', {})
        require(gate.get('schema') == 'offmenu-qualified-whole-family-resolution/1' and
                gate.get('qualification') == 'passed' and gate.get('status') == 'eligible-staged-resolution' and
                gate.get('reasons') == [] and not gate.get('suppressedCandidates') and
                gate.get('foundationQualified') is False and gate.get('engineResolution') == context,
                'qualified-gate-no-bypass')
        require(context.get('status') == 'accepted-classification' and context.get('entityKind') == 'ingredient' and
                context.get('classificationAccepted') is True and context.get('productTypeAccepted') is True and
                context.get('normalizationComplete') is False and hook.get('normalizationComplete') is False and
                context.get('mappingRevision') == self.cut['registry']['sha256'], 'actual-context')
        hits = [r for r in context.get('candidateTargets', [])
                if r.get('ruleId') in self.new_rules and r.get('semanticAccepted') is True]
        require(len(hits) == 1, 'one-exact-new-target')
        rule_id = hits[0]['ruleId']
        rule, relation = self.rules[rule_id], self.relations[rule_id]
        require(hits[0]['target'] == rule['target'] and all(binding.get(k) == v for k, v in rule['sourceScope'].items()) and
                all(context.get(k) == rule['target'][k] for k in
                    ('entityKind', 'conceptId', 'canonicalEnglishKey', 'canonicalEnglishLabel')), 'target-source')
        for hit in context['candidateTargets']:
            if hit.get('semanticAccepted') is True:
                require(all(hit.get('target', {}).get(k) == rule['target'][k] for k in
                            ('entityKind', 'conceptId', 'canonicalEnglishKey', 'canonicalEnglishLabel')),
                        'conflicting-whole-target')
        links = [r for r in hook.get('qualifiedWholeFamilyTypeRelations', [])
                 if r.get('relation', {}).get('sourceRuleId') == rule_id]
        require(len(links) == 1 and links[0].get('relation') == relation and
                links[0].get('acceptedTypeReceiptSha256') == self.cut['separateAcceptedTypeReceipt']['sha256'] and
                links[0].get('foundationQualified') is False and same_subject(links[0].get('sourceBinding'), binding) and
                links[0].get('stageAssertionBinding') == stage, 'exact-type-link')
        refs = [r for r in context.get('evidenceRefs', []) if r.get('ruleId') == rule_id]
        require(len(refs) == 1 and same_subject(refs[0].get('sourceBinding'), binding), 'exact-rule-evidence')
        fields = refs[0].get('fieldEvidence')
        require(isinstance(fields, list) and 1 <= len(fields) <= 32 and
                len({r.get('field') for r in fields}) == len(fields), 'field-evidence')
        require(set(rule['requiredContextFields']) <= {r.get('field') for r in fields}, 'required-whole-fields')
        evidence = []
        for item in fields:
            require(text(item.get('field')) and text(item.get('sourcePointer')) and sha(item.get('valueSha256')),
                    'field-commitment')
            if item['field'] in rule.get('sourceFieldPointers', {}):
                require(item['sourcePointer'] == rule['sourceFieldPointers'][item['field']], 'field-pointer')
            evidence.append({'kind': 'source-field', 'pointer': item['sourcePointer'],
                             'valueSha256': item['valueSha256'], 'ruleId': rule_id,
                             'sourceBinding': deepcopy(binding)})
        definition = self.policy['definitions'][rule['target']['canonicalEnglishKey']]
        stamp = {'state': 'reviewed', 'registrySha256': self.policy['registrySha256'],
                 'independentReviewSha256': self.policy['independentReviewSha256'], 'evidence': evidence}
        candidate = {'barcode': barcode, 'foundationPolicySha256': self.policy_sha256,
                     'identity': {'namespace': 'barcode', 'lexicalValue': barcode,
                                  **{k: deepcopy(identity[k]) for k in
                                     ('nativeRecordId', 'stageRecordId', 'stageRecordWireSha256', 'sourceBinding')}},
                     'classification': {**deepcopy(stamp), 'value': 'ingredient'},
                     'base': {**deepcopy(stamp), 'conceptId': definition['conceptId'],
                              'canonicalEnglishKey': rule['target']['canonicalEnglishKey'],
                              'canonicalEnglishLabel': definition['canonicalEnglishLabel'], 'typeKey': definition['typeKey']},
                     'type': {'state': 'reviewed', **deepcopy(definition['typeRelation']),
                              'evidence': [{'kind': 'reviewed-type-rule',
                                            'pointer': definition['typeRelation']['relationshipId'],
                                            'sourceBinding': deepcopy(binding)}]},
                     'parameters': {axis: {'state': 'unknown', 'reason': 'not-provided-in-qualified-representation',
                                           'evidence': [{'kind': 'qualified-representation-omission',
                                                         'pointer': '/parametersByAxis/' + axis,
                                                         'sourceBinding': deepcopy(binding)}]} for axis in AXES}}
        return {'schema': 'offmenu-closed-whole-family-phase-projection/1',
                'status': 'projected-review-required', 'candidate': candidate,
                'policySha256': self.policy_sha256, 'matchedRuleId': rule_id,
                'retainedContextVariantAssertions': deepcopy(context.get('variantAssertions', [])),
                'retainedSourceAttributeClaims': deepcopy(context.get('sourceAttributeClaims', [])),
                'originalHookSha256': hashlib.sha256(canonical(hook)).hexdigest(),
                'foundationQualified': False, 'normalizationComplete': False,
                'goldAdmitted': False, 'publicationAccepted': False,
                'requiresIndependentImplementationReview': True,
                'requiresActualSourceIdentityRightsReadback': True}
