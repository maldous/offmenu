import test from 'node:test';
import assert from 'node:assert/strict';
import {planSummary} from '../../public/menu-model.js';
import {matchMeals} from '../../public/model.js';
const date='2026-10-26';
const recipe={id:'generated:review-boundary',servings:2,ingredients:[{ingredient:'rice',quantity:100,unit:'g'}]};
const plan=[{recipeId:recipe.id,date,servings:2}];
const stock={barcode:'1111',ingredient:'rice',quantity:100,unit:'g'};
const products={'1111':{product_quantity:100,product_quantity_unit:'g',nutrition_data_per:'100g',nutriments:{'energy-kcal_100g':350}}};
test('menu demand stays unresolved while the same recipe is withheld by stock readiness',()=>{
 const held={...recipe,needsReview:true};
 assert.equal(matchMeals([stock],[held],2,date)[0].status,'needs_review');
 const summary=planSummary(plan,[held],[stock],products,[date]);
 assert.equal(summary.unresolved,1);
 assert.deepEqual(summary.requirements,[]);assert.deepEqual(summary.missing,[]);
 assert.equal(summary.totals['energy-kcal_100g'].known,0);
 assert.equal(summary.totals['energy-kcal_100g'].total,1);
});
test('expired stock cannot supply menu nutrition after allocation rejects it',()=>{
 const summary=planSummary(plan,[recipe],[{...stock,expires:'2026-10-25'}],products,[date]);
 assert.equal(summary.missing[0].quantity,100);
 assert.equal(summary.totals['energy-kcal_100g'].known,0);
});
test('usable explicitly mapped generated stock still connects quantities to conditional menu values',()=>{
 const summary=planSummary(plan,[recipe],[stock],products,[date]);
 assert.equal(summary.unresolved,0);assert.equal(summary.requirements[0].quantity,100);
 assert.deepEqual(summary.missing,[]);assert.equal(summary.totals['energy-kcal_100g'].value,350);
 assert.equal(summary.totals['energy-kcal_100g'].known,1);
 assert.equal(summary.totals.fat_100g.known,0);
});
test('unknown yields, nonpositive amounts and unsupported units never become measured requirements',()=>{
 for(const held of [{...recipe,servings:0},{...recipe,servings:NaN},
   {...recipe,servingsUnknown:true},
   {...recipe,ingredients:[{ingredient:'rice',quantity:-10,unit:'g'}]},
   {...recipe,ingredients:[{ingredient:'rice',quantity:100,unit:'cup'}]}]){
  const summary=planSummary(plan,[held],[stock],products,[date]);
  assert.equal(summary.unresolved,1);assert.deepEqual(summary.requirements,[]);
  assert.equal(summary.totals['energy-kcal_100g'].known,0);
 }
});

test('package units without an explicit nutrient basis leave nutrition unknown',()=>{
 const {nutrition_data_per,...packageOnly}=products['1111'];
 const summary=planSummary(plan,[recipe],[stock],{'1111':packageOnly},[date]);
 assert.deepEqual(summary.missing,[]);
 assert.deepEqual(summary.totals['energy-kcal_100g'],{value:0,known:0,total:1});
});
