"""EC/NE/TJ/VU metadata bindings; no source-body reader or admission engine.

Only reviewed, pinned receipt JSON is projected. Original asset paths/hashes are
claims in those receipts, never filesystem inputs. Shared refresh components own
serialization, origin coverage, age policy and downstream qualification.
"""
import copy

from ..core import RefreshError, canonical, safe_path, sha, strict_json, timestamp
from ..field_provenance import field_origin_errors
from ..global_run import StageResult
from ..serialization import encode_records
from ._bindings import BINDINGS

MAX_METADATA = 1024 * 1024
COUNTRIES = ('EC', 'NE', 'TJ', 'VU')
TYPES = ('ingredients', 'recipes', 'nutrition', 'retailers/providers',
         'prices/baskets', 'dietary references')


def registry():
    """Static portfolio configuration, never caller modules or data adapters."""
    return copy.deepcopy(BINDINGS)


def pointer(document, locator):
    """Strict RFC6901 traversal; missing != null, list indices are canonical."""
    if not isinstance(locator, str) or not locator.startswith('/'):
        raise ValueError('selector-invalid')
    value = document
    for token in locator[1:].split('/'):
        # Reject malformed escapes instead of silently changing a field name.
        import re
        if re.search(r'~(?![01])', token):
            raise ValueError('selector-invalid')
        token = token.replace('~1', '/').replace('~0', '~')
        if isinstance(value, list):
            if not token.isascii() or not token.isdecimal() or str(int(token)) != token:
                raise ValueError('selector-invalid')
            value = value[int(token)]
        elif isinstance(value, dict):
            value = value[token]
        else:
            raise KeyError(token)
    return value


def read_metadata(path):
    """Explicit receipt mapping only; no discovery, archive or body operations."""
    path = safe_path(path)
    if path.suffix != '.json' or not path.is_file():
        raise ValueError('metadata-file-invalid')
    with path.open('rb') as stream:
        raw = stream.read(MAX_METADATA + 1)
    if len(raw) > MAX_METADATA:
        raise ValueError('metadata-byte-limit')
    return raw


def _failure(spec, status, code):
    return {'sourceId': spec['sourceId'], 'country': spec['country'],
            'status': status, 'diagnostics': [code], 'record': None,
            'sourceBodyAdmission': False, 'countryComplete': False,
            'dataRecords': 0}


def _assess(spec, raw, *, now):
    """Pure portfolio projection, also exercised with tiny authored test inputs.

This is metadata staging only. A valid projection never authorizes the described
data asset. Every shipped source has separately retained raw-data holds.
"""
    if not spec['metadataReadAllowed']:
        return _failure(spec, 'held', 'metadata-use-held')
    if raw is None:
        return _failure(spec, 'missing', 'pinned-metadata-not-supplied')
    if not isinstance(raw, bytes) or len(raw) > MAX_METADATA:
        return _failure(spec, 'malformed', 'metadata-byte-limit-or-type')
    pin = spec['metadata']
    if len(raw) != pin['bytes'] or sha(raw) != pin['sha256']:
        return _failure(spec, 'stale', 'metadata-pin-mismatch')
    if not hasattr(now, 'tzinfo') or now.tzinfo is None:
        return _failure(spec, 'malformed', 'policy-clock-invalid')
    try:
        document = strict_json(raw)
        if not isinstance(document, dict):
            raise ValueError()
        canonical(document)  # Includes overflow-to-infinity rejection.
    except (ValueError, TypeError, UnicodeError, RefreshError):
        return _failure(spec, 'malformed', 'metadata-json-invalid')

    policy_pin = sha(canonical({'interface': 'portfolio48-metadata/1', 'binding': spec}))
    data, origins, diagnostics = {}, {}, []
    for field, declaration in spec['fields'].items():
        selector = declaration['selector']
        if selector is None:
            data[field] = declaration['constant']
            origins['/data/' + field] = {
                'kind': 'constant', 'policySha256': policy_pin,
                'symbol': declaration['reason']}
            continue
        try:
            value = pointer(document, selector)
            # Each declared metadata field is a scalar; no bulk source subtree.
            if isinstance(value, (dict, list)):
                raise ValueError()
            if 'expected' in declaration and value != declaration['expected']:
                diagnostics.append('source-release-or-identity-mismatch')
            data[field] = value
            origins['/data/' + field] = {
                'kind': 'source', 'sourceId': spec['sourceId'],
                'releaseId': spec['releaseKey'], 'inputPath': pin['name'],
                'inputSha256': pin['sha256'], 'sourceRecordId': '/',
                'sourceField': selector}
        except (KeyError, IndexError, TypeError, ValueError):
            diagnostics.append('metadata-selector-missing-or-invalid')
    if diagnostics:
        return _failure(spec, 'missing' if set(diagnostics) == {
            'metadata-selector-missing-or-invalid'} else 'malformed',
                        sorted(set(diagnostics))[0])

    acquired = data.get('originalAcquiredAt')
    cache = {'minimumReuseDays': 30, 'originalAcquiredAt': acquired,
             'acquisitionAgeDays': None, 'minimumReuseWindowElapsed': None,
             'plannerCapability': 'shared-pure-cache-planner-unavailable',
             'effectiveDecision': 'not-enabled-no-source-cache-read',
             'validationObservedAt': data.pop('validationObservedAt', None),
             'mtimeUsedForFreshness': False, 'networkRequests': 0,
             'nextOnlineStep': 'none', 'validationResetsAcquisitionAge': False,
             'sourceBytesVerified': False}
    # Validation time is diagnostic metadata, not a staged source datum or clock.
    origins.pop('/data/validationObservedAt', None)
    if cache['validationObservedAt'] is not None:
        try:
            observed = timestamp(cache['validationObservedAt'])
            if observed > now or (acquired is not None and observed < timestamp(acquired)):
                raise ValueError()
        except (ValueError, TypeError, RefreshError):
            return _failure(spec, 'malformed', 'validation-time-invalid')
    if acquired is not None:
        try:
            # Diagnostic age only. abec has no generic pure cache planner:
            # core.cache_policy is Wikibooks-specific. Do not relabel it, invoke
            # operational CachedAcquirer, or install another refresh engine.
            if now.tzinfo is None:
                raise ValueError()
            seconds = (now - timestamp(acquired)).total_seconds()
            if seconds < 0:
                raise ValueError()
            cache.update(acquisitionAgeDays=int(seconds // 86400),
                         minimumReuseWindowElapsed=seconds >= 30 * 86400)
        except (ValueError, TypeError, RefreshError):
            return _failure(spec, 'malformed', 'acquisition-time-invalid')
    elif now.tzinfo is None:
        return _failure(spec, 'malformed', 'policy-clock-invalid')

    record = {'schemaVersion': 'portfolio48-metadata-row/1',
              'id': spec['sourceId'] + ':' + pin['sha256'],
              'kind': 'source-input-metadata',
              'provenance': {'sourceId': spec['sourceId'],
                             'releaseId': spec['releaseKey'],
                             'fetchedAt': acquired, 'fieldOrigins': origins},
              'data': data}
    errors = field_origin_errors(record, {pin['name']: pin['sha256']},
                                 policy_pins=(policy_pin,))
    if errors:
        return _failure(spec, 'malformed', 'metadata-field-origin-invalid')
    holds = sorted(set(spec['sourceDataHolds']))
    return {'sourceId': spec['sourceId'], 'country': spec['country'],
            'status': 'held' if holds else 'valid', 'diagnostics': holds,
            'record': record, 'policySha256': policy_pin,
            'metadataSha256': pin['sha256'], 'metadataRecords': 1,
            'dataTypes': spec['dataTypes'],
            'applicability': spec['applicability'], 'cache': cache,
            'sourceBodyAdmission': False, 'countryComplete': False,
            'dataRecords': 0}


def assess(source_id, raw=None, *, now):
    """Assess only a hardcoded portfolio source; caller data cannot lift holds."""
    specs = {s['sourceId']: s for s in registry()['sources']}
    if source_id not in specs:
        raise ValueError('portfolio-source-unsupported')
    return _assess(specs[source_id], raw, now=now)


def assess_portfolio(metadata_paths=None, *, now, reader=read_metadata):
    """Bounded independent per-source diagnostics, no automatic path following."""
    metadata_paths = {} if metadata_paths is None else metadata_paths
    sources = registry()['sources']
    aliases = {s['metadata']['name'] for s in sources}
    if not isinstance(metadata_paths, dict) or set(metadata_paths) - aliases:
        raise ValueError('metadata-map-unknown-input')
    results = []
    for spec in sources:
        path = metadata_paths.get(spec['metadata']['name'])
        if not spec['metadataReadAllowed'] or path is None:
            result = _assess(spec, None, now=now)
        else:
            try:
                result = _assess(spec, reader(path), now=now)
            except (OSError, ValueError, TypeError, RefreshError):
                result = _failure(spec, 'malformed', 'metadata-input-unreadable')
        results.append(result)
    rows = [r['record'] for r in results if r.get('record') is not None]
    raw = encode_records(rows)
    # Diagnostic age/state changes are not canonical metadata content identity.
    return {'schemaVersion': 'portfolio48-staging-binding/1',
            'scope': 'receipt-metadata-only', 'sources': results,
            'candidateSha256': sha(raw), 'candidateBytes': len(raw),
            'metadataRecords': len(rows), 'dataRecords': 0,
            'coverage': [{'country': country, 'dataType': kind,
                          'status': 'unassessed'}
                         for country in COUNTRIES for kind in TYPES],
            'countryComplete': False, 'goldAdmitted': False,
            'productionBindingInstalled': False,
            'osResourceBoundaryVerified': False,
            'sourceBodyAdmission': False, 'networkRequests': 0}


def candidate_bytes(report):
    return encode_records([r['record'] for r in report['sources']
                           if r.get('record') is not None])


def replay(report, previous=None):
    """Pure metadata byte replay/no-op interface; shared engine owns publication.

previous is an explicit bounded generated metadata candidate, never a source
asset locator. Equality verifies the bytes, not a caller's claimed digest.
"""
    current = candidate_bytes(report)
    if (report.get('candidateSha256') != sha(current)
            or report.get('candidateBytes') != len(current)
            or report.get('metadataRecords') != sum(
                r.get('record') is not None for r in report['sources'])):
        raise ValueError('metadata-replay-report-mismatch')
    if previous is not None and (not isinstance(previous, bytes)
                                 or len(previous) > 16 * MAX_METADATA):
        raise ValueError('previous-candidate-byte-limit-or-type')
    return {'action': 'verified-no-op' if previous == current else 'metadata-replayed',
            'candidateSha256': sha(current), 'candidateBytes': len(current),
            'metadataRecords': report['metadataRecords'], 'dataRecords': 0,
            'sourceBodyAdmission': False}


def stage_result(result):
    """Shared StageResult interface; no production Binding/admission is installed."""
    evidence = (sha(canonical(result)),)
    if result['status'] == 'valid':
        return StageResult('succeeded', 'metadata-only', evidence, 1)
    if result['status'] == 'held':
        return StageResult('held', 'source-data-held', evidence)
    return StageResult('failed', 'metadata-' + result['status'], evidence)
