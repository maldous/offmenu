// Classify only. Tokens stay in the browser fragment for the existing SDK.
// No token value is returned, persisted, logged or exchanged by this module.
export function classifyIdentityCallback(hash='') {
  if(typeof hash!=='string'||hash.length>16384)return {kind:'invalid'};
  if(!hash||hash==='#')return {kind:'none'};
  const parameters=new URLSearchParams(hash.replace(/^#/,''));
  const kinds={access_token:'oauth',confirmation_token:'confirmation',recovery_token:'recovery',
    invite_token:'invite',email_change_token:'email_change'};
  const found=Object.keys(kinds).filter(key=>parameters.has(key));
  if(!found.length)return {kind:[...parameters.keys()].some(key=>/token|^error/.test(key))?'invalid':'none'};
  if(found.length!==1)return {kind:'invalid'};
  const key=found[0];
  if(parameters.getAll(key).length!==1||!parameters.get(key)||parameters.get(key).length>8192)return {kind:'invalid'};
  const allowed=key==='access_token'?['access_token','refresh_token','token_type','expires_in','expires_at','state']: [key];
  if([...parameters.keys()].some(name=>!allowed.includes(name)||parameters.getAll(name).length!==1))return {kind:'invalid'};
  return {kind:kinds[key]};
}
