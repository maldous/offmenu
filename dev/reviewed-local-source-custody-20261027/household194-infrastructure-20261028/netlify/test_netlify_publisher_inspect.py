import importlib.util,unittest
from unittest.mock import patch
from pathlib import Path
s=importlib.util.spec_from_file_location('inspect_netlify',Path(__file__).with_name('netlify_publisher_inspect.py'));m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
TOKEN='nfp_TEST_ONLY_NOT_REAL_123456'
class Tests(unittest.TestCase):
 def replies(self):
  site={'id':m.SITE_ID,'name':m.SITE_NAME,'published_deploy':{'id':'current-id'}}
  return [{'id':'test-user'},site,[{'path':'/manifest.json','sha':'a'*40},{'path':'/recipes/manifest.json','sha':'b'*40}],site]
 def test_read_only_metadata(self):
  with patch.object(m,'get',side_effect=self.replies()) as get:r=m.inspect(TOKEN)
  self.assertEqual(r['current_public_file_count'],2);self.assertTrue(r['base_manifest_present']);self.assertNotIn(TOKEN,str(r));self.assertEqual(get.call_count,4)
 def test_changed_deploy(self):
  replies=self.replies();replies[-1]={**replies[-1],'published_deploy':{'id':'new'}}
  with patch.object(m,'get',side_effect=replies):
   with self.assertRaises(m.SafeStop):m.inspect(TOKEN)
 def test_other_site(self):
  replies=self.replies();replies[1]={**replies[1],'id':'other'}
  with patch.object(m,'get',side_effect=replies):
   with self.assertRaises(m.SafeStop):m.inspect(TOKEN)
 def test_no_arbitrary_endpoint(self):
  with self.assertRaises(m.SafeStop):m.get(TOKEN,'/api/v1/sites/another')
 def test_invalid_digest(self):
  replies=self.replies();replies[2][0]['sha']='not-digest'
  with patch.object(m,'get',side_effect=replies):
   with self.assertRaises(m.SafeStop):m.inspect(TOKEN)
 def test_reject_duplicate_files(self):
  replies=self.replies();replies[2].append(replies[2][0])
  with patch.object(m,'get',side_effect=replies):
   with self.assertRaises(m.SafeStop):m.inspect(TOKEN)
if __name__=='__main__':unittest.main()
