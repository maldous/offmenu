#!/usr/bin/env python3
"""Attach a validated data-only package to the existing static corpus publication."""
import argparse,hashlib,json,shutil
from pathlib import Path
STATUS='all-packets-schema-identity-citation-and-scope-checked'
def digest(value):return hashlib.sha256(value).hexdigest()
def read(path):return json.loads(path.read_text())
def publish(package,target):
 m=read(package/'manifest.json');assert m['status']==STATUS
 encoded=json.dumps({k:v for k,v in m.items() if k!='manifestSha256'},separators=(',',':')).encode();assert digest(encoded)==m['manifestSha256']
 root=read(target/'manifest.json');recipes=read(target/'recipes/manifest.json');assert recipes['records']==m['recipeRecords'];prefix='common-data/releases/'+m['releaseId']+'/'
 for f in m['files']:
  key=Path(f['key']);assert not key.is_absolute() and '..' not in key.parts
  b=(package/key).read_bytes();assert len(b)==f['bytes'] and digest(b)==f['sha256'];dest=target/prefix/key;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(b)
 dest=target/prefix/'manifest.json';shutil.copyfile(package/'manifest.json',dest)
 serving={**m,'releaseBaseUrl':'https://offmenu-corpus.netlify.app/'+prefix,'packageManifestUrl':'https://offmenu-corpus.netlify.app/'+prefix+'manifest.json','baseCorpusManifest':'https://offmenu-corpus.netlify.app/manifest.json','recipeManifest':'https://offmenu-corpus.netlify.app/recipes/manifest.json','baseCorpusManifestSha256':root['manifestSha256'],'files':[{**f,'url':'https://offmenu-corpus.netlify.app/'+prefix+f['key']} for f in m['files']]}
 serving.pop('manifestSha256');serving['manifestSha256']=digest(json.dumps(serving,separators=(',',':')).encode());(target/'common-data/manifest.json').write_text(json.dumps(serving,ensure_ascii=False,indent=2)+'\n')
 for key in ['schema.json','contract.json','source-mappings.json']:shutil.copyfile(package/key,target/'common-data'/key)
 recipes['library']['commonData']={'manifest':'https://offmenu-corpus.netlify.app/common-data/manifest.json','schema':'https://offmenu-corpus.netlify.app/common-data/schema.json','contract':'https://offmenu-corpus.netlify.app/common-data/contract.json','sourceMappings':'https://offmenu-corpus.netlify.app/common-data/source-mappings.json','status':STATUS,'releaseId':m['releaseId']};recipes.pop('manifestSha256');recipes['manifestSha256']=digest(json.dumps(recipes,ensure_ascii=False,separators=(',',':')).encode());(target/'recipes/manifest.json').write_text(json.dumps(recipes,ensure_ascii=False,separators=(',',':')))
 p=target/'index.html';s=p.read_text();s=s.replace('</main>','<h2>Common data contract</h2><p><a href="/common-data/manifest.json">Aligned data manifest</a> · <a href="/common-data/schema.json">Schema</a> · <a href="/common-data/contract.json">Type and relation contract</a> · <a href="/common-data/source-mappings.json">Whole-corpus source mappings</a>. Original citations, cultural variants and typed quantities are retained. Candidate joins require review.</p></main>');p.write_text(s)
 print(json.dumps({'status':'checked-common-data-publication-ready','files':len(m['files']),'recipeRecords':m['recipeRecords'],'sourceCount':m['sourceCount'],'manifestSha256':serving['manifestSha256'],'baseCorpusUnchanged':root['releaseId']}))
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('package',type=Path);p.add_argument('target',type=Path);a=p.parse_args();publish(a.package,a.target)
