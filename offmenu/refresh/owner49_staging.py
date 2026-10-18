"""Owner49 portfolio metadata bindings; no acquisition, body I/O or admission.

Trusted binding declarations are reviewed code, never source-supplied manifests.
Successful assessment means metadata is consistent, not that a source is accepted.
The fixture adapter deliberately cannot process real source bodies.
"""
from dataclasses import asdict, dataclass
import re

from .acquisition import MIN_TTL
from .core import RefreshError, canonical, sha, strict_json, timestamp
from .field_provenance import datum_pointers, field_origin_errors
from .national_tabular import valid_input_name
from .serialization import encode_records


@dataclass(frozen=True)
class InputPin:
    path: str
    sha256: str
    bytes: int


@dataclass(frozen=True)
class MetadataBinding:
    source_id: str
    release_id: str
    country: str
    record_kind: str
    manifest_sha256: str
    inputs: tuple[InputPin, ...]
    # Concrete target-datum pointer -> exact source selector, no inferred origins.
    selectors: tuple[tuple[str, str], ...]
    native_units: tuple[str, ...]
    basis: str
    unknowns: tuple[str, ...] = ()
    holds: tuple[str, ...] = ()
    fixture: bool = False


def _digest(value):
    return isinstance(value, str) and re.fullmatch('[0-9a-f]{64}', value) is not None


def _binding_fields_valid(binding):
    if not isinstance(binding, MetadataBinding):
        return False
    return (type(binding.fixture) is bool
            and all(isinstance(items, tuple) for items in
                    (binding.inputs, binding.selectors, binding.native_units,
                     binding.unknowns, binding.holds))
            and all(isinstance(x, str) and x for x in
                    (*binding.native_units, *binding.unknowns, *binding.holds))
            and all(isinstance(x, InputPin) for x in binding.inputs)
            and all(isinstance(pair, tuple) and len(pair) == 2 for pair in binding.selectors)
            and all(isinstance(x, str) and x for x in
                (binding.source_id, binding.release_id, binding.country,
                 binding.record_kind, binding.basis))
            and _digest(binding.manifest_sha256)
            and bool(binding.inputs)
            and len({x.path for x in binding.inputs}) == len(binding.inputs)
            and all(valid_input_name(x.path) and _digest(x.sha256)
                    and type(x.bytes) is int and x.bytes > 0 for x in binding.inputs)
            and bool(binding.selectors)
            and len(dict(binding.selectors)) == len(binding.selectors)
            and all(isinstance(t, str) and t.startswith('/data/')
                    and isinstance(s, str) and s for t, s in binding.selectors))


def _binding_valid(binding):
    try:
        return _binding_fields_valid(binding)
    except (ValueError, TypeError, AttributeError):
        return False


def assess_metadata(binding, manifest_raw, *, validated_at, previous_key=None):
    """Assess caller-supplied small metadata bytes, without following any path.

    Manifest envelope is the shared staging-input handoff proposed to integrator00,
    not an assertion that historical receipts already have this shape. Missing
    original acquisition time stays missing. Validation time cannot reset it.
    Stale inputs stop here; only a separately authorized shared acquisition runner
    may decide a refresh. There is no force/download/revalidate bypass parameter.
    """
    result = {'status': 'malformed', 'code': 'binding-invalid',
              'admitted': False, 'replayKey': None, 'cache': 'not-assessed'}
    if not _binding_valid(binding):
        return result
    if binding.holds:
        return {**result, 'status': 'held', 'code': 'source-held',
                'holds': list(binding.holds)}
    if manifest_raw is None:
        return {**result, 'status': 'missing', 'code': 'manifest-missing'}
    if not isinstance(manifest_raw, bytes) or len(manifest_raw) > 65536:
        return {**result, 'code': 'manifest-invalid'}
    try:
        # Strict parsing and pin checking both fail with a fixed safe diagnostic.
        value = strict_json(manifest_raw)
        if not isinstance(value, dict):
            raise RefreshError('manifest-invalid')
        if sha(manifest_raw) != binding.manifest_sha256:
            raise RefreshError('manifest-pin-mismatch')
        expected = {'schemaVersion': 'owner49-staging-input/1',
                    'sourceId': binding.source_id, 'releaseId': binding.release_id,
                    'country': binding.country, 'recordKind': binding.record_kind,
                    'inputFiles': [asdict(x) for x in binding.inputs]}
        if any(value.get(k) != v for k, v in expected.items()):
            raise RefreshError('manifest-contract-mismatch')
        if set(value) != set(expected) | {'originalAcquiredAt'}:
            raise RefreshError('manifest-fields-invalid')
        if value['originalAcquiredAt'] is None:
            return {**result, 'status': 'missing', 'code': 'original-acquisition-missing'}
        acquired, checked = timestamp(value['originalAcquiredAt']), timestamp(validated_at)
        age = (checked - acquired).total_seconds()
        if age < 0:
            raise RefreshError('validation-precedes-acquisition')
        # Includes trusted selectors, native semantics and input identities. Excludes
        # validation time/previous result so repeated validation doesn't change key.
        key = sha(canonical({'binding': asdict(binding), 'manifest': value}))
        common = {**result, 'replayKey': key,
                  'originalAcquiredAt': value['originalAcquiredAt'],
                  'validatedAt': validated_at, 'ageSeconds': age,
                  'minimumReuseSeconds': MIN_TTL}
        if age >= MIN_TTL:
            return {**common, 'status': 'stale-input', 'code': 'refresh-not-authorized',
                    'cache': 'expired'}
        return {**common, 'status': 'no-op' if previous_key == key else 'valid',
                'code': 'metadata-only', 'cache': 'reuse-under-thirty-days'}
    except (ValueError, TypeError, KeyError, OverflowError, RecursionError):
        # Do not serialize exceptions, metadata, source paths or URLs in diagnostics.
        return {**result, 'code': 'manifest-invalid'}


def assess_portfolio(requests, *, validated_at):
    """Independent bounded metadata requests, each with its own safe diagnostic."""
    if not isinstance(requests, dict):
        raise RefreshError('portfolio-requests-invalid')
    if len(requests) > 16:
        raise RefreshError('portfolio-request-limit')
    def malformed(code):
        return {'status': 'malformed', 'code': code, 'admitted': False,
                'replayKey': None, 'cache': 'not-assessed'}
    # Never sort or echo malformed non-string names. Preserve valid peers and give
    # unnamed entries deterministic, collision-free diagnostic slots instead.
    names = sorted(name for name in requests
                   if isinstance(name, str) and 0 < len(name) <= 128)
    results = {}
    for name in names:
        envelope = requests[name]
        if not isinstance(envelope, (tuple, list)) or len(envelope) != 3:
            results[name] = malformed('request-envelope-invalid')
            continue
        binding, raw, prior = envelope
        results[name] = assess_metadata(binding, raw, validated_at=validated_at, previous_key=prior)
    ordinal = 0
    for _ in range(len(requests) - len(names)):
        while f'__invalid_request_{ordinal}' in results:
            ordinal += 1
        results[f'__invalid_request_{ordinal}'] = malformed('request-name-invalid')
        ordinal += 1
    return results


def retained_diagnostics(catalog_raw):
    """Emit deterministic, non-admitting diagnostics for this retained portfolio.

    Historical receipt formats are not rewritten to impersonate shared input
    manifests. Their exact pins/selectors remain in the catalog; held/missing
    sources have no production adapter. This performs no asset verification.
    """
    if not isinstance(catalog_raw, bytes) or len(catalog_raw) > 65536:
        raise RefreshError('portfolio-catalog-invalid')
    try:
        catalog = strict_json(catalog_raw)
        if catalog['schemaVersion'] != 'owner49-retained-staging-catalog/1':
            raise ValueError()
        sources = catalog['sources']
        if len(sources) != 4 or {s['country'] for s in sources} != {'FI', 'JP', 'KE', 'KG'}:
            raise ValueError()
        results = {}
        for source in sources:
            if source['admitted'] is not False or not source['blockers'] or not source['evidence']:
                raise ValueError()
            results[source['country']] = {
                'status': source['status'], 'admitted': False,
                'recordKindApplicability': source['applicableTypes'],
                'productionCapability': 'unsupported', 'bodyVerification': 'not-performed',
                'cacheIntent': 'unknown-no-download', 'blockers': source['blockers'],
                'evidence': source['evidence']}
        return canonical({'catalogSha256': sha(catalog_raw), 'sources': results})
    except (ValueError, TypeError, KeyError, RecursionError):
        raise RefreshError('portfolio-catalog-invalid') from None


def stage_authored_fixture(binding, manifest_raw, source_raw, *, validated_at):
    """Exercise shared provenance/serialization only with a pinned authored fixture.

    This small fixture has flat source cells; portfolio selectors for real CSV/PDF
    formats remain declarations. No production SourceContract or handler is installed.
    """
    if not isinstance(binding, MetadataBinding) or binding.fixture is not True:
        raise RefreshError('authored-fixture-required')
    assessment = assess_metadata(binding, manifest_raw, validated_at=validated_at)
    if assessment['status'] != 'valid':
        raise RefreshError('fixture-metadata-not-valid')
    if len(binding.inputs) != 1 or not isinstance(source_raw, bytes) or len(source_raw) > 16384:
        raise RefreshError('fixture-input-invalid')
    pin = binding.inputs[0]
    if len(source_raw) != pin.bytes or sha(source_raw) != pin.sha256:
        raise RefreshError('fixture-input-pin-mismatch')
    cells = strict_json(source_raw)
    if not isinstance(cells, dict) or 'id' not in cells or not isinstance(cells['id'], str):
        raise RefreshError('fixture-source-invalid')
    if cells.get('unit') not in binding.native_units or cells.get('basis') != binding.basis:
        raise RefreshError('fixture-native-semantics-mismatch')
    data, origins = {}, {}
    for target, selector in binding.selectors:
        # Fixture-only flat-cell coordinate; never a parser for actual national data.
        if target.count('/') != 2 or selector not in cells:
            raise RefreshError('fixture-selector-invalid')
        key = target.split('/')[-1]
        if '~' in key or key in data:
            raise RefreshError('fixture-selector-invalid')
        data[key] = cells[selector]
        origins[target] = {'kind': 'source', 'sourceId': binding.source_id,
                           'releaseId': binding.release_id, 'inputPath': pin.path,
                           'inputSha256': pin.sha256, 'sourceRecordId': cells['id'],
                           'sourceField': selector}
    row = {'id': cells['id'], 'kind': binding.record_kind, 'schemaVersion': '1.0',
           'countries': [binding.country], 'data': data,
           'provenance': {'sourceId': binding.source_id, 'releaseId': binding.release_id,
                          'fetchedAt': assessment['originalAcquiredAt'],
                          'fieldOrigins': origins}}
    errors = field_origin_errors(row, {pin.path: pin.sha256})
    if errors or set(origins) != set(datum_pointers(data)):
        raise RefreshError('fixture-origin-invalid')
    return encode_records([row])
