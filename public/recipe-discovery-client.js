import {assertCurated} from '../corpus/assert-curated.mjs';

const MANIFEST='https://offmenu-corpus.netlify.app/recipes/manifest.json';
const digest=async bytes=>Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256',bytes)),b=>b.toString(16).padStart(2,'0')).join('');
async function boundedJSON(response,limit){
 if(!response.ok)throw Error('Shared recipes unavailable ('+response.status+').');
 const reader=response.body.getReader(),chunks=[];let length=0;
 try{for(;;){const {done,value}=await reader.read();if(done)break;length+=value.byteLength;if(length>limit)throw Error('Recipe response exceeds limit.');chunks.push(value);}}
 finally{await reader.cancel();}
 const bytes=new Uint8Array(length);let offset=0;for(const chunk of chunks){bytes.set(chunk,offset);offset+=chunk.length;}
 return {value:JSON.parse(new TextDecoder().decode(bytes)),bytes};
}

// The public route retains its existing access guard. No private connection,
// pantry contents, upstream fallback or new account permission is requested.
export function createRecipeDiscovery({fetcher=fetch}={}){
 let manifestPromise;
 function manifest(){
  if(!manifestPromise)manifestPromise=(async()=>{
   const {value,bytes}=await boundedJSON(await fetcher(MANIFEST,{redirect:'error',credentials:'omit',signal:AbortSignal.timeout(15000)}),4*1024*1024);
   if(value.format!=='offmenu-curated/1'||value.status!=='curated-release-ready'||value.privateProviderData!==false||value.acquisitionAtRuntime!==false||value.curatedAcceptance?.status!=='all-curated-records-exercised'||value.library?.schema!=='offmenu-recipe-library/1'||!/^[-A-Za-z0-9.]{1,128}$/.test(value.releaseId||'')||!Number.isSafeInteger(value.records)||value.records<0||value.library.records!==value.records||!Array.isArray(value.library.languages))throw Error('Unaccepted recipe collection.');
   return {document:value,releaseId:value.releaseId,manifestSha256:await digest(bytes)};
  })().catch(error=>{manifestPromise=undefined;throw error;});
  return manifestPromise;
 }
 async function search({query='',cursor='',signal}={}){
  if(typeof query!=='string'||query.length>100||typeof cursor!=='string'||cursor.length>600)throw Error('Enter a recipe search of at most 100 characters.');
  const selection=await manifest();signal?.throwIfAborted();
  const params=new URLSearchParams({source:'world-recipes',kind:'recipe',query:query.trim(),limit:'20',releaseId:selection.releaseId,manifestSha256:selection.manifestSha256});
  if(cursor)params.set('cursor',cursor);
  const timeout=AbortSignal.timeout(15000),requestSignal=signal?AbortSignal.any([signal,timeout]):timeout;
  const {value}=await boundedJSON(await fetcher('/api/data/public?'+params,{method:'GET',redirect:'error',credentials:'same-origin',signal:requestSignal}),5*1024*1024);
  if(value.source!=='world-recipes'||value.releaseId!==selection.releaseId||value.manifestSha256!==selection.manifestSha256||!Array.isArray(value.records)||value.records.length>20||!(value.nextCursor===null||typeof value.nextCursor==='string'&&value.nextCursor.length>0&&value.nextCursor.length<=600&&value.nextCursor!==cursor))throw Error('Recipe response does not match the selected release.');
  const ids=new Set();for(const record of value.records){assertCurated(record);if(record.kind!=='recipe'||record.provenance.sourceId!=='world-recipes'||!record.provenance.license||!record.provenance.attribution||ids.has(record.id)||!record.data||!Array.isArray(record.data.ingredients)||!Array.isArray(record.data.directions))throw Error('Invalid curated recipe response.');ids.add(record.id);}
  return {...selection,records:value.records,nextCursor:value.nextCursor};
 }
 return {manifest,search};
}

// Display projections retain the original record separately for review/export.
// Ingredient IDs remain source/editorial hints; this creates no canonical map.
export function recipeDiscoveryView(record){
 const d=record.data;return {...d,id:record.id,name:d.name||d.title||record.id,languages:d.languages||[],publisher:d.sourcePublisher||record.provenance.attribution};
}
