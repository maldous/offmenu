import {corpusLookup} from './corpus.mjs';
export const SELECTED_RELEASE=Object.freeze({sourceId:'off',releaseId:'offmenu-off-selected-products-20261025-v1',manifestSha256:'1bf09a371a164ebd8215fd9b44a1b2ac9816caaa65cd13504086defad76d4e8f'});
const headers={'Cache-Control':'no-store','X-Content-Type-Options':'nosniff'};
const json=(value,status=200)=>Response.json(value,{status,headers});
export async function selectedProductionLookup(request,env){
 const url=new URL(request.url);if(url.pathname!=='/api/data/public')return null;
 if(!['GET','HEAD'].includes(request.method))return json({error:'METHOD_NOT_ALLOWED'},405);
 const p=url.searchParams;
 if(!p.get('releaseId')||!p.get('manifestSha256')||p.get('source')!==SELECTED_RELEASE.sourceId)return json({error:'Product information is unavailable.'},503);
 if(p.get('releaseId')!==SELECTED_RELEASE.releaseId||p.get('manifestSha256')!==SELECTED_RELEASE.manifestSha256)return json({error:'Selected curated release does not match.'},409);
 try{
  const result=await corpusLookup(env,{source:SELECTED_RELEASE.sourceId,barcode:p.get('barcode')||'',query:p.get('query')||'',kind:p.get('kind')||'',country:p.get('country')||'',cursor:p.get('cursor')||'',limit:p.get('limit')||20},SELECTED_RELEASE);
  const response=json(result);return request.method==='HEAD'?new Response(null,{status:response.status,headers:response.headers}):response;
 }catch(error){const status=error.status===409?409:error.status===400?400:503;return json({error:status===409?'Selected curated manifest does not match.':status===400?'Invalid collection filter.':'Product information is unavailable.'},status);}
}
