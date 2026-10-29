import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {fileURLToPath} from 'node:url';
import {build} from 'esbuild';
import {Miniflare, createFetchMock} from 'miniflare';
import {getMigrations} from 'better-auth/db/migration';
import {createOffMenuAuth} from '../../cloud/auth.mjs';

const root = fileURLToPath(new URL('../../', import.meta.url));
const schema = readFileSync(new URL('../../cloud/auth-schema.sql', import.meta.url), 'utf8');
const origin = 'https://offmenu.test';
const secret = 'synthetic-only-native-D1-test-secret-never-deploy-000000';
const sessionPolicy = {expiresIn: 3600, updateAge: 600};
const source = `
import {createOffMenuAuth} from './cloud/auth.mjs';
import {getOffMenuPrincipal} from './cloud/auth-principal.mjs';
let verificationMail = [], resetMail = [];
export default {async fetch(request, env) {
  const auth = createOffMenuAuth(env, {sessionPolicy: {expiresIn: 3600, updateAge: 600},
    ...(env.TEST_EMAIL === 'enabled' ? {email: {enabled: true, allowSignUp: true,
      sendVerificationEmail: async ({url}) => {verificationMail.push(url);},
      sendResetPassword: async ({url}) => {resetMail.push(url);}}} : {})});
  const path = new URL(request.url).pathname;
  // These synthetic fixture routes exist only inside this test bundle.
  if (path === '/__fixture/mail') return Response.json({verificationMail, resetMail});
  if (path === '/__fixture/principal') return Response.json(await getOffMenuPrincipal(auth, request));
  if (path === '/__fixture/state') {
    const principal = await getOffMenuPrincipal(auth, request);
    if (!principal) return new Response('Sign in required', {status: 401});
    return Response.json(await env.DB.prepare('SELECT revision,state_json FROM user_state WHERE user_id=?').bind(principal.id).first());
  }
  return auth.handler(request);
}};`;

async function fixture({email = true, migrate = true} = {}) {
  const compiled = await build({stdin: {contents: source, resolveDir: root, sourcefile: 'auth-fixture.mjs'},
    bundle: true, write: false, minify: true, format: 'esm', platform: 'browser',
    conditions: ['workerd'], external: ['node:*'], metafile: true});
  assert(Object.keys(compiled.metafile.inputs).some(path => path.endsWith('/async_hooks/index.mjs')));
  assert(!Object.keys(compiled.metafile.inputs).some(path => path.endsWith('/async_hooks/pure.index.mjs')));
  assert(!compiled.outputFiles[0].text.includes(secret));
  const mock = createFetchMock();
  mock.disableNetConnect();
  const worker = new Miniflare({modules: true, script: compiled.outputFiles[0].text,
    compatibilityDate: '2026-08-06', compatibilityFlags: ['nodejs_compat'],
    host: '127.0.0.1', port: 0, d1Databases: ['DB'], fetchMock: mock,
    bindings: {BETTER_AUTH_URL: origin, BETTER_AUTH_SECRET: secret, TEST_EMAIL: email ? 'enabled' : 'disabled'}});
  try {
    const db = await worker.getD1Database('DB');
    if (migrate) await db.exec(schema);
    const request = (path, {method = 'GET', body, cookie, requestOrigin = origin, ip = '192.0.2.10', authorization} = {}) =>
      worker.dispatchFetch(origin + path, {method, redirect: 'manual',
        headers: {Origin: requestOrigin, 'Content-Type': 'application/json', 'cf-connecting-ip': ip,
          ...(cookie ? {Cookie: cookie} : {}), ...(authorization ? {Authorization: authorization} : {})},
        ...(body === undefined ? {} : {body: JSON.stringify(body)})});
    return {worker, db, request};
  } catch (error) {await worker.dispose(); throw error;}
}

async function signIn(request, email, password, ip = '192.0.2.10') {
  const response = await request('/api/auth/sign-in/email', {method: 'POST', body: {email, password}, ip});
  const body = await response.json();
  assert.equal(response.status, 200, JSON.stringify(body));
  const setCookie = response.headers.get('set-cookie');
  assert.match(setCookie, /__Secure-offmenu-auth\.session_token=/);
  for (const attribute of [/HttpOnly/i, /Secure/i, /SameSite=Lax/i, /Path=\//i]) assert.match(setCookie, attribute);
  assert.doesNotMatch(setCookie, /Domain=/i);
  return {user: body.user, cookie: setCookie.split(';')[0]};
}

async function confirmedAccount(request, email = 'alice@example.test', ip = '192.0.2.10') {
  const password = 'SyntheticOnly_Password!234';
  const response = await request('/api/auth/sign-up/email', {method: 'POST', ip,
    body: {name: 'Alice', email, password, appRoles: '["admin"]'}});
  const body = await response.json();
  assert.equal(response.status, 200, JSON.stringify(body));
  assert.equal(response.headers.get('set-cookie'), null);
  const mail = await (await request('/__fixture/mail')).json();
  const link = new URL(mail.verificationMail.at(-1));
  assert.equal(link.origin, origin);
  const verified = await request(link.pathname + link.search);
  assert.equal(verified.status, 302);
  return {password, ...(await signIn(request, email, password, ip))};
}

test('foundation schema is explicit, additive, repeatable and matches the pinned factory', async () => {
  const {worker, db, request} = await fixture({email: false, migrate: false});
  try {
    await db.exec('CREATE TABLE user_state(user_id TEXT PRIMARY KEY, revision INTEGER, state_json TEXT);');
    await db.prepare('INSERT INTO user_state VALUES(?,?,?)').bind('legacy', 7, '{"private":"unchanged"}').run();
    assert.equal((await request('/api/auth/get-session')).status, 500);
    assert.deepEqual((await db.prepare("SELECT name FROM sqlite_master WHERE name LIKE 'auth_%'").all()).results, []);
    await db.exec(schema);
    await db.exec(schema);
    const tables = (await db.prepare("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'auth_%' ORDER BY name").all()).results.map(row => row.name);
    assert.deepEqual(tables, ['auth_account', 'auth_rate_limit', 'auth_session', 'auth_user', 'auth_verification']);
    const auth = createOffMenuAuth({DB: db, BETTER_AUTH_URL: origin, BETTER_AUTH_SECRET: secret}, {sessionPolicy});
    const migration = await getMigrations(auth.options);
    assert.deepEqual(migration.toBeCreated, []);
    assert.deepEqual(migration.toBeAdded, []);
    assert.deepEqual(await db.prepare('SELECT * FROM user_state').first(), {user_id: 'legacy', revision: 7, state_json: '{"private":"unchanged"}'});
    assert.equal(await (await request('/api/auth/get-session')).json(), null);
    const disabled = await request('/api/auth/sign-up/email', {method: 'POST', body: {name: 'Disabled', email: 'disabled@example.test', password: 'SyntheticOnly_234'}});
    assert.equal(disabled.status, 400);
    const google = await request('/api/auth/sign-in/social', {method: 'POST', body: {provider: 'google', callbackURL: '/'}});
    assert.equal(google.status, 404);
    assert.equal((await db.prepare('SELECT COUNT(*) AS n FROM auth_user').first()).n, 0);
  } finally {await worker.dispose();}
});

test('email verification, secure sessions, origin checks and fresh trusted roles run in native D1', async () => {
  const {worker, db, request} = await fixture();
  try {
    const body = {name: 'Alice', email: 'alice@example.test', password: 'SyntheticOnly_Password!234', appRoles: '["admin"]'};
    assert.equal((await request('/api/auth/sign-up/email', {method: 'POST', body, requestOrigin: 'https://untrusted.test'})).status, 403);
    assert.equal((await request('/api/auth/sign-up/email', {method: 'POST', body})).status, 200);
    assert.equal((await request('/api/auth/sign-in/email', {method: 'POST', body})).status, 403);
    const mail = await (await request('/__fixture/mail')).json();
    const link = new URL(mail.verificationMail[0]);
    assert.equal((await request(link.pathname + link.search)).status, 302);
    const {user, cookie} = await signIn(request, body.email, body.password);
    const principal = await (await request('/__fixture/principal', {cookie})).json();
    assert.equal(principal.id, user.id);
    assert.equal(principal.emailVerified, true);
    assert.deepEqual(principal.app_metadata.roles, []);
    assert(!('token' in principal));
    assert.equal(await (await request('/__fixture/principal', {cookie: cookie + 'corrupt'})).json(), null);
    assert.equal(await (await request('/__fixture/principal', {authorization: 'Bearer legacy-netlify-token'})).json(), null);
    assert.equal(await (await request('/__fixture/principal')).json(), null);
    await db.prepare('UPDATE auth_user SET appRoles=? WHERE id=?').bind('["offmenu-admin"]', user.id).run();
    assert.deepEqual((await (await request('/__fixture/principal', {cookie})).json()).app_metadata.roles, ['offmenu-admin']);
    await db.prepare('UPDATE auth_user SET appRoles=? WHERE id=?').bind('[]', user.id).run();
    await request('/api/auth/update-user', {method: 'POST', cookie, body: {appRoles: '["admin"]'}});
    assert.deepEqual((await (await request('/__fixture/principal', {cookie})).json()).app_metadata.roles, []);
    const session = await request('/api/auth/get-session', {cookie});
    assert.equal(session.headers.get('cache-control'), 'no-store');
    assert.equal((await request('/api/auth/sign-out', {method: 'POST', body: {}, cookie, requestOrigin: 'https://untrusted.test'})).status, 403);
    assert.equal((await request('/api/auth/sign-out', {method: 'POST', body: {}, cookie})).status, 200);
    assert.equal(await (await request('/__fixture/principal', {cookie})).json(), null);
  } finally {await worker.dispose();}
});

test('imported subject stays stable and retains private state and encrypted-data binding', async () => {
  const {worker, db, request} = await fixture();
  try {
    const account = await confirmedAccount(request);
    const originalId = 'Original-Netlify-Subject_01';
    await db.prepare('INSERT INTO auth_user(id,name,email,emailVerified,createdAt,updatedAt,appRoles) SELECT ?,name,?,emailVerified,createdAt,updatedAt,? FROM auth_user WHERE id=?')
      .bind(originalId, 'legacy@example.test', '[]', account.user.id).run();
    await db.prepare('INSERT INTO auth_account(id,accountId,providerId,userId,password,createdAt,updatedAt) SELECT ?,?,providerId,?,password,createdAt,updatedAt FROM auth_account WHERE userId=?')
      .bind('legacy-credential-fixture', originalId, originalId, account.user.id).run();
    await db.exec('CREATE TABLE user_state(user_id TEXT PRIMARY KEY, revision INTEGER, state_json TEXT);');
    await db.prepare('INSERT INTO user_state VALUES(?,?,?)').bind(originalId, 19, '{"private":"original pantry"}').run();
    await db.prepare('INSERT INTO user_state VALUES(?,?,?)').bind(account.user.id, 3, '{"private":"other pantry"}').run();
    const legacy = await signIn(request, 'legacy@example.test', account.password, '192.0.2.11');
    const principal = await (await request('/__fixture/principal', {cookie: legacy.cookie})).json();
    assert.equal(principal.id, originalId);
    assert.deepEqual(await (await request('/__fixture/state?userId=' + account.user.id, {cookie: legacy.cookie})).json(),
      {revision: 19, state_json: '{"private":"original pantry"}'});
    assert.deepEqual(await (await request('/__fixture/state?userId=' + originalId, {cookie: account.cookie})).json(),
      {revision: 3, state_json: '{"private":"other pantry"}'});
    // Synthetic ciphertext uses the production vault's documented owner|source AAD contract.
    const key = await crypto.subtle.generateKey({name: 'AES-GCM', length: 256}, false, ['encrypt', 'decrypt']);
    const iv = crypto.getRandomValues(new Uint8Array(12));
    const encode = value => new TextEncoder().encode(value);
    const sealed = await crypto.subtle.encrypt({name: 'AES-GCM', iv, additionalData: encode(originalId + '|usda')}, key, encode('synthetic-provider-secret'));
    const opened = await crypto.subtle.decrypt({name: 'AES-GCM', iv, additionalData: encode(principal.id + '|usda')}, key, sealed);
    assert.equal(new TextDecoder().decode(opened), 'synthetic-provider-secret');
    await assert.rejects(crypto.subtle.decrypt({name: 'AES-GCM', iv, additionalData: encode(account.user.id + '|usda')}, key, sealed));
    await db.prepare('UPDATE auth_session SET expiresAt=? WHERE userId=?').bind(0, originalId).run();
    assert.equal(await (await request('/__fixture/principal', {cookie: legacy.cookie})).json(), null);
    assert.equal((await db.prepare('SELECT revision FROM user_state WHERE user_id=?').bind(originalId).first()).revision, 19);
  } finally {await worker.dispose();}
});

test('password reset consumes its token and revokes sessions without exposing unknown accounts', async () => {
  const {worker, db, request} = await fixture();
  try {
    const account = await confirmedAccount(request);
    const reset = email => request('/api/auth/request-password-reset', {method: 'POST', body: {email, redirectTo: origin + '/account'}});
    const known = await reset('alice@example.test');
    const unknown = await reset('unknown@example.test');
    assert.equal(known.status, 200);
    assert.equal(unknown.status, 200);
    assert.deepEqual(await known.json(), await unknown.json());
    const mail = await (await request('/__fixture/mail')).json();
    assert.equal(mail.resetMail.length, 1);
    const token = new URL(mail.resetMail[0]).pathname.split('/').at(-1);
    const body = {token, newPassword: 'SyntheticOnly_NewPassword!234'};
    assert.equal((await request('/api/auth/reset-password', {method: 'POST', body})).status, 200);
    assert.equal(await (await request('/__fixture/principal', {cookie: account.cookie})).json(), null);
    assert.notEqual((await request('/api/auth/reset-password', {method: 'POST', body})).status, 200);
    assert.equal((await db.prepare('SELECT COUNT(*) AS n FROM auth_session WHERE userId=?').bind(account.user.id).first()).n, 0);
  } finally {await worker.dispose();}
});
