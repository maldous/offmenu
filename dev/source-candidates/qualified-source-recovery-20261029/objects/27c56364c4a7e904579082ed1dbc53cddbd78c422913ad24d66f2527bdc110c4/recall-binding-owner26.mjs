import { admission } from './evidence-model.js';

export const RECALL_HELPER_PIN = '643c130eed6d4d64a7e755d6c233128fa978aaa8';
const present = value => typeof value === 'string' && value.trim().length > 0;
const instant = value => typeof value === 'string'
  && /^\d{4}-\d{2}-\d{2}T(?:[01]\d|2[0-3]):[0-5]\d:[0-5]\d(?:\.\d{1,3})?Z$/.test(value)
  && Number.isFinite(Date.parse(value))
  && new Date(value).toISOString().slice(0, 10) === value.slice(0, 10);

// Owner supplies a reviewed helper dependency and notice projections; no feed-name admission.
export function createRecallConsumer({ evaluateScope, helperPin, independentlyReviewed } = {}) {
  const usable = typeof evaluateScope === 'function' && helperPin === RECALL_HELPER_PIN
    && independentlyReviewed === true;
  return function decideInventoryRecalls({ lots = [], notices = [], asOf } = {}) {
    if (!Array.isArray(lots) || !Array.isArray(notices)) throw new TypeError('Expected inventory and notice arrays');
    return lots.map(lot => {
      const results = notices.map(envelope => {
        const { notice, sourceVersion, recordVersion, policy, assertion, review } = envelope ?? {};
        const unresolved = reason => ({ noticeId: notice?.id ?? null, decision: 'needs-review', reason,
          provenance: structuredClone(notice?.provenance ?? null) });
        if (!usable) return unresolved('reviewed-helper-unavailable');
        if (!instant(asOf)) return unresolved('evaluation-time-unresolved');
        // Bind each assessment to the owner-reviewed source record and selected product/lot.
        const bindings = {
          sourceId: notice?.provenance?.sourceId, sourceVersion,
          recordId: notice?.provenance?.recordId, recordVersion, noticeId: notice?.id,
          productId: lot?.productId, productVersion: lot?.productVersion, lotId: lot?.id,
        };
        if (!review || review.status !== 'accepted' || review.scopeComplete !== true
          || review.conflictFree !== true || !instant(review.checkedAt) || !instant(review.freshUntil)
          || Date.parse(review.checkedAt) > Date.parse(asOf) || Date.parse(asOf) >= Date.parse(review.freshUntil)
          || Object.entries(bindings).some(([key, value]) => !present(value) || review[key] !== value)) {
          return unresolved('source-version-product-lot-review-unresolved');
        }
        if (assertion?.sourceId !== bindings.sourceId || assertion?.recordId !== bindings.recordId
          || assertion?.sourceVersion !== sourceVersion || assertion?.recordVersion !== recordVersion
          || assertion?.status !== 'active' || assertion?.personal !== false
          || policy?.sourceId !== bindings.sourceId || policy?.sourceVersion !== sourceVersion
          || !instant(policy.expiresAt)) return unresolved('source-permission-binding-unresolved');
        const rights = admission(policy, assertion, { action: 'display', audience: 'public',
          market: lot?.market, now: Date.parse(asOf) });
        if (!rights.allowed) return unresolved('source-display-not-permitted');
        const evaluated = evaluateScope(notice, lot, { asOf });
        // Do not treat malformed/custom helper output as a notice exclusion.
        const decision = evaluated?.applicability === 'matched' && evaluated?.evidenceStatus === 'current'
          ? 'recall-match-review' : evaluated?.applicability === 'not-matched'
            ? 'outside-this-notice' : 'needs-review';
        return { noticeId: notice.id, decision, evidence: structuredClone(evaluated) };
      });
      return { lotId: lot?.id ?? null,
        decision: !usable ? 'needs-review' : results.some(r => r.decision === 'recall-match-review')
          ? 'recall-match-review' : results.some(r => r.decision === 'needs-review')
            ? 'needs-review' : 'no-applicable-notice-established',
        safety: 'unknown', exhaustiveCoverage: false, automaticSelection: false, results };
    });
  };
}
