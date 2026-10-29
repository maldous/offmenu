"""Pure portfolio metadata adapter over shared refresh contracts.

Only pinned receipt JSON is an input. Original paths are inert provenance values.
There is no acquisition, parser dispatch, SourceContract creation or acceptance.
"""
from dataclasses import dataclass
from datetime import timedelta
import os
import re
import stat

from offmenu.refresh.acquisition import MIN_TTL
from offmenu.refresh.core import RefreshError, canonical, sha, strict_json, timestamp, safe_path
from offmenu.refresh.field_provenance import datum_pointers, field_origin_errors
from offmenu.refresh.global_run import StageResult
from offmenu.refresh.serialization import encode_records
from .sources import BINDING_DATA

MAX_METADATA_BYTES = 32768
MINIMUM_REUSE_SECONDS = max(MIN_TTL, int(timedelta(days=30).total_seconds()))
COUNTRIES = ('CX', 'MZ', 'SZ', 'VE')
TYPES = ('ingredients', 'recipes', 'nutrition', 'retailers/providers',
         'prices/baskets', 'dietary references')


@dataclass(frozen=True)
class ReceiptBinding:
    """Trusted code/configuration, never constructed from an input receipt."""
    country: str
    source_id: str
    release_id: str
    metadata_path: str
    metadata_bytes: int
    metadata_sha256: str
    retained_metadata_path: str
    selectors: dict
    applicability: tuple
    holds: tuple
    acquisition_epoch_qualified: bool = False


def bindings():
    return tuple(ReceiptBinding(**{**row, 'applicability': tuple(row['applicability']),
                                 'holds': tuple(row['holds'])})
                 for row in BINDING_DATA['bindings'])


def _pointer(value, pointer):
    if not isinstance(pointer, str) or not pointer.startswith('/'):
        raise RefreshError('binding-selector-invalid')
    for part in pointer[1:].split('/'):
        if re.search(r'~(?![01])', part):
            raise RefreshError('binding-selector-invalid')
        key = part.replace('~1', '/').replace('~0', '~')
        if isinstance(value, list):
            if not re.fullmatch(r'0|[1-9][0-9]*', key):
                raise RefreshError('binding-selector-missing')
            try:
                value = value[int(key)]
            except IndexError:
                raise RefreshError('binding-selector-missing') from None
        elif isinstance(value, dict) and key in value:
            value = value[key]
        else:
            raise RefreshError('binding-selector-missing')
    return value


def _stage(status, code, evidence=(), count=None):
    # Shared diagnostic envelope, not a bespoke execution engine.
    return StageResult(status, code, tuple(evidence), count).receipt()


def _policy(binding):
    return sha(canonical({'scope': 'portfolio39-receipt-metadata-only-v1',
                          'country': binding.country, 'sourceId': binding.source_id,
                          'releaseId': binding.release_id, 'selectors': binding.selectors,
                          'applicability': binding.applicability, 'holds': binding.holds,
                          'acquisitionEpochQualified': binding.acquisition_epoch_qualified}))


def _cache_view(data, binding, now):
    """Metadata-only age declaration; the shared acquirer owns actual caching.

    Never uses mtime or validation age as original-acquisition age. No fetch mode
    or network callback exists here, including for stale/missing inputs.
    """
    clock = timestamp(now)
    acquired = data['originalAcquiredAt']
    validated = data['lastValidatedAt']
    result = {'minimumReuseSeconds': MINIMUM_REUSE_SECONDS,
              'originalAcquiredAt': acquired, 'lastValidatedAt': validated,
              'acquisitionAgeSeconds': None, 'validationAgeSeconds': None,
              'acquisitionEpochQualified': binding.acquisition_epoch_qualified,
              'intentOnly': True, 'retainedBodyVerified': False,
              'sharedPureCachePlanner': 'unsupported-at-selected-baseline',
              'mtimeUsed': False, 'validationResetsAcquisitionAge': False,
              'networkRequests': 0, 'fetchAllowed': False}
    if validated is not None:
        age = (clock - timestamp(validated)).total_seconds()
        if age < 0:
            raise RefreshError('binding-validation-time-in-future')
        result['validationAgeSeconds'] = int(age)
    if acquired is None:
        result['decision'] = 'original-acquisition-time-unknown'
        return result
    age = (clock - timestamp(acquired)).total_seconds()
    if age < 0:
        raise RefreshError('binding-acquisition-time-in-future')
    if validated is not None and timestamp(validated) < timestamp(acquired):
        raise RefreshError('binding-validation-before-acquisition')
    result['acquisitionAgeSeconds'] = int(age)
    if not binding.acquisition_epoch_qualified:
        result['decision'] = 'acquisition-epoch-review-required'
    elif age < MINIMUM_REUSE_SECONDS:
        result['decision'] = 'reuse-under-30-days-zero-download'
    else:
        result['decision'] = 'stale-review-required-no-download'
    return result


def bind_receipt(binding, raw, *, now, previous_key=None):
    """Return one metadata record plus isolated diagnostics; never food records.

    A 'valid' result means a pinned metadata binding is usable, not that rights,
    raw inputs, parser execution, STAGING acceptance or country coverage passed.
    """
    report = {'country': binding.country, 'sourceId': binding.source_id,
              'releaseId': binding.release_id, 'outcome': 'malformed',
              'metadataStage': None, 'sourceStage': None, 'record': None,
              'buildKey': None, 'cache': None, 'diagnostics': [],
              'sourceOperations': [], 'datasetAccepted': False, 'goldAdmitted': False}
    try:
        if raw is None:
            report.update(outcome='missing', diagnostics=['binding-metadata-missing'])
            report['metadataStage'] = _stage('held', 'binding-metadata-missing')
            report['sourceStage'] = _stage('held', 'source-operation-not-selected')
            return report
        if not isinstance(raw, bytes) or len(raw) > MAX_METADATA_BYTES:
            raise RefreshError('binding-metadata-size-invalid')
        if len(raw) != binding.metadata_bytes or sha(raw) != binding.metadata_sha256:
            raise RefreshError('binding-metadata-pin-mismatch')
        source = strict_json(raw)
        if not isinstance(source, dict):
            raise RefreshError('binding-metadata-object-required')
        if binding.country not in COUNTRIES or not set(binding.applicability) <= set(TYPES):
            raise RefreshError('binding-applicability-invalid')
        policy = _policy(binding)
        data, origins = {}, {}
        for key, pointer in binding.selectors.items():
            if not re.fullmatch('[a-zA-Z][a-zA-Z0-9]*', key):
                raise RefreshError('binding-field-name-invalid')
            value = None if pointer is None else _pointer(source, pointer)
            data[key] = value
            for datum in datum_pointers(value, '/data/' + key):
                origins[datum] = ({'kind': 'source', 'sourceId': binding.source_id,
                    'releaseId': binding.release_id, 'inputPath': binding.metadata_path,
                    'inputSha256': binding.metadata_sha256, 'sourceRecordId': binding.source_id,
                    'sourceField': pointer + datum[len('/data/' + key):]} if pointer is not None else
                    {'kind': 'constant', 'policySha256': policy, 'symbol': 'unknown-' + key})
        required = {'originalAcquiredAt', 'lastValidatedAt', 'nativeUnits', 'nativeBasis'}
        if not required <= set(data):
            raise RefreshError('binding-required-fields-missing')
        row = {'id': binding.source_id + ':metadata:' + binding.metadata_sha256,
               'kind': 'source-input-binding', 'schemaVersion': 'offmenu-portfolio39-binding/1',
               'data': data, 'provenance': {'sourceId': binding.source_id,
                   'releaseId': binding.release_id, 'fetchedAt': data['originalAcquiredAt'],
                   'fieldOrigins': origins}}
        errors = field_origin_errors(row, {binding.metadata_path: binding.metadata_sha256},
                                    policy_pins=(policy,))
        if errors:
            raise RefreshError(errors[0])
        # Qualification of source coordinates/values is not implied by coverage.
        content = encode_records([row])
        key = sha(canonical({'adapter': 'portfolio39-metadata-v1', 'policy': policy,
                             'input': binding.metadata_sha256, 'content': sha(content)}))
        report.update(record=row, buildKey=key, cache=_cache_view(data, binding, now))
        report['metadataStage'] = _stage('succeeded', 'metadata-binding-valid', (sha(content),), 1)
        if binding.holds:
            report.update(outcome='held', diagnostics=list(binding.holds))
            report['sourceStage'] = _stage('held', 'source-use-held')
        elif report['cache']['decision'] != 'reuse-under-30-days-zero-download':
            report.update(outcome='stale', diagnostics=[report['cache']['decision']])
            report['sourceStage'] = _stage('held', 'source-operation-not-selected')
        else:
            report['outcome'] = 'noop' if previous_key == key else 'valid'
            report['sourceStage'] = _stage('held', 'source-operation-not-selected')
    except (ValueError, TypeError, UnicodeError, OverflowError, RecursionError) as error:
        # Fixed codes only: no paths, receipt snippets, exceptions or secrets in diagnostics.
        code = str(error) if isinstance(error, RefreshError) else 'binding-metadata-malformed'
        report.update(outcome='malformed', diagnostics=[code], record=None, buildKey=None, cache=None,
                      metadataStage=_stage('failed', code),
                      sourceStage=_stage('held', 'source-operation-not-selected'))
    return report


def read_metadata_json(path):
    """Read bounded regular metadata from the same descriptor we validate.

    Nonblocking open rejects a FIFO replacement without waiting for a writer;
    no-follow also closes the final-component symlink replacement window.
    """
    path = safe_path(path)
    if path.suffix != '.json':
        raise RefreshError('binding-metadata-json-required')
    descriptor = os.open(path, os.O_RDONLY | os.O_NONBLOCK | os.O_NOFOLLOW | os.O_CLOEXEC)
    try:
        metadata = os.fstat(descriptor)
        if not stat.S_ISREG(metadata.st_mode) or metadata.st_size > MAX_METADATA_BYTES:
            raise RefreshError('binding-metadata-size-invalid')
        with os.fdopen(descriptor, 'rb', closefd=False) as stream:
            raw = stream.read(MAX_METADATA_BYTES + 1)
        if len(raw) > MAX_METADATA_BYTES:
            raise RefreshError('binding-metadata-size-invalid')
        return raw
    finally:
        os.close(descriptor)


def read_retained_metadata(binding):
    """Only the static configured receipt JSON; never follows raw input paths."""
    try:
        return read_metadata_json(binding.retained_metadata_path)
    except FileNotFoundError:
        return None


def run_portfolio(entries, provider, *, now, previous=None):
    """Provider is metadata-only. A failed peer never prevents other diagnostics."""
    entries = tuple(entries)
    rows = []
    for binding in entries:
        try:
            raw = provider(binding)
        except (OSError, ValueError):
            missing = bind_receipt(binding, None, now=now)
            missing.update(diagnostics=['binding-metadata-unavailable'],
                           metadataStage=_stage('held', 'binding-metadata-unavailable'))
            rows.append(missing)
            continue
        rows.append(bind_receipt(binding, raw, now=now,
                                 previous_key=(previous or {}).get(binding.source_id)))
    cells = []
    for country in COUNTRIES:
        for kind in TYPES:
            selected = [b.source_id for b in entries
                        if b.country == country and kind in b.applicability]
            cells.append({'country': country, 'type': kind, 'sourceIds': selected,
                          'status': 'metadata-only-source-execution-unselected' if selected
                          else 'missing-source-binding', 'accepted': False})
    return {'schemaVersion': 'offmenu-portfolio39-plan/1', 'countries': list(COUNTRIES),
            'scope': 'receipt-metadata-only', 'bindings': rows, 'networkRequests': 0,
            'countryTypes': cells, 'realSourceCapability': 'unsupported-unselected',
            'rawBodyReads': 0, 'datasetAccepted': False, 'countryCoverageComplete': False,
            'goldAdmitted': False}
