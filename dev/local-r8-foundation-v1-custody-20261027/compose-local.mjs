import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
import {gzipSync,gunzipSync} from 'node:zlib';
const R=import.meta.dirname,P=path.dirname(R),OLD=path.join(P,'local7645-named-foundation-r3-20261027/compact-composition-r3');
const REVIEW=path.join(P,'r8-generic-phase-adapter-v1-20261027');
const OWNER='/home/user/src/offmenu-data/runtime/layout-migration/worker19/remaining-held-public-english-serving-20261026/reviewed86-r8-application/closed-r8-phase-projection-v1';
const release='offmenu-reviewed-foundation-r8-local-20261027-v1';
const sha=b=>crypto.createHash('sha256').update(b).digest('hex');
const read=p=>JSON.parse(fs.readFileSync(p));
const ref=p=>({path:p,sha256:sha(fs.readFileSync(p))});
const need=(ok,s)=>{if(!ok)throw Error(s);};
const json=v=>Buffer.from(JSON.stringify(v)+'\n');
function write(name,bytes){const f=path.join(R,name);fs.mkdirSync(path.dirname(f),{recursive:true});fs.writeFileSync(f,bytes,{flag:'wx'});return ref(f);}
const handoff=read(path.join(OWNER,'derivative-handoff.json'));
need(ref(path.join(OWNER,'derivative-handoff.json')).sha256==='3e56878cac19e074c20d31c948af5d759d87d9a582ec890c6166927c40017005','source handoff');
for(const v of Object.values(handoff.outputs))need(ref(v.path).sha256===v.sha256,'source output');
const disposition=read(path.join(REVIEW,'source-readback-order-contract-disposition.json'));
need(disposition.status==='DONE_WITH_CONCERNS_EXACT_CLOSED_DERIVATIVE_SOURCE_INPUT_ACCEPTED_FOR_LOCAL_COMPOSITION_NO_RERUN','source order disposition');
need(ref(path.join(REVIEW,'policy.candidate.json')).sha256==='78eb758816cac23ebbe7c08b8cbf0285f2ceff57870a65119727fd203f3bfd19','new accepted policy');
const oldManifest=read(path.join(OLD,'manifest.local-admitted.json'));
need(ref(path.join(OLD,'manifest.local-admitted.json')).sha256==='fc2e17c8864cef45b36ad7cfee4a3c0ef15dd73acb8dbe54cf008fca141cd4a7','old manifest');
const oldSelections=read(path.join(OLD,'fixed-selections.local.json'));
const oldPrefix='own-data/foundation/'+oldManifest.releaseId+'/',prefix='own-data/foundation/'+release+'/';
const oldPolicyFile=path.join(OLD,'blobs',oldSelections.off.policy.key),oldPolicyBytes=fs.readFileSync(oldPolicyFile);
need(sha(oldPolicyBytes)===oldSelections.off.policy.sha256,'old policy bytes');
const policy=JSON.parse(oldPolicyBytes),newPolicyBytes=fs.readFileSync(path.join(REVIEW,'policy.candidate.json')),newPolicySha=sha(newPolicyBytes);
const retainedMembers=structuredClone(policy.policies);
need(policy.schema==='offmenu-foundation-policy-set/1'&&!Object.hasOwn(policy.policies,newPolicySha),'new distinct policy');
policy.policies[newPolicySha]=newPolicyBytes.toString();
for(const [key,bytes]of Object.entries(retainedMembers))need(policy.policies[key]===bytes&&sha(Buffer.from(bytes))===key,'old policy member restamped');
const policyBytes=json(policy),policySHA=sha(policyBytes);need(policyBytes.length<=128*1024,'policy bound');
const sourceRows=gunzipSync(fs.readFileSync(handoff.outputs.newOnlyCandidates.path),{maxOutputLength:32*1024*1024}).toString().trim().split('\n').map(JSON.parse);
need(sourceRows.length===651&&new Set(sourceRows.map(v=>v.id)).size===651&&new Set(sourceRows.map(v=>v.barcode)).size===651,'new unique count');
const additions=new Map();
for(const row of sourceRows){
 const c=row.projection.candidate;
 need(c.foundationPolicySha256===newPolicySha&&c.identity.stageRecordId===row.id&&c.identity.stageRecordWireSha256===row.stageRecordWireSha256&&c.identity.nativeRecordId===row.nativeRecordId&&c.barcode===row.barcode,'new identity');
 need(row.projection.foundationQualified===false&&row.projection.normalizationComplete===false&&row.projection.goldAdmitted===false&&row.projection.publicationAccepted===false,'preserve projection flags');
 need(Object.keys(c.parameters).length===24&&Object.values(c.parameters).every(v=>v.state==='unknown'&&!Object.hasOwn(v,'value')),'new unknown axes');
 const part=sha(Buffer.from(row.barcode)).slice(0,2);
 if(!additions.has(part))additions.set(part,[]);additions.get(part).push(row);
}
const blobs={},stats={retainedRows:0,retainedQueries:0,retainedRowsHashIdentical:0,newRows:0,newQueries:0,sources:{}};
function blob(key,body,expanded){const d={key,sha256:sha(body),bytes:body.length,...(expanded===undefined?{}:{uncompressedBytes:expanded})};write('blobs/'+key,body);blobs[key]={...d,bodyBase64:body.toString('base64')};return d;}
const manifest=structuredClone(oldManifest);
for(const [source,entry]of Object.entries(manifest.sources)){
 const counts={retainedRows:0,newRows:0,retainedQueries:0,newQueries:0};
 for(const [part,d]of Object.entries(entry.partitions)){
  const bytes=fs.readFileSync(path.join(OLD,'blobs',d.key));need(bytes.length===d.bytes&&sha(bytes)===d.sha256,'retained bytes');
  const raw=gunzipSync(bytes,{maxOutputLength:2*1024*1024});need(raw.length===d.uncompressedBytes,'retained expanded size');
  const value=JSON.parse(raw);need(value.sourceId===source&&value.policySha256===oldManifest.policySha256,'retained shell');
  const before=new Map();
  for(const [code,rows]of Object.entries(value.entries)){
   if(rows.length){stats.retainedQueries++;counts.retainedQueries++;}
   for(const row of rows){const key=JSON.stringify([code,row.id]);need(!before.has(key),'duplicate retained row');before.set(key,sha(Buffer.from(JSON.stringify(row))));stats.retainedRows++;counts.retainedRows++;}
  }
  if(source==='off')for(const row of additions.get(part)||[]){
   need(!value.entries[row.barcode]||value.entries[row.barcode].length===0,'unexpected existing query, preserve instead');
   value.entries[row.barcode]=[{schema:'offmenu-foundation-product/2',id:row.id,candidate:row.projection.candidate,
    sourceProjection:{originalHookSha256:row.projection.originalHookSha256,retainedContextVariantAssertions:row.projection.retainedContextVariantAssertions,retainedSourceAttributeClaims:row.projection.retainedSourceAttributeClaims}}];
   stats.newRows++;stats.newQueries++;counts.newRows++;counts.newQueries++;
  }
  value.policySha256=policySHA;
  for(const [code,rows]of Object.entries(value.entries))for(const row of rows){const key=JSON.stringify([code,row.id]);if(before.has(key)){need(sha(Buffer.from(JSON.stringify(row)))===before.get(key),'retained row/hash/review changed');stats.retainedRowsHashIdentical++;}}
  const next=json(value),compressed=gzipSync(next,{level:9,mtime:0});need(next.length<=2*1024*1024&&compressed.length<=1024*1024,'derived product bounds');
  entry.partitions[part]=blob(d.key.replace(oldPrefix,prefix),compressed,next.length);
 }
 stats.sources[source]=counts;
}
need(stats.retainedRows===10876&&stats.retainedRowsHashIdentical===10876&&stats.retainedQueries===4257&&stats.newRows===651&&stats.newQueries===651,'actual composition counts');
const policyDescriptor=blob(prefix+'policy.json',policyBytes);
const notice=fs.readFileSync(path.join(OLD,'blobs',oldPrefix+'SOURCE-NOTICES.txt'));
blob(prefix+'SOURCE-NOTICES.txt',Buffer.concat([notice,Buffer.from('\nAdditional local OFF derivative: reviewed whole-product policy, exact source identity readback and phase assessment. Twenty-four parameter axes remain unknown. Full normalization, product completion, Gold, planning, publication and physical equivalence are not admitted.\n')]));
for(const name of ['foundation-phase-contract.mjs','foundation-phase-contract-v2.mjs','foundation-policy-set.mjs','foundation-origin-reader.mjs','foundation-product-handler.mjs'])write('corpus/'+name,fs.readFileSync(path.join(OLD,'corpus',name)));
manifest.releaseId=release;manifest.policySha256=policySHA;manifest.consumerCodeSha256=ref(path.join(R,'corpus/foundation-origin-reader.mjs')).sha256;
manifest.status='prepared';manifest.acceptance={status:'not-admitted',receiptSha256:null};
manifest.counts={sourceObservations:11527,sourceSpecificQueries:4908,retainedRows:10876,newQualifiedSourceObservations:651,Gold:0};
const prepared=write('manifest.prepared.json',json(manifest));need(fs.statSync(prepared.path).size<=128*1024,'manifest bound');
const admission=write('local-source-admission.json',json({id:'worker00-local-r8-651-source-derivative-admission-20261027',atUTC:new Date().toISOString(),issuerWorker:0,threadId:'01a1371c-66f7-70e0-9e3b-a79d2b2eee9f',status:'ADMITTED_LOCAL_REVIEWED_SOURCE_DERIVATIVE_ONLY_NOT_RUNTIME_PUBLICATION',releaseId:release,preparedManifest:prepared,sourceHandoff:ref(path.join(OWNER,'derivative-handoff.json')),sourceOrderDisposition:ref(path.join(REVIEW,'source-readback-order-contract-disposition.json')),implementation:ref('/home/user/src/offmenu-data/runtime/layout-migration/worker57/general-variant-semantic-review-20261026/r8-phase-adapter-review-20261027/accepted-implementation.json'),policyAcceptance:ref('/home/user/src/offmenu-data/runtime/layout-migration/worker57/general-variant-semantic-review-20261026/r8-phase-adapter-review-20261027/accepted-policy.json'),phaseAssessment:handoff.outputs.phaseAssessmentResult,retainedSourceAdmission:ref(path.join(OLD,'local-source-admission.json')),retainedManifest:ref(path.join(OLD,'manifest.local-admitted.json')),counts:stats,scope:'LOCAL same qualified OFF/USDA public-derived fields plus exact651 independently source/native/dualarray/wire-qualified and acceptedpolicy phase-assessed OFF rows. Preserve all10876 prior rows/stamps/policybytes and82overlap unchanged;23nonGTIN retained outsidephase. No classifier/sourcepass/acquisition/private/native-source/credentials/externalfallback/runtime/publication/Gold/normalization/fullproduct/planning/recipejoin admission.',runtimeActivation:false,publication:false,production:false,goldAdmitted:false}));
manifest.status='phase-qualified-release-ready';manifest.acceptance={status:'selected-phase-records-exercised',receiptSha256:admission.sha256};
const manifestBytes=json(manifest);need(manifestBytes.length<=128*1024,'admitted manifest bound');const manifestRef=write('manifest.local-admitted.json',manifestBytes);
const manifestDescriptor=blob(prefix+'manifest.json',manifestBytes);
const selections=Object.fromEntries(Object.keys(manifest.sources).map(sourceId=>[sourceId,{manifest:manifestDescriptor,policy:policyDescriptor,sourceId,releaseId:release,consumerCodeSha256:manifest.consumerCodeSha256,admissionReceiptSha256:admission.sha256}]));write('fixed-selections.local.json',json(selections));
const oldBindingText=fs.readFileSync(path.join(OLD,'consumer/foundation-handoff-bindings.mjs'),'utf8');const bindings=JSON.parse(oldBindingText.slice(oldBindingText.indexOf('=')+1).trim().replace(/;$/,''));
const currentCut={releaseId:release,manifestSha256:manifestRef.sha256,sourceAdmissionSha256:admission.sha256,sources:Object.fromEntries(Object.entries(manifest.sources).map(([id,s])=>[id,{releaseId:s.releaseId,qualificationSha256:s.qualificationSha256,license:s.license,attribution:s.attribution}]))};
bindings.selections.unshift(currentCut);write('consumer/foundation-handoff-bindings.mjs',Buffer.from('export const FOUNDATION_HANDOFF_BINDINGS='+JSON.stringify(bindings)+';\n'));
for(const name of ['foundation-scanner-handoff.mjs','foundation-local-response-with-reference.mjs'])write('consumer/'+name,fs.readFileSync(path.join(OLD,'consumer',name)));
write('foundation-local-blobs.mjs',Buffer.from('export const LOCAL_SELECTIONS='+JSON.stringify(selections)+';\nexport const LOCAL_BLOBS='+JSON.stringify(blobs)+';\n'));
const result={atUTC:new Date().toISOString(),status:'LOCAL_SOURCE_DERIVATIVE_COMPOSED_NOT_RUNTIME_ADOPTED_FUNCTION_CHECKS_PENDING',releaseId:release,manifest:manifestRef,sourceAdmission:admission,policySet:policyDescriptor,acceptedNewPolicySha256:newPolicySha,retainedPolicyMembers:Object.keys(retainedMembers),consumerReader:ref(path.join(R,'corpus/foundation-origin-reader.mjs')),bindings:ref(path.join(R,'consumer/foundation-handoff-bindings.mjs')),service:ref(path.join(R,'consumer/foundation-local-response-with-reference.mjs')),inlineBlobs:ref(path.join(R,'foundation-local-blobs.mjs')),helper:ref(path.join(R,'consumer/foundation-scanner-handoff.mjs')),stats,files:Object.values(blobs).map(({bodyBase64,...v})=>v),effects:'Closed derivative composition only, no rawsource/nativeDB/classifier/network/provider/runtime/browser/production action. Currentd425 and urgent422story-header qualification remain separate.'};
write('composition-result.json',json(result));console.log(JSON.stringify({manifest:manifestRef,admission,releaseId:release,files:Object.keys(blobs).length,stats,bindings:result.bindings}));
