import test from 'node:test';
import assert from 'node:assert/strict';
import {analyzeWaste} from '../../apps/web/src/waste-analysis-model.js';
const context={accountId:'a'};
const row={accountId:'a',receiptId:'r',sourceId:'s',measured:true,quantity:1,unit:'g',costSnapshot:{sourceId:'s',quantity:1,unit:'g',amount:1,currency:'AUD'}};
test('finite quantities whose sum overflows reject instead of JSON null with known coverage',()=>{
 assert.throws(()=>analyzeWaste([{...row,quantity:Number.MAX_VALUE,costSnapshot:null},{...row,quantity:Number.MAX_VALUE,costSnapshot:null}],context),/aggregate overflow/);
});
test('finite costs whose sum overflows reject instead of JSON null with known coverage',()=>{
 const costly={...row,costSnapshot:{...row.costSnapshot,amount:Number.MAX_VALUE}};
 assert.throws(()=>analyzeWaste([costly,costly],context),/aggregate overflow/);
});
test('largest single finite observation remains valid; ordinary values preserve unknown coverage',()=>{
 const result=analyzeWaste([{...row,quantity:Number.MAX_VALUE,costSnapshot:null}],context);
 assert.equal(result.quantities[0].quantity,Number.MAX_VALUE);
 const mixed=analyzeWaste([row,{...row,sourceId:'other',costSnapshot:null}],context);
 assert.equal(mixed.values[0].amount,1);assert.equal(mixed.coverage.unknownValueRecords,1);
 assert.equal(mixed.records[1].value,null);assert.equal(JSON.parse(JSON.stringify(mixed)).quantities[0].quantity,2);
});
