// Unmounted view coordinator for an authenticated kitchen. No storage, URL,
// provider, public search, telemetry or write. Consent/membership changes must
// notify watchContext synchronously; checking a previous preview is never a save.
const atom=x=>typeof x==='string'&&x.trim()&&x.length<=512;
const validDig=x=>typeof x==='string'&&/^[0-9a-f]{64}$/u.test(x);
const status=new Set(['met','failed','unknown','conflicting']);
const unavailable=()=>({state:'unavailable',persisted:false});
export function createPrivateMenuPreview({readContext,watchContext,verify,paint,clock,
  schedule=(f,ms)=>setTimeout(f,ms),cancel=t=>clearTimeout(t)}={}) {
  if(![readContext,watchContext,verify,paint,clock,schedule,cancel].every(x=>typeof x==='function'))throw Error('Private menu view unavailable.');
  let generation=0,current=null,timer=null,closed=false;
  const audience=()=>{const a=readContext();
    if(a?.authenticated!==true||a.consentActive!==true||![a.accountId,a.householdId,a.memberId,a.sessionGeneration,a.consentGeneration].every(atom))return null;
    return JSON.stringify([a.accountId,a.householdId,a.memberId,a.sessionGeneration,a.consentGeneration]);};
  function clear(){generation++;current=null;if(timer!==null)cancel(timer);timer=null;paint(unavailable());}
  const stop=watchContext(clear);if(typeof stop!=='function'){clear();throw Error('Private menu observations unavailable.');}
  clear();
  function now(){const t=clock();if(!Number.isSafeInteger(t)||t<0)throw Error('Clock unavailable');return t;}
  function still(g,a){return !closed&&generation===g&&a!==null&&audience()===a;}
  function checked(result,selection){
    if(!result||result.schema!=='offmenu-private-menu-preview/1'||!validDig(result.previewTag)||!Number.isSafeInteger(result.validUntil)||result.validUntil<=now()
      ||result.persisted!==false||!Array.isArray(result.options)||result.options.length<1||result.options.length>100)return null;
    const opts=[];const ids=new Set();
    for(const o of result.options){if(!atom(o?.planId)||!status.has(o.status)||ids.has(o.planId))return null;
      ids.add(o.planId);opts.push({planId:o.planId,status:o.status});}
    const eligible=id=>opts.some(o=>o.planId===id&&o.status==='met');
    if((result.selectedPlanId!==null&&!eligible(result.selectedPlanId))||
        result.checkedPlanId!==selection||(selection!==null&&!eligible(selection)))return null;
    return {tag:result.previewTag,until:result.validUntil,selectedPlanId:result.selectedPlanId,options:opts};
  }
  function expire(g,a){if(generation!==g||closed)return;
    try{if(!still(g,a)||current.until<=now()){clear();return;}
      timer=schedule(()=>expire(g,a),Math.min(2147483647,current.until-now()));}catch{clear();}}
  async function preview(candidateSetId){
    if(closed)return unavailable();clear();const g=generation;
    try{const a=audience();if(!a||!atom(candidateSetId))throw Error();
      const memberId=JSON.parse(a)[2],d=checked(await verify({operation:'preview',memberId,candidateSetId}),null);
      if(!still(g,a)){if(!closed&&generation===g)clear();return unavailable();}if(!d)throw Error();
      current={...d,candidateSetId,a};expire(g,a);if(!still(g,a)||!current)return unavailable();
      const view={state:'preview',selectedPlanId:d.selectedPlanId,options:structuredClone(d.options),persisted:false};
      paint(structuredClone(view));return view;
    }catch{if(!closed&&generation===g)clear();return unavailable();}
  }
  async function checkSelection(planId){
    const g=generation,c=current;
    try{if(closed||!c||!still(g,c.a)||c.until<=now()||!c.options.some(o=>o.planId===planId&&o.status==='met'))throw Error();
      const memberId=JSON.parse(c.a)[2],d=checked(await verify({operation:'check-selection',memberId,candidateSetId:c.candidateSetId,planId,previewTag:c.tag}),planId);
      if(!still(g,c.a)){if(!closed&&generation===g)clear();return unavailable();}if(!d||d.tag!==c.tag||c.until<=now())throw Error();
      // An actual writer must compare a freshly validated fence atomically.
      return {state:'rechecked',planId,persisted:false};
    }catch{if(!closed&&generation===g)clear();return unavailable();}
  }
  function dispose(){if(closed)return;closed=true;try{stop();}finally{clear();}}
  return Object.freeze({preview,checkSelection,dispose});
}
