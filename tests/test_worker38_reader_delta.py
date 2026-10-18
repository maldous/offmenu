"""W38-R23-F1: authored temporary metadata paths only; no real receipts."""
import copy
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from offmenu.refresh.portfolios import worker38 as m
from test_worker38_staging_bindings import fixture, NOW


class Worker38ReaderDelta(unittest.TestCase):
    def test_regular_bytes_same_descriptor_no_path_content_reopen(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'metadata.json'
            _, raw = fixture()
            path.write_bytes(raw)
            with patch.object(Path, 'read_bytes', side_effect=AssertionError('unguarded read')):
                self.assertEqual(m._read_metadata(path), raw)

    def test_oversized_file_rejected_before_content_open(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'metadata.json'
            path.write_bytes(b'x' * (m.MAX_METADATA + 1))
            with patch.object(m.os, 'open', side_effect=AssertionError('oversized open')):
                with self.assertRaisesRegex(ValueError, 'metadata-bound-or-type-invalid'):
                    m._read_metadata(path)

    def test_fifo_replacement_after_stat_is_bounded_and_peer_continues(self):
        # Parent owns all temporary paths, and kills/reaps a blocking regression.
        child = r'''
import copy,json,os,sys
from pathlib import Path
from offmenu.refresh.portfolios import worker38 as m
sys.path.insert(0, str(Path.cwd()/'tests'))
from test_worker38_staging_bindings import fixture,NOW
directory=Path(sys.argv[1]); e,raw=fixture()
bad=directory/'bad.json'; good=directory/'good.json'
bad.write_bytes(raw);good.write_bytes(raw)
b=copy.deepcopy(e);b['metadata']['path']=str(bad)
g=copy.deepcopy(e);g['metadata']['path']=str(good)
g['sourceId']='good-peer'
real_open=os.open;swapped=[]
def swap(path,flags,*args,**kwargs):
 if Path(path)==bad and not swapped:
  bad.unlink();os.mkfifo(bad);swapped.append(True)
  assert flags & os.O_NONBLOCK and flags & os.O_NOFOLLOW
 return real_open(path,flags,*args,**kwargs)
m.os.open=swap
result=m.run({'entries':[b,g],'countries':['PT'],'types':['nutrition']},now=NOW)
assert swapped
assert result['results'][0]['errors']==['metadata-unavailable']
assert result['results'][1]['metadataCandidate'] is not None
print(json.dumps({'replacement':'fifo','returned':True,'peerPreserved':True}))
'''
        with tempfile.TemporaryDirectory() as directory:
            process = subprocess.Popen([sys.executable, '-B', '-c', child, directory],
                                       stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                       text=True)
            try:
                stdout, stderr = process.communicate(timeout=3)
            except subprocess.TimeoutExpired:
                process.kill()
                process.communicate(timeout=3)
                self.fail('reader blocked; child killed and reaped')
            self.assertEqual(process.returncode, 0, stderr)
            self.assertTrue(json.loads(stdout)['peerPreserved'])

    def test_symlink_replacement_after_stat_is_refused_without_read(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / 'metadata.json'
            peer = target.parent / 'peer.json'
            _, raw = fixture()
            target.write_bytes(raw)
            peer.write_bytes(raw)
            real_open = os.open
            def swap(path, flags, *args, **kwargs):
                target.unlink()
                target.symlink_to(peer)
                return real_open(path, flags, *args, **kwargs)
            with patch.object(m.os, 'open', side_effect=swap), patch.object(
                    m.os, 'read', side_effect=AssertionError('symlink read')):
                with self.assertRaises(OSError):
                    m._read_metadata(target)

    def test_growth_after_descriptor_verification_never_exceeds_read_ceiling(self):
        with tempfile.TemporaryDirectory() as directory:
            entry, raw = fixture()
            bad = Path(directory) / 'bad.json'
            peer = bad.parent / 'peer.json'
            bad.write_bytes(raw)
            peer.write_bytes(raw)
            bad_inode = bad.stat().st_ino
            b, g = copy.deepcopy(entry), copy.deepcopy(entry)
            b['metadata']['path'], g['metadata']['path'] = str(bad), str(peer)
            g['sourceId'] = 'good-peer'
            real_read = os.read
            consumed = []
            def grow(fd, limit):
                if os.fstat(fd).st_ino == bad_inode:
                    if not consumed:
                        with bad.open('ab') as stream:
                            stream.write(b'x' * (m.MAX_METADATA + 17))
                    chunk = real_read(fd, limit)
                    consumed.append(len(chunk))
                    return chunk
                return real_read(fd, limit)
            with patch.object(m.os, 'read', side_effect=grow):
                result = m.run({'entries': [b, g], 'countries': ['PT'],
                                'types': ['nutrition']}, now=NOW)
            self.assertLessEqual(sum(consumed), m.MAX_METADATA + 1)
            self.assertEqual(result['results'][0]['errors'], ['metadata-unavailable'])
            self.assertIsNotNone(result['results'][1]['metadataCandidate'])

    def test_path_replaced_after_open_does_not_reopen_fifo(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'metadata.json'
            _, raw = fixture()
            path.write_bytes(raw)
            real_read = os.read
            swapped = []
            def replace_after_read(fd, limit):
                chunk = real_read(fd, limit)
                if not swapped:
                    path.unlink()
                    os.mkfifo(path)
                    swapped.append(True)
                return chunk
            with patch.object(m.os, 'read', side_effect=replace_after_read):
                with self.assertRaisesRegex(ValueError, 'metadata-changed-during-read'):
                    m._read_metadata(path)


if __name__ == '__main__':
    unittest.main()
