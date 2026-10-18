"""Global orchestration fixtures. No source requests or original data."""
from copy import deepcopy
import importlib.util,io,json,tempfile,time,unittest
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
def module(name,file):
 spec=importlib.util.spec_from_file_location(name,ROOT/file);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
g=module('global_fixture','scripts/collect-fixed-global.py')
f=module('global_save_fixture','tests/test_fixed_source_private_save.py')
class GlobalTests(unittest.TestCase):
 tearDown=f.SaveTests.tearDown
 folder=f.SaveTests.folder
 transport=f.SaveTests.transport
 def setUp(self):
  f.SaveTests.setUp(self)
  for key,value in [('a',f.a),('b',f.m),('save',f.save)]:self.stack.enter_context(patch.object(g,key,value))
  self.stack.enter_context(patch.object(g.time,'sleep',return_value=None))
  self.selected['schemaVersion']='offmenu-global-source-selection/1';self.selected['preparation']=[]
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
   if calls==2:kwargs['batch_meter']['requests']+=1;raise RuntimeError('private-error')
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
   count=source['expectedBytes'] or 4096;kwargs['batch_meter']['requests']+=1;kwargs['batch_meter']['bodyBytesRead']+=count
   return {'status':'verified-private-original','errorCode':None,'network':{'requests':1,'bodyBytesRead':count},'responseMetadata':f.a.response_metadata(200,source['expectedResponse'],request_url=source['url']),
    'cacheStatus':None,'validation':{'bytes':count,'sha256':'a'*64,'originalAcquiredAt':'2026-10-18T21:00:00+00:00'},'receiptPersistence':'written','responsePolicy':f.save.policy_facts([('Cache-Control','private,no-store')]),'originalDisposition':'saved-original','privateSaveState':'saved-original','localBodyBytes':count}
  def prepare(asset_id,contract,path,folder,deadline,remaining):
   result={'status':'unsupported','errorCode':'parser-unavailable','stages':{'integrity':'passed','media':'passed','extraction':'unsupported'},'actualMediaType':contract['expectedMediaTypes'][0],
    'originalSHA256':contract['expectedSHA256'],'originalBytes':contract['expectedBytes'],'outputs':[],'nextStageReady':False,'metrics':{'pageCount':2000,'selectedPageCount':2000,'selectedExtentComplete':True}}
   return result,None,0
  with patch.object(f.save,'run_selected',side_effect=acquire),patch.object(g,'stat_original',return_value='stat-observed'):
   report=g.run_global(actual_manifest,actual_selected,transport=lambda *a:None,prepare=prepare)
  report=self.clean_global(report);self.assertEqual(report['assetCount'],len(actual_manifest['assets']));self.assertEqual(report['networkRequests'],10);self.assertEqual(report['statPathCount'],1937)
  self.assertGreaterEqual(len(report['changes']),40);self.assertLess(len(f.a.canonical(report)),g.MAX_SUMMARY)
  dispatch=module('global_actual_projection','scripts/dispatch-foo-job.py');evidence=dispatch.safe_evidence(f.a.canonical(report));self.assertEqual(evidence.get('globalCollection'),report,evidence)
 def test_projection_fallback_preserves_completed_sources_and_meter(self):
  report=self.execute();progress={'meter':{'requests':report['networkRequests'],'bodyBytesRead':report['networkBytesRead']},'changes':report['changes']}
  failure=g.projection_failure(self.selected,progress);clean=self.clean_global(failure);self.assertEqual(clean['networkRequests'],5);self.assertEqual(len(clean['completedSources']),5)
 def test_dispatcher_keeps_three_field_request_and_global_report_bound(self):
  dispatch=module('global_dispatch_fixture','scripts/dispatch-foo-job.py');request={'schemaVersion':1,'jobId':'global-test-20261019','profile':'global-collection'}
  self.assertEqual(dispatch.parse_request(f.a.canonical(request)),request);self.assertEqual(dispatch.report_limit(request),128*1024)
  with self.assertRaises(dispatch.JobError):dispatch.parse_request(f.a.canonical({**request,'url':'https://example.org'}))
  self.assertEqual([row[0] for row in dispatch.profile_steps('global-collection',ROOT)],['readiness','global-collection-tests','media-preparation-tests','global-collection'])
# Inherited source fixtures keep previous safety behavior under the global adapter.
if __name__=='__main__':unittest.main()
