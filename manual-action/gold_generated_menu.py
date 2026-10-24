"""Read-only application-created recipe groups in an already admitted snapshot."""
import argparse
import hashlib
import json
import math
from pathlib import Path
import re
import sqlite3
import time

from gold_snapshot_access import SnapshotAccessError, verified_snapshot

GROUP_VERSION = 'offmenu.application-created-recipe-group/1'
RESULT_VERSION = 'offmenu.generated-recipe-menu/1'


class GeneratedMenuError(ValueError):
    pass


def encoded(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True,
                      separators=(',', ':'), allow_nan=False).encode()


def _require(condition, code):
    if not condition:
        raise GeneratedMenuError(code)


def _sha(value):
    return type(value) is str and re.fullmatch('[0-9a-f]{64}', value) is not None


def _bounded_json(value, max_bytes=65536):
    nodes = 0

    def visit(item, depth=0):
        nonlocal nodes
        nodes += 1
        _require(depth <= 12 and nodes <= 4096, 'group-structure-limit')
        if type(item) is dict:
            _require(all(type(k) is str for k in item), 'group-json-shape')
            for child in item.values():
                visit(child, depth + 1)
        elif type(item) is list:
            for child in item:
                visit(child, depth + 1)
        else:
            _require(type(item) in (str, int, float, bool, type(None)), 'group-json-shape')
            if type(item) is float:
                _require(math.isfinite(item), 'group-json-shape')

    visit(value)
    _require(len(encoded(value)) <= max_bytes, 'group-byte-limit')


def _parsed_json(raw):
    try:
        value = json.loads(raw)
    except (ValueError, TypeError):
        return None
    _bounded_json(value)
    return value


def _native_pins_valid(run):
    source = run.get('native_source_pin')
    modules = _parsed_json(run.get('native_modules_json'))
    return (type(source) is str and re.fullmatch('[0-9a-f]{40}|[0-9a-f]{64}', source) is not None
            and type(modules) is dict and bool(modules)
            and all(k.strip() and _sha(v) for k, v in modules.items())
            and all(_sha(run.get(k)) for k in [
                'rules_artifact_sha256', 'semantic_review_sha256',
                'translation_receipts_sha256', 'connection_sha256', 'source_original_sha256']))


def _action_evidence_valid(evidence, action):
    original, order = action.get('original_text'), action.get('source_order')
    if not (type(original) is str and type(order) is int and order >= 0
            and type(evidence) is list and evidence):
        return False
    return all(type(span) is dict and span.get('pointer') == f'/steps/{order}/raw_text'
               and span.get('offset_unit') == 'unicode_codepoint'
               and type(span.get('start')) is int and type(span.get('end')) is int
               and 0 <= span['start'] < span['end'] <= len(original)
               and type(span.get('text')) is str
               and original[span['start']:span['end']] == span['text'] for span in evidence)


def _receipt_limits(receipt):
    fields = {k: receipt[k] for k in ['scopeLimits', 'sourceAndConsumerLimits'] if k in receipt}
    _bounded_json(fields)
    reasons = []
    schema = receipt.get('schemaVersion')
    if schema != 'offmenu.private-incremental-source-data-admission/1':
        reasons.append('unsupported-receipt-schema')
    if not fields:
        reasons.append('admission-limits-unknown')
    if any(type(v) is not dict or not v for v in fields.values()):
        reasons.append('admission-limits-invalid')
    return {'receiptSchemaVersion': schema, 'status': 'held' if reasons else 'present',
            'sourceFields': fields, 'holdReasons': reasons}


def read_generated_menu(db, group, *, database_sha256, admission_sha256,
                        max_members=8, max_rows=2000, max_bytes=1048576,
                        max_steps=1000000, max_seconds=3):
    """Resolve a generated sidecar using a caller-owned, selected RO connection.

    The caller must establish admission and verify the snapshot bytes first;
    query_snapshot does that for file callers. This function never selects a run,
    claims source menu evidence, or transfers/combines recipe nutrients.
    The connection is exclusively owned for the call, including its progress
    handler. A bound failure raises; no partial menu is returned.
    """
    _require(_sha(database_sha256) and _sha(admission_sha256), 'unselected-snapshot')
    for value, ceiling in [(max_members, 16), (max_rows, 10000),
                           (max_bytes, 2097152), (max_steps, 2000000)]:
        _require(type(value) is int and 1 <= value <= ceiling, 'invalid-limit')
    _require(type(max_seconds) in (int, float) and math.isfinite(max_seconds)
             and 0 < max_seconds <= 10, 'invalid-limit')
    _bounded_json(group)
    _require(type(group) is dict and set(group) == {
        'schemaVersion', 'id', 'title', 'origin', 'selectionOrigin', 'snapshot', 'members'}, 'group-schema')
    _require(group['schemaVersion'] == GROUP_VERSION
             and group['origin'] == 'APPLICATION_CREATED'
             and group['selectionOrigin'] == 'GENERATED', 'generated-origin-required')
    _require(type(group['id']) is str and re.fullmatch(
        r'application-menu:[A-Za-z0-9][A-Za-z0-9._:-]{0,100}', group['id']) is not None,
        'application-menu-id-required')
    _require(type(group['title']) is str and 1 <= len(group['title'].strip()) <= 200,
             'application-title-required')
    snapshot = {'databaseSha256': database_sha256, 'admissionSha256': admission_sha256}
    _require(group['snapshot'] == snapshot, 'group-snapshot-mismatch')
    members = group['members']
    _require(type(members) is list and 1 <= len(members) <= max_members, 'member-limit')
    seen = set()
    for member in members:
        _require(type(member) is dict and set(member) in (
            {'recipeEntityId'}, {'recipeEntityId', 'nativeRunId'}), 'member-schema')
        _require(_sha(member['recipeEntityId']), 'recipe-entity-id-required')
        _require(member['recipeEntityId'] not in seen, 'duplicate-recipe-reference')
        seen.add(member['recipeEntityId'])
        if 'nativeRunId' in member:
            _require(type(member['nativeRunId']) is str and re.fullmatch(
                'recipe-actions:[0-9a-f]{64}', member['nativeRunId']) is not None, 'native-run-id-required')
    _require(db.execute('PRAGMA query_only').fetchone()[0] == 1, 'read-only-connection-required')
    remaining, source_bytes, ticks = max_rows, 0, 0
    deadline = time.monotonic() + max_seconds

    def progress():
        nonlocal ticks
        ticks += 100
        return ticks > max_steps or time.monotonic() > deadline

    def query(sql, args=()):
        nonlocal remaining, source_bytes
        _require(time.monotonic() <= deadline, 'query-resource-limit')
        cur = db.execute('SELECT * FROM (' + sql + ') LIMIT ?', (*args, remaining + 1))
        columns = [x[0] for x in cur.description]
        result = []
        for row in cur:
            _require(remaining > 0, 'query-row-limit')
            source_bytes += sum(len(x.encode()) if type(x) is str else
                                len(x) if type(x) is bytes else 8 for x in row)
            _require(source_bytes <= 8388608, 'query-source-byte-limit')
            remaining -= 1
            result.append(dict(zip(columns, row)))
        return result

    def output_bound():
        _require(len(encoded(out)) <= max_bytes, 'menu-output-limit')

    out = {'schemaVersion': RESULT_VERSION, 'id': group['id'], 'title': group['title'],
           'origin': 'APPLICATION_CREATED', 'selectionOrigin': 'GENERATED',
           'snapshot': snapshot, 'members': [], 'sourceMenuEvidence': None,
           'actualUserSelection': False, 'mealSuitabilityQualified': False,
           'combinedNutrition': None, 'nutritionTotals': None,
           'automaticPlanning': False, 'physicalCookingObserved': False,
           'purpose': 'Private attributed generated grouping of source-backed recipe references only',
           'unknowns': ['meal-suitability', 'combined-nutrition', 'servings-and-scaling',
                        'actual-user-selection', 'whole-menu-executability'],
           'limits': {'members': max_members, 'rows': max_rows, 'outputBytes': max_bytes,
                      'sqliteSteps': max_steps, 'seconds': max_seconds}}
    old_length = db.setlimit(sqlite3.SQLITE_LIMIT_LENGTH,
                             min(db.getlimit(sqlite3.SQLITE_LIMIT_LENGTH), 1048576))
    db.set_progress_handler(progress, 100)
    try:
        for member in members:
            eid = member['recipeEntityId']
            rows = query('SELECT * FROM gold_entities WHERE entity_id=?', (eid,))
            _require(len(rows) == 1 and (rows[0]['domain'], rows[0]['entity_type'], rows[0]['state'])
                     == ('recipes', 'recipe', 'verified'), 'missing-or-foreign-recipe-reference')
            entity = rows[0]
            payload = json.loads(entity['payload_json'])
            _require(payload.get('id') == entity['resource_id'], 'recipe-resource-binding')
            texts = query("SELECT * FROM gold_texts WHERE entity_id=? AND state='verified' ORDER BY text_id", (eid,))
            names = {x.get('id'): x for x in payload.get('names', []) if type(x) is dict}
            origins = query('SELECT o.* FROM gold_occurrences o JOIN gold_entity_occurrences x '
                            'ON x.occurrence_id=o.occurrence_id WHERE x.entity_id=? ORDER BY o.occurrence_id', (eid,))
            _require(origins and all(x['state'] == 'verified' for x in origins), 'recipe-source-occurrence-required')
            source_records = []
            citation_ids = set(payload.get('citationIds', []))
            for origin in origins:
                original = json.loads(origin['payload_json'])
                _require(entity['resource_id'] in original.get('resource_ids', []), 'recipe-occurrence-binding')
                citation_ids.update(original.get('citation_ids', []))
                source_records.append({k: origin[k] for k in ['occurrence_id', 'source_key', 'source_version',
                                      'record_id', 'content_sha256', 'normalized_artifact_sha256']} |
                                      {'sourceOriginal': original.get('source_original')})
            _require(citation_ids and len(citation_ids) <= 64
                     and all(type(cid) is str and cid for cid in citation_ids), 'recipe-citations-required')
            citations = []
            for cid in sorted(citation_ids):
                cite = query('SELECT payload_json FROM gold_citations WHERE citation_id=?', (cid,))
                _require(len(cite) == 1, 'missing-recipe-citation')
                value = json.loads(cite[0]['payload_json'])
                _require(value.get('id') == cid, 'recipe-citation-binding')
                citations.append(value)
            # A name can be qualified by a citation distinct from its resource.
            # Preserve that text's complete provenance, not only its display string.
            citation_cache = {c['id']: c for c in citations}
            english, name_records = [], []
            for text in texts:
                name = names.get(text['source_text_id'], {})
                reasons, name_citations, support_records = [], [], []
                if not (type(text['original_text']) is str
                        and name.get('value') == text['original_text']
                        and name.get('sourceTextSha256') == hashlib.sha256(text['original_text'].encode()).hexdigest()
                        and type(text.get('language')) is str and text['language']
                        and name.get('language') == text['language']
                        and type(text['english_text']) is str and text['english_text'].strip()):
                    reasons.append('name-text-binding-unqualified')
                try:
                    evidence = json.loads(text['evidence_json']) if text.get('evidence_json') is not None else None
                except (ValueError, TypeError):
                    evidence = None
                    reasons.append('name-evidence-invalid')
                cids = name.get('citationIds')
                if not (type(cids) is list and 1 <= len(cids) <= 64
                        and all(type(cid) is str and cid for cid in cids)
                        and len(set(cids)) == len(cids)):
                    reasons.append('name-citation-ids-unqualified')
                    cids = []
                for cid in cids:
                    if cid not in citation_cache:
                        rows = query('SELECT payload_json FROM gold_citations WHERE citation_id=?', (cid,))
                        try:
                            citation_cache[cid] = json.loads(rows[0]['payload_json']) if len(rows) == 1 else None
                        except (ValueError, TypeError):
                            citation_cache[cid] = None
                    citation = citation_cache[cid]
                    if type(citation) is not dict or citation.get('id') != cid:
                        reasons.append('name-citation-missing-or-invalid')
                    elif not all(type(citation.get(k)) is str and citation[k].strip()
                                 for k in ['license', 'attribution']):
                        reasons.append('name-citation-rights-unknown')
                    else:
                        name_citations.append(citation)
                    supports = query('SELECT * FROM gold_support WHERE target_kind=\'text\' '
                                     'AND target_id=? AND citation_id=? '
                                     "AND support_scope IN ('field','translation')", (text['source_text_id'], cid))
                    valid = [s for s in supports if _sha(s['evidence_sha256'])]
                    if not valid:
                        reasons.append('name-support-missing-or-invalid')
                    support_records.extend(valid)
                status = 'held' if reasons else 'qualified'
                name_records.append({'status': status, 'holdReasons': sorted(set(reasons)),
                    'sourceName': name, 'textRecord': text, 'evidence': evidence,
                    'citations': name_citations, 'supportRecords': support_records})
                if status == 'qualified':
                    english.append(text['english_text'])
                    existing = {c['id'] for c in citations}
                    for citation in name_citations:
                        if citation['id'] not in existing:
                            citations.append(citation)
                            existing.add(citation['id'])
                    _require(len(citations) <= 64, 'recipe-citation-limit')
            runs = query('SELECT * FROM gold_recipe_runs WHERE recipe_entity_id=? ORDER BY run_id', (eid,))
            selected = next((x for x in runs if x['run_id'] == member.get('nativeRunId')), None)
            _require('nativeRunId' not in member or selected is not None, 'missing-or-foreign-native-run')
            instructions, instruction_records, native = [], [], None
            instruction_state = 'unknown-no-run-selected'
            if selected is not None:
                _require(selected['source_occurrence_id'] in {x['occurrence_id'] for x in origins}
                         and selected['target_language'] == 'en'
                         and selected['status'] == 'ready-for-review', 'native-run-source-language-binding')
                actions = query('SELECT * FROM gold_recipe_actions WHERE run_id=? ORDER BY sequence_index',
                                (selected['run_id'],))
                _require(actions and all(type(x['english_text']) is str and x['english_text'].strip()
                                         for x in actions), 'native-english-instructions-required')
                pins_valid = _native_pins_valid(selected)
                for action in actions:
                    reasons, action_citations = [], []
                    if not pins_valid:
                        reasons.append('native-run-pins-unqualified')
                    evidence = _parsed_json(action.get('evidence_json'))
                    if not _action_evidence_valid(evidence, action):
                        reasons.append('action-evidence-invalid')
                    supports = query('SELECT * FROM gold_recipe_action_support WHERE run_id=? '
                                     'AND action_id=? ORDER BY citation_id',
                                     (selected['run_id'], action.get('action_id')))
                    if not supports:
                        reasons.append('action-support-missing')
                    support_evidence = []
                    for support in supports:
                        parsed = _parsed_json(support.get('evidence_json'))
                        support_evidence.append(parsed)
                        if not _action_evidence_valid(parsed, action) or parsed != evidence:
                            reasons.append('action-support-evidence-invalid')
                        cid = support.get('citation_id')
                        if not (type(cid) is str and cid.strip()):
                            reasons.append('action-citation-missing-or-invalid')
                            continue
                        if cid not in citation_cache:
                            rows = query('SELECT payload_json FROM gold_citations WHERE citation_id=?', (cid,))
                            citation_cache[cid] = _parsed_json(rows[0]['payload_json']) if len(rows) == 1 else None
                        citation = citation_cache[cid]
                        if type(citation) is not dict or citation.get('id') != cid:
                            reasons.append('action-citation-missing-or-invalid')
                        elif not all(type(citation.get(k)) is str and citation[k].strip()
                                     for k in ['license', 'attribution']):
                            reasons.append('action-citation-rights-unknown')
                        else:
                            action_citations.append(citation)
                    status = 'held' if reasons else 'qualified'
                    instruction_records.append({'status': status, 'holdReasons': sorted(set(reasons)),
                        'actionRecord': action, 'evidence': evidence, 'supportRecords': supports,
                        'supportEvidence': support_evidence, 'citations': action_citations})
                    if status == 'qualified':
                        existing = {c['id'] for c in citations}
                        for citation in action_citations:
                            if citation['id'] not in existing:
                                citations.append(citation)
                                existing.add(citation['id'])
                        _require(len(citations) <= 64, 'recipe-citation-limit')
                qualified = all(r['status'] == 'qualified' for r in instruction_records)
                if qualified:
                    instructions = [x['english_text'] for x in actions]
                instruction_state = 'selected-native-run' if qualified else 'held-action-provenance'
                graph = {}
                for key, table, order in (
                        ('dependencies', 'gold_recipe_dependencies', 'action_sequence,dependency_sequence'),
                        ('ingredients', 'gold_recipe_ingredients', 'action_id,slot_name'),
                        ('ingredientSupport', 'gold_recipe_ingredient_support', 'action_id,slot_name,citation_id'),
                        ('materials', 'gold_recipe_materials', 'producer_sequence,material_id'),
                        ('materialSupport', 'gold_recipe_material_support', 'material_id,citation_id'),
                        ('materialInputs', 'gold_recipe_material_inputs', 'action_sequence,material_id'),
                        ('materialInputSupport', 'gold_recipe_material_input_support', 'action_id,material_id,citation_id')):
                    # Fixed table/order literals only; every row and byte is charged
                    # to the existing SQL budget, including support/graph metadata.
                    graph[key] = query('SELECT * FROM ' + table + ' WHERE run_id=? ORDER BY ' + order,
                                       (selected['run_id'],))
                for support in graph['ingredientSupport'] + graph['materialSupport'] + graph['materialInputSupport']:
                    cid = support.get('citation_id')
                    if cid not in citation_cache:
                        rows = query('SELECT payload_json FROM gold_citations WHERE citation_id=?', (cid,))
                        citation_cache[cid] = _parsed_json(rows[0]['payload_json']) if len(rows) == 1 else None
                    citation = citation_cache[cid]
                    _require(type(citation) is dict and citation.get('id') == cid
                             and all(type(citation.get(k)) is str and citation[k].strip()
                                     for k in ('license', 'attribution')), 'native-graph-citation-required')
                    if cid not in {c['id'] for c in citations}:
                        citations.append(citation)
                    _require(len(citations) <= 64, 'recipe-citation-limit')
                native = {'run': selected, 'actions': actions, 'graph': graph,
                          'meaning': 'Exact selected admitted records; instructionState controls display qualification. Retain scope and unknown parameters. No whole-recipe automation acceptance.'}
            holds = query('SELECT hold_id,target_kind,target_id,reason FROM gold_holds '
                          'WHERE target_id IN (?,?,?) ORDER BY hold_id',
                          (eid, entity['resource_id'], member.get('nativeRunId', '')))
            out['members'].append({'recipeEntityId': eid, 'recipeResourceId': entity['resource_id'],
                'englishNames': english, 'englishNameState': 'present' if english else 'unknown',
                'nameRecords': name_records,
                'instructions': instructions, 'instructionState': instruction_state,
                'instructionRecords': instruction_records,
                'native': native, 'availableNativeRunIds': [x['run_id'] for x in runs],
                'sourceRecords': source_records, 'citations': citations,
                'sourceScope': payload.get('scope'), 'holds': holds,
                'recipeNutrition': None, 'userSelected': False})
            output_bound()
        out['limits'].update(rowsRead=max_rows - remaining, sourceBytesRead=source_bytes,
                             maxSourceBytes=8388608, sqliteStepsUpperBound=ticks + 99)
        output_bound()
        return out
    except (sqlite3.Error, json.JSONDecodeError, KeyError, TypeError, RecursionError) as exc:
        raise GeneratedMenuError('snapshot-query-or-payload-invalid') from exc
    finally:
        db.set_progress_handler(None, 0)
        db.setlimit(sqlite3.SQLITE_LIMIT_LENGTH, old_length)


def query_snapshot(admission_path, admission_sha256, group, **limits):
    """Verify an explicitly selected receipt and sealed file, independently of SQL limits."""
    try:
        with verified_snapshot(admission_path, admission_sha256) as access:
            result = read_generated_menu(access.db, group,
                database_sha256=access.database_sha256,
                admission_sha256=admission_sha256, **limits)
            receipt = access.receipt
        result['snapshotVerification'] = access.verification
        result['admissionState'] = receipt['state']
        result['admissionLimits'] = _receipt_limits(receipt)
        qualified = result['admissionLimits']['status'] == 'present'
        result['admissionScopeLimits'] = receipt.get('scopeLimits') if qualified else None
        result['admissionSourceAndConsumerLimits'] = receipt.get('sourceAndConsumerLimits') if qualified else None
        _require(len(encoded(result)) <= limits.get('max_bytes', 1048576), 'menu-output-limit')
        return result
    except SnapshotAccessError as error:
        raise GeneratedMenuError(str(error)) from error


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--admission', required=True)
    parser.add_argument('--admission-sha256', required=True)
    parser.add_argument('--group', required=True)
    args = parser.parse_args()
    try:
        path = Path(args.group)
        _require(path.stat().st_size <= 65536, 'group-byte-limit')
        result = query_snapshot(args.admission, args.admission_sha256, json.loads(path.read_text()))
        print(encoded(result).decode())
        return 0
    except (GeneratedMenuError, ValueError, OSError) as exc:
        print(encoded({'status': 'error', 'error': str(exc)}).decode())
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
