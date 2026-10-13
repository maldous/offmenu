// Netlify serves static OffMenu curation. Cloudflare performs read-only indexed
// queries and optionally caches checksummed files and curated query responses.
import {createEngine} from '../corpus/engine.mjs';
import {assertCurated} from '../corpus/assert-curated.mjs';
function origin(env){if(!env.CURATED_CORPUS_ORIGIN)return null;const url=new URL(env.CURATED_CORPUS_ORIGIN);if(url.origin!=='https://offmenu-corpus.netlify.app'||url.pathname!=='/'||url.search||url.hash)throw Error('Unsupported curation origin');return url.origin;}
async function engine(env){
 const base=origin(env);if(!base)return null;let manifest;
 return createEngine(async key=>{
  const metadata=key==='manifest.json'?null:manifest.files.find(f=>f.key===key);if(key!=='manifest.json'&&!metadata)throw Error('Unlisted curation file');
  // Cache the manifest and completed query responses. Caching every index and
  // record shard multiplies subrequests and can exhaust a cold page's budget.
  const url=base+'/'+(metadata?'releases/'+manifest.releaseId+'/':'')+key,cache=metadata?null:globalThis.caches?.default;
  const cacheKey=url+(metadata?'?release='+manifest.manifestSha256:'');let response;
  try{response=await cache?.match(cacheKey);}catch{/* cache is optional */}
  if(!response){response=await fetch(url,{redirect:'manual',signal:AbortSignal.timeout(15000)});if(!response.ok)throw Error('Curated release unavailable ('+response.status+')');}
  const bytes=await response.arrayBuffer();if(bytes.byteLength>10*1024*1024)throw Error('Curated file exceeds request limit');
  if(metadata){const digest=Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256',bytes)),b=>b.toString(16).padStart(2,'0')).join('');if(bytes.byteLength!==metadata.bytes||digest!==metadata.sha256)throw Error('Curated file checksum mismatch');}
  else{manifest=JSON.parse(new TextDecoder().decode(bytes));if(manifest.format!=='offmenu-curated/1'||manifest.status!=='curated-release-ready'||manifest.privateProviderData!==false||manifest.curatedAcceptance?.status!=='all-curated-records-exercised'||!/^[-A-Za-z0-9.]+$/.test(manifest.releaseId))throw Error('Unaccepted OffMenu curation');}
  try{await cache?.put(cacheKey,new Response(bytes,{headers:{'Cache-Control':metadata?'public, max-age=86400':'public, max-age=60'}}));}catch{/* cache is optional */}
  return bytes;
 },{maxBlobReads:40});
}
export async function corpusCoverage(env){const value=await engine(env);return value?Object.values(value.manifest.sources).map(s=>({source_id:s.sourceId,releaseId:value.manifest.releaseId,records:s.records,scope:'OffMenu selected facts and discovery references',normalizedLocalRecords:s.normalizedLocalRecords,rawSourcePayloadPublished:false,status:'published OffMenu curation',independentAcceptance:false,license:s.license})):[];}
export async function corpusLookup(env,filters){
 const value=await engine(env);if(!value||!value.manifest.sources[filters.source])return null;
 const key='https://offmenu.aldous.info/__curation-cache/'+value.manifest.manifestSha256+'?filters='+encodeURIComponent(JSON.stringify(filters)),cache=globalThis.caches?.default;
 try{const cached=await cache?.match(key);if(cached){const result=await cached.json();if(result.releaseId!==value.manifest.releaseId)throw Error('Stale cached release');result.records.forEach(assertCurated);return result;}}catch{/* public cache is optional */}
 const result=await value.lookup(filters);
 try{await cache?.put(key,Response.json(result,{headers:{'Cache-Control':'public, max-age=300'}}));}catch{/* public cache is optional */}
 return result;
}
