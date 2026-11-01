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
from unittest.mock import Mock, patch

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


# Import the actual standalone bridge with inert SDK modules: no credentials,
# SSH access, Windmill API or package installation is exercised by these tests.
bridge_spec = importlib.util.spec_from_file_location('projected_windmill_bridge',
                                                   MODULE.with_name('windmill_bridge.py'))
bridge = importlib.util.module_from_spec(bridge_spec)
with patch.dict(sys.modules, {'paramiko': Mock(), 'wmill': Mock()}):
    bridge_spec.loader.exec_module(bridge)


class WindmillResourceReceiptTests(unittest.TestCase):
    def fixture(self):
        import test_release_qualification
        value = test_release_qualification.ReleaseQualificationTests(methodName='runTest')
        value.setUp()
        self.addCleanup(value.doCleanups)
        return value

    def test_runner_receipt_projection_qualifies_exact_release_resources_and_hash(self):
        fixture = self.fixture()
        results = [fixture.result(), fixture.result(1)]
        for index, result in enumerate(results):
            path = fixture.root / ('receipt-' + str(index) + '.json')
            original = json.loads(path.read_text())
            service = dict(original, raw_log='PRIVATE', unknown_error={'secret': 'PRIVATE'})
            projected = bridge._job_result('status', original['job_id'], service, 'resources-v1')['receipt']
            self.assertEqual(projected['resources'], original['resources'])
            self.assertEqual(projected['request_sha256'], original['request_sha256'])
            self.assertNotIn('PRIVATE', json.dumps(projected))
            self.assertIsNot(projected['resources'], original['resources'])
            path.write_text(json.dumps(projected))
            result['handoff']['operation']['receipt'] = fixture.ref(path.name)
        self.assertEqual(fixture.aggregate(results)['status'], 'qualified')

    def test_resource_drift_is_never_repaired_from_requested_arguments(self):
        fixture = self.fixture()
        result = fixture.result()
        path = fixture.root / 'receipt-0.json'
        actual = json.loads(path.read_text())
        actual['resources']['memory_bytes'] += 1
        projected = bridge._safe_receipt(actual['job_id'], actual, 'resources-v1')
        self.assertEqual(projected['resources']['memory_bytes'], actual['resources']['memory_bytes'])
        path.write_text(json.dumps(projected))
        result['handoff']['operation']['receipt'] = fixture.ref(path.name)
        with self.assertRaises(ValueError): fixture.aggregate([result])

    def test_missing_resource_fact_is_not_filled_from_main_request(self):
        fixture = self.fixture()
        result = fixture.result()
        raw = json.loads((fixture.root / 'receipt-0.json').read_text())
        requested = raw.pop('resources')
        transport = Mock()
        transport.is_authenticated.return_value = True
        client = Mock()
        client.get_transport.return_value = transport
        with patch.object(bridge.paramiko, 'SSHClient', return_value=client), \
             patch.object(bridge, '_pin'), \
             patch.object(bridge.wmill, 'get_variable', return_value='synthetic-only'), \
             patch.object(bridge, '_drain', return_value=dict(exit_code=0, stdout=json.dumps(raw),
                                      truncated={'stdout': False, 'stderr': False})):
            response = bridge.main(action='run', job_id=raw['job_id'],
                                   command=fixture.plan['checks'][0]['command'],
                                   mode='write', timeout_seconds=raw['timeout_seconds'], resources=requested,
                                   receipt_projection='resources-v1')
        self.assertNotIn('resources', response['receipt'])
        path = fixture.root / 'receipt-0.json';path.write_text(json.dumps(response['receipt']))
        result['handoff']['operation']['receipt'] = fixture.ref(path.name)
        with self.assertRaises(ValueError): fixture.aggregate([result])

    def test_malformed_or_control_resource_values_are_rejected(self):
        import copy
        fixture = self.fixture();fixture.result()
        original = json.loads((fixture.root / 'receipt-0.json').read_text())
        changes = [{'workers': True}, {'workers': 65}, {'overhead_processes': 9},
                   {'cpu_millis': float('nan')}, {'memory_bytes': float('inf')},
                   {'memory_bytes': 42 * 1024**3 + 1}, {'output_bytes': -1}, {'io_slots': 33},
                   {'extra': 'PRIVATE'}, {'read_roots': ['/outside']},
                   {'read_roots': ['/offmenu/../outside']}, {'read_roots': ['/offmenu//data']},
                   {'read_roots': ['/offmenu/data/']}, {'read_roots': ['/offmenu/data\\nsecret']},
                   {'read_roots': ['/offmenu/data'] * 2}, {'read_roots': ['/offmenu/data'] * 33},
                   {'write_roots': []}, {'write_roots': ['/offmenu/tools/delivery/code.py']},
                   {'write_roots': ['/offmenu/scripts/windmill']},
                   {'write_roots': ['/offmenu/data/.offmenu-platform/jobs/job']},
                   {'write_roots': ['/offmenu/data/.offmenu-platform/locks']},
                   {'write_roots': ['/offmenu/data']}, {'read_roots': ['/' + 'a' * 4097]}]
        for change in changes:
            receipt = copy.deepcopy(original);receipt['resources'].update(change)
            with self.subTest(change=change), self.assertRaises(ValueError):
                bridge._safe_receipt(receipt['job_id'], receipt, 'resources-v1')
        receipt = copy.deepcopy(original);del receipt['resources']['io_slots']
        with self.assertRaises(ValueError):bridge._safe_receipt(receipt['job_id'], receipt, 'resources-v1')
        receipt = copy.deepcopy(original);receipt['mode'] = 'read'
        with self.assertRaises(ValueError):bridge._safe_receipt(receipt['job_id'], receipt, 'resources-v1')

    def test_legacy_receipts_and_other_field_validation_are_unchanged(self):
        import windmill_dispatcher
        job = 'offmenu-' + 'a'*48
        legacy = dict(job_id=job, status='succeeded', exit_code=0, child_tree_gone=True)
        self.assertEqual(bridge._safe_receipt(job, dict(legacy, raw_log='PRIVATE')), legacy)
        # The bridge DEFAULT still strips resources, including old unsupported
        # declarations, before the unchanged strict legacy dispatcher sees them.
        response = bridge._job_result('status', job,
                                     dict(legacy, resources={'old': 'private declaration'}))
        self.assertEqual(windmill_dispatcher.compact_result(response)['receipt'], legacy)
        with self.assertRaises(ValueError):bridge._safe_receipt(job, dict(legacy, exit_code=True))
        with self.assertRaises(bridge.OutcomeUnknown):bridge._job_result('status', job,
            dict(legacy, child_tree_gone=False))
        # Legacy dispatcher is untouched and still refuses the new optional field.
        with self.assertRaises(ValueError):windmill_dispatcher._safe_receipt(job,
            dict(legacy, resources={'not': 'a legacy field'}))

    def test_invalid_projection_fails_before_transport_or_credential_access(self):
        for selection in ('raw', '', True, None, {}):
            with self.subTest(selection=selection), \
                 patch.object(bridge.paramiko, 'SSHClient') as connect, \
                 patch.object(bridge.wmill, 'get_variable') as credential:
                with self.assertRaises(bridge.JobValidationFailure):
                    bridge.main(action='status', job_id='synthetic', receipt_projection=selection)
                connect.assert_not_called()
                credential.assert_not_called()

    def test_supported_boundaries_detachment_and_projection_size_are_explicit(self):
        resources = dict(workers=runner.WORKER_CEILING, overhead_processes=runner.OVERHEAD_CEILING,
            cpu_millis=27000, memory_bytes=runner.MEMORY_BUDGET, output_bytes=64*runner.GIB,
            io_slots=runner.IO_BUDGET, read_roots=['/offmenu'], write_roots=[])
        self.assertEqual(bridge._safe_resources(resources, 'read'),
                         runner.validate_resources(resources, 'read'))
        projected = bridge._safe_resources(resources, 'read')
        projected['read_roots'].append('/offmenu/data')
        self.assertEqual(resources['read_roots'], ['/offmenu'])
        # Keep the 600-byte payload while using legal filesystem components.
        long_root = '/'.join(['a'*100]*5 + ['a'*95])
        self.assertEqual(len(long_root), 600)
        too_large = dict(resources, read_roots=['/offmenu/' + long_root + str(n) for n in range(32)])
        runner.validate_resources(too_large, 'read')  # Admission permits this larger declaration.
        with self.assertRaises(ValueError): bridge._safe_resources(too_large, 'read')
        for field, invalid in [('workers',0),('overhead_processes',0),('cpu_millis',27001),
                               ('memory_bytes',1048575),('output_bytes',64*runner.GIB+1),('io_slots',0)]:
            with self.subTest(field=field), self.assertRaises(ValueError):
                bridge._safe_resources(dict(resources, **{field:invalid}), 'read')
