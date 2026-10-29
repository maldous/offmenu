#!/usr/bin/env python3
"""Derive checked country/kind postings from an accepted immutable entry index."""
import argparse,array,collections,gzip,hashlib,json,os,re
from pathlib import Path
from datetime import datetime,timezone

def sha(path):
 h=hashlib.sha256()
 with path.open('rb') as f:
  for block in iter(lambda:f.read(8*1024*1024),b''):h.update(block)
 return h.hexdigest()
def index(root,output,version):
 if output.exists():raise ValueError('Immutable output exists')
 m=json.loads((root/'manifest.json').read_text())
 if m.get('curatedAcceptance',{}).get('status')!='all-curated-records-exercised':raise ValueError('Accepted records required')
 output.mkdir(parents=True);postings=collections.defaultdict(lambda:array.array('I'));count=0;source_counts=collections.Counter()
 for i,file in enumerate(sorted(m['files'],key=lambda f:(0,int(f['key'].removeprefix('entries-').removesuffix('.json.gz'))) if f['key'].startswith('entries-') else (1,f['key']))):
  path=root/file['key']
  if path.stat().st_size!=file['bytes'] or sha(path)!=file['sha256']:raise ValueError('Input checksum mismatch')
  destination=output/file['key'];destination.parent.mkdir(parents=True,exist_ok=True);os.link(path,destination)
  if file['key'].startswith('entries-'):
   with gzip.open(path,'rt',encoding='utf8') as f:rows=json.load(f)
   for row in rows:
    source=row['source'];ident=row['id'];count+=1;source_counts[source]+=1
    if source not in m['sources'] or not m['sources'][source]['entryRange'][0]<=ident<m['sources'][source]['entryRange'][1]:raise ValueError('Entry source range mismatch')
    for country in row['countries']:
     if not re.fullmatch('[A-Z]{2}',country):raise ValueError('Invalid country index code')
     postings[(source,country,'all')].append(ident)
     for kind in set(row['kinds']):postings[(source,country,kind)].append(ident)
  if i%5000==0:print(json.dumps({'filesChecked':i,'entriesIndexed':count}),flush=True)
 if count!=m['entries'] or any(source_counts[s]!=d['bundles'] for s,d in m['sources'].items()):raise ValueError('Full country index reconciliation failed')
 for (source,country,kind),ids in sorted(postings.items()):
  if any(ids[i]>=ids[i+1] for i in range(len(ids)-1)):raise ValueError('Country postings are not strictly ordered')
  key='countries/'+source+'/'+country+'-'+kind+'.json.gz';path=output/key;path.parent.mkdir(parents=True,exist_ok=True)
  with gzip.open(path,'wt',encoding='utf8',compresslevel=1) as f:json.dump(list(ids),f,separators=(',',':'))
  m['files'].append({'key':key,'bytes':path.stat().st_size,'sha256':sha(path)})
 for notice in m.get('notices',[]):
  path=root/notice['key']
  if sha(path)!=notice['sha256'] or path.stat().st_size!=notice['bytes']:raise ValueError('Licence checksum mismatch')
  destination=output/notice['key'];destination.parent.mkdir(parents=True,exist_ok=True);os.link(path,destination)
 for definition in m['sources'].values():definition['countryIndex']=True
 m['releaseId']=version;m['countryIndexAcceptance']={'entries':count,'postingFiles':len(postings),'status':'complete-checked-entry-derived-index','inputReleaseId':m['curatedAcceptance']['releaseId']};m['curatedAcceptance']={**m['curatedAcceptance'],'releaseId':version};m['completedAt']=datetime.now(timezone.utc).isoformat();m.pop('manifestSha256',None);m['manifestSha256']=hashlib.sha256(json.dumps(m,separators=(',',':')).encode()).hexdigest();(output/'manifest.json').write_text(json.dumps(m,separators=(',',':'))+'\n');print(json.dumps({'release':version,'records':m['records'],'entries':count,'countryPostingFiles':len(postings),'files':len(m['files'])}),flush=True)
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('input',type=Path);p.add_argument('output',type=Path);p.add_argument('--version',required=True);a=p.parse_args();index(a.input,a.output,a.version)
