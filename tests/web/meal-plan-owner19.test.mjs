import test from 'node:test';
import assert from 'node:assert/strict';
import {transitionMealPlan19, createMealPlanOwner19} from '../../public/meal-plan-owner19.mjs';
import {planSummary} from '../../public/menu-model.js';
import {validateState} from '../../cloud/state.mjs';

const clock = () => '2026-10-14T10:00:00.000Z';
function state() {
  return {inventory: [{id: 'lot-rice', barcode: 'local:rice', name: 'Rice', ingredient: 'rice', quantity: 400, unit: 'g', location: {area: 'Pantry', shelf: 'A'}, amountBasis: 'manual', needsReview: false}], products: {}, recipes: [{id: 'rice', title: 'Rice', servings: 2, ingredients: [{ingredient: 'rice', quantity: 100, unit: 'g', sourceQuantity: '100 g', provenance: {sourceId: 'fixture', rights: 'unknown'}}], instructions: ['Cook'], source: 'Synthetic fixture', license: 'unknown', provenance: {sourceId: 'fixture', certainty: null}}], profile: {country: 'AU', units: 'metric', servings: 2, plan: [{id: 'plan-a', recipeId: 'rice', date: '2026-10-14', slot: 'Dinner', servings: 2, memberIds: ['member-a']}], batches: [], history: []}, selections: []};
}
const run = (s, action) => transitionMealPlan19({state: s, action, clock});
const cook = {type: 'cook', planId: 'plan-a', date: '2026-10-14', reviewed: true, mutationId: 'cook-a'};
const serve = {type: 'serve', planId: 'plan-a', date: '2026-10-14', eventId: 'serve-a', portions: 1, memberId: 'member-a'};

test('real cook/serve/undo lifecycle returns immutable app state and preserves unknown intake', () => {
  const original = state(), before = structuredClone(original), cooked = run(original, cook);
  assert.deepEqual(original, before);
  assert.equal(cooked.state.inventory.find(l => l.id === 'lot-rice').quantity, 300);
  assert.equal(cooked.state.profile.plan[0].cookBatchId, 'cook-a');
  assert.equal(cooked.state.profile.batches[0].createdAt, clock());
  assert.deepEqual(cooked.state.profile.batches[0].sourceEvidence.sourceRecipe, before.recipes[0]);
  const untouchedCooked = structuredClone(cooked.state);
  const undone = run(cooked.state, {type: 'undo', planId: 'plan-a'});
  assert.equal(undone.state.inventory[0].quantity, 400);
  assert.equal(undone.state.profile.plan[0].cookBatchId, undefined);
  assert.equal(undone.state.profile.batches[0].undone, true);
  assert.deepEqual(cooked.state, untouchedCooked);
  const served = run(cooked.state, serve);
  assert.equal(served.state.profile.history[0].intakeKnown, false);
  assert.equal(served.state.profile.history[0].completion, null);
  assert.equal(served.state.profile.history[0].createdAt, clock());
  assert.equal(served.state.profile.batches[0].remaining, 1);
  assert.throws(() => run(served.state, {type: 'undo', planId: 'plan-a'}));
});
test('cook replay repairs missing link once; serving replay does not append undefined history', () => {
  const cooked = run(state(), cook).state;
  delete cooked.profile.plan[0].cookBatchId;
  const repaired = run(cooked, {...cook, mutationId: 'cook-retry'});
  assert.equal(repaired.result.duplicate, true);
  assert.equal(repaired.state.profile.plan[0].cookBatchId, 'cook-a');
  assert.equal(repaired.state.inventory.find(l => l.id === 'lot-rice').quantity, 300);
  assert.equal(repaired.state.profile.batches.length, 1);
  const served = run(repaired.state, serve).state;
  const replay = run(served, serve);
  assert.equal(replay.result.duplicate, true);
  assert.equal(replay.state.profile.history.length, 1);
  assert.deepEqual(replay.state, served);
  assert.throws(() => run(served, {...serve, portions: 2}), /retry differs/);
  served.profile.history = [];
  assert.throws(() => run(served, serve), /history needs reconciliation/);
});
test('editable copy preserves source quantities/provenance and clears active cooked link', () => {
  const cooked = run(state(), cook).state, before = structuredClone(cooked);
  const copy = run(cooked, {type: 'copy', planId: 'plan-a', newPlanId: 'plan-copy', changes: {date: '2026-10-21', servings: 4}});
  assert.deepEqual(cooked, before);
  assert.deepEqual(copy.state.profile.plan[0], before.profile.plan[0]);
  const copied = copy.state.profile.plan[1];
  assert.equal(copied.cookBatchId, undefined);
  assert.equal(copied.servings, 4);
  assert.equal(copied.sourceEvidence.sourceRecipe.ingredients[0].quantity, 100);
  assert.equal(copied.sourceEvidence.sourceRecipe.ingredients[0].sourceQuantity, '100 g');
  assert.equal(copied.sourceEvidence.sourceRecipe.provenance.certainty, null);
  assert.equal(copied.sourceEvidence.sourceRecipe.license, 'unknown');
  assert.equal(copy.result.requiresReview, true);
  assert.equal(planSummary([copied], copy.state.recipes, [], {}, ['2026-10-21']).missing[0].quantity, 200);
  const edited = run(copy.state, {type: 'edit', planId: 'plan-copy', changes: {slot: 'Lunch', servings: 2}});
  assert.deepEqual(edited.state.profile.plan[1].sourceEvidence, copied.sourceEvidence);
  assert.equal(edited.state.profile.plan[1].sourceEvidence.sourcePlan.servings, 2);
  assert.throws(() => run(cooked, {type: 'edit', planId: 'plan-a', changes: {servings: 4}}), /Undo cooking/);
});
test('identity, review, stale stock and invalid edits fail before original state changes', () => {
  const s = state(), before = structuredClone(s);
  for (const action of [
    {...cook, reviewed: false}, {...cook, date: '2026-10-15'}, {...cook, mutationId: ''},
    {type: 'copy', planId: 'plan-a', newPlanId: 'plan-a'},
    {type: 'edit', planId: 'plan-a', changes: {date: '2026-02-30'}},
    {type: 'edit', planId: 'plan-a', changes: {recipeId: 'replacement'}},
    {type: 'edit', planId: 'plan-a', changes: {servings: 0}}
  ]) assert.throws(() => run(s, action));
  assert.deepEqual(s, before);
  const cooked = run(s, cook).state;
  const undone = run(cooked, {type: 'undo', planId: 'plan-a'}).state;
  assert.throws(() => run(undone, cook), /identity already used/);
  assert.throws(() => run(cooked, {...serve, memberId: 'other'}), /outside plan/);
  cooked.inventory.find(l => l.cookBatchId === 'cook-a').quantity = 1;
  assert.throws(() => run(cooked, cook), /reconciliation/);
});
test('generated cooked-lot identity cannot collide with unrelated inventory', () => {
  const s = state();
  s.inventory.push({...structuredClone(s.inventory[0]), id: 'cooked-cook-a', quantity: 25});
  const before = structuredClone(s);
  let clockCalls = 0;
  assert.throws(() => transitionMealPlan19({state: s, action: cook, clock: () => { clockCalls++; return clock(); }}), /Cooked lot identity already used/);
  assert.equal(clockCalls, 0);
  assert.deepEqual(s, before);
});
test('rejects sparse/accessor/custom/cyclic/nonfinite data without invoking getters', () => {
  let hits = 0;
  const getter = state(); Object.defineProperty(getter.profile, 'plan', {enumerable: true, get() { hits++; return []; }});
  assert.throws(() => run(getter, cook)); assert.equal(hits, 0);
  const sparse = state(); sparse.profile.plan = Array(1); assert.throws(() => run(sparse, cook));
  const custom = state(); custom.profile.plan.extra = true; assert.throws(() => run(custom, cook));
  const cyclic = state(); cyclic.profile.self = cyclic; assert.throws(() => run(cyclic, cook));
  const nonfinite = state(); nonfinite.inventory[0].quantity = NaN; assert.throws(() => run(nonfinite, cook));
});
test('owner UI entrypoint exercises actual cooking module through revision-bound commit', async () => {
  let snapshot = {accountId: 'account-a', revision: 'r1', state: state(), preservesPlanEvidence: true};
  let commits = 0;
  const controller = createMealPlanOwner19({read: () => snapshot, scope: () => 'account-a', clock, commit: payload => {
    assert.equal(payload.accountId, 'account-a'); assert.equal(payload.expectedRevision, snapshot.revision);
    snapshot = {...snapshot, revision: 'r' + (++commits + 1), state: payload.state};
    return {committed: true};
  }});
  await controller(cook); await controller(serve); await controller(serve);
  assert.equal(snapshot.state.profile.batches.length, 1);
  assert.equal(snapshot.state.profile.history.length, 1);
  assert.equal(snapshot.state.inventory.find(l => l.id === 'lot-rice').quantity, 300);
});
test('account switch, absent persistence capability and stale revision never commit', async () => {
  let account = 'account-a', commits = 0;
  const snapshot = {accountId: account, revision: 'r1', state: state(), preservesPlanEvidence: true};
  const changed = createMealPlanOwner19({read: () => { account = 'account-b'; return snapshot; }, scope: () => account, clock, commit: () => { commits++; }});
  await assert.rejects(changed(cook), /Account\/revision/); assert.equal(commits, 0);
  account = 'account-a';
  const unavailable = createMealPlanOwner19({read: () => ({...snapshot, preservesPlanEvidence: false}), scope: () => account, clock, commit: () => { commits++; }});
  await assert.rejects(unavailable(cook), /persistence contract unavailable/); assert.equal(commits, 0);
  const stale = createMealPlanOwner19({read: () => snapshot, scope: () => account, clock, commit: () => { throw Error('Stale revision'); }});
  await assert.rejects(stale(cook), /Stale revision/); assert.equal(snapshot.state.profile.batches.length, 0);
});
test('pending operation captures original intent and serializes UI commits', async () => {
  let release, commits = 0;
  const gate = new Promise(resolve => { release = resolve; });
  const controller = createMealPlanOwner19({scope: () => 'account-a', clock,
    read: async () => { await gate; return {accountId: 'account-a', revision: 'r1', state: state(), preservesPlanEvidence: true}; },
    commit: payload => { commits++; assert.equal(payload.state.profile.plan[1].date, '2026-10-21'); return {committed: true}; }
  });
  const action = {type: 'copy', planId: 'plan-a', newPlanId: 'copy', changes: {date: '2026-10-21'}};
  const pending = controller(action); action.changes.date = '2026-11-02';
  await assert.rejects(controller(cook), /already pending/);
  release(); await pending; assert.equal(commits, 1);
});
test('current real cloud validator drops plan source evidence: adoption remains gated', () => {
  const copied = run(state(), {type: 'copy', planId: 'plan-a', newPlanId: 'copy', changes: {date: '2026-10-21'}}).state;
  const validated = validateState(copied);
  assert.ok(copied.profile.plan[1].sourceEvidence);
  assert.equal(validated.profile.plan[1].sourceEvidence, undefined);
});
