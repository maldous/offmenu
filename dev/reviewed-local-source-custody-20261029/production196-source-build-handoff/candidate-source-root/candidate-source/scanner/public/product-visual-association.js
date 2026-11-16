import {validateClassificationProjection} from './source-classification-contract.mjs';
import {retainedSourcePhotoCandidate} from './retained-source-photo-selection.js';
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

export const VISUAL_CLASSIFICATION='offmenu-product-visual-classification/1';
const textValue=value=>typeof value==='string'&&value.length>0&&value.length<=2000?value:null;
function classificationSnapshot(reference,detail) {
  const empty={state:'unresolved',evidenceReference:null,ingredientApplicability:{state:'unresolved',evidenceReference:null},ingredientMappings:[],typeMappings:[],canonicalConcepts:[],permittedLocalAssets:[]};
  if(!reference)return empty;
  const projection=detail?.classificationProjection;
  try{validateClassificationProjection(projection);}catch{return empty;}
  const semantic=projection.classification;
  if(JSON.stringify(referenceSnapshot(projection.sourceBinding.sourceObservationReference))!==JSON.stringify(reference))return empty;
  const sourceRecordId=reference.sourceRecordId;
  if(typeof sourceRecordId!=='string'||!sourceRecordId||projection.sourceBinding.sourceRecordId!==sourceRecordId)return empty;
  for(const [binding,key] of [[detail?.sourceObservation,'source_record_id'],
    [detail?.sourceBinding,'identifierSourceRecordId'],[detail?.sourceBinding,'sourceRecordId']])
    if(binding&&Object.hasOwn(binding,key)&&binding[key]!==sourceRecordId)return empty;
  if(['unresolved','conflict'].includes(semantic.disposition))return {...empty,state:semantic.disposition,semanticDisposition:semantic.disposition,
    semanticRelation:semantic.relation??null,ingredientApplicability:{state:semantic.ingredientApplicability,evidenceReference:null}};
  const semanticOnly={...empty,semanticDisposition:semantic.disposition,semanticRelation:semantic.relation??null,
    ingredientApplicability:{state:semantic.ingredientApplicability,evidenceReference:null}};
  const value=projection.visualClassification;
  if(!reference||value?.schema!==VISUAL_CLASSIFICATION||value.productRecordId!==detail.referenceRecordId||
    !value.productRecordId||value.qualification?.state!=='qualified'||!textValue(value.qualification.evidenceReference)||
    JSON.stringify(referenceSnapshot(value.sourceObservationReference))!==JSON.stringify(reference))return semanticOnly;
  const state=value.ingredientApplicability?.state;
  if(state!==semantic.ingredientApplicability)return semanticOnly;
  const applicability=['applicable','nonfood','not-applicable'].includes(state)&&textValue(value.ingredientApplicability.evidenceReference)?
    {state,evidenceReference:value.ingredientApplicability.evidenceReference}:empty.ingredientApplicability;
  const mappings=name=>(Array.isArray(value[name])?value[name]:[]).slice(0,100).filter(m=>m&&typeof m==='object').map(m=>({
    sourceObservationReference:referenceSnapshot(m.sourceObservationReference),productRecordId:m.productRecordId,
    status:m.status,relation:m.relation,conceptId:m.conceptId,taxonomyVersion:m.taxonomyVersion,crosswalkVersion:m.crosswalkVersion,
    originalSource:{term:m.originalSource?.term,code:m.originalSource?.code,language:m.originalSource?.language},
    provenance:{sourceId:m.provenance?.sourceId,releaseId:m.provenance?.releaseId,pointer:m.provenance?.pointer}}));
  const concepts=(Array.isArray(value.canonicalConcepts)?value.canonicalConcepts:[]).slice(0,100).filter(c=>c&&typeof c==='object').map(c=>({
    conceptId:c.conceptId,taxonomyVersion:c.taxonomyVersion,kind:c.kind,definitionStatus:c.definitionStatus,
    preferredEnglishLabel:c.preferredEnglishLabel,presentation:{status:c.presentation?.status,evidenceReference:c.presentation?.evidenceReference,
      emoji:c.presentation?.emoji,localIconAssetPath:c.presentation?.localIconAssetPath,offlineAvailable:c.presentation?.offlineAvailable,
      iconRights:{displayPermitted:c.presentation?.iconRights?.displayPermitted,evidenceReference:c.presentation?.iconRights?.evidenceReference}}}));
  return {state:'qualified',semanticDisposition:semantic.disposition,semanticRelation:semantic.relation,
    evidenceReference:value.qualification.evidenceReference,ingredientApplicability:applicability,
    ingredientMappings:mappings('ingredientMappings'),typeMappings:mappings('typeMappings'),canonicalConcepts:concepts,
    permittedLocalAssets:(Array.isArray(value.permittedLocalAssets)?value.permittedLocalAssets:[]).filter(textValue).slice(0,100)};
}

function prepare(input={}) {
  const {reference=null,detail=null,name='',theme='light',offline=false,sourcePhotoSelection=null}=input??{};
  const retained=sourcePhotoSelection?retainedSourcePhotoCandidate(sourcePhotoSelection,detail,{origin:input?.origin??globalThis.location?.origin}):null;
  const native=retained?.state==='qualified';
  const selected=referenceSnapshot(native?sourcePhotoSelection.reference:reference),appearance={theme,offline};
  const selectedDetail=native?{...retained.assertion.binding,classificationProjection:retained.assertion.classificationProjection}:detail;
  const classification=classificationSnapshot(selected,selectedDetail);
  if(!selected)return {reference:null,input:null,appearance,classification,retained};
  // The existing catalogue owns exact observation/detail and photo qualification.
  // No caller photo list, category, product name or bare barcode can add a join.
  const photoCandidates=sourcePhotoSelection?(native?[retained.candidate]:[]):selectedPublisherPhotos(selected,detail);
  return {reference:selected,appearance,classification,retained,input:{sourceObservationReference:selected,
    selectedProductRecordId:typeof selectedDetail?.referenceRecordId==='string'?selectedDetail.referenceRecordId:null,
    sourceProductName:native?'explicit independent source assertion':typeof name==='string'?name:'',theme,offline,
    photoCandidates,categoryMappings:[],ingredientMappings:classification.ingredientMappings,typeMappings:classification.typeMappings,
    canonicalConcepts:classification.canonicalConcepts,ingredientApplicability:classification.ingredientApplicability,
    classificationEvidenceReference:classification.evidenceReference,
    permittedLocalAssets:[...OFF_PHOTOS.map(photo=>photo.path),...classification.permittedLocalAssets,...(native?[sourcePhotoSelection.localAsset.path]:[])]}};
}

function descriptor(prepared,visual) {
  return {schema:PRODUCT_VISUAL_ASSOCIATION,selectorVersion:PRODUCT_VISUAL_SELECTOR,
    sourceObservationReference:prepared.reference,
    productRecordId:visual.tier==='product-photo'?prepared.input.selectedProductRecordId:null,
    sourcePhotoSelection:{state:prepared.retained?.state??'not-supplied',reasonCode:prepared.retained?.reasonCode??null,
      scope:prepared.retained?.state==='qualified'?'explicit-independent-native-source-assertion':null},
    associationState:visual.tier==='product-photo'?'qualified-current-publisher-photo':['ingredient-illustration','type-illustration'].includes(visual.tier)?'qualified-canonical-illustration':'unavailable',
    classification:{state:prepared.classification.state,semanticDisposition:prepared.classification.semanticDisposition??'unresolved',
      semanticRelation:prepared.classification.semanticRelation??null,evidenceReference:prepared.classification.evidenceReference,
      ingredientApplicability:prepared.classification.ingredientApplicability,
      selectedIcon:visual.evidence?.kind?{kind:visual.evidence.kind,conceptId:visual.evidence.conceptId,taxonomyVersion:visual.evidence.taxonomyVersion}:null,
      meaning:'Visual classification supplies no recipe composition, nutrition or physical-product equivalence.'},
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
