import unittest,sys,types,importlib.util
from unittest.mock import Mock,patch
wm=types.ModuleType('wmill');sdk=types.ModuleType('wmill.client');wm.client=sdk
sys.modules['wmill']=wm;sys.modules['wmill.client']=sdk
spec=importlib.util.spec_from_file_location('batch',__file__.replace('test_public_development_batch.py','offmenu_public_development_batch_20261028.py'));m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
class Tests(unittest.TestCase):
 def setUp(self):
  sdk.Windmill=Mock(return_value=object());wm.get_resource=Mock(return_value={'providers':[{'provider':p,'free_eligible':True,'enabled':'fixed_public_synthetic_development_tasks'} for p in ('groq','gemini')]});wm.run_script_async=Mock(return_value='01a180ed-6906-738f-2fed-3fa24a02357f')
 def test_plan_no_network(self):
  self.assertEqual(m.main()['status'],'ready');sdk.Windmill.assert_not_called()
 def test_private_reject(self):
  self.assertEqual(m.main('submit',input_class='private')['status'],'unsupported_data_class_no_dispatch');wm.run_script_async.assert_not_called()
 def test_unsupported(self):
  for tasks in [['private prompt'],['atomic_checkpoint_review']*2,list(m.CATALOG),['atomic_checkpoint_review','parallel_batch_test_design','capacity_admission_invariants']]:
   self.assertNotEqual(m.main('submit',tasks)['status'],'submitted')
  wm.run_script_async.assert_not_called()
 @patch.object(m,'api',return_value=[])
 def test_dispatch(self,api):
  r=m.main('submit',['atomic_checkpoint_review','manifest_verification_tests']);self.assertEqual(len(r['jobs']),2);self.assertEqual(wm.run_script_async.call_count,2)
  for call in wm.run_script_async.call_args_list:self.assertTrue(call.kwargs['args']['connection'].startswith('$res:'))
 @patch.object(m,'api')
 def test_hold(self,api):
  api.side_effect=[[{'id':'01a180ed-6906-738f-2fed-3fa24a02357f','success':True}],{'result':{'http_status':429}}]
  self.assertEqual(m.main('submit',['atomic_checkpoint_review'])['status'],'provider_hold_reconcile_required');wm.run_script_async.assert_not_called()
 def test_quality(self):
  self.assertEqual(m.disposition({'status':'completed','http_status':200}),'candidate_requires_human_or_deterministic_review_not_delivered')
  self.assertEqual(m.disposition({'status':'completed','output_truncated':True}),'incomplete_or_failed_reject')
 @patch.object(m,'api',return_value={'script_path':'u/admin/secret'})
 def test_results_scope(self,api):
  r=m.main('results',job_ids=['01a180ed-6906-738f-2fed-3fa24a02357f']);self.assertEqual(r['jobs'][0]['status'],'outside_task_allowlist')
 @patch.object(m,'api',return_value={'script_path':m.GROQ})
 def test_cancel_scope(self,api):
  r=m.main('cancel',job_ids=['01a180ed-6906-738f-2fed-3fa24a02357f']);self.assertEqual(r['jobs'][0]['status'],'not_created_by_this_entrypoint');self.assertEqual(api.call_count,1)
 def test_output_whitelist(self):
  r=m.safe_result({'api_key':'not-real','status':'completed','output':'x'*7000});self.assertNotIn('api_key',r);self.assertEqual(len(r['output']),6000)
if __name__=='__main__':unittest.main()
