/** Offline synthetic boundaries. Fixture adapters are not live acceptance. */
import test from 'node:test';
import assert from 'node:assert/strict';
import {execFile, spawn} from 'node:child_process';
import {promisify} from 'node:util';
import {mkdtempSync, readFileSync, writeFileSync, rmSync} from 'node:fs';
import {tmpdir} from 'node:os';
import {join, resolve} from 'node:path';
import {pathToFileURL} from 'node:url';
import {createHash, randomBytes} from 'node:crypto';

const python='/home/user/src/offmenu/.delivery/stokowski/venv/bin/python';
const source=resolve(import.meta.dirname,'../..');
const sha=s=>createHash('sha256').update(s).digest('hex');
// Reuse only the accepted fixture builder, never its historical test methods.
const setup=String.raw`
import importlib.util, json, pathlib, shutil, subprocess, sys, tempfile
repo, parent, mode = map(str, sys.argv[1:])
tempfile.tempdir = parent
spec = importlib.util.spec_from_file_location('fixture', pathlib.Path(repo)/'tests/delivery/test_stokowski_prepare_publication.py')
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)
if mode.startswith('successor'):
    sys.path.insert(0,str(pathlib.Path(repo)/'tests/delivery'))
    from test_stokowski_current_dispatch import CurrentDispatchTests
    original_temp = tempfile.TemporaryDirectory
    def retained_temp(*args,**kwargs):
        value=original_temp(*args,**kwargs)
        value._finalizer.detach()
        return value
    tempfile.TemporaryDirectory=retained_temp
    c=CurrentDispatchTests()
    c.successor_real=True
    c.setUp()
    f,issue,runtime,owner,client,review,journal,key=c.successor_fixture(real=True, fault='uncertain' if mode=='successor-uncertain' else None)
    if mode == 'successor-cancelled':
        _,state=journal.read(key)
        journal.save(key,dict(state,cancel_requested=True),'synthetic cancellation after request')
    context=dict(source_head=c.current.config['source_head'],source_branch='feature/test-current',
        source_sha256=c.current.config['source_sha256'],python_sha256=f.sha(pathlib.Path(sys.executable).resolve()),
        handoff=f.ref(f.handoff_path),owner_config=f.ref(f.qualified/'config.json'))
    print(json.dumps(dict(root=str(c.source),context=context,catalog=str(f.catalog),runtime=str(f.runtime),
        coordinator=str(c.runtime),original_runtime=str(runtime),task_source=f.packet['source'])))
    sys.exit(0)
f = m.PublicationTests()
f.setUp()
f.temporary._finalizer.detach()
# Fixture setup patches only its process; production consumer uses real git.
# enterContext cleanup patches are explicitly unwound without deleting fixture.
for function, args, kwargs in reversed(f._cleanups):
    if getattr(function, '__name__', '') == '__exit__':
        function(*args, **kwargs)
for p in (pathlib.Path(repo)/'tools/delivery').glob('*.py'):
    shutil.copyfile(p, f.source/'tools/delivery'/p.name)
shutil.copyfile(pathlib.Path(repo)/'tools/delivery/integration-gateway.mjs', f.source/'tools/delivery/integration-gateway.mjs')
shutil.copyfile(pathlib.Path(repo)/'tools/delivery/capacity-policy.json', f.source/'tools/delivery/capacity-policy.json')
# Synthetic trusted provider replaces the probe in this temporary source only.
launch = f.source/'tools/delivery/symphony_launch.py'
s = launch.read_text()
a, b = s.index('def provider_proof('), s.index('\ndef default_manifest(')
body = '''def provider_proof(model, ceiling):
    marker = SOURCE/'.delivery/provider-calls'
    marker.write_text(marker.read_text()+'x' if marker.exists() else 'x')
    return dict(route='codex-chatgpt', available=True, checked_at=time.time(), requested_model=model, session_ceiling=ceiling)
'''
if mode == 'refused':
    body = body.replace('available=True', 'available=False')
if mode == 'uncertain':
    body = body[:body.index('    return')] + "    raise OSError('synthetic uncertainty')\n"
launch.write_text(s[:a]+body+s[b:])
if mode == 'lost-reply':
    consumer=f.source/'tools/delivery/stokowski_publication.py'
    consumer.write_text(consumer.read_text().replace('sys.stdout.write(json.dumps(reply,', "if decode(data)['mode'] == 'prepare':\n        sys.exit(7)\n    sys.stdout.write(json.dumps(reply,"))
if mode in ('response-hash', 'response-binding'):
    consumer=f.source/'tools/delivery/stokowski_publication.py'
    text=consumer.read_text()
    if mode == 'response-hash':
        text=text.replace('response_sha256=sha(response.encode())', "response_sha256='0'*64")
    else:
        text=text.replace("request_sha256=wire['request_sha256'],\n                                   result=result", "request_sha256='0'*64,\n                                   result=result")
    consumer.write_text(text)
if mode in ('large-source', 'oversized-source'):
    adapter=f.source/'tools/delivery/stokowski_adapter.py'
    size = 128 * 1024 if mode == 'large-source' else 1024 * 1024 + 1
    adapter.write_text(adapter.read_text() + '\n#' + 'x' * size + '\n')
(f.source/'.gitignore').write_text('.delivery/\n__pycache__/\n')
(f.source/'package.json').write_text('{"type":"module"}')
def git(*args):
    return subprocess.check_output(['/usr/bin/git','-C',str(f.source),*args], stderr=subprocess.DEVNULL).decode().strip()
separate = mode.startswith('source-separation')
git('init','-b','develop' if separate else f.branch)
git('add','.')
git('-c','user.name=Synthetic','-c','user.email=synthetic@example.invalid','-c','commit.gpgsign=false','commit','-m','Offline synthetic source')
installation_head=git('rev-parse','HEAD')
installation_branch=git('branch','--show-current')
f.base=installation_head
gateway=f.source
if separate:
    task=f.directory/'task-source'
    (task/'tools/delivery').mkdir(parents=True)
    shutil.copyfile(gateway/'tools/delivery/capacity-policy.json', task/'tools/delivery/capacity-policy.json')
    subprocess.check_call(['/usr/bin/git','init','-q','-b',f.branch,str(task)])
    def task_git(*args):
        return subprocess.check_output(['/usr/bin/git','-C',str(task),*args], stderr=subprocess.DEVNULL).decode().strip()
    task_git('add','.')
    task_git('-c','user.name=Synthetic','-c','user.email=synthetic@example.invalid','-c','commit.gpgsign=false','commit','-m','Separate synthetic task source')
    f.base=task_git('rev-parse','HEAD')
    f.source=task  # repin the task policy; runtime/config stay with the gateway owner.
    f.packet['source']['source_checkout']=str(task)
f.packet['source']['base']=f.base
f.manifest['base_revision']=f.base
f.write(f.qualified/'manifest.json', f.manifest)
f.handoff['source_base']=f.base
if mode == 'source-separation-checkout':
    f.packet['source']['source_checkout']=str(gateway)
if mode == 'source-separation-manifest':
    f.manifest['branch']='feature/unbound'
    f.write(f.qualified/'manifest.json', f.manifest)
f.repin()
if mode == 'source-separation-head':
    task_git('-c','user.name=Synthetic','-c','user.email=synthetic@example.invalid','-c','commit.gpgsign=false','commit','--allow-empty','-m','Unbound head')
if mode == 'source-separation-branch':
    task_git('branch','-m','feature/unbound')
f.source=gateway
context=dict(source_head=installation_head, source_branch=installation_branch,
    source_sha256={str(p.relative_to(f.source)): f.sha(p) for p in (f.source/'tools/delivery').iterdir() if p.suffix in ('.py','.mjs')},
    python_sha256=f.sha(pathlib.Path(sys.executable).resolve()),
    handoff=f.ref(f.handoff_path), owner_config=f.ref(f.qualified/'config.json'))
print(json.dumps(dict(root=str(f.source), context=context, catalog=str(f.catalog), runtime=str(f.runtime), task_source=f.packet['source'])))
`;
async function fixture(t, mode='good') {
  const directory=mkdtempSync(join(tmpdir(),'owner-publication-test-'));
  t.after(()=>rmSync(directory,{recursive:true,force:true}));
  const f=JSON.parse((await promisify(execFile)(python,['-B','-c',setup,source,directory,mode],{timeout:5000,maxBuffer:65536,env:{PATH:'/usr/bin:/bin',LANG:'C.UTF-8',PYTHONPATH:`${source}/src`}})).stdout);
  f.catalogBefore=readFileSync(f.catalog);
  f.marker=join(f.root,'.delivery/provider-calls');
  f.journal=join(f.root,'.delivery/stokowski',`owner-bridge-${f.context.handoff.sha256}.json`);
  return f;
}
async function action(f, profile={id:123,login:'synthetic'}) {
  const {prepareOwnerPublication}=await import(pathToFileURL(join(f.root,'tools/delivery/integration-gateway.mjs')));
  let calls=0;
  const result=await prepareOwnerPublication({github:{getProfile:async()=>{calls++;return profile;}},reviewedPublication:f.context});
  assert.equal(calls,1);
  return result;
}
function envelope(f) {
  return {context:f.context,nonce:randomBytes(32).toString('hex'),observed_at:Date.now()/1000,
    provenance:{service:'github',connector_tool:'mcp__codex_apps__github_get_profile',flow:'same-invocation-getProfile-to-fixed-stdin'},
    principal:{service:'github',principal_id:'123',login:'synthetic'}};
}
async function stdin(f, e, mode='prepare', hash) {
  const payload=JSON.stringify(e);
  const input=JSON.stringify({version:1,mode,payload,request_sha256:hash??sha(payload)});
  const r=await new Promise((resolve,reject)=>{
    const child=spawn(python,['-B',join(f.root,'tools/delivery/stokowski_publication.py')],{
      env:{PATH:'/usr/bin:/bin',LANG:'C.UTF-8'},stdio:['pipe','pipe','pipe']});
    let stdout='';
    child.stdout.on('data',chunk=>{stdout+=chunk;});
    child.stderr.resume();
    child.on('error',reject);
    child.stdin.on('error',()=>{});
    child.on('close',status=>resolve({status,stdout}));
    child.stdin.end(input);
  });
  if(r.status!==0)return {code:r.status};
  const reply=JSON.parse(r.stdout);
  assert.equal(reply.response_sha256,sha(reply.response));
  const response=JSON.parse(reply.response);
  assert.equal(response.nonce,e.nonce);
  assert.equal(response.request_sha256,sha(payload));
  assert.equal(response.result.dispatches,0);
  return {code:0,result:response.result};
}
function noProbe(f) {
  assert.throws(()=>readFileSync(f.marker),{code:'ENOENT'});
  assert.deepEqual(readFileSync(f.catalog),f.catalogBefore);
}

test('actual gateway fresh callback and fixed stdin consume accepted API with zero dispatch',async t=>{
  const f=await fixture(t);
  assert.equal((await action(f)).status,'published');
  assert.equal(readFileSync(f.marker,'utf8'),'x');
  assert.equal(JSON.parse(readFileSync(f.journal)).status,'published');
  assert.equal(JSON.parse(readFileSync(f.catalog)).entries.length,1);
  await assert.rejects(action(f)); // New nonce cannot republish the handoff.
  assert.equal(readFileSync(f.marker,'utf8'),'x');
});

test('reviewed source blob above wire limit publishes without raising message limit',async t=>{
  const f=await fixture(t,'large-source');
  assert.ok(readFileSync(join(f.root,'tools/delivery/stokowski_adapter.py')).length>65536);
  assert.equal((await action(f)).status,'published');
  assert.equal(readFileSync(f.marker,'utf8'),'x');
});

test('source blob above separate bounded limit refuses before identity or effects',async t=>{
  const f=await fixture(t,'oversized-source');
  const {prepareOwnerPublication}=await import(pathToFileURL(join(f.root,'tools/delivery/integration-gateway.mjs')));
  let calls=0;
  await assert.rejects(prepareOwnerPublication({github:{getProfile:async()=>{calls++;return {id:123,login:'synthetic'};}},reviewedPublication:f.context}),{code:'ERR_CHILD_PROCESS_STDIO_MAXBUFFER'});
  assert.equal(calls,0);
  noProbe(f);
});

test('lost reply reconciles retained result read-only, no second prepare/provider call',async t=>{
  const f=await fixture(t,'lost-reply');
  assert.equal((await action(f)).status,'published');
  assert.equal(readFileSync(f.marker,'utf8'),'x');
});

for(const mode of ['refused','uncertain'])test(`API ${mode} is retained and never retried`,async t=>{
  const f=await fixture(t,mode);
  assert.equal((await action(f)).status,mode);
  assert.deepEqual(readFileSync(f.catalog),f.catalogBefore);
  await assert.rejects(action(f));
  assert.equal(readFileSync(f.marker,'utf8'),'x');
});

test('fresh gateway identity mismatch refuses before provider or catalog effects',async t=>{
  const f=await fixture(t);
  await assert.rejects(action(f,{id:999,login:'forged'}));
  noProbe(f);
});

for (const kind of ['stale','future','principal','provenance','nonce','request-hash','config','handoff','source','claim']) {
  test(`stdin refuses ${kind} before any publication`,async t=>{
    const f=await fixture(t),e=envelope(f);
    if(kind==='stale')e.observed_at-=31;
    if(kind==='future')e.observed_at+=5;
    if(kind==='principal')e.principal.principal_id='999';
    if(kind==='provenance')e.provenance.connector_tool='saved-report';
    if(kind==='nonce')e.nonce='bad';
    if(kind==='config')e.context.owner_config.sha256='0'.repeat(64);
    if(kind==='handoff')e.context.handoff.sha256='0'.repeat(64);
    if(kind==='source')writeFileSync(join(f.root,'tools/delivery/stokowski_prepare.py'),'drift');
    if(kind==='claim') {
      const config=JSON.parse(readFileSync(f.context.owner_config.path));
      writeFileSync(config.repository_claim.path,'{}');
    }
    assert.notEqual((await stdin(f,e,'prepare',kind==='request-hash'?'0'.repeat(64):undefined)).code,0);
    noProbe(f);
  });
}

test('unresolved intent permits exact read-only status and refuses replay/new nonce',async t=>{
  const f=await fixture(t),e=envelope(f),payload=JSON.stringify(e);
  writeFileSync(f.journal,JSON.stringify({version:1,status:'intent',nonce:e.nonce,request_sha256:sha(payload),context:f.context}));
  assert.equal((await stdin(f,e,'status')).result.status,'uncertain');
  assert.notEqual((await stdin(f,e)).code,0);
  assert.notEqual((await stdin(f,{...e,nonce:'a'.repeat(64)})).code,0);
  noProbe(f);
});

test('exact replay is refused; retained response is hash-bound',async t=>{
  const f=await fixture(t),e=envelope(f);
  assert.equal((await stdin(f,e)).result.status,'published');
  assert.notEqual((await stdin(f,e)).code,0);
  assert.equal((await stdin(f,e,'status')).result.status,'published');
  assert.equal(readFileSync(f.marker,'utf8'),'x');
});

for (const mode of ['response-hash','response-binding']) {
  test(`gateway refuses forged ${mode} even after a real synthetic publication`,async t=>{
    const f=await fixture(t,mode);
    await assert.rejects(action(f));
    assert.equal(readFileSync(f.marker,'utf8'),'x');
    assert.equal(JSON.parse(readFileSync(f.journal)).status,'published');
  });
}

test('post-review integration decision remains independently consumed',async()=>{
  const {advanceIntegration}=await import('../../tools/delivery/integration-gateway.mjs');
  const decision={status:'waiting',action:null};
  let observations=0;
  assert.equal(await advanceIntegration({controller:{step:async()=>decision},
    observe:async()=>{observations++;return {};},github:{},linear:{}}),decision);
  assert.equal(observations,1);
});

test('missing imported-source pin stops before observing identity or spawning consumer',async t=>{
  const f=await fixture(t);
  delete f.context.source_sha256['tools/delivery/symphony_launch.py'];
  const {prepareOwnerPublication}=await import(pathToFileURL(join(f.root,'tools/delivery/integration-gateway.mjs')));
  let calls=0;
  await assert.rejects(prepareOwnerPublication({reviewedPublication:f.context,
    github:{getProfile:async()=>{calls++;throw Error('must not observe');}}}));
  assert.equal(calls,0);
  noProbe(f);
});


test('source separation: develop gateway publishes exact independent feature task through stdin/API',async t=>{
  const f=await fixture(t,'source-separation');
  assert.equal(f.context.source_branch,'develop');
  assert.notEqual(f.task_source.source_checkout,f.root);
  assert.notEqual(f.task_source.base,f.context.source_head);
  assert.match(f.task_source.branch,/^feature\//);
  assert.equal((await action(f)).status,'published');
  const admission=JSON.parse(readFileSync(join(f.runtime,'current-admission.json')));
  const manifest=JSON.parse(readFileSync(join(f.runtime,'manifest.json')));
  assert.equal(admission.source,f.task_source.source_checkout);
  assert.equal(manifest.base_revision,f.task_source.base);
  assert.equal(manifest.branch,f.task_source.branch);
  assert.equal(readFileSync(f.marker,'utf8'),'x');
  assert.equal(JSON.parse(readFileSync(f.catalog)).entries.length,1);
  assert.equal(JSON.parse(readFileSync(f.journal)).status,'published');
  await assert.rejects(action(f));
  assert.equal(readFileSync(f.marker,'utf8'),'x');
});

for(const kind of ['checkout','head','branch','manifest']) {
  test(`source separation: accepted API refuses mismatched task ${kind} before publication`,async t=>{
    const f=await fixture(t,`source-separation-${kind}`);
    assert.equal((await action(f)).status,'refused');
    assert.equal(JSON.parse(readFileSync(f.journal)).status,'refused');
    noProbe(f);
    assert.throws(()=>readFileSync(join(f.runtime,'current-admission.json')),{code:'ENOENT'});
  });
}


test('successor: actual caller publishes once, restart reconciles and normal poller selects',async t=>{
  const f=await fixture(t,'successor');
  const before=readFileSync(join(f.original_runtime,'manifest.json'));
  const stateBefore=readFileSync(join(f.coordinator,'current-owner.json'));
  assert.equal((await action(f)).status,'published');
  assert.equal(readFileSync(join(f.coordinator,'current-owner.json')).equals(stateBefore),true);
  assert.equal(JSON.parse(readFileSync(f.catalog)).entries.length,2);
  assert.equal(readFileSync(f.marker,'utf8'),'x');
  const {prepareOwnerPublication}=await import(pathToFileURL(join(f.root,'tools/delivery/integration-gateway.mjs')));
  for(let i=0;i<2;i++) {
    const result=await prepareOwnerPublication({github:{getProfile:async()=>{throw Error('status only');}},reviewedPublication:f.context});
    assert.equal(result.status,'published');
  }
  const script=String.raw`
import asyncio,json,pathlib,sys
sys.path.insert(0,str(pathlib.Path(sys.argv[1])/'tools/delivery'))
from stokowski_adapter import CurrentWork,install_adapters,SLUG
from stokowski.models import Issue
from stokowski.linear import LinearClient
from unittest.mock import AsyncMock,patch
c=CurrentWork(pathlib.Path(sys.argv[2]))
assert c.state['successor_request']['status']=='published',c.state
identity=c.state['successor_request']['identity']
for _ in range(2):
    c=CurrentWork(pathlib.Path(sys.argv[2]))
    assert c.state['successor_request']['identity']==identity
issue=Issue(id='00000000-0000-4000-8000-000000000231',identifier='UIF-231',title='Synthetic',state='Todo')
async def select():
    with patch.object(LinearClient,'fetch_candidate_issues',new=AsyncMock(return_value=[issue])), patch.object(LinearClient,'_graphql',new=AsyncMock(return_value={'issue':{'id':issue.id,'identifier':issue.identifier,'project':{'id':'ce60c1ab-a732-4a71-8471-14c9dc393886'},'state':{'name':'Todo'}}})):
        install_adapters(c.runtime,{'tasks':{}},'fixture-only',c)
        client=LinearClient('https://api.linear.app/graphql','fixture-only')
        selected=await client.fetch_candidate_issues(SLUG,['Todo'])
        assert [i.identifier for i in selected]==['UIF-231'],c.state
asyncio.run(select())
print('successor selected once; no action or provider replay')
`;
  const result=await promisify(execFile)(python,['-B','-c',script,f.root,f.coordinator],{
    timeout:10000,env:{PATH:'/usr/bin:/bin',LANG:'C.UTF-8',PYTHONPATH:`${f.root}/src`}});
  assert.match(result.stdout,/successor selected once/);
  assert.equal(readFileSync(f.marker,'utf8'),'x');
  assert.equal(readFileSync(join(f.original_runtime,'manifest.json')).equals(before),true);
  assert.equal(JSON.parse(readFileSync(f.catalog)).entries.length,2);
});


test('successor: uncertain publication is status-only across caller restart',async t=>{
  const f=await fixture(t,'successor-uncertain');
  assert.equal((await action(f)).status,'uncertain');
  const {prepareOwnerPublication}=await import(pathToFileURL(join(f.root,'tools/delivery/integration-gateway.mjs')));
  assert.equal((await prepareOwnerPublication({reviewedPublication:f.context,
    github:{getProfile:async()=>{throw Error('no second identity/action');}}})).status,'uncertain');
  assert.equal(readFileSync(f.marker,'utf8'),'x');
  assert.equal(JSON.parse(readFileSync(f.catalog)).entries.length,1);
});

for(const drift of ['stale','owner','config','handoff','trigger','resources','source','unqualified']) {
  test(`successor: ${drift} is held before authentication or provider`,async t=>{
    const f=await fixture(t,'successor');
    const statePath=join(f.coordinator,'current-owner.json');
    const state=JSON.parse(readFileSync(statePath));
    const now=Date.now;
    if(drift==='stale') Date.now=()=>now()+700000;
    t.after(()=>{Date.now=now;});
    if(drift==='owner') state.owner='foreign-owner';
    writeFileSync(statePath,JSON.stringify(state));
    if(drift==='config') writeFileSync(f.context.owner_config.path,readFileSync(f.context.owner_config.path)+' ');
    if(drift==='handoff') writeFileSync(f.context.handoff.path,readFileSync(f.context.handoff.path)+' ');
    if(drift==='source') {
      const path=join(f.root,'tools/delivery/stokowski_adapter.py');
      writeFileSync(path,readFileSync(path)+'\n# synthetic source drift\n');
    }
    if(drift==='trigger' || drift==='resources') {
      const handoff=JSON.parse(readFileSync(f.context.handoff.path));
      const packet=JSON.parse(readFileSync(handoff.task_packet.path));
      if(drift==='trigger') packet.trigger.review_sha256='0'.repeat(64);
      else packet.resources.cpu_millis++;
      writeFileSync(handoff.task_packet.path,JSON.stringify(packet));
    }
    if(drift==='unqualified') {
      const path=join(f.coordinator,'current.json');
      const config=JSON.parse(readFileSync(path));
      delete config.qualified_successor;
      writeFileSync(path,JSON.stringify(config));
    }
    const {prepareOwnerPublication}=await import(pathToFileURL(join(f.root,'tools/delivery/integration-gateway.mjs')));
    await assert.rejects(prepareOwnerPublication({reviewedPublication:f.context,
      github:{getProfile:async()=>{throw Error('must not authenticate');}}}));
    assert.throws(()=>readFileSync(f.marker),{code:'ENOENT'});
    assert.equal(JSON.parse(readFileSync(f.catalog)).entries.length,1);
  });
}


test('successor: actual caller rechecks current cancelled trigger before exposure',async t=>{
  const f=await fixture(t,'successor-cancelled');
  assert.equal((await action(f)).status,'refused');
  assert.equal(JSON.parse(readFileSync(f.catalog)).entries.length,1);
  assert.throws(()=>readFileSync(f.marker),{code:'ENOENT'});
});


test('successor: actual caller refuses drifted exact request before provider',async t=>{
  const f=await fixture(t,'successor');
  const handoff=JSON.parse(readFileSync(f.context.handoff.path));
  writeFileSync(handoff.request.path,readFileSync(handoff.request.path)+' ');
  assert.equal((await action(f)).status,'refused');
  assert.throws(()=>readFileSync(f.marker),{code:'ENOENT'});
  assert.equal(JSON.parse(readFileSync(f.catalog)).entries.length,1);
});
