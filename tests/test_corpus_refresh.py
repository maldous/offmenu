"""No live downloads. All data is synthetic and every workspace is disposable."""
import contextlib
import copy
from datetime import datetime, timedelta, timezone
import gzip
import importlib.util
import io
import json
import os
from pathlib import Path
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from offmenu.refresh import core
from offmenu.refresh.inventory import inventory
from offmenu.refresh.__main__ import main

FIXTURE = Path(__file__).parent / 'fixtures/corpus-refresh'


class RefreshTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.inputs = self.root / 'input'
        shutil.copytree(FIXTURE, self.inputs)
        self.manifest_path = self.inputs / 'input-manifest.json'
        self.manifest = core.load_manifest(self.manifest_path)
        self.workspace = self.root / 'work'

    def run_refresh(self, **kwargs):
        return core.replay(self.manifest, self.inputs, self.workspace, **kwargs)

    def test_replay_idempotence_force_and_offline_provenance(self):
        first = self.run_refresh()
        final = self.workspace / 'releases' / first['identity']
        times = {p.name: p.stat().st_mtime_ns for p in final.iterdir()}
        with patch.object(core, 'transform', side_effect=AssertionError('no-op transformed')):
            second = self.run_refresh()
        self.assertEqual(second['action'], 'verified-no-op')
        self.assertEqual(first['artifacts'], second['artifacts'])
        self.assertEqual(times, {p.name: p.stat().st_mtime_ns for p in final.iterdir()})
        with patch.object(core, 'transform', wraps=core.transform) as transform:
            forced = self.run_refresh(force=True)
        transform.assert_called_once()
        self.assertEqual(forced['action'], 'force-verified-identical')
        self.assertEqual(first['artifacts'], forced['artifacts'])
        self.assertEqual(first['counts'], {'raw': 3, 'accepted': 1, 'duplicates': 1, 'quarantined': 1, 'excluded': 0, 'records': 1})
        self.assertNotEqual(first['runId'], second['runId'])
        self.assertFalse(first['countryCoverage']['complete'])
        self.assertEqual(first['countryCoverage']['observedCountryCodes'], [])
        with gzip.open(final / 'normalized.jsonl.gz', 'rt') as handle:
            row = json.loads(next(handle))[0]
        self.assertIsNone(row['data']['ingredients'][1]['amount'])
        self.assertFalse(row['data']['automaticPlanningEligible'])
        self.assertEqual(row['provenance']['fetchedAt'], self.manifest['acquiredAt'])
        self.assertEqual(row['provenance']['archiveSha256'], self.manifest['input']['sha256'])
        self.assertNotIn(str(self.root), json.dumps(first))
        self.assertNotIn('recipes_parsed.json', json.dumps(first))

    def test_independent_workspaces_reproduce_bytes(self):
        first = self.run_refresh()
        other = core.replay(self.manifest, self.inputs, self.root / 'other')
        self.assertEqual(first['identity'], other['identity'])
        self.assertEqual(first['artifacts'], other['artifacts'])

    def test_crash_resume_at_every_publication_boundary(self):
        for boundary in ['cached', 'transformed', 'renamed-before-checkpoint', 'published']:
            with self.subTest(boundary=boundary):
                self.workspace = self.root / boundary
                def crash(stage):
                    if stage == boundary:
                        raise RuntimeError('simulated interruption')
                with self.assertRaisesRegex(RuntimeError, 'simulated'):
                    self.run_refresh(failpoint=crash)
                with self.assertRaisesRegex(core.RefreshError, 'requires-resume'):
                    self.run_refresh()
                receipt = self.run_refresh(resume=True)
                self.assertEqual(receipt['status'], 'complete')
                self.assertEqual(len(list((self.workspace / 'releases').iterdir())), 1)
                self.assertTrue((self.workspace / 'workspace.lock').exists())
                self.assertEqual(self.run_refresh()['action'], 'verified-no-op')

    def test_partial_transform_is_rebuilt_on_resume(self):
        def partial(cache, destination, manifest, **kwargs):
            destination.mkdir()
            (destination / 'normalized.jsonl.gz').write_bytes(b'truncated')
            raise RuntimeError('crash')
        with patch.object(core, 'transform', side_effect=partial):
            with self.assertRaises(RuntimeError):
                self.run_refresh()
        result = self.run_refresh(resume=True)
        self.assertEqual(result['counts']['accepted'], 1)

    def test_resume_changed_pins_refused(self):
        def crash(stage):
            raise RuntimeError('crash')
        with self.assertRaises(RuntimeError):
            self.run_refresh(failpoint=crash)
        self.manifest['acquiredAt'] = '2026-10-16T00:00:00+00:00'
        with self.assertRaisesRegex(core.RefreshError, 'no-matching-run'):
            self.run_refresh(resume=True)

    def test_corrupt_cache_and_force_do_not_repair_silently(self):
        result = self.run_refresh()
        cache = self.workspace / 'cache/sha256' / self.manifest['input']['sha256']
        cache.write_bytes(b'corrupt')
        with self.assertRaisesRegex(core.RefreshError, 'checksum-mismatch'):
            self.run_refresh(force=True)
        self.assertEqual(cache.read_bytes(), b'corrupt')
        self.assertTrue((self.workspace / 'releases' / result['identity']).is_dir())

    def test_corrupt_published_output_fails(self):
        result = self.run_refresh()
        final = self.workspace / 'releases' / result['identity']
        (final / 'manifest.json').write_text('{}')
        with self.assertRaisesRegex(core.RefreshError, 'checksum-mismatch'):
            self.run_refresh()
        self.assertEqual((final / 'manifest.json').read_text(), '{}')

    def test_input_changed_is_rejected_before_workspace_creation(self):
        (self.inputs / self.manifest['input']['path']).write_text('changed')
        with self.assertRaisesRegex(core.RefreshError, 'checksum-mismatch'):
            self.run_refresh()
        self.assertFalse(self.workspace.exists())

    def test_shared_lock_blocks_and_is_not_removed(self):
        self.workspace.mkdir()
        lock = self.workspace / 'workspace.lock'
        with core.writer_lock(lock):
            original = lock.read_bytes()
            with self.assertRaisesRegex(core.RefreshError, 'writer-lock'):
                self.run_refresh()
            self.assertEqual(lock.read_bytes(), original)
        self.assertFalse((self.workspace / 'checkpoint.sqlite').exists())
        self.assertEqual(self.run_refresh()['status'], 'complete')

    def test_source_lock_blocks(self):
        (self.workspace / 'locks').mkdir(parents=True)
        lock = self.workspace / 'locks/wikibooks.lock'
        with core.writer_lock(lock):
            with self.assertRaisesRegex(core.RefreshError, 'writer-lock'):
                self.run_refresh()
        self.assertTrue(lock.exists())
        self.assertEqual(self.run_refresh()['status'], 'complete')

    def test_low_disk_stops_before_checkpoint(self):
        usage = shutil.disk_usage(self.root)._replace(free=1)
        with patch.object(core.shutil, 'disk_usage', return_value=usage):
            with self.assertRaisesRegex(core.RefreshError, 'insufficient-staging'):
                self.run_refresh()
        self.assertFalse((self.workspace / 'checkpoint.sqlite').exists())

    def test_overlaps_and_symlinks_fail_closed(self):
        for workspace in [self.inputs, self.inputs / 'work', self.root]:
            with self.subTest(workspace=workspace):
                with self.assertRaisesRegex(core.RefreshError, 'overlap'):
                    core.replay(self.manifest, self.inputs, workspace)
        linked = self.root / 'linked'
        linked.symlink_to(self.inputs, target_is_directory=True)
        with self.assertRaisesRegex(core.RefreshError, 'symlink'):
            core.replay(self.manifest, linked, self.workspace)
        path = self.inputs / self.manifest['input']['path']
        original = self.root / 'outside.json'
        path.rename(original)
        path.symlink_to(original)
        with self.assertRaisesRegex(core.RefreshError, 'symlink'):
            self.run_refresh()

    def test_manifest_strict_allowlist_and_rights(self):
        mutations = [lambda m: m.update(secret='never echoed'),
                     lambda m: m.update(schemaVersion='future'),
                     lambda m: m.update(sourceId='not-an-adapter'),
                     lambda m: m['rights'].update(status='unknown'),
                     lambda m: m['rights'].update(license='unknown'),
                     lambda m: m['input'].update(path='../escape'),
                     lambda m: m['input'].update(path='/absolute'),
                     lambda m: m['input'].update(bytes=core.MAX_INPUT + 1),
                     lambda m: m['input'].update(bytes=True),
                     lambda m: m.update(acquiredAt='2026-10-17')]
        for mutate in mutations:
            with self.subTest(mutate=mutate):
                value = copy.deepcopy(self.manifest)
                mutate(value)
                self.manifest_path.write_text(json.dumps(value))
                with self.assertRaises(core.RefreshError):
                    core.load_manifest(self.manifest_path)
        self.manifest_path.write_text('{"schemaVersion":1,"schemaVersion":2}')
        with self.assertRaisesRegex(core.RefreshError, 'duplicate'):
            core.load_manifest(self.manifest_path)

    def test_bad_input_json_never_publishes_and_error_is_sanitized(self):
        for index, content in enumerate(['[{"recipe_data":{"url":NaN}}]', '[{"recipe_data":{"title":"a","title":"b"}}]', '[{"recipe_data":{"url":123,"title":"SECRET"}}]']):
            with self.subTest(index=index):
                source = self.inputs / self.manifest['input']['path']
                source.write_text(content)
                self.manifest['input'].update(core.digest(source))
                self.manifest_path.write_text(json.dumps(self.manifest))
                output = io.StringIO()
                with contextlib.redirect_stdout(output):
                    code = main(['replay', '--manifest', str(self.manifest_path), '--input-root', str(self.inputs), '--workspace', str(self.root / ('bad' + str(index)))])
                self.assertEqual(code, 2)
                result = json.loads(output.getvalue())
                self.assertEqual(result['errorCode'], 'adapter-failed-no-output-published')
                self.assertNotIn('SECRET', output.getvalue())
                self.assertNotIn(str(self.root), output.getvalue())
                self.assertEqual(list((self.root / ('bad' + str(index)) / 'releases').iterdir()), [])

    def test_force_refresh_is_reserved_and_does_not_create_workspace(self):
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            code = main(['replay', '--manifest', str(self.manifest_path), '--input-root', str(self.inputs), '--workspace', str(self.workspace), '--force-refresh'])
        self.assertEqual(code, 2)
        self.assertEqual(json.loads(output.getvalue())['errorCode'], 'online-acquisition-not-implemented')
        self.assertFalse(self.workspace.exists())

    def test_cache_minimum_30_day_policy_and_future_time(self):
        acquired = core.timestamp(self.manifest['acquiredAt'])
        for delta, expected in [(timedelta(days=29, hours=23), 'reuse-verified-cache'),
                                (timedelta(days=30), 'conditional-revalidation-required'),
                                (timedelta(days=300), 'conditional-revalidation-required')]:
            result = core.cache_policy(self.manifest, acquired + delta)
            self.assertEqual(result['decision'], expected)
            self.assertFalse(result['mtimeUsedForFreshness'])
            self.assertEqual(result['networkRequests'], 0)
        self.assertEqual(core.cache_policy(self.manifest, acquired, force=True)['decision'], 'explicit-refresh-requested')
        with self.assertRaisesRegex(core.RefreshError, 'future'):
            core.cache_policy(self.manifest, acquired - timedelta(seconds=1))

    def test_code_fingerprint_uses_actual_bytes_and_runtime(self):
        identity = core.code_identity()
        self.assertRegex(identity['codeCommit'], r'^[0-9a-f]{40}$')
        self.assertRegex(identity['codeFingerprint'], r'^[0-9a-f]{64}$')
        with patch.object(core.platform, 'python_version', return_value='different'):
            changed = core.code_identity()
        self.assertNotEqual(identity['codeFingerprint'], changed['codeFingerprint'])

    def test_inventory_read_only_bounded_and_redacted(self):
        secret = self.inputs / '.env'
        secret.write_text('password=NEVER_READ')
        (self.inputs / 'linked').symlink_to(secret)
        before = {p.name: (p.stat().st_mtime_ns, p.stat().st_size) for p in self.inputs.iterdir()}
        with patch.object(Path, 'open', side_effect=AssertionError('inventory opened contents')):
            result = inventory(self.inputs)
        self.assertFalse(result['contentsRead'])
        self.assertFalse(result['scopeComplete'])
        self.assertEqual(len(result['candidates']), 1)
        encoded = json.dumps(result)
        self.assertNotIn('NEVER_READ', encoded)
        self.assertNotIn(str(self.inputs), encoded)
        self.assertNotIn('recipes_parsed.json', encoded)
        self.assertEqual(before, {p.name: (p.stat().st_mtime_ns, p.stat().st_size) for p in self.inputs.iterdir()})
        result = inventory(self.inputs, max_entries=1)
        self.assertFalse(result['boundedScanComplete'])
        self.assertEqual(result['counts']['entries'], 1)

    def test_inventory_depth_exclusions_are_not_full_coverage(self):
        (self.inputs / 'deeper').mkdir()
        result = inventory(self.inputs, max_depth=0)
        self.assertFalse(result['scopeComplete'])
        self.assertEqual(result['counts']['depthLimitedDirectories'], 1)

    def test_network_and_subprocess_are_denied_in_guard(self):
        # Run the real guard in a child so its permanent audit hook cannot affect unittest.
        runner = core.ROOT / 'offmenu/refresh/runner.py'
        program = f'''import importlib.util,sys,socket,subprocess
s=importlib.util.spec_from_file_location("runner",{str(runner)!r}); m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
sys.addaudithook(m.deny_network)
for fn in (lambda:socket.socket(),lambda:socket.getaddrinfo("example.com",443),lambda:subprocess.run(["true"])):
 try:fn()
 except RuntimeError:pass
 else:raise SystemExit(3)
'''
        result = subprocess.run([sys.executable, '-I', '-B', '-c', program], capture_output=True)
        self.assertEqual(result.returncode, 0, result.stderr.decode())


if __name__ == '__main__':
    unittest.main()
