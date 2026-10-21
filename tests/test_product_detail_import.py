"""Generated packets/new temporary stores only; no optional display imports."""
import copy
from contextlib import closing
from dataclasses import asdict, replace
import gzip
import hashlib
import json
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from offmenu.refresh import product_detail_import as store
from offmenu.refresh import product_detail_import_readers as readers
from offmenu.refresh.acceptance import Asset, SourceContract, canonical, fingerprint, ids_digest, qualify
from offmenu.refresh.core import RefreshError


class ProductDetailImportTests(unittest.TestCase):
    def test_active_caller_transaction_is_rejected_without_sql_or_commit(self):
        for ignore_storage_settings in (False, True):
            with self.subTest(ignore_storage_settings=ignore_storage_settings), closing(sqlite3.connect(':memory:')) as db:
                db.execute('CREATE TEMP TABLE caller_work(value TEXT)'); db.commit()
                db.execute("INSERT INTO caller_work VALUES('pending')")
                db.execute('SAVEPOINT caller_savepoint')
                db.execute("INSERT INTO caller_work VALUES('after-savepoint')")
                if ignore_storage_settings:
                    def authorizer(action, name, value, database, trigger):
                        return sqlite3.SQLITE_IGNORE if action == sqlite3.SQLITE_PRAGMA and name in ('journal_mode', 'synchronous', 'temp_store') and value is not None else sqlite3.SQLITE_OK
                    db.set_authorizer(authorizer)
                self.assertTrue(db.in_transaction); statements = []; scans = []
                db.set_trace_callback(statements.append)
                def scan(asset, consume):
                    scans.append(asset['assetId']); return self.scan(asset, consume)
                with self.assertRaisesRegex(RefreshError, 'caller-transaction-active'):
                    self.load(db, scan)
                self.assertEqual(statements, []); self.assertEqual(scans, [])
                db.set_trace_callback(None)
                self.assertTrue(db.in_transaction)
                self.assertEqual(db.execute('PRAGMA foreign_keys').fetchone()[0], 0)
                self.assertEqual(db.execute('SELECT value FROM caller_work').fetchall(), [('pending',), ('after-savepoint',)])
                self.assertEqual(db.execute('SELECT count(*) FROM sqlite_master').fetchone()[0], 0)
                db.execute('ROLLBACK TO caller_savepoint')
                self.assertEqual(db.execute('SELECT value FROM caller_work').fetchall(), [('pending',)])
                db.execute('RELEASE caller_savepoint'); db.rollback()
                self.assertEqual(db.execute('SELECT value FROM caller_work').fetchall(), [])

    def test_fk_enable_ignored_by_caller_policy_fails_before_schema_or_scan(self):
        with closing(sqlite3.connect(':memory:')) as db:
            def authorizer(action, name, value, database, trigger):
                return sqlite3.SQLITE_IGNORE if action == sqlite3.SQLITE_PRAGMA and name == 'foreign_keys' and value is not None else sqlite3.SQLITE_OK
            db.set_authorizer(authorizer); scans = []
            def scan(asset, consume):
                scans.append(asset['assetId']); return self.scan(asset, consume)
            with self.assertRaisesRegex(RefreshError, 'foreign-keys-required'):
                self.load(db, scan)
            self.assertEqual(scans, [])
            self.assertFalse(db.in_transaction)
            self.assertEqual(db.execute('PRAGMA foreign_keys').fetchone()[0], 0)
            self.assertEqual(db.execute('SELECT count(*) FROM sqlite_master').fetchone()[0], 0)

    def test_fresh_store_enforces_identifier_profile_and_generation_relations(self):
        with closing(sqlite3.connect(':memory:')) as db:
            self.load(db); self.assertEqual(db.execute('PRAGMA foreign_keys').fetchone()[0], 1)
            for statement, parameters in (
                ('INSERT INTO product_detail_identifier VALUES(?,?,?,?,?,?)', ('missing', 1, 'barcode', '00123', 'source-asserted', '/fixture')),
                ('UPDATE product_detail_projection SET paired_profile_reference=? WHERE record_kind=?', ('missing', 'product')),
                ('UPDATE product_detail_projection SET generation_id=?', ('missing',))):
                with self.subTest(statement=statement), self.assertRaisesRegex(sqlite3.IntegrityError, 'FOREIGN KEY'):
                    db.execute(statement, parameters)
                db.rollback()
            self.assertEqual(db.execute('SELECT count(*) FROM retained_reference_record').fetchone()[0], 6)
            self.assertEqual(db.execute('PRAGMA foreign_key_check').fetchall(), [])

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name); self.bundle = self.root / 'inputs'; self.bundle.mkdir()
        self.code = '00012345'; self.shard = hashlib.sha256(self.code.encode()).hexdigest()[:2]
        other = next(str(n) for n in range(1000, 10000) if hashlib.sha256(str(n).encode()).hexdigest()[:2] == self.shard)
        self.off_packets = [self.off_packet(self.code, 7), self.off_packet(other, 8)]
        self.off_path = self.root / (self.shard + '.jsonl.gz')
        self.off_path.write_bytes(gzip.compress(b''.join(canonical(p) + b'\n' for p in self.off_packets)))
        self.off_selection = readers.RetainedProductShard('fixture-r1', 'a'*64, 'b'*64, self.shard,
            hashlib.sha256(self.off_path.read_bytes()).hexdigest(), self.off_path.stat().st_size, 2,
            readers._identity(self.off_path.stat()), 'c'*64, 'd'*64, 'e'*64, 'f'*64,
            frozenset(('retain', 'parse', 'transform')), fixture=True)
        self.off_limits = readers.RetainedProductLimits(1048576, 2097152, 1048576, 100, 262144, 30)
        provenance = {'sourceId': 'usda-files', 'releaseId': 'fixture-r1', 'recordId': 'fixture-fdc',
            'fetchedAt': '2026-10-21T00:00:00Z', 'visibility': 'private-candidate'}
        product = {'schemaVersion': '1.0', 'kind': 'product', 'id': 'usda-files:product:fixture-fdc',
            'countries': [], 'provenance': provenance, 'data': {'name': 'Fixture milk',
                'ingredientsText': '  milk, 豆  ', 'brand': None, 'identifiers': [{'system': 'barcode', 'value': self.code}],
                'nutritionId': 'usda-files:nutrientProfile:fixture-fdc'}}
        profile = copy.deepcopy(product); profile['kind'] = 'nutrientProfile'; profile['id'] = product['data']['nutritionId']
        profile['data'] = {'identifiers': product['data']['identifiers'], 'basis': {'amount': 100, 'unit': 'g'},
            'nutrients': {'sodium': {'value': 0.1, 'sourceAmount': '0.10', 'sourceUnit': 'mg'}}}
        self.native_rows = [product, profile]; self.native_path = self.root / 'native.jsonl'
        self.native_path.write_bytes(b''.join(canonical([row]) + b'\n' for row in self.native_rows))
        for name in ('original.txt', 'rights.txt', 'scope.txt'):
            (self.bundle / name).write_bytes(('distinct generated ' + name).encode())
        inputs = tuple(Asset(p.name, p.stat().st_size, hashlib.sha256(p.read_bytes()).hexdigest())
            for p in sorted(self.bundle.iterdir()))
        shape = {'type': 'object', 'required': ['schemaVersion', 'kind', 'id', 'countries', 'provenance', 'data']}
        schemas = {'product': shape, 'nutrientProfile': shape}
        self.contract = SourceContract('usda-files', 'fixture-r1', 'fixture-native', provenance['fetchedAt'],
            inputs, 2, ids_digest([row['id'] for row in self.native_rows]), schemas, fingerprint(schemas),
            lambda _: (), 'f'*64, inputs[1], inputs[2], frozenset(('retain', 'parse', 'transform')), fixture=True)
        raw = self.native_path.read_bytes()
        manifest = {'sourceId': 'usda-files', 'releaseId': 'fixture-r1', 'acquiredAt': self.contract.acquired_at,
            'normalizedRecords': 2, 'rightsEvidenceSha256': inputs[1].sha256, 'scopeEvidenceSha256': inputs[2].sha256,
            'candidateBytes': len(raw), 'candidateSha256': hashlib.sha256(raw).hexdigest(),
            'inputFiles': [vars(a) for a in inputs]}
        self.qualification = qualify(self.contract, self.bundle, self.native_path, manifest, scratch_root=self.root)
        self.assertTrue(self.qualification['qualified'], self.qualification['errors'])
        self.pin = self.qualification['qualificationSha256']
        common = {'releaseId': 'fixture-r1', 'rightsReceiptSHA256': 'd'*64, 'custodyReceiptSHA256': 'e'*64,
            'citationId': None, 'citationStatus': 'fixture-only', 'projectionLimitations': ['generated only']}
        self.assets = [dict(common, assetId='fixture-off', sourceId='off', inputPath=str(self.off_path),
            inputSHA256=self.off_selection.sha256, inputBytes=self.off_selection.bytes, products=2, profiles=2,
            representation='off-legacy-paired-gzip', identifierInputId='parse-derived:off-occurrences:'+'b'*64,
            identifierAssetSHA256='b'*64, originalSHA256='a'*64, projectionVersion='offmenu-bulk/1'),
            dict(common, assetId='fixture-usda', sourceId='usda-files', inputPath=str(self.native_path),
            inputSHA256=manifest['candidateSha256'], inputBytes=len(raw), products=1, profiles=1,
            representation='usda-native-jsonl', qualificationSHA256=self.pin, identifierInputId='fixture-usda',
            identifierAssetSHA256=manifest['candidateSha256'], originalSHA256=inputs[0].sha256,
            projectionVersion='fixture-native/1')]
        self.limits = store.ProductDetailStoreLimits(10, 4194304, 100, 1048576, 16777216, 30)

    def off_packet(self, code, ordinal):
        provenance = {'sourceId': 'off', 'releaseId': 'fixture-r1', 'recordId': code,
            'archiveSha256': 'a'*64, 'sourceRow': ordinal, 'transform': 'offmenu-bulk/1'}
        product = {'schemaVersion': '1.0', 'kind': 'product', 'id': 'off:product:'+code, 'countries': [],
            'provenance': provenance, 'data': {'name': 'Fixture 豆', 'brand': None,
                'ingredientsText': '  Water, Salt  ', 'identifiers': [{'system': 'barcode', 'value': code}],
                'nutritionId': 'off:nutrientProfile:'+code}}
        profile = copy.deepcopy(product); profile['kind'] = 'nutrientProfile'; profile['id'] = product['data']['nutritionId']
        profile['data'] = {'basis': {'amount': 100, 'unit': 'g'}, 'nutrients': {}}
        return [product, profile]

    def scan(self, asset, consume):
        if asset['sourceId'] == 'off':
            return readers.scan_retained_off_product_shard(self.off_path, selection=self.off_selection,
                limits=self.off_limits, on_packet=lambda packet, n, code, ordinal:
                    consume(packet, 2*n-1, 2*n, ordinal, 'jsonl:packet:'+str(n)))
        return readers.scan_qualified_native_product_pairs(self.native_path, contract=self.contract,
            qualification=self.qualification, qualification_sha256=self.pin,
            identity=readers._identity(self.native_path.stat()),
            limits=readers.NativeProductScanLimits(1048576, 100, 1048576, 30),
            on_pair=lambda packet, product, profile: consume(packet, product, profile, product, 'jsonl:line:'+str(product)))

    def load(self, db, scan=None, limits=None):
        return store.ingest_product_details(db, self.assets, scan_asset_once=scan or self.scan,
            limits=limits or self.limits, generation_id='fixture-gen',
            input_manifest_sha256=store._hash(store.prepare_product_detail_manifest(self.assets)),
            operation_selection_sha256='e'*64, identifier_database_sha256='c'*64,
            coverage_scope={'scope': 'generated fixture, not actual population'})

    def assert_prefix(self, db, error):
        self.assertEqual(db.execute('SELECT state,processed_asset_count,product_records,profile_records FROM product_detail_generation').fetchone(),
            ('incomplete', 1, 2, 2))
        self.assertEqual(db.execute('SELECT count(*) FROM retained_reference_record').fetchone()[0], 4)
        self.assertEqual(error.product_detail_retained_state['productsRetained'], 2)
        self.assertEqual(len(error.product_detail_retained_state['completedAssets']), 1)
        self.assertFalse(error.product_detail_retained_state['completeReceiptReturned'])

    def test_new_namespace_imports_without_optional_modules_and_checks_typed_selections(self):
        code = """import sys
from offmenu.refresh import product_detail_import as s,product_detail_import_readers as r
assert s.readers is r
assert s.ProductDetailStoreLimits.__module__ == 'offmenu.refresh.product_detail_import'
assert r.RetainedProductShard.__module__ == 'offmenu.refresh.product_detail_import_readers'
for name in ('native_barcode_lookup','product_detail_store','product_label_sections','identifier_database'):
    assert 'offmenu.refresh.'+name not in sys.modules
for name in ('_fields','CurrentIdentifierEvidence','read_product_details','scan_cached_product_detail_asset'):
    assert not hasattr(s,name)
for name in ('lookup_native_barcode','lookup_retained_off_products','_retained_details'):
    assert not hasattr(r,name)
"""
        subprocess.run([sys.executable, '-c', code], cwd=Path(__file__).resolve().parents[1], check=True)
        with self.assertRaisesRegex(readers.NativeLookupError, 'retained-selection-required'):
            readers.scan_retained_off_product_shard(self.off_path, selection=SimpleNamespace(**asdict(self.off_selection)),
                limits=self.off_limits, on_packet=lambda *args: self.fail('wrong namespace'))

    def test_full_source_readers_import_complete_payloads_with_actual_record_pointers(self):
        with closing(sqlite3.connect(':memory:')) as db:
            result = self.load(db)
            self.assertEqual((result['products'], result['profiles'], len(result['completedAssets'])), (3, 3, 2))
            for source, pointer, payload, digest, encoded in db.execute('SELECT r.source_id,r.source_pointer,r.source_payload_json,r.parsed_record_sha256,p.source_binding_json FROM retained_reference_record r JOIN product_detail_projection p USING(reference_record_id)'):
                location, _, tail = pointer.partition('/'); number = int(location.rsplit(':', 1)[1])
                lines = gzip.decompress(self.off_path.read_bytes()).splitlines() if source == 'off' else self.native_path.read_bytes().splitlines()
                actual = json.loads(lines[number-1])[int(tail)]
                self.assertEqual(actual, json.loads(payload)); self.assertEqual(store._hash(actual), digest)
                binding = json.loads(encoded)
                self.assertEqual(binding['recordPointer'], pointer); self.assertIn(pointer, binding['recordPointers'])
            self.assertEqual(db.execute('PRAGMA foreign_key_check').fetchall(), [])
            self.assertEqual(db.execute('SELECT count(*) FROM product_detail_projection WHERE fields_json IS NOT NULL OR canonical_ingredient_id IS NOT NULL').fetchone()[0], 0)
        receipt = self.scan(self.assets[1], lambda *args: None)
        self.assertEqual(receipt['originalAssetSHA256s'], [self.contract.inputs[0].sha256])
        self.assertTrue(receipt['EOFFullyVerified']); self.assertEqual(receipt['bodyPasses'], 1)
        # Metadata coordinate cases retained in the exact writer closure; no cache decoder is installed here.
        self.assertEqual(store._record_source_pointers('off-cached-qualified-pair', 1, 1, 2, '/records'), ('/records/0', '/records/1'))
        self.assertEqual(store._record_source_pointers('usda-reviewed-lookup-products-json', 1, 1, None, '/lookup/matches/0/record'), ('/lookup/matches/0/record',))

    def test_bad_final_receipt_or_original_source_binding_rolls_back_current_asset(self):
        for change in ({'EOFFullyVerified': False}, {'bodyPasses': 2}, {'sourceId': 'wrong'},
                       {'originalAssetSHA256s': [self.contract.rights_evidence.sha256]}):
            with self.subTest(change=change), closing(sqlite3.connect(':memory:')) as db:
                def bad(asset, consume):
                    receipt = self.scan(asset, consume)
                    return dict(receipt, **change) if asset['sourceId'] == 'usda-files' else receipt
                with self.assertRaises(RefreshError) as error: self.load(db, bad)
                self.assert_prefix(db, error.exception)

    def test_late_native_hash_failure_retains_only_completed_prefix(self):
        raw = self.native_path.read_bytes(); self.native_path.write_bytes(raw.replace(b'milk', b'MILK'))
        with closing(sqlite3.connect(':memory:')) as db:
            with self.assertRaisesRegex(readers.NativeLookupError, 'hash-or-count') as error: self.load(db)
            self.assert_prefix(db, error.exception)

    def test_truncated_gzip_footer_and_unterminated_native_line_never_complete(self):
        original = self.off_path.read_bytes(); old_selection = self.off_selection; old_asset = dict(self.assets[0])
        truncated = original[:-8]; self.off_path.write_bytes(truncated)
        self.off_selection = replace(old_selection, sha256=hashlib.sha256(truncated).hexdigest(),
            bytes=len(truncated), identity=readers._identity(self.off_path.stat()))
        self.assets[0] = dict(old_asset, inputSHA256=self.off_selection.sha256, inputBytes=len(truncated))
        with closing(sqlite3.connect(':memory:')) as db:
            with self.assertRaises(readers.NativeLookupError) as error: self.load(db)
            self.assertEqual(db.execute('SELECT state,processed_asset_count,product_records,profile_records FROM product_detail_generation').fetchone(), ('incomplete', 0, 0, 0))
            self.assertEqual(db.execute('SELECT count(*) FROM retained_reference_record').fetchone()[0], 0)
            self.assertEqual(error.exception.product_detail_retained_state['completedAssets'], [])
        self.off_path.write_bytes(original)
        self.off_selection = replace(old_selection, identity=readers._identity(self.off_path.stat()))
        self.assets[0] = old_asset
        self.native_path.write_bytes(self.native_path.read_bytes()[:-1])
        with closing(sqlite3.connect(':memory:')) as db:
            with self.assertRaises(readers.NativeLookupError) as error: self.load(db)
            self.assert_prefix(db, error.exception)

    def test_coordinate_or_profile_provenance_failure_retains_prefix(self):
        for mode in ('pointer', 'profile-line', 'profile-release'):
            with self.subTest(mode=mode), closing(sqlite3.connect(':memory:')) as db:
                def bad(asset, consume):
                    if asset['sourceId'] == 'off': return self.scan(asset, consume)
                    def changed(packet, product, profile, identifier, pointer):
                        packet = copy.deepcopy(packet)
                        if mode == 'pointer': pointer = 'jsonl:line:999'
                        if mode == 'profile-line': profile += 1
                        if mode == 'profile-release': packet[1]['provenance']['releaseId'] = 'wrong'
                        consume(packet, product, profile, identifier, pointer)
                    return self.scan(asset, changed)
                with self.assertRaises(RefreshError) as error: self.load(db, bad)
                self.assert_prefix(db, error.exception)

    def test_reader_holds_custody_and_byte_limits_fail_before_qualified_output(self):
        with self.assertRaises(readers.NativeLookupError):
            readers.scan_qualified_native_product_pairs(self.native_path, contract=replace(self.contract, holds=('fixture-hold',)),
                qualification=self.qualification, qualification_sha256=self.pin, identity=readers._identity(self.native_path.stat()),
                limits=readers.NativeProductScanLimits(1048576, 100, 1048576, 30), on_pair=lambda *args: self.fail('held'))
        with self.assertRaises(readers.NativeLookupError):
            readers.scan_retained_off_product_shard(self.off_path, selection=self.off_selection,
                limits=replace(self.off_limits, max_compressed_bytes=1), on_packet=lambda *args: self.fail('bound'))
        with self.assertRaises(readers.NativeLookupError):
            readers.scan_retained_off_product_shard(self.off_path,
                selection=replace(self.off_selection, identity=(0, 0, self.off_selection.bytes, 0, 0)),
                limits=self.off_limits, on_packet=lambda *args: self.fail('custody'))

    def test_pure_manifest_new_empty_store_and_finite_limits(self):
        with patch.object(store.Path, 'open', side_effect=AssertionError('no source open')), patch.object(store.Path, 'stat', side_effect=AssertionError('no source stat')):
            store.prepare_product_detail_manifest(self.assets)
        with closing(sqlite3.connect(':memory:')) as db:
            with self.assertRaisesRegex(RefreshError, 'selection-or-limits'): self.load(db, limits=replace(self.limits, max_records=1))
            self.assertEqual(db.execute('SELECT count(*) FROM sqlite_master').fetchone()[0], 0)
            self.load(db)
            with self.assertRaisesRegex(RefreshError, 'new-empty-store'): self.load(db)

    def test_late_completion_deadline_retains_committed_rows_and_clears_hook(self):
        with closing(sqlite3.connect(':memory:')) as db, patch.object(store.time, 'monotonic', return_value=100.0) as clock:
            completed = [False]
            def trace(sql):
                if sql.startswith("UPDATE product_detail_generation SET state='completed'"): completed[0] = True
                if completed[0] and sql == 'COMMIT': clock.return_value = 1000.0
            db.set_trace_callback(trace)
            with self.assertRaisesRegex(RefreshError, 'time-bound') as error: self.load(db)
            db.set_trace_callback(None)
            self.assertEqual(db.execute('SELECT state,processed_asset_count,product_records,profile_records FROM product_detail_generation').fetchone(), ('incomplete', 2, 3, 3))
            self.assertEqual(error.exception.product_detail_retained_state['productsRetained'], 3)
            self.assertEqual(len(error.exception.product_detail_retained_state['completedAssets']), 2)
            self.assertEqual(db.execute('WITH RECURSIVE n(x) AS (VALUES(1) UNION ALL SELECT x+1 FROM n WHERE x<2000) SELECT sum(x) FROM n').fetchone()[0], 2001000)


if __name__ == '__main__': unittest.main()
