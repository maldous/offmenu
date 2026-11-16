// A shared-kitchen response may only affect the account and kitchen that asked
// for it. This is a client lifecycle guard, not server authorization.
export function captureKitchenScope(getScope,{selection=true}={}) {
 const started=getScope();
 return ()=>{
  const current=getScope();
  if(current.owner!==started.owner||current.key!==started.key||
    current.demo!==started.demo||current.generation!==started.generation||
    selection&&current.selected!==started.selected) {
   throw Object.assign(Error('Account or kitchen changed. Retry from your current kitchen.'),{code:'KITCHEN_SCOPE_CHANGED'});
  }
 };
}

export function createScopedKitchenRequest({getScope,refreshSession,request=globalThis.fetch}) {
 return async(path,options)=>{
  const check=captureKitchenScope(getScope);
  await refreshSession();
  check(); // Never send a queued write using a different account's session.
  const response=await request(path,options);
  check();
  const value=await response.json();
  check(); // Headers arriving first must not permit a stale body to be applied.
  return {response,value};
 };
}
