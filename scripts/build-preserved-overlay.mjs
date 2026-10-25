import {build} from 'esbuild';
import {readFile,writeFile,mkdir} from 'node:fs/promises';
import {execFileSync} from 'node:child_process';
await mkdir('dist',{recursive:true});
const assets={};
for(const [source,target] of [['public/production-auth/auth.js','auth.js'],['public/auth-return-bridge.js','auth-return-bridge.js'],['public/landing.js','landing.js'],['public/production-scanner/shelf-scanner.js','shelf-scanner.js'],['public/production-scanner/scanner-worker.js','production-scanner-worker.js']]){
  await build({entryPoints:[source],bundle:true,minify:true,format:'esm',outfile:'dist/'+target});
  assets[target]=await readFile('dist/'+target,'utf8');
}
for(const file of ['landing.html','landing.css','offmenu-neon.html','auth.html','shelf-scanner.html','scanner-balanced-final.svg','scanner-balanced-final-dark.svg','offmenu-system.css','scanner-theme-init.js','scanner-font-license.txt'])assets[file]=await readFile('public/'+file,'utf8');
for(const file of ['scanner-roboto-regular.ttf','scanner-roboto-bold.ttf'])assets[file]=(await readFile('public/'+file)).toString('base64');
const release={sourceCommit:execFileSync('git',['rev-parse','HEAD'],{encoding:'utf8'}).trim(),builtAt:new Date().toISOString(),preservedApplicationVersion:'c776cb4e-15ff-4221-84f8-b100461f0df8',preservedApplicationSha256:'2a07a3e6e302a328c65dbb0c21b3dce0fa8bd993edcfc5dbcf3511762c15ff6e'};
await writeFile('cloud/production-overlay-assets.mjs','export const assets='+JSON.stringify(assets)+';\nexport const release='+JSON.stringify(release)+';\n');
const result=await build({entryPoints:['cloud/production-preserved-overlay.mjs'],bundle:true,minify:true,format:'esm',platform:'browser',external:['./deployed-application.mjs'],outfile:'dist/production-overlay.mjs',metafile:true});
await writeFile('dist/production-overlay-inputs.json',JSON.stringify(result.metafile,null,2)+'\n');
console.log(JSON.stringify({assetCount:Object.keys(assets).length,release}));
