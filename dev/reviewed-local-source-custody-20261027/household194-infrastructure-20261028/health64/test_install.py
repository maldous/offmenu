from contextlib import redirect_stdout
import io
import os
from pathlib import Path
import tempfile
import unittest
HERE=Path(__file__).parent
SOURCE=(HERE/'install_health64.py').read_text()
OLD=(HERE/'platform_check_preimage.py').read_bytes()
NEW=(HERE/'platform_check.py').read_bytes()
class Tests(unittest.TestCase):
 def setUp(self):
  self.t=tempfile.TemporaryDirectory();self.p=Path(self.t.name);(self.p/'platform_check.py').write_bytes(OLD)
 def tearDown(self):self.t.cleanup()
 def run_install(self):
  s=SOURCE.replace("Path('/offmenu/scripts/windmill')",'Path('+repr(str(self.p))+')')
  out=io.StringIO()
  with redirect_stdout(out):exec(compile(s,'health-installer','exec'),{})
  return out.getvalue()
 def test_create_only_idempotent_and_old_preserved(self):
  self.assertIn('created_new_version',self.run_install());self.assertIn('already_present_exact',self.run_install())
  self.assertEqual((self.p/'platform_check.py').read_bytes(),OLD)
  self.assertEqual((self.p/'platform_check_capacity64.py').read_bytes(),NEW)
  self.assertEqual(list(self.p.glob('.health64-*')),[])
 def test_preimage_mismatch_refused(self):
  (self.p/'platform_check.py').write_text('changed')
  with self.assertRaisesRegex(RuntimeError,'OldPreimageMismatch'):self.run_install()
  self.assertFalse((self.p/'platform_check_capacity64.py').exists())
 def test_target_collision_refused(self):
  p=self.p/'platform_check_capacity64.py';p.write_text('existing')
  with self.assertRaisesRegex(RuntimeError,'ExistingVersionMismatch'):self.run_install()
  self.assertEqual(p.read_text(),'existing')
 def test_fifo_and_symlink_refused(self):
  p=self.p/'platform_check.py';p.unlink();os.mkfifo(p)
  with self.assertRaisesRegex(RuntimeError,'SourceTypeRefused'):self.run_install()
  p.unlink();p.symlink_to(HERE/'platform_check_preimage.py')
  with self.assertRaises(OSError):self.run_install()
if __name__=='__main__':unittest.main()
