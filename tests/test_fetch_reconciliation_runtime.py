"""Offline authority and mandatory whole-invocation admission guards."""
from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import base64,hashlib,os,tempfile,time,unittest
from offmenu.refresh import fetch_reconciliation_runtime as f,reviewed_fetch_intake as i
from offmenu.refresh.core import canonical,sha,RefreshError
import test_actual988_stages as full

class RuntimeTests(unittest.TestCase):
 def setUp(self):
  self.c=f.configuration(allow_inactive=True)
 def test_adopted_config_metadata_admission_performs_no_io(self):
  with patch('socket.socket',side_effect=AssertionError('no network')):
   self.assertEqual(f.configuration()['additionalAuthorityPin']['commit'],'babf36f5a93fd1a07b8f7efadbf6e6dbdfbda58c')
 def fixture(self,root):
  c=deepcopy(self.c);c['status']='parent-reviewed-owner-manual'
  raw=(f.ROOT/f.AUTHORITY_PATH).read_bytes();p=Path(root)/f.AUTHORITY_PATH;p.parent.mkdir(parents=True);p.write_bytes(raw)
  c['additionalAuthorityPin']={'path':f.AUTHORITY_PATH,'sha256':sha(raw),'bytes':len(raw),'gitBlobSha':hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest(),'commit':'a'*40}
  p=Path(root)/f.CONFIG_PATH;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(canonical(c))
  return c
 def test_active_null_authority_rejected(self):
  c=deepcopy(self.c);c['status']='parent-reviewed-owner-manual';c['additionalAuthorityPin']=None
  with tempfile.TemporaryDirectory()as d:
   p=Path(d)/f.CONFIG_PATH;p.parent.mkdir(parents=True);p.write_bytes(canonical(c))
   with patch.object(f,'CONFIG_SHA256',sha(p.read_bytes())),self.assertRaises(RefreshError):f.configuration(d)
 def test_exact_adopted_authority_is_accepted(self):
  with tempfile.TemporaryDirectory()as d:
   c=self.fixture(d)
   with patch.object(f,'CONFIG_SHA256',sha(canonical(c))):self.assertEqual(f.configuration(d),c)
 def test_changed_authority_hash_length_or_scope_rejected(self):
  for key,value in [('sha256','f'*64),('bytes',1),('gitBlobSha','f'*40),('path','../escape')]:
   with self.subTest(key=key),tempfile.TemporaryDirectory()as d:
    c=self.fixture(d);c['additionalAuthorityPin'][key]=value
    with self.assertRaises(RefreshError):f.authority_document(c,root=d)
 def test_remote_authority_requires_same_current_bytes(self):
  p=full.g.publisher_module();raw=(f.ROOT/f.AUTHORITY_PATH).read_bytes();calls=[]
  class API:
   def call(self,method,path,payload=None,absent=False):
    calls.append((method,path));self.assertion=method=='GET'
    if path=='user':return {'id':p.OWNER_ID}
    if path=='repos/'+p.REPOSITORY:return {'id':p.REPOSITORY_ID,'full_name':p.REPOSITORY,'private':True,'owner':{'id':p.OWNER_ID},'permissions':{'push':True}}
    if '/git/ref/'in path:return {'object':{'sha':'b'*40}}
    if '/compare/'in path:return {'status':'ahead'}
    return {'type':'file','size':len(raw),'sha':p.blob_sha(raw),'encoding':'base64','content':base64.b64encode(raw).decode()}
  with tempfile.TemporaryDirectory()as d:
   c=self.fixture(d)
   with patch.object(f,'authority_document',return_value=({},raw)):
    self.assertEqual(f.verify_additional_authority(c,SimpleNamespace(publisher_module=lambda:p),API())['status'],'active-verified')
   self.assertTrue(all(m=='GET'for m,_ in calls));self.assertEqual(len(calls),5)
 def test_stale_or_missing_same_pass_metadata_rejected(self):
  with patch.object(f,'_REPORT_CONTEXT',None),self.assertRaises(RefreshError):f.extension(self.c,{},owner_runtime=object(),adapter=object(),current_holds=lambda s:[])
 def test_reviewed_head_snapshot_preserves_bundle_admission(self):
  before=f.heads.repository_bytes
  with f.reviewed_head_dependencies():
   manifest,sources,selection,runtime=f.heads.load_bundle()
   self.assertEqual(len(sources),5)
   self.assertEqual(sha((f.ROOT/f.HEAD_COLLECTOR_PATH).read_bytes()),f.HEAD_COLLECTOR_SHA)
   module=f.heads.collector_module(f.ROOT)
   self.assertEqual(module.ROOT,f.ROOT)
   self.assertTrue(hasattr(module,'OwnerRuntime'))
  self.assertIs(f.heads.repository_bytes,before)
 def guard(self):
  g=full.g;s=i.prepared_sources()[0];authority=object.__new__(i.FetchAuthority)
  authority._seal=i._SEAL;authority._sources={s['sourceKey']:canonical(s)};authority.selectionSHA256=self.c['transferSelectionSHA256'];authority.maximumRequests=26;authority.maximumBytes=644874240;authority.requiredMetadataTargets={}
  owner=object.__new__(i.OwnerExtension);owner.authority=authority;owner.metadata={'synthetic':'validated separately'}
  deadline=time.monotonic()+30;ext={'authority':authority,'owner_runtime':owner,'absoluteDeadline':deadline,'samePassMetadataSHA256':sha(canonical(owner.metadata))}
  meter=g.SharedBudget(26,644874240);child=meter.child(s['sourceKey'],s['hardTransferBytes']);fd=os.open('/dev/null',os.O_RDONLY);self.addCleanup(os.close,fd)
  coordinator=g.ParallelCoordinator(Path('/unused'),fd)
  return [s,ext,child,meter,coordinator,deadline,self.c]
 def test_complete_shared_execution_guard(self):
  with patch.object(f,'metadata_validator',return_value=True):self.assertTrue(full.g.validate_fetch_execution(*self.guard()))
 def test_missing_or_wrong_shared_limits_reject_before_transfer(self):
  for index in (1,2,3,4,5):
   with self.subTest(index=index):
    args=self.guard();args[index]=None
    with patch.object(f,'metadata_validator',side_effect=AssertionError('must reject first')),self.assertRaises(RefreshError):full.g.validate_fetch_execution(*args)
 def test_other_batch_meter_rejected(self):
  args=self.guard();args[2]=full.g.SharedBudget(26,644874240).child(args[0]['sourceKey'],args[0]['hardTransferBytes'])
  with self.assertRaises(RefreshError):full.g.validate_fetch_execution(*args)
 def test_modified_metadata_rejected(self):
  args=self.guard();args[1]['owner_runtime'].metadata['changed']=True
  with self.assertRaises(RefreshError):full.g.validate_fetch_execution(*args)
 def test_bad_metadata_validator_rejected(self):
  with patch.object(f,'metadata_validator',side_effect=ValueError('invalid-metadata-report')),self.assertRaises(ValueError):full.g.validate_fetch_execution(*self.guard())
 def test_lease_fd_must_be_live(self):
  args=self.guard();args[4].fd=-1
  with patch.object(f,'metadata_validator',return_value=True),self.assertRaises(OSError):full.g.validate_fetch_execution(*args)
 def test_no_arbitrary_transfer_budget(self):
  args=self.guard();args[3].maximumRequests=27
  with self.assertRaises(RefreshError):full.g.validate_fetch_execution(*args)

if __name__=='__main__':unittest.main()
