"""Generated in-memory fixtures only; never open a retained DB or source file."""
import copy
import importlib.util
import json
from pathlib import Path
import sqlite3
import sys
import time
import unittest

_path = Path(__file__).resolve().parents[1] / 'offmenu/refresh/source_json_slices.py'
_spec = importlib.util.spec_from_file_location('_source_json_slices_under_test', _path)
api = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = api
_spec.loader.exec_module(api)

DDL = '''CREATE TABLE retained_reference_record(
 reference_record_id TEXT PRIMARY KEY NOT NULL,
 source_id TEXT NOT NULL,release_id TEXT NOT NULL,asset_id TEXT NOT NULL,
 asset_sha256 TEXT NOT NULL,source_ordinal INTEGER NOT NULL CHECK(source_ordinal>=1),
 native_record_id TEXT,source_pointer TEXT NOT NULL,original_language TEXT NOT NULL,
 source_payload_json TEXT NOT NULL,parsed_record_sha256 TEXT NOT NULL,
 citation_id TEXT,citation_binding_status TEXT NOT NULL,parse_engine_id TEXT NOT NULL,
 parse_engine_version TEXT NOT NULL,processing_status TEXT NOT NULL,
 UNIQUE(asset_id,asset_sha256,source_ordinal))'''


class BlobSpy:
    def __init__(self, blob, owner):
        self.blob, self.owner, self.closed = blob, owner, False
    def __len__(self): return len(self.blob)
    def seek(self, offset):
        self.owner.seeks.append(offset)
        return self.blob.seek(offset)
    def read(self, size):
        self.owner.reads.append(size)
        if getattr(self.owner, 'fail_read', False):
            raise sqlite3.OperationalError('private source path must not be exposed')
        return self.blob.read(size)
    def close(self):
        self.closed = True
        self.blob.close()


class ConnectionSpy(sqlite3.Connection):
    def blobopen(self, table, column, row, *, readonly=False, name='main'):
        self.opens.append((table, column, row, readonly, name))
        blob = BlobSpy(super().blobopen(table, column, row, readonly=readonly, name=name), self)
        self.blobs.append(blob)
        return blob


class Fixture:
    def __init__(self, payload='{"generated":true}', *, length_limit=4096, utf16=False, blob_value=False):
        self.db = sqlite3.connect(':memory:', factory=ConnectionSpy)
        self.db.opens, self.db.reads, self.db.seeks, self.db.blobs = [], [], [], []
        if utf16: self.db.execute("PRAGMA encoding='UTF-16'")
        self.db.execute(DDL)
        self.identity = {'rowid': 1, 'reference_record_id': 'synthetic-record',
            'source_id': 'synthetic-source', 'release_id': 'synthetic-release', 'asset_id': 'generated-only',
            'asset_sha256': 'a' * 64, 'source_ordinal': 1, 'native_record_id': None,
            'source_pointer': '/generated/1', 'original_language': 'und', 'parsed_record_sha256': 'b' * 64,
            'citation_id': None, 'citation_binding_status': 'fixture-only',
            'parse_engine_id': 'generated-fixture', 'parse_engine_version': '1', 'processing_status': 'synthetic'}
        columns = [name for name in api.IDENTITY_COLUMNS if name != 'rowid'] + ['source_payload_json']
        values = [self.identity[name] for name in columns[:-1]] + [payload]
        placeholders = ['?'] * len(values)
        if type(payload) is bytes and not blob_value: placeholders[-1] = 'CAST(? AS TEXT)'
        self.db.execute('INSERT INTO retained_reference_record(' + ','.join(columns) + ') VALUES(' +
                        ','.join(placeholders) + ')', values)
        self.db.commit()
        self.raw = payload if type(payload) is bytes else payload.encode('utf-8')
        self.binding = {'store': {'databaseSha256': 'c' * 64, 'qualificationSha256': 'd' * 64,
                                 'generationId': 'generated-store'},
            'operation': {'receiptSha256': 'e' * 64, 'operationId': 'synthetic-private-slice'},
            'rights': {'receiptSha256': 'f' * 64, 'state': 'permitted'},
            'unknownExtension': {'attribution': 'Generated fixture, not a retained source.'}}
        self.selection = self.select()
        self.db.execute('PRAGMA query_only=ON')
        self.db.execute('BEGIN')
        self.db.setlimit(sqlite3.SQLITE_LIMIT_LENGTH, length_limit)
        self.trace, self.qualifications, self.budget_calls, self.steps = [], 0, 0, 0
        self.revoked, self.revoke_at, self.step_cap = False, None, 100000
        self.db.set_trace_callback(self.trace.append)
        def progress():
            self.steps += 1
            return int(self.steps > self.step_cap)
        self.progress = progress
        self.db.set_progress_handler(progress, 1)

    def select(self, *, identity=None, binding=None, source_bytes=None, cap=api.SOURCE_VALUE_BYTES):
        return api.SourceJsonSelection(record_id=(identity or self.identity)['reference_record_id'],
            row_identity=copy.deepcopy(identity or self.identity), binding=copy.deepcopy(binding or self.binding),
            source_bytes=len(self.raw) if source_bytes is None else source_bytes, source_value_cap=cap)
    def qualify(self, selection):
        self.qualifications += 1
        if self.revoked or self.qualifications == self.revoke_at:
            raise api.SourceJsonSliceError('access-revoked')
        return api.QualifiedRead(self.db, self.selection)
    def budget(self):
        self.budget_calls += 1
        if self.steps > self.step_cap: raise api.SourceJsonSliceError('budget-exhausted')
    def read(self, offset=0, **overrides):
        options = {'offset': offset, 'qualify': self.qualify, 'check_budget': self.budget,
                   'deadline': time.monotonic() + 5}
        options.update(overrides)
        return api.read_source_json_slice(self.db, self.selection, **options)
    def close(self): self.db.close()


class SliceTests(unittest.TestCase):
    def fixture(self, *args, **kwargs):
        f = Fixture(*args, **kwargs)
        self.addCleanup(f.close)
        return f
    def error(self, code, call):
        with self.assertRaises(api.SourceJsonSliceError) as caught: call()
        self.assertEqual(caught.exception.code, 'source-json-slice-' + code)
        return caught.exception

    def test_large_text_low_sqlite_limit_verbatim_unicode_crlf_huge_integer_extensions(self):
        payload = '{\r\n "unknown/extension~":"' + ('😀e\u0301漢字' * 30000) + '\",\r\n "huge":' + \
                  ('9' * 10000) + ',"lexical":1.2300e+004,"extensions":{"unknown":null}}\r\n'
        f = self.fixture(payload)
        self.assertGreater(len(f.raw), 262144)
        self.assertEqual(f.db.getlimit(sqlite3.SQLITE_LIMIT_LENGTH), 4096)
        chunks, offset, calls = [], 0, 0
        while True:
            p = f.read(offset)
            calls += 1
            self.assertEqual(p['offsetBytes'], offset)
            self.assertEqual(p['endOffsetBytes'] - offset, len(p['jsonText'].encode()))
            self.assertLessEqual(len(p['jsonText'].encode()), 16384)
            self.assertLessEqual(len(api.canonical(p)), 262144)
            self.assertLessEqual(len(api.canonical(p['selection'])), 8192)
            self.assertEqual(p['extentBytes'], len(f.raw))
            chunks.append(p['jsonText'])
            if not p['hasMore']: break
            self.assertGreater(p['nextOffsetBytes'], offset)
            offset = p['nextOffsetBytes']
        self.assertEqual(''.join(chunks).encode(), f.raw)
        self.assertEqual(f.qualifications, 4 * calls)
        self.assertTrue(all(0 < n <= 16384 for n in f.db.reads))
        self.assertTrue(all(x[0:2] == ('retained_reference_record', 'source_payload_json') and x[3:] == (True, 'main') for x in f.db.opens))
        selects = [sql for sql in f.trace if sql.upper().startswith('SELECT')]
        self.assertTrue(selects)
        self.assertTrue(all('typeof(source_payload_json)' in sql and 'WHERE reference_record_id=' in sql for sql in selects))
        self.assertFalse(any(repr(payload) in sql for sql in f.trace))
        self.assertTrue(all(blob.closed for blob in f.db.blobs))
        self.assertEqual(f.db.getlimit(sqlite3.SQLITE_LIMIT_LENGTH), 4096)
        self.assertLess(f.steps, 100000)
        self.assertTrue(f.db.in_transaction)

    def test_utf8_chunk_boundary_repeats_only_unconsumed_tail(self):
        f = self.fixture('{"v":"😀"}')
        first = f.read(chunk_bytes=8)
        self.assertEqual(first['jsonText'], '{"v":"')
        self.assertEqual(first['nextOffsetBytes'], 6)
        second = f.read(6, chunk_bytes=8)
        self.assertEqual(first['jsonText'] + second['jsonText'], f.raw.decode())
        self.assertFalse(second['hasMore'])
        self.assertEqual(f.db.reads, [8, len(f.raw) - 6])

    def test_mid_codepoint_offset_and_too_small_chunk_fail_typed(self):
        f = self.fixture('{"v":"😀"}')
        self.error('offset-not-utf8-boundary', lambda: f.read(7))
        self.error('chunk-too-small', lambda: f.read(6, chunk_bytes=1))
        self.assertTrue(all(blob.closed for blob in f.db.blobs))

    def test_every_continuation_requires_fresh_rights_and_revoke_blocks_body(self):
        f = self.fixture('x' * 50000)
        first = f.read()
        reads = len(f.db.reads)
        f.revoked = True
        self.error('access-revoked', lambda: f.read(first['nextOffsetBytes']))
        self.assertEqual(len(f.db.reads), reads)

    def test_revocation_at_each_stage_never_releases_a_value(self):
        for phase in (1, 2, 3, 4):
            with self.subTest(phase=phase):
                f = self.fixture()
                f.revoke_at = phase
                e = self.error('access-revoked', f.read)
                self.assertNotIn('jsonText', api.error_envelope(e))
                self.assertEqual(len(f.db.reads), int(phase == 4))
                self.assertTrue(all(blob.closed for blob in f.db.blobs))

    def test_wrong_native_context_connection_or_untyped_approval_is_rejected(self):
        f, other = self.fixture(), self.fixture()
        for current in [True, {'permitted': True}, api.QualifiedRead(other.db, f.selection)]:
            self.error('qualification-mismatch', lambda: f.read(qualify=lambda _: current))
        changed = copy.deepcopy(f.binding);changed['operation']['receiptSha256'] = '0' * 64
        bad = f.select(binding=changed)
        self.error('qualification-mismatch', lambda: f.read(qualify=lambda _: api.QualifiedRead(f.db, bad)))
        self.assertEqual(f.trace, [])
        self.assertEqual(f.db.reads, [])

    def test_wrong_row_hash_or_complete_persisted_metadata_never_opens_payload(self):
        for key, value in [('rowid', 2), ('asset_sha256', '0' * 64),
                           ('parsed_record_sha256', '0' * 64), ('parse_engine_version', '2'),
                           ('source_pointer', '/other'), ('citation_binding_status', 'changed')]:
            with self.subTest(key=key):
                f = self.fixture();identity = copy.deepcopy(f.identity);identity[key] = value
                f.selection = f.select(identity=identity)
                self.error('row-identity-mismatch', f.read)
                self.assertEqual(f.db.opens, [])

    def test_missing_record_rejected_before_blobopen(self):
        f = self.fixture();identity = copy.deepcopy(f.identity);identity['reference_record_id'] = 'missing'
        f.selection = f.select(identity=identity)
        self.error('row-missing', f.read)
        self.assertEqual(f.db.opens, [])

    def test_invalid_offsets_and_chunk_caps_do_not_attempt_db_access(self):
        f = self.fixture()
        for offset in [-1, len(f.raw) + 1, True, '0', 0.0]:
            self.error('offset', lambda: f.read(offset))
        for size in [0, 16385, True, -1]: self.error('chunk-bound', lambda: f.read(chunk_bytes=size))
        self.assertEqual(f.trace, [])
        self.assertEqual(f.qualifications, 0)

    def test_extent_mismatch_and_tighter_source_cap_fail_before_read(self):
        f = self.fixture('x' * 1000)
        f.selection = f.select(source_bytes=999)
        self.error('extent-mismatch', f.read)
        self.assertEqual(f.db.reads, [])
        f.selection = f.select(source_bytes=500, cap=500)
        self.error('extent-bound', f.read)
        self.assertEqual(f.db.reads, [])

    def test_candidate_16mib_ceiling_never_raises_other_caps(self):
        f = self.fixture()
        for options in [{'source_bytes': 16 * 1024**2 + 1}, {'cap': 16 * 1024**2 + 1}, {'cap': True}]:
            self.error('selection', lambda: f.select(**options))
        self.assertEqual(f.db.getlimit(sqlite3.SQLITE_LIMIT_LENGTH), 4096)
        self.assertEqual(api.WIRE_BYTES, 262144)

    def test_query_only_read_transaction_and_encoding_are_mandatory(self):
        f = self.fixture();f.db.execute('PRAGMA query_only=OFF')
        self.error('query-only-required', f.read)
        self.assertEqual(f.db.opens, [])
        g = self.fixture();g.db.rollback()
        self.error('read-transaction-required', g.read)
        h = self.fixture('"text"', utf16=True)
        self.error('encoding', h.read)
        self.assertEqual(h.db.opens, [])

    def test_readonly_blob_rejects_generated_write_and_module_never_writes(self):
        f = self.fixture()
        first = f.read()
        with sqlite3.Connection.blobopen(f.db, 'retained_reference_record', 'source_payload_json', 1, readonly=True) as blob:
            with self.assertRaises(sqlite3.OperationalError) as caught: blob.write(b'X')
            self.assertEqual(caught.exception.sqlite_errorname, 'SQLITE_READONLY')
        self.assertEqual(f.read()['jsonText'], first['jsonText'])
        self.assertTrue(all(sql.upper().startswith(('SELECT', 'PRAGMA')) for sql in f.trace))

    def test_precise_runtime_sqlite_failure_preserves_low_limit(self):
        f = self.fixture(length_limit=8)
        e = self.error('sqlite-failure', f.read)
        self.assertEqual(e.sqlite_details['sqliteErrorName'], 'SQLITE_TOOBIG')
        self.assertEqual(e.sqlite_details['sqliteErrorCode'], sqlite3.SQLITE_TOOBIG)
        self.assertEqual(f.db.getlimit(sqlite3.SQLITE_LIMIT_LENGTH), 8)
        self.assertEqual(f.db.reads, [])

    def test_caller_progress_handler_remains_and_100k_vm_budget_interrupts(self):
        f = self.fixture();f.steps = 99999
        e = self.error('sqlite-failure', f.read)
        self.assertEqual(e.sqlite_details['sqliteErrorName'], 'SQLITE_INTERRUPT')
        f.steps = 0
        f.db.execute('SELECT 1').fetchone()
        self.assertGreater(f.steps, 0)
        self.assertEqual(f.db.reads, [])

    def test_host_deadline_and_five_second_ceiling_without_sleep(self):
        for host_deadline, shift in [(0.5, 1), (100, 6)]:
            f = self.fixture();now = [0]
            def qualify(selection):
                result = f.qualify(selection);now[0] += shift;return result
            self.error('deadline', lambda: f.read(deadline=host_deadline, clock=lambda: now[0], qualify=qualify))
            self.assertEqual(f.db.reads, [])
        f = self.fixture()
        self.error('deadline', lambda: f.read(deadline=time.monotonic() - 1))

    def test_budget_and_qualification_callbacks_are_mandatory_and_fail_closed(self):
        f = self.fixture()
        self.error('qualification-required', lambda: f.read(qualify=None))
        self.error('budget-required', lambda: f.read(check_budget=None))
        def denied(_): raise PermissionError('private path/token must not be copied')
        e = self.error('qualification-unavailable', lambda: f.read(qualify=denied))
        self.assertNotIn('private', json.dumps(api.error_envelope(e)))
        def broken(): raise RuntimeError('private runtime text')
        self.error('budget-unavailable', lambda: f.read(check_budget=broken))
        self.assertEqual(f.db.reads, [])

    def test_invalid_utf8_inside_and_at_final_boundary_is_not_silently_replaced(self):
        for raw in [b'{"x":"\xff"}', b'{"x":"\xf0\x9f', b'\x80']:
            f = self.fixture(raw)
            self.error('invalid-utf8', f.read)
            self.assertTrue(all(blob.closed for blob in f.db.blobs))

    def test_eof_range_never_claims_whole_value_was_supplied(self):
        f = self.fixture('"source"')
        p = f.read(len(f.raw))
        self.assertEqual(p['jsonText'], '')
        self.assertFalse(p['hasMore'])
        self.assertIsNone(p['nextOffsetBytes'])
        self.assertFalse(p['valueCompleteInThisSlice'])
        self.assertEqual(f.db.reads, [])

    def test_complete_metadata_is_copied_and_oversize_or_missing_fields_fail(self):
        f = self.fixture();before = f.selection.metadata
        f.identity['source_id'] = 'changed caller';f.binding['rights']['state'] = 'revoked'
        self.assertEqual(f.selection.metadata, before)
        exposed = f.selection.metadata;exposed['binding']['rights']['state'] = 'changed'
        self.assertEqual(f.selection.metadata, before)
        with self.assertRaises(AttributeError): f.selection._json = b'changed'
        identity = copy.deepcopy(before['rowIdentity']);identity.pop('parse_engine_id')
        self.error('selection', lambda: f.select(identity=identity, binding=before['binding']))
        binding = before['binding'];binding['large'] = 'x' * 9000
        self.error('metadata-bound', lambda: api.SourceJsonSelection(record_id=before['recordId'],
            row_identity=before['rowIdentity'],binding=binding,source_bytes=len(f.raw)))

    def test_row_factory_limits_transaction_and_wire_bound_are_preserved(self):
        f = self.fixture('\x00' * 16384, length_limit=4096)
        f.db.row_factory = sqlite3.Row
        limit = f.db.getlimit(sqlite3.SQLITE_LIMIT_LENGTH)
        p = f.read()
        self.assertLessEqual(len(api.canonical(p)), 262144)
        self.assertEqual(len(p['jsonText'].encode()), 16384)
        self.assertIs(f.db.row_factory, sqlite3.Row)
        self.assertTrue(f.db.in_transaction)
        self.assertEqual(f.db.getlimit(sqlite3.SQLITE_LIMIT_LENGTH), limit)

    def test_boolean_budget_result_is_not_treated_as_permission(self):
        f = self.fixture()
        self.error('budget-exhausted', lambda: f.read(check_budget=lambda: False))
        self.assertEqual(f.db.reads, [])

    def test_blob_failure_is_safe_precise_stage_and_handle_is_closed(self):
        f = self.fixture();f.db.fail_read = True
        e = self.error('sqlite-failure', f.read)
        self.assertEqual(e.sqlite_details['stage'], 'blob-read')
        self.assertNotIn('private', json.dumps(api.error_envelope(e)))
        self.assertTrue(all(blob.closed for blob in f.db.blobs))
        unsafe = api.SourceJsonSliceError('internal', sqlite_details={'private': 'must not escape'})
        self.assertNotIn('sqlite', api.error_envelope(unsafe))

    def test_text_column_type_is_required_and_record_identifier_is_only_bound_data(self):
        f = self.fixture(b'{}', blob_value=True)
        self.error('payload-type', f.read)
        self.assertEqual(f.db.opens, [])
        g = self.fixture();identity = copy.deepcopy(g.identity)
        identity['reference_record_id'] = "synthetic-record' OR 1=1 --"
        g.selection = g.select(identity=identity)
        self.error('row-missing', g.read)
        self.assertEqual(g.db.opens, [])

    def test_missing_blob_api_has_typed_failure_and_no_select_fallback(self):
        f = self.fixture();f.db.blobopen = None
        self.error('blob-api-unavailable', f.read)
        self.assertEqual(f.trace, [])
        self.assertEqual(f.db.reads, [])


if __name__ == '__main__': unittest.main(verbosity=2)
