import test from 'node:test';
import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
import {gzipSync} from 'node:zlib';
import {providerDataRoutes} from '../../cloud/provider-data.mjs';

// Invented in-memory serving fixture, not a real source or acceptance receipt.
const origin='https://offmenu-corpus.netlify.app';
const sha=bytes=>createHash('sha256').update(bytes).digest('hex');
const options={verifiedUser:async()=>null,boundedJSON:async r=>r.json(),assets:{}};
function fixture(source='off'){
 const blobs=new Map(),files=[];
 const row={id:'offmenu:product:invented',schemaVersion:'1.0',kind:'product',countries:[],
  data:{name:'Invented food',identifiers:[{system:'barcode',value:'001234'}],ingredientConcepts:[],ingredientMappingStatus:'unresolved',qualificationStatus:'unknown'},
  provenance:{sourceId:source,releaseId:'invented-source-1',visibility:'public',license:'Invented fixture only',attribution:'Synthetic test'},
  curation:{schema:'offmenu-curation/1',rawSourcePayloadPublished:false,humanReviewed:false,automaticDietQualification:false}};
 const releaseId='invented-consumer-1';
 function file(key,text){const bytes=gzipSync(text);files.push({key,bytes:bytes.length,sha256:sha(bytes)});blobs.set(origin+'/releases/'+releaseId+'/'+key,bytes);}
 file('barcodes/'+sha('001234').slice(0,3)+'.jsonl.gz',JSON.stringify(['001234',{[source]:[0]}])+'\n');
 file('entries-0.json.gz',JSON.stringify([{id:0,source,key:row.id,shard:'a',kinds:['product'],countries:[]}]));
 file('records/'+source+'/a.jsonl.gz',JSON.stringify([row.id,[row]])+'\n');
 const manifest={format:'offmenu-curated/1',status:'curated-release-ready',privateProviderData:false,acquisitionAtRuntime:false,
  // This existing serving marker is synthetic; independentAcceptance stays false.
  curatedAcceptance:{status:'all-curated-records-exercised'},releaseId,manifestSha256:'a'.repeat(64),
  entryPageSize:1000,shardLength:3,sources:{[source]:{records:1,normalizedLocalRecords:1,license:'Invented fixture only',entryRange:[0,1]}},files};
 const bytes=Buffer.from(JSON.stringify(manifest)+'\n');blobs.set(origin+'/manifest.json',bytes);
 return {blobs,manifest,row,selection:{releaseId,manifestSha256:sha(bytes)}};
}
function request(source='off',selection=null,extra=''){
 const params=new URLSearchParams({source,barcode:'001234',...selection});
 return new Request('https://offmenu.example/api/data/public?'+params+extra);
}
function fetchFixture(t,f,{missing=false,upstream=false}={}){
 const calls={curated:[],upstream:[]};
 t.mock.method(globalThis,'fetch',async input=>{
  const url=String(input);
  if(url.startsWith(origin+'/')){calls.curated.push(url);const bytes=f?.blobs.get(url);return bytes&&!missing?new Response(bytes):new Response('missing',{status:404});}
  calls.upstream.push(url);
  if(!upstream)throw Error('Unexpected upstream request');
  return Response.json(url.includes('prices.openfoodfacts.org')?{items:[]}:{status:0});
 });
 return calls;
}
for(const source of ['off','prices']){
 test(source+': selected release with no configured curation never fetches upstream',async t=>{
  const f=fixture(source),calls=fetchFixture(t,f);
  const response=await providerDataRoutes(request(source,f.selection),{},options);
  assert.equal(response.status,503);assert.deepEqual(calls,{curated:[],upstream:[]});
 });
 test(source+': missing curated manifest never falls through',async t=>{
  const f=fixture(source),calls=fetchFixture(t,f,{missing:true});
  const response=await providerDataRoutes(request(source,f.selection),{CURATED_CORPUS_ORIGIN:origin},options);
  assert.equal(response.status,503);assert.equal(calls.curated.length,1);assert.deepEqual(calls.upstream,[]);
 });
 test(source+': ordinary unselected request retains existing live fallback',async t=>{
  const calls=fetchFixture(t,null,{upstream:true});
  const response=await providerDataRoutes(request(source),{},options);
  assert.equal(response.status,200);assert.equal(calls.upstream.length,1);assert.deepEqual(calls.curated,[]);
 });
}
test('malformed, partial and duplicate bindings fail before all fetches',async t=>{
 const f=fixture(),calls=fetchFixture(t,f);
 for(const selection of [{releaseId:f.selection.releaseId},{manifestSha256:f.selection.manifestSha256},{releaseId:'',manifestSha256:f.selection.manifestSha256},{...f.selection,manifestSha256:'not-a-hash'}])assert.equal((await providerDataRoutes(request('off',selection),{},options)).status,400);
 assert.equal((await providerDataRoutes(request('off',f.selection,'&releaseId=other'),{},options)).status,400);
 assert.deepEqual(calls,{curated:[],upstream:[]});
});
test('release ID mismatch fails before shard reads and upstream',async t=>{
 const f=fixture(),calls=fetchFixture(t,f);
 const response=await providerDataRoutes(request('off',{...f.selection,releaseId:'other'}),{CURATED_CORPUS_ORIGIN:origin},options);
 assert.equal(response.status,409);assert.equal(calls.curated.length,1);assert.deepEqual(calls.upstream,[]);
});
test('exact manifest bytes required, not its self-declared manifest hash',async t=>{
 const f=fixture(),calls=fetchFixture(t,f);
 const response=await providerDataRoutes(request('off',{...f.selection,manifestSha256:f.manifest.manifestSha256}),{CURATED_CORPUS_ORIGIN:origin},options);
 assert.equal(response.status,409);assert.equal(calls.curated.length,1);assert.deepEqual(calls.upstream,[]);
});
test('source absent from matching release fails closed',async t=>{
 const f=fixture('off'),calls=fetchFixture(t,f);
 const response=await providerDataRoutes(request('prices',f.selection),{CURATED_CORPUS_ORIGIN:origin},options);
 assert.equal(response.status,503);assert.equal(calls.curated.length,1);assert.deepEqual(calls.upstream,[]);
});
test('matching release uses existing checksummed barcode engine without promoting acceptance',async t=>{
 const f=fixture(),calls=fetchFixture(t,f);
 const response=await providerDataRoutes(request('off',f.selection),{CURATED_CORPUS_ORIGIN:origin},options),body=await response.json();
 assert.equal(response.status,200);assert.deepEqual(body.records,[f.row]);assert.equal(body.releaseId,f.selection.releaseId);assert.equal(body.manifestSha256,f.selection.manifestSha256);assert.equal(body.coverage.independentAcceptance,false);assert.equal(body.records[0].data.qualificationStatus,'unknown');assert.equal(calls.curated.length,4);assert.deepEqual(calls.upstream,[]);
});
test('ordinary matching curated response retains original shape',async t=>{
 const f=fixture(),calls=fetchFixture(t,f);
 const response=await providerDataRoutes(request(),{CURATED_CORPUS_ORIGIN:origin},options),body=await response.json();
 assert.equal(response.status,200);assert.deepEqual(body.records,[f.row]);assert.equal(Object.hasOwn(body,'manifestSha256'),false);assert.deepEqual(calls.upstream,[]);
});
test('missing selected record shard fails closed without upstream',async t=>{
 const f=fixture(),calls=fetchFixture(t,f);f.blobs.delete(origin+'/releases/'+f.selection.releaseId+'/records/off/a.jsonl.gz');
 const response=await providerDataRoutes(request('off',f.selection),{CURATED_CORPUS_ORIGIN:origin},options);
 assert.equal(response.status,503);assert.deepEqual(calls.upstream,[]);
});
test('cached manifest bytes are checked before selected query-cache reads',async t=>{
 const f=fixture(),calls=fetchFixture(t,f),keys=[];
 const previous=Object.getOwnPropertyDescriptor(globalThis,'caches');
 Object.defineProperty(globalThis,'caches',{configurable:true,value:{default:{async match(key){keys.push(key);return new Response(f.blobs.get(origin+'/manifest.json'));},async put(){}}}});
 t.after(()=>{if(previous)Object.defineProperty(globalThis,'caches',previous);else delete globalThis.caches;});
 const response=await providerDataRoutes(request('off',{...f.selection,manifestSha256:'0'.repeat(64)}),{CURATED_CORPUS_ORIGIN:origin},options);
 assert.equal(response.status,409);assert.deepEqual(keys,[origin+'/manifest.json']);assert.deepEqual(calls,{curated:[],upstream:[]});
});

test('selected empty barcode result remains scoped and never fetches upstream',async t=>{
 const f=fixture(),calls=fetchFixture(t,f);
 const response=await providerDataRoutes(new Request(request('off',f.selection).url.replace('001234','999999')),{CURATED_CORPUS_ORIGIN:origin},options),body=await response.json();
 assert.equal(response.status,200);assert.deepEqual(body.records,[]);assert.equal(body.manifestSha256,f.selection.manifestSha256);assert.deepEqual(calls.upstream,[]);
});
test('country prefilter cannot bypass selected release qualification',async t=>{
 const f=fixture(),calls=fetchFixture(t,f);
 const response=await providerDataRoutes(request('ciqual',f.selection,'&country=US'),{},options);
 assert.equal(response.status,503);assert.deepEqual(calls,{curated:[],upstream:[]});
 const ordinary=await providerDataRoutes(request('ciqual',null,'&country=US'),{},options);
 assert.equal(ordinary.status,200);assert.deepEqual((await ordinary.json()).records,[]);
});

// PR60 P2: invalid client input keeps its category after release verification.
const encodedCursor=value=>Buffer.from(JSON.stringify(value)).toString('base64url');
const matchingCursor={release:'a'.repeat(64),filters:sha(JSON.stringify(['off','','001234','',''])),offset:0};
const invalidClientInputs=[
 ['barcode',params=>params.set('barcode','not-digits')],
 ['kind',params=>params.set('kind','bad-kind')],
 ['malformed cursor',params=>params.set('cursor','not-valid-json')],
 ['null cursor payload',params=>params.set('cursor',encodedCursor(null))],
 ['negative cursor offset',params=>params.set('cursor',encodedCursor({...matchingCursor,offset:-1}))],
 ['out-of-range cursor',params=>params.set('cursor',encodedCursor({...matchingCursor,offset:2}))],
 ['foreign search cursor',params=>params.set('cursor',encodedCursor({...matchingCursor,filters:sha('another search')}))],
 ['foreign release cursor',params=>params.set('cursor',encodedCursor({...matchingCursor,release:'other'}))],
];
for(const [name,change] of invalidClientInputs){
 test('selected '+name+' is a client400 with zero upstream requests',async t=>{
  const f=fixture(),calls=fetchFixture(t,f),url=new URL(request('off',f.selection).url);change(url.searchParams);
  const response=await providerDataRoutes(new Request(url),{CURATED_CORPUS_ORIGIN:origin},options);
  assert.deepEqual(calls.upstream,[]);assert.equal(response.status,400);
 });
}
test('ordinary client validation remains400 for same invalid inputs',async t=>{
 const f=fixture(),calls=fetchFixture(t,f);
 for(const [,change] of invalidClientInputs){
  const url=new URL(request().url);change(url.searchParams);
  assert.equal((await providerDataRoutes(new Request(url),{CURATED_CORPUS_ORIGIN:origin},options)).status,400);
 }
 assert.deepEqual(calls.upstream,[]);
});
