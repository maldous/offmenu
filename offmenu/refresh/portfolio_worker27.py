"""DK/DM/DO/DZ metadata bindings. No payload access or acquisition interface.

`valid` means metadata-ready-for-review, never source or country acceptance.
The checked-in catalog is the contract; request metadata cannot remove its holds.
"""
import argparse
import json
import re
from pathlib import Path, PurePosixPath

from .acquisition import MIN_TTL
from .adapter_mapping import retained_adapters
from .core import RefreshError, canonical, safe_path, sha, strict_json, timestamp
from .field_provenance import field_origin_errors
from ._worker27_catalog import load_catalog

# Review mirror only. Installed default loading uses the inert packaged literal.
CATALOG = Path(__file__).resolve().parents[2] / 'config/portfolios/worker27-staging.json'
MAX_METADATA = 512 * 1024
COUNTRIES = ('DK', 'DM', 'DO', 'DZ')
TYPES = ('ingredients', 'recipes', 'nutrition', 'retailers/providers',
         'prices/baskets', 'dietary references')


def read_metadata(path):
    """Read only the explicitly supplied metadata document; never follow its refs."""
    path = safe_path(path)
    if not path.is_file() or path.stat().st_size > MAX_METADATA:
        raise RefreshError('metadata-missing-or-too-large')
    try:
        value = strict_json(path.read_bytes())
        # Also reject overflow floats such as 1e999 accepted by json.loads.
        canonical(value)
    except (ValueError, UnicodeError, RecursionError) as error:
        raise RefreshError('metadata-json-invalid') from error
    return value


def _digest(value):
    return isinstance(value, str) and re.fullmatch('[0-9a-f]{64}', value) is not None


def _pins(value):
    return (isinstance(value, dict) and bool(value)
            and all(isinstance(p, str) and bool(p) and '\\' not in p
                    and not PurePosixPath(p).is_absolute() and '..' not in p.split('/')
                    and p == PurePosixPath(p).as_posix() and _digest(h)
                    for p, h in value.items()))


def assess_binding(contract, observation, as_of, adapters=None):
    """Pure isolated assessment. Contracts are code-owned, observations untrusted.

    No input bytes, URLs, imports, source paths or field expressions are evaluated.
    Even a complete synthetic observation cannot open a payload route.
    """
    now = timestamp(as_of)
    source = contract['sourceId']
    errors, missing = [], []
    result = {
        'bindingId': contract['bindingId'], 'country': contract['country'],
        'sourceId': source, 'releaseId': contract['releaseId'],
        'types': contract['types'], 'manifest': contract['manifest'],
        'declaredFields': contract['declaredFields'],
        'nativeSemantics': contract['nativeSemantics'],
        'holds': list(contract['holds']),
        'sourceIdentity': sha(canonical({k: contract[k] for k in
             ('bindingId', 'country', 'sourceId', 'releaseId', 'manifest', 'archiveSha256')})),
        'observationEvidenceSha256': None, 'replayIdentity': None,
        'status': 'missing', 'diagnostics': [],
        'cache': {'originalAcquiredAt': None, 'checkedAt': None,
                  'ageSeconds': None, 'policy': 'unknown-age-no-acquisition'},
        'sourceAdmission': False, 'payloadBytesVerified': False,
        'normalizationExecuted': False, 'networkRequests': 0,
        'acceptedRecords': 0,
        'cachePlanner': 'shared-pure-planner-unavailable; age classification only',
    }
    # Gates precede any inspection of observation, and cannot be removed by it.
    if contract['holds']:
        result.update(status='held', diagnostics=['contract-held'])
        return result
    adapters = retained_adapters() if adapters is None else adapters
    adapter = next((a for a in adapters if a['sourceId'] == source
                    and a['releaseId'] == contract['releaseId']), None)
    if adapter is None:
        missing.append('shared-adapter-unavailable')
    result['sharedAdapter'] = ({k: adapter[k] for k in
        ('sourceId', 'releaseId', 'adapterFamily', 'inputFormat') if k in adapter}
        if adapter else None)
    if observation is None:
        result['diagnostics'] = sorted(missing + ['observation-missing'])
        return result
    if not isinstance(observation, dict):
        result.update(status='malformed', diagnostics=['observation-object-required'])
        return result
    # Bind every supplied non-clock declaration, including malformed/extra fields,
    # without following evidence references or exposing their contents. Catalog
    # holds above deliberately leave unassessed observations unfingerprinted.
    try:
        evidence = {k: v for k, v in observation.items()
                    if k not in ('originalAcquiredAt', 'checkedAt')}
        result['observationEvidenceSha256'] = sha(canonical(evidence))
    except (ValueError, TypeError, RecursionError):
        result.update(status='malformed', diagnostics=['observation-json-invalid'])
        return result
    result['replayIdentity'] = sha(canonical({
        'contractSha256': sha(canonical(contract)),
        'observationEvidenceSha256': result['observationEvidenceSha256'],
    }))
    required = {'bindingId', 'country', 'sourceId', 'releaseId', 'manifestSha256',
                'archiveSha256', 'originalAcquiredAt', 'checkedAt', 'inputPins',
                'roles', 'countrySelector', 'rightsEvidence', 'originTemplate'}
    if set(observation) - required:
        errors.append('observation-unknown-fields')
    for key in sorted(required - observation.keys()):
        missing.append('missing-' + key)
    for key in ('bindingId', 'country', 'sourceId', 'releaseId', 'archiveSha256'):
        if key in observation and observation[key] != contract[key]:
            errors.append('identity-' + key + '-mismatch')
    if ('manifestSha256' in observation
            and observation['manifestSha256'] != contract['manifest']['sha256']):
        errors.append('manifest-pin-mismatch')
    pins = observation.get('inputPins')
    if pins is not None and not _pins(pins):
        errors.append('input-pins-invalid')
    if not pins:
        missing.append('exact-input-pins-required')
    roles = observation.get('roles')
    if roles is None:
        missing.append('input-roles-required')
    else:
        if not isinstance(roles, dict) or set(roles) != set(contract['requiredRoles']):
            errors.append('input-role-inventory-mismatch')
        elif not _pins(pins) or any(not isinstance(p, str) or p not in pins
                                    for p in roles.values()):
            errors.append('input-role-pin-missing')
    for key in ('countrySelector', 'rightsEvidence'):
        value = observation.get(key)
        # Evidence pins are declarations for a reviewer, not an approval signal.
        if value is None:
            missing.append(key + '-required')
        elif (not isinstance(value, dict) or set(value) != {'path', 'sha256'}
              or not isinstance(value['path'], str)
              or not _pins({value['path']: value['sha256']})):
            errors.append(key + '-invalid')
    template = observation.get('originTemplate')
    if template is None:
        missing.append('field-origin-template-required')
    elif (not isinstance(template, dict) or not isinstance(template.get('provenance'), dict)
          or not isinstance(template.get('data'), dict)):
        errors.append('field-origin-template-invalid')
    else:
        provenance = template['provenance']
        if provenance.get('sourceId') != source or provenance.get('releaseId') != contract['releaseId']:
            errors.append('field-origin-template-identity-mismatch')
        errors.extend(field_origin_errors(template, pins))
        if set(template.get('data', {})) != set(contract['declaredFields']):
            errors.append('field-template-inventory-mismatch')
    acquired, checked = observation.get('originalAcquiredAt'), observation.get('checkedAt')
    result['cache'].update(originalAcquiredAt=acquired, checkedAt=checked)
    age = None
    if acquired is None:
        missing.append('original-acquisition-time-required')
    else:
        try:
            acquisition_time = timestamp(acquired)
            age = (now - acquisition_time).total_seconds()
            if age < 0:
                errors.append('acquisition-in-future')
            result['cache']['ageSeconds'] = age
        except RefreshError:
            errors.append('original-acquisition-time-invalid')
    if checked is not None:
        try:
            check_time = timestamp(checked)
            if check_time > now or (age is not None and check_time < timestamp(acquired)):
                errors.append('check-time-out-of-order')
        except RefreshError:
            errors.append('check-time-invalid')
    # An observation check can never reset the original acquisition age.
    if age is not None and age >= MIN_TTL:
        result['cache']['policy'] = 'stale-review-only-no-download'
    elif age is not None and age >= 0:
        result['cache']['policy'] = 'reuse-only-zero-download'
    result['diagnostics'] = sorted(set(errors + missing))
    result['status'] = ('malformed' if errors else 'missing' if missing
                        else 'stale' if age >= MIN_TTL else 'valid')
    result['readinessMeaning'] = 'metadata-ready-for-review-only'
    return result


def assess(catalog, request, as_of):
    if not isinstance(request, dict) or set(request) != {'observations'} or not isinstance(request['observations'], list):
        raise RefreshError('request-observations-required')
    observations = request['observations']
    if any(not isinstance(o, dict) or not isinstance(o.get('bindingId'), str) for o in observations):
        raise RefreshError('observation-binding-id-required')
    ids = [o['bindingId'] for o in observations]
    known = {c['bindingId'] for c in catalog['bindings']}
    if len(set(ids)) != len(ids) or not set(ids) <= known:
        raise RefreshError('duplicate-or-unknown-binding-id')
    indexed = {o['bindingId']: o for o in observations}
    adapters = retained_adapters()
    rows = [assess_binding(c, indexed.get(c['bindingId']), as_of, adapters)
            for c in sorted(catalog['bindings'], key=lambda c: c['bindingId'])]
    return {'schemaVersion': 'offmenu-worker27-metadata-bindings/1', 'asOf': as_of,
            'catalogSha256': sha(canonical(catalog)), 'bindings': rows,
            'countryRequirements': catalog['countryRequirements'],
            'wholeCountryComplete': {country: False for country in COUNTRIES},
            'executionAuthorized': False, 'networkRequests': 0, 'acceptedRecords': 0}


def write_report(path, value):
    """Exclusive creation; exact replay is a no-op, any collision is an error."""
    path, raw = safe_path(path), canonical(value)
    try:
        with path.open('xb') as handle:
            handle.write(raw)
    except FileExistsError:
        if not path.is_file() or path.stat().st_size != len(raw) or path.read_bytes() != raw:
            raise RefreshError('report-output-conflict')
        return 'no-op'
    return 'created'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--request', type=Path, required=True, help='Metadata observations JSON only')
    parser.add_argument('--as-of', required=True, help='Explicit UTC assessment time')
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    try:
        result = assess(load_catalog(), read_metadata(args.request), args.as_of)
        outcome = write_report(args.output, result)
        print(json.dumps({'outcome': outcome, 'sha256': sha(canonical(result)),
                          'bindingCount': len(result['bindings'])}, sort_keys=True))
    except (RefreshError, OSError, ValueError, TypeError, RecursionError):
        # Never echo untrusted content, paths or source values in diagnostics.
        print('{"outcome":"error","diagnostic":"metadata-binding-failed"}')
        return 2
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
