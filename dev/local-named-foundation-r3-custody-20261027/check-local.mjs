import fs from 'node:fs';
import path from 'node:path';
import assert from 'node:assert/strict';
import crypto from 'node:crypto';
const R=path.join(import.meta.dirname,'compact-composition-r3'),P=path.dirname(import.meta.dirname);
const {localFoundationResponse}=await import('./compact-composition-r3/consumer/foundation-local-response-with-reference.mjs');
const {copyFoundationSourceReference,validFoundationSourceReference}=await import('./compact-composition-r3/consumer/foundation-scanner-handoff.mjs');
const {createAcceptedFoundationReader}=await import('./compact-composition-r3/corpus/foundation-origin-reader.mjs');
const {LOCAL_SELECTIONS,LOCAL_BLOBS}=await import('./compact-composition-r3/foundation-local-blobs.mjs');
const read=p=>JSON.parse(fs.readFileSync(p)), sha=b=>crypto.createHash('sha256').update(b).digest('hex');
const result={atUTC:new Date().toISOString(),status:'PASS_BOUNDED_DIRECT_LOCAL_FUNCTION_CHECKS_NOT_SERVED_HTTP',requests:[],oldCandidateDataCompared:0,retainedSavedReferencesAccepted:0,preparedRefusal:false};
for(const[source,barcode]of [['off','4061464939738'],['off','12178162'],['usda-files','20026103']]){
 const url='http://127.0.0.1:7645/api/corpus/foundation?'+new URLSearchParams({source,barcode});
 const response=await localFoundationResponse(new Request(url));assert.equal(response.status,200);
 const dto=await response.json();assert.equal(dto.records.length,1);assert.equal(dto.metrics.blobReads,3);
 const record=dto.records[0],ref=record.foundationSourceReference;
 assert.equal(validFoundationSourceReference(ref,barcode),true);assert.deepEqual(copyFoundationSourceReference(ref,barcode),ref);
 assert.equal(dto.externalFallback,false);assert.equal(record.data.goldAdmitted,false);assert.equal(record.data.normalizationComplete,false);
 assert.equal(record.data.automaticPlanningEligible,false);assert.equal(record.data.recipeNutritionJoinsAccepted,false);
 assert.equal(ref.manifestSha256,LOCAL_SELECTIONS[source].manifest.sha256);
 if(barcode==='4061464939738'){
  assert.equal(record.data.canonicalEnglishKey,'beetroot');assert.equal(record.data.meaningfulType.conceptId,'urn:offmenu:type:sliced-beetroot');
  assert.equal(record.data.variantParameters.form.value,'sliced');assert.equal(record.data.variantParameters.form.evidenceKind,'source-name-declared');
  assert.equal(Object.values(record.data.variantParameters).filter(p=>p.state==='unknown').length,23);
 }else{
  const old=read(path.join(P,'local7645-foundation-root14-r1/consumer-source-example-'+source+'.json')).dto.records[0];
  const copy=structuredClone(record);delete copy.foundationSourceReference;
  assert.deepEqual(copy,old);result.oldCandidateDataCompared++;
 }
 const head=await localFoundationResponse(new Request(url,{method:'HEAD'}));assert.equal(head.status,200);assert.equal(await head.text(),'');
 result.requests.push({source,barcode,status:response.status,recordCount:dto.records.length,manifestSha256:dto.manifestSha256,bodySha256:sha(Buffer.from(JSON.stringify(dto))),blobReads:dto.metrics.blobReads,foundationComplete:record.data.foundationComplete,Gold:record.data.goldAdmitted,normalizationComplete:record.data.normalizationComplete,headBodyless:true});
 fs.writeFileSync(path.join(R,'response-'+source+'-'+barcode+'.json'),JSON.stringify(dto,null,2)+'\n',{flag:'wx'});
}
for(const source of ['off','usda-files']){
 const example=read(path.join(P,'local7645-foundation-root14-r1/confirmed-handoff-r1/reference-example-'+source+'.json'));
 const ref=example.records[0].foundationSourceReference;
 assert.equal(validFoundationSourceReference(ref,ref.lexicalValue),true);result.retainedSavedReferencesAccepted++;
}
const absent=await localFoundationResponse(new Request('http://127.0.0.1:7645/api/corpus/foundation?source=off&barcode=00000000'));
assert.equal(absent.status,503);assert.equal((await absent.json()).externalFallback,false);
const prepared=fs.readFileSync(path.join(R,'manifest.prepared.json')),selection=structuredClone(LOCAL_SELECTIONS.off);
selection.manifest={...selection.manifest,bytes:prepared.length,sha256:sha(prepared)};
let reads=0;
await assert.rejects(()=>createAcceptedFoundationReader(async(key)=>{reads++;return key===selection.manifest.key?prepared:Buffer.from(LOCAL_BLOBS[key].bodyBase64,'base64');},selection),/not admitted/);
assert.equal(reads,1);result.preparedRefusal=true;
result.effects='Direct functions and public-derived selected blobs only; no HTTP socket/server/currentapp/account/profile/nativeDB/network/provider/classifier/matcher/sourcepass or runtime action.';
fs.writeFileSync(path.join(R,'bounded-local-service-check-result.json'),JSON.stringify(result,null,2)+'\n',{flag:'wx'});console.log(JSON.stringify(result));
