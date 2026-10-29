// Manually called as part of the local publication build. No upstream network/acquisition.
// Copies ONLY checksummed curation blobs, never the build SQLite or originals.
import {readFile,writeFile,mkdir,rm,copyFile,realpath} from 'node:fs/promises';
import {resolve,dirname,sep} from 'node:path';
import {createHash} from 'node:crypto';
import {gunzipSync} from 'node:zlib';
import {assertCurated,createEngine} from '../tools/corpus/engine.mjs';
const release=process.argv[2]||process.env.OFFMENU_CURATED_RELEASE;
if(!release)throw Error('Manual local build requires OFFMENU_CURATED_RELEASE');
const source=await realpath(resolve(release,'blobs'));
const bytes=await readFile(resolve(source,'manifest.json')),manifest=JSON.parse(bytes);
if(manifest.curatedAcceptance?.status!=='all-curated-records-exercised')throw Error('Full curated consumer acceptance is required before publication');
await createEngine(key=>readFile(resolve(source,key)));
if(!/^[-A-Za-z0-9.]+$/.test(manifest.releaseId))throw Error('Invalid release ID');
const target=resolve('dist/curated-public');await rm(target,{recursive:true,force:true});await mkdir(target,{recursive:true});
async function copyNotices(value,root){
 for(const notice of value.notices||[]){
  if(!/^notices\/[-A-Za-z0-9./]+\.txt$/.test(notice.key)||notice.key.split('/').some(part=>part==='.'||part==='..')||!Number.isInteger(notice.bytes)||notice.bytes<0||notice.bytes>256*1024)throw Error('Invalid licence document path');
  const path=await realpath(resolve(root,notice.key));if(!path.startsWith(root+sep))throw Error('Licence document outside release');
  const bytes=await readFile(path);if(bytes.length!==notice.bytes||createHash('sha256').update(bytes).digest('hex')!==notice.sha256)throw Error('Licence document checksum mismatch');
  const destination=resolve(target,notice.key);await mkdir(dirname(destination),{recursive:true});
  try{const existing=await readFile(destination);if(!existing.equals(bytes))throw Error('Conflicting retained licence document');}catch(e){if(e.code!=='ENOENT')throw e;}
  await copyFile(path,destination);
 }
}
await copyNotices(manifest,source);
let verified=0;
for(const file of manifest.files){
 const path=await realpath(resolve(source,file.key));if(!path.startsWith(source+sep)||!file.key.endsWith('.gz'))throw Error('Non-curation publication path');
 const data=await readFile(path);if(data.length!==file.bytes||createHash('sha256').update(data).digest('hex')!==file.sha256)throw Error('Publication checksum mismatch');
 if(file.key.startsWith('records/'))for(const line of gunzipSync(data,{maxOutputLength:80*1024*1024}).toString('utf8').split('\n')){if(!line)continue;for(const row of JSON.parse(line)[1]){assertCurated(row);verified++;}}
 const destination=resolve(target,'releases',manifest.releaseId,file.key);await mkdir(dirname(destination),{recursive:true});await copyFile(path,destination);
}
if(verified!==manifest.records)throw Error('Publication record count mismatch');
// Retain an accepted preceding release so cached manifests can finish queries
// across the atomic Netlify switch without referring to removed file paths.
const retainIndex=process.argv.indexOf('--retain-release');
if(retainIndex>=0){
 const previous=await realpath(resolve(process.argv[retainIndex+1],'blobs')),old=JSON.parse(await readFile(resolve(previous,'manifest.json')));
 if(old.curatedAcceptance?.status!=='all-curated-records-exercised'||old.privateProviderData!==false||old.acquisitionAtRuntime!==false||!/^[-A-Za-z0-9.]+$/.test(old.releaseId)||old.releaseId===manifest.releaseId)throw Error('Invalid retained curation release');
 await createEngine(key=>readFile(resolve(previous,key)));await copyNotices(old,previous);
 for(const file of old.files){
  const path=await realpath(resolve(previous,file.key));if(!path.startsWith(previous+sep)||!file.key.endsWith('.gz'))throw Error('Non-curation retained publication path');
  const data=await readFile(path);if(data.length!==file.bytes||createHash('sha256').update(data).digest('hex')!==file.sha256)throw Error('Retained publication checksum mismatch');
  if(file.key.startsWith('records/'))for(const line of gunzipSync(data,{maxOutputLength:80*1024*1024}).toString('utf8').split('\n')){if(!line)continue;for(const row of JSON.parse(line)[1])assertCurated(row);}
  const destination=resolve(target,'releases',old.releaseId,file.key);await mkdir(dirname(destination),{recursive:true});await copyFile(path,destination);
 }
 console.log(JSON.stringify({status:'accepted-prior-curation-retained',releaseId:old.releaseId,files:old.files.length}));
}
await copyFile(resolve(source,'manifest.json'),resolve(target,'manifest.json'));
await copyFile('deploy/netlify/public/index.html',resolve(target,'index.html'));
await writeFile(resolve(target,'_headers'),'/*\n  Cache-Control: public, max-age=60\n  X-Content-Type-Options: nosniff\n  Content-Security-Policy: default-src \'none\'; style-src \'self\'\n');
console.log(JSON.stringify({status:'curation-only-publication-prepared',releaseId:manifest.releaseId,records:verified,rawSourcesPublished:false}));
