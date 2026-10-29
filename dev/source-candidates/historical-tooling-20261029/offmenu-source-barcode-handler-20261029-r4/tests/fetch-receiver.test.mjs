import test from 'node:test';
import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
import {gzipSync} from 'node:zlib';
import {createSourceBarcodeHandler,keySha,ORIGIN,PREFIX,INDEX_RELEASE,PUBLIC_BASE,RESOURCE_BOUNDS} from '../source/source-barcode-handler.mjs';
import {SOURCE_PINS} from '../source/protocol-pins.mjs';
const hash=b=>createHash('sha256').update(b).digest('hex');
const q={source:'synthetic-source',release:'synthetic-release',namespace:'barcode',lexical:'non-food: 001-A'};
const req=()=>new Request('https://offmenu.aldous.info/api/corpus/source-barcode?'+new URLSearchParams({source:q.source,release:q.release,namespace:q.namespace,value:q.lexical}));
async function fixture(){
 const prefix=(await keySha(q)).slice(0,2),decoded=Buffer.from(JSON.stringify({entries:[],prefix,schemaVersion:'offmenu-source-barcode-index-shard/1'})+'\n');
 const compressed=gzipSync(decoded),shards={};for(let i=0;i<256;i++){const p=i.toString(16).padStart(2,'0');shards[p]={path:'shards/'+p+'.json.gz',publicPath:PREFIX+'shards/'+p+'.json.gz',bytes:compressed.length,uncompressedBytes:decoded.length,sha256:hash(compressed),indexedKeys:0};}
 const manifest=Buffer.from(JSON.stringify({schemaVersion:'offmenu-source-barcode-index/1',indexReleaseId:INDEX_RELEASE,complete:true,
 sourcePins:SOURCE_PINS,publicBase:PUBLIC_BASE,candidateReferenceCap:20,keyHash:{algorithm:'SHA256',input:'UTF-8 canonical JSON array [source,release,namespace,lexical]',canonicalJSON:'sorted object keys; no whitespace; ensure_ascii=false; finite JSON',normalization:'none',shardPrefixHexCharacters:2},shards,canonicalIdentityAsserted:false,automaticPlanningEligible:false,nutritionAggregationEligible:false})+'\n');
 return {manifest,compressed,prefix,selection:{manifestUrl:ORIGIN+PREFIX+'manifest.json',manifestSha256:hash(manifest),indexReleaseId:INDEX_RELEASE,sourcePins:SOURCE_PINS,publicBase:PUBLIC_BASE}};
}
test('default fetch preserves host receiver and all trusted URL/security/options through both reads',async t=>{
 const f=await fixture(),saved=globalThis.fetch,calls=[],events=[];t.after(()=>{globalThis.fetch=saved;});
 globalThis.fetch=function(url,options){
  if(this!==globalThis)throw new TypeError('Illegal invocation: function called with incorrect this reference');
  calls.push({url,options});if(url===f.selection.manifestUrl)return Promise.resolve(new Response(f.manifest));
  if(url===ORIGIN+PREFIX+'shards/'+f.prefix+'.json.gz')return Promise.resolve(new Response(f.compressed));
  throw Error('untrusted-url');
 };
 // No fetchImpl injected: this is the actual production factory-default seam.
 const response=await createSourceBarcodeHandler({selection:f.selection,onDiagnostic:e=>events.push(e)})(req());
 assert.equal(response.status,200);const value=await response.json();assert.equal(value.status,'source-key-not-found');assert.equal(value.complete,true);
 assert.equal(calls.length,2);assert.deepEqual(events,[]);
 for(const {url,options} of calls){assert.equal(new URL(url).origin,ORIGIN);assert.equal(options.method,'GET');assert.equal(options.cache,'no-store');
  assert.equal(options.redirect,'error');assert.equal(options.credentials,'omit');assert.equal(options.headers['Accept-Encoding'],'identity');assert.ok(options.signal instanceof AbortSignal);}
});
test('bound default still aborts a stalled fetch at the original deadline with no duplicate fallback',async t=>{
 const f=await fixture(),saved=globalThis.fetch,events=[];let calls=0,signal;
 t.after(()=>{globalThis.fetch=saved;});t.mock.timers.enable({apis:['setTimeout','Date']});t.after(()=>t.mock.timers.reset());
 globalThis.fetch=function(url,options){assert.equal(this,globalThis);calls++;signal=options.signal;return new Promise(()=>{});};
 const pending=createSourceBarcodeHandler({selection:f.selection,onDiagnostic:e=>events.push(e)})(req());
 await Promise.resolve();await Promise.resolve();t.mock.timers.tick(RESOURCE_BOUNDS.deadlineMs+1);
 const response=await pending;assert.equal(response.status,503);assert.equal((await response.json()).status,'index-unavailable');
 assert.equal(calls,1);assert.equal(signal.aborted,true);assert.equal(events[0].stage,'manifest-fetch');assert.equal(events[0].code,'cancelled-or-deadline');
});
