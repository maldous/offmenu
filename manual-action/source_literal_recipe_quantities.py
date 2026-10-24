"""Pure source-literal annotations, not metric normalization or calibration.

The immutable native ingredient quantity stays unresolved. This successor
connection contract preserves a supported literal amount with source evidence.
It does not infer physical equivalence, food mass, serving size or scaling.
"""
import copy
import re
import unicodedata


class SourceLiteralQuantityError(ValueError):
    pass


def _complete_literal_phrase(phrase, spans, source):
    # Evidence has already been validated against this source. Check numeric
    # boundaries in the full value, not just the selected span: a span starting
    # at '4' must not hide the preceding '1/', range operator or unary sign.
    pattern = r'(?<![\w.])' + re.escape(phrase) + r'(?!\w)'
    for span in spans:
        raw = source
        for part in span['pointer'][1:].split('/'):
            key = part.replace('~1', '/').replace('~0', '~')
            raw = raw[int(key)] if isinstance(raw, list) else raw[key]
        for match in re.finditer(pattern, raw):
            if not span['start'] <= match.start() < match.end() <= span['end']:
                continue
            prefix = raw[:match.start()]
            tail = prefix.rstrip()
            while tail.endswith(('(', '[')):
                tail = tail[:-1].rstrip()
            if tail and (tail[-1] in '/⁄∕+−﹣－＋﹢±' or unicodedata.category(tail[-1]) == 'Pd'):
                continue
            if re.search(r'\d\s*(?:[.,]|to)\s*$', prefix, re.IGNORECASE):
                continue
            return True
    return False


def validate_source_literal(row, ingredient, *, allowed_pointers, source,
                            citations, validate_evidence):
    expected = {'source_ingredient_line_id', 'kind', 'value', 'unit',
                'descriptor', 'evidence', 'citation_ids'}
    if not isinstance(row, dict) or set(row) != expected:
        raise SourceLiteralQuantityError('source_literal_shape')
    if row['source_ingredient_line_id'] != ingredient['ingredient_id']:
        raise SourceLiteralQuantityError('source_literal_line_mismatch')
    kind, unit, descriptor, value = (row[k] for k in ('kind', 'unit', 'descriptor', 'value'))
    valid = ((kind == 'household-measure' and unit in ('handful', 'handfuls') and descriptor is None)
             or (kind == 'item-count' and unit in ('egg', 'eggs') and descriptor in (None, 'large')))
    if not valid:
        raise SourceLiteralQuantityError('source_literal_kind_or_descriptor_unsupported')
    if not isinstance(value, str) or not re.fullmatch(r'[1-9][0-9]{0,8}', value):
        raise SourceLiteralQuantityError('source_literal_positive_integer_required')
    quantity = ingredient.get('quantity')
    if (not isinstance(quantity, dict) or quantity.get('status') != 'unresolved'
        or not quantity.get('issues')
        or any(i.get('code') != 'quantity_unit_unsupported' for i in quantity['issues'])
        or ingredient.get('source_quantity') != value or ingredient.get('source_unit') != unit
        or quantity.get('original') != {'value': value, 'unit': unit}):
        raise SourceLiteralQuantityError('source_literal_native_quantity_mismatch')
    validate_evidence(row['evidence'], source)
    if any(span['pointer'] not in allowed_pointers for span in row['evidence']):
        raise SourceLiteralQuantityError('source_literal_evidence_wrong_line')
    phrase = value + ((' ' + descriptor) if descriptor else '') + ' ' + unit
    if not _complete_literal_phrase(phrase, row['evidence'], source):
        raise SourceLiteralQuantityError('source_literal_phrase_not_in_evidence')
    ids = row['citation_ids']
    if (not isinstance(ids, list) or not ids or any(not isinstance(i, str) for i in ids)
        or len(set(ids)) != len(ids)
        or any(citations.get(i, {}).get('state') != 'verified' for i in ids)):
        raise SourceLiteralQuantityError('source_literal_citation_not_qualified')
    return copy.deepcopy(row)


def literal_allocation(row, quantity, quantity_slot, *, unit_slot, ingredient_name):
    """Bind a whole source amount once; no split, factor or metric conversion."""
    if quantity != {'value': row['value'], 'unit': row['unit']}:
        raise SourceLiteralQuantityError('source_literal_allocation_mismatch')
    if quantity_slot.get('type') != 'quantity':
        raise SourceLiteralQuantityError('source_literal_quantity_slot_required')
    raw = quantity_slot.get('value')
    if isinstance(raw, dict):
        if set(raw) - {'value', 'unit', 'descriptor'}:
            raise SourceLiteralQuantityError('source_literal_slot_shape')
        value, unit, descriptor = raw.get('value'), raw.get('unit'), raw.get('descriptor')
    else:
        value, unit, descriptor = raw, row['unit'], None
    if value != row['value'] or unit != row['unit'] or descriptor != row['descriptor']:
        raise SourceLiteralQuantityError('source_literal_slot_mismatch')
    display = row['value'] + ((' ' + row['descriptor']) if row['descriptor'] else '')
    if row['kind'] == 'item-count':
        # The food noun supplies the count unit. A second unit placeholder would
        # duplicate it; the descriptor remains in the quantity display.
        if unit_slot is not None or ingredient_name != row['unit']:
            raise SourceLiteralQuantityError('source_literal_count_noun_binding')
    elif unit_slot is not None:
        if unit_slot.get('type') != 'unit' or unit_slot.get('value') != row['unit']:
            raise SourceLiteralQuantityError('source_literal_unit_slot_mismatch')
    else:
        display += ' ' + row['unit']
    allocation = dict(copy.deepcopy(row), status='source-literal',
                      metric_normalization=None, scaling='not-qualified')
    return allocation, display
