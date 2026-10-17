// Read-only live smoke through the shipped LocalClient.snapshot against the real
// loopback API on this host, using the private poller config so the target
// binding is identical to production use. Run manually:
//   node poller/live-snapshot-smoke.mjs
// Prints only identity, pause state, counts and timestamps — never message text,
// titles, or credential values. No writes: snapshot() is GET-only. Dispatch
// remains disabled; this does not install or start any service.
import fs from 'node:fs';
import { validateConfig } from './src/contracts.mjs';
import { LocalClient, readPrivateFile } from './src/transport.mjs';
import verified from './adapters/freebuff-verified.mjs';

const CONFIG_FILE = '/home/user/.local/state/freebuff-relay/poller-config.json';
const config = validateConfig(JSON.parse(fs.readFileSync(CONFIG_FILE, 'utf8')));
const local = new LocalClient(config, verified, readPrivateFile(config.pollerTokenFile).trim());

let ok = 0;
for (const sessionId of config.sessionIds) {
  try {
    const snapshot = await local.snapshot(sessionId);
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
    ok += 1;
  } catch (error) {
    // Report the poller's own safe error code; no bodies, headers, or credentials.
    console.log(JSON.stringify({ sessionId, ok: false, error: error.code ?? error.name }));
  }
}
if (ok === config.sessionIds.length) {
  console.log('LIVE_SMOKE_OK');
} else {
  console.log(`LIVE_SMOKE_INCOMPLETE ${ok}/${config.sessionIds.length} snapshots succeeded`);
  process.exitCode = 1;
}
