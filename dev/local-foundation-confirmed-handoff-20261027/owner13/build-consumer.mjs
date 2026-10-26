import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
import {build} from '/home/user/src/offmenu-worktrees/worker00-generation2-code-batch-20261025/node_modules/esbuild/lib/main.js';
const root=path.dirname(new URL(import.meta.url).pathname),base='/home/user/src/offmenu-worktrees/worker00-generation2-code-batch-20261025',local='/home/user/src/offmenu-data/runtime/layout-migration/worker05/normal-app-dc39-minimal-20261027',old='/home/user/src/offmenu-data/runtime/layout-migration/worker00/private10300-local-integration-20261026/accepted-url91-current-source-20261026',source=old+'/source-freeze';
const contractRoot='/home/user/src/offmenu-data/runtime/layout-migration/worker00/private10300-local-integration-20261026/local7645-foundation-root14-r1/confirmed-handoff-r1';
const owned00=new Set(['public/foundation-scanner-handoff.mjs','public/foundation-handoff-bindings.mjs','public/model.js','public/checkout-model.js','public/scanner-kitchen-handoff.js']);
const sha=b=>crypto.createHash('sha256').update(b).digest('hex');
const appOverlays=new Set(JSON.parse(fs.readFileSync(local+'/retained-overlay-list.json'))),scannerOverlays=new Set(JSON.parse(fs.readFileSync(old+'/build-receipt.json')).overlays);
const newUI=new Set(['public/app.js','public/journey-ui.js']);
const within=(dir,p)=>{const r=path.relative(dir,p);return !r.startsWith('..')&&!path.isAbsolute(r)?r:null;};
async function compile(kind,candidate){
 const entry=kind==='app'?local+'/source/public/app.js':source+'/public/production-scanner/shelf-scanner.js';
 return build({absWorkingDir:base,entryPoints:[candidate?root+'/candidate/'+(kind==='app'?'app.js':'shelf-scanner.js'):entry],bundle:true,minify:true,format:'esm',platform:'browser',write:false,metafile:true,nodePaths:[base+'/node_modules'],logLevel:'silent',plugins:[{name:'same-local05-input-graph-with-consumer-only-delta',setup(b){b.onResolve({filter:/^\.{1,2}\//},args=>{
  if(!args.importer)return;if(args.path.endsWith('foundation-scanner-handoff.mjs'))return{path:contractRoot+'/foundation-scanner-handoff.mjs'};if(args.path.endsWith('foundation-handoff-bindings.mjs'))return{path:contractRoot+'/foundation-handoff-bindings.mjs'};if(candidate&&args.path==='./foundation-scanner-client.mjs')return{path:root+'/candidate/foundation-scanner-client.mjs'};
  const importer=args.importer.startsWith(contractRoot+'/')?source+'/public/'+path.basename(args.importer):args.importer===root+'/candidate/app.js'?local+'/source/public/app.js':args.importer===root+'/candidate/shelf-scanner.js'?source+'/public/production-scanner/shelf-scanner.js':args.importer;
  const target=path.resolve(path.dirname(importer),args.path),rel=within(local+'/source',target)??within(source,target)??within(base,target);if(!rel)return;if(candidate&&owned00.has(rel))return{path:contractRoot+'/'+path.basename(rel)};
  const selected=kind==='app'?(newUI.has(rel)?local+'/source':appOverlays.has(rel)?source:base):(scannerOverlays.has(rel)?source:base);return{path:path.join(selected,rel)};
 });}}]});
}
const proof={status:'PASS_CURRENT05_APP_AND_SCANNER_REPRODUCED_CONSUMER_ONLY_SUCCESSOR',assets:{},inputs:{}};
for(const [kind,name,expected]of [['app','app.js','82729f17c4acfd701da85ff134101c0433c2993924d4874c41e7755fc7baa986'],['scanner','shelf-scanner.js','ca239c53d73e5431b7924e81f43517e020b4db1b3258806697e4c736501a6797']]){
 const before=await compile(kind,false);if(sha(before.outputFiles[0].contents)!==expected)throw Error('CURRENT05_REPRODUCTION_FAILED:'+kind+':'+sha(before.outputFiles[0].contents));
 const after=await compile(kind,true);fs.mkdirSync(root+'/assets',{recursive:true});fs.writeFileSync(root+'/assets/'+name,after.outputFiles[0].contents);
 const inputs=r=>Object.keys(r.metafile.inputs).map(p=>{p=path.resolve(base,p);return{path:p,sha256:sha(fs.readFileSync(p))};});const a=inputs(before),b=inputs(after),map=new Map(a.map(x=>[x.path,x.sha256]));const changed=b.filter(x=>map.get(x.path)!==x.sha256);
 if(changed.some(x=>!x.path.startsWith(root+'/candidate/')&&!x.path.startsWith(contractRoot+'/')))throw Error('UNEXPECTED_NONCONSUMER_INPUT_DELTA');
 proof.assets[name]={baselineSha256:expected,baselineReproduced:true,path:root+'/assets/'+name,sha256:sha(after.outputFiles[0].contents),bytes:after.outputFiles[0].contents.length,unchangedInputs:b.length-changed.length,changedInputs:changed};proof.inputs[kind]=b;
}
proof.scope='00 owned reference/model/checkout/receipt-contract overlays plus13 confirmed consumer successor; Offline only; current05 ordinary UI/identity inputs retained. No backend,root14,auth,state,provider or runtime action; new scanner client imports no legacy public-product projector.';
fs.writeFileSync(root+'/build-proof.json',JSON.stringify(proof,null,2)+'\n');console.log(JSON.stringify({...proof,inputs:undefined}));
