import {ownershipPath} from '../public/evidence-model.js';

const roles = new Set(['company', 'brand', 'site', 'product']);
const relations = new Set(['control', 'accounting-parent', 'minority', 'operating-brand', 'site-operator', 'franchise', 'licence']);
const text = x => typeof x === 'string' && x.trim().length > 0;
const key = ref => ref && text(ref.sourceId) && text(ref.recordId) ? JSON.stringify([ref.sourceId, ref.recordId]) : null;
const date = x => typeof x === 'string' && /^\d{4}-\d{2}-\d{2}$/.test(x)
  && Number.isFinite(Date.parse(x)) && new Date(Date.parse(x)).toISOString().slice(0, 10) === x;
const current = (row, now) => row.status === 'active' && date(row.validFrom) && Date.parse(row.validFrom) <= now
  && date(row.freshUntil) && Date.parse(row.freshUntil) > now
  && (row.validUntil === undefined || date(row.validUntil) && Date.parse(row.validUntil) > now);

// Input is an owner-reviewed source projection, never discovery CSV metadata.
// This pure boundary performs no reads, persistence, account lookup or source admission.
export function evaluateBusinessIdentity(projection, {subject, target, now, jurisdiction, market, includeMinority = false} = {}) {
  const minorityOptIn = includeMinority === true;
  const unknown = reason => ({status: 'unknown', path: [], reason});
  const errors = [], crosswalk = [], evidence = [];
  const result = ownership => ({ownership, crosswalk, evidence, errors});
  if (!projection || !Array.isArray(projection.identities) || !Array.isArray(projection.relationships)
    || projection.identities.length > 1000 || projection.relationships.length > 1000
    || !Number.isFinite(now) || !text(jurisdiction) || !text(market)) return result(unknown('Bounded projection, time and explicit jurisdiction/market required'));
  const usable = row => row && row.personal !== true && row.matchStatus === 'verified'
    && row.reviewStatus === 'admitted' && text(row.rightsRevision) && text(row.sourceRecordId)
    && row.jurisdiction === jurisdiction && row.market === market && current(row, now);
  const aliases = new Map(), canonicalRoles = new Map();
  for (const row of projection.identities) {
    if (!usable(row) || !key(row) || !roles.has(row.role) || !text(row.canonicalId)) {
      errors.push({id: row?.sourceRecordId ?? null, reason: 'Identity mapping not current/admitted/typed'}); continue;
    }
    const alias = key(row);
    if (!aliases.has(alias)) aliases.set(alias, []);
    aliases.get(alias).push(row);
    if (!canonicalRoles.has(row.canonicalId)) canonicalRoles.set(row.canonicalId, new Set());
    canonicalRoles.get(row.canonicalId).add(row.role);
  }
  const resolve = ref => {
    const rows = aliases.get(key(ref)) || [];
    if (!rows.length || new Set(rows.map(row => row.canonicalId)).size !== 1
      || canonicalRoles.get(rows[0].canonicalId).size !== 1) return null;
    return rows[0];
  };
  for (const rows of aliases.values()) {
    if (resolve(rows[0])) crosswalk.push({source: {sourceId: rows[0].sourceId, recordId: rows[0].recordId},
      canonicalId: rows[0].canonicalId, role: rows[0].role, evidence: rows});
    else errors.push({id: rows[0].sourceRecordId, reason: 'Ambiguous alias or conflicting canonical role'});
  }
  const counts = new Map();
  for (const row of projection.relationships) if (row && text(row.id)) counts.set(row.id, (counts.get(row.id) || 0) + 1);
  for (const row of projection.relationships) {
    const from = resolve(row?.subject), to = resolve(row?.object);
    if (!usable(row) || !text(row.sourceId) || !text(row.id) || counts.get(row.id) !== 1 || !from || !to || !relations.has(row.predicate)) {
      errors.push({id: row?.id ?? null, reason: 'Relationship not current/admitted or endpoints unresolved'}); continue;
    }
    const typed = row.predicate === 'operating-brand' ? from.role === 'company' && to.role === 'brand'
      : row.predicate === 'site-operator' ? from.role === 'site' && to.role === 'company'
      : row.predicate === 'accounting-parent' ? from.role === 'company' && to.role === 'company'
      : ['company', 'brand'].includes(from.role) && to.role === 'company';
    if (!typed) { errors.push({id: row.id, reason: 'Relationship role mismatch'}); continue; }
    evidence.push({id: row.id, subject: from.canonicalId, value: to.canonicalId, predicate: row.predicate,
      matchStatus: 'verified', source: row});
  }
  const start = resolve(subject), end = resolve(target);
  if (!start || !end) return result(unknown('Exact current source identities unresolved'));
  const control = evidence.filter(row => ['control', 'accounting-parent', ...(minorityOptIn ? ['minority'] : [])].includes(row.predicate));
  const conflict = new Set(control.filter(row => control.some(other => other.subject === row.subject
    && other.predicate === row.predicate && other.value !== row.value)).map(row => row.subject));
  return result(ownershipPath(control.filter(row => !conflict.has(row.subject)), start.canonicalId, end.canonicalId, {now, includeMinority: minorityOptIn}));
}
