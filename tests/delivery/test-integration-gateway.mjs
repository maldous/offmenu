import test from 'node:test';
import assert from 'node:assert/strict';
import {advanceIntegration} from '../../tools/delivery/integration-gateway.mjs';
function fixture(kind='merge-pr') {
  const action={kind,repository:'maldous/offmenu',pr_number:145,expected_head_sha:'a'.repeat(40),expected_base_sha:'b'.repeat(40),issue_id:'issue',merge_commit_sha:'c'.repeat(40),validation_operation_key:'d'.repeat(64)};
  const f={calls:[],decision:{status:kind==='merge-pr'?'merge-intent':'linear-intent',action}};
  f.controller={step:async()=>{const d=f.decision;f.decision={status:'reconciliation-required',action:null};return d;},outcome:async(...args)=>f.calls.push(['outcome',...args])};
  f.github={getPullRequest:async()=>({merged:false,head_sha:action.expected_head_sha,base_sha:action.expected_base_sha,head:'feature/langgraph-delivery-standardization',base:'develop',draft:false,mergeable:true}),mergePullRequest:async args=>{f.calls.push(['merge',args]);return {merged:true};}};
  f.linear={completeIssue:async(...args)=>f.calls.push(['linear',...args])};f.observe=async()=>({});return f;
}
test('exact-head normal merge followed by reconciliation; never approval or bypass',async()=>{const f=fixture();await advanceIntegration(f);assert.equal(f.calls[0][0],'merge');assert.deepEqual(Object.keys(f.calls[0][1]).sort(),['expected_head_sha','merge_method','pr_number','repository_full_name']);assert.deepEqual(f.calls[1],['outcome','merge','succeeded']);await advanceIntegration(f);assert.equal(f.calls.filter(c=>c[0]==='merge').length,1);});
test('moved base blocks mutation',async()=>{const f=fixture();f.github.getPullRequest=async()=>({base_sha:'changed'});await advanceIntegration(f);assert.deepEqual(f.calls,[['outcome','merge','uncertain']]);});
test('timeout is uncertain, not retryable refusal',async()=>{const f=fixture();f.github.mergePullRequest=async()=>{throw Error('timeout')};await advanceIntegration(f);assert.deepEqual(f.calls,[['outcome','merge','uncertain']]);});
test('known permission refusal stays refused',async()=>{const f=fixture();f.github.mergePullRequest=async()=>{throw Object.assign(Error('denied'),{knownRefused:true})};await advanceIntegration(f);assert.deepEqual(f.calls,[['outcome','merge','refused']]);});
test('Linear failure only records metadata uncertainty',async()=>{const f=fixture('update-linear');f.linear.completeIssue=async()=>{throw Error('timeout')};await advanceIntegration(f);assert.deepEqual(f.calls,[['outcome','linear','uncertain']]);});
test('repair packet does not execute candidate commands',async()=>{const f=fixture('repair');await advanceIntegration(f);assert.deepEqual(f.calls,[]);});
