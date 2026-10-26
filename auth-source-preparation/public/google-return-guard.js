export const GOOGLE_APP_ORIGIN='https://offmenu.aldous.info';
export const GOOGLE_RETURN_PATH='/auth.html';
export const GOOGLE_CONSUME_PATH='/api/auth-page/google-return';
export const GOOGLE_NONCE=/^[a-f0-9]{64}$/;
export async function guardGoogleReturn({location=globalThis.location,history=globalThis.history,request=globalThis.fetch}={}){
  if(typeof location.href!=='string'||location.href.length>32768)throw Error('GOOGLE_RETURN_REFUSED');
  const url=new URL(location.href),fragment=new URLSearchParams(url.hash.slice(1));
  if(!fragment.has('access_token')&&!url.searchParams.has('oauth_return'))return false;
  const nonce=url.searchParams.get('oauth_return');
  if(url.origin!==GOOGLE_APP_ORIGIN||url.pathname!==GOOGLE_RETURN_PATH||url.username||url.password||
     url.searchParams.size!==1||!GOOGLE_NONCE.test(nonce||''))throw Error('GOOGLE_RETURN_REFUSED');
  const keys=[...fragment.keys()],error=fragment.has('error');
  const allowed=error?['error','error_description','error_code','error_id']:['access_token','token_type','expires_in','expires_at','refresh_token'];
  if(!keys.length||keys.length!==new Set(keys).size||keys.some(k=>!allowed.includes(k))||
     [...fragment.values()].some(v=>v.length>8192||/[\x00-\x1f\x7f]/.test(v)))throw Error('GOOGLE_RETURN_REFUSED');
  if(!error&&(!fragment.get('access_token')||fragment.get('token_type')!=='bearer'||!/^\d+$/.test(fragment.get('expires_in')||'')||
     !Number.isSafeInteger(Number(fragment.get('expires_in')))||Number(fragment.get('expires_in'))<=0))throw Error('GOOGLE_RETURN_REFUSED');
  if(!error&&['access_token','refresh_token'].some(key=>fragment.has(key)&&/\s/.test(fragment.get(key))))throw Error('GOOGLE_RETURN_REFUSED');
  const response=await request(GOOGLE_CONSUME_PATH,{method:'POST',credentials:'same-origin',cache:'no-store',redirect:'error',
    headers:{'Content-Type':'application/json'},body:JSON.stringify({nonce}),signal:AbortSignal.timeout(10000)});
  if(!response.ok||!response.headers.get('Content-Type')?.includes('application/json')||(await response.json()).correlationVerified!==true)
    throw Error('GOOGLE_RETURN_CORRELATION_REFUSED');
  history.replaceState(null,'',GOOGLE_RETURN_PATH+(error?'':url.hash));
  if(error)throw Error('GOOGLE_PROVIDER_DID_NOT_COMPLETE');
  return true; // Existing SDK and SAME verified server subject still required.
}
