import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {readFileSync,readlinkSync} from 'node:fs';
export const ownerThread='01a138a5-6210-7ad3-af85-b50eb97eaf38';
export const sourceRoot=path.dirname(fileURLToPath(import.meta.url));
export const externalRoot='/home/user/src/offmenu-data/dev-preview-20261014';
export const receiptRoot=path.join(externalRoot,'workers','worker-05','runs');
export function configuration(env=process.env) {
 const runId=env.OFFMENU_DEV_RUN;
 if(!runId||!/^[a-zA-Z0-9][a-zA-Z0-9_-]{0,63}$/.test(runId))throw new Error('Set OFFMENU_DEV_RUN to a new short alphanumeric run ID.');
 if(env.OFFMENU_DEV_STATE)throw new Error('OFFMENU_DEV_STATE is legacy-only; Worker 05 uses a fresh namespace per run.');
 const port=Number(env.OFFMENU_DEV_PORT||8787);
 if(!Number.isInteger(port)||port<1024||port>65535)throw new Error('Invalid OFFMENU_DEV_PORT.');
 const runRoot=path.join(receiptRoot,runId);
 const stateId=`worker-05-${runId}`;
 return {ownerThread,sourceRoot,runId,port,runRoot,receiptPath:path.join(runRoot,'current-run.json'),stateId,statePath:path.join(externalRoot,'states',stateId),retainedStatePath:path.join(externalRoot,'state')};
}
export function processBirth(pid) {
 const stat=readFileSync(`/proc/${pid}/stat`,'utf8');
 const fields=stat.slice(stat.lastIndexOf(')')+2).trim().split(/\s+/);
 return {bootId:readFileSync('/proc/sys/kernel/random/boot_id','utf8').trim(),startTicks:fields[19]};
}
export function verifyReceipt(receipt,config) {
 for(const key of ['ownerThread','sourceRoot','runId','stateId','statePath','port'])if(receipt[key]!==config[key])throw new Error(`Runner ${key} mismatch: refusing to signal.`);
 if(!Number.isInteger(receipt.pid)||receipt.pid<=1||!receipt.bootId||!receipt.startTicks)throw new Error('Missing runner birth identity: refusing to signal.');
}
export function verifyLiveRunner(receipt,config) {
 verifyReceipt(receipt,config);
 const birth=processBirth(receipt.pid);
 if(birth.bootId!==receipt.bootId||birth.startTicks!==receipt.startTicks)throw new Error('Runner birth mismatch: refusing to signal.');
 const cwd=readlinkSync(`/proc/${receipt.pid}/cwd`);
 const args=readFileSync(`/proc/${receipt.pid}/cmdline`,'utf8').split('\0');
 if(cwd!==sourceRoot||!args.some(arg=>arg==='dev-server.mjs'||arg===path.join(sourceRoot,'dev-server.mjs')))throw new Error('Runner cwd/command mismatch: refusing to signal.');
}

// Composition receipts are supplied by the owners after Morgan reviews the pinned tree.
// Hashes identify evidence; they are not a substitute for that management decision.
export const mockOwner='01a138a5-afff-7282-acd3-3a457bb91d24';
export const authOwner='01a138a5-1538-7861-8b0f-d3d28311fc62';
export const mockRoot='/home/user/src/offmenu-workers/worker-06';
const gateway='01a130cd-91c1-73da-9978-889018a100dd';
const mockFiles=['dev/wiremock/adapter.mjs','dev/wiremock/mappings.mjs','dev/wiremock/fixtures.mjs','dev/wiremock/contracts.json','dev/wiremock/runtime-lock.json','package.json','package-lock.json'];
const hex=(value,length)=>typeof value==='string'&&new RegExp(`^[a-f0-9]{${length}}$`).test(value);
function requireField(condition,message){if(!condition)throw new Error(`Composition refused: ${message}`);}
function fresh(record,now){
 const issued=Date.parse(record.qualifiedAt),expires=Date.parse(record.expiresAt);
 requireField(Number.isFinite(issued)&&Number.isFinite(expires)&&issued<=now&&expires>now&&expires-issued<=15*60*1000,'missing/stale qualification (maximum 15 minutes)');
}
export function validateCompositionShape(d,now=Date.now()) {
 requireField(d?.schema==='offmenu-dev-composition/1','descriptor schema');
 requireField(d.approval?.via===gateway&&typeof d.approval.reference==='string'&&d.approval.reference.length>0,'Morgan approval reference via Gateway required');
 requireField(d.app&&(/^\/home\/user\/src\/offmenu-workers\/worker-0[1-8]$/.test(d.app.root)||d.app.source&&d.app.disposition==='isolated-compatibility-only')&&hex(d.app.commit,40),'pinned permanent application source');
 requireField(d.app.artifact?.path===`${d.app.root}/dist/worker.mjs`&&hex(d.app.artifact.sha256,64),'pinned compiled application');
 requireField(d.app.schemas&&['cloud/schema.sql','cloud/catalogue-schema.sql'].every(f=>hex(d.app.schemas[f],64)),'pinned account/catalogue schemas');
 requireField(d.mock?.ownerThread===mockOwner&&d.mock.root===mockRoot&&hex(d.mock.commit,40)&&d.mock.api==='offmenu-mocks/1','Worker 06 owner/source/API');
 requireField(d.mock.files&&mockFiles.every(f=>hex(d.mock.files[f],64)),'complete adapter/dependency checksums');
 requireField(d.mock.receipt&&path.isAbsolute(d.mock.receipt.path)&&hex(d.mock.receipt.sha256,64),'qualified runtime receipt pin');
 requireField(d.auth&&path.isAbsolute(d.auth.path)&&hex(d.auth.sha256,64),'Worker 04 auth contract pin');
 requireField(d.scenario==='success','only success scenario qualified for this lifecycle seam');
 fresh(d,now);
 return d;
}
import {createHash} from 'node:crypto';
import {Response as MiniflareResponse} from 'miniflare';
import {execFileSync} from 'node:child_process';
import {pathToFileURL} from 'node:url';
const digest=(file,algorithm='sha256')=>createHash(algorithm).update(readFileSync(file)).digest('hex');
export function verifyFilePin(file,expected,algorithm='sha256'){requireField(digest(file,algorithm)===expected,'file checksum');}
function pinnedJSON(ref){verifyFilePin(ref.path,ref.sha256);return JSON.parse(readFileSync(ref.path,'utf8'));}
function sourcePin(root,commit){
 requireField(execFileSync('git',['rev-parse','HEAD'],{cwd:root,encoding:'utf8'}).trim()===commit,'source HEAD mismatch');
 requireField(execFileSync('git',['diff','HEAD','--name-only'],{cwd:root,encoding:'utf8'}).trim()==='','tracked source differs from pinned HEAD');
}
export function validateCompositionFiles(d) {
 if(d.app.source)verifyCandidateSource(d.app.source,d.app.root);else sourcePin(d.app.root,d.app.commit);
 sourcePin(mockRoot,d.mock.commit);
 requireField(digest(d.app.artifact.path)===d.app.artifact.sha256,'application artifact checksum');
 for(const [f,h] of Object.entries(d.app.schemas)) {
  requireField(['cloud/schema.sql','cloud/catalogue-schema.sql'].includes(f),'unknown schema');
  requireField(digest(path.join(d.app.root,f))===h,'schema checksum');
 }
 for(const f of mockFiles)requireField(digest(path.join(mockRoot,f))===d.mock.files[f],`mock checksum ${f}`);
 const auth=pinnedJSON(d.auth);let runtime=pinnedJSON(d.mock.receipt);
 if(runtime.schemaVersion===1&&runtime.operation==='status'){
  requireField(d.mock.commit===candidatePins['06']&&d.mock.qualification,'pinned native runtime qualification');
  const q=pinnedJSON(d.mock.qualification);
  requireField(d.mock.qualification.sha256===hashBytes(gitBytes('show',`${candidatePins['06']}:dev/wiremock/identity-verification.json`))&&q.schema==='offmenu-identity-fidelity-verification/1'&&q.semanticsVersion==='offmenu-identity-session/2'&&q.java.representativeScenariosPassed===119&&q.java.identity.assertions===176&&q.java.identity.logoutRevocation===true&&q.java.identity.passwordRevival===true,'native WireMock qualification');
  const at=Date.parse(runtime.at);
  runtime={schema:'offmenu-mock-runtime/1',ownerThread:mockOwner,status:'qualified',api:'offmenu-mocks/1',sourceCommit:d.mock.commit,qualifiedAt:runtime.at,expiresAt:new Date(at+15*60*1000).toISOString(),version:runtime.custody.version,jarSha512:runtime.custody.jarSha512,bootId:runtime.custody.bootId,custody:runtime.custody};
 }
 const lock=JSON.parse(readFileSync(path.join(mockRoot,'dev/wiremock/runtime-lock.json'),'utf8'));
 validateOwnerContracts(d,auth,runtime,lock);
 const c=runtime.custody;
 requireField(digest(c.jar,'sha512')===lock.sha512,'runtime JAR checksum');
 return {auth,runtime};
}
export function validateOwnerContracts(d,auth,runtime,lock) {
 if(auth.schemaVersion===1&&auth.owner==='OffMenu Worker 04'){
  requireField(d.app.source&&d.auth.sha256===hashBytes(gitBytes('show',`${candidatePins['04']}:dev/google-idp/contract.json`))&&auth.isolation.liveFallback===false&&auth.identity.prefix==='/.netlify/identity/'&&auth.checkpoint==='02da1609a0cfc3da249aa69c9717ad25ff06191d','native auth source/boundary');
 }else {
 requireField(auth.schema==='offmenu-dev-auth/1'&&auth.ownerThread===authOwner&&auth.status==='qualified'&&auth.appCommit===d.app.commit&&auth.mockCommit===d.mock.commit,'auth qualification/composition mismatch');
 requireField(auth.mode==='synthetic-only'&&auth.providerAcceptance===false&&auth.sameOriginPath==='/.netlify/identity/'&&auth.upstream==='https://offmenu-accounts.netlify.app/.netlify/identity'&&auth.googleOAuth==='blocked-501'&&auth.profileUpdate==='blocked-501','auth boundary contract');
 requireField(['password','refresh','user'].every(v=>auth.capabilities?.includes(v)),'required synthetic auth capabilities');
 }
 requireField(runtime.schema==='offmenu-mock-runtime/1'&&runtime.ownerThread===mockOwner&&runtime.status==='qualified'&&runtime.api===d.mock.api&&runtime.sourceCommit===d.mock.commit,'runtime owner/source/qualification');
 requireField(runtime.version===lock.version&&runtime.jarSha512===lock.sha512,'runtime version/checksum pin');
 const c=runtime.custody;
 requireField(c&&[1,2].includes(c.schemaVersion)&&Number.isInteger(c.pid)&&c.pid>1&&c.cwd===mockRoot&&Number.isInteger(c.port)&&c.port>=1024&&c.port<=65535&&(c.schemaVersion===1?c.root===`${mockRoot}/dev/wiremock/.runtime/port-${c.port}`:new RegExp(`^${mockRoot}/dev/wiremock/\\.runtime/run-${c.port}-[a-f0-9-]{36}$`).test(c.root))&&path.isAbsolute(c.jar)&&typeof c.token==='string'&&c.token.length>=16&&c.version===lock.version,'runtime custody shape');
 requireField(hex(runtime.bootId?.replaceAll('-',''),32)&&/^\d+$/.test(c.birthTicks),'runtime birth pin');
}
export async function verifyMockRuntime(runtime,now=Date.now()) {
 fresh(runtime,now);
 const c=runtime.custody,birth=processBirth(c.pid);
 if(runtime.nativeCustodyReceipt){requireField(runtime.nativeCustodyReceipt.path===path.join(c.root,'custody.json'),'native custody receipt path');verifyFilePin(runtime.nativeCustodyReceipt.path,runtime.nativeCustodyReceipt.sha256);}
 const native=JSON.parse(readFileSync(path.join(c.root,'custody.json'),'utf8'));
 for(const key of ['schemaVersion','pid','bootId','jarSha512','mappingsSha256','birthTicks','port','jar','root','cwd','token','version','startedAt'])requireField(native[key]===c[key],'native custody differs from qualified receipt');
 requireField(birth.bootId===runtime.bootId&&birth.startTicks===c.birthTicks,'runtime birth mismatch');
 requireField(readlinkSync(`/proc/${c.pid}/cwd`)===mockRoot,'runtime cwd');
 const args=readFileSync(`/proc/${c.pid}/cmdline`,'utf8').split('\0');
 requireField(args.includes(c.jar)&&args[args.indexOf('--root-dir')+1]===c.root&&args[args.indexOf('--port')+1]===String(c.port)&&args[args.indexOf('--bind-address')+1]==='127.0.0.1','runtime command');
 const response=await fetch(`http://127.0.0.1:${c.port}/__offmenu_fixture_health`,{redirect:'error',signal:AbortSignal.timeout(1000)});
 requireField(response.ok&&(await response.json()).custodyToken===c.token,'runtime health token');
}
export function guardedOutbound({adapter,contractFor,check,onEvent=()=>{}}) {
 return async request=>{
  try {
   requireField(Boolean(contractFor(request.url,request.method)),'unknown outbound contract; no live fallback');
   await check();
   const response=await adapter(request);
   requireField(response.headers.get('X-OffMenu-Dev-Mock')==='wiremock'&&!(response.status>=300&&response.status<400),'unmarked/redirect response; no live fallback');
   const url=new URL(request.url);
   await onEvent({blocked:false,host:url.hostname,path:url.pathname,method:request.method,status:response.status});
   return response;
  }catch {
   await onEvent({blocked:true,method:request.method,status:502});
   return MiniflareResponse.json({error:'DEV_COMPOSITION_BLOCKED'},{status:502,headers:{'X-OffMenu-Dev-Mock':'blocked'}});
  }
 };
}
export async function loadComposition(env=process.env,{probe=true,onEvent=()=>{}}={}) {
 if(!env.OFFMENU_DEV_COMPOSITION&&!env.OFFMENU_DEV_COMPOSITION_SHA256)return null;
 requireField(path.isAbsolute(env.OFFMENU_DEV_COMPOSITION||'')&&hex(env.OFFMENU_DEV_COMPOSITION_SHA256,64),'descriptor path/hash must both be supplied');
 const ref={path:env.OFFMENU_DEV_COMPOSITION,sha256:env.OFFMENU_DEV_COMPOSITION_SHA256};
 const d=validateCompositionShape(pinnedJSON(ref)),pins=validateCompositionFiles(d);
 fresh(pins.runtime,Date.now());
 if(probe)await verifyMockRuntime(pins.runtime);
 // Revalidate every imported input after a successful probe, before module evaluation.
 validateCompositionFiles(d);
 if(!probe)return {descriptor:d,descriptorSha256:ref.sha256,auth:pins.auth,runtime:pins.runtime};
 const module=await import(pathToFileURL(path.join(mockRoot,'dev/wiremock/adapter.mjs')).href);
 requireField(typeof module.createOutboundAdapter==='function'&&typeof module.contractFor==='function','adapter API');
 const fixtures=await import(pathToFileURL(path.join(mockRoot,'dev/wiremock/fixtures.mjs')).href);
 if(pins.auth.schemaVersion===1)for(const [id,actor] of Object.entries(pins.auth.actors))for(const key of ['id','token','refreshToken'])requireField(fixtures.ACTORS[id]?.[key]===actor[key],'auth/mock actor mismatch');
 const adapter=module.createOutboundAdapter({wiremockOrigin:`http://127.0.0.1:${pins.runtime.custody.port}`,scenario:d.scenario,onEvent:()=>{}});
 const outboundService=guardedOutbound({adapter,contractFor:module.contractFor,onEvent,check:async()=>{
  validateCompositionShape(d);validateCompositionFiles(d);await verifyMockRuntime(pins.runtime);
 }});
 const service=pins.auth.schemaVersion===1?syntheticAuthBoundary(outboundService):outboundService;
 return {descriptor:d,descriptorSha256:ref.sha256,outboundService:service,auth:pins.auth,runtime:pins.runtime};
}

export const candidatePins={
 '02':'1469cea8b6c91f705de9c4c8aee91c4c4d723660',
 '04':'5102bc7a42d7eab37522301705335acdf75c7b13',
 '05':'e513539ed952e1e4271529206d5274553221f6b5',
 '06':'9b31f7d4de21dd30add0c49b038e5ac31413ec5d',
 '08':'223ea760124b8fea642c29ed549181d2e5a02cb4'
};
const mainPin='8652b312ce7989c5e4f2d49ae765d5d8daf5841d',thirdPin='84c4732af985965c3e5b00383acaa662bdd52ea6';
const gitBytes=(...args)=>execFileSync('git',args,{cwd:sourceRoot,maxBuffer:32*1024*1024});
const hashBytes=value=>createHash('sha256').update(value).digest('hex');
export function verifyCandidateSource(ref,root){
 const s=pinnedJSON(ref);
 requireField(s.schema==='offmenu-local-candidate-source/1'&&s.disposition==='isolated-compatibility-only'&&s.root===root,'candidate source/disposition');
 requireField(root.startsWith(path.join(externalRoot,'workers/worker-05/candidates')+'/')&&path.resolve(root)===root,'candidate root');
 requireField(JSON.stringify(s.pins)===JSON.stringify(candidatePins)&&s.main===mainPin&&s.thirdParty===thirdPin&&s.compositionManifestSha256==='31ad2805f7df39660ede64dd5468aac82d9cced681d5e04e924963fa1db2ef9a','candidate selection pins');
 requireField(s.files.length>0&&s.files.length<300&&hex(s.manifestSha256,64),'bounded source manifest');
 const names=new Set();
 for(const f of s.files){
  requireField(typeof f.path==='string'&&!path.isAbsolute(f.path)&&!f.path.split('/').includes('..')&&!names.has(f.path),'candidate path');names.add(f.path);
  requireField(digest(path.join(root,f.path))===f.sha256,'candidate input checksum');
  if(f.gitBlob){requireField([mainPin,thirdPin,candidatePins['04']].includes(f.sourceCommit),'unselected source revision');requireField(hashBytes(gitBytes('cat-file','blob',f.gitBlob))===f.sha256&&gitBytes('rev-parse',`${f.sourceCommit}:${f.path}`).toString().trim()===f.gitBlob,'candidate Git source');}
 }
 requireField(hashBytes(JSON.stringify(s.files))===s.manifestSha256,'candidate manifest hash');
 return s;
}
export async function buildCandidate(){
 const helperPath='/home/user/src/offmenu-workers/worker-02/scripts/lib/third-party-compatibility.mjs';
 requireField(hashBytes(gitBytes('show',`${candidatePins['02']}:scripts/lib/third-party-compatibility.mjs`))===digest(helperPath),'pinned Worker 02 composer');
 const {snapshot,composeSnapshots,blob}=await import(pathToFileURL(helperPath).href);
 const base=gitBytes('merge-base',mainPin,thirdPin).toString().trim();
 const composed=composeSnapshots(snapshot(sourceRoot,base),snapshot(sourceRoot,mainPin),snapshot(sourceRoot,thirdPin));
 const merged=composeSnapshots(snapshot(sourceRoot,'65805762cf398202a765d1dc9d8ec26cfe035348'),composed.entries,snapshot(sourceRoot,candidatePins['04']));
 const {mkdir,writeFile,symlink}=await import('node:fs/promises');
 const {randomUUID}=await import('node:crypto');
 const root=path.join(externalRoot,'workers/worker-05/candidates',randomUUID());await mkdir(root,{recursive:true});
 const files=[];let bytes=0;
 const put=async(name,data,metadata={})=>{bytes+=Buffer.byteLength(data);requireField(bytes<=16*1024*1024,'candidate exceeds 16MiB');await mkdir(path.dirname(path.join(root,name)),{recursive:true});await writeFile(path.join(root,name),data,{flag:'wx'});files.push({path:name,sha256:hashBytes(data),...metadata});};
 const assetsNames=['index.html','data-workspace.html','style.css','icon.svg','manifest.webmanifest','manifest-ar.webmanifest'];
 const specific=new Set([...assetsNames.map(f=>'public/'+f),'public/locales/en.json','public/recipe-ingredient-aliases.json','research/manifest.json','netlify-return/callback-policy.js']);
 for(const [name,entry] of merged.entries){
  if(!specific.has(name)&&!/^((cloud|corpus)\/.*\.mjs|cloud\/.*\.sql|public\/.*\.js)$/.test(name))continue;
  await put(name,blob(sourceRoot,entry),{sourceCommit:entry.commit,gitBlob:entry.oid});
 }
 await put('package.json','{"type":"module","private":true}\n');await symlink(path.join(sourceRoot,'node_modules'),path.join(root,'node_modules'),'dir');
 const {build}=await import('esbuild');
 const assets={'recipes.json':'[]','afcd-nutrient-details.json':'{}','scanner.wasm':'','retailer-extension.zip':''};
 for(const name of assetsNames)assets[name]=readFileSync(path.join(root,'public',name),'utf8');
 for(const [name,format] of [['app','esm'],['data-workspace','esm'],['sw','iife']]){
  const result=await build({entryPoints:[path.join(root,'public',name+'.js')],bundle:true,minify:true,write:false,format,platform:'browser'});assets[name+'.js']=result.outputFiles[0].text;
 }
 const release={sourceCommit:mainPin,candidatePins,compositionManifest:merged.manifestSHA256,isolatedCandidate:true};
 await put('cloud/generated.mjs','const ASSETS='+JSON.stringify(assets)+';\nconst RELEASE='+JSON.stringify(release)+';\n'+readFileSync(path.join(root,'cloud/handler.mjs'),'utf8'));
 const built=await build({entryPoints:[path.join(root,'cloud/generated.mjs')],bundle:true,minify:true,write:false,format:'esm',platform:'browser'});
 await put('dist/worker.mjs',built.outputFiles[0].text);
 files.sort((a,b)=>a.path.localeCompare(b.path));
 const source={schema:'offmenu-local-candidate-source/1',disposition:'isolated-compatibility-only',root,pins:candidatePins,base,main:mainPin,thirdParty:thirdPin,mainTree:gitBytes('rev-parse',`${mainPin}^{tree}`).toString().trim(),idpTree:gitBytes('rev-parse',`${candidatePins['04']}^{tree}`).toString().trim(),compositionManifestSha256:merged.manifestSHA256,bytes,files,manifestSha256:hashBytes(JSON.stringify(files)),syntheticAssets:['recipes.json','afcd-nutrient-details.json','scanner.wasm','retailer-extension.zip'],corpus07:'PENDING'};
 const manifest=path.join(root,'candidate-source.json');await writeFile(manifest,JSON.stringify(source,null,2)+'\n',{flag:'wx'});
 return {root,commit:mainPin,artifact:{path:path.join(root,'dist/worker.mjs'),sha256:digest(path.join(root,'dist/worker.mjs'))},schemas:Object.fromEntries(['cloud/schema.sql','cloud/catalogue-schema.sql'].map(f=>[f,digest(path.join(root,f))])),source:{path:manifest,sha256:digest(manifest)},disposition:source.disposition};
}

export async function createCandidateDescriptor(runtimeReceipt){
 requireField(path.isAbsolute(runtimeReceipt),'explicit Worker 06 status receipt');
 const app=await buildCandidate();
 const native=pinnedJSON({path:runtimeReceipt,sha256:digest(runtimeReceipt)});
 requireField(native.operation==='status'||native.schema==='offmenu-mock-runtime/1'&&native.status==='qualified','fresh live native status or qualified runtime receipt required');
 const d={schema:'offmenu-dev-composition/1',disposition:'isolated-compatibility-only',approval:{via:gateway,reference:'Morgan selected immutable 04/05/06/08 via setup 01a137cf; isolated candidate compatibility only'},qualifiedAt:new Date().toISOString(),expiresAt:new Date(Date.now()+15*60*1000).toISOString(),scenario:'success',app,
  mock:{root:mockRoot,ownerThread:mockOwner,commit:candidatePins['06'],api:'offmenu-mocks/1',files:Object.fromEntries(mockFiles.map(f=>[f,digest(path.join(mockRoot,f))])),receipt:{path:runtimeReceipt,sha256:digest(runtimeReceipt)},qualification:{path:path.join(mockRoot,'dev/wiremock/identity-verification.json'),sha256:digest(path.join(mockRoot,'dev/wiremock/identity-verification.json'))}},
  auth:{path:'/home/user/src/offmenu-workers/worker-04/dev/google-idp/contract.json',sha256:digest('/home/user/src/offmenu-workers/worker-04/dev/google-idp/contract.json')},corpus07:'PENDING',pins:candidatePins};
 validateCompositionShape(d);const {runtime}=validateCompositionFiles(d);await verifyMockRuntime(runtime);
 const descriptorPath=path.join(app.root,'composition.json');
 const {writeFile}=await import('node:fs/promises');await writeFile(descriptorPath,JSON.stringify(d,null,2)+'\n',{flag:'wx'});
 return {descriptorPath,descriptorSha256:digest(descriptorPath),candidateRoot:app.root,artifactSha256:app.artifact.sha256,source:d.app.source};
}
if(process.argv[1]&&path.resolve(process.argv[1])===fileURLToPath(import.meta.url)&&process.argv[2]==='candidate')console.log(JSON.stringify(await createCandidateDescriptor(process.argv[3]),null,2));

export function syntheticAuthBoundary(outbound){
 return async request=>{
  const u=new URL(request.url);
  if(u.hostname==='offmenu-accounts.netlify.app'&&u.pathname.startsWith('/.netlify/identity/')){
   const suffix=u.pathname.slice('/.netlify/identity/'.length);
   if(!((request.method==='GET'&&['settings','user'].includes(suffix))||(request.method==='POST'&&['token','logout'].includes(suffix))))return MiniflareResponse.json({error:'DEV_AUTH_FLOW_PENDING',synthetic:true},{status:501,headers:{'X-OffMenu-Dev-Mock':'wiremock'}});
  }
  return outbound(request);
 };
}

export function loadCandidateApplication(env=process.env){
 if(!env.OFFMENU_DEV_CANDIDATE_SOURCE&&!env.OFFMENU_DEV_CANDIDATE_SHA256)return null;
 requireField(!env.OFFMENU_DEV_COMPOSITION&&!env.OFFMENU_DEV_COMPOSITION_SHA256,'explicit candidate deny-all and mock composition cannot be mixed');
 requireField(path.isAbsolute(env.OFFMENU_DEV_CANDIDATE_SOURCE||'')&&hex(env.OFFMENU_DEV_CANDIDATE_SHA256,64),'candidate source path/hash pair');
 const ref={path:env.OFFMENU_DEV_CANDIDATE_SOURCE,sha256:env.OFFMENU_DEV_CANDIDATE_SHA256};
 const source=pinnedJSON(ref);verifyCandidateSource(ref,source.root);
 const file=name=>{const entry=source.files.find(f=>f.path===name);requireField(entry,'candidate artifact/schema missing');return entry.sha256;};
 return {root:source.root,commit:source.main,artifact:{path:path.join(source.root,'dist/worker.mjs'),sha256:file('dist/worker.mjs')},schemas:Object.fromEntries(['cloud/schema.sql','cloud/catalogue-schema.sql'].map(f=>[f,file(f)])),source:ref,disposition:source.disposition};
}

export async function initializeCandidateSchema(db,root){
 const {DatabaseSync}=await import('node:sqlite');
 const schema=new DatabaseSync(':memory:');
 try{
  for(const file of ['cloud/schema.sql','cloud/catalogue-schema.sql'])schema.exec(readFileSync(path.join(root,file),'utf8'));
  const statements=schema.prepare("SELECT sql FROM sqlite_master WHERE sql IS NOT NULL AND name NOT LIKE 'sqlite_%' ORDER BY CASE type WHEN 'table' THEN 0 ELSE 1 END,name").all();
  for(const {sql} of statements)await db.prepare(sql.replace(/^CREATE TABLE /,'CREATE TABLE IF NOT EXISTS ').replace(/^CREATE INDEX /,'CREATE INDEX IF NOT EXISTS ')).run();
  return statements.length;
 }finally{schema.close();}
}
