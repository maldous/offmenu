"""EE/EG/EH/ER retained-metadata bindings; never a source reader or admission.

Inputs are explicitly supplied metadata bytes. Locator paths are provenance only,
never opened here. Shared helpers own JSON, serialization and field-origin checks.
The only candidate rendering path is permanently authored-fixture scope.
"""
from dataclasses import dataclass

from . import acceptance, serialization
from .acquisition import MIN_TTL
from .core import RefreshError, canonical, sha, strict_json, timestamp
from .field_provenance import field_origin_errors
from .portfolio28_catalogue import load_catalogue

MAX_METADATA_BYTES = 128 * 1024
POLICY_VERSION = 'owner28-metadata-only/1'
COUNTRIES = ('EE', 'EG', 'EH', 'ER')
DATA_TYPES = ('ingredients', 'recipes', 'nutrition', 'retailers/providers',
              'prices/baskets', 'dietary references')


@dataclass(frozen=True)
class MetadataBinding:
    """Trusted portfolio configuration, not a SourceContract or rights grant."""
    identity: str
    country: str
    release: str
    acquired_at: str | None
    manifests: tuple
    selectors: tuple = ()
    holds: tuple = ()


def portfolio_config():
    return load_catalogue()


def bindings():
    return tuple(MetadataBinding(
        identity=x['id'], country=x['country'], release=x['release'],
        acquired_at=x['originalAcquiredAt'],
        manifests=tuple((m['key'], m['sha256']) for m in x['metadataInputs']),
        selectors=tuple((s['input'], s['pointer'], s['expected'])
                        for s in x['selectors']), holds=tuple(x['holds']))
        for x in portfolio_config()['bindings'])


def _pointer(value, pointer):
    if not isinstance(pointer, str) or not pointer.startswith('/'):
        raise ValueError('selector-invalid')
    for token in pointer[1:].split('/'):
        key = token.replace('~1', '/').replace('~0', '~')
        if isinstance(value, list):
            if not key.isdecimal() or (len(key) > 1 and key.startswith('0')):
                raise ValueError('selector-invalid')
            value = value[int(key)]
        elif isinstance(value, dict):
            value = value[key]
        else:
            raise ValueError('selector-invalid')
    return value


def assess_binding(binding, metadata, *, now, validated_at=None, previous=None):
    """Pure deterministic metadata preflight; no paths, mtime, AI or network.

    No previous output, manifest flag or licence label can enable source actions.
    Validation age is reported separately and cannot reset acquisition age.
    """
    errors = set()
    documents = {}
    pins = dict(binding.manifests)
    if (not isinstance(metadata, dict) or binding.country not in COUNTRIES
            or not binding.identity or not binding.release or not pins
            or len(pins) != len(binding.manifests)
            or any(not isinstance(k, str) or not k or not isinstance(v, str)
                   or not acceptance.DIGEST.fullmatch(v) for k, v in pins.items())):
        errors.add('binding-contract-invalid')
        metadata = {} if not isinstance(metadata, dict) else metadata
    if set(metadata) - set(pins):
        errors.add('unexpected-metadata-input')
    for key, digest in binding.manifests:
        raw = metadata.get(key)
        if raw is None:
            errors.add('metadata-input-missing')
            continue
        if not isinstance(raw, bytes) or not 0 < len(raw) <= MAX_METADATA_BYTES:
            errors.add('metadata-input-malformed')
            continue
        if sha(raw) != digest:
            errors.add('metadata-input-stale-pin')
        try:
            value = strict_json(raw)
            canonical(value)  # Also reject overflowed finite-JSON numbers.
            if not isinstance(value, dict):
                raise ValueError()
            documents[key] = value
        except (ValueError, TypeError, UnicodeError, RecursionError):
            errors.add('metadata-input-malformed')
    for key, pointer, expected in binding.selectors:
        if key not in documents:
            continue
        try:
            actual = _pointer(documents[key], pointer)
            if type(actual) is not type(expected) or actual != expected:
                errors.add('metadata-selector-mismatch')
        except (KeyError, IndexError, TypeError, ValueError):
            errors.add('metadata-selector-missing')
    age = validation_age = None
    try:
        clock = timestamp(now)
        if binding.acquired_at is None:
            errors.add('original-acquisition-time-missing')
        else:
            acquired = timestamp(binding.acquired_at)
            age = int((clock - acquired).total_seconds())
            if age < 0:
                raise ValueError()
        if validated_at is not None:
            validated = timestamp(validated_at)
            validation_age = int((clock - validated).total_seconds())
            if validation_age < 0 or (age is not None and validated < acquired):
                raise ValueError()
    except (ValueError, TypeError, OverflowError):
        errors.add('metadata-clock-invalid')
    if binding.holds:
        errors.add('source-operation-held')
    if any(x in errors for x in ('binding-contract-invalid', 'metadata-clock-invalid',
                                 'metadata-input-malformed')):
        status = 'malformed'
    elif 'metadata-input-stale-pin' in errors:
        status = 'stale-input'
    elif 'source-operation-held' in errors:
        status = 'held'
    elif errors:
        status = 'missing'
    elif age >= MIN_TTL:
        status = 'stale-review-required'
    else:
        status = 'bound-metadata-only'
    identity = acceptance.fingerprint({
        'policyVersion': POLICY_VERSION, 'minimumReuseSeconds': MIN_TTL,
        'maximumMetadataBytes': MAX_METADATA_BYTES,
        'binding': binding.identity, 'country': binding.country,
        'release': binding.release, 'inputs': sorted(pins.items()),
        'selectors': binding.selectors, 'holds': binding.holds,
        'originalAcquiredAt': binding.acquired_at})
    replay = (status == 'bound-metadata-only' and isinstance(previous, dict)
              and previous.get('schemaVersion') == 'owner28-metadata-binding/1'
              and previous.get('bindingId') == binding.identity
              and previous.get('status') == status
              and previous.get('bindingSha256') == identity)
    return {
        'schemaVersion': 'owner28-metadata-binding/1',
        'policyVersion': POLICY_VERSION,
        'bindingId': binding.identity, 'country': binding.country,
        'releaseId': binding.release, 'bindingSha256': identity,
        'status': status, 'errors': sorted(errors), 'holds': list(binding.holds),
        'metadataInputsVerified': not bool(errors - {'source-operation-held',
                                                     'original-acquisition-time-missing'}),
        'selectorDeclarations': [dict(input=k, pointer=p) for k, p, _ in binding.selectors],
        'originalAcquiredAt': binding.acquired_at, 'validatedAt': validated_at,
        'acquisitionAgeSeconds': age, 'validationAgeSeconds': validation_age,
        'minimumReuseSeconds': MIN_TTL, 'validationResetsAcquisitionAge': False,
        'cacheAction': ('reuse-retained-metadata-no-network' if status == 'bound-metadata-only'
                        else 'review-required-no-network'),
        'replayAction': 'no-op' if replay else 'metadata-report-only',
        'networkRequests': 0, 'sourceBodyReads': 0, 'aiCalls': 0,
        'sourceProcessingEnabled': False, 'countryComplete': False,
        'goldAdmitted': False,
    }


def assess_portfolio(metadata, *, now, validated_at=None):
    """Independent per-binding diagnostics across the fixed four-country scope."""
    configured = bindings()
    invalid = not isinstance(metadata, dict)
    known = {k for b in configured for k, _ in b.manifests}
    results = [assess_binding(
        b, metadata if invalid else {k: metadata[k] for k, _ in b.manifests if k in metadata},
        now=now, validated_at=validated_at) for b in configured]
    return {'schemaVersion': 'owner28-portfolio-binding-report/1',
            'countries': list(COUNTRIES), 'requiredDataTypes': list(DATA_TYPES),
            'errors': (['portfolio-metadata-malformed'] if invalid else
                       ['unexpected-portfolio-metadata-input'] if set(metadata) - known else []),
            'bindings': results, 'sourceProcessingEnabled': False,
            'acceptedCountryTypeCells': 0, 'countryComplete': False}


FIXTURE_SOURCE = 'owner28-authored-methodology-fixture'
FIXTURE_RELEASE = 'authored-1'
FIXTURE_ACQUIRED = '2026-01-01T00:00:00Z'
FIXTURE_IDS = ('SYN:28:0001', 'SYN:28:0002')


def render_authored_fixture(raw):
    """Portfolio field mapping demonstrator: exact two-record authored format only.

    This does not parse the retained EG report/candidate formats. Fixture source
    identity is permanent; output cannot be presented as a real release.
    """
    try:
        if not isinstance(raw, bytes) or len(raw) > 4096:
            raise ValueError()
        payload = strict_json(raw)
        if (set(payload) != {'fixtureOnly', 'country', 'observations'}
                or payload['fixtureOnly'] is not True or payload['country'] != 'EG'
                or not isinstance(payload['observations'], list)
                or len(payload['observations']) != 2):
            raise ValueError()
        rows = []
        for i, item in enumerate(payload['observations']):
            if (not isinstance(item, dict) or set(item) != {'id', 'literal', 'unit', 'basis'}
                    or item['id'] != FIXTURE_IDS[i]
                    or not isinstance(item['literal'], str) or not item['literal']
                    or item['unit'] is not None or item['basis'] is not None):
                raise ValueError()
            pointers = {'country': '/country',
                        **{k: f'/observations/{i}/{k}' for k in ('literal', 'unit', 'basis')}}
            origins = {'/data/' + k: {
                'kind': 'source', 'sourceId': FIXTURE_SOURCE,
                'releaseId': FIXTURE_RELEASE, 'inputPath': 'fixture.json',
                'inputSha256': sha(raw), 'sourceRecordId': item['id'], 'sourceField': p}
                for k, p in pointers.items()}
            rows.append({'id': item['id'], 'kind': 'owner28-methodology-fixture',
                         'schemaVersion': '1', 'provenance': {
                             'sourceId': FIXTURE_SOURCE, 'releaseId': FIXTURE_RELEASE,
                             'fetchedAt': FIXTURE_ACQUIRED, 'fieldOrigins': origins},
                         'data': {k: _pointer(payload, p) for k, p in pointers.items()}})
        return rows
    except (KeyError, TypeError, ValueError, UnicodeError, RecursionError):
        raise RefreshError('authored-fixture-layout-invalid') from None


def authored_fixture_contract(raw, assets):
    """Trusted fixture-only factory; real source manifests cannot create contracts."""
    rows = render_authored_fixture(raw)
    pins = {'fixture.json': sha(raw)}

    def semantics(row):
        errors = set(field_origin_errors(row, pins))
        expected = {r['id']: r for r in rows}.get(row.get('id'))
        if expected is None or row != expected:
            errors.add('authored-fixture-source-value-mismatch')
        return sorted(errors)

    schema = {'type': 'object', 'required': ['id', 'kind', 'schemaVersion', 'provenance', 'data'],
              'properties': {'id': {'enum': list(FIXTURE_IDS)},
                             'kind': {'const': 'owner28-methodology-fixture'},
                             'schemaVersion': {'const': '1'},
                             'provenance': {'type': 'object'},
                             'data': {'type': 'object', 'required': ['country', 'literal', 'unit', 'basis'],
                                      'properties': {'country': {'const': 'EG'},
                                                     'literal': {'type': 'string', 'minLength': 1},
                                                     'unit': {'type': 'null'}, 'basis': {'type': 'null'}},
                                      'additionalProperties': False}},
              'additionalProperties': False}
    schemas = {'owner28-methodology-fixture': schema}
    by_path = {a.path: a for a in assets}
    if set(by_path) != {'fixture.json', 'rights.json', 'scope.json'}:
        raise RefreshError('authored-fixture-assets-invalid')
    return acceptance.SourceContract(
        source_id=FIXTURE_SOURCE, release_id=FIXTURE_RELEASE,
        scope_id='owner28-authored-metadata-only', acquired_at=FIXTURE_ACQUIRED,
        inputs=tuple(assets), expected_records=2,
        expected_ids_sha256=acceptance.ids_digest(FIXTURE_IDS), schemas=schemas,
        schemas_sha256=acceptance.fingerprint(schemas), semantic_validator=semantics,
        policy_sha256=acceptance.fingerprint({'policy': 'owner28-authored-metadata-only/1'}),
        rights_evidence=by_path['rights.json'], scope_evidence=by_path['scope.json'],
        permitted_operations=frozenset(('retain', 'parse', 'transform')), fixture=True)


def authored_fixture_manifest(raw, assets):
    """Shared packet serialization; no files, source registry or pointers mutated."""
    candidate = serialization.encode_records(render_authored_fixture(raw))
    by_path = {a.path: a for a in assets}
    return candidate, {
        'sourceId': FIXTURE_SOURCE, 'releaseId': FIXTURE_RELEASE,
        'acquiredAt': FIXTURE_ACQUIRED, 'normalizedRecords': 2,
        'candidateSha256': sha(candidate), 'candidateBytes': len(candidate),
        'inputFiles': [vars(a) for a in assets],
        'rightsEvidenceSha256': by_path['rights.json'].sha256,
        'scopeEvidenceSha256': by_path['scope.json'].sha256}
