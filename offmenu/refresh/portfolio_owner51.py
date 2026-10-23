"""Owner51 metadata binding and offline authored-fixture qualification.

No production reader, acquisition hook or acceptance entrypoint is exposed.
Real portfolio pins are documentary; they cannot become trusted SourceContracts.
"""
import argparse
import copy
import json
import os
from pathlib import Path
import stat
import tempfile

from .acceptance import Asset, SourceContract, fingerprint, ids_digest, qualify
from .acquisition import MIN_TTL
from .core import RefreshError, canonical, safe_path, strict_json, timestamp
from .field_provenance import datum_pointers, field_origin_errors
from .serialization import asset, encode_records

ACQUIRED = '2026-10-01T00:00:00Z'
SOURCE = 'owner51-authored-fixture'
RELEASE = 'synthetic-v1'
ASSETS = (
    Asset('input.json', 335, 'ef0e47e4ad63990af36a1fa98e8b4e2ea0fc2fb98abeff06436fe094b9100d20'),
    Asset('rights.json', 142, '9355bfb58f3893ded77e205b166311ec47c872bf0ec56094c2cb76fd2c4c35f8'),
    Asset('scope.json', 117, '737f6a25355edfa3e4549f46d074cdc0b54ae61b994599d26923600a0a6e269f'),
)
IDS = ('fixture-home:a', 'fixture-lunch:b')
POLICY = {'scope': 'authored-fixture-only', 'transform': 'literal-cell-copy-v1',
          'currency': 'preserve-explicit-null', 'basis': 'monthly-reference-cost',
          'minimumReuseSeconds': MIN_TTL, 'acquisition': 'unavailable'}
POLICY_SHA = fingerprint(POLICY)


def cache_diagnostic(original_acquired_at, now, validated_at=None):
    """Age derives solely from acquisition. Validation does not extend reuse.

    At the 30-day boundary revalidation needs separately authorized action;
    this function never refreshes or grants permission to read an input.
    """
    try:
        acquired, current = timestamp(original_acquired_at), timestamp(now)
        validated = timestamp(validated_at) if validated_at is not None else None
        if current < acquired or (validated is not None and not acquired <= validated <= current):
            return {'status': 'held', 'errors': ['clock-order-invalid']}
        age = (current - acquired).total_seconds()
        return {'status': 'reuse-window' if age < MIN_TTL else 'revalidation-required',
                'originalAcquiredAt': original_acquired_at, 'ageSeconds': age,
                'minimumReuseSeconds': MIN_TTL, 'networkEnabled': False,
                'errors': [] if age < MIN_TTL else ['cache-stale']}
    except (TypeError, ValueError, OverflowError):
        return {'status': 'held', 'errors': ['timestamp-invalid']}


def _source_origin(record_id, field):
    return {'kind': 'source', 'sourceId': SOURCE, 'releaseId': RELEASE,
            'inputPath': ASSETS[0].path, 'inputSha256': ASSETS[0].sha256,
            'sourceRecordId': record_id, 'sourceField': field}


def _row(cell, index):
    data = {key: cell[key] for key in ('scenario', 'age', 'valueLiteral',
                                      'periodLiteral', 'currencyLiteral', 'currencyISO')}
    origins = {pointer: _source_origin(cell['id'], '/cells/' + str(index) + pointer[5:])
               for pointer in datum_pointers(data)}
    return {'id': cell['id'], 'kind': 'referenceCost', 'schemaVersion': 'owner51-fixture/1',
            'data': data, 'provenance': {'sourceId': SOURCE, 'releaseId': RELEASE,
                                       'fetchedAt': ACQUIRED, 'fieldOrigins': origins}}


EXPECTED_CELLS = (
    {'id': IDS[0], 'scenario': 'fixture-home', 'age': 'A', 'valueLiteral': '1 234',
     'periodLiteral': 'per månad', 'currencyLiteral': None, 'currencyISO': None},
    {'id': IDS[1], 'scenario': 'fixture-lunch', 'age': 'B', 'valueLiteral': '567',
     'periodLiteral': 'per månad', 'currencyLiteral': None, 'currencyISO': None},
)
EXPECTED_ROWS = tuple(_row(cell, i) for i, cell in enumerate(EXPECTED_CELLS))


def semantics(row):
    errors = field_origin_errors(row, {a.path: a.sha256 for a in ASSETS})
    expected = next((r for r in EXPECTED_ROWS if r['id'] == row.get('id')), None)
    if row != expected:
        errors.append('fixture-value-or-origin-mismatch')
    return sorted(set(errors))


SCHEMAS = {'referenceCost': {'type': 'object', 'additionalProperties': False,
    'required': ['id', 'kind', 'schemaVersion', 'data', 'provenance'],
    'properties': {'id': {'enum': list(IDS)}, 'kind': {'const': 'referenceCost'},
                   'schemaVersion': {'const': 'owner51-fixture/1'},
                   'data': {'type': 'object'}, 'provenance': {'type': 'object'}}}}


def fixture_contract():
    """Code-owned fixture inventory; no caller-supplied rights or schema factory."""
    return SourceContract(SOURCE, RELEASE, 'authored-two-cell-fixture', ACQUIRED,
        ASSETS, 2, ids_digest(IDS), copy.deepcopy(SCHEMAS), fingerprint(SCHEMAS), semantics,
        POLICY_SHA, ASSETS[1], ASSETS[2], frozenset(('retain', 'parse', 'transform')),
        fixture=True, max_input_bytes=4096, max_output_bytes=32768, max_records=2)


def _read_regular(path, max_bytes):
    """Bounded bytes from one nonblocking descriptor; refuse changed paths.

    Walk directories without following links. Parsing and hashing both consume
    these returned bytes, never a second path open. This is a local reader for
    authored fixture ingress, not a production acquisition or shared API.
    """
    path = Path(os.path.abspath(path))
    flags = os.O_RDONLY | os.O_NONBLOCK | os.O_NOFOLLOW
    directory = os.open(path.anchor, flags | os.O_DIRECTORY)
    signature = lambda s: (s.st_dev, s.st_ino, s.st_mode, s.st_size,
                           s.st_mtime_ns, s.st_ctime_ns)
    try:
        for component in path.parts[1:-1]:
            child = os.open(component, flags | os.O_DIRECTORY, dir_fd=directory)
            os.close(directory)
            directory = child
        named = os.stat(path.name, dir_fd=directory, follow_symlinks=False)
        if not stat.S_ISREG(named.st_mode):
            raise RefreshError('regular-file-required')
        descriptor = os.open(path.name, flags, dir_fd=directory)
        try:
            before = os.fstat(descriptor)
            if not stat.S_ISREG(before.st_mode) or signature(named) != signature(before):
                raise RefreshError('input-replaced')
            if before.st_size > max_bytes:
                raise RefreshError('asset-size-limit-exceeded')
            raw = os.read(descriptor, max_bytes + 1)
            after = os.fstat(descriptor)
            current = os.stat(path.name, dir_fd=directory, follow_symlinks=False)
            # Also detect an ancestor replaced while our directory handle stayed open.
            live = safe_path(path).stat(follow_symlinks=False)
            if (len(raw) != before.st_size or len(raw) > max_bytes
                    or any(signature(s) != signature(before) for s in (after, current, live))):
                raise RefreshError('input-changed-during-read')
            return raw
        finally:
            os.close(descriptor)
    finally:
        os.close(directory)


def run_fixture(bundle, *, now, held=False, validated_at=None):
    """Return fixture candidate bytes and shared qualification, or fixed diagnostics.

    Held/stale paths are rejected before opening any bundle component. Outputs
    are returned to the caller; failed qualification yields no candidate bytes.
    """
    result = {'fixture': True, 'productionAccepted': False, 'countryCoverageComplete': False,
              'goldAdmitted': False, 'status': 'held', 'errors': []}
    if held:
        return {**result, 'errors': ['source-use-held']}, None
    lifecycle = cache_diagnostic(ACQUIRED, now, validated_at)
    if lifecycle['errors']:
        return {**result, 'errors': lifecycle['errors'], 'lifecycle': lifecycle}, None
    try:
        root = safe_path(bundle)
        bodies = {}
        for pin in ASSETS:
            raw = _read_regular(root / pin.path, 4096)
            if asset(raw) != {'bytes': pin.bytes, 'sha256': pin.sha256}:
                return {**result, 'errors': ['input-pin-mismatch']}, None
            bodies[pin.path] = raw
        packet = strict_json(bodies['input.json'])
        if packet != {'fixture': True, 'cells': list(EXPECTED_CELLS)}:
            return {**result, 'errors': ['fixture-shape-invalid']}, None
        rows = [_row(cell, i) for i, cell in enumerate(packet['cells'])]
        raw = encode_records(rows)
        contract = fixture_contract()
        manifest = {'sourceId': SOURCE, 'releaseId': RELEASE, 'acquiredAt': ACQUIRED,
                    'normalizedRecords': len(rows), 'candidateBytes': len(raw),
                    'candidateSha256': asset(raw)['sha256'],
                    'rightsEvidenceSha256': ASSETS[1].sha256,
                    'scopeEvidenceSha256': ASSETS[2].sha256,
                    'inputFiles': [vars(a) for a in ASSETS]}
        with tempfile.TemporaryDirectory(prefix='owner51-fixture-') as directory:
            candidate = Path(directory) / 'candidate.jsonl'
            candidate.write_bytes(raw)
            qualification = qualify(contract, root, candidate, manifest)
        result.update(status='fixture-qualified' if qualification['qualified'] else 'held',
                      errors=qualification['errors'], lifecycle=lifecycle,
                      qualification=qualification, manifest=manifest)
        return result, raw if qualification['qualified'] else None
    except FileNotFoundError:
        return {**result, 'errors': ['input-missing']}, None
    except (OSError, ValueError, KeyError, TypeError):
        return {**result, 'errors': ['input-invalid']}, None


def diagnose_many(bundles, *, now):
    """Independent diagnostics; one held or malformed fixture does not hide peers."""
    return {key: run_fixture(path, now=now)[0] for key, path in sorted(bundles.items())}


def write_fixture_output(path, raw):
    """Create an exclusive fixture output or preserve an identical existing file.

    No overwrite, parent creation, persistent lock or acceptance side effect.
    """
    target = safe_path(path)
    try:
        with target.open('xb') as stream:
            stream.write(raw)
        return 'created'
    except FileExistsError:
        previous = _read_regular(target, len(raw))
        if previous == raw:
            return 'no-op'
        raise RefreshError('output-conflict')


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    subs = parser.add_subparsers(dest='command', required=True)
    subs.add_parser('describe')
    fixture = subs.add_parser('fixture')
    fixture.add_argument('--bundle', type=Path, required=True)
    fixture.add_argument('--as-of', required=True)
    fixture.add_argument('--output', type=Path)
    args = parser.parse_args(argv)
    if args.command == 'describe':
        metadata = Path(__file__).with_name('portfolio_owner51.json')
        print(json.dumps(strict_json(metadata.read_bytes()), ensure_ascii=False, indent=2))
        return 0
    result, raw = run_fixture(args.bundle, now=args.as_of)
    if raw is not None and args.output:
        try:
            result['write'] = write_fixture_output(args.output, raw)
        except (OSError, ValueError):
            result.update(status='held', errors=['output-conflict-or-invalid'])
    print(canonical(result).decode(), end='')
    return 0 if result['status'] == 'fixture-qualified' else 1


if __name__ == '__main__':
    raise SystemExit(main())
