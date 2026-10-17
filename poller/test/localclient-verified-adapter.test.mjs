import test from 'node:test';
import assert from 'node:assert/strict';
import { LocalClient } from '../src/transport.mjs';
import { PROJECT_PATH, validateConfig, verifyAdapter, validateCredentialHeaders } from '../src/contracts.mjs';
import verified from '../adapters/freebuff-verified.mjs';

// Integration through the SHIPPED caller boundary: LocalClient.snapshot invokes
// adapter.normalizeSnapshot(raw, { sessionId }) and then contracts.validateSnapshot.
// The raw response below is the verified live shape captured on this host
// (top-level {thread, messages, items}; pause state on thread.queuePaused). All
// content is redacted; no real credential or prompt text is used or printed.
const SESSION = 'bac212ab-b73c-4f64-a995-e57ee9ec0877'; // Morgan's bound target
const RAW_CREDENTIAL = JSON.stringify({ port: 26833, launchId: '00000000-0000-4000-8000-000000000001' });
const RAW_RESPONSE = {
  thread: {
    archivedAt: 1792034681554,
    id: SESSION,
    projectId: PROJECT_PATH,
    projectPath: PROJECT_PATH,
    title: 'REDACTED_TITLE',
    status: 'open',
    model: 'm-0000000000',
    agentMode: 'build',
    executionMode: 'local',
    executionTarget: 'local',
    turnState: 'idle',
    queuePaused: true,
    pendingWorkCount: 6,
  },
  messages: [
    { role: 'user', parts: [{ kind: 'text', text: 'REDACTED_INITIAL_USER_PROMPT' }], ts: 1792019481269 },
    { role: 'assistant', parts: [{ kind: 'reasoning', id: 'p1', text: 'REDACTED_REASONING' }, { kind: 'text', id: 'p2', text: 'REDACTED_ASSISTANT_TEXT' }], ts: 1792019481270 },
    { role: 'assistant', parts: [{ kind: 'tool' }, { kind: 'text', text: 'REDACTED_STREAMING' }] }, // in flight: no ts yet
  ],
  items: [{ id: '00000000-0000-4000-8000-000000000002', kind: 'prompt', state: 'queued' }],
};

const base = {
  schemaVersion: 1,
  gatewayUrl: 'https://gateway.example', // never contacted by LocalClient.snapshot
  localApiUrl: 'http://127.0.0.1:26833',
  projectPath: PROJECT_PATH,
  sessionIds: [SESSION],
  stateDir: '/tmp/private-relay-integration',
  localCredentialFile: '/tmp/private-local-credential-integration',
  pollerTokenFile: '/tmp/private-remote-token-integration',
  adapterFile: '/tmp/adapter-integration.mjs',
};
const config = () => validateConfig(base);
const GATEWAY_TOKEN = 'g'.repeat(43); // synthetic; never leaves the process

function client(overrides = {}) {
  const calls = [];
  const local = new LocalClient(config(), verified, GATEWAY_TOKEN, {
    read: () => RAW_CREDENTIAL,
    request: async (url, options) => {
      calls.push({ url: url.href, options });
      return overrides.response ?? RAW_RESPONSE;
    },
  });
  return { local, calls };
}

test('verified adapter passes the poller activation gate', () => {
  assert.doesNotThrow(() => verifyAdapter(verified));
});

test('adapter interface is the shipped object form; a bare sessionId string fails closed', () => {
  assert.doesNotThrow(() => verified.normalizeSnapshot(RAW_RESPONSE, { sessionId: SESSION }));
  assert.throws(() => verified.normalizeSnapshot(RAW_RESPONSE, SESSION), /LOCAL_ADAPTER_BAD_SNAPSHOT/);
});

test('LocalClient.snapshot normalizes the verified live response shape end to end', async () => {
  const { local, calls } = client();
  const snapshot = await local.snapshot(SESSION);

  assert.equal(calls.length, 1);
  assert.equal(calls[0].url, `http://127.0.0.1:26833/api/thread/${SESSION}?projectPath=${encodeURIComponent(PROJECT_PATH)}`);
  assert.deepEqual(
    Object.keys(calls[0].options.headers).filter(name => name !== 'accept'),
    ['x-freebuff-launch-id']
  );

  assert.deepEqual(snapshot, {
    sessionId: SESSION,
    paused: true,
    messages: [
      { id: 'msg-1792019481269-user', role: 'user', text: 'REDACTED_INITIAL_USER_PROMPT', timestamp: '2026-10-14T23:11:21.269Z' },
      { id: 'msg-1792019481270-assistant', role: 'assistant', text: 'REDACTED_ASSISTANT_TEXT', timestamp: '2026-10-14T23:11:21.270Z' },
    ],
  });
});

test('LocalClient.snapshot fails closed on session identity mismatch', async () => {
  const { local } = client({
    response: { ...RAW_RESPONSE, thread: { ...RAW_RESPONSE.thread, id: '00000000-0000-4000-8000-000000000099' } },
  });
  await assert.rejects(local.snapshot(SESSION), /LOCAL_ADAPTER_BAD_SNAPSHOT/);
});

test('LocalClient.snapshot fails closed on malformed responses', async () => {
  const { local } = client({ response: { thread: { id: SESSION }, messages: 'oops' } });
  await assert.rejects(local.snapshot(SESSION), /LOCAL_ADAPTER_BAD_SNAPSHOT/);
});

test('deliberate allowlist addition still rejects arbitrary headers and malformed values', () => {
  assert.deepEqual(validateCredentialHeaders({ 'x-freebuff-launch-id': '00000000-0000-4000-8000-000000000001' }),
    { 'x-freebuff-launch-id': '00000000-0000-4000-8000-000000000001' });
  assert.throws(() => validateCredentialHeaders({ host: 'external.example' }), /LOCAL_AUTH_INVALID/);
  assert.throws(() => validateCredentialHeaders({ 'x-freebuff-launch-id': 'bad\r\nx: y' }), /LOCAL_AUTH_INVALID/);
  assert.throws(() => validateCredentialHeaders({ 'x-freebuff-launch-id': 'short' }), /LOCAL_AUTH_INVALID/);
  assert.throws(() => validateCredentialHeaders({
    'x-freebuff-launch-id': '00000000-0000-4000-8000-000000000001',
    authorization: 'Bearer 00000000-0000-4000-8000-000000000002',
    'x-api-key': '00000000-0000-4000-8000-000000000003',
  }), /LOCAL_AUTH_INVALID/); // still at most 2 entries
});

test('local and gateway credentials remain independent through LocalClient.headers()', async () => {
  const same = 'same_fake_token_'.repeat(3);
  const local = new LocalClient(config(), verified, same, {
    read: () => JSON.stringify({ port: 26833, launchId: same }),
  });
  await assert.rejects(local.snapshot(SESSION), /CREDENTIALS_MUST_BE_INDEPENDENT/);
});
