"""Runtime isolation and real owned-child cleanup regressions; no model calls."""
import copy
import ctypes
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

from tools.delivery import symphony_launch as launch
from tools.delivery.symphony_capacity import AdmissionError, Pool, digest
from tools.delivery.symphony_tasks import manifest_digest, runtime_lease_ids

ROOT=Path(__file__).resolve().parents[2]
spec=importlib.util.spec_from_file_location('protected_capacity_runner',ROOT/'tools/delivery/windmill_runner.py')
runner=importlib.util.module_from_spec(spec);spec.loader.exec_module(runner)


class RuntimeIsolation(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)
        self.policy=json.loads((ROOT/'tools/delivery/capacity-policy.json').read_text())
        self.policy['symphony']['pool_path']=str(self.root/'pool')
        self.pool=Pool(self.root/'pool',self.policy)
        self.provider={'route':'codex-chatgpt','available':True,'checked_at':time.time(),'session_ceiling':8}
        self.host={'cpu_millis':31000,'available_memory_bytes':60*1024**3,'available_disk_bytes':200*1024**3}
        self.a=self.root/'run';self.b=self.root/'run-other';self.a.mkdir();self.b.mkdir()
        self.ma=launch.default_manifest('a'*40);self.mb=copy.deepcopy(self.ma)
        task=self.mb['tasks'].pop('UIF-90');task['allowed_paths']=['tests/other.py'];self.mb['tasks']['UIF-91']=task
        self.la=self.admit(self.a,self.ma,'UIF-90');self.lb=self.admit(self.b,self.mb,'UIF-91')

    def admit(self,runtime,manifest,name):
        task=manifest['tasks'][name]
        binding={'branch':manifest['branch'],'head':manifest['base_revision'],'owner':task['owner'],
                 'write_roots':task['allowed_paths'],'resources':task['resources'],
                 'task_sha256':manifest_digest({'runtime':str(runtime),'task':task})}
        lease=runtime_lease_ids(runtime,manifest)[name]
        self.pool.admit(lease,binding,self.provider,self.host)
        return lease

    def states(self):return {r['id']:r['status'] for r in self.pool.status()}

    def test_cancellation_cannot_select_prefixed_runtime(self):
        launch.cancel_runtime_leases(self.a,self.ma,self.policy)
        self.assertEqual(self.states()[self.la],'cancel_requested')
        self.assertEqual(self.states()[self.lb],'running')

    def test_reconciliation_preserves_other_runtime_reservation_and_ownership(self):
        with patch.object(launch,'workspace_processes',return_value=[]) as observed:
            self.assertEqual(launch.reconcile_runtime_leases(self.a,self.ma,self.policy,True),[])
        observed.assert_called_once_with(self.a/'workspaces/UIF-90')
        self.assertEqual(self.states()[self.la],'failed');self.assertEqual(self.states()[self.lb],'running')
        binding={'branch':launch.BRANCH,'head':'a'*40,'owner':'conflicting-owner',
                 'write_roots':['tests/other.py'],'resources':self.policy['symphony']['default_resources'],
                 'task_sha256':digest('new task')}
        with self.assertRaisesRegex(AdmissionError,'ownership_conflict'):
            self.pool.admit('new-task',binding,self.provider,self.host)

    def test_identical_basename_and_manifest_in_different_parent_has_distinct_identity(self):
        self.assertNotEqual(runtime_lease_ids(self.root/'first/run',self.ma),
                            runtime_lease_ids(self.root/'second/run',self.ma))

    def test_unproven_cleanup_does_not_release_selected_lease(self):
        self.assertEqual(launch.reconcile_runtime_leases(self.a,self.ma,self.policy,False),['UIF-90'])
        self.assertEqual(self.states()[self.la],'running')

    def fail_refresh(self,write_failure):
        self.assertEqual(ctypes.CDLL(None,use_errno=True).prctl(36,1,0,0,0),0)
        marker=self.a/'child.pid'
        program="import subprocess,sys,time;from pathlib import Path;p=subprocess.Popen([sys.executable,'-c','import time;time.sleep(60)'],start_new_session=True);Path(sys.argv[1]).write_text(str(p.pid));time.sleep(60)"
        process=subprocess.Popen([sys.executable,'-c',program,str(marker)],cwd=self.a,
                                 stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,start_new_session=True)
        self.addCleanup(lambda: launch.cleanup_owned_tree(process) if process.poll() is None else None)
        deadline=time.monotonic()+5
        while not marker.exists() and time.monotonic()<deadline:time.sleep(.01)
        self.assertTrue(marker.exists());child=int(marker.read_text())
        clock_values=iter([0,0,61,61]);receipt={}
        with patch.object(launch,'provider_proof',side_effect=None if write_failure else OSError('provider unavailable'),return_value=self.provider), \
             patch.object(launch,'write_provider_proof',side_effect=OSError('proof storage unavailable') if write_failure else None):
            with self.assertRaises(OSError):
                launch.supervise_native(process,self.a,self.ma,self.policy,receipt,'gpt-6.1-sol',120,clock=lambda:next(clock_values))
        self.assertIsNotNone(process.poll());self.assertFalse(Path('/proc',str(child)).exists())
        self.assertTrue(receipt['owned_process_tree_gone'])
        saved=json.loads((self.a/'process-receipt.json').read_text())
        self.assertEqual(saved['supervisor_error_type'],'OSError')
        self.assertEqual(self.states()[self.la],'failed');self.assertEqual(self.states()[self.lb],'running')

    def test_provider_rpc_failure_reaps_real_parent_and_detached_child(self):self.fail_refresh(False)
    def test_proof_write_failure_reaps_real_parent_and_detached_child(self):self.fail_refresh(True)


class CoordinatorProtection(unittest.TestCase):
    def test_tracked_execution_code_policy_and_ancestor_writes_are_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            request={'workers':1,'overhead_processes':1,'cpu_millis':1,'memory_bytes':1024**2,
                     'output_bytes':0,'read_roots':[str(root)],'write_roots':[]}
            for relative in ['tools/delivery/windmill_runner.py','tools/delivery/capacity-policy.json',
                             'tools/delivery/windmill_bridge.py','tools/delivery','tools']:
                with self.subTest(path=relative),self.assertRaisesRegex(ValueError,'CoordinatorWrite'):
                    runner.validate_resources(dict(request,write_roots=[str(root/relative)]),'write',scope=root)
            self.assertEqual(runner.validate_resources(dict(request,write_roots=[str(root/'apps/example.py')]),'write',scope=root)['workers'],1)


if __name__=='__main__':unittest.main()
