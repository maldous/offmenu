import json,sys,tempfile,unittest,hashlib,gzip
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parents[1]/'scripts'))
import importlib.util
spec=importlib.util.spec_from_file_location("foodon",Path(__file__).parents[1]/"tools/data-processing/collect_foodon_definitions.py")
foodon=importlib.util.module_from_spec(spec);spec.loader.exec_module(foodon)
import jsonschema_rs
ROOT=Path(__file__).parents[1]
class CommonDataTests(unittest.TestCase):
 def test_manifest_payload_and_byte_checksums_are_distinct(self):
  spec=importlib.util.spec_from_file_location('publisher',ROOT/'tools/data-processing/publish_common_data.py');publisher=importlib.util.module_from_spec(spec);spec.loader.exec_module(publisher)
  with tempfile.TemporaryDirectory() as temp:
   root=Path(temp);release=root/'common-data/releases/fixture';release.mkdir(parents=True)
   m={'releaseId':'fixture','label':'餡'};m['manifestSha256']=hashlib.sha256(json.dumps(m,separators=(',',':')).encode()).hexdigest();b=(json.dumps(m,ensure_ascii=False,indent=2)+'\n').encode()
   (release/'manifest.json').write_bytes(b);(root/'common-data/manifest.json').write_bytes(b)
   receipt=publisher.write_manifest_checksums(root)
   for f in receipt['files']:
    self.assertEqual(f['byteSha256'],hashlib.sha256(b).hexdigest());self.assertEqual(f['payloadSha256'],m['manifestSha256']);self.assertNotEqual(f['byteSha256'],f['payloadSha256']);self.assertEqual((root/(f['key']+'.sha256')).read_text(),f['byteSha256']+'  manifest.json\n')
 def test_unicode_links_and_formal_expressions_remain_fixed(self):
  schema=json.loads((ROOT/'contracts/corpus/common-data.schema.json').read_text())
  validator=jsonschema_rs.Draft202012Validator({'$defs':schema['$defs'],'$ref':'#/$defs/value'},validate_formats=True)
  validator.validate({'kind':'uri','value':'https://ja.wikipedia.org/wiki/餡'})
  validator.validate({'kind':'expression','syntax':'rdf/xml','value':'<owl:Restriction />'})
  self.assertFalse(validator.is_valid({'kind':'uri','value':'A prose definition'}))
 def test_mistyped_source_uri_preserves_original_and_marks_interpretation(self):
  with tempfile.TemporaryDirectory() as temp:
   source=Path(temp)/'source';source.mkdir();output=Path(temp)/'aligned'
   xml='<rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#" xmlns:owl="http://www.w3.org/2002/07/owl#" xmlns:rdfs="http://www.w3.org/2000/01/rdf-schema#"><owl:Class rdf:about="http://purl.obolibrary.org/obo/FOODON_00000001"><rdfs:label rdf:datatype="http://www.w3.org/2001/XMLSchema#anyURI">A prose definition</rdfs:label></owl:Class></rdf:RDF>'
   (source/'foodon.owl').write_text(xml)
   (source/'acquisition.json').write_text(json.dumps({'revision':'fixture','root':'https://example.org/','files':[{'key':'foodon.owl','sha256':hashlib.sha256(xml.encode()).hexdigest(),'url':'https://example.org/foodon.owl','bytes':len(xml)}]}))
   foodon.collect(source,output)
   packet=json.loads(gzip.open(output/'foodon-common.jsonl.gz','rt').readline());fact=packet['assertions'][0];original=packet['assertions'][1]
   self.assertEqual(fact['status'],'candidate');self.assertEqual(fact['value']['kind'],'text');self.assertEqual(fact['value']['value'],'A prose definition')
   self.assertIn(foodon.RDF+'datatype',original['value']['fields']['attributes']['fields'])
   self.assertEqual(original['value']['fields']['lexicalValue']['value'],'A prose definition')
   jsonschema_rs.Draft202012Validator(json.loads((ROOT/'contracts/corpus/common-data.schema.json').read_text()),validate_formats=True).validate(packet)
if __name__=='__main__':unittest.main()
