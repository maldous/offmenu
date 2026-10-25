// Preserve publisher claims; this module contains no category taxonomy or mapping.
export function unknownCategoryDisposition() {
  return {state:'ambiguous-unknown',reasonCode:'NO_QUALIFIED_SHARED_CATEGORY_MAPPING',
    canonicalConceptId:null,preferredEnglishLabel:null,crosswalk:null,
    ingredientCompositionAsserted:false};
}

export function sourceCategoryClaims(input) {
  const expected=['categories','categories_tags','categories_hierarchy','food_groups',
    'food_groups_tags','food_groups_hierarchy','lang','lc','categories_lc',
    'taxonomy_version','categories_taxonomy_version'];
  const keys=new Set([...expected,...Object.keys(input).filter(key=>
    /^(?:categories|food_groups)(?:_[A-Za-z0-9_-]+)?$/.test(key))]);
  const fields=Object.fromEntries([...keys].filter(key=>Object.hasOwn(input,key))
    .map(key=>[key,structuredClone(input[key])]));
  const fieldStates=Object.fromEntries([...keys].map(key=>[key,
    !Object.hasOwn(input,key)?'not-provided-in-input':input[key]===null?'source-null':'source-provided-unverified']));
  return {schema:'offmenu-source-category-claims/1',fields,fieldStates,
    scope:'Only supplied source fields; omitted input fields do not establish publisher absence.',
    mappingState:'unmapped',ingredientCompositionAsserted:false};
}
