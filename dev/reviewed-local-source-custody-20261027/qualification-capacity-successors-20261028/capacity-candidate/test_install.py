"""Offline create-only installer validation in disposable local directories."""
from contextlib import redirect_stdout
import io
import os
import fcntl
import hashlib
from pathlib import Path
import tempfile
import unittest

HERE=Path(__file__).parent
INSTALL=(HERE/'install_capacity.py').read_text()
OLD=(HERE/'job_runner_preimage.py').read_bytes()
NEW=(HERE/'job_runner.py').read_bytes()

class Tests(unittest.TestCase):
    def setUp(self):
        self.t=tempfile.TemporaryDirectory();self.root=Path(self.t.name)
        self.code=self.root/'scripts/windmill';self.code.mkdir(parents=True)
        self.locks=self.root/'data/.offmenu-platform/locks';self.locks.mkdir(parents=True)
        (self.code/'job_runner.py').write_bytes(OLD)
    def tearDown(self):self.t.cleanup()
    def install(self):
        source=INSTALL.replace("Path('/offmenu/scripts/windmill')",'Path('+repr(str(self.code))+')').replace("Path('/offmenu/data/.offmenu-platform/locks')",'Path('+repr(str(self.locks))+')')
        out=io.StringIO()
        with redirect_stdout(out):exec(compile(source,'installer','exec'),{})
        return out.getvalue()
    def test_create_then_exact_idempotent(self):
        self.assertIn('created_new_version',self.install())
        self.assertEqual((self.code/'job_runner_capacity_v3.py').read_bytes(),NEW)
        self.assertIn('already_present_exact',self.install())
        self.assertEqual((self.code/'job_runner.py').read_bytes(),OLD)
        self.assertEqual(list(self.code.glob('.capacity-v3-*')),[])
    def test_inflight_refused(self):
        (self.locks/'execution-slot-63.inflight.json').write_text('{}')
        with self.assertRaisesRegex(RuntimeError,'InflightMarkerPresent'):self.install()
        self.assertFalse((self.code/'job_runner_capacity_v3.py').exists())
    def test_preimage_change_refused(self):
        (self.code/'job_runner.py').write_text('# changed')
        with self.assertRaisesRegex(RuntimeError,'LegacyPreimageMismatch'):self.install()
        self.assertFalse((self.code/'job_runner_capacity_v3.py').exists())
    def test_collision_never_overwritten(self):
        p=self.code/'job_runner_capacity_v3.py';p.write_text('# other')
        with self.assertRaisesRegex(RuntimeError,'ExistingVersionMismatch'):self.install()
        self.assertEqual(p.read_text(),'# other')
    def test_held_access_lock_refused(self):
        fd=os.open(self.locks/'execution-access.lock',os.O_RDWR|os.O_CREAT,0o600)
        try:
            fcntl.flock(fd,fcntl.LOCK_EX|fcntl.LOCK_NB)
            with self.assertRaises(BlockingIOError):self.install()
            self.assertFalse((self.code/'job_runner_capacity_v3.py').exists())
        finally:os.close(fd)
    def test_fifo_preimage_refused_without_blocking(self):
        p=self.code/'job_runner.py';p.unlink();os.mkfifo(p)
        with self.assertRaisesRegex(RuntimeError,'SourceTypeRefused'):self.install()

    def test_symlink_refused(self):
        p=self.code/'job_runner_capacity_v3.py';p.symlink_to(self.code/'job_runner.py')
        with self.assertRaises(OSError):self.install()
        self.assertEqual((self.code/'job_runner.py').read_bytes(),OLD)

if __name__=='__main__':unittest.main()
