"""F1/F2 delta regressions: authored temporary files only, no source replay."""
import importlib.util
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

SCRIPT = Path(__file__).resolve().parents[1] / 'scripts/worker63_staging_bindings.py'
spec = importlib.util.spec_from_file_location('worker63_io', SCRIPT)
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


class IOCorrectionTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.path = self.root / 'report.json'

    def child(self, operation):
        # A regression that blocks is killed and reaped by subprocess.run.
        code = f'''import importlib.util, os
from pathlib import Path
from unittest.mock import patch
s = importlib.util.spec_from_file_location('bindings', {str(SCRIPT)!r})
m = importlib.util.module_from_spec(s); s.loader.exec_module(m)
p = Path({str(self.path)!r})
{operation}
'''
        result = subprocess.run([sys.executable, '-B', '-c', code],
                                capture_output=True, text=True, timeout=3,
                                env={**os.environ, 'PYTHONDONTWRITEBYTECODE': '1'})
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_existing_output_fifo_is_bounded(self):
        os.mkfifo(self.path)
        self.child("try: m.write_if_changed(p, {})\nexcept m.RefreshError as e: assert str(e) == 'binding-file-not-regular'\nelse: raise AssertionError('FIFO admitted')")

    def test_metadata_fifo_is_bounded(self):
        os.mkfifo(self.path)
        self.child("try: m.read_metadata(p)\nexcept m.RefreshError as e: assert str(e) == 'binding-file-not-regular'\nelse: raise AssertionError('FIFO admitted')")

    def test_open_descriptor_survives_fifo_replacement_and_detects_identity(self):
        self.path.write_bytes(b'{}')
        self.child('''original = os.read
replaced = False
def replace(fd, count):
    global replaced
    if not replaced:
        replaced = True; p.unlink(); os.mkfifo(p)
    return original(fd, count)
with patch.object(m.os, 'read', side_effect=replace):
    try: m.read_metadata(p)
    except m.RefreshError as e: assert str(e) == 'binding-file-changed-during-read'
    else: raise AssertionError('replacement admitted')''')

    def test_metadata_bound_checked_before_read(self):
        with self.path.open('wb') as stream:
            stream.truncate(m.MAX_METADATA + 1)
        with patch.object(m.os, 'read', side_effect=AssertionError('oversized read')):
            with self.assertRaisesRegex(m.RefreshError, 'binding-file-bound-exceeded'):
                m.read_metadata(self.path)

    def test_existing_report_bound_checked_before_read(self):
        with self.path.open('wb') as stream:
            stream.truncate(m.MAX_REPORT + 1)
        with patch.object(m.os, 'read', side_effect=AssertionError('oversized read')):
            with self.assertRaisesRegex(m.RefreshError, 'binding-file-bound-exceeded'):
                m.write_if_changed(self.path, {})

    def compete(self, competitor):
        original = os.open
        inserted = False

        def racing_open(name, flags, *args, **kwargs):
            nonlocal inserted
            if name == self.path.name and flags & os.O_EXCL and not inserted:
                inserted = True
                fd = original(name, flags, *args, **kwargs)
                try:
                    os.write(fd, competitor)
                finally:
                    os.close(fd)
            return original(name, flags, *args, **kwargs)

        with patch.object(m.os, 'open', side_effect=racing_open):
            return m.write_if_changed(self.path, {'generation': 1})

    def test_intervening_different_generation_is_preserved(self):
        competitor = b'{"other":true}\n'
        with self.assertRaisesRegex(m.RefreshError, 'binding-output-generation-conflict'):
            self.compete(competitor)
        self.assertEqual(self.path.read_bytes(), competitor)

    def test_intervening_identical_generation_is_noop(self):
        body = m.canonical({'generation': 1})
        self.assertEqual(self.compete(body), 'unchanged-no-op')
        self.assertEqual(self.path.read_bytes(), body)

    def test_new_generation_then_replay_preserves_mtime(self):
        self.assertEqual(m.write_if_changed(self.path, {}), 'metadata-report-written')
        before = self.path.stat().st_mtime_ns
        self.assertEqual(m.write_if_changed(self.path, {}), 'unchanged-no-op')
        self.assertEqual(self.path.stat().st_mtime_ns, before)
        raw, pin = m.read_metadata(self.path)
        self.assertEqual(pin['bytes'], len(raw))

    def test_final_symlink_is_rejected(self):
        target = self.root / 'target.json'
        target.write_bytes(b'{}')
        self.path.symlink_to(target)
        with self.assertRaisesRegex(m.RefreshError, 'symlink-path-rejected'):
            m.read_metadata(self.path)
        with self.assertRaisesRegex(m.RefreshError, 'symlink-path-rejected'):
            m.write_if_changed(self.path, {})
        self.assertEqual(target.read_bytes(), b'{}')
