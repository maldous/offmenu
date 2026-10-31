import test from 'node:test';
import assert from 'node:assert/strict';
import {spawn} from 'node:child_process';
import {mkdtemp,readFile,rm} from 'node:fs/promises';
import {tmpdir} from 'node:os';
import {join,resolve} from 'node:path';
import {createRepositoryGitHubAppAdapter} from '../../tools/delivery/github-app-adapter.mjs';
import {advanceIntegration} from '../../tools/delivery/integration-gateway.mjs';

// All identities, signatures, keys and HTTP responses below are DUMMY fixtures.
const H='a'.repeat(40), B='b'.repeat(40), T='c'.repeat(40), M='2'.repeat(40);
const repo={id:1416253963,full_name:'maldous/offmenu'};
const perms={contents:'write',pull_requests:'write',metadata:'read'};
const clock=Date.parse('2026-10-31T00:00:00Z');
const binding={repository:repo.full_name,prNumber:145,headSha:H,baseSha:B,
  headBranch:'feature/repository-github-app-adapter',intentSha256:'d'.repeat(64)};
const mergeArgs={repository_full_name:repo.full_name,pr_number:145,expected_head_sha:H,merge_method:'merge'};
function fixture() {
  const f={calls:[],loads:0,signs:[],intents:[],uid:2345,time:clock};
  f.pr={number:145,merged:false,draft:false,state:'open',mergeable:true,
    head:{sha:H,ref:binding.headBranch,repo},base:{sha:B,ref:'develop',repo}};
  f.routes={
    '/app':{id:12,permissions:perms},
    '/app/installations/34':{id:34,app_id:12,permissions:perms,repository_selection:'selected',suspended_at:null},
    '/app/installations/34/access_tokens':{token:'DUMMY-installation-token-variable-length',
      expires_at:new Date(clock+3600000).toISOString(),permissions:perms,repositories:[repo]},
    '/installation/repositories':{total_count:1,repositories:[repo]},
    '/repos/maldous/offmenu/pulls/145/merge':{merged:true,sha:M},
    [`/repos/maldous/offmenu/commits/${H}`]:{sha:H,commit:{tree:{sha:T}},parents:[{sha:B}]},
    [`/repos/maldous/offmenu/commits/${M}`]:{sha:M,commit:{tree:{sha:T}},parents:[{sha:B},{sha:H}]},
    [`/repos/maldous/offmenu/compare/${M}...develop`]:{status:'ahead',base_commit:{sha:M},merge_base_commit:{sha:M}},
    '/repos/maldous/offmenu/pulls/145/reviews':[
      {id:1,user:{id:22},commit_id:H,state:'COMMENTED',body:'DUMMY-SECRET'},
      {id:2,user:{id:22},commit_id:B,state:'APPROVED'}],
    '/repos/maldous/offmenu/pulls/145/comments':[
      {id:3,user:{id:22},commit_id:H,body:'DUMMY-SECRET'},
      {id:4,user:{id:22},commit_id:B,body:'old'}]
  };
  f.options={config:{appId:12,installationId:34,repositoryId:repo.id,publisherUid:2345},binding:{...binding},
    getUid:()=>f.uid,now:()=>f.time,
    loadPrivateKey:async()=>{f.loads++;return 'DUMMY-key-capability';},
    sign:async(input,key)=>{assert.equal(key,'DUMMY-key-capability');f.signs.push(input);return Buffer.from('DUMMY-signature');},
    authorizeIntent:async intent=>{f.intents.push(intent);return true;},
    http:async(url,options)=>{
      f.calls.push({url,...options});
      assert.equal(new URL(url).origin,'https://api.github.com');
      assert.equal(new URL(url).search,'');assert.equal(options.redirect,'error');
      assert.deepEqual(Object.keys(options.headers).sort(),
        ['Accept','Authorization','X-GitHub-Api-Version',...(options.body?['Content-Type']:[])].sort());
      assert.equal(options.headers['X-GitHub-Api-Version'],'2022-11-28');
      assert.equal(options.headers.Accept,'application/vnd.github+json');
      assert.match(options.headers.Authorization,/^Bearer /);
      assert.ok(options.signal instanceof AbortSignal);
      const path=new URL(url).pathname;
      const data=path==='/repos/maldous/offmenu/pulls/145'?f.pr:f.routes[path];
      assert.ok(data,`unexpected endpoint ${path}`);
      if(f.respond) {const r=await f.respond(path,options);if(r) return r;}
      return new Response(JSON.stringify(data),{status:options.method==='POST'?201:200,
        headers:{'content-type':'application/json'}});
    }};
  f.make=()=>createRepositoryGitHubAppAdapter(f.options);
  f.puts=()=>f.calls.filter(c=>c.method==='PUT');
  return f;
}
function gateway(github) {
  const f={github,outcomes:[],observe:async()=>({}),linear:{}};
  let used=false;
  f.controller={step:async()=>used?{status:'merge-unknown',action:null}:
    (used=true,{status:'merge-intent',action:{kind:'merge-pr',repository:repo.full_name,
      pr_number:145,expected_head_sha:H,expected_base_sha:B,expected_head_branch:binding.headBranch}}),
    outcome:async(...args)=>{f.outcomes.push(args);return {status:'stopped'};}};
  return f;
}

test('actual gateway reads adapter then sends only exact merge body and scoped grant',async()=>{
  const f=fixture(), adapter=await f.make(), g=gateway(adapter);
  await advanceIntegration(g);
  assert.deepEqual(g.outcomes,[['merge','succeeded']]);
  assert.equal(f.puts().length,1);
  assert.equal(f.puts()[0].url,'https://api.github.com/repos/maldous/offmenu/pulls/145/merge');
  assert.deepEqual(JSON.parse(f.puts()[0].body),{sha:H,merge_method:'merge'});
  assert.equal(f.calls.filter(c=>c.url.endsWith('/pulls/145')).length,2);
  assert.deepEqual(JSON.parse(f.calls.find(c=>c.method==='POST').body),{repository_ids:[repo.id],permissions:perms});
  assert.deepEqual(f.intents,[{kind:'merge-pr',repository:repo.full_name,pr_number:145,
    expected_head_sha:H,expected_base_sha:B,expected_head_branch:binding.headBranch,
    merge_method:'merge',intent_sha256:binding.intentSha256}]);
  const [header,payload]=f.signs[0].split('.').map(s=>JSON.parse(Buffer.from(s,'base64url')));
  assert.deepEqual(header,{alg:'RS256',typ:'JWT'});
  assert.deepEqual(payload,{iat:clock/1000-60,exp:clock/1000+540,iss:12});
  assert.deepEqual(adapter.provenance,{kind:'github-app-installation',app_id:12,
    installation_id:34,repository_id:repo.id,publisher_uid:2345,os_isolation_verified:false});
  assert.equal(adapter.getProfile,undefined);
  assert.doesNotMatch(JSON.stringify([adapter,g.outcomes]),/DUMMY|Bearer|token|private.key/i);
});

test('stale/foreign/draft/unknown PR facts never PUT through real gateway',async()=>{
  for(const mutate of [p=>p.head.sha=B,p=>p.base.sha=H,p=>p.number=999,
    p=>p.head.repo={...repo,id:99},p=>p.base.repo={...repo,full_name:'evil/repo'},
    p=>p.head.ref='feature/foreign',p=>p.base.ref='main',p=>p.draft=true,
    p=>p.mergeable=null,p=>p.mergeable=false,p=>p.merged=true,p=>delete p.draft]) {
    const f=fixture();mutate(f.pr);const g=gateway(await f.make());await advanceIntegration(g);
    assert.equal(f.puts().length,0);assert.deepEqual(g.outcomes,[['merge','not-issued']]);
  }
  for(const [repository,number] of [['evil/repo',145],[repo.full_name,999]]) {
    const f=fixture(), a=await f.make();await assert.rejects(a.getPullRequest(repository,number));
    assert.equal(f.calls.length,4);
  }
});

test('fresh second read and durable intent refuse stale/racing/direct/extra/replayed mutation',async()=>{
  const f=fixture(),a=await f.make(); f.pr.base.sha=H;
  assert.deepEqual(await a.mergePullRequest(mergeArgs),{merged:false,known_refused:true});
  assert.equal(f.puts().length,0);
  for(const change of [{repository_full_name:'evil/repo'},{pr_number:999},{expected_head_sha:B},
    {merge_method:'squash'},{force:true},{bypass_flags:[]}]) {
    const f=fixture(),a=await f.make();await a.mergePullRequest({...mergeArgs,...change});assert.equal(f.puts().length,0);
  }
  const no=fixture();no.options.authorizeIntent=async()=>false;
  await (await no.make()).mergePullRequest(mergeArgs);assert.equal(no.puts().length,0);
  const replay=fixture(),r=await replay.make();await r.mergePullRequest(mergeArgs);await r.mergePullRequest(mergeArgs);
  assert.equal(replay.puts().length,1);
});

test('strict config and caller UID gate precede key and HTTP; no configured paths/commands',async()=>{
  for(const change of [{appId:0},{appId:'12'},{installationId:null},{repositoryId:1},
    {publisherUid:0},{publisherUid:1000},{publisherUid:1.5},{keyPath:'/tmp/key'},
    {command:'anything'},{host:'https://evil.invalid'}]) {
    const f=fixture();Object.assign(f.options.config,change);
    await assert.rejects(f.make(),/github_app_adapter_refused/);assert.equal(f.loads,0);assert.equal(f.calls.length,0);
  }
  const f=fixture();f.uid=1000;await assert.rejects(f.make());assert.equal(f.loads,0);
  const wrong=fixture();wrong.options.binding.intentSha256='';await assert.rejects(wrong.make());assert.equal(wrong.loads,0);
});

test('fresh App installation repository permissions scope expiry association fail closed',async()=>{
  for(const mutate of [
    f=>f.routes['/app'].id=99,
    f=>f.routes['/app/installations/34'].app_id=99,
    f=>f.routes['/app/installations/34'].id=99,
    f=>f.routes['/app/installations/34'].repository_selection='all',
    f=>f.routes['/app/installations/34'].suspended_at='date',
    f=>f.routes['/app'].permissions={...perms,actions:'write'},
    f=>f.routes['/app/installations/34/access_tokens'].permissions={...perms,issues:'read'},
    f=>f.routes['/app/installations/34/access_tokens'].repositories=[repo,{id:1}],
    f=>f.routes['/app/installations/34/access_tokens'].expires_at=new Date(clock-1).toISOString(),
    f=>f.routes['/app/installations/34/access_tokens'].expires_at=new Date(clock+7200000).toISOString(),
    f=>f.routes['/app/installations/34/access_tokens'].expires_at='invalid',
    f=>f.routes['/installation/repositories'].total_count=2,
    f=>f.routes['/installation/repositories'].repositories=[{...repo,id:9}]
  ]) {const f=fixture();mutate(f);await assert.rejects(f.make());assert.equal(f.puts().length,0);}
  const f=fixture(),a=await f.make();f.time+=3600000;await assert.rejects(a.getPullRequest(repo.full_name,145));
  const u=fixture(),b=await u.make();u.uid=1000;await assert.rejects(b.getPullRequest(repo.full_name,145));
});

test('redirects oversized/malformed bodies links HTTP errors and callbacks are sanitized',async()=>{
  for(const response of [
    ()=>new Response('DUMMY-SECRET',{status:302,headers:{location:'https://evil.invalid'}}),
    ()=>new Response('DUMMY-SECRET',{status:500}),
    ()=>new Response('bad DUMMY-SECRET',{headers:{'content-type':'application/json'}}),
    ()=>new Response(' '.repeat(1024*1024+1),{headers:{'content-type':'application/json'}}),
    ()=>new Response('{}',{headers:{'content-type':'application/json',link:'<https://evil.invalid>; rel="next"'}}),
    ()=>{throw Error('DUMMY-SECRET token=secret');}
  ]) {
    const f=fixture();f.respond=response;
    await assert.rejects(f.make(),e=>e.message==='github_app_adapter_refused' && !JSON.stringify(e).includes('DUMMY'));
  }
  const f=fixture();f.options.loadPrivateKey=()=>{throw Error('DUMMY-SECRET');};
  await assert.rejects(f.make(),e=>e.message==='github_app_adapter_refused');
});

test('mutation timeout/5xx/bad reply are uncertain, read failures not-issued/refused',async()=>{
  for(const status of ['timeout',500,'malformed',302]) {
    const f=fixture(),a=await f.make();
    f.respond=(path)=>{if(!path.endsWith('/merge'))return;
      if(status==='timeout')throw Object.assign(Error('DUMMY-SECRET timeout'),{knownRefused:true});
      return new Response(status==='malformed'?'bad':JSON.stringify({message:'DUMMY-SECRET'}),
        {status:typeof status==='number'?status:200,headers:{'content-type':'application/json'}});};
    const g=gateway(a);await advanceIntegration(g);assert.deepEqual(g.outcomes,[['merge','uncertain']]);
    assert.equal((await a.mergePullRequest(mergeArgs)).merged,false);assert.equal(f.puts().length,1);
  }
  for(const status of [403,409,422]) {
    const f=fixture(),a=await f.make();f.respond=p=>p.endsWith('/merge')?new Response('',{status}):undefined;
    const g=gateway(a);await advanceIntegration(g);assert.deepEqual(g.outcomes,[['merge','refused']]);
  }
  for(const status of [403,500]) {
    const f=fixture(),a=await f.make();f.respond=p=>p.endsWith('/145')?new Response('',{status}):undefined;
    const g=gateway(a);await advanceIntegration(g);
    assert.deepEqual(g.outcomes,[['merge',status===403?'refused':'not-issued']]);assert.equal(f.puts().length,0);
  }
});

test('canonical source commit/tree/parents/develop and exact-head review are facts only',async()=>{
  const f=fixture(),a=await f.make();
  assert.deepEqual(await a.readCanonicalFacts(M),{source_commit:{sha:H,tree:T,parents:[B]},
    merge_commit:{sha:M,tree:T,parents:[B,H]},develop_contains_merge:true});
  const facts=await a.readExactHeadReviewFacts();
  assert.deepEqual(facts.reviews,[{id:1,reviewer_id:22,state:'COMMENTED',head:H}]);
  assert.deepEqual(facts.findings,[{id:3,reviewer_id:22,head:H}]);
  assert.doesNotMatch(JSON.stringify(facts),/DUMMY|APPROVED|independent.*true/);
  f.routes[`/repos/maldous/offmenu/commits/${H}`].sha=B;
  await assert.rejects(a.readCanonicalFacts(M));
  await assert.rejects(a.readCanonicalFacts('../main?force=true'));
  assert.equal(f.calls.some(c=>c.method!=='GET' && c.method!=='POST'),false);
});

// Real pinned Python Controller, isolated synthetic state, never live owner state.
const python='/home/user/src/offmenu/.venv-delivery/bin/python';
async function controllerCall(directory,mode,b,snapshot) {
  return await new Promise((accept,reject)=>{
    const child=spawn(python,['-B','-c',
      'import json,sys\nfrom pathlib import Path\nfrom offmenu.delivery.integration import Controller\np=json.load(sys.stdin)\nc=Controller(Path(p["directory"]),p["binding"])\nr=c.run(p["snapshot"]) if p["mode"]=="step" else c.record_api_outcome("merge",p["mode"])\nprint(json.dumps(r))'],
    {cwd:resolve('.'),env:{PATH:'/usr/bin:/bin',PYTHONPATH:resolve('src'),LANG:'C.UTF-8'},stdio:['pipe','pipe','pipe']});
    let size=0,output='';const timer=setTimeout(()=>child.kill('SIGKILL'),15000);
    child.stdout.on('data',v=>{size+=v.length;if(size>1024*1024)child.kill('SIGKILL');else output+=v;});
    child.stderr.on('data',()=>{});child.on('error',reject);
    child.on('close',code=>{clearTimeout(timer);if(code!==0)reject(Error('synthetic controller failed'));else {
      try {accept(JSON.parse(output));}catch {reject(Error('synthetic controller bad reply'));}}});
    child.stdin.end(JSON.stringify({directory,mode,binding:b,snapshot}));
  });
}
test('real gateway and Controller retain uncertain intent and never automatically repeat merge',async()=>{
  const root=await mkdtemp(join(tmpdir(),'offmenu-app-adapter-'));
  const directory=join(root,'selected');
  try {
    const b={version:1,repository:repo.full_name,pr_number:145,
      issue_id:'8daac134-01ab-4a02-a4d2-c0c417d0bd32',owner:'DUMMY-owner',head_branch:binding.headBranch,
      head:H,base:B,tree:T,policy_sha256:'d'.repeat(64),capacity_policy_sha256:'e'.repeat(64),
      validation_operation_key:'f'.repeat(64),outputs:{'tests/behavior.py':'1'.repeat(64)}};
    const snapshot={observed_at:Date.now()/1000,publisher_owner:b.owner,
      github:{repository:repo.full_name,number:145,merged:false,state:'open',draft:false,head:H,base:B,
        head_branch:binding.headBranch,base_branch:'develop',mergeable:true},
      policy_sha256:b.policy_sha256,capacity_policy_sha256:b.capacity_policy_sha256,
      validation:{operation_key:b.validation_operation_key,status:'succeeded',head:H,base:B,
        capacity_policy_sha256:b.capacity_policy_sha256,outputs:b.outputs,child_tree_gone:true,reconcile_required:false},
      review:{head:H,base:B,independent:true,evidence_id:'DUMMY-review',verdict:'accept',findings:[]},
      unresolved_findings:[],source_tree:T,source_clean:true,publication_triggers_actions:false,automatic_integration_enabled:true};
    const f=fixture();
    f.options.authorizeIntent=async intent=>{
      const state=JSON.parse(await readFile(join(directory,'state.json'),'utf8'));
      return state.merge_effect==='pending' && state.action.expected_head_sha===intent.expected_head_sha &&
        state.action.expected_base_sha===intent.expected_base_sha && intent.intent_sha256===binding.intentSha256;
    };
    const github=await f.make();f.respond=p=>{if(p.endsWith('/merge')) throw Error('DUMMY lost reply');};
    const controller={step:s=>controllerCall(directory,'step',b,s),outcome:(_,o)=>controllerCall(directory,o,b,snapshot)};
    const args={controller,github,linear:{},observe:async()=>snapshot};
    await advanceIntegration(args);await advanceIntegration(args);
    const state=JSON.parse(await readFile(join(directory,'state.json'),'utf8'));
    assert.equal(state.merge_effect,'unknown');assert.equal(state.action,null);
    assert.equal(f.puts().length,1);
  } finally {await rm(root,{recursive:true,force:true});}
});
