import assert from 'node:assert/strict';
import test from 'node:test';
import {matchMeals,normalize} from '../../apps/web/src/model.js';
const ingredient='Batch A | test';
const date='2026-11-23';
const recipe={id:'test',servings:1,ingredients:[{ingredient,quantity:40,unit:'g'}]};
const stock=[{ingredient,quantity:40,unit:'ml'}];
test('a valid separator in a recipe name cannot alter its shortage identity or unit',()=>{
 assert.match(normalize(ingredient),/\|/);
 for (const forRestock of [false,true]){
  const [row]=matchMeals(stock,[recipe],1,date,{forRestock});
  assert.equal(row.status,'missing');
  assert.deepEqual(row.missing,[{ingredient:normalize(ingredient),unit:'g',quantity:40}]);
 }
});
