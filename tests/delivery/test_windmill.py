"""Worker adapter contract without network or a live Windmill installation."""
import errno
import importlib.util
import json
from pathlib import Path
import shlex
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from test_engine import DeliveryFixture
from offmenu.delivery.engine import Engine, writer, DeliveryError

MODULE = Path(__file__).resolve().parents[2] / 'tools/delivery/windmill_entrypoint.py'
spec = importlib.util.spec_from_file_location('windmill_entrypoint', MODULE)
adapter = importlib.util.module_from_spec(spec)
spec.loader.exec_module(adapter)


class WindmillTests(DeliveryFixture):
    def prepare(self):
        state = self.root / '.delivery'
        state.mkdir(exist_ok=True)
        path = state / 'task.json'
        path.write_text(json.dumps(self.task))
        return '.delivery/task.json'

    def test_reviewed_task_runs_and_status_returns_recorded_acceptance(self):
        task_path = self.prepare()
        with patch.object(adapter, 'CHECKOUT_ROOT', str(self.root)):
            self.assertEqual(adapter.main(task_path, 'run')['status'], 'accepted')
            self.assertEqual(adapter.main(task_path)['status'], 'accepted')

    def test_status_rejects_conflicting_task_binding(self):
        task_path = self.prepare()
        with writer(self.root) as state:
            Engine(self.root, state, self.task)
        self.task['owner'] = 'another-owner'
        (self.root / task_path).write_text(json.dumps(self.task))
        with patch.object(adapter, 'CHECKOUT_ROOT', str(self.root)):
            with self.assertRaisesRegex(DeliveryError, 'binding mismatch'):
                adapter.main(task_path)

    def test_relocated_reviewed_task_directory_is_admitted(self):
        task_path = self.prepare()
        directory = self.root / 'tools/delivery'
        directory.mkdir(parents=True)
        (directory / 'task.json').write_text(json.dumps(self.task))
        with patch.object(adapter, 'CHECKOUT_ROOT', str(self.root)):
            self.assertEqual(adapter.main('tools/delivery/task.json')['status'], 'not_accepted')

    def test_retired_task_directory_is_rejected(self):
        self.prepare()
        directory = self.root / 'dev/delivery'
        directory.mkdir(parents=True)
        (directory / 'task.json').write_text(json.dumps(self.task))
        with patch.object(adapter, 'CHECKOUT_ROOT', str(self.root)):
            with self.assertRaisesRegex(ValueError, 'reviewed delivery'):
                adapter.main('dev/delivery/task.json')

    def test_rejects_outside_task_path(self):
        with patch.object(adapter, 'CHECKOUT_ROOT', str(self.root)):
            with self.assertRaisesRegex(ValueError, 'reviewed delivery'):
                adapter.main('../outside.json')


RUNNER = MODULE.with_name('windmill_runner.py')
runner_spec = importlib.util.spec_from_file_location('native_windmill_runner', RUNNER)
runner = importlib.util.module_from_spec(runner_spec)
runner_spec.loader.exec_module(runner)


class WindmillSamplingTests(unittest.TestCase):
    def test_disappearing_child_does_not_abort_capacity_supervision(self):
        # Linux procfs can return ESRCH as well as ENOENT after enumeration.
        for error in (FileNotFoundError(errno.ENOENT, 'gone'),
                      ProcessLookupError(errno.ESRCH, 'gone')):
            with self.subTest(error=type(error).__name__), \
                 patch.object(runner, 'descendants', return_value={123, 456}), \
                 patch.object(runner.Path, 'read_text', side_effect=[error,
                     '456 (child with spaces) ' + ' '.join(['0'] * 21 + ['2'])]):
                usage = runner.capacity_usage()
                self.assertEqual(usage['rss_bytes'], 2 * runner.os.sysconf('SC_PAGE_SIZE'))
                # Keep the conservative enumerated count until the next sample.
                self.assertEqual(usage['processes'], 2)

    def test_other_sampling_errors_still_fail_closed(self):
        for error in (PermissionError(errno.EACCES, 'denied'),
                      OSError(errno.EIO, 'unreadable')):
            with self.subTest(error=type(error).__name__), \
                 patch.object(runner, 'descendants', return_value={123}), \
                 patch.object(runner.Path, 'read_text', side_effect=error):
                with self.assertRaises(type(error)):
                    runner.capacity_usage()


class WindmillRecoveryTests(unittest.TestCase):
    def invoke(self, root, action, command=None):
        argv = [sys.executable, str(RUNNER), '--root', str(root), action,
                '--job-id', 'synthetic-native-recovery']
        if command is not None:
            argv += ['--mode', 'read', '--timeout', '1']
        result = subprocess.run(argv, input=json.dumps({'command': command}) if command else '',
                                text=True, capture_output=True, timeout=8, check=True)
        return json.loads(result.stdout)

    def test_timeout_reopen_retains_identity_without_recomputation(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / 'receipts'
            count = Path(directory) / 'computations'
            child_pid = Path(directory) / 'detached-pid'
            # A detached descendant outlives its wrapper unless subreaper cleanup works.
            body = ('import os,time; from pathlib import Path; '
                    f'Path({str(count)!r}).open("a").write("once\\n"); '
                    'pid=os.fork(); '
                    'os.setsid() if pid == 0 else None; '
                    f'Path({str(child_pid)!r}).write_text(str(os.getpid())) if pid == 0 else None; '
                    'time.sleep(10)')
            command = shlex.join([sys.executable, '-c', body])
            first = self.invoke(root, 'run', command)
            self.assertEqual(first['status'], 'timed_out')
            self.assertTrue(first['child_tree_gone'])
            self.assertFalse(first['reconcile_required'])
            self.assertFalse(Path('/proc', child_pid.read_text()).exists())
            before = count.read_bytes()
            self.assertEqual(before, b'once\n')
            self.assertEqual(self.invoke(root, 'status'), first)
            self.assertEqual(self.invoke(root, 'run', command), first)
            self.assertEqual(count.read_bytes(), before)
            # Changing executor or policy bytes never rebinds a completed ID.
            with patch.object(runner, 'POLICY_BYTES', b'changed policy'):
                self.assertEqual(runner.run(root, first['job_id'], command, 'read', 1)
                                 ['status'], 'id_conflict')
            with patch.object(runner.Path, 'read_bytes', return_value=b'changed runner'):
                self.assertEqual(runner.run(root, first['job_id'], command, 'read', 1)
                                 ['status'], 'id_conflict')
            conflict = self.invoke(root, 'run', command + ' # changed source command')
            self.assertEqual(conflict['status'], 'id_conflict')
            self.assertTrue(conflict['reconcile_required'])
            self.assertEqual(self.invoke(root, 'status'), first)
            self.assertFalse(list((root / 'locks').glob('*.inflight.json')))

    def test_stale_receipt_and_reservation_never_authorize_replay(self):
        with tempfile.TemporaryDirectory() as directory:
            root, job = runner.setup(directory, 'synthetic-native-recovery')
            job.mkdir()
            receipt = job / 'receipt.json'
            runner.atomic(receipt, {'job_id': job.name, 'status': 'running',
                                    'heartbeat_at': 0, 'request_sha256': 'a' * 64})
            marker = root / 'locks/execution-slot-0.inflight.json'
            runner.atomic(marker, {'job_id': job.name, 'mode': 'write'})
            original = receipt.read_bytes(), marker.read_bytes()
            observed = self.invoke(root, 'status')
            self.assertTrue(observed['reconcile_required'])
            self.assertEqual(self.invoke(root, 'run', 'exit 0')['status'], 'id_conflict')
            with patch.object(runner.subprocess, 'Popen', side_effect=AssertionError('replay')):
                result = runner.run(root, 'another-job', 'exit 0', 'write', 1)
            self.assertEqual(result['status'], 'blocked_reconciliation')
            self.assertEqual((receipt.read_bytes(), marker.read_bytes()), original)
