import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {runInNewContext} from 'node:vm';
const src=readFileSync(new URL('../../apps/web/src/insights-ui.js',import.meta.url),'utf8');
const markup=readFileSync(new URL('../../apps/web/assets/index.html',import.meta.url),'utf8');
const handler=src.split('\n').find(line=>line.startsWith("$('shopping-add-form').onsubmit="));
function fixture(){
 let writes=0,renders=0,focus=0,warnings=0,n=0;
 const name={value:'',focus(){focus++},reportValidity(){warnings++;return false;}},amount={value:'1 pack'},form={}, profile={shopping:[{id:'original',name:'Existing'}]};
 runInNewContext(handler,{$:id=>({'shopping-name':name,'shopping-amount':amount,'shopping-add-form':form})[id],
 data:()=>({profile}),persist:()=>writes++,renderShopping:()=>renders++,crypto:{randomUUID:()=>String(++n)}});
 return {name,amount,profile,submit(value){name.value=value;form.onsubmit({preventDefault(){}});},calls:()=>[writes,renders,focus,warnings]};
}
test('whitespace-only manual name makes no list write and reports the native required input',()=>{
 assert.match(markup,/<input id="shopping-name"[^>]*\brequired\b/);
 const f=fixture(); f.submit(' \u00a0\t ');
 assert.deepEqual(f.calls(),[0,0,1,1],'Blank manual row must not be written');
 assert.equal(f.profile.shopping.length,1); assert.equal(f.name.value,''); assert.equal(f.amount.value,'1 pack');
});
test('trimmed duplicate labels remain separately identified and no note is synthesized',()=>{
 const f=fixture(); f.submit('  Rice '); f.amount.value=''; f.submit('Rice');
 assert.deepEqual(f.calls(),[2,2,0,0]); assert.equal(f.profile.shopping.length,3); assert.equal(f.profile.shopping[1].name,'Rice');
 assert.equal(f.profile.shopping[1].amount,'1 pack'); assert.equal(f.profile.shopping[2].amount,''); assert.notEqual(f.profile.shopping[1].id,f.profile.shopping[2].id);
});
