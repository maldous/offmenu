import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {createLotNutritionSelection,copyLotNutritionSelection,nutritionForLot} from '../public/lot-nutrition.js';
import {validateLot} from '../public/model.js';
import {planSummary} from '../public/menu-model.js';
import {cookMeal} from '../public/cooking-model.js';
import {asOffNutriments} from '../public/unified-data.js';
import {validateState} from '../cloud/state.mjs';

const date='2026-10-29';
const recipe={id:'rice',title:'Rice',servings:1,source:'Synthetic fixture',license:'CC0',instructions:['Cook.'],ingredients:[{ingredient:'rice',quantity:100,unit:'g'}]};
const fixture=()=>({inventory:[{id:'a',barcode:'1111',name:'Rice A',ingredient:'rice',quantity:100,unit:'g',needsReview:false},{id:'b',barcode:'1111',name:'Rice B',ingredient:'rice',quantity:100,unit:'g',needsReview:false}],products:{'1111':{name:'Barcode product',nutrition_data_per:'100g',nutriments:{fat_100g:1}}}});
const sourceProfile=()=>({schemaVersion:'1.0',kind:'nutrientProfile',id:'usda-files:nutrientProfile:fixture',countries:[],provenance:{sourceId:'usda-files',recordId:'fixture',releaseId:'fixture-release',license:'CC0',attribution:'Synthetic fixture',visibility:'public',sourceDate:null},data:{status:'candidate',basis:{amount:100,unit:'g',state:'as-described'},nutrients:{fat:{value:7,unit:'g',basis:{amount:100,unit:'g',state:'as-described'},method:'source'},protein:{value:0,unit:'g',basis:{amount:100,unit:'g',state:'as-described'},method:'source'},sugars:{value:null,unit:'g',qualifier:'unknown'}}}});

// Execute the actual application's callback, rather than a second implementation.
function appFixture({writeAllowed=true}={}){
 const app=readFileSync(new URL('../public/app.js',import.meta.url),'utf8');
 const marker='applyNutrition:(lot,record,nutriments)=>{',start=app.indexOf(marker),end=app.indexOf('}});',start);
 assert.ok(start>=0&&end>start);const callback=app.slice(start+'applyNutrition:'.length,end+1);
 const build=new Function('createLotNutritionSelection','validateLot','initial','writeAllowed',`
  let lots=initial.inventory,products=initial.products;
  const sharing={canWrite:()=>writeAllowed},localStorage={setItem(){}},PRODUCTS='products';
  const t=x=>x;function markDirty(){}function findMeals(){}function pantry(){}function save(next){lots=next;}
  return {apply:${callback},state:()=>({inventory:lots,products}),replaceInventory:next=>{lots=next;}};
 `);
 return build(createLotNutritionSelection,validateLot,fixture(),writeAllowed);
}
function apply(ui){const record=sourceProfile(),lot=ui.state().inventory[0];ui.apply(lot,record,asOffNutriments(record,lot.unit));return ui.state();}

test('existing source-data UI assigns nutrition only to the selected lot',()=>{
 const ui=appFixture(),before=structuredClone(ui.state().products),state=apply(ui);
 assert.deepEqual(state.products,before);assert.ok(state.inventory[0].nutritionSelection);assert.equal(state.inventory[1].nutritionSelection,undefined);
});
test('actual planner consumes selected and barcode profiles independently',()=>{
 const state=apply(appFixture()),summary=planSummary([{recipeId:'rice',date,servings:2}],[recipe],state.inventory,state.products,[date]);
 assert.equal(summary.totals.fat_100g.value,8);assert.deepEqual(summary.totals.proteins_100g,{value:0,known:1,total:2});assert.deepEqual(summary.totals.sugars_100g,{value:0,known:0,total:2});
});
test('actual cooking consumes each lot profile without contaminating the next batch',()=>{
 const state=apply(appFixture()),first=cookMeal({recipe,...state,servings:1,date,mutationId:'first'});
 const second=cookMeal({recipe,inventory:first.inventory,products:state.products,servings:1,date,mutationId:'second',batches:[first.batch]});
 assert.equal(first.batch.totals.fat_100g.value,7);assert.equal(second.batch.totals.fat_100g.value,1);
});
test('cloud validation retains source, method, basis, unknown and zero across roundtrip',()=>{
 const state=apply(appFixture()),roundtrip=validateState({...state,recipes:[recipe],profile:{country:'AU',units:'metric',servings:2}});
 assert.deepEqual(roundtrip.inventory[0].nutritionSelection,state.inventory[0].nutritionSelection);
 assert.equal(roundtrip.inventory[0].nutritionSelection.sourceProfile.status,'candidate');
 assert.equal(roundtrip.inventory[0].nutritionSelection.canonicalIdentityAsserted,false);
 assert.equal(roundtrip.inventory[0].nutritionSelection.sourceProfile.nutrients.protein.value,0);
 assert.equal(roundtrip.inventory[0].nutritionSelection.sourceProfile.nutrients.sugars.value,null);
});
test('view-only kitchen cannot apply the source-data UI selection',()=>{
 const ui=appFixture({writeAllowed:false}),before=JSON.stringify(ui.state());assert.throws(()=>apply(ui),/editable|view|permission/i);assert.equal(JSON.stringify(ui.state()),before);
});
test('stale inventory object cannot apply a source profile after replacement',()=>{
 const ui=appFixture(),old=ui.state().inventory[0],record=sourceProfile();ui.replaceInventory(ui.state().inventory.map(l=>({...l})));
 assert.throws(()=>ui.apply(old,record,asOffNutriments(record,'g')),/changed|current/i);
});
test('changed lot identity or unit makes its explicit selection unknown',()=>{
 const lot=fixture().inventory[0],record=sourceProfile(),selection=createLotNutritionSelection(lot,record,asOffNutriments(record,'g'),{confirmed:true});
 for(const change of [{id:'other'},{barcode:'2222'},{ingredient:'peas'},{unit:'ml'}])assert.equal(nutritionForLot({...lot,...change,nutritionSelection:selection},fixture().products),null);
});
test('rights-held, incompatible basis and unconfirmed selections are refused',()=>{
 const lot=fixture().inventory[0],record=sourceProfile(),n=asOffNutriments(record,'g');
 assert.throws(()=>createLotNutritionSelection(lot,record,n),/complete|source|basis/i);
 assert.throws(()=>createLotNutritionSelection(lot,{...record,provenance:{...record.provenance,status:'withdrawn'}},n,{confirmed:true}),/permit/i);
 assert.throws(()=>createLotNutritionSelection(lot,{...record,data:{...record.data,basis:{amount:100,unit:'ml'}}},n,{confirmed:true}),/basis/i);
 const mismatch=structuredClone(record);mismatch.data.nutrients.fat.basis.unit='ml';assert.throws(()=>createLotNutritionSelection(lot,mismatch,n,{confirmed:true}),/basis/i);
});
test('expired selection remains retained but is excluded from consumption',()=>{
 const lot=fixture().inventory[0],record=sourceProfile();record.provenance.retainUntil='2026-10-30T00:00:00Z';
 const selected=createLotNutritionSelection(lot,record,asOffNutriments(record,'g'),{confirmed:true,now:Date.parse('2026-10-29T00:00:00Z')});
 assert.equal(nutritionForLot({...lot,nutritionSelection:selected},fixture().products,{now:Date.parse('2026-10-31T00:00:00Z')}),null);
});
test('mapped values cannot diverge from the retained source profile or replace missing with zero',()=>{
 const lot=fixture().inventory[0],record=sourceProfile(),selected=createLotNutritionSelection(lot,record,asOffNutriments(record,'g'),{confirmed:true});
 for(const mutation of [s=>{s.nutriments.fat_100g=90;},s=>{s.nutriments.sugars_100g=0;}]){
  const changed=structuredClone(selected);mutation(changed);assert.throws(()=>copyLotNutritionSelection(changed));assert.equal(nutritionForLot({...lot,nutritionSelection:changed},fixture().products),null);
 }
});
