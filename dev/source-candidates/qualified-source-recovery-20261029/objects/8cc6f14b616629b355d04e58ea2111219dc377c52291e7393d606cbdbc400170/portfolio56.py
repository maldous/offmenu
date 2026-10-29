"""ES/NI/TK/WF metadata binding preflight. No body parser or admission route.

All filesystem inputs are explicitly pinned JSON metadata. This module never
constructs SourceContract from a manifest, imports historical engines, fetches,
refreshes, or runs an adapter. A ready result is a metadata candidate only.
"""
import argparse
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


def read_metadata(binding):
    """Read bounded JSON metadata only; never stat/hash referenced source bodies."""
    _check_binding(binding)
    path = Path(binding['metadata']['path'])
    if path.suffix != '.json':
        raise RefreshError('metadata-json-only-no-source-body')
    path = safe_path(path)
    info = path.stat()
    if not stat.S_ISREG(info.st_mode) or not 0 < info.st_size <= LIMIT:
        raise RefreshError('metadata-file-limit')
    raw = path.read_bytes()
    if not 0 < len(raw) <= LIMIT:
        raise RefreshError('metadata-file-limit')
    return raw


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
    implementation = sha(Path(__file__).read_bytes())
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
        old = strict_json(safe_path(directory / 'plan.json').read_bytes())
        prior = safe_path(directory / 'metadata-candidates.jsonl').read_bytes()
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
    config_path = safe_path(args.config)
    if not config_path.is_file() or config_path.stat().st_size > LIMIT:
        raise RefreshError('portfolio-config-limit')
    config = strict_json(config_path.read_bytes())
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
