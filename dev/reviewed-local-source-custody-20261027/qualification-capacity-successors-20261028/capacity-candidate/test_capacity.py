import copy
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

HERE = Path(__file__).parent
spec = importlib.util.spec_from_file_location('runner', HERE/'job_runner.py')
r = importlib.util.module_from_spec(spec); spec.loader.exec_module(r)

def budget(**kwargs):
    d = dict(workers=1, overhead_processes=4, cpu_millis=100,
             memory_bytes=128*1024**2, output_bytes=0,
             read_roots=['/offmenu/input'], write_roots=[])
    d.update(kwargs)
    return d

class AdmissionTests(unittest.TestCase):
    def test_configured_ceiling_without_fanout(self):
        # Pure declaration accounting: no64-job/256-process execution.
        d=budget(workers=256)
        self.assertEqual(r.validate_resources(d,'read'),d)
        self.assertIsNone(r.decide(d,[copy.deepcopy(d) for _ in range(63)],31,62*r.GIB,500*r.GIB))
        self.assertEqual(r.decide(d,[d]*64,31,62*r.GIB,500*r.GIB),'capacity_slots_active')
        with self.assertRaises(ValueError):r.validate_resources(budget(workers=257),'read')
    def test_cpu_independent_of_workers(self):
        self.assertIsNone(r.decide(budget(workers=256,cpu_millis=1000),[],31,62*r.GIB,500*r.GIB))
        self.assertEqual(r.decide(budget(cpu_millis=27000),[budget(cpu_millis=1)],31,62*r.GIB,500*r.GIB),'capacity_cpu_reserved')
    def test_aggregate_memory_disk(self):
        self.assertEqual(r.decide(budget(memory_bytes=30*r.GIB),[budget(memory_bytes=30*r.GIB)],31,62*r.GIB,500*r.GIB),'capacity_memory_reserved')
        self.assertEqual(r.decide(budget(output_bytes=r.GIB),[],31,62*r.GIB,70*r.GIB),'capacity_disk_reserved')
    def test_disjoint_and_parent_child_conflicts(self):
        a=budget(write_roots=['/offmenu/output/a'],read_roots=[])
        b=budget(write_roots=['/offmenu/output/b'],read_roots=[])
        self.assertIsNone(r.decide(a,[b],31,62*r.GIB,500*r.GIB))
        for x in (budget(write_roots=['/offmenu/output']),budget(read_roots=['/offmenu/output/a/file'])):
            self.assertEqual(r.decide(x,[a],31,62*r.GIB,500*r.GIB),'capacity_paths_conflict')
    def test_canonical_scope_coordinator_and_types(self):
        for d in (budget(workers=True), budget(write_roots=['/offmenu/data/.offmenu-platform']),budget(read_roots=['/offmenu/../etc']), budget(read_roots=['/tmp']),budget(write_roots=['/offmenu/scripts/windmill']),budget(read_roots=['/offmenu/input/'])):
            with self.assertRaises(ValueError):r.validate_resources(d,'write' if d['write_roots'] else 'read')
        with tempfile.TemporaryDirectory() as t:
            p=Path(t);(p/'link').symlink_to('/tmp')
            with self.assertRaises(ValueError):r.validate_resources(budget(read_roots=[str(p/'link')]),'read',scope=p)

class RunnerTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(); self.root=Path(self.tmp.name)
    def tearDown(self):self.tmp.cleanup()
    def runjob(self,job,command='true',resources=None,mode='read',timeout=5):
        with patch.object(r,'memory_available',return_value=62*r.GIB),patch.object(r,'free_bytes',return_value=500*r.GIB):
            return r.run(self.root/'state',job,command,mode,timeout,resources)
    def test_pooled_success_and_resource_identity(self):
        q=self.runjob('a',resources=budget());self.assertEqual(q['status'],'succeeded');self.assertTrue(q['child_tree_gone'])
        self.assertEqual(self.runjob('a',resources=budget(cpu_millis=200))['status'],'id_conflict')
        self.assertEqual(list((self.root/'state/locks').glob('*.inflight.json')),[])
    def test_stale_high_slot_blocks(self):
        root=self.root/'state';r.setup(root,'probe')
        r.atomic(root/'locks/execution-slot-63.inflight.json',dict(job_id='crashed',mode='read',resources=budget(),capacity_version=1))
        out=self.runjob('probe',resources=budget());self.assertEqual(out['status'],'blocked_reconciliation')
        self.assertFalse((root/'jobs/probe').exists())
    def test_live_legacy_reader_blocks_pool(self):
        root=self.root/'state';r.setup(root,'probe')
        fd=r.try_lock(root/'locks/execution-slot-0.lock')
        try:
            r.atomic(root/'locks/execution-slot-0.inflight.json',dict(job_id='legacy',mode='read',timeout_seconds=30))
            out=self.runjob('probe',resources=budget());self.assertEqual(out['reason'],'capacity_legacy_active')
        finally:os.close(fd)
    def test_existing_writer_lock_blocks_pool(self):
        root=self.root/'state';r.setup(root,'probe');fd=r.try_lock(root/'locks/execution-access.lock')
        try:self.assertEqual(self.runjob('probe',resources=budget())['reason'],'incompatible_job_active')
        finally:os.close(fd)
    def test_live_pool_blocks_legacy(self):
        root=self.root/'state';r.setup(root,'probe');fd=r.try_lock(root/'locks/execution-slot-0.lock')
        try:
            r.atomic(root/'locks/execution-slot-0.inflight.json',dict(job_id='live',mode='read',resources=budget(),capacity_version=1))
            self.assertEqual(self.runjob('probe')['reason'],'capacity_pool_active')
        finally:os.close(fd)
    def test_admission_lock_busy_not_reserved(self):
        root=self.root/'state';r.setup(root,'probe');fd=r.try_lock(root/'locks/capacity-admission.lock')
        try:
            out=self.runjob('probe',resources=budget());self.assertEqual(out['reason'],'capacity_admission_busy');self.assertFalse(out['reserved'])
        finally:os.close(fd)
    def test_sampled_overbudget_stops_and_releases(self):
        with patch.object(r,'capacity_usage',return_value={'processes':6,'rss_bytes':0}):
            q=self.runjob('budget','sleep 20',resources=budget())
        self.assertEqual(q['status'],'failed');self.assertEqual(q['error_class'],'CapacityBudgetExceeded');self.assertTrue(q['child_tree_gone'])
        self.assertEqual(list((self.root/'state/locks').glob('*.inflight.json')),[])
    def test_cancelled_before_launch_releases(self):
        with patch.object(r,'stop_requested',return_value=True):q=self.runjob('cancelled',resources=budget())
        self.assertEqual(q['status'],'cancelled');self.assertTrue(q['child_tree_gone'])
        self.assertEqual(list((self.root/'state/locks').glob('*.inflight.json')),[])
    def test_subreaper_failure_release(self):
        with patch.object(r.ctypes,'CDLL') as libc:
            libc.return_value.prctl.return_value=1
            q=self.runjob('failure',resources=budget())
        self.assertEqual(q['status'],'supervisor_error');self.assertTrue(q['child_tree_gone'])
        self.assertEqual(list((self.root/'state/locks').glob('*.inflight.json')),[])

if __name__=='__main__':unittest.main()
