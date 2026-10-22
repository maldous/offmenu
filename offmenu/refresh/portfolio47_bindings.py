"""LI/KY/LA/LB metadata bindings; never reads payloads or enables admissions.

The bundled catalog is reviewed portfolio configuration, not a runtime source
registry. A ready result means metadata is ready for binding review only.
"""
import argparse
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
import re

from .acquisition import MIN_TTL
from .core import RefreshError, canonical, safe_path, sha, strict_json, timestamp
from .field_provenance import field_origin_errors
from .serialization import encode_records

CATALOG = Path(__file__).with_name('portfolio47_sources.json')
MAX_METADATA_BYTES = 256 * 1024
MAX_SOURCES = 16
MAX_FILES = 8
MAX_FIELDS = 32
DOMAINS = ('ingredients', 'recipes', 'nutrition', 'retailers/providers',
           'prices/baskets', 'dietary references')
COUNTRIES = ('LI', 'KY', 'LA', 'LB')
DIGEST = re.compile(r'[0-9a-f]{64}')
POLICY = {
    'schemaVersion': 'offmenu-portfolio47-binding-policy/1',
    'scope': 'metadata-only-private-binding-review',
    'unknown': 'explicit-null-no-imputation',
    'sourceBodies': 'never-opened',
    'acceptance': 'not-enabled',
    'cache': 'shared-source-neutral-planner-required-no-network',
}
POLICY_SHA = sha(canonical(POLICY))


def _pointer(document, pointer):
    if not isinstance(pointer, str) or not pointer.startswith('/'):
        raise ValueError('metadata-selector-invalid')
    value = document
    for token in pointer[1:].split('/'):
        # Reject malformed escapes, negative/aliased array indexes.
        if re.search(r'~(?![01])', token):
            raise ValueError('metadata-selector-invalid')
        token = token.replace('~1', '/').replace('~0', '~')
        if isinstance(value, list):
            if not re.fullmatch(r'0|[1-9][0-9]*', token):
                raise KeyError(token)
            value = value[int(token)]
        else:
            value = value[token]
    if isinstance(value, (dict, list)):
        raise ValueError('metadata-scalar-selector-required')
    return value


def _valid_spec(spec):
    if (not isinstance(spec, dict)
            or any(not isinstance(spec.get(k), str) or not spec[k]
                   for k in ('sourceId', 'releaseId', 'country', 'evidenceRole'))
            or spec['country'] not in COUNTRIES
            or type(spec.get('fixture')) is not bool
            or not isinstance(spec.get('holds'), list)
            or any(not isinstance(h, str) or not re.fullmatch('[a-z][a-z0-9-]{0,95}', h)
                   for h in spec['holds'])
            or not isinstance(spec.get('domains'), list)
            or not spec['domains']
            or any(not isinstance(d, str) for d in spec['domains'])
            or not set(spec['domains']) <= set(DOMAINS)
            or not isinstance(spec.get('files'), dict)
            or not 1 <= len(spec['files']) <= MAX_FILES
            or not isinstance(spec.get('fields'), dict)
            or not 1 <= len(spec['fields']) <= MAX_FIELDS
            or not isinstance(spec.get('identityChecks'), list)
            or not 1 <= len(spec['identityChecks']) <= 8
            or not isinstance(spec.get('acquisition'), dict)):
        return False
    # Validate the full declaration boundary before sorting, dereferencing or
    # reporting it. Malformed contracts must not abort an independent peer.
    name_pattern = '[A-Za-z][A-Za-z0-9_]{0,63}'
    if any(not isinstance(k, str) or not re.fullmatch(name_pattern, k)
           for k in (*spec['files'], *spec['fields'])):
        return False

    def selector(declaration):
        return (isinstance(declaration, dict)
                and isinstance(declaration.get('file'), str)
                and declaration['file'] in spec['files']
                and isinstance(declaration.get('pointer'), str))

    if (not selector(spec['acquisition'])
            or not isinstance(spec['acquisition'].get('basis'), str)
            or spec['acquisition']['basis'] not in (
                'original-completed', 'request-start-only',
                'receipt-observation-only', 'landing-access-only')
            or any(not selector(d) for d in spec['fields'].values())
            or any(not selector(d) or 'expected' not in d for d in spec['identityChecks'])
            or spec.get('validation') is not None and not selector(spec['validation'])):
        return False
    names = []
    for asset in spec['files'].values():
        if not isinstance(asset, dict):
            return False
        name = asset.get('path')
        if (not isinstance(name, str) or not name.endswith('.json')
                or PurePosixPath(name).is_absolute() or '..' in name.split('/')
                or name != PurePosixPath(name).as_posix() or '\\' in name
                or not isinstance(asset.get('sha256'), str)
                or not DIGEST.fullmatch(asset['sha256'])
                or type(asset.get('bytes')) is not int
                or not 0 < asset['bytes'] <= MAX_METADATA_BYTES
                or asset.get('role') != 'permitted-metadata'):
            return False
        names.append(name)
    return len(names) == len(set(names))


def _metadata(asset, root):
    # Catalog locators are metadata JSON only, never response bodies. Fixture
    # roots expose only authored metadata; source-controlled retainedPath is not
    # taken from a manifest or command supplied by source data.
    if root is None:
        repository_name = asset.get('repositoryPath')
        if repository_name is not None:
            relative = PurePosixPath(repository_name)
            if (relative.is_absolute() or '..' in relative.parts
                    or relative.as_posix() != repository_name or '\\' in repository_name
                    or not repository_name.endswith('.json')):
                raise ValueError('metadata-repository-path-invalid')
            path = safe_path(Path(__file__).resolve().parents[2] / repository_name)
        else:
            location = asset.get('retainedPath')
            if not isinstance(location, str) or not location.endswith('.json'):
                raise FileNotFoundError()
            path = safe_path(location)
    else:
        path = safe_path(safe_path(root) / asset['path'])
    if not path.is_file():
        raise FileNotFoundError()
    if path.stat().st_size != asset['bytes']:
        raise ValueError('metadata-pin-mismatch')
    with path.open('rb') as stream:
        raw = stream.read(MAX_METADATA_BYTES + 1)
    if len(raw) != asset['bytes'] or sha(raw) != asset['sha256']:
        raise ValueError('metadata-pin-mismatch')
    value = strict_json(raw)
    canonical(value)  # Also rejects overflow such as 1e999, not just NaN tokens.
    if not isinstance(value, dict):
        raise ValueError('metadata-object-required')
    return value


def inspect_binding(spec, *, metadata_root=None, now):
    """Inspect bounded metadata only; shared helpers validate origins/JSON/time.

    Clock is explicit for deterministic replay. Validation time is an independent
    observation and NEVER substitutes for original acquisition. No network,
    subprocess, payload fallback, acceptance constructor or pointer publication.
    """
    if not _valid_spec(spec):
        return {'sourceId': None, 'state': 'malformed', 'diagnostics': ['binding-spec-invalid']}
    errors = set()
    documents, inputs = {}, {}
    for role, asset in sorted(spec['files'].items()):
        try:
            documents[role] = _metadata(asset, metadata_root)
            inputs[asset['path']] = asset['sha256']
        except FileNotFoundError:
            errors.add('metadata-missing')
        except (OSError, ValueError, TypeError, RecursionError, RefreshError):
            errors.add('metadata-malformed-or-pin-mismatch')

    def selected(declaration):
        if not isinstance(declaration, dict):
            raise ValueError()
        role, pointer = declaration['file'], declaration['pointer']
        document = documents[role]
        value = _pointer(document, pointer)
        asset = spec['files'][role]
        origin = {'kind': 'source', 'sourceId': spec['sourceId'],
                  'releaseId': spec['releaseId'], 'inputPath': asset['path'],
                  'inputSha256': asset['sha256'], 'sourceRecordId': spec['sourceId'],
                  'sourceField': pointer}
        return value, origin

    unknown_origin = {'kind': 'constant', 'policySha256': POLICY_SHA,
                      'symbol': 'explicit-unknown-metadata-value'}
    for declaration in spec['identityChecks']:
        try:
            actual, _ = selected(declaration)
            if actual != declaration['expected']:
                errors.add('metadata-identity-invalid')
        except (KeyError, IndexError):
            errors.add('metadata-selector-missing')
        except (TypeError, ValueError):
            errors.add('metadata-selector-invalid')
    data, origins = {}, {}
    for name, declaration in sorted(spec['fields'].items()):
        if not re.fullmatch('[A-Za-z][A-Za-z0-9_]{0,63}', name):
            errors.add('metadata-field-name-invalid')
            continue
        try:
            value, origin = selected(declaration)
        except (KeyError, IndexError):
            value, origin = None, deepcopy(unknown_origin)
            errors.add('metadata-selector-missing')
        except (TypeError, ValueError):
            value, origin = None, deepcopy(unknown_origin)
            errors.add('metadata-selector-invalid')
        data[name], origins['/data/' + name] = value, origin

    original, validated, age = None, None, None
    try:
        clock = timestamp(now)
        observed, _ = selected(spec['acquisition'])
        # Request start or generic receipt time does not prove completion.
        if spec['acquisition'].get('basis') == 'original-completed':
            original = timestamp(observed)
            age = (clock - original).total_seconds()
            if age < 0:
                raise ValueError()
        else:
            errors.add('original-acquisition-time-unknown')
        validation = spec.get('validation')
        if validation:
            validated, _ = selected(validation)
            checked = timestamp(validated)
            if checked > clock or (original is not None and checked < original):
                raise ValueError()
    except (KeyError, IndexError):
        errors.add('acquisition-or-validation-metadata-missing')
    except (TypeError, ValueError, RefreshError):
        errors.add('acquisition-or-validation-time-invalid')

    row = {'id': spec['sourceId'] + ':binding', 'kind': 'SourceInputBinding',
           'schemaVersion': 'offmenu-portfolio47-metadata-binding/1', 'data': data,
           'provenance': {'sourceId': spec['sourceId'], 'releaseId': spec['releaseId'],
                          'fetchedAt': original.isoformat() if original else None,
                          'fieldOrigins': origins}}
    if inputs:
        errors.update(field_origin_errors(row, inputs, policy_pins=(POLICY_SHA,)))
    if spec['holds']:
        errors.add('source-scope-held')
    if age is not None and age >= MIN_TTL:
        errors.add('stale-input-needs-reviewed-revalidation')
    malformed = any('invalid' in c or 'malformed' in c or c.startswith('field-origin') for c in errors)
    missing = any('missing' in c or c == 'original-acquisition-time-unknown' for c in errors)
    state = ('malformed' if malformed else 'missing' if missing else 'held' if spec['holds']
             else 'stale' if age is not None and age >= MIN_TTL else 'ready')
    return {'sourceId': spec['sourceId'], 'releaseId': spec['releaseId'],
            'country': spec['country'], 'domains': spec['domains'],
            'evidenceRole': spec['evidenceRole'], 'fixture': spec['fixture'],
            'state': state, 'readyFor': 'metadata-binding-review-only' if state == 'ready' else None,
            'diagnostics': sorted(errors), 'holds': spec['holds'], 'record': row,
            'inputPins': inputs, 'nativeSemantics': deepcopy(spec.get('nativeSemantics', {})),
            'cacheRequest': {'sourceId': spec['sourceId'], 'releaseId': spec['releaseId'],
                             'originalAcquiredAt': original.isoformat() if original else None,
                             'acquisitionTimeBasis': spec['acquisition'].get('basis'),
                             'lastValidatedAt': validated, 'acquisitionAgeSeconds': age,
                             'minimumReuseSeconds': MIN_TTL, 'validationResetsAge': False,
                             'payloadBytesVerified': False, 'networkRequests': 0,
                             'automaticRefreshEnabled': False,
                             'sharedPlanner': 'source-neutral-pure-planner-required'},
            'dataProcessingAuthorized': False, 'acceptedRecords': 0,
            'sourceBodyAdapter': 'not-selected-or-installed-by-this-binding',
            'countryCoverageComplete': False}


def plan(specs, *, metadata_root=None, now, previous_content_sha256=None):
    """Isolate metadata failures and deterministic serialization from shared core."""
    if (not isinstance(specs, list) or not 1 <= len(specs) <= MAX_SOURCES
            or previous_content_sha256 is not None and
            (not isinstance(previous_content_sha256, str) or not DIGEST.fullmatch(previous_content_sha256))):
        raise ValueError('portfolio-plan-input-invalid')
    evaluated_at = timestamp(now).isoformat()
    results = [inspect_binding(s, metadata_root=metadata_root, now=now) for s in specs]
    ids = [r['sourceId'] for r in results if r['sourceId'] is not None]
    if len(ids) != len(set(ids)):
        raise ValueError('portfolio-source-identity-duplicate')
    rows = [r['record'] for r in results if 'record' in r]
    payload = encode_records(rows)
    # Time-dependent age/diagnostics cannot be bypassed by unchanged content.
    content_sha = sha(payload)
    return {'schemaVersion': 'offmenu-portfolio47-binding-plan/1', 'policySha256': POLICY_SHA,
            'evaluatedAt': evaluated_at,
            'results': results, 'contentSha256': content_sha,
            'metadataContentAction': 'unchanged-metadata-no-op' if previous_content_sha256 == content_sha
                                     else 'new-metadata-binding-content',
            'noOpScope': 'metadata content only; every input/pin/time/hold was still checked',
            'isolatedDiagnostics': True, 'networkRequests': 0, 'payloadReads': 0,
            'requiredCountryTypes': {c: list(DOMAINS) for c in COUNTRIES},
            'notCovered': 'A type applicability edge is source context, never a mandatory-source CellRequirement or completeness assertion.',
            'sharedInterfaceBlockers': ['source-neutral-pure-cache-planner-required'],
            'stagingAccepted': False, 'goldenPromotion': False}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--retained-metadata', action='store_true')
    mode.add_argument('--authored-fixture', action='store_true')
    parser.add_argument('--now', required=True)
    parser.add_argument('--previous-content-sha256')
    args = parser.parse_args(argv)
    catalog = strict_json(CATALOG.read_bytes())
    if args.authored_fixture:
        fixture_root = Path(__file__).resolve().parents[2] / 'tests/fixtures/portfolio47'
        specs = strict_json((fixture_root / 'catalog.json').read_bytes())['sources']
        root = fixture_root
    else:
        specs, root = catalog['sources'], None
    report = plan(specs, metadata_root=root, now=args.now,
                  previous_content_sha256=args.previous_content_sha256)
    print(canonical(report).decode(), end='')


if __name__ == '__main__':
    main()
