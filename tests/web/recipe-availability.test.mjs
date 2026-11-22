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
 assert.match(source,/owner===requestIdentity&&ticket===recipeAvailabilityTicket/);
});
