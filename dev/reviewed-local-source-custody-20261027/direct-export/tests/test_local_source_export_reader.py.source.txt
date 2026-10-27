"""Focused regression for equal-metadata same-length source changes."""
import importlib.util
from pathlib import Path
import tempfile
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location('export_reader', ROOT / 'scripts/export-local-source.py')
export = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(export)


class DescriptorReread(unittest.TestCase):
    def test_same_length_change_rejected_even_when_metadata_is_unchanged(self):
        with tempfile.TemporaryDirectory() as temporary:
            target = Path(temporary) / 'source.py'
            target.write_bytes(b'original')
            same_stat = target.stat()
            original_read = export.os.read
            changed = False

            def read_then_change(fd, count):
                nonlocal changed
                result = original_read(fd, count)
                if result and not changed:
                    changed = True
                    target.write_bytes(b'changed!')
                return result

            with mock.patch.object(export.os, 'fstat', return_value=same_stat), \
                    mock.patch.object(export.os, 'read', side_effect=read_then_change):
                with self.assertRaisesRegex(export.Rejected, '^file-changed-during-read$'):
                    export.read_regular(str(target))

    def test_stable_content_accepts_short_reads_on_the_same_descriptor(self):
        with tempfile.TemporaryDirectory() as temporary:
            target = Path(temporary) / 'source.py'
            body = b'unchanged source'
            target.write_bytes(body)
            original_read = export.os.read
            descriptors = set()

            def short_read(fd, count):
                descriptors.add(fd)
                return original_read(fd, min(count, 3))

            with mock.patch.object(export.os, 'read', side_effect=short_read):
                actual, _ = export.read_regular(str(target))
            self.assertEqual(actual, body)
            self.assertEqual(len(descriptors), 1)


if __name__ == '__main__':
    unittest.main()
