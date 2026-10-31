import test from 'node:test';
import assert from 'node:assert/strict';
import {advanceIntegration,reviewWireBytes,reviewStandaloneValidation,reviewCompletedNativeValidation} from '../../tools/delivery/integration-gateway.mjs';
function fixture(kind='merge-pr') {
  const action={kind,repository:'maldous/offmenu',pr_number:145,expected_head_branch:'feature/langgraph-delivery-standardization',expected_head_sha:'a'.repeat(40),expected_base_sha:'b'.repeat(40),issue_id:'issue',merge_commit_sha:'c'.repeat(40),validation_operation_key:'d'.repeat(64)};
  const f={calls:[],decision:{status:kind==='merge-pr'?'merge-intent':'linear-intent',action}};
  f.controller={step:async()=>{const d=f.decision;f.decision={status:'reconciliation-required',action:null};return d;},outcome:async(...args)=>f.calls.push(['outcome',...args])};
  f.github={getPullRequest:async()=>({merged:false,head_sha:action.expected_head_sha,base_sha:action.expected_base_sha,head:'feature/langgraph-delivery-standardization',base:'develop',draft:false,mergeable:true}),mergePullRequest:async args=>{f.calls.push(['merge',args]);return {merged:true};}};
  f.linear={completeIssue:async(...args)=>f.calls.push(['linear',...args])};f.observe=async()=>({});return f;
}
test('exact-head normal merge followed by reconciliation; never approval or bypass',async()=>{const f=fixture();await advanceIntegration(f);assert.equal(f.calls[0][0],'merge');assert.deepEqual(Object.keys(f.calls[0][1]).sort(),['expected_head_sha','merge_method','pr_number','repository_full_name']);assert.deepEqual(f.calls[1],['outcome','merge','succeeded']);await advanceIntegration(f);assert.equal(f.calls.filter(c=>c[0]==='merge').length,1);});
test('moved base blocks mutation',async()=>{const f=fixture();f.github.getPullRequest=async()=>({base_sha:'changed'});await advanceIntegration(f);assert.deepEqual(f.calls,[['outcome','merge','not-issued']]);});
test('timeout is uncertain, not retryable refusal',async()=>{const f=fixture();f.github.mergePullRequest=async()=>{throw Error('timeout')};await advanceIntegration(f);assert.deepEqual(f.calls,[['outcome','merge','uncertain']]);});
test('known permission refusal stays refused',async()=>{const f=fixture();f.github.mergePullRequest=async()=>{throw Object.assign(Error('denied'),{knownRefused:true})};await advanceIntegration(f);assert.deepEqual(f.calls,[['outcome','merge','refused']]);});
test('Linear failure only records metadata uncertainty',async()=>{const f=fixture('update-linear');f.linear.completeIssue=async()=>{throw Error('timeout')};await advanceIntegration(f);assert.deepEqual(f.calls,[['outcome','linear','uncertain']]);});
test('repair packet does not execute candidate commands',async()=>{const f=fixture('repair');await advanceIntegration(f);assert.deepEqual(f.calls,[]);});

test('successful merge consumes returned metadata intent immediately',async()=>{const f=fixture();let steps=0;f.controller.step=async()=>{steps++;return steps===1?f.decision:steps===2?{status:'linear-intent',action:{kind:'update-linear',issue_id:'issue',merge_commit_sha:'c',validation_operation_key:'d'}}:{status:'accepted',action:null};};const result=await advanceIntegration(f);assert.equal(result.status,'accepted');assert.equal(f.calls.filter(c=>c[0]==='merge').length,1);assert.equal(f.calls.filter(c=>c[0]==='linear').length,1);assert.deepEqual(f.calls.filter(c=>c[0]==='outcome'),[['outcome','merge','succeeded'],['outcome','linear','succeeded']]);});
test('preflight read timeout releases known-unissued merge intent',async()=>{const f=fixture();f.github.getPullRequest=async()=>{throw Error('read timeout')};await advanceIntegration(f);assert.deepEqual(f.calls,[['outcome','merge','not-issued']]);});
test('preflight permission refusal preserves authority stop',async()=>{const f=fixture();f.github.getPullRequest=async()=>{throw Object.assign(Error('denied'),{knownRefused:true})};await advanceIntegration(f);assert.deepEqual(f.calls,[['outcome','merge','refused']]);});
test('slow metadata readbacks consume every emitted retry without dropping an action',async()=>{const f=fixture('update-linear');let attempts=0;f.controller.step=async()=>attempts<3?f.decision:{status:'accepted',action:null};f.linear.completeIssue=async()=>{attempts++;f.calls.push(['linear']);};const result=await advanceIntegration(f);assert.equal(result.status,'accepted');assert.equal(attempts,3);assert.equal(f.calls.filter(c=>c[0]==='outcome').length,3);});

test('malformed preflight response is known nonexecution',async()=>{const f=fixture();f.github.getPullRequest=async()=>null;await advanceIntegration(f);assert.deepEqual(f.calls,[['outcome','merge','not-issued']]);});

test('optional trusted writer sees qualified exact snapshot once without extra effects',async()=>{
  const f=fixture(); let written;
  f.decision.merge_effect='pending'; f.decision.qualification_sha256='e'.repeat(64);
  f.observe=async()=>({review:{verdict:'accept',findings:[]},validation:{operation_key:'d'}});
  f.unitReviewWriter=async packet=>{written=packet;packet.snapshot.review.verdict='mutated';};
  await advanceIntegration(f);
  assert.equal(written.decision.status,'merge-intent');
  assert.equal(f.calls.filter(c=>c[0]==='merge').length,1);
  assert.equal(f.calls.filter(c=>c[0]==='linear').length,0);
});
test('unit writer never receives repair, unqualified, cancelled or uncertain decisions',async()=>{
  for(const change of [{status:'repair-required'},{status:'awaiting-validation'},
    {merge_effect:'uncertain'},{qualification_sha256:null}]){
    const f=fixture();Object.assign(f.decision,{merge_effect:'pending',qualification_sha256:'e'.repeat(64)},change);
    f.observe=async()=>({review:{verdict:'accept',findings:[]}});
    f.unitReviewWriter=async()=>assert.fail('unqualified writer');await advanceIntegration(f);
  }
  for(const snapshot of [{cancel_requested:true},{unresolved_findings:['open']},{review:{verdict:'changes-requested'}}]){
    const f=fixture();Object.assign(f.decision,{merge_effect:'pending',qualification_sha256:'e'.repeat(64)});
    f.observe=async()=>({review:{verdict:'accept'},...snapshot});
    f.unitReviewWriter=async()=>assert.fail('held writer');await advanceIntegration(f);
  }
});

test('wire v2 immutable byte oracle and unsupported domain',async()=>{
  const {createHash}=await import('node:crypto');
  const bytes=reviewWireBytes({duration_seconds:1e-7});
  assert.equal(bytes,'{"duration_seconds":1e-7}');
  assert.equal(createHash('sha256').update(bytes).digest('hex'),
    'd69596f32f2541138b93f4d3b73427f7c2345864eab139ba7bdd22da962b5084');
  assert.equal(reviewWireBytes({'10':1,'2':1.0,'𐀀':'😀','\ue000':'é'}),
    '{"2":1,"10":1,"𐀀":"😀","\ue000":"é"}');
  const cycle={};cycle.self=cycle;
  const sparse=[,];sparse.extra=1;
  const hidden=Object.defineProperty({},'toJSON',{value:()=>null});
  for(const value of [NaN,Infinity,-Infinity,-0,2**53,1e100,undefined,1n,cycle,
      [,,],sparse,hidden,new Date(),{x:undefined},'\ud800']) assert.throws(()=>reviewWireBytes(value));
});

if (process.argv[2] !== '--local-review-fixture') test('standalone owner gateway consumes explicit qualification without controller or merge',async()=>{
  const snapshot={review:{verdict:'accept',independent:true,findings:[]},validation:{status:'succeeded'}};
  const decision={version:1,kind:'standalone-validation-review-v1',status:'standalone-validation-qualified',
    action:null,merge_effect:'not-applicable',binding_sha256:'b'.repeat(64),qualification_sha256:'c'.repeat(64)};
  let calls=0;
  const args={observe:async()=>snapshot,qualification:{snapshot,decision},unitReviewWriter:async envelope=>{
    calls++;assert.deepEqual(envelope,{snapshot,decision});return {status:'retained'};
  }};
  assert.equal((await reviewStandaloneValidation(args)).status,'retained');
  assert.equal(calls,1);
  for(const change of [{kind:'merge-pr'},{action:{kind:'merge-pr'}},{merge_effect:'pending'},
    {status:'merge-intent'},{qualification_sha256:null}]){
    await assert.rejects(reviewStandaloneValidation({...args,
      qualification:{snapshot,decision:{...decision,...change}}}));
  }
  await assert.rejects(reviewStandaloneValidation({...args,observe:async()=>({...snapshot,cancel_requested:true})}));
  assert.equal(calls,1);
});

if (process.argv[2] === '--standalone-review-fixture') test('standalone fixed gateway, exact pins and no actual merge',async()=>{
  const {readFileSync,writeFileSync,statSync,existsSync}=await import('node:fs');
  const {pathToFileURL}=await import('node:url');
  const {createHash}=await import('node:crypto');
  const hash=raw=>createHash('sha256').update(raw).digest('hex');
  const {context,packet}=JSON.parse(readFileSync(process.argv[3]));
  const {reviewStandaloneValidation:advance}=await import(pathToFileURL(process.argv[4]));
  const incoming=`${context.runtime}/unit-review-${context.issue}.json`;
  const args=()=>({reviewedCurrentUnit:structuredClone(context),observe:async()=>structuredClone(packet.snapshot)});
  const refused=async call=>{await assert.rejects(advance(call));assert.equal(existsSync(incoming),false);};
  for (const mutate of [
    c=>{c.qualification_source.sha256='0'.repeat(64);},
    c=>{c.validation_receipt_source.sha256='0'.repeat(64);},
    c=>{c.source_sha256['tools/delivery/stokowski_stage.py']='0'.repeat(64);},
    c=>{delete c.source_sha256['src/offmenu/delivery/integration.py'];},
    c=>{c.unit_binding.request_sha256='0'.repeat(64);},
    c=>{c.validation_receipt.job_id='foreign';},
    c=>{c.workspace_roots=[context.runtime];}
  ]) {const call=args();mutate(call.reviewedCurrentUnit);await refused(call);}
  // Fresh raw byte pin still cannot replace the original Journal digest.
  const receiptPath=context.validation_receipt_source.path,receipt=readFileSync(receiptPath);
  writeFileSync(receiptPath,JSON.stringify(context.validation_receipt));
  const normalized=args();normalized.reviewedCurrentUnit.validation_receipt_source.sha256=hash(readFileSync(receiptPath));
  await refused(normalized);writeFileSync(receiptPath,receipt);
  const activePath=`${context.claim_root}/active-owner.json`,active=readFileSync(activePath);
  const immutablePath=`${context.controller_directory}/repository-claim.json`,immutable=readFileSync(immutablePath);
  for (const claimPath of [activePath,immutablePath]) {
    const original=readFileSync(claimPath);
    writeFileSync(claimPath,JSON.stringify({...JSON.parse(original),owner:'foreign-owner'}));
    await refused(args());writeFileSync(claimPath,original);
  }
  // A malformed active pointer must not fall back to the historical root claim.
  writeFileSync(activePath,'null');await refused(args());writeFileSync(activePath,active);
  assert.deepEqual(readFileSync(immutablePath),immutable);
  const qualificationPath=context.qualification_source.path,qualification=readFileSync(qualificationPath);
  for(const mutate of [
    p=>{p.snapshot.review.reviewer=p.snapshot.review.author;},
    p=>{p.snapshot.validation.operation_key='0'.repeat(64);},
    p=>{p.snapshot.source_tree='0'.repeat(40);},
    p=>{p.snapshot.policy_sha256='0'.repeat(64);},
    p=>{p.snapshot.review.evidence_sha256='0'.repeat(64);},
    p=>{p.decision.action={kind:'merge-pr'};}
  ]) {
    const altered=structuredClone(packet);mutate(altered);writeFileSync(qualificationPath,JSON.stringify(altered));
    const call=args();call.reviewedCurrentUnit.qualification_source.sha256=hash(readFileSync(qualificationPath));
    call.observe=async()=>altered.snapshot;await refused(call);
  }
  writeFileSync(qualificationPath,qualification);
  await advance(args());
  const first=readFileSync(incoming),stat=statSync(incoming);
  await advance(args());assert.deepEqual(readFileSync(incoming),first);
  assert.equal(statSync(incoming).ino,stat.ino);assert.equal(statSync(incoming).mtimeMs,stat.mtimeMs);
  assert.equal(existsSync(`${context.controller_directory}/state.json`),false);
  assert.equal(existsSync(`${context.controller_directory}/graph.sqlite`),false);
});

// Invoked by the Python private fixture with actual committed transport source.
// The owner/controller here are fixture-controlled, not production authenticated.
if (process.argv[2] === '--local-review-fixture') test('fixed gateway process, timeout reconciliation, duplicate and refusals', async () => {
  const {readFileSync,statSync,writeFileSync,unlinkSync} = await import('node:fs');
  const {pathToFileURL} = await import('node:url');
  const {context,packet} = JSON.parse(readFileSync(process.argv[3]));
  const {advanceIntegration:advance} = await import(pathToFileURL(process.argv[4]));
  const incoming = `${context.runtime}/unit-review-${context.issue}.json`;
  const args = () => ({reviewedCurrentUnit:context,observe:async()=>packet.snapshot,
    controller:{step:async()=>packet.decision,outcome:async()=>({status:'stopped'})},
    github:{getPullRequest:async()=>null},linear:{}});
  // Unsupported callbacks/context must fail before any publication.
  const {existsSync}=await import('node:fs');
  for (const value of [NaN,Infinity,-Infinity,-0,2**53,1e100]) {
    const call=args();
    call.observe=async()=>({...packet.snapshot, unsupported:value});
    await assert.rejects(advance(call));
    assert.equal(existsSync(incoming),false);
  }
  const badPin=args();badPin.reviewedCurrentUnit=structuredClone(context);
  badPin.reviewedCurrentUnit.validation_receipt_source.sha256='0'.repeat(64);
  await assert.rejects(advance(badPin));
  assert.equal(existsSync(incoming),false);
  // Matching a freshly pinned JS-normalized receipt is insufficient: the
  // original Journal digest still requires Python's retained 1.0 spelling.
  const {createHash}=await import('node:crypto');
  const receiptPath=context.validation_receipt_source.path;
  const originalReceipt=readFileSync(receiptPath);
  writeFileSync(receiptPath,JSON.stringify(context.validation_receipt));
  const normalized=args();normalized.reviewedCurrentUnit=structuredClone(context);
  normalized.reviewedCurrentUnit.validation_receipt_source.sha256=
    createHash('sha256').update(readFileSync(receiptPath)).digest('hex');
  await assert.rejects(advance(normalized));
  assert.equal(existsSync(incoming),false);
  writeFileSync(receiptPath,originalReceipt);
  const bool=args();bool.observe=async()=>{
    const snapshot=structuredClone(packet.snapshot);snapshot.source_clean=1;return snapshot;
  };
  await assert.rejects(advance(bool));
  assert.equal(existsSync(incoming),false);
  await advance(args());
  const first=readFileSync(incoming), stat=statSync(incoming);
  await advance(args());
  assert.deepEqual(readFileSync(incoming),first);
  assert.equal(statSync(incoming).ino,stat.ino);
  assert.equal(statSync(incoming).mtimeMs,stat.mtimeMs);
  for (const mutate of [
    c=>{c.actor_uid++;}, c=>{c.python_sha256='0'.repeat(64);},
    c=>{c.source_sha256['tools/delivery/stokowski_adapter.py']='0'.repeat(64);},
    c=>{c.workspace_roots=[context.runtime];},c=>{c.unit_binding.request_sha256='0'.repeat(64);},
    c=>{c.validation_receipt.child_tree_gone=false;},
    c=>{c.controller_directory=context.runtime;}
  ]) {
    const call=args();call.reviewedCurrentUnit=structuredClone(context);mutate(call.reviewedCurrentUnit);
    await assert.rejects(advance(call));
    assert.deepEqual(readFileSync(incoming),first);
  }
  const altered=args();altered.observe=async()=>{
    const s=structuredClone(packet.snapshot);s.review.reviewer=s.review.author;return s;
  };
  await assert.rejects(advance(altered));
  const statePath=`${context.controller_directory}/state.json`;
  const original=readFileSync(statePath);
  writeFileSync(statePath,JSON.stringify({...packet.decision,status:'repair-required'}));
  await assert.rejects(advance(args()));
  writeFileSync(statePath,original);
  const claimPath=`${context.claim_root}/active-owner.json`;
  const claim=readFileSync(claimPath);
  const claimMode=statSync(claimPath).mode & 0o777;
  const legacyPath=`${context.claim_root}/repository-claim.json`;
  const legacy=readFileSync(legacyPath);
  // A valid historical owner cannot authorize the current snapshot/graph.
  writeFileSync(claimPath,legacy);
  await assert.rejects(advance(args()));
  writeFileSync(claimPath,claim);
  // Historical shared evidence does not override the selected active owner.
  await advance(args());
  const evidencePath=`${context.controller_directory}/repository-claim.json`;
  const evidence=readFileSync(evidencePath);
  const evidenceMode=statSync(evidencePath).mode & 0o777;
  writeFileSync(evidencePath,legacy);
  await assert.rejects(advance(args()));
  writeFileSync(evidencePath,evidence);
  // A matching legacy claim is a fallback only when the new pointer is absent.
  writeFileSync(legacyPath,claim);
  for (const invalid of ['{}','null','{']) {
    writeFileSync(claimPath,invalid);
    await assert.rejects(advance(args()));
  }
  unlinkSync(claimPath);
  unlinkSync(evidencePath);
  await advance(args());
  // Recreating deleted fixture files must preserve their private custody.
  writeFileSync(evidencePath,evidence,{mode:evidenceMode});
  writeFileSync(claimPath,claim,{mode:claimMode});
  assert.equal(statSync(evidencePath).mode & 0o777,evidenceMode);
  assert.equal(statSync(claimPath).mode & 0o777,claimMode);
  writeFileSync(legacyPath,legacy);
  const artifact=`${context.runtime_root}/task-230/workspaces/${context.issue}/tests/task230.py`;
  const output=readFileSync(artifact);
  writeFileSync(artifact,'changed');
  await assert.rejects(advance(args()));
  writeFileSync(artifact,output);
});
test('failed unit review publication records known nonexecution before propagating',async()=>{
  for(const error of [Error('publication failed'),Object.assign(Error('transport refused'),{knownRefused:true})]){
    const f=fixture();Object.assign(f.decision,{merge_effect:'pending',qualification_sha256:'e'.repeat(64)});
    f.observe=async()=>({review:{verdict:'accept',findings:[]}});
    f.unitReviewWriter=async()=>{throw error};
    f.github.getPullRequest=async()=>assert.fail('preflight must not run after writer failure');
    await assert.rejects(advanceIntegration(f),value=>value===error);
    assert.deepEqual(f.calls,[['outcome','merge','not-issued']]);
  }
});

test('actual unit review factory rejects non-JSON context before installation or preflight',async()=>{
  const f=fixture();Object.assign(f.decision,{merge_effect:'pending',qualification_sha256:'e'.repeat(64)});
  f.observe=async()=>({review:{verdict:'accept',findings:[]}});
  // Refuse caller configuration before any host-specific interpreter lookup.
  f.reviewedCurrentUnit={python_sha256:0n};
  f.github.getPullRequest=async()=>assert.fail('preflight must not run after factory refusal');
  await assert.rejects(advanceIntegration(f),{message:'local_review_refused'});
  assert.deepEqual(f.calls,[['outcome','merge','not-issued']]);
});

test('unqualified decisions never construct the actual unit review factory',async()=>{
  for(const change of [{status:'awaiting-validation'},{status:'awaiting-review'},
    {status:'repair-required'},{status:'cancelled'},{merge_effect:'uncertain'},
    {qualification_sha256:null}]){
    const f=fixture();Object.assign(f.decision,{merge_effect:'pending',qualification_sha256:'e'.repeat(64)},change);
    f.decision.action=null;
    f.observe=async()=>({review:{verdict:'accept',findings:[]}});
    f.reviewedCurrentUnit={python_sha256:'0'.repeat(64)};
    await advanceIntegration(f);
    assert.deepEqual(f.calls,[]);
  }
  for(const snapshot of [{cancel_requested:true},{unresolved_findings:['open']},
    {review:{verdict:'changes-requested'}},{review:{verdict:'accept',findings:['open']}}]){
    const f=fixture();Object.assign(f.decision,{merge_effect:'pending',qualification_sha256:'e'.repeat(64)});
    f.observe=async()=>({review:{verdict:'accept',findings:[]},...snapshot});
    f.reviewedCurrentUnit={python_sha256:'0'.repeat(64)};
    f.github.getPullRequest=async()=>null;
    await advanceIntegration(f);
    assert.deepEqual(f.calls,[['outcome','merge','not-issued']]);
  }
});


if (!['--local-review-fixture','--standalone-review-fixture'].includes(process.argv[2])) test('completed native evidence ingestion has no merge or submission route',async()=>{
  const context={completed_native_source:{path:'/owner/private/completed.json',sha256:'e'.repeat(64)}};
  const snapshot={review:{verdict:'accept',independent:true,findings:[]},validation:{status:'succeeded'}};
  const decision={version:1,kind:'completed-native-validation-v1',status:'completed-native-qualified',
    action:null,merge_effect:'verified',completed_evidence_sha256:'e'.repeat(64),
    binding_sha256:'b'.repeat(64),qualification_sha256:'c'.repeat(64),merge_commit_sha:'d'.repeat(40)};
  let writes=0;
  const call={reviewedCurrentUnit:context,observe:async()=>({snapshot,decision}),
    unitReviewWriter:async envelope=>{writes++;assert.deepEqual(envelope,{snapshot,decision});return {status:'retained'};}};
  assert.equal((await reviewCompletedNativeValidation(call)).status,'retained');
  for(const change of [{kind:'merge-pr'},{action:{kind:'merge-pr'}},{merge_effect:'pending'},
    {completed_evidence_sha256:'f'.repeat(64)},{merge_commit_sha:'not-a-commit'},
    {qualification_sha256:null},{status:'merge-intent'}]){
    await assert.rejects(reviewCompletedNativeValidation({...call,observe:async()=>({snapshot,decision:{...decision,...change}})}));
  }
  for(const change of [{cancel_requested:true},{unresolved_findings:['unresolved']},
    {validation:{status:'running'}},{review:{verdict:'accept',independent:false}}]){
    await assert.rejects(reviewCompletedNativeValidation({...call,observe:async()=>({snapshot:{...snapshot,...change},decision})}));
  }
  assert.equal(writes,1);
});
