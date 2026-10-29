import test from 'node:test';import assert from 'node:assert/strict';
import {proposeShoppingHandoff,confirmShoppingHandoff} from '../../public/shopping-handoff-model.js';
const options={now:Date.parse('2026-10-16T00:00:00Z')};
const draft=()=>({id:'direct-1',scope:'account:a/kitchen:k',revision:'r1',kind:'retailer',records:[{id:'source:rice',kind:'product',data:{quantity:null,unit:null},provenance:{sourceId:'off',attribution:'synthetic'}}],detail:{destinationId:'manual-list'}});
test('direct helper rejects root/nested accessors without invoking them',()=>{
 for(const nested of [false,true]){
  const d=draft();let calls=0;const target=nested?d.records[0].data:d;const key=nested?'quantity':'scope';
  Object.defineProperty(target,key,{enumerable:true,get(){calls++;return nested?null:'account:a/kitchen:k';}});
  assert.throws(()=>proposeShoppingHandoff(d,options),/Plain JSON required/);assert.equal(calls,0);
 }
});
test('direct helper rejects root/nested toJSON code without executing or synthesizing a proposal',()=>{
 for(const nested of [false,true]){
  const d=draft();let calls=0;const target=nested?d.records[0].data:d;
  target.toJSON=()=>{calls++;return nested?{quantity:999,unit:'g'}:draft();};
  assert.throws(()=>proposeShoppingHandoff(d,options),/Plain JSON required/);assert.equal(calls,0);
 }
});
test('confirmation rejects a changed draft accessor before invoking it',()=>{
 const d=draft(),p=proposeShoppingHandoff(d,options);let calls=0;
 Object.defineProperty(d.records[0].data,'quantity',{enumerable:true,get(){calls++;return null;}});
 assert.throws(()=>confirmShoppingHandoff(d,{confirmed:true,scope:d.scope,revision:d.revision,proposalId:d.id,snapshot:p.snapshot},options),/Plain JSON required/);assert.equal(calls,0);
});
test('cycles, sparse/custom arrays, custom prototypes and non-JSON values reject with bounded errors',()=>{
 for(const mutate of [d=>d.detail.loop=d,d=>d.records.length=2,d=>d.records.extra='hidden',d=>d.detail=new Date(),d=>d.detail.bad=undefined,d=>d.detail.bad=()=>0,d=>d.detail.bad=Symbol('x'),d=>d.detail.bad=1n,d=>d.detail.bad=NaN,d=>d.detail.bad=Infinity,d=>Object.defineProperty(d.detail,'hidden',{value:1}),d=>d.detail[Symbol('x')]=1]){
  const d=draft();mutate(d);assert.throws(()=>proposeShoppingHandoff(d,options),/Plain JSON required|Invalid numeric value/);
 }
 const deep=draft();let cursor=deep.detail;for(let i=0;i<25;i++){cursor.child={};cursor=cursor.child;}assert.throws(()=>proposeShoppingHandoff(deep,options),/exceeds bounds/);
 const huge=draft();huge.detail.extra='x'.repeat(65537);assert.throws(()=>proposeShoppingHandoff(huge,options),/exceeds bounds/);
});
test('valid plain JSON, null prototypes, repeated references and __proto__ data preserve detached values',()=>{
 const d=draft(),shared={unknown:null};d.detail.first=shared;d.detail.second=shared;
 d.records[0].data=Object.assign(Object.create(null),{quantity:null,unit:null,preparation:'unknown'});
 Object.defineProperty(d.detail,'__proto__',{value:{source:'literal'},enumerable:true});
 const p=proposeShoppingHandoff(d,options);assert.equal(p.draft.records[0].data.quantity,null);assert.equal(p.draft.records[0].data.preparation,'unknown');assert.deepEqual(p.draft.detail.first,p.draft.detail.second);assert.ok(Object.hasOwn(p.draft.detail,'__proto__'));assert.equal(p.draft.detail.__proto__.source,'literal');
 const accepted=confirmShoppingHandoff(d,{confirmed:true,scope:d.scope,revision:d.revision,proposalId:d.id,snapshot:p.snapshot},options);assert.equal(accepted.status,'confirmed-proposal');
 p.draft.records[0].data.quantity=900;assert.equal(d.records[0].data.quantity,null);
});
