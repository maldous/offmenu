"""Generated owned databases only; no corpus, original files, AI or network."""
import hashlib
import json
from pathlib import Path
import sqlite3
import sys
import tempfile
import threading
import time
import unittest
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import normalization_reconciliation_engine as engine
from normalization_core import CompactNormalizationStore, canonical_json, digest, run_rules
from normalization_reconciliation import ReconciliationStore
from ingest_store import SCHEMA

class ReconciliationEngineTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.root=Path(self.temp.name)
        self.options={'disk_reserve_bytes':0,'batch_rows':4,'sample_rows':2,'max_rows':50,'report_interval':.001}
    def seed(self,domain,payloads=()):
        path=self.root/'staging'/(domain+'.sqlite3');path.parent.mkdir(exist_ok=True)
        db=sqlite3.connect(path);db.executescript(SCHEMA)
        for k,v in {'domain':domain,'binding':'additive_staging_not_app_bound','schema_version':'1','database_id':domain,'record_count':str(len(payloads))}.items():db.execute('INSERT INTO ingest_meta VALUES(?,?)',(k,v))
        db.execute('INSERT INTO sources VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)',('source','v1','/ABSENT-NEVER-OPEN','json','fixture','unverified','{}','{}','complete',0,0,0,1))
        entries=[]
        for i,payload in enumerate(payloads):
            rid='r'+str(i);db.execute('INSERT INTO records VALUES(?,?,?,?,?,?,?)',('source','v1',rid,1,digest(payload),canonical_json(payload),1))
            record={'domain':domain,'source_key':'source','source_version':'v1','record_id':rid,'content_sha256':digest(payload),'payload':payload,'row_number':1,
                'provenance':{'license':'unverified','provider':'fixture','custody':{},'rights_status':'unverified'}}
            entries.append(CompactNormalizationStore.encode(run_rules(record)))
        db.commit();db.close()
        with CompactNormalizationStore(self.root,domain) as cache:
            cache.db.executemany('INSERT INTO rules_cache VALUES(?,?,?,?)',entries);cache.db.commit()
        return sorted(entry[0] for entry in entries)
    def all_domains(self):
        for domain in engine.PUBLIC_DOMAINS:
            if not (self.root/'staging'/(domain+'.sqlite3')).exists():self.seed(domain)
    def run_engine(self,**opts):return engine.run_reconciliation(self.root,{**self.options,**opts})
    def output(self):return engine.prepare_default(self.root,self.options)['output_path']
    def test_six_public_domains_db_only_no_source_cache_mutations_or_workers(self):
        for domain in engine.PUBLIC_DOMAINS:
            p={'name':'fixture','language':'en'}
            if domain=='recipes':p.update(id='recipe',kind='recipe',ingredients=[],steps=[])
            if domain=='barcodes':p['barcode']='012345678905'
            self.seed(domain,[p])
        before={p:hashlib.sha256(p.read_bytes()).hexdigest() for p in (self.root/'staging').glob('*.sqlite3')}
        before.update({p:hashlib.sha256(p.read_bytes()).hexdigest() for p in (self.root/'normalization-private').glob('compact-*.sqlite3')})
        with patch('socket.socket',side_effect=AssertionError('network')),patch('normalization_parallel.RulesExecutor',side_effect=AssertionError('new rules dispatch')),patch.object(ReconciliationStore,'report',side_effect=AssertionError('COUNT scan')):report=self.run_engine()
        self.assertEqual(report['status'],'cache_complete');self.assertEqual(set(report['domains']),set(engine.PUBLIC_DOMAINS))
        self.assertTrue(all(r['scanned']==r['indexed_new']==1 for r in report['domains'].values()))
        self.assertTrue(all(r['selected_keys'] is None for r in report['domains'].values()))
        self.assertEqual(report['entity_merges'],0);self.assertEqual(report['gold_status'],'blocked');self.assertEqual(before,{p:hashlib.sha256(p.read_bytes()).hexdigest() for p in before})
        self.assertNotIn('ABSENT',json.dumps(report));self.assertNotIn('fixture',json.dumps(report))
    def test_row_cap_resume_repeat_no_integrity_replay(self):
        self.seed('ingredients',[{'name':str(i)} for i in range(5)]);self.all_domains()
        first=self.run_engine(max_rows=2);self.assertEqual(first['stop_reason'],'row_cap');self.assertEqual(first['domains']['ingredients']['scanned'],2)
        second=self.run_engine();self.assertEqual(second['domains']['ingredients']['scanned'],5)
        with patch.object(engine,'ingest_cache_keys',side_effect=AssertionError('historical replay')):third=self.run_engine()
        self.assertEqual(third['domains'],second['domains']);self.assertEqual(third['resources']['invocation_rows'],0);self.assertGreater(third['resources']['output_logical_bytes'],0);self.assertEqual(third['resources']['output_logical_bytes'],second['resources']['output_logical_bytes'])
    def test_bad_key_quarantine_continues_and_changed_cache_retries(self):
        keys=self.seed('ingredients',[{'name':str(i)} for i in range(3)]);self.all_domains();bad=keys[1]
        with CompactNormalizationStore(self.root,'ingredients') as cache:
            original=cache.db.execute('SELECT body_zlib FROM rules_cache WHERE cache_key=?',(bad,)).fetchone()[0]
            cache.db.execute('UPDATE rules_cache SET body_zlib=? WHERE cache_key=?',(b'bad-zlib',bad));cache.db.commit()
        first=self.run_engine(sample_rows=3);row=first['domains']['ingredients']
        self.assertEqual((row['scanned'],row['indexed_new'],row['quarantined']),(3,2,1));self.assertTrue(row['exhausted']);self.assertEqual(first['status'],'partial');self.assertEqual(first['capacity']['sample_rows'],2)
        with CompactNormalizationStore(self.root,'ingredients') as cache:cache.db.execute('UPDATE rules_cache SET body_zlib=? WHERE cache_key=?',(original,bad));cache.db.commit()
        second=self.run_engine(sample_rows=3);row=second['domains']['ingredients']
        self.assertEqual((row['scanned'],row['indexed_new'],row['indexed_reused'],row['quarantined'],row['quarantine_retries']),(3,1,2,0,1));self.assertEqual(second['status'],'cache_complete')
        with sqlite3.connect(self.output()) as db:self.assertEqual(db.execute('SELECT attempts,reason FROM engine_quarantine').fetchall(),[(1,'invalid_cache_or_source')])
    def test_explicit_retry_generation_retries_only_held_keys(self):
        keys=self.seed('ingredients',[{'name':'a'},{'name':'b'}]);self.all_domains()
        with CompactNormalizationStore(self.root,'ingredients') as cache:cache.db.execute('UPDATE rules_cache SET body_zlib=? WHERE cache_key=?',(b'bad',keys[0]));cache.db.commit()
        first=self.run_engine();second=self.run_engine(retry_generation=1)
        row=second['domains']['ingredients'];self.assertNotEqual(first['input_sha256'],second['input_sha256'])
        self.assertEqual((row['indexed_reused'],row['quarantined'],row['quarantine_retries']),(1,1,1))
    def test_memory_fault_stops_without_quarantine_or_cursor(self):
        self.seed('barcodes',[{'barcode':'bad'}]*3);self.all_domains()
        with patch.object(engine,'ingest_cache_keys',side_effect=MemoryError):report=self.run_engine()
        self.assertEqual(report['stop_reason'],'resource_failure');self.assertEqual(sum(r['scanned'] for r in report['domains'].values()),0)
        with sqlite3.connect(self.output()) as db:self.assertIsNone(db.execute('SELECT 1 FROM artifacts LIMIT 1').fetchone());self.assertIsNone(db.execute('SELECT 1 FROM engine_quarantine LIMIT 1').fetchone())
    def test_actual_sqlite_full_output_cap_rolls_back_facts_cursor_and_tail(self):
        self.seed('barcodes',[{'barcode':'bad'}]*3);self.all_domains();original=ReconciliationStore._project
        def huge(store,artifact,sha):
            original(store,artifact,sha);store.db.execute('INSERT INTO nodes VALUES(?,?,?,?,?)',('fixture-cap','test','test','test','x'*(2*1024**2)))
        with patch.object(ReconciliationStore,'_project',huge):report=self.run_engine(max_output_bytes=1024**2)
        self.assertEqual(report['stop_reason'],'output_cap');self.assertEqual(sum(r['scanned'] for r in report['domains'].values()),0)
        self.assertLessEqual(report['resources']['output_logical_bytes'],1024**2)
        with sqlite3.connect(self.output()) as db:
            for table in ('artifacts','engine_progress','engine_quarantine'):self.assertIsNone(db.execute('SELECT 1 FROM '+table+' LIMIT 1').fetchone())
    def test_actual_sample_admits_bounded_invocation_not_source_denominator(self):
        self.seed('ingredients',[{'name':str(i)} for i in range(20)]);self.all_domains()
        report=self.run_engine(max_output_bytes=1024**2)
        self.assertEqual(report['stop_reason'],'capacity_limit');self.assertEqual(report['capacity']['sample_rows'],2)
        self.assertGreater(report['capacity']['sample_output_bytes'],0);self.assertLess(report['capacity']['admitted_rows'],50)
        self.assertEqual(report['resources']['invocation_rows'],report['capacity']['admitted_rows'])
        self.assertIsNone(report['domains']['ingredients']['selected_keys'])
    def test_low_disk_no_creation_then_preserves_committed_prefix(self):
        self.seed('barcodes',[{'barcode':'bad'}]*4);self.all_domains()
        with patch.object(engine.shutil,'disk_usage',return_value=type('Usage',(),{'free':1})()):first=self.run_engine(disk_reserve_bytes=2)
        self.assertEqual(first['stop_reason'],'disk_reserve');self.assertFalse(self.output().exists())
        self.run_engine(max_rows=2)
        with patch.object(engine.shutil,'disk_usage',return_value=type('Usage',(),{'free':1})()):second=self.run_engine(disk_reserve_bytes=2)
        self.assertEqual(second['stop_reason'],'disk_reserve');self.assertEqual(second['domains']['barcodes']['scanned'],2)
    def test_interrupt_after_commit_then_resume(self):
        self.seed('barcodes',[{'barcode':'bad'}]*4);self.all_domains()
        def interrupt(report):
            if report['domains']['barcodes']['scanned']>=2:raise KeyboardInterrupt()
        with self.assertRaises(KeyboardInterrupt):engine.run_reconciliation(self.root,self.options,interrupt)
        self.assertEqual(self.run_engine()['domains']['barcodes']['scanned'],4)
    def test_callback_value_error_cannot_replay_committed_batch(self):
        self.seed('barcodes',[{'barcode':'bad'}]*4);self.all_domains();calls=[]
        def fail(report):
            if report['domains']['barcodes']['scanned']>=2:
                calls.append(report['domains']['barcodes']['scanned'])
                if len(calls)==1:raise ValueError('fixture callback')
        result=engine.run_reconciliation(self.root,self.options,fail)
        self.assertEqual(result['domains']['barcodes']['scanned'],2);self.assertEqual(result['stop_reason'],'store_unavailable')
        self.assertEqual(self.run_engine()['domains']['barcodes']['scanned'],4)
    def test_cancel_deadline_and_source_change_rollback_uncommitted_batch(self):
        self.seed('barcodes',[{'barcode':'bad'}]);self.all_domains();original=engine.ingest_cache_keys;event=threading.Event()
        def cancelled(*args,**kw):event.set();return original(*args,**kw)
        with patch.object(engine,'ingest_cache_keys',cancelled):report=self.run_engine(cancelled=event)
        self.assertEqual(report['stop_reason'],'cancelled');self.assertEqual(report['domains']['barcodes']['scanned'],0)
        def slow(*args,**kw):time.sleep(.04);return original(*args,**kw)
        with patch.object(engine,'ingest_cache_keys',slow):report=self.run_engine(max_seconds=.025)
        self.assertEqual(report['stop_reason'],'wall_time_cap');self.assertEqual(report['domains']['barcodes']['scanned'],0)
        def mutate(*args,**kw):
            with sqlite3.connect(self.root/'staging/barcodes.sqlite3') as db:db.execute('UPDATE records SET updated_at=2')
            return original(*args,**kw)
        with patch.object(engine,'ingest_cache_keys',mutate):report=self.run_engine()
        self.assertEqual(report['stop_reason'],'snapshot_changed');self.assertEqual(report['domains']['barcodes']['scanned'],0)
    def test_missing_private_inputs_never_selected_and_empty_known_cache(self):
        self.seed('ingredients');report=self.run_engine()
        self.assertEqual(report['domains']['ingredients']['status'],'cache_complete');self.assertEqual(report['status'],'partial')
        self.assertEqual(report['domains']['recipes']['status'],'unavailable');self.assertNotIn('inventory',report['domains'])
    def test_new_cache_key_below_cursor_resets_discovery_without_replaying_receipts(self):
        keys=self.seed('ingredients',[{'name':str(i)} for i in range(3)]);self.all_domains()
        first=self.run_engine(max_rows=1);self.assertEqual(first['domains']['ingredients']['scanned'],1)
        for i in range(512):
            payload={'name':'new-'+str(i)}
            record={'domain':'ingredients','source_key':'source','source_version':'v1','record_id':'new','content_sha256':digest(payload),'payload':payload,'row_number':1,
                'provenance':{'license':'unverified','provider':'fixture','custody':{},'rights_status':'unverified'}}
            entry=CompactNormalizationStore.encode(run_rules(record))
            if entry[0]<keys[0]:break
        self.assertLess(entry[0],keys[0])
        db=sqlite3.connect(self.root/'staging/ingredients.sqlite3')
        db.execute('INSERT INTO records VALUES(?,?,?,?,?,?,?)',('source','v1','new',1,digest(payload),canonical_json(payload),1));db.commit();db.close()
        with CompactNormalizationStore(self.root,'ingredients') as cache:cache.db.execute('INSERT INTO rules_cache VALUES(?,?,?,?)',entry);cache.db.commit()
        second=self.run_engine();row=second['domains']['ingredients']
        self.assertNotEqual(first['input_sha256'],second['input_sha256'])
        self.assertEqual((row['scanned'],row['indexed_new'],row['indexed_reused']),(4,3,1));self.assertEqual(second['status'],'cache_complete')
    def test_checkpoint_insert_failure_rolls_back_graph_receipts_atomically(self):
        self.seed('ingredients',[{'name':'a'},{'name':'b'}]);self.all_domains()
        with ReconciliationStore(self.output(),disk_reserve_bytes=0) as graph:
            graph.db.executescript(engine._ENGINE_SQL)
            graph.db.execute('INSERT INTO engine_meta VALUES(?,?)',('binding',engine.ENGINE_VERSION))
            graph.db.execute("CREATE TRIGGER abort_progress BEFORE INSERT ON engine_progress WHEN NEW.domain='ingredients' BEGIN SELECT RAISE(ABORT,'fixture'); END");graph.db.commit()
        first=self.run_engine();self.assertEqual(first['domains']['ingredients']['scanned'],0)
        with sqlite3.connect(self.output()) as db:
            self.assertIsNone(db.execute('SELECT 1 FROM artifacts LIMIT 1').fetchone())
            self.assertIsNone(db.execute("SELECT 1 FROM engine_progress WHERE domain='ingredients'").fetchone())
            self.assertIsNone(db.execute('SELECT 1 FROM engine_quarantine LIMIT 1').fetchone())
            db.execute('DROP TRIGGER abort_progress')
        self.assertEqual(self.run_engine()['domains']['ingredients']['scanned'],2)
    def test_completed_reuse_rechecks_prepared_snapshot_and_owned_binding(self):
        self.seed('ingredients',[{'name':'a'}]);self.all_domains();self.run_engine()
        prepared=engine.prepare_default(self.root,self.options)
        with CompactNormalizationStore(self.root,'ingredients') as cache:cache.db.execute("INSERT INTO compact_meta VALUES('fixture_change','1')");cache.db.commit()
        changed=engine.run_prepared(prepared)
        self.assertEqual(changed['stop_reason'],'snapshot_changed');self.assertNotEqual(changed['status'],'cache_complete')
        self.assertFalse(changed['domains']['ingredients']['exhausted'])
        self.assertEqual(self.run_engine()['status'],'cache_complete')
        with sqlite3.connect(self.output()) as db:db.execute("UPDATE engine_meta SET value='foreign' WHERE key='binding'")
        foreign=self.run_engine();self.assertEqual(foreign['stop_reason'],'store_unavailable');self.assertNotEqual(foreign['status'],'cache_complete')
    def test_reports_validate_strict_public_contract(self):
        from normalization_reconciliation_receipts import validate_report
        self.seed('barcodes',[{'barcode':'bad'}]);self.all_domains();reports=[]
        result=engine.run_reconciliation(self.root,self.options,lambda value:reports.append(value))
        for report in reports:validate_report(report)
        validate_report(result)

if __name__=='__main__':unittest.main()
