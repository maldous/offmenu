import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import vm from 'node:vm';

const app=readFileSync(new URL('../../apps/web/src/app.js',import.meta.url),'utf8');
const source=app.split('\n').find(line=>line.startsWith('function storeReviewedRecipe(recipe)'));
assert.ok(source?.includes('sharing.canWrite()'));
function fixture({writable=true,deny=false}={}){
 const initial=[{id:'existing',title:'Existing'},{id:'sibling',title:'Sibling'}];
 let ctx;
 const operations=[];
 ctx=vm.createContext({
  recipeLibrary:null,lifecycleFixture:false,today:()=>'',fileDownload:()=>{},menuInventory:()=>[],
  setupRecipeLibrary:x=>x,sharing:{canWrite:()=>writable},t:s=>s,recipes:initial,
  validateRecipes:x=>x,RECIPES:'private-recipe-cache',
  localStorage:{setItem(key,value){operations.push({kind:'store',key,value:JSON.parse(value),before:ctx.recipes});if(deny)throw Error('Storage write refused');}},
  markDirty:()=>operations.push({kind:'dirty'}),findMeals:()=>operations.push({kind:'render'}),
 });
 vm.runInContext(source,ctx);
 return {initial,operations,ctx,save:ctx.storeReviewedRecipe};
}
test('a refused save keeps the original recipe array and siblings without marking or rendering',()=>{
 const f=fixture({deny:true});
 assert.throws(()=>f.save({id:'existing',title:'Unsaved edit'}),/Storage write refused/);
 assert.equal(f.ctx.recipes,f.initial);
 assert.deepEqual(f.ctx.recipes,[{id:'existing',title:'Existing'},{id:'sibling',title:'Sibling'}]);
 assert.deepEqual(f.operations.map(x=>x.kind),['store']);
});
test('a successful save writes before changing memory, then marks and renders once',()=>{
 const f=fixture();
 const edited={id:'existing',title:'Saved edit'};
 f.save(edited);
 const wanted=[edited,{id:'sibling',title:'Sibling'}];
 assert.deepEqual(Array.from(f.ctx.recipes),wanted);
 assert.deepEqual(f.operations.map(x=>x.kind),['store','dirty','render']);
 assert.equal(f.operations[0].before,f.initial);
 assert.equal(f.operations[0].key,'private-recipe-cache');
 assert.deepEqual(f.operations[0].value,wanted);
});
test('an uneditable kitchen does not validate or write a recipe',()=>{
 const f=fixture({writable:false});
 assert.throws(()=>f.save({id:'new'}),/Open an editable kitchen/);
 assert.equal(f.ctx.recipes,f.initial);
 assert.deepEqual(f.operations,[]);
});
