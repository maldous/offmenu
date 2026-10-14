import {Miniflare, Response} from 'miniflare';
import {readFile, appendFile, writeFile, mkdir, access} from 'node:fs/promises';
import path from 'node:path';
import net from 'node:net';
import {execFileSync} from 'node:child_process';
import {configuration,processBirth,loadComposition,loadCandidateApplication,candidatePins,initializeCandidateSchema} from './dev-lifecycle.mjs';
import {loadInteractive,inputPins} from './interactive-preview.mjs';
for(const key of Object.keys(process.env))if(key.startsWith('GIT_'))delete process.env[key];
const config=configuration();
const audit=event=>appendFile(path.join(config.runRoot,'mock-audit.jsonl'),JSON.stringify({at:new Date().toISOString(),...event})+'\n');
const dryRun=process.argv.includes('--dry-run');
const candidateApp=loadCandidateApplication();
const interactive=await loadInteractive(process.env,{probe:!dryRun});
const composition=interactive||await loadComposition(process.env,{probe:!dryRun,onEvent:audit});
if(dryRun){console.log(JSON.stringify({...config,composition:composition?{mode:'pinned-synthetic',descriptorSha256:composition.descriptorSha256,runtimeProbe:'not performed; dry-run is not readiness'}:{mode:candidateApp?'deny-all-candidate':'deny-all'},application:candidateApp||composition?.descriptor.app||null},null,2));process.exit(0);}

const {sourceRoot:root,runRoot:home,stateId,statePath,receiptPath,ownerThread,runId,port}=config;
process.chdir(root);
// Missing local build must fail before reserving a run or touching state.
const application=composition?.descriptor.app||candidateApp;
const authorPins=interactive?inputPins:candidatePins;
const compositionMode=composition?'pinned-synthetic':candidateApp?'deny-all-candidate':'deny-all';
const artifactPath=application?.artifact.path||path.join(root,'dist/worker.mjs');
await access(artifactPath);
// Check loopback ownership before starting workerd or touching synthetic D1.
await new Promise((resolve,reject)=>{const probe=net.createServer();probe.once('error',reject);probe.listen(port,'127.0.0.1',()=>probe.close(resolve));});
await mkdir(path.dirname(home),{recursive:true});
await mkdir(home); // Exclusive run reservation; never overwrite or adopt another run.
await mkdir(statePath); // Fresh state only; retained and prior namespaces stay untouched.
const sourceCommit=execFileSync('git',['rev-parse','HEAD'],{cwd:root,encoding:'utf8'}).trim();
const receipt={pid:process.pid,ownerThread,runId,...processBirth(process.pid),sourceRoot:root,sourceCommit,stateId,statePath,port,schema:'offmenu.worker05.lifecycle.v2',owner:'worker-05',processOwner:'worker-05',applicationArtifact:application?.artifact||null,applicationArtifactSha256:application?.artifact?.sha256||null,authorPins:application?{...authorPins}:null,freshState:true,stateNamespace:stateId,lifecycleLeaseId:runId+'-'+process.pid+'-'+processBirth(process.pid).startTicks,accepted:false,candidateStatus:'isolated-compatibility-only',compositionMode,candidateSourceSha256:application?.source?.sha256||null,pins:candidateApp||composition?{...authorPins}:null,mode:composition?'pinned-synthetic-mocks':candidateApp?'isolated-candidate-no-live-outbound':'isolated-no-live-outbound',compositionSha256:composition?.descriptorSha256||null,applicationCommit:application?.commit||sourceCommit,developmentCompatibilityDate:'2026-08-06',productionCompatibilityDate:'2026-10-12',interactive:!!interactive,qualifiedContext:interactive?.qualifiedContext||null,grantBinding:interactive?.descriptor.authority||null,blockedFeatures:interactive?.descriptor.blockedFeatures||null,startedAt:new Date().toISOString(),status:'starting'};
await writeFile(receiptPath,JSON.stringify(receipt,null,2)+'\n');
const record=async changes=>{Object.assign(receipt,changes);await writeFile(receiptPath,JSON.stringify(receipt,null,2)+'\n');};
const entryPath=application?path.join(home,'dev-entry.mjs'):path.join(root,'dev-entry.mjs');
if(application){
 const entry=await readFile(path.join(root,'dev-entry.mjs'),'utf8');
 await writeFile(entryPath,entry.replace("'./dist/worker.mjs'",JSON.stringify(artifactPath)),{flag:'wx'});
}
const mf=new Miniflare({host:'127.0.0.1',port,modules:true,scriptPath:entryPath,modulesRoot:'/',compatibilityDate:'2026-08-06',compatibilityFlags:['nodejs_compat'],cf:{country:'AU'},d1Databases:{DB:'offmenu-development-synthetic'},d1Persist:statePath,bindings:{...(interactive?.bindings||{}),DEV_SOURCE_COMMIT:sourceCommit,DEV_STATE_ID:stateId,DEV_OWNER_THREAD:ownerThread,DEV_RUN_ID:runId,DEV_COMPOSITION:compositionMode,DEV_COMPOSITION_SHA256:composition?.descriptorSha256||'',DEV_APP_COMMIT:application?.commit||sourceCommit,DEV_APPLICATION_ARTIFACT:JSON.stringify(application?.artifact||null),DEV_APPLICATION_ARTIFACT_SHA256:application?.artifact?.sha256||'',DEV_AUTHOR_PINS:application?JSON.stringify(authorPins):'null',DEV_INTERACTIVE:!!interactive,DEV_QUALIFIED_CONTEXT:interactive?.qualifiedContext||'',DEV_BLOCKED_FEATURES:JSON.stringify(interactive?.descriptor.blockedFeatures||null)},
  outboundService:composition?.outboundService|| (async request=>{
    const url=new URL(request.url);
    await appendFile(path.join(home,'outbound-blocked.jsonl'),JSON.stringify({at:new Date().toISOString(),method:request.method,origin:url.origin,path:url.pathname,result:'blocked-unmatched-no-live-passthrough'})+'\n');
    return Response.json({error:'DEV_OUTBOUND_BLOCKED',message:'No local mock contract is connected for this request.',origin:url.origin,path:url.pathname},{status:501});
  })
});
let closing=false;
async function stop(){if(closing)return;closing=true;await mf.dispose();await record({status:'stopped',stoppedAt:new Date().toISOString()});console.log('Development server stopped');process.exit(0);}
process.on('SIGINT',stop);process.on('SIGTERM',stop);
// Terminal command avoids competing runtime signal-exit hooks.
process.stdin.setEncoding('utf8');
process.stdin.on('data',data=>{if(data.trim()==='stop')void stop();});
try {
const db=await mf.getD1Database('DB');
const schemaRoot=application?.root||root;
if(application)await initializeCandidateSchema(db,schemaRoot);
else for(const file of ['cloud/schema.sql','cloud/catalogue-schema.sql'])await db.exec(await readFile(path.join(schemaRoot,file),'utf8'));
await db.prepare('INSERT INTO catalogue(kind,id,country,document,search_text,version) VALUES(?,?,?,?,?,?) ON CONFLICT(kind,id) DO NOTHING').bind('country','dev:AU','AU',JSON.stringify({id:'dev:AU',code:'AU',name:'Australia (synthetic development record)',countryCode:'AU',starterLines:[],source:'dev-fixture'}),'australia synthetic development','development-fixture-1').run();
const url=await mf.ready;
await record({status:'ready',url:String(url)});
console.log(JSON.stringify(receipt));
} catch(error) {
  await mf.dispose();await record({status:'failed',failedAt:new Date().toISOString(),error:error.message});throw error;
}
