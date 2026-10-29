import test from 'node:test';
import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
import {gzipSync} from 'node:zlib';
import {createSourceBarcodeHandler,FACTS_BOUNDS,selectOriginalPacket} from '../../apps/web/server/source-barcode-api/source-barcode-facts-handler.mjs';
import {createSourceBarcodeHandler as originalR5,canonical,keySha,ORIGIN,PREFIX,INDEX_RELEASE,PUBLIC_BASE} from '../../apps/web/server/source-barcode-api/source-barcode-handler.mjs';
import {SOURCE_PINS} from '../../apps/web/server/source-barcode-api/protocol-pins.mjs';
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
test('valid 18-second pinned input completes facts lookup inside the scanner 40-second window',async t=>{
 const f=await fixture();let entered;const began=new Promise(resolve=>entered=resolve),events=[];const calls=[];
 t.mock.timers.enable({apis:['setTimeout','Date']});t.after(()=>t.mock.timers.reset());
 const handler=createSourceBarcodeHandler({selection:f.selection,onDiagnostic:e=>events.push(e),fetchImpl:(url,options)=>{
  calls.push(url);if(url===f.selection.manifestUrl){entered();return new Promise(resolve=>setTimeout(()=>resolve(f.fetchImpl(url,options)),18000));}
  return f.fetchImpl(url,options);
 }});
 const pending=handler(request());await began;t.mock.timers.tick(18000);
 const response=await pending,value=await response.json();
 // Fixed stage metadata is safe and helps establish the exact baseline failure.
 if(response.status!==200)console.log(JSON.stringify({offlineBaselineRejection:{http:response.status,factsStatus:value.factsStatus,diagnostic:events[0]}}));
 assert.equal(response.status,200);assert.equal(value.factsStatus,'verified-original-public-packet');assert.equal(value.originalFacts.name,'Synthetic original name');
 assert.equal(value.candidateLookup.complete,true);assert.equal(calls.length,3);assert.deepEqual(events,[]);
});
test('index budget remains absolute across fetches; 33-second cumulative delay is refused without false absence',async t=>{
 const f=await fixture();let enteredManifest,enteredShard;
 const manifestStarted=new Promise(resolve=>enteredManifest=resolve),shardStarted=new Promise(resolve=>enteredShard=resolve),events=[];
 t.mock.timers.enable({apis:['setTimeout','Date']});t.after(()=>t.mock.timers.reset());
 let calls=0;const handler=createSourceBarcodeHandler({selection:f.selection,onDiagnostic:e=>events.push(e),fetchImpl:(url,options)=>{
  calls++;if(url===f.selection.manifestUrl){enteredManifest();return new Promise(resolve=>setTimeout(()=>resolve(f.fetchImpl(url,options)),14000));}
  enteredShard();return new Promise(resolve=>setTimeout(()=>resolve(f.fetchImpl(url,options)),19000));
 }});
 const pending=handler(request());await manifestStarted;t.mock.timers.tick(14000);await shardStarted;t.mock.timers.tick(19000);
 const response=await pending,value=await response.json();assert.equal(response.status,503);assert.equal(value.factsStatus,'index-unavailable');
 assert.equal(value.candidateLookup.candidateTotal,null);assert.equal(value.candidateLookup.complete,false);assert.equal(calls,2);
 assert.equal(events[0].stage,'shard-fetch');assert.equal(events[0].code,'cancelled-or-deadline');
});
test('noncooperative fetch still expires at finite index deadline with no retry',async t=>{
 const f=await fixture();const {RESOURCE_BOUNDS}=await import('../../apps/web/server/source-barcode-api/source-barcode-handler.mjs');let entered,signal,calls=0;
 const began=new Promise(resolve=>entered=resolve),events=[];t.mock.timers.enable({apis:['setTimeout','Date']});t.after(()=>t.mock.timers.reset());
 const pending=createSourceBarcodeHandler({selection:f.selection,onDiagnostic:e=>events.push(e),fetchImpl:(url,options)=>{calls++;signal=options.signal;entered();return new Promise(()=>{});}})(request());
 await began;t.mock.timers.tick(RESOURCE_BOUNDS.deadlineMs+1);const response=await pending,value=await response.json();
 assert.ok(RESOURCE_BOUNDS.deadlineMs<40000);assert.equal(response.status,503);assert.equal(value.candidateLookup.countKnown,false);assert.equal(signal.aborted,true);assert.equal(calls,1);assert.equal(events[0].code,'cancelled-or-deadline');
});
test('caller cancellation remains immediate before revised budget; no fallback or fact fabrication',async t=>{
 const f=await fixture();let entered,calls=0,signal;const began=new Promise(resolve=>entered=resolve),controller=new AbortController();
 t.mock.timers.enable({apis:['setTimeout','Date']});t.after(()=>t.mock.timers.reset());
 const pending=createSourceBarcodeHandler({selection:f.selection,fetchImpl:(url,options)=>{calls++;signal=options.signal;entered();return new Promise(()=>{});}})(request({include:'facts'},controller.signal));
 await began;t.mock.timers.tick(5000);controller.abort();const response=await pending,value=await response.json();
 assert.equal(response.status,503);assert.equal(value.factsStatus,'index-unavailable');assert.equal(value.originalFacts,null);assert.equal(signal.aborted,true);assert.equal(calls,1);
});
