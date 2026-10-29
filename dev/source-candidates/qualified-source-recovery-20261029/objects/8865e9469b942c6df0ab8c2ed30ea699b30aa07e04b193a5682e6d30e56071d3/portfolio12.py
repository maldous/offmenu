"""Worker12 portfolio metadata preflight; no source IO or acquisition interface.

Use shared acceptance/field-origin validation for separately reviewed candidates.
This module cannot create a SourceContract, activate rights, or accept a dataset.
Observed evidence is caller-supplied metadata bytes, never original source bytes.
"""
import argparse
import hashlib
import json
import re

from .acceptance import fingerprint
from .acquisition import MIN_TTL
from .core import strict_json, timestamp
from .field_provenance import field_origin_errors
from .portfolio12_bindings import BINDINGS

COUNTRIES = ('ML', 'MM', 'MN', 'MO')
TYPES = ('ingredients', 'recipes', 'nutrition', 'retailers/providers',
         'prices/baskets', 'dietary references')
POLICY = 'worker12-metadata-binding/1'
MAX_METADATA_BYTES = 2 * 1024**2


def literal_errors(binding, row, input_pins):
    """Shared origin coverage plus declared native unit/basis/coordinate checks.

    Coordinates are declarations: this callback does not compare raw source cells.
    A real SourceContract still needs reviewed source correspondence and scope.
    """
    errors = set(field_origin_errors(row, input_pins))
    if not isinstance(row, dict):
        return sorted(errors | {'portfolio-record-invalid'})
    provenance, data = row.get('provenance'), row.get('data')
    if not isinstance(provenance, dict) or not isinstance(data, dict):
        return sorted(errors | {'portfolio-record-invalid'})
    if (provenance.get('sourceId'), provenance.get('releaseId')) != (
            binding['sourceId'], binding['releaseId']):
        errors.add('portfolio-source-release-mismatch')
    if row.get('kind') != 'sourceLiteral' or row.get('schemaVersion') != '1.0':
        errors.add('portfolio-record-schema-invalid')
    if set(data) != {'text', 'unit', 'basis'} or not isinstance(data.get('text'), str):
        errors.add('portfolio-literal-shape-invalid')
    if data.get('unit') not in binding['units']:
        errors.add('portfolio-native-unit-unreviewed')
    if data.get('basis') not in binding['bases']:
        errors.add('portfolio-basis-unreviewed')
    pattern = binding.get('originPattern')
    origins = provenance.get('fieldOrigins', {})
    if not isinstance(origins, dict):
        origins = {}
    for origin in origins.values():
        if (not isinstance(origin, dict) or origin.get('kind') != 'source'
                or not pattern or not isinstance(origin.get('sourceRecordId'), str)
                or not re.fullmatch(pattern, origin['sourceRecordId'])):
            errors.add('portfolio-selector-unbound')
    return sorted(errors)


def preflight(binding, *, now, observed=None, previous_key=None):
    """Deterministic metadata-only diagnostic; catches malformed siblings alone.

    `observed` maps declared evidence path to its metadata bytes. No paths are
    opened here. Missing/held/malformed/stale outcomes never invoke a downloader.
    Previous keys are hints for repeat planning, not verified acceptance receipts.
    """
    result = {'key': binding.get('key') if isinstance(binding, dict) else None,
              'status': 'malformed', 'diagnostics': [], 'networkRequests': 0,
              'sourceBodiesRead': 0, 'productionAccepted': False,
              'countryComplete': False, 'cacheDecision': 'unavailable',
              'assetBytesVerified': False, 'replay': 'blocked',
              'bindingKey': None, 'validationAgeSeconds': None,
              'acquisitionAgeSeconds': None}
    errors = set()
    try:
        clock = timestamp(now)
        if (binding['country'] not in COUNTRIES
                or any(not isinstance(binding[k], str) or not binding[k]
                       for k in ('key', 'sourceId', 'releaseId'))
                or type(binding['fixture']) is not bool
                or not isinstance(binding['holds'], list)
                or any(not isinstance(x, str) or not x for x in binding['holds'])
                or not binding['types'] or not set(binding['types']) <= set(TYPES)
                or not isinstance(binding['evidence'], list) or not binding['evidence']
                or not isinstance(binding['unknowns'], list)
                or binding['cacheRights'] not in ('unknown', 'fixture-only')):
            raise ValueError()
        # A later metadata validation affects diagnostics, not content identity.
        key = fingerprint({'policy': POLICY,
                           'binding': {k: v for k, v in binding.items() if k != 'validatedAt'}})
        result['bindingKey'] = key
        missing = False
        paths = set()
        for item in binding['evidence']:
            if (not isinstance(item['path'], str) or not item['path']
                    or item['path'] in paths
                    or not re.fullmatch('[0-9a-f]{64}', item['sha256'])
                    or not isinstance(item['selectors'], list)
                    or not item['selectors']
                    or any(not isinstance(s, str) or (s and not s.startswith('/'))
                           for s in item['selectors'])):
                raise ValueError()
            paths.add(item['path'])
            raw = (observed or {}).get(item['path'])
            if raw is None:
                errors.add('metadata-evidence-missing')
                missing = True
            elif not isinstance(raw, bytes) or len(raw) > MAX_METADATA_BYTES:
                errors.add('metadata-evidence-size-or-type-invalid')
            elif hashlib.sha256(raw).hexdigest() != item['sha256']:
                errors.add('metadata-evidence-pin-mismatch')
            else:
                document = strict_json(raw)
                for selector in item['selectors']:
                    value = document
                    try:
                        for token in selector.split('/')[1:]:
                            token = token.replace('~1', '/').replace('~0', '~')
                            if isinstance(value, list):
                                if not re.fullmatch('0|[1-9][0-9]*', token):
                                    raise KeyError()
                                value = value[int(token)]
                            elif isinstance(value, dict):
                                value = value[token]
                            else:
                                raise KeyError()
                    except (KeyError, IndexError):
                        errors.add('metadata-evidence-selector-missing')
        acquired = binding['originalAcquiredAt']
        validated = binding['validatedAt']
        if acquired is None:
            errors.add('original-acquisition-time-unknown')
        else:
            age = (clock - timestamp(acquired)).total_seconds()
            if age < 0:
                raise ValueError()
            result['acquisitionAgeSeconds'] = int(age)
            result['cacheDecision'] = ('recorded-under30d-no-download' if age < MIN_TTL
                                       else 'stale-input-review-no-download')
            if age >= MIN_TTL:
                errors.add('stale-input-review-required')
        if validated is not None:
            age = (clock - timestamp(validated)).total_seconds()
            if age < 0 or (acquired is not None and timestamp(validated) < timestamp(acquired)):
                raise ValueError()
            result['validationAgeSeconds'] = int(age)
        # Later validation never resets original acquisition age. No force mode.
        if binding['cacheRights'] == 'unknown':
            errors.add('cache-retention-scope-unresolved')
        if binding['holds']:
            errors.add('source-held')
        if binding['unknowns']:
            errors.add('binding-fields-unresolved')
        if not binding['fixture']:
            errors.add('real-source-processing-not-selected')
        result['status'] = ('missing' if missing else 'held' if errors else 'fixture-ready')
        if not errors:
            result['replay'] = 'no-op-metadata-plan' if previous_key == key else 'new-metadata-plan'
    except (KeyError, TypeError, ValueError, OverflowError):
        errors.add('portfolio-metadata-malformed')
        result['status'] = 'malformed'
    result['diagnostics'] = sorted(errors)
    return result


def portfolio_report(*, now, bindings=None, observed=None, previous=None):
    """Isolate each source and report all 24 country/type gaps, without admission."""
    bindings = BINDINGS if bindings is None else bindings
    results = [preflight(b, now=now, observed=observed,
                         previous_key=(previous or {}).get(b.get('key'))
                         if isinstance(b, dict) else None) for b in bindings]
    cells = [{'country': country, 'type': kind,
              'bindingKeys': [b['key'] for b in bindings if isinstance(b, dict)
                              and isinstance(b.get('key'), str)
                              and isinstance(b.get('types'), list)
                              and b.get('country') == country and kind in b['types']],
              'accepted': False} for country in COUNTRIES for kind in TYPES]
    return {'schemaVersion': POLICY, 'results': results, 'cells': cells,
            'networkRequests': 0, 'sourceBodiesRead': 0,
            'countryCoverageComplete': False, 'productionAccepted': False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--now', required=True, help='Explicit UTC policy time; no wall-clock or mtime inference')
    args = parser.parse_args()
    print(json.dumps(portfolio_report(now=args.now), sort_keys=True, separators=(',', ':')))


if __name__ == '__main__':
    main()
