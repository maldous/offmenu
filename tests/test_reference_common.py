import gzip,hashlib,importlib.util,json,tempfile,unittest
from pathlib import Path
ROOT=Path(__file__).parents[1]
spec=importlib.util.spec_from_file_location('reference_align',ROOT/'scripts/align-reference-common.py');module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
class ReferenceAlignmentTests(unittest.TestCase):
 def test_curated_input_is_complete_and_raw_fields_are_not_restored(self):
  with tempfile.TemporaryDirectory() as temp:
   data=Path(temp);curated=data/'curated-expanded-country-search-20261013/blobs';curated.mkdir(parents=True);files=[];sources={}
   for source,directory,kind in [('dietary-guidelines','dietary-guidelines-20261013','sourceAssertion'),('wikibooks','wikibooks-2026-10-13-live','recipe')]:
    native=data/directory;native.mkdir();(native/'manifest.json').write_text(json.dumps({'releaseId':'fixture','normalizedRows':1,'license':'CC0'}));(native/'normalized.jsonl.gz').write_bytes(gzip.compress(b'raw archive only'))
    row={'id':'offmenu:'+kind+':fixture','kind':kind,'schemaVersion':'1.0','countries':['GB'],'data':{'name':'Example','description':'語','yield':{'value':None,'unit':'portion'}},'provenance':{'sourceId':source,'recordId':'native-record','url':'https://example.org/source','license':'CC0','attribution':'Example','visibility':'public','sourceDate':'2026-10-14'},'curation':{'schema':'offmenu-curation/1','rawSourcePayloadPublished':False}}
    key='records/'+source+'/0.jsonl.gz';p=curated/key;p.parent.mkdir(parents=True);b=gzip.compress((json.dumps([row['id'],[row]])+'\n').encode());p.write_bytes(b);files.append({'key':key,'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()});sources[source]={'records':1,'withheldRecords':0}
   (curated/'manifest.json').write_text(json.dumps({'releaseId':'fixture','sources':sources,'files':files}));out=data/'output';module.align(data,out);m=json.loads((out/'manifest.json').read_text());self.assertTrue(m['complete']);self.assertEqual(m['counts']['resources'],2);self.assertEqual(m['counts']['translations'],0)
   packet=json.loads(gzip.decompress((out/m['files'][0]['key']).read_bytes()).decode().split('\n')[0]);data_fact=next(a for a in packet['assertions'] if a['sourcePath']=='data');self.assertEqual(data_fact['value']['fields']['description']['language'],'und');self.assertEqual(data_fact['value']['fields']['yield']['fields']['value'],{'kind':'null','value':None});self.assertNotIn('raw archive only',json.dumps(packet))
if __name__=='__main__':unittest.main()
