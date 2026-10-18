"""Bounded, read-only structural evidence for an already verified Norway bundle.

This module deliberately has no IO, acquisition, normalization, or candidate path.
The caller must verify pins and its resource sandbox before supplying bytes.
Dictionary labels are public schema evidence; food/source values never leave here.
"""
from __future__ import annotations

from collections import Counter
from decimal import Decimal, InvalidOperation
import hashlib
import json
import math
import re

INPUTS = ('en-foods.json', 'nb-foods.json', 'en-nutrients.json', 'en-sources.json')
MAX_FILE_BYTES = 32 * 1024 * 1024
MAX_BUNDLE_BYTES = 64 * 1024 * 1024
MAX_FOODS = 10000
MAX_DEFINITIONS = 256
MAX_REFERENCES = 4096
MAX_OBSERVATIONS = 1000000
MAX_DEPTH = 40
MAX_TEXT = 4096
MAX_LABEL = 256
MAX_OUTPUT_BYTES = 32 * 1024
MAX_FIELDS = 128
VERSION = 'offmenu-norway-structural-survey/1'
MISSING = object()
TYPES = ('missing', 'null', 'boolean', 'integer', 'number', 'string', 'array', 'object')
TOKEN = re.compile(r'[A-Za-z_][A-Za-z0-9_]{0,63}\Z', re.ASCII)
NUMBER = re.compile(r'[+-]?(?:\d+(?:[.,]\d*)?|[.,]\d+)(?:[eE][+-]?\d+)?\Z', re.ASCII)
CANONICAL = {
    'PROT': ('protein', 'g'), 'FAT': ('fat', 'g'), 'CHO': ('carbohydrate', 'g'),
    'FIBT': ('fibre', 'g'), 'SUGAR': ('sugars', 'g'), 'NA': ('sodium', 'mg'),
    'CA': ('calcium', 'mg'), 'FE': ('iron', 'mg'), 'K': ('potassium', 'mg'),
    'FASAT': ('saturatedFat', 'g'), 'NACL': ('salt', 'g'), 'VITC': ('vitaminC', 'mg'),
}
SEMANTICS = ('absent', 'null', 'blank', 'dash', 'literal-zero', 'numeric', 'trace',
             'ND', 'NT', 'N', 'less-than', 'unresolved', 'invalid')
LEXICAL = ('absent', 'null', 'json-integer', 'json-number', 'boolean', 'object',
           'array', 'blank', 'dash', 'qualifier', 'integer-text', 'decimal-dot',
           'decimal-comma', 'exponent', 'less-than-numeric', 'less-than-invalid',
           'nonfinite-text', 'other-text')
REASONS = frozenset((
    'input-set-mismatch', 'invalid-input-bytes', 'file-size-limit-exceeded',
    'bundle-size-limit-exceeded', 'invalid-json', 'duplicate-json-key',
    'nonfinite-json-number', 'json-number-underflow', 'depth-limit-exceeded',
    'text-limit-exceeded', 'invalid-unicode', 'collection-size-limit-exceeded',
    'observation-limit-exceeded', 'reference-limit-exceeded',
    'schema-field-limit-exceeded', 'output-size-limit-exceeded',
    'dictionary-label-limit-exceeded', 'unsafe-dictionary-label',
    'invalid-source-envelope', 'invalid-source-row', 'empty-food-collection',
    'unsafe-structural-key', 'invalid-native-identity', 'duplicate-native-identity',
    'locale-identity-set-mismatch', 'invalid-food-metadata',
    'invalid-nutrient-definition', 'duplicate-eurofir-identity',
    'canonical-unit-mismatch', 'canonical-component-collision',
    'invalid-constituent-array', 'invalid-constituent-row',
    'missing-nutrient-reference', 'invalid-nutrient-reference',
    'unresolved-nutrient-reference', 'ambiguous-nutrient-reference',
    'duplicate-food-nutrient', 'invalid-observation-unit', 'observation-unit-mismatch',
    'invalid-energy-shape', 'energy-unit-mismatch', 'invalid-source-reference',
    'unresolved-source-reference', 'ambiguous-source-reference',
    'unresolved-quantity', 'invalid-quantity', 'quantity-underflow',
    'nonfinite-quantity', 'explicit-basis-unresolved',
))


class SurveyError(ValueError):
    """An intentionally source-content-free reason code."""


def _kind(value):
    if value is MISSING:
        return 'missing'
    return {type(None): 'null', bool: 'boolean', int: 'integer', float: 'number',
            str: 'string', list: 'array', dict: 'object'}.get(type(value), 'object')


def _increment(counts, key, amount=1):
    counts[key] = counts.get(key, 0) + amount
    if counts[key] > MAX_OBSERVATIONS:
        raise SurveyError('observation-limit-exceeded')


def _counts(keys):
    return dict.fromkeys(keys, 0)


def _held(codes):
    return {'schemaVersion': VERSION, 'country': 'NO', 'status': 'held',
            'evidenceComplete': False, 'candidateGenerationEnabled': False,
            'reasonCodes': sorted(set(codes))}


def _strict_json(raw, *, progress=None, python_scanner=False):
    seen = set()
    def emit(event):
        if progress is not None:
            progress(event)
    def once(event):
        if event in seen:
            return False
        seen.add(event)
        emit(event)
        return True
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise SurveyError('duplicate-json-key')
            result[key] = value
        return result

    def constant(_):
        raise SurveyError('nonfinite-json-number')

    def number(value):
        marked = once('float-hook-entry')
        parsed = float(value)
        marked = once('float-hook-complete') or marked
        if not math.isfinite(parsed):
            raise SurveyError('nonfinite-json-number')
        if parsed == 0:
            marked = once('decimal-zero-entry') or marked
            nonzero = Decimal(value) != 0
            marked = once('decimal-zero-complete') or marked
            if nonzero:
                raise SurveyError('json-number-underflow')
        if marked:
            emit('json-decoder-entry')
        return parsed

    try:
        emit('decode-entry')
        text = raw.decode('utf-8')
        emit('decode-complete')
        emit('depth-scan-entry')
        # Bound nesting before json.loads can recurse. String contents do not count.
        depth = 0
        in_string = escaped = False
        for char in text:
            if in_string:
                if escaped:
                    escaped = False
                elif char == '\\':
                    escaped = True
                elif char == '"':
                    in_string = False
            elif char == '"':
                in_string = True
            elif char in '[{':
                depth += 1
                if depth > MAX_DEPTH:
                    raise SurveyError('depth-limit-exceeded')
            elif char in ']}':
                depth -= 1
        emit('depth-scan-complete')
        emit('json-decoder-entry')
        if python_scanner:
            decoder = json.JSONDecoder(object_pairs_hook=pairs, parse_constant=constant,
                                       parse_float=number)
            decoder.parse_string = json.decoder.py_scanstring
            decoder.scan_once = json.scanner.py_make_scanner(decoder)
            value = decoder.decode(text)
        else:
            value = json.loads(text, object_pairs_hook=pairs, parse_constant=constant,
                               parse_float=number)
        emit('json-decoder-complete')
        emit('structural-walk-entry')
        stack = [(value, 0)]
        while stack:
            item, depth = stack.pop()
            if depth > MAX_DEPTH:
                raise SurveyError('depth-limit-exceeded')
            if isinstance(item, str):
                if len(item) > MAX_TEXT:
                    raise SurveyError('text-limit-exceeded')
                if any(0xD800 <= ord(c) <= 0xDFFF for c in item):
                    raise SurveyError('invalid-unicode')
            elif isinstance(item, dict):
                if len(item) > MAX_FIELDS:
                    raise SurveyError('schema-field-limit-exceeded')
                stack.extend((child, depth + 1) for child in item.values())
                stack.extend((key, depth + 1) for key in item)
            elif isinstance(item, list):
                if len(item) > MAX_OBSERVATIONS:
                    raise SurveyError('observation-limit-exceeded')
                stack.extend((child, depth + 1) for child in item)
        emit('structural-walk-complete')
        return value
    except (UnicodeDecodeError, json.JSONDecodeError, RecursionError, ValueError) as exc:
        if isinstance(exc, SurveyError):
            raise
        raise SurveyError('invalid-json') from None


def _field_hist(rows, holds):
    result = {}
    for row in rows:
        if type(row) is not dict:
            continue
        for key, value in row.items():
            if not TOKEN.fullmatch(key):
                holds.add('unsafe-structural-key')
                continue
            if key not in result:
                if len(result) >= MAX_FIELDS:
                    raise SurveyError('schema-field-limit-exceeded')
                result[key] = {'present': 0, 'types': {}}
            _increment(result[key], 'present')
            _increment(result[key]['types'], _kind(value))
    return result


def _shape(values, holds):
    result = {'count': len(values), 'types': {}, 'fields': _field_hist(values, holds)}
    for value in values:
        _increment(result['types'], _kind(value))
    return result


def _valid_id(value):
    return type(value) is str and bool(value.strip())


def _identity(rows, key, holds, *, optional=False, duplicate_code='duplicate-native-identity'):
    values = [row.get(key, MISSING) if type(row) is dict else MISSING for row in rows]
    types = dict(Counter(_kind(value) for value in values))
    valid = [value for value in values if _valid_id(value)]
    unique = set(valid)
    missing = sum(value is MISSING or value is None for value in values)
    invalid = len(values) - len(valid) - (missing if optional else 0)
    duplicates = len(valid) - len(unique)
    if invalid:
        holds.add('invalid-native-identity')
    if duplicates:
        holds.add(duplicate_code)
    digest = hashlib.sha256(json.dumps(sorted(unique), ensure_ascii=True,
                                       separators=(',', ':')).encode('ascii')).hexdigest()
    return ({'rowCount': len(rows), 'types': types, 'validCount': len(valid),
             'missingCount': missing, 'invalidCount': invalid,
             'uniqueCount': len(unique), 'duplicateCount': duplicates,
             'setSha256': digest}, unique, Counter(valid))


def _label(value, *, optional=False):
    if optional and (value is MISSING or value is None):
        return None
    if type(value) is not str or not value.strip():
        return None
    if len(value) > MAX_LABEL:
        raise SurveyError('dictionary-label-limit-exceeded')
    if not value.isprintable():
        raise SurveyError('unsafe-dictionary-label')
    if '://' in value or value.lower().startswith(('www.', 'mailto:', 'data:')):
        raise SurveyError('unsafe-dictionary-label')
    return value


def _quantities():
    return {'semantics': _counts(SEMANTICS), 'lexicalShapes': _counts(LEXICAL)}


def _quantity(value, out, holds):
    kind = _kind(value)
    sem, lex = 'invalid', kind
    if value is MISSING or value is None:
        sem = lex = 'absent' if value is MISSING else 'null'
    elif type(value) in (int, float):
        sem, lex = ('literal-zero' if value == 0 else 'numeric'), 'json-' + kind
    elif type(value) is str:
        stripped = value.strip()
        upper = stripped.upper()
        if not stripped:
            sem = lex = 'blank'
        elif stripped == '-':
            sem = lex = 'dash'
        elif upper in ('TR', 'TRACE', 'ND', 'NOT DETECTED', 'NT', 'NOT TESTED', 'N'):
            sem = {'TR': 'trace', 'TRACE': 'trace', 'NOT DETECTED': 'ND',
                   'NOT TESTED': 'NT'}.get(upper, upper)
            lex = 'qualifier'
        else:
            less = stripped.startswith('<')
            numeric = stripped[1:].strip() if less else stripped
            if NUMBER.fullmatch(numeric):
                lex = ('less-than-numeric' if less else 'exponent' if 'e' in numeric.lower()
                       else 'decimal-comma' if ',' in numeric else 'decimal-dot'
                       if '.' in numeric else 'integer-text')
                decimal = Decimal(numeric.replace(',', '.'))
                try:
                    binary = float(decimal)
                except (OverflowError, ValueError):
                    binary = float('inf')
                if not math.isfinite(binary):
                    holds.add('nonfinite-quantity')
                elif binary == 0 and decimal != 0:
                    holds.add('quantity-underflow')
                elif less and decimal < 0:
                    holds.add('invalid-quantity')
                else:
                    sem = 'less-than' if less else 'literal-zero' if decimal == 0 else 'numeric'
            else:
                sem = 'unresolved'
                lex = 'less-than-invalid' if less else 'other-text'
                if upper in ('NAN', 'INF', 'INFINITY', '+INF', '-INF', '+INFINITY', '-INFINITY'):
                    sem, lex = 'invalid', 'nonfinite-text'
                    holds.add('nonfinite-quantity')
    if sem == 'invalid':
        holds.add('invalid-quantity')
    if sem == 'unresolved':
        holds.add('unresolved-quantity')
    _increment(out['semantics'], sem)
    _increment(out['lexicalShapes'], lex)


def _walk(value):
    stack = [value]
    while stack:
        item = stack.pop()
        if type(item) is dict:
            yield item
            stack.extend(item.values())
        elif type(item) is list:
            stack.extend(item)


def _basis(documents, holds):
    values = []
    by_input = {}
    for name, document in documents.items():
        found = [obj['basis'] for obj in _walk(document) if 'basis' in obj]
        values.extend(found)
        by_input[name] = len(found)
    forms = _counts(('exact-per100g-edible-as-described', 'other-object', 'non-object'))
    details = {key: _counts(('missing', 'expected', 'other', 'invalid'))
               for key in ('amount', 'unit', 'state', 'portion')}
    expected = {'amount': 100, 'unit': 'g', 'state': 'as-described', 'portion': 'edible portion'}
    for value in values:
        if type(value) is not dict:
            forms['non-object'] += 1
            holds.add('explicit-basis-unresolved')
            continue
        exact = set(value) == set(expected)
        for key, target in expected.items():
            val = value.get(key, MISSING)
            valid = type(val) in (int, float) if key == 'amount' else type(val) is str
            category = ('missing' if val is MISSING else 'invalid' if not valid
                        else 'expected' if val == target else 'other')
            details[key][category] += 1
            exact = exact and category == 'expected'
        forms['exact-per100g-edible-as-described' if exact else 'other-object'] += 1
        if not exact:
            holds.add('explicit-basis-unresolved')
    return {'occurrencesByInput': by_input, 'structure': _shape(values, holds),
            'forms': forms, 'fieldsComparedWithSyntheticContract': details,
            'defaultBasisInferred': False}


def _reference_checks(documents, source_counts, holds):
    result = {}
    all_unique = set()
    for name, document in documents.items():
        checks = _counts(('present', 'null', 'invalid', 'resolved', 'unresolved', 'ambiguous'))
        unique, unresolved = set(), set()
        rows = document.get('sources', []) if name == 'en-sources.json' and type(document) is dict else []
        source_rows = {id(row) for row in rows} if type(rows) is list else set()
        for obj in _walk(document):
            if 'sourceId' not in obj or id(obj) in source_rows:
                continue
            value = obj['sourceId']
            checks['present'] += 1
            if value is None:
                checks['null'] += 1
            elif not _valid_id(value):
                checks['invalid'] += 1
                holds.add('invalid-source-reference')
            else:
                unique.add(value)
                all_unique.add(value)
                count = source_counts[value]
                key = 'resolved' if count == 1 else 'ambiguous' if count > 1 else 'unresolved'
                checks[key] += 1
                if key != 'resolved':
                    holds.add(key + '-source-reference')
                if not count:
                    unresolved.add(value)
            if len(all_unique) > MAX_REFERENCES:
                raise SurveyError('reference-limit-exceeded')
            if checks['present'] > MAX_OBSERVATIONS:
                raise SurveyError('observation-limit-exceeded')
        checks.update(uniqueCount=len(unique), unresolvedUniqueCount=len(unresolved))
        result[name] = checks
    return result


def _observations(foods, definitions, holds, budget):
    observations = []
    references = _counts(('missing', 'invalid', 'resolved', 'unresolved', 'ambiguous',
                          'uniqueReferenced', 'duplicateWithinFood'))
    units = _counts(('absent', 'null', 'matching', 'mismatching', 'invalid', 'unresolved'))
    quantities = _quantities()
    nutrient_ids = set()
    for food in foods:
        if type(food) is not dict:
            continue
        rows = food.get('constituents', MISSING)
        if type(rows) is not list:
            # Locale translations may contain identity/name only: absence is recorded,
            # while an explicit malformed constituents container is held.
            if rows is not MISSING:
                holds.add('invalid-constituent-array')
            continue
        seen = set()
        for row in rows:
            budget[0] += 1
            if budget[0] > MAX_OBSERVATIONS:
                raise SurveyError('observation-limit-exceeded')
            observations.append(row)
            if type(row) is not dict:
                holds.add('invalid-constituent-row')
                continue
            identity = row.get('nutrientId', MISSING)
            definition = None
            if identity is MISSING:
                references['missing'] += 1
                holds.add('missing-nutrient-reference')
            elif not _valid_id(identity):
                references['invalid'] += 1
                holds.add('invalid-nutrient-reference')
            else:
                nutrient_ids.add(identity)
                if len(nutrient_ids) > MAX_REFERENCES:
                    raise SurveyError('reference-limit-exceeded')
                if identity in seen:
                    references['duplicateWithinFood'] += 1
                    holds.add('duplicate-food-nutrient')
                seen.add(identity)
                candidates = definitions.get(identity, [])
                category = 'resolved' if len(candidates) == 1 else 'ambiguous' if candidates else 'unresolved'
                references[category] += 1
                if category == 'resolved':
                    definition = candidates[0]
                else:
                    holds.add(category + '-nutrient-reference')
            unit = row.get('unit', MISSING)
            if unit is MISSING:
                units['absent'] += 1
            elif unit is None:
                units['null'] += 1
                holds.add('invalid-observation-unit')
            elif not _valid_id(unit):
                units['invalid'] += 1
                holds.add('invalid-observation-unit')
            elif definition is None or not _valid_id(definition.get('unit')):
                units['unresolved'] += 1
            elif unit != definition['unit']:
                units['mismatching'] += 1
                holds.add('observation-unit-mismatch')
            else:
                units['matching'] += 1
            _quantity(row.get('quantity', MISSING), quantities, holds)
    references['uniqueReferenced'] = len(nutrient_ids)
    return {'structure': _shape(observations, holds), 'nutrientReferences': references,
            'units': units, 'quantities': quantities}


def _food_structure(foods, holds, budget):
    energy = {}
    for field, unit in (('calories', 'kcal'), ('energy', 'kJ')):
        values = [food.get(field, MISSING) for food in foods if type(food) is dict]
        quantities = _quantities()
        units = _counts(('absent', 'matching', 'mismatching', 'invalid'))
        for value in values:
            if value is MISSING:
                continue
            if type(value) is not dict:
                holds.add('invalid-energy-shape')
                continue
            budget[0] += 1
            if budget[0] > MAX_OBSERVATIONS:
                raise SurveyError('observation-limit-exceeded')
            _quantity(value.get('quantity', MISSING), quantities, holds)
            observed = value.get('unit', MISSING)
            key = 'absent' if observed is MISSING else 'invalid' if not _valid_id(observed) else 'matching' if observed == unit else 'mismatching'
            units[key] += 1
            if key in ('invalid', 'mismatching'):
                holds.add('energy-unit-mismatch')
        energy[field] = {'structure': _shape(values, holds), 'quantities': quantities, 'units': units}
    metadata = {}
    for field in ('portions', 'langualCodes'):
        values = [food.get(field, MISSING) for food in foods if type(food) is dict]
        elements = []
        container_types = dict(Counter(_kind(value) for value in values))
        for value in values:
            if type(value) is list:
                elements.extend(value)
                if len(elements) > MAX_OBSERVATIONS:
                    raise SurveyError('observation-limit-exceeded')
            elif value is not MISSING:
                holds.add('invalid-food-metadata')
        metadata[field] = {'containerTypes': container_types, 'elements': _shape(elements, holds)}
    for food in foods:
        if type(food) is dict:
            for key in ('foodName', 'uri'):
                if key in food and not _valid_id(food[key]):
                    holds.add('invalid-food-metadata')
    return {'energy': energy, 'metadata': metadata}


def _survey(blobs, progress=None, python_scanner=False):
    if type(blobs) is not dict or set(blobs) != set(INPUTS):
        raise SurveyError('input-set-mismatch')
    if any(type(body) is not bytes for body in blobs.values()):
        raise SurveyError('invalid-input-bytes')
    if any(len(body) > MAX_FILE_BYTES for body in blobs.values()):
        raise SurveyError('file-size-limit-exceeded')
    if sum(map(len, blobs.values())) > MAX_BUNDLE_BYTES:
        raise SurveyError('bundle-size-limit-exceeded')
    documents, errors = {}, set()
    for name in INPUTS:
        try:
            if progress is not None:
                progress('parse-entry', name)
            def phase(event):
                if progress is not None:
                    progress(event, name)
            documents[name] = _strict_json(blobs[name], progress=phase, python_scanner=python_scanner)
            if progress is not None:
                progress('parse-complete', name)
        except SurveyError as exc:
            errors.add(str(exc))
    if errors:
        return _held(errors)
    holds = set()
    inputs, collections = {}, {}
    for name in INPUTS:
        document = documents[name]
        array_key = 'nutrients' if name == 'en-nutrients.json' else 'sources' if name == 'en-sources.json' else 'foods'
        value = document.get(array_key, MISSING) if type(document) is dict else MISSING
        if type(document) is not dict or type(value) is not list:
            holds.add('invalid-source-envelope')
        rows = value if type(value) is list else []
        maximum = MAX_DEFINITIONS if array_key == 'nutrients' else MAX_REFERENCES if array_key == 'sources' else MAX_FOODS
        if len(rows) > maximum:
            raise SurveyError('collection-size-limit-exceeded')
        if any(type(row) is not dict for row in rows):
            holds.add('invalid-source-row')
        if array_key == 'foods' and not rows:
            holds.add('empty-food-collection')
        inputs[name] = {'rootType': _kind(document), 'rootFields': _field_hist([document], holds),
                        'collectionType': _kind(value), 'rows': _shape(rows, holds)}
        collections[name] = rows
    identities, sets, frequencies = {}, {}, {}
    for name, key in (('en-foods.json', 'foodId'), ('nb-foods.json', 'foodId'),
                      ('en-nutrients.json', 'nutrientId'), ('en-sources.json', 'sourceId')):
        identities[name], sets[name], frequencies[name] = _identity(collections[name], key, holds)
    identities['euroFirId'], _, _ = _identity(collections['en-nutrients.json'], 'euroFirId', holds,
                                             optional=True, duplicate_code='duplicate-eurofir-identity')
    left, right = sets['en-foods.json'], sets['nb-foods.json']
    comparison = {'sameSet': left == right, 'enOnlyCount': len(left - right), 'nbOnlyCount': len(right - left)}
    if left != right:
        holds.add('locale-identity-set-mismatch')
    definitions, dictionary, mapped = {}, [], Counter()
    mapping = _counts(('mappedDefinitions', 'unmappedDefinitions', 'unitMismatches', 'componentCollisions'))
    for row in collections['en-nutrients.json']:
        if type(row) is not dict:
            continue
        labels = {key: _label(row.get(key, MISSING), optional=key == 'euroFirId')
                  for key in ('nutrientId', 'euroFirId', 'name', 'unit')}
        if any(labels[key] is None for key in ('nutrientId', 'name', 'unit')):
            holds.add('invalid-nutrient-definition')
        if 'euroFirId' in row and row['euroFirId'] is not None and labels['euroFirId'] is None:
            holds.add('invalid-nutrient-definition')
        if _valid_id(row.get('nutrientId')):
            definitions.setdefault(row['nutrientId'], []).append(row)
        component = labels['euroFirId'] or labels['nutrientId']
        target = CANONICAL.get(component)
        state = 'unmapped'
        if target:
            mapped[target[0]] += 1
            mapping['mappedDefinitions'] += 1
            state = 'compatible' if labels['unit'] == target[1] else 'unit-mismatch'
            if state == 'unit-mismatch':
                mapping['unitMismatches'] += 1
                holds.add('canonical-unit-mismatch')
        else:
            mapping['unmappedDefinitions'] += 1
        dictionary.append({**labels, 'canonicalComponent': target[0] if target else None,
                           'canonicalUnit': target[1] if target else None, 'mappingStatus': state})
    mapping['componentCollisions'] = sum(count - 1 for count in mapped.values() if count > 1)
    if mapping['componentCollisions']:
        holds.add('canonical-component-collision')
    dictionary.sort(key=lambda row: tuple(row[key] or '' for key in ('nutrientId', 'euroFirId', 'name', 'unit')))
    observations, structure, budget = {}, {}, [0]
    for locale, name in (('en', 'en-foods.json'), ('nb', 'nb-foods.json')):
        for food in collections[name]:
            if type(food) is not dict:
                continue
            if not _valid_id(food.get('foodName')):
                holds.add('invalid-food-metadata')
            if locale == 'en':
                if not _valid_id(food.get('uri')):
                    holds.add('invalid-food-metadata')
                if 'constituents' not in food:
                    holds.add('invalid-constituent-array')
                for field in ('calories', 'energy'):
                    if field not in food:
                        holds.add('invalid-energy-shape')
                for field in ('portions', 'langualCodes'):
                    if field not in food:
                        holds.add('invalid-food-metadata')
        observations[locale] = _observations(collections[name], definitions, holds, budget)
        structure[locale] = _food_structure(collections[name], holds, budget)
    references = _reference_checks(documents, frequencies['en-sources.json'], holds)
    basis = _basis(documents, holds)
    return {'schemaVersion': VERSION, 'country': 'NO', 'status': 'held' if holds else 'surveyed',
            'evidenceComplete': True, 'candidateGenerationEnabled': False,
            'reasonCodes': sorted(holds), 'inputs': inputs, 'identities': identities,
            'identityComparison': comparison, 'nutrientDictionary': dictionary,
            'canonicalMapping': mapping, 'observations': observations,
            'foodStructure': structure, 'sourceReferences': references, 'explicitBasis': basis}


# Closed report schema. Dynamic maps exist only at declared histogram coordinates;
# no arbitrary value strings, rows, provenance, URLs, or nested pass-through objects.
def _enum(*values):
    return ('enum', values)


def _map(keys, value, maximum):
    return ('map', keys, value, maximum)


def _list(value, maximum):
    return ('list', value, maximum)


_COUNT = ('count',)
_BOOL = ('bool',)
_LABEL = ('label',)
_NULL_LABEL = ('nullable', _LABEL)
_TYPE = _enum(*TYPES)
_TYPE_HIST = _map(_TYPE, _COUNT, len(TYPES))
_FIELD_HIST = _map(('token',), {'present': _COUNT, 'types': _TYPE_HIST}, MAX_FIELDS)
_SHAPE = {'count': _COUNT, 'types': _TYPE_HIST, 'fields': _FIELD_HIST}
_QUANTITY = {'semantics': dict.fromkeys(SEMANTICS, _COUNT), 'lexicalShapes': dict.fromkeys(LEXICAL, _COUNT)}
_IDENTITY = dict.fromkeys(('rowCount', 'validCount', 'missingCount', 'invalidCount', 'uniqueCount', 'duplicateCount'), _COUNT)
_IDENTITY.update(types=_TYPE_HIST, setSha256=('digest',))
_OBS = {'structure': _SHAPE, 'nutrientReferences': dict.fromkeys(('missing', 'invalid', 'resolved', 'unresolved', 'ambiguous', 'uniqueReferenced', 'duplicateWithinFood'), _COUNT),
        'units': dict.fromkeys(('absent', 'null', 'matching', 'mismatching', 'invalid', 'unresolved'), _COUNT), 'quantities': _QUANTITY}
_ENERGY = {'structure': _SHAPE, 'quantities': _QUANTITY, 'units': dict.fromkeys(('absent', 'matching', 'mismatching', 'invalid'), _COUNT)}
_FOOD = {'energy': dict.fromkeys(('calories', 'energy'), _ENERGY),
         'metadata': dict.fromkeys(('portions', 'langualCodes'), {'containerTypes': _TYPE_HIST, 'elements': _SHAPE})}
_BASE_SCHEMA = {'schemaVersion': _enum(VERSION), 'country': _enum('NO'), 'status': _enum('surveyed', 'held'),
                'evidenceComplete': _BOOL, 'candidateGenerationEnabled': _enum(False),
                'reasonCodes': _list(_enum(*sorted(REASONS)), len(REASONS))}
_FULL_SCHEMA = {**_BASE_SCHEMA,
    'inputs': dict.fromkeys(INPUTS, {'rootType': _TYPE, 'rootFields': _FIELD_HIST, 'collectionType': _TYPE, 'rows': _SHAPE}),
    'identities': dict.fromkeys((*INPUTS, 'euroFirId'), _IDENTITY),
    'identityComparison': {'sameSet': _BOOL, 'enOnlyCount': _COUNT, 'nbOnlyCount': _COUNT},
    'nutrientDictionary': _list({**dict.fromkeys(('nutrientId', 'euroFirId', 'name', 'unit'), _NULL_LABEL),
                               'canonicalComponent': _enum(None, *(target[0] for target in CANONICAL.values())),
                               'canonicalUnit': _enum(None, 'g', 'mg'),
                               'mappingStatus': _enum('compatible', 'unit-mismatch', 'unmapped')}, MAX_DEFINITIONS),
    'canonicalMapping': dict.fromkeys(('mappedDefinitions', 'unmappedDefinitions', 'unitMismatches', 'componentCollisions'), _COUNT),
    'observations': dict.fromkeys(('en', 'nb'), _OBS), 'foodStructure': dict.fromkeys(('en', 'nb'), _FOOD),
    'sourceReferences': dict.fromkeys(INPUTS, dict.fromkeys(('present', 'null', 'invalid', 'resolved', 'unresolved', 'ambiguous', 'uniqueCount', 'unresolvedUniqueCount'), _COUNT)),
    'explicitBasis': {'occurrencesByInput': dict.fromkeys(INPUTS, _COUNT), 'structure': _SHAPE,
                      'forms': dict.fromkeys(('exact-per100g-edible-as-described', 'other-object', 'non-object'), _COUNT),
                      'fieldsComparedWithSyntheticContract': dict.fromkeys(('amount', 'unit', 'state', 'portion'), dict.fromkeys(('missing', 'expected', 'other', 'invalid'), _COUNT)),
                      'defaultBasisInferred': _enum(False)}}


def _validate(value, schema):
    if type(schema) is dict:
        if type(value) is not dict or set(value) != set(schema):
            raise SurveyError('invalid-survey-report')
        return {key: _validate(value[key], child) for key, child in schema.items()}
    kind, *args = schema
    if kind == 'enum':
        if not any(type(value) is type(item) and value == item for item in args[0]):
            raise SurveyError('invalid-survey-report')
    elif kind == 'count':
        if type(value) is not int or not 0 <= value <= MAX_OBSERVATIONS:
            raise SurveyError('invalid-survey-report')
    elif kind == 'bool':
        if type(value) is not bool:
            raise SurveyError('invalid-survey-report')
    elif kind == 'digest':
        if type(value) is not str or not re.fullmatch(r'[0-9a-f]{64}', value, re.ASCII):
            raise SurveyError('invalid-survey-report')
    elif kind == 'token':
        if type(value) is not str or not TOKEN.fullmatch(value):
            raise SurveyError('invalid-survey-report')
    elif kind == 'label':
        if type(value) is not str or _label(value) != value:
            raise SurveyError('invalid-survey-report')
    elif kind == 'nullable':
        return None if value is None else _validate(value, args[0])
    elif kind == 'list':
        if type(value) is not list or len(value) > args[1]:
            raise SurveyError('invalid-survey-report')
        return [_validate(child, args[0]) for child in value]
    elif kind == 'map':
        if type(value) is not dict or len(value) > args[2]:
            raise SurveyError('invalid-survey-report')
        return {_validate(key, args[0]): _validate(child, args[1]) for key, child in value.items()}
    else:
        raise SurveyError('invalid-survey-report')
    return value


def sanitize_report(value) -> dict:
    """Revalidate and copy only this closed aggregate schema, or raise SurveyError."""
    if type(value) is not dict or type(value.get('evidenceComplete')) is not bool:
        raise SurveyError('invalid-survey-report')
    result = _validate(value, _FULL_SCHEMA if value['evidenceComplete'] else _BASE_SCHEMA)
    if result['reasonCodes'] != sorted(set(result['reasonCodes'])):
        raise SurveyError('invalid-survey-report')
    if (result['status'] == 'surveyed') != (result['evidenceComplete'] and not result['reasonCodes']):
        raise SurveyError('invalid-survey-report')
    if not result['evidenceComplete'] and not result['reasonCodes']:
        raise SurveyError('invalid-survey-report')
    if len(json.dumps(result, ensure_ascii=True, sort_keys=True, separators=(',', ':'), allow_nan=False).encode('ascii')) > MAX_OUTPUT_BYTES:
        raise SurveyError('output-size-limit-exceeded')
    return result


def survey(blobs: dict[str, bytes], *, progress=None, python_scanner=False) -> dict:
    """Return complete bounded structural evidence, or a content-free fatal hold."""
    try:
        return sanitize_report(_survey(blobs, progress=progress, python_scanner=python_scanner))
    except SurveyError as exc:
        code = str(exc)
        if code not in REASONS:
            raise
        return _held([code])
    except (InvalidOperation, OverflowError, RecursionError):
        return _held(['invalid-json'])
