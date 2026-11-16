import base64
import json
import os
from pathlib import Path
import types
import unittest
from unittest.mock import patch


class Wrapper(unittest.TestCase):
    def setUp(self):
        root = Path(__file__).resolve().parent
        self.calls = []
        self.sdk = types.SimpleNamespace(run_script_by_path_async=self.enqueue)
        self.ns = {'base64':base64,'json':json,'wmill':self.sdk,
                   '_QUERY_SOURCE_B64':base64.b64encode((root/'duckdb_query.py').read_bytes()).decode(),
                   '_confined_exec':lambda command:{'ok':True,'stdout':json.dumps({'job_id':'query-test','status':'not_found'}),'truncated':{}}}
        exec((root/'wrapper_entrypoint.py').read_text(),self.ns)
        self.env = patch.dict(os.environ, {'WM_WORKSPACE':'offmenu','WM_USERNAME':'admin'})
        self.env.start(); self.addCleanup(self.env.stop)
        self.inputs = {'job_id':'query-test','input_path':'/offmenu/data/final.parquet',
                       'sql_path':'/offmenu/queries/report.sql','threads':8,'memory_gib':1,'spill_gib':1,'result_gib':1}

    def enqueue(self, path, args):
        self.calls.append((path,args))
        return '00000000-0000-0000-0000-000000000001'

    def test_plan_does_not_submit(self):
        result=self.ns['main'](**self.inputs)
        self.assertFalse(result['submitted']); self.assertEqual(self.calls,[])
        self.assertEqual(result['plan']['resources']['cpu_millis'],8000)

    def test_submit_exact_reservation_and_one_child(self):
        plan=self.ns['main'](**self.inputs)['plan']
        result=self.ns['main'](action='submit',**self.inputs)
        self.assertEqual(len(self.calls),1)
        path,args=self.calls[0]
        self.assertEqual(path,'u/admin/foo_jobs_20261027')
        self.assertEqual(args['resources'],plan['resources'])
        self.assertLess(len(args['command'].encode()),32000)
        self.assertIsNone(result['admitted'])

    def test_mismatched_status_child_rejected(self):
        self.sdk.get_job=lambda job:{'script_path':'different','args':{'job_id':'query-test'}}
        with self.assertRaisesRegex(ValueError,'MISMATCH'):
            self.ns['main'](action='status',job_id='query-test',windmill_job_id='00000000-0000-0000-0000-000000000001')

    def test_busy_admission_not_hidden_by_green_child(self):
        self.sdk.get_job=lambda job:{'script_path':'u/admin/foo_jobs_20261027','args':{'job_id':'query-test'},'success':True}
        self.sdk.get_job_status=lambda job:'COMPLETED'
        self.sdk.get_result=lambda job:{'job_id':'query-test','admitted':False,'job_succeeded':False,'receipt':{'status':'busy','reason':'capacity_cpu_reserved'}}
        value=self.ns['main'](action='status',job_id='query-test',windmill_job_id='00000000-0000-0000-0000-000000000001')
        self.assertFalse(value['admission']['admitted'])
        self.assertEqual(value['admission']['reason'],'capacity_cpu_reserved')

    def test_no_implicit_retry_or_cancel(self):
        result=self.ns['main'](action='results',job_id='query-test')
        self.assertEqual(self.calls,[])
        self.assertEqual(result['query']['status'],'not_found')

    def test_cancel_is_explicit_single_request(self):
        result=self.ns['main'](action='cancel',job_id='query-test')
        self.assertFalse(result['terminal'])
        self.assertEqual(self.calls[0][1],{'action':'cancel','job_id':'query-test'})

    def test_owner_guard(self):
        with patch.dict(os.environ,{'WM_USERNAME':'someone_else'}):
            with self.assertRaisesRegex(ValueError,'OWNER_REQUIRED'):
                self.ns['main'](**self.inputs)


if __name__=='__main__': unittest.main()
