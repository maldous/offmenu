import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import http from 'node:http';
import { spawnSync } from 'node:child_process';
import { Journal } from '../src/journal.mjs';
import { Poller } from '../src/engine.mjs';
import { LocalClient, GatewayClient, readPrivateFile, requestJson } from '../src/transport.mjs';
import { EXCLUDED_SESSION_ID, MAX_TEXT_BYTES, PROJECT_PATH, RETENTION_MS, payloadHash, queueText,
  validateConfig, validateLease, remoteSnapshot, markerEvidence, validateSnapshot, SafeError, HttpError } from '../src/contracts.mjs';
import unverified from '../adapters/unverified.mjs';

const SESSION = '11111111-1111-4111-8111-111111111111';
const SECOND_SESSION = '22222222-2222-4222-8222-222222222222';
const NOW = 1800000000000;
const base = {
  schemaVersion: 1, gatewayUrl: 'https://gateway.example', localApiUrl: 'http://127.0.0.1:4321',
  projectPath: PROJECT_PATH, sessionIds: [SESSION], stateDir: '/tmp/private-relay',
  localCredentialFile: '/tmp/private-local-credential', pollerTokenFile: '/tmp/private-remote-token',
  adapterFile: '/tmp/adapter.mjs'
};
const config = () => validateConfig(base);
const lease = (changes = {}) => ({ requestId: '33333333-3333-4333-8333-333333333333', sessionId: SESSION,
  text: 'Please inspect the existing test failure.', payloadHash: payloadHash(SESSION, 'Please inspect the existing test failure.'),
  leaseId: '44444444-4444-4444-8444-444444444444', leaseExpiresAt: NOW + 300000,
  acceptedAt: NOW, expiresAt: NOW + RETENTION_MS, ...changes });
const message = (text, role = 'user') => ({ id: 'm-1', role, text, timestamp: new Date(NOW).toISOString() });
const snapshot = (changes = {}) => ({ sessionId: SESSION, paused: false, messages: [], ...changes });
const adapter = { verified: true, schemaVersion: 1,
  extractCredential: raw => ({ authorization: `Bearer ${JSON.parse(raw).testOnlyToken}` }),
  normalizeSnapshot: raw => raw };

function fixture(t, options = {}) {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'freebuff-poller-test-'));
  let time = NOW;
  const now = () => time;
  const journal = new Journal(path.join(dir, 'journal.sqlite'), now);
  t.after(() => { try { journal.close(); } catch {} fs.rmSync(dir, { recursive: true, force: true }); });
  const posted = []; const reports = []; const snapshots = [];
  let localSnapshot = snapshot(); let incoming = null;
  const local = {
    secrets: [], snapshot: async () => structuredClone(localSnapshot),
    queue: async (sessionId, text) => {
      assert.equal(journal.get(lease().requestId).state, 'sending', 'intent is durable before POST');
      posted.push({ sessionId, text });
      if (options.ambiguous) throw new Error('fake secret must never be reported');
      if (!options.noReadback) localSnapshot.messages.push(message(text));
      return { ignored: 'unverified queue response' };
    }
  };
  const gateway = { poll: async () => ({ lease: incoming, commands: [] }),
    report: async report => { if (options.reportFail) throw new Error('offline'); reports.push(report);
      return { ...report, payloadHash: journal.get(report.requestId).payloadHash }; },
    snapshot: async value => { snapshots.push(value); return { ok: true }; } };
  const poller = new Poller({ config: config(), journal, local, gateway, now });
  return { dir, now, journal, poller, local, gateway, posted, reports, snapshots,
    setTime: value => { time = value; }, setSnapshot: value => { localSnapshot = value; },
    setLease: value => { incoming = value; } };
}

test('configuration requires literal loopback, fixed project, separate tokens, and 1–3 sessions', () => {
  assert.equal(config().intervalMs, 30000);
  assert.equal(config().snapshotIntervalMs, 60000);
  for (const localApiUrl of ['https://example.com', 'http://localhost:1', 'http://127.0.0.2:1', 'http://127.0.0.1:1/path', 'http://user:pass@127.0.0.1:1']) {
    assert.throws(() => validateConfig({ ...base, localApiUrl }));
  }
  assert.equal(validateConfig({ ...base, localApiUrl: 'http://[::1]:4321' }).localApiUrl, 'http://[::1]:4321');
  assert.throws(() => validateConfig({ ...base, gatewayUrl: 'http://gateway.example' }));
  assert.throws(() => validateConfig({ ...base, projectPath: '/etc' }));
  assert.throws(() => validateConfig({ ...base, sessionIds: [] }));
  assert.throws(() => validateConfig({ ...base, sessionIds: [SESSION, SESSION] }));
  assert.throws(() => validateConfig({ ...base, sessionIds: [EXCLUDED_SESSION_ID] }));
  assert.throws(() => validateConfig({ ...base, pollerTokenFile: base.localCredentialFile }));
});

test('lease requires canonical hash, UUIDv4 identity, allowlist, byte bound, and marker-free text', () => {
  assert.equal(validateLease(lease(), config(), NOW).payloadHash, lease().payloadHash);
  for (const changes of [{ payloadHash: '0'.repeat(64) }, { sessionId: SECOND_SESSION }, { requestId: '../../etc/passwd' },
    { leaseId: 'not-a-lease' }, { text: '€'.repeat(MAX_TEXT_BYTES) }, { text: '[freebuff-relay requestId=spoof]' }]) {
    assert.throws(() => validateLease(lease(changes), config(), NOW));
  }
});

test('unverified adapter fails before credentials are read or network used', () => {
  let read = false;
  assert.throws(() => new LocalClient(config(), unverified, 'x'.repeat(48), { read: () => { read = true; } }), /LOCAL_ADAPTER_UNVERIFIED/);
  assert.equal(read, false);
});

test('local client sends only exact permitted paths, local auth, and now:false', async () => {
  const calls = [];
  const local = new LocalClient(config(), adapter, 'remote_fake_token_'.repeat(3), {
    read: () => JSON.stringify({ testOnlyToken: 'local_fake_token_'.repeat(3) }),
    request: async (url, options) => { calls.push({ url: url.href, options }); return snapshot(); }
  });
  await local.snapshot(SESSION);
  await local.queue(SESSION, 'hello');
  assert.equal(calls[0].url, `http://127.0.0.1:4321/api/thread/${SESSION}?projectPath=${encodeURIComponent(PROJECT_PATH)}`);
  assert.equal(calls[1].url, `http://127.0.0.1:4321/api/thread/${SESSION}/queue`);
  assert.deepEqual(calls[1].options.body, { projectPath: PROJECT_PATH, text: 'hello', now: false });
  assert.ok(calls[1].options.headers.authorization.includes('local_fake_token_'));
  assert.ok(!JSON.stringify(calls).includes('remote_fake_token_'));
  await assert.rejects(local.queue(SECOND_SESSION, 'hello'), /SESSION_NOT_ALLOWED/);
});

test('remote client has only gateway bearer, no local credential', async () => {
  let seen;
  const gateway = new GatewayClient(config(), 'remote_fake_token_'.repeat(3), { request: async (url, options) => { seen = { url, options }; return { ok: true }; } });
  await gateway.poll();
  assert.equal(seen.url.pathname, '/bridge/poll');
  assert.equal(seen.options.headers.authorization, `Bearer ${'remote_fake_token_'.repeat(3)}`);
});

test('identical credentials or unsafe auth headers are rejected', async () => {
  const same = 'same_fake_token_'.repeat(3);
  const local = new LocalClient(config(), adapter, same, { read: () => JSON.stringify({ testOnlyToken: same }) });
  await assert.rejects(local.snapshot(SESSION), /CREDENTIALS_MUST_BE_INDEPENDENT/);
  const unsafe = new LocalClient(config(), { ...adapter, extractCredential: () => ({ host: 'external.example' }) }, same, { read: () => '{}' });
  await assert.rejects(unsafe.snapshot(SESSION), /LOCAL_AUTH_INVALID/);
});

test('private credential files reject symlinks and readable-by-others mode', t => {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'private-file-test-'));
  t.after(() => fs.rmSync(dir, { recursive: true, force: true }));
  const file = path.join(dir, 'fake');
  fs.writeFileSync(file, 'test-only-no-secret', { mode: 0o600 });
  assert.equal(readPrivateFile(file), 'test-only-no-secret');
  fs.symlinkSync(file, path.join(dir, 'link'));
  assert.throws(() => readPrivateFile(path.join(dir, 'link')));
  fs.chmodSync(file, 0o644);
  assert.throws(() => readPrivateFile(file), /PRIVATE_FILE_PERMISSIONS/);
});

test('queue is delivered only after exact user-message readback; replay never posts twice', async t => {
  const f = fixture(t);
  await f.poller.handle(lease());
  assert.equal(f.journal.get(lease().requestId).state, 'delivered');
  assert.equal(f.posted.length, 1);
  assert.equal(f.journal.reports()[0].payload.evidence, 'exact_marker:m-1');
  await f.poller.handle(lease());
  assert.equal(f.posted.length, 1);
  await f.poller.flushReports();
  assert.deepEqual(f.reports.map(report => report.state), ['delivered']);
  assert.equal(f.journal.reports().length, 0);
});

for (const paused of [true, null]) test(`paused=${paused} never permits a POST`, async t => {
  const f = fixture(t);
  f.setSnapshot(snapshot({ paused }));
  await f.poller.handle(lease());
  assert.equal(f.posted.length, 0);
  assert.equal(f.journal.get(lease().requestId).state, 'failed');
});

test('configured pause wins over a local unpaused response', async t => {
  const f = fixture(t);
  f.poller.config = validateConfig({ ...base, pausedSessionIds: [SESSION] });
  await f.poller.handle(lease());
  assert.equal(f.posted.length, 0);
  assert.equal(f.journal.get(lease().requestId).reason, 'SESSION_CONFIGURED_PAUSED');
});

test('expired lease never posts even if expiry occurs during snapshot read', async t => {
  const f = fixture(t);
  f.local.snapshot = async () => { f.setTime(NOW + 500000); return snapshot(); };
  await f.poller.handle(lease());
  assert.equal(f.posted.length, 0);
  assert.equal(f.journal.get(lease().requestId).reason, 'LEASE_EXPIRED_BEFORE_ATTEMPT');
});

test('ambiguous POST is permanently non-retryable until positive exact evidence', async t => {
  const f = fixture(t, { ambiguous: true });
  await f.poller.handle(lease());
  assert.equal(f.journal.get(lease().requestId).state, 'uncertain');
  await f.poller.handle(lease());
  assert.equal(f.posted.length, 1);
  f.setSnapshot(snapshot({ messages: [message(queueText(lease()), 'assistant')] }));
  await f.poller.handle(lease());
  assert.equal(f.journal.get(lease().requestId).state, 'uncertain');
  f.setSnapshot(snapshot({ messages: [message(queueText(lease()))] }));
  await f.poller.handle(lease());
  assert.equal(f.journal.get(lease().requestId).state, 'delivered');
  assert.equal(f.posted.length, 1);
  assert.ok(!JSON.stringify(f.journal.reports()).includes('fake secret'));
});

test('2xx queue without readback is uncertain, not delivered or started', async t => {
  const f = fixture(t, { noReadback: true });
  await f.poller.handle(lease());
  assert.equal(f.journal.get(lease().requestId).state, 'uncertain');
  assert.equal(f.posted.length, 1);
});

test('exact marker requires entire exact original user text, not a substring or assistant quote', () => {
  assert.equal(markerEvidence(snapshot({ messages: [message(`prefix ${queueText(lease())}`)] }), lease()), null);
  assert.equal(markerEvidence(snapshot({ messages: [message(queueText(lease()), 'assistant')] }), lease()), null);
  assert.equal(markerEvidence(snapshot({ messages: [message(queueText(lease()))] }), lease()), 'exact_marker:m-1');
});

test('durable sending intent recovers as uncertain across process/database restart', async t => {
  const f = fixture(t);
  f.journal.accept(lease()); f.journal.transition(lease().requestId, 'sending'); f.journal.close();
  const recovered = new Journal(path.join(f.dir, 'journal.sqlite'), f.now);
  t.after(() => recovered.close());
  recovered.recover();
  f.poller.journal = recovered;
  await f.poller.handle(lease());
  assert.equal(recovered.get(lease().requestId).state, 'uncertain');
  assert.equal(f.posted.length, 0);
  assert.equal(recovered.reports()[0].payload.reason, 'PROCESS_INTERRUPTED_AFTER_INTENT');
});

test('pre-attempt accepted state can resume after restart', async t => {
  const f = fixture(t);
  f.journal.accept(lease()); f.journal.recover();
  await f.poller.handle(lease());
  assert.equal(f.posted.length, 1);
});

test('request identity cannot be rebound to a changed hash/session/lease', t => {
  const f = fixture(t);
  f.journal.accept(lease());
  for (const changes of [{ payloadHash: '0'.repeat(64) }, { sessionId: SECOND_SESSION }, { leaseId: '55555555-5555-4555-8555-555555555555' }]) {
    assert.throws(() => f.journal.accept(lease(changes)), /REQUEST_ID_REUSE/);
  }
});

test('report failure preserves durable outbox; retry does not redeliver', async t => {
  const f = fixture(t, { reportFail: true });
  await f.poller.handle(lease());
  await assert.rejects(f.poller.flushReports());
  assert.equal(f.journal.reports().length, 1);
  await f.poller.handle(lease());
  assert.equal(f.posted.length, 1);
});

test('mismatched report acknowledgment never removes durable outbox', async t => {
  const f = fixture(t);
  await f.poller.handle(lease());
  f.gateway.report = async () => ({ requestId: lease().requestId, payloadHash: 'wrong', state: 'delivered' });
  await assert.rejects(f.poller.flushReports(), /REPORT_ACK_MISMATCH/);
  assert.equal(f.journal.reports().length, 1);
});

for (const [status, code] of [[403, 'SESSION_NOT_ALLOWED'], [404, 'REQUEST_NOT_FOUND']]) test(`confirmed ${code} retires only outbox without authorizing redelivery`, async t => {
  const f = fixture(t);
  await f.poller.handle(lease());
  f.gateway.report = async () => { throw new HttpError(status, code); };
  await f.poller.flushReports();
  assert.equal(f.journal.reports().length, 0);
  assert.equal(f.journal.get(lease().requestId).state, 'delivered');
  await f.poller.handle(lease());
  assert.equal(f.posted.length, 1);
  await f.poller.tick();
  assert.equal(f.snapshots.length, 1);
});

for (const status of [403, 404]) test(`unrecognized HTTP${status} preserves durable outbox`, async t => {
  const f = fixture(t);
  await f.poller.handle(lease());
  f.gateway.report = async () => { throw new HttpError(status); };
  await assert.rejects(f.poller.flushReports(), new RegExp(`HTTP_${status}`));
  assert.equal(f.journal.reports().length, 1);
});

test('expiring an old accepted request cannot create a fresh blocking report', t => {
  const f = fixture(t);
  f.journal.accept(lease());
  f.setTime(NOW + RETENTION_MS + 1); f.journal.prune();
  assert.equal(f.journal.get(lease().requestId).state, 'failed');
  assert.equal(f.journal.get(lease().requestId).text, null);
  assert.equal(f.journal.reports().length, 0);
});

test('local payload retention follows gateway acceptance, not lease acquisition', t => {
  const f = fixture(t);
  const old = lease({ acceptedAt: NOW - RETENTION_MS + 1000, expiresAt: NOW + 1000 });
  assert.equal(validateLease(old, config(), NOW).expiresAt, NOW + 1000);
  f.journal.accept(old);
  f.setTime(NOW + 1001); f.journal.prune();
  assert.equal(f.journal.get(old.requestId).text, null);
  assert.equal(f.journal.reports().length, 0);
});

test('request expiry prevents posting even while its delivery lease remains valid', async t => {
  const f = fixture(t);
  await f.poller.handle(lease({ acceptedAt: NOW - RETENTION_MS, expiresAt: NOW }));
  assert.equal(f.posted.length, 0);
  assert.equal(f.journal.get(lease().requestId).state, 'failed');
});

test('retention removes payload but keeps identity tombstone and prohibits redelivery', async t => {
  const f = fixture(t, { ambiguous: true });
  await f.poller.handle(lease());
  f.setTime(NOW + RETENTION_MS + 1); f.journal.prune();
  assert.equal(f.journal.get(lease().requestId).text, null);
  await f.poller.handle(lease());
  assert.equal(f.posted.length, 1);
});

test('snapshot publication is bounded and strips known credentials', () => {
  const secret = 'local_fake_secret_0123456789';
  const data = snapshot({ messages: Array.from({ length: 100 }, (_, index) => ({ ...message(`${secret}${'x'.repeat(5000)}`), id: `m-${index}` })) });
  const output = remoteSnapshot(data, NOW, [secret]);
  assert.equal(output.messages.length, 40);
  assert.ok(output.messages.every(value => value.text.length <= 4096));
  assert.ok(!JSON.stringify(output).includes(secret));
  assert.ok(output.messages[0].text.startsWith('[truncated]\n'));
  assert.equal(output.observedAt, NOW);
});

test('malformed and unknown paused snapshots fail closed', () => {
  for (const bad of [snapshot({ paused: undefined }), snapshot({ paused: 'false' }), snapshot({ sessionId: SECOND_SESSION }),
    snapshot({ messages: [message('hi', 'tool')] })]) assert.throws(() => validateSnapshot(bad, SESSION));
});

test('polling has no command or lifecycle inference capability and snapshots default to 60 seconds', async t => {
  const f = fixture(t);
  await f.poller.tick(); assert.equal(f.snapshots.length, 1);
  f.setTime(NOW + 30000); await f.poller.tick(); assert.equal(f.snapshots.length, 1);
  f.setTime(NOW + 60000); await f.poller.tick(); assert.equal(f.snapshots.length, 2);
  f.gateway.poll = async () => ({ lease: null, commands: [{ type: 'resume', sessionId: SESSION }] });
  await assert.rejects(f.poller.tick(), /POLL_RESPONSE_INVALID/);
  assert.equal(f.posted.length, 0);
});

test('HTTP transport refuses redirects and caps streamed response sizes', async t => {
  let redirectedHits = 0;
  const server = http.createServer((req, res) => {
    if (req.url === '/redirect') { res.writeHead(302, { location: '/destination' }); res.end(); }
    else if (req.url === '/big') { res.end(JSON.stringify({ text: 'x'.repeat(200) })); }
    else { redirectedHits++; res.end('{}'); }
  });
  await new Promise(resolve => server.listen(0, '127.0.0.1', resolve));
  t.after(() => new Promise(resolve => server.close(resolve)));
  const origin = `http://127.0.0.1:${server.address().port}`;
  await assert.rejects(requestJson(new URL('/redirect', origin)), /HTTP_302/);
  await assert.rejects(requestJson(new URL('/big', origin), { maxBytes: 20 }), /RESPONSE_TOO_LARGE/);
  assert.equal(redirectedHits, 0);
});

test('HTTP transport recognizes only bounded exact gateway receipt error envelopes', async t => {
  const server = http.createServer((req, res) => {
    const cases = {
      '/missing': [404, 'application/json', '{"error":"REQUEST_NOT_FOUND"}'],
      '/revoked': [403, 'application/json; charset=utf-8', '{"error":"SESSION_NOT_ALLOWED"}'],
      '/waf': [403, 'text/html', '<h1>Temporarily blocked</h1>'],
      '/route': [404, 'application/json', '{"error":"NOT_FOUND"}'],
      '/wrong-type': [404, 'text/html', '{"error":"REQUEST_NOT_FOUND"}'],
      '/wrong-status': [403, 'application/json', '{"error":"REQUEST_NOT_FOUND"}']
    };
    const [status, type, body] = cases[req.url];
    res.writeHead(status, { 'content-type': type }); res.end(body);
  });
  await new Promise(resolve => server.listen(0, '127.0.0.1', resolve));
  t.after(() => new Promise(resolve => server.close(resolve)));
  const origin = `http://127.0.0.1:${server.address().port}`;
  for (const [route, expected] of [['/missing', 'REQUEST_NOT_FOUND'], ['/revoked', 'SESSION_NOT_ALLOWED'],
    ['/waf', null], ['/route', null], ['/wrong-type', null], ['/wrong-status', null]]) {
    await assert.rejects(requestJson(new URL(route, origin)), error => error instanceof HttpError && error.serviceCode === expected);
  }
});

test('CLI with unverified adapter fails without trying missing credential paths', t => {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'cli-test-'));
  t.after(() => fs.rmSync(dir, { recursive: true, force: true }));
  const cfg = { ...base, adapterFile: path.resolve(import.meta.dirname, '../adapters/unverified.mjs'),
    localCredentialFile: '/nonexistent/local', pollerTokenFile: '/nonexistent/remote' };
  const file = path.join(dir, 'config.json'); fs.writeFileSync(file, JSON.stringify(cfg));
  const result = spawnSync(process.execPath, [path.resolve(import.meta.dirname, '../src/cli.mjs'), file], { encoding: 'utf8' });
  assert.equal(result.status, 1);
  assert.match(result.stderr, /LOCAL_ADAPTER_UNVERIFIED/);
  assert.ok(!result.stderr.includes('/nonexistent'));
});
