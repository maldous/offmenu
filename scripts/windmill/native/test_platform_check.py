import copy
import sys
import types
import unittest
from unittest.mock import patch
sys.modules.setdefault('paramiko',types.ModuleType('paramiko'))
sys.modules.setdefault('wmill',types.ModuleType('wmill'))
import windmill_platform_check as check


def report():
    return {'schema_version':1,'checked_at':'2026-10-27T22:00:00+00:00','mode':'health',
            'ok':True,'findings':[], 'counts':dict.fromkeys(check._COUNT_KEYS,0),
            'budgets':{'max_items':100,'max_bytes':67108864,'max_seconds':8,'bytes_read':0},
            'coverage':{'full_coverage':False,'scope':check._SCOPES['health'],
                        'selection_truncated':False,'stopped_reason':None,'selected_scope_complete':True},
            'status':'ok'}

class Tests(unittest.TestCase):
    def test_valid_report(self):
        self.assertEqual(check._check_receipt(report(),'health',100),report())
    def test_extra_raw_data_refused(self):
        r=report(); r['raw_log']='PRIVATE'
        with self.assertRaisesRegex(check.PlatformCheckFailure,'RECEIPT_INVALID'): check._check_receipt(r,'health',100)
    def test_unrecognized_finding_refused(self):
        r=report(); r['findings']=[{'code':'SECRET_DETAILS','severity':'info'}]
        with self.assertRaises(check.PlatformCheckFailure): check._check_receipt(r,'health',100)
    def test_path_data_in_finding_refused(self):
        r=report(); r['findings']=[{'code':'STALE_ACTIVE_JOB','severity':'error','raw_path':'x'}]
        with self.assertRaises(check.PlatformCheckFailure): check._check_receipt(r,'health',100)
    def test_inconsistent_coverage_refused(self):
        r=report(); r['coverage']['selection_truncated']=True
        with self.assertRaises(check.PlatformCheckFailure): check._check_receipt(r,'health',100)
    def test_partial_without_errors_returns_explicit_incomplete_no_incident(self):
        r=report(); r['ok']=False; r['status']='incomplete'; r['coverage'].update(selection_truncated=True,selected_scope_complete=False)
        with patch.object(check,'_check_native_state'),patch.object(check,'_remote_check',return_value=r),patch.object(check,'record_incident') as record:
            result=check.main(); self.assertFalse(result['ok']); self.assertEqual(result['status'],'incomplete'); record.assert_not_called()
    def test_concurrent_checkpoint_advance_is_incomplete_no_incident(self):
        r=report(); r.update(mode="verify",ok=False,status="incomplete",findings=[{"code":"CHECKPOINT_ADVANCED","severity":"warning","checkpoint_hash":"a"*64}])
        r["coverage"].update(scope=check._SCOPES["verify"],selected_scope_complete=False); r["counts"]["items_skipped"]=1
        self.assertEqual(check._check_receipt(r,"verify",100),r)
        with patch.object(check,"_check_native_state"),patch.object(check,"_remote_check",return_value=r),patch.object(check,"record_incident") as record:
            result=check.main("verify"); self.assertFalse(result["ok"]); self.assertEqual(result["status"],"incomplete"); record.assert_not_called()
    def test_info_historical_failure_does_not_trigger_incident(self):
        r=report(); r['findings']=[{'code':'COMPLETED_NON_SUCCESS','severity':'info','job_id':'fixture','status':'failed'}]
        with patch.object(check,'_check_native_state'),patch.object(check,'_remote_check',return_value=r),patch.object(check,'record_incident') as record:
            self.assertTrue(check.main()['ok']); record.assert_not_called()
    def test_error_findings_record_and_fail(self):
        r=report(); r.update(ok=False,status='findings',findings=[{'code':'STALE_ACTIVE_JOB','severity':'error','job_id':'fixture'}])
        with patch.object(check,'_check_native_state'),patch.object(check,'_remote_check',return_value=r),patch.object(check,'record_incident',return_value={'resource_path':'safe'}) as record,patch('builtins.print'):
            with self.assertRaisesRegex(check.PlatformCheckFailure,'HEALTH_FINDINGS'): check.main()
            record.assert_called_once(); self.assertEqual(record.call_args.args[2],'HEALTH_FINDINGS')
    def test_raw_transport_exception_is_sanitized(self):
        with patch.object(check,'_check_native_state'),patch.object(check,'_remote_check',side_effect=RuntimeError('RAW_SECRET')),patch.object(check,'record_incident',return_value={'resource_path':'safe'}),patch('builtins.print'):
            with self.assertRaisesRegex(check.PlatformCheckFailure,'CHECK_TRANSPORT_FAILED') as e: check.main()
            self.assertNotIn('RAW_SECRET',str(e.exception))
    def test_incident_persistence_failure_never_masks_failed_check(self):
        with patch.object(check,'_check_native_state',side_effect=RuntimeError('RAW_SECRET')),patch.object(check,'record_incident',side_effect=check.IncidentError('INCIDENT_READ_REFUSED')),patch('builtins.print'):
            with self.assertRaisesRegex(check.PlatformCheckFailure,'CHECK_TRANSPORT_FAILED'): check.main()
    def test_invalid_inputs_do_not_connect(self):
        for mode,count in [('rm -rf',100),('health',True),('verify',101),('health',0)]:
            with patch.object(check,'_remote_check') as remote:
                with self.assertRaisesRegex(ValueError,'CHECK_INPUT_INVALID'): check.main(mode,count)
                remote.assert_not_called()

if __name__ == '__main__': unittest.main()
