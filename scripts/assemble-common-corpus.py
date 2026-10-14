#!/usr/bin/env python3
"""Combine immutable qualified source packages without expanding or rewriting their data."""
import argparse,collections,hashlib,json,os,re,shutil
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
GRAPH_COUNTS=['packets','resources','assertions','relations','translations']
CORE_SHA='c15005b224ae18c1e660837c6ac9fab88beb0b4d53ce34db6a5a87f12f6d919d'
def sha_file(path):
 h=hashlib.sha256()
 with path.open('rb') as f:
  for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
 return h.hexdigest()
def assemble(inputs,output,qualification):
 if output.exists():raise ValueError('Immutable output exists')
 evidence=json.loads(qualification.read_text());assert evidence['schemaVersion']=='offmenu-common-expansion-qualification/1' and evidence['status']=='all-packages-streamed-global-identities-references-and-provenance-checked'
 assert inputs[0][0]=='core' and sha_file(inputs[0][1]/'manifest.json')==CORE_SHA,'Pinned accepted core must be first'
 assert evidence['packageCount']==len(inputs)==len(evidence['packages'])
 for name,path in [('schemaByteSha256',ROOT/'corpus/common-data.schema.json'),('contractByteSha256',ROOT/'corpus/common-data-contract.json')]:assert evidence[name]==sha_file(path),'Validation definitions changed since qualification'
 qualified={str(Path(p['directory']).resolve()):p['manifestByteSha256'] for p in evidence['packages']};assert set(qualified)=={str(p.resolve()) for _,p in inputs},'Qualification package set mismatch'
 proof_packages={str(Path(p['directory']).resolve()):p for p in evidence['packages']}
 output.mkdir();files=[];packages=[];counts=collections.Counter({k:0 for k in GRAPH_COUNTS});source_records={};additional_recipes=0;recovered_recipes=0
 def asset(source,key,expected=None):
  keypath=Path(key);assert not keypath.is_absolute() and '..' not in keypath.parts
  digest=sha_file(source);size=source.stat().st_size
  if expected:assert digest==expected['sha256'] and size==expected['bytes'],'Source asset checksum mismatch'
  p=output/keypath;p.parent.mkdir(parents=True,exist_ok=True)
  if source.resolve().is_relative_to(ROOT):shutil.copyfile(source,p)
  else:
   try:os.link(source,p)
   except OSError:shutil.copyfile(source,p)
  item={'key':key,'bytes':size,'sha256':digest}
  if expected and 'packets' in expected:item['packets']=expected['packets']
  files.append(item)
 for name,directory in inputs:
  assert re.fullmatch('[a-z][a-z0-9-]*',name)
  assert sha_file(directory/'manifest.json')==qualified[str(directory.resolve())],'Manifest changed since global qualification'
  m=json.loads((directory/'manifest.json').read_text());status=str(m.get('status',''))
  assert not any(x in status.lower() for x in ['sample','benchmark','partial','pending','failed']),status
  assert m.get('files') and m.get('counts'), 'Missing qualification manifest'
  proof=proof_packages[str(directory.resolve())]
  assert {k:proof['observedCounts'][k] for k in GRAPH_COUNTS}=={k:m['counts'][k] for k in GRAPH_COUNTS},'Package counters differ from qualification'
  admitted=m.get('observedSourceRecords')
  if name=='core':admitted={'world-recipes':m['recipeRecords'],'foodon':29255}
  proof_admitted=admitted
  if isinstance(admitted,int) and not isinstance(admitted,bool):
   source_id=m.get('source',{}).get('id') or m.get('sourceId');assert source_id
   proof_admitted={source_id:admitted}
  assert proof['admittedSourceRecords']==proof_admitted,'Source admission declarations differ from qualification'
  coverage=admitted
  if m.get('sourceId')=='recipe-expansion-20261014':
   additional_recipes=sum(admitted.values());coverage={m['sourceId']:additional_recipes}
  elif m.get('source',{}).get('id')=='smithsonian-archive':
   recovered_recipes=admitted;coverage={} # New representations of existing source recipes.
  elif isinstance(admitted,int):
   source_id=m.get('source',{}).get('id') or m.get('sourceId');assert source_id
   coverage={source_id:admitted}
  assert isinstance(coverage,dict)
  for source,n in coverage.items():
   assert isinstance(n,int) and not isinstance(n,bool) and n>=0 and source not in source_records,'Ambiguous source coverage'
   source_records[source]=n
  for f in m['files']:asset(directory/f['key'],name+'/'+f['key'],f)
  asset(directory/'manifest.json',name+'/source-package-manifest.json')
  packages.append({'name':name,'status':status,'manifestKey':name+'/source-package-manifest.json','manifestByteSha256':sha_file(directory/'manifest.json'),'counts':m['counts'],'admittedSourceRecords':admitted,'sourceCollectionCoverage':coverage,'sources':m.get('sources'),'scope':m.get('scope')})
  for key in ['packets','resources','assertions','relations','translations']:
   if isinstance(m['counts'].get(key),int):counts[key]+=m['counts'][key]
 for path,key in [(ROOT/'corpus/common-data.schema.json','schema.json'),(ROOT/'corpus/common-data-contract.json','contract.json'),(ROOT/'corpus/common-source-mappings.json','source-mappings.json'),(ROOT/'docs/common-data-type-discovery-20261014.json','type-discovery.json')]:asset(path,key)
 assert dict(counts)=={k:evidence['aggregateObservedCounts'][k] for k in counts},'Qualified graph count mismatch'
 asset(qualification,'global-qualification.json')
 core=json.loads((inputs[0][1]/'manifest.json').read_text());mapping=json.loads((ROOT/'corpus/common-source-mappings.json').read_text());contract=json.loads((ROOT/'corpus/common-data-contract.json').read_text())
 assert source_records=={s['sourceId']:s['sourceRecords'] for s in mapping['sources']},'Declarative mapping differs from qualified source coverage'
 assert mapping['sourceCount']==len(source_records) and mapping['sourceRecordTotal']==sum(source_records.values())
 m={'schemaVersion':'offmenu-common-package/1','releaseId':'common-corpus-expanded-20261014','status':'all-source-packages-qualified-and-file-digests-checked','contractVersion':contract['schemaVersion'],'sourceCount':mapping['sourceCount'],'sourceRecordTotal':mapping['sourceRecordTotal'],'schema':'schema.json','contract':'contract.json','sourceMappings':'source-mappings.json','counts':counts,'sourcePackages':packages,'globalQualification':'global-qualification.json','recipeRecords':core['recipeRecords'],'recipeConcepts':core['recipeConcepts'],'crossSourceConcepts':core['crossSourceConcepts'],'multiLanguageConcepts':core['multiLanguageConcepts'],'identityEvidenceLinks':core['identityEvidenceLinks'],'files':files,'licence':'Original per-citation source licences and notices remain attached. Source package notices apply to their retained definitions and data.','scope':'Full source-specific common-schema graphs, coordinated as one typed and cited corpus. Original values, source identities, quantities and cultural variants remain distinct; no universal recipe synthesis or dietary qualification inferred. Additional recipes/units are separately reconciled in source packages.','originalSourceArchivesPublished':False,'privateDataPublished':False}
 m.update({'complete':True,'sourceGraphCoverage':source_records,'recipeLibraryRecords':core['recipeRecords'],'additionalRecipeSourceRecords':additional_recipes,'historicalRecoveryRepresentations':recovered_recipes,'recipeSourceRecords':core['recipeRecords']+additional_recipes,'sourceRecordCountingRule':'Counts admitted source collections once. Recovery variants are additional representations of existing recipes, excluded from source-record totals. Recipe-library downloads remain separately versioned.'})
 m['manifestSha256']=hashlib.sha256(json.dumps(m,separators=(',',':')).encode()).hexdigest();(output/'manifest.json').write_text(json.dumps(m,ensure_ascii=False,indent=2)+'\n');print(json.dumps({'releaseId':m['releaseId'],'counts':counts,'files':len(files),'packages':len(packages)}))
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('output',type=Path);p.add_argument('qualification',type=Path);p.add_argument('packages',nargs='+',help='name=qualified directory; core first');a=p.parse_args();assemble([(x.split('=',1)[0],Path(x.split('=',1)[1])) for x in a.packages],a.output,a.qualification)
