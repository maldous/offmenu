import {readFile,writeFile} from 'node:fs/promises';
import {createHash} from 'node:crypto';
import {createRequire} from 'node:module';
import {resolve} from 'node:path';
const require=createRequire(import.meta.url),esbuild=require('/workspace/shared/offmenu-lifecycle-maintenance/candidate/node_modules/esbuild');
const root=new URL('.',import.meta.url).pathname,hash=b=>createHash('sha256').update(b).digest('hex');
if(esbuild.version!=='0.25.12')throw Error('Unexpected compiler');
const out=root+'private-release-build/production/owned-foundation-response.mjs';
const result=await esbuild.build({absWorkingDir:root+'source',entryPoints:['owned-foundation-response.mjs'],bundle:true,minify:true,format:'esm',platform:'neutral',target:'es2022',external:['./foundation-production-release.mjs'],outfile:out,metafile:true,write:false,legalComments:'eof'});
const code=result.outputFiles.find(f=>f.path===out)?.contents;if(!code)throw Error('Missing build');await writeFile(out,code);const inputs=[];for(const n of Object.keys(result.metafile.inputs)){const p=resolve(root+'source',n),b=await readFile(p);inputs.push({path:p,bytes:b.length,sha256:hash(b)});}
const report={schema:'offmenu-owned-foundation-api-build/1',output:{path:out,bytes:code.length,sha256:hash(code)},inputs,externalImports:Object.values(result.metafile.outputs).flatMap(x=>x.imports).filter(x=>x.external),sourceOnlyAPI:true,dataModuleIsSeparate:true,deployed:false};await writeFile(root+'api-build-manifest.json',JSON.stringify(report,null,2)+'\n');console.log(JSON.stringify({output:report.output,externalImports:report.externalImports},null,2));
