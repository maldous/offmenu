// Pure, injected NORM-13 authority boundary. No issuer data, I/O or defaults.
export const NAMED_REFERENCE_VERSION = 'named-reference/1';
const named = x => typeof x === 'string' && x.length > 0 && x.trim() === x && x.length <= 500;
const positive = x => typeof x === 'number' && Number.isFinite(x) && x > 0;
const hash = x => typeof x === 'string' && /^[a-f0-9]{64}$/.test(x);
const url = x => {
  if (!named(x)) return false;
  try {const u = new URL(x); return u.protocol === 'https:' && !!u.hostname && !u.username && !u.password;}
  catch {return false;}
};

// Capture data before crossing async owner boundaries. Never execute accessors,
// inherit approval fields, serialize NaN as null, or retain mutable input aliases.
function capture(value, budget = {nodes:0, chars:0}, seen = new Set(), depth = 0) {
  if (++budget.nodes > 20000 || depth > 32) throw Error('bounded-data');
  if (value === null || typeof value === 'boolean') return value;
  if (typeof value === 'number' && Number.isFinite(value)) return value;
  if (typeof value === 'string' && (budget.chars += value.length) <= 250000) return value;
  if (!value || typeof value !== 'object' || seen.has(value)) throw Error('plain-data');
  const array = Array.isArray(value), proto = Object.getPrototypeOf(value);
  if (!array && proto !== Object.prototype && proto !== null) throw Error('own-data');
  const keys = Reflect.ownKeys(value).filter(key => !(array && key === 'length'));
  if (keys.some(key => typeof key !== 'string') || keys.length > 1000 ||
      array && (keys.length !== value.length || keys.some((key, i) => key !== String(i)))) throw Error('dense-data');
  seen.add(value);
  const result = array ? [] : {};
  for (const key of keys) {
    const descriptor = Object.getOwnPropertyDescriptor(value, key);
    if (!descriptor.enumerable || !Object.hasOwn(descriptor, 'value')) throw Error('data-property');
    Object.defineProperty(result, key, {value:capture(descriptor.value, budget, seen, depth + 1),
      enumerable:true, configurable:true, writable:true});
  }
  seen.delete(value);
  return result;
}
const detached = value => capture(value);
const canonical = value => value && typeof value === 'object'
  ? Array.isArray(value) ? '[' + value.map(canonical).join(',') + ']'
    : '{' + Object.keys(value).sort().map(k => JSON.stringify(k) + ':' + canonical(value[k])).join(',') + '}'
  : JSON.stringify(value);
const same = (a, b) => canonical(a) === canonical(b); // Only captured finite data.
const ownFunction = (object, key) => {
  const d = object && Object.getOwnPropertyDescriptor(object, key);
  return d && Object.hasOwn(d, 'value') && typeof d.value === 'function' ? d.value : null;
};
const withheldMetric = reason => ({status:'withheld', denominator:null, percentReference:null,
  rankEligible:false, reason, issuerCell:null});

function registrySnapshot(raw) {
  if (!raw || typeof raw !== 'object' || ![Object.prototype, null].includes(Object.getPrototypeOf(raw))) throw Error('registry-data');
  const descriptors = Object.getOwnPropertyDescriptors(raw), header = {};
  for (const key of Reflect.ownKeys(descriptors)) {
    const d = descriptors[key];
    if (typeof key !== 'string' || !d.enumerable || !Object.hasOwn(d, 'value')) throw Error('registry-property');
    if (key !== 'metricCells') Object.defineProperty(header, key, {value:d.value, enumerable:true});
  }
  const budget = {nodes:0, chars:0}, captured = capture(header, budget), cells = descriptors.metricCells?.value;
  if (!cells || ![Object.prototype, null].includes(Object.getPrototypeOf(cells)) || Reflect.ownKeys(cells).length > 1000) throw Error('registry-cells');
  captured.metricCells = {};
  for (const key of Reflect.ownKeys(cells)) {
    if (typeof key !== 'string') throw Error('registry-cell-key');
    const d = Object.getOwnPropertyDescriptor(cells, key);
    let cell;
    try {if (!d.enumerable || !Object.hasOwn(d, 'value')) throw Error('cell-property'); cell = capture(d.value, budget);}
    catch {cell = {invalidCellData:true};}
    Object.defineProperty(captured.metricCells, key, {value:cell, enumerable:true, writable:true});
  }
  return captured;
}

function compatibleHeader(profile, request) {
  const {selection:s, calculation:c, context:x} = request, issuer = profile.issuer, rights = profile.rights, policy = profile.contextPolicy;
  return ['system','profileId','version','issuerId','referenceType','cohortId'].every(k => named(s[k])) &&
    s.system === profile.system && s.profileId === profile.id && s.version === profile.version &&
    s.issuerId === issuer?.id && s.referenceType === profile.referenceType && s.cohortId === profile.cohort?.id &&
    named(profile.name) && named(profile.sourceId) && profile.basis === 'person-day' &&
    named(issuer.documentId) && named(issuer.documentVersion) && hash(issuer.documentSha256) && url(issuer.documentUrl) &&
    ['id','lifeStage','ageBand','sexIfApplicable','pregnancyLactationIfApplicable'].every(k => named(profile.cohort[k])) &&
    same(profile.cohort, x.cohort) && c.population === profile.cohort.lifeStage &&
    named(x.accountScope) && named(x.audience) && x.action === 'derive' &&
    rights?.sourceId === profile.sourceId && named(rights.revision) && url(rights.evidenceUrl) &&
    rights.status === 'active' && Array.isArray(rights.actions) && Array.isArray(rights.audiences) &&
    rights.actions.includes(x.action) && rights.audiences.includes(x.audience) &&
    c.calculationVersion === 'basket/1.1' && named(c.basketId) && Number.isSafeInteger(c.version) && c.version > 0 &&
    ['track','purpose','state','referencePeriod'].every(k => named(c[k])) && positive(c.personDays) &&
    named(policy?.id) && named(policy.version) && policy.id === x.policyId && policy.version === x.policyVersion &&
    ['tracks','purposes','states','referencePeriods'].every(k => Array.isArray(policy[k])) &&
    policy.tracks.includes(c.track) && policy.purposes.includes(c.purpose) &&
    policy.states.includes(c.state) && policy.referencePeriods.includes(c.referencePeriod);
}

function decisionMatches(decision, status, binding, now) {
  return decision?.status === status && named(decision.decisionId) && named(decision.revision) &&
    decision.binding && same(decision.binding, binding) && Number.isFinite(decision.checkedAt) &&
    Number.isFinite(decision.validUntil) && decision.checkedAt <= now && now < decision.validUntil;
}

/** Trusted server caller supplies registry/admission/policy/clock functions. Client
 * declarations never provide that authority. No implicit analytical/medical selection. */
export async function resolveNamedReference(input, dependencies = {}) {
  let request;
  try {request = capture(input);} catch {return {version:NAMED_REFERENCE_VERSION, status:'withheld',
    reason:'invalid-own-input', metrics:{}, referenceProfile:null};}
  const metricIds = Object.keys(request.calculation?.metrics || {}), results = Object.fromEntries(metricIds.map(id => [id, withheldMetric('unqualified-source')]));
  const stop = reason => ({version:NAMED_REFERENCE_VERSION, status:'withheld', reason,
    metrics:Object.fromEntries(metricIds.map(id => [id, withheldMetric(reason)])), referenceProfile:null});
  if (!request.selection || !request.context || !request.calculation || !metricIds.length || metricIds.length > 1000) return stop('missing-context');
  const readRegistry = ownFunction(dependencies, 'readRegistry'), admitSource = ownFunction(dependencies, 'admitSource');
  const qualifyContext = ownFunction(dependencies, 'qualifyContext'), clock = ownFunction(dependencies, 'clock');
  if (!readRegistry || !admitSource || !qualifyContext || !clock) return stop('missing-owner-boundary');
  let profile, binding, admission, contextDecision, startedAt, now;
  try {
    startedAt = clock(); if (!Number.isFinite(startedAt)) return stop('unknown-clock');
    profile = registrySnapshot(await readRegistry(detached(request.selection), detached(request.context)));
    if (!compatibleHeader(profile, request)) return stop('incompatible-profile-context');
    binding = {request:detached(request), registry:detached(profile), evaluatedAt:startedAt};
    admission = capture(await admitSource(detached(binding)));
    now = clock(); if (!Number.isFinite(now) || now < startedAt) return stop('unknown-clock');
    if (!decisionMatches(admission, 'admitted', binding, now)) return stop('source-not-admitted');
    const admittedAt = now;
    contextDecision = capture(await qualifyContext(detached(binding)));
    now = clock(); if (!Number.isFinite(now) || now < admittedAt) return stop('unknown-clock');
  } catch {return stop('owner-boundary-unavailable');}
  if (!decisionMatches(admission, 'admitted', binding, now)) return stop('source-not-admitted');
  if (!decisionMatches(contextDecision, 'compatible', binding, now)) return stop('context-not-qualified');
  const projection = {system:profile.system, id:profile.id, version:profile.version, name:profile.name,
    lifeStage:profile.cohort.lifeStage, sourceId:profile.sourceId, basis:'person-day', metrics:{}};
  for (const id of metricIds) {
    const m = request.calculation.metrics[id], cell = Object.hasOwn(profile.metricCells, id) ? profile.metricCells[id] : null;
    let reason = null;
    if (!cell || cell.invalidCellData) reason = 'missing-or-invalid-issuer-cell';
    else if (!positive(cell.amount)) reason = 'nonpositive-or-unknown-target';
    else if (cell.status !== 'source-issued' || cell.conflict === true ||
      cell.issuerId !== profile.issuer.id || cell.documentVersion !== profile.issuer.documentVersion ||
      cell.sourceSha256 !== profile.issuer.documentSha256 || cell.sourceUrl !== profile.issuer.documentUrl ||
      cell.sourceId !== profile.sourceId || cell.rightsRevision !== profile.rights.revision ||
      cell.metricId !== id || cell.referenceType !== profile.referenceType || cell.cohortId !== profile.cohort.id || cell.basis !== 'person-day' ||
      !['cellId','tableId','rowId','columnId'].every(k => named(cell[k]))) reason = 'incompatible-issuer-cell';
    else if (m?.status !== 'complete' || typeof m.total !== 'number' || !Number.isFinite(m.total) || m.total < 0 ||
      !named(m.unit) || !Array.isArray(m.definitions) || m.definitions.length !== 1 || !named(m.definitions[0]) ||
      cell.unit !== m.unit || cell.componentDefinition !== m.definitions[0]) reason = 'incomplete-or-incompatible-metric';
    const perDay = reason ? null : m.total / request.calculation.personDays;
    const percent = reason ? null : 100 * perDay / cell.amount;
    if (!reason && (!Number.isFinite(perDay) || !Number.isFinite(percent) ||
      Object.hasOwn(m, 'perPersonDay') && m.perPersonDay !== perDay)) reason = 'invalid-person-day-amount';
    if (reason) {results[id] = withheldMetric(reason); continue;}
    results[id] = {status:'qualified', denominator:cell.amount, denominatorUnit:cell.unit,
      percentReference:percent, rankEligible:false, reason:null, issuerCell:detached(cell)};
    Object.defineProperty(projection.metrics, id, {value:{value:cell.amount, unit:cell.unit,
      definition:cell.componentDefinition, status:'complete', referenceType:cell.referenceType,
      issuerCell:detached(cell)}, enumerable:true});
  }
  const count = Object.values(results).filter(x => x.status === 'qualified').length;
  return {version:NAMED_REFERENCE_VERSION, status:count === metricIds.length ? 'qualified' : count ? 'partial' : 'withheld',
    reason:count ? null : 'no-qualified-metrics', metrics:results, referenceProfile:count ? projection : null,
    authorityEvidence:{admission:detached(admission), contextPolicy:detached(contextDecision)}, binding:detached(binding),
    notice:'Descriptive analytical reference coverage only. No ranking, medical selection, safety or adequacy certification.'};
}
