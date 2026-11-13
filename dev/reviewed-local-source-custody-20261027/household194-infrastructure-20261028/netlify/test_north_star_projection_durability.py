import contextlib,io,json,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
import prepare_north_star_projection_reviewed as M
from test_north_star_publication import NorthStarTests
class DurableTests(unittest.TestCase):
 def setup_case(self,root):
  src=root/'source';src.mkdir();out=root/'final-common-publication/north-star-publication-delta'
  m=NorthStarTests().manifest();body=b'data';m['files'][0]['sha256']=M.sha(body)
  shard=src/m['files'][0]['key'];shard.parent.mkdir(parents=True);shard.write_bytes(body)
  mb=json.dumps(m).encode();(src/'manifest.json').write_bytes(mb)
  proof=NorthStarTests().proof();proof['producerManifestSha256']=M.sha(mb);pb=json.dumps(proof).encode();(src/'reviewed-consumer-proof.json').write_bytes(pb)
  args=['prog','--producer-manifest-sha256',M.sha(mb),'--consumer-proof-sha256',M.sha(pb),'--served-base-manifest-sha256','e'*64,'--base-deploy-id','f'*24]
  return src,out,args
 def invoke(self,root,src,out,args):
  with patch.object(M,'BASE',root),patch.object(M,'SOURCE',src),patch.object(M,'OUT',out),patch('sys.argv',args),contextlib.redirect_stdout(io.StringIO()):M.main()
 def test_complete_descriptor_last_and_idempotent_refusal(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);src,out,args=self.setup_case(root);self.invoke(root,src,out,args)
   desc=root/'final-common-publication/north-star-publication-delta.json';before=desc.read_bytes()
   for f in json.loads(before)['files']:
    b=(out/f['path'].lstrip('/')).read_bytes();self.assertEqual(M.sha(b),f['sha256'])
   with self.assertRaises(AssertionError):self.invoke(root,src,out,args)
   self.assertEqual(desc.read_bytes(),before)
 def test_failure_before_descriptor_preserves_delta_and_foreign_staging(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);src,out,args=self.setup_case(root);out.parent.mkdir();foreign=out.parent/(out.name+'.tmp-foreign');foreign.mkdir();(foreign/'keep').write_bytes(b'keep')
   with patch.object(M,'publish_descriptor',side_effect=OSError('injected')):
    with self.assertRaises(OSError):self.invoke(root,src,out,args)
   self.assertTrue(out.is_dir());self.assertFalse((out.parent/'north-star-publication-delta.json').exists());self.assertEqual((foreign/'keep').read_bytes(),b'keep')
 def test_exclusive_descriptor_does_not_overwrite(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)/'descriptor';p.write_bytes(b'old')
   with self.assertRaises(FileExistsError):M.publish_descriptor(p,b'new')
   self.assertEqual(p.read_bytes(),b'old')
 def test_fsync_failure_before_link_no_descriptor(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)/'descriptor'
   with patch.object(M.os,'fsync',side_effect=OSError('injected')):
    with self.assertRaises(OSError):M.publish_descriptor(p,b'new')
   self.assertFalse(p.exists())
if __name__=='__main__':unittest.main()
