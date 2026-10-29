import test from 'node:test';
import assert from 'node:assert/strict';
import {execFileSync} from 'node:child_process';
import {createHash} from 'node:crypto';
import {DatabaseSync} from 'node:sqlite';
import {readFileSync} from 'node:fs';
import {createQueueStateBridge} from '../cloud/queue-state-bridge-owner16.mjs';
const env = Object.fromEntries(Object.entries(process.env).filter(([key]) => !key.startsWith('GIT_')));
const bytes = execFileSync('git', ['show', '25543bd75c3812a203e0d3b865d51302bfe1854d:cloud/session-state-owner04.mjs'], {env});
assert.equal(createHash('sha256').update(bytes).digest('hex'), '4520436816c70f93028fbbef38fdec572018dd507a8489c9027bb528af6f0be5');
assert.equal(createHash('sha256').update(readFileSync(new URL('../cloud/state.mjs', import.meta.url))).digest('hex'), '801c68accc3a21fa59756e8cc8029251319ff0266ad93152563ad499f666b88b');
const source = bytes.toString().replace("'./state.mjs'", JSON.stringify(new URL('../cloud/state.mjs', import.meta.url).href));
const {createSessionStateProtocol, createSqliteStateStore, SESSION_STATE_DDL} = await import('data:text/javascript;base64,' + bytesToBase64(source));
function bytesToBase64(text) { return Buffer.from(text).toString('base64'); }
const state = () => ({inventory: [], products: {}, recipes: [], selections: [], profile: {country: 'AU', units: 'metric', servings: 2}});
const command = (id = 'synthetic_operation_0001', version = 0) => ({operationId: id, expectedVersion: version, state: state()});
async function fixture(t, authenticate = async req => ({id: req.subject})) {
  let clock = 100;
  const db = new DatabaseSync(':memory:'); t.after(() => db.close());
  db.exec(readFileSync(new URL('../cloud/schema.sql', import.meta.url), 'utf8'));
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
  const oldSource = execFileSync('git', ['show', '61192ddba1c40747b974a45d5ed2fdad368d6c3d:public/durable-queue-owner16.mjs'], {env, encoding: 'utf8'});
  const queueSource = execFileSync('git', ['show', '0e7279a7b3ba9e8d68f5aba546d2404fc3fc99a9:public/durable-operation-queue.js'], {env, encoding: 'utf8'});
  const {createStateQueueClient} = await import('data:text/javascript;base64,' + bytesToBase64(oldSource));
  const {createDurableOperationQueue: createQueue} = await import('data:text/javascript;base64,' + bytesToBase64(queueSource));
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
