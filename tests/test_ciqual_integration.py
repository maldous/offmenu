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

from offmenu_ciqual import adapter

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / 'tools/data-processing/run_ciqual_synthetic.py'
FIXTURES = ROOT / 'tests/fixtures/ciqual'
EVIDENCE = ROOT / 'docs/evidence/ciqual-synthetic/approved-artifact'
spec = importlib.util.spec_from_file_location('ciqual_synthetic_entry', SCRIPT)
entry = importlib.util.module_from_spec(spec)
spec.loader.exec_module(entry)


class CiqualIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.output = Path(self.temp.name) / 'candidate'
        self.lock = json.loads(entry.LOCK_PATH.read_bytes())

    def test_four_implementation_files_match_independent_approval(self):
        self.assertEqual(len(self.lock['dependencies']), 4)
        for pin in self.lock['dependencies']:
            raw = (ROOT / 'src' / pin['path']).read_bytes()
            self.assertEqual(len(raw), pin['bytes'])
            self.assertEqual(hashlib.sha256(raw).hexdigest(), pin['sha256'])
        self.assertEqual({pin['path'] for pin in self.lock['inputs']}, set(adapter.INPUTS))

    def test_repository_cli_builds_and_verifies_identical_retry(self):
        command = [sys.executable, '-B', str(SCRIPT), '--output', str(self.output),
                   '--repin-synthetic-runtime']
        first = subprocess.run(command, cwd=self.temp.name, capture_output=True, text=True, timeout=15)
        self.assertEqual(first.returncode, 0, first.stderr + first.stdout)
        self.assertEqual(json.loads(first.stdout)['status'], 'synthetic-normalized-candidate')
        before = {p.name: p.read_bytes() for p in self.output.iterdir()}
        second = subprocess.run(command, cwd=self.temp.name, capture_output=True, text=True, timeout=15)
        self.assertEqual(second.returncode, 0, second.stderr + second.stdout)
        self.assertEqual(json.loads(first.stdout), json.loads(second.stdout))
        self.assertEqual({p.name: p.read_bytes() for p in self.output.iterdir()}, before)
        self.assertEqual(before, adapter.render(FIXTURES, adapter.fixture_lock(FIXTURES)))

    def test_default_cli_does_not_silently_repin_runtime(self):
        with patch.object(adapter, 'runtime', return_value={**adapter.runtime(), 'python': '0.0-test-only'}):
            with self.assertRaisesRegex(adapter.DataError, '^runtime-pin-mismatch$'):
                entry.run(self.output)
        self.assertFalse(self.output.exists())

    def test_opt_in_repins_only_runtime_without_changing_frozen_lock_or_inputs(self):
        before = entry.LOCK_PATH.read_bytes()
        current = adapter.runtime()
        with patch.object(adapter, 'runtime', return_value={**current, 'python': '0.0-test-only'}):
            result = entry.run(self.output, repin_synthetic_runtime=True)
        self.assertTrue(result['runtimeRepinned'])
        self.assertTrue(result['syntheticOnly'])
        self.assertEqual(entry.LOCK_PATH.read_bytes(), before)
        changed = json.loads((self.output / 'content-manifest.json').read_bytes())['dependencyLock']
        for key in ('inputs', 'dependencies'):
            self.assertEqual(sorted(changed[key], key=lambda p: p['path']),
                             sorted(self.lock[key], key=lambda p: p['path']))

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
            with self.assertRaisesRegex(adapter.DataError, '^historical-source-input-not-enabled$'):
                adapter.build(FIXTURES, lock, self.output)
        self.assertFalse(self.output.exists())

    def test_final_review_bytes_match_same_runtime_render(self):
        if self.lock['runtime'] != adapter.runtime():
            self.skipTest('Frozen candidate requires its recorded CPython/Expat/zlib runtime.')
        rendered = adapter.render(FIXTURES, self.lock)
        for directory in ('candidate-v3-A', 'candidate-v3-B'):
            self.assertEqual({p.name: p.read_bytes() for p in (EVIDENCE / directory).iterdir()}, rendered)

    def test_synthetic_acquisition_evidence_is_outside_content_dependencies(self):
        evidence = json.loads((ROOT / 'tests/fixtures/ciqual-acquisition-evidence.json').read_bytes())
        self.assertIn('acquiredAt', evidence)
        self.assertNotIn('acquiredAt', self.lock)
        self.assertNotIn('acquiredAt', (EVIDENCE / 'candidate-v3-A/content-manifest.json').read_text())

    def test_existing_offmenu_norway_and_ciqual_import_in_both_orders(self):
        modules = ['offmenu.core', 'offmenu.refresh', 'offmenu_norway.adapter', 'offmenu_ciqual.adapter']
        for order in (modules, list(reversed(modules))):
            proc = subprocess.run([sys.executable, '-B', '-c', '; '.join('import ' + name for name in order)],
                                  cwd=ROOT, capture_output=True, text=True, timeout=15)
            self.assertEqual(proc.returncode, 0, proc.stderr)

    def test_manifest_preserves_norway_and_includes_ciqual_contract(self):
        lines = (ROOT / 'MANIFEST.in').read_text().splitlines()
        self.assertIn('include src/offmenu_norway/contract.json', lines)
        self.assertIn('include src/offmenu_ciqual/contract.json', lines)


if __name__ == '__main__':
    unittest.main()
