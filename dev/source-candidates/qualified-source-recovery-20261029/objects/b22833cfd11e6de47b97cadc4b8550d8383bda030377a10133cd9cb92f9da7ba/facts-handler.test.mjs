import test from 'node:test';
import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
import {gzipSync} from 'node:zlib';
import {createSourceBarcodeHandler,FACTS_BOUNDS,selectOriginalPacket} from '../source/source-barcode-facts-handler.mjs';
import {createSourceBarcodeHandler as originalR5,canonical,keySha,ORIGIN,PREFIX,INDEX_RELEASE,PUBLIC_BASE} from '../source/source-barcode-handler.mjs';
import {SOURCE_PINS} from '../source/protocol-pins.mjs';
const hash=x=>createHash('sha256').update(x).digest('hex'),json=x=>Buffer.from(canonical(x)+'\n');
const query={source:'synthetic-source',release:'synthetic-release',namespace:'barcode',lexical:'001-A non-food / β '},P='urn:offmenu:property:';
const text=value=>({kind:'text',value,sourceTextSha256:hash(Buffer.from(value)),citationIds:['citation'],status:'source-asserted'});
async function fixture({found=true,total=1,mutateGraph=()=>{},mutateRef=()=>{}}={}) {
 const citation={id:'citation',sourceId:query.source,revisionId:query.release,license:'CC0 synthetic',attribution:'Synthetic fixture',scope:{visibility:'public'}};
 const pub={scope:{visibility:'public'},citationIds:['citation'],status:'source-asserted'};
 const graph={schemaVersion:'offmenu-common/1',resources:[{...pub,id:'resource',names:[text('Synthetic original name')],type:'Original source type',identityStatus:'source-asserted'}],
 assertions:[{...pub,id:'identifier',subjectId:'resource',propertyId:P+'sourceIdentifier',value:{kind:'structure',fields:{system:{kind:'identifier',value:'barcode'},value:{kind:'identifier',value:query.lexical}}}},
 {...pub,id:'fields',subjectId:'resource',propertyId:P+'sourceFields',value:{kind:'structure',fields:{originalLabel:text('Original source field'),zero:{kind:'number',value:0},unknown:{kind:'null',value:null},related:{kind:'reference',id:'unresolved-source-profile'}}}}],
 relations:[{...pub,id:'relation',subjectId:'resource',predicateId:P+'hasNutrientProfile',objectId:'unresolved-source-profile'}],citations:[citation],translations:[]};
 const identifierSha=hash(Buffer.from(canonical(graph.assertions[0])));mutateGraph(graph);
 const empty={schemaVersion:'offmenu-common/1',resources:[],assertions:[],relations:[],citations:[],translations:[]};
 const asset=gzipSync(Buffer.concat([json(empty),json(graph),json(empty)]));
 const ref={sourceResourceId:'resource',asset:{path:PUBLIC_BASE.assetPrefix+'synthetic-facts.jsonl.gz',sha256:hash(asset),bytes:asset.length,packetOrdinal:1,packetCount:3,packetCanonicalSha256:null,packetDigestState:'not-retained-in-selected-product-locator-index'},
 identifierAssertion:{id:'identifier',canonicalSha256:identifierSha,matchingAssertionCount:1,referencesTruncated:false},sourceAssertionStatus:null,sourceAssertionStatusState:'resolve-original-public-assertion',citationRefs:null,ingredientRefs:null,nutrientRefs:null};mutateRef(ref);
 const h=await keySha(query),prefix=h.slice(0,2),refs=Array.from({length:Math.min(total,20)},(_,i)=>i?{...ref,sourceResourceId:'other-resource-'+i}:ref);
 const decoded=json({schemaVersion:'offmenu-source-barcode-index-shard/1',prefix,entries:found?[{key:query,keySha256:h,candidateTotal:total,returnedCount:refs.length,truncated:total>refs.length,candidates:refs}]:[]});
 const compressed=gzipSync(decoded),shards={};for(let i=0;i<256;i++){const p=i.toString(16).padStart(2,'0');shards[p]={path:'shards/'+p+'.json.gz',publicPath:PREFIX+'shards/'+p+'.json.gz',bytes:compressed.length,uncompressedBytes:decoded.length,sha256:hash(compressed),indexedKeys:found?1:0};}
 const manifest=json({schemaVersion:'offmenu-source-barcode-index/1',indexReleaseId:INDEX_RELEASE,complete:true,sourcePins:SOURCE_PINS,publicBase:PUBLIC_BASE,candidateReferenceCap:20,keyHash:{algorithm:'SHA256',input:'UTF-8 canonical JSON array [source,release,namespace,lexical]',canonicalJSON:'sorted object keys; no whitespace; ensure_ascii=false; finite JSON',normalization:'none',shardPrefixHexCharacters:2},shards,canonicalIdentityAsserted:false,automaticPlanningEligible:false,nutritionAggregationEligible:false});
 const selection={manifestUrl:ORIGIN+PREFIX+'manifest.json',manifestSha256:hash(manifest),indexReleaseId:INDEX_RELEASE,sourcePins:SOURCE_PINS,publicBase:PUBLIC_BASE};
 const calls=[];const fetchImpl=async(url,options)=>{calls.push({url,options});assert.equal(options.redirect,'manual');
 if(url===selection.manifestUrl)return new Response(manifest);if(url===ORIGIN+PREFIX+'shards/'+prefix+'.json.gz')return new Response(compressed);
 if(url===ORIGIN+ref.asset.path)return new Response(asset);throw Error('Unexpected outbound URL');};
 return {graph,asset,ref,selection,fetchImpl,calls};
}
function request(extra={include:'facts'},signal){return new Request('https://offmenu.aldous.info/api/corpus/source-barcode?'+new URLSearchParams({source:query.source,release:query.release,namespace:'barcode',value:query.lexical,...extra}),{signal,headers:{Cookie:'synthetic-never-forward',Authorization:'Bearer synthetic-never-forward'}});}
async function get(f,req=request(),fetchImpl=f.fetchImpl){const response=await createSourceBarcodeHandler({selection:f.selection,fetchImpl})(req);return {response,value:await response.json()};}
test('facts mode returns reused verified original projection, zero, unknown, citations and unresolved boundaries',async()=>{
 const f=await fixture(),r=await get(f);assert.equal(r.response.status,200);assert.equal(r.value.schemaVersion,'offmenu-source-barcode-facts/1');
 assert.equal(r.value.factsStatus,'verified-original-public-packet');const facts=r.value.originalFacts;
 assert.equal(facts.name,'Synthetic original name');assert.equal(facts.facts.length,4);assert.equal(facts.facts.find(x=>x.label==='zero').text,'0');assert.equal(facts.facts.find(x=>x.label==='unknown').text,'Unknown');
 assert.match(facts.facts.find(x=>x.label==='related').text,/unresolved/);assert.equal(facts.citations.length,1);assert.equal(facts.citations[0].license,'CC0 synthetic');assert.equal(facts.unresolvedRelations.length,1);
 assert.equal(r.value.candidateLookup.candidateTotal,1);assert.equal(r.value.candidateLookup.candidates[0].nutrientRefs,null);
 for(const k of ['canonicalIdentityAsserted','automaticPlanningEligible','nutritionAggregationEligible']){assert.equal(r.value[k],false);assert.equal(facts[k],false);}
 assert.equal(f.calls.length,3);for(const {url,options} of f.calls){assert.equal(new URL(url).origin,ORIGIN);assert.equal(options.credentials,'omit');assert.equal(options.cache,'no-store');assert.equal(options.headers['Accept-Encoding'],'identity');assert.equal(JSON.stringify(options).includes('synthetic-never-forward'),false);}
 assert.equal(r.response.headers.get('cache-control'),'no-store');
});
test('candidate-only default remains byte-exact R5; unknown include and duplicate include remain invalid',async()=>{
 const f=await fixture(),req=request({});const actual=await createSourceBarcodeHandler({selection:f.selection,fetchImpl:f.fetchImpl})(req);
 const expected=await originalR5({selection:f.selection,fetchImpl:f.fetchImpl})(req);assert.equal(await actual.text(),await expected.text());
 for(const req of [request({include:'other'}),new Request(request().url+'&include=facts')])assert.equal((await get(f,req)).response.status,400);
});
test('successful scoped miss stays HTTP200 and never hydrates or claims global absence',async()=>{
 const f=await fixture({found:false}),r=await get(f);assert.equal(r.response.status,200);assert.equal(r.value.factsStatus,'source-key-not-found');assert.equal(r.value.originalFacts,null);assert.equal(r.value.candidateLookup.complete,true);assert.equal(f.calls.length,2);
});
test('ambiguity is selection-required even if page contains one reference; no arbitrary hydration',async()=>{
 const f=await fixture({total:2}),r=await get(f,request({include:'facts',limit:'1'}));assert.equal(r.response.status,200);assert.equal(r.value.factsStatus,'selection-required');assert.equal(r.value.originalFacts,null);assert.equal(r.value.candidateLookup.candidateTotal,2);assert.equal(r.value.candidateLookup.returnedCount,1);assert.equal(f.calls.length,2);
});
test('index technical failure retains unavailable candidateLookup and does not manufacture absence',async()=>{
 const f=await fixture(),r=await get(f,request(),async()=>new Response(null,{status:503}));assert.equal(r.response.status,503);assert.equal(r.value.factsStatus,'index-unavailable');assert.equal(r.value.candidateLookup.countKnown,false);assert.equal(r.value.originalFacts,null);
});
test('asset corruption/redirect/encoding/ordinal/count failures preserve successful candidate lookup as facts-unavailable',async()=>{
 for(const mode of ['corrupt','redirect','encoding','count','ordinal']){
 const f=await fixture({mutateRef:r=>{if(mode==='count')r.asset.packetCount=4;if(mode==='ordinal')r.asset.packetOrdinal=0;}});
 const fetchImpl=async(url,opts)=>{if(url!==ORIGIN+f.ref.asset.path)return f.fetchImpl(url,opts);
 if(mode==='corrupt')return new Response(Buffer.from(f.asset).fill(1));if(mode==='redirect')return new Response(null,{status:302,headers:{Location:'https://evil.example'}});
 return new Response(f.asset,{headers:mode==='encoding'?{'Content-Encoding':'gzip'}:{}});};
 const r=await get(f,request(),fetchImpl);assert.equal(r.response.status,503,mode);assert.equal(r.value.factsStatus,'facts-unavailable');assert.equal(r.value.originalFacts,null);assert.equal(r.value.candidateLookup.candidateTotal,1);assert.equal(r.value.candidateLookup.complete,true);}
});
test('citation scope/release/licence, original text and identifier digest/lexical/resource mismatches refuse facts',async()=>{
 for(const mutateGraph of [g=>g.citations[0].scope.visibility='private',g=>g.citations[0].revisionId='other',g=>g.citations[0].license='',
 g=>g.resources[0].names[0].value='changed without text hash',g=>g.assertions[0].value.fields.value.value='other-key',g=>g.resources[0].id='other-resource']){
 const r=await get(await fixture({mutateGraph}));assert.equal(r.response.status,503);assert.equal(r.value.factsStatus,'facts-unavailable');assert.equal(r.value.originalFacts,null);}
});
test('selected-packet streaming validates complete count/EOF and packet limit across tiny chunks',async()=>{
 const f=await fixture();const graphText=canonical(f.graph);const raw=Buffer.from('{}\n'+graphText+'\n{}\n');
 const stream=new ReadableStream({start(c){for(let i=0;i<raw.length;i+=3)c.enqueue(raw.subarray(i,i+3));c.close();}});
 const life={signal:new AbortController().signal,run:fn=>fn()};const result=await selectOriginalPacket(stream,f.ref.asset,life);assert.equal(result.resources[0].id,'resource');
 await assert.rejects(()=>selectOriginalPacket(new Response(raw.subarray(0,-1)).body,f.ref.asset,life));
 await assert.rejects(()=>selectOriginalPacket(new Response(raw).body,{...f.ref.asset,packetCount:4},life));
});
test('facts request cancellation aborts a stalled asset fetch with no fallback facts or duplicate request',async()=>{
 const f=await fixture(),controller=new AbortController();let requested=0;const fetchImpl=async(url,opts)=>{
 if(url!==ORIGIN+f.ref.asset.path)return f.fetchImpl(url,opts);requested++;controller.abort();return new Promise(()=>{});};
 const r=await get(f,request({include:'facts'},controller.signal),fetchImpl);assert.equal(r.response.status,503);assert.equal(r.value.factsStatus,'facts-unavailable');assert.equal(requested,1);assert.equal(r.value.candidateLookup.complete,true);
});
test('facts total deadline bounds a noncooperative asset fetch without changing candidate evidence',async t=>{
 const f=await fixture();let entered,signal,calls=0;const began=new Promise(resolve=>entered=resolve);
 t.mock.timers.enable({apis:['setTimeout','Date']});t.after(()=>t.mock.timers.reset());
 const fetchImpl=async(url,options)=>{if(url!==ORIGIN+f.ref.asset.path)return f.fetchImpl(url,options);calls++;signal=options.signal;entered();return new Promise(()=>{});};
 const pending=get(f,request(),fetchImpl);await began;t.mock.timers.tick(FACTS_BOUNDS.timeoutMs+1);
 const r=await pending;assert.equal(r.response.status,503);assert.equal(r.value.factsStatus,'facts-unavailable');assert.equal(r.value.candidateLookup.complete,true);assert.equal(signal.aborted,true);assert.equal(calls,1);
});
test('a selected packet exceeding its explicit byte cap fails before graph parsing',async()=>{
 const stream=new ReadableStream({start(c){c.enqueue(Buffer.alloc(1024*1024,32));c.enqueue(Buffer.alloc(1024*1024,32));c.enqueue(Buffer.from('x\n'));c.close();}});
 await assert.rejects(()=>selectOriginalPacket(stream,{packetOrdinal:0,packetCount:1},{signal:new AbortController().signal,run:fn=>fn()}));
});
