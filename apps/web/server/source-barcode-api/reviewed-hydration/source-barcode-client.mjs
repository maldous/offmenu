import {SOURCE_BARCODE_SELECTION} from './source-barcode-selection.mjs';

export const SOURCE_BARCODE_SCHEMA='offmenu-source-barcode-candidates/1';
export const SOURCE_BARCODE_INDEX_RELEASE='source-barcode-index-v1-20261029';
export const SOURCE_BARCODE_PINS=Object.freeze({
 sourceManifestSha256:'8cd8abbf28f8fac11ccb73f336a91c7a5d90fbaff6ec1c864ec7b492f13da58e',
 structuralManifestSha256:'83773291ac70931a110f60e872ae47a2bd470b5f397c709195dcf016c0bf0694',
 consumerIndexSha256:'5e6d5c14a26515632a56aac2ff128a12baaa6ec7d030703c368cc8c297a4c1ad',
 locatorManifestSha256:'3520dff24e7b96635fd3d8f8cfa60664d03d5bd65709b547059cee10b306e1a9',
 locatorIndexSha256:'1691828696477efe932d6b3bfc1e20cbdc99ddf047da3e695067f40478e8c2cd',
 publicBaseManifestSha256:'66b2ee6e016838453c59c1d1f6f05941d14c84a8084361ef099463a3a6471c05',
 qualificationReceiptSha256:'9e60de075a9bf049e0348c666e4cc2cbe9edb07c6771bcab95649038dafd1226',
 schemaSha256:'89ff701460e0c9c6e27c5d5ece7bd6868f26f55fc2aedd1d85c87b4408cf1f6c',
 contractSha256:'b4fa5afb2f8cc77326299b55ccd75b93f121e807317fdc1f9953709e98faa0aa'
});
const PREFIX='/common-data/releases/common-corpus-expanded-20261014/';
export const SOURCE_BARCODE_PUBLIC_BASE=Object.freeze({origin:'https://offmenu-corpus.netlify.app',releaseId:'common-corpus-expanded-20261014',manifestPath:PREFIX+'manifest.json',manifestSha256:SOURCE_BARCODE_PINS.publicBaseManifestSha256,sourcePackageManifestPath:PREFIX+'bulk-food/source-package-manifest.json',sourcePackageManifestSha256:SOURCE_BARCODE_PINS.sourceManifestSha256,assetPrefix:PREFIX+'bulk-food/'});
const SHARED=['schemaVersion','query','status','candidateTotal','countKnown','complete','returnedCount','truncated','candidates','nextCursor','referenceCoverageComplete','canonicalIdentityAsserted','automaticPlanningEligible','nutritionAggregationEligible'];
const SUCCESS=[...SHARED,'manifestSha256','indexReleaseId','sourcePins','publicBase'];
const object=x=>x!==null&&typeof x==='object'&&!Array.isArray(x);
const exact=(x,keys)=>object(x)&&Object.keys(x).length===keys.length&&keys.every(k=>Object.hasOwn(x,k));
const nonempty=x=>typeof x==='string'&&x.length>0;
const integer=x=>Number.isSafeInteger(x)&&x>=0;
const sha=x=>typeof x==='string'&&/^[a-f0-9]{64}$/.test(x);
const stable=x=>Array.isArray(x)?'['+x.map(stable).join(',')+']':object(x)?'{'+Object.keys(x).sort().map(k=>JSON.stringify(k)+':'+stable(x[k])).join(',')+'}':JSON.stringify(x);
const same=(a,b)=>stable(a)===stable(b);
const need=(ok,reason='SOURCE_BARCODE_RESPONSE_MISMATCH')=>{if(!ok)throw Error(reason);};
const clone=x=>structuredClone(x);

// JSON.parse alone silently accepts duplicate keys and overflowing numbers.
export function parseSourceBarcodeJSON(text){
 need(typeof text==='string'&&new TextEncoder().encode(text).length<=2*1024*1024,'SOURCE_BARCODE_RESPONSE_BOUND');
 const value=JSON.parse(text);let p=0;
 const space=()=>{while(/[\x20\t\n\r]/.test(text[p]||'x'))p++;};
 function string(){const start=p++;while(p<text.length){const c=text[p++];if(c==='\\')p++;else if(c==='"')return JSON.parse(text.slice(start,p));}throw Error('SOURCE_BARCODE_JSON');}
 function walk(depth=0){need(depth<=40,'SOURCE_BARCODE_JSON_DEPTH');space();
  if(text[p]==='{'){p++;space();const keys=new Set();if(text[p]==='}'){p++;return;}for(;;){space();const key=string();need(!keys.has(key),'SOURCE_BARCODE_DUPLICATE_JSON_KEY');keys.add(key);space();p++;walk(depth+1);space();if(text[p++]==='}')break;}}
  else if(text[p]==='['){p++;space();if(text[p]===']'){p++;return;}for(;;){walk(depth+1);space();if(text[p++]===']')break;}}
  else if(text[p]==='"')string();else{const start=p;while(p<text.length&&!/[\x20\t\n\r,}\]]/.test(text[p]))p++;const n=JSON.parse(text.slice(start,p));need(typeof n!=='number'||Number.isFinite(n),'SOURCE_BARCODE_NONFINITE_JSON');}
 }
 walk();space();need(p===text.length);return value;
}
async function boundedResponseText(response){
 const bound=2*1024*1024;
 if(response.headers?.get('content-length'))need(Number(response.headers.get('content-length'))<=bound,'SOURCE_BARCODE_RESPONSE_BOUND');
 if(!response.body?.getReader){const text=await response.text();need(new TextEncoder().encode(text).length<=bound,'SOURCE_BARCODE_RESPONSE_BOUND');return text;}
 const reader=response.body.getReader(),decoder=new TextDecoder('utf-8',{fatal:true});let bytes=0,text='';
 try{for(;;){const part=await reader.read();if(part.done)break;bytes+=part.value.byteLength;need(bytes<=bound,'SOURCE_BARCODE_RESPONSE_BOUND');text+=decoder.decode(part.value,{stream:true});}return text+decoder.decode();}
 catch(error){await reader.cancel().catch(()=>{});throw error;}finally{reader.releaseLock();}
}
function queryFor(scope,value,namespace){
 const query={source:scope.source,release:scope.release,namespace,lexical:value};
 need(nonempty(query.source)&&nonempty(query.release)&&namespace==='barcode'&&nonempty(value),'SOURCE_BARCODE_QUERY_UNAVAILABLE');
 need(new TextEncoder().encode(JSON.stringify([query.source,query.release,namespace,value])).length<=16384,'SOURCE_BARCODE_QUERY_BOUND');return query;
}
export function validateSourceBarcodeSelection(value){
 need(exact(value,['manifestSha256','indexReleaseId','scopes'])&&sha(value.manifestSha256)&&value.indexReleaseId===SOURCE_BARCODE_INDEX_RELEASE&&Array.isArray(value.scopes)&&value.scopes.length>0&&value.scopes.length<=8,'SOURCE_BARCODE_NOT_CONFIGURED');
 for(const scope of value.scopes)need(exact(scope,['source','release'])&&nonempty(scope.source)&&nonempty(scope.release),'SOURCE_BARCODE_NOT_CONFIGURED');
 need(new Set(value.scopes.map(stable)).size===value.scopes.length,'SOURCE_BARCODE_NOT_CONFIGURED');return clone(value);
}
function cursorBody(cursor,query,limit,selection){
 need(nonempty(cursor)&&cursor.length<=32768&&/^[A-Za-z0-9_-]+$/.test(cursor),'SOURCE_BARCODE_CURSOR_MISMATCH');
 const bytes=Uint8Array.from(atob(cursor.replaceAll('-','+').replaceAll('_','/')+'='.repeat((4-cursor.length%4)%4)),c=>c.charCodeAt(0));
 const c=parseSourceBarcodeJSON(new TextDecoder('utf-8',{fatal:true}).decode(bytes));
 need(exact(c,['manifestSha256','query','limit','offset'])&&c.manifestSha256===selection.manifestSha256&&same(c.query,query)&&c.limit===limit&&integer(c.offset)&&c.offset<=20,'SOURCE_BARCODE_CURSOR_MISMATCH');return c;
}
function reference(ref,base){
 need(exact(ref,['sourceResourceId','asset','identifierAssertion','sourceAssertionStatus','sourceAssertionStatusState','citationRefs','ingredientRefs','nutrientRefs'])&&nonempty(ref.sourceResourceId));
 const a=ref.asset;need(exact(a,['path','sha256','bytes','packetOrdinal','packetCount','packetCanonicalSha256','packetDigestState']));
 need(nonempty(a.path)&&a.path.startsWith(base.assetPrefix)&&!a.path.split('/').slice(1).some(p=>!p||p==='.'||p==='..'));
 const url=new URL(a.path,base.origin);need(url.origin===base.origin&&url.pathname===a.path&&!url.search&&!url.hash);
 need(sha(a.sha256)&&integer(a.bytes)&&a.bytes>0&&integer(a.packetOrdinal)&&integer(a.packetCount)&&a.packetOrdinal<a.packetCount);
 need(a.packetCanonicalSha256===null&&a.packetDigestState==='not-retained-in-selected-product-locator-index');
 const i=ref.identifierAssertion;need(exact(i,['id','canonicalSha256','matchingAssertionCount','referencesTruncated'])&&nonempty(i.id)&&sha(i.canonicalSha256)&&integer(i.matchingAssertionCount)&&i.matchingAssertionCount>=1&&i.referencesTruncated===(i.matchingAssertionCount>1));
 need(ref.sourceAssertionStatus===null&&ref.sourceAssertionStatusState==='resolve-original-public-assertion'&&ref.citationRefs===null&&ref.ingredientRefs===null&&ref.nutrientRefs===null);return clone(ref);
}
export function validateSourceBarcodeEnvelope(value,query,selection,{limit=20,cursor=null}={}){
 need(value?.schemaVersion===SOURCE_BARCODE_SCHEMA&&same(value.query,query));
 need(value.canonicalIdentityAsserted===false&&value.automaticPlanningEligible===false&&value.nutritionAggregationEligible===false);
 if(value.status==='index-unavailable'){
  need(exact(value,SHARED)&&value.candidateTotal===null&&value.countKnown===false&&value.complete===false&&value.returnedCount===0&&value.truncated===null&&Array.isArray(value.candidates)&&value.candidates.length===0&&value.nextCursor===null&&value.referenceCoverageComplete===false);return clone(value);
 }
 need(exact(value,SUCCESS)&&value.manifestSha256===selection.manifestSha256&&value.indexReleaseId===selection.indexReleaseId&&same(value.sourcePins,SOURCE_BARCODE_PINS)&&same(value.publicBase,SOURCE_BARCODE_PUBLIC_BASE));
 need(value.countKnown===true&&value.complete===true&&integer(value.candidateTotal)&&Array.isArray(value.candidates)&&value.candidates.length<=limit&&value.returnedCount===value.candidates.length);
 const offset=cursor===null?0:cursorBody(cursor,query,limit,selection).offset,retained=Math.min(value.candidateTotal,20);
 need(offset<=retained&&value.returnedCount===Math.min(limit,retained-offset)&&value.truncated===(value.candidateTotal>value.returnedCount)&&value.referenceCoverageComplete===(retained===value.candidateTotal));
 need(value.status===(value.candidateTotal===0?'source-key-not-found':value.candidateTotal>1?'ambiguous-source-key':'source-scoped-candidates'));
 const ids=new Set();for(const ref of value.candidates){reference(ref,value.publicBase);need(!ids.has(ref.sourceResourceId));ids.add(ref.sourceResourceId);}
 if(offset+value.returnedCount<retained){need(value.nextCursor!==null);need(cursorBody(value.nextCursor,query,limit,selection).offset===offset+value.returnedCount);}else need(value.nextCursor===null);
 return clone(value);
}
function unavailable(query,reason){return {schemaVersion:SOURCE_BARCODE_SCHEMA,query:clone(query),status:'index-unavailable',candidateTotal:null,countKnown:false,complete:false,returnedCount:0,truncated:null,candidates:[],nextCursor:null,referenceCoverageComplete:false,canonicalIdentityAsserted:false,automaticPlanningEligible:false,nutritionAggregationEligible:false,clientError:reason};}
export function sourceBarcodeMatch(ref,lane){
 const id=stable(['source-barcode-candidate',lane.manifestSha256,lane.query,ref.sourceResourceId,ref.asset.sha256,ref.asset.packetOrdinal,ref.identifierAssertion.canonicalSha256]);
 return {kind:'source-barcode-candidate',id,name:null,brand:null,provenance:{sourceId:lane.query.source,releaseId:lane.query.release},sourceBarcodeCandidate:{query:clone(lane.query),manifestSha256:lane.manifestSha256,indexReleaseId:lane.indexReleaseId,publicBase:clone(lane.publicBase),reference:clone(ref),hydrationState:'not-loaded',factsState:'details-pending',canonicalIdentityAsserted:false,automaticPlanningEligible:false,nutritionAggregationEligible:false}};
}
function result(raw,generation,symbology,lanes,selection){
 return {enabled:true,original:raw,namespace:'barcode',generation,symbology,manifestSha256:selection.manifestSha256,indexReleaseId:selection.indexReleaseId,lanes,matches:lanes.flatMap(l=>l.candidates.map(r=>sourceBarcodeMatch(r,l))),hasMore:lanes.some(l=>l.nextCursor!==null),complete:lanes.every(l=>l.complete===true),ambiguous:lanes.some(l=>l.candidateTotal>1),referenceCoverageComplete:lanes.every(l=>l.referenceCoverageComplete===true)};
}
export function createSourceBarcodeLookup({selection=SOURCE_BARCODE_SELECTION,fetchImpl=globalThis.fetch,limit=20}={}){
 let fixed;try{fixed=validateSourceBarcodeSelection(selection);need(Number.isSafeInteger(limit)&&limit>=1&&limit<=20);}catch{fixed=null;}
 let closed=false;const controllers=new Set();
 async function page(query,limit,cursor){
  if(closed)return unavailable(query,'SOURCE_BARCODE_CLOSED');
  if(cursor!==null)cursorBody(cursor,query,limit,fixed);
  const url=new URL('/api/corpus/source-barcode','https://offmenu.invalid');for(const[k,v]of Object.entries({source:query.source,release:query.release,namespace:query.namespace,value:query.lexical,limit}))url.searchParams.set(k,String(v));if(cursor!==null)url.searchParams.set('cursor',cursor);
  const controller=new AbortController();controllers.add(controller);const timer=setTimeout(()=>controller.abort(),12000);
  try{
   const response=await fetchImpl(url.pathname+url.search,{method:'GET',credentials:'omit',cache:'no-store',redirect:'error',mode:'same-origin',headers:{Accept:'application/json'},signal:controller.signal});
   if(closed||controller.signal.aborted)return unavailable(query,'SOURCE_BARCODE_CLOSED');
   if(response.status!==200)return unavailable(query,'SOURCE_BARCODE_TRANSPORT_UNAVAILABLE');
   const body=await boundedResponseText(response);if(closed||controller.signal.aborted)return unavailable(query,'SOURCE_BARCODE_CLOSED');const checked=validateSourceBarcodeEnvelope(parseSourceBarcodeJSON(body),query,fixed,{limit,cursor});return {...checked,requestCursor:cursor,limit};
  }catch{return unavailable(query,'SOURCE_BARCODE_RESPONSE_UNAVAILABLE');}finally{clearTimeout(timer);controllers.delete(controller);}
 }
 async function lookup(raw,generation,symbology=null,namespace='barcode'){
  if(!fixed)return {enabled:selection!==null&&selection!==undefined,matches:[],lanes:[],hasMore:false,complete:false,configurationError:selection!==null&&selection!==undefined,reason:'SOURCE_BARCODE_NOT_CONFIGURED'};
  let queries;try{need(Number.isSafeInteger(generation),'SOURCE_BARCODE_QUERY_UNAVAILABLE');queries=fixed.scopes.map(s=>queryFor(s,raw,namespace));}catch{return result(raw,generation,symbology,fixed.scopes.map(s=>unavailable({source:s.source,release:s.release,namespace,lexical:raw},'SOURCE_BARCODE_QUERY_UNAVAILABLE')),fixed);}
  return result(raw,generation,symbology,await Promise.all(queries.map(q=>page(q,limit,null))),fixed);
 }
 async function more(previous){
  need(fixed&&previous?.enabled&&previous.manifestSha256===fixed.manifestSha256&&previous.indexReleaseId===fixed.indexReleaseId&&previous.lanes.length===fixed.scopes.length,'SOURCE_BARCODE_PAGE_CONTEXT_CHANGED');
  const lanes=await Promise.all(previous.lanes.map(async(old,index)=>{
   need(same(old.query,queryFor(fixed.scopes[index],previous.original,previous.namespace)),'SOURCE_BARCODE_PAGE_CONTEXT_CHANGED');
   if(!old.nextCursor)return old;
   const next=await page(old.query,old.limit,old.nextCursor);if(next.status==='index-unavailable')return {...old,pageError:next.clientError||'SOURCE_BARCODE_PAGE_UNAVAILABLE'};
   need(next.candidateTotal===old.candidateTotal&&same(next.sourcePins,old.sourcePins)&&same(next.publicBase,old.publicBase),'SOURCE_BARCODE_PAGE_CONTEXT_CHANGED');
   const seen=new Set(old.candidates.map(r=>r.sourceResourceId));for(const r of next.candidates){need(!seen.has(r.sourceResourceId),'SOURCE_BARCODE_DUPLICATE_PAGE_RESOURCE');seen.add(r.sourceResourceId);}
   return {...next,candidates:[...old.candidates,...next.candidates],returnedCount:old.candidates.length+next.candidates.length};
  }));return result(previous.original,previous.generation,previous.symbology,lanes,fixed);
 }
 return Object.assign(lookup,{more,destroy(){closed=true;for(const controller of controllers)controller.abort();controllers.clear();}});
}
export function sourceBarcodeReadout(match,entry,tab='overview'){
 const c=match?.sourceBarcodeCandidate;if(!c)return [];
 const lane=entry?.sourceBarcodeResult?.lanes.find(l=>same(l.query,c.query));
 const rows=[{label:'Identifier match · details pending',text:c.query.lexical},{label:'Source scope',text:c.query.source+' · '+c.query.release+' · '+c.query.namespace},{label:'Original resource reference',text:c.reference.sourceResourceId},{label:'Facts not loaded',text:'This is a source-scoped identifier candidate. Original name, type, ingredient, nutrition, citations, status and licence require verified original-packet hydration. Unknown, not absent or zero. No product/food identity or planning admission is asserted.'}];
 if(lane)rows.push({label:'Candidate coverage',text:String(lane.candidateTotal)+' eligible source resource(s); '+lane.candidates.length+' reference(s) loaded'+(lane.referenceCoverageComplete?'':'; reference inventory is capped or incomplete')+(lane.nextCursor?'; another stored page is available':'')+(lane.pageError?'; additional page unavailable':'')});
 if(tab==='source')rows.push({label:'Exact index/asset/assertion binding',text:JSON.stringify(c)},{label:'Source evidence state',text:'citationRefs, ingredientRefs and nutrientRefs are not materialized in this index. Original packet digest is not retained; verify asset bytes/SHA, ordinal, resource and assertion digest before factual display.'});
 return rows;
}

export const validateSourceBarcodeReference=(ref,base=SOURCE_BARCODE_PUBLIC_BASE)=>reference(ref,base);
