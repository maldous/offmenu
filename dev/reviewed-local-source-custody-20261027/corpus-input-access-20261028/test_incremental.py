import importlib.util
import json
import os
from pathlib import Path
import stat
import tempfile
import unittest
from unittest.mock import patch, Mock

HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('combined',HERE/'offmenu_input_readonly_acl_mount.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
a=m.ACLM

class PlannerTests(unittest.TestCase):
 def plan(self,t,d=False):return a['readonly_plan'](t,owner=1000,group=1000,is_dir=d)
 def test_700_dir(self):
  out,ch=self.plan('user::rwx\ngroup::---\nother::---\n',True)
  self.assertTrue(ch);access,default=a['parse'](out)
  self.assertEqual(a['effective_for_identity'](access,owner=1000,group=1000),5);self.assertFalse(default)
 def test_600_file(self):
  out,ch=self.plan('user::rw-\ngroup::---\nother::---\n');self.assertTrue(ch)
  self.assertEqual(a['parse'](out)[0]['user','985'],4)
 def test_masked_other_grants_preserved(self):
  before='user::rw-\nuser:1234:rwx\ngroup::rwx\ngroup:2222:rwx\nmask::--x\nother::---\n'
  out,ch=self.plan(before);old,_=a['parse'](before);new,_=a['parse'](out)
  self.assertTrue(ch);a['verify_preserved'](old,new)
  self.assertEqual(a['effective'](new,('user','1234')),1)
  self.assertEqual(a['effective'](new,('group','')),1)
  self.assertEqual(a['effective'](new,('group','2222')),1)
 def test_defaults_identical(self):
  before='user::rwx\ngroup::---\nother::---\ndefault:user::rwx\ndefault:user:1234:rwx\ndefault:group::rwx\ndefault:mask::--x\ndefault:other::---\n'
  out,_=self.plan(before,True);self.assertEqual(a['parse'](out)[1],a['parse'](before)[1])
 def test_already_readable_unchanged(self):
  before='user::rw-\ngroup::r--\nother::r--\n';out,ch=self.plan(before)
  self.assertFalse(ch);self.assertEqual(out,before)
 def test_write_collision_refused(self):
  with self.assertRaises(a['ACLPlanError']):self.plan('user::rw-\ngroup::---\nother::rw-\n')
 def test_worker_owner_refused(self):
  with self.assertRaises(a['ACLPlanError']):a['readonly_plan']('user::r--\ngroup::---\nother::---\n',owner=985,group=977,is_dir=False)
 def test_named_worker_deny_changed_only_worker(self):
  before='user::rw-\nuser:985:---\nuser:1234:rwx\ngroup::rwx\nmask::r-x\nother::---\n';out,ch=self.plan(before)
  old,_=a['parse'](before);new,_=a['parse'](out);a['verify_preserved'](old,new,exceptions=(('user','985'),));self.assertTrue(ch)
 def test_group_match_does_not_fallthrough(self):
  before='user::rw-\ngroup::---\ngroup:977:---\nmask::---\nother::r--\n';_,ch=self.plan(before);self.assertTrue(ch)

class ScopeTests(unittest.TestCase):
 def test_exact_approved_paths(self):
  d=json.loads((HERE/'approved-input-scope.json').read_text())
  self.assertEqual([m.DATA+n for n in m.DIRECTORIES],d['input_access_request']['directories'])
  self.assertEqual([m.DATA+n for n in m.OPTIONAL_FILES],d['input_access_request']['optional_existing_files'])
 def test_access_setter_never_writes_default(self):
  acl=Mock();m.set_access_only(acl,10,'user::rwx\ngroup::---\nother::---\ndefault:user::rwx\ndefault:group::---\ndefault:other::---\n')
  acl._set.assert_called_once_with(10,'user::rwx\ngroup::---\nother::---\n');acl.put.assert_not_called()
 def test_mount_template_no_host_fd_inheritance(self):
  self.assertNotIn('pass_fds',m.LAUNCHER_TEMPLATE);self.assertNotIn('/proc/self/fd/',m.LAUNCHER_TEMPLATE)
  self.assertIn("'--unshare-all'",m.LAUNCHER_TEMPLATE)
  self.assertIn("'--ro-bind', item['source'], item['destination']",m.LAUNCHER_TEMPLATE)

class FilesystemTests(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory(dir=HERE);self.root=Path(self.temp.name)
  self.corpus=self.root/'corpus';self.corpus.mkdir()
  self.pkg=self.corpus/'package';self.pkg.mkdir(mode=0o700)
  self.file=self.pkg/'data';self.file.write_text('synthetic fixture');self.file.chmod(0o600)
  self.patches=[patch.object(m,'DATA',str(self.corpus)+'/'),patch.object(m,'DIRECTORIES',('package',)),patch.object(m,'FILES',())]
  for p in self.patches:p.start()
  self.acl=m.ACLIO_MOD['ACLIO']()
 def tearDown(self):
  for p in reversed(self.patches):p.stop()
  self.temp.cleanup()
 def test_root_fd_is_readable(self):
  fd,s=m.open_pinned('/')
  try:self.assertTrue(stat.S_ISDIR(s.st_mode));self.assertTrue(os.readlink('/proc/self/fd/'+str(fd))=='/')
  finally:os.close(fd)
 def test_snapshot_no_mutation(self):
  plan,shared=m.snapshot_acl_plan(self.acl);self.assertEqual(len(plan),2);self.assertEqual(shared,0)
  self.assertEqual(stat.S_IMODE(self.pkg.stat().st_mode),0o700);self.assertEqual(stat.S_IMODE(self.file.stat().st_mode),0o600)
 def test_outside_hardlink_missing_read_refused(self):
  os.link(self.file,self.root/'outside')
  with self.assertRaises(m.Stop):m.snapshot_acl_plan(self.acl)
 def test_outside_readable_hardlink_untouched(self):
  self.file.chmod(0o644);os.link(self.file,self.root/'outside');plan,shared=m.snapshot_acl_plan(self.acl)
  self.assertEqual(shared,1);self.assertFalse(next(x for x in plan if not x['dir'])['change'])
 def test_internal_hardlink_one_inode(self):
  os.link(self.file,self.pkg/'alias');plan,shared=m.snapshot_acl_plan(self.acl)
  self.assertEqual(len(plan),2);self.assertEqual(shared,0);self.assertEqual(len(next(x for x in plan if not x['dir'])['aliases']),2)
 def test_symlink_refused(self):
  (self.pkg/'link').symlink_to(self.file)
  with self.assertRaises(m.Stop):m.snapshot_acl_plan(self.acl)
 def test_special_refused(self):
  os.mkfifo(self.pkg/'fifo')
  with self.assertRaises(m.Stop):m.snapshot_acl_plan(self.acl)
 def syscall_plan(self):
  # Cloud maps only UID1000. Exercise real libacl I/O/rollback with a mapped
  # named entry; target985 semantics are separately tested in PlannerTests.
  plan,_=m.snapshot_acl_plan(self.acl)
  for item in plan:item['after']=item['after'].replace('user:985:', 'user:1000:')
  return plan
 def journal(self):return os.open(self.root/'journal',os.O_RDWR|os.O_CREAT|os.O_EXCL,0o600)
 def test_apply_and_rollback_real_acl(self):
  plan=self.syscall_plan();fd=self.journal();touched=[]
  try:
   m.apply_acl_plan(self.acl,plan,fd,touched);self.assertEqual(len(touched),2)
   self.assertFalse(m.rollback_acls(self.acl,touched,fd))
   self.assertEqual(stat.S_IMODE(self.pkg.stat().st_mode),0o700);self.assertEqual(stat.S_IMODE(self.file.stat().st_mode),0o600)
  finally:os.close(fd)
 def test_fsync_error_after_acl_has_rollback(self):
  plan=self.syscall_plan();fd=self.journal();touched=[];orig=m.os.fsync;calls=[]
  def fail_second(f):
   calls.append(f)
   if len(calls)==2:raise OSError('synthetic post-acl fsync failure')
   return orig(f)
  try:
   with patch.object(m.os,'fsync',side_effect=fail_second):
    with self.assertRaises(OSError):m.apply_acl_plan(self.acl,plan,fd,touched)
   self.assertEqual(len(touched),1);self.assertFalse(m.rollback_acls(self.acl,touched,fd))
   self.assertEqual(stat.S_IMODE(self.pkg.stat().st_mode),0o700)
  finally:os.close(fd)
 def test_link_topology_change_preapply_refused(self):
  plan=self.syscall_plan();os.link(self.file,self.root/'outside');fd=self.journal();touched=[]
  try:
   with self.assertRaises(m.Stop):m.apply_acl_plan(self.acl,plan,fd,touched)
   self.assertFalse(m.rollback_acls(self.acl,touched,fd))
  finally:os.close(fd)
 def test_defaults_real_untouched(self):
  fd,_=m.open_pinned(str(self.pkg));self.acl._set(fd,'user::rwx\ngroup::---\nother::---\n',default=True);os.close(fd)
  plan=self.syscall_plan();fd=self.journal();touched=[]
  try:m.apply_acl_plan(self.acl,plan,fd,touched);self.assertFalse(m.rollback_acls(self.acl,touched,fd))
  finally:os.close(fd)
 def test_rollback_refuses_changed_inode(self):
  plan=self.syscall_plan();fd=self.journal();touched=[]
  try:
   m.apply_acl_plan(self.acl,plan,fd,touched);self.file.rename(self.pkg/'original');self.file.write_text('replacement')
   failures=m.rollback_acls(self.acl,touched,fd);self.assertTrue(failures)
  finally:os.close(fd)

if __name__=='__main__':unittest.main()
