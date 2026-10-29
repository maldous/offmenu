import test from 'node:test';
import assert from 'node:assert/strict';
import {copyReviewedWeek} from '../../apps/web/src/plan-template-model.js';
import {planSummary} from '../../apps/web/src/menu-model.js';

function fixture() {
  return {
    source: {accountId: 'account-a', reviewed: true, weekStart: '2026-10-26', entries: [
      {id: 'old', recipeId: 'rice', date: '2026-11-01', slot: 'Lunch', servings: 2, memberIds: ['member-a'], adjustments: ['manual review'], cookBatchId: 'old-batch', provenance: {sourceId: 'synthetic-rice', rights: 'unknown', quantity: null}}
    ]},
    target: {accountId: 'account-a', weekStart: '2026-11-02', attendance: {'2026-11-08|Lunch': ['member-a']}, equipmentIds: ['pot'], lunchboxPortability: {old: true}},
    requirements: {old: {equipmentIds: ['pot'], lunchbox: true}}, newIds: ['new'], existingIds: []
  };
}
test('copies weekday across month boundary; preserves quantities and opaque uncertainty without mutating source', () => {
  const input = fixture(), before = structuredClone(input), result = copyReviewedWeek(input);
  assert.equal(result.status, 'needs-target-review');
  assert.equal(result.entries[0].date, '2026-11-08');
  const expected = {...before.source.entries[0], id: 'new', date: '2026-11-08'};
  delete expected.cookBatchId;
  assert.deepEqual(result.entries[0], expected);
  assert.deepEqual(input, before);
  result.entries[0].provenance.rights = 'changed';
  result.entries[0].memberIds.push('other');
  assert.deepEqual(input, before);
});
test('a second blocked meal prevents partial copying, and duplicate identities are rejected', () => {
  const input = fixture();
  input.source.entries.push({...structuredClone(input.source.entries[0]), id: 'second', slot: 'Dinner'});
  input.newIds.push('new-second');
  const result = copyReviewedWeek(input);
  assert.equal(result.status, 'blocked'); assert.deepEqual(result.entries, []);
  input.source.entries[1].id = 'old';
  assert.throws(() => copyReviewedWeek(input), /Invalid template entry/);
  input.newIds = ['new', 'new'];
  assert.throws(() => copyReviewedWeek(input), /Invalid target IDs/);
});
test('explicit empty equipment requirements and non-lunchbox meals need no portability claim', () => {
  const input = fixture();
  input.requirements.old = {equipmentIds: [], lunchbox: false};
  input.target.equipmentIds = [];
  delete input.target.lunchboxPortability;
  assert.equal(copyReviewedWeek(input).status, 'needs-target-review');
});
test('new week requires ingredients rather than reusing old cooked stock', () => {
  const input = fixture(), recipes = [{id: 'rice', servings: 2, ingredients: [{ingredient: 'rice', quantity: 100, unit: 'g'}]}];
  const naive = {...input.source.entries[0], date: '2026-11-08'};
  assert.deepEqual(planSummary([naive], recipes, [], {}, [naive.date]).missing, []);
  const result = copyReviewedWeek(input);
  assert.equal(planSummary(result.entries, recipes, [], {}, ['2026-11-08']).missing[0].quantity, 100);
});
test('missing and incompatible bounds block all entries', () => {
  for (const [change, code] of [
    [x => delete x.target.attendance, 'attendance-unknown'],
    [x => x.target.attendance['2026-11-08|Lunch'] = [], 'attendee-unavailable'],
    [x => delete x.requirements.old, 'requirements-unknown'],
    [x => delete x.target.equipmentIds, 'equipment-unknown'],
    [x => x.target.equipmentIds = [], 'equipment-unavailable'],
    [x => delete x.target.lunchboxPortability, 'lunchbox-portability-unconfirmed'],
    [x => x.target.lunchboxPortability.old = false, 'lunchbox-portability-unconfirmed']
  ]) {
    const input = fixture(); change(input);
    const result = copyReviewedWeek(input);
    assert.equal(result.status, 'blocked'); assert.deepEqual(result.entries, []);
    assert.ok(result.blockers.some(blocker => blocker.code === code));
  }
});
test('rejects cross-account, unreviewed, invalid dates, IDs and oversized inputs', () => {
  for (const change of [
    x => x.target.accountId = 'account-b', x => x.source.reviewed = false,
    x => x.target.weekStart = '2026-02-30', x => x.target.weekStart = '2026-11-03',
    x => x.source.entries[0].date = '2026-11-02', x => x.newIds = ['old'],
    x => x.existingIds = ['new'], x => x.source.entries[0].memberIds = undefined,
    x => x.source.entries[0].servings = NaN,
    x => x.source.entries = Array(101).fill(x.source.entries[0])
  ]) { const input = fixture(); change(input); assert.throws(() => copyReviewedWeek(input)); }
});
