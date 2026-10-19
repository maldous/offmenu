"""Actual pinned 988-row proposal, synthetic workers/custody, no live requests."""
from contextlib import ExitStack,contextmanager
from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import hashlib,importlib.util,json,os,tempfile,unittest
ROOT=Path(__file__).resolve().parents[1];HERE=Path(__file__).resolve().parent

def module(name,path):
 s=importlib.util.spec_from_file_location(name,ROOT/path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
g=module('independent_actual988_global','scripts/collect-fixed-global.py')
pub_fixture=module('independent_actual988_publisher_fixture','tests/test_manual_global_publication.py')
small=module('independent_actual988_small','tests/test_collection_stages.py')
mf=module('independent_actual988_media','tests/test_known_asset_intake.py')
RES={'logicalCPUs':8,'affinityCPUs':8,'cgroupCPUCap':8,'effectiveCPUs':8,'memoryAvailableBytes':64*1024**3,'cgroupMemoryHeadroomBytes':64*1024**3,'effectiveMemoryBytes':64*1024**3,'resourceLimitsIncomplete':False,'ioWorkers':8,'preparationWorkers':8,'perHostWorkers':1,'memoryPerPreparationBytes':2560*1024**2,'memoryReserveBytes':2*1024**3}

class Actual988Tests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.selected,cls.manifest=g.prepared_comprehensive_configs();cls.selected['knownIntakeSuccessor']['status']=cls.selected['retainedVerification']['status']=cls.manifest['retainedContractExtension']['status']='parent-reviewed-owner-manual'
  cls.ext,cls.plan=g.retained_collection.config(ROOT);cls.ids=set(cls.plan['proposedAssetIds']);cls.structural=set(cls.plan['proposedStructuralAssetIds']);cls.indices={r['assetId']:i for i,r in enumerate(cls.manifest['assets'])}
  cls.paths=[*ROOT.glob('docs/collection-selections/*comprehensive*.json'),ROOT/'docs/collection-selections/retained-contract-extension-runtime.json',ROOT/'docs/collection-selections/retained-verification-selection-review.json'];cls.pins={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in cls.paths}
 @contextmanager
 def execution(self,stage,uncertain=None):
  selected,manifest=deepcopy(self.selected),deepcopy(self.manifest);calls={'verify':[],'prepare':[],'acquire':[],'fooOpens':0}
  def acquire(source,**kw):
   calls['acquire'].append((source['sourceKey'],kw.get('reuse_only',False)))
   if stage=='parse':self.assertIs(kw.get('reuse_only'),True)
   else:
    for _ in range(g.intake.maximum_requests(source)):kw['batch_meter'].start_request()
   return {'status':'blocked','errorCode':'private-original-conflict','network':kw['batch_meter'].snapshot(),'validation':None,'responseMetadata':None,'responsePolicy':None,'cacheStatus':None,'originalDisposition':None,'privateSaveState':'none','localBodyBytes':0,'receiptPersistence':'written'}
  def prepare(asset,contract,path,folder,deadline,maximum):
   self.assertEqual(stage,'parse');self.assertIs(contract['permissions']['extract'],True);calls['prepare'].append(asset)
   return {'status':'unsupported','errorCode':'parser-unavailable','stages':{'integrity':'passed','media':'passed','extraction':'unsupported'},'actualMediaType':contract['expectedMediaTypes'][0],'originalSHA256':contract['expectedSHA256'],'originalBytes':contract['expectedBytes'],'outputs':[],'nextStageReady':False,'metrics':{}},None,0
  def verify(contract,path,deadline,slot=None):
   self.assertEqual(stage,'fetch');self.assertEqual(contract['permissions'],{'read':True,'copy':False,'extract':False});self.assertEqual(contract['maximumOutputBytes'],0);self.assertFalse(contract['decompressionAllowed']);g.retained_verification.validate_contract(contract);calls['verify'].append(contract['assetId'])
   if contract['assetId']==uncertain:raise TimeoutError('synthetic isolated worker interruption')
   return {'schemaVersion':g.retained_verification.RESULT_SCHEMA,'assetId':contract['assetId'],'contractSHA256':g.a.sha(g.a.canonical(contract)),'status':'verified-retained','errorCode':'verification-media-unverified','bytesRead':contract['expectedBytes'],'maximumReadBytes':contract['expectedBytes'],'originalSHA256':contract['expectedSHA256'],'originalBytes':contract['expectedBytes'],'actualMediaType':None,'integrityVerified':True,'mediaObserved':False,'nextStageReady':False,'sourceCopied':False,'extractionPerformed':False,'networkRequests':0,'payloadBytesWritten':0}
  real_open=os.open
  def no_foo_open(path,*args,**kw):
   if isinstance(path,(str,bytes,os.PathLike)) and os.fsdecode(path).startswith(('/home/user/','/srv/offmenu-refresh/')):calls['fooOpens']+=1;raise AssertionError('Foo read forbidden')
   return real_open(path,*args,**kw)
  with tempfile.TemporaryDirectory(dir=HERE) as directory,ExitStack() as stack:
   root=Path(directory);(root/'collection/intents').mkdir(parents=True)
   for key,value in [('OUTPUT',root),('GUARD',0)]:stack.enter_context(patch.object(g.a,key,value))
   for key,value in [('selection_config',selected),('manifest_config',manifest),('effective_resources',RES),('stat_original','stat-observed')]:stack.enter_context(patch.object(g,key,return_value=value))
   stack.enter_context(patch.object(g.time,'sleep',return_value=None));stack.enter_context(patch.object(g.a,'capacity',return_value=10**15));stack.enter_context(patch.object(g.a,'reserve',side_effect=lambda *a,**kw:(os.open('/dev/null',os.O_RDONLY),None)));stack.enter_context(patch.object(g.a,'release_own_reservation',side_effect=lambda path,fd,identity:os.close(fd)))
   for handler in (g.save,g.media_save):stack.enter_context(patch.object(handler,'run_selected',side_effect=acquire))
   stack.enter_context(patch.object(g.retained_collection,'verify_worker',side_effect=verify))
   for obj,name in [(g.taiwan,'run_diagnostics'),(g.prepdiag,'run_diagnostics'),(g.twrecovery,'validate_selected')]:stack.enter_context(patch.object(obj,name,side_effect=AssertionError('stage diagnostic forbidden')))
   stack.enter_context(patch.object(g.media,'capabilities',return_value=g.runtime_capabilities('fetch')));stack.enter_context(patch('socket.create_connection',side_effect=AssertionError('live network forbidden')));stack.enter_context(patch.object(os,'open',side_effect=no_foo_open))
   report=g.run_global(manifest,selected,prepare=prepare,owner_runtime=object(),stage=stage);g.sanitize_report(report)
   yield report,calls,root
   self.assertEqual(calls['fooOpens'],0);self.assertEqual(self.pins,{str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in self.paths})
 def test_fetch988_verified_retained_no_extraction_exact_budget(self):
  with self.execution('fetch') as (r,c,root):
   self.assertEqual(set(c['verify'])&self.ids,self.ids);self.assertEqual(len([k for k in c['verify'] if k in self.ids]),988);self.assertEqual(c['prepare'],[]);self.assertFalse(set(c['verify'])&set(self.plan['excludedAssetIds']))
   outcomes=g.expand_outcomes(r['assetOutcomeGroups'],len(self.manifest['assets']))
   for key in self.ids:self.assertEqual(outcomes[self.indices[key]],{'custody':'verified-original','stage':'retained','code':None},key)
   a=r['retainedOriginalVerification'];self.assertEqual((a['executionStage'],a['executionSelectedJobs'],a['skippedForStage']),('fetch',988,0));self.assertEqual(a['reservedOriginalReadBytes'],28437596435);self.assertEqual(a['verifiedOriginalPayloadBytes'],28437595507);self.assertEqual(a['heldUnselected'],10)
   self.assertEqual(r['preparedBytes'],0);self.assertEqual(r['preparationUncertainGrants'],[]);self.assertTrue(all(x['preparation'] is None for x in r['changes']));self.assertFalse(list((root/'collection/global-preparation').rglob('receipt.json')));self.assertEqual(r['networkRequests'],17);self.assertEqual(len(c['acquire']),15);self.assertTrue(all(not flag for _,flag in c['acquire']));self.publish_and_reload(r,root,988)
 def test_fetch_uncertain_stream_worker_remains_publishable(self):
  target=self.plan['proposedStreamingAssetIds'][0]
  with self.execution('fetch',target) as (r,c,root):
   self.assertEqual(len(set(c['verify'])&self.ids),988);self.assertEqual(r['preparationUncertainGrants'],[]);self.assertEqual(r['preparedUncertainBytes'],0);self.assertEqual(r['retainedOriginalVerification']['reservedOriginalReadBytes'],28437596435)
   observations=g.retained_collection.observations(r['retainedOriginalVerification']);self.assertEqual(observations[self.indices[target]],'uncertain');self.assertEqual(sum(s=='completed-verified' for s in observations.values()),987);self.publish_and_reload(r,root,988)
 def test_parse_only10_retained_structural_rows_zero_downloads(self):
  with self.execution('parse') as (r,c,root):
   self.assertEqual(c['verify'],[]);self.assertEqual(set(c['prepare'])&self.ids,self.structural);self.assertEqual(len([k for k in c['prepare'] if k in self.ids]),10);self.assertFalse(set(c['prepare'])&set(self.plan['excludedAssetIds']))
   self.assertEqual(r['networkRequests'],0);self.assertEqual(r['networkBytesRead'],0);self.assertEqual(r['observedPeakTransfers'],0);self.assertEqual(len(c['acquire']),15);self.assertTrue(all(flag for _,flag in c['acquire']))
   a=r['retainedOriginalVerification'];self.assertEqual((a['executionStage'],a['executionSelectedJobs'],a['skippedForStage']),('parse',10,978));self.assertEqual(a['reservedOriginalReadBytes'],735611);self.assertEqual(a['verifiedOriginalPayloadBytes'],735601)
   outcomes=g.expand_outcomes(r['assetOutcomeGroups'],len(self.manifest['assets']))
   for key in self.ids-self.structural:self.assertNotEqual(outcomes[self.indices[key]]['code'],'extract-permission-held',key)
   self.publish_and_reload(r,root,10)
 def publish_and_reload(self,r,root,expected):
  with g.owner_successor_profile(['--mode','user']):p=g.publisher_module()
  self.assertEqual(p.HANDOFF,'owner-local-comprehensive-20261018-002')
  env={'schemaVersion':'offmenu-owner-manual-global-result/1','executionContext':'owner-manual-foo','invokingUID':1000,'outputRoot':'/home/test/src/offmenu-data/owner-collection-runtime','handover':{'handoffId':p.HANDOFF,'runtimeConfigSHA256':p.RUNTIME_SHA256,'dispatchHoldSHA256':p.HOLD_SHA256,'executionContext':'owner-manual-foo','runnerResumeRequiresOutcomeImport':True},'historicalRunnerRootAccess':{'/srv/offmenu-refresh/outputs/collection':'inaccessible','/srv/offmenu-refresh/cache':'absent'},'nativeClaimsRoot':p.NATIVE_CLAIMS,'nativeCoverageExhaustive':False,'globalReportSHA256':g.a.sha(g.a.canonical(r)),'globalReport':r}
  stage=r['executionStage'];runtime=SimpleNamespace(root=root);saved,path,digest=g.saved_manual_result(runtime,env,stage=stage);self.assertEqual(g.saved_manual_result(runtime,stage=stage),(saved,path,digest));self.assertTrue((root/'collection/manual-results'/('latest-'+stage+'.json')).is_file())
  with patch.object(p.os,'getuid',return_value=1000),patch.object(p.os,'geteuid',return_value=1000),patch.object(p.pwd,'getpwuid',return_value=SimpleNamespace(pw_dir='/home/test')):
   receipt,files,raw=p.build_payload(saved,g);self.assertEqual(receipt['executionStage'],stage);self.assertFalse(receipt['rawSourceBodiesPublished']);self.assertFalse(receipt['checkpointBodiesPublished']);self.assertEqual(receipt['expandedCounts'],{'assets':4753,'countryTypeCells':3237,'statPaths':1937})
   rows=[row for name,data in files if '/assets-' in name for row in json.loads(data)['rows']];self.assertEqual(sum('retainedVerification' in row for row in rows),expected);self.assertTrue(all(row.get('retainedVerification',{}).get('parserReadinessInferred') in (None,False) for row in rows))
   api=pub_fixture.FakeAPI();first=p.publish_result(saved,g,api);self.assertTrue(first['verified'],first);api.calls=[];again=p.publish_result(saved,g,api);self.assertEqual(again['status'],'verified-existing');self.assertTrue(all(call[0]=='GET' for call in api.calls))
  print('ACTUAL988_STAGE',json.dumps({'stage':stage,'summaryBytes':len(g.a.canonical(r)),'payloadFiles':len(files),'payloadBytes':sum(len(b) for _,b in files),'retainedObservations':expected,'reservedBytes':r['retainedOriginalVerification']['reservedOriginalReadBytes']}))
 def test_parse_scope_rejects_verification_only_observation_and_reservation(self):
  account=g.retained_collection.ReadAccounting(self.manifest,self.ext,self.plan,stage='parse')
  index=self.indices[next(k for k in self.plan['proposedMediaAssetIds'] if k not in self.structural)]
  with self.assertRaises(g.a.RefreshError):account.reserve(index)
  bad=account.summary(g.ranges);bad['jobOutcomeGroups']=[{'state':'attempted','assetIndices':[index]}];bad['reservedOriginalReadBytes']=account.rows[index]['retainedOriginal']['bytes']+1
  with self.assertRaises(ValueError):g.retained_collection.sanitize_summary(bad,self.manifest,self.ext,self.plan,stage='parse')
 def test_saved_stage_pointers_independent_and_legacy_readable(self):
  with tempfile.TemporaryDirectory(dir=HERE) as path:
   root=Path(path);(root/'collection').mkdir();runtime=SimpleNamespace(root=root);env={stage:{'globalReport':{} if stage is None else {'executionStage':stage}} for stage in (None,'fetch','parse')};expected={stage:g.saved_manual_result(runtime,value,stage=stage) for stage,value in env.items()}
   for stage in expected:self.assertEqual(g.saved_manual_result(runtime,stage=stage),expected[stage])
   self.assertEqual({p.name for p in (root/'collection/manual-results').glob('latest*.json')},{'latest.json','latest-fetch.json','latest-parse.json'})
   with self.assertRaises(g.a.RefreshError):g.saved_manual_result(runtime,env['fetch'],stage='parse')
 def test_exact002_profile_contract_documents_unchanged(self):
  with g.owner_successor_profile(['--mode','user']):
   selected=g.pinned(g.SELECTION_PIN);manifest=g.pinned(g.MANIFEST_PIN);self.assertEqual(selected,self.selected);self.assertEqual(manifest,self.manifest);self.assertEqual(g.owner_config(selected)['handoffId'],'owner-local-comprehensive-20261018-002')
  self.assertEqual(self.pins,{str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in self.paths})

class SaverGuards(unittest.TestCase):
 def test_legacy_failed_intents_partials_preserved(self):
  t=small.StageTests();t.setUp()
  try:t.test_failed_original_stays_failed_and_never_retries()
  finally:t.tearDown()
 def test_legacy_parse_reuses_without_intent_changes(self):
  t=small.StageTests();t.setUp()
  try:t.test_parse_reuses_existing_sources_without_touching_intents()
  finally:t.tearDown()
 def test_historical_unstaged_report_accepted(self):
  t=small.StageTests();t.setUp()
  try:t.test_stage_labels_are_closed_and_historical_report_stays_valid()
  finally:t.tearDown()
 def test_five_media_reuse_only_blocks_download_and_preserves_failure(self):
  t=mf.IntakeTests();t.setUp()
  try:
   for i in range(5):
    r=t.run_source(i,reuse_only=True);self.assertEqual(r['network']['requests'],0);self.assertEqual(r['errorCode'],'private-original-conflict');self.assertFalse((t.folder(i)/'successor-intent.json').exists())
    failed=t.folder(i)/'successor-intent.json';partial=t.folder(i)/'original.partial';failed.write_bytes(b'{"state":"failed-no-retry"}\n');partial.write_bytes(b'synthetic partial');before=(failed.read_bytes(),partial.read_bytes());r=t.run_source(i,reuse_only=True);self.assertEqual(r['network']['requests'],0);self.assertEqual(r['errorCode'],'private-save-intent-uncertain');self.assertEqual((failed.read_bytes(),partial.read_bytes()),before)
   self.assertEqual(t.calls,[])
  finally:t.tearDown()
 def test_five_media_reuse_only_accepts_existing_synthetic_custody(self):
  t=mf.IntakeTests();t.setUp()
  try:
   for i in range(5):
    first=t.run_source(i);self.assertEqual(first['status'],'verified-private-original',first);before={p.name:p.read_bytes() for p in t.folder(i).iterdir() if p.is_file()};second=t.run_source(i,reuse_only=True,transport=lambda *a,**k:(_ for _ in ()).throw(AssertionError('download forbidden')));self.assertEqual(second['network']['requests'],0);self.assertEqual(second['originalDisposition'],'retained-original-no-network');self.assertEqual(before,{p.name:p.read_bytes() for p in t.folder(i).iterdir() if p.is_file()})
  finally:t.tearDown()
if __name__=='__main__':unittest.main()
