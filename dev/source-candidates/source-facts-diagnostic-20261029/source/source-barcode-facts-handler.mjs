import {createSourceBarcodeHandler as createCandidateHandler,ORIGIN,PUBLIC_BASE} from './source-barcode-handler.mjs';
import {projectOriginalPacket} from './reviewed-hydration/source-barcode-hydrator.mjs';
import {validateSourceBarcodeReference,parseSourceBarcodeJSON} from './reviewed-hydration/source-barcode-client.mjs';
export {PUBLIC_BASE,ORIGIN,PREFIX,INDEX_RELEASE,RESOURCE_BOUNDS,keySha} from './source-barcode-handler.mjs';
export const FACTS_BOUNDS=Object.freeze({compressedBytes:8*1024*1024,expandedBytes:32*1024*1024,
 packetBytes:2*1024*1024,packets:10000,responseBytes:2*1024*1024,timeoutMs:120000,decodeWindow:65536});
const need=ok=>{if(!ok)throw Error('facts-unavailable');};
const encoder=new TextEncoder();
const sha=async bytes=>Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256',bytes)),b=>b.toString(16).padStart(2,'0')).join('');
function lifetime(request) {
 const controller=new AbortController();const abort=()=>controller.abort();
 request.signal.addEventListener('abort',abort,{once:true});if(request.signal.aborted)abort();
 const timer=setTimeout(abort,FACTS_BOUNDS.timeoutMs);
 async function run(call){need(!controller.signal.aborted);let listener;
  try{return await Promise.race([Promise.resolve().then(call),new Promise((_,reject)=>{
   listener=()=>reject(Error('facts-unavailable'));controller.signal.addEventListener('abort',listener,{once:true});
   if(controller.signal.aborted)listener();})]);}
  finally{if(listener)controller.signal.removeEventListener('abort',listener);}
 }
 return {signal:controller.signal,run,close(){controller.abort();clearTimeout(timer);request.signal.removeEventListener('abort',abort);}};
}
async function compressedBytes(stream,expected,life) {
 need(stream?.getReader);const reader=stream.getReader(),parts=[];let size=0,done=false;
 try {
  for(;;){const p=await life.run(()=>reader.read());if(p.done){done=true;break;}
   need(p.value instanceof Uint8Array);size+=p.value.byteLength;need(size<=expected);parts.push(p.value);}
  need(size===expected);const out=new Uint8Array(size);let offset=0;for(const p of parts){out.set(p,offset);offset+=p.byteLength;}return out;
 }finally{if(!done)void reader.cancel().catch(()=>{});reader.releaseLock();}
}
// Validate the complete JSONL/gzip boundary while retaining only the exact selected
// ordinal. No decoded-asset string, split-lines array or other packets' graphs.
export async function selectOriginalPacket(stream,asset,life) {
 need(stream?.getReader);const reader=stream.getReader(),decoder=new TextDecoder('utf-8',{fatal:true});
 let expanded=0,ordinal=0,selectedBytes=0,lastNewline=false,done=false;const selected=[];
 function consume(text){
  if(!text.length)return;lastNewline=text.endsWith('\n');let start=0;
  for(;;){const newline=text.indexOf('\n',start),end=newline<0?text.length:newline;
   if(ordinal===asset.packetOrdinal){const piece=text.slice(start,end);selectedBytes+=encoder.encode(piece).length;
    need(selectedBytes<=FACTS_BOUNDS.packetBytes);selected.push(piece);}
   if(newline<0)break;ordinal++;need(ordinal<=asset.packetCount&&ordinal<=FACTS_BOUNDS.packets);start=newline+1;
   if(start===text.length)break;
  }
 }
 try {
  for(;;){const p=await life.run(()=>reader.read());if(p.done){done=true;break;}
   need(p.value instanceof Uint8Array);expanded+=p.value.byteLength;need(expanded<=FACTS_BOUNDS.expandedBytes);
   for(let offset=0;offset<p.value.length;offset+=FACTS_BOUNDS.decodeWindow)
    consume(decoder.decode(p.value.subarray(offset,offset+FACTS_BOUNDS.decodeWindow),{stream:true}));
  }
  consume(decoder.decode());need(lastNewline&&ordinal===asset.packetCount&&selectedBytes>0&&!life.signal.aborted);
  return parseSourceBarcodeJSON(selected.join(''));
 }finally{if(!done)void reader.cancel().catch(()=>{});reader.releaseLock();}
}
async function hydrateOriginal(candidateLookup,request,fetchImpl,diagnostic) {
 diagnostic.stage='asset-reference';
 const reference=validateSourceBarcodeReference(candidateLookup.candidates[0],PUBLIC_BASE),a=reference.asset;
 need(a.bytes<=FACTS_BOUNDS.compressedBytes&&a.packetCount<=FACTS_BOUNDS.packets&&a.path.endsWith('.jsonl.gz'));
 const url=new URL(a.path,ORIGIN);need(url.origin===ORIGIN&&url.pathname===a.path&&!url.search&&!url.hash&&!url.username&&!url.password);
 const life=lifetime(request);let response;
 try {
  diagnostic.stage='asset-fetch';response=await life.run(()=>fetchImpl(url.href,{method:'GET',redirect:'manual',credentials:'omit',cache:'no-store',
   headers:{Accept:'application/gzip','Accept-Encoding':'identity'},signal:life.signal}));
  diagnostic.stage='asset-response';need(response.status===200&&!response.redirected&&(!response.url||response.url===url.href));
  need(!response.headers.get('content-encoding')||response.headers.get('content-encoding')==='identity');
  const declared=response.headers.get('content-length');if(declared!==null)need(/^\d+$/.test(declared)&&Number(declared)===a.bytes);
  diagnostic.stage='asset-bytes';const bytes=await compressedBytes(response.body,a.bytes,life);
  diagnostic.stage='asset-sha';need(await life.run(()=>sha(bytes))===a.sha256);
  let offset=0;const input=new ReadableStream({pull(c){if(offset===bytes.length){c.close();return;}
   const end=Math.min(bytes.length,offset+65536);c.enqueue(bytes.subarray(offset,end));offset=end;}});
  diagnostic.stage='packet-stream';const graph=await selectOriginalPacket(input.pipeThrough(new DecompressionStream('gzip')),a,life);
  const context={query:candidateLookup.query,reference};
  diagnostic.stage='original-projection';const projection=await life.run(()=>projectOriginalPacket(graph,context,life.signal));need(!life.signal.aborted);
  return projection;
 }catch(error){diagnostic.aborted=life.signal.aborted;throw error;}finally{
  life.close();if(response?.body&&!response.body.locked)void response.body.cancel().catch(()=>{});
 }
}
function factsEnvelope(candidateLookup,factsStatus,originalFacts=null) {
 return {schemaVersion:'offmenu-source-barcode-facts/1',candidateLookup,factsStatus,originalFacts,
  canonicalIdentityAsserted:false,automaticPlanningEligible:false,nutritionAggregationEligible:false};
}
function respond(envelope,base,status=base.status) {
 const body=JSON.stringify(envelope);need(encoder.encode(body).length<=FACTS_BOUNDS.responseBytes);
 const headers=new Headers(base.headers);headers.set('Content-Type','application/json; charset=utf-8');headers.set('Cache-Control','no-store');
 return new Response(body,{status,headers});
}
// Same production export/inputs. Only explicit include=facts takes the new path.
export function createSourceBarcodeHandler({selection,fetchImpl=(...args)=>globalThis.fetch(...args),onDiagnostic}={}) {
 const candidates=createCandidateHandler({selection,fetchImpl,onDiagnostic});
 return async function handle(request) {
  const url=new URL(request.url);
  if(url.pathname!=='/api/corpus/source-barcode'||!url.searchParams.has('include'))return candidates(request);
  if(url.searchParams.getAll('include').length!==1||url.searchParams.get('include')!=='facts')return candidates(request);
  url.searchParams.delete('include');
  // Do not copy incoming auth/cookies/private headers to either transport.
  const candidateRequest=new Request(url.href,{method:request.method,signal:request.signal});
  const base=await candidates(candidateRequest),candidateLookup=await base.json();
  if(base.status!==200)return respond(factsEnvelope(candidateLookup,'index-unavailable'),base);
  if(candidateLookup.candidateTotal===0)return respond(factsEnvelope(candidateLookup,'source-key-not-found'),base);
  if(candidateLookup.candidateTotal>1)return respond(factsEnvelope(candidateLookup,'selection-required'),base);
  const diagnostic={stage:'candidate-page',aborted:false};
  try {
   need(candidateLookup.candidateTotal===1&&candidateLookup.candidates.length===1);
   const originalFacts=await hydrateOriginal(candidateLookup,request,fetchImpl,diagnostic);
   diagnostic.stage='facts-response';return respond(factsEnvelope(candidateLookup,'verified-original-public-packet',originalFacts),base);
  }catch(error){
   if(typeof onDiagnostic==='function'){
    const types=new Set(['Error','TypeError','RangeError','AbortError','DataError','OperationError']);
    try{onDiagnostic(Object.freeze({schema:'offmenu-source-barcode-facts-internal-diagnostic/1',stage:diagnostic.stage,
     code:diagnostic.aborted?'abort-or-deadline':'facts-stage-failed',errorType:types.has(error?.name)?error.name:'UnknownError'}));}catch{}
   }
   return respond(factsEnvelope(candidateLookup,'facts-unavailable'),base,503);
  }
 };
}
