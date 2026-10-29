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
test('current workerd redirect contract accepts the default fetch without forwarding incoming credentials',async t=>{
 const f=await fixture(),saved=globalThis.fetch,calls=[],events=[];t.after(()=>{globalThis.fetch=saved;});
 globalThis.fetch=function(url,options){
  assert.equal(this,globalThis);
  // Mirrors current Cloudflare Request::tryParseRedirect: follow/manual only.
  if(!['follow','manual'].includes(options.redirect))throw new TypeError('unsupported-redirect-mode');
  calls.push({url,options});if(url===f.selection.manifestUrl)return Promise.resolve(new Response(f.manifest));
  if(url===ORIGIN+PREFIX+'shards/'+f.prefix+'.json.gz')return Promise.resolve(new Response(f.compressed));
  throw Error('untrusted-url');
 };
 const incoming=new Request(req(),{headers:{Cookie:'synthetic-must-not-forward',Authorization:'Bearer synthetic-must-not-forward',
  'X-Private-Synthetic':'must-not-forward'}});
 const response=await createSourceBarcodeHandler({selection:f.selection,onDiagnostic:e=>events.push(e)})(incoming);
 assert.equal(response.status,200);assert.equal((await response.json()).status,'source-key-not-found');assert.equal(calls.length,2);assert.deepEqual(events,[]);
 for(const {url,options} of calls){const parsed=new URL(url);assert.equal(parsed.origin,ORIGIN);assert.equal(parsed.username,'');assert.equal(parsed.password,'');
  assert.equal(options.redirect,'manual');assert.equal(options.credentials,'omit');assert.equal(options.cache,'no-store');assert.equal(options.method,'GET');
  assert.deepEqual(Object.keys(options.headers).sort(),['Accept','Accept-Encoding']);assert.equal(options.headers['Accept-Encoding'],'identity');
  assert.ok(options.signal instanceof AbortSignal);assert.equal(JSON.stringify(options).includes('synthetic-must-not-forward'),false);}
});
test('manual redirect is rejected without following target, copying Set-Cookie, or weakening integrity',async()=>{
 const f=await fixture(),events=[];let calls=0;
 const response=await createSourceBarcodeHandler({selection:f.selection,onDiagnostic:e=>events.push(e),fetchImpl:async(url,options)=>{
  calls++;assert.equal(url,f.selection.manifestUrl);assert.equal(options.redirect,'manual');
  return new Response('synthetic',{status:302,headers:{Location:'https://untrusted.example/','Set-Cookie':'synthetic=never-forward'}});
 }})(req());
 assert.equal(response.status,503);assert.equal((await response.json()).status,'index-unavailable');assert.equal(response.headers.get('set-cookie'),null);
 assert.equal(calls,1);assert.equal(events[0].stage,'manifest-fetch');assert.equal(events[0].code,'http');
});
test('supported manual fetch preserves cancellation and original absolute budget, without fallback',async t=>{
 const f=await fixture(),saved=globalThis.fetch,events=[];let signal,calls=0;t.after(()=>{globalThis.fetch=saved;});
 t.mock.timers.enable({apis:['setTimeout','Date']});t.after(()=>t.mock.timers.reset());
 globalThis.fetch=function(url,options){assert.equal(this,globalThis);assert.equal(options.redirect,'manual');signal=options.signal;calls++;return new Promise(()=>{});};
 const pending=createSourceBarcodeHandler({selection:f.selection,onDiagnostic:e=>events.push(e)})(req());
 await Promise.resolve();await Promise.resolve();t.mock.timers.tick(RESOURCE_BOUNDS.deadlineMs+1);
 const response=await pending;assert.equal(response.status,503);assert.equal((await response.json()).status,'index-unavailable');
 assert.equal(calls,1);assert.equal(signal.aborted,true);assert.equal(events[0].code,'cancelled-or-deadline');
});
