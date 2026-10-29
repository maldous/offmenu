from pathlib import Path
import json,hashlib
r=Path(__file__).parent
public=(r/'input/demo-full-scanner.js').read_text();private=(r/'input/shelf-scanner.js').read_text();bundle=(r/'source-barcode.iife.js').read_text();selection=public.split('var _OffMenuSourceBarcodeSelection = ',1)[1].split(';',1)[0]
changes=[]
def add(route,seam,old,new):
 s=public if route=='demo-full-scanner.js' else private
 assert s.count(old)==1,(route,seam,s.count(old))
 changes.append(dict(route=route,seam=seam,old=old,new=new,preimageSha256=hashlib.sha256(old.encode()).hexdigest(),replacementSha256=hashlib.sha256(new.encode()).hexdigest(),expectedMatches=1))
namespace=public[:public.index('\n\nvar _OffMenuSourceBarcodeSelection')]
add('demo-full-scanner.js','replace bounded additive namespace only',namespace,bundle.rstrip())
add('demo-full-scanner.js','pending readout is progress rather than completed outcome','function readoutItems() {','function readoutItems() {\n  if(current?.status==="pending")return _OffMenuSourceBarcode.inventoryReadout(_OffMenuGuestFoundation.foundationReadout,null,current,tab);')
# Remove the obsolete direct-public-asset hydration button. Facts are now
# supplied by the owned API; unavailable facts remain explicit, not re-fetched.
start=public.index('if(selected2?.kind===\"source-barcode-candidate\"&&selected2.sourceBarcodeCandidate.hydrationState!==\"verified\")rows.push(')
end=public.index('return rows;}',start)
add('demo-full-scanner.js','remove obsolete browser graph hydration action',public[start:end],'')
add('demo-full-scanner.js','dedupe same original decoder code before generation changes','  processed.add(eventId);','  if(decoderCapture&&current?.raw===raw&&current?.namespace===sourceNamespace)return;\n  processed.add(eventId);')
add('demo-full-scanner.js','source facts summary before legacy detail gate','function renderConsumerSummary() {\n  const host = $("consumer-summary");\n  host.replaceChildren();','function renderConsumerSummary() {\n  const host = $("consumer-summary");\n  host.replaceChildren();\n  if(current?.status===\"pending\"){host.append(el2(\"p\",\"Original code retained · checking owned source facts (up to40seconds)\",\"label\"));return;}\n  if(selected2?.kind==="source-barcode-candidate"){for(const row of _OffMenuSourceBarcode.inventoryReadout(_OffMenuGuestFoundation.foundationReadout,selected2,current,"overview").slice(0,8))host.append(el2("p",row.label+": "+row.text,"label"));return;}')
add('demo-full-scanner.js','classification unknown does not hide known source name','const categoryText = category?.status === "qualified"','const categoryText = latest?.status === "pending" ? "Lookup in progress" : selected2?.kind === "source-barcode-candidate" ? "Unknown source category" : category?.status === "qualified"')
add('demo-full-scanner.js','ingredient unknown independent of source match','const ingredientText = ingredient?.status === "qualified"','const ingredientText = latest?.status === "pending" ? "Lookup in progress" : selected2?.kind === "source-barcode-candidate" ? "Unknown source ingredient mapping" : ingredient?.status === "qualified"')
add('demo-full-scanner.js','preserve original source pack unknown or value','const packageText = projectedField("packageQuantity")','const packageText = selected2?.kind === "source-barcode-candidate" ? _OffMenuSourceBarcode.sourceFactField(selected2,"pack") || "Unknown" : projectedField("packageQuantity")')
add('demo-full-scanner.js','bounded pending progress','latest.status === "pending" ? "Code read \\xB7 checking OffMenu inventory"','latest.status === "pending" ? "Original code retained · checking owned source facts (up to40seconds)"')
# Existing foundation final override must use original foundation counts and
# expose additional facts failures without overwriting source-facts status.
a=public.index('  if (latest?.foundationLookup && selected2?.kind !== "source-barcode-candidate")');b=public.index('\n',a)
add('demo-full-scanner.js','final status retains truthful source and foundation boundaries',public[a:b],'  if(latest?.foundationLookup&&selected2?.kind!=="source-barcode-candidate")message(_OffMenuSourceBarcode.foundationStatusText(latest));')
add('shelf-scanner.js','inject shared bounded facts namespace without replacing composed scanner','var yl=',bundle+'\nvar _OffMenuSourceBarcodeSelection = '+selection+';\nvar yl=')
old='var Vn=Xh(),cc=e=>Vn.moreIdentity(e);'
new='var _OffMenuPrivateFoundation=Xh(),_OffMenuPrivateFactsInventory=_OffMenuSourceBarcode.createSourceBarcodeInventory({foundationInventory:{lookupIdentifiers:(...args)=>_OffMenuPrivateFoundation(...args),mergeIdentifierPages:(a,b)=>lc(a,b),destroy(){}},selection:_OffMenuSourceBarcodeSelection,fetchImpl:(...args)=>fetch(...args)}),Vn=Object.assign((...args)=>_OffMenuPrivateFactsInventory.lookupIdentifiers(...args),{moreIdentity:entry=>_OffMenuPrivateFoundation.moreIdentity(entry.foundationResult||entry)}),cc=e=>Vn.moreIdentity(e);'
add('shelf-scanner.js','wrap actual foundation function with shared owned facts consumer',old,new)
add('shelf-scanner.js','route exact readout and summary through verified source facts','function vo(e,t,r="overview"){return e?.kind==="source-identity"?Ja(e,t,r):[...mo(e,t,r),...Za(t)]}','function vo(e,t,r="overview"){return _OffMenuSourceBarcode.inventoryReadout((m,entry,tab)=>m?.kind==="source-identity"?Ja(m,entry,tab):[...mo(m,entry,tab),...Za(entry)],e,t,r)}')
add('shelf-scanner.js','keep sole known foundation or source selection','He=h.status==="source-match"?h.matches[0]:null','He=_OffMenuSourceBarcode.automaticSourceSelection(h)')
add('shelf-scanner.js','preserve source facts across original foundation paging','Object.assign(e,lc(e,i))','Object.assign(e,_OffMenuPrivateFactsInventory.mergeIdentifierPages(e,i))')
add('shelf-scanner.js','dedupe same original decoder code before generation changes','Rd.add(i),jd(),En=null','if(o&&Ue?.raw===e&&Ue?.namespace===n)return;Rd.add(i),jd(),En=null')
add('shelf-scanner.js','source category unknown independent of known product','i=He?.kind==="source-identity"?"Unknown":','i=e?.status==="pending"?"Lookup in progress":He?.kind==="source-identity"||He?.kind==="source-barcode-candidate"?"Unknown source category":')
add('shelf-scanner.js','source ingredient mapping unknown independent of known product','n=He?.kind==="source-identity"?"Unknown":','n=e?.status==="pending"?"Lookup in progress":He?.kind==="source-identity"||He?.kind==="source-barcode-candidate"?"Unknown source ingredient mapping":')
add('shelf-scanner.js','preserve source pack unknown or value','a=ka("packageQuantity")?.state==="present"','a=He?.kind==="source-barcode-candidate"?_OffMenuSourceBarcode.sourceFactField(He,"pack")||"Unknown":ka("packageQuantity")?.state==="present"')
add('shelf-scanner.js','source facts status precedes legacy status','Vt(e?e.status===','Vt(He?.kind==="source-barcode-candidate"?(He.sourceBarcodeCandidate.hydrationState==="verified"?"Verified owned source facts · source-scoped identity":He.sourceBarcodeCandidate.hydrationState==="unavailable"?"Original code retained · source facts technically unavailable":"Original code retained · source candidate details unknown"):e?e.status===')
add('shelf-scanner.js','bounded pending progress','e.status==="pending"?"Code read \\xB7 checking available product records"','e.status==="pending"?"Original code retained · checking owned source facts (up to40seconds)"')
old='e?.foundationLookup&&Vt(e.status==="scoped-miss"?"Barcode retained · no qualified details in the selected source indexes. Other sources may differ.":e.status==="unavailable"?"Code read \\xB7 selected foundation data unavailable; no global absence established":e.matches.length+" source foundation observation(s) \\xB7 full product not established")'
add('shelf-scanner.js','final status never overwrites verified source facts',old,'e?.foundationLookup&&He?.kind!=="source-barcode-candidate"&&Vt(_OffMenuSourceBarcode.foundationStatusText(e))')
for route,s in [('demo-full-scanner.js',public),('shelf-scanner.js',private)]:
 for c in changes:
  if c['route']==route:
   assert s.count(c['old'])==1;(s:=s.replace(c['old'],c['new']))
 (r/('candidate-'+route)).write_text(s)
packet={'schemaVersion':'offmenu-scanner208-owned-facts-function-handoff/1','baselinePublicSha256':hashlib.sha256(public.encode()).hexdigest(),'baselinePrivateSha256':hashlib.sha256(private.encode()).hexdigest(),'userFixtureBytes':5976,'userFixtureSha256':'604b9d1e98f43eb9fdc22d624d9bbede8385b85cbdb7929ae4ee3927aa3b3388','changes':changes,'authOrBackendChanges':False,'wholeScannerBuild':False}
(r/'FUNCTION-LOCAL-HANDOFF.json').write_text(json.dumps(packet,indent=2)+'\n');print('Exact208 single-match seams:',len(changes))
