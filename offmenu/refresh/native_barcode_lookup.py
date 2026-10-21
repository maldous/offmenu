"""Private exact-barcode consumer for an independently qualified native artifact.

Trusted callers select the SourceContract and independent qualification digest.
No source factory, index, normalization, network or public route is installed.
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


def _retained_selection(selection, observations, limits):
    _retained_scope(selection, limits)
    _require(type(observations) is list and 1 <= len(observations) <= 25,
             'retained-observation-bound')
    _require(len(canonical(observations)) <= limits.max_result_bytes, 'retained-observation-bound')
    selected = {}; keys = set()
    for row in observations:
        _require(type(row) is dict, 'retained-observation')
        ordinal = row.get('record_ordinal'); code = row.get('lexical_value')
        _require(type(ordinal) is int and ordinal > 0
                 and type(code) is str and re.fullmatch('[0-9]{4,32}', code)
                 and row.get('namespace') == 'barcode' and row.get('source_id') == 'off'
                 and row.get('release_id') == selection.release_id
                 and row.get('artifact_sha256') == selection.occurrence_sha256
                 and row.get('input_id') == 'parse-derived:off-occurrences:' + selection.occurrence_sha256
                 and row.get('source_record_id') == str(ordinal)
                 and row.get('native_record_id') == 'off:sourceOccurrence:' + selection.original_sha256 + ':' + str(ordinal)
                 and type(row.get('assertion_id')) is int and row['assertion_id'] > 0
                 and all(type(row.get(k)) is str and 0 < len(row[k]) <= 1024 for k in ('run_id', 'input_id'))
                 and row.get('disposition') in ('source-asserted', 'unresolved')
                 and hashlib.sha256(code.encode()).hexdigest()[:2] == selection.shard_key,
                 'retained-observation-binding')
        key = (row['run_id'], row['input_id'], row['assertion_id'])
        _require(key not in keys, 'retained-duplicate-observation'); keys.add(key)
        selected.setdefault((code, ordinal), []).append(row)
    return selected


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


def _retained_details(row, packet, line, selection):
    key = {name: row[name] for name in ('run_id', 'input_id', 'assertion_id', 'record_ordinal')}
    key['databaseSha256'] = selection.database_sha256
    binding = {'sourceId': 'off', 'releaseId': selection.release_id,
               'originalSha256': selection.original_sha256, 'occurrenceAssetSha256': selection.occurrence_sha256,
               'inputAssetSha256': selection.sha256, 'sourceOccurrence': row['record_ordinal'],
               'recordPointer': 'jsonl:packet:' + str(line) if packet else None,
               'projectionVersion': 'offmenu-bulk/1',
               'rightsReceiptSha256': selection.rights_receipt_sha256,
               'custodyReceiptSha256': selection.custody_receipt_sha256,
               'operationReceiptSha256': selection.operation_receipt_sha256,
               'citationId': row.get('citation_id'),
               'recordSha256': hashlib.sha256(canonical(packet)).hexdigest() if packet else None}
    fields = {}
    mapping = {'name': 'name', 'names': 'names', 'brand': 'brand', 'packageQuantity': 'pack',
               'ingredientDeclaration': 'ingredientsText', 'categories': 'categories',
               'sourceAllergenClaims': 'allergens', 'sourceTraceClaims': 'traces', 'sourceDietaryLabelClaims': 'labels',
               'origins': 'origins', 'manufacturingPlaces': 'manufacturingPlaces',
               'rawNutriments': 'rawNutriments', 'nutritionSourceBasis': 'nutritionSourceBasis'}
    values = [(name, ('product', 'data', source_name)) for name, source_name in mapping.items()]
    values += [('markets', ('product', 'countries')), ('nutrientProfile', ('nutrientProfile', 'data')),
               ('sourceProvenance', ('product', 'provenance'))]
    for name, path in values:
        value = packet[0 if path[0] == 'product' else 1] if packet else None
        present = packet is not None
        for component in path[1:]:
            present = present and type(value) is dict and component in value
            value = value[component] if present else None
        state = ('present' if value is not None else 'null') if present else ('missing' if packet else 'not-loaded')
        fields[name] = {'state': state, 'value': value, 'reasonCode': None if state == 'present' else
                        ('explicit-projected-null' if state == 'null' else 'projection-field-absent' if state == 'missing' else 'exact-occurrence-not-in-selected-representation'),
                        'fieldPointer': '/' + ('0' if path[0] == 'product' else '1') + '/' + '/'.join(path[1:]) if present else None,
                        'evidenceSha256': binding['recordSha256'], 'valueOrigin': 'upstream-projection' if packet else 'unknown',
                        'sourceFieldState': 'unknown', 'language': None}
    fields['imageUrlReferences'] = {'state': 'not-loaded', 'value': None,
        'reasonCode': 'representation-not-provided', 'fieldPointer': None, 'evidenceSha256': None,
        'valueOrigin': 'unknown', 'sourceFieldState': 'unknown', 'language': None}
    return {'observationKey': key, 'sourceObservation': row, 'sourceBinding': binding, 'fields': fields,
            'records': packet, 'canonicalIngredient': {'conceptId': None, 'status': 'unmapped'},
            'assurance': 'retained upstream projection; not original-field presence, canonical identity, dietary certification or gold'}


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
    try:
        _retained_scope(selection, limits); _require(callable(on_packet), 'retained-sink')
        result = _scan_retained_off_shard(candidate, selection, limits, on_packet, time.monotonic())
        return {**result, 'scannedProducts': result['scannedPackets'], 'scannedProfiles': result['scannedPackets'],
                'EOFFullyVerified': True, 'bodyPasses': 1, 'sourceId': 'off', 'releaseId': selection.release_id,
                'originalSha256': selection.original_sha256, 'identifierAssetSha256': selection.occurrence_sha256}
    except NativeLookupError:
        raise
    except Exception:
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
                    on_pair([pending, row], count - 1, count); pending = None; pairs += 1
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
    except Exception:
        raise NativeLookupError('native-lookup-native-pair-invalid-input') from None


def lookup_retained_off_products(candidate, *, selection, observations, limits):
    """Preparation/load-time bounded shard read, NEVER an HTTP per-query scan.

    Caller57 independently selects current rights, custody, exact observed rows,
    held-file identity and runtime bounds. Typed pins are not authorisation.
    No real selection factory, DB open, network or publisher is installed here.
    """
    try:
        selected = _retained_selection(selection, observations, limits)
        start = time.monotonic()
        found = {}; retained_bytes = 0
        def collect(packet, line, code, ordinal):
            nonlocal retained_bytes
            if (code, ordinal) in selected:
                found[(code, ordinal)] = (packet, line)
                retained_bytes += len(canonical(found[(code, ordinal)]))
                _require(retained_bytes <= limits.max_result_bytes, 'retained-result-bound')
        stats = _scan_retained_off_shard(candidate, selection, limits, collect, start)
        products = [_retained_details(row, *found.get((row['lexical_value'], row['record_ordinal']), (None, 0)), selection)
                    for row in observations]
        result = {'version': 'offmenu-retained-off-product-lookup/1', 'sourceProducts': products,
                  **stats,
                  'projectionLimitations': ['name may use English/code fallback; no per-field language inferred',
                     'missing/null/empty source values may have been collapsed upstream',
                     'package quantities/countries/nutrients/bases may be converted, mapped, defaulted or derived upstream',
                     'legacy first-key projection excludes duplicate/quarantine bodies; other observations remain not-loaded',
                     'image references not provided by this projection; no image fetch'],
                  'identifierIndexCompleteMeaning': 'separate from populated product details; no coverage or acceptance implied',
                  'accepted': False, 'publication': 'private caller-owned; no UI/runtime activation'}
        _require(len(canonical(result)) <= limits.max_result_bytes, 'retained-result-bound')
        _require(time.monotonic() - start < limits.max_seconds, 'retained-time-bound')
        return result
    except NativeLookupError:
        raise
    except Exception:
        raise NativeLookupError('native-lookup-retained-invalid-input') from None
