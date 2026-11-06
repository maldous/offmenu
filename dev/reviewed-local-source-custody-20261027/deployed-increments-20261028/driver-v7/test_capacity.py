import copy
import fcntl
import json
import os
from pathlib import Path
import unittest
from test_baseline import DriverTests,m

class CapacityTests(DriverTests):
    def setUp(self):
        super().setUp(); self.p=self.plan(); self.lane0=self.p['lanes'][0]
        self.resources={'workers':1,'overhead_processes':2,'cpu_millis':1000,'memory_bytes':int(1.5*m.GIB),'output_bytes':m.GIB,'read_roots':[self.lane0['argv'][2]],'write_roots':[self.lane0['output_root'],str(self.root/'parallel'/'run')]}
        self.own={'job_id':'outer','mode':'write','timeout_seconds':30,'capacity_version':1,'request_sha256':'a'*64,'resources':self.resources}
        self.lock=os.open(self.root/'locks'/'execution-slot-0.lock',os.O_RDWR|os.O_CREAT,0o600);fcntl.flock(self.lock,fcntl.LOCK_EX)
        (self.root/'locks'/'capacity-admission.lock').touch();self.write()
    def tearDown(self):os.close(self.lock);super().tearDown()
    def write(self):
        (self.root/'locks'/'execution-slot-0.inflight.json').write_text(json.dumps(self.own))
        (self.root/'jobs'/'outer'/'receipt.json').write_text(json.dumps(dict(self.own,version=3,status='running')))
    def select(self):return m.outer_reservation(self.p,self.root,'outer')
    # Inherited baseline tests deliberately require legacy markers. Run only new cases here.
    def test_own_selected_with_disjoint_peer(self):
        other=copy.deepcopy(self.own);other['job_id']='peer';other['resources']['write_roots']=[str(self.root/'peer')]
        (self.root/'locks'/'execution-slot-63.inflight.json').write_text(json.dumps(other))
        self.assertEqual(self.select()['job_id'],'outer')
    def test_overlap_refused(self):
        other=copy.deepcopy(self.own);other['job_id']='peer';(self.root/'locks'/'execution-slot-1.inflight.json').write_text(json.dumps(other))
        with self.assertRaises(ValueError):self.select()
    def test_legacy_cannot_silently_opt_in(self):
        with self.assertRaises(ValueError):m.outer_reservation(self.p,self.root)
    def test_wrong_identity_refused(self):
        with self.assertRaises(ValueError):m.outer_reservation(self.p,self.root,'different')
    def test_unheld_slot_refused(self):
        fcntl.flock(self.lock,fcntl.LOCK_UN)
        with self.assertRaises(ValueError):self.select()
    def test_receipt_mismatch_refused(self):
        path=self.root/'jobs'/'outer'/'receipt.json';r=json.loads(path.read_text());r['request_sha256']='b'*64;path.write_text(json.dumps(r))
        with self.assertRaises(ValueError):self.select()
    def test_terminal_receipt_refused(self):
        path=self.root/'jobs'/'outer'/'receipt.json';r=json.loads(path.read_text());r['status']='succeeded';path.write_text(json.dumps(r))
        with self.assertRaises(ValueError):self.select()
    def test_budgets_refuse_understatement(self):
        for key in ('workers','overhead_processes','cpu_millis','memory_bytes','output_bytes'):
            old=self.resources[key];self.resources[key]=old-1;self.write()
            with self.subTest(key=key),self.assertRaises(ValueError):self.select()
            self.resources[key]=old
    def test_scope_refuses_missing_output_or_logs(self):
        original=list(self.resources['write_roots'])
        for i in range(2):
            self.resources['write_roots']=original[:i]+original[i+1:];self.write()
            with self.assertRaises(ValueError):self.select()
        self.resources['write_roots']=original
    def test_source_scope_required(self):
        self.resources['read_roots']=[];self.write()
        with self.assertRaises(ValueError):self.select()
    def test_capacity_cpu_not_double_reserved(self):
        self.lane0['cpu_count']=27;m.allocation(self.p,range(27),64*m.GIB,True)
        with self.assertRaises(ValueError):m.allocation(self.p,range(27),64*m.GIB)
    def test_admission_snapshot_busy_fails_closed(self):
        fd=os.open(self.root/'locks'/'capacity-admission.lock',os.O_RDWR)
        try:
            fcntl.flock(fd,fcntl.LOCK_EX)
            with self.assertRaises(BlockingIOError):self.select()
        finally:os.close(fd)
    def test_fifo_json_rejected(self):
        p=self.root/'fifo';os.mkfifo(p)
        with self.assertRaises(ValueError):m.read_json(p)

# Avoid rerunning legacy tests with capacity-only setup.
for name in list(DriverTests.__dict__):
    if name.startswith('test_') and name not in CapacityTests.__dict__:setattr(CapacityTests,name,None)
del DriverTests
