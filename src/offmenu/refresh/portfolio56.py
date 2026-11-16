"""ES/NI/TK/WF metadata binding preflight. No body parser or admission route.

All filesystem inputs are explicitly pinned JSON metadata. This module never
constructs SourceContract from a manifest, imports historical engines, fetches,
refreshes, or runs an adapter. A ready result is a metadata candidate only.
"""
import argparse
from contextlib import ExitStack
import os
from copy import deepcopy
from datetime import timedelta
import json
from pathlib import Path
import re
import stat

from .adapter_mapping import retained_adapters
from .core import RefreshError, canonical, safe_path, sha, strict_json, timestamp
from .field_provenance import field_origin_errors
from .serialization import encode_records

COUNTRIES = frozenset(('ES', 'NI', 'TK', 'WF'))
DOMAINS = frozenset(('ingredients', 'recipes', 'nutrition', 'retailers/providers',
                     'prices/baskets', 'dietary references'))
VERSION = 'offmenu-portfolio56-metadata-binding/1'
LIMIT = 2 * 1024 * 1024
MAX_BINDINGS = 64
REPLAY_LIMIT = 256 * 1024 * 1024
HEX = re.compile(r'[a-f0-9]{64}')


def _pointer(document, pointer):
    if not isinstance(pointer, str) or not pointer.startswith('/'):
        raise RefreshError('invalid-metadata-selector')
    value = document
    for part in pointer[1:].split('/'):
        if re.search(r'~(?![01])', part):
            raise RefreshError('invalid-metadata-selector')
        part = part.replace('~1', '/').replace('~0', '~')
        if isinstance(value, list):
            if not re.fullmatch(r'0|[1-9][0-9]*', part):
                raise KeyError(part)
            value = value[int(part)]
        elif isinstance(value, dict):
            value = value[part]
        else:
            raise KeyError(part)
    return value


def _check_binding(binding):
    if not isinstance(binding, dict):
        raise RefreshError('binding-object-required')
    if set(binding) != {'sourceId', 'releaseId', 'countries', 'domains', 'metadata',
                        'acquiredAtSelector', 'fields', 'unknowns', 'holds', 'adapter'}:
        raise RefreshError('binding-fields-invalid')
    for key in ('sourceId', 'releaseId'):
        if not isinstance(binding[key], str) or not binding[key].strip():
            raise RefreshError('binding-identity-invalid')
    for key, allowed in (('countries', COUNTRIES), ('domains', DOMAINS)):
        values = binding[key]
        if (not isinstance(values, list) or not values or len(set(values)) != len(values)
                or any(not isinstance(v, str) or v not in allowed for v in values)):
            raise RefreshError('binding-applicability-invalid')
    meta = binding['metadata']
    if (not isinstance(meta, dict) or set(meta) != {'path', 'sha256'}
            or not isinstance(meta['path'], str) or not isinstance(meta['sha256'], str)
            or not HEX.fullmatch(meta['sha256'])):
        raise RefreshError('metadata-pin-invalid')
    for key in ('unknowns', 'holds'):
        if (not isinstance(binding[key], list)
                or any(not isinstance(v, str) or not v.strip() for v in binding[key])):
            raise RefreshError('binding-blockers-invalid')
    if binding['adapter'] is not None and not isinstance(binding['adapter'], dict):
        raise RefreshError('adapter-declaration-invalid')
    if (not isinstance(binding['fields'], dict) or not binding['fields']
            or len(binding['fields']) > 32):
        raise RefreshError('metadata-fields-required')
    for key, pointer in binding['fields'].items():
        if not isinstance(key, str) or not key or '/' in key or '~' in key:
            raise RefreshError('metadata-field-name-invalid')
        if not isinstance(pointer, str) or not pointer.startswith('/'):
            raise RefreshError('invalid-metadata-selector')
    if not isinstance(binding['acquiredAtSelector'], str):
        raise RefreshError('acquisition-selector-required')


def _read_regular(path, *, limit, allow_empty=False):
    """Bound reads to one checked descriptor, including ancestor identities.

Linux no-follow/nonblocking opens reject special files before any read.
A pathname is never reopened after its content/identity has been validated.
"""
    required = ('O_NOFOLLOW', 'O_NONBLOCK', 'O_DIRECTORY', 'O_CLOEXEC')
    if any(not hasattr(os, flag) for flag in required):
        raise RefreshError('bounded-reader-platform-unsupported')
    path = safe_path(path)
    parts = path.parts[1:]
    if not parts:
        raise RefreshError('bounded-file-path-required')
    identity = lambda info: (info.st_dev, info.st_ino)
    snapshot = lambda info: (info.st_dev, info.st_ino, info.st_size,
                             info.st_mtime_ns, info.st_ctime_ns, info.st_nlink)
    flags = os.O_RDONLY | os.O_CLOEXEC | os.O_NOFOLLOW | os.O_NONBLOCK
    try:
        with ExitStack() as stack:
            parent = os.open(path.anchor, flags | os.O_DIRECTORY)
            stack.callback(os.close, parent)
            for component in parts[:-1]:
                before_dir = os.stat(component, dir_fd=parent, follow_symlinks=False)
                if not stat.S_ISDIR(before_dir.st_mode):
                    raise RefreshError('bounded-file-ancestor-rejected')
                opened = os.open(component, flags | os.O_DIRECTORY, dir_fd=parent)
                stack.callback(os.close, opened)
                if identity(before_dir) != identity(os.fstat(opened)):
                    raise RefreshError('bounded-file-ancestor-changed')
                parent = opened
            name = parts[-1]
            before = os.stat(name, dir_fd=parent, follow_symlinks=False)
            if (not stat.S_ISREG(before.st_mode) or before.st_nlink != 1
                    or not (0 if allow_empty else 1) <= before.st_size <= limit):
                raise RefreshError('bounded-file-type-size-or-link-rejected')
            descriptor = os.open(name, flags, dir_fd=parent)
            stack.callback(os.close, descriptor)
            opened = os.fstat(descriptor)
            if (not stat.S_ISREG(opened.st_mode) or opened.st_nlink != 1
                    or snapshot(before) != snapshot(opened)):
                raise RefreshError('bounded-file-changed-before-read')
            blocks = []
            consumed = 0
            while True:
                block = os.read(descriptor, min(65536, limit - consumed + 1))
                if not block:
                    break
                consumed += len(block)
                if consumed > limit:
                    raise RefreshError('bounded-file-read-limit')
                blocks.append(block)
            after = os.fstat(descriptor)
            current = os.stat(name, dir_fd=parent, follow_symlinks=False)
            if (snapshot(opened) != snapshot(after) or snapshot(after) != snapshot(current)
                    or consumed != opened.st_size):
                raise RefreshError('bounded-file-changed-during-read')
            return b''.join(blocks)
    except FileNotFoundError:
        raise
    except OSError:
        raise RefreshError('bounded-file-open-or-read-rejected') from None


def read_metadata(binding):
    """Read bounded JSON metadata only; never stat/hash referenced source bodies."""
    _check_binding(binding)
    path = Path(binding['metadata']['path'])
    if path.suffix != '.json':
        raise RefreshError('metadata-json-only-no-source-body')
    return _read_regular(path, limit=LIMIT)


def assess(binding, raw, *, now):
    """Pure bounded preflight of supplied metadata bytes, with explicit clock.

Holds are never permissions. No result here authorizes processing, even if a
caller edits its own configuration to clear a hold. Shared acceptance still
requires an independently reviewed code-owned SourceContract.
"""
    result = {'sourceId': binding.get('sourceId') if isinstance(binding, dict) else None,
              'status': 'malformed', 'diagnostics': [], 'record': None,
              'inputKey': None, 'acquisitionAgeDays': None,
              'refreshDecision': 'none-no-download', 'networkRequests': 0,
              'stageExecutionAuthorized': False, 'countryAccepted': False,
              'realSourceCapability': 'unsupported-unselected'}
    try:
        _check_binding(binding)
        clock = timestamp(now)
        result['inputKey'] = sha(canonical({'version': VERSION, 'binding': binding}))
        if raw is None:
            result.update(status='missing', diagnostics=['metadata-input-missing'])
            return result
        if not isinstance(raw, bytes) or not 0 < len(raw) <= LIMIT:
            raise RefreshError('metadata-input-limit-or-type')
        if sha(raw) != binding['metadata']['sha256']:
            result.update(status='stale-input', diagnostics=['metadata-pin-mismatch'])
            return result
        document = strict_json(raw)
        if not isinstance(document, dict):
            raise RefreshError('metadata-object-required')
        # Ignore filesystem mtime and local verification age. Only this pinned
        # original acquisition claim supplies the cache age; not a source grant.
        acquired = timestamp(_pointer(document, binding['acquiredAtSelector']))
        if acquired > clock:
            raise RefreshError('acquisition-timestamp-in-future')
        age = clock - acquired
        result['acquisitionAgeDays'] = age.days
        result['refreshDecision'] = ('reuse-retained-no-download' if age < timedelta(days=30)
                                     else 'conditional-review-required-no-download')
        result['inputKey'] = sha(canonical({'version': VERSION, 'binding': binding}))
        selected = {key: deepcopy(_pointer(document, pointer))
                    for key, pointer in binding['fields'].items()}
        record = {'id': 'metadata:' + binding['sourceId'] + ':' + binding['releaseId'],
                  'kind': 'source-input-metadata', 'schemaVersion': VERSION,
                  'countries': list(binding['countries']), 'data': selected,
                  'provenance': {'sourceId': binding['sourceId'],
                                 'releaseId': binding['releaseId'],
                                 'fetchedAt': acquired.isoformat(),
                                 'fieldOrigins': {}}}
        # Only scalar fields are declared by this metadata contract. Source JSON
        # objects/arrays require a separate reviewed binding, not invented joins.
        if any(isinstance(value, (dict, list)) for value in selected.values()):
            raise RefreshError('metadata-scalar-selector-required')
        for key in selected:
            record['provenance']['fieldOrigins']['/data/' + key] = {
                'kind': 'source', 'sourceId': binding['sourceId'],
                'releaseId': binding['releaseId'], 'inputPath': 'metadata.json',
                'inputSha256': sha(raw), 'sourceRecordId': 'retained-manifest',
                'sourceField': binding['fields'][key]}
        if len(canonical(record)) > LIMIT:
            raise RefreshError('metadata-candidate-limit')
        errors = field_origin_errors(record, {'metadata.json': sha(raw)})
        if errors:
            raise RefreshError('shared-field-origin-invalid')
        diagnostics = ['held:' + code for code in binding['holds']]
        diagnostics += ['unknown:' + code for code in binding['unknowns']]
        adapter = binding['adapter']
        if adapter is not None:
            # Explicit shared retained-format match only. Names/domains are not
            # country coverage or a right to invoke the adapter.
            keys = {'sourceId', 'releaseId'}
            if set(adapter) != keys or not all(isinstance(adapter[k], str) for k in keys):
                raise RefreshError('adapter-declaration-invalid')
            if any(adapter[k] != binding[k] for k in keys):
                diagnostics.append('adapter-identity-mismatch')
            elif not any(all(row[k] == adapter[k] for k in keys)
                         for row in retained_adapters()):
                diagnostics.append('adapter-release-unsupported')
            else:
                result['realSourceCapability'] = 'shared-retained-format-only-not-executed'
        if binding['holds']:
            result.update(status='held', diagnostics=sorted(diagnostics))
        elif age >= timedelta(days=30):
            result.update(status='stale-input', diagnostics=sorted(diagnostics + ['acquisition-age-at-least-30-days']))
        elif diagnostics:
            result.update(status='missing', diagnostics=sorted(diagnostics))
        else:
            result.update(status='ready-metadata-candidate', record=record)
    except (RefreshError, ValueError, TypeError, KeyError, IndexError, OverflowError, RecursionError):
        # Fixed codes only: no source values or arbitrary exception text in errors.
        result.update(status='malformed', diagnostics=['metadata-or-binding-malformed'], record=None)
    return result


def plan(bindings, *, now, reader=read_metadata):
    """Isolate each input failure; no one-source failure hides another source."""
    if not isinstance(bindings, list) or not 0 < len(bindings) <= MAX_BINDINGS:
        raise RefreshError('portfolio-binding-count-invalid')
    results = []
    seen = set()
    for binding in bindings:
        identity = ((binding.get('sourceId'), binding.get('releaseId'))
                    if isinstance(binding, dict) and all(isinstance(binding.get(k), str)
                    for k in ('sourceId', 'releaseId')) else None)
        if identity is not None and identity in seen:
            raise RefreshError('duplicate-binding-identity')
        if identity is not None:
            seen.add(identity)
        try:
            raw = reader(binding)
            result = assess(binding, raw, now=now)
        except FileNotFoundError:
            result = assess(binding, None, now=now)
        except (OSError, RefreshError, ValueError, TypeError):
            result = {'sourceId': binding.get('sourceId') if isinstance(binding, dict) else None,
                      'status': 'malformed', 'diagnostics': ['metadata-reader-rejected'],
                      'record': None, 'inputKey': None, 'networkRequests': 0,
                      'stageExecutionAuthorized': False, 'countryAccepted': False,
              'realSourceCapability': 'unsupported-unselected'}
        results.append(result)
    records = [row['record'] for row in results if row['record'] is not None]
    encoded = encode_records(records)  # Existing shared singleton JSONL policy.
    stable = [{key: row.get(key) for key in ('sourceId', 'status', 'diagnostics', 'inputKey')}
              for row in results]
    implementation = sha(_read_regular(__file__, limit=LIMIT))
    return {'schemaVersion': VERSION, 'implementationSha256': implementation, 'results': results,
            'candidateSha256': sha(encoded), 'metadataCandidates': len(records),
            'buildKey': sha(canonical({'version': VERSION, 'implementationSha256': implementation, 'inputs': stable,
                                       'candidateSha256': sha(encoded)})),
            'networkRequests': 0, 'datasetRecords': 0, 'countryAccepted': False,
            'stageExecutionAuthorized': False}, encoded


def write_plan(report, candidate, directory):
    """Immutable isolated diagnostics. A matching replay validates cached output."""
    directory = safe_path(directory)
    def replay_identity(value):
        value = deepcopy(value)
        for item in value.get('results', []):
            item.pop('acquisitionAgeDays', None)
        return canonical(value)
    if directory.exists():
        try:
            old = strict_json(_read_regular(directory / 'plan.json', limit=REPLAY_LIMIT))
            prior = _read_regular(directory / 'metadata-candidates.jsonl',
                                  limit=REPLAY_LIMIT, allow_empty=True)
            if (not isinstance(old, dict) or not isinstance(old.get('results'), list)
                    or any(not isinstance(item, dict) for item in old['results'])):
                raise RefreshError('replay-plan-malformed')
            replay_identity(old)
        except (OSError, ValueError, TypeError, UnicodeError, RecursionError):
            raise RefreshError('replay-input-rejected') from None
        if (old.get('buildKey') == report['buildKey']
                and sha(prior) == old.get('candidateSha256') == sha(candidate)
                and replay_identity(old) == replay_identity(report)):
            return 'no-op-verified-metadata-cache'
        raise RefreshError('output-conflict-use-new-directory')
    directory.mkdir(parents=True)
    (directory / 'metadata-candidates.jsonl').write_bytes(candidate)
    (directory / 'plan.json').write_bytes(canonical(report))
    return 'written-isolated-metadata-plan'


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', required=True, type=Path)
    parser.add_argument('--now', required=True, help='Explicit UTC policy clock; never filesystem mtime')
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args(argv)
    if args.config.suffix != '.json':
        raise RefreshError('portfolio-config-json-only')
    try:
        config = strict_json(_read_regular(args.config, limit=LIMIT))
    except (OSError, ValueError, UnicodeError, RecursionError):
        raise RefreshError('portfolio-config-read-rejected') from None
    if (not isinstance(config, dict) or config.get('schemaVersion') != VERSION
            or not isinstance(config.get('bindings'), list)):
        raise RefreshError('portfolio-config-invalid')
    report, candidate = plan(config['bindings'], now=args.now)
    decision = write_plan(report, candidate, args.output)
    print(canonical({'decision': decision, 'buildKey': report['buildKey'],
                     'statuses': [row['status'] for row in report['results']],
                     'metadataCandidates': report['metadataCandidates'],
                     'datasetRecords': 0, 'networkRequests': 0}).decode(), end='')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
