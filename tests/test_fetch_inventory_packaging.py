"""Offline, exact-byte tests for lossless source metadata packaging."""
from contextlib import ExitStack
import gzip
import hashlib
import io
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from offmenu.refresh import fetch_reconciliation_runtime as runtime
from offmenu.refresh import fetch_metadata_reconciliation as metadata
from offmenu.refresh.core import RefreshError

class PackagingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.packed=(runtime.ROOT/runtime.CLOSURE_PACKED_PATH).read_bytes()

    def load(self, packed, *, trust_packed=False, extent=None, digest=None):
        with tempfile.TemporaryDirectory() as directory, ExitStack() as stack:
            root=Path(directory);target=root/runtime.CLOSURE_PACKED_PATH
            target.parent.mkdir(parents=True);target.write_bytes(packed)
            if trust_packed:
                stack.enter_context(patch.object(runtime,'CLOSURE_PACKED_BYTES',len(packed)))
                stack.enter_context(patch.object(runtime,'CLOSURE_PACKED_SHA256',hashlib.sha256(packed).hexdigest()))
            if extent is not None or digest is not None:
                old_hash,old_size=metadata.INVENTORY_PINS['closure_raw']
                stack.enter_context(patch.dict(metadata.INVENTORY_PINS,closure_raw=(digest or old_hash,old_size if extent is None else extent)))
            return runtime.closure_bytes(root)

    def test_exact_reviewed_bytes_and_repeat_compression(self):
        raw=runtime.closure_bytes()
        digest,extent=metadata.INVENTORY_PINS['closure_raw']
        self.assertEqual(len(raw),extent);self.assertEqual(hashlib.sha256(raw).hexdigest(),digest)
        packed=bytearray(gzip.compress(raw,compresslevel=9,mtime=0));packed[9]=255
        self.assertEqual(bytes(packed),self.packed)
        self.assertFalse((runtime.ROOT/runtime.INPUT_PATHS['closure_raw']).exists())

    def test_reader_is_bounded(self):
        stream=io.BytesIO(self.packed)
        with patch.object(Path,'open') as opened:
            entered=opened.return_value.__enter__.return_value
            entered.read.side_effect=stream.read
            runtime.closure_bytes()
            entered.read.assert_called_once_with(runtime.CLOSURE_PACKED_BYTES+1)

    def test_tamper(self):
        with self.assertRaises(RefreshError):self.load(self.packed[:-1]+bytes([self.packed[-1]^1]))
    def test_oversized_packed(self):
        with self.assertRaises(RefreshError):self.load(self.packed+b'x')
    def test_truncated_stream(self):
        with self.assertRaises(RefreshError):self.load(self.packed[:-1],trust_packed=True)
    def test_trailing_bytes(self):
        with self.assertRaises(RefreshError):self.load(self.packed+b'x',trust_packed=True)
    def test_concatenated_members(self):
        with self.assertRaises(RefreshError):self.load(self.packed+gzip.compress(b'x',mtime=0),trust_packed=True)
    def test_expansion_cap(self):
        with self.assertRaises(RefreshError):self.load(self.packed,extent=31783524)
    def test_short_output(self):
        with self.assertRaises(RefreshError):self.load(self.packed,extent=31783526)
    def test_decoded_hash(self):
        with self.assertRaises(RefreshError):self.load(self.packed,digest='0'*64)
    def test_invalid_gzip(self):
        with self.assertRaises(RefreshError):self.load(b'not gzip',trust_packed=True)
    def test_missing_input(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(RefreshError):runtime.closure_bytes(Path(directory))

if __name__=='__main__':unittest.main()
