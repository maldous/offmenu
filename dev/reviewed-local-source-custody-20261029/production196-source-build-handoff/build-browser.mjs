import {readFile,writeFile,mkdir} from 'node:fs/promises';
import {resolve,join} from 'node:path';
import {createHash} from 'node:crypto';
import {createRequire} from 'node:module';
const require=createRequire(import.meta.url),esbuild=require('./toolchain/node_modules/esbuild');
const sha=b=>createHash('sha256').update(b).digest('hex'),assert=(x,m)=>{if(!x)throw Error(m)};
const root=resolve(process.argv[2]),out=resolve(process.argv[3]),deps=resolve(new URL('./build-tools/node_modules',import.meta.url).pathname);
assert(esbuild.version==='0.25.12','builder version');const mb=await readFile(join(root,'candidate-source-manifest.json')),m=JSON.parse(mb),selected=new Map();
for(const x of m.files){if(x.sourceAvailable===false)continue;const p=join(root,'candidate-source',x.group,x.path),b=await readFile(p);assert(sha(b)===x.afterSha256,'source pin '+p);selected.set(resolve(p),{group:x.group,path:x.path,sha256:sha(b),bytes:b.length});}
for(const [p,h]of [['@netlify/identity/dist/main.js','bbfddfc66293ecc3a2ca94c6cdc4a3fd039705bded3e44808ec4e159bc6c23d3'],['gotrue-js/lib/index.js','0f26ddf432d7693264ede22528edb58087f646bc6cecfc686ce47351e89bc5df']]){const path=join(deps,p),b=await readFile(path);assert(sha(b)===h,'dependency pin');selected.set(path,{path:p,bytes:b.length,sha256:h,thirdParty:true});}
await mkdir(out,{recursive:true});let results=[];
for(const [group,entry,output]of [['app','public/app.js','app.js'],['scanner','public/production-scanner/shelf-scanner.js','shelf-scanner.js'],['guest','public/production-scanner/guest-shelf-scanner-inventory.js','full-scanner.js']]){
 const cwd=join(root,'candidate-source',group),path=join(out,output);const result=await esbuild.build({absWorkingDir:cwd,entryPoints:[entry],bundle:true,minify:true,format:'esm',platform:'browser',nodePaths:[deps],outfile:path,metafile:true,write:false,legalComments:'eof'});
 const inputs=Object.keys(result.metafile.inputs).map(p=>{const pin=selected.get(resolve(cwd,p));assert(pin,'unpinnedinput '+p);return pin;});const code=result.outputFiles.find(f=>f.path===path).contents;await writeFile(path,code);await writeFile(path+'.metafile.json',JSON.stringify(result.metafile,null,2));results.push({group,entry,output,bytes:code.length,sha256:sha(code),inputs,externalImports:Object.values(result.metafile.outputs).flatMap(o=>o.imports).filter(i=>i.external)});
}
await writeFile(join(out,'build-manifest.json'),JSON.stringify({schema:'offmenu-pinned-browser-build/1',esbuild:esbuild.version,sourceManifestSha256:sha(mb),results},null,2));console.log(JSON.stringify(results.map(({group,bytes,sha256,externalImports})=>({group,bytes,sha256,externalImports}))));
