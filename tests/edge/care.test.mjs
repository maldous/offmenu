import test from 'node:test';
import assert from 'node:assert/strict';
import {Miniflare,createFetchMock} from 'miniflare';
import {readFileSync} from 'node:fs';
import {DatabaseSync} from 'node:sqlite';
test('fresh canonical schema supports compiled care ownership and public recipe moderation',async()=>{
 const mock=createFetchMock();mock.disableNetConnect();
 mock.get('https://offmenu-accounts.netlify.app').intercept({path:'/.netlify/identity/user',method:'GET'}).reply(200,({headers})=>{const id=(headers.authorization||headers.Authorization).replace('Bearer ','');return JSON.stringify({id,app_metadata:{roles:id==='admin'?['admin']:[]},user_metadata:{roles:['admin']}});}).persist();
 const worker=new Miniflare({modules:true,scriptPath:'dist/worker.mjs',compatibilityDate:'2026-08-06',compatibilityFlags:['nodejs_compat'],d1Databases:['DB'],fetchMock:mock,bindings:{PROVIDER_VAULT_KEY:'a'.repeat(64)}});
 try{
  const db=await worker.getD1Database('DB'),schema=new DatabaseSync(':memory:');schema.exec(readFileSync('cloud/schema.sql','utf8'));
  for(const {sql} of schema.prepare("SELECT sql FROM sqlite_master WHERE sql IS NOT NULL AND name NOT LIKE 'sqlite_%' ORDER BY CASE type WHEN 'table' THEN 0 ELSE 1 END").all())await db.prepare(sql).run();schema.close();
  const call=(path,token,method='GET',body)=>worker.dispatchFetch('https://offmenu.test'+path,{method,headers:{...(token?{Authorization:'Bearer '+token}:{}),Origin:'https://offmenu.test','Content-Type':'application/json'},...(body?{body:JSON.stringify(body)}:{})});
  let response=await call('/api/care/cases','alice','POST',{confirmed:true,idempotencyKey:'compiled_case_creation_01',category:'recipe',title:'Correction',message:'The displayed public quantity needs checking.'});assert.equal(response.status,201);const caseId=(await response.json()).case.id;
  assert.equal((await call('/api/care/cases/'+caseId,'bob')).status,404);
  assert.equal((await call('/api/admin/care/cases','bob')).status,403);
  response=await call('/api/care/cases/'+caseId+'/messages','alice','POST',{revision:1,confirmed:true,idempotencyKey:'compiled_case_reply_01',message:'Additional context.'});assert.equal(response.status,201);
  assert.equal((await (await call('/api/admin/care/cases/'+caseId,'admin')).json()).case.messages.length,2);
  const recipe={title:'Toast',description:'Simple toast.',servings:1,ingredients:[{name:'Bread',quantity:2,unit:'slices'}],steps:['Toast bread.'],language:'en',license:'CC BY 4.0'};
  response=await call('/api/community/recipes','alice','POST',{confirmed:true,rightsConfirmed:true,idempotencyKey:'compiled_recipe_create_01',alias:'Cook',recipe,attribution:{kind:'ai',agentName:'Selected Chef'}});assert.equal(response.status,201);const recipeId=(await response.json()).recipeId;
  assert.equal((await (await call('/api/community/recipes')).json()).recipes.length,0);
  assert.equal((await call('/api/admin/community/recipes/'+recipeId,'admin','PUT',{revision:1,confirmed:true,action:'approve',reason:'Reviewed contribution'})).status,200);
  const publicRows=(await (await call('/api/community/recipes')).json()).recipes;assert.equal(publicRows.length,1);assert.equal(publicRows[0].attribution.agentName,'Selected Chef');assert(!JSON.stringify(publicRows).includes('alice'));
  assert.equal((await call('/api/community/recipes/'+recipeId+'/vote','bob','PUT',{value:1,rating:4})).status,200);
  assert.equal((await call('/api/community/recipes/'+recipeId+'/vote','alice','PUT',{value:1,rating:5})).status,403);
 }finally{await worker.dispose();}
});
