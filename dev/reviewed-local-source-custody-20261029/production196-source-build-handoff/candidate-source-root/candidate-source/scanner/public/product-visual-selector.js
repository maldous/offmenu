// Pure visual selection. No lookup, image request, barcode normalization or
// frontend-only category taxonomy. The caller supplies qualified evidence.
export const PRODUCT_VISUAL_SELECTOR = 'offmenu-product-visual-selector/1';
const APP_ICONS = Object.freeze({light:'/scanner-balanced-final.svg',dark:'/scanner-balanced-final-dark.svg'});
const object = value => value !== null && typeof value === 'object' && !Array.isArray(value);
function stable(value) {
  if (Array.isArray(value)) return '['+value.map(stable).join(',')+']';
  if (object(value)) return '{'+Object.keys(value).sort().map(k=>JSON.stringify(k)+':'+stable(value[k])).join(',')+'}';
  return JSON.stringify(value);
}
function exactReference(a,b) {
  return object(a) && object(b) && a.schema==='offmenu-identifier-observation/2' &&
    stable(a)===stable(b);
}
function localAsset(path, permitted) {
  return typeof path==='string' && Array.isArray(permitted) && permitted.includes(path) &&
    /^\/[A-Za-z0-9/_-]+\.(?:svg|png|webp|jpe?g)$/.test(path) &&
    !path.includes('..') && !path.includes('//');
}
function offImageUrl(url) {
  try {
    const parsed=new URL(url);
    return parsed.protocol==='https:' && parsed.hostname==='images.openfoodfacts.org' &&
      parsed.username==='' && parsed.password==='' && parsed.search==='' && parsed.hash==='' &&
      /^\/images\/products\/(?:[0-9]{3}\/)+[0-9]+\/front_[a-z]{2}\.[1-9][0-9]*\.[1-9][0-9]*\.(?:jpg|jpeg|png|webp)$/.test(parsed.pathname) &&
      parsed.href===url;
  } catch {return false;}
}
function photoSource(candidate, input, failed) {
  if (!object(candidate) || !exactReference(candidate.sourceObservationReference,input.sourceObservationReference) ||
      candidate.qualification?.state!=='qualified' || candidate.rights?.displayPermitted!==true ||
      typeof input.selectedProductRecordId!=='string' || !input.selectedProductRecordId ||
      candidate.productRecordId!==input.selectedProductRecordId ||
      candidate.role!=='front' || !object(candidate.provenance) ||
      !candidate.provenance.sourceId ||
      !(candidate.provenance.releaseId || candidate.provenance.releaseId===null &&
        candidate.qualification.scope==='separately-observed-current-publisher-photo-for-exact-OFF-source-code' &&
        candidate.provenance.relationship==='current-publisher-photo; retained-snapshot-image-membership-unverified' &&
        /^\d{4}-\d{2}-\d{2}$/.test(candidate.provenance.evidenceObservedDate)) ||
      !candidate.provenance.imageId || !candidate.provenance.revision ||
      !candidate.rights.license || !candidate.rights.attribution ||
      !candidate.rights.evidenceReference) return null;
  const src=candidate.localAssetPath || candidate.sourceUrl;
  if (typeof src!=='string' || failed.has(src) ||
      !(candidate.localAssetPath ? localAsset(src,input.permittedLocalAssets) :
        candidate.provenance.sourceId==='off' && offImageUrl(src)) ||
      input.offline===true && (!candidate.localAssetPath || candidate.offlineAvailable!==true)) return null;
  return {src,candidate};
}
function mappedChoice(input, failed, kind='category') {
  const key=kind==='ingredient'?'ingredientMappings':kind==='type'?'typeMappings':'categoryMappings';
  if(kind!=='category' && (!input.classificationEvidenceReference ||
    kind==='ingredient' && (input.ingredientApplicability?.state!=='applicable' || !input.ingredientApplicability.evidenceReference)))return null;
  const mappings=(Array.isArray(input[key])?input[key]:[]).filter(item=>
    object(item) && exactReference(item.sourceObservationReference,input.sourceObservationReference) &&
    item.status==='qualified' && item.relation==='exact' &&
    typeof input.selectedProductRecordId==='string' && item.productRecordId===input.selectedProductRecordId &&
    typeof item.conceptId==='string' && item.conceptId &&
    typeof item.taxonomyVersion==='string' && item.taxonomyVersion &&
    typeof item.crosswalkVersion==='string' && item.crosswalkVersion &&
    object(item.provenance) && object(item.originalSource) &&
    (kind==='category'||typeof item.provenance.sourceId==='string'&&!!item.provenance.sourceId&&
      typeof item.provenance.pointer==='string'&&!!item.provenance.pointer) &&
    (typeof item.originalSource.term==='string' && !!item.originalSource.term ||
     typeof item.originalSource.code==='string' && !!item.originalSource.code));
  const ids=new Set(mappings.map(item=>item.taxonomyVersion+'\u0000'+item.conceptId));
  if (ids.size!==1) return null; // Ambiguous/broader/unmapped is not category equality.
  const [mapping]=mappings;
  const concepts=(Array.isArray(input.canonicalConcepts)?input.canonicalConcepts:[]).filter(item=>object(item) &&
    (kind==='category'||item.kind===kind) &&
    item.conceptId===mapping.conceptId && item.taxonomyVersion===mapping.taxonomyVersion &&
    item.definitionStatus==='accepted' && typeof item.preferredEnglishLabel==='string' &&
    item.preferredEnglishLabel.trim());
  if (concepts.length!==1) return null;
  const concept=concepts[0], presentation=concept.presentation;
  if (presentation?.status!=='approved' || kind!=='category' && !presentation.evidenceReference) return null;
  const title=kind==='ingredient'?'Ingredient':kind==='type'?'Type':'Category';
  const tier=kind==='category'?'category-illustration':kind+'-illustration';
  const evidence={conceptId:concept.conceptId,taxonomyVersion:concept.taxonomyVersion,
    preferredEnglishLabel:concept.preferredEnglishLabel,
    ...(kind==='category'?{}:{kind,classificationEvidenceReference:input.classificationEvidenceReference,presentationEvidenceReference:presentation.evidenceReference}),
    mappings:mappings.map(item=>({crosswalkVersion:item.crosswalkVersion,relation:item.relation,
      originalSource:item.originalSource,provenance:item.provenance}))};
  if (typeof presentation.emoji==='string' && presentation.emoji.length>0 &&
      Array.from(presentation.emoji).length<=16 && !/[\x00-\x1f\x7f<>]/.test(presentation.emoji))
    return {tier,kind:'emoji',text:presentation.emoji,
      alt:title+' illustration of '+concept.preferredEnglishLabel+'; not a product photo',
      caption:title+' illustration, not product photo · emoji appearance varies by platform',
      evidence,rights:{presentation:'Unicode emoji; platform appearance varies'}};
  const src=presentation.localIconAssetPath;
  if (localAsset(src,input.permittedLocalAssets) && !failed.has(src) &&
      presentation.iconRights?.displayPermitted===true && presentation.iconRights?.evidenceReference &&
      (input.offline!==true || presentation.offlineAvailable===true))
    return {tier,kind:'image',src,
      alt:title+' illustration of '+concept.preferredEnglishLabel+'; not a product photo',
      caption:title+' illustration, not product photo',evidence,rights:presentation.iconRights};
  return null;
}
/** Returns data for semantic DOM rendering; no URL is fetched by this module. */
export function selectProductVisual(input,{failedSources=[]}={}) {
  if (!object(input) || input.sourceObservationReference?.schema!=='offmenu-identifier-observation/2')
    throw new TypeError('Exact selected source observation required');
  const failed=new Set(failedSources);
  const photos=(input.photoCandidates||[]).map(item=>photoSource(item,input,failed)).filter(Boolean);
  const primary=photos.filter(item=>item.candidate.selectionRole==='selected-front');
  const chosen=primary.length===1?primary[0]:photos.length===1?photos[0]:null;
  if (chosen) {
    const {src,candidate}=chosen;
    const name=typeof input.sourceProductName==='string'&&input.sourceProductName.trim()?
      input.sourceProductName.trim():'selected source product';
    const nativeAssertion=candidate.qualification.scope==='reviewed-retained-photo-for-explicit-native-source-assertion';
    const currentPublisher=candidate.qualification.scope==='separately-observed-current-publisher-photo-for-exact-OFF-source-code';
    return {tier:'product-photo',kind:'image',src,
      alt:nativeAssertion?'Photo from the explicitly selected source; product variant match unverified':currentPublisher?'Current Open Food Facts photo for source code '+candidate.provenance.sourceCode+
        '; retained label '+name+'; snapshot image unverified':'Source product photo for '+name,
      caption:nativeAssertion?'Selected source photo':currentPublisher?'Current publisher photo':'Source product photo',
      provenance:candidate.provenance,rights:candidate.rights,
      identity:{sourceObservationReference:input.sourceObservationReference},
      competingPhotoCount:photos.length};
  }
  const illustration=mappedChoice(input,failed,'ingredient')||mappedChoice(input,failed,'type')||mappedChoice(input,failed);
  if (illustration) return illustration;
  return appProductVisualFallback(input,{failedSources});
}
export function appProductVisualFallback(input={}, {failedSources=[]}={}) {
  const failed=new Set(failedSources);
  const theme=input.theme==='dark'?'dark':'light',src=APP_ICONS[theme];
  if (failed.has(src)) return {tier:'app-fallback',kind:'text',text:'OffMenu',
    alt:'OffMenu app fallback; no eligible product photo or category illustration',
    caption:'Product photo unavailable · no qualified category illustration'};
  return {tier:'app-fallback',kind:'image',src,
    alt:'OffMenu app icon; no eligible product photo or category illustration',
    caption:'Product photo unavailable · no qualified category illustration',
    provenance:{asset:'Selected Balanced Final OffMenu app icon',theme}};
}
export function afterVisualLoadFailure(input,previous,{failedSources=[]}={}) {
  if (!previous || previous.kind!=='image' || typeof previous.src!=='string')
    return selectProductVisual(input,{failedSources});
  return selectProductVisual(input,{failedSources:[...failedSources,previous.src]});
}
