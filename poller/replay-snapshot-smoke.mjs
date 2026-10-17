// Full-stack replay smoke through the shipped LocalClient.snapshot: real HTTP
// transport (requestJson), real private-file read (readPrivateFile on the live
// credential file), real adapter, real contracts — with the request served by a
// loopback stub replaying a REAL captured live response body (never printed).
// Proves the entire chain on real captured bytes without a write to any session.
// Run manually: node poller/replay-snapshot-smoke.mjs
import http from 'node:http';
import fs from 'node:fs';
import { PROJECT_PATH, validateConfig } from './src/contracts.mjs';
import { LocalClient, readPrivateFile } from './src/transport.mjs';
import verified from './adapters/freebuff-verified.mjs';

const CAPTURE = '/home/user/.local/state/freebuff/observed-ed6c1915-e0aa-4d09-8504-cab7f3827e28.json';
const SESSION = 'ed6c1915-e0aa-4d09-8504-cab7f3827e28';
const body = fs.readFileSync(CAPTURE); // real captured bytes; content is never printed

const server = http.createServer((req, res) => {
  res.writeHead(200, { 'content-type': 'application/json' });
  res.end(body);
});
await new Promise(resolve => server.listen(0, '127.0.0.1', resolve));
try {
  const config = validateConfig({
    schemaVersion: 1,
    gatewayUrl: 'https://gateway.example', // never contacted by LocalClient.snapshot
    localApiUrl: `http://127.0.0.1:${server.address().port}`,
    projectPath: PROJECT_PATH,
    sessionIds: [SESSION],
    stateDir: '/home/user/.local/state/freebuff-relay',
    localCredentialFile: '/home/user/.local/state/freebuff/api-session.json',
    pollerTokenFile: '/home/user/.local/state/freebuff-relay/gateway-poller-token',
    adapterFile: '/home/user/src/offmenu-workers/worker-62/poller/adapters/freebuff-verified.mjs',
  });
  const local = new LocalClient(config, verified, readPrivateFile(config.pollerTokenFile).trim());
  const snapshot = await local.snapshot(SESSION);
  const roles = {};
  for (const message of snapshot.messages) roles[message.role] = (roles[message.role] ?? 0) + 1;
  console.log(JSON.stringify({
    sessionId: snapshot.sessionId,
    ok: true,
    paused: snapshot.paused,
    messages: snapshot.messages.length,
    roles,
    firstTimestamp: snapshot.messages[0]?.timestamp ?? null,
    lastTimestamp: snapshot.messages.at(-1)?.timestamp ?? null,
  }));
  console.log('REPLAY_SMOKE_OK');
} finally {
  await new Promise(resolve => server.close(resolve));
}
