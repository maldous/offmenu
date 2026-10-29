import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import test from 'node:test';
import { DatabaseSync } from 'node:sqlite';
import { careUpdateRoutes, notifyCare } from '../../cloud/care-updates.mjs';

function database(){
 const sqlite=new DatabaseSync(':memory:');sqlite.exec(readFileSync(new URL('../../cloud/care-updates-schema.sql',import.meta.url),'utf8'));
 const statement=sql=>({bind(...args){const query=sqlite.prepare(sql);return {first:async()=>query.get(...args)||null,all:async()=>({results:query.all(...args)}),run:async()=>query.run(...args)};}});
 return {sqlite,DB:{prepare:statement,batch:async statements=>Promise.all(statements.map(statement=>statement.all?.()))}};
}
const admin={id:'admin-000000000001',app_metadata:{roles:['admin']}}, owner={id:'owner-000000000001'};
const reply=(data,status=200)=>Response.json(data,{status});
const call=(env,url,{method='GET',user,body}={})=>careUpdateRoutes(new Request('https://app.example'+url,{method,headers:method==='GET'?{}:{Origin:'https://app.example','content-type':'application/json'},body:body&&JSON.stringify(body)}),env,{verifiedUser:async()=>user||null,boundedJSON:request=>request.json(),reply});

test('scheduled publication visibility is locale-specific and guest-safe',async()=>{
 const env=database(),future=new Date(Date.now()+3600000).toISOString(),past=new Date(Date.now()-1000).toISOString();
 let response=await call(env,'/api/admin/care/updates',{method:'POST',user:admin,body:{idempotencyKey:'a'.repeat(16),confirmed:true,title:'English update',text:'Safe generic update',locale:'en',publishAt:future}});assert.equal(response.status,201);let update=(await response.json()).update;
 response=await call(env,'/api/admin/care/updates/'+update.id,{method:'PUT',user:admin,body:{revision:1,confirmed:true,action:'publish',publishAt:past}});assert.equal(response.status,200);
 response=await call(env,'/api/care/updates?locale=en');assert.equal(response.status,200);assert.equal((await response.json()).updates.length,1);
 response=await call(env,'/api/care/updates?locale=ar');assert.equal((await response.json()).updates.length,0);
});

test('preferences are owner-only, notifications are generic, and unsubscribe prevents new updates',async()=>{
 const env=database();let response=await call(env,'/api/care/preferences',{method:'PUT',user:owner,body:{revision:0,caseNotifications:true,communityNotifications:true,updateNotifications:false,emailUpdates:false}});assert.equal(response.status,200);
 assert.equal(await notifyCare(env,owner.id,'update','b'.repeat(36)),false);
 assert.equal(await notifyCare(env,owner.id,'case','c'.repeat(36)),true);
 response=await call(env,'/api/care/notifications',{user:owner});const body=await response.json();assert.equal(body.notifications.length,1);assert.deepEqual(Object.keys(body.notifications[0]).sort(),['createdAt','id','kind','resourceId','seenAt']);
 response=await call(env,'/api/care/notifications/mark-seen',{method:'PUT',user:{id:'other-owner-000001'},body:{ids:[body.notifications[0].id]}});assert.equal(response.status,200);assert.equal(env.sqlite.prepare('SELECT seen_at FROM care_notifications WHERE owner=?').get(owner.id).seen_at,null);
});

test('admin changes are revision guarded and failed CAS leaves no audit record',async()=>{
 const env=database(),date=new Date(Date.now()-1000).toISOString();let response=await call(env,'/api/admin/care/updates',{method:'POST',user:admin,body:{idempotencyKey:'d'.repeat(16),confirmed:true,title:'Draft',text:'Draft text',locale:'en',publishAt:date}});const update=(await response.json()).update;
 response=await call(env,'/api/admin/care/updates/'+update.id,{method:'PUT',user:admin,body:{revision:99,confirmed:true,action:'publish'}});assert.equal(response.status,409);assert.equal(env.sqlite.prepare('SELECT count(*) AS count FROM care_update_audit WHERE update_id=?').get(update.id).count,1);
 response=await call(env,'/api/admin/care/updates/'+update.id,{method:'PUT',user:admin,body:{revision:1,confirmed:true,action:'publish'}});assert.equal(response.status,200);assert.equal(env.sqlite.prepare('SELECT count(*) AS count FROM care_update_audit WHERE update_id=?').get(update.id).count,2);
});

test('deterministic update notifications remain strictly owner-scoped and can be marked seen',async()=>{
 const env=database(),updateId='11111111-1111-4111-8111-111111111111',now=new Date(Date.now()-1000).toISOString();
 env.sqlite.prepare("INSERT INTO care_updates(id,idempotency_key,payload_hash,title,text,locale,state,publish_at,release_ref,attribution_json,revision,write_id,created_at,updated_at) VALUES(?,?,?,?,?,?,'published',?,?,?,1,?,?,?)").run(updateId,'e'.repeat(16),'hash','Update','Text','en',now,null,'{"kind":"human"}','write',now,now);
 let response=await call(env,'/api/care/notifications',{user:owner});let body=await response.json();assert.equal(body.notifications.length,1);const notification=body.notifications[0];assert.match(notification.id,/^update:/);
 response=await call(env,'/api/care/notifications/mark-seen',{method:'PUT',user:owner,body:{ids:[notification.id]}});assert.equal(response.status,200);assert.notEqual(env.sqlite.prepare('SELECT seen_at FROM care_notifications WHERE id=? AND owner=?').get(notification.id,owner.id).seen_at,null);
 response=await call(env,'/api/care/notifications/mark-seen',{method:'PUT',user:{id:'other-owner-000001'},body:{ids:[notification.id]}});assert.equal(response.status,200);assert.equal(env.sqlite.prepare('SELECT owner FROM care_notifications WHERE id=?').get(notification.id).owner,owner.id);
});
