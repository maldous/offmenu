import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {fileURLToPath} from 'node:url';
import {build} from 'esbuild';
import {Miniflare, createFetchMock} from 'miniflare';
import {workerRuntimeBuildOptions} from '../../scripts/worker-build-options.mjs';
const origin = 'https://offmenu.test';
const source = `
import {createOffMenuAuthRuntime} from './apps/web/server/auth-runtime.mjs';
let verification;
export default {async fetch(request, env) {
 const runtime = createOffMenuAuthRuntime(env, {
  legacyVerifiedUser: async () => { throw Error('Legacy fallback must never run'); },
  authOptions: {sessionPolicy: {expiresIn: 3600, updateAge: 600}, email: {
   enabled: true, allowSignUp: true,
   sendVerificationEmail: async ({url}) => {verification = url;}, sendResetPassword: async () => {},
  }},
 });
 const response = await runtime.handleAuthRequest(request);
 if(response) return response;
 const path = new URL(request.url).pathname;
 if(path === '/__fixture/mail') return Response.json({verification});
 if(path === '/__fixture/principal') return Response.json(await runtime.verifiedUser(request));
 return new Response('Unrelated route', {status: 404});
}};`;
async function fixture({schema = true} = {}) {
 const compiled = await build({...workerRuntimeBuildOptions, stdin: {contents: source,
  resolveDir: fileURLToPath(new URL('../../', import.meta.url)), sourcefile: 'runtime-fixture.mjs'},
  bundle: true, write: false, minify: true, format: 'esm', platform: 'browser', metafile: true});
 assert(Object.keys(compiled.metafile.inputs).some(x => x.endsWith('/async_hooks/index.mjs')));
 assert(!Object.keys(compiled.metafile.inputs).some(x => x.endsWith('/async_hooks/pure.index.mjs')));
 const mock = createFetchMock(); mock.disableNetConnect();
 const worker = new Miniflare({modules: true, script: compiled.outputFiles[0].text,
  compatibilityDate: '2026-08-06', compatibilityFlags: ['nodejs_compat'], host: '127.0.0.1', port: 0,
  d1Databases: ['DB'], fetchMock: mock, bindings: {OFFMENU_AUTH_MODE: 'better-auth',
   BETTER_AUTH_URL: origin, BETTER_AUTH_SECRET: 'synthetic-runtime-seam-only-never-deploy-0000000000'}});
 try {
 const db = await worker.getD1Database('DB');
 if(schema) await db.exec(readFileSync(new URL('../../apps/web/server/auth-schema.sql', import.meta.url), 'utf8'));
 const request = (path, {method = 'GET', body, cookie, requestOrigin = origin} = {}) => worker.dispatchFetch(origin + path,
  {method, redirect: 'manual', headers: {Origin: requestOrigin, 'Content-Type': 'application/json',
   'cf-connecting-ip': '192.0.2.25', ...(cookie ? {Cookie: cookie} : {})},
   ...(body === undefined ? {} : {body: JSON.stringify(body)})});
 return {worker, db, request};
 } catch(error) {await worker.dispose(); throw error;}
}

test('enabled offline seam preserves redirects, cookie headers, origin rules and fresh principal', async () => {
 const {worker, db, request} = await fixture();
 try {
  assert.equal((await request('/.netlify/identity/user')).status, 410);
  assert.equal((await request('/.netlify/identity')).status, 410);
  assert.equal((await request('/.netlify/identityish')).status, 404);
  assert.equal((await request('/api/authish')).status, 404);
  assert.equal(await (await request('/__fixture/principal')).json(), null);
  const body = {email: 'runtime@example.test', password: 'SyntheticOnly_Pass!123', name: 'Runtime'};
  assert.equal((await request('/api/auth/sign-up/email', {method: 'POST', body, requestOrigin: 'https://other.test'})).status, 403);
  assert.equal((await request('/api/auth/sign-up/email', {method: 'POST', body})).status, 200);
  const mail = await (await request('/__fixture/mail')).json(); const link = new URL(mail.verification);
  const verification = await request(link.pathname + link.search);
  assert.equal(verification.status, 302);
  assert(verification.headers.get('location'));
  const signed = await request('/api/auth/sign-in/email', {method: 'POST', body});
  assert.equal(signed.status, 200);
  assert.equal(signed.headers.get('cache-control'), 'no-store');
  assert.equal(signed.headers.get('x-content-type-options'), 'nosniff');
  const cookies = signed.headers.getSetCookie();
  assert(cookies.length > 0);
  const sessionCookie = cookies.find(c => c.startsWith('__Secure-offmenu-auth.session_token='));
  assert(sessionCookie); assert.match(sessionCookie, /HttpOnly/); assert.match(sessionCookie, /SameSite=Lax/);
  const cookie = sessionCookie.split(';')[0], user = (await signed.json()).user;
  assert.equal((await (await request('/__fixture/principal', {cookie})).json()).id, user.id);
  await db.prepare('UPDATE auth_user SET appRoles=? WHERE id=?').bind('["offmenu-admin"]', user.id).run();
  assert.deepEqual((await (await request('/__fixture/principal', {cookie})).json()).app_metadata.roles, ['offmenu-admin']);
  await db.prepare('UPDATE auth_user SET appRoles=? WHERE id=?').bind('[]', user.id).run();
  assert.deepEqual((await (await request('/__fixture/principal', {cookie})).json()).app_metadata.roles, []);
  assert.equal(await (await request('/__fixture/principal', {cookie: cookie + 'tamper'})).json(), null);
  const logout = await request('/api/auth/sign-out', {method: 'POST', body: {}, cookie});
  assert.equal(logout.status, 200);
  assert(logout.headers.getSetCookie().some(c => c.startsWith('__Secure-offmenu-auth.session_token=') && /Max-Age=0/i.test(c)));
  assert.equal(await (await request('/__fixture/principal', {cookie})).json(), null);
 } finally {await worker.dispose();}
});

test('missing schema is an outage, never a legacy fallback or successful anonymous auth route', async () => {
 const {worker, request} = await fixture({schema: false});
 try {
  const response = await request('/api/auth/get-session');
  assert.equal(response.status, 503);
  assert.equal(response.headers.get('cache-control'), 'no-store');
  assert.deepEqual(await response.json(), {error: 'Authentication is temporarily unavailable.'});
  assert.equal((await request('/__fixture/principal')).status, 500);
 } finally {await worker.dispose();}
});
