"""Authored inode fixtures for the shared publication lock."""
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from offmenu.refresh import core


class WriterLockPreservationTest(unittest.TestCase):
    def setUp(self):
        self.scratch = tempfile.TemporaryDirectory()
        self.addCleanup(self.scratch.cleanup)
        self.root = Path(self.scratch.name)
        self.lock = self.root / 'writer.lock'
        self.source = self.root / 'metadata.json'
        self.source.write_bytes(b'{"authored":true}\n')

    def snapshot(self):
        value = self.source.stat()
        return self.source.read_bytes(), value.st_mtime_ns, value.st_ino

    def test_hardlinked_input_is_rejected_without_mutation(self):
        os.link(self.source, self.lock)
        before = self.snapshot()
        with self.assertRaisesRegex(core.RefreshError, 'unsafe-writer-lock'):
            with core.writer_lock(self.lock):
                self.fail('aliased lock was admitted')
        self.assertEqual(self.snapshot(), before)

    def test_nonregular_fifo_is_rejected_and_retained(self):
        os.mkfifo(self.lock)
        before = self.lock.lstat()
        with self.assertRaisesRegex(core.RefreshError, 'unsafe-writer-lock'):
            with core.writer_lock(self.lock):
                self.fail('nonregular lock was admitted')
        self.assertEqual(self.lock.lstat().st_ino, before.st_ino)

    def test_link_added_during_lock_acquisition_is_rejected(self):
        self.lock.write_bytes(b'original lock bytes')
        before = self.lock.read_bytes()
        real_flock = core.fcntl.flock

        def add_alias(descriptor, operation):
            real_flock(descriptor, operation)
            os.link(self.lock, self.root / 'new-alias')

        with patch.object(core.fcntl, 'flock', side_effect=add_alias):
            with self.assertRaisesRegex(core.RefreshError, 'unsafe-writer-lock'):
                with core.writer_lock(self.lock):
                    self.fail('newly aliased lock was admitted')
        self.assertEqual(self.lock.read_bytes(), before)

    def test_regular_lock_retains_inode_and_content_on_contention(self):
        with core.writer_lock(self.lock):
            inode = self.lock.stat().st_ino
            body = self.lock.read_bytes()
            with self.assertRaisesRegex(core.RefreshError, 'writer-lock-held'):
                with core.writer_lock(self.lock):
                    self.fail('concurrent writer was admitted')
            self.assertEqual(self.lock.read_bytes(), body)
        with core.writer_lock(self.lock):
            self.assertEqual(self.lock.stat().st_ino, inode)
        self.assertEqual(self.lock.stat().st_ino, inode)


if __name__ == '__main__':
    unittest.main()
