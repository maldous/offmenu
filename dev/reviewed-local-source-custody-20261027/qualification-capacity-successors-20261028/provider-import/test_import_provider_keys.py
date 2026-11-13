import contextlib,io,json,unittest
import import_provider_keys as m
class Fake:
 def __init__(self,existing=False,deny=False): self.calls=[]; self.existing=existing; self.deny=deny; self.created=set()
 def call(self,method,path,payload=None):
  self.calls.append((method,path,payload))
  if path.endswith('/whoami'): return 200,b'{"username":"admin"}'
  if method=='POST': self.created.add(payload['path']); return 201,b''
  if self.deny: raise m.Stop('HTTP 403; required_scope=True; gateway_html=False')
  present=self.existing or any('/get/'+x+'?' in path for x in self.created)
  return (200,b'{"is_secret":true}') if present else (404,b'')
class Tests(unittest.TestCase):
 def run_silent(self,a,e,apply=False):
  with contextlib.redirect_stdout(io.StringIO()) as out: m.run(a,e,apply)
  self.assertNotIn('supersecret',out.getvalue()); return out.getvalue()
 def test_dryrun(self):
  a=Fake(); self.run_silent(a,{'GROQ_API_KEY':'supersecret'})
  self.assertTrue(all(x[0]=='GET' for x in a.calls))
 def test_existing(self):
  a=Fake(True); self.run_silent(a,{'GROQ_API_KEY':'supersecret'},True)
  self.assertFalse(a.created)
 def test_403_no_writes(self):
  a=Fake(deny=True)
  with self.assertRaises(m.Stop): self.run_silent(a,{'GROQ_API_KEY':'supersecret'},True)
  self.assertFalse(a.created)
 def test_aliases_preserved(self):
  a=Fake(); out=self.run_silent(a,{'GROQ_API_KEY':'supersecretA','GROQ_TOKEN':'supersecretB'},True)
  self.assertEqual(len(a.created),2); self.assertIn('groq__groq_token',out)
 def test_all_preflight_first(self):
  a=Fake(); self.run_silent(a,{'GROQ_API_KEY':'supersecret','MISTRAL_API_KEY':'supersecret'},True)
  first=next(i for i,x in enumerate(a.calls) if x[0]=='POST')
  self.assertEqual(first,3)
 def test_no_infra_and_metadata_only(self):
  a=Fake(); self.run_silent(a,{'GROQ_API_KEY':'supersecret','GITHUB_TOKEN':'DO-NOT-IMPORT'},True)
  self.assertEqual(len(a.created),1)
  self.assertTrue(all('decrypt_secret=false' in path for method,path,_ in a.calls if '/variables/get/' in path))
 def test_identity_stop(self):
  class Wrong(Fake):
   def call(self,*args): return 200,b'{"username":"someone_else"}'
  with self.assertRaises(m.Stop): self.run_silent(Wrong(),{},True)
 def test_late_preflight403(self):
  class Late(Fake):
   def call(self,method,path,payload=None):
    if 'mistral?' in path: raise m.Stop('HTTP 403')
    return super().call(method,path,payload)
  a=Late()
  with self.assertRaises(m.Stop): self.run_silent(a,{'GROQ_API_KEY':'supersecret','MISTRAL_API_KEY':'supersecret'},True)
  self.assertFalse(a.created)
 def test_create_collision_no_update(self):
  class Collision(Fake):
   def call(self,method,path,payload=None):
    if method=='POST': raise m.Stop('HTTP 400')
    return super().call(method,path,payload)
  a=Collision()
  with self.assertRaises(m.Stop): self.run_silent(a,{'GROQ_API_KEY':'supersecret'},True)
  self.assertFalse(a.created)
 def test_classifier_no_body_echo(self):
  result=m.classify(403,b'Required scope: secretvalue cloudflare')
  self.assertNotIn('secretvalue',result); self.assertIn('True',result)
if __name__=='__main__': unittest.main()
