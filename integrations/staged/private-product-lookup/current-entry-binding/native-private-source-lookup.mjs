// Node-side internal native service only; this file never creates a listener.
import {readFileSync,realpathSync,statSync} from 'node:fs';
import {createHash} from 'node:crypto';
import {execFile} from 'node:child_process';
import {promisify} from 'node:util';
import path from 'node:path';
const run=promisify(execFile);
export const SNAPSHOT='27472e67235c37f9cd1637886d1f38acfc8596dfba2caa5a88868f2af8c9700e';
export const SOURCE_SCOPE='e40e6b80cc8fcdcc834be3ebe8bcf869ea74654471bea5851cc848be4965e89d';
const OWNER05='01a138a5-6210-7ad3-af85-b50eb97eaf38';
const reply=(data,status)=>Response.json(data,{status,headers:{'Cache-Control':'no-store','X-Content-Type-Options':'nosniff'}});
function pinned(ref){
  if(!ref||!path.isAbsolute(ref.path||'')||!/^[a-f0-9]{64}$/.test(ref.sha256||'')||realpathSync(ref.path)!==ref.path||!statSync(ref.path).isFile())throw Error('PIN_REQUIRED');
  const data=readFileSync(ref.path);
  if(createHash('sha256').update(data).digest('hex')!==ref.sha256)throw Error('PIN_MISMATCH');
  return data;
}

export function createNativePrivateSourceLookup({enabled=false,sourceScopeRef,readerRef,lookupRef,pythonPath,assertAuthority}={}){
  let busy=false;
  return async function nativeLookup(request){
    const url=new URL(request.url);
    if(url.origin!=='https://offmenu-private-product-source.invalid')return null;
    if(!enabled)return reply({error:'PRIVATE_LOOKUP_DISABLED'},404);
    if(url.pathname!=='/lookup'||request.method!=='GET'||request.headers.has('Authorization')||request.headers.has('Cookie')||
       request.headers.get('X-OffMenu-Private-Lookup')!=='prior10300'||url.searchParams.size!==1||
       !/^[0-9]{1,64}$/.test(url.searchParams.get('barcode')||''))return reply({error:'PRIVATE_LOOKUP_REQUEST_REJECTED'},400);
    if(busy)return reply({error:'PRIVATE_LOOKUP_BUSY'},503);
    busy=true;
    try{
      // The existing05 owner closure must revalidate its exact00 admission and
      // native runtime/source selection; a caller request cannot supply this.
      const authority=typeof assertAuthority==='function'?await assertAuthority():null;
      if(authority?.ownerThread!==OWNER05||authority.origin!=='http://127.0.0.1:7645'||
         authority.environment!=='local-development'||authority.boundHost!=='127.0.0.1'||authority.boundPort!==7645||authority.snapshotSha256!==SNAPSHOT||
         authority.sourceScopeSha256!==SOURCE_SCOPE)throw Error('ACTUAL_OWNER_AUTHORITY_REQUIRED');
      const scope=JSON.parse(pinned(sourceScopeRef));
      if(sourceScopeRef.sha256!==SOURCE_SCOPE||scope.worker!==56||scope.snapshotOnly?.sha256!==SNAPSHOT)throw Error('SOURCE_SCOPE_REQUIRED');
      pinned(readerRef);pinned(lookupRef);
      if(path.basename(readerRef.path)!=='lookup-cli.py'||path.basename(lookupRef.path)!=='lookup.py'||
         path.dirname(readerRef.path)!==path.dirname(lookupRef.path)||!path.isAbsolute(pythonPath||'')||
         realpathSync(pythonPath)!==pythonPath||!statSync(pythonPath).isFile())throw Error('EXACT_READER_RUNTIME_REQUIRED');
      const {stdout}=await run(pythonPath,['-I','-B',readerRef.path,url.searchParams.get('barcode')],{
        cwd:path.dirname(readerRef.path),encoding:'utf8',timeout:3500,maxBuffer:65536,
        signal:request.signal,windowsHide:true,env:{PYTHONDONTWRITEBYTECODE:'1',PYTHONNOUSERSITE:'1',LANG:'C.UTF-8'}
      });
      const value=JSON.parse(stdout);
      if(value.snapshotSha256!==SNAPSHOT||value.barcode!==url.searchParams.get('barcode')||
         value.reviewStatus!=='unreviewed'||value.goldAdmitted!==false||value.canonicalEquivalence!==false||
         !Array.isArray(value.products)||value.products.length>8)throw Error('BOUNDED_DTO_REQUIRED');
      return reply(value,200);
    }catch{return reply({error:'PRIVATE_LOOKUP_UNAVAILABLE'},503);}
    finally{busy=false;}
  };
}
