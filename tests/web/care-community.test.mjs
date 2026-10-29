import test from 'node:test';
import assert from 'node:assert/strict';
import {DatabaseSync} from 'node:sqlite';
import {readFileSync} from 'node:fs';
import {careCommunityRoutes,listCommunityCandidates,moderateCommunityCandidate,cleanupCareCommunity,isCommunityRestricted} from '../../cloud/care-community.mjs';

const database=new DatabaseSync(':memory:');database.exec(readFileSync(new URL('../../cloud/care-community-schema.sql',import.meta.url),'utf8'));database.exec(readFileSync(new URL('../../cloud/recipe-community-schema.sql',import.meta.url),'utf8'));
const queries=[];let beforeBatch=null;
const DB={prepare(sql){queries.push(sql);const make=args=>({async first(){return database.prepare(sql).get(...args)||null;},async all(){return {results:database.prepare(sql).all(...args)};},async run(){return database.prepare(sql).run(...args);},_run(){const statement=database.prepare(sql);if(/^\s*(UPDATE|INSERT|DELETE).*RETURNING/i.test(sql))return {results:statement.all(...args)};const meta=statement.run(...args);return {results:[],meta:{changes:meta.changes}};}});return {...make([]),bind(...args){return make(args);}}},async batch(statements){beforeBatch?.();beforeBatch=null;return statements.map(statement=>statement._run());}};
const env={DB,PROVIDER_VAULT_KEY:'a'.repeat(64)},origin='https://offmenu.example';
const users={alice:{id:'alice',app_metadata:{roles:[]}},bob:{id:'bob',app_metadata:{roles:[]}},admin:{id:'admin',app_metadata:{roles:['offmenu-admin']}},forged:{id:'forged',user_metadata:{roles:['admin']}}};
const options={verifiedUser:async request=>users[request.headers.get('Cookie')]||null,boundedJSON:request=>request.json()};
const request=(path,{method='GET',cookie,body,originHeader=origin}={})=>new Request(origin+path,{method,headers:{...(cookie?{Cookie:cookie}:{}),...(method!=='GET'?{Origin:originHeader,'Content-Type':'application/json'}:{})},...(body===undefined?{}:{body:JSON.stringify(body)})});
const call=(path,optionsValue)=>careCommunityRoutes(request(path,optionsValue),env,options);
const topicBody={idempotencyKey:'topic_submission_key_0001',confirmed:true,title:'A public suggestion',body:'Please add a public care forum.',alias:'Alice',category:'suggestion'};

test('new public-confirmed text stays pending, hidden from guests, and visible only to its author',async()=>{
 const created=await call('/api/care/topics',{method:'POST',cookie:'alice',body:topicBody});assert.equal(created.status,201);const {topicId}=await created.json();
 assert.deepEqual((await(await call('/api/care/topics')).json()).topics,[]);
 assert.equal((await call('/api/care/topics/'+topicId)).status,404);
 const mine=await call('/api/care/topics/'+topicId,{cookie:'alice'});assert.equal(mine.status,200);assert.equal((await mine.json()).visibility,'your pending review');
 assert.equal((await call('/api/care/topics',{method:'POST',cookie:'alice',body:topicBody,originHeader:'https://evil.example'})).status,403);
});
test('fresh trusted administrator can publish and moderation leaves a value-free audit',async()=>{
 const pending=database.prepare("SELECT id,revision FROM care_topics WHERE author_id='alice'").get();
 assert.equal((await call('/api/admin/care/topics',{cookie:'forged'})).status,403);
 const queue=await call('/api/admin/care/topics',{cookie:'admin'});assert.equal(queue.status,200);assert.equal((await queue.json()).topics.length,1);
 const approved=await call('/api/admin/care/topics/'+pending.id,{method:'PUT',cookie:'admin',body:{revision:pending.revision,confirmed:true,action:'approve',reason:'Appropriate public submission'}});assert.equal(approved.status,200);
 const publicTopic=await call('/api/care/topics/'+pending.id);assert.equal(publicTopic.status,200);assert.equal((await publicTopic.json()).visibility,'public');
 const audit=database.prepare("SELECT actor_id,subject,action,reason FROM care_admin_audit WHERE subject=?").get(pending.id);assert.equal(audit.actor_id,'admin');assert.equal(audit.subject,pending.id);assert.equal(audit.action,'approve');assert.equal(audit.reason,'Appropriate public submission');
});
test('replies are pending, flags are sealed and admin-only, and following is owner-scoped',async()=>{
 const topic=database.prepare("SELECT id,revision FROM care_topics WHERE author_id='alice'").get();const replyBody={revision:topic.revision,idempotencyKey:'reply_submission_key_0001',confirmed:true,body:'I support this idea.',alias:'Alice'};
 const posted=await call('/api/care/topics/'+topic.id+'/replies',{method:'POST',cookie:'alice',body:replyBody});assert.equal(posted.status,201);const replyId=(await posted.json()).replyId;
 const guest=await(await call('/api/care/topics/'+topic.id)).json();assert.deepEqual(guest.replies,[]);
 const own=await(await call('/api/care/topics/'+topic.id,{cookie:'alice'})).json();assert.equal(own.replies.length,1);
 const flagged=await call('/api/care/topics/'+topic.id+'/flags',{method:'POST',cookie:'alice',body:{idempotencyKey:'flag_submission_key_00001',confirmed:true,reason:'privacy',message:'Contains a personal address.'}});assert.equal(flagged.status,201);assert.equal((await call('/api/care/topics/'+topic.id+'/flags',{method:'POST',cookie:'alice',body:{idempotencyKey:'flag_submission_key_00002',confirmed:true,reason:'privacy',message:'A second fresh-key report.'}})).status,429);assert.equal(database.prepare('SELECT sealed FROM care_flags').get().sealed.includes('personal address'),false);
 assert.equal((await call('/api/care/topics/'+topic.id+'/follow',{method:'PUT',cookie:'alice',body:{following:true}})).status,200);assert.equal(database.prepare("SELECT count(*) AS n FROM care_follows WHERE owner_id='alice'").get().n,1);
 const queue=await(await call('/api/admin/care/topics',{cookie:'admin'})).json();assert.equal(queue.replies[0].id,replyId);assert.equal(queue.flags[0].message,'Contains a personal address.');
});
test('community routes never query profile or private-provider tables and restriction needs an observed community author',async()=>{
 database.prepare("INSERT INTO community_recipes(id,author_id,alias,recipe_json,attribution_json,source_ref,status,revision,write_id,created_at,updated_at) VALUES(?,?,?,?,?,?, 'pending',1,?,?,?)").run(crypto.randomUUID(),'recipe-only-author','Recipe author','{}','{"kind":"human"}','original-user-submission',crypto.randomUUID(),new Date().toISOString(),new Date().toISOString());queries.length=0;const missing=await call('/api/admin/care/restrictions/no-such-user',{method:'PUT',cookie:'admin',body:{confirmed:true,reason:'Repeated spam',until:new Date(Date.now()+86400000).toISOString()}});assert.equal(missing.status,404);
 assert.equal((await call('/api/admin/care/restrictions/recipe-only-author',{method:'PUT',cookie:'admin',body:{confirmed:true,reason:'Recipe-only abuse',until:new Date(Date.now()+86400000).toISOString()}})).status,200);
 const restricted=await call('/api/admin/care/restrictions/alice',{method:'PUT',cookie:'admin',body:{confirmed:true,reason:'Repeated spam',until:new Date(Date.now()+86400000).toISOString()}});assert.equal(restricted.status,200);
 const result=await call('/api/care/topics',{method:'POST',cookie:'alice',body:{...topicBody,idempotencyKey:'topic_submission_key_0002'}});assert.equal(result.status,403);
 const appeal=await call('/api/care/appeals',{method:'POST',cookie:'alice',body:{idempotencyKey:'appeal_submission_key_001',confirmed:true,message:'Please review this restriction.'}});assert.equal(appeal.status,201);const appealId=(await appeal.json()).appealId;
 const queue=await(await call('/api/admin/care/topics',{cookie:'admin'})).json();assert.equal(queue.appeals.find(item=>item.id===appealId).message,'Please review this restriction.');
 assert.equal((await call('/api/admin/care/appeals/'+appealId,{method:'PUT',cookie:'admin',body:{revision:1,confirmed:true,action:'resolve'}})).status,200);
 assert.equal((await call('/api/admin/care/restrictions/alice',{method:'PUT',cookie:'admin',body:{confirmed:true,action:'lift'}})).status,200);
 assert.equal(queries.some(sql=>/user_state|private_documents|provider_connections|unified_records|kitchens|service_requests/i.test(sql)),false);
});
test('a stale moderation race cannot write a loser audit record',async()=>{
 const row=database.prepare("SELECT id,revision FROM care_replies WHERE author_id='alice'").get();const before=database.prepare("SELECT count(*) AS n FROM care_admin_audit WHERE subject=?").get(row.id).n;
 beforeBatch=()=>database.prepare('UPDATE care_replies SET revision=revision+1 WHERE id=?').run(row.id);
 const response=await call('/api/admin/care/replies/'+row.id,{method:'PUT',cookie:'admin',body:{revision:row.revision,confirmed:true,action:'approve'}});assert.equal(response.status,409);assert.equal(database.prepare("SELECT count(*) AS n FROM care_admin_audit WHERE subject=?").get(row.id).n,before);
});
test('the global monthly posting cap does not overshoot or create an idempotency result on rejection',async()=>{
 const now=new Date().toISOString();const total=database.prepare('SELECT count(*) AS n FROM care_topics').get().n+database.prepare('SELECT count(*) AS n FROM care_replies').get().n;
 for(let index=total;index<200;index++)database.prepare("INSERT INTO care_topics(id,author_id,alias,title,body,category,status,revision,created_at,updated_at) VALUES(?,?,?,?,?,'discussion','pending',1,?,?)").run(crypto.randomUUID(),'filler','Filler','Filler topic','Filler body',now,now);
 const response=await call('/api/care/topics',{method:'POST',cookie:'bob',body:{...topicBody,idempotencyKey:'topic_submission_key_cap_01'}});assert.equal(response.status,429);
 assert.equal(database.prepare('SELECT count(*) AS n FROM care_topics').get().n+database.prepare('SELECT count(*) AS n FROM care_replies').get().n,200);
 assert.equal(database.prepare("SELECT count(*) AS n FROM care_idempotency WHERE owner_id='bob'").get().n,0);
});
test('management candidate exports omit authors and retain the same stale-CAS moderation audit',async()=>{
 database.prepare("DELETE FROM care_topics WHERE author_id='filler'").run();const now=new Date().toISOString(),candidateId=crypto.randomUUID();database.prepare("INSERT INTO care_topics(id,author_id,alias,title,body,category,status,revision,created_at,updated_at) VALUES(?,?,?,?,?,'discussion','pending',1,?,?)").run(candidateId,'private-author','Alias','Candidate title','Candidate body',now,now);
 const candidates=await listCommunityCandidates(env,50),candidate=candidates.find(item=>item.id===candidateId);assert.deepEqual(candidate,{kind:'topic',id:candidateId,revision:1,title:'Candidate title',body:'Candidate body'});assert.equal(JSON.stringify(candidate).includes('private-author'),false);
 const approved=await moderateCommunityCandidate(env,{kind:'topic',id:candidateId,revision:1,action:'approve',actor:'ai-management',reason:'Matches publication rules'});assert.equal(approved.status,200);
 const stale=await moderateCommunityCandidate(env,{kind:'topic',id:candidateId,revision:1,action:'hide',actor:'ai-management',reason:'stale'});assert.equal(stale.status,409);assert.equal(database.prepare("SELECT count(*) AS n FROM care_admin_audit WHERE subject=?").get(candidateId).n,1);
});
test('only exact community routes are claimed and unrelated private care routes pass through',async()=>{
 for(const path of ['/api/care/cases','/api/care/updates','/api/care/recipe/votes','/api/admin/care/cases'])assert.equal(await careCommunityRoutes(request(path),{},options),null,path);
});
test('expired flags and appeals are not decrypted before cleanup and retention erases identifying sealed payloads',async()=>{
 const flag=database.prepare('SELECT id,topic_id FROM care_flags LIMIT 1').get(),appeal=database.prepare('SELECT id FROM care_appeals LIMIT 1').get(),past=Date.now()-1;
 database.prepare('UPDATE care_flags SET retain_until=? WHERE id=?').run(past,flag.id);database.prepare("UPDATE care_appeals SET retain_until=?,status='open' WHERE id=?").run(past,appeal.id);
 const queue=await(await call('/api/admin/care/topics',{cookie:'admin'})).json();assert.equal(queue.flags.find(item=>item.id===flag.id).message,'[expired]');assert.equal(queue.appeals.find(item=>item.id===appeal.id).message,'[expired]');
 database.prepare('INSERT INTO care_restrictions(subject,reason,until_at,created_at,created_by) VALUES(?,?,?,?,?)').run('bob','expired',new Date(past).toISOString(),new Date(past).toISOString(),'admin');assert.equal(await isCommunityRestricted(env,'bob'),false);
 await cleanupCareCommunity(env,Date.now());const erasedFlag=database.prepare('SELECT sealed,reporter_id FROM care_flags WHERE id=?').get(flag.id),erasedAppeal=database.prepare('SELECT sealed,owner_id FROM care_appeals WHERE id=?').get(appeal.id);assert.equal(erasedFlag.sealed,null);assert.equal(erasedFlag.reporter_id,'');assert.equal(erasedAppeal.sealed,null);assert.equal(erasedAppeal.owner_id,'');assert.equal(database.prepare("SELECT count(*) AS n FROM care_idempotency i JOIN care_flags f ON f.id=i.result_id WHERE f.id=?").get(flag.id).n,0);assert.equal(database.prepare("SELECT count(*) AS n FROM care_idempotency i JOIN care_appeals a ON a.id=i.result_id WHERE a.id=?").get(appeal.id).n,0);assert.equal((await call('/api/care/topics/'+flag.topic_id+'/flags',{method:'POST',cookie:'alice',body:{idempotencyKey:'flag_submission_key_00001',confirmed:true,reason:'privacy',message:'Contains a personal address.'}})).status,410);assert.equal(database.prepare("SELECT count(*) AS n FROM care_restrictions WHERE subject='bob'").get().n,0);
});
