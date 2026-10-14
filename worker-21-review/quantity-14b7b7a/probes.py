import copy,os,subprocess,types,unittest
from pathlib import Path
env={k:v for k,v in os.environ.items() if not k.startswith('GIT_')}
pin='14b7b7af37f1be842913d0f0c923c8a1c1df1147'
source=subprocess.check_output(['git','show',pin+':scripts/recipe-quantity-owner15.py'],env=env,text=True)
module=types.ModuleType('pinned_quantity_owner15');exec(compile(source,pin+':scripts/recipe-quantity-owner15.py','exec'),module.__dict__)
converter=module.ReviewedConverter(Path.cwd())
def ingredient(value=1500,unit='mg',**extras):
 return {'name':'synthetic source','amount':None,'unit':None,'form':'drained','originalText':'synthetic observed quantity','densityGPerMl':None,
  'sourceQuantity':{'value':value,'unit':unit,'status':'source-reported',**extras}}
def record(items):
 return {'id':'synthetic:review21','kind':'recipe','provenance':{'sourceId':'synthetic-only','recordId':'r1','url':'https://example.invalid/synthetic','license':'synthetic-only','attribution':'review fixture'},
  'data':{'ingredients':items,'yield':{'value':None,'unit':'portion'},'automaticPlanningEligible':True}}
def run(items):return module.normalize_recipe(record(items),converter)
class Review(unittest.TestCase):
 def test_measured_regional_and_count_evidence_still_withheld(self):
  cup=ingredient(1,'cup',definitionId='synthetic:AU-cup-250ml');cup['measuredMl']=250
  count=ingredient(2,'count');count['unitMassEvidence']={'value':40,'unit':'g','sourceId':'synthetic-scale'}
  for item in run([cup,count])['data']['ingredients']:
   self.assertIsNone(item['amount']);self.assertEqual(item['quantityNormalization']['status'],'unresolved')
 def test_density_never_becomes_mass_or_nutrient_transfer(self):
  item=ingredient(0.25,'l');item['densityGPerMl']=1.2;item['nutrientBasis']='per100g-prepared'
  out=run([item])['data']['ingredients'][0]
  self.assertEqual((out['amount'],out['unit']),(250,'ml'));self.assertIsNone(out['quantityNormalization']['edibleMassG'])
  self.assertEqual(out['densityGPerMl'],1.2);self.assertEqual(out['nutrientBasis'],'per100g-prepared')
 def test_gross_drained_and_preparation_basis_are_retained_not_equated(self):
  item=ingredient(0.2,'kg',basis={'kind':'gross-purchased','denominator':None},preparationStateId='synthetic:raw')
  item['edibleFraction']=0.8;before=copy.deepcopy(item);result=run([item]);out=result['data']['ingredients'][0]
  self.assertEqual(out['amount'],200);self.assertIsNone(out['quantityNormalization']['edibleMassG'])
  self.assertEqual(out['sourceQuantity'],before['sourceQuantity']);self.assertEqual(out['form'],'drained')
  self.assertEqual(out['quantityNormalization']['conversion']['quantity']['preparationStateId'],'synthetic:raw')
  self.assertFalse(result['data']['automaticPlanningEligible']);self.assertEqual(item,before)
 def test_source_and_prior_projection_mismatch_withholds_canonical_amount(self):
  item=ingredient();item.update(amount=20,unit='ml');out=run([item])['data']['ingredients'][0]
  self.assertIsNone(out['amount']);self.assertIsNone(out['unit'])
  self.assertEqual(out['quantityNormalization']['reason'],'conflicting-prior-projection')
  self.assertEqual(out['quantityNormalization']['originalProjection'],{'amount':20,'unit':'ml'})
 def test_incomplete_conversion_never_reuses_old_numeric_projection(self):
  items=[ingredient(None),ingredient(2,qualifier='trace'),ingredient(1,range={'min':None,'max':3}),ingredient(1,definitionId='synthetic:custom-g')]
  for item in items:item.update(amount=50,unit='g')
  result=run(items)
  for old,out in zip(items,result['data']['ingredients']):
   self.assertIsNone(out['amount']);self.assertEqual(out['sourceQuantity'],old['sourceQuantity'])
  self.assertEqual(result['provenance'],record(items)['provenance'])
if __name__=='__main__':unittest.main(verbosity=2)
