import {readFile,writeFile} from 'node:fs/promises';
import {resolve,dirname} from 'node:path';
import {createHash} from 'node:crypto';
import {createRequire} from 'node:module';
const require=createRequire(import.meta.url),esbuild=require('/workspace/shared/offmenu-lifecycle-maintenance/candidate/node_modules/esbuild');
const hash=b=>createHash('sha256').update(b).digest('hex');
const root=dirname(new URL(import.meta.url).pathname),entry=resolve(process.argv[2]||root+'/source-reference-stock-entry.mjs'),output=resolve(process.argv[3]||root+'/source-reference-stock.mjs');
if(esbuild.version!=='0.25.12')throw Error('Unexpected compiler.');
const result=await esbuild.build({absWorkingDir:root,entryPoints:[entry],bundle:true,minify:true,format:'esm',platform:'neutral',target:'es2022',outfile:output,metafile:true,write:false,legalComments:'eof'});
const code=result.outputFiles.find(f=>f.path===output)?.contents;if(!code)throw Error('Missing bundle.');
const inputs=[];for(const name of Object.keys(result.metafile.inputs)){const path=resolve(root,name),bytes=await readFile(path);inputs.push({path,bytes:bytes.length,sha256:hash(bytes)});}
await writeFile(output,code);const receipt={schema:'offmenu-source-reference-stock-build/1',esbuild:esbuild.version,output:{path:output,bytes:code.length,sha256:hash(code)},inputs,externalImports:Object.values(result.metafile.outputs).flatMap(x=>x.imports).filter(x=>x.external),actualSourceIdentitySelection:'null/unconfigured; no admission issued',scope:'Helper for private stock validation only; existing runtime entrypoints/policy unchanged'};await writeFile(output+'.build.json',JSON.stringify(receipt,null,2)+'\n');console.log(JSON.stringify({output:receipt.output,inputs:inputs.length,externalImports:receipt.externalImports}));
