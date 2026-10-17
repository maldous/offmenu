import gzip,importlib.util,json,tempfile,unittest
from pathlib import Path
spec=importlib.util.spec_from_file_location('fineli_refs',Path(__file__).parents[1]/'scripts/collect-fineli-reference-tables.py');module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
class FineliReferenceTests(unittest.TestCase):
 def test_formula_yield_and_source_diet_tags_remain_unreviewed(self):
  with tempfile.TemporaryDirectory() as temp:
   root=Path(temp);p=root/'fineli-basic2';p.mkdir()
   for name,text in {'foodname_EN':'FOODID;FOODNAME\n1;Recipe\n2;Ingredient\n','specdiet_EN':'THSCODE;DESCRIPT\nVEGAN;vegan\n','contribfood':'FOODID;CONFDID;AMOUNT;FOODUNIT;MASS;EVREMAIN;RECYEAR\n1;2;50,00;G;50,00;70;\n','specdiet':'FOODID;SPECDIET\n1;VEGAN\n'}.items():(p/(name+'.csv')).write_text(text,encoding='cp1252')
   (root/'acquisition.json').write_text(json.dumps([{'key':'fineli-basic2.zip','sha256':'fixture'}]));output=root/'normalized';module.collect(root,output)
   with gzip.open(output/'normalized.jsonl.gz','rt') as f:rows=[json.loads(line)[0] for line in f]
   recipe,assertion=rows;self.assertIsNone(recipe['data']['yield']['value']);self.assertFalse(recipe['data']['automaticPlanningEligible']);self.assertEqual(recipe['data']['ingredients'][0]['sourceFields']['EVREMAIN'],'70');self.assertEqual(recipe['data']['ingredients'][0]['amount'],50);self.assertEqual(assertion['data']['qualificationStatus'],'unknown');self.assertFalse(assertion['data']['automaticDietQualification'])
