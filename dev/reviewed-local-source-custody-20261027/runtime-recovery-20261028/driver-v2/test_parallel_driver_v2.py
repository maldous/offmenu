import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import tempfile
import time
import unittest
from unittest.mock import patch

SPEC=importlib.util.spec_from_file_location('driver',Path(__file__).with_name('parallel_driver_v2.py'))
m=importlib.util.module_from_spec(SPEC);SPEC.loader.exec_module(m)

class DriverTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name)
        (self.root/'locks').mkdir();(self.root/'jobs'/'outer').mkdir(parents=True)
        (self.root/'locks'/'execution-slot-0.inflight.json').write_text(json.dumps({'mode':'write','job_id':'outer','timeout_seconds':30}))
        self.original_popen=subprocess.Popen
    def tearDown(self):self.tmp.cleanup()
    def lane(self,name='one',code='print("ok")'):
        script=self.root/(name+'.py');script.write_text(code)
        return {'id':name,'argv':['/usr/bin/python3','-I',str(script),'--unused'], 'output_root':str(self.root/name),
            'cpu_count':1,'memory_bytes':m.GIB,'memory_processes':1,'additional_output_budget_bytes':m.GIB,'source_pins':[{'path':str(script),'sha256':hashlib.sha256(script.read_bytes()).hexdigest()}]}
    def plan(self,lanes=None):return {'version':1,'run_id':'run','timeout_seconds':5,'reserve_bytes':70*m.GIB,'lanes':lanes or [self.lane()]}
    def run_plan(self,p):
        def popen(*a,**kw):kw['cwd']=self.root;return self.original_popen(*a,**kw)
        with patch.object(m.subprocess,'Popen',popen),patch.object(m,'free_bytes',return_value=100*m.GIB),patch.object(m,'available_memory',return_value=64*m.GIB):return m.run(p,self.root)
    def test_internal_pool_memory_includes_parent(self):
        p=self.plan();lane=p['lanes'][0];lane['argv'] += ['--workers','4'];lane['memory_processes']=4
        with self.assertRaises(ValueError):m.validate(p,self.root)
        lane['memory_processes']=5;m.validate(p,self.root)
    def test_internal_pool_aggregate_admission(self):
        p=self.plan();lane=p['lanes'][0];lane['argv'] += ['--workers','8'];lane['memory_processes']=9;lane['memory_bytes']=4*m.GIB
        with self.assertRaises(ValueError):m.validate(p,self.root)
    def test_worker_argument_bypasses_rejected(self):
        for flags in [['--workers=4'],['--workers','1','--workers','16'],['--work','4'],['--work=4']]:
            p=self.plan();p['lanes'][0]['argv']+=flags
            with self.assertRaises(ValueError):m.validate(p,self.root)
    def test_only_reviewed_interpreters(self):
        p=self.plan();p['lanes'][0]['argv'][0]='/offmenu/.venv/bin/python3';m.validate(p,self.root)
        p['lanes'][0]['argv'][0]='/tmp/python3'
        with self.assertRaises(ValueError):m.validate(p,self.root)
    def test_validation(self):m.validate(self.plan(),self.root)
    def test_overlapping_roots_refused(self):
        a=self.lane();b=self.lane('two');b['output_root']=a['output_root']+'/child'
        with self.assertRaises(ValueError):m.validate(self.plan([a,b]),self.root)
    def test_outside_path_refused(self):
        a=self.lane();a['output_root']='/etc'
        with self.assertRaises(ValueError):m.validate(self.plan([a]),self.root)
    def test_symlink_refused(self):
        a=self.lane();(self.root/'one').symlink_to('/tmp')
        with self.assertRaises(ValueError):m.validate(self.plan([a]),self.root)
    def test_unpinned_script_refused(self):
        p=self.plan();p['lanes'][0]['source_pins'][0]['path']=str(self.root/'other.py')
        with self.assertRaises(ValueError):m.validate(p,self.root)
    def test_wrong_hash_refused(self):
        p=self.plan();p['lanes'][0]['source_pins'][0]['sha256']='0'*64
        r=self.run_plan(p);self.assertEqual(r['status'],'preflight_error');self.assertEqual(r['lanes'],[])
    def test_fifo_source_refused_promptly(self):
        p=self.plan();path=Path(p['lanes'][0]['source_pins'][0]['path']);path.unlink();os.mkfifo(path)
        start=time.monotonic();r=self.run_plan(p);self.assertEqual(r['status'],'preflight_error');self.assertLess(time.monotonic()-start,1)
    def test_oversized_source_refused(self):
        p=self.plan();path=Path(p['lanes'][0]['source_pins'][0]['path'])
        with open(path,'wb') as f:f.truncate(9*1024**2)
        r=self.run_plan(p);self.assertEqual(r['status'],'preflight_error')
    def test_source_deadline(self):
        with self.assertRaises(ValueError):m.verify_pins(self.plan()['lanes'],time.monotonic()-1)
    def test_cpu_reserve(self):
        with self.assertRaises(ValueError):m.allocation(self.plan(),range(4),64*m.GIB)
    def test_memory_reserve(self):
        with self.assertRaises(ValueError):m.allocation(self.plan(),range(8),8*m.GIB)
    def test_aggregate_disk_reservation(self):
        p=self.plan([self.lane('one'),self.lane('two')]);p['lanes'][0]['additional_output_budget_bytes']=20*m.GIB;p['lanes'][1]['additional_output_budget_bytes']=20*m.GIB
        r=self.run_plan(p);self.assertEqual(r['status'],'preflight_error');self.assertEqual(r['lanes'],[])
    def test_outer_deadline_headroom(self):
        p=self.plan();p['timeout_seconds']=30
        with self.assertRaises(ValueError):self.run_plan(p)
    def test_control_required(self):
        (self.root/'locks'/'execution-slot-0.inflight.json').unlink()
        with self.assertRaises(ValueError):self.run_plan(self.plan())
    def test_two_processes_overlap(self):
        p=self.plan([self.lane('one','import time;time.sleep(.4);print("one")'),self.lane('two','import time;time.sleep(.4);print("two")')])
        start=time.monotonic();r=self.run_plan(p);elapsed=time.monotonic()-start
        self.assertEqual(r['status'],'commands_exited');self.assertEqual([x['exit_code'] for x in r['lanes']],[0,0]);self.assertLess(elapsed,1.2)
        self.assertNotEqual(r['lanes'][0]['cpu_affinity'],r['lanes'][1]['cpu_affinity'])
        self.assertTrue(r['outer_cleanup_verification_required']);self.assertFalse(r['output_qualification_established'])
    def test_logs_bounded(self):
        r=self.run_plan(self.plan([self.lane(code='print("x"*2000000)')]))
        self.assertEqual(r['lanes'][0]['log_bytes']['stdout'],m.LOG_LIMIT);self.assertGreater(r['lanes'][0]['output_bytes']['stdout'],m.LOG_LIMIT)
    def test_existing_run_not_replayed(self):
        p=self.plan();self.run_plan(p)
        with self.assertRaises(FileExistsError):self.run_plan(p)
    def test_cancel_before_launch(self):
        (self.root/'jobs'/'outer'/'cancel.json').write_text('{}')
        r=self.run_plan(self.plan());self.assertEqual(r['status'],'cancelled');self.assertEqual(r['lanes'],[])
    def test_nonzero_not_hidden(self):
        r=self.run_plan(self.plan([self.lane(code='raise SystemExit(7)')]))
        self.assertEqual(r['lanes'][0]['exit_code'],7);self.assertEqual(r['lanes'][0]['status'],'exit_nonzero')
    def test_lane_lock_contention(self):
        p=self.plan();key=hashlib.sha256(p['lanes'][0]['output_root'].encode()).hexdigest()
        fd=os.open(self.root/'locks'/('lane-'+key+'.lock'),os.O_CREAT|os.O_RDWR,0o600);m.fcntl.flock(fd,m.fcntl.LOCK_EX)
        try:r=self.run_plan(p);self.assertEqual(r['status'],'preflight_error');self.assertEqual(r['lanes'],[])
        finally:os.close(fd)
    def test_deadline_kills_leader(self):
        r=self.run_plan(self.plan([self.lane(code='import time;time.sleep(20)')]))
        self.assertEqual(r['status'],'deadline');self.assertIsNotNone(r['lanes'][0]['exit_code'])

if __name__=='__main__':unittest.main()
