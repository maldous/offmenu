import test from 'node:test';
import assert from 'node:assert/strict';
import {sourceCategoryClaims,unknownCategoryDisposition} from '../public/source-category-claims.js';
import {normalizeOFF,normalizeUSDA,record} from '../public/unified-data.js';

const source={id:'off',name:'Generated source',url:'https://source.invalid/',license:'synthetic',countries:[]};
test('OFF source category terms, code paths, language, version and extensions survive normalization exactly',()=>{
  const raw={code:'001234',product_name:'Source name',categories:'Pâtisserie, 菓子',
    categories_tags:['fr:pâtisseries','en:snacks'],categories_hierarchy:['en:foods','en:snacks','fr:pâtisseries'],
    categories_taxonomy_version:'synthetic:2026-v3',categories_properties:{'original/key':{codes:['A','A']}},
    food_groups_tags:['en:biscuits-and-cakes'],lang:'fr',lc:'be',food_groups:null,nutriments:{}};
  const [product]=normalizeOFF(raw,source);
  const claims=product.data.sourceCategoryClaims;
  for(const key of ['categories','categories_tags','categories_hierarchy','categories_taxonomy_version',
    'categories_properties','food_groups_tags','lang','lc','food_groups'])assert.deepEqual(claims.fields[key],raw[key]);
  assert.equal(claims.mappingState,'unmapped');
  assert.equal(product.data.categoryDisposition.state,'ambiguous-unknown');
  assert.equal(product.provenance.sourceId,'off');
  raw.categories_tags.push('later mutation');
  assert.deepEqual(claims.fields.categories_tags,['fr:pâtisseries','en:snacks']);
});

test('omitted, null and empty supplied categories remain distinct without a publisher-absence claim',()=>{
  const omitted=sourceCategoryClaims({}),nil=sourceCategoryClaims({categories_tags:null}),empty=sourceCategoryClaims({categories_tags:[]});
  assert.equal(omitted.fieldStates.categories_tags,'not-provided-in-input');
  assert.equal(Object.hasOwn(omitted.fields,'categories_tags'),false);
  assert.equal(nil.fieldStates.categories_tags,'source-null');
  assert.equal(nil.fields.categories_tags,null);
  assert.equal(empty.fieldStates.categories_tags,'source-provided-unverified');
  assert.deepEqual(empty.fields.categories_tags,[]);
});

test('names and unreviewed source nonfood claims never invent a canonical mapping or a noningredient disposition',()=>{
  const [product]=normalizeOFF({code:'00123',product_name:'Laundry detergent',categories_tags:['en:non-food']},source);
  assert.deepEqual(product.data.categoryDisposition,unknownCategoryDisposition());
  assert.equal(product.data.categoryDisposition.canonicalConceptId,null);
  assert.equal(product.data.categoryDisposition.ingredientCompositionAsserted,false);
});

test('all normalizer-created product records have an explicit unknown mapping disposition',()=>{
  const [usda]=normalizeUSDA({fdcId:7,description:'Synthetic food',foodNutrients:[]},{...source,id:'usda'});
  assert.deepEqual(usda.data.categoryDisposition,unknownCategoryDisposition());
  const custom=record('product','001',{name:'Unknown'},source);
  assert.deepEqual(custom.data.categoryDisposition,unknownCategoryDisposition());
  assert.equal(Object.hasOwn(record('recipe','r',{},source).data,'categoryDisposition'),false);
});
