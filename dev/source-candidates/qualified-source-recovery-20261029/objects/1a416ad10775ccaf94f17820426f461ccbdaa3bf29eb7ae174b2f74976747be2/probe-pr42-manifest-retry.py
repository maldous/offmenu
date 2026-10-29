import sys,json,copy,hashlib
from pathlib import Path
sys.dont_write_bytecode=True
sys.path[:0]=['/tmp/offmenu-worker00-pr42-20261018/tests','/tmp/offmenu-worker00-pr42-20261018']
from test_product_origin_stage import ProductOriginStageTest
out=Path(__file__).resolve().parent;results=[]
for field,value in [('accepted',True),('status','accepted-source-scope'),('rawStorage',{'visibility':'public','publishable':True})]:
 t=ProductOriginStageTest();t.setUp()
 try:
  r=t.run_stage();assert r['manifest']['accepted'] is False
  p=t.f.root/'enriched/manifest.json';m=json.loads(p.read_text());candidateHash=hashlib.sha256(r['candidate'].read_bytes()).hexdigest();contract=copy.deepcopy(m['originStageContract']);hashes=copy.deepcopy(m['outputHashes']);m[field]=value;p.write_text(json.dumps(m)+'\n')
  again=t.run_stage();assert again['manifest'][field]==value
  assert again['manifest']['originStageContract']==contract and again['manifest']['outputHashes']==hashes and hashlib.sha256(r['candidate'].read_bytes()).hexdigest()==candidateHash
  results.append({'mutatedField':field,'returnedValue':again['manifest'][field],'qualified':again['qualification']['qualified'],'manifestMutationRejected':False,'candidateBytesUnchanged':True})
 finally:t.doCleanups()
p=out/'manifest-retry-reproduction.json';p.write_text(json.dumps({'status':'FINDING_REPRODUCED','source':'PR42 unresolved thread PRRT_kwDOVGpSC86tnNrX, comment4305676855','head':'dacbef5481d95f89bb1cd18ec4dfefafde43f645','scope':'Synthetic authored OFF fixture only; no real inputs, no candidate implementation changes','cases':results},indent=2)+'\n');print(p.read_text())
