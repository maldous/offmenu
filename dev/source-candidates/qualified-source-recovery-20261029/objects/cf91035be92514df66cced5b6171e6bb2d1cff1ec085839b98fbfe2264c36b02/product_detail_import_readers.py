"""Pinned corrected product-detail import closure; no display/query/cache/label API.

Source definitions and schema are preserved verbatim from reviewed63dd92023.
This module provides no real-source factory, admission, job or activation.
"""

from dataclasses import dataclass, asdict
import gzip
import hashlib
import os
from pathlib import Path
import re
import stat
import time
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


@dataclass(frozen=True)
class RetainedProductShard:
    """Trusted application selection, not a licence or qualification factory."""
    release_id: str
    original_sha256: str
    occurrence_sha256: str
    shard_key: str
    sha256: str
    bytes: int
    packets: int
    identity: tuple
    database_sha256: str
    rights_receipt_sha256: str
    custody_receipt_sha256: str
    operation_receipt_sha256: str
    permitted_operations: frozenset
    holds: tuple = ()
    fixture: bool = False


@dataclass(frozen=True)
class RetainedProductLimits:
    max_compressed_bytes: int
    max_expanded_bytes: int
    max_packet_bytes: int
    max_packets: int
    max_result_bytes: int
    max_seconds: int


def _retained_scope(selection, limits):
    valid_sha = lambda value: type(value) is str and re.fullmatch('[a-f0-9]{64}', value)
    _require(type(selection) is RetainedProductShard and type(limits) is RetainedProductLimits,
             'retained-selection-required')
    _require(all(type(n) is int and 0 < n < 2**63 for n in asdict(limits).values())
             and limits.max_packet_bytes <= limits.max_expanded_bytes
             and limits.max_packet_bytes <= MAX_LINE
             and limits.max_result_bytes <= 64 * 1024 * 1024, 'retained-limits')
    _require(type(selection.release_id) is str and 0 < len(selection.release_id) <= 256
             and all(valid_sha(getattr(selection, name)) for name in (
                 'original_sha256', 'occurrence_sha256', 'sha256', 'database_sha256',
                 'rights_receipt_sha256', 'custody_receipt_sha256', 'operation_receipt_sha256'))
             and type(selection.shard_key) is str and re.fullmatch('[a-f0-9]{2}', selection.shard_key)
             and type(selection.bytes) is int and 0 < selection.bytes <= limits.max_compressed_bytes
             and type(selection.packets) is int and 0 < selection.packets <= limits.max_packets
             and type(selection.identity) is tuple and len(selection.identity) == 5
             and all(type(n) is int and n >= 0 for n in selection.identity)
             and selection.identity[2] == selection.bytes
             and type(selection.fixture) is bool and type(selection.holds) is tuple
             and not selection.holds and type(selection.permitted_operations) is frozenset
             and {'retain', 'parse', 'transform'} <= selection.permitted_operations,
             'retained-selection-invalid-or-held')


def _retained_packet(packet, selection):
    _require(type(packet) is list and len(packet) == 2
             and all(type(row) is dict for row in packet), 'retained-packet-schema')
    product, profile = packet
    code = product.get('provenance', {}).get('recordId') if type(product.get('provenance')) is dict else None
    _require(type(code) is str and re.fullmatch('[0-9]{4,32}', code)
             and hashlib.sha256(code.encode()).hexdigest()[:2] == selection.shard_key,
             'retained-shard-key')
    ordinal = None
    for row, kind in zip(packet, ('product', 'nutrientProfile')):
        p = row.get('provenance'); data = row.get('data')
        _require(row.get('schemaVersion') == '1.0' and row.get('kind') == kind
                 and row.get('id') == 'off:' + kind + ':' + code
                 and type(row.get('countries')) is list and all(type(c) is str for c in row['countries'])
                 and type(p) is dict and p.get('sourceId') == 'off' and p.get('recordId') == code
                 and p.get('releaseId') == selection.release_id
                 and p.get('archiveSha256') == selection.original_sha256
                 and p.get('transform') == 'offmenu-bulk/1'
                 and type(p.get('sourceRow')) is int and p['sourceRow'] > 0
                 and type(data) is dict,
                 'retained-record-schema-or-provenance')
        if kind == 'product' or 'identifiers' in data:
            _require(data.get('identifiers') == [{'system': 'barcode', 'value': code}], 'retained-product-identifier')
        if ordinal is None: ordinal = p['sourceRow']
        _require(p['sourceRow'] == ordinal, 'retained-profile-occurrence')
    _require(product['data'].get('nutritionId') == profile['id']
             and type(profile['data'].get('basis')) is dict
             and type(profile['data'].get('nutrients')) is dict, 'retained-profile-binding')
    for name in ('name', 'brand', 'ingredientsText', 'nutritionSourceBasis'):
        _require(product['data'].get(name) is None or type(product['data'][name]) is str,
                 'retained-product-field-schema')
    for name in ('names', 'pack', 'rawNutriments'):
        _require(name not in product['data'] or type(product['data'][name]) is dict,
                 'retained-product-field-schema')
    for name in ('allergens', 'traces', 'labels', 'categories', 'origins', 'manufacturingPlaces'):
        _require(name not in product['data'] or (type(product['data'][name]) is list
                 and all(type(v) is str for v in product['data'][name])), 'retained-product-field-schema')
    return code, ordinal


def _scan_retained_off_shard(candidate, selection, limits, on_packet, start):
    path = _safe(Path(candidate)); _require(path.name == selection.shard_key + '.jsonl.gz', 'retained-path')
    before = path.stat()
    _require(stat.S_ISREG(before.st_mode) and _identity(before) == selection.identity, 'retained-custody')
    def guard():
        _require(time.monotonic() - start < limits.max_seconds, 'retained-time-bound')
    seen = set(); expanded = 0; packets = 0
    digest = hashlib.sha256(); consumed = [0]
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    with os.fdopen(fd, 'rb', buffering=0) as raw:
        _require(_identity(os.fstat(raw.fileno())) == selection.identity, 'retained-custody')
        class Reader:
            def read(self, size=-1):
                guard()
                block = raw.read(min(65536, selection.bytes - consumed[0] + 1, size if size >= 0 else 65536))
                consumed[0] += len(block); digest.update(block)
                _require(consumed[0] <= selection.bytes, 'retained-compressed-bound')
                return block
        reader = Reader()
        with gzip.GzipFile(fileobj=reader, mode='rb') as stream:
            while True:
                guard(); line = stream.readline(limits.max_packet_bytes + 1)
                if not line: break
                expanded += len(line); packets += 1
                _require(len(line) <= limits.max_packet_bytes and line.endswith(b'\n')
                         and expanded <= limits.max_expanded_bytes and packets <= selection.packets,
                         'retained-packet-or-expanded-bound')
                packet = strict_json(line.decode('utf-8')); canonical(packet)
                code, ordinal = _retained_packet(packet, selection)
                _require(code not in seen, 'retained-duplicate-native-key'); seen.add(code)
                on_packet(packet, packets, code, ordinal)  # Provisional until the final checks below.
        _require(reader.read(1) == b'' and consumed[0] == selection.bytes
                 and digest.hexdigest() == selection.sha256 and packets == selection.packets,
                 'retained-hash-or-count')
        _require(_identity(os.fstat(raw.fileno())) == selection.identity, 'retained-custody')
    _require(_identity(_safe(path).stat()) == selection.identity, 'retained-custody'); guard()
    return {'assetSha256': selection.sha256, 'scannedBytes': consumed[0], 'expandedBytes': expanded,
            'scannedPackets': packets, 'scannedRecords': packets * 2, 'fixture': selection.fixture}


def scan_retained_off_product_shard(candidate, *, selection, limits, on_packet):
    """Stream ALL pairs provisionally into caller's uncommitted private stage.

    A callback is not a qualified result. Commit/publish only after this returns
    the full hash/CRC/EOF/custody receipt; roll back on ANY failure. No real factory.
    """
    callback_error = None
    def forward_packet(*args):
        nonlocal callback_error
        try:
            return on_packet(*args)
        except Exception as error:
            callback_error = error
            raise
    try:
        _retained_scope(selection, limits); _require(callable(on_packet), 'retained-sink')
        result = _scan_retained_off_shard(candidate, selection, limits, forward_packet, time.monotonic())
        return {**result, 'scannedProducts': result['scannedPackets'], 'scannedProfiles': result['scannedPackets'],
                'EOFFullyVerified': True, 'bodyPasses': 1, 'sourceId': 'off', 'releaseId': selection.release_id,
                'originalSha256': selection.original_sha256, 'identifierAssetSha256': selection.occurrence_sha256}
    except NativeLookupError:
        raise
    except Exception as error:
        if error is callback_error: raise
        raise NativeLookupError('native-lookup-retained-invalid-input') from None


@dataclass(frozen=True)
class NativeProductScanLimits:
    max_input_bytes: int
    max_records: int
    max_packet_bytes: int
    max_seconds: int


def scan_qualified_native_product_pairs(candidate, *, contract, qualification, qualification_sha256,
                                        identity, limits, on_pair):
    """One selected USDA candidate pass; pairs are provisional until final receipt.

    Reuses the existing native qualification binding. Does not re-open source
    archives/staging, re-run qualification, publish, or collect all rows in RAM.
    """
    callback_error = None
    try:
        q = _binding(contract, qualification, qualification_sha256)
        _require(contract.source_id == 'usda-files' and type(limits) is NativeProductScanLimits
                 and all(type(v) is int and 0 < v < 2**63 for v in asdict(limits).values())
                 and limits.max_packet_bytes <= MAX_LINE and contract.expected_records % 2 == 0
                 and contract.expected_records <= limits.max_records and callable(on_pair)
                 and type(identity) is tuple and len(identity) == 5
                 and all(type(n) is int and n >= 0 for n in identity), 'native-pair-selection')
        path = _safe(Path(candidate)); before = path.stat()
        _require(stat.S_ISREG(before.st_mode) and _identity(before) == identity
                 and before.st_size <= min(limits.max_input_bytes, contract.max_output_bytes), 'native-pair-custody-or-bound')
        start = time.monotonic(); total = 0; count = 0; pairs = 0; pending = None; digest = hashlib.sha256()
        def guard():
            _require(time.monotonic() - start < limits.max_seconds, 'native-pair-time-bound')
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
        with os.fdopen(fd, 'rb') as raw:
            _require(_identity(os.fstat(raw.fileno())) == identity, 'native-pair-custody')
            while True:
                guard(); line = raw.readline(limits.max_packet_bytes + 1)
                if not line: break
                total += len(line); count += 1; digest.update(line)
                _require(total <= before.st_size and len(line) <= limits.max_packet_bytes
                         and line.endswith(b'\n') and count <= contract.expected_records, 'native-pair-input-bound')
                packet = strict_json(line.decode('utf-8'))
                _require(type(packet) is list and len(packet) == 1 and type(packet[0]) is dict, 'native-pair-packet')
                row = packet[0]; canonical(row); p = row.get('provenance'); data = row.get('data')
                kind = 'product' if count % 2 else 'nutrientProfile'
                _require(row.get('schemaVersion') == '1.0' and row.get('kind') == kind
                         and type(p) is dict and (p.get('sourceId'), p.get('releaseId'), p.get('fetchedAt'))
                         == (contract.source_id, contract.release_id, contract.acquired_at)
                         and p.get('visibility') == 'private-candidate'
                         and type(p.get('recordId')) is str and bool(p['recordId'])
                         and row.get('id') == 'usda-files:' + kind + ':' + p['recordId']
                         and type(data) is dict and type(data.get('identifiers')) is list
                         and type(row.get('countries')) is list, 'native-pair-record-binding')
                if kind == 'product':
                    pending = row
                else:
                    _require(pending is not None and pending['data'].get('nutritionId') == row['id']
                             and pending['provenance']['recordId'] == p['recordId']
                             and pending['data']['identifiers'] == data['identifiers']
                             and type(data.get('basis')) is dict and type(data.get('nutrients')) is dict,
                             'native-pair-profile-binding')
                    try:
                        on_pair([pending, row], count - 1, count)
                    except Exception as error:
                        callback_error = error
                        raise
                    pending = None; pairs += 1
            _require(total == before.st_size and count == contract.expected_records and pending is None
                     and digest.hexdigest() == q['candidateSha256'], 'native-pair-hash-or-count')
            _require(_identity(os.fstat(raw.fileno())) == identity, 'native-pair-custody')
        _require(_identity(_safe(path).stat()) == identity, 'native-pair-custody'); guard()
        evidence_paths = {contract.rights_evidence.path, contract.scope_evidence.path}
        if contract.clock_evidence is not None:
            evidence_paths.add(contract.clock_evidence.path)
        return {'assetSha256': q['candidateSha256'], 'scannedBytes': total, 'scannedRecords': count,
                'scannedProducts': pairs, 'scannedProfiles': pairs, 'EOFFullyVerified': True,
                'bodyPasses': 1, 'qualificationSha256': qualification_sha256, 'fixture': q['fixture'],
                'sourceId': contract.source_id, 'releaseId': contract.release_id,
                'originalAssetSHA256s': [a.sha256 for a in contract.inputs if a.path not in evidence_paths],
                'identifierAssetSha256': q['candidateSha256']}
    except NativeLookupError:
        raise
    except Exception as error:
        if error is callback_error: raise
        raise NativeLookupError('native-lookup-native-pair-invalid-input') from None
