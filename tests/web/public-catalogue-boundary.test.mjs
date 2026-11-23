import {test} from 'node:test';
import assert from 'node:assert/strict';
import {createOffMenuHandler} from '../../apps/web/server/handler.mjs';
import {isPublicCatalogueHeld,heldPublicIdentifier,heldPublicDetails} from '../../apps/web/src/public-catalogue-boundary.js';

const origin='https://local.invalid';
const withheld=[
 '/api/product?barcode=00123456','/api/prices?barcode=00123456','/api/recipes',
 '/api/data/public?source=example','/api/data/public?releaseId=unadmitted&manifestSha256='+ 'a'.repeat(64),
 '/api/data/coverage','/api/data/sources',
 '/api/catalogue/coverage','/api/catalogue/records','/api/catalogue/country',
 '/api/catalogue/enrich','/api/catalogue/calculate','/api/catalogue/compare',
 '/api/off-photos/not-a-photo','/recipes.json?v=stale','/afcd-nutrient-details.json?v=stale',
 '/recipes/manifest.json','/recipes/prior-edition/page.json',
 '/__dev/identifiers','/__dev/identifiers/status',
];

test('public data routes stop before any identity, storage, provider, or body access',async()=>{
 const original=globalThis.fetch;
 const reads=[];
 const field=name=>{reads.push(String(name));throw Error('Unexpected effect: '+String(name));};
 const env=new Proxy({}, {get:(_t,key)=>field(key)});
 const requestOptions=(method,withIdentity)=>({method,headers:withIdentity?{Authorization:'Bearer invented',Cookie:'local=fixture'}:{}});
 try{
  globalThis.fetch=()=>field('fetch');
  const handler=createOffMenuHandler({ownedBackupRoute:()=>field('backup routing')});
  for(const path of withheld){
   for(const [method,withIdentity] of [['GET',false],['POST',true]]){
    const response=await handler.fetch(new Request(origin+path,requestOptions(method,withIdentity)),env);
    assert.equal(response.status,503,path);
    assert.equal(response.headers.get('Cache-Control'),'no-store',path);
    assert.equal(response.headers.get('X-Content-Type-Options'),'nosniff',path);
    assert.deepEqual(await response.json(),{code:'catalogue_unavailable',error:'Public catalogue unavailable.'},path);
   }
  }
  assert.deepEqual(reads,[]);
 }finally{globalThis.fetch=original;}
});

test('route boundary excludes authenticated domains, exact lookalikes, and the app shell',()=>{
 for(const path of ['/','/app.js','/shelf-scanner.html','/api/state','/api/session',
  '/api/data/schema','/api/data/connections','/api/data/lookup','/api/data/records',
  '/api/catalogue/evaluate','/api/catalogue/lot-restriction','/api/personal/settings',
  '/api/v1/inventory','/mcp','/oauth/authorize','/openapi.json',
  '/api/prices-not-the-route','/recipes-v2/some-file.json','/__dev/identifiers-other']){
  assert.equal(isPublicCatalogueHeld(path),false,path);
 }
});

test('the actual public shelf capture preserves the literal without attempting or reporting a lookup',async()=>{
 const {readFile}=await import('node:fs/promises');
 const {runInNewContext}=await import('node:vm');
 const source=await readFile(new URL('../../apps/web/src/shelf-scanner.js',import.meta.url),'utf8');
 assert.match(source,/import \{heldPublicIdentifier as lookupIdentifiers,heldPublicDetails as loadSelectedDetails\} from '\.\/public-catalogue-boundary\.js';/);
 const a=source.indexOf('async function capture(');
 const b=source.indexOf('function showMatches()',a);
 assert(a>=0&&b>a);
 const fail=()=>assert.fail('Unexpected lookup, authority, or identifier effect');
 const scope={active:true,paused:false,processed:new Set(),CAPTURE_FORMATS:{},generation:0,
  queue:[],current:null,selected:null,mode:'audit',requestedSourceReference:null,
  sheetTouched:true,connection:'live',scanner:{noteAccepted:fail},render(){},readTone(){},
  lookupIdentifiers:heldPublicIdentifier,loadSelectedDetails:heldPublicDetails,inspectMatch:fail,
  resolveSavedResult:fail,fetch:fail,message:fail};
 const capture=runInNewContext(source.slice(a,b)+'\ncapture',scope);
 await capture('0004','typed',null,'invented-occurrence');
 assert.equal(scope.current.raw,'0004');
 assert.equal(scope.current.original,'0004');
 assert.equal(scope.current.status,'unavailable');
 assert.equal(scope.current.error,'catalogue_unavailable');
 assert.equal(scope.current.matches.length,0);
 assert.equal(scope.current.hasMore,false);
 assert.equal(scope.selected,null);
});

test('normal Demo restores only new own recipe imports, never the old shared snapshot',async()=>{
 const {readFile}=await import('node:fs/promises');
 const {runInNewContext}=await import('node:vm');
 const source=await readFile(new URL('../../apps/web/src/app.js',import.meta.url),'utf8');
 assert.match(source,/RECIPES=demoMode\?'offmenu-recipes-v1-demo-local':'offmenu-recipes-v1'\+suffix/);
 const helper=source.split('\n').find(line=>line.startsWith('function readDemoOwnRecipes('));
 const line=source.split('\n').find(line=>line.startsWith('async function enterDemo('));
 const guarded=line?.match(/if\(lifecycleFixture\)\{recipes=validateRecipes\(await jsonFetch\('[^']+'\)\);localStorage\.setItem\(RECIPES,JSON\.stringify\(recipes\)\);\}else recipes=readDemoOwnRecipes\(\);/);
 assert(helper&&guarded);
 let requests=0,writes=0;
 const own='offmenu-recipes-v1-demo-local',oldDemo='offmenu-recipes-v1-demo',guest='offmenu-recipes-v1';
 const store=new Map([[oldDemo,'[{"id":"old-shared"}]'],[guest,'[{"id":"guest-only"}]']]);
 const reads=[];
 const env={lifecycleFixture:false,recipes:[{id:'previous-scope'}],RECIPES:own,
  async jsonFetch(){requests++;return [{id:'fixture'}];},validateRecipes:r=>r,localStorage:{
   getItem(k){reads.push(k);return store.get(k);},setItem(k,v){writes++;store.set(k,v);}
  }};
 const run=()=>runInNewContext(helper+'\n(async()=>{'+guarded[0]+'})()',env);
 await run();assert.equal(env.recipes.length,0);assert.deepEqual(reads,[own]);assert.equal(writes,0);
 store.set(own,'[{"id":"explicit-local-import"}]');
 await run();assert.equal(env.recipes[0].id,'explicit-local-import');
 assert.deepEqual(reads,[own,own]);assert.equal(writes,0);assert.equal(requests,0);
 assert.equal(store.get(oldDemo),'[{"id":"old-shared"}]');assert.equal(store.get(guest),'[{"id":"guest-only"}]');
 env.lifecycleFixture=true;await run();assert.equal(env.recipes[0].id,'fixture');assert.equal(requests,1);assert.equal(writes,1);
});

test('public app startup does not mount shared recipe discovery or a stored scanner provider handoff',async()=>{
 const {readFile}=await import('node:fs/promises');
 const s=await readFile(new URL('../../apps/web/src/app.js',import.meta.url),'utf8');
 assert.match(s,/let pendingScannerImport=null/);
 assert.equal((s.match(/\breadScannerImport\(/g)||[]).length,1,'detached parser definition only');
 assert.doesNotMatch(s,/\bsetupRecipeLibrary\(/);
 assert.equal((s.match(/\bstoreReviewedRecipe\(/g)||[]).length,1,'detached durable save contract only');
});
