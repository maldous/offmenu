"""Focused W22-R42-F1 regressions, using authored metadata only."""
from contextlib import redirect_stdout
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from offmenu.refresh import portfolio22 as p
from offmenu.refresh.core import canonical


NOW = '2026-10-18T12:00:00Z'


class Portfolio22IngressTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.path = self.root / 'metadata.json'
        evidence = p.expected_evidence('CF')
        evidence['lastValidatedAt'] = '2026-10-17T12:00:00Z'
        self.raw = canonical(evidence)
        self.path.write_bytes(self.raw)

    def cli(self, path=None):
        output = io.StringIO()
        with patch.object(sys, 'argv', ['portfolio22', 'CF', str(path or self.path), '--now', NOW]):
            with redirect_stdout(output):
                code = p.main()
        return code, json.loads(output.getvalue())

    def test_valid_missing_oversize_and_directory_have_typed_cli_results(self):
        self.assertEqual(self.cli()[0], 0)
        self.assertEqual(self.cli()[1]['state'], 'ready')
        self.path.write_bytes(b'x' * (p.MAX_METADATA + 1))
        for path in (self.path, self.root / 'absent.json', self.root):
            with self.subTest(path=path):
                code, report = self.cli(path)
                self.assertEqual(code, 2)
                self.assertEqual(report['stage']['code'], 'metadata-input-unreadable')

    def test_growth_after_fstat_caps_actual_bytes_and_closes_descriptor(self):
        original_fstat, original_read = os.fstat, os.read
        descriptors, reads = [], []

        def grow(descriptor):
            before = original_fstat(descriptor)
            descriptors.append(descriptor)
            with self.path.open('ab') as stream:
                stream.write(b' ' * (2 * p.MAX_METADATA))
            return before

        def measured_read(descriptor, count):
            raw = original_read(descriptor, count)
            reads.append((count, len(raw)))
            return raw

        with patch.object(p.os, 'fstat', side_effect=grow):
            with patch.object(p.os, 'read', side_effect=measured_read):
                code, report = self.cli()
        self.assertEqual((code, report['stage']['code']), (2, 'metadata-input-unreadable'))
        self.assertEqual(sum(size for _, size in reads), p.MAX_METADATA + 1)
        self.assertTrue(all(count <= p.MAX_METADATA + 1 for count, _ in reads))
        self.assertEqual(len(descriptors), 1)
        with self.assertRaises(OSError):
            original_fstat(descriptors[0])

    def test_short_reads_share_one_total_budget(self):
        original_read = os.read
        reads = []

        def short_read(descriptor, count):
            raw = original_read(descriptor, min(count, 31))
            reads.append(len(raw))
            return raw

        with patch.object(p.os, 'read', side_effect=short_read):
            self.assertEqual(p._read_metadata(self.path), self.raw)
        self.assertEqual(sum(reads), len(self.raw))

    def test_path_swap_after_open_uses_same_regular_descriptor(self):
        original_fstat = os.fstat

        def swap(descriptor):
            opened = original_fstat(descriptor)
            self.path.rename(self.root / 'opened.json')
            os.mkfifo(self.path)
            return opened

        with patch.object(p.os, 'fstat', side_effect=swap):
            self.assertEqual(p._read_metadata(self.path), self.raw)

    def test_symlink_swap_at_open_is_refused_without_read(self):
        original_open = os.open
        target = self.root / 'target.json'
        target.write_bytes(self.raw)

        def swap(path, flags):
            self.path.unlink()
            self.path.symlink_to(target)
            return original_open(path, flags)

        with patch.object(p.os, 'open', side_effect=swap):
            with patch.object(p.os, 'read', side_effect=AssertionError('must not read symlink')):
                code, report = self.cli()
        self.assertEqual((code, report['stage']['code']), (2, 'metadata-input-unreadable'))

    def test_fifo_cli_is_bounded_and_typed(self):
        self.path.unlink()
        os.mkfifo(self.path)
        result = subprocess.run(
            [sys.executable, '-B', '-m', 'offmenu.refresh.portfolio22', 'CF', str(self.path), '--now', NOW],
            capture_output=True, text=True, timeout=2)
        self.assertEqual(result.returncode, 2, result.stderr)
        self.assertEqual(json.loads(result.stdout)['stage']['code'], 'metadata-input-unreadable')


if __name__ == '__main__':
    unittest.main()
