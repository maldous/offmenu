#!/usr/bin/env python3
"""Validate and partition aligned data for the implementing agent and public download."""
import argparse,collections,gzip,hashlib,json,shutil,time
from pathlib import Path
import jsonschema_rs
ROOT=Path(__file__).resolve().parents[1]

def package(recipes,ontology,terminology,output):
 if output.exists():raise ValueError('Immutable package exists')
 output.mkdir();schema=json.loads((ROOT/'corpus/common-data.schema.json').read_text());contract=json.loads((ROOT/'corpus/common-data-contract.json').read_text());validator=jsonschema_rs.Draft202012Validator(schema,validate_formats=True);counts=collections.Counter();resources={};assertions=set();relations=set();references=set();files=[];start=time.time()
 def asset(key,bytes,packets=None):
  path=output/key;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(bytes);meta={'key':key,'bytes':len(bytes),'sha256':hashlib.sha256(bytes).hexdigest()}
  if packets is not None:meta['packets']=packets
  files.append(meta)
 def validate(packet):
  validator.validate(packet)
  local_citations={c['id'] for c in packet['citations']}
  for c in packet['citations']:assert c['scope']['visibility']=='public'
  def check_citations(value):
   if isinstance(value,dict):
    if 'citationIds' in value:assert set(value['citationIds'])<=local_citations,'Unresolved citation'
    if 'scope' in value:assert value['scope']['visibility']=='public','Non-public nested value'
    for child in value.values():check_citations(child)
   elif isinstance(value,list):
    for child in value:check_citations(child)
  check_citations(packet)
  for r in packet['resources']:
   assert r['id'] not in resources,'Duplicate resource';resources[r['id']]=r['type'];assert r['type'].split(':')[-1] in contract['types'];assert r['scope']['visibility']=='public';counts['resources']+=1
  for key,seen in [('assertions',assertions),('relations',relations)]:
   for item in packet[key]:
    assert item['id'] not in seen,'Duplicate '+key;seen.add(item['id']);assert item['scope']['visibility']=='public';assert set(item['citationIds'])<=local_citations;references.add(item['subjectId']);counts[key]+=1
    if key=='relations':references.add(item['objectId'])
  counts['translations']+=len(packet['translations']);counts['packets']+=1
 def write_group(file,group):
  batch=[];index=0
  def flush():
   nonlocal batch,index
   if not batch:return
   bytes=gzip.compress(('\n'.join(batch)+'\n').encode())
   if len(bytes)>8*1024*1024:raise ValueError('Partition exceeds delivery bound')
   asset(group+'/part-'+str(index).zfill(4)+'.jsonl.gz',bytes,len(batch));index+=1;batch=[]
  for line in gzip.open(file,'rt',encoding='utf8'):
   p=json.loads(line)
   if group=='recipes':
    source=p['citations'][0]['sourceId'];by_statement={a['subjectId']:a['id'] for a in p['assertions'] if a['propertyId']=='urn:offmenu:property:originalIngredientStatement'}
    for a in p['assertions']:
     if a['propertyId']=='urn:offmenu:property:scalingRule' and source!='unitools':
      a['status']='candidate';a['derivation']={'methodId':'urn:offmenu:method:normalizer-default-linear-scaling','inputAssertionIds':[by_statement[a['subjectId']]],'reviewStatus':'candidate'}
     if a['propertyId']=='urn:offmenu:property:sourceBook' and a['value']['kind']=='text':a['value']['language']='und'
   validate(p);batch.append(json.dumps(p,ensure_ascii=False,separators=(',',':')))
   if len(batch)==500:flush()
  flush()
 write_group(recipes/'recipe-concepts.jsonl.gz','concepts');write_group(recipes/'recipe-source-alignment.jsonl.gz','recipes');write_group(terminology/'ingredient-resources.jsonl.gz','terminology');write_group(ontology/'foodon-common.jsonl.gz','ontology')
 unresolved=references-set(resources)
 assert all(id.startswith(('urn:offmenu:country:','urn:offmenu:unit:','http://','https://')) for id in unresolved),'Unresolved internal resource references'
 for source,key in [(ROOT/'corpus/common-data.schema.json','schema.json'),(ROOT/'corpus/common-data-contract.json','contract.json'),(ROOT/'corpus/common-source-mappings.json','source-mappings.json'),(ROOT/'docs/common-data-type-discovery-20261014.json','type-discovery.json'),(ROOT/'public/recipe-ingredient-aliases.json','ingredient-aliases.json'),(recipes/'recipe-membership.json','recipe-membership.json'),(recipes/'recipe-identity-evidence.jsonl.gz','recipe-identity-evidence.jsonl.gz'),(ontology/'manifest.json','foodon-source-manifest.json')]:asset(key,source.read_bytes())
 base=recipes.parent/'foodon-research-20261014';asset('notices/foodon-CC-BY-4.0.txt',(base/'LICENSE.txt').read_bytes())
 metrics=json.loads((recipes/'manifest.json').read_text());mapping=json.loads((output/'source-mappings.json').read_text())
 manifest={'schemaVersion':'offmenu-common-package/1','releaseId':'common-data-20261014','status':'all-packets-schema-identity-citation-and-scope-checked','contractVersion':contract['schemaVersion'],'sourceCount':mapping['sourceCount'],'sourceRecordTotal':mapping['sourceRecordTotal'],'schema':'schema.json','contract':'contract.json','sourceMappings':'source-mappings.json','recipeRecords':metrics['sourceRecords'],'recipeConcepts':metrics['recipeConcepts'],'crossSourceConcepts':metrics['crossSourceConcepts'],'multiLanguageConcepts':metrics['multiLanguageConcepts'],'identityEvidenceLinks':metrics['identityEvidenceLinks'],'counts':counts,'declaredExternalReferenceCount':len(unresolved),'files':files,'licence':'Per-citation original licences apply; FoodOn definitions CC-BY-4.0; terminology facts CC0. Shared identities never remove upstream attribution/share-alike or private scope.','scope':'Data acquisition and alignment package. Corpus-wide source mappings plus fully aligned recipe/terminology/FoodOn packets. Application migration and translation implementation belongs to OffMenu i18n. Recipe concept joins are candidates; no new formulation, nutritional equivalence or dietary qualification inferred.','originalSourceArchivesPublished':False,'privateDataPublished':False,'seconds':time.time()-start}
 manifest['manifestSha256']=hashlib.sha256(json.dumps(manifest,separators=(',',':')).encode()).hexdigest();(output/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n');print(json.dumps({k:manifest[k] for k in ['status','recipeRecords','recipeConcepts','sourceCount','counts','declaredExternalReferenceCount','seconds']}))

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('recipes',type=Path);p.add_argument('ontology',type=Path);p.add_argument('terminology',type=Path);p.add_argument('output',type=Path);a=p.parse_args();package(a.recipes,a.ontology,a.terminology,a.output)
