#!/usr/bin/env python3
"""Pinned normal-user setup and repeatable global collection entrypoint."""
import hashlib,json,os,pwd,re,shlex,stat,subprocess,sys,tempfile,fcntl,threading
from pathlib import Path
REPOSITORY='https://github.com/maldous/offmenu.git'
PINNED_FILES={'docs/collection-selections/belgium-permission-evidence.json': '0c7895dce194e92cf36ce923e5dfaa66c11f73c4c13dd57b846b0db2c35c029c', 'docs/collection-selections/belgium-two-fixed-contracts.json': '4c12c144d97edf7aa88e430b95cd629ea7357aabeeafbf58a7912cefe02ad96a', 'docs/collection-selections/global-known-assets-runtime.json': 'd846a735762e627fbf69475da958f39fa68418bea19c6b186e516f9e7feef270', 'docs/collection-selections/global-original-selection.json': '12bb04632ea6bbe078b68d28efab566f38c942e39a4339e91f02a738d7fe1008', 'docs/collection-selections/known-source-contract-enrichment.json': '58d198c9b0bebab95eade8d72f872bd30feb853104117fdcab1f8b31c26b41d2', 'docs/collection-selections/owner-local-runtime.json': '8dd3372dd9c2f4f0ec5f845cdc1a97c64addf8fe12ccecc26603128bb2bf514b', 'docs/collection-selections/py-larger-three-exact-contracts.json': '4dbcd7d6a3d3c0a0b787439617d67ebc814bc24064c0a9357b2c64259fcc4c49', 'docs/collection-selections/py-larger-three-metadata-evidence.json': 'c5ee54bbc021fb333b44a1f35af6d2f261f430b03712d5061869eec36a4947da', 'docs/collection-selections/recipe-batch-39162098764-prior-report.json': '423972355cb5c7007ccfc2add61eed2a503e4ce53cc93597e5e0d213e48a7265', 'docs/collection-selections/recipe-batch-recovery-diagnostic.json': 'fbfb376ebc943dc9c4e1f69ad58f6400c1c7fdbbaedbf4ac9c79c453352a82ab', 'docs/collection-selections/recipe-five-private-save-selection.json': 'c5ba55a9ca56c6f2bf42153ed3f3096b57a17845b0d4b9ebcd04caafcda24dcb', 'docs/collection-selections/recipe-five-recovery-observation.json': '4be1b7b1703617e29a67e4cc7d4265452ef30d990101200679ac2a01eae96f4b', 'docs/collection-selections/recipe-originals-batch-selection.json': '2b12090957ddc6cd9ab4393a1d1ea731132836fa35532ee0f6af59bbda84bc02', 'docs/collection-selections/swiss-v71-selection.json': '14f516e7c7a8b2eca7645bd13b5608b7d332217412dd97920da1e0c45fb0d042', 'docs/collection-selections/swiss-v71-source-evidence.json': 'ce0c272072de774effd377d7eee7933f85c079a34193d21e2419d0559ddac028', 'docs/collection-selections/zenodo15169428-head-diagnostic.json': '1bfe2d00a02353e92bcf9c7177865ba4e1153380e5a2cb35eed0f4515646af79', 'docs/collection-selections/zenodo15169428-selection.json': 'fc52fa57a04e389a5ec47509d8043477312bc4de2aae78267ca13a99c10b7bfd', 'docs/global-fixed-collection.md': '967f36b42b7e87c65447efbcc025add627476f1b4d310e016ea3fd94c4725d76', 'docs/media-preparation.md': '5eaa20ee37fde49acb8ee7e5f7ac1add0554a07eae7cf9bd6ea9348277687d51', 'docs/operations/global-collection-manual-handoff-20261018.json': 'fa87ebcb5463ffdec2f7bbfe0141da0c518b40a59c29297646b92a0644e165f1', 'docs/operations/retained-taiwan-boundary-diagnostic.md': '2ccdb9d407f43c15d3e69271327118ef44378ac0c73c92b264700ef753109ff0', 'docs/owner-local-global-collection.md': '0f4a7f810fe09ef511d7de586c98805a17a4e127773c5bfa1910e855144df1f6', 'offmenu/refresh/acquisition.py': '9a4ffa93b82c10d5971a61e2ce00277ad8e8e5dd58d9fec7d6bf9dfcf826105b', 'offmenu/refresh/core.py': '795fd06586c446c91be3bb592855e69dc42feb931e9a8044738c5dca94361e52', 'offmenu/refresh/media_preparation.py': '418b3bb5d006af25a072c5a91628c2ef080008d1ec4a6eea2c0008bf534c2dc5', 'schemas/media-preparation-contract.schema.json': '3ad39a7a8da79b7b7eb44ca7552cd0e1907ac467951ed3ae199a97c1723823cb', 'scripts/acquire-fixed-batch.py': '13e201bd23b6899e9e9191091cd6b2f760813db9c8994c3ef62a7decb44d7ee4', 'scripts/acquire-fixed-swiss.py': '2b9ccd32e58c7497e66923a635d67389dca957d4b26060098e8b60ba237c8e6d', 'scripts/acquire-fixed-zenodo.py': '0c314e7f55e565f01b9c26ed7269a04f1a9eaaa6ac353e47627a39b0210dbe67', 'scripts/collect-fixed-global.py': '1fb067e48135e1b1156f8c80c070fcf1ee519e77489d4c9927ea835b02ba3f10', 'scripts/collect-source-access.py': '7bc6cc34dc833e907a60239fe3d3b2f0b21d24f3fc7b9ff1c39e1189b614bb8d', 'scripts/diagnose-fixed-batch.py': 'ba3a61988343a690696f9f69c6d1c644451ff5be2126d8bfd91fbfca44b6f008', 'scripts/diagnose-retained-taiwan.py': 'a6f438929bbfa3a16d3678a4c0196fa234f5cc8ef3bb0b4e07db2552341da957', 'scripts/dispatch-foo-job.py': 'ea02466f1f665cfc2511c77e737cef546ef74316426940a71e24f1900749d361', 'scripts/prepare-fixed-collection.py': '25f825723b8725cce9c8d3197db4150ae5249d1489c4686c26282f84fe7a4c4b', 'scripts/publish-manual-global-result.py': 'fa11537ff721abab119652cc7ca301c649897951bc62226e324f5dd59f0f351a', 'scripts/save-private-original.py': 'ce6f7a4f15a6364d2e1bbcd147b054180c7339593299c0cea98e94846c3278ad', 'tests/fixtures/manual-global-handoff-checkpoint.json': 'fa87ebcb5463ffdec2f7bbfe0141da0c518b40a59c29297646b92a0644e165f1', 'tests/test_fixed_source_batch.py': 'a1829e95d980e971409dbdd54cd577ce38fafac3049c39053e21b3c0946f4e6b', 'tests/test_fixed_source_private_save.py': '874a2c37667d1b0953c9dc904d65762a2080496173e0fcce358c76048712b0b9', 'tests/test_global_collection.py': '8d79aca85622b697f843da1373c7d819a85c473b9953d0d40c4a6aa178cfc300', 'tests/test_manual_global_publication.py': '24a579cdfdfa165dd2fa5eb2ff92ca23856f06797635031c7a220fada6e1bb16', 'tests/test_media_preparation.py': '110184d05127edc3950aa4aed7951c6a92488cd3956e6ec565dacd0778542a16', 'tests/test_owner_launcher.py': '209babffebfd8e78c1bc10c3be426f0ef03bb293845165ed0690c3cda78d536c', 'tests/test_owner_local_collection.py': '2da77bc9f9b71864231e8a7c25cc23c6f7d6717831606cee41ad44cddf4eba6c', 'tests/test_resource_detection.py': '49c7165c8cfa7d314c62cb6cf1c078fe4e4dbd8736a4069454dd0cf7b2e0398e', 'tests/test_retained_taiwan_diagnostic.py': 'f373eab8a235569211ad8d70a95d217ed8241e025f1c258a5ec42e279325cee6'}
PREDECESSOR={'commit':'d97316cf3bdd9fce2d415b87a708d071ad8074e7','tree':'f05dd477739b713ddc9b0a31074ffa54b182e1c4'}
PREDECESSOR_FILES={'docs/collection-selections/belgium-permission-evidence.json': '0c7895dce194e92cf36ce923e5dfaa66c11f73c4c13dd57b846b0db2c35c029c', 'docs/collection-selections/belgium-two-fixed-contracts.json': '4c12c144d97edf7aa88e430b95cd629ea7357aabeeafbf58a7912cefe02ad96a', 'docs/collection-selections/global-known-assets-runtime.json': 'd846a735762e627fbf69475da958f39fa68418bea19c6b186e516f9e7feef270', 'docs/collection-selections/global-original-selection.json': '12bb04632ea6bbe078b68d28efab566f38c942e39a4339e91f02a738d7fe1008', 'docs/collection-selections/known-source-contract-enrichment.json': '58d198c9b0bebab95eade8d72f872bd30feb853104117fdcab1f8b31c26b41d2', 'docs/collection-selections/owner-local-runtime.json': '8dd3372dd9c2f4f0ec5f845cdc1a97c64addf8fe12ccecc26603128bb2bf514b', 'docs/collection-selections/py-larger-three-exact-contracts.json': '4dbcd7d6a3d3c0a0b787439617d67ebc814bc24064c0a9357b2c64259fcc4c49', 'docs/collection-selections/py-larger-three-metadata-evidence.json': 'c5ee54bbc021fb333b44a1f35af6d2f261f430b03712d5061869eec36a4947da', 'docs/collection-selections/recipe-batch-39162098764-prior-report.json': '423972355cb5c7007ccfc2add61eed2a503e4ce53cc93597e5e0d213e48a7265', 'docs/collection-selections/recipe-batch-recovery-diagnostic.json': 'fbfb376ebc943dc9c4e1f69ad58f6400c1c7fdbbaedbf4ac9c79c453352a82ab', 'docs/collection-selections/recipe-five-private-save-selection.json': 'c5ba55a9ca56c6f2bf42153ed3f3096b57a17845b0d4b9ebcd04caafcda24dcb', 'docs/collection-selections/recipe-five-recovery-observation.json': '4be1b7b1703617e29a67e4cc7d4265452ef30d990101200679ac2a01eae96f4b', 'docs/collection-selections/recipe-originals-batch-selection.json': '2b12090957ddc6cd9ab4393a1d1ea731132836fa35532ee0f6af59bbda84bc02', 'docs/collection-selections/swiss-v71-selection.json': '14f516e7c7a8b2eca7645bd13b5608b7d332217412dd97920da1e0c45fb0d042', 'docs/collection-selections/swiss-v71-source-evidence.json': 'ce0c272072de774effd377d7eee7933f85c079a34193d21e2419d0559ddac028', 'docs/collection-selections/zenodo15169428-head-diagnostic.json': '1bfe2d00a02353e92bcf9c7177865ba4e1153380e5a2cb35eed0f4515646af79', 'docs/collection-selections/zenodo15169428-selection.json': 'fc52fa57a04e389a5ec47509d8043477312bc4de2aae78267ca13a99c10b7bfd', 'docs/global-fixed-collection.md': '967f36b42b7e87c65447efbcc025add627476f1b4d310e016ea3fd94c4725d76', 'docs/media-preparation.md': '5eaa20ee37fde49acb8ee7e5f7ac1add0554a07eae7cf9bd6ea9348277687d51', 'docs/operations/global-collection-manual-handoff-20261018.json': 'fa87ebcb5463ffdec2f7bbfe0141da0c518b40a59c29297646b92a0644e165f1', 'docs/owner-local-global-collection.md': 'd08954267ff2a8b4e1bd884a035de39fdce07eb1829224b278ce2c91672e829e', 'offmenu/refresh/acquisition.py': '9a4ffa93b82c10d5971a61e2ce00277ad8e8e5dd58d9fec7d6bf9dfcf826105b', 'offmenu/refresh/core.py': '795fd06586c446c91be3bb592855e69dc42feb931e9a8044738c5dca94361e52', 'offmenu/refresh/media_preparation.py': '418b3bb5d006af25a072c5a91628c2ef080008d1ec4a6eea2c0008bf534c2dc5', 'schemas/media-preparation-contract.schema.json': '3ad39a7a8da79b7b7eb44ca7552cd0e1907ac467951ed3ae199a97c1723823cb', 'scripts/acquire-fixed-batch.py': '13e201bd23b6899e9e9191091cd6b2f760813db9c8994c3ef62a7decb44d7ee4', 'scripts/acquire-fixed-swiss.py': '2b9ccd32e58c7497e66923a635d67389dca957d4b26060098e8b60ba237c8e6d', 'scripts/acquire-fixed-zenodo.py': '0c314e7f55e565f01b9c26ed7269a04f1a9eaaa6ac353e47627a39b0210dbe67', 'scripts/collect-fixed-global.py': 'f1515c97fd627a51b56b558aff63fddd8265293baf082de5c5b3d0e9e083e411', 'scripts/collect-source-access.py': '7bc6cc34dc833e907a60239fe3d3b2f0b21d24f3fc7b9ff1c39e1189b614bb8d', 'scripts/diagnose-fixed-batch.py': 'ba3a61988343a690696f9f69c6d1c644451ff5be2126d8bfd91fbfca44b6f008', 'scripts/dispatch-foo-job.py': 'ea02466f1f665cfc2511c77e737cef546ef74316426940a71e24f1900749d361', 'scripts/prepare-fixed-collection.py': '25f825723b8725cce9c8d3197db4150ae5249d1489c4686c26282f84fe7a4c4b', 'scripts/publish-manual-global-result.py': 'fa11537ff721abab119652cc7ca301c649897951bc62226e324f5dd59f0f351a', 'scripts/run-global-on-foo.py': '4360412a0fd57dd5033233f29c80388940cdfee54282eabc683b7d0a9d0520c5', 'scripts/save-private-original.py': 'ce6f7a4f15a6364d2e1bbcd147b054180c7339593299c0cea98e94846c3278ad', 'tests/fixtures/manual-global-handoff-checkpoint.json': 'fa87ebcb5463ffdec2f7bbfe0141da0c518b40a59c29297646b92a0644e165f1', 'tests/test_fixed_source_batch.py': 'a1829e95d980e971409dbdd54cd577ce38fafac3049c39053e21b3c0946f4e6b', 'tests/test_fixed_source_private_save.py': '874a2c37667d1b0953c9dc904d65762a2080496173e0fcce358c76048712b0b9', 'tests/test_global_collection.py': 'f7cc1e22ad5fecb02eff35188f28ebbedcaca8453d86f11975d20435658c4dc0', 'tests/test_manual_global_publication.py': '24a579cdfdfa165dd2fa5eb2ff92ca23856f06797635031c7a220fada6e1bb16', 'tests/test_media_preparation.py': '110184d05127edc3950aa4aed7951c6a92488cd3956e6ec565dacd0778542a16', 'tests/test_owner_launcher.py': '62d37a3e57d6a99bb9b1663321f93cf217a72ca61ad5a8dfaa74310140a039d4', 'tests/test_owner_local_collection.py': '2da77bc9f9b71864231e8a7c25cc23c6f7d6717831606cee41ad44cddf4eba6c'}
AUTH_KEYS=('GH_TOKEN','GITHUB_TOKEN')
def clean_environment():
 home=pwd.getpwuid(os.getuid()).pw_dir
 config=os.environ.get('GH_CONFIG_DIR') or str(Path(os.environ.get('XDG_CONFIG_HOME') or str(Path(os.environ.get('HOME') or home)/'.config'))/'gh')
 env={'HOME':home,'PATH':'/usr/local/bin:/usr/bin:/bin','LANG':'C.UTF-8','GH_CONFIG_DIR':os.path.abspath(config),'GH_PROMPT_DISABLED':'1','GH_NO_UPDATE_NOTIFIER':'1','GIT_TERMINAL_PROMPT':'0','GIT_CONFIG_NOSYSTEM':'1','GIT_CONFIG_GLOBAL':'/dev/null','PYTHONDONTWRITEBYTECODE':'1'}
 env.update({k:os.environ[k] for k in AUTH_KEYS if k in os.environ})
 return env

def safe_directory(path,create=False,private=False):
 path=Path(path)
 for parent in reversed(path.parents):
  if parent.is_symlink():raise ValueError('unsafe-install-path')
 try:info=path.lstat()
 except FileNotFoundError:
  if not create:raise
  path.mkdir(mode=0o700);info=path.lstat()
 if not stat.S_ISDIR(info.st_mode) or info.st_uid!=os.getuid() or (private and info.st_mode&0o077):raise ValueError('unsafe-install-directory')
 return path

def safe_bytes(path,maximum=32*1024*1024):
 fd=os.open(path,os.O_RDONLY|os.O_NOFOLLOW)
 with os.fdopen(fd,'rb') as stream:
  info=os.fstat(stream.fileno())
  if not stat.S_ISREG(info.st_mode) or info.st_uid!=os.getuid() or info.st_size>maximum:raise ValueError('unsafe-install-file')
  raw=stream.read(maximum+1)
  if len(raw)>maximum:raise ValueError('install-file-limit')
  return raw

def immutable(path,raw,mode=0o600):
 try:
  if safe_bytes(path)!=raw:raise ValueError('existing-install-mismatch')
  return
 except FileNotFoundError:pass
 fd,name=tempfile.mkstemp(prefix='.install-',dir=path.parent)
 try:
  with os.fdopen(fd,'wb') as stream:os.fchmod(stream.fileno(),mode);stream.write(raw);stream.flush();os.fsync(stream.fileno())
  try:os.link(name,path)
  except FileExistsError:
   if safe_bytes(path)!=raw:raise ValueError('existing-install-mismatch')
 finally:os.unlink(name)

def git(env,*args):
 return subprocess.run(['git','-c','core.hooksPath=/dev/null',*map(str,args)],env=env,stdin=subprocess.DEVNULL,stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=180,check=True).stdout.decode().strip()

def verify_source(source,pin,env,pins=None):
 safe_directory(source);safe_directory(source/'.git')
 if git(env,'-C',source,'rev-parse','HEAD')!=pin['commit'] or git(env,'-C',source,'rev-parse','HEAD^{tree}')!=pin['tree']:raise ValueError('source-pin-mismatch')
 if git(env,'-C',source,'status','--porcelain','--untracked-files=all'):raise ValueError('source-checkout-changed')
 for name,digest in (PINNED_FILES if pins is None else pins).items():
  if hashlib.sha256(safe_bytes(source/name)).hexdigest()!=digest:raise ValueError('source-file-pin-mismatch')

def wrapper_bytes(source):
 return ('#!/bin/sh\nexec /usr/bin/python3 -I -B '+shlex.quote(str(source/'scripts/run-global-on-foo.py'))+' "$@"\n').encode()

def install(commit,tree):
 if not re.fullmatch('[a-f0-9]{40}',commit) or not re.fullmatch('[a-f0-9]{40}',tree):raise ValueError('invalid-source-pin')
 env=clean_environment();home=safe_directory(Path(env['HOME']));root=safe_directory(home/'offmenu-global-collection',True,True)
 fd=os.open(root/'.setup.lock',os.O_RDWR|os.O_CREAT|os.O_NOFOLLOW,0o600)
 try:
  info=os.fstat(fd)
  if not stat.S_ISREG(info.st_mode) or info.st_uid!=os.getuid():raise ValueError('unsafe-install-lock')
  fcntl.flock(fd,fcntl.LOCK_EX|fcntl.LOCK_NB)
  source=safe_directory(root/'sources',True,True)/commit;pins=safe_directory(root/'pins',True,True);pin={'commit':commit,'tree':tree}
  try:previous=safe_bytes(root/'run',4096)
  except FileNotFoundError:previous=None
  desired=wrapper_bytes(source);legacy=root/'source'
  if previous is not None and previous not in (wrapper_bytes(legacy),desired):raise ValueError('unknown-install-predecessor')
  if previous==wrapper_bytes(legacy):
   if json.loads(safe_bytes(root/'source-pin.json',1024))!=PREDECESSOR:raise ValueError('unknown-install-predecessor')
   verify_source(legacy,PREDECESSOR,env,PREDECESSOR_FILES)
  elif previous is None and (os.path.lexists(legacy) or os.path.lexists(root/'source-pin.json')):raise ValueError('incomplete-install-predecessor')
  if not os.path.lexists(source):
   staging=Path(tempfile.mkdtemp(prefix='.source-',dir=root))
   git(env,'init','--template=','-q',staging);git(env,'-C',staging,'remote','add','origin',REPOSITORY)
   git(env,'-C',staging,'-c','credential.helper=','-c','credential.helper=!gh auth git-credential','fetch','--no-tags','--depth=1','origin',commit)
   git(env,'-C',staging,'checkout','-q','--detach',commit);verify_source(staging,pin,env)
   if safe_bytes(staging/'scripts/run-global-on-foo.py')!=safe_bytes(Path(__file__).absolute()):raise ValueError('launcher-readback-mismatch')
   os.rename(staging,source)
  else:verify_source(source,pin,env)
  immutable(pins/(commit+'.json'),(json.dumps(pin,sort_keys=True)+'\n').encode())
  if previous!=desired:
   tempfd,name=tempfile.mkstemp(prefix='.run-',dir=root)
   try:
    with os.fdopen(tempfd,'wb') as stream:os.fchmod(stream.fileno(),0o700);stream.write(desired);stream.flush();os.fsync(stream.fileno())
    try:current=safe_bytes(root/'run',4096)
    except FileNotFoundError:current=None
    if current!=previous:raise ValueError('install-pointer-changed')
    os.replace(name,root/'run')
    directory=os.open(root,os.O_RDONLY|os.O_DIRECTORY)
    try:os.fsync(directory)
    finally:os.close(directory)
   finally:
    if os.path.lexists(name):os.unlink(name)
  print('Installed. Run: '+shlex.quote(str(root/'run')))
 finally:os.close(fd)

def announce_progress():
 def write():
  try:os.write(2,b'OffMenu pass stage=verifying-installation\n')
  except OSError:pass
 status=threading.Thread(target=write,name='collection-startup-progress',daemon=True);status.start();status.join(.2)

def run(publish_only=False):
 announce_progress()
 env=clean_environment();root=safe_directory(Path(env['HOME'])/'offmenu-global-collection',private=True);source=Path(__file__).absolute().parents[1]
 if source.parent!=root/'sources' or not re.fullmatch('[a-f0-9]{40}',source.name):raise ValueError('launcher-location-mismatch')
 pin=json.loads(safe_bytes(root/'pins'/(source.name+'.json'),1024));
 if set(pin)!={'commit','tree'} or pin.get('commit')!=source.name or any(not isinstance(v,str) or not re.fullmatch('[a-f0-9]{40}',v) for v in pin.values()):raise ValueError('invalid-source-pin')
 verify_source(source,pin,env)
 if Path(__file__).absolute()!=source/'scripts/run-global-on-foo.py':raise ValueError('launcher-location-mismatch')
 # Existing GitHub credentials are inherited, never placed in argv or written.
 args=['timeout','--signal=TERM','--kill-after=15s','1800s','/usr/bin/python3','-I','-B',str(source/'scripts/collect-fixed-global.py'),'--mode','user']
 if publish_only:args.append('--publish-only')
 os.chdir(source);os.execvpe(args[0],args,env)

def main():
 if os.getuid()==0 or os.geteuid()!=os.getuid():raise ValueError('normal-user-required')
 args=sys.argv[1:]
 if len(args)==3 and args[0]=='--install':install(args[1],args[2]);return
 if args not in ([],['--publish-only']):raise ValueError('unexpected-launcher-arguments')
 run(bool(args))
if __name__=='__main__':
 try:main()
 except (OSError,ValueError,subprocess.SubprocessError):
  print('OffMenu setup/run stopped before invoking collection. Check existing gh authentication and the pinned installation; no credentials were printed.',file=sys.stderr);raise SystemExit(3)
