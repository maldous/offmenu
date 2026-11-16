import importlib.util
from pathlib import Path
import stat,os,json
import types
import unittest
from unittest.mock import patch,mock_open,Mock
HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('inc',HERE/'offmenu_input_readonly_acl_mount.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)

class IncrementalTests(unittest.TestCase):
 def old_mounts(self):
  return [{'source':m.DATA+n,'destination':m.DEST+n,'kind':'directory' if n in m.EXISTING_DIRECTORIES else 'file','identity':[1,i+10,stat.S_IFDIR if n in m.EXISTING_DIRECTORIES else stat.S_IFREG]} for i,n in enumerate(m.EXISTING_DIRECTORIES+m.EXISTING_FILES)]
 def old_bytes(self,items):return m.ORIGINAL_LAUNCHER_TEMPLATE.replace('__CORPUS_MOUNTS__',repr(items)).encode()
 def test_old_pins_preserved_exactly(self):
  items=self.old_mounts();old=self.old_bytes(items)
  with patch.object(m,'ORIGINAL_SHA',m.digest(old)):self.assertEqual(m.parse_existing_mounts(old),items)
 def test_wrong_hash_refused(self):
  with self.assertRaises(m.Stop):m.parse_existing_mounts(self.old_bytes(self.old_mounts()))
 def test_old_path_changed_even_matching_hash_refused(self):
  items=self.old_mounts();items[0]['source']='/different';old=self.old_bytes(items)
  with patch.object(m,'ORIGINAL_SHA',m.digest(old)):
   with self.assertRaises(m.Stop):m.parse_existing_mounts(old)
 def test_extra_old_source_code_refused(self):
  old=self.old_bytes(self.old_mounts())+b'\nprint("extra")\n'
  with patch.object(m,'ORIGINAL_SHA',m.digest(old)):
   with self.assertRaises(m.Stop):m.parse_existing_mounts(old)
 def test_optional_absent_skipped(self):
  with patch.object(m.os,'lstat',side_effect=FileNotFoundError):present,absent=m.select_optional_files()
  self.assertFalse(present);self.assertEqual(absent,m.OPTIONAL_FILES)
 def test_optional_permission_not_absent(self):
  with patch.object(m.os,'lstat',side_effect=PermissionError):
   with self.assertRaises(PermissionError):m.select_optional_files()
 def test_generated_account_helper_compiles(self):
  with patch.object(m,'run_as_account',side_effect=lambda code:compile(code,'helper','exec')):m.verify_account_paths([])

class RuntimeTests(unittest.TestCase):
 def setUp(self):
  self.ns={'__name__':'test'};exec(m.make_launcher([]),self.ns)
  self.source=m.DATA+m.OPTIONAL_FILES[0];self.dest=m.DEST+m.OPTIONAL_FILES[0]
  self.item={'source':self.source,'destination':self.dest,'kind':'file','identity':[1,100,stat.S_IFREG],'optional':True}
  self.live={};self.serial=10;self.missing=False;self.mode=stat.S_IFREG;self.ino=100
  def op(path,flags,dir_fd=None):
   if path=='/':full='/'
   else:full=self.live[dir_fd].rstrip('/')+'/'+path
   if full==self.source and self.missing:raise FileNotFoundError(full)
   self.serial+=1;self.live[self.serial]=full;return self.serial
  def fs(fd):
   full=self.live[fd];return types.SimpleNamespace(st_dev=1,st_ino=self.ino if full==self.source else 3,st_mode=self.mode if full==self.source else stat.S_IFDIR)
  fake=types.SimpleNamespace(open=op,close=lambda fd:self.live.pop(fd),fstat=fs,access=lambda p,mode,effective_ids=True:mode!=os.W_OK,
    O_PATH=os.O_PATH,O_DIRECTORY=os.O_DIRECTORY,O_CLOEXEC=os.O_CLOEXEC,O_NOFOLLOW=os.O_NOFOLLOW,R_OK=os.R_OK,W_OK=os.W_OK,X_OK=os.X_OK)
  self.ns['os']=fake;self.ns['CORPUS_MOUNTS']=[self.item]
 def call(self):
  with patch('builtins.open',mock_open(read_data='')):return self.ns['open_corpus_mounts']()
 def test_existing_optional_kept(self):
  active=self.call();self.assertEqual(len(active),1);self.assertEqual(active[0][1],self.item)
  for fd,_ in active:self.ns['os'].close(fd)
  self.assertFalse(self.live)
 def test_missing_optional_omitted_fd_closed(self):
  self.missing=True;self.assertEqual(self.call(),[]);self.assertFalse(self.live)
 def test_replaced_optional_omitted_fd_closed(self):
  self.ino=101;self.assertEqual(self.call(),[]);self.assertFalse(self.live)
 def test_symlink_optional_omitted(self):
  self.mode=stat.S_IFLNK;self.assertEqual(self.call(),[]);self.assertFalse(self.live)
 def test_directory_replacement_omitted(self):
  self.mode=stat.S_IFDIR;self.assertEqual(self.call(),[]);self.assertFalse(self.live)
 def test_required_missing_not_omitted(self):
  self.item.pop('optional');self.missing=True
  with self.assertRaises(FileNotFoundError):self.call()
  self.assertFalse(self.live)
 def test_required_changed_not_omitted(self):
  self.item.pop('optional');self.ino=101
  with self.assertRaises(SystemExit):self.call()
  self.assertFalse(self.live)
 def test_arbitrary_optional_path_refused(self):
  self.item['source']='/unapproved'
  with self.assertRaises(SystemExit):self.call()
  self.assertFalse(self.live)
 def test_optional_wrong_flag_refused(self):
  self.item['optional']='yes'
  with self.assertRaises(SystemExit):self.call()
 def test_guard_blocks_post_bind_replacement(self):
  fake_os=types.SimpleNamespace(stat=lambda *a,**k:types.SimpleNamespace(st_dev=1,st_ino=101,st_mode=stat.S_IFREG),statvfs=lambda p:types.SimpleNamespace(f_flag=os.ST_RDONLY),ST_RDONLY=os.ST_RDONLY,execv=Mock())
  fake_sys=types.SimpleNamespace(argv=['guard',json.dumps([self.item]),'never execute'])
  with patch.dict('sys.modules',{'os':fake_os,'sys':fake_sys}):
   with self.assertRaises(SystemExit):exec(self.ns['BIND_IDENTITY_GUARD'],{})
  fake_os.execv.assert_not_called()
 def test_guard_allows_exact_readonly_pin(self):
  fake_os=types.SimpleNamespace(stat=lambda *a,**k:types.SimpleNamespace(st_dev=1,st_ino=100,st_mode=stat.S_IFREG),statvfs=lambda p:types.SimpleNamespace(f_flag=os.ST_RDONLY),ST_RDONLY=os.ST_RDONLY,execv=Mock())
  fake_sys=types.SimpleNamespace(argv=['guard',json.dumps([self.item]),'approved command'])
  with patch.dict('sys.modules',{'os':fake_os,'sys':fake_sys}):exec(self.ns['BIND_IDENTITY_GUARD'],{})
  fake_os.execv.assert_called_once_with('/bin/bash',['/bin/bash','--noprofile','--norc','-c','approved command'])
if __name__=='__main__':unittest.main()
