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
  return response;
 };
}
