import test from 'node:test';
import assert from 'node:assert/strict';
import {emptyMealContext, validateMealContext, transitionMealContext, mealContextAt} from '../../apps/web/src/meal-context-model.js';
const source = {label: 'Original user declaration — العربية', reference: null};
const declaration = (id, kind, extra = {}) => ({id, kind, label: '  Original label  ', source, qualifiers: ['unknown suitability', 'as stated'], status: 'declared', ...extra});
const caller = {accountId: 'a', actorId: 'user-a', permit: () => ({allowed: true})};
const edit = (value, d) => transitionMealContext(value, caller, {type: 'declare', declaration: d});
function fixture() {
  let value = emptyMealContext('a');
  value = edit(value, declaration('home1', 'home'));
  value = edit(value, declaration('home2', 'home'));
  return edit(value, declaration('carer1', 'carer', {homeIds: ['home1']}));
}
test('explicit home transfer requires choice and scoped authority, never carries a carer to an unscoped home', () => {
  const initial = fixture();
  const chosen = transitionMealContext(initial, caller, {type: 'choose', homeId: 'home1', carerId: 'carer1'});
  assert.deepEqual(initial.selection, {homeId: null, carerId: null});
  assert.throws(() => transitionMealContext(chosen, caller, {type: 'choose', homeId: 'home2', carerId: 'carer1'}), /carer unavailable/);
  const moved = transitionMealContext(chosen, caller, {type: 'choose', homeId: 'home2', carerId: null});
  assert.deepEqual(moved.selection, {homeId: 'home2', carerId: null});
  assert.deepEqual(chosen.selection, {homeId: 'home1', carerId: 'carer1'});
  assert.throws(() => transitionMealContext(chosen, {...caller, permit: () => ({allowed: false})}, {type: 'choose', homeId: 'home2', carerId: null}), /not authorized/);
});
test('culture/taste preserve original source, label and unknown qualifiers without generating restrictions', () => {
  const d = declaration('culture', 'culture', {label: 'رمضان / original user label'});
  const initial = emptyMealContext('a'), snapshot = JSON.stringify(d);
  const value = edit(edit(initial, d), declaration('taste', 'taste', {label: 'spicy', status: 'unknown'}));
  assert.equal(JSON.stringify(d), snapshot);
  assert.deepEqual(value.declarations[0], d);
  const projection = mealContextAt(value, {accountId: 'a', at: '2026-10-15T00:00:00Z'});
  assert.deepEqual(projection.fasting, []);
  assert.deepEqual(Object.keys(projection).sort(), ['declarations', 'fasting', 'selection']);
  assert.equal(projection.declarations[1].status, 'unknown');
  assert.throws(() => { value.declarations[0].source.label = 'mutated'; }, TypeError);
  d.source = {label: 'changed externally', reference: null};
  assert.equal(value.declarations[0].source.label, source.label);
});
test('dated Melbourne midnight window uses explicit zone and half-open boundaries', () => {
  const value = edit(emptyMealContext('a'), declaration('fast', 'fasting', {window: {start: '2026-10-14T23:00:00+11:00', end: '2026-10-15T05:00:00+11:00', timeZone: 'Australia/Melbourne'}}));
  const status = at => mealContextAt(value, {accountId: 'a', at}).fasting[0].status;
  assert.equal(status('2026-10-14T11:59:59Z'), 'outside-declared-window');
  assert.equal(status('2026-10-14T12:00:00Z'), 'inside-declared-window');
  assert.equal(status('2026-10-14T17:59:59Z'), 'inside-declared-window');
  assert.equal(status('2026-10-14T18:00:00Z'), 'outside-declared-window');
});
test('DST transition preserves offset-qualified endpoints and rejects nonexistent wall times', () => {
  const window = {start: '2026-10-04T01:30:00+10:00', end: '2026-10-04T03:30:00+11:00', timeZone: 'Australia/Melbourne'};
  const value = edit(emptyMealContext('a'), declaration('dst', 'fasting', {window}));
  assert.equal(mealContextAt(value, {accountId: 'a', at: '2026-10-03T16:00:00Z'}).fasting[0].status, 'inside-declared-window');
  assert.throws(() => edit(emptyMealContext('a'), declaration('bad', 'fasting', {window: {...window, start: '2026-10-04T02:30:00+10:00', end: '2026-10-04T04:30:00+11:00'}})), /Offset/);
  assert.throws(() => edit(emptyMealContext('a'), declaration('bad', 'fasting', {window: {...window, start: '2026-10-04T01:30:00'}})), /explicit offset/);
});
test('unknown fasting and withdrawal remain explicit, preserving source facts', () => {
  const value = edit(emptyMealContext('a'), declaration('fast', 'fasting', {window: null}));
  assert.equal(mealContextAt(value, {accountId: 'a', at: '2026-10-15T00:00:00Z'}).fasting[0].status, 'unknown');
  const withdrawn = transitionMealContext(value, caller, {type: 'withdraw', id: 'fast'});
  assert.equal(withdrawn.declarations[0].status, 'withdrawn');
  assert.deepEqual(withdrawn.declarations[0].source, value.declarations[0].source);
  assert.equal(mealContextAt(withdrawn, {accountId: 'a', at: '2026-10-15T00:00:00Z'}).fasting[0].status, 'withdrawn');
  assert.equal(value.declarations[0].status, 'declared');
});
test('withdrawn selected home clears selection; unknown carer scope is not a grant', () => {
  const chosen = transitionMealContext(fixture(), caller, {type: 'choose', homeId: 'home1', carerId: 'carer1'});
  const next = transitionMealContext(chosen, caller, {type: 'withdraw', id: 'home1'});
  assert.deepEqual(next.selection, {homeId: null, carerId: null});
  const unknown = edit(chosen, declaration('carer1', 'carer', {homeIds: null}));
  assert.equal(unknown.selection.carerId, null);
  assert.throws(() => transitionMealContext(unknown, caller, {type: 'choose', homeId: 'home1', carerId: 'carer1'}), /carer unavailable/);
});
test('permissions bind verified caller and exact frozen choice; async approvals are unavailable', () => {
  let observed;
  const value = transitionMealContext(fixture(), {...caller, permit: input => { observed = input; return {allowed: true}; }}, {type: 'choose', homeId: 'home2', carerId: null});
  assert.deepEqual(observed, {accountId: 'a', actorId: 'user-a', action: {type: 'choose', homeId: 'home2', carerId: null}, homeId: 'home2', carerId: null});
  assert(Object.isFrozen(observed.action));
  assert.equal(value.selection.homeId, 'home2');
  assert.throws(() => transitionMealContext(fixture(), {...caller, permit: () => Promise.resolve({allowed: true})}, {type: 'choose', homeId: 'home2', carerId: null}), /not authorized/);
  assert.throws(() => validateMealContext(fixture(), 'other-account'), /same-account/);
});
test('invalid dates/zone/order and foreign/malformed scopes fail without partial transition', () => {
  const value = emptyMealContext('a');
  for (const window of [
    {start: '2026-02-30T00:00:00Z', end: '2026-03-02T00:00:00Z', timeZone: 'UTC'},
    {start: '2026-10-15T01:00:00Z', end: '2026-10-15T00:00:00Z', timeZone: 'UTC'},
    {start: '2026-10-15T00:00:00Z', end: '2026-10-15T01:00:00Z', timeZone: 'Mars/Unknown'}]) assert.throws(() => edit(value, declaration('bad', 'fasting', {window})));
  assert.throws(() => edit(value, declaration('carer', 'carer', {homeIds: ['unavailable']})), /Unknown carer home/);
  assert.throws(() => edit(value, {...declaration('culture', 'culture'), religiousRestriction: true}), /Unsupported/);
  assert.deepEqual(value, emptyMealContext('a'));
});
test('untrusted accessors and sparse/oversized payloads are rejected without invoking getters', () => {
  let calls = 0; const value = {get accountId() { calls++; return 'a'; }};
  assert.throws(() => validateMealContext(value, 'a'), /Unsafe/); assert.equal(calls, 0);
  assert.throws(() => validateMealContext({version: 1, accountId: 'a', declarations: Array(2), selection: {homeId: null, carerId: null}}, 'a'), /Dense|sparse/);
  assert.throws(() => edit(emptyMealContext('a'), declaration('long', 'taste', {label: 'x'.repeat(70000)})), /bounds/);
});
