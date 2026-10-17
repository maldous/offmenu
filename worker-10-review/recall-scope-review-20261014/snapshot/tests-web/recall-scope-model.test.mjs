import test from 'node:test';
import assert from 'node:assert/strict';
import { matchRecall } from '../public/evidence-model.js';
import { evaluateRecallScope } from '../public/recall-scope-model.js';

const asOf = '2026-10-14T06:00:00Z';
const notice = () => ({
  id: 'synthetic-notice',
  action: { type: 'recall', regulator: 'synthetic-regulator', originalText: 'Synthetic declared recall', url: 'https://regulator.invalid/action' },
  provenance: { sourceId: 'synthetic-source', recordId: 'synthetic-record', url: 'https://regulator.invalid/notice', retrievedAt: '2026-10-14T05:00:00Z', license: 'synthetic-only', attribution: 'Synthetic fixture', transformation: ['reviewed-projection'] },
  evidence: { kind: 'current', validFrom: '2026-10-13T00:00:00Z', freshUntil: '2026-10-15T00:00:00Z' },
  scope: { gtin: '4006381333931', markets: ['AU'], lots: ['A'], labelVersions: ['v1'], dateRange: { field: 'bestBefore', from: '2026-10-01', through: '2026-10-31' } },
});
const lot = () => ({ barcode: '04006381333931', market: 'AU', lotCode: 'A', labelVersion: 'v1', bestBefore: '2026-10-14' });
const evaluate = (n = notice(), l = lot(), clock = asOf) => evaluateRecallScope(n, l, { asOf: clock });

test('legacy matcher already covers known GTIN/market/lot cases; missing market is the actual gap', () => {
  const legacy = { gtin: notice().scope.gtin, market: 'AU', lots: ['A'] };
  assert.equal(matchRecall(legacy, lot()), 'matched');
  assert.equal(matchRecall(legacy, { ...lot(), market: 'NZ' }), 'not-matched');
  assert.equal(matchRecall(legacy, { ...lot(), lotCode: 'B' }), 'not-matched');
  assert.equal(matchRecall(legacy, { ...lot(), lotCode: undefined }), 'possible');
  assert.equal(matchRecall(legacy, { ...lot(), market: undefined }), 'matched');
  assert.equal(evaluate(notice(), { ...lot(), market: undefined }).applicability, 'unknown');
});

test('exact current scoped evidence matches with canonical leading-zero GTIN', () => {
  const result = evaluate();
  assert.equal(result.applicability, 'matched');
  assert.equal(result.evidenceStatus, 'current');
  assert.deepEqual(result.reasons, []);
  assert.equal(result.automaticSelection, false);
});

test('each declared scope dimension independently excludes; exclusions are not a safety pass', () => {
  for (const [field, value, reason] of [
    ['barcode', '96385074', 'gtin'], ['market', 'NZ', 'market'], ['lotCode', 'B', 'lot'],
    ['labelVersion', 'v2', 'label-version'], ['bestBefore', '2026-11-01', 'date'],
  ]) {
    const result = evaluate(notice(), { ...lot(), [field]: value });
    assert.equal(result.applicability, 'not-matched', field);
    assert.ok(result.reasons.includes(`outside-${reason}`));
    assert.equal(result.automaticSelection, false);
  }
});

test('missing scoped identity is unknown, invalid GTIN is never a proven mismatch', () => {
  for (const field of ['barcode', 'market', 'lotCode', 'labelVersion', 'bestBefore']) {
    assert.equal(evaluate(notice(), { ...lot(), [field]: undefined }).applicability, 'unknown', field);
  }
  assert.equal(evaluate(notice(), { ...lot(), barcode: '4006381333932' }).applicability, 'unknown');
  assert.equal(evaluate(notice(), { ...lot(), barcode: 4006381333931 }).applicability, 'unknown');
});

test('all batches bypasses only lot code; market, date and label still constrain', () => {
  const n = notice(); delete n.scope.lots; n.scope.allBatches = true;
  assert.equal(evaluate(n, { ...lot(), lotCode: undefined }).applicability, 'matched');
  for (const field of ['market', 'labelVersion', 'bestBefore']) {
    assert.equal(evaluate(n, { ...lot(), [field]: undefined }).applicability, 'unknown');
  }
  assert.equal(evaluate(n, { ...lot(), bestBefore: '2026-11-01' }).applicability, 'not-matched');
  n.scope.lots = ['A'];
  assert.equal(evaluate(n).applicability, 'unknown');
});

test('date range is inclusive and date types are never substituted', () => {
  for (const value of ['2026-10-01', '2026-10-31']) {
    assert.equal(evaluate(notice(), { ...lot(), bestBefore: value }).applicability, 'matched');
  }
  assert.equal(evaluate(notice(), { ...lot(), bestBefore: '2026-09-30' }).applicability, 'not-matched');
  assert.equal(evaluate(notice(), { ...lot(), bestBefore: undefined, useBy: '2026-10-14' }).applicability, 'unknown');
  for (const field of ['useBy', 'productionDate']) {
    const n = notice(); n.scope.dateRange.field = field;
    assert.equal(evaluate(n, { ...lot(), [field]: '2026-10-14' }).applicability, 'matched');
  }
});

test('malformed or incomplete notice scope remains unknown', () => {
  for (const patch of [
    { gtin: null }, { markets: [] }, { markets: 'AU' }, { markets: {} }, { lots: [] }, { lots: null },
    { labelVersions: [] }, { labelVersions: {} }, { dateRange: null },
    { dateRange: { field: 'expiry', from: '2026-10-01', through: '2026-10-31' } },
    { dateRange: { field: 'bestBefore', from: '2026-11-01', through: '2026-10-31' } },
    { dateRange: { field: 'bestBefore', from: '2026-02-30', through: '2026-10-31' } },
  ]) {
    const n = notice(); Object.assign(n.scope, patch);
    assert.equal(evaluate(n).applicability, 'unknown', JSON.stringify(patch));
  }
  const n = notice(); delete n.scope.lots;
  assert.equal(evaluate(n).applicability, 'unknown');
  assert.equal(evaluate(notice(), { ...lot(), bestBefore: '2026-02-30' }).applicability, 'unknown');
});

test('owner-reviewed unrestricted label/date fields need no invented restriction', () => {
  const n = notice(); delete n.scope.labelVersions; delete n.scope.dateRange;
  assert.equal(evaluate(n, { ...lot(), labelVersion: undefined, bestBefore: undefined }).applicability, 'matched');
});

test('historical scope matches stay historical and never become current applicability', () => {
  const n = notice(); n.evidence.kind = 'historical';
  const result = evaluate(n);
  assert.equal(result.scopeMatch, 'matched');
  assert.equal(result.evidenceStatus, 'historical');
  assert.equal(result.applicability, 'unknown');
  assert.ok(result.reasons.includes('evidence-historical'));
});

test('inspection, noncompliance or undeclared action is not inferred to be a recall', () => {
  for (const action of [undefined, { type: 'inspection', regulator: 'synthetic' }, { type: 'noncompliance', regulator: 'synthetic' }, { type: 'recall' }]) {
    const result = evaluate({ ...notice(), action });
    assert.equal(result.scopeMatch, 'matched');
    assert.equal(result.applicability, 'unknown');
    assert.ok(result.reasons.includes('declared-recall-action-unresolved'));
  }
});

test('missing, stale, future or invalid temporal evidence cannot yield a current match', () => {
  for (const patch of [
    { kind: undefined }, { freshUntil: undefined }, { freshUntil: asOf },
    { validFrom: '2026-10-15T00:00:00Z' }, { validUntil: asOf }, { validUntil: null },
    { validFrom: '2026-02-30T00:00:00Z' }, { freshUntil: 'not-a-date' },
    { freshUntil: '2026-10-14T24:00:00Z' },
  ]) {
    const n = notice(); Object.assign(n.evidence, patch);
    assert.equal(evaluate(n).applicability, 'unknown', JSON.stringify(patch));
  }
  assert.equal(evaluateRecallScope(notice(), lot()).applicability, 'unknown');
  assert.equal(evaluate(notice(), lot(), 'invalid').applicability, 'unknown');
  const n = notice(); n.evidence.validUntil = '2026-10-14T06:00:01Z';
  assert.equal(evaluate(n).applicability, 'matched');
});

test('unresolved provenance, future retrieval or retrieval preceding effective evidence stays unknown', () => {
  for (const field of ['sourceId', 'recordId', 'url', 'retrievedAt']) {
    const n = notice(); delete n.provenance[field];
    assert.equal(evaluate(n).applicability, 'unknown', field);
  }
  for (const retrievedAt of ['2026-10-15T00:00:00Z', '2026-10-12T00:00:00Z']) {
    const n = notice(); n.provenance.retrievedAt = retrievedAt;
    assert.equal(evaluate(n).applicability, 'unknown');
  }
});

test('known exclusion takes precedence over missing scope but claims only this notice', () => {
  const result = evaluate(notice(), { ...lot(), market: 'NZ', lotCode: undefined });
  assert.equal(result.applicability, 'not-matched');
  assert.ok(result.reasons.includes('outside-market'));
  assert.ok(result.reasons.includes('unresolved-lot'));
});

test('inputs stay unchanged and returned provenance/action are independent snapshots', () => {
  const n = notice(), l = lot(), before = structuredClone({ n, l });
  const result = evaluate(n, l);
  assert.deepEqual(result.provenance, n.provenance);
  assert.deepEqual(result.declaredAction, n.action);
  result.provenance.transformation.push('changed-output');
  result.declaredAction.originalText = 'changed-output';
  assert.deepEqual({ n, l }, before);
  assert.equal(evaluateRecallScope(null, null).applicability, 'unknown');
});
