import test from 'node:test';
import assert from 'node:assert/strict';
import {DatabaseSync} from 'node:sqlite';
import {readFileSync} from 'node:fs';
import handler from '../../apps/web/server/handler.mjs';
import {parseServiceConfig,serviceConfiguration,serviceCSP,serviceHTML,sentryDestination} from '../../apps/web/server/service-config.mjs';
import {diagnosticEvent,diagnosticRoutes,reportDiagnostic,routeGroup} from '../../apps/web/server/service-observability.mjs';

const dsn='https://0123456789abcdef0123456789abcdef@o123.ingest.de.sentry.io/456';
const configured={THIRD_PARTY_CONFIG:JSON.stringify({client:{diagnostics:{enabled:true}}}),SENTRY_DSN:dsn};
function storage(){
  const db=new DatabaseSync(':memory:');
  db.exec(readFileSync(new URL('../../apps/web/server/schema.sql',import.meta.url),'utf8'));
  return {db,DB:{prepare(sql){const make=args=>({async first(){return db.prepare(sql).get(...args)||null;},async run(){return db.prepare(sql).run(...args);}});return {...make([]),bind(...args){return make(args);}}}}};
}
const req=(body,origin='https://offmenu.test')=>new Request('https://offmenu.test/api/services/diagnostics',{method:'POST',headers:{Origin:origin,'Content-Type':'application/json'},body:JSON.stringify(body)});
const deps={reply:(body,status=200)=>Response.json(body,{status}),verifiedUser:async()=>({id:'private-account-id'}),boundedJSON:request=>request.json()};

test('public capability status exposes no runtime credentials and downgrades absent prerequisites',async()=>{
 const env={...storage(),PROVIDER_VAULT_KEY:'a'.repeat(64),BREVO_API_KEY:'private-brevo-credential',BREVO_SENDER_NAME:'OffMenu',BREVO_SENDER_EMAIL:'sender@example.test',SUPPORT_EMAIL:'support@example.test',...configured};
 const result=await handler.fetch(new Request('https://offmenu.test/api/services'),env);
 assert.equal(result.status,200);assert.equal(result.headers.get('Cache-Control'),'no-store');
 const body=await result.json(),text=JSON.stringify(body);
 for(const value of [env.BREVO_API_KEY,env.PROVIDER_VAULT_KEY,env.SENTRY_DSN,env.BREVO_SENDER_EMAIL,env.SUPPORT_EMAIL])assert(!text.includes(value));
 assert.equal(body.services.find(s=>s.id==='brevo').status,'configured');
 assert.equal(serviceConfiguration({THIRD_PARTY_CONFIG:configured.THIRD_PARTY_CONFIG}).client.diagnostics.enabled,false);
 assert.equal(serviceConfiguration({THIRD_PARTY_CONFIG:'{"client":{"trackingSecret":"oops"}}'}).configurationValid,false);
});
test('configuration denies unsafe scripts, partial consent, unknown secrets and unapproved advertising',()=>{
 for(const value of [{secret:'x'},{client:{feedback:{boardUrl:'https://attacker.test/'}}},{client:{consent:{siteId:'123'}}},{client:{consent:{siteId:'90071992547409930',cookiePolicyId:'1'}}},{client:{analytics:{enabled:true}}},{client:{ads:{approved:true,client:'ca-pub-1234567890123456',slot:'1'}}}])assert.throws(()=>parseServiceConfig(value));
 const policy=serviceCSP({});assert(!policy.includes('sleekplan'));assert(!policy.includes('googlesyndication'));assert(!policy.includes('iubenda'));
 const vendor={THIRD_PARTY_CONFIG:JSON.stringify({client:{consent:{siteId:'123',cookiePolicyId:'456'},feedback:{productId:'789'}}})};
 assert(serviceCSP(vendor).includes('https://client.sleekplan.com'));
});
test('verification metadata is escaped by strict token validation and indexing excludes private routes',async()=>{
 const html='<head></head><body></body>',env={THIRD_PARTY_CONFIG:JSON.stringify({seo:{googleSiteVerification:'abc_123',bingSiteVerification:'DEF456'}})};
 assert(serviceHTML(html,env).includes('name="google-site-verification" content="abc_123"'));
 assert.throws(()=>parseServiceConfig({seo:{bingSiteVerification:'"><script>'}}));
 const robots=await(await handler.fetch(new Request('https://offmenu.test/robots.txt'),{})).text();assert(robots.includes('Disallow: /api/'));assert(robots.includes('/sitemap.xml'));
 const sitemap=await(await handler.fetch(new Request('https://offmenu.test/sitemap.xml'),{})).text();assert(sitemap.includes('<loc>https://offmenu.test/</loc>'));assert(!sitemap.includes('api/'));
});
test('Sentry transport only accepts its fixed ingest hosts and constant redacted fields',async()=>{
 for(const value of [dsn.replace('o123.ingest.de.sentry.io','attacker.test'),dsn+'?private=1',dsn.replace('/456','/../../other'),dsn.replace('https:','http:')])assert.equal(sentryDestination(value),null);
 const event=diagnosticEvent('browser_error',{sourceCommit:'f'.repeat(40),email:'alice@example.test',url:'/api/state?token=private'});
 assert.equal(event.release,'f'.repeat(40));assert(!JSON.stringify(event).includes('alice'));assert(!JSON.stringify(event).includes('token'));assert.equal(event.request,undefined);assert.equal(event.user,undefined);
 let seen;assert.equal(await reportDiagnostic(configured,'worker_error',{},async(url,options)=>{seen={url,options};return new Response(null,{status:200});}),true);
 assert.equal(seen.url,'https://o123.ingest.de.sentry.io/api/456/envelope/');
 assert(!seen.options.body.includes('private-account-id'));assert(!seen.options.body.includes('stacktrace'));assert.equal(seen.options.redirect,'error');
 let calls=0;assert.equal(await reportDiagnostic({},'worker_error',{},async()=>{calls++;}),false);assert.equal(calls,0);
 assert.equal(routeGroup('/api/services/support/secret-id'),'services');assert.equal(routeGroup('/oauth/token?secret'),'identity');
});
test('diagnostics require explicit consent, auth, same-origin and exact enum payload',async()=>{
 const env={...configured,...storage()};
 assert.equal((await diagnosticRoutes(req({code:'browser_error',consent:true},'https://attacker.test'),env,deps)).status,403);
 assert.equal((await diagnosticRoutes(req({code:'browser_error',consent:true}),env,{...deps,verifiedUser:async()=>null})).status,401);
 for(const body of [{code:'browser_error'},{code:'worker_error',consent:true},{code:'browser_error',consent:true,stack:'private pantry'},null])assert.equal((await diagnosticRoutes(req(body),env,deps)).status,400);
 assert.equal((await diagnosticRoutes(req({code:'browser_error',consent:true}),{},deps)).status,503);
});
test('diagnostic authenticated rate limit denies before a provider call',async()=>{
 const env={...configured,...storage()},key=[...new Uint8Array(await crypto.subtle.digest('SHA-256',new TextEncoder().encode('diagnostics:private-account-id')))].map(x=>x.toString(16).padStart(2,'0')).join('');
 env.db.prepare('INSERT INTO integration_limits VALUES(?,?,?)').run(key,Math.floor(Date.now()/3600000),30);
 assert.equal((await diagnosticRoutes(req({code:'browser_error',consent:true}),env,deps)).status,429);
 assert.equal(env.db.prepare('SELECT count(*) AS count FROM integration_limits').get().count,1);
});
