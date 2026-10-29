import fs from 'node:fs';
import {createRequire} from 'node:module';
const require=createRequire(import.meta.url);
const esbuild=require('/home/user/src/offmenu/node_modules/esbuild');
if(esbuild.version!=='0.25.12')throw Error('esbuild version pin');
const root=new URL('./',import.meta.url).pathname;
fs.mkdirSync(root+'build',{recursive:true});
const result=await esbuild.build({entryPoints:[root+'source/source-barcode-handler.mjs'],outfile:root+'build/source-barcode-handler.bundle.mjs',
 bundle:true,format:'esm',platform:'browser',target:'es2022',metafile:true,write:true});
if(Object.values(result.metafile.outputs).some(o=>o.imports.length))throw Error('external import');
fs.writeFileSync(root+'build/metafile.json',JSON.stringify(result.metafile,null,2)+'\n');
console.log(JSON.stringify({esbuild:esbuild.version,inputCount:Object.keys(result.metafile.inputs).length,externalImports:0,scope:'pure endpoint component only; no full app/Worker build'}));
