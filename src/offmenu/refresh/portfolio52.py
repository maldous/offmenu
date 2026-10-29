"""Offline MX/SG staging-input proposals; no loader, fetcher or rights constructor.

The catalogue is retained metadata. A plan never verifies body bytes or accepts
data. Callers may validate explicitly supplied observations with the shared
field-origin validator; the production SourceContract remains a separate gate.
"""
import argparse
import copy
from decimal import Decimal, InvalidOperation
import re
import sys

from .acceptance import fingerprint
from .core import RefreshError, canonical, strict_json, timestamp
from .field_provenance import field_origin_errors
from .portfolio52_bindings import BINDINGS

MAX_METADATA_BYTES = 65536
REUSE_SECONDS = 30 * 86400

DECLARATIONS = {
    'MX': {
        'scope': 'source-literal basket classification and expenditure weights',
        'rowSelector': 'Table 1 rows 3..447; header/total rows 1,2,448 excluded from proposed observations',
        'fields': {'labelLiteral': 'xl/worksheets/sheet1.xml!A{row}',
                   'durabilityLiteral': 'xl/worksheets/sheet1.xml!B{row}',
                   'weightLiteral': 'xl/worksheets/sheet1.xml!C{row}'},
        'unit': 'percent', 'basis': 'generic expenditure / total basket expenditure * 100',
        'unitEvidence': 'MX-METHOD section5.1 printedpage29/PDFpage38; B03 terms evidence',
        'unknowns': ['canonical ingredient identity', 'current item price', 'basket quantity'],
    },
    'SG': {
        'scope': 'annual end-of-period counts by establishment type; no entity register',
        'rowSelector': '/result/records/{index0}, index0 0..4; year keys 1993..2025',
        'fields': {'seriesLiteral': '/result/records/{index0}/DataSeries',
                   'yearLiteral': 'object-member-name of /result/records/{index0}/{year}',
                   'valueLiteral': '/result/records/{index0}/{year}'},
        'unit': 'Number', 'basis': 'end-of-period count, not annual flow',
        'unitEvidence': 'Exact dataset catalogue column legend; B03 terms evidence',
        'unknowns': ['na means unavailable versus inapplicable', 'individual establishment identity'],
        'notes': ['2006 category change', '2019 SFA transition/duplicate adjustments',
                  '2020 private markets subsumed; no automatic addition across series'],
    },
    'RS': {'unit': 'kilogram; eggs pieces; sterilised milk liter',
           'basis': 'source min/modal/max market-class prices in literal RSD',
           'unknowns': ['operation-specific derivative scope', 'merchant identity'],
           'fields': {}, 'scope': 'held private price reference'},
    'SS': {'unit': 'index', 'basis': 'June 2011=100, not price or quantity',
           'unknowns': ['authoritative scale erratum', 'numeric-copy permission and NBS credit'],
           'fields': {}, 'scope': 'held inspection metadata only'},
}


def catalogue():
    """Return detached metadata; never follow paths in this document."""
    return copy.deepcopy(BINDINGS)


def observation_policy(country):
    return fingerprint({'version': 'portfolio52-literal-origins/1',
                        'country': country, 'declaration': DECLARATIONS[country]})


def _metadata_errors(country, metadata, now):
    """A caller-supplied metadata document cannot repin release/time/content."""
    if not isinstance(metadata, dict):
        return ['metadata-malformed']
    expected = BINDINGS[country]
    if set(metadata) != set(expected):
        return ['metadata-fields-mismatch']
    # Deliberately compare the complete trusted declaration, including holds,
    # rights evidence, input hashes, inherited counts and acquisition timestamp.
    try:
        if canonical(metadata) != canonical(expected):
            return ['metadata-binding-mismatch']
    except (ValueError, TypeError, RecursionError):
        return ['metadata-malformed']
    try:
        acquired = timestamp(metadata['originalAcquiredAt'])
        validated = timestamp(metadata['lastValidatedAt'])
        current = timestamp(now)
        if not acquired <= validated <= current:
            return ['metadata-time-order-invalid']
    except (RefreshError, TypeError, ValueError):
        return ['metadata-time-invalid']
    return []


def plan(country, metadata, *, now, previous_key=None):
    """Pure bounded metadata plan; no source bytes or files are ever accessed.

    Validation age is diagnostic only. Thirty-day eligibility uses the pinned
    original acquisition, never lastValidatedAt, mtime, caller force or a 304.
    Replay means reusing an unchanged *proposal*, not qualifying cached data.
    """
    out = {'country': country, 'status': 'missing-input', 'errors': [],
           'datasetExecutionAllowed': False, 'accepted': False,
           'networkRequests': 0, 'sourceBytesVerified': False,
           'replay': 'blocked', 'bindingKey': None}
    if country not in BINDINGS:
        return {**out, 'status': 'unsupported', 'errors': ['portfolio-binding-unsupported']}
    if metadata is None:
        return {**out, 'errors': ['metadata-missing']}
    errors = _metadata_errors(country, metadata, now)
    if previous_key is not None and (not isinstance(previous_key, str)
                                   or re.fullmatch('[0-9a-f]{64}', previous_key) is None):
        errors.append('previous-key-invalid')
    if errors:
        return {**out, 'status': 'malformed-input', 'errors': sorted(errors)}
    acquired = timestamp(metadata['originalAcquiredAt'])
    current = timestamp(now)
    age = (current - acquired).total_seconds()
    binding_key = fingerprint({'metadata': {k: v for k, v in metadata.items()
                                           if k != 'lastValidatedAt'},
                               'policySha256': observation_policy(country)})
    out.update(sourceId=metadata['sourceId'], releaseId=metadata['releaseId'],
               bindingKey=binding_key, metadata=copy.deepcopy(metadata),
               declaration=copy.deepcopy(DECLARATIONS[country]),
               originPolicySha256=observation_policy(country),
               cache={'minimumReuseDays': 30,
                      'originalAcquiredAt': metadata['originalAcquiredAt'],
                      'lastValidatedAt': metadata['lastValidatedAt'],
                      'acquisitionAgeDays': int(age // 86400),
                      'validationAgeDays': int((current - timestamp(metadata['lastValidatedAt'])).total_seconds() // 86400),
                      'under30DayReuse': age < REUSE_SECONDS,
                      'revalidationResetsAcquisitionAge': False,
                      'network': 'not implemented; review before any conditional refresh'},
               executionHolds=list(metadata['executionHolds']))
    if metadata['metadataHold']:
        return {**out, 'status': 'held', 'errors': ['source-operation-held']}
    if age >= REUSE_SECONDS:
        return {**out, 'status': 'stale-input', 'errors': ['source-stale-review-required-no-download']}
    return {**out, 'status': 'binding-ready-pending-review',
            'replay': 'no-op' if previous_key == binding_key else 'emit-metadata-proposal'}


def plan_portfolio(inputs, *, now, previous_keys=None):
    """Isolate invalid/missing/held countries; never suppress a peer result."""
    if not isinstance(inputs, dict) or (previous_keys is not None and not isinstance(previous_keys, dict)):
        raise RefreshError('portfolio-input-malformed')
    if set(inputs) - set(BINDINGS) or set(previous_keys or {}) - set(BINDINGS):
        raise RefreshError('portfolio-country-unsupported')
    previous_keys = previous_keys or {}
    return {'schemaVersion': 'offmenu-portfolio52-binding-proposal/1',
            'sources': [plan(c, inputs.get(c), now=now, previous_key=previous_keys.get(c))
                        for c in BINDINGS],
            'productionAcceptance': False, 'countryCoverageComplete': False}


def observation_errors(country, row):
    """Source-specific selector/lexeme hook for a future trusted SourceContract.

    This checks declaration consistency, not equality with source bytes. It must
    be combined with shared qualify() and an independently reviewed projection.
    No source manifest can create a trusted SourceContract using this function.
    """
    if country not in ('MX', 'SG'):
        return ['source-operation-held']
    spec = BINDINGS[country]
    input_name = spec['originalInput']['path'].split('/')[-1]
    if not isinstance(row, dict) or not isinstance(row.get('data'), dict):
        return ['observation-malformed']
    p = row.get('provenance', {})
    if not isinstance(p, dict):
        return ['observation-malformed']
    if any(isinstance(x, (dict, list)) for x in row['data'].values()):
        return ['observation-scalar-required']
    errors = set(field_origin_errors(row, {input_name: spec['originalInput']['sha256']},
                                    policy_pins=(observation_policy(country),)))
    if (row.get('kind') != spec['kind'] or row.get('schemaVersion') != '1.0'
            or row.get('countries') != [country]
            or not isinstance(row.get('id'), str) or not row['id']
            or p.get('sourceId') != spec['sourceId']
            or p.get('releaseId') != spec['releaseId']
            or p.get('fetchedAt') != spec['originalAcquiredAt']
            or p.get('retainedProjection') != spec['retainedArtifacts'][0]):
        errors.add('observation-identity-mismatch')
    data = row['data']
    fields = DECLARATIONS[country]['fields']
    if set(data) != set(fields):
        return sorted(errors | {'observation-fields-mismatch'})
    origins = p.get('fieldOrigins', {})
    if not isinstance(origins, dict):
        return sorted(errors)
    if country == 'MX':
        n = p.get('sourceRow')
        if type(n) is not int or not 3 <= n <= 447:
            return sorted(errors | {'mx-row-selector-invalid'})
        record_id = f'Table 1!row:{n}'
        expected_fields = {key: value.format(row=n) for key, value in fields.items()}
        if not isinstance(data['labelLiteral'], str) or not data['labelLiteral'].strip():
            errors.add('mx-label-invalid')
        if data['durabilityLiteral'] is not None and not isinstance(data['durabilityLiteral'], str):
            errors.add('mx-durability-invalid')
        weight = data['weightLiteral']
        # Null remains structural/unknown; a numeric lexeme is not a canonical value.
        if weight is not None:
            try:
                if (not isinstance(weight, str) or re.fullmatch(r'\d+(?:\.\d+)?', weight) is None
                        or not Decimal(0) <= Decimal(weight) <= Decimal(100)):
                    errors.add('mx-weight-lexeme-invalid')
            except InvalidOperation:
                errors.add('mx-weight-lexeme-invalid')
    else:
        n = p.get('sourceRecordIndex0')
        year = data['yearLiteral']
        if (type(n) is not int or not 0 <= n <= 4 or not isinstance(year, str)
                or re.fullmatch(r'\d{4}', year) is None or not 1993 <= int(year) <= 2025):
            return sorted(errors | {'sg-record-year-selector-invalid'})
        record_id = f'/result/records/{n}'
        expected_fields = {'seriesLiteral': record_id + '/DataSeries',
                           'valueLiteral': record_id + '/' + year}
        if not isinstance(data['seriesLiteral'], str) or not data['seriesLiteral'].strip():
            errors.add('sg-series-invalid')
        value = data['valueLiteral']
        if not isinstance(value, str) or (value != 'na' and re.fullmatch(r'[0-9]+', value) is None):
            errors.add('sg-count-lexeme-invalid')
        # A JSON object member's name is not the source value at that pointer.
        expected_year = {'kind': 'derived', 'policySha256': observation_policy(country),
                         'transform': 'json-object-member-name',
                         'inputs': [{'kind': 'source', 'sourceId': spec['sourceId'],
                                     'releaseId': spec['releaseId'], 'inputPath': input_name,
                                     'inputSha256': spec['originalInput']['sha256'],
                                     'sourceRecordId': record_id,
                                     'sourceField': expected_fields['valueLiteral']}]}
        if origins.get('/data/yearLiteral') != expected_year:
            errors.add('sg-year-key-origin-invalid')
    for key, selector in expected_fields.items():
        expected = {'kind': 'source', 'sourceId': spec['sourceId'],
                    'releaseId': spec['releaseId'], 'inputPath': input_name,
                    'inputSha256': spec['originalInput']['sha256'],
                    'sourceRecordId': record_id, 'sourceField': selector}
        if origins.get('/data/' + key) != expected:
            errors.add('source-selector-mismatch')
    return sorted(errors)


def observation_schema(country):
    """Full private literal-envelope schema for the shared SourceContract API.

    This is reviewed-code proposal material, not a contract constructed from a
    manifest. Independent count/IDs, rights and scope evidence remain required.
    """
    if country not in ('MX', 'SG'):
        raise RefreshError('source-operation-held')
    spec = BINDINGS[country]
    fields = ({'labelLiteral': {'type': 'string', 'minLength': 1},
               'durabilityLiteral': {'type': ['string', 'null']},
               'weightLiteral': {'type': ['string', 'null']}}
              if country == 'MX' else
              {'seriesLiteral': {'type': 'string', 'minLength': 1},
               'yearLiteral': {'type': 'string', 'pattern': '^(199[3-9]|20[01][0-9]|202[0-5])$'},
               'valueLiteral': {'type': 'string', 'pattern': '^(na|[0-9]+)$'}})
    return {'type': 'object', 'additionalProperties': False,
            'required': ['id', 'schemaVersion', 'kind', 'countries', 'provenance', 'data'],
            'properties': {'id': {'type': 'string', 'minLength': 1},
                'schemaVersion': {'const': '1.0'}, 'kind': {'const': spec['kind']},
                'countries': {'const': [country]},
                'data': {'type': 'object', 'additionalProperties': False,
                         'required': list(fields), 'properties': fields},
                'provenance': {'type': 'object', 'additionalProperties': False,
                    'required': ['sourceId', 'releaseId', 'fetchedAt', 'fieldOrigins', 'retainedProjection',
                                 *(['sourceRow', 'sourceRole'] if country == 'MX' else ['sourceRecordIndex0'])],
                    'properties': {'sourceId': {'const': spec['sourceId']},
                                   'releaseId': {'const': spec['releaseId']},
                                   'fetchedAt': {'const': spec['originalAcquiredAt']},
                                   'retainedProjection': {'const': spec['retainedArtifacts'][0]},
                                   **({'sourceRow': {'type': 'integer', 'minimum': 3, 'maximum': 447},
                                       'sourceRole': {'enum': ['source-item', 'source-classification-group']}}
                                      if country == 'MX' else
                                      {'sourceRecordIndex0': {'type': 'integer', 'minimum': 0, 'maximum': 4}}),
                                   'fieldOrigins': {'type': 'object'}}}}}


def bind_literal(country, literal):
    """Pure projection of an explicitly supplied, previously parsed literal.

    Does not load the retained file, parse originals or verify claim bytes. The
    shared qualifier must later check both originals and the retained projection
    under independent rights/scope/count/ID contracts. This API grants none.
    """
    if country not in ('MX', 'SG'):
        raise RefreshError('source-operation-held')
    spec = BINDINGS[country]
    if (not isinstance(literal, dict) or literal.get('country') != country
            or literal.get('lineage') != spec['originalInput']):
        raise RefreshError('literal-source-binding-mismatch')
    input_name = spec['originalInput']['path'].split('/')[-1]
    if country == 'MX':
        n = literal.get('sourceRow')
        if (literal.get('schema') != 'offmenu-source-literal-row/1'
                or literal.get('worksheet') != 'Table 1'
                or literal.get('worksheetPart') != 'xl/worksheets/sheet1.xml'
                or literal.get('sourceRole') not in ('source-item', 'source-classification-group')
                or type(n) is not int or not 3 <= n <= 447):
            raise RefreshError('mx-literal-selector-invalid')
        cells = literal.get('cells')
        if not isinstance(cells, list) or any(not isinstance(c, dict) for c in cells):
            raise RefreshError('mx-literal-cells-invalid')
        selected = {}
        for col in ('A', 'B', 'C'):
            found = [c for c in cells if c.get('address') == f'{col}{n}']
            if len(found) != 1 or 'textLiteral' not in found[0] or found[0].get('formulaLiteral') is not None:
                raise RefreshError('mx-literal-cells-invalid')
            selected[col] = found[0]['textLiteral']
        data = dict(zip(('labelLiteral', 'durabilityLiteral', 'weightLiteral'),
                        (selected['A'], selected['B'], selected['C'])))
        record_id = f'Table 1!row:{n}'
        selectors = {k: v.format(row=n) for k, v in DECLARATIONS[country]['fields'].items()}
        coordinate = {'sourceRow': n, 'sourceRole': literal['sourceRole']}
    else:
        pointer = literal.get('sourcePointer')
        match = re.fullmatch(r'/result/records/([0-4])/(199[3-9]|20[01][0-9]|202[0-5])', pointer or '') if isinstance(pointer, str) else None
        if (literal.get('schema') != 'offmenu-source-aggregate-observation/1'
                or literal.get('datasetId') != 'd_a9e81ab29216b10b69e23e7957b680b9'
                or literal.get('sourceRole') != 'aggregate-establishment-type-count'
                or not match or literal.get('yearLiteral') != match[2]):
            raise RefreshError('sg-literal-selector-invalid')
        data = {k: literal.get(v) for k, v in
                [('seriesLiteral', 'sourceSeriesLiteral'), ('yearLiteral', 'yearLiteral'), ('valueLiteral', 'valueLiteral')]}
        record_id = '/result/records/' + match[1]
        selectors = {'seriesLiteral': record_id + '/DataSeries', 'valueLiteral': pointer}
        coordinate = {'sourceRecordIndex0': int(match[1])}
    origins = {'/data/' + key: {'kind': 'source', 'sourceId': spec['sourceId'],
                'releaseId': spec['releaseId'], 'inputPath': input_name,
                'inputSha256': spec['originalInput']['sha256'],
                'sourceRecordId': record_id, 'sourceField': selector}
               for key, selector in selectors.items()}
    if country == 'SG':
        origins['/data/yearLiteral'] = {'kind': 'derived', 'policySha256': observation_policy(country),
            'transform': 'json-object-member-name', 'inputs': [dict(origins['/data/valueLiteral'])]}
    row = {'id': spec['sourceId'] + ':' + record_id + (':' + data['yearLiteral'] if country == 'SG' else ''),
           'schemaVersion': '1.0', 'kind': spec['kind'], 'countries': [country],
           'provenance': {'sourceId': spec['sourceId'], 'releaseId': spec['releaseId'],
                          'fetchedAt': spec['originalAcquiredAt'], 'fieldOrigins': origins,
                          'retainedProjection': copy.deepcopy(spec['retainedArtifacts'][0]), **coordinate},
           'data': data}
    if observation_errors(country, row):
        raise RefreshError('literal-semantics-invalid')
    return row


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--now', required=True, help='explicit UTC diagnostic time')
    parser.add_argument('--stdin', action='store_true', help='bounded metadata only; never file paths to load')
    args = parser.parse_args(argv)
    try:
        packet = {'inputs': catalogue()}
        if args.stdin:
            raw = sys.stdin.buffer.read(MAX_METADATA_BYTES + 1)
            if len(raw) > MAX_METADATA_BYTES:
                raise RefreshError('metadata-input-limit')
            packet = strict_json(raw)
            if (not isinstance(packet, dict) or not set(packet) <= {'inputs', 'previousKeys'}
                    or 'inputs' not in packet):
                raise RefreshError('portfolio-packet-invalid')
        result = plan_portfolio(packet['inputs'], now=args.now, previous_keys=packet.get('previousKeys'))
        sys.stdout.buffer.write(canonical(result))
        return 0 if all(s['status'] == 'binding-ready-pending-review' for s in result['sources']) else 2
    except (RefreshError, ValueError, TypeError, UnicodeError, RecursionError):
        sys.stdout.buffer.write(canonical({'status': 'malformed-input', 'errors': ['metadata-packet-invalid']}))
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
