// The same read-only curation engine runs locally and in Cloudflare Workers.
// It never reads source archives, the local SQLite build index or private data.
const encoder=new TextEncoder(),decoder=new TextDecoder();
const hash=async value=>Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256',typeof value==='string'?encoder.encode(value):value)),b=>b.toString(16).padStart(2,'0')).join('');
async function decompress(bytes){const stream=new Blob([bytes]).stream().pipeThrough(new DecompressionStream('gzip')),reader=stream.getReader();let total=0,text='';const decode=new TextDecoder();try{while(true){const {done,value}=await reader.read();if(done)break;total+=value.byteLength;if(total>80*1024*1024)throw Error('Curated partition exceeds limit');text+=decode.decode(value,{stream:true});}return text+decode.decode();}finally{await reader.cancel();}}
const norm=value=>value.normalize('NFKD').replace(/\p{M}/gu,'').toLowerCase();
import {assertCurated} from './assert-curated.mjs';
export {assertCurated} from './assert-curated.mjs';
export async function createEngine(readBlob,{maxBlobReads=Infinity}={}){
 const bytes=await readBlob('manifest.json');if(!bytes)throw Error('Curated release is not published');
 const manifest=JSON.parse(decoder.decode(bytes));
 if(manifest.format!=='offmenu-curated/1'||manifest.status!=='curated-release-ready'||manifest.privateProviderData!==false||manifest.acquisitionAtRuntime!==false)throw Error('Unaccepted curation manifest');
 const files=new Map(manifest.files.map(f=>[f.key,f]));
 async function load(key){
  const metadata=files.get(key);if(!metadata)return null;
  const data=await readBlob(key);if(!data)throw Error('Curated release file missing');
  const compressed=new Uint8Array(data);if(compressed.byteLength!==metadata.bytes||await hash(compressed)!==metadata.sha256)throw Error('Curated release checksum failed');
  return decompress(compressed);
 }
 async function posting(namespace,key,source,read){
  const text=await read(`${namespace}/${(await hash(key)).slice(0,manifest.shardLength)}.jsonl.gz`);if(!text)return [];
  for(const line of text.split('\n')){if(!line)continue;const [term,values]=JSON.parse(line);if(term===key)return values[source]||[];}return [];
 }
 async function lookup({source,query='',barcode='',kind='',country='',cursor='',limit=20}={}){
  let reads=0;
  const read=async key=>{if(reads>=maxBlobReads)throw Error('Search needs too many index reads; use fewer search terms.');reads++;return load(key);};
  const definition=manifest.sources[source];if(!definition)throw Error('Source absent from curated release');
  if(typeof query!=='string'||query.length>100||barcode&&!/^\d{4,32}$/.test(barcode)||country&&!/^[A-Z]{2}$/.test(country)||kind&&!/^[A-Za-z]+$/.test(kind)||cursor.length>600)throw Error('Invalid collection filter');
  const size=Math.max(1,Math.min(100,Number(limit)||20));
  const filters=await hash(JSON.stringify([source,query,barcode,kind,country]));
  let offset=0;
  if(cursor){let decoded;try{decoded=JSON.parse(atob(cursor.replaceAll('-','+').replaceAll('_','/')));}catch{throw Error('Invalid cursor');}
   if(decoded.release!==manifest.manifestSha256||decoded.filters!==filters)throw Error('Cursor belongs to a different release or search');
   if(!Number.isSafeInteger(decoded.offset)||decoded.offset<0)throw Error('Invalid cursor');offset=decoded.offset;
  }
  let candidates=null;
  if(barcode)candidates=await posting('barcodes',barcode,source,read);
  // Unicode words: JS \w is ASCII, so use explicit letters/numbers for search.
  const unicodeTerms=[...new Set(norm(query).match(/[\p{L}\p{N}]+/gu)||[])];
  for(const term of unicodeTerms){const found=await posting('terms',term,source,read);if(candidates===null)candidates=found;else{const set=new Set(found);candidates=candidates.filter(id=>set.has(id));}if(!candidates.length)break;}
  const [start,end]=definition.entryRange,total=candidates?.length??end-start;
  if(offset>total)throw Error('Cursor outside collection');
  const pages=new Map(),selected=[],recordShards=new Set();let examined=0;
  while(offset<total&&selected.length<size&&examined<10000){
   const id=candidates?candidates[offset]:start+offset;
   const pageId=Math.floor(id/manifest.entryPageSize);
   // Reserve a read for every selected record shard before advancing the
   // cursor. A bounded page must never skip a candidate it could not load.
   if(!pages.has(pageId)){if(reads+1+recordShards.size>maxBlobReads)break;const text=await read(`entries-${pageId}.json.gz`);if(!text)throw Error('Entry index missing');pages.set(pageId,JSON.parse(text));}
   const entry=pages.get(pageId).find(e=>e.id===id);if(!entry||entry.source!==source)throw Error('Entry index mismatch');
   if(kind&&!entry.kinds.includes(kind)||country&&entry.countries.length&&!entry.countries.includes(country)){offset++;examined++;continue;}
   if(reads+recordShards.size+(recordShards.has(entry.shard)?0:1)>maxBlobReads)break;
   recordShards.add(entry.shard);offset++;examined++;
   selected.push(entry);
  }
  if(!examined&&offset<total)throw Error('Search needs too many index reads; use fewer search terms.');
  const buckets=new Map();for(const e of selected){if(!buckets.has(e.shard))buckets.set(e.shard,new Map());buckets.get(e.shard).set(e.key,e);}
  const recordsByKey=new Map();
  for(const [shard,keys] of buckets){const text=await read(`records/${source}/${shard}.jsonl.gz`);if(!text)throw Error('Record partition missing');
   for(const line of text.split('\n')){if(!line)continue;const [key,records]=JSON.parse(line);if(keys.has(key))recordsByKey.set(key,records.map(assertCurated));}
  }
  const records=selected.flatMap(e=>{const rows=recordsByKey.get(e.key);if(!rows)throw Error('Record missing from curation partition');return rows.filter(r=>!kind||r.kind===kind);});
  if(encoder.encode(JSON.stringify(records)).byteLength>4*1024*1024)throw Error('Reduce page size: response exceeds limit');
  return {schemaVersion:'1.0',source,records,releaseId:manifest.releaseId,
   nextCursor:offset<total?btoa(JSON.stringify({release:manifest.manifestSha256,filters,offset})).replaceAll('+','-').replaceAll('/','_').replace(/=+$/,''):null,
   coverage:{curatedRecords:definition.records,normalizedLocalRecords:definition.normalizedLocalRecords,rawSourcePayloadPublished:false,independentAcceptance:false},sourceTerms:definition.license};
 }
 return {manifest,lookup};
}
