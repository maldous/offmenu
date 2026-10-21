"""Generated HTML/records only; no retained recipe originals or populated DBs."""
from contextlib import closing
import copy,hashlib,json,sqlite3,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from offmenu.refresh import recipe_menu_store as s,source_faithful_parse as parser
from offmenu.refresh.core import canonical,RefreshError

class RecipeMenuStoreTests(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.root=Path(self.temp.name)
  self.limits=s.StoreLimits(1048576,15,1000,8388608,500,500,16777216,33554432,30);self.raws={};self.calls=[]
 def asset(self,key,kind='recipe',variant=0):
  if kind=='recipe':
   data={'@type':'Recipe','name':'Pâte & Öl','recipeYield':'4 personnes','recipeIngredient':['1,5 dl crème','','½ tsp salt'],
         'recipeInstructions':['Mélanger doucement.','Cuire 10 minutes.']}
   visible='<p>4 personnes</p><ul><li>1,5 dl crème</li><li>½ tsp salt</li></ul><p>Mélanger doucement.</p><p>Cuire 10 minutes.</p>'
   raw=('<html lang="fr"><h1>Pâte &amp; Öl</h1>'+visible+'<script type="application/ld+json">'+json.dumps(data,ensure_ascii=False)+'</script><!--'+str(variant)+'--></html>').encode()
  else:
   raw=('<html lang="fr"><div class="menuCategory"><h2>Déjeuner</h2>'+''.join('<div class="menuItemBox" id="repeat"><span class="menuItemName">Café</span><span class="menuItemDesc">Crème</span>'+p+'</div>'for p in ('3 $','7,50 EUR'))+'</div></html>').encode()
  sha=hashlib.sha256(raw).hexdigest();self.raws[sha]=raw
  return {'sourceId':'fixture-recipe'if kind=='recipe'else'fixture-menu','sourceRecordId':key,'recordKind':kind,
          'inputPath':'/fixture-not-opened/'+key+'.html','inputBytes':len(raw),'inputSHA256':sha,'release':'fixture-v1','sourceUseScope':'fixture-only'}
 def parse(self,a,module):
  self.calls.append(a['inputSHA256']);raw=self.raws[a['inputSHA256']]
  src={'originalSHA256':a['inputSHA256'],'sourceURL':'https://example.invalid/fixture','release':a['release'],
       'licenseStatus':'fixture-only','region':None,'encoding':'utf-8','adapter':'calmos-menu-v1'}
  if a['recordKind']=='recipe':records=[module.parse_html_recipe(raw,source=src,source_id=a['sourceId'],source_record_id=a['sourceRecordId'],country='AU',language='fr',attribution='fixture')]
  else:records=module.parse_html_menu(raw,source=src,source_id=a['sourceId'],country='MF',language='fr',attribution='fixture')
  return records,{'inputSHA256':a['inputSHA256'],'inputBytes':len(raw),'parserVersion':module.PARSER_VERSION,'EOFFullyVerified':True,'bodyPasses':1,'records':len(records)}
 def load(self,db,assets,callback=None,**kwargs):
  manifest=s.prepare_recipe_menu(assets)
  return s.ingest_recipe_menu(db,assets,parser_module=parser,parse_asset_once=callback or self.parse,limits=self.limits,
    run_id='fixture-run',input_manifest_sha256=s._hash(manifest),selection_receipt_sha256='f'*64,**kwargs)
 def test_real_parser_projection_titles_quantities_steps_menus_and_payload(self):
  assets=[self.asset('one',variant=1),self.asset('two',variant=2),self.asset('menu','menuItem')]
  assets[0]['citationBinding']={'fetch_asset':{'asset_id':'fixture-asset','citation_id':'fixture-citation','original_sha256':assets[0]['inputSHA256'],'original_bytes':assets[0]['inputBytes']},
      'fetch_citation':{'citation_id':'fixture-citation','identity_state':'unresolved-backfill','metadata_origin_pointer':'fixture-only','fetch_receipt_sha256':None,'unknown_fields_json':'{"clock":"unknown"}'}}
  with closing(sqlite3.connect(self.root/'generated.sqlite'))as db:
   result=self.load(db,assets);counts=result['tableCounts']
   self.assertEqual(self.calls,[a['inputSHA256']for a in assets]);self.assertEqual((counts['recipe_source_record'],counts['source_recipe_variant'],counts['source_menu_item'],counts['menu_entry']),(4,2,2,2))
   self.assertEqual((counts['recipe_ingredient_line'],counts['recipe_ordered_step'],counts['recipe_region_assertion']),(4,4,0))
   self.assertEqual(db.execute('SELECT count(DISTINCT recipe_variant_id),count(DISTINCT original_title) FROM source_recipe_variant').fetchone(),(2,1))
   self.assertEqual(db.execute("SELECT yield_raw_text,yield_value_lexeme,yield_unit_lexeme,yield_interpreted_value,dish_concept_id FROM source_recipe_variant LIMIT 1").fetchone(),('4 personnes','4','personnes',None,None))
   self.assertEqual(db.execute("SELECT raw_value_lexeme,raw_unit_lexeme,interpreted_value,ingredient_concept_id,food_match_status FROM recipe_ingredient_line WHERE original_expression='1,5 dl crème' LIMIT 1").fetchone(),('1,5','dl',None,None,'pending'))
   self.assertEqual(db.execute('SELECT step_order,original_text FROM recipe_ordered_step WHERE recipe_variant_id=(SELECT recipe_variant_id FROM source_recipe_variant LIMIT 1) ORDER BY step_order').fetchall(),[(1,'Mélanger doucement.'),(2,'Cuire 10 minutes.')])
   self.assertEqual(db.execute('SELECT line_order FROM recipe_ingredient_line WHERE recipe_variant_id=(SELECT recipe_variant_id FROM source_recipe_variant LIMIT 1) ORDER BY line_order').fetchall(),[(1,),(3,)])
   self.assertEqual(db.execute('SELECT count(DISTINCT native_record_id) FROM recipe_source_record WHERE source_id=?',('fixture-menu',)).fetchone()[0],1)
   self.assertEqual(db.execute('SELECT price_lexeme,price_value,currency FROM source_menu_item ORDER BY price_lexeme').fetchall(),[('3',None,None),('7,50',None,'EUR')])
   full=json.loads(db.execute('SELECT source_payload_json FROM recipe_source_record WHERE source_id=? LIMIT 1',('fixture-recipe',)).fetchone()[0])
   self.assertEqual(full['ingredientLines'][0]['originalExpression'],'1,5 dl crème');self.assertIn('sourceNotes',full)
   self.assertEqual(db.execute('PRAGMA foreign_key_check').fetchall(),[])
   self.assertEqual(db.execute('SELECT identity_state,unknown_reason FROM recipe_citation_ref').fetchone(),('unresolved-backfill','{"clock":"unknown"}'))
   with self.assertRaisesRegex(RefreshError,'new-empty-store-required'):self.load(db,assets)
 def test_receipt_failure_holds_and_preserves_only_completed_asset(self):
  assets=[self.asset('one',variant=1),self.asset('two',variant=2)]
  def bad(a,module):
   records,receipt=self.parse(a,module)
   if a['sourceRecordId']=='two':receipt['EOFFullyVerified']=False
   return records,receipt
  with closing(sqlite3.connect(':memory:'))as db:
   with self.assertRaisesRegex(RefreshError,'parser-receipt')as error:self.load(db,assets,bad)
   self.assertEqual(db.execute('SELECT count(*) FROM recipe_source_record').fetchone()[0],1)
   self.assertEqual(db.execute('SELECT state,exception_count FROM recipe_store_release').fetchone(),('incomplete',1))
   self.assertFalse(error.exception.recipe_store_retained_state['completeReceiptReturned'])
 def _assert_caller_usable_after_import_deadline(self,fail):
  assets=[self.asset('deadline')]
  def callback(a,module):
   records,receipt=self.parse(a,module)
   if fail:receipt['EOFFullyVerified']=False
   return records,receipt
  with closing(sqlite3.connect(':memory:'))as db,patch.object(s.time,'monotonic',return_value=100.0)as clock:
   if fail:
    with self.assertRaisesRegex(RefreshError,'parser-receipt'):self.load(db,assets,callback)
    self.assertEqual(db.execute('SELECT state FROM recipe_store_release').fetchone()[0],'incomplete')
   else:self.load(db,assets,callback)
   clock.return_value=1000.0
   self.assertEqual(db.execute('WITH RECURSIVE n(x) AS (VALUES(1) UNION ALL SELECT x+1 FROM n WHERE x<2000) SELECT sum(x) FROM n').fetchone()[0],2001000)
 def test_deadline_handler_cleared_after_success(self):self._assert_caller_usable_after_import_deadline(False)
 def test_deadline_handler_cleared_after_invalid_receipt(self):self._assert_caller_usable_after_import_deadline(True)
 def test_prepare_is_pure_and_missing_steps_or_yield_are_not_fabricated(self):
  assets=[self.asset('one')]
  with patch.object(Path,'open',side_effect=AssertionError('no body open')),patch.object(Path,'stat',side_effect=AssertionError('no body stat')):s.prepare_recipe_menu(assets)
  def partial(a,module):
   records,receipt=self.parse(a,module);records=copy.deepcopy(records);records[0]['yield']=None;records[0]['orderedSteps']=[];records[0]['language']='und'
   return records,receipt
  with closing(sqlite3.connect(':memory:'))as db:
   result=self.load(db,assets,partial)
   self.assertEqual(db.execute('SELECT yield_raw_text,yield_interpreted_value,language,step_extraction_state FROM source_recipe_variant').fetchone(),(None,None,'und','missing'))
   self.assertEqual(db.execute('SELECT count(*) FROM recipe_ordered_step').fetchone()[0],0)
   self.assertEqual(result['assets'][0]['exceptions'],1)
   self.assertEqual(db.execute('SELECT reason_code FROM recipe_store_exception').fetchone()[0],'directions-missing')

if __name__=='__main__':unittest.main()
