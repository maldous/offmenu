import {GOOGLE_APP_ORIGIN,GOOGLE_RETURN_PATH,GOOGLE_CONSUME_PATH,GOOGLE_NONCE} from '../public/google-return-guard.js';
const REALM='https://offmenu-accounts.netlify.app/.netlify/identity';
const AUTHORIZE='/.netlify/identity/authorize',COOKIE='offmenu_google_return_v2',TTL=300000;
const headers={'Cache-Control':'no-store','Referrer-Policy':'no-referrer','X-Content-Type-Options':'nosniff'};
const json=(value,status=200,extra={})=>Response.json(value,{status,headers:{...headers,...extra}});
const hex=bytes=>[...new Uint8Array(bytes)].map(b=>b.toString(16).padStart(2,'0')).join('');
const sha=value=>crypto.subtle.digest('SHA-256',new TextEncoder().encode(value)).then(hex);
const cookie=value=>COOKIE+'='+value+'; Path='+GOOGLE_CONSUME_PATH+'; Secure; HttpOnly; SameSite=Lax; Max-Age='+(value?'300':'0');
function policyReady(policy){
  if(!policy||typeof policy.callbackUrl!=='string'||!/^\/[a-zA-Z0-9/_-]+$/.test(policy.authorizePath||'')||
     !['/o/oauth2/auth','/o/oauth2/v2/auth'].includes(policy.authorizePath)||
     !/^[a-zA-Z0-9_-]+\.apps\.googleusercontent\.com$/.test(policy.clientId||'')||
     !Array.isArray(policy.scopes)||!policy.scopes.length||policy.scopes.length!==new Set(policy.scopes).size||
     policy.scopes.some(s=>!['openid','email','profile','https://www.googleapis.com/auth/userinfo.email','https://www.googleapis.com/auth/userinfo.profile'].includes(s)))return false;
  try{const url=new URL(policy.callbackUrl);
    // Observed centralhost only. Exactpath/publicclient/scopes MUST be qualified;
    // no old realm-callback pin or wildcard is accepted by this correction.
    return url.origin==='https://identity.services.netlify.com'&&url.pathname!=='/'&&!url.username&&!url.password&&!url.search&&!url.hash;
  }catch{return false;}
}
function validateProviderRedirect(raw,policy){
  if(typeof raw!=='string'||raw.length>16384||/[\x00-\x20\x7f]/.test(raw))throw Error('GOOGLE_REDIRECT_REFUSED');
  const url=new URL(raw),keys=[...url.searchParams.keys()],expected=['client_id','redirect_uri','response_type','scope','state'];
  if(url.origin!=='https://accounts.google.com'||url.pathname!==policy.authorizePath||url.username||url.password||url.hash||
     keys.length!==expected.length||new Set(keys).size!==keys.length||keys.some(k=>!expected.includes(k))||
     url.searchParams.get('client_id')!==policy.clientId||url.searchParams.get('redirect_uri')!==policy.callbackUrl||
     url.searchParams.get('response_type')!=='code')throw Error('GOOGLE_REDIRECT_REFUSED');
  const scopes=(url.searchParams.get('scope')||'').split(' '),state=url.searchParams.get('state');
  if(scopes.length!==policy.scopes.length||new Set(scopes).size!==scopes.length||scopes.some(s=>!policy.scopes.includes(s))||
     !state||state.length>8192)throw Error('GOOGLE_REDIRECT_REFUSED');
  // Provider state remains opaque and unchanged; never decode/log/store it.
}
export function createGoogleReturnProxy({enabled=false,callbackPolicy=null,fetchImpl,assertAuthority,pendingStore,now=()=>Date.now()}={}){
  return Object.freeze({async handle(request){
    const url=new URL(request.url);
    if(![AUTHORIZE,GOOGLE_CONSUME_PATH].includes(url.pathname))return null;
    if(url.pathname===AUTHORIZE&&url.searchParams.get('provider')!=='google')return null;
    // Preserve the existing provider route while this correction is unselected.
    if(!enabled)return url.pathname===AUTHORIZE?null:json({error:'GOOGLE_RETURN_NOT_QUALIFIED'},501);
    if(!enabled||!policyReady(callbackPolicy)||typeof fetchImpl!=='function'||typeof assertAuthority!=='function')
      return json({error:'GOOGLE_RETURN_NOT_QUALIFIED'},501);
    if(typeof pendingStore?.reserve!=='function'||typeof pendingStore?.consume!=='function')return json({error:'GOOGLE_RETURN_NOT_QUALIFIED'},501);
    if(url.origin!==GOOGLE_APP_ORIGIN||url.username||url.password||url.hash)return json({error:'GOOGLE_APP_ORIGIN_REFUSED'},403);
    if(url.pathname===AUTHORIZE){
      if(request.method!=='GET'||url.searchParams.size!==1||url.searchParams.get('provider')!=='google'||
         !['same-origin','none'].includes(request.headers.get('Sec-Fetch-Site')))return json({error:'GOOGLE_REQUEST_REFUSED'},403);
      let nonceKey,issued=false;
      try{
        if(await assertAuthority({operation:'authorize-google',origin:GOOGLE_APP_ORIGIN,returnPath:GOOGLE_RETURN_PATH})!==undefined)throw Error();
        const nonce=hex(crypto.getRandomValues(new Uint8Array(32))),returnURL=new URL(GOOGLE_RETURN_PATH,GOOGLE_APP_ORIGIN);
        nonceKey=await sha(nonce);
        if(!await pendingStore.reserve(nonceKey,now()+TTL,now()))return json({error:'GOOGLE_RETURN_CAPACITY'},429);
        returnURL.searchParams.set('oauth_return',nonce);
        const upstreamURL=new URL(REALM+'/authorize');upstreamURL.searchParams.set('provider','google');
        // Actual SDK query preserved. This is GoTrue's published getReferrer
        // mechanism, constructed by this allowlisted proxy, not a caller header.
        const response=await fetchImpl(upstreamURL.href,{method:'GET',headers:{Accept:'text/html',Referer:returnURL.href},
          credentials:'omit',redirect:'manual',signal:AbortSignal.timeout(10000)});
        if(response.redirected||response.status!==302){await response.body?.cancel();return json({error:'GOOGLE_AUTHORIZE_UNAVAILABLE'},response.status===429?429:503);}
        const location=response.headers.get('Location');validateProviderRedirect(location,callbackPolicy);await response.body?.cancel();
        issued=true;return new Response(null,{status:302,headers:{...headers,Location:location,'Set-Cookie':cookie(nonce)}});
      }catch{return json({error:'GOOGLE_AUTHORIZE_UNAVAILABLE'},503);}
      finally{if(nonceKey&&!issued)try{await pendingStore.consume(nonceKey,now());}catch{}}
    }
    if(request.method!=='POST'||url.search||request.headers.get('Origin')!==GOOGLE_APP_ORIGIN||
       request.headers.get('Content-Type')?.split(';')[0].trim()!=='application/json')return json({error:'GOOGLE_CONSUME_REFUSED'},403);
    try{
      const reader=request.body?.getReader();if(!reader)throw Error();let text='',size=0;const decoder=new TextDecoder();
      try{for(;;){const part=await reader.read();if(part.done)break;size+=part.value.length;if(size>1024)throw Error();text+=decoder.decode(part.value,{stream:true});}}
      finally{await reader.cancel().catch(()=>{});reader.releaseLock();}
      const body=JSON.parse(text+decoder.decode());
      if(Object.keys(body).length!==1||!GOOGLE_NONCE.test(body.nonce||''))throw Error();
      const cookies=(request.headers.get('Cookie')||'').split(';').map(s=>s.trim()).filter(s=>s.startsWith(COOKIE+'='));
      if(cookies.length!==1||cookies[0]!==COOKIE+'='+body.nonce)throw Error();
      if(await assertAuthority({operation:'consume-google-return',origin:GOOGLE_APP_ORIGIN,returnPath:GOOGLE_RETURN_PATH})!==undefined)throw Error();
      const key=await sha(body.nonce);if(!await pendingStore.consume(key,now()))throw Error();
      return json({correlationVerified:true,identityVerified:false},200,{'Set-Cookie':cookie('')});
    }catch{return json({error:'GOOGLE_CONSUME_REFUSED'},403,{'Set-Cookie':cookie('')});}
  }});
}
