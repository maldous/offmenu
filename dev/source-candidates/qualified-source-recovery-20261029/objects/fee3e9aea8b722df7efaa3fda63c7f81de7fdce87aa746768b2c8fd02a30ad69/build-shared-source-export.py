from pathlib import Path
import subprocess,os,json,hashlib,io,tarfile,datetime
STORE='/tmp/offmenu-worker00-return-custody-20261018.git'
OUT=Path('/home/user/Documents/Codex/2026-10-18/offmenu-worker00-shared-availability');OUT.mkdir(exist_ok=True)
SHARED=Path('/home/user/Documents/Codex/2026-10-18/offmenu-shared-source');SHARED.mkdir(exist_ok=True)
ENV={k:v for k,v in os.environ.items() if not k.startswith('GIT_')};ENV.update(GIT_OPTIONAL_LOCKS='0',GIT_NO_LAZY_FETCH='1')
def run(path,*args):
 p=subprocess.run(['git','-C',str(path),*args],env=ENV,capture_output=True,text=True);return {'exit':p.returncode,'stdout':p.stdout,'stderr':p.stderr}
def snapshot(path):
 return {key:run(path,*args) for key,args in [('head',('rev-parse','HEAD')),('branch',('symbolic-ref','--short','-q','HEAD')),('status',('status','--porcelain=v1','--untracked-files=all')),('diff',('diff','--binary'))]}
def snapall():
 result={}
 for i in range(65):
  p=Path('/home/user/src/offmenu') if i==0 else Path(f'/home/user/src/offmenu-workers/worker-{i:02d}')
  if p.exists():
   v=snapshot(p);v['diffSha256']=hashlib.sha256(v.pop('diff')['stdout'].encode()).hexdigest();result[str(p)]=v
  else:result[str(p)]={'missing':True}
 return result
before=snapall();(OUT/'worktrees-before.json').write_text(json.dumps(before,indent=2)+'\n')
exports=[]
for label,commit in [('develop','abecb99ee1125730ccbc2824b6ec49ffc5cc4302'),('handover-pending-unmerged','28a5ba731dbac090303f92ebb90013a204e9f509')]:
 final=SHARED/f'{label}-{commit}';assert not final.exists(),'Do not overwrite existing export'
 pending=SHARED/f'.pending-{label}-{os.getpid()}';pending.mkdir()
 raw=subprocess.check_output(['git','--git-dir='+STORE,'ls-tree','-rz',commit]);entries=[]
 for row in raw.split(b'\0'):
  if not row:continue
  hdr,path=row.split(b'\t',1);mode,kind,oid=hdr.decode().split();path=path.decode();assert kind=='blob' and mode in ('100644','100755') and not Path(path).is_absolute() and '..' not in Path(path).parts
  entries.append({'path':path,'gitMode':mode,'blob':oid})
 archive=subprocess.check_output(['git','--git-dir='+STORE,'archive','--format=tar',commit]);archive_path=OUT/f'{label}-{commit}.tar';archive_path.write_bytes(archive)
 with tarfile.open(fileobj=io.BytesIO(archive)) as t:t.extractall(pending,filter='data')
 actual={str(p.relative_to(pending)) for p in pending.rglob('*') if p.is_file()};assert actual=={e['path'] for e in entries}
 for e in entries:
  p=pending/e['path'];b=p.read_bytes();assert hashlib.sha1(b'blob '+str(len(b)).encode()+b'\0'+b).hexdigest()==e['blob'];e.update(bytes=len(b),sha256=hashlib.sha256(b).hexdigest());p.chmod(0o555 if e['gitMode']=='100755' else 0o444)
 for p in sorted([x for x in pending.rglob('*') if x.is_dir()],key=lambda x:len(x.parts),reverse=True):p.chmod(0o555)
 pending.chmod(0o555);pending.rename(final)
 manifest={'schema':'offmenu-source-export/1','label':label,'commit':commit,'tree':subprocess.check_output(['git','--git-dir='+STORE,'rev-parse',commit+'^{tree}'],text=True).strip(),'root':str(final),'files':entries,'scope':'Tracked source tree only; no Git history/raw datasets/credentials, no admission or runtime activation. Pending handover is NOT develop baseline.','archive':{'path':str(archive_path),'sha256':hashlib.sha256(archive).hexdigest(),'bytes':len(archive)},'readOnly':'New export files0444 or0555 for original executable; directories0555. Existing workspace/settings permissions unchanged; same owner can deliberately alter modes, hash verification remains required.'}
 mp=OUT/f'{label}-manifest.json';mp.write_text(json.dumps(manifest,indent=2)+'\n');exports.append({'label':label,'commit':commit,'tree':manifest['tree'],'root':str(final),'fileCount':len(entries),'manifest':{'path':str(mp),'sha256':hashlib.sha256(mp.read_bytes()).hexdigest()},'archive':manifest['archive']})
reads=[]
for i in range(1,65):
 cwd=Path(f'/home/user/src/offmenu-workers/worker-{i:02d}')
 checks=[]
 for e in exports:
  p=Path(e['root'])/('README.md' if e['label']=='develop' else 'docs/operations/foo-return-2026-10-18/custody.json')
  code='from pathlib import Path;import hashlib; p=Path('+repr(str(p))+');print(hashlib.sha256(p.read_bytes()).hexdigest())'
  q=subprocess.run(['/bin/python3','-c',code],cwd=cwd,capture_output=True,text=True)
  expected=hashlib.sha256(p.read_bytes()).hexdigest();checks.append({'label':e['label'],'path':str(p),'exit':q.returncode,'sha256':q.stdout.strip(),'expectedSha256':expected,'passed':q.returncode==0 and q.stdout.strip()==expected,'stderr':q.stderr})
 reads.append({'worker':i,'cwd':str(cwd),'checks':checks,'note':'Read/hash subprocess in existing cwd as current normal user; not native agent pickup or actual session use.'})
after=snapall();(OUT/'worktrees-after.json').write_text(json.dumps(after,indent=2)+'\n');changed=[p for p in before if before[p]!=after[p]]
receipt={'schema':'offmenu-shared-source-availability/1','decision':'Morgan migration availability and closeout follow-through 2026-10-18','observedUTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),'exports':exports,'workerReadChecks':reads,'workerChecksPassed':sum(all(c['passed'] for c in r['checks']) for r in reads),'networkFetchesThisTask':0,'existingStore':STORE,'sharedGitMetadataModified':False,'worktreesObserved':len(before),'worktreeSnapshotDifferences':changed,'limits':['Read-only filesystem availability is verified for64cwd; native worker use/read acknowledgment not established.','Read-only exports are source references, not Git checkouts or changes to existing branches. Fresh task source must be current verified develop at scheduling time.','Handover pending tree includes PR42 and pendingUI requirements; do not adopt it as accepted develop.','No reset, shared fetch/ref/index edit, worker/coordinator, credentials, production/CIX, source data acquisition, Actions or automation changes.']}
(OUT/'availability-receipt.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps({'exports':exports,'workerChecksPassed':receipt['workerChecksPassed'],'worktreeSnapshotDifferences':changed}))
