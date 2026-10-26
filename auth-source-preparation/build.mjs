import {build} from 'esbuild';
import {createHash} from 'node:crypto';
import {readFile,writeFile,mkdir} from 'node:fs/promises';
import {fileURLToPath} from 'node:url';

const root=fileURLToPath(new URL('./',import.meta.url));
const hash=value=>createHash('sha256').update(value).digest('hex');
const expected={
  'auth.js':'72e9d654210a59438c4bb87b25cc14347c16e7394180b36d39f140fb99bfba56',
  'auth-return-bridge.js':'78f7d66ea3efb63c0c62c4b11a0fee734ad8c3b03d3e3040cab55c509d07aa11',
  'auth.html':'b29b7d4c8becc8645407af4dbb491603a18fbc15eb26f27b0a90bfd27caf6f20',
};
const assets={};
for(const [entry,name] of [
  ['public/production-auth/auth.js','auth.js'],
  ['public/auth-return-bridge.js','auth-return-bridge.js'],
]){
  const result=await build({entryPoints:[root+entry],bundle:true,minify:true,
    format:'esm',platform:'browser',target:'es2022',write:false,logLevel:'silent'});
  assets[name]=result.outputFiles[0].text;
}
assets['auth.html']=await readFile(root+'public/auth.html','utf8');
for(const [name,value] of Object.entries(assets)){
  if(hash(value)!==expected[name])throw Error('Reviewed authentication asset mismatch: '+name);
}
const module='// FINAL COMPOSED email + correlated Google capability asset. No deployment.\nexport const FINAL_AUTH_ASSETS='+JSON.stringify(assets)+';\n';
if(hash(module)!=='40777e3c8eb3b82410534619e9622dadb374c23b9a99c92fc9dde92f7932902b')
  throw Error('Reviewed authentication asset map mismatch');
await mkdir(root+'dist',{recursive:true});
for(const [name,value] of Object.entries(assets))await writeFile(root+'dist/'+name,value);
await writeFile(root+'dist/final-auth-assets.mjs',module);
console.log(JSON.stringify({status:'PASS',assets:expected,activation:false}));
