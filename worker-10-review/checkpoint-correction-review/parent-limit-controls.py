import pathlib,json,hashlib,gzip,sqlite3,tempfile,sys,importlib.util
from unittest.mock import patch
r=pathlib.Path(__file__).parent;s=r/'parent-snapshot';sys.path.insert(0,str(s/'scripts'))
def module(name,path):
 spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
places=module('review_places',s/'scripts/align-places-common.py');preflight=module('review_preflight',s/'scripts/places-recovery-preflight.py')
def digest(b):return hashlib.sha256(b).hexdigest()
def fixture(root):
 source=root/'curated';sources=['overture-food-places','wikidata-food-businesses']
 for sourceId in sources:
  path=source/'records'/sourceId/'00.jsonl.gz';path.parent.mkdir(parents=True)
  rows=[]
  for n in range(1,4):
   row={'schemaVersion':'1.0','kind':'site' if sourceId==sources[0] else 'organization','id':sourceId+':review:'+str(n),'countries':['AU'],'provenance':{'sourceId':sourceId,'recordId':str(n),'url':'https://review.invalid/'+str(n),'license':'CC0 1.0','licenseUrl':'https://review.invalid/license','attribution':'Reviewer synthetic fixture','visibility':'public','releaseId':'review-only','sourceDate':'2026-10-14'},'data':{'name':'Reviewer '+sourceId+' '+str(n)}}
   rows.append(json.dumps(['review:'+sourceId+':'+str(n),[row]]))
  path.write_bytes(gzip.compress(('\n'.join(rows)+'\n').encode(),mtime=0))
 files=[{'key':str(p.relative_to(source)),'bytes':p.stat().st_size,'sha256':digest(p.read_bytes())} for p in sorted(source.rglob('*.gz'))]
 (source/'manifest.json').write_text(json.dumps({'releaseId':'review-only','files':files,'sources':{sid:{'releaseId':'review-only','records':3,'license':'CC0 1.0','attribution':'Reviewer synthetic fixture','rawSourcePayloadPublished':False} for sid in sources}}))
 return source

def tree(root):return {str(p.relative_to(root)):p.read_bytes() for p in root.rglob('*') if p.is_file()}
def footprint(root):
 return {str(p.relative_to(root)):{'dev':p.stat().st_dev,'ino':p.stat().st_ino,'mode':p.stat().st_mode,'size':p.stat().st_size,'mtimeNs':p.stat().st_mtime_ns,'sha256':digest(p.read_bytes())} for p in root.rglob('*') if p.is_file()}

results=[]
for packetSize,limit in [(1,1),(2,2)]:
 with tempfile.TemporaryDirectory(prefix='worker10-parent-limit-control-') as temp:
  root=pathlib.Path(temp);source=fixture(root);out=root/'resumed';original=places.Checkpoint.save
  def interrupt(c):
   original(c)
   if sum(c.value['input_counts'].values())==limit:raise RuntimeError('reviewer committed limit')
  with patch.object(places.Checkpoint,'save',interrupt):
   try:places.align(source,out,records_per_packet=packetSize,limit=limit)
   except RuntimeError:pass
  with sqlite3.connect(root/'resumed.checkpoint.sqlite') as db:state=json.loads(db.execute('SELECT payload FROM state').fetchone()[0])
  with patch.object(places.dt,'datetime') as clock:
   clock.now.return_value.isoformat.return_value=state['createdAt'];expected=places.align(source,root/'expected',records_per_packet=packetSize,limit=limit)
  actual=places.align(source,out,records_per_packet=packetSize,limit=limit,resume=True)
  different=[key for key in actual if actual.get(key)!=expected.get(key)]
  assert actual!=expected and 'sources' in different
  results.append({'parent':'e8c248c0448ca25f87cd6277efcd4876715585d2','packetSize':packetSize,'limit':limit,'manifestMismatchReproduced':True,'differentFields':different,'expectedSources':list(expected['sources']),'resumedSources':list(actual['sources'])})
(r/'parent-limit-controls.json').write_text(json.dumps(results,indent=2)+'\n');print(json.dumps(results,indent=2))
