"""Private exact-barcode consumer for an independently qualified native artifact.

Trusted callers select the SourceContract and independent qualification digest.
No source factory, index, normalization, network or public route is installed.
"""
import hashlib
import os
from pathlib import Path
import re
import stat

from .acceptance import SourceContract, MAX_LINE, canonical, contract_fingerprint, fingerprint, _safe
from .core import RefreshError, strict_json


class NativeLookupError(RefreshError):
    pass


def _require(condition, code):
    if not condition:
        raise NativeLookupError('native-lookup-' + code)


def _binding(contract, qualification, expected_sha256):
    _require(isinstance(contract, SourceContract) and contract.source_id in ('off', 'usda-files')
             and contract.output_scope == 'native' and contract.output_visibility == 'private'
             and not contract.holds and type(contract.fixture) is bool
             and {'retain', 'parse', 'transform'} <= contract.required_operations
             and contract.required_operations <= contract.permitted_operations,
             'private-native-contract-required')
    _require(isinstance(qualification, dict), 'qualification-required')
    encoded = canonical(qualification)
    _require(len(encoded) <= 1024 * 1024, 'qualification-bound')
    q = strict_json(encoded)  # Retain a private snapshot, never mutate the receipt.
    _require(isinstance(expected_sha256, str) and re.fullmatch('[a-f0-9]{64}', expected_sha256)
             and q.get('qualificationSha256') == expected_sha256
             and fingerprint({k: v for k, v in q.items() if k != 'qualificationSha256'}) == expected_sha256,
             'qualification-pin-mismatch')
    _require(q.get('schemaVersion') == 'offmenu-source-qualification/1'
             and q.get('qualified') is True and q.get('status') == 'qualified' and q.get('errors') == []
             and q.get('contractSha256') == contract_fingerprint(contract)
             and (q.get('sourceId'), q.get('releaseId'), q.get('scopeId'), q.get('outputScope'), q.get('outputVisibility'))
             == (contract.source_id, contract.release_id, contract.scope_id, 'native', 'private')
             and type(q.get('fixture')) is bool and q['fixture'] == contract.fixture
             and type(q.get('normalizedRecords')) is int
             and q['normalizedRecords'] == contract.expected_records
             and isinstance(q.get('candidateSha256'), str)
             and re.fullmatch('[a-f0-9]{64}', q['candidateSha256']), 'qualification-invalid')
    return q


def _identity(info):
    return (info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns, info.st_ctime_ns)


def lookup_native_barcode(candidate, *, contract, qualification, qualification_sha256,
                          barcode, max_scan_bytes=64 * 1024 * 1024,
                          max_matches=100, max_result_bytes=8 * 1024 * 1024):
    """Scan one selected uncompressed singleton-packet JSONL output, fail closed.

    Select the qualification_sha256 independently in trusted application code;
    receipt fingerprints alone are not permission/authenticity grants. Full exact
    candidate bytes are verified before ANY matches are returned. Runtime57 must
    qualify any real artifact read and full-scan budget. Limits never truncate.
    """
    try:
        return _lookup(candidate, contract, qualification, qualification_sha256, barcode,
                       max_scan_bytes, max_matches, max_result_bytes)
    except NativeLookupError:
        raise
    except Exception:
        raise NativeLookupError('native-lookup-invalid-input') from None


def _lookup(candidate, contract, qualification, expected_sha256, barcode,
            max_scan_bytes, max_matches, max_result_bytes):
    _require(isinstance(barcode, str) and 0 < len(barcode) <= 256, 'barcode-invalid')
    _require(type(max_scan_bytes) is int and 0 < max_scan_bytes <= 1024**4
             and type(max_matches) is int and 0 < max_matches <= 1000
             and type(max_result_bytes) is int and 0 < max_result_bytes <= 64 * 1024 * 1024,
             'limits-invalid')
    q = _binding(contract, qualification, expected_sha256)
    limit = min(max_scan_bytes, contract.max_output_bytes)
    path = _safe(Path(candidate))
    before = path.stat()
    _require(stat.S_ISREG(before.st_mode) and before.st_size <= limit, 'artifact-bound-or-type')
    matches, digest, total, count, response_bytes = [], hashlib.sha256(), 0, 0, 0
    with path.open('rb') as stream:
        _require(_identity(os.fstat(stream.fileno())) == _identity(before), 'artifact-changed')
        while True:
            raw = stream.readline(MAX_LINE + 1)
            if not raw:
                break
            total += len(raw)
            _require(total <= limit and len(raw) <= MAX_LINE and raw.endswith(b'\n'), 'scan-bound-or-line')
            digest.update(raw)
            packet = strict_json(raw)
            _require(isinstance(packet, list) and len(packet) == 1 and isinstance(packet[0], dict), 'packet-invalid')
            row = packet[0]; canonical(row)  # Includes overflow/nonfinite rejection.
            count += 1
            _require(count <= q['normalizedRecords'], 'record-count-mismatch')
            provenance = row.get('provenance')
            _require(isinstance(provenance, dict)
                     and (provenance.get('sourceId'), provenance.get('releaseId'), provenance.get('fetchedAt'))
                     == (contract.source_id, contract.release_id, contract.acquired_at)
                     and provenance.get('visibility') == 'private-candidate', 'record-scope-mismatch')
            if row.get('kind') != 'product':
                continue
            data = row.get('data')
            _require(isinstance(data, dict) and isinstance(data.get('identifiers'), list)
                     and isinstance(row.get('id'), str) and bool(row['id'])
                     and isinstance(provenance.get('recordId'), str) and bool(provenance['recordId']), 'product-invalid')
            ingredients = data.get('ingredientsText')
            _require(ingredients is None or isinstance(ingredients, str), 'ingredients-invalid')
            found = False
            for identifier in data['identifiers']:
                _require(isinstance(identifier, dict), 'identifier-invalid')
                if identifier.get('system') == 'barcode':
                    value = identifier.get('value')
                    _require(isinstance(value, str) and 0 < len(value) <= 256, 'identifier-invalid')
                    found = found or value == barcode  # No strip/cast/check-digit or identity inference.
            if found:
                match = {'nativeProductId': row['id'], 'sourceRecordId': provenance['recordId'],
                         'ingredientsText': ingredients,
                         'ingredientsTextState': ('missing' if 'ingredientsText' not in data
                                                  else 'null' if ingredients is None else 'source-text'),
                         'candidateLine': count, 'record': row}
                response_bytes += len(canonical(match))
                _require(len(matches) < max_matches and response_bytes <= max_result_bytes, 'result-bound')
                matches.append(match)
        _require(_identity(os.fstat(stream.fileno())) == _identity(before), 'artifact-changed')
    _require(_identity(_safe(path).stat()) == _identity(before), 'artifact-changed')
    _require(total == before.st_size and count == q['normalizedRecords']
             and digest.hexdigest() == q['candidateSha256'], 'artifact-pin-or-count-mismatch')
    return {'sourceId': contract.source_id, 'releaseId': contract.release_id, 'scopeId': contract.scope_id,
            'barcode': barcode, 'status': 'matched' if matches else 'no-match', 'matches': matches,
            'candidateSha256': q['candidateSha256'], 'qualificationSha256': expected_sha256,
            'contractSha256': q['contractSha256'], 'fixture': q['fixture'],
            'scannedRecords': count, 'scannedBytes': total, 'visibility': 'private',
            'barcodeAssurance': 'lexical-source-assertion-only',
            'qualificationMeaning': 'Native selected source scope only; lexical source barcode assertion, no GTIN assurance, cross-source identity, ingredient edges or English/gold admission.'}
