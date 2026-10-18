import {cookMeal, serveBatch, undoCook} from './cooking-model.js';

// Inputs must be bounded plain data from the owner's authenticated state boundary.
// Copy descriptors first: accessors, sparse arrays and unsupported values cannot
// invoke hooks while being captured. There is no storage, transport or auth here.
function capture(value) {
  let nodes = 0, characters = 0;
  function visit(v, depth = 0) {
    if (++nodes > 200000 || depth > 30) throw Error('State exceeds capture bounds');
    if (v === null || typeof v === 'boolean') return v;
    if (typeof v === 'number' && Number.isFinite(v)) return v;
    if (typeof v === 'string') {
      characters += v.length;
      if (characters > 2000000) throw Error('State exceeds capture bounds');
      return v;
    }
    if (!v || typeof v !== 'object') throw Error('Plain data required');
    const array = Array.isArray(v), proto = Object.getPrototypeOf(v);
    if (proto !== (array ? Array.prototype : Object.prototype) && !(proto === null && !array)) throw Error('Plain data required');
    const descriptors = Object.getOwnPropertyDescriptors(v);
    if (Object.getOwnPropertySymbols(v).length) throw Error('Plain data required');
    if (array && v.length > 10000) throw Error('Array exceeds bounds');
    const keys = Object.keys(descriptors);
    if (array && keys.length !== v.length + 1) throw Error('Dense arrays required');
    const out = array ? [] : {};
    for (const key of keys) {
      if (array && key === 'length') continue;
      if (['__proto__', 'constructor', 'prototype'].includes(key)) throw Error('Unsafe data key');
      if (array && !/^(0|[1-9]\d*)$/.test(key)) throw Error('Plain arrays required');
      const d = descriptors[key];
      if (!Object.hasOwn(d, 'value') || !d.enumerable) throw Error('Plain data required');
      out[key] = visit(d.value, depth + 1);
    }
    return out;
  }
  return visit(value);
}
const identifier = v => typeof v === 'string' && v.length > 0 && v.length <= 100;
function requireId(v) { if (!identifier(v)) throw Error('Invalid identity'); }
function date(v) {
  if (typeof v !== 'string' || !/^\d{4}-\d{2}-\d{2}$/.test(v)) throw Error('Invalid date');
  const time = Date.parse(v + 'T12:00:00Z');
  if (!Number.isFinite(time) || new Date(time).toISOString().slice(0, 10) !== v) throw Error('Invalid date');
}
function planEntry(p) {
  requireId(p.id); requireId(p.recipeId); date(p.date);
  if (!['Breakfast', 'Lunch', 'Dinner', 'Snack'].includes(p.slot) || !Number.isFinite(p.servings) || p.servings <= 0) throw Error('Invalid plan');
  if (p.memberIds !== undefined && (!Array.isArray(p.memberIds) || p.memberIds.length > 100 || p.memberIds.some(v => !identifier(v)) || new Set(p.memberIds).size !== p.memberIds.length)) throw Error('Invalid attendees');
}
function unique(rows) {
  if (!Array.isArray(rows) || rows.length > 10000 || rows.some(x => !x || !identifier(x.id)) || new Set(rows.map(x => x.id)).size !== rows.length) throw Error('Duplicate or invalid identities');
}
function timestamp(clock) {
  const result = clock();
  if (typeof result !== 'string' || !Number.isFinite(Date.parse(result))) throw Error('Invalid clock');
  return result;
}
function edit(entry, changes) {
  if (!changes || Array.isArray(changes) || Object.keys(changes).some(k => !['date', 'slot', 'servings', 'memberIds', 'adjustments'].includes(k))) throw Error('Unsupported plan edit');
  const next = {...entry, ...changes};
  planEntry(next);
  if (next.adjustments !== undefined && (!Array.isArray(next.adjustments) || next.adjustments.length > 100 || next.adjustments.some(v => typeof v !== 'string' || v.length > 1000))) throw Error('Invalid adjustments');
  return next;
}
function stockMatches(state, batch) {
  const remaining = state.inventory.filter(l => l.cookBatchId === batch.id).reduce((sum, l) => sum + l.quantity, 0);
  if (!Number.isFinite(batch.remaining) || Math.abs(remaining - batch.remaining) > 1e-7) throw Error('Cooked stock needs reconciliation');
}

/** Pure transition on real app state; original state, recipes and plans survive.
 * Actions: copy, edit, cook, serve, undo. Review is caller-confirmed for the exact
 * current revision; it is never a diet, rights or food-safety qualification.
 */
export function transitionMealPlan19({state, action, clock = () => new Date().toISOString()}) {
  const next = capture(state), request = capture(action);
  if (!next.profile || !Array.isArray(next.inventory) || !Array.isArray(next.recipes) || !next.products) throw Error('Invalid app state');
  const profile = next.profile;
  const plans = profile.plan ?? [], batches = profile.batches ?? [], history = profile.history ?? [];
  unique(plans); unique(batches); unique(history); unique(next.inventory);
  for (const p of plans) planEntry(p);
  requireId(request.planId);
  const entry = plans.find(p => p.id === request.planId);
  if (!entry) throw Error('Plan no longer exists');
  const recipe = next.recipes.find(r => r.id === entry.recipeId);
  const active = batches.find(b => b.planId === entry.id && !b.undone);
  const linked = entry.cookBatchId && batches.find(b => b.id === entry.cookBatchId && !b.undone);
  if (entry.cookBatchId && (!linked || linked.planId !== entry.id) || batches.filter(b => b.planId === entry.id && !b.undone).length > 1) throw Error('Plan batch link needs reconciliation');
  const replacePlan = p => { profile.plan = plans.map(x => x.id === p.id ? p : x); };
  if (request.type === 'copy') {
    requireId(request.newPlanId);
    if (plans.length >= 10000 || plans.some(p => p.id === request.newPlanId)) throw Error('Plan identity collision or capacity');
    if (!recipe) throw Error('Recipe no longer exists');
    const copied = edit({...entry, id: request.newPlanId}, request.changes ?? {});
    delete copied.cookBatchId;
    // Preserve old evidence; capture publisher quantities, units, uncertainty,
    // licence and provenance without converting, rewriting or admitting them.
    copied.sourceEvidence = entry.sourceEvidence ?? {sourcePlanId: entry.id, sourcePlan: capture(entry), sourceRecipe: capture(recipe)};
    profile.plan = [...plans, copied];
    return {state: next, result: {type: 'copy', planId: copied.id, requiresReview: true}};
  }
  if (request.type === 'edit') {
    if (active || linked) throw Error('Undo cooking before editing this plan');
    replacePlan(edit(entry, request.changes));
    return {state: next, result: {type: 'edit', planId: entry.id, requiresReview: true}};
  }
  if (request.type === 'cook') {
    if (request.reviewed !== true) throw Error('Current plan and packages need review');
    if (!recipe) throw Error('Recipe no longer exists');
    requireId(request.mutationId); date(request.date);
    if (request.date !== entry.date) throw Error('Review a date edit before cooking');
    const collision = batches.find(b => b.id === request.mutationId);
    if (collision && (collision.undone || collision.planId !== entry.id)) throw Error('Cooking identity already used');
    if (!active && next.inventory.some(l => l.id === 'cooked-' + request.mutationId)) throw Error('Cooked lot identity already used');
    if (active && (active.recipeId !== entry.recipeId || active.servings !== entry.servings || active.date !== entry.date)) throw Error('Existing batch differs from plan');
    if (active) stockMatches(next, active);
    const cooked = cookMeal({recipe, inventory: next.inventory, products: next.products, servings: entry.servings, date: request.date, planId: entry.id, batches, mutationId: request.mutationId});
    unique(cooked.inventory); // Verify generated output before any owner commit.
    next.inventory = cooked.inventory;
    profile.batches = cooked.duplicate ? batches : [...batches, {...cooked.batch, createdAt: timestamp(clock), sourceEvidence: {sourcePlan: capture(entry), sourceRecipe: capture(recipe)}}];
    replacePlan({...entry, cookBatchId: cooked.batch.id}); // Also repairs duplicate-cook link.
    return {state: next, result: {type: 'cook', batchId: cooked.batch.id, duplicate: cooked.duplicate}};
  }
  if (request.type === 'serve' || request.type === 'undo') {
    const batch = linked ?? active;
    if (!batch) throw Error('No active cooked batch for plan');
    stockMatches(next, batch);
    if (request.type === 'undo') {
      next.inventory = undoCook(batch, next.inventory);
      profile.batches = batches.map(b => b.id === batch.id ? {...b, undone: true} : b);
      profile.plan = plans.map(p => {
        if (p.cookBatchId !== batch.id) return p;
        const cleared = {...p}; delete cleared.cookBatchId; return cleared;
      });
      return {state: next, result: {type: 'undo', batchId: batch.id}};
    }
    requireId(request.eventId); date(request.date);
    if (request.memberId && !entry.memberIds?.includes(request.memberId)) throw Error('Member is outside plan attendance');
    const priorLog = history.find(h => h.id === request.eventId);
    if (priorLog && priorLog.batchId !== batch.id) throw Error('Serving identity already used');
    if (priorLog && (priorLog.servedPortions !== request.portions || priorLog.completion !== (request.completion ?? null) || priorLog.date !== request.date || priorLog.slot !== entry.slot || priorLog.memberId !== (request.memberId ?? '') || priorLog.leftovers !== (request.remainder ?? 'unspecified'))) throw Error('Serving retry differs from recorded event');
    const served = serveBatch({batch, inventory: next.inventory, portions: request.portions, completion: request.completion ?? null, remainder: request.remainder ?? 'unspecified', memberId: request.memberId ?? '', date: request.date, slot: entry.slot, eventId: request.eventId});
    if (served.duplicate) {
      if (!priorLog) throw Error('Serving history needs reconciliation');
      return {state: next, result: {type: 'serve', duplicate: true, batchId: batch.id}};
    }
    if (priorLog) throw Error('Serving history needs reconciliation');
    if (history.length >= 10000) throw Error('History exceeds bounds');
    next.inventory = served.inventory;
    profile.batches = batches.map(b => b.id === batch.id ? served.batch : b);
    profile.history = [...history, {...served.log, createdAt: timestamp(clock)}];
    replacePlan({...entry, cookBatchId: batch.id});
    return {state: next, result: {type: 'serve', duplicate: false, batchId: batch.id}};
  }
  throw Error('Unsupported plan action');
}

/** Owner03/UI entrypoint; Owner04 supplies account+revision-bound atomic commit.
 * read() -> {accountId, revision, state, preservesPlanEvidence: true}
 * commit({accountId, expectedRevision, state}) must reject stale/account-switched
 * state at the actual write and return {committed:true}; no split persistence.
 */
export function createMealPlanOwner19({read, commit, scope, clock}) {
  if (![read, commit, scope, clock].every(f => typeof f === 'function')) throw Error('Owner state boundary required');
  let busy = false;
  return async action => {
    if (busy) throw Error('Plan operation already pending');
    busy = true;
    try {
      const request = capture(action); // Capture intent before any asynchronous read.
      const accountId = scope(); requireId(accountId);
      const snapshot = capture(await read());
      if (snapshot.accountId !== accountId || scope() !== accountId || !identifier(snapshot.revision)) throw Error('Account/revision changed');
      if (snapshot.preservesPlanEvidence !== true) throw Error('Plan evidence persistence contract unavailable');
      const result = transitionMealPlan19({state: snapshot.state, action: request, clock});
      if (scope() !== accountId) throw Error('Account changed before commit');
      const saved = await commit({accountId, expectedRevision: snapshot.revision, state: result.state});
      if (saved?.committed !== true) throw Error('Plan commit not confirmed');
      return result.result;
    } finally { busy = false; }
  };
}
