import test from 'node:test';
import assert from 'node:assert/strict';
import handler from '../cloud/handler.mjs';
import {validateState} from '../cloud/state.mjs';
import {memberSuitability} from '../public/household-model.js';
import {kitchenProjection, applyKitchen} from '../public/sync-model.js';
import {validateMealPreferences, validateAccountMealState, updateAccountMealPreferences} from '../cloud/meal-preference-owner20.mjs';

const context = {accountId: 'account-a', memberId: 'sam', consent: true};
const pref = () => ({version: 1, scope: {accountId: 'account-a', memberId: 'sam'}, likes: ['rice'], textures: ['Crisp'], spice: null});
const state = () => ({inventory: [], products: {}, recipes: [], selections: [], profile: {country: 'AU', units: 'metric', servings: 1, members: [{id: 'sam', name: 'Sam', portion: 1, avoid: ['onion'], advisors: ['vegan'], restrictions: [{type: 'allergy', term: 'peanut'}], mealPreferences: pref()}]}});

test('actual /api/state PUT currently drops envelope: central owner integration remains required', async () => {
  const originalFetch = globalThis.fetch;
  let stored;
  globalThis.fetch = async url => {
    assert.equal(url, 'https://offmenu-accounts.netlify.app/.netlify/identity/user');
    return Response.json({id: 'account-a'});
  };
  const DB = {prepare(sql) { return {bind(...values) {
    assert.match(sql, /INSERT INTO user_state/);
    assert.equal(values[0], 'account-a');
    stored = JSON.parse(values[1]);
    return {first: async () => ({revision: 1})};
  }}; }};
  try {
    const response = await handler.fetch(new Request('https://synthetic.invalid/api/state', {method: 'PUT', headers: {Origin: 'https://synthetic.invalid', Authorization: 'Bearer synthetic', 'Content-Type': 'application/json'}, body: JSON.stringify({revision: 0, state: state()})}), {DB});
    assert.equal(response.status, 200);
    assert.equal(stored.profile.members[0].mealPreferences, undefined);
    assert.deepEqual(stored.profile.members[0].restrictions, state().profile.members[0].restrictions);
  } finally { globalThis.fetch = originalFetch; }
});

test('wrapper exercises real validator and preserves scoped preferences through JSON save/restore', () => {
  const input = state(), before = structuredClone(input);
  assert.equal(validateState(input).profile.members[0].mealPreferences, undefined);
  const validated = validateAccountMealState(input, 'account-a');
  assert.deepEqual(validated.profile.members[0].mealPreferences, pref());
  assert.deepEqual(validateAccountMealState(JSON.parse(JSON.stringify(validated)), 'account-a'), validated);
  assert.deepEqual(input, before);
  assert.throws(() => validateAccountMealState(validated, 'account-b'), /scope/);
});

test('account consumer edits and resets only taste; unknown and explicit none remain distinct', () => {
  const input = state(), before = structuredClone(input);
  const edited = updateAccountMealPreferences(input, context, {type: 'edit', patch: {spice: 'none', likes: ['peanut']}});
  assert.equal(edited.profile.members[0].mealPreferences.spice, 'none');
  assert.deepEqual(edited.profile.members[0].mealPreferences.textures, ['Crisp']);
  const reset = updateAccountMealPreferences(edited, context, {type: 'reset', fields: ['spice']});
  assert.equal(reset.profile.members[0].mealPreferences.spice, null);
  assert.deepEqual(reset.profile.members[0].mealPreferences.likes, ['peanut']);
  const full = updateAccountMealPreferences(reset, context, {type: 'reset'});
  assert.deepEqual(full.profile.members[0].mealPreferences, {...pref(), likes: [], textures: []});
  for (const output of [edited, reset, full]) {
    const {mealPreferences, ...member} = output.profile.members[0];
    const {mealPreferences: ignored, ...baseline} = validateState(input).profile.members[0];
    assert.deepEqual(member, baseline);
    assert.equal(memberSuitability({ingredients: [{ingredient: 'peanut butter'}]}, output.profile.members[0]).status, 'blocked');
    const unknown = memberSuitability({ingredients: [{ingredient: 'mystery sauce'}]}, output.profile.members[0]);
    assert.equal(unknown.status, 'needs-check'); assert.equal(unknown.automaticSelection, false);
  }
  assert.deepEqual(input, before);
});

test('legacy members remain without inferred preference; new explicit edit may create envelope', () => {
  const input = state(); delete input.profile.members[0].mealPreferences;
  assert.equal(validateAccountMealState(input, 'account-a').profile.members[0].mealPreferences, undefined);
  assert.equal(updateAccountMealPreferences(input, context, {type: 'edit', patch: {likes: ['rice']}}).profile.members[0].mealPreferences.spice, null);
});

test('consumer rejects missing consent/member, foreign account, duplicate IDs, and exclusion edits', () => {
  for (const ctx of [{...context, consent: false}, {...context, consent: undefined}, {...context, memberId: 'other'}, {...context, accountId: 'account-b'}]) assert.throws(() => updateAccountMealPreferences(state(), ctx, {type: 'reset'}));
  assert.throws(() => updateAccountMealPreferences(state(), context, {type: 'edit', patch: {restrictions: []}}));
  assert.throws(() => updateAccountMealPreferences(state(), context, {type: 'reset', fields: ['allergies']}));
  const duplicate = state(); duplicate.profile.members.push(structuredClone(duplicate.profile.members[0]));
  assert.throws(() => validateAccountMealState(duplicate, 'account-a'), /Duplicate/);
});

test('persisted boundary rejects malformed/sparse/custom/accessor objects without invoking getters', () => {
  let calls = 0;
  const accessor = pref(); Object.defineProperty(accessor, 'spice', {enumerable: true, get() {calls++; return 'safe';}});
  const custom = [42]; custom.some = () => {calls++; return false;};
  for (const invalid of [{...pref(), likes: new Array(1)}, {...pref(), likes: custom}, {...pref(), version: 2}, {...pref(), scope: {...pref().scope, memberId: 'other'}}, {...pref(), spice: 'safe'}, {...pref(), restrictions: []}, accessor]) assert.throws(() => validateMealPreferences(invalid, 'account-a', 'sam'));
  const input = state(); Object.defineProperty(input.profile.members[0], 'mealPreferences', {enumerable: true, get() {calls++; return pref();}});
  assert.throws(() => validateAccountMealState(input, 'account-a'));
  assert.equal(calls, 0);
});

test('dense boundaries, all spice scalars, source spelling and detached output are retained', () => {
  for (const spice of [null, 'none', 'mild', 'medium', 'hot']) {
    const input = {...pref(), likes: Array(32).fill('x'.repeat(100)), textures: [' Cilantro '], spice};
    const output = validateMealPreferences(input, 'account-a', 'sam');
    assert.deepEqual(JSON.parse(JSON.stringify(output)), input);
    output.likes.push('new'); assert.equal(input.likes.length, 32);
  }
  assert.throws(() => validateMealPreferences({...pref(), likes: Array(33).fill('rice')}, 'account-a', 'sam'));
});

test('private preferences are excluded from actual shared kitchen projection and retained on apply', () => {
  const account = validateAccountMealState(state(), 'account-a'), kitchen = kitchenProjection(account);
  assert.equal(kitchen.profile.members, undefined);
  assert.deepEqual(applyKitchen(account, kitchen).profile.members, account.profile.members);
});
