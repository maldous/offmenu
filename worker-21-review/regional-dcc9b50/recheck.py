import os,unittest,copy
from pathlib import Path
old='b086c941cc3de3c6da126e15c650f2cd544686c2'
pin='dcc9b50ee837a6099f4e18cac7712f2084f3728a'
original=Path('worker-21-review/regional-b086c94/probes.py').read_text()
namespace={'__name__':'focused_recheck'}
exec(compile(original.replace(old,pin),'original-W21-REGIONAL-F1-at-correction','exec'),namespace)
m,source,fixtures,allow=[namespace[k] for k in ['m','source','fixtures','allow']]
class NoCoercion(unittest.TestCase):
 def test_string_subclass_and_nonstring_unit_do_not_coerce_or_reach_authority(self):
  calls=[]
  class Lexeme(str):
   def __str__(self):raise AssertionError('coercion attempted')
   def __hash__(self):raise AssertionError('unit hashing attempted')
  for value in [Lexeme('regional-cup'),['regional-cup'],{'id':'regional-cup'},1,True,None,'']:
   q=source(unit=value);before=copy.deepcopy(q)
   def authority(e):calls.append(e);return allow(e)
   result=m.convert_chain(q,fixtures(),authority,target_basis='gross')
   self.assertEqual(result['status'],'unknown');self.assertIsNone(result['quantity'])
   self.assertEqual(result['source'],before);self.assertEqual(q,before);self.assertEqual(calls,[])
 def test_valid_chain_control_unchanged(self):
  r=m.convert_chain(source(),fixtures(),allow,target_basis='gross')
  self.assertEqual(r['quantity'],109.6);self.assertTrue(m.shopping_projection(r,required_basis='gross')['ready'])
suite=unittest.TestSuite([namespace['IndependentReview']('test_malformed_observed_unit_is_unknown_not_uncaught_exception')])
suite.addTests(unittest.defaultTestLoader.loadTestsFromTestCase(NoCoercion))
if __name__=='__main__':
 result=unittest.TextTestRunner(verbosity=2).run(suite)
 raise SystemExit(0 if result.wasSuccessful() else 1)
