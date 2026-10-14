#!/usr/bin/env python3
"""Prepare a reviewed static projection. No network, deploy, or raw-corpus copy."""
import collections,gzip,hashlib,json,pathlib,urllib.parse
ROOT=pathlib.Path(__file__).resolve().parent
SOURCE=pathlib.Path('/home/user/src/offmenu-data/world-recipes-global-final-20261014/normalized.jsonl.gz')
EXPECTED='90dcf2c498c8b86ba723a66214ce4573f32b4fc2b6d1c88c184ce5e365247e73'
OUT=ROOT/'.local/proposed-preview'
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def safeurl(v):
 try:
  u=urllib.parse.urlparse(str(v));return v if u.scheme in ['http','https'] and u.hostname and not u.username and not u.password else None
 except ValueError:return None
def writegz(name,value):
 p=OUT/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(gzip.compress(json.dumps(value,ensure_ascii=False,separators=(',',':')).encode(),mtime=0))
def identity(r):
 p=r['provenance'];return (p.get('originSourceId') or p['sourceId'])+'\0'+str(p.get('recordId') or r['id'])
assert SOURCE.stat().st_size==19589524 and digest(SOURCE)==EXPECTED
assert not OUT.exists(),'Frozen proposal exists; preserve it rather than overwrite reviewed payload'
OUT.mkdir(parents=True)
rows=[];pages=[];current=[];licences=collections.Counter();origins=collections.Counter();excluded=collections.Counter();read=0;seen=set()
with gzip.open(SOURCE,'rb') as f:
 for line in f:
  values=json.loads(line);values=values if isinstance(values,list) else [values]
  for r in values:
   if r.get('kind')!='recipe':continue
   read+=1;p=r['provenance'];d=r['data'];origin=p.get('originSourceId') or p.get('sourceId');key=hashlib.sha256(identity(r).encode()).hexdigest();assert key not in seen;seen.add(key)
   if origin=='recipecommons/openrecipe-spec':excluded['schema-example-fixture']+=1;continue
   if origin=='smithsonian-archive':excluded['incomplete-OCR-candidate-detail-scope']+=1;continue
   if p.get('visibility')!='public':excluded['private-or-unclassified']+=1;continue
   licence=p.get('license');uri=safeurl(p.get('licenseUrl'));sourceurl=safeurl(p.get('url'))
   if not licence or not uri or not sourceurl or not p.get('attribution'):excluded['missing-rights-or-public-source']+=1;continue
   if not d.get('ingredients') or not d.get('directions'):excluded['missing-details']+=1;continue
   ingredients=[]
   for ingredient in d['ingredients']:
    ingredients.append({k:ingredient[k] for k in ['name','amount','unit','optional','originalText','foodMatchStatus','sourceQuantity'] if k in ingredient} if isinstance(ingredient,dict) else str(ingredient))
   provenance={k:p[k] for k in ['sourceId','originSourceId','recordId','license','attribution','revisionId','sourceRevision','sourceDate','changes','recipeReuse','rightsEvidenceUrl'] if k in p}
   for k in ['url','licenseUrl','historyUrl','rightsEvidenceUrl']:
    if safeurl(p.get(k)):provenance[k]=p[k]
    else:provenance.pop(k,None)
   provenance['visibility']='public';provenance['presentationChanges']='Selected recipe fields serialized for static browse/search; no quantity conversion, automatic planning, dietary or origin inference.'
   projected={'schemaVersion':'offmenu-recipe-catalogue-projection/1','kind':'recipe','id':r['id'],'provenance':provenance,'data':{k:d[k] for k in ['name','languages','yield','quantityCoverage','reviewStatus','qualificationStatus','limitations'] if k in d}}
   projected['data'].update(ingredients=ingredients,directions=d['directions'],automaticPlanningEligible=False)
   page=len(pages);index=len(current);current.append(projected)
   rows.append({'key':key,'title':d.get('name') or 'Title not supplied','origin':origin,'language':','.join(d.get('languages') or []),'licence':licence,'review':d.get('reviewStatus') or 'unknown','ingredients':len(ingredients),'directions':len(d['directions']),'collection':'global-qualified','private':0,'part':f'recipes/part-{page:04}.json.gz','item':index})
   licences[licence]+=1;origins[origin]+=1
   if len(current)==100:writegz(f'recipes/part-{page:04}.json.gz',current);pages.append(len(current));current=[]
if current:writegz(f'recipes/part-{len(pages):04}.json.gz',current);pages.append(len(current))
assert read==25135 and len(seen)==25135
facets={name:[{'value':k or 'unknown','count':v} for k,v in counter.most_common()] for name,counter in [('sources',origins),('languages',collections.Counter(r['language'] for r in rows)),('licences',licences),('collections',collections.Counter({'global-qualified':len(rows)}))]}
public={'schema':'offmenu-recipe-catalogue-public-index/1','selectedSourceIdentities':len(rows),'sourceOccurrences':len(rows),'overlapOccurrences':0,'completeHeldInventory':False,'scope':f'First reviewed-payload proposal: {len(rows)} detail-bearing projected records from the verified 25,135-record main input; {sum(excluded.values())} excluded. Not ALL held recipes or release certification.','facets':facets,'inputRecords':read,'excludedCounts':dict(excluded),'items':rows}
writegz('catalogue-index.json.gz',public)
html=(ROOT/'index.html').read_text().replace('Private preparation · no new publication','Recipe catalogue · reviewed payload preview').replace('Your held recipes.','Browse the recipe collection.')
(OUT/'index.html').write_text(html)
(OUT/'style.css').write_bytes((ROOT/'style.css').read_bytes())
app=(ROOT/'app.js').read_text();start=app.index('async function api(path)');end=app.index('\nfunction sourceLink',start)
static='''let publicIndex;const detailPages=new Map();
async function gz(path){const r=await fetch(path,{signal:AbortSignal.timeout(30000)});if(!r.ok)throw Error('Projected recipe file unavailable');const b=new Uint8Array(await r.arrayBuffer());const t=b[0]===31&&b[1]===139?await new Response(new Blob([b]).stream().pipeThrough(new DecompressionStream('gzip'))).text():new TextDecoder().decode(b);return JSON.parse(t);}
async function api(path){publicIndex??=await gz('/catalogue-index.json.gz');const u=new URL(path,location.origin);if(u.pathname==='/api/inventory'){const {items,...inventory}=publicIndex;return inventory;}if(u.pathname==='/api/recipes'){let items=publicIndex.items;const q=(u.searchParams.get('q')||'').toLocaleLowerCase();if(q)items=items.filter(x=>[x.title,x.origin,x.language,x.licence,x.review].join(' ').toLocaleLowerCase().includes(q));for(const [param,key] of [['source','origin'],['language','language'],['licence','licence'],['collection','collection']]){const v=u.searchParams.get(param);if(v)items=items.filter(x=>(x[key]||'unknown')===v);}const page=Number(u.searchParams.get('page')||0);items=items.slice().sort((a,b)=>a.title.localeCompare(b.title)||a.key.localeCompare(b.key));return {total:items.length,page,items:items.slice(page*48,(page+1)*48)};}if(u.pathname==='/api/recipe'){const item=publicIndex.items.find(x=>x.key===u.searchParams.get('id'));if(!item)throw Error('Recipe not in reviewed payload');if(!detailPages.has(item.part)){if(detailPages.size>=4)detailPages.delete(detailPages.keys().next().value);detailPages.set(item.part,await gz('/'+item.part));}return {record:detailPages.get(item.part)[item.item],occurrences:[{collection:'main projected payload',source_id:item.origin,record_id:'see original provenance'}]};}throw Error('Unsupported catalogue route');}
'''
app=app[:start]+static+app[end:];(OUT/'app.js').write_text(app)
rights={'schema':'offmenu-catalogue-rights-notices/1','scope':'Source-derived recipe content retains each record licence/attribution/source revision. UI code is separate original presentation code.','changes':'Fields selected and serialized for static browsing; no images, media, source archives or original full-text containers; quantities remain source-qualified. No endorsement implied.','sourceLicenceCounts':dict(licences),'attribution':'Per-record attribution, licence URI, original source URL, revision/history and original change notices retained. CC BY-SA recipe derivatives remain share-alike under their source terms; CC0/Unlicense/public-domain-labelled records retain their labels without relicensing other components.','limitation':'Licence labels and original-source qualification are inherited from held records, not independent new legal/culinary certification. Incomplete OCR/schema-example fixtures excluded; no dietary/allergen/health/origin claim.'}
(OUT/'rights-notices.json').write_text(json.dumps(rights,ensure_ascii=False,indent=2)+'\n')
(OUT/'_headers').write_text("/*\n  X-Robots-Tag: noindex, nofollow\n  X-Content-Type-Options: nosniff\n  Referrer-Policy: no-referrer\n  Content-Security-Policy: default-src 'self'; connect-src 'self'; script-src 'self'; style-src 'self'; img-src 'self'; object-src 'none'; base-uri 'none'; frame-ancestors 'none'\n")
assets=[{'path':str(p.relative_to(OUT)),'localPath':str(p),'bytes':p.stat().st_size,'sha256':digest(p),'classification':'original UI/public presentation code' if p.name in ['index.html','app.js','style.css','_headers'] else 'derived retained-public real-recipe content and source rights notices; additional disclosure pending approval'} for p in sorted(OUT.rglob('*')) if p.is_file()]
manifest={'schema':'offmenu-recipe-publication-proposal/1','status':'FROZEN LOCAL PROPOSAL; NOT UPLOADED; specific disclosure approval required','source':{'path':str(SOURCE),'sha256':EXPECTED,'bytes':SOURCE.stat().st_size,'actualRecipeRecords':read,'directEOFVerified':True},'projectedRecords':len(rows),'excludedCounts':dict(excluded),'sourceLicenceDistribution':dict(licences),'privacyDistribution':{'sourceDeclaredPublicIncluded':len(rows),'personalIncluded':0,'internalOperationalIncluded':0,'schemaFixtureIncluded':0,'incompleteOCRIncluded':0},'destination':{'existingSite':'offmenu-corpus','siteId':'a1df1508-4bb9-4b55-ab1f-88611e456e61','teamId':'6949661f255143bbcf578c0e','mode':'manual isolated DRAFT deploy ID permalink only','productionPublish':False,'productionOverwrite':False,'newSite':False,'visibility':'public URL; existing destination has no password/SSO protection'},'fields':{'index':['key','title','origin','language','licence','review','ingredient/direction counts','part/item pointer'],'record':['source-scoped id','name','languages','yield','ingredients: original text/name/amount/unit/optional/source quantity/food-match qualifier','directions','quantity/review/qualification/limitation fields','planning disabled'],'provenance':['source/origin IDs','record ID','public source URL','revision/history','licence URI and label','attribution','source change notices','presentation change notice'],'noInferredFields':['allergens','dietary suitability','nutrition','origin','complete/accepted recipe guarantee']},'excluded':['3796live-Wikibooks additional snapshot','42 expansion','70 editorial/internal app recipes','5 corrected historical','54843 raw historical-labelled objects','Fineli formula references','all personal/account data, credentials, private SQLite/index/source paths/PIDs/runtime receipts','raw full normalized corpus/archive/images/media and additional source files'],'artifactRoot':str(OUT),'allowlist':assets,'totalFiles':len(assets),'totalBytes':sum(a['bytes'] for a in assets),'allowlistSha256':hashlib.sha256(json.dumps([{k:v for k,v in a.items() if k!='localPath'} for a in assets],sort_keys=True,separators=(',',':')).encode()).hexdigest(),'deployMethod':'Installed Netlify CLI23.13 authenticated read-only listSites. Manual deploy explicit --dir/--site/no production flag; no build hooks or AgentRunner. No linked-site/settings modification needed.','costFacts':{'existingPlan':'nf_team_pro from connected site readback','paidBuildOrAgentRunnerRequested':False,'accountCreditsBandwidthOrDeployCostLimits':'unavailable; no new limit/spend setting inferred'},'approvalQuestion':f'Approve a public, isolated manual DRAFT snapshot on existing offmenu-corpus site a1df1508-4bb9-4b55-ab1f-88611e456e61 containing exactly these {len(assets)} files/{sum(a["bytes"] for a in assets)} bytes and {len(rows)} projected recipe records from the pinned 25,135 main input, with listed exclusions and retained source rights/attribution? Production and supplementary holdings remain excluded.'}
(ROOT/'publication-manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({'manifest':str(ROOT/'publication-manifest.json'),'manifestSha256':digest(ROOT/'publication-manifest.json'),'projectedRecords':len(rows),'excluded':dict(excluded),'files':len(assets),'bytes':manifest['totalBytes'],'allowlistSha256':manifest['allowlistSha256'],'licences':dict(licences),'destination':manifest['destination'],'approvalQuestion':manifest['approvalQuestion']}))
