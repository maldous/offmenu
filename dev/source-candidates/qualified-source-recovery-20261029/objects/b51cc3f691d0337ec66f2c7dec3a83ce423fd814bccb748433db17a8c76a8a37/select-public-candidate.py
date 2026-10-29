from pathlib import Path
import sys,json,hashlib,urllib.request,importlib.util
r=Path(__file__).parent
spec=importlib.util.spec_from_file_location('protocol',r.parent/'source-barcode-candidate/protocol/source_barcode_protocol.py');p=importlib.util.module_from_spec(spec);spec.loader.exec_module(p)
origin=p.BASE_ORIGIN;prefix=p.PREFIX;expected='d22d0c464d32ea8df1b81da1f74701db5b563cd3c5b69c1d4e0f9b116709c839'
root=r/'metadata';root.mkdir(exist_ok=True)
def read(path,cap):
 assert path.startswith(prefix) and '..' not in path and '?' not in path
 req=urllib.request.Request(origin+path,headers={'Accept-Encoding':'identity'})
 with urllib.request.urlopen(req,timeout=20) as res:
  assert res.status==200 and res.url==origin+path
  data=res.read(cap+1);assert len(data)<=cap;return data
manifest=read(prefix+'manifest.json',2*1024*1024);assert hashlib.sha256(manifest).hexdigest()==expected;(root/'manifest.json').write_bytes(manifest)
m=p.checked_manifest(root,expected)
query={'source':'off','release':'2026-10-12','namespace':'barcode','lexical':'4088700055496'}
h=p.key_sha(query);assert h[:2]=='85'
d=m['shards']['85'];assert d['path']=='shards/85.json.gz' and d['publicPath']==prefix+d['path'] and 0<d['bytes']<=p.MAX_COMPRESSED
b=read(d['publicPath'],d['bytes']);(root/'shards').mkdir(exist_ok=True);(root/d['path']).write_bytes(b)
s=p.read_shard(root,m,'85');entries=[e for e in s['entries'] if e['keySha256']==h and e['key']==query];assert len(entries)==1;entry=entries[0];assert entry['candidateTotal']==1 and len(entry['candidates'])==1
out={'selection':{'manifestSha256':expected,'indexReleaseId':m['indexReleaseId'],'scopes':[{'source':query['source'],'release':query['release']}]},'lane':{'query':query,'manifestSha256':expected,'indexReleaseId':m['indexReleaseId'],'publicBase':m['publicBase']},'reference':entry['candidates'][0]}
(r/'selected-reference.json').write_text(json.dumps(out)+'\n')
receipt={'manifestSha256':expected,'manifestVerified':True,'singleShard':'85','shardSha256':d['sha256'],'shardBytes':len(b),'exactQueryTupleMatched':True,'candidateTotal':1,'networkRequests':2,'scope':'one manifest and its selected shard for the first real hydration boundary; not six-query/corpus proof rerun'};(r/'selection-receipt.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(receipt))
