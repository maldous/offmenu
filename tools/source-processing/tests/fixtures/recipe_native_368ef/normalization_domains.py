"""Small, source-preserving deterministic normalization rules. No I/O or joins.

This is a candidate representation, not a worldwide ontology or a declaration
that source claims are true. Review/translation, custody, caching and gold gates
belong to the normalization engine. Every function is pure and leaves input
objects unchanged. See normalization-rules.json for rule scope and references.
"""
from __future__ import annotations

from copy import deepcopy
from decimal import Decimal, InvalidOperation, localcontext
from fractions import Fraction
import re
from urllib.parse import urlsplit

RULE_VERSION = 'offmenu-domain-normalization/1'
RULE_IDS = ('source-fields-v1', 'gtin-syntax-v1', 'quantity-exact-v1',
            'nutrient-basis-v1', 'ingredient-source-v1', 'supplier-claims-v1',
            'citation-url-v1', 'household-scope-v1', 'identity-link-v1')


def _issue(code, path='', detail=None, severity='warning'):
    return {'code': code, 'severity': severity, 'path': path,
            'detail': detail or code.replace('_', ' ')}


def _pointer(prefix, key):
    return prefix + '/' + str(key).replace('~', '~0').replace('/', '~1')


def _first(row, keys):
    for key in keys:
        if key in row and row[key] is not None and row[key] != '':
            return key, row[key]
    return None, None


def _lineage(target, sources, rule='source-fields-v1', certainty='source_asserted'):
    return {'target_path': target, 'source_paths': sources, 'rule_id': rule,
            'rule_version': RULE_VERSION, 'certainty': certainty}


def _decimal(value):
    # Do not recreate a lexical barcode or decimal from a binary float.
    if isinstance(value, bool) or not isinstance(value, (str, int, Decimal)):
        raise ValueError('quantity_numeric_type_unresolved')
    token = str(value)
    if len(token) > 256 or not re.fullmatch(r'[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?', token):
        raise ValueError('quantity_lexeme_unresolved')
    try:
        number = Decimal(token)
    except InvalidOperation:
        raise ValueError('quantity_lexeme_unresolved') from None
    if not number.is_finite() or abs(number.adjusted()) > 100:
        raise ValueError('quantity_precision_limit')
    return Fraction(number)


def _number(value):
    """Render exact finite decimals; otherwise preserve an exact rational."""
    denominator = value.denominator
    while denominator % 2 == 0:
        denominator //= 2
    while denominator % 5 == 0:
        denominator //= 5
    if denominator != 1:
        return str(value.numerator) + '/' + str(value.denominator), 'rational'
    with localcontext() as ctx:
        ctx.prec = 1024
        result = format(Decimal(value.numerator) / Decimal(value.denominator), 'f')
    result = result.rstrip('0').rstrip('.') if '.' in result else result
    return ('0' if result in ('-0', '') else result), 'decimal'


# Exact factors only. Unit symbols stay case-sensitive (mL is not ML).
_UNITS = {
    'kg': ('mass', 'g', '1000'), 'g': ('mass', 'g', '1'),
    'mg': ('mass', 'g', '.001'), 'µg': ('mass', 'g', '.000001'),
    'μg': ('mass', 'g', '.000001'), 'ug': ('mass', 'g', '.000001'),
    'L': ('volume', 'mL', '1000'), 'l': ('volume', 'mL', '1000'),
    'mL': ('volume', 'mL', '1'), 'ml': ('volume', 'mL', '1'),
    'cL': ('volume', 'mL', '10'), 'cl': ('volume', 'mL', '10'),
    'dL': ('volume', 'mL', '100'), 'dl': ('volume', 'mL', '100'),
    'm³': ('volume', 'mL', '1000000'), 'm^3': ('volume', 'mL', '1000000'),
    'cm³': ('volume', 'mL', '1'), 'cm^3': ('volume', 'mL', '1'),
    'dm³': ('volume', 'mL', '1000'), 'dm^3': ('volume', 'mL', '1000'),
    's': ('time', 's', '1'), 'min': ('time', 's', '60'),
    'h': ('time', 's', '3600'),
    '°C': ('temperature', '°C', '1'), 'K': ('temperature', '°C', '1'),
    '°F': ('temperature', '°C', '1'),
    'J': ('energy', 'J', '1'), 'kJ': ('energy', 'J', '1000'),
}
_UNIT_NAMES = {
    'gram': 'g', 'grams': 'g', 'kilogram': 'kg', 'kilograms': 'kg',
    'milligram': 'mg', 'milligrams': 'mg', 'microgram': 'µg', 'micrograms': 'µg',
    'litre': 'L', 'litres': 'L', 'liter': 'L', 'liters': 'L',
    'millilitre': 'mL', 'millilitres': 'mL', 'milliliter': 'mL', 'milliliters': 'mL',
    'second': 's', 'seconds': 's', 'minute': 'min', 'minutes': 'min',
    'hour': 'h', 'hours': 'h', 'celsius': '°C', 'kelvin': 'K', 'fahrenheit': '°F',
    'joule': 'J', 'joules': 'J', 'kilojoule': 'kJ', 'kilojoules': 'kJ',
}
_AMBIGUOUS_UNITS = frozenset(('cup', 'cups', 'tbsp', 'tablespoon', 'tablespoons',
                             'tsp', 'teaspoon', 'teaspoons', 'oz', 'ounce', 'ounces',
                             'fl oz', 'fluid ounce', 'pint', 'pints', 'gallon', 'gallons'))


def normalize_quantity(value, unit=None, *, locale=None, density_g_per_ml=None,
                       target_unit=None, temperature_kind='absolute'):
    """Exact explicit quantities; no inferred spoon/cup/density/serving factors.

    Output always includes original, issues, status. Normalized output adds
    value or min/max (decimal or rational strings), unit, dimension, exact=true.
    Floats without a separately supplied lexical token remain unresolved.
    Ranges are explicit {min,max} or decimal strings separated by '-'/'–'/'to'.
    Density conversion requires a positive explicit density and target_unit.
    """
    result = {'original': {'value': deepcopy(value), 'unit': deepcopy(unit)},
              'status': 'unresolved', 'issues': [], 'rule_id': 'quantity-exact-v1'}
    if locale is not None:
        result['source_locale'] = deepcopy(locale)
    if isinstance(value, dict) and unit is None and 'unit' in value:
        unit = value['unit']
        value = value.get('value', value)
    if not isinstance(unit, str) or not unit.strip():
        result['issues'].append(_issue('quantity_unit_missing'))
        return result
    token = unit.strip()
    symbol = token if token in _UNITS else _UNIT_NAMES.get(token.casefold())
    if symbol is None:
        code = 'quantity_locale_unit_unresolved' if token.casefold() in _AMBIGUOUS_UNITS else 'quantity_unit_unsupported'
        result['issues'].append(_issue(code))
        return result
    dimension, canonical_unit, factor = _UNITS[symbol]
    if dimension == 'temperature' and temperature_kind not in ('absolute', 'interval'):
        result['issues'].append(_issue('temperature_kind_unresolved'))
        return result
    try:
        if isinstance(value, dict) and set(('min', 'max')).issubset(value):
            values = [_decimal(value['min']), _decimal(value['max'])]
            is_range = True
        elif isinstance(value, str):
            match = re.fullmatch(r'\s*([+-]?(?:\d+(?:\.\d*)?|\.\d+))\s*(?:–|—|-|\bto\b)\s*([+-]?(?:\d+(?:\.\d*)?|\.\d+))\s*', value)
            values = [_decimal(match[1]), _decimal(match[2])] if match else [_decimal(value.strip())]
            is_range = bool(match)
        else:
            values, is_range = [_decimal(value)], False
        if is_range and values[0] > values[1]:
            raise ValueError('quantity_range_reversed')
        if dimension != 'temperature' and any(number < 0 for number in values):
            raise ValueError('quantity_negative_unresolved')
        if dimension == 'temperature':
            if symbol == 'K' and temperature_kind == 'absolute':
                values = [number - Fraction('273.15') for number in values]
            elif symbol == '°F':
                offset = 32 if temperature_kind == 'absolute' else 0
                values = [(number - offset) * Fraction(5, 9) for number in values]
            if temperature_kind == 'absolute' and any(number < -Fraction('273.15') for number in values):
                raise ValueError('temperature_below_absolute_zero')
        else:
            values = [number * Fraction(factor) for number in values]
        if target_unit is not None and target_unit != canonical_unit:
            if (canonical_unit, target_unit) not in (('g', 'mL'), ('mL', 'g')):
                raise ValueError('quantity_target_unsupported')
            if density_g_per_ml is None:
                raise ValueError('quantity_density_required')
            density = _decimal(density_g_per_ml)
            if density <= 0:
                raise ValueError('quantity_density_invalid')
            values = [number / density if canonical_unit == 'g' else number * density for number in values]
            canonical_unit = target_unit
            dimension = 'mass' if target_unit == 'g' else 'volume'
            result['density_basis'] = {'g_per_mL': deepcopy(density_g_per_ml), 'status': 'explicit_source_value_not_independently_verified'}
        rendered = [_number(number) for number in values]
        if is_range:
            result.update(min=rendered[0][0], max=rendered[1][0])
        else:
            result['value'] = rendered[0][0]
        result.update(status='normalized', unit=canonical_unit, dimension=dimension,
                      number_type='rational' if any(kind == 'rational' for _, kind in rendered) else 'decimal', exact=True)
        if symbol in ('K', '°C', '°F'):
            result['temperature_kind'] = temperature_kind
    except (ValueError, TypeError, InvalidOperation) as exc:
        code = str(exc) if str(exc).startswith(('quantity_', 'temperature_')) else 'quantity_value_unresolved'
        result['issues'].append(_issue(code))
    return result


def normalize_gtin(value, namespace=None):
    """Check lexical GTIN syntax only, not allocation, product or ownership."""
    result = {'original': deepcopy(value), 'source_namespace': namespace,
              'status': 'unresolved', 'aliases': [], 'issues': []}
    if not isinstance(value, str):
        result['issues'].append(_issue('barcode_lexical_form_required'))
    elif not re.fullmatch(r'[0-9]+', value):
        result['issues'].append(_issue('barcode_non_ascii_digits'))
    elif len(value) not in (8, 12, 13, 14):
        result['issues'].append(_issue('barcode_length_invalid'))
    elif (sum(int(digit) * (3 if index % 2 == 0 else 1)
              for index, digit in enumerate(reversed(value[:-1]))) + int(value[-1])) % 10:
        result['issues'].append(_issue('barcode_check_digit_invalid'))
    else:
        result.update(lexical=value, gtin14=value.zfill(14),
                      status='syntax_valid_not_registry_verified',
                      aliases=[{'namespace': 'gs1:gtin14', 'value': value.zfill(14),
                                'status': 'syntactic_alias_not_entity_merge'}])
    return result


def normalize_url(value):
    """Lowercase only HTTP(S) scheme and ASCII host; retain every other byte.

    No query stripping/reordering, fragment removal, percent decoding, default
    port removal, redirect fetch, trailing slash change or document equivalence.
    """
    result = {'original': deepcopy(value), 'canonical': None, 'issues': []}
    if not isinstance(value, str) or any(ord(c) <= 32 or ord(c) == 127 for c in value):
        result['issues'].append(_issue('citation_url_unresolved'))
        return result
    try:
        parsed = urlsplit(value)
        match = re.match(r'(?i)^(https?)://([^/?#]*)(.*)$', value)
        if not match or not parsed.hostname or parsed.username is not None or parsed.password is not None:
            raise ValueError()
        # Validate explicit port but retain its lexical spelling.
        parsed.port
        authority = match[2]
        if any(ord(c) > 127 for c in authority) or '\\' in authority:
            raise ValueError()
        result['canonical'] = match[1].lower() + '://' + authority.lower() + match[3]
    except ValueError:
        result['issues'].append(_issue('citation_url_unresolved'))
    return result


def _namespace(row):
    provenance = row.get('provenance') if isinstance(row.get('provenance'), dict) else {}
    value = _first(row, ('source_namespace', 'namespace', 'provider'))[1] or _first(provenance, ('sourceId', 'source_id', 'source_key'))[1]
    return value if isinstance(value, str) and value else None


def _identity_claims(row, namespace, keys):
    claims = []
    for key in keys:
        value = row.get(key)
        if value is not None and isinstance(value, (str, int)) and not isinstance(value, bool):
            claims.append({'source_field': key, 'namespace': namespace, 'value': str(value),
                           'status': 'source_asserted', 'authoritative': False})
    for claim in row.get('identifiers', []) if isinstance(row.get('identifiers'), list) else []:
        if not isinstance(claim, dict):
            continue
        system = claim.get('namespace', claim.get('system'))
        value = claim.get('value')
        if isinstance(system, str) and isinstance(value, (str, int)) and not isinstance(value, bool):
            claims.append({'source_field': 'identifiers', 'namespace': system,
                           'value': str(value), 'status': 'source_asserted', 'authoritative': False})
    return claims


def exact_identifier_links(left, right, *, scope=None):
    """Candidate edges only; caller must explicitly attest authoritative IDs.

    No fuzzy comparison, no merging and no authority inferred from a name.
    Private identifiers must contain the same nonempty household_scope.
    """
    links = []
    for a in left:
        for b in right:
            if not isinstance(a, dict) or not isinstance(b, dict):
                continue
            if a.get('authoritative') is not True or b.get('authoritative') is not True:
                continue
            if not isinstance(a.get('namespace'), str) or not a['namespace'] or not isinstance(a.get('value'), str) or not a['value']:
                continue
            if (a['namespace'], a['value']) != (b.get('namespace'), b.get('value')):
                continue
            private_scope = a.get('household_scope') or b.get('household_scope') or scope
            scoped = 'household_scope' in a or 'household_scope' in b or scope is not None
            if scoped and not (isinstance(private_scope, str) and private_scope and
                               a.get('household_scope') == b.get('household_scope') == private_scope):
                continue
            user_scope = a.get('user_scope') or b.get('user_scope')
            if ('user_scope' in a or 'user_scope' in b) and not (
                    isinstance(user_scope, str) and user_scope and a.get('user_scope') == b.get('user_scope') == user_scope):
                continue
            link = {'kind': 'exact_authoritative_identifier', 'namespace': a['namespace'],
                    'value': a['value'], 'status': 'link_candidate_not_merge'}
            if private_scope is not None:
                link['household_scope'] = deepcopy(private_scope)
            if user_scope is not None:
                link['user_scope'] = deepcopy(user_scope)
            if link not in links:
                links.append(link)
    return links


def normalize_nutrient(observation, *, path='', basis=None, numeric_lexemes=None):
    """Preserve nutrient, basis and method; never derive salt/sodium/energy."""
    result = {'source_assertion': deepcopy(observation), 'basis': None, 'issues': []}
    if not isinstance(observation, dict):
        result['issues'].append(_issue('nutrient_structure_unresolved', path))
        return result
    nutrient = observation.get('nutrient')
    nested = nutrient if isinstance(nutrient, dict) else {}
    result['nutrient_id'] = _first(observation, ('nutrient_id', 'nutrientId'))[1] or nested.get('id')
    result['name'] = _first(observation, ('name', 'nutrient_name'))[1] or nested.get('name') or (nutrient if isinstance(nutrient, str) else None)
    raw_basis = _first(observation, ('basis', 'per', 'measurement_basis'))[1]
    raw_basis = raw_basis if raw_basis is not None else basis
    result['source_basis'] = deepcopy(raw_basis)
    basis_aliases = {'per_100g': 'per_100g', 'per 100 g': 'per_100g', '100 g': 'per_100g',
                     'per_100ml': 'per_100mL', 'per_100mL': 'per_100mL', 'per 100 mL': 'per_100mL', '100 mL': 'per_100mL',
                     'per_serving': 'per_serving', 'per serving': 'per_serving'}
    if isinstance(raw_basis, str):
        result['basis'] = basis_aliases.get(raw_basis)
    elif isinstance(raw_basis, dict):
        if str(raw_basis.get('amount')) == '100' and raw_basis.get('unit') == 'g':
            result['basis'] = 'per_100g'
        elif str(raw_basis.get('amount')) == '100' and raw_basis.get('unit') in ('mL', 'ml'):
            result['basis'] = 'per_100mL'
        elif raw_basis.get('unit') == 'serving' and str(raw_basis.get('amount')) == '1':
            result['basis'] = 'per_serving'
    if result['basis'] is None:
        result['issues'].append(_issue('nutrient_basis_unresolved', path))
    value_key, value = _first(observation, ('value_lexeme', 'amount_lexeme', 'value', 'amount'))
    if isinstance(numeric_lexemes, dict) and value_key in ('value', 'amount'):
        lexical = numeric_lexemes.get(_pointer(path.removeprefix('/source_fields'), value_key))
        if isinstance(lexical, str):
            result['source_numeric_lexeme'] = lexical
            try:
                exact = _decimal(lexical)
                agrees = (float(exact) == value if isinstance(value, float) else
                          exact == _decimal(value))
            except (ValueError, OverflowError):
                agrees = False
            if agrees:
                value = lexical
            else:
                result['issues'].append(_issue('nutrient_numeric_lexeme_conflict', path, severity='error'))
    unit = _first(observation, ('unit', 'unitName', 'unit_name'))[1] or nested.get('unitName')
    result['quantity'] = normalize_quantity(value, unit)
    result['issues'].extend({**item, 'path': path} for item in result['quantity']['issues'])
    for key in ('method', 'qualifier', 'derivationCode', 'dataPoints', 'serving_weight', 'servingWeight', 'serving_size', 'servingSize'):
        if key in observation:
            result[key] = deepcopy(observation[key])
    result['qualification'] = 'source_assertion_not_dietary_advice'
    return result


_TYPE_ALIASES = {'barcodes': 'barcode', 'ingredients': 'ingredient', 'dietary': 'dietary_assertion',
                 'user_profiles': 'profile', 'user_profile': 'profile', 'suppliers': 'supplier',
                 'citations': 'citation', 'source_citation': 'citation'}
_TYPE_ALIASES.update(dict.fromkeys(('nutrientprofile', 'foodcompositionobservation', 'nutrientdefinition',
    'dietaryguideline', 'dietaryreference', 'allergenmapping', 'dietflagassertion', 'dietarytype',
    'metricbasisdefinition', 'source_assertion', 'common_dietary_packet', 'guideline_reference_packet',
    'nutrition_reference', 'source_diet_flag', 'usda_nutrient_observation', 'provider_composition_table'), 'dietary_assertion'))


def normalize_payload(payload, record_type=None):
    """Normalize recognized ingest wrappers into the common typed candidate."""
    if not isinstance(payload, dict):
        return {'normalized': {'title': None, 'language': None, 'fields': {}, 'relations': [], 'field_lineage': []},
                'issues': [_issue('record_not_object', '', severity='error')],
                'uncertainty': ['record_not_object'], 'required_review': True}
    inferred = record_type or payload.get('record_type') or payload.get('kind')
    kind = _TYPE_ALIASES.get(inferred, inferred) if isinstance(inferred, str) else None
    if kind and str(kind).startswith('ingredient_'):
        kind = 'ingredient'
    issues, lineage = [], []
    fields = {'record_type': kind, 'identity_claims': []}
    # Source wrappers are preserved by the core; projection never mutates them.
    row, prefix = payload, ''
    if kind == 'dietary_assertion' and isinstance(payload.get('source_fields'), dict):
        row, prefix = payload['source_fields'], '/source_fields'
    if kind == 'citation' and isinstance(payload.get('reference'), dict):
        row, prefix = payload['reference'], '/reference'
    if isinstance(row.get('data'), dict):
        row, prefix = row['data'], prefix + '/data'
    fallback = payload.get('raw_source') if kind == 'ingredient' and isinstance(payload.get('raw_source'), dict) else {}
    language_key, language = _first(row, ('source_language', 'language', 'inLanguage', 'lang'))
    if language is None:
        language_key, language = _first(payload, ('source_language', 'language', 'inLanguage', 'lang'))
        language_path = _pointer('', language_key) if language_key else None
    else:
        language_path = _pointer(prefix, language_key)
    if language is None:
        language_key, language = _first(fallback, ('source_language', 'language', 'inLanguage', 'lang'))
        language_path = _pointer('/raw_source', language_key) if language_key else None
    language = language if isinstance(language, str) else None
    title_key, title = _first(row, ('title', 'name', 'source_name_text', 'raw_text', 'product_name', 'foodName', 'description'))
    title = title if isinstance(title, str) else None
    if title_key and title is not None:
        lineage.append(_lineage('/title', [_pointer(prefix, title_key)]))
    if language is not None:
        lineage.append(_lineage('/language', [language_path]))
    namespace = _namespace(payload) or _namespace(row)

    def take(target, keys, rule='source-fields-v1'):
        key, value = _first(row, keys)
        source_prefix = prefix
        if key is None and fallback:
            key, value = _first(fallback, keys)
            source_prefix = '/raw_source'
        if key is not None:
            fields[target] = deepcopy(value)
            lineage.append(_lineage('/fields/' + target, [_pointer(source_prefix, key)], rule))
        return key, value

    def quantities():
        key, value = _first(row, ('quantity_lexeme', 'quantity', 'amount'))
        if key is None:
            return
        unit = row.get('unit')
        if isinstance(value, dict):
            unit = value.get('unit', unit)
            value = value.get('value', value)
        result = normalize_quantity(value, unit, locale=row.get('locale'))
        fields['quantity'] = result
        issues.extend({**item, 'path': _pointer(prefix, key)} for item in result['issues'])
        lineage.append(_lineage('/fields/quantity', [_pointer(prefix, key)] + ([_pointer(prefix, 'unit')] if 'unit' in row else []), 'quantity-exact-v1', 'exact' if result['status'] == 'normalized' else 'unresolved'))

    if kind == 'barcode':
        if payload.get('kind') == 'readonly_source_reference':
            fields['reference_only'] = True
            take('binding_status', ('binding_status',))
            issues.append(_issue('barcode_reference_not_product_record'))
        else:
            identifiers = []
            for key in ('gtin', 'barcode', 'code', 'ean', 'upc', 'gtin_upc', 'gtinUpc', 'ean13', 'upc12'):
                if key in row and row[key] is not None:
                    result = normalize_gtin(row[key], namespace)
                    result['source_field'] = key
                    identifiers.append(result)
                    issues.extend({**item, 'path': _pointer(prefix, key)} for item in result['issues'])
                    lineage.append(_lineage('/fields/barcodes/' + str(len(identifiers)-1), [_pointer(prefix, key)], 'gtin-syntax-v1', 'exact' if result['aliases'] else 'unresolved'))
            fields['barcodes'] = identifiers
            if not identifiers:
                issues.append(_issue('barcode_identifier_missing'))
            if len({item['gtin14'] for item in identifiers if 'gtin14' in item}) > 1:
                issues.append(_issue('barcode_identifier_conflict', severity='error'))
            take('product_name', ('product_name', 'name', 'description'))
            take('brand_claim', ('brands', 'brand'))
            take('country_claim', ('countries', 'country'))
        fields['identity_claims'] = _identity_claims(row, namespace, ('fdcId', 'fdc_id'))
    elif kind == 'ingredient':
        take('name_original', ('source_name_text', 'name', 'raw_text', 'description', 'ingredientName'), 'ingredient-source-v1')
        take('aliases_original', ('aliases', 'synonyms'), 'ingredient-source-v1')
        take('preparation_original', ('preparation', 'preparation_form', 'form'), 'ingredient-source-v1')
        take('reported_identity', ('reported_food_identity', 'source_asserted_ingredient_id', 'source_native_id'), 'ingredient-source-v1')
        fields['identity_claims'] = _identity_claims(row, namespace, ('source_native_id', 'source_asserted_ingredient_id', 'ingredientId', 'fdcId', 'fdc_id'))
        fields['name_match_status'] = 'unresolved_no_lexical_equivalence'
        quantities()
        # Names, aliases, plant parts and preparation are never collapsed.
        if title:
            issues.append(_issue('ingredient_identity_requires_review', _pointer(prefix, title_key)))
    elif kind == 'dietary_assertion':
        take('assertion_kind', ('kind', 'type', 'predicate'), 'nutrient-basis-v1')
        fields['automatic_diet_qualification'] = False
        fields['qualification'] = 'source_asserted_not_independently_qualified'
        key, nutrients = _first(row, ('nutrients', 'foodNutrients', 'nutriments', 'nutrition'))
        basis = _first(row, ('basis', 'per', 'measurement_basis'))[1]
        observations = []
        if isinstance(nutrients, list):
            for index, nutrient in enumerate(nutrients):
                path = _pointer(_pointer(prefix, key), index)
                observations.append(normalize_nutrient(nutrient, path=path, basis=basis,
                    numeric_lexemes=payload.get('source_numeric_lexemes')))
        elif key is not None:
            # Arbitrary provider column names (including OFF _100g suffixes)
            # need a separate reviewed provider contract; retain, do not guess.
            fields['nutrients_unmapped'] = deepcopy(nutrients)
            issues.append(_issue('nutrient_mapping_unresolved', _pointer(prefix, key)))
        elif any(k in row for k in ('nutrient_id', 'nutrientId', 'nutrient')):
            observations.append(normalize_nutrient(row, path=prefix, basis=basis,
                numeric_lexemes=payload.get('source_numeric_lexemes')))
        fields['nutrient_observations'] = observations
        for item in observations:
            issues.extend(item['issues'])
        take('assertions_original', ('assertions', 'diet_flags', 'dietCode', 'allergenCode', 'specdiet'), 'nutrient-basis-v1')
        if not observations and not fields.get('assertions_original'):
            issues.append(_issue('dietary_semantics_unresolved', prefix))
        lineage.append(_lineage('/fields/nutrient_observations', [prefix or ''], 'nutrient-basis-v1'))
        fields['identity_claims'] = _identity_claims(row, namespace, ('food_id', 'foodId', 'FOODID', 'fdc_id', 'fdcId'))
    elif kind == 'supplier':
        key, declared_type = take('entity_kind', ('type', 'kind'), 'supplier-claims-v1')
        allowed = ('organization', 'supplier_entity', 'place', 'food_place', 'company_ownership', 'price_observation')
        if declared_type not in allowed:
            fields['entity_kind'] = 'unresolved'
            issues.append(_issue('supplier_entity_kind_unresolved', _pointer(prefix, key) if key else prefix))
        for target, keys in (('name_original', ('name',)), ('legal_name_original', ('legal_name', 'legalName')),
                             ('website_claim', ('website',)), ('address_claim', ('address',)),
                             ('country_claim', ('country',)), ('country_basis', ('country_basis',)),
                             ('roles_claim', ('roles',)), ('ownership_claims', ('relations',)),
                             ('observed_price', ('observed_price',)), ('currency', ('currency',)),
                             ('observed_at', ('observed_at',))):
            take(target, keys, 'supplier-claims-v1')
        fields['identity_claims'] = _identity_claims(row, namespace, ('entity_id', 'supplier_id', 'company_id', 'place_id'))
        fields['relationship_status'] = 'source_claims_not_verified_business_relationships'
    elif kind == 'citation':
        urls = []
        for key in ('url', 'sourceUrl', 'source_url', 'originalUrl', 'downloadUrl', 'download_url', 'referenceUrl', 'licenseUrl', 'rightsEvidenceUrl'):
            if key in row:
                result = normalize_url(row[key])
                result['source_field'] = key
                urls.append(result)
                issues.extend({**item, 'path': _pointer(prefix, key)} for item in result['issues'])
                lineage.append(_lineage('/fields/urls/' + str(len(urls)-1), [_pointer(prefix, key)], 'citation-url-v1', 'exact' if result['canonical'] else 'unresolved'))
        fields['urls'] = urls
        for name in ('title', 'name', 'license', 'licence', 'attribution', 'rights', 'version', 'sha256', 'contentSha256', 'archiveSha256', 'referenceType', 'evidence_fragment', 'fragment', 'page', 'section', 'publishedAt', 'retrievedAt', 'fetchedAt'):
            take(name, (name,), 'citation-url-v1')
        if isinstance(payload.get('parent_reference'), dict):
            fields['parent_reference'] = deepcopy(payload['parent_reference'])
            lineage.append(_lineage('/fields/parent_reference', ['/parent_reference']))
        fields['identity_claims'] = _identity_claims(row, namespace, ('sourceId', 'recordId', 'id'))
        fields['rights_status'] = 'source_claims_not_rights_clearance'
    elif kind in ('profile', 'inventory'):
        fields['visibility'] = 'private_household'
        household_key, household = _first(row, ('household_id', 'householdId'))
        user_key, user = _first(row, ('user_id', 'userId', 'profile_id'))
        scope_key, scope_value = _first(row, ('household_namespace', 'scope_namespace'))
        scope_namespace = scope_value or namespace
        fields['identity_scope'] = {'namespace': deepcopy(scope_namespace), 'household_id': deepcopy(household), 'user_id': deepcopy(user)}
        valid_scope = all(isinstance(value, (str, int)) and not isinstance(value, bool) and str(value) for value in (scope_namespace, household))
        fields['cross_household_merge_allowed'] = False
        if not valid_scope:
            issues.append(_issue('household_scope_missing', prefix, severity='error'))
        scope_paths = [_pointer(prefix, key) for key in (household_key, user_key, scope_key) if key]
        lineage.append(_lineage('/fields/identity_scope', scope_paths, 'household-scope-v1', 'source_asserted' if valid_scope else 'unresolved'))
        if kind == 'profile':
            for name in ('preferences', 'dietary_preferences', 'allergies', 'restrictions', 'locale', 'language'):
                take(name, (name,), 'household-scope-v1')
            fields['preference_status'] = 'explicit_source_preferences_not_inferred_health_traits'
        else:
            for target, keys in (('item_id', ('item_id', 'inventory_id', 'id')), ('item_name_original', ('item_name', 'name')),
                                 ('location_original', ('location',)), ('expiry_original', ('expiry', 'expires_at', 'expiration_date')),
                                 ('product_reference', ('product_id', 'barcode', 'gtin'))):
                take(target, keys, 'household-scope-v1')
            quantities()
            fields['observation_status'] = 'source_snapshot_not_current_stock_guarantee'
    else:
        issues.append(_issue('record_type_unsupported', '/record_type', severity='error'))
    relations = []
    for index, relation in enumerate(payload.get('relations', []) if isinstance(payload.get('relations'), list) else []):
        if isinstance(relation, dict):
            relations.append({'source_assertion': deepcopy(relation), 'status': 'unresolved_source_claim'})
            lineage.append(_lineage('/relations/' + str(len(relations)-1), ['/relations/' + str(index)]))
    for index, claim in enumerate(fields['identity_claims']):
        lineage.append(_lineage('/fields/identity_claims/' + str(index),
                                [_pointer(prefix, claim['source_field'])], 'identity-link-v1'))
    return {'normalized': {'title': title, 'language': language, 'fields': fields,
                           'relations': relations, 'field_lineage': lineage},
            'issues': issues, 'uncertainty': sorted({item['code'] for item in issues}),
            'source_language': language, 'required_review': True}


def translation_text_paths(normalized):
    """Explicit textual projections; never translate raw IDs, status or units.

    The reviewer may preserve a proper name unchanged. No language is inferred
    and no translation is performed here. Raw source copies, scope keys, product
    references, provenance, dates, URLs, nutrient IDs and unit symbols are not
    lexical translation targets. Structured terms use explicit name/label/text
    keys; arbitrary mapping keys are not reclassified as prose.
    """
    fields = normalized.get('fields', {})
    result = []
    text_keys = frozenset(('text', 'name', 'label', 'description', 'value', 'original'))

    def text(value, path):
        if isinstance(value, str) and value.strip():
            result.append(path)
        elif isinstance(value, list):
            for index, child in enumerate(value):
                text(child, _pointer(path, index))
        elif isinstance(value, dict):
            for key in sorted(value):
                if key in text_keys:
                    text(value[key], _pointer(path, key))

    text(normalized.get('title'), '/title')
    kind = fields.get('record_type')
    by_kind = {
        'barcode': ('product_name',),
        'ingredient': ('name_original', 'aliases_original', 'preparation_original'),
        'dietary_assertion': (),
        'supplier': ('name_original', 'legal_name_original', 'address_claim'),
        'citation': ('title', 'name', 'attribution', 'evidence_fragment', 'fragment', 'section'),
        'profile': ('preferences', 'dietary_preferences', 'allergies', 'restrictions'),
        'inventory': ('item_name_original', 'location_original'),
    }
    for key in by_kind.get(kind, ()):
        if key in fields:
            text(fields[key], '/fields/' + key)
    if kind == 'dietary_assertion':
        for index, observation in enumerate(fields.get('nutrient_observations', [])):
            if isinstance(observation, dict):
                text(observation.get('name'), '/fields/nutrient_observations/' + str(index) + '/name')
    return sorted(set(result))
