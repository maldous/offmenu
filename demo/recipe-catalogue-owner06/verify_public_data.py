import collections,gzip,hashlib,json,pathlib,urllib.request,zlib
ROOT=pathlib.Path(__file__).resolve().parent
URL='https://offmenu-corpus.netlify.app/recipes/manifest.json'
with urllib.request.urlopen(URL,timeout=30) as r:
 mb=r.read(4*1024*1024);assert not r.read(1),'Manifest4MiBcap';manifest=json.loads(mb)
local=pathlib.Path('/home/user/src/offmenu-data/world-recipes-global-final-20261014/normalized.jsonl.gz');assert hashlib.sha256(local.read_bytes()).hexdigest()=='90dcf2c498c8b86ba723a66214ce4573f32b4fc2b6d1c88c184ce5e365247e73'
def identity(r):
 p=r['provenance'];return (p.get('originSourceId')or p['sourceId'],str(p.get('recordId')or r['id']))
def signature(r):
 d=r['data'];p=r['provenance'];v={'name':d.get('name'),'languages':d.get('languages'),'ingredientsOriginal':[i.get('originalText')or i.get('name') if isinstance(i,dict) else i for i in d.get('ingredients',[])],'directions':d.get('directions'),'licence':p.get('license'),'attribution':p.get('attribution'),'sourceURL':p.get('url')};return hashlib.sha256(json.dumps(v,sort_keys=True,ensure_ascii=False).encode()).hexdigest()
original={}
with gzip.open(local,'rt') as f:
 for line in f:
  v=json.loads(line)
  for r in v if isinstance(v,list) else [v]:
   if r.get('kind')=='recipe':original[identity(r)]=signature(r)
ref=next(x for x in manifest['library']['downloads'] if x['key']=='recipes.jsonl.gz');url='https://offmenu-corpus.netlify.app/releases/'+manifest['releaseId']+'/'+ref['key'];h=hashlib.sha256();dec=zlib.decompressobj(31);pending=b'';count=0;read=0;decoded=0;seen=set();differences=[];licences=collections.Counter();classes=collections.Counter()
def record(line):
 global count
 r=json.loads(line);assert r['kind']=='recipe';key=identity(r);assert key not in seen;seen.add(key);count+=1;p=r['provenance'];d=r['data'];licences[p.get('license','unknown')]+=1
 classes['sourceDeclaredPublic' if p.get('visibility')=='public' else 'privateOrUnknown']+=1
 if d.get('ingredientExtractionComplete')is False:classes['incompleteOCR']+=1
 if (p.get('originSourceId')or p.get('sourceId'))=='recipecommons/openrecipe-spec':classes['schemaExample']+=1
 if not d.get('ingredients'):classes['missingIngredients']+=1
 if not d.get('directions'):classes['missingDirections']+=1
 if original.get(key)!=signature(r):differences.append({'origin':key[0],'recordId':key[1]})
with urllib.request.urlopen(urllib.request.Request(url,headers={'Accept-Encoding':'identity'}),timeout=40) as r:
 while True:
  part=r.read(65536)
  if not part:break
  read+=len(part);assert read<=32*1024*1024,'Compressed32MiBbound';h.update(part);new=dec.decompress(part);decoded+=len(new);assert decoded<=768*1024*1024,'Expanded768MiBbound';pending+=new
  while b'\n' in pending:
   line,pending=pending.split(b'\n',1)
   if line:record(line)
  assert len(pending)<=2*1024*1024,'Record2MiBbound'
 tail=dec.flush();pending+=tail
 if pending.strip():record(pending)
assert dec.eof and read==ref['bytes'] and h.hexdigest()==ref['sha256'];assert len(original)==25135 and count==25135 and set(original)==seen
proof={'schema':'offmenu-already-public-recipe-proof/1','manifest':{'url':URL,'bytes':len(mb),'sha256':hashlib.sha256(mb).hexdigest(),'releaseId':manifest['releaseId']},'publicRecipeDownload':{'url':url,'bytes':read,'sha256':h.hexdigest(),'gzipEOFValidated':True,'recordCount':count},'pinnedLocalInput':{'path':str(local),'bytes':local.stat().st_size,'sha256':hashlib.sha256(local.read_bytes()).hexdigest(),'records':len(original)},'identityIntersection':len(seen),'comparedFields':['original source identity','title','languages','original ingredient wording','directions','licence','attribution','sourceURL'],'comparedFieldDifferences':len(differences),'differenceExamples':differences[:5],'licenceDistribution':dict(licences),'classification':dict(classes),'uploads':'NO recipe/data payload to upload; UI code consumes existing exact public catalogue and detail files','cataloguePages':len(manifest['library']['catalogueFiles']),'detailFiles':len([x for x in manifest['files'] if x['key'].startswith('records/')])}
(ROOT/'.local/public-existing-data-proof.json').write_text(json.dumps(proof,ensure_ascii=False,indent=2)+'\n');(ROOT/'.local/public-manifest.json').write_bytes(mb);print(json.dumps(proof,ensure_ascii=False))
