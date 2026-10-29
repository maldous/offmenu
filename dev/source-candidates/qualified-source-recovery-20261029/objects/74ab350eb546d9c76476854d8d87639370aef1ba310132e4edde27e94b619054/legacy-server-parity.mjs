import {readFileSync,writeFileSync} from 'node:fs';
import vm from 'node:vm';import assert from 'node:assert/strict';
import {preserveCookingWitnesses} from '../public/cooking-witness.js';
const source=readFileSync(new URL('./server-history-helper.js',import.meta.url),'utf8');
const f=vm.runInNewContext('('+source+')',{T:[],__offmenuCookingWitness198:{preserveCookingWitnesses}});
const base={id:'entry-a',title:'Rice',recipeId:'rice',date:'2026-10-29',slot:'Dinner',servings:0,memberId:'',source:'Historical entry',createdAt:'2026-10-29T12:00:00Z',totals:{}};
let checks=0;
for(const fields of [{},{intakeKnown:false,completion:null},{intakeKnown:true,completion:0}]){const a=f({history:[{...base,...fields}]});assert.equal(a.history[0].servedPortions,undefined);assert.equal(JSON.stringify(f(a)),JSON.stringify(a));checks++;}
for(const fields of [{servedPortions:2},{servings:2}]){const a=f({history:[{...base,...fields}]});assert.equal(a.history[0].servedPortions,2);assert.equal(JSON.stringify(f(a)),JSON.stringify(a));checks++;}
for(const servedPortions of [0,-1]){assert.throws(()=>f({history:[{...base,servedPortions}]}),/Invalid served portions/);checks++;}
const result={checks,pass:checks,fail:0,scope:'Existing seven legacy server-history case families reused from production195 history-server-parity.cjs; helper locator/namespace adapted, prior fix not reapplied.'};
writeFileSync(new URL('../legacy-server-parity-summary.json',import.meta.url),JSON.stringify(result,null,2));console.log(JSON.stringify(result));
