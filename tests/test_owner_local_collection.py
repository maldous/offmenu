"""Offline normal-user handover tests; no original network requests."""
from copy import deepcopy
from types import SimpleNamespace
from pathlib import Path
import importlib.util,json,os,time,unittest,io,subprocess,sys
from contextlib import redirect_stdout
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
def module(name,path):
 spec=importlib.util.spec_from_file_location(name,ROOT/path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
gt=module('owner_global_fixtures','tests/test_global_collection.py');g=gt.g;f=gt.f
class OwnerTests(unittest.TestCase):
 def setUp(self):
  gt.GlobalTests.setUp(self)
  # These are immutable001/002 regression fixtures; comprehensive amendment
  # activation and its additional preflight are tested separately.
  gate=patch.object(g.fetch_reconciliation,'configuration',return_value=None);gate.start();self.addCleanup(gate.stop)
 tearDown=gt.GlobalTests.tearDown
 transport=gt.GlobalTests.transport
 folder=gt.GlobalTests.folder
 clean_global=gt.GlobalTests.clean_global
 def runtime(self):
  home=self.root/'home';(home/'src/offmenu-data').mkdir(parents=True,exist_ok=True)
  config={'nativeClaimsRoot':str(self.root/'native/claims'),'sourceKeys':[s['sourceKey'] for s in self.selected['sources']],
   'handoffId':'owner-local-global-20261018-001','dispatchHoldPin':{'sha256':'a'*64}}
  Path(config['nativeClaimsRoot']).mkdir(parents=True,exist_ok=True)
  with patch.object(g.pwd,'getpwuid',return_value=SimpleNamespace(pw_dir=str(home))):runtime=g.OwnerRuntime(config,self.selected)
  runtime.runner_work=self.work;runtime.runner_cache=self.root/'runner-cache'
  return runtime
 def run_owner(self,runtime):
  with patch.object(f.a,'OUTPUT',runtime.root):return g.run_global(self.manifest,self.selected,transport=self.transport,owner_runtime=runtime)
 def test_exact_pinned_handover_and_all_ten_contracts(self):
  m=module('real_owner_global','scripts/collect-fixed-global.py');s=m.selection_config();c=m.owner_config(s)
  self.assertEqual(len(c['sourceKeys']),10);self.assertEqual(len(s['privateOriginalDownload']['predecessors']),5)
 def test_local_uid_additive_successor_and_stable_zero_get_resume(self):
  runtime=self.runtime();first=self.run_owner(runtime);self.assertEqual(first['networkRequests'],5)
  for source,prior in zip(self.selected['sources'],self.selected['privateOriginalDownload']['predecessors']):
   folder=runtime.root/'collection/private-originals'/f.a.sha(f.a.canonical(source));intent=json.loads((folder/'successor-intent.json').read_text())
   self.assertEqual(intent['owner'],os.getuid());self.assertEqual(intent['predecessor'],prior);self.assertEqual(intent['ownerHandover']['handoffId'],runtime.config['handoffId'])
  self.assertEqual({p.name:p.read_bytes() for p in (self.work/'intents').iterdir()},self.before)
  self.calls=[];second=self.run_owner(runtime);self.assertEqual(second['networkRequests'],0);self.assertFalse(self.calls)
  self.assertEqual(self.runtime().root,runtime.root)
 def test_inaccessible_runner_exact_handover_still_checks_native(self):
  runtime=self.runtime();runtime.runner_work=self.root/'absent-runner';first=self.run_owner(runtime)
  self.assertEqual(first['networkRequests'],5);self.assertEqual(len(first['changes']),5)
 def test_native_exact_filename_without_url_blocks_only_affected(self):
  runtime=self.runtime();source=self.selected['sources'][1]
  (runtime.native/(f.a.sha(source['url'].encode())+'.json')).write_text('{"owner":4,"state":"active"}')
  report=self.run_owner(runtime);self.assertEqual(report['networkRequests'],4)
  self.assertEqual(report['changes'][1]['acquisition']['errorCode'],'known-exact-source-alternate-cache')
 def test_native_claim_alias_in_key_blocks(self):
  runtime=self.runtime();source=self.selected['sources'][0]
  (runtime.native/'other.json').write_text(json.dumps({source['aliases'][0]:{'state':'partial'}}))
  self.assertEqual(self.run_owner(runtime)['networkRequests'],4)
 def test_native_inaccessible_keeps_complete_zero_get_report(self):
  runtime=self.runtime();runtime.native=self.root/'absent-native'
  report=self.run_owner(runtime);self.assertEqual(report['networkRequests'],0);self.assertEqual(len(report['changes']),5)
  self.assertTrue(all(c['acquisition']['errorCode']=='owner-native-claims-unavailable' for c in report['changes']))
 def test_local_orphan_partial_blocks_source(self):
  runtime=self.runtime();source=self.selected['sources'][0];cache=runtime.root/'collection/source-cache/requests'/f.a.sha(f.a.canonical(f.a.source_spec(source).identity()));cache.mkdir(parents=True);(cache/'body.partial').write_bytes(b'partial')
  self.assertEqual(self.run_owner(runtime)['networkRequests'],4)
 def test_readable_runner_changed_predecessor_blocks_source(self):
  runtime=self.runtime();source=self.selected['sources'][0];claim=self.work/'intents'/(f.a.sha(source['url'].encode())+'.json');claim.write_text('{"state":"active"}')
  self.assertEqual(self.run_owner(runtime)['networkRequests'],4)
 def test_no_root_or_symlink_runtime(self):
  with patch.object(g.os,'getuid',return_value=0),self.assertRaises(f.a.RefreshError):self.runtime()
  runtime=self.runtime();parent=runtime.root.parent;runtime.root.rename(parent/'old-runtime');runtime.root.symlink_to(parent/'old-runtime')
  with self.assertRaises(f.a.RefreshError):self.runtime()
 def test_manual_envelope_separate_no_actions_identity(self):
  runtime=self.runtime();report=self.run_owner(runtime)
  with patch.object(g,'manifest_config',return_value=self.manifest),patch.object(g,'selection_config',return_value=self.selected):g.sanitize_report(report)
  value=g.manual_envelope(report,runtime);self.assertEqual(value['globalReportSHA256'],f.a.sha(f.a.canonical(report)));self.assertNotIn('GITHUB',json.dumps(value));self.assertEqual(value['invokingUID'],os.getuid())
 def test_actual_normal_user_creation_has_private_stable_directories(self):
  runtime=self.runtime()
  for p in (runtime.root,runtime.root/'collection',runtime.root/'collection/intents',runtime.root/'tmp'):self.assertEqual(p.stat().st_mode&0o777,0o700)
 def test_publish_failure_keeps_durable_envelope_and_publish_only_never_runs(self):
  runtime=self.runtime();report=self.run_owner(runtime)
  with patch.object(g,'selection_config',return_value=self.selected),patch.object(g,'manifest_config',return_value=self.manifest),patch.object(g,'owner_config',return_value=runtime.config),patch.object(g,'OwnerRuntime',return_value=runtime),patch.object(g.b,'source_conflicts',return_value=[]),patch.object(g,'run_global',return_value=report) as run,patch.object(g,'verify_manual_handover',return_value=None),patch.object(g,'publish_manual_result',side_effect=RuntimeError('private-publish-error')),redirect_stdout(io.StringIO()) as out:
   code=g.main(['--mode','user']);self.assertEqual(code,3);self.assertEqual(run.call_args.kwargs['owner_runtime'],runtime)
  result=json.loads(out.getvalue());self.assertNotIn('private-publish-error',out.getvalue());self.assertTrue(Path(result['resultPath']).exists())
  with patch.object(g,'selection_config',return_value=self.selected),patch.object(g,'owner_config',return_value=runtime.config),patch.object(g,'OwnerRuntime',return_value=runtime),patch.object(g,'run_global',side_effect=AssertionError('GET path')),patch.object(g,'publish_manual_result',return_value={'status':'verified-existing'}) as publish,redirect_stdout(io.StringIO()):
   self.assertEqual(g.main(['--mode','user','--publish-only']),0);self.assertEqual(publish.call_args.args[0]['globalReport'],report)
 def test_explicit_runner_mode_matches_default_and_does_not_publish(self):
  report=self.run_owner(self.runtime())
  with patch.object(g,'selection_config',return_value=self.selected),patch.object(g,'manifest_config',return_value=self.manifest),patch.object(g.b,'source_conflicts',return_value=[]),patch.object(g,'run_global',return_value=report) as run,patch.object(g,'publish_manual_result',side_effect=AssertionError('manual publication')),redirect_stdout(io.StringIO()) as out:
   g.main(['--mode','runner']);one=json.loads(out.getvalue());self.assertIsNone(run.call_args.kwargs['owner_runtime'])
  self.assertEqual(one,report)
 def test_manual_saved_pointer_refuses_path_escape(self):
  runtime=self.runtime();folder=runtime.root/'collection/manual-results';folder.mkdir();(folder/'latest.json').write_text(json.dumps({'schemaVersion':'offmenu-manual-result-pointer/1','resultFilename':'../../private','resultSHA256':'a'*64}))
  with self.assertRaises(f.a.RefreshError):g.saved_manual_result(runtime)
 def test_historical_not_directory_or_symlink_blocks(self):
  runtime=self.runtime();p=self.root/'bad-history';p.write_bytes(b'x');runtime.runner_cache=p
  self.assertEqual(self.run_owner(runtime)['networkRequests'],0)
  p.unlink();p.symlink_to(self.root/'missing');self.assertEqual(runtime.access_state(p),'unsafe-path');self.assertEqual(self.run_owner(runtime)['networkRequests'],0)
 def test_historical_orphan_partial_blocks_without_claim(self):
  runtime=self.runtime();source=self.selected['sources'][0];historical=self.root/'other-runner';historical.mkdir();runtime.runner_work=historical
  # Model a fresh source whose historical cache contains an unbound partial.
  self.selected['privateOriginalDownload']['predecessors']=[];self.selected['privateOriginalDownload']['freshSources']=[s['sourceKey'] for s in self.selected['sources']]
  cache=historical/'source-cache/requests'/f.a.sha(f.a.canonical(f.a.source_spec(source).identity()));cache.mkdir(parents=True);(cache/'body.partial').write_bytes(b'partial')
  report=self.run_owner(runtime);self.assertEqual(report['networkRequests'],4);self.assertEqual(report['changes'][0]['acquisition']['errorCode'],'source-claim-uncertain')
 def test_actual_4753_inventory_manual_publication_roundtrip(self):
  captured=[];real=g.run_global
  def capture(*args,**kwargs):
   value=real(*args,**kwargs);captured.append(value);return value
  with patch.object(g,'run_global',side_effect=capture):gt.GlobalTests.test_full_actual_cardinality_complete_projection(self)
  report=captured[0];pub=module('actual_manual_publisher','scripts/publish-manual-global-result.py');tests=module('actual_manual_pub_fixture','tests/test_manual_global_publication.py')
  root=Path(g.pwd.getpwuid(os.getuid()).pw_dir)/'src/offmenu-data/owner-collection-runtime'
  runtime=SimpleNamespace(uid=os.getuid(),root=root,native=Path(pub.NATIVE_CLAIMS),access={'/srv/offmenu-refresh/outputs/collection':'inaccessible','/srv/offmenu-refresh/cache':'inaccessible'},provenance=lambda:{'handoffId':pub.HANDOFF,'runtimeConfigSHA256':pub.RUNTIME_SHA256,'dispatchHoldSHA256':pub.HOLD_SHA256,'executionContext':'owner-manual-foo','runnerResumeRequiresOutcomeImport':True})
  envelope=g.manual_envelope(report,runtime)
  with patch.object(g,'manifest_config',return_value=self.manifest),patch.object(g,'selection_config',return_value=self.selected):
   receipt,files,raw=pub.build_payload(envelope,g);api=tests.FakeAPI();result=pub.publish_result(envelope,g,api);self.assertTrue(result['verified'],result)
   api.calls=[];again=pub.publish_result(envelope,g,api);self.assertEqual(again['status'],'verified-existing');self.assertTrue(all(c[0]=='GET' for c in api.calls))
  self.assertEqual(receipt['expandedCounts'],{'assets':4753,'countryTypeCells':3237,'statPaths':1937});self.assertTrue(all(len(b)<=pub.MAX_CHUNK for _,b in files))
 def test_changed_current_handover_blocks_before_global_and_saves_reason(self):
  runtime=self.runtime()
  with patch.object(g,'selection_config',return_value=self.selected),patch.object(g,'manifest_config',return_value=self.manifest),patch.object(g,'owner_config',return_value=runtime.config),patch.object(g,'OwnerRuntime',return_value=runtime),patch.object(g,'verify_manual_handover',side_effect=ValueError('revoked')),patch.object(g,'run_global',side_effect=AssertionError('acquisition')),patch.object(g,'publish_manual_result',return_value={'status':'published-and-verified'}),redirect_stdout(io.StringIO()):
   self.assertEqual(g.main(['--mode','user']),2)
  envelope,_,_=g.saved_manual_result(runtime,stage='fetch');self.assertEqual(envelope['globalReport']['executionStage'],'fetch');self.assertEqual(envelope['globalReport']['errorCode'],'owner-handover-invalid');self.assertEqual(envelope['globalReport']['networkRequests'],0)
 def test_github_tokens_absent_in_worker_child_and_restored_on_exception(self):
  with patch.dict(os.environ,{'GH_TOKEN':'synthetic-gh','GITHUB_TOKEN':'synthetic-github'}):
   with self.assertRaises(RuntimeError):
    with g.without_github_credentials():
     self.assertNotIn('GH_TOKEN',os.environ);self.assertNotIn('GITHUB_TOKEN',os.environ)
     subprocess.run([sys.executable,'-I','-c',"import os; assert 'GH_TOKEN' not in os.environ and 'GITHUB_TOKEN' not in os.environ"],check=True)
     raise RuntimeError('synthetic')
   self.assertEqual(os.environ['GH_TOKEN'],'synthetic-gh');self.assertEqual(os.environ['GITHUB_TOKEN'],'synthetic-github')
 def test_main_auth_only_preflight_and_publication_including_publish_only(self):
  runtime=self.runtime();report=self.run_owner(runtime);observed=[]
  def auth(*args):
   self.assertEqual(os.environ.get('GITHUB_TOKEN'),'synthetic-github');observed.append('auth');return {'status':'verified-existing'}
  def collect(*args,**kwargs):
   self.assertNotIn('GH_TOKEN',os.environ);self.assertNotIn('GITHUB_TOKEN',os.environ);observed.append('collect');return report
  with patch.dict(os.environ,{'GITHUB_TOKEN':'synthetic-github'}),patch.object(g,'selection_config',return_value=self.selected),patch.object(g,'manifest_config',return_value=self.manifest),patch.object(g,'owner_config',return_value=runtime.config),patch.object(g,'OwnerRuntime',return_value=runtime),patch.object(g.b,'source_conflicts',return_value=[]),patch.object(g,'run_global',side_effect=collect),patch.object(g,'verify_manual_handover',side_effect=auth),patch.object(g,'publish_manual_result',side_effect=auth),redirect_stdout(io.StringIO()) as out:
   g.main(['--mode','user']);self.assertEqual(observed,['auth','collect','auth'])
   g.main(['--mode','user','--publish-only']);self.assertEqual(observed,['auth','collect','auth','auth'])
   self.assertNotIn('synthetic-github',out.getvalue())
if __name__=='__main__':unittest.main()
