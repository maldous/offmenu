// Worker-isolate route. The existing handler supplies ITS runtime.verifiedUser.
// No server, account store, credentials, role issuer or identity substitution.
export const SNAPSHOT='27472e67235c37f9cd1637886d1f38acfc8596dfba2caa5a88868f2af8c9700e';
export const SOURCE_SCOPE='e40e6b80cc8fcdcc834be3ebe8bcf869ea74654471bea5851cc848be4965e89d';
const headers={'Cache-Control':'no-store','Vary':'Cookie, Authorization','X-Content-Type-Options':'nosniff'};
const reply=(data,status)=>Response.json(data,{status,headers});
async function boundedBody(response){
  const reader=response.body?.getReader();if(!reader)throw Error('READER_RESPONSE_REQUIRED');
  const chunks=[];let length=0;
  try{for(;;){const {done,value}=await reader.read();if(done)break;length+=value.byteLength;
    if(length>65536){await reader.cancel();throw Error('RESPONSE_LIMIT');}chunks.push(value);}}
  finally{reader.releaseLock();}
  const data=new Uint8Array(length);let offset=0;for(const chunk of chunks){data.set(chunk,offset);offset+=chunk.length;}
  return JSON.parse(new TextDecoder().decode(data));
}
export function createPrivateSourceProductRoutes({enabled=false,snapshotSha256,sourceScopeSha256,fetchImpl=fetch}={}){
  return async function privateSourceProductRoutes(request,env,{runtime}={}){
    const url=new URL(request.url);
    if(url.pathname!=='/api/private-source-products')return null;
    if(!enabled)return reply({error:'PRIVATE_LOOKUP_DISABLED'},404);
    if(url.origin!=='http://127.0.0.1:7645'||env?.DEV_INTERACTIVE!==true||
       env?.DEV_IDENTITY_TRANSPORT!=='real-existing-netlify'||runtime?.mode!=='netlify'||
       snapshotSha256!==SNAPSHOT||sourceScopeSha256!==SOURCE_SCOPE)
      return reply({error:'PRIVATE_LOCAL_LOOKUP_UNAVAILABLE'},403);
    if(request.method!=='GET')return reply({error:'METHOD_NOT_ALLOWED'},405);
    if(request.headers.has('Origin')&&request.headers.get('Origin')!==url.origin)return reply({error:'ORIGIN_REJECTED'},403);
    // Sec-Fetch-Site is an extra reject, never an authentication or peer claim.
    if(request.headers.get('Sec-Fetch-Site')==='cross-site')return reply({error:'ORIGIN_REJECTED'},403);
    let user;try{user=await runtime.verifiedUser(request);}catch{return reply({error:'AUTH_SESSION_UNAVAILABLE'},503);}
    if(!user||typeof user.id!=='string'||!user.id||user.id.length>=200)return reply({error:'SIGN_IN_REQUIRED'},401);
    if(url.searchParams.size!==1||url.searchParams.getAll('barcode').length!==1||
       !/^[0-9]{1,64}$/.test(url.searchParams.get('barcode')||''))return reply({error:'EXACT_BARCODE_REQUIRED'},400);
    const barcode=url.searchParams.get('barcode');
    // One fixed native-service request AFTER real authentication. No user or
    // credentials travel to the native reader, and no upstream source is read.
    const nativeURL=new URL('https://offmenu-private-product-source.invalid/lookup');
    nativeURL.searchParams.set('barcode',barcode);
    try{
      const response=await fetchImpl(nativeURL.href,{method:'GET',headers:{'X-OffMenu-Private-Lookup':'prior10300'},
        redirect:'error',signal:AbortSignal.timeout(4500)});
      if(!response.ok)return reply({error:'PRIVATE_LOOKUP_UNAVAILABLE'},503);
      const value=await boundedBody(response);
      if(value.snapshotSha256!==SNAPSHOT||value.barcode!==barcode||value.reviewStatus!=='unreviewed'||
         value.goldAdmitted!==false||value.canonicalEquivalence!==false||!Array.isArray(value.products)||value.products.length>8||
         value.products.some(p=>!Array.isArray(p.candidateProfiles)||p.candidateProfiles.length>4||
           p.candidateProfiles.some(q=>!Array.isArray(q.nutrients)||q.nutrients.length>32)))throw Error('BOUNDED_DTO_REQUIRED');
      return reply(value,200);
    }catch{return reply({error:'PRIVATE_LOOKUP_UNAVAILABLE'},503);}
  };
}
