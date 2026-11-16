#!/usr/bin/env python3
"""Assessor-run derived delta preparation after qualified assembly; no network or credentials."""
import argparse,hashlib,importlib.util,json,os,shutil
from pathlib import Path
BASE=Path('/offmenu/data/.offmenu-platform/corpus-recovery-20261028-v1/final-common-publication')
PUBLISHER=BASE/'publication-runtime-20261028/scripts/publish-common-data.py'
PIN='e3449bbcde6895a312889a8f7889d56ded34d744f7f7d34d19b2ab013f6b25f6'
SITE='a1df1508-4bb9-4b55-ab1f-88611e456e61'
def digest(b):return hashlib.sha256(b).hexdigest()
def main():
 p=argparse.ArgumentParser();p.add_argument('--qualification-sha256',required=True);p.add_argument('--assembly-manifest-sha256',required=True);p.add_argument('--base-deploy-id',required=True);a=p.parse_args()
 package=BASE/'assembled-common';seed=BASE/'publication-seed';target=BASE/'publication-delta';descriptor=BASE/'publication-delta.json'
 assert not target.exists() and not descriptor.exists(),'Existing candidate must be reconciled, not overwritten'
 assert digest(PUBLISHER.read_bytes())==PIN,'Reviewed publisher source differs'
 proof_bytes=(BASE/'global-qualification.json').read_bytes();assert digest(proof_bytes)==a.qualification_sha256
 proof=json.loads(proof_bytes);assert proof['status']=='all-packages-streamed-global-identities-references-and-provenance-checked' and proof['packageCount']==8
 assert digest((package/'manifest.json').read_bytes())==a.assembly_manifest_sha256
 m=json.loads((package/'manifest.json').read_bytes());assert m['complete'] is True and m['sourceCount']==22 and m['sourceRecordTotal']==22574390
 receipt=json.loads((seed/'seed-receipt.json').read_bytes());assert receipt['siteId']==SITE and receipt['baseDeployId']==a.base_deploy_id and receipt['qualificationSha256']==a.qualification_sha256
 # Only public base metadata and retained release manifests seed the reviewed publisher.
 for f in receipt['files']:
  key=f['path'];assert key.startswith('/') and '..' not in key.split('/') and key not in ('/seed-receipt.json',)
  src=seed/key.lstrip('/');assert not src.is_symlink() and digest(src.read_bytes())==f['sha256']
  assert key in ('/manifest.json','/recipes/manifest.json','/index.html') or key.startswith('/common-data/releases/') and key.endswith('/manifest.json')
  dest=target/key.lstrip('/');dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(src,dest)
 spec=importlib.util.spec_from_file_location('reviewed_publisher',PUBLISHER);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);module.publish(package,target)
 # Exclude unchanged base/retained metadata; uploader reuses their current remote digests.
 (target/'manifest.json').unlink()
 for f in receipt['files']:
  if f['path'].startswith('/common-data/releases/'):
   retained=target/f['path'].lstrip('/')
   if digest(retained.read_bytes())==f['sha256']:retained.unlink()
 files=[]
 for path in sorted(target.rglob('*')):
  if path.is_dir():continue
  assert path.is_file() and not path.is_symlink()
  h256=hashlib.sha256();h1=hashlib.sha1();size=0
  with path.open('rb') as stream:
   for block in iter(lambda:stream.read(1024*1024),b''):h256.update(block);h1.update(block);size+=len(block)
  files.append({'path':'/'+path.relative_to(target).as_posix(),'bytes':size,'sha256':h256.hexdigest(),'sha1':h1.hexdigest()})
 d={'schemaVersion':'offmenu-netlify-derived-delta/1','siteId':SITE,'baseDeployId':a.base_deploy_id,'qualificationSha256':a.qualification_sha256,'assemblyManifestSha256':a.assembly_manifest_sha256,'sourceCount':22,'sourceRecordTotal':22574390,'files':files}
 b=(json.dumps(d,separators=(',',':'))+'\n').encode();descriptor.write_bytes(b)
 print(json.dumps({'status':'derived_delta_ready_not_deployed','descriptor_sha256':digest(b),'descriptor_bytes':len(b),'delta_files':len(files),'delta_bytes':sum(f['bytes'] for f in files)}))
if __name__=='__main__':main()
