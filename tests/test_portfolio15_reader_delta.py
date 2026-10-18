"""Authored owned-reader regression and descriptor controls only."""
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from offmenu.refresh import portfolio15 as p
from offmenu.refresh.core import RefreshError, digest, sha
from tests.test_portfolio15_binding import contract


class ReaderDeltaTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.binding, self.raw = contract()
        self.path = self.root / 'metadata.json'
        self.path.write_bytes(self.raw)
        self.binding['evidence']['fixture']['recordedPath'] = str(self.path)

    def test_verify_then_reopen_regression(self):
        def replace_after_digest(path, **kwargs):
            result = digest(path, **kwargs)
            path.write_bytes(b'x' * (p.MAX_METADATA + 1))
            return result
        with patch.object(p, 'digest', side_effect=replace_after_digest, create=True):
            try:
                result = p.read_metadata(self.binding)
            except RefreshError:
                return
        self.assertEqual(result['fixture'], self.raw)
        self.assertEqual(sha(result['fixture']), self.binding['evidence']['fixture']['sha256'])

    def test_same_open_descriptor_survives_path_replacement(self):
        real_open = os.open
        def open_then_replace(path, flags, *args, **kwargs):
            fd = real_open(path, flags, *args, **kwargs)
            if path == self.path.name:
                self.path.rename(self.root / 'original.json')
                self.path.write_bytes(b'x' * (p.MAX_METADATA + 1))
            return fd
        with patch.object(p.os, 'open', side_effect=open_then_replace), patch.object(Path, 'read_bytes', side_effect=AssertionError('path reopen')):
            try:
                result = p.read_metadata(self.binding)
            except RefreshError:
                return  # Inode metadata mutation may be conservatively refused.
            self.assertEqual(result['fixture'], self.raw)

    def test_actual_buffer_sha_length_and_bound_refused(self):
        for raw in [b'x' * len(self.raw), self.raw[:-1], b'x' * (p.MAX_METADATA + 1)]:
            with self.subTest(size=len(raw)):
                self.path.write_bytes(raw)
                with self.assertRaises(RefreshError):
                    p.read_metadata(self.binding)

    def test_descriptor_growth_during_read_refused(self):
        real_fstat = os.fstat
        count = 0
        def grow(fd):
            nonlocal count
            count += 1
            before = real_fstat(fd)
            if count == 1:
                self.path.write_bytes(b'x' * (p.MAX_METADATA + 1))
            return before
        real_read = os.read
        returned = 0
        def bounded_read(fd, maximum):
            nonlocal returned
            self.assertLessEqual(maximum, p.MAX_METADATA + 1 - returned)
            chunk = real_read(fd, maximum)
            returned += len(chunk)
            return chunk
        with patch.object(p.os, 'fstat', side_effect=grow), patch.object(p.os, 'read', side_effect=bounded_read):
            with self.assertRaises(RefreshError):
                p.read_metadata(self.binding)
        self.assertLessEqual(returned, p.MAX_METADATA + 1)

    def test_fifo_refusal_and_healthy_cli_peer(self):
        fifo = self.root / 'fifo.json'
        os.mkfifo(fifo)
        good, _ = contract()
        bad, _ = contract()
        bad['id'], good['id'] = 'authored-fifo', 'authored-healthy'
        bad['evidence']['fixture']['recordedPath'] = str(fifo)
        good['evidence']['fixture']['recordedPath'] = str(self.path)
        from offmenu.refresh.core import canonical
        catalogue = self.root / 'authored-catalogue.json'
        catalogue.write_bytes(canonical({'schemaVersion': p.VERSION, 'bindings': [bad, good]}))
        code = ('import sys,json;from pathlib import Path;from offmenu.refresh import portfolio15 as p;'
                'p.CATALOGUE=json.loads(Path(sys.argv[1]).read_bytes());'
                'sys.argv=["portfolio15","--now","2026-10-18T00:00:00Z"];p.main()')
        run = subprocess.run([sys.executable, '-B', '-c', code, str(catalogue)],
            cwd=Path(__file__).resolve().parents[1], capture_output=True, text=True, timeout=5)
        import json
        self.assertEqual(run.returncode, 0, run.stderr)
        rows = [json.loads(line) for line in run.stdout.splitlines()]
        self.assertEqual([r['status'] for r in rows], ['MALFORMED', 'READY_METADATA_ONLY'])
        self.assertEqual(rows[0]['diagnostics'], ['metadata-read-or-custody-invalid'])
        self.assertNotIn(str(fifo), run.stdout)

    def test_symlink_and_directory_refused_missing_and_holds_preserved(self):
        self.path.unlink()
        self.path.symlink_to(self.root / 'target.json')
        with self.assertRaises(RefreshError):p.read_metadata(self.binding)
        self.path.unlink();self.path.mkdir()
        with self.assertRaises(RefreshError):p.read_metadata(self.binding)
        self.path.rmdir()
        self.assertEqual(p.read_metadata(self.binding), {})
        self.binding['metadataHeld'] = True
        with patch.object(p.os, 'open', side_effect=AssertionError('held input opened')):
            self.assertEqual(p.read_metadata(self.binding), {})
            self.binding['metadataHeld'] = False
            self.assertEqual(p.read_metadata(self.binding, operation='source-body'), {})

    def test_only_owned_descriptors_closed_on_success_and_refusals(self):
        real_open, real_close = os.open, os.close
        owned = set()
        def track_open(*a, **kw):
            fd = real_open(*a, **kw);owned.add(fd);return fd
        def track_close(fd):
            real_close(fd);owned.discard(fd)
        # Explicit os.close owns every fd in this reader, including the file fd.
        with patch.object(p.os, 'open', side_effect=track_open), patch.object(p.os, 'close', side_effect=track_close):
            self.assertEqual(p.read_metadata(self.binding)['fixture'], self.raw)
            self.path.write_bytes(b'bad')
            with self.assertRaises(RefreshError):p.read_metadata(self.binding)
            self.path.unlink();self.path.mkdir()
            with self.assertRaises(RefreshError):p.read_metadata(self.binding)
            self.path.rmdir();self.path.write_bytes(self.raw)
            with patch.object(p.os, 'read', side_effect=OSError('authored-path-secret')):
                with self.assertRaisesRegex(RefreshError, '^metadata-open-or-read-refused$'):
                    p.read_metadata(self.binding)
        self.assertEqual(owned, set())

    def test_final_symlink_swap_is_not_followed(self):
        real_open = os.open
        target = self.root / 'other.json'
        target.write_bytes(self.raw)
        def swap(path, flags, *args, **kwargs):
            if path == self.path.name:
                self.path.unlink()
                self.path.symlink_to(target)
            return real_open(path, flags, *args, **kwargs)
        with patch.object(p.os, 'open', side_effect=swap):
            with self.assertRaisesRegex(RefreshError, '^metadata-open-or-read-refused$'):
                p.read_metadata(self.binding)
