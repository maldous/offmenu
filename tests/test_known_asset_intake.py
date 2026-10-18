"""Synthetic offline tests. Any live socket is an assertion failure."""
from contextlib import ExitStack
from copy import deepcopy
from datetime import datetime, timezone, timedelta
import hashlib, importlib.util, io, json, os, tempfile, time, unittest, zipfile
from pathlib import Path
from types import SimpleNamespace
from urllib.parse import urlencode
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
def module(name,path):
 spec=importlib.util.spec_from_file_location(name,ROOT/path);value=importlib.util.module_from_spec(spec);spec.loader.exec_module(value);return value
g=module('known_global_fixture','scripts/collect-fixed-global.py');a=g.a;k=g.intake;m=g.media_save

class Response:
 def __init__(self,body=b'',status=200,headers=()):self.status=status;self.headers=list(headers);self.body=io.BytesIO(body);self.reads=0;self.closed=False
 def read(self,size):self.reads+=1;return self.body.read(size)
 def close(self):self.closed=True

def docx(extra=None):
 out=io.BytesIO()
 with zipfile.ZipFile(out,'w',zipfile.ZIP_DEFLATED) as archive:
  archive.writestr(zipfile.ZipInfo('[Content_Types].xml',date_time=(2020,1,1,0,0,0)),'<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/></Types>')
  archive.writestr(zipfile.ZipInfo('word/document.xml',date_time=(2020,1,1,0,0,0)),'<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:body><w:p><w:r><w:t>Synthetic fixture</w:t></w:r></w:p></w:body></w:document>')
  for name,value in (extra or {}).items():archive.writestr(name,value)
 return out.getvalue()

def capability(source,**replace):
 now=datetime.now(timezone.utc)
 query={'X-Goog-Algorithm':'GOOG4-RSA-SHA256','X-Goog-Credential':'fixture@example.invalid/'+now.strftime('%Y%m%d')+'/auto/storage/goog4_request','X-Goog-Date':now.strftime('%Y%m%dT%H%M%SZ'),'X-Goog-Expires':'600','X-Goog-Signature':'a'*512,'X-Goog-SignedHeaders':'host'};query.update(replace)
 rule=source['mediaIntake']['redirect'];return 'https://'+rule['targetHost']+rule['targetPath']+'?'+urlencode(query)

class IntakeTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name);self.work=self.root/'collection';(self.work/'intents').mkdir(parents=True)
  self.base_selection=g.selection_config();self.base_manifest=g.manifest_config();self.stack=ExitStack();self.calls=[];self.responses=[];self.sources=deepcopy(k.successor_config()['intakeSources'])
  self.mode={'mode':'owner-directed-private-original-save/1','diagnosticReportPin':None,'minimumOriginalDedupSeconds':a.TTL,'httpResponseCacheEnabled':False,'preserveFailedIntents':True,'predecessors':[],'freshSources':[s['sourceKey'] for s in self.sources]}
  for key,value in [('OUTPUT',self.root),('LEGACY_CACHE',self.root/'legacy'),('GUARD',0)]:self.stack.enter_context(patch.object(a,key,value))
  self.stack.enter_context(patch('socket.create_connection',side_effect=AssertionError('live network forbidden')))
 def tearDown(self):self.stack.close();self.tmp.cleanup()
 def body(self,source):
  kind=source['validation']['kind']
  if kind=='docx-original':return docx()
  if kind=='json-original':return json.dumps({'success':True,'result':{'id':source['mediaIntake']['integrity']['expectedDatasetId'],'name':'fixture'}}).encode()
  head=source['mediaIntake']['integrity'].get('requiredHeader',['market_id','market'])
  return (','.join(head)+'\n'+','.join('1' for _ in head)+'\n').encode()
 def transport(self,spec,headers,*,deadline):
  self.calls.append((spec.source_key,repr(spec),headers));source=next(s for s in self.sources if s['sourceKey']==spec.source_key)
  if isinstance(spec,k.EphemeralStorageRequest):
   self.assertTrue(spec.url.startswith('https://storage.googleapis.com/'));self.assertEqual(headers,{'Accept-Encoding':'identity'})
  elif source['mediaIntake']['redirect']:
   response=Response(b'DO NOT READ REDIRECT BODY',302,[('Location',capability(source)),('Set-Cookie','private=fixture')]);self.responses.append(response);return response
  body=self.body(source);response=Response(body,200,[('Content-Type',source['expectedResponse']['content-type']),('Content-Length',str(len(body))),('Cache-Control','private, no-store'),('Set-Cookie','private=fixture'),('ETag','"fixture-etag"')]);self.responses.append(response);return response
 def run_source(self,index=0,**kwargs):return m.run_selected(self.sources[index],adapter=a,mode=self.mode,transport=kwargs.pop('transport',self.transport),**kwargs)
 def folder(self,index=0):return self.work/'private-originals'/a.sha(a.canonical(self.sources[index]))
 def test_all_five_strict_originals_save_and_reuse_with_exact_meters(self):
  meter=g.SharedBudget(7,13*k.MiB);one=[]
  for i,s in enumerate(self.sources):one.append(self.run_source(i,batch_meter=meter.child(s['sourceKey'],s['hardTransferBytes'],k.maximum_requests(s))))
  self.assertEqual([r['status'] for r in one],['verified-private-original']*5,one);self.assertEqual(meter.snapshot()['requests'],7)
  self.assertEqual(meter.snapshot()['bodyBytesRead'],sum(len(self.body(s)) for s in self.sources))
  self.assertEqual([r.reads for r in self.responses if r.status==302],[0,0]);self.assertTrue(all(r.closed for r in self.responses))
  self.calls=[]
  for i,s in enumerate(self.sources):
   again=self.run_source(i);self.assertEqual(again['network']['requests'],0);self.assertEqual(again['originalDisposition'],'retained-original-no-network');self.assertEqual(again['validation']['originalAcquiredAt'],one[i]['validation']['originalAcquiredAt'])
   self.assertEqual((self.folder(i)/k.original_filename(s)).read_bytes(),self.body(s));self.assertEqual((self.folder(i)/k.original_filename(s)).stat().st_mode&0o777,0o600)
  self.assertFalse(self.calls);self.assertFalse((self.work/'source-cache').exists())
 def test_capability_cookie_and_raw_validation_values_never_persist(self):
  report=self.run_source(3);self.assertEqual(report['status'],'verified-private-original',report)
  for path in self.work.rglob('*.json'):
   raw=path.read_text();self.assertNotIn('X-Goog-Credential',raw);self.assertNotIn('X-Goog-Signature',raw);self.assertNotIn('private=fixture',raw);self.assertNotIn('fixture-etag',raw)
  self.assertNotIn('X-Goog-',json.dumps(report));self.assertNotIn('X-Goog-',repr(k.redirect_request(self.sources[3],capability(self.sources[3]))))
 def test_wrong_endpoint_schema_or_rights_rejected_before_work(self):
  for field,value in [('url','https://example.invalid/a.csv'),('hardTransferBytes',9*k.MiB),('privateCustodyApproved',False),('validation',{'kind':'pdf-original'})]:
   source=deepcopy(self.sources[0]);source[field]=value
   with self.subTest(field=field),self.assertRaises(a.RefreshError):m.run_selected(source,adapter=a,mode=self.mode,transport=self.transport)
  self.assertEqual(self.calls,[])
 def test_denial_is_terminal_without_read_or_retry(self):
  response=Response(b'private denial',403,[('Content-Type','text/html')])
  first=self.run_source(0,transport=lambda *a,**kw:response);self.assertEqual(first['network']['requests'],1);self.assertEqual(first['network']['bodyBytesRead'],0);self.assertEqual(response.reads,0)
  second=self.run_source(0,transport=lambda *a,**kw:(_ for _ in ()).throw(AssertionError('retry')));self.assertEqual(second['errorCode'],'private-save-intent-uncertain');self.assertEqual(second['network']['requests'],0)
 def test_bad_publisher_redirect_stops_after_one_request_zero_body(self):
  response=Response(b'not allowed',302,[('Location','https://evil.invalid/?private=fixture')])
  first=self.run_source(3,transport=lambda *a,**kw:response);self.assertEqual(first['network'],{'requests':1,'bodyBytesRead':0});self.assertEqual(response.reads,0);self.assertTrue(response.closed);self.assertNotIn('evil.invalid',json.dumps(first))
 def test_storage_redirect_not_followed(self):
  def transport(spec,*args,**kwargs):
   if not isinstance(spec,k.EphemeralStorageRequest):return self.transport(spec,*args,**kwargs)
   return Response(b'not read',302,[('Location','https://storage.googleapis.com/other')])
  result=self.run_source(3,transport=transport);self.assertEqual(result['network'],{'requests':2,'bodyBytesRead':0});self.assertEqual(result['errorCode'],'source-response-not-permitted')
 def test_redirect_request_budget_exhaustion_has_no_second_request(self):
  result=self.run_source(3,batch_meter=g.SharedBudget(1,13*k.MiB).child('fixture',k.MiB,2));self.assertEqual(result['network']['requests'],1);self.assertEqual(result['errorCode'],'network-request-limit');self.assertEqual(len(self.calls),1);self.assertEqual(self.responses[0].reads,0)
 def test_redirect_rejects_changed_host_path_credentials_extra_duplicates_and_expired(self):
  s=self.sources[3];url=capability(s)
  bad=[url.replace('storage.googleapis.com','evil.invalid'),url.replace('.s001.docx','.s002.docx'),url.replace('https://','http://'),url+'&extra=x',url+'&X-Goog-Date=x',url+'#x',url.replace('storage.googleapis.com','user@storage.googleapis.com'),capability(s,**{'X-Goog-Date':'20000101T000000Z'}),capability(s,**{'X-Goog-Expires':'86401'}),capability(s,**{'X-Goog-SignedHeaders':'host;authorization'}),capability(s,**{'X-Goog-Algorithm':'GOOG4-HMAC-SHA256'})]
  for value in bad:
   with self.subTest(value=value[:50]),self.assertRaises(a.RefreshError):k.redirect_request(s,value)
 def test_unknown_location_or_duplicate_metadata_rejected_without_body(self):
  for headers in [[('Content-Type','text/csv'),('Content-Length','10'),('Content-Length','10')],[('Content-Type','text/csv'),('Content-Length','10'),('Transfer-Encoding','chunked')],[('Content-Type','text/html'),('Content-Length','10')],[('Content-Type','text/csv')],[('Content-Type','text/csv'),('Content-Length','10'),('Content-Encoding','gzip')],[('Content-Type','text/csv'),('Content-Length','10'),('Location','https://example.invalid')]]:
   with self.subTest(headers=headers),self.assertRaises(a.RefreshError):k.checked_headers(headers,self.sources[0])
 def validate_body(self,body,index=0):
  path=self.root/'fixture-original';path.write_bytes(body);path.chmod(0o600)
  return k.validate_original(SimpleNamespace(path=path,sha256=hashlib.sha256(body).hexdigest(),bytes=len(body),provenance={'originalAcquiredAt':'fixture-time'}),self.sources[index],time.monotonic()+10,a)
 def test_csv_header_record_encoding_and_html_rejection(self):
  for body,index in [(b'<html>error</html>',0),(b'a,b\n1\n',0),(b'a,a\n1,2\n',0),(b'a,b\n\xff,2\n',0),(b'a,b\n1,2\n',2),(b'a,b\n',0),(b'a,b\n1,\x00\n',0)]:
   with self.subTest(body=body),self.assertRaises(a.RefreshError):self.validate_body(body,index)
 def test_json_exact_dataset_duplicate_nonfinite_depth_rejection(self):
  for body in [b'{"success":true,"result":{"id":"wrong"}}',b'{"success":false,"result":{}}',b'{"success":true,"success":true}',b'{"x":NaN}',b'{"x":1e999}',b'{"x":'+b'['*130+b'1'+b']'*130+b'}']:
   with self.subTest(body=body[:40]),self.assertRaises(a.RefreshError):self.validate_body(body,1)
 def test_docx_traversal_macro_xml_dtd_invalid_crc_and_expansion_rejection(self):
  for body in [docx({'../escape':'x'}),docx({'word/vbaProject.bin':'x'}),docx({'word/oversized.txt':'x'*(k.MiB)}),b'not a docx',docx({'word/document.xml':'<!DOCTYPE x [<!ENTITY x "x">]><x/>'})]:
   with self.subTest(bytes=len(body)),self.assertRaises(a.RefreshError):self.validate_body(body,3)
  body=bytearray(docx());body[60]^=1
  with self.assertRaises(a.RefreshError):self.validate_body(bytes(body),3)
 def test_partial_retained_and_no_retry(self):
  r=Response(b'x',200,[('Content-Type','text/csv'),('Content-Length','100')]);reads=0
  def read(size):
   nonlocal reads
   reads+=1
   if reads==1:return b'a,b\n'
   raise TimeoutError('secret URL must not escape')
  r.read=read
  first=self.run_source(0,transport=lambda *a,**kw:r);self.assertEqual(first['network']['bodyBytesRead'],4);self.assertEqual(first['privateSaveState'],'partial-retained');self.assertEqual((self.folder()/'original.partial').read_bytes(),b'a,b\n')
  again=self.run_source(0);self.assertEqual(again['network']['requests'],0);self.assertNotIn('secret',json.dumps(first))
 def test_bad_metadata_and_capacity_prevent_get(self):
  source=self.sources[0];claim=self.work/'intents'/(a.sha(source['url'].encode())+'.json');claim.write_text('{}')
  first=self.run_source(0);self.assertEqual(first['network']['requests'],0);self.assertEqual(first['errorCode'],'source-claim-uncertain')
  with patch.object(a,'capacity',return_value=0):second=self.run_source(1)
  self.assertEqual(second['network']['requests'],0);self.assertEqual(self.calls,[])
 def test_global_budget_accounts_two_requests_and_no_double_preparation(self):
  selected=deepcopy(self.base_selection);selected.update(sources=self.sources,maximumRequests=7,maximumTransferBytes=13*k.MiB,preparation=[])
  selected['privateOriginalDownload']=self.mode;selected['parallelism']={**g.DEFAULT_PARALLELISM,'minimumHostStartSpacingSeconds':0}
  manifest=deepcopy(self.base_manifest);manifest['assets']=[{'assetId':s['mediaIntake']['assetId'],'sourceKey':s['sourceKey'],'bindings':[],'disposition':'eligible','retainedOriginal':None,'preparationContract':None} for s in self.sources];manifest['statTargets']=[]
  for cell in manifest['cells']:cell['assetIds']=[]
  with patch.object(g,'selection_config',return_value=selected),patch.object(g,'manifest_config',return_value=manifest):
   report=g.run_global(manifest,selected,transport=self.transport);g.sanitize_report(report)
  self.assertEqual(report['networkRequests'],7);self.assertEqual(len(report['changes']),5);self.assertEqual(report['preparedBytes'],0);self.assertLessEqual(report['observedPeakTransfers'],2)
  self.assertEqual([c['acquisition']['networkRequests'] for c in report['changes']],[1,1,1,2,2])
 def test_full_successor_join_summary_is_closed_bounded_and_counts_only_real_sources(self):
  selected,manifest=k.compose_for_review(self.base_selection,self.base_manifest,k.successor_config());selected['knownIntakeSuccessor']['status']='parent-reviewed-owner-manual'
  resources={'logicalCPUs':1,'affinityCPUs':1,'cgroupCPUCap':1,'effectiveCPUs':1,'memoryAvailableBytes':0,'cgroupMemoryHeadroomBytes':0,'effectiveMemoryBytes':0,'resourceLimitsIncomplete':False,'ioWorkers':8,'preparationWorkers':0,'perHostWorkers':1,'memoryPerPreparationBytes':2560*1024**2,'memoryReserveBytes':2*1024**3}
  def save(source,**kwargs):
   meter=kwargs['batch_meter']
   for _ in range(k.maximum_requests(source)):meter.start_request()
   return {'status':'failed','errorCode':'collector-rejected','network':meter.snapshot(),'validation':None,'responseMetadata':None,'responsePolicy':None,'cacheStatus':None,'originalDisposition':None,'privateSaveState':'none','localBodyBytes':0,'receiptPersistence':'written'}
  with patch.object(g,'selection_config',return_value=selected),patch.object(g,'manifest_config',return_value=manifest),patch.object(g,'effective_resources',return_value=resources),patch.object(g,'stat_original',return_value='stat-observed'),patch.object(g.save,'run_selected',side_effect=save),patch.object(g.media_save,'run_selected',side_effect=save),patch.object(g.taiwan,'run_diagnostics',return_value=None):
   report=g.run_global(manifest,selected,transport=lambda *a,**kw:(_ for _ in ()).throw(AssertionError('network')),owner_runtime=object());g.sanitize_report(report)
   self.assertEqual(report['networkRequests'],17);self.assertEqual(report['networkBytesRead'],0);self.assertEqual(len(report['reuseOutcomeJoins']),22);self.assertEqual(len([c for c in report['changes'] if c['acquisition']]),15);self.assertLess(len(a.canonical(report)),g.MAX_SUMMARY)
   bad=deepcopy(report);bad['reuseOutcomeJoins'][0]['memberOutcomeGroups'][0]['stage']='ready-nextstage'
   with self.assertRaises(ValueError):g.sanitize_report(bad)

 def test_prepared_draft_cannot_run_and_defaults_remain_immutable(self):
  selected,manifest=k.compose_for_review(self.base_selection,self.base_manifest,k.successor_config())
  with self.assertRaisesRegex(a.RefreshError,'media-intake-successor-inactive'):g.run_global(manifest,selected,transport=self.transport)
  self.assertFalse(self.calls);self.assertEqual(len(self.base_selection['sources']),10);self.assertEqual(g.SELECTION_PIN[1],k.successor_config()['basePins']['global-original-selection.json']['sha256'])

class HeaderEnvelopeTests(unittest.TestCase):
 def test_header_stream_never_reads_past_bound(self):
  from offmenu.refresh.bounded_media_transport import HeaderEnvelope,HeaderReader
  raw=io.BytesIO(b'X-Test: '+b'x'*70000+b'\r\n\r\nbody')
  envelope=HeaderEnvelope(65536);reader=HeaderReader(raw,envelope)
  with self.assertRaises(a.RefreshError):reader.readline()
  self.assertEqual(raw.tell(),65536);self.assertEqual(envelope.read,65536)
 def test_two_responses_share_one_source_envelope(self):
  from offmenu.refresh.bounded_media_transport import HeaderEnvelope,HeaderReader
  envelope=HeaderEnvelope(20)
  first=HeaderReader(io.BytesIO(b'X-A: 123\r\n\r\n'),envelope)
  self.assertEqual(first.readline(),b'X-A: 123\r\n');self.assertEqual(first.readline(),b'\r\n')
  secondraw=io.BytesIO(b'X-B: 456789123456\r\n\r\nbody');second=HeaderReader(secondraw,envelope)
  with self.assertRaises(a.RefreshError):second.readline()
  self.assertEqual(envelope.read,20);self.assertEqual(secondraw.tell(),8)
 def test_real_httpresponse_chunk_framing_and_trailers_share_redirect_envelope(self):
  import http.client
  from offmenu.refresh.bounded_media_transport import BoundedHTTPSFileTransport
  source=k.successor_config()['intakeSources'][3]
  first=b'HTTP/1.1 302 Found\r\nLocation: '+capability(source).encode()+b'\r\nContent-Length: 0\r\n\r\n'
  prefix=b'HTTP/1.1 200 OK\r\nContent-Type: '+source['expectedResponse']['content-type'].encode()+b'\r\nTransfer-Encoding: chunked\r\n\r\n'
  class Socket:
   def __init__(self,raw):self.raw=raw
   def makefile(self,*args):return self.raw
  class Connection:
   streams=[];opened=[]
   def __init__(self,*args,**kwargs):self.raw=io.BytesIO(self.streams.pop(0));self.sock=Socket(self.raw);self.opened.append(self)
   def request(self,*args,**kwargs):pass
   def getresponse(self):r=self.response_class(self.sock);r.begin();return r
   def close(self):pass
  for framing in (b'1;'+b'x'*70000+b'\r\nx\r\n0\r\n\r\n',b'1\r\nx\r\n0\r\nX-Trailer: '+b'y'*70000+b'\r\n\r\n'):
   Connection.streams=[first,prefix+framing];Connection.opened=[];transport=BoundedHTTPSFileTransport()
   with patch.object(http.client,'HTTPSConnection',Connection):
    redirect=transport(a.source_spec(source),{'Accept-Encoding':'identity'},deadline=time.monotonic()+2);redirect.close()
    response=transport(k.redirect_request(source,capability(source)),{'Accept-Encoding':'identity'},deadline=time.monotonic()+2)
    with self.assertRaises((a.RefreshError,http.client.IncompleteRead)):
     while response.read(100):pass
    consumed=Connection.opened[-1].raw.tell();response.close()
   self.assertEqual(transport.envelope.read,65536)
   self.assertLessEqual(len(first)+consumed,65539) # At most one data byte and its CRLF outside readline framing.

 def test_bounded_transport_uses_no_ambient_headers_or_proxy(self):
  from offmenu.refresh.bounded_media_transport import BoundedHTTPSFileTransport
  with self.assertRaises(a.RefreshError):BoundedHTTPSFileTransport()(SimpleNamespace(url='https://example.invalid/x',request_method='GET',request_body=''),{'Accept-Encoding':'identity','Cookie':'forbidden'},deadline=time.monotonic()+1)

class ReuseTests(unittest.TestCase):
 def setUp(self):self.manifest=g.manifest_config();self.successor=k.successor_config();self.joins=self.successor['reuseJoins'];self.indices={r['assetId']:i for i,r in enumerate(self.manifest['assets'])}
 def states(self):return [{'custody':'stat-observed','stage':'retained','code':None} for _ in self.manifest['assets']]
 def test_exact_partition_22_46_30_16_and_old_sources_unchanged(self):
  self.assertEqual(len(self.joins),22);members=set(m for r in self.joins for m in r['memberAssetIds']);self.assertEqual(len(members),46)
  alias=[r for r in self.joins if r['kind']=='exact-original-alias'];self.assertEqual(len(alias),16)
  before=g.selection_config();after,manifest=g.prepared_successor_configs();self.assertEqual(after['sources'][:10],before['sources']);self.assertEqual(len(after['sources']),15);self.assertEqual(after['maximumRequests'],17);self.assertLess(after['maximumTransferBytes'],256*k.MiB)
 def test_pure_join_zero_io_and_all_member_states_preserved(self):
  outcomes=self.states();family=self.joins[0];indices=[self.indices[k] for k in family['memberAssetIds']]
  sample=[('ready-nextstage',None),('held','selection-partial'),('error','parser-invalid-input'),('unsupported','unsupported-media'),('unverified',None),('retained',None)]
  for index,(stage,code) in zip(indices,sample):outcomes[index]={'custody':'verified-original' if stage=='ready-nextstage' else 'stat-observed','stage':stage,'code':code}
  original=deepcopy(outcomes)
  with patch('builtins.open',side_effect=AssertionError('IO forbidden')),patch('socket.create_connection',side_effect=AssertionError('GET forbidden')),patch.object(Path,'stat',side_effect=AssertionError('stat forbidden')):
   report=k.join_outcomes(self.joins,self.manifest,outcomes)
  self.assertEqual(outcomes[self.indices[family['assetId']]]['stage'],'held');self.assertEqual([outcomes[i] for i in indices],[original[i] for i in indices]);self.assertEqual(len(report[0]['memberOutcomeGroups']),6)
  self.assertTrue(all(r['metadataOnly'] for r in report))
 def test_partial_alias_inherits_exact_hold_and_no_verified_fabrication(self):
  alias=next(r for r in self.joins if r['kind']=='exact-original-alias');outcomes=self.states();member=self.indices[alias['memberAssetIds'][0]];target=self.indices[alias['assetId']]
  outcomes[member]={'custody':'stat-observed','stage':'held','code':'selection-partial'};k.join_outcomes(self.joins,self.manifest,outcomes);self.assertEqual(outcomes[target],outcomes[member]);self.assertEqual(outcomes[target]['custody'],'stat-observed')
 def test_original_mapping_hold_is_not_overridden(self):
  outcomes=self.states();target=self.indices[self.joins[0]['assetId']];outcomes[target]={'custody':'held','stage':'held','code':'read-permission-held'};k.join_outcomes(self.joins,self.manifest,outcomes);self.assertEqual(outcomes[target],{'custody':'held','stage':'held','code':'read-permission-held'})
 def test_explicit_frozen_binding_baseline_allows_only_preparation_attachment(self):
  current=deepcopy(self.manifest);member=self.joins[0]['memberAssetIds'][0];index=self.indices[member];current['assets'][index]['preparationContract']={'reviewedFixture':'metadata-only change'}
  with self.assertRaises(a.RefreshError):k.validate_joins(self.joins,current)
  k.validate_joins(self.joins,current,binding_manifest=self.manifest)
  current['assets'][index]['sourceStageHolds']=['read']
  with self.assertRaises(a.RefreshError):k.validate_joins(self.joins,current,binding_manifest=self.manifest)

 def test_changed_member_identity_duplicate_and_cycle_rejected(self):
  for alter in ('hash','duplicate','cycle'):
   joins=deepcopy(self.joins)
   if alter=='hash':joins[0]['memberAssetSHA256'][0]='0'*64
   elif alter=='duplicate':joins.append(deepcopy(joins[0]))
   else:joins[0]['memberAssetIds'][0]=joins[0]['assetId']
   with self.subTest(alter=alter),self.assertRaises(a.RefreshError):k.join_outcomes(joins,self.manifest,self.states())

if __name__=='__main__':unittest.main()
