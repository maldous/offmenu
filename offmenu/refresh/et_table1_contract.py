"""ET Table1 literal-grid contract and offline authored-fixture qualification.

Never reads historical bodies or their derived rows. The CLI reads only a small
request declaration, generates authored fixture inputs, and uses shared qualify.
No fixture pass admits the retained ET source or resets its acquisition clock.
"""
import argparse
import json
import os
from pathlib import Path
import tempfile

from .acceptance import (Asset, SourceContract, contract_fingerprint, fingerprint,
                         ids_digest, qualify)
from .core import (RefreshError, atomic_json, canonical, code_identity, safe_path,
                   sha, strict_json, timestamp, fsync_directory)
from .et_table1_declaration import DECLARATION
from .field_provenance import datum_pointers, field_origin_errors
from .portfolio_w07 import bounded_declaration, read_metadata
from .serialization import asset, encode_records

FIXTURE_SOURCE = 'offmenu-authored-et-table1'
FIXTURE_RELEASE = 'literal-grid-fixture-v1'
# Explicit authored scenario timestamp, NOT publisher acquisition evidence.
FIXTURE_ACQUIRED = '2000-01-01T00:00:00+00:00'
POLICY = {'version': 'et-table1-literal-grid-fixture/2', 'rows': 32, 'columns': 5,
          'headers': 5, 'dashes': 24, 'blanks': [[25, 5], [32, 5]],
          'nativeUnit': None, 'nativeBasis': 'label-profile',
          'role': 'source-label-product-sample-profiles', 'numericCoercion': False}
POLICY_PIN = sha(canonical(POLICY))
PLANNER_DEPENDENCY = {
    'commit': 'd5147b2713abfe0c87332ab3ee692b33a80a05b1',
    'moduleSha256': 'ba47921d80d3cc43afe109d10f24db6d196f97231d50ad423505ed32f62e8f9e',
    'independentReviewSha256': '8195e32bb1c6b016892d1fedeeed231bf168a0c0415df1d37223532b7d572d4a',
}
SELECTOR = 'physical-page7/table1/rows1-32/columns1-5/headers'


def expected_ids():
    return tuple(DECLARATION['grid']['expectedIds'] +
                 [r['id'] for r in DECLARATION['linkedRegions']])


def authored_input():
    """Synthetic strings and placements; never a copy of accepted Table1 rows."""
    cells = []
    for row in range(33):
        for col in range(1, 6):
            identity = f'p7/table1/r{row:02d}/c{col:02d}'
            literal = ('' if [row, col] in POLICY['blanks'] else
                       '-' if 1 <= row <= 24 and col == 4 else
                       '0' if (row, col) == (1, 1) else f'AUTHORED r{row} c{col}')
            cells.append({'id': identity, 'kind': 'etLiteralCell', 'data': {
                'physicalPage': 7, 'row': row, 'column': col,
                'literal': literal, 'cellRole': 'header' if row == 0 else 'data',
                'lexicalState': 'blank' if literal == '' else
                    'dash' if literal == '-' else 'text',
                'nativeUnit': None, 'nativeBasis': 'label-profile',
                'role': 'source-label-product-sample-profiles'}})
    for region in DECLARATION['linkedRegions']:
        cells.append({'id': region['id'], 'kind': 'etLinkedRegion', 'data': {
            'physicalPage': region['page'], 'role': region['role'],
            'literal': 'AUTHORED linked region ' + region['role'],
            'metadataPointer': region['metadataPointer'],
            'nativeUnit': None, 'nativeBasis': 'label-profile'}})
    return {'fixture': True, 'sourceId': FIXTURE_SOURCE, 'records': cells,
            'notice': 'Synthetic grid: dash placement is authored, not retained source positions.'}


def fixture_assets():
    return {'authored-grid.json': canonical(authored_input()),
            'fixture-rights.json': canonical({'fixtureOnly': True,
                'operations': ['retain', 'parse', 'transform'],
                'grant': 'OffMenu authored fixture only; no publisher/source permission'}),
            'fixture-scope.json': canonical({'fixtureOnly': True,
                'expectedIds': list(expected_ids()), 'retainedMetadata': DECLARATION})}


def fixture_rows():
    pins = asset(fixture_assets()['authored-grid.json'])
    rows = []
    for index, entry in enumerate(authored_input()['records']):
        rows.append({**entry, 'schemaVersion': 'offmenu-et-table1-fixture/1',
            'provenance': {'sourceId': FIXTURE_SOURCE, 'releaseId': FIXTURE_RELEASE,
                'fetchedAt': FIXTURE_ACQUIRED,
                'fieldOrigins': {pointer: {'kind': 'source', 'sourceId': FIXTURE_SOURCE,
                    'releaseId': FIXTURE_RELEASE, 'inputPath': 'authored-grid.json',
                    'inputSha256': pins['sha256'], 'sourceRecordId': entry['id'],
                    'sourceField': f'/records/{index}' + pointer}
                    for pointer in datum_pointers(entry['data'])}}})
    return rows


def source_contract(*, holds=()):
    """Trusted fixture-only factory; no CLI contract/plugin/source substitution."""
    blobs = fixture_assets()
    assets = tuple(Asset(name, len(raw), sha(raw)) for name, raw in sorted(blobs.items()))
    by_name = {a.path: a for a in assets}
    expected = {r['id']: r for r in fixture_rows()}
    pins = {'authored-grid.json': by_name['authored-grid.json'].sha256}

    def semantic(row):
        errors = set(field_origin_errors(row, pins))
        wanted = expected.get(row.get('id'))
        if wanted is None:
            errors.add('et-coordinate-id-invalid')
        else:
            if row.get('kind') != wanted['kind'] or canonical(row.get('data')) != canonical(wanted['data']):
                errors.add('et-literal-coordinate-role-mismatch')
            if row.get('provenance') != wanted['provenance']:
                errors.add('et-exact-field-origin-mismatch')
        return sorted(errors)

    def schema(kind):
        return {'type': 'object', 'additionalProperties': False,
                'required': ['id', 'kind', 'schemaVersion', 'data', 'provenance'],
                'properties': {'id': {'type': 'string', 'enum': list(expected_ids())},
                    'kind': {'const': kind},
                    'schemaVersion': {'const': 'offmenu-et-table1-fixture/1'},
                    'data': {'type': 'object'}, 'provenance': {'type': 'object'}}}

    schemas = {kind: schema(kind) for kind in ('etLiteralCell', 'etLinkedRegion')}
    return SourceContract(FIXTURE_SOURCE, FIXTURE_RELEASE, 'et-table1-authored-grid-only',
        FIXTURE_ACQUIRED, assets, len(expected_ids()), ids_digest(expected_ids()),
        schemas, fingerprint(schemas), semantic, POLICY_PIN,
        by_name['fixture-rights.json'], by_name['fixture-scope.json'],
        frozenset(('retain', 'parse', 'transform')), holds=tuple(holds), fixture=True,
        max_input_bytes=256 * 1024, max_output_bytes=1024 * 1024, max_records=169)


def qualify_fixture(rows=None, *, holds=(), corrupt_input=False):
    """Shared full-record qualification on generated authored temporary assets only."""
    contract = source_contract(holds=holds)
    rows = fixture_rows() if rows is None else rows
    candidate = encode_records(rows)
    manifest = {'sourceId': contract.source_id, 'releaseId': contract.release_id,
        'acquiredAt': contract.acquired_at, 'normalizedRecords': contract.expected_records,
        'candidateBytes': len(candidate), 'candidateSha256': sha(candidate),
        'inputFiles': [vars(a) for a in contract.inputs],
        'rightsEvidenceSha256': contract.rights_evidence.sha256,
        'scopeEvidenceSha256': contract.scope_evidence.sha256}
    with tempfile.TemporaryDirectory(prefix='offmenu-et-authored-') as temporary:
        root = Path(temporary); bundle = root / 'bundle'; bundle.mkdir()
        for name, raw in fixture_assets().items():
            (bundle / name).write_bytes(raw + (b' ' if corrupt_input and name == 'authored-grid.json' else b''))
        output = root / 'candidate.jsonl'; output.write_bytes(candidate)
        return qualify(contract, bundle, output, manifest, scratch_root=root)


def default_case(key='et-table1'):
    return {'key': key, 'sourceSha256': DECLARATION['sourceDeclaredSha256'],
            'selector': SELECTOR, 'role': POLICY['role'], 'nativeUnit': None,
            'nativeBasis': 'label-profile', 'rightsScope': 'private-attributed-research-only',
            'expectedIdsSha256': ids_digest(expected_ids()),
            'originalAcquiredAt': DECLARATION['originalAcquisition']['value'],
            'validationAt': None, 'previousKey': None, 'holds': []}


def assess_case(case, *, as_of, qualification=None):
    """Small source declaration/fixture result; never a source-processing grant."""
    key = case.get('key') if isinstance(case, dict) else None
    result = {'key': key if isinstance(key, str) and len(key) <= 256 else None,
              'status': 'malformed', 'diagnostics': [], 'fixtureQualified': False,
              'cacheKey': None, 'cacheIdentity': None}
    try:
        bounded_declaration(case)
        if (not isinstance(case, dict) or not isinstance(case.get('key'), str)
                or not case['key'] or len(case['key']) > 256):
            raise RefreshError('et-case-invalid')
        wanted = default_case(case['key'])
        if set(case) - set(wanted):
            raise RefreshError('et-case-fields-invalid')
        holds = case.get('holds')
        if not isinstance(holds, list) or any(not isinstance(h, str) or not h for h in holds):
            raise RefreshError('et-holds-invalid')
        result['holds'] = sorted(set(holds))
        if holds:
            result.update(status='held', diagnostics=['et-source-held'])
            return result
        errors = []
        for key in ('sourceSha256', 'selector', 'role', 'nativeUnit', 'nativeBasis',
                    'rightsScope', 'expectedIdsSha256'):
            if key not in case:
                errors.append('et-missing-' + key.lower())
            elif case[key] != wanted[key]:
                errors.append('et-invalid-' + key.lower())
        # Original source clock comes only from exact retained acquisition metadata.
        acquired = case.get('originalAcquiredAt')
        if acquired is None:
            errors.append('et-original-acquisition-missing')
        else:
            try:
                original = timestamp(acquired); now = timestamp(as_of)
                if original > now:
                    errors.append('et-acquisition-in-future')
                if original != timestamp(wanted['originalAcquiredAt']):
                    errors.append('et-original-acquisition-binding-mismatch')
                checked = case.get('validationAt')
                if checked is not None and not original <= timestamp(checked) <= now:
                    errors.append('et-validation-time-out-of-order')
            except RefreshError:
                errors.append('et-clock-invalid')
        result['diagnostics'] = sorted(errors)
        result['declarationEvidenceSha256'] = sha(canonical({k: v for k, v in case.items()
            if k not in ('validationAt', 'previousKey')}))
        if errors:
            return result
        checked = qualification if qualification is not None else qualify_fixture()
        result.update(status='qualified-authored-fixture' if checked['qualified'] else 'held',
            diagnostics=checked['errors'], fixtureQualified=checked['qualified'],
            qualificationSha256=checked['qualificationSha256'])
        return result
    except (RefreshError, ValueError, TypeError, RecursionError):
        result['diagnostics'] = ['et-case-invalid']
        return result


def cache_plan(case, *, as_of, code_fingerprint):
    """Call the centrally owned neutral API; no local fallback policy engine."""
    try:
        from .retained_policy import plan_retained_input
    except ImportError as error:
        raise RefreshError('et-shared-retained-planner-unavailable') from error
    return plan_retained_input(
        source_id=DECLARATION['sourceId'], release_id=DECLARATION['releaseId'],
        input_pins={
            'retained-original-declared-only': {
                'sha256': DECLARATION['sourceDeclaredSha256'], 'bytes': 910355},
            'accepted-grid-declared-only': {
                'sha256': DECLARATION['acceptedDerivedCandidateSha256'], 'bytes': 878096},
            'reviewed-manifest-metadata': {
                'sha256': DECLARATION['manifestSha256'], 'bytes': 4432}},
        policy_sha256=sha(canonical({'policy': POLICY_PIN, 'code': code_fingerprint,
                                   'sharedPlanner': PLANNER_DEPENDENCY})),
        scope_sha256=sha(canonical(DECLARATION)),
        original_acquired_at=case.get('originalAcquiredAt'), now=as_of,
        validated_at=case.get('validationAt'), previous_key=case.get('previousKey'),
        holds=case.get('holds', ()))

def assess(request, *, as_of):
    timestamp(as_of)
    if (not isinstance(request, dict) or set(request) != {'schemaVersion', 'cases'}
            or request['schemaVersion'] != 'offmenu-et-table1-fixture-request/1'
            or not isinstance(request['cases'], list) or not 1 <= len(request['cases']) <= 8):
        raise RefreshError('et-request-invalid')
    # Qualification uses only fixed authored inputs, once per bounded request.
    qualification = qualify_fixture()
    code = code_identity()['codeFingerprint']
    rows, observations = [], []
    for case in request['cases']:
        row = assess_case(case, as_of=as_of, qualification=qualification)
        if row['fixtureQualified']:
            try:
                plan = cache_plan(case, as_of=as_of, code_fingerprint=code)
                row['cacheKey'] = plan['key']
                row['cacheIdentity'] = plan['identity']
                observations.append({'key': row['key'], 'asOf': as_of, 'plan': plan})
            except RefreshError as error:
                row.update(status='malformed', fixtureQualified=False,
                           diagnostics=[str(error)])
        rows.append(row)
    keys = [r['key'] for r in rows if r['key'] is not None]
    if len(set(keys)) != len(keys):
        raise RefreshError('et-duplicate-peer-key')
    contract = source_contract()
    return {'schemaVersion': 'offmenu-et-table1-fixture-result/1',
        'retainedDeclaration': DECLARATION, 'contractSha256': contract_fingerprint(contract),
        'codeFingerprint': code, 'policySha256': POLICY_PIN,
        'cases': rows, 'cacheInterface': 'retained_policy.plan_retained_input',
        'sharedPlannerDependency': PLANNER_DEPENDENCY,
        'cacheObservations': observations,
        'sourceBodyOperations': 0, 'networkRequests': 0, 'acceptedSourceRecords': 0,
        'countryComplete': False, 'originalAcquisition': DECLARATION['originalAcquisition']}


def content_receipt(value):
    # Current/validation clocks are observations; immutable content keeps original age evidence.
    return {key: child for key, child in value.items() if key != 'cacheObservations'}


def publish(path, value):
    value = content_receipt(value)
    path = safe_path(path); raw = canonical(value)
    path.parent.mkdir(parents=True, exist_ok=True)
    # Shared atomic JSON writes only a private temporary, then link exclusively.
    # A concurrent report can win creation, but can never be overwritten here.
    with tempfile.TemporaryDirectory(prefix='.et-report-', dir=path.parent) as temporary:
        draft = Path(temporary) / 'receipt.json'
        atomic_json(draft, value)
        try:
            os.link(draft, path)
        except FileExistsError:
            if read_metadata(path, limit=512 * 1024) != raw:
                raise RefreshError('et-output-conflict')
            return 'no-op'
        fsync_directory(path.parent)
    return 'created'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--request', required=True, type=Path)
    parser.add_argument('--as-of', required=True)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    try:
        request = strict_json(read_metadata(args.request, limit=64 * 1024))
        result = assess(request, as_of=args.as_of)
        outcome = publish(args.output, result)
        print(json.dumps({'outcome': outcome, 'sha256': sha(canonical(content_receipt(result))),
            'cacheInterface': result['cacheInterface'], 'cacheObservations': result['cacheObservations'],
            'sourceAdmission': False}, sort_keys=True))
    except (RefreshError, OSError, ValueError, TypeError, RecursionError):
        print('{"outcome":"error","diagnostic":"et-fixture-request-or-output-invalid"}')
        return 2
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
