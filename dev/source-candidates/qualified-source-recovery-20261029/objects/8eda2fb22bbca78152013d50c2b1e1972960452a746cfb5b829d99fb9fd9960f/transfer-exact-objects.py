from pathlib import Path
import subprocess,os,json,hashlib,datetime
OUT=Path('/home/user/Documents/Codex/2026-10-18/offmenu-worker00-shared-object-availability');P=json.loads((OUT/'exact-object-transfer-plan.json').read_text());SRC=P['sourceStore'];DST=P['destinationCommonGit'];ENV={k:v for k,v in os.environ.items() if not k.startswith('GIT_')};ENV.update(GIT_OPTIONAL_LOCKS='0',GIT_NO_LAZY_FETCH='1')
def git(store,*args,input=None):return subprocess.check_output(['git','--git-dir='+store,*args],input=input,env=ENV)
def h(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def metadata():
 root=Path(DST);files={}
 for folder in ['refs','worktrees','logs']:
  p=root/folder
  if p.exists():
   for f in p.rglob('*'):
    if f.is_file():files[str(f.relative_to(root))]=h(f)
 for rel in ['HEAD','index','packed-refs','config','config.worktree','FETCH_HEAD','ORIG_HEAD','info/refs','objects/info/alternates']:
  p=root/rel;files[rel]=h(p) if p.exists() else None
 return files
before=metadata();(OUT/'shared-git-metadata-before.json').write_text(json.dumps(before,indent=2)+'\n')
assert len(P['missingObjects'])==609 and P['missingExpandedBytes']==10021575
# Verify content-address identity for every transferred source object before packing.
q=subprocess.run(['git','--git-dir='+SRC,'cat-file','--batch'],input=('\n'.join(x['oid'] for x in P['missingObjects'])+'\n').encode(),env=ENV,capture_output=True,check=True);raw=q.stdout;offset=0;verified=[]
for row in P['missingObjects']:
 end=raw.index(b'\n',offset);header=raw[offset:end].decode().split();oid,kind,size=header[0],header[1],int(header[2]);start=end+1;body=raw[start:start+size];assert raw[start+size:start+size+1]==b'\n';offset=start+size+1
 assert oid==row['oid'] and kind==row['type'] and size==row['bytes'] and hashlib.sha1((kind+' '+str(size)).encode()+b'\0'+body).hexdigest()==oid
 verified.append({**row,'sha256':hashlib.sha256(body).hexdigest()})
assert offset==len(raw)
pack=git(SRC,'pack-objects','--stdout','--no-reuse-delta','--no-reuse-object',input=('\n'.join(x['oid'] for x in verified)+'\n').encode());(OUT/'exact-missing-objects.pack').write_bytes(pack)
cmd=['git','--git-dir='+DST,'index-pack','--stdin','--index-version=2'];r=subprocess.run(cmd,input=pack,env=ENV,capture_output=True);(OUT/'index-pack-command.json').write_text(json.dumps({'command':cmd,'exit':r.returncode,'stdout':r.stdout.decode(),'stderr':r.stderr.decode()},indent=2)+'\n');assert r.returncode==0,r.stderr.decode();packid=r.stdout.decode().split()[-1]
idx=Path(DST)/'objects/pack'/('pack-'+packid+'.idx');listing=git(DST,'verify-pack','-v',str(idx)).decode();(OUT/'verify-pack-output.txt').write_text(listing);packed={x.split()[0] for x in listing.splitlines() if len(x.split()[0])==40 and x.split()[1] in ['commit','tree','blob','tag']};assert packed=={x['oid'] for x in verified}
# Full selected-tip reachability must now resolve locally, without all refs/lazy fetch.
afterIds=git(DST,'rev-list','--objects','--no-object-names',*P['tips']).decode().splitlines();assert set(afterIds)==set(P['allSelectedReachableObjects'])
for oid in P['tips']:
 assert git(DST,'cat-file','-t',oid).strip()==b'commit'
 assert git(DST,'rev-parse',oid+'^{tree}')==git(SRC,'rev-parse',oid+'^{tree}')
 for rel in (['docs/operations/foo-return-2026-10-18/README.md','docs/operations/foo-return-2026-10-18/custody.json'] if oid.startswith('28a5') else ['docs/operations/morgan-delivery-ledger.json']):assert git(DST,'show',oid+':'+rel)==git(SRC,'show',oid+':'+rel)
after=metadata();(OUT/'shared-git-metadata-after.json').write_text(json.dumps(after,indent=2)+'\n');assert before==after,'Unexpected shared metadata difference; preserve and report'
receipt={'resultId':'soleintegrator-exact-shared-object-availability-result-20261018','observedUTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),'sourceStore':SRC,'destinationCommonGit':DST,'tips':P['tips'],'reachableObjectsVerified':len(set(afterIds)),'objectsTransferred':len(verified),'expandedBytes':sum(x['bytes'] for x in verified),'packBytes':len(pack),'packSha256':hashlib.sha256(pack).hexdigest(),'packId':packid,'packPath':str(idx.with_suffix('.pack')),'indexPath':str(idx),'exactObjectContentVerified':True,'indexPackExit':r.returncode,'verifyPackExit':0,'packObjectsExactlyMatchPlannedMissingSet':True,'sharedRefsHeadsIndexesReflogsConfigFetchHeadUnchanged':before==after,'networkFetches':0,'objects':verified,'scope':'Selected two-tip complete missing ancestry/tree closure only; existing1983objects reused. No refs/branches/indexes/worktree/alternates edits; no collector/data/runtime/merge/control/security/automation operation. Existing bad zero-byte checkpoint ref untouched; no --all/fsck/repair used.'}
(OUT/'transfer-receipt.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps({k:receipt[k] for k in ['objectsTransferred','reachableObjectsVerified','packBytes','packSha256','packId','sharedRefsHeadsIndexesReflogsConfigFetchHeadUnchanged']}))
