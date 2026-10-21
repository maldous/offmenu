"""Generated source packets and in-memory/new temporary DBs only."""
import copy
from dataclasses import replace
import hashlib
import json
import sqlite3
import subprocess
import unittest
from contextlib import closing
from unittest.mock import patch

from tests import test_native_barcode_lookup as fixtures
from offmenu.refresh import native_barcode_lookup as readers, product_detail_store as store
from offmenu.refresh.core import canonical, RefreshError
from offmenu.refresh import identifier_database
from offmenu.refresh.acceptance import Asset, qualify, contract_fingerprint
from offmenu.refresh.usda_product_contract import native_schemas


class ProductDetailStoreTests(unittest.TestCase):
    def test_capabilities_match_closed_usda_schema_and_actual_legacy_off_projector(self):
        usda = native_schemas()['product']['properties']['data']
        self.assertIs(usda['additionalProperties'], False)
        self.assertEqual(store.USDA_NATIVE_PRODUCT_KEYS, frozenset(usda['properties']))
        # collect-jsonl.mjs imports this exact normalizer, not off_native_policy.
        code = "import {normalizeOFF} from './public/unified-data.js'; console.log(JSON.stringify(Object.keys(normalizeOFF({code:'00123'},{id:'off',url:'https://example.invalid',license:'fixture',name:'fixture'})[0].data)));"
        keys = json.loads(subprocess.check_output(['node', '--input-type=module', '-e', code],
            cwd=store.Path(__file__).resolve().parents[1], text=True))
        self.assertEqual(store.OFF_LEGACY_PRODUCT_KEYS, frozenset(keys))
        for name in ('off-legacy-paired-gzip', 'off-cached-qualified-pair'):
            self.assertEqual(store.PRODUCT_KEYS_BY_REPRESENTATION[name], frozenset(keys))
        for name in ('usda-native-jsonl', 'usda-reviewed-lookup-products-json'):
            self.assertEqual(store.PRODUCT_KEYS_BY_REPRESENTATION[name], frozenset(usda['properties']))

    def test_representation_specific_unsupported_fields_stay_not_loaded(self):
        cases = [('usda-native-jsonl', self.native.rows[0],
                  ('packageQuantity', 'names', 'categories', 'rawNutriments', 'sourceAllergenClaims')),
                 ('usda-reviewed-lookup-products-json', self.native.rows[0],
                  ('packageQuantity', 'names', 'categories', 'rawNutriments', 'sourceAllergenClaims')),
                 ('off-legacy-paired-gzip', self.off.packet[0], ('servingQuantity', 'dataType')),
                 ('off-cached-qualified-pair', self.off.packet[0], ('servingQuantity', 'dataType'))]
        for representation, product, unsupported in cases:
            with self.subTest(representation=representation):
                fields = store._fields([product], representation)
                for name in unsupported:
                    field = fields[name]
                    self.assertEqual(field['state'], 'not-loaded', name)
                    self.assertEqual(field['reasonCode'], 'representation-not-provided')
                    self.assertIsNone(field['value']); self.assertIsNone(field['evidenceSha256'])
                key, name = ('pack', 'packageQuantity') if representation.startswith('off-') else ('serving', 'servingQuantity')
                packet = [copy.deepcopy(product)]; packet[0]['data'].pop(key, None)
                field = store._fields(packet, representation)[name]
                self.assertEqual(field['state'], 'missing'); self.assertIsNotNone(field['evidenceSha256'])
                self.assertEqual(field['sourceFieldState'], 'unknown')
                for value, state in ((None, 'null'), ({}, 'present')):
                    packet[0]['data'][key] = value
                    field = store._fields(packet, representation)[name]
                    self.assertEqual(field['state'], state); self.assertEqual(field['value'], value)
                # Unknown extension values stay in raw data without expanding a
                # closed representation's supported wrapper capabilities.
                extra, wrapper = ('serving', 'servingQuantity') if representation.startswith('off-') else ('pack', 'packageQuantity')
                packet[0]['data'][extra] = {'unknown': 'retained'}; before = copy.deepcopy(packet)
                self.assertEqual(store._fields(packet, representation)[wrapper]['state'], 'not-loaded')
                self.assertEqual(packet, before)

    def test_cached_original_rejects_upstream_lookup_and_evidence_hashes(self):
        for name in ('rights.txt', 'scope.txt'):
            (self.native.bundle / name).write_bytes(('distinct ' + name).encode())
        self.native.prepare('usda-files')
        _, path, asset, metadata, cached = self.cached_native_fixture()
        forbidden = [self.native.q['candidateSha256'], asset['inputSHA256'],
            self.native.contract.rights_evidence.sha256, self.native.contract.scope_evidence.sha256]
        self.assertTrue(all(value != asset['originalSHA256'] for value in forbidden))
        for value in forbidden:
            with self.subTest(sha=value):
                consumed = []
                with self.assertRaisesRegex(RefreshError, 'cached-native'):
                    cached(dict(asset, originalSHA256=value), lambda *args: consumed.append(args))
                self.assertEqual(consumed, [])

    def test_cached_source_contract_is_independent_and_exact(self):
        _, path, asset, metadata, cached = self.cached_native_fixture()
        def call(context, details):
            return store.scan_cached_product_detail_asset(asset, identity=readers._identity(path.stat()),
                consume=lambda *args: self.fail('must fail before consuming'),
                native_lookup_metadata=details, native_lookup_contract=context)
        with patch.object(store.os, 'open', side_effect=AssertionError('no body before contract selection')), self.assertRaisesRegex(RefreshError, 'cached-native-contract'):
            call(None, metadata)
        for context, details in ((replace(self.native.contract, scope_id='wrong'), metadata),
                (self.native.contract, dict(metadata, originalContractInputs=[])),
                (self.native.contract, dict(metadata, contractSha256='9'*64))):
            with self.subTest(context=context.scope_id, metadata=list(details)), patch.object(store.os, 'open', side_effect=AssertionError('no body before contract selection')), self.assertRaisesRegex(RefreshError, 'cached-native'):
                call(context, details)

    def test_loaded_mapped_fields_distinguish_missing_null_empty_and_unavailable(self):
        for representation in ('usda-native-jsonl', 'usda-reviewed-lookup-products-json',
                               'off-legacy-paired-gzip', 'off-cached-qualified-pair'):
            with self.subTest(representation=representation):
                product = copy.deepcopy(self.native.rows[0])
                product['provenance']['sourceId'] = 'off' if representation.startswith('off-') else 'usda-files'
                product['data'].pop('ingredientsText'); product['data'].pop('marketCountry', None)
                fields = store._fields([product], representation)
                missing = fields['ingredientDeclaration']
                self.assertEqual(missing['state'], 'missing')
                self.assertEqual(missing['reasonCode'], 'projection-field-absent')
                self.assertIsNone(missing['value']); self.assertIsNone(missing['fieldPointer'])
                self.assertIsNotNone(missing['evidenceSha256'])
                self.assertEqual(missing['sourceFieldState'], 'unknown')
                self.assertEqual(fields['nutrientProfile']['state'], 'not-loaded')
                self.assertEqual(fields['imageUrlReferences']['state'], 'not-loaded')
                if product['provenance']['sourceId'] == 'usda-files':
                    self.assertEqual(fields['markets']['state'], 'missing')
                for value, expected in ((None, 'null'), ('', 'present'), ('  source text  ', 'present')):
                    product['data']['ingredientsText'] = value
                    field = store._fields([product], representation)['ingredientDeclaration']
                    self.assertEqual(field['state'], expected); self.assertEqual(field['value'], value)

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
        self.identifier_db = sqlite3.connect(':memory:'); self.addCleanup(self.identifier_db.close)
        self.populate_identifier_evidence()
        self.identifier_evidence = store.CurrentIdentifierEvidence(self.identifier_db, 'fixture-run', 'c'*64)

    def populate_identifier_evidence(self):
        # Real accepted identifier schema/view, with generated metadata only.
        db = self.identifier_db; db.executescript(identifier_database.DDL)
        def insert(table, **values):
            db.execute('INSERT INTO ' + table + '(' + ','.join(values) + ') VALUES(' +
                ','.join('?' for _ in values) + ')', tuple(values.values()))
        insert('fetch_citation', citation_id='fixture', identity_state='unresolved-backfill',
            unknown_fields_json='{}', metadata_origin_pointer='fixture')
        insert('fetch_asset', asset_id='fixture', citation_id='fixture', identity_state='unresolved-backfill',
            retrieval_clock_state='fixture', unknown_fields_json='{}')
        insert('parse_job', parse_job_id='fixture', input_manifest_sha256='a'*64, engine_id='fixture',
            engine_version='1', engine_code_sha256='a'*64, interpretation_mode='deterministic',
            input_assets_manifest_sha256='a'*64, state='completed', database_created_at='fixture')
        insert('identifier_load', run_id='fixture-run', input_manifest_sha256='a'*64, parse_job_id='fixture',
            input_manifest_pointer='fixture', loader_version=identifier_database.VERSION,
            selection_receipt_sha256='a'*64, state='completed', finalization_evidence_sha256='a'*64,
            database_created_at='fixture')
        for row in self.observations():
            insert('identifier_input', run_id=row['run_id'], input_id=row['input_id'], asset_id='fixture',
                source_id=row['source_id'], release_id=row['release_id'], artifact_sha256=row['artifact_sha256'],
                artifact_bytes=1, acquisition_clock_state='fixture', operation_evidence_sha256='a'*64)
            insert('identifier_source_record', run_id=row['run_id'], input_id=row['input_id'],
                record_ordinal=row['record_ordinal'], source_record_id=row['source_record_id'],
                native_record_id=row['native_record_id'], source_pointer='/fixture', parse_job_id='fixture',
                identity_state='source-asserted')
            insert('identifier_assertion', assertion_id=row['assertion_id'], run_id=row['run_id'], input_id=row['input_id'],
                record_ordinal=row['record_ordinal'], identifier_ordinal=1, namespace=row['namespace'],
                lexical_value=row['lexical_value'], source_pointer='/fixture', disposition=row['disposition'])
        db.commit()

    def read_details(self, db, observations, **kwargs):
        return store.read_product_details(db, observations, identifier_evidence=self.identifier_evidence, **kwargs)

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
            output = self.read_details(db, self.observations(), selection=self.selection)
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
                output = self.read_details(db, [{**off, **change}], selection=self.selection)
                self.assertEqual(output['sourceProducts'], [])
                self.assertEqual(output['productDetailAvailability'][0]['state'], 'not-loaded')
            with self.assertRaisesRegex(RefreshError, 'identifier-evidence'):
                self.read_details(db, [off], selection=replace(self.selection, identifier_database_sha256='9'*64))

    def test_fabricated_run_assertion_or_invalid_disposition_never_emits_bridge(self):
        with closing(sqlite3.connect(':memory:')) as db:
            self.load(db); observation = self.observations()[0]
            for change in ({'run_id': 'fabricated'}, {'assertion_id': 999999},
                           {'disposition': 'invalid'}, {'disposition': 'unresolved'}):
                with self.subTest(change=change):
                    output = self.read_details(db, [{**observation, **change}], selection=self.selection)
                    self.assertEqual(output['sourceProducts'], [])
                    self.assertEqual(output['productDetailAvailability'][0]['state'], 'not-loaded')

    def test_current_evidence_is_required_selected_and_read_by_assertion_pk(self):
        with closing(sqlite3.connect(':memory:')) as db:
            self.load(db); row = self.observations()[0]
            with self.assertRaisesRegex(RefreshError, 'identifier-evidence'):
                store.read_product_details(db, [row], selection=self.selection)
            plan = self.identifier_db.execute('EXPLAIN QUERY PLAN ' + store.CURRENT_OBSERVATION_SQL,
                (row['assertion_id'], 'fixture-run')).fetchall()
            self.assertTrue(any('SEARCH a USING INTEGER PRIMARY KEY' in p[3] for p in plan), plan)
            self.assertFalse(any('SCAN ' in p[3] for p in plan), plan)
            output = self.read_details(db, [row], selection=self.selection)
            evidence = output['sourceProducts'][0]['exactObservationBridge']['assertionEvidence']
            self.assertEqual(evidence['assertion_id'], row['assertion_id'])
            self.assertEqual(evidence['disposition'], 'source-asserted')
            for sql in ("UPDATE identifier_assertion SET disposition='invalid',reason_code='fixture' WHERE assertion_id=11",
                        "UPDATE identifier_load SET state='incomplete' WHERE run_id='fixture-run'"):
                self.identifier_db.execute(sql)
                result = self.read_details(db, [row], selection=self.selection)
                self.assertEqual(result['sourceProducts'], [])
                self.assertEqual(result['productDetailAvailability'][0]['reasonCode'], 'no-current-identifier-assertion')

    def test_identifier_failure_clears_both_query_progress_handlers(self):
        with closing(sqlite3.connect(':memory:')) as db:
            self.load(db)
            self.identifier_db.execute('DROP VIEW barcode_identifier_inspection')
            with self.assertRaises(sqlite3.OperationalError):
                self.read_details(db, self.observations(), selection=self.selection, max_steps=1)
            for connection in (db, self.identifier_db):
                self.assertEqual(connection.execute('WITH RECURSIVE n(x) AS (VALUES(1) UNION ALL SELECT x+1 FROM n WHERE x<2000) SELECT sum(x) FROM n').fetchone()[0], 2001000)

    def test_evidence_hash_cannot_be_persisted_as_original_source(self):
        for name in ('rights.txt', 'scope.txt'):
            (self.native.bundle / name).write_bytes(('distinct fixture ' + name).encode())
        self.native.prepare('usda-files'); self.assets[1] = self.asset('usda-files')
        evidence = (self.native.contract.rights_evidence, self.native.contract.scope_evidence)
        self.assertTrue(all(a.sha256 != self.assets[1]['originalSHA256'] for a in evidence))
        for item in evidence:
            assets = [self.assets[0], dict(self.assets[1], originalSHA256=item.sha256)]
            with self.subTest(path=item.path), closing(sqlite3.connect(':memory:')) as db:
                with self.assertRaisesRegex(RefreshError, 'asset-source-receipt'):
                    self.load(db, assets=assets)
                self.assertEqual(db.execute('SELECT product_records,profile_records FROM product_detail_generation').fetchone(), (2, 2))

    def test_optional_clock_evidence_is_excluded_from_qualified_native_receipt(self):
        native = self.native
        def asset(name, value):
            raw = canonical(value); (native.bundle / name).write_bytes(raw)
            return Asset(name, len(raw), hashlib.sha256(raw).hexdigest())
        original = native.contract.inputs[0]
        rights = asset('rights.txt', {'fixture': 'rights only'})
        identity = {'sourceId': 'usda-files', 'releaseId': native.contract.release_id, 'scopeId': native.contract.scope_id}
        clock = asset('clock.json', {**identity, 'schemaVersion': 'offmenu-retained-clock-evidence/1',
            'status': 'unknown-retained', 'originalAcquiredAt': None, 'rightsEvidenceSha256': rights.sha256,
            'inputFiles': [vars(original)], 'basisEvidenceSha256': 'a'*64})
        marker = {'status': 'unknown-retained', 'evidenceSha256': clock.sha256}
        scope = asset('scope.txt', {**identity, 'acquisitionClock': marker})
        native.contract = replace(native.contract, acquired_at=None, inputs=(original, rights, scope, clock),
            rights_evidence=rights, scope_evidence=scope, clock_evidence=clock, acquisition_clock_status='unknown-retained')
        for row in native.rows:
            row['provenance'].update(fetchedAt=None, acquisitionClock=marker)
        raw = b''.join(readers.canonical([row]) + b'\n' for row in native.rows); native.candidate.write_bytes(raw)
        manifest = {**identity, 'acquiredAt': None, 'normalizedRecords': 2,
            'rightsEvidenceSha256': rights.sha256, 'scopeEvidenceSha256': scope.sha256, 'acquisitionClock': marker,
            'candidateBytes': len(raw), 'candidateSha256': hashlib.sha256(raw).hexdigest(),
            'inputFiles': [vars(a) for a in native.contract.inputs]}
        native.q = qualify(native.contract, native.bundle, native.candidate, manifest, scratch_root=native.root)
        self.assertTrue(native.q['qualified'], native.q['errors']); native.pin = native.q['qualificationSha256']
        self.assets[1] = self.asset('usda-files')
        receipt = self.scan(self.assets[1], lambda *args: None)
        self.assertEqual(receipt['originalAssetSHA256s'], [original.sha256])
        with closing(sqlite3.connect(':memory:')) as db:
            with self.assertRaisesRegex(RefreshError, 'asset-source-receipt'):
                self.load(db, assets=[self.assets[0], dict(self.assets[1], originalSHA256=clock.sha256)])
        _, path, asset, metadata, cached = self.cached_native_fixture()
        self.assertEqual(cached(asset, lambda *args: None)['originalSha256'], original.sha256)
        with self.assertRaisesRegex(RefreshError, 'cached-native-metadata'):
            cached(dict(asset, originalSHA256=clock.sha256), lambda *args: self.fail('clock evidence is not a source'))

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
                self.read_details(db, self.observations(), selection=self.selection, max_result_bytes=2000)

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
            output = self.read_details(db, [self.observations()[1]], selection=selection)
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
                        self.read_details(db, [self.observations()[0]], selection=self.selection)
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
            output = self.read_details(db, [self.observations()[1]], selection=selection)
            self.assertEqual(output['productDetailAvailability'][0]['state'], 'ambiguous')
            self.assertEqual(len(output['sourceProducts']), 2)
            with self.assertRaisesRegex(RefreshError, 'query-candidate-bound'):
                self.read_details(db, [self.observations()[1]], selection=selection, max_candidates=1)

    def cached_native_fixture(self):
        product = self.native.rows[0]
        document = {'status': 'PRIVATE_NATIVE_LOOKUP_VERIFIED', 'lookup': {
            'sourceId': 'usda-files', 'releaseId': self.native.contract.release_id, 'scopeId': self.native.contract.scope_id,
            'candidateSha256': self.native.q['candidateSha256'], 'qualificationSha256': self.native.pin,
            'visibility': 'private', 'fixture': True, 'status': 'matched', 'barcode': self.off.code,
            'matches': [{'record': product, 'nativeProductId': product['id'], 'sourceRecordId': product['provenance']['recordId'], 'candidateLine': 1}]}}
        raw = canonical(document); path = self.native.root / 'cached.json'; path.write_bytes(raw)
        asset = dict(self.asset('usda-files'), assetId='fixture-cache', representation='usda-reviewed-lookup-products-json',
            inputPath=str(path), inputSHA256=hashlib.sha256(raw).hexdigest(), inputBytes=len(raw), profiles=0, cacheReviewSHA256='f'*64)
        metadata = {'sourceId': 'usda-files', 'releaseId': self.native.contract.release_id, 'scopeId': self.native.contract.scope_id,
            'candidateSha256': asset['inputSHA256'], 'upstreamCandidateSha256': self.native.q['candidateSha256'],
            'qualificationSha256': self.native.pin, 'expectedRecords': 1, 'upstreamExpectedRecords': 2, 'fixture': True,
            'contractSha256': contract_fingerprint(self.native.contract),
            'originalContractInputs': [vars(a) for a in self.native.contract.inputs],
            'assetBindings': [{'sha256': a.sha256} for a in self.native.contract.inputs] +
                [{'sha256': self.native.q['candidateSha256']}, {'sha256': asset['inputSHA256']}]}
        def cached(a, consume):
            return store.scan_cached_product_detail_asset(a, identity=readers._identity(path.stat()), consume=consume,
                native_lookup_metadata=metadata, native_lookup_contract=self.native.contract)
        return product, path, asset, metadata, cached

    def test_cached_native_wrapper_reuses_existing_bounded_decoder_without_parent_scan(self):
        product, path, asset, metadata, cached = self.cached_native_fixture()
        with closing(sqlite3.connect(':memory:')) as db, patch.object(readers, 'scan_qualified_native_product_pairs', side_effect=AssertionError('no parent scan')):
            self.load(db, cached, [asset])
            selection = replace(self.selection, input_manifest_sha256=store._hash(store.prepare_product_detail_manifest([asset])))
            output = self.read_details(db, [self.observations()[1]], selection=selection)
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
            output = self.read_details(db, [self.observations()[0]], selection=selection)
            self.assertEqual(output['sourceProducts'][0]['records'], self.off.packet)


if __name__ == '__main__': unittest.main()
