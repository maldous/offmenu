import os,subprocess,types,copy,unittest
env={k:v for k,v in os.environ.items() if not k.startswith('GIT_')}
pin='b086c941cc3de3c6da126e15c650f2cd544686c2'
def blob(p):return subprocess.check_output(['git','show',pin+':'+p],env=env,text=True)
m=types.ModuleType('regional15');exec(compile(blob('scripts/regional-quantity-owner15.py'),pin,'exec'),m.__dict__)
fixtures_source=blob('tests/global-data-validation/test_regional_quantity_owner15.py')
exec(fixtures_source[fixtures_source.index('CONTEXT ='):fixtures_source.index('class RegionalChain')])
class IndependentReview(unittest.TestCase):
 def test_region_definition_temperature_food_version_and_state_do_not_join(self):
  for field in m.CONTEXT:
   q=source();q['context'][field]='synthetic:other'
   self.assertEqual(m.convert_chain(q,fixtures(),allow,target_basis='gross')['status'],'unknown',field)
 def test_no_inferred_inverse_gross_or_drained_transfer(self):
  for basis in ['edible','drained']:
   self.assertEqual(m.convert_chain(source(unit='g',basis=basis),fixtures(),allow,target_basis='gross')['status'],'unknown')
  r=m.convert_chain(source(),fixtures(),allow,target_basis='edible')
  self.assertFalse(m.shopping_projection(r,required_basis='gross')['ready'])
 def test_combined_cohort_conflict_and_unresolved_inputs_never_become_total(self):
  a=m.convert_chain(source(),fixtures(),allow,target_basis='gross')
  q=source();e=fixtures();q['context']['region']='synthetic:B'
  for x in e:x['context']['region']='synthetic:B'
  b=m.convert_chain(q,e,allow,target_basis='gross')
  self.assertFalse(m.combined_projection([a,b],required_basis='gross')['ready'])
  unknown=m.convert_chain(source(),[],allow,target_basis='gross')
  self.assertFalse(m.combined_projection([a,unknown],required_basis='gross')['ready'])
 def test_identical_density_paths_are_conflicts_and_result_mutation_is_not_ready(self):
  e=fixtures();duplicate=copy.deepcopy(e[1]);duplicate['id']='other-density'
  self.assertEqual(m.convert_chain(source(),e+[duplicate],allow,target_basis='gross')['reason'],'conflicting-chains')
  r=m.convert_chain(source(),e,allow,target_basis='gross');r['lineage'][0]['version']='changed'
  self.assertFalse(m.shopping_projection(r,required_basis='gross')['ready'])
 def test_issuer_grant_hash_and_use_mismatch_withhold(self):
  for field,value in [('sha256','wrong'),('use','display'),('issuer','other')]:
   def denied(x):g=allow(x);g[field]=value;return g
   self.assertEqual(m.convert_chain(source(),fixtures(),denied,target_basis='gross')['status'],'unknown')
 def test_malformed_observed_unit_is_unknown_not_uncaught_exception(self):
  for unit in [['regional-cup'],{'id':'regional-cup'}]:
   q=source(unit=unit)
   self.assertEqual(m.convert_chain(q,fixtures(),allow,target_basis='gross')['status'],'unknown')
if __name__=='__main__':unittest.main(verbosity=2)
