import {validateState} from './state.mjs';

// Owner 04 isolated protocol. No routes, schema initialization or provider credentials.
// A caller must supply its actual fresh verifiedUser and reviewed CSRF/enrollment policies.
export const SESSION_STATE_SCOPE='state:read-write';
export const SESSION_STATE_DDL=[
 `CREATE TABLE owner04_state_sessions (
 id TEXT PRIMARY KEY, subject TEXT NOT NULL, secret_hash TEXT NOT NULL,
 realm TEXT NOT NULL, epoch INTEGER NOT NULL CHECK(epoch>0), scope TEXT NOT NULL,
 audience TEXT NOT NULL, expires_at INTEGER NOT NULL, revoked_at INTEGER,
 revoked_from_epoch INTEGER)`,
 `CREATE TABLE owner04_state_operations (
 session_id TEXT NOT NULL, subject TEXT NOT NULL, realm TEXT NOT NULL,
 epoch INTEGER NOT NULL, operation_id TEXT NOT NULL, digest TEXT NOT NULL,
 result_json TEXT NOT NULL, PRIMARY KEY(session_id,realm,epoch,operation_id))`
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

/** Actual synchronous SQLite adapter; D1 cannot be substituted for this interface.
 * Owner 02 must qualify an equivalent primary atomic transaction adapter before
 * Worker integration. Every transaction owns admission AND mutation/ledger/revoke.
 * No automatic DDL, missing-table fallback, caching, or initialization on request.
 */
export function createSqliteStateStore(database){
 return {transaction(work){
  let begun=false;
  try{
   database.exec('BEGIN IMMEDIATE');begun=true;
   const tx={
    session:id=>database.prepare('SELECT * FROM owner04_state_sessions WHERE id=?').get(id),
    issue:row=>database.prepare('INSERT INTO owner04_state_sessions(id,subject,secret_hash,realm,epoch,scope,audience,expires_at) VALUES(?,?,?,?,?,?,?,?)').run(row.id,row.subject,row.secret_hash,row.realm,row.epoch,row.scope,row.audience,row.expires_at),
    revoke:(id,at)=>database.prepare('UPDATE owner04_state_sessions SET revoked_at=?,revoked_from_epoch=epoch,epoch=epoch+1 WHERE id=? AND revoked_at IS NULL').run(at,id),
    state:subject=>database.prepare('SELECT revision,state_json,updated_at FROM user_state WHERE user_id=?').get(subject),
    write(subject,version,state,at){
     const result=version===0?
      database.prepare('INSERT INTO user_state(user_id,revision,state_json,updated_at) VALUES(?,1,?,?) ON CONFLICT(user_id) DO NOTHING').run(subject,state,at):
      database.prepare('UPDATE user_state SET revision=revision+1,state_json=?,updated_at=? WHERE user_id=? AND revision=?').run(state,at,subject,version);
     if(result.changes!==1)deny('VERSION_CONFLICT',409);
    },
    operation:(row,id)=>database.prepare('SELECT digest,result_json FROM owner04_state_operations WHERE session_id=? AND subject=? AND realm=? AND epoch=? AND operation_id=?').get(row.id,row.subject,row.realm,row.epoch,id),
    record:(row,id,digest,result)=>database.prepare('INSERT INTO owner04_state_operations(session_id,subject,realm,epoch,operation_id,digest,result_json) VALUES(?,?,?,?,?,?,?)').run(row.id,row.subject,row.realm,row.epoch,id,digest,JSON.stringify(result))
   };
   const result=work(tx);if(result&&typeof result.then==='function')throw Error('Transaction callback must be synchronous');
   database.exec('COMMIT');begun=false;return result;
  }catch(error){if(begun){try{database.exec('ROLLBACK');}catch{}}
   throw error;
  }
 }};
}

/** Transport-neutral API. readSession reads a reviewed protected cookie/transport,
 * not body authority; its untrusted values are always matched to persisted rows.
 * authorizeRequest must enforce method/resource/CSRF/exact configured Origin.
 * authorizeEnrollment is an explicit server policy; never auto-reissue on denial.
 */
export function createSessionStateProtocol({store,authenticate,readSession,authorizeRequest,authorizeEnrollment,audience,realm,ttlMs,now=Date.now}={}){
 if(!store||typeof store.transaction!=='function'||[authenticate,readSession,authorizeRequest,authorizeEnrollment,now].some(f=>typeof f!=='function'))throw Error('Trusted server hooks and transactional store required');
 const url=new URL(audience);
 if(url.protocol!=='https:'||url.username||url.password||url.pathname!=='/api/state'||url.search||url.hash||url.href!==audience)throw Error('Fixed canonical HTTPS state audience required');
 if(!identifier(realm)||!Number.isSafeInteger(ttlMs)||ttlMs<1||ttlMs>86400000)throw Error('Explicit realm and bounded server TTL required');
 const clock=()=>{const n=now();if(!Number.isSafeInteger(n)||n<0||n>8640000000000000-ttlMs)deny('CLOCK_UNAVAILABLE',503);return n;};
 const transaction=work=>{try{return store.transaction(work);}catch(error){if(error instanceof StateProtocolError)throw error;throw new StateProtocolError('STORAGE_UNAVAILABLE',503,'unknown');}};
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
 function admission(tx,ctx,b,{allowRevoked=false}={}){
  const row=tx.session(b.sessionId);
  if(!row||row.subject!==ctx.subject||row.secret_hash!==b.secretHash||row.realm!==realm||row.audience!==audience||row.scope!==SESSION_STATE_SCOPE)deny();
  if(!Number.isSafeInteger(row.epoch)||row.epoch<1||row.epoch>=Number.MAX_SAFE_INTEGER||!Number.isSafeInteger(row.expires_at)||row.expires_at<0)deny();
  if(allowRevoked&&row.revoked_at!==null&&row.revoked_from_epoch===b.epoch)return row;
  if(row.revoked_at!==null||row.epoch!==b.epoch||row.expires_at<=clock())deny();
  return row;
 }
 const publicBinding=row=>({subject:row.subject,sessionId:row.id,realm:row.realm,epoch:row.epoch,resource:row.audience});
 return {
  async enroll(request){
   const ctx=await context(request,'enroll');
   let allowed;try{allowed=await authorizeEnrollment(request,{id:ctx.subject});}catch{deny('ENROLLMENT_POLICY_UNAVAILABLE',503);}
   if(allowed!==true)deny('ENROLLMENT_DENIED');
   const capability=random(),row={id:random(),subject:ctx.subject,secret_hash:await hash(capability),realm,epoch:1,scope:SESSION_STATE_SCOPE,audience,expires_at:clock()+ttlMs};
   transaction(tx=>tx.issue(row));
   // Secret returned only to the server caller for protected transport; never log it.
   return {sessionId:row.id,capability,realm,epoch:row.epoch,expiresAt:row.expires_at,audience,scope:row.scope,binding:publicBinding(row)};
  },
  async read(request){
   const captured=captureBinding(request),ctx=await context(request,'read'),b=await binding(captured);
   return transaction(tx=>{const session=admission(tx,ctx,b),row=tx.state(ctx.subject);return {revision:row?.revision||0,state:row?JSON.parse(row.state_json):null,binding:publicBinding(session)};});
  },
  async mutate(request,command){
   // Capture and validate every caller-owned command field before the first await.
   const captured=captureCommand(command,audience),credential=captureBinding(request);
   const ctx=await context(request,'mutate'),b=await binding(credential);
   const digest=await hash(captured.digestInput);
   return transaction(tx=>{
    const row=admission(tx,ctx,b),prior=tx.operation(row,captured.operationId);
    if(prior){if(prior.digest!==digest)deny('OPERATION_ID_REUSED',409);return JSON.parse(prior.result_json);}
    const current=tx.state(ctx.subject),version=current?.revision||0;
    if(!Number.isSafeInteger(version)||version<0)deny('INVALID_STORED_VERSION',503);
    const result=version!==captured.expectedVersion?{status:'conflict',acknowledged:false,binding:publicBinding(row),operationId:captured.operationId,revision:version,digest}:
     {status:'committed',acknowledged:true,binding:publicBinding(row),operationId:captured.operationId,revision:version+1,digest};
    if(result.status==='committed')tx.write(ctx.subject,version,captured.serialized,new Date(clock()).toISOString());
    tx.record(row,captured.operationId,digest,result);return result;
   });
  },
  async status(request,operationId){
   const credential=captureBinding(request);if(!identifier(operationId))deny('INVALID_OPERATION',400);
   const ctx=await context(request,'status'),b=await binding(credential);
   return transaction(tx=>{const row=admission(tx,ctx,b),record=tx.operation(row,operationId);return record?JSON.parse(record.result_json):{status:'unknown',acknowledged:false,operationId,binding:publicBinding(row)};});
  },
  async revoke(request){
   const credential=captureBinding(request),ctx=await context(request,'revoke'),b=await binding(credential);
   return transaction(tx=>{const row=admission(tx,ctx,b,{allowRevoked:true});if(row.revoked_at===null)tx.revoke(row.id,clock());return {status:'revoked',sessionId:row.id,epoch:row.revoked_at===null?row.epoch+1:row.epoch};});
  }
 };
}
