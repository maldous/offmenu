"""Worker08 metadata-only bindings. No body reader, transport or source admission.

Policies are reviewed application configuration, never manifest authority. The
CLI exposes only fixed held sources or the explicitly authored synthetic fixture.
"""
import argparse
import json
import re
from pathlib import Path

from .acquisition import MIN_TTL
from .core import RefreshError, atomic_json, canonical, exact_keys, safe_path, sha, strict_json, timestamp
from .field_provenance import field_origin_errors
from .national_tabular import valid_input_name

ROOT = Path(__file__).resolve().parents[2]
COUNTRIES = frozenset(('AW', 'AX', 'AZ', 'BA'))
DATA_TYPES = frozenset(('ingredients/composition', 'recipes', 'nutrition',
                        'retailers/providers', 'prices/baskets', 'dietary references'))
MAX_METADATA = 65536


def load_metadata(path):
    """Read only explicitly selected small metadata, never referenced inputs."""
    path = safe_path(path)
    if not path.is_file() or path.stat().st_size > MAX_METADATA:
        raise RefreshError('binding-metadata-missing-or-too-large')
    value = strict_json(path.read_bytes())
    if not isinstance(value, dict):
        raise RefreshError('binding-metadata-not-object')
    return value


def policies():
    return load_metadata(ROOT / 'config/portfolio08-source-bindings.json')['sources']


def _pin_valid(pin):
    return (isinstance(pin, dict) and set(pin) == {'path', 'sha256', 'bytes'}
            and valid_input_name(pin['path']) and type(pin['bytes']) is int
            and 0 < pin['bytes'] <= MAX_METADATA and isinstance(pin['sha256'], str)
            and len(pin['sha256']) == 64
            and all(c in '0123456789abcdef' for c in pin['sha256']))


def assess(policy, manifest, *, now, metadata=None):
    """Pure plan/metadata candidate. Does not verify or open source input bytes.

The trusted caller supplies policy. Permission strings/flags in a manifest do
not grant authority. Every result remains metadata-only and unaccepted.
"""
    result = {'schemaVersion': 'offmenu-owner08-binding-result/1', 'sourceId': None,
              'status': 'malformed', 'diagnostics': [], 'candidate': None,
              'networkRequests': 0, 'sourceBodiesRead': 0,
              'sourceAdmission': False, 'countryComplete': False,
              'inputBytesVerified': False, 'cacheMetadata': None,
              'refreshPlanner': {'status': 'unsupported-shared-interface',
                                 'dependency': 'Morgan/00 pure retained-input planner proposal',
                                 'networkRequests': 0}}

    def stop(status, *codes):
        result.update(status=status, diagnostics=list(codes))
        return result

    try:
        # Detached finite JSON data only; never retain caller mutable aliases.
        raw_policy = canonical(policy)
        if len(raw_policy) > MAX_METADATA:
            return stop('malformed', 'binding-policy-too-large')
        policy = strict_json(raw_policy)
        if not isinstance(policy, dict) or not isinstance(policy.get('sourceId'), str):
            return stop('malformed', 'binding-policy-invalid')
        result['sourceId'] = policy['sourceId']
        result['evidence'] = policy.get('evidence', [])
        result['applicability'] = policy.get('applicability', {})
        if policy.get('enabled') is not True or policy.get('holds'):
            return stop('held', *(policy.get('holds') or ['metadata-policy-not-enabled']))
        if policy.get('operations') != ['stage-authored-metadata']:
            return stop('held', 'metadata-operation-not-qualified')
        if (not isinstance(policy.get('countries'), list) or not policy['countries']
                or len(set(policy['countries'])) != len(policy['countries'])
                or not set(policy['countries']) <= COUNTRIES
                or policy.get('dataType') not in DATA_TYPES):
            return stop('malformed', 'binding-applicability-invalid')
        pins = policy.get('inputs')
        if (not isinstance(pins, list) or not pins or len(pins) > 32
                or not all(_pin_valid(p) for p in pins)
                or len({p['path'] for p in pins}) != len(pins)):
            return stop('malformed', 'binding-input-pin-contract-invalid')
        selectors = policy.get('selectors')
        if not isinstance(selectors, dict) or not selectors:
            return stop('missing', 'exact-field-selectors-not-supplied')
        if manifest is None:
            return stop('missing', 'input-manifest-not-supplied')
        raw_manifest = canonical(manifest)
        if len(raw_manifest) > MAX_METADATA:
            return stop('malformed', 'binding-manifest-too-large')
        manifest = strict_json(raw_manifest)
        if not isinstance(manifest, dict):
            return stop('malformed', 'input-manifest-not-object')
        required = {'schemaVersion', 'sourceId', 'releaseId', 'countries', 'dataType',
                    'inputs', 'data', 'fieldOrigins', 'cacheEvidence'}
        if required - set(manifest):
            return stop('missing', *['missing-' + k for k in sorted(required - set(manifest))])
        exact_keys(manifest, required)
        if (manifest['schemaVersion'] != 'offmenu-owner08-source-input/1'
                or manifest['sourceId'] != policy['sourceId']
                or manifest['releaseId'] != policy['releaseId']
                or manifest['countries'] != policy['countries']
                or manifest['dataType'] != policy['dataType']):
            return stop('malformed', 'source-release-scope-mismatch')
        if manifest['inputs'] != pins:
            return stop('malformed', 'retained-manifest-pin-mismatch')
        data = manifest['data']
        if (not isinstance(data, dict) or set(data) != set(selectors)
                or not {'value', 'unit', 'basis'} <= set(data)
                or any(v is not None and not isinstance(v, str) for v in data.values())):
            return stop('malformed', 'lexical-data-or-field-set-invalid')
        if data['unit'] != policy.get('nativeUnit') or data['basis'] != policy.get('nativeBasis'):
            return stop('malformed', 'native-unit-or-basis-mismatch')
        if metadata is None:
            return stop('missing', 'pinned-metadata-inputs-not-supplied')
        if not isinstance(metadata, dict) or set(metadata) != {p['path'] for p in pins}:
            return stop('malformed', 'metadata-input-set-mismatch')
        documents = {}
        for pin in pins:
            raw = metadata[pin['path']]
            if isinstance(raw, str):
                raw = raw.encode('utf-8')
            if (not isinstance(raw, bytes) or len(raw) != pin['bytes']
                    or len(raw) > MAX_METADATA or sha(raw) != pin['sha256']):
                return stop('malformed', 'metadata-input-bytes-mismatch')
            documents[pin['path']] = strict_json(raw)
        result['inputBytesVerified'] = True
        row = {'kind': 'sourceMetadata', 'data': data,
               'provenance': {'sourceId': policy['sourceId'], 'releaseId': policy['releaseId'],
                              'fieldOrigins': manifest['fieldOrigins']}}
        errors = field_origin_errors(row, {p['path']: p['sha256'] for p in pins})
        if errors:
            return stop('malformed', *errors)
        for field, coordinate in selectors.items():
            actual = manifest['fieldOrigins'].get('/data/' + field)
            expected = {'kind': 'source', 'sourceId': policy['sourceId'],
                        'releaseId': policy['releaseId'], **coordinate}
            if actual != expected:
                return stop('malformed', 'field-selector-mismatch:' + field)
            pointer = coordinate['sourceRecordId'] + coordinate['sourceField']
            if (not coordinate['sourceRecordId'].startswith('/')
                    or not coordinate['sourceField'].startswith('/')
                    or re.search(r'~(?![01])', pointer)):
                return stop('malformed', 'metadata-selector-invalid')
            selected = documents[coordinate['inputPath']]
            for token in pointer.split('/')[1:]:
                token = token.replace('~1', '/').replace('~0', '~')
                if isinstance(selected, list):
                    if not token.isdigit() or str(int(token)) != token:
                        return stop('malformed', 'metadata-selector-invalid')
                    selected = selected[int(token)]
                else:
                    selected = selected[token]
            if type(selected) is not type(data[field]) or selected != data[field]:
                return stop('malformed', 'metadata-field-value-mismatch:' + field)
        bundle_key = sha(canonical({'sourceId': policy['sourceId'], 'releaseId': policy['releaseId'],
                                    'inputs': pins}))
        evidence = manifest['cacheEvidence']
        if evidence is None:
            return stop('missing', 'cache-acquisition-evidence-not-supplied')
        exact_keys(evidence, ('inputBundleSha256', 'originalAcquiredAt', 'checkedAt'))
        if evidence['inputBundleSha256'] != bundle_key:
            return stop('malformed', 'cache-bundle-identity-mismatch')
        clock = timestamp(now)
        acquired = timestamp(evidence['originalAcquiredAt'])
        checked = timestamp(evidence['checkedAt'])
        if not acquired <= checked <= clock:
            return stop('malformed', 'cache-time-order-invalid')
        acquisition_age = (clock - acquired).total_seconds()
        validation_age = (clock - checked).total_seconds()
        result['cacheMetadata'] = {'minimumReuseSeconds': MIN_TTL,
                               'originalAcquiredAt': evidence['originalAcquiredAt'],
                               'checkedAt': evidence['checkedAt'],
                               'acquisitionAgeSeconds': acquisition_age,
                               'validationAgeSeconds': validation_age,
                               'metadataAge': 'under-30-days' if validation_age < MIN_TTL
                               else '30-days-or-older',
                               'scope': 'metadata-age-diagnostic-only',
                               'operationalReuseOrRefreshQualified': False,
                               'revalidationResetsOriginalAcquisition': False,
                               'networkAllowedByThisBinding': False}
        if validation_age >= MIN_TTL:
            return stop('stale', 'metadata-cache-review-required')
        candidate = {'schemaVersion': 'offmenu-owner08-staging-metadata/1',
                     'sourceId': policy['sourceId'], 'releaseId': policy['releaseId'],
                     'countries': policy['countries'], 'dataType': policy['dataType'],
                     'policySha256': sha(canonical(policy)), 'inputBundleSha256': bundle_key,
                     'row': row, 'acceptance': 'NOT_PERFORMED', 'goldAdmission': False,
                     'bodyProcessingAuthorized': False}
        candidate['bindingKey'] = sha(canonical(candidate))
        if len(canonical(candidate)) > MAX_METADATA:
            return stop('malformed', 'metadata-candidate-too-large')
        result.update(status='valid', candidate=candidate)
        result['diagnostics'] = ['explicit-unknown-' + k for k in ('unit', 'basis') if data[k] is None]
        return result
    except (ValueError, TypeError, KeyError, IndexError, OverflowError, RecursionError):
        return stop('malformed', 'binding-metadata-invalid')


def assess_many(items, *, now):
    """Independent per-input diagnostics; one bad/held source never grants another."""
    return [assess(policy, manifest, now=now, metadata=metadata)
            for policy, manifest, metadata in items]


def write_candidate(path, result):
    """Publish only a valid small metadata candidate; identical bytes are a no-op."""
    if result.get('status') != 'valid' or result.get('candidate') is None:
        return 'withheld'
    path = safe_path(path)
    body = canonical(result['candidate'])
    if path.exists():
        previous = load_metadata(path)
        if previous.get('schemaVersion') != 'offmenu-owner08-staging-metadata/1':
            raise RefreshError('binding-output-type-mismatch')
        if canonical(previous) == body:
            return 'no-op'
    atomic_json(path, result['candidate'])
    return 'written'


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    choice = parser.add_mutually_exclusive_group()
    choice.add_argument('--source')
    choice.add_argument('--fixture', action='store_true')
    parser.add_argument('--now', required=True, help='explicit UTC clock')
    parser.add_argument('--output', type=Path, help='small metadata candidate only')
    args = parser.parse_args(argv)
    try:
        if args.fixture:
            fixture = load_metadata(ROOT / 'tests/fixtures/portfolio08-bindings/synthetic.json')
            results = [assess(fixture['policy'], fixture['manifest'],
                              now=args.now, metadata=fixture['metadata'])]
        else:
            selected = policies()
            if args.source:
                selected = [p for p in selected if p['sourceId'] == args.source]
                if not selected:
                    raise RefreshError('portfolio08-source-not-registered')
            # No CLI body/manifest pathname, dynamic URL or policy injection.
            results = assess_many([(p, None, None) for p in selected], now=args.now)
        if args.output:
            if len(results) != 1:
                raise RefreshError('single-binding-output-required')
            results[0]['writeOperation'] = write_candidate(args.output, results[0])
        print(canonical({'results': results, 'countryAcceptance': False}).decode(), end='')
        return 0 if all(r['status'] == 'valid' for r in results) else 2
    except (OSError, ValueError, TypeError) as error:
        # Fixed error class only: do not echo arbitrary local paths or input text.
        print(json.dumps({'status': 'malformed', 'diagnostics': [str(error) if isinstance(error, RefreshError) else 'binding-cli-invalid'],
                          'networkRequests': 0, 'sourceBodiesRead': 0}))
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
