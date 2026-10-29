import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {DatabaseSync} from 'node:sqlite';
import {createQueueStateBridge} from '../../cloud/queue-state-bridge-owner16.mjs';
import {verifyFixtures} from './fixtures/queue-state-owner16/verify.mjs';
import {createSessionStateProtocol, createSqliteStateStore, SESSION_STATE_DDL} from './fixtures/queue-state-owner16/sqlite04/cloud/session-state-owner04.mjs';
import {createStateQueueClient} from './fixtures/queue-state-owner16/predecessor16/public/durable-queue-owner16.mjs';
import {createDurableOperationQueue as createQueue} from './fixtures/queue-state-owner16/queue12/public/durable-operation-queue.js';
verifyFixtures();
const state = () => ({inventory: [], products: {}, recipes: [], selections: [], profile: {country: 'AU', units: 'metric', servings: 2}});
const command = (id = 'synthetic_operation_0001', version = 0) => ({operationId: id, expectedVersion: version, state: state()});
async function fixture(t, authenticate = async req => ({id: req.subject})) {
  let clock = 100;
  const db = new DatabaseSync(':memory:'); t.after(() => db.close());
  db.exec(readFileSync(new URL('./fixtures/queue-state-owner16/sqlite04/cloud/schema.sql', import.meta.url), 'utf8'));
  for (const sql of SESSION_STATE_DDL) db.exec(sql);
  const protocol = createSessionStateProtocol({store: createSqliteStateStore(db), authenticate,
    readSession: req => req.protectedSession, authorizeRequest: async () => true, authorizeEnrollment: async () => true,
    audience: 'https://offmenu.test/api/state', realm: 'synthetic_realm_0001', ttlMs: 10000, now: () => clock});
  const alice = await protocol.enroll({subject: 'synthetic-alice'}), bob = await protocol.enroll({subject: 'synthetic-bob'});
  const request = (session = alice, subject = 'synthetic-alice') => ({subject, protectedSession: session});
  const bridge = (selected = protocol, binding = alice.binding) => createQueueStateBridge({protocol: selected, trustedBinding: () => binding});
  return {db, protocol, alice, bob, request, bridge, expire: () => { clock = 20000; },
    rows: () => db.prepare('SELECT count(*) n FROM owner04_state_operations').get().n,
    revision: () => db.prepare('SELECT revision FROM user_state WHERE user_id=?').get('synthetic-alice')?.revision || 0};
}
test('bridge verifies exact digest, version and server binding; replay one effect and terminal stale conflict', async t => {
  const f = await fixture(t), b = f.bridge(), cmd = command();
  const result = await b.submit(f.request(), cmd); assert.equal(result.confirmed, true); assert.equal(result.acknowledged, true);
  assert.deepEqual(await b.submit(f.request(), cmd), result); assert.equal(f.rows(), 1); assert.equal(f.revision(), 1);
  const conflict = await b.submit(f.request(), command('synthetic_operation_stale'));
  assert.equal(conflict.status, 'conflict'); assert.equal(conflict.confirmed, true); assert.equal(conflict.acknowledged, false);
  assert.equal(f.revision(), 1); assert.equal(f.rows(), 2);
});
test('lost acknowledgement is unconfirmed; status reconciles exact operation/digest, not another payload', async t => {
  const f = await fixture(t), cmd = command();
  const transport = {...f.protocol, async mutate(req, op) { await f.protocol.mutate(req, op); throw Error('Lost response'); }};
  assert.equal((await f.bridge(transport).submit(f.request(), cmd)).confirmed, false);
  assert.equal((await f.bridge().recover(f.request(), cmd)).acknowledged, true);
  const altered = command(); altered.state.profile.servings = 3;
  assert.equal((await f.bridge().recover(f.request(), altered)).confirmed, false);
  assert.equal((await f.bridge().recover(f.request(), command('synthetic_missing_operation'))).confirmed, false);
  assert.equal(f.revision(), 1);
});
test('real SQLite rollback on failed ledger insertion leaves neither state nor ACK', async t => {
  const f = await fixture(t);
  f.db.exec("CREATE TRIGGER reject_outcome BEFORE INSERT ON owner04_state_operations BEGIN SELECT RAISE(ABORT,'fixture ledger failure'); END;");
  assert.equal((await f.bridge().submit(f.request(), command())).confirmed, false);
  assert.equal(f.rows(), 0); assert.equal(f.revision(), 0);
});
test('revoke-first rejects queued work/status; commit-first remains stored but revoked replay unconfirmed', async t => {
  const f = await fixture(t), cmd = command();
  assert.equal((await f.bridge().submit(f.request(), cmd)).confirmed, true);
  await f.protocol.revoke(f.request());
  assert.equal((await f.bridge().recover(f.request(), cmd)).confirmed, false);
  assert.equal((await f.bridge().submit(f.request(), command('synthetic_later_operation', 1))).confirmed, false);
  assert.equal(f.revision(), 1); assert.equal(f.rows(), 1);
  const bobBridge = f.bridge(f.protocol, f.bob.binding);
  await f.protocol.revoke(f.request(f.bob, 'synthetic-bob'));
  assert.equal((await bobBridge.submit(f.request(f.bob, 'synthetic-bob'), cmd)).confirmed, false);
  assert.equal(f.rows(), 1);
});
test('cross-account binding and body authority cannot confer ACK or authorize other account state', async t => {
  const f = await fixture(t);
  assert.equal((await f.bridge().submit(f.request(f.alice, 'synthetic-bob'), command())).confirmed, false);
  assert.equal(f.rows(), 0);
  await assert.rejects(f.bridge().submit(f.request(), {...command(), subject: 'synthetic-bob'}), /Invalid command/);
  const wrongSelector = f.bridge(f.protocol, f.bob.binding);
  assert.equal((await wrongSelector.submit(f.request(), command())).confirmed, false);
  assert.equal(f.revision(), 1); // Selector mismatch suppresses ACK, never pretends to undo a commit.
});
test('wrong digest/ID/version or reordered equal binding: new ACK boundary probes', async t => {
  const f = await fixture(t);
  const good = await f.protocol.mutate(f.request(), command());
  for (const patch of [{digest: '0'.repeat(64)}, {operationId: 'synthetic_wrong_operation'}, {revision: 50}, {acknowledged: false}]) {
    const selected = {...f.protocol, mutate: async () => ({...good, ...patch})};
    assert.equal((await f.bridge(selected).submit(f.request(), command())).confirmed, false);
  }
  const reordered = Object.fromEntries(Object.entries(good.binding).reverse());
  assert.equal((await f.bridge({...f.protocol, mutate: async () => ({...good, binding: reordered})}).submit(f.request(), command())).confirmed, true);
});
test('malformed and accessor outcomes stay unknown without invoking getters', async t => {
  const f = await fixture(t), good = await f.protocol.mutate(f.request(), command());
  let calls = 0;
  const accessor = {...good};
  Object.defineProperty(accessor, 'digest', {enumerable: true, get() { calls++; return good.digest; }});
  for (const damaged of [null, [], {}, {...good, digest: null}, {...good, digest: ''}, accessor]) {
    const selected = {...f.protocol, mutate: async () => damaged, status: async () => damaged};
    for (const method of ['submit', 'recover']) {
      const result = await f.bridge(selected)[method](f.request(), command());
      assert.equal(result.status, 'unknown');
      assert.equal(result.confirmed, false); assert.equal(result.acknowledged, false);
    }
  }
  assert.equal(calls, 0); assert.equal(f.rows(), 1); assert.equal(f.revision(), 1);
});
test('credentials/command are captured before auth awaits; getters never run', async t => {
  let hold = false, release, entered;
  const waiting = new Promise(resolve => { release = resolve; }), started = new Promise(resolve => { entered = resolve; });
  const f = await fixture(t, async req => { const id = req.subject; if (hold) { entered(); await waiting; } return {id}; });
  const req = f.request({...f.alice}), op = command(); hold = true;
  const result = f.bridge().submit(req, op); await started;
  req.protectedSession.capability = f.bob.capability; op.state.profile.servings = 99; op.operationId = 'synthetic_replaced_operation';
  release(); assert.equal((await result).confirmed, true);
  assert.equal(JSON.parse(f.db.prepare('SELECT state_json FROM user_state').get().state_json).profile.servings, 2);
  let calls = 0; const bad = command(); Object.defineProperty(bad.state.profile, 'servings', {enumerable: true, get() { calls++; return 3; }});
  await assert.rejects(f.bridge().submit(f.request(), bad), /Invalid JSON/); assert.equal(calls, 0);
});

test('demonstrated predecessor gap: valid-looking ACK with wrong digest passed consumer but bridge refuses', async t => {
  const f = await fixture(t), good = await f.protocol.mutate(f.request(), command());
  const damaged = {...good, digest: '0'.repeat(64)};
  const records = new Map();
  const old = createStateQueueClient({createQueue, publicBinding: f.alice.binding, now: () => 100,
    storage: {load: async key => records.get(key), save: async (key, value) => records.set(key, value)},
    locks: {request: (_key, _options, callback) => callback()}, service: {mutate: async () => damaged}});
  await old.enqueue({operationId: command().operationId, expectedRevision: 0, state: state(), expiresAt: 1000});
  assert.equal((await old.flush()).status, 'acknowledged'); // Actual immutable predecessor observation.
  const selected = {...f.protocol, mutate: async () => damaged};
  assert.equal((await f.bridge(selected).submit(f.request(), command())).confirmed, false);
});

test('late ACK confirms earlier commit; expired grant denies a new send and body expiresAt is never authority', async t => {
  const f = await fixture(t);
  const delayed = {...f.protocol, async mutate(req, op) {
    const committed = await f.protocol.mutate(req, op);
    f.expire(); // Response arrives after server grant expiry, effect already committed.
    return committed;
  }};
  assert.equal((await f.bridge(delayed).submit(f.request(), command())).acknowledged, true);
  assert.equal((await f.bridge().submit(f.request(), command('synthetic_post_expiry', 1))).confirmed, false);
  assert.equal((await f.bridge().recover(f.request(), command())).confirmed, false); // Status requires current authority.
  await assert.rejects(f.bridge().submit(f.request(), {...command(), expiresAt: 999999}), /Invalid command/);
  assert.equal(f.revision(), 1); assert.equal(f.rows(), 1);
});
