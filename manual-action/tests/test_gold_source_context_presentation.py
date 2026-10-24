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
    MAX_HOLD_REASON_BYTES, MAX_INPUT_BYTES, MAX_INSTRUCTIONS, MAX_JSON_NODES,
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
