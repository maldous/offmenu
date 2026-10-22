"""Synthetic Swiss original fixtures; never access a publisher or real original."""
from contextlib import ExitStack,redirect_stdout
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import tempfile
import time
import unittest
from unittest.mock import patch
import zipfile
ROOT=Path(__file__).resolve().parents[1]
def module(name,file):
 s=importlib.util.spec_from_file_location(name,ROOT/'scripts'/file);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
m=module('swiss_fixture','acquire-fixed-swiss.py');a=m.a
dispatch=module('swiss_dispatch','dispatch-foo-job.py')
class Response:
 def __init__(self,body,status=200,headers=None,fail_after=None):
  self.status=status;self.headers=headers or {};self.body=io.BytesIO(body);self.reads=0;self.fail_after=fail_after;self.closed=False
 def read(self,size):
  self.reads+=1
  if self.fail_after and self.reads>self.fail_after:raise TimeoutError()
  return self.body.read(min(size,10) if self.fail_after else size)
 def close(self):self.closed=True
class SwissTests(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name);self.stack=ExitStack()
  self.body=self.xlsx();self.selected=json.loads((ROOT/m.PIN[0]).read_text())
  self.selected.update(expectedBytes=len(self.body),hardTransferBytes=len(self.body))
  self.selected['expectedResponse']['content-length']=str(len(self.body))
  for key,value in [('OUTPUT',self.root),('LEGACY_CACHE',self.root/'legacy'),('GUARD',0)]:self.stack.enter_context(patch.object(a,key,value))
  self.stack.enter_context(patch.object(m,'EXPECTED_BYTES',len(self.body)))
  self.stack.enter_context(patch('socket.create_connection',side_effect=AssertionError('live network forbidden')))
  self.calls=[]
 def tearDown(self):self.stack.close();self.temp.cleanup()
 def xlsx(self,extra=None):
  b=io.BytesIO()
  with zipfile.ZipFile(b,'w',compression=zipfile.ZIP_STORED) as z:
   for name in ['[Content_Types].xml','_rels/.rels','xl/workbook.xml','xl/worksheets/sheet1.xml']:z.writestr(name,b'<synthetic/>')
   for name,body in (extra or {}).items():z.writestr(name,body)
  return b.getvalue()
 def run_source(self,response=None):
  response=response or Response(self.body,headers=list(self.selected['expectedResponse'].items()))
  def transport(spec,headers,*,deadline):
   self.calls.append((spec,headers,deadline));return response
  return a.run_selected(self.selected,transport=transport)
 def claim(self):return self.root/'collection/intents'/(a.sha(m.URL.encode())+'.json')
 def test_original_existing_engine_hash_and_container(self):
  r=self.run_source();self.assertEqual(r['status'],'verified-private-original',r)
  s=m.summary(r);self.assertEqual(s['verifiedBytes'],len(self.body));self.assertTrue(s['xlsxContainerAndCRCVerified'])
  self.assertFalse(s['publisherCryptographicChecksumAvailable']);self.assertEqual(s['originalSHA256'],hashlib.sha256(self.body).hexdigest())
  self.assertEqual(len(self.calls),1);self.assertEqual(self.calls[0][1],{'Accept-Encoding':'identity'})
 def test_reuse_zero_get_preserves_clock(self):
  first=self.run_source();self.calls=[];second=self.run_source()
  self.assertFalse(self.calls);self.assertEqual(first['validation']['originalAcquiredAt'],second['validation']['originalAcquiredAt'])
  self.assertEqual(second['cacheStatus'],'reused-fresh')
 def test_denial_preserves_metadata_and_sticky_claim(self):
  r=self.run_source(Response(b'',403,{'Content-Type':'text/html','Content-Length':'0'}));s=m.summary(r)
  self.assertEqual(s['responseMetadata']['httpStatus'],403);self.assertEqual(s['networkBytesRead'],0)
  self.assertEqual(json.loads(self.claim().read_text())['state'],'failed-no-retry');self.calls=[]
  r=self.run_source();self.assertEqual(r['errorCode'],'source-claim-uncertain');self.assertFalse(self.calls)
 def test_redirect_not_followed_and_location_sanitized(self):
  r=self.run_source(Response(b'',302,{'Location':'/login?token=secret'}));s=m.summary(r)
  self.assertEqual(s['responseMetadata']['location']['classification'],'same-host');self.assertNotIn('secret',json.dumps(s))
  self.assertEqual(len(self.calls),1);self.assertEqual(s['networkBytesRead'],0)
 def test_changed_validator_blocks_body(self):
  for key in self.selected['expectedResponse']:
   with self.subTest(key=key):
    root=self.root/key;root.mkdir()
    with patch.object(a,'OUTPUT',root):
     headers=dict(self.selected['expectedResponse']);headers[key]='changed'
     r=self.run_source(Response(self.body,headers=headers))
     self.assertEqual(r['errorCode'],'source-response-contract-changed');self.assertEqual(r['network']['bodyBytesRead'],0)
     self.assertEqual(m.summary(r)['responseMetadata']['httpStatus'],200)
 def test_bad_xlsx_not_verified_bytes_meter_retained(self):
  r=self.run_source(Response(b'x'*len(self.body),headers=self.selected['expectedResponse']))
  self.assertEqual(r['errorCode'],'source-xlsx-invalid');self.assertEqual(m.summary(r)['networkBytesRead'],len(self.body))
 def test_crc_corruption_rejected(self):
  corrupted=self.body.replace(b'<synthetic/>',b'<synthetix/>',1)
  r=self.run_source(Response(corrupted,headers=self.selected['expectedResponse']))
  self.assertEqual(r['errorCode'],'source-xlsx-invalid');self.assertEqual(m.summary(r)['networkBytesRead'],len(self.body))
 def test_partial_transfer_counts_consumed_bytes(self):
  r=self.run_source(Response(self.body,headers=self.selected['expectedResponse'],fail_after=1))
  self.assertEqual(m.summary(r)['networkBytesRead'],10);self.assertEqual(len(self.calls),1)
 def test_known_exact_alias_claim_key_blocks(self):
  legacy=self.root/'legacy';legacy.mkdir();p=legacy/'source-claims.json';p.write_text(json.dumps({'S062':{'owner':4,'state':'active'}}));raw=p.read_bytes()
  r=self.run_source();self.assertEqual(r['errorCode'],'known-exact-source-alternate-cache');self.assertFalse(self.calls);self.assertEqual(p.read_bytes(),raw)
 def test_known_native_exact_url_is_positive_but_citation_not_custody(self):
  self.assertTrue(m.exact_original_evidence({'sourceUrl':m.URL,'owner':4}))
  self.assertFalse(m.exact_original_evidence({'assetId':'citation:x','publisherCitation':{'url':'https://www.naehrwertdaten.ch/en/downloads/','sourceIds':['S062']},'holds':['discovery-only; acquisition not selected']}))
 def test_uncertain_existing_claim_unchanged(self):
  p=self.claim();p.parent.mkdir(parents=True);p.write_text('{"state":"acquiring","owner":4}');raw=p.read_bytes()
  r=self.run_source();self.assertEqual(r['errorCode'],'source-claim-uncertain');self.assertFalse(self.calls);self.assertEqual(p.read_bytes(),raw)
 def test_capacity_stop_before_get(self):
  with patch.object(a,'capacity',return_value=0):r=self.run_source()
  self.assertEqual(r['errorCode'],'capacity-planning-bound-not-protected');self.assertFalse(self.calls)
 def test_late_claim_failure_keeps_meter(self):
  with patch.object(a,'atomic_json',side_effect=OSError()):r=self.run_source()
  s=m.summary(r);self.assertEqual(s['errorCode'],'claim-state-write-failed');self.assertEqual(s['networkBytesRead'],len(self.body))
 def test_late_receipt_failure_keeps_meter(self):
  with patch.object(a,'write_immutable',side_effect=OSError()):r=self.run_source()
  s=m.summary(r);self.assertEqual(s['errorCode'],'result-write-failed');self.assertEqual(s['networkBytesRead'],len(self.body));self.assertFalse(s['detailPersisted'])
 def test_late_release_failure_keeps_meter(self):
  real=a.release_own_reservation
  def release(*args):real(*args);raise OSError()
  with patch.object(a,'release_own_reservation',side_effect=release):r=self.run_source()
  self.assertEqual(m.summary(r)['networkBytesRead'],len(self.body));self.assertEqual(r['errorCode'],'reservation-release-failed')
 def test_post_download_deadline_shared_with_xlsx_validation(self):
  with patch.object(a,'validate_xlsx',side_effect=a.RefreshError('operation-deadline-exceeded')):r=self.run_source()
  self.assertEqual(r['errorCode'],'operation-deadline-exceeded');self.assertEqual(m.summary(r)['networkBytesRead'],len(self.body))
 def test_archive_path_traversal_never_extracted(self):
  path=self.root/'bad.xlsx';path.write_bytes(self.xlsx({'../escape':b'x'}))
  with path.open('rb') as stream, self.assertRaisesRegex(a.RefreshError,'source-xlsx-invalid'):a.validate_xlsx(stream,time.monotonic()+10)
  self.assertFalse((self.root.parent/'escape').exists())
 def test_summary_closed_and_cannot_claim_publisher_hash(self):
  s=m.summary(self.run_source());s['publisherCryptographicChecksumAvailable']=True
  with self.assertRaises(ValueError):m.sanitize_report(s)
  s=m.summary(error='cache-missing');s['rawRows']=[]
  with self.assertRaises(ValueError):m.sanitize_report(s)
 def test_fixed_request_and_no_extra_parameters(self):
  request={'schemaVersion':1,'jobId':'swiss-original-fixture','profile':'swiss-private-original'}
  self.assertEqual(dispatch.parse_request(json.dumps(request).encode()),request)
  request['url']=m.URL
  with self.assertRaises(dispatch.JobError):dispatch.parse_request(json.dumps(request).encode())
  with redirect_stdout(io.StringIO()):self.assertEqual(m.main(['--url',m.URL]),2)
 def test_dispatch_projection_retains_failed_http_evidence(self):
  # Failure summary uses production byte bound, so independent module validates it.
  s=m.summary(self.run_source(Response(b'',403,{'Content-Type':'text/html'})))
  evidence=dispatch.safe_evidence(a.canonical(s))
  self.assertEqual(evidence['fixedSwissOriginal']['responseMetadata']['httpStatus'],403)
 def test_real_pins_and_bounded_native_evidence_load(self):
  with patch.object(a,'GUARD',88418025472),patch.object(m,'EXPECTED_BYTES',1014249):s=m.load_selection()
  self.assertEqual(s['sourceKey'],m.SOURCE_KEY);self.assertFalse(s['coordinatorSelection']['nativeCoverageExhaustive'])

 def test_exact_cap_list_headers_real_framing_and_main_success(self):
  # Exact production length, synthetic stored ZIP only; no original dataset rows.
  self.body=self.xlsx({'fixture.bin':b'0'*(1014249-len(self.xlsx({'fixture.bin':b''})))})
  self.selected.update(expectedBytes=1014249,hardTransferBytes=1014249)
  self.selected['expectedResponse']['content-length']='1014249'
  class FramedResponse(Response):
   def __init__(inner):
    super().__init__(self.body,headers=list(self.selected['expectedResponse'].items()))
    inner.response=type('HTTPFraming',(),{'length':len(self.body),'chunked':False})()
   def read(inner,size):
    block=super().read(size);inner.response.length-=len(block);return block
  response=FramedResponse();real=a.run_selected
  def run(selected,**kw):return real(selected,transport=lambda *args,**kw:response,**kw)
  output=io.StringIO()
  with patch.object(m,'EXPECTED_BYTES',1014249),patch.object(m,'load_selection',return_value=self.selected),patch.object(a,'run_selected',side_effect=run),redirect_stdout(output):code=m.main([])
  result=json.loads(output.getvalue());self.assertEqual(code,0,result)
  self.assertEqual(result['cacheStatus'],'downloaded-200');self.assertEqual(result['networkRequests'],1)
  self.assertEqual(result['networkBytesRead'],len(self.body));self.assertEqual(response.reads,1)
  evidence=dispatch.safe_evidence(a.canonical(result))
  self.assertEqual(evidence['fixedSwissOriginal']['status'],'verified-private-original')
 def test_duplicate_headers_rejected_before_body_with_metadata(self):
  response=Response(self.body,headers=list(self.selected['expectedResponse'].items())+[('Content-Length',str(len(self.body)))])
  r=self.run_source(response);self.assertNotEqual(r['status'],'verified-private-original');self.assertEqual(response.reads,0)
  self.assertEqual(m.summary(r)['responseMetadata']['duplicateMetadataHeaders'],True);self.assertTrue(response.closed)
 def test_content_length_and_transfer_encoding_conflict_stops(self):
  headers={**self.selected['expectedResponse'],'Transfer-Encoding':'chunked'}
  response=Response(self.body,headers=headers);r=self.run_source(response)
  self.assertEqual(r['errorCode'],'source-response-contract-changed');self.assertEqual(response.reads,0)
 def test_validation_uses_same_open_snapshot(self):
  real=a.validate_xlsx;seen=[]
  def validate(stream,deadline):
   seen.append(stream.fileno());real(stream,deadline)
  with patch.object(a,'validate_xlsx',side_effect=validate):r=self.run_source()
  self.assertEqual(r['status'],'verified-private-original',r);self.assertEqual(len(seen),1)

 def test_validation_detects_same_fd_metadata_change(self):
  import os
  real=a.validate_xlsx
  def validate(stream,deadline):
   real(stream,deadline);os.utime(stream.fileno(),ns=(1,1))
  with patch.object(a,'validate_xlsx',side_effect=validate):r=self.run_source()
  self.assertEqual(r['errorCode'],'source-changed-during-validation');self.assertEqual(m.summary(r)['networkBytesRead'],len(self.body))

 def test_unparseable_http_response_preserves_one_request_in_stdout(self):
  import http.client
  real=a.run_selected
  def malformed(*args,**kw):raise http.client.BadStatusLine('not retained')
  def run(selected,**kw):return real(selected,transport=malformed,**kw)
  output=io.StringIO()
  with patch.object(m,'load_selection',return_value=self.selected),patch.object(a,'run_selected',side_effect=run),redirect_stdout(output):code=m.main([])
  report=json.loads(output.getvalue());self.assertEqual(code,2);self.assertEqual(report['networkRequests'],1)
  self.assertEqual(report['networkBytesRead'],0);self.assertIsNone(report['responseMetadata']);self.assertNotIn('not retained',output.getvalue())
