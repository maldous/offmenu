// Landing-page handoff only. The existing SDK on /auth.html processes callbacks.
// Never log, persist, exchange or forward a callback to another origin.
export function routeIdentityReturn(location=globalThis.location){
  if(!location)return false;
  const url=new URL(location.href);
  if(url.pathname==='/auth.html'||!url.hash)return false;
  const parameters=new URLSearchParams(url.hash.slice(1));
  if(!['access_token','confirmation_token','recovery_token','email_change_token'].some(key=>parameters.has(key)))return false;
  location.replace('/auth.html'+url.hash);return true;
}
if(typeof window!=='undefined')routeIdentityReturn();
