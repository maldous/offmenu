// UI configuration/session readback only. Authentication remains with the
// deployment-selected existing runtime; this module issues no session or role.
const headers={'Content-Type':'application/json','Cache-Control':'no-store',
  'X-Content-Type-Options':'nosniff','Vary':'Cookie, Authorization'};
const json=(value,status=200)=>new Response(JSON.stringify(value),{status,headers});
export async function authPageRoutes(request,env,{runtime,authOptions,authPageOptions}={}) {
  const url=new URL(request.url);
  if(!['/api/auth-page/config','/api/auth-page/session'].includes(url.pathname))return null;
  if(request.method!=='GET')return json({error:'METHOD_NOT_ALLOWED'},405);
  if(!runtime||!['netlify','better-auth'].includes(runtime.mode)||typeof runtime.verifiedUser!=='function')
    return json({error:'AUTH_SETUP_UNAVAILABLE'},503);
  // Only the owner-selected deployment binding can qualify a real transport
  // and callback. Global synthetic data composition does not describe auth.
  const identityTransport=runtime.mode==='netlify'&&authPageOptions?.identityTransport==='real'?'real':
    env?.DEV_COMPOSITION==='pinned-synthetic'?'fixture':'unverified';
  // This selected adapter implements Google correlation only. Other configured
  // realm providers remain unsupported here until their own callback contracts.
  const oauthProviders=identityTransport==='real'&&authPageOptions?.oauthCallbackReady===true&&
    Array.isArray(authPageOptions?.oauthProviders)&&authPageOptions.oauthProviders.includes('google')?['google']:[];
  const oauthAvailable=oauthProviders.length===1;
  const email=authPageOptions?.emailFlows;
  // Deployment-owned exact origin/path qualification, never a browser flag.
  const qualified=identityTransport==='real'&&email?.origin===url.origin&&email?.callbackPath==='/auth.html';
  const confirmationAvailable=qualified&&email.confirmationVerify===true;
  const passwordUpdateAvailable=qualified&&email.passwordUpdate===true;
  const recoveryCallbackAvailable=qualified&&email.recoveryVerify===true&&passwordUpdateAvailable;
  const recoveryAvailable=recoveryCallbackAvailable&&email.recoveryRequest===true;
  const signupAvailable=confirmationAvailable&&email.signup===true;
  if(url.pathname.endsWith('/config'))return json({schema:'offmenu-auth-page/1',
    mode:runtime.mode,origin:url.origin,identityTransport,synthetic:identityTransport==='fixture',
    emailSignIn:runtime.mode==='netlify'?'existing-provider':authOptions?.email?.enabled===true?'enabled':'not-configured',
    oauthAvailable,oauthProviders,callbackStatus:oauthAvailable?'owner-qualified':'not-inspected-for-this-origin',
    signupAvailable,confirmationAvailable,recoveryAvailable,recoveryCallbackAvailable,passwordUpdateAvailable,
    emailCallbackPath:'/auth.html',emailCallbackStatus:qualified?'owner-qualified-exact-origin':'not-qualified',
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
