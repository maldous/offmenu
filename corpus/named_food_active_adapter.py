"""Pure named-food projection; no source acquisition, serving or admission.

The caller pins the accepted input and separately qualifies actual identifier,
native-record, stage-wire and source-use evidence. The unchanged reviewed matcher
is run on the complete supplied context, never on a barcode membership list.
"""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import re
from types import ModuleType

SUBJECT = ('sourceId', 'releaseId', 'recordId', 'sourceObservationSha256',
           'sourceDocumentSha256', 'inputDatabaseSha256', 'sourceQualificationSha256')
CONTRACT = 'offmenu-barcode-foundation-phase/2'


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True,
                      separators=(',', ':'), allow_nan=False).encode()


def _require(ok, reason):
    if not ok:
        raise ValueError('NAMED_ACTIVE_POLICY:' + reason)


def _sha(value):
    return isinstance(value, str) and re.fullmatch('[a-f0-9]{64}', value) is not None


def _pinned(ref):
    _require(isinstance(ref, dict) and _sha(ref.get('sha256')), 'pin')
    body = Path(ref['path']).read_bytes()
    _require(hashlib.sha256(body).hexdigest() == ref['sha256'], 'pin-mismatch')
    return body


def _gtin(value):
    if not isinstance(value, str) or re.fullmatch(r'(?:[0-9]{8}|[0-9]{12}|[0-9]{13}|[0-9]{14})', value) is None:
        return False
    total = sum(int(c) * (3 if i % 2 == 0 else 1)
                for i, c in enumerate(reversed(value[:-1])))
    return (10 - total % 10) % 10 == int(value[-1])


class NamedFoodActiveAdapter:
    def __init__(self, accepted_input_path, accepted_input_sha256):
        self.input_ref = {'path': str(accepted_input_path), 'sha256': accepted_input_sha256}
        entry = json.loads(_pinned(self.input_ref))
        _require(entry.get('schema') == 'offmenu-accepted-named-food-active-policy-input/1', 'input-schema')
        refs = entry['receiptPins']
        docs = [(ref, _pinned(ref)) for ref in refs]
        policies = [(ref, json.loads(body)) for ref, body in docs
                    if body.lstrip().startswith(b'{') and
                    json.loads(body).get('schema') == 'offmenu-reviewed-named-food-active-declarative-policy/1']
        _require(len(policies) == 1, 'one-reviewed-declarative-policy')
        self.policy_ref, self.accepted = policies[0]
        accepted = self.accepted
        _require(accepted.get('verdict') == 'ACCEPTED_EXACT_DERIVED_FOOD_USE_BASE_PRODUCT_TYPE_FORM_DECLARATIVE_POLICY_SCOPE', 'semantic-review')
        _require(accepted.get('candidateMatcherAdmissionFlagsRemainFalse') is True and
                 accepted.get('actualProductAcceptance') is False and
                 accepted.get('publication') is False, 'policy-boundary')
        by_sha = {ref['sha256']: body for ref, body in docs}
        _require(accepted['sourcePolicy']['sha256'] in by_sha, 'source-policy-pin')
        receipt_ref = accepted['candidateMatcherReceipt']
        _require(receipt_ref['sha256'] in by_sha, 'matcher-receipt-pin')
        receipt = json.loads(by_sha[receipt_ref['sha256']])
        _require(receipt.get('schema') == 'offmenu-reviewed-named-context-candidate-matcher/1' and
                 receipt.get('verdict') == 'ACCEPTED_EXACT_NAMED_CONTEXT_CANDIDATE_MATCHER_SCOPE_ONLY', 'matcher-review')
        _require(receipt['candidateCode']['sha256'] in by_sha and
                 receipt['rule']['sha256'] in by_sha, 'matcher-pair-pins')
        self.rule = json.loads(by_sha[receipt['rule']['sha256']])
        _require(all(accepted['sourceScope'].get(k) == v for k, v in receipt['sourceScope'].items()) and
                 self.rule['sourceScope'] == receipt['sourceScope'] and
                 receipt['requiredContext'] == self.rule['requiredContext'], 'source-context-agreement')
        # Execute the verified bytes, rather than reopening a mutable code path
        # after checking it. __file__ retains the reviewed module's path context.
        module = ModuleType('offmenu_reviewed_named_matcher')
        module.__file__ = receipt['candidateCode']['path']
        exec(compile(by_sha[receipt['candidateCode']['sha256']], module.__file__, 'exec'), module.__dict__)
        self.matcher = module.NamedContextCandidate(receipt['rule']['path'], receipt['rule']['sha256'])
        self.receipt = receipt
        assertions = accepted['acceptedCanonicalAssertions']
        meanings = receipt['acceptedCandidateOutputMeanings']
        form = accepted['controlledFormRepresentation']
        _require(assertions['base'] == meanings['namedCulinaryBase'], 'base-agreement')
        typed = assertions['meaningfulProductType']
        _require(all(typed[k] == meanings['productType'][k]
                     for k in ('typeId', 'canonicalEnglishKey', 'canonicalEnglishLabel')) and
                 typed['typeId'] == entry['selectedCanonicalTypeId'] == accepted['selectedCanonicalTypeId'], 'type-agreement')
        _require(form['state'] == 'known' and all(form[k] == meanings['sourceNameForm'][k]
                 for k in ('typeKey', 'value', 'evidenceRole')), 'form-agreement')
        axes = accepted['otherControlledAxes']['axes']
        _require(len(axes) == 23 and len(set(axes)) == 23 and form['typeKey'] not in axes and
                 accepted['otherControlledAxes']['state'] == 'unknown', 'controlled-axes')
        _require(assertions['entityKind'] == 'ingredient' and
                 accepted['acceptedEligibilityAssertion']['proposedState'] == 'eligible-derived-curator-assertion', 'food-use')
        registry = accepted['sourcePolicy']['sha256']
        review = self.policy_ref['sha256']
        relation = {'typeKey': typed['canonicalEnglishKey'],
                    'canonicalEnglishLabel': typed['canonicalEnglishLabel'],
                    'conceptId': typed['typeId'],
                    'relationshipId': self.rule['ruleId'] + ':matched-product-type',
                    'relationshipKind': 'is-a',
                    'subjectConceptId': assertions['base']['conceptId'],
                    'registrySha256': registry, 'independentReviewSha256': review,
                    'associationScope': 'actual-product-matched-by-exact-reviewed-context-only'}
        parameters = {axis: {'kind': 'string'} for axis in axes}
        parameters[form['typeKey']] = {'kind': 'string', 'values': [form['value']]}
        scope = accepted['sourceScope']
        self.policy = {'schema': CONTRACT, 'registrySha256': registry,
                       'independentReviewSha256': review,
                       'sourceQualifications': {scope['sourceId']: {
                           'releaseId': scope['releaseId'],
                           'qualificationSha256': scope['sourceQualificationSha256']}},
                       'definitions': {assertions['base']['canonicalEnglishKey']: {
                           **deepcopy(assertions['base']), 'classification': assertions['entityKind'],
                           'typeKey': typed['canonicalEnglishKey'], 'typeRelation': relation,
                           'parameters': parameters}},
                       'derivation': {'acceptedInputSha256': accepted_input_sha256,
                                      'matcherSha256': receipt['candidateCode']['sha256'],
                                      'ruleSha256': receipt['rule']['sha256'],
                                      'semanticReviewSha256': review,
                                      'kind': 'source-bound-derived-curator-policy'}}
        self.policy_bytes = canonical(self.policy)
        self.policy_sha256 = hashlib.sha256(self.policy_bytes).hexdigest()

    def project(self, record, identity):
        # Never trust caller-supplied matcher statuses or delete richer fields.
        result = self.matcher.evaluate(deepcopy(record))
        out = {'schema': 'offmenu-named-food-active-projection/1',
               'matcherResult': result, 'status': 'unresolved',
               'candidate': None, 'foundationQualified': False,
               'normalizationComplete': False, 'goldAdmitted': False,
               'publicationAccepted': False, 'requiresIndependentImplementationReview': True,
               'requiresActualSourceIdentityRightsReadback': True}
        if result['status'] != 'matched-unreviewed-named-meanings':
            return out
        _require(all(result[k] is False for k in self.receipt['requiredAdmissionFlags']), 'matcher-flags')
        _require(result['candidateMeanings'] == self.receipt['acceptedCandidateOutputMeanings'], 'matcher-meanings')
        evidence = result['evidenceRefs']
        _require(len(evidence) == 1, 'evidence-count')
        source = evidence[0]['sourceBinding']
        _require(isinstance(identity, dict) and isinstance(identity.get('sourceBinding'), dict) and
                 all(identity['sourceBinding'].get(k) == source[k] for k in SUBJECT), 'source-identity')
        outer = record.get('sourceBinding', {})
        inner = record.get('sourceAdapterInput', {}).get('sourceBinding', {})
        native = identity.get('nativeRecordId')
        _require(all(view.get('nativeRecordId') == native for view in
                     (outer, inner, identity['sourceBinding'])), 'native-source-binding')
        for k in ('stageRecordId', 'stageRecordWireSha256'):
            _require(identity.get(k) == evidence[0].get(k) and isinstance(identity.get(k), str) and
                     len(identity[k]) > 0, 'stage-identity')
        _require(outer.get('stageRecordId') == record.get('stageRecordId') == identity['stageRecordId'] and
                 outer.get('stageRecordWireSha256') ==
                 record.get('evidenceSource', {}).get('recordWireSha256') == identity['stageRecordWireSha256'], 'stage-wire-readback')
        _require(_sha(identity['stageRecordWireSha256']) and
                 isinstance(identity.get('nativeRecordId'), str) and 0 < len(identity['nativeRecordId']) <= 512 and
                 _gtin(identity.get('barcode')), 'exact-identifier')
        barcode = identity['barcode']
        identifiers = record.get('sourceAdapterInput', {}).get('identifiers')
        _require(isinstance(identifiers, list) and identifiers == record.get('originalFields', {}).get('identifiers') and
                 any(isinstance(item, dict) and item.get('system') == 'barcode' and
                     item.get('value') == barcode for item in identifiers), 'dual-source-barcode-evidence')
        _require(isinstance(identity.get('exactSourceKeys'), list) and
                 isinstance(identity.get('qualifiedGtinKeys'), list) and
                 barcode in identity['exactSourceKeys'] and barcode in identity['qualifiedGtinKeys'], 'qualified-source-identifier')
        # Barcode/native identity evidence is supplied by the closed-source owner,
        # not inferred by the semantic matcher. Caller must verify it to source.
        for view in (record, record.get('sourceAdapterInput', {})):
            if 'nativeRecordId' in view:
                _require(view['nativeRecordId'] == identity['nativeRecordId'], 'native-identity-conflict')
        refs = [{'kind': 'source-field', 'pointer': field['sourcePointer'],
                 'valueSha256': field['valueSha256'], 'sourceBinding': deepcopy(source),
                 'ruleId': self.rule['ruleId']}
                for field in evidence[0]['fieldEvidence'].values()]
        assertions = self.accepted['acceptedCanonicalAssertions']
        definition = self.policy['definitions'][assertions['base']['canonicalEnglishKey']]
        stamp = {'state': 'reviewed', 'registrySha256': self.policy['registrySha256'],
                 'independentReviewSha256': self.policy['independentReviewSha256'], 'evidence': refs}
        form = self.accepted['controlledFormRepresentation']
        field = evidence[0]['fieldEvidence'][form['evidenceRole']]
        parameters = {axis: {'state': 'unknown', 'reason': 'not-provided-in-qualified-representation',
                             'evidence': [{'kind': 'qualified-representation-omission',
                                           'pointer': '/parametersByAxis/' + axis,
                                           'sourceBinding': deepcopy(source)}]}
                      for axis in self.accepted['otherControlledAxes']['axes']}
        parameters[form['typeKey']] = {
            'state': 'known', 'value': form['value'], 'qualifier': form['qualifier'],
            'evidenceKind': 'source-name-declared',
            'independentReviewSha256': self.policy['independentReviewSha256'],
            'evidence': [{'kind': 'source-field', 'pointer': field['sourcePointer'],
                          'valueSha256': field['valueSha256'], 'sourceBinding': deepcopy(source)}]}
        candidate = {'barcode': barcode, 'foundationPolicySha256': self.policy_sha256,
                     'identity': {'namespace': 'barcode', 'lexicalValue': barcode,
                                  **{k: deepcopy(identity[k]) for k in
                                     ('nativeRecordId', 'stageRecordId', 'stageRecordWireSha256', 'sourceBinding')}},
                     'classification': {**deepcopy(stamp), 'value': assertions['entityKind']},
                     'base': {**deepcopy(stamp), **deepcopy(assertions['base']), 'typeKey': definition['typeKey']},
                     'type': {'state': 'reviewed', **deepcopy(definition['typeRelation']),
                              'evidence': [{'kind': 'reviewed-type-rule',
                                            'pointer': definition['typeRelation']['relationshipId'],
                                            'sourceBinding': deepcopy(source)}]},
                     'parameters': parameters}
        out.update(status='projected-derived-food-policy-candidate', candidate=candidate,
                   policySha256=self.policy_sha256)
        return out
