import copy
import importlib.util
import json
from pathlib import Path
import tempfile
import time
import unittest
from unittest.mock import patch

import duckdb_query as q


class Contract(unittest.TestCase):
    def plan(self, **kwargs):
        return q.make_plan('query-01', '/offmenu/data/final.parquet', '/offmenu/queries/report.sql', **kwargs)

    def test_defaults_are_not_maximum(self):
        plan = self.plan()
        self.assertEqual(plan['engine']['threads'], 4)
        self.assertEqual(plan['resources']['workers'], 1)
        self.assertEqual(plan['resources']['cpu_millis'], 4000)
        self.assertEqual(plan['resources']['memory_bytes'], 11 * q.GIB)

    def test_engine_threads_separate_from_processes(self):
        plan = self.plan(threads=12, memory_gib=16)
        self.assertEqual(plan['resources']['cpu_millis'], 12000)
        self.assertEqual(plan['resources']['workers'], 1)
        self.assertEqual(q.validate_plan(plan), plan)

    def test_mutated_reservation_rejected(self):
        for field in ('cpu_millis', 'memory_bytes', 'output_bytes', 'workers'):
            plan = self.plan()
            plan['resources'][field] += 1
            with self.assertRaises(ValueError): q.validate_plan(plan)

    def test_invalid_budget_types_and_limits(self):
        for kwargs in ({'threads': True}, {'threads': 0}, {'threads': 28},
                       {'memory_gib': 44}, {'memory_gib': 43},
                       {'spill_gib': 62, 'result_gib': 2}, {'result_gib': 0}):
            with self.subTest(kwargs=kwargs), self.assertRaises(ValueError):
                self.plan(**kwargs)

    def test_not_sqlite_or_corpus(self):
        for path in ('/offmenu/data/proof.sqlite', '/offmenu-corpus/file.parquet',
                     '/offmenu/../etc/file.parquet', 'file.parquet'):
            with self.assertRaises(ValueError):
                q.make_plan('query-01', path, '/offmenu/query.sql')

    def test_scoped_output_roots(self):
        plan = self.plan()
        self.assertEqual(plan['resources']['write_roots'], [str(q.OUTPUT_ROOT / 'query-01')])
        self.assertNotIn('/offmenu', plan['resources']['read_roots'])

    def test_file_budgets_symlinks_and_stable_identity(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / 'query.sql'
            p.write_bytes(b'SELECT 1')
            self.assertEqual(q.selected_file(p, 100), b'SELECT 1')
            self.assertEqual(q.selected_file(p)['bytes'], 8)
            with self.assertRaises(ValueError): q.selected_file(p, 1)
            link = Path(td) / 'link.sql'; link.symlink_to(p)
            with self.assertRaises(ValueError): q.selected_file(link, 100)

    def test_exclusive_receipt(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / 'receipt.json'
            q.write_new(p, b'{}')
            with self.assertRaises(FileExistsError): q.write_new(p, b'changed')
            self.assertEqual(p.read_bytes(), b'{}')

    def test_runtime_connection_enforces_assigned_cpu(self):
        with patch.object(q.os, 'sched_getaffinity', return_value={1, 2}):
            with self.assertRaisesRegex(ValueError, 'ASSIGNED_CPUS'):
                q.connect(self.plan(threads=3), Path('/unused'))

    def test_new_directory_syncs_parent(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / 'new'
            with patch.object(q, 'sync_dir') as sync:
                q.private_dir(path)
                sync.assert_called_once_with(Path(td))
                q.private_dir(path)
                self.assertEqual(sync.call_count, 1)

    def test_output_guard_interrupts_growth(self):
        with tempfile.TemporaryDirectory() as td:
            target = Path(td) / 'output.parquet'
            class Fake:
                interrupted = False
                def interrupt(self): self.interrupted = True
                def execute(self, sql, args):
                    target.write_bytes(b'x' * 100)
                    for _ in range(40):
                        if self.interrupted: raise RuntimeError('interrupted')
                        time.sleep(.01)
                    raise AssertionError('watcher failed')
            fake = Fake()
            with self.assertRaisesRegex(ValueError, 'RESULT_BUDGET_EXCEEDED'):
                q.bounded_copy(fake, target, 50)
            self.assertTrue(fake.interrupted)

    def test_output_guard_handles_fast_completed_copy(self):
        with tempfile.TemporaryDirectory() as td:
            target = Path(td) / 'output.parquet'
            class Fake:
                def interrupt(self): raise AssertionError('unexpected interrupt')
                def execute(self, sql, args):
                    target.write_bytes(b'x' * 100)
                    return self
                def fetchall(self): return []
            with self.assertRaisesRegex(ValueError, 'RESULT_BUDGET_EXCEEDED'):
                q.bounded_copy(Fake(), target, 50)

    def test_status_not_found_without_writes(self):
        with tempfile.TemporaryDirectory() as td, patch.object(q, 'OUTPUT_ROOT', Path(td)):
            self.assertEqual(q.read_status('absent'), {'job_id': 'absent', 'status': 'not_found'})
            self.assertEqual(list(Path(td).iterdir()), [])


if __name__ == '__main__': unittest.main()
