import test from 'node:test';
import assert from 'node:assert/strict';
import {matchRecipeStock,personallyReviewedRecipe,recipeJSONLD,recipeIngredientKey} from '../public/recipe-library-model.js';
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
