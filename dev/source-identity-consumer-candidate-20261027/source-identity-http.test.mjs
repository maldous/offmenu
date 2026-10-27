import test from 'node:test';
import assert from 'node:assert/strict';
import {webcrypto} from 'node:crypto';
import {createSourceIdentityHTTP,HTTP_SCHEMA} from './source-identity-http.mjs';
import {sha256,FIELD_SET,IDENTITY_INDEX,IDENTITY_MANIFEST} from './source-identity-reader.mjs';
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

const base='http://localhost:7645/api/corpus/source-identity?source=usda-files&namespace=barcode&value=0049022712744';
const request=(url=base,options)=>new Request(url,options);
test('synthetic admitted claim serves exact lexical IDs/unknowns without phase, name, type or nutrition',async()=>{
 const http=await createSourceIdentityHTTP(await fixture());const r=await http.handle(request());assert.equal(r.status,200);const d=await r.json();assert.equal(d.schema,HTTP_SCHEMA);assert.equal(d.kind,'source-identifier-claims');assert.equal(d.readerResult.records.length,1);assert.equal(d.readerResult.lexicalValue,'0049022712744');assert.equal(d.readerResult.records[0].originalProductName.state,'unknown');assert.equal(d.readerResult.records[0].foodType.state,'unknown');assert.equal(d.readerResult.records[0].goldAdmitted,false);assert.equal(r.headers.get('Access-Control-Allow-Origin'),null);assert.equal(r.headers.get('Cache-Control'),'no-store');
});
test('only exact localhost/127 origin+optional matchingOrigin, no CORS or other host/scheme/port',async()=>{
 const http=await createSourceIdentityHTTP(await fixture());
 for(const origin of ['http://localhost:7645','http://127.0.0.1:7645']){const u=base.replace('http://localhost:7645',origin);assert.equal((await http.handle(request(u,{headers:{Origin:origin}}))).status,200);}
 for(const origin of ['https://localhost:7645','http://localhost:7646','http://example.test:7645'])assert.equal((await http.handle(request(base.replace('http://localhost:7645',origin)))).status,403);
 assert.equal((await http.handle(request(base,{headers:{Origin:'http://127.0.0.1:7645'}}))).status,403);
});
test('unknown/duplicate params, invalid pagination/source/ns and controls rejected without repair',async()=>{
 const http=await createSourceIdentityHTTP(await fixture());
 for(const u of [base+'&source=usda-files',base+'&manifest=x',base+'&limit=21',base+'&offset=01',base+'&offset=-1',base+'&offset=2',base.replace('source=usda-files','source=off'),base.replace('namespace=barcode','namespace=ISBN'),base.replace('value=0049022712744','value=%00')])assert.equal((await http.handle(request(u))).status,400,u);
 assert.equal((await(await http.handle(request(base.replace('0049022712744','49022712744')))).json()).readerResult.records.length,0);
});
test('HEAD has exact GET metadata and no body; method/unrelatedroute stay bounded',async()=>{
 const http=await createSourceIdentityHTTP(await fixture());const g=await http.handle(request());const h=await http.handle(request(base,{method:'HEAD'}));assert.equal(h.status,200);assert.equal(await h.text(),'');assert.equal(h.headers.get('Content-Length'),g.headers.get('Content-Length'));assert.equal(h.headers.get('Content-Type'),g.headers.get('Content-Type'));assert.equal((await http.handle(request(base,{method:'POST'}))).status,405);assert.equal(await http.handle(request('http://localhost:7645/api/corpus/foundation')),null);
});
test('prepared/wrongcut admission refuses construction, without request/network/runtime',async()=>{
 await assert.rejects(()=>fixture({manifestChange:m=>{m.status='prepared';}}).then(createSourceIdentityHTTP),/not-admitted/);
 await assert.rejects(()=>fixture({admissionChange:a=>{a.manifestSha256=h('0');}}).then(createSourceIdentityHTTP),/admission-release-binding/);
});
test('explicit FDC native identity and source-scoped empty remain separate from canonical eligibility',async()=>{
 const http=await createSourceIdentityHTTP(await fixture());const d=await(await http.handle(request(base.replace('namespace=barcode&value=0049022712744','namespace=USDA-FDC&value=1')))).json();assert.equal(d.readerResult.records[0].matchedIdentifier.physicalCarrier,'not-applicable');assert.equal(d.readerResult.records[0].automaticPlanningEligible,false);
 const empty=await(await http.handle(request(base.replace('0049022712744','0000000000000')))).json();assert.equal(empty.httpStatus,200);assert.equal(empty.readerResult.status,'no-selected-source-identity');assert.equal(empty.readerResult.totalSourceObservations,0);assert.equal(empty.readerResult.externalFallback,false);
});
test('bounded independent pagination and operator selection isolation',async()=>{
 const input=await fixture({records:[row('1'),row('2')]});const http=await createSourceIdentityHTTP(input);input.selection.admission.sha256=h('0');
 const a=await(await http.handle(request(base+'&limit=1'))).json();const b=await(await http.handle(request(base+'&limit=1&offset=1'))).json();assert.equal(a.readerResult.nextOffset,1);assert.equal(b.readerResult.nextOffset,null);assert.notEqual(a.readerResult.records[0].stageId,b.readerResult.records[0].stageId);assert.equal(a.selectionSha256,b.selectionSha256);assert.notEqual(a.admissionSha256,h('0'));
});

test('caller mutation during asynchronous construction cannot replace verified bytes or reported pins',async()=>{
 const input=await fixture();const selected=structuredClone(input.selection);const starting=createSourceIdentityHTTP(input);
 input.selection.admission.sha256=h('0');input.manifestBytes.fill(32);input.indexBytes.fill(32);input.admissionBytes.fill(32);
 const http=await starting;const data=await(await http.handle(request())).json();assert.equal(data.readerResult.records.length,1);assert.equal(data.admissionSha256,selected.admission.sha256);assert.equal(data.readerResult.manifestSha256,selected.manifest.sha256);
});
