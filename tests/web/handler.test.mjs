import test from 'node:test';
import assert from 'node:assert/strict';
import {DatabaseSync} from 'node:sqlite';
import {readFileSync} from 'node:fs';
import handler from '../../apps/web/server/handler.mjs';
const db=new DatabaseSync(':memory:');db.exec(readFileSync(new URL('../../apps/web/server/schema.sql',import.meta.url),'utf8'));
const env={DB:{prepare(sql){return {bind(...args){return {async first(){return db.prepare(sql).get(...args)||null;},async run(){return db.prepare(sql).run(...args);}}},async all(){return {results:db.prepare(sql).all()};}}}}};
const original=globalThis.fetch;
globalThis.fetch=async(url,options)=>url.endsWith('/user')?Response.json(options.headers.Authorization==='Bearer alice'?{id:'alice'}:options.headers.Authorization==='Bearer bob'?{id:'bob'}:{error:'Unauthorized'},{status:['Bearer alice','Bearer bob'].includes(options.headers.Authorization)?200:401}):original(url,options);
const state={inventory:[],products:{},recipes:[],profile:{country:'AU',units:'metric',servings:2},selections:[]};
function req(method,token,body,origin='https://offmenu.aldous.info'){return new Request('https://offmenu.aldous.info/api/state',{method,headers:{Authorization:'Bearer '+token,Origin:origin,'Content-Type':'application/json'},body:body?JSON.stringify(body):undefined});}
test('authentication, ownership, atomic revision conflicts and CSRF',async()=>{
 assert.equal((await handler.fetch(req('GET','invalid'),env)).status,401);
 assert.equal((await handler.fetch(req('PUT','alice',{revision:0,state}),env)).status,200);
 assert.equal((await handler.fetch(req('PUT','alice',{revision:0,state}),env)).status,409);
 const alice=await(await handler.fetch(req('GET','alice'),env)).json();assert.equal(alice.revision,1);assert.equal(alice.state.profile.country,'AU');
 const bob=await(await handler.fetch(req('GET','bob'),env)).json();assert.equal(bob.state,null);
 assert.equal((await handler.fetch(req('PUT','alice',{revision:1,state},'https://other.example'),env)).status,403);
 assert.equal((await handler.fetch(req('PUT','alice',{revision:1,state}),env)).status,200);
 assert.equal((await handler.fetch(req('PUT','alice',{revision:1,state}),env)).status,409);
});
