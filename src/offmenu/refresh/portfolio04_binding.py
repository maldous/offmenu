"""Worker04 retained metadata bindings; no source body reader or admissions.

The bundled profile is reviewed code configuration, not a user permission file.
All I/O is restricted to its pinned JSON evidence. Original asset paths are data
only and are never opened, statted or hashed. Pure evaluate() also accepts small
authored fixtures. No download/execution/acceptance callbacks are installed.
"""
import argparse
from copy import deepcopy
import hashlib
import os
from pathlib import Path
import re
import stat
import sys

from .acceptance import canonical, fingerprint
from .acquisition import MIN_TTL
from .core import strict_json, timestamp
from .field_provenance import field_origin_errors
from .reference_adapters import candidate_bytes
from .portfolio04_catalogue import CATALOGUE

# Source-checkout JSON mirror for equivalence tests/documentation, not runtime input.
PROFILE = Path(__file__).resolve().parents[3] / 'config/portfolio04-staging-bindings.json'
MAX_EVIDENCE = 2 * 1024**2
MAX_TOTAL = 16 * 1024**2
PORTFOLIO = frozenset(('AE', 'CH', 'GL', 'KZ'))
POLICY = fingerprint({'binding': 'portfolio04-metadata/1', 'unknown': None,
                      'bodyOperations': False, 'minimumReuseSeconds': MIN_TTL})
HEX = re.compile('[0-9a-f]{64}')


def load_catalogue():
    """Portable installed code resource; callers cannot mutate later loads."""
    return deepcopy(CATALOGUE)


def pointer(document, selector):
    """Strict RFC6901 lookup, not JSONPath or an executable expression."""
    if not isinstance(selector, str) or not selector.startswith('/'):
        raise ValueError('selector-invalid')
    value = document
    for part in selector.split('/')[1:]:
        if re.search(r'~(?![01])', part):
            raise ValueError('selector-invalid')
        key = part.replace('~1', '/').replace('~0', '~')
        if isinstance(value, list):
            if not re.fullmatch('0|[1-9][0-9]*', key):
                raise ValueError('selector-invalid')
            value = value[int(key)]
        else:
            value = value[key]
    return value


def metadata_semantic_errors(row, documents):
    """Shared SourceContract callback for this metadata-only candidate shape.

    documents uses the same logical *.json names as field_origin_errors pins.
    This checks coordinate/value equality, including null/bool/zero distinctions;
    it does not validate units or any held source-body datum.
    """
    errors = set()
    try:
        for field, value in row['data'].items():
            target = '/data/' + field.replace('~', '~0').replace('/', '~1')
            origin = row['provenance']['fieldOrigins'][target]
            if origin['kind'] == 'source':
                if (origin['sourceRecordId'] != row['id'] or canonical(value) != canonical(
                        pointer(documents[origin['inputPath']], origin['sourceField']))):
                    errors.add('metadata-origin-value-mismatch')
            elif (origin['kind'] != 'constant' or value is not None
                    or origin.get('policySha256') != POLICY
                    or origin.get('symbol') != 'explicit-unknown:' + field):
                errors.add('metadata-unknown-policy-mismatch')
    except (ValueError, KeyError, TypeError, IndexError, RecursionError):
        errors.add('metadata-origin-unresolved')
    return sorted(errors)


def _profile(profile):
    if not isinstance(profile, dict) or profile.get('schemaVersion') != 'portfolio04-bindings/1':
        raise ValueError('profile-invalid')
    evidence, bindings = profile.get('evidence'), profile.get('bindings')
    if (not isinstance(evidence, dict) or not 0 < len(evidence) <= 128
            or not isinstance(bindings, list) or not 0 < len(bindings) <= 64):
        raise ValueError('profile-bounds-invalid')
    for key, asset in evidence.items():
        if (not isinstance(key, str) or not re.fullmatch('[a-z0-9._-]+', key)
                or not isinstance(asset, dict) or set(asset) != {'path', 'sha256', 'bytes'}
                or not isinstance(asset['path'], str) or not asset['path'].endswith('.json')
                or not isinstance(asset['sha256'], str) or not HEX.fullmatch(asset['sha256'])
                or type(asset['bytes']) is not int or not 0 < asset['bytes'] <= MAX_EVIDENCE):
            raise ValueError('metadata-pin-invalid')
    if sum(a['bytes'] for a in evidence.values()) > MAX_TOTAL:
        raise ValueError('metadata-total-limit')
    ids = [b.get('id') for b in bindings if isinstance(b, dict)]
    if (len(ids) != len(bindings) or any(not isinstance(i, str) or not i for i in ids)
            or len(set(ids)) != len(ids)):
        raise ValueError('binding-identity-invalid')
    return evidence, bindings


def read_metadata(profile):
    """Read only the static profile's explicit metadata pins, never asset paths.

    Failure is isolated per evidence item. Missing/type/permission/size failures
    become missing evidence in evaluate(); malformed bytes keep their own code.
    The actual descriptor is opened nonblocking/no-follow and must match the
    checked regular pathname before and after reading. No directories are
    inventoried and no source paths/selectors are followed.
    """
    evidence, _ = _profile(profile)
    result = {}
    for key, asset in evidence.items():
        path = Path(asset['path'])
        try:
            if any(p.is_symlink() for p in (path, *path.parents)):
                continue
            before = path.stat(follow_symlinks=False)
            if not stat.S_ISREG(before.st_mode):
                continue
            # Fail closed where this owned Foo reader cannot express its guards.
            if not hasattr(os, 'O_NONBLOCK') or not hasattr(os, 'O_NOFOLLOW'):
                continue
            fd = os.open(path, os.O_RDONLY | os.O_NONBLOCK | os.O_NOFOLLOW)
            try:
                def identity(info):
                    return (info.st_dev, info.st_ino, info.st_mode, info.st_size,
                            info.st_mtime_ns, info.st_ctime_ns, info.st_nlink)
                opened = os.fstat(fd)
                expected = identity(before)
                if (not stat.S_ISREG(opened.st_mode) or identity(opened) != expected
                        or identity(path.stat(follow_symlinks=False)) != expected):
                    continue
                # Read this verified descriptor, never reopen its pathname.
                with os.fdopen(fd, 'rb', closefd=False) as stream:
                    raw = stream.read(MAX_EVIDENCE + 1)
                if (identity(os.fstat(fd)) == expected
                        and identity(path.stat(follow_symlinks=False)) == expected
                        and not any(p.is_symlink() for p in path.parents)):
                    result[key] = raw
            finally:
                os.close(fd)
        except OSError:
            continue
    return result


def evaluate(profile, metadata, *, now, previous_candidate_sha256=None):
    """Return deterministic metadata candidates and isolated readiness diagnostics.

    Fresh validation never resets original acquisition age. Even a ready binding
    is only metadata-ready; this API grants no source/staging/country acceptance.
    Caller owns OS isolation. --now is explicit UTC; no clock/network is read.
    """
    evidence, bindings = _profile(profile)
    observed = timestamp(now)
    if not isinstance(metadata, dict):
        raise ValueError('metadata-map-invalid')
    if previous_candidate_sha256 is not None and (
            not isinstance(previous_candidate_sha256, str)
            or not HEX.fullmatch(previous_candidate_sha256)):
        raise ValueError('previous-digest-invalid')
    documents, evidence_errors = {}, {}
    for key, asset in evidence.items():
        raw = metadata.get(key)
        if raw is None:
            evidence_errors[key] = 'evidence-missing'
            continue
        if (not isinstance(raw, bytes) or len(raw) != asset['bytes']
                or len(raw) > MAX_EVIDENCE
                or hashlib.sha256(raw).hexdigest() != asset['sha256']):
            evidence_errors[key] = 'evidence-pin-mismatch'
            continue
        try:
            documents[key] = strict_json(raw)
        except (ValueError, UnicodeError, RecursionError):
            evidence_errors[key] = 'evidence-json-malformed'

    records, results = [], []
    for binding in sorted(bindings, key=lambda b: b['id']):
        errors, missing = set(), []
        cache = {'originalAcquiredAt': None, 'originalAgeSeconds': None,
                 'metadataVerifiedAt': None, 'minimumReuseSeconds': MIN_TTL,
                 'state': 'unknown', 'networkAllowed': False,
                 'refreshAction': 'none-selected'}
        try:
            if (binding.get('country') not in PORTFOLIO
                    or not isinstance(binding.get('sourceId'), str) or not binding['sourceId']
                    or not isinstance(binding.get('metadataReleaseId'), str)
                    or not binding['metadataReleaseId']
                    or not isinstance(binding.get('dataTypes'), list) or not binding['dataTypes']
                    or any(not isinstance(x, str) for x in binding['dataTypes'])
                    or not isinstance(binding.get('holds'), list)
                    or any(not isinstance(x, str) or not x for x in binding['holds'])
                    or not isinstance(binding.get('requiredFields'), list)
                    or any(not isinstance(x, str) for x in binding['requiredFields'])
                    or not isinstance(binding.get('fields'), dict) or not binding['fields']):
                raise ValueError('binding-shape-invalid')
            data, origins, used_pins = {}, {}, {}
            for field, declaration in sorted(binding['fields'].items()):
                if not isinstance(field, str) or not field or not isinstance(declaration, dict):
                    raise ValueError('field-declaration-invalid')
                target = '/data/' + field.replace('~', '~0').replace('/', '~1')
                if set(declaration) == {'unknown'}:
                    if not isinstance(declaration['unknown'], str) or not declaration['unknown']:
                        raise ValueError('unknown-reason-required')
                    data[field] = None
                    origins[target] = {'kind': 'constant', 'policySha256': POLICY,
                                       'symbol': 'explicit-unknown:' + field}
                elif set(declaration) == {'evidence', 'selector'}:
                    key = declaration['evidence']
                    if not isinstance(key, str) or key not in evidence:
                        raise ValueError('field-evidence-not-declared')
                    used_pins[key + '.json'] = evidence[key]['sha256']
                    if key in evidence_errors:
                        errors.add(evidence_errors[key])
                        continue
                    try:
                        value = pointer(documents[key], declaration['selector'])
                    except (ValueError, KeyError, IndexError, TypeError):
                        raise ValueError('field-selector-unresolved') from None
                    if isinstance(value, (dict, list)):
                        raise ValueError('field-must-be-scalar')
                    data[field] = value
                    origins[target] = {'kind': 'source', 'sourceId': binding['sourceId'],
                        'releaseId': binding['metadataReleaseId'], 'inputPath': key + '.json',
                        'inputSha256': evidence[key]['sha256'], 'sourceRecordId': binding['id'],
                        'sourceField': declaration['selector']}
                else:
                    raise ValueError('field-declaration-invalid')
            missing = sorted({name for name in binding['requiredFields'] if data.get(name) is None})
            if not used_pins:
                raise ValueError('source-evidence-required')
            record = {'schemaVersion': '1.0', 'id': binding['id'],
                'kind': 'portfolio04-source-input-binding', 'countries': [binding['country']],
                'data': data, 'provenance': {'sourceId': binding['sourceId'],
                    'releaseId': binding['metadataReleaseId'],
                    'fetchedAt': data.get('originalAcquiredAt'), 'fieldOrigins': origins}}
            if not errors:
                errors.update(field_origin_errors(record, used_pins, policy_pins=(POLICY,)))
            if not errors:
                errors.update(metadata_semantic_errors(record,
                              {k + '.json': v for k, v in documents.items()}))
            acquired = data.get('originalAcquiredAt')
            if acquired is None:
                missing.append('originalAcquiredAt')
            else:
                try:
                    age = (observed - timestamp(acquired)).total_seconds()
                    if age < 0:
                        raise ValueError('future-acquisition-time')
                    cache.update(originalAcquiredAt=acquired, originalAgeSeconds=age,
                                 state='under-minimum-reuse' if age < MIN_TTL else 'stale-review-required')
                except ValueError:
                    errors.add('acquisition-time-invalid')
            if not errors:
                cache['metadataVerifiedAt'] = now
                records.append(record)
            status = ('malformed' if any(e != 'evidence-missing' for e in errors)
                      else 'missing' if errors else 'held' if binding['holds']
                      else 'missing' if missing else 'stale' if cache['state'] == 'stale-review-required'
                      else 'metadata-ready')
            if status == 'stale':
                errors.add('refresh-selection-required')
        except (ValueError, TypeError, KeyError) as exc:
            errors.add(str(exc) if isinstance(exc, ValueError) else 'binding-shape-invalid')
            status = 'malformed'
        results.append({'id': binding['id'], 'country': binding.get('country'),
            'dataTypes': binding.get('dataTypes', []), 'status': status,
            'errors': sorted(errors), 'missingFields': sorted(set(missing)),
            'holds': binding.get('holds', []), 'cache': cache,
            'sourceOperationAuthorized': False, 'countryAccepted': False})
    content = candidate_bytes(records)
    digest = hashlib.sha256(content).hexdigest()
    intact = not any(evidence_errors.values()) and all(r['status'] != 'malformed' for r in results)
    return {'schemaVersion': 'portfolio04-binding-result/1', 'policySha256': POLICY,
            'profileSha256': fingerprint(profile), 'candidateSha256': digest,
            'candidateBytes': len(content), 'candidateRecords': records,
            'results': results, 'checkedAt': now,
            'replay': 'no-op' if intact and previous_candidate_sha256 == digest else 'metadata-output',
            'replayScope': 'candidate-bytes-only; diagnostics and holds must still be consumed',
            'diagnosticInterface': 'per-binding fixed status/errors/missingFields/holds/cache',
            'productionAdmission': False, 'goldAdmission': False, 'networkRequests': 0}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--now', required=True, help='Explicit UTC evaluation time')
    parser.add_argument('--previous-candidate-sha256')
    args = parser.parse_args(argv)
    try:
        profile = load_catalogue()
        result = evaluate(profile, read_metadata(profile), now=args.now,
                          previous_candidate_sha256=args.previous_candidate_sha256)
        sys.stdout.buffer.write(canonical(result) + b'\n')
        return 0 if all(r['status'] == 'metadata-ready' for r in result['results']) else 2
    except (ValueError, OSError):
        sys.stdout.buffer.write(canonical({'schemaVersion': 'portfolio04-binding-result/1',
            'error': 'profile-or-invocation-invalid', 'productionAdmission': False}) + b'\n')
        return 3


if __name__ == '__main__':
    raise SystemExit(main())
