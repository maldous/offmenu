import sys
import unittest
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'candidate/scripts'),str(ROOT/'candidate/tests')]
import exercise_source_scoped_consumer as P
import test_source_scoped_consumer as F
from derive_north_star_bulk import sha_file

class IndependentProbeTests(unittest.TestCase):
    def setUp(self):
        self.fixture=F.SourceConsumerTests('test_actual_value_context_and_restored_basis');self.fixture.setUp()
    def tearDown(self):self.fixture.tearDown()
    def exercise(self,**kwargs):
        f=self.fixture
        return P.exercise(f.source,f.bulk,f.basis,sha_file(f.bulk/'manifest.json'),sha_file(f.basis/'manifest.json'),**kwargs)
    def test_selection_order_uses_existing_index_without_temp_sort(self):
        rows=self.fixture.reader.index.execute('EXPLAIN QUERY PLAN '+P.SQL,(1024,)).fetchall()
        self.assertFalse(any('TEMP B-TREE' in row[-1].upper() for row in rows),rows)
    def test_changed_admission_flags_do_not_create_success_receipt(self):
        original=P.SourceScopedConsumer.lookup
        def altered(reader,*args,**kwargs):
            result=original(reader,*args,**kwargs)
            if kwargs.get('include_candidates') is True:result['automaticPlanningEligible']=True
            return result
        with patch.object(P.SourceScopedConsumer,'lookup',altered):
            with self.assertRaisesRegex(ValueError,'admission boundary'):self.exercise()
    def test_elapsed_deadline_during_initialization_cannot_mint_success(self):
        calls=[0]
        def clock():
            calls[0]+=1
            return 0 if calls[0]==1 else 10000
        with patch.object(P.time,'monotonic',clock):
            with self.assertRaises(TimeoutError):self.exercise(seconds=1)

if __name__=='__main__':unittest.main()
