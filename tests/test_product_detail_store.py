"""Generated source packets and in-memory/new temporary DBs only."""
import copy
from dataclasses import replace
import hashlib
import json
import sqlite3
import unittest
from contextlib import closing
from unittest.mock import patch

from tests import test_native_barcode_lookup as fixtures
from offmenu.refresh import native_barcode_lookup as readers, product_detail_store as store
from offmenu.refresh.core import canonical, RefreshError


class ProductDetailStoreTests(unittest.TestCase):
    def setUp(self):
        self.off = fixtures.RetainedProductShardTests(); self.off.setUp(); self.addCleanup(self.off.doCleanups)
        other = next(str(n) for n in range(1000, 10000) if hashlib.sha256(str(n).encode()).hexdigest()[:2] == self.off.key)
        self.off.prepare([self.off.packet, self.off.make_packet(other, 8)])
        self.native = fixtures.NativeBarcodeLookupTests(); self.native.setUp(); self.addCleanup(self.native.doCleanups)
        product = self.native.row('fixture-fdc', self.off.code, '  Native milk\n豆  ')
        product['data'].update(nutritionId='usda-files:nutrientProfile:fixture-fdc', brand=None,
            serving={'amount': 1.5, 'unit': 'g', 'label': '1,50 source serving'}, marketCountry='source market', dataType='fixture')
        profile = copy.deepcopy(product); profile['kind'] = 'nutrientProfile'
        profile['data'] = {'identifiers': product['data']['identifiers'], 'basis': {'amount': 100, 'unit': 'g', 'state': 'as-described'},
            'nutrients': {'sodium': {'value': 0.1, 'sourceAmount': '0.10', 'sourceUnit': 'mg', 'rawFields': {'amount': '0.10'}, 'method': 'source'}}}
        self.native.rows = [product, profile]; self.native.prepare('usda-files')
        self.assets = [self.asset('off'), self.asset('usda-files')]
        self.limits = store.ProductDetailStoreLimits(10, 1048576, 1000, 1048576, 16777216, 30)
        self.selection = store.ProductDetailQuerySelection('fixture-gen', store._hash(store.prepare_product_detail_manifest(self.assets)), 'e'*64, 'c'*64)

    def asset(self, source):
        if source == 'off':
            return {'assetId': 'fixture-off-shard', 'sourceId': source, 'releaseId': self.off.selection.release_id,
                'inputPath': str(self.off.path), 'inputSHA256': self.off.selection.sha256, 'inputBytes': self.off.selection.bytes,
                'products': self.off.selection.packets, 'profiles': self.off.selection.packets, 'representation': 'off-legacy-paired-gzip',
                'identifierInputId': 'parse-derived:off-occurrences:' + self.off.selection.occurrence_sha256,
                'identifierAssetSHA256': self.off.selection.occurrence_sha256, 'originalSHA256': self.off.selection.original_sha256,
                'projectionVersion': 'offmenu-bulk/1', 'rightsReceiptSHA256': 'd'*64, 'custodyReceiptSHA256': 'e'*64,
                'citationId': 'fixture-citation', 'citationStatus': 'fixture-only',
                'projectionLimitations': ['legacy name fallback/null collapse; original field state unknown; duplicate/quarantine gaps']}
        raw = self.native.candidate.read_bytes()
        return {'assetId': 'fixture-usda-native', 'sourceId': source, 'releaseId': self.native.contract.release_id,
            'inputPath': str(self.native.candidate), 'inputSHA256': hashlib.sha256(raw).hexdigest(), 'inputBytes': len(raw),
            'products': 1, 'profiles': 1, 'representation': 'usda-native-jsonl', 'qualificationSHA256': self.native.pin,
            'identifierInputId': 'fixture-usda-native', 'identifierAssetSHA256': self.native.q['candidateSha256'],
            'originalSHA256': self.native.contract.inputs[0].sha256, 'projectionVersion': 'offmenu-products-offline/2',
            'rightsReceiptSHA256': 'd'*64, 'custodyReceiptSHA256': 'e'*64, 'citationId': None, 'citationStatus': 'fixture-only',
            'projectionLimitations': ['native serving conversion/source basis; original field state unknown']}

    def scan(self, asset, consume):
        if asset['sourceId'] == 'off':
            return readers.scan_retained_off_product_shard(self.off.path, selection=self.off.selection, limits=self.off.limits,
                on_packet=lambda packet, n, code, ordinal: consume(packet, 2*n-1, 2*n, ordinal, 'jsonl:packet:' + str(n)))
        return readers.scan_qualified_native_product_pairs(self.native.candidate, contract=self.native.contract,
            qualification=self.native.q, qualification_sha256=self.native.pin,
            identity=readers._identity(self.native.candidate.stat()),
            limits=readers.NativeProductScanLimits(1048576, 1000, 1048576, 30),
            on_pair=lambda packet, p, n: consume(packet, p, n, p, 'jsonl:line:' + str(p)))

    def load(self, db, scan=None, assets=None):
        assets = assets or self.assets
        return store.ingest_product_details(db, assets, scan_asset_once=scan or self.scan, limits=self.limits,
            generation_id='fixture-gen', input_manifest_sha256=store._hash(store.prepare_product_detail_manifest(assets)),
            operation_selection_sha256='e'*64, identifier_database_sha256='c'*64,
            coverage_scope={'meaning': 'fixture source occurrences, not physical products', 'dedupGaps': 'retained fixture limitation'})

    def observations(self):
        off = self.off.observation(7, 11)
        native = {'source_id': 'usda-files', 'release_id': self.native.contract.release_id,
            'run_id': 'fixture-run', 'input_id': 'fixture-usda-native', 'record_ordinal': 1,
            'source_record_id': 'fixture-fdc', 'native_record_id': 'usda-files:product:fixture-fdc',
            'assertion_id': 12, 'artifact_sha256': self.assets[1]['inputSHA256'],
            'namespace': 'barcode', 'lexical_value': self.off.code, 'disposition': 'source-asserted'}
        return [off, native]

    def test_full_cohorts_all_pairs_profiles_nulls_rawfields_and_exact_indexed_query(self):
        with closing(sqlite3.connect(':memory:')) as db:
            result = self.load(db)
            self.assertEqual((result['products'], result['profiles'], len(result['completedAssets'])), (3, 3, 2))
            self.assertEqual(db.execute('SELECT count(*) FROM retained_reference_record').fetchone()[0], 6)
            self.assertEqual(db.execute('SELECT count(*) FROM product_detail_projection WHERE canonical_ingredient_id IS NOT NULL').fetchone()[0], 0)
            self.assertEqual(db.execute('SELECT count(*) FROM product_detail_projection WHERE fields_json IS NOT NULL').fetchone()[0], 0)
            output = store.read_product_details(db, self.observations(), selection=self.selection)
            self.assertEqual([a['state'] for a in output['productDetailAvailability']], ['loaded', 'loaded'])
            self.assertEqual(len(output['sourceProducts']), 2)
            self.assertEqual(output['sourceProducts'][0]['fields']['ingredientDeclaration']['value'], '  Milch, 豆\n\u2028Salz  ')
            native = output['sourceProducts'][1]
            self.assertEqual(native['fields']['ingredientDeclaration']['value'], '  Native milk\n豆  ')
            self.assertEqual(native['fields']['nutrientProfile']['value']['nutrients']['sodium']['rawFields']['amount'], '0.10')
            self.assertEqual(native['fields']['brand']['state'], 'null')
            self.assertEqual(native['fields']['packageQuantity']['state'], 'not-loaded')
            self.assertEqual(native['fields']['servingQuantity']['value']['label'], '1,50 source serving')
            self.assertIsNone(native['canonicalIngredient']['conceptId'])
            self.assertTrue(output['coverage']['identifierIndexCoverageSeparate'])
            self.assertEqual(db.execute('PRAGMA foreign_key_check').fetchall(), [])
            plan = db.execute('EXPLAIN QUERY PLAN SELECT i.reference_record_id FROM product_detail_identifier i INDEXED BY product_detail_key_lookup CROSS JOIN product_detail_projection p ON p.reference_record_id=i.reference_record_id WHERE i.namespace=? AND i.lexical_value=? AND p.generation_id=?', ('barcode', self.off.code, 'fixture-gen')).fetchall()
            self.assertTrue(any('SEARCH i USING' in row[3] and 'product_detail_key_lookup' in row[3] for row in plan), plan)
            self.assertFalse(any('SCAN ' in row[3] for row in plan), plan)

    def test_same_barcode_wrong_ordinal_generation_or_input_hash_never_falls_back(self):
        with closing(sqlite3.connect(':memory:')) as db:
            self.load(db); off = self.observations()[0]
            for change in ({'record_ordinal': 999}, {'input_id': 'wrong'}, {'artifact_sha256': '9'*64}, {'native_record_id': 'wrong'}):
                output = store.read_product_details(db, [{**off, **change}], selection=self.selection)
                self.assertEqual(output['sourceProducts'], [])
                self.assertEqual(output['productDetailAvailability'][0]['state'], 'not-loaded')
            with self.assertRaisesRegex(RefreshError, 'unselected-generation'):
                store.read_product_details(db, [off], selection=replace(self.selection, identifier_database_sha256='9'*64))

    def test_late_actual_native_hash_failure_rolls_back_only_current_asset(self):
        raw = self.native.candidate.read_bytes(); self.native.candidate.write_bytes(raw.replace(b'unknownClockNote', b'UNKNOWNClockNote'))
        with closing(sqlite3.connect(':memory:')) as db:
            with self.assertRaisesRegex(readers.NativeLookupError, 'hash-or-count') as error: self.load(db)
            self.assertEqual(db.execute('SELECT state,processed_asset_count,product_records,profile_records FROM product_detail_generation').fetchone(), ('incomplete', 1, 2, 2))
            self.assertEqual(db.execute('SELECT count(*) FROM retained_reference_record').fetchone()[0], 4)
            self.assertEqual(error.exception.product_detail_retained_state['productsRetained'], 2)
            self.assertEqual(len(error.exception.product_detail_retained_state['completedAssets']), 1)
            self.assertFalse(error.exception.product_detail_retained_state['completeReceiptReturned'])

    def test_bad_eof_receipt_or_wrong_original_binding_never_commits_asset(self):
        for change in ({'EOFFullyVerified': False}, {'bodyPasses': 2}, {'sourceId': 'wrong'}, {'originalAssetSHA256s': ['9'*64]}):
            with self.subTest(change=change), closing(sqlite3.connect(':memory:')) as db:
                def bad(asset, consume):
                    receipt = self.scan(asset, consume)
                    return {**receipt, **change} if asset['sourceId'] == 'usda-files' else receipt
                with self.assertRaises(RefreshError): self.load(db, bad)
                self.assertEqual(db.execute('SELECT count(*) FROM retained_reference_record').fetchone()[0], 4)

    def test_prepare_pure_duplicate_preflight_empty_connection_and_strict_query_limit(self):
        with patch.object(store.Path, 'open', side_effect=AssertionError('no body open')), patch.object(store.Path, 'stat', side_effect=AssertionError('no body stat')):
            store.prepare_product_detail_manifest(self.assets)
        with closing(sqlite3.connect(':memory:')) as db:
            with self.assertRaisesRegex(RefreshError, 'duplicate-asset'): self.load(db, assets=self.assets + [self.assets[0]])
            self.assertEqual(db.execute('SELECT count(*) FROM sqlite_master').fetchone()[0], 0)
            self.load(db)
            with self.assertRaisesRegex(RefreshError, 'new-empty-store'): self.load(db)
            with self.assertRaisesRegex(RefreshError, 'query-result-bound'):
                store.read_product_details(db, self.observations(), selection=self.selection, max_result_bytes=2000)

    def test_cached_product_without_profile_stays_usable_without_fabricated_nutrients(self):
        asset = dict(self.assets[1], assetId='fixture-cache', representation='usda-reviewed-lookup-products-json',
            inputPath='/fixture-not-opened/cached.json', inputSHA256='8'*64, inputBytes=100, profiles=0, cacheReviewSHA256='f'*64)
        def cached(a, consume):
            consume([self.native.rows[0]], 1, None, 1, '/lookup/matches/0/record')
            return {'assetSha256': a['inputSHA256'], 'scannedBytes': 100, 'scannedRecords': 1,
                'scannedProducts': 1, 'scannedProfiles': 0, 'EOFFullyVerified': True, 'bodyPasses': 1,
                'sourceId': a['sourceId'], 'releaseId': a['releaseId'], 'identifierAssetSha256': a['identifierAssetSHA256'],
                'originalSha256': a['originalSHA256'], 'cacheReviewSha256': 'f'*64}
        with closing(sqlite3.connect(':memory:')) as db:
            self.load(db, cached, [asset])
            selection = replace(self.selection, input_manifest_sha256=store._hash(store.prepare_product_detail_manifest([asset])))
            output = store.read_product_details(db, [self.observations()[1]], selection=selection)
            self.assertEqual(output['sourceProducts'][0]['fields']['nutrientProfile']['state'], 'not-loaded')
            self.assertEqual(output['sourceProducts'][0]['fields']['ingredientDeclaration']['value'], '  Native milk\n豆  ')
            self.assertEqual(db.execute('SELECT profile_records FROM product_detail_generation').fetchone()[0], 0)

    def test_late_completion_deadline_keeps_all_committed_assets_and_clears_hook(self):
        with closing(sqlite3.connect(':memory:')) as db, patch.object(store.time, 'monotonic', return_value=100.0) as clock:
            completed = [False]
            def trace(sql):
                if sql.startswith("UPDATE product_detail_generation SET state='completed'"): completed[0] = True
                if completed[0] and sql == 'COMMIT': clock.return_value = 1000.0
            db.set_trace_callback(trace)
            with self.assertRaisesRegex(RefreshError, 'time-bound') as error: self.load(db)
            db.set_trace_callback(None)
            self.assertEqual(db.execute('SELECT state,processed_asset_count,product_records,profile_records FROM product_detail_generation').fetchone(), ('incomplete', 2, 3, 3))
            self.assertEqual(len(error.exception.product_detail_retained_state['completedAssets']), 2)
            self.assertEqual(db.execute('WITH RECURSIVE n(x) AS (VALUES(1) UNION ALL SELECT x+1 FROM n WHERE x<2000) SELECT sum(x) FROM n').fetchone()[0], 2001000)

    def test_query_clears_expired_handler_and_preserves_no_silent_partial_result(self):
        with closing(sqlite3.connect(':memory:')) as db:
            self.load(db)
            fields = store._fields
            with patch.object(store.time, 'monotonic', return_value=100.0) as clock:
                def slow(*args):
                    value = fields(*args); clock.return_value = 1000.0; return value
                with patch.object(store, '_fields', side_effect=slow):
                    with self.assertRaises((RefreshError, sqlite3.OperationalError)):
                        store.read_product_details(db, [self.observations()[0]], selection=self.selection)
                self.assertEqual(db.execute('WITH RECURSIVE n(x) AS (VALUES(1) UNION ALL SELECT x+1 FROM n WHERE x<2000) SELECT sum(x) FROM n').fetchone()[0], 2001000)

    def test_multiple_eligible_projection_evidence_is_explicit_ambiguity_not_first_winner(self):
        assets = [dict(self.assets[1], assetId='fixture-cache-' + digit,
            representation='usda-reviewed-lookup-products-json', inputSHA256=digit*64, inputBytes=100, profiles=0, cacheReviewSHA256='f'*64)
            for digit in ('8', '9')]
        def cached(a, consume):
            consume([self.native.rows[0]], 1, None, 1, '/lookup/matches/0/record')
            return {'assetSha256': a['inputSHA256'], 'scannedBytes': 100, 'scannedRecords': 1,
                'scannedProducts': 1, 'scannedProfiles': 0, 'EOFFullyVerified': True, 'bodyPasses': 1,
                'sourceId': a['sourceId'], 'releaseId': a['releaseId'], 'identifierAssetSha256': a['identifierAssetSHA256'],
                'originalSha256': a['originalSHA256'], 'cacheReviewSha256': 'f'*64}
        with closing(sqlite3.connect(':memory:')) as db:
            self.load(db, cached, assets)
            selection = replace(self.selection, input_manifest_sha256=store._hash(store.prepare_product_detail_manifest(assets)))
            output = store.read_product_details(db, [self.observations()[1]], selection=selection)
            self.assertEqual(output['productDetailAvailability'][0]['state'], 'ambiguous')
            self.assertEqual(len(output['sourceProducts']), 2)
            with self.assertRaisesRegex(RefreshError, 'query-candidate-bound'):
                store.read_product_details(db, [self.observations()[1]], selection=selection, max_candidates=1)

    def test_cached_native_wrapper_reuses_existing_bounded_decoder_without_parent_scan(self):
        product = self.native.rows[0]
        document = {'status': 'PRIVATE_NATIVE_LOOKUP_VERIFIED', 'lookup': {
            'sourceId': 'usda-files', 'releaseId': self.native.contract.release_id, 'scopeId': self.native.contract.scope_id,
            'candidateSha256': self.native.q['candidateSha256'], 'qualificationSha256': self.native.pin,
            'visibility': 'private', 'fixture': True, 'status': 'matched', 'barcode': self.off.code,
            'matches': [{'record': product, 'nativeProductId': product['id'], 'sourceRecordId': product['provenance']['recordId'], 'candidateLine': 1}]}}
        raw = canonical(document); path = self.native.root / 'cached.json'; path.write_bytes(raw)
        asset = dict(self.assets[1], assetId='fixture-cache', representation='usda-reviewed-lookup-products-json',
            inputPath=str(path), inputSHA256=hashlib.sha256(raw).hexdigest(), inputBytes=len(raw), profiles=0, cacheReviewSHA256='f'*64)
        metadata = {'sourceId': 'usda-files', 'releaseId': self.native.contract.release_id, 'scopeId': self.native.contract.scope_id,
            'candidateSha256': asset['inputSHA256'], 'upstreamCandidateSha256': self.native.q['candidateSha256'],
            'qualificationSha256': self.native.pin, 'expectedRecords': 1, 'upstreamExpectedRecords': 2, 'fixture': True,
            'assetBindings': [{'sha256': asset['originalSHA256']}]}
        def cached(a, consume):
            return store.scan_cached_product_detail_asset(a, identity=readers._identity(path.stat()), consume=consume, native_lookup_metadata=metadata)
        with closing(sqlite3.connect(':memory:')) as db, patch.object(readers, 'scan_qualified_native_product_pairs', side_effect=AssertionError('no parent scan')):
            self.load(db, cached, [asset])
            selection = replace(self.selection, input_manifest_sha256=store._hash(store.prepare_product_detail_manifest([asset])))
            output = store.read_product_details(db, [self.observations()[1]], selection=selection)
            self.assertEqual(output['sourceProducts'][0]['records'], [product])
            self.assertEqual(output['sourceProducts'][0]['fields']['nutrientProfile']['state'], 'not-loaded')

    def test_cached_off_pair_reuses_verified_saved_document_without_shard_scan(self):
        saved = readers.lookup_retained_off_products(self.off.path, selection=self.off.selection,
            observations=[self.off.observation(7, 11)], limits=self.off.limits)['sourceProducts'][0]
        raw = canonical({'sourceBinding': saved['sourceBinding'], 'records': saved['records']})
        path = self.off.root / 'cached-pair.json'; path.write_bytes(raw)
        asset = dict(self.assets[0], assetId='fixture-off-cache', representation='off-cached-qualified-pair',
            inputPath=str(path), inputSHA256=hashlib.sha256(raw).hexdigest(), inputBytes=len(raw),
            products=1, profiles=1, cacheReviewSHA256='f'*64, upstreamAssetSHA256=self.off.selection.sha256)
        def cached(a, consume):
            return store.scan_cached_product_detail_asset(a, identity=readers._identity(path.stat()), consume=consume)
        with closing(sqlite3.connect(':memory:')) as db, patch.object(readers, 'scan_retained_off_product_shard', side_effect=AssertionError('no shard scan')):
            self.load(db, cached, [asset])
            selection = replace(self.selection, input_manifest_sha256=store._hash(store.prepare_product_detail_manifest([asset])))
            output = store.read_product_details(db, [self.observations()[0]], selection=selection)
            self.assertEqual(output['sourceProducts'][0]['records'], self.off.packet)


if __name__ == '__main__': unittest.main()
