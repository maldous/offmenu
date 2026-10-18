"""Authored W21-W23-READER-01 regressions; no retained source inputs."""
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from offmenu.refresh import core
from offmenu.refresh.portfolios import worker23 as binding


class Worker23ReaderCorrectionTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix='w23-reader-test-')
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.raw = core.canonical({'country': 'CI', 'value': 0})
        self.target = self.root / 'allowed.json'
        self.target.write_bytes(self.raw)

    def spec(self, name, path):
        return {'id': name, 'country': 'CI', 'sourceId': 'authored-ci',
                'releaseId': 'authored-only-v1',
                'metadataAsset': {'path': str(path), 'bytes': len(self.raw),
                                  'sha256': core.sha(self.raw), 'role': 'retained-metadata'},
                'selectors': {'value': '/value'}, 'nativeSemantics': {'basis': None},
                'originalAcquiredAt': '2026-10-01T00:00:00Z',
                'metadataValidatedAt': None, 'payloadHolds': ['fixture-held']}

    def test_regular_read_bound_and_descriptor_cleanup(self):
        actual_open, actual_close = os.open, os.close
        live = set()

        def opened(*args, **kwargs):
            fd = actual_open(*args, **kwargs)
            live.add(fd)
            return fd

        def closed(fd):
            live.remove(fd)
            return actual_close(fd)

        with patch.object(binding.os, 'open', side_effect=opened), \
                patch.object(binding.os, 'close', side_effect=closed):
            self.assertEqual(binding._read_metadata(self.target), self.raw)
            self.assertFalse(live)
            self.target.write_bytes(b'x' * (binding.MAX_METADATA_BYTES + 1))
            with self.assertRaises(core.RefreshError):
                binding._read_metadata(self.target)
            self.assertFalse(live)

    def test_leaf_symlink_replacement_never_reads_canary_and_peer_continues(self):
        canary = self.root / 'outside-allowlist.json'
        canary.write_bytes(self.raw)  # Same pin cannot legitimize following it.
        peer = self.root / 'peer.json'
        peer.write_bytes(self.raw)
        original_stat, original_read = os.stat, os.read
        swapped = False
        canary_read = False

        def replace_after_stat(path, *args, **kwargs):
            nonlocal swapped
            result = original_stat(path, *args, **kwargs)
            if path == self.target.name and kwargs.get('dir_fd') is not None and not swapped:
                swapped = True
                self.target.unlink()
                self.target.symlink_to(canary)
            return result

        def read(fd, size):
            nonlocal canary_read
            canary_read |= os.fstat(fd).st_ino == original_stat(canary).st_ino
            return original_read(fd, size)

        specs = [self.spec('a-replaced', self.target), self.spec('b-peer', peer)]
        with patch.object(binding.os, 'stat', side_effect=replace_after_stat), \
                patch.object(binding.os, 'read', side_effect=read), \
                patch.object(binding, 'registry', return_value={'sources': specs}):
            report = binding.run(now='2026-10-18T00:00:00Z')
        self.assertTrue(swapped)
        self.assertFalse(canary_read)
        self.assertEqual([r['status'] for r in report['sources']], ['malformed', 'valid'])
        self.assertEqual(report['sources'][0]['diagnostics'], ['metadata-read-failed'])

    def test_ancestor_symlink_replacement_rejected(self):
        allowed_dir = self.root / 'allowed-dir'
        allowed_dir.mkdir()
        (allowed_dir / 'receipt.json').write_bytes(self.raw)
        outside = self.root / 'outside-dir'
        outside.mkdir()
        (outside / 'receipt.json').write_bytes(self.raw)
        original_stat = os.stat
        swapped = False

        def replace(path, *args, **kwargs):
            nonlocal swapped
            result = original_stat(path, *args, **kwargs)
            if path == allowed_dir.name and kwargs.get('dir_fd') is not None and not swapped:
                swapped = True
                allowed_dir.rename(self.root / 'old-dir')
                allowed_dir.symlink_to(outside, target_is_directory=True)
            return result

        with patch.object(binding.os, 'stat', side_effect=replace):
            with self.assertRaises(OSError):
                binding._read_metadata(allowed_dir / 'receipt.json')
        self.assertTrue(swapped)

    def test_fifo_successor_returns_without_blocking(self):
        # Child has a deadline so a reader regression cannot hang the test suite.
        script = '''
import os
from pathlib import Path
from unittest.mock import patch
from offmenu.refresh.portfolios import worker23 as m
from offmenu.refresh import core
p=Path(__import__('sys').argv[1]); original_stat=os.stat; swapped=False
def swap(path,*args,**kwargs):
 global swapped
 result=original_stat(path,*args,**kwargs)
 if path==p.name and kwargs.get('dir_fd') is not None and not swapped:
  swapped=True;p.unlink();os.mkfifo(p)
 return result
with patch.object(m.os,'stat',side_effect=swap):
 try:m._read_metadata(p)
 except (OSError,core.RefreshError):print('rejected-without-blocking')
 else:raise AssertionError('FIFO accepted')
assert swapped
'''
        process = subprocess.run([sys.executable, '-B', '-c', script, str(self.target)],
                                 capture_output=True, text=True, timeout=3,
                                 cwd=Path(binding.__file__).parents[3])
        self.assertEqual(process.returncode, 0, process.stderr)
        self.assertEqual(process.stdout.strip(), 'rejected-without-blocking')

    def test_in_place_growth_during_read_fails_and_closes_descriptors(self):
        original_read = os.read
        modified = False

        def grow(fd, size):
            nonlocal modified
            block = original_read(fd, size)
            if not modified:
                modified = True
                with self.target.open('ab') as stream:
                    stream.write(b'x' * (binding.MAX_METADATA_BYTES + 1))
            return block

        with patch.object(binding.os, 'read', side_effect=grow):
            with self.assertRaises(core.RefreshError):
                binding._read_metadata(self.target)
        self.assertTrue(modified)

    def test_acquisition_evidence_uses_same_protected_reader(self):
        acquisition = self.root / 'acquisition.json'
        acquired_raw = core.canonical({'capturedAt': '2026-10-01T00:00:00Z'})
        acquisition.write_bytes(acquired_raw)
        spec = self.spec('a-replaced-acquisition', self.target)
        spec['acquisitionEvidence'] = {'path': str(acquisition),
                                       'sha256': core.sha(acquired_raw),
                                       'selector': '/capturedAt'}
        peer = self.spec('b-independent-peer', self.target)
        canary = self.root / 'outside-acquisition.json'
        canary.write_bytes(acquired_raw)
        original_stat = os.stat
        swapped = False

        def replace(path, *args, **kwargs):
            nonlocal swapped
            result = original_stat(path, *args, **kwargs)
            if path == acquisition.name and kwargs.get('dir_fd') is not None and not swapped:
                swapped = True
                acquisition.unlink()
                acquisition.symlink_to(canary)
            return result

        with patch.object(binding.os, 'stat', side_effect=replace), \
                patch.object(binding, 'registry', return_value={'sources': [spec, peer]}):
            report = binding.run(now='2026-10-18T00:00:00Z')
        self.assertTrue(swapped)
        self.assertEqual([r['status'] for r in report['sources']], ['malformed', 'valid'])

    def test_mid_read_name_replacement_and_failure_cleanup(self):
        actual_open, actual_close, actual_read = os.open, os.close, os.read
        live = set()
        replaced = False

        def opened(*args, **kwargs):
            fd = actual_open(*args, **kwargs)
            live.add(fd)
            return fd

        def closed(fd):
            live.remove(fd)
            actual_close(fd)

        def replace(fd, size):
            nonlocal replaced
            raw = actual_read(fd, size)
            if not replaced:
                replaced = True
                self.target.rename(self.root / 'previous.json')
                self.target.write_bytes(self.raw)
            return raw

        with patch.object(binding.os, 'open', side_effect=opened), \
                patch.object(binding.os, 'close', side_effect=closed), \
                patch.object(binding.os, 'read', side_effect=replace):
            with self.assertRaises(core.RefreshError):
                binding._read_metadata(self.target)
        self.assertFalse(live)


if __name__ == '__main__':
    unittest.main()
