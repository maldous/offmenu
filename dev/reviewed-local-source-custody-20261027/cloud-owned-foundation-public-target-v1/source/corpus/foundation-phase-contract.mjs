// Pure source-scoped phase assessment. This module grants no publication,
// source-use, registry, physical-product-identity or runtime admission.
export const FOUNDATION_CONTRACT = 'offmenu-barcode-foundation-phase/1';
const SHA = /^[a-f0-9]{64}$/;
const SUBJECT = ['sourceId','releaseId','recordId','sourceObservationSha256',
  'inputDatabaseSha256','sourceQualificationSha256','sourceDocumentSha256'];
const own = (value,key) => Object.hasOwn(value,key);
const object = value => value !== null && typeof value === 'object' && !Array.isArray(value);
const text = value => typeof value === 'string' && value.length > 0 && value.length <= 512 && !/[\x00-\x1f\x7f]/.test(value);
const sameSubject = (a,b) => object(a) && object(b) && SUBJECT.every(key => own(a,key) && own(b,key) && text(a[key]) && a[key] === b[key]) && SUBJECT.slice(3).every(key => SHA.test(a[key]));
function exactGtin(value) {
  if (typeof value !== 'string' || !/^(?:[0-9]{8}|[0-9]{12}|[0-9]{13}|[0-9]{14})$/.test(value)) return false;
  let sum = 0, weight = 3;
  for (let i=value.length-2;i>=0;i--) { sum += Number(value[i])*weight; weight = weight===3 ? 1 : 3; }
  return (10-sum%10)%10 === Number(value.at(-1));
}
function provenance(evidence,subject) {
  return Array.isArray(evidence) && evidence.length > 0 && evidence.length <= 32 &&
    evidence.every(row => object(row) && sameSubject(row.sourceBinding,subject) && text(row.pointer) &&
      ['source-field','qualified-representation-omission','reviewed-type-rule'].includes(row.kind));
}
function reviewed(value,subject,policy) {
  return object(value) && value.state === 'reviewed' &&
    value.registrySha256 === policy.registrySha256 &&
    value.independentReviewSha256 === policy.independentReviewSha256 && provenance(value.evidence,subject);
}
function parameterValue(value,definition) {
  if (definition.kind === 'number') return typeof value === 'number' && Number.isFinite(value) &&
    (definition.minimum === undefined || value >= definition.minimum) &&
    (definition.maximum === undefined || value <= definition.maximum);
  return definition.kind === 'string' && text(value) &&
    (!definition.values || definition.values.includes(value));
}

// The caller must independently pin/review the policy and qualify the reader's
// source/record binding. A status or digest supplied by an app user is not proof.
export function assessFoundation(candidate,policy) {
  if (!object(policy) || policy.schema !== FOUNDATION_CONTRACT || !SHA.test(policy.registrySha256) ||
      !SHA.test(policy.independentReviewSha256) || !object(policy.definitions)) throw Error('FOUNDATION_POLICY_REQUIRED');
  const reasons = [], parameters = {known:[],unknown:[],notApplicable:[]};
  const result = () => ({schema:FOUNDATION_CONTRACT,phase:'barcode-foundation',
    state:reasons.length ? 'incomplete' : 'phase-qualified',foundationComplete:reasons.length===0,
    ingredientApplicationEligible:reasons.length ? null : candidate.classification.value==='ingredient',
    classification:reasons.length ? null : candidate.classification.value,
    parameters,reasons:[...new Set(reasons)],physicalProductEquivalenceAsserted:false,
    fullProductComplete:false,goldAdmitted:false,publicationAccepted:false,recipeNutritionJoinsAccepted:false});
  if (!object(candidate)) { reasons.push('candidate-missing'); return result(); }
  const identity = candidate.identity, subject = identity?.sourceBinding;
  if (!object(identity) || identity.namespace !== 'barcode' || !exactGtin(candidate.barcode) ||
      identity.lexicalValue !== candidate.barcode || !text(identity.nativeRecordId) ||
      !text(identity.stageRecordId) || !SHA.test(identity.stageRecordWireSha256) || !sameSubject(subject,subject))
    reasons.push('exact-source-barcode-identity-unqualified');
  const classification = candidate.classification;
  if (!reviewed(classification,subject,policy) || !['ingredient','noningredient'].includes(classification.value))
    reasons.push('application-classification-unresolved');
  const base = candidate.base;
  const definition = object(base) && text(base.canonicalEnglishKey) && own(policy.definitions,base.canonicalEnglishKey)
    ? policy.definitions[base.canonicalEnglishKey] : null;
  if (!object(definition) || !object(definition.parameters) || !['ingredient','noningredient'].includes(definition.classification)) {
    reasons.push('canonical-english-base-or-type-unresolved'); return result();
  }
  if (!reviewed(base,subject,policy) || base.canonicalEnglishLabel !== definition.canonicalEnglishLabel ||
      base.conceptId !== definition.conceptId || base.typeKey !== definition.typeKey ||
      classification?.value !== definition.classification) reasons.push('canonical-english-base-or-type-unresolved');
  const supplied = object(candidate.parameters) ? candidate.parameters : {};
  for (const [key,definitionValue] of Object.entries(definition.parameters)) {
    const row = own(supplied,key) ? supplied[key] : null;
    if (!object(row) || !provenance(row.evidence,subject)) { reasons.push('parameter-state-or-provenance-missing:'+key); continue; }
    if (row.state === 'known') {
      if (row.independentReviewSha256 !== policy.independentReviewSha256 || !parameterValue(row.value,definitionValue) ||
          row.evidence.some(e => e.kind !== 'source-field')) reasons.push('parameter-known-value-unqualified:'+key);
      else parameters.known.push(key);
    } else if (row.state === 'unknown') {
      if (own(row,'value') || row.reason !== 'not-provided-in-qualified-representation' ||
          row.evidence.some(e => e.kind !== 'qualified-representation-omission')) reasons.push('parameter-unknown-state-unqualified:'+key);
      else parameters.unknown.push(key);
    } else if (row.state === 'not-applicable') {
      if (definitionValue.notApplicable !== true || own(row,'value') ||
          row.independentReviewSha256 !== policy.independentReviewSha256 ||
          row.evidence.some(e => e.kind !== 'reviewed-type-rule')) reasons.push('parameter-not-applicable-unqualified:'+key);
      else parameters.notApplicable.push(key);
    } else reasons.push('parameter-state-or-provenance-missing:'+key);
  }
  for (const key of Object.keys(supplied)) if (!own(definition.parameters,key)) reasons.push('parameter-not-in-selected-policy:'+key);
  return result();
}

export function summarizeFoundation(assessments) {
  if (!Array.isArray(assessments) || assessments.some(row => row?.schema !== FOUNDATION_CONTRACT ||
      !['phase-qualified','incomplete'].includes(row.state) || row.foundationComplete !== (row.state==='phase-qualified') ||
      row.goldAdmitted !== false || row.publicationAccepted !== false ||
      row.foundationComplete && !['ingredient','noningredient'].includes(row.classification))) throw Error('FOUNDATION_ASSESSMENTS_REQUIRED');
  return {schema:FOUNDATION_CONTRACT,scope:'selected-assessments-only',observations:assessments.length,
    foundationComplete:assessments.filter(row=>row.foundationComplete).length,
    ingredient:assessments.filter(row=>row.foundationComplete&&row.classification==='ingredient').length,
    noningredient:assessments.filter(row=>row.foundationComplete&&row.classification==='noningredient').length,
    incomplete:assessments.filter(row=>!row.foundationComplete).length,
    fullProductComplete:0,goldAdmitted:0,publicationAccepted:false};
}
