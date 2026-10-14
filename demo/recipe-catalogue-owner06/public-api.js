// Code-only catalogue adapter: consumes existing hash-pinned public recipe files.
// No retained record data, local path, runtime or account material is embedded.
let recipeManifest;let publicInventory;let publicItems;const recordPages=new Map();
const MANIFEST_SHA256='e6e74eb3e9333d67450fcf2cf8250f4aabf819b133c6cb0b85be9c78e6075a54';
const digest=async b=>[...new Uint8Array(await crypto.subtle.digest('SHA-256',b))].map(x=>x.toString(16).padStart(2,'0')).join('');
async function checkedBytes(path,expected,cap){
 const response=await fetch(path,{redirect:'error',signal:AbortSignal.timeout(45000)});if(!response.ok)throw Error('Existing public recipe file unavailable: '+response.status);
 const reader=response.body.getReader();const parts=[];let size=0;
 for(;;){const {done,value}=await reader.read();if(done)break;size+=value.byteLength;if(size>cap){await reader.cancel();throw Error('Public recipe file exceeds bounded read');}parts.push(value);}
 const bytes=new Uint8Array(size);let cursor=0;for(const p of parts){bytes.set(p,cursor);cursor+=p.length;}
 if(expected.bytes!==undefined&&size!==expected.bytes)throw Error('Existing public file byte count changed');if(await digest(bytes)!==expected.sha256)throw Error('Existing public file checksum changed');return bytes;
}
async function existingGzip(file,cap){
 if(!/^[-A-Za-z0-9/.]+$/.test(file.key)||file.key.split('/').includes('..'))throw Error('Unsafe public source file path');
 const bytes=await checkedBytes('/releases/'+recipeManifest.releaseId+'/'+file.key,file,cap);return await new Response(new Blob([bytes]).stream().pipeThrough(new DecompressionStream('gzip'))).text();
}
async function initialize(){
 if(publicItems)return;
 const manifestBytes=await checkedBytes('/recipes/manifest.json',{bytes:2115538,sha256:MANIFEST_SHA256},4*1024*1024);recipeManifest=JSON.parse(new TextDecoder().decode(manifestBytes));
 if(recipeManifest.library?.records!==25135||recipeManifest.library.schema!=='offmenu-recipe-library/1'||!/^[-A-Za-z0-9.]+$/.test(recipeManifest.releaseId))throw Error('Existing public main recipe coverage changed');
 const rows=[];const files=recipeManifest.library.catalogueFiles;let cursor=0;let completed=0;
 async function worker(){for(;;){const next=cursor++;if(next>=files.length)return;const content=JSON.parse(await existingGzip(files[next],4*1024*1024));for(const r of content){const origin=r.publisher||'Source not supplied';rows.push({key:r.id,title:r.name||'Title not supplied',origin,language:(r.languages||[]).join(','),licence:r.license||'unknown',review:r.ingredientExtractionComplete===false?'Partial historical/OCR extraction · needs transcription':origin==='recipecommons/openrecipe-spec'?'Specification example · not culinary acceptance':'Source recipe · quantity and food review required',ingredients:(r.ingredients||[]).length,directions:null,collection:'global-qualified',private:0,search:(r.search||r.name||'').normalize('NFKD').replace(/\p{M}/gu,'').toLowerCase(),partial:r.ingredientExtractionComplete===false});}completed++;const el=document.getElementById('coverage');if(el)el.textContent='Reading existing public catalogue: '+completed+' of '+files.length+' checksum-verified pages…';}}
 await Promise.all([worker(),worker(),worker(),worker()]);if(rows.length!==25135||new Set(rows.map(r=>r.key)).size!==25135)throw Error('Existing public catalogue count/identity reconciliation failed');
 rows.sort((a,b)=>a.title.localeCompare(b.title)||a.key.localeCompare(b.key));publicItems=rows;
 const facets={};for(const [label,column] of [['sources','origin'],['languages','language'],['licences','licence'],['collections','collection']]){const counts=new Map();for(const row of rows){const k=row[column]||'unknown';counts.set(k,(counts.get(k)||0)+1);}facets[label]=[...counts].map(([value,count])=>({value,count})).sort((a,b)=>b.count-a.count);}
 publicInventory={publicSnapshot:recipeManifest.releaseId,comparedFieldDifferences:336,selectedSourceIdentities:25135,sourceOccurrences:25135,overlapOccurrences:0,completeHeldInventory:false,scope:'Verified existing public main collection: 25,135 source record identities, including 256 partial historical/OCR records and one specification example. Other held/raw collections are not included. This is browsing, not recipe/rights/food acceptance.',facets};
}
async function api(path){
 await initialize();const u=new URL(path,location.origin);if(u.pathname==='/api/inventory')return publicInventory;
 if(u.pathname==='/api/recipes'){let rows=publicItems;const q=(u.searchParams.get('q')||'').normalize('NFKD').replace(/\p{M}/gu,'').toLowerCase();if(q)rows=rows.filter(r=>[r.search,r.origin,r.language,r.licence,r.review].join(' ').toLowerCase().includes(q));for(const [param,key] of [['source','origin'],['language','language'],['licence','licence'],['collection','collection']]){const v=u.searchParams.get(param);if(v)rows=rows.filter(r=>(r[key]||'unknown')===v);}const page=Math.max(0,Number(u.searchParams.get('page')||0));return {total:rows.length,page,items:rows.slice(page*48,(page+1)*48)};}
 if(u.pathname==='/api/recipe'){const key=u.searchParams.get('id');if(!publicItems.some(r=>r.key===key))throw Error('Recipe identity is not in pinned public catalogue');const hash=await digest(new TextEncoder().encode(key));const fileKey='records/world-recipes/'+hash.slice(0,2)+'.jsonl.gz';const file=recipeManifest.files.find(f=>f.key===fileKey);if(!file)throw Error('Existing public detail reference missing');if(!recordPages.has(fileKey)){const content=await existingGzip(file,8*1024*1024);const records=new Map();for(const line of content.split('\n')){if(!line.trim())continue;const bundle=JSON.parse(line);for(const r of bundle[1])records.set(r.id,r);}if(recordPages.size>=3)recordPages.delete(recordPages.keys().next().value);recordPages.set(fileKey,records);}const r=recordPages.get(fileKey).get(key);if(!r||r.kind!=='recipe')throw Error('Existing public detail identity mismatch');return {record:r,occurrences:[{collection:recipeManifest.releaseId,source_id:r.provenance.originSourceId||r.provenance.sourceId,record_id:r.provenance.recordId}]};}
 throw Error('Unsupported catalogue request');
}
