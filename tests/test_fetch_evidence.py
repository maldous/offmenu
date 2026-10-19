"""Exact sanitized metadata custody and bounded publication parts, offline."""
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import json,os,tempfile,unittest
from offmenu.refresh import fetch_evidence as f

class EvidenceTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name);(self.root/'collection').mkdir()
  self.value={'schemaVersion':'synthetic','rows':[{'id':'known'}]}
  def directory(p,a=None):p.mkdir(exist_ok=True);p.chmod(0o700);return p
  def write(p,v):
   raw=f.canonical(v)
   try:fd=os.open(p,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
   except FileExistsError:
    if p.read_bytes()!=raw:raise ValueError('conflict')
   else:
    with os.fdopen(fd,'wb')as stream:stream.write(raw)
  self.a=SimpleNamespace(owned_directory=lambda p:p,write_immutable=write);self.directory=directory
 def tearDown(self):self.tmp.cleanup()
 def save(self,value=None):return f.save('metadata-reconciliation',value or self.value,output_root=self.root,adapter=self.a,validator=lambda v:None,private_directory=self.directory)
 def test_exact_save_load_idempotency(self):
  ref=self.save();self.assertEqual(f.load(ref,output_root=self.root,validator=lambda v:None),self.value);self.assertEqual(self.save(),ref)
 def test_no_arbitrary_path_field(self):
  r=self.save();r['path']='/private/source'
  with self.assertRaises(f.RefreshError):f.load(r,output_root=self.root,validator=lambda v:None)
 def test_unknown_kind_rejected(self):
  with self.assertRaises(f.RefreshError):f.save('body',{},output_root=self.root,adapter=self.a,validator=lambda v:None,private_directory=self.directory)
 def test_injected_body_rejected_before_save(self):
  with self.assertRaises(ValueError):f.save('metadata-reconciliation',{},output_root=self.root,adapter=self.a,validator=lambda v:(_ for _ in ()).throw(ValueError()),private_directory=self.directory)
  self.assertFalse((self.root/'collection/fetch-evidence').exists())
 def test_changed_digest_rejected(self):
  r=self.save();p=next((self.root/'collection/fetch-evidence').iterdir());p.write_bytes(b'x'*r['bytes'])
  with self.assertRaises(f.RefreshError):f.load(r,output_root=self.root,validator=lambda v:None)
 def test_public_permissions_rejected(self):
  r=self.save();next((self.root/'collection/fetch-evidence').iterdir()).chmod(0o644)
  with self.assertRaises(f.RefreshError):f.load(r,output_root=self.root,validator=lambda v:None)
 def test_link_rejected(self):
  r=self.save();p=next((self.root/'collection/fetch-evidence').iterdir());os.link(p,p.with_name('copy'))
  with self.assertRaises(f.RefreshError):f.load(r,output_root=self.root,validator=lambda v:None)
 def test_symlink_rejected(self):
  r=self.save();p=next((self.root/'collection/fetch-evidence').iterdir());q=p.with_name('copy');p.rename(q);p.symlink_to(q)
  with self.assertRaises(f.RefreshError):f.load(r,output_root=self.root,validator=lambda v:None)
 def test_declared_bound_rejected(self):
  r=self.save();r['bytes']=4*1024**2+1
  with self.assertRaises(f.RefreshError):f.validate_reference(r)
 def test_controls_and_rows_reconstruct_exactly(self):
  r=self.save();parts=f.publication_parts(r,self.value,lambda k,v:[(k+'-000.json',f.canonical({'rows':v}))])
  control=json.loads(parts[0][1]);digest=control.pop('reconstructedReportSHA256');control['rows']=json.loads(parts[1][1])['rows']
  self.assertEqual(f.sha(f.canonical(control)),digest)
 def test_chunk_content_identity_mismatch(self):
  with self.assertRaises(f.RefreshError):f.publication_parts(self.save(),{'rows':[]},lambda *a:[])
 def test_publisher_load_revalidates_schema(self):
  with self.assertRaises(ValueError):f.load(self.save(),output_root=self.root,validator=lambda v:(_ for _ in ()).throw(ValueError()))

if __name__=='__main__':unittest.main()
