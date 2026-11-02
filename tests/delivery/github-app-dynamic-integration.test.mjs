import test from 'node:test';
import assert from 'node:assert/strict';
import {fingerprint,validateConfig,integrationStep,nativePublisherRequest} from '../../tools/delivery/github-app-publisher.mjs';
import {advanceIntegration} from '../../tools/delivery/integration-gateway.mjs';

// Synthetic authenticated owner, API and Controller boundaries only. The actual
// publisher/gateway observer and immutable config checks run unchanged.
function fixture() {
  const b={version:2,repository:'maldous/offmenu',pr_number:null,owner:'fixture-owner',
    issue_id:'12345678-1234-1234-1234-123456789abc',head:'a'.repeat(40),base:'b'.repeat(40),
    tree:'c'.repeat(40),head_branch:'feature/original',validation_operation_key:'d'.repeat(64),
    outputs:{'identity.txt':'e'.repeat(64)},policy_sha256:'f'.repeat(64),capacity_policy_sha256:'1'.repeat(64)};
  const source={repository:b.repository,branch:b.head_branch,base:'2'.repeat(40),head:b.head,
    tree:b.tree,target:'develop',policy_sha256:b.policy_sha256};
  const n={issue_id:b.issue_id,project_id:'ffb6c7d9-4eff-46eb-a805-99f0cc2edfa0',owner:b.owner,
    source,unit_sha256:'3'.repeat(64),packet_sha256:'4'.repeat(64)};
  b.source_projection={version:1,profile:'identity-client-focused',
    source:{head:b.head,base:source.base,tree:b.tree,branch:b.head_branch},
    target:{base:b.base,tree:'5'.repeat(40)},merge_tree:'6'.repeat(40),outputs:b.outputs,
    unit_sha256:n.unit_sha256,operation_key:b.validation_operation_key,
    receipt:{path:'/private/original-receipt.json',sha256:'7'.repeat(64)},review_sha256:'8'.repeat(64)};
  const snapshot={publisher_owner:b.owner,native_runtime:n,source_tree:b.tree,source_clean:true,
    policy_sha256:b.policy_sha256,capacity_policy_sha256:b.capacity_policy_sha256,
    publication_triggers_actions:false,unresolved_findings:[],
    validation:{head:b.head,base:source.base,operation_key:b.validation_operation_key,outputs:b.outputs,
      status:'succeeded',child_tree_gone:true,reconcile_required:false},
    review:{head:b.head,base:source.base,independent:true,verdict:'accept',findings:[],
      evidence_id:'original-native-review',evidence_source:{path:'/private/typed-review.json',sha256:'8'.repeat(64)},
      qualification_source:{path:'/private/qualified-unit.json',sha256:'9'.repeat(64)}}};
  const plan={operations:[],changedFiles:b.outputs};
  b.publication={plan_sha256:fingerprint(plan),qualification_sha256:fingerprint(snapshot)};
  const pins=['tools/delivery/github-app-publisher.mjs','tools/delivery/github-app-adapter.mjs',
    'tools/delivery/integration-gateway.mjs','src/offmenu/delivery/integration.py',
    'src/offmenu/delivery/engine.py','src/offmenu/__init__.py','src/offmenu/delivery/__init__.py',
    'src/offmenu/delivery/identity_source_projection.py'];
  const config={version:1,appId:12,installationId:34,repositoryId:1416253963,publisherUid:2345,publisherGid:3456,
    logicalOwner:b.owner,sourceHead:'a'.repeat(40),pythonSha256:'b'.repeat(64),
    codePins:Object.fromEntries(pins.map(p=>[p,'c'.repeat(64)])),binding:b,snapshot,plan,workspace:'/synthetic/original'};
  config.integration_admission={version:1,kind:'native-reviewed-integration-v1',binding_sha256:fingerprint(b),
    unit_sha256:n.unit_sha256,review_sha256:b.source_projection.review_sha256,
    permission_sha256:'d'.repeat(64),automatic_integration_enabled:true};
  let merged=false,mutations=0,lose=false;const observations=[],outcomes=[];
  const facts={head:b.head,base:b.base,reviews:[],findings:[],
    qualification:'facts-only-requires-independent-owner-review-and-thread-resolution'};
  const controller=async(op,data)=>{
    if(op==='status')return {publication:{effect:'verified',pr_number:201}};
    if(op==='outcome'){outcomes.push(data);return {};}
    assert.equal(op,'step');observations.push(data.observation);
    if(merged)return {status:'merge-verified',action:null};
    assert.equal(data.observation.automatic_integration_enabled,true);
    return {status:'merge-intent',action:{kind:'merge-pr',repository:b.repository,pr_number:201,
      expected_head_sha:b.head,expected_base_sha:b.base,expected_head_branch:b.head_branch}};
  };
  const github={getPullRequest:async()=>({merged,head_sha:b.head,base_sha:b.base,base:'develop',
      head:b.head_branch,draft:false,mergeable:true,merge_commit_sha:'e'.repeat(40)}),
    readExactHeadReviewFacts:async()=>structuredClone(facts),
    readCanonicalFacts:async()=>({merge_commit:{sha:'e'.repeat(40),parents:[b.base,b.head],
      tree:b.source_projection?.merge_tree ?? b.tree},develop_contains_merge:true}),
    mergePullRequest:async()=>{mutations++;merged=true;if(lose)throw Error('lost reply');return {merged:true};}};
  const run=()=>integrationStep({config,controller,adapterFactory:async()=>github,advanceIntegration});
  return {config,facts,run,observations,outcomes,mutations:()=>mutations,lose:()=>{lose=true;}};
}
test('sealed dynamic admission qualifies actual fresh facts without changing snapshot or operation',async()=>{
  const f=fixture(),original=structuredClone(f.config),key=fingerprint(f.config.binding);
  validateConfig(f.config,{uid:2345,euid:2345,gid:3456,egid:3456});
  assert.equal((await f.run()).status,'merge-verified');
  assert.equal(f.mutations(),1);assert.deepEqual(f.config,original);
  assert.equal(fingerprint(f.config.binding),key);
  assert.deepEqual(f.observations[0].review,original.snapshot.review);
  assert.deepEqual(f.observations[0].validation,original.snapshot.validation);
  assert.deepEqual(f.observations[0].github_review_facts.reviews,[]); // no invented approval
  assert.equal(f.observations[0].integration_admission_sha256,fingerprint(original.integration_admission));
});
test('changes requested, pending reviews, findings and head/base drift hold before a Controller merge decision',async()=>{
  for(const change of [f=>{f.findings=[{id:1,reviewer_id:2,head:f.head}];},
    f=>{f.reviews=[{id:1,reviewer_id:2,head:f.head,state:'CHANGES_REQUESTED'}];},
    f=>{f.reviews=[{id:1,reviewer_id:2,head:f.head,state:'PENDING'}];},
    f=>{f.head='0'.repeat(40);},f=>{f.base='0'.repeat(40);}]) {
    const f=fixture();change(f.facts);
    await assert.rejects(f.run(),/publisher-held/);assert.equal(f.mutations(),0);assert.equal(f.observations.length,0);
  }
});
test('no admission keeps the frozen facts guard; false or differently bound admission never enables integration',async()=>{
  for(const change of [c=>{delete c.integration_admission;},
    c=>{c.integration_admission.automatic_integration_enabled=false;},
    c=>{c.integration_admission.binding_sha256='0'.repeat(64);},
    c=>{c.integration_admission.review_sha256=c.snapshot.review.qualification_source.sha256;},
    c=>{c.snapshot.review.evidence_source.sha256='0'.repeat(64);},
    c=>{c.version=2;}]) {
    const f=fixture();change(f.config);await assert.rejects(f.run(),/publisher-held/);assert.equal(f.mutations(),0);
  }
});
test('lost merge reply uses canonical merged readback and never replays mutation',async()=>{
  const f=fixture();f.lose();assert.equal((await f.run()).status,'merge-verified');
  assert.equal(f.outcomes[0].outcome,'uncertain');await f.run();assert.equal(f.mutations(),1);
});
test('native continuity is an independent exact finite association, never integration permission',()=>{
  const f=fixture(),n=f.config.snapshot.native_runtime;
  delete f.config.integration_admission;
  const a={version:1,operation_id:fingerprint(f.config.binding),unit_sha256:n.unit_sha256,
    packet_sha256:n.packet_sha256,claim_sha256:'1'.repeat(64),previous_selection_sha256:'2'.repeat(64),
    previous_record_sha256:'3'.repeat(64),previous_capability:{version:1,
      closure_sha256:'4'.repeat(64),host_confirmation_sha256:'5'.repeat(64)},
    receipts:[{invocation_id:'12345678-1234-4234-8234-123456789abc',
      closure_sha256:'4'.repeat(64),receipt_sha256:'6'.repeat(64)}]};
  f.config.nativeContinuation=a;
  const identity={uid:2345,euid:2345,gid:3456,egid:3456};
  validateConfig(f.config,identity);
  for(const change of [r=>{r.receipts=[];},r=>{r.receipts.push({...r.receipts[0]});},
    r=>{r.operation_id='0'.repeat(64);},r=>{r.packet_sha256='not-a-pin';},
    r=>{r.previous_capability.version=true;},r=>{r.new_closure_sha256='0'.repeat(64);}]) {
    f.config.nativeContinuation=structuredClone(a);change(f.config.nativeContinuation);
    assert.throws(()=>validateConfig(f.config,identity),/publisher-held/);
  }
});

function nativeFixture() {
  const f=fixture(),c=f.config,b=c.binding,s=c.snapshot,n=s.native_runtime;
  delete b.source_projection;b.base=n.source.base;f.facts.base=b.base;
  delete c.codePins['src/offmenu/delivery/identity_source_projection.py'];
  n.source.policy_sha256='9'.repeat(64); // Native release/source policy != integration policy.
  s.validation.capacity_policy_sha256=b.capacity_policy_sha256;
  Object.assign(s.review,{outputs:b.outputs,author:b.owner,reviewer:'independent-reviewer',
    model:'unknown',provider:'unknown',requested_model:'unknown',requested_provider:'unknown',
    resolved_model:null,resolution_status:'unknown'});
  s.review.evidence_sha256=fingerprint(s.review);
  s.native_receipt_source={path:'/private/original/attempts/UIF-102/receipt.json',sha256:'a'.repeat(64)};
  s.validation_receipt_source={path:'/private/original/validation-receipt.json',sha256:'b'.repeat(64)};
  b.publication.qualification_sha256=fingerprint(s);
  c.integration_admission={...c.integration_admission,kind:'native-source-reviewed-integration-v1',
    binding_sha256:fingerprint(b),native_origin:{version:1,kind:'native-v1',profile:'enrichment-resilience-focused',
      source_sha256:fingerprint(n.source),packet_sha256:n.packet_sha256,
      validation_operation_key:b.validation_operation_key,outputs:b.outputs,
      native_receipt:s.native_receipt_source,validation_receipt:s.validation_receipt_source}};
  return f;
}
test('unprojected native origin retains exact original source, review, terminal refs and fresh facts',async()=>{
  const f=nativeFixture(),before=structuredClone(f.config);
  validateConfig(f.config,{uid:2345,euid:2345,gid:3456,egid:3456});
  assert.equal((await f.run()).status,'merge-verified');assert.equal(f.mutations(),1);
  assert.deepEqual(f.config,before);assert.equal(Object.hasOwn(f.config.binding,'source_projection'),false);
  assert.deepEqual(f.observations[0].review,before.snapshot.review);
  assert.deepEqual(f.observations[0].github_review_facts.reviews,[]);
  for(const change of [c=>{c.integration_admission.native_origin.profile='identity-client-focused';},
    c=>{c.integration_admission.kind='native-reviewed-integration-v1';},
    c=>{c.integration_admission.native_origin.source_sha256='0'.repeat(64);},
    c=>{c.integration_admission.native_origin.packet_sha256='0'.repeat(64);},
    c=>{c.integration_admission.native_origin.validation_receipt={path:'/foreign.json',sha256:'0'.repeat(64)};},
    c=>{c.snapshot.native_runtime.source.base='0'.repeat(40);},
    c=>{c.snapshot.review.evidence_sha256='0'.repeat(64);},
    c=>{c.snapshot.review.author='foreign';},
    c=>{c.integration_admission.permission_sha256='not-a-pin';}]) {
    const bad=nativeFixture();change(bad.config);
    await assert.rejects(bad.run(),/publisher-held/);assert.equal(bad.mutations(),0);
    assert.equal(bad.observations.length,0);
  }
  const bad=nativeFixture();bad.facts.reviews=[{id:1,reviewer_id:2,head:bad.facts.head,state:'CHANGES_REQUESTED'}];
  await assert.rejects(bad.run(),/publisher-held/);assert.equal(bad.mutations(),0);
  const frozen=nativeFixture();delete frozen.config.integration_admission;
  await assert.rejects(frozen.run(),/publisher-held/);assert.equal(frozen.mutations(),0);
});

test('normal native publication-only request obtains real pending qualification without a merge',async()=>{
  const f=nativeFixture(),c=f.config,n=c.snapshot.native_runtime,b=c.binding;
  let state={status:'publication-verified',publication:{effect:'verified',pr_number:201}},qualified=0;
  const operations=[];
  const controller=async(op,data)=>{
    operations.push(op);
    if(op==='observe')return {state:structuredClone(state),claim_current:true,claim_available:true};
    if(op==='status')return structuredClone(state);
    assert.equal(op,'observe-step');qualified++;
    assert.equal(data.observation.github.number,201);
    state={...state,status:'merge-intent',merge_effect:'pending',qualification_sha256:'a'.repeat(64),
      action:{kind:'merge-pr',expected_head_sha:b.head,expected_base_sha:b.base}};
    return state;
  };
  const github={getPullRequest:async()=>({merged:false,head_sha:b.head,base_sha:b.base,
      base:'develop',head:b.head_branch,draft:false,mergeable:true}),
    readExactHeadReviewFacts:async()=>f.facts,mergePullRequest:async()=>assert.fail('publication-only cannot merge')};
  const request={version:1,mode:'publish',operation_id:fingerprint(b),issue_id:n.issue_id,
    project_id:n.project_id,owner:n.owner,unit_sha256:n.unit_sha256,packet_sha256:n.packet_sha256,
    source_sha256:fingerprint(n.source)};
  const response=await nativePublisherRequest({config:c,request,controller,adapterFactory:async()=>github,qualify:async()=>{}});
  assert.equal(response.status,'ready');assert.equal(qualified,1);
  assert.equal(state.merge_effect,'pending');assert.equal(operations.includes('consume'),false);
  // A later observer can requalify the unconsumed original intent, still no API.
  const observed=await nativePublisherRequest({config:c,request:{...request,mode:'observe'},controller,
    adapterFactory:async()=>github,qualify:async()=>assert.fail('no candidate execution for observer')});
  assert.equal(observed.status,'ready');assert.equal(qualified,2);
  const projected=fixture();
  await assert.rejects(nativePublisherRequest({config:projected.config,request,controller,
    adapterFactory:async()=>github,qualify:async()=>{}}),/publisher-held/);
});
