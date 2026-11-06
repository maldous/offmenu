import unittest,types,sys,io,json
from unittest.mock import patch
import netlify_publication_seed as s
class SeedTests(unittest.TestCase):
 def test_incomplete_proof_never_writes(self):
  with patch.dict(sys.modules,{'wmill':types.SimpleNamespace(get_variable=lambda p:'private')}),patch.object(s,'ssh'),patch.object(s,'fetch',return_value=io.BytesIO(json.dumps({'status':'pending','packageCount':8}).encode())),patch.object(s,'write_seed') as write:
   r=s.main('a'*24,'b'*64,10);self.assertEqual(r['reason'],'proof_incomplete');write.assert_not_called()
 def test_public_digest_mismatch_never_writes(self):
  proof={'status':'all-packages-streamed-global-identities-references-and-provenance-checked','packageCount':8}
  with patch.dict(sys.modules,{'wmill':types.SimpleNamespace(get_variable=lambda p:'private')}),patch.object(s,'ssh'),patch.object(s,'fetch',return_value=io.BytesIO(json.dumps(proof).encode())),patch.object(s,'inventory',return_value={'/index.html':'a'*40,'/manifest.json':'b'*40,'/recipes/manifest.json':'c'*40}),patch.object(s.http.client,'HTTPSConnection') as conn,patch.object(s,'write_seed') as write:
   conn.return_value.getresponse.return_value.status=200;conn.return_value.getresponse.return_value.read.return_value=b'bad';r=s.main('a'*24,'b'*64,10);self.assertEqual(r['reason'],'public_seed_digest_mismatch');write.assert_not_called()
 def test_seed_remote_code_compiles_and_fsyncs(self):
  with patch.object(s,'remote_safe') as remote:
   s.write_seed(None,'/manifest.json',b'{"ok":true}')
   self.assertEqual(remote.call_count,3)
   for call in remote.call_args_list:compile(call.args[1],'<remote>','exec')
   self.assertIn('os.fsync(f)',remote.call_args_list[1].args[1]);self.assertIn('os.fsync(fd)',remote.call_args_list[1].args[1])
