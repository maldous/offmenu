"""Focused W19-W36-F1/F2 authored regressions; no retained data inputs."""
import fcntl
import hashlib
import json
import os
from pathlib import Path
import stat
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from offmenu.refresh import portfolio36 as lane


class ReplayGuards(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.metadata = self.root / 'metadata'
        self.workspace = self.root / 'workspace'
        self.metadata.mkdir()
        self.workspace.mkdir()
        self.raw = b'{"release":"authored-v1","basis":null}'
        self.input = self.metadata / 'metadata.json'
        self.input.write_bytes(self.raw)
        self.config = {'schemaVersion': 'offmenu-portfolio36/1', 'scope': 'metadata-only',
            'sources': [{'sourceId': 'authored', 'releaseId': 'authored-v1', 'country': 'SV',
                'domain': 'prices/baskets', 'originalAcquiredAt': '2026-01-01T00:00:00Z',
                'inputs': [{'path': 'metadata.json', 'bytes': len(self.raw),
                            'sha256': hashlib.sha256(self.raw).hexdigest()}],
                'fields': {'release': {'input': 'metadata.json', 'selector': '/release'},
                           'basis': {'input': 'metadata.json', 'selector': '/basis'}},
                'holds': [], 'payloadBlockers': ['authored-no-admission']}]}

    def replay(self):
        return lane.replay(self.config, self.metadata, self.workspace,
                           now='2026-01-02T00:00:00Z')

    def test_F1_hardlink_lock_rejected_without_input_mutation(self):
        lock = self.workspace / 'owner36.lock'
        os.link(self.input, lock)
        with self.assertRaisesRegex(ValueError, '^binding-lock-invalid$'):
            self.replay()
        self.assertEqual(self.input.read_bytes(), self.raw)
        self.assertEqual(lock.read_bytes(), self.raw)
        self.assertFalse((self.workspace / 'binding-manifest.json').exists())
        self.assertFalse((self.workspace / 'diagnostics.json').exists())

    def test_F1_regular_lock_never_truncated_and_competing_writer_rejected(self):
        lock = self.workspace / 'owner36.lock'
        lock.write_bytes(b'preserve-existing-lock-bytes')
        self.assertEqual(self.replay()['status'], 'metadata-bindings-written')
        self.assertEqual(lock.read_bytes(), b'preserve-existing-lock-bytes')
        with lock.open('rb') as stream:
            fcntl.flock(stream.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            with self.assertRaisesRegex(ValueError, '^binding-lock-held$'):
                self.replay()
        self.assertEqual(self.input.read_bytes(), self.raw)

    def _fifo_child(self, filename, expected):
        target = self.workspace / filename
        os.mkfifo(target)
        config = self.root / 'authored-config.json'
        config.write_text(json.dumps(self.config))
        code = ('import json,sys;sys.path.insert(0,sys.argv[1]);'
                'from offmenu.refresh.portfolio36 import replay;'
                'from pathlib import Path;'
                '\ntry: replay(json.loads(Path(sys.argv[2]).read_text()),sys.argv[3],sys.argv[4],'
                'now="2026-01-02T00:00:00Z")'
                '\nexcept ValueError as e: print(str(e));sys.exit(2)')
        command = [sys.executable, '-I', '-B', '-c', code,
                   str(Path(__file__).resolve().parents[1]), str(config),
                   str(self.metadata), str(self.workspace)]
        result = subprocess.run(command, capture_output=True, text=True, timeout=2)
        self.assertEqual(result.returncode, 2, result.stderr)
        self.assertEqual(result.stdout.strip(), expected)
        self.assertTrue(stat.S_ISFIFO(target.stat().st_mode))
        self.assertEqual(self.input.read_bytes(), self.raw)

    def test_F1_fifo_lock_rejected_without_blocking(self):
        self._fifo_child('owner36.lock', 'binding-lock-invalid')

    def test_F2_fifo_previous_manifest_rejected_without_blocking(self):
        self._fifo_child('binding-manifest.json', 'replay-manifest-not-regular')

    def test_F2_oversized_previous_manifest_preserved(self):
        path = self.workspace / 'binding-manifest.json'
        raw = b'x' * 129
        path.write_bytes(raw)
        with patch.object(lane, 'MAX_MANIFEST', 128):
            with self.assertRaisesRegex(ValueError, '^replay-manifest-byte-limit$'):
                self.replay()
        self.assertEqual(path.read_bytes(), raw)

    def test_F2_invalid_json_manifest_preserved(self):
        path = self.workspace / 'binding-manifest.json'
        path.write_bytes(b'{not-json')
        with self.assertRaisesRegex(ValueError, '^replay-manifest-invalid$'):
            self.replay()
        self.assertEqual(path.read_bytes(), b'{not-json')

    def test_F2_changed_opened_manifest_fails_without_replacing_it(self):
        self.replay()
        path = self.workspace / 'binding-manifest.json'
        old = path.read_bytes()
        real_fstat = lane.os.fstat
        # Mutate only this authored opened manifest between its pre/post checks.
        calls = []
        def changing_stat(fd):
            value = real_fstat(fd)
            if value.st_ino == path.stat().st_ino:
                calls.append(fd)
                if len(calls) == 2:
                    path.write_bytes(old + b' ')
                    return real_fstat(fd)
            return value
        with patch.object(lane.os, 'fstat', side_effect=changing_stat):
            with self.assertRaisesRegex(ValueError, '^replay-manifest-changed$'):
                self.replay()
        self.assertEqual(path.read_bytes(), old + b' ')

    def test_positive_noop_stale_age_and_last_good_manifest_preserved(self):
        self.assertEqual(self.replay()['status'], 'metadata-bindings-written')
        path = self.workspace / 'binding-manifest.json'
        raw = path.read_bytes()
        before = path.stat().st_mtime_ns
        later = lane.replay(self.config, self.metadata, self.workspace,
                            now='2026-02-01T00:00:00Z')
        self.assertEqual(later['status'], 'verified-no-op')
        self.assertEqual(path.stat().st_mtime_ns, before)
        self.assertEqual(path.read_bytes(), raw)
        self.assertEqual(later['diagnostics']['sources'][0]['status'], 'stale-input')
        self.input.unlink()
        self.assertEqual(self.replay()['status'], 'isolated-failures')
        self.assertEqual(path.read_bytes(), raw)


if __name__ == '__main__':
    unittest.main()
