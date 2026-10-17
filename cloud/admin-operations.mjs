import {isAdministrator} from './admin-settings.mjs';

const replyFallback=(data,status=200)=>Response.json(data,{status,headers:{'Cache-Control':'no-store','X-Content-Type-Options':'nosniff'}});
const sourceId=value=>typeof value==='string'&&/^[a-z0-9][a-z0-9_-]{0,63}$/.test(value);
const text=(value,max)=>typeof value==='string'&&value.length>0&&value.length<=max&&!/[\u0000-\u001F\u007F-\u009F]/.test(value);
const stringList=(value,allowed,max=30)=>Array.isArray(value)&&value.length<=max&&value.every(item=>typeof item==='string'&&allowed.has(item));
const publicPolicy=(id,value)=>{
 if(!value||typeof value!=='object'||Array.isArray(value)||value.id!==id||!sourceId(id))return null;
 const allowed=['id','version','license','actions','audiences','countries','evidenceUrl','expiresAt','personalFields','promotion'];
 if(Object.keys(value).some(key=>!allowed.includes(key)))return null;
 if(!text(value.version,80)||!text(value.license,200)||!stringList(value.actions,new Set(['display','persist','export']))||!value.actions.length||!stringList(value.audiences,new Set(['public']))||!value.audiences.includes('public')||!Array.isArray(value.countries)||value.countries.length>300||!value.countries.every(country=>typeof country==='string'&&/^[A-Z]{2}$/.test(country))||!text(value.evidenceUrl,500)||!/^https:\/\//.test(value.evidenceUrl)||!(value.expiresAt===null||typeof value.expiresAt==='string'&&value.expiresAt.length<=80&&Number.isFinite(Date.parse(value.expiresAt)))||!text(value.personalFields,300)||!text(value.promotion,200))return null;
 // Policies remain publication-safe only when their reviewed document expressly
 // keeps user-contributed records out of the public source.
 if(value.promotion!=='user-contributed promotion disabled')return null;
 return {id,value:{id:value.id,version:value.version,license:value.license,actions:[...value.actions],audiences:['public'],countries:[...value.countries],evidenceUrl:value.evidenceUrl,expiresAt:value.expiresAt,personalFields:value.personalFields,promotion:value.promotion}};
};
const parseBody=value=>!!value&&typeof value==='object'&&!Array.isArray(value)&&Object.keys(value).every(key=>['revision','active','confirmed'].includes(key))&&Number.isSafeInteger(value.revision)&&value.revision>=0&&typeof value.active==='boolean'&&value.confirmed===true;

export async function adminOperationsRoutes(request,env,{verifiedUser,boundedJSON,reply=replyFallback}){
 const url=new URL(request.url),path=url.pathname;
 if(path!=='/api/admin/sources'&&!path.startsWith('/api/admin/sources/'))return null;
 if(!env.DB)return reply({error:'Administrative storage unavailable.'},503);
 const user=await verifiedUser(request);
 if(!user?.id)return reply({error:'Sign in required.'},401);
 if(!isAdministrator(user))return reply({error:'Administrator permission required.'},403);
 if(path==='/api/admin/sources'){
  if(request.method!=='GET')return reply({error:'Method not allowed'},405);
  try{
   const [rows,audits]=await Promise.all([
    env.DB.prepare('SELECT id,document,revision,active FROM source_policies ORDER BY id').all(),
    env.DB.prepare('SELECT actor_id,source_id,revision,action,created_at FROM admin_operations_audit ORDER BY created_at DESC LIMIT 50').all()
   ]);
   const sources=[];
   for(const row of rows.results||[]){let policy;try{policy=publicPolicy(row.id,JSON.parse(row.document));}catch{policy=null;}if(policy)sources.push({id:row.id,document:policy.value,revision:row.revision,active:row.active===1});}
   return reply({sources,audit:(audits.results||[]).map(row=>({actor:row.actor_id,sourceId:row.source_id,revision:row.revision,action:row.action,at:row.created_at}))});
  }catch{return reply({error:'Public source policies unavailable.'},503);}
 }
 if(request.method!=='PUT')return reply({error:'Method not allowed'},405);
 if(request.headers.get('Origin')!==url.origin)return reply({error:'Origin mismatch'},403);
 let id;try{id=decodeURIComponent(path.slice('/api/admin/sources/'.length));}catch{return reply({error:'Source unavailable.'},404);}
 if(!sourceId(id)||path!==`/api/admin/sources/${id}`)return reply({error:'Source unavailable.'},404);
 let body;try{body=await boundedJSON(request,10_000);if(!parseBody(body))throw Error();}catch{return reply({error:'Invalid source operation.'},400);}
 let existing;try{existing=await env.DB.prepare('SELECT id,document,revision,active FROM source_policies WHERE id=?').bind(id).first();}catch{return reply({error:'Public source policies unavailable.'},503);}
 let policy;try{policy=existing&&publicPolicy(id,JSON.parse(existing.document));}catch{policy=null;}
 if(!policy)return reply({error:'Source is not an administrable public policy.'},404);
 if(existing.revision!==body.revision)return reply({error:'A newer public source revision exists.'},409);
 if((existing.active===1)===body.active)return reply({error:'Choose a different source status.'},400);
 const revision=body.revision+1,nonce=crypto.randomUUID(),now=new Date().toISOString(),action=body.active?'reactivated':'suspended';
 const lock=env.DB.prepare('INSERT INTO admin_operations_locks(source_id,nonce,created_at) VALUES(?,?,?) ON CONFLICT(source_id) DO NOTHING RETURNING source_id').bind(id,nonce,now);
 const update=env.DB.prepare("UPDATE source_policies SET active=?,revision=revision+1 WHERE id=? AND revision=? AND EXISTS(SELECT 1 FROM admin_operations_locks WHERE source_id=? AND nonce=?) RETURNING revision").bind(body.active?1:0,id,body.revision,id,nonce);
 // `changes()` belongs to this D1 batch connection and therefore records the
 // immediately preceding CAS UPDATE. It prevents a loser that acquires the
 // lock after a winner has released it from writing a misleading audit row.
 const audit=env.DB.prepare("INSERT INTO admin_operations_audit(id,actor_id,source_id,revision,action,created_at) SELECT ?,?,?,?,?,? WHERE changes()=1 AND EXISTS(SELECT 1 FROM admin_operations_locks WHERE source_id=? AND nonce=?)").bind(crypto.randomUUID(),user.id,id,revision,action,now,id,nonce);
 const release=env.DB.prepare('DELETE FROM admin_operations_locks WHERE source_id=? AND nonce=?').bind(id,nonce);
 try{
  if(!env.DB.batch)throw Error();
  const result=await env.DB.batch([lock,update,audit,release]);
  if(!result[0]?.results?.length||!result[1]?.results?.length)return reply({error:'A newer public source revision exists.'},409);
  if(result[2]?.meta?.changes!==undefined&&result[2].meta.changes!==1)return reply({error:'Public source operation failed.'},503);
 }catch{return reply({error:'Public source operation failed.'},503);}
 return reply({id,revision,active:body.active,action});
}
