"""Portfolio configuration projected through shared offline validators.

Only explicitly pinned JSON evidence is read. Payload paths in that evidence are
never followed. The emitted object is metadata staging, not accepted source data.
"""
from dataclasses import dataclass
from pathlib import Path
import re
from urllib.parse import urlsplit

from offmenu.refresh.acquisition import MIN_TTL, SourceSpec
from offmenu.refresh.core import (RefreshError, canonical, safe_path, sha,
                                  strict_json, timestamp, verify_source)
from offmenu.refresh.field_provenance import datum_pointers, field_origin_errors

MAX_METADATA = 64 * 1024
MAX_TOTAL_METADATA = 1024 * 1024
COUNTRIES = frozenset(('GG', 'NR', 'TM', 'YE'))
DOMAINS = frozenset(('ingredients', 'recipes', 'nutrition', 'retailers/providers',
                     'prices/baskets', 'dietary references'))
POLICY_SHA256 = sha(Path(__file__).read_bytes())


@dataclass(frozen=True)
class Evidence:
    name: str
    path: str
    bytes: int
    sha256: str


@dataclass(frozen=True)
class Field:
    name: str
    evidence: str = ''
    selector: str = ''
    unknown: str = ''


@dataclass(frozen=True)
class Binding:
    key: str
    country: str
    source_id: str
    release_id: str
    release_basis: str
    url: str
    role: str
    domains: tuple
    inputs: tuple
    fields: tuple
    country_evidence: str
    country_selector: str
    release_evidence: str
    release_selector: str
    holds: tuple
    required_fields: tuple
    # Original-download record selectors, never metadata-validation time/mtime.
    acquisition: tuple = ()  # evidence, utc, sha256, bytes, status, complete, expected-complete
    fixture: bool = False


def pointer(document, selector):
    if not isinstance(selector, str) or not selector.startswith('/'):
        raise ValueError('invalid-selector')
    value = document
    for token in selector[1:].split('/'):
        token = token.replace('~1', '/').replace('~0', '~')
        if isinstance(value, list):
            if not token.isdigit() or str(int(token)) != token:
                raise ValueError('invalid-selector')
            value = value[int(token)]
        elif isinstance(value, dict):
            value = value[token]
        else:
            raise ValueError('invalid-selector')
    return value


def validate_binding(spec):
    if (spec.country not in COUNTRIES or not spec.key or not spec.source_id
            or not spec.release_id or not spec.role or type(spec.fixture) is not bool
            or not spec.domains or not set(spec.domains) <= DOMAINS
            or not 1 <= len(spec.inputs) <= 8
            or len({a.name for a in spec.inputs}) != len(spec.inputs)
            or sum(a.bytes for a in spec.inputs) > MAX_TOTAL_METADATA):
        raise RefreshError('binding-contract-invalid')
    names = {a.name for a in spec.inputs}
    for asset in spec.inputs:
        if (not re.fullmatch(r'metadata/[a-z0-9-]+\.json', asset.name)
                or type(asset.bytes) is not int or not 0 < asset.bytes <= MAX_METADATA
                or not re.fullmatch('[a-f0-9]{64}', asset.sha256)
                or Path(asset.path).name not in ('receipt.json', 'acquisition-receipt.json',
                                                'response.json', 'custody-response.json',
                                                'R2-W61-B03-W60-custody-response.json')):
            raise RefreshError('metadata-contract-invalid')
    if (spec.country_evidence not in names or spec.release_evidence not in names
            or len({f.name for f in spec.fields}) != len(spec.fields)
            or any(not re.fullmatch('[A-Za-z][A-Za-z0-9]*', f.name) for f in spec.fields)
            or not set(spec.required_fields) <= {f.name for f in spec.fields}):
        raise RefreshError('field-contract-invalid')
    for f in spec.fields:
        if (bool(f.unknown) == bool(f.evidence or f.selector)
                or not f.unknown and (f.evidence not in names or not f.selector.startswith('/'))):
            raise RefreshError('field-contract-invalid')
    if spec.acquisition and (len(spec.acquisition) != 7 or spec.acquisition[0] not in names):
        raise RefreshError('acquisition-contract-invalid')
    u = urlsplit(spec.url)
    if (u.scheme != 'https' or not u.hostname or u.username or u.password
            or u.query or u.fragment or u.port not in (None, 443)
            or '\\' in spec.url or any(ord(c) < 33 or ord(c) > 126 for c in spec.url)):
        raise RefreshError('binding-contract-invalid')


def read_metadata(asset):
    """Exact selected metadata only; no walking, inferred manifests or payload IO."""
    path = safe_path(asset.path)
    with path.open('rb') as stream:
        raw = stream.read(MAX_METADATA + 1)
    if len(raw) > MAX_METADATA:
        raise RefreshError('metadata-size-limit')
    return raw


def _load(asset, loader):
    try:
        raw = loader(asset)
        if not isinstance(raw, bytes) or len(raw) > MAX_METADATA:
            return None, 'malformed', 'metadata-size-or-type'
        try:
            verify_source(raw, {'bytes': asset.bytes, 'sha256': asset.sha256})
        except RefreshError:
            return None, 'stale-input', 'metadata-pin-mismatch'
        value = strict_json(raw)
        if not isinstance(value, dict):
            return None, 'malformed', 'metadata-object-required'
        canonical(value)  # Also rejects finite-JSON exponent overflow (1e999).
        return value, None, None
    except FileNotFoundError:
        return None, 'missing', 'metadata-not-held'
    except PermissionError:
        return None, 'held', 'metadata-read-denied'
    except (ValueError, UnicodeError, OSError):
        return None, 'malformed', 'metadata-invalid-or-unsafe'


def cache_observation(acquired, as_of):
    """Age projection only, using shared UTC validation/minimum constant.

    This is not an acquisition/cache engine. No refresh or force mode exists.
    A generic pure planner in shared core is an explicit integration proposal.
    """
    if acquired is None:
        return {'originalAcquiredAt': None, 'originalAcquisitionAgeSeconds': None,
                'state': 'original-age-unknown-no-download', 'minimumReuseSeconds': MIN_TTL,
                'networkRequests': 0, 'refreshAuthorized': False}
    age = (as_of - timestamp(acquired)).total_seconds()
    if age < 0:
        raise RefreshError('original-acquisition-in-future')
    return {'originalAcquiredAt': acquired, 'originalAcquisitionAgeSeconds': age,
            'state': ('under-30-days-zero-download' if age < MIN_TTL
                      else 'at-least-30-days-review-only-no-download'),
            'minimumReuseSeconds': MIN_TTL, 'networkRequests': 0, 'refreshAuthorized': False}


def assess(specs, *, as_of, loader=read_metadata):
    """Isolate malformed/missing/held/stale inputs per binding, returning fixed codes."""
    now = timestamp(as_of)
    results, stable = [], []
    for spec in specs:
        diagnostics, docs = [], {}
        result = {'bindingKey': spec.key, 'sourceId': spec.source_id,
                  'country': spec.country, 'releaseId': spec.release_id,
                  'fixture': spec.fixture,
                  'status': 'malformed', 'diagnostics': diagnostics,
                  'sourceExecutionAuthorized': False, 'acceptedRecords': 0}
        row = None
        try:
            validate_binding(spec)
            failures = []
            for asset in spec.inputs:
                doc, state, error = _load(asset, loader)
                if error:
                    failures.append(state)
                    diagnostics.append({'code': error, 'input': asset.name})
                else:
                    docs[asset.name] = doc
            if failures:
                result['status'] = next(s for s in ('malformed', 'stale-input', 'missing', 'held') if s in failures)
                raise _Stop
            if pointer(docs[spec.country_evidence], spec.country_selector) != spec.country:
                raise RefreshError('country-source-binding-mismatch')
            if pointer(docs[spec.release_evidence], spec.release_selector) != spec.release_id:
                raise RefreshError('release-source-binding-mismatch')
            data = {'country': spec.country, 'sourceRole': spec.role,
                    'domainApplicability': list(spec.domains),
                    'applicabilityStatus': 'source-lead-only-not-country-acceptance',
                    'releaseIdentityBasis': spec.release_basis,
                    'payloadBytesReverified': False}
            origins = {}
            unresolved = []
            for field in spec.fields:
                if field.unknown:
                    data[field.name] = None
                    if field.name in spec.required_fields:
                        unresolved.append(field.name)
                else:
                    value = pointer(docs[field.evidence], field.selector)
                    if isinstance(value, (dict, list)):
                        raise RefreshError('field-selector-not-scalar')
                    data[field.name] = value
                    asset = next(a for a in spec.inputs if a.name == field.evidence)
                    origins['/data/' + field.name] = {
                        'kind': 'source', 'sourceId': spec.source_id, 'releaseId': spec.release_id,
                        'inputPath': asset.name, 'inputSha256': asset.sha256,
                        'sourceRecordId': spec.key, 'sourceField': field.selector}
                    if value is None and field.name in spec.required_fields:
                        unresolved.append(field.name)
            acquired = None
            if data.get('sourceUrl') != spec.url:
                raise RefreshError('source-locator-binding-mismatch')
            if data.get('originalSha256') is not None and not (
                    isinstance(data['originalSha256'], str)
                    and re.fullmatch('[0-9a-f]{64}', data['originalSha256'])):
                raise RefreshError('original-download-evidence-mismatch')
            if data.get('originalBytes') is not None and not (
                    type(data['originalBytes']) is int and data['originalBytes'] > 0):
                raise RefreshError('original-download-evidence-mismatch')
            if any(data.get(k) is not None and not isinstance(data[k], str)
                   for k in ('nativeUnit', 'nativeBasis', 'recordInputSelector')):
                raise RefreshError('field-selector-not-scalar')
            if spec.acquisition:
                evidence, utc, checksum, size, status, complete, expected = spec.acquisition
                doc = docs[evidence]
                # A reported original download must bind this same checksum/extent.
                if (pointer(doc, checksum) != data.get('originalSha256')
                        or pointer(doc, size) != data.get('originalBytes')
                        or type(pointer(doc, status)) is not int or pointer(doc, status) != 200
                        or type(pointer(doc, complete)) is not bool or pointer(doc, complete) is not expected):
                    raise RefreshError('original-download-evidence-mismatch')
                acquired = pointer(doc, utc)
                timestamp(acquired)
                # The declaration's acquisition time must be the same event value.
                if data.get('originalAcquiredAt') != acquired:
                    raise RefreshError('original-acquisition-selector-mismatch')
            elif data.get('originalAcquiredAt') is not None:
                raise RefreshError('original-acquisition-proof-missing')
            observed = cache_observation(acquired, now)
            for p in datum_pointers(data):
                origins.setdefault(p, {'kind': 'constant', 'policySha256': POLICY_SHA256,
                                       'symbol': 'portfolio-metadata-declaration:' + p})
            row = {'id': 'portfolio60:' + spec.key, 'kind': 'source-input-binding',
                   'provenance': {'sourceId': spec.source_id, 'releaseId': spec.release_id,
                                  'fieldOrigins': origins}, 'data': data}
            input_pins = {a.name: a.sha256 for a in spec.inputs}
            errors = field_origin_errors(row, input_pins, policy_pins=(POLICY_SHA256,))
            if errors:
                raise RefreshError('shared-field-origin-validation-failed')
            for code in spec.holds:
                diagnostics.append({'code': 'source-held', 'reason': code})
            for name in unresolved:
                diagnostics.append({'code': 'required-field-unknown', 'field': name})
            result.update(status='held' if spec.holds else 'missing' if unresolved else 'valid',
                          cacheObservation=observed, metadataValidatedAt=as_of,
                          validationDoesNotResetAcquisition=True,
                          originalPayloadVerification='historical-receipt-claim-only',
                          sharedFieldOriginErrors=errors)
            result['sharedCachePlanner'] = {'status': 'unsupported-interface-at-selected-base',
                                            'execution': 'not-installed', 'networkRequests': 0}
            result['sourceContentClaimIdentity'] = (sha(canonical({
                'sourceId': spec.source_id, 'releaseId': spec.release_id,
                'reportedOriginalSha256': data['originalSha256']}))
                if data.get('originalSha256') else None)
            result['sourceContentIdentityVerified'] = False
            result['explicitUnknowns'] = {f.name: f.unknown for f in spec.fields if f.unknown}
            # Disabled shared SourceSpec: metadata validity cannot enable acquisition.
            registration = SourceSpec(spec.key, spec.url, POLICY_SHA256,
                                      spec.inputs[-1].sha256, enabled=False,
                                      rights_approved=False, held=bool(spec.holds),
                                      release=spec.release_id)
            result['sourceRegistration'] = {**registration.identity(), 'enabled': False,
                                            'rightsApproved': False, 'held': bool(spec.holds)}
        except _Stop:
            pass
        except (RefreshError, KeyError, IndexError, TypeError, ValueError) as exc:
            # Never serialize arbitrary exception/source values into diagnostics.
            safe_codes = {'country-source-binding-mismatch', 'release-source-binding-mismatch',
                          'source-locator-binding-mismatch',
                          'field-selector-not-scalar', 'original-download-evidence-mismatch',
                          'original-acquisition-selector-mismatch', 'original-acquisition-proof-missing',
                          'original-acquisition-in-future', 'binding-contract-invalid',
                          'metadata-contract-invalid', 'field-contract-invalid',
                          'acquisition-contract-invalid', 'shared-field-origin-validation-failed'}
            code = str(exc) if type(exc) is RefreshError and str(exc) in safe_codes else 'binding-metadata-malformed'
            result['status'] = 'malformed'
            diagnostics.append({'code': code})
            row = None
        # Status/input pins belong in content identity; validation age/time do not.
        stable.append({'bindingKey': spec.key, 'sourceId': spec.source_id,
                       'country': spec.country, 'releaseId': spec.release_id,
                       'fixture': spec.fixture,
                       'status': result['status'], 'row': row,
                       'inputPins': [{'path': a.name, 'bytes': a.bytes, 'sha256': a.sha256}
                                     for a in spec.inputs], 'holds': list(spec.holds),
                       'explicitUnknowns': {f.name: f.unknown for f in spec.fields if f.unknown},
                       'diagnostics': diagnostics.copy()})
        results.append(result)
    manifest = {'schemaVersion': 'offmenu-portfolio60-input-bindings/1',
                'scope': 'metadata-only-not-source-staging-acceptance',
                'policySha256': POLICY_SHA256, 'bindings': stable,
                'sourceRecordsAccepted': 0, 'countryCoverageComplete': False,
                'goldAdmission': False}
    return {'manifest': manifest, 'manifestSha256': sha(canonical(manifest)),
            'diagnostics': results, 'networkRequests': 0,
            'sourcePayloadReads': 0, 'asOf': as_of}


class _Stop(Exception):
    pass


def publish_metadata(report, directory):
    """Append-only metadata artifact; unchanged content is a true file no-op."""
    encoded = canonical(report['manifest'])
    key = sha(encoded)
    if key != report['manifestSha256']:
        raise RefreshError('metadata-manifest-digest-mismatch')
    root = safe_path(directory)
    destination = safe_path(root / key / 'binding-manifest.json')
    if destination.exists():
        if destination.stat().st_size != len(encoded):
            raise RefreshError('metadata-manifest-digest-mismatch')
        verify_source(destination.read_bytes(), {'bytes': len(encoded), 'sha256': key})
        return {'outcome': 'unchanged-no-op', 'manifestSha256': key}
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open('xb') as stream:
        stream.write(encoded)
    return {'outcome': 'metadata-manifest-created', 'manifestSha256': key}
