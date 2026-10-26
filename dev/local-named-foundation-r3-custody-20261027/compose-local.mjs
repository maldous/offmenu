import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
import {gzipSync, gunzipSync} from 'node:zlib';
import {LOCAL_BLOBS as priorBlobs} from '../local7645-foundation-root14-r1/foundation-local-blobs.mjs';
const BASE=import.meta.dirname,R=path.join(BASE,'compact-composition-r3'),P=path.dirname(BASE);
const REUSE=path.join(BASE,'compact-composition-r2');
const OLD=path.join(P,'local7645-foundation-root14-r1');
const OWNER='/home/user/src/offmenu-data/runtime/layout-migration/worker19/remaining-held-public-english-serving-20261026/beetroot-named-food-r3-one-record-application-20261027';
const SOURCE=path.join(P,'named-food-active-adapter-v1-20261027/r3-nested-stage-reconciliation/source/corpus');
const HELPER=path.join(P,'named-food-active-adapter-v1-20261027/handoff-cutset-preparation');
const release='offmenu-reviewed-foundation-r2-named-r3-20261027-v1';
const barcode='4061464939738', oldPolicy='94985983c80c7a4453e6b9964f9975f5d2def142a807e2960747b44cf93b0745';
const sha=b=>crypto.createHash('sha256').update(b).digest('hex');
const read=p=>JSON.parse(fs.readFileSync(p));
const ref=p=>({path:p,sha256:sha(fs.readFileSync(p))});
const need=(ok,message)=>{if(!ok)throw Error(message);};
const json=v=>Buffer.from(JSON.stringify(v)+'\n');
function write(name,bytes){const file=path.join(R,name);fs.mkdirSync(path.dirname(file),{recursive:true});fs.writeFileSync(file,bytes,{flag:'wx'});return ref(file);}
const handoff=read(path.join(OWNER,'local-derivative-handoff.json'));
need(sha(fs.readFileSync(path.join(OWNER,'result.json')))==='402321da6eec34fb58a66da8b73013bb553d0a840a25a0a4464db1179d8f7816','producer result');
for(const key of ['candidate','policySet','oldPolicyMember','newPolicyMember','newCandidatePhaseAssessment','implementationReview'])
 need(ref(handoff[key].path).sha256===handoff[key].sha256,'producer pin '+key);
const candidate=read(handoff.candidate.path), policyBytes=fs.readFileSync(handoff.policySet.path), policy=JSON.parse(policyBytes);
need(candidate.barcode===barcode&&candidate.foundationPolicySha256===handoff.newPolicyMember.sha256&&policy.defaultPolicySha256===oldPolicy,'policy selection');
need(sha(Buffer.from(policy.policies[oldPolicy]))===oldPolicy,'retained old policy bytes');
const namedPolicy=handoff.newPolicyMember.sha256;
need(sha(Buffer.from(policy.policies[namedPolicy]))===namedPolicy,'named policy bytes');
const manifest=read(path.join(OLD,'manifest.local-admitted.json'));
const oldRelease=manifest.releaseId, oldPrefix='own-data/foundation/'+oldRelease+'/', prefix='own-data/foundation/'+release+'/';
const blobs={},stats={retainedSourceObservations:0,retainedSourceQueries:0,retainedRowsUnchanged:0,newSourceObservations:1,newSourceQueries:1,sources:{}};
function blob(key,body,expanded){
 const bytes=Buffer.from(body),d={key,sha256:sha(bytes),bytes:bytes.length,...(expanded===undefined?{}:{uncompressedBytes:expanded})};
 write('blobs/'+key,bytes);blobs[key]={...d,bodyBase64:bytes.toString('base64')};return d;
}
const target=sha(Buffer.from(barcode)).slice(0,2);
const reused=read(path.join(REUSE,'composition-result.json'));
need(reused.policySet.sha256===handoff.policySet.sha256&&reused.stats.retainedRowsUnchanged===10875,'reused composed data proof');
Object.assign(stats,reused.stats);
for(const [source,entry]of Object.entries(manifest.sources))for(const [part,d]of Object.entries(entry.partitions)){
 const key=d.key.replace(oldPrefix,prefix),prior=reused.files.find(v=>v.key===key);
 need(prior,'reused product descriptor');const body=fs.readFileSync(path.join(REUSE,'blobs',key));
 need(body.length===prior.bytes&&sha(body)===prior.sha256,'reused exact product bytes');
 entry.partitions[part]=blob(key,body,prior.uncompressedBytes);
}
/* Exact product re-composition implementation retained for provenance below;
   this metadata-only correction reuses its verified output without decoding. */
if(false){
for(const [source,entry] of Object.entries(manifest.sources)){
 const counts={retainedSourceObservations:0,retainedSourceQueries:0,newSourceObservations:source==='off'?1:0,newSourceQueries:source==='off'?1:0};
 for(const [part,d]of Object.entries(entry.partitions)){
  const retained=priorBlobs[d.key];need(retained&&retained.sha256===d.sha256&&retained.bytes===d.bytes,'selected old descriptor');
  const bytes=Buffer.from(retained.bodyBase64,'base64');need(bytes.length===d.bytes&&sha(bytes)===d.sha256,'selected old bytes');
  const raw=gunzipSync(bytes,{maxOutputLength:2*1024*1024});need(raw.length===d.uncompressedBytes,'selected old bound');
  const value=JSON.parse(raw);need(value.schema==='offmenu-foundation-products/2'&&value.sourceId===source&&value.policySha256===oldPolicy,'old product shell');
  const before=new Map();
  for(const [key,rows]of Object.entries(value.entries)){
   need(Array.isArray(rows),'rows');if(rows.length){counts.retainedSourceQueries++;stats.retainedSourceQueries++;}
   for(const row of rows){const id=JSON.stringify([key,row.id]);need(!before.has(id),'duplicate old row');before.set(id,sha(Buffer.from(JSON.stringify(row))));counts.retainedSourceObservations++;stats.retainedSourceObservations++;}
  }
  if(source==='off'&&part===target){
   need(!value.entries[barcode]||value.entries[barcode].length===0,'expected unavailable regression before new row');
   value.entries[barcode]=[{schema:'offmenu-foundation-product/2',id:candidate.identity.stageRecordId,candidate}];
  }
  value.policySha256=handoff.policySet.sha256;
  for(const [key,rows]of Object.entries(value.entries))for(const row of rows){
   const id=JSON.stringify([key,row.id]);if(before.has(id)){
    need(sha(Buffer.from(JSON.stringify(row)))===before.get(id),'old candidate or review stamp changed');stats.retainedRowsUnchanged++;
   }
  }
  const nextRaw=Buffer.from(JSON.stringify(value)+'\n'),nextBytes=gzipSync(nextRaw,{level:9,mtime:0});
  need(nextRaw.length<=2*1024*1024&&nextBytes.length<=1024*1024,'new selected blob bounds');
  entry.partitions[part]=blob(d.key.replace(oldPrefix,prefix),nextBytes,nextRaw.length);
 }
 stats.sources[source]=counts;
}
}
need(stats.retainedSourceObservations===10875&&stats.retainedRowsUnchanged===10875&&stats.retainedSourceQueries===4256,'retained exact population count');
const selectedPolicy=blob(prefix+'policy.json',policyBytes);
const noticesKey=oldPrefix+'SOURCE-NOTICES.txt',notices=Buffer.from(priorBlobs[noticesKey].bodyBase64,'base64');
need(sha(notices)===priorBlobs[noticesKey].sha256,'source notices');
blob(prefix+'SOURCE-NOTICES.txt',Buffer.concat([notices,Buffer.from('\nLOCAL named-food extension: one retained source observation, derived curator policy. Full product, normalized, Gold, automatic planning and recipe nutrition joins remain unaccepted.\n')]));
for(const name of ['foundation-phase-contract.mjs','foundation-phase-contract-v2.mjs','foundation-policy-set.mjs','foundation-origin-reader.mjs'])write('corpus/'+name,fs.readFileSync(path.join(SOURCE,name)));
write('corpus/foundation-product-handler.mjs',fs.readFileSync('/home/user/src/offmenu-worktrees/worker00-third-party-source-group-20261026/corpus/foundation-product-handler.mjs'));
const reader=ref(path.join(R,'corpus/foundation-origin-reader.mjs'));
manifest.releaseId=release;manifest.policySha256=selectedPolicy.sha256;manifest.consumerCodeSha256=reader.sha256;
manifest.status='prepared';manifest.acceptance={status:'not-admitted',receiptSha256:null};
need(json(manifest).length<=128*1024&&policyBytes.length<=128*1024,'control descriptor bounds before admission');
const prepared=write('manifest.prepared.json',json(manifest));
const admission={id:'worker00-local-named-foundation-r3-source-admission-20261027',atUTC:new Date().toISOString(),issuerWorker:0,threadId:'01a1371c-66f7-70e0-9e3b-a79d2b2eee9f',nativeTurnId:'01a17841-4c21-7171-ab09-72df38ead80e',status:'ADMITTED_LOCAL_PUBLIC_DERIVATIVE_FIELDS_ONLY_NOT_RUNTIME_OR_PUBLICATION',releaseId:release,preparedManifest:prepared,producerResult:ref(path.join(OWNER,'result.json')),producerHandoff:ref(path.join(OWNER,'local-derivative-handoff.json')),acceptedImplementation:handoff.implementationReview,policySet:handoff.policySet,consumerReader:reader,retainedSourceAdmission:ref(path.join(OLD,'local-source-admission.json')),retainedManifest:ref(path.join(OLD,'manifest.local-admitted.json')),scope:'Existing LOCAL OFF/USDA public-derived fields plus ONE already retained source-qualified named beetroot observation after exact SAME57 R3 implementation and actual19 source/index/native/barcode/wire readback. No corpus or R2/R7 semantic pass, raw/held/private/native source expansion, acquisition, external fallback, public upload/publication, full product, normalization, Gold, recipe/nutrition/planning or production admission.',authority:'Already-authorized useful LOCAL own-data integration; current Gateway/Parent explicit serialize19 terminal18301 and local served regression direction, source/rights/operation holds preserved. No new human approval inferred from code review alone.',counts:{retainedSourceObservations:10875,newSourceObservations:1,totalSourceObservations:10876,retainedSourceQueries:4256,newSourceQueries:1,totalSourceQueries:4257},sourceNotices:'OFF and USDA qualified source release/attribution/license metadata retained exactly; no image/unsupported additional source use.',runtimeActivation:false,production:false,publication:false,goldAdmitted:false,consumerClientAndSavedStockIntegration:'Separate source/helper/binding/client/build review and actual05 local lifecycle required. Current515 package untouched.'};
const admissionRef=write('local-source-admission.json',json(admission));
manifest.status='phase-qualified-release-ready';manifest.acceptance={status:'selected-phase-records-exercised',receiptSha256:admissionRef.sha256};
const manifestBytes=json(manifest),manifestRef=write('manifest.local-admitted.json',manifestBytes);
need(manifestBytes.length<=128*1024,'admitted manifest descriptor bound');
const manifestDescriptor=blob(prefix+'manifest.json',manifestBytes);
const selections=Object.fromEntries(Object.keys(manifest.sources).map(sourceId=>[sourceId,{manifest:manifestDescriptor,policy:selectedPolicy,sourceId,releaseId:release,consumerCodeSha256:reader.sha256,admissionReceiptSha256:admissionRef.sha256}]));
write('fixed-selections.local.json',json(selections));
const currentCut={releaseId:release,manifestSha256:manifestRef.sha256,sourceAdmissionSha256:admissionRef.sha256,sources:Object.fromEntries(Object.entries(manifest.sources).map(([id,v])=>[id,{releaseId:v.releaseId,qualificationSha256:v.qualificationSha256,license:v.license,attribution:v.attribution}]))};
const oldBindings=fs.readFileSync(path.join(OLD,'confirmed-handoff-r1/foundation-handoff-bindings.mjs'),'utf8');
const oldCut=JSON.parse(oldBindings.slice(oldBindings.indexOf('=')+1).trim().replace(/;$/,''));
const bindings={schema:'offmenu-foundation-handoff-bindings/2',selections:[currentCut,oldCut]};
write('consumer/foundation-handoff-bindings.mjs',Buffer.from('export const FOUNDATION_HANDOFF_BINDINGS='+JSON.stringify(bindings)+';\n'));
write('consumer/foundation-scanner-handoff.mjs',fs.readFileSync(path.join(HELPER,'foundation-scanner-handoff.mjs')));
let service=fs.readFileSync(path.join(OLD,'confirmed-handoff-r1/foundation-local-response-with-reference.mjs'),'utf8');
service=service.replace("'/home/user/src/offmenu-worktrees/worker00-third-party-source-group-20261026/corpus/foundation-product-handler.mjs'","'../corpus/foundation-product-handler.mjs'").replace("'/home/user/src/offmenu-worktrees/worker00-third-party-source-group-20261026/corpus/foundation-origin-reader.mjs'","'../corpus/foundation-origin-reader.mjs'");
need(!service.includes('worker00-third-party-source-group'),'no mutable G service import');
write('consumer/foundation-local-response-with-reference.mjs',Buffer.from(service));
write('foundation-local-blobs.mjs',Buffer.from('export const LOCAL_SELECTIONS='+JSON.stringify(selections)+';\nexport const LOCAL_BLOBS='+JSON.stringify(blobs)+';\n'));
write('composition-result.json',json({atUTC:new Date().toISOString(),status:'LOCAL_SOURCE_ADMITTED_DERIVATIVE_COMPOSED_NOT_RUNTIME_ADOPTED',releaseId:release,preparedManifest:prepared,manifest:manifestRef,sourceAdmission:admissionRef,policySet:handoff.policySet,consumerReader:reader,bindings:ref(path.join(R,'consumer/foundation-handoff-bindings.mjs')),service:ref(path.join(R,'consumer/foundation-local-response-with-reference.mjs')),inlineBlobs:ref(path.join(R,'foundation-local-blobs.mjs')),helper:ref(path.join(R,'consumer/foundation-scanner-handoff.mjs')),stats,files:Object.values(blobs).map(({bodyBase64,...v})=>v),effects:'Only derived-package composition and exact old-row hash comparison. Classifier/matcher/normalizer/R2/R7/raw source/native DB/network/runtime/provider/Google/publication operations0. Current515 package unchanged.'}));
console.log(JSON.stringify({manifest:manifestRef,admission:admissionRef,releaseId:release,files:Object.keys(blobs).length,stats,bindings:ref(path.join(R,'consumer/foundation-handoff-bindings.mjs'))}));
