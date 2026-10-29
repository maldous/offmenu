import test from 'node:test';
import assert from 'node:assert/strict';
import {matchRecipeStock,personallyReviewedRecipe,recipeJSONLD,recipeIngredientKey} from '../../apps/web/src/recipe-library-model.js';
const item=(amount=100,unit='g')=>({name:'rice',ingredientId:'rice',amount,unit,originalText:'100 g rice',optional:false,sourceQuantity:{value:100,unit:'g',original:'100 g rice',status:'parsed'}});
const record=()=>({id:'world-recipes:recipe:test',kind:'recipe',countries:[],provenance:{sourceId:'world-recipes',visibility:'public',license:'CC BY-SA 4.0',licenseUrl:'https://creativecommons.org/licenses/by-sa/4.0/',url:'https://example.org/recipe',attribution:'Recipe author'},data:{name:'Rice',languages:['en'],yield:{value:null,unit:'portion'},ingredients:[item()],directions:['Boil rice.'],automaticPlanningEligible:false}});
test('pantry quantities aggregate compatible lots and exclude unusable stock',()=>{
 const ingredients=[item(70),item(30)];
 assert.equal(matchRecipeStock({ingredients},[{ingredient:'rice',quantity:50,unit:'g'},{ingredient:'rice',quantity:50,unit:'g'}]).quantitiesAvailable,true);
 for(const lot of [{ingredient:'rice',quantity:100,unit:'ml'},{ingredient:'rice',quantity:100,unit:'g',needsReview:true},{ingredient:'rice',quantity:100,unit:'g',expires:'2020-01-01'}])assert.equal(matchRecipeStock({ingredients},[lot]).quantitiesAvailable,false);
 assert.equal(matchRecipeStock({ingredients:[item(null,null)]},[{ingredient:'rice',quantity:100,unit:'g'}]).quantitiesAvailable,false);
 assert.notEqual(recipeIngredientKey({name:'cooked rice'}),recipeIngredientKey({name:'rice'}));
 assert.equal(recipeIngredientKey({name:'鸡蛋'}),'egg');
});
for(const [scenario,amounts,quantities]of [
 ['requirement overflow',[Number.MAX_VALUE,Number.MAX_VALUE],[100]],
 ['stock overflow',[100],[Number.MAX_VALUE,Number.MAX_VALUE]],
 ['requirement and stock overflow',[Number.MAX_VALUE,Number.MAX_VALUE],[Number.MAX_VALUE,Number.MAX_VALUE]],
])test(`pantry quantities remain unknown for ${scenario}`,()=>{
 const recipe={ingredients:amounts.map(amount=>item(amount))};
 const inventory=quantities.map(quantity=>({ingredient:'rice',quantity,unit:'g'}));
 const before=structuredClone({recipe,inventory});
 const result=matchRecipeStock(recipe,inventory,{today:'2026-10-29'});
 assert.equal(result.quantitiesAvailable,false);
 assert.deepEqual(result.unknown,['rice']);
 assert.deepEqual(result.missing,[]);
 assert.equal(result.required,amounts.length);assert.equal(result.presence,amounts.length);
 assert.equal(result.coverage,1);assert.deepEqual(result.missingNames,[]);assert.equal(result.needsReview,true);
 assert.deepEqual({recipe,inventory},before);
});
test('large finite pantry totals and deficits remain measurable',()=>{
 const half=Number.MAX_VALUE/2;
 const recipe={ingredients:[item(half),item(half)]};
 const inventory=[{ingredient:'rice',quantity:half,unit:'g'},{ingredient:'rice',quantity:half,unit:'g'}];
 const before=structuredClone({recipe,inventory});
 const available=matchRecipeStock(recipe,inventory);
 assert.equal(available.quantitiesAvailable,true);assert.deepEqual(available.unknown,[]);assert.deepEqual(available.missing,[]);
 const missing=matchRecipeStock(recipe,inventory.slice(0,1));
 assert.equal(missing.quantitiesAvailable,false);assert.deepEqual(missing.unknown,[]);
 assert.deepEqual(missing.missing,[{ingredient:'rice',unit:'g',quantity:half}]);
 assert.deepEqual({recipe,inventory},before);
});
test('personal recipe requires explicit review and does not alter the public source',()=>{
 const r=record(),before=JSON.stringify(r),ingredients=[{name:'rice',amount:100,unit:'g',optional:false}];
 assert.throws(()=>personallyReviewedRecipe(r,{servings:2,ingredients,confirmed:false}));
 assert.throws(()=>personallyReviewedRecipe(r,{servings:0,ingredients,confirmed:true}));
 assert.throws(()=>personallyReviewedRecipe(r,{servings:2,ingredients:[{...ingredients[0],unit:'cup'}],confirmed:true}));
 const personal=personallyReviewedRecipe(r,{servings:2,ingredients,confirmed:true});
 assert.equal(personal.needsReview,false);assert.equal(personal.provenance.visibility,'private');
 assert.equal(JSON.stringify(r),before);
});
test('portable export preserves instructions, credit and unknown yield',()=>{
 const exported=recipeJSONLD(record());assert.equal(exported.recipeYield,undefined);assert.equal(exported.creditText,'Recipe author');assert.equal(exported.recipeInstructions[0].text,'Boil rice.');assert.equal(exported.recipeIngredient[0],'100 g rice');
});
test('partial OCR extraction cannot claim pantry coverage or become a kitchen recipe',()=>{
 const r=record();r.data.sourcePublisher='smithsonian-archive';r.data.ingredientExtractionComplete=false;
 const match=matchRecipeStock(r.data,[{ingredient:'rice',quantity:100,unit:'g'}]);
 assert.equal(match.quantitiesAvailable,false);assert.equal(match.coverage,0);assert.equal(match.incomplete,true);
 assert.throws(()=>personallyReviewedRecipe(r,{servings:1,ingredients:[{name:'rice',amount:100,unit:'g',optional:false}],confirmed:true}),/complete historical OCR/);
});
