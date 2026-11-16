import {validSourceProductReference,appProductVisualFallback} from './product-visual-selector.js';
const stable=x=>Array.isArray(x)?'['+x.map(stable).join(',')+']':x&&typeof x==='object'?
  '{'+Object.keys(x).sort().map(k=>JSON.stringify(k)+':'+stable(x[k])).join(',')+'}':JSON.stringify(x);
const same=(a,b)=>stable(a)===stable(b);
// Presentation validation, never access control. Only the authenticated LOCAL
// endpoint supplies this DTO; browser flags/values confer no source-use grant.
export function retainedCategoryAssociation(dto,reference,input={},failedSources=[]){
  if(dto?.schema!=='offmenu-local-retained-category-presentation/1'||
    !validSourceProductReference(reference)||!same(dto.sourceProductReference,reference))return null;
  const value=dto.association,type=value?.sourceTypePresentation,visual=value?.visual;
  if(!same(value?.sourceProductReference,reference)||value.sourceCategoryBinding?.state!=='qualified-source-type'||
    value.sourceCategoryBinding.semanticIdentity!==false||
    value.sourceCategoryBinding.currentToHistoricalEquivalence!==false||
    value.sourceCategoryBinding.ingredientEligibility!=='unresolved'||
    type?.identityEquivalence!==false||type.productDefinitionEquivalence!==false||
    type.recipeEligibility!=='unresolved'||type.taxonomySnapshotSHA256!==dto.taxonomySnapshotSHA256||
    dto.categories?.state!=='present'||dto.categories.pointer!=='/data/categories'||
    dto.categories.evidenceEncoding!=='typed-exact-decimal-json/1; not an original byte-span hash'||
    !/^[a-f0-9]{64}$/.test(dto.categories.parsedValueEvidenceSha256||'')||
    dto.categories.originalSourceAbsenceEstablished!==false)return null;
  const views=value.sourceCategoryBinding.categoryViews;
  if(!Array.isArray(views)||!views.length||views.length!==dto.categories.sourceValue?.length||
    !views.every((view,index)=>view.categoryID===dto.categories.sourceValue[index]&&
      view.snapshotSHA256===dto.taxonomySnapshotSHA256&&view.type?.id===type.typeID))return null;
  if(visual?.tier!=='type-illustration'||visual.kind!=='image'||
    !/^\/source-categories\/icons\/[a-z0-9-]+\.svg$/.test(visual.src||'')||
    visual.rights?.displayPermitted!==true||!views.every(view=>view.icon?.path===visual.src&&
      view.icon.rightsID===visual.rights.evidenceReference))return null;
  const result=structuredClone(value);
  if(failedSources.includes(visual.src)){
    result.visual=appProductVisualFallback(input,{failedSources});result.associationState='unavailable';
  }
  return result;
}
