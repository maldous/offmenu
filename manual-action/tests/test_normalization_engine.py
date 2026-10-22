"""Generated SQLite fixtures only; no corpus/originals/AI/network."""
import json
from pathlib import Path
import sqlite3
import sys
import tempfile
import threading
import unittest
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import normalization_engine as engine
from normalization_core import CompactNormalizationStore,artifact_digest,canonical_json,digest,run_rules
from normalization_api import NormalizationError
from ingest_store import SCHEMA
from normalization_parallel import RulesBatchLimitError, RulesWorkerError

class InlineRules:
    def __init__(self,workers=1,**kwargs):self.workers=workers;self.actual_workers=0;self.check=kwargs['check_cancel']
    def __enter__(self):return self
    def __exit__(self,*args):pass
    def run_batch(self,records,versions=None):
        out=[];self.actual_workers=1
        for record in records:
            self.check();source={k:record[k] for k in ('domain','source_key','source_version','record_id','content_sha256')}
            try:
                artifact=run_rules(record,versions=versions);sha=artifact_digest(artifact);del artifact['source_original']
                out.append({'source':source,'artifact':artifact,'artifact_sha256':sha,'error_code':None})
            except (ValueError,TypeError):out.append({'source':source,'artifact':None,'artifact_sha256':None,'error_code':'rules_validation_error'})
        return out

class DatabaseNormalizationTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.root=Path(self.temp.name)
        self.options={'workers':1,'disk_reserve_bytes':0,'batch_rows':2,'report_interval':.001}
        self.pool=patch('normalization_parallel.RulesExecutor',InlineRules);self.pool.start();self.addCleanup(self.pool.stop)
    def db(self,domain,rows=(),source=True):
        path=self.root/'staging'/(domain+'.sqlite3');path.parent.mkdir(exist_ok=True)
        with sqlite3.connect(path) as db:
            db.executescript(SCHEMA)
            for k,v in {'domain':domain,'binding':'additive_staging_not_app_bound','schema_version':'1','database_id':domain,'record_count':str(len(rows))}.items():db.execute('INSERT INTO ingest_meta VALUES(?,?)',(k,v))
            for i,row in enumerate(rows):
                key,version,rid,payload=row if isinstance(row,tuple) else ('source','v1','r'+str(i),row)
                if source:db.execute('INSERT OR IGNORE INTO sources VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)',(key,version,'/ABSENT-ORIGINAL-DO-NOT-OPEN','json','fixture','unverified','{}','{}','complete',0,0,0,1))
                db.execute('INSERT INTO records VALUES(?,?,?,?,?,?,?)',(key,version,rid,1,digest(payload),canonical_json(payload),1))
        return path
    def empties(self):
        for domain in engine.PUBLIC_DOMAINS:
            if not (self.root/'staging'/(domain+'.sqlite3')).exists():self.db(domain)
    def run_engine(self,**options):return engine.run_normalization(self.root,{**self.options,**options})
    def test_public_db_only_no_originals_source_unchanged(self):
        for domain in engine.PUBLIC_DOMAINS:
            payload={'id':'one','name':'Fixture','language':'en','kind':'recipe','ingredients':[],'steps':[]} if domain=='recipes' else {'id':'one','name':'Fixture','language':'en'}
            self.db(domain,[payload])
        (self.root/'private-household').mkdir();(self.root/'private-household'/'MUST-NOT-READ').write_text('private')
        before={p:p.read_bytes() for p in (self.root/'staging').iterdir()}
        with patch('socket.socket',side_effect=AssertionError('network forbidden')):report=self.run_engine()
        self.assertEqual(set(report['domains']),set(engine.PUBLIC_DOMAINS));self.assertEqual(report['status'],'rules_complete')
        self.assertTrue(all(r['scanned']==r['pendingreview']==1 for r in report['domains'].values()))
        self.assertTrue(all(r['accepted']==r['rejected']==r['needs_changes']==0 for r in report['domains'].values()))
        self.assertEqual(report['gold_status'],'blocked');self.assertEqual(report['review_status'],'pending_approved_route')
        self.assertNotIn('ABSENT',json.dumps(report));self.assertNotIn('Fixture',json.dumps(report))
        self.assertEqual(before,{p:p.read_bytes() for p in before})
    def test_pk_ties_all_versions_resume_without_historical_replay(self):
        self.db('ingredients',[('s','v1',f'{i:03}',{'name':str(i)}) for i in range(5)]+[('s','v2','000',{'name':'v2'})]);self.empties()
        first=self.run_engine(max_rows=2);self.assertEqual(first['stop_reason'],'row_cap');self.assertEqual(first['domains']['ingredients']['scanned'],2)
        second=self.run_engine();self.assertEqual(second['domains']['ingredients']['scanned'],6);self.assertEqual(second['domains']['ingredients']['rules_new'],6)
        with patch.object(InlineRules,'run_batch',side_effect=AssertionError('historical replay')):third=self.run_engine()
        self.assertEqual(third['domains'],second['domains']);self.assertEqual(third['resources']['workers'],0)
    def test_changed_content_behind_cursor_and_rule_version_invalidates(self):
        path=self.db('ingredients',[('s','v1','a',{'name':'old'}),('s','v1','z',{'name':'same'})]);self.empties();first=self.run_engine()
        with sqlite3.connect(path) as db:
            payload={'name':'changed'};db.execute('UPDATE records SET payload_json=?,content_sha256=? WHERE record_id=?',(canonical_json(payload),digest(payload),'a'))
        second=self.run_engine();self.assertNotEqual(first['input_sha256'],second['input_sha256']);row=second['domains']['ingredients']
        self.assertEqual((row['rules_new'],row['rules_reused'],row['scanned']),(1,1,2))
        self.assertEqual(self.run_engine(versions={'rule_version':'fixture-v2'})['domains']['ingredients']['rules_new'],2)
    def test_orphans_bad_json_hash_and_missing_recipe_fields_are_per_record(self):
        path=self.db('ingredients',[{'name':'orphan'},{'name':'mismatch'},{'name':'bad-json'}],source=False)
        self.db('recipes',[{'title':'missing kind/id'},{'id':'valid','kind':'menu','title':'Menu'}]);self.empties()
        with sqlite3.connect(path) as db:
            db.execute("UPDATE records SET content_sha256=? WHERE record_id='r1'",('0'*64,));db.execute("UPDATE records SET payload_json='not json' WHERE record_id='r2'")
        report=self.run_engine();row=report['domains']['ingredients'];self.assertEqual((row['scanned'],row['rules_new'],row['failed'],row['unresolved']),(3,1,2,3))
        self.assertEqual(report['domains']['recipes']['failed'],1);self.assertEqual(report['domains']['recipes']['pendingreview'],1)
    def test_prepared_snapshot_change_stops_without_projection(self):
        path=self.db('barcodes',[{'barcode':'bad'}]);self.empties();prepared=engine.prepare_default(self.root,self.options)
        with sqlite3.connect(path) as db:db.execute('UPDATE records SET updated_at=2')
        with patch.object(InlineRules,'run_batch',side_effect=AssertionError('stale snapshot')):report=engine.run_prepared(prepared)
        self.assertEqual(report['stop_reason'],'snapshot_changed');self.assertEqual(sum(r['scanned'] for r in report['domains'].values()),0)
    def test_disk_stop_once_and_cancel_resumes_committed_prefix(self):
        self.db('barcodes',[{'barcode':'bad'} for _ in range(5)]);self.empties()
        with patch('normalization_engine.shutil.disk_usage',return_value=type('Usage',(),{'free':1})()):stopped=self.run_engine(disk_reserve_bytes=2)
        self.assertEqual(stopped['stop_reason'],'disk_reserve');self.assertFalse((self.root/'normalization-private').exists())
        event=threading.Event()
        def callback(report):
            if report['domains']['barcodes']['scanned']>=2:event.set()
        report=engine.run_normalization(self.root,{**self.options,'cancelled':event},callback)
        self.assertEqual(report['stop_reason'],'cancelled');self.assertEqual(report['domains']['barcodes']['scanned'],2)
        self.assertEqual(self.run_engine()['domains']['barcodes']['scanned'],5)
    def test_compact_queue_no_raw_copy_and_exact_bound_resolution(self):
        payload={'name':'Projected','unprojected':'NEVER-COPIED-RAW-SENTINEL'};self.db('ingredients',[payload]);self.empties();self.run_engine()
        with CompactNormalizationStore(self.root,'ingredients') as store:
            key,=store.db.execute('SELECT cache_key FROM review_refs').fetchone();body,_=store.get_compact(key)
            self.assertNotIn('source_original',body);self.assertNotIn('NEVER-COPIED',json.dumps(body))
            self.assertEqual([c[1] for c in store.db.execute('PRAGMA table_info(review_refs)')],['cache_key','artifact_sha256','status'])
            record={'domain':'ingredients','source_key':'source','source_version':'v1','record_id':'r0','content_sha256':digest(payload),'payload':payload,'provenance':{'license':'unverified','provider':'fixture','custody':{},'rights_status':'unverified'}}
            self.assertEqual(store.resolve(key,record)['source_original'],payload)
            record['payload']={'name':'mutated'};record['content_sha256']=digest(record['payload'])
            with self.assertRaisesRegex(NormalizationError,'stale_database'):store.resolve(key,record)
    def test_atomic_rollback_cache_queue_and_checkpoint(self):
        self.db('ingredients',[{'name':'a'},{'name':'b'}]);self.empties();prepared=engine.prepare_default(self.root,self.options)
        with CompactNormalizationStore(self.root,'ingredients') as store:
            store.db.execute("CREATE TRIGGER stop_progress BEFORE INSERT ON progress BEGIN SELECT RAISE(ABORT,'fixture'); END");store.db.commit()
        report=engine.run_prepared(prepared);self.assertEqual(report['domains']['ingredients']['scanned'],0)
        with CompactNormalizationStore(self.root,'ingredients') as store:
            self.assertIsNone(store.db.execute('SELECT cache_key FROM rules_cache LIMIT 1').fetchone());self.assertIsNone(store.db.execute('SELECT cache_key FROM review_refs LIMIT 1').fetchone());self.assertIsNone(store.checkpoint(prepared['domains']['ingredients']['snapshot_key']))
            store.db.execute('DROP TRIGGER stop_progress');store.db.commit()
        self.assertEqual(self.run_engine()['domains']['ingredients']['scanned'],2)
    def test_output_overflow_retries_bounded_smaller_pages(self):
        self.db('ingredients',[{'name':str(i)} for i in range(5)]);self.empties();original=InlineRules.run_batch;sizes=[]
        def bounded(instance,records,versions=None):
            sizes.append(len(records))
            if len(records)>1:raise RulesBatchLimitError('rules_batch_output_limit')
            return original(instance,records,versions)
        with patch.object(InlineRules,'run_batch',bounded):report=self.run_engine(batch_rows=4)
        self.assertEqual(report['domains']['ingredients']['scanned'],5);self.assertEqual(report['domains']['ingredients']['rules_new'],5);self.assertEqual(sizes[:3],[4,2,1])
    def test_indexed_sql_no_count_and_missing_db_not_complete(self):
        path=self.db('ingredients',[{'name':'fixture'}])
        with sqlite3.connect(path) as db:plan=' '.join(str(row) for row in db.execute('EXPLAIN QUERY PLAN '+engine._QUERY,(1024,1024,'','','',2)))
        self.assertNotIn('TEMP B-TREE',plan);self.assertNotIn('COUNT(',engine._QUERY.upper());report=self.run_engine()
        self.assertEqual(report['status'],'partial');self.assertEqual(report['domains']['recipes']['status'],'unavailable')
    def test_interrupt_after_commit_keeps_prefix_and_resume(self):
        self.db('barcodes',[{'barcode':'bad'} for _ in range(5)]);self.empties()
        def interrupt(report):
            if report['domains']['barcodes']['scanned']>=2:raise KeyboardInterrupt()
        with self.assertRaises(KeyboardInterrupt):engine.run_normalization(self.root,self.options,interrupt)
        resumed=self.run_engine();self.assertEqual(resumed['domains']['barcodes']['scanned'],5)
        self.assertEqual(resumed['domains']['barcodes']['rules_new'],5)
    def test_deadline_discards_uncommitted_worker_results(self):
        import time
        self.db('barcodes',[{'barcode':'bad'}]);self.empties();original=InlineRules.run_batch
        def slow(instance,records,versions=None):
            result=original(instance,records,versions);time.sleep(.04);return result
        with patch.object(InlineRules,'run_batch',slow):report=self.run_engine(max_seconds=.025)
        self.assertEqual(report['stop_reason'],'wall_time_cap');self.assertEqual(report['domains']['barcodes']['scanned'],0)
        self.assertEqual(self.run_engine()['domains']['barcodes']['scanned'],1)
    def test_oversize_database_payload_is_unresolved_not_materialized_to_worker(self):
        self.db('ingredients',[{'unused':'x'*20000},{'name':'small'}]);self.empties()
        report=self.run_engine(batch_bytes=16384);row=report['domains']['ingredients']
        self.assertEqual((row['scanned'],row['failed'],row['rules_new']),(2,1,1))
    def test_wal_snapshot_ignores_reader_shm_metadata(self):
        import os
        path=self.db('barcodes',[{'barcode':'bad'}]);self.empties()
        writer=sqlite3.connect(path);self.addCleanup(writer.close)
        writer.execute('PRAGMA journal_mode=WAL');writer.execute('UPDATE records SET updated_at=3');writer.commit()
        prepared=engine.prepare_default(self.root,self.options)
        shm=Path(str(path)+'-shm');os.utime(shm,None)
        before={p:p.read_bytes() for p in (path,Path(str(path)+'-wal'))}
        report=engine.run_prepared(prepared)
        self.assertEqual(report['status'],'rules_complete');self.assertEqual(before,{p:p.read_bytes() for p in before})
        self.assertEqual(engine.prepare_default(self.root,self.options)['input_sha256'],prepared['input_sha256'])
    def test_empty_identity_is_accounted_not_skipped_by_initial_cursor(self):
        self.db('ingredients',[('','','',{'name':'invalid identity'})]);self.empties()
        row=self.run_engine()['domains']['ingredients'];self.assertEqual((row['scanned'],row['failed']),(1,1))
    def test_corrupt_checkpoint_is_not_publicly_forwarded(self):
        self.db('ingredients',[{'name':'a'}]);self.empties();self.run_engine()
        with CompactNormalizationStore(self.root,'ingredients') as store:
            store.db.execute("UPDATE progress SET counters_json=?",(json.dumps({'private_path':'DO-NOT-REPORT'}),));store.db.commit()
        report=self.run_engine();self.assertNotIn('DO-NOT-REPORT',json.dumps(report))
        self.assertEqual(report['domains']['ingredients']['status'],'unavailable')
    def test_larger_admission_cap_retries_prior_oversize_record(self):
        self.db('ingredients',[{'name':'large','unused':'x'*20000}]);self.empties()
        first=self.run_engine(batch_bytes=16384);self.assertEqual(first['domains']['ingredients']['failed'],1)
        second=self.run_engine(batch_bytes=65536)
        self.assertNotEqual(first['input_sha256'],second['input_sha256'])
        self.assertEqual((second['domains']['ingredients']['failed'],second['domains']['ingredients']['rules_new']),(0,1))
    def test_worker_resource_failure_stops_once_without_unread_failures(self):
        self.db('barcodes',[{'barcode':'bad'} for _ in range(5)]);self.db('ingredients',[{'name':'unread'}]);self.empties()
        with patch.object(InlineRules,'run_batch',side_effect=RulesWorkerError('rules_worker_resource_failure')):report=self.run_engine()
        self.assertEqual(report['stop_reason'],'worker_resource_failure')
        self.assertEqual(sum(r['scanned'] for r in report['domains'].values()),0)
        self.assertEqual(sum(r['failed'] for r in report['domains'].values()),0)
        self.assertEqual(self.run_engine()['domains']['barcodes']['scanned'],5)
    def test_low_disk_repeat_preserves_durable_progress_without_writes(self):
        self.db('barcodes',[{'barcode':'bad'} for _ in range(5)]);self.empties()
        first=self.run_engine(max_rows=2);self.assertEqual(first['domains']['barcodes']['scanned'],2)
        with patch('normalization_engine.shutil.disk_usage',return_value=type('Usage',(),{'free':1})()):second=self.run_engine(disk_reserve_bytes=2)
        self.assertEqual(second['stop_reason'],'disk_reserve');self.assertEqual(second['domains']['barcodes']['scanned'],2)
        completed=self.run_engine()
        with patch('normalization_engine.shutil.disk_usage',return_value=type('Usage',(),{'free':1})()):repeat=self.run_engine(disk_reserve_bytes=2)
        self.assertEqual(repeat['status'],'rules_complete');self.assertIsNone(repeat['stop_reason']);self.assertEqual(repeat['domains'],completed['domains'])
    def test_long_unresolved_identity_resumes_and_is_charged_by_bytes(self):
        long_id='a'+'界'*10000
        self.db('ingredients',[('s','v1',long_id,{'name':'invalid identity'}),('s','v1','z',{'name':'next'})]);self.empties()
        original=engine._Budget.space;margins=[]
        def observe(budget,required=0,**kwargs):
            margins.append(required);return original(budget,required,**kwargs)
        with patch.object(engine._Budget,'space',observe):first=self.run_engine(batch_rows=1,max_rows=1)
        row=first['domains']['ingredients'];self.assertEqual((row['scanned'],row['failed']),(1,1));self.assertEqual(first['stop_reason'],'row_cap')
        self.assertGreater(max(margins),1024**2+8*len(long_id.encode('utf-8')))
        second=self.run_engine(batch_rows=1);row=second['domains']['ingredients']
        self.assertEqual((row['scanned'],row['failed'],row['rules_new']),(2,1,1));self.assertNotEqual(row['status'],'unavailable')
        self.assertNotIn(long_id,json.dumps(second));self.assertEqual(self.run_engine()['domains'],second['domains'])
if __name__=='__main__':unittest.main()
