import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {fileURLToPath} from 'node:url';
import {DatabaseSync} from 'node:sqlite';
import {build} from 'esbuild';
import {Miniflare, createFetchMock} from 'miniflare';
import {workerRuntimeBuildOptions} from '../../scripts/worker-build-options.mjs';

const origin = 'https://offmenu.test';
const compiled = new Map();
async function fixture({mode, configured = false, authSchema = true} = {}) {
  const key = configured ? 'configured' : 'default';
  if (!compiled.has(key)) {
    const source = `
import defaultHandler, {createOffMenuHandler} from './apps/web/server/handler.mjs';
let verification;
const handler = ${configured ? `createOffMenuHandler({authOptions: {
 sessionPolicy: {expiresIn: 3600, updateAge: 600},
 email: {enabled: true, allowSignUp: true,
  sendVerificationEmail: async ({url}) => {verification = url;},
  sendResetPassword: async () => {}},
}})` : 'defaultHandler'};
export default {async fetch(request, env, ctx) {
 if(new URL(request.url).pathname === '/__fixture/mail') return Response.json({verification});
 return handler.fetch(request, env, ctx);
}};`;
    compiled.set(key, await build({...workerRuntimeBuildOptions,
      stdin: {contents: source, resolveDir: fileURLToPath(new URL('../../', import.meta.url)), sourcefile: 'handler-auth-fixture.mjs'},
      define: {ASSETS: '{}'}, bundle: true, write: false, minify: true, format: 'esm', platform: 'browser', metafile: true}));
  }
  const bundle = compiled.get(key);
  assert(Object.keys(bundle.metafile.inputs).some(path => path.endsWith('/async_hooks/index.mjs')));
  assert(!Object.keys(bundle.metafile.inputs).some(path => path.endsWith('/async_hooks/pure.index.mjs')));
  let legacyCalls = 0;
  const mock = createFetchMock();
  mock.disableNetConnect();
  // A successful synthetic legacy response makes any accidental fallback observable.
  mock.get('https://offmenu-accounts.netlify.app')
    .intercept({path: '/.netlify/identity/user', method: 'GET'})
    .reply(200, () => {legacyCalls++; return JSON.stringify({id: 'Legacy-opaque:ID', app_metadata: {roles: ['offmenu-admin']}});}).persist();
  const worker = new Miniflare({modules: true, script: bundle.outputFiles[0].text,
    compatibilityDate: '2026-08-06', compatibilityFlags: ['nodejs_compat'],
    host: '127.0.0.1', port: 0, d1Databases: ['DB'], fetchMock: mock,
    bindings: {...(mode === undefined ? {} : {OFFMENU_AUTH_MODE: mode}),
      BETTER_AUTH_URL: origin, BETTER_AUTH_SECRET: 'synthetic-dispatcher-test-only-never-deploy-00000000'}});
  try {
    const db = await worker.getD1Database('DB');
    const schema = new DatabaseSync(':memory:');
    try {
      schema.exec(readFileSync(new URL('../../apps/web/server/schema.sql', import.meta.url), 'utf8'));
      for (const {sql} of schema.prepare("SELECT sql FROM sqlite_master WHERE sql IS NOT NULL AND name NOT LIKE 'sqlite_%' ORDER BY CASE type WHEN 'table' THEN 0 ELSE 1 END").all())
        await db.prepare(sql).run();
    } finally {schema.close();}
    if (authSchema) await db.exec(readFileSync(new URL('../../apps/web/server/auth-schema.sql', import.meta.url), 'utf8'));
    const request = (path, {method = 'GET', body, cookie, bearer, requestOrigin = origin, headers = {}} = {}) =>
      worker.dispatchFetch(origin + path, {method, redirect: 'manual',
        headers: {Origin: requestOrigin, 'Content-Type': 'application/json', 'cf-connecting-ip': '192.0.2.19',
          ...(cookie ? {Cookie: cookie} : {}), ...(bearer ? {Authorization: 'Bearer ' + bearer} : {}), ...headers},
        ...(body === undefined ? {} : {body: JSON.stringify(body)})});
    return {worker, db, request, legacyCalls: () => legacyCalls};
  } catch (error) {await worker.dispose(); throw error;}
}

async function signIn(request) {
  const body = {email: 'dispatcher@example.test', password: 'SyntheticOnly_Dispatcher!234', name: 'Dispatcher'};
  const rejected = await request('/api/auth/sign-up/email', {method: 'POST', body, requestOrigin: 'https://other.test'});
  assert.equal(rejected.status, 403);
  const created = await request('/api/auth/sign-up/email', {method: 'POST', body});
  assert.equal(created.status, 200);
  const link = new URL((await (await request('/__fixture/mail')).json()).verification);
  const verification = await request(link.pathname + link.search);
  assert.equal(verification.status, 302);
  assert(verification.headers.get('location'));
  assert.equal(verification.headers.get('cache-control'), 'no-store');
  assert.equal(verification.headers.get('x-content-type-options'), 'nosniff');
  const signed = await request('/api/auth/sign-in/email', {method: 'POST', body});
  assert.equal(signed.status, 200);
  assert.equal(signed.headers.get('cache-control'), 'no-store');
  assert.equal(signed.headers.get('x-content-type-options'), 'nosniff');
  const cookies = signed.headers.getSetCookie();
  const session = cookies.find(value => value.startsWith('__Secure-offmenu-auth.session_token='));
  assert(session);
  for (const flag of [/HttpOnly/, /Secure/, /SameSite=Lax/]) assert.match(session, flag);
  return {cookie: session.split(';')[0], user: (await signed.json()).user};
}

test('default export retains missing/explicit Netlify mode, proxy restrictions and opaque ownership', async () => {
  for (const mode of [undefined, 'netlify']) {
    const {worker, db, request, legacyCalls} = await fixture({mode});
    try {
      await db.prepare('INSERT INTO user_state(user_id,revision,state_json,updated_at) VALUES(?,7,?,?)')
        .bind('Legacy-opaque:ID', JSON.stringify({sentinel: 'legacy-private'}), '2026-10-25T00:00:00Z').run();
      assert.equal((await request('/api/health?OFFMENU_AUTH_MODE=better-auth', {headers: {'X-OffMenu-Auth-Mode': 'better-auth'}})).status, 200);
      assert.equal((await request('/api/auth/get-session')).status, 404);
      assert.equal((await request('/api/state')).status, 401);
      const state = await request('/api/state', {bearer: 'synthetic-legacy-bearer'});
      assert.equal(state.status, 200);
      assert.equal((await state.json()).state.sentinel, 'legacy-private');
      assert.equal((await request('/api/admin/session', {cookie: 'nf_jwt=synthetic-legacy-cookie'})).status, 200);
      assert.equal((await request('/.netlify/identity/user')).status, 200);
      assert.equal((await request('/.netlify/identity/not-allowed')).status, 404);
      assert.equal((await request('/.netlify/identity/user', {method: 'DELETE'})).status, 405);
      assert.equal((await request('/.netlify/identity/user', {method: 'POST', body: {}, requestOrigin: 'https://other.test'})).status, 403);
      assert.equal(legacyCalls(), 3);
    } finally {await worker.dispose();}
  }
});

test('mounted auth precedes legacy proxy and catch-all with exact route boundaries', async () => {
  const {worker, request, legacyCalls} = await fixture({mode: 'better-auth', configured: true});
  try {
    for (const path of ['/.netlify/identity', '/.netlify/identity/user', '/.netlify/identity/token']) {
      const response = await request(path);
      assert.equal(response.status, 410);
      assert.equal(response.headers.get('cache-control'), 'no-store');
    }
    for (const path of ['/api/authish', '/.netlify/identityish']) assert.equal((await request(path)).status, 404);
    const response = await request('/api/auth/get-session');
    assert.equal(response.status, 200);
    assert.equal(await response.json(), null);
    assert.equal(response.headers.get('cache-control'), 'no-store');
    assert.equal(legacyCalls(), 0);
  } finally {await worker.dispose();}
});

test('mounted sessions select exact private owner, fresh admin roles and revocation without legacy fallback', async () => {
  const {worker, db, request, legacyCalls} = await fixture({mode: 'better-auth', configured: true});
  try {
    const {cookie, user} = await signIn(request);
    for (const [id, sentinel] of [[user.id, 'better-private'], ['Legacy-opaque:ID', 'legacy-private']])
      await db.prepare('INSERT INTO user_state(user_id,revision,state_json,updated_at) VALUES(?,9,?,?)')
        .bind(id, JSON.stringify({sentinel}), '2026-10-25T00:00:00Z').run();
    const own = await request('/api/state', {cookie, bearer: 'synthetic-legacy-bearer'});
    assert.equal(own.status, 200);
    assert.equal((await own.json()).state.sentinel, 'better-private');
    assert.deepEqual(await (await request('/api/admin/session', {cookie})).json(), {isAdmin: false});
    await db.prepare('UPDATE auth_user SET appRoles=? WHERE id=?').bind('["offmenu-admin"]', user.id).run();
    assert.deepEqual(await (await request('/api/admin/session', {cookie})).json(), {isAdmin: true});
    await db.prepare('UPDATE auth_user SET appRoles=? WHERE id=?').bind('[]', user.id).run();
    assert.deepEqual(await (await request('/api/admin/session', {cookie})).json(), {isAdmin: false});
    for (const headers of [{bearer: 'synthetic-legacy-bearer'}, {cookie: cookie + 'tamper', bearer: 'synthetic-legacy-bearer'}])
      assert.equal((await request('/api/state', headers)).status, 401);
    const logout = await request('/api/auth/sign-out', {method: 'POST', body: {}, cookie});
    assert.equal(logout.status, 200);
    assert(logout.headers.getSetCookie().some(value => value.startsWith('__Secure-offmenu-auth.session_token=') && /Max-Age=0/i.test(value)));
    assert.equal(logout.headers.get('cache-control'), 'no-store');
    assert.equal((await request('/api/state', {cookie, bearer: 'synthetic-legacy-bearer'})).status, 401);
    assert.equal(legacyCalls(), 0);
  } finally {await worker.dispose();}
});

test('dispatcher fails closed for unknown mode, missing explicit policy and native auth outages', async () => {
  for (const options of [{mode: 'auto'}, {mode: 'better-auth'}]) {
    const {worker, request, legacyCalls} = await fixture(options);
    try {
      const response = await request('/api/state', {bearer: 'synthetic-legacy-bearer'});
      assert.equal(response.status, 503);
      assert.equal(response.headers.get('cache-control'), 'no-store');
      assert.deepEqual(await response.json(), {error: 'Service temporarily unavailable. Your local pantry is retained.'});
      assert.equal(legacyCalls(), 0);
    } finally {await worker.dispose();}
  }
  const {worker, request, legacyCalls} = await fixture({mode: 'better-auth', configured: true, authSchema: false});
  try {
    const response = await request('/api/auth/get-session');
    assert.equal(response.status, 503);
    assert.equal(response.headers.get('cache-control'), 'no-store');
    assert.deepEqual(await response.json(), {error: 'Authentication is temporarily unavailable.'});
    assert.equal(legacyCalls(), 0);
  } finally {await worker.dispose();}
});

test('authenticated principal lookup outage returns generic 503 and never retries Netlify', async () => {
  const {worker, db, request, legacyCalls} = await fixture({mode: 'better-auth', configured: true});
  try {
    const {cookie} = await signIn(request);
    await db.prepare('DROP TABLE auth_session').run();
    const response = await request('/api/state', {cookie, bearer: 'synthetic-legacy-bearer'});
    assert.equal(response.status, 503);
    assert.equal(response.headers.get('cache-control'), 'no-store');
    assert.deepEqual(await response.json(), {error: 'Service temporarily unavailable. Your local pantry is retained.'});
    assert.equal(legacyCalls(), 0);
  } finally {await worker.dispose();}
});
