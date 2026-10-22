import json
import os
from pathlib import Path
import sqlite3
import sys
import tempfile
import threading
import time
import unittest
from unittest import mock
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from ingest_api import DOMAINS, BudgetExceeded
from ingest_engine import run_ingest, sanitize_report, completed_outputs_available
from ingest_store import DomainStore


class IngestTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.root=Path(self.tmp.name)
        self.state=self.root/'state'
        self.state.mkdir()
        self.path=self.root/'input.jsonl'
        self.path.write_text('{}\n')
        self.source={'id':'fixture','path':str(self.path),'format':'jsonl','domain':'recipes'}
        self.config={'reserve_bytes':0,'batch_size':2,'terminal_progress':False}

    def tearDown(self):
        self.tmp.cleanup()

    def rows(self,count=5):
        return [{'id':str(i),'title':'meal '+str(i),'nutrition':{'protein':i},'ingredients':['salt','water'],
                 'relations':[{'kind':'uses','target_domain':'ingredients','target_id':'salt'}]} for i in range(count)]

    def test_records_fields_relations_and_idempotence(self):
        with DomainStore('recipes',self.state,self.config) as store:
            first=store.ingest(self.source,iter(self.rows()))
            second=store.ingest(self.source,iter(self.rows()))
            self.assertEqual(first['written'],5)
            self.assertEqual(second['written'],0)
            self.assertEqual(second['unchanged'],5)
            self.assertEqual(store.db.execute('SELECT count(*) FROM records').fetchone()[0],5)
            self.assertEqual(store.db.execute("SELECT number_value FROM record_fields WHERE record_id='3' AND field_path='/nutrition/protein'").fetchone()[0],3)
            self.assertEqual(store.db.execute('SELECT count(*) FROM relations').fetchone()[0],5)
            self.assertEqual(store.db.execute('SELECT count(*) FROM logical_records').fetchone()[0],5)

    def test_crash_resume_keeps_committed_prefix(self):
        def broken():
            yield from self.rows(3)
            raise OSError('private payload must not reach report')
        with DomainStore('recipes',self.state,self.config) as store:
            first=store.ingest(self.source,broken())
            self.assertEqual(first['written'],3)
            self.assertEqual(first['status'],'partial')
        with DomainStore('recipes',self.state,self.config) as store:
            second=store.ingest(self.source,iter(self.rows()))
            self.assertEqual(second['resumed_from'],3)
            self.assertEqual(second['written'],2)
            self.assertEqual(store.db.execute('SELECT count(*) FROM records').fetchone()[0],5)

    def test_hard_crash_replays_only_uncommitted_batch(self):
        class Crash(BaseException): pass
        def broken():
            yield from self.rows(3)
            raise Crash()
        with DomainStore('recipes',self.state,self.config) as store:
            with self.assertRaises(Crash): store.ingest(self.source,broken())
        with DomainStore('recipes',self.state,self.config) as store:
            second=store.ingest(self.source,iter(self.rows()))
            self.assertEqual(second['resumed_from'],2)
            self.assertEqual(second['written'],3)
            self.assertEqual(store.db.execute('SELECT count(*) FROM records').fetchone()[0],5)

    def test_one_writer_lock_and_release(self):
        with DomainStore('recipes',self.state,self.config):
            with self.assertRaisesRegex(RuntimeError,'already_active'):
                DomainStore('recipes',self.state,self.config)
            with DomainStore('ingredients',self.state,self.config): pass
        with DomainStore('recipes',self.state,self.config): pass

    def test_row_budget_resumes(self):
        limited={**self.config,'max_rows_per_source':2}
        for expected in (0,2,4):
            with DomainStore('recipes',self.state,limited) as store:
                result=store.ingest(self.source,iter(self.rows()))
                self.assertEqual(result['resumed_from'],expected)
        self.assertTrue(result['completed'])
        with DomainStore('recipes',self.state,self.config) as store:
            self.assertEqual(store.db.execute('SELECT count(*) FROM records').fetchone()[0],5)

    def test_bad_row_isolation_and_durable_partial(self):
        rows=[{'id':'good'},{'id':'bad','relations':[9]},{'id':'good2'}]
        with DomainStore('recipes',self.state,self.config) as store:
            result=store.ingest(self.source,iter(rows))
            self.assertEqual((result['written'],result['errors']),(2,1))
            self.assertEqual(result['status'],'partial')
            replay=store.ingest(self.source,iter(rows))
            self.assertEqual(replay['status'],'partial')
            self.assertEqual(replay['errors'],1)
            self.assertEqual(store.db.execute('SELECT count(*) FROM records').fetchone()[0],2)

    def test_parser_errors_persist(self):
        with DomainStore('recipes',self.state,self.config) as store:
            def reader():
                yield {'id':'one'}
                store.record_error(self.source,ValueError('private'))
                yield {'id':'two'}
            result=store.ingest(self.source,reader())
            self.assertEqual(result['errors'],1)
            self.assertEqual(result['status'],'partial')
            self.assertEqual(store.ingest(self.source,iter([]))['errors'],1)

    def test_changed_source_retains_provenance_history(self):
        with DomainStore('recipes',self.state,self.config) as store:
            first=store.ingest(self.source,iter([{'id':'a','v':1}]))
            self.path.write_text('{"changed":true}\n')
            second=store.ingest(self.source,iter([{'id':'a','v':2}]))
            self.assertNotEqual(first['source_version'],second['source_version'])
            self.assertEqual(store.db.execute('SELECT count(*) FROM records').fetchone()[0],2)

    def test_restricted_no_open(self):
        with DomainStore('recipes',self.state,self.config) as store:
            result=store.ingest({**self.source,'path':'/does/not/exist','restricted':True},iter([]))
            self.assertEqual(result['status'],'skipped')

    def test_parallel_progress_main_thread_callback_and_error_isolation(self):
        barrier=threading.Barrier(2)
        caller=threading.get_ident()
        seen=[]
        def adapter(domain,sources,context):
            if domain in ('recipes','ingredients'):
                barrier.wait(timeout=5)
            if domain=='dietary': raise ValueError('private secret')
            results=[context.ingest(source,iter([{'id':domain,'value':4}])) for source in sources]
            return {'status':'complete','sources':results}
        sources=[{**self.source,'id':d,'domain':d} for d in DOMAINS]
        def callback(report):
            self.assertEqual(threading.get_ident(),caller)
            seen.append(report)
        report=run_ingest(sources,{'state_dir':str(self.state),**self.config,'workers':8},callback,{d:adapter for d in DOMAINS})
        self.assertEqual(report['status'],'partial')
        self.assertEqual(report['domains']['dietary']['status'],'failed')
        self.assertEqual(report['domains']['recipes']['written'],1)
        self.assertEqual(report['domains']['ingredients']['written'],1)
        self.assertGreaterEqual(len(seen),2)
        self.assertEqual(seen[0]['status'],'running')
        self.assertTrue((self.state/'private-household'/'staging'/'inventory.sqlite3').exists())
        self.assertNotIn('private secret',json.dumps(report))
        self.assertNotIn(str(self.root),json.dumps(report))

    def test_disk_budget_preserves_independent_schemas(self):
        report=run_ingest([],{'state_dir':str(self.state),**self.config,'reserve_bytes':10**30})
        self.assertEqual(report['status'],'partial')
        self.assertTrue(all(x['status']=='partial' for x in report['domains'].values()))

    def test_public_schema_allowlists(self):
        raw={'status':'private','run_id':'secret path','domains':{'recipes':{'status':'complete','written':2,'path':'SECRET','payload':'BAD'}},'started_at':'PASSWORD','updated_at':'TOKEN','path':'SECRET'}
        safe=sanitize_report(raw)
        encoded=json.dumps(safe)
        for bad in ('SECRET','BAD','PASSWORD','TOKEN','secret path'):
            self.assertNotIn(bad,encoded)
        self.assertEqual(safe['domains']['recipes']['written'],2)

    def test_existing_non_owned_database_refused_without_changes(self):
        target=self.state/'staging'/'recipes.sqlite3'
        target.parent.mkdir()
        db=sqlite3.connect(target)
        db.execute('CREATE TABLE precious(value TEXT)')
        db.commit();db.close()
        original=target.read_bytes()
        with self.assertRaises(sqlite3.Error):
            DomainStore('recipes',self.state,self.config)
        self.assertEqual(target.read_bytes(),original)

    def test_index_expansion_capped_raw_source_preserved(self):
        with DomainStore('recipes',self.state,{**self.config,'max_indexed_fields':5}) as store:
            record={'id':'one','raw_source':{'huge':'preserved'},'values':list(range(1000))}
            store.ingest(self.source,[record])
            self.assertEqual(store.db.execute('SELECT count(*) FROM record_fields').fetchone()[0],5)
            payload=json.loads(store.db.execute('SELECT payload_json FROM records').fetchone()[0])
            self.assertEqual(payload,record)

    def test_registered_adapters_eight_domains_and_output_loss_recovery(self):
        def source(name,value,domains,**extra):
            path=self.root/name
            path.write_text(json.dumps(value)+'\n')
            return {'id':name,'path':str(path),'format':'jsonl','domains':domains,**extra}
        recipes=source('recipes.jsonl',{'name':'Generated soup','ingredients':['salt','water'],'instructions':['Mix','Serve']},['recipes','ingredients'])
        nutrient=source('nutrients.jsonl',{'kind':'nutrientProfile','id':'fixture:food','provenance':{'sourceId':'generated','license':'fixture','url':'https://example.invalid'},'data':{'foodName':'Generated food','nutrients':{'iron':{'value':1,'unit':'mg'}}}},['dietary','citations'])
        supplier=source('suppliers.jsonl',{'kind':'organization','id':'fixture:organization','provenance':{'sourceId':'wikidata','license':'CC0'},'data':{'name':'Generated store','roles':['supermarket-chain']}},['suppliers'])
        dbpath=self.root/'barcode.sqlite'
        with sqlite3.connect(dbpath) as db:
            db.executescript('CREATE TABLE code_keys(barcode TEXT PRIMARY KEY);INSERT INTO code_keys VALUES("001"),("002");')
        barcodes={'id':'barcodes','path':str(dbpath),'format':'sqlite','existing_store':True,'loaded':True,'domains':['barcodes']}
        config={'state_dir':str(self.state),**self.config,'catalog_sha256':'a'*64}
        sources=[recipes,nutrient,supplier,barcodes]
        first=run_ingest(sources,config)
        self.assertEqual(first['status'],'complete',first)
        self.assertEqual(first['domains']['barcodes']['reused_stores'],1)
        self.assertEqual(first['domains']['barcodes']['written'],0)
        self.assertEqual(first['domains']['user_profiles']['status'],'awaiting_user_input')
        self.assertGreater(first['domains']['recipes']['written'],0)
        prepared={'config':config,'catalog_sha256':'a'*64}
        self.assertTrue(completed_outputs_available(prepared))
        second=run_ingest(sources,config)
        self.assertEqual(sum(row['written'] for row in second['domains'].values()),0)
        self.assertTrue(completed_outputs_available(prepared))
        (self.state/'staging'/'recipes.sqlite3').unlink()
        self.assertFalse(completed_outputs_available(prepared))
        third=run_ingest(sources,config)
        self.assertGreater(third['domains']['recipes']['written'],0)
        self.assertTrue(completed_outputs_available(prepared))

    def test_reference_only_progress_never_counts_reference_as_import(self):
        events=[]
        with DomainStore('barcodes',self.state,self.config,progress=lambda **event:events.append(event)) as store:
            result=store.ingest({**self.source,'reference_only':True},[{'id':'reference','kind':'readonly_source_reference'}])
            self.assertEqual(result['written'],1)  # Private storage remains accurate.
            self.assertEqual(store.db.execute('SELECT count(*) FROM records').fetchone()[0],1)
        for event in events:
            for field in ('read','written','unchanged'):
                self.assertEqual(event.get(field,0),0)


if __name__=='__main__': unittest.main()
