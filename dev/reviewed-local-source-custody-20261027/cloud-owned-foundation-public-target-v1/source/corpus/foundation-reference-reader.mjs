// The existing owner00 reference extension, unchanged except export/import paths.
import {createAcceptedFoundationReader,foundationDigest} from './foundation-origin-reader.mjs';
import {copyFoundationSourceReference,FOUNDATION_SOURCE_REFERENCE} from '../public/foundation-scanner-handoff.mjs';
const SUBJECT=['sourceId','releaseId','recordId','sourceObservationSha256','sourceDocumentSha256','inputDatabaseSha256','sourceQualificationSha256'];
const need=value=>{if(!value)throw Error('LOCAL_FOUNDATION_REFERENCE_UNAVAILABLE');};
async function productPartition(bytes,d){
 need(Number.isSafeInteger(d.uncompressedBytes)&&d.uncompressedBytes>0&&d.uncompressedBytes<=2097152&&await foundationDigest(bytes)===d.sha256);
 const stream=new Blob([bytes]).stream().pipeThrough(new DecompressionStream('gzip')).getReader();let total=0;const chunks=[];
 try{while(true){const {done,value}=await stream.read();if(done)break;total+=value.byteLength;need(total<=d.uncompressedBytes);chunks.push(value);}}finally{await stream.cancel();}
 need(total===d.uncompressedBytes);const raw=new Uint8Array(total);let offset=0;for(const value of chunks){raw.set(value,offset);offset+=value.byteLength;}
 return JSON.parse(new TextDecoder('utf-8',{fatal:true}).decode(raw));
}
export async function readerWithReferences(blob,selection){
 const observed=new Map();
 const reader=await createAcceptedFoundationReader(async(key,d)=>{
  const bytes=await blob(key,d);
  if(key.endsWith('.json.gz')&&key.includes('/products/')){
   const p=await productPartition(bytes,d);
   need(p.schema==='offmenu-foundation-products/2'&&p.sourceId===selection.sourceId&&p.policySha256===selection.policy.sha256&&p.entries&&typeof p.entries==='object'&&!Array.isArray(p.entries));
   for(const [barcode,rows]of Object.entries(p.entries)){
    need(Array.isArray(rows));
    for(const row of rows){const id=JSON.stringify([barcode,row.id]);need(!observed.has(id));observed.set(id,row.candidate);}
   }
  }
  return bytes;
 },selection);
 return {lookup:async query=>{
  const dto=await reader.lookup(query);
  for(const record of dto.records){
   const c=observed.get(JSON.stringify([query.barcode,record.id])),i=c?.identity,p=record.provenance;
   need(i&&i.stageRecordId===record.id&&c.barcode===query.barcode&&i.lexicalValue===query.barcode&&SUBJECT.every(k=>i.sourceBinding[k]===p[k]));
   record.foundationSourceReference=copyFoundationSourceReference({schema:FOUNDATION_SOURCE_REFERENCE,fieldContract:dto.fieldContract,releaseId:selection.releaseId,manifestSha256:selection.manifest.sha256,sourceAdmissionSha256:selection.admissionReceiptSha256,recordId:record.id,namespace:i.namespace,lexicalValue:i.lexicalValue,nativeRecordId:i.nativeRecordId,stageRecordWireSha256:i.stageRecordWireSha256,sourceBinding:Object.fromEntries(SUBJECT.map(k=>[k,i.sourceBinding[k]])),license:p.license,attribution:p.attribution,foundationComplete:true,normalizationComplete:false,fullProductComplete:false,goldAdmitted:false,automaticPlanningEligible:false,recipeNutritionJoinsAccepted:false},query.barcode);
  }
  return dto;
 }};
}
