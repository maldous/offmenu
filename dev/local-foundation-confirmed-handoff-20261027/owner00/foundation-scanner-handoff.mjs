// Source references annotate a user's manually confirmed stock; never product admission.
import {FOUNDATION_HANDOFF_BINDINGS} from './foundation-handoff-bindings.mjs';
export const FOUNDATION_SOURCE_REFERENCE='offmenu-foundation-source-reference/1';
export const FOUNDATION_SCANNER_HANDOFF='offmenu-foundation-scanner-handoff/1';
const SUBJECT=['sourceId','releaseId','recordId','sourceObservationSha256','sourceDocumentSha256','inputDatabaseSha256','sourceQualificationSha256'];
const FLAGS=['normalizationComplete','fullProductComplete','goldAdmitted','automaticPlanningEligible','recipeNutritionJoinsAccepted'];
const SHA=/^[a-f0-9]{64}$/,uuid=v=>typeof v==='string'&&/^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/.test(v);
const object=v=>v!==null&&typeof v==='object'&&!Array.isArray(v);
const text=(v,n)=>typeof v==='string'&&v.length>0&&v.length<=n&&!/[\x00-\x1f\x7f]/.test(v);
const need=(v,message)=>{if(!v)throw Error(message);};
const keys=(v,expected)=>object(v)&&Object.keys(v).length===expected.length&&expected.every(k=>Object.hasOwn(v,k));
function gtin(v){if(typeof v!=='string'||!(/^(?:[0-9]{8}|[0-9]{12}|[0-9]{13}|[0-9]{14})$/).test(v))return false;let sum=0,w=3;for(let i=v.length-2;i>=0;i--){sum+=Number(v[i])*w;w=w===3?1:3;}return (10-sum%10)%10===Number(v.at(-1));}
export function createFoundationHandoffContract(bindings){
 const fixed=structuredClone(bindings);
 need(text(fixed?.releaseId,128)&&SHA.test(fixed.manifestSha256)&&SHA.test(fixed.sourceAdmissionSha256)&&object(fixed.sources),'Fixed foundation handoff selection required.');
 function copyFoundationSourceReference(ref,barcode){
  const expected=['schema','fieldContract','releaseId','manifestSha256','sourceAdmissionSha256','recordId','namespace','lexicalValue','nativeRecordId','stageRecordWireSha256','sourceBinding','license','attribution','foundationComplete',...FLAGS];
  need(keys(ref,expected)&&ref.schema===FOUNDATION_SOURCE_REFERENCE&&ref.fieldContract==='offmenu-barcode-foundation-phase/2'&&ref.releaseId===fixed.releaseId&&ref.manifestSha256===fixed.manifestSha256&&ref.sourceAdmissionSha256===fixed.sourceAdmissionSha256,'Foundation source selection changed.');
  const b=ref.sourceBinding,s=fixed.sources[b?.sourceId];
  need(keys(b,SUBJECT)&&s&&text(b.sourceId,40)&&b.releaseId===s.releaseId&&b.sourceQualificationSha256===s.qualificationSha256&&text(b.recordId,250)&&SUBJECT.slice(3).every(k=>SHA.test(b[k])),'Foundation source subject is incomplete.');
  need(ref.namespace==='barcode'&&gtin(barcode)&&ref.lexicalValue===barcode&&text(ref.recordId,250)&&text(ref.nativeRecordId,250)&&ref.nativeRecordId.startsWith(b.sourceId+':product:')&&SHA.test(ref.stageRecordWireSha256),'Foundation exact barcode or wire binding changed.');
  need(ref.license===s.license&&ref.attribution===s.attribution&&text(ref.license,512)&&text(ref.attribution,512)&&ref.foundationComplete===true&&FLAGS.every(k=>ref[k]===false),'Foundation qualification or source notices changed.');
  return {schema:FOUNDATION_SOURCE_REFERENCE,fieldContract:ref.fieldContract,releaseId:fixed.releaseId,manifestSha256:fixed.manifestSha256,sourceAdmissionSha256:fixed.sourceAdmissionSha256,recordId:ref.recordId,namespace:'barcode',lexicalValue:barcode,nativeRecordId:ref.nativeRecordId,stageRecordWireSha256:ref.stageRecordWireSha256,sourceBinding:Object.fromEntries(SUBJECT.map(k=>[k,b[k]])),license:ref.license,attribution:ref.attribution,foundationComplete:true,...Object.fromEntries(FLAGS.map(k=>[k,false]))};
 }
 const validFoundationSourceReference=(ref,barcode)=>{try{copyFoundationSourceReference(ref,barcode);return true;}catch{return false;}};
 function normalized(item){
  need(keys(item,['operationId','barcode','namespace','symbology','name','brand','userSelected','foundationSourceReference'])&&uuid(item.operationId)&&item.namespace==='barcode'&&item.userSelected===true&&gtin(item.barcode)&&(item.symbology===null||text(item.symbology,128))&&(item.name===null||text(item.name,240))&&(item.brand===null||text(item.brand,240)),'Explicit source choice is required for every kept item.');
  return {operationId:item.operationId,barcode:item.barcode,namespace:'barcode',symbology:item.symbology,name:item.name,brand:item.brand,userSelected:true,foundationSourceReference:copyFoundationSourceReference(item.foundationSourceReference,item.barcode)};
 }
 const foundationHandoffFingerprint=item=>JSON.stringify(normalized(item));
 function parseFoundationScannerHandoff(value){
  need(keys(value,['schema','items'])&&value.schema===FOUNDATION_SCANNER_HANDOFF&&Array.isArray(value.items)&&value.items.length>0&&value.items.length<=20,'Foundation scanner handoff is invalid.');
  const items=value.items.map(normalized);need(new Set(items.map(i=>i.operationId)).size===items.length,'Scanner handoff repeats an operation.');
  const result={schema:FOUNDATION_SCANNER_HANDOFF,items};need(new TextEncoder().encode(JSON.stringify(result)).byteLength<=3000,'Scanner handoff exceeds the existing tab limit. Review a smaller batch.');return result;
 }
 function createFoundationScannerHandoff(queue){
  need(Array.isArray(queue)&&queue.length>0,'Scan at least one item before finishing.');
  return parseFoundationScannerHandoff({schema:FOUNDATION_SCANNER_HANDOFF,items:queue.map(entry=>{
   const selected=entry?.selectedRecord;
   need(entry.foundationLookup===true&&entry.namespace==='barcode'&&entry.sourceChoiceConfirmed===true&&entry.status!=='pending'&&entry.pending!==true&&entry.lookupPending!==true&&entry.matches?.includes(selected),'Choose and confirm a qualified source observation for every kept item.');
   return {operationId:entry.id,barcode:entry.raw,namespace:'barcode',symbology:entry.symbology??null,name:selected.name??null,brand:selected.brand??null,userSelected:true,foundationSourceReference:selected.foundationSourceReference};
  })});
 }
 return Object.freeze({validFoundationSourceReference,copyFoundationSourceReference,foundationHandoffFingerprint,parseFoundationScannerHandoff,createFoundationScannerHandoff});
}
const current=createFoundationHandoffContract(FOUNDATION_HANDOFF_BINDINGS);
export const {validFoundationSourceReference,copyFoundationSourceReference,foundationHandoffFingerprint,parseFoundationScannerHandoff,createFoundationScannerHandoff}=current;
