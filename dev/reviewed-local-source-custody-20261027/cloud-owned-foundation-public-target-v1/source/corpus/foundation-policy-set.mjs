// A release may carry independently reviewed policy cuts without re-stamping
// retained candidates with another cut's registry or review receipt.
import {assessFoundation, FOUNDATION_CONTRACT} from './foundation-phase-contract-v2.mjs';
const SET = 'offmenu-foundation-policy-set/1', SHA = /^[a-f0-9]{64}$/;
const object = v => v !== null && typeof v === 'object' && !Array.isArray(v);
const own = (v, k) => Object.hasOwn(v, k);
const bytes = s => new TextEncoder().encode(s);
async function digest(s) {
  return [...new Uint8Array(await crypto.subtle.digest('SHA-256', bytes(s)))]
    .map(v => v.toString(16).padStart(2, '0')).join('');
}
function need(ok) { if (!ok) throw Error('FOUNDATION_POLICY_SELECTION_UNQUALIFIED'); }

// Caller has already checked the fixed policy file's bytes, SHA and admission.
// No policy URL, arbitrary import or source acquisition is accepted here.
export async function createFoundationPolicySelector(policy, {sha256, sourceId} = {}) {
  need(object(policy) && SHA.test(sha256) && typeof sourceId === 'string');
  const policies = new Map();
  let defaultSha256 = sha256;
  if (policy.schema === FOUNDATION_CONTRACT) policies.set(sha256, policy);
  else {
    need(policy.schema === SET && object(policy.policies) &&
      SHA.test(policy.defaultPolicySha256) && object(policy.sourceQualifications));
    const members = Object.entries(policy.policies);
    need(members.length >= 1 && members.length <= 8);
    for (const [key, serialized] of members) {
      need(SHA.test(key) && typeof serialized === 'string' &&
        bytes(serialized).byteLength > 0 && bytes(serialized).byteLength <= 128 * 1024 &&
        await digest(serialized) === key);
      const member = JSON.parse(serialized);
      need(member?.schema === FOUNDATION_CONTRACT && object(member.sourceQualifications));
      policies.set(key, member);
    }
    defaultSha256 = policy.defaultPolicySha256;
    need(policies.has(defaultSha256));
  }
  const scope = policy.sourceQualifications?.[sourceId];
  need(own(policy.sourceQualifications || {}, sourceId) && object(scope) &&
    typeof scope.releaseId === 'string' && SHA.test(scope.qualificationSha256));
  // Snapshot the qualified file; later caller mutations cannot alter selection.
  const qualified = structuredClone(scope);
  const selected = new Map([...policies].map(([key, member]) => [key, structuredClone(member)]));
  return {sourceQualification: qualified, assess(candidate) {
    const key = own(candidate || {}, 'foundationPolicySha256')
      ? candidate.foundationPolicySha256 : defaultSha256;
    need(SHA.test(key) && selected.has(key));
    const member = selected.get(key), actual = member.sourceQualifications?.[sourceId];
    need(own(member.sourceQualifications || {}, sourceId) &&
      actual?.releaseId === qualified.releaseId &&
      actual?.qualificationSha256 === qualified.qualificationSha256 &&
      candidate?.identity?.sourceBinding?.sourceId === sourceId);
    return assessFoundation(candidate, member);
  }};
}
