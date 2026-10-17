import {sealCredentials} from './provider-data.mjs';
import {defaultGlobalSettings,parseGlobalSettings} from './global-settings.mjs';

const BREVO_URL='https://api.brevo.com/v3/smtp/email';
const encoder=new TextEncoder();
const replyFallback=(data,status=200)=>Response.json(data,{status,headers:{'Cache-Control':'no-store','X-Content-Type-Options':'nosniff'}});
const email=/^[^\s@]+@[^\s@]+\.[^\s@]+$/;
function runtimeSettings(env){try{const value=env.SERVICE_GLOBAL_SETTINGS||{};return parseGlobalSettings(typeof value==='string'?JSON.parse(value):value);}catch{return defaultGlobalSettings();}}

const hex=bytes=>[...new Uint8Array(bytes)].map(byte=>byte.toString(16).padStart(2,'0')).join('');
const validVault=value=>typeof value==='string'&&/^[a-f0-9]{64}$/.test(value);
const validEmail=value=>typeof value==='string'&&value.length<=254&&!/[\u0000-\u001F\u007F-\u009F]/.test(value)&&email.test(value);
async function requestHash(env,owner,kind,payload){if(!validVault(env.PROVIDER_VAULT_KEY))throw Error('Vault unavailable');const key=await crypto.subtle.importKey('raw',Uint8Array.from(env.PROVIDER_VAULT_KEY.match(/../g),pair=>parseInt(pair,16)),{name:'HMAC',hash:'SHA-256'},false,['sign']);const data=`offmenu/service-request/v1\0${owner}\0${kind}\0${JSON.stringify(payload)}`;return 'hmac-sha256:v1:'+hex(await crypto.subtle.sign('HMAC',key,encoder.encode(data)));}
function requestKey(value){return typeof value==='string'&&/^[A-Za-z0-9_-]{16,128}$/.test(value)?value:null;}
function text(value,max,{singleLine=false}={}){if(typeof value!=='string'||value.length>max||/[\u0000-\u0008\u000B\u000C\u000E-\u001F\u007F-\u009F]/.test(value)||(singleLine&&/[\r\n]/.test(value))||!value.trim())return null;return value;}
function confirmedAt(value){return typeof value==='string'&&value.length<=64&&/^\d{4}-\d{2}-\d{2}T/.test(value)&&Number.isFinite(Date.parse(value));}
function ownerEmail(user){const value=user?.email,confirmed=confirmedAt(user?.confirmed_at)||confirmedAt(user?.email_confirmed_at);return confirmed&&validEmail(value)?value:null;}
function display(row){return {id:row.id,kind:row.kind,status:row.status,createdAt:row.created_at,updatedAt:row.updated_at};}
async function rateLimit(env,owner,kind,limit){const bucket=Math.floor(Date.now()/3600000),row=await env.DB.prepare('INSERT INTO service_rate_limits(owner,kind,bucket,count) VALUES(?,?,?,1) ON CONFLICT(owner,kind,bucket) DO UPDATE SET count=count+1 RETURNING count').bind(owner,kind,bucket).first();if(row.count>limit)return false;return true;}
async function setStatus(env,id,status){await env.DB.prepare('UPDATE service_requests SET status=?,updated_at=? WHERE id=?').bind(status,new Date().toISOString(),id).run();}
export function serviceEmailConfigured(env){return typeof env.BREVO_API_KEY==='string'&&env.BREVO_API_KEY.length>10&&validEmail(env.BREVO_SENDER_EMAIL)&&typeof env.BREVO_SENDER_NAME==='string'&&!!text(env.BREVO_SENDER_NAME,120,{singleLine:true})&&validVault(env.PROVIDER_VAULT_KEY);}
async function deliver(env,{to,subject,textContent}){let response;try{response=await fetch(BREVO_URL,{method:'POST',headers:{'api-key':env.BREVO_API_KEY,'content-type':'application/json',accept:'application/json'},body:JSON.stringify({sender:{email:env.BREVO_SENDER_EMAIL,name:env.BREVO_SENDER_NAME},to:[{email:to}],subject,textContent}),redirect:'manual',signal:AbortSignal.timeout(15000)});if(response.ok)return 'sent';if(response.status>=400&&response.status<500)return 'failed';return 'unknown';}finally{await response?.body?.cancel();}}
function exactKeys(value,keys){return !!value&&typeof value==='object'&&!Array.isArray(value)&&Object.keys(value).every(key=>keys.includes(key));}
export async function cleanupServiceRequests(env,now=Date.now()){if(!env.DB)return;const bucket=Math.floor(now/3600000);await env.DB.prepare('UPDATE service_requests SET sealed=NULL,updated_at=? WHERE sealed IS NOT NULL AND retain_until<?').bind(new Date(now).toISOString(),now).run();await env.DB.prepare('DELETE FROM service_rate_limits WHERE bucket<?').bind(bucket-24).run();}

/* Handles only private support and deliberate email-to-self requests. */
export async function serviceSupportRoutes(request,env,{verifiedUser,boundedJSON,reply=replyFallback}){
 const url=new URL(request.url),path=url.pathname;
 if(path!=='/api/services/support'&&path!=='/api/services/email')return null;
 if(!env.DB)return reply({error:'Private service storage is unavailable.'},503);
 if((path==='/api/services/support'&&request.method!=='GET'&&request.method!=='POST')||(path==='/api/services/email'&&request.method!=='POST'))return reply({error:'Method not allowed'},405);
 if(request.method!=='GET'&&request.headers.get('Origin')!==url.origin)return reply({error:'Origin mismatch'},403);
 const user=await verifiedUser(request);if(!user?.id)return reply({error:'Sign in to use private support.'},401);
 if(path==='/api/services/support'&&request.method==='GET'){
  const rows=await env.DB.prepare('SELECT id,kind,status,created_at,updated_at FROM service_requests WHERE owner=? ORDER BY created_at DESC LIMIT 100').bind(user.id).all();
  return reply({requests:rows.results.map(display)});
 }
 let body;try{body=await boundedJSON(request,20_000);}catch(error){return reply({error:'Use a small JSON request.'},400);}
 if(!exactKeys(body,path.endsWith('/support')?['idempotencyKey','confirmed','subject','message']:['idempotencyKey','confirmed','document'])||body?.confirmed!==true)return reply({error:'Confirm a valid email request before it is sent.'},400);
 const kind=path.endsWith('/support')?'support':'email',key=requestKey(body.idempotencyKey);if(!key)return reply({error:'Use an idempotency key with 16–128 letters, numbers, underscores or hyphens.'},400);
 const settings=runtimeSettings(env);if(kind==='support'&&!settings.features.supportEmail)return reply({error:'Support email is not available.'},503);if(kind==='email'&&!settings.features.documentEmail)return reply({error:'Document email is not available.'},503);
 const to=kind==='support'?text(env.SUPPORT_EMAIL,254,{singleLine:true}):ownerEmail(user);
 if(!to||!validEmail(to))return reply({error:kind==='support'?'Support email is not configured.':'Your verified account has no deliverable email address.'},503);
 if(kind==='email'&&!exactKeys(body.document,['title','text']))return reply({error:'Select a titled plain-text document.'},400);
 const subject=kind==='support'?text(body.subject,160,{singleLine:true}):text(body.document?.title,160,{singleLine:true});
 const content=kind==='support'?text(body.message,10_000):text(body.document?.text,10_000);
 if(!subject||!content)return reply({error:kind==='support'?'Provide a subject and message.':'Select a titled plain-text document.'},400);
 const payload=kind==='support'?{subject,message:content,from:ownerEmail(user)}:{title:subject,text:content,to};
 let bodyHash;try{bodyHash=await requestHash(env,user.id,kind,payload);}catch{return reply({error:'Private request encryption is unavailable.'},503);}
 const existing=await env.DB.prepare('SELECT id,kind,body_hash,status,created_at,updated_at FROM service_requests WHERE owner=? AND kind=? AND idempotency_key=?').bind(user.id,kind,key).first();
 if(existing){if(existing.body_hash!==bodyHash)return reply({error:'This idempotency key was already used for a different request.'},409);if(existing.status==='pending'||existing.status==='unknown')return reply({error:'Delivery is uncertain and will not be resent automatically.',request:display(existing)},409);return reply({request:display(existing),replayed:true},existing.status==='sent'?200:409);}
 if(!await rateLimit(env,user.id,kind,kind==='support'?settings.limits.supportHourlyLimit:settings.limits.documentHourlyLimit))return reply({error:'Private service request limit reached. Try again next hour.'},429);
 if(!serviceEmailConfigured(env))return reply({error:'Email delivery is not configured.'},503);
 const id=crypto.randomUUID(),now=new Date().toISOString();let sealed;try{sealed=await sealCredentials(payload,env.PROVIDER_VAULT_KEY,user.id+'|service|'+id);}catch{return reply({error:'Private request encryption is unavailable.'},503);}
 try{await env.DB.prepare('INSERT INTO service_requests(id,owner,kind,idempotency_key,body_hash,status,sealed,created_at,updated_at,retain_until) VALUES(?,?,?,?,?,\'pending\',?,?,?,?)').bind(id,user.id,kind,key,bodyHash,sealed,now,now,Date.now()+settings.limits.supportRetentionDays*86400000).run();}catch(error){return reply({error:'Unable to create the private request.'},409);}
 try{const delivery=await deliver(env,{to,subject,textContent:kind==='support'?`Private support request from ${ownerEmail(user)||'an OffMenu account'}\n\n${content}`:content});if(delivery==='failed'){await setStatus(env,id,'failed');return reply({error:'Email provider rejected the request.',request:{id,status:'failed'}},502);}if(delivery==='unknown'){await setStatus(env,id,'unknown');return reply({error:'Email delivery is uncertain and will not be resent automatically.',request:{id,status:'unknown'}},502);}await setStatus(env,id,'sent');return reply({request:{id,status:'sent'}},201);}catch{try{await setStatus(env,id,'unknown');}catch{}return reply({error:'Email delivery is uncertain and will not be resent automatically.',request:{id,status:'unknown'}},502);}
}
