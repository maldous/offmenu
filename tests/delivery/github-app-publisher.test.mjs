import test from 'node:test';
import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
import {mkdtemp,writeFile,readFile,rm} from 'node:fs/promises';
import {tmpdir} from 'node:os';
import {join,resolve} from 'node:path';
import {spawn} from 'node:child_process';
import {fileURLToPath} from 'node:url';
import {createRepositoryGitHubAppAdapter} from '../../tools/delivery/github-app-adapter.mjs';
import {advanceIntegration,advanceRelease} from '../../tools/delivery/integration-gateway.mjs';
import {fingerprint,validateConfig,protectedRead,loadProtectedConfig,loadProtectedKey,
  qualifyCandidate,canonicalPublication,publicationStep,integrationStep} from '../../tools/delivery/github-app-publisher.mjs';

// Synthetic identities, credentials, objects and transport ONLY. Fixed host paths
// below are handled by fake metadata/readers, never real /etc or home probes.
const ROOT='/repos/maldous/offmenu', perms={contents:'write',pull_requests:'write',metadata:'read'};
const repo={id:1416253963,full_name:'maldous/offmenu'};
const epoch=Date.parse('2026-10-31T00:00:00Z')/1000;
const digest=b=>createHash('sha256').update(b).digest('hex');
const gitHash=(type,b)=>createHash('sha1').update(`${type} ${b.length}\0`).update(b).digest('hex');
const codePaths=['tools/delivery/github-app-publisher.mjs','tools/delivery/github-app-adapter.mjs',
  'tools/delivery/integration-gateway.mjs','src/offmenu/delivery/integration.py',
  'src/offmenu/delivery/engine.py','src/offmenu/__init__.py','src/offmenu/delivery/__init__.py'];
const clone=structuredClone;
const objectOp=(kind,sha,body)=>({kind,method:'POST',path:`${ROOT}/git/${{blob:'blobs',tree:'trees',commit:'commits'}[kind]}`,
  body,readPath:`${ROOT}/git/${{blob:'blobs',tree:'trees',commit:'commits'}[kind]}/${sha}`,expected:sha});
function fixture() {
  const objects=new Map(), raw=Buffer.from('synthetic candidate\n');
  const add=(type,b)=>{const sha=gitHash(type,b);objects.set(sha,{type,raw:b});return sha;};
  const blob=add('blob',raw), empty=add('tree',Buffer.alloc(0));
  const identity=`Dummy <dummy@example.invalid> ${epoch} +0000`;
  const base=add('commit',Buffer.from(`tree ${empty}\nauthor ${identity}\ncommitter ${identity}\n\nbase\n`));
  const tree=add('tree',Buffer.concat([Buffer.from('100644 a.txt\0'),Buffer.from(blob,'hex')]));
  const head=add('commit',Buffer.from(`tree ${tree}\nparent ${base}\nauthor ${identity}\ncommitter ${identity}\n\nreviewed candidate\n`));
  const who={name:'Dummy',email:'dummy@example.invalid',date:'2026-10-31T00:00:00+00:00'};
  const binding={version:2,repository:repo.full_name,pr_number:null,
    issue_id:'8daac134-01ab-4a02-a4d2-c0c417d0bd32',owner:'synthetic-owner',
    head_branch:'feature/synthetic-publisher',head,base,tree,policy_sha256:'d'.repeat(64),
    capacity_policy_sha256:'e'.repeat(64),validation_operation_key:'f'.repeat(64),outputs:{'a.txt':digest(raw)}};
  const snapshot={publisher_owner:binding.owner,policy_sha256:binding.policy_sha256,
    capacity_policy_sha256:binding.capacity_policy_sha256,
    validation:{operation_key:binding.validation_operation_key,status:'succeeded',head,base,
      capacity_policy_sha256:binding.capacity_policy_sha256,outputs:binding.outputs,
      child_tree_gone:true,reconcile_required:false},
    review:{head,base,independent:true,evidence_id:'synthetic-review',verdict:'accept',findings:[]},
    unresolved_findings:[],source_tree:tree,source_clean:true,publication_triggers_actions:false,
    automatic_integration_enabled:true};
  const operations=[objectOp('blob',blob,{content:raw.toString('base64'),encoding:'base64'}),
    objectOp('tree',tree,{tree:[{path:'a.txt',mode:'100644',type:'blob',sha:blob}]}),
    objectOp('commit',head,{message:'reviewed candidate\n',tree,parents:[base],author:who,committer:who}),
    {kind:'ref',method:'POST',path:`${ROOT}/git/refs`,body:{ref:`refs/heads/${binding.head_branch}`,sha:head},
      readPath:`${ROOT}/git/ref/heads/${binding.head_branch}`,expected:null},
    {kind:'create-pr',method:'POST',path:`${ROOT}/pulls`,
      body:{title:'Reviewed fixture',body:'synthetic metadata',base:'develop',head:binding.head_branch},
      readPath:`${ROOT}/pulls?state=all&head=maldous:${binding.head_branch}&base=develop`,expected:head},
    {kind:'update-pr',method:'PATCH',path:`${ROOT}/pulls/{canonical}`,
      body:{title:'Reviewed fixture updated',body:'synthetic updated metadata',base:'develop'},
      readPath:`${ROOT}/pulls/{canonical}`,expected:head}];
  const plan={operations,changedFiles:{'a.txt':digest(raw)}};
  binding.publication={plan_sha256:fingerprint(plan),qualification_sha256:fingerprint(snapshot)};
  const config={version:1,appId:12,installationId:34,repositoryId:repo.id,publisherUid:2345,publisherGid:3456,
    logicalOwner:binding.owner,sourceHead:'1'.repeat(40),codePins:Object.fromEntries(codePaths.map(p=>[p,'2'.repeat(64)])),
    pythonSha256:'3'.repeat(64),binding,snapshot,plan,workspace:'/synthetic/candidate'};
  return {config,objects,raw,qualify:()=>qualifyCandidate(config,{branchHead:head,
    readObject:async(type,id)=>{assert.equal(objects.get(id)?.type,type);return objects.get(id).raw;},
    readChangedFile:async path=>{assert.equal(path,'a.txt');return raw;}})};
}
function metadataIO(config) {
  const files=new Map([['/etc/offmenu-publisher/config.json',Buffer.from(JSON.stringify(config))],
    ['/etc/offmenu-publisher/github-app-private-key.pem',Buffer.from('DUMMY-SYNTHETIC-KEY')]]);
  const changes=new Map(),opened=[];
  const stat=path=>Object.assign({uid:0,gid:3456,mode:files.has(path)?0o100440:0o40750,
    nlink:1,size:files.get(path)?.length??0,ino:files.has(path)?5:6,dev:7,
    isFile:()=>files.has(path),isDirectory:()=>!files.has(path)},changes.get(path));
  return {changes,opened,files,realpathSync:p=>p,lstatSync:stat,
    openSync:(path,flags)=>{opened.push({path,flags});return path;},fstatSync:stat,
    readFileSync:fd=>files.get(fd),closeSync:()=>{}};
}
const uid={uid:2345,euid:2345,gid:3456,egid:3456};
test('normal protected config/key loader uses only fixed paths and synthetic metadata',()=>{
  const {config}=fixture(),io=metadataIO(config);
  assert.equal(loadProtectedConfig({io,identity:uid}).appId,12);
  assert.equal(loadProtectedKey(config,{io}).toString(),'DUMMY-SYNTHETIC-KEY');
  assert.deepEqual(io.opened.map(x=>x.path),['/etc/offmenu-publisher/config.json',
    '/etc/offmenu-publisher/github-app-private-key.pem']);
  for(const path of ['/etc/offmenu-publisher/config.json','/etc/offmenu-publisher/github-app-private-key.pem']) {
    for(const change of [{uid:1000},{nlink:2},{mode:0o100640},{size:2**21},{isFile:()=>false}]) {
      const bad=metadataIO(config);bad.changes.set(path,change);
      assert.throws(()=>path.endsWith('config.json')?loadProtectedConfig({io:bad,identity:uid}):loadProtectedKey(config,{io:bad}),/publisher-held/);
      assert.equal(bad.opened.length,0);
    }
  }
  for(const change of [{uid:1000},{mode:0o40770},{gid:1}]) {
    const bad=metadataIO(config);bad.changes.set('/etc/offmenu-publisher',change);
    assert.throws(()=>loadProtectedKey(config,{io:bad}),/publisher-held/);
  }
  const symlink=metadataIO(config);symlink.realpathSync=()=>'/foreign';
  assert.throws(()=>protectedRead('/etc/offmenu-publisher/config.json',{io:symlink}));
  const race=metadataIO(config);race.fstatSync=p=>({...race.lstatSync(p),ino:99});
  assert.throws(()=>loadProtectedKey(config,{io:race}));
});
test('actual config/identity guards reject unknown IDs, root/coding IDs, foreign scope and hooks',()=>{
  const {config}=fixture();validateConfig(config,uid);
  for(const change of [{appId:null},{installationId:0},{repositoryId:1},{publisherUid:1000},
    {publisherGid:0},{logicalOwner:'foreign'},{loadPrivateKey:'/tmp/key'},{workspace:'relative'},
    {sourceHead:null},{codePins:{}}]) assert.throws(()=>validateConfig({...config,...change},uid));
  for(const change of [{uid:0},{uid:1000},{euid:0},{gid:1000},{egid:0}])
    assert.throws(()=>loadProtectedConfig({io:metadataIO(config),identity:{...uid,...change}}));
});
test('qualifies exact local Git object identity and changed regular-file bytes',async()=>{
  const f=fixture();assert.equal(await f.qualify(),f.config.plan);
  const c=clone(f.config);c.plan.operations[2].body.committer.name='rewritten';
  c.binding.publication.plan_sha256=fingerprint(c.plan);
  await assert.rejects(()=>qualifyCandidate(c,{branchHead:c.binding.head,
    readObject:async(type,id)=>f.objects.get(id).raw,readChangedFile:async()=>f.raw}));
  await assert.rejects(()=>qualifyCandidate(f.config,{branchHead:'0'.repeat(40),readObject:async()=>Buffer.alloc(0)}));
  await assert.rejects(()=>qualifyCandidate(f.config,{branchHead:f.config.binding.head,
    readObject:async(type,id)=>f.objects.get(id).raw,readChangedFile:async()=>Buffer.from('tamper')}));
  const head=f.objects.get(f.config.binding.head);head.raw=Buffer.from('unsafe signed commit');
  await assert.rejects(f.qualify);
});

async function actualController(t,f) {
  const temp=await mkdtemp(join(tmpdir(),'offmenu-publisher-'));t.after(()=>rm(temp,{recursive:true,force:true}));
  const configPath=join(temp,'synthetic-config.json');
  await writeFile(configPath,JSON.stringify(f.config));
  const invoke=async(op,data={})=>new Promise((resolvePromise,reject)=>{
    const code=`import json,sys; from pathlib import Path; from offmenu.delivery.integration import Controller,_publisher_request,publisher_directory; c=json.load(open(sys.argv[1])); ctl=Controller(publisher_directory(Path(sys.argv[2]),c['binding']),c['binding'],Path(sys.argv[2])); r=_publisher_request(ctl,c,json.load(sys.stdin)); print(json.dumps(r))`;
    const child=spawn(process.env.OFFMENU_DELIVERY_TEST_PYTHON || fileURLToPath(new URL('../../.venv-delivery/bin/python',import.meta.url)),['-B','-c',code,configPath,temp],
      {cwd:resolve('.'),env:{PATH:'/usr/bin:/bin',PYTHONPATH:resolve('src'),LANG:'C.UTF-8',PYTHONDONTWRITEBYTECODE:'1'},
        stdio:['pipe','pipe','pipe']});
    let out='',size=0;const timer=setTimeout(()=>child.kill('SIGKILL'),10000);
    child.stdout.on('data',b=>{size+=b.length;if(size>1048576)child.kill('SIGKILL');else out+=b;});
    child.stderr.on('data',b=>{size+=b.length;if(size>1048576)child.kill('SIGKILL');});
    child.on('error',reject);child.on('close',code=>{clearTimeout(timer);if(code)reject(Error('fixture-controller-held'));else {
      try{resolvePromise(JSON.parse(out));}catch(e){reject(e);}}});child.stdin.end(JSON.stringify({op,...data}));
  });
  invoke.state=()=>readFile(join(temp,'transaction-'+fingerprint(f.config.binding),'state.json'),'utf8').then(JSON.parse);
  invoke.config=async()=>writeFile(configPath,JSON.stringify(f.config));
  invoke.temp=temp;
  return invoke;
}
function syntheticHTTP(f,controller) {
  const remote=new Map(), calls=[];let pr=null, lost=false, failRead=false;
  const prValue=(body,number=247)=>({number,merged:false,merged_at:null,draft:false,state:'open',mergeable:true,
    title:body.title,body:body.body,head:{sha:f.config.binding.head,ref:f.config.binding.head_branch,repo},
    base:{sha:f.config.binding.base,ref:'develop',repo}});
  async function http(url,options) {
    const u=new URL(url),path=u.pathname+u.search;calls.push({path,method:options.method});
    assert.equal(u.origin,'https://api.github.com');assert.equal(options.redirect,'error');
    const body=options.body?JSON.parse(options.body):null;
    let status=200,data;
    if(path==='/app') data={id:12,permissions:perms};
    else if(path==='/app/installations/34') data={id:34,app_id:12,repository_selection:'selected',suspended_at:null,permissions:perms};
    else if(path==='/app/installations/34/access_tokens') {status=201;data={token:'DUMMY-ONLY-token',
      expires_at:new Date((epoch+3600)*1000).toISOString(),permissions:perms,repositories:[repo]};}
    else if(path==='/installation/repositories') data={total_count:1,repositories:[repo]};
    else if(path===`${ROOT}/pulls/247/reviews`||path===`${ROOT}/pulls/247/comments`) data=[];
    else if(path===`${ROOT}/pulls/247/merge`) {
      assert.equal(options.method,'PUT');pr.merged=true;pr.state='closed';pr.merge_commit_sha='4'.repeat(40);
      data={merged:true,sha:pr.merge_commit_sha};
      if(lost) throw Error('DUMMY-ONLY-secret');
    } else if(path.startsWith(`${ROOT}/commits/`)) {
      const id=path.slice(path.lastIndexOf('/')+1);data={sha:id,commit:{tree:{sha:f.config.binding.tree}},
        parents:(id===f.config.binding.head?[f.config.binding.base]:[f.config.binding.base,f.config.binding.head]).map(sha=>({sha}))};
    } else if(path.startsWith(`${ROOT}/compare/`)) data={status:'ahead',base_commit:{sha:'4'.repeat(40)},merge_base_commit:{sha:'4'.repeat(40)}};
    else if(options.method==='GET') {
      if(failRead) throw Error('DUMMY-ONLY-secret');
      if(path.includes('/pulls?')) data=pr?[pr]:[];
      else if(path===`${ROOT}/pulls/247`) data=pr;
      else data=remote.get(path)??null;
      if(data===null) status=404;
    } else {
      const state=await controller.state();
      assert.equal(state.publication.effect,'unknown','real durable consumption precedes mutation');
      const operation=state.publication.action;assert.equal(operation.path,path);
      assert.deepEqual(body,operation.body);
      status=options.method==='POST'?201:200;
      if(operation.kind==='blob') data={sha:operation.expected,encoding:'base64',content:body.content};
      else if(operation.kind==='tree') data={sha:operation.expected,truncated:false,tree:body.tree};
      else if(operation.kind==='commit') data={...body,sha:operation.expected,tree:{sha:body.tree},parents:body.parents.map(sha=>({sha}))};
      else if(operation.kind==='ref') data={ref:`refs/heads/${f.config.binding.head_branch}`,object:{type:'commit',sha:body.sha}};
      else if(operation.kind==='create-pr') {pr=prValue(body);data=pr;}
      else {Object.assign(pr,{title:body.title,body:body.body});data=pr;}
      if(!operation.kind.endsWith('-pr')) remote.set(operation.readPath,data);
      if(lost) throw Error('DUMMY-ONLY-secret');
    }
    return new Response(JSON.stringify(data),{status,headers:{'content-type':'application/json'}});
  }
  const factory=async({operation,index,number})=>createRepositoryGitHubAppAdapter({
    config:{appId:12,installationId:34,repositoryId:repo.id,publisherUid:2345},
    binding:{repository:repo.full_name,prNumber:number,headSha:f.config.binding.head,baseSha:f.config.binding.base,
      headBranch:f.config.binding.head_branch,intentSha256:fingerprint(operation)},
    publicationPlan:[operation],getUid:()=>2345,now:()=>epoch*1000,http,
    loadPrivateKey:async()=>Buffer.from('DUMMY-ONLY-key'),sign:async()=>Buffer.from('DUMMY-ONLY-signature'),
    authorizeIntent:async intent=>(await controller('consume',{intent})).authorized===true});
  return {factory,http,calls,remote,get pr(){return pr;},set pr(v){pr=v;},prValue,
    set lost(v){lost=v;},set failRead(v){failRead=v;},
    step:()=>publicationStep({config:f.config,controller,adapterFactory:factory,qualify:f.qualify})};
}

test('real Controller pending state drives synthetic blob/tree/commit/ref/PR create/update with canonical freeze',async t=>{
  const f=fixture(),ctl=await actualController(t,f),net=syntheticHTTP(f,ctl);
  for(let i=0;i<6;i++) await net.step();
  const state=await ctl.state();assert.equal(state.publication.effect,'verified');assert.equal(state.publication.pr_number,247);
  assert.equal(net.pr.title,'Reviewed fixture updated');
  assert.equal(f.config.binding.pr_number,null);
  assert.equal(net.calls.filter(c=>c.method==='POST'&&c.path===`${ROOT}/pulls`).length,1);
  assert.equal(net.calls.filter(c=>c.method==='PATCH').length,1);
  assert.ok((await readFile(join(ctl.temp,'transaction-'+fingerprint(f.config.binding),'graph.sqlite'))).length>0);
  const claim=await readFile(join(ctl.temp,'repository-claim.json'),'utf8');
  await ctl('status');assert.equal(await readFile(join(ctl.temp,'repository-claim.json'),'utf8'),claim);
  assert.ok(!JSON.stringify(state).includes('DUMMY-ONLY'));
});
test('lost blob/ref/PR replies reconcile by GET without second mutation after restart',async t=>{
  for(const target of [0,3,4]) {
    const f=fixture(),ctl=await actualController(t,f),net=syntheticHTTP(f,ctl);
    for(let i=0;i<target;i++) await net.step();
    net.lost=true;net.failRead=false;
    // Mutation succeeds remotely, reply lost; immediate canonical read may finish.
    await net.step();const mutations=net.calls.filter(c=>['POST','PATCH'].includes(c.method)&&!c.path.endsWith('access_tokens')).length;
    net.lost=false;await net.step();
    assert.equal(net.calls.filter(c=>['POST','PATCH'].includes(c.method)&&!c.path.endsWith('access_tokens')).length,mutations+1);
    // The +1 is the NEXT admitted object, never the lost operation replay.
    const path=f.config.plan.operations[target].path;
    assert.equal(net.calls.filter(c=>c.path===path&&c.method===f.config.plan.operations[target].method).length,1);
  }
});
test('pending/unknown consume is single use, refuses tamper, and absent readback remains held',async t=>{
  const f=fixture(),ctl=await actualController(t,f),net=syntheticHTTP(f,ctl);
  await ctl('prepare');const action=f.config.plan.operations[0];await ctl('intent',{index:0,action});
  await assert.rejects(()=>ctl('consume',{intent:{...action,path:'/repos/foreign/repo/git/blobs'}}));
  const consume=await Promise.allSettled([ctl('consume',{intent:action}),ctl('consume',{intent:action})]);
  assert.equal(consume.filter(r=>r.status==='fulfilled').length,1);
  await assert.rejects(()=>ctl('consume',{intent:action}));
  assert.deepEqual(await net.step(),{status:'publication-reconciliation-required'});
  assert.equal(net.calls.filter(c=>c.path===action.path&&c.method==='POST').length,0);
  await assert.rejects(()=>ctl('reconcile',{index:0,action,canonical:'0'.repeat(64),final:false}));
  await assert.rejects(()=>ctl('intent',{index:1,action:f.config.plan.operations[1]}));
});
test('foreign repo/ref/protected branch/arbitrary endpoint fail before key or HTTP',async()=>{
  for(const change of [o=>o.path='/repos/foreign/repo/git/blobs',o=>o.readPath='https://evil.invalid',
    o=>{o.kind='ref';o.method='PATCH';o.path=`${ROOT}/git/refs/heads/develop`;o.body={sha:'a'.repeat(40),force:true};},
    o=>{o.kind='create-pr';o.path=`${ROOT}/pulls`;o.body={title:'x',body:'',base:'main',head:'feature/foreign'};}]) {
    const f=fixture(),operation=clone(f.config.plan.operations[0]);change(operation);let effects=0;
    await assert.rejects(()=>createRepositoryGitHubAppAdapter({
      config:{appId:12,installationId:34,repositoryId:repo.id,publisherUid:2345},
      binding:{repository:repo.full_name,prNumber:null,headSha:f.config.binding.head,baseSha:f.config.binding.base,
        headBranch:f.config.binding.head_branch,intentSha256:'d'.repeat(64)},publicationPlan:[operation],
      getUid:()=>2345,loadPrivateKey:async()=>{effects++;},authorizeIntent:async()=>false,http:async()=>{effects++;}}));
    assert.equal(effects,0);
  }
});
test('PR creation canonical readback rejects wrong head/base/repo/metadata and duplicates',()=>{
  const f=fixture(),op=f.config.plan.operations[4];
  const p={number:247,state:'open',draft:false,merged_at:null,title:op.body.title,body:op.body.body,
    head:{ref:f.config.binding.head_branch,sha:f.config.binding.head,repo},
    base:{ref:'develop',sha:f.config.binding.base,repo}};
  assert.equal(canonicalPublication(op,[p],f.config.binding,null),true);
  for(const bad of [{...p,number:0},{...p,title:'other'},{...p,head:{...p.head,sha:'0'.repeat(40)}},
    {...p,base:{...p.base,ref:'main'}},{...p,head:{...p.head,repo:{id:1,full_name:'foreign/repo'}}}])
    assert.equal(canonicalPublication(op,[bad],f.config.binding,null),false);
  assert.equal(canonicalPublication(op,[p,p],f.config.binding,null),false);
});

test('published actual PR enters existing gateway; lost merge reply uses canonical parents/tree without replay',async t=>{
  const f=fixture();
  f.config.snapshot.github_review_facts_sha256=fingerprint({head:f.config.binding.head,base:f.config.binding.base,
    reviews:[],findings:[],qualification:'facts-only-requires-independent-owner-review-and-thread-resolution'});
  f.config.binding.publication.qualification_sha256=fingerprint(f.config.snapshot);
  const ctl=await actualController(t,f),net=syntheticHTTP(f,ctl);
  for(let i=0;i<6;i++) await net.step();
  const factory=options=>createRepositoryGitHubAppAdapter({...options,
    http:net.http,now:()=>epoch*1000,getUid:()=>2345,
    loadPrivateKey:async()=>Buffer.from('DUMMY-ONLY-key'),sign:async()=>Buffer.from('DUMMY-ONLY-signature')});
  net.lost=true;
  const result=await integrationStep({config:f.config,controller:ctl,adapterFactory:factory,advanceIntegration});
  assert.equal(result.status,'merge-verified');
  await integrationStep({config:f.config,controller:ctl,adapterFactory:factory,advanceIntegration});
  assert.equal(net.calls.filter(c=>c.method==='PUT').length,1);
  assert.equal((await ctl.state()).merge_effect,'verified');
});

test('Git Data GET fixtures normalize one terminal message newline without weakening identity',()=>{
  const f=fixture(),op=f.config.plan.operations[2];
  const response={...clone(op.body),sha:op.expected,message:'reviewed candidate',
    tree:{sha:op.body.tree},parents:op.body.parents.map(sha=>({sha})),
    url:'https://api.github.com/repos/maldous/offmenu/git/commits/'+op.expected,
    html_url:'https://github.com/maldous/offmenu/commit/'+op.expected,
    verification:{verified:false,reason:'unsigned',signature:null,payload:null,verified_at:null}};
  assert.equal(canonicalPublication(op,response,f.config.binding),true);
  for(const change of [{message:'reviewed candidate\n\n'},{message:'reviewed candidate altered'},
    {sha:'0'.repeat(40)},{tree:{sha:'0'.repeat(40)}},{parents:[{sha:'0'.repeat(40)}]},
    {author:{...op.body.author,name:'different'}}])
    assert.equal(canonicalPublication(op,{...response,...change},f.config.binding),false);
});

test('finite release gateway consumes typed promotion and tag phases without repeated effects',async()=>{
  const head='a'.repeat(40),base='b'.repeat(40),merged='c'.repeat(40);
  const branch='release/candidate-'+'1'.repeat(64);
  let phase=0,merges=0,tags=0;
  const github={getPullRequest:async()=>({merged:false,head_sha:head,base_sha:base,
    head:branch,base:'main',draft:false,mergeable:true}),
    mergePullRequest:async args=>{assert.equal(args.expected_head_sha,head);merges++;phase=1;},
    createReleaseTag:async sha=>{assert.equal(sha,merged);tags++;phase=2;}};
  const controller={step:async()=>phase===0?{status:'release-intent',action:{kind:'promote-release',
    repository:repo.full_name,pr_number:248,expected_head_sha:head,expected_base_sha:base,expected_head_branch:branch}}:
    phase===1?{status:'release-tag-intent',action:{kind:'create-release-tag',commit_sha:merged}}:
    {status:'release-verified',action:null}};
  const run=()=>advanceRelease({controller,github,observe:async()=>({})});
  assert.equal((await run()).status,'release-tag-intent');assert.equal(merges,1);assert.equal(tags,0);
  assert.equal((await run()).status,'release-verified');assert.equal(merges,1);assert.equal(tags,1);
  await run();assert.equal(merges,1);assert.equal(tags,1);
  phase=0;github.getPullRequest=async()=>({head_sha:'0'.repeat(40)});
  assert.equal((await run()).status,'release-reconciliation-required');assert.equal(merges,1);
});
