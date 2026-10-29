import { isAdministrator } from './admin-settings.mjs';

const replyFallback=(data,status=200)=>Response.json(data,{status,headers:{'Cache-Control':'no-store','X-Content-Type-Options':'nosniff'}});
const id=value=>typeof value==='string'&&/^[A-Za-z0-9_-]{16,128}$/.test(value);
const updateId=value=>typeof value==='string'&&/^[0-9a-f-]{36}$/i.test(value);
const notificationId=value=>updateId(value)||(typeof value==='string'&&/^update:[A-Za-z0-9_-]{1,128}:[0-9a-f-]{36}$/i.test(value));
const text=(value,max)=>typeof value==='string'&&value.length>0&&value.length<=max&&!/[\u0000-\u001F\u007F-\u009F]/.test(value)?value:null;
const date=value=>typeof value==='string'&&value.length<=40&&Number.isFinite(Date.parse(value))?new Date(value).toISOString():null;
const object=(value,keys)=>!!value&&typeof value==='object'&&!Array.isArray(value)&&Object.keys(value).every(key=>keys.includes(key));
const defaults={caseNotifications:true,communityNotifications:true,updateNotifications:true,emailUpdates:false};
const feature={case:'caseNotifications',community:'communityNotifications',update:'updateNotifications'};
const attribution=value=>{if(!value)return {kind:'human'};if(!object(value,['kind','agentName'])||!['human','ai'].includes(value.kind)||(value.kind==='human'&&value.agentName!==undefined)||(value.kind==='ai'&&!text(value.agentName,100)))return null;return value.kind==='ai'?{kind:'ai',agentName:value.agentName}:{kind:'human'};};
const display=row=>({id:row.id,title:row.title,text:row.text,locale:row.locale,publishAt:row.publish_at,releaseRef:row.release_ref||null,attribution:JSON.parse(row.attribution_json||'{"kind":"human"}'),state:row.state,revision:row.revision,createdAt:row.created_at,updatedAt:row.updated_at});
function localeFor(request){const value=new URL(request.url).searchParams.get('locale');return value==='ar'?'ar':'en';}
function preferences(row){return row?{caseNotifications:row.case_notifications===1,communityNotifications:row.community_notifications===1,updateNotifications:row.update_notifications===1,emailUpdates:row.email_updates===1}:structuredClone(defaults);}
async function preferenceRow(env,owner){return env.DB.prepare('SELECT * FROM care_preferences WHERE owner=?').bind(owner).first();}

export async function notifyCare(env,owner,kind,resourceId){
 if(!env.DB||!feature[kind]||!id(owner)||!text(resourceId,200))return false;
 const row=await preferenceRow(env,owner);if(!preferences(row)[feature[kind]])return false;
 const now=new Date().toISOString();
 await env.DB.prepare("INSERT INTO care_notifications(id,owner,kind,resource_id,created_at,seen_at) VALUES(?,?,?,?,?,NULL) ON CONFLICT(owner,kind,resource_id) DO UPDATE SET seen_at=CASE WHEN excluded.kind IN ('case','community') THEN NULL ELSE care_notifications.seen_at END").bind(crypto.randomUUID(),owner,kind,resourceId,now).run();
 return true;
}
async function seedUpdates(env,owner){
 const row=await preferenceRow(env,owner);if(!preferences(row).updateNotifications)return;
 const now=new Date().toISOString();
 await env.DB.prepare("INSERT INTO care_notifications(id,owner,kind,resource_id,created_at,seen_at) SELECT 'update:'||?||':'||id,?,'update',id,?,NULL FROM (SELECT id FROM care_updates WHERE state='published' AND publish_at<=? ORDER BY publish_at DESC LIMIT 50) WHERE 1 ON CONFLICT(owner,kind,resource_id) DO NOTHING").bind(owner,owner,now,now).run();
 await env.DB.prepare('DELETE FROM care_notifications WHERE owner=? AND id NOT IN (SELECT id FROM care_notifications WHERE owner=? ORDER BY created_at DESC LIMIT 50)').bind(owner,owner).run();
}
export async function cleanupCareUpdates(env,now=Date.now()){
 if(!env.DB)return;
 await env.DB.prepare('DELETE FROM care_update_locks WHERE created_at<?').bind(new Date(now-86400000).toISOString()).run();
}
function strictUpdate(body,{create=false}={}){
 const keys=create?['idempotencyKey','confirmed','title','text','locale','publishAt','releaseRef','attribution']:['revision','confirmed','action','title','text','locale','publishAt','releaseRef','attribution'];
 if(!object(body,keys)||body.confirmed!==true)return null;
 if(create&&!id(body.idempotencyKey))return null;
 if(!create&&(!Number.isSafeInteger(body.revision)||body.revision<1||!['publish','withdraw','edit'].includes(body.action)))return null;
 for(const key of ['title','text','locale','publishAt','releaseRef'])if(!create&&body[key]===undefined)continue;else if(key==='title'&&!text(body.title,200)||key==='text'&&!text(body.text,10000)||key==='locale'&&!['en','ar'].includes(body.locale)||key==='publishAt'&&!date(body.publishAt)||key==='releaseRef'&&body.releaseRef!==undefined&&body.releaseRef!==null&&!text(body.releaseRef,500))return null;
 if(body.attribution!==undefined&&!attribution(body.attribution))return null;if(create&&(!body.title||!body.text||!body.locale||!body.publishAt))return null;
 return body;
}
async function admin(request,env,user,boundedJSON,reply){
 const url=new URL(request.url),path=url.pathname;
 if(path==='/api/admin/care/updates'&&request.method==='GET'){
  const rows=(await env.DB.prepare('SELECT * FROM care_updates ORDER BY updated_at DESC LIMIT 100').all()).results||[];return reply({updates:rows.map(display)});
 }
 if(path==='/api/admin/care/updates'&&request.method==='POST'){
  let body;try{body=strictUpdate(await boundedJSON(request,20000),{create:true});if(!body)throw Error();}catch{return reply({error:'Invalid care update.'},400);}
  const now=new Date().toISOString(),update={id:crypto.randomUUID(),title:body.title,text:body.text,locale:body.locale,publishAt:date(body.publishAt),releaseRef:body.releaseRef||null,attribution:attribution(body.attribution)||{kind:'human'}},payload=JSON.stringify({title:update.title,text:update.text,locale:update.locale,publishAt:update.publishAt,releaseRef:update.releaseRef,attribution:update.attribution}),hash=await crypto.subtle.digest('SHA-256',new TextEncoder().encode(payload)),payloadHash=[...new Uint8Array(hash)].map(x=>x.toString(16).padStart(2,'0')).join('');
  const old=await env.DB.prepare('SELECT * FROM care_updates WHERE idempotency_key=?').bind(body.idempotencyKey).first();if(old)return old.payload_hash===payloadHash?reply({update:display(old),replayed:true}):reply({error:'Idempotency key already used for a different update.'},409);
  try{await env.DB.batch([env.DB.prepare("INSERT INTO care_updates(id,idempotency_key,payload_hash,title,text,locale,state,publish_at,release_ref,attribution_json,revision,write_id,created_at,updated_at) VALUES(?,?,?,?,?,?,'draft',?,?,?,1,?,?,?)").bind(update.id,body.idempotencyKey,payloadHash,update.title,update.text,update.locale,update.publishAt,update.releaseRef,JSON.stringify(update.attribution),crypto.randomUUID(),now,now),env.DB.prepare('INSERT INTO care_update_audit(id,update_id,actor_id,revision,action,paths_json,created_at) VALUES(?,?,?,?,?,?,?)').bind(crypto.randomUUID(),update.id,user.id,1,'create',JSON.stringify(['title','text','locale','publishAt','releaseRef','attribution']),now)]);}catch{return reply({error:'Care update creation failed.'},503);}
  return reply({update:{...update,state:'draft',revision:1,createdAt:now,updatedAt:now}},201);
 }
 const match=path.match(/^\/api\/admin\/care\/updates\/([0-9a-f-]{36})$/i);if(!match)return reply({error:'Not found'},404);if(request.method!=='PUT')return reply({error:'Method not allowed'},405);
 let body;try{body=strictUpdate(await boundedJSON(request,20000));if(!body)throw Error();}catch{return reply({error:'Invalid care update.'},400);}
 const row=await env.DB.prepare('SELECT * FROM care_updates WHERE id=?').bind(match[1]).first();if(!row)return reply({error:'Care update not found.'},404);if(row.revision!==body.revision)return reply({error:'A newer care update revision exists.'},409);
 const next={title:body.title===undefined?row.title:body.title,text:body.text===undefined?row.text:body.text,locale:body.locale===undefined?row.locale:body.locale,publishAt:body.publishAt===undefined?row.publish_at:date(body.publishAt),releaseRef:body.releaseRef===undefined?row.release_ref:body.releaseRef,attribution:body.attribution===undefined?JSON.parse(row.attribution_json||'{"kind":"human"}'):attribution(body.attribution),state:body.action==='publish'?'published':body.action==='withdraw'?'withdrawn':row.state};
 const now=new Date().toISOString(),nonce=crypto.randomUUID(),writeId=crypto.randomUUID(),paths=['title','text','locale','publishAt','releaseRef','attribution'].filter(key=>body[key]!==undefined);if(body.action!=='edit')paths.push('state');
 const lock=env.DB.prepare('INSERT INTO care_update_locks(update_id,nonce,created_at) VALUES(?,?,?) ON CONFLICT(update_id) DO NOTHING RETURNING update_id').bind(row.id,nonce,now);
 const write=env.DB.prepare('UPDATE care_updates SET title=?,text=?,locale=?,state=?,publish_at=?,release_ref=?,attribution_json=?,revision=revision+1,write_id=?,updated_at=? WHERE id=? AND revision=? AND EXISTS(SELECT 1 FROM care_update_locks WHERE update_id=? AND nonce=?) RETURNING revision').bind(next.title,next.text,next.locale,next.state,next.publishAt,next.releaseRef,JSON.stringify(next.attribution),writeId,now,row.id,body.revision,row.id,nonce);
 const audit=env.DB.prepare('INSERT INTO care_update_audit(id,update_id,actor_id,revision,action,paths_json,created_at) SELECT ?,?,?,?,?,?,? WHERE EXISTS(SELECT 1 FROM care_update_locks WHERE update_id=? AND nonce=?) AND EXISTS(SELECT 1 FROM care_updates WHERE id=? AND revision=? AND write_id=?)').bind(crypto.randomUUID(),row.id,user.id,body.revision+1,body.action,JSON.stringify(paths),now,row.id,nonce,row.id,body.revision+1,writeId);
 const release=env.DB.prepare('DELETE FROM care_update_locks WHERE update_id=? AND nonce=?').bind(row.id,nonce);
 try{const result=await env.DB.batch([lock,write,audit,release]);if(!result[0]?.results?.length||!result[1]?.results?.length)return reply({error:'A newer care update revision exists.'},409);}catch{return reply({error:'Care update change failed.'},503);}
 return reply({revision:body.revision+1,state:next.state});
}
export async function careUpdateRoutes(request,env,{verifiedUser,boundedJSON,reply=replyFallback}){
 const url=new URL(request.url),path=url.pathname,adminPath=path==='/api/admin/care/updates'||/^\/api\/admin\/care\/updates\/[0-9a-f-]{36}$/i.test(path),carePath=['/api/care/updates','/api/care/preferences','/api/care/notifications','/api/care/notifications/mark-seen'].includes(path);
 if(!adminPath&&!carePath)return null;if(!env.DB)return reply({error:'Care storage unavailable.'},503);
 if(request.method!=='GET'&&request.method!=='POST'&&request.method!=='PUT')return reply({error:'Method not allowed'},405);
 if(request.method!=='GET'&&request.headers.get('Origin')!==url.origin)return reply({error:'Origin mismatch'},403);
 if(adminPath){const user=await verifiedUser(request);if(!user?.id)return reply({error:'Sign in required.'},401);if(!isAdministrator(user))return reply({error:'Administrator permission required.'},403);return admin(request,env,user,boundedJSON,reply);}
 if(path==='/api/care/updates'&&request.method==='GET'){const locale=localeFor(request),rows=(await env.DB.prepare("SELECT * FROM care_updates WHERE state='published' AND publish_at<=? AND locale=? ORDER BY publish_at DESC LIMIT 50").bind(new Date().toISOString(),locale).all()).results||[];return reply({locale,updates:rows.map(display)});}
 const user=await verifiedUser(request);if(!user?.id)return reply({error:'Sign in required.'},401);
 if(path==='/api/care/preferences'){
  const row=await preferenceRow(env,user.id);if(request.method==='GET')return reply({revision:row?.revision||0,preferences:preferences(row)});
  if(request.method!=='PUT')return reply({error:'Method not allowed'},405);let body;try{body=await boundedJSON(request,2000);if(!object(body,[...Object.keys(defaults),'revision'])||!Number.isSafeInteger(body.revision)||body.revision<0||Object.keys(defaults).some(key=>typeof body[key]!=='boolean'))throw Error();}catch{return reply({error:'Invalid care preferences.'},400);}
  const now=new Date().toISOString(),saved=body.revision===0?await env.DB.prepare('INSERT INTO care_preferences(owner,case_notifications,community_notifications,update_notifications,email_updates,revision,updated_at) VALUES(?,?,?,?,?,1,?) ON CONFLICT(owner) DO NOTHING RETURNING revision').bind(user.id,body.caseNotifications?1:0,body.communityNotifications?1:0,body.updateNotifications?1:0,body.emailUpdates?1:0,now).first():await env.DB.prepare('UPDATE care_preferences SET case_notifications=?,community_notifications=?,update_notifications=?,email_updates=?,revision=revision+1,updated_at=? WHERE owner=? AND revision=? RETURNING revision').bind(body.caseNotifications?1:0,body.communityNotifications?1:0,body.updateNotifications?1:0,body.emailUpdates?1:0,now,user.id,body.revision).first();if(!saved)return reply({error:'A newer care preference revision exists.'},409);return reply({revision:saved.revision,preferences:{caseNotifications:body.caseNotifications,communityNotifications:body.communityNotifications,updateNotifications:body.updateNotifications,emailUpdates:body.emailUpdates}});
 }
 if(path==='/api/care/notifications'||path==='/api/care/notifications/mark-seen'){
  if(request.method==='GET'){await seedUpdates(env,user.id);const rows=(await env.DB.prepare('SELECT id,kind,resource_id,created_at,seen_at FROM care_notifications WHERE owner=? ORDER BY created_at DESC LIMIT 50').bind(user.id).all()).results||[];return reply({notifications:rows.map(row=>({id:row.id,kind:row.kind,resourceId:row.resource_id,createdAt:row.created_at,seenAt:row.seen_at||null}))});}
  if(path!=='/api/care/notifications/mark-seen'||request.method!=='PUT')return reply({error:'Method not allowed'},405);let body;try{body=await boundedJSON(request,5000);if(!object(body,['ids'])||!Array.isArray(body.ids)||body.ids.length>50||!body.ids.every(notificationId))throw Error();}catch{return reply({error:'Invalid notification update.'},400);}
  for(const value of new Set(body.ids))await env.DB.prepare('UPDATE care_notifications SET seen_at=? WHERE id=? AND owner=?').bind(new Date().toISOString(),value,user.id).run();return reply({seen:body.ids.length});
 }
 return reply({error:'Not found'},404);
}
