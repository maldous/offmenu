#!/usr/bin/env python3
"""Attach a validated data-only package to the existing static corpus publication."""
import argparse,hashlib,json,shutil
from pathlib import Path
STATUS='all-packets-schema-identity-citation-and-scope-checked'
def digest(value):return hashlib.sha256(value).hexdigest()
def read(path):return json.loads(path.read_text())
def write_manifest_checksums(target):
 serving=read(target/'common-data/manifest.json');prefix='common-data/releases/'+serving['releaseId']+'/'
 files=[]
 for key in ['common-data/manifest.json',prefix+'manifest.json']:
  path=target/key;b=path.read_bytes();m=json.loads(b)
  payload=digest(json.dumps({k:v for k,v in m.items() if k!='manifestSha256'},ensure_ascii=True,separators=(',',':')).encode('utf8'));assert payload==m['manifestSha256']
  exact=digest(b);(target/(key+'.sha256')).write_text(exact+'  manifest.json\n')
  files.append({'key':key,'bytes':len(b),'byteSha256':exact,'payloadSha256':payload,'checksumUrl':'https://offmenu-corpus.netlify.app/'+key+'.sha256'})
 # Retained immutable releases remain downloadable and checksum-addressable.
 for path in sorted((target/'common-data/releases').glob('*/manifest.json')):
  key=path.relative_to(target).as_posix()
  if any(f['key']==key for f in files):continue
  b=path.read_bytes();m=json.loads(b)
  payload=digest(json.dumps({k:v for k,v in m.items() if k!='manifestSha256'},ensure_ascii=True,separators=(',',':')).encode('utf8'));assert payload==m['manifestSha256']
  exact=digest(b);(target/(key+'.sha256')).write_text(exact+'  manifest.json\n')
  files.append({'key':key,'bytes':len(b),'byteSha256':exact,'payloadSha256':payload,'checksumUrl':'https://offmenu-corpus.netlify.app/'+key+'.sha256'})
 receipt={'schemaVersion':'offmenu-manifest-checksums/1','byteSha256Definition':'SHA-256 of the exact UTF-8 file bytes, including whitespace and trailing newline. Use this value to pin downloaded manifests.','manifestSha256Definition':'Legacy producer payload digest: remove only the top-level manifestSha256 field, retain JSON member order, serialize with Python json.dumps ensure_ascii=True and separators=(comma,colon), then SHA-256 UTF-8 bytes. This is not a digest of downloaded bytes and not RFC 8785 canonical JSON.','files':files}
 (target/'common-data/manifest-checksums.json').write_text(json.dumps(receipt,indent=2)+'\n');return receipt
def publish(package,target):
 m=read(package/'manifest.json');assert m['status'] in [STATUS,'all-source-packages-qualified-and-file-digests-checked']
 encoded=json.dumps({k:v for k,v in m.items() if k!='manifestSha256'},separators=(',',':')).encode();assert digest(encoded)==m['manifestSha256']
 if m['status']=='all-source-packages-qualified-and-file-digests-checked':
  assert m.get('complete') is True
  key=m['globalQualification'];assert not Path(key).is_absolute() and '..' not in Path(key).parts
  asset=next(f for f in m['files'] if f['key']==key);b=(package/key).read_bytes();assert len(b)==asset['bytes'] and digest(b)==asset['sha256']
  proof=json.loads(b);assert proof['schemaVersion']=='offmenu-common-expansion-qualification/1' and proof['status']=='all-packages-streamed-global-identities-references-and-provenance-checked'
  assert proof['packageCount']==len(m['sourcePackages'])==len(proof['packages'])
  assert sorted(p['manifestByteSha256'] for p in proof['packages'])==sorted(p['manifestByteSha256'] for p in m['sourcePackages'])
  assert {k:proof['aggregateObservedCounts'][k] for k in m['counts']}==m['counts']
  assert proof['schemaByteSha256']==digest((package/m['schema']).read_bytes()) and proof['contractByteSha256']==digest((package/m['contract']).read_bytes())
  mapping=read(package/m['sourceMappings']);assert m['sourceGraphCoverage']=={s['sourceId']:s['sourceRecords'] for s in mapping['sources']}
  assert m['sourceCount']==len(m['sourceGraphCoverage']) and m['sourceRecordTotal']==sum(m['sourceGraphCoverage'].values())
 root=read(target/'manifest.json');recipes=read(target/'recipes/manifest.json');assert recipes['records']==m.get('recipeLibraryRecords',m['recipeRecords']);prefix='common-data/releases/'+m['releaseId']+'/'
 for f in m['files']:
  key=Path(f['key']);assert not key.is_absolute() and '..' not in key.parts
  b=(package/key).read_bytes();assert len(b)==f['bytes'] and digest(b)==f['sha256'];dest=target/prefix/key;dest.parent.mkdir(parents=True,exist_ok=True);
  if not dest.exists():
   try:__import__('os').link(package/key,dest)
   except OSError:dest.write_bytes(b)
  else:assert dest.read_bytes()==b,'Immutable destination differs'
 dest=target/prefix/'manifest.json';shutil.copyfile(package/'manifest.json',dest)
 serving={**m,'releaseBaseUrl':'https://offmenu-corpus.netlify.app/'+prefix,'packageManifestUrl':'https://offmenu-corpus.netlify.app/'+prefix+'manifest.json','baseCorpusManifest':'https://offmenu-corpus.netlify.app/manifest.json','recipeManifest':'https://offmenu-corpus.netlify.app/recipes/manifest.json','baseCorpusManifestSha256':root['manifestSha256'],'files':[{**f,'url':'https://offmenu-corpus.netlify.app/'+prefix+f['key']} for f in m['files']]}
 serving.pop('manifestSha256');serving['manifestSha256']=digest(json.dumps(serving,separators=(',',':')).encode());(target/'common-data/manifest.json').write_text(json.dumps(serving,ensure_ascii=False,indent=2)+'\n')
 for key in ['schema.json','contract.json','source-mappings.json']:shutil.copyfile(package/key,target/'common-data'/key)
 recipes['library']['commonData']={'manifest':'https://offmenu-corpus.netlify.app/common-data/manifest.json','schema':'https://offmenu-corpus.netlify.app/common-data/schema.json','contract':'https://offmenu-corpus.netlify.app/common-data/contract.json','sourceMappings':'https://offmenu-corpus.netlify.app/common-data/source-mappings.json','status':m['status'],'releaseId':m['releaseId']};recipes.pop('manifestSha256');recipes['manifestSha256']=digest(json.dumps(recipes,ensure_ascii=False,separators=(',',':')).encode());(target/'recipes/manifest.json').write_text(json.dumps(recipes,ensure_ascii=False,separators=(',',':')))
 p=target/'index.html';s=p.read_text();s=__import__('re').sub(r'<h2>Common data contract</h2><p>.*?</p>','',s,flags=__import__('re').S);s=s.replace('</main>','<h2>Common data contract</h2><p><a href="/common-data/manifest.json">Aligned data manifest</a> · <a href="/common-data/schema.json">Schema</a> · <a href="/common-data/contract.json">Type and relation contract</a> · <a href="/common-data/source-mappings.json">Whole-corpus source mappings</a>. Original citations, cultural variants and typed quantities are retained. Candidate joins require review.</p></main>');p.write_text(s)
 write_manifest_checksums(target)
 print(json.dumps({'status':'checked-common-data-publication-ready','files':len(m['files']),'recipeRecords':m['recipeRecords'],'sourceCount':m['sourceCount'],'manifestSha256':serving['manifestSha256'],'baseCorpusUnchanged':root['releaseId']}))
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('package',type=Path);p.add_argument('target',type=Path);a=p.parse_args();publish(a.package,a.target)
