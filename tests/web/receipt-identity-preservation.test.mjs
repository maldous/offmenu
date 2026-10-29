import test from 'node:test';
import assert from 'node:assert/strict';
import {validateState} from '../../apps/web/server/state.mjs';
const lot={id:'synthetic-stock',barcode:'12345678',name:'Rice',ingredient:'rice',quantity:500,unit:'g',location:{area:'Bench',shelf:'Bowl'}};
const receipt=(id='receipt:1')=>({id,mode:'waste',area:'Bench',shelf:'Bowl',startedAt:'2026-10-14T10:00:00Z',finishedAt:'2026-10-14T10:01:00Z',items:[{...lot}]});
const state=(r=receipt())=>({inventory:[{...lot}],products:{},recipes:[],profile:{servings:1,uiLanguage:'ar',dataLanguage:'ja',lastReceipt:r,waste:[r]}});
test('preserves explicitly supplied receipt IDs through JSON state round trip without changing source identities',()=>{
 const input=state(),before=structuredClone(input);const output=validateState(JSON.parse(JSON.stringify(input)));
 assert.equal(output.profile.lastReceipt.id,'receipt:1');assert.equal(output.profile.waste[0].id,'receipt:1');
 assert.equal(output.profile.waste[0].items[0].id,lot.id);assert.equal(output.profile.uiLanguage,'ar');assert.equal(output.profile.dataLanguage,'ja');assert.deepEqual(input,before);
 assert.deepEqual(validateState(JSON.parse(JSON.stringify(output))),output);
});
test('legacy receipts stay unlinked and IDs are never fabricated',()=>{
 const r=receipt();delete r.id;const result=validateState(state(r));
 assert.equal(Object.hasOwn(result.profile.lastReceipt,'id'),false);assert.equal(Object.hasOwn(result.profile.waste[0],'id'),false);
});
test('rejects malformed explicit receipt IDs and duplicate waste receipt IDs',()=>{
 for(const id of ['', '   ',null,7,{},'x'.repeat(201)])assert.throws(()=>validateState(state(receipt(id))),/receipt ID/);
 const input=state();input.profile.waste.push(receipt());assert.throws(()=>validateState(input),/Duplicate waste receipt IDs/);
});
test('distinct waste IDs and current unrelated validation remain intact',()=>{
 const input=state();input.profile.waste.push(receipt('receipt:2'));assert.equal(validateState(input).profile.waste.length,2);
 input.inventory[0].quantity=-1;assert.throws(()=>validateState(input));
});
