import {validateGTIN} from './typed-identifier-contract.mjs';

export const IDENTITY_INDEX = 'offmenu-source-identity-index/2';
export const IDENTITY_MANIFEST = 'offmenu-source-identity-manifest/2';
export const FIELD_SET = 'source-identifier-claims-with-provenance/2';
const hex = value => typeof value === 'string' && /^[a-f0-9]{64}$/.test(value);
const object = value => value !== null && typeof value === 'object' && !Array.isArray(value);
const text = value => typeof value === 'string' && value.length > 0 && value.length <= 512 && !/[\x00-\x1f\x7f]/.test(value);
function need(ok, reason) { if (!ok) throw new Error(reason); }
function exact(value, fields, label) {
  need(object(value) && Object.keys(value).length === fields.length && fields.every(key => Object.hasOwn(value, key)), label);
}
const BINDING = ['inputDatabaseSha256','nativeRecordId','recordId','releaseId','sourceDocumentSha256','sourceId','sourceObservationSha256','sourceQualificationSha256'];
const RECORD = ['stageId','nativeId','wireSha256','sourceInputIndexSha256','rightsVisibilityField','sourceBinding','identifiers','barcodePostings','sourceRights','canonicalStatus','englishStatus','normalizationComplete','goldAdmitted'];
const RIGHTS = ['attribution','license','sourceVisibility'];

/** Validates the producer's metadata projection, never a food classification. */
export function validateIdentityRecord(record, scope) {
  need(scope.sourceId === 'usda-files', 'bounded-source-only');
  exact(record, RECORD, 'identity-record-fields');
  need(hex(record.sourceInputIndexSha256) && Array.isArray(scope.selectedSourceIndexes) && scope.selectedSourceIndexes.includes(record.sourceInputIndexSha256), 'selected-source-input-binding');
  need(['sourceVisibility','visibility'].includes(record.rightsVisibilityField), 'source-rights-field-provenance');
  const binding = record.sourceBinding;
  exact(binding, BINDING, 'source-binding-fields');
  need(text(record.stageId) && text(record.nativeId) && hex(record.wireSha256), 'stage-native-wire-binding');
  need(binding.nativeRecordId === record.nativeId && text(binding.recordId), 'native-source-record-binding');
  need(binding.sourceId === scope.sourceId && binding.releaseId === scope.releaseId && binding.sourceQualificationSha256 === scope.sourceQualificationSha256, 'source-release-qualification-binding');
  for (const field of ['inputDatabaseSha256','sourceDocumentSha256','sourceObservationSha256','sourceQualificationSha256']) need(hex(binding[field]), 'source-evidence-hash');
  exact(record.sourceRights, RIGHTS, 'rights-fields');
  need(object(scope.sourceRights) && RIGHTS.every(key => record.sourceRights[key] === scope.sourceRights[key]), 'exact-source-rights');
  need(record.sourceRights.sourceVisibility === 'source-staging' && text(record.sourceRights.license) && text(record.sourceRights.attribution), 'source-claim-rights');
  need(record.canonicalStatus === 'unresolved' && record.englishStatus === 'unresolved' && record.normalizationComplete === false && record.goldAdmitted === false, 'source-not-canonical');
  need(Array.isArray(record.identifiers) && record.identifiers.length > 0 && record.identifiers.length <= 16, 'identifier-bound');
  for (const identifier of record.identifiers) {
    exact(identifier, ['system','value'], 'source-identifier-fields');
    need(text(identifier.system) && text(identifier.value), 'source-identifier-value');
    need(['barcode','USDA-FDC'].includes(identifier.system), 'bounded-source-identifier-system');
  }
  need(record.identifiers.some(identifier => identifier.system === 'USDA-FDC' && identifier.value === binding.recordId), 'native-source-identifier-binding');
  need(Array.isArray(record.barcodePostings) && record.barcodePostings.length > 0 && record.barcodePostings.length <= 16, 'posting-bound');
  const codes = new Set();
  for (const posting of record.barcodePostings) {
    exact(posting, ['checksumValid','lexicalCode'], 'posting-fields');
    need(typeof posting.checksumValid === 'boolean' && text(posting.lexicalCode) && posting.checksumValid === validateGTIN(posting.lexicalCode), 'honest-source-checksum-claim');
    need(record.identifiers.some(identifier => identifier.system === 'barcode' && identifier.value === posting.lexicalCode), 'posting-source-identifier-binding');
    need(!codes.has(posting.lexicalCode), 'duplicate-posting');
    codes.add(posting.lexicalCode);
  }
  return structuredClone(record);
}

export async function sha256(bytes) {
  return Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256', bytes)), value => value.toString(16).padStart(2, '0')).join('');
}
async function document(bytes, descriptor, maxBytes, label) {
  need(bytes instanceof Uint8Array && bytes.byteLength > 0 && bytes.byteLength <= maxBytes, label + '-bytes');
  const ownedBytes = new Uint8Array(bytes);
  need(object(descriptor) && descriptor.bytes === ownedBytes.byteLength && hex(descriptor.sha256) && await sha256(ownedBytes) === descriptor.sha256, label + '-pin');
  return JSON.parse(new TextDecoder('utf-8', {fatal:true}).decode(ownedBytes));
}
const unknown = () => ({state:'unknown', reason:'not-in-qualified-identity-metadata'});

/** Operator-fixed selection. Queries cannot choose a release, index, policy or origin. */
export async function createSourceIdentityReader({selection, manifestBytes, indexBytes, admissionBytes} = {}) {
  need(object(selection), 'fixed-selection-required');
  const fixed = structuredClone(selection);
  const manifest = await document(manifestBytes, fixed.manifest, 128 * 1024, 'manifest');
  need(manifest.schema === IDENTITY_MANIFEST && manifest.status === 'identity-claims-admitted-local' && manifest.scope === 'localhost-only', 'identity-release-not-admitted');
  need(object(manifest.sourceIndex) && hex(manifest.sourceIndex.sha256), 'source-index-evidence-pin');
  need(Array.isArray(manifest.selectedSourceIndexes) && manifest.selectedSourceIndexes.length > 0 && manifest.selectedSourceIndexes.length <= 16 && manifest.selectedSourceIndexes.every(hex) && new Set(manifest.selectedSourceIndexes).size === manifest.selectedSourceIndexes.length, 'selected-source-input-set');
  need(await sha256(new TextEncoder().encode(JSON.stringify(manifest.selectedSourceIndexes))) === manifest.sourceIndex.sha256, 'selected-source-input-set-pin');
  need(manifest.sourceRightsFieldContractSha256 === fixed.sourceRightsFieldContractSha256 && hex(fixed.sourceRightsFieldContractSha256) && manifest.nativeRepresentationQualificationSha256 === fixed.nativeRepresentationQualificationSha256 && hex(fixed.nativeRepresentationQualificationSha256), 'source-rights-role-contract-pins');
  need(manifest.sourceURL === 'https://fdc.nal.usda.gov/download-datasets/', 'qualified-source-notice');
  need(manifest.fieldSet === FIELD_SET && manifest.publicPublicationAccepted === false && manifest.normalizationComplete === false && manifest.goldAdmitted === false, 'identity-release-scope');
  need(manifest.sourceId === fixed.sourceId && manifest.releaseId === fixed.releaseId && manifest.sourceQualificationSha256 === fixed.sourceQualificationSha256, 'fixed-source-selection');
  const admission = await document(admissionBytes, fixed.admission, 64 * 1024, 'admission');
  need(admission.status === 'accepted-local-source-identity-claims' && admission.scope === 'localhost-only' && admission.fieldSet === FIELD_SET, 'identity-operation-not-admitted');
  need(admission.manifestSha256 === fixed.manifest.sha256 && admission.indexSha256 === fixed.index.sha256 && admission.sourceIndexSha256 === manifest.sourceIndex.sha256 && admission.sourceQualificationSha256 === fixed.sourceQualificationSha256, 'admission-release-binding');
  need(admission.sourceRightsFieldContractSha256 === fixed.sourceRightsFieldContractSha256 && admission.nativeRepresentationQualificationSha256 === fixed.nativeRepresentationQualificationSha256 && admission.operation === 'serve-source-identity-claims-local', 'outward-operation-binding');
  need(admission.publicPublicationAccepted === false && admission.runtimeActivation === false, 'no-public-or-runtime-grant');
  const index = await document(indexBytes, fixed.index, 8 * 1024 * 1024, 'index');
  need(index.schema === IDENTITY_INDEX && index.fieldSet === FIELD_SET && index.sourceId === fixed.sourceId && index.releaseId === fixed.releaseId, 'identity-index-release');
  need(manifest.index.sha256 === fixed.index.sha256 && manifest.index.bytes === fixed.index.bytes && index.sourceIndexSha256 === manifest.sourceIndex.sha256, 'identity-index-source-binding');
  need(Array.isArray(index.records) && index.records.length > 0 && index.records.length <= 10000 && index.records.length === manifest.recordCount, 'identity-index-count');
  const seen = new Set(), records = [], byCode = new Map(), byNative = new Map();
  for (const candidate of index.records) {
    const record = validateIdentityRecord(candidate, manifest);
    need(!seen.has(record.stageId), 'duplicate-stage-record');
    seen.add(record.stageId); records.push(record);
    const nativeKey=record.sourceBinding.recordId;
    if (!byNative.has(nativeKey)) byNative.set(nativeKey, []);
    byNative.get(nativeKey).push(record);
    for (const posting of record.barcodePostings) {
      if (!byCode.has(posting.lexicalCode)) byCode.set(posting.lexicalCode, []);
      byCode.get(posting.lexicalCode).push(record);
    }
  }
  need(byCode.size === manifest.sourceDistinctLexicalKeys, 'identity-key-count');
  return Object.freeze({lookup({sourceId, namespace, lexicalValue, offset=0, limit=20} = {}) {
    need(sourceId === fixed.sourceId && ['barcode','USDA-FDC'].includes(namespace) && text(lexicalValue), 'fixed-identity-query');
    need(Number.isSafeInteger(offset) && offset >= 0 && offset <= records.length && Number.isSafeInteger(limit) && limit > 0 && limit <= 20, 'identity-query-bound');
    const matches = (namespace === 'barcode' ? byCode : byNative).get(lexicalValue) || [];
    const page = matches.slice(offset, offset + limit);
    return {
      status:matches.length ? 'source-identity-claims-found' : 'no-selected-source-identity',
      sourceId, namespace, lexicalValue, manifestSha256:fixed.manifest.sha256,
      totalSourceObservations:matches.length,
      nextOffset:offset + page.length < matches.length ? offset + page.length : null,
      records:page.map(record => ({
        schema:'offmenu-source-identity-observation/2',
        stageId:record.stageId, nativeId:record.nativeId, wireSha256:record.wireSha256,
        sourceBinding:structuredClone(record.sourceBinding),
        sourceIdentifiers:structuredClone(record.identifiers), sourceRights:structuredClone(record.sourceRights),
        matchedIdentifier:{namespace, lexicalValue, relationship:'exact-source-claim', representation:'untyped', physicalCarrier:namespace === 'barcode' ? 'unverified' : 'not-applicable', sourceChecksumValid:namespace === 'barcode' ? record.barcodePostings.find(posting => posting.lexicalCode === lexicalValue).checksumValid : null},
        sourceInputIndexSha256:record.sourceInputIndexSha256, rightsVisibilityField:record.rightsVisibilityField, sourceURL:manifest.sourceURL,
        originalProductName:unknown(), originalLanguage:unknown(), englishName:unknown(), foodType:unknown(), nutrition:unknown(),
        canonicalIdentityAccepted:false, identityAssociationAccepted:false, physicalProductEquivalenceAsserted:false,
        normalizationComplete:false, goldAdmitted:false, automaticPlanningEligible:false, recipeNutritionJoinsAccepted:false,
      })),
      externalFallback:false, publicPublicationAccepted:false, normalizationComplete:false, goldAdmitted:false,
    };
  }});
}

// Exactly the existing foundation reader's seven-field source subject.
const SUBJECT = ['sourceId','releaseId','recordId','sourceObservationSha256','sourceDocumentSha256','inputDatabaseSha256','sourceQualificationSha256'];
function subjectKey(binding) {
  need(object(binding) && SUBJECT.every(key => text(binding[key])), 'complete-source-subject');
  for (const key of SUBJECT.filter(key => key.endsWith('Sha256'))) need(hex(binding[key]), 'source-subject-evidence');
  return JSON.stringify(SUBJECT.map(key => binding[key]));
}

/** Compose results from the two fixed readers; never replace a qualified phase row. */
export function composeWithQualifiedPhase(phase, identity) {
  need(object(phase) && object(identity) && Array.isArray(phase.records) && Array.isArray(identity.records), 'source-result-shape');
  need(identity.namespace === 'barcode' && phase.source === identity.sourceId && phase.barcode === identity.lexicalValue, 'same-source-query-required');
  need(phase.fieldContract === 'offmenu-barcode-foundation-phase/2' && hex(phase.manifestSha256) && hex(identity.manifestSha256) && phase.externalFallback === false && identity.externalFallback === false, 'qualified-reader-results-required');
  const found = phase.status === 'phase-qualified-own-data' && phase.httpStatus === 200 && phase.records.length > 0;
  const absent = phase.status === 'own-data-unavailable' && phase.httpStatus === 503 && phase.records.length === 0;
  need(found || absent, 'do-not-mask-phase-technical-failure');
  const phaseSubjects = new Set();
  for (const record of phase.records) {
    need(record.data?.foundationComplete === true, 'qualified-phase-record-required');
    phaseSubjects.add(subjectKey(record.provenance));
  }
  let suppressed = 0;
  const claims = [];
  for (const record of identity.records) {
    need(record.schema === 'offmenu-source-identity-observation/2' && record.canonicalIdentityAccepted === false && record.identityAssociationAccepted === false && record.normalizationComplete === false && record.goldAdmitted === false, 'partial-identity-truth-required');
    if (phaseSubjects.has(subjectKey(record.sourceBinding))) suppressed++;
    else claims.push(structuredClone(record));
  }
  return {
    schema:'offmenu-own-data-observation-composition/1',
    sourceId:identity.sourceId, namespace:'barcode', lexicalValue:identity.lexicalValue,
    phaseResult:structuredClone(phase), sourceIdentityClaims:claims,
    sourceIdentityManifestSha256:identity.manifestSha256,
    sourceClaimsSuppressedForQualifiedSubject:suppressed,
    sourceIdentityClaimsCanonical:false, externalFallback:false,
  };
}
