import fcntl
import json
import multiprocessing
import signal
from pathlib import Path
import tempfile
import time
import unittest
from unittest.mock import patch

from test_accepted_reuse import a, response, run, TASK


def hold_lock(path, ready, release):
    with open(path, 'a') as stream:
        fcntl.flock(stream, fcntl.LOCK_EX)
        ready.set()
        release.wait(3)


def stalled_provider(*args):
    time.sleep(3)
    return response()


class DeadlineAndLiveTaskTests(unittest.TestCase):
    def test_waiter_has_finite_outcome_without_duplicate_fallback(self):
        ctx = multiprocessing.get_context('fork')
        with tempfile.TemporaryDirectory() as root:
            key = a.digest(a.canonical(a.provenance(TASK, 'public-fixture-account', 'verified-epoch-1')))
            locks = Path(root)/'locks'
            locks.mkdir()
            ready, release = ctx.Event(), ctx.Event()
            owner = ctx.Process(target=hold_lock, args=(str(locks/key), ready, release))
            owner.start()
            try:
                self.assertTrue(ready.wait(2))
                started = time.monotonic()
                with patch.object(a, '_provider_with_deadline') as provider:
                    result = run(root, wait_seconds=.06)
                self.assertLess(time.monotonic()-started, 1)
                provider.assert_not_called()
                self.assertEqual(result['status'], 'single_flight_wait_timeout')
                self.assertEqual(result['inference_calls'], 0)
                self.assertFalse(result['accepted'])
                self.assertTrue(Path(result['receipt_path']).exists())
                self.assertEqual(list((Path(root)/'accepted').iterdir()), [])
            finally:
                release.set()
                owner.join(2)
                if owner.is_alive():
                    owner.kill()
                    owner.join(.25)

    def test_total_provider_deadline_kills_stalled_child_and_retains_failure(self):
        with tempfile.TemporaryDirectory() as root:
            existing = {p.pid for p in multiprocessing.active_children()}
            started = time.monotonic()
            with patch.object(a, 'main', side_effect=stalled_provider):
                result = run(root, provider_seconds=.08)
            self.assertLess(time.monotonic()-started, 1.5)
            self.assertEqual(result['status'], 'provider_deadline_exceeded')
            self.assertTrue(result['provider_outcome_unknown'])
            self.assertIsNone(result['inference_calls'])
            self.assertFalse(result['accepted'])
            self.assertEqual(list((Path(root)/'accepted').iterdir()), [])
            self.assertTrue(Path(result['receipt_path']).exists())
            self.assertEqual({p.pid for p in multiprocessing.active_children()}, existing)
            # No automatic fallback. A separate explicit call can acquire the lock.
            with patch.object(a, '_provider_with_deadline', return_value=response()) as provider:
                later = run(root)
            provider.assert_called_once()
            self.assertTrue(later['accepted'])

    def test_worker_deadline_does_not_depend_on_supervisor(self):
        ctx = multiprocessing.get_context('fork')
        with tempfile.TemporaryDirectory() as root, patch.object(a, 'main', side_effect=stalled_provider):
            worker = ctx.Process(target=a._provider_child,
                                 args=({}, TASK, str(Path(root)/'result.json'), time.monotonic()+.1))
            worker.start()
            worker.join(1)
            try:
                self.assertFalse(worker.is_alive())
                self.assertIn(worker.exitcode, (-signal.SIGALRM, 124))
                self.assertFalse((Path(root)/'result.json').exists())
            finally:
                if worker.is_alive():
                    worker.kill()
                    worker.join(.25)

    def test_cancellation_is_reraised_and_receipted(self):
        with tempfile.TemporaryDirectory() as root:
            with patch.object(a, '_provider_with_deadline', side_effect=KeyboardInterrupt):
                with self.assertRaises(KeyboardInterrupt):
                    run(root)
            receipts = list((Path(root)/'receipts').iterdir())
            self.assertEqual(len(receipts), 1)
            result = json.loads(receipts[0].read_text())['result']
            self.assertEqual(result['status'], 'cancelled')
            self.assertEqual(result['error_type'], 'KeyboardInterrupt')
            self.assertEqual(list((Path(root)/'accepted').iterdir()), [])

    def test_both_retained_live_task_shapes(self):
        for task in ('capacity_admission_invariants', 'checkpoint_cancellation_boundary'):
            self.assertIn(task, a.TASKS)
            good = [{'name': str(i), 'setup_summary': 'synthetic scenario', 'invariant': 'contract holds'} for i in range(4)]
            self.assertTrue(a.validate(task, response(output=json.dumps(good)))[0])
            for bad in (good[:3], {'tests': good}, [dict(item, expected='extra') for item in good],
                        [dict(item, invariant='') for item in good]):
                self.assertFalse(a.validate(task, response(output=json.dumps(bad)))[0])

    def test_invalid_deadlines_fail_before_provider(self):
        with tempfile.TemporaryDirectory() as root, patch.object(a, '_provider_with_deadline') as provider:
            for options in ({'wait_seconds': float('inf')}, {'provider_seconds': 0},
                            {'provider_seconds': 46}, {'wait_seconds': float('nan')}):
                with self.assertRaises(ValueError):
                    run(root, **options)
            provider.assert_not_called()
