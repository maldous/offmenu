import test from 'node:test';
import assert from 'node:assert/strict';
import {createOffMenuIdentityClient} from '../public/offmenu-identity-client.js';

const user = id => ({user: {id, name: 'Invented User', email: 'invented@example.test'}, session: {userId: id}});
function fake(sequence) {
  const calls = [];
  const request = async (path, options) => {
    calls.push({path, options});
    const next = sequence.shift();
    if (next instanceof Error) throw next;
    return Response.json(next.body, {status: next.status || 200});
  };
  return {request, calls};
}

test('missing mode passes through the exact existing Netlify adapter without network calls', async () => {
  const legacy = {getUser: async () => ({id: 'Legacy:Opaque'}), refreshSession: async () => {}, login() {}};
  const unavailable = () => { throw Error('No network expected'); };
  const client = createOffMenuIdentityClient({netlify: legacy, request: unavailable});
  assert.equal(client, legacy);
  assert.deepEqual(await client.getUser(), {id: 'Legacy:Opaque'});
  assert.throws(() => createOffMenuIdentityClient({mode: 'automatic', netlify: legacy, request: unavailable}));
});

test('session lookup preserves an exact opaque account ID, without returning token or browser roles', async () => {
  const id = 'Opaque: 001 / account';
  const {request, calls} = fake([{body: user(id)}]);
  const client = createOffMenuIdentityClient({mode: 'better-auth', request});
  assert.deepEqual(await client.getUser(), {id, name: 'Invented User', email: 'invented@example.test', emailVerified: false});
  assert.equal(calls[0].path, '/api/auth/get-session');
  assert.equal(calls[0].options.credentials, 'same-origin');
  assert.equal(calls[0].options.redirect, 'manual');
  assert.equal(calls[0].options.cache, 'no-store');
  assert.equal(calls[0].options.headers.Authorization, undefined);
  assert.equal(await client.getSettings().then(x => x.disableSignup), true);
  assert.deepEqual((await client.getSettings()).providers, {});
});

test('guest, identity mismatch and outage never fall back to Netlify or become another account', async () => {
  const {request, calls} = fake([{body: null}, {body: {user: {id: 'A'}, session: {userId: 'B'}}},
    {status: 503, body: {error: 'Authentication is temporarily unavailable.'}}]);
  const client = createOffMenuIdentityClient({mode: 'better-auth', request, netlify: {getUser() {throw Error('legacy used');}}});
  assert.equal(await client.getUser(), null);
  await assert.rejects(client.getUser(), /session unavailable/);
  await assert.rejects(client.getUser(), /request failed/);
  assert.equal(calls.length, 3);
});

test('email sign-in uses same-origin cookies, confirms the new session and never stores a bearer', async () => {
  const {request, calls} = fake([{body: {token: 'synthetic-token-not-used'}}, {body: user('opaque-signin')}]);
  const client = createOffMenuIdentityClient({mode: 'better-auth', request});
  assert.equal((await client.login('invented@example.test', 'synthetic-password')).id, 'opaque-signin');
  assert.deepEqual(calls.map(x => x.path), ['/api/auth/sign-in/email', '/api/auth/get-session']);
  assert.deepEqual(JSON.parse(calls[0].options.body), {email: 'invented@example.test', password: 'synthetic-password'});
  assert.equal(calls[0].options.headers.Authorization, undefined);
  assert.equal(calls[0].options.credentials, 'same-origin');
});

test('logout requires server acknowledgement and observed guest session', async () => {
  const one = fake([{body: {success: true}}, {body: null}]);
  await createOffMenuIdentityClient({mode: 'better-auth', request: one.request}).logout();
  assert.deepEqual(one.calls.map(x => x.path), ['/api/auth/sign-out', '/api/auth/get-session']);
  const two = fake([{body: {success: true}}, {body: user('still-active')}]);
  await assert.rejects(createOffMenuIdentityClient({mode: 'better-auth', request: two.request}).logout(), /remains active/);
});

test('unqualified provider, signup, recovery, invite and profile-change flows fail closed', async () => {
  const client = createOffMenuIdentityClient({mode: 'better-auth', request: () => {throw Error('No request expected');}});
  for (const name of ['signup', 'oauthLogin', 'requestPasswordRecovery', 'updateUser', 'acceptInvite'])
    assert.throws(() => client[name](), {code: 'AUTH_FLOW_NOT_CONFIGURED'});
  assert.equal(await client.handleAuthCallback(), null);
});

test('redirect, non-JSON response, malformed session and refresh outage are surfaced', async () => {
  const requests = [async () => new Response(null, {status: 302, headers: {Location: 'https://other.test'}}),
    async () => new Response('html', {headers: {'Content-Type': 'text/html'}}),
    async () => Response.json({user: {id: 'X'}}),
    async () => Response.json({error: 'synthetic outage'}, {status: 503})];
  for (const request of requests) {
    const client = createOffMenuIdentityClient({mode: 'better-auth', request});
    await assert.rejects(client.refreshSession());
  }
});

test('accepted account guard rejects an in-flight owner switch without accepting the body', async () => {
  const {sessionFetch} = await import('../public/session-fetch.js');
  let owner = {owner: 'opaque-A'}, requests = 0;
  const bound = sessionFetch({identity: () => owner, refresh: async () => {},
    currentUser: async () => ({id: 'opaque-A'}),
    request: async () => {requests++; return Response.json({private: true});}});
  const response = await bound('/api/state', {method: 'GET'});
  assert.equal(requests, 1);
  owner = {owner: 'opaque-B'};
  await assert.rejects(response.json(), /Account changed/);
  const second = sessionFetch({identity: () => owner,
    refresh: async () => {owner = {owner: 'opaque-C'};},
    currentUser: async () => ({id: 'opaque-B'}),
    request: async () => {requests++; return Response.json({private: true});}});
  await assert.rejects(second('/api/state', {method: 'GET'}), /Account changed/);
  assert.equal(requests, 1);
});
