import fs from 'node:fs';import path from 'node:path';import assert from 'node:assert/strict';import crypto from 'node:crypto';import{gunzipSync}from'node:zlib';
import{localFoundationResponse}from'./consumer/foundation-local-response-with-reference.mjs';
import{validFoundationSourceReference}from'./consumer/foundation-scanner-handoff.mjs';
import{createAcceptedFoundationReader}from'./corpus/foundation-origin-reader.mjs';
import{LOCAL_SELECTIONS,LOCAL_BLOBS}from'./foundation-local-blobs.mjs';
const R=import.meta.dirname,P=path.dirname(R),OLD=path.join(P,'local7645-named-foundation-r3-20261027/compact-composition-r3');
const rows=gunzipSync(fs.readFileSync('/home/user/src/offmenu-data/runtime/layout-migration/worker19/remaining-held-public-english-serving-20261026/reviewed86-r8-application/closed-r8-phase-projection-v1/new-only-candidates.jsonl.gz')).toString().trim().split('\n').map(JSON.parse);
const selected=[...new Map(rows.map(v=>[v.family,v])).values()].map(v=>({source:'off',barcode:v.barcode,family:v.family}));assert.equal(selected.length,3);
selected.push({source:'off',barcode:'4061464939738',old:true},{source:'off',barcode:'12178162',old:true},{source:'usda-files',barcode:'20026103',old:true});
const sha=b=>crypto.createHash('sha256').update(b).digest('hex'),result={atUTC:new Date().toISOString(),status:'PASS_SIX_BOUNDED_DIRECT_FUNCTION_QUERIES_NOT_SERVED',observations:[],oldDTOsPreserved:0,retainedSavedRefs:0};
for(const item of selected){
 const url='http://127.0.0.1:7645/api/corpus/foundation?'+new URLSearchParams({source:item.source,barcode:item.barcode});
 const response=await localFoundationResponse(new Request(url));assert.equal(response.status,200);const dto=await response.json();assert.equal(dto.records.length,1);assert.equal(dto.metrics.blobReads,3);
 const record=dto.records[0];assert.equal(validFoundationSourceReference(record.foundationSourceReference,item.barcode),true);assert.equal(record.foundationSourceReference.manifestSha256,LOCAL_SELECTIONS[item.source].manifest.sha256);
 assert.equal(dto.externalFallback,false);for(const flag of ['goldAdmitted','normalizationComplete','automaticPlanningEligible','recipeNutritionJoinsAccepted'])assert.equal(record.data[flag],false);
 if(item.old){const before=JSON.parse(fs.readFileSync(path.join(OLD,'response-'+item.source+'-'+item.barcode+'.json'))).records[0],a=structuredClone(record),b=structuredClone(before);delete a.foundationSourceReference;delete b.foundationSourceReference;assert.deepEqual(a,b);assert.equal(validFoundationSourceReference(before.foundationSourceReference,item.barcode),true);result.oldDTOsPreserved++;result.retainedSavedRefs++;}
 else{assert.equal(Object.values(record.data.variantParameters).filter(v=>v.state==='unknown').length,24);assert.equal(record.data.foundationComplete,true);}
 const head=await localFoundationResponse(new Request(url,{method:'HEAD'}));assert.equal(head.status,200);assert.equal(await head.text(),'');
 result.observations.push({...item,status:200,manifestSha256:dto.manifestSha256,recordCount:1,bodySha256:sha(Buffer.from(JSON.stringify(dto))),blobReads:3,headBodyless:true});
 fs.writeFileSync(path.join(R,'response-'+item.source+'-'+item.barcode+'.json'),JSON.stringify(dto,null,2)+'\n',{flag:'wx'});
}
const prepared=fs.readFileSync(path.join(R,'manifest.prepared.json')),selection=structuredClone(LOCAL_SELECTIONS.off);selection.manifest={...selection.manifest,bytes:prepared.length,sha256:sha(prepared)};let reads=0;
await assert.rejects(()=>createAcceptedFoundationReader(async key=>{reads++;return key===selection.manifest.key?prepared:Buffer.from(LOCAL_BLOBS[key].bodyBase64,'base64');},selection),/not admitted/);assert.equal(reads,1);result.preparedRefusedBeforePolicyRead=true;
result.effects='Direct pure functions/public-derived blobs only; no HTTP socket/server/currentapp/account/profile/nativeDB/network/provider/classifier/rawsource/runtime.';
fs.writeFileSync(path.join(R,'bounded-local-service-check-result.json'),JSON.stringify(result,null,2)+'\n',{flag:'wx'});console.log(JSON.stringify(result));
