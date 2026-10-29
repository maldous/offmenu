// Netlify serves static OffMenu curation. Cloudflare performs read-only indexed
// queries and optionally caches checksummed files and curated query responses.
import {createEngine} from '../../../tools/corpus/engine.mjs';
import {assertCurated} from '../../../tools/corpus/assert-curated.mjs';
function origin(env){if(!env.CURATED_CORPUS_ORIGIN)return null;const url=new URL(env.CURATED_CORPUS_ORIGIN);if(url.origin!=='https://offmenu-corpus.netlify.app'||url.pathname!=='/'||url.search||url.hash)throw Error('Unsupported curation origin');return url.origin;}
// Selected publication is append-only: its manifest must not replace the
// site's existing root or recipe manifests. Only this named namespace is allowed.
const selectedReleaseNamespaces=new Map([
 ['offmenu-off-selected-products-20261025-v1','products-selected/offmenu-off-selected-products-20261025-v1']
]);
function safeRelativeFile(key){return typeof key==='string'&&key.split('/').every(part=>/^[-A-Za-z0-9._]+$/.test(part)&&part!=='.'&&part!=='..');}
function selectedReleaseError(message,status){return Object.assign(new Error(message),{status});}
async function engine(env,recipeLibrary=false,selection=null){
 const base=origin(env);if(!base)return null;const namespace=selection&&selectedReleaseNamespaces.get(selection.releaseId),servingBase=namespace?base+'/'+namespace:base;let manifest;
 return createEngine(async key=>{
  if(!safeRelativeFile(key))throw Error('Unsafe curation file path');
  const metadata=key==='manifest.json'?null:manifest.files.find(f=>f.key===key);if(key!=='manifest.json'&&!metadata)throw Error('Unlisted curation file');
  // Cache the manifest and completed query responses. Caching every index and
  // record shard multiplies subrequests and can exhaust a cold page's budget.
  const url=servingBase+'/'+(metadata?'releases/'+manifest.releaseId+'/':recipeLibrary&&!namespace?'recipes/':'')+key,cache=metadata?null:globalThis.caches?.default;
  const cacheKey=url+(metadata?'?release='+manifest.manifestSha256:'');let response;
  try{response=await cache?.match(cacheKey);}catch{/* cache is optional */}
  if(!response){response=await fetch(url,{redirect:'manual',signal:AbortSignal.timeout(15000)});if(!response.ok)throw Error('Curated release unavailable ('+response.status+')');}
  const bytes=await response.arrayBuffer();if(bytes.byteLength>10*1024*1024)throw Error('Curated file exceeds request limit');
  // Selection pins exact published manifest bytes, not its self-declared legacy
  // manifestSha256 field. Verify cached manifests as well as fetched manifests.
  if(!metadata&&selection){
   const digest=Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256',bytes)),b=>b.toString(16).padStart(2,'0')).join('');
   if(digest!==selection.manifestSha256)throw selectedReleaseError('Selected curated manifest does not match.',409);
  }
  if(metadata){const digest=Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256',bytes)),b=>b.toString(16).padStart(2,'0')).join('');if(bytes.byteLength!==metadata.bytes||digest!==metadata.sha256)throw Error('Curated file checksum mismatch');}
  else{manifest=JSON.parse(new TextDecoder().decode(bytes));if(manifest.format!=='offmenu-curated/1'||manifest.status!=='curated-release-ready'||manifest.privateProviderData!==false||manifest.curatedAcceptance?.status!=='all-curated-records-exercised'||typeof manifest.releaseId!=='string'||!/^[-A-Za-z0-9.]+$/.test(manifest.releaseId)||manifest.releaseId==='.'||manifest.releaseId==='..')throw Error('Unaccepted OffMenu curation');if(selection&&manifest.releaseId!==selection.releaseId)throw selectedReleaseError('Selected curated release does not match.',409);}
  try{await cache?.put(cacheKey,new Response(bytes,{headers:{'Cache-Control':metadata?'public, max-age=86400':'public, max-age=60'}}));}catch{/* cache is optional */}
  return bytes;
 },{maxBlobReads:24,maxPageEntries:20});
}
export async function corpusCoverage(env){const [value,library]=await Promise.all([engine(env),engine(env,true).catch(()=>null)]);const definitions=[...(value?Object.values(value.manifest.sources).map(s=>({...s,servingRelease:value.manifest.releaseId})):[]),...(library?Object.values(library.manifest.sources).map(s=>({...s,servingRelease:library.manifest.releaseId})):[])];return definitions.map(s=>({source_id:s.sourceId,releaseId:s.servingRelease,records:s.records,scope:s.sourceId==='world-recipes'?'Licensed full recipes with source ingredients, directions and reviewable quantities':'OffMenu selected facts and discovery references',normalizedLocalRecords:s.normalizedLocalRecords,rawSourcePayloadPublished:false,status:'published OffMenu curation',independentAcceptance:false,license:s.license}));}
export async function corpusLookup(env,filters,selection=null){
 const value=await engine(env,filters.source==='world-recipes',selection);
 if(!value||!value.manifest.sources[filters.source]){
  if(selection)throw selectedReleaseError('Selected curated release/source is unavailable.',503);
  return null;
 }
 const key='https://offmenu.aldous.info/__curation-cache/'+value.manifest.manifestSha256+'?filters='+encodeURIComponent(JSON.stringify(filters))+(selection?'&manifestFile='+selection.manifestSha256:''),cache=globalThis.caches?.default;
 try{const cached=await cache?.match(key);if(cached){const result=await cached.json();if(result.releaseId!==value.manifest.releaseId||selection&&result.manifestSha256!==selection.manifestSha256)throw Error('Stale cached release');result.records.forEach(assertCurated);return result;}}catch{/* public cache is optional */}
 const result=await value.lookup(filters);
 if(selection)result.manifestSha256=selection.manifestSha256;
 try{await cache?.put(key,Response.json(result,{headers:{'Cache-Control':'public, max-age=300'}}));}catch{/* public cache is optional */}
 return result;
}
