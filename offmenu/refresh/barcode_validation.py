"""Finite, private, deterministic validation; no acquisition or runtime admission.

Inputs are immutable selected snapshots. Optional missing data never invalidates
an identifier. Representation aliases are not physical-product equivalence.
"""
from collections import Counter
from decimal import Decimal, InvalidOperation
import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import re
import stat
import time

VERSION = 'offmenu-barcode-validation/2'


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True,
                      separators=(',', ':'), allow_nan=False).encode()


def digest(value):
    return hashlib.sha256(canonical(value)).hexdigest()


def gtin_valid(value):
    if not isinstance(value, str) or not re.fullmatch(r'(?:[0-9]{8}|[0-9]{12}|[0-9]{13}|[0-9]{14})', value):
        return False
    total = sum(int(c) * (3 if i % 2 == 0 else 1)
                for i, c in enumerate(reversed(value[:-1])))
    return (10 - total % 10) % 10 == int(value[-1])


def upce_expand(value):
    if not isinstance(value, str) or not re.fullmatch(r'[01][0-9]{7}', value):
        return None
    n, a, b, c, d, e, f, k = value
    if f <= '2':
        return n+a+b+f+'0000'+c+d+e+k
    if f == '3':
        return n+a+b+c+'00000'+d+e+k
    if f == '4':
        return n+a+b+c+d+'00000'+e+k
    return n+a+b+c+d+e+'0000'+f+k


def identifier(value, namespace='barcode', symbology=None):
    out = {'originalLexicalValue': value, 'namespace': namespace,
           'sourceSymbology': symbology, 'aliases': [],
           'physicalIdentityEstablished': False, 'reasons': []}
    if namespace == 'USDA-FDC':
        out.update(state='excluded-reference-namespace', reason='not-barcode-identifier')
        return out
    if namespace != 'barcode':
        out.update(state='unresolved', reason='unsupported-namespace')
        return out
    if not isinstance(value, str):
        out.update(state='invalid', reason='identifier-not-lexical-string')
        return out
    if not value or len(value) > 128 or re.search(r'[\x00-\x20\x7f]', value):
        out.update(state='invalid', reason='identifier-lexical-shape')
        return out
    if symbology == 'ISBN-10':
        ok = bool(re.fullmatch(r'[0-9]{9}[0-9X]', value))
        if ok:
            ok = sum((10-i)*(10 if c == 'X' else int(c)) for i, c in enumerate(value)) % 11 == 0
        out.update(state='valid' if ok else 'invalid',
                   reason=None if ok else 'isbn10-checksum-or-shape', type='ISBN-10', editionIdentity='source-asserted-only')
        # ISBN conversion does not establish edition/package equivalence.
        return out
    expected = {'UPC-E': 8, 'UPC-A': 12, 'EAN-8': 8, 'EAN-13': 13,
                'GTIN-14': 14, 'ITF-14': 14, 'ISBN-13': 13}
    if symbology is not None and symbology not in expected:
        out.update(state='unresolved', reason='unsupported-symbology')
        return out
    if symbology and (len(value) != expected[symbology] or not re.fullmatch('[0-9]+', value)):
        out.update(state='invalid', reason='symbology-length-or-characters')
        return out
    expanded = upce_expand(value) if symbology == 'UPC-E' else value
    if not gtin_valid(expanded):
        supported_length = len(value) in (8, 12, 13, 14)
        out.update(state='invalid' if supported_length or symbology else 'unresolved',
                   reason='gtin-checksum-or-shape' if supported_length or symbology else 'untyped-identifier-format')
        return out
    if symbology == 'ISBN-13' and not value.startswith(('978', '979')):
        out.update(state='invalid', reason='isbn13-prefix')
        return out
    out.update(state='valid', reason=None,
               type=symbology or {8:'GTIN-8',12:'GTIN-12',13:'GTIN-13',14:'GTIN-14'}[len(value)],
               packageIdentity='source-asserted-only')
    if expanded != value:
        out['aliases'].append({'value': expanded, 'derivation': 'explicit-upc-e-to-upc-a'})
    if len(expanded) == 12 and symbology in (None, 'UPC-A', 'UPC-E'):
        out['aliases'].append({'value': '0'+expanded, 'derivation': 'upc-a-as-leading-zero-ean-13'})
    if len(expanded) == 13 and expanded[0] == '0' and symbology in (None, 'EAN-13'):
        out['aliases'].append({'value': expanded[1:], 'derivation': 'leading-zero-ean-13-as-upc-a'})
    return out


def nutrient(value, unit=None, basis=None):
    out = {'sourceAmount': value, 'sourceUnit': unit, 'sourceBasis': basis,
           'value': None, 'state': 'unknown'}
    if value is None or value == '':
        out['reason'] = 'missing-or-empty-amount'
        return out
    if isinstance(value, bool) or not isinstance(value, (str, int, float)):
        out['reason'] = 'invalid-amount-type'
        return out
    try:
        number = Decimal(str(value))
        if not number.is_finite() or number < 0 or not math.isfinite(float(number)):
            raise InvalidOperation
    except (InvalidOperation, ValueError):
        out['reason'] = 'trace-not-quantified' if isinstance(value, str) and value.lower() in ('tr', 'trace') else 'invalid-numeric-amount'
        return out
    if unit not in ('g', 'mg', 'µg', 'ug', 'kcal', 'kJ', 'ml', 'IU', '%'):
        out['reason'] = 'unit-unknown-or-unsupported'
        return out
    if not isinstance(basis, dict) or basis.get('unit') not in ('g', 'ml', 'serving'):
        out['reason'] = 'basis-unknown-or-unsupported'
        return out
    amount = basis.get('amount')
    try:
        finite_basis = isinstance(amount, (int, float)) and not isinstance(amount, bool) and math.isfinite(amount) and amount > 0
    except OverflowError:
        finite_basis = False
    if not finite_basis:
        out['reason'] = 'basis-amount-invalid'
        return out
    out.update(state='present', value=str(number), reason=None)
    return out


def field_state(data, key):
    if key not in data:
        return {'state': 'not-projected', 'reason': 'source-absence-not-established'}
    return {'state': 'null' if data[key] is None else 'present', 'value': data[key]}


def normalize_record(record, source_pointer):
    """Consume source-native product, raw OFF row or assertion-only envelope."""
    if not isinstance(record, dict):
        return {'sourcePointer': source_pointer, 'state': 'quarantine', 'reasons': ['record-not-object']}
    data = record.get('data', record)
    provenance = record.get('provenance', {})
    reasons = []
    if not isinstance(data, dict) or not isinstance(provenance, dict):
        return {'sourcePointer': source_pointer, 'state': 'quarantine', 'reasons': ['record-field-shape']}
    raw_identifiers = data.get('identifiers')
    if raw_identifiers is None:
        if 'lexical_value' in data:
            raw_identifiers = [{'value': data['lexical_value'], 'system': data.get('namespace'), 'symbology': data.get('symbology')}]
        elif 'code' in data:
            raw_identifiers = [{'value': data['code'], 'system': 'barcode'}]
    identifiers = []
    if isinstance(raw_identifiers, list):
        for item in raw_identifiers:
            if isinstance(item, dict):
                identifiers.append(identifier(item.get('value'), item.get('system'), item.get('symbology')))
            else:
                reasons.append('identifier-entry-not-object')
    else:
        reasons.append('identifier-list-not-projected-or-invalid')
    barcodes = [i for i in identifiers if i['namespace'] == 'barcode']
    valid = any(i['state'] == 'valid' for i in barcodes)
    unknown = any(i['state'] == 'unresolved' for i in barcodes)
    state = 'lookup-visible' if valid else 'unresolved' if unknown else 'quarantine' if barcodes or reasons else 'excluded-reference-namespace'
    names = {}
    if isinstance(data.get('names'), dict):
        names.update(data['names'])
    for key, value in data.items():
        match = re.fullmatch(r'product_name_([A-Za-z]{2,3}(?:[-_][A-Za-z0-9]+)*)', key)
        if match:
            names[match.group(1)] = value
    language = data.get('lang') or data.get('lc')
    if 'product_name' in data:
        names.setdefault(language if isinstance(language, str) else 'und', data['product_name'])
    # A display name is not evidence of a human-readable upstream name.
    name = field_state(data, 'name')
    # Raw/native string names lack19's consumer-origin evidence. Lexical equality
    # alone must not manufacture its qualified display-warning predicate.
    name['semanticAssessment'] = 'not-established-by-structural-validation'
    nutrients = {}
    source_nutrients = data.get('nutrients')
    if isinstance(source_nutrients, dict):
        for key, item in source_nutrients.items():
            if isinstance(item, dict):
                nutrients[key] = nutrient(item.get('sourceAmount', item.get('value')), item.get('unit'), item.get('basis', data.get('basis')))
            else:
                nutrients[key] = nutrient(item)
    raw_nutrients = data.get('rawNutriments', data.get('nutriments'))
    if isinstance(raw_nutrients, dict):
        for key, value in raw_nutrients.items():
            # Preserve explicit units/basis. Suffix alone is not all-source truth.
            if key.endswith('_100g'):
                unit = 'kcal' if key == 'energy-kcal_100g' else 'kJ' if key == 'energy-kj_100g' else 'g' if key.split('_')[0] in ('proteins','fat','carbohydrates','sugars','fiber','sodium','salt','saturated-fat') else None
                per = data.get('nutrition_data_per', data.get('nutritionSourceBasis'))
                basis = {'amount': 100, 'unit': 'g'} if per == '100g' else {'amount': 100, 'unit': 'ml'} if per == '100ml' else None
                nutrients[key] = nutrient(value, unit, basis)
    categories = data.get('sourceCategoryFields')
    if categories is None:
        categories = {k:v for k,v in data.items() if k in ('categories','categories_tags','categories_hierarchy','food_groups','food_groups_tags')}
    images = []
    # Only an explicitly qualified source metadata list is projected. No fetch.
    for image in data.get('qualifiedImageReferences', []) if isinstance(data.get('qualifiedImageReferences'), list) else []:
        if isinstance(image, dict) and all(image.get(k) for k in ('url', 'sourcePointer', 'rightsEvidenceSha256', 'version')):
            images.append(image)
    return {'version': VERSION, 'sourcePointer': source_pointer,
            'sourceRecordSha256': digest(record), 'sourceRecordId': provenance.get('recordId'),
            'nativeRecordId': record.get('id'), 'provenance': {k:provenance[k] for k in ('sourceId','releaseId','recordId','rightsEvidenceSha256','scopeEvidenceSha256','fetchedAt','acquisitionClock','transform') if k in provenance},
            'state': state, 'reasons': reasons, 'identifiers': identifiers,
            'name': name, 'names': names, 'nameLanguage': language,
            'brand': field_state(data, 'brand' if 'brand' in data else 'brands'),
            'sourceCategories': categories, 'categoryMapping': {'state':'unknown', 'reason':'no-qualified-canonical-crosswalk'},
            'ingredientText': field_state(data, 'ingredientsText' if 'ingredientsText' in data else 'ingredients_text'),
            'ingredientMapping': {'state':'unknown','reason':'opaque-source-text-not-parsed'},
            'foodApplicability': {'state':'unknown','reason':'no-qualified-food-classification'},
            'nutrients': nutrients, 'images': images,
            'imageAvailability': 'qualified-metadata-present' if images else 'not-projected-or-not-qualified',
            'goldAdmitted': False}


def validate_records(records):
    """Retain all observations; repeated barcode assertions are not duplicates."""
    outputs = [normalize_record(record, pointer) for pointer, record in records]
    groups = {}
    for index, row in enumerate(outputs):
        for ident in row.get('identifiers', []):
            value = ident.get('originalLexicalValue')
            if ident.get('state') == 'valid':
                groups.setdefault((ident['namespace'], value), set()).add(index)
    for indexes in groups.values():
        if len(indexes) > 1:
            for index in indexes:
                outputs[index]['collisionDisposition'] = {'state':'ambiguous-source-observations-retained', 'observationCount':len(indexes), 'physicalMerge':False}
    return outputs, summarize_outputs(outputs)


def summarize_outputs(outputs):
    counts = Counter(row['state'] for row in outputs)
    reasons = Counter(reason for row in outputs for reason in row.get('reasons', []))
    for row in outputs:
        reasons.update(i['reason'] for i in row.get('identifiers', []) if i.get('reason'))
        reasons.update(n['reason'] for n in row.get('nutrients', {}).values() if n.get('reason'))
    return {'records':len(outputs), 'dispositions':dict(counts), 'reasonCounts':dict(reasons), 'goldAdmitted':0}


def read_selected_json(operation):
    """One bounded read of an explicitly selected snapshot; no authority discovery."""
    source = operation['source']
    path = Path(source['path'])
    if path.is_symlink() or any(p.is_symlink() for p in path.parents):
        raise ValueError('source-symlink-rejected')
    parent = path.parent.stat()
    if operation.get('privateCustodyRequired') and (parent.st_uid != os.geteuid() or stat.S_IMODE(parent.st_mode) & 0o077):
        raise ValueError('source-parent-not-private-owner-custody')
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    try:
        before = os.fstat(fd)
        identity = [before.st_dev,before.st_ino,before.st_size,before.st_mtime_ns,before.st_ctime_ns]
        if not stat.S_ISREG(before.st_mode) or before.st_size != source['bytes'] or before.st_size > operation['limits']['maxInputBytes']:
            raise ValueError('source-size-or-type-mismatch')
        if operation.get('privateCustodyRequired') and (before.st_uid != os.geteuid() or stat.S_IMODE(before.st_mode) & 0o077):
            raise ValueError('source-file-not-private-owner-custody')
        if source.get('identity') is not None and identity != source['identity']:
            raise ValueError('source-custody-mismatch')
        raw = b''
        while len(raw) <= source['bytes']:
            block = os.read(fd, min(65536, source['bytes']+1-len(raw)))
            if not block:
                break
            raw += block
        after = os.fstat(fd)
        if identity != [after.st_dev,after.st_ino,after.st_size,after.st_mtime_ns,after.st_ctime_ns] or hashlib.sha256(raw).hexdigest() != source['sha256']:
            raise ValueError('source-changed-or-digest-mismatch')
        document = json.loads(raw, parse_constant=lambda x: (_ for _ in ()).throw(ValueError('nonfinite-json')))
        return document, identity
    finally:
        os.close(fd)


def execute(operation, output_root):
    if operation.get('version') != VERSION or operation.get('format') != 'private-native-lookup-json':
        raise ValueError('unsupported-operation-contract')
    if not operation.get('selectionReference'):
        raise ValueError('exact-current-operation-selection-required')
    # The reference is a receipt pointer, not a permission constructor.
    started = time.monotonic()
    key = digest({'operation':operation, 'version':VERSION, 'codeSha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest()})
    output_root = Path(output_root)
    output_root.mkdir(mode=0o700, parents=True, exist_ok=True)
    target = output_root / key
    if target.exists():
        receipt = json.loads((target/'receipt.json').read_text())
        blob = (target/'projection.jsonl').read_bytes()
        if hashlib.sha256(blob).hexdigest() != receipt.get('projectionSha256'):
            raise ValueError('existing-projection-digest-mismatch')
        if len(blob) > operation['limits']['maxOutputBytes']:
            raise ValueError('existing-projection-size-cap')
        outputs = [json.loads(line) for line in blob.splitlines()]
        if (receipt.get('generation') != key or receipt.get('version') != VERSION or
                receipt.get('operationSha256') != digest(operation) or
                receipt.get('source') != operation['source'] or
                receipt.get('counts') != summarize_outputs(outputs) or
                receipt.get('outputBytes') != len(blob) or
                receipt.get('inputBytes') != operation['source']['bytes'] or
                len(outputs) != operation['expectedRecords'] or
                receipt.get('runtimeAdmitted') is not False or
                receipt.get('allHeldInventoryComplete') is not False):
            raise ValueError('existing-projection-receipt-binding-mismatch')
        return {**receipt, 'reused':True}
    document, identity = read_selected_json(operation)
    wrapper = document.get('lookup', document)
    if not isinstance(wrapper, dict) or not isinstance(wrapper.get('matches'), list):
        raise ValueError('lookup-wrapper-shape')
    matches = wrapper['matches']
    if len(matches) != operation['expectedRecords'] or len(matches) > operation['limits']['maxRecords']:
        raise ValueError('selected-record-count-mismatch')
    rows = []
    for index, match in enumerate(matches):
        if not isinstance(match, dict) or not isinstance(match.get('record'), dict):
            raise ValueError('lookup-match-shape')
        row = match['record']
        provenance = row.get('provenance', {})
        if row.get('kind') != 'product' or provenance.get('sourceId') != operation['sourceId'] or provenance.get('releaseId') != operation['releaseId']:
            raise ValueError('selected-source-binding-mismatch')
        for field in ('rightsEvidenceSha256', 'scopeEvidenceSha256'):
            if field in operation and provenance.get(field) != operation[field]:
                raise ValueError('selected-rights-or-scope-binding-mismatch')
        if match.get('nativeProductId') != row.get('id') or match.get('sourceRecordId') != provenance.get('recordId'):
            raise ValueError('selected-observation-binding-mismatch')
        rows.append((('/lookup' if 'lookup' in document else '')+f'/matches/{index}/record', row))
    projected, counts = validate_records(rows)
    blob = b''.join(canonical(row)+b'\n' for row in projected)
    if len(blob) > operation['limits']['maxOutputBytes'] or time.monotonic()-started > operation['limits']['maxSeconds']:
        raise ValueError('selected-operation-budget-exceeded')
    staging = output_root/('.partial-'+key)
    staging.mkdir(mode=0o700)
    try:
        (staging/'projection.jsonl').write_bytes(blob)
        receipt = {'version':VERSION, 'generation':key, 'operationSha256':digest(operation),
                   'source':operation['source'], 'sourceIdentityObserved':identity,
                   'projectionSha256':hashlib.sha256(blob).hexdigest(), 'counts':counts,
                   'elapsedSeconds':time.monotonic()-started, 'inputBytes':operation['source']['bytes'],
                   'outputBytes':len(blob), 'scopeComplete':True, 'allHeldInventoryComplete':False,
                   'runtimeAdmitted':False, 'selectionReference':operation['selectionReference'],
                   'nextAction':'Independent scoped review; expand only exact selected eligible partitions.'}
        (staging/'receipt.json').write_bytes(canonical(receipt)+b'\n')
        for path in staging.iterdir():
            path.chmod(0o600)
        os.rename(staging, target)
    except BaseException:
        # Retain failed staging for diagnosis; never replace a previous generation.
        raise
    return receipt


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--operation', required=True)
    parser.add_argument('--output-root', required=True)
    args = parser.parse_args()
    print(json.dumps(execute(json.loads(Path(args.operation).read_text()), args.output_root), sort_keys=True))


if __name__ == '__main__':
    main()
