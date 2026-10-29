import test from 'node:test';
import assert from 'node:assert/strict';
import { analyzeWaste } from '../../public/waste-analysis-model.js';
const row = { accountId:'kitchen-a', receiptId:'receipt-1', sourceId:'lot-1', quantity:125, unit:'g', measured:true, reason:'oversized-pack', season:'spring', costSnapshot:{sourceId:'lot-1', quantity:500, unit:'g', amount:4, currency:'AUD'}, packOptions:[{sourceId:'offer-1', quantity:250, unit:'g', season:'spring'}] };
const run = records => analyzeWaste(records, {accountId:'kitchen-a'});
test('partial measured discard values proportionally and retains missing cost coverage', () => {
 const input=[row,{...row,sourceId:'lot-2',costSnapshot:null,quantity:50}];
 const before=JSON.stringify(input); const result=run(input);
 assert.deepEqual(result.values,[{currency:'AUD',amount:1,knownRecords:1}]);
 assert.equal(result.coverage.unknownValueRecords,1);
 assert.deepEqual(result.quantities,[{unit:'g',quantity:175}]);
 assert.equal(result.records[0].sourceId,'lot-1');
 assert.equal(result.records[1].value,null);
 assert.equal(JSON.stringify(input),before);
 assert.deepEqual(result.suggestions[0].packSourceIds,['offer-1']);
});
test('unknown quantities, stale cost identity and mixed currencies do not become zero or combine',()=>{
 const result=run([{...row,measured:false},{...row,sourceId:'lot-2'}, {...row,costSnapshot:{...row.costSnapshot,currency:'USD'}}]);
 assert.equal(result.coverage.unknownQuantityRecords,1);
 assert.equal(result.coverage.unknownValueRecords,2);
 assert.deepEqual(result.values,[{currency:'USD',amount:1,knownRecords:1}]);
 assert.equal(result.records[0].quantity,null);
});
test('missing reason/season, unknown quantity and incompatible pack units suppress suggestions',()=>{
 for(const change of [{reason:null},{season:null},{measured:false},{packOptions:[{sourceId:'x',quantity:1,unit:'kg',season:'spring'}]}]) assert.deepEqual(run([{...row,...change}]).suggestions,[]);
});
test('account boundary fails closed and oversized/invalid cost snapshots stay unknown',()=>{
 assert.throws(()=>run([{...row,accountId:'other'}]),/account/);
 assert.throws(()=>analyzeWaste([row],{}),/account/);
 for(const quantity of [100,0,NaN]) assert.equal(run([{...row,costSnapshot:{...row.costSnapshot,quantity}}]).records[0].value,null);
 assert.equal(run([{...row,costSnapshot:{...row.costSnapshot,amount:0}}]).records[0].value.amount,0);
});
