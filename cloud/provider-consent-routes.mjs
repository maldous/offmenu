// Existing-provider consent flow. Authoritative terms and persistence must be
// supplied by their current owner; no generated terms or credential storage.
const json=(body,status=200)=>Response.json(body,{status,headers:{'Cache-Control':'no-store','X-Content-Type-Options':'nosniff'}});
const purposes=new Set(['private_use','background_refresh']);
function validTerms(t,providerId){
  let url;try{url=new URL(t?.url);}catch{return false;}
  return t.providerId===providerId&&typeof t.connectionId==='string'&&!!t.connectionId&&
    typeof t.version==='string'&&!!t.version&&t.version.length<=200&&
    url.protocol==='https:'&&!url.username&&!url.password&&
    Array.isArray(t.scopes)&&t.scopes.length<=50&&t.scopes.every(s=>typeof s==='string'&&s.length>0&&s.length<=100)&&
    Array.isArray(t.purposes)&&t.purposes.length>0&&t.purposes.every(p=>purposes.has(p));
}
export async function providerConsentRoutes(request,env,{verifiedUser,boundedJSON,termsFor,storeConsent,withdrawConsent,now=()=>Date.now()}={}){
  const url=new URL(request.url),match=/^\/api\/provider-consent\/([a-z0-9_-]{1,60})$/.exec(url.pathname);
  if(!match)return null;
  if(!['GET','POST'].includes(request.method))return json({error:'METHOD_NOT_ALLOWED'},405);
  if(request.method==='POST'&&request.headers.get('Origin')!==url.origin)return json({error:'ORIGIN_MISMATCH'},403);
  if(typeof verifiedUser!=='function')return json({error:'CONSENT_SETUP_UNAVAILABLE'},503);
  let user;try{user=await verifiedUser(request);}catch{return json({error:'CONSENT_SESSION_UNAVAILABLE'},503);}
  if(!user)return json({error:'SIGN_IN_REQUIRED'},401);
  if(typeof user.id!=='string'||!user.id||user.id.length>=200)return json({error:'CONSENT_SESSION_UNAVAILABLE'},503);
  const providerId=match[1];let body;
  if(request.method==='POST'){
    try{body=await boundedJSON(request,8192);}catch{return json({error:'INVALID_CONSENT'},400);}
    // Withdrawal targets the existing server-owned connection. It must not
    // require acceptance of newer terms or trust an old browser notice version.
    if(body?.choice==='withdrawn'){
      if(Object.keys(body).some(key=>key!=='choice'))return json({error:'INVALID_WITHDRAWAL'},400);
      if(typeof withdrawConsent!=='function')return json({error:'CONSENT_STORE_NOT_CONFIGURED'},503);
      try{const receipt=await withdrawConsent({ownerUserId:user.id,actorUserId:user.id,providerId,occurredAt:now()});
        if(!Number.isSafeInteger(receipt?.revision)||receipt.revision<1)throw Error('receipt');
        return json({recorded:true,choice:'withdrawn',revision:receipt.revision});
      }catch{return json({error:'CONSENT_RECORD_UNAVAILABLE'},503);}
    }
  }
  if(typeof termsFor!=='function'||typeof storeConsent!=='function')return json({error:'PROVIDER_TERMS_NOT_CONFIGURED'},503);
  let terms;
  try{terms=await termsFor(user.id,providerId);}catch{return json({error:'PROVIDER_TERMS_UNAVAILABLE'},503);}
  if(!validTerms(terms,providerId))return json({error:'PROVIDER_TERMS_NOT_CONFIGURED'},503);
  if(request.method==='GET')return json({providerId,termsUrl:terms.url,termsVersion:terms.version,
    scopes:terms.scopes,purposes:terms.purposes});
  const allowed=new Set(['termsVersion','purpose','scopes','choice']);
  if(!body||Object.keys(body).some(k=>!allowed.has(k))||
    body.choice!=='granted'||body.termsVersion!==terms.version||
    !terms.purposes.includes(body.purpose)||!Array.isArray(body.scopes)||
    new Set(body.scopes).size!==body.scopes.length||body.scopes.some(s=>!terms.scopes.includes(s)))
    return json({error:'CONSENT_NOTICE_OR_SCOPE_CHANGED'},409);
  // Identity, provider, URL, version and time are authoritative server inputs,
  // never browser-provided authority. The existing store owns revision/history.
  let receipt;try{receipt=await storeConsent({ownerUserId:user.id,actorUserId:user.id,
    objectType:'connection',objectId:terms.connectionId,providerId,
    termsUrl:terms.url,noticeVersion:terms.version,purpose:body.purpose,
    scopes:[...body.scopes],choice:body.choice,occurredAt:now()});}
  catch{return json({error:'CONSENT_RECORD_UNAVAILABLE'},503);}
  if(!Number.isSafeInteger(receipt?.revision)||receipt.revision<1)return json({error:'CONSENT_RECORD_UNAVAILABLE'},503);
  return json({recorded:true,choice:body.choice,revision:receipt.revision});
}
