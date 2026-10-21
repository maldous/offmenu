"""Generated local inputs only; no existing corpus or DB reads."""
from dataclasses import replace
from contextlib import closing
import gzip,hashlib,json,os,sqlite3,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from offmenu.refresh import ingredient_ingestion as s
from offmenu.refresh.core import canonical,RefreshError

class SourceIngredientImportTests(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.root=Path(self.temp.name)
  self.limits=s.ImportLimits(1048576,100,2097152,262144,4194304,8388608,30)
 def run_import(self,a,db):
  m=s.prepare_source_import((a,));return s.ingest_source_assets(db,(a,),limits=self.limits,input_manifest_sha256=s._digest(m),selection_receipt_sha256='f'*64)
 def test_native_raw_declarations_absence_units_and_pending_links(self):
  rows=[]
  for i,v in enumerate(('  Épices / 油  ','',None,False,{'unit':'1,5 dl'})):
   rows.append({'id':'fixture:product:'+str(i),'kind':'product','provenance':{'sourceId':'fixture','releaseId':'1','recordId':str(i)},'data':{'ingredientsText':v,'language':'fr','quantity':'1,5','unit':'dl'}})
  rows.append({'id':'fixture:product:missing','kind':'product','provenance':{'sourceId':'fixture','releaseId':'1','recordId':'missing'},'data':{'quantity':'unknown'}})
  rows.append({'kind':'nutrientProfile','data':{'retainedElsewhere':True}})
  raw=b''.join(canonical([r]) for r in rows);p=self.root/'products.jsonl';p.write_bytes(raw)
  a=s.SourceAsset('fixture-products',str(p),len(raw),hashlib.sha256(raw).hexdigest(),7,'fixture','1','products',6)
  with patch.object(os,'open',side_effect=AssertionError('prepare has no source IO')),patch.object(Path,'stat',side_effect=AssertionError('prepare has no source stat')):s.prepare_source_import((a,))
  with closing(sqlite3.connect(self.root/'new.sqlite')) as db:
   result=self.run_import(a,db)
   self.assertEqual(result['tableCounts']['retained_reference_record'],6);self.assertEqual(result['tableCounts']['product_processing_audit'],6)
   self.assertEqual(result['tableCounts']['ingredient_concept'],0);self.assertEqual(result['tableCounts']['ingredient_declaration_ref'],0)
   self.assertEqual(db.execute("SELECT count(*) FROM product_processing_audit WHERE declaration_id IS NULL AND semantic_mapping_status='pending' AND composition_state='unknown'").fetchone()[0],6)
   stored=db.execute('SELECT source_payload_json FROM retained_reference_record WHERE source_ordinal=1').fetchone()[0]
   self.assertEqual(stored,canonical([rows[0]]).decode())
   counts=result['assets'][0]['counts'];self.assertEqual((counts['products'],counts['non_product'],counts['quarantined'],counts['declaration_missing']),(6,1,2,1))
   self.assertEqual(db.execute('PRAGMA foreign_key_check').fetchall(),[])
   with self.assertRaisesRegex(RefreshError,'new-empty-store'):self.run_import(a,db)
 def test_gzipped_native_registry_is_raw_cache_not_canonical_concepts(self):
  rows=[{'id':'source:0001','language':'de','name':'Öl','unit':'1,5 L'},{'id':'source:0001','language':'ja','name':'油'}]
  raw=b''.join(canonical(r) for r in rows);packed=gzip.compress(raw,mtime=0);p=self.root/'registry.jsonl.gz';p.write_bytes(packed)
  a=s.SourceAsset('fixture-registry',str(p),len(packed),hashlib.sha256(packed).hexdigest(),2,'fixture-dictionary','1','registry',compression='gzip')
  with closing(sqlite3.connect(':memory:')) as db:
   result=self.run_import(a,db)
   self.assertEqual(result['tableCounts']['retained_reference_record'],2);self.assertEqual(result['tableCounts']['ingredient_concept'],0)
   self.assertEqual(db.execute('SELECT count(DISTINCT reference_record_id) FROM retained_reference_record').fetchone()[0],2)
   self.assertEqual(db.execute('SELECT source_payload_json FROM retained_reference_record ORDER BY source_ordinal').fetchall(),[(canonical(r).decode(),) for r in rows])

if __name__=='__main__':unittest.main()
