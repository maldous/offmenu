#!/usr/bin/env python3
"""Owner51 selected packet A: qualify retained MEXT normalization, no acquisition.

The old full projection is an input by reference. Only unresolved source-lexical,
field-mapping and semantic qualification evidence is emitted to a new namespace.
"""
import argparse
import gzip
import hashlib
import io
import json
import os
from pathlib import Path
import subprocess
import types
import xml.etree.ElementTree as ET
import zipfile
from collections import Counter

BASE = 'f6cb92aef52a5cc8193717d7e794556bd84f8b3b'
ADAPTER = '8b7a5edb8412c8f3e2573ac99faef203e61fd969'
LEGACY = Path('/home/user/src/offmenu-data/mext-2023-main/normalized.jsonl.gz')
MANIFEST = LEGACY.with_name('manifest.json')
LEGACY_SHA = 'cd8af4f89b8f54b2db54d38c807999ce55f2374d9c4140db7d525c2bb5cfe3d1'
DEFAULT_OUTPUT = Path('/home/user/src/offmenu-data/owner-51/DATA-NORMALIZE-20261015-A-OWNER51')


def sha(b):
    return hashlib.sha256(b).hexdigest()


def canon(x):
    return json.dumps(x, ensure_ascii=False, sort_keys=True, separators=(',', ':'))


def git_blob(commit, path):
    env = {k: v for k, v in os.environ.items() if not k.startswith('GIT_')}
    env['GIT_OPTIONAL_LOCKS'] = '0'
    return subprocess.check_output(['git', 'show', commit + ':' + path], env=env)


def pin_file(p):
    b = p.read_bytes()
    return {'path': str(p), 'bytes': len(b), 'sha256': sha(b)}


def adapter():
    m = types.ModuleType('immutable_mext_source_adapter')
    code = git_blob(ADAPTER, 'scripts/global-data-validation/worker-51.py')
    exec(compile(code, ADAPTER + ':worker-51.py', 'exec'), m.__dict__)
    return m, sha(code)


def provenance_ok(record, m):
    p = record.get('provenance', {})
    d = record.get('data', {})
    return (p.get('sourceId') == 'mext' and p.get('releaseId') == m.RELEASE
            and p.get('archiveSha256') == m.SHA256 and record.get('countries') == ['JP']
            and p.get('recordId') == record.get('id', '').rsplit(':', 1)[-1]
            and d.get('identifiers') == [{'system': 'JP-MEXT', 'value': p.get('recordId')}]
            and d.get('basis') == {'amount': 100, 'unit': 'g', 'state': 'as-described', 'portion': 'edible portion'})


def build(output):
    output = Path(output)
    if output.exists():
        raise ValueError('Existing packet: do not overwrite or duplicate a pending task')
    m, adapter_sha = adapter()
    m._trusted_workbook()  # Exact original + release/acquisition manifests; no network.
    legacy_bytes = LEGACY.read_bytes()
    if sha(legacy_bytes) != LEGACY_SHA:
        raise ValueError('Retained full normalization changed; independent reconciliation required')
    old = {}
    excluded = []
    with gzip.open(io.BytesIO(legacy_bytes), 'rt', encoding='utf-8') as f:
        for line in f:
            records = json.loads(line)
            if len(records) != 1:
                raise ValueError('Unexpected retained wrapper')
            r = records[0]
            code = r.get('provenance', {}).get('recordId')
            if code in old:
                raise ValueError('Duplicate retained source record')
            if provenance_ok(r, m):
                old[code] = r
            else:
                excluded.append({'id': r.get('id'), 'reason': 'provenance/release/hash/ID/basis mismatch'})
    contract_bytes = git_blob(BASE, 'corpus/common-data-contract.json')
    schema_bytes = git_blob(BASE, 'corpus/common-data.schema.json')
    contract = json.loads(contract_bytes)
    rows, unknowns, unit_conflicts, label_conflicts = [], Counter(), [], []
    raw = m.WORKBOOK.read_bytes()
    with zipfile.ZipFile(io.BytesIO(raw)) as z:
        member = 'xl/worksheets/sheet1.xml'
        blob = z.read(member)
        member_sha = m.digest(blob)
        strings, _ = m._trusted_workbook()
        headers, definitions, seen = {}, None, set()
        for _, el in ET.iterparse(io.BytesIO(blob), events=('end',)):
            if el.tag != '{' + m.NS['s'] + '}row':
                continue
            row = int(el.get('r'))
            cells = m.cells(el, strings)
            if row <= 12:
                headers[row] = cells
                if row == 12:
                    definitions = m.schema_from_headers(headers)
            elif (code := cells.get('B' + str(row))) and m.re.fullmatch(r'\d{5}', code):
                if code in seen:
                    raise ValueError('Duplicate original code')
                seen.add(code)
                if code not in old:
                    el.clear()
                    continue
                source = m.adapt(cells, row, '表全体', member, definitions, member_sha)
                source['source'].update(basisHeaderCell='D2', basisHeaderLexical=headers[2]['D2'])
                m.roundtrip(source)  # Also binds schema/member/header against trusted original.
                prior = old[code]
                if source['labels']['ja'] != prior['data']['foodName']:
                    label_conflicts.append(code)
                    excluded.append({'id': prior['id'], 'reason': 'original label mismatch'})
                    el.clear()
                    continue
                observations = []
                nutrients = {x['sourceComponent'].strip(): x for x in prior['data']['nutrients'].values()}
                for x in source['components']:
                    unknowns[x['qualifier']] += 1
                    code_component = x['componentCode']
                    if code_component in nutrients and nutrients[code_component]['unit'] != x['unit']:
                        unit_conflicts.append({'foodCode': code, 'component': code_component,
                                               'before': nutrients[code_component]['unit'], 'source': x['unit']})
                    observations.append({'sourceComponent': code_component, 'sourceCell': x['sourceCell'],
                                         'sourceLexical': x['sourceLexical'], 'valueDecimal': x['valueDecimal'],
                                         'qualifier': x['qualifier'], 'sourceUnit': x['unit'],
                                         'sourceUnitHeaderCell': x['unitHeaderCell'], 'basis': x['basis'],
                                         'method': x['method'],
                                         'propertyProposal': 'urn:offmenu:property:source-field:mext:' + code_component,
                                         'semanticStatus': 'source-specific; no nutrient equivalence accepted'})
                rows.append({'sourceId': 'mext', 'release': m.RELEASE, 'country': 'JP', 'category': 'composition',
                             'legacyRecordRef': prior['id'], 'legacyInputSha256': LEGACY_SHA,
                             'sourceCode': code, 'labels': source['labels'], 'form': source['form'],
                             'basis': source['basis'], 'provenance': source['source'],
                             'observations': observations, 'unmappedSourceCells': source['unmappedCells'],
                             'translationAccepted': False, 'semanticGold': False, 'admitted': False})
            el.clear()
    if len(seen) != 2538 or len(old) + len(excluded) < 2538:
        raise ValueError('Full release identity reconciliation failed')
    if set(old) - seen:
        raise ValueError('Legacy records absent from pinned original')
    english = {'01001': 'Amaranth, whole grain', '06001': 'Artichoke, flower bud, raw',
               '06002': 'Artichoke, flower bud, boiled', '09001': 'Sea lettuce, dried',
               '13001': 'Raw milk, Jersey cattle'}
    proposals = [{'sourceCode': r['sourceCode'], 'sourceJapaneseLabel': r['labels']['ja'],
                  'sourceRow': r['provenance']['row'], 'sourceCellsSha256': r['provenance']['recordCellsSha256'],
                  'englishProposal': english[r['sourceCode']], 'authority': 'author proposal, not publisher English label',
                  'status': 'unreviewed; frozen ontology and independent semantic acceptance required',
                  'identityOrNutrientEquivalence': False} for r in rows if r['sourceCode'] in english]
    output.mkdir(parents=True, exist_ok=False)
    target = output / 'source-qualification-delta.jsonl.gz'
    data = ''.join(canon(r) + '\n' for r in rows).encode('utf-8')
    target.write_bytes(gzip.compress(data, mtime=0))
    (output / 'english-mapping-proposals.json').write_text(json.dumps(proposals, ensure_ascii=False, indent=2) + '\n')
    inputs = [pin_file(m.WORKBOOK), pin_file(MANIFEST), pin_file(LEGACY), pin_file(m.ACQUISITION)]
    receipt = {'packetId': 'DATA-NORMALIZE-20261015-A-OWNER51', 'sourceId': 'mext', 'release': m.RELEASE,
               'country': 'JP', 'category': 'composition', 'owner': 51, 'selectedBase': BASE,
               'dedup': 'reused retained 2538-record normalization by reference; new output is unresolved qualification sidecar only',
               'inputHashes': inputs, 'rights': {'policyUrl': 'https://www.mext.go.jp/b_menu/1351168.htm',
                 'claim': 'MEXT use rules; attribution/modification notices and excluded-content scope retained from prior evidence',
                 'evidence': {'commit': '17275322a1a99a925364b321fca8dfbc6d8fed0a', 'path': 'docs/dataset-discovery/worker-15/receipt.json',
                              'sha256': sha(git_blob('17275322a1a99a925364b321fca8dfbc6d8fed0a', 'docs/dataset-discovery/worker-15/receipt.json'))},
                 'independentlyClearedPublication': False},
               'reusedAdapter': {'commit': ADAPTER, 'path': 'scripts/global-data-validation/worker-51.py', 'sha256': adapter_sha},
               'reusedReview': {'finding': 'W10-MEXT-F1', 'ownerFix': ADAPTER,
                               'status': 'owner provenance fix retained; no independent successor acceptance inferred'},
               'normalizedOutput': pin_file(target), 'uncompressedJsonlSha256': sha(data),
               'counts': {'originalFoodRows': len(seen), 'retainedNormalizedInputRows': len(old),
                          'qualificationRows': len(rows), 'provenanceRejectedOrExcluded': len(excluded),
                          'componentObservations': sum(len(r['observations']) for r in rows)},
               'rejectedOrUnknown': {'excludedRecords': excluded, 'componentQualifiers': dict(unknowns),
                                     'unitConflicts': unit_conflicts, 'labelConflicts': label_conflicts,
                                     'analyticalMethods': 'not independently established; source table notation retained'},
               'ontology': {'referenceCommit': BASE, 'contractSha256': sha(contract_bytes), 'schemaSha256': sha(schema_bytes),
                            'frozenOwner56OntologyHash': None, 'freezeStatus': 'pending/unavailable; reference hashes are not frozen acceptance'},
               'mappingProposals': pin_file(output / 'english-mapping-proposals.json'),
               'resourceTypesProposed': [x for x in ['SourceRecord', 'FoodCompositionObservation', 'UnmappedSourceFact'] if x in contract['types']],
               'review': 'independent semantic review pending exact output hashes and frozen ontology hash',
               'blockers': ['Owner56 exact frozen ontology hash unavailable', 'Independent semantic/English acceptance pending',
                            'Primary rights capture/publication scope not independently cleared',
                            'Canonical food/preparation/component equivalence and measurement methods unresolved'],
               'sourceRequests': 0, 'rawOriginalsOverwritten': False, 'canonicalMasterOverwritten': False,
               'semanticGold': False, 'translatedAcceptance': False, 'admitted': False, 'production': 'STOP'}
    (output / 'manifest.json').write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + '\n')
    return receipt


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output', type=Path, default=DEFAULT_OUTPUT)
    args = p.parse_args()
    result = build(args.output)
    print(json.dumps({'output': str(args.output), 'counts': result['counts'],
                      'unknown': result['rejectedOrUnknown']['componentQualifiers'],
                      'unitConflicts': len(result['rejectedOrUnknown']['unitConflicts']),
                      'normalizedSha256': result['normalizedOutput']['sha256']}))
