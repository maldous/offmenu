import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { DatabaseSync } from 'node:sqlite';
import { Miniflare, createFetchMock } from 'miniflare';

if (process.env.OFFMENU_COMPAT_FIXTURE !== '1') throw Error('Run through scripts/run-third-party-compatibility.mjs.');
const inputs = JSON.parse(readFileSync(new URL('./inputs.json', import.meta.url), 'utf8'));
const mainSQL = readFileSync(new URL('./main-schema.sql', import.meta.url), 'utf8');
const sql = name => readFileSync(new URL('../cloud/' + name, import.meta.url), 'utf8');
const stamp = '2026-10-14T00:00:00.000Z';
const sentinel = { user_id: 'sentinel-owner', revision: 7, state_json: '{"private":"PINNED_PRIVATE_CANARY"}', updated_at: stamp };
const schemaRows = db => db.prepare("SELECT type,name,sql FROM sqlite_master WHERE type IN ('table','index') AND name NOT LIKE 'sqlite_%' ORDER BY type,name").all()
  .map(row => ({ ...row, sql: row.sql?.replace(/--[^\n]*/g, '').replace(/\s+/g, ' ').replace(/\(\s+/g, '(').replace(/\s+\)/g, ')').replace(/\s*,\s*/g, ',').trim() }));
function migrated() {
  const db = new DatabaseSync(':memory:');
  db.exec(mainSQL);
  db.prepare('INSERT INTO user_state(user_id,revision,state_json,updated_at) VALUES(?,?,?,?)').run(...Object.values(sentinel));
  db.prepare('INSERT INTO provider_connections VALUES(?,?,?,?,?)').run('sentinel-owner', 'usda', 'PRIVATE_CONNECTION_CANARY', 'SEALED_PRIVATE_CANARY', stamp);
  for (let replay = 0; replay < 2; replay++) for (const name of inputs.migrations) db.exec(sql(name));
  return db;
}

test('actual pinned main schema plus twice-replayed additive migrations equals canonical schema and preserves full private rows', () => {
  const db = migrated(), fresh = new DatabaseSync(':memory:');
  try {
    fresh.exec(sql('schema.sql'));
    assert.deepEqual(schemaRows(db), schemaRows(fresh));
    assert.deepEqual({ ...db.prepare('SELECT * FROM user_state').get() }, sentinel);
    assert.equal(db.prepare('SELECT sealed FROM provider_connections').get().sealed, 'SEALED_PRIVATE_CANARY');
  } finally { db.close(); fresh.close(); }
});

test('composed compiled Worker on migrated main preserves private sentinels, rejects forged roles and separates care ownership', async () => {
  let trustedRole = true;
  const mock = createFetchMock(); mock.disableNetConnect();
  mock.get('https://offmenu-accounts.netlify.app').intercept({ path: '/.netlify/identity/user', method: 'GET' })
    .reply(200, ({ headers }) => {
      const id = (headers.authorization || headers.Authorization).replace('Bearer ', '');
      return JSON.stringify({ id, app_metadata: { roles: id === 'admin' && trustedRole ? ['offmenu-admin'] : [] }, user_metadata: { roles: ['admin'] } });
    }).persist();
  const worker = new Miniflare({ modules: true, scriptPath: 'dist/worker.mjs', compatibilityDate: '2026-08-06',
    compatibilityFlags: ['nodejs_compat'], d1Databases: ['DB'], fetchMock: mock, bindings: { PROVIDER_VAULT_KEY: 'a'.repeat(64) } });
  try {
    const db = await worker.getD1Database('DB'), source = new DatabaseSync(':memory:');
    try {
      source.exec(mainSQL);
      for (const { sql: statement } of source.prepare("SELECT sql FROM sqlite_master WHERE sql IS NOT NULL AND name NOT LIKE 'sqlite_%' ORDER BY CASE type WHEN 'table' THEN 0 ELSE 1 END").all()) await db.prepare(statement).run();
      await db.prepare('INSERT INTO user_state(user_id,revision,state_json,updated_at) VALUES(?,?,?,?)').bind(...Object.values(sentinel)).run();
      await db.prepare('INSERT INTO provider_connections VALUES(?,?,?,?,?)').bind('sentinel-owner', 'usda', 'PRIVATE_CONNECTION_CANARY', 'SEALED_PRIVATE_CANARY', stamp).run();
      // Replay in D1 as well, rather than assuming SQLite-only acceptance.
      for (let pass = 0; pass < 2; pass++) for (const name of inputs.migrations) {
        const replay = new DatabaseSync(':memory:');
        try {
          replay.exec(sql(name));
          for (const { sql: statement } of replay.prepare("SELECT sql FROM sqlite_master WHERE sql IS NOT NULL AND name NOT LIKE 'sqlite_%' ORDER BY CASE type WHEN 'table' THEN 0 ELSE 1 END").all()) {
            await db.prepare(statement.replace(/^CREATE TABLE /, 'CREATE TABLE IF NOT EXISTS ').replace(/^CREATE INDEX /, 'CREATE INDEX IF NOT EXISTS ')).run();
          }
        } finally { replay.close(); }
      }
    } finally { source.close(); }
    const call = (path, token, method = 'GET', body, origin = 'https://offmenu.test') => worker.dispatchFetch('https://offmenu.test' + path, {
      method, headers: { ...(token ? { Authorization: 'Bearer ' + token } : {}), Origin: origin, 'Content-Type': 'application/json' },
      ...(body ? { body: JSON.stringify(body) } : {}),
    });
    const health = await (await call('/api/health')).json();
    assert.equal(health.release.sourceCommit, inputs.thirdParty); assert.equal(health.release.compatibilityMain, inputs.main);
    assert.equal((await call('/api/care/cases')).status, 401);
    assert.equal((await call('/api/admin/settings', 'forged')).status, 403);
    assert.equal((await call('/api/admin/care/cases', 'forged')).status, 403);
    for (const path of ['/api/state?userId=sentinel-owner', '/api/data/connections?userId=sentinel-owner', '/api/services/support?owner=sentinel-owner']) {
      for (const token of ['bob', 'admin']) {
        const response = await call(path, token); assert.equal(response.status, 200, path);
        assert.doesNotMatch(await response.text(), /PINNED_PRIVATE_CANARY|PRIVATE_CONNECTION_CANARY|SEALED_PRIVATE_CANARY/);
      }
    }
    const creation = { confirmed: true, idempotencyKey: 'pinned_compat_case_creation_01', category: 'recipe', title: 'Synthetic correction', message: 'Synthetic submitted care text.' };
    assert.equal((await call('/api/care/cases', 'alice', 'POST', creation, 'https://other.test')).status, 403);
    const created = await call('/api/care/cases', 'alice', 'POST', creation); assert.equal(created.status, 201);
    const id = (await created.json()).case.id;
    assert.equal((await call('/api/care/cases/' + id, 'bob')).status, 404);
    assert.equal((await call('/api/care/cases/' + id, 'alice')).status, 200);
    assert.equal((await call('/api/admin/care/cases/' + id, 'admin')).status, 200);
    trustedRole = false; assert.equal((await call('/api/admin/care/cases/' + id, 'admin')).status, 403);
    const services = await call('/api/services'); assert.equal(services.status, 200);
    assert.doesNotMatch(await services.text(), /PINNED_PRIVATE_CANARY|PRIVATE_CONNECTION_CANARY|SEALED_PRIVATE_CANARY/);
    const landing = await call('/?uiLanguage=ar'); assert.equal(landing.headers.get('Content-Language'), 'ar');
    assert.equal(landing.headers.get('Cache-Control'), 'private, no-store');
    assert.deepEqual(await db.prepare('SELECT * FROM user_state WHERE user_id=?').bind(sentinel.user_id).first(), sentinel);
    assert.equal((await db.prepare('SELECT sealed FROM provider_connections WHERE user_id=?').bind(sentinel.user_id).first()).sealed, 'SEALED_PRIVATE_CANARY');
  } finally { await worker.dispose(); await mock.close(); }
});
