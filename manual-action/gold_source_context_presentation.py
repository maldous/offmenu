"""Pure plain-text presentation of already selected, admitted source records.

Callers supply a verified generated-menu result and independent trusted snapshot
and run guards. This adapter does not authenticate a database or qualify facts.
It performs no I/O, returns no HTML, and never changes its inputs.
"""
import copy
import hashlib
import json
import math
import re
from urllib.parse import urlsplit

SCHEMA_VERSION = 'offmenu.source-context-presentation/1'
MAX_INPUT_BYTES = 1048576
MAX_OUTPUT_BYTES = 1048576
MAX_JSON_NODES = 100000
MAX_DEPTH = 20
MAX_MEMBERS = 8
MAX_INSTRUCTIONS = 128
MAX_CONTEXTS = 16
MAX_HOLD_REASON_BYTES = 65536
MAX_TEXT_BYTES = 16384
_SHA = re.compile(r'[0-9a-f]{64}\Z')
_RUN = re.compile(r'recipe-actions:[0-9a-f]{64}\Z')
_COMPANION = 'attributed-source-context-companion'
_CAUTION = 'report-only-attributed-source-caution-companion'
_FALSE_SCOPE = ('actualCookingQualified', 'actualUserChoice',
                'recipeNutritionQualified', 'scalingQualified', 'executionQualified',
                'cookingSafetyNutritionScalingAcceptance')


class SourceContextPresentationError(ValueError):
    """The complete input cannot be presented under the selected contract."""


def _need(condition, code):
    if not condition:
        raise SourceContextPresentationError(code)


def _encoded(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False,
                      separators=(',', ':'), allow_nan=False).encode('utf-8')


def _digest(value):
    return hashlib.sha256(_encoded(value)).hexdigest()


def _text(value, limit=MAX_TEXT_BYTES):
    _need(type(value) is str and bool(value.strip())
          and len(value.encode('utf-8')) <= limit, 'text-bound-or-shape')
    return value


def _bounded(value, byte_limit):
    stack, nodes = [(value, 0)], 0
    while stack:
        item, depth = stack.pop()
        nodes += 1
        _need(depth <= MAX_DEPTH and nodes <= MAX_JSON_NODES, 'json-node-or-depth-bound')
        if type(item) is dict:
            _need(all(type(k) is str for k in item), 'json-key-shape')
            nodes += len(item)  # Count keys as well as values.
            _need(nodes + len(item) <= MAX_JSON_NODES, 'json-node-or-depth-bound')
            stack.extend((v, depth + 1) for v in item.values())
        elif type(item) is list:
            _need(nodes + len(item) <= MAX_JSON_NODES, 'json-node-or-depth-bound')
            stack.extend((v, depth + 1) for v in item)
        else:
            _need(type(item) in (str, int, float, bool, type(None)), 'json-value-shape')
            _need(type(item) is not float or math.isfinite(item), 'json-nonfinite')
    _need(len(_encoded(value)) <= byte_limit, 'json-byte-bound')


def _pairs(pairs):
    result = {}
    for key, value in pairs:
        _need(key not in result, 'duplicate-json-key')
        result[key] = value
    return result


def _bad_constant(_):
    raise SourceContextPresentationError('json-nonfinite')


def _parsed(raw):
    _text(raw, MAX_HOLD_REASON_BYTES)
    value = json.loads(raw, object_pairs_hook=_pairs, parse_constant=_bad_constant)
    _bounded(value, MAX_HOLD_REASON_BYTES)
    return value


def _sha(value):
    return type(value) is str and _SHA.fullmatch(value) is not None


def _url(value):
    _text(value, 8192)
    _need(not any(c.isspace() or ord(c) < 32 or ord(c) == 127 for c in value),
          'unsafe-source-url')
    parsed = urlsplit(value)
    _need(parsed.scheme in ('http', 'https') and bool(parsed.hostname)
          and parsed.username is None and parsed.password is None, 'unsafe-source-url')
    _need(parsed.port is None or 1 <= parsed.port <= 65535, 'unsafe-source-url')
    _need(not any(c in parsed.netloc for c in '<>"\\'), 'unsafe-source-url')


def _rights(citation, provenance):
    _need(type(citation) is dict and type(provenance) is dict, 'source-rights-shape')
    _text(citation.get('id'))
    for key in ('sourceId', 'license', 'attribution', 'historyUrl', 'sourceDate'):
        _text(provenance.get(key))
        _need(citation.get(key) == provenance[key], 'source-rights-mismatch')
    _need('revisionId' in provenance and citation.get('revisionId') == provenance['revisionId'],
          'source-revision-mismatch')
    for source, target in (('recordId', 'originalRecordId'), ('url', 'originalUrl'),
                           ('licenseUrl', 'rightsEvidenceUrl')):
        _text(provenance.get(source))
        _need(citation.get(target) == provenance[source], 'source-rights-mismatch')
    _need(citation.get('scope', {}).get('visibility') == provenance.get('visibility')
          and provenance.get('visibility') in ('public', 'local-restricted'),
          'source-visibility-mismatch')
    for key in ('url', 'historyUrl', 'licenseUrl'):
        _url(provenance[key])


def _pointer(original, pointer):
    _need(type(pointer) is str and pointer.startswith('/') and pointer != '/',
          'source-pointer-shape')
    value = original
    for key in pointer[1:].split('/'):
        key = key.replace('~1', '/').replace('~0', '~')
        if type(value) is list:
            _need(bool(re.fullmatch(r'0|[1-9][0-9]*', key)), 'source-pointer-shape')
            index = int(key)
            _need(index < len(value), 'source-pointer-range')
            value = value[index]
        else:
            _need(type(value) is dict and key in value, 'source-pointer-range')
            value = value[key]
    return value


def _span(span, original, *, whole=False, caution=False):
    _need(type(span) is dict and span.get('offset_unit') == 'unicode_codepoint',
          'source-span-shape')
    target = _pointer(original, span.get('pointer'))
    start, end = span.get('start'), span.get('end')
    _need(type(target) is str and type(start) is int and type(end) is int
          and 0 <= start < end <= len(target), 'source-span-range')
    _need(target[start:end] == _text(span.get('text')), 'source-span-text-mismatch')
    if whole:
        _need(start == 0 and end == len(target), 'whole-context-required')
    if caution:
        marker = 2 if target.startswith(('* ', '# ', '- ')) else 0
        _need(start == marker and end == len(target), 'whole-caution-required')
    return target


def _scope_flags(payload):
    for key in _FALSE_SCOPE:
        _need(key not in payload or payload[key] is False, 'source-authority-uplift')
    for key in ('servings', 'yield', 'recipeNutrition', 'nutritionTotals'):
        _need(key not in payload or payload[key] is None, 'source-authority-uplift')


def _guard(guard):
    _need(type(guard) is dict and set(guard) == {
        'recipeEntityId', 'sourceOccurrenceId', 'contextCount', 'cautionsBefore'},
        'run-guard-shape')
    _need(_sha(guard['recipeEntityId']) and _sha(guard['sourceOccurrenceId'])
          and type(guard['contextCount']) is int and 0 <= guard['contextCount'] <= MAX_CONTEXTS
          and type(guard['cautionsBefore']) is list
          and len(guard['cautionsBefore']) <= MAX_CONTEXTS, 'run-guard-shape')
    seen = set()
    for item in guard['cautionsBefore']:
        _need(type(item) is dict and set(item) == {'actionId', 'sequenceIndex'}
              and type(item['sequenceIndex']) is int and item['sequenceIndex'] >= 0,
              'caution-guard-shape')
        _text(item['actionId'])
        _need(item['actionId'] not in seen, 'duplicate-caution-guard')
        seen.add(item['actionId'])


def _instruction_events(member, run, provenance, citations):
    actions, records = member['native']['actions'], member['instructionRecords']
    _need(type(actions) is list and 1 <= len(actions) <= MAX_INSTRUCTIONS
          and type(records) is list and len(records) == len(actions), 'instruction-count')
    _need([a.get('sequence_index') for a in actions] == list(range(len(actions)))
          and all(type(a.get('sequence_index')) is int for a in actions), 'instruction-order')
    _need(len({a['action_id'] for a in actions}) == len(actions), 'duplicate-action')
    _need(member['instructions'] == [a['english_text'] for a in actions],
          'instruction-display-mismatch')
    events = []
    for action, record in zip(actions, records):
        _need(action.get('run_id') == run['run_id']
              and record.get('actionRecord', {}).get('run_id') == run['run_id'],
              'instruction-run-binding')
        _need(record.get('status') == 'qualified' and record.get('holdReasons') == []
              and record.get('actionRecord') == action, 'instruction-provenance')
        _text(action['action_id']); _text(action['english_text'])
        _need(type(action.get('source_order')) is int and action['source_order'] >= 0,
              'instruction-source-order')
        evidence, unknowns = _parsed(action['evidence_json']), _parsed(action['unknown_parameters_json'])
        _need(type(evidence) is list and evidence and evidence == record.get('evidence'),
              'instruction-evidence')
        _need(type(unknowns) is list and all(type(x) is str for x in unknowns), 'unknowns-shape')
        for span in evidence:
            _need(span.get('pointer') == '/steps/' + str(action['source_order']) + '/raw_text',
                  'instruction-evidence')
            original = _text(action['original_text'])
            start, end = span.get('start'), span.get('end')
            _need(span.get('offset_unit') == 'unicode_codepoint'
                  and type(start) is int and type(end) is int
                  and 0 <= start < end <= len(original)
                  and original[start:end] == _text(span.get('text')), 'instruction-evidence')
        instance = _parsed(action['native_instance_json'])
        _need(instance.get('instance_id') == action['action_id']
              and instance.get('template_id') == action['template_id']
              and instance.get('unknown_parameters') == unknowns, 'native-instance-binding')
        supports = record.get('supportRecords')
        _need(type(supports) is list and supports, 'instruction-support')
        rcites = record.get('citations')
        _need(type(rcites) is list and rcites, 'instruction-rights')
        ids = set()
        for citation in rcites:
            _rights(citation, provenance)
            cid = citation['id']; ids.add(cid)
            _need(citations.get(cid) == citation, 'instruction-rights-mismatch')
        parsed_supports = []
        for support in supports:
            _need(support.get('run_id') == run['run_id']
                  and support.get('action_id') == action['action_id']
                  and support.get('citation_id') in ids, 'instruction-support-binding')
            parsed = _parsed(support['evidence_json'])
            _need(parsed == evidence, 'instruction-support-evidence')
            parsed_supports.append(parsed)
        _need(record.get('supportEvidence') == parsed_supports, 'instruction-support-evidence')
        events.append({'kind': 'instruction', 'actionId': action['action_id'],
                       'sequenceIndex': action['sequence_index'], 'text': action['english_text'],
                       'textFormat': 'plain', 'unknownParameters': unknowns,
                       'evidence': evidence, 'citations': rcites})
    return events


def _member(member, guard):
    _guard(guard)
    _need(member.get('instructionState') == 'selected-native-run'
          and member.get('userSelected') is False and member.get('recipeNutrition') is None,
          'member-source-scope')
    run = member['native']['run']; rid = run['run_id']
    _need(_RUN.fullmatch(rid) is not None and run['recipe_entity_id'] == member['recipeEntityId']
          == guard['recipeEntityId'] and run['source_occurrence_id'] == guard['sourceOccurrenceId']
          and run['status'] == 'ready-for-review' and run['target_language'] == 'en',
          'selected-run-binding')
    sources = [s for s in member['sourceRecords'] if s['occurrence_id'] == run['source_occurrence_id']]
    _need(len(sources) == 1, 'selected-source-occurrence')
    source = sources[0]; original = source['sourceOriginal']
    _need(_sha(source.get('content_sha256')) and _digest(original) == source['content_sha256'],
          'source-content-mismatch')
    provenance = original['provenance']
    citations = {c['id']: c for c in member['citations']}
    _need(len(citations) == len(member['citations']), 'duplicate-citation')
    instructions = _instruction_events(member, run, provenance, citations)
    context_events, cautions, context_ids = [], {}, set()
    companions, require_companion = 0, False
    for hold in member['holds']:
        reason = _text(hold['reason'], MAX_HOLD_REASON_BYTES)
        if not reason.lstrip().startswith(('{', '[')):
            continue  # Preserve plain holds, without interpreting their English as policy.
        payload = _parsed(reason)
        if type(payload) is not dict:
            continue
        _scope_flags(payload)
        if payload.get('sourceContextsRequiredAlongsideInstructions') is True:
            _need(hold.get('target_kind') == 'recipe-run' and hold.get('target_id') == rid,
                  'scope-hold-target')
            require_companion = True
        kind = payload.get('documentKind')
        if kind not in (_COMPANION, _CAUTION):
            _need(not any(k in payload for k in ('sourceContexts', 'boundNativeRun', 'sourceSpan')),
                  'unrecognized-context-document')
            continue
        _need(hold.get('target_kind') == 'recipe-run' and hold.get('target_id') == rid,
              'context-hold-target')
        binding = payload['boundNativeRun']
        _need(binding['runId'] == rid and binding['recipeEntityId'] == member['recipeEntityId']
              and binding['sourceOccurrenceId'] == source['occurrence_id'], 'context-run-binding')
        source_pin = payload['sourceOriginal']
        _need(type(source_pin) is dict and _sha(source_pin.get('sha256')), 'source-file-pin')
        _text(source_pin.get('path'), 8192)  # Metadata only; never dereferenced.
        contexts = payload['sourceContexts'] if kind == _COMPANION else [payload]
        _need(type(contexts) is list and len(contexts) <= MAX_CONTEXTS, 'context-count')
        if kind == _COMPANION:
            companions += 1
            _need(companions == 1 and payload['provenance'] == provenance,
                  'duplicate-or-foreign-companion')
        else:
            _need(payload['attribution'] == provenance and payload['sourceOccurrenceId'] == source['occurrence_id']
                  and payload['sourceResourceId'] == member['recipeResourceId']
                  and payload['sourcePageId'] == provenance['recordId'], 'caution-source-binding')
            _need(binding['actionIds'] == [e['actionId'] for e in instructions], 'caution-action-binding')
        for context in contexts:
            span = context['sourceSpan']
            target = _span(span, original, whole=kind == _COMPANION, caution=kind == _CAUTION)
            text = context['fullText'] if kind == _COMPANION else context['text']
            _need(text == span['text'], 'whole-context-text')
            if kind == _CAUTION:
                _need(payload['sourceRawLine'] == target, 'caution-raw-source-line')
            cid = context['citationId'] if kind == _COMPANION else context['sourceCitationId']
            _need(context['sourceRevision'] == provenance['revisionId'] and cid in citations,
                  'context-citation-binding')
            _rights(citations[cid], provenance)
            identity = _digest([rid, kind, span, cid])
            _need(identity not in context_ids, 'duplicate-context')
            context_ids.add(identity)
            event = {'kind': 'source-context' if kind == _COMPANION else 'source-caution',
                     'contextId': 'source-context:' + identity, 'text': text, 'textFormat': 'plain',
                     'sourceSpan': span, 'citationIds': [cid], 'citations': [citations[cid]],
                     'sourceRevision': context['sourceRevision'], 'provenance': provenance,
                     'sourceOriginalPin': source_pin,
                     'sourceBinding': {'nativeRunId': rid, 'recipeEntityId': member['recipeEntityId'],
                                       'sourceOccurrenceId': source['occurrence_id'],
                                       'sourceContentSha256': source['content_sha256']}}
            if kind == _COMPANION:
                context_events.append(event)
            else:
                aid, seq = binding['affectedActionId'], binding['affectedSequenceIndex']
                _need(type(seq) is int and 0 <= seq < len(instructions)
                      and instructions[seq]['actionId'] == aid and aid not in cautions,
                      'caution-action-order')
                event.update(beforeActionId=aid, beforeSequenceIndex=seq)
                cautions[aid] = event
    _need(len(context_events) == guard['contextCount'] and (not require_companion or companions == 1),
          'required-context-missing-or-extra')
    actual_cautions = sorted((k, v['beforeSequenceIndex']) for k, v in cautions.items())
    required_cautions = sorted((x['actionId'], x['sequenceIndex']) for x in guard['cautionsBefore'])
    _need(actual_cautions == required_cautions, 'required-caution-missing-or-extra')
    events = context_events[:]
    for instruction in instructions:
        if instruction['actionId'] in cautions:
            events.append(cautions[instruction['actionId']])
        events.append(instruction)
    return {'recipeEntityId': member['recipeEntityId'], 'recipeResourceId': member['recipeResourceId'],
            'nativeRunId': rid, 'sourceOccurrenceId': source['occurrence_id'],
            'sourceContentSha256': source['content_sha256'], 'sourceProvenance': provenance,
            'events': events, 'remainingHolds': member['holds'],
            'recipeNutrition': None, 'userSelected': False, 'completeCookingPlan': False}


def build_source_context_presentation(menu_result, *, expected_snapshot, required_run_contexts):
    """Return a complete plain-text event DTO, or raise without partial output.

    Snapshot pins and run/context guards must come from a trusted caller, not
    an incoming UI request. The menu must be the unmodified result of the
    existing verified snapshot reader. Hash agreement is not new admission or
    independent qualification. Render text with textContent/escaping, never as
    HTML; URL checks do not make strings safe to concatenate into markup.
    """
    try:
        _bounded(menu_result, MAX_INPUT_BYTES)
        _bounded(expected_snapshot, MAX_INPUT_BYTES)
        _bounded(required_run_contexts, MAX_INPUT_BYTES)
        _need(type(expected_snapshot) is dict and set(expected_snapshot) == {
            'databaseSha256', 'admissionSha256'} and all(_sha(v) for v in expected_snapshot.values()),
            'trusted-snapshot-shape')
        _need(type(menu_result) is dict and menu_result.get('schemaVersion') == 'offmenu.generated-recipe-menu/1'
              and menu_result.get('snapshot') == expected_snapshot, 'snapshot-mismatch')
        _need(menu_result.get('origin') == 'APPLICATION_CREATED'
              and menu_result.get('selectionOrigin') == 'GENERATED'
              and menu_result.get('sourceMenuEvidence') is None, 'generated-source-only-origin')
        _need(menu_result.get('actualUserSelection') is False and menu_result.get('automaticPlanning') is False
              and menu_result.get('physicalCookingObserved') is False
              and menu_result.get('combinedNutrition') is None and menu_result.get('nutritionTotals') is None,
              'source-authority-uplift')
        _need(type(menu_result.get('admissionState')) is str
              and menu_result['admissionState'].startswith('ACCEPTED_')
              and menu_result.get('admissionLimits', {}).get('status') == 'present', 'admission-limits-required')
        members = menu_result['members']
        _need(type(members) is list and 1 <= len(members) <= MAX_MEMBERS
              and type(required_run_contexts) is dict and len(required_run_contexts) == len(members),
              'member-or-guard-count')
        runs = [m['native']['run']['run_id'] for m in members]
        _need(len(set(runs)) == len(runs) and set(runs) == set(required_run_contexts),
              'explicit-run-set-mismatch')
        _need(len({m['recipeEntityId'] for m in members}) == len(members), 'duplicate-recipe')
        result = {'schemaVersion': SCHEMA_VERSION, 'textFormat': 'plain',
                  'snapshot': expected_snapshot, 'admissionLimits': menu_result['admissionLimits'],
                  'origin': 'APPLICATION_CREATED', 'selectionOrigin': 'GENERATED',
                  'sourceMenuEvidence': None, 'actualUserSelection': False, 'combinedNutrition': None,
                  'nutritionTotals': None, 'automaticPlanning': False, 'physicalCookingObserved': False,
                  'completeCookingPlan': False,
                  'purpose': 'Presentation of existing source instructions and contexts only; no new qualification.',
                  'members': [_member(m, required_run_contexts[r]) for m, r in zip(members, runs)]}
        kinds = [e['kind'] for m in result['members'] for e in m['events']]
        _need(kinds.count('instruction') <= MAX_INSTRUCTIONS
              and kinds.count('source-context') + kinds.count('source-caution') <= MAX_CONTEXTS,
              'presentation-event-count')
        result['counts'] = {'instructions': kinds.count('instruction'),
                            'sourceContexts': kinds.count('source-context'),
                            'cautions': kinds.count('source-caution'), 'events': len(kinds)}
        _bounded(result, MAX_OUTPUT_BYTES)
        return copy.deepcopy(result)
    except SourceContextPresentationError:
        raise
    except (KeyError, TypeError, ValueError, IndexError, AttributeError, RecursionError, OverflowError):
        raise SourceContextPresentationError('malformed-presentation-input') from None
