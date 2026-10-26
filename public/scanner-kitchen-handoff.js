import {analyzeIdentifier} from './typed-identifier-contract.mjs';
// The existing tab handoff and checkout store remain the only persistence route.
export const SCANNER_HANDOFF_KEY='offmenu-scanner-kitchen-pending-v1';
export const PUBLIC_SCANNER_HANDOFF='offmenu-scanner-kitchen-handoff/2';
export const PUBLIC_PRODUCT_REFERENCE='offmenu-published-product-reference/1';
export const SCANNER_COMPLETION='offmenu-public-scanner-completion/1';
export const HANDOFF_LIMIT=3000;
export const PUBLIC_PRODUCT_SELECTION=Object.freeze({sourceId:'off',releaseId:'offmenu-off-selected-products-20261025-v1',manifestSha256:'1bf09a371a164ebd8215fd9b44a1b2ac9816caaa65cd13504086defad76d4e8f'});
const uuid=v=>typeof v==='string'&&/^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/.test(v);
const text=(v,n)=>typeof v==='string'&&v.length>0&&v.length<=n&&!/[\x00-\x1f\x7f]/.test(v);
const optional=(v,n)=>v===null||text(v,n);
const barcode=v=>typeof v==='string'&&/^\d{4,32}$/.test(v);
const web=v=>{if(v==null)return true;if(!text(v,700))return false;try{const u=new URL(v);return u.protocol==='https:'&&!u.username&&!u.password&&(u.href===v||v===u.origin);}catch{return false;}};
function validLexicalBinding(ref,raw){
 if(!text(raw,128))return false;
 if(ref?.lexicalValue===raw)return barcode(raw)&&ref.capturedLexicalValue===undefined&&ref.representationHint===undefined;
 if(ref?.capturedLexicalValue!==raw||typeof ref.representationHint!=='string'||!barcode(ref.lexicalValue))return false;
 const typed=analyzeIdentifier({original:raw,namespace:'barcode',representationHint:ref.representationHint});
 return typed.status==='checksum-valid'&&typed.labelledEquivalents.some(form=>form.value===ref.lexicalValue);
}
export function validPublicProductReference(ref,raw){
 const p=ref?.provenance;
 return ref?.schema===PUBLIC_PRODUCT_REFERENCE&&ref.sourceId===PUBLIC_PRODUCT_SELECTION.sourceId&&ref.releaseId===PUBLIC_PRODUCT_SELECTION.releaseId&&ref.manifestSha256===PUBLIC_PRODUCT_SELECTION.manifestSha256&&text(ref.recordId,200)&&ref.recordId.startsWith('offmenu:')&&ref.namespace==='barcode'&&validLexicalBinding(ref,raw)&&p?.sourceId==='off'&&p.visibility==='public'&&text(p.license,160)&&text(p.attribution,240)&&web(p.url)&&web(p.licenseUrl)&&optional(p.sourceDate,80);
}
export function copyPublicProductReference(ref,raw){
 if(!validPublicProductReference(ref,raw))throw Error('Published source reference does not match the selected barcode and release.');
 return {schema:PUBLIC_PRODUCT_REFERENCE,sourceId:ref.sourceId,releaseId:ref.releaseId,manifestSha256:ref.manifestSha256,recordId:ref.recordId,namespace:'barcode',lexicalValue:ref.lexicalValue,
  ...(ref.lexicalValue!==raw?{capturedLexicalValue:raw,representationHint:ref.representationHint}:{}),
  provenance:{sourceId:'off',visibility:'public',license:ref.provenance.license,attribution:ref.provenance.attribution,url:ref.provenance.url??null,licenseUrl:ref.provenance.licenseUrl??null,sourceDate:ref.provenance.sourceDate}};
}
function normalizedItem(item){
 if(!uuid(item?.operationId)||!validLexicalBinding(item.publicProductReference,item.barcode)||!optional(item.name,240)||!optional(item.brand,240))throw Error('Scanner handoff item is incomplete.');
 return {operationId:item.operationId,barcode:item.barcode,name:item.name,brand:item.brand,publicProductReference:copyPublicProductReference(item.publicProductReference,item.barcode)};
}
export function publicHandoffFingerprint(item){return JSON.stringify(normalizedItem(item));}
export function validateScannerHandoffReceipts(value,operations){
 if(value===undefined)return {};
 if(!value||typeof value!=='object'||Array.isArray(value))throw Error('Scanner handoff receipt history is invalid.');
 const result={};
 for(const [id,fingerprint] of Object.entries(value)){
  if(!uuid(id)||!operations.includes(id)||typeof fingerprint!=='string'||fingerprint.length>HANDOFF_LIMIT)throw Error('Scanner handoff receipt history is invalid.');
  const item=JSON.parse(fingerprint);if(item.operationId!==id||publicHandoffFingerprint(item)!==fingerprint)throw Error('Scanner handoff receipt history is invalid.');
  result[id]=fingerprint;
 }
 return result;
}
export function parsePublicScannerHandoff(value){
 if(value?.schema!==PUBLIC_SCANNER_HANDOFF||!Array.isArray(value.items)||!value.items.length||value.items.length>20)throw Error('Scanner handoff is invalid.');
 const items=value.items.map(normalizedItem);
 if(new Set(items.map(i=>i.operationId)).size!==items.length)throw Error('Scanner handoff repeats an operation.');
 const result={schema:PUBLIC_SCANNER_HANDOFF,items};
 if(new TextEncoder().encode(JSON.stringify(result)).byteLength>HANDOFF_LIMIT)throw Error('Scanner handoff exceeds the existing tab limit. Review a smaller batch.');
 return result;
}
export function createPublicScannerHandoff(queue){
 if(!Array.isArray(queue)||!queue.length)throw Error('Scan at least one item before finishing.');
 return parsePublicScannerHandoff({schema:PUBLIC_SCANNER_HANDOFF,items:queue.map(entry=>{
  const selected=entry.selectedRecord,record=selected?.publicRecord,p=record?.provenance;
  const lexical=selected?.matchContext?.sourceLexicalValue??entry.raw;
  const binding={lexicalValue:lexical,...(lexical!==entry.raw?{capturedLexicalValue:entry.raw,representationHint:entry.symbology}:{})};
  if(!entry.matches?.includes(selected)||!validLexicalBinding(binding,entry.raw)||!record?.data?.identifiers?.some(i=>i.system==='barcode'&&i.value===lexical)||p?.sourceId!=='off'||p.visibility!=='public')throw Error('Choose a published source record for every kept item, or Undo it before finishing.');
  const ref={schema:PUBLIC_PRODUCT_REFERENCE,sourceId:'off',releaseId:entry.releaseId,manifestSha256:entry.manifestSha256,recordId:record.id,namespace:entry.namespace,...binding,
   provenance:{sourceId:p.sourceId,visibility:p.visibility,license:p.license,attribution:p.attribution,url:p.url??null,licenseUrl:p.licenseUrl??null,sourceDate:p.sourceDate??null}};
  return {operationId:entry.id,barcode:entry.raw,name:selected.name??null,brand:selected.brand??null,publicProductReference:ref};
 })});
}
