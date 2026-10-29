"""Exact operating ceilings and admission invariants, with no service/model load."""
import concurrent.futures
import importlib.util
import json
from pathlib import Path
import tempfile
import time
import unittest
from tools.delivery.symphony_capacity import AdmissionError, Pool, digest

ROOT=Path(__file__).resolve().parents[2]
POLICY=json.loads((ROOT/'tools/delivery/capacity-policy.json').read_text())
spec=importlib.util.spec_from_file_location('reviewed_capacity_runner',ROOT/'tools/delivery/windmill_runner.py')
runner=importlib.util.module_from_spec(spec);spec.loader.exec_module(runner)


class CapacityPolicy(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.path=Path(self.temp.name)/'pool';self.pool=Pool(self.path,POLICY)
        self.provider={'route':'codex-chatgpt','available':True,'checked_at':time.time(),'session_ceiling':8}
        self.host={'cpu_millis':31000,'available_memory_bytes':60*1024**3,'available_disk_bytes':200*1024**3}

    def binding(self,n=0):
        return {'branch':'feature/langgraph-delivery-standardization','head':'a'*40,'owner':'task-'+str(n),'write_roots':['tests/owned-'+str(n)],'resources':dict(POLICY['symphony']['default_resources']),'task_sha256':digest({'n':n})}

    def admit(self,n):return self.pool.admit('task-'+str(n),self.binding(n),self.provider,self.host)

    def test_exact_requested_ceilings(self):
        self.assertEqual(POLICY['symphony']['max_concurrent_agents'],8)
        self.assertEqual(POLICY['windmill']['service_workers'],16)
        self.assertEqual((runner.JOB_CEILING,runner.WORKER_CEILING),(32,64))
        demand={'workers':64,'overhead_processes':1,'cpu_millis':1,'memory_bytes':1024**2,'output_bytes':0,'read_roots':['/offmenu'],'write_roots':[]}
        self.assertEqual(runner.validate_resources(demand,'read')['workers'],64)
        with self.assertRaises(ValueError):runner.validate_resources(dict(demand,workers=65),'read')
        self.assertIsNone(runner.decide(demand,[demand]*31,31,100*1024**3,1000*1024**3))
        self.assertEqual(runner.decide(demand,[demand]*32,31,100*1024**3,1000*1024**3),'capacity_io_reserved')

    def test_eight_concurrent_reservations_no_lower_cap(self):
        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
            self.assertEqual(len(list(executor.map(self.admit,range(8)))),8)
        with self.assertRaisesRegex(AdmissionError,'capacity_sessions'):self.admit(8)
        self.assertEqual(len(Pool(self.path,POLICY).status()),8)
        self.assertTrue(self.admit(0)['reused'])

    def test_disjoint_scope_and_immutable_binding(self):
        self.admit(0);binding=self.binding(1);binding['write_roots']=['tests/owned-0/child.py']
        with self.assertRaisesRegex(AdmissionError,'ownership_conflict'):self.pool.admit('other',binding,self.provider,self.host)
        binding=self.binding(0);binding['owner']='changed'
        with self.assertRaisesRegex(AdmissionError,'immutable_binding_conflict'):self.pool.admit('task-0',binding,self.provider,self.host)

    def test_provider_shortage_and_aggregate_resources(self):
        for proof in [dict(self.provider,available=False),dict(self.provider,checked_at=time.time()-301)]:
            with self.assertRaisesRegex(AdmissionError,'provider_unavailable'):self.pool.admit('unavailable',self.binding(),proof,self.host)
        for key,value in [('cpu_millis',4000),('available_memory_bytes',8*1024**3),('available_disk_bytes',70*1024**3)]:
            with self.assertRaisesRegex(AdmissionError,'capacity_'):self.pool.admit('shortage',self.binding(),self.provider,dict(self.host,**{key:value}))

    def test_cancel_and_crash_hold_until_explicit_process_proof(self):
        self.admit(0);self.pool.cancel('task-0')
        self.assertEqual(Pool(self.path,POLICY).status()[0]['status'],'cancel_requested')
        with self.assertRaisesRegex(AdmissionError,'reconciliation'):self.pool.finish('task-0',False,'cancelled')
        with self.assertRaisesRegex(AdmissionError,'cannot_succeed'):self.pool.finish('task-0',True,'succeeded')
        self.pool.finish('task-0',True,'cancelled');self.assertEqual(self.pool.status()[0]['status'],'failed')


if __name__=='__main__':unittest.main()
