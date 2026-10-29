import test from 'node:test';import assert from 'node:assert/strict';
import {DatabaseSync} from 'node:sqlite';import {readFileSync} from 'node:fs';
import {cacheInvalidationAdapter} from '../../apps/web/server/cache-invalidation-owner29.mjs';
import {admission} from '../../apps/web/src/evidence-model.js';
// Injected test double ONLY for this exact two-node synthetic fixture. This
// does not implement or adopt the unaccepted general f2e195b evaluator.
function fixtureDependencyGate(rows,{clock,permit}) {
 assert.deepEqual(rows.map(row=>row.id),['r','derived']);
 const [root,derived]=rows,now=clock();
 const rootAllowed=permit(root,{now}).allowed===true&&!['withdrawn','quarantined'].includes(root.status);
 const fields=['owner','sourceId','id','predicate','version'];
 const dependency=derived.dependencies?.[0];
 const bound=derived.dependencies?.length===1&&dependency&&fields.every(field=>typeof root[field]==='string'&&dependency[field]===root[field]);
 return [{allowed:rootAllowed},{allowed:rootAllowed&&bound&&permit(derived,{now}).allowed===true}];
}
function setup(){
 const db=new DatabaseSync(':memory:');db.exec(readFileSync(new URL('../../apps/web/server/catalogue-schema.sql',import.meta.url),'utf8'));
 const policy=JSON.stringify({active:true,actions:['display','persist'],audiences:['private']});db.prepare('INSERT INTO source_policies VALUES(?,?,1,1)').run('s',policy);
 const DB={prepare(sql){return {bind(...args){return {async first(){return db.prepare(sql).get(...args)||null;}};}}}};
 let now=1000,calls=0,allowed=true;
 const adapter=cacheInvalidationAdapter({DB,clock:()=>now,evaluateDependencies:fixtureDependencyGate,permit:(node,{scope,policy,action,now})=>admission(policy,{...node,dependencies:[]},{owner:scope.owner,audience:scope.audience,action,now}),reserve:async()=>{calls++;return {allowed};}});
 const scope={owner:'alice',audience:'private',sourceId:'s',query:'q',producerEpoch:'producer-v1'};
 const root={id:'r',owner:'alice',sourceId:'s',predicate:'name',version:'1',dependencies:[]};
 const envelope={format:'owner29/1',scope,epochs:[{sourceId:'s',document:policy,revision:1}],freshUntil:2000,assertions:[root,{...root,id:'derived',dependencies:[{...root}]}],payload:{value:'synthetic',uncertainty:'unknown'}};
 for(const node of envelope.assertions)db.prepare('INSERT INTO evidence_assertions VALUES(?,?,?,?,?,?,?,?,?,?,?,?)').run(node.owner,node.id,'subject',node.predicate,node.sourceId,'s','',JSON.stringify(node),2000,2000,'active','test');
 return {db,DB,adapter,scope,envelope,calls:()=>calls,setBudget:v=>allowed=v,setTime:v=>now=v};
}
test('actual caller/store miss then hit, isolated private scope and producer epoch',async()=>{const x=setup();try{assert.equal((await x.adapter.resolve(x.scope,x.envelope,async()=>x.envelope)).status,'miss');assert.equal(x.calls(),1);assert.equal((await x.adapter.resolve(x.scope,x.envelope,async()=>{throw Error('unexpected transport');})).status,'hit');assert.equal(await x.adapter.read({...x.scope,owner:'bob'}),null);assert.equal(await x.adapter.read({...x.scope,producerEpoch:'producer-v2'}),null);}finally{x.db.close();}});
test('withdrawal/revision changes withhold cache and in-flight publication',async()=>{const x=setup();try{assert.equal(await x.adapter.publish(x.scope,x.envelope),true);x.db.prepare("UPDATE source_policies SET active=0 WHERE id='s'").run();assert.equal(await x.adapter.read(x.scope),null);x.db.prepare("UPDATE source_policies SET active=1,revision=2 WHERE id='s'").run();assert.equal(await x.adapter.publish(x.scope,x.envelope),false);}finally{x.db.close();}});
test('budget deny precedes transport; policy change during transport withholds response',async()=>{const x=setup();try{x.setBudget(false);assert.equal((await x.adapter.resolve(x.scope,x.envelope,async()=>{throw Error('transport');})).status,'budget-denied');x.setBudget(true);assert.equal((await x.adapter.resolve(x.scope,x.envelope,async()=>{x.db.exec("UPDATE source_policies SET active=0 WHERE id='s'");return x.envelope;})).status,'withheld');assert.equal(x.db.prepare('SELECT count(*) n FROM resolver_cache').get().n,0);}finally{x.db.close();}});
test('withdrawn graph, expiry and foreign private input withheld without reservation',async()=>{const x=setup();try{x.envelope.assertions[0].status='withdrawn';assert.equal((await x.adapter.resolve(x.scope,x.envelope,async()=>x.envelope)).status,'withheld');assert.equal(x.calls(),0);delete x.envelope.assertions[0].status;x.envelope.assertions[0].owner='bob';assert.equal(await x.adapter.publish(x.scope,x.envelope),false);x.envelope.assertions[0].owner='alice';x.setTime(2000);assert.equal(await x.adapter.publish(x.scope,x.envelope),false);}finally{x.db.close();}});

test('authoritative dependency withdrawal invalidates previously stored envelope',async()=>{const x=setup();try{assert.equal(await x.adapter.publish(x.scope,x.envelope),true);x.db.exec("UPDATE evidence_assertions SET status='withdrawn' WHERE id='r'");assert.equal(await x.adapter.read(x.scope),null);}finally{x.db.close();}});

test('independent: source rights expiry crossed during final read must withhold',async()=>{const x=setup();try{
 const policy=JSON.stringify({active:true,actions:['display','persist'],audiences:['private'],expiresAt:new Date(1500).toISOString()});
 x.db.prepare('UPDATE source_policies SET document=? WHERE id=?').run(policy,'s');x.envelope.epochs[0].document=policy;
 assert.equal(await x.adapter.publish(x.scope,x.envelope),true);
 const prepare=x.DB.prepare.bind(x.DB);x.DB.prepare=sql=>{if(sql.includes('AND document=? AND fresh_until>'))x.setTime(1600);return prepare(sql);};
 assert.equal(await x.adapter.read(x.scope),null,'expired source rights must not return an envelope');
}finally{x.db.close();}});

test('independent: policy changed during final SQL invalidates cache read',async()=>{const x=setup();try{
 assert.equal(await x.adapter.publish(x.scope,x.envelope),true);
 const prepare=x.DB.prepare.bind(x.DB);x.DB.prepare=sql=>{if(sql.includes('AND document=? AND fresh_until>'))x.db.exec("UPDATE source_policies SET revision=revision+1 WHERE id='s'");return prepare(sql);};
 assert.equal(await x.adapter.read(x.scope),null);
}finally{x.db.close();}});
test('independent: authoritative node changed before conditional insertion rejects publish',async()=>{const x=setup();try{
 const prepare=x.DB.prepare.bind(x.DB);x.DB.prepare=sql=>{if(sql.startsWith('INSERT INTO resolver_cache'))x.db.exec("UPDATE evidence_assertions SET status='quarantined' WHERE id='r'");return prepare(sql);};
 assert.equal(await x.adapter.publish(x.scope,x.envelope),false);
 assert.equal(x.db.prepare('SELECT count(*) n FROM resolver_cache').get().n,0);
}finally{x.db.close();}});
test('independent: foreign private graph denies before reserve/transport',async()=>{const x=setup();try{
 x.envelope.assertions[1].dependencies[0].owner='bob';
 x.db.prepare('UPDATE evidence_assertions SET document=? WHERE id=?').run(JSON.stringify(x.envelope.assertions[1]),'derived');
 assert.equal((await x.adapter.resolve(x.scope,x.envelope,async()=>assert.fail('transport'))).status,'withheld');assert.equal(x.calls(),0);
}finally{x.db.close();}});
test('policy expiry at final insertion withholds and writes nothing',async()=>{const x=setup();try{
 const policy=JSON.stringify({active:true,actions:['display','persist'],audiences:['private'],expiresAt:new Date(1500).toISOString()});
 x.db.prepare('UPDATE source_policies SET document=? WHERE id=?').run(policy,'s');x.envelope.epochs[0].document=policy;
 const prepare=x.DB.prepare.bind(x.DB);x.DB.prepare=sql=>{if(sql.startsWith('INSERT INTO resolver_cache'))x.setTime(1500);return prepare(sql);};
 assert.equal(await x.adapter.publish(x.scope,x.envelope),false);
 assert.equal(x.db.prepare('SELECT count(*) n FROM resolver_cache').get().n,0);
}finally{x.db.close();}});
test('rights expire during injected reservation: no transport',async()=>{const x=setup();try{
 const policy=JSON.stringify({active:true,actions:['display','persist'],audiences:['private'],expiresAt:new Date(1500).toISOString()});
 x.db.prepare('UPDATE source_policies SET document=? WHERE id=?').run(policy,'s');x.envelope.epochs[0].document=policy;
 let now=1000;
 const adapter=cacheInvalidationAdapter({DB:x.DB,clock:()=>now,evaluateDependencies:fixtureDependencyGate,permit:(node,{scope,policy,action,now})=>admission(policy,{...node,dependencies:[]},{owner:scope.owner,audience:scope.audience,action,now}),reserve:async()=>{now=1500;return {allowed:true};}});
 assert.equal((await adapter.resolve(x.scope,x.envelope,async()=>assert.fail('transport'))).status,'withheld');
}finally{x.db.close();}});

test('rereview: expiry during asynchronous final read must withhold',async()=>{const x=setup();try{
 const policy=JSON.stringify({active:true,actions:['display','persist'],audiences:['private'],expiresAt:new Date(1500).toISOString()});
 x.db.prepare('UPDATE source_policies SET document=? WHERE id=?').run(policy,'s');x.envelope.epochs[0].document=policy;
 assert.equal(await x.adapter.publish(x.scope,x.envelope),true);
 const prepare=x.DB.prepare.bind(x.DB);x.DB.prepare=sql=>{const stmt=prepare(sql);if(!sql.includes('AND document=? AND fresh_until>'))return stmt;
 return {bind(...args){const bound=stmt.bind(...args);return {async first(){await Promise.resolve();x.setTime(1600);return bound.first();}};}};};
 assert.equal(await x.adapter.read(x.scope),null,'rights expired while final query was pending');
}finally{x.db.close();}});
test('rereview: producer epoch metadata cannot replace source-policy conditional gate',async()=>{const x=setup();try{
 const spoof={owner:'alice',id:'epoch-spoof',sourceId:'s'};x.envelope.epochs[0].node=spoof;
 // A synthetically permitted authoritative row with exact policy bytes makes
 // the metadata confusion observable, without changing any graph assertions.
 x.db.prepare('INSERT INTO evidence_assertions VALUES(?,?,?,?,?,?,?,?,?,?,?,?)').run('alice','epoch-spoof','subject','name','s','s','',x.envelope.epochs[0].document,2000,2000,'active','test');
 const prepare=x.DB.prepare.bind(x.DB);x.DB.prepare=sql=>{if(sql.startsWith('INSERT INTO resolver_cache'))x.db.exec("UPDATE source_policies SET revision=2,active=0 WHERE id='s'");return prepare(sql);};
 assert.equal(await x.adapter.publish(x.scope,x.envelope),false,'epoch extras must not bypass changed source policy');
}finally{x.db.close();}});


for(const mode of ['read','publish'])test(`delayed final ${mode} enforces every authoritative deadline`,async()=>{
 for(const deadline of ['source','row-retention','row-freshness','document-retention','envelope']) {
  const x=setup();try{
   if(deadline==='source') {const policy=JSON.stringify({active:true,actions:['display','persist'],audiences:['private'],expiresAt:new Date(1500).toISOString()});x.db.prepare('UPDATE source_policies SET document=? WHERE id=?').run(policy,'s');x.envelope.epochs[0].document=policy;}
   if(deadline==='row-retention')x.db.exec('UPDATE evidence_assertions SET retain_until=1500');
   if(deadline==='row-freshness')x.db.exec('UPDATE evidence_assertions SET fresh_until=1500');
   if(deadline==='document-retention'){x.envelope.assertions[0].retainUntil=new Date(1500).toISOString();x.db.prepare('UPDATE evidence_assertions SET document=? WHERE id=?').run(JSON.stringify(x.envelope.assertions[0]),'r');}
   if(deadline==='envelope')x.envelope.freshUntil=1500;
   if(mode==='read')assert.equal(await x.adapter.publish(x.scope,x.envelope),true);
   const prepare=x.DB.prepare.bind(x.DB);x.DB.prepare=sql=>{const stmt=prepare(sql);if(!(mode==='read'?sql.includes('AND document=? AND fresh_until>'):sql.startsWith('INSERT INTO resolver_cache')))return stmt;return {bind(...args){const bound=stmt.bind(...args);return {async first(){await Promise.resolve();x.setTime(1500);return bound.first();}};}};};
   assert.equal(mode==='read'?await x.adapter.read(x.scope):await x.adapter.publish(x.scope,x.envelope),mode==='read'?null:false,deadline);
   if(mode==='publish')assert.equal(x.db.prepare('SELECT count(*) n FROM resolver_cache').get().n,0,deadline);
  }finally{x.db.close();}
 }
});
test('reservation cannot mutate captured scope or graph authority',async()=>{const x=setup();try{
 const adapter=cacheInvalidationAdapter({DB:x.DB,clock:()=>1000,evaluateDependencies:fixtureDependencyGate,permit:(node,{scope,policy,action,now})=>admission(policy,{...node,dependencies:[]},{owner:scope.owner,audience:scope.audience,action,now}),reserve:async({scope})=>{assert.throws(()=>scope.owner='bob',TypeError);x.scope.owner='bob';x.envelope.assertions[0].owner='bob';return {allowed:true};}});
 assert.equal((await adapter.resolve(x.scope,x.envelope,async()=>x.envelope)).status,'withheld');
}finally{x.db.close();}});

test('delta: delayed cache row freshness independently withholds',async()=>{const x=setup();try{
 assert.equal(await x.adapter.publish(x.scope,x.envelope),true);x.db.exec('UPDATE resolver_cache SET fresh_until=1500');
 const prepare=x.DB.prepare.bind(x.DB);x.DB.prepare=sql=>{const stmt=prepare(sql);if(!sql.includes('AND document=? AND fresh_until>'))return stmt;return {bind(...args){const bound=stmt.bind(...args);return {async first(){await Promise.resolve();x.setTime(1500);return bound.first();}};}};};
 assert.equal(await x.adapter.read(x.scope),null);
}finally{x.db.close();}});
test('delta: cleanup preserves actual second publisher with identical producer envelope',async()=>{const x=setup();try{
 x.db.exec('UPDATE evidence_assertions SET retain_until=1500');
 const prepare=x.DB.prepare.bind(x.DB);let first=true;let replacement;
 x.DB.prepare=sql=>{const stmt=prepare(sql);if(!sql.startsWith('INSERT INTO resolver_cache')||!first)return stmt;first=false;return {bind(...args){const bound=stmt.bind(...args);return {async first(){const row=await bound.first();x.setTime(1600);x.db.exec('UPDATE evidence_assertions SET retain_until=3000');assert.equal(await x.adapter.publish(x.scope,x.envelope),true);replacement=x.db.prepare('SELECT document,updated_at FROM resolver_cache').get();return row;}};}};};
 assert.equal(await x.adapter.publish(x.scope,x.envelope),false);
 assert.deepEqual(x.db.prepare('SELECT document,updated_at FROM resolver_cache').get(),replacement);
 assert.notEqual(await x.adapter.read(x.scope),null);
}finally{x.db.close();}});
test('delta: same-clock identical payload publishers have distinct physical generations',async()=>{const x=setup();try{
 x.envelope.cacheWriteGeneration='producer-controlled';
 assert.equal(await x.adapter.publish(x.scope,x.envelope),true);const first=x.db.prepare('SELECT document,updated_at FROM resolver_cache').get();
 assert.equal(await x.adapter.publish(x.scope,x.envelope),true);const second=x.db.prepare('SELECT document,updated_at FROM resolver_cache').get();
 assert.equal(first.updated_at,second.updated_at);assert.notEqual(first.document,second.document);
 const firstGeneration=JSON.parse(first.document).cacheWriteGeneration,secondGeneration=JSON.parse(second.document).cacheWriteGeneration;
 assert.notEqual(firstGeneration,'producer-controlled');assert.notEqual(firstGeneration,secondGeneration);
 assert.equal((await x.adapter.read(x.scope)).cacheWriteGeneration,undefined);
}finally{x.db.close();}});
test('delta: exact physical row renewal also fences cleanup',async()=>{const x=setup();try{
 x.db.exec('UPDATE evidence_assertions SET retain_until=1500');
 const prepare=x.DB.prepare.bind(x.DB);x.DB.prepare=sql=>{const stmt=prepare(sql);if(!sql.startsWith('INSERT INTO resolver_cache'))return stmt;return {bind(...args){const bound=stmt.bind(...args);return {async first(){const row=await bound.first();x.setTime(1600);x.db.exec('UPDATE evidence_assertions SET retain_until=3000; UPDATE resolver_cache SET fresh_until=3000');return row;}};}};};
 assert.equal(await x.adapter.publish(x.scope,x.envelope),false);
 assert.equal(x.db.prepare('SELECT fresh_until FROM resolver_cache').get().fresh_until,3000);
}finally{x.db.close();}});
