import test from 'node:test';
import assert from 'node:assert/strict';
import {validateInsights} from '../public/insights-model.js';
const base={id:'entry-a',title:'Rice',recipeId:'rice',date:'2026-10-29',slot:'Dinner',servings:0,memberId:'',source:'Historical entry',createdAt:'2026-10-29T12:00:00Z',totals:{fat_100g:{value:0,known:0,total:1}}};
function normalize(entry){return validateInsights({history:[entry]});}
for(const [name,fields] of Object.entries({legacy:{},unknown:{intakeKnown:false,completion:null},'known zero completion':{intakeKnown:true,completion:0}})){
 test(name+' without served amount remains valid across repeated saves',()=>{
  const first=normalize({...base,...fields}),second=validateInsights(first);
  assert.deepEqual(second,first);assert.equal(first.history[0].servedPortions,undefined);
  assert.equal(first.history[0].servings,0);
 });
}
test('explicit known served amount survives zero consumption',()=>{
 const first=normalize({...base,intakeKnown:true,completion:0,servedPortions:2});
 assert.equal(first.history[0].servedPortions,2);assert.deepEqual(validateInsights(first),first);
});
test('positive legacy consumption retains its existing fallback served amount',()=>{
 const first=normalize({...base,servings:2});
 assert.equal(first.history[0].servedPortions,2);assert.deepEqual(validateInsights(first),first);
});
test('explicit zero or negative served amount is still invalid',()=>{
 for(const servedPortions of [0,-1])assert.throws(()=>normalize({...base,servedPortions}),/served portions/i);
});
test('known zero and unknown nutrient counts remain unchanged',()=>{
 const totals={fat_100g:{value:0,known:1,total:1},salt_100g:{value:0,known:0,total:1}};
 const first=normalize({...base,servedPortions:1,totals});
 assert.deepEqual(first.history[0].totals,totals);assert.deepEqual(validateInsights(first),first);
});
