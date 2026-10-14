import test from 'node:test';
import assert from 'node:assert/strict';
import {createPrivateAggregateValidator, RECEIPT_KINDS, aggregateDigest, canonicalAggregateJSON} from '../public/private-aggregate-admission-owner59.js';

// Fabricated, isolated capability; no real producer, user, DB or rights grant.
async function fixture() {
  const h = 'a'.repeat(64), scope = {accountId: 'synthetic-account', actorId: 'synthetic-actor',
    sessionEpoch: 'session-1', purposeId: 'synthetic-private-purpose', market: 'AU', audience: 'private'};
  const producer = {commit: 'a'.repeat(40), path: 'synthetic/producer.js', sha256: h, epoch: 'producer-1'};
  const bindings = {querySha256: h, inputSha256: h, outputSha256: h,
    contributionSnapshotSha256: h, historySha256: h, producer};
  const selection = {format: 'owner59-private-aggregate-selection/1', id: 'synthetic-selection',
    revision: 1, scope, ...bindings, validFrom: 0, validUntil: 5000, receiptPins: []};
  const input = {id: 'input-1', sourceId: 'synthetic-source', revision: 1,
    contentSha256: h, dependencies: [], independentRoot: true,
    validFrom: 0, validUntil: 5000, freshUntil: 5000, retainUntil: 5000};
  const permission = {id: input.id, revision: input.revision, contentSha256: h,
    active: true, permissionEpoch: 1, purposeId: scope.purposeId, action: 'private-aggregate',
    audience: 'private', validFrom: 0, validUntil: 5000};
  const evidence = {
    producer: {qualified: true, producer},
    lineage: {complete: true, inputs: [input]},
    rights: {inputs: [permission]}, contribution: {inputs: [structuredClone(permission)]},
    cohort: {unit: 'household', minimumRequired: 5, minimumObserved: 6,
      maxContributionPerUnit: 2, observedMaxContribution: 1, ruleSetSha256: h,
      smallCellsReviewed: true, complementsReviewed: true, rareAttributesReviewed: true},
    composition: {ledgerId: 'synthetic-ledger', ledgerRevision: 1, intersectionsReviewed: true, differencingReviewed: true,
      temporalReviewed: true, linkabilityReviewed: true, releaseClosureReviewed: true},
    privacyBudget: {accounting: 'disclosure-composition', status: 'reserved', reservationId: 'synthetic-reservation',
      ledgerId: 'synthetic-ledger', ledgerRevision: 1, mechanism: 'independently-reviewed-policy',
      parametersSha256: h, chargeReceiptSha256: h},
    revocation: {withdrawalEpoch: 1, allInputsCurrent: true, pendingWithdrawals: false,
      dependenciesCurrent: true, restoreReplayCurrent: true},
  };
  const docs = Object.fromEntries(RECEIPT_KINDS.map(kind => [kind, {
    format: 'owner59-private-aggregate-receipt/1', kind, selectionId: selection.id,
    selectionRevision: 1, scope, bindings, decision: 'approved', reviewerId: 'synthetic-reviewer',
    assessmentSha256: h, evidenceClass: 'synthetic', validFrom: 0, validUntil: 5000, ...evidence[kind],
  }]));
  let snapshot, at = 1000, context = structuredClone(scope), gate = null, readHook = null;
  async function seal() {
    bindings.inputSha256 = selection.inputSha256 = await aggregateDigest(canonicalAggregateJSON(docs.lineage.inputs));
    const receipts = RECEIPT_KINDS.map(kind => ({id: 'receipt-' + kind, revision: 1, document: JSON.stringify(docs[kind])}));
    selection.receiptPins = await Promise.all(receipts.map(async (r, i) => ({id: r.id,
      kind: RECEIPT_KINDS[i], revision: r.revision, sha256: await aggregateDigest(r.document)})));
    snapshot = {selection: {id: selection.id, revision: selection.revision, document: JSON.stringify(selection)}, receipts};
  }
  await seal();
  const authority = {
    async read() { if (readHook) return readHook(snapshot); return structuredClone(snapshot); },
    async readIfCurrent(expected, consume) {
      if (gate) return gate(expected, consume, snapshot);
      return {matched: true, value: consume(structuredClone(snapshot))};
    },
  };
  const options = {authority, getContext: () => context, clock: () => at, mode: 'synthetic'};
  return {docs, selection, options, seal, request: {selectionId: selection.id},
    setTime: v => { at = v; }, setContext: v => { context = v; },
    setGate: fn => { gate = fn; }, setRead: fn => { readHook = fn; },
    getSnapshot: () => snapshot, evaluate: () => createPrivateAggregateValidator(options).assess({selectionId: selection.id})};
}
const denied = result => { assert.equal(result.allowed, false); assert.equal(result.privateEligible, false); assert.equal(result.publicationAllowed, false); };

test('complete synthetic receipts exercise the contract but never grant real admission or publication', async () => {
  const f = await fixture(), result = await f.evaluate();
  assert.equal(result.privateEligible, true); assert.equal(result.testOnly, true);
  assert.equal(result.allowed, false); assert.equal(result.publicationAllowed, false);
  assert.equal(result.validUntil, 5000); assert.ok(Object.isFrozen(result));
});
test('unqualified capabilities and synthetic receipts in authoritative mode deny', async () => {
  denied(await createPrivateAggregateValidator().assess({selectionId: 'x'}));
  const f = await fixture(); denied(await createPrivateAggregateValidator({...f.options, mode: 'authoritative'}).assess(f.request));
});
test('public audiences and client-supplied evidence/authority deny', async () => {
  const f = await fixture(); denied(await createPrivateAggregateValidator(f.options).assess({...f.request, receipts: []}));
  f.setContext({...f.selection.scope, audience: 'public'}); denied(await f.evaluate());
});
for (const kind of RECEIPT_KINDS) test(`missing or unreviewed ${kind} denies`, async () => {
  const f = await fixture(); f.docs[kind].decision = 'unknown'; await f.seal(); denied(await f.evaluate());
  f.docs[kind].decision = 'approved'; await f.seal(); f.getSnapshot().receipts.pop(); denied(await f.evaluate());
});
test('unqualified producer, changed output/history/source pins, receipt bytes and selection revision deny', async () => {
  for (const mutate of [f => { f.docs.producer.qualified = false; },
    f => { f.docs.cohort.bindings = {...f.docs.cohort.bindings, outputSha256: 'b'.repeat(64)}; },
    f => { f.docs.composition.bindings = {...f.docs.composition.bindings, historySha256: 'b'.repeat(64)}; },
    f => { f.docs.rights.inputs[0].contentSha256 = 'b'.repeat(64); },
    f => { f.selection.producer.commit = 'develop'; },
    f => { f.selection.producer.commit = ['a'.repeat(40)]; },
    f => { f.docs.producer.selectionRevision = 2; }]) {
    const f = await fixture(); mutate(f); await f.seal(); denied(await f.evaluate());
  }
  const f = await fixture(); f.getSnapshot().receipts[0].document += ' '; denied(await f.evaluate());
});
test('missing dependencies, cycles, duplicate identities and implicit independent roots deny', async () => {
  for (const change of [n => {n.dependencies = ['missing']; n.independentRoot = false;},
    n => {n.dependencies = [n.id]; n.independentRoot = false;}, n => {n.independentRoot = undefined;}]) {
    const f = await fixture(); change(f.docs.lineage.inputs[0]); await f.seal(); denied(await f.evaluate());
  }
  const f = await fixture(); f.docs.lineage.inputs.push(structuredClone(f.docs.lineage.inputs[0])); await f.seal(); denied(await f.evaluate());
});
test('input graph digest and all three input clocks are bound and fail closed', async () => {
  for (const key of ['validUntil', 'freshUntil', 'retainUntil']) {
    const f = await fixture(); f.docs.lineage.inputs[0][key] = 1000; await f.seal(); denied(await f.evaluate());
  }
  const f = await fixture();
  const row = f.getSnapshot().receipts.find(r => JSON.parse(r.document).kind === 'lineage');
  const doc = JSON.parse(row.document); doc.inputs[0].sourceId = 'substituted-source'; row.document = JSON.stringify(doc);
  const selected = JSON.parse(f.getSnapshot().selection.document);
  selected.receiptPins.find(p => p.kind === 'lineage').sha256 = await aggregateDigest(row.document);
  f.getSnapshot().selection.document = JSON.stringify(selected);
  denied(await f.evaluate());
});
test('small groups, excess contributions, rare attributes and complementary suppression need receipts', async () => {
  for (const [key, value] of [['minimumObserved', 1], ['minimumRequired', 1], ['observedMaxContribution', 100],
    ['rareAttributesReviewed', false], ['complementsReviewed', false], ['smallCellsReviewed', false]]) {
    const f = await fixture(); f.docs.cohort[key] = value; await f.seal(); denied(await f.evaluate());
  }
});
test('intersections, differencing, temporal change, linkage and release closure each deny when unreviewed', async () => {
  for (const key of ['intersectionsReviewed', 'differencingReviewed', 'temporalReviewed', 'linkabilityReviewed', 'releaseClosureReviewed']) {
    const f = await fixture(); f.docs.composition[key] = false; await f.seal(); denied(await f.evaluate());
  }
});
test('provider quota, exhausted/unreserved privacy ledger or unknown mechanism cannot substitute', async () => {
  for (const [key, value] of [['accounting', 'provider-requests'], ['status', 'exhausted'],
    ['status', 'unknown'], ['ledgerRevision', 0], ['ledgerRevision', 2], ['ledgerId', 'another-ledger'],
    ['mechanism', 'unspecified-DP'], ['chargeReceiptSha256', '']]) {
    const f = await fixture(); f.docs.privacyBudget[key] = value; await f.seal(); denied(await f.evaluate());
  }
});
test('withdrawal, restore and input rights changes deny even with otherwise reviewed cohort', async () => {
  for (const [kind, key, value] of [['revocation', 'pendingWithdrawals', true], ['revocation', 'restoreReplayCurrent', false],
    ['revocation', 'allInputsCurrent', false], ['revocation', 'dependenciesCurrent', false]]) {
    const f = await fixture(); f.docs[kind][key] = value; await f.seal(); denied(await f.evaluate());
  }
  for (const kind of ['rights', 'contribution']) {
    const f = await fixture(); f.docs[kind].inputs[0].active = false; await f.seal(); denied(await f.evaluate());
  }
});
test('exact current authority snapshot, receipt revision and account/purpose/session are rechecked', async () => {
  for (const change of [s => {s.receipts[0].revision++;}, s => {s.selection.document += ' ';}]) {
    const f = await fixture(); f.setGate((expected, consume, snapshot) => {
      const current = structuredClone(snapshot); change(current); return {matched: true, value: consume(current)};
    }); denied(await f.evaluate());
  }
  const f = await fixture(); f.setGate((expected, consume, snapshot) => {
    f.setContext({...f.selection.scope, sessionEpoch: 'switched'}); return {matched: true, value: consume(snapshot)};
  }); denied(await f.evaluate());
});
test('withdrawal after snapshot read but before final gate denies; no retained decision is a future lease', async () => {
  const f = await fixture(); f.setGate(() => ({matched: false})); denied(await f.evaluate());
});
test('expiry in every receipt, per-input permission and while final acknowledgement awaits denies', async () => {
  for (const kind of RECEIPT_KINDS) {
    const f = await fixture(); f.docs[kind].validUntil = 1000; await f.seal(); denied(await f.evaluate());
  }
  for (const kind of ['rights', 'contribution']) {
    const f = await fixture(); f.docs[kind].inputs[0].validUntil = 1000; await f.seal(); denied(await f.evaluate());
  }
  const f = await fixture(); f.setGate(async (expected, consume, snapshot) => {
    const value = consume(snapshot); await Promise.resolve(); f.setTime(5000); return {matched: true, value};
  }); denied(await f.evaluate());
});
test('clock regression, missing/repeated callbacks, async grants and raw error contents deny', async () => {
  const gates = [() => ({matched: true}), (e, c, s) => {c(s); return {matched: true, value: c(s)};},
    () => ({matched: Promise.resolve(true)}), () => {throw Error('synthetic-private-record-DO-NOT-RETURN');}];
  for (const gate of gates) {const f = await fixture(); f.setGate(gate); const r = await f.evaluate(); denied(r); assert.ok(!JSON.stringify(r).includes('DO-NOT-RETURN'));}
  const f = await fixture(); f.setGate((e, c, s) => {f.setTime(999); return {matched: true, value: c(s)};}); denied(await f.evaluate());
});
test('mutation of detached expected receipts cannot rewrite captured authority', async () => {
  const f = await fixture(); f.setGate((expected, consume, snapshot) => {
    expected.receipts[0].document = '{}'; expected.context.purposeId = 'changed';
    return {matched: true, value: consume(structuredClone(snapshot))};
  }); assert.equal((await f.evaluate()).privateEligible, true);
});
test('malformed, oversized, future and unknown evidence never becomes a default approval', async () => {
  for (const value of ['{broken', ' '.repeat(65537)]) {
    const f = await fixture(); f.getSnapshot().selection.document = value; denied(await f.evaluate());
  }
  for (const mutate of [f => {f.docs.cohort.minimumObserved = null;},
    f => {f.docs.rights.validFrom = 1001;}, f => {f.docs.rights.validUntil = null;},
    f => {f.docs.composition.differencingReviewed = 'true';},
    f => {f.docs.revocation.evidenceClass = 'independently-qualified';}]) {
    const f = await fixture(); mutate(f); await f.seal(); denied(await f.evaluate());
  }
  const f = await fixture(); f.setTime(NaN); denied(await f.evaluate());
});
test('consume deferred until after readIfCurrent invocation is refused', async () => {
  for (const mode of ['authoritative', 'synthetic']) for (const defer of [() => Promise.resolve(), () => new Promise(resolve => setImmediate(resolve))]) {
    const f = await fixture();
    // Fabricated qualification labels test the boundary, not real evidence.
    f.options.mode = mode;
    if (mode === 'authoritative') {
      for (const doc of Object.values(f.docs)) doc.evidenceClass = 'independently-qualified';
      await f.seal();
    }
    f.setGate(async (expected, consume, snapshot) => {
      await defer();
      return {matched: true, value: consume(snapshot)};
    });
    denied(await f.evaluate());
  }
});
