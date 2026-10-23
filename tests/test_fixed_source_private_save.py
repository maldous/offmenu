"""User-directed private original fixtures, all synthetic and offline."""
from contextlib import ExitStack,redirect_stdout
from copy import deepcopy
import http.client,importlib.util,io,json,os,tempfile,time,unittest
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
def module(name,file):
 spec=importlib.util.spec_from_file_location(name,ROOT/'scripts'/file);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
m=module('save_batch_fixture','acquire-fixed-batch.py');a=m.a;save=m.save
d=module('save_dispatch','dispatch-foo-job.py')
BODY=b'%PDF-1.7\n1 0 obj\n<< /Type /Catalog >>\nendobj\n%%EOF\n'
class Response:
 def __init__(self,headers,status=200,body=BODY):self.headers=headers;self.status=status;self.body=io.BytesIO(body);self.reads=0
 def read(self,size):self.reads+=1;return self.body.read(size)
 def close(self):pass
class SaveTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name);self.stack=ExitStack();self.selected=deepcopy(m.selection_config());self.selected['planningGuardBytes']=0
  self.work=self.root/'collection';(self.work/'intents').mkdir(parents=True);self.calls=[];self.responses=[]
  for source,prior in zip(self.selected['sources'],self.selected['privateOriginalDownload']['predecessors']):
   source['hardTransferBytes']=len(BODY)+16
   if source['expectedBytes'] is not None:source['expectedBytes']=len(BODY);source['expectedResponse']['content-length']=str(len(BODY))
   fingerprint=a.sha(a.canonical(source));prior['sourceContractSHA256']=fingerprint
   detail={'sourceKey':source['sourceKey'],'selectionSHA256':fingerprint,'status':'failed','errorCode':'collector-rejected','network':{'requests':1,'bodyBytesRead':0},'responseMetadata':{'httpStatus':200}}
   raw=a.canonical(detail);prior['detailSHA256']=a.sha(raw);(self.work/('fixed-source-result-'+prior['detailSHA256']+'.json')).write_bytes(raw)
   claim={'schemaVersion':'offmenu-fixed-source-intent/1','sourceKey':source['sourceKey'],'url':source['url'],'owner':0,'selectionSHA256':fingerprint,'requestIdentitySHA256':a.sha(a.canonical(a.source_spec(source).identity())),'state':'failed-no-retry','errorCode':'collector-rejected','network':{'requests':1,'bodyBytesRead':0}}
   raw=a.canonical(claim);prior['intentSHA256']=a.sha(raw);(self.work/'intents'/(a.sha(source['url'].encode())+'.json')).write_bytes(raw)
  self.selected['maximumTransferBytes']=sum(s['hardTransferBytes'] for s in self.selected['sources'])
  self.before={p.name:p.read_bytes() for p in (self.work/'intents').iterdir()}
  for key,value in [('OUTPUT',self.root),('LEGACY_CACHE',self.root/'legacy'),('GUARD',0)]:self.stack.enter_context(patch.object(a,key,value))
  self.stack.enter_context(patch('socket.create_connection',side_effect=AssertionError('no live network')))
 def tearDown(self):self.stack.close();self.tmp.cleanup()
 def folder(self,index=0):return self.work/'private-originals'/a.sha(a.canonical(self.selected['sources'][index]))
 def transport(self,spec,headers,*,deadline):
  self.calls.append((spec,headers,deadline));source=next(s for s in self.selected['sources'] if s['sourceKey']==spec.source_key)
  h=list(source['expectedResponse'].items())+[('Cache-Control','private, no-store, no-cache'),('Set-Cookie','secret=a'),('Set-Cookie','secret=b'),('Content-Security-Policy',"default-src 'none'"),('Content-Security-Policy',"sandbox"),('Content-Security-Policy',"script-src 'none'")]
  if source['expectedBytes'] is None:h.append(('Transfer-Encoding','chunked'))
  response=Response(h);self.responses.append(response);return response
 def run_batch(self,transport=None):
  with patch.object(save,'validate_mode',return_value=self.selected['privateOriginalDownload']):return m.run_batch(self.selected,transport=transport or self.transport)
 def clean(self,r):
  with patch.object(m,'selection_config',return_value=self.selected):return m.sanitize_report(r)
 def test_five_private_downloads_no_http_cache_and_prior_intents_preserved(self):
  r=self.clean(self.run_batch());self.assertEqual(r['status'],'complete',r);self.assertEqual(r['networkRequests'],5);self.assertEqual(r['networkBytesRead'],len(BODY)*5)
  self.assertFalse((self.work/'source-cache').exists());self.assertEqual({p.name:p.read_bytes() for p in (self.work/'intents').iterdir()},self.before)
  for i in range(5):
   self.assertEqual((self.folder(i)/'original.pdf').read_bytes(),BODY);self.assertEqual((self.folder(i)/'original.pdf').stat().st_mode&0o777,0o600);self.assertEqual(self.folder(i).stat().st_mode&0o777,0o700)
   self.assertEqual((self.folder(i)/'successor-intent.json').stat().st_mode&0o777,0o600)
   saved=json.loads((self.folder(i)/'provenance.json').read_text());self.assertTrue(saved['responsePolicy']['cacheControlNoStore']);self.assertFalse(saved['httpResponseCacheEnabled']);self.assertNotIn('secret=',json.dumps(saved))
  self.assertTrue(all(c[1]=={'Accept-Encoding':'identity'} for c in self.calls))
 def test_saved_original_dedup_zero_network_preserves_original_time(self):
  first=self.run_batch();self.calls=[];second=self.clean(self.run_batch());self.assertEqual(second['networkRequests'],0);self.assertFalse(self.calls)
  self.assertEqual([i['originalAcquiredAt'] for i in first['items']],[i['originalAcquiredAt'] for i in second['items']]);self.assertTrue(all(i['originalDisposition']=='retained-original-no-network' for i in second['items']))
 def test_mutated_prior_intent_stops_its_source(self):
  prior=next((self.work/'intents').iterdir());v=json.loads(prior.read_text());v['network']['bodyBytesRead']=1;prior.write_bytes(a.canonical(v));raw=prior.read_bytes()
  r=self.clean(self.run_batch());self.assertEqual(r['networkRequests'],4);self.assertEqual(prior.read_bytes(),raw)
 def test_known_alternate_claim_blocks_source(self):
  p=self.root/'legacy/source-claims.json';p.parent.mkdir();p.write_bytes(a.canonical({self.selected['sources'][0]['url']:{'owner':4,'state':'active'}}))
  r=self.clean(self.run_batch());self.assertEqual(r['networkRequests'],4);self.assertEqual(r['items'][0]['errorCode'],'known-exact-source-alternate-cache')
 def test_previous_cache_partial_stops_its_source(self):
  source=self.selected['sources'][0];folder=self.work/'source-cache/requests'/a.sha(a.canonical(a.source_spec(source).identity()));folder.mkdir(parents=True);(folder/'body.partial').write_bytes(b'old')
  r=self.clean(self.run_batch());self.assertEqual(r['networkRequests'],4);self.assertEqual((folder/'body.partial').read_bytes(),b'old')
 def test_ambiguous_critical_duplicates_reject_before_body(self):
  for key in ['Content-Length','Content-Type','Location','Cache-Control','Vary','Content-Encoding','Transfer-Encoding','Strict-Transport-Security']:
   with self.subTest(key=key),self.assertRaises(a.RefreshError):save.download_headers(list(self.selected['sources'][0]['expectedResponse'].items())+[(key,'a'),(key,'b')],self.selected['sources'][0],a)
 def test_no_cookies_stored_and_invalid_csp_value_rejected(self):
  s=self.selected['sources'][0]
  with self.assertRaises(a.RefreshError):save.download_headers(list(s['expectedResponse'].items())+[('Content-Security-Policy','bad\r\nvalue')],s,a)
  self.assertEqual(save.policy_facts([('Set-Cookie','secret')])['setCookieFields'],1)
 def test_vary_cookie_and_encoded_body_remain_blocked(self):
  for key,value in [('Vary','Cookie'),('Content-Encoding','gzip')]:
   with self.subTest(key=key),self.assertRaises(a.RefreshError):save.download_headers(list(self.selected['sources'][0]['expectedResponse'].items())+[(key,value)],self.selected['sources'][0],a)
 def test_denial_and_redirect_no_body_and_continue(self):
  count=0
  def transport(*args,**kwargs):
   nonlocal count
   r=self.transport(*args,**kwargs);count+=1
   if count==1:r.status=403
   if count==2:r.status=302;r.headers.append(('Location','https://other.example/?secret=x'))
   return r
  r=self.clean(self.run_batch(transport));self.assertEqual(r['networkRequests'],5);self.assertEqual(r['networkBytesRead'],len(BODY)*3);self.assertEqual([x.reads for x in self.responses[:2]],[0,0]);self.assertNotIn('secret',json.dumps(r))
 def test_partial_failure_is_retained_no_automatic_retry(self):
  count=0
  def transport(*args,**kwargs):
   nonlocal count
   r=self.transport(*args,**kwargs);count+=1
   if count==1:
    calls=0
    def read(size):
     nonlocal calls
     calls+=1
     if calls==1:return BODY[:7]
     raise TimeoutError('private')
    r.read=read
   return r
  r=self.clean(self.run_batch(transport));self.assertEqual(r['items'][0]['networkBytesRead'],7);self.assertEqual(r['items'][0]['privateSaveState'],'partial-retained');self.assertEqual((self.folder()/'original.partial').read_bytes(),BODY[:7]);self.calls=[]
  again=self.clean(self.run_batch());self.assertEqual(again['networkRequests'],0);self.assertFalse(self.calls)
 def test_full_uncommitted_original_after_provenance_failure_is_retained(self):
  real=a.write_immutable
  def write(path,value):
   if path.name=='provenance.json':raise a.RefreshError('fixed-evidence-invalid')
   return real(path,value)
  with patch.object(a,'write_immutable',side_effect=write):r=self.clean(self.run_batch())
  self.assertEqual(r['networkRequests'],5);self.assertEqual(r['networkBytesRead'],len(BODY)*5);self.assertTrue(all(i['privateSaveState']=='uncommitted-original' for i in r['items']));self.assertEqual((self.folder()/'original.pdf').read_bytes(),BODY)
  self.calls=[];again=self.clean(self.run_batch());self.assertEqual(again['networkRequests'],0)
 def test_late_result_failure_preserves_counters_policy_and_local_files(self):
  real=a.write_immutable
  def write(path,value):
   if path.name.startswith('private-original-result-'):raise a.RefreshError('fixed-evidence-invalid')
   return real(path,value)
  with patch.object(a,'write_immutable',side_effect=write):r=self.clean(self.run_batch())
  self.assertEqual(r['networkRequests'],5);self.assertEqual(r['networkBytesRead'],len(BODY)*5);self.assertTrue(all(i['errorCode']=='result-write-failed' and i['responsePolicy']['cacheControlNoStore'] for i in r['items']))
 def test_successor_claim_failure_preserves_transfer_and_original(self):
  real=save.write_private_intent
  def write(path,value,adapter):
   if path.name=='successor-intent.json' and value.get('state')=='verified':raise OSError()
   return real(path,value,adapter)
  with patch.object(save,'write_private_intent',side_effect=write):r=self.clean(self.run_batch())
  self.assertEqual(r['networkRequests'],5);self.assertEqual(r['networkBytesRead'],len(BODY)*5);self.assertTrue(all(i['privateSaveState']=='uncommitted-original' for i in r['items']))
 def test_release_failure_preserves_meters(self):
  real=a.release_own_reservation
  def release(*args):real(*args);raise OSError()
  with patch.object(a,'release_own_reservation',side_effect=release):r=self.clean(self.run_batch())
  self.assertEqual(r['networkRequests'],5);self.assertEqual(r['networkBytesRead'],len(BODY)*5);self.assertTrue(all(i['errorCode']=='reservation-release-failed' for i in r['items']))
 def test_cap_and_capacity_failure_before_or_at_bound(self):
  with patch.object(a,'capacity',return_value=0):r=self.clean(self.run_batch())
  self.assertEqual(r['networkRequests'],0)
 def test_malformed_http_counted_no_raw_text(self):
  def transport(*args,**kwargs):raise http.client.BadStatusLine('private-server-text')
  r=self.clean(self.run_batch(transport));self.assertEqual(r['networkRequests'],5);self.assertNotIn('private-server-text',json.dumps(r))
 def test_partial_write_failure_reports_stat_extent_not_network_count(self):
  real=save.os.fdopen;opened=0
  class FailingWriter:
   def __init__(self,stream):self.stream=stream
   def __enter__(self):self.stream.__enter__();return self
   def __exit__(self,*args):return self.stream.__exit__(*args)
   def write(self,block):self.stream.write(block[:7]);self.stream.flush();raise OSError('synthetic-write-failure')
   def flush(self):return self.stream.flush()
   def fileno(self):return self.stream.fileno()
  def fdopen(fd,*args,**kwargs):
   nonlocal opened
   stream=real(fd,*args,**kwargs)
   if args==('wb',):
    opened+=1
    if opened==2:return FailingWriter(stream)
   return stream
  with patch.object(save.os,'fdopen',side_effect=fdopen):r=self.clean(self.run_batch())
  self.assertEqual(r['items'][0]['networkBytesRead'],len(BODY));self.assertEqual(r['items'][0]['localBodyBytes'],7);self.assertEqual(r['items'][0]['privateSaveState'],'partial-retained')
 def test_private_marker_directory_is_durable_before_transport(self):
  synced=[];real=save.fsync_directory
  def sync(path):synced.append(Path(path));return real(path)
  def transport(*args,**kwargs):
   source=next(s for s in self.selected['sources'] if s['sourceKey']==args[0].source_key);folder=self.work/'private-originals'/a.sha(a.canonical(source))
   self.assertIn(folder,synced);self.assertIn(folder.parent,synced);self.assertIn(folder.parent.parent,synced)
   return self.transport(*args,**kwargs)
  with patch.object(save,'fsync_directory',side_effect=sync):self.assertEqual(self.clean(self.run_batch(transport))['status'],'complete')
 def test_policy_normalization_matches_transfer_acceptance(self):
  facts=save.policy_facts([('Vary',''),('Content-Encoding','Identity')]);self.assertEqual(facts['vary'],'absent');self.assertEqual(facts['contentEncoding'],'identity')
 def test_stdlib_http_chunked_response_with_no_store_and_multiple_csp(self):
  import threading
  from offmenu.refresh.acquisition import _Response
  source=self.selected['sources'][0];headers=list(source['expectedResponse'].items())+[('Transfer-Encoding','chunked'),('Cache-Control','no-store'),('Content-Security-Policy',"default-src 'none'"),('Content-Security-Policy','sandbox')]
  wire=b'HTTP/1.1 200 OK\r\n'+b''.join(k.encode()+b': '+v.encode()+b'\r\n' for k,v in headers)+b'\r\n'+hex(len(BODY))[2:].encode()+b'\r\n'+BODY+b'\r\n0\r\n\r\n'
  class Sock:
   def makefile(self,*args):return io.BytesIO(wire)
  class Closed:
   def close(self):pass
   def cancel(self):pass
  response=http.client.HTTPResponse(Sock());response.begin();wrapped=_Response(Closed(),response,Closed(),threading.Event())
  result=save.run_selected(source,adapter=a,mode=self.selected['privateOriginalDownload'],transport=lambda *args,**kwargs:wrapped)
  self.assertEqual(result['status'],'verified-private-original',result);self.assertEqual(result['network']['bodyBytesRead'],len(BODY))
 def test_exact_framed_cap_does_not_require_overread(self):
  source=self.selected['sources'][3];prior=self.selected['privateOriginalDownload']['predecessors'][3];source['hardTransferBytes']=len(BODY);fp=a.sha(a.canonical(source));prior['sourceContractSHA256']=fp
  detail={'sourceKey':source['sourceKey'],'selectionSHA256':fp,'status':'failed','errorCode':'collector-rejected','network':{'requests':1,'bodyBytesRead':0},'responseMetadata':{'httpStatus':200}}
  raw=a.canonical(detail);prior['detailSHA256']=a.sha(raw);(self.work/('fixed-source-result-'+prior['detailSHA256']+'.json')).write_bytes(raw)
  claimpath=self.work/'intents'/(a.sha(source['url'].encode())+'.json');claim=json.loads(claimpath.read_text());claim['selectionSHA256']=fp;claim['requestIdentitySHA256']=a.sha(a.canonical(a.source_spec(source).identity()));claimpath.write_bytes(a.canonical(claim));prior['intentSHA256']=a.sha(claimpath.read_bytes())
  response=Response(list(source['expectedResponse'].items())+[('Cache-Control','no-store')])
  result=save.run_selected(source,adapter=a,mode=self.selected['privateOriginalDownload'],transport=lambda *args,**kwargs:response)
  self.assertEqual(result['status'],'verified-private-original',result);self.assertEqual(response.reads,1)
 def test_closed_policy_rejects_raw_header_fields(self):
  r=self.run_batch();r['items'][0]['responsePolicy']['raw']='private'
  with self.assertRaises(ValueError):self.clean(r)
 def test_actual_exact_mode_pins_and_default_collector_unchanged(self):
  with patch.object(a,'GUARD',88418025472):s=m.selection_config()
  self.assertEqual(len(s['sources']),5);self.assertEqual(s['maximumTransferBytes'],61538304);self.assertEqual(s['privateOriginalDownload']['mode'],'owner-directed-private-original-save/1')
  from offmenu.refresh.acquisition import _retention
  for value in ['private','no-store']:
   with self.assertRaises(a.RefreshError):_retention({'cache-control':value})
 def test_main_and_dispatcher_preserve_new_actual_summary(self):
  with patch.object(a,'GUARD',88418025472):selected=m.selection_config()
  r=m.blocked_report('private-save-contract-invalid');self.assertEqual(d.safe_evidence(a.canonical(r))['fixedSourceBatch'],r)
  items=[]
  for s in selected['sources']:
   count=s['expectedBytes'] or 1234
   detail={'status':'verified-private-original','errorCode':None,'network':{'requests':1,'bodyBytesRead':count},'responseMetadata':a.response_metadata(200,s['expectedResponse'],request_url=s['url']), 'responsePolicy':save.policy_facts([('Cache-Control','private,no-store')]),'originalDisposition':'saved-original','privateSaveState':'saved-original','localBodyBytes':count,'cacheStatus':None,'validation':{'bytes':count,'sha256':'a'*64,'originalAcquiredAt':'2026-10-18T20:30:00+00:00'},'receiptPersistence':'written'}
   items.append(m.item_report(s,detail))
  report={'schemaVersion':m.SCHEMA,'batchId':selected['batchId'],'selectionSHA256':a.sha(a.canonical(selected)),'status':'complete','errorCode':None,'networkRequests':5,'networkBytesRead':sum(i['networkBytesRead'] for i in items),'items':items,**a.SAFETY}
  evidence=d.safe_evidence(a.canonical(report));self.assertEqual(evidence['fixedSourceBatch'],report);self.assertLess(len(a.canonical(report)),12288)
if __name__=='__main__':unittest.main()
