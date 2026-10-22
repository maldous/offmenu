"""Portfolio42 binding for existing IN reference metadata, never source admission.

No filesystem/network/AI operations in prepare(). Inputs are bounded buffers
supplied by an independently selected execution caller. Shared core stays intact.
"""
from copy import deepcopy
from dataclasses import dataclass
import sys

from jsonschema import Draft202012Validator
from .acquisition import MIN_TTL
from .core import RefreshError, canonical, sha, strict_json, timestamp
from .field_provenance import datum_pointers, field_origin_errors
from .serialization import CONTENT_POLICY, asset, encode_records

SOURCE = 'dietary-guidelines'
RELEASE = 'fao-directory-20261013'
IDENTITY = 'dietary-guidelines:sourceAssertion:IN'
SCOPE = 'IN-own-reference-metadata-only-v1'
MAX_INPUT = 64 * 1024
DATA_FIELDS = ('name', 'referenceType', 'referenceUrl', 'directoryUrl',
               'reviewStatus', 'contentPermission', 'qualificationStatus')
LICENCE = 'CC0 1.0 for OffMenu original reference metadata; linked documents retain national owner rights'
PERMISSION = 'national copyright-holder permission required before document republication'
POLICY = {'scope': SCOPE, 'recordSelector': '/record', 'dataFields': DATA_FIELDS,
          'nativeUnits': None, 'quantityBasis': None,
          'noNationalDocumentRights': True, 'serialization': CONTENT_POLICY}
POLICY_SHA256 = sha(canonical(POLICY))
PORTFOLIO_HOLDS = {
    'IM': ('source-use-unresolved', 'currency-portion-unknown'),
    'IO': ('applicable-source-missing',),
    'IQ': ('source-custody-unestablished', 'derivative-use-not-held'),
}


@dataclass(frozen=True)
class Pin:
    path: str
    bytes: int
    sha256: str


@dataclass(frozen=True)
class Binding:
    """Trusted application configuration, never constructed from input JSON."""
    input: Pin
    rights: Pin
    scope: Pin
    original_acquired_at: str
    holds: tuple = ()
    upstream_sha256: str = "5fd9e0bae196ff4bb347d9036a0d3e735f19329e13eb67b9aa5e309ceec0ce5d"

    def pins(self):
        return tuple(dict(vars(p)) for p in (self.input, self.rights, self.scope))


# Only retained own-reference metadata is selected, not a national document.
RETAINED = Binding(
    Pin('reference-wrapper.json', 2319, '1f04c3ff5f532a0778c12e0852e75f08b95496a06b1fd6a533418491e749bcfd'),
    Pin('rights.json', 817, 'b7ea4c7c11e92507956025e07db1020fea9e91e543be694a7a22e5114b0a8941'),
    Pin('scope.json', 7787, '1d29bc6deb0ca642358a0c821425e13adcad354171bb1203ac0c5d12cfe94777'),
    '2026-10-13T07:13:20.585551+00:00')

RECORD_SCHEMA = {
    'type': 'object', 'additionalProperties': False,
    'required': ['schemaVersion', 'kind', 'id', 'countries', 'provenance', 'data'],
    'properties': {
        'schemaVersion': {'const': '1.0'}, 'kind': {'const': 'sourceAssertion'},
        'id': {'const': IDENTITY}, 'countries': {'const': ['IN']},
        'provenance': {'type': 'object', 'additionalProperties': False, 'required': ['sourceId', 'releaseId', 'recordId',
            'fetchedAt', 'license', 'attribution', 'rights'], 'properties': {
            'url': {'type': 'string', 'minLength': 1}, 'visibility': {'const': 'public'},
            'sourceDate': {'type': 'string'}, 'transform': {'const': 'offmenu-guideline-reference/1'},
            'fieldOrigins': {'type': 'object'},
            'sourceId': {'const': SOURCE}, 'releaseId': {'const': RELEASE},
            'recordId': {'const': 'IN'}, 'fetchedAt': {'type': 'string'},
            'license': {'const': LICENCE}, 'attribution': {'type': 'string', 'minLength': 1},
            'rights': {'const': 'FAO says permission for further use of country materials must be obtained from the copyright holder.'}}},
        'data': {'type': 'object', 'additionalProperties': False,
                 'required': list(DATA_FIELDS), 'properties': {
                     **{k: {'type': 'string', 'minLength': 1} for k in DATA_FIELDS},
                     'referenceType': {'const': 'national-dietary-guideline-directory-entry'},
                     'reviewStatus': {'const': 'directory-entry-observed'},
                     'contentPermission': {'const': PERMISSION},
                     'qualificationStatus': {'const': 'reference only; no personal diet recommendations or verified certification'}}}}
}


def describe():
    return {'sourceId': SOURCE, 'releaseId': RELEASE, 'scope': SCOPE,
            'country': 'IN', 'type': 'dietary-reference-metadata',
            'recordSelector': '/record', 'upstreamSelector': {'logicalLine': 47, 'index': 0},
            'inputs': list(RETAINED.pins()), 'originalAcquiredAt': RETAINED.original_acquired_at,
            'fieldSelectors': {p: '/record' + p for p in datum_pointers({k: None for k in DATA_FIELDS})},
            'nativeUnits': None, 'quantityBasis': None,
            'nativeDimensionMeaning': 'not-applicable-to-directory-strings; no nutrient/unit conversion',
            'minimumReuseSeconds': MIN_TTL, 'policySha256': POLICY_SHA256,
            'sourceAdmissionInstalled': False, 'goldAdmitted': False,
            'reviewRequired': True, 'heldCountries': PORTFOLIO_HOLDS}


def semantics(record, binding):
    """Exact source-specific shape plus shared per-datum origin coverage checks."""
    issues = []
    if not Draft202012Validator(RECORD_SCHEMA).is_valid(record):
        issues.append('reference-schema-invalid')
    if isinstance(record, dict):
        provenance = record.get('provenance', {})
        if isinstance(provenance, dict) and provenance.get('fetchedAt') != binding.original_acquired_at:
            issues.append('original-acquisition-mismatch')
    issues.extend(field_origin_errors(record, {binding.input.path: binding.input.sha256}))
    if isinstance(record, dict) and isinstance(record.get('data'), dict):
        provenance = record.get('provenance', {})
        origins = provenance.get('fieldOrigins', {}) if isinstance(provenance, dict) else {}
        for pointer in datum_pointers(record['data']):
            expected = {'kind': 'source', 'sourceId': SOURCE, 'releaseId': RELEASE,
                        'inputPath': binding.input.path, 'inputSha256': binding.input.sha256,
                        'sourceRecordId': 'IN', 'sourceField': '/record' + pointer}
            if origins.get(pointer) != expected:
                issues.append('reference-selector-mismatch')
    return sorted(set(issues))


def prepare(payload, *, binding=RETAINED, country='IN', now, validated_at=None,
            previous_build_key=None):
    """Return typed proposal/diagnostics; never read a path or fetch/accept data.

A caller may add a hold in trusted configuration, never waive one through source
metadata. Validation age is reported separately and never resets acquisition age.
The stale outcome requires external review; it cannot initiate an online refresh.
"""
    result = {'status': None, 'diagnostics': [], 'records': [], 'manifest': None,
              'buildKey': None, 'networkRequests': 0, 'admission': False,
              'countryComplete': False, 'goldAdmitted': False,
              'cache': {'originalAcquiredAt': binding.original_acquired_at,
                        'validatedAt': validated_at, 'minimumReuseSeconds': MIN_TTL,
                        'acquisitionAgeSeconds': None, 'validationAgeSeconds': None,
                        'decision': 'no-input-action', 'onlineRefreshEnabled': False}}
    def stop(status, *codes):
        result.update(status=status, diagnostics=sorted(set(codes)))
        return result
    if country in PORTFOLIO_HOLDS:
        return stop('held', *PORTFOLIO_HOLDS[country])
    if country != 'IN':
        return stop('held', 'country-not-in-binding')
    if binding.holds:
        return stop('held', 'source-held')
    try:
        instant = timestamp(now)
        acquired = timestamp(binding.original_acquired_at)
        age = (instant - acquired).total_seconds()
        if age < 0:
            return stop('malformed', 'acquisition-timestamp-in-future')
        if validated_at is not None:
            validated = timestamp(validated_at)
            if not acquired <= validated <= instant:
                return stop('malformed', 'validation-time-outside-source-window')
            result['cache']['validationAgeSeconds'] = (instant - validated).total_seconds()
        result['cache']['acquisitionAgeSeconds'] = age
        if any(type(p.bytes) is not int or not 0 < p.bytes <= MAX_INPUT
               or len(p.sha256) != 64 or any(c not in '0123456789abcdef' for c in p.sha256)
               or not p.path or '/' in p.path or '\\' in p.path or p.path in ('.', '..')
               for p in (binding.input, binding.rights, binding.scope)):
            return stop('malformed', 'binding-pin-invalid')
        if len({p.path for p in (binding.input, binding.rights, binding.scope)}) != 3:
            return stop('malformed', 'binding-pin-invalid')
        if payload is None:
            return stop('missing', 'retained-input-required')
        if not isinstance(payload, bytes) or len(payload) > MAX_INPUT:
            return stop('malformed', 'metadata-input-bound-or-type')
        if asset(payload) != {'bytes': binding.input.bytes, 'sha256': binding.input.sha256}:
            return stop('stale', 'input-pin-mismatch')
        wrapper = strict_json(payload)
        if (not isinstance(wrapper, dict) or wrapper.get('country') != 'IN'
                or type(wrapper.get('recordCount')) is not int or wrapper['recordCount'] != 1):
            return stop('malformed', 'reference-wrapper-invalid')
        if (not isinstance(wrapper.get('source'), dict)
                or wrapper['source'].get('sha256') != binding.upstream_sha256
                or wrapper.get('selector') != {'logicalLine': 47, 'index': 0}
                or any(type(wrapper['selector'].get(k)) is not int for k in ('logicalLine', 'index'))):
            return stop('malformed', 'upstream-selector-or-pin-mismatch')
        record = deepcopy(wrapper.get('record'))
        if not isinstance(record, dict) or not isinstance(record.get('provenance'), dict):
            return stop('malformed', 'reference-record-required')
        # Existing source origins cannot silently be overwritten by a new mapper.
        if 'fieldOrigins' in record['provenance']:
            return stop('held', 'preexisting-field-origins-require-review')
        if not isinstance(record.get('data'), dict):
            return stop('malformed', 'reference-data-required')
        record['provenance']['fieldOrigins'] = {
            pointer: {'kind': 'source', 'sourceId': SOURCE, 'releaseId': RELEASE,
                      'inputPath': binding.input.path, 'inputSha256': binding.input.sha256,
                      'sourceRecordId': 'IN', 'sourceField': '/record' + pointer}
            for pointer in datum_pointers(record['data'])}
        issues = semantics(record, binding)
        if issues:
            return stop('malformed', *issues)
        if age >= MIN_TTL:
            result['cache']['decision'] = 'conditional-review-required-no-download'
            return stop('stale', 'cache-age-requires-review')
        content = encode_records([record])
        manifest = {'sourceId': SOURCE, 'releaseId': RELEASE,
                    'acquiredAt': binding.original_acquired_at,
                    'normalizedRecords': 1, 'candidateSha256': sha(content),
                    'candidateBytes': len(content), 'inputFiles': list(binding.pins()),
                    'rightsEvidenceSha256': binding.rights.sha256,
                    'scopeEvidenceSha256': binding.scope.sha256,
                    'scope': SCOPE, 'status': 'candidate-only'}
        key = sha(canonical({'inputs': list(binding.pins()), 'policy': POLICY_SHA256,
                             'scope': SCOPE, 'candidateSha256': manifest['candidateSha256']}))
        result.update(status='candidate-ready', records=[record], manifest=manifest, buildKey=key)
        result['cache']['decision'] = 'verified-no-op' if previous_build_key == key else 'reuse-retained-input'
        return result
    except (RefreshError, ValueError, TypeError, KeyError, AttributeError, OverflowError):
        return stop('malformed', 'metadata-or-time-malformed')


def main():
    """Offline diagnostics only. No URL, plugin, grant or force-download flag."""
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--describe', action='store_true')
    parser.add_argument('--now')
    parser.add_argument('--validated-at')
    parser.add_argument('--country', default='IN')
    parser.add_argument('--previous-build-key')
    args = parser.parse_args()
    if args.describe:
        print(canonical(describe()).decode(), end='')
        return 0
    if args.now is None:
        parser.error('--now is required for deterministic diagnostics')
    options = dict(now=args.now, validated_at=args.validated_at,
                   country=args.country, previous_build_key=args.previous_build_key)
    # Apply the existing country/binding/clock gates before consuming ingress.
    result = prepare(None, **options)
    if result['status'] == 'missing':
        payload = sys.stdin.buffer.read(MAX_INPUT + 1)
        result = prepare(payload or None, **options)
    print(canonical(result).decode(), end='')
    return 0 if result['status'] == 'candidate-ready' else 2


if __name__ == '__main__':
    raise SystemExit(main())
