#!/usr/bin/env python3
"""Read back every public package file and both native recipe downloads."""
import argparse,concurrent.futures,gzip,hashlib,json,time
from pathlib import Path
import requests

def verify(origin,target,output):
 def get(url):
  r=requests.get(url,timeout=180);r.raise_for_status();assert r.headers.get('Access-Control-Allow-Origin')=='*','CORS missing';return r
 manifest_bytes=get(origin+'/common-data/manifest.json').content;assert manifest_bytes==(target/'common-data/manifest.json').read_bytes(),'Serving manifest byte mismatch';remote=json.loads(manifest_bytes);local=json.loads((target/'common-data/manifest.json').read_text());assert remote==local,'Serving common manifest mismatch'
 checks=get(origin+'/common-data/manifest-checksums.json').json()
 for f in checks['files']:
  b=get(origin+'/'+f['key']).content;assert len(b)==f['bytes'] and hashlib.sha256(b).hexdigest()==f['byteSha256'],'Manifest byte checksum mismatch';m=json.loads(b);assert hashlib.sha256(json.dumps({k:v for k,v in m.items() if k!='manifestSha256'},ensure_ascii=True,separators=(',',':')).encode()).hexdigest()==f['payloadSha256']==m['manifestSha256'];assert get(origin+'/'+f['key']+'.sha256').text==f['byteSha256']+'  manifest.json\n'
 base=get(origin+'/manifest.json').json();assert base==json.loads((target/'manifest.json').read_text()),'Base corpus changed'
 recipes=get(origin+'/recipes/manifest.json').json();assert recipes==json.loads((target/'recipes/manifest.json').read_text()),'Recipe manifest mismatch';assert recipes['records']==remote['recipeRecords']
 def check(f):
  b=get(f['url']).content;assert len(b)==f['bytes'] and hashlib.sha256(b).hexdigest()==f['sha256'],f['key']+' digest mismatch'
  if 'packets' in f:assert gzip.decompress(b).count(b'\n')==f['packets'],f['key']+' packet count mismatch'
  return {'key':f['key'],'sha256':f['sha256'],'bytes':len(b),'status':'verified'}
 with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:files=list(pool.map(check,remote['files']))
 for key in ['schema.json','contract.json','source-mappings.json']:
  f=next(f for f in remote['files'] if f['key']==key);b=get(origin+'/common-data/'+key).content;assert hashlib.sha256(b).hexdigest()==f['sha256']
 downloads=[]
 for f in recipes['library']['downloads']:
  b=get(origin+'/releases/'+recipes['releaseId']+'/'+f['key']).content;assert len(b)==f['bytes'] and hashlib.sha256(b).hexdigest()==f['sha256'];raw=gzip.decompress(b);records=len(json.loads(raw)['@graph']) if 'schemaorg' in f['key'] else raw.count(b'\n');assert records==recipes['records'];downloads.append({**f,'records':records,'status':'verified'})
 result={'schemaVersion':'offmenu-common-publication-verification/1','status':'all-public-package-files-and-native-downloads-verified','origin':origin,'commonManifestSha256':remote['manifestSha256'],'commonManifestPayloadSha256':remote['manifestSha256'],'commonManifestByteSha256':hashlib.sha256(manifest_bytes).hexdigest(),'manifestChecksums':checks,'recipeManifestSha256':recipes['manifestSha256'],'baseManifestSha256':base['manifestSha256'],'baseRecords':base['records'],'recipeRecords':recipes['records'],'sourceCount':remote['sourceCount'],'checkedAtUnix':time.time(),'files':files,'nativeDownloads':downloads,'privateDataPublished':False,'applicationChanged':False};output.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({k:v for k,v in result.items() if k not in ['files','nativeDownloads']}))
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('origin');p.add_argument('target',type=Path);p.add_argument('output',type=Path);a=p.parse_args();verify(a.origin,a.target,a.output)
