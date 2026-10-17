import {writeFile} from 'node:fs/promises';
import {selection,environment,deferred} from './snapshot/tests-web/reviewer-fixtures.mjs';
import {localizedField} from './snapshot/public/content-locale.js';
const observations=[];
async function probe(id,make,expectedRejected){const cleanup=[],t={after(fn){cleanup.push(fn);}};let e,f;
 try{
  ({f,e}=await make(t));let rejected=false,error,result;
  try{result=await e.ui.loadSelectedCommonPackage();}catch(err){rejected=true;error=err.message;}
  observations.push({id,expectedRejected,rejected,passed:rejected===expectedRejected,visibleRows:e.$('data-results').children.length,notice:e.$('data-notice').textContent,sideEffects:e.sideEffects,saveDisabled:e.$('data-save').disabled,exportDisabled:e.$('data-export').disabled,transportCalls:f.calls.length,error,...(id==='receipt-sparse-row'?{receiptLength:result?.receipt.files.length,receiptOwnIndexes:result?Object.keys(result.receipt.files):null}:{}),...(f.extraEvidence||{})});
 }finally{for(const fn of cleanup.reverse())await fn();}
}
for(const [kind,mutate] of [
 ['schema',r=>r.receipt.schemaVersion='wrong'],['manifest-url',r=>r.receipt.manifestUrl='https://other.test/manifest.json'],['missing-key',r=>delete r.receipt.files[0].key],['wrong-file-hash',r=>r.receipt.files[0].sha256='f'.repeat(64)],['wrong-byte-type',r=>r.receipt.files[0].compressedBytes=String(r.receipt.files[0].compressedBytes)],['missing-indexes',r=>delete r.receipt.files[0].packetIndexes],['null-row',r=>r.receipt.files[0]=null],['undefined-row',r=>r.receipt.files[0]=undefined],['empty-rows',r=>r.receipt.files=[]],['extra-row',r=>r.receipt.files.push({...r.receipt.files[0]})],['sparse-row',r=>r.receipt.files=new Array(1)],
])await probe('receipt-'+kind,async t=>{const f=selection();const e=environment(t,f,async options=>{const result=await f.load(options);mutate(result);return result;});return {f,e};},true);
for(const [kind,mutate] of [
 ['missing-policy-id',f=>delete f.policy.policyId],['missing-scope',f=>delete f.policy.scope],['wrong-account',f=>f.policy.accountKey='demo'],['wrong-qualification-schema-pin',f=>f.policy.selection.qualification.schemaSha256='0'.repeat(64)],['wrong-qualification-contract-pin',f=>f.policy.selection.qualification.contractSha256='0'.repeat(64)],['wrong-qualification-release',f=>f.policy.selection.qualification.releaseId='other'],['invalid-qualification-hash',f=>{f.descriptor.qualification.schemaSha256='BAD';f.policy.selection=structuredClone(f.descriptor);}],['missing-independent-authorizer',f=>{f.authorize=undefined;f.descriptor.permission={allowed:true,policyId:'descriptor-claim'};}],
])await probe('admission-'+kind,async t=>{const f=selection();mutate(f);const e=environment(t,f);return {f,e};},true);
await probe('permission-policy-change-with-cloned-decisions',async t=>{const f=selection();const e=environment(t,f,async options=>{const r=await f.load(options);f.policy.policyId='changed-policy';return r;});return {f,e};},true);
await probe('permission-policy-change-with-shared-mutable-decision',async t=>{const f=selection();f.authorize=async()=>f.policy;const initial=f.policy.policyId;const e=environment(t,f,async options=>{const r=await f.load(options);f.policy.policyId='changed-policy';f.extraEvidence={initialPolicyId:initial,confirmedPolicyId:f.policy.policyId,authorizerReturnsSharedObject:true};return r;});return {f,e};},true);
await probe('scope-change-with-shared-mutable-decision',async t=>{const f=selection({permission:{accountKey:'user:alice',scope:{privateOwnerId:null}}});f.authorize=async()=>f.policy;const e=environment(t,f,async options=>{const r=await f.load(options);f.policy.scope.privateOwnerId='alice';return r;});e.state.user={id:'alice'};return {f,e};},true);
await probe('capability-mutation-of-options-cannot-rewrite-receipt-expectations',async t=>{const f=selection();const e=environment(t,f,async options=>{const r=await f.load(options);options.files[0].sha256='0'.repeat(64);r.receipt.files[0].sha256='0'.repeat(64);return r;});return {f,e};},true);
await probe('second-authorization-revoked',async t=>{const f=selection();let n=0;f.authorize=async()=>({...structuredClone(f.policy),allowed:++n===1});const e=environment(t,f);return {f,e};},true);
await probe('good-public-load-rechecks-rights-twice',async t=>{const f=selection();let n=0;f.authorize=async()=>{f.extraEvidence={authorizeCalls:++n};return structuredClone(f.policy);};const e=environment(t,f);return {f,e};},false);
await probe('public-authorized-scope-overrides-descriptor-privilege-claims',async t=>{const f=selection({permission:{accountKey:'user:alice'}});f.descriptor.transport.readerOptions={userId:'alice',allowLocalRestricted:true};f.policy.selection=structuredClone(f.descriptor);let options;const e=environment(t,f,o=>{options=o;f.extraEvidence={readerOptionsReceived:o.readerOptions};return f.load(o);});e.state.user={id:'alice'};return {f,e};},false);
const integration=[];
for(const reset of [false,true]){
 const cleanup=[],t={after(fn){cleanup.push(fn);}};const f=selection({permission:{accountKey:'user:alice',scope:{privateOwnerId:'alice'}}});const e=environment(t,f);e.state.user={id:'alice'};
 try{await e.ui.loadSelectedCommonPackage();e.state.user={id:'bob'};if(reset)e.ui.reset();e.$('data-language').value='native';e.$('data-language').onchange();const p=localizedField({commonResourceId:'urn:private'},'name','ar');integration.push({case:'completed-private-load-account-change',hostResetCalled:reset,visibleRows:e.$('data-results').children.length,alicePrivateTextStillRendered:e.$('data-results').textContent.includes('خاص'),globalResolverRetainsAlicePrivateText:p?.value==='خاص',sideEffects:e.sideEffects,interpretation:reset?'Existing host reset hook clears the cached reader/resolver.':'No active account/policy recheck on cached locale rendering; host identity reset remains required.'});}finally{for(const fn of cleanup.reverse())await fn();}
}
{
 const cleanup=[],t={after(fn){cleanup.push(fn);}};const f=selection();let n=0;f.authorize=async()=>{n++;return structuredClone(f.policy);};const e=environment(t,f);
 try{await e.ui.loadSelectedCommonPackage();f.policy.allowed=false;e.$('data-language').value='en';e.$('data-language').onchange();integration.push({case:'rights-revoked-after-successful-load',authorizeCalls:n,visibleRows:e.$('data-results').children.length,translationStillRendered:e.$('data-results').textContent.includes('Lentils'),sideEffects:e.sideEffects,interpretation:'Post-load cache uses a load-time authorization snapshot; no policy recheck on later locale render. Future host needs explicit invalidation or caller needs ongoing recheck if that is the intended contract.'});}finally{for(const fn of cleanup.reverse())await fn();}
}

for(const [kind,mutate] of [
 ['array-row',r=>r.receipt.files=[Object.assign([],r.receipt.files[0])]],
 ['inherited-index',r=>{const row=r.receipt.files[0];r.receipt.files=new Array(1);Object.setPrototypeOf(r.receipt.files,Object.assign(Object.create(Array.prototype),{0:row}));}],
 ['inherited-row-fields',r=>r.receipt.files=[Object.create(r.receipt.files[0])]],
 ['primitive-row',r=>r.receipt.files=['bad']],
 ['missing-own-byte-field',r=>{const row=r.receipt.files[0],value=row.compressedBytes;delete row.compressedBytes;Object.setPrototypeOf(row,{compressedBytes:value});}],
])await probe('correction-receipt-'+kind,async t=>{const f=selection();const e=environment(t,f,async options=>{const r=await f.load(options);mutate(r);return r;});return {f,e};},true);
for(const kind of ['scope-and-options','account','allowed','selection'])await probe('correction-mutable-grant-'+kind,async t=>{
 const f=selection({permission:{accountKey:'user:alice',scope:{privateOwnerId:null}}});f.authorize=async()=>f.policy;
 const e=environment(t,f,async options=>{const r=await f.load(options);if(kind==='scope-and-options'){f.policy.scope.privateOwnerId='alice';options.readerOptions.userId='alice';}if(kind==='account')f.policy.accountKey='user:bob';if(kind==='allowed')f.policy.allowed=false;if(kind==='selection')f.policy.selection.qualification.contractSha256='0'.repeat(64);return r;});e.state.user={id:'alice'};return {f,e};
},true);
await probe('correction-stable-shared-decision',async t=>{const f=selection();f.authorize=async()=>f.policy;const e=environment(t,f);return {f,e};},false);
await probe('correction-mutated-loader-options-cannot-hide-receipt-rewrite',async t=>{const f=selection();const e=environment(t,f,async options=>{const r=await f.load(options);options.files[0].bytes++;r.receipt.files[0].compressedBytes++;return r;});return {f,e};},true);

const report={schema:'offmenu.worker10.caller-edge-cases/1',candidate:'f99c308cac7e6d7033d17abdabcb07aead5c8e5c',cases:observations.length,passed:observations.filter(x=>x.passed).length,failed:observations.filter(x=>!x.passed).length,observations,integration};
await writeFile(new URL('./edge-results.json',import.meta.url),JSON.stringify(report,null,2)+'\n');console.log(JSON.stringify({cases:report.cases,passed:report.passed,failed:report.failed,failedCases:observations.filter(x=>!x.passed),integration},null,2));process.exitCode=report.failed?1:0;
