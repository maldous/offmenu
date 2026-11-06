// A source reference annotates manually confirmed personal stock. It is not a
// foundation record, source admission, normalized ingredient or product identity.
import {copyFoundationSourceReference} from './foundation-scanner-handoff.mjs';
import {validateIdentitySelection,validateSourceIdentityWire} from './production-scanner/source-identity-client.mjs';
import {SOURCE_IDENTITY_SELECTION} from './production-scanner/source-identity-selection.mjs';

export const SOURCE_IDENTITY_REFERENCE='offmenu-source-identity-reference/1';
export const OWNED_SOURCE_SCANNER_HANDOFF='offmenu-owned-source-scanner-handoff/1';
// The old public/foundation envelopes keep their existing 3,000-byte contract.
// This distinct envelope retains full provenance for up to the same 20 choices.
export const OWNED_SOURCE_HANDOFF_LIMIT=64*1024;
const object=v=>v!==null&&typeof v==='object'&&!Array.isArray(v);
const text=(v,n)=>typeof v==='string'&&v.length>0&&v.length<=n&&!/[\x00-\x1f\x7f]/.test(v);
const uuid=v=>typeof v==='string'&&/^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/.test(v);
const keys=(v,expected)=>object(v)&&Object.keys(v).length===expected.length&&expected.every(k=>Object.hasOwn(v,k));
const stable=v=>Array.isArray(v)?'['+v.map(stable).join(',')+']':object(v)?'{'+Object.keys(v).sort().map(k=>JSON.stringify(k)+':'+stable(v[k])).join(',')+'}':JSON.stringify(v);
const need=(v,message)=>{if(!v)throw Error(message);};

export function createOwnedSourceHandoffContract(selection,{copyFoundation=copyFoundationSourceReference}={}){
 let fixed=null;try{fixed=validateIdentitySelection(selection);}catch{}
 function copySourceIdentityReference(ref,raw,namespace=ref?.observation?.matchedIdentifier?.namespace){
  need(fixed,'SOURCE_IDENTITY_NOT_CONFIGURED');
  need(keys(ref,['schema','selectionSha256','admissionSha256','manifestSha256','observation'])&&ref.schema===SOURCE_IDENTITY_REFERENCE&&ref.selectionSha256===fixed.selectionSha256&&ref.admissionSha256===fixed.admissionSha256&&ref.manifestSha256===fixed.manifestSha256,'Source identity selection changed.');
  // Reuse the exact transport validator rather than a second observation parser.
  // This validation envelope does not issue admission: all pins must match the
  // operator-fixed selection already required by the existing source client.
  const status='source-identity-claims-found';
  const checked=validateSourceIdentityWire({schema:'offmenu-source-identity-http/1',kind:'source-identifier-claims',httpStatus:200,status,selectionSha256:fixed.selectionSha256,admissionSha256:fixed.admissionSha256,
   readerResult:{status,sourceId:fixed.sourceId,namespace,lexicalValue:raw,manifestSha256:fixed.manifestSha256,totalSourceObservations:1,nextOffset:null,records:[ref.observation],externalFallback:false,publicPublicationAccepted:false,normalizationComplete:false,goldAdmitted:false}},
   {namespace,value:raw,offset:0,limit:1},fixed);
  return {schema:SOURCE_IDENTITY_REFERENCE,selectionSha256:fixed.selectionSha256,admissionSha256:fixed.admissionSha256,manifestSha256:fixed.manifestSha256,observation:JSON.parse(stable(checked.records[0]))};
 }
 function sourceReferenceFromChoice(entry){
  const record=entry.selectedRecord?.sourceIdentityRecord,state=entry.identityState;
  need(state&&state.namespace===entry.namespace&&state.lexicalValue===entry.raw&&state.generation===(entry.queryGeneration??entry.generation)&&Array.isArray(state.records)&&state.records.some(r=>stable(r)===stable(record)),'Selected source observation is not in this lookup.');
  return copySourceIdentityReference({schema:SOURCE_IDENTITY_REFERENCE,selectionSha256:state.selectionSha256,admissionSha256:state.admissionSha256,manifestSha256:state.manifestSha256,observation:record},entry.raw,entry.namespace);
 }
 function normalized(item){
  const identity=Object.hasOwn(item??{},'sourceIdentityReference');
  const reference=identity?'sourceIdentityReference':'foundationSourceReference';
  need(keys(item,['operationId','barcode','namespace','symbology','name','brand','userSelected',reference])&&uuid(item.operationId)&&text(item.barcode,512)&&item.userSelected===true&&(item.symbology===null||text(item.symbology,128))&&(item.name===null||text(item.name,240))&&(item.brand===null||text(item.brand,240)),'Explicit source choice is required for every kept item.');
  need(identity?['barcode','USDA-FDC'].includes(item.namespace)&&item.name===null&&item.brand===null:item.namespace==='barcode','Source identity must not acquire a product name or type.');
  const ref=identity?copySourceIdentityReference(item[reference],item.barcode,item.namespace):copyFoundation(item[reference],item.barcode);
  return {operationId:item.operationId,barcode:item.barcode,namespace:item.namespace,symbology:item.symbology,name:item.name,brand:item.brand,userSelected:true,[reference]:ref};
 }
 const ownedSourceHandoffFingerprint=item=>stable(normalized(item));
 function parseOwnedSourceScannerHandoff(value){
  need(keys(value,['schema','items'])&&value.schema===OWNED_SOURCE_SCANNER_HANDOFF&&Array.isArray(value.items)&&value.items.length>0&&value.items.length<=20,'Owned source scanner handoff is invalid.');
  const items=value.items.map(normalized);need(new Set(items.map(i=>i.operationId)).size===items.length,'Scanner handoff repeats an operation.');
  const result={schema:OWNED_SOURCE_SCANNER_HANDOFF,items};
  need(new TextEncoder().encode(JSON.stringify(result)).byteLength<=OWNED_SOURCE_HANDOFF_LIMIT,'Source handoff exceeds the bounded tab payload. Nothing was dropped.');
  return result;
 }
 function createOwnedSourceScannerHandoff(queue){
  need(Array.isArray(queue)&&queue.length>0,'Scan at least one item before finishing.');
  return parseOwnedSourceScannerHandoff({schema:OWNED_SOURCE_SCANNER_HANDOFF,items:queue.map(entry=>{
   const selected=entry?.selectedRecord;
   need(entry.foundationLookup===true&&entry.sourceChoiceConfirmed===true&&entry.status!=='pending'&&entry.pending!==true&&entry.lookupPending!==true&&entry.matches?.includes(selected),'Choose and confirm a source observation for every kept item.');
   const identity=selected.kind==='source-identity';
   return {operationId:entry.id,barcode:entry.raw,namespace:entry.namespace,symbology:entry.symbology??null,name:identity?null:selected.name??null,brand:identity?null:selected.brand??null,userSelected:true,
    ...(identity?{sourceIdentityReference:sourceReferenceFromChoice(entry)}:{foundationSourceReference:selected.foundationSourceReference})};
  })});
 }
 return Object.freeze({copySourceIdentityReference,ownedSourceHandoffFingerprint,parseOwnedSourceScannerHandoff,createOwnedSourceScannerHandoff});
}
const current=createOwnedSourceHandoffContract(SOURCE_IDENTITY_SELECTION);
export const {copySourceIdentityReference,ownedSourceHandoffFingerprint,parseOwnedSourceScannerHandoff,createOwnedSourceScannerHandoff}=current;
