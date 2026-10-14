// Private persistence consumer only. Owner28 retains portable validation ownership.
export const REVIEWED_PREVIEW=Object.freeze({commit:'a108e1645ad5f19a5e0fe85e37e5c080f3582d8f',sha256:'94b84d2420d8c900d61eab0dab458c05d3b16942f15d860369854743e6fcdc4b'});
export class HealthImportRefusal extends Error {}
const deny=code=>{throw new HealthImportRefusal(code);};
const id=x=>typeof x==='string'&&/^[\w.:/-]{1,200}$/.test(x);
function capture(x,depth=0){
 if(depth>12)deny('COMMAND_DEPTH');
 if(x===null||typeof x==='string'||typeof x==='boolean')return x;
 if(typeof x==='number'&&Number.isFinite(x))return x;
 if(!x||typeof x!=='object'||(!Array.isArray(x)&&Object.getPrototypeOf(x)!==Object.prototype))deny('INVALID_COMMAND');
 const out=Array.isArray(x)?[]:{};
 for(const key of Reflect.ownKeys(x)){
  if(Array.isArray(x)&&key==='length')continue;
  const d=Object.getOwnPropertyDescriptor(x,key);
  if(typeof key!=='string'||!d.enumerable||!Object.hasOwn(d,'value')||['__proto__','constructor','prototype'].includes(key))deny('INVALID_COMMAND');
  if(Array.isArray(x)&&!/^(0|[1-9]\d*)$/.test(key))deny('INVALID_COMMAND');
  out[key]=capture(d.value,depth+1);
 }
 if(Array.isArray(x)&&Object.keys(out).length!==x.length)deny('INVALID_COMMAND');
 return out;
}
function canonical(x){return JSON.stringify(x&&typeof x==='object'?Array.isArray(x)?x.map(v=>JSON.parse(canonical(v))):Object.fromEntries(Object.keys(x).sort().map(k=>[k,JSON.parse(canonical(x[k]))])):x);}
export async function healthCommandDigest(command){return Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256',new TextEncoder().encode(canonical(command)))),b=>b.toString(16).padStart(2,'0')).join('');}
function keys(x,allowed){if(!x||Array.isArray(x)||Object.keys(x).some(k=>!allowed.includes(k)))deny('UNKNOWN_FIELD');}
function timestamp(x){if(typeof x!=='string'||!/^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d(?:\.\d{3})?Z$/.test(x)||!Number.isFinite(Date.parse(x))||new Date(Date.parse(x)).toISOString().replace('.000Z','Z')!==x.replace('.000Z','Z'))deny('INVALID_INTERVAL');return Date.parse(x);}
const overlaps=(a,b)=>a.type===b.type&&(a.start===a.end&&b.start===b.end?a.start===b.start:a.start===a.end?a.start>=b.start&&a.start<b.end:b.start===b.end?b.start>=a.start&&b.start<a.end:Math.max(a.start,b.start)<Math.min(a.end,b.end));
/** Trusted server binding (not packet fields):
 * preview is EXACT reviewed Owner28 validateHealthImport, sourceSha256 verified
 * by server loader. authenticate(request) gives current verified {id}.
 * transaction(owner, callback) serializes ALL account/member health writes and
 * invokes synchronous callback with {state,authorize,commit}. It MUST atomically
 * read current session/member/source consent policy and commit or roll back.
 * authorize supplies {sessionCurrent,sourceActive,context,devices,vendors,
 * confirmationDigest}; context matches28's owner/member/revision/now/consent.
 * commit({state,revoke?}) MUST atomically disable source/member permission on
 * withdrawal as well as write tombstones. No preview-only or separate writes.
 * Backend errors are unknown outcomes, never proof of rollback or success.
 */
export function createNativeHealthConsumer({preview,sourceSha256,authenticate,transaction}={}){
 if(typeof preview!=='function'||sourceSha256!==REVIEWED_PREVIEW.sha256||typeof authenticate!=='function'||typeof transaction!=='function')deny('REVIEWED_SERVER_BINDINGS_REQUIRED');
 async function run(request,input,withdraw){
  const command=capture(input);keys(command,withdraw?['operationId','memberId','sourceId','expectedRevision']:['operationId','memberId','sourceId','expectedRevision','upload','selectedIds','details']);
  if(!id(command.operationId)||!id(command.memberId)||!id(command.sourceId)||!Number.isSafeInteger(command.expectedRevision)||command.expectedRevision<0)deny('INVALID_ID_REVISION');
  if(new TextEncoder().encode(canonical(command)).length>131072)deny('COMMAND_TOO_LARGE');
  if(!withdraw&&(!Array.isArray(command.selectedIds)||command.selectedIds.length<1||command.selectedIds.length>100||new Set(command.selectedIds).size!==command.selectedIds.length||!command.selectedIds.every(id)||!Array.isArray(command.details)||command.details.length!==command.selectedIds.length))deny('EXACT_SELECTION_REQUIRED');
  const digest=await healthCommandDigest(command),user=await authenticate(request);
  if(!user||!id(user.id))deny('UNAUTHENTICATED');const owner=user.id;
  try{return await transaction(owner,tx=>{
   const state=capture(tx.state),policy=capture(tx.authorize({action:withdraw?'withdraw':'import',owner,memberId:command.memberId,sourceId:command.sourceId,commandDigest:digest})),ctx=policy.context;
   if(policy.sessionCurrent!==true||policy.sourceActive!==true||ctx?.owner!==owner||ctx?.memberId!==command.memberId||policy.confirmationDigest!==digest)deny('CURRENT_MEMBER_SOURCE_CONFIRMATION_REQUIRED');
   if(ctx.consent?.status!=='active'||ctx.consent.owner!==owner||ctx.consent.memberId!==command.memberId||!ctx.consent.sources?.includes(command.sourceId)||!ctx.consent.purposes?.includes('health-import')||timestamp(ctx.consent.expiresAt)<=ctx.now||!Number.isFinite(ctx.now))deny('CURRENT_CONSENT_REQUIRED');
   if(state.owner!==owner||!Number.isSafeInteger(state.revision)||state.revision<0||state.revision>=Number.MAX_SAFE_INTEGER||ctx.revision!==state.revision||!Array.isArray(state.records)||!Array.isArray(state.tombstones)||!Array.isArray(state.operations)||state.records.length>1000||state.operations.length>1000||state.tombstones.length>1000||state.records.some(r=>r.owner!==owner))deny('STATE_ACCOUNT_CONTRACT');
   for(const r of state.records)if(!id(r.memberId)||!id(r.source)||!id(r.sourceRecordId)||!Number.isSafeInteger(r.sourceRevision)||r.sourceRevision<0||typeof r.type!=='string'||!Number.isFinite(r.start)||!Number.isFinite(r.end)||r.end<r.start||timestamp(r.startAt)!==r.start||timestamp(r.endAt)!==r.end)deny('UNQUALIFIED_STORED_RECORD');
   for(const t of state.tombstones)if(t.owner!==owner||!id(t.memberId)||!id(t.source)||!id(t.sourceRecordId)||!Number.isSafeInteger(t.sourceRevision)||t.sourceRevision<0)deny('UNQUALIFIED_TOMBSTONE');
   const operationKey=canonical([command.memberId,command.operationId]),previous=state.operations.find(r=>r.key===operationKey);
   if(previous){if(previous.digest!==digest)deny('OPERATION_REPLAY_CONFLICT');return {...previous.result,replayed:true};}
   if(state.revision!==command.expectedRevision)deny('STALE_ACCOUNT_REVISION');
   if(withdraw){
    const removed=state.records.filter(r=>r.memberId===command.memberId&&r.source===command.sourceId);
    for(const r of removed)state.tombstones.push({owner,memberId:r.memberId,source:r.source,sourceRecordId:r.sourceRecordId,type:r.type,sourceRevision:r.sourceRevision});
    state.records=state.records.filter(r=>!removed.includes(r));
   }else{
    const result=preview(command.upload,ctx);
    if(!['preview','needs-review'].includes(result.status)||result.writes!==false||result.visibility!=='private'||!Array.isArray(result.records))deny('OWNER28_PREVIEW_REFUSED');
    if(result.records.some(r=>r.owner!==owner||r.memberId!==command.memberId||r.source!==command.sourceId))deny('PREVIEW_BINDING_MISMATCH');
    const selected=command.selectedIds.map(recordId=>result.records.find(r=>r.id===recordId));if(selected.some(r=>!r))deny('SELECTION_NOT_IN_PREVIEW');
    if(!Array.isArray(policy.devices)||!Array.isArray(policy.vendors))deny('SOURCE_ORIGIN_POLICY_REQUIRED');
    for(const row of selected){
     const matching=command.details.filter(d=>d.recordId===row.id);if(matching.length!==1)deny('EXACT_DETAIL_REQUIRED');const d=matching[0];keys(d,['recordId','sourceRecordId','sourceRevision','originDevice','vendor','startAt','endAt','timeZone','valueLexeme']);
     if(d.sourceRecordId!==row.sourceRecordId||!Number.isSafeInteger(d.sourceRevision)||d.sourceRevision<0||!policy.devices.includes(d.originDevice)||!policy.vendors.includes(d.vendor)||d.startAt!==row.observedAt)deny('SOURCE_REVISION_ORIGIN_REQUIRED');
     if(typeof d.timeZone!=='string'||d.timeZone.length>100)deny('TIMEZONE_REQUIRED');try{new Intl.DateTimeFormat('en',{timeZone:d.timeZone});}catch{deny('TIMEZONE_REQUIRED');}
     if(typeof d.valueLexeme!=='string'||d.valueLexeme.length>100||!/^(?:\d+(?:\.\d*)?|\.\d+)$/.test(d.valueLexeme)||Number(d.valueLexeme)!==row.value)deny('LEXEME_VALUE_MISMATCH');
     const start=timestamp(d.startAt),end=timestamp(d.endAt);if(end<start||end>ctx.now)deny('INVALID_INTERVAL');
     const candidate={...row,sourceRevision:d.sourceRevision,originDevice:d.originDevice,vendor:d.vendor,startAt:d.startAt,endAt:d.endAt,timeZone:d.timeZone,valueLexeme:d.valueLexeme,start,end};
     if(state.tombstones.some(t=>t.memberId===row.memberId&&t.source===row.source&&t.sourceRecordId===row.sourceRecordId&&t.type===row.type))deny('WITHDRAWN_RECORD');
     const index=state.records.findIndex(r=>r.memberId===row.memberId&&r.source===row.source&&r.sourceRecordId===row.sourceRecordId&&r.type===row.type),old=state.records[index];
     if(old&&candidate.sourceRevision<old.sourceRevision)deny('STALE_SOURCE_REVISION');
     if(old&&candidate.sourceRevision===old.sourceRevision){if(canonical(old)!==canonical(candidate))deny('SOURCE_REVISION_CONTENT_CONFLICT');continue;}
     if(state.records.some((r,i)=>i!==index&&r.memberId===row.memberId&&overlaps(r,candidate)))deny('MEASURED_OVERLAP_REFUSED');
     if(index<0)state.records.push(candidate);else state.records[index]=candidate;
    }
   }
   if(state.records.length>1000||state.tombstones.length>1000||state.operations.length>=1000)deny('ACCOUNT_STORAGE_LIMIT');
   state.revision++;const result={status:'committed',revision:state.revision,visibility:'private'};
   state.operations.push({key:operationKey,digest,result});
   tx.commit({state,revoke:withdraw?{owner,memberId:command.memberId,sourceId:command.sourceId}:null});return result;
  });}catch(error){if(error instanceof HealthImportRefusal)throw error;return {status:'unknown',operationId:command.operationId};}
 }
 return Object.freeze({import:(request,command)=>run(request,command,false),withdraw:(request,command)=>run(request,command,true),publicProjection:()=>({records:[]})});
}
