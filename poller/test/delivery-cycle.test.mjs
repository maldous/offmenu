import test from 'node:test';
import assert from 'node:assert/strict';
import http from 'node:http';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { Journal } from '../src/journal.mjs';
import { Poller } from '../src/engine.mjs';
import { LocalClient, GatewayClient } from '../src/transport.mjs';
import { PROJECT_PATH, RETENTION_MS, payloadHash, queueText, validateConfig } from '../src/contracts.mjs';
import verified from '../adapters/freebuff-verified.mjs';

// Full delivery cycle through the REAL shipped stack: real Journal (SQLite WAL),
// real Poller engine, real LocalClient over real HTTP (requestJson) to a loopback
// stub local API, real GatewayClient protocol against a stub gateway handler.
// Only the two network endpoints are stubs. The stub local API serves the
// verified live response shape and records every queue POST with the journal
// state observed at POST time. No real credentials, sessions, or writes.

const SESSION = '11111111-1111-4111-8111-111111111111';
const LAUNCH_ID = '00000000-0000-4000-8000-000000000001';
const GATEWAY_TOKEN = 'g'.repeat(43);
const TEXT = 'Please inspect the existing test failure.';
const REQUEST_ID = '33333333-3333-4333-8333-333333333333';
const LEASE_ID = '44444444-4444-4444-8444-444444444444';

const lease = now => ({
  requestId: REQUEST_ID,
  sessionId: SESSION,
  text: TEXT,
  payloadHash: payloadHash(SESSION, TEXT),
  leaseId: LEASE_ID,
  leaseExpiresAt: now + 300000,
  acceptedAt: now,
  expiresAt: now + RETENTION_MS,
});

async function fixture(t, { queuePaused } = {}) {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'delivery-cycle-'));
  const state = {
    queuePaused,
    messages: [{ role: 'user', parts: [{ kind: 'text', text: 'seeded message' }], ts: 1 }],
    posts: [],
    lastQueuedTs: null,
  };
  let journal;
  const server = http.createServer((req, res) => {
    const url = new URL(req.url, 'http://127.0.0.1');
    if (req.method === 'GET' && url.pathname === `/api/thread/${SESSION}`) {
      const thread = { id: SESSION, projectPath: PROJECT_PATH, title: 'REDACTED', status: 'open', turnState: 'idle', pendingWorkCount: 0 };
      if (state.queuePaused !== undefined) thread.queuePaused = state.queuePaused;
      res.writeHead(200, { 'content-type': 'application/json' });
      res.end(JSON.stringify({ thread, messages: state.messages, items: [] }));
      return;
    }
    if (req.method === 'POST' && url.pathname === `/api/thread/${SESSION}/queue`) {
      let raw = '';
      req.on('data', chunk => { raw += chunk; });
      req.on('end', () => {
        const body = JSON.parse(raw);
        // Durable-intent evidence: 'sending' must already be committed at POST time.
        const intentState = journal.get(REQUEST_ID).state;
        state.posts.push({ headers: req.headers, body, intentState });
        const ts = Date.now();
        state.lastQueuedTs = ts;
        state.messages.push({ role: 'user', parts: [{ kind: 'text', text: body.text }], ts });
        res.writeHead(200, { 'content-type': 'application/json' });
        res.end(JSON.stringify({ ok: true }));
      });
      return;
    }
    res.writeHead(404, { 'content-type': 'application/json' });
    res.end(JSON.stringify({ error: 'not found' }));
  });
  await new Promise(resolve => server.listen(0, '127.0.0.1', resolve));

  const credentialFile = path.join(dir, 'local-credential');
  fs.writeFileSync(credentialFile, JSON.stringify({ port: server.address().port, launchId: LAUNCH_ID }), { mode: 0o600 });
  const tokenFile = path.join(dir, 'remote-token');
  fs.writeFileSync(tokenFile, GATEWAY_TOKEN, { mode: 0o600 });

  const config = validateConfig({
    schemaVersion: 1,
    gatewayUrl: 'https://gateway.example', // stubbed at the request handler below
    localApiUrl: `http://127.0.0.1:${server.address().port}`,
    projectPath: PROJECT_PATH,
    sessionIds: [SESSION],
    stateDir: dir,
    localCredentialFile: credentialFile,
    pollerTokenFile: tokenFile,
    adapterFile: path.join(dir, 'adapter.mjs'),
  });

  journal = new Journal(path.join(dir, 'journal.sqlite'), () => Date.now());
  const local = new LocalClient(config, verified, GATEWAY_TOKEN); // real readPrivateFile + requestJson
  const gatewayCalls = [];
  let incoming = null;
  const gateway = new GatewayClient(config, GATEWAY_TOKEN, {
    request: async (url, options) => {
      gatewayCalls.push({ path: url.pathname, headers: options.headers, body: options.body });
      if (url.pathname === '/bridge/poll') return { lease: incoming, commands: [] };
      if (url.pathname === '/bridge/report') {
        return { requestId: options.body.requestId, payloadHash: payloadHash(SESSION, TEXT), state: options.body.state };
      }
      if (url.pathname === '/bridge/snapshot') return { ok: true };
      throw new Error(`unexpected gateway path ${url.pathname}`);
    },
  });
  const poller = new Poller({ config, journal, local, gateway });

  t.after(async () => {
    journal.close();
    await new Promise(resolve => server.close(resolve));
    fs.rmSync(dir, { recursive: true, force: true });
  });
  return { state, journal, poller, gatewayCalls, setLease: value => { incoming = value; } };
}

test('full delivery cycle: lease -> durable sending -> queue POST now:false -> exact readback -> delivered -> ack', async t => {
  const f = await fixture(t, { queuePaused: false });
  const request = lease(Date.now());
  f.setLease(request);
  await f.poller.tick();

  assert.equal(f.state.posts.length, 1);
  const post = f.state.posts[0];
  assert.equal(post.intentState, 'sending', 'sending intent is durable before the only local write');
  assert.deepEqual(post.body, { projectPath: PROJECT_PATH, text: queueText(request), now: false });
  assert.equal(post.headers['x-freebuff-launch-id'], LAUNCH_ID);
  assert.ok(!JSON.stringify(post.headers).includes(GATEWAY_TOKEN), 'poller token never sent to the local API');

  const record = f.journal.get(request.requestId);
  assert.equal(record.state, 'delivered');
  const report = f.gatewayCalls.find(call => call.path === '/bridge/report').body;
  assert.equal(report.requestId, request.requestId);
  assert.equal(report.leaseId, LEASE_ID);
  assert.equal(report.state, 'delivered');
  assert.equal(report.evidence, `exact_marker:msg-${f.state.lastQueuedTs}-user`, 'evidence is the exact user-message readback id');

  const poll = f.gatewayCalls.find(call => call.path === '/bridge/poll');
  assert.equal(poll.headers.authorization, `Bearer ${GATEWAY_TOKEN}`);
  assert.ok(!JSON.stringify(f.gatewayCalls).includes(LAUNCH_ID), 'local credential never reaches the gateway');

  const publication = f.gatewayCalls.find(call => call.path === '/bridge/snapshot').body;
  assert.equal(publication.sessionId, SESSION);
  assert.equal(publication.paused, false);
  assert.ok(publication.messages.length >= 1);

  // Replay protection: the same lease is never posted twice.
  await f.poller.handle(request);
  assert.equal(f.state.posts.length, 1);
});

for (const [queuePaused, reason] of [[true, 'SESSION_PAUSED'], [undefined, 'PAUSE_STATE_UNKNOWN']]) {
  test(`queuePaused=${queuePaused} rejects delivery with zero local writes`, async t => {
    const f = await fixture(t, { queuePaused });
    const request = lease(Date.now());
    f.setLease(request);
    await f.poller.tick();

    assert.equal(f.state.posts.length, 0);
    const record = f.journal.get(request.requestId);
    assert.equal(record.state, 'failed');
    assert.equal(record.reason, reason);
  });
}
