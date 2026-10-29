// Bind a request to the account that initiated it, across asynchronous refreshes.
export function sessionFetch({identity,refresh,currentUser,request=fetch,changed=()=>Error('Account changed. Retry from your current account.')}) {
 return async (path,options)=>{
  const started=identity();
  const check=()=>{if(identity()!==started)throw changed();};
  if(started.owner)await refresh();
  check();
  const actual=await currentUser();
  check();
  if((actual?.id||null)!==started.owner)throw changed();
  const response=await request(path,options);
  check();
  // A body may arrive after headers. Reject it if another account took over.
  const guarded=response=>new Proxy(response,{get(target,key){
   const value=Reflect.get(target,key,target);
   if(key==='clone')return ()=>{check();return guarded(target.clone());};
   if(['json','text','blob','arrayBuffer','formData','bytes'].includes(key)&&typeof value==='function')return async(...args)=>{check();const body=await value.apply(target,args);check();return body;};
   return typeof value==='function'?value.bind(target):value;
  }});
  return guarded(response);
 };
}
