import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import test from 'node:test';
import vm from 'node:vm';

test('Guest Find puts focus back on an invalid typed barcode without changing the field or staging',async()=>{
 const source=readFileSync(new URL('../../apps/web/src/app.js',import.meta.url),'utf8');
 const lookup=source.match(/^async function lookup\(\)\{.*\}$/m)?.[0];
 assert.ok(lookup,'execute the isolated explicit Find handler only');
 const field={value:'12',focus(){calls.push('input-focused')}};
 const calls=[];
 const invoke=vm.runInNewContext(lookup+';lookup',{
  lifecycleFixture:false,location:{pathname:'/'},$:(id)=>{assert.equal(id,'barcode');return field;},
  products:Object.create(null),autoAccept:()=>assert.fail('must not stage an invalid barcode'),
  openRetainedScanner:()=>assert.fail('Guest lane should not navigate'),t:key=>key,
  msg:key=>calls.push(key),
 });
 await invoke();
 assert.deepEqual(calls,['input-focused','Enter a barcode with 4–32 digits.']);
 assert.equal(field.value,'12');
});
