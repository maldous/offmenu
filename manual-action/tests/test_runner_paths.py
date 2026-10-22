"""Synthetic path-layout checks; no runner, corpus, or retained state is opened."""
from __future__ import annotations

import fcntl
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch


PACKAGE = Path(__file__).resolve().parents[1]


def load_module():
    spec = importlib.util.spec_from_file_location('runner_paths', PACKAGE / 'runner_paths.py')
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class RunnerPathsTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.base = Path(self.temp.name)
        self.legacy = self.base / 'legacy-state'
        self.module = load_module()

    def tearDown(self):
        self.temp.cleanup()

    def private_dir(self, name):
        path = self.base / name
        path.mkdir(mode=0o700)
        os.chmod(path, 0o700)
        return path

    def layout_config(self, *, overlap=False, config_mode=0o600, lock=True, suffix=''):
        runtime = self.private_dir('runtime' + suffix)
        public = runtime if overlap else self.private_dir('public' + suffix)
        normalization = self.private_dir('normalization' + suffix)
        household = self.private_dir('household' + suffix)
        locks = self.private_dir('locks' + suffix)
        lock_path = locks / 'singleton.lock'
        if lock:
            fd = os.open(lock_path, os.O_CREAT | os.O_EXCL | os.O_RDWR, 0o600)
            os.close(fd)
        value = {
            'schema': 'offmenu-runner-layout/1',
            'runtime': str(runtime),
            'public_staging': str(public),
            'normalization': str(normalization),
            'household': str(household),
            'lock': str(lock_path),
        }
        config = self.base / ('layout' + suffix + '.json')
        config.write_text(json.dumps(value, sort_keys=True), encoding='utf-8')
        os.chmod(config, config_mode)
        return config, value

    def resolve(self, config, *, require_lease=False, extra=None):
        env = {'OFFMENU_RUN_LAYOUT': str(config)}
        if extra:
            env.update(extra)
        with patch.dict(os.environ, env, clear=True):
            return self.module.resolve_layout(self.legacy, require_lease=require_lease)

    def test_missing_selector_refuses_before_legacy_state_or_lock_creation(self):
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaisesRegex(ValueError, '^runner_layout_required$'):
                self.module.resolve_layout(self.legacy, require_lease=False)
        self.assertFalse(self.legacy.exists())
        self.assertEqual(list(self.base.glob('*.lock')), [])

    def test_explicit_legacy_fixture_is_the_only_legacy_route(self):
        with patch.dict(os.environ, {'OFFMENU_RUN_LEGACY_FIXTURE': '1'}, clear=True):
            layout = self.module.resolve_layout(self.legacy / 'ingest', require_lease=False)
        self.assertTrue(layout.legacy)
        self.assertEqual(layout.runtime, self.legacy)
        self.assertEqual(layout.ingest, self.legacy / 'ingest')
        self.assertEqual(layout.public_staging, self.legacy / 'ingest' / 'staging')
        self.assertEqual(layout.normalization, self.legacy / 'ingest' / 'normalization-private')
        self.assertEqual(layout.household, self.legacy / 'ingest' / 'private-household')

    def test_explicit_layout_routes_public_private_and_normalization_paths(self):
        config, paths = self.layout_config()
        layout = self.resolve(config)
        self.assertFalse(layout.legacy)
        self.assertEqual(layout.runtime, Path(paths['runtime']))
        self.assertEqual(layout.ingest, Path(paths['runtime']) / 'ingest')
        self.assertEqual(layout.domain_path('barcodes'), Path(paths['public_staging']) / 'barcodes.sqlite3')
        self.assertEqual(layout.domain_path('inventory'), Path(paths['household']) / 'staging' / 'inventory.sqlite3')
        self.assertEqual(layout.normalization, Path(paths['normalization']))
        self.assertEqual(layout.lock, Path(paths['lock']))
        binding = layout.binding()
        self.assertEqual(binding['schema'], 'offmenu-runner-layout/1')
        self.assertEqual(binding['config_sha256'], layout.config_digest)
        self.assertEqual(binding['roots']['runtime'], str(layout.runtime))

    def test_partial_overlap_and_bad_permissions_refuse(self):
        config, paths = self.layout_config(overlap=True)
        with self.assertRaises(ValueError):
            self.resolve(config)
        config, paths = self.layout_config(suffix='partial')
        partial = {'schema': 'offmenu-runner-layout/1', **paths}
        del partial['household']
        config.write_text(json.dumps(partial, sort_keys=True), encoding='utf-8')
        os.chmod(config, 0o600)
        with self.assertRaises(ValueError):
            self.resolve(config)
        config, paths = self.layout_config(suffix='modes')
        os.chmod(Path(paths['normalization']), 0o755)
        with self.assertRaises(ValueError):
            self.resolve(config)
        os.chmod(Path(paths['normalization']), 0o700)
        os.chmod(config, 0o644)
        with self.assertRaises(ValueError):
            self.resolve(config)

    def test_symlink_root_refuses(self):
        config, paths = self.layout_config()
        replacement = self.private_dir('replacement')
        public = Path(paths['public_staging'])
        public.rmdir()
        public.symlink_to(replacement, target_is_directory=True)
        with self.assertRaises(ValueError):
            self.resolve(config)

    def test_config_digest_or_root_identity_change_refuses_verify(self):
        config, paths = self.layout_config(suffix='digest')
        layout = self.resolve(config)
        alternate_runtime = self.private_dir('runtime-alternate')
        changed = {'schema': 'offmenu-runner-layout/1', **paths, 'runtime': str(alternate_runtime)}
        config.write_text(json.dumps(changed, sort_keys=True), encoding='utf-8')
        os.chmod(config, 0o600)
        with patch.dict(os.environ, {'OFFMENU_RUN_LAYOUT': str(config)}, clear=True):
            with self.assertRaises(ValueError):
                layout.verify()

        config, paths = self.layout_config(suffix='replace')
        layout = self.resolve(config)
        normalization = Path(paths['normalization'])
        retired = self.base / 'normalization-retired'
        normalization.rename(retired)
        self.private_dir('normalizationreplace')
        with patch.dict(os.environ, {'OFFMENU_RUN_LAYOUT': str(config)}, clear=True):
            with self.assertRaises(ValueError):
                layout.verify()

    def test_operational_lease_requires_selected_fd_and_digest(self):
        config, paths = self.layout_config()
        layout = self.resolve(config)
        fd = os.open(paths['lock'], os.O_RDWR)
        self.addCleanup(os.close, fd)
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        with patch.dict(os.environ, {'OFFMENU_RUN_LAYOUT': str(config)}, clear=True):
            layout.activate(fd)
            selected = self.module.resolve_layout(self.legacy, require_lease=True)
        self.assertEqual(selected.lock, Path(paths['lock']))
        with patch.dict(os.environ, {
            'OFFMENU_RUN_LAYOUT': str(config), 'OFFMENU_RUN_FD': str(fd),
            'OFFMENU_RUN_LAYOUT_SHA256': '0' * 64,
        }, clear=True):
            with self.assertRaises(ValueError):
                self.module.resolve_layout(self.legacy, require_lease=True)

    def test_distinct_processes_contend_on_the_same_singleton(self):
        config, paths = self.layout_config()
        fd = os.open(paths['lock'], os.O_RDWR)
        self.addCleanup(os.close, fd)
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        code = (
            'import fcntl, os, sys; '
            'fd=os.open(sys.argv[1], os.O_RDWR); '
            'fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)'
        )
        result = subprocess.run(
            [sys.executable, '-c', code, paths['lock']],
            cwd=self.base, capture_output=True, text=True,
        )
        self.assertNotEqual(result.returncode, 0)


if __name__ == '__main__':
    unittest.main()
