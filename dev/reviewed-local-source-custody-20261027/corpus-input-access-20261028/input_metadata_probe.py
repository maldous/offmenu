import os,json,hashlib,stat,shutil
from pathlib import Path
roots=['common-bulk-food-20261014','curated-expanded-country-search-20261013/blobs']
out={'schema':'offmenu-input-metadata/1','inputs':[]}
for name in roots:
 p=Path('/offmenu-corpus')/name
 v={'root':name,'exists':p.is_dir(),'writable':os.access(p,os.W_OK)}
 m=p/'manifest.json'
 if m.is_file():
  assert m.stat().st_size<16000000
  b=m.read_bytes();d=json.loads(b)
  v.update(manifestBytes=len(b),manifestByteSha256=hashlib.sha256(b).hexdigest(),topKeys=sorted(d.keys()))
  for k in ['schema','schemaVersion','format','version','releaseId','manifestSha256','manifestPayloadSha256','counts','expectedCounts','observedCounts','coverage','contractVersion','schemaSha256','contractSha256']:
   if k in d:v[k]=d[k]
  for k in ['files','notices']:
   a=d.get(k,[])
   if isinstance(a,list):v[k+'Count']=len(a);v[k+'DeclaredBytes']=sum(x.get('bytes',0) for x in a)
  v['sources']={k:{f:x[f] for f in ['records','expectedRecords','releaseId','archiveSha256','rawSourcePayloadPublished'] if f in x} for k,x in d.get('sources',{}).items()} if isinstance(d.get('sources',{}),dict) else None
  if 'manifestSha256'in d:
   payload={k:x for k,x in d.items() if k!='manifestSha256'}
   v['manifestPayloadDigestMatches']=hashlib.sha256(json.dumps(payload,ensure_ascii=True,separators=(',',':')).encode()).hexdigest()==d['manifestSha256']
  count=total=links=0
  for base,ds,fs in os.walk(p,followlinks=False):
   for f in fs:
    s=(Path(base)/f).lstat()
    if stat.S_ISREG(s.st_mode):count+=1;total+=s.st_size
    else:links+=1
  v.update(actualRegularFiles=count,actualBytes=total,nonRegularFiles=links)
 out['inputs'].append(v)
u=shutil.disk_usage('/offmenu/data');out['disk']={'total':u.total,'used':u.used,'free':u.free,'freeGiB':round(u.free/2**30,3)}
out['codePins']={}
for f in ['scripts/repair-bulk-controls-20261014.py','scripts/verify-bulk-repair-checkpoint.py','scripts/align-places-common.py','scripts/places_checkpoint.py','corpus/common-data.schema.json','corpus/common-data-contract.json']:
 p=Path('/offmenu')/f
 out['codePins'][f]=hashlib.sha256(p.read_bytes()).hexdigest() if p.is_file() else None
print(json.dumps(out,separators=(',',':')))
