"""Worker33 retained-metadata bindings; no source-body or acquisition interface.

Only caller-supplied, exactly pinned metadata bytes are inspected. This module
does not register global-run handlers, confer rights, or admit country data.
"""
import re

from .acquisition import MIN_TTL
from .core import RefreshError, canonical, sha, strict_json, timestamp
from .field_provenance import field_origin_errors
from .global_run import StageResult

MAX_METADATA_BYTES = 65536
PORTFOLIO = frozenset(('GH', 'GI', 'GM', 'GN'))
KINDS = frozenset(('price-coverage', 'cpi-locator', 'recipe-locator', 'discovery'))
HEX = re.compile(r'[0-9a-f]{64}')
NAME = re.compile(r'[a-z][a-z0-9-]{0,95}')
PIN_KEYS = {'path', 'sha256'}
SPEC_KEYS = {'id', 'country', 'kind', 'sourceId', 'releaseId', 'publisherRelease',
             'input', 'parentManifest', 'original', 'countrySelectors', 'fields',
             'originalAcquiredAt', 'acquisitionEvidence', 'holds', 'adapter',
             'unknowns', 'retainedCounts'}


def _pin(value):
    return (isinstance(value, dict) and set(value) == PIN_KEYS
            and isinstance(value['path'], str) and bool(value['path'])
            and isinstance(value['sha256'], str)
            and HEX.fullmatch(value['sha256']) is not None)


def _selector(value, pointer):
    """Strict RFC6901 coordinates into the retained metadata, never a raw file."""
    if not isinstance(pointer, str) or not pointer.startswith('/'):
        raise RefreshError('metadata-selector-invalid')
    for token in pointer[1:].split('/'):
        if re.search(r'~(?![01])', token):
            raise RefreshError('metadata-selector-invalid')
        token = token.replace('~1', '/').replace('~0', '~')
        if isinstance(value, list):
            if not re.fullmatch(r'0|[1-9][0-9]*', token):
                raise RefreshError('metadata-selector-invalid')
            try:
                value = value[int(token)]
            except (IndexError, ValueError):
                raise RefreshError('metadata-selector-missing') from None
        elif isinstance(value, dict) and token in value:
            value = value[token]
        else:
            raise RefreshError('metadata-selector-missing')
    return value


def _validate_spec(spec):
    if not isinstance(spec, dict) or set(spec) != SPEC_KEYS:
        raise RefreshError('metadata-binding-invalid')
    if (not isinstance(spec['id'], str) or not NAME.fullmatch(spec['id'])
            or spec['country'] not in PORTFOLIO or spec['kind'] not in KINDS
            or any(not isinstance(spec[k], str) or not spec[k]
                   for k in ('sourceId', 'releaseId', 'adapter'))
            or not _pin(spec['input']) or not _pin(spec['parentManifest'])
            or (spec['original'] is not None and not _pin(spec['original']))):
        raise RefreshError('metadata-binding-invalid')
    if (not isinstance(spec['countrySelectors'], list)
            or not 1 <= len(spec['countrySelectors']) <= 8):
        raise RefreshError('metadata-binding-invalid')
    for key in ('holds', 'unknowns'):
        if not isinstance(spec[key], list) or any(not isinstance(x, str) or not NAME.fullmatch(x) for x in spec[key]):
            raise RefreshError('metadata-binding-invalid')
    if (not isinstance(spec['retainedCounts'], dict)
            or any(not isinstance(k, str) or type(v) is not int or v < 0
                   for k, v in spec['retainedCounts'].items())):
        raise RefreshError('metadata-binding-invalid')
    if spec['publisherRelease'] is not None and not isinstance(spec['publisherRelease'], str):
        raise RefreshError('metadata-binding-invalid')
    if spec['originalAcquiredAt'] is not None:
        timestamp(spec['originalAcquiredAt'])
        if not _pin(spec['acquisitionEvidence']):
            raise RefreshError('acquisition-evidence-required')
    elif spec['acquisitionEvidence'] is not None:
        raise RefreshError('acquisition-time-unknown')
    if not isinstance(spec['fields'], dict) or not 1 <= len(spec['fields']) <= 128:
        raise RefreshError('metadata-binding-invalid')
    for name, field in spec['fields'].items():
        if (not isinstance(name, str) or not NAME.fullmatch(name)
                or not isinstance(field, dict) or set(field) != {'selector', 'type', 'meaning'}
                or field['type'] not in ('string', 'integer', 'null')
                or not isinstance(field['meaning'], str) or not field['meaning']):
            raise RefreshError('metadata-binding-invalid')


def assess(spec, supplied, *, now, previous_key=None):
    """Pure bounded metadata assessment returning the shared StageResult receipt.

`supplied` maps a binding ID to retained metadata bytes (not raw source bytes).
The validatedAt timestamp is observational and excluded from the build key.
`reused` is metadata replay only. No result is a source parse/accept receipt.
"""
    try:
        _validate_spec(spec)
        if not isinstance(supplied, dict):
            raise RefreshError('metadata-input-map-invalid')
        observed = timestamp(now)
        key = sha(canonical(spec))
        raw = supplied.get(spec['id'])
        if raw is None:
            return _result(spec, key, 'missing', 'unsupported', 'retained-metadata-missing', now)
        if not isinstance(raw, bytes) or len(raw) > MAX_METADATA_BYTES:
            raise RefreshError('metadata-size-or-type-invalid')
        if sha(raw) != spec['input']['sha256']:
            return _result(spec, key, 'stale-input', 'quarantined', 'retained-metadata-pin-mismatch', now)
        payload = strict_json(raw)
        if any(_selector(payload, p) != spec['country'] for p in spec['countrySelectors']):
            raise RefreshError('metadata-country-mismatch')
        data, origins = {}, {}
        for name, field in spec['fields'].items():
            value = _selector(payload, field['selector'])
            expected = {'string': str, 'integer': int, 'null': type(None)}[field['type']]
            if type(value) is not expected:
                raise RefreshError('metadata-field-type-mismatch')
            data[name] = value
            origins['/data/' + name] = {
                'kind': 'source', 'sourceId': spec['sourceId'], 'releaseId': spec['releaseId'],
                'inputPath': spec['id'] + '.json', 'inputSha256': spec['input']['sha256'],
                'sourceRecordId': field['selector'], 'sourceField': field['selector']}
        errors = field_origin_errors({'data': data, 'provenance': {
            'sourceId': spec['sourceId'], 'releaseId': spec['releaseId'],
            'fieldOrigins': origins}}, {spec['id'] + '.json': spec['input']['sha256']})
        if errors:
            raise RefreshError('metadata-field-origin-invalid')
        age = None
        if spec['originalAcquiredAt'] is not None:
            age = (observed - timestamp(spec['originalAcquiredAt'])).total_seconds()
            if age < 0:
                raise RefreshError('acquisition-timestamp-in-future')
        status = 'held' if spec['holds'] else ('reused' if previous_key == key else 'succeeded')
        result = _result(spec, key, 'valid', status,
                         'source-operation-held' if spec['holds'] else 'metadata-contract-valid', now)
        result.update(fieldOriginCount=len(origins),
                      originalAcquisitionAgeSeconds=age,
                      cacheIntent=('acquisition-age-unknown' if age is None else
                                     'retain-no-refresh' if age < MIN_TTL else
                                     'refresh-review-required-no-network'),
                      replay='no-op' if previous_key == key else 'metadata-assessed')
        return result
    except (RefreshError, KeyError, TypeError, ValueError, RecursionError):
        # Never return source text, paths, URLs, selectors, or exception strings.
        return {'metadataOutcome': 'malformed',
                'stage': StageResult('failed', 'metadata-contract-invalid').receipt(),
                'sourceBodyRead': False, 'networkRequests': 0,
                'countryAccepted': False, 'goldAdmitted': 0}


def _result(spec, key, outcome, status, code, now):
    return {'bindingId': spec['id'], 'country': spec['country'], 'kind': spec['kind'],
            'metadataOutcome': outcome, 'buildKey': key, 'validatedAt': now,
            'stage': StageResult(status, code, (key, spec['input']['sha256'])).receipt(),
            'sourceBodyRead': False, 'networkRequests': 0, 'minimumReuseSeconds': MIN_TTL,
            'revalidationResetsAcquisitionAge': False, 'mtimeUsedForFreshness': False,
            'refreshOverridesAvailable': False, 'originalBytesVerified': False,
            'cachePlanner': 'shared-pure-planner-unavailable',
            'parentManifestBytesVerified': False,
            'sourceAdapter': spec['adapter'], 'sourceParsingEnabled': False,
            'normalizedRecords': 0, 'mappedRecords': 0, 'goldAdmitted': 0,
            'countryAccepted': False, 'authorizedSourceOperations': [],
            'reviewed': False, 'production': 'stopped', 'cix': 'paused'}


def assess_portfolio(specs, supplied, *, now, previous_keys=None):
    """Diagnostic isolation: malformed peer bindings cannot suppress other results."""
    if not isinstance(specs, list) or len(specs) > 32:
        raise RefreshError('portfolio-size-invalid')
    return [assess(spec, supplied, now=now,
                   previous_key=(previous_keys or {}).get(spec.get('id'))
                   if isinstance(spec, dict) else None) for spec in specs]
