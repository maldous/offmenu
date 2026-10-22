"""Generated tiny local fixtures; no real household/provider data or host paths."""
import importlib.util
import json
from pathlib import Path
import sqlite3
import sys
import tempfile
import threading
import unittest
PACKAGE=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(PACKAGE))
from ingest_existing import run_domain, inspect_existing
from ingest_store import DomainStore

class Context:
    def __init__(self,path,domain):
        self.config={'batch_size':2,'reserve_bytes':0}
        self.state_dir=path
        self.cancelled=threading.Event()
        self.store=DomainStore(domain,path,self.config)
        self.errors=[]
    def check_budget(self): pass
    def ingest(self,source,rows): return self.store.ingest(source,rows)
    def report_error(self,source,exc): self.errors.append(type(exc).__name__)

class ExistingTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name);self.contexts=[]
    def tearDown(self):
        for c in self.contexts:c.store.close()
        self.tmp.cleanup()
    def context(self,domain):
        c=Context(self.root/domain,domain);self.contexts.append(c);return c
    def database(self):
        path=self.root/'fixture.sqlite';db=sqlite3.connect(path)
        db.executescript('CREATE TABLE code_keys(barcode TEXT PRIMARY KEY);INSERT INTO code_keys VALUES("00123"),("00456");')
        db.close();return path
    def test_loaded_database_reused_without_copy(self):
        path=self.database();before=path.read_bytes();context=self.context('barcodes')
        source={'id':'generated','path':str(path),'format':'sqlite','provider':'off','existing_store':True,'loaded':True}
        report=run_domain('barcodes',[source],context)
        self.assertEqual(report['status'],'reused');self.assertEqual(report['reused_rows'],2)
        self.assertEqual(context.store.db.execute('SELECT COUNT(*) FROM records').fetchone()[0],1)
        record=json.loads(context.store.db.execute('SELECT payload_json FROM records').fetchone()[0])
        self.assertTrue(record['read_only']);self.assertEqual(record['tables'][0]['primary_key'],['barcode'])
        self.assertNotIn('00123',json.dumps(record));self.assertEqual(path.read_bytes(),before)
        report=run_domain('barcodes',[source],context);self.assertEqual(report['written'],0)
    def test_existing_provider_binding_prevents_duplicate_raw_bulk_copy(self):
        path=self.database();context=self.context('barcodes')
        raw=self.root/'raw.jsonl';raw.write_text('{"code":"00123"}\n')
        sources=[{'id':'raw','path':str(raw),'format':'jsonl','provider':'off'},
                 {'id':'db','path':str(path),'format':'sqlite','provider':'off','loaded':True}]
        report=run_domain('barcodes',sources,context)
        self.assertEqual(report['status'],'reused');self.assertEqual(report['written'],0)
        self.assertEqual(report['reused_stores'],1)
        self.assertEqual(context.store.db.execute('SELECT COUNT(*) FROM records').fetchone()[0],1)
        self.assertEqual(report['sources'][1]['reason'],'existing_binding_reused')

    def test_bad_database_does_not_prevent_valid_source(self):
        path=self.database();bad=self.root/'bad.sqlite';bad.write_text('invalid SQLite')
        sources=[{'id':str(n),'path':str(p),'format':'sqlite','existing_store':True} for n,p in enumerate((bad,path))]
        report=run_domain('barcodes',sources,self.context('barcodes'))
        self.assertEqual(report['status'],'partial');self.assertEqual(report['errors'],1);self.assertEqual(report['reused_rows'],2)
    def test_private_without_explicit_scope_never_read(self):
        for domain in ('inventory','user_profiles'):
            context=self.context(domain)
            report=run_domain(domain,[{'id':'unapproved','path':'/not/a/personal/file','format':'json'}],context)
            self.assertEqual(report['status'],'schema_only');self.assertEqual(report['reason'],'awaiting_user_input')
            self.assertEqual(context.errors,[]);self.assertEqual(context.store.db.execute('SELECT COUNT(*) FROM records').fetchone()[0],0)
    def test_explicit_private_scope_preserves_real_supplied_rows(self):
        path=self.root/'supplied.jsonl';path.write_text('{"id":"fixture-household","quantity":2}\n')
        context=self.context('inventory')
        source={'id':'supplied','path':str(path),'format':'jsonl','restricted':True,'metadata':{'user_supplied':True,'household_scope':True}}
        report=run_domain('inventory',[source],context)
        self.assertEqual(report['status'],'imported');self.assertEqual(report['written'],1)
    def test_historical_demo_and_incomplete_sources_are_not_opened(self):
        context=self.context('barcodes')
        sources=[{'id':kind,'path':'/not/a/real/file','format':'sqlite','disposition':kind} for kind in ('historical-demo','incomplete-hold','metadata-only')]
        report=run_domain('barcodes',sources,context)
        self.assertEqual(report['written'],0);self.assertEqual(report['reused_stores'],0)
        self.assertEqual(report['skipped'],3);self.assertEqual(context.errors,[])

    def test_symlink_source_rejected(self):
        path=self.database();link=self.root/'link.sqlite';link.symlink_to(path)
        report=run_domain('barcodes',[{'id':'link','path':str(link),'format':'sqlite'}],self.context('barcodes'))
        self.assertEqual(report['status'],'failed')
    def test_unrecognized_database_reference_keeps_schema_uncertainty(self):
        path=self.root/'other.sqlite';db=sqlite3.connect(path);db.execute('CREATE TABLE arbitrary(secret TEXT)');db.close()
        context=self.context('barcodes')
        report=run_domain('barcodes',[{'id':'unknown','path':str(path),'format':'sqlite'}],context)
        self.assertEqual(report['status'],'reused');self.assertEqual(report['sources'][0]['reason'],'schema_uncertain')
        self.assertEqual(report['reused_rows'],0);self.assertEqual(context.store.db.execute('SELECT COUNT(*) FROM records').fetchone()[0],1)
if __name__=='__main__':unittest.main()
