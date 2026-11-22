import test from 'node:test';
import assert from 'node:assert/strict';
import {planSummary} from '../../apps/web/src/menu-model.js';
import {shoppingItems} from '../../apps/web/src/integrations.js';
const date='2026-11-23';
const recipe={id:'synthetic',servings:1,ingredients:[{ingredient:'synthetic measure',quantity:Number.MAX_VALUE,unit:'g'}]};
const plan=[{date,recipeId:recipe.id,servings:2}];
const inventory=[{id:'synthetic-lot',ingredient:'synthetic measure',quantity:100,unit:'g',barcode:'synthetic-barcode'}];
const products={'synthetic-barcode':{nutrition_data_per:'100g',nutriments:{'energy-kcal_100g':100}}};
test('unrepresentable scaled demand is unresolved, not Infinity, and allocates no stock',()=>{
 const original=structuredClone(inventory);
 const summary=planSummary(plan,[recipe],inventory,products,[date]);
 assert.equal(summary.unresolved,1);
 assert.deepEqual(summary.requirements,[]);
 assert.deepEqual(summary.missing,[]);
 assert.deepEqual(shoppingItems({plan},[recipe],inventory,products,date),[]);
 assert.equal(summary.totals['energy-kcal_100g'].known,0);
 assert.equal(summary.totals['energy-kcal_100g'].total,1);
 assert.deepEqual(inventory,original);
});

test('underflow from positive inputs stays unresolved without hiding a finite neighbor',()=>{
 const mixed={id:'mixed',servings:2,ingredients:[
  {ingredient:'tiny',quantity:Number.MIN_VALUE,unit:'g'},
  {ingredient:'ordinary',quantity:10,unit:'g'}
 ]};
 const meals=[{date,recipeId:mixed.id,servings:1}];
 const summary=planSummary(meals,[mixed],[],{},[date]);
 assert.equal(summary.unresolved,1);
 assert.deepEqual(summary.requirements,[{ingredient:'ordinary',unit:'g',quantity:5}]);
 assert.deepEqual(summary.missing,[{ingredient:'ordinary',unit:'g',quantity:5}]);
});
