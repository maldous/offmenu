"""RW/TH/US/VN metadata bindings; no acquisition, raw reader or admission registry.

The retained catalogue is evidence, not a SourceContract permission constructor.
Only the explicitly authored fixture helper constructs an executable contract.
Real source staging still needs the selected independent binding review/runner.
"""
from copy import deepcopy
from dataclasses import dataclass, replace
import hashlib
import re

from . import acceptance as shared
from .acquisition import MIN_TTL
from .core import strict_json, timestamp
from .field_provenance import datum_pointers, field_origin_errors
from .global_run import POLICIES as FETCH_POLICIES
from .national_tabular import valid_input_name
from .serialization import encode_records

VERSION = 'worker46-source-bindings/1'
MAX_JSON_DEPTH = 64
POLICY = shared.fingerprint({'version': VERSION, 'scope': 'private-source-native',
    'conversion': 'none', 'unknowns': 'explicit-null', 'admission': False})
RW_HEADERS = ('Tab', 'Column', 'description_abstract', 'title', 'Measurement',
    'data_type', 'creator', 'source', 'source date', 'source file', 'identifier',
    'subject', 'subject.agrovoc', 'format', 'language', 'relation', 'coverage',
    'coverage.country', 'rights')
TH_FIELDS = ('sampleCodeLiteral', 'nutrientLabelLiteral', 'unitAndBasisLiteral',
    'sourceCellTextLiteral', 'meanLexeme', 'standardDeviationLexeme',
    'significanceGroupLiteral', 'noteMarkerLiteral')
TH_ROWS = (('Calories', 'Kcal/100 g'), ('Carbohydrate', 'g/100 g'),
    ('Fat', 'g/100 g'), ('Moisture', 'g/100 g'), ('Protein', 'g/100 g'),
    ('Total sugar', 'g/100 g'), ('Sodium', 'mg/kg'))


@dataclass(frozen=True)
class BindingSpec:
    key: str
    country: str
    data_type: str
    source_id: str
    release_id: str
    input_path: str
    input_sha256: str | None
    acquired_at: str | None
    manifest_sha256: str | None
    rights_sha256: str | None
    scope_sha256: str | None
    hold: str | None = None


REVIEW = 'dbc7aee63006bbb70743b37c010e087174c831be2780cf137dd0dbb0ea674f3b'
SPECS = {
    'rw-codebook': BindingSpec('rw-codebook', 'RW', 'dietary-metadata',
        'rw-citizen-h2d3-codebook', 'retained-descriptor-8fe362318e26',
        'source/data_descriptor.csv',
        '8fe362318e26a64f1b7ce93bc3b533d5004d4e204215591c1f4f5dda8db8e169',
        '2026-10-14T22:16:26.306818+00:00',
        'd666810b848e5396fc672773ecdb4178b8fb8f28837f9257c562dab73a711bd4',
        '41e4d909ff06872bebac49d923838c1f2758fd9d500c671697f791da31140bf6', REVIEW),
    'th-table1': BindingSpec('th-table1', 'TH', 'experimental-nutrition-reference',
        'th-peerj-19606-table1', 'peerj-13-e19606-2025-06-27-retained-8a4d551114a3',
        'source/publisher-page.html',
        '8a4d551114a33dbd31cfa434c8a8f251b3ad8213daa7053dbcff7fe6db40e8d7',
        '2026-10-14T22:47:36.140724+00:00',
        '6382f0049d9713883564a5ff2464df20146cbf1d7e1a8173093084b77129c6e1',
        '05055858e163a021f83e0d49e247a9397cf3b92e91ca9ccc237bf979df890cb1', REVIEW),
    'rw-participants': BindingSpec('rw-participants', 'RW', 'participant-dietary',
        'rw-citizen-h2d3-participants', 'unqualified-secondary-use',
        'source/participant-input-not-selected', None, None, None, None, None,
        'participant-privacy-consent-use-held'),
    'rw-recipes': BindingSpec('rw-recipes', 'RW', 'recipes', 'rw-wellspring',
        'undated-retained-ebook', 'source/ebook-not-selected', None, None,
        None, None, None, 'recipe-text-image-use-held'),
    'us-recipes': BindingSpec('us-recipes', 'US', 'recipes', 'us-fns430',
        'may-2013-fns-430', 'source/recipe-input-not-selected', None, None,
        None, None, None, 'publication-credits-use-selector-held'),
    'vn-composition': BindingSpec('vn-composition', 'VN', 'nutrition',
        'vn-food-composition', '2017-catalogue-only',
        'source/primary-input-not-held', None, None, None, None, None),
}


class BindingError(ValueError):
    """Fixed diagnostic; never include source text, paths or exception messages."""


def metadata_template(key, *, validated_at=None):
    """Declared pins only; does not verify bytes or grant source-body access."""
    spec = SPECS[key]
    return {'sourceId': spec.source_id, 'releaseId': spec.release_id,
        'inputPath': spec.input_path, 'inputSha256': spec.input_sha256,
        'originalAcquiredAt': spec.acquired_at, 'validatedAt': validated_at,
        'retainedManifestSha256': spec.manifest_sha256,
        'rightsEvidenceSha256': spec.rights_sha256,
        'scopeEvidenceSha256': spec.scope_sha256, 'activeHolds': []}


def assess_input(key, metadata, *, now):
    """Portfolio metadata preflight, not a cache engine or execution admission.

    Original acquisition age and validation age stay distinct. No fetch policy,
    force switch, clock read, path traversal, source-file or network I/O exists.
    Shared CachedAcquirer owns acquisition; its public-only scope is NOT widened.
    """
    result = {'binding': key, 'status': 'missing-input', 'errors': [],
        'originalAcquisitionAgeSeconds': None, 'validationAgeSeconds': None,
        'minimumReuseSeconds': MIN_TTL, 'networkRequests': 0,
        'cacheIntent': 'no-download', 'realExecutionAuthorized': False,
        'countryComplete': False, 'goldAdmitted': False}
    spec = SPECS.get(key)
    if spec is None:
        result.update(status='malformed-input', errors=['binding-unknown'])
        return result
    if spec.hold:
        result.update(status='held', errors=[spec.hold])
        return result
    if spec.input_sha256 is None:
        result['errors'] = ['qualified-primary-input-not-held']
        return result
    if metadata is None:
        result['errors'] = ['input-metadata-missing']
        return result
    expected = metadata_template(key)
    if not isinstance(metadata, dict) or set(metadata) != set(expected):
        result.update(status='malformed-input', errors=['metadata-shape-invalid'])
        return result
    if not isinstance(metadata['activeHolds'], list) or any(
            not isinstance(x, str) or not x for x in metadata['activeHolds']):
        result.update(status='malformed-input', errors=['hold-metadata-invalid'])
        return result
    if metadata['activeHolds']:
        result.update(status='held', errors=['source-held'])
        return result
    if any(metadata[k] != v for k, v in expected.items()
           if k not in ('validatedAt', 'activeHolds')):
        result.update(status='malformed-input', errors=['retained-binding-pin-mismatch'])
        return result
    if not valid_input_name(metadata['inputPath']):
        result.update(status='malformed-input', errors=['input-name-invalid'])
        return result
    try:
        observed = timestamp(now)
        acquired = timestamp(metadata['originalAcquiredAt'])
        checked = (timestamp(metadata['validatedAt'])
                   if metadata['validatedAt'] is not None else None)
        if acquired > observed or (checked and not acquired <= checked <= observed):
            raise ValueError()
    except (TypeError, ValueError, OverflowError):
        result.update(status='malformed-input', errors=['evidence-time-invalid'])
        return result
    age = int((observed - acquired).total_seconds())
    result['originalAcquisitionAgeSeconds'] = age
    result['validationAgeSeconds'] = (int((observed - checked).total_seconds())
                                     if checked else None)
    if age >= MIN_TTL:
        result.update(status='stale-input', errors=['cache-revalidation-decision-required'],
                      cacheIntent='stale-no-download')
    else:
        result.update(status='ready-for-binding-review', cacheIntent='reuse-retained-no-download')
    return result


def assess_portfolio(metadata_by_key, *, now):
    """Independent fixed-code diagnostics per binding; no source can hide a peer."""
    if not isinstance(metadata_by_key, dict) or set(metadata_by_key) - set(SPECS):
        raise BindingError('portfolio-metadata-shape-invalid')
    return {key: assess_input(key, metadata_by_key.get(key), now=now)
            for key in sorted(SPECS)}


def replay_intent(key, metadata, *, now, previous_identity=None, mode='reuse'):
    """Bind metadata identity/no-op to shared modes, never execute acquisition.

    Validation time and requested mode are excluded from content identity. This
    interface emits an offline intent only: no claim of underlying byte custody.
    A general private-cache planner/runner remains integration00's shared seam.
    """
    result = assess_input(key, metadata, now=now)
    result['identitySha256'] = None
    result['bytesVerifiedByThisPlan'] = False
    if mode not in FETCH_POLICIES:
        result.update(status='malformed-input', errors=['fetch-mode-invalid'])
        return result
    if result['status'] != 'ready-for-binding-review':
        return result
    identity = {k: v for k, v in metadata.items()
                if k not in ('validatedAt', 'activeHolds')}
    result['identitySha256'] = shared.fingerprint({'policy': POLICY, 'input': identity})
    result['cacheIntent'] = ('unchanged-binding-no-op'
                            if previous_identity == result['identitySha256']
                            else 'staging-binding-review-required')
    return result


def _source_origin(spec, record, field):
    return {'kind': 'source', 'sourceId': spec.source_id,
        'releaseId': spec.release_id, 'inputPath': spec.input_path,
        'inputSha256': spec.input_sha256, 'sourceRecordId': record,
        'sourceField': field}


def _bind(spec, records):
    """Thin declarative projection of a reviewed input envelope, no raw parser.

    Real execution is deliberately not registered. This helper is exercised only
    by authored_fixture; the exact real input reader/isolation remains integrator
    selection. Do not copy a national/reference parser to this portfolio module.
    """
    out = []
    for item in records:
        if not isinstance(item, dict) or set(item) != {'sourceRecordId', 'values'}:
            raise BindingError('source-envelope-invalid')
        record, values = item['sourceRecordId'], item['values']
        if not isinstance(record, str) or not isinstance(values, dict):
            raise BindingError('source-envelope-invalid')
        fields = RW_HEADERS if spec.key == 'rw-codebook' else TH_FIELDS
        if set(values) != set(fields) or any(
                not isinstance(v, str) and not (k == 'noteMarkerLiteral' and v is None)
                for k, v in values.items()):
            raise BindingError('source-field-shape-invalid')
        if spec.key == 'rw-codebook':
            if not re.fullmatch(r'codebook-data-record:(?:[1-9]|[1-9][0-9]|10[0-2])', record):
                raise BindingError('codebook-row-selector-invalid')
        elif spec.key == 'th-table1':
            match = re.fullmatch(r'table-1:tr([3-9]):td([2-6])', record)
            if not match:
                raise BindingError('table-cell-selector-invalid')
            row, col = map(int, match.groups())
            if ((values['nutrientLabelLiteral'], values['unitAndBasisLiteral']) != TH_ROWS[row-3]
                    or values['sampleCodeLiteral'] != 'ABCDE'[col-2]):
                raise BindingError('table-row-column-role-mismatch')
            lex = re.fullmatch(r'([\d,]+\.\d+) ± (\d+\.\d+)([a-z]+)(\*\*)?\s*',
                               values['sourceCellTextLiteral'])
            if lex is None or lex.groups() != tuple(values[k] for k in
                    ('meanLexeme', 'standardDeviationLexeme',
                     'significanceGroupLiteral', 'noteMarkerLiteral')):
                raise BindingError('table-cell-lexical-components-mismatch')
        else:
            raise BindingError('source-reader-not-selected')
        data = {'sourceRole': spec.data_type, 'values': deepcopy(values),
                'canonicalId': None, 'wetDryEdibleBasis': None}
        origins = {}
        for pointer in datum_pointers(data):
            if pointer in ('/data/sourceRole', '/data/canonicalId', '/data/wetDryEdibleBasis'):
                origins[pointer] = {'kind': 'constant', 'policySha256': POLICY,
                    'symbol': {'/data/sourceRole': 'source-role',
                        '/data/canonicalId': 'canonical-unknown',
                        '/data/wetDryEdibleBasis': 'basis-not-established'}[pointer]}
                continue
            key = pointer.rsplit('/', 1)[-1].replace('~1', '/').replace('~0', '~')
            if spec.key == 'rw-codebook':
                origins[pointer] = _source_origin(spec, record,
                    f'csv-column:{RW_HEADERS.index(key)+1}:{key}')
            else:
                cell = f'#table-1/tbody/tr:{row-2}/td:{col}'
                if key == 'sampleCodeLiteral':
                    origins[pointer] = _source_origin(spec, 'table-1',
                        f'#table-1/thead/tr:2/th:{col-1}')
                elif key == 'sourceCellTextLiteral':
                    origins[pointer] = _source_origin(spec, record, cell)
                else:
                    source_field = f'#table-1/tbody/tr:{row-2}/td:1'
                    if key not in ('nutrientLabelLiteral', 'unitAndBasisLiteral'):
                        source_field = cell
                    origins[pointer] = {'kind': 'derived', 'policySha256': POLICY,
                        'transform': 'source-lexical-' + key,
                        'inputs': [_source_origin(spec, record, source_field)]}
        out.append({'id': spec.source_id + ':' + record,
            'kind': 'worker46SourceReference', 'schemaVersion': '1.0',
            'data': data, 'provenance': {'sourceId': spec.source_id,
                'releaseId': spec.release_id, 'fetchedAt': spec.acquired_at,
                'fieldOrigins': origins}})
    return out


def _schema(spec):
    fields = RW_HEADERS if spec.key == 'rw-codebook' else TH_FIELDS
    values = {k: {'type': ['string', 'null'] if k == 'noteMarkerLiteral' else 'string'}
              for k in fields}
    return {'type': 'object', 'required': ['id', 'kind', 'schemaVersion', 'data', 'provenance'],
        'additionalProperties': False, 'properties': {
            'id': {'type': 'string', 'minLength': 1},
            'kind': {'const': 'worker46SourceReference'}, 'schemaVersion': {'const': '1.0'},
            'data': {'type': 'object', 'additionalProperties': False,
                'required': ['sourceRole', 'values', 'canonicalId', 'wetDryEdibleBasis'],
                'properties': {'sourceRole': {'const': spec.data_type},
                    'values': {'type': 'object', 'additionalProperties': False,
                               'required': list(fields), 'properties': values},
                    'canonicalId': {'type': 'null'}, 'wetDryEdibleBasis': {'type': 'null'}}},
            'provenance': {'type': 'object'}}}


def authored_fixture(key, records, *, acquired_at='2026-10-14T00:00:00Z'):
    """Build a tiny in-memory fixture and shared qualification descriptor.

    All bytes/rights/count evidence are AUTHOR-FIXTURE scope. Never manufactures
    a real admission, reads a retained file, or authorizes a held source.
    """
    spec = SPECS.get(key)
    if spec is None or key not in ('rw-codebook', 'th-table1') or not records or len(records) > 4:
        raise BindingError('authored-fixture-scope-invalid')
    records = deepcopy(records)
    timestamp(acquired_at)
    payload = shared.canonical({'authoredFixture': True, 'records': records}) + b'\n'
    fixture = replace(spec, source_id='fixture-' + spec.source_id,
        release_id='authored-' + key + '-v1', input_path='authored-input.json',
        input_sha256=hashlib.sha256(payload).hexdigest(), acquired_at=acquired_at)
    rows = _bind(fixture, records)
    raw = encode_records(rows)
    schema = {'worker46SourceReference': _schema(fixture)}
    rights = b'{"scope":"authored fixture only","operations":["retain","parse","transform"]}\n'
    scope = shared.canonical({'authoredFixture': True,
        'expectedIds': [fixture.source_id + ':' + r['sourceRecordId'] for r in records]}) + b'\n'
    contents = {'authored-input.json': payload, 'rights.json': rights, 'scope.json': scope}
    assets = tuple(shared.Asset(n, len(b), hashlib.sha256(b).hexdigest()) for n, b in contents.items())

    def semantics(row):
        errors = field_origin_errors(row, {fixture.input_path: fixture.input_sha256},
                                     policy_pins=(POLICY,))
        try:
            identity = row['id'].removeprefix(fixture.source_id + ':')
            original = next(r for r in records if r['sourceRecordId'] == identity)
            expected = _bind(fixture, [original])[0]
            if row != expected:
                errors.append('portfolio-source-field-fidelity-mismatch')
        except (KeyError, TypeError, StopIteration, BindingError):
            errors.append('portfolio-source-field-fidelity-mismatch')
        return sorted(set(errors))

    contract = shared.SourceContract(source_id=fixture.source_id, release_id=fixture.release_id,
        scope_id='authored-worker46-binding-only', acquired_at=acquired_at,
        inputs=assets, expected_records=len(records),
        expected_ids_sha256=shared.ids_digest([fixture.source_id + ':' + r['sourceRecordId'] for r in records]),
        schemas=schema, schemas_sha256=shared.fingerprint(schema), semantic_validator=semantics,
        policy_sha256=POLICY, rights_evidence=assets[1], scope_evidence=assets[2],
        permitted_operations=frozenset(('retain', 'parse', 'transform')), fixture=True)
    manifest = {'sourceId': fixture.source_id, 'releaseId': fixture.release_id,
        'acquiredAt': acquired_at, 'normalizedRecords': len(records),
        'candidateSha256': hashlib.sha256(raw).hexdigest(), 'candidateBytes': len(raw),
        'inputFiles': [{'path': a.path, 'bytes': a.bytes, 'sha256': a.sha256} for a in assets],
        'rightsEvidenceSha256': assets[1].sha256, 'scopeEvidenceSha256': assets[2].sha256}
    return {'contract': contract, 'contents': contents, 'candidate': raw,
            'manifest': manifest, 'rows': rows}


def _check_json_depth(raw):
    """Bound container nesting before decoding; quoted brackets are literals.

    This lexical guard does not replace strict_json's grammar validation. UTF-8
    continuation bytes cannot alias the ASCII quote, escape or bracket bytes.
    """
    depth = 0
    quoted = escaped = False
    for char in raw:
        if quoted:
            if escaped:
                escaped = False
            elif char == 92:
                escaped = True
            elif char == 34:
                quoted = False
        elif char == 34:
            quoted = True
        elif char in (91, 123):
            depth += 1
            if depth > MAX_JSON_DEPTH:
                raise BindingError('metadata-depth-exceeded')
        elif char in (93, 125):
            depth -= 1
            if depth < 0:
                raise BindingError('metadata-structure-invalid')


def main(argv=None, *, stdin=None, stdout=None):
    """Metadata JSON via stdin only; never accepts raw-source or output paths."""
    import argparse
    import sys
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=('catalog', 'assess'))
    parser.add_argument('--now', help='Explicit UTC evidence time, required for assess')
    args = parser.parse_args(argv)
    stdout = sys.stdout if stdout is None else stdout
    if args.command == 'catalog':
        result = {key: metadata_template(key) for key in sorted(SPECS)}
    else:
        if args.now is None:
            parser.error('assess requires --now')
        stdin = sys.stdin if stdin is None else stdin
        try:
            # Native stdin is bounded before UTF-8 decoding. String streams are
            # supported for embedded callers, with the same encoded-byte limit.
            raw = getattr(stdin, 'buffer', stdin).read(65537)
            encoded = raw.encode('utf-8') if isinstance(raw, str) else raw
            if len(encoded) > 65536:
                raise BindingError('metadata-limit-exceeded')
            _check_json_depth(encoded)
            result = assess_portfolio(strict_json(encoded.decode('utf-8')), now=args.now)
        except (TypeError, ValueError, UnicodeError, RecursionError):
            stdout.write(shared.canonical({'error': 'portfolio-metadata-invalid'}).decode())
            return 2
    stdout.write(shared.canonical(result).decode())
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
