import test from 'node:test';
import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
import {fingerprint,validateConfig,qualifySourceProjection,qualifyCandidate,
  qualifyNativeRequest,canonicalPublication} from '../../tools/delivery/github-app-publisher.mjs';

// Original source objects stay original; the target is a later distinct commit.
// All identities/objects/readers are synthetic. No API, config, Git or key access.
const sha=b=>createHash('sha256').update(b).digest('hex');
function fixture() {
  const objects=new Map(),raw=Buffer.from('reviewed identity delta\n');
  const add=(kind,bytes)=>{const id=createHash('sha1').update(`${kind} ${bytes.length}\0`).update(bytes).digest('hex');
    objects.set(id,{kind,bytes});return id;};
  const ident='Fixture <fixture@example.invalid> 1793404800 +0000';
  const empty=add('tree',Buffer.alloc(0));
  const base=add('commit',Buffer.from(`tree ${empty}\nauthor ${ident}\ncommitter ${ident}\n\nbase\n`));
  const target=add('commit',Buffer.from(`tree ${empty}\nparent ${base}\nauthor ${ident}\ncommitter ${ident}\n\nadvanced target\n`));
  const blob=add('blob',raw),entry={path:'identity.txt',mode:'100644',type:'blob',sha:blob};
  const tree=add('tree',Buffer.concat([Buffer.from('100644 identity.txt\0'),Buffer.from(blob,'hex')]));
  const head=add('commit',Buffer.from(`tree ${tree}\nparent ${base}\nauthor ${ident}\ncommitter ${ident}\n\noriginal source\n`));
  const b={version:2,repository:'maldous/offmenu',pr_number:null,
    issue_id:'12345678-1234-1234-1234-123456789abc',owner:'fixture-owner',
    head_branch:'feature/original-identity',head,base:target,tree,policy_sha256:'a'.repeat(64),
    capacity_policy_sha256:'b'.repeat(64),validation_operation_key:'c'.repeat(64),outputs:{'identity.txt':sha(raw)}};
  const source={repository:b.repository,branch:b.head_branch,head,base,tree,target:'develop',policy_sha256:b.policy_sha256};
  const native={issue_id:b.issue_id,project_id:'ffb6c7d9-4eff-46eb-a805-99f0cc2edfa0',owner:b.owner,
    unit_sha256:'d'.repeat(64),packet_sha256:'e'.repeat(64),source};
  b.source_projection={version:1,profile:'identity-client-focused',
    source:{head,base,tree,branch:b.head_branch},target:{base:target,tree:empty},merge_tree:tree,
    outputs:b.outputs,unit_sha256:native.unit_sha256,operation_key:b.validation_operation_key,
    receipt:{path:'/private/original-receipt.json',sha256:'f'.repeat(64)},review_sha256:'1'.repeat(64)};
  const op=(kind,id,body)=>({kind,method:'POST',path:`/repos/maldous/offmenu/git/${kind}s`,
    readPath:`/repos/maldous/offmenu/git/${kind}s/${id}`,expected:id,body});
  const who={name:'Fixture',email:'fixture@example.invalid',date:'2026-10-31T00:00:00+00:00'};
  const tail=[{kind:'ref',method:'POST',path:'/repos/maldous/offmenu/git/refs',
    readPath:`/repos/maldous/offmenu/git/ref/heads/${b.head_branch}`,expected:null,
    body:{ref:`refs/heads/${b.head_branch}`,sha:head}},
    {kind:'create-pr',method:'POST',path:'/repos/maldous/offmenu/pulls',
      readPath:`/repos/maldous/offmenu/pulls?state=all&head=maldous:${b.head_branch}&base=develop`,
      expected:head,body:{title:'Original reviewed source',body:'Original unit evidence',base:'develop',head:b.head_branch}}];
  const plan={changedFiles:b.outputs,operations:[op('blob',blob,{content:raw.toString('base64'),encoding:'base64'}),
    op('tree',tree,{tree:[entry]}),op('commit',head,{message:'original source\n',tree,parents:[base],author:who,committer:who}),...tail]};
  const snapshot={publisher_owner:b.owner,source_tree:tree,native_runtime:native,
    validation:{head,base,operation_key:b.validation_operation_key,outputs:b.outputs},
    review:{head,base,independent:true,evidence_id:'original-review',verdict:'accept',findings:[]}};
  b.publication={plan_sha256:fingerprint(plan),qualification_sha256:fingerprint(snapshot)};
  const pins=['tools/delivery/github-app-publisher.mjs','tools/delivery/github-app-adapter.mjs',
    'tools/delivery/integration-gateway.mjs','src/offmenu/delivery/integration.py',
    'src/offmenu/delivery/engine.py','src/offmenu/__init__.py','src/offmenu/delivery/__init__.py',
    'src/offmenu/delivery/identity_source_projection.py'];
  const config={version:1,appId:12,installationId:34,repositoryId:1416253963,publisherUid:2345,publisherGid:3456,
    logicalOwner:b.owner,sourceHead:'2'.repeat(40),pythonSha256:'3'.repeat(64),
    codePins:Object.fromEntries(pins.map(p=>[p,'4'.repeat(64)])),binding:b,snapshot,plan,workspace:'/synthetic/source'};
  const request={version:1,mode:'step',operation_id:fingerprint(b),issue_id:native.issue_id,
    project_id:native.project_id,owner:native.owner,unit_sha256:native.unit_sha256,
    packet_sha256:native.packet_sha256,source_sha256:fingerprint(source)};
  const qualify=()=>qualifyCandidate(config,{branchHead:head,
    readObject:async(kind,id)=>{assert.equal(objects.get(id)?.kind,kind);return objects.get(id).bytes;},
    readChangedFile:async path=>{assert.equal(path,'identity.txt');return raw;}});
  return {config,request,qualify,base,head,tree,objects};
}
test('original reviewed commit publishes against a distinct sealed target without relabelling native evidence',async()=>{
  const f=fixture(),before=structuredClone(f.config.snapshot);
  validateConfig(f.config,{uid:2345,euid:2345,gid:3456,egid:3456});
  assert.equal(qualifySourceProjection(f.config).source.base,f.base);
  await f.qualify();
  assert.equal(qualifyNativeRequest(f.config,f.request).source_sha256,fingerprint(before.native_runtime.source));
  assert.deepEqual(f.config.snapshot,before);
  assert.equal(f.config.plan.operations.find(o=>o.kind==='commit').body.parents[0],f.base);
  assert.notEqual(f.config.binding.base,f.base);
  const op=f.config.plan.operations.at(-1),b=f.config.binding,repo={id:1416253963,full_name:b.repository};
  const pr={number:201,base:{repo,ref:'develop',sha:b.base},head:{repo,ref:b.head_branch,sha:b.head},
    title:op.body.title,body:op.body.body,state:'open',draft:false,merged_at:null};
  assert.equal(canonicalPublication(op,[pr],b),true);
  pr.base.sha=f.base;assert.equal(canonicalPublication(op,[pr],b),false);
});
test('no projection cannot relax the original single-parent or native source-base association',async()=>{
  const f=fixture();delete f.config.binding.source_projection;
  await assert.rejects(f.qualify(),/publisher-held/);
  assert.throws(()=>qualifyNativeRequest(f.config,f.request),/publisher-held/);
});
test('source projection rejects source relabelling, unit drift, profile changes and missing helper pin',()=>{
  for(const change of [c=>{c.snapshot.native_runtime.source.base=c.binding.base;},
    c=>{c.snapshot.validation.base=c.binding.base;},c=>{c.binding.source_projection.unit_sha256='0'.repeat(64);},
    c=>{c.binding.source_projection.profile='other';},
    c=>{delete c.codePins['src/offmenu/delivery/identity_source_projection.py'];}]) {
    const f=fixture();change(f.config);
    assert.throws(()=>validateConfig(f.config,{uid:2345,euid:2345,gid:3456,egid:3456}),/publisher-held/);
  }
});
test('projected publication keeps raw object and exact target-tree checks',async()=>{
  const f=fixture();f.config.binding.source_projection.target.tree='0'.repeat(40);
  await assert.rejects(f.qualify(),/publisher-held/);
  const raw=fixture();raw.objects.get(raw.head).bytes=Buffer.from('different commit');
  await assert.rejects(raw.qualify(),/publisher-held/);
});
test('a projected object plan cannot smuggle another changed output',async()=>{
  const f=fixture();f.config.plan.changedFiles={...f.config.plan.changedFiles,'other.txt':'0'.repeat(64)};
  f.config.binding.publication.plan_sha256=fingerprint(f.config.plan);
  await assert.rejects(f.qualify(),/publisher-held/);
});
