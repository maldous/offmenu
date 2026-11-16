// Production-target delivery of an explicitly selected curated foundation cut.
// No request/header rewriting, external provider lookup or raw-blob endpoint.
import {createFoundationProductHandler} from './foundation-product-handler.mjs';
import {foundationDigest} from './foundation-origin-reader.mjs';
import {readerWithReferences} from './foundation-reference-reader.mjs';
const PATH='/api/corpus/foundation',TARGET='https://offmenu.aldous.info';
const decoder=new TextDecoder('utf-8',{fatal:true});
const need=(v,m)=>{if(!v)throw Error(m);};
export function createOwnedFoundationResponse({readBlob,selections}={}){
 const fixed=structuredClone(selections),values=Object.values(fixed??{});
 need(typeof readBlob==='function'&&values.length===2&&['off','usda-files'].every(id=>fixed[id]?.sourceId===id),'Fixed own foundation sources required');
 const first=values[0];need(values.every(s=>s.releaseId===first.releaseId&&s.manifest.sha256===first.manifest.sha256&&s.admissionReceiptSha256===first.admissionReceiptSha256),'Foundation source selections disagree');
 const handle=createFoundationProductHandler({readBlob,selections:fixed,readerFactory:readerWithReferences});
 let metadataPromise;
 async function checked(descriptor){const bytes=await readBlob(descriptor.key,descriptor);need(bytes.byteLength===descriptor.bytes&&await foundationDigest(bytes)===descriptor.sha256,'Public target metadata changed');return bytes;}
 async function publicMetadata(){
  const manifest=JSON.parse(decoder.decode(await checked(first.manifest)));
  need(manifest.releaseId===first.releaseId&&manifest.deploymentScope==='owned-production-origin'&&manifest.productionOrigin===TARGET&&manifest.publicPublicationAccepted===true&&manifest.rawSourcePayloadPublished===false&&manifest.privateProviderData===false&&manifest.acquisitionAtRuntime===false&&manifest.goldAdmitted===false&&manifest.fullProductComplete===false&&manifest.acceptance?.receiptSha256===first.admissionReceiptSha256&&manifest.publicationReceipt?.sha256===first.admissionReceiptSha256,'Production target is not selected');
  const receipt=JSON.parse(decoder.decode(await checked(manifest.publicationReceipt)));
  need(receipt.schema==='offmenu-foundation-production-target-receipt/1'&&receipt.status==='selected-phase-records-exercised'&&receipt.releaseId===first.releaseId&&receipt.targetOrigin===TARGET&&receipt.publicPublicationAccepted===true&&receipt.rawSourcePayloadPublished===false&&receipt.privateProviderData===false&&receipt.acquisitionAtRuntime===false&&receipt.qualification?.allSelectedQueriesExercised===true&&receipt.qualification?.noRawPrivateFieldsOrFilesystemLocators===true&&receipt.qualification?.policySha256===manifest.policySha256&&receipt.qualification?.consumerCodeSha256===manifest.consumerCodeSha256,'Production target receipt mismatch');
  const notices=decoder.decode(await checked(manifest.sourceNotices));need(receipt.sourceNoticesSha256===manifest.sourceNotices.sha256,'Source notices changed');
  return {manifest,receipt,notices};
 }
 return async function ownedFoundationResponse(request){
  const url=new URL(request.url);if(![PATH,PATH+'/notices',PATH+'/release'].includes(url.pathname))return null;
  const head=request.method==='HEAD',reply=(status,body,type='application/json; charset=utf-8',extra={})=>new Response(head?null:(type.startsWith('application/json')?JSON.stringify(body):body),{status,headers:{'Content-Type':type,'Cache-Control':'no-store','X-Content-Type-Options':'nosniff',...extra}});
  if(url.origin!==TARGET||(request.headers.has('Origin')&&request.headers.get('Origin')!==TARGET))return reply(403,{error:'OWNED_FOUNDATION_ORIGIN_REQUIRED',externalFallback:false});
  if(!['GET','HEAD'].includes(request.method))return reply(405,{error:'METHOD_NOT_ALLOWED',externalFallback:false},'application/json; charset=utf-8',{Allow:'GET, HEAD'});
  try{
   const meta=await (metadataPromise??=publicMetadata());
   if(url.pathname===PATH+'/notices'){if(url.search)return reply(400,{error:'INVALID_FOUNDATION_QUERY',externalFallback:false});return reply(200,meta.notices,'text/plain; charset=utf-8');}
   if(url.pathname===PATH+'/release'){
    if(url.search)return reply(400,{error:'INVALID_FOUNDATION_QUERY',externalFallback:false});
    return reply(200,{releaseId:meta.manifest.releaseId,fieldContract:meta.manifest.fieldContract,manifestSha256:first.manifest.sha256,publicationReceiptSha256:first.admissionReceiptSha256,productionOrigin:TARGET,publicPublicationAccepted:true,counts:meta.manifest.counts,sources:Object.fromEntries(Object.entries(meta.manifest.sources).map(([id,s])=>[id,{releaseId:s.releaseId,qualificationSha256:s.qualificationSha256,license:s.license,attribution:s.attribution}])),sourceNotices:{path:PATH+'/notices',sha256:meta.manifest.sourceNotices.sha256},normalizationComplete:false,fullProductComplete:false,goldAdmitted:false,externalFallback:false});
   }
   const response=await handle(request);need(response instanceof Response,'Foundation handler unavailable');const headers=new Headers(response.headers);headers.set('Link','<'+PATH+'/notices>; rel="license"');return new Response(response.body,{status:response.status,headers});
  }catch{return reply(503,{error:'OWN_DATA_UNAVAILABLE',externalFallback:false});}
 };
}
