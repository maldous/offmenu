import test from 'node:test';
import assert from 'node:assert/strict';
import {createQueueStateHttpHandler} from '../../apps/web/server/queue-state-bridge-owner16.mjs';
const origin = 'https://offmenu.test';
const command = {operationId: 'synthetic_operation_http1', expectedVersion: 0,
  state: {profile: {ownerMetadata: {source: 'synthetic', qualifier: 'unknown'}}}};
function request(body = command, path = '/api/private/v2/state', method = 'PUT') {
  return new Request(origin + path, {method, headers: {Origin: origin, 'Content-Type': 'application/json', 'X-Synthetic-Session': 'fixture-session'}, body: JSON.stringify(body)});
}
// Prepared HTTP seam tests only: no D1-candidate import/adoption or server started.
test('HTTP seam forwards exact metadata and cloned headers, with explicit confirmed ACK response', async () => {
  let observed;
  const bridge = {async submit(req, value) {
    observed = {session: req.headers.get('X-Synthetic-Session'), value};
    return {status: 'committed', acknowledged: true, confirmed: true};
  }, async recover() { assert.fail('Not recovery'); }};
  const handler = createQueueStateHttpHandler({bridge, origin}), req = request();
  const pending = handler(req); req.headers.set('X-Synthetic-Session', 'changed-after-call');
  const response = await pending;
  assert.equal(response.status, 200); assert.equal(response.headers.get('Cache-Control'), 'private, no-store');
  assert.deepEqual(observed.value, command); assert.equal(observed.session, 'fixture-session');
});
test('HTTP-like success without qualified ACK remains unknown; conflicts do not become successful queue ACKs', async () => {
  for (const [outcome, status] of [[{ok: true}, 503], [{status: 'committed', acknowledged: true, confirmed: false}, 503],
    [{status: 'conflict', acknowledged: false, confirmed: true}, 409]]) {
    const handler = createQueueStateHttpHandler({origin, bridge: {submit: async () => outcome, recover: async () => outcome}});
    const response = await handler(request()); assert.equal(response.status, status);
    assert.equal((await response.json()).acknowledged, false);
  }
  const lost = createQueueStateHttpHandler({origin, bridge: {submit: async () => { throw Error('Lost after commit'); }, recover: async () => {}}});
  assert.equal((await lost(request())).status, 503);
});
test('status HTTP request forwards the original command for digest recovery, not a bare operation lookup', async () => {
  const handler = createQueueStateHttpHandler({origin, bridge: {submit: async () => assert.fail('Not send'),
    async recover(req, value) { assert.deepEqual(value, command); return {status: 'unknown', acknowledged: false, confirmed: false}; }}});
  assert.equal((await handler(request(command, '/api/private/v2/state/status', 'POST'))).status, 503);
});
test('wrong origin/method/route, invalid JSON and byte cap stop before protocol dispatch', async () => {
  let calls = 0;
  const handler = createQueueStateHttpHandler({origin, maxBytes: 256,
    bridge: {submit: async () => { calls++; }, recover: async () => { calls++; }}});
  const wrong = request(); wrong.headers.set('Origin', 'https://other.test');
  assert.equal((await handler(wrong)).status, 403);
  assert.equal((await handler(request(command, '/api/private/v2/state', 'POST'))).status, 405);
  assert.equal((await handler(request(command, '/api/state'))).status, 404);
  assert.equal((await handler(request({text: 'x'.repeat(256)}))).status, 413);
  const invalid = new Request(origin + '/api/private/v2/state', {method: 'PUT', headers: {Origin: origin, 'Content-Type': 'application/json'}, body: '{'});
  assert.equal((await handler(invalid)).status, 400);
  assert.equal(calls, 0);
});
