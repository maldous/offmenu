// Pure common descriptor. No DOM, lookup, fetch, persistence or mapping resolver.
import {validSourceObservationReference} from './model.js';
import {selectedPublisherPhotos,OFF_PHOTOS} from './off-photo-catalogue.js';
import {PRODUCT_VISUAL_SELECTOR,selectProductVisual,afterVisualLoadFailure,
  appProductVisualFallback} from './product-visual-selector.js';

export const PRODUCT_VISUAL_ASSOCIATION='offmenu-product-visual-association/1';
const REFERENCE_KEYS=['schema','databaseSha256','runId','namespace','originalLexicalValue',
  'sourceLexicalValue','symbology','matchType','equivalence','disposition','sourceId',
  'releaseId','sourceRecordId','detailSelectionSha256'];
const OBSERVATION_KEYS=['run_id','input_id','record_ordinal','assertion_id'];

function referenceSnapshot(reference) {
  try {
    if(reference?.schema!=='offmenu-identifier-observation/2'||
      !validSourceObservationReference(reference,reference.originalLexicalValue))return null;
    // Preserve the existing typed identity, not unrelated caller/profile fields.
    return {...Object.fromEntries(REFERENCE_KEYS.map(key=>[key,reference[key]])),
      observationKey:Object.fromEntries(OBSERVATION_KEYS.map(key=>[key,reference.observationKey[key]]))};
  } catch {return null;}
}

function prepare(input={}) {
  const {reference=null,detail=null,name='',theme='light',offline=false}=input??{};
  const selected=referenceSnapshot(reference),appearance={theme,offline};
  if(!selected)return {reference:null,input:null,appearance};
  // The existing catalogue owns exact observation/detail and photo qualification.
  // No caller photo list, category, product name or bare barcode can add a join.
  const photoCandidates=selectedPublisherPhotos(selected,detail);
  return {reference:selected,appearance,input:{sourceObservationReference:selected,
    selectedProductRecordId:typeof detail?.referenceRecordId==='string'?detail.referenceRecordId:null,
    sourceProductName:typeof name==='string'?name:'',theme,offline,
    photoCandidates,categoryMappings:[],canonicalConcepts:[],
    permittedLocalAssets:OFF_PHOTOS.map(photo=>photo.path)}};
}

function descriptor(prepared,visual) {
  return {schema:PRODUCT_VISUAL_ASSOCIATION,selectorVersion:PRODUCT_VISUAL_SELECTOR,
    sourceObservationReference:prepared.reference,
    productRecordId:visual.tier==='product-photo'?prepared.input.selectedProductRecordId:null,
    associationState:visual.tier==='product-photo'?'qualified-current-publisher-photo':'unavailable',
    visual,
    category:{label:'Category',state:'unidentified',display:'Not yet identified',
      sourceCategory:{state:'not-loaded-by-association',claims:null,evidence:null,
        reasonCode:'SOURCE_CATEGORY_CLAIMS_REQUIRE_SEPARATELY_BOUND_DETAIL_EVIDENCE'},
      normalizedCategory:{state:'unknown',conceptId:null,preferredEnglishLabel:null,crosswalk:null,
        reasonCode:'NO_ACCEPTED_BACKING_STORE_QUALIFIED_CATEGORY_MAPPING'}},
    ingredientMatch:{label:'Ingredient match',state:'unidentified',display:'Not yet identified',
      conceptId:null,composition:null,evidence:null,
      reasonCode:'NO_ACCEPTED_BACKING_STORE_QUALIFIED_INGREDIENT_MAPPING'},
    evidence:{associationVersion:PRODUCT_VISUAL_ASSOCIATION,selectorVersion:PRODUCT_VISUAL_SELECTOR,
      sourceReferenceState:prepared.reference?'valid-current-selected-contract':'unavailable',
      sourceCategoryAndMappings:'Separate source claims, normalized category and ingredient authority required; photo qualification supplies none.'}};
}

/** Shared input for scanner/search/kitchen/review/details; no caller is wired here. */
export function associateProductVisual(input={}, {failedSources=[]}={}) {
  const prepared=prepare(input);
  const visual=prepared.input?selectProductVisual(prepared.input,{failedSources}):
    appProductVisualFallback(prepared.appearance,{failedSources});
  return descriptor(prepared,visual);
}

/** Revalidate current input; never trust an old descriptor as identity authority. */
export function afterProductVisualAssociationFailure(input,previous,{failedSources=[]}={}) {
  const prepared=prepare(input);
  const visual=prepared.input?afterVisualLoadFailure(prepared.input,previous?.visual,{failedSources}):
    appProductVisualFallback(prepared.appearance,{failedSources:previous?.visual?.kind==='image'?
      [...failedSources,previous.visual.src]:failedSources});
  return descriptor(prepared,visual);
}
