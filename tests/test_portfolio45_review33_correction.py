"""Only review33 F1/F2 regressions; all files/metadata are authored fixtures."""
import copy
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from offmenu.refresh import portfolio45 as p
from offmenu.refresh.core import canonical


class Review33CorrectionTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.input = self.root / 'metadata.json'
        self.input.write_bytes(b'[]')

    def test_regular_input_read_on_single_descriptor_without_path_reopen(self):
        with patch.object(Path, 'read_bytes', side_effect=AssertionError('path reopen')):
            self.assertEqual(p.read_metadata_input(self.input), b'[]')

    def test_symlink_ancestor_and_hardlink_rejected(self):
        linked = self.root / 'linked.json'
        linked.symlink_to(self.input)
        with self.assertRaises((ValueError, OSError)):
            p.read_metadata_input(linked)
        parent_link = self.root / 'parent'
        parent_link.symlink_to(self.root, target_is_directory=True)
        with self.assertRaises((ValueError, OSError)):
            p.read_metadata_input(parent_link / 'metadata.json')
        linked.unlink()
        os.link(self.input, linked)
        with self.assertRaises((ValueError, OSError)):
            p.read_metadata_input(self.input)

    def test_replacement_before_open_does_not_read_symlink_target(self):
        replacement = self.root / 'replacement.json'
        replacement.write_bytes(b' ' * 600000 + b'[]')
        original_open = os.open
        swapped = []
        def race(path, flags, *args, **kwargs):
            if path == self.input.name and not swapped:
                self.input.unlink()
                self.input.symlink_to(replacement)
                swapped.append(True)
            return original_open(path, flags, *args, **kwargs)
        with patch.object(os, 'open', race), patch.object(os, 'read', wraps=os.read) as reads:
            with self.assertRaises((ValueError, OSError)):
                p.read_metadata_input(self.input)
            self.assertEqual(reads.call_count, 0)
        self.assertTrue(swapped)

    def test_replacement_after_open_rejected_before_read(self):
        replacement = self.root / 'replacement.json'
        replacement.write_bytes(b'["different authored inode"]')
        original_open = os.open
        swapped = []
        def race(path, flags, *args, **kwargs):
            fd = original_open(path, flags, *args, **kwargs)
            if path == self.input.name and not swapped:
                self.input.unlink()
                self.input.symlink_to(replacement)
                swapped.append(True)
            return fd
        with patch.object(os, 'open', race), patch.object(os, 'read', wraps=os.read) as reads:
            with self.assertRaises((ValueError, OSError)):
                p.read_metadata_input(self.input)
            self.assertEqual(reads.call_count, 0)

    def test_growth_during_read_is_bounded_and_rejected(self):
        original_read = os.read
        lengths = []
        def grow(fd, count):
            if not lengths:
                self.input.write_bytes(b' ' * 600000 + b'[]')
            raw = original_read(fd, count)
            lengths.append(len(raw))
            return raw
        with patch.object(os, 'read', grow):
            with self.assertRaises(ValueError):
                p.read_metadata_input(self.input)
        self.assertLessEqual(sum(lengths), 16 * p.MAX_BYTES + 1)
        self.assertLessEqual(max(lengths), 65536)

    def test_fifo_cli_rejected_promptly_without_traceback(self):
        self.input.unlink()
        os.mkfifo(self.input)
        result = subprocess.run(
            [sys.executable, '-B', '-m', 'offmenu.refresh.portfolio45',
             '--input', str(self.input), '--as-of', '2026-10-18T00:00:00Z'],
            capture_output=True, text=True, timeout=2)
        self.assertEqual(result.returncode, 2)
        self.assertEqual(result.stdout, '')
        self.assertNotIn('Traceback', result.stderr)

    def test_recursive_descriptor_returns_malformed_and_preserves_valid_peer(self):
        binding = copy.deepcopy(p.catalog()['bindings'][4])
        binding.update(id='authored33', sourceId='authored33', holds=[],
                       originalAcquiredAt='2026-10-01T00:00:00Z')
        valid = p.template(binding)
        bad = copy.deepcopy(valid)
        nested = 0
        for _ in range(1100):
            nested = [nested]
        bad['row']['data']['authoredDeep'] = nested
        result = p.assess_many([bad, valid], as_of='2026-10-18T00:00:00Z', bindings=[binding])
        self.assertEqual([r['status'] for r in result], ['malformed', 'valid'])
        self.assertIn('malformed-descriptor', result[0]['diagnostics'])
        self.assertFalse(result[1]['datasetAccepted'])

    def test_unknown_recursive_identity_not_echoed_into_result(self):
        nested = []
        nested.append(nested)
        result = p.assess_many([{'bindingId': nested}], as_of='2026-10-18T00:00:00Z')
        self.assertIsNone(result[0]['bindingId'])
        canonical(result)  # Result remains serializable instead of retaining cycle.

    def test_deep_cli_json_decoder_fails_cleanly(self):
        self.input.write_bytes(b'[' * 20000 + b'0' + b']' * 20000)
        result = subprocess.run(
            [sys.executable, '-B', '-m', 'offmenu.refresh.portfolio45',
             '--input', str(self.input), '--as-of', '2026-10-18T00:00:00Z'],
            capture_output=True, text=True, timeout=2)
        self.assertEqual(result.returncode, 2)
        self.assertEqual(result.stdout, '')
        self.assertNotIn('Traceback', result.stderr)


if __name__ == '__main__':
    unittest.main()
