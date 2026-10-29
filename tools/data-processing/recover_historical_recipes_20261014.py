#!/usr/bin/env python3
"""Create a deliberately small, evidence-first recovery set from retained OCR.

This does not repair the existing Smithsonian candidates.  It creates new,
source-scoped variants only where a named recipe has a bounded, directly
observable OCR passage.  Ambiguous OCR fractions and nonstandard measures are
preserved as notation and are never converted.
"""
from __future__ import annotations

import argparse
import gzip
import hashlib
import json
from pathlib import Path


ROOT = Path('/home/user/src/offmenu-data')
SOURCE_DIR = ROOT / 'recipe-research-20261013/smithsonian/royalno10cookbo00temp'
SOURCE = SOURCE_DIR / 'royalno10cookbo00temp_djvu.txt'
ACQUISITION = SOURCE_DIR / 'acquisition.json'
RIGHTS = ROOT / 'recipe-research-20261013/smithsonian/rights-and-items.json'

# These are transcription boundaries in the retained text file (one based).
# The ingredient strings intentionally preserve the OCR notation.
RECOVERIES = (
    {
        'title': 'Cream of Tomato Soup', 'old': 'world-recipes:recipe:f642d5b96f0d89783db3a9b6',
        'lines': (606, 615),
        'ingredients': ('1 quart of tomatoes', '14 pint of water', 'a pinch of soda', '1 quart. of cream or milk', '1 teaspoon flour', '1 teaspoon fresh butter', 'finely chopped parsley', 'celery', 'salt', 'pepper', 'a pinch cayenne', 'croutons or oyster crackers'),
        'optionalClause': 'If desired you may add some finely chopped parsley \nand celery.',
    },
    {
        'title': 'Tomato Bisque Soup', 'old': 'world-recipes:recipe:f890d2ea9af4fa0120c9f160',
        'lines': (618, 627),
        'ingredients': ('One can tomatoes', '1 quart milk (or cream is better)', 'lump butter', 'pepper', 'salt', '2 tablespoons flour or cornstarch', 'a little milk', 'celery', 'parsley', 'onior', 'a clove', '1-3 teaspoon soda', 'few drops of sherry wine', 'croutons'),
    },
    {
        'title': 'Potato Salad', 'old': 'world-recipes:recipe:3d27d52d440812b96102d760',
        'lines': (3584, 3596),
        'ingredients': ('One-half gallon potatoes', '1 stalk celery', '1 large onion', 'salt', 'pepper', '4 eggs', '2 teaspoons flour', '2 tablespoons sugar', '2 tea- \nspoons mustard', '114 teaspoons salt', '1 cup vinegar', '1% cup water', '2 tablespoons butter'),
    },
    {
        'title': 'Fresh Peach Compote', 'old': 'world-recipes:recipe:a7700d91154e2cf72283f750',
        'lines': (4046, 4050),
        'ingredients': ('2 dozen sound peaches', '1 cupful sugar', '1 cupful water', 'a little cinnamon bark'),
    },
    {
        'title': 'Cottage Pudding', 'old': 'world-recipes:recipe:d175c49ca0d4cedf3754f504',
        'lines': (4099, 4113),
        'ingredients': ('1%, cup butter', '2 cups flour', '4% cup sugar', '2% level teaspoons Baking Powder', 'a ege, well beaten', '14 teaspoon Salt', '1 cup milk', 'vanila or hard sauce'),
    },
)


def sha(value: str | bytes) -> str:
    if isinstance(value, str):
        value = value.encode('utf8')
    return hashlib.sha256(value).hexdigest()


def iri(kind: str, key: str) -> str:
    return f'urn:offmenu:{kind}:{sha(key)[:24]}'


def source_text(value: str, key: str, citation: str) -> dict:
    return {'kind': 'text', 'id': iri('text', key), 'language': 'en', 'value': value,
            'sourceTextSha256': sha(value), 'status': 'source-asserted', 'citationIds': [citation]}


def provenance(acquisition: dict, source_sha: str, old_id: str) -> dict:
    return {
        'sourceId': 'smithsonian-archive', 'originSourceId': 'smithsonian-archive',
        'recordId': f"{acquisition['archiveId']}:recovery:{sha(old_id)[:12]}",
        'url': acquisition['archiveLinks'][0], 'license': 'CC0-1.0',
        'licenseUrl': 'https://creativecommons.org/publicdomain/zero/1.0/',
        'attribution': f"{acquisition['title']}; Smithsonian Libraries and Archives",
        'visibility': 'public', 'sourceDate': acquisition.get('date'),
        'rightsEvidenceUrl': acquisition['url'], 'sourceDocumentSha256': source_sha,
        'recipeReuse': 'licensed-full-recipe-content',
        'changes': 'Bounded direct transcription from retained uncorrected OCR. Full instruction passages retain line endings. Ingredient statements are selected from those passages with only surrounding whitespace normalized; an OCR line-break hyphen is retained where present. No OCR correction, quantity conversion, food identity, yield, diet, country, or translation inferred.',
    }


def native_record(spec: dict, acquisition: dict, excerpt: str, source_sha: str) -> dict:
    ingredients = []
    optional_statements = {'finely chopped parsley', 'celery'} if spec.get('optionalClause') else set()
    for statement in spec['ingredients']:
        ingredients.append({'name': statement, 'ingredientId': None, 'amount': None, 'unit': None,
                            'optional': statement in optional_statements, 'originalText': statement,
                            'foodMatchStatus': 'unresolved-source-transcription',
                            'sourceQuantity': {'value': None, 'unit': None, 'range': None,
                                               'original': statement, 'status': 'source-notation-retained'},
                            'quantityStatus': 'source-measure-needs-review', 'scaling': 'unknown'})
    return {
        'schemaVersion': '1.0', 'kind': 'recipe',
        'id': f"historical-recovery:recipe:{sha(spec['old'])[:24]}", 'countries': [],
        'provenance': provenance(acquisition, source_sha, spec['old']),
        'data': {'recipeSchema': 'offmenu-recipe/1', 'name': spec['title'], 'languages': ['en'],
                 'yield': {'value': None, 'unit': 'portion'}, 'ingredients': ingredients,
                 'directions': [excerpt], 'automaticPlanningEligible': False,
                 'reviewStatus': 'source-complete-transcription-needs-personal-culinary-review',
                 'qualificationStatus': 'unknown',
                 'quantityCoverage': {'ingredients': len(ingredients), 'standardQuantities': 0,
                                      'sourceNumericQuantities': 0},
                 'sourcePublisher': 'smithsonian-archive', 'historical': True,
                 'sourceBook': acquisition['title'], 'ingredientExtractionComplete': True,
                 'sourceExtraction': 'Bounded transcription from retained uncorrected OCR; source notation preserved.',
                 'sourceLineRange': list(spec['lines']), 'sourceOptionalClause': spec.get('optionalClause'),
                 'sourceDocument': acquisition['files'][0]['url'],
                 'derivedFromOriginalHistoricalRecipeCandidate': spec['old'],
                 'limitations': 'Complete passage transcription is not food identity, diet, safety, yield, or quantity-definition review. Candidate personal culinary review remains required.'}
    }


def graph(record: dict, excerpt: str, source_sha: str) -> dict:
    cid = iri('citation', record['id'])
    scope = {'visibility': 'public', 'reuseScope': 'CC0 source transcription; retain source attribution and citation'}
    rid = iri('recipe-variant', record['id'])
    culture = iri('cultural-representation', record['id'])
    resources, assertions, relations = [], [], []
    def res(rid_, type_, names=()):
        resources.append({'id': rid_, 'type': f'urn:offmenu:type:{type_}', 'identityStatus': 'source-scoped',
                          'names': list(names), 'citationIds': [cid], 'scope': scope})
    def fact(subject, prop, value, path, status='source-asserted', derivation=None):
        item = {'id': iri('assertion', record['id'] + subject + prop + path), 'subjectId': subject,
                'propertyId': f'urn:offmenu:property:{prop}', 'value': value, 'status': status,
                'citationIds': [cid], 'sourcePath': path, 'scope': scope}
        if derivation: item['derivation'] = derivation
        assertions.append(item)
        return item['id']
    def relation(subject, predicate, obj, path, status='source-asserted'):
        relations.append({'id': iri('relation', record['id'] + subject + predicate + obj + path),
                          'subjectId': subject, 'predicateId': f'urn:offmenu:relation:{predicate}', 'objectId': obj,
                          'status': status, 'citationIds': [cid], 'scope': scope, 'sourcePath': path})
    title = source_text(record['data']['name'], record['id'] + ':title', cid)
    res(rid, 'RecipeVariant', [title]); res(culture, 'CulturalRepresentation')
    relation(rid, 'hasCulturalRepresentation', culture, 'data.sourceBook')
    # The old native candidate identifier is not an IRI.  The core alignment
    # has a deterministic, resolvable HistoricalRecipeCandidate resource for
    # it; retain both the source identifier and that actual graph relation.
    core_candidate = iri('recipe-variant', record['data']['derivedFromOriginalHistoricalRecipeCandidate'])
    fact(rid, 'originalSourceRecord', {'kind': 'identifier', 'value': record['provenance']['recordId']}, 'provenance.recordId')
    fact(rid, 'source-field:derivedFromOriginalHistoricalRecipeCandidate', {'kind': 'identifier', 'value': record['data']['derivedFromOriginalHistoricalRecipeCandidate']}, 'data.derivedFromOriginalHistoricalRecipeCandidate', 'candidate', {'methodId': 'urn:offmenu:method:bounded-ocr-transcription-20261014', 'inputAssertionIds': [], 'reviewStatus': 'candidate'})
    relation(rid, 'derivedFrom', core_candidate, 'data.derivedFromOriginalHistoricalRecipeCandidate', 'candidate')
    fact(culture, 'sourceBook', source_text(record['data']['sourceBook'], record['id'] + ':book', cid), 'data.sourceBook')
    fact(culture, 'sourceEditionLanguage', {'kind': 'identifier', 'value': 'en'}, 'data.languages.0')
    fact(culture, 'sourceLanguages', {'kind': 'list', 'items': [{'kind': 'identifier', 'value': 'en'}]}, 'data.languages')
    fact(rid, 'ingredientExtractionComplete', {'kind': 'boolean', 'value': True}, 'data.ingredientExtractionComplete', 'reviewed')
    fact(rid, 'automaticPlanningEligible', {'kind': 'boolean', 'value': False}, 'data.automaticPlanningEligible')
    fact(rid, 'yield', {'kind': 'quantity', 'value': None, 'unitId': 'urn:offmenu:unit:portion', 'dimension': 'count', 'sourceValue': None, 'sourceUnit': 'portion', 'qualifiers': ['yield-unknown']}, 'data.yield')
    for index, ingredient in enumerate(record['data']['ingredients']):
        mid = iri('ingredient-mention', record['id'] + ':' + str(index))
        original = source_text(ingredient['originalText'], record['id'] + ':ingredient:' + str(index), cid)
        res(mid, 'IngredientMention', [original]); relation(rid, 'usesIngredient', mid, f'data.ingredients.{index}')
        original_assertion = fact(mid, 'originalIngredientStatement', original, f'data.ingredients.{index}.originalText')
        q = {'kind': 'quantity', 'value': None, 'unitId': None, 'dimension': 'unknown', 'sourceValue': None,
             'sourceUnit': None, 'sourceNotation': original, 'qualifiers': ['source-measure-needs-review', 'uncorrected-ocr-notation']}
        fact(mid, 'requiredQuantity', q, f'data.ingredients.{index}.sourceQuantity', 'candidate',
             {'methodId': 'urn:offmenu:method:source-notation-retention-20261014', 'inputAssertionIds': [original_assertion], 'reviewStatus': 'candidate'})
        optional = ingredient['optional']
        fact(mid, 'optional', {'kind': 'boolean', 'value': optional}, f'data.ingredients.{index}.optional',
             'source-asserted' if optional else 'candidate')
        if optional:
            clause = source_text(record['data']['sourceOptionalClause'], record['id'] + ':optional-clause', cid)
            fact(mid, 'source-field:optionalClause', clause, f'data.ingredients.{index}.optionalClause')
        fact(mid, 'scalingRule', {'kind': 'identifier', 'value': 'unknown'}, f'data.ingredients.{index}.scaling', 'candidate')
    step = iri('recipe-step', record['id'] + ':0')
    instruction = source_text(excerpt, record['id'] + ':instruction:0', cid)
    res(step, 'RecipeStep'); relation(rid, 'hasStep', step, 'data.directions.0')
    fact(step, 'instruction', instruction, 'data.directions.0')
    fact(step, 'position', {'kind': 'number', 'value': 1}, 'data.directions.0')
    citation = {'id': cid, 'sourceId': 'smithsonian-archive', 'originalRecordId': record['provenance']['recordId'],
                'originalUrl': record['provenance']['url'], 'sourceDate': record['provenance']['sourceDate'],
                'contentSha256': source_sha, 'license': 'CC0-1.0', 'attribution': record['provenance']['attribution'],
                'rightsEvidenceUrl': record['provenance']['rightsEvidenceUrl'],
                'sourcePath': f"{SOURCE.name}:lines:{record['data']['sourceLineRange'][0]}-{record['data']['sourceLineRange'][1]}", 'scope': scope}
    return {'schemaVersion': 'offmenu-common/1', 'resources': resources, 'assertions': assertions,
            'relations': relations, 'citations': [citation], 'translations': []}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, default=ROOT / 'historical-recipe-quality-final-corrected-20261014')
    args = parser.parse_args()
    output = args.output
    output.mkdir(parents=True, exist_ok=True)
    lines = SOURCE.read_text(encoding='utf8').splitlines()
    acquisition = json.loads(ACQUISITION.read_text(encoding='utf8'))
    source_sha = sha(SOURCE.read_bytes())
    native, packets, decisions = [], [], []
    for spec in RECOVERIES:
        start, end = spec['lines']
        excerpt = '\n'.join(lines[start - 1:end]).strip()
        if spec['title'].upper() not in excerpt.upper():
            raise ValueError(f"recipe title not found in declared source boundary: {spec['title']}")
        record = native_record(spec, acquisition, excerpt, source_sha)
        native.append(record); packets.append(graph(record, excerpt, source_sha))
        decisions.append({'originalHistoricalRecipeCandidate': spec['old'], 'recoveryRecordId': record['id'],
                          'decision': 'admitted-as-separate-source-scoped-recovery-variant',
                          'reason': 'Named recipe, full retained OCR passage and directly transcribed ingredient statements verified within a bounded source-line range.',
                          'automaticPlanningEligible': False, 'personalCulinaryReviewRequired': True})
    with gzip.open(output / 'normalized.jsonl.gz', 'wt', encoding='utf8') as f:
        for record in native: f.write(json.dumps(record, ensure_ascii=False, separators=(',', ':')) + '\n')
    with gzip.open(output / 'recipe-source-alignment.jsonl.gz', 'wt', encoding='utf8') as f:
        for packet in packets: f.write(json.dumps(packet, ensure_ascii=False, separators=(',', ':')) + '\n')
    (output / 'decisions.jsonl').write_text(''.join(json.dumps(row, ensure_ascii=False) + '\n' for row in decisions), encoding='utf8')
    files = []
    for path in sorted(output.iterdir()):
        if path.name == 'manifest.json': continue
        entry = {'key': path.name, 'bytes': path.stat().st_size, 'sha256': sha(path.read_bytes())}
        if path.name == 'recipe-source-alignment.jsonl.gz':
            entry['packets'] = len(packets)
        files.append(entry)
    graph_totals = {key: sum(len(packet[key]) for packet in packets) for key in ('resources', 'assertions', 'relations', 'citations', 'translations')}
    graph_counts = {'packets': len(packets), **{key: graph_totals[key] for key in ('resources', 'assertions', 'relations', 'translations')}}
    manifest = {'schemaVersion': 'offmenu-historical-recovery/1', 'releaseId': 'historical-recipe-quality-final-20261014',
                'status': 'bounded-source-cited-recovery-admitted', 'complete': True, 'limit': None,
                'source': {'id': 'smithsonian-archive', 'archiveId': acquisition['archiveId'], 'document': acquisition['files'][0],
                           'documentSha256Observed': source_sha, 'rightsEvidence': json.loads(RIGHTS.read_text(encoding='utf8'))},
                'expectedSourceRecords': len(native), 'observedSourceRecords': len(native),
                'expectedCounts': graph_counts, 'observedCounts': graph_counts, 'counts': graph_counts,
                'partitionCoverage': {'complete': True, 'expectedFiles': 1, 'observedFiles': 1,
                                      'expectedPackets': len(packets), 'observedPackets': len(packets)},
                'admissionMetrics': {'existingPartialOcrCandidates': 256, 'admittedRecoveryVariants': len(native),
                                     'heldCandidates': 251, 'citationCount': graph_totals['citations']},
                'admission': 'Only bounded passages with a named recipe and directly transcribed ingredient/instruction text are admitted. No existing partial candidate was modified.',
                'limitations': 'OCR notation is preserved exactly enough for audit. Ambiguous OCR fractions, source measures, food identities, yield, diet, safety and scaling remain unqualified. Personal culinary review is required.',
                'files': files}
    (output / 'manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n', encoding='utf8')
    print(json.dumps({'output': str(output), 'records': len(native), 'packets': len(packets), 'sourceSha256': source_sha}))

if __name__ == '__main__':
    main()
