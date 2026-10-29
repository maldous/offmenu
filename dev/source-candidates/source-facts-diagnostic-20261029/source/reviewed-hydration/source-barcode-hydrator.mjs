import {SOURCE_BARCODE_PUBLIC_BASE,validateSourceBarcodeSelection,validateSourceBarcodeReference,parseSourceBarcodeJSON} from './source-barcode-client.mjs';
const P='urn:offmenu:property:';
const need=(ok)=>{if(!ok)throw Error('SOURCE_DETAILS_UNAVAILABLE');};
const canonical=v=>Array.isArray(v)?'['+v.map(canonical).join(',')+']':v!==null&&typeof v==='object'?'{'+Object.keys(v).sort().map(k=>JSON.stringify(k)+':'+canonical(v[k])).join(',')+'}':JSON.stringify(v);
const same=(a,b)=>canonical(a)===canonical(b);
const hash=async bytes=>Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256',bytes)),b=>b.toString(16).padStart(2,'0')).join('');
export const HYDRATION_LIMITS=Object.freeze({compressedBytes:8*1024*1024,expandedBytes:32*1024*1024,packetBytes:2*1024*1024,packets:10000,rows:30000,timeoutMs:15000,displayCharacters:65536});
async function bounded(stream,cap,signal){
 need(stream?.getReader);const reader=stream.getReader(),parts=[];let size=0;
 const abort=()=>{void reader.cancel().catch(()=>{});};signal.addEventListener('abort',abort,{once:true});
 try{for(;;){need(!signal.aborted);const part=await reader.read();need(!signal.aborted);if(part.done)break;size+=part.value.byteLength;need(size<=cap);parts.push(part.value);}const bytes=new Uint8Array(size);let n=0;for(const p of parts){bytes.set(p,n);n+=p.byteLength;}return bytes;}
 finally{signal.removeEventListener('abort',abort);await reader.cancel().catch(()=>{});reader.releaseLock();}
}
// This is a public source projection, not a replacement validator for schema
// 89ff7014. Fields below follow retained align-bulk-food-common.py and the
// read-only common-corpus-locale.js reader. No inference or release stitching.
export async function projectOriginalPacket(graph,c,signal=new AbortController().signal){
 need(graph?.schemaVersion==='offmenu-common/1');const maps={};let count=0;
 for(const key of ['resources','assertions','relations','citations','translations']){
  need(Array.isArray(graph[key]));count+=graph[key].length;need(count<=HYDRATION_LIMITS.rows);maps[key]=new Map();
  for(const row of graph[key]){need(typeof row.id==='string'&&row.id&&!maps[key].has(row.id));maps[key].set(row.id,row);}
 }
 const cite=id=>{const row=maps.citations.get(id);need(row?.scope?.visibility==='public'&&row.sourceId===c.query.source&&row.revisionId===c.query.release&&typeof row.license==='string'&&row.license.length>0&&typeof row.attribution==='string'&&row.attribution.length>0);return row;};
 const cited=ids=>{need(Array.isArray(ids)&&ids.length>0);return ids.map(cite);};
 const publicRow=row=>{need(row?.scope?.visibility==='public');cited(row.citationIds);need(row.status!=='superseded');return row;};
 const resource=publicRow(maps.resources.get(c.reference.sourceResourceId));
 const assertion=publicRow(maps.assertions.get(c.reference.identifierAssertion.id));
 need(assertion.subjectId===resource.id&&assertion.propertyId===P+'sourceIdentifier'&&['source-asserted','candidate','editor-authored','reviewed','verified'].includes(assertion.status));
 need(await hash(new TextEncoder().encode(canonical(assertion)))===c.reference.identifierAssertion.canonicalSha256);
 const f=assertion.value?.fields;need(assertion.value?.kind==='structure'&&f?.system?.kind==='identifier'&&f.system.value===c.query.namespace&&f.value?.kind==='identifier'&&f.value.value===c.query.lexical);
 let budget=HYDRATION_LIMITS.displayCharacters;const retainedCitations=new Map();
 function evidence(ids){for(const row of cited(ids))retainedCitations.set(row.id,{id:row.id,sourceId:row.sourceId,revisionId:row.revisionId,originalRecordId:row.originalRecordId??null,license:row.license,attribution:row.attribution,originalUrl:row.originalUrl??null,rightsEvidenceUrl:row.rightsEvidenceUrl??null});}
 function text(s){need(typeof s==='string');budget-=s.length;need(budget>=0&&!signal.aborted);return s;}
 async function value(v,depth=0){
  need(depth<=30&&v&&typeof v==='object'&&!signal.aborted);
  switch(v.kind){
   case 'text':need(v.status!=='superseded');evidence(v.citationIds);need(typeof v.value==='string'&&await hash(new TextEncoder().encode(v.value))===v.sourceTextSha256);return text(v.value);
   case 'null':need(v.value===null);return 'Unknown';
   case 'number':need(typeof v.value==='number'&&Number.isFinite(v.value));return String(v.value);
   case 'boolean':need(typeof v.value==='boolean');return String(v.value);
   case 'identifier':case 'uri':case 'expression':case 'date':case 'datetime':return text(v.value);
   case 'reference':return text(v.id)+' (source reference; unresolved)';
   case 'list':need(Array.isArray(v.items));return (await Promise.all(v.items.map(i=>value(i,depth+1)))).join(' · ');
   case 'structure':need(v.fields&&typeof v.fields==='object'&&!Array.isArray(v.fields));return (await Promise.all(Object.entries(v.fields).map(async([k,item])=>text(k)+': '+await value(item,depth+1)))).join(' · ');
   case 'quantity':{
    need(v.value===null||typeof v.value==='number'&&Number.isFinite(v.value));let out=(v.value===null?'Unknown':String(v.value))+' '+text(v.sourceUnit||v.unitId||'Unknown unit');
    if(v.basis)out+=' per '+await value(v.basis,depth+1);
    if(v.qualifiers)out+='; qualifiers: '+text(JSON.stringify(v.qualifiers));
    if(v.sourceValue!==undefined)out+='; original value: '+text(JSON.stringify(v.sourceValue));
    if(v.sourceNotation)out+='; notation: '+await value(v.sourceNotation,depth+1);return out;
   }
   default:throw Error('SOURCE_DETAILS_UNAVAILABLE');
  }
 }
 evidence(resource.citationIds);evidence(assertion.citationIds);
 const names=[];for(const name of resource.names||[])names.push(await value(name));
 const facts=[];
 for(const row of graph.assertions.filter(r=>r.subjectId===resource.id)){
  publicRow(row);evidence(row.citationIds);
  if(!['sourceFields','nutrientObservation','sourceNutrientMetadata'].some(k=>row.propertyId===P+k))continue;
  if(row.propertyId===P+'sourceFields'){
   need(row.value?.kind==='structure'&&row.value.fields);
   for(const [key,v] of Object.entries(row.value.fields))facts.push({label:text(key),text:await value(v),assertionId:row.id,status:row.status,sourcePath:row.sourcePath??null,citationIds:[...row.citationIds]});
  }else facts.push({label:row.sourcePath||row.propertyId.slice(P.length),text:await value(row.value),assertionId:row.id,status:row.status,sourcePath:row.sourcePath??null,citationIds:[...row.citationIds]});
 }
 const unresolved=[];
 for(const row of graph.relations.filter(r=>r.subjectId===resource.id)){publicRow(row);evidence(row.citationIds);unresolved.push({predicateId:row.predicateId,objectId:row.objectId,status:row.status});}
 need(!signal.aborted);
 return {name:names[0]??null,names,resourceType:resource.type,identityStatus:resource.identityStatus,identifierStatus:assertion.status,facts,citations:[...retainedCitations.values()],unresolvedRelations:unresolved,
 canonicalIdentityAsserted:false,automaticPlanningEligible:false,nutritionAggregationEligible:false};
}
export function createSourceBarcodeHydrator({selection,fetchImpl=globalThis.fetch}={}){
 let fixed=null;try{fixed=validateSourceBarcodeSelection(selection);}catch{}let closed=false;const controllers=new Set();
 async function hydrate(match,{signal}={}){
  const c=structuredClone(match?.sourceBarcodeCandidate);let controller,timer,onAbort;
  try{
   need(!closed&&controllers.size===0&&fixed&&c&&c.manifestSha256===fixed.manifestSha256&&c.indexReleaseId===fixed.indexReleaseId&&same(c.publicBase,SOURCE_BARCODE_PUBLIC_BASE));
   need(c.canonicalIdentityAsserted===false&&c.automaticPlanningEligible===false&&c.nutritionAggregationEligible===false);
   need(c.query?.namespace==='barcode'&&typeof c.query.lexical==='string'&&c.query.lexical.length>0&&fixed.scopes.some(s=>s.source===c.query.source&&s.release===c.query.release));
   validateSourceBarcodeReference(c.reference,SOURCE_BARCODE_PUBLIC_BASE);
   const a=c.reference.asset;need(a.bytes<=HYDRATION_LIMITS.compressedBytes&&a.packetCount<=HYDRATION_LIMITS.packets&&a.path.endsWith('.jsonl.gz'));
   const url=new URL(a.path,SOURCE_BARCODE_PUBLIC_BASE.origin);need(url.origin===SOURCE_BARCODE_PUBLIC_BASE.origin&&url.pathname===a.path&&!url.search&&!url.hash);
   controller=new AbortController();controllers.add(controller);onAbort=()=>controller.abort();signal?.addEventListener('abort',onAbort,{once:true});need(!signal?.aborted);timer=setTimeout(onAbort,HYDRATION_LIMITS.timeoutMs);
   const response=await fetchImpl(url.href,{method:'GET',credentials:'omit',cache:'no-store',redirect:'error',signal:controller.signal});
   need(response.status===200&&!response.redirected&&(!response.url||response.url===url.href));
   // Content-Encoding transformation would destroy the declared compressed-byte
   // binding. Never hash decompressed transport bytes as the original asset.
   need(!response.headers.get('content-encoding')||response.headers.get('content-encoding')==='identity');
   if(response.headers.has('content-length'))need(Number(response.headers.get('content-length'))===a.bytes);
   const bytes=await bounded(response.body,a.bytes,controller.signal);need(bytes.byteLength===a.bytes&&await hash(bytes)===a.sha256&&!controller.signal.aborted);
   const expanded=await bounded(new Blob([bytes]).stream().pipeThrough(new DecompressionStream('gzip')),HYDRATION_LIMITS.expandedBytes,controller.signal);
   const decoded=new TextDecoder('utf-8',{fatal:true}).decode(expanded);need(decoded.endsWith('\n'));
   const lines=decoded.slice(0,-1).split('\n');need(lines.length===a.packetCount&&lines.length<=HYDRATION_LIMITS.packets);
   const line=lines[a.packetOrdinal];need(new TextEncoder().encode(line).length<=HYDRATION_LIMITS.packetBytes);
   const facts=await projectOriginalPacket(parseSourceBarcodeJSON(line),c,controller.signal);need(!closed&&!controller.signal.aborted);
   return {...match,name:facts.name,sourceBarcodeCandidate:{...c,hydrationState:'verified',factsState:'verified-original-public-packet',facts}};
  }catch{return {...match,sourceBarcodeCandidate:{...c,hydrationState:'unavailable',factsState:'technical-details-unavailable'}};}
  finally{clearTimeout(timer);if(onAbort)signal?.removeEventListener('abort',onAbort);if(controller)controllers.delete(controller);}
 }
 return Object.freeze({hydrate,destroy(){closed=true;for(const c of controllers)c.abort();controllers.clear();}});
}
export function hydratedSourceBarcodeReadout(match){
 const c=match?.sourceBarcodeCandidate,f=c?.facts;if(c?.hydrationState!=='verified'||!f)return null;
 return [{label:f.name||'Verified source identifier · name unknown',text:c.query.lexical},
 {label:'Source scope / assertion',text:c.query.source+' · '+c.query.release+' · '+f.identifierStatus+' · '+f.identityStatus},
 {label:'Original resource type',text:f.resourceType},...f.facts.map(r=>({label:r.label,text:r.text+' ['+r.status+']'})),
 ...f.citations.map(r=>({label:'Source citation / licence',text:r.sourceId+' · '+r.revisionId+' · '+r.license+' · '+r.attribution+' · '+(r.originalRecordId||'record unknown')+' · '+(r.originalUrl||'source URL unknown')})),
 ...f.unresolvedRelations.map(r=>({label:'Related source facts unresolved',text:r.predicateId+' → '+r.objectId+'; this referenced packet has not been verified. Nutrition/ingredients remain unknown where not supplied above.'})),
 {label:'Unspecified source facts',text:'Any name, ingredient, quantity or nutrient fact not supplied above remains unknown in this verified packet. Index null references do not establish absence. Related packets remain unhydrated.'},
 {label:'Evidence boundary',text:'Exact original public asset SHA/bytes, packet ordinal, resource and identifier assertion verified. Fields retain source names, units, zero, unknown and basis. No canonical identity, planning or nutrition aggregation admission.'}];
}
