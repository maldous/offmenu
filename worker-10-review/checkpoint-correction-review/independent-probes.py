import pathlib,json,hashlib,gzip,sqlite3,tempfile,sys,importlib.util
from unittest.mock import patch
r=pathlib.Path(__file__).parent;s=r/'snapshot';sys.path.insert(0,str(s/'scripts'))
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
for packetSize,limit,group in [(1,1,1),(1,2,1),(2,2,1),(2,2,3),(3,3,1),(2,4,1),(1,5,3),(3,6,3)]:
 with tempfile.TemporaryDirectory(prefix='worker10-reached-limit-') as temp:
  root=pathlib.Path(temp);source=fixture(root);out=root/'resumed';original=places.Checkpoint.save;hit=False
  def interrupt(c):
   global hit
   original(c)
   if not hit and sum(c.value['input_counts'].values())==limit:hit=True;raise RuntimeError('reviewer committed limit')
  with patch.object(places.Checkpoint,'save',interrupt):
   try:places.align(source,out,records_per_packet=packetSize,packets_per_file=group,limit=limit)
   except RuntimeError as e:assert str(e)=='reviewer committed limit'
  assert hit
  with sqlite3.connect(root/'resumed.checkpoint.sqlite') as db:state=json.loads(db.execute('SELECT payload FROM state').fetchone()[0])
  assert sum(state['input_counts'].values())==limit
  before=footprint(root);metadata=preflight.inventory(root/'resumed.partial',0,hash_limit=0);assert metadata['checkpointStatus']=='matching-output-metadata';assert footprint(root)==before
  expected=root/'uninterrupted'
  with patch.object(places.dt,'datetime') as clock:
   clock.now.return_value.isoformat.return_value=state['createdAt'];expectedManifest=places.align(source,expected,records_per_packet=packetSize,packets_per_file=group,limit=limit)
  actualManifest=places.align(source,out,records_per_packet=packetSize,packets_per_file=group,limit=limit,resume=True)
  actual=tree(out);reference=tree(expected);assert actual==reference and actualManifest==expectedManifest
  results.append({'kind':'reached-limit','recordsPerPacket':packetSize,'limit':limit,'packetsPerFile':group,'inputRecordsPerSource':3,'cursor':state['cursor'],'committedRows':sum(state['input_counts'].values()),'byteIdentical':True,'manifestSources':list(actualManifest['sources']),'metadataReadOnly':True,'files':[{'key':key,'actualSha256':digest(raw),'expectedSha256':digest(reference[key]),'bytes':len(raw)} for key,raw in sorted(actual.items())]})
for kind in ['actual-writer','absent','legacy-only','foreign','unsupported','invalid-db','malformed-json','missing-state','missing-row','encoded-path']:
 with tempfile.TemporaryDirectory(prefix='worker10-checkpoint-metadata-') as temp:
  root=pathlib.Path(temp);output=root/('out ? 餡' if kind=='encoded-path' else 'out');partial=output.with_name(output.name+'.partial');partial.mkdir();(partial/'packets').mkdir();path=output.with_name(output.name+'.checkpoint.sqlite')
  if kind in ['actual-writer','encoded-path']:
   (partial/'packets').rmdir();partial.rmdir();c=places.Checkpoint(output,partial,{'output':str(output.resolve()),'createdAt':'synthetic'},resume=False);c.close();partial.mkdir();(partial/'packets').mkdir()
  elif kind not in ['absent','legacy-only']:
   if kind=='invalid-db':path.write_bytes(b'not SQLite')
   else:
    with sqlite3.connect(path) as db:
     if kind=='missing-state':db.execute('CREATE TABLE other(value TEXT)')
     else:
      db.execute('CREATE TABLE state(id INTEGER PRIMARY KEY,payload TEXT)')
      if kind!='missing-row':
       payload='bad JSON' if kind=='malformed-json' else json.dumps({'version':2 if kind=='unsupported' else 1,'pins':{'output':str(root/'foreign') if kind=='foreign' else str(output.resolve())}})
       db.execute('INSERT INTO state VALUES(1,?)',(payload,))
  if kind=='legacy-only':(partial/'checkpoint.json').write_text('{}')
  before=footprint(root);observed=preflight.inventory(partial,0,hash_limit=0);after=footprint(root);assert before==after
  expected='matching-output-metadata' if kind in ['actual-writer','encoded-path'] else 'absent' if kind in ['absent','legacy-only'] else 'foreign-or-unsupported-metadata' if kind in ['foreign','unsupported','missing-row'] else 'unreadable-metadata'
  assert observed['checkpointStatus']==expected,(kind,observed)
  results.append({'kind':'metadata','case':kind,'expectedStatus':expected,'actual':observed,'completeFileFootprintEqual':True,'noJournalOrWALCreated':set(before)==set(after)})
(r/'independent-results.json').write_text(json.dumps({'candidate':'dfd7448788aa199eff7bde20ffdbbf1161973427','status':'passed','cases':len(results),'results':results},indent=2)+'\n');print('Independent cases passed:',len(results),'limit cases 8; metadata cases 10; all byte/footprint comparisons exact')
