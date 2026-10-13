import test from 'node:test';
import assert from 'node:assert/strict';
import {mkdtemp,writeFile,readFile,rm} from 'node:fs/promises';
import {tmpdir} from 'node:os';
import {join} from 'node:path';
import {gzipSync} from 'node:zlib';
import {execFileSync} from 'node:child_process';
import {gzipLines} from '../scripts/gzip-jsonl.mjs';
import {createEngine,assertCurated} from '../corpus/engine.mjs';
import {corpusLookup} from '../cloud/corpus.mjs';
test('literal LF reader preserves Unicode separators and rejects truncated gzip',async()=>{
 const dir=await mkdtemp(join(tmpdir(),'offmenu-lines-'));
 try{const rows=[{name:'Milk\u2028Zutaten\u2029日本語',text:'a\r\nb'}, {code:'00012345'}],bytes=gzipSync(rows.map(JSON.stringify).join('\n'));
  await writeFile(join(dir,'ok.gz'),bytes);const decoded=[];for await(const line of gzipLines(join(dir,'ok.gz')))decoded.push(JSON.parse(line));assert.deepEqual(decoded,rows);
  await writeFile(join(dir,'bad.gz'),bytes.subarray(0,bytes.length-5));await assert.rejects(async()=>{for await(const line of gzipLines(join(dir,'bad.gz')))JSON.parse(line);});
 }finally{await rm(dir,{recursive:true,force:true});}
});
test('local compiler and serving engine publish selected facts, page Unicode/barcodes and reject private input',async()=>{
 const dir=await mkdtemp(join(tmpdir(),'offmenu-curation-'));
 const provenance={sourceId:'off',recordId:'001',visibility:'public',license:'ODbL',attribution:'Open Food Facts'};
 const row={schemaVersion:'1.0',kind:'product',id:'off:product:001',countries:['JP'],provenance,data:{name:'日本語 milk',identifiers:[{system:'barcode',value:'00012345'}],rawNutriments:{arbitrary:'original'},ingredientsText:'Original wording'}};
 try{
  const input=join(dir,'input'),output=join(dir,'release');execFileSync('mkdir',['-p',input]);
  await writeFile(join(input,'normalized.jsonl.gz'),gzipSync(JSON.stringify([row])+'\n'));
  await writeFile(join(input,'manifest.json'),JSON.stringify({sourceId:'off',status:'normalized',releaseId:'fixture',normalizedRows:1,scope:'fixture',license:'ODbL',archiveSha256:'test'}));
  execFileSync('python3',['scripts/build-curated-corpus.py','--release-dir',input,'--output',output,'--version','test'],{cwd:process.cwd()});
  const engine=await createEngine(key=>readFile(join(output,'blobs',key)));
  const page=await engine.lookup({source:'off',barcode:'00012345',country:'JP'});assert.equal(page.records.length,1);assertCurated(page.records[0]);assert.equal(page.records[0].data.ingredientsText,undefined);assert.equal(page.records[0].data.rawNutriments,undefined);assert.equal(page.records[0].curation.automaticDietQualification,false);
  assert.equal((await engine.lookup({source:'off',query:'日本語'})).records.length,1);assert.equal((await engine.lookup({source:'off',country:'FR'})).records.length,0);
  // The deployed adapter uses static files and optional cache, never a D1 query
  // or a Netlify function. Public cache failures still allow valid lookups.
  const oldFetch=globalThis.fetch,oldCaches=globalThis.caches;
  const manifest=engine.manifest;manifest.curatedAcceptance={status:'all-curated-records-exercised'};
  globalThis.fetch=async (url,options)=>{assert.equal(options.redirect,'manual','Workers must inspect redirects without following them');const path=new URL(url).pathname;assert.equal(path.includes('/v1/'),false);return path==='/manifest.json'?Response.json(manifest):new Response(await readFile(join(output,'blobs',path.replace('/releases/test/',''))));};
  globalThis.caches={default:{match:async()=>{throw Error('cache unavailable');},put:async()=>{throw Error('cache unavailable');}}};
  try{const result=await corpusLookup({CURATED_CORPUS_ORIGIN:'https://offmenu-corpus.netlify.app',DB:{prepare(){throw Error('Account DB touched');}}},{source:'off',barcode:'00012345'});assert.equal(result.records.length,1);
   globalThis.fetch=async (_url,options)=>{assert.equal(options.redirect,'manual');return new Response(null,{status:302,headers:{Location:'https://example.com/untrusted'}});};
   await assert.rejects(corpusLookup({CURATED_CORPUS_ORIGIN:'https://offmenu-corpus.netlify.app'},{source:'off'}),/Curated release unavailable \(302\)/);
  }
  finally{globalThis.fetch=oldFetch;globalThis.caches=oldCaches;}
  assert.throws(()=>assertCurated({...page.records[0],data:{credentials:'secret'}}),/private payload/);
  await writeFile(join(input,'normalized.jsonl.gz'),gzipSync(JSON.stringify([{...row,provenance:{...provenance,visibility:'private'}}])+'\n'));
  assert.throws(()=>execFileSync('python3',['scripts/build-curated-corpus.py','--release-dir',input,'--output',join(dir,'private-output'),'--version','bad'],{stdio:'pipe'}),/Command failed/);
  await assert.rejects(readFile(join(dir,'private-output/blobs/manifest.json')),/ENOENT/);
 }finally{await rm(dir,{recursive:true,force:true});}
});
