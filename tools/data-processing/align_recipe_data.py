#!/usr/bin/env python3
"""Produce citation-bearing common-schema data from collected recipes, not UI code."""
import argparse,collections,gzip,hashlib,json,re,urllib.parse
from pathlib import Path
from recipe_format import norm,ALIASES

def digest(value):return hashlib.sha256(value.encode()).hexdigest()
def identifier(kind,key):return 'urn:offmenu:'+kind+':'+digest(key)[:24]
def language(code):return 'en-x-simple' if code=='simple' else code or 'und'
SEEDS={
 'ratatouille':['ratatouille','ratatouille2','ratatouille3'],
 'hummus':['hummus','houmous','hummous','hommos','חומוס','хумус','حمص'],
 'paella':['paella','paellà','パエリャ','паэлья'],
 'guacamole':['guacamole','guacamol','гуакамоле'],
 'crepe':['crêpe','crêpes','crepe','crepes'],
 'hard-boiled-egg':['hard boiled eggs','hard-boiled eggs','hard cooked eggs','hard-cooked eggs','œuf dur','oeuf dur','œufs durs','hartgekochte eier'],
 'omelette':['omelette','omelet','omelett','омлет'],
}

def align(input_dir,wikis,english,output):
 if output.exists():raise ValueError('Immutable common data output already exists')
 output.mkdir();rows=[]
 for line in gzip.open(input_dir/'normalized.jsonl.gz','rt',encoding='utf8'):rows.extend(json.loads(line))
 byid={r['id']:r for r in rows};parent={id:id for id in byid};edges=[]
 def find(id):
  while parent[id]!=id:parent[id]=parent[parent[id]];id=parent[id]
  return id
 def union(a,b,method):
  aroot,broot=find(a),find(b)
  if aroot!=broot:parent[max(aroot,broot)]=min(aroot,broot)
  edges.append({'from':a,'to':b,'basis':method})
 title_lookup={};page_lookup={}
 for r in rows:
  pub=r['data']['sourcePublisher'];p=r['provenance']
  if pub.startswith('wikibooks:'):
   code=pub.split(':')[1];title=urllib.parse.unquote(urllib.parse.urlsplit(p['url']).path.split('/wiki/',1)[-1]).replace('_',' ')
   title_lookup[(code,norm(title))]=r['id'];page_lookup[(code,str(p['recordId']))]=r['id']
 for directory,code in [(english/'originals','en'),*[(p,p.name) for p in wikis.iterdir() if p.is_dir()]]:
  for file in directory.glob('*revisions-*.json'):
   original=json.loads(file.read_text());pages=original if isinstance(original,list) else original.get('query',{}).get('pages',[])
   for page in pages:
    source=page_lookup.get((code,str(page.get('pageid'))))
    if not source or not page.get('revisions'):continue
    body=page['revisions'][0]['slots']['main']['content']
    for target_code,title in re.findall(r'\[\[([a-z][a-z0-9-]{1,10}):([^\]|]+)(?:\|[^\]]*)?\]\]',body):
     target=title_lookup.get((target_code,norm(title.replace('_',' '))))
     if target and source!=target:union(source,target,'publisher-interlanguage-recipe-link')
 for seed,names in SEEDS.items():
  variants=[r['id'] for r in rows if r['data'].get('ingredientExtractionComplete') is not False and norm(r['data']['name'].split(':')[-1]) in {norm(n) for n in names}]
  for target in variants[1:]:union(variants[0],target,'curated-dish-name-candidate:'+seed)
 groups=collections.defaultdict(list)
 for r in rows:groups[find(r['id'])].append(r)
 membership={};concepts=[];scope={'visibility':'public','reuseScope':'Per-source licences and derivative requirements apply'}
 def citation(r):
  p=r['provenance'];c={'id':identifier('citation',r['id']),'sourceId':p.get('originSourceId',p['sourceId']),'originalRecordId':str(p['recordId']),'originalUrl':p['url'],'license':p['license'],'attribution':p['attribution'],'scope':scope}
  for key,target in [('revisionId','revisionId'),('sourceDate','sourceDate'),('originalContentSha256','contentSha256'),('rightsEvidenceUrl','rightsEvidenceUrl')]:
   if key in p:c[target]=p[key]
  if 'revisionId' not in c and p.get('sourceRevision'):c['revisionId']=p['sourceRevision']
  if p.get('historyUrl'):c['historyUrl']=p['historyUrl']
  return c
 def text(value,lang,key,cid):return {'kind':'text','id':identifier('text',key),'language':language(lang),'value':str(value),'sourceTextSha256':digest(str(value)),'status':'source-asserted','citationIds':[cid]}
 for root,members in sorted(groups.items()):
  # A recipe concept joins variants; it never declares their ingredient lists equal.
  seed=next((s for s,names in SEEDS.items() if any(r['data'].get('ingredientExtractionComplete') is not False and norm(r['data']['name'].split(':')[-1]) in {norm(n) for n in names} for r in members)),None)
  id='urn:offmenu:recipe-concept:'+seed if seed else identifier('recipe-concept',root)
  names=[];citations=[]
  for r in members:
   c=citation(r);citations.append(c);membership[r['id']]=id
   for lang,name in (r['data'].get('names') or {r['data']['languages'][0]:r['data']['name']}).items():names.append(text(name,lang,r['id']+':name:'+lang,c['id']))
  concepts.append({'schemaVersion':'offmenu-common/1','resources':[{'id':id,'type':'urn:offmenu:type:RecipeConcept','identityStatus':'candidate-join' if len(members)>1 else 'source-scoped','names':names,'citationIds':[c['id'] for c in citations],'scope':scope}],'assertions':[],'relations':[],'citations':citations,'translations':[]})
 def graph(r):
  d=r['data'];c=citation(r);cid=c['id'];rid=identifier('recipe-variant',r['id']);culture=identifier('cultural-representation',r['id']);lang=d['languages'][0];names=d.get('names') or {lang:d['name']};resources=[];assertions=[];relations=[];translations=[]
  def resource(id,type,names=None):resources.append({'id':id,'type':'urn:offmenu:type:'+type,'identityStatus':'source-scoped','names':names or [],'citationIds':[cid],'scope':scope})
  def fact(subject,property,value,path,status='source-asserted'):assertions.append({'id':identifier('assertion',r['id']+':'+subject+':'+property+':'+path),'subjectId':subject,'propertyId':'urn:offmenu:property:'+property,'value':value,'status':status,'citationIds':[cid],'sourcePath':path,'culturalRepresentationIds':[culture],'scope':scope})
  def relation(subject,predicate,obj,path,status='source-asserted'):relations.append({'id':identifier('relation',r['id']+subject+predicate+obj),'subjectId':subject,'predicateId':'urn:offmenu:relation:'+predicate,'objectId':obj,'status':status,'citationIds':[cid],'sourcePath':path,'scope':scope})
  resource(rid,'HistoricalRecipeCandidate' if d.get('ingredientExtractionComplete') is False else 'RecipeVariant',[text(name,l,r['id']+':name:'+l,cid) for l,name in names.items()]);resource(culture,'CulturalRepresentation')
  relation(rid,'variantOf',membership[r['id']],'data.name','candidate');relation(rid,'hasCulturalRepresentation',culture,'data.sourceCulture')
  fact(rid,'originalSourceRecord',{'kind':'identifier','value':r['id']},'id')
  for key in ['sourceCulture','sourceCuisineCountry','sourceBook','sourceOriginalLanguages','sourcePublicationYear','sourceExtraction','ingredientExtractionComplete']:
   if key in d:
    value=d[key];v={'kind':'boolean','value':value} if isinstance(value,bool) else {'kind':'number','value':value} if isinstance(value,(int,float)) else {'kind':'list','items':[{'kind':'identifier','value':str(x)} for x in value]} if isinstance(value,list) else {'kind':'identifier','value':str(value)} if key in ['sourceCuisineCountry','sourcePublicationYear'] else text(value,lang,r['id']+':'+key,cid)
    fact(culture,key,v,'data.'+key)
  fact(culture,'sourceLanguages',{'kind':'list','items':[{'kind':'identifier','value':l} for l in d['languages']]},'data.languages')
  fact(culture,'sourceEditionLanguage',{'kind':'identifier','value':lang},'data.languages.0')
  for country in r.get('countries',[]):relation(culture,'assertedOrigin','urn:offmenu:country:'+country,'countries','source-asserted')
  y=d['yield'];fact(rid,'yield',{'kind':'quantity','value':y['value'],'unitId':'urn:offmenu:unit:portion','dimension':'count','sourceValue':y['value'],'sourceUnit':y['unit'],'qualifiers':['source-yield' if y['value'] is not None else 'yield-unknown']},'data.yield')
  for index,i in enumerate(d['ingredients']):
   mention=identifier('ingredient-mention',r['id']+':'+str(index));path='data.ingredients.'+str(index)
   resource(mention,'IngredientMention',[text(n,l,r['id']+':ingredient:'+str(index)+':'+l,cid) for l,n in (i.get('names') or {lang:i['name']}).items()]);relation(rid,'usesIngredient',mention,path)
   if i.get('ingredientId'):relation(mention,'candidateMatch','urn:offmenu:ingredient:'+urllib.parse.quote(i['ingredientId'],safe=''),path+'.ingredientId','candidate')
   source=i['sourceQuantity'];q={'kind':'quantity','value':i['amount'],'unitId':'urn:offmenu:unit:'+i['unit'] if i['unit'] else None,'dimension':{'g':'mass','ml':'volume','count':'count'}.get(i['unit'],'unknown'),'sourceValue':source.get('value'),'sourceUnit':source.get('unit'),'sourceNotation':text(i['originalText'],lang,r['id']+':ingredient-original:'+str(index),cid),'qualifiers':[i['quantityStatus'],source['status']]}
   if source.get('range'):q['range']=source['range']
   fact(mention,'originalIngredientStatement',text(i['originalText'],lang,r['id']+':ingredient-original:'+str(index),cid),path+'.originalText');fact(mention,'requiredQuantity',q,path+'.sourceQuantity','candidate');assertions[-1]['derivation']={'methodId':'urn:offmenu:method:source-measure-normalisation-2','inputAssertionIds':[assertions[-2]['id']],'reviewStatus':'candidate'};fact(mention,'optional',{'kind':'boolean','value':i['optional']},path+'.optional')
   fact(mention,'scalingRule',{'kind':'identifier','value':i.get('scaling','linear')},path+'.scaling','source-asserted' if d['sourcePublisher']=='unitools' else 'candidate')
  steps=d.get('directionsByLanguage') or {lang:d['directions']}
  for index,step in enumerate(d['directions']):
   sid=identifier('recipe-step',r['id']+':'+str(index));resource(sid,'RecipeStep');relation(rid,'hasStep',sid,'data.directions.'+str(index));base=text(step,lang,r['id']+':step:'+str(index),cid);fact(sid,'instruction',base,'data.directions.'+str(index));fact(sid,'position',{'kind':'number','value':index+1},'data.directions.'+str(index))
   for target_lang,values in steps.items():
    if target_lang!=lang and index<len(values):translations.append({'id':identifier('translation',r['id']+':step:'+str(index)+':'+target_lang),'textId':base['id'],'language':language(target_lang),'value':values[index],'sourceTextSha256':base['sourceTextSha256'],'translator':d['sourcePublisher'],'method':'source-published','status':'published-source','citationIds':[cid],'terminologyResourceIds':[]})
  def literal(value,path):
   if value is None:return {'kind':'null','value':None}
   if isinstance(value,bool):return {'kind':'boolean','value':value}
   if isinstance(value,(int,float)):return {'kind':'number','value':value}
   if isinstance(value,list):return {'kind':'list','items':[literal(v,path+'.'+str(i)) for i,v in enumerate(value)]}
   if isinstance(value,dict):return {'kind':'structure','fields':{k:literal(v,path+'.'+k) for k,v in value.items()}}
   if path.split('.')[-1] in ['recipeSchema','sourcePublisher','reviewStatus','qualificationStatus','foodMatchStatus','quantityStatus','sourceIngredientId','status']:return {'kind':'identifier','value':str(value)}
   if isinstance(value,str) and value.startswith(('https://','http://')):return {'kind':'uri','value':value}
   return text(value,'und' if path.split('.')[-1]=='nativeName' else lang,r['id']+':'+path,cid)
  # Preserve typed additional source fields instead of dropping a newly discovered type.
  for key,value in d.items():
   if key not in ['name','names','languages','yield','ingredients','directions','directionsByLanguage','sourceCulture','sourceCuisineCountry','sourceBook','sourceOriginalLanguages','sourcePublicationYear','sourceExtraction','ingredientExtractionComplete','automaticPlanningEligible']:
    fact(rid,'source-field:'+key,literal(value,'data.'+key),'data.'+key)
  for index,i in enumerate(d['ingredients']):
   for key,value in i.items():
    if key not in ['name','names','ingredientId','amount','unit','optional','sourceQuantity','originalText','scaling']:
     fact(identifier('ingredient-mention',r['id']+':'+str(index)),'source-field:'+key,literal(value,'data.ingredients.'+str(index)+'.'+key),'data.ingredients.'+str(index)+'.'+key)
  fact(rid,'automaticPlanningEligible',{'kind':'boolean','value':False},'data.automaticPlanningEligible')
  return {'schemaVersion':'offmenu-common/1','resources':resources,'assertions':assertions,'relations':relations,'citations':[c],'translations':translations}
 def write(name,values):
  with gzip.open(output/name,'wt',encoding='utf8') as f:
   for value in values:f.write(json.dumps(value,ensure_ascii=False,separators=(',',':'))+'\n')
 write('recipe-concepts.jsonl.gz',concepts);write('recipe-source-alignment.jsonl.gz',(graph(r) for r in rows));write('recipe-identity-evidence.jsonl.gz',edges)
 (output/'recipe-membership.json').write_text(json.dumps(membership,ensure_ascii=False,separators=(',',':')))
 metrics={'schemaVersion':'offmenu-common-alignment/1','sourceRecords':len(rows),'recipeConcepts':len(concepts),'crossSourceConcepts':sum(len(g)>1 for g in groups.values()),'multiLanguageConcepts':sum(len({l for r in g for l in r['data']['languages']})>1 for g in groups.values()),'identityEvidenceLinks':len(edges),'identityNote':'Concept candidates group identified dish representations. Source variant measurements, methods and cultures remain separate; no quantities averaged, new worked recipe authored or source rights removed.','scope':'Data acquisition and alignment artifacts only; internationalization/application code is owned by the other agent.','files':[]}
 for file in sorted(output.iterdir()):metrics['files'].append({'key':file.name,'bytes':file.stat().st_size,'sha256':hashlib.sha256(file.read_bytes()).hexdigest()})
 (output/'manifest.json').write_text(json.dumps(metrics,ensure_ascii=False,indent=2)+'\n');print(json.dumps(metrics,ensure_ascii=False))

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('input',type=Path);p.add_argument('wikis',type=Path);p.add_argument('english',type=Path);p.add_argument('output',type=Path);a=p.parse_args();align(a.input,a.wikis,a.english,a.output)
