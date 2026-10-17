import fs from 'node:fs';
import path from 'node:path';
import { pathToFileURL } from 'node:url';
import { DatabaseSync } from 'node:sqlite';
import { setTimeout as delay } from 'node:timers/promises';
import { validateConfig, verifyAdapter, requireThat, SafeError } from './contracts.mjs';
import { Journal } from './journal.mjs';
import { LocalClient, GatewayClient, readPrivateFile } from './transport.mjs';
import { Poller } from './engine.mjs';

function secureDirectory(directory) {
  fs.mkdirSync(directory, { recursive: true, mode: 0o700 });
  const stat = fs.lstatSync(directory);
  requireThat(stat.isDirectory() && !stat.isSymbolicLink() && (stat.mode & 0o077) === 0 &&
    (process.getuid === undefined || stat.uid === process.getuid()), 'STATE_DIRECTORY_PERMISSIONS');
  for (const filename of ['journal.sqlite', 'journal.sqlite-wal', 'journal.sqlite-shm', 'process-lock.sqlite', 'process-lock.sqlite-journal']) {
    const file = path.join(directory, filename);
    if (fs.existsSync(file)) {
      const info = fs.lstatSync(file);
      requireThat(info.isFile() && !info.isSymbolicLink() && (info.mode & 0o077) === 0 &&
        (process.getuid === undefined || info.uid === process.getuid()), 'STATE_FILE_PERMISSIONS');
    }
  }
}

async function main() {
  process.umask(0o077);
  requireThat(Number(process.versions.node.split('.')[0]) === 24, 'NODE_24_REQUIRED');
  requireThat(process.argv.length === 3, 'USAGE_NODE_CLI_CONFIG_JSON');
  const config = validateConfig(JSON.parse(fs.readFileSync(process.argv[2], 'utf8')));
  const adapter = (await import(pathToFileURL(config.adapterFile))).default;
  // Must fail before either credential file is read or any network request is made.
  verifyAdapter(adapter);
  secureDirectory(config.stateDir);
  const lock = new DatabaseSync(path.join(config.stateDir, 'process-lock.sqlite'), { timeout: 0 });
  try { lock.exec('PRAGMA journal_mode=DELETE; BEGIN EXCLUSIVE; CREATE TABLE IF NOT EXISTS lock_holder (id INTEGER);'); }
  catch { lock.close(); throw new SafeError('ANOTHER_POLLER_OWNS_STATE_DIRECTORY'); }
  const token = readPrivateFile(config.pollerTokenFile).trim();
  const journal = new Journal(path.join(config.stateDir, 'journal.sqlite'));
  const gateway = new GatewayClient(config, token);
  const local = new LocalClient(config, adapter, token);
  const event = code => process.stderr.write(`${JSON.stringify({ time: new Date().toISOString(), event: code })}\n`);
  const poller = new Poller({ config, journal, gateway, local, event });
  let stopping = false;
  for (const signal of ['SIGTERM', 'SIGINT']) process.on(signal, () => { stopping = true; });
  try {
    journal.recover();
    event('POLLER_STARTED');
    while (!stopping) {
      try { await poller.tick(); } catch { event('POLL_CYCLE_FAILED'); }
      if (!stopping) await delay(config.intervalMs);
    }
  } finally { journal.close(); lock.close(); }
}

main().catch(error => {
  // Never print raw exception messages, response bodies, headers, or credential paths.
  process.stderr.write(`${JSON.stringify({ event: error instanceof SafeError ? error.code : 'POLLER_STARTUP_FAILED' })}\n`);
  process.exitCode = 1;
});
