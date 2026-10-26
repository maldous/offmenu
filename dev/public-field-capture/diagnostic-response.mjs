import {capturePublicProducts} from './public-field-capture.mjs';

export const DIAGNOSTIC_MEDIA='application/vnd.offmenu.public-field-capture+json';
const MAX_BYTES=262144;
// Call only after the existing native identifier handler has authorized and
// validated its operation. This formatter never loads data or grants access.
export async function diagnosticPublicResponse(request,response){
  if(new URL(request.url).pathname!=='/__dev/identifiers'||
     request.headers.get('Accept')!==DIAGNOSTIC_MEDIA||response.status!==200)return response;
  if(!response.headers.get('Content-Type')?.includes('application/json'))return response;
  try{
    const bytes=await response.clone().arrayBuffer();
    if(bytes.byteLength>MAX_BYTES)throw Error('PUBLIC_DIAGNOSTIC_INPUT_BOUND');
    const native=JSON.parse(new TextDecoder('utf-8',{fatal:true}).decode(bytes));
    if(native.error||native.operation!=='observation-detail'||native.details?.error||
       native.details?.detailBackend!=='retained-product-federation-v1'||
       ['unavailable','not-loaded'].includes(native.details.state))return response;
    const products=native.details.sourceProducts;
    if(!Array.isArray(products)||!Array.isArray(native.rows)||!Array.isArray(native.identityMatches))
      throw Error('PUBLIC_DIAGNOSTIC_REPLY_REQUIRED');
    if(products.length===0)return response;
    for(const product of products){
      if(product?.schema==='offmenu-public-field-capture/1'||Object.hasOwn(product||{},'binding'))
        throw Error('PUBLIC_DIAGNOSTIC_FLAT_INPUT_REQUIRED');
      const key=product?.observationKey;
      if(!key||key.databaseSha256!==native.databaseSha256||!native.rows.some(row=>
        ['run_id','input_id','record_ordinal','assertion_id'].every(name=>row[name]===key[name])))
        throw Error('PUBLIC_DIAGNOSTIC_OBSERVATION_BINDING');
    }
    const value={schema:'offmenu-public-field-diagnostic/1',operation:native.operation,
      databaseSha256:native.databaseSha256,generation:native.generation,
      detailBackend:native.details.detailBackend,detailSelectionSha256:native.details.detailSelectionSha256,
      ...(Object.hasOwn(native.details,'state')?{nativeDetailState:native.details.state}:{}),
      nativeRows:native.rows.length,nativeIdentityMatches:native.identityMatches.length,
      sourceProducts:capturePublicProducts(products)};
    const body=JSON.stringify(value);
    if(new TextEncoder().encode(body).byteLength>MAX_BYTES)throw Error('PUBLIC_DIAGNOSTIC_OUTPUT_BOUND');
    const headers=new Headers(response.headers);headers.delete('Content-Length');headers.delete('ETag');
    headers.set('Content-Type',DIAGNOSTIC_MEDIA);headers.set('Cache-Control','no-store');
    const vary=new Set((headers.get('Vary')||'').split(',').map(s=>s.trim()).filter(Boolean));
    vary.add('Accept');headers.set('Vary',[...vary].join(', '));
    return new Response(body,{status:200,headers});
  }catch{
    return Response.json({error:'PUBLIC_DIAGNOSTIC_CAPTURE_UNAVAILABLE'},{status:503,
      headers:{'Cache-Control':'no-store','Vary':'Accept, Cookie, Authorization'}});
  }
}
