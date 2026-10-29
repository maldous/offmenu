// Local proposal boundary only. No navigation, sharing, purchasing or transport.
function plain(value, depth=0, budget={nodes:0}) {
  if(++budget.nodes>10000||depth>20)throw Error('Input exceeds bounds');
  if(value===null||typeof value==='boolean'||typeof value==='string')return value;
  if(typeof value==='number'&&Number.isFinite(value))return value;
  if(!value||typeof value!=='object')throw Error('Plain JSON required');
  const array=Array.isArray(value);
  if(Object.getPrototypeOf(value)!==(array?Array.prototype:Object.prototype))throw Error('Plain JSON required');
  const out=array?[]:{};
  for(const key of Reflect.ownKeys(value)) {
    if(array&&key==='length')continue;
    const d=Object.getOwnPropertyDescriptor(value,key);
    if(typeof key!=='string'||!d.enumerable||!Object.hasOwn(d,'value')||['__proto__','constructor','toJSON'].includes(key))throw Error('Plain JSON required');
    if(array&&!/^(0|[1-9]\d*)$/.test(key))throw Error('Dense array required');
    out[key]=plain(d.value,depth+1,budget);
  }
  if(array&&Object.keys(out).length!==value.length)throw Error('Dense array required');
  if(depth===0&&JSON.stringify(out).length>65536)throw Error('Input exceeds bounds');
  return out;
}
function keys(value,expected) {
  if(!value||Array.isArray(value)||typeof value!=='object'||Object.keys(value).sort().join('|')!==[...expected].sort().join('|'))throw Error('Unsupported fields; credentials and URLs must not come from a request');
}
const text=v=>typeof v==='string'&&v.trim().length>0&&v.length<=256;
const id=v=>typeof v==='string'&&/^[a-z][a-z0-9-]{0,63}$/.test(v);
function approvedURL(value) {
  if(typeof value!=='string'||value.length>2048||/[\s\\\u0000-\u001f\u007f]/.test(value))throw Error('Invalid approved URL');
  const url=new URL(value);
  if(url.protocol!=='https:'||url.username||url.password||value.includes('?')||value.includes('#')||url.port||url.href!==value)throw Error('Approved URL must be canonical HTTPS without credentials, query, fragment or custom port');
  return value;
}

// These injected producers must be independently qualified by their owners.
// A local allowlist entry is not source rights, authentication or user consent.
export function createShoppingDestinationBoundary({handoff,readPolicy=()=>({version:'unconfigured',destinations:[]}),readContext=()=>null,now=()=>NaN}={}) {
  const pending=new WeakMap();
  function read(destinationId) {
    const policy=plain(readPolicy()),context=plain(readContext()),clock=now();
    keys(policy,['version','destinations']);
    if(!text(policy.version)||!Array.isArray(policy.destinations)||policy.destinations.length>50)throw Error('Invalid destination policy');
    if(!id(destinationId))throw Error('Unapproved destination ID');
    if(!Number.isFinite(clock))throw Error('Injected clock required');
    const seen=new Set();let selected;
    for(const entry of policy.destinations) {
      keys(entry,['id','url','markets','enabled','expiresAt']);
      if(!id(entry.id)||seen.has(entry.id)||typeof entry.enabled!=='boolean'||!Number.isFinite(entry.expiresAt)||!Array.isArray(entry.markets)||!entry.markets.length||entry.markets.some(m=>typeof m!=='string'||! /^[A-Z]{2}$/.test(m)))throw Error('Invalid destination policy entry');
      seen.add(entry.id);approvedURL(entry.url);
      if(entry.id===destinationId)selected=entry;
    }
    if(!selected||selected.enabled!==true||selected.expiresAt<=clock)throw Error('Destination blocked or expired');
    keys(context,['accountId','kitchenId','revision','sessionEpoch','market','canExport','demo']);
    if(!['accountId','kitchenId','revision','sessionEpoch'].every(k=>text(context[k]))||context.canExport!==true||context.demo!==false||!selected.markets.includes(context.market))throw Error('Destination not approved for current scope/market');
    return {policy,context,destination:{id:selected.id,url:selected.url,market:context.market,policyVersion:policy.version}};
  }
  function checkScope(proposal,context,destinationId,status) {
    const d=proposal?.draft;
    if(proposal?.status!==status||d?.kind!=='retailer'||d.scope!==JSON.stringify([context.accountId,context.kitchenId])||d.revision!==context.revision||d.detail?.sessionEpoch!==context.sessionEpoch||d.detail.destinationId!==destinationId)throw Error('Handoff does not match current destination/scope');
  }
  return {
    preview(request) {
      const req=plain(request);keys(req,['id','kind','destinationId']);
      if(!text(req.id)||req.kind!=='retailer')throw Error('Retailer proposal required');
      const state=read(req.destinationId);
      if(typeof handoff?.preview!=='function'||typeof handoff?.confirm!=='function')throw Error('Qualified handoff controller required');
      const raw=handoff.preview(req),proposal=plain(raw);
      checkScope(proposal,state.context,req.destinationId,'proposed');
      const view={status:'destination-preview',destination:plain(state.destination),handoff:proposal};
      pending.set(view,{request:req,state,snapshot:JSON.stringify(view),raw});return view;
    },
    confirm(view,{confirmed=false}={}) {
      const old=pending.get(view);
      if(!old||confirmed!==true)throw Error('Explicit confirmation of this destination preview required');
      if(JSON.stringify(plain(view))!==old.snapshot)throw Error('Destination preview changed');
      const fresh=read(old.request.destinationId);
      if(JSON.stringify(fresh)!==JSON.stringify(old.state))throw Error('Destination policy or scope changed; review again');
      // Existing controller rechecks current quantities, provenance and source rights.
      const proposal=plain(handoff.confirm(old.raw,{confirmed:true}));
      checkScope(proposal,fresh.context,old.request.destinationId,'confirmed-proposal');
      pending.delete(view);
      return {status:'destination-approved-proposal',destination:plain(fresh.destination),handoff:proposal};
    },
  };
}
