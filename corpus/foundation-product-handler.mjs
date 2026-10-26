// Install alongside foundation-origin-reader.mjs. No runtime acquisition.
import {createAcceptedFoundationReader, FoundationOriginError} from './foundation-origin-reader.mjs';
const PATH='/api/corpus/foundation';
const keys=new Set(['source','barcode','cursor','limit']);
export function createFoundationProductHandler({readBlob,selections,readerFactory=createAcceptedFoundationReader}={}) {
  // Copy configuration once; requests cannot supply release, origin or descriptors.
  const fixed=new Map();
  if(selections && typeof selections==='object' && !Array.isArray(selections)) {
    for(const [key,value] of Object.entries(selections)) {
      if(value?.sourceId===key) fixed.set(key,structuredClone(value));
    }
  }
  return async function handle(request) {
    const url=new URL(request.url);
    if(url.pathname!==PATH)return null;
    const head=request.method==='HEAD';
    const reply=(status,payload,extra={})=>new Response(head?null:JSON.stringify(payload),{status,headers:{'Content-Type':'application/json; charset=utf-8','Cache-Control':'no-store','X-Content-Type-Options':'nosniff',...extra}});
    const error=(status,code)=>reply(status,{error:code,externalFallback:false});
    if(!['GET','HEAD'].includes(request.method))return reply(405,{error:'METHOD_NOT_ALLOWED',externalFallback:false},{Allow:'GET, HEAD'});
    for(const key of url.searchParams.keys())if(!keys.has(key)||url.searchParams.getAll(key).length!==1)return error(400,'INVALID_FOUNDATION_QUERY');
    const source=url.searchParams.get('source'),barcode=url.searchParams.get('barcode');
    const cursor=url.searchParams.get('cursor')??'',rawLimit=url.searchParams.get('limit');
    if(!source||source.length>512||/[\x00-\x1f\x7f]/.test(source)||!barcode||!/^\d{4,32}$/.test(barcode)||cursor.length>700||(rawLimit!==null&&!/^(?:[1-9]|1[0-9]|20)$/.test(rawLimit)))return error(400,'INVALID_FOUNDATION_QUERY');
    const selection=fixed.get(source);
    if(!selection||typeof readBlob!=='function'||typeof readerFactory!=='function')return error(503,'OWN_DATA_UNAVAILABLE');
    try {
      // Fresh reader and clone isolate its cache/read budget and configuration.
      const reader=await readerFactory(readBlob,structuredClone(selection));
      const payload=await reader.lookup({source,barcode,cursor,limit:rawLimit===null?20:Number(rawLimit)});
      if(!payload||![200,503].includes(payload.httpStatus)||payload.externalFallback!==false) return error(503,'OWN_DATA_UNAVAILABLE');
      return reply(payload.httpStatus,payload);
    } catch(e) {
      if(e instanceof FoundationOriginError&&[400,409].includes(e.status))return error(e.status,'INVALID_FOUNDATION_QUERY');
      return error(503,'OWN_DATA_UNAVAILABLE');
    }
  };
}
