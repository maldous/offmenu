"""Authored PR48 partial-publication recovery probes, no source data."""
from dataclasses import replace
import io
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from offmenu.refresh import portfolio44 as m
from offmenu.refresh.portfolio44_catalog import BINDINGS
from tests.test_portfolio44 import fixture, NOW


class Portfolio44PublicationTests(unittest.TestCase):
    def setup_output(self, root):
        b, raw = fixture()
        source = root / 'receipt.json'
        source.write_bytes(raw)
        b = replace(b, metadata_path=str(source))
        out = root / 'output'
        args = ['--binding', 'authored', '--validated-at', NOW, '--now', NOW,
                '--output', str(out)]
        return b, raw, source, out, args

    def call(self, args):
        with patch('sys.stdout', new_callable=io.StringIO) as stdout:
            code = m.main(args)
        return code, json.loads(stdout.getvalue())

    def test_manifest_publication_failure_then_identical_retry(self):
        with tempfile.TemporaryDirectory() as t:
            b, raw, source, out, args = self.setup_output(Path(t))
            original_open, original_link = Path.open, os.link
            failed = False
            def fail_open(path, *a, **kw):
                nonlocal failed
                if path == out / 'manifest.json' and (a[0] if a else kw.get('mode')) == 'xb':
                    failed = True
                    raise OSError('authored manifest publication failure')
                return original_open(path, *a, **kw)
            def fail_link(src, dst, *a, **kw):
                nonlocal failed
                if Path(dst) == out / 'manifest.json':
                    failed = True
                    raise OSError('authored manifest publication failure')
                return original_link(src, dst, *a, **kw)
            with patch.dict(BINDINGS, authored=b):
                with patch.object(Path, 'open', fail_open), patch.object(os, 'link', fail_link):
                    first, diagnostic = self.call(args)
                self.assertEqual(first, 2)
                self.assertTrue(failed)
                candidate = out / 'candidate.jsonl'
                self.assertTrue(candidate.is_file())
                self.assertFalse((out / 'manifest.json').exists())
                original = candidate.read_bytes(), candidate.stat().st_mtime_ns
                retry, report = self.call(args)
                self.assertEqual(retry, 0)
                self.assertEqual(report['replay'], 'recovered-identical-partial')
                self.assertFalse(report['sourceAcceptance'])
                self.assertEqual((candidate.read_bytes(), candidate.stat().st_mtime_ns), original)
                manifest = out / 'manifest.json'
                self.assertEqual(json.loads(manifest.read_bytes()), report['manifest'])
                manifest_time = manifest.stat().st_mtime_ns
                code, again = self.call(args)
                self.assertEqual(code, 0)
                self.assertEqual(again['replay'], 'unchanged-no-op')
                self.assertEqual(manifest.stat().st_mtime_ns, manifest_time)
                self.assertEqual(source.read_bytes(), raw)

    def test_manifest_staging_failure_leaves_no_final_partial_manifest(self):
        with tempfile.TemporaryDirectory() as t:
            b, raw, _, out, args = self.setup_output(Path(t))
            fsync, calls = os.fsync, 0
            def fail_second(fd):
                nonlocal calls
                calls += 1
                if calls == 2:
                    raise OSError('authored manifest fsync failure')
                return fsync(fd)
            with patch.dict(BINDINGS, authored=b):
                with patch.object(os, 'fsync', fail_second):
                    code, _ = self.call(args)
                self.assertEqual(code, 2)
                self.assertTrue((out / 'candidate.jsonl').is_file())
                self.assertFalse((out / 'manifest.json').exists())
                self.assertEqual(sorted(p.name for p in out.iterdir()), ['candidate.jsonl'])
                self.assertEqual(self.call(args)[0], 0)

    def test_mismatching_partial_outputs_and_aliases_are_preserved(self):
        for mode in ('wrong-candidate', 'wrong-manifest', 'symlink-candidate', 'hardlink-manifest'):
            with self.subTest(mode=mode), tempfile.TemporaryDirectory() as t:
                b, raw, source, out, args = self.setup_output(Path(t))
                out.mkdir()
                if mode == 'wrong-candidate':
                    target = out / 'candidate.jsonl'
                    target.write_bytes(b'other output')
                elif mode == 'wrong-manifest':
                    target = out / 'manifest.json'
                    target.write_bytes(b'{"foreign":true}')
                elif mode == 'symlink-candidate':
                    target = out / 'candidate.jsonl'
                    target.symlink_to(source)
                else:
                    target = out / 'manifest.json'
                    os.link(source, target)
                before = target.read_bytes(), target.stat().st_mtime_ns
                with patch.dict(BINDINGS, authored=b):
                    code, report = self.call(args)
                self.assertEqual(code, 2)
                self.assertEqual(report['errors'], ['metadata-io-or-output-invalid'])
                self.assertEqual((target.read_bytes(), target.stat().st_mtime_ns), before)
                self.assertEqual(source.read_bytes(), raw)
                self.assertEqual(len(list(out.iterdir())), 1)

    def test_identical_manifest_only_recovers_without_rewrite(self):
        with tempfile.TemporaryDirectory() as t:
            b, raw, _, out, args = self.setup_output(Path(t))
            report, content = m.bind_receipt(b, raw, validated_at=NOW, now=NOW)
            out.mkdir()
            manifest = out / 'manifest.json'
            manifest.write_text(json.dumps(report['manifest']))
            before = manifest.read_bytes(), manifest.stat().st_mtime_ns
            with patch.dict(BINDINGS, authored=b):
                code, recovered = self.call(args)
            self.assertEqual(code, 0)
            self.assertEqual(recovered['replay'], 'recovered-identical-partial')
            self.assertEqual((manifest.read_bytes(), manifest.stat().st_mtime_ns), before)
            self.assertEqual((out / 'candidate.jsonl').read_bytes(), content)


if __name__ == '__main__':
    unittest.main()
