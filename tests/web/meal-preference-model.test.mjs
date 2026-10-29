import test from 'node:test';
import assert from 'node:assert/strict';
import {createMealPreferences, setMealPreferences, resetMealPreferences, withMealPreferences} from '../../apps/web/src/meal-preference-model.js';
import {validateState} from '../../apps/web/server/state.mjs';
import {memberSuitability} from '../../apps/web/src/household-model.js';

const scope = {accountId: 'synthetic-account', memberId: 'sam'};
const filled = () => setMealPreferences(createMealPreferences(scope), scope, {likes: ['rice'], textures: ['crunchy'], spice: 'mild'});

test('rejects sparse arrays and custom some/iterator hooks without invoking them', () => {
  let calls = 0;
  const custom = [42];
  custom.some = () => { calls++; return false; };
  const iterator = ['rice'];
  iterator[Symbol.iterator] = function* () { calls++; yield 42; };
  const indexed = ['rice'];
  Object.defineProperty(indexed, '0', {enumerable: true, get() { calls++; return 'rice'; }});
  for (const terms of [new Array(1), custom, iterator, indexed]) {
    for (const field of ['likes', 'textures']) {
      assert.throws(() => setMealPreferences(filled(), scope, {[field]: terms}));
    }
  }
  assert.throws(() => resetMealPreferences(filled(), scope, new Array(1)));
  assert.throws(() => resetMealPreferences(filled(), scope, custom));
  assert.equal(calls, 0);
});

test('rejects accessors across state/patch/scope/member without reading them', () => {
  let reads = 0;
  const accessor = (object, key) => Object.defineProperty(object, key, {
    enumerable: true, get() { reads++; return reads <= 2 ? 'mild' : 'safe'; }
  });
  const state = accessor(createMealPreferences(scope), 'spice');
  assert.throws(() => withMealPreferences({id: 'sam'}, state, scope));
  assert.throws(() => setMealPreferences(state, scope, {}));
  assert.throws(() => resetMealPreferences(state, scope));
  assert.throws(() => setMealPreferences(filled(), scope, accessor({}, 'spice')));
  assert.throws(() => createMealPreferences(accessor({...scope}, 'accountId')));
  assert.throws(() => withMealPreferences({id: 'sam', source: accessor({}, 'quantity')}, filled(), scope));
  assert.equal(reads, 0);
});

test('dense boundary data and every ordinary spice value survive JSON roundtrip/reset', () => {
  for (const spice of [null, 'none', 'mild', 'medium', 'hot']) {
    const state = setMealPreferences(createMealPreferences(scope), scope, {
      likes: Array.from({length: 32}, (_, i) => 'x'.repeat(98) + String(i).padStart(2, '0')),
      textures: ['Crisp', ' soft '], spice
    });
    const restored = JSON.parse(JSON.stringify(state));
    assert.deepEqual(setMealPreferences(restored, scope, {}), state);
    assert.equal(withMealPreferences({id: 'sam'}, restored, scope).mealPreferences.spice, spice);
    assert.deepEqual(resetMealPreferences(restored, scope), createMealPreferences(scope));
    assert.deepEqual(state.textures, ['Crisp', ' soft ']);
  }
});

test('existing cloud validator drops explicit taste fields: adoption requires schema owner', () => {
  const member = {id: 'sam', name: 'Sam', portion: 1, avoid: [], advisors: ['balanced'], likes: ['rice'], textures: ['crunchy'], spice: 'mild'};
  const saved = validateState({inventory: [], products: {}, recipes: [], selections: [], profile: {country: 'AU', units: 'metric', servings: 1, members: [member]}}).profile.members[0];
  assert.equal(saved.likes, undefined);
  assert.equal(saved.textures, undefined);
  assert.equal(saved.spice, undefined);
});

test('partial edits preserve entered terms and distinguish unknown spice from explicit none', () => {
  const original = filled(), before = structuredClone(original);
  const input = ['Cilantro', 'rice'];
  const next = setMealPreferences(original, scope, {likes: input, spice: 'none'});
  input.push('changed later');
  assert.deepEqual(next.likes, ['Cilantro', 'rice']);
  assert.deepEqual(next.textures, ['crunchy']);
  assert.equal(next.spice, 'none');
  assert.equal(createMealPreferences(scope).spice, null);
  assert.deepEqual(original, before);
  next.textures.push('soft');
  assert.deepEqual(original.textures, ['crunchy']);
});

test('selective and full reset affect taste only and are idempotent', () => {
  const state = filled(), before = structuredClone(state);
  const selective = resetMealPreferences(state, scope, ['textures']);
  assert.deepEqual(selective, {...state, textures: []});
  const reset = resetMealPreferences(state, scope);
  assert.deepEqual(reset, createMealPreferences(scope));
  assert.deepEqual(resetMealPreferences(reset, scope), reset);
  assert.deepEqual(state, before);
  assert.deepEqual(resetMealPreferences(state, scope, []), state);
});

test('all operations reject cross-account, cross-member and malformed scope', () => {
  const state = filled();
  for (const wrong of [{...scope, accountId: 'other'}, {...scope, memberId: 'other'}, {}, {...scope, accountId: ''}]) {
    assert.throws(() => setMealPreferences(state, wrong, {}));
    assert.throws(() => resetMealPreferences(state, wrong));
    assert.throws(() => withMealPreferences({id: 'sam'}, state, wrong));
  }
  assert.throws(() => withMealPreferences({id: 'other'}, state, scope));
  assert.throws(() => setMealPreferences({...state, version: 2}, scope, {}));
});

test('rejects invalid/unbounded inputs and attempts to update medical or scope fields', () => {
  const state = filled();
  for (const patch of [{likes: ['']}, {likes: Array(33).fill('rice')}, {textures: ['x'.repeat(101)]}, {textures: [42]}, {spice: undefined}, {spice: 'safe'}, {restrictions: []}, {scope}, {allergies: []}, null, []]) {
    assert.throws(() => setMealPreferences(state, scope, patch));
  }
  assert.throws(() => resetMealPreferences(state, scope, ['restrictions']));
  assert.throws(() => setMealPreferences({...state, restrictions: []}, scope, {}));
});

test('adapter preserves restrictions, uncertainty, consent, rights and source quantities; reset cannot clear allergy', () => {
  const member = {id: 'sam', name: 'Sam', portion: 1, advisors: [], avoid: ['onion'], restrictions: [{type: 'allergy', term: 'peanut'}], certainty: 'unknown', consent: false, source: {id: 'synthetic-source', quantity: 2, unit: 'g', rights: 'synthetic-only'}};
  const before = structuredClone(member);
  const preferences = setMealPreferences(filled(), scope, {likes: ['peanut']});
  const result = withMealPreferences(member, resetMealPreferences(preferences, scope), scope);
  const {mealPreferences, ...preserved} = result;
  assert.deepEqual(preserved, before);
  assert.deepEqual(mealPreferences, createMealPreferences(scope));
  const recipe = {ingredients: [{ingredient: 'peanut butter', quantity: 2, unit: 'g'}]};
  assert.equal(memberSuitability(recipe, withMealPreferences(member, preferences, scope)).status, 'blocked');
  assert.equal(memberSuitability(recipe, result).status, 'blocked');
  result.restrictions[0].term = 'changed';
  result.source.quantity = 99;
  assert.deepEqual(member, before);
});
