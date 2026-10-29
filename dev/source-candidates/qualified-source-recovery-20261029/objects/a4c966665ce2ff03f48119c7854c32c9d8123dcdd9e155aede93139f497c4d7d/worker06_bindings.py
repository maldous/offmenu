"""ME/MF/MG/MH metadata bindings; no payload reader, downloader or admission.

Use shared strict JSON, timestamp, fingerprints and per-datum origin validation.
This portfolio module only projects pinned validation metadata. It cannot create
a trusted SourceContract or enable a production source from a descriptor.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import stat

from .acceptance import fingerprint
from .acquisition import MIN_TTL
from .core import RefreshError, strict_json, timestamp
from .field_provenance import field_origin_errors

VERSION = 'worker06-metadata-binding/1'
POLICY = fingerprint({'version': VERSION, 'scope': 'metadata-only',
                      'unknown': None, 'minimumReuseSecondsRequired': MIN_TTL,
                      'cachePlanning': 'unsupported-real-source-cache-planner'})
MAX_METADATA = 128 * 1024
DEFAULT_CONFIG = Path(__file__).resolve().parents[2] / 'docs/operations/worker06-staging-bindings.json'


def load_config(path=DEFAULT_CONFIG):
    """Load reviewed portfolio configuration, never a SourceContract factory."""
    config = strict_json(Path(path).read_bytes())
    if config.get('schemaVersion') != VERSION or not isinstance(config.get('bindings'), list):
        raise RefreshError('binding-config-invalid')
    ids = [b['id'] for b in config['bindings']]
    if len(set(ids)) != len(ids):
        raise RefreshError('binding-id-duplicate')
    return config


def _pointer(value, pointer):
    if not isinstance(pointer, str) or not pointer.startswith('/'):
        raise ValueError('selector-invalid')
    for part in pointer[1:].split('/'):
        part = part.replace('~1', '/').replace('~0', '~')
        value = value[int(part)] if isinstance(value, list) else value[part]
    return value


def _clock(value):
    # Reuse shared UTC-only timestamp contract. Clock is always caller supplied.
    return timestamp(value)


def assess(binding, metadata, *, now, previous_fingerprint=None):
    """Return deterministic, isolated metadata diagnostics without any I/O.

    metadata is the bytes of the exact *validation manifest*, not an original
    PDF/HTML body. A valid result means metadata validity only. Rights and missing
    body selectors are independent blockers and cannot be cleared by these bytes.
    Timestamp age is observation only; no generic cache planner exists at base.
    """
    result = {'schemaVersion': VERSION, 'bindingId': binding['id'],
              'country': binding['country'], 'status': 'malformed',
              'diagnostics': [], 'blockers': list(binding['blockers']),
              'candidate': None, 'candidateFingerprint': None,
              'metadataReplay': 'none',
              'cacheDecision': 'unsupported-real-source-cache-planner',
              'freshness': 'unknown', 'minimumReuseSecondsRequired': MIN_TTL,
              'acquisitionAgeSeconds': None, 'validationAgeSeconds': None,
              'validationResetsAcquisitionAge': False,
              'networkRequests': 0, 'assetBytesVerified': False,
              'payloadProcessingAuthorized': False, 'acceptedRecords': 0,
              'countryComplete': False}
    errors = set()
    try:
        current = _clock(now)
        acquired_text = binding['originalAcquiredAt']
        acquired = _clock(acquired_text) if acquired_text is not None else None
        validated = _clock(binding['integrityValidatedAt'])
        if validated > current or (acquired is not None and (acquired > current or acquired > validated)):
            errors.add('timestamp-order-invalid')
        result['acquisitionAgeSeconds'] = (current - acquired).total_seconds() if acquired else None
        result['validationAgeSeconds'] = (current - validated).total_seconds()
        if metadata is None:
            result.update(status='missing', diagnostics=['metadata-input-missing'])
            return result
        if not isinstance(metadata, bytes) or len(metadata) > MAX_METADATA:
            raise ValueError('metadata-bound-invalid')
        parsed = strict_json(metadata)
        # Parse first so malformed/duplicate JSON remains distinct from drift.
        pin = binding['metadataAsset']
        if len(metadata) != pin['bytes'] or hashlib.sha256(metadata).hexdigest() != pin['sha256']:
            result.update(status='stale', diagnostics=['metadata-pin-mismatch'])
            return result
        data, origins = {}, {}
        for field, declaration in binding['fields'].items():
            selector = declaration['selector']
            if selector is None:
                data[field] = None
                origins['/data/' + field] = {'kind': 'constant', 'policySha256': POLICY,
                                            'symbol': 'explicit-unknown'}
            else:
                value = _pointer(parsed, selector)
                if value != declaration['expected'] or not isinstance(value, (str, int, float, bool, type(None))):
                    errors.add('metadata-selector-value-mismatch')
                data[field] = value
                origins['/data/' + field] = {
                    'kind': 'source', 'sourceId': binding['sourceId'],
                    'releaseId': binding['releaseId'], 'inputPath': pin['logicalPath'],
                    'inputSha256': pin['sha256'], 'sourceRecordId': binding['recordSelector'],
                    'sourceField': selector}
        candidate = {'id': binding['id'], 'kind': 'source-input-binding-metadata',
                     'schemaVersion': VERSION, 'data': data,
                     'provenance': {'sourceId': binding['sourceId'], 'releaseId': binding['releaseId'],
                                    'fieldOrigins': origins}}
        errors.update(field_origin_errors(candidate, {pin['logicalPath']: pin['sha256']},
                                          policy_pins=(POLICY,)))
        if errors:
            result['diagnostics'] = sorted(errors)
            return result
        content = fingerprint({'binding': binding, 'candidate': candidate, 'policy': POLICY})
        result.update(candidate=candidate, candidateFingerprint=content,
                      metadataReplay='unchanged-no-op' if previous_fingerprint == content else 'new-metadata',
                      status='held' if result['blockers'] else 'valid')
        return result
    except (ValueError, TypeError, KeyError, IndexError, OverflowError):
        result['diagnostics'] = sorted(errors | {'metadata-contract-malformed'})
        return result


def assess_all(config, metadata_by_id, *, now, previous=None):
    """One bad source never prevents independent portfolio results."""
    previous = previous or {}
    return [assess(b, metadata_by_id.get(b['id']), now=now,
                   previous_fingerprint=previous.get(b['id'])) for b in config['bindings']]


def read_metadata(binding):
    """Read only the exact retained validation metadata path, bounded; no bodies.

    Source/custody assets embedded in the descriptor are inert pointers. This
    helper never dereferences them or searches for replacement files.
    """
    from .core import safe_path
    path = safe_path(binding['metadataAsset']['path'])
    directory = None
    descriptor = None
    try:
        # Follow no directory or final-component symlink, even if the path is
        # swapped after safe_path. NONBLOCK prevents a raced FIFO open hanging.
        flags = os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC
        directory = os.open(path.anchor, flags | os.O_DIRECTORY)
        for part in path.parts[1:-1]:
            child = os.open(part, flags | os.O_DIRECTORY, dir_fd=directory)
            os.close(directory)
            directory = child
        descriptor = os.open(path.name, flags | os.O_NONBLOCK, dir_fd=directory)
        before = os.fstat(descriptor)
        if not stat.S_ISREG(before.st_mode) or before.st_size > MAX_METADATA:
            raise RefreshError('metadata-regular-file-required')
        with os.fdopen(descriptor, 'rb') as stream:
            descriptor = None  # stream owns this descriptor from here.
            raw = stream.read(MAX_METADATA + 1)
            after = os.fstat(stream.fileno())
        if (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns, before.st_ctime_ns) != (
                after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns, after.st_ctime_ns):
            raise RefreshError('metadata-changed-during-read')
        if len(raw) != before.st_size or len(raw) > MAX_METADATA:
            raise RefreshError('metadata-read-bound-invalid')
        return raw  # assess separately enforces the exact expected byte/hash pin.
    except FileNotFoundError:
        return None
    finally:
        if descriptor is not None:
            os.close(descriptor)
        if directory is not None:
            os.close(directory)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--now', required=True, help='Explicit UTC timestamp')
    parser.add_argument('--previous', type=Path, help='Prior JSON output, for metadata no-op comparison')
    args = parser.parse_args(argv)
    config = load_config()
    previous = {}
    if args.previous:
        try:
            raw = read_metadata({'metadataAsset': {'path': str(args.previous)}})
            if raw is None:
                raise RefreshError('previous-report-missing')
            report = strict_json(raw)
            if not isinstance(report, list):
                raise RefreshError('previous-report-invalid')
            for row in report:
                if (not isinstance(row, dict) or not isinstance(row.get('bindingId'), str)
                        or not row['bindingId'] or row['bindingId'] in previous
                        or (row.get('candidateFingerprint') is not None
                            and (not isinstance(row['candidateFingerprint'], str)
                                 or len(row['candidateFingerprint']) != 64
                                 or any(c not in '0123456789abcdef' for c in row['candidateFingerprint'])))):
                    raise RefreshError('previous-report-invalid')
                previous[row['bindingId']] = row.get('candidateFingerprint')
        except (OSError, ValueError, TypeError, RecursionError):
            parser.error('previous-report-unreadable-or-invalid')
    results = []
    for binding in config['bindings']:
        try:
            metadata = read_metadata(binding)
            results.append(assess(binding, metadata, now=args.now, previous_fingerprint=previous.get(binding['id'])))
        except (OSError, RefreshError):
            result = assess(binding, None, now=args.now)
            result['diagnostics'] = ['metadata-read-failed']
            results.append(result)
    print(json.dumps(results, sort_keys=True, ensure_ascii=False, allow_nan=False))
    return 0 if all(r['status'] in ('valid', 'held') for r in results) else 1


if __name__ == '__main__':
    raise SystemExit(main())
