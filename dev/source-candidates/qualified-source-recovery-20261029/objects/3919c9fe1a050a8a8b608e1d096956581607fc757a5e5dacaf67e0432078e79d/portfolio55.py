"""Worker55 metadata binding checks; no source I/O, fetching or admission.

The caller supplies metadata, never paths to open. Shared provenance validation
checks proposed envelopes; this does not convert the retained legacy MY output.
"""
from datetime import timedelta

from .acceptance import fingerprint
from .field_provenance import field_origin_errors
from .core import RefreshError, canonical, strict_json, timestamp

_ABSENT = object()


def _time(value):
    return timestamp(value)


def assess(binding, observed, *, now, previous_key=None):
    """Deterministic, isolated metadata diagnostics with an injected UTC clock.

    ``binding`` is reviewed configuration. ``observed`` is a retained metadata
    inventory, not evidence that the referenced source bytes were checked now.
    Age uses original acquisition, never later validation time. Thirty-day age
    alone cannot authorize a download. No result grants dataset acceptance.
    """
    result = {'country': binding['country'], 'status': 'invalid', 'errors': [],
              'bindingKey': None, 'replay': 'blocked', 'refresh': 'blocked',
              'acceptedRecords': 0, 'countryComplete': False,
              'sourceBodiesRead': 0, 'metadataIntentOnly': True,
              'sharedGenericCachePlanner': 'unavailable-at-verified-base',
              'realSourceAdapter': 'unsupported-pending-reviewed-caller'}
    errors = result['errors']
    if binding['holds']:
        result.update(status='held', errors=list(binding['holds']))
        return result
    if observed is None:
        result.update(status='missing', errors=['metadata-missing'])
        return result
    if not isinstance(observed, dict):
        errors.append('metadata-malformed')
        return result
    required = ('sourceId', 'releaseId', 'pins', 'originalAcquiredAt')
    if any(k not in observed for k in required):
        errors.append('metadata-fields-missing')
        return result
    if (observed['sourceId'] != binding['sourceId']
            or observed['releaseId'] != binding['releaseId']
            or observed['pins'] != binding['pins']
            or observed['originalAcquiredAt'] != binding['originalAcquiredAt']):
        result.update(status='stale-input', errors=['retained-binding-mismatch'])
        return result
    try:
        clock = _time(now)
        acquired = _time(observed['originalAcquiredAt'])
        if acquired > clock:
            raise ValueError('future-acquisition')
        validated = observed.get('validatedAt')
        if validated is not None and not acquired <= _time(validated) <= clock:
            raise ValueError('invalid-validation-clock')
        key = fingerprint({k: binding[k] for k in (
            'sourceId', 'releaseId', 'pins', 'fieldBindings', 'nativeBasis',
            'originalAcquiredAt', 'contractVersion')})
    except (RefreshError, TypeError, ValueError, OverflowError):
        errors.append('metadata-clock-or-value-invalid')
        return result
    result.update(status='valid-metadata', bindingKey=key,
                  replay='no-op' if previous_key == key else 'bind-metadata',
                  refresh='reuse-under-30-days' if clock < acquired + timedelta(days=30)
                  else 'conditional-refresh-requires-custodian-qualification',
                  notBefore=(acquired + timedelta(days=30)).isoformat(),
                  validationAgeSeconds=None if validated is None
                  else (clock - _time(validated)).total_seconds())
    return result


def assess_portfolio(bindings, observations, *, now, previous_keys=_ABSENT):
    """A failed country cannot suppress the other portfolio diagnostics."""
    errors = []
    if not isinstance(observations, dict):
        observations = {}
        errors.append('request-observations-malformed')
    if previous_keys is _ABSENT:
        previous_keys = {}
    if not isinstance(previous_keys, dict):
        previous_keys = {}
        errors.append('request-previous-keys-malformed')
    results = [assess(b, observations.get(b['country']), now=now,
                      previous_key=previous_keys.get(b['country'])) for b in bindings]
    return _request_errors(results, errors)


def _request_errors(results, errors):
    for result in results:
        if errors:
            result['errors'] = sorted(set(result['errors']) | set(errors))
            if result['status'] != 'held':
                result.update(status='invalid', replay='blocked', refresh='blocked')
    return results


def assess_request(bindings, request):
    """Guard JSON request shape before accessing fields or iterating countries."""
    errors = []
    if not isinstance(request, dict):
        errors.append('request-malformed')
        request = {}
    if 'now' not in request:
        errors.append('request-now-required')
    results = assess_portfolio(bindings, request.get('observations'),
                               now=request.get('now'),
                               previous_keys=request.get('previousKeys', _ABSENT))
    return _request_errors(results, errors)


def proposed_origin_errors(binding, row):
    """Shared validator plus exact MY selectors; authored envelope checks only.

    Legacy retained records have no shared ``data``/``provenance`` envelope.
    An independently reviewed caller conversion is required before real use.
    """
    if binding['holds']:
        return ['binding-held']
    if not isinstance(row, dict):
        return ['candidate-malformed']
    provenance = row.get('provenance', {})
    if not isinstance(provenance, dict):
        return ['candidate-malformed']
    errors = set(field_origin_errors(row, binding['inputPins']))
    if (provenance.get('sourceId') != binding['sourceId']
            or provenance.get('releaseId') != binding['releaseId']):
        errors.add('binding-source-release-mismatch')
    origins = provenance.get('fieldOrigins', {})
    if not isinstance(origins, dict):
        return sorted(errors | {'field-origins-required'})
    if not isinstance(row.get('data'), dict) or set(row['data']) != set(binding['fieldBindings']):
        errors.add('binding-field-inventory-mismatch')
    row_ids = set()
    for field, declaration in binding['fieldBindings'].items():
        origin = origins.get('/data/' + field)
        if not isinstance(origin, dict) or any(
                origin.get(k) != declaration[k]
                for k in ('kind', 'inputPath', 'inputSha256', 'sourceField')):
            errors.add('binding-selector-mismatch')
        identity = origin.get('sourceRecordId') if isinstance(origin, dict) else None
        if isinstance(identity, str) and identity:
            row_ids.add(identity)
        else:
            errors.add('binding-source-row-mismatch')
    if len(row_ids) != 1:
        errors.add('binding-source-row-mismatch')
    return sorted(errors)


def main():
    """Read a small metadata request on stdin; emit diagnostics on stdout only."""
    import sys
    from pathlib import Path
    config = Path(__file__).with_name('portfolio55.json')
    bindings = strict_json(config.read_bytes())['bindings']
    try:
        request = strict_json(sys.stdin.read())
    except (ValueError, RefreshError):
        request = None
    result = assess_request(bindings, request)
    sys.stdout.buffer.write(canonical(result))


if __name__ == '__main__':
    main()
