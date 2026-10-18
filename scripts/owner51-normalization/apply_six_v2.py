#!/usr/bin/env python3
"""Apply only reviewed six-source annotations into a NEW local version.
No source parsing, acquisition, equivalence, rights grant or calculation authority.
"""
import copy
import gzip
import hashlib
import json
from pathlib import Path

PARENT = Path('/home/user/src/offmenu-data/owner-51/DATA-NORMALIZE-20261015-A-OWNER51')
DELTA = Path('/home/user/src/offmenu-data/owner-51/DATA-NORMALIZE-20261015-A-OWNER51-SIX-DELTA1')
ELIGIBILITY = Path('/home/user/src/offmenu-data/owner-30/JAPAN-SIX-CALCULATION-ELIGIBILITY-20261016-DELTA1')
OUTPUT = Path('/home/user/src/offmenu-data/owner-51/JAPAN-NORMALIZATION-ANNOTATIONS-20261016-V2')
PINS = {
    'parent': '480f18c67f30bf41ddb3f66152c30d02a7690aba5bf422022bf95a5228b62798',
    'deltaManifest': 'd190aee6a904a3cd071763e678c8b6275ac2fe9fa56147d5456c635063a253e4',
    'sidecar': '9dd74eb5dcbaf2c47e11ff3a750914d6669958d5b186528f64edbc82410f10da',
    'binding': 'c4c11c0cae887ff65c25ca663c76457e996a7aa540af406ddc325a5d62578e2f',
    'review': '4bc355245561eb1546ea16cce37acbea8590dde0a901fc402d575fd5bb08ca21',
}


def sha(b):
    return hashlib.sha256(b).hexdigest()


def pinned(path, expected):
    b = Path(path).read_bytes()
    if sha(b) != expected:
        raise ValueError('Input hash mismatch: ' + str(path))
    return b


def key(decision):
    k = decision['observationKey']
    return k['sourceCode'], k['cell'], k['sourceComponent']


def apply(record, decision):
    k, evidence = decision['observationKey'], decision['sourceEvidence']
    if (record['sourceId'], record['release'], record['sourceCode']) != (k['sourceId'], k['release'], k['sourceCode']):
        raise ValueError('Record identity mismatch')
    p = record['provenance']
    if any(p[x] != k[y] for x, y in [('sheet', 'sheet'), ('member', 'member'), ('row', 'row')]):
        raise ValueError('Source coordinates mismatch')
    if record['labels']['ja'] != evidence['originalJapaneseLabel'] or p['memberSha256'] != evidence['memberSha256']:
        raise ValueError('Source evidence mismatch')
    selected = [o for o in record['observations'] if (o['sourceCell'], o['sourceComponent']) == (k['cell'], k['sourceComponent'])]
    if len(selected) != 1:
        raise ValueError('Missing/duplicate observation')
    observation = selected[0]
    if observation['sourceLexical'] != evidence['originalLexical'] or observation['qualifier'] != 'uninterpreted-source-text' or observation['valueDecimal'] is not None:
        raise ValueError('Unexpected pre-annotation observation')
    candidate, eligibility = decision['sourceQualifiedCandidate'], decision['calculationEligibility']
    if candidate['unit'] != observation['sourceUnit'] or candidate['basis'] != observation['basis']:
        raise ValueError('Unit/basis conversion prohibited')
    for field in ['nutritionCalculationEligible', 'unqualifiedNutritionCalculationEligible', 'conversionPerformed', 'fallbackToZeroAllowed', 'referenceSampleSubstitutionAllowed']:
        if eligibility[field] is not False:
            raise ValueError('Calculation exclusion must be explicit false: ' + field)
    if eligibility['calculationValueDecimal'] is not None:
        raise ValueError('Calculation value must remain null')
    if eligibility['basis'] != observation['basis'] or eligibility['unit'] != observation['sourceUnit']:
        raise ValueError('Eligibility basis/unit mismatch')
    if candidate['annotation'] == '*':
        if candidate['valueDecimal'] is not None or candidate['qualifier'] != 'standard-value-deliberately-withheld':
            raise ValueError('Withheld observation must stay null')
    elif candidate['annotation'] == '†':
        if candidate['valueDecimal'] is None or candidate['valueDecimal'] + '†' != observation['sourceLexical'] or candidate['qualifier'] != 'source-measured-prescribed-method':
            raise ValueError('Method-qualified lexical candidate mismatch')
    else:
        raise ValueError('Unsupported annotation')
    observation.update(valueDecimal=candidate['valueDecimal'], qualifier=candidate['qualifier'],
                       annotation=candidate['annotation'], method=candidate['method'],
                       calculationEligibility=copy.deepcopy(eligibility), nutritionCalculationEligible=False,
                       unqualifiedNutritionCalculationEligible=False, calculationValueDecimal=None,
                       reviewedAnnotationSidecarSha256=PINS['sidecar'])


def build(output=OUTPUT):
    output = Path(output)
    if output.exists():
        raise ValueError('New version only: existing output must not be overwritten')
    parent_path = PARENT / 'source-qualification-delta.jsonl.gz'
    parent_bytes = pinned(parent_path, PINS['parent'])
    dm = json.loads(pinned(DELTA / 'manifest.json', PINS['deltaManifest']))
    parent_manifest = json.loads(pinned(PARENT / 'manifest.json', dm['parentManifestSHA256']))
    proposal_pin = parent_manifest['mappingProposals']
    pinned(proposal_pin['path'], proposal_pin['sha256'])
    side_path = ELIGIBILITY / 'calculation-eligibility.json'
    side = json.loads(pinned(side_path, PINS['sidecar']))
    binding = json.loads(pinned(ELIGIBILITY / 'independent-review-binding.json', PINS['binding']))
    if binding['sidecarSha256'] != PINS['sidecar'] or binding['independentReview']['sha256'] != PINS['review']:
        raise ValueError('Review chain mismatch')
    pinned(binding['independentReview']['path'], PINS['review'])
    if dm['parentCandidate'] != side['parentCandidate'] or side['deltaManifest']['sha256'] != PINS['deltaManifest']:
        raise ValueError('Parent/delta mismatch')
    delta_bytes = pinned(side['deltaInput']['path'], side['deltaInput']['sha256'])
    deltas = json.loads(delta_bytes)
    decisions = side['records']
    if len(decisions) != 6 or len({key(x) for x in decisions}) != 6:
        raise ValueError('Exactly six distinct decisions required')
    delta_map = {(x['sourceCode'], x['cell'], x['component']): x for x in deltas}
    for decision in decisions:
        if decision['sourceQualifiedCandidate'] != delta_map[key(decision)]['proposed']:
            raise ValueError('Candidate interpretation differs from accepted delta')
    targets = {x['observationKey']['sourceCode'] for x in decisions}
    tokens = {code: ('"sourceCode":"' + code + '"').encode() for code in targets}
    output.mkdir(parents=True, exist_ok=False)
    new_path = output / 'normalization-v2.jsonl.gz'
    untouched_before, untouched_after = hashlib.sha256(), hashlib.sha256()
    changes, total, untouched, parsed = [], 0, 0, 0
    with gzip.open(parent_path, 'rb') as source, new_path.open('xb') as raw:
        with gzip.GzipFile(filename='', mode='wb', fileobj=raw, mtime=0) as dest:
            for line in source:
                total += 1
                if not any(token in line for token in tokens.values()):
                    dest.write(line); untouched_before.update(line); untouched_after.update(line); untouched += 1
                    continue
                record = json.loads(line); parsed += 1
                original = copy.deepcopy(record)
                for decision in decisions:
                    if record['sourceCode'] == decision['observationKey']['sourceCode']:
                        apply(record, decision)
                        changes.append({'key': decision['observationKey'], 'before': delta_map[key(decision)]['before'],
                                        'after': decision['sourceQualifiedCandidate'], 'calculationEligibility': decision['calculationEligibility']})
                before = {(o['sourceCell'], o['sourceComponent']): o for o in original['observations']}
                for o in record['observations']:
                    if (record['sourceCode'], o['sourceCell'], o['sourceComponent']) not in {key(d) for d in decisions}:
                        if o != before[o['sourceCell'], o['sourceComponent']]:
                            raise ValueError('Non-target observation changed')
                for field in original:
                    if field != 'observations' and original[field] != record[field]:
                        raise ValueError('Non-observation record data changed')
                dest.write((json.dumps(record, ensure_ascii=False, sort_keys=True, separators=(',', ':')) + '\n').encode())
    if len(changes) != 6 or parsed != 4 or total != 2538 or untouched != 2534:
        raise ValueError('Scope/count mismatch')
    if sha(parent_path.read_bytes()) != PINS['parent'] or untouched_before.digest() != untouched_after.digest():
        raise ValueError('Parent or non-target data changed')
    manifest = {'packet': 'JAPAN-NORMALIZATION-ANNOTATIONS-20261016-V2', 'parentCandidate': side['parentCandidate'],
                'parentNormalized': {'path': str(parent_path), 'sha256': PINS['parent']},
                'appliedInputs': {'deltaManifestSha256': PINS['deltaManifest'], 'sidecarPath': str(side_path),
                                  'sidecarSha256': PINS['sidecar'], 'reviewBindingSha256': PINS['binding'],
                                  'independentReview': binding['independentReview']},
                'newNormalization': {'path': str(new_path), 'bytes': new_path.stat().st_size, 'sha256': sha(new_path.read_bytes())},
                'counts': {'rows': total, 'targetRowsParsed': parsed, 'unchangedRowsCopiedVerbatim': untouched,
                           'changedObservations': len(changes), 'methodQualifiedValues': 3, 'withheldIodineNulls': 3,
                           'calculationExcludedObservations': 6},
                'unchangedRowsSha256': untouched_before.hexdigest(), 'changes': changes,
                'holds': {'rights': dm['rights'], 'frozenOntologyHash': dm['frozenOntologyHash'],
                          'EnglishProposals': dm['EnglishProposals'], 'parentOriginalsAndOutputPreserved': True},
                'retainedSourcePinsByReference': parent_manifest['inputHashes'],
                'parentManifestSha256': dm['parentManifestSHA256'], 'unchangedEnglishProposalPin': proposal_pin,
                'reviewRequested': {'reviewer': 20, 'thread': '01a138f8-9d74-75c2-b5f4-b487f610f5e6', 'scope': 'six-observation application delta only'},
                'interpretationScope': 'Operational measurement does not establish intrinsic starch/maltodextrin composition. No conversion/equivalence, calculation, rights or admission authority.',
                'sourceAcquisition': False, 'admitted': False, 'published': False, 'semanticGold': False, 'production': 'STOP'}
    (output / 'manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n')
    return manifest


if __name__ == '__main__':
    print(json.dumps(build(), ensure_ascii=False, indent=2))
