import path from 'node:path';
import {readFile,writeFile,mkdir,symlink,readdir} from 'node:fs/promises';
import {readFileSync,readlinkSync} from 'node:fs';
import {execFileSync,spawn} from 'node:child_process';
import {createHash,randomUUID} from 'node:crypto';
import {pathToFileURL,fileURLToPath} from 'node:url';
import {Response as WorkerResponse} from 'miniflare';
import {ownerThread,sourceRoot,externalRoot,processBirth,guardedOutbound,initializeCandidateSchema} from './dev-lifecycle.mjs';
export const inputPins=Object.freeze({'02':'c996bb469621c57820007c261585aba5faddd519','03':'e1de8e839954905d82f939730ac5ea79412bc805','05':'8dc49b2b3683f2532ee4e3581d105c446f6f575e','06':'be166bb61483825498094d496e2caed9d8b775bb'});
const base='5f5bdb6ae716cbf80fab1e174d1af2e354468ead';
export const cleanEnv=()=>Object.fromEntries(Object.entries(process.env).filter(([k])=>!k.startsWith('GIT_')));
const git=(...args)=>execFileSync('git',args,{cwd:sourceRoot,env:cleanEnv(),maxBuffer:32*1024*1024});
const hash=(data,algorithm='sha256')=>createHash(algorithm).update(data).digest('hex');
const sha=file=>hash(readFileSync(file));
const requireThat=(condition,message)=>{if(!condition)throw Error('Interactive preview refused: '+message);};
export const taskAdmission=Object.freeze({sourceThread:'01a137cf-2242-761d-8fd7-6e6fc5658013',grant:'Explicit current native root task: owner05 interactive isolated private DEV; selected02/03/05/06 pins; no production/provider/paid/security changes.',actions:Object.freeze(['owned-loopback-preview','synthetic-fixture-account-flows','fresh-isolated-synthetic-state','independent58-read/flow-checks','birth-verified-own-process-stop'])});
export function validateTaskAdmission(a,m){
 requireThat(a&&a.sourceThread===taskAdmission.sourceThread&&a.grant===taskAdmission.grant,'registered task source/grant reference');
 requireThat(Array.isArray(a.permittedActions)&&a.permittedActions.every(x=>typeof x==='string')&&new Set(a.permittedActions).size===a.permittedActions.length&&JSON.stringify([...a.permittedActions].sort())===JSON.stringify([...taskAdmission.actions].sort()),'registered synthetic fixture action scope');
 requireThat(a.boundSession===ownerThread&&a.boundRoot===sourceRoot&&JSON.stringify(a.pins)===JSON.stringify(inputPins)&&a.compositionSha256===m.compositionSha256&&JSON.stringify(a.applicationArtifact)===JSON.stringify(m.artifact),'grant session/input/artifact binding');
 requireThat(a.actualSuppliedControls?.filesystem==='danger-full-access; no restrictions'&&a.actualSuppliedControls.network==='enabled'&&a.actualSuppliedControls.mandatoryReviewer==='auto_review'&&a.actualSuppliedControls.approvalPolicy===null&&a.actualSuppliedControls.namedProfile===null&&a.environmentProfile===null&&a.notNewAccountGrant===true,'declared controls must not fabricate unavailable profile/policy or grants');
}
function nativeEqual(a,b){return ['schemaVersion','pid','bootId','birthTicks','port','jar','jarSha512','root','cwd','token','version','mappingsSha256','startedAt'].every(k=>a[k]===b[k]);}
export async function validateQualification(r,m,{live=true}={}){
 const c=r.custody,baseRoot=m.mockRoot||path.join(m.root,'mock');
 requireThat(c&&c.schemaVersion===2&&Number.isInteger(c.pid)&&c.pid>1&&c.cwd===baseRoot&&Number.isInteger(c.port)&&c.port>=1024&&c.port<=65535&&c.root.startsWith(path.join(baseRoot,'dev/wiremock/.runtime',`run-${c.port}-`))&&path.resolve(c.root)===c.root,'native qualification root/process shape');
 requireThat(r.nativeCustody?.path===path.join(c.root,'custody.json')&&sha(r.nativeCustody.path)===r.nativeCustody.sha256,'native qualification reference hash');
 const native=JSON.parse(readFileSync(r.nativeCustody.path));requireThat(nativeEqual(native,c),'declared custody differs from immutable native record');
 const lock=JSON.parse(readFileSync(path.join(baseRoot,'dev/wiremock/runtime-lock.json')));
 requireThat(r.version===lock.version&&c.version===lock.version&&r.jarSha512===lock.sha512&&c.jarSha512===lock.sha512&&hash(readFileSync(c.jar),'sha512')===lock.sha512,'qualification JAR/version versus lock/current bytes');
 const runtimePath=path.join(baseRoot,'dev/wiremock/runtime.mjs'),source=m.files.find(f=>f.part==='mock'&&f.path==='dev/wiremock/runtime.mjs');
 requireThat(r.runtimeSource?.path===runtimePath&&r.runtimeSource.sha256===source.sha256&&sha(runtimePath)===source.sha256,'qualification runtime source hash');
 const started=Date.parse(c.startedAt),qualified=Date.parse(r.qualifiedAt),now=Date.now();
 requireThat(Number.isFinite(started)&&Number.isFinite(qualified)&&qualified>=started&&qualified<=now,'qualification time before process/future/invalid');
 if(r.expiresAt!==undefined)requireThat(Number.isFinite(Date.parse(r.expiresAt))&&Date.parse(r.expiresAt)>now&&Date.parse(r.expiresAt)>=qualified,'expired qualification');
 requireThat(r.identity?.semanticsVersion==='offmenu-identity-session/2'&&JSON.stringify(r.identity.actors)===JSON.stringify(['alice','bob','admin'])&&r.identity.assertions===176&&r.identity.malformedGrantCasesPerActor===13&&r.identity.logoutRevocation===true&&r.identity.otherActorPreservation===true&&r.identity.passwordRevival===true&&r.identity.aliceRevokedForReset===true&&r.resetCheck?.assertions===2&&r.resetCheck.resetRestoresRevokedActor===true,'declared qualification semantics/assertion evidence');
 requireThat(r.reset?.receipt?.startsWith(c.root+'/reset-')&&sha(r.reset.receipt)===r.reset.sha256&&r.reset.previousAudit?.startsWith(c.root+'/audit-')&&sha(r.reset.previousAudit)===r.reset.previousAuditSha256,'preserved reset/audit evidence hashes');
 const reset=JSON.parse(readFileSync(r.reset.receipt)),audit=JSON.parse(readFileSync(r.reset.previousAudit));
 requireThat(reset.operation==='reset'&&reset.result.reset===true&&nativeEqual(reset.custody,c)&&audit.operation==='audit'&&nativeEqual(audit.custody,c)&&Date.parse(reset.at)>=started&&Date.parse(reset.at)<=qualified&&Date.parse(audit.at)>=started&&Date.parse(audit.at)<=Date.parse(reset.at),'reset/audit process/time binding');
 requireThat(sha(m.scannerDependency.path)===m.scannerDependency.sha256,'referenced scanner dependency changed');
 {
  requireThat(r.executionEvidence&&typeof r.executionEvidence.path==='string'&&typeof r.executionEvidence.sha256==='string','required actual Identity execution reference');
  requireThat(r.executionEvidence.path===path.join(c.root,'identity-execution.json')&&sha(r.executionEvidence.path)===r.executionEvidence.sha256,'preserved actual Identity execution evidence');
  const e=JSON.parse(readFileSync(r.executionEvidence.path)),validatorPath=path.join(baseRoot,'dev/wiremock/identity-validation.mjs'),vf=m.files.find(f=>f.part==='mock'&&f.path==='dev/wiremock/identity-validation.mjs');
  requireThat(e.schema==='offmenu-owner05-identity-execution/1'&&e.ownerThread===ownerThread&&e.sourceCommit===inputPins['06']&&nativeEqual(e.custody,c)&&e.validator.path===validatorPath&&e.validator.sha256===vf.sha256&&sha(validatorPath)===vf.sha256&&JSON.stringify(e.identity)===JSON.stringify(r.identity)&&JSON.stringify(e.reset)===JSON.stringify(r.reset)&&JSON.stringify(e.resetCheck)===JSON.stringify(r.resetCheck)&&Date.parse(e.completedAt)>=Date.parse(reset.at)&&Date.parse(e.completedAt)<=qualified,'qualification versus actual test/source/process evidence');
 }


 if(m.mockRoot){
  requireThat(r.selectedExecution?.path===path.join(c.root,'qualification-execution.json')&&sha(r.selectedExecution.path)===r.selectedExecution.sha256,'required selected native callback execution');
  const x=JSON.parse(readFileSync(r.selectedExecution.path)),cf=m.files.find(f=>f.part==='mock'&&f.path==='dev/wiremock/callback-source-contract.mjs');
  requireThat(x.schema==='offmenu-owner05-selected-mock-execution/1'&&x.sourceCommit===inputPins['06']&&x.ownerThread===ownerThread&&nativeEqual(x.custody,c)&&JSON.stringify(x.identity)===JSON.stringify(r.identity)&&JSON.stringify(x.reset)===JSON.stringify(r.reset)&&JSON.stringify(x.resetCheck)===JSON.stringify(r.resetCheck)&&x.callback.assertions===28&&x.callback.providerAcceptance===false&&Date.parse(x.completedAt)<=qualified&&sha(path.join(m.mockRoot,cf.path))===cf.sha256,'selected callback execution/source/process binding');
  requireThat(sha(x.audit.receipt)===x.audit.sha256,'selected native audit hash');const xa=JSON.parse(readFileSync(x.audit.receipt));requireThat(nativeEqual(xa.custody,c)&&xa.operation==='audit'&&xa.result.unmatched.length===0&&Date.parse(xa.at)>=Date.parse(reset.at)&&Date.parse(xa.at)<=Date.parse(x.completedAt),'selected native audit custody/time/unmatched');
 }

 if(live){
  const birth=processBirth(c.pid);requireThat(birth.bootId===c.bootId&&birth.startTicks===c.birthTicks&&readlinkSync(`/proc/${c.pid}/cwd`)===c.cwd,'live native boot/birth/cwd');
  const hz=Number(execFileSync('getconf',['CLK_TCK'],{env:cleanEnv(),encoding:'utf8'}));const boot=Number(readFileSync('/proc/stat','utf8').match(/^btime (\d+)$/m)?.[1]);const actualBirth=(boot+Number(c.birthTicks)/hz)*1000;
  requireThat(Number.isFinite(actualBirth)&&Math.abs(started-actualBirth)<=5000&&qualified>=actualBirth-1000,'qualification/native timestamp versus kernel process birth');
  const nativeRuntime=await import(pathToFileURL(runtimePath));await nativeRuntime.assertOwner(c);
 }
}

const put=async(file,bytes)=>{await mkdir(path.dirname(file),{recursive:true});await writeFile(file,bytes,{flag:'wx'});};
export async function buildInteractive({mockPreparation}={}){
 const selectedMockRoot=mockPreparation?verifyMockPreparation(mockPreparation).root:null;
 const root=path.join(externalRoot,'workers/worker-05/interactive',randomUUID());await mkdir(root,{recursive:true});
 const files=[];let inputBytes=0;
 async function sourceFile(part,pin,name,materialize=true){
  const meta=git('ls-tree',pin,'--',name).toString().trim().split(/\s+/);requireThat(['100644','100755'].includes(meta[0])&&meta[1]==='blob','regular pinned Git source required: '+name);
  const bytes=git('show',`${pin}:${name}`);inputBytes+=bytes.length;requireThat(inputBytes<16*1024*1024,'bounded source exceeded16MiB');
  const entry={part,path:name,commit:pin,blob:meta[2],sha256:hash(bytes),bytes:bytes.length,materialized:materialize};files.push(entry);
  if(materialize)await put(path.join(root,part,name),bytes);return bytes;
 }
 const assetsNames=['index.html','style.css','scanner-licenses.txt','recipes.json','afcd-nutrient-details.json','icon.svg','manifest.webmanifest','manifest-ar.webmanifest','data-workspace.html'];
 const selected=new Set(assetsNames.filter(f=>!['recipes.json','afcd-nutrient-details.json'].includes(f)).map(f=>'public/'+f));
 for(const line of git('ls-tree','-r','--name-only',inputPins['02']).toString().split('\n')){
  if(selected.has(line)||/^(cloud|corpus)\/.*\.(mjs|sql)$/.test(line)||/^public\/.*\.(js|mjs)$/.test(line)||/^netlify-return\/.*\.(js|html|css)$/.test(line)||/^public\/locales\/(en|ar)\.json$/.test(line)||line==='public/recipe-ingredient-aliases.json'||line==='research/manifest.json')await sourceFile('app',inputPins['02'],line);
 }
 await sourceFile('app',inputPins['02'],'package.json');await sourceFile('app',inputPins['02'],'package-lock.json');await symlink(path.join(sourceRoot,'node_modules'),path.join(root,'app/node_modules'),'dir');
 for(const name of ['adapter.mjs','fixtures.mjs','mappings.mjs','contracts.json','runtime-lock.json','runtime.mjs','identity-validation.mjs','identity-verification.json','callback-source-contract.mjs','callback-source-contract.md','callback-source-verification.json'])await sourceFile('mock',inputPins['06'],'dev/wiremock/'+name);
 await sourceFile('mock',inputPins['06'],'package.json');await sourceFile('mock',inputPins['06'],'package-lock.json');await symlink(path.join(sourceRoot,'node_modules'),path.join(root,'mock/node_modules'),'dir');
 await sourceFile('audit',inputPins['03'],'scripts/verify-uiux-browser.mjs');await sourceFile('audit',inputPins['03'],'tests-uiux/dom-audit.mjs');
 await put(path.join(root,'audit/package.json'),'{"type":"module","private":true}\n');
 for(const name of ['dev-entry.mjs','dev-server.mjs','dev-stop.mjs','dev-lifecycle.mjs'])await sourceFile('producer-input',inputPins['05'],name);
 const {build}=await import('esbuild'),assets={};
 for(const name of assetsNames){
  const bytes=['recipes.json','afcd-nutrient-details.json'].includes(name)?await sourceFile('app',inputPins['02'],'public/'+name,false):await readFile(path.join(root,'app/public',name));assets[name]=bytes.toString();
 }
 for(const [name,format] of [['app','esm'],['data-workspace','esm'],['sw','iife'],['scanner-worker','esm']]){
  const b=await build({entryPoints:[path.join(root,'app/public',name+'.js')],bundle:true,minify:true,write:false,format,platform:'browser'});assets[name+'.js']=b.outputFiles[0].text;
 }
 assets['scanner.wasm']=(await readFile(path.join(sourceRoot,'node_modules/zxing-wasm/dist/reader/zxing_reader.wasm'))).toString('base64');
 assets['retailer-extension.zip']=''; // Extension installation is not qualified in this preview.
 const release={sourceCommit:inputPins['02'],base,inputPins,developmentPendingAcceptance:true,production:false};
 const generated='const ASSETS='+JSON.stringify(assets)+';\nconst RELEASE='+JSON.stringify(release)+';\n'+await readFile(path.join(root,'app/cloud/handler.mjs'),'utf8');
 await put(path.join(root,'app/cloud/generated.mjs'),generated);
 const compiled=await build({entryPoints:[path.join(root,'app/cloud/generated.mjs')],bundle:true,minify:true,write:false,format:'esm',platform:'browser'});const artifact=path.join(root,'app/dist/worker.mjs');await put(artifact,compiled.outputFiles[0].contents);
 const trees=Object.fromEntries(Object.entries(inputPins).map(([k,p])=>[k,git('rev-parse',p+'^{tree}').toString().trim()]));
 const manifest={schema:'offmenu-owner05-private-inputs/1',root,mockRoot:selectedMockRoot,mockPreparation:mockPreparation||null,base,pins:inputPins,trees,files,inputBytes,compositionSha256:hash(JSON.stringify({base,pins:inputPins,trees,files})),artifact:{path:artifact,sha256:sha(artifact)},schemas:Object.fromEntries(['cloud/schema.sql','cloud/catalogue-schema.sql'].map(f=>[f,sha(path.join(root,'app',f))])),externalCorporaCopied:false,shippedAppAssets:'Recipes/nutrient-detail bytes are build inputs from the selected existing app Git blobs, not acquired or materialized external corpora.',scannerDependency:{path:path.join(sourceRoot,'node_modules/zxing-wasm/dist/reader/zxing_reader.wasm'),sha256:sha(path.join(sourceRoot,'node_modules/zxing-wasm/dist/reader/zxing_reader.wasm'))},dependencies:await readlinkSync(path.join(sourceRoot,'node_modules'))};
 const file=path.join(root,'inputs.json');await put(file,JSON.stringify(manifest,null,2)+'\n');return {path:file,sha256:sha(file),root,artifact:manifest.artifact,compositionSha256:manifest.compositionSha256};
}
function verifyMockPreparation(ref){
 requireThat(ref&&path.isAbsolute(ref.path)&&sha(ref.path)===ref.sha256,'selected mock preparation hash');
 const p=JSON.parse(readFileSync(ref.path));requireThat(p.schema==='offmenu-owner05-selected-mock-inputs/1'&&p.ownerThread===ownerThread&&p.sourceOwner==='06'&&p.sourceCommit===inputPins['06']&&path.resolve(p.root)===p.root&&p.root.startsWith(path.join(externalRoot,'workers/worker-05/mock-preparation')+'/'),'selected mock preparation identity');
 for(const f of p.files){requireThat(!path.isAbsolute(f.path)&&!f.path.split('/').includes('..')&&sha(path.join(p.root,f.path))===f.sha256&&hash(git('cat-file','blob',f.blob))===f.sha256&&git('rev-parse',`${p.sourceCommit}:${f.path}`).toString().trim()===f.blob,'selected mock preparation source');}return p;
}
export function verifyInputs(ref){
 requireThat(ref&&path.isAbsolute(ref.path)&&sha(ref.path)===ref.sha256,'input manifest hash');const m=JSON.parse(readFileSync(ref.path));
 if(m.mockRoot)requireThat(verifyMockPreparation(m.mockPreparation).root===m.mockRoot,'separate owned mock source root binding');
 requireThat(m.schema==='offmenu-owner05-private-inputs/1'&&m.root.startsWith(path.join(externalRoot,'workers/worker-05/interactive')+'/')&&path.resolve(m.root)===m.root&&JSON.stringify(m.pins)===JSON.stringify(inputPins),'owner/input binding');
 for(const f of m.files){requireThat(['app','mock','audit','producer-input'].includes(f.part)&&f.commit===inputPins[{'app':'02','mock':'06','audit':'03','producer-input':'05'}[f.part]]&&!path.isAbsolute(f.path)&&!f.path.split('/').includes('..'),'input path/pin');requireThat(hash(git('cat-file','blob',f.blob))===f.sha256&&git('rev-parse',`${f.commit}:${f.path}`).toString().trim()===f.blob,'input Git blob binding');if(f.materialized)requireThat(sha(path.join(m.root,f.part,f.path))===f.sha256,'materialized input changed');}
 requireThat(JSON.stringify(m.schemas)===JSON.stringify(Object.fromEntries(['cloud/schema.sql','cloud/catalogue-schema.sql'].map(f=>[f,sha(path.join(m.root,'app',f))]))),'manifest schema hashes versus selected bytes');
 requireThat(m.compositionSha256===hash(JSON.stringify({base:m.base,pins:m.pins,trees:m.trees,files:m.files}))&&sha(m.artifact.path)===m.artifact.sha256,'composition/artifact hash');return m;
}
export async function startOwnedMock(ref,port=19075){
 requireThat(process.env.CODEX_THREAD_ID===ownerThread,'actual native owner session');
 const m=verifyInputs(ref),runtime=path.join(m.mockRoot||path.join(m.root,'mock'),'dev/wiremock/runtime.mjs'),jar='/home/user/src/offmenu-workers/worker-06/dev/wiremock/.cache/wiremock-standalone-3.13.2.jar';
 const lock=JSON.parse(readFileSync(path.join(m.root,'mock/dev/wiremock/runtime-lock.json')));requireThat(hash(readFileSync(jar),'sha512')===lock.sha512,'retained JAR checksum');
 const log=path.join(m.root,`mock-start-${port}-${randomUUID()}.log`),{open}=await import('node:fs/promises');const fd=await open(log,'wx');
 const proc=spawn(process.execPath,[runtime,'start',String(port),jar],{cwd:path.join(m.root,'mock'),env:cleanEnv(),stdio:['ignore',fd.fd,fd.fd]});proc.once('exit',()=>fd.close());
 let ready;for(let i=0;i<150;i++){const text=await readFile(log,'utf8');for(const line of text.split('\n'))try{const value=JSON.parse(line);if(value.ready)ready=value;}catch{}if(ready)break;if(proc.exitCode!==null)throw Error('Own mock startup failed; log preserved '+log);await new Promise(ok=>setTimeout(ok,100));}requireThat(ready,'own mock readiness timeout; preserve startup log');
 const custody=JSON.parse(await readFile(ready.custody));const module=await import(pathToFileURL(runtime));await module.assertOwner(custody);
 const validation=await import(pathToFileURL(path.join(m.root,'mock/dev/wiremock/identity-validation.mjs')));const identity=await validation.validateIdentityRuntime(`http://127.0.0.1:${port}`);const reset=await module.operate('reset',ready.custody);const resetCheck=await validation.validateIdentityReset(`http://127.0.0.1:${port}`);
 const executionPath=path.join(custody.root,'identity-execution.json');const execution={schema:'offmenu-owner05-identity-execution/1',ownerThread,sourceCommit:inputPins['06'],validator:{path:path.join(m.root,'mock/dev/wiremock/identity-validation.mjs'),sha256:sha(path.join(m.root,'mock/dev/wiremock/identity-validation.mjs'))},custody,completedAt:new Date().toISOString(),identity,reset,resetCheck};await put(executionPath,JSON.stringify(execution,null,2)+'\n');
 const executionEvidence={path:executionPath,sha256:sha(executionPath)};
 const receipt={schema:'offmenu-owner05-mock-runtime/2',executionEvidence,ownerThread,sourceOwner:'06',sourceCommit:inputPins['06'],status:'qualified-live',qualifiedAt:new Date().toISOString(),validity:'Only while this exact owned birth, source hashes, JAR and health identity remain live; no historical PID adoption.',custody,nativeCustody:{path:ready.custody,sha256:sha(ready.custody)},runtimeSource:{path:runtime,sha256:sha(runtime)},jarSha512:lock.sha512,version:lock.version,identity,reset,resetCheck,startLog:log,startLogSha256:sha(log)};
 const file=path.join(custody.root,'qualification.json');await put(file,JSON.stringify(receipt,null,2)+'\n');return {path:file,sha256:sha(file),custodyPath:ready.custody,port};
}
export async function buildDescriptor(inputs,mock){
 const m=verifyInputs(inputs);const authority={sourceThread:'01a137cf-2242-761d-8fd7-6e6fc5658013',grant:'Explicit current native root task: owner05 interactive isolated private DEV; selected02/03/05/06 pins; no production/provider/paid/security changes.',boundSession:ownerThread,boundRoot:sourceRoot,pins:inputPins,compositionSha256:m.compositionSha256,applicationArtifact:m.artifact,permittedActions:['owned-loopback-preview','synthetic-fixture-account-flows','fresh-isolated-synthetic-state','independent58-read/flow-checks','birth-verified-own-process-stop'],actualSuppliedControls:{filesystem:'danger-full-access; no restrictions',network:'enabled',mandatoryReviewer:'auto_review',approvalPolicy:null,namedProfile:null},userConfiguration:{permissionProfile:'disabled',filesystem:'unrestricted'},environmentProfile:process.env.CODEX_PERMISSION_PROFILE||null,unavailableNotInferred:['separate AskForApproval value','named permission profile'],notNewAccountGrant:true};
 const d={schema:'offmenu-owner05-interactive-composition/2',ownerThread,sourceRoot,developmentPendingAcceptance:true,accepted:false,inputs,mock,authority,app:{root:path.join(m.root,'app'),commit:inputPins['02'],artifact:m.artifact,schemas:m.schemas},scenario:'success',pins:inputPins,compositionSha256:m.compositionSha256,qualifiedAt:new Date().toISOString(),blockedFeatures:['real Google authorize/callback','real provider calls/credentials','real corpus source admission/transport','native device access','extension install']};
 const file=path.join(m.root,`composition-${JSON.parse(readFileSync(mock.path)).custody.pid}.json`);await put(file,JSON.stringify(d,null,2)+'\n');return {path:file,sha256:sha(file),root:m.root};
}
export function validateDescriptorTime(d,r){
 const qualified=Date.parse(d.qualifiedAt),mockQualified=Date.parse(r.qualifiedAt),now=Date.now();
 // Same host clock; no tolerance and no implicit rolling expiry for a live preview.
 requireThat(typeof d.qualifiedAt==='string'&&Number.isFinite(qualified)&&Number.isFinite(mockQualified)&&qualified>=mockQualified&&qualified<=now,'descriptor qualification before mock/future/invalid');
 if(d.expiresAt!==undefined)requireThat(typeof d.expiresAt==='string'&&Number.isFinite(Date.parse(d.expiresAt))&&Date.parse(d.expiresAt)>now&&Date.parse(d.expiresAt)>=qualified,'expired descriptor qualification');
}
function validateAppBinding(d,m){
 requireThat(d.app?.commit===inputPins['02']&&d.app.root===path.join(m.root,'app')&&JSON.stringify(d.app.schemas)===JSON.stringify(m.schemas),'app commit/root/schema binding');
}
export async function loadInteractive(env=process.env,{probe=true}={}){
 if(!env.OFFMENU_DEV_INTERACTIVE&&!env.OFFMENU_DEV_INTERACTIVE_SHA256)return null;
 requireThat(!env.OFFMENU_DEV_COMPOSITION&&!env.OFFMENU_DEV_CANDIDATE_SOURCE,'modes cannot be mixed');const ref={path:env.OFFMENU_DEV_INTERACTIVE,sha256:env.OFFMENU_DEV_INTERACTIVE_SHA256};requireThat(ref.path&&sha(ref.path)===ref.sha256,'interactive descriptor hash');const d=JSON.parse(readFileSync(ref.path));
 requireThat(d.schema==='offmenu-owner05-interactive-composition/2'&&d.ownerThread===ownerThread&&d.sourceRoot===sourceRoot&&d.accepted===false,'explicit owner/schema/development scope');const m=verifyInputs(d.inputs);validateAppBinding(d,m);requireThat(JSON.stringify(d.pins)===JSON.stringify(inputPins)&&d.compositionSha256===m.compositionSha256&&JSON.stringify(d.app.artifact)===JSON.stringify(m.artifact),'descriptor input/artifact binding');
 requireThat(d.authority.boundSession===ownerThread&&d.authority.boundRoot===sourceRoot&&JSON.stringify(d.authority.pins)===JSON.stringify(inputPins)&&d.authority.actualSuppliedControls.mandatoryReviewer==='auto_review'&&d.authority.compositionSha256===m.compositionSha256&&JSON.stringify(d.authority.applicationArtifact)===JSON.stringify(m.artifact),'grant/session/policy binding');
 requireThat(sha(d.mock.path)===d.mock.sha256,'owned mock receipt hash');const receipt=JSON.parse(readFileSync(d.mock.path));requireThat(receipt.ownerThread===ownerThread&&receipt.sourceOwner==='06'&&receipt.sourceCommit===inputPins['06']&&receipt.status==='qualified-live'&&receipt.identity.assertions===176&&receipt.resetCheck.assertions===2,'actual owned Java qualification');
 validateTaskAdmission(d.authority,m);await validateQualification(receipt,m,{live:probe});validateDescriptorTime(d,receipt);
 if(!probe)return {descriptor:d,descriptorSha256:ref.sha256,qualifiedContext:'Dry-run only; live runtime not probed'};
 const runtime=await import(pathToFileURL(path.join(m.mockRoot||path.join(m.root,'mock'),'dev/wiremock/runtime.mjs'))),adapter=await import(pathToFileURL(path.join(m.mockRoot||path.join(m.root,'mock'),'dev/wiremock/adapter.mjs'))),fixtures=await import(pathToFileURL(path.join(m.mockRoot||path.join(m.root,'mock'),'dev/wiremock/fixtures.mjs')));
 const check=async()=>{validateAppBinding(d,m);validateDescriptorTime(d,receipt);validateTaskAdmission(d.authority,m);await validateQualification(receipt,m,{live:true});requireThat(sha(receipt.nativeCustody.path)===receipt.nativeCustody.sha256,'native custody receipt');requireThat(receipt.custody.cwd===(m.mockRoot||path.join(m.root,'mock'))&&receipt.custody.root.startsWith(path.join(m.mockRoot||path.join(m.root,'mock'),'dev/wiremock/.runtime/run-')),'actual private mock root');await runtime.assertOwner(receipt.custody);for(const name of ['adapter.mjs','fixtures.mjs','mappings.mjs','contracts.json','runtime-lock.json','runtime.mjs']){const f=m.files.find(f=>f.part==='mock'&&f.path==='dev/wiremock/'+name);requireThat(sha(path.join(m.mockRoot||path.join(m.root,'mock'),f.path))===f.sha256,'mock source changed');}};
 await check();const original=adapter.createOutboundAdapter({wiremockOrigin:`http://127.0.0.1:${receipt.custody.port}`,scenario:'success'});
 const guarded=guardedOutbound({adapter:original,contractFor:adapter.contractFor,check});
 const service=async request=>{const u=new URL(request.url);if(u.hostname==='offmenu-accounts.netlify.app'&&u.pathname.startsWith('/.netlify/identity/')){const suffix=u.pathname.slice('/.netlify/identity/'.length);if(!((request.method==='GET'&&['settings','user'].includes(suffix))||(request.method==='POST'&&['token','logout'].includes(suffix))))return WorkerResponse.json({error:'DEV_AUTH_FLOW_BLOCKED',synthetic:true},{status:501,headers:{'X-OffMenu-Dev-Mock':'wiremock'}});}return guarded(request);};
 return {descriptor:d,descriptorSha256:ref.sha256,outboundService:service,bindings:fixtures.BINDINGS(),runtime:receipt,check,qualifiedContext:'Interactive owner05 private overlay; independent58 acceptance pending'};
}
if(process.argv[1]&&path.resolve(process.argv[1])===fileURLToPath(import.meta.url)&&process.argv[2]==='build')console.log(JSON.stringify(await buildInteractive(),null,2));
