import test from 'node:test';
import assert from 'node:assert/strict';
import {createPrivateMenuPreview} from '../../apps/web/src/private-menu-preview.mjs';
const tag='a'.repeat(64),view=(more={})=>({schema:'offmenu-private-menu-preview/1',previewTag:tag,validUntil:2000,
  selectedPlanId:'good',options:[{planId:'good',status:'met'},{planId:'undecided',status:'unknown'}],checkedPlanId:null,persisted:false,...more});
const defer=()=>{let resolve;const promise=new Promise(r=>resolve=r);return {promise,resolve};};
function fixture(){
  const h={clock:1000,context:{authenticated:true,consentActive:true,accountId:'A',householdId:'H',memberId:'M',sessionGeneration:'v1',consentGeneration:'c1'},
    paints:[],requests:[],timers:new Map(),next:0,responder:async r=>view({checkedPlanId:r.planId??null})};
  h.ui=createPrivateMenuPreview({readContext:()=>h.context,watchContext:f=>{h.change=f;return ()=>{h.stopped=true;};},
    verify:async input=>{h.requests.push(input);return h.responder(input);},paint:x=>h.paints.push(x),clock:()=>h.clock,
    schedule:(fn,delay)=>{h.next++;h.timers.set(h.next,{fn,delay});return h.next;},cancel:id=>h.timers.delete(id)});
  return h;
}
test('shows only plan IDs and four-valued verdicts, never source specifics, freshness tag or enrollment',async()=>{
  const h=fixture();h.responder=async r=>view({checkedPlanId:r.planId??null,secretRule:'not public',options:[{planId:'good',status:'met',hidden:'not public'}]});
  const v=await h.ui.preview('window');assert.deepEqual(v,{state:'preview',options:[{planId:'good',status:'met'}],selectedPlanId:'good',persisted:false});
  assert.deepEqual(h.requests[0],{operation:'preview',memberId:'M',candidateSetId:'window'});
  const c=await h.ui.checkSelection('good');assert.deepEqual(c,{state:'rechecked',planId:'good',persisted:false});
  assert.equal(h.requests[1].previewTag,tag);assert.ok(!JSON.stringify(h.paints).includes(tag));assert.ok(!JSON.stringify(h.paints).includes('not public'));
  h.ui.dispose();assert.ok(h.stopped);assert.equal(h.timers.size,0);
});
test('rejects changed audience even without a callback, and synchronously clears an observed revocation',async()=>{
  const h=fixture();await h.ui.preview('window');h.context.consentActive=false;h.change();
  assert.equal(h.paints.at(-1).state,'unavailable');assert.equal((await h.ui.checkSelection('good')).state,'unavailable');
  assert.equal(h.requests.length,1);h.context.consentActive=true;await h.ui.preview('window');
  h.context.memberId='N';assert.equal((await h.ui.checkSelection('good')).state,'unavailable');assert.equal(h.requests.length,2);
});
test('delayed previews that resolve after scope change, replacement or dispose cannot paint stale output',async()=>{
  for(const action of ['changed','replaced','disposed']){
    const h=fixture(),d=defer();h.responder=()=>d.promise;const waiting=h.ui.preview('old');
    if(action==='changed'){h.context.sessionGeneration='new';h.change();}
    if(action==='replaced'){h.responder=async()=>view({selectedPlanId:'new',options:[{planId:'new',status:'met'}]});await h.ui.preview('new');}
    if(action==='disposed')h.ui.dispose();d.resolve(view());assert.equal((await waiting).state,'unavailable');
    assert.equal(h.paints.at(-1).state,action==='replaced'?'preview':'unavailable');
    if(action==='replaced')assert.equal(h.paints.at(-1).selectedPlanId,'new');
  }
});
test('unsupported or expired verdicts cannot enable selection; changed recheck never persists anything',async()=>{
  for(const change of [{selectedPlanId:'undecided'},{validUntil:1000},{previewTag:'unverified'},{persisted:true},
       {options:[{planId:'good',status:'maybe'}]},{options:[{planId:'good',status:'met'},{planId:'good',status:'met'}]}]){
    const h=fixture();h.responder=async()=>view(change);assert.equal((await h.ui.preview('window')).state,'unavailable');}
  const h=fixture();await h.ui.preview('window');h.responder=async()=>view({previewTag:'b'.repeat(64),checkedPlanId:'good'});
  assert.equal((await h.ui.checkSelection('good')).state,'unavailable');
  await h.ui.preview('window');h.responder=async()=>view();await h.ui.preview('window');const [timer]=h.timers.values();
  assert.equal(timer.delay,1000);h.clock=2000;timer.fn();assert.equal(h.paints.at(-1).state,'unavailable');
});
test('no signed-in member, active consent, watcher or per-operation verifier means no preview',async()=>{
  for(const change of [{authenticated:false},{consentActive:false},{memberId:''},{sessionGeneration:''},{accountId:''}]){
    const h=fixture();Object.assign(h.context,change);assert.equal((await h.ui.preview('x')).state,'unavailable');assert.equal(h.requests.length,0);}
  assert.throws(()=>createPrivateMenuPreview({}));const h=fixture();await h.ui.preview('x');
  assert.equal((await h.ui.checkSelection('undecided')).state,'unavailable');assert.equal(h.requests.length,1);
});

test('a missed audience event during a recheck still erases the previously painted view',async()=>{
  const h=fixture();await h.ui.preview('window');const d=defer();h.responder=()=>d.promise;
  const waiting=h.ui.checkSelection('good');h.context.householdId='changed';d.resolve(view({checkedPlanId:'good'}));
  assert.equal((await waiting).state,'unavailable');assert.equal(h.paints.at(-1).state,'unavailable');
});
