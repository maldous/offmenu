import test from 'node:test';
import assert from 'node:assert/strict';
import {fingerprint,validateConfig,integrationStep} from '../../tools/delivery/github-app-publisher.mjs';
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
      tree:b.source_projection.merge_tree},develop_contains_merge:true}),
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
