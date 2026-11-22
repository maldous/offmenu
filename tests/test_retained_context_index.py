"""Synthetic SQLite indexes only; not a real-provider metadata or corpus operation."""
import contextlib
from dataclasses import asdict,replace
import os
from pathlib import Path
import sqlite3
import tempfile
import time
import unittest
from unittest.mock import patch
from offmenu import retained_context_consumers as adapters
from offmenu.retained_context_job import Budget,Unit,Refused,digest
from offmenu.retained_context_source import input_key,run_qualified
from offmenu.retained_context_index import Snapshot,Cohort,Limits,qualify_selection,SelectedProof
from test_retained_context_job import TestIssuer
from test_retained_context_route import fixture


class Issuer:
    def __init__(self,limits,snapshot):
        self.limits=limits;self.snapshot=snapshot;self.extra={};self.held=False
    @contextlib.contextmanager
    def hold_index_proof(self,request):
        self.held=True
        try:
            grant=dict(request=request,snapshot_id=self.snapshot.snapshot_id,global_metadata_sweep_allowed=True,global_record_sweep_allowed=True,
                       stable_snapshot_held=True,provider_rights_and_claims_current=True,host_limits_enforced=True,
                       offline_only=True,limits=asdict(self.limits),valid_until=time.time()+self.limits.timeout_seconds+30)
            grant.update(self.extra);yield grant
        finally:self.held=False


class IndexTest(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name);self.fd=os.open(self.root,os.O_DIRECTORY);self.addCleanup(os.close,self.fd)
        self.fixtures=[];self.cohorts=[]
        for prov in ('off','usda-files'):
            t=self.root/prov;t.mkdir(); r,d,p,rel,rights,key=fixture(t,prov,one_zero=True); self.fixtures.append((r,d,p,rel,rights,key))
            self.cohorts.append(Cohort(prov,rel,int(key.split('/')[0][7:]),p['cohort_receipt'].sha256,
                3,((key,None),),3,p['cohort_receipt'],p['index']))
        self.cohorts=tuple(self.cohorts);self.db=self.root/'stable-global.sqlite'
        # Create a SHARED snapshot used by both origins (metadata only).
        with sqlite3.connect(self.db) as db:
            db.executescript('CREATE TABLE records(id TEXT PRIMARY KEY,source,release,native_id,ref_sha,cohort,record_shard);'
                             'CREATE TABLE barcodes(code,checksum_valid,id,PRIMARY KEY(code,id));'
                             'CREATE TABLE completed(cohort INTEGER PRIMARY KEY,products INTEGER,result_sha TEXT);')
            for _,_,p,*_ in self.fixtures:
                with sqlite3.connect(p['global_index'].path) as local:
                    for table in ('records','barcodes','completed'):
                        rows=local.execute('SELECT * FROM '+table).fetchall()
                        db.executemany('INSERT INTO '+table+' VALUES('+','.join('?'*len(rows[0]))+')',rows)
            # One unrelated observation: included once in the admitted sweep; no key leaves the verifier.
            db.execute("INSERT INTO barcodes VALUES ('999',0,'unrequested')")
        self.limit=Limits(10,20,20,20,8*2**20,1000000,30,512*2**20)
    def snap(self):
        s=self.db.stat(); return Snapshot(str(self.db),'fixture-snapshot-v1',s.st_size,s.st_dev,s.st_ino,s.st_mtime_ns,s.st_ctime_ns)
    def proof(self,*,cohorts=None,limit=None,extra=None):
        cap=limit or self.limit;s=self.snap();iss=Issuer(cap,s);iss.extra=extra or {}
        return qualify_selection(root=str(self.root),root_fd=self.fd,snapshot=s,cohorts=cohorts or self.cohorts,limits=cap,issuer=iss)
    def test_one_sweep_two_sources_including_zero_postings_and_derived_shard_counts(self):
        sql=[];conn=sqlite3.connect
        def tracing(*args,**kw):
            db=conn(*args,**kw);db.set_trace_callback(sql.append);return db
        with patch('offmenu.retained_context_index.sqlite3.connect',side_effect=tracing):
            p=self.proof()
        self.assertEqual(sum(x=='SELECT code,id,checksum_valid FROM barcodes' for x in sql),1)
        self.assertEqual(sum(x=='SELECT id,source,release,native_id,ref_sha,cohort,record_shard FROM records' for x in sql),1)
        self.assertEqual(p.metadata()['global_records_examined'],6)
        self.assertEqual(p.metadata()['global_postings_examined'],5)
        self.assertEqual(p.metadata()['selected_records'],6);self.assertEqual(p.metadata()['selected_postings'],4)
        self.assertFalse(p.metadata()['whole_file_hash_verified']);self.assertFalse(p.metadata()['public_distribution_approved'])
        for c in self.cohorts:self.assertEqual(p.count(c.provider,c.release,c.shards[0][0]),3)
        self.assertNotIn('unrequested',str(p.metadata()))
    def test_missing_extra_mismatch_and_zero_postings(self):
        with sqlite3.connect(self.db) as d:d.execute("INSERT INTO barcodes VALUES ('extra',0,?)",('offmenu:product:'+format(3,'024x'),))
        with self.assertRaisesRegex(Refused,'extra or changed'):self.proof()
        with sqlite3.connect(self.db) as d:
            d.execute("DELETE FROM barcodes WHERE code='extra'")
            d.execute("DELETE FROM barcodes WHERE id=?",('offmenu:product:'+format(1,'024x'),))
        with self.assertRaisesRegex(Refused,'missing selected'):self.proof()
    def test_changed_global_id_or_completion_and_early_stop(self):
        with self.assertRaisesRegex(Refused,'exceeded admission before EOF'):self.proof(limit=replace(self.limit,max_global_postings=3))
        with sqlite3.connect(self.db) as d:d.execute("UPDATE completed SET products=99 WHERE cohort=114")
        with self.assertRaisesRegex(Refused,'not anchored'):self.proof()
    def test_reverse_membership_extra_zero_and_misplaced_records(self):
        with sqlite3.connect(self.db) as d:
            d.execute("INSERT INTO records SELECT 'offmenu:product:ffffffffffffffffffffffff',source,release,'unexpected',ref_sha,cohort,record_shard FROM records WHERE source='off' LIMIT 1")
        with self.assertRaisesRegex(Refused,'extra or changed selected global'):self.proof()
        with sqlite3.connect(self.db) as d:
            d.execute("DELETE FROM records WHERE native_id='unexpected'")
            d.execute("DELETE FROM records WHERE id=?",('offmenu:product:'+format(3,'024x'),))
        with self.assertRaisesRegex(Refused,'missing selected global record'):self.proof()

    def test_exact_primary_keys_and_separate_global_record_budget(self):
        with self.assertRaisesRegex(Refused,'record sweep exceeded'):self.proof(limit=replace(self.limit,max_global_records=2))
        with sqlite3.connect(self.db) as d:
            d.executescript('ALTER TABLE records RENAME TO old_records;'
                'CREATE TABLE records(id TEXT,source,release,native_id,ref_sha,cohort,record_shard,PRIMARY KEY(id,source));'
                'INSERT INTO records SELECT * FROM old_records;')
        with self.assertRaisesRegex(Refused,'unique source identity'):self.proof()

    def test_scope_issuer_and_deadline_before_reads(self):
        for extra in [{'stable_snapshot_held':False},{'provider_rights_and_claims_current':False},
                      {'global_metadata_sweep_allowed':False},{'global_record_sweep_allowed':False},{'limits':{}},{'valid_until':time.time()+1}]:
            with patch('offmenu.retained_context_index._open',side_effect=AssertionError('unadmitted inputs opened')):
                with self.assertRaisesRegex(Refused,'missing scoped'):self.proof(extra=extra)
        with self.assertRaisesRegex(Refused,'unissued'):SelectedProof('x',self.snap(),{}, {})
    def test_bad_pins_and_incomplete_shard_scope(self):
        c=self.cohorts[0]
        with self.assertRaisesRegex(Refused,'pinned provider cohort'):
            self.proof(cohorts=(replace(c,shards=(('cohort-114/chunk-00002',None),)),))
        with self.assertRaisesRegex(Refused,'per-shard'):self.proof(cohorts=(replace(c,shards=((c.shards[0][0],2),)),))
        with sqlite3.connect(self.db) as d:d.execute("UPDATE records SET native_id='cross' WHERE id=?",('offmenu:product:'+format(1,'024x'),))
        with self.assertRaisesRegex(Refused,'row differs'):self.proof()
    def test_content_change_with_reobserved_stat_is_not_enough(self):
        c=self.cohorts[0];path=Path(c.index.path)
        with path.open('ab') as f:f.write(b'fixture tail')
        s=path.stat();p=replace(c.index,size=s.st_size,mtime_ns=s.st_mtime_ns,ctime_ns=s.st_ctime_ns)
        with self.assertRaisesRegex(Refused,'content differs'):self.proof(cohorts=(replace(c,index=p),))

    def test_end_to_end_without_false_global_content_hash(self):
        root,dest,pins,release,rights,shard=self.fixtures[0]; gp=Path(pins['global_index'].path);s=gp.stat()
        snap=Snapshot(str(gp),'single-stable-fixture',s.st_size,s.st_dev,s.st_ino,s.st_mtime_ns,s.st_ctime_ns)
        srcfd=os.open(root,os.O_DIRECTORY);self.addCleanup(os.close,srcfd)
        dstfd=os.open(dest,os.O_DIRECTORY);self.addCleanup(os.close,dstfd)
        proof=qualify_selection(root=str(root),root_fd=srcfd,snapshot=snap,cohorts=(self.cohorts[0],),
                                limits=self.limit,issuer=Issuer(self.limit,snap))
        pins=dict(pins,global_index=snap);ds=os.fstat(dstfd)
        u=Unit('off',release,'fixture-queue',shard,'independent-test',1,pins['queue'].sha256,
               pins['assignment'].sha256,rights,digest(Path(adapters.__file__).read_bytes()),input_key(str(root),srcfd,pins),
               ds.st_dev,ds.st_ino,proof.count('off',release,shard),128*1024,2,Budget(1000,2*1024**3,1,2*1024**3,900),
               snapshot_id=snap.snapshot_id,proof_request_sha256=proof.request)
        issuer=TestIssuer(u); local_checks=[]
        def verify(pin,fd):
            self.assertEqual(pin,pins['index']);local_checks.append(pin)
            return digest(os.pread(fd,pin.size,0))==pin.sha256
        args=dict(source_root=str(root),source_fd=srcfd,destination_fd=dstfd,pins=pins,issuer=issuer,verify_index=verify)
        with self.assertRaises(Refused):run_qualified(u,selected_proof=proof,**args)
        issuer.mutate={'snapshot_id':snap.snapshot_id,'stable_snapshot_held':True}
        with self.assertRaisesRegex(Refused,'missing exact'):run_qualified(u,selected_proof=None,**args)
        self.assertEqual(run_qualified(u,selected_proof=proof,**args)['rows'],3)
        self.assertEqual(local_checks,[pins['index']])

    def test_snapshot_sidecars_refused(self):
        Path(str(self.db)+'-wal').touch()
        with self.assertRaisesRegex(ValueError,'sidecars'):self.proof()
