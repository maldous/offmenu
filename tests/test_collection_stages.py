"""Stage isolation: synthetic local originals, never live source requests."""
from copy import deepcopy
from pathlib import Path
from unittest.mock import patch
import importlib.util, unittest, json, time
from offmenu.refresh import collection_stages as stages
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('stage_global_fixture',ROOT/'tests/test_global_collection.py');fixture=importlib.util.module_from_spec(spec);spec.loader.exec_module(fixture)
g=fixture.g

class StageTests(unittest.TestCase):
 setUp=fixture.GlobalTests.setUp
 tearDown=fixture.GlobalTests.tearDown
 folder=fixture.GlobalTests.folder
 transport=fixture.GlobalTests.transport
 clean_global=fixture.GlobalTests.clean_global
 def execute(self,stage,**kwargs):
  return g.run_global(self.manifest,self.selected,transport=self.transport,stage=stage,**kwargs)
 def no_prepare(self,*args,**kwargs):raise AssertionError('extraction is not requested')
 def retained(self,extract=True,holds=()):
  body=b'first,second\na,b\n';path=self.root/'retained.csv';path.write_bytes(body)
  contract={'schemaVersion':g.media.SCHEMA,'assetId':'retained:test','expectedSHA256':g.a.sha(body),'expectedBytes':len(body),'expectedMediaTypes':['text/csv'],'permissions':{'read':True,'copy':True,'extract':extract},'holds':list(holds),'parameters':{'encoding':'utf-8','delimiter':',','hasHeader':True}}
  asset={'assetId':'retained:test','sourceKey':None,'bindings':[],'disposition':'retained','retainedOriginal':{'path':str(path),'sha256':g.a.sha(body),'bytes':len(body)},'preparationContract':contract}
  self.manifest['assets'].append(asset);return asset,path,contract
 def test_fetch_never_calls_extractor_or_parser_diagnostics(self):
  asset,path,contract=self.retained()
  with patch.object(g.media,'capabilities',side_effect=AssertionError('parser probe')),patch.object(g.prepdiag,'run_diagnostics',side_effect=AssertionError('parser diagnostic')),patch.object(g.twrecovery,'validate_selected',side_effect=AssertionError('PDF parser')):
   report=self.clean_global(self.execute('fetch',prepare=self.no_prepare))
  rows=g.expand_outcomes(report['assetOutcomeGroups'],len(self.manifest['assets']))
  self.assertEqual(rows[-1],{'custody':'verified-original','stage':'retained','code':None});self.assertEqual(report['preparedBytes'],0);self.assertEqual(report['executionStage'],'fetch')
  self.assertTrue(all(change['preparation'] is None for change in report['changes']));self.assertFalse(list((self.work/'global-preparation').rglob('receipt.json')))
 def test_fetch_extract_disabled_is_verified_collection(self):
  self.retained(False)
  report=self.clean_global(self.execute('fetch',prepare=self.no_prepare));row=g.expand_outcomes(report['assetOutcomeGroups'],len(self.manifest['assets']))[-1]
  self.assertEqual(row['custody'],'verified-original');self.assertEqual(row['stage'],'retained');self.assertIsNone(row['code'])
 def test_fetch_actual_read_hold_remains_enforced(self):
  self.retained(True,['read'])
  report=self.clean_global(self.execute('fetch',prepare=self.no_prepare));row=g.expand_outcomes(report['assetOutcomeGroups'],len(self.manifest['assets']))[-1]
  self.assertNotEqual(row['custody'],'verified-original');self.assertEqual(row['code'],'verification-read-held')
 def test_parse_missing_original_never_creates_intent_or_network(self):
  with patch.object(g.a,'HTTPSFileTransport',side_effect=AssertionError('transport constructed')):
   report=self.clean_global(self.execute('parse',prepare=self.no_prepare))
  self.assertEqual(self.calls,[]);self.assertEqual(report['networkRequests'],0);self.assertEqual(report['networkBytesRead'],0);self.assertEqual(report['observedPeakTransfers'],0)
  self.assertFalse(list((self.work/'private-originals').glob('*/successor-intent.json')))
 def test_parse_reuses_existing_sources_without_touching_intents(self):
  self.execute('fetch',prepare=self.no_prepare);self.calls=[]
  before={p:p.read_bytes() for p in (self.work/'private-originals').glob('*/*')}
  report=self.clean_global(self.execute('parse',prepare=self.no_prepare))
  self.assertEqual(self.calls,[]);self.assertEqual(report['networkRequests'],0);self.assertTrue(all(r['acquisition']['originalDisposition']=='retained-original-no-network' for r in report['changes']))
  self.assertEqual(before,{p:p.read_bytes() for p in (self.work/'private-originals').glob('*/*')})
 def test_parse_runs_existing_authorized_preparation(self):
  asset,path,contract=self.retained();calls=[]
  def prepare(*args):
   calls.append(args[0]);return {'status':'unsupported','errorCode':'parser-unavailable','stages':{'integrity':'passed','media':'passed','extraction':'unsupported'},'actualMediaType':'text/csv','originalSHA256':contract['expectedSHA256'],'originalBytes':contract['expectedBytes'],'outputs':[],'nextStageReady':False},None,0
  report=self.clean_global(self.execute('parse',prepare=prepare));self.assertEqual(calls,['retained:test']);self.assertEqual(report['networkRequests'],0)
 def test_parse_skips_unrequested_extraction_without_read(self):
  asset,path,contract=self.retained(False)
  with patch.object(g.retained_collection,'verify_worker',side_effect=AssertionError('unrequested verification')):
   report=self.clean_global(self.execute('parse',prepare=self.no_prepare))
  row=g.expand_outcomes(report['assetOutcomeGroups'],len(self.manifest['assets']))[-1];self.assertEqual(row['stage'],'retained');self.assertIsNone(row['code'])
 def test_failed_original_stays_failed_and_never_retries(self):
  source=self.selected['sources'][0];folder=self.folder();folder.mkdir(parents=True)
  failed=g.a.canonical({'state':'failed-no-retry'});(folder/'successor-intent.json').write_bytes(failed);(folder/'original.partial').write_bytes(b'old partial')
  report=self.clean_global(self.execute('parse',prepare=self.no_prepare));self.assertEqual(self.calls,[]);self.assertEqual((folder/'successor-intent.json').read_bytes(),failed);self.assertEqual((folder/'original.partial').read_bytes(),b'old partial')
 def test_fetch_worker_uncertainty_preserves_publishable_metadata(self):
  self.retained()
  with patch.object(g.retained_collection,'verify_worker',side_effect=RuntimeError('synthetic worker failure')):
   report=self.clean_global(self.execute('fetch',prepare=self.no_prepare))
  self.assertEqual(report['preparationUncertainGrants'],[]);self.assertEqual(report['preparedUncertainBytes'],0)
  self.assertEqual(g.expand_outcomes(report['assetOutcomeGroups'],len(self.manifest['assets']))[-1]['stage'],'error')
 def test_stage_labels_are_closed_and_historical_report_stays_valid(self):
  report=self.clean_global(self.execute('fetch',prepare=self.no_prepare));report['executionStage']='normalize'
  with self.assertRaises(ValueError):self.clean_global(report)
  report=self.execute(None,prepare=self.no_prepare);self.assertNotIn('executionStage',report);self.clean_global(report)
 def test_parse_report_rejects_network_and_fetch_rejects_preparation(self):
  report=self.execute('fetch',prepare=self.no_prepare);report['executionStage']='parse'
  with self.assertRaises(ValueError):self.clean_global(report)

class PointerTests(unittest.TestCase):
 def test_stage_specific_result_pointers_and_historical_pointer(self):
  from tempfile import TemporaryDirectory
  from types import SimpleNamespace
  with TemporaryDirectory() as tmp:
   runtime=SimpleNamespace(root=Path(tmp));(runtime.root/'collection').mkdir()
   with patch.object(g.a,'OUTPUT',runtime.root):
    old={'globalReport':{'status':'complete'}}
    g.saved_manual_result(runtime,old)
    for stage in ('fetch','parse'):
     value={'globalReport':{'status':'complete','executionStage':stage}}
     g.saved_manual_result(runtime,value,stage=stage)
    self.assertEqual(g.saved_manual_result(runtime)[0],old)
    for stage in ('fetch','parse'):
     self.assertEqual(g.saved_manual_result(runtime,stage=stage)[0]['globalReport']['executionStage'],stage)
    with self.assertRaises(g.a.RefreshError):g.saved_manual_result(runtime,{'globalReport':{'executionStage':'parse'}},stage='fetch')
 def test_labelled_blocked_reports_preserve_stage(self):
  for stage in ('fetch','parse'):
   report={**g.blocked_report('owner-handover-invalid'),'executionStage':stage};self.assertEqual(g.sanitize_report(report),report)

class ArgumentTests(unittest.TestCase):
 def test_owner_default_and_alias_select_fetch(self):self.assertEqual(stages.owner_stage(['--mode','user']),'fetch')
 def test_explicit_stages_and_publish_only(self):
  for stage in ('fetch','parse'):
   args=['--mode','user','--stage',stage,'--publish-only'];self.assertEqual(stages.owner_stage(args),stage);self.assertEqual(stages.base_arguments(args),['--mode','user','--publish-only'])
 def test_runner_does_not_gain_stage_selection(self):
  self.assertIsNone(stages.owner_stage(['--mode','runner']));self.assertFalse(stages.owner_arguments(['--mode','runner','--stage','parse']))
 def test_no_unimplemented_normalize_or_ambiguous_arguments(self):
  for args in (['--mode','user','--stage','normalize'],['--mode','user','--stage','fetch','--stage','parse']):
   with self.assertRaises(g.a.RefreshError):stages.owner_stage(args)
if __name__=='__main__':unittest.main()
