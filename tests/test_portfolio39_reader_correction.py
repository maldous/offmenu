"""Authored metadata only; bounded children cover both replacement races."""
import json
import os
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import patch

from offmenu.portfolio39.binding import MAX_METADATA_BYTES, read_metadata_json
from offmenu.refresh.core import RefreshError


class MetadataReaderCorrectionTests(TestCase):
    def test_regular_size_missing_and_symlink_controls(self):
        with TemporaryDirectory() as td:
            root = Path(td)
            regular = root / 'receipt.json'
            regular.write_bytes(b'x' * MAX_METADATA_BYTES)
            self.assertEqual(read_metadata_json(regular), b'x' * MAX_METADATA_BYTES)
            regular.write_bytes(b'x' * (MAX_METADATA_BYTES + 1))
            with self.assertRaises(RefreshError):
                read_metadata_json(regular)
            with self.assertRaises(FileNotFoundError):
                read_metadata_json(root / 'missing.json')
            link = root / 'link.json'
            link.symlink_to(regular)
            with self.assertRaises(RefreshError):
                read_metadata_json(link)

    def test_descriptor_closed_on_type_failure(self):
        with TemporaryDirectory() as td:
            target = Path(td) / 'receipt.json'
            os.mkfifo(target)
            actual_open = os.open
            opened = []
            def capture(*args, **kwargs):
                descriptor = actual_open(*args, **kwargs)
                opened.append(descriptor)
                return descriptor
            with patch('offmenu.portfolio39.binding.os.open', side_effect=capture):
                with self.assertRaises(RefreshError):
                    read_metadata_json(target)
            self.assertEqual(len(opened), 1)
            with self.assertRaises(OSError):
                os.fstat(opened[0])

    def test_both_readers_reject_fifo_and_replacements_without_hiding_peer(self):
        # Parent owns cleanup even if a regression forces subprocess timeout.
        program = r'''
import contextlib, io, json, os, sys
from dataclasses import replace
from pathlib import Path
from unittest.mock import patch
from offmenu.portfolio39.binding import bindings, read_retained_metadata, run_portfolio
from offmenu.portfolio39.__main__ import main
from offmenu.refresh.core import canonical, sha
root, reader, replacement = Path(sys.argv[1]), sys.argv[2], sys.argv[3]
target = root / 'receipt.json'
raw = canonical({'originalAcquiredAt': '2026-10-01T00:00:00Z',
                 'lastValidatedAt': '2026-10-17T00:00:00Z',
                 'nativeUnits': None, 'nativeBasis': None})
if replacement == 'direct':
    os.mkfifo(target)
else:
    target.write_bytes(raw)
good = root / 'good.json'
good.write_bytes(raw)
actual_open = os.open
swaps = []
def swap_open(path, flags, *args, **kwargs):
    if Path(path) == target and replacement != 'direct' and not swaps:
        target.unlink()
        if replacement == 'fifo': os.mkfifo(target)
        else: target.symlink_to(good)
        swaps.append(True)
    return actual_open(path, flags, *args, **kwargs)
with patch('offmenu.portfolio39.binding.os.open', side_effect=swap_open):
    if reader == 'retained':
        template = replace(bindings()[0], country='CX', metadata_bytes=len(raw),
            metadata_sha256=sha(raw), holds=(), acquisition_epoch_qualified=True,
            selectors={key:'/'+key for key in json.loads(raw)})
        bad = replace(template, source_id='bad', retained_metadata_path=str(target))
        valid = replace(template, source_id='good', retained_metadata_path=str(good))
        report = run_portfolio((bad, valid), read_retained_metadata,
                               now='2026-10-18T00:00:00Z')
        assert [r['outcome'] for r in report['bindings']] == ['missing', 'valid'], report
        assert not report['datasetAccepted'] and not report['goldAdmitted']
        assert report['rawBodyReads'] == report['networkRequests'] == 0
    else:
        output = io.StringIO()
        with patch('offmenu.portfolio39.__main__.bindings', return_value=()), contextlib.redirect_stdout(output):
            status = main(['--now', '2026-10-18T00:00:00Z', '--previous', str(target)])
        report = json.loads(output.getvalue())
        assert status == 2 and report['code'] == 'binding-cli-input-invalid', report
        assert report['networkRequests'] == 0 and not report['datasetAccepted']
assert bool(swaps) == (replacement != 'direct')
print(json.dumps({'reader':reader, 'case':replacement, 'passed':True}))
'''
        for reader in ('retained', 'previous'):
            for replacement in ('direct', 'fifo', 'symlink'):
                with self.subTest(reader=reader, replacement=replacement), TemporaryDirectory() as td:
                    env = {key: value for key, value in os.environ.items()
                           if not key.startswith('GIT_')}
                    run = subprocess.run([sys.executable, '-c', program, td, reader, replacement],
                                         capture_output=True, text=True, timeout=3, env=env)
                    self.assertEqual(run.returncode, 0, run.stderr + run.stdout)
                    self.assertTrue(json.loads(run.stdout)['passed'])
