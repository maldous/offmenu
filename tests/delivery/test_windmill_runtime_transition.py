"""Offline runtime installation checks; never mutate a deployed runtime."""
import importlib.util
import json
import os
import subprocess
import sys
import time
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('runtime_stage', ROOT / 'tools/operations/prepare_windmill_runtime.py')
stage = importlib.util.module_from_spec(spec); spec.loader.exec_module(stage)


class Installation(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.source, self.candidate, self.destination = [self.root / x for x in ('source', 'candidate', 'destination')]
        for p in (self.source, self.candidate, self.destination): p.mkdir()
        self.held = ['scripts/windmill/platform_check.py', 'scripts/windmill/storage/store.py']
        (self.candidate / 'repository-standard.json').write_text(json.dumps({'runtime_hold_paths': self.held}))
        for rel in self.held + [stage.POLICY]:
            p = self.source / rel; p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text('{}' if rel == stage.POLICY else '# preserved source\n')
        p = self.candidate / stage.RUNNER; p.parent.mkdir(parents=True); p.write_text('# candidate runner\n')

    def install(self):
        result = stage.stage(self.source, self.candidate, self.destination)
        return self.destination / stage.RUNTIME / result['fingerprint'], result

    def test_reproducible_private_install_preserves_layout(self):
        folder, result = self.install()
        self.assertEqual(len(result['files']), 4)
        self.assertFalse(result['cutover']); self.assertFalse(result['reader_access_qualified'])
        self.assertEqual((folder / stage.POLICY).read_bytes(), (self.source / stage.POLICY).read_bytes())
        self.assertEqual((folder / stage.RUNNER).read_bytes(), (self.candidate / stage.RUNNER).read_bytes())
        self.assertEqual(stage.stage(self.source, self.candidate, self.destination), result)
        self.assertEqual(folder.stat().st_mode & 0o077, 0)

    def test_fifo_source_refused_without_opening(self):
        p = self.source / self.held[0]; p.unlink(); os.mkfifo(p)
        with self.assertRaisesRegex(ValueError, 'Nonregular'): self.install()

    def test_unexpected_fifo_refused(self):
        folder, _ = self.install(); os.mkfifo(folder / 'unexpected')
        with self.assertRaisesRegex(ValueError, 'Nonregular'): stage.verify(folder, [*self.held, stage.RUNNER, stage.POLICY])

    def test_writable_tree_and_file_modes_refused(self):
        folder, _ = self.install(); os.chmod(folder, 0o777)
        with self.assertRaisesRegex(ValueError, 'mode'): stage.verify(folder, [*self.held, stage.RUNNER, stage.POLICY])
        os.chmod(folder, 0o700); os.chmod(folder / self.held[0], 0o666)
        with self.assertRaisesRegex(ValueError, 'mode'): stage.verify(folder, [*self.held, stage.RUNNER, stage.POLICY])

    def test_content_tampering_refused(self):
        folder, _ = self.install(); (folder / self.held[0]).write_text('changed')
        with self.assertRaisesRegex(ValueError, 'content mismatch'): stage.verify(folder, [*self.held, stage.RUNNER, stage.POLICY])

    def test_extra_files_refused(self):
        folder, _ = self.install(); (folder / 'unexpected').write_text('x'); os.chmod(folder / 'unexpected', 0o600)
        with self.assertRaisesRegex(ValueError, 'Unexpected'): stage.verify(folder, [*self.held, stage.RUNNER, stage.POLICY])

    def test_symlink_input_refused(self):
        p = self.source / self.held[0]; p.unlink(); p.symlink_to(self.source / stage.POLICY)
        with self.assertRaisesRegex(ValueError, 'Symlink'): self.install()

    def test_symlink_destination_refused(self):
        (self.destination / '.delivery').symlink_to(self.source, target_is_directory=True)
        with self.assertRaisesRegex(ValueError, 'Symlink'): self.install()

    def test_symlink_installed_payload_refused(self):
        folder, _ = self.install(); p = folder / self.held[0]; p.unlink(); p.symlink_to(self.source / self.held[0])
        with self.assertRaisesRegex(ValueError, 'Symlink'): stage.verify(folder, [*self.held, stage.RUNNER, stage.POLICY])

    def test_partial_existing_install_not_overwritten(self):
        identity = stage.fingerprint(stage.records(stage.payload(self.source, self.candidate)))
        folder = self.destination / stage.RUNTIME / identity; folder.mkdir(parents=True)
        with self.assertRaises(FileNotFoundError): self.install()
        self.assertEqual(list(folder.iterdir()), [])

    def test_invalid_inventory_refused(self):
        (self.candidate / 'repository-standard.json').write_text(json.dumps({'runtime_hold_paths': ['../outside']}))
        with self.assertRaises(ValueError): self.install()

    def test_unsupported_accounting_refused(self):
        (self.source / stage.POLICY).write_text('{"resource_accounting":"unknown"}')
        with self.assertRaisesRegex(ValueError, 'accounting'): self.install()

    def test_incomplete_self_consistent_manifest_refused(self):
        folder, result = self.install()
        with self.assertRaisesRegex(ValueError, 'inventory'):
            stage.verify(folder, [*self.held, stage.RUNNER, stage.POLICY, 'scripts/windmill/missing.py'])

    def test_staging_claim_mutation_refused(self):
        folder, result = self.install(); p = folder / 'manifest.json'
        result['reader_access_qualified'] = True; p.write_text(json.dumps(result))
        with self.assertRaisesRegex(ValueError, 'contract'):
            stage.verify(folder, [*self.held, stage.RUNNER, stage.POLICY])

    def test_manifest_modification_refused(self):
        folder, _ = self.install(); p = folder / 'manifest.json'; value = json.loads(p.read_text())
        value['files'][0]['sha256'] = '0' * 64; p.write_text(json.dumps(value))
        with self.assertRaisesRegex(ValueError, 'identity'): stage.verify(folder, [*self.held, stage.RUNNER, stage.POLICY])


class Admission(unittest.TestCase):
    def setUp(self):
        spec = importlib.util.spec_from_file_location('candidate_runner', ROOT / stage.RUNNER)
        self.runner = importlib.util.module_from_spec(spec); spec.loader.exec_module(self.runner)
        self.request = {'workers': 1, 'overhead_processes': 1, 'cpu_millis': 1000,
                        'memory_bytes': 1024**2, 'output_bytes': 0, 'io_slots': 1,
                        'read_roots': ['/offmenu/data'], 'write_roots': []}

    def test_runtime_roots_descendants_and_ancestors_protected(self):
        for root in ['/offmenu/.delivery/windmill-runtime', '/offmenu/.delivery/windmill-runtime/pin/file',
                     '/offmenu/.delivery', '/offmenu/.offmenu-runtime',
                     '/offmenu/.offmenu-runtime/pin/policy', '/offmenu']:
            with self.subTest(root=root), self.assertRaisesRegex(ValueError, 'CoordinatorWrite'):
                self.runner.validate_resources(dict(self.request, write_roots=[root]), 'write')

    def test_old_receipt_status_cancel_and_changed_runner_conflict(self):
        with tempfile.TemporaryDirectory() as t:
            root, directory = self.runner.setup(t, 'old-job'); directory.mkdir()
            receipt = {'job_id': 'old-job', 'status': 'succeeded', 'child_tree_gone': True,
                       'request_sha256': '0'*64}
            (directory / 'receipt.json').write_text(json.dumps(receipt))
            before = (directory / 'receipt.json').read_bytes()
            self.assertEqual(self.runner.status(root, 'old-job'), receipt)
            self.assertEqual(self.runner.cancel(root, 'old-job'), receipt)
            with patch.object(self.runner.subprocess, 'Popen') as launch:
                result = self.runner.run(root, 'old-job', 'echo never-run', 'read', 1)
                self.assertEqual(result['status'], 'id_conflict'); launch.assert_not_called()
            self.assertEqual((directory / 'receipt.json').read_bytes(), before)

    def test_actual_policy_modes_initialize_budgets(self):
        for mode in ['reserved-maxima-v1', 'observed-host-v1', 'unsupported']:
            with self.subTest(mode=mode), tempfile.TemporaryDirectory() as t:
                root = Path(t); p = root / stage.RUNNER; p.parent.mkdir(parents=True)
                p.write_bytes((ROOT / stage.RUNNER).read_bytes())
                policy = json.loads((ROOT / stage.POLICY).read_text()); policy['resource_accounting'] = mode
                (root / stage.POLICY).write_text(json.dumps(policy))
                spec = importlib.util.spec_from_file_location('mode_runner', p)
                module = importlib.util.module_from_spec(spec)
                if mode == 'unsupported':
                    with self.assertRaisesRegex(ValueError, 'InvalidResourceAccounting'): spec.loader.exec_module(module)
                    continue
                spec.loader.exec_module(module)
                observed = mode == 'observed-host-v1'
                self.assertEqual(module.OBSERVED_HOST, observed)
                self.assertEqual(module.MEMORY_BUDGET, policy['host']['memory_budget_bytes'] -
                                 (0 if observed else policy['symphony']['memory_budget_bytes']))
                self.assertEqual(module.IO_BUDGET, policy['host']['io_slots'] -
                                 (0 if observed else policy['symphony']['io_slots']))

    def test_reserved_mode_retains_aggregate_accounting(self):
        with patch.object(self.runner, 'OBSERVED_HOST', False):
            self.assertEqual(self.runner.decide(self.request, [self.request] * 31, 31, 100*1024**3, 1000*1024**3),
                             'capacity_cpu_reserved')

    def test_observed_mode_preserves_installed_per_job_behavior(self):
        with patch.object(self.runner, 'OBSERVED_HOST', True), patch.object(self.runner, 'IO_BUDGET', 40):
            self.assertIsNone(self.runner.decide(self.request, [self.request] * 31, 31, 100*1024**3, 1000*1024**3))
            self.assertEqual(self.runner.decide(self.request, [self.request] * 32, 31, 100*1024**3, 1000*1024**3),
                             'capacity_slots_active')




class InstallationPlan(unittest.TestCase):
    def setUp(self):
        spec = importlib.util.spec_from_file_location('runtime_install', ROOT / 'tools/operations/install_windmill_runtime.py')
        self.installer = importlib.util.module_from_spec(spec); spec.loader.exec_module(self.installer)
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name); self.source = self.root / 'source'; self.source.mkdir()
        self.candidate = self.root / 'candidate'; self.candidate.mkdir()
        self.destination = self.root / 'destination'; self.destination.mkdir()
        held = [*self.installer.SELECTED[2:], 'scripts/windmill/private-receipt.json']
        (self.candidate / 'repository-standard.json').write_text(json.dumps({'runtime_hold_paths': held}))
        for relative in [*held, stage.POLICY]:
            p = self.source / relative; p.parent.mkdir(parents=True, exist_ok=True); p.write_text('{}')
        p = self.candidate / stage.RUNNER; p.parent.mkdir(parents=True); p.write_text('# source\n')
        result = stage.stage(self.source, self.candidate, self.destination)
        self.fingerprint = result['fingerprint']; self.staged = self.destination / stage.RUNTIME / self.fingerprint

    def test_plan_excludes_opaque_receipts(self):
        plan, files = self.installer.plan(self.staged, self.candidate, self.fingerprint)
        self.assertEqual(set(files), set(self.installer.SELECTED))
        self.assertEqual(len(plan['files']), 4)
        self.assertFalse(plan['consumer_cutover'])
        self.assertEqual(plan['reader_uid'], 985)
        self.assertFalse((self.destination / self.installer.LOCATION).exists())

    def test_selected_bytes_race_refused(self):
        original = self.installer.prepare.regular
        counts = {}
        def changing(path):
            key = str(path); counts[key] = counts.get(key, 0) + 1
            data = original(path)
            return data + b'changed' if key == str(self.staged / stage.RUNNER) and counts[key] > 1 else data
        with patch.object(self.installer.prepare, 'regular', side_effect=changing):
            with self.assertRaisesRegex(ValueError, 'changed after verification'):
                self.installer.plan(self.staged, self.candidate, self.fingerprint)

    def test_wrong_source_pin_refused(self):
        with self.assertRaisesRegex(ValueError, 'fingerprint'):
            self.installer.plan(self.staged, self.candidate, '0'*64)

    def test_acl_contract_rejects_write_grant(self):
        output = 'user::rwx\nuser:985:rwx\ngroup::---\nmask::rwx\nother::---\n'
        with patch.object(self.installer.subprocess, 'check_output', return_value=output):
            with self.assertRaisesRegex(ValueError, 'ACL'):
                self.installer.inspect_acl(self.staged, True)

    def test_create_only_install_with_mock_permissions(self):
        with patch.object(self.installer, 'acl'), patch.object(self.installer, 'inspect_acl'):
            first = self.installer.install(self.staged, self.candidate, self.destination, self.fingerprint)
            second = self.installer.install(self.staged, self.candidate, self.destination, self.fingerprint)
            self.assertEqual(first, second)
            folder = self.destination / self.installer.LOCATION / first['fingerprint']
            self.assertFalse((folder / 'scripts/windmill/private-receipt.json').exists())
            (folder / stage.RUNNER).write_text('changed')
            with self.assertRaisesRegex(ValueError, 'content'):
                self.installer.install(self.staged, self.candidate, self.destination, self.fingerprint)

    def test_partial_install_refused_without_repair(self):
        plan, _ = self.installer.plan(self.staged, self.candidate, self.fingerprint)
        folder = self.destination / self.installer.LOCATION / plan['fingerprint']; folder.mkdir(parents=True)
        with patch.object(self.installer, 'acl'), patch.object(self.installer, 'inspect_acl'):
            with self.assertRaises(FileNotFoundError):
                self.installer.install(self.staged, self.candidate, self.destination, self.fingerprint)
        self.assertEqual(list(folder.iterdir()), [])


class RuntimeProcesses(unittest.TestCase):
    """Actual child lifecycle checks against private synthetic state only."""
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name); self.runtime = self.root / 'runtime'
        self.runner = self.runtime / stage.RUNNER; self.runner.parent.mkdir(parents=True)
        self.runner.write_bytes((ROOT / stage.RUNNER).read_bytes())
        policy = json.loads((ROOT / stage.POLICY).read_text()); policy['resource_accounting'] = 'observed-host-v1'
        # Synthetic fixtures must not inherit production host reserves.
        policy['host'].update(cpu_reserve=0, memory_reserve_bytes=0, disk_reserve_bytes=0,
                              memory_budget_bytes=1024**3, io_slots=8)
        policy['symphony'].update(cpu_budget_millis=0, memory_budget_bytes=0, io_slots=0)
        (self.runtime / stage.POLICY).write_text(json.dumps(policy))
        self.state = self.root / 'state'; self.children = []
        self.addCleanup(self.reap)
        self.resources = {'workers': 1, 'overhead_processes': 1, 'cpu_millis': 1,
                          'memory_bytes': 16*1024**2, 'output_bytes': 0, 'io_slots': 1,
                          'read_roots': ['/offmenu/data'], 'write_roots': []}

    def reap(self):
        for child in self.children:
            if child.poll() is None:
                child.terminate()
            try: child.communicate(timeout=8)
            except subprocess.TimeoutExpired:
                child.kill(); child.communicate(timeout=5)

    def start(self, job, command='while [ ! -f release ]; do sleep 0.02; done', resources=True, mode='read', timeout=8):
        args = [sys.executable, '-B', str(self.runner), '--root', str(self.state),
                'run', '--job-id', job, '--mode', mode, '--timeout', str(timeout)]
        child = subprocess.Popen(args, cwd=self.root, stdin=subprocess.PIPE,
                                 stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        payload = {'command': command}
        if resources: payload['resources'] = self.resources
        child.stdin.write(json.dumps(payload)); child.stdin.close(); child.stdin = None
        self.children.append(child); return child

    def finish(self, child):
        out, err = child.communicate(timeout=10)
        self.assertEqual(child.returncode, 0, err)
        return json.loads(out)

    def await_running(self, job):
        path = self.state / 'jobs' / job / 'receipt.json'
        for _ in range(100):
            if path.exists() and json.loads(path.read_text()).get('status') == 'running': return
            time.sleep(0.02)
        self.fail('Synthetic child did not enter running state')

    def test_two_capacity_reads_complete_and_release_markers(self):
        one = self.start('one'); self.await_running('one')
        two = self.start('two'); self.await_running('two')
        self.assertIsNone(one.poll()); self.assertIsNone(two.poll())
        (self.root / 'release').write_text('release both readers')
        for child in [one, two]:
            result = self.finish(child)
            self.assertEqual(result['status'], 'succeeded'); self.assertTrue(result['child_tree_gone'])
        self.assertFalse(list((self.state / 'locks').glob('*.inflight.json')))

    def test_legacy_writer_blocks_capacity_without_duplicate_execution(self):
        legacy = self.start('legacy', resources=False, mode='write'); self.await_running('legacy')
        candidate = self.finish(self.start('candidate'))
        self.assertEqual(candidate['status'], 'busy')
        self.assertFalse(candidate['reserved'])
        self.assertIsNone(legacy.poll())
        (self.root / 'release').write_text('release legacy writer')
        self.assertEqual(self.finish(legacy)['status'], 'succeeded')

    def test_timeout_reaps_child_and_releases_marker(self):
        result = self.finish(self.start('timeout', command='sleep 3', timeout=1))
        self.assertEqual(result['status'], 'timed_out'); self.assertTrue(result['child_tree_gone'])
        self.assertFalse(list((self.state / 'locks').glob('*.inflight.json')))

    def test_cancel_preserves_receipt_and_releases_marker(self):
        child = self.start('cancel', command='sleep 3'); self.await_running('cancel')
        result = json.loads(subprocess.check_output([sys.executable, '-B', str(self.runner),
            '--root', str(self.state), 'cancel', '--job-id', 'cancel'], text=True))
        self.assertEqual(result['status'], 'cancellation_requested')
        final = self.finish(child)
        self.assertEqual(final['status'], 'cancelled'); self.assertTrue(final['child_tree_gone'])
        self.assertFalse(list((self.state / 'locks').glob('*.inflight.json')))


if __name__ == "__main__":
    unittest.main()
