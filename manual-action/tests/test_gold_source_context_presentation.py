"""Generated-only tests. No retained corpus, database, native helpers or I/O."""
import copy
import hashlib
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from gold_source_context_presentation import (
    MAX_HOLD_REASON_BYTES, MAX_INPUT_BYTES, MAX_INSTRUCTIONS, MAX_JSON_NODES, MAX_OUTPUT_BYTES,
    SourceContextPresentationError, build_source_context_presentation,
)


def encoded(x):
    return json.dumps(x, sort_keys=True, ensure_ascii=False, separators=(',', ':')).encode()


def sha(x):
    return hashlib.sha256(encoded(x)).hexdigest()


def fixture(*, contexts=1, caution=True, actions=3, provenance_extra=0):
    """Genuine-shaped generated DTO, never a real admission/qualification receipt."""
    eid, oid = sha('entity'), sha('occurrence')
    rid, run = 'generated:recipe:revision:7', 'recipe-actions:' + sha('run')
    cid = 'generated:citation:7'
    provenance = {'sourceId': 'generated', 'recordId': '7', 'revisionId': 7,
        'url': 'https://example.test/recipe', 'historyUrl': 'https://example.test/history',
        'licenseUrl': 'https://example.test/license', 'license': 'Generated test licence',
        'attribution': 'Generated fixture authors', 'sourceDate': '2000-01-01',
        'visibility': 'public', 'changes': 'Generated fixture only'}
    if provenance_extra:
        provenance['historicalExtra'] = 'z' * provenance_extra
    citation = {'id': cid, 'sourceId': 'generated', 'originalRecordId': '7',
        'revisionId': 7, 'originalUrl': provenance['url'], 'historyUrl': provenance['historyUrl'],
        'rightsEvidenceUrl': provenance['licenseUrl'], 'license': provenance['license'],
        'attribution': provenance['attribution'], 'sourceDate': provenance['sourceDate'],
        'scope': {'visibility': 'public'}}
    notes = ['Full source café 😀 branch ' + str(i) for i in range(contexts)]
    if caution:
        notes.append('* Full source warning; even the final clause stays.')
    original = {'data': {'notes': notes}, 'provenance': provenance}
    native_actions, records = [], []
    for i in range(actions):
        aid = 'generated:action:' + str(i)
        text = 'Generated source action ' + str(i) + '.'
        evidence = [{'pointer': '/steps/' + str(i) + '/raw_text', 'start': 0,
                     'end': len(text), 'text': text, 'offset_unit': 'unicode_codepoint'}]
        unknowns = ['source tool choice unknown']
        instance = {'instance_id': aid, 'template_id': 'generated:template:' + str(i),
                    'unknown_parameters': unknowns}
        action = {'run_id': run, 'action_id': aid, 'template_id': instance['template_id'],
                  'source_order': i, 'sequence_index': i, 'original_text': text,
                  'english_text': text, 'unknown_parameters_json': encoded(unknowns).decode(),
                  'evidence_json': encoded(evidence).decode(),
                  'native_instance_json': encoded(instance).decode()}
        native_actions.append(action)
        records.append({'status': 'qualified', 'holdReasons': [], 'actionRecord': action,
                        'evidence': evidence, 'citations': [citation], 'supportEvidence': [evidence],
                        'supportRecords': [{'run_id': run, 'action_id': aid,
                                            'citation_id': cid, 'evidence_json': encoded(evidence).decode()}]})
    binding = {'runId': run, 'recipeEntityId': eid, 'sourceOccurrenceId': oid}
    source_pin = {'path': 'generated-fixture-only/source.json', 'sha256': sha('source-file')}
    def hold(payload):
        return {'target_kind': 'recipe-run', 'target_id': run, 'reason': encoded(payload).decode()}
    holds = [{'target_kind': 'resource', 'target_id': rid, 'reason': 'Unknown yield and safety remain held.'}]
    if contexts:
        payload = {'documentKind': 'attributed-source-context-companion',
                   'boundNativeRun': binding, 'sourceOriginal': source_pin,
                   'provenance': provenance, 'sourceContexts': []}
        for i, text in enumerate(notes[:contexts]):
            payload['sourceContexts'].append({'fullText': text, 'sourceRevision': 7,
                'citationId': cid, 'sourceSpan': {'pointer': '/data/notes/' + str(i),
                'start': 0, 'end': len(text), 'text': text, 'offset_unit': 'unicode_codepoint'}})
        holds.append(hold(payload))
        holds.append(hold({'sourceContextsRequiredAlongsideInstructions': True,
                           'actualCookingQualified': False, 'servings': None, 'yield': None}))
    cautions = []
    if caution:
        target = native_actions[-1]
        text = notes[-1][2:]
        payload = {'documentKind': 'report-only-attributed-source-caution-companion',
            'boundNativeRun': binding | {'actionIds': [a['action_id'] for a in native_actions],
                'affectedActionId': target['action_id'], 'affectedSequenceIndex': actions - 1},
            'sourceOriginal': source_pin, 'sourceOccurrenceId': oid, 'sourceResourceId': rid,
            'sourcePageId': '7', 'sourceRevision': 7, 'sourceCitationId': cid,
            'attribution': provenance, 'sourceRawLine': notes[-1], 'text': text,
            'cookingSafetyNutritionScalingAcceptance': False,
            'sourceSpan': {'pointer': '/data/notes/' + str(contexts), 'start': 2,
                          'end': len(notes[-1]), 'text': text, 'offset_unit': 'unicode_codepoint'}}
        holds.append(hold(payload))
        cautions = [{'actionId': target['action_id'], 'sequenceIndex': actions - 1}]
    snapshot = {'databaseSha256': sha('generated-database'), 'admissionSha256': sha('generated-admission')}
    menu = {'schemaVersion': 'offmenu.generated-recipe-menu/1', 'snapshot': snapshot,
        'origin': 'APPLICATION_CREATED', 'selectionOrigin': 'GENERATED',
        'sourceMenuEvidence': None, 'actualUserSelection': False, 'automaticPlanning': False,
        'physicalCookingObserved': False, 'combinedNutrition': None, 'nutritionTotals': None,
        'admissionState': 'ACCEPTED_GENERATED_FIXTURE_ONLY', 'admissionLimits': {'status': 'present'},
        'members': [{'recipeEntityId': eid, 'recipeResourceId': rid,
            'instructionState': 'selected-native-run', 'userSelected': False, 'recipeNutrition': None,
            'native': {'run': {'run_id': run, 'recipe_entity_id': eid, 'source_occurrence_id': oid,
                               'status': 'ready-for-review', 'target_language': 'en'},
                       'actions': native_actions},
            'instructionRecords': records, 'instructions': [a['english_text'] for a in native_actions],
            'sourceRecords': [{'occurrence_id': oid, 'content_sha256': sha(original),
                               'sourceOriginal': original}], 'citations': [citation], 'holds': holds}]}
    guards = {run: {'recipeEntityId': eid, 'sourceOccurrenceId': oid,
                    'contextCount': contexts, 'cautionsBefore': cautions}}
    return menu, copy.deepcopy(snapshot), guards


def present(menu, snapshot, guards):
    return build_source_context_presentation(menu, expected_snapshot=snapshot,
                                             required_run_contexts=guards)


def lineage_fixture():
    menu, snapshot, guards = fixture(contexts=0, caution=False, actions=9)
    member = menu['members'][0]
    run = member['native']['run']['run_id']
    source = member['sourceRecords'][0]
    original = source['sourceOriginal']
    original['data']['originalTextLines'] = ['W' * 184, '* ' + 'V' * 92]
    source['content_sha256'] = sha(original)
    citation = member['citations'][0]
    actions = member['native']['actions']
    def span(i):
        text = original['data']['originalTextLines'][i]
        return {'pointer': '/source_original/data/originalTextLines/' + str(i),
                'start': 0, 'end': len(text), 'text': text, 'offset_unit': 'unicode_codepoint'}
    source_context = {'provenance': original['provenance'],
        'source_original': {'path': 'generated-source.json', 'sha256': sha('file')},
        'warning_source_context': span(0), 'appliance_variation': span(1),
        'unknownFutureSourceField': {'retain': ['all', 'fields']}}
    materials = [{'run_id': run, 'material_id': 'generated:material:' + str(i),
        'producer_instance_id': actions[0]['action_id'], 'producer_sequence': 0,
        'source_label': 'generated label ' + str(i), 'evidence_json': actions[0]['evidence_json']}
        for i in range(3)]
    inputs, contexts, references = [], [], []
    for i, action in enumerate(actions[1:]):
        material = materials[i % 3]
        inputs.append({'run_id': run, 'action_id': action['action_id'],
            'material_id': material['material_id'], 'action_sequence': i + 1,
            'producer_sequence': 0, 'evidence_json': action['evidence_json']})
        restrictions = ['Generated restriction ' + str(j) for j in range(6)]
        context = {'consumerInstanceId': action['action_id'], 'materialId': material['material_id'],
            'producerInstanceId': material['producer_instance_id'], 'basis': 'GENERATED_SOURCE_LINEAGE',
            'restrictions': restrictions, 'heldStrongerMeanings': restrictions[:2],
            'sourceLocalMeaning': 'Generated source participation only.', 'futureUnknown': None}
        contexts.append(context)
        references.append({k: context[k] for k in ('consumerInstanceId', 'producerInstanceId', 'materialId', 'basis')} |
            {'runId': run, 'sourceLabel': material['source_label'], 'contextPointer': '/perBindingContexts/' + str(i),
             'restrictionEntries': 6, 'restrictionCanonicalSHA256': sha(restrictions)})
    graph = {'materials': materials, 'materialInputs': inputs,
        'materialSupport': [{**{k: m[k] for k in ('run_id', 'material_id', 'evidence_json')},
                             'citation_id': citation['id']} for m in materials],
        'materialInputSupport': [{**{k: m[k] for k in ('run_id', 'action_id', 'material_id', 'evidence_json')},
                                  'citation_id': citation['id']} for m in inputs],
        'ingredients': [], 'ingredientSupport': [],
        'dependencies': [{'run_id': run, 'action_id': actions[i]['action_id'],
            'depends_on': actions[i - 1]['action_id'], 'action_sequence': i, 'dependency_sequence': i - 1}
            for i in range(1, 9)]}
    member['native']['graph'] = graph
    companion = {'schema': 'offmenu-qualified-source-local-lineage-context/1',
        'fullOriginalSourceContext': {'path': 'generated-context.json', 'sha256': sha('context-file')},
        'fullSourceWarning': span(0), 'applianceVariation': span(1),
        'perBindingContexts': contexts, 'nativeUnknownsByInstance': {
            a['action_id']: json.loads(a['unknown_parameters_json']) for a in actions},
        'rightsCitation': citation, 'meaning': 'Generated restricted source lineage only.',
        'requiredUse': 'Retain every restriction and unknown; no quantity or physical equivalence.'}
    pin = {'path': 'generated-only.json', 'sha256': sha('generated-file')}
    complete = {'documentKind': 'offmenu-source-local-lineage-qualified-companion/1',
        'boundRun': {'runId': run, 'recipeEntityId': member['recipeEntityId'],
                     'sourceOccurrenceId': source['occurrence_id'], 'rawOutput': pin},
        'completeCompanion': companion, 'completeOriginalSource': original,
        'completeOriginalSourceContext': source_context, 'referenceBindings': references,
        'independentActualOutputReview': pin, 'originalCompanion': pin,
        'requiredWrittenConsumerBindings': pin, 'meaning': 'Generated only.'}
    hid = sha('lineage-hold')
    member['holds'].extend([
        {'hold_id': hid, 'target_kind': 'recipe-run', 'target_id': run, 'reason': encoded(complete).decode()},
        {'hold_id': sha('scope-hold'), 'target_kind': 'recipe-run', 'target_id': run, 'reason': encoded({
            'sourceContextsRequiredAlongsideInstructions': True, 'requiredRunId': run,
            'all48PerBindingRestrictionsAnd9NativeUnknownArraysMandatory': True,
            'mandatoryCompanionHoldId': hid, 'mandatoryCompanionSHA256': pin['sha256'],
            'actualCookingQualified': False, 'servings': None, 'yield': None}).decode()}])
    guards[run]['contextCount'] = 3
    return menu, snapshot, guards


def add_historical(args, *, claim='generated-claim'):
    menu, snapshot, guards = args
    member = menu['members'][0]
    source = member['sourceRecords'][0]
    proof = {'databaseSHA256': sha('old-db'), 'admissionSHA256': sha('old-admission')}
    claim_sha = sha(claim)
    mention = member['recipeResourceId'] + ':ingredient:' + claim
    scope = {'sourceOnly': True, 'globalFit': False, 'actualRecipeComposition': None,
        'actualSelection': 'unobserved', 'purpose': 'HISTORICAL_SOURCE_DECLARATION_COMPATIBILITY_ONLY',
        'operationVisibility': 'private-internal-attributed-only',
        'requiredGroupClosure': {'role': 'GENERATED_TEST_ROLE', 'members': ['a', 'b']},
        'unknownRestriction': {'neverDrop': True}}
    result = {'claimSHA256': claim_sha, 'factsSHA256': sha('facts'), 'snapshot': proof,
        'actualRecipeComposition': None, 'currentStateFit': None, 'preparedYieldG': None, 'servings': None,
        'actualSelection': 'unobserved', 'compositionReadiness': 'held',
        'existingProductFitAcceptance': False, 'productFitAcceptance': False,
        'compositionGaps': {str(i): 'unobserved' for i in range(7)},
        'constraints': scope, 'sourceRestrictions': copy.deepcopy(scope),
        'sourcePins': {'sourceOccurrence': {'recipeId': member['recipeResourceId'], 'mentionId': mention,
            'occurrenceId': source['occurrence_id'], 'contentSha256': source['content_sha256']},
            'mention': {'resourceId': mention}, 'sourceCitations': [member['citations'][0]]},
        'futureUnknownResult': {'retainNull': None}}
    complete = {'documentKind': 'offmenu-private-historical-source-proof-context/1',
        'proofSnapshot': proof, 'currentSnapshotRebound': False, 'claimSHA256': claim_sha,
        'factsSHA256': sha('facts'), 'actualOutputRowSHA256': sha(result), 'completeActualResult': result,
        'purpose': scope['purpose'], 'callerTrust': 'Never reconstruct caller authority from stored JSON.',
        'qualifiedAcceptedEntries': {'path': 'DO-NOT-OPEN.json', 'sha256': sha('inert-pointer')},
        'join': {'physicalRecipeEntityId': member['recipeEntityId'],
                 'logicalRecipeResourceId': member['recipeResourceId'], 'claimSHA256': claim_sha, 'mentionId': mention},
        'futureUnknownContext': ['preserve', {'nested': None}]}
    member['holds'].append({'hold_id': sha(claim), 'target_kind': 'resource',
                            'target_id': member['recipeEntityId'], 'reason': encoded(complete).decode()})
    guards[member['native']['run']['run_id']]['contextCount'] += 1
    return complete


class ExtendedContextTests(unittest.TestCase):
    def test_current_shaped_five_members_fit_existing_bounds_without_dropping_contexts(self):
        cases = [fixture(contexts=0, caution=False, actions=3),
                 fixture(contexts=0, caution=True, actions=13),
                 fixture(contexts=3, caution=False, actions=13),
                 fixture(contexts=2, caution=False, actions=10), lineage_fixture()]
        members, guards = [], {}
        for index, args in enumerate(cases):
            for number in range(2 if index == 0 else 1 if index < 4 else 0):
                add_historical(args, claim='generated-' + str(index) + '-' + str(number))
            member = args[0]['members'][0]
            mapping = {member['recipeEntityId']: sha('entity-' + str(index)),
                       member['sourceRecords'][0]['occurrence_id']: sha('occ-' + str(index)),
                       member['native']['run']['run_id']: 'recipe-actions:' + sha('run-' + str(index)),
                       member['recipeResourceId']: 'generated:recipe:' + str(index)}
            def rename(value):
                if isinstance(value, str):
                    for old, new in mapping.items():
                        value = value.replace(old, new)
                    return value
                if isinstance(value, (list, tuple)): return [rename(v) for v in value]
                if isinstance(value, dict): return {rename(k): rename(v) for k, v in value.items()}
                return value
            renamed = rename(args)
            # Historical row hashes cover the now-renamed generated bindings.
            for hold in renamed[0]['members'][0]['holds']:
                if hold['reason'].startswith('{'):
                    document = json.loads(hold['reason'])
                    if document.get('documentKind') == 'offmenu-private-historical-source-proof-context/1':
                        document['actualOutputRowSHA256'] = sha(document['completeActualResult'])
                        hold['reason'] = encoded(document).decode()
            members.append(renamed[0]['members'][0]); guards.update(renamed[2])
        menu = copy.deepcopy(cases[0][0]); menu['members'] = members
        result = present(menu, cases[0][1], guards)
        self.assertEqual(result['counts'], {'instructions': 48, 'sourceContexts': 13, 'cautions': 1, 'events': 62})
        self.assertLessEqual(len(encoded(menu)), MAX_INPUT_BYTES)
        self.assertLessEqual(len(encoded(result)), MAX_OUTPUT_BYTES)

    def test_full_lineage_three_events_before_nine_instructions_no_io_or_mutation(self):
        args = lineage_fixture(); before = copy.deepcopy(args)
        with patch('builtins.open', side_effect=AssertionError('no I/O')):
            out = present(*args)
        self.assertEqual(args, before)
        events = out['members'][0]['events']
        self.assertEqual([e['kind'] for e in events], ['source-context'] * 3 + ['instruction'] * 9)
        self.assertEqual([len(e['text']) for e in events[:2]], [184, 94])
        self.assertEqual(events[2]['completeContext']['completeCompanion']['perBindingContexts'][0]['restrictions'],
                         ['Generated restriction ' + str(i) for i in range(6)])
        self.assertEqual(events[2]['selectedRunGraph'], args[0]['members'][0]['native']['graph'])
        self.assertFalse(events[2]['quantityAllocationAuthority'])

    def test_lineage_foreign_graph_reference_restrictions_unknowns_rights_and_scope_fail(self):
        for field in ('reference', 'restriction', 'unknowns', 'support', 'dependency', 'rights', 'scope', 'hold-id'):
            args = lineage_fixture(); member = args[0]['members'][0]
            hold, value = payload(args[0], 'offmenu-source-local-lineage-qualified-companion/1')
            if field == 'reference': value['referenceBindings'][0]['materialId'] = 'foreign'
            if field == 'restriction': value['completeCompanion']['perBindingContexts'][0]['restrictions'].pop()
            if field == 'unknowns': value['completeCompanion']['nativeUnknownsByInstance'].pop(next(iter(value['completeCompanion']['nativeUnknownsByInstance'])))
            if field == 'support': member['native']['graph']['materialInputSupport'].pop()
            if field == 'dependency': member['native']['graph']['dependencies'].clear()
            if field == 'rights': value['completeCompanion']['rightsCitation']['license'] = 'foreign'
            if field == 'scope': member['holds'].pop()
            if field == 'hold-id': hold['hold_id'] = sha('foreign')
            hold['reason'] = encoded(value).decode()
            with self.subTest(field=field), self.assertRaises(SourceContextPresentationError):
                present(*args)

    def test_full_historical_two_claims_keep_proof_storage_group_roles_and_unknowns(self):
        args = fixture(contexts=0, caution=False)
        first = add_historical(args, claim='first'); second = add_historical(args, claim='second')
        with patch('builtins.open', side_effect=AssertionError('no stored authority read')):
            events = present(*args)['members'][0]['events']
        self.assertEqual([e['completeContext'] for e in events[:2]], [first, second])
        self.assertNotEqual(events[0]['contextId'], events[1]['contextId'])
        self.assertEqual(events[0]['proofSnapshot'], first['proofSnapshot'])
        self.assertEqual(events[0]['storageSnapshot'], args[1])
        self.assertFalse(events[0]['callerAuthorityReconstructed'])
        self.assertFalse(events[0]['proofSnapshotReboundToStorageSnapshot'])
        self.assertEqual(events[0]['completeContext']['completeActualResult']['constraints']['requiredGroupClosure']['members'], ['a', 'b'])

    def test_historical_foreign_source_rebound_uplift_duplicate_or_incomplete_guard_fail(self):
        for field in ('foreign', 'rebound', 'uplift', 'row-hash', 'proof', 'duplicate', 'guard', 'unsupported'):
            args = fixture(contexts=0, caution=False); value = add_historical(args)
            hold = args[0]['members'][0]['holds'][-1]
            if field == 'foreign': value['join']['physicalRecipeEntityId'] = sha('foreign')
            if field == 'rebound': value['currentSnapshotRebound'] = True
            if field == 'uplift': value['completeActualResult']['currentStateFit'] = True; value['actualOutputRowSHA256'] = sha(value['completeActualResult'])
            if field == 'row-hash': value['completeActualResult']['futureUnknownResult'] = 'changed'
            if field == 'proof': value['proofSnapshot']['databaseSHA256'] = sha('new-proof')
            if field == 'unsupported': value['documentKind'] = 'unsupported-historical/2'
            hold['reason'] = encoded(value).decode()
            if field == 'duplicate': args[0]['members'][0]['holds'].append(copy.deepcopy(hold))
            if field == 'guard': next(iter(args[2].values()))['contextCount'] = 0
            with self.subTest(field=field), self.assertRaises(SourceContextPresentationError):
                present(*args)


def payload(menu, kind):
    member = menu['members'][0]
    for hold in member['holds']:
        if hold['reason'].startswith('{'):
            value = json.loads(hold['reason'])
            if value.get('documentKind') == kind:
                return hold, value
    raise AssertionError('Generated context missing')


class PresentationTests(unittest.TestCase):
    def rejected(self, mutate, *, case=None, code=None):
        menu, snapshot, guards = case or fixture()
        mutate(menu, snapshot, guards)
        with self.assertRaisesRegex(SourceContextPresentationError, code or '.'):
            present(menu, snapshot, guards)

    def test_whole_events_unknowns_and_warning_order(self):
        args = fixture(contexts=2)
        out = present(*args)
        events = out['members'][0]['events']
        self.assertEqual([x['kind'] for x in events],
                         ['source-context'] * 2 + ['instruction'] * 2 + ['source-caution', 'instruction'])
        self.assertEqual(out['counts'], {'instructions': 3, 'sourceContexts': 2, 'cautions': 1, 'events': 6})
        self.assertIn('final clause stays.', events[-2]['text'])
        self.assertEqual(events[-1]['unknownParameters'], ['source tool choice unknown'])
        self.assertEqual(out['members'][0]['remainingHolds'], args[0]['members'][0]['holds'])
        self.assertIsNone(out['nutritionTotals'])
        self.assertFalse(out['actualUserSelection'])

    def test_instruction_only_run(self):
        out = present(*fixture(contexts=0, caution=False))
        self.assertEqual(out['counts']['instructions'], 3)
        self.assertTrue(all(e['kind'] == 'instruction' for e in out['members'][0]['events']))

    def test_deterministic_pure_and_no_input_mutation(self):
        args = fixture(); before = copy.deepcopy(args)
        with patch('builtins.open', side_effect=AssertionError('I/O forbidden')):
            first, second = present(*args), present(*args)
        self.assertEqual(first, second)
        self.assertEqual(args, before)
        first['members'][0]['remainingHolds'].clear()
        self.assertEqual(args, before)

    def test_markup_is_literal_plaintext_not_trusted_html(self):
        menu, snapshot, guards = fixture()
        hold, doc = payload(menu, 'attributed-source-context-companion')
        source = menu['members'][0]['sourceRecords'][0]
        text = '<img src=x onerror="alert(1)"> literal source text'
        source['sourceOriginal']['data']['notes'][0] = text
        source['content_sha256'] = sha(source['sourceOriginal'])
        doc['sourceContexts'][0].update(fullText=text)
        doc['sourceContexts'][0]['sourceSpan'].update(text=text, end=len(text))
        hold['reason'] = encoded(doc).decode()
        event = present(menu, snapshot, guards)['members'][0]['events'][0]
        self.assertEqual(event['text'], text)
        self.assertEqual(event['textFormat'], 'plain')
        self.assertNotIn('html', event)

    def test_snapshot_and_guard_mismatch(self):
        self.rejected(lambda m,s,g: s.update(databaseSha256=sha('foreign')), code='snapshot')
        self.rejected(lambda m,s,g: g.clear(), code='count')
        self.rejected(lambda m,s,g: next(iter(g.values())).update(recipeEntityId=sha('foreign')))
        self.rejected(lambda m,s,g: next(iter(g.values())).update(sourceOccurrenceId=sha('foreign')))

    def test_missing_foreign_and_duplicate_companion(self):
        def missing(m,s,g):
            h,_=payload(m,'attributed-source-context-companion');m['members'][0]['holds'].remove(h)
        def duplicate(m,s,g):
            h,_=payload(m,'attributed-source-context-companion');m['members'][0]['holds'].append(copy.deepcopy(h))
        def foreign(m,s,g):
            h,d=payload(m,'attributed-source-context-companion');d['boundNativeRun']['runId']='recipe-actions:'+sha('foreign');h['reason']=encoded(d).decode()
        for mutation in [missing, duplicate, foreign]:
            with self.subTest(mutation=mutation.__name__):self.rejected(mutation)

    def test_missing_caution_and_wrong_guard_target(self):
        def missing(m,s,g):
            h,_=payload(m,'report-only-attributed-source-caution-companion');m['members'][0]['holds'].remove(h)
        self.rejected(missing, code='required-caution')
        self.rejected(lambda m,s,g: next(iter(g.values()))['cautionsBefore'][0].update(sequenceIndex=0))

    def test_wrong_caution_sequence_or_rawline_or_action_set(self):
        for field, value in [('affectedSequenceIndex', 0), ('affectedActionId', 'foreign'), ('actionIds', [])]:
            def mutate(m,s,g,field=field,value=value):
                h,d=payload(m,'report-only-attributed-source-caution-companion');d['boundNativeRun'][field]=value;h['reason']=encoded(d).decode()
            with self.subTest(field=field):self.rejected(mutate)
        def rawline(m,s,g):
            h,d=payload(m,'report-only-attributed-source-caution-companion');d['sourceRawLine']='wrong';h['reason']=encoded(d).decode()
        self.rejected(rawline)

    def test_clipped_context_or_caution_is_rejected(self):
        for kind in ['attributed-source-context-companion','report-only-attributed-source-caution-companion']:
            def clip(m,s,g,kind=kind):
                h,d=payload(m,kind);c=d['sourceContexts'][0]if 'sourceContexts'in d else d
                field='fullText'if 'fullText'in c else'text';c[field]=c[field][:-1];c['sourceSpan']['text']=c[field];c['sourceSpan']['end']-=1;h['reason']=encoded(d).decode()
            with self.subTest(kind=kind):self.rejected(clip, code='whole-')

    def test_unicode_codepoints_not_utf16_or_bytes(self):
        def mutate(m,s,g):
            h,d=payload(m,'attributed-source-context-companion');span=d['sourceContexts'][0]['sourceSpan'];span['end']=len(span['text'].encode('utf-16-le'))//2;h['reason']=encoded(d).decode()
        self.rejected(mutate)
        self.rejected(lambda m,s,g: m['members'][0]['sourceRecords'][0].update(content_sha256=sha('wrong')))

    def test_rights_revision_and_provenance_mismatch(self):
        for field,value in [('license',''),('attribution','wrong'),('revisionId',8),('historyUrl','https://wrong.test/history')]:
            def mutate(m,s,g,field=field,value=value):m['members'][0]['citations'][0][field]=value
            with self.subTest(field=field):self.rejected(mutate)
        def wrong(m,s,g):
            h,d=payload(m,'attributed-source-context-companion');d['provenance']['changes']='wrong';h['reason']=encoded(d).decode()
        self.rejected(wrong)

    def test_unsafe_urls(self):
        for url in ['javascript:alert(1)','data:text/html,x','https://user:password@example.test/','https://example.test/\npath','https://example.test:99999/']:
            def mutate(m,s,g,url=url):
                member=m['members'][0];source=member['sourceRecords'][0];source['sourceOriginal']['provenance']['url']=url;source['content_sha256']=sha(source['sourceOriginal']);member['citations'][0]['originalUrl']=url
                for h in member['holds']:
                    if h['reason'].startswith('{'):
                        d=json.loads(h['reason'])
                        for key in ['provenance','attribution']:
                            if type(d.get(key))is dict:d[key]['url']=url
                        h['reason']=encoded(d).decode()
            with self.subTest(url=url):self.rejected(mutate)

    def test_malformed_duplicate_and_nonfinite_hold_json(self):
        for reason in ['{"documentKind":', '{"a":1,"a":2}', '{"a":NaN}']:
            with self.subTest(reason=reason):self.rejected(lambda m,s,g: m['members'][0]['holds'].append({'reason':reason}))

    def test_unknown_json_hold_retained_but_context_shape_not_ignored(self):
        args=fixture();args[0]['members'][0]['holds'].append({'reason':'{"futureMetadata":[1,2]}'})
        self.assertEqual(present(*args)['members'][0]['remainingHolds'][-1]['reason'],'{"futureMetadata":[1,2]}')
        def wrong(m,s,g):
            h,d=payload(m,'attributed-source-context-companion');d['documentKind']='unknown';h['reason']=encoded(d).decode()
        self.rejected(wrong)

    def test_authority_uplift_and_unqualified_action(self):
        for field,value in [('actualUserSelection',True),('nutritionTotals',{}),('sourceMenuEvidence',{})]:
            with self.subTest(field=field):self.rejected(lambda m,s,g,field=field,value=value:m.update({field:value}))
        self.rejected(lambda m,s,g:m['members'][0]['instructionRecords'][0].update(status='held'))
        def uplift(m,s,g):m['members'][0]['holds'].append({'reason':'{"actualCookingQualified":true}'})
        self.rejected(uplift)

    def test_instruction_order_evidence_support_and_unknowns(self):
        self.rejected(lambda m,s,g:m['members'][0]['native']['actions'].reverse())
        self.rejected(lambda m,s,g:m['members'][0]['instructions'].reverse())
        self.rejected(lambda m,s,g:m['members'][0]['instructionRecords'][0]['supportRecords'][0].update(run_id='foreign'))
        self.rejected(lambda m,s,g:m['members'][0]['native']['actions'][0].update(unknown_parameters_json='[]'))
        self.rejected(lambda m,s,g:m['members'][0]['native']['actions'][0].update(evidence_json='[]'))

    def test_both_action_rows_must_belong_to_selected_run(self):
        for target in ('action', 'record', 'both', 'missing-action', 'missing-record'):
            args = fixture()
            member = args[0]['members'][0]
            action = member['native']['actions'][0]
            record = member['instructionRecords'][0]
            record['actionRecord'] = copy.deepcopy(action)
            if target in ('action', 'both'):
                action['run_id'] = 'recipe-actions:' + sha('foreign')
            if target in ('record', 'both'):
                record['actionRecord']['run_id'] = 'recipe-actions:' + sha('foreign')
            if target == 'missing-action':
                del action['run_id']
            if target == 'missing-record':
                del record['actionRecord']['run_id']
            self.assertEqual(record['supportRecords'][0]['run_id'],
                             member['native']['run']['run_id'])
            before = copy.deepcopy(args)
            with self.subTest(target=target):
                with self.assertRaisesRegex(SourceContextPresentationError, 'instruction-run-binding'):
                    present(*args)
                self.assertEqual(args, before)

    def test_complete_admission_limits_and_unknown_restrictions_survive(self):
        args = fixture()
        limits = {'status': 'present', 'allowedPurpose': 'PRIVATE_INTERNAL_ATTRIBUTED_SOURCE_ONLY',
                  'publicRedistributionQualified': False,
                  'unknownFutureRightsRestriction': {'exact': 'RETAIN café 😀',
                      'unknownFlags': [False, None, {'unreviewed': True}]}}
        args[0]['admissionLimits'] = copy.deepcopy(limits)
        before = copy.deepcopy(args)
        out = present(*args)
        self.assertEqual(out['admissionLimits'], limits)
        self.assertEqual(out['snapshot'], args[1])
        out['admissionLimits']['unknownFutureRightsRestriction']['unknownFlags'].clear()
        self.assertEqual(args, before)

    def test_preserved_admission_limits_still_obey_whole_output_cap(self):
        args = fixture(contexts=10, provenance_extra=18000)
        base = present(*args)
        padding = MAX_OUTPUT_BYTES - len(encoded(base)) + 1
        self.assertGreater(padding, 0)
        args[0]['admissionLimits']['unknownFutureRestriction'] = 'x' * padding
        self.assertLess(len(encoded(args[0])), MAX_INPUT_BYTES)
        before = copy.deepcopy(args)
        with self.assertRaisesRegex(SourceContextPresentationError, 'json-byte-bound'):
            present(*args)
        self.assertEqual(args, before)

    def test_input_bytes_nodes_depth_and_count_limits(self):
        self.rejected(lambda m,s,g:m.update(padding='x'*MAX_INPUT_BYTES),code='json-byte-bound')
        self.rejected(lambda m,s,g:m.update(padding=[None]*(MAX_JSON_NODES+1)),code='json-node')
        def deep(m,s,g):
            x={};m['padding']=x
            for _ in range(22):x['child']={};x=x['child']
        self.rejected(deep,code='depth')
        self.rejected(lambda m,s,g:None,case=fixture(actions=MAX_INSTRUCTIONS+1),code='instruction-count')
        self.rejected(lambda m,s,g:m['members'][0]['holds'].append({'reason':'x'*(MAX_HOLD_REASON_BYTES+1)}))

    def test_output_amplification_is_bounded_without_partial_result(self):
        args=fixture(contexts=15,caution=True,provenance_extra=55000)
        self.assertLess(len(encoded(args[0])),MAX_INPUT_BYTES)
        self.assertTrue(all(len(h['reason'].encode())<=MAX_HOLD_REASON_BYTES for h in args[0]['members'][0]['holds']))
        with self.assertRaisesRegex(SourceContextPresentationError,'json-byte-bound'):
            present(*args)


if __name__ == '__main__':
    unittest.main()
