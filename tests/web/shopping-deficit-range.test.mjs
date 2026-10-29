import test from 'node:test';
import assert from 'node:assert/strict';
import {calculateShoppingDeficit} from '../../dev/shopping-deficit.mjs';
const row=(rowRef,quantity)=>({rowRef,quantity,ingredientId:'synthetic:a',unit:'g',basis:'synthetic:dry'});
test('rejects exact requirement aggregates above binary64 maximum before rounding',()=>{
 assert.throws(()=>calculateShoppingDeficit({requirements:[row('r1',Number.MAX_VALUE),row('r2',1e292)],available:[row('a1',Number.MAX_VALUE)]}),RangeError);
});
test('rejects exact stock aggregates above binary64 maximum before rounding',()=>{
 assert.throws(()=>calculateShoppingDeficit({requirements:[row('r1',1)],available:[row('a1',Number.MAX_VALUE),row('a2',1e292)]}),RangeError);
});
test('retains maximum single quantity, tiny quantities and exact-zero deficits',()=>{
 for(const quantity of [Number.MAX_VALUE,Number.MIN_VALUE,0]){
 const result=calculateShoppingDeficit({requirements:[row('r1',quantity)],available:[row('a1',quantity)]});
 assert.equal(result.complete,true);assert.equal(result.groups[0].requiredQuantity,quantity);assert.equal(result.groups[0].deficit,0);
 }
});
test('accepts aggregate below exact maximum and rejects overflow in unknown groups',()=>{
 const result=calculateShoppingDeficit({requirements:[row('r1',Number.MAX_VALUE),row('r2',1e290)],available:[]});
 assert.equal(result.groups[0].requiredQuantity,Number.MAX_VALUE);
 assert.throws(()=>calculateShoppingDeficit({requirements:[row('r1',Number.MAX_VALUE),row('r2',1e292),row('r3',null)],available:[]}),RangeError);
});
