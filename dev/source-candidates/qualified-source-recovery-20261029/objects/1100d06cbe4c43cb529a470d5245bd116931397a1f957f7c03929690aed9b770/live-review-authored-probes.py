import copy,json
from test_portfolio_owner02 import fixture,NOW
from offmenu.portfolio_owner02 import evaluate_binding
from offmenu.refresh.core import canonical,sha
results=[]
for name,actual,expected in [('bool-int',1,True),('int-bool',True,1),('false-zero',0,False)]:
 spec,evidence=fixture();doc=json.loads(next(iter(evidence.values())));doc['flag']=actual
 spec['fields']['flag']={'kind':'source','pointer':'/flag','expected':expected}
 raw=canonical(doc);spec['metadata'].update(sha256=sha(raw),bytes=len(raw));r=evaluate_binding(spec,{'fixture/receipt.json':raw},now=NOW)
 results.append({'case':name,'actualType':type(actual).__name__,'expectedType':type(expected).__name__,'status':r['status'],'diagnostics':r['diagnostics']})
spec,evidence=fixture();doc=json.loads(next(iter(evidence.values())));doc['release~2name']='synthetic-release';spec['fields']['releaseLabel']['pointer']='/release~2name'
raw=canonical(doc);spec['metadata'].update(sha256=sha(raw),bytes=len(raw));r=evaluate_binding(spec,{'fixture/receipt.json':raw},now=NOW)
results.append({'case':'invalid-pointer-escape','pointer':'/release~2name','status':r['status'],'diagnostics':r['diagnostics']})
print(json.dumps({'head':'eda87089602e6a0081b8d1714c5825095a8f97e9','authoredOnly':True,'cases':results,'realMetadataOrSourceBodyReads':0,'authorEdits':0}))
