"""PR48 comment4306286777: explicit depth, authored bytes only."""
import contextlib
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from offmenu.refresh import portfolio45 as p
from offmenu.refresh.core import canonical


class DepthDeltaTests(unittest.TestCase):
    def test_explicit_container_boundary_arrays_and_objects(self):
        raw = b'[' * p.MAX_JSON_DEPTH + b'0' + b']' * p.MAX_JSON_DEPTH
        value = p.load_metadata_json(raw)
        levels = 0
        while isinstance(value, list):
            levels += 1
            value = value[0]
        self.assertEqual(levels, p.MAX_JSON_DEPTH)
        mixed = b'{"k":[' * (p.MAX_JSON_DEPTH // 2) + b'0' + b']}' * (p.MAX_JSON_DEPTH // 2)
        p.load_metadata_json(mixed)
        with self.assertRaises(p.MetadataNestingError):
            p.load_metadata_json(b'[' + mixed + b']')

    def test_excess_depth_rejects_before_even_a_permissive_decoder(self):
        for levels in (p.MAX_JSON_DEPTH + 1, 20000):
            with self.subTest(levels=levels):
                raw = b'[' * levels + b'0' + b']' * levels
                with patch.object(p, 'strict_json', return_value=[]) as decoder:
                    with self.assertRaises(p.MetadataNestingError):
                        p.load_metadata_json(raw)
                    decoder.assert_not_called()

    def test_quotes_backslashes_and_structural_bytes_in_strings(self):
        value = {'literal': ('[]{}' * 1000) + '\\"' + '\\\\' + '"escaped"',
                 'unicode': 'braces { and [ with café', 'tail': [{'value': 0}]}
        raw = json.dumps(value, ensure_ascii=False).encode()
        self.assertEqual(p.load_metadata_json(raw), value)
        # JSON unicode escapes for quote/backslash remain inside the string.
        self.assertEqual(p.load_metadata_json(b'"\\u0022[]{}\\u005c"'), '"[]{}\\')

    def test_shared_json_syntax_and_duplicate_key_validation_preserved(self):
        for raw in (b'{"a":0,"a":1}', b'{"bad":NaN}', b'][', b'"unterminated'):
            with self.subTest(raw=raw), self.assertRaises(ValueError):
                p.load_metadata_json(raw)

    def test_actual_cli_depth_diagnostic_is_fixed(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'metadata.json'
            for levels in (p.MAX_JSON_DEPTH + 1, 20000):
                path.write_bytes(b'[' * levels + b'0' + b']' * levels)
                run = subprocess.run(
                    [sys.executable, '-B', '-m', 'offmenu.refresh.portfolio45',
                     '--input', str(path), '--as-of', '2026-10-18T00:00:00Z'],
                    capture_output=True, text=True, timeout=3)
                self.assertEqual(run.returncode, 2)
                self.assertEqual(run.stdout, '')
                self.assertEqual(run.stderr, 'metadata-input-invalid: json-nesting-limit\n')

    def test_cli_never_decodes_or_assesses_excess_depth(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'metadata.json'
            path.write_bytes(b'[' * 20000 + b'0' + b']' * 20000)
            args = ['portfolio45', '--input', str(path), '--as-of', '2026-10-18T00:00:00Z']
            stdout, stderr = io.StringIO(), io.StringIO()
            with patch.object(sys, 'argv', args), patch.object(p, 'strict_json', return_value=[]) as decoder, \
                    patch.object(p, 'assess_many') as assessor, \
                    contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
                with self.assertRaises(SystemExit) as exit_info:
                    p.main()
                self.assertEqual(exit_info.exception.code, 2)
                decoder.assert_not_called()
                assessor.assert_not_called()
            self.assertEqual(stdout.getvalue(), '')
            self.assertEqual(stderr.getvalue(), 'metadata-input-invalid: json-nesting-limit\n')

    def test_ordinary_metadata_cli_remains_held_without_source_io(self):
        descriptors = [p.template(b) for b in p.catalog()['bindings']]
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'metadata.json'
            path.write_bytes(canonical(descriptors))
            run = subprocess.run(
                [sys.executable, '-B', '-m', 'offmenu.refresh.portfolio45',
                 '--input', str(path), '--as-of', '2026-10-18T00:00:00Z'],
                capture_output=True, text=True, timeout=3)
            self.assertEqual(run.returncode, 0, run.stderr)
            result = json.loads(run.stdout)
            self.assertEqual(len(result), 7)
            self.assertTrue(all(r['status'] == 'held' and not r['datasetAccepted'] for r in result))
            self.assertTrue(all(r['networkRequests'] == 0 for r in result))


if __name__ == '__main__':
    unittest.main()
