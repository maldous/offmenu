import {Response as WorkerResponse} from 'miniflare';
import {CONTRACTS} from './mappings.mjs';
import {ACTORS} from './fixtures.mjs';
export function loopbackOrigin(value){const u=new URL(value);if(u.protocol!=='http:'||!['127.0.0.1','[::1]'].includes(u.hostname)||!u.port||u.username||u.password||u.pathname!=='/'||u.search||u.hash)throw Error('WireMock must use an explicit loopback HTTP origin/port.');return u.origin;}
export function contractFor(url,method){const u=new URL(url);return CONTRACTS.http.find(c=>(c.hosts?.includes(u.hostname)||c.hostPattern&&new RegExp(c.hostPattern).test(u.hostname))&&c.methods.includes(method.toUpperCase())&&c.paths.some(p=>new RegExp(p).test(u.pathname)));}
function syntheticOnly(url,headers,body,contract){
 const expected={api_key:'fixture-usda',app_id:'fixture-edamam-id',app_key:'fixture-edamam-key'};
 for(const [name,value] of url.searchParams)if(/key|token|secret|password/i.test(name)&&value!==expected[name])throw Error('Non-fixture query credential refused.');
 const auth=headers.get('authorization');if(auth&&!Object.values(ACTORS).some(a=>auth==='Bearer '+a.token)&&auth!=='Bearer fixture-ai'&&auth!=='Bearer fixture-invalid')throw Error('Non-fixture authorization refused.');
 if(headers.has('api-key')&&headers.get('api-key')!=='fixture-brevo')throw Error('Non-fixture email key refused.');
 if(headers.has('x-api-key'))throw Error('Uncontracted credential header refused.');
 const sentry=headers.get('x-sentry-auth');if(sentry&&!/sentry_key=0{32}(?:,|$)/.test(sentry))throw Error('Non-fixture diagnostics key refused.');
 if(contract.id==='identity'&&body){const type=headers.get('content-type')||'';let data;if(type.includes('json')){data=JSON.parse(body);}else data=Object.fromEntries(new URLSearchParams(body));for(const name of ['email','username'])if(data[name]&&!/^(alice|bob|admin)@example\.test$/.test(data[name]))throw Error('Identity accepts synthetic actors only.');if(data.password&&data.password!=='fixture-password')throw Error('Identity accepts fixture-password only.');if(data.refresh_token&&!Object.values(ACTORS).some(a=>a.refreshToken===data.refresh_token))throw Error('Non-fixture refresh token refused.');}
 if(contract.id==='brevo'&&body){const payload=JSON.parse(body);const addresses=[payload.sender,...(payload.to||[])];if(addresses.some(x=>!x?.email?.endsWith('@example.test')))throw Error('Email accepts synthetic recipients only.');}
}
export function createOutboundAdapter({wiremockOrigin,scenario='success',overrides={},timeoutMs=2000,onEvent=()=>{}}){
 const origin=loopbackOrigin(wiremockOrigin);if(!CONTRACTS.scenarios.includes(scenario)||Object.values(overrides).some(s=>!CONTRACTS.scenarios.includes(s)))throw Error('Unknown fixture scenario.');
 return async request=>{
  const u=new URL(request.url),contract=contractFor(u,request.method),event={host:u.hostname,path:u.pathname,method:request.method,contract:contract?.id||null};
  try{
   if(!contract)throw Error('Uncontracted outbound request; live passthrough is disabled.');
   const headers=new Headers(request.headers),body=['GET','HEAD'].includes(request.method)?undefined:await request.text();syntheticOnly(u,headers,body,contract);
   const local=new URL(u.pathname+u.search,origin);const forwarded=new Headers();for(const name of ['content-type','accept','authorization','api-key','x-api-version','x-sentry-auth'])if(headers.has(name))forwarded.set(name,headers.get(name));
   forwarded.set('X-OffMenu-Upstream-Host',u.hostname);forwarded.set('X-OffMenu-Scenario',overrides[contract.id]||scenario);
   const response=await fetch(local,{method:request.method,headers:forwarded,body,redirect:'manual',signal:AbortSignal.timeout(timeoutMs)});
   if(response.status===404&&!response.headers.get('X-OffMenu-Dev-Mock'))throw Error('Known dependency has no seeded WireMock mapping.');
   onEvent({...event,status:response.status,blocked:false});return new WorkerResponse(await response.arrayBuffer(),{status:response.status,headers:response.headers});
  }catch(error){onEvent({...event,status:502,blocked:true,error:error.message});return WorkerResponse.json({error:'Development mock failure: '+error.message},{status:502,headers:{'X-OffMenu-Dev-Mock':'blocked','Cache-Control':'no-store'}});}
 };
}
// Playwright BrowserContext adapter: install before any navigation.
export async function installBrowserAudit(context,{appOrigin,wiremockOrigin,scenario='success',onEvent=()=>{}}){
 const app=new URL(appOrigin);if(!['127.0.0.1','localhost','[::1]'].includes(app.hostname))throw Error('Browser audit requires a local app.');
 const adapter=createOutboundAdapter({wiremockOrigin,scenario,onEvent});
 await context.route('**/*',async route=>{
  const r=route.request(),u=new URL(r.url());if(u.origin===app.origin)return route.continue();
  const contract=contractFor(u,r.method());if(!contract||!['browser','both'].includes(contract.kind)){onEvent({host:u.hostname,path:u.pathname,method:r.method(),blocked:true,error:'Uncontracted browser request'});return route.fulfill({status:502,contentType:'text/plain',body:'External development request blocked; no live passthrough.'});}
  const response=await adapter(new Request(r.url(),{method:r.method(),headers:r.headers(),...(['GET','HEAD'].includes(r.method())?{}:{body:r.postData()||''})}));
  return route.fulfill({status:response.status,headers:Object.fromEntries(response.headers),body:Buffer.from(await response.arrayBuffer())});
 });
}
