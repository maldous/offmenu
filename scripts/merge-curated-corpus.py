#!/usr/bin/env python3
"""Merge immutable local curation releases, replacing sources supplied later.

Entry IDs move by whole pages; source ranges never include alignment gaps.
Every checksum is revalidated. Original source data never enters this output.
"""
import argparse,gzip,hashlib,json,math,os
from pathlib import Path
from datetime import datetime,timezone

def sha(path):
 h=hashlib.sha256()
 with path.open('rb') as f:
  for b in iter(lambda:f.read(8*1024*1024),b''):h.update(b)
 return h.hexdigest()
def merge(inputs,output,version):
 if output.exists():raise ValueError('Immutable output exists')
 manifests=[json.loads((p/'manifest.json').read_text()) for p in inputs];first=manifests[0];page=first['entryPageSize'];winners={}
 for i,m in enumerate(manifests):
  if m['format']!='offmenu-curated/1' or m['status']!='curated-release-ready' or m['privateProviderData'] is not False or m['acquisitionAtRuntime'] is not False:raise ValueError('Invalid source curation')
  if m['entryPageSize']!=page or m['shardLength']!=first['shardLength'] or {k:v for k,v in m['curationPolicy'].items() if k!='publicSources'}!={k:v for k,v in first['curationPolicy'].items() if k!='publicSources'}:raise ValueError('Incompatible curation contracts')
  for source in m['sources']:winners[source]=i
 output.mkdir(parents=True);offsets=[];next_id=0
 for m in manifests:
  offset=math.ceil(next_id/page)*page;offsets.append(offset);next_id=offset+max((s['entryRange'][1] for s in m['sources'].values()),default=0)
 files={};sources={};posting_files={};pages_count=0
 for i,(root,m) in enumerate(zip(inputs,manifests)):
  offset=offsets[i]
  for source,s in m['sources'].items():
   if winners[source]==i:sources[source]={**s,'entryRange':[x+offset for x in s['entryRange']]}
  for metadata in m['files']:
   key=metadata['key'];p=root/key
   if p.stat().st_size!=metadata['bytes'] or sha(p)!=metadata['sha256']:raise ValueError('Input checksum mismatch: '+key)
   if key.startswith(('terms/','barcodes/')):posting_files.setdefault(key,[]).append((i,p));continue
   if key.startswith('records/'):
    source=key.split('/')[1]
    if winners[source]!=i:continue
    dest=output/key;dest.parent.mkdir(parents=True,exist_ok=True);os.link(p,dest)
   elif key.startswith('countries/'):
    source=key.split('/')[1]
    if winners[source]!=i:continue
    with gzip.open(p,'rt',encoding='utf8') as f:ids=json.load(f)
    dest=output/key;dest.parent.mkdir(parents=True,exist_ok=True)
    if offset==0:os.link(p,dest)
    else:
     with gzip.open(dest,'wt',encoding='utf8',compresslevel=1) as f:json.dump([ident+offset for ident in ids],f,separators=(',',':'))
   elif key.startswith('entries-'):
    with gzip.open(p,'rt',encoding='utf8') as f:original_rows=json.load(f)
    rows=[{**r,'id':r['id']+offset} for r in original_rows if winners[r['source']]==i]
    if not rows:continue
    page_id=int(key.removeprefix('entries-').removesuffix('.json.gz'))+offset//page;dest=output/f'entries-{page_id}.json.gz'
    if dest.exists():raise ValueError('Overlapping entry page')
    if offset==0 and len(rows)==len(original_rows):os.link(p,dest)
    else:
     with gzip.open(dest,'wt',encoding='utf8',compresslevel=1) as f:json.dump(rows,f,ensure_ascii=False,separators=(',',':'))
    pages_count+=1
   else:raise ValueError('Unexpected curation file '+key)
 for key,parts in posting_files.items():
  if len(parts)==1 and offsets[parts[0][0]]==0 and all(winners[source]==parts[0][0] for source in manifests[parts[0][0]]['sources']):
   dest=output/key;dest.parent.mkdir(parents=True,exist_ok=True);os.link(parts[0][1],dest);continue
  index={}
  for i,p in parts:
   with gzip.open(p,'rt',encoding='utf8') as f:
    for line in f:
     term,source_ids=json.loads(line)
     for source,ids in source_ids.items():
      if winners[source]==i:index.setdefault(term,{})[source]=[x+offsets[i] for x in ids]
  if not index:continue
  dest=output/key;dest.parent.mkdir(parents=True,exist_ok=True)
  with gzip.open(dest,'wt',encoding='utf8',compresslevel=1) as f:
   for term in sorted(index):f.write(json.dumps([term,index[term]],ensure_ascii=False,separators=(',',':'))+'\n')
 manifest={k:v for k,v in first.items() if k not in ['notices','manifestSha256','curatedAcceptance','files','sources','releaseId','completedAt','records','entries','entryPages']}
 notices={}
 for i,(root,m) in enumerate(zip(inputs,manifests)):
  for item in m.get('notices',[]):
   if winners.get(item['sourceId'])!=i:continue
   original=(root/item['key']).resolve()
   if not original.is_relative_to(root.resolve()) or sha(original)!=item['sha256'] or original.stat().st_size!=item['bytes']:raise ValueError('Licence document mismatch')
   destination=output/item['key'];destination.parent.mkdir(parents=True,exist_ok=True);os.link(original,destination);notices[item['key']]=item
 manifest['notices']=list(notices.values())
 manifest['curationPolicy']={**first['curationPolicy'],'publicSources':sorted(set(s for m in manifests for s in m['curationPolicy']['publicSources']))}
 manifest.update(releaseId=version,sources=sources,records=sum(s['records'] for s in sources.values()),entries=sum(s['bundles'] for s in sources.values()),entryPages=pages_count,completedAt=datetime.now(timezone.utc).isoformat(),mergedReleaseIds=[m['releaseId'] for m in manifests],files=[{'key':str(p.relative_to(output)),'bytes':p.stat().st_size,'sha256':sha(p)} for p in sorted(output.rglob('*.gz'))]);source_count=sum(len(m['sources']) for m in manifests)
 if len(winners)==source_count and all(m.get('curatedAcceptance',{}).get('status')=='all-curated-records-exercised' for m in manifests):
  accepted=[m['curatedAcceptance'] for m in manifests]
  if any(a['records']!=m['records'] for a,m in zip(accepted,manifests)):raise ValueError('Input acceptance count mismatch')
  acceptance={'status':'all-curated-records-exercised','releaseId':version,'rawSourcePayloadPublished':False,'independentlyAccepted':False,'method':'Composition of individually exercised immutable source files; every source-file checksum revalidated by merger.','limitation':'Structural and synthetic consumer checks do not establish independently reviewed food identity or dietary qualification.','completedAt':manifest['completedAt'],'countryRecordCounts':{}}
  for key in ['records','profiles','planningExercises','recipeReferences','prices','organizationReferences','guidelineReferences','retailerReferences','siteReferences']:acceptance[key]=sum(a.get(key,0) for a in accepted)
  for a in accepted:acceptance['countryRecordCounts'].update(a.get('countryRecordCounts',{}))
  manifest['curatedAcceptance']=acceptance
 manifest['manifestSha256']=hashlib.sha256(json.dumps(manifest,separators=(',',':')).encode()).hexdigest();(output/'manifest.json').write_text(json.dumps(manifest,separators=(',',':'))+'\n');print(json.dumps({'release':version,'sources':list(sources),'records':manifest['records'],'files':len(manifest['files'])}),flush=True)
 return manifest
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--input',type=Path,action='append',required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--version',required=True);a=p.parse_args();merge(a.input,a.output,a.version)
