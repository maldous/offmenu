"""Generated closed checkpoints only; no real corpus, database, process or job."""
import copy
from contextlib import closing
from dataclasses import replace
import gzip
import hashlib
import json
from pathlib import Path
import sqlite3
import unittest
from unittest.mock import patch

from offmenu.refresh import product_detail_import as store
from offmenu.refresh import product_detail_import_readers as readers
from offmenu.refresh.core import RefreshError
from tests import test_product_detail_import as fixture_module


class ProductDetailResumeTests(unittest.TestCase):
    def setUp(self):
        self.f = fixture_module.ProductDetailImportTests(); self.f.setUp(); self.addCleanup(self.f.doCleanups)
        self.path = self.f.root / 'checkpoint.sqlite'
        code = next(str(n) for n in range(10000, 20000) if hashlib.sha256(str(n).encode()).hexdigest()[:2] != self.f.shard)
        key = hashlib.sha256(code.encode()).hexdigest()[:2]
        self.c_path = self.f.root / (key + '.jsonl.gz')
        self.c_path.write_bytes(gzip.compress(readers.canonical(self.f.off_packet(code, 9)) + b'\n'))
        self.c_selection = replace(self.f.off_selection, shard_key=key,
            sha256=hashlib.sha256(self.c_path.read_bytes()).hexdigest(), bytes=self.c_path.stat().st_size,
            packets=1, identity=readers._identity(self.c_path.stat()))
        self.assets = self.f.assets + [dict(self.f.assets[0], assetId='fixture-C', inputPath=str(self.c_path),
            inputSHA256=self.c_selection.sha256, inputBytes=self.c_selection.bytes, products=1, profiles=1)]
        self.manifest_sha = store._hash(store.prepare_product_detail_manifest(self.assets))
        self.receipts = {}; self.scans = []

    def scan(self, asset, consume):
        self.scans.append(asset['assetId'])
        if asset['assetId'] == 'fixture-C':
            receipt = readers.scan_retained_off_product_shard(self.c_path, selection=self.c_selection,
                limits=self.f.off_limits, on_packet=lambda packet, n, code, ordinal:
                    consume(packet, 2*n-1, 2*n, ordinal, 'jsonl:packet:'+str(n)))
        else: receipt = self.f.scan(asset, consume)
        self.receipts[asset['assetId']] = receipt
        return receipt

    def args(self, scan=None, operation='f'*64, limits=None):
        return dict(scan_asset_once=scan or self.scan, limits=limits or self.f.limits,
            generation_id='fixture-gen', input_manifest_sha256=self.manifest_sha,
            operation_selection_sha256=operation, identifier_database_sha256='c'*64,
            coverage_scope={'scope':'generated fixture, not actual population'})

    def prefix(self):
        def bad(asset, consume):
            receipt = self.scan(asset, consume)
            if asset['assetId'] == 'fixture-usda': return dict(receipt, EOFFullyVerified=False)
            return receipt
        with closing(sqlite3.connect(self.path)) as db:
            with self.assertRaisesRegex(RefreshError, 'asset-receipt'):
                store.ingest_product_details(db, self.assets, **self.args(bad, operation='e'*64))
            self.assertEqual(db.execute('SELECT state,processed_asset_count,product_records,profile_records FROM product_detail_generation').fetchone(), ('incomplete',1,2,2))
        self.assertIn('fixture-usda', self.receipts)  # reader complete is not SQL progress
        self.assertNotIn('fixture-C', self.scans)
        self.scans.clear()
        return self.select()

    def select(self, operation='f'*64):
        # Trusted generated caller verifies CLOSED checkpoint and keeps the
        # independently selected receipt digest, not a self-asserted DB field.
        with closing(sqlite3.connect('file:'+str(self.path)+'?mode=ro', uri=True)) as db:
            self.assertEqual(db.execute('PRAGMA integrity_check').fetchone(), ('ok',))
            self.assertEqual(db.execute('PRAGMA foreign_key_check').fetchall(), [])
            gen, manifest, original, state, encoded = db.execute('SELECT generation_id,input_manifest_sha256,operation_selection_sha256,state,coverage_scope_json FROM product_detail_generation').fetchone()
            coverage = json.loads(encoded)
        receipt = dict(version='offmenu-product-detail-checkpoint/1', generationId=gen,
            inputManifestSha256=manifest, originalOperationSelectionSha256=original,
            identifierDatabaseSha256='c'*64, coverageSha256=store._hash(coverage),
            databasePath=str(self.path), databaseIdentity=list(readers._identity(self.path.stat())),
            databaseSha256=hashlib.sha256(self.path.read_bytes()).hexdigest(),
            producerTerminal=True, producerReaped=True, writableHandlesClosed=True,
            cleanJournalVerified=True, integrityAndForeignKeysVerified=True, state=state,
            committedReceipts=[self.receipts[a['assetId']] for a in coverage['assets']],
            resumeOperationSelectionSha256=operation)
        return receipt

    def resume(self, db, checkpoint, **kwargs):
        args = self.args(**kwargs)
        return store.resume_existing_product_details(db, self.assets, checkpoint_receipt=checkpoint,
            checkpoint_sha256=store._hash(checkpoint), **args)

    def rows(self, db, asset='fixture-off'):
        return (db.execute('SELECT * FROM retained_reference_record WHERE asset_id=? ORDER BY reference_record_id', (asset,)).fetchall(),
            db.execute('SELECT p.* FROM product_detail_projection p JOIN retained_reference_record r USING(reference_record_id) WHERE r.asset_id=? ORDER BY p.reference_record_id', (asset,)).fetchall(),
            db.execute('SELECT i.* FROM product_detail_identifier i JOIN retained_reference_record r USING(reference_record_id) WHERE r.asset_id=? ORDER BY i.reference_record_id,i.identifier_ordinal', (asset,)).fetchall())

    def usable(self, db):
        self.assertFalse(db.in_transaction)
        self.assertEqual(db.execute('WITH RECURSIVE n(x) AS (VALUES(1) UNION ALL SELECT x+1 FROM n WHERE x<2000) SELECT sum(x) FROM n').fetchone(), (2001000,))

    def test_initial_coverage_rejects_all_writer_owned_keys_before_SQL(self):
        forged={'operationSelectionSha256':'1'*64,'checkpointSha256':'2'*64,
            'previousCoverageSha256':'3'*64,'startedAfterAssetCount':1,
            'startedAt':'2026-10-22T00:00:00+11:00','previousExceptions':[]}
        values={'resumeAttempts':[forged],'identifierOccurrences':999,
            'identifierDatabaseSha256':'c'*64,'assets':[],'sourceFirst':True}
        for key,value in values.items():
            with self.subTest(key=key),closing(sqlite3.connect(':memory:')) as db:
                statements=[];db.set_trace_callback(statements.append)
                args=self.args(scan=lambda *a:self.fail('reserved coverage reached scanner'))
                args['coverage_scope']={'scope':'caller metadata',key:value}
                with self.assertRaisesRegex(RefreshError,'coverage-reserved-key'):
                    store.ingest_product_details(db,self.assets,**args)
                self.assertEqual(statements,[]);db.set_trace_callback(None)
                self.assertEqual(db.execute('SELECT count(*) FROM sqlite_master').fetchone(),(0,))
                self.assertFalse(db.in_transaction)

    def test_resume_coverage_rejects_all_writer_owned_keys_without_prefix_mutation(self):
        checkpoint=self.prefix();before=self.path.read_bytes()
        for key,value in {'resumeAttempts':[],'identifierOccurrences':0,
            'identifierDatabaseSha256':'c'*64,'assets':[],'sourceFirst':True}.items():
            with self.subTest(key=key),closing(sqlite3.connect(self.path)) as db:
                statements=[];db.set_trace_callback(statements.append)
                args=self.args();args['coverage_scope'][key]=value
                with self.assertRaisesRegex(RefreshError,'coverage-reserved-key'):
                    store.resume_existing_product_details(db,self.assets,checkpoint_receipt=checkpoint,
                        checkpoint_sha256=store._hash(checkpoint),**args)
                self.assertEqual(statements,[]);db.set_trace_callback(None)
                self.assertEqual(self.scans,[]);self.usable(db)
            self.assertEqual(self.path.read_bytes(),before)

    def test_normal_coverage_preserves_nested_metadata_and_starts_empty_writer_lineage(self):
        scope={'scope':'generated normal scope','unknownExtension':{'resumeAttempts':['caller note'],
            'identifierOccurrences':'nested non-control annotation'},'note':None}
        def fail_A(asset,consume):raise RuntimeError('generated before any asset commit')
        with closing(sqlite3.connect(self.path)) as db:
            args=self.args(scan=fail_A,operation='e'*64);args['coverage_scope']=scope
            with self.assertRaisesRegex(RuntimeError,'before any asset commit'):
                store.ingest_product_details(db,self.assets,**args)
            coverage=json.loads(db.execute('SELECT coverage_scope_json FROM product_detail_generation').fetchone()[0])
            self.assertEqual({k:coverage[k] for k in scope},scope)
            self.assertEqual(coverage.get('resumeAttempts',[]),[])
            self.assertEqual(coverage.get('identifierOccurrences',0),0)
        checkpoint=self.select()
        with closing(sqlite3.connect(self.path)) as db:
            args=self.args();args['coverage_scope']=scope
            result=store.resume_existing_product_details(db,self.assets,checkpoint_receipt=checkpoint,
                checkpoint_sha256=store._hash(checkpoint),**args)
            coverage=json.loads(db.execute('SELECT coverage_scope_json FROM product_detail_generation').fetchone()[0])
            self.assertEqual({k:coverage[k] for k in scope},scope)
            self.assertEqual(len(result['resumeAttempts']),1)
            self.assertEqual(result['resumeAttempts'][0]['startedAfterAssetCount'],0)
            self.assertEqual(coverage['identifierOccurrences'],4)
            self.assertEqual((result['products'],result['profiles'],len(result['completedAssets'])),(4,4,3))

    def test_resume_skips_A_including_all_source_file_access_and_preserves_query_lineage(self):
        checkpoint = self.prefix()
        with closing(sqlite3.connect(self.path)) as db:
            old = self.rows(db)
            # Deleting the GENERATED completed source proves no stat/hash/open
            # is required for A. The original manifest is retained unchanged.
            self.f.off_path.unlink()
            def remaining(asset, consume):
                self.assertNotEqual(asset['assetId'], 'fixture-off', 'completed source replay')
                return self.scan(asset, consume)
            result = self.resume(db, checkpoint, scan=remaining)
            self.assertEqual(self.scans, ['fixture-usda','fixture-C'])
            self.assertEqual(self.rows(db), old)
            self.assertEqual((result['products'],result['profiles'],len(result['completedAssets']),result['unreadAssets']), (4,4,3,0))
            self.assertEqual(result['previouslyCompletedAssets'],1); self.assertFalse(result['accepted'])
            self.assertEqual(db.execute('SELECT operation_selection_sha256,state,expected_asset_count,processed_asset_count FROM product_detail_generation').fetchone(), ('e'*64,'completed',3,3))
            bindings = [(a,json.loads(b)['operationReceiptSha256']) for a,b in db.execute('SELECT r.asset_id,p.source_binding_json FROM product_detail_projection p JOIN retained_reference_record r USING(reference_record_id)')]
            self.assertTrue(all(op == ('e'*64 if asset=='fixture-off' else 'f'*64) for asset,op in bindings))
            coverage = json.loads(db.execute('SELECT coverage_scope_json FROM product_detail_generation').fetchone()[0])
            self.assertEqual(coverage['resumeAttempts'][0]['checkpointSha256'],store._hash(checkpoint))
            self.assertEqual(coverage['resumeAttempts'][0]['startedAfterAssetCount'],1)
            self.assertEqual(db.execute('PRAGMA foreign_keys').fetchone(),(1,)); self.usable(db)
            self.check_query(db)

    def check_query(self, detail, incomplete=False):
        from tests.test_product_detail_query import IDENTIFIER_SCHEMA
        from offmenu.refresh import product_detail_query as query
        with closing(sqlite3.connect(':memory:')) as index:
            index.executescript(IDENTIFIER_SCHEMA)
            index.execute('INSERT INTO fetch_asset VALUES(?)', ('generated-identifier-asset',))
            index.execute('INSERT INTO identifier_load VALUES(?,?)', ('fixture-run','completed'))
            observations=[]; operations=[]
            for number,asset in enumerate(('fixture-off','fixture-usda','fixture-C'),1):
                row=detail.execute("SELECT p.source_binding_json,i.namespace,i.lexical_value FROM retained_reference_record r JOIN product_detail_projection p USING(reference_record_id) JOIN product_detail_identifier i USING(reference_record_id) WHERE r.asset_id=? LIMIT 1",(asset,)).fetchone()
                if row is None:continue
                b=json.loads(row[0])
                obs=dict(run_id='fixture-run',assertion_id=number,disposition='source-asserted',
                    input_id=b['identifierInputId'],record_ordinal=b['identifierRecordOrdinal'],
                    namespace=row[1],lexical_value=row[2],source_id=b['sourceId'],release_id=b['releaseId'],
                    artifact_sha256=b['identifierAssetSha256'],native_record_id=b['identifierNativeRecordId'],
                    source_record_id=b['identifierSourceRecordId'])
                index.execute('INSERT OR IGNORE INTO identifier_input VALUES(?,?,?,?,?,?)',
                    (obs['run_id'],obs['input_id'],obs['source_id'],obs['release_id'],obs['artifact_sha256'],'generated-identifier-asset'))
                index.execute('INSERT INTO identifier_source_record VALUES(?,?,?,?,?)',
                    (obs['run_id'],obs['input_id'],obs['record_ordinal'],obs['source_record_id'],obs['native_record_id']))
                index.execute('INSERT INTO identifier_assertion VALUES(?,?,?,?,?,?,?)',
                    (obs['assertion_id'],obs['run_id'],obs['input_id'],obs['record_ordinal'],obs['namespace'],obs['lexical_value'],obs['disposition']))
                observations.append(obs);operations.append(b['operationReceiptSha256'])
            index.commit();index.execute('PRAGMA query_only=ON')
            generation=detail.execute('SELECT input_manifest_sha256,operation_selection_sha256 FROM product_detail_generation').fetchone()
            selection=query.ProductDetailQuerySelection('fixture-gen',generation[0],generation[1],'c'*64)
            evidence=query.CurrentIdentifierEvidence(index,'fixture-run','c'*64)
            if incomplete:
                with self.assertRaisesRegex(RefreshError,'query-unselected-generation'):
                    query.read_product_details(detail,observations,selection=selection,identifier_evidence=evidence)
                return
            before=detail.total_changes
            result=query.read_product_details(detail,observations,selection=selection,identifier_evidence=evidence)
            self.assertEqual([p['sourceBinding']['operationReceiptSha256'] for p in result['sourceProducts']],operations)
            self.assertEqual([p['state'] for p in result['productDetailAvailability']],['loaded']*3)
            self.assertEqual(result['operationSelectionSha256'],'e'*64)
            self.assertEqual(result['coverage']['scope']['resumeAttempts'][0]['operationSelectionSha256'],'f'*64)
            self.assertEqual(detail.total_changes,before)
            self.assertLessEqual(len(store.canonical(result)),262144)
            for product in result['sourceProducts']:
                self.assertEqual(product['exactObservationBridge']['state'],'matched')
                self.assertEqual(product['sourceBinding']['recordPointer'],product['sourceBinding']['recordPointers'][0])
            with self.assertRaisesRegex(RefreshError,'query-unselected-generation'):
                query.read_product_details(detail,[],selection=replace(selection,operation_selection_sha256='f'*64),identifier_evidence=evidence)

    def test_incomplete_query_refuses_selected_partial_prefix(self):
        self.prefix()
        with closing(sqlite3.connect(self.path)) as db:self.check_query(db,incomplete=True)

    def test_B_failure_preserves_A_and_C_failure_preserves_A_plus_B(self):
        checkpoint=self.prefix()
        with closing(sqlite3.connect(self.path)) as db:
            old=self.rows(db)
            def fail_B(asset, consume):
                self.assertNotEqual(asset['assetId'],'fixture-off')
                receipt=self.scan(asset,consume)
                return dict(receipt,bodyPasses=2)
            with self.assertRaisesRegex(RefreshError,'asset-receipt') as error:self.resume(db,checkpoint,scan=fail_B)
            self.assertEqual(self.rows(db),old); self.assertEqual(len(error.exception.product_detail_retained_state['completedAssets']),1)
            self.assertEqual(db.execute('SELECT count(*) FROM retained_reference_record').fetchone(),(4,));self.usable(db)
        checkpoint=self.select(operation='1'*64);self.scans.clear()
        with closing(sqlite3.connect(self.path)) as db:
            def fail_C(asset, consume):
                receipt=self.scan(asset,consume)
                if asset['assetId']=='fixture-C':raise RuntimeError('generated after provisional C')
                return receipt
            with self.assertRaisesRegex(RuntimeError,'provisional C') as error:self.resume(db,checkpoint,scan=fail_C,operation='1'*64)
            self.assertEqual(self.scans,['fixture-usda','fixture-C']);self.assertEqual(self.rows(db),old)
            self.assertEqual(db.execute('SELECT state,processed_asset_count,product_records,profile_records FROM product_detail_generation').fetchone(),('incomplete',2,3,3))
            self.assertEqual(len(error.exception.product_detail_retained_state['completedAssets']),2);self.usable(db)
        checkpoint=self.select(operation='2'*64);self.scans.clear()
        with closing(sqlite3.connect(self.path)) as db:
            B=self.rows(db,'fixture-usda');result=self.resume(db,checkpoint,operation='2'*64)
            self.assertEqual(self.scans,['fixture-C']);self.assertEqual(self.rows(db,'fixture-usda'),B)
            self.assertEqual(len(result['resumeAttempts']),3)

    def test_caller_transaction_rejected_before_any_SQL_and_FK_refusal_preserves_prefix(self):
        checkpoint=self.prefix()
        with closing(sqlite3.connect(self.path)) as db:
            db.execute('CREATE TEMP TABLE caller(value)');db.execute('INSERT INTO caller VALUES(1)');db.execute('SAVEPOINT caller_savepoint')
            statements=[];db.set_trace_callback(statements.append)
            with self.assertRaisesRegex(RefreshError,'caller-transaction-active'):self.resume(db,checkpoint)
            self.assertEqual(statements,[]);self.assertEqual(self.scans,[]);self.assertTrue(db.in_transaction)
            db.set_trace_callback(None);db.execute('ROLLBACK TO caller_savepoint');self.assertEqual(db.execute('SELECT * FROM caller').fetchall(),[(1,)])
            db.rollback()
        with closing(sqlite3.connect(self.path)) as db:
            old=self.rows(db)
            def deny(action,name,value,database,trigger):
                return sqlite3.SQLITE_IGNORE if action==sqlite3.SQLITE_PRAGMA and name=='foreign_keys' and value is not None else sqlite3.SQLITE_OK
            db.set_authorizer(deny)
            with self.assertRaisesRegex(RefreshError,'foreign-keys-required'):self.resume(db,checkpoint)
            self.assertEqual(self.rows(db),old);self.assertEqual(self.scans,[]);self.usable(db)

    def test_wrong_selection_closed_evidence_identity_and_journal_fail_without_mutation(self):
        checkpoint=self.prefix();original=self.path.read_bytes()
        changes=[{'producerTerminal':False},{'producerReaped':False},{'writableHandlesClosed':False},
            {'cleanJournalVerified':False},{'integrityAndForeignKeysVerified':False},{'state':'loading'},
            {'databaseIdentity':[0]*5},{'generationId':'wrong'},{'inputManifestSha256':'0'*64},
            {'identifierDatabaseSha256':'0'*64},{'originalOperationSelectionSha256':'0'*64},
            {'coverageSha256':'0'*64},{'resumeOperationSelectionSha256':'0'*64},
            {'committedReceipts':[dict(checkpoint['committedReceipts'][0],EOFFullyVerified=False)]}]
        for change in changes:
            with self.subTest(change=change),closing(sqlite3.connect(self.path)) as db:
                with self.assertRaises(RefreshError):self.resume(db,dict(checkpoint,**change))
                self.assertEqual(self.scans,[]);self.usable(db)
            self.assertEqual(self.path.read_bytes(),original)
        with closing(sqlite3.connect(self.path)) as db:
            with self.assertRaisesRegex(RefreshError,'checkpoint-selection'):
                store.resume_existing_product_details(db,self.assets,checkpoint_receipt=checkpoint,checkpoint_sha256='0'*64,**self.args())
        for suffix in ('-journal','-wal','-shm'):
            sidecar=Path(str(self.path)+suffix);sidecar.write_bytes(b'generated unsupported journal')
            # Open before sidecar creation in real callers; even a stale sidecar
            # is rejected by the API. Avoid SQLite's own open-time recovery here.
            with closing(sqlite3.connect(':memory:')) as db:
                with self.assertRaisesRegex(RefreshError,'checkpoint-journal'):self.resume(db,checkpoint)
            self.assertEqual(sidecar.read_bytes(),b'generated unsupported journal');sidecar.unlink()
        self.assertEqual(self.path.read_bytes(),original)

    def test_dirty_loading_and_contradictory_prefix_never_repair_or_scan(self):
        checkpoint=self.prefix()
        mutations=[("UPDATE product_detail_generation SET state='loading'",()),
            ("UPDATE product_detail_generation SET state='completed'",()),
            ("UPDATE product_detail_generation SET processed_asset_count=2",()),
            ("UPDATE product_detail_generation SET product_records=NULL",()),
            ("UPDATE product_detail_generation SET expected_asset_count='bad'",()),
            ("UPDATE product_detail_generation SET operation_selection_sha256=?",('0'*64,)),
            ("UPDATE product_detail_projection SET source_binding_json=json_set(source_binding_json,'$.operationReceiptSha256',?)",('0'*64,)),
            ("DELETE FROM product_detail_identifier",()),
            ("CREATE TABLE unselected(value)",())]
        pristine=self.path.read_bytes()
        for sql,params in mutations:
            with self.subTest(sql=sql):
                self.path.write_bytes(pristine)
                with closing(sqlite3.connect(self.path)) as db:db.execute(sql,params);db.commit()
                c=self.select();c['state']='incomplete'
                before=self.path.read_bytes()
                with closing(sqlite3.connect(self.path)) as db:
                    with self.assertRaises(RefreshError):self.resume(db,c)
                    self.assertEqual(self.scans,[]);self.usable(db)
                self.assertEqual(self.path.read_bytes(),before)
        self.path.write_bytes(pristine)
        # A forged reader-only progress row/prefix hole or duplicate is bound to
        # the receipt but must still contradict SQL/manifest order.
        for mode in ('hole','duplicate','reader-only'):
            with closing(sqlite3.connect(self.path)) as db:
                coverage=json.loads(db.execute('SELECT coverage_scope_json FROM product_detail_generation').fetchone()[0])
                if mode=='hole':coverage['assets'][0]['assetId']='fixture-usda'
                else:coverage['assets'].append(copy.deepcopy(coverage['assets'][0]))
                db.execute('UPDATE product_detail_generation SET coverage_scope_json=?,processed_asset_count=?',(store.canonical(coverage).decode(),len(coverage['assets'])));db.commit()
            c=self.select()
            with closing(sqlite3.connect(self.path)) as db:
                with self.assertRaises(RefreshError):self.resume(db,c)
                self.assertEqual(self.scans,[]);self.usable(db)
            self.path.write_bytes(pristine)

    def test_stale_selection_wrong_full_manifest_and_reused_operation_refuse(self):
        checkpoint=self.prefix()
        with closing(sqlite3.connect(self.path)) as db:
            for assets in (list(reversed(self.assets)),self.assets[1:],self.assets+[self.assets[0]]):
                with self.assertRaises(RefreshError):
                    store.resume_existing_product_details(db,assets,checkpoint_receipt=checkpoint,checkpoint_sha256=store._hash(checkpoint),**self.args())
            reused=dict(checkpoint,resumeOperationSelectionSha256='e'*64)
            with self.assertRaisesRegex(RefreshError,'operation-reuse'):self.resume(db,reused,operation='e'*64)
            self.assertEqual(self.scans,[])
            self.resume(db,checkpoint)
            self.scans.clear()
            with self.assertRaises(RefreshError):self.resume(db,checkpoint)
            self.assertEqual(self.scans,[])
            with self.assertRaisesRegex(RefreshError,'new-empty-store'):
                store.ingest_product_details(db,self.assets,**self.args())

    def test_limits_deadline_and_cleanup_preserve_committed_prefix(self):
        checkpoint=self.prefix()
        for limits in (replace(self.f.limits,max_records=1),replace(self.f.limits,max_assets=1),
            replace(self.f.limits,max_input_bytes=1),replace(self.f.limits,max_database_bytes=4096)):
            with self.subTest(limits=limits),closing(sqlite3.connect(self.path)) as db:
                old=self.rows(db)
                with self.assertRaises(RefreshError):self.resume(db,checkpoint,limits=limits)
                self.assertEqual(self.scans,[]);self.assertEqual(self.rows(db),old);self.usable(db)
        with closing(sqlite3.connect(self.path)) as db,patch.object(store.time,'monotonic',return_value=100.0) as clock:
            old=self.rows(db)
            def expire(asset,consume):
                receipt=self.scan(asset,consume);clock.return_value=1000.0;return receipt
            with self.assertRaisesRegex(RefreshError,'time-bound'):self.resume(db,checkpoint,scan=expire)
            self.assertEqual(self.rows(db),old);self.assertEqual(db.execute('SELECT processed_asset_count FROM product_detail_generation').fetchone(),(1,));self.usable(db)

    def test_reader_callback_failures_preserve_original_objects_and_input_validation(self):
        for asset in self.f.assets:
            for error in (RefreshError('generated-store-bound'),sqlite3.OperationalError('generated database full'),
                          ValueError('generated callback value'),RuntimeError('generated callback'),KeyboardInterrupt()):
                with self.subTest(source=asset['sourceId'],error=type(error).__name__):
                    def fail(*args):raise error
                    try:self.f.scan(asset,fail)
                    except BaseException as caught:self.assertIs(caught,error)
                    else:self.fail('callback failure swallowed')
        raw=self.f.native_path.read_bytes();self.f.native_path.write_bytes(raw.replace(b'milk',b'MILK'))
        with self.assertRaisesRegex(readers.NativeLookupError,'native-pair-hash-or-count'):
            self.f.scan(self.f.assets[1],lambda *args:None)
        self.f.native_path.write_bytes(b'\xff'+raw[1:])
        with self.assertRaisesRegex(readers.NativeLookupError,'native-pair-invalid-input'):
            self.f.scan(self.f.assets[1],lambda *args:None)

    def test_record_and_database_bounds_roll_back_B_and_leave_A_usable(self):
        for mode in ('record','database'):
            with self.subTest(mode=mode):
                checkpoint=self.prefix() if not self.path.exists() else self.select(operation='1'*64)
                operation=checkpoint['resumeOperationSelectionSha256']
                footprint=self.path.stat().st_size
                limits=replace(self.f.limits, max_record_bytes=4096) if mode=='record' else replace(self.f.limits,max_database_bytes=footprint)
                with closing(sqlite3.connect(self.path)) as db:
                    old=self.rows(db)
                    def large(asset,consume):
                        def inflated(packet,*coordinates):
                            packet=copy.deepcopy(packet);packet[0]['data']['generatedLarge']='x'*60000
                            consume(packet,*coordinates)
                        return self.scan(asset,inflated)
                    expected=RefreshError if mode=='record' else sqlite3.OperationalError
                    with self.assertRaises(expected):self.resume(db,checkpoint,scan=large,limits=limits,operation=operation)
                    self.assertEqual(self.rows(db),old)
                    self.assertEqual(db.execute('SELECT count(*) FROM retained_reference_record').fetchone(),(4,))
                    self.assertEqual(db.execute('SELECT processed_asset_count FROM product_detail_generation').fetchone(),(1,));self.usable(db)

    def test_all_committed_incomplete_checkpoint_finalizes_without_any_source_scan(self):
        with closing(sqlite3.connect(self.path)) as db,patch.object(store.time,'monotonic',return_value=100.0) as clock:
            final=[False]
            def trace(sql):
                if sql.startswith("UPDATE product_detail_generation SET state='completed'"):final[0]=True
                if final[0] and sql=='COMMIT':clock.return_value=1000.0
            db.set_trace_callback(trace)
            with self.assertRaisesRegex(RefreshError,'time-bound'):
                store.ingest_product_details(db,self.assets,**self.args(operation='e'*64))
            db.set_trace_callback(None)
        checkpoint=self.select();self.scans.clear()
        with closing(sqlite3.connect(self.path)) as db:
            old=[self.rows(db,a['assetId']) for a in self.assets]
            result=self.resume(db,checkpoint,scan=lambda *args:self.fail('no remaining source'))
            self.assertEqual(result['previouslyCompletedAssets'],3)
            self.assertEqual([self.rows(db,a['assetId']) for a in self.assets],old)
            self.assertEqual(self.scans,[])
            self.assertEqual(db.execute('SELECT exceptions_json,state FROM product_detail_generation').fetchone(),('[]','completed'))
            self.assertTrue(result['resumeAttempts'][0]['previousExceptions'])

    def test_failed_incomplete_update_leaves_loading_and_no_implicit_recovery(self):
        checkpoint=self.prefix()
        with closing(sqlite3.connect(self.path)) as db:
            def trace(sql):
                if sql.startswith("UPDATE product_detail_generation SET state='incomplete'"):
                    db.interrupt()
            db.set_trace_callback(trace)
            def fail(asset,consume):raise RuntimeError('generated asset failure')
            with self.assertRaises(sqlite3.OperationalError):self.resume(db,checkpoint,scan=fail)
            db.set_trace_callback(None);self.usable(db)
            self.assertEqual(db.execute('SELECT state,processed_asset_count FROM product_detail_generation').fetchone(),('loading',1))
        checkpoint=self.select();checkpoint['state']='incomplete'
        with closing(sqlite3.connect(self.path)) as db:
            with self.assertRaisesRegex(RefreshError,'checkpoint-generation'):self.resume(db,checkpoint)
            self.assertEqual(db.execute('SELECT state FROM product_detail_generation').fetchone(),('loading',));self.assertEqual(self.scans,[])


if __name__=='__main__':unittest.main()
