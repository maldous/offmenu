// Isolated decision validator. No data access, release, persistence or grants.
export const RECEIPT_KINDS = Object.freeze([
  'producer', 'lineage', 'rights', 'contribution', 'cohort',
  'composition', 'privacyBudget', 'revocation',
]);
const object = v => v !== null && typeof v === 'object' && !Array.isArray(v);
const text = v => typeof v === 'string' && v.length > 0 && v.length <= 256;
const hash = v => typeof v === 'string' && /^[a-f0-9]{64}$/.test(v);
const positive = v => Number.isSafeInteger(v) && v > 0;
const reject = code => { throw new Error(code); };
function requireThat(value, code) { if (!value) reject(code); }
export const canonicalAggregateJSON = value => JSON.stringify(value, (_, v) =>
  object(v) ? Object.fromEntries(Object.keys(v).sort().map(k => [k, v[k]])) : v);
export async function aggregateDigest(value) {
  return [...new Uint8Array(await crypto.subtle.digest('SHA-256',
    new TextEncoder().encode(value)))].map(v => v.toString(16).padStart(2, '0')).join('');
}
const same = (a, b) => canonicalAggregateJSON(a) === canonicalAggregateJSON(b);
function parse(document) {
  requireThat(typeof document === 'string' && new TextEncoder().encode(document).length <= 65536, 'DOCUMENT_BOUND');
  const value = JSON.parse(document);
  requireThat(object(value), 'DOCUMENT_SHAPE');
  return value;
}
function scopeKey(scope) {
  requireThat(object(scope) && scope.audience === 'private' &&
    ['accountId', 'actorId', 'sessionEpoch', 'purposeId', 'market'].every(k => text(scope[k])) &&
    Object.keys(scope).length === 6, 'PRIVATE_CONTEXT_REQUIRED');
  return canonicalAggregateJSON(scope);
}
function live(doc, now) {
  requireThat(Number.isSafeInteger(doc.validFrom) && doc.validFrom >= 0 &&
    positive(doc.validUntil) && doc.validFrom <= now && now < doc.validUntil, 'RECEIPT_EXPIRED');
}
function bindings(selection) {
  return Object.fromEntries(['querySha256', 'inputSha256', 'outputSha256',
    'contributionSnapshotSha256', 'historySha256', 'producer'].map(k => [k, selection[k]]));
}
function validateEvidence(selection, receipts, context, mode, now) {
  requireThat(selection.format === 'owner59-private-aggregate-selection/1' &&
    scopeKey(selection.scope) === scopeKey(context), 'SELECTION_SCOPE');
  for (const k of ['querySha256', 'inputSha256', 'outputSha256', 'contributionSnapshotSha256', 'historySha256'])
    requireThat(hash(selection[k]), 'EXACT_BINDINGS_REQUIRED');
  const producer = selection.producer;
  requireThat(object(producer) && typeof producer.commit === 'string' && /^[a-f0-9]{40}$/.test(producer.commit) &&
    text(producer.path) && hash(producer.sha256) && text(producer.epoch), 'PRODUCER_PIN_REQUIRED');
  live(selection, now);
  const docs = {};
  for (const row of receipts) {
    const doc = parse(row.document);
    requireThat(doc.format === 'owner59-private-aggregate-receipt/1' &&
      RECEIPT_KINDS.includes(doc.kind) && !docs[doc.kind], 'RECEIPT_KIND');
    requireThat(doc.selectionId === selection.id && doc.selectionRevision === selection.revision &&
      same(doc.scope, context) && same(doc.bindings, bindings(selection)), 'RECEIPT_BINDING');
    requireThat(doc.decision === 'approved' && text(doc.reviewerId) && hash(doc.assessmentSha256), 'REVIEW_REQUIRED');
    requireThat(doc.evidenceClass === (mode === 'synthetic' ? 'synthetic' : 'independently-qualified'), 'EVIDENCE_CLASS');
    live(doc, now); docs[doc.kind] = doc;
  }
  requireThat(RECEIPT_KINDS.every(k => docs[k]), 'MISSING_EVIDENCE');
  requireThat(docs.producer.qualified === true && same(docs.producer.producer, producer), 'PRODUCER_UNQUALIFIED');
  const inputs = docs.lineage.inputs;
  requireThat(docs.lineage.complete === true && Array.isArray(inputs) && inputs.length > 0 && inputs.length <= 128, 'LINEAGE_INCOMPLETE');
  const nodes = new Map();
  for (const input of inputs) {
    requireThat(object(input) && text(input.id) && !nodes.has(input.id) && text(input.sourceId) &&
      positive(input.revision) && hash(input.contentSha256) && Array.isArray(input.dependencies) &&
      input.dependencies.length <= 128 && typeof input.independentRoot === 'boolean', 'LINEAGE_NODE');
    requireThat(input.independentRoot === (input.dependencies.length === 0) &&
      new Set(input.dependencies).size === input.dependencies.length, 'LINEAGE_ROOT');
    live(input, now);
    requireThat(positive(input.freshUntil) && positive(input.retainUntil) &&
      now < input.freshUntil && now < input.retainUntil, 'INPUT_CLOCKS');
    nodes.set(input.id, input);
  }
  const visiting = new Set(), visited = new Set();
  function visit(id) {
    requireThat(nodes.has(id) && !visiting.has(id), 'LINEAGE_CYCLE_OR_MISSING');
    if (visited.has(id)) return;
    visiting.add(id); nodes.get(id).dependencies.forEach(visit);
    visiting.delete(id); visited.add(id);
  }
  inputs.forEach(n => visit(n.id));
  // Rights and contribution attestations must cover every exact input revision.
  for (const kind of ['rights', 'contribution']) {
    const entries = docs[kind].inputs;
    requireThat(Array.isArray(entries) && entries.length === inputs.length, 'INPUT_PERMISSION_COVERAGE');
    const seen = new Set();
    for (const entry of entries) {
      const node = nodes.get(entry?.id);
      requireThat(node && !seen.has(entry.id) && entry.revision === node.revision &&
        entry.contentSha256 === node.contentSha256 && entry.active === true &&
        positive(entry.permissionEpoch) && entry.purposeId === context.purposeId &&
        entry.action === 'private-aggregate' && entry.audience === 'private', 'INPUT_PERMISSION');
      live(entry, now); seen.add(entry.id);
    }
  }
  const cohort = docs.cohort;
  requireThat(['person', 'household'].includes(cohort.unit) && positive(cohort.minimumRequired) &&
    cohort.minimumRequired >= 2 && positive(cohort.minimumObserved) &&
    cohort.minimumObserved >= cohort.minimumRequired && positive(cohort.maxContributionPerUnit) &&
    positive(cohort.observedMaxContribution) && cohort.observedMaxContribution <= cohort.maxContributionPerUnit &&
    hash(cohort.ruleSetSha256) && ['smallCellsReviewed', 'complementsReviewed', 'rareAttributesReviewed']
      .every(k => cohort[k] === true), 'COHORT_REVIEW');
  requireThat(text(docs.composition.ledgerId) && positive(docs.composition.ledgerRevision) &&
    ['intersectionsReviewed', 'differencingReviewed', 'temporalReviewed', 'linkabilityReviewed', 'releaseClosureReviewed']
      .every(k => docs.composition[k] === true), 'COMPOSITION_REVIEW');
  const budget = docs.privacyBudget;
  requireThat(budget.accounting === 'disclosure-composition' && budget.status === 'reserved' &&
    text(budget.reservationId) && text(budget.ledgerId) && positive(budget.ledgerRevision) &&
    budget.ledgerId === docs.composition.ledgerId && budget.ledgerRevision === docs.composition.ledgerRevision &&
    budget.mechanism === 'independently-reviewed-policy' && hash(budget.parametersSha256) &&
    hash(budget.chargeReceiptSha256), 'PRIVACY_BUDGET_REQUIRED');
  const revoke = docs.revocation;
  requireThat(positive(revoke.withdrawalEpoch) && revoke.allInputsCurrent === true &&
    revoke.pendingWithdrawals === false && revoke.dependenciesCurrent === true &&
    revoke.restoreReplayCurrent === true, 'WITHDRAWAL_CURRENT_REQUIRED');
  return Math.min(selection.validUntil, ...Object.values(docs).map(d => d.validUntil),
    ...inputs.flatMap(d => [d.validUntil, d.freshUntil, d.retainUntil]),
    ...docs.rights.inputs.map(d => d.validUntil), ...docs.contribution.inputs.map(d => d.validUntil));
}

/**
 * Trusted capability, NOT request JSON: read() and readIfCurrent() must consult
 * independently authoritative selection/receipt/withdrawal/history/budget rows.
 * readIfCurrent(expected, consume) conditionally reads them together and calls
 * consume(rows) synchronously exactly once iff those exact epochs are current.
 * No store adapter is supplied. Caller must apply a new gate at each operation;
 * this decision is not a lease or authorization for future persistence/release.
 */
export function createPrivateAggregateValidator({authority, getContext, clock, mode = 'unqualified'} = {}) {
  return {async assess(request) {
    try {
      requireThat(['synthetic', 'authoritative'].includes(mode) && typeof authority?.read === 'function' &&
        typeof authority?.readIfCurrent === 'function' && typeof getContext === 'function' &&
        typeof clock === 'function', 'TRUSTED_CAPABILITIES_REQUIRED');
      const selectionId = request?.selectionId;
      requireThat(object(request) && Object.keys(request).length === 1 && text(selectionId), 'OPAQUE_SELECTION_ONLY');
      const context = structuredClone(getContext()), contextStamp = scopeKey(context);
      let last = -1;
      function now() {
        const at = clock();
        requireThat(Number.isSafeInteger(at) && at >= 0 && at >= last, 'CLOCK_REQUIRED');
        last = at; return at;
      }
      function check() { requireThat(scopeKey(getContext()) === contextStamp, 'CONTEXT_CHANGED'); }
      check(); now();
      const snapshot = structuredClone(await authority.read({selectionId, context: structuredClone(context)}));
      check();
      const row = snapshot?.selection, receipts = snapshot?.receipts;
      requireThat(row?.id === selectionId && positive(row.revision) && Array.isArray(receipts) &&
        receipts.length === RECEIPT_KINDS.length, 'AUTHORITATIVE_SNAPSHOT_REQUIRED');
      const selection = parse(row.document);
      requireThat(selection.id === row.id && selection.revision === row.revision &&
        Array.isArray(selection.receiptPins) && selection.receiptPins.length === RECEIPT_KINDS.length, 'SELECTION_REVISION');
      const pinned = new Set();
      for (const receipt of receipts) {
        requireThat(object(receipt) && text(receipt.id) && positive(receipt.revision) && !pinned.has(receipt.id), 'RECEIPT_ID');
        const doc = parse(receipt.document), matches = selection.receiptPins.filter(p => p.id === receipt.id);
        requireThat(matches.length === 1 && matches[0].revision === receipt.revision && matches[0].kind === doc.kind &&
          matches[0].sha256 === await aggregateDigest(receipt.document), 'EXACT_RECEIPT_PIN');
        pinned.add(receipt.id);
      }
      const lineage = receipts.map(r => parse(r.document)).find(d => d.kind === 'lineage');
      requireThat(lineage && await aggregateDigest(canonicalAggregateJSON(lineage.inputs)) ===
        selection.inputSha256, 'INPUT_GRAPH_DIGEST');
      const deadline = validateEvidence(selection, receipts, context, mode, now());
      const expected = {selectionId, revision: row.revision, document: row.document,
        receipts: structuredClone(receipts), context: structuredClone(context)};
      let calls = 0, validated = false, active = true;
      let acknowledgement;
      try {
        acknowledgement = authority.readIfCurrent(expected, rows => {
          requireThat(active && ++calls === 1, 'CONDITIONAL_CALLBACK');
          check();
          requireThat(same(rows, snapshot), 'AUTHORITY_CHANGED');
          validateEvidence(selection, receipts, context, mode, now());
          validated = true; return true;
        });
      } finally { active = false; }
      // Close the synchronous invocation window BEFORE awaiting any adapter ACK.
      const current = await acknowledgement;
      check();
      requireThat(current?.matched === true && calls === 1 && validated, 'CURRENT_GATE_REFUSED');
      requireThat(now() < deadline, 'RECEIPT_EXPIRED');
      return Object.freeze({allowed: mode === 'authoritative', privateEligible: true,
        testOnly: mode === 'synthetic', publicationAllowed: false, selectionId,
        selectionRevision: row.revision, validUntil: deadline,
        reason: mode === 'synthetic' ? 'SYNTHETIC_CONTRACT_ONLY' : 'PRIVATE_CURRENT_DECISION_ONLY'});
    } catch {
      // Never return receipt documents, scope, private data or raw adapter errors.
      return Object.freeze({allowed: false, privateEligible: false, publicationAllowed: false,
        reason: 'MISSING_STALE_OR_UNQUALIFIED_EVIDENCE'});
    }
  }};
}
