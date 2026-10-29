"""Generated file fixtures only; no admitted source database is opened."""
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import sys
import tempfile
import tracemalloc
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import gold_snapshot_access as access


def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda: f.read(65536), b''):
            h.update(block)
    return h.hexdigest()


class SnapshotAccessTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='generated-snapshot-access-')
        self.root = Path(self.tmp.name)
        self.database = self.root / 'generated.sqlite3'
        with sqlite3.connect(self.database) as db:
            db.execute('CREATE TABLE example(value TEXT)')
            db.execute("INSERT INTO example VALUES('generated')")
        db.close()
        self.receipt = self.root / 'receipt.json'
        self.select()

    def tearDown(self):
        self.tmp.cleanup()

    def select(self):
        self.receipt.write_text(json.dumps({'state': 'ACCEPTED_GENERATED_ONLY',
            'artifact': {'path': str(self.database), 'sha256': digest(self.database)}}))
        self.pin = digest(self.receipt)

    def query(self):
        with access.verified_snapshot(self.receipt, self.pin) as selected:
            rows = selected.db.execute('SELECT * FROM example').fetchall()
        return rows, selected.verification

    def test_actual_size_carrier_is_streamed_with_small_peak_memory(self):
        # Same byte boundary as actual23; trailing sparse pages are generated.
        with self.database.open('r+b') as f:
            f.truncate(75481088)
        self.select()
        tracemalloc.start()
        try:
            rows, report = self.query()
            _, peak = tracemalloc.get_traced_memory()
        finally:
            tracemalloc.stop()
        self.assertEqual(rows, [('generated',)])
        self.assertLess(peak, 5 * 1048576)
        self.assertEqual(report['databaseBytes'], 75481088)
        self.assertEqual(report['verificationBytesRead'], 2 * 75481088)
        self.assertEqual(report['hashPasses'], 2)
        self.assertEqual(report['maxChunkBytes'], 1048576)
        self.assertEqual(report['maxDatabaseBytes'], 1073741824)

    def test_connection_is_immutable_query_only_and_does_not_create_files(self):
        original = self.database.read_bytes()
        with access.verified_snapshot(self.receipt, self.pin) as selected:
            self.assertEqual(selected.db.execute('PRAGMA query_only').fetchone(), (1,))
            with self.assertRaises(sqlite3.OperationalError):
                selected.db.execute("INSERT INTO example VALUES('denied')")
        self.assertEqual(self.database.read_bytes(), original)
        self.assertEqual(set(self.root.iterdir()), {self.database, self.receipt})
        with self.assertRaises(sqlite3.ProgrammingError):
            selected.db.execute('SELECT 1')

    def test_consumer_error_is_not_relabelled_and_resources_close(self):
        class ConsumerError(ValueError):
            pass
        with self.assertRaisesRegex(ConsumerError, 'consumer-budget'):
            with access.verified_snapshot(self.receipt, self.pin) as selected:
                raise ConsumerError('consumer-budget')
        with self.assertRaises(sqlite3.ProgrammingError):
            selected.db.execute('SELECT 1')
        self.assertEqual(self.query()[0], [('generated',)])

    def test_receipt_or_database_pin_failure(self):
        with self.assertRaisesRegex(access.SnapshotAccessError, 'admission-hash-mismatch'):
            with access.verified_snapshot(self.receipt, '0' * 64):
                self.fail('must not enter')
        with self.database.open('ab') as f:
            f.write(b'x')
        with self.assertRaisesRegex(access.SnapshotAccessError, 'database-hash-mismatch'):
            self.query()

    def test_oversize_database_rejected_before_hash(self):
        with self.database.open('r+b') as f:
            f.truncate(access.MAX_DATABASE_BYTES + 1)
        with patch.object(access._Verification, 'digest', side_effect=AssertionError('must not hash')):
            with self.assertRaisesRegex(access.SnapshotAccessError, 'snapshot-file-byte-limit'):
                self.query()

    def test_each_sidecar_including_dangling_symlink_rejected(self):
        for suffix in ('-wal', '-shm', '-journal'):
            sidecar = Path(str(self.database) + suffix)
            sidecar.symlink_to(self.root / 'missing')
            with self.assertRaisesRegex(access.SnapshotAccessError, 'sealed-snapshot-required'):
                self.query()
            sidecar.unlink()

    def test_sidecar_created_during_query_rejects_result(self):
        with self.assertRaisesRegex(access.SnapshotAccessError, 'sealed-snapshot-required'):
            with access.verified_snapshot(self.receipt, self.pin):
                Path(str(self.database) + '-wal').write_bytes(b'generated')

    def test_database_or_receipt_replacement_during_query_rejects_result(self):
        for selected_path in (self.database, self.receipt):
            with self.subTest(path=selected_path):
                with self.assertRaisesRegex(access.SnapshotAccessError, 'identity-changed'):
                    with access.verified_snapshot(self.receipt, self.pin):
                        other = self.root / 'replacement'
                        other.write_bytes(selected_path.read_bytes())
                        os.replace(other, selected_path)
                self.select()

    def test_write_then_restore_same_bytes_still_rejected(self):
        with self.assertRaisesRegex(access.SnapshotAccessError, 'identity-changed'):
            with access.verified_snapshot(self.receipt, self.pin):
                with self.database.open('r+b') as f:
                    f.seek(-1, os.SEEK_END)
                    original = f.read(1)
                    f.seek(-1, os.SEEK_END)
                    f.write(b'x')
                    f.seek(-1, os.SEEK_END)
                    f.write(original)

    def test_sqlite_opening_foreign_file_cannot_pass_matching_path_hash(self):
        other = self.root / 'foreign.sqlite3'
        with sqlite3.connect(other) as db:
            db.execute('CREATE TABLE example(value TEXT)')
        db.close()
        connect = sqlite3.connect
        def foreign(*args, **kwargs):
            return connect(other.as_uri() + '?mode=ro&immutable=1', uri=True)
        with patch.object(access.sqlite3, 'connect', foreign):
            with self.assertRaisesRegex(access.SnapshotAccessError, 'connection-identity-mismatch'):
                self.query()

    def test_unavailable_connection_identity_fails_closed(self):
        with patch.object(access, '_regular_descriptors', return_value={}):
            with self.assertRaisesRegex(access.SnapshotAccessError, 'connection-identity-mismatch'):
                self.query()

    def test_descriptor_scan_has_an_independent_entry_bound(self):
        with patch.object(access, 'MAX_DESCRIPTOR_ENTRIES', 1):
            with self.assertRaisesRegex(access.SnapshotAccessError, 'descriptor-scan-limit'):
                self.query()

    def test_verification_time_has_its_own_limit(self):
        # Advancing the hash clock does not alter the consumer's SQL limits.
        with patch.object(access.time, 'monotonic', side_effect=[0, 11, 11]):
            with self.assertRaisesRegex(access.SnapshotAccessError, 'verification-time-limit'):
                self.query()

    def test_duplicate_receipt_keys_and_nonfinite_values_rejected(self):
        for raw in (b'{"state":1,"state":2}', b'{"value":NaN}'):
            self.receipt.write_bytes(raw)
            self.pin = digest(self.receipt)
            with self.assertRaises(access.SnapshotAccessError):
                self.query()

    def test_symlink_database_is_not_silently_resolved(self):
        actual = self.root / 'actual.sqlite3'
        self.database.rename(actual)
        self.database.symlink_to(actual)
        with self.assertRaises(access.SnapshotAccessError):
            self.query()


if __name__ == '__main__':
    unittest.main()
