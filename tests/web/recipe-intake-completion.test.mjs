import test from 'node:test';
import assert from 'node:assert/strict';
import {recipeIntakeSnapshot,intakeSummary,validateInsights} from '../../apps/web/src/insights-model.js';

const date='2026-10-25';
const input=()=>({date,slot:'Dinner',servings:2,memberId:'sam',note:'User note',
  recipe:{id:'rice',title:'Rice',servings:1,ingredients:[{ingredient:'rice',quantity:100,unit:'g'}]},
  inventory:[{id:'lot',barcode:'12345678',ingredient:'rice',quantity:500,unit:'g'}],
  products:{'12345678':{quantity:'500 g',nutrition_data_per:'100g',nutriments:{fat_100g:2}}}});

test('blank recipe completion records serving with unknown intake through validation and aggregation',()=>{
  const meal=recipeIntakeSnapshot(input());
  assert.equal(meal.completion,null);assert.equal(meal.intakeKnown,false);
  assert.equal(meal.servedPortions,2);assert.equal(meal.servings,0);
  assert.match(meal.note,/User note.*unknown/);
  const stored=validateInsights({history:[meal]}).history[0];
  assert.equal(stored.intakeKnown,false);assert.equal(stored.completion,null);
  const nutrient=intakeSummary([stored],[date],'sam').totals.fat_100g;
  assert.equal(nutrient.value,0);assert.equal(nutrient.known,0);assert.ok(nutrient.total>0);
});

test('explicit zero is known no intake, distinct from blank completion',()=>{
  const meal=recipeIntakeSnapshot({...input(),completion:0});
  assert.equal(meal.completion,0);assert.equal(meal.intakeKnown,true);
  assert.equal(meal.servings,0);assert.equal(meal.totals.fat_100g.value,0);
  assert.ok(meal.totals.fat_100g.known>0);
});

test('partial and full completion scale consumed portions and nutrients once, preserving missing data',()=>{
  const half=recipeIntakeSnapshot({...input(),completion:50});
  const full=recipeIntakeSnapshot({...input(),completion:100});
  assert.equal(half.servings,1);assert.equal(full.servings,2);
  assert.equal(half.totals.fat_100g.value,2);assert.equal(full.totals.fat_100g.value,4);
  assert.equal(full.totals.iron_100g.known,0);
  assert.equal(full.servedPortions,2);assert.equal(half.intakeKnown,true);
});

test('unknown and known records aggregate without treating the unknown serving as a complete zero',()=>{
  const unknown=recipeIntakeSnapshot(input());
  const known=recipeIntakeSnapshot({...input(),completion:50});
  const summary=intakeSummary([unknown,known],[date],'sam');
  assert.equal(summary.totals.fat_100g.value,2);
  assert.ok(summary.totals.fat_100g.known<summary.totals.fat_100g.total);
  assert.equal(summary.meals.length,2);
});

test('invalid completion and serving quantities are rejected without mutating input',()=>{
  for(const completion of [-1,101,NaN,Infinity,'100'])assert.throws(()=>recipeIntakeSnapshot({...input(),completion}));
  for(const servings of [0,-1,Infinity,1001])assert.throws(()=>recipeIntakeSnapshot({...input(),servings}));
  const data=input(),before=structuredClone(data);recipeIntakeSnapshot({...data,completion:50});
  assert.deepEqual(data,before);
});
