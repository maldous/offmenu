"""W48-R36-INGRESS delta regressions: authored files only, no source bodies."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from offmenu.refresh.portfolio48 import __main__ as cli

ROOT = Path(__file__).resolve().parents[1]
BOOT = ('import runpy,sys;sys.path.insert(0,' + repr(str(ROOT)) + ');'
        'sys.argv=["portfolio48"]+sys.argv[1:];'
        'runpy.run_module("offmenu.refresh.portfolio48",run_name="__main__")')


class CLIIngressCorrection(unittest.TestCase):
    def invoke(self, args, cwd):
        # Timeout kills/reaps only this authored fixture process on regression.
        result = subprocess.run([sys.executable, '-I', '-B', '-c', BOOT,
                                 '--now', '2026-10-18T06:00:00Z', *args],
                                cwd=cwd, capture_output=True, timeout=2,
                                env={'PATH': os.defpath, 'LANG': 'C.UTF-8',
                                     'PYTHONDONTWRITEBYTECODE': '1'})
        self.assertEqual(result.returncode, 2, result.stderr)
        self.assertEqual(result.stderr, b'')
        return json.loads(result.stdout)

    def test_regular_map_and_previous_candidate_control(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            mapping = root / 'map.json'; mapping.write_bytes(b'{}')
            candidate = root / 'candidate.jsonl'; candidate.write_bytes(b'')
            before = (mapping.read_bytes(), candidate.read_bytes())
            report = self.invoke(['--metadata-map', str(mapping),
                                  '--previous-candidate', str(candidate)], root)
            self.assertEqual(report['replay']['action'], 'verified-no-op')
            self.assertEqual(report['metadataRecords'], 0)
            self.assertEqual(report['dataRecords'], 0)
            self.assertEqual(len(report['coverage']), 24)
            self.assertFalse(report['sourceBodyAdmission'])
            self.assertEqual(before, (mapping.read_bytes(), candidate.read_bytes()))

    def test_both_fifo_endpoints_return_fixed_error_without_blocking(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            pipe = root / 'input.json'; os.mkfifo(pipe)
            for endpoint in ['--metadata-map', '--previous-candidate']:
                with self.subTest(endpoint=endpoint):
                    report = self.invoke([endpoint, str(pipe)], root)
                    self.assertEqual(report['diagnostics'], ['portfolio48-command-input-invalid'])
                    self.assertFalse(report['sourceBodyAdmission'])

    def test_directory_and_symlink_endpoints_fail_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            target = root / 'regular.json'; target.write_bytes(b'{}')
            alias = root / 'alias.json'; alias.symlink_to(target)
            for endpoint in ['--metadata-map', '--previous-candidate']:
                for path in [root, alias]:
                    with self.subTest(endpoint=endpoint, path=path.name):
                        report = self.invoke([endpoint, str(path)], root)
                        self.assertEqual(report['diagnostics'], ['portfolio48-command-input-invalid'])

    def test_descriptor_reads_are_bounded_including_size_growth(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'input.json'; path.write_bytes(b'12345678')
            self.assertEqual(cli._read_cli_input(path, 8), b'12345678')
            with self.assertRaises(ValueError):
                cli._read_cli_input(path, 7)
            original = cli.os.fstat
            def grow_after_size_check(fd):
                info = original(fd)
                with path.open('ab') as stream:
                    stream.write(b'9')
                return info
            with patch.object(cli.os, 'fstat', side_effect=grow_after_size_check):
                with self.assertRaises(ValueError):
                    cli._read_cli_input(path, 8)

    def test_leaf_swap_after_safe_path_does_not_read_symlink_target(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            selected = root / 'map.json'; selected.write_bytes(b'{}')
            unselected = root / 'other.json'; unselected.write_bytes(b'authored-unselected')
            original = cli.safe_path
            def swap(path):
                checked = original(path)
                checked.unlink(); checked.symlink_to(unselected)
                return checked
            with patch.object(cli, 'safe_path', side_effect=swap):
                with self.assertRaises(OSError):
                    cli._read_cli_input(selected, 64)

    def test_checks_and_read_use_same_opened_descriptor(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'map.json'; path.write_bytes(b'original-authored')
            original = cli.os.open
            def open_then_replace(p, flags):
                fd = original(p, flags)
                Path(p).unlink()
                Path(p).write_bytes(b'replacement-authored')
                return fd
            with patch.object(cli.os, 'open', side_effect=open_then_replace):
                self.assertEqual(cli._read_cli_input(path, 64), b'original-authored')
            self.assertEqual(path.read_bytes(), b'replacement-authored')


if __name__ == '__main__':
    unittest.main()
