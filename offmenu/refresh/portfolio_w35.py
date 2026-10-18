"""GY/HK/HM/HN metadata bindings; no source reader, acquisition or admission.

The checked-in table is reviewed-code configuration, never a CLI-supplied
SourceContract. Evidence declarations are checked, not promoted to byte custody.
Use the existing acceptance/isolation boundary for any later payload operation.
"""
import argparse
from copy import deepcopy
import json
import os
from pathlib import Path
import stat

from .acceptance import fingerprint
from .acquisition import MIN_TTL
from .core import strict_json, timestamp
from .field_provenance import field_origin_errors
from .global_run import StageResult

CONFIG = Path(__file__).with_name('portfolio_w35.json')
MAX_METADATA = 64 * 1024
MAX_PACKETS = 32


def bindings():
    """Return an independent copy of the fixed portfolio configuration."""
    return deepcopy(strict_json(CONFIG.read_bytes())['bindings'])


def _check(packet, spec, now, previous_key):
    errors = set()
    required = {'schemaVersion', 'bindingId', 'sourceId', 'releaseId',
                'manifestPins', 'originalAcquiredAt', 'metadataValidatedAt',
                'inputSha256', 'fieldDeclarations'}
    if set(packet) != required or packet.get('schemaVersion') != 'offmenu-w35-input-metadata/1':
        errors.add('metadata-shape-invalid')
    if any(packet.get(k) != spec[k] for k in ('sourceId', 'releaseId')):
        errors.add('source-release-mismatch')
    pins = packet.get('manifestPins')
    if pins != spec['manifestPins']:
        errors.add('retained-manifest-pin-mismatch')
    if not spec['inputSha256']:
        errors.add('payload-pin-missing')
    elif packet.get('inputSha256') != spec['inputSha256']:
        errors.add('input-pin-mismatch')
    acquisition_age = validation_age = None
    for key in ('originalAcquiredAt', 'metadataValidatedAt'):
        if packet.get(key) is None:
            errors.add('original-acquisition-time-missing' if key == 'originalAcquiredAt'
                       else 'metadata-validation-time-missing')
    acquired = validated = None
    try:
        validated = timestamp(packet['metadataValidatedAt'])
        if validated > now:
            errors.add('metadata-time-order-invalid')
        else:
            validation_age = int((now - validated).total_seconds())
    except (ValueError, TypeError, KeyError):
        errors.add('metadata-time-invalid')
    try:
        acquired = timestamp(packet['originalAcquiredAt'])
        if validated is None or not acquired <= validated <= now:
            errors.add('metadata-time-order-invalid')
        else:
            acquisition_age = int((now - acquired).total_seconds())
    except (ValueError, TypeError, KeyError):
        errors.add('metadata-time-invalid')
    declarations = packet.get('fieldDeclarations')
    expected = spec['fields']
    if not expected:
        errors.add('field-selector-contract-missing')
    if declarations != expected:
        errors.add('field-selector-contract-mismatch')
    # Reuse the shared per-datum origin validator for declared native fields.
    # Nulls here are declaration placeholders, not source null observations.
    if expected and declarations == expected:
        row = {'data': {k: None for k in expected},
               'provenance': {'sourceId': spec['sourceId'], 'releaseId': spec['releaseId'],
                              'fieldOrigins': {}}}
        for name, field in expected.items():
            row['provenance']['fieldOrigins']['/data/' + name] = {
                'kind': 'source', 'sourceId': spec['sourceId'],
                'releaseId': spec['releaseId'], 'inputPath': spec['inputPath'],
                'inputSha256': spec['inputSha256'],
                'sourceRecordId': field['recordSelector'],
                'sourceField': field['fieldSelector']}
        errors.update(field_origin_errors(row, {spec['inputPath']: spec['inputSha256']}))
    # Observations/validation times never reset original acquisition age or keys.
    identity = {k: spec[k] for k in ('bindingId', 'sourceId', 'releaseId', 'country',
                                     'dataType', 'inputPath', 'inputSha256', 'manifestPins',
                                     'fields', 'basis', 'holds', 'unknowns')}
    key = fingerprint(identity)
    if spec['holds']:
        state = 'held'
    elif errors:
        state = 'missing-input' if any(e.endswith('-missing') for e in errors) else 'malformed-input'
    elif acquisition_age >= MIN_TTL:
        state = 'stale-input'
        errors.add('conditional-validation-review-required')
    else:
        state = 'no-op' if previous_key == key else 'metadata-ready'
    return {**_base(spec['bindingId']), 'country': spec['country'],
            'dataType': spec['dataType'], 'sourceId': spec['sourceId'],
            'releaseId': spec['releaseId'], 'status': state,
            'errors': sorted(errors), 'holds': spec['holds'], 'unknowns': spec['unknowns'],
            'bindingKey': key, 'originalAcquisitionAgeSeconds': acquisition_age,
            'metadataValidationAgeSeconds': validation_age,
            'cacheDecision': ('zero-download-reuse-window' if acquisition_age is not None
                              and 0 <= acquisition_age < MIN_TTL else
                              'review-required-no-download'),
            'minimumReuseSeconds': MIN_TTL,
            'nextAction': {'metadata-ready': 'review-metadata-binding',
                           'no-op': 'retain-identical-binding',
                           'held': 'resolve-exact-operation-holds',
                           'stale-input': 'review-conditional-validation-with-existing-owner',
                           'missing-input': 'supply-exact-missing-metadata',
                           'malformed-input': 'correct-metadata-contract'}[state]}


def _base(binding_id):
    return {'schemaVersion': 'offmenu-w35-binding-diagnostic/1',
            'bindingId': binding_id, 'networkRequests': 0,
            'assetBytesVerified': False, 'sourceProcessingAuthorized': False,
            'observationTimesVerified': False,
            'datasetAccepted': False, 'countryComplete': False,
            'goldAdmitted': False, 'normalizedRecords': 0}


def assess(packet, *, now, previous_key=None):
    """One isolated, deterministic metadata result; no source bytes are opened.

now is explicit UTC. previous_key is a prior bindingKey, not acceptance proof.
No fresh validation/mtime/landing page can override a code-bound source hold.
"""
    identity = packet.get('bindingId') if isinstance(packet, dict) else None
    spec = next((s for s in bindings() if s['bindingId'] == identity), None)
    try:
        now = timestamp(now)
        if spec is None:
            raise ValueError()
        return _check(packet, spec, now, previous_key)
    except (ValueError, TypeError, KeyError, OverflowError):
        return {**_base(spec['bindingId'] if spec else None),
                'status': 'malformed-input', 'errors': ['metadata-contract-invalid'],
                'holds': spec['holds'] if spec else [],
                'nextAction': 'correct-metadata-contract'}


def diagnose(raw, *, now):
    """Bounded JSON interface; a bad packet does not suppress independent peers."""
    try:
        if not isinstance(raw, bytes) or len(raw) > MAX_METADATA:
            raise ValueError()
        packets = strict_json(raw)
        if not isinstance(packets, list) or not 1 <= len(packets) <= MAX_PACKETS:
            raise ValueError()
    except (ValueError, UnicodeError, TypeError, RecursionError):
        return [assess(None, now=now)]
    return [assess(packet, now=now) for packet in packets]


def metadata_stage_result(report):
    """Shared StageResult for a metadata check only, never parse/accept binding."""
    state = report['status']
    status = ('reused' if state == 'no-op' else 'succeeded' if state == 'metadata-ready'
              else 'held' if state in ('held', 'missing-input', 'stale-input') else 'failed')
    return StageResult(status, 'portfolio-metadata-' + state,
                       (fingerprint(report),)).receipt()


def read_metadata(path):
    """Read bounded regular input from one checked, nonblocking descriptor.

    Reject final-component symlinks and nonregular files before reading. A path
    replacement after fstat cannot redirect this read or turn it into FIFO open.
    """
    descriptor = os.open(path, os.O_RDONLY | os.O_NONBLOCK | os.O_NOFOLLOW | os.O_CLOEXEC)
    try:
        info = os.fstat(descriptor)
        if not stat.S_ISREG(info.st_mode) or info.st_size > MAX_METADATA:
            raise ValueError('metadata-file-invalid')
        with os.fdopen(descriptor, 'rb', closefd=False) as stream:
            return stream.read(MAX_METADATA + 1)
    finally:
        os.close(descriptor)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--metadata', type=Path)
    parser.add_argument('--now', required=True, help='explicit UTC policy clock')
    args = parser.parse_args()
    if args.metadata:
        try:
            raw = read_metadata(args.metadata)
        except (OSError, ValueError):
            raw = b''
        result = diagnose(raw, now=args.now)
    else:
        result = bindings()
    print(json.dumps(result, sort_keys=True, ensure_ascii=False, allow_nan=False))


if __name__ == '__main__':
    main()
