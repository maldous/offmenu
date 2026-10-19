"""Exact candidate conversion, bounded original observation, and inactive guards."""
from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import hashlib,json,os,tempfile,time,unittest
from offmenu.refresh import reviewed_fetch_intake as f
from offmenu.refresh.core import canonical,sha,RefreshError
ROOT=Path(__file__).resolve().parents[1]

class Contracts(unittest.TestCase):
 @classmethod
 def setUpClass(cls):cls.bundle=f.candidate_bundle();cls.sources=f.prepared_sources()
 def test_exact26_caps_and_fetch_only(self):
  self.assertEqual(len(self.sources),26);self.assertEqual(sum(s['hardTransferBytes']for s in self.sources),644874240)
  for s,r in zip(self.sources,self.bundle['records']):
   self.assertEqual(s['url'],r['contract']['request']['url']);self.assertEqual(s['expectedResponse']['content-type'],r['contract']['response']['acceptedContentTypes'][0])
   self.assertEqual(s['mediaIntake']['permissions'],{'read':True,'copy':True,'extract':False})
   self.assertEqual(s['mediaIntake']['maximumRequests'],1);self.assertIsNone(s['mediaIntake']['redirect'])
 def test_four_json_mime_not_suffix_guess(self):
  rows=[s for s in self.sources if s['expectedResponse']['content-type']=='application/json'];self.assertEqual(len(rows),4)
  for s in rows:self.assertEqual(s['mediaIntake']['originalFilename'],'original.json')
 def test_three_download_pdfs_have_strict_mime(self):
  rows=[s for s in self.sources if '/download/' in s['url'] and s['sourceKey'].startswith('so-')];self.assertEqual(len(rows),3)
  for s in rows:self.assertEqual(s['expectedResponse'],{'content-type':'application/pdf'})
 def test_rss_mime_never_union_xml(self):
  s=next(x for x in self.sources if x['sourceKey']=='mk-15-fva-rss')
  self.assertEqual(s['expectedResponse'],{'content-type':'application/rss+xml'})
  with self.assertRaises(RefreshError):f.legacy_intake.checked_headers({'Content-Type':'application/xml','Content-Length':'10'},s)
 def test_all_single_mimes_closed(self):
  for row in self.bundle['records']:
   r=deepcopy(row);r['contract']['response']['acceptedContentTypes']=[]
   with self.assertRaises(RefreshError):f.convert_record(r)
 def test_source_conditions_not_discarded(self):
  for s,r in zip(self.sources,self.bundle['records']):self.assertEqual(s['mediaIntake']['retainedConditions'],r['retainedConditions'])
 def test_new_source_hold_blocks(self):
  row=deepcopy(self.bundle['records'][0]);row['retainedConditions']['sourceStageHolds']=['do-not-read']
  with self.assertRaises(RefreshError):f.convert_record(row)
 def test_arbitrary_endpoint_changes_do_not_gain_authority(self):
  with self.assertRaises(RefreshError):f.run_selected(self.sources[0],owner_runtime=object())
 def test_inactive_has_zero_transport_or_filesystem(self):
  with patch('socket.socket',side_effect=AssertionError('network')),patch('os.open',side_effect=AssertionError('open')):
   with self.assertRaises(RefreshError):f.run_selected(self.sources[0],owner_runtime=object())
 def test_old_known_five_remain_closed(self):
  with self.assertRaises(RefreshError):f.legacy_intake.validate_source(self.sources[0])
 def test_candidate_pin_changed_rejected(self):
  with tempfile.TemporaryDirectory()as d:
   p=Path(d)/f.CANDIDATE_PATH;p.parent.mkdir(parents=True);p.write_bytes(canonical(self.bundle))
   with self.assertRaises(RefreshError):f.candidate_bundle(d)
 def test_no_active_selection_from_candidates(self):
  with self.assertRaises(RefreshError):f.admit_authority(None,expected_selection_sha256=None,baseline_manifest_raw=b'',baseline_selection_raw=b'')
 def test_changed_request_and_budget_reject(self):
  for edit in (lambda r:r['contract']['request'].update(method='HEAD'),lambda r:r['contract']['bounds'].update(maxRetries=1),lambda r:r['contract']['request'].update(cookies=True),lambda r:r['contract']['permissions'].update(proposedExtract=True)):
   row=deepcopy(self.bundle['records'][0]);edit(row)
   with self.assertRaises(RefreshError):f.convert_record(row)

class Observation(unittest.TestCase):
 def observe(self,data,source=None):
  source=source or f.prepared_sources()[0]
  with tempfile.TemporaryDirectory()as folder:
   path=Path(folder)/'original.partial';path.write_bytes(data);path.chmod(0o600)
   result=SimpleNamespace(path=path,bytes=len(data),sha256=sha(data),provenance={'originalAcquiredAt':'2026-10-19T00:00:00Z'})
   return f.validate_original(result,source,time.monotonic()+10,SimpleNamespace(deadline_check=lambda d:None))
 def test_pdf_hash_extent_not_parser_claim(self):
  r=self.observe(b'%PDF-1.7\n'+b'a'*150000+b'\n%%EOF\n');self.assertEqual(r['bytes'],150016)
  self.assertEqual(r['localValidationBytesRead'],r['bytes']);self.assertFalse(r['extractionPerformed']);self.assertFalse(r['fullStructuralValidation'])
 def test_nonpdf_and_missing_eof_reject(self):
  for body in (b'<!doctype html>',b'%PDF-1.7\nnot-complete'):
   with self.assertRaises(RefreshError):self.observe(body)
 def test_changed_hash_rejects(self):
  with tempfile.TemporaryDirectory()as d:
   p=Path(d)/'file';p.write_bytes(b'%PDF-1.7\n%%EOF');p.chmod(0o600)
   with self.assertRaises(RefreshError):f.validate_original(SimpleNamespace(path=p,bytes=p.stat().st_size,sha256='a'*64),f.prepared_sources()[0],time.monotonic()+1,SimpleNamespace(deadline_check=lambda d:None))
 def test_json_sniff_not_semantic_parse(self):
  s=next(s for s in f.prepared_sources()if s['expectedResponse']['content-type']=='application/json')
  r=self.observe(b'\xef\xbb\xbf {"source":"native"}',s);self.assertEqual(r['mediaObservation'],'json-prefix')
 def test_no_partial_bom_acceptance(self):
  s=next(s for s in f.prepared_sources()if s['expectedResponse']['content-type']=='application/json')
  with self.assertRaises(RefreshError):self.observe(b'\xef{"a":1}',s)
 def test_rss_root_required(self):
  s=next(s for s in f.prepared_sources()if s['expectedResponse']['content-type']=='application/rss+xml')
  self.observe(b'<?xml version="1.0"?><rss version="2.0"></rss>',s)
  with self.assertRaises(RefreshError):self.observe(b'<?xml version="1.0"?><html/>',s)
 def test_body_growth_or_path_replacement_rejects(self):
  with tempfile.TemporaryDirectory()as d:
   p=Path(d)/'file';body=b'%PDF-1.7\n%%EOF';p.write_bytes(body);p.chmod(0o600);calls=[]
   def check(deadline):
    if not calls:p.write_bytes(body+b'growth');calls.append(1)
   with self.assertRaises(RefreshError):f.validate_original(SimpleNamespace(path=p,bytes=len(body),sha256=sha(body)),f.prepared_sources()[0],time.monotonic()+1,SimpleNamespace(deadline_check=check))

if __name__=='__main__':unittest.main()

class FreshGate(unittest.TestCase):
 def setUp(self):
  self.sources=f.prepared_sources()[:2]
  self.selection={'requiredMetadataTargetIds':{s['sourceKey']:['metadata-'+str(i)]for i,s in enumerate(self.sources)},'maximumRequests':2,'maximumBodyBytes':sum(s['hardTransferBytes']for s in self.sources)}
  self.authority=f.FetchAuthority(f._SEAL,self.sources,self.selection)
  self.report={'status':'metadata-proposals-only','outcomes':[{'targetId':'metadata-'+str(i),'code':'reconciled','excludedObjects':0}for i in range(2)],'rows':[]}
  self.base=SimpleNamespace(uid=1000,root=Path('/synthetic'),native=Path('/synthetic/native'),runner_work=Path('/synthetic/runner'),runner_cache=Path('/synthetic/cache'),provenance=lambda:{'handoffId':'002'},access_state=lambda p:'inaccessible')
  self.holds=lambda s:{'sourceContractSHA256':sha(canonical(s)),'read':True,'copy':True,'currentSourceHolds':[]}
 def runtime(self):
  with patch.object(f.os,'getuid',return_value=1000):return f.OwnerExtension(self.base,self.authority,metadata_report=self.report,metadata_validator=lambda r:None,current_holds=self.holds,adapter=SimpleNamespace(deadline_check=lambda d:None))
 def test_target_failure_only_blocks_dependent_source(self):
  self.report['outcomes'][0]['code']='missing';r=self.runtime()
  with self.assertRaises(RefreshError):r.metadata_gate(self.sources[0],0)
  r.metadata_gate(self.sources[1],0)
 def test_missing_dependency_never_empty_clearance(self):
  self.authority.requiredMetadataTargets[self.sources[0]['sourceKey']]=[]
  with self.assertRaises(RefreshError):self.runtime().metadata_gate(self.sources[0],0)
 def test_positive_url_match_stays_unresolved(self):
  self.report['rows']=[{'identifiers':{},'urls':{'sourceUrl':{'exactURLSHA256':sha(self.sources[0]['url'].encode())}}}]
  r=self.runtime()
  with self.assertRaises(RefreshError):r.metadata_gate(self.sources[0],0)
  r.metadata_gate(self.sources[1],0)
 def test_changed_current_holds_block(self):
  self.holds=lambda s:{'sourceContractSHA256':sha(canonical(s)),'read':True,'copy':True,'currentSourceHolds':['no-read']}
  with self.assertRaises(RefreshError):self.runtime().metadata_gate(self.sources[0],0)
 def test_metadata_success_does_not_bypass_unreadable_claim_root(self):
  r=self.runtime();r.metadata_gate(self.sources[0],0)
  with self.assertRaises(RefreshError):r.admit(Path('/synthetic/work'),self.sources[0],None,None,None,0)
 def test_changed_request_cannot_reuse_gate(self):
  s=deepcopy(self.sources[0]);s['url']+='?new=1'
  with self.assertRaises(RefreshError):self.runtime().metadata_gate(s,0)
 def test_old_handover_provenance_not_extended(self):
  r=self.runtime()
  with self.assertRaises(RefreshError):r.reuse_provenance(self.sources[0],{'ownerHandover':self.base.provenance()})
 def test_exact_new_provenance_survives_retry_without_rebinding(self):
  r=self.runtime();self.assertEqual(r.reuse_provenance(self.sources[0],{'ownerHandover':r.provenance()}),r.provenance())

class SaverIntegration(unittest.TestCase):
 def setUp(self):
  import test_known_asset_intake as previous
  self.previous=previous;self.fixture=previous.IntakeTests();self.fixture.setUp()
  self.sources=f.prepared_sources();self.fixture.sources=self.sources
  selection={'requiredMetadataTargetIds':{s['sourceKey']:['synthetic']for s in self.sources},'maximumRequests':26,'maximumBodyBytes':644874240}
  self.authority=f.FetchAuthority(f._SEAL,self.sources,selection)
  self.owner=SimpleNamespace(uid=os.getuid(),fetchAuthoritySHA256=self.authority.selectionSHA256,admit=lambda *a:{},provenance=lambda:{'fixture':'synthetic'},reuse_provenance=lambda s,i:{'fixture':'synthetic'})
  self.mode={'predecessors':[],'diagnosticReportPin':None,'freshSources':[s['sourceKey']for s in self.sources]}
 def tearDown(self):self.fixture.tearDown()
 def body(self,s):
  kind=s['mediaIntake']['integrity']['observation']
  return {'pdf-prefix-and-eof':b'%PDF-1.7\n%%EOF\n','json-prefix':b'{"native":"retained"}','ole-container-prefix':bytes.fromhex('d0cf11e0a1b11ae1')+b'fixture','zip-container-prefix':b'PK\x03\x04fixture','rss-root-prefix':b'<rss version="2.0"></rss>'}[kind]
 def run_source(self,s,transport=None,batch_meter=None):
  if transport is None:
   body=self.body(s);transport=lambda *a,**k:self.previous.Response(body,200,[('Content-Type',s['expectedResponse']['content-type']),('Content-Length',str(len(body)))])
  return f.run_selected(s,authority=self.authority,owner_runtime=self.owner,adapter=self.previous.a,mode=self.mode,transport=transport,batch_meter=batch_meter)
 def test_all26_save_then_zero_request_reuse(self):
  meter=self.previous.g.SharedBudget(26,644874240)
  for s in self.sources:
   first=self.run_source(s,batch_meter=meter.child(s['sourceKey'],s['hardTransferBytes'],1));self.assertEqual(first['status'],'verified-private-original',first)
   again=self.run_source(s,lambda *a,**k:(_ for _ in ()).throw(AssertionError('GET during reuse')))
   self.assertEqual(again['network']['requests'],0);self.assertEqual(again['originalDisposition'],'retained-original-no-network')
   self.assertFalse(again['validation']['fullStructuralValidation'])
  self.assertEqual(meter.snapshot()['requests'],26)
 def test_denial_remains_terminal_without_get_retry(self):
  s=self.sources[0];response=self.previous.Response(b'denial',403,[('Content-Type','text/html')])
  one=self.run_source(s,lambda *a,**k:response);self.assertEqual(one['network'],{'requests':1,'bodyBytesRead':0});self.assertEqual(response.reads,0)
  folder=self.fixture.work/'private-originals'/sha(canonical(s));old=(folder/'successor-intent.json').read_bytes()
  again=self.run_source(s,lambda *a,**k:(_ for _ in ()).throw(AssertionError('retry')))
  self.assertEqual(again['errorCode'],'private-save-intent-uncertain');self.assertEqual(again['network']['requests'],0);self.assertEqual((folder/'successor-intent.json').read_bytes(),old)
 def test_redirect_never_followed_or_body_read(self):
  response=self.previous.Response(b'redirect-secret',302,[('Location','https://unapproved.invalid/new?secret=x')]);r=self.run_source(self.sources[0],lambda *a,**k:response)
  self.assertEqual(r['network'],{'requests':1,'bodyBytesRead':0});self.assertEqual(response.reads,0)
 def test_conflicting_framing_rejected_before_body(self):
  s=self.sources[0];response=self.previous.Response(b'%PDF-1.7\n%%EOF',200,[('Content-Type','application/pdf'),('Content-Length','14'),('Transfer-Encoding','chunked')]);r=self.run_source(s,lambda *a,**k:response)
  self.assertEqual(r['errorCode'],'media-intake-framing-invalid');self.assertEqual(response.reads,0)
