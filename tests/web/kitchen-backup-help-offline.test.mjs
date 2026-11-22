import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {test} from 'node:test';
import {fileURLToPath} from 'node:url';
import vm from 'node:vm';
import {build} from 'esbuild';
import {rankedTopics} from '../../apps/web/assets/help.js';

const origin='https://offmenu.test';
const previous='offmenu-shell-v12';
const current='offmenu-shell-v13';
const basePaths=['/','/app.js?v=i18n-1','/scanner-worker.js','/scanner-theme-init.js','/scanner.wasm','/style.css?v=i18n-1','/offmenu-tokens.css','/recipes.json?v=i18n-1','/data-workspace.html','/data-workspace.js?v=i18n-1','/afcd-nutrient-details.json','/icon.svg','/receipt-bars.svg','/manifest.webmanifest','/manifest-ar.webmanifest','/offmenu-neon.css','/offmenu-neon.svg','/offmenu-neon-material.jpg'];
const helpPaths=['/help.html','/help.css','/help.js'];
const helpBytes=new Map(helpPaths.map(path=>[path,readFileSync(new URL('../../apps/web/assets'+path,import.meta.url),'utf8')]));
const worker=(await build({
  entryPoints:[fileURLToPath(new URL('../../apps/web/src/sw.js',import.meta.url))],
  bundle:true,minify:true,format:'iife',write:false
})).outputFiles[0].text;

// This is a deterministic lifecycle contract test, not an installed worker. The
// mock stages successful responses before atomically recording addAll and lets a
// test explicitly deliver activate only after a successful install.
function fixture({upgrading=false,missing}={}){
  const buckets=new Map(), handlers=new Map(), seen={loads:[],preloads:[],deleted:[],wait:0,claim:0};
  const unrelated='other-app-cache';
  if(upgrading) {
    buckets.set(previous,new Map([[origin+'/',new Response('v12 retained guest shell')]]));
    buckets.set(unrelated,new Map());
  }
  let online=true;
  const key=(request,ignoreSearch=false)=>{
    const u=new URL(typeof request==='string'?request:request.url,origin);
    u.hash='';
    if(ignoreSearch)u.search='';
    return u.href;
  };
  const fetchFixture=async request=>{
    const u=new URL(key(request));
    assert.equal(u.origin,origin,'worker must never fetch a foreign origin');
    seen.loads.push(u.pathname+u.search);
    if(!online)throw new Error('mock disconnected');
    if(u.pathname===missing)return new Response('missing fixture',{status:404});
    return new Response(helpBytes.get(u.pathname)??'fixture shell '+u.pathname);
  };
  const caches={
    async open(name){
      if(!buckets.has(name))buckets.set(name,new Map());
      const bucket=buckets.get(name);
      return {async addAll(paths){
        seen.preloads.push(Array.from(paths));
        const pending=await Promise.all(paths.map(async path=>{
          const result=await fetchFixture(path);
          if(!result.ok)throw new Error('precache rejected '+path);
          return [key(path),result];
        }));
        for(const [url,response] of pending)bucket.set(url,response);
      }};
    },
    async keys(){return [...buckets.keys()];},
    async delete(name){seen.deleted.push(name);return buckets.delete(name);},
    async match(request,{ignoreSearch}={}){
      for(const bucket of buckets.values()){
        for(const [url,response] of bucket)
          if(key(url,ignoreSearch)===key(request,ignoreSearch))return response.clone();
      }
    }
  };
  const self={location:new URL(origin),clients:{claim(){seen.claim++;}},
    skipWaiting(){seen.wait++;},addEventListener(name,cb){handlers.set(name,cb);}};
  vm.runInNewContext(worker,{self,caches,fetch:fetchFixture,Response,URL});
  return {buckets,seen,unrelated,disconnect(){online=false;},phase(name){
    let completion;
    handlers.get(name)({waitUntil(p){assert.equal(completion,undefined);completion=p;}});
    assert(completion,'lifecycle phase must await its work');
    return completion;
  },request(path,{method='GET',headers={}}={}){
    let result;
    handlers.get('fetch')({request:new Request(new URL(path,origin),{method,headers}),
      respondWith(p){assert.equal(result,undefined);result=p;}});
    return result;
  }};
}

async function expectOfflineHelp(f){
  f.disconnect();
  for(const path of ['/help.html?uiLanguage=ar#account-backup',...helpPaths]){
    const response=await f.request(path);
    assert.equal(response.status,200,path);
    assert.equal(await response.text(),helpBytes.get(new URL(path,origin).pathname),path);
  }
}

test('fresh install precaches only the existing shell plus the three exact Help assets',async()=>{
  const f=fixture();
  await f.phase('install');
  assert.equal(f.seen.preloads.length,1);
  assert.deepEqual(f.seen.preloads[0].slice().sort(),[...basePaths,...helpPaths].sort());
  assert.equal(f.buckets.get(current)?.size,basePaths.length+helpPaths.length);
  assert.equal(f.seen.wait,1);
  assert.equal(f.seen.claim,0);
  await f.phase('activate');
  assert.equal(f.seen.claim,1);
  await expectOfflineHelp(f);
});

test('an upgrade retains the warm v12 Guest shell until v13 is installed and activated',async()=>{
  const f=fixture({upgrading:true});
  await f.phase('install');
  assert(f.buckets.has(current));
  assert.equal(await f.buckets.get(previous).get(origin+'/').clone().text(),'v12 retained guest shell');
  assert.deepEqual(f.seen.deleted,[]);
  assert.equal(f.seen.claim,0);
  await f.phase('activate');
  assert.deepEqual(f.seen.deleted,[previous]);
  assert(f.buckets.has(f.unrelated));
  assert.equal(f.seen.claim,1);
  await expectOfflineHelp(f);
});

for(const missing of helpPaths)test('missing '+missing+' cannot displace the warm v12 cache',async()=>{
  const f=fixture({upgrading:true,missing});
  await assert.rejects(f.phase('install'),error=>error.message==='precache rejected '+missing);
  assert.equal(f.seen.wait,0);
  assert.equal(f.seen.claim,0);
  assert.deepEqual(f.seen.deleted,[]);
  assert.equal(f.buckets.get(current)?.size,0);
  assert.equal(await f.buckets.get(previous).get(origin+'/').clone().text(),'v12 retained guest shell');
});

test('non-GET, off-origin and existing excluded authority paths are not intercepted',()=>{
  const f=fixture();
  for(const path of ['/api/session','/.netlify/functions/session','/oauth/callback','/.well-known/openid-configuration','/mcp','/openapi.json','https://other.test/help.html'])
    assert.equal(f.request(path),undefined,path);
  assert.equal(f.request('/help.html',{method:'POST'}),undefined);
  assert.deepEqual(f.seen.loads,[]);
});

test('the cached Help shell still uses one exact anchor and bounds local search input',()=>{
  const html=helpBytes.get('/help.html');
  assert.match(html,/<input id="query"[^>]+maxlength="160"/);
  assert.deepEqual([...html.matchAll(/<article id="([^"]+)"/g)].map(x=>x[1]),['account-backup','recipe-import']);
  const topics=[{id:'account-backup',title:'Kitchen backup',aliases:['restore'],summary:'Back up your kitchen',body:'Backup and restore'}];
  assert.deepEqual(rankedTopics(topics,'backup'+' '.repeat(154)+'shopping'),topics);
  assert.deepEqual(rankedTopics(topics,' '.repeat(160)+'backup'),[]);
});
