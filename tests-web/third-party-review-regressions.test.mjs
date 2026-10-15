import test from 'node:test';
import assert from 'node:assert/strict';
import {DatabaseSync} from 'node:sqlite';
import {readFileSync} from 'node:fs';
import handler from '../cloud/handler.mjs';

test('static assets and unknown paths do not read administrative settings',async()=>{
 const previous=globalThis.ASSETS;
 globalThis.ASSETS={'app.js':'export {};','style.css':'body{}','icon.svg':'<svg/>','recipes.json':'[]','scanner.wasm':'AGFzbQ=='};
 const queries=[],env={DB:{prepare(sql){queries.push(sql);return {first:async()=>null};}}};
 try{
  for(const path of ['/app.js','/style.css','/icon.svg','/recipes.json','/scanner.wasm','/missing-file','/missing.html']){
   queries.length=0;const response=await handler.fetch(new Request('https://offmenu.test'+path),env);
   assert.equal(response.status,path.startsWith('/missing')?404:200,path);
   assert.deepEqual(queries,[],path+' must not query D1');
  }
 }finally{if(previous===undefined)delete globalThis.ASSETS;else globalThis.ASSETS=previous;}
});

test('scheduled cleanup deletes expired direct and OAuth proofs but preserves live proofs',async()=>{
 const db=new DatabaseSync(':memory:');db.exec(readFileSync(new URL('../cloud/schema.sql',import.meta.url),'utf8'));db.exec(readFileSync(new URL('../cloud/catalogue-schema.sql',import.meta.url),'utf8'));
 const now=Date.now();for(const table of ['admin_mcp_proofs','oauth_admin_proofs']){
  const key=table==='admin_mcp_proofs'?'token_id':'code_hash';
  db.prepare(`INSERT INTO ${table}(${key},sealed,expires_at) VALUES(?,?,?)`).run('expired','synthetic expired ciphertext',now-60000);
  db.prepare(`INSERT INTO ${table}(${key},sealed,expires_at) VALUES(?,?,?)`).run('live','synthetic live ciphertext',now+60000);
 }
 const statement=(sql,args=[])=>({bind(...values){return statement(sql,values);},async first(){return db.prepare(sql).get(...args)||null;},async all(){return {results:db.prepare(sql).all(...args)};},async run(){return db.prepare(sql).run(...args);},sql,args});
 const env={DB:{prepare:sql=>statement(sql),async batch(items){return items.map(item=>({meta:db.prepare(item.sql).run(...item.args)}));}}},pending=[];
 try{
  await handler.scheduled({},env,{waitUntil(promise){pending.push(promise);}});await Promise.all(pending);
  for(const table of ['admin_mcp_proofs','oauth_admin_proofs'])assert.deepEqual(db.prepare(`SELECT sealed FROM ${table}`).all().map(row=>row.sealed),['synthetic live ciphertext']);
 }finally{db.close();}
});
