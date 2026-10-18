"""Authored controls for W32-W44-7DD4-F1; no country source bodies."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from offmenu.refresh import portfolio44 as m
from offmenu.refresh.portfolio44_catalog import BINDINGS
from tests.test_portfolio44 import NOW
from tests.test_portfolio44_publication import Portfolio44PublicationTests


class Portfolio44ManifestTypeTests(unittest.TestCase):
    setup_output = Portfolio44PublicationTests.setup_output
    call = Portfolio44PublicationTests.call

    def test_wrong_type_manifest_only_is_preserved_without_candidate(self):
        for key, value in [('normalizedRecords', True), ('productionAdmission', 0)]:
            with self.subTest(field=key), tempfile.TemporaryDirectory() as t:
                b, raw, source, out, args = self.setup_output(Path(t))
                report, _ = m.bind_receipt(b, raw, validated_at=NOW, now=NOW)
                manifest_data = report['manifest'].copy()
                manifest_data[key] = value
                out.mkdir()
                manifest = out / 'manifest.json'
                manifest.write_text(json.dumps(manifest_data))
                before = manifest.read_bytes(), manifest.stat().st_mtime_ns
                with patch.dict(BINDINGS, authored=b):
                    code, diagnostic = self.call(args)
                self.assertEqual(code, 2)
                self.assertEqual(diagnostic['errors'], ['metadata-io-or-output-invalid'])
                self.assertEqual((manifest.read_bytes(), manifest.stat().st_mtime_ns), before)
                self.assertFalse((out / 'candidate.jsonl').exists())
                self.assertEqual(source.read_bytes(), raw)

    def test_readback_wrong_type_is_rejected(self):
        for key, value in [('normalizedRecords', True), ('productionAdmission', 0)]:
            with self.subTest(field=key), tempfile.TemporaryDirectory() as t:
                b, raw, source, out, args = self.setup_output(Path(t))
                report, content = m.bind_receipt(b, raw, validated_at=NOW, now=NOW)
                out.mkdir()
                manifest = out / 'manifest.json'
                manifest.write_text(json.dumps(report['manifest']))
                publish = m._publish_new
                injected = []
                def mutate_after_candidate(path, data):
                    publish(path, data)
                    if path == out / 'candidate.jsonl':
                        altered = report['manifest'].copy()
                        altered[key] = value
                        manifest.write_text(json.dumps(altered))
                        injected.append((manifest.read_bytes(), manifest.stat().st_mtime_ns))
                with patch.dict(BINDINGS, authored=b), patch.object(m, '_publish_new', mutate_after_candidate):
                    code, diagnostic = self.call(args)
                self.assertEqual(len(injected), 1)
                self.assertEqual(code, 2)
                self.assertEqual(diagnostic['errors'], ['metadata-io-or-output-invalid'])
                self.assertEqual((manifest.read_bytes(), manifest.stat().st_mtime_ns), injected[0])
                self.assertEqual((out / 'candidate.jsonl').read_bytes(), content)
                self.assertEqual(source.read_bytes(), raw)

    def test_reformatted_manifest_recovers_then_noops_without_rewrite(self):
        with tempfile.TemporaryDirectory() as t:
            b, raw, _, out, args = self.setup_output(Path(t))
            report, content = m.bind_receipt(b, raw, validated_at=NOW, now=NOW)
            out.mkdir()
            manifest = out / 'manifest.json'
            manifest.write_text(json.dumps(dict(reversed(list(report['manifest'].items()))), indent=4)+'\n')
            before = manifest.read_bytes(), manifest.stat().st_mtime_ns
            with patch.dict(BINDINGS, authored=b):
                code, recovered = self.call(args)
                self.assertEqual(code, 0)
                self.assertEqual(recovered['replay'], 'recovered-identical-partial')
                candidate = out / 'candidate.jsonl'
                original_candidate = candidate.read_bytes(), candidate.stat().st_mtime_ns
                code, noop = self.call(args)
            self.assertEqual(code, 0)
            self.assertEqual(noop['replay'], 'unchanged-no-op')
            self.assertEqual((manifest.read_bytes(), manifest.stat().st_mtime_ns), before)
            self.assertEqual((candidate.read_bytes(), candidate.stat().st_mtime_ns), original_candidate)
            self.assertEqual(candidate.read_bytes(), content)


if __name__ == '__main__':
    unittest.main()
