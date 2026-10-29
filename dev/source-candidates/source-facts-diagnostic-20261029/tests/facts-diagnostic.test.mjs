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
test('facts failure reports only fixed request-local stage/code/type and retains exact candidate evidence',async()=>{
 const f=await fixture(),events=[];const handler=createSourceBarcodeHandler({selection:f.selection,onDiagnostic:e=>events.push(e),fetchImpl:async(url,opts)=>{
 if(url===ORIGIN+f.ref.asset.path)return new Response(null,{status:503});return f.fetchImpl(url,opts);}});
 const res=await handler(request()),value=await res.json();assert.equal(res.status,503);assert.equal(value.factsStatus,'facts-unavailable');assert.equal(value.candidateLookup.complete,true);
 assert.deepEqual(events,[{schema:'offmenu-source-barcode-facts-internal-diagnostic/1',stage:'asset-response',code:'facts-stage-failed',errorType:'Error'}]);
 assert.deepEqual(Object.keys(events[0]).sort(),['code','errorType','schema','stage']);
});
test('unknown transport error content and observer exceptions cannot escape or change HTTP semantics',async()=>{
 const f=await fixture();let event;const handler=createSourceBarcodeHandler({selection:f.selection,onDiagnostic:e=>{event=e;throw Error('observer');},fetchImpl:async(url,opts)=>{
 if(url===ORIGIN+f.ref.asset.path)throw new TypeError('SYNTHETIC_PRIVATE_MARKER');return f.fetchImpl(url,opts);}});
 const res=await handler(request()),value=await res.json();assert.equal(res.status,503);assert.equal(value.factsStatus,'facts-unavailable');assert.equal(value.originalFacts,null);
 assert.deepEqual(event,{schema:'offmenu-source-barcode-facts-internal-diagnostic/1',stage:'asset-fetch',code:'facts-stage-failed',errorType:'TypeError'});
 assert.equal(JSON.stringify(event).includes('SYNTHETIC_PRIVATE_MARKER'),false);
});
