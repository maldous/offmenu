import test from 'node:test';
import assert from 'node:assert/strict';
import {DatabaseSync} from 'node:sqlite';
import {readFileSync} from 'node:fs';
import {createHash} from 'node:crypto';
import {createQueueStateBridge,createQueueStateHttpHandler} from './snapshot/cloud/queue-state-bridge-owner16.mjs';
import {createSessionStateProtocol,createSqliteStateStore,SESSION_STATE_DDL} from './snapshot/cloud/session-state-owner04.mjs';
const origin='https://digest-review.invalid',audience=origin+'/api/state';
const state=()=>({inventory:[],products:{},recipes:[],selections:[],profile:{country:'AU',units:'metric',servings:2}});
const command=(id='review_operation_0001',version=0)=>({operationId:id,expectedVersion:version,state:state()});
const canonical=v=>v===null||typeof v!=='object'?JSON.stringify(v):Array.isArray(v)?'['+v.map(canonical).join(',')+']':'{'+Object.keys(v).sort().map(k=>JSON.stringify(k)+':'+canonical(v[k])).join(',')+'}';
const expectedDigest=op=>createHash('sha256').update(canonical({audience,method:'PUT',version:op.expectedVersion,state:op.state})).digest('hex');
async function fixture(t,authenticate=async req=>({id:req.subject})) {
  const db=new DatabaseSync(':memory:');t.after(()=>db.close());
  db.exec(readFileSync(new URL('./snapshot/cloud/schema.sql',import.meta.url),'utf8'));
  for(const ddl of SESSION_STATE_DDL)db.exec(ddl);
  let time=100;
  const p=createSessionStateProtocol({store:createSqliteStateStore(db),authenticate,readSession:r=>r.protectedSession,
    authorizeRequest:async()=>true,authorizeEnrollment:async()=>true,audience,realm:'review_realm_0001',ttlMs:1000,now:()=>time});
  const session=await p.enroll({subject:'review-account'});
  const req=()=>({subject:'review-account',protectedSession:{...session}});
  const bridge=protocol=>createQueueStateBridge({protocol:protocol||p,trustedBinding:()=>session.binding});
  return {db,p,session,req,bridge,expire:()=>time=2000};
}
test('independent canonical digest matches actual SQLite outcome; damaged digest never confirms',async t=>{
  const f=await fixture(t),op=command(),good=await f.bridge().submit(f.req(),op);
  assert.equal(good.confirmed,true);assert.equal(good.digest,expectedDigest(op));
  for(const digest of [undefined,null,'', '0'.repeat(64),expectedDigest({...op,state:{...op.state,profile:{...op.state.profile,servings:3}}})]) {
    const bad=f.bridge({...f.p,mutate:async()=>({...good,digest})});
    assert.equal((await bad.submit(f.req(),op)).confirmed,false);
  }
  assert.equal(f.db.prepare('SELECT revision FROM user_state').get().revision,1);
});
test('all binding fields, operation and successor revision bind ACK; reordered binding is equivalent',async t=>{
  const f=await fixture(t),op=command(),good=await f.p.mutate(f.req(),op);
  for(const field of ['subject','sessionId','realm','epoch','resource']) {
    const changed={...good.binding,[field]:field==='epoch'?2:field==='resource'?'https://other.invalid/api/state':'different'};
    assert.equal((await f.bridge({...f.p,mutate:async()=>({...good,binding:changed})}).submit(f.req(),op)).confirmed,false);
  }
  for(const patch of [{operationId:'other_operation_0001'},{revision:9},{acknowledged:false}])
    assert.equal((await f.bridge({...f.p,mutate:async()=>({...good,...patch})}).submit(f.req(),op)).confirmed,false);
  assert.equal((await f.bridge({...f.p,mutate:async()=>({...good,binding:Object.fromEntries(Object.entries(good.binding).reverse())})}).submit(f.req(),op)).confirmed,true);
});
test('lost applied outcome recovers only same payload; conflict never becomes mutation ACK',async t=>{
  const f=await fixture(t),op=command();
  const lost=f.bridge({...f.p,mutate:async(r,c)=>{await f.p.mutate(r,c);throw Error('synthetic lost response');}});
  assert.equal((await lost.submit(f.req(),op)).confirmed,false);
  assert.equal((await f.bridge().recover(f.req(),op)).acknowledged,true);
  const changed=command();changed.state.profile.servings=3;
  assert.equal((await f.bridge().recover(f.req(),changed)).confirmed,false);
  const conflict=await f.bridge().submit(f.req(),command('review_stale_operation'));
  assert.equal(conflict.confirmed,true);assert.equal(conflict.status,'conflict');assert.equal(conflict.acknowledged,false);
});
test('pre-await private command/credentials survive caller mutation; revoke before admission denies',async t=>{
  let release,entered;const waiting=new Promise(r=>release=r),started=new Promise(r=>entered=r);
  const f=await fixture(t,async req=>{const subject=req.subject;if(req.pause){entered();await waiting;}return {id:subject};});
  const req=f.req();req.pause=true;const op=command();const pending=f.bridge().submit(req,op);await started;
  req.protectedSession.capability='x'.repeat(64);op.state.profile.servings=99;release();
  assert.equal((await pending).confirmed,true);assert.equal(JSON.parse(f.db.prepare('SELECT state_json FROM user_state').get().state_json).profile.servings,2);
  let unblock,atAuth;const barrier=new Promise(r=>unblock=r),seen=new Promise(r=>atAuth=r);
  const other=await fixture(t,async req=>{if(req.pause){atAuth();await barrier;}return {id:req.subject};});
  const queued=other.req();queued.pause=true;const result=other.bridge().submit(queued,command());await seen;
  await other.p.revoke(other.req());unblock();assert.equal((await result).confirmed,false);
  assert.equal(other.db.prepare('SELECT count(*) n FROM user_state').get().n,0);
});
test('malformed returned ACKs and accessor hooks remain unknown without hook execution',async t=>{
  const f=await fixture(t);let calls=0;const evil={};Object.defineProperty(evil,'binding',{enumerable:true,get(){calls++;throw Error('hook');}});
  for(const value of [null,[],{},evil])assert.equal((await f.bridge({...f.p,mutate:async()=>value}).submit(f.req(),command())).confirmed,false);
  assert.equal(calls,0);
  const op=command();Object.defineProperty(op.state.profile,'servings',{enumerable:true,get(){calls++;return 3;}});
  await assert.rejects(f.bridge().submit(f.req(),op));assert.equal(calls,0);
});
test('late committed ACK is distinct from expired authority for new send and status',async t=>{
  const f=await fixture(t),op=command();
  const late=f.bridge({...f.p,mutate:async(r,c)=>{const value=await f.p.mutate(r,c);f.expire();return value;}});
  assert.equal((await late.submit(f.req(),op)).confirmed,true);
  assert.equal((await f.bridge().submit(f.req(),command('review_expired_operation',1))).confirmed,false);
  assert.equal((await f.bridge().recover(f.req(),op)).confirmed,false);
  await assert.rejects(f.bridge().submit(f.req(),{...op,expiresAt:9999}));
});
test('prepared HTTP gate rejects foreign origin before dispatch and retains no-store unknown semantics',async()=>{
  let calls=0;const bridge={submit:async()=>{calls++;return {status:'unknown',confirmed:false,acknowledged:false};},recover:async()=>({status:'unknown'})};
  const handler=createQueueStateHttpHandler({bridge,origin});
  const req=o=>new Request(origin+'/api/private/v2/state',{method:'PUT',headers:{Origin:o,'Content-Type':'application/json'},body:JSON.stringify(command())});
  assert.equal((await handler(req('https://other.invalid'))).status,403);assert.equal(calls,0);
  const response=await handler(req(origin));assert.equal(response.status,503);assert.equal(response.headers.get('Cache-Control'),'private, no-store');assert.equal((await response.json()).confirmed,false);
});
