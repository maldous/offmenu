"""Worker10 retained-metadata bindings. No source payload or acquisition route.

Only caller-supplied metadata paths are opened; references inside them are values.
Uses shared strict JSON, canonical serialization, time and field-origin contracts.
"""
import argparse
from copy import deepcopy
from pathlib import Path
import re
import stat
import sys

from .core import RefreshError, canonical, safe_path, sha, strict_json, timestamp
from .field_provenance import field_origin_errors

MAX_METADATA_BYTES = 1024 * 1024
TYPES = ('ingredients', 'recipes', 'nutrition', 'retailers/providers',
         'prices/baskets', 'dietary references')
COUNTRIES = ('KW', 'NO', 'SA', 'UA')
CONFIG = Path(__file__).resolve().parents[2] / 'config/worker10-staging-bindings.json'


def pointer(document, selector):
    """Resolve an exact JSON pointer; no wildcard, expression or inference."""
    if not isinstance(selector, str) or not selector.startswith('/'):
        raise RefreshError('metadata-selector-invalid')
    value = document
    for raw in selector[1:].split('/'):
        if re.search(r'~(?![01])', raw):
            raise RefreshError('metadata-selector-invalid')
        key = raw.replace('~1', '/').replace('~0', '~')
        if isinstance(value, dict) and key in value:
            value = value[key]
        elif isinstance(value, list) and re.fullmatch(r'0|[1-9][0-9]*', key) and int(key) < len(value):
            value = value[int(key)]
        else:
            raise RefreshError('metadata-selector-missing')
    if isinstance(value, (dict, list)):
        raise RefreshError('metadata-selector-must-be-scalar')
    return value


def validate_config(config):
    if (not isinstance(config, dict) or config.get('schemaVersion') != 'offmenu-worker10-bindings/1'
            or config.get('countries') != list(COUNTRIES)
            or config.get('requiredTypes') != list(TYPES)):
        raise RefreshError('worker10-binding-config-invalid')
    entries = config.get('bindings')
    if not isinstance(entries, list) or not entries:
        raise RefreshError('worker10-bindings-required')
    seen = set()
    for entry in entries:
        if not isinstance(entry, dict):
            raise RefreshError('worker10-binding-invalid')
        for key in ('id', 'sourceId', 'releaseId', 'metadataPath', 'inputPath'):
            if not isinstance(entry.get(key), str) or not entry[key]:
                raise RefreshError('worker10-binding-identity-invalid')
        if entry['id'] in seen:
            raise RefreshError('worker10-binding-duplicate')
        seen.add(entry['id'])
        if (entry.get('country') not in COUNTRIES or not isinstance(entry.get('types'), list)
                or not entry['types'] or any(t not in TYPES for t in entry['types'])
                or entry.get('sourceStage') not in ('held', 'metadata-only')
                or not isinstance(entry.get('prerequisites'), list)
                or not isinstance(entry.get('fields'), dict) or not entry['fields']):
            raise RefreshError('worker10-binding-scope-invalid')
        if not isinstance(entry.get('sha256'), str) or not re.fullmatch('[0-9a-f]{64}', entry['sha256']):
            raise RefreshError('worker10-binding-pin-invalid')
        if type(entry.get('bytes')) is not int or not 0 < entry['bytes'] <= MAX_METADATA_BYTES:
            raise RefreshError('worker10-binding-size-invalid')
        if any(not re.fullmatch('[A-Za-z][A-Za-z0-9]*', name) or not isinstance(selector, str)
               for name, selector in entry['fields'].items()):
            raise RefreshError('worker10-binding-fields-invalid')
    return config


def load_config(path=CONFIG):
    path = safe_path(path)
    if path.stat().st_size > MAX_METADATA_BYTES:
        raise RefreshError('worker10-config-limit')
    return validate_config(strict_json(path.read_bytes()))


def assess(config, metadata_paths, *, validated_at, previous_staging=None, force=False):
    """Project pinned metadata only; failures are isolated except pin/budget stops.

    Paths are an explicit id->metadata-path mapping. Never follows original/manifest
    paths found in documents. Source stages/rights are fixed reviewed declarations,
    not obtained from HTTP or inferred from validation success. `force` cannot
    enable a download, alter pins or reset the original acquisition age.
    """
    validate_config(config)
    observed = timestamp(validated_at)
    if not isinstance(metadata_paths, dict):
        raise RefreshError('worker10-metadata-path-map-required')
    if previous_staging is not None and not isinstance(previous_staging, bytes):
        raise RefreshError('worker10-prior-staging-bytes-required')
    results, rows, consumed = [], [], 0
    config_sha = sha(canonical(config))
    for entry in sorted(config['bindings'], key=lambda item: item['id']):
        item = {'bindingId': entry['id'], 'country': entry['country'],
                'sourceStage': entry['sourceStage'], 'types': list(entry['types']),
                'prerequisites': deepcopy(entry['prerequisites']), 'status': 'missing',
                'diagnostics': [], 'metadataRecords': 0}
        results.append(item)
        path = metadata_paths.get(entry['id'])
        if path is None:
            item['diagnostics'] = ['metadata-input-missing']
            continue
        try:
            path = safe_path(path)
            info = path.stat()
            if not stat.S_ISREG(info.st_mode):
                raise RefreshError('metadata-regular-file-required')
            if info.st_size > MAX_METADATA_BYTES - consumed:
                raise RefreshError('metadata-cumulative-budget-exhausted')
            with path.open('rb') as handle:
                raw = handle.read(MAX_METADATA_BYTES - consumed + 1)
            consumed += len(raw)
            if consumed > MAX_METADATA_BYTES:
                raise RefreshError('metadata-cumulative-budget-exhausted')
            if len(raw) != entry['bytes'] or sha(raw) != entry['sha256']:
                raise RefreshError('metadata-pin-mismatch')
            document = strict_json(raw)
            data = {name: pointer(document, selector) for name, selector in entry['fields'].items()}
            acquired_selector = entry.get('originalAcquiredAtSelector')
            acquired = timestamp(pointer(document, acquired_selector)) if acquired_selector else None
            if acquired is not None and acquired > observed:
                raise RefreshError('metadata-acquisition-in-future')
            age = (observed - acquired).total_seconds() if acquired is not None else None
            item['cache'] = {
                'originalAcquiredAt': acquired.isoformat() if acquired is not None else None,
                'validatedAt': validated_at, 'validationAgeSeconds': 0,
                'acquisitionAgeSeconds': age, 'minimumReuseDays': 30,
                'decision': ('original-acquisition-age-unknown' if age is None else
                             'reuse-retained-metadata-zero-download' if age < 30 * 86400 else
                             'stale-input-review-required-zero-download'),
                'mtimeUsedForFreshness': False, 'revalidationResetsAcquisitionAge': False,
                'forceRequested': bool(force), 'downloadAllowed': False,
            }
            row = {'id': 'worker10-metadata:' + entry['id'], 'kind': 'source-input-metadata',
                   'countries': [entry['country']], 'data': data,
                   'provenance': {'sourceId': entry['sourceId'], 'releaseId': entry['releaseId'],
                                  'metadataSha256': entry['sha256'], 'bindingConfigSha256': config_sha,
                                  'fieldOrigins': {
                                      '/data/' + name: {'kind': 'source', 'sourceId': entry['sourceId'],
                                                       'releaseId': entry['releaseId'],
                                                       'inputPath': entry['inputPath'],
                                                       'inputSha256': entry['sha256'],
                                                       'sourceRecordId': entry['id'],
                                                       'sourceField': selector}
                                      for name, selector in entry['fields'].items()}}}
            errors = field_origin_errors(row, {entry['inputPath']: entry['sha256']})
            if errors:
                raise RefreshError('metadata-field-origin-invalid')
            rows.append(row)
            item['metadataRecords'] = 1
            item['status'] = ('stale-input' if age is not None and age >= 30 * 86400 else
                              'held' if entry['sourceStage'] == 'held' else 'valid')
            if item['status'] == 'stale-input':
                item['diagnostics'] = ['original-acquisition-age-requires-review']
        except FileNotFoundError:
            item['diagnostics'] = ['metadata-input-missing']
        except (RefreshError, OSError, ValueError, TypeError, RecursionError) as error:
            code = str(error) if isinstance(error, RefreshError) else 'metadata-malformed-or-unreadable'
            item.update(status='malformed', diagnostics=[code])
            if code in ('metadata-pin-mismatch', 'metadata-cumulative-budget-exhausted'):
                return _report(config, results, [], consumed, validated_at, 'stopped', previous_staging)
    return _report(config, results, rows, consumed, validated_at, 'assessed', previous_staging)


def _report(config, results, rows, consumed, validated_at, status, previous):
    staged = canonical(rows)
    coverage = []
    for country in COUNTRIES:
        for kind in TYPES:
            ids = [b['id'] for b in config['bindings'] if b['country'] == country and kind in b['types']]
            coverage.append({'country': country, 'type': kind, 'metadataBindingIds': ids,
                             'dataStatus': 'unaccepted-evidence-only' if ids else 'missing-input',
                             'dependencyOwner': 'Morgan/Gateway scheduling; existing source custodians retain custody',
                             'nextAction': ('Resolve exact binding prerequisites and independent semantic review; '
                                            'metadata presence does not establish category completeness.' if ids else
                                            'Select an exact finite source/release with permitted use, native selectors, '
                                            'units, extent and independent semantic acceptance; no acquisition selected.'),
                             'countryComplete': False})
    return {'schemaVersion': 'offmenu-worker10-metadata-staging/1', 'status': status,
            'validatedAt': validated_at, 'results': results, 'metadataBytesRead': consumed,
            'staging': rows, 'stagingSha256': sha(staged),
            'replay': 'verified-no-op' if status != 'stopped' and previous == staged else 'not-replayed',
            'coverage': coverage, 'sourceBodiesRead': 0, 'networkRequests': 0,
            'normalizedFoodRecords': 0, 'mappedFoodRecords': 0, 'goldAdmittedRecords': 0,
            'productionAdmission': False, 'countryComplete': False}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--validated-at', required=True, help='Explicit UTC observation time')
    parser.add_argument('--retained-metadata', action='store_true',
                        help='Open ONLY the five exact configured metadata documents')
    args = parser.parse_args(argv)
    try:
        config = load_config()
        paths = {b['id']: b['metadataPath'] for b in config['bindings']} if args.retained_metadata else {}
        report = assess(config, paths, validated_at=args.validated_at)
    except (RefreshError, ValueError, OSError) as error:
        code = str(error) if isinstance(error, RefreshError) else 'metadata-config-malformed-or-unreadable'
        sys.stdout.buffer.write(canonical({'status': 'stopped', 'diagnostics': [code],
                                          'sourceBodiesRead': 0, 'networkRequests': 0}))
        return 2
    sys.stdout.buffer.write(canonical(report))
    return 2 if report['status'] == 'stopped' else 0


if __name__ == '__main__':
    raise SystemExit(main())
