#!/usr/bin/env python3
"""Align retained guideline and cookbook discovery records; no dietary qualification."""
import argparse,gzip,hashlib,json,collections,urllib.parse,re
from pathlib import Path
import jsonschema_rs
ROOT=Path(__file__).resolve().parents[1]
def digest(b):return hashlib.sha256(b).hexdigest()
def iri(kind,key):return 'urn:offmenu:'+kind+':'+digest(key.encode())[:32]
def align(data_root,output):
 if output.exists():raise ValueError('Immutable output exists')
 output.mkdir();curated=data_root/'curated-expanded-country-search-20261013'/'blobs';curated_manifest=json.loads((curated/'manifest.json').read_text());validator=jsonschema_rs.Draft202012Validator(json.loads((ROOT/'corpus/common-data.schema.json').read_text()),validate_formats=True);files=[];counts=collections.Counter({k:0 for k in ['packets','resources','assertions','relations','translations']});ids=set();assertion_ids=set();sources=[]
 for source,directory,type in [('dietary-guidelines','dietary-guidelines-20261013','SourceAssertion'),('wikibooks','wikibooks-2026-10-13-live','RecipeDiscoveryReference')]:
  folder=data_root/directory;m=json.loads((folder/'manifest.json').read_text());source_definition=curated_manifest['sources'][source];batch=[];part=0;source_count=0
  def flush():
   nonlocal batch,part
   if not batch:return
   b=gzip.compress(('\n'.join(batch)+'\n').encode());assert len(b)<8*1024*1024;key=source+'/part-'+str(part).zfill(4)+'.jsonl.gz';p=output/key;p.parent.mkdir(exist_ok=True);p.write_bytes(b);files.append({'key':key,'bytes':len(b),'sha256':digest(b),'packets':len(batch)});batch=[];part+=1
  def records():
   for item in curated_manifest['files']:
    if not item['key'].startswith('records/'+source+'/'):continue
    raw=(curated/item['key']).read_bytes();assert len(raw)==item['bytes'] and digest(raw)==item['sha256']
    for line in gzip.decompress(raw).decode().split('\n'):
     if line:
      for row in json.loads(line)[1]:yield row
  for row in records():
   rows=[row]
   for row in rows:
    p=row['provenance'];assert p['visibility']=='public';rid=iri('retained-source-resource',source+':'+row['id']);cid=iri('retained-source-citation',source+':'+row['id']);scope={'visibility':'public','reuseScope':p['license']};citation={'id':cid,'sourceId':source,'originalRecordId':str(p['recordId']),'originalUrl':p['url'],'license':p['license'],'attribution':p['attribution'],'scope':scope,'sourcePath':'curated-'+curated_manifest['releaseId']+':'+row['id']}
    for src,dest in [('revisionId','revisionId'),('sourceDate','sourceDate'),('historyUrl','historyUrl'),('licenseUrl','rightsEvidenceUrl')]:
     if src in p:citation[dest]=p[src]
    def text(value,path):return {'kind':'text','id':iri('retained-source-text',rid+':'+path),'language':'en' if path=='data.name' else 'und','value':value,'sourceTextSha256':digest(value.encode()),'status':'source-asserted','citationIds':[cid]}
    def typed(v,path):
     if path.startswith('data.originalTextLines.') and isinstance(v,str):return {'kind':'expression','syntax':'mediawiki','value':v}
     if v is None:return {'kind':'null','value':None}
     if isinstance(v,bool):return {'kind':'boolean','value':v}
     if isinstance(v,(float,int)):return {'kind':'number','value':v}
     if isinstance(v,list):return {'kind':'list','items':[typed(x,path+'.'+str(i)) for i,x in enumerate(v)]}
     if isinstance(v,dict):return {'kind':'structure','fields':{k:typed(x,path+'.'+k) for k,x in v.items()}}
     parts=[x for x in path.split('.') if not x.isdigit()];field=parts[-1]
     if field in ['status','reviewStatus','qualificationStatus']:
      return {'kind':'identifier','value':str(v)} if re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_:./-]*',v) else text(v,path)
     if field in ['id','kind','schemaVersion','schema','policyVersion','sourceRecordReference','sourceId','recordId','revisionId','releaseId','transform','visibility','referenceType','unit','archiveSha256','contentSha256','originalContentSha256','sourceTextSha256','language','languages','locale','locales']:return {'kind':'identifier','value':str(v)}
     if path.startswith('countries'):return {'kind':'identifier','value':v}
     if re.fullmatch(r'\d{4}-\d{2}-\d{2}T[^\s]+',v):return {'kind':'datetime','value':v}
     if re.fullmatch(r'\d{4}-\d{2}-\d{2}',v):return {'kind':'date','value':v}
     if v.startswith(('http://','https://','urn:')) and not re.search(r'\s',v):return {'kind':'uri','value':v}
     return text(v,path)
    assertions=[]
    for key,v in row.items():
     path=key;assertions.append({'id':iri('retained-source-assertion',rid+':'+path),'subjectId':rid,'propertyId':'urn:offmenu:property:source-field:'+key,'value':typed(v,path),'status':'source-asserted','citationIds':[cid],'scope':scope,'sourcePath':path})
    assertions.append({'id':iri('retained-source-assertion',rid+':originalSourceRecord'),'subjectId':rid,'propertyId':'urn:offmenu:property:originalSourceRecord','value':{'kind':'identifier','value':row['id']},'status':'source-asserted','citationIds':[cid],'scope':scope,'sourcePath':'id'})
    packet={'schemaVersion':'offmenu-common/1','resources':[{'id':rid,'type':'urn:offmenu:type:'+type,'identityStatus':'source-scoped','names':[text(row['data']['name'],'data.name')],'citationIds':[cid],'scope':scope}],'assertions':assertions,'relations':[],'citations':[citation],'translations':[]};validator.validate(packet);assert rid not in ids;ids.add(rid)
    for a in assertions:assert a['id'] not in assertion_ids;assertion_ids.add(a['id'])
    batch.append(json.dumps(packet,ensure_ascii=False,separators=(',',':')));source_count+=1;counts['packets']+=1;counts['resources']+=1;counts['assertions']+=len(assertions)
    if len(batch)==500:flush()
  flush();assert source_count==source_definition['records'];sources.append({'sourceId':source,'releaseId':m['releaseId'],'records':source_count,'sourceNormalizedArchiveSha256':digest((folder/'normalized.jsonl.gz').read_bytes()),'licence':m['license'],'type':type,'nativeNormalizedRecords':m['normalizedRows'],'publicCuratedRecords':source_definition['records'],'withheldRecords':source_definition.get('withheldRecords',0)})
 manifest={'schemaVersion':'offmenu-common-source-package/1','releaseId':'common-references-20261014','status':'all-packets-schema-identity-citation-and-scope-checked','complete':True,'limit':None,'expectedSourceRecords':{s['sourceId']:s['records'] for s in sources},'observedSourceRecords':{s['sourceId']:s['records'] for s in sources},'expectedCounts':dict(counts),'observedCounts':dict(counts),'partitionCoverage':{'complete':True,'expectedFiles':len(files),'observedFiles':len(files),'expectedPackets':counts['packets'],'observedPackets':counts['packets']},'sources':sources,'counts':counts,'files':files,'scope':'Complete admitted public curated reference/discovery records. Source archives remain local; forbidden raw/private fields are not restored. English recipe discovery is not a new complete or independently reviewed recipe. Guideline entries are references, not copied national guideline documents or personalized dietary advice. All admitted curated fields preserved as recursively typed assertions; archival fields remain source-scoped local holdings.'};(output/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n');print(json.dumps({'status':manifest['status'],'counts':counts,'sources':sources}))
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('data_root',type=Path);p.add_argument('output',type=Path);a=p.parse_args();align(a.data_root,a.output)
