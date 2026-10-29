import test from 'node:test';
import assert from 'node:assert/strict';
import {toOffMenuPrincipal, getOffMenuPrincipal} from '../../apps/web/server/auth-principal.mjs';
import {createOffMenuAuth} from '../../apps/web/server/auth.mjs';

const user = {id: 'Original-Subject_01', email: 'alice@example.test', emailVerified: true,
  name: 'Alice', appRoles: '["offmenu-admin"]', password: 'must-not-leak',
  user_metadata: {roles: ['admin']}, app_metadata: {roles: ['admin']}};
const env = {DB: {prepare() {}, batch() {}}, BETTER_AUTH_URL: 'https://offmenu.test',
  BETTER_AUTH_SECRET: 'synthetic-only-not-a-deployment-secret-000000000'};
const sessionPolicy = {expiresIn: 3600, updateAge: 600};

test('principal keeps the exact opaque owner and only trusted role storage', () => {
  const result = toOffMenuPrincipal(user);
  assert.deepEqual(result, {id: user.id, name: 'Alice', email: user.email, emailVerified: true,
    app_metadata: {roles: ['offmenu-admin']}});
  assert(Object.isFrozen(result));
  assert(Object.isFrozen(result.app_metadata.roles));
  assert(!('password' in result));
  assert(!('user_metadata' in result));
  assert.equal(toOffMenuPrincipal({...user, id: 'MixedCase_User:Opaque'}).id, 'MixedCase_User:Opaque');
});

test('malformed roles and untrusted metadata cannot grant administrator access', () => {
  for (const appRoles of [undefined, null, '', 'bad json', '{}', '["admin",false]', '"admin"']) {
    assert.deepEqual(toOffMenuPrincipal({...user, appRoles}).app_metadata.roles, []);
  }
  assert.deepEqual(toOffMenuPrincipal({...user, appRoles: '["admin","admin","custom-role"]'}).app_metadata.roles, ['admin', 'custom-role']);
  for (const emailVerified of [false, undefined, 'true', 1]) {
    assert.equal(toOffMenuPrincipal({...user, emailVerified}).emailVerified, false);
  }
});

test('missing or malformed subjects are rejected without normalizing ownership', () => {
  for (const id of ['', ' ', null, 4, 'x'.repeat(200)]) assert.equal(toOffMenuPrincipal({...user, id}), null);
  assert.equal(toOffMenuPrincipal(null), null);
});

test('route adapter requires matching verified session owner and disables stale cache/hidden refresh', async () => {
  const request = new Request('https://offmenu.test/api/state', {headers: {Cookie: 'synthetic-cookie'}});
  let seen;
  const auth = {api: {getSession: async options => {seen = options; return {user, session: {userId: user.id}};}}};
  assert.equal((await getOffMenuPrincipal(auth, request)).id, user.id);
  assert.equal(seen.headers, request.headers);
  assert.deepEqual(seen.query, {disableCookieCache: true, disableRefresh: true});
  for (const result of [null, {}, {user, session: {userId: 'different'}}, {user}]) {
    assert.equal(await getOffMenuPrincipal({api: {getSession: async () => result}}, request), null);
  }
  const error = new Error('synthetic database outage');
  await assert.rejects(getOffMenuPrincipal({api: {getSession: async () => {throw error;}}}, request), error);
});

test('factory fails before construction for missing database, origin, secret or session policy', () => {
  assert.throws(() => createOffMenuAuth({}, {sessionPolicy}), /D1/);
  for (const BETTER_AUTH_URL of [undefined, 'http://offmenu.test', 'https://u:p@offmenu.test', 'https://offmenu.test/path', 'https://offmenu.test/?x=1', 'https://offmenu.test/#x']) {
    assert.throws(() => createOffMenuAuth({...env, BETTER_AUTH_URL}, {sessionPolicy}), /HTTPS origin/);
  }
  assert.throws(() => createOffMenuAuth({...env, BETTER_AUTH_SECRET: 'short'}, {sessionPolicy}), /secret/);
  for (const policy of [undefined, {}, {expiresIn: 0, updateAge: 0}, {expiresIn: 10, updateAge: 10}, {expiresIn: 10, updateAge: -1}]) {
    assert.throws(() => createOffMenuAuth(env, {sessionPolicy: policy}), /session expiry/);
  }
  assert.throws(() => createOffMenuAuth(env, {sessionPolicy, email: {enabled: true}}), /delivery/);
});
