"""Read-only queries over one frozen completed application; no normalization run.

Only the explicitly selected product may dereference its existing retained row.
All other observations expose completed decisions, never new corpus reads.
"""
import argparse
from collections import Counter
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path('/home/user/src/offmenu-data/runtime/layout-migration')
APPLICATION_ROOT = ROOT / 'worker57/exact19-retained225-application-20261026'
REGISTRY_ROOT = ROOT / 'worker00/coherent-typed-capture-auth-revision-20261025/vocabulary-source-catalogue-batch/local-reviewed-registry'
VERSION_ROOT = REGISTRY_ROOT / 'versions/offmenu-local-reviewed-vocabulary-20261026-v1'
PINS = {
    'applicationResult': (APPLICATION_ROOT / 'result.json', 'acb9b797844460a1615a8665a0dc577e07dc19fafc67bc3251d0cbf40b696a58'),
    'application': (APPLICATION_ROOT / 'registry-application.jsonl', 'b0a1dab7f989115d71ba8b7d02acceadafd433c95fa1a1b31ee0cada54c21acc'),
    'registry': (VERSION_ROOT / 'registry.json', 'bd94d9fb4029eb3470e330d8331683208fb83e22665edf46ca7fea2de8c7ef15'),
    'disposition': (REGISTRY_ROOT / 'application-dispositions/worker57-exact19-retained225-scoped-result-disposition-20261026.json', '3f7d69bb264fa57798a5249dfbbf3583aa8eaf5f7fd894acfd5b49dbeec16700'),
}
SELECTED_PRODUCT = 'off:product:0009300000277'
SELECTED_SOURCE = {
    'file': str(ROOT / 'worker56/rich-product-local-projection-20261026/selected-225-expansion/local-projection-225/products.jsonl'),
    'fileSha256': '0eb0e8a634ff4bfc0bee0c5d2d91960e73adaed252766004431b073a8d40e129',
    'line': 1,
    'lineSha256': 'd99ade18005fa05f8b27a3edb3d138dacff015f7fd4608a745d1caad0bd57b80',
}
UNKNOWN_VALUES = 'not-in-completed-application; original source absence not established'


def digest(data):
    return hashlib.sha256(data).hexdigest()


def encode(value):
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False) + '\n').encode('utf-8')


def read_pinned(path, expected):
    data = path.read_bytes()
    if digest(data) != expected:
        raise ValueError('input-pin-mismatch: ' + str(path))
    return data


def load_completed():
    blobs = {key: read_pinned(path, sha) for key, (path, sha) in PINS.items()}
    registry = json.loads(blobs['registry'])
    rows = [json.loads(line) for line in blobs['application'].splitlines()]
    result = json.loads(blobs['applicationResult'])
    counts = Counter(d['applicationStatus'] for row in rows for d in row['decisions'])
    if len(rows) != 225 or sum(counts.values()) != 2526 or counts != {
        'preexisting-contract-unit-candidate-retained': 1086,
        'projected-unit-format-reference': 6, 'unresolved': 1434,
    }:
        raise ValueError('completed-application-scope-mismatch')
    if result['counts']['newCanonicalIdentityMappings'] != 0:
        raise ValueError('unexpected-canonical-mapping')
    for row in rows:
        if row['registrySHA256'] != PINS['registry'][1] or row['GoldAdmission'] or row['newCanonicalMappings']:
            raise ValueError('unexpected-application-qualification')
        for decision in row['decisions']:
            scoped_units(decision, registry)
    refs = {key: {'path': str(path), 'sha256': sha} for key, (path, sha) in PINS.items()}
    return rows, registry, refs


def scoped_units(decision, registry):
    """Expose accepted notation relations only; do not apply aliases again."""
    if decision['applicationStatus'] != 'projected-unit-format-reference':
        if decision.get('targets'):
            raise ValueError('unexpected-new-semantic-edge')
        return []
    if decision['domain'] != 'unit' or decision.get('originalSourceUnitQualification'):
        raise ValueError('unexpected-unit-qualification')
    targets = deepcopy(decision['targets'])
    if not targets:
        raise ValueError('missing-projected-reference')
    for target in targets:
        pointer = target['mappingPointer']
        if not pointer.startswith('/mappings/'):
            raise ValueError('invalid-registry-pointer')
        mapping = registry['mappings'][int(pointer.split('/')[-1])]
        if (mapping != target['reviewedMappingVerbatim'] or
            mapping['originalAlias'] != decision['sourceValueEvidence'] or
            mapping['targetId'] != target['id']):
            raise ValueError('reference-does-not-match-exact-reviewed-alias')
    return targets


def selected_retained(row):
    """One allowlisted existing row, not an original225 processing pass."""
    if row['sourceRecordId'] != SELECTED_PRODUCT:
        return None
    if row['originalSource'] != SELECTED_SOURCE:
        raise ValueError('selected-source-reference-mismatch')
    with Path(SELECTED_SOURCE['file']).open('rb') as handle:
        line = handle.readline()
    if digest(line) != SELECTED_SOURCE['lineSha256']:
        raise ValueError('selected-line-pin-mismatch')
    source = json.loads(line)
    if source['id'] != SELECTED_PRODUCT or source['kind'] != 'product':
        raise ValueError('selected-source-identity-mismatch')
    return source


def observation(row, line_number, registry, application_sha, retained=None):
    decisions = deepcopy(row['decisions'])
    evidence = []
    for decision in decisions:
        role = ('product-label' if decision['sourcePointer'].startswith('/data/name') else
                'opaque-declaration-placeholder' if decision['sourcePointer'] == '/data/ingredientsText' else
                decision['domain'])
        evidence.append({
            'candidateId': decision['candidateId'], 'role': role,
            'sourcePointer': decision['sourcePointer'], 'verbatim': decision['sourceValueEvidence'],
            'sourceLanguage': decision['sourceLanguage'],
            'codepoints': None if not isinstance(decision['sourceValueEvidence'], str) else
                ['U+%04X' % ord(c) for c in decision['sourceValueEvidence']],
            'status': decision['applicationStatus'], 'reason': decision['reason'],
            'permittedScopedUnitReferences': scoped_units(decision, registry),
        })
    units = [x for x in evidence if x['role'] == 'unit']
    nutrients = [{
        'sourcePointer': x['sourcePointer'], 'verbatimLabel': x['verbatim'],
        'sourceLanguage': x['sourceLanguage'], 'mappingStatus': x['status'],
        'amount': None, 'amountStatus': UNKNOWN_VALUES, 'basis': None,
        'unitEvidence': [u for u in units if u['sourcePointer'] in
                         (x['sourcePointer'] + '/unit', x['sourcePointer'] + '/unit/notation')],
    } for x in evidence if x['role'] == 'nutrient']
    out = {
        'observationRef': 'urn:offmenu:completed-application-observation:' + application_sha + ':' + str(line_number),
        'applicationLine': line_number, 'sourceRecordId': row['sourceRecordId'], 'sourceKind': row['sourceKind'],
        'originalSource': deepcopy(row['originalSource']),
        'retainedEvidence': deepcopy(row['retainedEvidence']),
        'decisionsVerbatim': decisions, 'fieldEvidence': evidence,
        'ingredientDeclarations': [], 'permittedIngredientEdges': [], 'recipeEdges': [], 'profileEdges': [],
        'supportedQuantityValues': [], 'quantityStatus': UNKNOWN_VALUES,
        'nutrientFields': nutrients, 'supportedNutrientValues': [],
        'chainStatus': 'UNRESOLVED_NOT_CHAIN_DELIVERY',
        'missingFields': ['explicit qualified ingredient identity and source sense',
                          'explicit ingredient-to-recipe edge with reviewed quantities/yield',
                          'qualified product-to-profile edge and nutrient amount/unit/basis'],
        'canonicalMappings': 0, 'GoldAdmission': False,
    }
    if retained is not None:
        data = retained['data']
        declaration = data.get('fieldEvidence', {}).get('ingredientDeclaration', {})
        text = data.get('ingredientsText')
        if declaration.get('state') == 'present' and isinstance(text, str) and declaration.get('sourceValue') == text:
            out['ingredientDeclarations'].append({
                'relation': 'retained-product-declares-opaque-text; NOT normalized ingredient identity',
                'sourcePointer': '/data/ingredientsText', 'verbatim': text,
                'language': None, 'languageStatus': 'not established for this ingredient declaration',
                'fieldEvidenceVerbatim': deepcopy(declaration), 'termEdges': [],
                'unmappedReason': 'No retained structured ingredient IDs/token spans/source-sense qualification; no substring/case/translation inference.',
            })
        out['retainedProductFacts'] = {
            key: deepcopy(data.get(key)) for key in [
                'identifiers', 'name', 'nameLanguage', 'names', 'sourceLanguageFields',
                'ingredientConcepts', 'ingredientInterpretation', 'ingredientMappingStatus',
                'nutritionId', 'nutritionLinkStatus', 'nutritionSourceBasis', 'serving']
        }
        out['retainedProvenanceVerbatim'] = deepcopy(retained['provenance'])
        out['retainedQuantityEvidence'] = deepcopy(data.get('fieldEvidence', {}).get('sourceQuantity'))
        out['missingFields'].append('ingredient declaration language and reviewed structured ingredient spans/IDs')
        out['readScope'] = 'ONE selected retained product line; no retained profile/recipe/body traversal'
    else:
        out['readScope'] = 'completed application only; originalSource and retainedEvidence not dereferenced'
    return out


def query(rows, registry, refs, record_id, retained=None):
    if retained is not None and retained['id'] != record_id:
        raise ValueError('retained-row-does-not-match-query')
    found = [observation(row, i, registry, refs['application']['sha256'], retained)
             for i, row in enumerate(rows, 1) if row['sourceRecordId'] == record_id]
    return {
        'schemaVersion': 'offmenu.completed-normalization-query/1',
        'visibility': 'private-local', 'sourcePins': deepcopy(refs),
        'query': {'sourceRecordId': record_id, 'match': 'exact; no normalization or variant merge'},
        'scope': {'completedObservations': len(rows), 'matchedOccurrences': len(found),
                  'retainedProductRowsOpened': 1 if retained is not None and found else 0,
                  'notFoundMeaning': 'only this frozen completed application; no source-wide absence claim'},
        'observations': found,
        'registryExtension': {'candidateMappings': [], 'status': 'NO_SUPPORTED_EXTENSION_FROM_THIS_EVIDENCE',
                              'reason': 'Product labels and opaque declarations do not qualify ingredient concepts; source language/spans/sense and recipe edges missing.'},
        'chainStatus': 'UNRESOLVED_NOT_CHAIN_DELIVERY',
        'limits': 'No new mapping, alias application, tokenization, source acquisition, bulk normalization, nutrient conversion, recipe inference, public export or runtime adoption.',
    }


def catalog(rows, refs):
    ingredient_fields = [d for row in rows for d in row['decisions'] if d['domain'] == 'ingredient']
    return {
        'schemaVersion': 'offmenu.completed-normalization-catalog/1', 'visibility': 'private-local',
        'sourcePins': refs,
        'counts': {'observations': len(rows), 'kinds': dict(sorted(Counter(r['sourceKind'] for r in rows).items())),
                   'decisions': sum(len(r['decisions']) for r in rows),
                   'statuses': dict(sorted(Counter(d['applicationStatus'] for r in rows for d in r['decisions']).items())),
                   'ingredientDomainFields': len(ingredient_fields),
                   'nonNullProductLabelEvidence': sum(d['sourceValueEvidence'] is not None and d['sourcePointer'].startswith('/data/name') for d in ingredient_fields),
                   'opaqueDeclarationPlaceholders': sum(d['sourcePointer'] == '/data/ingredientsText' for d in ingredient_fields)},
        'observations': [{'applicationLine': i, 'sourceRecordId': row['sourceRecordId'], 'sourceKind': row['sourceKind'],
                          'observationRef': 'urn:offmenu:completed-application-observation:' + refs['application']['sha256'] + ':' + str(i)}
                         for i, row in enumerate(rows, 1)],
        'unmatchedIngredientDomainEvidence': [{
            'sourceRecordId': row['sourceRecordId'], 'applicationLine': i,
            'originalSource': deepcopy(row['originalSource']),
            'retainedEvidence': deepcopy(row['retainedEvidence']),
            'role': 'opaque-declaration-placeholder' if d['sourcePointer'] == '/data/ingredientsText' else 'product-label',
            'decisionVerbatim': deepcopy(d),
        } for i, row in enumerate(rows, 1) for d in row['decisions'] if d['domain'] == 'ingredient'],
        'limits': 'Label candidates are not ingredient-bearing records. Opaque null placeholders are not source absence. No retained source rows opened by catalog.',
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--record')
    group.add_argument('--barcode', choices=['0009300000277'], help='only the explicitly selected retained product; exact identifier, leading zeroes preserved')
    group.add_argument('--catalog', action='store_true')
    args = parser.parse_args()
    rows, registry, refs = load_completed()
    if args.catalog:
        result = catalog(rows, refs)
    else:
        record_id = SELECTED_PRODUCT if args.barcode else args.record
        matches = [row for row in rows if row['sourceRecordId'] == record_id]
        retained = selected_retained(matches[0]) if matches else None
        if args.barcode and not any(i.get('system') == 'barcode' and i.get('value') == args.barcode
                                    for i in retained['data'].get('identifiers', [])):
            raise ValueError('selected-explicit-barcode-mismatch')
        result = query(rows, registry, refs, record_id, retained)
        if args.barcode:
            result['query']['barcode'] = args.barcode
            result['query']['barcodeScope'] = 'one selected retained exact identifier; no barcode scan or source-wide lookup'
    sys.stdout.buffer.write(encode(result))


if __name__ == '__main__':
    try:
        main()
    except (ValueError, KeyError, OSError, IndexError) as exc:
        print(json.dumps({'error': str(exc), 'status': 'FAILED_CLOSED'}), file=sys.stderr)
        sys.exit(2)
