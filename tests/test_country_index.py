import gzip,hashlib,importlib.util,json,tempfile,unittest
from pathlib import Path
spec=importlib.util.spec_from_file_location('country_index',Path(__file__).parents[1]/'scripts/index-curated-countries.py');module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
from test_curation_merge import release,merger
class CountryIndexTests(unittest.TestCase):
 def test_complete_country_postings_survive_source_offset_merge(self):
  with tempfile.TemporaryDirectory() as temp:
   root=Path(temp);original=release(root/'input','fixture','off','food');m=json.loads((original/'manifest.json').read_text());m.update(entries=1,records=1,curatedAcceptance={'status':'all-curated-records-exercised','releaseId':'fixture','records':1});(original/'manifest.json').write_text(json.dumps(m))
   indexed=root/'indexed';module.index(original,indexed,'indexed');m=json.loads((indexed/'manifest.json').read_text());self.assertEqual(m['countryIndexAcceptance']['entries'],1);self.assertTrue(m['sources']['off']['countryIndex'])
   with gzip.open(indexed/'countries/off/AU-product.json.gz','rt') as f:self.assertEqual(json.load(f),[0])
   other=release(root/'other','other','prices','price');merged=merger.merge([other,indexed],root/'merged','combined')
   with gzip.open(root/'merged/countries/off/AU-product.json.gz','rt') as f:self.assertEqual(json.load(f),[1000])
   self.assertTrue(merged['sources']['off']['countryIndex'])
