"""All-cardinality synthetic orchestration, no original reads or live requests."""
from copy import deepcopy
from contextlib import ExitStack
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import importlib.util,json,os,tempfile,time,unittest
ROOT=Path(__file__).resolve().parents[1]
def module(name,path):
 spec=importlib.util.spec_from_file_location(name,ROOT/path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
g=module('comprehensive_global','scripts/collect-fixed-global.py');p=module('comprehensive_publisher','scripts/publish-manual-global-result.py');publication_fixture=module('comprehensive_publication_fixture','tests/test_manual_global_publication.py')
class Tests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.selected,cls.manifest=g.prepared_comprehensive_configs();cls.extension,cls.plan=g.retained_collection.config(ROOT)
 def test_owner_successor_profile_user_only_and_restored(self):
  profile={'schemaVersion':'offmenu-owner-successor-profile/1','status':'parent-reviewed-owner-manual','selectionPin':{'path':'docs/new-selection.json','sha256':'a'*64},'manifestPin':{'path':'docs/new-manifest.json','sha256':'b'*64},'ownerRuntimePin':{'path':'docs/new-owner.json','sha256':'c'*64}}
  prior=(g.SELECTION_PIN,g.MANIFEST_PIN,g.OWNER_PIN)
  with patch.object(g,'OWNER_SUCCESSOR_PROFILE_PIN',('docs/profile.json','d'*64)),patch.object(g,'pinned',return_value=profile) as read:
   for args in ([],['--mode','runner']):
    with g.owner_successor_profile(args):self.assertEqual((g.SELECTION_PIN,g.MANIFEST_PIN,g.OWNER_PIN),prior)
   read.assert_not_called()
   with g.owner_successor_profile(['--mode','user']):self.assertEqual(g.SELECTION_PIN,('docs/new-selection.json','a'*64))
   self.assertEqual((g.SELECTION_PIN,g.MANIFEST_PIN,g.OWNER_PIN),prior)
   profile['status']='prepared-for-review-not-active'
   with self.assertRaises(g.a.RefreshError):
    with g.owner_successor_profile(['--mode','user']):pass
 def test_combined_selection_requires_owner_before_source_or_stat_work(self):
  selected,manifest=deepcopy(self.selected),deepcopy(self.manifest)
  selected['knownIntakeSuccessor']['status']=selected['retainedVerification']['status']=manifest['retainedContractExtension']['status']='parent-reviewed-owner-manual'
  with patch.object(g,'stat_original',side_effect=AssertionError('stat forbidden')),self.assertRaisesRegex(g.a.RefreshError,'media-intake-successor-inactive'):g._run_global_locked(manifest,selected)
 def test_exact_inactive_partition_and_immutable_base(self):
  self.assertEqual(len(self.selected['sources']),15);self.assertEqual(self.selected['maximumRequests'],17)
  self.assertEqual(self.manifest['retainedContractExtension']['selectedCount'],988)
  self.assertEqual(len(self.plan['excludedAssetIds']),10);self.assertEqual(self.plan['budget']['maximumOriginalReadBytes'],28437596435)
  self.assertEqual(g.selection_config()['maximumRequests'],10)
  with self.assertRaisesRegex(g.a.RefreshError,'media-intake-successor-inactive'):g.run_global(self.manifest,self.selected)
 def test_source_bound_combination_rejects_rights_paths_and_budget_changes(self):
  selected,manifest=deepcopy(self.selected),deepcopy(self.manifest)
  selected['knownIntakeSuccessor']['status']=selected['retainedVerification']['status']=manifest['retainedContractExtension']['status']='parent-reviewed-owner-manual'
  g.retained_collection.validate_combined(selected,manifest,ROOT)
  asset=next(a for a in manifest['assets'] if a['assetId']==self.plan['proposedAssetIds'][0]);asset['retainedOriginal']['path']='/tmp/arbitrary'
  with self.assertRaises(g.a.RefreshError):g.retained_collection.validate_combined(selected,manifest,ROOT)
 def test_read_reservations_once_and_closed_sanitizer(self):
  r=g.retained_collection.ReadAccounting(self.manifest,self.extension,self.plan)
  for index in r.rows:r.reserve(index);r.finish(index,{'integrityVerified':True})
  summary=r.summary(g.ranges);self.assertEqual(summary['reservedOriginalReadBytes'],28437596435);self.assertEqual(summary['verifiedOriginalPayloadBytes'],28437595507)
  g.retained_collection.sanitize_summary(summary,self.manifest,self.extension,self.plan)
  with self.assertRaises(g.a.RefreshError):r.reserve(next(iter(r.rows)))
  for key,value in [('raw','secret'),('reservedOriginalReadBytes',28437596436),('verifiedOriginalPayloadBytes',True)]:
   with self.subTest(key=key),self.assertRaises(ValueError):g.retained_collection.sanitize_summary({**summary,key:value},self.manifest,self.extension,self.plan)
 def test_full_988_queue_summary_diagnostics_and_publisher_bounds(self):
  selected,manifest=deepcopy(self.selected),deepcopy(self.manifest)
  selected['knownIntakeSuccessor']['status']=selected['retainedVerification']['status']=manifest['retainedContractExtension']['status']='parent-reviewed-owner-manual'
  calls=[];stream_calls=[];mixed=os.environ.get('OFFMENU_TEST_MIXED')=='1'
  def acquire(source,**kwargs):
   meter=kwargs['batch_meter']
   for _ in range(g.intake.maximum_requests(source)):meter.start_request()
   return {'status':'failed','errorCode':'collector-rejected','network':meter.snapshot(),'validation':None,'responseMetadata':None,'responsePolicy':None,'cacheStatus':None,'originalDisposition':None,'privateSaveState':'none','localBodyBytes':0,'receiptPersistence':'written'}
  def prepare(asset_id,contract,path,folder,deadline,remaining):
   calls.append(asset_id)
   status='failed' if mixed and int(contract['expectedSHA256'][:2],16)%3==0 else 'held'
   return {'status':status,'errorCode':'parser-unavailable' if status=='failed' else 'extract-permission-held','stages':{'integrity':'failed' if status=='failed' else 'passed','media':'not-run' if status=='failed' else 'passed','extraction':'held'},'actualMediaType':None if status=='failed' else contract['expectedMediaTypes'][0],'originalSHA256':None if status=='failed' else contract['expectedSHA256'],'originalBytes':None if status=='failed' else contract['expectedBytes'],'outputs':[],'nextStageReady':False,'metrics':{}},None,0
  def stream(contract,path,deadline,slot=None):
   stream_calls.append(contract['assetId'])
   if mixed and int(contract['expectedSHA256'][:2],16)%4==0:raise TimeoutError('synthetic worker uncertainty')
   return {'schemaVersion':g.retained_verification.RESULT_SCHEMA,'assetId':contract['assetId'],'contractSHA256':g.a.sha(g.a.canonical(contract)),'status':'verified-retained','errorCode':'verification-media-unverified','bytesRead':contract['expectedBytes'],'maximumReadBytes':contract['expectedBytes'],'originalSHA256':contract['expectedSHA256'],'originalBytes':contract['expectedBytes'],'actualMediaType':None,'integrityVerified':True,'mediaObserved':False,'nextStageReady':False,'sourceCopied':False,'extractionPerformed':False,'networkRequests':0,'payloadBytesWritten':0}
  resources={'logicalCPUs':8,'affinityCPUs':8,'cgroupCPUCap':8,'effectiveCPUs':8,'memoryAvailableBytes':64*1024**3,'cgroupMemoryHeadroomBytes':64*1024**3,'effectiveMemoryBytes':64*1024**3,'resourceLimitsIncomplete':False,'ioWorkers':8,'preparationWorkers':8,'perHostWorkers':1,'memoryPerPreparationBytes':2560*1024**2,'memoryReserveBytes':2*1024**3}
  with tempfile.TemporaryDirectory() as tmp,ExitStack() as stack:
   root=Path(tmp);(root/'collection').mkdir();(root/'collection/intents').mkdir()
   for key,value in [('OUTPUT',root),('GUARD',0)]:stack.enter_context(patch.object(g.a,key,value))
   for key,value in [('selection_config',selected),('manifest_config',manifest),('effective_resources',resources),('stat_original','stat-observed')]:stack.enter_context(patch.object(g,key,return_value=value))
   stack.enter_context(patch.object(g.time,'sleep',return_value=None));stack.enter_context(patch.object(g.save,'run_selected',side_effect=acquire));stack.enter_context(patch.object(g.media_save,'run_selected',side_effect=acquire));stack.enter_context(patch.object(g.retained_collection,'verify_worker',side_effect=stream));stack.enter_context(patch.object(g.a,'capacity',return_value=10**15))
   stack.enter_context(patch('socket.create_connection',side_effect=AssertionError('live request forbidden')))
   stack.enter_context(patch.object(g.a,'reserve',side_effect=lambda *args,**kwargs:(os.open('/dev/null',os.O_RDONLY),None)))
   stack.enter_context(patch.object(g.a,'release_own_reservation',side_effect=lambda path,fd,identity:os.close(fd)))
   report=g.run_global(manifest,selected,prepare=prepare,owner_runtime=object())
   diagnostic=report['retainedPreparationDiagnostics'];diagnostic['status']='complete'
   for entry,row in zip(g.prepdiag.ENTRIES,diagnostic['items']):
    row.update(status='observed',errorCode=None,access='readable',identityVerified=True,priorDetailVerified=True,bytesHashed=entry['size'])
    if entry['media']=='application/pdf':row['pdf']={'factsFromPriorParser':True,'encryptedFlagObserved':True,'passwordRequired':None,'pageCount':2000,'selectedPageCount':2000,'pagesWithoutText':2000,'pagesWithText':0,'ocrPerformed':False,'imageOnlyEstablished':False,'parser':'poppler-pdftotext'}
    elif entry['media'] in {'application/zip','application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'}:row['archive']={'entries':512,'centralBytes':524288,'largestMemberBytes':33554432,'expandedBytes':134217728,'maximumRatioCeil':200,'reasons':sorted(g.prepdiag.ARCHIVE_REASONS),'relationships':{'count':10000,'internal':10000,'worksheet':10000,'reasons':{k:10000 for k in g.prepdiag.REL_REASONS}}}
   diagnostic['bytesHashed']=sum(x['bytesHashed'] for x in diagnostic['items']);g.prepdiag.sanitize_diagnostics(diagnostic)
   for row in report['retainedTaiwanRecoveryProposals']:
    row.update(status='validated-proposal',errorCode=None)
    row['parser'].update(status='passed',errorCode=None,pdfinfoVersion='2'+'.1'*31,pdftotextVersion='2'+'.1'*31,pdfinfoExitCode=0,pdftotextExitCode=0,pageCount=2000,encrypted=False,allPagesTraversed=True,textBytesExamined=16777216)
    row['proposedDisposition']={'kind':'validated-retained-original-reference/1','relativePath':'collection/private-originals/'+row['sourceContractSHA256']+'/original.partial','sourceContractSHA256':row['sourceContractSHA256'],'sha256':row['retainedSHA256'],'bytes':row['retainedBytes'],'preserveOriginalBytes':True,'preserveFailedIntent':True,'originalAcquiredAt':None,'scope':'private-unchanged-original-structural-validation-only'}
   g.sanitize_report(report)
   self.assertTrue(set(self.plan['proposedMediaAssetIds'])<=set(calls));self.assertEqual(set(stream_calls),set(self.plan['proposedStreamingAssetIds']));self.assertEqual(len(stream_calls),60)
   account=report['retainedOriginalVerification'];self.assertEqual(account['reservedOriginalReadBytes'],28437596435);self.assertLessEqual(account['verifiedOriginalPayloadBytes'],28437595507)
   if not mixed:self.assertEqual(account['verifiedOriginalPayloadBytes'],28437595507)
   else:self.assertTrue(any(row['state']=='uncertain' for row in account['jobOutcomeGroups']))
   self.assertEqual(len(report['reuseOutcomeJoins']),22);self.assertEqual(len(report['retainedPreparationDiagnostics']['items']),22);self.assertEqual(len(report['retainedTaiwanRecoveryProposals']),3)
   self.assertLess(len(g.a.canonical(report)),g.MAX_SUMMARY);self.assertLess(len(report['changes']),100)
   envelope={'schemaVersion':'offmenu-owner-manual-global-result/1','executionContext':'owner-manual-foo','invokingUID':1000,'outputRoot':'/home/test/src/offmenu-data/owner-collection-runtime','handover':{'handoffId':p.HANDOFF,'runtimeConfigSHA256':p.RUNTIME_SHA256,'dispatchHoldSHA256':p.HOLD_SHA256,'executionContext':'owner-manual-foo','runnerResumeRequiresOutcomeImport':True},'historicalRunnerRootAccess':{'/srv/offmenu-refresh/outputs/collection':'inaccessible','/srv/offmenu-refresh/cache':'absent'},'nativeClaimsRoot':p.NATIVE_CLAIMS,'nativeCoverageExhaustive':False,'globalReportSHA256':g.a.sha(g.a.canonical(report)),'globalReport':report}
   with patch.object(p.os,'getuid',return_value=1000),patch.object(p.os,'geteuid',return_value=1000),patch.object(p.pwd,'getpwuid',return_value=SimpleNamespace(pw_dir='/home/test')):
    receipt,files,raw=p.build_payload(envelope,g)
    api=publication_fixture.FakeAPI();first=p.publish_result(envelope,g,api);self.assertTrue(first['verified'],first)
    api.calls=[];again=p.publish_result(envelope,g,api);self.assertEqual(again['status'],'verified-existing');self.assertTrue(all(call[0]=='GET' for call in api.calls))
    published=[row for name,raw in files if '/assets-' in name for row in json.loads(raw)['rows']]
    self.assertEqual(sum('retainedVerification' in row for row in published),988)
   self.assertEqual(receipt['expandedCounts'],{'assets':4753,'countryTypeCells':3237,'statPaths':1937});self.assertLessEqual(len(files),p.MAX_FILES);self.assertLessEqual(sum(len(b) for _,b in files),p.MAX_TOTAL)
   print('COMPREHENSIVE_BOUNDS',json.dumps({'summaryBytes':len(g.a.canonical(report)),'publisherFiles':len(files),'publisherBytes':sum(len(b) for _,b in files),'mediaJobs':len(calls),'streamingJobs':len(stream_calls)}))
if __name__=='__main__':unittest.main()
