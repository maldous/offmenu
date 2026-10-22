"""Offline five-source failure diagnostics; no source bodies or live sockets."""
from contextlib import ExitStack,redirect_stdout
from copy import deepcopy
import http.client,importlib.util,io,json,tempfile,time,unittest
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
def module(name,file):
 spec=importlib.util.spec_from_file_location(name,ROOT/'scripts'/file);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
m=module('recovery_diagnostic','diagnose-fixed-batch.py');a=m.a
d=module('recovery_dispatch','dispatch-foo-job.py')
class Response:
 def __init__(self,status=200,headers=()):self.status=status;self.headers=list(headers);self.closed=False
 def getheaders(self):return self.headers
 def read(self,*args):raise AssertionError('HEAD must never read body')
 def close(self):self.closed=True
class DiagnosticTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name);self.stack=ExitStack()
  self.config,self.entries=deepcopy(m.load_selection());self.calls=[];self.responses=[]
  self.work=self.root/'collection';(self.work/'intents').mkdir(parents=True)
  self.stack.enter_context(patch.object(a,'OUTPUT',self.root))
  self.stack.enter_context(patch('socket.create_connection',side_effect=AssertionError('live network forbidden')))
  for e in self.entries:
   s=e['source'];p=e['prior'];key=a.sha(a.canonical(a.source_spec(s).identity()))
   detail={'sourceKey':s['sourceKey'],'selectionSHA256':p['sourceContractSHA256'],'status':'failed','errorCode':'collector-rejected','network':{'requests':1,'bodyBytesRead':0},'responseMetadata':{'httpStatus':200}}
   raw=a.canonical(detail);p['detailSHA256']=a.sha(raw);(self.work/('fixed-source-result-'+p['detailSHA256']+'.json')).write_bytes(raw)
   claim={'schemaVersion':'offmenu-fixed-source-intent/1','sourceKey':s['sourceKey'],'url':s['url'],'owner':0,'selectionSHA256':p['sourceContractSHA256'],'requestIdentitySHA256':key,'state':'failed-no-retry','errorCode':'collector-rejected','network':{'requests':1,'bodyBytesRead':0}}
   (self.work/'intents'/(a.sha(s['url'].encode())+'.json')).write_bytes(a.canonical(claim))
  self.initial_claims={p.name:p.read_bytes() for p in (self.work/'intents').iterdir()}
 def tearDown(self):self.stack.close();self.tmp.cleanup()
 def folder(self,index=0):
  s=self.entries[index]['source'];return self.work/'source-cache/requests'/a.sha(a.canonical(a.source_spec(s).identity()))
 def factory(self,host,port,**kwargs):
  parent=self
  class Connection:
   sock=None
   def request(self,method,path,headers):parent.calls.append((host,port,method,path,headers))
   def getresponse(self):
    source=next(e['source'] for e in parent.entries if e['source']['url'].split('/')[2]==host and e['source']['url'].split(host,1)[1]==parent.calls[-1][3])
    response=Response(headers=list(source['expectedResponse'].items())+[('Set-Cookie','private-cookie-one'),('Set-Cookie','private-cookie-two')]);parent.responses.append(response);return response
   def close(self):pass
  return Connection()
 def run_diag(self,factory=None):return m.run_diagnostics(self.config,self.entries,connection_factory=factory or self.factory)
 def clean(self,report):
  with patch.object(m,'load_selection',return_value=(self.config,self.entries)):return m.sanitize_report(report)
 def test_actual_selection_raw_and_canonical_pins_bind_five_only(self):
  config,entries=m.load_selection();self.assertEqual(len(entries),5);self.assertEqual(config['maximumHEADs'],5)
  self.assertEqual(config['priorCanonicalSelectionSHA256'],'5ae20ed24432b06aa596a717a620c09390472ff138bdda58f428cd789663d8a1')
  self.assertTrue(all(e['source']['sourceKey'].startswith(('tw41','py-drive-health')) for e in entries))
 def test_five_heads_zero_bodies_claims_unchanged(self):
  report=self.clean(self.run_diag());self.assertEqual(report['status'],'complete',report);self.assertEqual(report['networkRequests'],5)
  self.assertTrue(all(c[2]=='HEAD' and c[4]=={'Accept-Encoding':'identity'} for c in self.calls));self.assertTrue(all(r.closed for r in self.responses))
  self.assertEqual({p.name:p.read_bytes() for p in (self.work/'intents').iterdir()},self.initial_claims)
  self.assertEqual(report['networkBodyBytesRead'],0);self.assertFalse(report['priorGETCauseEstablished']);self.assertFalse(report['acquisitionEnabledByDiagnostic'])
  self.assertLess(len(a.canonical(report)),12288);self.assertNotIn('private-cookie',json.dumps(report))
 def test_duplicate_ancillary_headers_reproduces_core_candidate_only(self):
  facts=m.header_facts([('Set-Cookie','a=secret'),('Set-Cookie','b=secret')],self.entries[0]['source'])
  self.assertEqual(facts['coreHeaderValidation'],'invalid-response-headers');self.assertEqual(facts['recognizedNameCounts'],{'set-cookie':2})
  self.assertEqual(facts['retentionCheckOnUniqueRelevantHeaders'],'accepted');self.assertNotIn('secret',json.dumps(facts))
 def test_unknown_header_names_and_values_never_published(self):
  facts=m.header_facts([('X-Private-Account','secret'),('X-Private-Account','secret')],self.entries[0]['source'])
  self.assertEqual(facts['unrecognizedHeaderCount'],2);self.assertTrue(facts['duplicateUnrecognizedName']);self.assertNotIn('Private',json.dumps(facts));self.assertNotIn('secret',json.dumps(facts))
 def test_critical_duplicate_framing_classifications(self):
  for headers,framing in [([('Content-Length','3'),('Content-Length','4')],'invalid'),([('Content-Length','3'),('Transfer-Encoding','chunked')],'conflicting'),([('Transfer-Encoding','chunked')],'chunked'),([], 'unspecified')]:
   self.assertEqual(m.header_facts(headers,self.entries[0]['source'])['framing'],framing)
 def test_retention_restrictions_are_not_cleared(self):
  for key,value,result in [('Cache-Control','private, max-age=0','response-retention-not-approved'),('Vary','Cookie','unsupported-response-vary'),('Content-Encoding','gzip','unsupported-response-encoding')]:
   self.assertEqual(m.header_facts([(key,value)],self.entries[0]['source'])['retentionCheckOnUniqueRelevantHeaders'],result)
 def test_duplicate_retention_header_is_unknown_not_clear(self):
  f=m.header_facts([('Cache-Control','private'),('Cache-Control','public')],self.entries[0]['source']);self.assertEqual(f['retentionCheckOnUniqueRelevantHeaders'],'unavailable')
 def test_repeat_marker_blocks_every_head(self):
  self.run_diag();self.calls=[];r=self.clean(self.run_diag());self.assertEqual(r['networkRequests'],0);self.assertFalse(self.calls);self.assertTrue(all(i['errorCode']=='diagnostic-already-attempted' for i in r['items']))
 def test_partial_stat_only_preserved_and_other_sources_continue(self):
  folder=self.folder();folder.mkdir(parents=True);partial=folder/'body.partial';partial.write_bytes(b'body-must-not-read')
  original=a.read_metadata
  def read(path,**kw):
   self.assertNotEqual(Path(path),partial);return original(path,**kw)
  with patch.object(a,'read_metadata',side_effect=read):r=self.clean(self.run_diag())
  self.assertEqual(r['networkRequests'],4);self.assertEqual(r['items'][0]['localState']['partialBody'],{'state':'regular','bytes':18});self.assertEqual(partial.stat().st_size,18)
 def test_recovery_metadata_blocks_without_reading_contents(self):
  folder=self.folder();folder.mkdir(parents=True);(folder/'recovery.json').write_bytes(b'not-json-preserve')
  r=self.clean(self.run_diag());self.assertEqual(r['networkRequests'],4);self.assertEqual(r['items'][0]['errorCode'],'existing-source-custody-or-partial')
 def test_reservation_stat_blocks_without_modification(self):
  s=self.entries[0]['source'];p=self.work/('reservation-'+a.sha(s['url'].encode())+'.bin');p.write_bytes(b'123')
  r=self.clean(self.run_diag());self.assertEqual(r['networkRequests'],4);self.assertEqual(r['items'][0]['localState']['sourceReservation'],{'state':'regular','bytes':3})
 def test_current_pointer_stats_object_without_reading_body(self):
  folder=self.folder();folder.mkdir(parents=True);checksum='f'*64;(folder/'current.json').write_bytes(a.canonical({'sha256':checksum}))
  objects=self.work/'source-cache/objects';objects.mkdir();(objects/checksum).write_bytes(b'private')
  r=self.clean(self.run_diag());self.assertEqual(r['networkRequests'],4);self.assertEqual(r['items'][0]['localState']['acceptedObject'],{'state':'regular','bytes':7})
 def test_detail_hash_mismatch_blocks_before_head(self):
  p=self.entries[0]['prior'];(self.work/('fixed-source-result-'+p['detailSHA256']+'.json')).write_bytes(b'{}')
  r=self.clean(self.run_diag());self.assertEqual(r['networkRequests'],4);self.assertIsNone(r['items'][0]['localState'])
 def test_changed_intent_blocks_without_overwrite(self):
  p=next((self.work/'intents').iterdir());claim=json.loads(p.read_text());claim['state']='acquiring';p.write_bytes(a.canonical(claim));before=p.read_bytes()
  r=self.clean(self.run_diag());self.assertEqual(r['networkRequests'],4);self.assertEqual(p.read_bytes(),before)
 def test_head_denial_or_redirect_recorded_without_following(self):
  count=0
  def factory(*args,**kwargs):
   nonlocal count
   c=self.factory(*args,**kwargs);count+=1;status=403 if count==1 else 302;c.getresponse=lambda:Response(status,[('Content-Type','text/html'),('Location','https://elsewhere.example/path?secret=x')]);return c
  r=self.clean(self.run_diag(factory));self.assertEqual(r['networkRequests'],5);self.assertEqual(r['items'][0]['responseMetadata']['httpStatus'],403);self.assertEqual(len(self.calls),5);self.assertNotIn('secret',json.dumps(r))
 def test_late_oserror_preserves_all_counts_and_http(self):
  with patch.object(a,'write_immutable',side_effect=OSError('private')):r=self.clean(self.run_diag())
  self.assertEqual(r['networkRequests'],5);self.assertEqual(r['errorCode'],'diagnostic-result-write-failed');self.assertTrue(all(i['responseMetadata']['httpStatus']==200 for i in r['items']))
 def test_late_refresherror_preserves_all_counts_and_http(self):
  with patch.object(a,'write_immutable',side_effect=a.RefreshError('private')):r=self.clean(self.run_diag())
  self.assertEqual(r['networkRequests'],5);self.assertEqual(r['errorCode'],'diagnostic-result-write-failed');self.assertFalse(r['detailPersisted'])
 def test_malformed_http_preserves_attempt_and_continues(self):
  count=0
  def factory(*args,**kwargs):
   nonlocal count
   c=self.factory(*args,**kwargs);count+=1
   if count==1:c.getresponse=lambda:(_ for _ in ()).throw(http.client.BadStatusLine('private-server-data'))
   return c
  r=self.clean(self.run_diag(factory));self.assertEqual(r['networkRequests'],5);self.assertEqual(r['items'][0]['errorCode'],'diagnostic-request-failed');self.assertNotIn('private-server',json.dumps(r))
 def test_expired_deadline_zero_head(self):
  r=m.run_one(self.entries[0],time.monotonic()-1,connection_factory=self.factory);self.assertEqual(r['networkRequests'],0);self.assertEqual(r['errorCode'],'diagnostic-deadline-exceeded')
 def test_symlink_partial_not_followed(self):
  f=self.folder();f.mkdir(parents=True);(f/'body.partial').symlink_to('/does-not-exist')
  r=self.clean(self.run_diag());self.assertEqual(r['networkRequests'],4);self.assertEqual(r['items'][0]['localState']['partialBody']['state'],'inaccessible')
 def test_closed_sanitizer_rejects_raw_header_extra_field(self):
  r=self.run_diag();r['items'][0]['headerFacts']['cookie']='secret'
  with self.assertRaises(ValueError):self.clean(r)
 def test_safe_evidence_retains_fixed_summary(self):
  # Use actual pins with a closed blocked report; full synthetic report rebound separately.
  r=m.report_template();e=d.safe_evidence(a.canonical(r));self.assertEqual(e['batchRecoveryDiagnostic'],r)
 def test_full_maximum_name_projection_survives_dispatcher_bound(self):
  r=self.run_diag();actual=m.load_selection()[1]
  for item,entry in zip(r['items'],actual):
   item['priorDetailSHA256']=entry['prior']['detailSHA256']
   item['headerFacts']['recognizedNameCounts']={key:2 for key in m.KNOWN_HEADERS}
   item['headerFacts']['oversizedOrInvalidKnownValues']=sorted(m.KNOWN_HEADERS)
  e=d.safe_evidence(a.canonical(r));self.assertEqual(e['batchRecoveryDiagnostic'],r)
  self.assertLess(len(a.canonical(r)),12288)
 def test_main_late_write_failure_has_truthful_stdout(self):
  output=io.StringIO()
  with patch.object(m,'load_selection',return_value=(self.config,self.entries)),patch.object(m.http.client,'HTTPSConnection',self.factory),patch.object(a,'write_immutable',side_effect=a.RefreshError('private')),redirect_stdout(output):code=m.main([])
  r=json.loads(output.getvalue());self.assertEqual(code,2);self.assertEqual(r['networkRequests'],5);self.assertEqual(r['errorCode'],'diagnostic-result-write-failed')
 def test_main_rejects_arbitrary_arguments(self):
  output=io.StringIO()
  with redirect_stdout(output):code=m.main(['https://unselected.example'])
  self.assertEqual(code,2);self.assertEqual(json.loads(output.getvalue())['networkRequests'],0)
if __name__=='__main__':unittest.main()
