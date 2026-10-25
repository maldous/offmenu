// Production application access only. Original dispatch retains role/owner ACLs.
const docs=new Set(['/shelf-scanner.html','/shelf-scanner','/kitchen.html','/index.html','/data-workspace.html']);
const bootstrap=new Set(['/','/landing.html','/landing.css','/landing.js','/offmenu-neon.html',
  '/auth.html','/auth.js','/auth-return-bridge.js','/legacy-sign-in-redirect.js',
  '/offmenu-system.css','/style.css','/app.js','/sw.js','/manifest.webmanifest',
  '/scanner-balanced-final.svg','/scanner-balanced-final-dark.svg','/scanner-roboto-regular.ttf',
  '/scanner-roboto-bold.ttf','/scanner-font-license.txt','/scanner-theme-init.js',
  '/api/landing-release','/api/health','/api/auth-page/config','/api/auth-page/session']);
const within=(path,base)=>path===base||path.startsWith(base+'/');
export function productionAccessClass(path){
  // These are delegated to existing DB-hashed personal-token / OAuth verifiers,
  // not made public and not subjected to a second, unrelated Netlify identity.
  if(path==='/mcp'||path.startsWith('/api/v1/')||within(path,'/oauth')||
    path.startsWith('/.well-known/')||path==='/openapi.json')return 'original-protocol-auth';
  if(bootstrap.has(path)||within(path,'/.netlify/identity'))return 'public-auth-bootstrap';
  if(docs.has(path))return 'protected-document';
  if(path.startsWith('/api/'))return 'protected-api';
  if(path==='/recipes.json'||path==='/afcd-nutrient-details.json')return 'protected-data';
  if(path.startsWith('/scanner-')||path.startsWith('/shelf-scanner')||
    path.startsWith('/production-scanner-')||path==='/scanner.wasm')return 'protected-asset';
  return 'original-dispatch';
}
const protectedClass=value=>value.startsWith('protected-');
const denialHeaders={'Cache-Control':'no-store','Vary':'Cookie, Authorization',
  'X-Content-Type-Options':'nosniff','Referrer-Policy':'no-referrer'};
export async function productionAccessGuard(request,env,{verifiedUser}={}){
  const kind=productionAccessClass(new URL(request.url).pathname);
  if(!protectedClass(kind))return null;
  if((env?.OFFMENU_AUTH_MODE!==undefined&&env.OFFMENU_AUTH_MODE!=='netlify')||
    env?.DEV_COMPOSITION||env?.OFFMENU_LOCAL_LAB||typeof verifiedUser!=='function')
    return Response.json({error:'AUTH_SESSION_UNAVAILABLE'},{status:503,headers:denialHeaders});
  let user;
  try{user=await verifiedUser(request);}catch{
    return Response.json({error:'AUTH_SESSION_UNAVAILABLE'},{status:503,headers:denialHeaders});
  }
  if(user&&typeof user.id==='string'&&user.id.trim()&&user.id.length<200)return null;
  if(kind==='protected-document'&&['GET','HEAD'].includes(request.method))
    return new Response(null,{status:303,headers:{...denialHeaders,Location:'/auth.html'}});
  return Response.json({error:'SIGN_IN_REQUIRED',signIn:'/auth.html'},{status:401,headers:denialHeaders});
}
// The 00 wrapper applies this to delegated responses too: authenticated scanner
// bytes must not enter shared/browser caches. No body or Set-Cookie is flattened.
export function protectProductionResponse(request,response){
  if(!protectedClass(productionAccessClass(new URL(request.url).pathname)))return response;
  const next=new Response(response.body,response);
  next.headers.set('Cache-Control','no-store');next.headers.delete('ETag');
  const vary=new Set((next.headers.get('Vary')||'').split(',').map(x=>x.trim()).filter(Boolean));
  vary.add('Cookie');vary.add('Authorization');next.headers.set('Vary',[...vary].join(', '));
  return next;
}
