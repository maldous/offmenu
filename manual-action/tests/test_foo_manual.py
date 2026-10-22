"""Generated fixtures only; never touches Foo paths or retained data."""
import gzip
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import tarfile
import tempfile
import unittest
from unittest.mock import patch

SPEC = importlib.util.spec_from_file_location('foo_manual', Path(__file__).resolve().parents[1] / 'foo_manual.py')
m = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(m)


class ManualActionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name) / 'known' / 'root'
        self.root.mkdir(parents=True)
        self.archive = self.root / 'source.tar.gz'

    def tearDown(self):
        self.temp.cleanup()

    def archive_of(self, entries, trailing=b''):
        body = io.BytesIO()
        with tarfile.open(fileobj=body, mode='w', format=tarfile.PAX_FORMAT) as tf:
            for name, value, kind in entries:
                member = tarfile.TarInfo(name)
                member.type = kind
                if kind == tarfile.REGTYPE:
                    member.size = len(value)
                    tf.addfile(member, io.BytesIO(value))
                else:
                    member.linkname = value.decode()
                    tf.addfile(member)
        raw = gzip.compress(body.getvalue() + trailing, mtime=0)
        self.archive.write_bytes(raw)
        return hashlib.sha256(raw).hexdigest()[:8]

    def inspect(self, entries, trailing=b''):
        prefix = self.archive_of(entries, trailing)
        return m.inspect_supplier(self.archive, prefix)

    def test_safe_source_has_full_archive_and_member_digests_no_extraction(self):
        out = self.inspect([('./source/review.py', b'print("generated fixture")\n', tarfile.REGTYPE), ('manifest.json', b'{"kind":"generated"}', tarfile.REGTYPE)])
        self.assertEqual(out['status'], 'inspection_pass_manual_review_required')
        self.assertEqual(len(out['observed_sha256']), 64)
        self.assertEqual(len(out['manifest']), 2)
        self.assertFalse((self.root / 'source').exists())
        self.assertEqual(out['transfer'], 'NOT_UPLOADED')

    def test_corrupt_deflate_is_structured_block(self):
        # Gzip header, deliberately invalid reserved DEFLATE block, fake trailer.
        raw = bytes.fromhex('1f8b0800000000000003') + b'\x07' + b'\x00' * 8
        self.archive.write_bytes(raw)
        out = m.inspect_supplier(self.archive, hashlib.sha256(raw).hexdigest()[:8])
        self.assertEqual(out['status'], 'blocked')
        self.assertEqual(out['reason'], 'error')

    def test_deadline_propagates_past_per_file_handlers_and_writes_receipt(self):
        with patch.object(m, 'open_dir', side_effect=m.Deadline('wall_time_limit')):
            with self.assertRaises(m.Deadline):
                m.file_meta(self.root)
        result = self.root / 'timeout.json'
        with patch.object(m, 'inventory', side_effect=m.Deadline('wall_time_limit')):
            code = m.main(['inventory', '--inventory-root', str(self.root), '--output', str(result)])
        self.assertEqual(code, 2)
        self.assertEqual(json.loads(result.read_text())['error'], 'wall_time_limit')

    def test_missing_archive_is_blocked(self):
        self.assertEqual(m.inspect_supplier(self.archive)['reason'], 'missing')

    def test_prefix_mismatch_is_blocked(self):
        self.archive_of([('code.py', b'x=1', tarfile.REGTYPE)])
        self.assertEqual(m.inspect_supplier(self.archive, '00000000')['reason'], 'sha256_prefix_mismatch')

    def test_traversal_absolute_backslash_and_control_names_blocked(self):
        for name in ('../evil.py', '/evil.py', 'a/../../evil.py', 'a\\evil.py', 'a\nevil.py', 'C:evil.py'):
            with self.subTest(name=name):
                self.assertEqual(self.inspect([(name, b'x=1', tarfile.REGTYPE)])['status'], 'blocked')

    def test_links_and_special_types_blocked(self):
        for kind in (tarfile.SYMTYPE, tarfile.LNKTYPE, tarfile.FIFOTYPE, tarfile.CHRTYPE):
            with self.subTest(kind=kind):
                self.assertEqual(self.inspect([('code.py', b'/etc/passwd', kind)])['reason'], 'unsafe_member_type')

    def test_secrets_and_dataset_names_blocked(self):
        for name in ('.env', '.aws/config.py', 'secrets/token.py', 'data.csv', 'planet.pbf', 'raw/code.py', 'a.sqlite', 'retained/a.json'):
            with self.subTest(name=name):
                self.assertEqual(self.inspect([(name, b'x=1', tarfile.REGTYPE)])['status'], 'blocked')

    def test_secret_content_and_binary_blocked_without_echo(self):
        for content in (b'-----BEGIN PRIVATE KEY-----', b'\x00binary', b'API_KEY="' + b'a' * 32 + b'"'):
            out = self.inspect([('source.py', content, tarfile.REGTYPE)])
            self.assertEqual(out['reason'], 'binary_or_secret_looking_content')
            self.assertNotIn(content.decode(errors='replace'), json.dumps(out))

    def test_json_rows_and_unknown_extensions_blocked(self):
        for name, body in (('fixture.json', b'[{"item":1}]'), ('customers.json', b'{}'), ('opaque.exe', b'plain text')):
            self.assertEqual(self.inspect([(name, body, tarfile.REGTYPE)])['status'], 'blocked')

    def test_exact_supplier_metadata_names_accept_generated_dicts(self):
        for name in ('generated-author-proof.json', 'generated-boundary-evidence.json', 'source-file-pins.json'):
            with self.subTest(name=name):
                out = self.inspect([('supplier-review/' + name, b'{"kind":"generated","checks":2}', tarfile.REGTYPE)])
                self.assertEqual(out['status'], 'inspection_pass_manual_review_required')
                self.assertEqual(out['manifest'][0]['bytes'], 31)

    def test_supplier_metadata_names_do_not_bypass_row_content_or_raw_path_guards(self):
        for name in ('generated-author-proof.json', 'generated-boundary-evidence.json', 'source-file-pins.json'):
            for data in (b'[{"raw_record":1}]', b'"not metadata"', b'{"token":"ghp_' + b'A' * 25 + b'"}', b'\xff'):
                with self.subTest(name=name, data_kind=data[:1]):
                    self.assertEqual(self.inspect([('supplier-review/' + name, data, tarfile.REGTYPE)])['status'], 'blocked')
            with self.subTest(name=name, case='raw_path'):
                self.assertEqual(self.inspect([('raw/' + name, b'{"records":[]}', tarfile.REGTYPE)])['reason'], 'dataset_looking_member_path')

    def test_supplier_metadata_name_allowance_is_exact_not_proof_evidence_pattern(self):
        for name in ('other-proof.json', 'other-evidence.json', 'x-generated-author-proof.json', 'generated-author-proof-copy.json', 'SOURCE-FILE-PINS.json'):
            with self.subTest(name=name):
                self.assertEqual(self.inspect([(name, b'{}', tarfile.REGTYPE)])['reason'], 'json_not_named_as_source_metadata')

    def test_exact_supplier_schema_ddl_is_read_only_source(self):
        sql = b"""-- Generated source schema, not a database.
        PRAGMA foreign_keys = ON;
        BEGIN TRANSACTION;
        CREATE TABLE IF NOT EXISTS parent (id TEXT PRIMARY KEY) WITHOUT ROWID;
        CREATE TABLE item (id INTEGER PRIMARY KEY, parent_id TEXT,
          note TEXT DEFAULT 'example; value',
          FOREIGN KEY (parent_id) REFERENCES parent(id) ON DELETE CASCADE ON UPDATE RESTRICT) STRICT;
        CREATE UNIQUE INDEX IF NOT EXISTS item_parent ON item(parent_id) WHERE parent_id IS NOT NULL;
        COMMIT;
        """
        out = self.inspect([(m.SUPPLIER_SCHEMA_MEMBER, sql, tarfile.REGTYPE)])
        self.assertEqual(out['status'], 'inspection_pass_manual_review_required')
        self.assertEqual(out['manifest'][0]['path'], m.SUPPLIER_SCHEMA_MEMBER)
        self.assertFalse((self.root / 'supplier-review').exists())

    def test_sql_allowance_is_exact_member_not_extension(self):
        for name in ('schema.sql', 'source/schema.sql', 'supplier-review/schema.sql', 'supplier-review/source/other.sql', 'supplier-review/source/SCHEMA.sql'):
            with self.subTest(name=name):
                self.assertEqual(self.inspect([(name, b'CREATE TABLE t(id INT);', tarfile.REGTYPE)])['reason'], 'non_source_member_extension')

    def test_supplier_schema_rejects_dml_dumps_and_hidden_secondary_statements(self):
        cases = [
            b'INSERT INTO t VALUES (1);', b'COPY t FROM STDIN;\n1\n\\.',
            b'CREATE TABLE t(id INT); INSERT INTO t VALUES (1);',
            b'CREATE TABLE t AS SELECT 1;', b'CREATE TABLE t AS VALUES (1);',
            b'CREATE TABLE t(id INT) INSERT INTO t VALUES (1);',
            b'CREATE TABLE t(id INT); UPDATE t SET id=2;', b'DELETE FROM t;',
            b'REPLACE INTO t VALUES (1);', b'CREATE TRIGGER tr AFTER INSERT ON t BEGIN SELECT 1; END;',
            b'PRAGMA load_extension="extension";', b'ATTACH DATABASE "other.db" AS other;',
            b'CREATE TABLE t(id TEXT DEFAULT(readfile("secret")));',
            b'CREATE TABLE t(id TEXT DEFAULT(LOAD_EXTENSION("evil")));',
            b'CREATE TABLE t(id INT); .read dump.sql', b'1,raw,row\n2,raw,row',
            b'CREATE TABLE t(id INT); /* unterminated', b"CREATE TABLE t(id TEXT DEFAULT 'unterminated);",
        ]
        for sql in cases:
            with self.subTest(sql=sql[:40]):
                out = self.inspect([(m.SUPPLIER_SCHEMA_MEMBER, sql, tarfile.REGTYPE)])
                self.assertEqual(out['reason'], 'sql_not_schema_ddl')

    def test_supplier_schema_rejects_quoted_unsafe_function_calls(self):
        for quote, end in (('"', '"'), ('`', '`'), ('[', ']')):
            for function in ('readfile', 'writefile', 'load_extension'):
                with self.subTest(quote=quote, function=function):
                    sql = ('CREATE TABLE t(id TEXT DEFAULT(' + quote + function + end + "('private')));").encode()
                    self.assertEqual(self.inspect([(m.SUPPLIER_SCHEMA_MEMBER, sql, tarfile.REGTYPE)])['reason'], 'sql_not_schema_ddl')
        sql = b'CREATE TABLE t("readfile" TEXT, `writefile` TEXT, [load_extension] TEXT);'
        self.assertEqual(self.inspect([(m.SUPPLIER_SCHEMA_MEMBER, sql, tarfile.REGTYPE)])['status'], 'inspection_pass_manual_review_required')

    def test_supplier_schema_keeps_secret_binary_size_and_raw_path_guards(self):
        for data in (b'CREATE TABLE t(id INT); -- ghp_' + b'A' * 25, b'CREATE TABLE t(id INT);\x00', b'\xff'):
            self.assertEqual(self.inspect([(m.SUPPLIER_SCHEMA_MEMBER, data, tarfile.REGTYPE)])['status'], 'blocked')
        out = self.inspect([('raw/' + m.SUPPLIER_SCHEMA_MEMBER, b'CREATE TABLE t(id INT);', tarfile.REGTYPE)])
        self.assertEqual(out['reason'], 'dataset_looking_member_path')
        prefix = self.archive_of([(m.SUPPLIER_SCHEMA_MEMBER, b'CREATE TABLE t(id INT);', tarfile.REGTYPE)])
        with patch.object(m, 'MAX_MEMBER', 1):
            self.assertEqual(m.inspect_supplier(self.archive, prefix)['reason'], 'member_size_limit')

    def test_blocked_archive_retains_digest_and_private_failed_member_only(self):
        out = self.inspect([('supplier-review/opaque.exe', b'source', tarfile.REGTYPE)])
        self.assertEqual(out['reason'], 'non_source_member_extension')
        self.assertEqual(out['observed_sha256'], hashlib.sha256(self.archive.read_bytes()).hexdigest())
        self.assertEqual(out['failed_member'], {'ordinal': 1, 'name': 'supplier-review/opaque.exe', 'kind': 'file', 'bytes': 6})
        summary = m.public_summary({'observed_at': 'test', 'command': 'supplier', 'supplier': out})
        self.assertNotIn('failed_member', json.dumps(summary))
        self.assertNotIn('opaque.exe', json.dumps(summary))
        self.assertNotIn(str(self.root), json.dumps(summary))
        self.assertEqual(summary['supplier']['observed_sha256'], out['observed_sha256'])
        unsafe = self.inspect([('../secret.py', b'x=1', tarfile.REGTYPE)])
        self.assertEqual(unsafe['failed_member'], {'ordinal': 1})
        self.assertNotIn('../secret.py', json.dumps(unsafe))

    def test_duplicate_canonical_member_blocked(self):
        out = self.inspect([('a.py', b'x=1', tarfile.REGTYPE), ('./a.py', b'x=2', tarfile.REGTYPE)])
        self.assertEqual(out['reason'], 'duplicate_member_path')

    def test_member_size_count_compressed_expanded_and_tail_limits(self):
        entries = [('a.py', b'x' * 5000, tarfile.REGTYPE)]
        prefix = self.archive_of(entries)
        with patch.object(m, 'MAX_MEMBER', 100):
            self.assertEqual(m.inspect_supplier(self.archive, prefix)['reason'], 'member_size_limit')
        with patch.object(m, 'MAX_MEMBERS', 0):
            self.assertEqual(m.inspect_supplier(self.archive, prefix)['reason'], 'archive_member_limit')
        with patch.object(m, 'MAX_COMPRESSED', 1):
            self.assertEqual(m.inspect_supplier(self.archive, prefix)['reason'], 'compressed_archive_limit')
        with patch.object(m, 'MAX_EXPANDED', 512):
            self.assertEqual(m.inspect_supplier(self.archive, prefix)['reason'], 'expanded_archive_limit')
        self.assertEqual(self.inspect(entries, b'HIDDEN')['reason'], 'trailing_archive_payload')

    def test_archive_symlink_and_parent_symlink_refused(self):
        self.archive_of([('a.py', b'x=1', tarfile.REGTYPE)])
        alias = self.root / 'alias.tar.gz'
        alias.symlink_to(self.archive)
        self.assertEqual(m.inspect_supplier(alias)['status'], 'blocked')
        alias_dir = self.root / 'aliasdir'
        alias_dir.symlink_to(self.root, target_is_directory=True)
        self.assertEqual(m.inspect_supplier(alias_dir / self.archive.name)['status'], 'blocked')

    def test_inventory_is_bounded_metadata_only_and_skips_symlinks(self):
        for i in range(20):
            (self.root / ('planet-%s.part' % i)).write_bytes(b'not a real dataset')
        (self.root / 'osm-link').symlink_to('/etc', target_is_directory=True)
        with patch.object(Path, 'read_bytes', side_effect=AssertionError('dataset body read')):
            out = m.inventory([self.root], max_entries=4)
        self.assertEqual(out['entries_seen'], 4)
        self.assertTrue(out['truncated'])
        self.assertLessEqual(len(out['matches']), 4)
        self.assertFalse(any('osm-link' in r['path'] for r in out['matches']))

    def test_inventory_depth_results_and_missing_root(self):
        deep = self.root / 'a' / 'b'
        deep.mkdir(parents=True)
        (deep / 'planet.part').touch()
        self.assertFalse(m.inventory([self.root], max_depth=0)['matches'])
        out = m.inventory([self.root / 'absent'])
        self.assertEqual(out['roots'][0]['status'], 'missing')
        (self.root / 'manifest.json').touch()
        (self.root / 'receipt.json').touch()
        self.assertEqual(len(m.inventory([self.root], max_results=1)['matches']), 1)

    def test_sensitive_or_broad_root_refused(self):
        for path in ('/', '/home/user', '/home/user/.ssh/something', '/proc/1234/fd'):
            with self.subTest(path=path), self.assertRaises(m.Refusal):
                m.validate_root(path)

    def test_exclusive_output_preserves_previous_and_rejects_symlink(self):
        output = self.root / 'result.json'
        m.write_result(output, {'ok': 1})
        with self.assertRaises(FileExistsError):
            m.write_result(output, {'ok': 2})
        self.assertEqual(json.loads(output.read_text()), {'ok': 1})
        link = self.root / 'alias.json'
        link.symlink_to(output)
        with self.assertRaises(m.Refusal):
            m.write_result(link, {'ok': 3})
        self.assertEqual(output.stat().st_mode & 0o777, 0o600)

    def test_proc_reads_no_command_line_or_environment(self):
        proc = self.root / 'proc-fixture'
        (proc / '123').mkdir(parents=True)
        (proc / '123' / 'stat').write_text('123 (python worker) S 1 2 3')
        (proc / '123' / 'cmdline').write_text('SECRET_ARGUMENT')
        (proc / '123' / 'environ').write_text('SECRET_ENVIRONMENT')
        out = m.jobs(proc)
        self.assertEqual(out['jobs'], [{'pid': 123, 'name': 'python worker', 'state': 'S'}])
        self.assertNotIn('SECRET', json.dumps(out))

    def test_summary_does_not_include_operational_metadata(self):
        result = {'observed_at': 'test', 'command': 'inventory', 'inventory': m.inventory([self.root])}
        out = m.public_summary(result)
        self.assertNotIn(str(self.root), json.dumps(out))
        self.assertEqual(out['data_loads'], 'not_implemented')

    def test_cli_generated_only_smoke_and_no_overwrite(self):
        result, summary = self.root / 'private.json', self.root / 'return.json'
        args = ['inventory', '--inventory-root', str(self.root), '--output', str(result), '--return-output', str(summary)]
        self.assertEqual(m.main(args), 0)
        self.assertEqual(json.loads(summary.read_text())['schema'], 'offmenu-manual-action-return/1')
        self.assertEqual(m.main(args), 2)


if __name__ == '__main__':
    unittest.main()
