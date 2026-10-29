import {SOURCE_PINS} from './protocol-pins.mjs';
import {strictJSON} from './strict-json.mjs';
import {scanShard} from './stream-shard.mjs';
export const INDEX_RELEASE = 'source-barcode-index-v1-20261029';
export const ORIGIN = 'https://offmenu-corpus.netlify.app';
export const PREFIX = '/common-data/derived-releases/' + INDEX_RELEASE + '/';
const BASE = '/common-data/releases/common-corpus-expanded-20261014/';
export const PUBLIC_BASE = Object.freeze({origin:ORIGIN,releaseId:'common-corpus-expanded-20261014',
  manifestPath:BASE+'manifest.json',manifestSha256:SOURCE_PINS.publicBaseManifestSha256,
  sourcePackageManifestPath:BASE+'bulk-food/source-package-manifest.json',
  sourcePackageManifestSha256:SOURCE_PINS.sourceManifestSha256,assetPrefix:BASE+'bulk-food/'});
export const RESOURCE_BOUNDS = Object.freeze({manifestBytes:2*1024*1024,compressedBytes:8*1024*1024,
  expandedBytes:32*1024*1024,entries:65536,jsonNodes:200000,responseBytes:256*1024,cursorBytes:32768,deadlineMs:30000});
const SCHEMA='offmenu-source-barcode-candidates/1', ENC=new TextEncoder();
// Exact security headers from the supplied v201 landing-only seam. No CORS or auth policy changes.
const HEADERS={'X-Content-Type-Options':'nosniff','Referrer-Policy':'no-referrer',
 'Permissions-Policy':'camera=(self), microphone=()',
 'Content-Security-Policy':"default-src 'self'; script-src 'self' 'wasm-unsafe-eval'; style-src 'self' 'unsafe-inline'; img-src 'self' blob: data:; media-src 'self' blob:; connect-src 'self' https://offmenu-corpus.netlify.app; worker-src 'self'; object-src 'none'; base-uri 'self'; frame-ancestors 'none'",
 'Cache-Control':'no-store','Content-Type':'application/json; charset=utf-8'};
const need=(ok,code='integrity')=>{if(!ok)throw Error(code);};
const object=x=>x!==null && typeof x==='object' && !Array.isArray(x);
const integer=(x,min=0,max=Number.MAX_SAFE_INTEGER)=>Number.isSafeInteger(x)&&x>=min&&x<=max;
const sha=x=>typeof x==='string'&&/^[a-f0-9]{64}$/.test(x);
const text=(x,max=4096)=>typeof x==='string'&&x.length>0&&ENC.encode(x).length<=max;
const same=(a,b)=>canonical(a)===canonical(b);
const fields=(x,keys)=>object(x)&&same(Object.keys(x).sort(),keys.slice().sort());
export function canonical(x) {
  if (Array.isArray(x)) return '['+x.map(canonical).join(',')+']';
  if (object(x)) return '{'+Object.keys(x).sort().map(k=>JSON.stringify(k)+':'+canonical(x[k])).join(',')+'}';
  return JSON.stringify(x);
}
async function digest(bytes) {
  return Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256',bytes)),b=>b.toString(16).padStart(2,'0')).join('');
}
function validateQuery(q) {
  need(fields(q,['source','release','namespace','lexical']),'query');
  need(Object.values(q).every(v=>text(v,16384))&&q.namespace==='barcode','query');
  need(ENC.encode(canonical([q.source,q.release,q.namespace,q.lexical])).length<=16384,'query');
  // Preserve all original lexical characters; no digit-length/checksum/food gate or trim.
  for(const v of Object.values(q)) for(const cp of v) need(!(cp.codePointAt(0)>=0xd800&&cp.codePointAt(0)<=0xdfff),'query');
}
export async function keySha(q) { validateQuery(q);return digest(ENC.encode(canonical([q.source,q.release,q.namespace,q.lexical]))); }
function unavailable(query) {
  return {schemaVersion:SCHEMA,query,status:'index-unavailable',candidateTotal:null,countKnown:false,complete:false,
    returnedCount:0,truncated:null,candidates:[],nextCursor:null,referenceCoverageComplete:false,
    canonicalIdentityAsserted:false,automaticPlanningEligible:false,nutritionAggregationEligible:false};
}
function response(value,status=200,extra={}) {
  const body=JSON.stringify(value); need(ENC.encode(body).length<=RESOURCE_BOUNDS.responseBytes,'response-bound');
  return new Response(body,{status,headers:{...HEADERS,...extra}});
}
function selectionCopy(selection) {
  // Trusted factory input only. Request parameters can never select a URL, pin or public base.
  need(object(selection)&&selection.manifestUrl===ORIGIN+PREFIX+'manifest.json'&&sha(selection.manifestSha256)&&
    selection.indexReleaseId===INDEX_RELEASE&&same(selection.sourcePins,SOURCE_PINS)&&same(selection.publicBase,PUBLIC_BASE),'selection');
  return {manifestUrl:selection.manifestUrl,manifestSha256:selection.manifestSha256,indexReleaseId:INDEX_RELEASE};
}
function validateManifest(m) {
  need(object(m)&&m.schemaVersion==='offmenu-source-barcode-index/1'&&m.indexReleaseId===INDEX_RELEASE&&m.complete===true&&
    same(m.sourcePins,SOURCE_PINS)&&same(m.publicBase,PUBLIC_BASE)&&m.candidateReferenceCap===20&&
    m.canonicalIdentityAsserted===false&&m.automaticPlanningEligible===false&&m.nutritionAggregationEligible===false,'manifest');
  need(same(m.keyHash,{algorithm:'SHA256',input:'UTF-8 canonical JSON array [source,release,namespace,lexical]',
    canonicalJSON:'sorted object keys; no whitespace; ensure_ascii=false; finite JSON',normalization:'none',shardPrefixHexCharacters:2}),'key-hash');
  const prefixes=Array.from({length:256},(_,i)=>i.toString(16).padStart(2,'0'));
  need(object(m.shards)&&same(Object.keys(m.shards).sort(),prefixes),'inventory');
  for(const prefix of prefixes) {
    const d=m.shards[prefix];
    need(object(d)&&d.path==='shards/'+prefix+'.json.gz'&&d.publicPath===PREFIX+d.path&&sha(d.sha256)&&
      integer(d.bytes,1,64*1024*1024)&&integer(d.uncompressedBytes,1,256*1024*1024)&&integer(d.indexedKeys),'descriptor');
  }
}
function validateRef(ref) {
  need(fields(ref,['sourceResourceId','asset','identifierAssertion','sourceAssertionStatus','sourceAssertionStatusState',
    'citationRefs','ingredientRefs','nutrientRefs'])&&text(ref.sourceResourceId),'reference');
  const a=ref.asset;
  need(fields(a,['path','sha256','bytes','packetOrdinal','packetCount','packetCanonicalSha256','packetDigestState']),'asset');
  need(text(a.path,2048)&&a.path.startsWith(PUBLIC_BASE.assetPrefix)&&!/[\\%?#\x00-\x20]/.test(a.path)&&
    a.path.split('/').slice(1).every(x=>x&&x!=='.'&&x!=='..')&&new URL(a.path,ORIGIN).pathname===a.path,'asset-path');
  need(sha(a.sha256)&&integer(a.bytes,1)&&integer(a.packetCount,1)&&integer(a.packetOrdinal,0,a.packetCount-1)&&
    a.packetCanonicalSha256===null&&a.packetDigestState==='not-retained-in-selected-product-locator-index','asset-locator');
  const assertion=ref.identifierAssertion;
  need(fields(assertion,['id','canonicalSha256','matchingAssertionCount','referencesTruncated'])&&text(assertion.id)&&
    sha(assertion.canonicalSha256)&&integer(assertion.matchingAssertionCount,1)&&
    assertion.referencesTruncated===(assertion.matchingAssertionCount>1),'assertion');
  need(ref.sourceAssertionStatus===null&&ref.sourceAssertionStatusState==='resolve-original-public-assertion'&&
    ['citationRefs','ingredientRefs','nutrientRefs'].every(k=>ref[k]===null),'evidence');
}
function cursorDecode(cursor,selection,query,limit) {
  if(cursor===null)return 0;
  need(text(cursor,RESOURCE_BOUNDS.cursorBytes)&&/^[A-Za-z0-9_-]+$/.test(cursor),'cursor');
  const bytes=Uint8Array.from(atob(cursor.replace(/-/g,'+').replace(/_/g,'/')+'='.repeat((4-cursor.length%4)%4)),c=>c.charCodeAt(0));
  const c=strictJSON(new TextDecoder('utf-8',{fatal:true}).decode(bytes),()=>{},100);
  need(fields(c,['manifestSha256','query','limit','offset'])&&c.manifestSha256===selection.manifestSha256&&
    same(c.query,query)&&c.limit===limit&&integer(c.offset,0,20),'cursor-binding');
  // Accept the producer's one canonical representation, never malformed aliases.
  need(cursorEncode(c)===cursor,'cursor-canonical');return c.offset;
}
function cursorEncode(c) {return btoa(Array.from(ENC.encode(canonical(c)),b=>String.fromCharCode(b)).join('')).replace(/=/g,'').replace(/\+/g,'-').replace(/\//g,'_');}
function lifetime(request) {
  const controller=new AbortController(),deadline=Date.now()+RESOURCE_BOUNDS.deadlineMs;
  const abort=()=>controller.abort();request.signal.addEventListener('abort',abort,{once:true});
  if(request.signal.aborted)abort();const timer=setTimeout(abort,RESOURCE_BOUNDS.deadlineMs);
  const check=()=>need(!controller.signal.aborted&&Date.now()<=deadline,'deadline');
  async function run(call) {
    check();let listener;
    try {return await Promise.race([Promise.resolve().then(call),new Promise((_,reject)=>{
      listener=()=>reject(Error('cancelled-or-deadline'));controller.signal.addEventListener('abort',listener,{once:true});
      if(controller.signal.aborted)listener();
    })]);}finally{if(listener)controller.signal.removeEventListener('abort',listener);}
  }
  return {stage:'request',signal:controller.signal,check,run,close:()=>{controller.abort();clearTimeout(timer);request.signal.removeEventListener('abort',abort);}};
}
async function boundedBytes(stream,max,life,exact=null) {
  need(stream&&typeof stream.getReader==='function','stream');const reader=stream.getReader();const chunks=[];let size=0,done=false;
  try {
    while(true) {
      const part=await life.run(()=>reader.read());if(part.done){done=true;break;}
      need(part.value instanceof Uint8Array,'stream-chunk');size+=part.value.byteLength;need(size<=max,'byte-bound');
      chunks.push(part.value);
    }
    need(exact===null||size===exact,'byte-count');const joined=new Uint8Array(size);let offset=0;
    for(const c of chunks){joined.set(c,offset);offset+=c.byteLength;}return joined;
  } finally {
    if(!done)void reader.cancel().catch(()=>{});reader.releaseLock();
  }
}
async function fetchBytes(url,max,life,fetchImpl,exact=null) {
  const res=await life.run(()=>fetchImpl(url,{method:'GET',redirect:'manual',credentials:'omit',cache:'no-store',
    headers:{Accept:'application/json, application/gzip','Accept-Encoding':'identity'},signal:life.signal}));
  let consumed=false;
  try {
    need(res&&res.status===200&&!res.redirected&&(!res.url||res.url===url),'http');
    // Auto-decompressed Content-Encoding responses cannot prove compressed file bytes.
    need(!res.headers.get('content-encoding')||res.headers.get('content-encoding')==='identity','http-encoding');
    const len=res.headers.get('content-length');if(len!==null)need(/^\d+$/.test(len)&&Number(len)<=max&&
      (exact===null||Number(len)===exact),'http-size');
    const result=await boundedBytes(res.body,max,life,exact);consumed=true;return result;
  } finally {if(!consumed&&res?.body&&!res.body.locked)void res.body.cancel().catch(()=>{});}
}
async function lookup(query,limit,cursor,selection,fetchImpl,life) {
  life.stage='cursor';const offset=cursorDecode(cursor,selection,query,limit);
  life.stage='manifest-fetch';const manifestBytes=await fetchBytes(selection.manifestUrl,RESOURCE_BOUNDS.manifestBytes,life,fetchImpl);
  life.stage='manifest-sha';need(await life.run(()=>digest(manifestBytes))===selection.manifestSha256,'manifest-sha');
  const decode=bytes=>strictJSON(new TextDecoder('utf-8',{fatal:true}).decode(bytes),life.check,RESOURCE_BOUNDS.jsonNodes);
  life.stage='manifest-parse';const m=decode(manifestBytes);validateManifest(m);
  life.stage='key-hash';const hash=await life.run(()=>keySha(query)),prefix=hash.slice(0,2),d=m.shards[prefix];
  life.stage='resource-bounds';need(d.bytes<=RESOURCE_BOUNDS.compressedBytes&&d.uncompressedBytes<=RESOURCE_BOUNDS.expandedBytes&&
    d.indexedKeys<=RESOURCE_BOUNDS.entries,'worker-resource-bound');
  life.stage='shard-fetch';const bytes=await fetchBytes(ORIGIN+d.publicPath,d.bytes,life,fetchImpl,d.bytes);
  life.stage='shard-sha';need(await life.run(()=>digest(bytes))===d.sha256,'shard-sha');
  life.stage='shard-stream';let compressedOffset=0;
  const input=new ReadableStream({pull(controller){
    if(compressedOffset===bytes.length){controller.close();return;}
    const end=Math.min(bytes.length,compressedOffset+65536);
    controller.enqueue(bytes.subarray(compressedOffset,end));compressedOffset=end;
  }});
  let previous='',entry=null;
  await scanShard(input.pipeThrough(new DecompressionStream('gzip')),{
    expectedBytes:d.uncompressedBytes,expectedPrefix:prefix,expectedEntries:d.indexedKeys,
    maxEntries:RESOURCE_BOUNDS.entries,life,onEntry:async e=>{
    life.check();validateQuery(e.key);const h=await life.run(()=>keySha(e.key));
    need(h===e.keySha256&&h.startsWith(prefix)&&h>previous,'key-binding');previous=h;
    need(integer(e.candidateTotal,1)&&Array.isArray(e.candidates)&&e.candidates.length===Math.min(e.candidateTotal,20)&&
      e.returnedCount===e.candidates.length&&e.truncated===(e.candidateTotal>e.candidates.length),'candidate-count');
    const seen=new Set();for(const ref of e.candidates){validateRef(ref);need(!seen.has(ref.sourceResourceId),'duplicate-resource');seen.add(ref.sourceResourceId);}
    if(h===hash){need(same(e.key,query)&&entry===null,'exact-tuple');entry=e;}
  }});
  life.stage='response';const refs=entry?.candidates||[],total=entry?.candidateTotal||0;need(offset<=refs.length,'cursor-offset');
  const page=refs.slice(offset,offset+limit),next=offset+page.length;
  return {...unavailable(query),status:total===0?'source-key-not-found':total>1?'ambiguous-source-key':'source-scoped-candidates',
    candidateTotal:total,countKnown:true,complete:true,returnedCount:page.length,truncated:total>page.length,candidates:page,
    nextCursor:next<refs.length?cursorEncode({manifestSha256:selection.manifestSha256,query,limit,offset:next}):null,
    referenceCoverageComplete:refs.length===total,manifestSha256:selection.manifestSha256,indexReleaseId:INDEX_RELEASE,
    sourcePins:m.sourcePins,publicBase:m.publicBase};
}
export function createSourceBarcodeHandler({selection,fetchImpl=(...args)=>globalThis.fetch(...args),onDiagnostic}={}) {
  let pinned=null;try{pinned=selectionCopy(selection);}catch{/* absent/unverified pin stays unavailable */}
  return async function handle(request) {
    const url=new URL(request.url);if(url.pathname!=='/api/corpus/source-barcode')return null;
    if(request.method!=='GET')return response(unavailable(null),405,{Allow:'GET'});
    let query=null,limit,cursor;
    try {
      need(ENC.encode(url.search).length<=65536,'query-size');
      const allowed=['source','release','namespace','value','limit','cursor'];
      for(const k of url.searchParams.keys())need(allowed.includes(k)&&url.searchParams.getAll(k).length===1,'query-fields');
      query={source:url.searchParams.get('source'),release:url.searchParams.get('release'),namespace:url.searchParams.get('namespace'),lexical:url.searchParams.get('value')};
      validateQuery(query);const raw=url.searchParams.get('limit');need(raw===null||/^(?:[1-9]|1[0-9]|20)$/.test(raw),'limit');
      limit=raw===null?20:Number(raw);cursor=url.searchParams.get('cursor');
      need(cursor===null||text(cursor,RESOURCE_BOUNDS.cursorBytes),'cursor');
    }catch{return response(unavailable(null),400);}
    const report=(stage,error)=>{
      if(typeof onDiagnostic!=='function')return;
      const codes=new Set(['selection','http','http-encoding','http-size','stream','stream-chunk','byte-bound','byte-count',
        'manifest-sha','manifest','key-hash','inventory','descriptor','worker-resource-bound','shard-sha',
        'invalid-json','unterminated-json-string','invalid-streamed-shard','key-binding','candidate-count',
        'duplicate-resource','reference','asset','asset-path','asset-locator','assertion','evidence','exact-tuple',
        'cursor','cursor-binding','cursor-canonical','cursor-offset','response-bound','deadline','cancelled-or-deadline']);
      const names=new Set(['Error','TypeError','RangeError','AbortError','DataError','OperationError']);
      try{onDiagnostic(Object.freeze({schema:'offmenu-source-barcode-internal-diagnostic/1',stage,
        code:codes.has(error?.message)?error.message:'runtime-operation-failed',
        errorType:names.has(error?.name)?error.name:'UnknownError'}));}catch{/* observer cannot change result */}
    };
    if(!pinned||typeof fetchImpl!=='function'){report('selection',Error('selection'));return response(unavailable(query),503);}
    const life=lifetime(request);
    try {return response(await lookup(query,limit,cursor,pinned,fetchImpl,life));}
    catch(error) {report(life.stage,error);return response(unavailable(query),503);}
    finally {life.close();}
  };
}
