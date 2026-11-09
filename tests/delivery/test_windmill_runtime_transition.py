"""Offline runtime installation checks; never mutate a deployed runtime."""
import importlib.util
import json
import os
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


if __name__ == "__main__":
    unittest.main()
