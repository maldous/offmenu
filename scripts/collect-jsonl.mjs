// Full gzip JSONL acquisition projection. Never run in an interactive Worker.
// Originals remain in the supplied gzip; public projections omit contributor
// identities and proof-image paths. Whole release acceptance is atomic.
import {createReadStream,createWriteStream} from 'node:fs';
import {mkdir,readFile,writeFile,rename,rm,stat} from 'node:fs/promises';
import {createGunzip,createGzip} from 'node:zlib';
import {createHash} from 'node:crypto';
import {createInterface} from 'node:readline';
import {once} from 'node:events';
import {finished} from 'node:stream/promises';
import {normalizeOFF,normalizePrices,record,validateRecords} from '../public/unified-data.js';
import {sourceById} from '../public/sources.js';

async function hash(path){const h=createHash('sha256');for await(const b of createReadStream(path))h.update(b);return h.digest('hex');}
async function* lines(path){
 const unzip=createReadStream(path).pipe(createGunzip());
 // readline alone does not reliably propagate upstream gzip integrity errors.
 let failure;unzip.on('error',e=>{failure=e;});
 const reader=createInterface({input:unzip,crlfDelay:Infinity});
 for await(const line of reader){if(line.trim())yield line;}
 if(failure)throw failure;
}
const [sourceId,release,input,directory,locationInput,proofInput]=process.argv.slice(2);
if(!['off','prices'].includes(sourceId)||!release||!input||!directory)throw Error('Usage: node scripts/collect-jsonl.mjs off|prices release input.gz output-directory [locations.gz proofs.gz]');
const source=sourceById(sourceId),sha256=await hash(input);
try{const old=JSON.parse(await readFile(directory+'/manifest.json','utf8'));if(old.archiveSha256!==sha256||old.releaseId!==release)throw Error('Use a different directory for a changed release');if(old.status==='normalized'){console.log(JSON.stringify({resumed:true,...old.counts}));process.exit(0);}}catch(e){if(e.code!=='ENOENT')throw e;}
const pending=directory+'.partial';await rm(pending,{recursive:true,force:true});await mkdir(pending,{recursive:true});
const manifest={schemaVersion:'offmenu-collection/1',sourceId,releaseId:release,archiveSha256:sha256,
 license:source.license,attribution:source.name,url:source.url,status:'collecting',
 scope:sourceId==='off'?'All product rows in the full JSONL export; original fields retained in archive':'All prices, locations and proof metadata rows; images and contributor identities excluded from public projection',
 counts:{raw:0,accepted:0,duplicates:0,quarantined:0,excluded:0,records:0},countries:{},kinds:{},
 publication:'local only; no production corpus storage enabled',featureExercises:[]};
const locations=new Map();
if(sourceId==='prices'){
 if(!locationInput||!proofInput)throw Error('Full price scope requires locations and proof metadata exports');
 manifest.related=[];
 for(const [kind,path] of [['locations',locationInput],['proofs',proofInput]]){
  let count=0;for await(const line of lines(path)){const row=JSON.parse(line);if(row.id==null)throw Error('Missing related-row identity');if(kind==='locations'){if(locations.has(String(row.id)))throw Error('Duplicate location identity');locations.set(String(row.id),row);}count++;}
  manifest.related.push({kind,sha256:await hash(path),raw:count,accepted:count,publicFields:kind==='proofs'?'IDs referenced by price observations only; no image/user/comment/consumption projection':'location identity, name, address, country; no contributor identities'});
 }
}
const outputs=new Map(),ids=new Set(),quarantine=createWriteStream(pending+'/quarantine.jsonl');
const fetchedAt=new Date().toISOString();
async function output(rows,key){
 const shard=createHash('sha256').update(key).digest('hex').slice(0,2);
 if(!outputs.has(shard)){const file=createWriteStream(pending+'/'+shard+'.jsonl.gz'),gzip=createGzip({level:1});gzip.pipe(file);outputs.set(shard,{file,gzip,rows:0});}
 const out=outputs.get(shard);out.rows+=rows.length;
 if(!out.gzip.write(JSON.stringify(rows)+'\n'))await once(out.gzip,'drain');
}
for await(const line of lines(input)){
 const counts=manifest.counts;counts.raw++;
 try{
  const raw=JSON.parse(line),key=String(sourceId==='off'?raw.code??'':raw.id??'');
  if(!key||sourceId==='off'&&!/^\d{4,32}$/.test(key))throw Error('Missing or invalid source identifier');
  if(ids.has(key)){counts.duplicates++;continue;}ids.add(key);
  if(sourceId==='prices'&&raw.duplicate_of!=null){counts.excluded++;continue;}
  if(sourceId==='prices'&&raw.location_id!=null&&!locations.has(String(raw.location_id)))throw Error('Unresolved location reference');
  const rows=sourceId==='off'?normalizeOFF(raw,source):normalizePrices({items:[{...raw,location:locations.get(String(raw.location_id))}]},source);
  for(const r of rows){r.provenance={...r.provenance,fetchedAt,releaseId:release,archiveSha256:sha256,transform:'offmenu-bulk/1',sourceRow:counts.raw};}
  validateRecords(rows);await output(rows,key);counts.accepted++;counts.records+=rows.length;
  for(const r of rows){manifest.kinds[r.kind]=(manifest.kinds[r.kind]||0)+1;for(const c of r.countries)manifest.countries[c]=(manifest.countries[c]||0)+1;}
 }catch(e){counts.quarantined++;if(!quarantine.write(JSON.stringify({row:counts.raw,reason:e.message})+'\n'))await once(quarantine,'drain');}
 if(counts.raw%100000===0)console.log(JSON.stringify(counts));
}
quarantine.end();await finished(quarantine);
for(const o of outputs.values())o.gzip.end();
await Promise.all([...outputs.values()].map(async o=>{await finished(o.gzip);await finished(o.file);}));
const c=manifest.counts;if(c.raw!==c.accepted+c.duplicates+c.quarantined+c.excluded)throw Error('Reconciliation failed');
manifest.partitions=[];
for(const [shard,o] of outputs){const path=pending+'/'+shard+'.jsonl.gz';manifest.partitions.push({key:shard+'.jsonl.gz',records:o.rows,bytes:(await stat(path)).size,sha256:await hash(path)});}
manifest.status='normalized';manifest.completedAt=new Date().toISOString();
await writeFile(pending+'/manifest.json',JSON.stringify(manifest,null,2)+'\n');await rename(pending,directory);
console.log(JSON.stringify({status:manifest.status,...c,partitions:manifest.partitions.length}));
