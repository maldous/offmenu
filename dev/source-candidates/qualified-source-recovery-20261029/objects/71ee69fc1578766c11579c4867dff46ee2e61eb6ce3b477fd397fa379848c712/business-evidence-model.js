import {ownershipPath} from './evidence-model.js';

// Pure projection of already permitted assertions; this is not identity or rights review.
const kinds = new Set(['company', 'site', 'brand', 'product']);
const relationships = new Set(['control', 'accounting-parent', 'minority', 'franchise', 'licence', 'operating-brand', 'site-operator']);
const origins = new Set(['manufactured-in', 'headquartered-in', 'incorporated-in']);
// Source owners explicitly admit this projection state; absence is never a legacy default.
// Identity verification does not establish evidence validity or grant source rights.
const usableAssertionState = row => row.status === 'active';
const text = value => typeof value === 'string' && value.trim().length > 0;
const date = value => text(value) && /^\d{4}-\d{2}-\d{2}(?:T\d{2}:\d{2}:\d{2}(?:\.\d+)?Z)?$/.test(value)
  && Number.isFinite(Date.parse(value)) && new Date(Date.parse(value)).toISOString().slice(0, 10) === value.slice(0, 10);
const metadata = ['sourceId', 'sourceRecordId', 'sourceCountry', 'retrievedAt', 'jurisdiction', 'market', 'scope',
  'issuer', 'evidenceClass', 'rightsRevision', 'validFrom', 'validUntil', 'freshUntil', 'retainUntil', 'status', 'matchStatus'];

export function adaptBusinessEvidence({entities = [], assertions = []} = {}) {
  const errors = [], identities = [], evidence = [];
  const reject = (id, reason) => errors.push({id: text(id) ? id : null, reason});
  const counts = new Map();
  for (const entity of entities) counts.set(entity?.id, (counts.get(entity?.id) || 0) + 1);
  for (const entity of entities) {
    if (!entity || entity.personal === true || !text(entity.id) || counts.get(entity.id) !== 1 || !kinds.has(entity.kind)) {
      reject(entity?.id, 'Unique non-personal typed identity required'); continue;
    }
    identities.push({id: entity.id, kind: entity.kind, name: text(entity.name) ? entity.name : null,
      matchStatus: entity.matchStatus === 'verified' ? 'verified' : 'candidate'});
  }
  const byId = new Map(identities.map(entity => [entity.id, entity]));
  const assertionCounts = new Map();
  for (const row of assertions) assertionCounts.set(row?.id, (assertionCounts.get(row?.id) || 0) + 1);
  for (const row of assertions) {
    if (!row || row.personal === true || !text(row.id) || assertionCounts.get(row.id) !== 1 || !byId.has(row.subject)) {
      reject(row?.id, 'Unique non-personal assertion and exact subject ID required'); continue;
    }
    if (!['sourceId', 'sourceRecordId', 'jurisdiction', 'scope', 'evidenceClass', 'rightsRevision'].every(key => text(row[key]))
      || !date(row.retrievedAt) || !date(row.validFrom) || !date(row.freshUntil)
      || ['validUntil', 'retainUntil'].some(key => row[key] !== undefined && !date(row[key]))
      || row.validUntil && Date.parse(row.validUntil) <= Date.parse(row.validFrom)
      || Date.parse(row.freshUntil) <= Date.parse(row.validFrom)) {
      reject(row.id, 'Source, scope, rights revision and valid temporal evidence required'); continue;
    }
    const subject = byId.get(row.subject), object = byId.get(row.value);
    let valid = false;
    if (relationships.has(row.predicate)) {
      valid = !!object && (row.predicate === 'operating-brand'
        ? subject.kind === 'company' && object.kind === 'brand'
        : row.predicate === 'site-operator' ? subject.kind === 'site' && object.kind === 'company'
        : ['company', 'brand'].includes(subject.kind) && object.kind === 'company');
    } else if (origins.has(row.predicate)) {
      valid = text(row.value) && /^[A-Z]{2}$/.test(row.value) && (row.predicate === 'manufactured-in'
        ? ['product', 'site'].includes(subject.kind) : subject.kind === 'company');
    } else if (row.predicate === 'size') {
      const value = row.value;
      valid = subject.kind === 'company' && !!value && ['headcount', 'revenue', 'farm-area'].includes(value.metric)
        && Number.isFinite(value.amount) && value.amount >= 0 && text(value.unit)
        && /^\d{4}$/.test(value.fiscalYear) && ['entity', 'group'].includes(value.basis)
        && ['declared', 'estimated'].includes(value.method)
        && (value.metric !== 'revenue' || /^[A-Z]{3}$/.test(value.currency))
        && (value.metric !== 'headcount' || value.unit === 'people');
    }
    if (!valid) { reject(row.id, 'Unsupported predicate or incompatible typed value'); continue; }
    const result = {id: row.id, subject: row.subject, predicate: row.predicate, value: row.value};
    for (const key of metadata) if (row[key] !== undefined) result[key] = row[key];
    if (row.predicate === 'size') result.value = Object.fromEntries(
      ['metric', 'amount', 'unit', 'currency', 'fiscalYear', 'basis', 'method'].filter(key => row.value[key] !== undefined).map(key => [key, row.value[key]]));
    if (row.matchStatus !== 'verified' || subject.matchStatus !== 'verified' || object && object.matchStatus !== 'verified') result.matchStatus = 'candidate';
    if (!usableAssertionState(row)) reject(row.id, 'Assertion state is not explicitly admitted active');
    evidence.push(result);
  }
  return {entities: identities, assertions: evidence, errors};
}

export function businessOwnershipPath(model, start, target, {now = Date.now(), market = '', jurisdiction = '', includeMinority = false} = {}) {
  const unknown = reason => ({status: 'unknown', path: [], reason});
  if (!Number.isFinite(now) || ![start, target].every(id => model.entities.some(entity => entity.id === id && entity.matchStatus === 'verified')))
    return unknown('Verified exact identities and evaluation time required');
  const rows = model.assertions.filter(row => row.matchStatus === 'verified'
    && ['control', 'accounting-parent', ...(includeMinority ? ['minority'] : [])].includes(row.predicate)
    && usableAssertionState(row)
    && (!market || row.market === market) && (!jurisdiction || row.jurisdiction === jurisdiction)
    && date(row.validFrom) && Date.parse(row.validFrom) <= now
    && date(row.freshUntil) && Date.parse(row.freshUntil) > now
    && (!row.validUntil || date(row.validUntil) && Date.parse(row.validUntil) > now)
    && (!row.retainUntil || date(row.retainUntil) && Date.parse(row.retainUntil) > now));
  const conflicts = new Set(rows.filter(row => rows.some(other => other.subject === row.subject
    && other.predicate === row.predicate && other.value !== row.value)).map(row => row.subject));
  // A contradictory node must not yield one arbitrarily selected control path.
  const result = ownershipPath(rows.filter(row => !conflicts.has(row.subject)), start, target, {now, includeMinority});
  return result;
}
