import {test} from 'node:test';
import {createServer} from 'node:net';
import assert from 'node:assert/strict';
import {createRequire} from 'node:module';
import {realpathSync} from 'node:fs';
import {resolve,sep} from 'node:path';
import {pathToFileURL,fileURLToPath} from 'node:url';
// Bind default resolution to this test's declared project, independent of CWD.
// An explicit runtime override is optional and remains checked against its root.
const projectManifestURL=new URL('../../package.json',import.meta.url);
const projectRoot=fileURLToPath(new URL('../../',import.meta.url));
const projectRequire=createRequire(projectManifestURL);
const projectManifest=projectRequire(fileURLToPath(projectManifestURL));
if(!projectManifest.devDependencies?.miniflare||!projectManifest.devDependencies?.esbuild)throw Error('Project must declare the native D1 test dependencies.');
const override=process.env.OFFMENU_D1_RUNTIME_ROOT;
const runtimeRoot=realpathSync(override||new URL('../../node_modules/',import.meta.url));
const runtimeRequire=override?createRequire(resolve(runtimeRoot,'package.json')):projectRequire;
const pinnedRuntime={miniflare:'4.20260730.0',esbuild:'0.25.12',workerd:'1.20260730.1'};
for(const [name,version] of Object.entries(pinnedRuntime)){
 const metadata=realpathSync(runtimeRequire.resolve(name+'/package.json'));
 if(!metadata.startsWith(runtimeRoot+sep))throw Error('Native dependency resolves outside the verified install root.');
 if(runtimeRequire(name+'/package.json').version!==version)throw Error('Native D1 qualification requires '+name+'@'+version);
}
if(runtimeRequire('miniflare/package.json').dependencies.workerd!==pinnedRuntime.workerd)throw Error('Miniflare native workerd closure mismatch.');
const runtimeEntry=name=>{
 const entry=realpathSync(runtimeRequire.resolve(name));
 if(!entry.startsWith(runtimeRoot+sep))throw Error('Native module entry resolves outside the verified install root.');
 return pathToFileURL(entry).href;
};
const {Miniflare}=await import(runtimeEntry('miniflare'));
const {build}=await import(runtimeEntry('esbuild'));
import {SESSION_STATE_D1_DDL,createD1SessionStateProtocol} from '../../apps/web/server/session-state-d1-owner04.mjs';
import {validateState} from '../../apps/web/server/state.mjs';

const realm='local_owner04_d1_realm';
const audience='https://offmenu.example/api/state';
const state=()=>validateState({inventory:[],profile:{servings:2}});
const bundle=await build({stdin:{contents:`
import {createD1SessionStateProtocol} from './apps/web/server/session-state-d1-owner04.mjs';
export default {async fetch(request,env){
 const input=await request.json();
 const protocol=createD1SessionStateProtocol({database:env.DB,audience:${JSON.stringify(audience)},realm:${JSON.stringify(realm)},ttlMs:60000,
 authenticate:async()=>input.rejectAuth?null:{id:input.subject||'owner-a'},
 readSession:()=>input.binding,authorizeRequest:async()=>input.rejectPolicy!==true,authorizeEnrollment:async()=>true});
 try{const value=await protocol[input.action](request,input.action==='status'?input.operationId:input.command);
 if(input.dropAck)return Response.json({code:'ACK_LOST',outcome:'unknown'},{status:503});
 return Response.json(value);}catch(e){return Response.json({code:e.code||'UNEXPECTED',outcome:e.outcome},{status:e.status||500});}
}}`,resolveDir:projectRoot,sourcefile:'owner04-d1-fixture.mjs'},bundle:true,write:false,format:'esm',platform:'browser'});

async function loopbackPort(){
 const server=createServer();await new Promise((resolve,reject)=>{server.once('error',reject);server.listen(0,'127.0.0.1',resolve);});
 const port=server.address().port;await new Promise((resolve,reject)=>server.close(error=>error?reject(error):resolve()));return port;
}
async function fixture(t){
 const mf=new Miniflare({host:'127.0.0.1',port:await loopbackPort(),modules:true,script:bundle.outputFiles[0].text,compatibilityDate:'2026-08-06',d1Databases:{DB:'owner04-disposable-local-d1'}});
 t.after(()=>mf.dispose());
 const db=await mf.getD1Database('DB');
 for(const sql of SESSION_STATE_D1_DDL)await db.prepare(sql).run();
 await db.prepare('CREATE TABLE user_state(user_id TEXT PRIMARY KEY,revision INTEGER NOT NULL,state_json TEXT NOT NULL,updated_at TEXT NOT NULL)').run();
 const call=async input=>{const response=await mf.dispatchFetch(audience,{method:'POST',body:JSON.stringify(input)});return {status:response.status,value:await response.json()};};
 const enroll=async(subject='owner-a')=>(await call({action:'enroll',subject})).value;
 const a=await enroll();assert.ok(a.capability);
 return {db,call,a,enroll};
}
const command=(id='operation_00000001',expectedVersion=0)=>({operationId:id,expectedVersion,state:state()});

test('native Worker/D1 concurrent CAS, replay, terminal conflict and altered operation reuse',async t=>{
 const {db,call,a}=await fixture(t);
 const emptyConflict=await call({action:'mutate',binding:a,command:command('operation_empty_001',1)});assert.equal(emptyConflict.value.status,'conflict');assert.equal(emptyConflict.value.revision,0);
 const results=await Promise.all(['operation_00000001','operation_00000002'].map(id=>call({action:'mutate',binding:a,command:command(id)})));
 assert.deepEqual(results.map(x=>x.value.status).sort(),['committed','conflict']);
 const persisted=await db.prepare('SELECT revision FROM user_state').first();assert.equal(persisted.revision,1);
 const conflict=results.find(x=>x.value.status==='conflict').value;
 const exact=await call({action:'mutate',binding:a,command:command(conflict.operationId)});assert.deepEqual(exact.value,conflict);
 const status=await call({action:'status',binding:a,operationId:conflict.operationId});assert.deepEqual(status.value,conflict);
 const reused=await call({action:'mutate',binding:a,command:command(conflict.operationId,1)});assert.equal(reused.value.code,'OPERATION_ID_REUSED');
 assert.equal((await call({action:'read',binding:a})).value.revision,1);
});

test('fresh subject, capability, realm, epoch and policy checks; revoke isolates other sessions',async t=>{
 const {call,a,enroll}=await fixture(t);const other=await enroll();
 for(const patch of [{subject:'other'},{binding:{...a,capability:'z'.repeat(64)}},{binding:{...a,epoch:2}},{binding:{...a,realm:'another_realm_0001'}},{rejectPolicy:true},{rejectAuth:true}]){
  const r=await call({action:'mutate',binding:a,command:command(),...patch});assert.ok(r.status>=400);
 }
 assert.equal((await call({action:'revoke',binding:a})).value.epoch,2);
 assert.equal((await call({action:'revoke',binding:a})).value.epoch,2);
 for(const action of ['read','mutate','status'])assert.equal((await call({action,binding:a,command:command(),operationId:'operation_00000001'})).value.code,'SESSION_DENIED');
 assert.equal((await call({action:'mutate',binding:other,command:command()})).value.status,'committed');
});

test('native D1 rollback includes ledger, then lost acknowledgment resolves through status',async t=>{
 const {db,call,a}=await fixture(t);
 await db.prepare("CREATE TRIGGER reject_write BEFORE INSERT ON user_state BEGIN SELECT RAISE(ABORT,'fixture failure'); END").run();
 const failed=await call({action:'mutate',binding:a,command:command()});assert.equal(failed.value.code,'STORAGE_UNAVAILABLE');assert.equal(failed.value.outcome,'unknown');
 assert.equal((await db.prepare('SELECT count(*) n FROM owner04_d1_operations').first()).n,0);
 assert.equal((await db.prepare('SELECT count(*) n FROM user_state').first()).n,0);
 await db.prepare('DROP TRIGGER reject_write').run();
 assert.equal((await call({action:'mutate',binding:a,command:command(),dropAck:true})).value.outcome,'unknown');
 assert.equal((await call({action:'status',binding:a,operationId:'operation_00000001'})).value.status,'committed');
 assert.equal((await call({action:'mutate',binding:a,command:command()})).value.revision,1);
});

test('SQL guards fail closed on expiry/corrupt version and ignored writes roll back ledger',async t=>{
 const {db,call,a}=await fixture(t);
 await db.prepare("CREATE TRIGGER ignore_write BEFORE INSERT ON user_state BEGIN SELECT RAISE(IGNORE); END").run();
 assert.equal((await call({action:'mutate',binding:a,command:command()})).value.code,'STORAGE_UNAVAILABLE');
 assert.equal((await db.prepare('SELECT count(*) n FROM owner04_d1_operations').first()).n,0);
 await db.prepare('DROP TRIGGER ignore_write').run();
 await db.prepare("INSERT INTO user_state VALUES('owner-a',-1,'{}','test')").run();
 assert.equal((await call({action:'mutate',binding:a,command:command()})).value.code,'INVALID_STORED_VERSION');
 await db.prepare('UPDATE owner04_d1_sessions SET expires_at=0 WHERE id=?').bind(a.sessionId).run();
 assert.equal((await call({action:'read',binding:a})).value.code,'SESSION_DENIED');
 assert.equal((await call({action:'revoke',binding:a})).value.code,'SESSION_DENIED');
});


test('captured command survives await; revoke before admission defeats pending mutation',async t=>{
 const {db,call,a}=await fixture(t);
 let release;const gate=new Promise(resolve=>{release=resolve;});
 const protocol=createD1SessionStateProtocol({database:db,audience,realm,ttlMs:60000,authenticate:async()=>{await gate;return {id:'owner-a'};},readSession:()=>a,authorizeRequest:async()=>true,authorizeEnrollment:async()=>true});
 const c=command();const pending=protocol.mutate({},c);
 c.operationId='replacement_000001';c.expectedVersion=9;c.state.profile.servings=100;
 release();const result=await pending;assert.equal(result.operationId,'operation_00000001');assert.equal(result.revision,1);
 assert.equal(JSON.parse((await db.prepare('SELECT state_json FROM user_state').first()).state_json).profile.servings,2);
 let continueAuth;const authGate=new Promise(resolve=>{continueAuth=resolve;});
 const late=createD1SessionStateProtocol({database:db,audience,realm,ttlMs:60000,authenticate:async()=>{await authGate;return {id:'owner-a'};},readSession:()=>a,authorizeRequest:async()=>true,authorizeEnrollment:async()=>true});
 const blocked=late.mutate({},command('operation_00000002',1));
 await call({action:'revoke',binding:a});continueAuth();
 await assert.rejects(blocked,{code:'SESSION_DENIED'});
 assert.equal((await db.prepare('SELECT revision FROM user_state').first()).revision,1);
 assert.equal((await db.prepare('SELECT count(*) n FROM owner04_d1_operations').first()).n,1);
});
