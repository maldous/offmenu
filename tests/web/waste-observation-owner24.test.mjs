import test from 'node:test';
import assert from 'node:assert/strict';
import {validateState} from '../../apps/web/server/state.mjs';
import {validateWasteObservation,wasteObservationCoverage,persistWasteObservation} from '../../apps/web/server/waste-observation-owner24.mjs';
const context={accountId:'a',sessionEpoch:'epoch-1',consent:true};
const row={id:'o1',accountId:'a',receiptId:'r1',sourceId:'lot1',observedAt:'2026-10-14T10:00:00.000Z',quantity:125,unit:'g',reason:'uneaten',provenance:{sourceRef:'receipt:r1/lot:lot1',method:'measured'}};
test('actual production state entrypoint drops observations: integration remains blocked',()=>{
 const lot={id:'lot1',barcode:'12345678',name:'Rice',ingredient:'rice',quantity:500,unit:'g',location:{area:'Bench',shelf:'Bowl'}};
 const result=validateState({inventory:[lot],products:{},recipes:[],profile:{servings:1,wasteObservations:[row],waste:[{mode:'waste',area:'Bench',shelf:'Bowl',startedAt:row.observedAt,finishedAt:row.observedAt,items:[{...lot,wasteObservation:row}]}]}});
 assert.equal(result.profile.wasteObservations,undefined);
 assert.equal(result.profile.waste[0].items[0].wasteObservation,undefined);
});
test('dates, provenance, unknown and measured zero survive serialized storage; units remain separate',()=>{
 const values=[row,{...row,id:'o2',quantity:null,unit:null},{...row,id:'o3',quantity:0},{...row,id:'o4',quantity:1,unit:'kg'}];
 const result=wasteObservationCoverage(JSON.parse(JSON.stringify(values)),context);
 assert.deepEqual(result.coverage,{total:4,knownQuantity:3,unknownQuantity:1});
 assert.deepEqual(result.quantities,[{unit:'g',quantity:125},{unit:'kg',quantity:1}]);assert.equal(result.records[0].observedAt,row.observedAt);assert.deepEqual(result.records[0].provenance,row.provenance);
});
test('invalid dates, inferred measurements, wrong account and missing consent rejected',()=>{
 for(const input of [{...row,observedAt:'2026-02-30T10:00:00.000Z'},{...row,accountId:'b'},{...row,provenance:{...row.provenance,method:'assumed'}},{...row,quantity:-1}])assert.throws(()=>validateWasteObservation(input,context));
 assert.throws(()=>validateWasteObservation(row,{...context,consent:false}));
});
test('persistence awaits atomic write and rejects stale scope/revision and revoked authorization',async()=>{
 let disk={accountId:'a',sessionEpoch:'epoch-1',revision:0,observations:[],wasteReceipts:[{id:'r1',items:[{id:'lot1',unit:'g',discardQuantity:125}]}]};
 const store={read:async()=>JSON.parse(JSON.stringify(disk)),compareAndSwap:async(ctx,revision,observations)=>{if(ctx.sessionEpoch!==disk.sessionEpoch||revision!==disk.revision)return false;disk={...disk,revision:revision+1,observations:JSON.parse(JSON.stringify(observations))};return true;}};
 assert.equal((await persistWasteObservation({store,context,observation:row,expectedRevision:0})).revision,1);
 await assert.rejects(persistWasteObservation({store,context,observation:{...row,id:'tooMuch',quantity:126},expectedRevision:1}),/exceeds/);
 await assert.rejects(persistWasteObservation({store,context,observation:{...row,id:'missing',sourceId:'other'},expectedRevision:1}),/binding/);
 assert.deepEqual(disk.observations,[row]);await assert.rejects(persistWasteObservation({store,context,observation:row,expectedRevision:0}),/Revision/);
 await assert.rejects(persistWasteObservation({store,context,observation:row,expectedRevision:1}),/Duplicate/);
 await assert.rejects(persistWasteObservation({store:{...store,compareAndSwap:async()=>false},context,observation:{...row,id:'new'},expectedRevision:1}),/authorization/);
 disk.sessionEpoch='new';await assert.rejects(persistWasteObservation({store,context,observation:row,expectedRevision:1}),/scope/);
});
