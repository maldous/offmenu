import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {createContext,runInContext} from 'node:vm';
const source=readFileSync(new URL('../../apps/web/src/app.js',import.meta.url),'utf8');
const start=source.indexOf("\$('recipe-import').onchange=");
const end=source.indexOf('function connectivity()',start);
assert.ok(start>=0&&end>start);
const mounted=source.slice(start,end);
async function run(existing,incoming){
 const input={value:'selected'},writes=[],status=[],effects=[];
 const context=createContext({$:id=>id==='account-dialog'?{open:true}:input,readJSON:async()=>incoming,validateRecipes:x=>x,
  recipeImportGeneration:0,requestIdentity:{},clearAccountFileErrors:()=>{},showAccountFileError:(_id,e)=>status.push(e.message),
  recipes:existing,RECIPES:'private-test-key',localStorage:{setItem:(k,v)=>writes.push([k,JSON.parse(v)])},
  markDirty:()=>effects.push('dirty'),findMeals:()=>effects.push('render'),msg:x=>status.push(x),t:x=>x});
 runInContext(mounted,context);await input.onchange();assert.equal(input.value,'');
 return {writes,status,effects,recipes:JSON.parse(JSON.stringify(context.recipes))};
}
const old={id:'one',title:'Original',metadata:{b:2,a:1},steps:['First','Second']};
const same={steps:['First','Second'],metadata:{a:1,b:2},title:'Original',id:'one'};
const second={id:'two',title:'New'};
test('mounted recipe import rejects divergent existing and same-file IDs atomically',async()=>{
 for(const [existing,incoming] of [[[old],[second,{...same,steps:['Second','First']}]],[[old],[second,{...second,title:'Conflict'}]]]){
  const result=await run(existing,incoming);
  assert.deepEqual(result.writes,[]);assert.deepEqual(result.effects,[]);assert.deepEqual(result.recipes,existing);
  assert.match(result.status[0],/matching ID/);
 }
});
test('mounted recipe import preserves identical records, collapses same-file copies and writes only new IDs',async()=>{
 const unchanged=await run([old],[same,same]);assert.deepEqual(unchanged.writes,[]);assert.deepEqual(unchanged.effects,[]);
 const result=await run([old],[same,second,second]);
 assert.deepEqual(result.writes,[['private-test-key',[old,second]]]);
 assert.deepEqual(result.effects,['dirty','render']);
});
