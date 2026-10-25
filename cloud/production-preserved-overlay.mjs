import application from './deployed-application.mjs';
import {selectedProductionLookup} from './production-selected-lookup.mjs';
import {authPageRoutes} from './auth-page-routes.mjs';
import {productionAccessGuard,protectProductionResponse} from './production-access-guard.mjs';
import {assets, release} from './production-overlay-assets.mjs';

// Same verifier and existing realm as the deployed ac2 application. No sessions
// or roles are issued by this readback endpoint.
const IDENTITY='https://offmenu-accounts.netlify.app/.netlify/identity';
async function verifiedUser(request){const auth=request.headers.get('Authorization');const cookie=request.headers.get('Cookie')||'';const encoded=cookie.match(/(?:^|;\s*)nf_jwt=([^;]+)/)?.[1];let token;try{token=auth?.startsWith('Bearer ')?auth.slice(7):encoded?decodeURIComponent(encoded):null;}catch{return null;}if(!token)return null;const r=await fetch(IDENTITY+'/user',{headers:{Authorization:'Bearer '+token},signal:AbortSignal.timeout(10000)});if(!r.ok)return null;const user=await r.json();return typeof user.id==='string'&&user.id.length<200?user:null;}
const headers={'X-Content-Type-Options':'nosniff','Referrer-Policy':'no-referrer','Permissions-Policy':'camera=(self), microphone=()',
  'Content-Security-Policy':"default-src 'self'; script-src 'self' 'wasm-unsafe-eval'; style-src 'self' 'unsafe-inline'; img-src 'self' blob: data:; media-src 'self' blob:; connect-src 'self' https://offmenu-corpus.netlify.app; worker-src 'self'; object-src 'none'; base-uri 'self'; frame-ancestors 'none'"};
async function retainedKitchenPage(request,env,ctx){
  const response=await application.fetch(request,env,ctx);
  if(request.method!=='GET'||response.status!==200||!response.headers.get('Content-Type')?.includes('text/html'))return response;
  const html=await response.text();
  const body=html.replace('</head>','<script type="module" src="/legacy-sign-in-redirect.js"></script></head>');
  const nextHeaders=new Headers(response.headers);nextHeaders.delete('Content-Length');nextHeaders.delete('ETag');
  nextHeaders.set('Cache-Control','no-cache');
  return new Response(body,{status:response.status,headers:nextHeaders});
}
export default {
  async fetch(request,env,ctx){
    const url=new URL(request.url);
    if((env.OFFMENU_AUTH_MODE!==undefined&&env.OFFMENU_AUTH_MODE!=='netlify')||env.DEV_COMPOSITION||env.OFFMENU_LOCAL_LAB)
      return Response.json({error:'Authentication is unavailable.'},{status:503,headers:{'Cache-Control':'no-store'}});
    if(url.pathname.startsWith('/__dev/')||url.pathname.startsWith('/api/dev-auth'))return new Response('Not found',{status:404});
    const auth=await authPageRoutes(request,env,{runtime:{mode:'netlify',verifiedUser},authPageOptions:{identityTransport:'real',oauthCallbackReady:false}});
    if(auth)return auth;
    const denied=await productionAccessGuard(request,env,{verifiedUser});
    if(denied)return denied;
    const respond=async()=>{
    const selectedLookup=await selectedProductionLookup(request,env);if(selectedLookup)return selectedLookup;
    if(['/api/product','/api/prices','/api/data/public'].includes(url.pathname))
      return Response.json({error:'Product information is unavailable.'},{status:503,headers:{'Cache-Control':'no-store'}});
    if(['GET','HEAD'].includes(request.method)){
      if(url.pathname==='/api/landing-release')return Response.json(release,{headers:{'Cache-Control':'no-store'}});
      const file=url.pathname==='/'?'landing.html':url.pathname.slice(1);
      if(Object.hasOwn(assets,file)){
        const type=file.endsWith('.html')?'text/html; charset=utf-8':file.endsWith('.css')?'text/css; charset=utf-8':file.endsWith('.js')?'application/javascript':file.endsWith('.svg')?'image/svg+xml':file.endsWith('.ttf')?'font/ttf':'text/plain; charset=utf-8';
        const value=file.endsWith('.ttf')?Uint8Array.from(atob(assets[file]),c=>c.charCodeAt(0)):assets[file];
        return new Response(request.method==='HEAD'?null:value,{headers:{...headers,'Content-Type':type,'Cache-Control':'no-cache'}});
      }
      if(url.pathname==='/kitchen.html'){url.pathname='/';return retainedKitchenPage(new Request(url,request),env,ctx);}
      if(url.pathname==='/index.html')return retainedKitchenPage(request,env,ctx);
    }
    return application.fetch(request,env,ctx);
    };
    return protectProductionResponse(request,await respond());
  },
  scheduled(event,env,ctx){return application.scheduled(event,env,ctx);}
};
