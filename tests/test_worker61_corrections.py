"""Reviewer49 F1/F2/F3 regressions; authored bytes and temporary files only."""
import copy
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from offmenu.portfolios import worker61 as module
from offmenu.refresh.core import canonical

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / 'tests/fixtures/worker61'
NOW = '2026-10-18T00:00:00Z'


class Worker61CorrectionTests(unittest.TestCase):
    def child(self, code=None, args=None):
        # subprocess.run kills AND reaps on timeout: a failed regression leaves
        # no waiting FIFO reader behind. No actual source is opened in children.
        command = [sys.executable, '-B'] + (['-c', code] if code is not None else args)
        return subprocess.run(command, cwd=ROOT, capture_output=True, text=True, timeout=3)

    def report(self, raw, *, validated_at=None):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / 'bad.json').write_bytes(raw)
            (root / 'good.json').write_bytes((FIXTURES / 'receipt.json').read_bytes())
            config = json.loads((FIXTURES / 'valid.json').read_text())
            bad = config['sources'][0]
            bad.update(sourceId='authored-bad')
            bad['manifest'] = {'path': 'bad.json', 'bytes': len(raw),
                               'sha256': hashlib.sha256(raw).hexdigest()}
            if validated_at is not None:
                bad['validatedAt'] = validated_at
            peer = json.loads((FIXTURES / 'valid.json').read_text())['sources'][0]
            peer['manifest']['path'] = 'good.json'
            config['sources'].append(peer)
            report = module.assess(config, root, now=NOW)
            self.assertEqual(report['results'][1]['status'], 'metadata-bound')
            # Both serialization and the actual report writer must work.
            canonical(report)
            self.assertEqual(module.write_report(root / 'report.json', report), 'written')
            self.assertEqual(module.write_report(root / 'report.json', report), 'no-op')
            return report

    def test_f1_cli_config_fifo_rejected_without_waiting(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); fifo = root / 'config.json'; os.mkfifo(fifo)
            result = self.child(args=['-m', 'offmenu.portfolios.worker61', '--config', str(fifo),
                '--metadata-root', str(root), '--now', NOW, '--output', str(root / 'report.json')])
            self.assertEqual(result.returncode, 2, result.stderr)
            self.assertIn('config-not-bounded-regular-file', result.stderr)
            self.assertFalse((root / 'report.json').exists())

    def test_f1_existing_report_fifo_rejected_without_waiting(self):
        with tempfile.TemporaryDirectory() as tmp:
            fifo = Path(tmp) / 'report.json'; os.mkfifo(fifo)
            result = self.child(code=f'''from pathlib import Path
from offmenu.portfolios.worker61 import write_report
try:
    write_report(Path({str(fifo)!r}), {{'authored': True}})
except ValueError as error:
    assert str(error) == 'regular-file-required'
else:
    raise AssertionError('FIFO accepted')
''')
            self.assertEqual(result.returncode, 0, result.stderr)

    def test_f1_replacement_before_open_is_nonblocking_and_peer_survives(self):
        result = self.child(code='''import copy, hashlib, json, os, tempfile
from pathlib import Path
from unittest.mock import patch
from offmenu.portfolios import worker61 as m
from offmenu.refresh.core import canonical
with tempfile.TemporaryDirectory() as tmp:
    root=Path(tmp); raw=b'{"title":"authored","unit":null,"basis":null,"acquiredAt":"2026-10-01T00:00:00Z"}'
    (root/'bad.json').write_bytes(raw)
    config=json.loads(Path('tests/fixtures/worker61/valid.json').read_text())
    bad=config['sources'][0]; bad['sourceId']='bad'
    bad['manifest']={'path':'bad.json','bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()}
    peer=json.loads(Path('tests/fixtures/worker61/valid.json').read_text())['sources'][0]
    peer['manifest']['path']='good.json'
    (root/'good.json').write_bytes(Path('tests/fixtures/worker61/receipt.json').read_bytes())
    config['sources'].append(peer)
    original=os.open
    def replace(path, flags, *args, **kwargs):
        if path=='bad.json':
            (root/'bad.json').unlink(); os.mkfifo(root/'bad.json')
        return original(path, flags, *args, **kwargs)
    with patch.object(m.os,'open',replace):
        report=m.assess(config,root,now='2026-10-18T00:00:00Z')
    assert [r['status'] for r in report['results']]==['invalid','metadata-bound']
    canonical(report)
''')
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_f1_opened_regular_descriptor_not_reopened_after_rename(self):
        result = self.child(code='''import hashlib, os, tempfile
from pathlib import Path
from unittest.mock import patch
from offmenu.portfolios import worker61 as m
with tempfile.TemporaryDirectory() as tmp:
    root=Path(tmp); path=root/'receipt.json'; raw=b'{"authored":true}'; path.write_bytes(raw)
    original=os.open; opens=[]
    def replace(pathname, flags, *args, **kwargs):
        fd=original(pathname,flags,*args,**kwargs)
        if pathname=='receipt.json':
            opens.append(pathname); path.unlink(); os.mkfifo(path)
        return fd
    with patch.object(m.os,'open',replace):
        value=m._metadata(root,{'path':'receipt.json','bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()})
    assert value=={'authored':True}
    assert len(opens)==1
''')
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_f1_regular_read_bounds_type_and_symlink_controls(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); path = root / 'x'; path.write_bytes(b'1234')
            with self.assertRaisesRegex(ValueError, 'runtime-input-too-large'):
                module.read_regular(path, 3)
            self.assertEqual(module.read_regular(path, 4), b'1234')
            with self.assertRaisesRegex(ValueError, 'regular-file-required'):
                module.read_regular(root, 4)
            (root / 'link').symlink_to(path)
            with self.assertRaises(ValueError):
                module.read_regular(root / 'link', 4)

    def test_f2_positive_negative_overflow_cleared_and_report_writable(self):
        for number in [b'1e999', b'-1e999']:
            with self.subTest(number=number):
                raw = (b'{"title":' + number + b',"unit":null,"basis":null,'
                       b'"acquiredAt":"2026-10-01T00:00:00Z"}')
                report = self.report(raw)
                bad = report['results'][0]
                self.assertIn('field-selector-missing:title', bad['diagnostics'])
                self.assertIsNone(bad['fields']['title']['value'])
                self.assertNotIn('title', bad['stagingReference']['data'])
                self.assertNotIn('Infinity', canonical(report).decode())

    def test_f3_invalid_acquisition_values_never_attached_or_echoed(self):
        marker = 'AUTHORED_PRIVATE_MARKER'
        for value in [{'private': marker}, marker * 400, 12, True,
                      marker, '2026-10-01T00:00:00', '2026-11-01T00:00:00Z']:
            with self.subTest(valueType=type(value).__name__):
                raw = json.dumps({'title': 'authored', 'unit': None, 'basis': None,
                                  'acquiredAt': value}).encode()
                report = self.report(raw)
                self.assertEqual(report['results'][0]['status'], 'invalid')
                self.assertIsNone(report['results'][0]['cache']['originalAcquiredAt'])
                self.assertNotIn(marker, canonical(report).decode())

    def test_f3_validation_clock_validated_before_attachment(self):
        report = self.report((FIXTURES / 'receipt.json').read_bytes(),
                             validated_at='AUTHORED_PRIVATE_MARKER')
        self.assertIsNone(report['results'][0]['cache']['validatedAt'])
        self.assertNotIn('AUTHORED_PRIVATE_MARKER', canonical(report).decode())

    def test_positive_metadata_clocks_origins_and_noop_unchanged(self):
        report = self.report((FIXTURES / 'receipt.json').read_bytes())
        for row in report['results']:
            self.assertEqual(row['status'], 'metadata-bound')
            self.assertEqual(row['cache']['originalAcquiredAt'], '2026-10-01T00:00:00Z')
            self.assertEqual(row['cache']['validatedAt'], '2026-10-17T00:00:00Z')
            self.assertEqual(row['fieldOriginErrors'], [])
            self.assertFalse(row['sourceProcessingAuthorized'])
        self.assertFalse(report['countryAccepted'])
        self.assertEqual(report['sourceBodyReads'], 0)


if __name__ == '__main__':
    unittest.main()
