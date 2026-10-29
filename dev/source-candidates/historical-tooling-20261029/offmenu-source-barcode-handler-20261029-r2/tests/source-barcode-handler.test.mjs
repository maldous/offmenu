import test from 'node:test';
import assert from 'node:assert/strict';
import {gzipSync} from 'node:zlib';
import {createHash} from 'node:crypto';
import fs from 'node:fs';
import vm from 'node:vm';
import {createSourceBarcodeHandler,canonical,keySha,INDEX_RELEASE,ORIGIN,PREFIX,PUBLIC_BASE,RESOURCE_BOUNDS} from '../source/source-barcode-handler.mjs';
import {SOURCE_PINS} from '../source/protocol-pins.mjs';
import {strictJSON} from '../source/strict-json.mjs';
import {scanShard} from '../source/stream-shard.mjs';
const hash=b=>createHash('sha256').update(b).digest('hex'), bytes=x=>Buffer.from(canonical(x)+'\n');
const query={source:'synthetic-source',release:'synthetic-release',namespace:'barcode',lexical:'00001234'};
const keyHash={algorithm:'SHA256',input:'UTF-8 canonical JSON array [source,release,namespace,lexical]',
 canonicalJSON:'sorted object keys; no whitespace; ensure_ascii=false; finite JSON',normalization:'none',shardPrefixHexCharacters:2};
function ref(i) {return {sourceResourceId:'synthetic-resource-'+i,asset:{path:PUBLIC_BASE.assetPrefix+'synthetic.json.gz',sha256:'a'.repeat(64),
 bytes:100,packetOrdinal:i,packetCount:100,packetCanonicalSha256:null,packetDigestState:'not-retained-in-selected-product-locator-index'},
 identifierAssertion:{id:'synthetic-assertion-'+i,canonicalSha256:'b'.repeat(64),matchingAssertionCount:1,referencesTruncated:false},
 sourceAssertionStatus:null,sourceAssertionStatusState:'resolve-original-public-assertion',citationRefs:null,ingredientRefs:null,nutrientRefs:null};}
async function fixture({q=query,total=1,found=true,mutateShard=()=>{},mutateManifest=()=>{},rawManifest=null,rawShard=null}={}) {
 q=structuredClone(q);const h=await keySha(q),prefix=h.slice(0,2);
 const shard={schemaVersion:'offmenu-source-barcode-index-shard/1',prefix,entries:found?[{key:q,keySha256:h,candidateTotal:total,
   returnedCount:Math.min(total,20),truncated:total>20,candidates:Array.from({length:Math.min(total,20)},(_,i)=>ref(i))}]:[]};
 mutateShard(shard);const decoded=rawShard?Buffer.from(rawShard(shard)):bytes(shard),compressed=gzipSync(decoded);
 const shards={};for(let i=0;i<256;i++){const p=i.toString(16).padStart(2,'0');shards[p]={path:'shards/'+p+'.json.gz',publicPath:PREFIX+'shards/'+p+'.json.gz',
 bytes:compressed.length,sha256:hash(compressed),uncompressedBytes:decoded.length,indexedKeys:shard.entries.length};}
 const manifest={schemaVersion:'offmenu-source-barcode-index/1',indexReleaseId:INDEX_RELEASE,complete:true,sourcePins:structuredClone(SOURCE_PINS),
 publicBase:structuredClone(PUBLIC_BASE),candidateReferenceCap:20,keyHash:structuredClone(keyHash),shards,canonicalIdentityAsserted:false,automaticPlanningEligible:false,nutritionAggregationEligible:false};
 mutateManifest(manifest);const manifestBytes=rawManifest?Buffer.from(rawManifest(manifest)):bytes(manifest);
 const selection={manifestUrl:ORIGIN+PREFIX+'manifest.json',manifestSha256:hash(manifestBytes),indexReleaseId:INDEX_RELEASE,
  sourcePins:SOURCE_PINS,publicBase:PUBLIC_BASE};
 const requests=[];const fetchImpl=async(url,options)=>{requests.push({url,options});
  if(url===selection.manifestUrl)return new Response(manifestBytes);
  if(url===ORIGIN+PREFIX+'shards/'+prefix+'.json.gz')return new Response(compressed);
  throw Error('No other outbound route is allowed in fixture');};
 return {q,h,prefix,shard,compressed,decoded,manifest,manifestBytes,selection,fetchImpl,requests};
}
function request(q=query,extra={}) {const p=new URLSearchParams({source:q.source,release:q.release,namespace:q.namespace,value:q.lexical,...extra});
 return new Request('https://offmenu.aldous.info/api/corpus/source-barcode?'+p);}
async function result(f,req=request(f.q),selection=f.selection,fetchImpl=f.fetchImpl){const response=await createSourceBarcodeHandler({selection,fetchImpl})(req);return {response,value:await response.json()};}
function unavailable(r){assert.equal(r.response.status,503);assert.equal(r.value.status,'index-unavailable');assert.equal(r.value.candidateTotal,null);
 assert.equal(r.value.countKnown,false);assert.equal(r.value.complete,false);assert.equal(r.value.truncated,null);assert.deepEqual(r.value.candidates,[]);}
test('exact lexical/Unicode hashes follow producer canonical tuple; no leading-zero repair',async()=>{
 const q={...query,source:'日本語',lexical:' 00001234 '};assert.equal(await keySha(q),hash(Buffer.from(JSON.stringify([q.source,q.release,q.namespace,q.lexical]))));
 assert.notEqual(await keySha(query),await keySha({...query,lexical:'1234'}));
 const f=await fixture({q});const r=await result(f);assert.equal(r.value.query.lexical,q.lexical);assert.equal(r.value.status,'source-scoped-candidates');
});
test('reference envelope preserves unresolved evidence, selected provenance and false promotion flags',async()=>{
 const f=await fixture();const r=await result(f);assert.equal(r.response.status,200);assert.equal(r.value.schemaVersion,'offmenu-source-barcode-candidates/1');
 assert.equal(r.value.status,'source-scoped-candidates');assert.equal(r.value.complete,true);assert.equal(r.value.referenceCoverageComplete,true);
 assert.deepEqual(r.value.candidates,[ref(0)]);for(const k of ['canonicalIdentityAsserted','automaticPlanningEligible','nutritionAggregationEligible'])assert.equal(r.value[k],false);
 assert.equal(r.value.manifestSha256,f.selection.manifestSha256);assert.deepEqual(r.value.sourcePins,SOURCE_PINS);assert.deepEqual(r.value.publicBase,PUBLIC_BASE);
 assert.equal(r.response.headers.get('cache-control'),'no-store');assert.equal(r.response.headers.get('referrer-policy'),'no-referrer');assert.equal(r.response.headers.get('access-control-allow-origin'),null);
 for(const {url,options} of f.requests){assert.equal(new URL(url).origin,ORIGIN);assert.equal(options.redirect,'error');assert.equal(options.credentials,'omit');assert.equal(options.headers['Accept-Encoding'],'identity');}
});
test('ambiguous capped terminal page remains truncated and coverage-incomplete; cursor binds full query/limit/pin',async()=>{
 const f=await fixture({total:23});const first=await result(f,request(query,{limit:'7'}));assert.equal(first.value.status,'ambiguous-source-key');assert.equal(first.value.candidateTotal,23);
 assert.equal(first.value.truncated,true);assert.equal(first.value.referenceCoverageComplete,false);assert.ok(first.value.nextCursor);
 const second=await result(f,request(query,{limit:'7',cursor:first.value.nextCursor}));assert.equal(second.value.returnedCount,7);
 const last=await result(f,request(query,{limit:'7',cursor:second.value.nextCursor}));assert.equal(last.value.returnedCount,6);assert.equal(last.value.nextCursor,null);assert.equal(last.value.truncated,true);
 for(const req of [request({...query,source:'different'},{limit:'7',cursor:first.value.nextCursor}),request(query,{limit:'8',cursor:first.value.nextCursor})])unavailable(await result(f,req));
 unavailable(await result(f,request(query,{limit:'7',cursor:first.value.nextCursor}),{...f.selection,manifestSha256:'f'.repeat(64)}));
});
test('not-found requires complete successful selected shard lookup',async()=>{
 const f=await fixture({found:false});const r=await result(f);assert.equal(r.value.status,'source-key-not-found');assert.equal(r.value.candidateTotal,0);assert.equal(r.value.complete,true);assert.equal(r.value.countKnown,true);
 unavailable(await result(f,request(),f.selection,async()=>new Response('missing',{status:404})));
 unavailable(await result(await fixture({found:false,mutateManifest:m=>m.complete=false})));
});
test('missing selection and mutated/untrusted selection cannot fetch or assert absence',async()=>{
 const f=await fixture();for(const selection of [null,{...f.selection,manifestUrl:'https://evil.example/manifest.json'},
 {...f.selection,manifestUrl:ORIGIN+PREFIX+'../manifest.json'},{...f.selection,indexReleaseId:'different'},
 {...f.selection,sourcePins:{...SOURCE_PINS,schemaSha256:'0'.repeat(64)}},{...f.selection,publicBase:{...PUBLIC_BASE,origin:'https://evil.example'}}]) {
 let calls=0;unavailable(await result(f,request(),selection,async()=>{calls++;throw Error('must not fetch');}));assert.equal(calls,0);}
});
test('exact route/method/query/page bounds are enforced without broad route effects',async()=>{
 const f=await fixture(),handle=createSourceBarcodeHandler({selection:f.selection,fetchImpl:f.fetchImpl});
 assert.equal(await handle(new Request('https://offmenu.aldous.info/api/data/public')),null);
 const method=await handle(new Request(request().url,{method:'POST'}));assert.equal(method.status,405);assert.equal(method.headers.get('allow'),'GET');
 for(const extra of [{limit:'0'},{limit:'21'},{limit:'01'},{url:'https://evil.example/'},{namespace:'fdc'},{value:''},{cursor:'x'.repeat(32769)}]) {
 const r=await result(f,request(query,extra));assert.equal(r.response.status,400);assert.equal(r.value.status,'index-unavailable');}
 const dup=await handle(new Request(request().url+'&source=other'));assert.equal(dup.status,400);assert.equal(f.requests.length,0);
});
test('manifest hash/source pins/key algorithm/complete inventory changes fail closed',async()=>{
 const f=await fixture();unavailable(await result(f,request(),{...f.selection,manifestSha256:'0'.repeat(64)}));
 for(const mutateManifest of [m=>m.sourcePins={...SOURCE_PINS,contractSha256:'0'.repeat(64)},m=>m.publicBase={...PUBLIC_BASE,releaseId:'other'},
 m=>delete m.shards.ff,m=>m.keyHash.normalization='trim',m=>m.canonicalIdentityAsserted=true,m=>m.shards.ff.publicPath='/other'])
 unavailable(await result(await fixture({mutateManifest})));
});
test('compressed byte/hash/expanded size, gzip corruption and unsafe response encoding are unavailable',async()=>{
 const f=await fixture();
 for(const mode of ['hash','short','redirect','encoding','length']){
 const fetchImpl=async(url,opts)=>{if(url===f.selection.manifestUrl)return f.fetchImpl(url,opts);
  if(mode==='hash')return new Response(Buffer.from(f.compressed).fill(1));
  if(mode==='short')return new Response(f.compressed.subarray(0,-1));
  if(mode==='redirect')return new Response(null,{status:302,headers:{Location:'https://evil.example'}});
  return new Response(f.compressed,{headers:mode==='encoding'?{'Content-Encoding':'gzip'}:{'Content-Length':'1'}});};
 unavailable(await result(f,request(),f.selection,fetchImpl));}
 unavailable(await result(await fixture({mutateManifest:m=>m.shards[f.prefix].uncompressedBytes++})));
 const g=await fixture({mutateManifest:m=>m.shards[f.prefix].sha256=hash(Buffer.from('not gzip'))});
 unavailable(await result(g,request(),g.selection,async(url,opts)=>url===g.selection.manifestUrl?g.fetchImpl(url,opts):new Response('not gzip')));
});
test('duplicate JSON keys, nonfinite/unsafe numbers, excessive depth and node count are rejected',async()=>{
 for(const s of ['{"a":1,"a":2}','{"a":1,"\\u0061":2}','[1e999]','[9007199254740993]', '['.repeat(34)+'0'+']'.repeat(34)])assert.throws(()=>strictJSON(s));
 assert.throws(()=>strictJSON('[0,0,0]',()=>{},3));
 unavailable(await result(await fixture({rawManifest:m=>'{"complete":false,'+canonical(m).slice(1)+'\n'})));
 unavailable(await result(await fixture({rawShard:s=>'{"prefix":"bad",'+canonical(s).slice(1)+'\n'})));
});
test('invalid key binding/order/count/duplicate resources or fabricated evidence invalidates entire shard',async()=>{
 for(const mutateShard of [s=>s.entries[0].key.source='other',s=>s.entries.push(s.entries[0]),s=>s.entries[0].returnedCount=9,
 s=>s.entries[0].candidates[0].citationRefs=[],s=>s.entries[0].candidates[0].asset.packetCanonicalSha256='a'.repeat(64),
 s=>s.entries[0].candidates[0].asset.path=PUBLIC_BASE.assetPrefix+'../private',s=>s.entries[0].candidates[0].asset.packetOrdinal=100,
 s=>s.entries[0].candidates[0].identifierAssertion.referencesTruncated=true]) unavailable(await result(await fixture({mutateShard})));
 unavailable(await result(await fixture({total:2,mutateShard:s=>s.entries[0].candidates[1]=s.entries[0].candidates[0]})));
});
test('declared Worker resource bound fails before fetching large shard, never returns partial absence',async()=>{
 const f=await fixture({found:false,mutateManifest:m=>{for(const d of Object.values(m.shards))d.uncompressedBytes=RESOURCE_BOUNDS.expandedBytes+1;}});
 unavailable(await result(f));assert.equal(f.requests.length,1);
});
test('stream bound cancels excess data and caller cancellation interrupts a noncooperative fetch',async()=>{
 const f=await fixture();let cancelled=false;
 const oversize=async()=>new Response(new ReadableStream({pull(c){c.enqueue(new Uint8Array(1024*1024));},cancel(){cancelled=true;}}));
 unavailable(await result(f,request(),f.selection,oversize));assert.equal(cancelled,true);
 const controller=new AbortController();const req=new Request(request(),{signal:controller.signal});
 const pending=result(f,req,f.selection,()=>new Promise(()=>{}));controller.abort();unavailable(await pending);
});
test('cursor malformed/out-of-range and returned response resource bound cannot manufacture not-found',async()=>{
 const f=await fixture();for(const cursor of ['!','e30',Buffer.from(canonical({manifestSha256:f.selection.manifestSha256,query,limit:20,offset:21})).toString('base64url')])unavailable(await result(f,request(query,{cursor})));
});
test('dispatcher integration preserves all unrelated behavior and environment fallback precedes adapter',async()=>{
 const seam=JSON.parse(fs.readFileSync(new URL('../input/endpoint-seam201.json',import.meta.url)));
 const guard="if(env.OFFMENU_AUTH_MODE!==undefined&&env.OFFMENU_AUTH_MODE!=='netlify'||env.DEV_COMPOSITION||env.OFFMENU_LOCAL_LAB)return previous.fetch(request,env,ctx);";
 const addition="if(new URL(request.url).pathname==='/api/corpus/source-barcode')return sourceBarcode(request);";
 const original=seam.dispatcher.replace(/\\n$/,'').trimEnd();assert.equal(original.split(guard).length,2);
 const adapted=original.replace(guard,guard+addition);assert.equal(adapted.replace(addition,''),original);
 const calls=[];const context={URL,Response,Blob,Uint8Array,headers:{},assets:{},
 previous:{fetch:async()=>{calls.push('fallback');return new Response('fallback');},scheduled(){}},
 sourceBarcode:async()=>{calls.push('source');return new Response('source');},EXISTING_PUBLIC_INVENTORY_SELECTION:{sourceId:'unused'},publicDemoProduct(){}};
 const dispatcher=vm.runInNewContext(adapted.replace('export default','(').replace(/;$/,'')+')',context);
 await dispatcher.fetch(request(),{});assert.deepEqual(calls,['source']);calls.length=0;
 await dispatcher.fetch(request(),{OFFMENU_AUTH_MODE:'other'});assert.deepEqual(calls,['fallback']);
});
test('absolute handler deadline bounds a stalled fetch without a duplicate fallback',async t=>{
 const f=await fixture();t.mock.timers.enable({apis:['setTimeout','Date']});let calls=0;
 try {
  const pending=result(f,request(),f.selection,()=>{calls++;return new Promise(()=>{});});
  await Promise.resolve();await Promise.resolve();t.mock.timers.tick(RESOURCE_BOUNDS.deadlineMs+1);
  unavailable(await pending);assert.equal(calls,1);
 } finally {t.mock.timers.reset();}
});

test('arbitrary supported non-food identifiers remain exact; no digits-only or food-only gate',async()=>{
 const q={...query,source:'non-food-source',lexical:'part: A-001 / β '};const f=await fixture({q});
 const r=await result(f);assert.equal(r.value.status,'source-scoped-candidates');assert.equal(r.value.query.lexical,q.lexical);
});
const immediateLife={check(){},run:fn=>fn()};
function streamChunks(parts){return new ReadableStream({start(c){for(const p of parts)c.enqueue(Buffer.from(p));c.close();}});}
test('incremental parser handles every one-byte boundary, escapes and UTF8; validates EOF/count/schema',async()=>{
 const entry={key:{...query,lexical:'β \"quoted\" \\ brace }'},marker:'[{}]'};
 const raw=bytes({entries:[entry],prefix:'ab',schemaVersion:'offmenu-source-barcode-index-shard/1'});let selected;
 await scanShard(streamChunks([...raw].map(b=>Buffer.from([b]))),{expectedBytes:raw.length,expectedPrefix:'ab',expectedEntries:1,maxEntries:2,life:immediateLife,onEntry:async e=>selected=e});
 assert.deepEqual(JSON.parse(JSON.stringify(selected)),entry);
 for(const malformed of ['{"entries":[],"prefix":"ab","schemaVersion":"wrong"}',
 '{"entries":[],"entries":[],"prefix":"ab","schemaVersion":"offmenu-source-barcode-index-shard/1"}',
 '{"entries":[{},],"prefix":"ab","schemaVersion":"offmenu-source-barcode-index-shard/1"}',
 '{"entries":[],"prefix":"ab","schemaVersion":"offmenu-source-barcode-index-shard/1"}{}']) {
 const raw=Buffer.from(malformed);await assert.rejects(()=>scanShard(streamChunks([raw]),{expectedBytes:raw.length,expectedPrefix:'ab',expectedEntries:0,maxEntries:2,life:immediateLife,onEntry:async()=>{}}));}
});
test('incremental parser enforces one-entry bound and validates suffix after the selected entry',async()=>{
 const raw=bytes({entries:[{large:'x'.repeat(300)}],prefix:'ab',schemaVersion:'offmenu-source-barcode-index-shard/1'});
 await assert.rejects(()=>scanShard(streamChunks([raw]),{expectedBytes:raw.length,expectedPrefix:'ab',expectedEntries:1,maxEntries:2,maxEntryBytes:100,life:immediateLife,onEntry:async()=>{}}));
 const f=await fixture({rawShard:s=>canonical(s)+'TRAILER'});unavailable(await result(f));
 const f2=await fixture({mutateShard:s=>s.prefix='ff'});unavailable(await result(f2));
});
test('measured real maximum descriptor sizes fit runtime bounds without allocating a real shard',()=>{
 assert.ok(4322325<=RESOURCE_BOUNDS.compressedBytes);assert.ok(25303410<=RESOURCE_BOUNDS.expandedBytes);
 // No full real index download, dataset allocation, stress test or producer replay.
});
