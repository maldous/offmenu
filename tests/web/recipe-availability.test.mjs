import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {readRecipeAvailability} from '../../apps/web/src/recipe-availability.js';

test('two successful empty recipe reads are distinct from partial or unavailable responses',async()=>{
 const base='/recipes.json?v=i18n-1', api='/api/recipes';
 const result=(a,b)=>readRecipeAvailability(async url=>{
  assert.ok([base,api].includes(url));const item=url===base?a:b;
  if(item instanceof Error)throw item;return item;
 });
 const failure=new Error('induced isolated catalogue error');
 assert.deepEqual(await result([],[]),{status:'loaded',recipes:[]});
 assert.deepEqual(await result([],failure),{status:'partial',recipes:[]});
 assert.deepEqual(await result(failure,[]),{status:'partial',recipes:[]});
 assert.deepEqual(await result(failure,failure),{status:'unavailable',recipes:[]});
 const saved={id:'fixture',title:'trusted baseline'}, newer={id:'fixture',title:'newer existing API precedence'};
 assert.deepEqual(await result([saved],failure),{status:'partial',recipes:[saved]});
 assert.deepEqual(await result(failure,[newer]),{status:'partial',recipes:[newer]});
 assert.deepEqual(await result([saved],[newer]),{status:'loaded',recipes:[newer]});
 assert.deepEqual(await result([],{}),{status:'partial',recipes:[]});
 const source=readFileSync(new URL('../../apps/web/src/app.js',import.meta.url),'utf8');
 assert.match(source,/recipeAvailability==='unavailable'\?'The recipe catalogue did not load/);
 assert.match(source,/recipeAvailability==='loaded'\?'No matching menus in the recipes loaded/);
 assert.match(source,/result.owner===requestIdentity&&result.ticket===recipeAvailabilityTicket/);
});

test('malformed rows are not a definitive empty result and do not erase valid rows',async()=>{
 const valid={id:'synthetic-valid'};
 const result=await readRecipeAvailability(async path=>path.startsWith('/api/')?[null,{id:'reject'}]:[valid],row=>{
  if(row?.id==='reject')throw Error('invalid recipe shape');
  return row;
 });
 assert.deepEqual(result,{recipes:[valid],status:'partial'});
 assert.deepEqual(await readRecipeAvailability(async()=>[null]),{recipes:[],status:'unavailable'});
});

test('older startup cannot replace newer rows or status in memory or storage', async()=>{
 const {runInNewContext}=await import('node:vm');
 const {readFileSync}=await import('node:fs');
 const app=readFileSync(new URL('../../apps/web/src/app.js',import.meta.url),'utf8');
 const fetchSource=app.slice(app.indexOf('async function fetchRecipes(){'),app.indexOf('function switchAccount('));
 const initSource=app.slice(app.indexOf('async function init(){'),app.indexOf('function markDirty(){'));
 const pending=[];
 const saved=[];
 const c={readRecipeAvailability:()=>new Promise(resolve=>pending.push(resolve)),validateRecipes:rows=>rows,validateLot:row=>row,
  jsonFetch:async()=>({}), initAuth:async()=>{},loadProfile(){},pantry(){},findMeals(){},connectivity(){},
  localStorage:{getItem(){return null},setItem(key,rows){saved.push(JSON.parse(rows));}},
  navigator:{}, msg(message){throw Error(message)},t(message,values){return values?.v0||message}};
 runInNewContext(`let requestIdentity={},recipeAvailabilityTicket=0,recipeAvailability='local-only',recipes=[],lots=[],products={};const KEY='k',PRODUCTS='p',RECIPES='r',lifecycleFixture=true; ${fetchSource}${initSource} globalThis.start=init;globalThis.snapshot=()=>JSON.stringify({recipes,status:recipeAvailability});`,c);
 const older=c.start(),newer=c.start();
 for(let i=0;i<6&&pending.length!==2;i++)await Promise.resolve();
 assert.equal(pending.length,2);
 pending[1]({recipes:[{id:'new'}],status:'loaded'});await newer;
 pending[0]({recipes:[{id:'old'}],status:'partial'});await older;
 assert.deepEqual(JSON.parse(c.snapshot()),{recipes:[{id:'new'}],status:'loaded'});
 assert.deepEqual(saved,[[{id:'new'}]]);
});
