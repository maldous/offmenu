"""Bounded source-faithful organization import; trusted selection stays external.

No network, public caller, source acquisition, canonical mapping or runtime launcher.
The caller selects custody, operation, schema and OS/output resources independently.
"""
import gzip
import hashlib
import io
import json
import os
from pathlib import Path
import sqlite3
import stat
import tempfile

SCHEMA_SHA256 = '1a0bb6cbec8e1477d8d51cac30bb8cd1c8e100125f56bdb0b82339cb59ba293d'
SOURCE_ID = 'wikidata-food-businesses'
RELEASE_ID = '2026-10-13-direct-types'


class SupplierImportError(Exception):
    def __init__(self, code, receipt):
        super().__init__(code)
        self.receipt = receipt  # Finally closes descriptors and updates this receipt before delivery.


def _identity(info):
    return (info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns, info.st_ctime_ns)


def _json(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True,
                      separators=(',', ':'), allow_nan=False).encode('utf-8')


def _strict(raw):
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError('duplicate-key')
            result[key] = value
        return result
    def nonfinite(value):
        raise ValueError('nonfinite')
    return json.loads(raw, object_pairs_hook=pairs, parse_constant=nonfinite)


def import_local_source_actors(source, output_dir, *, schema_sql, expected_identity,
                               expected_records, expected_input_sha256, hash_policy,
                               max_compressed_bytes, max_expanded_bytes, max_line_bytes,
                               max_database_bytes, max_output_bytes, checkpoint_rows=64):
    """One exclusive private generation with durable progress/error counters.

    hash_policy is independently-pinned or observe-selected-custody-snapshot. The
    latter records the observed digest, never publisher authenticity. Real source
    invocation needs a fresh separate selection; no manifest-to-permission loader.
    Metadata I/O failure or abrupt termination can leave only the last checkpoint;
    committed state then needs explicit reconciliation, never an automatic retry.
    parsed_record_sha256 hashes the exact decompressed singleton-packet line + LF.
    """
    source, output = Path(source), Path(output_dir)
    progress = {'state': 'preparing', 'source_id': SOURCE_ID, 'release_id': RELEASE_ID,
                'compressed_bytes_read': 0, 'observed_input_sha256': None,
                'expanded_bytes_read': 0, 'read_records': 0, 'parsed_records': 0,
                'pending_reference_rows': 0, 'pending_actor_rows': 0,
                'committed_reference_rows': 0, 'committed_actor_rows': 0,
                'offer_rows': 0, 'price_offer_field_records': 0,
                'crc_eof_verified': False, 'source_identity_verified': False,
                'source_fd_closed': True, 'database_closed': True,
                'checkpoint_rows': checkpoint_rows, 'crash_counter_overshoot_max_rows': checkpoint_rows,
                'expected_records': expected_records,
                'selected_input_identity': list(expected_identity) if isinstance(expected_identity, tuple) else None,
                'input_hash_policy': hash_policy,
                'automatic_retry': False, 'accepted': False,
                'normalization_status': 'pending', 'canonical_links': 0}
    owned = False
    connection = stream = None
    def reject(code):
        raise SupplierImportError(code, progress)
    def persist():
        if not owned:
            return
        fd, name = tempfile.mkstemp(prefix='.progress-', dir=output)
        with os.fdopen(fd, 'wb') as saved:
            saved.write(_json(progress) + b'\n')
            saved.flush()
            os.fsync(saved.fileno())
        os.replace(name, output / 'progress.json')
        directory = os.open(output, os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)
    def output_size():
        return sum(max(p.stat().st_size, p.stat().st_blocks * 512)
                   for p in output.iterdir() if p.is_file())
    try:
        integers = [expected_records, max_compressed_bytes, max_expanded_bytes,
                    max_line_bytes, max_database_bytes, max_output_bytes, checkpoint_rows]
        if (any(type(x) is not int or x <= 0 for x in integers)
                or expected_records > 100000 or max_compressed_bytes > 16 * 1024**2
                or max_expanded_bytes > 128 * 1024**2 or max_line_bytes > 1024**2
                or max_database_bytes % 4096 or max_database_bytes > 64 * 1024**2
                or max_output_bytes < 2 * max_database_bytes + 65536
                or max_output_bytes > 256 * 1024**2 or checkpoint_rows > 1024
                or not isinstance(expected_identity, tuple) or len(expected_identity) != 5):
            reject('supplier-invalid-limits')
        if hashlib.sha256(schema_sql).hexdigest() != SCHEMA_SHA256:
            reject('supplier-schema-pin')
        if hash_policy not in ('independently-pinned', 'observe-selected-custody-snapshot'):
            reject('supplier-hash-policy')
        if (expected_input_sha256 is None and hash_policy == 'independently-pinned'):
            reject('supplier-input-pin-required')
        if expected_input_sha256 is not None and (not isinstance(expected_input_sha256, str)
                or len(expected_input_sha256) != 64
                or any(x not in '0123456789abcdef' for x in expected_input_sha256)):
            reject('supplier-input-pin-invalid')
        if output.exists() or output.is_symlink():
            reject('supplier-output-exists')
        output.mkdir(mode=0o700)
        owned = True
        persist()
        before = source.lstat()
        if not stat.S_ISREG(before.st_mode) or _identity(before) != expected_identity:
            reject('supplier-input-identity')
        stream = os.fdopen(os.open(source, os.O_RDONLY | os.O_NOFOLLOW), 'rb')
        progress['source_fd_closed'] = False
        if _identity(os.fstat(stream.fileno())) != expected_identity:
            reject('supplier-input-identity')
        if before.st_size > max_compressed_bytes:
            reject('supplier-input-bound')
        compressed = stream.read(before.st_size)
        progress['compressed_bytes_read'] = len(compressed)
        progress['observed_input_sha256'] = hashlib.sha256(compressed).hexdigest()
        # Persist the digest before ANY database write: failed11529 lost it.
        persist()
        if (len(compressed) != before.st_size
                or _identity(os.fstat(stream.fileno())) != expected_identity
                or (expected_input_sha256 is not None
                    and progress['observed_input_sha256'] != expected_input_sha256)):
            reject('supplier-input-pin-or-identity')
        database = output / 'suppliers.sqlite'
        fd = os.open(database, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        os.close(fd)
        connection = sqlite3.connect(database)
        progress['database_closed'] = False
        connection.execute('PRAGMA foreign_keys=ON')
        connection.execute('PRAGMA page_size=4096')
        connection.execute('PRAGMA max_page_count=' + str(max_database_bytes // 4096))
        connection.execute('PRAGMA synchronous=FULL')
        connection.executescript(schema_sql.decode('utf-8'))
        asset = 'local-retained-asset:' + SOURCE_ID + ':' + progress['observed_input_sha256']
        seen = set()
        with gzip.GzipFile(fileobj=io.BytesIO(compressed), mode='rb') as expanded:
            while True:
                raw = expanded.readline(max_line_bytes + 1)
                if not raw:
                    break
                progress['expanded_bytes_read'] += len(raw)
                if (len(raw) > max_line_bytes or not raw.endswith(b'\n')
                        or progress['expanded_bytes_read'] > max_expanded_bytes):
                    reject('supplier-expanded-bound')
                progress['read_records'] += 1
                if progress['read_records'] > expected_records:
                    reject('supplier-record-count')
                packet = _strict(raw)
                _json(packet)  # Reject overflow/nonfinite values without changing retained source bytes.
                if not isinstance(packet, list) or len(packet) != 1 or not isinstance(packet[0], dict):
                    reject('supplier-packet-shape')
                row = packet[0]
                provenance, data = row.get('provenance'), row.get('data')
                if not isinstance(provenance, dict) or not isinstance(data, dict):
                    reject('supplier-record-shape')
                native = provenance.get('recordId')
                if (row.get('kind') != 'organization' or not isinstance(native, str)
                        or row.get('id') != SOURCE_ID + ':organization:' + native
                        or (provenance.get('sourceId'), provenance.get('releaseId'),
                            provenance.get('license'), provenance.get('visibility'))
                        != (SOURCE_ID, RELEASE_ID, 'CC0 1.0', 'public')
                        or not isinstance(data.get('name'), str)
                        or not isinstance(data.get('roles'), list)
                        or not all(isinstance(x, str) for x in data['roles'])
                        or not isinstance(data.get('identifiers'), list)
                        or {'system': 'Wikidata', 'value': native} not in data['identifiers']):
                    reject('supplier-record-scope')
                ordinal = progress['read_records']
                token = hashlib.sha256(_json([asset, ordinal, row['id']])).hexdigest()
                reference, actor = 'local-source-record:' + token, 'local-source-actor:' + token
                pointer = str(source) + '#decompressed-jsonl-line=' + str(ordinal) + '#/0'
                progress['parsed_records'] += 1
                connection.execute('INSERT INTO retained_reference_record VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)',
                    (reference, SOURCE_ID, RELEASE_ID, asset, progress['observed_input_sha256'], ordinal,
                     row['id'], pointer, 'und', raw.decode('utf-8'), hashlib.sha256(raw).hexdigest(),
                     None, 'external-binding-pending', 'offmenu-local-organization-source-import',
                     '2', 'source-faithful-imported'))
                progress['pending_reference_rows'] += 1
                connection.execute('INSERT INTO supplier_source_actor VALUES(?,?,?,?,?,?,?,?)',
                    (actor, reference, native, data['name'], _json(data['roles']).decode(),
                     None, None, 'pending'))
                progress['pending_actor_rows'] += 1
                seen.add(native)
                progress['price_offer_field_records'] += int(any(k in data for k in
                    ('price', 'prices', 'offer', 'offers', 'currency', 'availability')))
                if ordinal % checkpoint_rows == 0:
                    persist()
                    if output_size() > max_output_bytes - 65536:
                        reject('supplier-output-bound')
        progress['crc_eof_verified'] = True
        if progress['read_records'] != expected_records:
            reject('supplier-record-count')
        if (_identity(os.fstat(stream.fileno())) != expected_identity
                or _identity(source.lstat()) != expected_identity):
            reject('supplier-input-changed')
        progress['source_identity_verified'] = True
        if connection.execute('PRAGMA integrity_check').fetchone()[0] != 'ok' or connection.execute('PRAGMA foreign_key_check').fetchall():
            reject('supplier-storage-check')
        if output_size() > max_output_bytes - 65536:
            reject('supplier-output-bound')
        connection.commit()
        progress['committed_reference_rows'] = progress['pending_reference_rows']
        progress['committed_actor_rows'] = progress['pending_actor_rows']
        progress['distinct_source_actor_ids'] = len(seen)
        progress['repeated_source_actor_occurrences'] = progress['read_records'] - len(seen)
        progress['state'] = 'completed-source-import'
    except BaseException as error:
        if connection is not None:
            connection.rollback()
        code = error.args[0] if isinstance(error, SupplierImportError) else (
            'supplier-storage-bound' if isinstance(error, sqlite3.Error)
            and getattr(error, 'sqlite_errorcode', None) == sqlite3.SQLITE_FULL
            else 'supplier-invalid-or-incomplete-input')
        progress['state'], progress['error_code'] = 'failed', code
        raise SupplierImportError(code, progress) from None
    finally:
        if connection is not None:
            connection.close()
        if stream is not None:
            stream.close()
        progress['source_fd_closed'] = progress['database_closed'] = True
        persist()
    return dict(progress)
