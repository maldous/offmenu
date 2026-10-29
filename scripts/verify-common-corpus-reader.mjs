import {createReadStream} from 'node:fs';
import {readFile,writeFile} from 'node:fs/promises';
import {createHash} from 'node:crypto';
import {createGunzip} from 'node:zlib';
import {createInterface} from 'node:readline';
import {dirname,resolve,relative} from 'node:path';
import {createCommonCorpus} from '../apps/web/src/common-corpus-locale.js';

const manifestPath=resolve(process.argv[2]||''),root=dirname(manifestPath),bytes=await readFile(manifestPath);
const manifest=JSON.parse(bytes);
if(manifest.schemaVersion!=='offmenu-common-package/1'||!Array.isArray(manifest.files))throw Error('Unsupported package manifest.');
const groups=['concepts','recipes','terminology','ontology'];
const graphFiles=manifest.files.filter(file=>groups.some(group=>file.key.startsWith(group+'/'))&&file.key.endsWith('.jsonl.gz'));
const selected=new Set();
for(const group of groups){const files=graphFiles.filter(file=>file.key.startsWith(group+'/'));if(!files.length)throw Error('Missing package group: '+group);for(const index of [0,Math.floor(files.length/2),files.length-1])selected.add(files[index].key);}
const output={schema:'offmenu-reader-package-probe/1',manifestPath,manifestSha256:createHash('sha256').update(bytes).digest('hex'),
  releaseId:manifest.releaseId,producerStatus:manifest.status,producerCounts:manifest.counts,
  scope:'First and last packets from first/middle/last part of each group, plus published-translation packets while seeking a foreign-source English translation. Not full-package reader validation.',files:[],samples:[],publishedTranslation:null,foreignEnglishTranslation:null};
function pathFor(key){const path=resolve(root,key);if(relative(root,path).startsWith('..')||!key||key.includes('\\'))throw Error('Unsafe package path.');return path;}
async function verifyFile(file){const hash=createHash('sha256');let size=0;for await(const chunk of createReadStream(pathFor(file.key))){size+=chunk.length;hash.update(chunk);}if(size!==file.bytes||hash.digest('hex')!==file.sha256)throw Error('Package file differs from manifest: '+file.key);output.files.push({key:file.key,sha256:file.sha256,bytes:size});}
function values(packet){const result=[];function collect(value){if(!value||typeof value!=='object')return;if(value.kind)result.push(value);for(const child of Object.values(value)){if(Array.isArray(child))child.forEach(collect);else if(child&&typeof child==='object')collect(child);}}packet.resources.forEach(collect);packet.assertions.forEach(collect);return result;}
async function probe(packet,key,line,reason){const reader=await createCommonCorpus(packet),typed=values(packet);
  for(const value of typed.filter(value=>['uri','expression'].includes(value.kind)))if(reader.displayValue(value,'ar')!==value.value)throw Error('Fixed source value changed.');
  output.samples.push({key,line,reason,resources:reader.resources.length,assertions:reader.assertions.length,expressions:typed.filter(value=>value.kind==='expression').length,unicodeIRIs:typed.filter(value=>value.kind==='uri'&&/[^\x00-\x7f]/.test(value.value)).length});
  for(const translation of packet.translations.filter(row=>row.status==='published-source')){
    const text=typed.find(value=>value.kind==='text'&&value.id===translation.textId),projection=reader.projectText(text,translation.language);
    if(projection?.translated&&projection.value===translation.value){const evidence={key,line,sourceLanguage:projection.sourceLanguage,language:projection.language,textId:projection.textId,translationId:projection.translationId,citationIds:projection.citationIds};output.publishedTranslation??=evidence;if(projection.language==='en'&&projection.sourceLanguage!=='en')output.foreignEnglishTranslation??=evidence;}
  }
}
for(const file of graphFiles){
  if(!selected.has(file.key)&&output.publishedTranslation&&output.foreignEnglishTranslation)continue;
  if(selected.has(file.key))await verifyFile(file);
  let line=0,last;
  const stream=createInterface({input:createReadStream(pathFor(file.key)).pipe(createGunzip()),crlfDelay:Infinity});
  try{for await(const raw of stream){line++;if(raw.length>16*1024*1024)throw Error('Packet exceeds probe bound.');
    if(selected.has(file.key))last=raw;
    if(selected.has(file.key)&&line===1)await probe(JSON.parse(raw),file.key,line,'first');
    else if((!output.publishedTranslation||!output.foreignEnglishTranslation)&&/"translations"\s*:\s*\[\s*\{/.test(raw)){
      if(!selected.has(file.key)&&!output.files.some(row=>row.key===file.key))await verifyFile(file);
      await probe(JSON.parse(raw),file.key,line,'published-translation');
    }
    if(!selected.has(file.key)&&output.publishedTranslation&&output.foreignEnglishTranslation)break;
  }}finally{stream.close();stream.input.destroy();}
  if(selected.has(file.key)){if(line!==file.packets)throw Error('Packet count differs from manifest: '+file.key);if(line>1)await probe(JSON.parse(last),file.key,line,'last');}
}
if(!output.publishedTranslation)throw Error('No usable published translation found.');
output.status='sampled-packets-reader-compatible';
if(process.argv[3])await writeFile(process.argv[3],JSON.stringify(output,null,2)+'\n');
console.log(JSON.stringify({status:output.status,files:output.files.length,samples:output.samples.length,publishedTranslation:output.publishedTranslation,foreignEnglishTranslation:output.foreignEnglishTranslation,expressions:output.samples.reduce((n,row)=>n+row.expressions,0),unicodeIRIs:output.samples.reduce((n,row)=>n+row.unicodeIRIs,0)}));
