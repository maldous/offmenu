from pathlib import Path
import json,gzip,csv,itertools,hashlib,datetime
OUT=Path(__file__).resolve().parents[1]/'public'
PAGES=OUT/'record-pages';PAGES.mkdir(exist_ok=True)
DATA=Path('/home/user/src/offmenu-data')
SOURCE=DATA/'dev-preview-20261014/workers/worker-05/live-dev/3a50a8b5-5f92-4394-a0e7-ef3a3f7c1879/production-app'
types={key:{'id':key,'label':label,'pages':[],'indexedRecords':0,'countries':set(),'sources':[]} for key,label in [('ingredients','Ingredients'),('recipes','Recipes'),('nutrition','Nutrition'),('retailers','Retailers & providers'),('prices','Prices & baskets'),('dietary','Dietary references')]}
def add(kind,key,records,scope,total=None):
    if not records:return
    item=types[kind]
    for i in range(0,len(records),50):
        chunk=records[i:i+50];name=f'{kind}-{key}-{i//50:04d}.json';payload={'records':chunk}
        (PAGES/name).write_text(json.dumps(payload,ensure_ascii=False,separators=(',',':'))+'\n')
        countries=sorted(set((r.get('country') or 'unassigned') for r in chunk))
        item['pages'].append({'url':'/record-pages/'+name,'records':len(chunk),'countries':countries,'sourceKey':key})
        item['countries'].update(countries)
    item['indexedRecords']+=len(records)
    item['sources'].append({'name':key,'indexedRecords':len(records),'sourceRecordsReported':total,'scope':scope})

gateway=Path('/home/user/Documents/Codex/2026-10-13/task-3/data-type-record-index-v1')
manifest=json.loads((gateway/'manifest.json').read_text())
entry=manifest['types'][0]['pages'][0];raw=Path(entry['path']).read_bytes();assert hashlib.sha256(raw).hexdigest()==entry['sha256']
records=json.loads(raw)['records']
add('prices','WFP-Libya',records,'First retained CSV observations; source dates and units preserved.',69474)
je=DATA/'country-bundles-20261016/owner-45/JE/prices-increment-1/rpi-group-indices.csv'
rows=list(csv.DictReader(je.open()))
records=[{'id':f'jersey-rpi:csv-line:{i+2}','country':'JE','label':r['Quarter']+' '+r['Year']+' · Food index '+r['Food'],'dataType':'prices','values':r,'sourceId':'Statistics Jersey RPI','sourceURL':'https://opendata.gov.je/dataset/retail-prices-index','attribution':'Government of Jersey / Statistics Jersey','originalRecord':{'file':str(je),'csvLine':i+2},'recordFormat':'Original CSV row','specificIssue':'Index values; issuer base definition not bound in this snapshot.'} for i,r in enumerate(rows)]
add('prices','Jersey-RPI',records,'All 105 rows in this retained finite resource. Index points, not item prices.',105)

def first_records(path,limit):
    result=[]
    with gzip.open(path,'rt') as stream:
        for line in stream:
            batch=json.loads(line);batch=batch if isinstance(batch,list) else [batch]
            result.extend(batch[:limit-len(result)])
            if len(result)>=limit:break
    return result
for folder in ['afcd-3','ciqual-2025','cofid-2021','cnf-2015','mext-2023-main','germany-bls-4.0','matvaretabellen-2026','frida-5.5','fineli-20.0','foodfiles-2024-v01','sweden-food-2026-07-01']:
    path=DATA/folder/'normalized.jsonl.gz'
    if not path.exists():continue
    rows=first_records(path,50);records=[]
    for r in rows:
        d=r.get('data',{});p=r.get('provenance',{});values={'basis':d.get('basis')}
        nutrients={k:{f:v.get(f) for f in ['value','unit','qualifier','originalText','name'] if f in v} for k,v in d.get('nutrients',{}).items() if isinstance(v,dict)}
        values['nutrients']=nutrients
        records.append({'id':r['id'],'country':next(iter(r.get('countries',[])),None),'label':d.get('foodName') or r['id'],'dataType':'nutrition','values':values,'sourceId':p.get('sourceId'),'sourceURL':p.get('url'),'attribution':p.get('attribution'),'sourceDate':p.get('sourceDate'),'originalRecord':{'retainedFile':str(path),'publisherRecordId':p.get('recordId'),'releaseId':p.get('releaseId')},'recordFormat':'Retained normalized nutrient profile'})
    col=json.loads((DATA/folder/'manifest.json').read_text())
    add('nutrition',folder,records,'First 50 retained normalized food profiles; source qualifiers and basis retained.',col.get('normalizedRows'))

path=DATA/'wikidata-businesses-20261013-native/normalized.jsonl.gz'
records=[]
for r in first_records(path,100):
    p=r.get('provenance',{});d=r.get('data',{});label=d.get('name') or d.get('label') or r.get('id')
    if isinstance(label,dict):label=label.get('en') or next(iter(label.values()),r['id'])
    records.append({'id':r['id'],'country':next(iter(r.get('countries',[])),None),'label':label,'dataType':'retailers','values':d,'sourceId':p.get('sourceId'),'sourceURL':p.get('url'),'attribution':p.get('attribution'),'sourceDate':p.get('sourceDate'),'originalRecord':{'retainedFile':str(path),'publisherRecordId':p.get('recordId')},'recordFormat':'Retained normalized organization / role record'})
add('retailers','Wikidata-food-businesses',records,'First 100 retained food-business records. Country is the source assertion, not a store-location census.')

recipes=json.loads((SOURCE/'public/recipes.json').read_text());rr=[];ingredients=[]
for r in recipes:
    rr.append({'id':r['id'],'country':None,'label':r.get('title',r['id']),'dataType':'recipes','values':{k:r[k] for k in ['servings','time','ingredients','instructions'] if k in r},'sourceId':r.get('source'),'attribution':r.get('attribution'),'originalRecord':{'retainedFile':'public/recipes.json','recordId':r['id']},'recordFormat':'Bundled recipe record'})
    for i,v in enumerate(r.get('ingredients',[])):
        ingredients.append({'id':r['id']+':ingredient:'+str(i),'country':None,'label':v.get('ingredient') or v.get('name') or 'Ingredient mention','dataType':'ingredients','values':{**v,'recipe':r.get('title')},'sourceId':r.get('source'),'attribution':r.get('attribution'),'originalRecord':{'retainedFile':'public/recipes.json','recipeId':r['id'],'ingredientIndex':i},'recordFormat':'Recipe ingredient mention'})
add('recipes','Bundled-recipe-pack',rr,'All recipes in the existing app pack; includes OffMenu-authored starter recipes. Country is unassigned.',len(rr))
add('ingredients','Bundled-recipe-ingredient-mentions',ingredients,'All ingredient mentions in the app recipe pack; mentions are not a deduplicated ingredient dictionary.',len(ingredients))

country=json.loads((OUT/'country-progress.json').read_text())
index={'schema':'offmenu-data-browser/1','generatedUTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),'types':[{**v,'countries':sorted(v['countries'])} for v in types.values()],'countries':[{'code':c['code'],'name':c['name']} for c in country['countries']],'counts':country['counts'],'allocationAsOf':country['allocationAsOf'],'currentWork':country['currentWork'],'nextSteps':country['nextSteps']}
(OUT/'data-browser-index.json').write_text(json.dumps(index,ensure_ascii=False,separators=(',',':'))+'\n')
print(json.dumps({v['id']:v['indexedRecords'] for v in index['types']}))
