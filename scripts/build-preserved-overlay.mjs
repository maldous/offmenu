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
// Store repeated embedded image text once; every served asset is reconstructed
// byte-for-byte. This changes packaging only, not the approved image.
const shared=[];const ids=new Map();
const expressions=Object.entries(assets).map(([name,value])=>{
  const parts=[];let position=0;
  for(const match of value.matchAll(/data:image\/[^;]+;base64,[A-Za-z0-9/+=]+/g)){
    parts.push(JSON.stringify(value.slice(position,match.index)));
    if(!ids.has(match[0])){ids.set(match[0],shared.length);shared.push(match[0]);}
    parts.push('shared['+ids.get(match[0])+']');position=match.index+match[0].length;
  }
  parts.push(JSON.stringify(value.slice(position)));
  return JSON.stringify(name)+':'+parts.join('+');
});
await writeFile('cloud/production-overlay-assets.mjs','const shared='+JSON.stringify(shared)+';\nexport const assets={'+expressions.join(',')+'};\nexport const release='+JSON.stringify(release)+';\n');
const result=await build({entryPoints:['cloud/production-preserved-overlay.mjs'],bundle:true,minify:true,format:'esm',platform:'browser',external:['./deployed-application.mjs'],outfile:'dist/production-overlay.mjs',metafile:true});
await writeFile('dist/production-overlay-inputs.json',JSON.stringify(result.metafile,null,2)+'\n');
console.log(JSON.stringify({assetCount:Object.keys(assets).length,release}));
