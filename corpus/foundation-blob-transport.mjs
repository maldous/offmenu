// Fixed own-data origin; no request headers or credentials enter this transport.
const ORIGIN='https://offmenu-corpus.netlify.app';
const SHA=/^[a-f0-9]{64}$/;
const fail=()=>{throw Error('FOUNDATION_BLOB_UNAVAILABLE');};
const safe=key=>typeof key==='string'&&key.split('/').every(p=>/^[-A-Za-z0-9._]+$/.test(p)&&p!=='.'&&p!=='..');
export function createFoundationBlobTransport({fetchPublicFile,releaseId,allowedFiles}={}) {
  if(typeof fetchPublicFile!=='function'||!safe(releaseId)||releaseId.includes('/')||!Array.isArray(allowedFiles))fail();
  const prefix='own-data/foundation/'+releaseId+'/',fixed=new Map();
  for(const d of allowedFiles){
    if(!d||!safe(d.key)||!d.key.startsWith(prefix)||fixed.has(d.key)||!SHA.test(d.sha256)||
      !Number.isSafeInteger(d.bytes)||d.bytes<1||d.bytes>1024*1024||
      (d.uncompressedBytes!==undefined&&(!Number.isSafeInteger(d.uncompressedBytes)||d.uncompressedBytes<1||d.uncompressedBytes>2*1024*1024)))fail();
    fixed.set(d.key,{key:d.key,bytes:d.bytes,sha256:d.sha256,uncompressedBytes:d.uncompressedBytes});
  }
  return async function readBlob(key,descriptor){
    const d=fixed.get(key);
    if(!d||!descriptor||descriptor.key!==key||descriptor.bytes!==d.bytes||descriptor.sha256!==d.sha256||descriptor.uncompressedBytes!==d.uncompressedBytes)fail();
    const url=ORIGIN+'/'+key,controller=new AbortController();
    const timer=setTimeout(()=>controller.abort(),10000);
    let reader,response;
    try{
      response=await fetchPublicFile(url,{method:'GET',redirect:'error',credentials:'omit',cache:'no-store',signal:controller.signal});
      if(response?.status!==200||response.redirected||(response.url&&response.url!==url)||!response.body?.getReader)fail();
      const length=response.headers?.get('content-length');
      if(length!==null&&length!==undefined&&(!/^[0-9]+$/.test(length)||Number(length)!==d.bytes))fail();
      reader=response.body.getReader();
      const chunks=[];let total=0;
      while(true){
        const {done,value}=await reader.read();if(done)break;
        if(!(value instanceof Uint8Array))fail();
        total+=value.byteLength;if(total>d.bytes)fail();chunks.push(value);
      }
      if(total!==d.bytes)fail();
      const result=new Uint8Array(total);let offset=0;
      for(const chunk of chunks){result.set(chunk,offset);offset+=chunk.byteLength;}
      return result;
    }finally{
      clearTimeout(timer);
      try{if(reader)await reader.cancel();else await response?.body?.cancel();}catch{}
    }
  };
}
