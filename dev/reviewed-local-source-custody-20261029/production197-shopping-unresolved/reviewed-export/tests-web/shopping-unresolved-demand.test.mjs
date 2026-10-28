import test from 'node:test';
import assert from 'node:assert/strict';
import {shoppingItems} from '../public/integrations.js';
import {planSummary} from '../public/menu-model.js';
const date='2026-10-29',recipe={id:'rice',title:'Rice',servings:1,source:'Synthetic source',license:'CC0',ingredients:[{ingredient:'rice',quantity:100,unit:'g'}],instructions:[]};
const profile={plan:[{id:'meal',recipeId:'rice',date,slot:'Dinner',servings:2}]};
for(const [name,change]of Object.entries({'source review':{needsReview:true},'unknown yield':{servingsUnknown:true},'invalid yield':{servings:0}})){
 test(name+' remains visible in shopping without an invented quantity',()=>{
  const r={...recipe,...change},summary=planSummary(profile.plan,[r],[],{},[date]);assert.ok(summary.unresolved>0);
  const items=shoppingItems(profile,[r],[],{},date);assert.equal(items.length,1);assert.equal(items[0].id,'review:rice');assert.equal(items[0].amount,'Review source quantity');assert.equal(items[0].quantity,undefined);
 });
}
test('zero required amount is unresolved rather than an empty shopping list',()=>{
 const items=shoppingItems(profile,[{...recipe,ingredients:[{ingredient:'rice',quantity:0,unit:'g'}]}],[],{},date);
 assert.equal(items.length,1);assert.equal(items[0].id,'review:rice');assert.equal(items[0].quantity,undefined);
});
test('partly measured recipe keeps only its unresolved ingredient in review',()=>{
 const r={...recipe,ingredients:[...recipe.ingredients,{ingredient:'seasoning',quantity:null}]};
 const items=shoppingItems(profile,[r],[],{},date);assert.deepEqual(items.map(i=>i.id),['planned:rice|g','review:seasoning']);assert.equal(items[0].quantity,200);
});
test('optional unresolved ingredients never become purchases or review requirements',()=>{
 const r={...recipe,ingredients:[...recipe.ingredients,{ingredient:'seasoning',quantity:null,optional:true}]};
 assert.deepEqual(shoppingItems(profile,[r],[],{},date).map(i=>i.id),['planned:rice|g']);
});
test('pantry stock cannot resolve an unknown serving basis',()=>{
 const inventory=[{id:'lot',ingredient:'rice',quantity:1000,unit:'g'}];
 assert.deepEqual(shoppingItems(profile,[recipe],inventory,{},date),[]);
 const items=shoppingItems(profile,[{...recipe,servingsUnknown:true}],inventory,{},date);assert.deepEqual(items.map(i=>i.id),['review:rice']);
});
test('source text, checked state, custom additions and inputs are preserved',()=>{
 const r={...recipe,needsReview:true,ingredients:[{ingredient:'rice',raw:'Two handfuls of rice',quantity:100,unit:'g'}]},custom={id:'custom',name:'Tea',amount:'1 box',checked:false};
 const p={...profile,shoppingChecked:['review:Two handfuls of rice'],shopping:[custom]},before=JSON.stringify({p,r});
 const items=shoppingItems(p,[r],[],{},date);assert.equal(items[0].name,'Two handfuls of rice');assert.equal(items[0].checked,true);assert.equal(items.at(-1),custom);assert.equal(JSON.stringify({p,r}),before);
});
