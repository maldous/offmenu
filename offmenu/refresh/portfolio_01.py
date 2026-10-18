"""Worker 01 metadata planner and authored CPI fixture adapter. No source I/O.

Retained metadata is evidence, never a grant to process the retained bodies.
Real sources remain held. This module does not register production handlers.
"""
import argparse
from decimal import Decimal, InvalidOperation
import json
import math
import re
import sys

from .acquisition import MIN_TTL
from .core import RefreshError, canonical, sha, strict_json, timestamp
from .field_provenance import field_origin_errors
from .global_run import StageResult
from .serialization import CONTENT_POLICY, encode_records
from .portfolio_01_contract import CONTRACT

VERSION = 'portfolio-01-metadata/1'
FIXTURE_SOURCE = 'authored-portfolio01-cpi'
FIXTURE_RELEASE = 'synthetic-1'
FIXTURE_INPUT = 'authored/cpi.json'
FIXTURE_SHA = sha(canonical({'authored': 'portfolio01-cpi-synthetic-1'}))
SELECTORS = {
    'sheet': 'Table 2.7-4', 'columns': list('DEFGHIJKLMNOPQRS'),
    'yearRow': 9, 'valueRow': 13, 'codeCell': 'B13', 'labelCell': 'C13',
    'definitionCell': 'B6', 'unitCell': 'B7',
}
CONSTANTS = {
    'country': 'AI', 'frequency': 'annual-calendar-year-average',
    'measure': 'consumer-price-index', 'unit': 'index-points',
    'base': 'March 2010 quarter = 100', 'currency': None,
    'physicalQuantity': None, 'currentOffer': False,
    'basketPlanningEligible': False,
}
POLICY_SHA = sha(canonical({'version': VERSION, 'selectors': SELECTORS,
                          'constants': CONSTANTS, 'serialization': CONTENT_POLICY}))
HEX = re.compile('[0-9a-f]{64}')


def _result(status, code, **details):
    return {'schemaVersion': VERSION, **StageResult(status, code).receipt(),
            'sourceProcessingAllowed': False, 'networkAllowed': False,
            'goldAdmitted': False, **details}


def cpi_origins(column, source_id, release_id, input_path, input_sha):
    """Exact retained selector declaration; does not read or interpret a workbook."""
    if column not in SELECTORS['columns']:
        raise RefreshError('portfolio-selector-invalid')
    record_id = f"Table 2.7-4!{column}13"

    def source(cell):
        return {'kind': 'source', 'sourceId': source_id, 'releaseId': release_id,
                'inputPath': input_path, 'inputSha256': input_sha,
                'sourceRecordId': record_id, 'sourceField': f'Table 2.7-4!{cell}'}

    origins = {}
    for name, cell in {'period': column + '9', 'value': column + '13',
                       'originalXMLNumericLexical': column + '13',
                       'publisherGroupCode': 'B13', 'publisherLabel': 'C13'}.items():
        origins['/data/' + name] = source(cell)
    for name in CONSTANTS:
        # Units/basis are interpretations evidenced by B7/B6, not numeric prices.
        if name in ('unit', 'base'):
            origins['/data/' + name] = {
                'kind': 'derived', 'policySha256': POLICY_SHA,
                'transform': 'retained-cpi-unit' if name == 'unit' else 'retained-cpi-basis',
                'inputs': [source('B7' if name == 'unit' else 'B6')]}
        else:
            origins['/data/' + name] = {'kind': 'constant',
                'policySha256': POLICY_SHA, 'symbol': name}
    return origins


def stage_authored_fixture(row):
    """Validate an authored envelope and serialize via shared APIs, fixture only.

    Never pass retained observations here: real source identities are rejected.
    Supplied origins must equal the reviewed declaration, beyond coverage checks.
    """
    try:
        if not isinstance(row, dict) or set(row) != {'id', 'kind', 'schemaVersion', 'data', 'provenance'}:
            raise RefreshError('portfolio-fixture-schema-invalid')
        p, data = row['provenance'], row['data']
        if (not isinstance(p, dict) or set(p) != {'sourceId', 'releaseId', 'fieldOrigins'}
                or p['sourceId'] != FIXTURE_SOURCE or p['releaseId'] != FIXTURE_RELEASE):
            raise RefreshError('portfolio-fixture-identity-invalid')
        if not isinstance(data, dict) or set(data) != set(CONSTANTS) | {
                'period', 'value', 'originalXMLNumericLexical', 'publisherGroupCode', 'publisherLabel'}:
            raise RefreshError('portfolio-fixture-schema-invalid')
        if (row['kind'] != 'synthetic-cpi-observation' or row['schemaVersion'] != VERSION
                or not isinstance(data['period'], str)
                or data['period'] not in [str(y) for y in range(2010, 2026)]):
            raise RefreshError('portfolio-fixture-schema-invalid')
        column = SELECTORS['columns'][int(data['period']) - 2010]
        if row['id'] != f"{FIXTURE_SOURCE}:{data['period']}":
            raise RefreshError('portfolio-fixture-identity-invalid')
        for key, value in CONSTANTS.items():
            if type(data[key]) is not type(value) or data[key] != value:
                raise RefreshError('portfolio-native-unit-basis-or-null-invalid')
        if (type(data['publisherGroupCode']) is not float or data['publisherGroupCode'] != 11.01
                or data['publisherLabel'] != 'Food And Non-Alcoholic Beverages'):
            raise RefreshError('portfolio-publisher-scope-invalid')
        lexical, value = data['originalXMLNumericLexical'], data['value']
        if value is None and lexical is None:
            pass  # Explicit source null, never zero or an imputed value.
        elif (not isinstance(lexical, str) or len(lexical) > 64
                or type(value) not in (int, float) or not math.isfinite(value)
                or not re.fullmatch(r'-?(?:0|[1-9][0-9]*)(?:\.[0-9]+)?(?:[eE][+-]?[0-9]+)?', lexical)
                or not Decimal(lexical).is_finite() or Decimal(lexical) != Decimal(str(value))):
            raise RefreshError('portfolio-numeric-lexical-invalid')
        errors = field_origin_errors(row, {FIXTURE_INPUT: FIXTURE_SHA}, policy_pins=(POLICY_SHA,))
        if errors or p['fieldOrigins'] != cpi_origins(column, FIXTURE_SOURCE, FIXTURE_RELEASE,
                                                   FIXTURE_INPUT, FIXTURE_SHA):
            raise RefreshError('portfolio-field-origin-invalid')
        return encode_records([row])
    except (KeyError, TypeError, InvalidOperation, OverflowError) as error:
        raise RefreshError('portfolio-fixture-schema-invalid') from error


def plan(country, metadata, *, now, previous_key=None, fetch_policy='reuse'):
    """Pure metadata assessment; caller claims cannot open trusted source holds.

    Ages use acquisition and validation separately. Neither validation nor an
    explicit library fetch mode authorizes download through this planner.
    A matching key is only a metadata-plan no-op, never cached-body verification.
    """
    if not isinstance(country, str) or country not in CONTRACT['countries']:
        return _result('unsupported', 'portfolio-country-unsupported')
    declaration = CONTRACT['countries'][country]
    if metadata is None:
        return _result('held', 'portfolio-metadata-missing', country=country,
                       holds=declaration['holds'], cache=None, replay='unassessed')
    try:
        if fetch_policy not in ('reuse', 'refresh', 'revalidate', 'force-download'):
            raise RefreshError('portfolio-fetch-policy-invalid')
        if not isinstance(metadata, dict) or set(metadata) != {
                'receiptPins', 'acquiredAt', 'lastValidatedAt'}:
            raise RefreshError('portfolio-metadata-malformed')
        if metadata['receiptPins'] != declaration['receiptPins']:
            raise RefreshError('portfolio-receipt-pin-mismatch')
        clock = timestamp(now)
        acquired = metadata['acquiredAt']
        if acquired != declaration['acquiredAt']:
            raise RefreshError('portfolio-acquisition-pin-mismatch')
        validated = timestamp(metadata['lastValidatedAt']) if metadata['lastValidatedAt'] is not None else None
        original = timestamp(acquired) if acquired is not None else None
        if ((original is not None and original > clock) or
                (validated is not None and (validated > clock or
                 (original is not None and validated < original)))):
            raise RefreshError('portfolio-clock-invalid')
        if previous_key is not None and (not isinstance(previous_key, str) or not HEX.fullmatch(previous_key)):
            raise RefreshError('portfolio-replay-key-invalid')
        key = sha(canonical({'contract': CONTRACT, 'country': country, 'policySha256': POLICY_SHA}))
        age = (clock - original).total_seconds() if original is not None else None
        cache = {'acquisitionAgeSeconds': age,
                 'validationAgeSeconds': (clock - validated).total_seconds() if validated is not None else None,
                 'minimumReuseSeconds': MIN_TTL, 'bodyVerifiedThisRun': False,
                 'decision': 'acquisition-time-missing' if age is None else
                     ('reuse-window-no-download' if age < MIN_TTL else 'stale-conditional-review-required')}
        return _result('held', 'portfolio-source-use-held', country=country,
                       holds=declaration['holds'], cache=cache, metadataKey=key,
                       replay='metadata-no-op' if key == previous_key else 'metadata-plan-required',
                       requestedFetchPolicy=fetch_policy, sourceRecordsProcessed=0,
                       countryComplete=False, admission='unassessed')
    except RefreshError as error:
        # RefreshError messages from these shared helpers are fixed codes only.
        return _result('quarantined', 'portfolio-metadata-invalid', country=country,
                       diagnostics=[str(error)], cache=None, replay='unassessed')
    except (ValueError, TypeError, OverflowError, RecursionError):
        return _result('quarantined', 'portfolio-metadata-invalid', country=country,
                       diagnostics=['portfolio-metadata-malformed'], cache=None, replay='unassessed')


def plan_portfolio(metadata_by_country, *, now):
    """One malformed country's metadata cannot abort the other three assessments."""
    if not isinstance(metadata_by_country, dict):
        return _result('quarantined', 'portfolio-request-invalid')
    return {country: plan(country, metadata_by_country.get(country), now=now)
            for country in sorted(CONTRACT['countries'])}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--country', required=True, choices=sorted(CONTRACT['countries']))
    parser.add_argument('--now', required=True, help='Explicit UTC assessment time')
    args = parser.parse_args(argv)
    try:
        raw = sys.stdin.buffer.read(65537)
        if len(raw) > 65536:
            raise RefreshError('portfolio-metadata-too-large')
        request = strict_json(raw)
        if not isinstance(request, dict) or set(request) != {'metadata', 'previousKey', 'fetchPolicy'}:
            raise RefreshError('portfolio-request-invalid')
        result = plan(args.country, request['metadata'], now=args.now,
                      previous_key=request['previousKey'], fetch_policy=request['fetchPolicy'])
    except (ValueError, TypeError, UnicodeError, RecursionError):
        result = _result('quarantined', 'portfolio-request-invalid')
    sys.stdout.buffer.write(canonical(result))
    return 0 if result['status'] == 'held' else 2


if __name__ == '__main__':
    raise SystemExit(main())
