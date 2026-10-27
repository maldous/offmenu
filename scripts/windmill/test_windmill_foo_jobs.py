"""Offline client tests; no network or secret access."""
import importlib.util
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import patch
spec=importlib.util.spec_from_file_location('jobs_client',Path(__file__).with_name('windmill_foo_jobs.py'))
client=importlib.util.module_from_spec(spec)
with patch.dict(sys.modules,{'paramiko':types.ModuleType('paramiko'),'wmill':types.ModuleType('wmill')}):spec.loader.exec_module(client)

class Channel:
    def __init__(self):self.out=bytearray(b'x'*100000);self.err=bytearray(b'y'*100000)
    def recv_ready(self):return bool(self.out)
    def recv_stderr_ready(self):return bool(self.err)
    def recv(self,n):d=self.out[:n];del self.out[:n];return d
    def recv_stderr(self,n):d=self.err[:n];del self.err[:n];return d
    def exit_status_ready(self):return not self.out and not self.err
    def recv_exit_status(self):return 0

class Tests(unittest.TestCase):
    def test_invalid_inputs_before_network(self):
        for args in ({'action':'shell'},{'job_id':'../x'},{'job_id':'ok','timeout_seconds':True},{'job_id':'ok','timeout_seconds':1801},{'action':'run','job_id':'ok','command':'\x00'}):
            with self.assertRaises(client.JobValidationFailure):client.main(**args)
    def test_business_failure_is_red_with_incident(self):
        with patch.object(client,'record_incident',return_value={'recorded':True}) as record:
            with self.assertRaises(client.BusinessJobFailure) as raised:
                client._job_result('run','job1',{'job_id':'job1','status':'failed','exit_code':7,'child_tree_gone':True})
            self.assertEqual(str(raised.exception),'BUSINESS_FAILED; incident=recorded')
            self.assertEqual(record.call_args.args,('job1','run','BUSINESS_FAILED','u/admin/foo_jobs_20261027'))
    def test_capture_error_does_not_make_failure_green_or_leak(self):
        with patch.object(client,'record_incident',side_effect=RuntimeError('SENSITIVE_SDK_TEXT')):
            with self.assertRaises(client.BusinessJobFailure) as raised:
                client._job_result('run','job1',{'job_id':'job1','status':'timed_out','child_tree_gone':True})
            self.assertEqual(str(raised.exception),'BUSINESS_TIMED_OUT; incident=unavailable')
            self.assertNotIn('SENSITIVE',str(raised.exception))
    def test_busy_and_active_duplicates_have_no_incidents(self):
        with patch.object(client,'record_incident') as record:
            for state in ('busy','running','starting','queued'):
                r=client._job_result('run','job1',{'job_id':'job1','status':state,'reconcile_required':False})
                self.assertTrue(r['transport_ok']);self.assertFalse(r['job_succeeded'])
            record.assert_not_called()
    def test_unknown_and_stale_active_require_reconciliation(self):
        with patch.object(client,'record_incident',return_value={'recorded':True}):
            for receipt in ({'job_id':'job1','status':'unknown'},{'job_id':'job1','status':'running','reconcile_required':True},{'job_id':'job1','status':'supervisor_error'},{'job_id':'job1','status':'succeeded','exit_code':0}):
                with self.assertRaises(client.OutcomeUnknown):client._job_result('run','job1',receipt)
    def test_status_and_cancel_do_not_create_incidents(self):
        with patch.object(client,'record_incident') as record:
            for action in ('status','cancel'):
                for state in ('failed','unknown','cancelled','cancellation_requested'):
                    self.assertTrue(client._job_result(action,'job1',{'job_id':'job1','status':state,'child_tree_gone':True})['transport_ok'])
            record.assert_not_called()
    def test_cancelled_run_is_quiet_red(self):
        with patch.object(client,'record_incident') as record:
            with self.assertRaises(client.BusinessCancelled):client._job_result('run','job1',{'job_id':'job1','status':'cancelled','child_tree_gone':True})
            record.assert_not_called()
    def test_blocked_returns_nonadmission_and_incident(self):
        with patch.object(client,'record_incident',return_value={'recorded':True}) as record:
            r=client._job_result('run','job1',{'job_id':'job1','status':'blocked_reconciliation'})
            self.assertFalse(r['admitted']);self.assertTrue(r['incident']['recorded'])
            self.assertEqual(record.call_args.args[2],'RECONCILIATION_BLOCKED')
    def test_receipt_identity_and_raw_fields(self):
        with patch.object(client,'record_incident',return_value={'recorded':True}):
            with self.assertRaises(client.OutcomeUnknown):client._job_result('run','job1',{'job_id':'other','status':'succeeded','exit_code':0,'child_tree_gone':True})
        r=client._job_result('status','job1',{'job_id':'job1','status':'succeeded','exit_code':0,'child_tree_gone':True,'raw_log':'NEVER_RETURN'})
        self.assertNotIn('raw_log',r['receipt']);self.assertNotIn('NEVER_RETURN',str(r))
    def test_status_missing_cleanup_not_confirmed(self):
        with patch.object(client,'record_incident') as record:
            for state in ('succeeded','failed','cancelled'):
                with self.assertRaises(client.OutcomeUnknown):client._job_result('status','job1',{'job_id':'job1','status':state,'exit_code':0})
            record.assert_not_called()
    def test_bounded_streams(self):
        r=client._drain(Channel(),10)
        self.assertEqual(len(r['stdout']),65536);self.assertEqual(len(r['stderr']),65536)
        self.assertTrue(all(r['truncated'].values()))
    def test_deadline(self):
        with patch.object(client.time,'monotonic',side_effect=[0,11]):
            with self.assertRaises(TimeoutError):client._drain(Channel(),10)

if __name__=='__main__':unittest.main()
