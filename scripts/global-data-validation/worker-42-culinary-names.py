"""Read-only source-scoped culinary name assertions. No translation or equivalence."""
import argparse
import gzip
import hashlib
import itertools
import json
from pathlib import Path

# Historical origins are recognized only for these reviewed metadata contents.
CANONICAL_PROVENANCE = {
    'recipe_reference': ('06fe2ac95c41dec5415dfc82d79773559ff553465c4d9140b02e33787e06029a',
                         'reference_commit', '8d468982f7bc905af01d5262c8eabb8db7051e96'),
    'original_proof': ('e064b5dcc205e058922dd5d926759ab98950c25292afb251d055d4e3177d4d81',
                       'original_proof_commit', '6bf021a81d7660ae48b3eeba3656aa656f3553bf'),
}
DEFAULT_EVIDENCE = Path(__file__).resolve().parents[2] / 'docs/global-data-validation/worker-42-culinary-names.json'
LOCALES = {'hi', 'ar', 'cs', 'el', 'fa', 'zh'}


def sha(path):
    with Path(path).open('rb') as f:
        return hashlib.file_digest(f, 'sha256').hexdigest()


def load_inputs(evidence_path):
    """Tracked body-free metadata; retained original files are supplied explicitly."""
    data = Path(evidence_path).read_bytes()
    inputs = json.loads(data)['portable_inputs']
    declared = inputs.get('provenance', {})
    verified, digests = {}, {}
    for section, (expected, key, commit) in CANONICAL_PROVENANCE.items():
        encoded = json.dumps(inputs[section], sort_keys=True, ensure_ascii=False,
                             separators=(',', ':')).encode()
        digests[section] = hashlib.sha256(encoded).hexdigest()
        claim = declared.get(key)
        if claim is not None:
            if digests[section] != expected or claim != commit:
                raise ValueError('Unsupported evidence provenance: ' + key)
            verified[key] = claim
    unsupported = [key for key in declared if key.endswith('_commit') and
                   key not in {value[1] for value in CANONICAL_PROVENANCE.values()}]
    if unsupported:
        raise ValueError('Unsupported evidence provenance: ' + ', '.join(unsupported))
    # Do not trust caller-provided binding fields in a supplied bundle.
    inputs['verified_provenance'] = verified
    inputs['evidence_binding'] = {'sha256': hashlib.sha256(data).hexdigest(),
        'metadata_sha256': digests, 'verified_commit_provenance': verified,
        'verification': 'Only digest-matched reviewed metadata origins; external sources checked separately'}
    return inputs


def source_path(root, relative):
    root = Path(root).resolve()
    path = Path(relative)
    if path.is_absolute() or not path.parts:
        raise ValueError('Evidence source paths must be relative to source_root')
    resolved = (root / path).resolve()
    if not resolved.is_relative_to(root):
        raise ValueError('Evidence source path escapes source_root')
    return resolved


def assertion(row, item, coordinate, concepts, original_body_verified=False):
    p, d = row['provenance'], row['data']
    locales = d.get('languages') or ['und']
    lexeme = item.get('name')
    if not isinstance(lexeme, str):
        lexeme = None
    rights = p.get('license') == 'CC BY-SA 4.0' and bool(p.get('rightsEvidenceUrl'))
    # Exact original Unicode and locale only. No transliteration/fuzzy alias identity.
    candidates = sorted({c['id'] for c in concepts if any(
        t.get('value') == lexeme and t.get('language') in locales for t in c['names'])}) if lexeme else []
    return {'coordinate': coordinate, 'source_id': p.get('originSourceId'),
            'original_record_id': p.get('recordId'), 'revision': p.get('revisionId'),
            'source_content_sha256_claim': p.get('originalContentSha256'),
            'source_url': p.get('url'), 'licence': p.get('license'),
            'rights_evidence_url': p.get('rightsEvidenceUrl'), 'attribution': p.get('attribution'),
            'original_lexeme': lexeme if rights else None, 'source_original_lexeme': None, 'lexeme_status': 'retained normalized name; not original-body verified',
            'original_statement_sha256': hashlib.sha256(item.get('originalText', '').encode()).hexdigest(),
            'locales': locales, 'candidate_concept_ids': candidates,
            'crosswalk_status': 'candidate-only' if candidates else 'unresolved-no-exact-locale-match',
            'ingredient_identity': None, 'culinary_equivalence': None,
            'origin': None, 'automaticPlanningEligible': False,
            'blockers': ([] if rights else ['source-specific-rights-unverified']) +
                        ([] if original_body_verified else ['original-publisher-body-not-verified']),
            'qualification': 'source-scoped-assertion-proposal; independent-review-required'}


def pointer(value, coordinate):
    for token in coordinate.strip('/').split('/'):
        token = token.replace('~1', '/').replace('~0', '~')
        value = value[int(token)] if isinstance(value, list) else value[token]
    return value


def original_proofs(proof, source_root, *, proof_commit=None):
    verified = {}
    for record in proof['records']:
        original, rights = dict(record['original']), dict(record['rights'])
        original['path'] = str(source_path(source_root, original['path']))
        rights['path'] = str(source_path(source_root, rights['path']))
        if sha(original['path']) != original['file_sha256'] or sha(rights['path']) != rights['sha256']:
            raise ValueError('Original body or publisher rights file custody mismatch')
        raw = json.loads(Path(original['path']).read_text())
        body = pointer(raw, original['coordinate'])
        revision_coordinate = original['coordinate'].split('/slots/')[0]
        revision = pointer(raw, revision_coordinate)
        page = pointer(raw, revision_coordinate.split('/revisions/')[0])
        if (hashlib.sha256(body.encode()).hexdigest() != original['body_sha256'] or
                revision['revid'] != original['revisionId'] or revision['timestamp'] != original['timestamp'] or
                str(page['pageid']) != original['recordId']):
            raise ValueError('Original page/revision/body identity mismatch')
        declaration = pointer(json.loads(Path(rights['path']).read_text()), rights['coordinate'])
        if declaration != rights['publisher_declared']:
            raise ValueError('Publisher rights declaration mismatch')
        if sha(original['path']) != original['file_sha256'] or sha(rights['path']) != rights['sha256']:
            raise ValueError('Original custody changed during read')
        c = record['normalized_coordinate']
        verified[(c['line'], c['index'])] = {'proof_commit': proof_commit,
            'language': record['language'], 'source_id': record['provenance']['originSourceId'],
            'original': original, 'rights': rights, 'status': 'exact-body-page-revision-hash-verified; lexeme-crosswalk-review-pending'}
    return verified


def validate_attachment(row, evidence):
    """Bind normalized provenance to the verified publisher witness before using it."""
    p, original = row.get('provenance', {}), evidence['original']
    expected = {
        'originalContentSha256': original['body_sha256'],
        'revisionId': original['revisionId'],
        'recordId': original['recordId'],
        'sourceDate': original['timestamp'],
        'originSourceId': evidence['source_id'],
    }
    if (evidence['source_id'] != 'wikibooks:' + evidence['language'] or
            evidence['language'] not in row.get('data', {}).get('languages', [])):
        raise ValueError('Normalized source locale does not match original proof')
    for field, value in expected.items():
        if p.get(field) != value:
            raise ValueError('Normalized ' + field + ' does not match original proof')


def run(recipe_root, foodon_root, *, source_root, evidence_path=DEFAULT_EVIDENCE):
    inputs = load_inputs(evidence_path)
    reference = inputs['recipe_reference']
    refs = reference['census']['selected_refs'] + reference['census']['representative_source_refs']
    wanted = {(r['line'], r['index']): r for r in refs if set(r['coverage']['language']) & LOCALES}
    if not wanted:
        raise ValueError('Missing Worker53 multilingual held coordinates')
    paths = [recipe_root / 'manifest.json', recipe_root / 'normalized.jsonl.gz',
             foodon_root / 'manifest.json', foodon_root / 'foodon-common.jsonl.gz']
    for p in paths:
        if not p.is_file():
            raise FileNotFoundError('Missing held path: ' + str(p))
    before = [{'path': str(p), 'sha256': sha(p)} for p in paths]
    if before[1]['sha256'] != reference['census']['before_sha256']:
        raise ValueError('Worker53 release hash mismatch')
    manifest = json.loads(paths[2].read_text())
    expected = next(f['sha256'] for f in manifest['files'] if f['key'] == paths[3].name)
    if before[3]['sha256'] != expected or manifest['licence'] != 'CC-BY-4.0':
        raise ValueError('FoodOn rights/release digest mismatch')
    body_proofs = original_proofs(inputs['original_proof'], source_root,
        proof_commit=inputs['verified_provenance'].get('original_proof_commit'))
    concepts = []
    with gzip.open(paths[3], 'rt') as f:
        for line in itertools.islice(f, 1000 - len(wanted) - len(body_proofs)):
            packet = json.loads(line)
            resource = packet['resources'][0]
            if not resource['id'].startswith('http://purl.obolibrary.org/obo/FOODON_'):
                continue
            if not packet['citations'] or any(c.get('license') != 'CC-BY-4.0' or
                    c.get('revisionId') != manifest['revision'] for c in packet['citations']):
                raise ValueError('FoodOn citation qualification missing')
            concepts.append({'id': resource['id'], 'names': resource['names'],
                             'revision': manifest['revision'], 'citationIds': resource['citationIds']})
    assertions, record_pins, found = [], [], set()
    with gzip.open(paths[1], 'rt') as f:
        for line_no, line in enumerate(f, 1):
            indices = [index for number, index in wanted if number == line_no]
            if not indices:
                continue  # Traverse line bytes; parse only selected records' lines.
            rows = json.loads(line)
            for index in indices:
                row = rows[index]
                if row['id'] != wanted[(line_no, index)]['id']:
                    raise ValueError('Retained record coordinate identity mismatch')
                found.add((line_no, index))
                record_pins.append({'id': row['id'], 'line': line_no, 'index': index,
                    'record_sha256': hashlib.sha256(json.dumps(row, sort_keys=True, ensure_ascii=False).encode()).hexdigest()})
                for ingredient_index, item in enumerate(row['data'].get('ingredients', [])):
                    evidence = body_proofs.get((line_no, index))
                    if evidence:
                        validate_attachment(row, evidence)
                    a = assertion(row, item, {'line': line_no, 'index': index,
                        'ingredient_index': ingredient_index}, concepts, bool(evidence))
                    a['original_body_reference'] = evidence
                    if evidence:
                        a['blockers'].append('original-ingredient-lexeme-crosswalk-not-verified')
                    assertions.append(a)
            if found == set(wanted):
                break
    if found != set(wanted):
        raise ValueError('Missing requested retained coordinates')
    after = [{'path': str(p), 'sha256': sha(p)} for p in paths]
    if before != after:
        raise ValueError('Held custody changed')
    return {'worker53_commit': inputs['verified_provenance'].get('reference_commit'),
            'worker56_commit': None, 'evidence_binding': inputs['evidence_binding'],
            'before': before, 'after': after, 'foodon_revision': manifest['revision'],
            'original_body_records': len(body_proofs), 'recipe_records': len(record_pins), 'foodon_records': len(concepts),
            'record_pins': record_pins, 'assertions': assertions,
            'candidate_matches': sum(bool(a['candidate_concept_ids']) for a in assertions),
            'limitations': ['normalized name is not original publisher lexeme verification',
                            'original body and rights must be independently qualified',
                            'FoodOn bounded prefix is not a complete lexical index',
                            'no translation, similar-name identity or locale-to-origin inference'],
            'network_bytes': 0, 'admitted': 0, 'production_recipe_stop': 'preserved'}


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--recipes', type=Path, required=True, help='Retained recipe release directory')
    p.add_argument('--foodon', type=Path, required=True, help='Retained FoodOn release directory')
    p.add_argument('--source-root', type=Path, required=True, help='Root containing metadata-relative original/rights files')
    p.add_argument('--evidence', type=Path, default=DEFAULT_EVIDENCE, help='Body-free pinned input metadata JSON')
    a = p.parse_args()
    print(json.dumps(run(a.recipes, a.foodon, source_root=a.source_root, evidence_path=a.evidence), ensure_ascii=False, indent=2))
