import {validSourceProductReference} from '../product-visual-selector.js';
import {retainedCategoryAssociation} from '../local-retained-category-presentation.js';
const unavailable=(generation,error)=>({generation,status:'unavailable',matches:[],hasMore:false,nextCursor:null,error});
export function localRetainedCategorySelected(location=globalThis.location){
  try{const url=new URL(location.href);return url.origin==='http://127.0.0.1:17645'&&
    url.searchParams.getAll('source').length===1&&url.searchParams.get('source')==='retained-category';}
  catch{return false;}
}
export function createLocalRetainedCategoryLookup({fetchImpl=fetch}={}){
  return async function lookup(raw,generation,cursor=null,symbology=null,namespace='barcode'){
    if(cursor!==null||namespace!=='barcode'||typeof raw!=='string'||! /^[0-9]{1,64}$/.test(raw))
      return unavailable(generation,'LOCAL_RETAINED_EXACT_REQUEST_REQUIRED');
    try{
      const response=await fetchImpl('/api/local/retained-category-product?barcode='+encodeURIComponent(raw),
        {method:'GET',credentials:'same-origin',cache:'no-store',redirect:'error',headers:{Accept:'application/json'}});
      if(!response.ok)return unavailable(generation,response.status===401?'SIGN_IN_REQUIRED':'LOCAL_RETAINED_UNAVAILABLE');
      if(!response.headers.get('Content-Type')?.includes('application/json'))throw Error('type');
      const reader=response.body?.getReader();if(!reader)throw Error('body');
      let length=0;const chunks=[];
      try{for(;;){const {done,value}=await reader.read();if(done)break;length+=value.length;
        if(length>65536){await reader.cancel();throw Error('bound');}chunks.push(value);}}
      finally{reader.releaseLock();}
      const bytes=new Uint8Array(length);let at=0;for(const part of chunks){bytes.set(part,at);at+=part.length;}
      const dto=JSON.parse(new TextDecoder('utf-8',{fatal:true}).decode(bytes));
      if(dto.schema!=='offmenu-local-retained-category-product/1'||!validSourceProductReference(dto.sourceProductReference)||
        dto.id!==dto.sourceProductReference.productId||
        JSON.stringify(dto.detail?.fields?.categories?.value)!==JSON.stringify(dto.detail?.retainedSourceCategoryPresentation?.categories?.sourceValue)||
        dto.lexicalRequestGuard?.value!==raw||!retainedCategoryAssociation(dto.detail?.retainedSourceCategoryPresentation,
          dto.sourceProductReference))throw Error('binding');
      return {generation,status:'source-match',matches:[dto],hasMore:false,nextCursor:null,
        original:raw,namespace,symbology,releaseId:dto.sourceProductReference.releaseId,
        sourceId:dto.sourceProductReference.sourceId,privateRetainedSource:true};
    }catch{return unavailable(generation,'LOCAL_RETAINED_UNAVAILABLE');}
  };
}
export const lookupLocalRetainedCategory=createLocalRetainedCategoryLookup();
