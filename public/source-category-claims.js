// Preserve publisher claims; this module contains no category taxonomy or mapping.
export function unknownCategoryDisposition() {
  return {state:'ambiguous-unknown',reasonCode:'NO_QUALIFIED_SHARED_CATEGORY_MAPPING',
    canonicalConceptId:null,preferredEnglishLabel:null,crosswalk:null,
    ingredientCompositionAsserted:false};
}

export function sourceCategoryClaims(input) {
  const expected=['categories','categories_tags','categories_hierarchy','categories_lc',
    'categories_properties','categories_properties_tags','category_properties',
    'food_groups','food_groups_tags','food_groups_hierarchy','lang','lc','languages_codes'];
  const versions=Object.keys(input).filter(key=>
    /^(?:categories|category|food_groups|taxonomy|taxonomies)_(?:taxonomy_)?versions?$/.test(key)).sort();
  const keys=new Set([...expected,...versions]);
  const fields=Object.fromEntries([...keys].filter(key=>Object.hasOwn(input,key))
    .map(key=>[key,structuredClone(input[key])]));
  const fieldStates=Object.fromEntries([...keys].map(key=>[key,
    !Object.hasOwn(input,key)?'not-provided-in-input':input[key]===null?'source-null':'source-provided-unverified']));
  const evidence={projectionVersion:'offmenu-off-source-category-fields/1',
    qualificationStatus:'unverified-source-assertions',
    fields:Object.fromEntries([...keys].map(key=>[key,{state:!Object.hasOwn(input,key)?'missing':input[key]===null?'null':'present',
      sourcePointer:Object.hasOwn(input,key)?'/'+key:null}])),
    sourceVersionKeys:versions,sourceTaxonomyVersionStatus:versions.length?'unverified-source-assertions':'unknown'};
  return {schema:'offmenu-source-category-claims/1',fields,fieldStates,evidence,
    scope:'Only supplied source fields; omitted input fields do not establish publisher absence.',
    mappingState:'unmapped',ingredientCompositionAsserted:false};
}
