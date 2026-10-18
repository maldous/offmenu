"""Global orchestration fixtures. No source requests or original data."""
from copy import deepcopy
import importlib.util,io,json,tempfile,time,unittest
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
def module(name,file):
 spec=importlib.util.spec_from_file_location(name,ROOT/file);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
g=module('global_fixture','scripts/collect-fixed-global.py')
REAL_RESOURCES=g.effective_resources
f=module('global_save_fixture','tests/test_fixed_source_private_save.py')
class GlobalTests(unittest.TestCase):
 tearDown=f.SaveTests.tearDown
 folder=f.SaveTests.folder
 transport=f.SaveTests.transport
 def setUp(self):
  f.SaveTests.setUp(self)
  for key,value in [('a',f.a),('b',f.m),('save',f.save)]:self.stack.enter_context(patch.object(g,key,value))
  self.stack.enter_context(patch.object(g.time,'sleep',return_value=None))
  self.selected['schemaVersion']='offmenu-global-source-selection/1';self.selected['preparation']=[];self.selected['parallelism']={**g.DEFAULT_PARALLELISM,'minimumHostStartSpacingSeconds':0}
  resources={'logicalCPUs':24,'affinityCPUs':24,'cgroupCPUCap':24,'effectiveCPUs':24,'memoryAvailableBytes':64*1024**3,'cgroupMemoryHeadroomBytes':64*1024**3,'effectiveMemoryBytes':64*1024**3,'resourceLimitsIncomplete':False,'ioWorkers':8,'preparationWorkers':8,'perHostWorkers':1,'memoryPerPreparationBytes':2560*1024**2,'memoryReserveBytes':2*1024**3}
  self.stack.enter_context(patch.object(g,'effective_resources',return_value=resources))
  countries=[chr(65+i//26)+chr(65+i%26) for i in range(249)];types=['type'+str(i) for i in range(13)]
  assets=[]
  for source in self.selected['sources']:
   assets.append({'assetId':'source:'+source['sourceKey'],'sourceKey':source['sourceKey'],'bindings':[{'country':'AA','type':'type0'}],'disposition':'eligible','retainedOriginal':None,'preparationContract':None})
  for disposition in ('held','unverified','missing-contract','retained'):
   assets.append({'assetId':'fixture:'+disposition,'sourceKey':None,'bindings':[],'disposition':disposition,'retainedOriginal':None,'preparationContract':None})
  self.manifest={'schemaVersion':'offmenu-global-collection-manifest/1','countries':countries,'types':types,'assets':assets,'cells':[{'country':c,'type':t,'assetIds':[r['assetId'] for r in assets[:5]] if c=='AA' and t=='type0' else []} for c in countries for t in types]}
 def execute(self,**kwargs):
  # Source validator covered independently; these predecessor pins are synthetic.
  return g.run_global(self.manifest,self.selected,transport=self.transport,**kwargs)
 def clean_global(self,report):
  with patch.object(g,'manifest_config',return_value=self.manifest),patch.object(g,'selection_config',return_value=self.selected):return g.sanitize_report(report)
 def test_global_all_rows_and_cells_not_only_transfer_list(self):
  report=self.clean_global(self.execute());self.assertEqual(report['assetCount'],9);self.assertEqual(len(self.manifest['cells']),3237);self.assertEqual(report['checkpointCount'],5)
  rows=g.expand_outcomes(report['assetOutcomeGroups'],9);self.assertEqual(rows[5]['stage'],'held');self.assertEqual(report['networkRequests'],5);self.assertEqual(report['cellStageCounts']['overrides'][0][1][g.STATES.index('retained')],5)
  self.assertLess(len(f.a.canonical(report)),g.MAX_SUMMARY)
 def test_global_failed_source_continues_and_keeps_meters(self):
  real=f.save.run_selected;calls=0
  def run(*args,**kwargs):
   nonlocal calls
   calls+=1
   if args[0]['sourceKey']==self.selected['sources'][1]['sourceKey']:kwargs['batch_meter'].start_request();raise RuntimeError('private-error')
   return real(*args,**kwargs)
  with patch.object(f.save,'run_selected',side_effect=run):report=self.clean_global(self.execute())
  self.assertEqual(report['networkRequests'],5);self.assertEqual(report['networkBytesRead'],len(f.BODY)*4);self.assertEqual(report['changes'][1]['acquisition']['networkRequests'],1);self.assertNotIn('private-error',json.dumps(report))
 def test_global_exact_adverse_source_blocks_only_source(self):
  report=self.clean_global(self.execute(adverse_evidence=[{'sourceKey':self.selected['sources'][0]['sourceKey']}]))
  self.assertEqual(report['networkRequests'],4);self.assertEqual(report['changes'][0]['acquisition']['errorCode'],'global-source-conflict')
 def test_global_no_implicit_clearance_from_missing_catalogue(self):
  self.assertFalse(self.selected['coordinatorIntent']['nativeClaimsExhaustive']);self.assertFalse(self.selected['coordinatorIntent']['missingMatchMeansUnowned'])
 def test_group_projection_requires_every_asset_once(self):
  report=self.execute();groups=report['assetOutcomeGroups'];groups[0]['assetRanges'].append(groups[0]['assetRanges'][0])
  with self.assertRaises(ValueError):self.clean_global(report)
 def test_closed_global_summary_rejects_raw_fields(self):
  report=self.execute();report['raw']='secret'
  with self.assertRaises(ValueError):self.clean_global(report)
 def test_closed_acquisition_summary_rejects_raw_headers(self):
  report=self.execute();report['changes'][0]['acquisition']['headers']={'set-cookie':'private'}
  with self.assertRaises(ValueError):self.clean_global(report)
 def test_late_checkpoint_failure_preserves_results(self):
  real=f.a.write_immutable
  def write(path,value):
   if path.name.startswith('asset-') or path.name.startswith('result-'):raise f.a.RefreshError('fixed-evidence-invalid')
   return real(path,value)
  with patch.object(f.a,'write_immutable',side_effect=write):report=self.clean_global(self.execute())
  self.assertEqual(report['networkRequests'],5);self.assertEqual(report['networkBytesRead'],len(f.BODY)*5);self.assertFalse(report['detailPersisted']);self.assertIn('global-checkpoint-failed',report['globalErrors'])
 def test_static_path_stat_never_reads_body(self):
  path=self.root/'some-original';path.write_bytes(b'raw')
  with patch('builtins.open',side_effect=AssertionError('body-read')):self.assertEqual(g.stat_original({'path':str(path),'bytes':3}),'stat-observed')
  self.assertEqual(g.stat_original({'path':str(path),'bytes':4}),'extent-mismatch');link=self.root/'symlink';link.symlink_to(path);self.assertEqual(g.stat_original({'path':str(link),'bytes':3}),'unsafe-path')
 def test_static_parent_denied_not_absent(self):
  with patch.object(g.os,'access',return_value=False):self.assertEqual(g.stat_original({'path':str(self.root/'absent')}),'inaccessible')
 def test_global_deadline_stops_gets_but_reports_every_asset(self):
  with patch.object(g,'MAX_SECONDS',-1):report=self.execute()
  self.assertEqual(report['networkRequests'],0);self.assertEqual(report['assetCount'],9);self.assertEqual(report['checkpointCount'],0)
 def test_exact_country_type_completeness_validated(self):
  self.assertIs(g.validate_manifest(self.manifest),self.manifest);self.manifest['cells'].pop()
  with self.assertRaises(f.a.RefreshError):g.validate_manifest(self.manifest)
 def test_fresh_private_mode_download_dedup_and_old_claim_block(self):
  source=deepcopy(self.selected['sources'][0]);source.update(sourceKey='fixture.fresh',url='https://example.org/fresh.pdf',aliases=[],queryKeys=[])
  mode={'mode':'owner-directed-private-original-save/1','diagnosticReportPin':None,'minimumOriginalDedupSeconds':f.a.TTL,'httpResponseCacheEnabled':False,'preserveFailedIntents':True,'predecessors':[],'freshSources':[source['sourceKey']]}
  f.save.validate_mode(mode,{'sources':[source]},f.a)
  def transport(*args,**kwargs):return f.Response(list(source['expectedResponse'].items())+[('Transfer-Encoding','chunked')])
  one=f.save.run_selected(source,adapter=f.a,mode=mode,transport=transport);self.assertEqual(one['status'],'verified-private-original',one)
  two=f.save.run_selected(source,adapter=f.a,mode=mode,transport=lambda *a,**k:(_ for _ in ()).throw(AssertionError('duplicate')));self.assertEqual(two['network']['requests'],0);self.assertEqual(two['originalDisposition'],'retained-original-no-network')
 def test_fresh_private_mode_known_old_intent_blocks_before_get(self):
  source=self.selected['sources'][0];mode={'mode':'owner-directed-private-original-save/1','diagnosticReportPin':None,'minimumOriginalDedupSeconds':f.a.TTL,'httpResponseCacheEnabled':False,'preserveFailedIntents':True,'predecessors':[],'freshSources':[source['sourceKey']]}
  result=f.save.run_selected(source,adapter=f.a,mode=mode,transport=lambda *a,**k:(_ for _ in ()).throw(AssertionError('GET')));self.assertEqual(result['network']['requests'],0);self.assertEqual(result['errorCode'],'source-claim-uncertain')
 def test_fresh_mode_cannot_omit_or_overlap_source(self):
  mode={'mode':'owner-directed-private-original-save/1','diagnosticReportPin':None,'minimumOriginalDedupSeconds':f.a.TTL,'httpResponseCacheEnabled':False,'preserveFailedIntents':True,'predecessors':[],'freshSources':[]}
  with self.assertRaises(f.a.RefreshError):f.save.validate_mode(mode,self.selected,f.a)
 def test_missing_later_mapping_fails_before_any_get(self):
  self.manifest['assets'][4]['sourceKey']=None
  with self.assertRaises(f.a.RefreshError):self.execute()
  self.assertEqual(self.calls,[])
 def test_late_capability_failure_does_not_lose_successful_transfers(self):
  with patch.object(g.media,'capabilities',side_effect=RuntimeError('private')):report=self.clean_global(self.execute())
  self.assertEqual(report['networkRequests'],5);self.assertTrue(all(not p['available'] for p in report['runtimeCapabilities']['optionalParsers'].values()))
 def test_selected_retained_source_read_hold_skips_preparation(self):
  key=self.selected['sources'][0]['sourceKey'];asset=self.manifest['assets'][0]
  self.selected['sources']=self.selected['sources'][1:];self.selected['maximumRequests']=4;self.selected['maximumTransferBytes']=sum(s['hardTransferBytes'] for s in self.selected['sources'])
  self.selected['privateOriginalDownload']['predecessors']=self.selected['privateOriginalDownload']['predecessors'][1:]
  asset['disposition']='held';asset['sourceStageHolds']=['read']
  self.selected['preparation']=[{'sourceKey':key,'permissions':{'read':True,'extract':True,'copy':True},'holds':[],'expectedMediaTypes':['application/pdf'],'parameters':{},'retainedOriginal':{'path':str(self.root/'must-not-read'),'sha256':'a'*64,'bytes':1}}]
  with patch.object(g,'run_preparation',side_effect=AssertionError('read')):report=self.execute(prepare=lambda *args:(_ for _ in ()).throw(AssertionError('read')))
  self.assertEqual(g.expand_outcomes(report['assetOutcomeGroups'],9)[0]['stage'],'held');self.assertIsNone(report['changes'][-1]['preparation'])
 def test_full_actual_cardinality_complete_projection(self):
  actual_manifest=g.manifest_config();actual_selected=g.pinned(g.SELECTION_PIN);self.manifest=actual_manifest;self.selected=actual_selected
  def acquire(source,**kwargs):
   count=source['expectedBytes'] or 4096;kwargs['batch_meter'].start_request();kwargs['batch_meter'].record_bytes(count)
   return {'status':'verified-private-original','errorCode':None,'network':{'requests':1,'bodyBytesRead':count},'responseMetadata':f.a.response_metadata(200,source['expectedResponse'],request_url=source['url']),
    'cacheStatus':None,'validation':{'bytes':count,'sha256':'a'*64,'originalAcquiredAt':'2026-10-18T21:00:00+00:00'},'receiptPersistence':'written','responsePolicy':f.save.policy_facts([('Cache-Control','private,no-store')]),'originalDisposition':'saved-original','privateSaveState':'saved-original','localBodyBytes':count}
  def prepare(asset_id,contract,path,folder,deadline,remaining):
   result={'status':'unsupported','errorCode':'parser-unavailable','stages':{'integrity':'passed','media':'passed','extraction':'unsupported'},'actualMediaType':contract['expectedMediaTypes'][0],
    'originalSHA256':contract['expectedSHA256'],'originalBytes':contract['expectedBytes'],'outputs':[],'nextStageReady':False,'metrics':{'pageCount':2000,'selectedPageCount':2000,'selectedExtentComplete':True}}
   return result,None,0
  with patch.object(f.save,'run_selected',side_effect=acquire),patch.object(g,'stat_original',return_value='stat-observed'):
   report=g.run_global(actual_manifest,actual_selected,transport=lambda *a:None,prepare=prepare)
  report['retainedTaiwanDiagnostics']=g.taiwan.run_diagnostics(self.root,time.monotonic()+1)
  report=self.clean_global(report);self.assertEqual(report['assetCount'],len(actual_manifest['assets']));self.assertEqual(report['networkRequests'],10);self.assertEqual(report['statPathCount'],1937)
  self.assertGreaterEqual(len(report['changes']),40);self.assertLess(len(f.a.canonical(report)),g.MAX_SUMMARY)
  dispatch=module('global_actual_projection','scripts/dispatch-foo-job.py');evidence=dispatch.safe_evidence(f.a.canonical(report));self.assertEqual(evidence.get('globalCollection'),report,evidence)
 def test_owner_diagnostic_is_inside_existing_lease_and_deadline(self):
  import fcntl,os
  self.selected['sources']=[];self.selected['maximumRequests']=0;self.selected['maximumTransferBytes']=0;self.selected['preparation']=[]
  observed=[];original=g.taiwan.run_diagnostics
  def diagnostic(root,deadline):
   self.assertEqual(root,f.a.OUTPUT);self.assertGreater(deadline,time.monotonic());self.assertLessEqual(deadline,time.monotonic()+30)
   fd=os.open(self.work/'fixed-selection.lock',os.O_RDONLY)
   try:
    with self.assertRaises(BlockingIOError):fcntl.flock(fd,fcntl.LOCK_EX|fcntl.LOCK_NB)
   finally:os.close(fd)
   observed.append(True);return original(root,deadline)
  with patch.object(g.taiwan,'run_diagnostics',side_effect=diagnostic):report=self.clean_global(self.execute(owner_runtime=object()))
  self.assertEqual(observed,[True]);self.assertEqual(report['networkRequests'],0);self.assertIn('retainedTaiwanDiagnostics',report)
  report['retainedTaiwanDiagnostics']['rawBytes']='forbidden'
  with self.assertRaises(ValueError):self.clean_global(report)
 def test_projection_fallback_preserves_completed_sources_and_meter(self):
  report=self.execute();progress={'meter':{'requests':report['networkRequests'],'bodyBytesRead':report['networkBytesRead']},'changes':report['changes']}
  failure=g.projection_failure(self.selected,progress);clean=self.clean_global(failure);self.assertEqual(clean['networkRequests'],5);self.assertEqual(len(clean['completedSources']),5)
 def test_dispatcher_keeps_three_field_request_and_global_report_bound(self):
  dispatch=module('global_dispatch_fixture','scripts/dispatch-foo-job.py');request={'schemaVersion':1,'jobId':'global-test-20261019','profile':'global-collection'}
  self.assertEqual(dispatch.parse_request(f.a.canonical(request)),request);self.assertEqual(dispatch.report_limit(request),128*1024)
  with self.assertRaises(dispatch.JobError):dispatch.parse_request(f.a.canonical({**request,'url':'https://example.org'}))
  self.assertEqual([row[0] for row in dispatch.profile_steps('global-collection',ROOT)],['readiness','global-collection-tests','media-preparation-tests','global-collection'])
class ParallelTests(unittest.TestCase):
 setUp=GlobalTests.setUp
 tearDown=GlobalTests.tearDown
 execute=GlobalTests.execute
 clean_global=GlobalTests.clean_global
 transport=GlobalTests.transport
 folder=GlobalTests.folder
 def test_real_io_overlap_host_limit_independent_failure_and_resume(self):
  import threading
  lock=threading.Lock();both=threading.Event();active={};peak=0;first=set();violations=[]
  def transport(spec,headers,*,deadline):
   nonlocal peak
   host=g.urlsplit(spec.url).hostname
   with lock:
    active[host]=active.get(host,0)+1;peak=max(peak,sum(active.values()));first.add(host)
    if active[host]>1:violations.append(host)
    if len(first)>=2:both.set()
   self.assertTrue(both.wait(3),'different hosts never overlapped')
   response=self.transport(spec,headers,deadline=deadline)
   if spec.source_key==self.selected['sources'][0]['sourceKey']:response.status=403
   def close():
    with lock:active[host]-=1
   response.close=close;return response
  report=self.clean_global(g.run_global(self.manifest,self.selected,transport=transport))
  self.assertGreaterEqual(peak,2);self.assertEqual(violations,[]);self.assertEqual(report['networkRequests'],5)
  self.assertEqual(report['changes'][0]['acquisition']['errorCode'],'source-response-not-permitted')
  self.assertEqual(sum(x['acquisition']['status']=='verified-private-original' for x in report['changes']),4)
  calls=len(self.calls);again=self.clean_global(g.run_global(self.manifest,self.selected,transport=lambda *a,**k:(_ for _ in ()).throw(AssertionError('repeat GET'))))
  self.assertEqual(again['networkRequests'],0);self.assertEqual(len(self.calls),calls)
  self.assertEqual([r['assetIndex'] for r in report['changes']],sorted(r['assetIndex'] for r in report['changes']))
 def test_real_spawn_global_preparation_independent_failure_and_resume(self):
  self.selected['sources']=[];self.selected['maximumRequests']=0;self.selected['maximumTransferBytes']=0;self.selected['preparation']=[]
  for index in range(3):
   raw=(b'a,b\n1,2\n'*1000) if index<2 else b'not JSON'
   path=self.root/('original-'+str(index));path.write_bytes(raw)
   contract={'schemaVersion':g.media.SCHEMA,'assetId':self.manifest['assets'][index]['assetId'],'expectedSHA256':f.a.sha(raw),'expectedBytes':len(raw),'expectedMediaTypes':['text/csv'] if index<2 else ['application/json'],'permissions':{'read':True,'extract':True,'copy':True},'holds':[],'parameters':{'encoding':'utf-8','delimiter':',','hasHeader':True} if index<2 else {}}
   self.manifest['assets'][index].update(disposition='retained',retainedOriginal={'path':str(path),'sha256':f.a.sha(raw),'bytes':len(raw)},preparationContract=contract)
  first=self.clean_global(self.execute());self.assertEqual(first['networkRequests'],0);self.assertGreaterEqual(first['observedPeakPreparations'],2)
  self.assertEqual([x['preparation']['status'] for x in first['changes']],['ready','ready','failed']);self.assertGreater(first['preparedBytes'],0)
  second=self.clean_global(self.execute());self.assertEqual(second['preparedBytes'],0);self.assertTrue(all(x['preparation']['preparationReused'] for x in second['changes'][:2]))
  self.manifest['assets'][0]['sourceStageHolds']=['read'];third=self.clean_global(self.execute());held=third['changes'][0]['preparation'];self.assertEqual(held['status'],'held');self.assertFalse(held['preparationReused']);self.assertEqual(held['stages']['integrity'],'held')
 def test_global_spawn_deadline_reaps_workers_and_reports_all_rows(self):
  import multiprocessing
  self.selected['sources']=[];self.selected['maximumRequests']=0;self.selected['maximumTransferBytes']=0;self.selected['preparation']=[]
  path=self.root/'deadline.csv';raw=b'a,b\n1,2\n';path.write_bytes(raw)
  contract={'schemaVersion':g.media.SCHEMA,'assetId':self.manifest['assets'][0]['assetId'],'expectedSHA256':f.a.sha(raw),'expectedBytes':len(raw),'expectedMediaTypes':['text/csv'],'permissions':{'read':True,'extract':True,'copy':True},'holds':[],'parameters':{'encoding':'utf-8','delimiter':',','hasHeader':True}}
  self.manifest['assets'][0].update(disposition='retained',retainedOriginal={'path':str(path),'sha256':f.a.sha(raw),'bytes':len(raw)},preparationContract=contract)
  before={p.pid for p in multiprocessing.active_children()};start=time.monotonic()
  with patch.object(g,'MAX_SECONDS',20.01):report=self.execute()
  self.assertLess(time.monotonic()-start,5);self.assertEqual(report['assetCount'],9);self.assertEqual(report['networkRequests'],0)
  self.assertEqual({p.pid for p in multiprocessing.active_children()}-before,set())
 def test_unknown_preparation_failure_preserves_reserved_budget_and_continues(self):
  self.selected['sources']=[];self.selected['maximumRequests']=0;self.selected['maximumTransferBytes']=0;self.selected['preparation']=[]
  for index in range(2):
   path=self.root/('uncertain-'+str(index));raw=b'a,b\n1,2\n';path.write_bytes(raw)
   contract={'schemaVersion':g.media.SCHEMA,'assetId':self.manifest['assets'][index]['assetId'],'expectedSHA256':f.a.sha(raw),'expectedBytes':len(raw),'expectedMediaTypes':['text/csv'],'permissions':{'read':True,'extract':True,'copy':True},'holds':[],'parameters':{'encoding':'utf-8','delimiter':',','hasHeader':True}}
   self.manifest['assets'][index].update(disposition='retained',retainedOriginal={'path':str(path),'sha256':f.a.sha(raw),'bytes':len(raw)},preparationContract=contract)
  calls=[]
  def prepare(asset,contract,path,folder,deadline,maximum):
   calls.append(asset)
   if asset==self.manifest['assets'][0]['assetId']:(folder/'private-partial').write_bytes(b'abc');raise SystemExit('terminated-child')
   return {'status':'unsupported','errorCode':'parser-unavailable','stages':{'integrity':'passed','media':'passed','extraction':'unsupported'},'actualMediaType':'text/csv','originalSHA256':contract['expectedSHA256'],'originalBytes':contract['expectedBytes'],'outputs':[],'nextStageReady':False,'metrics':{}},None,0
  report=self.clean_global(self.execute(prepare=prepare));self.assertEqual(len(calls),2);self.assertEqual(report['preparedUncertainBytes'],128*1024**2)
  self.assertEqual(report['preparationUncertainGrants'],[[0,128*1024**2]]);self.assertEqual(len(list((self.work/'global-preparation').glob('*/reservation.bin'))),1)
 def test_atomic_request_and_byte_budget(self):
  from concurrent.futures import ThreadPoolExecutor
  budget=g.SharedBudget(4,40)
  def attempt(i):
   child=budget.child(str(i),10)
   try:child.start_request();child.record_bytes(10);return True
   except f.a.RefreshError:return False
  with ThreadPoolExecutor(max_workers=16) as pool:results=list(pool.map(attempt,range(50)))
  self.assertEqual(sum(results),4);self.assertEqual(budget.snapshot()['requests'],4);self.assertEqual(budget.snapshot()['bodyBytesRead'],40)
 def test_nested_cgroup_ancestor_cpu_and_memory_caps(self):
  real=g.effective_resources.__wrapped__ if hasattr(g.effective_resources,'__wrapped__') else REAL_RESOURCES
  files={'/proc/self/cgroup':'0::/user.slice/app','/proc/self/mountinfo':'29 23 0:26 / /sys/fs/cgroup rw - cgroup2 cgroup rw','/proc/meminfo':'MemAvailable: 67108864 kB'}
  for folder,cpu,cap,used in [('', 'max 100000','max','0'),('/user.slice','200000 100000',str(8*1024**3),str(2*1024**3)),('/user.slice/app','800000 100000',str(16*1024**3),str(1024**3))]:
   root='/sys/fs/cgroup'+folder;files.update({root+'/cpu.max':cpu,root+'/memory.max':cap,root+'/memory.current':used})
  with patch.object(g.os,'cpu_count',return_value=24),patch.object(g.os,'sched_getaffinity',return_value=set(range(24))):result=real(g.DEFAULT_PARALLELISM,files.__getitem__)
  self.assertEqual(result['effectiveCPUs'],2);self.assertEqual(result['effectiveMemoryBytes'],6*1024**3);self.assertEqual(result['preparationWorkers'],1);self.assertFalse(result['resourceLimitsIncomplete'])
  files.pop('/sys/fs/cgroup/cpu.max');files.pop('/sys/fs/cgroup/memory.max')
  def host_root(path):
   if path not in files:raise FileNotFoundError(path)
   return files[path]
  result=real(g.DEFAULT_PARALLELISM,host_root);self.assertEqual(result['preparationWorkers'],1);self.assertFalse(result['resourceLimitsIncomplete'])
  files.pop('/sys/fs/cgroup/user.slice/app/cpu.max');result=real(g.DEFAULT_PARALLELISM,files.__getitem__);self.assertEqual(result['preparationWorkers'],0);self.assertTrue(result['resourceLimitsIncomplete'])
 def test_capacity_accounts_for_other_active_output_and_flushes(self):
  import os
  lockpath=self.work/'fixed-selection.lock'
  with f.a.writer_lock(lockpath) as fd:
   coordinator=g.ParallelCoordinator(self.work,fd)
   with patch.object(f.a,'capacity',return_value=300),patch.object(f.a,'reserve',return_value=(None,None)):
    coordinator.reserve('one',self.work/'r1',self.work,time.monotonic()+10,100,100)
    with self.assertRaises(f.a.RefreshError):coordinator.reserve('two',self.work/'r2',self.work,time.monotonic()+10,100,150)
   stream=io.BytesIO();flushed=[]
   class Stream:
    def write(self,block):return stream.write(block)
    def flush(self):flushed.append(True)
   with patch.object(f.a,'capacity',return_value=300):coordinator.write('one',Stream(),b'abc',self.work)
   self.assertEqual(flushed,[True]);self.assertEqual(coordinator.active['one'],97)

# Inherited source fixtures keep previous safety behavior under the global adapter.
if __name__=='__main__':unittest.main()
