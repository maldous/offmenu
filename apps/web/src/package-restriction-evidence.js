import {admission, qualify} from './evidence-model.js';

const text = value => typeof value === 'string' && value.trim().length > 0;
const dated = value => value == null || (text(value) && Number.isFinite(Date.parse(value)));
const scopeKeys = {package: [], lot: ['lotCode'], menu: ['menuId', 'menuItemId']};

// Explicit caller-owned bindings only: culinary tags and raw provider labels are
// not assertions. No I/O, clock defaults, identity matching or quantity conversion.
export function packageRestrictionEvidence({rule, target, evidence = [], policies = {}, owner, consent, market, now} = {}) {
  const unknown = reason => ({status: 'unknown', reason, evidenceIds: [], automaticSelection: false});
  if (!Number.isFinite(now) || !text(owner) || consent !== true || !text(market))
    return unknown('Explicit clock, account, consent and market required');
  if (!target || !Object.hasOwn(scopeKeys, target.kind) || !text(target.subject) || target.owner !== owner ||
      scopeKeys[target.kind].some(key => !text(target[key])))
    return unknown('Actual package, lot or menu binding required');
  if (!rule || !text(rule.predicate) || !['include', 'exclude'].includes(rule.operator) ||
      rule.value == null || !Array.isArray(evidence) || evidence.length > 200 ||
      !policies || typeof policies !== 'object' || Array.isArray(policies))
    return unknown('Explicit rule and at most 200 assertions required');

  const rows = evidence.filter(row => {
    if (!row || !text(row.id) || !text(row.sourceId) || row.subject !== target.subject ||
        row.market !== market || row.scope?.kind !== target.kind ||
        scopeKeys[target.kind].some(key => row.scope[key] !== target[key]) ||
        row.matchStatus !== 'verified' || row.value == null ||
        !['validFrom', 'validUntil', 'freshUntil'].every(key => text(row[key])) ||
        (row.dependencies != null && (!Array.isArray(row.dependencies) || row.dependencies.some(d => !d || d.allowed !== true ||
          !dated(d.retainUntil) || (d.retainUntil != null && Date.parse(d.retainUntil) <= now)))) ||
        !['validFrom', 'validUntil', 'freshUntil', 'retainUntil'].every(key => dated(row[key]))) return false;
    const policy = Object.hasOwn(policies, row.sourceId) ? policies[row.sourceId] : null;
    if (!Array.isArray(policy?.actions) || !Array.isArray(policy?.audiences)) return false;
    const context = {owner, consent, market, now, audience: 'private'};
    return admission(policy, row, {...context, action: 'display'}).allowed &&
      admission(policy, row, {...context, action: 'derive'}).allowed;
  });
  let result = qualify(rule, rows, {subject: target.subject, market, now});
  // qualify's certifiedOnly gate checks whether *any* row is certified. Require
  // the matching value itself to have identified scheme/certifier evidence.
  // Preserve conflicts across all admitted rows before this narrower check.
  if (result.status === 'pass' && rule.certifiedOnly) {
    const certified = rows.filter(row => row.evidenceClass === 'certified' && text(row.schemeId) && text(row.certifierId));
    const certification = qualify(rule, certified, {subject: target.subject, market, now});
    if (certification.status !== 'pass') result = unknown('Scoped scheme and certifier evidence not established');
    else result = certification;
  }
  // This is a rule result, never a medical safety or menu selection clearance.
  return {...result, evidenceIds: result.evidenceIds || [], automaticSelection: false};
}
