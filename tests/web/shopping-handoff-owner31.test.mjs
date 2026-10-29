import test from 'node:test';
import assert from 'node:assert/strict';
import {createShoppingHandoff, RETAINED_HELPER_PIN} from '../../public/shopping-handoff-owner31.mjs';
import {shoppingItems} from '../../public/integrations.js';
import * as retained from '../../public/shopping-handoff-model.js';
const fixture=()=>({accountId:'alice',kitchenId:'one',revision:'r7',sessionEpoch:'login-1',canExport:true,demo:false,policies:{},data:{profile:{country:'AU',plan:[],shopping:[{id:'custom:rice',name:'Rice',amount:'Review source amount',checked:false}]},recipes:[],inventory:[],products:{},date:'2026-10-14',usePantry:true},bindings:[{lineId:'custom:rice',accountId:'alice',kitchenId:'one',revision:'r7',admitted:true,record:{id:'personal:rice',kind:'product',data:{quantity:null,unit:null},provenance:{sourceId:'personal-import',privateUseConfirmed:true,attribution:'Synthetic personal fixture'}}}]});
function setup(){let state=fixture(), clock=Date.parse('2026-10-14T10:00:00Z');const controller=createShoppingHandoff({read:()=>state,now:()=>clock,helper:{pin:RETAINED_HELPER_PIN,reviewRef:'synthetic-test-only-not-independent-review',propose:retained.proposeShoppingHandoff,confirm:retained.confirmShoppingHandoff}});return {controller,state,tick:n=>clock+=n,request:{id:'handoff-1',kind:'retailer',destinationId:'retailer:manual'}};}
test('actual shoppingItems entrypoint feeds quantity/provenance preview and confirmation, without mutation',()=>{
 const {state,controller,request}=setup(),before=structuredClone(state);
 assert.equal(shoppingItems(state.data.profile,[],[],{},state.data.date)[0].id,'custom:rice');
 const preview=controller.preview(request),line=preview.draft.detail.lines[0];
 assert.equal(line.quantity,null);assert.equal(line.unit,null);assert.deepEqual(line.sourceRecordIds,['personal:rice']);assert.ok(line.uncertainty.length);
 assert.throws(()=>controller.confirm(preview),/confirmation/);
 const result=controller.confirm(preview,{confirmed:true});assert.equal(result.status,'confirmed-proposal');assert.deepEqual(state,before);
 assert.throws(()=>controller.confirm(preview,{confirmed:true}),/confirmation/);
});
test('current measured quantities from shoppingItems survive unchanged',()=>{
 const {state,controller,request}=setup();Object.assign(state.data.profile.shopping[0],{quantity:250,unit:'g',amount:'250 g'});
 const p=controller.preview(request);assert.equal(p.draft.detail.lines[0].quantity,250);assert.equal(controller.confirm(p,{confirmed:true}).draft.detail.lines[0].unit,'g');
});
test('account, kitchen, revision, session, quantity, collected-state and preview changes require fresh review',()=>{
 for(const mutate of [s=>s.accountId='bob',s=>s.kitchenId='two',s=>s.revision='r8',s=>s.sessionEpoch='login-2',s=>s.data.profile.shopping[0].quantity=90,s=>s.data.profile.shopping[0].checked=true]){
  const {state,controller,request}=setup(),p=controller.preview(request);mutate(state);assert.throws(()=>controller.confirm(p,{confirmed:true}));
 }
 const {controller,request}=setup(),p=controller.preview(request);p.draft.detail.destinationId='other';assert.throws(()=>controller.confirm(p,{confirmed:true}),/changed/);
 assert.throws(()=>controller.confirm(structuredClone(p),{confirmed:true}),/confirmation/);
});
test('missing/admission-denied/expired provenance blocks, including at confirmation',()=>{
 for(const mutate of [s=>s.bindings=[],s=>s.bindings[0].admitted=false,s=>s.bindings[0].record.provenance.sourceId='unknown-provider',s=>s.demo=true,s=>s.canExport=false]){
  const {state,controller,request}=setup();mutate(state);assert.throws(()=>controller.preview(request));
 }
 const {state,controller,request,tick}=setup();state.bindings[0].record.provenance.retainUntil='2026-10-14T10:00:01Z';const p=controller.preview(request);tick(1000);assert.throws(()=>controller.confirm(p,{confirmed:true}),/expired/);
});
test('accessor, sparse array and purchase requests reject; no getter executes',()=>{
 const {state,controller,request}=setup();let calls=0;Object.defineProperty(state,'accountId',{get(){calls++;return 'alice';},enumerable:true});assert.throws(()=>controller.preview(request),/Plain/);assert.equal(calls,0);
 const a=setup();a.state.bindings.length=2;assert.throws(()=>a.controller.preview(a.request),/Dense/);
 const b=setup();assert.throws(()=>b.controller.preview({...b.request,kind:'purchase'}),/Retailer/);
});
test('composition on current develop calculates the reviewed recipe gap without inventing a pack',()=>{
 const {state,controller,request}=setup();
 state.data.profile.shopping=[];
 state.data.profile.plan=[{recipeId:'riceRecipe',date:'2026-10-14',servings:4},{recipeId:'riceRecipe',date:'2026-10-15',servings:4}];
 state.data.recipes=[{id:'riceRecipe',servings:1,ingredients:[{ingredient:'rice',quantity:75,unit:'g'}]}];
 state.data.inventory=[{id:'stock',ingredient:'rice',quantity:200,unit:'g'}];
 state.bindings[0].lineId='planned:rice|g';
 const p=controller.preview(request),line=p.draft.detail.lines[0];
 assert.equal(line.quantity,400);assert.equal(line.unit,'g');assert.equal(line.packCount,undefined);
 assert.equal(controller.confirm(p,{confirmed:true}).draft.detail.lines[0].quantity,400);
});
test('changed locale fallback composes with preserved Arabic labels, null quantity and source identity',async()=>{
 const {browserLocaleDecision}=await import('../../public/i18n.js');
 const decision=browserLocaleDecision({documentElement:{dataset:{offmenuDefaultLocale:'ar'}},cookie:''},{getItem:()=>null},{languages:[]});
 assert.deepEqual(decision,{locale:'ar',source:'default'});
 const {state,controller,request}=setup();
 state.data.profile.shopping[0].name='أرز';state.data.profile.shopping[0].amount='كمية غير معروفة';
 const p=controller.preview(request),line=p.draft.detail.lines[0];
 assert.equal(line.name,'أرز');assert.equal(line.amount,'كمية غير معروفة');assert.equal(line.quantity,null);
 assert.deepEqual(line.sourceRecordIds,['personal:rice']);
 assert.equal(controller.confirm(p,{confirmed:true}).draft.detail.lines[0].name,'أرز');
});
