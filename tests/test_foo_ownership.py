"""Generated private temp layouts only; no installed layout or live dispatcher."""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


guard = load('test_foo_ownership_module', ROOT / 'scripts/foo_ownership.py')
jobs = load('test_foo_dispatcher_module', ROOT / 'scripts/dispatch-foo-job.py')


class OwnershipTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # On00's composed candidate this is the reviewed same-checkout module.
        # Standalone91da author verification explicitly supplies frozen3478 API.
        path = Path(os.environ.get('OFFMENU_TEST_RUNNER_PATHS', ROOT / 'manual-action/runner_paths.py'))
        cls.paths = load('test_frozen_runner_paths', path)

    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        self.root.chmod(0o700)
        self.config = self.root / 'config.json'
        values = {'schema': 'offmenu-runner-layout/1'}
        for key in ('runtime', 'public_staging', 'normalization', 'household'):
            path = self.root / key
            path.mkdir(mode=0o700)
            values[key] = str(path)
        locks = self.root / 'locks'
        locks.mkdir(mode=0o700)
        self.lock = locks / 'manual-runner.lock'
        self.lock.touch(mode=0o600)
        values['lock'] = str(self.lock)
        self.write(self.config, values)
        env = patch.dict(os.environ, {'OFFMENU_RUN_LAYOUT': str(self.config)}, clear=True)
        env.start()
        self.addCleanup(env.stop)
        self.layout = self.paths.resolve_layout(self.root / 'unused', require_lease=False)
        fd = os.open(self.lock, os.O_RDWR)
        self.write(self.layout.runtime / 'layout-admission.json', self.layout.binding(fd))
        binding = self.layout.admission_digest(fd)
        os.close(fd)
        self.request = {'schemaVersion': 1, 'jobId': 'synthetic-test-job', 'profile': 'readiness'}
        self.identity = hashlib.sha256(jobs.canonical({'request': self.request, 'trustedCodeSha': 'a' * 40})).hexdigest()
        self.owner = {'schema': 'offmenu-foo-fallback/1', 'owner': 'actions-fallback',
                      'boundary': 'safe', 'native_thread_id': 'synthetic-native-session',
                      'handoff_id': 'synthetic-handoff', 'handoff_evidence': 'generated-local-boundary',
                      'request_identity': self.identity, 'github_run_id': '123', 'github_run_attempt': '1',
                      'config_sha256': self.layout.config_digest, 'binding_sha256': binding,
                      'expires_unix': int(time.time()) + 600}
        self.owner_path = self.layout.runtime / 'foo-fallback-admission.json'
        self.write(self.owner_path, self.owner)
        self.loader = patch.object(guard, 'load_layout', return_value=self.layout)
        self.load_mock = self.loader.start()
        self.addCleanup(self.loader.stop)

    def write(self, path, value):
        path.write_text(json.dumps(value))
        path.chmod(0o600)

    def acquire(self):
        return guard.acquire(ROOT, self.identity, '123', '1')

    def denied(self):
        with self.assertRaises((ValueError, OSError)):
            with self.acquire():
                self.fail('must not admit')

    def test_missing_selector_never_loads_or_creates(self):
        os.environ.pop('OFFMENU_RUN_LAYOUT')
        self.denied()
        self.load_mock.assert_not_called()

    def test_native_owner_denied_even_idle_with_free_lock(self):
        self.owner['owner'] = 'native'
        self.write(self.owner_path, self.owner)
        self.denied()

    def test_missing_handoff_denied_without_creating_it(self):
        self.owner_path.unlink()
        self.denied()
        self.assertFalse(self.owner_path.exists())

    def test_exact_handoff_identity_and_scope(self):
        for key, wrong in [('boundary', 'idle'), ('request_identity', 'b' * 64),
                           ('github_run_id', '124'), ('github_run_attempt', '2'),
                           ('config_sha256', 'b' * 64), ('binding_sha256', 'b' * 64),
                           ('handoff_evidence', ''), ('native_thread_id', '')]:
            with self.subTest(key=key):
                self.write(self.owner_path, {**self.owner, key: wrong})
                self.denied()

    def test_expired_and_unbounded_handoffs_denied(self):
        for expires in (0, int(time.time()) + 3600, True):
            self.write(self.owner_path, {**self.owner, 'expires_unix': expires})
            self.denied()

    def test_symlink_and_nonprivate_handoff_denied(self):
        target = self.root / 'other'
        self.owner_path.rename(target)
        self.owner_path.symlink_to(target)
        self.denied()
        self.owner_path.unlink()
        target.rename(self.owner_path)
        self.owner_path.chmod(0o644)
        self.denied()

    def test_shared_lock_held_by_native_denies(self):
        import fcntl
        fd = os.open(self.lock, os.O_RDWR)
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            self.denied()
        finally:
            os.close(fd)

    def test_missing_lock_is_not_created(self):
        self.lock.unlink()
        self.denied()
        self.assertFalse(self.lock.exists())

    def test_layout_binding_tamper_denied(self):
        path = self.layout.runtime / 'layout-admission.json'
        self.write(path, {'schema': 'offmenu-runner-layout/1'})
        self.denied()

    def test_config_and_physical_replacement_denied(self):
        with self.acquire() as admitted:
            self.config.write_text(self.config.read_text() + ' ')
            with self.assertRaises(ValueError):
                admitted.verify()

    def test_replaced_root_identity_denied(self):
        with self.acquire() as admitted:
            self.layout.public_staging.rename(self.root / 'old-public')
            self.layout.public_staging.mkdir(mode=0o700)
            with self.assertRaises(ValueError):
                admitted.verify()

    def test_operational_legacy_fixture_selector_cannot_bypass_guard(self):
        os.environ['OFFMENU_RUN_LEGACY_FIXTURE'] = '1'
        self.denied()

    def test_same_checkout_module_load_and_missing_module_refusal(self):
        self.loader.stop()
        code = self.root / 'synthetic-composed-code'
        code.mkdir(mode=0o700)
        (code / 'manual-action').mkdir(mode=0o700)
        with self.assertRaises(OSError):
            guard.load_layout(code)
        (code / 'manual-action' / 'runner_paths.py').write_bytes(Path(self.paths.__file__).read_bytes())
        with guard.acquire(code, self.identity, '123', '1') as admitted:
            admitted.verify()

    def test_replaced_lock_identity_denied(self):
        with self.acquire() as admitted:
            self.lock.rename(self.root / 'old-lock')
            self.lock.touch(mode=0o600)
            with self.assertRaises(ValueError):
                admitted.verify()

    def test_native_reclaim_revokes_held_admission(self):
        with self.acquire() as admitted:
            self.write(self.owner_path, {**self.owner, 'owner': 'native'})
            with self.assertRaises(ValueError):
                admitted.verify()

    def test_valid_scope_does_not_change_admission_and_restores_env(self):
        before = self.owner_path.read_bytes()
        with self.acquire() as admitted:
            self.assertEqual(admitted.child_env()['OFFMENU_RUN_LAYOUT'], str(self.config))
        self.assertNotIn('OFFMENU_RUN_FD', os.environ)
        self.assertEqual(self.owner_path.read_bytes(), before)

    def test_dispatcher_refusal_before_any_output_creation(self):
        out = self.root / 'not-created'
        self.write(self.owner_path, {**self.owner, 'owner': 'native'})
        with patch.object(jobs, 'ownership_guard', side_effect=lambda *args: self.acquire()), patch.object(jobs, 'OUTPUT', out), patch.object(jobs, 'run_profile') as run:
            with self.assertRaisesRegex(jobs.JobError, 'ownership-admission-refused'):
                jobs.execute(self.request, 'a' * 40, ROOT, '123', '1')
            run.assert_not_called()
        self.assertFalse(out.exists())

    def test_direct_child_inherits_bound_shared_lease_and_scrubbed_env(self):
        out = self.root / 'outputs'
        out.mkdir(mode=0o700)
        (out / 'tmp').mkdir(mode=0o700)
        command = [sys.executable, '-B', '-c',
                   "import os,fcntl; fd=int(os.environ['OFFMENU_RUN_FD']); fcntl.flock(fd,fcntl.LOCK_EX|fcntl.LOCK_NB); assert os.environ['OFFMENU_RUN_LAYOUT_BINDING_SHA256']; assert 'GH_TOKEN' not in os.environ"]
        with self.acquire() as admitted, patch.object(jobs, 'ACTIVE_OWNERSHIP', admitted), patch.object(jobs, 'OUTPUT', out):
            result = jobs.run_child(command, ROOT, timeout=3)
        self.assertEqual(result['status'], 'passed')

    def test_admitted_dispatch_and_terminal_reuse_hold_real_shared_lease(self):
        out = self.root / 'outputs'
        with patch.object(jobs, 'ownership_guard', side_effect=lambda *args: self.acquire()), patch.object(jobs, 'OUTPUT', out), patch.object(jobs, 'run_profile', return_value={'schemaVersion': 1, 'status': 'passed', 'steps': []}) as run:
            jobs.execute(self.request, 'a' * 40, ROOT, '123', '1')
            report = jobs.execute(self.request, 'a' * 40, ROOT, '123', '1')
        self.assertEqual(run.call_count, 1)
        self.assertEqual(report['delivery'], 'existing-receipt-no-execution')

    def test_reclaim_during_child_terminates_child_and_preserves_uncertainty(self):
        import threading
        out = self.root / 'outputs'
        out.mkdir(mode=0o700)
        (out / 'tmp').mkdir(mode=0o700)
        def reclaim():
            time.sleep(0.08)
            self.write(self.owner_path, {**self.owner, 'owner': 'native'})
        thread = threading.Thread(target=reclaim)
        with self.acquire() as admitted, patch.object(jobs, 'ACTIVE_OWNERSHIP', admitted), patch.object(jobs, 'OUTPUT', out):
            thread.start()
            try:
                with self.assertRaises(ValueError):
                    jobs.run_child([sys.executable, '-B', '-c', 'import time;time.sleep(5)'], ROOT, timeout=2)
            finally:
                thread.join()

    def test_reclaim_after_both_pipes_close_prevents_late_marker(self):
        import threading
        out = self.root / 'outputs'
        out.mkdir(mode=0o700)
        (out / 'tmp').mkdir(mode=0o700)
        marker = self.root / 'must-not-exist'
        command = [sys.executable, '-B', '-c',
                   'import os,time,pathlib,sys;os.close(1);os.close(2);time.sleep(.6);pathlib.Path(sys.argv[1]).write_text("survived")', str(marker)]
        def reclaim():
            time.sleep(0.12)
            self.write(self.owner_path, {**self.owner, 'owner': 'native'})
        thread = threading.Thread(target=reclaim)
        with self.acquire() as admitted, patch.object(jobs, 'ACTIVE_OWNERSHIP', admitted), patch.object(jobs, 'OUTPUT', out):
            thread.start()
            try:
                with self.assertRaises(ValueError):
                    jobs.run_child(command, ROOT, timeout=2)
            finally:
                thread.join()
        self.assertFalse(marker.exists())

    def test_closed_pipes_still_obey_cancellation_and_deadline(self):
        import threading
        out = self.root / 'outputs'
        out.mkdir(mode=0o700)
        (out / 'tmp').mkdir(mode=0o700)
        for cancel, expected in ((False, 'timeout'), (True, 'cancelled')):
            with self.subTest(expected=expected):
                marker = self.root / ('must-not-exist-' + expected)
                command = [sys.executable, '-B', '-c',
                           'import os,time,pathlib,sys;os.close(1);os.close(2);time.sleep(.6);pathlib.Path(sys.argv[1]).write_text("survived")', str(marker)]
                jobs.CANCEL_EVENT.clear()
                timer = threading.Timer(0.1, jobs.CANCEL_EVENT.set) if cancel else None
                with patch.object(jobs, 'OUTPUT', out):
                    if timer:
                        timer.start()
                    try:
                        result = jobs.run_child(command, ROOT, timeout=2 if cancel else .15)
                    finally:
                        if timer:
                            timer.join()
                        jobs.CANCEL_EVENT.clear()
                self.assertEqual(result['status'], expected)
                self.assertFalse(marker.exists())

    def test_final_revocation_does_not_publish_terminal_receipt(self):
        out = self.root / 'outputs'
        def finish(*args):
            self.write(self.owner_path, {**self.owner, 'owner': 'native'})
            return {'schemaVersion': 1, 'status': 'passed', 'steps': []}
        with patch.object(jobs, 'ownership_guard', side_effect=lambda *args: self.acquire()), patch.object(jobs, 'OUTPUT', out), patch.object(jobs, 'run_profile', side_effect=finish):
            with self.assertRaisesRegex(jobs.JobError, 'ownership-admission-refused'):
                jobs.execute(self.request, 'a' * 40, ROOT, '123', '1')
        receipt = json.loads(next((out / 'job-receipts').glob('*.json')).read_text())
        self.assertEqual(receipt['status'], 'running')
        self.assertEqual(receipt['requestIdentity'], self.identity)


if __name__ == '__main__':
    unittest.main()
