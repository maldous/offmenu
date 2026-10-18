"""Synthetic successor lineage and active-hold compatibility; no live requests."""
from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import importlib.util,json,unittest
ROOT=Path(__file__).resolve().parents[1]
def module(name,path):
 spec=importlib.util.spec_from_file_location(name,ROOT/path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
owner=module('successor_owner_fixtures','tests/test_owner_local_collection.py');g=owner.g
pubtests=module('successor_pub_fixtures','tests/test_manual_global_publication.py')
class ExactLineageTests(unittest.TestCase):
 def setUp(self):
  self.real=module('successor_real_global','scripts/collect-fixed-global.py');self.lineage=self.real.pinned(self.real.OWNER_REUSE_PIN)
  self.sources={s['sourceKey']:s for s in self.real.selection_config()['sources']}
  self.runtime=self.real.OwnerRuntime.__new__(self.real.OwnerRuntime)
  self.runtime.config={'handoffId':self.lineage['targetHandoffId'],'predecessorOwnerRuntimePin':self.lineage['predecessorOwnerRuntimePin'],'dispatchHoldPin':{'sha256':'d'*64}}
  self.runtime.uid=self.lineage['ownerUID'];self.runtime.root=Path(self.lineage['outputRoot'])
 def test_all_seven_exact_pinned_predecessors_accept_without_mutation(self):
  self.assertEqual(len(self.lineage['rows']),7);self.assertEqual(len(self.lineage['failedTaiwanSourceKeys']),3)
  for row in self.lineage['rows']:
   source=self.sources[row['sourceKey']];intent=deepcopy(row['expectedIntent']);before=self.real.a.canonical(intent)
   self.assertEqual(self.real.a.sha(before),row['expectedIntentSHA256'])
   self.assertEqual(self.real.a.sha(self.real.a.canonical(row['expectedProvenance'])),intent['provenanceSHA256'])
   self.assertEqual(self.runtime.reuse_provenance(source,intent),self.lineage['predecessorHandover']);self.assertEqual(self.real.a.canonical(intent),before)
 def test_changed_intent_state_identity_provenance_and_unknown_source_rejected(self):
  row=self.lineage['rows'][0];source=self.sources[row['sourceKey']]
  for key,value in [('state','failed'),('sha256','0'*64),('bytes',1),('owner',999),('provenanceSHA256','1'*64),('unexpected',True)]:
   bad={**deepcopy(row['expectedIntent']),key:value}
   with self.subTest(key=key),self.assertRaises(self.real.a.RefreshError):self.runtime.reuse_provenance(source,bad)
  source=deepcopy(source);source['url']+='&unreviewed=1'
  with self.assertRaises(self.real.a.RefreshError):self.runtime.reuse_provenance(source,row['expectedIntent'])
 def test_wrong_runtime_uid_root_and_predecessor_pin_rejected(self):
  row=self.lineage['rows'][0];source=self.sources[row['sourceKey']]
  for key,value in [('uid',999),('root',Path('/tmp/other'))]:
   with patch.object(self.runtime,key,value),self.assertRaises(self.real.a.RefreshError):self.runtime.reuse_provenance(source,row['expectedIntent'])
  for key,value in [('handoffId','unreviewed'),('predecessorOwnerRuntimePin',{'sha256':'0'*64})]:
   with patch.dict(self.runtime.config,{key:value}),self.assertRaises(self.real.a.RefreshError):self.runtime.reuse_provenance(source,row['expectedIntent'])
 def test_each_failed_taiwan_source_remains_outside_reuse_allowlist(self):
  for key in self.lineage['failedTaiwanSourceKeys']:
   source=self.sources[key]
   for state in ('failed','saving','verified'):
    existing=deepcopy(self.lineage['rows'][0]['expectedIntent']);existing.update(sourceKey=key,sourceContractSHA256=self.real.a.sha(self.real.a.canonical(source)),url=source['url'],state=state)
    with self.subTest(source=key,state=state),self.assertRaises(self.real.a.RefreshError):self.runtime.reuse_provenance(source,existing)
 def test_current_same_handover_keeps_existing_validation_path(self):
  current=self.runtime.provenance()
  with patch.object(self.real,'pinned',side_effect=AssertionError('unnecessary lineage load')):
   self.assertEqual(self.runtime.reuse_provenance({}, {'ownerHandover':current}),current)

class CustodyReuseTests(unittest.TestCase):
 setUp=owner.OwnerTests.setUp;tearDown=owner.OwnerTests.tearDown;transport=owner.OwnerTests.transport;folder=owner.OwnerTests.folder;clean_global=owner.OwnerTests.clean_global;runtime=owner.OwnerTests.runtime;run_owner=owner.OwnerTests.run_owner
 def install_successor(self,runtime):
  rows=[];self.custody_before={}
  for source in self.selected['sources']:
   folder=runtime.root/'collection/private-originals'/g.a.sha(g.a.canonical(source));intent=json.loads((folder/'successor-intent.json').read_bytes());saved=json.loads((folder/'provenance.json').read_bytes())
   rows.append({'sourceKey':source['sourceKey'],'sourceContractSHA256':g.a.sha(g.a.canonical(source)),'expectedIntent':intent,'expectedIntentSHA256':g.a.sha(g.a.canonical(intent)),'expectedProvenance':saved})
   for name in ('successor-intent.json','provenance.json','original.pdf'):self.custody_before[folder/name]=(folder/name).read_bytes()
  previous=runtime.provenance();runtime.config.update(handoffId='owner-local-comprehensive-20261018-002',predecessorOwnerRuntimePin={'path':'docs/old-owner.json','sha256':'a'*64},dispatchHoldPin={'sha256':'b'*64})
  lineage={'targetHandoffId':runtime.config['handoffId'],'predecessorOwnerRuntimePin':runtime.config['predecessorOwnerRuntimePin'],'predecessorHandover':previous,'ownerUID':runtime.uid,'outputRoot':str(runtime.root),'rows':rows}
  real=g.pinned
  self.addCleanup(patch.stopall)
  patch.object(g,'pinned',side_effect=lambda pin:lineage if pin==g.OWNER_REUSE_PIN else real(pin)).start()
  patch.object(g,'OWNER_PIN',('docs/successor-owner.json','c'*64)).start()
  return rows
 def test_actual_synthetic_saved_originals_survive_handover_zero_get(self):
  runtime=self.runtime();self.assertEqual(self.run_owner(runtime)['networkRequests'],5);self.install_successor(runtime);self.calls=[]
  report=self.run_owner(runtime);self.assertEqual(report['networkRequests'],0);self.assertFalse(self.calls)
  self.assertTrue(all(c['acquisition']['status']=='verified-private-original' for c in report['changes']),report['changes'])
  self.assertTrue(all(c['acquisition']['originalDisposition']=='retained-original-no-network' for c in report['changes']))
  self.assertEqual({p:p.read_bytes() for p in self.custody_before},self.custody_before)
 def test_changed_original_fails_revalidation_without_get_or_rewrite(self):
  runtime=self.runtime();self.run_owner(runtime);self.install_successor(runtime)
  original=next(p for p in self.custody_before if p.name=='original.pdf');original.write_bytes(b'%PDF-corrupt')
  self.calls=[];report=self.run_owner(runtime);self.assertEqual(report['networkRequests'],0);self.assertFalse(self.calls)
  self.assertTrue(any(c['acquisition']['status']!='verified-private-original' for c in report['changes']))
  self.assertEqual(original.read_bytes(),b'%PDF-corrupt')
 def test_failed_intent_and_partial_stay_held_no_get(self):
  runtime=self.runtime();self.run_owner(runtime);self.install_successor(runtime)
  intent=next(p for p in self.custody_before if p.name=='successor-intent.json');bad=json.loads(intent.read_bytes());bad['state']='failed';intent.write_bytes(g.a.canonical(bad));partial=intent.parent/'original.partial';partial.write_bytes(b'held-partial');before=intent.read_bytes()
  self.calls=[];report=self.run_owner(runtime);self.assertEqual(report['networkRequests'],0);self.assertFalse(self.calls)
  self.assertTrue(any(c['acquisition']['errorCode']=='private-save-intent-uncertain' for c in report['changes']))
  self.assertEqual(intent.read_bytes(),before);self.assertEqual(partial.read_bytes(),b'held-partial')

class SuccessorPreflightTests(unittest.TestCase):
 def fixture(self):
  real=module('successor_hold_global','scripts/collect-fixed-global.py');selected,_=real.prepared_comprehensive_configs();real.selection_config=lambda:selected;self.assertEqual(len(selected['sources']),15);hold=json.loads((ROOT/'docs/operations/global-comprehensive-manual-handoff-draft.json').read_bytes())
  hold['handoffId']='owner-local-comprehensive-20261018-002';hold['overlapHold']['active']=True;hold['source']['trustedCommit']='c'*40;hold['selectedSources']=[{'sourceKey':s['sourceKey'],'sourceContractSHA256':real.a.sha(real.a.canonical(s))} for s in selected['sources']]
  raw=real.a.canonical(hold);pin={'path':'docs/operations/successor-handoff.json','sha256':real.a.sha(raw)};config={'handoffId':hold['handoffId'],'dispatchHoldPin':pin}
  with patch.object(real,'OWNER_PIN',('docs/owner002.json','d'*64)),patch.object(real,'owner_config',return_value=config),patch.object(real,'selection_config',return_value=selected),patch.object(real,'pinned',return_value=hold),patch.object(real.a,'preparation_module',return_value=SimpleNamespace(pinned_bytes=lambda *args:raw)):pub=real.publisher_module()
  api=pubtests.FakeAPI();commit='c'*40;tree='e'*40;blob=pub.blob_sha(raw);api.blobs[blob]=raw;api.trees[tree]={pin['path']:blob};api.commits[commit]={'sha':commit,'tree':{'sha':tree},'parents':[]};api.refs['integration/runner-cutover-disposition-20261018']=commit
  return real,pub,api,raw
 def test_dynamic_exact_hold_blob_length_and_read_only_preflight(self):
  real,pub,api,raw=self.fixture();self.assertEqual(pub.HOLD_BYTES,len(raw));self.assertEqual(pub.HOLD_BLOB,pub.blob_sha(raw));self.assertNotEqual(pub.HOLD_BYTES,8676)
  self.assertEqual(pub.verify_active_handover(real,api)['status'],'active-verified');self.assertTrue(all(call[0]=='GET' for call in api.calls))
 def test_changed_hold_bytes_rejected(self):
  real,pub,api,raw=self.fixture();api.blobs[pub.HOLD_BLOB]=raw+b' '
  with self.assertRaises(pub.PublicationError):pub.verify_active_handover(real,api)
  self.assertTrue(all(call[0]=='GET' for call in api.calls))
 def test_legacy_publisher_constants_stay_exact(self):
  pub=module('legacy_successor_publisher','scripts/publish-manual-global-result.py');raw=(ROOT/'docs/operations/global-collection-manual-handoff-20261018.json').read_bytes()
  self.assertEqual(pub.HOLD_BYTES,len(raw));self.assertEqual(pub.HOLD_BLOB,pub.blob_sha(raw));self.assertEqual(pub.HOLD_SHA256,pub.sha(raw))
if __name__=='__main__':unittest.main()
