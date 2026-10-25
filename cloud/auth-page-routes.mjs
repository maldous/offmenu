// UI configuration/session readback only. Authentication remains with the
// deployment-selected existing runtime; this module issues no session or role.
const headers={'Content-Type':'application/json','Cache-Control':'no-store',
  'X-Content-Type-Options':'nosniff','Vary':'Cookie, Authorization'};
const json=(value,status=200)=>new Response(JSON.stringify(value),{status,headers});
export async function authPageRoutes(request,env,{runtime,authOptions}={}) {
  const url=new URL(request.url);
  if(!['/api/auth-page/config','/api/auth-page/session'].includes(url.pathname))return null;
  if(request.method!=='GET')return json({error:'METHOD_NOT_ALLOWED'},405);
  if(!runtime||!['netlify','better-auth'].includes(runtime.mode)||typeof runtime.verifiedUser!=='function')
    return json({error:'AUTH_SETUP_UNAVAILABLE'},503);
  if(url.pathname.endsWith('/config'))return json({schema:'offmenu-auth-page/1',
    mode:runtime.mode,origin:url.origin,synthetic:env?.DEV_COMPOSITION==='pinned-synthetic',
    emailSignIn:runtime.mode==='netlify'?'existing-provider':authOptions?.email?.enabled===true?'enabled':'not-configured',
    oauthAvailable:false,callbackStatus:'not-qualified-for-this-page',
    nextPath:'/shelf-scanner.html'});
  try {
    const user=await runtime.verifiedUser(request);
    if(!user)return json({authenticated:false},401);
    if(typeof user.id!=='string'||!user.id||user.id.length>=200)
      return json({error:'AUTH_SESSION_UNAVAILABLE'},503);
    // An opaque existing subject is enough to detect client/server account
    // disagreement. No profile, email, roles, credentials or tokens are returned.
    return json({authenticated:true,userId:user.id,mode:runtime.mode});
  }catch{return json({error:'AUTH_SESSION_UNAVAILABLE'},503);}
}
