import unittest,copy
from unittest.mock import patch
import netlify_fixed_site_publisher as p
class Tests(unittest.TestCase):
 def descriptor(self):
  return {'schemaVersion':'offmenu-netlify-derived-delta/1','siteId':p.SITE,'qualificationSha256':'a'*64,'assemblyManifestSha256':'b'*64,'sourceCount':22,'sourceRecordTotal':22574390,'files':[{'path':x,'bytes':1,'sha256':'c'*64,'sha1':'d'*40} for x in ('/index.html','/recipes/manifest.json','/common-data/manifest.json','/common-data/manifest-checksums.json')]}
 def test_accept(self):self.assertEqual(len(p.validate_descriptor(self.descriptor(),'a'*64,'b'*64)),4)
 def test_scope(self):
  for x in ('/manifest.json','/.env','/recipes/data.json','/common-data/../../secret'):
   d=self.descriptor();d['files'].append({'path':x,'bytes':1,'sha256':'c'*64,'sha1':'d'*40})
   with self.assertRaises(p.Stop):p.validate_descriptor(d,'a'*64,'b'*64)
 def test_pin(self):
  with self.assertRaises(p.Stop):p.validate_descriptor(self.descriptor(),'e'*64,'b'*64)
 def test_coverage(self):
  d=self.descriptor();d['sourceRecordTotal']=11527
  with self.assertRaises(p.Stop):p.validate_descriptor(d,'a'*64,'b'*64)
 def test_duplicate(self):
  d=self.descriptor();d['files'].append(d['files'][0])
  with self.assertRaises(p.Stop):p.validate_descriptor(d,'a'*64,'b'*64)
 def test_paths(self):
  for x in ('relative','/../x','/a//b','/a?x','/a#x','/a\\x','/a\nx'):self.assertFalse(p.valid_path(x))
 def test_inventory_changed(self):
  with patch.object(p,'api',side_effect=[{'id':p.SITE,'name':'offmenu-corpus','published_deploy':{'id':'a'}},[],{'published_deploy':{'id':'b'}}]):
   with self.assertRaises(p.Stop):p.inventory('notreal','a')
 def test_wrong_api(self):
  with self.assertRaises(p.Stop):p.api('notreal','POST','/api/v1/sites/other/deploys',{})
 def test_prepare_complete_map_preserved(self):
  import sys,types,io
  d=self.descriptor();d['baseDeployId']='a'*24
  with patch.dict(sys.modules,{'wmill':types.SimpleNamespace(get_variable=lambda p:'private')}),patch.object(p,'ssh') as ssh,patch.object(p,'fetch',return_value=io.BytesIO(__import__('json').dumps(d).encode())),patch.object(p,'inventory',return_value={'/existing-app.js':'e'*40,'/recipes/retained.json':'f'*40}),patch.object(p,'api') as api:
   result=p.main('prepare','a'*64,12,'a'*64,'b'*64,'a'*24)
   self.assertEqual(result['status'],'prepared_no_mutation');self.assertEqual(result['preserved_current_files'],2);self.assertEqual(result['merged_files'],6);api.assert_not_called()
 def test_wrong_base_descriptor_never_mutates(self):
  import sys,types,io
  d=self.descriptor();d['baseDeployId']='b'*24
  with patch.dict(sys.modules,{'wmill':types.SimpleNamespace(get_variable=lambda p:'private')}),patch.object(p,'ssh'),patch.object(p,'fetch',return_value=io.BytesIO(__import__('json').dumps(d).encode())),patch.object(p,'api') as api:
   result=p.main('upload','a'*64,12,'a'*64,'b'*64,'a'*24)
   self.assertEqual(result['reason'],'descriptor_base_mismatch');api.assert_not_called()
 def fixture_upload(self,journal_effect=None,post_effect=None):
  import sys,types,io,contextlib
  d=self.descriptor();d['baseDeployId']='a'*24
  stack=contextlib.ExitStack();stack.enter_context(patch.dict(sys.modules,{'wmill':types.SimpleNamespace(get_variable=lambda p:'private')}));stack.enter_context(patch.object(p,'ssh'));stack.enter_context(patch.object(p,'fetch',return_value=io.BytesIO(__import__('json').dumps(d).encode())));stack.enter_context(patch.object(p,'inventory',return_value={}))
  journal=stack.enter_context(patch.object(p,'journal',side_effect=journal_effect))
  def call(token,method,path,body=None):
   if method=='POST':
    if post_effect:raise post_effect
    return {'id':'b'*24,'site_id':p.SITE,'title':'OffMenu qualified corpus '+'a'*64}
   if path.endswith('a1df1508-4bb9-4b55-ab1f-88611e456e61'):return {'published_deploy':{'id':'a'*24}}
   return {'id':'b'*24,'site_id':p.SITE,'state':'ready','required':[]}
  api=stack.enter_context(patch.object(p,'api',side_effect=call));return stack,journal,api
 def test_intent_exists_blocks_post(self):
  stack,journal,api=self.fixture_upload(p.Stop('journal_exists_or_failed_reconcile_only'))
  with stack:
   r=p.main('upload','a'*64,12,'a'*64,'b'*64,'a'*24)
   self.assertEqual(r['reason'],'journal_exists_or_failed_reconcile_only');self.assertFalse(any(c.args[1]=='POST' for c in api.call_args_list))
 def test_unknown_post_has_one_intent_no_retry(self):
  stack,journal,api=self.fixture_upload(post_effect=TimeoutError())
  with stack:
   r=p.main('upload','a'*64,12,'a'*64,'b'*64,'a'*24)
   self.assertEqual(journal.call_count,1);self.assertEqual(sum(c.args[1]=='POST' for c in api.call_args_list),1);self.assertIsNone(r['deploy_id'])
 def test_create_id_persisted_before_upload(self):
  stack,journal,api=self.fixture_upload()
  with stack:
   r=p.main('upload','a'*64,12,'a'*64,'b'*64,'a'*24)
   self.assertEqual(r['deploy_id'],'b'*24);self.assertEqual(journal.call_args_list[1].args[2]['event'],'deploy_created');self.assertEqual(journal.call_args_list[1].args[2]['deploy_id'],'b'*24)
 def test_journal_remote_code_compiles(self):
  import json,shlex
  from unittest.mock import MagicMock
  client=MagicMock();ch=client.get_transport.return_value.open_session.return_value;ch.exit_status_ready.return_value=True;ch.recv_exit_status.return_value=0
  p.journal(client,'a'*64,{'event':'resume_intent'},verify_deploy='b'*24)
  code=shlex.split(json.loads(ch.sendall.call_args.args[0])['command'])[2];compile(code,'<remote>','exec');self.assertIn('os.fsync(fd)',code)
