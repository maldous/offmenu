"""BM/LC/SC metadata preflight. No source parser, acquisition or admission.

Configuration is reviewed code custody. CLI exposes only this portfolio and reads
only its pinned JSON metadata, never a path extracted from a receipt. The shared
field-origin validator checks declared metadata coordinates; no food semantics or
rights are inferred. Diagnostics contain fixed codes, never source values.
"""
import argparse
import os
from pathlib import Path
import re
import stat

from offmenu.refresh.core import canonical, sha, strict_json, timestamp, safe_path
from offmenu.refresh.field_provenance import field_origin_errors

CONFIG = Path(__file__).resolve().parents[2] / 'config/portfolios/bm-lc-sc.json'
MAX_METADATA = 1024 * 1024
POLICY = {'scope': 'metadata-only', 'unknown': None, 'cachePlanner': 'unsupported'}
POLICY_PIN = sha(canonical(POLICY))


def pointer(document, selector):
    """Exact RFC6901 coordinate, not a fallback lookup or inferred field."""
    if not isinstance(selector, str) or not selector.startswith('/'):
        raise ValueError('selector-invalid')
    value = document
    for token in selector[1:].split('/'):
        if re.search(r'~(?![01])', token):
            raise ValueError('selector-invalid')
        token = token.replace('~1', '/').replace('~0', '~')
        if isinstance(value, list):
            if not re.fullmatch(r'0|[1-9][0-9]*', token):
                raise ValueError('selector-invalid')
            value = value[int(token)]
        elif isinstance(value, dict):
            value = value[token]
        else:
            raise ValueError('selector-invalid')
    return value


def assess(binding, raw_metadata, *, now, previous_key=None):
    """Pure bounded preflight; raw_metadata is already selected metadata bytes.

    Returns a proposed metadata staging envelope only when valid. It never builds
    a SourceContract or changes rights, cache files, accepted pointers or clocks.
    The content key excludes validation time; acquisition age never does.
    """
    result = {'bindingId': None, 'status': 'malformed', 'errors': [],
              'metadataCandidate': None, 'contentKey': None, 'replay': 'not-ready',
              'cache': None, 'networkRequests': 0, 'bodyProcessing': False,
              'acceptedRecords': 0, 'countryComplete': False}
    errors = set()
    try:
        if (not isinstance(binding, dict) or binding.get('country') not in ('BM', 'LC', 'SC')
                or not isinstance(binding.get('id'), str) or not binding['id']
                or not isinstance(binding.get('sourceId'), str) or not binding['sourceId']
                or not isinstance(binding.get('releaseId'), str) or not binding['releaseId']
                or not isinstance(binding.get('holds'), list)
                or not all(isinstance(x, str) and x for x in binding['holds'])
                or not isinstance(binding.get('selectors'), dict)
                or not binding['selectors']
                or binding.get('scope') != 'retained-metadata-only'):
            raise ValueError('binding-invalid')
        result['bindingId'] = binding['id']
        asset = binding['metadata']
        if (type(asset['bytes']) is not int or not 0 < asset['bytes'] <= MAX_METADATA
                or not isinstance(asset['sha256'], str)
                or not re.fullmatch('[0-9a-f]{64}', asset['sha256'])):
            raise ValueError('metadata-pin-invalid')
        if binding['holds']:
            errors.add('source-use-held')
        if raw_metadata is None:
            errors.add('metadata-missing')
        elif (not isinstance(raw_metadata, bytes) or len(raw_metadata) != asset['bytes']
                or sha(raw_metadata) != asset['sha256']):
            errors.add('metadata-pin-mismatch')
        if errors - {'source-use-held'}:
            result['status'] = 'missing' if 'metadata-missing' in errors else 'malformed'
            result['errors'] = sorted(errors)
            return result
        document = strict_json(raw_metadata)
        if pointer(document, '/country') != binding['country']:
            raise ValueError('country-binding-mismatch')
        values, origins = {}, {}
        for name, selector in sorted(binding['selectors'].items()):
            if not re.fullmatch('[a-zA-Z][a-zA-Z0-9]*', name):
                raise ValueError('field-name-invalid')
            try:
                value = pointer(document, selector)
                if isinstance(value, (dict, list)):
                    raise ValueError('scalar-selector-required')
                values[name] = value
                origins['/data/' + name] = {
                    'kind': 'source', 'sourceId': binding['sourceId'],
                    'releaseId': binding['releaseId'], 'inputPath': 'metadata.json',
                    'inputSha256': asset['sha256'], 'sourceRecordId': binding['id'],
                    'sourceField': selector}
            except (KeyError, IndexError):
                errors.add('declared-field-missing')
        candidate = {'id': binding['id'], 'kind': 'SourceInputMetadata',
                     'schemaVersion': 'offmenu-portfolio-metadata/1', 'data': values,
                     'provenance': {'sourceId': binding['sourceId'],
                                    'releaseId': binding['releaseId'],
                                    'fieldOrigins': origins}}
        errors.update(field_origin_errors(candidate, {'metadata.json': asset['sha256']}))
        now_time = timestamp(now)
        acquisition_selector = binding.get('originalAcquiredAtSelector')
        acquired = None
        if acquisition_selector is not None:
            try:
                acquired = timestamp(pointer(document, acquisition_selector))
            except (KeyError, IndexError):
                errors.add('original-acquisition-time-missing')
        else:
            errors.add('original-acquisition-time-missing')
        cache = {'originalAcquiredAt': acquired.isoformat() if acquired else None,
                 'validationObservedAt': now_time.isoformat(),
                 'plannerCapability': 'unsupported', 'acquisitionAgeSeconds': None,
                 'decision': 'unknown-no-download', 'downloadAllowed': False,
                 'validationResetsAcquisitionAge': False}
        if acquired:
            age = (now_time - acquired).total_seconds()
            if age < 0:
                errors.add('acquisition-time-in-future')
            else:
                cache['acquisitionAgeSeconds'] = int(age)
        result['cache'] = cache
        # Pin the full reviewed declaration, including scope, holds and unknowns.
        result['contentKey'] = sha(canonical({'binding': binding, 'policy': POLICY_PIN}))
        result['status'] = ('malformed' if any(x in errors for x in
            ('acquisition-time-in-future',)) else 'missing' if any(x in errors for x in
            ('declared-field-missing', 'original-acquisition-time-missing')) else
            'held' if 'source-use-held' in errors else
            'malformed' if errors else 'ready-metadata-only')
        if not errors:
            result['metadataCandidate'] = candidate
            result['replay'] = ('unchanged-no-op' if previous_key == result['contentKey']
                                else 'metadata-binding-ready')
    except Exception:
        # No source text, path, exception detail or credential leaks in reports.
        errors.add('binding-or-metadata-malformed')
        result['status'] = 'malformed'
    result['errors'] = sorted(errors)
    return result


def read_metadata(asset):
    """Nonblocking regular metadata only, with no-follow directory descent.

    Descriptor custody closes the path-check/open race; pin validation remains in
    assess. File/size/change failures are isolated by run, before peer progress.
    """
    path = safe_path(asset['path'])
    directory = os.open('/', os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC)
    descriptor = None
    try:
        flags = os.O_RDONLY | os.O_NONBLOCK | os.O_NOFOLLOW | os.O_CLOEXEC
        for component in path.parts[1:-1]:
            next_directory = os.open(component, flags | os.O_DIRECTORY, dir_fd=directory)
            os.close(directory)
            directory = next_directory
        descriptor = os.open(path.name, flags, dir_fd=directory)
        before = os.fstat(descriptor)
        if not stat.S_ISREG(before.st_mode) or not 0 < before.st_size <= MAX_METADATA:
            raise ValueError('regular-bounded-metadata-required')
        data = bytearray()
        while len(data) <= MAX_METADATA:
            block = os.read(descriptor, min(65536, MAX_METADATA + 1 - len(data)))
            if not block:
                break
            data.extend(block)
        after = os.fstat(descriptor)
        identity = lambda s: (s.st_dev, s.st_ino, s.st_size, s.st_mtime_ns, s.st_ctime_ns)
        if identity(before) != identity(after) or len(data) != before.st_size:
            raise ValueError('metadata-changed-during-read')
        return bytes(data)
    finally:
        if descriptor is not None:
            os.close(descriptor)
        os.close(directory)


def run(bindings, *, now, previous=None, reader=read_metadata):
    results = []
    for binding in bindings:
        try:
            raw = reader(binding['metadata'])
        except FileNotFoundError:
            raw = None
        except Exception:
            results.append({'bindingId': binding.get('id'), 'status': 'malformed',
                            'errors': ['metadata-read-failed'], 'metadataCandidate': None,
                            'networkRequests': 0, 'bodyProcessing': False,
                            'acceptedRecords': 0, 'countryComplete': False})
            continue
        results.append(assess(binding, raw, now=now,
                             previous_key=(previous or {}).get(binding.get('id'))))
    return {'schemaVersion': 'offmenu-bm-lc-sc-preflight/1', 'bindings': results,
            'countryComplete': False, 'acceptedRecords': 0, 'networkRequests': 0}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--now', required=True, help='Explicit UTC validation clock')
    args = parser.parse_args(argv)
    config = strict_json(CONFIG.read_bytes())
    report = run(config['bindings'], now=args.now)
    print(canonical(report).decode(), end='')
    return 0 if all(x['status'] == 'ready-metadata-only' for x in report['bindings']) else 2


if __name__ == '__main__':
    raise SystemExit(main())
