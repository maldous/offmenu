"""Offline launcher authentication and installation tests; no source requests."""
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import importlib.util,io,json,os,subprocess,tempfile,unittest
from contextlib import redirect_stdout
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('owner_launcher',ROOT/'scripts/run-global-on-foo.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
class LauncherTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.home=Path(self.tmp.name);self.p=patch.object(m.pwd,'getpwuid',return_value=SimpleNamespace(pw_dir=str(self.home)));self.p.start()
 def tearDown(self):self.p.stop();self.tmp.cleanup()
 def test_clean_env_preserves_token_only_as_environment(self):
  with patch.dict(os.environ,{'GITHUB_TOKEN':'synthetic-existing','GH_TOKEN':'synthetic-precedence','GH_CONFIG_DIR':str(self.home/'custom gh'),'GIT_DIR':'hostile','GIT_INDEX_FILE':'hostile','GIT_CONFIG_COUNT':'2','BASH_ENV':'hostile','PYTHONPATH':'hostile','GH_DEBUG':'api'},clear=True):
   env=m.clean_environment()
   self.assertEqual(env['GITHUB_TOKEN'],'synthetic-existing');self.assertEqual(env['GH_TOKEN'],'synthetic-precedence');self.assertEqual(env['GH_CONFIG_DIR'],str(self.home/'custom gh'))
   for key in ('GIT_DIR','GIT_INDEX_FILE','GIT_CONFIG_COUNT','BASH_ENV','PYTHONPATH','GH_DEBUG'):self.assertNotIn(key,env)
 def test_config_resolution_xdg_and_default(self):
  with patch.dict(os.environ,{'HOME':str(self.home),'XDG_CONFIG_HOME':str(self.home/'xdg')},clear=True):self.assertEqual(m.clean_environment()['GH_CONFIG_DIR'],str(self.home/'xdg/gh'))
  with patch.dict(os.environ,{'HOME':str(self.home)},clear=True):self.assertEqual(m.clean_environment()['GH_CONFIG_DIR'],str(self.home/'.config/gh'))
 def test_git_never_places_credentials_in_argv(self):
  env={'GITHUB_TOKEN':'synthetic-existing'}
  with patch.object(m.subprocess,'run',return_value=SimpleNamespace(stdout=b'ok\n')) as call:
   self.assertEqual(m.git(env,'status'),'ok');self.assertNotIn('synthetic-existing',repr(call.call_args.args));self.assertEqual(call.call_args.kwargs['env'],env)
 def test_real_gh_credential_helper_existing_token_only(self):
  # gh credential get is an offline lookup; capture and compare without printing.
  env=m.clean_environment();env['GITHUB_TOKEN']='synthetic-launcher-existing';env.pop('GH_TOKEN',None);env['GH_CONFIG_DIR']=str(self.home/'empty')
  result=subprocess.run(['/usr/bin/gh','auth','git-credential','get'],input=b'protocol=https\nhost=github.com\n\n',stdout=subprocess.PIPE,stderr=subprocess.PIPE,env=env,timeout=5,check=True)
  self.assertIn(b'password=synthetic-launcher-existing',result.stdout)
 def test_install_is_pinned_and_repeat_non_destructive(self):
  pin={'commit':'a'*40,'tree':'b'*40};root=self.home/'offmenu-global-collection';source=root/'source';root.mkdir(mode=0o700);source.mkdir();(source/'.git').mkdir()
  with patch.object(m,'verify_source') as verify,redirect_stdout(io.StringIO()):
   m.install(**pin);before={p.name:p.read_bytes() for p in root.iterdir() if p.is_file()};m.install(**pin)
   self.assertEqual(before,{p.name:p.read_bytes() for p in root.iterdir() if p.is_file()});self.assertEqual(verify.call_count,2)
  self.assertEqual(json.loads((root/'source-pin.json').read_text()),pin);self.assertEqual((root/'run').stat().st_mode&0o777,0o700)
  with patch.object(m,'verify_source'),self.assertRaises(ValueError):m.install('c'*40,'b'*40)
 def test_symlink_install_rejected_without_overwrite(self):
  root=self.home/'offmenu-global-collection';root.symlink_to(self.home/'absent')
  with self.assertRaises(ValueError):m.install('a'*40,'b'*40)
  self.assertTrue(root.is_symlink())
 def test_run_from_arbitrary_cwd_inherited_auth_and_publish_only(self):
  root=self.home/'offmenu-global-collection';source=root/'source';root.mkdir(mode=0o700);source.mkdir();(root/'source-pin.json').write_text(json.dumps({'commit':'a'*40,'tree':'b'*40}))
  with patch.dict(os.environ,{'GITHUB_TOKEN':'synthetic-existing'}),patch.object(m,'__file__',str(source/'scripts/run-global-on-foo.py')),patch.object(m,'verify_source'),patch.object(m.os,'chdir') as cd,patch.object(m.os,'execvpe') as execute:
   m.run(True);args=execute.call_args.args;self.assertEqual(args[2]['GITHUB_TOKEN'],'synthetic-existing');self.assertNotIn('synthetic-existing',repr(args[:2]));self.assertEqual(args[1][-1],'--publish-only');cd.assert_called_once_with(source)
 def test_bad_launcher_args_stop(self):
  with patch.object(m.sys,'argv',['launcher','--url','https://invalid']),self.assertRaises(ValueError):m.main()
 def test_insecure_root_and_source_or_pin_symlinks_stop(self):
  root=self.home/'offmenu-global-collection';root.mkdir(mode=0o755)
  with self.assertRaises(ValueError):m.install('a'*40,'b'*40)
  root.chmod(0o700);source=root/'source';source.symlink_to(self.home/'absent')
  with self.assertRaises(ValueError):m.install('a'*40,'b'*40)
  source.unlink();source.mkdir();(root/'source-pin.json').symlink_to(self.home/'absent')
  with self.assertRaises(OSError):m.run()
if __name__=='__main__':unittest.main()
