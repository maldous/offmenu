import test from 'node:test';
import assert from 'node:assert/strict';
import {webcrypto} from 'node:crypto';
import {createSourceIdentityReader, validateIdentityRecord, composeWithQualifiedPhase, sha256, FIELD_SET, IDENTITY_INDEX, IDENTITY_MANIFEST} from './source-identity-reader.mjs';
globalThis.crypto ||= webcrypto;
const h = letter => letter.repeat(64);
const encode = value => new TextEncoder().encode(JSON.stringify(value));
const rights = {attribution:'Synthetic USDA fixture', license:'Synthetic test scope', sourceVisibility:'source-staging'};
const scope = {sourceId:'usda-files', releaseId:'synthetic-1', sourceQualificationSha256:h('a'), sourceRights:rights,selectedSourceIndexes:[h('f')]};
function row(id='1', code='0049022712744') {
  return {
    stageId:'synthetic:stage:'+id, nativeId:'synthetic:native:'+id, wireSha256:h('b'), sourceInputIndexSha256:h('f'), rightsVisibilityField:'sourceVisibility',
    sourceBinding:{inputDatabaseSha256:h('c'), nativeRecordId:'synthetic:native:'+id, recordId:id, releaseId:scope.releaseId, sourceDocumentSha256:h('d'), sourceId:scope.sourceId, sourceObservationSha256:h('e'), sourceQualificationSha256:scope.sourceQualificationSha256},
    identifiers:[{system:'USDA-FDC', value:id},{system:'barcode', value:code}],
    barcodePostings:[{checksumValid:true, lexicalCode:code}], sourceRights:structuredClone(rights),
    canonicalStatus:'unresolved', englishStatus:'unresolved', normalizationComplete:false, goldAdmitted:false,
  };
}
async function fixture({records=[row()], manifestChange=()=>{}, admissionChange=()=>{}, indexChange=()=>{}} = {}) {
  const inputSetSha=await sha256(encode(scope.selectedSourceIndexes));
  const index = {schema:IDENTITY_INDEX, fieldSet:FIELD_SET, sourceId:scope.sourceId, releaseId:scope.releaseId, sourceIndexSha256:inputSetSha, records};
  indexChange(index);
  const indexBytes = encode(index), indexRef = {sha256:await sha256(indexBytes), bytes:indexBytes.length};
  const manifest = {schema:IDENTITY_MANIFEST, status:'identity-claims-admitted-local', scope:'localhost-only', fieldSet:FIELD_SET, ...scope, publicPublicationAccepted:false, normalizationComplete:false, goldAdmitted:false, sourceIndex:{sha256:inputSetSha},sourceRightsFieldContractSha256:h('8'),nativeRepresentationQualificationSha256:h('9'),sourceURL:'https://fdc.nal.usda.gov/download-datasets/', index:indexRef, recordCount:records.length, sourceDistinctLexicalKeys:new Set(records.flatMap(record => record.barcodePostings.map(posting => posting.lexicalCode))).size};
  manifestChange(manifest);
  const manifestBytes = encode(manifest), manifestRef = {sha256:await sha256(manifestBytes), bytes:manifestBytes.length};
  const admission = {status:'accepted-local-source-identity-claims', scope:'localhost-only', fieldSet:FIELD_SET, manifestSha256:manifestRef.sha256, indexSha256:indexRef.sha256, sourceIndexSha256:inputSetSha, sourceQualificationSha256:scope.sourceQualificationSha256, publicPublicationAccepted:false, runtimeActivation:false,sourceRightsFieldContractSha256:h('8'),nativeRepresentationQualificationSha256:h('9'),operation:'serve-source-identity-claims-local'};
  admissionChange(admission);
  const admissionBytes = encode(admission);
  return {selection:{sourceId:scope.sourceId, releaseId:scope.releaseId, sourceQualificationSha256:scope.sourceQualificationSha256,sourceRightsFieldContractSha256:h('8'),nativeRepresentationQualificationSha256:h('9'), manifest:manifestRef, index:indexRef, admission:{sha256:await sha256(admissionBytes), bytes:admissionBytes.length}}, manifestBytes, indexBytes, admissionBytes};
}
const query = {sourceId:'usda-files', namespace:'barcode', lexicalValue:'0049022712744'};

test('identity claim is available without a name, English mapping, food type or nutrition', async () => {
  const reader = await createSourceIdentityReader(await fixture());
  const result = reader.lookup(query);
  assert.equal(result.status, 'source-identity-claims-found');
  assert.equal(result.records.length, 1);
  const record = result.records[0];
  for (const field of ['originalProductName','originalLanguage','englishName','foodType','nutrition']) assert.equal(record[field].state, 'unknown');
  for (const field of ['canonicalIdentityAccepted','identityAssociationAccepted','physicalProductEquivalenceAsserted','normalizationComplete','goldAdmitted','automaticPlanningEligible','recipeNutritionJoinsAccepted']) assert.equal(record[field], false);
  assert.equal(result.externalFallback, false);
  assert.deepEqual(record.sourceBinding, row().sourceBinding);
});

test('prepared release and public/runtime admission cannot start this local reader', async () => {
  await assert.rejects(() => fixture({manifestChange:manifest => {manifest.status='prepared';}}).then(createSourceIdentityReader), /not-admitted/);
  for (const field of ['publicPublicationAccepted','runtimeActivation']) await assert.rejects(() => fixture({admissionChange:admission => {admission[field]=true;}}).then(createSourceIdentityReader), /no-public-or-runtime-grant/);
  await assert.rejects(() => fixture({admissionChange:admission => {admission.scope='public';}}).then(createSourceIdentityReader), /not-admitted/);
});

test('exact source spelling is used, without zero stripping, UPC conversion or ISBN/food inference', async () => {
  const reader = await createSourceIdentityReader(await fixture());
  for (const lexicalValue of ['049022712744','49022712744','00049022712744','9780306406157']) assert.equal(reader.lookup({...query,lexicalValue}).records.length, 0);
  assert.throws(() => reader.lookup({...query,namespace:'ISBN'}), /fixed-identity-query/);
  assert.throws(() => reader.lookup({...query,sourceId:'off'}), /fixed-identity-query/);
  assert.equal(reader.lookup(query).records[0].matchedIdentifier.representation, 'untyped');
});

test('tampered bytes and a receipt bound to a different cut fail before lookup', async () => {
  const input = await fixture();
  input.indexBytes = encode({changed:true});
  await assert.rejects(() => createSourceIdentityReader(input), /index-pin/);
  await assert.rejects(() => fixture({admissionChange:admission => {admission.sourceIndexSha256=h('0');}}).then(createSourceIdentityReader), /admission-release-binding/);
  await assert.rejects(() => fixture({manifestChange:manifest => {manifest.releaseId='other';}}).then(createSourceIdentityReader), /fixed-source-selection/);
});

test('native/source identity, posting membership, provenance and rights cannot be mixed', () => {
  for (const mutate of [
    record => {record.nativeId='foreign';},
    record => {record.sourceBinding.sourceQualificationSha256=h('0');},
    record => {record.sourceBinding.sourceObservationSha256='missing';},
    record => {record.identifiers[0].value='other';},
    record => {record.identifiers[1].value='other';},
    record => {record.sourceRights.license='unqualified';},
    record => {record.barcodePostings[0].checksumValid=false;},
  ]) {
    const record = row(); mutate(record);
    assert.throws(() => validateIdentityRecord(record, scope));
  }
});

test('unqualified extra fields and canonical/normalized claims are refused', () => {
  for (const mutate of [
    record => {record.rawPayload={name:'not admitted'};},
    record => {record.sourceRights.token='not an identifier';},
    record => {record.identifiers.push({system:'credentials',value:'not admitted'});},
    record => {record.normalizationComplete=true;},
    record => {record.goldAdmitted=true;},
    record => {record.canonicalStatus='accepted';},
    record => {record.englishStatus='English';},
  ]) {
    const record = row(); mutate(record);
    assert.throws(() => validateIdentityRecord(record, scope));
  }
});

test('same-code source observations remain separate, with bounded pagination and no physical merge', async () => {
  const reader = await createSourceIdentityReader(await fixture({records:[row('1'),row('2')]}));
  const first = reader.lookup({...query,limit:1});
  assert.equal(first.totalSourceObservations, 2); assert.equal(first.nextOffset, 1);
  const second = reader.lookup({...query,offset:first.nextOffset,limit:1});
  assert.notEqual(first.records[0].stageId, second.records[0].stageId);
  assert.equal(second.nextOffset, null);
  assert.throws(() => reader.lookup({...query,limit:21}), /query-bound/);
  const duplicate = row();
  await assert.rejects(() => fixture({records:[duplicate,structuredClone(duplicate)]}).then(createSourceIdentityReader), /duplicate-stage-record/);
});

test('returned objects and later operator selection mutations cannot change reader state', async () => {
  const input = await fixture(); const reader = await createSourceIdentityReader(input);
  input.selection.sourceId='off';
  const result = reader.lookup(query); result.records[0].sourceIdentifiers.length=0;
  result.records[0].sourceRights.attribution='changed';
  assert.equal(reader.lookup(query).records[0].sourceIdentifiers.length, 2);
  assert.equal(reader.lookup(query).records[0].sourceRights.attribution, rights.attribution);
});

test('invalid source barcode remains an explicitly invalid claim and native FDC identity stays queryable', async () => {
  const record = row('1','123'); record.barcodePostings[0].checksumValid=false;
  record.rightsVisibilityField='visibility';
  const reader = await createSourceIdentityReader(await fixture({records:[record]}));
  const raw = reader.lookup({...query,lexicalValue:'123'});
  assert.equal(raw.records.length, 1);
  assert.equal(raw.records[0].matchedIdentifier.sourceChecksumValid, false);
  assert.equal(raw.records[0].matchedIdentifier.lexicalValue, '123');
  assert.equal(raw.records[0].canonicalIdentityAccepted, false);
  const native = reader.lookup({...query,namespace:'USDA-FDC',lexicalValue:'1'});
  assert.equal(native.records.length, 1);
  assert.equal(native.records[0].matchedIdentifier.sourceChecksumValid, null);
  assert.equal(native.records[0].rightsVisibilityField, 'visibility');
});

test('qualified phase observations are unchanged and suppress only the same complete source subject', async () => {
  const reader = await createSourceIdentityReader(await fixture({records:[row('1'),row('2')]}));
  const identity = reader.lookup(query), original = structuredClone(identity);
  const phase = {fieldContract:'offmenu-barcode-foundation-phase/2',manifestSha256:h('7'),source:'usda-files',barcode:query.lexicalValue,status:'phase-qualified-own-data',httpStatus:200,externalFallback:false,records:[{id:'accepted-phase-row',provenance:row('1').sourceBinding,data:{foundationComplete:true,name:'Separately accepted phase fact'}}]};
  // Real phase DTOs expose recordId in the seven-field subject, not nativeRecordId.
  delete phase.records[0].provenance.nativeRecordId;
  const accepted = structuredClone(phase), result = composeWithQualifiedPhase(phase,identity);
  assert.deepEqual(result.phaseResult, accepted); assert.deepEqual(phase,accepted);
  assert.deepEqual(identity,original);
  assert.equal(result.sourceClaimsSuppressedForQualifiedSubject,1);
  assert.equal(result.sourceIdentityClaims.length,1);
  assert.equal(result.sourceIdentityClaims[0].nativeId,row('2').nativeId);
  assert.throws(()=>composeWithQualifiedPhase({...phase,barcode:'other'},identity),/same-source-query/);
});

test('partial presentation is permitted for an empty selected phase result, but never masks a technical error', async () => {
  const reader = await createSourceIdentityReader(await fixture()), identity = reader.lookup(query);
  const phase = {fieldContract:'offmenu-barcode-foundation-phase/2',manifestSha256:h('7'),source:'usda-files',barcode:query.lexicalValue,status:'own-data-unavailable',httpStatus:503,externalFallback:false,records:[]};
  assert.equal(composeWithQualifiedPhase(phase,identity).sourceIdentityClaims.length,1);
  assert.throws(()=>composeWithQualifiedPhase({...phase,status:'error'},identity),/technical-failure/);
  assert.throws(()=>composeWithQualifiedPhase({...phase,fieldContract:undefined,error:'OWN_DATA_UNAVAILABLE'},identity),/qualified-reader-results/);
});
