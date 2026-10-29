"""NL CP01 reviewed metadata contract; offline only, no source-body operations.

The real contract is descriptive and held against execution. Shared qualification
and acquisition are exercised only with authored fixtures in the focused tests.
"""
import argparse
from dataclasses import asdict
import itertools
import json
import math
import os
from pathlib import Path
import re
import tempfile

from .acceptance import Asset, SourceContract, contract_fingerprint, fingerprint, ids_digest
from .acquisition import MIN_TTL
from .core import RefreshError, canonical, safe_path, sha, strict_json, timestamp
from .portfolio05 import _read_bounded_regular
from .field_provenance import field_origin_errors
from . import nl_cp01_metadata as meta

MAX_METADATA = 65536
MAX_REPORT = 1024 * 1024
VERSION = 'offmenu-nl-cp01-contract/1'
DATA_FIELDS = ('flatIndex', 'unit', 'time', 'unitLabel', 'valueState', 'value',
               'valueLexical', 'valuePresent', 'statusPresent', 'status',
               'valuePointer', 'statusPointer', 'canonicalTargets')
POLICY = fingerprint({'version': VERSION, 'source': meta.SOURCE_SHA256,
                      'selectors': meta.REQUIRED_SELECTORS, 'axes': meta.AXES,
                      'numeric': 'no-conversion-no-imputation',
                      'canonical': False, 'bodyExecution': False,
                      'minimumReuseSeconds': MIN_TTL})


def require(condition, code):
    if not condition:
        raise RefreshError(code)


def metadata_json(raw):
    require(isinstance(raw, bytes) and len(raw) <= MAX_METADATA, 'metadata-byte-bound')
    value = strict_json(raw)
    pending = [(value, 0)]
    while pending:
        node, depth = pending.pop()
        require(depth <= 48, 'metadata-depth-bound')
        children = node.values() if isinstance(node, dict) else node if isinstance(node, list) else ()
        pending.extend((child, depth + 1) for child in children)
    return value


def expected_inventory():
    """Independent Cartesian inventory from pinned metadata, never observations.

    Use dimension strides (not the original selector's recurrence). Unit/time
    codes are identity components, never canonical food IDs or converted units.
    """
    axes = [sorted(meta.AXES[name]['selected'], key=lambda c: c['position'])
            for name in meta.DIMENSION_ORDER]
    require([len(a) for a in axes] == [1, 5, 1, 1, 369], 'selected-axis-count-mismatch')
    strides = [math.prod(meta.SOURCE_SIZES[i + 1:]) for i in range(len(axes))]
    result = []
    for coordinates in itertools.product(*axes):
        codes = dict(zip(meta.DIMENSION_ORDER, (c['code'] for c in coordinates)))
        require(codes['freq'] == 'M' and codes['geo'] == 'NL' and codes['coicop18'] == 'CP01',
                'selected-scope-mismatch')
        flat = sum(c['position'] * stride for c, stride in zip(coordinates, strides))
        result.append({'id': ':'.join((meta.SOURCE_ID, codes['geo'], codes['freq'],
                                     codes['coicop18'], codes['unit'], codes['time'])),
                       'flatIndex': flat, 'unit': codes['unit'], 'time': codes['time']})
    require(len({r['id'] for r in result}) == len(result)
            and len({r['flatIndex'] for r in result}) == len(result), 'expected-inventory-duplicate')
    return result


def semantic_errors(row):
    """Future source-native wrapper checks; cannot establish value/source equality.

    Source value equality requires the separately selected original adapter and
    exact reviewed input; this code never reads that input or accepts the data.
    """
    errors = []
    try:
        inventory = {r['id']: r for r in expected_inventory()}
        expected = inventory.get(row.get('id'))
        data = row['data']
        require(expected is not None and isinstance(data, dict), 'nl-coordinate-invalid')
        require(set(data) == set(DATA_FIELDS), 'nl-field-inventory-mismatch')
        for field in ('flatIndex', 'unit', 'time'):
            require(type(data[field]) is type(expected[field]) and data[field] == expected[field],
                    'nl-coordinate-invalid')
        labels = {x['code']: x['label'] for x in meta.AXES['unit']['selected']}
        require(data['unitLabel'] == labels[data['unit']], 'nl-unit-basis-mismatch')
        state, value = data['valueState'], data['value']
        require(state in ('numeric', 'explicit-null', 'absent'), 'nl-value-state-invalid')
        if state == 'numeric':
            require(type(value) in (int, float) and math.isfinite(value), 'nl-number-invalid')
            lexical = data['valueLexical']
            require(isinstance(lexical, str) and bool(re.fullmatch(
                r'-?(?:0|[1-9][0-9]*)(?:\.[0-9]+)?(?:[eE][+-]?[0-9]+)?', lexical)),
                'nl-number-lexical-invalid')
            require(json.loads(lexical) == value, 'nl-number-lexical-mismatch')
        else:
            require(value is None and data['valueLexical'] is None, 'nl-missing-value-imputed')
        require(type(data['valuePresent']) is bool and data['valuePresent'] == (state != 'absent'),
                'nl-value-presence-mismatch')
        require(type(data['statusPresent']) is bool
                and (data['status'] is None or isinstance(data['status'], str)), 'nl-status-invalid')
        require(data['statusPresent'] or data['status'] is None, 'nl-status-presence-mismatch')
        require(data['valuePointer'] == '/value/' + str(expected['flatIndex'])
                and data['statusPointer'] == '/status/' + str(expected['flatIndex']),
                'nl-sparse-origin-mismatch')
        require(data['canonicalTargets'] is None, 'nl-canonical-inference')
        require(not field_origin_errors(row, {'retained/eurostat.json': meta.SOURCE_SHA256},
                                        policy_pins=(POLICY,)), 'nl-field-origin-invalid')
        provenance = row['provenance']
        require(provenance['sourceId'] == meta.SOURCE_ID
                and provenance['releaseId'] == meta.RELEASE_ID
                and provenance['fetchedAt'] == meta.ACQUIRED_AT, 'nl-provenance-mismatch')
        origins = provenance['fieldOrigins']
        for field, pointer in [('value', data['valuePointer']), ('status', data['statusPointer'])]:
            origin = origins['/data/' + field]
            require(origin.get('kind') == 'source' and origin.get('sourceField') == pointer
                    and origin.get('sourceRecordId') == str(expected['flatIndex']),
                    'nl-source-cell-origin-mismatch')
    except RefreshError as exc:
        errors.append(str(exc))
    except (ValueError, TypeError, KeyError, OverflowError, RecursionError):
        errors.append('nl-record-malformed')
    return errors


def source_contract():
    """Exact real-source contract descriptor, held; not a rights constructor."""
    inventory = expected_inventory()
    schema = {'type': 'object', 'required': ['id', 'kind', 'data', 'provenance'],
              'properties': {'id': {'type': 'string'}, 'kind': {'const': 'hicp-source-observation'},
                             'data': {'type': 'object', 'required': list(DATA_FIELDS),
                                      'properties': {key: {} for key in DATA_FIELDS},
                                      'additionalProperties': False},
                             'provenance': {'type': 'object'}}}
    schemas = {'hicp-source-observation': schema}
    raw = Asset('retained/eurostat.json', meta.SOURCE_BYTES, meta.SOURCE_SHA256)
    rights = Asset('metadata/terms.json', meta.METADATA_ASSETS['terms']['bytes'],
                   meta.METADATA_ASSETS['terms']['sha256'])
    scope = Asset('metadata/selected-scope.json', meta.METADATA_ASSETS['manifest']['bytes'],
                  meta.METADATA_ASSETS['manifest']['sha256'])
    return SourceContract(meta.SOURCE_ID, meta.RELEASE_ID, 'CP01-NL-M-source-native',
                          meta.ACQUIRED_AT, (raw, rights, scope), 1845,
                          ids_digest(r['id'] for r in inventory), schemas, fingerprint(schemas),
                          semantic_errors, POLICY, rights, scope,
                          frozenset(('retain', 'parse', 'transform')),
                          holds=('real-source-body-execution-not-selected',),
                          output_scope='native', output_visibility='private')


def stable_snapshot():
    contract = source_contract()
    return {'schemaVersion': VERSION, 'sourceId': meta.SOURCE_ID,
            'releaseId': meta.RELEASE_ID, 'sourceSha256': meta.SOURCE_SHA256,
            'originalAcquiredAt': meta.ACQUIRED_AT, 'selectors': meta.REQUIRED_SELECTORS,
            'selectedAxes': meta.AXES, 'sourceSizes': meta.SOURCE_SIZES,
            'expectedRecords': 1845, 'expectedIdsSha256': contract.expected_ids_sha256,
            'reviewedCounts': meta.REVIEWED_COUNTS,
            'reviewedLineage': [5002, 5751, 5903, 6010],
            'contractSha256': contract_fingerprint(contract), 'policySha256': POLICY,
            'metadataPins': meta.METADATA_ASSETS,
            'requiredBodyInputsNotRead': [asdict(a) for a in contract.inputs],
            'sourceProcessingAuthorized': False, 'countryComplete': False, 'goldAdmitted': 0}


def content_key(snapshot):
    # Bind actual owned code plus the exact shared APIs used by this binding.
    # No commit hash/self-reference, clock/mtime or absolute checkout path enters
    # the key; identical reviewed code is stable after commit/integration.
    package = Path(__file__).parent
    dependencies = [Path(__file__), package / 'nl_cp01_metadata.py',
                    package / 'acceptance.py', package / 'acquisition.py',
                    package / 'core.py', package / 'portfolio05.py',
                    package / 'field_provenance.py']
    code = {p.name: sha(_read_bounded_regular(p.absolute(), MAX_REPORT, 'code-identity'))
            for p in dependencies}
    return fingerprint({'contract': snapshot, 'code': code})


def inspect_one(payloads, *, now, previous_key=None, holds=()):
    """Metadata/code-identity inspection; no original/candidate body access."""
    result = {'bindingId': 'nl-cp01', 'status': 'malformed', 'diagnostics': [],
              'sourceBodyOperations': 0, 'networkRequests': 0, 'accepted': False,
              'cache': None, 'contentKey': None, 'unchangedContentNoOp': False}
    try:
        require(isinstance(payloads, dict), 'metadata-inputs-malformed')
        require(isinstance(holds, (tuple, list)) and all(isinstance(h, str) and h for h in holds),
                'holds-malformed')
        if holds:
            result.update(status='held', diagnostics=sorted(set(holds)))
            return result  # Explicit hold precedes parsing/body/code work.
        documents = {}
        for key, spec in meta.METADATA_ASSETS.items():
            raw = payloads.get(key)
            require(raw is not None, 'metadata-input-missing')
            require(isinstance(raw, bytes) and len(raw) == spec['bytes']
                    and sha(raw) == spec['sha256'], 'metadata-pin-mismatch')
            documents[key] = metadata_json(raw)
        manifest = documents['manifest']
        require(manifest['selectedDimensions'] == meta.AXES
                and manifest['dimensionOrder'] == meta.DIMENSION_ORDER
                and manifest['sourceSizes'] == meta.SOURCE_SIZES
                and manifest['sourceSha256'] == meta.SOURCE_SHA256
                and manifest['counts'] == meta.REVIEWED_COUNTS
                and documents['selectors'] == meta.REQUIRED_SELECTORS, 'reviewed-scope-mismatch')
        require(documents['provenance']['originalCaptureUTC'] == meta.ACQUIRED_AT,
                'acquisition-provenance-mismatch')
        require(documents['terms']['Eurostat']['asset']['sha256'] == meta.SOURCE_SHA256,
                'terms-source-mismatch')
        observed = timestamp(now)
        acquired = timestamp(meta.ACQUIRED_AT)
        age = (observed - acquired).total_seconds()
        require(age >= 0, 'acquisition-timestamp-in-future')
        cache = {'minimumReuseSeconds': MIN_TTL, 'minimumReuseDays': MIN_TTL // 86400,
                 'originalAcquiredAt': meta.ACQUIRED_AT, 'acquisitionAgeSeconds': age,
                 'validationAt': now, 'validationResetsAcquisition': False,
                 'mtimeUsed': False, 'bodyCacheVerified': False,
                 'decision': 'reuse-retained-input-policy-only' if age < MIN_TTL
                 else 'conditional-refresh-review-required-no-download',
                 'networkRequests': 0, 'onlineAcquisitionEnabled': False,
                 'sharedInterfaceLimit': 'No generic pure real-source cache planner; CachedAcquirer '
                 'requires body verification and excludes Eurostat query URLs. Never called for this real source.'}
        snapshot = stable_snapshot()
        key = content_key(snapshot)
        if previous_key is not None:
            require(isinstance(previous_key, str) and bool(re.fullmatch('[0-9a-f]{64}', previous_key)),
                    'previous-key-malformed')
        result.update(status='metadata-valid-execution-held', diagnostics=[], cache=cache,
                      contentKey=key, unchangedContentNoOp=key == previous_key,
                      invalidated=previous_key is not None and key != previous_key)
    except (ValueError, TypeError, KeyError, IndexError, OSError, RecursionError, OverflowError) as exc:
        code = str(exc) if isinstance(exc, RefreshError) else 'metadata-malformed'
        result.update(status='missing' if code == 'metadata-input-missing' else 'malformed',
                      diagnostics=[code], contentKey=None)
    return result


def inspect_many(entries, *, now):
    """Authored fixture/embedding entrypoint; one malformed peer stays isolated."""
    require(isinstance(entries, list) and 0 < len(entries) <= 32, 'binding-inventory-invalid')
    results = []
    for index, entry in enumerate(entries):
        if not isinstance(entry, dict):
            results.append({'position': index, 'status': 'malformed',
                            'diagnostics': ['binding-malformed'], 'sourceBodyOperations': 0})
            continue
        result = inspect_one(entry.get('payloads'), now=now,
                             previous_key=entry.get('previousKey'), holds=entry.get('holds', ()))
        result['position'] = index
        results.append(result)
    return results


def read_metadata():
    payloads, diagnostics = {}, {}
    for key, spec in meta.METADATA_ASSETS.items():
        try:
            payloads[key] = _read_bounded_regular(Path(spec['path']), spec['bytes'], 'metadata-input')
        except (OSError, ValueError) as exc:
            diagnostics[key] = str(exc) if isinstance(exc, RefreshError) else 'metadata-file-unavailable'
    return payloads, diagnostics


def write_snapshot(output, snapshot):
    output = Path(output).absolute()
    require(not output.is_relative_to(Path('/home/user/src/offmenu-data')),
            'output-overlaps-source-data')
    output = safe_path(output)
    for spec in meta.METADATA_ASSETS.values():
        protected = Path(spec['path']).absolute()
        require(output != protected and protected.parent not in output.parents,
                'output-overlaps-reviewed-metadata')
    raw = canonical(snapshot)
    if output.exists():
        require(output.stat().st_nlink == 1, 'output-hardlink-rejected')
        if _read_bounded_regular(output, MAX_REPORT, 'output') == raw:
            return 0
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(dir=output.parent, prefix='.nl-cp01-', delete=False) as stream:
            temporary = Path(stream.name)
            stream.write(raw)
        os.replace(temporary, output)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
    return 1


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--now', required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--previous', type=Path)
    args = parser.parse_args()
    try:
        payloads, ingress = read_metadata()
        previous = None
        if args.previous:
            require(not args.previous.absolute().is_relative_to(Path('/home/user/src/offmenu-data')),
                    'previous-overlaps-source-data')
            previous = metadata_json(_read_bounded_regular(args.previous.absolute(), MAX_METADATA, 'previous'))
            require(isinstance(previous, dict) and set(previous) == {'contentKey', 'snapshot'},
                    'previous-report-malformed')
            require(previous['contentKey'] == content_key(previous['snapshot']), 'previous-content-key-mismatch')
        result = inspect_one(payloads, now=args.now,
                             previous_key=previous['contentKey'] if previous else None)
        result['ingressDiagnostics'] = ingress
        require(result['status'] == 'metadata-valid-execution-held', 'metadata-binding-unavailable')
        snapshot = stable_snapshot()
        packet = {'contentKey': result['contentKey'], 'snapshot': snapshot}
        writes = write_snapshot(args.output.absolute(), packet)
        print(json.dumps({'binding': result, 'writes': writes, 'outputSha256': sha(canonical(packet))}, sort_keys=True))
    except (OSError, ValueError, TypeError, KeyError, RecursionError) as exc:
        code = str(exc) if isinstance(exc, RefreshError) else 'binding-ingress-malformed'
        print(json.dumps({'status': 'failed', 'diagnostics': [code],
                          'sourceBodyOperations': 0, 'networkRequests': 0}))
        raise SystemExit(2)


if __name__ == '__main__':
    main()
