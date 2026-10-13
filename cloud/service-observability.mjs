import {serviceConfiguration,sentryDestination} from './service-config.mjs';
import {DIAGNOSTIC_CODES as CLIENT_DIAGNOSTIC_CODES} from '../public/services-model.js';
export const DIAGNOSTIC_CODES = Object.freeze([...CLIENT_DIAGNOSTIC_CODES,'worker_error']);
export function diagnosticEvent(code, release = {}) {
  if (!DIAGNOSTIC_CODES.includes(code)) throw Error('Invalid diagnostic code.');
  return {
    event_id:crypto.randomUUID().replaceAll('-',''),timestamp:Date.now()/1000,platform:'javascript',level:'error',
    logger:'offmenu',message:'OffMenu runtime failure',fingerprint:['offmenu',code],
    tags:{code,component:code==='worker_error'?'worker':'browser'},
    ...(typeof release.sourceCommit==='string' && /^[a-f0-9]{40}$/.test(release.sourceCommit)?{release:release.sourceCommit}:{})
  };
}
export async function reportDiagnostic(env, code, release = {}, fetcher = fetch) {
  if (!serviceConfiguration(env).client.diagnostics.enabled) return false;
  const destination = sentryDestination(env.SENTRY_DSN), event = diagnosticEvent(code,release);
  const payload = JSON.stringify(event);
  const envelope = JSON.stringify({event_id:event.event_id,sent_at:new Date().toISOString()})+'\n'+JSON.stringify({type:'event',length:new TextEncoder().encode(payload).length})+'\n'+payload+'\n';
  try {
    const result = await fetcher(destination.url,{method:'POST',headers:{'Content-Type':'application/x-sentry-envelope','X-Sentry-Auth':'Sentry sentry_version=7,sentry_client=offmenu/1.0,sentry_key='+destination.key},body:envelope,signal:AbortSignal.timeout(5000),redirect:'error'});
    await result.body?.cancel();
    return result.ok;
  } catch { return false; }
}
export async function diagnosticRoutes(request, env, {reply,verifiedUser,boundedJSON,release = {}}) {
  if (new URL(request.url).pathname !== '/api/services/diagnostics') return null;
  if (request.method !== 'POST') return reply({error:'Method not allowed'},405);
  if (request.headers.get('Origin') !== new URL(request.url).origin) return reply({error:'Origin mismatch'},403);
  if (!serviceConfiguration(env).client.diagnostics.enabled) return reply({error:'Error reporting is not configured.'},503);
  const user = await verifiedUser(request);
  if (!user) return reply({error:'Sign in to send an error report.'},401);
  let body;
  try {
    body = await boundedJSON(request,1000);
    if (!body || body.consent !== true || !CLIENT_DIAGNOSTIC_CODES.includes(body.code) || Object.keys(body).some(key=>!['code','consent'].includes(key))) throw Error('Invalid error report.');
  } catch { return reply({error:'Invalid error report.'},400); }
  if (!env.DB) return reply({error:'Error reporting is unavailable.'},503);
  const bytes = await crypto.subtle.digest('SHA-256',new TextEncoder().encode('diagnostics:'+user.id));
  const key = [...new Uint8Array(bytes)].map(value=>value.toString(16).padStart(2,'0')).join('');
  const bucket=Math.floor(Date.now()/3600000);
  const count=await env.DB.prepare('INSERT INTO integration_limits(key,bucket,count) VALUES(?,?,1) ON CONFLICT(key,bucket) DO UPDATE SET count=count+1 RETURNING count').bind(key,bucket).first();
  if (count.count > 30) return reply({error:'Error reporting limit reached.'},429);
  const sent = await reportDiagnostic(env,body.code,release);
  return reply({accepted:sent},sent?202:502);
}
export function routeGroup(path) {
  if (path.startsWith('/api/services')) return 'services';
  if (path.startsWith('/api/')) return 'api';
  if (path.startsWith('/oauth/') || path.startsWith('/.netlify/identity/')) return 'identity';
  return 'public';
}
