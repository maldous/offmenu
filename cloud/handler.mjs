import {requestLocale,localizedHTML} from './locale.mjs';
import {catalogueRoutes} from './catalogue.mjs';
import {enrichmentRoutes} from './enrichment.mjs';
import {kitchenRoutes} from './kitchens.mjs';
import {sourceById} from '../public/sources.js';
import {normalizeOFF,normalizePrices} from '../public/unified-data.js';
import {providerDataRoutes} from './provider-data.mjs';
import {integrationRoutes} from './integrations.mjs';
import {cleanupAdminMcp} from './admin-mcp.mjs';
import {validateState} from './state.mjs';
import {serviceRoutes,serviceCSP,serviceHTML} from './service-config.mjs';
import {serviceSupportRoutes,cleanupServiceRequests} from './service-support.mjs';
import {diagnosticRoutes,reportDiagnostic,routeGroup} from './service-observability.mjs';
import {adminSettingsRoutes,loadAdminRuntime} from './admin-settings.mjs';
import {adminOperationsRoutes} from './admin-operations.mjs';
import {careCaseRoutes,cleanupCareCases} from './care-cases.mjs';
import {careCommunityRoutes,cleanupCareCommunity} from './care-community.mjs';
import {careUpdateRoutes,cleanupCareUpdates} from './care-updates.mjs';
import {recipeCommunityRoutes} from './recipe-community.mjs';
import {communityAIRoutes} from './community-ai.mjs';
import {personalAIRoutes} from './personal-ai.mjs';
const IDENTITY='https://offmenu-accounts.netlify.app/.netlify/identity';
const SECURITY={'X-Content-Type-Options':'nosniff','Referrer-Policy':'no-referrer','Permissions-Policy':'camera=(self), microphone=()','Content-Security-Policy':"default-src 'self'; script-src 'self' 'wasm-unsafe-eval'; style-src 'self' 'unsafe-inline'; img-src 'self' blob:; media-src 'self' blob:; connect-src 'self' https://offmenu-corpus.netlify.app; worker-src 'self'; object-src 'none'; base-uri 'self'; frame-ancestors 'none'"};
const reply=(data,status=200)=>Response.json(data,{status,headers:{...SECURITY,'Cache-Control':'no-store'}});
async function boundedJSON(request,limit=2_000_000){const reader=request.body?.getReader();if(!reader)throw Error('Missing body.');const chunks=[];let size=0;for(;;){const {done,value}=await reader.read();if(done)break;size+=value.length;if(size>limit){await reader.cancel();throw Error('Data exceeds 2 MB.');}chunks.push(value);}const bytes=new Uint8Array(size);let offset=0;for(const chunk of chunks){bytes.set(chunk,offset);offset+=chunk.length;}return JSON.parse(new TextDecoder().decode(bytes));}
async function verifiedUser(request){const auth=request.headers.get('Authorization');const cookie=request.headers.get('Cookie')||'';const encoded=cookie.match(/(?:^|;\s*)nf_jwt=([^;]+)/)?.[1];let token;try{token=auth?.startsWith('Bearer ')?auth.slice(7):encoded?decodeURIComponent(encoded):null;}catch{return null;}if(!token)return null;const r=await fetch(IDENTITY+'/user',{headers:{Authorization:'Bearer '+token},signal:AbortSignal.timeout(10000)});if(!r.ok)return null;const user=await r.json();return typeof user.id==='string'&&user.id.length<200?user:null;}
export default {async scheduled(event,env,ctx){ctx.waitUntil((async()=>{await cleanupAdminMcp(env);const runtime=await loadAdminRuntime(env),serviceEnv=runtime.env;await env.DB.prepare('DELETE FROM resolver_cache WHERE fresh_until<? AND retry_after<?').bind(Date.now()-14*86400000,Date.now()).run();await env.DB.prepare('DELETE FROM resolver_leases WHERE expires_at<?').bind(Date.now()).run();await env.DB.prepare("DELETE FROM unified_records WHERE owner NOT LIKE 'public:%' AND json_valid(document) AND json_extract(document,'$.provenance.retainUntil') IS NOT NULL AND julianday(json_extract(document,'$.provenance.retainUntil'))<=julianday(?)").bind(new Date().toISOString()).run();await env.DB.prepare('DELETE FROM evidence_assertions WHERE retain_until<?').bind(Date.now()).run();await env.DB.prepare('DELETE FROM integration_limits WHERE bucket<?').bind(Math.floor(Date.now()/3600000)-24).run();await cleanupServiceRequests(serviceEnv);await cleanupCareCases(env);await cleanupCareCommunity(env);await cleanupCareUpdates(env);})());},async fetch(request,env,ctx){const url=new URL(request.url);try{
for(const route of [careCaseRoutes,careCommunityRoutes,careUpdateRoutes,recipeCommunityRoutes,communityAIRoutes,personalAIRoutes]){const response=await route(request,env,{verifiedUser,boundedJSON,reply});if(response)return response;}
if(url.pathname.startsWith('/api/care/')||url.pathname.startsWith('/api/community/')||url.pathname.startsWith('/api/admin/care/')||url.pathname.startsWith('/api/admin/community/'))return reply({error:'Not found'},404);
const adminOperation=await adminOperationsRoutes(request,env,{verifiedUser,boundedJSON,reply});if(adminOperation)return adminOperation;
const admin=await adminSettingsRoutes(request,env,{verifiedUser,boundedJSON,reply});if(admin)return admin;
let serviceEnv=env;
if(url.pathname.startsWith('/api/services')||url.pathname==='/robots.txt'||url.pathname==='/sitemap.xml'){
 const runtime=await loadAdminRuntime(env);serviceEnv=runtime.env;
 const services=serviceRoutes(request,serviceEnv,{reply});if(services)return services;
 const support=await serviceSupportRoutes(request,serviceEnv,{verifiedUser,boundedJSON,reply});if(support)return support;
 const diagnostics=await diagnosticRoutes(request,serviceEnv,{verifiedUser,boundedJSON,reply,release:typeof RELEASE==='undefined'?{}:RELEASE});if(diagnostics)return diagnostics;
}
const catalogue=await catalogueRoutes(request,env,{verifiedUser,boundedJSON});if(catalogue)return catalogue;
const enrichment=await enrichmentRoutes(request,env,{boundedJSON});if(enrichment)return enrichment;
const kitchen=await kitchenRoutes(request,env,{verifiedUser,boundedJSON});if(kitchen)return kitchen;
const providerData=await providerDataRoutes(request,env,{verifiedUser,boundedJSON,assets:typeof ASSETS==='undefined'?{}:ASSETS});if(providerData)return providerData;
const integration=await integrationRoutes(request,env,{verifiedUser,boundedJSON,assets:typeof ASSETS==='undefined'?{}:ASSETS});if(integration)return integration;
if(url.pathname.startsWith('/.netlify/identity/')){
 if(!['GET','POST','PUT'].includes(request.method))return reply({error:'Method not allowed'},405);
 if(request.method!=='GET'&&request.headers.get('Origin')!==url.origin)return reply({error:'Origin mismatch'},403);
 const suffix=url.pathname.slice('/.netlify/identity'.length);if(!/^\/(settings|token|signup|user|verify|recover|logout|authorize|callback)$/.test(suffix))return reply({error:'Not found'},404);
 const headers=new Headers();for(const key of ['Content-Type','Authorization'])if(request.headers.has(key))headers.set(key,request.headers.get(key));
 const response=await fetch(IDENTITY+suffix+url.search,{method:request.method,headers,body:request.method==='GET'?undefined:request.body,redirect:'manual',signal:AbortSignal.timeout(15000)});
 const resultHeaders=new Headers({...SECURITY,'Cache-Control':'no-store'});for(const key of ['Content-Type','Location'])if(response.headers.has(key))resultHeaders.set(key,response.headers.get(key));return new Response(response.body,{status:response.status,headers:resultHeaders});
}
if(url.pathname==='/api/state'){
 if(!env.DB)return reply({error:'Cloud storage unavailable'},503);
 if(!['GET','PUT'].includes(request.method))return reply({error:'Method not allowed'},405);
 if(request.method==='PUT'&&request.headers.get('Origin')!==url.origin)return reply({error:'Origin mismatch'},403);
 const user=await verifiedUser(request);if(!user)return reply({error:'Sign in to access cloud data.'},401);
 if(request.method==='GET'){const row=await env.DB.prepare('SELECT revision,state_json AS data,updated_at FROM user_state WHERE user_id=?').bind(user.id).first();return reply({revision:row?.revision||0,state:row?JSON.parse(row.data):null,updated_at:row?.updated_at||null});}
 let body,state;try{body=await boundedJSON(request);state=validateState(body.state);if(!Number.isSafeInteger(body.revision)||body.revision<0)throw Error('Invalid revision.');}catch(e){return reply({error:e.message},400);}
 const now=new Date().toISOString();const row=body.revision===0?await env.DB.prepare('INSERT INTO user_state(user_id,revision,state_json,updated_at) VALUES(?,1,?,?) ON CONFLICT(user_id) DO NOTHING RETURNING revision').bind(user.id,JSON.stringify(state),now).first():await env.DB.prepare('UPDATE user_state SET revision=revision+1,state_json=?,updated_at=? WHERE user_id=? AND revision=? RETURNING revision').bind(JSON.stringify(state),now,user.id,body.revision).first();
 if(!row)return reply({error:'A newer cloud save exists. Load it before saving; export your local copy first.'},409);return reply({revision:row.revision,updated_at:now});
}
if(url.pathname==='/retailer-extension.zip'&&request.method==='GET')return new Response(Uint8Array.from(atob(ASSETS['retailer-extension.zip']),c=>c.charCodeAt(0)),{headers:{...SECURITY,'Content-Type':'application/zip','Content-Disposition':'attachment; filename=offmenu-retailer-extension.zip'}});
if(request.method!=='GET')return reply({error:'Method not allowed'},405);
if(url.pathname==='/api/health')return reply({status:'ok',cloud_storage:!!env.DB,release:typeof RELEASE==='undefined'?null:RELEASE});
if(url.pathname==='/api/recipes'){const data=await env.DB.prepare('SELECT doc AS data FROM recipes ORDER BY id').all();const saved=data.results.map(x=>JSON.parse(x.data)),shipped=typeof ASSETS==='undefined'?[]:JSON.parse(ASSETS['recipes.json']||'[]');return reply([...new Map([...saved,...shipped].map(r=>[r.id,r])).values()]);}
if(url.pathname==='/api/product'||url.pathname==='/api/prices'){
 const barcode=url.searchParams.get('barcode')||'';if(!/^\d{4,32}$/.test(barcode))return reply({error:'Invalid barcode'},400);
 const product=url.pathname==='/api/product',table=product?'products':'price_observations';const now=Date.now();const cached=null; // Source responses are transient; only OffMenu curation may be cached.
 if(cached&&now-cached.checked_at<3600000){const data=JSON.parse(cached.data);if(!data.offmenu)data.offmenu={schemaVersion:'1.0',records:product?(data.status===1?normalizeOFF(data,sourceById('off')):[]):normalizePrices(data,sourceById('prices'))};return reply(data);}
 const upstream=product?`https://world.openfoodfacts.org/api/v2/product/${barcode}.json?fields=code,rev,last_modified_t,last_updated_t,lang,product_name,product_name_en,brands,quantity,categories_tags,ingredients_text,allergens_tags,countries_tags,stores_tags,nutriments,nutrition_data_per,nutrition_data_prepared_per,nutriscore_grade,product_quantity,product_quantity_unit`:`https://prices.openfoodfacts.org/api/v1/prices?product_code=${barcode}&size=30&order_by=-date`;
 try{const response=await fetch(upstream,{headers:{'User-Agent':'offmenu/0.2 (https://offmenu.aldous.info)'},signal:AbortSignal.timeout(12000)});if(!response.ok)return reply({error:response.status===404?'Product not found.':'Lookup temporarily unavailable.'},response.status===404?404:502);const data=await boundedJSON(response);data.offmenu={schemaVersion:'1.0',records:product?(data.status===1?normalizeOFF(data,sourceById('off')):[]):normalizePrices(data,sourceById('prices'))};data.offmenu_cachePolicy='source-response-not-persisted';return reply(data);}catch{if(cached)return reply({...JSON.parse(cached.data),offmenu_stale:true,offmenu_checked_at:cached.checked_at});return reply({error:'Lookup timed out. Manual entry remains available.'},502);}
}
const file=url.pathname==='/'?'index.html':url.pathname.slice(1);if(!Object.hasOwn(ASSETS,file))return new Response('Not found',{status:404,headers:SECURITY});
const dynamicHTML=file.endsWith('.html');if(dynamicHTML){const runtime=await loadAdminRuntime(env);serviceEnv=runtime.env;}
if(file==='scanner.wasm')return new Response(Uint8Array.from(atob(ASSETS[file]),c=>c.charCodeAt(0)),{headers:{...SECURITY,'Content-Type':'application/wasm','Cache-Control':'public, max-age=300'}});const type=file.endsWith('.html')?'text/html; charset=utf-8':file.endsWith('.css')?'text/css; charset=utf-8':file.endsWith('.js')?'application/javascript':file.endsWith('.svg')?'image/svg+xml':file.endsWith('.webmanifest')?'application/manifest+json':file.endsWith('.txt')?'text/plain; charset=utf-8':'application/json';const response=new Response(file.endsWith('.html')?serviceHTML(ASSETS[file],serviceEnv):ASSETS[file],{headers:{...SECURITY,'Content-Security-Policy':dynamicHTML?serviceCSP(serviceEnv):SECURITY['Content-Security-Policy'],'Content-Type':type,'Cache-Control':file==='sw.js'||file==='index.html'?'no-cache':'public, max-age=300'}});if(file==='index.html'||file==='data-workspace.html')return localizedHTML(response,await requestLocale(request,serviceEnv,verifiedUser));return response;
}catch(e){console.error(JSON.stringify({event:'request_failed',route:routeGroup(url.pathname)}));let diagnosticEnv={};try{diagnosticEnv=(await loadAdminRuntime(env)).env;}catch{}const diagnostic=reportDiagnostic(diagnosticEnv,'worker_error',typeof RELEASE==='undefined'?{}:RELEASE);if(ctx?.waitUntil)ctx.waitUntil(diagnostic);else await diagnostic;return reply({error:'Service temporarily unavailable. Your local pantry is retained.'},503);}}};
