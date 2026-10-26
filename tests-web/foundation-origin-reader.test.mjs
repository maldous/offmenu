import test from'node:test';import assert from'node:assert/strict';import {gzipSync}from'node:zlib';
import{createAcceptedFoundationReader,foundationDigest}from'../corpus/foundation-origin-reader.mjs';
const h=x=>x.repeat(64),enc=new TextEncoder(),barcode='0036000291452';
async function fixture({prepared=false,badRecord=false}={}){
  const files=new Map(),reads=[];const namespace='own-data/foundation/generated-1/';
  async function file(name,value,zip=false){const raw=enc.encode(JSON.stringify(value)),bytes=zip?new Uint8Array(gzipSync(raw)):raw,key=namespace+name;files.set(key,bytes);return{key,bytes:bytes.length,sha256:await foundationDigest(bytes),...(zip?{uncompressedBytes:raw.length}:{})};}
  const binding={sourceId:'off',releaseId:'generated-source',recordId:'generated:1',sourceObservationSha256:h('1'),sourceDocumentSha256:h('2'),inputDatabaseSha256:h('3'),sourceQualificationSha256:h('4')};
  const evidence=kind=>[{kind,pointer:'/generated/source-field',sourceBinding:structuredClone(binding)}];
  const stamp={state:'reviewed',registrySha256:h('a'),independentReviewSha256:h('b'),evidence:evidence('source-field')};
  const type={typeKey:'milk-products',canonicalEnglishLabel:'Milk products',conceptId:'generated:milk-products',relationshipId:'generated:milk-is-a-milk-product',relationshipKind:'is-a',subjectConceptId:'generated:milk',registrySha256:h('5'),independentReviewSha256:h('6')};
  const policyValue={schema:'offmenu-barcode-foundation-phase/2',registrySha256:h('a'),independentReviewSha256:h('b'),sourceQualifications:{off:{releaseId:'generated-source',qualificationSha256:h('4')}},definitions:{milk:{classification:'ingredient',canonicalEnglishLabel:'Milk',conceptId:'generated:milk',typeKey:'milk-products',typeRelation:type,parameters:{fatPercentage:{kind:'number'}}}}};
  const candidate={barcode,identity:{namespace:'barcode',lexicalValue:barcode,nativeRecordId:'generated:1',stageRecordId:'generated-stage-1',stageRecordWireSha256:h('7'),sourceBinding:binding},classification:{...stamp,value:'ingredient'},base:{...stamp,canonicalEnglishKey:'milk',canonicalEnglishLabel:'Milk',conceptId:'generated:milk',typeKey:'milk-products'},type:{state:'reviewed',...type,evidence:evidence('reviewed-type-rule')},parameters:{fatPercentage:{state:'unknown',reason:'not-provided-in-qualified-representation',evidence:evidence('qualified-representation-omission')}}};
  if(badRecord)candidate.identity.sourceBinding.sourceQualificationSha256=h('f');
  const row={schema:'offmenu-foundation-product/2',id:'generated-stage-1',candidate};const other=structuredClone(row);other.id=other.candidate.identity.stageRecordId='generated-stage-2';
  const policy=await file('policy.json',policyValue),partition=await file('off/part.json.gz',{schema:'offmenu-foundation-products/2',sourceId:'off',policySha256:policy.sha256,entries:{[barcode]:[row,other]}},true);
  const prefix=(await foundationDigest(enc.encode(barcode))).slice(0,2);
  const manifestValue={schema:'offmenu-foundation-publication/2',releaseId:'generated-1',status:prepared?'prepared':'phase-qualified-release-ready',fieldContract:'offmenu-barcode-foundation-phase/2',policySha256:policy.sha256,consumerCodeSha256:h('c'),acceptance:{status:'selected-phase-records-exercised',receiptSha256:h('d')},privateProviderData:false,rawSourcePayloadPublished:false,acquisitionAtRuntime:false,goldAdmitted:false,fullProductComplete:false,legacyCuratedAdmission:false,sources:{off:{sourceId:'off',releaseId:'generated-source',license:'GENERATED',attribution:'GENERATED',qualificationSha256:h('4'),partitions:{[prefix]:partition}}}};
  const manifest=await file('manifest.json',manifestValue),selection={manifest,policy,sourceId:'off',releaseId:'generated-1',consumerCodeSha256:h('c'),admissionReceiptSha256:h('d')};
  const readBlob=async(key,desc)=>{reads.push({key,cache:desc.cachePolicy});return files.get(key)};
  return{selection,readBlob,reads,files,partition,manifestValue};
}
test('explicit foundation namespace serves re-assessed source-scoped records, unknown fat and no later-phase admission',async()=>{
  const f=await fixture(),reader=await createAcceptedFoundationReader(f.readBlob,f.selection),r=await reader.lookup({source:'off',barcode});
  assert.equal(r.httpStatus,200);assert.equal(r.records.length,2);assert.equal(r.records[0].data.name,'Milk');assert.equal(r.records[0].data.variantParameters.fatPercentage.state,'unknown');
  assert.equal(r.records[0].data.goldAdmitted,false);assert.equal(r.records[0].curation.legacyCuratedAdmission,false);assert.equal(r.externalFallback,false);assert.equal(f.reads.length,3);assert.ok(f.reads.every(r=>r.cache==='no-store'));
});
test('prepared publication is rejected before policy or product access',async()=>{
  const f=await fixture({prepared:true});await assert.rejects(()=>createAcceptedFoundationReader(f.readBlob,f.selection),/not admitted/);assert.equal(f.reads.length,1);
});
test('fixed source and cursor bind the exact publication, policy, barcode and page size',async()=>{
  const f=await fixture(),reader=await createAcceptedFoundationReader(f.readBlob,f.selection),r=await reader.lookup({source:'off',barcode,limit:1});assert.ok(r.nextCursor);
  await assert.rejects(()=>reader.lookup({source:'usda-files',barcode}),/selected foundation/);
  await assert.rejects(()=>reader.lookup({source:'off',barcode:'036000291452',limit:1,cursor:r.nextCursor}),/another lookup/);
  await assert.rejects(()=>reader.lookup({source:'off',barcode,limit:2,cursor:r.nextCursor}),/another lookup/);
  const next=await reader.lookup({source:'off',barcode,limit:1,cursor:r.nextCursor});assert.equal(next.records[0].id,'generated-stage-2');assert.equal(next.nextCursor,null);
});
test('checksummed products are revalidated against source qualification rather than trusting stored completion flags',async()=>{
  const f=await fixture({badRecord:true}),reader=await createAcceptedFoundationReader(f.readBlob,f.selection);await assert.rejects(()=>reader.lookup({source:'off',barcode}),/source\/identity/);
});
test('tampered bytes and namespace traversal cannot be read as foundation publications',async()=>{
  const f=await fixture();f.files.set(f.selection.manifest.key,enc.encode('{}'));await assert.rejects(()=>createAcceptedFoundationReader(f.readBlob,f.selection),/checksum/);
  f.selection.manifest.key='own-data/foundation/../private/manifest.json';await assert.rejects(()=>createAcceptedFoundationReader(f.readBlob,f.selection),/descriptor/);
});
