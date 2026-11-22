import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {createHash} from 'node:crypto';
import {posix} from 'node:path';
import {Miniflare} from 'miniflare';
import {build} from 'esbuild';
import {fileURLToPath} from 'node:url';
import {verifyFixtures} from './fixtures/queue-state-owner16/verify.mjs';
verifyFixtures();
const inputs = JSON.parse(readFileSync(new URL('../../docs/reviews/worker16-04-queue-compatibility/inputs.json', import.meta.url)));
// Keep the reviewed logical paths/hashes historical while resolving current
// checkout locations through the accepted repository migration contract.
const movedPaths = new Map(JSON.parse(readFileSync(new URL('../../docs/standards/layout-migration-v2.json', import.meta.url))).moves.map(({from, to}) => [from, to]));
const selected = new Map();
for (const file of inputs.files) {
  const localPath = movedPaths.get(file.localPath) ?? file.localPath.replace(/^tests-web\//, 'tests/web/');
  const lf = readFileSync(new URL('../../' + localPath, import.meta.url), 'utf8').replaceAll('\r\n', '\n');
  assert.equal(createHash('sha256').update(lf).digest('hex'), file.sha256, file.localPath);
  if (file.inputCommit === inputs.d1Commit) selected.set(file.sourcePath, lf);
}

const origin = 'https://owner16-compatibility.invalid', audience = origin + '/api/state';
const script = `
import {createD1SessionStateProtocol,SESSION_STATE_D1_DDL} from 'compat04:cloud/session-state-d1-owner04.mjs';
import {createQueueStateWorker} from './apps/web/server/queue-state-entry-owner16.mjs';
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
    if(mode==='id')return {...result,operationId:'synthetic_other_operation'};
    if(mode==='version')return {...result,revision:result.revision+1};
    if(mode==='ack')return {...result,acknowledged:false};
    if(mode?.startsWith('binding:')){const field=mode.slice(8);return {...result,binding:{...result.binding,[field]:field==='epoch'?result.binding.epoch+1:'synthetic_mismatched_value'}};}
    if(mode==='expire-after-commit')await opts.database.prepare('UPDATE owner04_d1_sessions SET expires_at=0 WHERE id=?').bind(result.binding.sessionId).run();
    return result;};return p;
  }});
 return worker.fetch(request,env);
}};`;
const bundled = await build({stdin: {contents: script, resolveDir: fileURLToPath(new URL('../../', import.meta.url)), sourcefile: 'owner16-native-http-fixture.mjs'}, bundle: true, write: false, platform: 'browser', format: 'esm', plugins: [{name: 'exact-selected-04', setup(builder) {
  builder.onResolve({filter: /^compat04:/}, args => ({path: args.path.slice(9), namespace: 'compat04'}));
  builder.onResolve({filter: /^\./, namespace: 'compat04'}, args => ({path: posix.normalize(posix.join(posix.dirname(args.importer), args.path)), namespace: 'compat04'}));
  builder.onLoad({filter: /.*/, namespace: 'compat04'}, args => {
    assert.ok(selected.has(args.path), 'Missing selected closure path ' + args.path);
    return {contents: selected.get(args.path), loader: 'js'};
  });
}}]});
const state = () => ({inventory: [], products: {}, recipes: [], selections: [], profile: {country: 'AU', units: 'metric', servings: 2}});
const command = (operationId = 'native_operation_0001', expectedVersion = 0) => ({operationId, expectedVersion, state: state()});
async function fixture(t) {
  const mf = new Miniflare({modules: true, script: bundled.outputFiles[0].text, compatibilityDate: '2026-08-06', d1Databases: {DB: 'owner16-04-queue-compatibility-disposable'}});
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
// Independently assembled sorted-key digest for the explicit synthetic command.
const canonical = value => value === null || typeof value !== 'object' ? JSON.stringify(value) :
  Array.isArray(value) ? '[' + value.map(canonical).join(',') + ']' :
  '{' + Object.keys(value).sort().map(key => JSON.stringify(key) + ':' + canonical(value[key])).join(',') + '}';
const expectedDigest = op => createHash('sha256').update(canonical({audience, method: 'PUT', version: op.expectedVersion, state: op.state})).digest('hex');

test('exact selected 04 D1 and integrated queue agree on binding, digest, version and ACK', async t => {
  const f = await fixture(t), op = command('compatibility_exact_0001');
  const result = await f.send(op);
  assert.equal(result.status, 200); assert.equal(result.body.status, 'committed');
  assert.equal(result.body.confirmed, true); assert.equal(result.body.acknowledged, true);
  assert.deepEqual(result.body.binding, {subject: 'synthetic-alice', sessionId: f.a.sessionId,
    realm: f.a.realm, epoch: f.a.epoch, resource: audience});
  assert.equal(result.body.operationId, op.operationId); assert.equal(result.body.revision, op.expectedVersion + 1);
  assert.equal(result.body.digest, expectedDigest(op));
  const row = await f.db.prepare('SELECT session_id,subject,realm,epoch,operation_id,digest,result_json FROM owner04_d1_operations WHERE operation_id=?').bind(op.operationId).first();
  assert.equal(row.subject, result.body.binding.subject); assert.equal(row.session_id, result.body.binding.sessionId);
  assert.equal(row.realm, result.body.binding.realm); assert.equal(row.epoch, result.body.binding.epoch);
  assert.equal(row.operation_id, op.operationId); assert.equal(row.digest, expectedDigest(op));
  const outcome = JSON.parse(row.result_json);
  assert.deepEqual(outcome.binding, result.body.binding); assert.equal(outcome.revision, 1); assert.equal(outcome.acknowledged, true);
  assert.deepEqual((await f.send(op)).body, result.body); assert.equal(await f.count(), 1);
});

test('selected pair withholds damaged contract ACKs and recovers only the exact committed command', async t => {
  const f = await fixture(t);
  const modes = ['binding:subject','binding:sessionId','binding:realm','binding:epoch','binding:resource','digest','id','version','ack'];
  for (const [version, mode] of modes.entries()) {
    const op = command('compatibility_matrix_' + String(version).padStart(4, '0'), version);
    const damaged = await f.send(op, f.a, 'alice', {'X-Fixture-Outcome': mode});
    assert.equal(damaged.status, 503, mode); assert.equal(damaged.body.confirmed, false, mode);
    assert.equal((await f.db.prepare('SELECT revision FROM user_state WHERE user_id=?').bind('synthetic-alice').first()).revision, version + 1);
    const recovered = await f.recover(op);
    assert.equal(recovered.status, 200, mode); assert.equal(recovered.body.digest, expectedDigest(op));
    assert.equal(recovered.body.revision, version + 1); assert.equal(recovered.body.acknowledged, true);
    const changed = structuredClone(op); changed.state.profile.servings++;
    assert.equal((await f.recover(changed)).status, 503, mode);
  }
  assert.equal(await f.count(), modes.length);
  const conflict = await f.send(command('compatibility_stale_0001', 0));
  assert.equal(conflict.status, 409); assert.equal(conflict.body.confirmed, true);
  assert.equal(conflict.body.acknowledged, false); assert.equal(conflict.body.revision, modes.length);
});

test('matching selector grants no authority; late committed ACK survives expiry while new requests deny', async t => {
  const f = await fixture(t), op = command('compatibility_authority_01');
  // Selector resolves Alice's real enrollment; D1 separately checks authority.
  for (const [session, account] of [[f.a, 'bob'], [{...f.a, capability: 'x'.repeat(64)}, 'alice'],
      [{...f.a, epoch: f.a.epoch + 1}, 'alice'], [{...f.a, realm: 'synthetic_wrong_realm'}, 'alice']]) {
    assert.equal((await f.send(op, session, account)).status, 503);
    assert.equal(await f.count(), 0);
  }
  const late = await f.send(op, f.a, 'alice', {'X-Fixture-Outcome': 'expire-after-commit'});
  assert.equal(late.status, 200); assert.equal(late.body.digest, expectedDigest(op));
  assert.equal(late.body.acknowledged, true); assert.equal(late.body.revision, 1);
  assert.equal((await f.send(command('compatibility_expired_0001', 1))).status, 503);
  assert.equal((await f.recover(op)).status, 503); assert.equal(await f.count(), 1);
});
