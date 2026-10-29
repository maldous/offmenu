// Generic private operational validator. Actual native/catalogue data belongs
// outside the public bundle and private Git publication; no I/O or auth here.
import {validSourceObservationReference} from '../../apps/web/src/scanner-identity-v2.js';
import {RETAINED_PHOTO_SELECTION,RETAINED_PHOTO_SCOPE,stablePhotoValue,photoDetailIdentity,currentPhotoUseMatches,flatNativePhotoBindingValid} from '../../apps/web/src/retained-source-photo-selection.js';
const equal=(a,b)=>stablePhotoValue(a)===stablePhotoValue(b);
const hex=v=>typeof v==='string'&&/^[a-f0-9]{64}$/.test(v);
export function qualifyRetainedSourcePhoto(selection,{catalogue,currentOutputUse,origin,runtimeSelectionSha256}={}){
 const refuse=reasonCode=>({state:'unavailable',reasonCode,selection:null});
 if(catalogue?.schema!=='offmenu-retained-source-photo-catalogue/1'||selection?.schema!==RETAINED_PHOTO_SELECTION||!validSourceObservationReference(selection.reference,selection.reference?.originalLexicalValue)||!flatNativePhotoBindingValid(selection.reference,selection.detail))return refuse('RETAINED_PHOTO_NATIVE_REFERENCE_MISSING');
 const entries=(Array.isArray(catalogue?.entries)?catalogue.entries:[]).filter(e=>e&&typeof e==='object'&&equal(e.reference,selection.reference)&&
  equal(photoDetailIdentity(e.detail),photoDetailIdentity(selection.detail))&&
  equal(e.imageObservation,selection.imageObservation)&&equal(e.localAsset,selection.localAsset)&&
  equal(e.useSelectionRef,selection.useSelectionRef));
 if(entries.length!==1)return refuse('RETAINED_PHOTO_CATALOGUE_BINDING');
 const entry=entries[0],adoption=catalogue.adoption;
 if(!hex(runtimeSelectionSha256)||adoption?.state!=='admitted'||!hex(adoption.receiptSha256)||!hex(adoption.bindingReviewRef?.sha256)||
  !currentPhotoUseMatches(currentOutputUse,adoption.currentOutputUse,{origin,runtimeSelectionSha256})||
  !equal(entry.useSelectionRef,currentOutputUse.useSelectionRef))return refuse('RETAINED_PHOTO_CURRENT_ADOPTION_UNAVAILABLE');
 if(entry.rights?.displayPermitted!==true||!entry.rights.evidenceReference)return refuse('RETAINED_PHOTO_RIGHTS_UNQUALIFIED');
 const dto={schema:RETAINED_PHOTO_SELECTION,reference:selection.reference,detail:photoDetailIdentity(selection.detail),
  imageObservation:{sourceCode:entry.imageObservation.sourceCode,role:entry.imageObservation.role,
   imageId:entry.imageObservation.imageId,revision:entry.imageObservation.revision,selectedKey:entry.imageObservation.selectedKey,
   resolution:entry.imageObservation.resolution,retrievedAt:entry.imageObservation.retrievedAt,
   sourceLocator:Object.fromEntries(['sourceId','releaseId','originalSha256','ordinal'].map(k=>[k,entry.imageObservation.sourceLocator[k]])),
   image:Object.fromEntries(['sha256','bytes','type','width','height'].filter(k=>Object.hasOwn(entry.imageObservation.image,k)).map(k=>[k,entry.imageObservation.image[k]]))},
  useSelectionRef:entry.useSelectionRef,localAsset:entry.localAsset,
  currentOutputUse,qualification:{state:'qualified',scope:RETAINED_PHOTO_SCOPE,
   adoptionReceiptSha256:adoption.receiptSha256,bindingReviewRef:{id:adoption.bindingReviewRef.id??null,sha256:adoption.bindingReviewRef.sha256}},
  rights:Object.fromEntries(['displayPermitted','license','licenseUrl','attribution','sourcePage','photoLicensePage','evidenceReference','changes','scopeQualification','attributionDetails'].filter(k=>Object.hasOwn(entry.rights,k)).map(k=>[k,entry.rights[k]]))};
 if(new TextEncoder().encode(JSON.stringify(dto)).length>65536)return refuse('RETAINED_PHOTO_OUTPUT_BOUND');
 return {state:'qualified',reasonCode:null,selection:JSON.parse(JSON.stringify(dto))};
}
