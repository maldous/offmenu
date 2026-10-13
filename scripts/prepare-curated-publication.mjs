// Manually called as part of the local publication build. No upstream network/acquisition.
// Copies ONLY checksummed curation blobs, never the build SQLite or originals.
import {readFile,writeFile,mkdir,rm,copyFile,realpath} from 'node:fs/promises';
import {resolve,dirname,sep} from 'node:path';
import {createHash} from 'node:crypto';
import {gunzipSync} from 'node:zlib';
import {assertCurated,createEngine} from '../corpus/engine.mjs';
const release=process.argv[2]||process.env.OFFMENU_CURATED_RELEASE;
if(!release)throw Error('Manual local build requires OFFMENU_CURATED_RELEASE');
const source=await realpath(resolve(release,'blobs'));
const bytes=await readFile(resolve(source,'manifest.json')),manifest=JSON.parse(bytes);
if(manifest.curatedAcceptance?.status!=='all-curated-records-exercised')throw Error('Full curated consumer acceptance is required before publication');
await createEngine(key=>readFile(resolve(source,key)));
if(!/^[-A-Za-z0-9.]+$/.test(manifest.releaseId))throw Error('Invalid release ID');
const target=resolve('dist/curated-public');await rm(target,{recursive:true,force:true});await mkdir(target,{recursive:true});
let verified=0;
for(const file of manifest.files){
 const path=await realpath(resolve(source,file.key));if(!path.startsWith(source+sep)||!file.key.endsWith('.gz'))throw Error('Non-curation publication path');
 const data=await readFile(path);if(data.length!==file.bytes||createHash('sha256').update(data).digest('hex')!==file.sha256)throw Error('Publication checksum mismatch');
 if(file.key.startsWith('records/'))for(const line of gunzipSync(data,{maxOutputLength:80*1024*1024}).toString('utf8').split('\n')){if(!line)continue;for(const row of JSON.parse(line)[1]){assertCurated(row);verified++;}}
 const destination=resolve(target,'releases',manifest.releaseId,file.key);await mkdir(dirname(destination),{recursive:true});await copyFile(path,destination);
}
if(verified!==manifest.records)throw Error('Publication record count mismatch');
await copyFile(resolve(source,'manifest.json'),resolve(target,'manifest.json'));
await copyFile('netlify/public/index.html',resolve(target,'index.html'));
await writeFile(resolve(target,'_headers'),'/*\n  Cache-Control: public, max-age=60\n  X-Content-Type-Options: nosniff\n  Content-Security-Policy: default-src \'none\'; style-src \'self\'\n');
console.log(JSON.stringify({status:'curation-only-publication-prepared',releaseId:manifest.releaseId,records:verified,rawSourcesPublished:false}));
