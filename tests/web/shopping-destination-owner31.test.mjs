import test from 'node:test';import assert from 'node:assert/strict';
import {createShoppingDestinationBoundary} from '../../public/shopping-destination-owner31.mjs';
import {createShoppingHandoff,RETAINED_HELPER_PIN} from '../../public/shopping-handoff-owner31.mjs';
import * as helper from '../../public/shopping-handoff-model.js';
function setup(){
 let clock=1000,calls=0;
 const state={accountId:'alice',kitchenId:'one',revision:'r1',sessionEpoch:'s1',canExport:true,demo:false,policies:{},data:{profile:{country:'AU',plan:[],shopping:[{id:'rice',name:'أرز',amount:'unknown pack',checked:false}]},recipes:[],inventory:[],products:{},date:'2026-10-15',usePantry:true},bindings:[{lineId:'rice',accountId:'alice',kitchenId:'one',revision:'r1',admitted:true,record:{id:'personal:rice',kind:'product',data:{quantity:null,unit:null},provenance:{sourceId:'personal-import',privateUseConfirmed:true,attribution:'synthetic owner fixture'}}}]};
 const policy={version:'review-1',destinations:[{id:'manual-list',url:'https://shop.example/list',markets:['AU'],enabled:true,expiresAt:5000}]};
 const context=()=>({accountId:state.accountId,kitchenId:state.kitchenId,revision:state.revision,sessionEpoch:state.sessionEpoch,market:state.data.profile.country,canExport:state.canExport,demo:state.demo});
 const handoff=createShoppingHandoff({read:()=>state,now:()=>clock,helper:{pin:RETAINED_HELPER_PIN,reviewRef:'synthetic only; independent review pending',propose:helper.proposeShoppingHandoff,confirm:helper.confirmShoppingHandoff}});
 const boundary=createShoppingDestinationBoundary({handoff:{preview:r=>handoff.preview(r),confirm:(...a)=>{calls++;return handoff.confirm(...a);}},readPolicy:()=>policy,readContext:context,now:()=>clock});
 return {state,policy,boundary,request:{id:'p1',kind:'retailer',destinationId:'manual-list'},tick:n=>clock=n,calls:()=>calls};
}
test('default is blocked; unapproved IDs and request URLs/credentials never reach confirmation',()=>{
 assert.throws(()=>createShoppingDestinationBoundary().preview({id:'x',kind:'retailer',destinationId:'manual-list'}));
 const s=setup();for(const r of [{...s.request,destinationId:'other'},{...s.request,destinationId:'https://evil.example/'},{...s.request,url:'https://evil.example/'},{...s.request,credentials:{token:'secret'}},{...s.request,kind:'purchase'}])assert.throws(()=>s.boundary.preview(r));assert.equal(s.calls(),0);
});
test('credentials, unsafe/noncanonical URLs and unknown registry fields reject',()=>{
 for(const url of ['https://user:secret@shop.example/list','https://@shop.example/list','http://shop.example/list','javascript:alert(1)','//shop.example/list','https://shop.example/list?token=secret','https://shop.example/list#secret','https://shop.example:8443/list','https://shop.example/\nlist','https://shop.example/list?','https://shop.example/list#']){
  const s=setup();s.policy.destinations[0].url=url;assert.throws(()=>s.boundary.preview(s.request),url);assert.equal(s.calls(),0);
 }
 const s=setup();s.policy.destinations[0].token='secret';assert.throws(()=>s.boundary.preview(s.request),/Unsupported fields/);
});
test('actual reviewed handoff chain preserves detached quantities, uncertainty and provenance',()=>{
 for(const measured of [false,true]){
  const s=setup();if(measured)Object.assign(s.state.data.profile.shopping[0],{quantity:400,unit:'g',amount:'400 g'});
  const p=s.boundary.preview(s.request);assert.throws(()=>s.boundary.confirm(p),/Explicit confirmation/);
  const result=s.boundary.confirm(p,{confirmed:true});assert.equal(result.status,'destination-approved-proposal');assert.equal(result.destination.url,'https://shop.example/list');
  const line=result.handoff.draft.detail.lines[0];assert.equal(line.quantity,measured?400:null);assert.equal(line.unit,measured?'g':null);assert.deepEqual(line.sourceRecordIds,['personal:rice']);if(!measured)assert.ok(line.uncertainty.length);
  result.handoff.draft.records[0].provenance.attribution='changed';assert.equal(s.state.bindings[0].record.provenance.attribution,'synthetic owner fixture');
  assert.throws(()=>s.boundary.confirm(p,{confirmed:true}),/Explicit confirmation/);
 }
});
test('policy withdrawal, URL/market/epoch/revision changes and expiry block before underlying confirm',()=>{
 for(const mutate of [s=>s.policy.version='review-2',s=>s.policy.destinations=[],s=>s.policy.destinations[0].enabled=false,s=>s.policy.destinations[0].url='https://shop.example/other',s=>s.policy.destinations[0].markets=['NZ'],s=>s.state.accountId='bob',s=>s.state.kitchenId='two',s=>s.state.revision='r2',s=>s.state.sessionEpoch='s2',s=>s.state.data.profile.country='NZ',s=>s.tick(5000),s=>s.state.canExport=false,s=>s.state.demo=true]){
  const s=setup(),p=s.boundary.preview(s.request);mutate(s);assert.throws(()=>s.boundary.confirm(p,{confirmed:true}));assert.equal(s.calls(),0);
 }
});
test('list/source changes still recheck existing confirmation/rights contract',()=>{
 for(const mutate of [s=>s.state.data.profile.shopping[0].quantity=200,s=>s.state.bindings[0].record.provenance.attribution='changed',s=>s.state.bindings[0].record.provenance.status='withdrawn',s=>s.state.data.profile.shopping[0].checked=true]){
  const s=setup(),p=s.boundary.preview(s.request);mutate(s);assert.throws(()=>s.boundary.confirm(p,{confirmed:true}));assert.equal(s.calls(),1);
 }
});
test('mutated/forged preview, duplicate policy IDs and non-boolean enabled reject',()=>{
 const s=setup(),p=s.boundary.preview(s.request);p.destination.url='https://evil.example/';assert.throws(()=>s.boundary.confirm(p,{confirmed:true}),/changed/);assert.equal(s.calls(),0);
 assert.throws(()=>s.boundary.confirm(structuredClone(p),{confirmed:true}),/Explicit confirmation/);
 for(const mutate of [s=>s.policy.destinations.push(structuredClone(s.policy.destinations[0])),s=>s.policy.destinations[0].enabled='true']){
  const a=setup();mutate(a);assert.throws(()=>a.boundary.preview(a.request));
 }
});
test('request accessors do not execute; original request/policy mutations cannot redirect an issued preview',()=>{
 const s=setup();let accessed=0;const r={...s.request};Object.defineProperty(r,'destinationId',{enumerable:true,get(){accessed++;return 'manual-list';}});assert.throws(()=>s.boundary.preview(r),/Plain/);assert.equal(accessed,0);
 const a=setup(),p=a.boundary.preview(a.request);a.request.destinationId='other';assert.equal(a.boundary.confirm(p,{confirmed:true}).destination.id,'manual-list');
});
