import importlib.util,unittest,tempfile
from pathlib import Path
import openpyxl
spec=importlib.util.spec_from_file_location('next_national',Path(__file__).parents[1]/'scripts/collect-next-national.py');module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
class NationalFileTests(unittest.TestCase):
 def test_fineli_units_locales_and_unquoted_bibliography_continuation(self):
  with tempfile.TemporaryDirectory() as temp:
   root=Path(temp);p=root/'fineli-basic2';p.mkdir()
   files={'food':'FOODID;FOODNAME\n1;RUOKA\n','component':'EUFDNAME;COMPUNIT\nPROT;G\nNA;MG\n','eufdname_EN':'THSCODE;DESCRIPT\nPROT;protein\nNA;sodium\n','component_value':'FOODID;EUFDNAME;BESTLOC;ACQTYPE;METHTYPE;METHIND\n1;PROT;3,5;A;M;I\n1;NA;;A;M;I\n','publication':'PUBLID;CITATION;REFTYPE;ACQTYPE;DOI\n10;First line\nsecond line;AJ;A;\n'}
   for lang in ['EN','FI','SV']:files['foodname_'+lang]='FOODID;FOODNAME;LANG\n1;Food;'+lang+'\n'
   for name,text in files.items():(p/(name+'.csv')).write_text(text,encoding='cp1252')
   rows,summary=module.fineli(root);self.assertEqual(rows[0]['nutrients']['protein']['value'],3.5);self.assertEqual(rows[0]['nutrients']['protein']['unit'],'g');self.assertIsNone(rows[0]['nutrients']['sodium']['value']);self.assertEqual(summary['nutrientObservations'],2);self.assertEqual(set(rows[0]['names']),{'en','fi','sv'})
 def test_foodfiles_non_food_denominators_cannot_become_whole_food_metrics(self):
  with tempfile.TemporaryDirectory() as temp:
   root=Path(temp);p=root/'nz-extracted';p.mkdir();w=openpyxl.Workbook();s=w.active;s.append(['Copyright']);s.append(['FoodID','Food Name']);s.append(['1','Food']);w.save(p/'ExcelFilesNamesx')
   (p/'UnabridgedCodes').write_text('Copyright\nCode~Description~Unit Code~Matrix Unit Code\nPROT~Protein~g~N\nFAT~Fat~g~W\n',encoding='utf8')
   (p/'UnabridgedDataFT').write_text('Copyright\nFoodID~Component Identifier~Value~Unit Code~Matrix Unit Code~Source Code~Value Type Code~Acquisition Type Code~Method Type Code~Method Indicator Code\n1~PROT~10~g~N~~A~A~A~A\n1~FAT~0~g~W~~A~A~A~A\n',encoding='utf8')
   rows,summary=module.foodfiles(root);nutrients=rows[0]['nutrients'];self.assertNotIn('protein',nutrients);self.assertEqual(nutrients['foodfiles:PROT']['basis']['unit'],'source-matrix:N');self.assertEqual(nutrients['fat']['value'],0);self.assertEqual(summary['nutrientObservations'],2)
 def test_source_table_rejects_unresolved_column_overflow(self):
  with tempfile.TemporaryDirectory() as temp:
   p=Path(temp)/'table.csv';p.write_text('id;value\n1;2;unescaped\n')
   with self.assertRaisesRegex(ValueError,'Malformed source row'):module.table(p)
