#!/usr/bin/env python3
"""AFCD A2: carry retained derivation conflicts; never replay recovery."""
import argparse
import hashlib
import json
from pathlib import Path

PARENT = 'c7ade2861c92662aa32996ec1b74292dfcd51b56'
PINS = {
    'parent': ('/home/user/src/offmenu-data/normalization-20261015/owner-48/AFCD-A/final/handoff.json', '4f2976184f9e9efd46f8d452c528546bea5c4d027774b6027f3ad8b0982e431d'),
    'review33': ('/home/user/Documents/Codex/2026-10-15/worker33-afcd-c7ade286-review/review-final.json', '56af8024af83e561fbd83d97791633e5b27f6acddfdd7248e86f89ca29f0a86e'),
    'witness19': ('/home/user/Documents/Codex/2026-10-16/task-2/worker19-afcd-F001972-witness/witness.json', '083aad1c88ca69be83333dd20666bf374bb0c404cff3b803595f9acc824d9a9a'),
    'review30': ('/home/user/Documents/Codex/2026-10-16/task-2/worker30-afcd-F001972-review/verdict.json', '1a135c8eecddef438a174b3e0e024493c4046935c5d4ba00e8690560a47609e8'),
    'witness20': ('/home/user/src/offmenu-data/owner20/AFCD-F009464-20261016/witness.json', '7c45ceda0b9d9f42a244a6c101596c7792b9fba77f1ff8bd234b85180bcdc496'),
    'review41': ('/home/user/Documents/Codex/2026-10-16/worker41-afcd-f009464-witness-review/review-receipt.json', '6f3739c68b8c330794d5a64d83b6decb7e38c921b390bda919b47b6d3d2ea954'),
}


def sha(b):
    return hashlib.sha256(b).hexdigest()


def encode(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()


def load_pin(path, digest, locations=None):
    if locations is not None and path not in locations:
        raise ValueError('Missing declared evidence location: ' + path)
    b = Path(locations[path] if locations is not None else path).read_bytes()
    if sha(b) != digest:
        raise ValueError('Evidence pin mismatch: ' + path)
    return json.loads(b)


def evidence(locations=None):
    if locations is None:
        raise ValueError('An explicit evidence location map is required; historical paths are provenance only')
    docs = {name: load_pin(*pin, locations) for name, pin in PINS.items()}
    parent, review = docs['parent'], docs['review33']
    assert parent['commit'] == review['candidate'] == PARENT
    assert review['handoffSHA256'] == PINS['parent'][1]
    assert docs['review30']['witnessSHA256'] == PINS['witness19'][1]
    assert docs['review41']['witnessSHA256'] == PINS['witness20'][1]
    load_pin(review['sourceDisagreements']['evidence'], review['sourceDisagreements']['evidenceSHA256'], locations)
    load_pin(docs['review41']['manifest'], docs['review41']['manifestSHA256'], locations)
    load_pin(parent['manifest_path'], parent['manifest_sha256'], locations)
    load_pin(review['owner56']['freezePath'], review['owner56']['freezeSHA256'], locations)
    cases = {}
    for source in docs['witness19']['observations']:
        cells = {x['cell']: x.get('resolvedValue') for x in source['selectedCells']}
        n = source['row']
        candidate = {'path': source['path'], 'workbook_sha256': source['workbookSHA256'],
                     'sheet': source['sheetName'], 'member': source['worksheetPart'],
                     'row': n, 'cell': 'C' + str(n), 'label': cells['C' + str(n)],
                     'raw_row_sha256': source['rawRowXMLFragmentSHA256']}
        case = cases.setdefault('F001972', {'witness': 'witness19', 'review': 'review30', 'labels': []})
        case['labels'].append(candidate)
        if source['sheetName'] == 'Food details' and 'F' + str(n) in cells:
            case['sampling_statement'] = {'cell': 'F' + str(n), 'text': cells['F' + str(n)],
                                          'source': candidate['path'], 'raw_row_sha256': candidate['raw_row_sha256']}
    for source in docs['witness20']['sourceRows']:
        cells = {x['cell']: x.get('value') for x in source['cells']}
        n = source['row']
        candidate = {'path': source['sourceFile'], 'workbook_sha256': source['workbookSHA256'],
                     'sheet': source['sheet'], 'member': source['member'], 'row': n,
                     'cell': 'C' + str(n), 'label': cells['C' + str(n)], 'raw_row_sha256': source['rawRowSHA256']}
        case = cases.setdefault('F009464', {'witness': 'witness20', 'review': 'review41', 'labels': []})
        case['labels'].append(candidate)
        if source['sheet'] == 'Food details' and 'F' + str(n) in cells:
            case['sampling_statement'] = {'cell': 'F' + str(n), 'text': cells['F' + str(n)],
                                          'source': candidate['path'], 'raw_row_sha256': candidate['raw_row_sha256']}
    for case in cases.values():
        case['evidence'] = {k: {'path': PINS[k][0], 'sha256': PINS[k][1]}
                            for k in [case['witness'], case['review']]}
        case['review_scope'] = 'Completed source-coordinate witness review only; not acceptance of this new packet'
    return docs, cases


def carry_conflict(record, case):
    result = dict(record)
    profile = next(x for x in case['labels'] if x['sheet'] == record['source_sheet'])
    details = next(x for x in case['labels'] if x['sheet'] == 'Food details')
    if (profile['raw_row_sha256'] != record['source_row_xml_sha256']
            or profile['row'] != record['source_row']
            or details['raw_row_sha256'] != record['food_detail_xml_sha256']
            or profile['label'] != record['derivation']):
        raise ValueError('Parent/source witness identity mismatch')
    result['prior_profile_derivation'] = record['derivation']
    result['derivation'] = None
    result['derivation_resolution'] = {'status': 'UNRESOLVED', 'preferred_label': None,
                                       'preferred_source': None, 'unified_nutrient_method_authority': None}
    result['source_derivation_evidence'] = case
    result['parent_record_sha256'] = sha(encode(record))
    return result


def run(output, locations):
    docs, cases = evidence(locations)
    parent, review = docs['parent'], docs['review33']
    delta_pin = next(p for p in parent['normalized_hashes'] if p['path'].endswith('normalization-delta.jsonl'))
    if delta_pin['path'] not in locations:
        raise ValueError('Missing declared parent delta location')
    source = Path(locations[delta_pin['path']])
    if sha(source.read_bytes()) != delta_pin['sha256']:
        raise ValueError('Parent delta pin mismatch')
    output.mkdir(parents=True, exist_ok=False)
    target = output / 'normalization-delta.jsonl'
    count = unchanged = 0
    changed = []
    with source.open('rb') as original, target.open('wb') as destination:
        for line in original:
            record = json.loads(line)
            count += 1
            case = cases.get(record['original_food_id'])
            if case is None:
                destination.write(line)
                unchanged += 1
                continue
            updated = carry_conflict(record, case)
            assert updated['recovered_source_columns'] == record['recovered_source_columns']
            destination.write(encode(updated) + b'\n')
            changed.append(record['original_food_id'])
    if sorted(changed) != ['F001972', 'F009464'] or count != 1801:
        raise ValueError('Unexpected conflict record extent')
    manifest = {'packet': 'AFCD-A2-DERIVATION-CONFLICTS-20261016', 'sourceId': 'afcd', 'release': '3',
                'country': 'AU', 'category': 'generic-ingredient-composition',
                'parent_commit': PARENT, 'parent_delta': delta_pin,
                'input_evidence': {k: {'path': v[0], 'sha256': v[1]} for k, v in PINS.items()},
                'source_disagreement_evidence': review['sourceDisagreements'],
                'rights': parent['rights'], 'change_notice': 'New local sidecar version exposes two source derivation conflicts without preferred label; all recovered values preserved.',
                'counts': {'records': count, 'unchanged_byte_identical_rows': unchanged,
                           'conflicting_unified_derivations': len(changed), 'changed_food_ids': changed,
                           'recovered_observations_preserved': parent['counts']['recovered_source_observations']},
                'output': {'path': str(target), 'bytes': target.stat().st_size, 'sha256': sha(target.read_bytes())},
                'parent_recovery_review': {'verdict': review['verdict'], 'scope': review['scope'], 'reissued': False},
                'owner56_proposal_freeze': review['owner56'], 'independent_new_delta_acceptance': None,
                'review_reservation': 'Owner33 after this frozen packet; no duplicate review started',
                'semantic_gold': False, 'translated_acceptance': False, 'admission': False,
                'unified_derivation_authority': 'UNRESOLVED for F001972/F009464; no winner or per-nutrient analytical authority inferred',
                'recovery_rerun': False, 'new_acquisition': False, 'canonical_writes': False,
                'blockers': ['New independent delta review pending; proposal freeze is not semantic acceptance.']}
    (output / 'manifest.json').write_bytes(encode(manifest) + b'\n')
    return manifest


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--evidence-map', type=Path, required=True,
                        help='JSON mapping historical evidence identities to declared file locations; relative values resolve beside this map')
    args = parser.parse_args()
    locations = {k: str((args.evidence_map.resolve().parent / v).resolve())
                 for k, v in json.loads(args.evidence_map.read_text()).items()}
    print(json.dumps(run(args.output, locations), indent=2))
