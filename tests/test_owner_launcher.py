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
 def installed_layout(self,commit='a'*40):
  root=self.home/'offmenu-global-collection';root.mkdir(mode=0o700,exist_ok=True);(root/'sources').mkdir(mode=0o700,exist_ok=True);(root/'pins').mkdir(mode=0o700,exist_ok=True);source=root/'sources'/commit;source.mkdir(exist_ok=True);(source/'.git').mkdir(exist_ok=True);return root,source
 def legacy(self):
  root=self.home/'offmenu-global-collection';root.mkdir(mode=0o700,exist_ok=True);legacy=root/'source';legacy.mkdir();(legacy/'prior-code').write_bytes(b'preserved');(root/'source-pin.json').write_text(json.dumps(m.PREDECESSOR));(root/'run').write_bytes(m.wrapper_bytes(legacy));return root,legacy
 def versioned_predecessor(self):
  root,source=self.installed_layout(m.VERSIONED_PREDECESSOR['commit']);(source/'prior-code').write_bytes(b'preserved');(root/'pins'/(m.VERSIONED_PREDECESSOR['commit']+'.json')).write_text(json.dumps(m.VERSIONED_PREDECESSOR));(root/'run').write_bytes(m.wrapper_bytes(source));return root,source
 def test_exact_versioned_upgrade_preserves_prior_code_and_pin(self):
  root,prior=self.versioned_predecessor();pin=root/'pins'/(m.VERSIONED_PREDECESSOR['commit']+'.json');before=pin.read_bytes();_,source=self.installed_layout()
  with patch.object(m,'verify_source') as verify,redirect_stdout(io.StringIO()):m.install('a'*40,'b'*40)
  self.assertEqual((prior/'prior-code').read_bytes(),b'preserved');self.assertEqual(pin.read_bytes(),before);self.assertEqual((root/'run').read_bytes(),m.wrapper_bytes(source));self.assertEqual(verify.call_args_list[0].args[1],m.VERSIONED_PREDECESSOR)
 def test_changed_versioned_pin_never_fetches(self):
  root,prior=self.versioned_predecessor();(root/'pins'/(m.VERSIONED_PREDECESSOR['commit']+'.json')).write_text(json.dumps({'commit':'c'*40,'tree':'d'*40}))
  with patch.object(m,'git',side_effect=AssertionError('fetch')),self.assertRaises(ValueError):m.install('a'*40,'b'*40)
 def test_versioned_failed_switch_preserves_wrapper(self):
  root,prior=self.versioned_predecessor();before=(root/'run').read_bytes();self.installed_layout()
  with patch.object(m,'verify_source'),patch.object(m.os,'replace',side_effect=OSError('synthetic')),self.assertRaises(OSError):m.install('a'*40,'b'*40)
  self.assertEqual((root/'run').read_bytes(),before);self.assertEqual((prior/'prior-code').read_bytes(),b'preserved')
 def test_install_is_pinned_and_repeat_non_destructive(self):
  pin={'commit':'a'*40,'tree':'b'*40};root,source=self.installed_layout()
  with patch.object(m,'verify_source') as verify,redirect_stdout(io.StringIO()):
   m.install(**pin);before=(root/'run').read_bytes();m.install(**pin);self.assertEqual(before,(root/'run').read_bytes());self.assertEqual(verify.call_count,2)
  self.assertEqual(json.loads((root/'pins'/(pin['commit']+'.json')).read_text()),pin);self.assertEqual((root/'run').stat().st_mode&0o777,0o700)
  with patch.object(m,'verify_source'),self.assertRaises(ValueError):m.install('c'*40,'b'*40)
 def test_exact_legacy_upgrade_preserves_old_code_and_pin(self):
  root,legacy=self.legacy();before=(root/'source-pin.json').read_bytes();_,source=self.installed_layout()
  with patch.object(m,'verify_source') as verify,redirect_stdout(io.StringIO()):m.install('a'*40,'b'*40)
  self.assertEqual((legacy/'prior-code').read_bytes(),b'preserved');self.assertEqual((root/'source-pin.json').read_bytes(),before);self.assertEqual((root/'run').read_bytes(),m.wrapper_bytes(source));self.assertEqual(verify.call_args_list[0].args[1],m.PREDECESSOR)
 def test_failed_upgrade_leaves_previous_command_usable(self):
  root,legacy=self.legacy();before=(root/'run').read_bytes()
  with patch.object(m,'verify_source'),patch.object(m,'git',side_effect=subprocess.SubprocessError('synthetic')),self.assertRaises(subprocess.SubprocessError):m.install('a'*40,'b'*40)
  self.assertEqual((root/'run').read_bytes(),before);self.assertEqual((legacy/'prior-code').read_bytes(),b'preserved')
 def test_failed_atomic_switch_preserves_prior_wrapper(self):
  root,legacy=self.legacy();before=(root/'run').read_bytes();self.installed_layout()
  with patch.object(m,'verify_source'),patch.object(m.os,'replace',side_effect=OSError('synthetic')),self.assertRaises(OSError):m.install('a'*40,'b'*40)
  self.assertEqual((root/'run').read_bytes(),before);self.assertEqual((legacy/'prior-code').read_bytes(),b'preserved')
 def test_versioned_pin_must_match_source_directory(self):
  root,source=self.installed_layout();(root/'pins'/('a'*40+'.json')).write_text(json.dumps({'commit':'c'*40,'tree':'b'*40}))
  with patch.object(m,'__file__',str(source/'scripts/run-global-on-foo.py')),patch.object(m,'verify_source') as verify,self.assertRaises(ValueError):m.run()
  verify.assert_not_called()
 def test_unknown_legacy_pin_never_fetches(self):
  root,legacy=self.legacy();(root/'source-pin.json').write_text(json.dumps({'commit':'c'*40,'tree':'d'*40}))
  with patch.object(m,'git',side_effect=AssertionError('fetch')),self.assertRaises(ValueError):m.install('a'*40,'b'*40)
 def test_symlink_install_rejected_without_overwrite(self):
  root=self.home/'offmenu-global-collection';root.symlink_to(self.home/'absent')
  with self.assertRaises(ValueError):m.install('a'*40,'b'*40)
  self.assertTrue(root.is_symlink())
 def test_run_from_arbitrary_cwd_inherited_auth_and_publish_only(self):
  root,source=self.installed_layout();(root/'pins'/('a'*40+'.json')).write_text(json.dumps({'commit':'a'*40,'tree':'b'*40}))
  with patch.dict(os.environ,{'GITHUB_TOKEN':'synthetic-existing'}),patch.object(m,'__file__',str(source/'scripts/run-global-on-foo.py')),patch.object(m,'verify_source'),patch.object(m.os,'chdir') as cd,patch.object(m.os,'execvpe') as execute:
   m.run(True);args=execute.call_args.args;self.assertEqual(args[2]['GITHUB_TOKEN'],'synthetic-existing');self.assertNotIn('synthetic-existing',repr(args[:2]));self.assertEqual(args[1][-1],'--publish-only');cd.assert_called_once_with(source)
 def test_bad_launcher_args_stop(self):
  with patch.object(m.sys,'argv',['launcher','--url','https://invalid']),self.assertRaises(ValueError):m.main()
 def test_insecure_root_and_source_or_pin_symlinks_stop(self):
  root=self.home/'offmenu-global-collection';root.mkdir(mode=0o755)
  with self.assertRaises(ValueError):m.install('a'*40,'b'*40)
  root.chmod(0o700);(root/'sources').mkdir(mode=0o700);source=root/'sources'/('a'*40);source.symlink_to(self.home/'absent')
  with self.assertRaises(ValueError):m.install('a'*40,'b'*40)
  source.unlink();source.mkdir();(root/'pins'/('a'*40+'.json')).symlink_to(self.home/'absent')
  with patch.object(m,'__file__',str(source/'scripts/run-global-on-foo.py')),self.assertRaises(OSError):m.run()
if __name__=='__main__':unittest.main()
