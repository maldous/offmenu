// Structural consumer guard only. Existing backend authorization and the
// authenticated retained-asset response remain the security authority.
import {validSourceObservationReference} from './scanner-identity-v2.js';
export const RETAINED_PHOTO_SELECTION='offmenu-source-assertion-photo-selection/1';
export const RETAINED_PHOTO_SCOPE='reviewed-retained-photo-for-explicit-native-source-assertion';
export const stablePhotoValue=value=>Array.isArray(value)?'['+value.map(stablePhotoValue).join(',')+']':value&&typeof value==='object'?'{'+Object.keys(value).sort().map(k=>JSON.stringify(k)+':'+stablePhotoValue(value[k])).join(',')+'}':JSON.stringify(value);
const equal=(a,b)=>stablePhotoValue(a)===stablePhotoValue(b);
const hex=value=>typeof value==='string'&&/^[a-f0-9]{64}$/.test(value);
const keys=['observationKey','sourceObservation','sourceBinding','referenceRecordId','exactObservationBridge'];
export const photoDetailIdentity=detail=>Object.fromEntries(keys.filter(k=>Object.hasOwn(detail||{},k)).map(k=>[k,detail[k]]));
export function currentPhotoUseMatches(marker,expected,{origin,runtimeSelectionSha256}={}){
 return marker?.state==='qualified'&&expected?.state==='qualified'&&
  Object.keys(marker).sort().join(',')==='origin,runtimeSelectionSha256,state,useSelectionRef'&&
  marker.useSelectionRef&&Object.keys(marker.useSelectionRef).sort().join(',')==='id,sha256'&&
  typeof marker.useSelectionRef?.id==='string'&&marker.useSelectionRef.id.length>0&&hex(marker.useSelectionRef.sha256)&&
  hex(marker.runtimeSelectionSha256)&&marker.origin===origin&&
  (!runtimeSelectionSha256||marker.runtimeSelectionSha256===runtimeSelectionSha256)&&equal(marker,expected);
}
export function flatNativePhotoBindingValid(reference,detail){
 const s=detail?.sourceBinding,o=detail?.sourceObservation,k=detail?.observationKey;
 if(reference?.sourceId!=='off'||reference.namespace!=='barcode'||reference.disposition!=='source-asserted'||typeof detail?.referenceRecordId!=='string'||!detail.referenceRecordId||
  !s||!o||!k||k.databaseSha256!==reference.databaseSha256)return false;
 for(const key of ['run_id','input_id','record_ordinal','assertion_id'])
  if(k[key]!==reference.observationKey[key]||o[key]!==reference.observationKey[key])return false;
 if(o.source_id!==reference.sourceId||o.release_id!==reference.releaseId||o.namespace!==reference.namespace||
  o.lexical_value!==reference.sourceLexicalValue||o.source_record_id!==reference.sourceRecordId||
  o.disposition!=='source-asserted'||s.sourceId!==reference.sourceId||s.releaseId!==reference.releaseId||
  s.identifierInputId!==reference.observationKey.input_id||s.identifierRecordOrdinal!==reference.observationKey.record_ordinal||
  s.identifierSourceRecordId!==reference.sourceRecordId||o.artifact_sha256!==s.identifierAssetSha256||
  o.native_record_id!==s.identifierNativeRecordId||
  s.identifierNativeRecordId!=='off:sourceOccurrence:'+s.originalSha256+':'+reference.observationKey.record_ordinal)return false;
 for(const key of ['originalSha256','recordSha256','identifierAssetSha256','inputAssetSha256',
  'operationReceiptSha256','rightsReceiptSha256','custodyReceiptSha256'])if(!hex(s[key]))return false;
 return s.componentDigests&&Object.keys(s.componentDigests).length>0&&Object.values(s.componentDigests).every(hex);
}
function safePhotoCredits(rights,code){
 const urls=[rights?.sourcePage,rights?.photoLicensePage,rights?.licenseUrl,rights?.attributionDetails?.productUrl];
 return urls.every(value=>{try{const u=new URL(value);if(u.protocol!=='https:'||u.username||u.password||u.port||u.hash||u.href!==value)return false;
  if(u.hostname==='creativecommons.org')return /^\/licenses\/by-sa\/3\.0(?:\/deed\.en)?\/?$/.test(u.pathname)&&!u.search;
  if(u.hostname!=='world.openfoodfacts.org')return false;
  return u.pathname==='/cgi/product_image.pl'?u.searchParams.get('code')===code&&u.searchParams.get('id')==='front_en'&&
   [...u.searchParams.keys()].length===2:
   (u.pathname==='/product/'+code||u.pathname.startsWith('/product/'+code+'/'))&&!u.search;
 }catch{return false;}});
}
export function retainedSourcePhotoCandidate(selection,detail,{origin}={}){
 const refuse=reasonCode=>({state:'unavailable',reasonCode,candidate:null});
 if(selection?.schema!==RETAINED_PHOTO_SELECTION)return refuse('RETAINED_PHOTO_SELECTION_MISSING');
 const ref=selection.reference;
 if(!validSourceObservationReference(ref,ref?.originalLexicalValue)||!flatNativePhotoBindingValid(ref,selection.detail))return refuse('RETAINED_PHOTO_NATIVE_REFERENCE_MISSING');
 if(!currentPhotoUseMatches(selection.currentOutputUse,detail?.currentOutputUse,{origin})||
  !equal(selection.useSelectionRef,selection.currentOutputUse.useSelectionRef))return refuse('RETAINED_PHOTO_CURRENT_OUTPUT_USE_UNQUALIFIED');
 const q=selection.qualification;
 if(q?.state!=='qualified'||q.scope!==RETAINED_PHOTO_SCOPE||!hex(q.adoptionReceiptSha256)||
  !hex(q.bindingReviewRef?.sha256))return refuse('RETAINED_PHOTO_ADOPTION_UNAVAILABLE');
 const matches=(Array.isArray(detail?.sourceAssertions)?detail.sourceAssertions:[]).filter(a=>a&&typeof a==='object'&&equal(a.sourceObservationReference,ref)&&
  equal(photoDetailIdentity(a.binding),photoDetailIdentity(selection.detail)));
 if(matches.length!==1)return refuse('RETAINED_PHOTO_EXPLICIT_ASSERTION_MISMATCH');
 const source=selection.detail?.sourceBinding,observation=selection.imageObservation,asset=selection.localAsset;
 if(!source||observation?.sourceCode!==ref.sourceLexicalValue||observation.role!=='front'||
  !/^front_[a-z]{2}$/.test(observation.selectedKey||'')||!/^[1-9][0-9]*$/.test(observation.revision||'')||
  !/^[0-9]+$/.test(observation.imageId||'')||!/^[1-9][0-9]*$/.test(observation.resolution||'')||
  !Number.isInteger(observation.image?.bytes)||observation.image.bytes<1||observation.image.type!=='image/jpeg'||
  observation.sourceLocator?.sourceId!==ref.sourceId||observation.sourceLocator?.releaseId!==ref.releaseId||
  observation.sourceLocator?.originalSha256!==source.originalSha256||
  observation.sourceLocator?.ordinal!==ref.observationKey.record_ordinal||
  !hex(asset?.sha256)||observation.image?.sha256!==asset.sha256||asset.type!=='image/jpeg'||
  typeof asset.path!=='string'||!/^\/api\/off-photos\/[A-Za-z0-9_-]+\.jpg$/.test(asset.path))return refuse('RETAINED_PHOTO_IMAGE_ASSET_BINDING');
 const rights=selection.rights;
 if(rights?.displayPermitted!==true||!rights.license||!rights.attribution||!rights.evidenceReference||!safePhotoCredits(rights,ref.sourceLexicalValue))
  return refuse('RETAINED_PHOTO_RIGHTS_UNQUALIFIED');
 return {state:'qualified',reasonCode:null,assertion:matches[0],candidate:{
  sourceObservationReference:ref,productRecordId:selection.detail.referenceRecordId,
  qualification:q,role:'front',selectionRole:'selected-front',localAssetPath:asset.path,offlineAvailable:false,
  provenance:{sourceId:ref.sourceId,releaseId:ref.releaseId,imageId:observation.imageId,
   revision:observation.revision,sourceCode:ref.sourceLexicalValue,
   associationScope:'explicit-independent-native-source-assertion',
   relationship:'Current retrieval selected by retained metadata; historical image bytes and primary-product variant match unverified',
   metadataRelease:ref.releaseId,retrievedAt:observation.retrievedAt,imageSha256:asset.sha256},rights}};
}
