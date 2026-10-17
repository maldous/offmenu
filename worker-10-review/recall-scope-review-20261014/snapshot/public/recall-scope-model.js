import { canonicalGTIN } from './evidence-model.js';

const text = value => typeof value === 'string' && value.trim().length > 0;
const list = value => Array.isArray(value) && value.length > 0 && value.every(text);
const day = value => typeof value === 'string' && /^\d{4}-\d{2}-\d{2}$/.test(value)
  && Number.isFinite(Date.parse(value)) && new Date(value).toISOString().slice(0, 10) === value;
const instant = value => typeof value === 'string'
  && /^\d{4}-\d{2}-\d{2}T(?:[01]\d|2[0-3]):[0-5]\d:[0-5]\d(?:\.\d+)?Z$/.test(value)
  && day(value.slice(0, 10)) && Number.isFinite(Date.parse(value));
const dateFields = new Set(['useBy', 'bestBefore', 'productionDate']);

// Evaluate an owner-reviewed projection, never raw provider data or a legal/safety rule.
// Omitting an optional label/date restriction means the owner established no such restriction.
export function evaluateRecallScope(notice = {}, lot = {}, { asOf } = {}) {
  notice ??= {};
  lot ??= {};
  const reasons = [];
  const unknown = [];
  const excluded = [];
  const compare = (dimension, valid, known, matches) => {
    if (!valid || !known) unknown.push(dimension);
    else if (!matches) excluded.push(dimension);
  };
  const scope = notice.scope ?? {};
  const gtin = typeof scope.gtin === 'string' ? canonicalGTIN(scope.gtin) : null;
  const barcode = typeof lot.barcode === 'string' ? canonicalGTIN(lot.barcode) : null;
  compare('gtin', !!gtin, !!barcode, gtin === barcode);
  compare('market', list(scope.markets), text(lot.market),
    list(scope.markets) && scope.markets.includes(lot.market));

  const hasLots = Object.hasOwn(scope, 'lots');
  const allBatches = scope.allBatches === true;
  if (allBatches && !hasLots) {
    // All batches bypasses only the lot-code dimension, never market/label/date gates.
  } else if (!allBatches && list(scope.lots) && [false, undefined].includes(scope.allBatches)) {
    compare('lot', true, text(lot.lotCode), scope.lots.includes(lot.lotCode));
  } else unknown.push('lot-scope');

  if (Object.hasOwn(scope, 'labelVersions')) {
    compare('label-version', list(scope.labelVersions), text(lot.labelVersion),
      list(scope.labelVersions) && scope.labelVersions.includes(lot.labelVersion));
  }
  if (Object.hasOwn(scope, 'dateRange')) {
    const range = scope.dateRange ?? {};
    const valid = dateFields.has(range.field) && day(range.from) && day(range.through)
      && range.from <= range.through;
    const value = lot[range.field];
    compare('date', valid, day(value), value >= range.from && value <= range.through);
  }

  const provenance = notice.provenance ?? {};
  const backed = text(provenance.sourceId) && text(provenance.recordId)
    && text(provenance.url) && instant(provenance.retrievedAt)
    && instant(asOf) && Date.parse(provenance.retrievedAt) <= Date.parse(asOf);
  const evidence = notice.evidence ?? {};
  let evidenceStatus = 'unknown';
  if (evidence.kind === 'historical') evidenceStatus = 'historical';
  else if (evidence.kind === 'current' && backed && instant(evidence.validFrom)
    && instant(evidence.freshUntil) && Date.parse(evidence.validFrom) <= Date.parse(asOf)
    && Date.parse(evidence.validFrom) <= Date.parse(provenance.retrievedAt)
    && Date.parse(provenance.retrievedAt) < Date.parse(evidence.freshUntil)
    && Date.parse(asOf) < Date.parse(evidence.freshUntil)
    && (!Object.hasOwn(evidence, 'validUntil') || (instant(evidence.validUntil)
      && Date.parse(evidence.validFrom) < Date.parse(evidence.validUntil)
      && Date.parse(asOf) < Date.parse(evidence.validUntil)))) evidenceStatus = 'current';
  if (!backed) reasons.push('source-provenance-unresolved');
  if (evidenceStatus !== 'current') reasons.push(`evidence-${evidenceStatus}`);
  const declaredRecall = notice.action?.type === 'recall' && text(notice.action.regulator);
  if (!declaredRecall) reasons.push('declared-recall-action-unresolved');
  reasons.push(...excluded.map(d => `outside-${d}`), ...unknown.map(d => `unresolved-${d}`));
  const scopeMatch = excluded.length ? 'not-matched' : unknown.length ? 'unknown' : 'matched';
  const applicability = scopeMatch === 'not-matched' ? 'not-matched'
    : scopeMatch === 'matched' && backed && declaredRecall && evidenceStatus === 'current'
      ? 'matched' : 'unknown';
  return {
    noticeId: notice.id ?? null,
    applicability,
    scopeMatch,
    evidenceStatus,
    reasons,
    provenance: structuredClone(notice.provenance ?? null),
    declaredAction: structuredClone(notice.action ?? null),
    automaticSelection: false,
  };
}
