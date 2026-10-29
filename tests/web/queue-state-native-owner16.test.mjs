import test from 'node:test';
import assert from 'node:assert/strict';
import {Miniflare} from 'miniflare';
import {build} from 'esbuild';
import {fileURLToPath} from 'node:url';
import {verifyFixtures} from './fixtures/queue-state-owner16/verify.mjs';
verifyFixtures();
const origin = 'https://offmenu.test', audience = origin + '/api/state';
const script = `
import {createD1SessionStateProtocol,SESSION_STATE_D1_DDL} from './tests/web/fixtures/queue-state-owner16/d104/cloud/session-state-d1-owner04.mjs';
import {createQueueStateWorker} from './cloud/queue-state-entry-owner16.mjs';
const origin=${JSON.stringify(origin)},audience=${JSON.stringify(audience)},realm='local_owner16_native_realm';
// Explicit synthetic HTTP credentials only, never body-selected auth.
const authenticate=async request=>{const token=request.headers.get('Authorization');return token==='Bearer fixture-alice'?{id:'synthetic-alice'}:token==='Bearer fixture-bob'?{id:'synthetic-bob'}:null;};
const readSession=request=>{const text=request.headers.get('Cookie')?.match(/(?:^|; *)owner16_fixture=([^;]+)/)?.[1];return text?JSON.parse(decodeURIComponent(text)):null;};
const options={authenticate,readSession,authorizeRequest:async request=>request.headers.get('Origin')===origin,authorizeEnrollment:async()=>true,audience,realm,ttlMs:60000};
const protocol=env=>createD1SessionStateProtocol({...options,database:env.DB});
export default {async fetch(request,env){
 const url=new URL(request.url);
 if(url.pathname==='/fixture/setup'){
  for(const sql of SESSION_STATE_D1_DDL)await env.DB.prepare(sql).run();
  await env.DB.prepare('CREATE TABLE user_state(user_id TEXT PRIMARY KEY,revision INTEGER NOT NULL,state_json TEXT NOT NULL,updated_at TEXT NOT NULL)').run();return new Response('ok');
 }
 if(url.pathname==='/fixture/enroll')return Response.json(await protocol(env).enroll(request));
 if(url.pathname==='/fixture/revoke')return Response.json(await protocol(env).revoke(request));
 const worker=createQueueStateWorker({origin,protocolOptions:options,
  resolveBinding:async(req,e)=>{
   const credential=readSession(req);if(!credential)throw Error('Missing protected fixture transport');
   const row=await e.DB.withSession('first-primary').prepare('SELECT subject,id,realm,epoch,audience FROM owner04_d1_sessions WHERE id=?').bind(credential.sessionId).first();
   if(!row)throw Error('Missing enrollment');return {subject:row.subject,sessionId:row.id,realm:row.realm,epoch:row.epoch,resource:row.audience};
  },createProtocol:opts=>{
   const p=createD1SessionStateProtocol(opts),mutate=p.mutate;
   // Failure injection is fixture-only, after the real native D1 operation.
   p.mutate=async(req,op)=>{const result=await mutate(req,op),mode=req.headers.get('X-Fixture-Outcome');
    if(mode==='lost')throw Error('Lost response after commit');
    if(mode==='digest')return {...result,digest:'0'.repeat(64)};
    if(mode==='expire-after-commit')await opts.database.prepare('UPDATE owner04_d1_sessions SET expires_at=0 WHERE id=?').bind(result.binding.sessionId).run();
    return result;};return p;
  }});
 return worker.fetch(request,env);
}};`;
const bundled = await build({stdin: {contents: script, resolveDir: fileURLToPath(new URL('../../', import.meta.url)), sourcefile: 'owner16-native-http-fixture.mjs'}, bundle: true, write: false, platform: 'browser', format: 'esm'});
const state = () => ({inventory: [], products: {}, recipes: [], selections: [], profile: {country: 'AU', units: 'metric', servings: 2}});
const command = (operationId = 'native_operation_0001', expectedVersion = 0) => ({operationId, expectedVersion, state: state()});
async function fixture(t) {
  const mf = new Miniflare({modules: true, script: bundled.outputFiles[0].text, compatibilityDate: '2026-08-06', d1Databases: {DB: 'owner16-native-http-disposable'}});
  t.after(() => mf.dispose());
  await mf.dispatchFetch(origin + '/fixture/setup');
  const db = await mf.getD1Database('DB');
  const call = async (path, body, session, account = 'alice', extra = {}) => {
    const headers = {Origin: origin, Authorization: 'Bearer fixture-' + account, 'Content-Type': 'application/json', ...extra};
    if (session) headers.Cookie = 'owner16_fixture=' + encodeURIComponent(JSON.stringify(session));
    const response = await mf.dispatchFetch(origin + path, {method: path.endsWith('/state') ? 'PUT' : 'POST', headers, body: body === undefined ? undefined : JSON.stringify(body)});
    return {status: response.status, body: await response.json()};
  };
  const a = (await call('/fixture/enroll', undefined)).body;
  const b = (await call('/fixture/enroll', undefined, undefined, 'bob')).body;
  const send = (body, session = a, account = 'alice', extra) => call('/api/private/v2/state', body, session, account, extra);
  const recover = (body, session = a) => call('/api/private/v2/state/status', body, session);
  const count = async () => (await db.prepare('SELECT count(*) n FROM owner04_d1_operations').first()).n;
  return {db, call, a, b, send, recover, count};
}
test('actual HTTP→native D1 commit/ledger/digest ACK, retry once and concurrent CAS conflict', async t => {
  const f = await fixture(t), op = command();
  const result = await f.send(op); assert.equal(result.status, 200); assert.equal(result.body.confirmed, true);
  assert.deepEqual(result.body.binding, f.a.binding);
  const row = await f.db.prepare('SELECT digest,result_json FROM owner04_d1_operations WHERE operation_id=?').bind(op.operationId).first();
  assert.equal(row.digest, result.body.digest); assert.equal(JSON.parse(row.result_json).revision, 1);
  assert.deepEqual((await f.send(op)).body, result.body); assert.equal(await f.count(), 1);
  const results = await Promise.all(['native_concurrent_001','native_concurrent_002'].map(id => f.send(command(id, 1))));
  assert.deepEqual(results.map(x => x.status).sort(), [200, 409]);
  assert.equal((await f.db.prepare('SELECT revision FROM user_state').first()).revision, 2);
});
test('before/after native outcome: committed damaged/lost ACK is unknown; exact HTTP recovery confirms', async t => {
  const f = await fixture(t), op = command();
  const damaged = await f.send(op, f.a, 'alice', {'X-Fixture-Outcome': 'digest'});
  assert.equal(damaged.status, 503); assert.equal(damaged.body.confirmed, false);
  assert.equal((await f.recover(op)).status, 200);
  const next = command('native_lost_operation', 1);
  assert.equal((await f.send(next, f.a, 'alice', {'X-Fixture-Outcome': 'lost'})).status, 503);
  assert.equal((await f.recover(next)).body.revision, 2);
  const altered = command('native_lost_operation', 1); altered.state.profile.servings = 3;
  assert.equal((await f.recover(altered)).status, 503); assert.equal(await f.count(), 2);
});
test('native account/epoch/capability/revocation and authoritative expiry deny new sends', async t => {
  const f = await fixture(t);
  for (const [session, account] of [[f.a, 'bob'], [{...f.a, epoch: 2}, 'alice'], [{...f.a, realm: 'wrong_realm_00001'}, 'alice'], [{...f.a, capability: 'x'.repeat(64)}, 'alice']])
    assert.equal((await f.send(command(), session, account)).status, 503);
  assert.equal(await f.count(), 0);
  assert.equal((await f.send(command())).status, 200);
  await f.call('/fixture/revoke', undefined, f.a);
  assert.equal((await f.recover(command())).status, 503);
  assert.equal((await f.send(command('native_after_revoke', 1))).status, 503);
  await f.db.prepare('UPDATE owner04_d1_sessions SET expires_at=0 WHERE id=?').bind(f.b.sessionId).run();
  assert.equal((await f.send(command('native_bob_expired'), f.b, 'bob')).status, 503);
  assert.equal(await f.count(), 1);
});
test('native HTTP rollback and metadata rejection preserve state/ledger without legacy projection', async t => {
  const f = await fixture(t);
  await f.db.prepare("CREATE TRIGGER owner16_reject BEFORE INSERT ON user_state BEGIN SELECT RAISE(ABORT,'synthetic rollback'); END").run();
  assert.equal((await f.send(command())).status, 503); assert.equal(await f.count(), 0);
  assert.equal((await f.db.prepare('SELECT count(*) n FROM user_state').first()).n, 0);
  await f.db.prepare('DROP TRIGGER owner16_reject').run();
  const extended = command(); extended.state.profile.owner16Metadata = {qualifier: 'unknown'};
  assert.equal((await f.send(extended)).status, 503); assert.equal(await f.count(), 0);
  assert.equal((await f.send(command())).status, 200);
  assert.equal(JSON.parse((await f.db.prepare('SELECT state_json FROM user_state').first()).state_json).profile.servings, 2);
});

test('native late committed ACK confirms despite subsequent expiry; new send/status cannot regain authority', async t => {
  const f = await fixture(t), op = command();
  const response = await f.send(op, f.a, 'alice', {'X-Fixture-Outcome': 'expire-after-commit'});
  assert.equal(response.status, 200); assert.equal(response.body.confirmed, true);
  assert.equal((await f.recover(op)).status, 503);
  assert.equal((await f.send(command('native_after_expiry', 1))).status, 503);
  assert.equal(await f.count(), 1);
  assert.equal((await f.db.prepare('SELECT revision FROM user_state').first()).revision, 1);
});
