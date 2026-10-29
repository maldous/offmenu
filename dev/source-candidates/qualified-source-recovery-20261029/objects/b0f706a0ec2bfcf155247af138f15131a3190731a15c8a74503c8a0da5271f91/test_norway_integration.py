"""Lightweight repository integration checks; authored synthetic input only."""
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from offmenu_norway import adapter

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / 'scripts/run-norway-synthetic.py'
FIXTURES = ROOT / 'tests/fixtures/norway'
EVIDENCE = ROOT / 'docs/evidence/norway-synthetic/approved-artifact'
spec = importlib.util.spec_from_file_location('norway_synthetic_entry', SCRIPT)
entry = importlib.util.module_from_spec(spec)
spec.loader.exec_module(entry)


class NorwayIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.output = Path(self.temp.name) / 'candidate'
        self.lock = json.loads(entry.LOCK_PATH.read_bytes())

    def test_three_implementation_files_match_independent_approval(self):
        for pin in self.lock['dependencies']:
            raw = (ROOT / pin['path']).read_bytes()
            self.assertEqual(len(raw), pin['bytes'])
            self.assertEqual(hashlib.sha256(raw).hexdigest(), pin['sha256'])
        self.assertEqual(set(pin['path'] for pin in self.lock['inputs']), set(adapter.INPUTS))

    def test_repository_cli_builds_and_verifies_identical_retry(self):
        command = [sys.executable, '-B', str(SCRIPT), '--output', str(self.output),
                   '--repin-synthetic-runtime']
        first = subprocess.run(command, cwd=self.temp.name, capture_output=True, text=True, timeout=15)
        self.assertEqual(first.returncode, 0, first.stderr + first.stdout)
        self.assertEqual(json.loads(first.stdout)['status'], 'created-local-candidate')
        second = subprocess.run(command, cwd=self.temp.name, capture_output=True, text=True, timeout=15)
        self.assertEqual(second.returncode, 0, second.stderr + second.stdout)
        self.assertEqual(json.loads(second.stdout)['status'], 'verified-existing-candidate')
        current = adapter.fixture_lock(FIXTURES)
        self.assertEqual({p.name: p.read_bytes() for p in self.output.iterdir()}, adapter.render(current, FIXTURES))

    def test_default_cli_does_not_silently_repin_runtime(self):
        with patch.object(adapter, 'runtime', return_value={**adapter.runtime(), 'python': '0.0-test-only'}):
            with self.assertRaisesRegex(adapter.AdapterError, '^runtime-pin-mismatch$'):
                entry.run(self.output)
        self.assertFalse(self.output.exists())

    def test_opt_in_repins_runtime_without_changing_frozen_lock_or_inputs(self):
        before = entry.LOCK_PATH.read_bytes()
        current = adapter.runtime()
        with patch.object(adapter, 'runtime', return_value={**current, 'python': '0.0-test-only'}):
            result = entry.run(self.output, repin_synthetic_runtime=True)
        self.assertTrue(result['runtimeRepinned'])
        self.assertTrue(result['syntheticOnly'])
        self.assertEqual(entry.LOCK_PATH.read_bytes(), before)
        self.assertEqual(json.loads((self.output / 'content-manifest.json').read_bytes())['inputBundleSha256'],
                         adapter.bundle_key(adapter.fixture_lock(FIXTURES)))

    def test_cli_has_no_arbitrary_input_or_historical_switch(self):
        for extra in (['--inputs', '/not-an-authorized-source'], ['--historical'], ['--lock', '/other-lock']):
            with self.subTest(extra=extra):
                proc = subprocess.run([sys.executable, '-B', str(SCRIPT), '--output', str(self.output), *extra],
                                      capture_output=True, text=True, timeout=15)
                self.assertEqual(proc.returncode, 2)
                self.assertIn('unrecognized arguments', proc.stderr)
                self.assertFalse(self.output.exists())

    def test_historical_lock_rejected_before_any_source_read(self):
        lock = copy.deepcopy(self.lock)
        lock['runtime'] = adapter.runtime()
        lock['scope'] = 'historical-source-snapshot'
        with patch.object(adapter, 'read_bytes', side_effect=AssertionError('unexpected source read')):
            with self.assertRaisesRegex(adapter.AdapterError, '^historical-source-input-not-enabled$'):
                adapter.build(lock, FIXTURES, self.output)
        self.assertFalse(self.output.exists())

    def test_final_review_bytes_match_same_runtime_render(self):
        if self.lock['runtime'] != adapter.runtime():
            self.skipTest('Frozen candidate requires the recorded CPython/zlib runtime.')
        rendered = adapter.render(self.lock, FIXTURES)
        for directory in ('candidate-v2-A', 'candidate-v2-B'):
            self.assertEqual({p.name: p.read_bytes() for p in (EVIDENCE / directory).iterdir()}, rendered)

    def test_synthetic_acquisition_evidence_is_outside_content_dependencies(self):
        evidence = json.loads((ROOT / 'tests/fixtures/norway-acquisition-evidence.json').read_bytes())
        self.assertIn('originalAcquiredAt', evidence)
        self.assertNotIn('originalAcquiredAt', self.lock)
        self.assertNotIn('originalAcquiredAt', (EVIDENCE / 'candidate-v2-A/content-manifest.json').read_text())

    def test_existing_offmenu_and_norway_import_in_both_orders(self):
        modules = ['offmenu.core', 'offmenu.refresh', 'offmenu_norway.adapter']
        for order in (modules, list(reversed(modules))):
            code = '; '.join('import ' + name for name in order)
            proc = subprocess.run([sys.executable, '-B', '-c', code], cwd=ROOT,
                                  capture_output=True, text=True, timeout=15)
            self.assertEqual(proc.returncode, 0, proc.stderr)

    def test_contract_is_requested_in_package_manifest(self):
        self.assertIn('include offmenu_norway/contract.json', (ROOT / 'MANIFEST.in').read_text().splitlines())


if __name__ == '__main__':
    unittest.main()
