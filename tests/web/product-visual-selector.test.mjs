import test from 'node:test';
import assert from 'node:assert/strict';
import {selectProductVisual,afterVisualLoadFailure} from '../../public/product-visual-selector.js';
const ref={schema:'offmenu-identifier-observation/2',namespace:'barcode',originalLexicalValue:'generated-code',
  sourceLexicalValue:'generated-source-code',sourceId:'off',releaseId:'generated-release',
  observationKey:{run_id:'generated',input_id:'generated',record_ordinal:7,assertion_id:9}};
const other={...ref,observationKey:{...ref.observationKey,assertion_id:10}};
const url='https://images.openfoodfacts.org/images/products/111/222/333/4444/front_en.1.400.jpg';
function photo(overrides={}) {return {sourceObservationReference:ref,productRecordId:'generated-record',
  qualification:{state:'qualified'},role:'front',selectionRole:'selected-front',sourceUrl:url,
  provenance:{sourceId:'off',releaseId:'generated-release',imageId:'generated-image',revision:1,
    sourcePage:'generated source page',recordPointer:'/generated/record'},
  rights:{displayPermitted:true,license:'Fixture CC BY-SA',attribution:'Generated fixture contributor',
    evidenceReference:'generated-rights-evidence'},...overrides};}
function mapping(overrides={}) {return {sourceObservationReference:ref,productRecordId:'generated-record',
  status:'qualified',relation:'exact',conceptId:'shared:example',taxonomyVersion:'shared-v1',
  crosswalkVersion:'crosswalk-v1',originalSource:{term:'generated category',language:'en',code:'fixture:01'},
  provenance:{sourceId:'off',releaseId:'generated-release',pointer:'/generated/category'},...overrides};}
const concept={conceptId:'shared:example',taxonomyVersion:'shared-v1',definitionStatus:'accepted',
  preferredEnglishLabel:'Generated non-food category',presentation:{status:'approved',emoji:'🧰'}};
const input=(overrides={})=>({sourceObservationReference:ref,selectedProductRecordId:'generated-record',
  sourceProductName:'Generated source name',theme:'dark',photoCandidates:[],categoryMappings:[],
  canonicalConcepts:[],permittedLocalAssets:[],...overrides});

test('qualified exact OFF front photo wins with source attribution; ingredient status is irrelevant',()=>{
  const result=selectProductVisual(input({photoCandidates:[photo()],ingredientStatus:'non-food'}));
  assert.equal(result.tier,'product-photo');assert.equal(result.src,url);
  assert.match(result.alt,/Generated source name/);
  assert.equal(result.caption,'Source product photo');
  assert.match(result.rights.attribution,/Generated fixture contributor/);
  assert.equal(result.provenance.sourceId,'off');
  assert.equal(result.rights.license,'Fixture CC BY-SA');
});

test('mismatch, rights hold, arbitrary URLs and competing photos never become a selected image',()=>{
  for(const candidate of [photo({sourceObservationReference:other}),photo({productRecordId:'other'}),
    photo({rights:{displayPermitted:false,license:'x',attribution:'y',evidenceReference:'z'}}),
    photo({sourceUrl:'https://images.openfoodfacts.org/images/products/111/222/333/4444/front_en.1.400.jpg?token=secret'}),
    photo({sourceUrl:'https://example.invalid/111.jpg'})])
    assert.equal(selectProductVisual(input({photoCandidates:[candidate]})).tier,'app-fallback');
  assert.equal(selectProductVisual(input({photoCandidates:[photo(),photo({sourceUrl:url.replace('.400.','.800.'),selectionRole:'selected-front'})]})).tier,'app-fallback');
});

test('qualified shared canonical mapping selects emoji, never category by product name or ingredient',()=>{
  const result=selectProductVisual(input({categoryMappings:[mapping()],canonicalConcepts:[concept],
    sourceProductName:'Food-sounding words',ingredientStatus:'unclassified'}));
  assert.equal(result.tier,'category-illustration');assert.equal(result.kind,'emoji');
  assert.match(result.alt,/not a product photo/);
  assert.match(result.caption,/platform/);
  assert.equal(result.evidence.conceptId,'shared:example');
  assert.equal(result.evidence.mappings[0].originalSource.code,'fixture:01');
  for(const variant of [mapping({relation:'broader'}),mapping({status:'candidate'}),
    mapping({sourceObservationReference:other})])
    assert.equal(selectProductVisual(input({categoryMappings:[variant],canonicalConcepts:[concept]})).tier,'app-fallback');
});

test('conflicting mapped concepts fall back to the selected app icon; unknown local icons are rejected',()=>{
  const otherConcept={...concept,conceptId:'shared:another'};
  const ambiguous=selectProductVisual(input({categoryMappings:[mapping(),mapping({conceptId:'shared:another'})],
    canonicalConcepts:[concept,otherConcept]}));
  assert.equal(ambiguous.tier,'app-fallback');assert.equal(ambiguous.src,'/scanner-balanced-final-dark.svg');
  const local={...concept,presentation:{status:'approved',localIconAssetPath:'/fixture/category.svg',
    iconRights:{displayPermitted:true,evidenceReference:'generated-authored-icon'}}};
  assert.equal(selectProductVisual(input({categoryMappings:[mapping()],canonicalConcepts:[local]})).tier,'app-fallback');
  const approved=selectProductVisual(input({categoryMappings:[mapping()],canonicalConcepts:[local],
    permittedLocalAssets:['/fixture/category.svg']}));
  assert.equal(approved.kind,'image');assert.equal(approved.src,'/fixture/category.svg');
  assert.match(approved.caption,/not product photo/);
});

test('photo failure, offline mode and app-icon failure cascade without inventing product data',()=>{
  const i=input({photoCandidates:[photo()],categoryMappings:[mapping()],canonicalConcepts:[concept]});
  const chosen=selectProductVisual(i);
  assert.equal(afterVisualLoadFailure(i,chosen).tier,'category-illustration');
  assert.equal(selectProductVisual({...i,offline:true}).tier,'category-illustration');
  const noCategory=input({photoCandidates:[photo()]});
  const logo=afterVisualLoadFailure(noCategory,selectProductVisual(noCategory));
  assert.equal(logo.tier,'app-fallback');
  const text=afterVisualLoadFailure(noCategory,logo,{failedSources:[url]});
  assert.equal(text.kind,'text');assert.equal(text.text,'OffMenu');
});
