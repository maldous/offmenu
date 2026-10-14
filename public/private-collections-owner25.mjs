// P2-03 standalone account-private consumer. No fetch, source import or sharing.
function capture(value) {
  let count=0;
  const active=new Set();
  function walk(v,depth=0) {
    if(++count>10000||depth>12)throw Error('Collection data exceeds bounds');
    if(v===null||typeof v==='boolean')return v;
    if(typeof v==='string'&&v.length<=10000)return v;
    if(typeof v==='number'&&Number.isFinite(v))return v;
    if(!v||typeof v!=='object'||active.has(v))throw Error('Plain JSON collection data required');
    const array=Array.isArray(v);
    if(Object.getPrototypeOf(v)!==(array?Array.prototype:Object.prototype))throw Error('Plain JSON collection data required');
    const descriptors=Object.getOwnPropertyDescriptors(v),keys=Reflect.ownKeys(descriptors);
    if(array&&(keys.length!==v.length+1||keys.some(k=>k!=='length'&&(typeof k!=='string'||! /^(0|[1-9][0-9]*)$/.test(k)||Number(k)>=v.length))))throw Error('Dense arrays required');
    const out=array?[]:{};active.add(v);
    for(const k of keys) {
      if(array&&k==='length')continue;
      const d=descriptors[k];
      if(typeof k!=='string'||!d.enumerable||!Object.hasOwn(d,'value'))throw Error('Data fields required');
      Object.defineProperty(out,k,{value:walk(d.value,depth+1),enumerable:true,writable:true,configurable:true});
    }
    active.delete(v);return out;
  }
  return walk(value);
}
function id(v) {if(typeof v!=='string'||!v.trim()||v.length>200)throw Error('Invalid collection identifier');return v;}
function revision(v) {if(!Number.isSafeInteger(v)||v<0||v>=Number.MAX_SAFE_INTEGER)throw Error('Invalid revision');return v;}
function ref(value) {
  const r=capture(value);
  for(const key of ['sourceId','recipeId','version','rightsVersion'])id(r[key]);
  const url=new URL(r.sourceUrl);if(url.protocol!=='https:'||url.username||url.password)throw Error('Invalid source URL');
  return r;
}
const identity=r=>JSON.stringify([r.sourceId,r.recipeId,r.version,r.rightsVersion]);
function envelope(value,accountId) {
  const state=capture(value);
  if(state.accountId!==accountId||state.version!==1||!Array.isArray(state.collections)||state.collections.length>100)throw Error('Invalid private collection envelope');
  revision(state.revision);const ids=new Set();
  for(const c of state.collections) {
    id(c.id);id(c.name);if(ids.has(c.id))throw Error('Duplicate collection ID');ids.add(c.id);
    if(!Array.isArray(c.bookmarks)||c.bookmarks.length>100)throw Error('Invalid bookmarks');
    const bids=new Set(),refs=new Set();
    for(const b of c.bookmarks) {
      id(b.id);ref(b.reference);
      if(bids.has(b.id)||refs.has(identity(b.reference)))throw Error('Duplicate bookmark');
      bids.add(b.id);refs.add(identity(b.reference));
      if(!['available','unavailable','withdrawn'].includes(b.status))throw Error('Invalid source status');
    }
  }
  return state;
}
export function createPrivateCollections({authorize,load,resolveRecipe,commit,clock}) {
  if([authorize,load,resolveRecipe,commit,clock].some(f=>typeof f!=='function'))throw Error('Authoritative collection dependencies required');
  async function authority(session,accountId,action) {
    const a=capture(await authorize(session,{accountId,action}));
    if(a.allowed!==true||a.accountId!==accountId||a.consent?.granted!==true||a.consent.purpose!=='private-recipe-collections')throw Error('Private collection access denied');
    for(const k of ['sessionId','realm','resource'])id(a[k]);
    if(!Number.isSafeInteger(a.epoch)||a.epoch<1)throw Error('Invalid authority epoch');
    id(a.consent.id);revision(a.consent.revision);return a;
  }
  const binding=a=>({accountId:a.accountId,sessionId:a.sessionId,realm:a.realm,epoch:a.epoch,resource:a.resource,consentId:a.consent.id,consentRevision:a.consent.revision});
  async function recheck(session,a,action) {
    const current=await authority(session,a.accountId,action);
    if(JSON.stringify(binding(current))!==JSON.stringify(binding(a)))throw Error('Collection authority changed');
  }
  async function resolve(reference,a) {
    const r=capture(await resolveRecipe(capture(reference),capture(binding(a))));
    if(!['available','unavailable','withdrawn'].includes(r.status)||identity(ref(r.reference))!==identity(reference)||r.reference.sourceUrl!==reference.sourceUrl)throw Error('Recipe identity unresolved');
    const result={reference:capture(reference),status:r.status,provenance:r.provenance??null};
    if(r.status==='available'&&r.privateCopyAllowed===true&&r.privateCopy) {
      const copy=r.privateCopy;
      if(copy.accountId!==a.accountId||copy.review?.status!=='personally-reviewed'||copy.review.sourceRecipeId!==reference.recipeId||copy.review.sourceVersion!==reference.version)throw Error('Private reviewed copy mismatch');
      id(copy.review.id);result.privateCopy=capture(copy);
    }
    return result;
  }
  return {
    async read({session,accountId}) {
      session=capture(session);id(accountId);const a=await authority(session,accountId,'read'),state=envelope(await load(binding(a)),accountId);
      for(const c of state.collections)for(const b of c.bookmarks) {
        const current=await resolve(b.reference,a);
        // Re-resolve visibility; never return retained private content after withdrawal.
        Object.assign(b,current);delete b.privateCopy;if(current.privateCopy)b.privateCopy=current.privateCopy;
      }
      await recheck(session,a,'read');return capture(state);
    },
    async mutate({session,accountId,command}) {
      session=capture(session);id(accountId);const cmd=capture(command);id(cmd.operationId);revision(cmd.expectedVersion);
      const a=await authority(session,accountId,'write'),state=envelope(await load(binding(a)),accountId);
      if(state.revision!==cmd.expectedVersion)return {status:'conflict',operationId:cmd.operationId,revision:state.revision};
      const c=state.collections.find(c=>c.id===cmd.collectionId);
      switch(cmd.type) {
        case 'add':
          id(cmd.collectionId);id(cmd.name);if(c||state.collections.length>=100)throw Error('Duplicate or full collection');
          state.collections.push({id:cmd.collectionId,name:cmd.name,bookmarks:[]});break;
        case 'rename':if(!c)throw Error('Collection unavailable');id(cmd.name);c.name=cmd.name;break;
        case 'remove':if(!c)throw Error('Collection unavailable');state.collections=state.collections.filter(x=>x.id!==c.id);break;
        case 'bookmark': {
          if(!c)throw Error('Collection unavailable');id(cmd.bookmarkId);const reference=ref(cmd.reference);
          if(c.bookmarks.length>=100||c.bookmarks.some(b=>b.id===cmd.bookmarkId||identity(b.reference)===identity(reference)))throw Error('Duplicate or full bookmark');
          c.bookmarks.push({id:cmd.bookmarkId,...await resolve(reference,a)});break;
        }
        case 'unbookmark':if(!c||!c.bookmarks.some(b=>b.id===cmd.bookmarkId))throw Error('Bookmark unavailable');c.bookmarks=c.bookmarks.filter(b=>b.id!==cmd.bookmarkId);break;
        case 'reset':state.collections=[];break;
        default:throw Error('Unknown collection operation');
      }
      const at=clock();if(typeof at!=='string'||!Number.isFinite(Date.parse(at)))throw Error('Invalid clock');state.updatedAt=at;
      await recheck(session,a,'write');
      // Owner adapter must atomically re-admit this exact binding/consent/source
      // policy and expectedVersion with mutation + operation ledger. Unknown stays unknown.
      let result;
      try {result=capture(await commit({binding:binding(a),operationId:cmd.operationId,expectedVersion:cmd.expectedVersion,state:capture(state)}));}
      catch {return {status:'unknown',operationId:cmd.operationId};}
      try {await recheck(session,a,'write');} catch {return {status:'unknown',operationId:cmd.operationId};}
      if(result.status!=='committed'||result.acknowledged!==true||result.operationId!==cmd.operationId||result.revision!==cmd.expectedVersion+1||JSON.stringify(result.binding)!==JSON.stringify(binding(a)))return {status:'unknown',operationId:cmd.operationId};
      return result;
    }
  };
}
