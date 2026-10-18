"""Per-datum provenance coverage for reviewed staging adapters.

No origin is inferred. Source cells, multi-input derivations and code constants
are distinct. This verifies coverage/identity, not the correctness of a transform;
use alongside full record schema and source-specific semantic validation.
"""
import re
from pathlib import PurePosixPath


def datum_pointers(value, prefix='/data'):
    """JSON pointers for every scalar datum, including zero/null and array items."""
    if isinstance(value, dict):
        for key, child in value.items():
            escaped = str(key).replace('~', '~0').replace('/', '~1')
            yield from datum_pointers(child, prefix + '/' + escaped)
    elif isinstance(value, list):
        for index, child in enumerate(value):
            yield from datum_pointers(child, prefix + '/' + str(index))
    else:
        yield prefix


def _digest(value):
    return isinstance(value, str) and bool(re.fullmatch('[0-9a-f]{64}', value))


def field_origin_errors(row, input_pins, *, policy_pins=()):
    """Verify exact origin coverage; input_pins/policy_pins are trusted contracts.

Each provenance.fieldOrigins JSON pointer maps to one tagged object:
source: kind/sourceId/releaseId/inputPath/inputSha256/sourceRecordId/sourceField.
derived: kind/policySha256/transform/inputs (nonempty list of origin objects).
constant: kind/policySha256/symbol (e.g. a reviewed unknown marker, not a cell).

A semantic validator must additionally check the actual source coordinate, value,
transform result or code constant. Source identity is scoped to this source release;
cross-source graph assembly needs its own reviewed provenance contract.
"""
    errors = set()
    if not isinstance(row, dict) or 'data' not in row or not isinstance(input_pins, dict):
        return ['field-origin-contract-invalid']
    if not input_pins or any(not isinstance(path, str) or not path
            or PurePosixPath(path).is_absolute() or '..' in path.split('/')
            or '\\' in path or path != PurePosixPath(path).as_posix()
            or not _digest(digest) for path, digest in input_pins.items()):
        return ['field-origin-contract-invalid']
    if any(not _digest(pin) for pin in policy_pins):
        return ['field-origin-contract-invalid']
    provenance = row.get('provenance')
    if not isinstance(provenance, dict):
        return ['field-origin-contract-invalid']
    origins = provenance.get('fieldOrigins')
    if not isinstance(origins, dict):
        return ['field-origins-required']
    expected = set(datum_pointers(row['data']))
    if not expected or set(origins) != expected:
        errors.add('field-origin-inventory-mismatch')

    def check(origin, depth=0):
        if not isinstance(origin, dict):
            errors.add('field-origin-missing')
            return
        if depth > 8:
            errors.add('field-origin-depth-exceeded')
            return
        kind = origin.get('kind')
        if kind == 'source':
            if any(not isinstance(origin.get(key), str) or not origin[key]
                   for key in ('sourceId', 'releaseId', 'inputPath', 'inputSha256',
                               'sourceRecordId', 'sourceField')):
                errors.add('field-origin-incomplete')
                return
            if (origin['sourceId'] != provenance.get('sourceId')
                    or origin['releaseId'] != provenance.get('releaseId')):
                errors.add('field-origin-source-mismatch')
            if input_pins.get(origin['inputPath']) != origin['inputSha256']:
                errors.add('field-origin-input-pin-mismatch')
        elif kind in ('derived', 'constant'):
            if origin.get('policySha256') not in policy_pins:
                errors.add('field-origin-policy-pin-mismatch')
            key = 'transform' if kind == 'derived' else 'symbol'
            if not isinstance(origin.get(key), str) or not origin[key]:
                errors.add('field-origin-incomplete')
            if kind == 'derived':
                inputs = origin.get('inputs')
                if not isinstance(inputs, list) or not inputs or len(inputs) > 256:
                    errors.add('field-origin-derived-inputs-invalid')
                else:
                    for item in inputs:
                        check(item, depth + 1)
        else:
            errors.add('field-origin-kind-invalid')

    for pointer in sorted(expected):
        check(origins.get(pointer))
    return sorted(errors)
