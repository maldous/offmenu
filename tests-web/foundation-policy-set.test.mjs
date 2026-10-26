import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {gzipSync} from 'node:zlib';
import {createFoundationPolicySelector} from '../corpus/foundation-policy-set.mjs';
import {createAcceptedFoundationReader, foundationDigest} from '../corpus/foundation-origin-reader.mjs';

// Generated fixture, separately checked against the real adapter by the Python
// test. Node/CI needs no operational paths, Python runtime or source packet.
const generated = JSON.parse(readFileSync(new URL('./fixtures/named-food-active-generated.json', import.meta.url)));
const enc = new TextEncoder(), clone = structuredClone, h = s => s.repeat(64);
const sha = s => foundationDigest(enc.encode(s));
async function fixture() {
  const named = JSON.parse(generated.policyJson), namedSha = await sha(generated.policyJson);
  const candidate = clone(generated.candidate), legacy = clone(named), old = clone(candidate);
  legacy.registrySha256 = h('a'); legacy.independentReviewSha256 = h('b');
  const definition = clone(Object.values(legacy.definitions)[0]);
  Object.assign(definition, {canonicalEnglishKey: 'milk', canonicalEnglishLabel: 'Milk',
    conceptId: 'generated:milk', typeKey: 'milk-products'});
  Object.assign(definition.typeRelation, {typeKey: 'milk-products', canonicalEnglishLabel: 'Milk products',
    conceptId: 'generated:milk-products', subjectConceptId: 'generated:milk',
    registrySha256: h('a'), independentReviewSha256: h('b')});
  legacy.definitions = {milk: definition};
  delete old.foundationPolicySha256;
  Object.assign(old.classification, {registrySha256: h('a'), independentReviewSha256: h('b')});
  Object.assign(old.base, {registrySha256: h('a'), independentReviewSha256: h('b'),
    canonicalEnglishKey: 'milk', canonicalEnglishLabel: 'Milk', conceptId: 'generated:milk', typeKey: 'milk-products'});
  old.type = {state: 'reviewed', ...definition.typeRelation, evidence: old.type.evidence};
  old.parameters.form = clone(old.parameters.baseMaterial);
  const legacyJson = JSON.stringify(legacy), legacySha = await sha(legacyJson);
  const set = {schema: 'offmenu-foundation-policy-set/1', sourceQualifications: clone(named.sourceQualifications),
    defaultPolicySha256: legacySha, policies: {[legacySha]: legacyJson, [namedSha]: generated.policyJson}};
  return {set, candidate, old, namedSha, legacySha};
}
test('independent policy receipts and known source-name form survive exact selection', async () => {
  const f = await fixture(), select = await createFoundationPolicySelector(f.set, {sha256: h('d'), sourceId: 'off'});
  assert.equal(select.assess(f.candidate).foundationComplete, true);
  assert.equal(select.assess(f.old).foundationComplete, true);
  assert.equal(f.candidate.classification.independentReviewSha256,
    '47c520f2a6a1527e2d8d2aa2c1bcdc075c8efa5d756fc3de3735f12ca6b0a5d5');
  assert.deepEqual(select.assess(f.candidate).parameters.known, ['form']);
  assert.equal(select.assess(f.candidate).parameters.unknown.length, 23);
  assert.equal(select.assess(f.candidate).goldAdmitted, false);
  assert.equal(generated.matcherResult.classificationAccepted, false);
  assert.equal(generated.matcherResult.foundationQualified, false);
});
test('a named candidate cannot inherit default-policy acceptance or choose an unknown policy', async () => {
  const f = await fixture(), select = await createFoundationPolicySelector(f.set, {sha256: h('d'), sourceId: 'off'});
  delete f.candidate.foundationPolicySha256;
  assert.equal(select.assess(f.candidate).foundationComplete, false);
  f.candidate.foundationPolicySha256 = h('f');
  assert.throws(() => select.assess(f.candidate), /SELECTION_UNQUALIFIED/);
});
test('tampered member, absent default, nested set and source-scope conflict fail closed', async () => {
  for (const change of ['tamper', 'default', 'nested', 'scope']) {
    const f = await fixture();
    if (change === 'tamper') f.set.policies[f.namedSha] += ' ';
    if (change === 'default') f.set.defaultPolicySha256 = h('f');
    if (change === 'nested') {
      const json = JSON.stringify(f.set), key = await sha(json);
      f.set.policies[key] = json;
    }
    if (change === 'scope') f.set.sourceQualifications.off.qualificationSha256 = h('f');
    if (change !== 'scope') await assert.rejects(() => createFoundationPolicySelector(f.set, {sha256: h('d'), sourceId: 'off'}));
    else {
      const select = await createFoundationPolicySelector(f.set, {sha256: h('d'), sourceId: 'off'});
      assert.throws(() => select.assess(f.candidate), /SELECTION_UNQUALIFIED/);
    }
  }
});
test('a prepared selector snapshots policy members and rejects cross-source candidates', async () => {
  const f = await fixture(), select = await createFoundationPolicySelector(f.set, {sha256: h('d'), sourceId: 'off'});
  f.set.policies[f.namedSha] = '{}';
  assert.equal(select.assess(f.candidate).foundationComplete, true);
  f.candidate.identity.sourceBinding.sourceId = 'usda-files';
  assert.throws(() => select.assess(f.candidate), /SELECTION_UNQUALIFIED/);
});
test('actual reader serves a policy set in three bounded blob reads and preserves qualifier/unknowns', async () => {
  const f = await fixture(), files = new Map(), ns = 'own-data/foundation/generated-named/', reads = [];
  async function file(name, body, zip = false) {
    const raw = enc.encode(JSON.stringify(body)), data = zip ? new Uint8Array(gzipSync(raw)) : raw;
    const descriptor = {key: ns + name, sha256: await foundationDigest(data), bytes: data.length,
      ...(zip ? {uncompressedBytes: raw.length} : {})};
    files.set(descriptor.key, data); return descriptor;
  }
  const policy = await file('policy.json', f.set), barcode = f.candidate.barcode;
  const partition = await file('off/part.json.gz', {schema: 'offmenu-foundation-products/2', sourceId: 'off',
    policySha256: policy.sha256, entries: {[barcode]: [{schema: 'offmenu-foundation-product/2',
      id: f.candidate.identity.stageRecordId, candidate: f.candidate}]}}, true);
  const prefix = (await sha(barcode)).slice(0, 2), scope = f.set.sourceQualifications.off;
  const manifest = await file('manifest.json', {schema: 'offmenu-foundation-publication/2',
    releaseId: 'generated-named', status: 'phase-qualified-release-ready',
    fieldContract: 'offmenu-barcode-foundation-phase/2', policySha256: policy.sha256,
    consumerCodeSha256: h('c'), acceptance: {status: 'selected-phase-records-exercised', receiptSha256: h('d')},
    privateProviderData: false, rawSourcePayloadPublished: false, acquisitionAtRuntime: false,
    goldAdmitted: false, fullProductComplete: false, legacyCuratedAdmission: false,
    sources: {off: {sourceId: 'off', ...scope, license: 'GENERATED', attribution: 'GENERATED',
      partitions: {[prefix]: partition}}}});
  const reader = await createAcceptedFoundationReader(async key => {reads.push(key); return files.get(key);},
    {manifest, policy, sourceId: 'off', releaseId: 'generated-named', consumerCodeSha256: h('c'), admissionReceiptSha256: h('d')});
  const result = await reader.lookup({source: 'off', barcode});
  assert.equal(result.httpStatus, 200); assert.equal(reads.length, 3);
  const data = result.records[0].data;
  assert.equal(data.canonicalEnglishKey, 'beetroot');
  assert.equal(data.meaningfulType.conceptId, 'urn:offmenu:type:sliced-beetroot');
  assert.equal(data.variantParameters.form.state, 'known');
  assert.equal(data.variantParameters.form.evidenceKind, 'source-name-declared');
  assert.equal(data.variantParameters.processing.state, 'unknown');
  assert.equal(data.normalizationComplete, false); assert.equal(data.goldAdmitted, false);
  assert.equal(data.automaticPlanningEligible, false); assert.equal(result.externalFallback, false);
});
