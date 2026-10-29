"""MU/SV/TN/VA metadata bindings; never a source parser or admission registry.

Only reviewed, explicitly pinned JSON metadata is opened. Locators contained in
metadata are values, not file capabilities. No original payload is followed.
"""
import argparse
from contextlib import ExitStack, contextmanager
import fcntl
import json
import os
from pathlib import Path, PurePosixPath
import re
import stat

from ._portfolio36_catalogue import load_catalogue
from .acceptance import assess_cells, canonical, fingerprint
from .core import (RefreshError, atomic_json, safe_path, sha, strict_json,
                   timestamp)
from .field_provenance import field_origin_errors

CONFIG = Path(__file__).resolve().parents[3] / 'config/source-bindings/owner36.json'
COUNTRIES = frozenset(('MU', 'SV', 'TN', 'VA'))
DOMAINS = frozenset(('ingredients', 'recipes', 'nutrition', 'retailers/providers',
                     'prices/baskets', 'dietary references'))
HEX = re.compile('[0-9a-f]{64}')
MAX_METADATA = 1024 * 1024
MAX_MANIFEST = 8 * 1024 * 1024


@contextmanager
def _binding_lock(path):
    """Caller-owned safe boundary; never truncate/write an existing lock inode.

    Keep a stable inode compatible with flock. Reject links/nonregular objects
    using the opened descriptor before use; shared core remains unchanged.
    """
    try:
        fd = os.open(safe_path(path), os.O_RDWR | os.O_CREAT | os.O_NONBLOCK | os.O_NOFOLLOW, 0o600)
    except OSError:
        raise RefreshError('binding-lock-invalid') from None
    try:
        before = os.fstat(fd)
        _require(stat.S_ISREG(before.st_mode) and before.st_nlink == 1, 'binding-lock-invalid')
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise RefreshError('binding-lock-held') from None
        after = os.fstat(fd)
        current = os.stat(path, follow_symlinks=False)
        _require(stat.S_ISREG(after.st_mode) and after.st_nlink == 1
                 and (after.st_dev, after.st_ino) == (current.st_dev, current.st_ino),
                 'binding-lock-invalid')
        yield
    finally:
        os.close(fd)


def _existing_manifest(path):
    """Bounded read of the actual opened regular object, never a pathname reopen."""
    try:
        fd = os.open(safe_path(path), os.O_RDONLY | os.O_NONBLOCK | os.O_NOFOLLOW)
    except FileNotFoundError:
        return None
    except OSError:
        raise RefreshError('replay-manifest-invalid') from None
    with os.fdopen(fd, 'rb') as stream:
        before = os.fstat(stream.fileno())
        _require(stat.S_ISREG(before.st_mode), 'replay-manifest-not-regular')
        _require(before.st_size <= MAX_MANIFEST, 'replay-manifest-byte-limit')
        raw = stream.read(MAX_MANIFEST + 1)
        _require(len(raw) <= MAX_MANIFEST, 'replay-manifest-byte-limit')
        after = os.fstat(stream.fileno())
        current = os.stat(path, follow_symlinks=False)
        identity = lambda s: (s.st_dev, s.st_ino, s.st_size, s.st_mtime_ns, s.st_ctime_ns)
        _require(identity(before) == identity(after) == identity(current),
                 'replay-manifest-changed')
    try:
        document = strict_json(raw)
        canonical(document)
    except (ValueError, TypeError, UnicodeError, RecursionError):
        raise RefreshError('replay-manifest-invalid') from None
    _require(isinstance(document, dict)
             and document.get('schemaVersion') == 'offmenu-portfolio36-staging-bindings/1'
             and document.get('scope') == 'metadata-only-not-dataset-staging-acceptance'
             and isinstance(document.get('records'), list), 'replay-manifest-invalid')
    return raw


def _require(condition, code):
    if not condition:
        raise RefreshError(code)


def pointer(document, selector):
    """RFC6901 selector, never an executable expression or inferred cell."""
    _require(isinstance(selector, str) and selector.startswith('/'), 'selector-invalid')
    value = document
    for raw in selector[1:].split('/'):
        _require(not re.search('~(?![01])', raw), 'selector-invalid')
        key = raw.replace('~1', '/').replace('~0', '~')
        if isinstance(value, list):
            _require(bool(re.fullmatch('0|[1-9][0-9]*', key)), 'selector-invalid')
            try:
                value = value[int(key)]
            except IndexError:
                raise RefreshError('selector-missing') from None
        elif isinstance(value, dict) and key in value:
            value = value[key]
        else:
            raise RefreshError('selector-missing')
    return value


def _config(config):
    _require(isinstance(config, dict) and config.get('schemaVersion') == 'offmenu-portfolio36/1'
             and config.get('scope') == 'metadata-only', 'binding-config-invalid')
    sources = config.get('sources')
    _require(isinstance(sources, list) and 0 < len(sources) <= 32, 'binding-config-invalid')
    identities = set()
    for source in sources:
        _require(isinstance(source, dict), 'binding-config-invalid')
        identity = source.get('sourceId')
        _require(isinstance(identity, str) and bool(identity) and identity not in identities,
                 'binding-identity-invalid')
        identities.add(identity)
        _require(source.get('country') in COUNTRIES and source.get('domain') in DOMAINS
                 and isinstance(source.get('releaseId'), str) and source['releaseId'],
                 'binding-applicability-invalid')
        timestamp(source.get('originalAcquiredAt'))
        inputs = source.get('inputs')
        _require(isinstance(inputs, list) and 0 < len(inputs) <= 8, 'metadata-inputs-invalid')
        paths = set()
        for asset in inputs:
            _require(isinstance(asset, dict), 'metadata-input-invalid')
            name = asset.get('path')
            _require(isinstance(name, str) and bool(re.fullmatch('[a-zA-Z0-9._-]+[.]json', name))
                     and name == PurePosixPath(name).as_posix() and name not in paths,
                     'metadata-path-invalid')
            paths.add(name)
            _require(type(asset.get('bytes')) is int and 0 < asset['bytes'] <= MAX_METADATA
                     and isinstance(asset.get('sha256'), str) and HEX.fullmatch(asset['sha256']),
                     'metadata-pin-invalid')
        fields = source.get('fields')
        _require(isinstance(fields, dict) and 0 < len(fields) <= 64, 'metadata-fields-invalid')
        for key, field in fields.items():
            _require(bool(re.fullmatch('[a-zA-Z][a-zA-Z0-9]*', key))
                     and isinstance(field, dict) and field.get('input') in paths
                     and isinstance(field.get('selector'), str)
                     and field['selector'].startswith('/'), 'metadata-field-binding-invalid')
        _require(isinstance(source.get('holds'), list)
                 and all(isinstance(x, str) and x for x in source['holds'])
                 and isinstance(source.get('payloadBlockers'), list)
                 and bool(source['payloadBlockers'])
                 and all(isinstance(x, str) and x for x in source['payloadBlockers']),
                 'binding-holds-required')
    return sources


def _metadata_identity(value):
    return (value.st_dev, value.st_ino, value.st_size,
            value.st_mtime_ns, value.st_ctime_ns)


@contextmanager
def _metadata_bytes(path, expected):
    """Pin one bounded regular descriptor through the caller's consumption.

    A pathname check alone cannot make a subsequent blocking open safe. Open
    nonblocking/nofollow, compare the opened inode with the pre-open snapshot,
    and never reopen the pathname for digesting or parsing.
    """
    try:
        before = os.stat(path, follow_symlinks=False)
        fd = os.open(path, os.O_RDONLY | os.O_NONBLOCK | os.O_NOFOLLOW)
    except FileNotFoundError:
        raise RefreshError('metadata-input-missing') from None
    except OSError:
        raise RefreshError('metadata-input-invalid') from None
    with os.fdopen(fd, 'rb') as stream:
        opened = os.fstat(stream.fileno())
        _require(stat.S_ISREG(opened.st_mode), 'regular-file-required')
        _require(_metadata_identity(before) == _metadata_identity(opened),
                 'metadata-input-changed')
        _require(opened.st_size == expected['bytes'] <= MAX_METADATA,
                 'asset-checksum-mismatch')
        raw = stream.read(expected['bytes'] + 1)
        _require(len(raw) == expected['bytes'] and sha(raw) == expected['sha256'],
                 'asset-checksum-mismatch')

        def unchanged():
            try:
                after = os.fstat(stream.fileno())
                current = os.stat(path, follow_symlinks=False)
            except OSError:
                raise RefreshError('metadata-input-changed') from None
            _require(stat.S_ISREG(current.st_mode)
                     and _metadata_identity(opened) == _metadata_identity(after)
                     == _metadata_identity(current), 'metadata-input-changed')

        unchanged()
        yield raw
        unchanged()


def evaluate(config, metadata_root, *, now):
    """Isolate failures; report receipt age, never emulate a refresh planner.

    Accepted develop has no source-neutral pure cache planner. Staleness here is
    only an age observation; no cache eligibility, retention or rights is granted.
    """
    timestamp(now)
    clock = timestamp(now)
    sources = _config(config)
    root = safe_path(metadata_root)
    reports, records = [], []
    policy_pin = fingerprint(config)
    for source in sorted(sources, key=lambda s: s['sourceId']):
        row = {'sourceId': source['sourceId'], 'country': source['country'],
               'domain': source['domain'], 'releaseId': source['releaseId'],
               'status': 'malformed', 'errors': [], 'cache': None,
               'payloadBlockers': source['payloadBlockers'], 'payloadProcessing': False}
        try:
            if source['holds']:
                row.update(status='held', errors=['metadata-scope-held'])
                reports.append(row)
                continue  # A hold closes even metadata file access.
            with ExitStack() as inputs:
                documents = {}
                for asset in source['inputs']:
                    path = safe_path(root / asset['path'])
                    raw = inputs.enter_context(_metadata_bytes(path, asset))
                    documents[asset['path']] = strict_json(raw)
                data, origins = {}, {}
                for key, field in sorted(source['fields'].items()):
                    value = pointer(documents[field['input']], field['selector'])
                    _require(value is None or isinstance(value, (str, int, float, bool)),
                             'metadata-field-must-be-scalar')
                    # Expected literals are trusted configuration constraints, not
                    # new values synthesized when the input is absent or different.
                    if 'expected' in field:
                        _require(type(value) is type(field['expected']) and value == field['expected'],
                                 'metadata-field-literal-mismatch')
                    data[key] = value
                    origins['/data/' + key] = {
                        'kind': 'source', 'sourceId': source['sourceId'],
                        'releaseId': source['releaseId'], 'inputPath': field['input'],
                        'inputSha256': next(a['sha256'] for a in source['inputs']
                                           if a['path'] == field['input']),
                        'sourceRecordId': source['sourceId'], 'sourceField': field['selector']}
                record = {'id': 'owner36:metadata:' + source['sourceId'],
                          'kind': 'sourceInputBinding', 'schemaVersion': 'offmenu-owner36-binding/1',
                          'data': data, 'provenance': {'sourceId': source['sourceId'],
                              'releaseId': source['releaseId'],
                              'fetchedAt': source['originalAcquiredAt'], 'fieldOrigins': origins}}
                errors = field_origin_errors(record, {a['path']: a['sha256'] for a in source['inputs']})
                _require(not errors, 'metadata-field-origin-invalid')
                canonical(record)  # Reject overflowed JSON numbers, including 1e999.
                age = (clock - timestamp(source['originalAcquiredAt'])).total_seconds()
                _require(age >= 0, 'acquisition-timestamp-in-future')
                row['cache'] = {'minimumReuseDays': 30, 'acquisitionAgeDays': int(age // 86400),
                                'originalAcquiredAt': source['originalAcquiredAt'],
                                'evaluatedAt': now, 'mtimeUsedForFreshness': False,
                                'validationResetsAcquisitionAge': False, 'networkRequests': 0,
                                'sharedPlannerCapability': 'unsupported-source-family',
                                'cacheEligibility': 'not-evaluated-no-download'}
                stale = age >= 30 * 86400
                row.update(status='stale-input' if stale else 'metadata-ready',
                           errors=['conditional-revalidation-not-selected'] if stale else [])
            records.append(record)
        except (OSError, ValueError, TypeError, KeyError, OverflowError) as error:
            code = str(error) if isinstance(error, RefreshError) else 'metadata-invalid'
            # Never echo source content, absolute paths or arbitrary exceptions.
            if not re.fullmatch('[a-z][a-z0-9-]{0,95}', code):
                code = 'metadata-invalid'
            row.update(status='missing' if code in ('metadata-input-missing', 'selector-missing')
                       else 'malformed', errors=[code])
        reports.append(row)
    manifest = {'schemaVersion': 'offmenu-portfolio36-staging-bindings/1',
                'scope': 'metadata-only-not-dataset-staging-acceptance',
                'policySha256': policy_pin, 'inputs': [s['inputs'] for s in sources],
                'bindings': [{k: s.get(k) for k in ('sourceId', 'releaseId', 'country',
                             'domain', 'originalAcquiredAt', 'validationAt',
                             'unknowns', 'payloadBlockers', 'evidenceReferences')}
                             for s in sources],
                'records': records, 'metadataRecords': len(records),
                'sourceRecordsProcessed': 0, 'normalizedRecords': 0,
                'acceptedRecords': 0, 'goldAdmittedRecords': 0,
                'countryCoverageComplete': False, 'networkRequests': 0}
    return manifest, {'schemaVersion': 'offmenu-portfolio36-diagnostics/1',
                      'sources': reports, 'networkRequests': 0,
                      'payloadProcessing': False, 'countryCoverageComplete': False,
                      'countryCells': assess_cells((), (), countries=sorted(COUNTRIES),
                                                   domains=sorted(DOMAINS))}


def replay(config, metadata_root, workspace, *, now):
    """Deterministic publication, shared path/atomic helpers and guarded local lock.

    The file named binding-manifest.json is evidence staging, not a common or
    native SourceContract candidate. This never calls acceptance.accept().
    """
    source, target = safe_path(metadata_root), safe_path(workspace)
    _require(not (source == target or source in target.parents or target in source.parents),
             'metadata-workspace-overlap')
    manifest, report = evaluate(config, source, now=now)
    # Report failures without overwriting a previously complete manifest.
    target.mkdir(parents=True, exist_ok=True)
    with _binding_lock(target / 'owner36.lock'):
        atomic_json(target / 'diagnostics.json', report)
        failures = any(s['status'] not in ('metadata-ready', 'stale-input') for s in report['sources'])
        if failures:
            return {'status': 'isolated-failures', 'manifestPublished': False, 'diagnostics': report}
        output = target / 'binding-manifest.json'
        previous = _existing_manifest(output)
        desired = canonical(manifest) + b'\n'
        _require(len(desired) <= MAX_MANIFEST, 'binding-manifest-byte-limit')
        if previous == desired:
            action = 'verified-no-op'
        else:
            atomic_json(output, manifest)
            action = 'metadata-bindings-written'
        return {'status': action, 'manifestPublished': True,
                'manifestSha256': fingerprint(manifest), 'diagnostics': report}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--metadata-root', required=True)
    parser.add_argument('--workspace', required=True)
    parser.add_argument('--now', required=True, help='Explicit UTC policy clock; never file mtime.')
    args = parser.parse_args(argv)
    try:
        config = load_catalogue()
        result = replay(config, args.metadata_root, args.workspace, now=args.now)
        print(json.dumps(result, sort_keys=True, ensure_ascii=False, allow_nan=False))
        return 2 if result['status'] == 'isolated-failures' else 0
    except (OSError, ValueError, TypeError, KeyError) as error:
        code = str(error) if isinstance(error, RefreshError) else 'binding-command-invalid'
        if not re.fullmatch('[a-z][a-z0-9-]{0,95}', code):
            code = 'binding-command-invalid'
        print(json.dumps({'status': 'invalid', 'errors': [code], 'networkRequests': 0}))
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
