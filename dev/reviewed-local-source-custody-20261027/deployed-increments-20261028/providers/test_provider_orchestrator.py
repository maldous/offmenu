import sys,types,unittest,importlib.util
from unittest.mock import Mock,patch
wm=types.ModuleType('wmill');sdk=types.ModuleType('wmill.client');wm.client=sdk;sys.modules['wmill']=wm;sys.modules['wmill.client']=sdk
s=importlib.util.spec_from_file_location('o',__file__.replace('test_provider_orchestrator.py','offmenu_provider_orchestrator_20261028.py'));o=importlib.util.module_from_spec(s);s.loader.exec_module(o)
class T(unittest.TestCase):
 def setUp(self):
  sdk.Windmill=Mock(return_value=object());wm.run_script_async=Mock(return_value='01a180ed-6906-738f-2fed-3fa24a02357f');wm.get_resource=Mock(return_value={'providers':[{'provider':p,'free_eligible':True,'dispatch':{'ready':True}} for p in ['groq','gemini','cohere']]+[{'provider':'nous','dispatch':{'ready':False,'status':'auth_deferred'}}]})
 def test_plan(self):self.assertEqual(len(o.main()['providers']),4);self.assertEqual(o.main()['max_batch'],62)
 def test_private(self):self.assertEqual(o.main('submit',input_class='private')['submitted'],0)
 def test_duplicate(self):self.assertEqual(o.main('submit',[{'provider':'groq','task':'atomic_checkpoint_review'}]*2)['status'],'duplicate_provider_task_no_filler')
 @patch.object(o,'api',side_effect=lambda c,m,p,**kw: {} if p.startswith('scripts/') else [])
 def test_native_submit(self,a):
  r=o.main('submit',[{'provider':'cohere','task':'batch_user_help'},{'provider':'gemini','task':'manifest_verification_tests'}]);self.assertEqual(len(r['jobs']),2);self.assertEqual(wm.run_script_async.call_count,2)
 @patch.object(o,'api',side_effect=lambda c,m,p,**kw: {} if p.startswith('scripts/') else [])
 def test_independent_not_blocked(self,a):
  r=o.main('submit',[{'provider':'nous','task':'anything'},{'provider':'cohere','task':'batch_user_help'}]);self.assertEqual(len(r['jobs']),1);self.assertEqual(r['blocked'][0]['status'],'auth_deferred')
 @patch.object(o,'api',return_value=[{'running':True}]*62)
 def test_capacity(self,a):
  r=o.main('submit',[{'provider':'cohere','task':'batch_user_help'}]);self.assertEqual(r['status'],'no_eligible_work');wm.run_script_async.assert_not_called()
 @patch.object(o,'api',side_effect=[[],[{'success':True,'id':'01a180ed-6906-738f-2fed-3fa24a02357f'}],{'result':{'http_status':429}}])
 def test_429(self,a):self.assertEqual(o.main('check',[{'provider':'cohere','task':'batch_user_help'}])['blocked'][0]['http_status'],429)
 @patch.object(o,'api',return_value={'script_path':o.ROUTES['groq'][0]})
 def test_cancel(self,a):self.assertEqual(o.main('cancel',job_ids=['01a180ed-6906-738f-2fed-3fa24a02357f'])['jobs'][0]['status'],'not_owned_by_entrypoint')
class Cooldowns(unittest.TestCase):
 def test_expired_header(self):
  now=o.datetime(2026,10,28,6,tzinfo=o.timezone.utc)
  self.assertTrue(o.cooldown({'observed_at':'2026-10-28T05:00:00Z','retry_after':'60'}, {},'job',now)['retry_eligible'])
 def test_future_header(self):
  now=o.datetime(2026,10,28,5,tzinfo=o.timezone.utc)
  self.assertFalse(o.cooldown({'observed_at':'2026-10-28T05:00:00Z','retry_after':'60'}, {},'job',now)['retry_eligible'])
 def test_unknown_reset(self):self.assertEqual(o.cooldown({'retry_after':None},{},'job')['status'],'reset_metadata_required')
 def test_bound_registry(self):
  d={'cooldown_evidence_job':'job','cooldown_until':'2026-10-28T05:00:00Z','cooldown_evidence_basis':'observed_provider_reset'}
  self.assertTrue(o.cooldown({},d,'job',o.datetime(2026,10,28,6,tzinfo=o.timezone.utc))['retry_eligible'])
  self.assertFalse(o.cooldown({},d,'different')['retry_eligible'])
 def test_old429_allows_controlled_retry(self):
  sdk.Windmill=Mock(return_value=object());wm.get_resource=Mock(return_value={'providers':[{'provider':'groq','free_eligible':True,'dispatch':{'ready':True}}]})
  jid='01a180ed-6906-738f-2fed-3fa24a02357f'
  def api(c,m,p,**kw):
   if p=='jobs/list':return [{'success':True,'id':jid}] if 'script_path_exact' in kw.get('params',{}) else []
   if p.startswith('jobs_u/get/'):return {'id':jid,'result':{'http_status':429,'observed_at':'2020-01-01T00:00:00Z','retry_after':'60'}}
   return {}
  with patch.object(o,'api',side_effect=api):
   r=o.main('check',[{'provider':'groq','task':'atomic_checkpoint_review'}],retry_providers=['groq'])
   self.assertEqual(len(r['ready']),1)
   r=o.main('check',[{'provider':'groq','task':'atomic_checkpoint_review'}])
   self.assertEqual(len(r['ready']),0)
 def test_exact_openrouter(self):self.assertEqual(o.RESOURCES['openrouter'],'u/admin/intelligible_openrouter')
if __name__=='__main__':unittest.main()
