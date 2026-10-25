import test from 'node:test';
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import vm from 'node:vm';
import {parse} from 'acorn';
import {sessionFetch} from '../public/session-fetch.js';

const source = await readFile(new URL('../public/app.js', import.meta.url), 'utf8');
const ast = parse(source, {ecmaVersion: 'latest', sourceType: 'module'});
const actualFunction = name => {
  const node = ast.body.find(node => node.type === 'FunctionDeclaration' && node.id.name === name);
  assert.ok(node, `Actual app ${name} exists`);
  return source.slice(node.start, node.end);
};
function kitchen(overrides = {}) {
  const requests = [], writes = [];
  const context = vm.createContext({
    Error, JSON, AbortSignal, Map, demoMode: false,
    requestIdentity: {owner: 'Opaque: Account-A'},
    getUser: async () => ({id: 'Opaque: Account-A'}),
    refreshSession: async () => {},
    fetch: async (path, options) => {requests.push({path, options}); return Response.json({revision: 7});},
    t: value => value, apiError: (data, fallback) => Error(data.error || fallback),
    KEY: 'account-a-inventory', PRODUCTS: 'account-a-products', RECIPES: 'account-a-recipes',
    PROFILE: 'account-a-profile', SELECTIONS: 'account-a-selections',
    localStorage: {setItem: (...args) => writes.push(['set', ...args]), removeItem: (...args) => writes.push(['remove', ...args])},
    confirm: () => true, fetchRecipes: async () => [], validateRecipes: rows => rows,
    loadProfile() {}, pantry() {}, findMeals() {}, syncReady: false,
    setLocalizedText() {}, $: () => ({}), ...overrides,
  });
  context.boundFetch = sessionFetch({identity: () => context.requestIdentity,
    refresh: () => context.refreshSession(), currentUser: () => context.getUser(),
    request: (...args) => context.fetch(...args)});
  vm.runInContext(actualFunction('cloudRequest') + '\n' + actualFunction('loadCloud'), context);
  return {context, requests, writes};
}
const saved = {inventory: [{id: 'A-only'}], products: {}, recipes: [], profile: {}, selections: []};

test('actual cloud state request preserves method, opaque initiating owner and JSON body', async () => {
  const {context, requests} = kitchen();
  const result = await context.cloudRequest('PUT', {revision: 6, state: saved});
  assert.equal(result.revision, 7);
  assert.equal(requests.length, 1);
  assert.equal(requests[0].path, '/api/state');
  assert.equal(requests[0].options.method, 'PUT');
  assert.deepEqual(JSON.parse(requests[0].options.body), {revision: 6, state: saved});
});

test('actual cloud state write never submits after an account switch during refresh', async () => {
  const {context, requests} = kitchen();
  context.refreshSession = async () => {context.requestIdentity = {owner: 'Account-B'};};
  await assert.rejects(context.cloudRequest('PUT', {state: saved}), /Account changed/);
  assert.equal(requests.length, 0);
});

test('actual cloud state discards a private body that arrives after an account switch', async () => {
  const {context} = kitchen();
  context.fetch = async () => ({ok: true, json: async () => {
    context.requestIdentity = {owner: 'Account-B'};
    return {revision: 7, state: saved};
  }});
  await assert.rejects(context.cloudRequest('GET'), /Account changed/);
});

test('actual demo cloud state request remains unavailable without refresh or network', async () => {
  const {context, requests} = kitchen({demoMode: true,
    refreshSession: () => {throw Error('Unexpected refresh');}});
  await assert.rejects(context.cloudRequest('GET'), /Exit the demo/);
  assert.equal(requests.length, 0);
});

test('actual load waits for recipes and rejects a changed owner before any kitchen write', async () => {
  const {context, writes} = kitchen({fetch: async () => Response.json({revision: 7, state: saved})});
  context.fetchRecipes = async () => {context.requestIdentity = {owner: 'Account-B'}; return [];};
  await assert.rejects(context.loadCloud(false), /Account changed/);
  assert.deepEqual(writes, []);
});

test('actual load with stable owner writes only its selected account keys and revision', async () => {
  const {context, writes} = kitchen({fetch: async () => Response.json({revision: 7, state: saved})});
  await context.loadCloud(false);
  assert.equal(context.revision, 7);
  assert.equal(context.dirty, false);
  assert.equal(writes.find(([kind, key]) => kind === 'set' && key === 'account-a-inventory')[2], JSON.stringify(saved.inventory));
  assert.equal(writes.find(([kind, key]) => kind === 'set' && key === 'account-a-inventory-revision')[2], '7');
  assert.equal(writes.every(([, key]) => key.startsWith('account-a-')), true);
});

test('declining replacement leaves all local kitchen data and revision untouched', async () => {
  const {context, writes} = kitchen({fetch: async () => Response.json({revision: 7, state: saved}), confirm: () => false});
  await context.loadCloud(true);
  assert.deepEqual(writes, []);
  assert.equal(context.revision, undefined);
});
