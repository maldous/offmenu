// Owner-only, unmounted. The application provides verified identity, an atomic
// authority snapshot, encrypted policy custody and immutable food/plan witnesses.
// No unsolicited network, telemetry, plaintext storage or fallback policy.
import {createEnvelopeCryptor} from './byoc-envelope-v1.mjs';
const deny=()=>{throw new Error('Private menu verification unavailable.');};
const ensure=v=>{if(!v)deny();};
const obj=v=>v!==null&&typeof v==='object'&&!Array.isArray(v)&&[Object.prototype,null].includes(Object.getPrototypeOf(v));
const atom=v=>typeof v==='string'&&v.trim().length>0&&v.length<=512&&!/[\p{Cc}\p{Cs}]/u.test(v);
const id=v=>atom(v)&&/^(urn:[A-Za-z0-9][A-Za-z0-9-]*:|https:\/\/)\S+$/u.test(v);
const dig=v=>typeof v==='string'&&/^[0-9a-f]{64}$/u.test(v);
const pos=v=>Number.isSafeInteger(v)&&v>0;
const day=v=>typeof v==='string'&&/^\d{4}-\d{2}-\d{2}$/u.test(v)&&v.slice(0,4)!=='0000'&&!Number.isNaN(Date.parse(v+'T12:00Z'))&&new Date(v+'T12:00Z').toISOString().slice(0,10)===v;
function keys(v,names){ensure(obj(v)&&Object.keys(v).length===names.length&&names.every(k=>Object.hasOwn(v,k)));}
function list(v,min,max){ensure(Array.isArray(v)&&v.length>=min&&v.length<=max);return v;}
function uniq(v){ensure(new Set(v).size===v.length);}
const codepoint=(a,b)=>{const x=[...a],y=[...b];for(let i=0;i<Math.min(x.length,y.length);i++){const n=x[i].codePointAt(0)-y[i].codePointAt(0);if(n)return n;}return x.length-y.length;};
// Canonical JSON matching the accepted profile fingerprint for this bounded wire
// domain (strings/booleans/null and safe integers). Reject rather than coerce.
function wire(value,cap=200000) {
  let n=0,chars=0;
  const visit=(v,depth)=>{
    ensure(++n<=cap&&depth<=20);
    if(v===null||typeof v==='boolean'||Number.isSafeInteger(v))return JSON.stringify(v);
    if(typeof v==='string'){ensure(!/\p{Cs}/u.test(v)&&(chars+=v.length)<=2_000_000);return JSON.stringify(v);}
    ensure(v&&typeof v==='object');const a=Array.isArray(v);
    ensure(a?Object.getPrototypeOf(v)===Array.prototype:obj(v));const ds=Object.getOwnPropertyDescriptors(v),ks=Reflect.ownKeys(ds);
    ensure(ks.length<=10001&&ks.every(k=>typeof k==='string'&&!['__proto__','constructor','prototype'].includes(k)));
    if(a){ensure(v.length<=10000&&ks.length===v.length+1);return '['+Array.from({length:v.length},(_,i)=>{
      const d=ds[i];ensure(d?.enumerable&&Object.hasOwn(d,'value'));return visit(d.value,depth+1);}).join(',')+']';}
    return '{'+ks.sort(codepoint).map(k=>{const d=ds[k];ensure(d.enumerable&&Object.hasOwn(d,'value'));return visit(k,depth+1)+':'+visit(d.value,depth+1);}).join(',')+'}';
  };return visit(value,0);
}
async function hash(v){const bytes=new TextEncoder().encode(wire(v));return [...new Uint8Array(await crypto.subtle.digest('SHA-256',bytes))].map(b=>b.toString(16).padStart(2,'0')).join('');}
const capture=v=>JSON.parse(wire(v));
const privateV='offmenu-private-dietary-planning-profile/1',purpose='private-menu-plan';
const scopes=['accountId','householdId','memberId','consentId','profileRevision','zone'];
const us={ug:['mass','0.000001'],mg:['mass','0.001'],g:['mass','1'],kg:['mass','1000'],'[oz_av]':['mass','28.349523125'],'[lb_av]':['mass','453.59237'],
  mL:['volume','1'],L:['volume','1000'],'[foz_us]':['volume','29.5735295625'],'[foz_br]':['volume','28.4130625'],
  J:['energy','1'],kJ:['energy','1000'],kcal_th:['energy','4184'],'1':['count','1']};
const units=u=>typeof u==='string'&&Object.hasOwn(us,u);
function rat(x,y){ensure(y>0n);let a=x,b=y;while(b){[a,b]=[b,a%b];}return [x/a,y/a];}
function amount(v){ensure(typeof v==='string'&&v.length<=48&&/^(0|[1-9][0-9]*)(\.[0-9]+)?$/u.test(v));const [w,f='']=v.split('.');return rat(BigInt(w+f),10n**BigInt(f.length));}
const mul=(a,b)=>rat(a[0]*b[0],a[1]*b[1]),div=(a,b)=>rat(a[0]*b[1],a[1]*b[0]),add=(a,b)=>rat(a[0]*b[1]+b[0]*a[1],a[1]*b[1]),cmp=(a,b)=>a[0]*b[1]-b[0]*a[1];
const conv=(a,s,d)=>us[s][0]!==us[d][0]?null:div(mul(a,amount(us[s][1])),amount(us[d][1]));
const req=['require-ingredient','require-attribute'],exc=['exclude-ingredient','exclude-attribute'],nut=['nutrient-min','nutrient-max'];
function rules(p,a){
  keys(p,['profileVersion',...scopes,'purpose','rules']);ensure(p.profileVersion===privateV&&p.purpose===purpose&&scopes.every(k=>p[k]===a[k]));
  try{new Intl.DateTimeFormat('en',{timeZone:p.zone});}catch{deny();}
  list(p.rules,0,128);uniq(p.rules.map(r=>r.ruleId));
  for(const r of p.rules){
    const base=['ruleId','kind','targetId','period','severity','from','through'];
    ensure(obj(r)&&atom(r.ruleId)&&id(r.targetId)&&['per-serving','per-meal','per-day'].includes(r.period)&&['hard','preference'].includes(r.severity)&&day(r.from)&&day(r.through)&&r.from<=r.through);
    if(nut.includes(r.kind)){keys(r,[...base,'inclusive','magnitude','unit']);ensure(typeof r.inclusive==='boolean'&&units(r.unit));amount(r.magnitude);}
    else{keys(r,[...base,'quantifier']);ensure((req.includes(r.kind)&&['any-item','every-item'].includes(r.quantifier))||(exc.includes(r.kind)&&r.quantifier==='every-item'));}
  }
}
function validVariant(v){
  keys(v,['variantId','revision','evidence','ingredients','attributes','nutrients','yieldServings','yieldEvidence']);
  ensure(atom(v.variantId)&&atom(v.revision)&&dig(v.evidence)&&(v.yieldEvidence===null||dig(v.yieldEvidence)));
  if(v.yieldServings!==null)amount(v.yieldServings);
  for(const type of ['ingredients','attributes','nutrients']){
    const dict=v[type];ensure(obj(dict)&&Object.keys(dict).length<=1024);
    for(const [target,f] of Object.entries(dict)){ensure(id(target)&&dig(f.evidence));
      if(type==='nutrients'){keys(f,['magnitude','unit','basis','evidence']);amount(f.magnitude);ensure(units(f.unit)&&['per-recipe','per-serving'].includes(f.basis));}
      else {keys(f,['state','evidence']);ensure(['present','absent','unknown','conflicting'].includes(f.state));}
    }
  }
}
function conflict(a,b){
  if(a.severity!=='hard'||b.severity!=='hard'||a.targetId!==b.targetId||a.period!==b.period)return false;
  if(req.includes(a.kind)&&a.kind.replace('require','exclude')===b.kind||req.includes(b.kind)&&b.kind.replace('require','exclude')===a.kind)return true;
  if(!nut.includes(a.kind)||!nut.includes(b.kind)||a.kind===b.kind)return false;
  const [min,max]=a.kind==='nutrient-min'?[a,b]:[b,a],x=conv(amount(max.magnitude),max.unit,min.unit);
  return x===null||cmp(amount(min.magnitude),x)>0n||(cmp(amount(min.magnitude),x)===0n&&!(min.inclusive&&max.inclusive));
}
function observe(r,rows,complete){
  if(!rows.length)return 'unknown';
  if(!nut.includes(r.kind)){
    const field=r.kind.endsWith('ingredient')?'ingredients':'attributes',flags=rows.map(([,v])=>v[field][r.targetId]?.state??'unknown');
    if(flags.includes('conflicting'))return 'conflicting';
    const whole=complete&&!flags.includes('unknown');
    if(exc.includes(r.kind))return flags.includes('present')?'failed':whole?'met':'unknown';
    if(r.quantifier==='every-item')return flags.includes('absent')?'failed':whole?'met':'unknown';
    return flags.includes('present')?'met':whole?'failed':'unknown';
  }
  let total=[0n,1n],unknown=!complete;
  for(const [entry,v] of rows){const f=v.nutrients[r.targetId];if(!f){unknown=true;continue;}
    let n=conv(amount(f.magnitude),f.unit,r.unit);if(!n){unknown=true;continue;}
    if(f.basis==='per-recipe'){if(!v.yieldEvidence||v.yieldServings===null||amount(v.yieldServings)[0]===0n){unknown=true;continue;}n=div(n,amount(v.yieldServings));}
    if(r.period!=='per-serving'){if(entry.servings===null){unknown=true;continue;}n=mul(n,amount(entry.servings));}
    total=add(total,n);
  }
  const diff=cmp(total,amount(r.magnitude)),min=r.kind==='nutrient-min',ok=min?(r.inclusive?diff>=0n:diff>0n):(r.inclusive?diff<=0n:diff<0n);
  return unknown&&(ok||min)?'unknown':ok?'met':'failed';
}
function choose(profile,plans,variants){
  const byKey=new Map(),results=[];list(variants,0,1024);for(const v of variants){validVariant(v);const k=JSON.stringify([v.variantId,v.revision]);ensure(!byKey.has(k));byKey.set(k,v);}
  list(plans,1,100);uniq(plans.map(p=>p.planId));let window;
  let work=0; // All candidates combined, independent of per-object limits.
  for(const p of plans){
    keys(p,['planId','zone','days','completeDays','entries']);ensure(atom(p.planId)&&p.zone===profile.zone);
    list(p.days,1,31);list(p.completeDays,0,31);uniq(p.days);uniq(p.completeDays);ensure(p.days.every(day)&&p.completeDays.every(d=>p.days.includes(d)));
    const w=JSON.stringify([...p.days].sort());ensure(window===undefined||window===w);window=w;
    list(p.entries,0,256);uniq(p.entries.map(e=>e.entryId));const days=new Map(p.days.map(d=>[d,[]]));
    for(const e of p.entries){keys(e,['entryId','day','mealId','variantId','revision','servings']);
      ensure([e.entryId,e.mealId,e.variantId,e.revision].every(atom)&&days.has(e.day)&&(e.servings===null||amount(e.servings)[0]>0n));
      const v=byKey.get(JSON.stringify([e.variantId,e.revision]));ensure(v);days.get(e.day).push([e,v]);}
    const statuses=new Set();let preferencesMet=0,complete=true;
    for(const [d,items] of days){
      const closed=p.completeDays.includes(d);complete&&=closed&&items.length>0;
      const applicable=profile.rules.filter(r=>r.from<=d&&d<=r.through);
      ensure((work+=applicable.length*(1+items.length+applicable.length))<=1_000_000);
      for(const r of applicable){const groups=new Map();for(const pair of items){
        const key=r.period==='per-serving'?pair[0].entryId:r.period==='per-meal'?pair[0].mealId:d;
        if(!groups.has(key))groups.set(key,[]);groups.get(key).push(pair);}
        const states=applicable.some(s=>r!==s&&conflict(r,s))?['conflicting']:[...(groups.size?groups.values():[[]])].map(g=>observe(r,g,closed||r.period==='per-serving'));
        if(r.severity==='hard')for(const s of states)statuses.add(s);else if(states.every(s=>s==='met'))preferencesMet++;
      }
    }
    const status=['conflicting','failed','unknown'].find(s=>statuses.has(s))??(complete?'met':'unknown');
    results.push({planId:p.planId,status,preferencesMet});
  }
  const selectedPlanId=results.filter(r=>r.status==='met').sort((a,b)=>b.preferencesMet-a.preferencesMet||codepoint(a.planId,b.planId))[0]?.planId??null;
  // No rules, condition names, evidence IDs, origin records or member IDs sent to UI.
  return {selectedPlanId,options:results.map(({planId,status})=>({planId,status}))};
}
const AUTH=[...scopes,'purpose','sessionId','sessionGeneration','consentRevision','choice','validFrom','expiresAt',
  'sessionExpiresAt','sessionActive','profileActive','candidateSetId','profileSha256','plansSha256','variantsSha256',
  'envelopeId','keyRef','keyVersion','requestAuthorized'];
function validateAuth(a,req,user,now){
  keys(a,AUTH);ensure(a.accountId===user.id&&a.memberId===req.memberId&&a.candidateSetId===req.candidateSetId
    &&scopes.every(k=>atom(a[k]))&&a.purpose===purpose&&a.choice==='granted'&&a.requestAuthorized===true&&a.profileActive===true&&a.sessionActive===true
    &&[a.sessionId,a.sessionGeneration,a.keyRef,a.envelopeId].every(atom)&&[a.keyVersion,a.consentRevision].every(pos)
    &&[a.validFrom,a.expiresAt,a.sessionExpiresAt,now].every(Number.isSafeInteger)&&a.validFrom<=now&&now<Math.min(a.expiresAt,a.sessionExpiresAt)
    &&[a.profileSha256,a.plansSha256,a.variantsSha256].every(dig));
}
/** Trusted ports only. actual actor/authority may NEVER come from request JSON.
 * readAuthority must attest active owner-only member, local calendar membership,
 * operation-scoped consent/grant/session revision, approved facts and key binding.
 * acquireOperationGuard is mandatory independent runtime custody: it must hold
 * the same authoritative snapshot, serialize revocation against protected use
 * or synchronously invalidate/drain it, and release on every exit. assertCurrent
 * must synchronously attest the held guard at the supplied phase. A polling
 * boolean, profile statement or stale request-scoped cache is NOT a guard.
 * Guarded selection is intentionally not a write: the actual writer must repeat
 * the entire decision AND compare its expected private fence in its own transaction.
 */
export function createPrivateMenuPolicy({verifiedUser,readAuthority,acquireOperationGuard,openSnapshot,resolveKey,clock}={}) {
  return async function verify(context,input) {
    try{
      ensure([verifiedUser,readAuthority,acquireOperationGuard,openSnapshot,resolveKey,clock].every(x=>typeof x==='function'));
      const r=capture(input);ensure(['preview','check-selection'].includes(r.operation));
      const selection=r.operation==='check-selection';keys(r,selection?['operation','memberId','candidateSetId','planId','previewTag']:['operation','memberId','candidateSetId']);
      ensure(atom(r.memberId)&&atom(r.candidateSetId)&&(!selection||(atom(r.planId)&&dig(r.previewTag))));
      const initial=await verifiedUser(context);ensure(atom(initial?.id));const user=Object.freeze({id:initial.id});
      let fence;
      const recheck=async()=>{ensure(!context?.signal?.aborted);const current=await verifiedUser(context);ensure(current?.id===user.id);
        const a=capture(await readAuthority(context,user,{memberId:r.memberId,candidateSetId:r.candidateSetId,purpose,operation:r.operation}));
        validateAuth(a,r,user,clock());const stamp=wire(a);ensure(fence===undefined||fence===stamp);fence=stamp;return a;};
      const a=await recheck(),tag=await hash(a);if(selection)ensure(r.previewTag===tag);
      await recheck();
      const guard=await acquireOperationGuard(context,user,{authority:capture(a),operation:r.operation,previewTag:tag});
      ensure(typeof guard?.release==='function');
      try{
        const held=phase=>{ensure(typeof guard.assertCurrent==='function' && guard.assertCurrent(phase)===true && !context?.signal?.aborted);
          validateAuth(a,r,user,clock());};
        const boundary=async phase=>{held(phase);await recheck();held(phase);};
        await boundary('before-private-read');
        const raw=await openSnapshot(context,user,capture(a),guard);
        await boundary('after-private-read');
        const snap=capture(raw);keys(snap,['envelope','plans','variants']);
        ensure(snap.envelope.keyRef===a.keyRef&&snap.envelope.keyVersion===a.keyVersion&&snap.envelope.custody==='server-envelope');
        const cryptor=createEnvelopeCryptor({resolveKey:async key=>{
          await boundary('before-key-read');const resolved=await resolveKey(context,user,capture(a),key,guard);
          // The key promise may span revocation or session expiry. Do not release
          // the resolved key into WebCrypto until that *post-read* check passes.
          await boundary('before-decrypt');return resolved;
        }});
        await boundary('before-envelope-open');
        const p=await cryptor.open(snap.envelope,{ownerUserId:user.id,kitchenId:a.householdId,objectType:'household_profile',objectId:a.envelopeId,purpose,providerId:null});
        await boundary('after-decrypt');
        ensure(await hash(p)===a.profileSha256);
        await boundary('before-plan-verify');ensure(await hash(snap.plans)===a.plansSha256);
        await boundary('before-fact-verify');ensure(await hash(snap.variants)===a.variantsSha256);
        await boundary('before-evaluate');rules(p,a);const decision=choose(p,snap.plans,snap.variants);
        if(selection)ensure(decision.options.some(o=>o.planId===r.planId&&o.status==='met'));
        await boundary('before-preview-release');
        return {schema:'offmenu-private-menu-preview/1',previewTag:tag,validUntil:Math.min(a.expiresAt,a.sessionExpiresAt),
          selectedPlanId:decision.selectedPlanId,options:decision.options,checkedPlanId:selection?r.planId:null,persisted:false};
      }finally{ensure(guard.release()===undefined);}
    }catch{deny();}
  };
}
