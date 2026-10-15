import {validateState} from './state.mjs';
// Bounded async D1 backend; no routes, implicit migration, or remote provisioning.
export const SESSION_STATE_SCOPE='state:read-write';
export const SESSION_STATE_D1_DDL=[
`CREATE TABLE owner04_d1_sessions (id TEXT PRIMARY KEY, subject TEXT NOT NULL, secret_hash TEXT NOT NULL, realm TEXT NOT NULL, epoch INTEGER NOT NULL CHECK(typeof(epoch)='integer' AND epoch>0 AND epoch<=9007199254740991), scope TEXT NOT NULL, audience TEXT NOT NULL, expires_at INTEGER NOT NULL CHECK(typeof(expires_at)='integer'), revoked_at INTEGER, revoked_from_epoch INTEGER)`,
`CREATE TABLE owner04_d1_operations (session_id TEXT NOT NULL, subject TEXT NOT NULL, realm TEXT NOT NULL, epoch INTEGER NOT NULL, operation_id TEXT NOT NULL, digest TEXT NOT NULL, result_json TEXT NOT NULL CHECK(json_valid(result_json)), commit_token TEXT NOT NULL, PRIMARY KEY(session_id,realm,epoch,operation_id))`
];
export class StateProtocolError extends Error {
 constructor(code,status=403,outcome='not-admitted'){super(code);this.code=code;this.status=status;this.outcome=outcome;}
}
const deny=(code='SESSION_DENIED',status=403)=>{throw new StateProtocolError(code,status);};
const identifier=value=>typeof value==='string'&&/^[A-Za-z0-9_-]{16,128}$/.test(value);
const encode=bytes=>Array.from(bytes,b=>b.toString(16).padStart(2,'0')).join('');
const random=()=>encode(crypto.getRandomValues(new Uint8Array(32)));
const hash=async value=>encode(new Uint8Array(await crypto.subtle.digest('SHA-256',new TextEncoder().encode(value))));
function canonical(value,depth=0){
 if(depth>64)deny('INVALID_STATE',400);
 if(value===null||typeof value==='string'||typeof value==='boolean')return JSON.stringify(value);
 if(typeof value==='number'){if(!Number.isFinite(value))deny('INVALID_STATE',400);return JSON.stringify(value);}
 if(Array.isArray(value)){
  if(Reflect.ownKeys(value).length!==value.length+1)deny('INVALID_STATE',400);
  const parts=[];for(let i=0;i<value.length;i++){const d=Object.getOwnPropertyDescriptor(value,String(i));if(!d||!Object.hasOwn(d,'value'))deny('INVALID_STATE',400);parts.push(canonical(d.value,depth+1));}
  return '['+parts.join(',')+']';
 }
 if(value&&Object.getPrototypeOf(value)===Object.prototype){
  const keys=Reflect.ownKeys(value);if(keys.some(k=>typeof k!=='string'))deny('INVALID_STATE',400);
  return '{'+keys.sort().map(k=>{const d=Object.getOwnPropertyDescriptor(value,k);if(!d||!d.enumerable||!Object.hasOwn(d,'value'))deny('INVALID_STATE',400);return JSON.stringify(k)+':'+canonical(d.value,depth+1);}).join(',')+'}';
 }
 deny('INVALID_STATE',400);
}
function captureCommand(command,audience){
 if(!command||Object.getPrototypeOf(command)!==Object.prototype||Reflect.ownKeys(command).length!==3||Reflect.ownKeys(command).some(k=>!['operationId','expectedVersion','state'].includes(k)))deny('INVALID_OPERATION',400);
 const descriptors=Object.getOwnPropertyDescriptors(command);
 if(Object.values(descriptors).some(d=>!Object.hasOwn(d,'value')))deny('INVALID_OPERATION',400);
 const operationId=descriptors.operationId.value,expectedVersion=descriptors.expectedVersion.value;
 if(!identifier(operationId)||!Number.isSafeInteger(expectedVersion)||expectedVersion<0||expectedVersion>=Number.MAX_SAFE_INTEGER)deny('INVALID_OPERATION',400);
 const original=canonical(descriptors.state.value);
 if(new TextEncoder().encode(original).length>2000000)deny('STATE_TOO_LARGE',413);
 // Parse a private JSON tree before validation; no retained caller references.
 let state;try{state=validateState(JSON.parse(original));}catch{deny('INVALID_STATE',400);}
 const serialized=canonical(state);if(original!==serialized)deny('STATE_NORMALIZATION_REQUIRED',400);
 return Object.freeze({operationId,expectedVersion,serialized,digestInput:canonical({audience,method:'PUT',version:expectedVersion,state})});
}


/** Each action uses first-primary; every mutation/revocation is one D1 batch.
 * Trusted hooks have the same contract as reviewed 25543. No transaction callbacks.
 */
export function createD1SessionStateProtocol({database,authenticate,readSession,authorizeRequest,authorizeEnrollment,audience,realm,ttlMs}={}){
 if(!database||typeof database.withSession!=='function'||[authenticate,readSession,authorizeRequest,authorizeEnrollment].some(f=>typeof f!=='function'))throw Error('Native D1 and trusted server hooks required');
 const url=new URL(audience);
 if(url.protocol!=='https:'||url.username||url.password||url.pathname!=='/api/state'||url.search||url.hash||url.href!==audience)throw Error('Fixed canonical HTTPS state audience required');
 if(!identifier(realm)||!Number.isSafeInteger(ttlMs)||ttlMs<1||ttlMs>86400000)throw Error('Explicit realm and bounded server TTL required');
 const dbTime="(CAST(strftime('%s','now') AS INTEGER)*1000+CAST(substr(strftime('%f','now'),4,3) AS INTEGER))";
 const clock=()=>Date.now();
 const run=async work=>{try{return await work(database.withSession('first-primary'));}catch(e){if(e instanceof StateProtocolError)throw e;throw new StateProtocolError('STORAGE_UNAVAILABLE',503,'unknown');}};
 async function context(request,action){
  let user;
  try{user=await authenticate(request);}catch{deny('AUTH_UNAVAILABLE',503);}
  if(!user||typeof user.id!=='string'||!user.id.trim()||user.id.length>=200)deny('UNAUTHENTICATED',401);
  const ctx=Object.freeze({subject:user.id});
  let allowed;try{allowed=await authorizeRequest(request,action,Object.freeze({...user,id:ctx.subject}));}catch{deny('REQUEST_POLICY_UNAVAILABLE',503);}
  if(allowed!==true)deny('REQUEST_DENIED');
  return ctx;
 }
 function captureBinding(request){
  // Transport parsing must be synchronous, so no caller-owned credential survives
  // across authentication/policy/hash awaits. It must not perform issuer lookups.
  let b;try{b=readSession(request);}catch{deny('SESSION_UNAVAILABLE',503);}
  if(b&&typeof b.then==='function')deny('SESSION_UNAVAILABLE',503);
  if(!b||Object.getPrototypeOf(b)!==Object.prototype)deny();
  const fields={};for(const k of ['sessionId','capability','epoch','realm']){const d=Object.getOwnPropertyDescriptor(b,k);if(!d||!Object.hasOwn(d,'value'))deny();fields[k]=d.value;}
  const captured=Object.freeze(fields);
  if(!identifier(captured.sessionId)||!identifier(captured.capability)||!Number.isSafeInteger(captured.epoch)||captured.epoch<1||captured.epoch>=Number.MAX_SAFE_INTEGER||captured.realm!==realm)deny();
  return captured;
 }
 async function binding(captured){
  const secretHash=await hash(captured.capability);
  return Object.freeze({sessionId:captured.sessionId,epoch:captured.epoch,realm:captured.realm,secretHash});
 }

 const publicBinding=(ctx,b)=>({subject:ctx.subject,sessionId:b.sessionId,realm,epoch:b.epoch,resource:audience});
 const args=(ctx,b)=>[b.sessionId,ctx.subject,b.secretHash,realm,audience,SESSION_STATE_SCOPE,b.epoch];
 const identity='s.id=? AND s.subject=? AND s.secret_hash=? AND s.realm=? AND s.audience=? AND s.scope=?';
 const live=`${identity} AND s.epoch=? AND s.revoked_at IS NULL AND s.expires_at>${dbTime}`;
 const validVersion="(u.revision IS NULL OR (typeof(u.revision)='integer' AND u.revision>=1 AND u.revision<=9007199254740991))";
 const row0=result=>result.results[0];
 const admitted=row=>{if(!row)deny();return row;};
 const version=row=>{if(row.revision!==null&&(!Number.isSafeInteger(row.revision)||row.revision<1||row.revision>Number.MAX_SAFE_INTEGER))deny('INVALID_STORED_VERSION',503);return row.revision??0;};
 return {
  async enroll(request){
   const ctx=await context(request,'enroll');let allowed;
   try{allowed=await authorizeEnrollment(request,{id:ctx.subject});}catch{deny('ENROLLMENT_POLICY_UNAVAILABLE',503);}
   if(allowed!==true)deny('ENROLLMENT_DENIED');
   const capability=random(),id=random(),secretHash=await hash(capability),expiresAt=clock()+ttlMs;
   await run(db=>db.prepare('INSERT INTO owner04_d1_sessions(id,subject,secret_hash,realm,epoch,scope,audience,expires_at) VALUES(?,?,?,?,1,?,?,?)').bind(id,ctx.subject,secretHash,realm,SESSION_STATE_SCOPE,audience,expiresAt).run());
   return {sessionId:id,capability,realm,epoch:1,expiresAt,audience,scope:SESSION_STATE_SCOPE,binding:publicBinding(ctx,{sessionId:id,epoch:1})};
  },
  async read(request){
   const credential=captureBinding(request),ctx=await context(request,'read'),b=await binding(credential);
   return run(async db=>{
    const row=admitted(await db.prepare(`SELECT u.revision,u.state_json FROM owner04_d1_sessions s LEFT JOIN user_state u ON u.user_id=s.subject WHERE ${live}`).bind(...args(ctx,b)).first());
    return {revision:version(row),state:row.state_json===null?null:JSON.parse(row.state_json),binding:publicBinding(ctx,b)};
   });
  },
  async mutate(request,command){
   const c=captureCommand(command,audience),credential=captureBinding(request);
   const ctx=await context(request,'mutate'),b=await binding(credential),digest=await hash(c.digestInput),token=random();
   return run(async db=>{
    const bind=JSON.stringify(publicBinding(ctx,b));
    const committed="coalesce(u.revision,0)=?";
    const insert=db.prepare(`INSERT INTO owner04_d1_operations(session_id,subject,realm,epoch,operation_id,digest,result_json,commit_token)
     SELECT s.id,s.subject,s.realm,s.epoch,?,?,json_object('status',CASE WHEN ${committed} THEN 'committed' ELSE 'conflict' END,'acknowledged',json(CASE WHEN ${committed} THEN 'true' ELSE 'false' END),'binding',json(?),'operationId',?,'revision',CASE WHEN ${committed} THEN coalesce(u.revision,0)+1 ELSE coalesce(u.revision,0) END,'digest',?),?
     FROM owner04_d1_sessions s LEFT JOIN user_state u ON u.user_id=s.subject WHERE ${live} AND ${validVersion}
     ON CONFLICT(session_id,realm,epoch,operation_id) DO NOTHING`).bind(c.operationId,digest,c.expectedVersion,c.expectedVersion,bind,c.operationId,c.expectedVersion,digest,token,...args(ctx,b));
    const ledger="EXISTS(SELECT 1 FROM owner04_d1_operations o WHERE o.session_id=? AND o.subject=? AND o.realm=? AND o.epoch=? AND o.operation_id=? AND o.commit_token=? AND json_extract(o.result_json,'$.status')='committed')";
    const la=[b.sessionId,ctx.subject,realm,b.epoch,c.operationId,token];
    const timestamp=new Date(clock()).toISOString();
    const results=await db.batch([
     insert,
     db.prepare(`INSERT INTO user_state(user_id,revision,state_json,updated_at) SELECT ?,1,?,? WHERE ?=0 AND ${ledger} ON CONFLICT(user_id) DO NOTHING`).bind(ctx.subject,c.serialized,timestamp,c.expectedVersion,...la),
     db.prepare(`UPDATE user_state SET revision=revision+1,state_json=?,updated_at=? WHERE user_id=? AND revision=? AND ?>0 AND ${ledger}`).bind(c.serialized,timestamp,ctx.subject,c.expectedVersion,c.expectedVersion,...la),
     db.prepare(`UPDATE owner04_d1_operations SET result_json=NULL WHERE commit_token=? AND json_extract(result_json,'$.status')='committed' AND NOT EXISTS(SELECT 1 FROM user_state WHERE user_id=? AND revision=? AND state_json=?)`).bind(token,ctx.subject,c.expectedVersion+1,c.serialized),
     db.prepare(`SELECT u.revision,o.digest,o.result_json FROM owner04_d1_sessions s LEFT JOIN user_state u ON u.user_id=s.subject LEFT JOIN owner04_d1_operations o ON o.session_id=s.id AND o.subject=s.subject AND o.realm=s.realm AND o.epoch=s.epoch AND o.operation_id=? WHERE ${live}`).bind(c.operationId,...args(ctx,b))
    ]);
    const selected=row0(results[4]);
    if(!selected&&results[0].meta.changes===1)throw new StateProtocolError('STORAGE_UNAVAILABLE',503,'unknown');
    const row=admitted(selected);version(row);
    if(!row.result_json)throw new StateProtocolError('STORAGE_UNAVAILABLE',503,'unknown');
    if(row.digest!==digest)deny('OPERATION_ID_REUSED',409);
    return JSON.parse(row.result_json);
   });
  },
  async status(request,operationId){
   const credential=captureBinding(request);if(!identifier(operationId))deny('INVALID_OPERATION',400);
   const ctx=await context(request,'status'),b=await binding(credential);
   return run(async db=>{
    const row=admitted(await db.prepare(`SELECT o.result_json FROM owner04_d1_sessions s LEFT JOIN owner04_d1_operations o ON o.session_id=s.id AND o.subject=s.subject AND o.realm=s.realm AND o.epoch=s.epoch AND o.operation_id=? WHERE ${live}`).bind(operationId,...args(ctx,b)).first());
    return row.result_json?JSON.parse(row.result_json):{status:'unknown',acknowledged:false,operationId,binding:publicBinding(ctx,b)};
   });
  },
  async revoke(request){
   const credential=captureBinding(request),ctx=await context(request,'revoke'),b=await binding(credential);
   return run(async db=>{
    const result=await db.batch([
     db.prepare(`UPDATE owner04_d1_sessions AS s SET revoked_at=${dbTime},revoked_from_epoch=epoch,epoch=epoch+1 WHERE ${live}`).bind(...args(ctx,b)),
     db.prepare(`SELECT s.epoch FROM owner04_d1_sessions s WHERE ${identity} AND s.revoked_at IS NOT NULL AND s.revoked_from_epoch=?`).bind(...args(ctx,b))
    ]);
    const row=admitted(row0(result[1]));return {status:'revoked',sessionId:b.sessionId,epoch:row.epoch};
   });
  }
 };
}
