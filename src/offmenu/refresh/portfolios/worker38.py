"""PT/SX/TR/VC metadata bindings; no acquisition or source-body execution.

Only the shipped, reviewable receipt allowlist can be read by the CLI. Runtime
rights, SourceContract admission and country acceptance are never constructed.
"""
import argparse
import copy
import hashlib
import json
import os
from pathlib import Path
import stat

from ..acceptance import fingerprint
from ..core import safe_path, strict_json, timestamp
from ..field_provenance import field_origin_errors
from ..national_tabular import valid_input_name

MAX_METADATA = 128 * 1024
from .worker38_sources import REGISTRY
UNKNOWN_FIELDS = ('rawManifest', 'rawSelector', 'nativeUnit', 'nativeBasis',
                  'scopeAcceptance', 'sourceUseDecision')


def _read_metadata(path):
    """Bounded bytes from one nonblocking, no-follow regular-file descriptor.

    Verify the descriptor actually read and the final path identity. Neither
    post-read custody checks nor the caller reopen a path for content.
    """
    path = safe_path(path)
    signature = lambda s: (s.st_dev, s.st_ino, s.st_mode, s.st_size,
                           s.st_mtime_ns, s.st_ctime_ns)
    before = path.stat(follow_symlinks=False)
    if not stat.S_ISREG(before.st_mode) or before.st_size > MAX_METADATA:
        raise ValueError('metadata-bound-or-type-invalid')
    descriptor = os.open(path, os.O_RDONLY | os.O_NONBLOCK | os.O_NOFOLLOW | os.O_CLOEXEC)
    try:
        opened = os.fstat(descriptor)
        if not stat.S_ISREG(opened.st_mode) or signature(opened) != signature(before):
            raise ValueError('metadata-changed-before-read')
        chunks, size = [], 0
        while size <= MAX_METADATA:
            chunk = os.read(descriptor, min(65536, MAX_METADATA + 1 - size))
            if not chunk:
                break
            size += len(chunk)
            if size > MAX_METADATA:
                raise ValueError('metadata-byte-bound-exceeded')
            chunks.append(chunk)
        after = os.fstat(descriptor)
        current = path.stat(follow_symlinks=False)
        if (size != opened.st_size or signature(after) != signature(opened)
                or signature(current) != signature(opened)):
            raise ValueError('metadata-changed-during-read')
        return b''.join(chunks)
    finally:
        os.close(descriptor)


def pointer(value, selector):
    if not isinstance(selector, str) or not selector.startswith('/'):
        raise ValueError('selector-invalid')
    for part in selector[1:].split('/'):
        key = part.replace('~1', '/').replace('~0', '~')
        if isinstance(value, list):
            if not key.isdigit() or str(int(key)) != key:
                raise ValueError('selector-invalid')
            value = value[int(key)]
        elif isinstance(value, dict):
            value = value[key]
        else:
            raise ValueError('selector-invalid')
    if isinstance(value, (dict, list)):
        raise ValueError('scalar-selector-required')
    return value


def diagnose(entry, payload, *, now, previous_key=None, cache_planner=None):
    """Pure binding over already supplied metadata bytes; no paths are followed.

    Unknowns refer to future raw-data staging, not the validity of the receipt.
    A metadata-ready result is still only a proposal, never source acceptance.
    """
    errors = set()
    row = None
    metadata_candidate = None
    policy = None
    key = None
    actual = None
    try:
        timestamp(now)
        sid, release = entry['sourceId'], entry['releaseId']
        if (not isinstance(sid, str) or not valid_input_name(sid)
                or '/' in sid or not isinstance(release, str) or not release
                or entry['country'] not in ('PT', 'SX', 'TR', 'VC')
                or not isinstance(entry['fields'], dict) or not entry['fields']
                or not isinstance(entry['holds'], list)
                or any(not isinstance(x, str) or not x for x in entry['holds'])
                or not isinstance(payload, bytes) or len(payload) > MAX_METADATA):
            raise ValueError('binding-invalid')
        expected = entry['metadata']['sha256']
        actual = hashlib.sha256(payload).hexdigest()
        if actual != expected:
            errors.add('metadata-pin-mismatch')
        metadata = strict_json(payload)
        fingerprint(metadata)  # Reject overflowed numbers as well as NaN tokens.
        if not isinstance(metadata, dict):
            raise ValueError('metadata-object-required')
        fields, origins = {}, {}
        relative = 'metadata/' + sid + '.json'
        for name, selector in entry['fields'].items():
            if not isinstance(name, str) or not name:
                raise ValueError('field-invalid')
            try:
                fields[name] = pointer(metadata, selector)
            except (KeyError, IndexError, TypeError, ValueError):
                errors.add('metadata-selector-missing')
                continue
            target = '/data/' + name.replace('~', '~0').replace('/', '~1')
            origins[target] = {
                'kind': 'source', 'sourceId': sid, 'releaseId': release,
                'inputPath': relative, 'inputSha256': expected,
                'sourceRecordId': 'receipt:' + expected, 'sourceField': selector}
        if fields.get('country') != entry['country']:
            errors.add('country-binding-mismatch')
        row = {'id': sid + ':metadata', 'kind': 'sourceMetadata',
               'schemaVersion': '1.0', 'data': fields,
               'provenance': {'sourceId': sid, 'releaseId': release,
                              'fieldOrigins': origins}}
        errors.update(field_origin_errors(row, {relative: expected}))
        if not errors:
            metadata_candidate = copy.deepcopy(row)
        selector = entry['originalAcquiredAtSelector']
        if selector is None:
            errors.add('original-acquisition-time-unknown')
        else:
            try:
                acquired = pointer(metadata, selector)
                if timestamp(acquired) > timestamp(now):
                    raise ValueError('future-acquisition')
                row['provenance']['fetchedAt'] = acquired
                # Trusted code injection only, never a source/CLI plugin.
                # Current shared planners are source-specific; do not clone a
                # country cache engine or reuse the Wikibooks admission here.
                if cache_planner is None:
                    errors.add('shared-cache-planner-unavailable')
                    policy = {'originalAcquiredAt': acquired,
                              'metadataValidatedAt': now,
                              'timestampKind': entry.get('acquisitionTimestampKind'),
                              'decision': 'shared-planner-unavailable',
                              'validationResetsAcquisitionAge': False,
                              'rawCacheReuseQualified': False}
                    shared = None
                else:
                    try:
                        shared = cache_planner(acquired, expected, now=timestamp(now))
                    except Exception:
                        errors.add('cache-planner-failed')
                        shared = None
                if shared is not None:
                    if (not isinstance(shared, dict)
                            or type(shared.get('minimumReuseDays')) is not int
                            or shared['minimumReuseDays'] < 30
                            or shared.get('decision') not in (
                                'reuse-verified-cache', 'conditional-revalidation-required')
                            or type(shared.get('networkRequests')) is not int
                            or shared['networkRequests'] != 0):
                        errors.add('cache-planner-contract-invalid')
                        shared = None
                if shared is not None:
                    policy = {k: shared[k] for k in (
                        'minimumReuseDays', 'acquisitionAgeDays', 'decision',
                        'mtimeUsedForFreshness', 'assetBytesVerifiedByThisPlan')}
                    policy.update(originalAcquiredAt=acquired,
                              metadataValidatedAt=now,
                              validationResetsAcquisitionAge=False,
                              scope='metadata-only-plan',
                              timestampKind=entry.get('acquisitionTimestampKind', 'authored-fixture'),
                              rawCacheReuseQualified=False)
                    if shared['decision'] != 'reuse-verified-cache':
                        errors.add('stale-input-review-required')
            except (KeyError, IndexError, TypeError, ValueError):
                errors.add('acquisition-time-invalid')
        if entry['holds']:
            errors.add('source-processing-held')
        # These fields never become inferred permissions or unit defaults.
        unknowns = [name for name in UNKNOWN_FIELDS if entry.get(name) is None]
        key = fingerprint({'sourceId': sid, 'releaseId': release,
                           'country': entry['country'], 'fields': entry['fields'],
                           'metadataSha256': actual, 'role': entry['role'],
                           'types': entry['types'],
                           'scope': {n: entry.get(n) for n in UNKNOWN_FIELDS},
                           'holds': entry['holds'],
                           'originalAcquiredAt': policy and policy['originalAcquiredAt']})
    except (KeyError, TypeError, ValueError, OverflowError):
        errors.add('malformed-input')
        unknowns = list(UNKNOWN_FIELDS)
    if errors:
        row = None  # Never emit a partial proposal as successful staging.
    return {'sourceId': entry.get('sourceId') if isinstance(entry, dict) else None,
            'status': 'withheld' if errors else 'metadata-proposal-ready',
            'errors': sorted(errors), 'unknowns': unknowns,
            'buildKey': key, 'metadataSha256': actual,
            'action': ('withheld' if errors else
                       'no-op' if previous_key == key else 'stage-metadata-proposal'),
            'cache': policy, 'candidate': row,
            'metadataCandidate': metadata_candidate,
            'rawBodyProcessed': False, 'sourceAccepted': False,
            'countryComplete': False, 'networkRequests': 0}


def run(registry, *, now, previous_keys=None, cache_planner=None):
    """Read only exact configured receipt bytes; no nested/body paths followed."""
    results = []
    for entry in registry['entries']:
        try:
            payload = _read_metadata(entry['metadata']['path'])
            result = diagnose(entry, payload, now=now,
                              previous_key=(previous_keys or {}).get(entry['sourceId']),
                              cache_planner=cache_planner)
        except (OSError, ValueError):
            result = {'sourceId': entry['sourceId'], 'status': 'withheld',
                      'errors': ['metadata-unavailable'], 'candidate': None,
                      'sourceAccepted': False, 'countryComplete': False,
                      'rawBodyProcessed': False, 'networkRequests': 0}
        results.append(result)
    cells = [{'country': country, 'type': kind, 'countryComplete': False,
              'sources': [e['sourceId'] for e in registry['entries']
                          if e['country'] == country and kind in e['types']],
              'accepted': False}
             for country in registry['countries'] for kind in registry['types']]
    return {'schemaVersion': 'worker38-binding-diagnostics/1',
            'scope': 'metadata-proposal-only', 'results': results, 'cells': cells,
            'sourceAccepted': False, 'countryComplete': False, 'networkRequests': 0}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--now', required=True, help='Explicit UTC timestamp')
    args = parser.parse_args()
    registry = REGISTRY
    print(json.dumps(run(registry, now=args.now), sort_keys=True,
                     ensure_ascii=False, allow_nan=False))


if __name__ == '__main__':
    main()
