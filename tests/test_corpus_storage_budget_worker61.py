import importlib.util
from pathlib import Path
import tempfile
import os
import subprocess
import sys
import json
from unittest.mock import patch
import unittest

spec = importlib.util.spec_from_file_location('budget61', Path(__file__).resolve().parents[1] / 'tools/data-processing/corpus_storage_budget_worker61.py')
b = importlib.util.module_from_spec(spec)
spec.loader.exec_module(b)


class StorageBudgetTests(unittest.TestCase):
    def plan(self, **changes):
        args = dict(available_bytes=10000, available_inodes=100,
                    reserve_bytes=1000, reserve_inodes=10, fixed_bytes=500,
                    fixed_inodes=5, per_record_bytes=dict(zip(b.COMPONENTS, (100, 20, 30, 50))),
                    per_record_inodes=dict(zip(b.COMPONENTS, (1, 1, 1, 1))),
                    batch_cap_bytes=2500, requested_records=10)
        args.update(changes)
        return b.capacity(**args)

    def test_independent_hand_calculated_boundary(self):
        x = self.plan()  # (2500-500)/200 = 10, inodes allow floor(85/4)=21
        self.assertEqual(x['maximumRecordsArithmetic'], 10)
        self.assertTrue(x['capacityPass'])
        self.assertFalse(self.plan(requested_records=11)['capacityPass'])
        self.assertFalse(x['executionAuthorized'])

    def test_inode_and_reserve_bind_before_bytes(self):
        self.assertEqual(self.plan(available_inodes=34)['maximumRecordsArithmetic'], 4)
        self.assertFalse(self.plan(available_bytes=999)['capacityPass'])
        self.assertFalse(self.plan(fixed_bytes=2501)['capacityPass'])
        self.assertFalse(self.plan(requested_records=0)['capacityPass'])

    def test_unknown_negative_boolean_and_float_refused(self):
        for value in (None, -1, True, 1.5, '100'):
            with self.subTest(value=value), self.assertRaises(b.BudgetRefusal):
                self.plan(fixed_bytes=value)
        with self.assertRaises(b.BudgetRefusal):
            self.plan(per_record_bytes={'output': 100})
        with self.assertRaises(b.BudgetRefusal):
            self.plan(batch_cap_bytes=256 * 1024**2 + 1)

    def test_copies_are_simultaneous_no_discount(self):
        self.assertEqual(self.plan(per_record_bytes=dict(zip(b.COMPONENTS, (100,20,30,250))))['maximumRecordsArithmetic'], 5)

    def test_legacy_unshared_guard_refused(self):
        with self.assertRaises(b.BudgetRefusal):
            b.CappedWriter(8192)

    def test_empty_files_consume_inodes_before_creation(self):
        with tempfile.TemporaryDirectory() as d:
            budget = b.SharedBudget.create(d, cap_inodes=3)
            budget.write('empty', [], 1, 'output')
            self.assertEqual(budget.snapshot()['charged_inodes'], 3)
            with self.assertRaises(b.BudgetRefusal):
                budget.write('refused', [], 1, 'copies')
            self.assertFalse((Path(d)/'refused').exists())
            self.assertGreater((Path(d)/'empty').stat().st_blocks*512, 0)

    def test_byte_envelope_refusal_leaves_no_path(self):
        with tempfile.TemporaryDirectory() as d:
            budget = b.SharedBudget.create(d, cap_bytes=200000)
            initial=budget.snapshot()['charged_bytes']
            with self.assertRaises(b.BudgetRefusal):
                budget.write('oversized', [], 100000, 'output')
            self.assertFalse((Path(d)/'oversized').exists())
            self.assertEqual(budget.snapshot()['charged_bytes'], initial)

    def test_categories_share_cap_no_discount(self):
        with tempfile.TemporaryDirectory() as d:
            budget=b.SharedBudget.create(d, cap_inodes=6)
            for name, category in zip(('out','checkpoint','scratch','copy'), b.COMPONENTS):
                b.SharedBudget(d).write(name,[b'x'],1,category)
            self.assertEqual(budget.snapshot()['charged_inodes'],6)
            with self.assertRaises(b.BudgetRefusal):
                budget.write('fifth',[],1,'copies')
            self.assertFalse((Path(d)/'fifth').exists())

    def test_failure_poison_and_before_chunk_limit(self):
        with tempfile.TemporaryDirectory() as d:
            budget=b.SharedBudget.create(d)
            with self.assertRaises(b.BudgetRefusal):
                budget.write('out',[b'a'*5,b'b'*6],10,'output')
            self.assertEqual((Path(d)/'out').read_bytes()[:11],b'a'*5+b'\0'*6)
            with self.assertRaises(b.BudgetRefusal):
                b.SharedBudget(d).write('new',[],1,'copies')
            self.assertFalse((Path(d)/'new').exists())

    def test_unknown_sqlite_temp_and_uncontrolled_files_refused(self):
        with tempfile.TemporaryDirectory() as d:
            budget=b.SharedBudget.create(d)
            for kind in ('sqlite','journal','temp','subprocess'):
                with self.assertRaises(b.BudgetRefusal):
                    budget.external_writer(kind)
            (Path(d)/'uncontrolled.sqlite').touch()
            with self.assertRaises(b.BudgetRefusal):
                budget.write('controlled',[],1,'output')
            self.assertFalse((Path(d)/'controlled').exists())

    def test_reserve_enforced_before_create(self):
        with tempfile.TemporaryDirectory() as d:
            budget=b.SharedBudget.create(d)
            fs=b.filesystem(d)
            for key,value in (('availableBytes',b.RESERVE_BYTES),('availableInodes',b.RESERVE_INODES)):
                observation=dict(fs);observation[key]=value
                with patch.object(b,'filesystem',return_value=observation), self.assertRaises(b.BudgetRefusal):
                    budget.write(key,[],1,'output')
                self.assertFalse((Path(d)/key).exists())
            self.assertEqual(budget.snapshot()['charged_inodes'],2)

    def test_records_and_fixed_ceilings(self):
        with tempfile.TemporaryDirectory() as d:
            budget=b.SharedBudget.create(d)
            budget.write('first',[b'x'],1,'output',records=1000)
            with self.assertRaises(b.BudgetRefusal):
                budget.write('more',[b'x'],1,'output',records=1)
            self.assertFalse((Path(d)/'more').exists())
        for field,value in (('cap_records',1001),('cap_bytes',238354433),('cap_inodes',4017),('reserve_bytes',1),('reserve_inodes',1)):
            with tempfile.TemporaryDirectory() as d, self.assertRaises(b.BudgetRefusal):
                b.SharedBudget.create(d,**{field:value})
            self.assertFalse((Path(d)/b.SharedBudget.ledger_name).exists())

    def test_atomic_processes_compete_for_last_inode(self):
        for ceilings in ({'cap_inodes':3},{'cap_bytes':220000}):
          with tempfile.TemporaryDirectory() as d:
            b.SharedBudget.create(d,**ceilings)
            source=str(Path(b.__file__).resolve())
            script="""import importlib.util,sys
spec=importlib.util.spec_from_file_location('b',sys.argv[1]);b=importlib.util.module_from_spec(spec);spec.loader.exec_module(b)
try:b.SharedBudget(sys.argv[2]).write(sys.argv[3],[],1,'copies')
except b.BudgetRefusal:sys.exit(2)
"""
            procs=[subprocess.Popen([sys.executable,'-c',script,source,d,name]) for name in ('one','two')]
            self.assertEqual(sorted(p.wait(timeout=10) for p in procs),[0,2])
            self.assertEqual(len([p for p in Path(d).iterdir() if not p.name.startswith('.')]),1)
            self.assertEqual(b.SharedBudget(d).snapshot()['charged_inodes'],3)

    def test_fallocate_failure_keeps_reservation_and_blocks_restart(self):
        with tempfile.TemporaryDirectory() as d:
            budget=b.SharedBudget.create(d)
            with patch.object(b.os,'posix_fallocate',side_effect=OSError('fixture disk full')), self.assertRaises(OSError):
                budget.write('out',[],1,'checkpoint_with_journal')
            with self.assertRaises(b.BudgetRefusal):budget.snapshot()
            self.assertFalse((Path(d)/'next').exists())

    def test_target_escape_and_corrupt_ledger_refused(self):
        with tempfile.TemporaryDirectory() as d:
            budget=b.SharedBudget.create(d)
            for name in ('../escape','/outside','.hidden'):
                with self.assertRaises(b.BudgetRefusal):budget.write(name,[],1,'output')
            budget.path.write_text('{broken')
            with self.assertRaises(b.BudgetRefusal):budget.snapshot()

    def test_historical_measurement_entrypoint_refuses_before_work(self):
        script=Path(b.__file__).with_name('measure_corpus_storage_worker61.py')
        p=subprocess.run([sys.executable,str(script)],capture_output=True,text=True,timeout=10)
        self.assertNotEqual(p.returncode,0)
        self.assertIn('Historical measurement rerun disabled',p.stderr)

    def test_exact_target_and_unavailable_refusal(self):
        with tempfile.TemporaryDirectory() as d:
            self.assertEqual(b.filesystem(d)['target'], str(Path(d).resolve()))
            with self.assertRaises(FileNotFoundError):
                b.filesystem(Path(d)/'missing')


if __name__ == '__main__':
    unittest.main()
