"""Synthetic fetch/parse wrappers and argv; no collection or live requests."""
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch
import ast
import io
import json
import os
import subprocess
import tempfile
import unittest

import test_owner_launcher as fixture

m = fixture.m


class StageLauncherTests(unittest.TestCase):
    setUp = fixture.LauncherTests.setUp
    tearDown = fixture.LauncherTests.tearDown
    installed_layout = fixture.LauncherTests.installed_layout
    comprehensive_prior = fixture.LauncherTests.comprehensive_prior

    def test_install_makes_explicit_commands_and_run_alias_without_execution(self):
        root, source = self.installed_layout()
        with patch.object(m, 'verify_source'), patch.object(m, 'git', side_effect=AssertionError('network forbidden')), \
             patch.object(m.os, 'execvpe', side_effect=AssertionError('collection forbidden')), redirect_stdout(io.StringIO()):
            m.install('a' * 40, 'b' * 40)
        self.assertEqual((root / 'run').read_bytes(), m.run_alias_bytes(root))
        self.assertIn(str(root / 'fetch').encode(), (root / 'run').read_bytes())
        self.assertNotIn(b'collect-fixed-global', (root / 'run').read_bytes())
        for stage in ('fetch', 'parse'):
            self.assertEqual((root / stage).read_bytes(), m.stage_wrapper_bytes(source, stage))
            self.assertEqual((root / stage).stat().st_mode & 0o777, 0o700)
        self.assertEqual((root / 'run').stat().st_mode & 0o777, 0o700)

    def test_real_shell_wrappers_preserve_stage_and_arguments_with_quoted_paths(self):
        # The launched script only prints argv. It cannot invoke the collector.
        with tempfile.TemporaryDirectory(prefix="synthetic space ' quote ") as tmp:
            root = Path(tmp)
            source = root / 'source'
            (source / 'scripts').mkdir(parents=True)
            (source / 'scripts/run-global-on-foo.py').write_text('import json,sys\nprint(json.dumps(sys.argv[1:]))\n')
            for stage in ('fetch', 'parse'):
                (root / stage).write_bytes(m.stage_wrapper_bytes(source, stage))
                (root / stage).chmod(0o700)
            (root / 'run').write_bytes(m.run_alias_bytes(root))
            (root / 'run').chmod(0o700)
            for command, stage in (('fetch', 'fetch'), ('parse', 'parse'), ('run', 'fetch')):
                result = subprocess.run([str(root / command), '--publish-only'], text=True, capture_output=True, timeout=5, check=True)
                self.assertEqual(json.loads(result.stdout), ['--stage', stage, '--publish-only'])
                self.assertEqual(result.stderr, '')

    def test_collector_always_receives_an_explicit_stage_and_owner_mode(self):
        root, source = self.installed_layout()
        (root / 'pins' / ('a' * 40 + '.json')).write_text(json.dumps({'commit': 'a' * 40, 'tree': 'b' * 40}))
        for stage in ('fetch', 'parse'):
            for publish in (False, True):
                with self.subTest(stage=stage, publish=publish), patch.object(m, '__file__', str(source / 'scripts/run-global-on-foo.py')), \
                     patch.object(m, 'verify_source'), patch.object(m, 'announce_progress'), patch.object(m.os, 'chdir'), patch.object(m.os, 'execvpe') as execute:
                    m.run(publish, stage=stage)
                argv = execute.call_args.args[1]
                expected = ['--mode', 'user', '--stage', stage] + (['--publish-only'] if publish else [])
                self.assertEqual(argv[argv.index('--mode'):], expected)
                self.assertEqual(argv.count('--stage'), 1)
                self.assertEqual(argv[:4], ['timeout', '--signal=TERM', '--kill-after=15s', '1800s'])

    def test_legacy_main_defaults_to_fetch_and_publish_recovery_survives(self):
        cases = [([], 'fetch', False), (['--publish-only'], 'fetch', True),
                 (['--stage', 'fetch'], 'fetch', False), (['--stage', 'parse'], 'parse', False),
                 (['--stage', 'fetch', '--publish-only'], 'fetch', True),
                 (['--stage', 'parse', '--publish-only'], 'parse', True)]
        for args, stage, publish in cases:
            with self.subTest(args=args), patch.object(m.sys, 'argv', ['launcher', *args]), \
                 patch.object(m.os, 'getuid', return_value=1000), patch.object(m.os, 'geteuid', return_value=1000), patch.object(m, 'run') as run:
                m.main()
                run.assert_called_once_with(publish, stage=stage)

    def test_unknown_combined_and_stage_override_arguments_stop(self):
        for args in (['--stage', 'all'], ['--stage', 'combined'], ['--stage', 'fetch', '--stage', 'parse'],
                     ['--stage'], ['--publish-only', '--publish-only'], ['fetch'], ['--stage', 'parse', '--execute']):
            with self.subTest(args=args), patch.object(m.sys, 'argv', ['launcher', *args]), \
                 patch.object(m.os, 'getuid', return_value=1000), patch.object(m.os, 'geteuid', return_value=1000), patch.object(m, 'run') as run, self.assertRaises(ValueError):
                m.main()
            run.assert_not_called()
        with patch.object(m, 'announce_progress') as progress, self.assertRaises(ValueError):
            m.run(stage='combined')
        progress.assert_not_called()
        with self.assertRaises(ValueError):
            m.stage_wrapper_bytes(Path('/synthetic'), 'combined')

    def test_exact_c74_wrapper_and_all_predecessor_maps_remain_available(self):
        self.assertEqual(m.COMPREHENSIVE_PREDECESSOR, {'commit': 'c74cfaee99c6d743c8d4982de4d8d8cce651b057', 'tree': 'e186e5eebf94d3c97426221e52772640d2e8fb04'})
        self.assertTrue(m.PREDECESSOR_FILES)
        self.assertTrue(m.VERSIONED_PREDECESSOR_FILES)
        self.assertTrue(m.COMPREHENSIVE_PREDECESSOR_FILES)
        root, prior = self.comprehensive_prior()
        expected = ('#!/bin/sh\nexec /usr/bin/python3 -I -B ' + str(prior / 'scripts/run-global-on-foo.py') + ' "$@"\n').encode()
        self.assertEqual((root / 'run').read_bytes(), expected)
        before = (root / 'pins' / (m.COMPREHENSIVE_PREDECESSOR['commit'] + '.json')).read_bytes()
        _, source = self.installed_layout()
        with patch.object(m, 'verify_source') as verify, redirect_stdout(io.StringIO()):
            m.install('a' * 40, 'b' * 40)
        self.assertEqual(verify.call_args_list[0].args[3], m.COMPREHENSIVE_PREDECESSOR_FILES)
        self.assertEqual((root / 'run').read_bytes(), m.run_alias_bytes(root))
        self.assertEqual((root / 'pins' / (m.COMPREHENSIVE_PREDECESSOR['commit'] + '.json')).read_bytes(), before)
        self.assertEqual((prior / 'preserved').read_bytes(), b'prior-c74-source')

    def test_unknown_stage_wrapper_blocks_before_source_fetch(self):
        root, source = self.installed_layout()
        (root / 'parse').write_bytes(b'#!/bin/sh\nexit 0\n')
        with patch.object(m, 'git', side_effect=AssertionError('network forbidden')), patch.object(m, 'verify_source') as verify, self.assertRaisesRegex(ValueError, 'unknown-install-stage-wrapper'):
            m.install('a' * 40, 'b' * 40)
        verify.assert_not_called()
        self.assertFalse((root / 'run').exists())
        self.assertEqual((root / 'parse').read_bytes(), b'#!/bin/sh\nexit 0\n')

    def test_failed_second_stage_switch_keeps_old_run_and_exact_retry_recovers(self):
        root, prior = self.comprehensive_prior()
        before = (root / 'run').read_bytes()
        _, source = self.installed_layout()
        original_replace = os.replace
        def fail_parse(src, dest):
            if Path(dest) == root / 'parse':
                raise OSError('synthetic parse switch failure')
            return original_replace(src, dest)
        with patch.object(m, 'verify_source'), patch.object(m.os, 'replace', side_effect=fail_parse), self.assertRaises(OSError):
            m.install('a' * 40, 'b' * 40)
        self.assertEqual((root / 'run').read_bytes(), before)
        self.assertEqual((root / 'fetch').read_bytes(), m.stage_wrapper_bytes(source, 'fetch'))
        self.assertFalse((root / 'parse').exists())
        with patch.object(m, 'verify_source'), redirect_stdout(io.StringIO()):
            m.install('a' * 40, 'b' * 40)
        self.assertEqual((root / 'run').read_bytes(), m.run_alias_bytes(root))
        self.assertEqual((root / 'parse').read_bytes(), m.stage_wrapper_bytes(source, 'parse'))
        self.assertEqual((prior / 'preserved').read_bytes(), b'prior-c74-source')

    def test_stage_pointer_race_is_detected_without_overwrite(self):
        root, source = self.installed_layout()
        def mutate(*args, **kwargs):
            (root / 'fetch').write_bytes(b'synthetic concurrent edit')
        with patch.object(m, 'verify_source', side_effect=mutate), self.assertRaisesRegex(ValueError, 'install-pointer-changed'):
            m.install('a' * 40, 'b' * 40)
        self.assertEqual((root / 'fetch').read_bytes(), b'synthetic concurrent edit')
        self.assertFalse((root / 'run').exists())

    def test_stage_symlinks_rejected_without_overwrite(self):
        root, source = self.installed_layout()
        target = self.home / 'target'
        target.write_bytes(b'preserve')
        (root / 'fetch').symlink_to(target)
        with patch.object(m, 'git', side_effect=AssertionError('network forbidden')), self.assertRaises(OSError):
            m.install('a' * 40, 'b' * 40)
        self.assertTrue((root / 'fetch').is_symlink())
        self.assertEqual(target.read_bytes(), b'preserve')


if __name__ == '__main__':
    unittest.main()
