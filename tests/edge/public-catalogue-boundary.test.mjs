import {test} from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {Miniflare,createFetchMock} from 'miniflare';

test('the generated Worker omits held catalogue assets and does not serve or redirect a public data request',async()=>{
 const envelope=readFileSync('apps/web/server/generated.mjs','utf8').split('\n',1)[0];
 for(const path of ['recipes.json','afcd-nutrient-details.json'])assert(!envelope.includes(JSON.stringify(path)+':'),path);
 const mock=createFetchMock();mock.disableNetConnect();
 const worker=new Miniflare({modules:true,scriptPath:'dist/worker.mjs',compatibilityDate:'2026-08-06',compatibilityFlags:['nodejs_compat'],fetchMock:mock});
 try{
  for(const path of ['/recipes.json?v=stale','/afcd-nutrient-details.json?v=stale','/recipes/manifest.json','/api/data/public?source=example','/api/off-photos/held.jpg']){
   const response=await worker.dispatchFetch('https://offmenu.test'+path,{redirect:'manual'});
   assert.equal(response.status,503,path);
   assert.equal(response.headers.get('Cache-Control'),'no-store',path);
   assert.equal(response.headers.get('Location'),null,path);
   assert.equal((await response.json()).code,'catalogue_unavailable',path);
  }
  const response=await worker.dispatchFetch('https://offmenu.test/');
  assert.equal(response.status,200);
  assert.match(await response.text(),/id="landing-title"/);
 }finally{await worker.dispose();}
});
