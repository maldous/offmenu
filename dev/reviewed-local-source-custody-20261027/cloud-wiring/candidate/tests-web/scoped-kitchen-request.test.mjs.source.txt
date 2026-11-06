import test from 'node:test';
import assert from 'node:assert/strict';
import {captureKitchenScope,createScopedKitchenRequest} from '../public/scoped-kitchen-request.js';
const deferred=()=>{let resolve;const promise=new Promise(r=>resolve=r);return {promise,resolve};};
const scope=()=>({owner:'account-a',key:'pantry-user-a',demo:false,generation:0,selected:{id:'kitchen-a'}});
const stale={code:'KITCHEN_SCOPE_CHANGED'};
for(const [field,value] of [['owner','account-b'],['key','pantry-user-b'],['demo',true],['generation',1],['selected',{id:'kitchen-b'}]]) {
 test('rejects '+field+' change during session refresh before dispatch',async()=>{
  let current=scope(),calls=0;const refresh=deferred();
  const request=createScopedKitchenRequest({getScope:()=>current,refreshSession:()=>refresh.promise,request:async()=>{calls++;return Response.json({});}});
  const pending=request('/api/kitchens/kitchen-a/state',{method:'PUT',body:'{"state":"private-a"}'});
  current={...current,[field]:value};refresh.resolve();
  await assert.rejects(pending,stale);assert.equal(calls,0);
 });
}
test('rejects account change while response headers are pending',async()=>{
 let current=scope();const headers=deferred();const request=createScopedKitchenRequest({getScope:()=>current,refreshSession:async()=>{},request:()=>headers.promise});
 const pending=request('/api/kitchens');await Promise.resolve();current={...current,owner:'account-b'};headers.resolve(Response.json({kitchens:[]}));await assert.rejects(pending,stale);
});
test('rejects delayed JSON body after account reset, including same account',async()=>{
 let current=scope();const body=deferred(),bodyStarted=deferred();const request=createScopedKitchenRequest({getScope:()=>current,refreshSession:async()=>{},request:async()=>({ok:true,json(){bodyStarted.resolve();return body.promise;}})});
 const pending=request('/api/kitchens/kitchen-a/state');await bodyStarted.promise;current={...current,generation:1};body.resolve({state:{inventory:['private-a']}});await assert.rejects(pending,stale);
});
test('preserves response/value and request options within unchanged scope',async()=>{
 const current=scope(),options={method:'PUT',body:'{"revision":1}'},response=Response.json({revision:2});let sent;
 const request=createScopedKitchenRequest({getScope:()=>({...current}),refreshSession:async()=>{},request:async(...args)=>{sent=args;return response;}});
 const result=await request('/api/kitchens/kitchen-a/state',options);assert.equal(result.response,response);assert.deepEqual(result.value,{revision:2});assert.deepEqual(sent,['/api/kitchens/kitchen-a/state',options]);
});
test('selection transition guard allows closing current kitchen but not account change',()=>{
 let current=scope();const check=captureKitchenScope(()=>current,{selection:false});current={...current,selected:null};assert.doesNotThrow(check);current={...current,owner:'account-b'};assert.throws(check,stale);
});
test('same kitchen id in a new selection object invalidates an old request',()=>{
 let current=scope();const check=captureKitchenScope(()=>current);current={...current,selected:{id:'kitchen-a'}};assert.throws(check,stale);
});
