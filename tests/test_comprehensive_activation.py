"""Offline exact adopted-profile and closed handoff verification; no source requests."""
import ast,base64,hashlib,importlib.util,json,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def load():
 s=importlib.util.spec_from_file_location('active_profile_fixture',ROOT/'scripts/collect-fixed-global.py');g=importlib.util.module_from_spec(s);s.loader.exec_module(g);return g
class ActivationTests(unittest.TestCase):
 def test_three_status_changes_only(self):
  for name,keys in [('global-comprehensive-selection',['knownIntakeSuccessor','retainedVerification']),('global-comprehensive-manifest',['retainedContractExtension'])]:
   old=json.loads((ROOT/f'docs/collection-selections/{name}-draft.json').read_bytes());new=json.loads((ROOT/f'docs/collection-selections/{name}.json').read_bytes())
   for key in keys:self.assertEqual(new[key]['status'],'parent-reviewed-owner-manual');new[key]['status']=old[key]['status']
   self.assertEqual(old,new)
 def test_user_only_selection_restores_runner_defaults(self):
  g=load();baseline=(g.SELECTION_PIN,g.MANIFEST_PIN,g.OWNER_PIN);old=g.selection_config()
  for args in ([],['--mode','runner']):
   with g.owner_successor_profile(args):self.assertEqual((g.SELECTION_PIN,g.MANIFEST_PIN,g.OWNER_PIN),baseline)
  for args in (['--mode','user'],['--mode','user','--publish-only']):
   with g.owner_successor_profile(args):
    selected=g.selection_config();manifest=g.manifest_config();self.assertEqual(selected['sources'][:10],old['sources']);self.assertEqual(len(selected['sources']),15);self.assertEqual(manifest['retainedContractExtension']['selectedCount'],988)
    owner=g.owner_config(selected);self.assertEqual(owner['handoffId'],'owner-local-comprehensive-20261018-002');self.assertEqual(owner['dispatchHoldPin']['blob'],'a01736373d5e2c42c613dc3c51b494d48bc32233')
   self.assertEqual((g.SELECTION_PIN,g.MANIFEST_PIN,g.OWNER_PIN),baseline)
 def test_exact_current_hold_preflight_read_only(self):
  g=load()
  with g.owner_successor_profile(['--mode','user']):
   owner=g.owner_config(g.selection_config());pin=owner['dispatchHoldPin'];raw=(ROOT/pin['path']).read_bytes();pub=g.publisher_module();calls=[]
   class API:
    def call(self,method,path,payload=None,absent=False):
     calls.append((method,path));assert method=='GET'
     if path=='user':return {'id':6347545}
     if path=='repos/maldous/offmenu':return {'id':1416253963,'full_name':'maldous/offmenu','private':True,'owner':{'id':6347545},'permissions':{'push':True}}
     if '/git/ref/' in path:return {'object':{'sha':pin['commit']}}
     if '/contents/' in path:return {'type':'file','sha':pin['blob'],'size':len(raw),'encoding':'base64','content':base64.b64encode(raw).decode()}
     raise AssertionError(path)
   result=pub.verify_active_handover(g,API());self.assertEqual(result['status'],'active-verified');self.assertEqual(result['checkpointSHA256'],pin['sha256']);self.assertEqual(len(calls),4)
 def test_old_handoff_and_runtime_exact(self):
  for path,digest in [('docs/operations/global-collection-manual-handoff-20261018.json','fa87ebcb5463ffdec2f7bbfe0141da0c518b40a59c29297646b92a0644e165f1'),('docs/collection-selections/owner-local-runtime.json','8dd3372dd9c2f4f0ec5f845cdc1a97c64addf8fe12ccecc26603128bb2bf514b')]:self.assertEqual(hashlib.sha256((ROOT/path).read_bytes()).hexdigest(),digest)
 def test_launcher_all_current_pins_match(self):
  tree=ast.parse((ROOT/'scripts/run-global-on-foo.py').read_text());pins=next(ast.literal_eval(n.value) for n in tree.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='PINNED_FILES' for t in n.targets))
  for path,digest in pins.items():self.assertEqual(hashlib.sha256((ROOT/path).read_bytes()).hexdigest(),digest,path)
if __name__=='__main__':unittest.main()
