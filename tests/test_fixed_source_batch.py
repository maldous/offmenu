"""Offline bounded batch fixtures; all PDF bodies are synthetic and network forbidden."""
from contextlib import ExitStack,redirect_stdout
from copy import deepcopy
import hashlib,http.client,importlib.util,io,json,os
from pathlib import Path
import tempfile,time,unittest
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
def module(name,file):
 spec=importlib.util.spec_from_file_location(name,ROOT/'scripts'/file);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
m=module('batch_fixture','acquire-fixed-batch.py');a=m.a
dispatch=module('batch_dispatch','dispatch-foo-job.py')
BODY=b'%PDF-1.7\n1 0 obj\n<< /Type /Catalog >>\nendobj\n%%EOF\n'
class Response:
 def __init__(self,body=BODY,status=200,headers=None,partial=False):
  self.status=status;self.headers=headers or {};self.body=io.BytesIO(body);self.partial=partial;self.reads=0;self.closed=False
 def read(self,size):
  self.reads+=1
  if self.partial and self.reads>1:raise TimeoutError()
  return self.body.read(min(size,7) if self.partial else size)
 def close(self):self.closed=True
class BatchTests(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name);self.stack=ExitStack()
  self.selected=deepcopy(m.selection_config());self.selected['planningGuardBytes']=0
  for s in self.selected['sources']:
   s['hardTransferBytes']=len(BODY)+16
   if s['expectedBytes'] is not None:s['expectedBytes']=len(BODY);s['expectedResponse']['content-length']=str(len(BODY))
  self.selected['maximumTransferBytes']=sum(s['hardTransferBytes'] for s in self.selected['sources'])
  for k,v in [('OUTPUT',self.root),('LEGACY_CACHE',self.root/'legacy'),('GUARD',0)]:self.stack.enter_context(patch.object(a,k,v))
  self.stack.enter_context(patch('socket.create_connection',side_effect=AssertionError('no live network')))
  self.calls=[]
 def tearDown(self):self.stack.close();self.temp.cleanup()
 def transport(self,spec,headers,*,deadline):
  self.calls.append((spec,headers,deadline));source=next(s for s in self.selected['sources'] if s['sourceKey']==spec.source_key)
  h=list(source['expectedResponse'].items())
  if source['expectedBytes'] is None:h.append(('Transfer-Encoding','chunked'))
  return Response(headers=h)
 def run_batch(self,transport=None,**kwargs):return m.run_batch(self.selected,transport=transport or self.transport,**kwargs)
 def clean(self,r):
  with patch.object(m,'selection_config',return_value=self.selected):return m.sanitize_report(r)
 def test_seven_independent_successes_exact_counters_pdf_integrity(self):
  r=self.clean(self.run_batch());self.assertEqual(r['status'],'complete',r);self.assertEqual(r['networkRequests'],7)
  self.assertEqual(r['networkBytesRead'],len(BODY)*7);self.assertEqual(len(self.calls),7)
  for item in r['items']:
   self.assertEqual(item['originalSHA256'],hashlib.sha256(BODY).hexdigest());self.assertTrue(item['detailPersisted'])
  self.assertTrue(all(c[1]=={'Accept-Encoding':'identity'} for c in self.calls))
 def test_reuse_zero_requests_preserves_original_clock(self):
  first=self.run_batch();self.calls=[];second=self.clean(self.run_batch())
  self.assertEqual(second['networkRequests'],0);self.assertFalse(self.calls)
  self.assertEqual([i['originalAcquiredAt'] for i in first['items']],[i['originalAcquiredAt'] for i in second['items']])
 def test_denial_and_redirect_do_not_stop_independent_items(self):
  def transport(spec,headers,**kw):
   if spec.source_key==self.selected['sources'][0]['sourceKey']:return Response(b'',403,{'Content-Type':'text/html'})
   if spec.source_key==self.selected['sources'][1]['sourceKey']:return Response(b'',302,{'Location':'https://elsewhere.example/path?secret=x'})
   return self.transport(spec,headers,**kw)
  r=self.clean(self.run_batch(transport));self.assertEqual(r['networkRequests'],7)
  self.assertEqual([i['status'] for i in r['items']],['failed','failed']+['verified-private-original']*5)
  self.assertEqual(r['networkBytesRead'],len(BODY)*5);self.assertNotIn('secret',json.dumps(r))
 def test_partial_and_malformed_http_continue_with_meter(self):
  def transport(spec,headers,**kw):
   if spec.source_key==self.selected['sources'][0]['sourceKey']:return Response(headers=self.selected['sources'][0]['expectedResponse'],partial=True)
   if spec.source_key==self.selected['sources'][1]['sourceKey']:raise http.client.BadStatusLine('private raw text')
   return self.transport(spec,headers,**kw)
  r=self.clean(self.run_batch(transport));self.assertEqual(r['networkRequests'],7);self.assertEqual(r['networkBytesRead'],7+len(BODY)*5)
  self.assertEqual(r['items'][0]['networkBytesRead'],7);self.assertNotIn('private raw text',json.dumps(r))
 def test_bad_pdf_header_or_eof_preserves_all_transfer_bytes(self):
  count=0
  def transport(spec,headers,**kw):
   nonlocal count
   count+=1;response=self.transport(spec,headers,**kw)
   if count==1:response.body=io.BytesIO(b'x'+BODY[1:])
   if count==2:response.body=io.BytesIO(BODY[:-3]+b'xxx')
   return response
  r=self.clean(self.run_batch(transport));self.assertEqual(r['networkBytesRead'],len(BODY)*7)
  self.assertEqual([i['errorCode'] for i in r['items'][:2]],['source-header-mismatch']*2)
 def test_fresh_local_exact_claim_blocks_only_its_source(self):
  p=self.root/'legacy/source-claims.json';p.parent.mkdir();p.write_text(json.dumps({self.selected['sources'][0]['url']:{'owner':12,'state':'active'}}));raw=p.read_bytes()
  r=self.clean(self.run_batch());self.assertEqual(r['networkRequests'],6);self.assertEqual(r['items'][0]['errorCode'],'known-exact-source-alternate-cache');self.assertEqual(p.read_bytes(),raw)
 def test_shared_request_budget_stops_new_get_but_records_all_items(self):
  self.selected['maximumRequests']=2;r=self.clean(self.run_batch());self.assertEqual(r['networkRequests'],2);self.assertEqual(len(r['items']),7)
  self.assertEqual([i['errorCode'] for i in r['items'][2:]],['network-request-limit']*5)
 def test_shared_byte_meter_never_reads_beyond_remaining(self):
  source=self.selected['sources'][0];meter={'requests':0,'bodyBytesRead':0,'maximumRequests':1,'maximumBytes':len(BODY)-1}
  r=a.run_selected(source,transport=self.transport,batch_meter=meter)
  self.assertEqual(meter['bodyBytesRead'],len(BODY)-1);self.assertEqual(r['errorCode'],'network-byte-limit')
 def test_raised_after_meter_keeps_previous_and_partial_counts(self):
  real=a.run_selected;count=0
  def run(source,**kw):
   nonlocal count
   count+=1
   if count==2:
    kw['batch_meter']['requests']+=1;kw['batch_meter']['bodyBytesRead']+=5
    raise OSError('not retained')
   return real(source,**kw)
  with patch.object(a,'run_selected',side_effect=run):r=self.clean(self.run_batch())
  self.assertEqual(r['networkRequests'],7);self.assertEqual(r['networkBytesRead'],len(BODY)*6+5)
  self.assertEqual(r['items'][0]['status'],'verified-private-original');self.assertEqual(r['items'][1]['networkBytesRead'],5)
 def test_expired_batch_still_reports_every_source(self):
  with patch.object(m.time,'monotonic',side_effect=[0]+[1300]*7):r=self.run_batch()
  self.assertEqual(r['networkRequests'],0);self.assertEqual(len(r['items']),7)
  self.assertTrue(all(i['errorCode']=='batch-deadline-exhausted' for i in r['items']))
 def test_capacity_failure_stops_get_and_other_items_continue(self):
  real=a.capacity;calls=0
  def capacity(path):
   nonlocal calls
   calls+=1
   if calls<=2:return 0
   return real(path)
  with patch.object(a,'capacity',side_effect=capacity):r=self.clean(self.run_batch())
  self.assertEqual(r['networkRequests'],6);self.assertEqual(r['items'][0]['errorCode'],'capacity-planning-bound-not-protected')
 def test_late_receipt_failure_preserves_every_meter(self):
  with patch.object(a,'write_immutable',side_effect=OSError()):r=self.clean(self.run_batch())
  self.assertEqual(r['networkRequests'],7);self.assertEqual(r['networkBytesRead'],len(BODY)*7)
  self.assertTrue(all(i['errorCode']=='result-write-failed' for i in r['items']))
 def test_unknown_length_chunked_body_success_and_no_invented_size(self):
  r=self.clean(self.run_batch())
  for index in (2,3,4):
   self.assertIsNone(self.selected['sources'][index]['expectedBytes']);self.assertIsNone(r['items'][index]['responseMetadata']['contentLength'])
   self.assertEqual(r['items'][index]['verifiedBytes'],len(BODY))
 def test_unknown_length_conflicting_framing_blocked_before_body(self):
  def transport(spec,headers,**kw):
   response=self.transport(spec,headers,**kw)
   if spec.source_key==self.selected['sources'][2]['sourceKey']:response.headers.append(('Content-Length',str(len(BODY))))
   return response
  r=self.clean(self.run_batch(transport));self.assertEqual(r['items'][2]['errorCode'],'source-response-contract-changed');self.assertEqual(r['items'][2]['networkBytesRead'],0)
 def test_unknown_length_allocation_uses_full_cap(self):
  real=a.reserve;seen=[]
  def reserve(*args,**kw):seen.append(kw['expected_bytes']);return real(*args,**kw)
  with patch.object(a,'reserve',side_effect=reserve):self.run_batch()
  self.assertEqual(seen[2:5],[len(BODY)+16]*3)
 def test_shared_asset_alias_duplicate_rejected(self):
  self.selected['sources'][1]['aliases'].append(self.selected['sources'][0]['url'])
  with self.assertRaises(a.RefreshError):m.validate_selection(self.selected)
 def test_empty_or_extra_parameter_selection_rejected(self):
  bad=deepcopy(self.selected);bad['sources']=[]
  with self.assertRaises(a.RefreshError):m.validate_selection(bad)
  bad=deepcopy(self.selected);bad['command']='anything'
  with self.assertRaises(a.RefreshError):m.validate_selection(bad)
 def test_queries_fixed_public_only_no_credentials(self):
  for source in self.selected['sources']:a.source_spec(source).validate()
  self.selected['sources'][2]['url']+='&token=secret';self.selected['sources'][2]['queryKeys'].append('token')
  with self.assertRaises(a.RefreshError):m.validate_selection(self.selected)
 def test_pinned_bare_ba_preparation_exception_only(self):
  source=self.selected['sources'][1];e=source['historicalPreparationExceptions'][0]
  obs={'path':e['metadataPath'],'metadataSHA256':e['metadataSHA256'],'pinStatus':'match','reconciliation':{'records':[{'sourceUrl':e['sourceUrl']}]}}
  self.assertEqual(m.source_conflicts(self.selected,{'metadata':[obs]},{}),[])
  later=deepcopy(obs);later['reconciliation']['records'][0]['owner']=8
  self.assertTrue(m.source_conflicts(self.selected,{'metadata':[later]},{}))
  self.assertTrue(m.source_conflicts(self.selected,{'discoveredMetadata':[obs]},{}))
  obs['metadataSHA256']='0'*64;self.assertTrue(m.source_conflicts(self.selected,{'metadata':[obs]},{}))
 def test_discovered_claim_records_always_participate(self):
  record={'sourceUrl':self.selected['sources'][0]['url'],'owner':4,'status':'active'}
  self.assertTrue(m.source_conflicts(self.selected,{'discoveredMetadata':[{'reconciliation':{'records':[record]}}]},{}))
 def test_exact_url_hash_claim_path_without_exported_query_blocks(self):
  source=self.selected['sources'][2];name=a.sha(source['url'].encode())+'.json'
  obs={'category':'claims','path':'/home/user/src/offmenu-data/originals/country-followthrough-20261015/claims/'+name,'reconciliation':None}
  self.assertEqual(m.source_conflicts(self.selected,{'discoveredMetadata':[obs]},{}),[{'sourceKey':source['sourceKey']}])
  obs['path']='/unrelated/'+name;self.assertEqual(m.source_conflicts(self.selected,{'discoveredMetadata':[obs]},{}),[])
 def test_closed_summary_rejects_raw_rows_or_invented_counts(self):
  r=self.run_batch();r['rawRows']=[]
  with self.assertRaises(ValueError):self.clean(r)
  del r['rawRows'];r['networkRequests']=0
  with self.assertRaises(ValueError):self.clean(r)
 def test_profile_request_stays_three_fields(self):
  request={'schemaVersion':1,'jobId':'recipe-batch-fixture','profile':'selected-original-batch'}
  self.assertEqual(dispatch.parse_request(json.dumps(request).encode()),request)
  request['sources']=[]
  with self.assertRaises(dispatch.JobError):dispatch.parse_request(json.dumps(request).encode())
  self.assertEqual([s[0] for s in dispatch.profile_steps('selected-original-batch',ROOT)],['readiness','fixed-source-batch-tests','selected-original-batch'])
 def test_actual_pins_and_bounded_snapshot_conflicts(self):
  with patch.object(a,'GUARD',88418025472):selected=m.selection_config()
  self.assertEqual(len(selected['sources']),7);self.assertEqual(selected['maximumTransferBytes'],99287040)
  prep=a.preparation_module()
  for p in selected['evidence']:prep.pinned_bytes(ROOT,(p['path'],p['sha256']))
  snapshot=prep.imported_snapshot(ROOT);adopted=a.strict_json(prep.pinned_bytes(ROOT,prep.SUMMARY_PIN))
  self.assertEqual(m.source_conflicts(selected,snapshot,adopted),[])
 def test_dispatch_retains_full_actual_contract_blocked_items(self):
  with patch.object(a,'GUARD',88418025472):selected=m.selection_config()
  # Exact production selection, pretransport synthetic adverse observations.
  with patch.object(a,'GUARD',88418025472):r=m.run_batch(selected,adverse_evidence=[{'sourceKey':s['sourceKey']} for s in selected['sources']])
  evidence=dispatch.safe_evidence(a.canonical(r));self.assertEqual(len(evidence['fixedSourceBatch']['items']),7)
  self.assertEqual(evidence['fixedSourceBatch']['networkRequests'],0)

 def test_stdlib_chunked_response_reaches_eof_without_excess(self):
  import threading
  from offmenu.refresh.acquisition import _Response
  source=self.selected['sources'][2]
  headers={**source['expectedResponse'],'Transfer-Encoding':'chunked'}
  wire=b'HTTP/1.1 200 OK\r\n'+b''.join(k.encode()+b': '+v.encode()+b'\r\n' for k,v in headers.items())+b'\r\n'+hex(len(BODY))[2:].encode()+b'\r\n'+BODY+b'\r\n0\r\n\r\n'
  class Sock:
   def makefile(self,*args):return io.BytesIO(wire)
  class Closed:
   def close(self):pass
   def cancel(self):pass
  response=http.client.HTTPResponse(Sock());response.begin()
  wrapped=_Response(Closed(),response,Closed(),threading.Event())
  detail=a.run_selected(source,transport=lambda *args,**kw:wrapped)
  self.assertEqual(detail['status'],'verified-private-original',detail);self.assertEqual(detail['network']['bodyBytesRead'],len(BODY))
 def test_maximal_actual_success_summary_survives_dispatcher_limit(self):
  with patch.object(a,'GUARD',88418025472):selected=m.selection_config()
  items=[]
  for source in selected['sources']:
   count=source['expectedBytes'] or source['hardTransferBytes']-1
   detail={'status':'verified-private-original','errorCode':None,'network':{'requests':1,'bodyBytesRead':count},
    'responseMetadata':a.response_metadata(200,source['expectedResponse'],request_url=source['url']),
    'cacheStatus':'downloaded-200','validation':{'bytes':count,'sha256':'a'*64,'originalAcquiredAt':'2026-10-18T20:00:00.123456+00:00'},'receiptPersistence':'written'}
   items.append(m.item_report(source,detail))
  report={'schemaVersion':m.SCHEMA,'batchId':selected['batchId'],'selectionSHA256':a.sha(a.canonical(selected)),
   'status':'complete','errorCode':None,'networkRequests':7,'networkBytesRead':sum(i['networkBytesRead'] for i in items),'items':items,**a.SAFETY}
  evidence=dispatch.safe_evidence(a.canonical(report));self.assertEqual(evidence['fixedSourceBatch']['status'],'complete')
  self.assertLess(len(a.canonical(report)),dispatch.MAX_DIAGNOSTIC_EVIDENCE)
 def test_main_keeps_completed_and_raised_after_meter_results(self):
  real=a.run_selected;count=0
  def run(source,**kw):
   nonlocal count
   count+=1
   if count==2:
    kw['batch_meter']['requests']+=1;kw['batch_meter']['bodyBytesRead']+=5
    raise OSError('private exception')
   return real(source,**kw)
  output=io.StringIO()
  with patch.object(m,'selection_config',return_value=self.selected),patch.object(a,'run_selected',side_effect=run),patch.object(a,'HTTPSFileTransport',return_value=self.transport),redirect_stdout(output):code=m.main([])
  report=json.loads(output.getvalue());self.assertEqual(code,2);self.assertEqual(report['networkRequests'],7)
  self.assertEqual(report['networkBytesRead'],len(BODY)*6+5);self.assertEqual(report['items'][0]['status'],'verified-private-original')

 def test_verified_py_uc_alias_claims_block_without_touching_them(self):
  aliases=[next(v for v in source['aliases'] if 'drive.usercontent.google.com/uc?' in v) for source in self.selected['sources'][5:]]
  p=self.root/'legacy/source-claims.json';p.parent.mkdir();p.write_text(json.dumps({u:{'owner':5,'state':'active'} for u in aliases}));raw=p.read_bytes()
  r=self.clean(self.run_batch());self.assertEqual(r['networkRequests'],5);self.assertEqual(p.read_bytes(),raw)
  self.assertTrue(all(i['errorCode']=='known-exact-source-alternate-cache' for i in r['items'][5:]))
  observations=[{'category':'claims','path':'/home/user/src/offmenu-data/originals/country-followthrough-20261015/claims/'+a.sha(u.encode())+'.json','reconciliation':None} for u in aliases]
  self.assertEqual(len(m.source_conflicts(self.selected,{'discoveredMetadata':observations},{})),2)
