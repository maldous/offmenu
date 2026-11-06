import {createSourceIdentityReader,sha256} from './source-identity-reader.mjs';
export const HTTP_SCHEMA='offmenu-source-identity-http/1';
const ORIGINS=new Set(['http://127.0.0.1:7645','http://localhost:7645']);
const ALLOWED=new Set(['source','namespace','value','offset','limit']);
const encoder=new TextEncoder();
const integer=(value,fallback,min,max)=>{
  if(value===null)return fallback;
  if(!/^(0|[1-9][0-9]*)$/.test(value))throw new Error('query');
  const n=Number(value);if(!Number.isSafeInteger(n)||n<min||n>max)throw new Error('query');return n;
};
function reply(request,status,data,extra={}){
  const body=JSON.stringify(data);const headers={'Content-Type':'application/json; charset=utf-8','Cache-Control':'no-store','X-Content-Type-Options':'nosniff','Content-Length':String(encoder.encode(body).byteLength),...extra};
  return new Response(request.method==='HEAD'?null:body,{status,headers});
}
/** Pure local HTTP adapter. Construction requires the reader's exact source admission.
 * It neither creates admission nor starts a runtime, fetches, or writes inventory.
 */
export async function createSourceIdentityHTTP(input){
  // Own all input buffers and selection before the first asynchronous pin check.
  const owned=structuredClone(input);
  const reader=await createSourceIdentityReader(owned);
  const fixed=owned.selection;
  const selectionSha256=await sha256(encoder.encode(JSON.stringify(fixed)));
  const manifest=JSON.parse(new TextDecoder().decode(owned.manifestBytes));
  const recordCount=manifest.recordCount;
  return Object.freeze({selectionSha256,async handle(request){
    const url=new URL(request.url);
    if(url.pathname!=='/api/corpus/source-identity')return null;
    const origin=request.headers.get('Origin');
    if(!ORIGINS.has(url.origin)||(origin!==null&&origin!==url.origin))return reply(request,403,{schema:HTTP_SCHEMA,error:'source-identity-origin-not-allowed'});
    if(request.method!=='GET'&&request.method!=='HEAD')return reply(request,405,{schema:HTTP_SCHEMA,error:'source-identity-method-not-allowed'},{Allow:'GET, HEAD'});
    let query;
    try{
      const seen=new Set();
      for(const [key]of url.searchParams){if(!ALLOWED.has(key)||seen.has(key))throw new Error('query');seen.add(key);}
      const sourceId=url.searchParams.get('source'),namespace=url.searchParams.get('namespace'),lexicalValue=url.searchParams.get('value');
      if(sourceId!=='usda-files'||!['barcode','USDA-FDC'].includes(namespace)||typeof lexicalValue!=='string'||lexicalValue.length<1||lexicalValue.length>512||/[\x00-\x1f\x7f]/.test(lexicalValue))throw new Error('query');
      query={sourceId,namespace,lexicalValue,offset:integer(url.searchParams.get('offset'),0,0,recordCount),limit:integer(url.searchParams.get('limit'),20,1,20)};
    }catch{return reply(request,400,{schema:HTTP_SCHEMA,error:'invalid-source-identity-request'});}
    try{
      const result=reader.lookup(query);
      return reply(request,200,{schema:HTTP_SCHEMA,kind:'source-identifier-claims',httpStatus:200,status:result.status,selectionSha256,admissionSha256:fixed.admission.sha256,readerResult:result});
    }catch{return reply(request,503,{schema:HTTP_SCHEMA,error:'source-identity-service-unavailable'});}
  }});
}
