// Unmounted LOCAL route. The handler supplies its existing runtime verifier and
// trusted adapters; this module never creates an identity, key or attestation.
import {createOwnedBackupExporter} from './private-portability-owned-backup-v1.mjs';
import {canonical} from './private-portability-v1.mjs';
const PATH='/api/private-portability/owned-backup/export',MAX=8192;
const headers={'Cache-Control':'private, no-store','Vary':'Cookie, Authorization',
  'X-Content-Type-Options':'nosniff'};
const reply=(code,status)=>Response.json({error:code},{status,headers});
const fail=(code,status)=>{throw Object.assign(new Error(code),{routeCode:code,routeStatus:status});};
const atom=x=>typeof x==='string'&&x.length>0&&x.length<=200&&!/[\u0000-\u001f]/u.test(x);
async function metadata(request){
  if(request.headers.get('Content-Type')?.split(';')[0].trim().toLowerCase()!=='application/json')fail('JSON_REQUIRED',415);
  const reader=request.body?.getReader();if(!reader)fail('REQUEST_METADATA_REQUIRED',400);
  let size=0;const parts=[];
  try{for(;;){const {done,value}=await reader.read();if(done)break;size+=value.byteLength;
    if(size>MAX){await reader.cancel();fail('REQUEST_TOO_LARGE',413);}parts.push(value);}}
  finally{reader.releaseLock();}
  const bytes=new Uint8Array(size);let offset=0;for(const p of parts){bytes.set(p,offset);offset+=p.length;}
  let body;try{body=JSON.parse(new TextDecoder('utf-8',{fatal:true}).decode(bytes));}catch{fail('INVALID_JSON',400);}
  if(!body||typeof body!=='object'||Array.isArray(body)||
    Object.keys(body).some(k=>!['packageId','recoveryRef','keyReference'].includes(k))||
    !atom(body.packageId)||!atom(body.recoveryRef)||!body.keyReference||
    Object.keys(body.keyReference).sort().join(',')!=='keyRef,keyVersion'||
    !atom(body.keyReference.keyRef)||!Number.isSafeInteger(body.keyReference.keyVersion)||body.keyReference.keyVersion<1)
    fail('INVALID_EXPORT_METADATA',400);
  return body;
}

export function createOwnedBackupExportRoute({readAuthority,openSnapshot,
  authorizeSourceRecord,resolveKey,custody='server-envelope',clock}={}){
  return async function ownedBackupExportRoute(request,env,{runtime}={}){
    const url=new URL(request.url);if(url.pathname!==PATH)return null;
    if(request.method!=='POST')return reply('METHOD_NOT_ALLOWED',405);
    if(!['http://127.0.0.1:7645','http://127.0.0.1:17645'].includes(url.origin)||
      request.headers.get('Origin')!==url.origin)return reply('SAME_LOCAL_ORIGIN_REQUIRED',403);
    if(typeof runtime?.verifiedUser!=='function')return reply('EXISTING_VERIFIER_UNAVAILABLE',503);
    try{
      let user;try{user=await runtime.verifiedUser(request);}catch{fail('AUTH_SESSION_UNAVAILABLE',503);}
      if(!user||!atom(user.id))return reply('SIGN_IN_REQUIRED',401);
      if([readAuthority,openSnapshot,authorizeSourceRecord,resolveKey,clock].some(f=>typeof f!=='function'))
        return reply('TRUSTED_EXPORT_ADAPTERS_UNAVAILABLE',503);
      const body=await metadata(request),principal=Object.freeze({id:user.id});
      const context=Object.freeze({request,env,principal});let fence;
      const boundAuthority=async query=>{
        if(request.signal.aborted)fail('REQUEST_ABORTED',408);
        const fresh=await runtime.verifiedUser(request);
        if(!fresh||fresh.id!==principal.id)fail('VERIFIED_IDENTITY_CHANGED',403);
        const authority=await readAuthority(query,context);
        if(authority?.principal?.id!==principal.id||authority?.identity?.ownerUserId!==principal.id)
          fail('AUTHORITY_OWNER_MISMATCH',403);
        const stamp=canonical(authority);
        if(fence===undefined)fence=stamp;else if(stamp!==fence)fail('AUTHORITY_CHANGED',403);
        return JSON.parse(stamp);
      };
      // The existing adapter still independently verifies exact issuer/subject,
      // namespace, consent, record/deletion scope and retained payload attestation.
      await boundAuthority({operation:'owned-backup',phase:'http-start',packageId:body.packageId});
      const exporter=createOwnedBackupExporter({readAuthority:boundAuthority,
        openSnapshot:q=>openSnapshot(q,context),
        authorizeSourceRecord:q=>authorizeSourceRecord(q,context),
        resolveKey:q=>resolveKey(q,context),custody,clock});
      const sealed=await exporter.exportOwnedBackup(body);
      await boundAuthority({operation:'owned-backup',phase:'http-before-release',packageId:body.packageId});
      return Response.json(sealed,{status:200,headers:{...headers,
        'Content-Disposition':'attachment; filename="offmenu-owned-backup.json"'}});
    }catch(error){return reply(error.routeCode||'OWNED_BACKUP_EXPORT_UNAVAILABLE',error.routeStatus||503);}
  };
}
