import test from 'node:test';
import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
import {createEnvelopeCryptor} from '../../apps/web/server/byoc-envelope-v1.mjs';
import {createPrivateMenuPreview} from '../../apps/web/src/private-menu-preview.mjs';
import {createPrivateMenuPolicy} from '../../apps/web/server/private-menu-policy.mjs';
const pin=v=>createHash('sha256').update(canonical(v)).digest('hex');
function canonical(v){return Array.isArray(v)?'['+v.map(canonical).join(',')+']':v&&typeof v==='object'?'{'+Object.keys(v).sort().map(k=>JSON.stringify(k)+':'+canonical(v[k])).join(',')+'}':JSON.stringify(v);}
const N='urn:fixture:measure:n',I='urn:fixture:ingredient:i',A='urn:fixture:attribute:a',day='2026-01-02',M='b'.repeat(64),H='a'.repeat(64),T=1000;
const proposal=(op='preview',more={})=>({operation:op,memberId:'member1',candidateSetId:'plans',...more});
const rule=(kind,targetId,extra={})=>({kind,targetId,period:'per-meal',severity:'hard',ruleId:'r',from:day,through:day,
  ...((kind.startsWith('require-')||kind.startsWith('exclude-'))?{quantifier:kind.startsWith('require-')?'any-item':'every-item'}:{unit:'mg',magnitude:'300',inclusive:true}),...extra});
const variant=(id,ingredient,attribute)=>({variantId:id,revision:'v',evidence:H,ingredients:{[I]:{state:ingredient,evidence:H}},
  attributes:{[A]:{state:attribute,evidence:M}},nutrients:{[N]:{magnitude:'0.6',unit:'g',basis:'per-recipe',evidence:M}},yieldServings:'2',yieldEvidence:H});
const plan=(id,v)=>({planId:id,zone:'Pacific/Auckland',days:[day],completeDays:[day],entries:[{entryId:'meal',day,mealId:'lunch',variantId:v,revision:'v',servings:'1'}]});
async function home({rules=[rule('exclude-ingredient',I)],alter=()=>{},tweak=()=>{}}={}){
  const p={accountId:'owner',householdId:'hh',memberId:'member1',consentId:'consent',profileRevision:'p1',zone:'Pacific/Auckland',
    purpose:'private-menu-plan',profileVersion:'offmenu-private-dietary-planning-profile/1',rules};
  const plans=[plan('good','x'),plan('bad','y'),plan('unsure','z')],variants=[variant('x','absent','present'),variant('y','present','absent'),variant('z','unknown','unknown')];
  alter(p,plans,variants);
  const key=await crypto.subtle.generateKey({name:'AES-GCM',length:256},false,['encrypt','decrypt']);
  const binding={ownerUserId:'owner',kitchenId:'hh',objectType:'household_profile',objectId:'env',purpose:'private-menu-plan',providerId:null};
  const envelope=await createEnvelopeCryptor({resolveKey:async()=>key}).seal(p,binding,{keyRef:'external-key',keyVersion:1});
  const a={...Object.fromEntries(['accountId','householdId','memberId','consentId','profileRevision','zone','purpose'].map(k=>[k,p[k]])),
    sessionId:'sess',sessionGeneration:'s1',consentRevision:2,choice:'granted',validFrom:0,expiresAt:3000,sessionExpiresAt:4000,sessionActive:true,
    profileActive:true,candidateSetId:'plans',profileSha256:pin(p),plansSha256:pin(plans),variantsSha256:pin(variants),envelopeId:'env',keyRef:'external-key',keyVersion:1,requestAuthorized:true};
  const s={a,snap:{envelope,plans,variants},calls:[],now:T,actor:'owner',phase:null};tweak(s);
  const fire=phase=>{s.calls.push(phase);s.phase?.(phase,s);};
  const verify=createPrivateMenuPolicy({clock:()=>s.now,acquireOperationGuard:s.noGuard?undefined:async()=>{
    fire('acquire');let active=true;return {assertCurrent(phase){fire('guard:'+phase);return active&&s.lost!==true;},release(){active=false;fire('release');}};},
    verifiedUser:async()=>{fire('principal');return {id:s.actor};},
    readAuthority:async()=>{fire('scope');return s.a;},openSnapshot:async()=>{fire('snapshot');return s.snap;},
    resolveKey:async(_ctx,user,receipt,request)=>{fire('key');if(s.keyDelay)await s.keyDelay();assert.equal(user.id,'owner');assert.equal(receipt.sessionId,'sess');assert.equal(request.operation,'decrypt');return key;}});
  return {...s,s,verify:r=>verify({},r)};
}
test('opens exact real AES envelope only within current scope and reduces to opaque plan/status',async()=>{
  const h=await home(),out=await h.verify(proposal());assert.equal(out.selectedPlanId,'good');
  assert.deepEqual(out.options,[{planId:'good',status:'met'},{planId:'bad',status:'failed'},{planId:'unsure',status:'unknown'}]);
  assert.equal(out.persisted,false);assert.ok(h.s.calls.filter(c=>c==='scope').length>=4);assert(!JSON.stringify(out).includes(I));
  assert.ok(!Object.hasOwn(out,'memberId'));const tag=out.previewTag;
  assert.equal((await h.verify(proposal('check-selection',{planId:'good',previewTag:tag}))).checkedPlanId,'good');
  await assert.rejects(h.verify(proposal('check-selection',{planId:'bad',previewTag:tag})));
  await assert.rejects(h.verify(proposal('check-selection',{planId:'good',previewTag:'f'.repeat(64)})));
});
test('no public/household/taste fallback, caller-supplied permissions or decrypted read on denial',async()=>{
  for(const d of [{choice:'withdrawn'},{memberId:'other'},{accountId:'other'},{purpose:'approved-public'}, {validFrom:1001},
    {expiresAt:T},{sessionExpiresAt:T},{sessionActive:false},{profileActive:false},{requestAuthorized:false},{consentRevision:0}]){
    const h=await home({tweak(s){Object.assign(s.a,d);}});await assert.rejects(h.verify(proposal()),/unavailable/);assert.ok(!h.s.calls.includes('snapshot'));}
  const h=await home();await assert.rejects(h.verify({...proposal(),authorized:true}));assert.deepEqual(h.s.calls,[]);
  await assert.rejects(createPrivateMenuPolicy()({},proposal()));
});
test('authority, body, session, evidence and key cannot change while evaluating',async()=>{
  for(const tweak of [
    s=>s.snap.variants[0].ingredients[I].state='present',s=>s.snap.plans[0].entries=[],s=>s.a.profileSha256='f'.repeat(64),
    s=>s.snap.envelope.keyRef='elsewhere',s=>s.a.envelopeId='other',s=>s.a.householdId='other',
    s=>s.phase=(p)=>{if(p==='key')s.a.choice='withdrawn';},s=>s.phase=p=>{if(p==='snapshot')s.actor='second';},
    s=>s.phase=p=>{if(p==='key')s.a.sessionGeneration='rotated';},s=>s.phase=p=>{if(p==='key')s.now=s.a.expiresAt;} ]){
    const h=await home({tweak});await assert.rejects(h.verify(proposal()),/^Error: Private menu verification unavailable\.$/);}
});
test('exact dimensions, quantities, yield, inclusive thresholds and completeness preserve unknown rather than invent compliance',async()=>{
  for(const [extra,alter,expected] of [
    [{},()=>{},'met'],[{magnitude:'0.3',unit:'g',inclusive:false},()=>{},'failed'],[{unit:'mL'},()=>{},'unknown'],
    [{},(_,ps,vs)=>{vs[0].yieldEvidence=null;},'unknown'],[{},(_,ps)=>{ps[0].entries[0].servings=null;},'unknown'],
    [{},(_,ps)=>{ps[0].completeDays=[];},'unknown'],[{magnitude:'299'},(_,ps)=>{ps[0].completeDays=[];},'failed'],
    [{period:'per-serving'},(_,ps)=>{ps[0].entries[0].servings='999';},'met'] ]){
    const h=await home({rules:[rule('nutrient-max',N,extra)],alter});assert.equal((await h.verify(proposal())).options[0].status,expected);}
});
test('quantified presence, incomplete window, contradictions, preference and stable tie breaking',async()=>{
  for(const [quantifier,expected] of [['any-item','met'],['every-item','failed']]){
    const h=await home({rules:[rule('require-attribute',A,{quantifier})],alter(_,ps){
      ps[0].entries.push({...ps[0].entries[0],entryId:'another',variantId:'y'});}});
    assert.equal((await h.verify(proposal())).options[0].status,expected);}
  for(const r of [rule('nutrient-min',N,{magnitude:'600'}),rule('require-ingredient',I)]){
    const h=await home({rules:[r],alter(_,ps){ps[0].completeDays=[];}});assert.equal((await h.verify(proposal())).options[0].status,'unknown');}
  const conflict=await home({rules:[rule('nutrient-max',N,{inclusive:false}),rule('nutrient-min',N,{ruleId:'m'})]});
  assert.equal((await conflict.verify(proposal())).selectedPlanId,null);
  const soft=await home({rules:[rule('require-attribute',A,{severity:'preference'})]});assert.equal((await soft.verify(proposal())).selectedPlanId,'good');
});
test('malformed/unauthenticated or mismatched imported private payload never passes even when content was pinned',async()=>{
  for(const alter of [(p)=>p.rules[0].clinical=true,(_p,ps)=>ps[0].entries[0].revision='obsolete',(_p,ps)=>ps[0].days=['2026-02-30'],
    (_p,ps)=>ps[0].entries[0].servings='-1',(_p,ps,vs)=>vs.push(vs[0]),(p)=>p.rules[0].quantifier='sometimes']){
    const h=await home({alter});await assert.rejects(h.verify(proposal()));}
});

test('actual encrypted synthetic source through private view preview and recheck; consent revision cannot be replayed',async()=>{
  const h=await home(),paints=[];let change;
  const ui=createPrivateMenuPreview({readContext:()=>({authenticated:true,consentActive:true,accountId:'owner',householdId:'hh',
    memberId:'member1',sessionGeneration:'s1',consentGeneration:String(h.s.a.consentRevision)}),watchContext:fn=>{change=fn;return ()=>{};},
    verify:h.verify,paint:x=>paints.push(x),clock:()=>h.s.now,schedule:()=>1,cancel:()=>{}});
  assert.equal((await ui.preview('plans')).selectedPlanId,'good');assert.deepEqual(await ui.checkSelection('good'),{state:'rechecked',planId:'good',persisted:false});
  h.s.a.consentRevision=3;change();assert.equal(paints.at(-1).state,'unavailable');
  assert.equal((await ui.checkSelection('good')).state,'unavailable');h.s.a.choice='withdrawn';
  assert.equal((await ui.preview('plans')).state,'unavailable');ui.dispose();
});

test('revocation while key resolution is pending prevents WebCrypto decrypt, not just the response',async(t)=>{
  const h=await home();let start,finish;const ready=new Promise(r=>start=r),resume=new Promise(r=>finish=r);
  // Interpose a real asynchronous gap at the existing runtime key boundary.
  const original=crypto.subtle.decrypt.bind(crypto.subtle),decrypt=t.mock.method(crypto.subtle,'decrypt',(...args)=>original(...args));
  h.s.keyDelay=async()=>{start();await resume;};
  const pending=h.verify(proposal());await ready;h.s.a.choice='withdrawn';finish();
  await assert.rejects(pending);assert.equal(decrypt.mock.callCount(),0);assert.equal(h.s.calls.at(-1),'release');
  assert.ok(!h.s.calls.includes('guard:before-evaluate'));
});
test('missing guard or a guard lost at any private boundary fails closed and releases once',async()=>{
  const absent=await home({tweak(s){s.noGuard=true;}});await assert.rejects(absent.verify(proposal()));assert.deepEqual(absent.s.calls,[]);
  for(const phase of ['before-private-read','after-private-read','before-key-read','before-decrypt','after-decrypt','before-evaluate','before-preview-release']){
    const h=await home({tweak(s){s.phase=p=>{if(p==='guard:'+phase)s.lost=true;};}});
    await assert.rejects(h.verify(proposal()));assert.equal(h.s.calls.filter(p=>p==='release').length,1);
    if(phase==='before-private-read')assert.ok(!h.s.calls.includes('snapshot'));
    if(phase==='after-decrypt')assert.ok(!h.s.calls.includes('guard:before-evaluate'));
  }
});
