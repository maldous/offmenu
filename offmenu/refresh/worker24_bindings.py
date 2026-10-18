"""PF/SL/TF/UY metadata binding only; never opens source/candidate paths.

Shared validators remain authoritative. No source engines, network clients,
SourceContracts, acceptance receipts or automatic refresh jobs are installed.
"""
import argparse
from copy import deepcopy
from pathlib import Path
import re

from .core import RefreshError, canonical, sha, strict_json, timestamp
from .field_provenance import field_origin_errors

CONFIG = Path(__file__).resolve().parents[2] / 'docs/operations/worker24/bindings.json'
COUNTRIES = {'PF', 'SL', 'TF', 'UY'}


def origin_template(profile, input_path, record_id):
    """Declare lexical cell origins; coordinate/value checking remains external.

    Only headers already evidenced in retained metadata are selectors. Numeric
    units, nutrient mappings, market availability and source joins are absent.
    """
    asset = next(x for x in profile['inputs'] if x['path'] == input_path)
    return {
        '/data/cells/' + str(i): {
            'kind': 'source', 'sourceId': profile['sourceId'],
            'releaseId': asset['releaseId'], 'inputPath': input_path,
            'inputSha256': asset['sha256'], 'sourceRecordId': record_id,
            'sourceField': header,
        } for i, header in enumerate(asset['headers'])
    }


def authored_row_errors(profile, input_path, row):
    """Shared structural provenance validator for authored fixtures only.

    Does not validate any actual source value or establish an acceptance scope.
    """
    asset = next(x for x in profile['inputs'] if x['path'] == input_path)
    errors = field_origin_errors(row, {input_path: asset['sha256']})
    cells = row.get('data', {}).get('cells')
    if (not isinstance(cells, list) or len(cells) != len(asset['headers'])
            or any(not isinstance(cell, str) for cell in cells)):
        errors.append('lexical-shape-invalid')
    provenance = row.get('provenance', {})
    if (provenance.get('sourceId') != profile['sourceId']
            or provenance.get('releaseId') != asset['releaseId']):
        errors.append('binding-release-mismatch')
    for i, header in enumerate(asset['headers']):
        origin = provenance.get('fieldOrigins', {}).get('/data/cells/' + str(i), {})
        if origin.get('sourceField') != header:
            errors.append('binding-selector-mismatch')
    return sorted(set(errors))


def _profile_plan(profile, now):
    if not isinstance(profile, dict) or profile.get('country') not in COUNTRIES:
        raise RefreshError('invalid-portfolio-country')
    if not isinstance(profile.get('holds'), list):
        raise RefreshError('invalid-holds')
    # Explicit holds dominate all possible input/cache evidence.
    if profile['holds']:
        return 'held', sorted(profile['holds']), None
    if not profile.get('sourceId') or not profile.get('releaseId'):
        return 'missing', ['source-release-required'], None
    inputs = profile.get('inputs')
    if not isinstance(inputs, list) or not inputs:
        return 'missing', ['retained-input-pins-required'], None
    names = set()
    for asset in inputs:
        name = asset['path']
        if (not isinstance(name, str) or '/' in name or '\\' in name
                or name in ('', '.', '..') or name in names):
            raise RefreshError('invalid-input-path')
        names.add(name)
        if (not isinstance(asset['sha256'], str)
                or not re.fullmatch('[0-9a-f]{64}', asset['sha256'])
                or type(asset['bytes']) is not int or asset['bytes'] < 0
                or not isinstance(asset['releaseId'], str) or not asset['releaseId']
                or not isinstance(asset['headers'], list) or not asset['headers']
                or any(not isinstance(h, str) or not h for h in asset['headers'])):
            raise RefreshError('invalid-input-metadata')
    acquisition = profile['acquisition']
    if acquisition.get('originalAcquiredAt') is None:
        return 'missing', ['original-acquisition-evidence-required'], None
    acquired = timestamp(acquisition['originalAcquiredAt'])
    if acquired > now:
        raise RefreshError('acquisition-in-future')
    validated = acquisition.get('lastValidatedAt')
    if validated is not None and not acquired <= timestamp(validated) <= now:
        raise RefreshError('invalid-validation-time')
    age = int((now - acquired).total_seconds() // 86400)
    return ('reuse-metadata-only' if age < 30 else 'stale-review-required'), [], age


def plan(document, *, now, previous_key=None):
    """Isolate metadata diagnostics by country; deterministic and zero-download.

    Content identity excludes observation clocks. Revalidation cannot reset the
    original acquisition age. Stale metadata requests review, never a download.
    A no-op refers solely to unchanged binding metadata, not payload validation.
    """
    if document.get('schemaVersion') != 'offmenu-worker24-binding/1':
        raise RefreshError('unsupported-binding-version')
    clock = timestamp(now)
    content = deepcopy(document)
    for p in content['profiles']:
        if isinstance(p, dict):
            p.pop('acquisition', None)
    key = sha(canonical(content))
    results = []
    seen = set()
    for index, profile in enumerate(document['profiles']):
        country = profile.get('country') if isinstance(profile, dict) else None
        try:
            if country in seen:
                raise RefreshError('duplicate-country-binding')
            seen.add(country)
            status, diagnostics, age = _profile_plan(profile, clock)
        except (KeyError, TypeError, ValueError, AttributeError) as exc:
            status, age = 'malformed', None
            diagnostics = [str(exc) if isinstance(exc, RefreshError) else 'invalid-binding-metadata']
        results.append({'index': index, 'country': country, 'status': status,
                        'diagnostics': diagnostics, 'acquisitionAgeDays': age})
    return {'schemaVersion': 'offmenu-worker24-binding-plan/1',
            'contentKey': key, 'metadataNoOp': previous_key == key,
            'profiles': results, 'missingCountries': sorted(COUNTRIES - seen),
            'networkRequests': 0, 'sourceBodiesRead': 0,
            'candidateBodiesRead': 0, 'payloadBytesVerified': False,
            'acceptedRecords': 0, 'countryAcceptance': False,
            'minimumReuseDays': 30, 'nextOnlineStep': 'none'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--now', required=True, help='Explicit UTC observation timestamp')
    parser.add_argument('--previous-key')
    args = parser.parse_args()
    # Fixed committed metadata only. Paths embedded in it are never followed.
    document = strict_json(CONFIG.read_bytes())
    print(canonical(plan(document, now=args.now, previous_key=args.previous_key)).decode(), end='')


if __name__ == '__main__':
    main()
