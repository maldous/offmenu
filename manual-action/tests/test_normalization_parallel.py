"""Generated public fixtures only; no host corpus, file source or AI route."""
import copy
from concurrent.futures import Future
from concurrent.futures.process import BrokenProcessPool
import json
import multiprocessing
import os
from pathlib import Path
import sys
import time
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from normalization_api import Versions
from normalization_core import artifact_digest, digest, run_rules
import normalization_parallel as parallel


def fixture(index, domain='ingredients', size=0):
    payload = {'id': str(index), 'name': 'Generated public ingredient ' + str(index),
               'language': 'en', 'quantity': '125', 'unit': 'g'}
    if domain == 'recipes':
        payload.update(kind='recipe', title=payload['name'], ingredients=[
            {'id': 'generated-beans', 'source_name_text': 'beans', 'quantity': '125', 'unit': 'g', 'raw_text': '125 g beans', 'ordinal': 0}],
            steps=[{'id': 'generated-step-' + str(i), 'raw_text': text, 'ordinal': i}
                   for i, text in enumerate(('Mix beans with water.', 'Cook for 10 minutes.', 'Serve.'))])
    if size:
        payload['name'] += 'x' * size
    return {'domain': domain, 'source_key': 'generated-public-only',
            'source_version': 'generated-v1', 'record_id': str(index),
            'content_sha256': digest(payload), 'payload': payload,
            'provenance': {'rights_status': 'unverified'}}


def expected(record, versions=None):
    artifact = run_rules(record, versions=versions)
    full_hash = artifact_digest(artifact)
    del artifact['source_original']
    return {'source': artifact['source'], 'artifact': artifact,
            'artifact_sha256': full_hash, 'error_code': None}


def block_worker(seconds):
    time.sleep(seconds)
    return os.getpid()


class RulesParallelTests(unittest.TestCase):
    def test_exact_core_output_all_six_public_domains_and_persistent_pool(self):
        records = [fixture(i, domain) for i, domain in enumerate(sorted(parallel.PUBLIC_DOMAINS))]
        originals = copy.deepcopy(records)
        version = Versions(model_version='generated-not-a-real-model', prompt_version='generated-v1')
        with parallel.RulesExecutor(workers=2) as executor:
            self.assertEqual(executor.actual_workers, 0)
            first = executor.run_batch(records, version)
            pool = executor._pool
            pids = set(executor.stats.worker_pids)
            second = executor.run_batch(records, version)
            self.assertIs(executor._pool, pool)
            self.assertTrue(pids <= executor.stats.worker_pids)
            self.assertEqual(first, [expected(record, version) for record in records])
            self.assertEqual(first, second)
            self.assertGreaterEqual(executor.actual_workers, 1)
            self.assertTrue(all(pid != os.getpid() for pid in executor.stats.worker_pids))
            self.assertEqual(executor._pool._mp_context.get_start_method(), 'spawn')
        self.assertEqual(records, originals)
        for value in first:
            self.assertNotIn('source_original', value['artifact'])
            self.assertEqual(value['artifact']['review']['status'], 'pendingreview')
            self.assertEqual(value['artifact']['gold_status'], 'blocked')

    def test_household_and_invalid_records_never_enter_worker(self):
        inventory = fixture(1, 'inventory')
        inventory['payload'] = {'private': object()}  # Cannot be serialized at all.
        with parallel.RulesExecutor(workers=2) as executor:
            with patch.object(executor, '_ensure_pool', side_effect=AssertionError('no worker admission')):
                results = executor.run_batch([inventory, None, fixture(2, 'user_profiles')])
            self.assertEqual(executor.actual_workers, 0)
        self.assertTrue(all(row['error_code'] == 'outside_public_domain' for row in results))
        self.assertNotIn('private', json.dumps(results))

    def test_bad_hash_isolated_and_source_order_exact(self):
        records = [fixture(i) for i in range(20)]
        records[5]['content_sha256'] = '0' * 64
        with parallel.RulesExecutor(workers=2) as executor:
            output = executor.run_batch(records)
        self.assertEqual([row['source']['record_id'] for row in output], [str(i) for i in range(20)])
        self.assertEqual(output[5]['error_code'], 'source_content_hash_mismatch')
        self.assertIsNone(output[5]['artifact'])
        self.assertEqual(sum(row['error_code'] is None for row in output), 19)

    def test_parent_admission_row_input_and_output_caps(self):
        with parallel.RulesExecutor(workers=2, max_input_bytes=16384, max_output_bytes=16384) as executor:
            with self.assertRaisesRegex(parallel.RulesBatchLimitError, 'rules_batch_row_limit'):
                executor.run_batch(None for i in range(129))
            self.assertIsNone(executor._pool)
            with self.assertRaisesRegex(parallel.RulesBatchLimitError, 'rules_batch_input_limit'):
                executor.run_batch([fixture(i, size=8000) for i in range(3)])
            self.assertIsNone(executor._pool)
            oversized = executor.run_batch([fixture(1, size=20000)])
            self.assertEqual(oversized[0]['error_code'], 'rules_input_limit')
            self.assertEqual(executor.actual_workers, 0)
            with self.assertRaisesRegex(parallel.RulesBatchLimitError, 'rules_batch_output_limit'):
                executor.run_batch([fixture(i) for i in range(10)])
            self.assertIsNone(executor._pool)
            # Overflow closes its pending work; smaller retries get clean results.
            self.assertEqual(executor.run_batch([fixture(100)])[0], expected(fixture(100)))

    def test_individual_output_cap_is_finite_error_not_truncation(self):
        record = fixture(1, size=20000)
        with parallel.RulesExecutor(workers=1, max_input_bytes=65536,
                                    max_output_bytes=16384) as executor:
            results = executor.run_batch([record])
        self.assertEqual(results[0]['error_code'], 'rules_output_limit')
        self.assertIsNone(results[0]['artifact'])
        self.assertLess(len(json.dumps(results)), 16384)

    def test_unexpected_rules_error_does_not_echo_payload_or_exception(self):
        record = fixture(1)
        secret_marker = 'generated-marker-never-returned-in-error'
        with patch('normalization_core.run_rules', side_effect=RuntimeError(secret_marker)):
            result = parallel._compact(parallel._encoded(record), Versions().as_dict())
        self.assertEqual(result['error_code'], 'rules_execution_error')
        self.assertNotIn(secret_marker, json.dumps(result))

    def test_resource_failure_is_batch_fault_never_durable_row_error(self):
        record = fixture(1)
        marker = 'generated-private-resource-context'
        for error in (MemoryError(marker), OSError(marker)):
            with self.subTest(error=type(error).__name__):
                with patch('normalization_core.run_rules', side_effect=error):
                    with self.assertRaisesRegex(parallel.RulesWorkerError, '^rules_worker_resource_failure$'):
                        parallel._compact(parallel._encoded(record), Versions().as_dict())
                with patch.object(parallel, '_compact', side_effect=error):
                    with self.assertRaisesRegex(parallel.RulesWorkerError, '^rules_worker_resource_failure$'):
                        parallel._run_task([(0, parallel._encoded(record))], Versions().as_dict(), 16384)
        with parallel.RulesExecutor(workers=1) as executor:
            executor.run_batch([record])
            child = list(executor._pool._processes.values())[0]
            with patch.object(executor, '_collect', side_effect=MemoryError(marker)):
                with self.assertRaisesRegex(parallel.RulesWorkerError, '^rules_worker_resource_failure$'):
                    executor.run_batch([record])
            self.assertFalse(child.is_alive())
            self.assertIsNone(executor._pool)
            # A later authorized retry evaluates the still-uncommitted record.
            self.assertEqual(executor.run_batch([record]), [expected(record)])

    def test_pure_worker_opens_no_db_file_or_network(self):
        record = fixture(1)
        with patch('sqlite3.connect', side_effect=AssertionError('no DB')), \
             patch('builtins.open', side_effect=AssertionError('no file')), \
             patch('socket.socket', side_effect=AssertionError('no network')):
            result = parallel._compact(parallel._encoded(record), Versions().as_dict())
        self.assertIsNone(result['error_code'])

    def test_broken_worker_retries_only_pure_batch_once(self):
        record = fixture(1)
        with parallel.RulesExecutor(workers=1) as executor:
            real_collect = executor._collect
            calls = []
            def flaky(*args):
                calls.append(1)
                if len(calls) == 1:
                    raise BrokenProcessPool('generated-private-context')
                return real_collect(*args)
            with patch.object(executor, '_collect', side_effect=flaky):
                result = executor.run_batch([record])
            self.assertEqual(result, [expected(record)])
            self.assertEqual(executor.stats.worker_restarts, 1)
            with patch.object(executor, '_collect', side_effect=BrokenProcessPool('do-not-return')):
                with self.assertRaisesRegex(RuntimeError, '^rules_worker_pool_failed$'):
                    executor.run_batch([record])

    def test_real_worker_death_recovers_persistent_executor(self):
        with parallel.RulesExecutor(workers=1) as executor:
            executor.run_batch([fixture(1)])
            processes = list(executor._pool._processes.values())
            processes[0].kill()
            processes[0].join(2)
            self.assertEqual(executor.run_batch([fixture(2)]), [expected(fixture(2))])
            self.assertEqual(executor.stats.worker_restarts, 1)

    def test_cancel_interrupts_running_child_and_cleans_pool(self):
        class Cancelled(Exception):
            pass
        cancel_at = [float('inf')]
        def check():
            if time.monotonic() >= cancel_at[0]:
                raise Cancelled('generated-cancel')
        executor = parallel.RulesExecutor(workers=1, check_cancel=check)
        executor.run_batch([fixture(0)])
        child = list(executor._pool._processes.values())[0]
        blocker = executor._pool.submit(block_worker, 30)
        cancel_at[0] = time.monotonic() + 0.2
        started = time.monotonic()
        with self.assertRaises(Cancelled):
            executor.run_batch([fixture(1)])
        self.assertLess(time.monotonic() - started, 3)
        self.assertFalse(child.is_alive())
        self.assertIsNone(executor._pool)
        executor.close()

    def test_admission_bound_and_inverted_completion_still_ordered(self):
        futures, sizes = [], []
        class FakePool:
            _processes = {}
            def submit(self, fn, task, version_map, cap):
                future = Future()
                futures.append((future, task, version_map, cap))
                sizes.append(len(task))
                # Complete tasks in reverse submission order once window fills.
                if len(futures) == 4:
                    for pending, frames, versions, output_cap in reversed(futures):
                        pending.set_result(parallel._run_task(frames, versions, output_cap))
                return future
            def shutdown(self, **kwargs):
                pass
        with parallel.RulesExecutor(workers=2) as executor:
            pool = FakePool()
            executor._pool = pool
            results = executor.run_batch([fixture(i) for i in range(128)])
            self.assertEqual(executor.stats.peak_inflight_tasks, 4)
            self.assertEqual(sum(sizes), 128)
            self.assertEqual([r['source']['record_id'] for r in results], [str(i) for i in range(128)])

    def test_defaults_resource_caps_and_bad_configuration(self):
        with patch('os.sched_getaffinity', return_value=set(range(24))):
            self.assertEqual(parallel.available_workers(), 16)
            self.assertEqual(parallel.available_workers(100), 22)
        for kwargs in ({'workers': 0}, {'workers': True}, {'max_batch_rows': 129},
                       {'max_input_bytes': 5}, {'workers': 1, 'max_inflight_tasks': 3}):
            with self.assertRaises(ValueError):
                parallel.RulesExecutor(**kwargs)


if __name__ == '__main__':
    unittest.main()
