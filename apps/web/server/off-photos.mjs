import {OFF_PHOTOS} from '../src/off-photo-catalogue.js';

// Fixed public publisher images only. No caller URL, credentials, redirects,
// arbitrary proxy, source persistence or CSP/provider setting change.
export function createOffPhotoRoutes({fetchImpl=fetch,maxBytes=1048576,timeoutMs=5000}={}) {
  if(!Number.isInteger(maxBytes)||maxBytes<3||maxBytes>1048576||
    !Number.isInteger(timeoutMs)||timeoutMs<1||timeoutMs>5000)throw TypeError('Invalid photo bounds');
  const failure=(status,code)=>Response.json({error:code},{status,headers:{'Cache-Control':'no-store','X-Content-Type-Options':'nosniff'}});
  return async request=>{
    const url=new URL(request.url);
    if(!url.pathname.startsWith('/api/off-photos/'))return null;
    const photo=OFF_PHOTOS.find(photo=>photo.path===url.pathname);
    if(!photo||url.search)return failure(404,'PHOTO_NOT_SELECTED');
    if(request.method!=='GET')return failure(405,'METHOD_NOT_ALLOWED');
    const controller=new AbortController();let timer,reader;
    const expired=new Promise((_,reject)=>{timer=setTimeout(()=>{controller.abort();reject(Error('deadline'));},timeoutMs);});
    const within=operation=>Promise.race([operation,expired]);
    try {
      const upstream=await within(fetchImpl(photo.url,{method:'GET',redirect:'error',credentials:'omit',
        headers:{Accept:'image/jpeg'},signal:controller.signal}));
      if(upstream.status!==200||upstream.redirected||upstream.headers.get('Content-Type')?.split(';')[0].trim().toLowerCase()!=='image/jpeg')
        throw Error('upstream');
      const declared=upstream.headers.get('Content-Length');
      if(declared!==null&&(!/^\d+$/.test(declared)||Number(declared)>maxBytes))throw Error('extent');
      reader=upstream.body?.getReader();if(!reader)throw Error('body');
      const chunks=[];let size=0;
      for(;;){const {done,value}=await within(reader.read());if(done)break;size+=value.byteLength;
        if(size>maxBytes)throw Error('extent');chunks.push(value);}
      if(declared!==null&&size!==Number(declared))throw Error('extent');
      const bytes=new Uint8Array(size);let offset=0;
      for(const chunk of chunks){bytes.set(chunk,offset);offset+=chunk.byteLength;}
      if(bytes[0]!==255||bytes[1]!==216||bytes[2]!==255)throw Error('format');
      return new Response(bytes,{headers:{'Content-Type':'image/jpeg','Content-Length':String(size),
        'Cache-Control':'public, max-age=300','X-Content-Type-Options':'nosniff',
        'Referrer-Policy':'no-referrer','Link':'<'+photo.licenseUrl+'>; rel="license", <'+photo.sourcePage+'>; rel="describedby"'}});
    }catch{return failure(502,'PUBLISHER_PHOTO_UNAVAILABLE');}
    finally{clearTimeout(timer);controller.abort();if(reader){void reader.cancel().catch(()=>{});reader.releaseLock();}}
  };
}
