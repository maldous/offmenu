import test from 'node:test';
import assert from 'node:assert/strict';
import {cookMeal} from '../public/cooking-model.js';
const recipe={id:'rice',title:'Measured rice',servings:1,ingredients:[{ingredient:'rice',quantity:100,unit:'g'}]};
const inventory=[{id:'lot',barcode:'1111',name:'Rice',ingredient:'rice',quantity:500,unit:'g'}];
function first(){return cookMeal({recipe,inventory,products:{},servings:2,date:'2026-10-29',planId:'plan-a',mutationId:'batch-a'});}
function retry(c,overrides={}){return cookMeal({recipe,inventory:c.inventory,products:{},servings:2,date:'2026-10-29',planId:'plan-a',mutationId:'batch-a',batches:[c.batch],...overrides});}
for(const [name,change] of Object.entries({recipe:{recipe:{...recipe,id:'other'}},servings:{servings:3},date:{date:'2026-10-30'}})){
 test('conflicting '+name+' is rejected before returning an existing cook',()=>{
  const c=first(),before=JSON.stringify(c);
  assert.throws(()=>retry(c,change),/changed|reconcile/i);assert.equal(JSON.stringify(c),before);
 });
}
test('same cook retry preserves batch and never deducts raw stock twice',()=>{
 const c=first(),r=retry(c);assert.equal(r.duplicate,true);assert.equal(r.batch,c.batch);assert.equal(r.inventory,c.inventory);assert.equal(c.inventory.find(x=>x.id==='lot').quantity,300);
});
test('same mutation retry may omit an already recorded plan binding',()=>{
 const c=first();assert.equal(retry(c,{planId:''}).duplicate,true);
});
test('same planned cook across a new mutation id remains idempotent',()=>{
 const c=first();assert.equal(retry(c,{mutationId:'batch-new'}).batch,c.batch);
});
test('an undone cook does not suppress a fresh cook request',()=>{
 const c=first();const r=cookMeal({recipe,inventory,products:{},servings:2,date:'2026-10-29',planId:'plan-a',mutationId:'batch-new',batches:[{...c.batch,undone:true}]});
 assert.equal(r.duplicate,false);assert.equal(r.batch.id,'batch-new');assert.equal(r.inventory.find(x=>x.id==='lot').quantity,300);
});
