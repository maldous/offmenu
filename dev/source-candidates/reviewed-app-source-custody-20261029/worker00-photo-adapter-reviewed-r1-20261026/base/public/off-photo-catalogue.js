// Exact publisher photo URLs verified by Morgan on 25 October 2026 and relayed
// through Gateway. These are current publisher observations, not retained-image
// index results or proof that a photo belongs to a historical snapshot.
export const OFF_PHOTOS=Object.freeze([
  Object.freeze({key:'flour-front-en-rev5',sourceCode:'0078742003986',imageId:'1',revision:'5',
    path:'/api/off-photos/flour-front-en-rev5.jpg',
    url:'https://images.openfoodfacts.org/images/products/007/874/200/3986/front_en.5.400.jpg',
    sourcePage:'https://world.openfoodfacts.org/product/0078742003986/all-purpose-flour-great-value',
    licensePage:'https://world.openfoodfacts.org/cgi/product_image.pl?code=0078742003986&id=front_en',
    contributor:'foodless',license:'CC BY-SA 3.0',licenseUrl:'https://creativecommons.org/licenses/by-sa/3.0/'}),
  Object.freeze({key:'nutella-front-en-rev879',sourceCode:'3017620422003',imageId:'180',revision:'879',
    path:'/api/off-photos/nutella-front-en-rev879.jpg',
    url:'https://images.openfoodfacts.org/images/products/301/762/042/2003/front_en.879.400.jpg',
    sourcePage:'https://world.openfoodfacts.org/cgi/product_image.pl?code=3017620422003&id=front_en',
    licensePage:'https://world.openfoodfacts.org/cgi/product_image.pl?code=3017620422003&id=front_en',
    contributor:'org-ferrero-france-commerciale',license:'CC BY-SA 3.0',licenseUrl:'https://creativecommons.org/licenses/by-sa/3.0/'})
]);

export function selectedPublisherPhotos(reference,detail) {
  if(reference?.schema!=='offmenu-identifier-observation/2'||reference.sourceId!=='off'||reference.namespace!=='barcode'||reference.disposition!=='source-asserted'||
    typeof detail?.referenceRecordId!=='string'||detail.sourceBinding?.sourceId!=='off'||
    detail.sourceObservation?.source_id!=='off'||detail.sourceObservation.lexical_value!==reference.sourceLexicalValue||
    detail.sourceObservation.release_id!==reference.releaseId||detail.sourceBinding.releaseId!==reference.releaseId||
    (detail.sourceObservation.source_record_id??null)!==(reference.sourceRecordId??null)||
    detail.sourceObservation.namespace!=='barcode'||detail.sourceObservation.disposition!=='source-asserted'||
    detail.observationKey?.databaseSha256!==reference.databaseSha256||
    ['run_id','input_id','record_ordinal','assertion_id'].some(key=>detail.observationKey?.[key]!==reference.observationKey?.[key]||
      detail.sourceObservation[key]!==reference.observationKey?.[key])||
    !detail.records?.[0]?.data?.identifiers?.some(id=>id.system==='barcode'&&id.value===reference.sourceLexicalValue))return [];
  return OFF_PHOTOS.filter(photo=>photo.sourceCode===reference.sourceLexicalValue).map(photo=>({
    sourceObservationReference:reference,productRecordId:detail.referenceRecordId,
    qualification:{state:'qualified',scope:'separately-observed-current-publisher-photo-for-exact-OFF-source-code'},
    role:'front',selectionRole:'selected-front',localAssetPath:photo.path,sourceUrl:photo.url,offlineAvailable:false,
    provenance:{sourceId:'off',releaseId:null,imageId:photo.imageId,revision:photo.revision,
      sourceCode:photo.sourceCode,sourcePage:photo.sourcePage,evidenceObservedDate:'2026-10-25',
      relationship:'current-publisher-photo; retained-snapshot-image-membership-unverified',
      contributor:photo.contributor,contributorRole:'publisher-reported-uploader; independent-authorship-unverified'},
    rights:{displayPermitted:true,license:photo.license,attribution:'Open Food Facts · contributor '+photo.contributor,
      licenseUrl:photo.licenseUrl,sourcePage:photo.sourcePage,photoLicensePage:photo.licensePage,
      changes:'Image bytes relayed unchanged; displayed to fit.',evidenceReference:'docs/off-publisher-photos.md#'+photo.key}}));
}
