"""Worker54 retained metadata bindings; no raw reader, admission or fetch path.

Only the code-owned portfolio configuration supplies declarations and sticky
holds. Observations are metadata assertions, not verification of original bytes.
Shared qualification still needs an independently reviewed SourceContract.
"""
import argparse
from copy import deepcopy

try:
    from jsonschema import Draft202012Validator
except ImportError:
    Draft202012Validator = None

from .acceptance import canonical, fingerprint
from .acquisition import MIN_TTL
from .core import RefreshError, strict_json, timestamp
from .field_provenance import field_origin_errors
from .portfolio54_config import BINDINGS

MAX_METADATA = 64 * 1024
OBSERVATION_SCHEMA = {
    'type': 'object', 'additionalProperties': False,
    'required': ['sourceId', 'releaseId', 'manifestSha256', 'originalSha256',
                 'acquiredAt', 'validatedAt'],
    'properties': {
        **{k: {'type': 'string', 'minLength': 1, 'maxLength': 256}
           for k in ('sourceId', 'releaseId')},
        'manifestSha256': {'type': 'string', 'pattern': '^[a-f0-9]{64}$'},
        'originalSha256': {'anyOf': [{'type': 'null'},
                                  {'type': 'string', 'pattern': '^[a-f0-9]{64}$'}]},
        **{k: {'anyOf': [{'type': 'null'}, {'type': 'string', 'maxLength': 64}]}
           for k in ('acquiredAt', 'validatedAt')},
    },
}


def bindings():
    """Return a fresh copy of reviewed code configuration, never a CLI plugin."""
    config = deepcopy(BINDINGS)
    if config['schemaVersion'] != 'offmenu-worker54-bindings/1':
        raise RefreshError('worker54-binding-version-invalid')
    return config['countries']


def _binding(country):
    try:
        return bindings()[country]
    except (KeyError, TypeError):
        raise RefreshError('worker54-country-not-bound') from None


def _record(binding):
    policy = fingerprint(binding)
    data, origins = {}, {}
    for name, field in binding['fields'].items():
        data[name] = deepcopy(field['value'])
        pointer = '/data/' + name.replace('~', '~0').replace('/', '~1')
        if 'selector' in field:
            origins[pointer] = {
                'kind': 'source', 'sourceId': binding['sourceId'],
                'releaseId': binding['releaseId'],
                'inputPath': binding['manifest']['path'],
                'inputSha256': binding['manifest']['sha256'],
                'sourceRecordId': field['sourceRecordId'],
                'sourceField': field['selector'],
            }
        else:
            origins[pointer] = {'kind': 'constant', 'policySha256': policy,
                                'symbol': field['unknownSymbol']}
    return {
        'id': 'offmenu:worker54:' + binding['country'],
        'kind': 'source-input-binding', 'schemaVersion': 'worker54-metadata/1',
        'country': binding['country'], 'dataType': binding['dataType'],
        'dataTypeApplicability': binding.get('dataTypeApplicability'),
        'requiredDataTypes': list(binding.get('requiredDataTypes', ())),
        'countryDataTypesAccepted': [],
        'declarationOnly': True, 'sourceProcessingAllowed': False,
        'holds': sorted(binding.get('holds', ())),
        'data': data,
        'provenance': {'sourceId': binding['sourceId'],
                       'releaseId': binding['releaseId'],
                       # Timestamp of this retained metadata declaration, NOT
                       # original acquisition or a newly fetched publisher page.
                       'fetchedAt': binding['metadataValidatedAt'],
                       'fieldOrigins': origins},
    }


def metadata_record(country):
    """Code-authored binding declaration; not a normalized source observation."""
    return _record(_binding(country))


def _semantic_errors(binding, row):
    errors = set(field_origin_errors(
        row, {binding['manifest']['path']: binding['manifest']['sha256']},
        policy_pins=(fingerprint(binding),)))
    # Origin coverage alone cannot validate actual selectors/values. Require the
    # exact code-bound declaration too; never infer a raw XLSX/HTML/PDF selector.
    try:
        exact = canonical(row) == canonical(_record(binding))
    except (TypeError, ValueError):
        exact = False
    if not exact:
        errors.add('worker54-declaration-mismatch')
    return sorted(errors)


def metadata_semantic_errors(country, row):
    """Non-mutating SourceContract semantic hook for the metadata scope only."""
    return _semantic_errors(_binding(country), row)


def _plan(binding, observation, *, now, previous_key=None):
    errors, state = set(), 'missing'
    result = {
        'schemaVersion': 'offmenu-worker54-binding-plan/1',
        'country': binding['country'], 'dataType': binding['dataType'],
        'sourceId': binding['sourceId'], 'releaseId': binding['releaseId'],
        'inputStatus': state, 'disposition': 'blocked',
        'holds': sorted(binding['holds']), 'diagnostics': [],
        'originalAgeSeconds': None, 'validationAgeSeconds': None,
        'minimumReuseSeconds': MIN_TTL, 'cacheStatus': 'unknown',
        'replay': 'not-ready', 'replayKey': None,
        'fetchAllowed': False, 'sourceBodyAccessAllowed': False,
        'qualified': False, 'accepted': False,
        'genericPlannerCapability': 'unsupported-at-abecb99',
        'assetVerification': 'not-performed-metadata-assertions-only',
    }
    try:
        clock = timestamp(now)
    except (RefreshError, TypeError):
        errors.add('binding-clock-invalid')
        clock = None
    if observation is None:
        errors.add('input-metadata-missing')
    elif Draft202012Validator is None:
        state = 'malformed'
        errors.add('schema-validator-unavailable')
    elif list(Draft202012Validator(OBSERVATION_SCHEMA).iter_errors(observation)):
        state = 'malformed'
        errors.add('input-metadata-malformed')
    else:
        state = 'valid'
        expected = {
            'sourceId': binding['targetSourceId'],
            'releaseId': binding['targetReleaseId'],
            'manifestSha256': binding['manifest']['sha256'],
            'originalSha256': binding['originalSha256'],
        }
        if any(observation[k] != v for k, v in expected.items()):
            errors.add('input-identity-or-pin-mismatch')
            state = 'malformed'
        acquired = validated = None
        for name, diagnostic in [('acquiredAt', 'acquisition-time-required'),
                                 ('validatedAt', 'validation-time-required')]:
            value = observation[name]
            if value is None:
                errors.add(diagnostic)
                continue
            try:
                moment = timestamp(value)
                if name == 'acquiredAt':
                    acquired = moment
                else:
                    validated = moment
                if clock is not None and moment > clock:
                    errors.add('input-time-in-future')
                    state = 'malformed'
            except (RefreshError, TypeError):
                errors.add('input-time-malformed')
                state = 'malformed'
        # A new validation must never silently renew original acquisition age.
        declared = binding['originalAcquiredAt']
        if declared is None:
            errors.add('original-acquisition-evidence-required')
        elif acquired is not None and acquired != timestamp(declared):
            errors.add('acquisition-time-evidence-mismatch')
            state = 'malformed'
        if acquired is not None and validated is not None and validated < acquired:
            errors.add('validation-before-acquisition')
            state = 'malformed'
        if clock is not None:
            if acquired is not None:
                age = (clock - acquired).total_seconds()
                result['originalAgeSeconds'] = age
                result['cacheStatus'] = ('minimum-reuse-window' if 0 <= age < MIN_TTL
                                         else 'window-elapsed-needs-review')
                if age >= MIN_TTL:
                    errors.add('original-cache-window-elapsed')
            if validated is not None:
                age = (clock - validated).total_seconds()
                result['validationAgeSeconds'] = age
                if age >= MIN_TTL:
                    errors.add('input-validation-stale')
        if state == 'valid' and any(code in errors for code in
                ('original-cache-window-elapsed', 'input-validation-stale')):
            state = 'stale'
        if not errors:
            key = fingerprint({'binding': fingerprint(binding), **expected,
                               'acquiredAt': observation['acquiredAt']})
            result['replayKey'] = key
            result['replay'] = 'noop' if previous_key == key else 'metadata-ready'
    result['inputStatus'] = state
    result['disposition'] = 'held' if binding['holds'] else ('blocked' if errors else 'metadata-ready')
    if binding['holds']:
        errors.add('source-processing-held')
        # A valid descriptor/noop never starts processing through a held source.
        result['replay'] = 'not-ready'
    result['diagnostics'] = sorted(errors)
    return result


def plan(country, observation, *, now, previous_key=None):
    """Pure bounded metadata preflight. No input path/URL is ever dereferenced."""
    return _plan(_binding(country), observation, now=now, previous_key=previous_key)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--country', required=True, choices=('KM', 'KN', 'KP', 'KR'))
    parser.add_argument('--now', required=True, help='Explicit UTC policy clock')
    parser.add_argument('--previous-key')
    group = parser.add_mutually_exclusive_group()
    group.add_argument('--observation', help='Metadata JSON on stdin only; use -')
    group.add_argument('--declaration', action='store_true',
                       help='Emit the code-owned metadata declaration, not source data')
    args = parser.parse_args(argv)
    if args.declaration:
        print(canonical(metadata_record(args.country)).decode())
        return 0  # Declaration emission is not source qualification/admission.
    observation = None
    try:
        if args.observation is not None:
            if args.observation != '-':
                raise RefreshError('metadata-stdin-only')
            import sys
            raw = sys.stdin.buffer.read(MAX_METADATA + 1)
            if len(raw) > MAX_METADATA:
                raise RefreshError('metadata-bound-exceeded')
            observation = strict_json(raw)
        result = plan(args.country, observation, now=args.now,
                      previous_key=args.previous_key)
    except (RefreshError, ValueError, UnicodeError, RecursionError):
        # A byte-bounded request can still exceed the JSON decoder's depth.
        # Fixed codes only: no raw metadata, path, URL or exception text in logs.
        result = {'schemaVersion': 'offmenu-worker54-binding-plan/1',
                  'country': args.country, 'inputStatus': 'malformed',
                  'diagnostics': ['metadata-request-invalid'],
                  'fetchAllowed': False, 'sourceBodyAccessAllowed': False,
                  'qualified': False, 'accepted': False}
    print(canonical(result).decode())
    return 0 if result.get('disposition') == 'metadata-ready' else 2


if __name__ == '__main__':
    raise SystemExit(main())
