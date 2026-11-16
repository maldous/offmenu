import contextlib,importlib.util,io,json,unittest
from unittest.mock import patch,MagicMock
from pathlib import Path
s=importlib.util.spec_from_file_location('imp',Path(__file__).with_name('import_netlify_token.py')); m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
TOKEN='nfp_TEST_TOKEN_NOT_REAL_123456'
def enc(obj):return json.dumps(obj).encode()
class Fake:
 def __init__(self,replies):self.replies=list(replies);self.calls=[]
 def call(self,*args):self.calls.append(args);r=self.replies.pop(0);return r
class Tests(unittest.TestCase):
 def wm(self,exists=False,private=True):
  return Fake([(200,enc({'username':'admin'})),(200,enc({'is_secret':True,'extra_perms':{} if private else {'g/all':False}})) if exists else (404,b''),(201,b''),(200,enc({'is_secret':True,'extra_perms':{}}))])
 def net(self,name=None):return Fake([(200,enc({'id':'test-user'})),(200,enc({'id':m.SITE_ID,'name':name or m.SITE_NAME}))])
 def run_it(self,w,n,apply=False):
  output=io.StringIO()
  with contextlib.redirect_stdout(output):m.run(w,n,TOKEN,apply)
  self.assertNotIn(TOKEN,output.getvalue());return output.getvalue()
 def test_dry_run(self):
  w=self.wm();self.assertIn('would_create',self.run_it(w,self.net()));self.assertEqual(len(w.calls),2)
 def test_create_metadata_only_verification(self):
  w=self.wm();self.assertIn('created_verified',self.run_it(w,self.net(),True));self.assertEqual(len(w.calls),4)
  payload=w.calls[2][2];self.assertEqual(payload['value'],TOKEN);self.assertIs(payload['is_secret'],True)
  self.assertTrue(w.calls[-1][1].endswith('?decrypt_secret=false'))
 def test_existing_never_overwritten(self):
  w=self.wm(True);self.assertIn('existing_private_secret_preserved',self.run_it(w,self.net(),True));self.assertEqual(len(w.calls),2)
 def test_shared_existing_stops(self):
  w=self.wm(True,False)
  with self.assertRaises(m.Stop):self.run_it(w,self.net(),True)
  self.assertEqual(len(w.calls),2)
 def test_wrong_site_stops_before_write(self):
  w=self.wm()
  with self.assertRaises(m.Stop):self.run_it(w,self.net('wrong'),True)
  self.assertEqual(len(w.calls),2)
 def test_wrong_workspace_identity(self):
  w=Fake([(200,enc({'username':'other'}))])
  with self.assertRaises(m.Stop):self.run_it(w,self.net(),True)
  self.assertEqual(len(w.calls),1)
 def test_missing_environment(self):
  with self.assertRaises(m.Stop):m.exported_token({})
 def test_token_newline_rejected(self):
  with self.assertRaises(m.Stop):m.exported_token({'NETLIFY_API_TOKEN':TOKEN+'\n'})
 def test_root_stops_without_file_read(self):
  with patch.object(m.os,'getuid',return_value=0),patch.object(m.os,'open') as op:
   with self.assertRaises(m.Stop):m.load_token()
   op.assert_not_called()
 def test_sudo_stops(self):
  with patch.object(m.os,'getuid',return_value=1000),patch.dict(m.os.environ,{'SUDO_USER':'user'}),patch.object(m.os,'open') as op:
   with self.assertRaises(m.Stop):m.load_token()
   op.assert_not_called()
 def test_netlify_write_or_other_site_rejected(self):
  a=m.API(TOKEN,m.NETLIFY_HOST)
  for method,path in [('POST','/api/v1/sites/'+m.SITE_ID+'/deploys'),('GET','/api/v1/sites/other')]:
   with self.assertRaises(m.Stop):a.call(method,path)
 def test_redirect_not_followed_and_token_not_leaked(self):
  conn=MagicMock();r=conn.getresponse.return_value;r.status=302;r.read.return_value=TOKEN.encode()
  with patch.object(m.http.client,'HTTPSConnection',return_value=conn):
   with self.assertRaises(m.Stop) as caught:m.API(TOKEN).call('GET',m.BASE+'/users/whoami')
  self.assertNotIn(TOKEN,str(caught.exception));self.assertEqual(conn.request.call_count,1);conn.close.assert_called_once()
 def test_create_failure_no_retry(self):
  w=self.wm();w.replies[2]=(404,b'')
  with self.assertRaises(m.Stop):self.run_it(w,self.net(),True)
  self.assertEqual(len(w.calls),3)
 def test_plaintext_existing_stops(self):
  w=self.wm(True);w.replies[1]=(200,enc({'is_secret':False}))
  with self.assertRaises(m.Stop):self.run_it(w,self.net(),True)
 def test_unsupported_host(self):
  with self.assertRaises(m.Stop):m.API(TOKEN,'example.com')
if __name__=='__main__':unittest.main()
