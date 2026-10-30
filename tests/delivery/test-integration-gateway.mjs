import test from 'node:test';
import assert from 'node:assert/strict';
import {advanceIntegration} from '../../tools/delivery/integration-gateway.mjs';
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
