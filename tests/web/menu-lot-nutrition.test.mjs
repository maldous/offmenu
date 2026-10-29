import test from 'node:test';
import assert from 'node:assert/strict';
import {planSummary} from '../../public/menu-model.js';
import {matchMeals} from '../../public/model.js';
import {quantified} from '../../public/ingredients.js';
import {readFileSync} from 'node:fs';
import vm from 'node:vm';
import {cookMeal} from '../../public/cooking-model.js';
import {validateState} from '../../cloud/state.mjs';
import {kitchenProjection,applyKitchen} from '../../public/sync-model.js';

// Synthetic ingredient joins and product nutrition; no corpus or private inputs.
const date='2026-10-26';
const recipe={id:'rice',title:'Synthetic rice',servings:1,ingredients:[{ingredient:'rice',quantity:100,unit:'g'}]};
const meal={recipeId:'rice',date,servings:1};
const lots=[
 {id:'a',barcode:'a',ingredient:'rice',quantity:20,unit:'g',expires:'2026-10-27'},
 {id:'b',barcode:'b',ingredient:'rice',quantity:80,unit:'g',expires:'2026-10-28'},
];
const products=Object.fromEntries([['a',10],['b',30]].map(([id,protein])=>[id,{product_quantity:100,product_quantity_unit:'g',nutrition_data_per:'100g',nutriments:{proteins_100g:protein}}]));
const summary=(inventory=lots,p=products,plan=[meal],r=recipe)=>planSummary(plan,[r],inventory,p,[date]);

test('100g demand uses20g at10 plus80g at30:26g protein, matching cooking in either inventory order',()=>{
 for(const inventory of [lots,[...lots].reverse()]){
  const before=structuredClone(inventory);
  const s=summary(inventory);
  const cooked=cookMeal({recipe,inventory,products,servings:1,date,mutationId:'synthetic-batch'});
  assert.equal(cooked.batch.totals.proteins_100g.value,26);
  assert.deepEqual(s.totals.proteins_100g,cooked.batch.totals.proteins_100g);
  assert.equal(s.missing.length,0);
  assert.deepEqual(inventory,before);
 }
});

test('FEFO allocation and depletion across meals agree with cooking',()=>{
 const inventory=[{...lots[1],quantity:200},{...lots[0],quantity:60}];
 const first=cookMeal({recipe,inventory,products,servings:1,date,mutationId:'first'});
 const second=cookMeal({recipe,inventory:first.inventory,products,servings:1,date,mutationId:'second'});
 assert.equal(summary(inventory).totals.proteins_100g.value,18);
 assert.equal(summary(inventory,products,[meal,{...meal}]).totals.proteins_100g.value,
  first.batch.totals.proteins_100g.value+second.batch.totals.proteins_100g.value);
});

test('uncovered quantity and unknown lot nutrients stay incomplete; generic estimate is separate',()=>{
 const genericRecipe={...recipe,nutrition:{proteins_100g:99,source:'generic estimate'}};
 const partial=summary([lots[0]],products,[meal],genericRecipe);
 assert.equal(partial.missing[0].quantity,80);
 assert.deepEqual(partial.totals.proteins_100g,{value:2,known:1,total:2});
 const unknown=summary(lots,{...products,b:{...products.b,nutriments:{}}});
 assert.deepEqual(unknown.totals.proteins_100g,{value:2,known:1,total:2});
 assert.deepEqual(unknown.totals.fat_100g,{value:0,known:0,total:2});
 assert.equal(genericRecipe.nutrition.source,'generic estimate');
 assert.equal(genericRecipe.nutrition.proteins_100g,99);
});

test('expired/review stock, incompatible nutrient units and cooked plans do not invent nutrition',()=>{
 for(const invalid of [{expires:'2026-10-25'},{needsReview:true}]){
  const s=summary(lots.map(l=>({...l,...invalid})));
  assert.equal(s.missing[0].quantity,100);
  assert.deepEqual(s.totals.proteins_100g,{value:0,known:0,total:1});
 }
 const incompatible=summary(lots,{a:{...products.a,nutrition_data_per:'100ml'},b:products.b});
 assert.deepEqual(incompatible.totals.proteins_100g,{value:24,known:1,total:2});
 const cooked=summary(lots,products,[{...meal,cookBatchId:'already-cooked'}]);
 assert.equal(cooked.missing.length,0);
 assert.deepEqual(cooked.totals.proteins_100g,{value:0,known:0,total:1});
 const unresolved=summary(lots,products,[meal],{...recipe,servingsUnknown:true});
 assert.equal(unresolved.unresolved,1);
 assert.deepEqual(unresolved.totals.proteins_100g,{value:0,known:0,total:1});
});

test('real applyNutrition callback retains imported profile binding separately from500ml package',()=>{
 const source=readFileSync(new URL('../../public/app.js',import.meta.url),'utf8');
 const start=source.indexOf('applyNutrition:(lot,record,nutriments)=>');
 assert.ok(start>=0);
 const callback=source.slice(start+'applyNutrition:'.length,source.indexOf('}});',start)+1);
 const p={a:{name:'Synthetic rice',product_quantity:500,product_quantity_unit:'ml'}};
 let stored;
 const context={products:p,structuredClone,PRODUCTS:'synthetic',localStorage:{setItem(key,value){stored=value;}},markDirty(){},findMeals(){}};
 const apply=vm.runInNewContext('('+callback+')',context);
 const profile={id:'synthetic:profile',kind:'nutrientProfile',status:'unverified',provenance:{sourceId:'synthetic',visibility:'private'},data:{basis:{amount:100,unit:'g',state:'as-described'}}};
 apply(lots[0],profile,{proteins_100g:12});
 assert.equal(p.a.product_quantity,500);
 assert.equal(p.a.product_quantity_unit,'ml');
 assert.equal(p.a.nutritionProvenance.nutrientProfile.id,profile.id);
 assert.deepEqual(p.a.nutritionProvenance.nutrientProfile.basis,profile.data.basis);
 assert.equal(p.a.nutritionProvenance.nutrientProfile.status,'unverified');
 // Exercise actual JSON persistence, cloud validation and shared-kitchen projection.
 const persisted=JSON.parse(stored).a;
 const state=validateState({inventory:[],products:{'1111':persisted},recipes:[],selections:[],profile:{country:'AU',units:'metric',servings:1}});
 assert.deepEqual(state.products['1111'].nutritionProvenance,persisted.nutritionProvenance);
 const privateKitchen=kitchenProjection(state);
 assert.equal(privateKitchen.products['1111'].nutriments,undefined);
 assert.equal(privateKitchen.products['1111'].nutritionProvenance,undefined);
 state.products['1111'].nutritionProvenance.visibility='public';
 const shared=applyKitchen(state,JSON.parse(JSON.stringify(kitchenProjection(state))));
 assert.deepEqual(shared.products['1111'].nutritionProvenance.nutrientProfile,persisted.nutritionProvenance.nutrientProfile);
 assert.equal(shared.products['1111'].product_quantity_unit,'ml');
 assert.equal(summary([{...lots[0],barcode:'1111',quantity:100}],shared.products).totals.proteins_100g.value,12);
 profile.data.basis.unit='ml';
 assert.equal(p.a.nutritionProvenance.nutrientProfile.basis.unit,'g');
 for(const unit of ['g','ml']){
  const r={...recipe,ingredients:[{ingredient:'rice',quantity:100,unit}]};
  const inventory=[{...lots[0],quantity:100,unit}];
  const planned=summary(inventory,p,[meal],r);
  const cooked=cookMeal({recipe:r,inventory,products:p,servings:1,date,mutationId:'basis-'+unit});
  assert.deepEqual(planned.totals.proteins_100g,cooked.batch.totals.proteins_100g);
  assert.equal(planned.totals.proteins_100g.value,unit==='g'?12:0);
  assert.equal(planned.totals.proteins_100g.known,unit==='g'?1:0);
 }
});

test('findMeals wording describes allocated lots and unknown uncovered nutrition',()=>{
 const source=readFileSync(new URL('../../public/app.js',import.meta.url),'utf8');
 const handler=source.slice(source.indexOf('function findMeals(){'),source.indexOf("\n$('refresh').onclick"));
 assert.ok(handler.includes('Based on allocated ingredient lots with a compatible nutrition basis'));
 assert.ok(handler.includes('Uncovered amounts and missing nutrition remain unknown.'));
 assert.equal(handler.includes('first matching mapped product'),false);
});

test('renderPlan caption uses localized contribution counts including uncovered demand',()=>{
 const source=readFileSync(new URL('../../public/app.js',import.meta.url),'utf8');
 const handler=source.slice(source.indexOf('function renderPlan(){'));
 const start=handler.indexOf('n.known<n.total?');
 const expression=handler.slice(start,handler.indexOf(');}for(const [id,list]',start));
 const calls=[];
 const t=(key,values={})=>{calls.push(key);return key.replace(/\{(v\d+)\}/g,(_,id)=>values[id]);};
 const caption=n=>vm.runInNewContext(expression,{n,t});
 assert.equal(caption({known:2,total:3}),'2/3 nutrition contributions have data (allocated lots and unknown amounts)');
 assert.equal(caption({known:0,total:1}),'0/1 nutrition contributions have data (allocated lots and unknown amounts)');
 assert.equal(caption({known:2,total:2}),'Estimate from allocated lots');
 assert.ok(calls[0].includes('{v0}/{v1}'));
 assert.equal(expression.includes('ingredient entries'),false);
});

test('missing nutrient denominator never inherits package units; explicit100ml is supported',()=>{
 const r={...recipe,ingredients:[{ingredient:'rice',quantity:100,unit:'ml'}]};
 const inventory=[{...lots[0],quantity:100,unit:'ml'}];
 for(const product of [
  {product_quantity:500,product_quantity_unit:'ml',nutriments:{proteins_100g:12}},
  {nutrition_data_per:'100ml',nutritionProvenance:{sourceId:'lost-binding'},nutriments:{proteins_100g:12}},
  {nutritionProvenance:{nutrientProfile:{basis:{amount:1,unit:'g'}}},nutriments:{proteins_100g:12}},
 ]){
  assert.equal(summary(inventory,{a:product},[meal],r).totals.proteins_100g.known,0);
  assert.equal(cookMeal({recipe:r,inventory,products:{a:product},servings:1,date,mutationId:'unknown'}).batch.totals.proteins_100g.known,0);
 }
 const product={product_quantity:500,product_quantity_unit:'g',nutrition_data_per:'100ml',nutriments:{proteins_100g:12}};
 assert.equal(summary(inventory,{a:product},[meal],r).totals.proteins_100g.value,12);
});

test('readiness, planning and cooking reject zero/nonfinite/nonpositive measured demand',()=>{
 for(const quantity of [0,-1,NaN,Infinity]){
  const r={...recipe,ingredients:[{ingredient:'rice',quantity,unit:'g'}]};
  assert.equal(quantified(r),false);
  assert.equal(matchMeals([], [r],1,date)[0].status,'needs_review');
  assert.equal(summary([],products,[meal],r).unresolved,1);
  assert.throws(()=>cookMeal({recipe:r,inventory:[],products,servings:1,date,mutationId:'invalid'}));
 }
});
