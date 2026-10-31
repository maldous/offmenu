/** Fixed, finite publisher SOURCE. Installation/host isolation remain adoption holds.
 * Legacy invocation: no arguments/stdin. Native mode accepts one fixed flag
 * and a bounded sealed-identity request, never callbacks, commands or key paths.
 * Root owner supplies protected config + admitted plan/evidence and installs this
 * exact source under /opt/offmenu-publisher. No daemon, setup or scheduling here.
 * Host sudo ALL/NOPASSWD means UID/key custody alone is NOT full isolation.
 */
import * as fs from 'node:fs';
import {createHash} from 'node:crypto';
import {execFile} from 'node:child_process';
import {promisify,isDeepStrictEqual} from 'node:util';
import {fileURLToPath} from 'node:url';
import {dirname,join} from 'node:path';
import {reviewWireBytes} from './integration-gateway.mjs';

const INSTALL='/opt/offmenu-publisher';
const CONFIG='/etc/offmenu-publisher/config.json';
const KEY='/etc/offmenu-publisher/github-app-private-key.pem';
const CLAIM='/var/lib/offmenu-publisher/integration';
const LIMIT=1024*1024;
const ROOT='/repos/maldous/offmenu';
const fail=()=>{throw Error('publisher-held');};
const check=x=>{if(!x) fail();};
const hex=(s,n=64)=>typeof s==='string' && new RegExp(`^[0-9a-f]{${n}}$`).test(s);
const positive=n=>Number.isSafeInteger(n)&&n>0;
const same=isDeepStrictEqual;
const hash=b=>createHash('sha256').update(b).digest('hex');
const objectHash=(type,b)=>createHash('sha1').update(`${type} ${b.length}\0`).update(b).digest('hex');
const exact=(o,keys)=>o && Object.getPrototypeOf(o)===Object.prototype &&
  same(Object.keys(o).sort(),[...keys].sort());
const bytesJSON=o=>{const b=Buffer.from(JSON.stringify(o));check(b.length<=LIMIT);return b;};
// Match Python Controller fingerprint for the restricted JSON wire used here.
export function fingerprint(o) {
  function ordered(v) {
    if(Array.isArray(v)) return v.map(ordered);
    if(v && typeof v==='object') return Object.fromEntries(Object.keys(v).sort().map(k=>[k,ordered(v[k])]));
    check(v===null || typeof v==='string' || typeof v==='boolean' || Number.isSafeInteger(v));
    return v;
  }
  // Python's canonical serializer escapes non-ASCII, including UTF-16 pairs.
  return hash(JSON.stringify(ordered(o)).replace(/[\u007f-\uffff]/g,c=>'\\u'+c.charCodeAt(0).toString(16).padStart(4,'0')));
}

/** Synthetic filesystem/identity injection is an in-process test boundary only.
 * Open descriptor metadata is compared with lstat to close final-component races.
 * All ancestor directories must be canonical and root-owned, except publisher
 * state directories explicitly checked separately. No key path comes from JSON.
 */
export function protectedRead(path,{uid=0,gid,mode=0o440,max=LIMIT,io=fs}={}) {
  check(typeof path==='string' && path.startsWith('/') && !path.includes('/../') &&
    io.realpathSync(path)===path);
  for(let parent=dirname(path);;parent=dirname(parent)) {
    const s=io.lstatSync(parent);
    check(s.isDirectory() && s.uid===0 && (s.mode&0o022)===0);
    if(parent==='/') break;
  }
  const before=io.lstatSync(path);
  check(before.isFile() && before.nlink===1 && before.uid===uid &&
    (gid===undefined || before.gid===gid) && (before.mode&0o7777)===mode && before.size>0 && before.size<=max);
  const fd=io.openSync(path,fs.constants.O_RDONLY|fs.constants.O_NOFOLLOW|fs.constants.O_NONBLOCK);
  try {
    const after=io.fstatSync(fd);
    check(after.isFile() && after.nlink===1 && after.ino===before.ino && after.dev===before.dev &&
      after.uid===before.uid && after.gid===before.gid && after.mode===before.mode && after.size===before.size);
    const b=io.readFileSync(fd);check(b.length===after.size && b.length<=max);return b;
  } finally {io.closeSync(fd);}
}
export function validateConfig(c, identity) {
  check(exact(c,['version','appId','installationId','repositoryId','publisherUid','publisherGid',
    'logicalOwner','sourceHead','codePins','pythonSha256','binding','snapshot','plan','workspace']));
  check([1,2].includes(c.version) && [c.appId,c.installationId,c.publisherUid,c.publisherGid].every(positive) &&
    ![0,1000].includes(c.publisherUid) && ![0,1000].includes(c.publisherGid) &&
    c.repositoryId===1416253963 && identity.uid===c.publisherUid && identity.euid===c.publisherUid &&
    identity.gid===c.publisherGid && identity.egid===c.publisherGid &&
    typeof c.logicalOwner==='string' && c.logicalOwner.length>0 &&
    c.binding.owner===c.logicalOwner && c.binding.repository==='maldous/offmenu' &&
    hex(c.sourceHead,40) && hex(c.pythonSha256) &&
    (c.version===2 ? c.binding.version===3 && c.binding.kind==='release-promotion-v1' &&
      same(c.plan,{kind:'release-promotion-v1'}) &&
      c.snapshot.qualification_sha256===fingerprint(c.binding.qualification) :
      c.binding.version===2 && c.binding.pr_number===null &&
      c.binding.publication.plan_sha256===fingerprint(c.plan) &&
      c.binding.publication.qualification_sha256===fingerprint(c.snapshot)));
  const required=['tools/delivery/github-app-publisher.mjs','tools/delivery/github-app-adapter.mjs',
    'tools/delivery/integration-gateway.mjs','src/offmenu/delivery/integration.py',
    'src/offmenu/delivery/engine.py','src/offmenu/__init__.py','src/offmenu/delivery/__init__.py'];
  if(c.version===2) required.push('tools/delivery/native_harness_contract.py','contracts/schemas/delivery-handoff-v1.schema.json','tools/delivery/release_qualification.py');
  check(c.codePins && required.every(p=>hex(c.codePins[p])) &&
    Object.entries(c.codePins).every(([p,h])=>required.includes(p)&&hex(h)) &&
    typeof c.workspace==='string' && c.workspace.startsWith('/') && !c.workspace.includes('/../') &&
    (c.version===2 || /^(feature|bugfix)\/[a-z0-9][a-z0-9/-]{0,159}$/.test(c.binding.head_branch) &&
    !c.binding.head_branch.includes('//') && !c.binding.head_branch.endsWith('/')));
  bytesJSON(c);
  return c;
}
export function loadProtectedConfig({io=fs,identity={uid:process.getuid(),euid:process.geteuid(),
  gid:process.getgid(),egid:process.getegid()}}={}) {
  check(![0,1000].includes(identity.uid) && identity.uid===identity.euid);
  const c=validateConfig(JSON.parse(protectedRead(CONFIG,{io}).toString('utf8')),identity);
  const d=io.lstatSync('/etc/offmenu-publisher');
  check(d.isDirectory() && d.uid===0 && d.gid===c.publisherGid && (d.mode&0o7777)===0o750);
  const s=io.lstatSync(CONFIG);check(s.gid===c.publisherGid);
  return c;
}
export function loadProtectedKey(c,{io=fs}={}) {
  // Fixed path only. Tests never call the real filesystem at this path.
  const d=io.lstatSync('/etc/offmenu-publisher');
  check(d.isDirectory() && d.uid===0 && d.gid===c.publisherGid && (d.mode&0o7777)===0o750);
  return protectedRead(KEY,{gid:c.publisherGid,io,max:65536});
}

function pathOK(path) {
  return typeof path==='string' && path.length<=512 && /^[a-zA-Z0-9_.@+/-]+$/.test(path) &&
    !path.startsWith('/') && !path.split('/').some(p=>!p || p==='.' || p==='..' || p==='.git') &&
    !path.startsWith('.github/workflows/');
}
function parseTree(raw) {
  const entries=[];
  for(let i=0;i<raw.length;) {
    const space=raw.indexOf(32,i), nul=raw.indexOf(0,space+1);
    check(space>i && nul>space && nul+21<=raw.length);
    const mode=raw.subarray(i,space).toString(), nameBytes=raw.subarray(space+1,nul);
    const name=nameBytes.toString('utf8');
    check(Buffer.from(name).equals(nameBytes) && pathOK(name) && !name.includes('/') &&
      ['100644','100755','40000'].includes(mode));
    entries.push({path:name,mode:mode==='40000'?'040000':mode,type:mode==='40000'?'tree':'blob',
      sha:raw.subarray(nul+1,nul+21).toString('hex')});i=nul+21;
  }
  check(new Set(entries.map(e=>e.path)).size===entries.length);
  return entries;
}
function parseCommit(raw) {
  const text=raw.toString('utf8');check(Buffer.from(text).equals(raw));
  const split=text.indexOf('\n\n');check(split>0);
  const headers=text.slice(0,split).split('\n');
  check(headers.length===4 && /^tree [0-9a-f]{40}$/.test(headers[0]) &&
    /^parent [0-9a-f]{40}$/.test(headers[1])); // signed/merge/encoding/extension headers held
  function identity(line,role) {
    const m=new RegExp(`^${role} ([^<>\\n]+) <([^<>\\s]+)> ([0-9]+) ([+-])([0-9]{2})([0-9]{2})$`).exec(line);
    check(m);const epoch=Number(m[3]), minutes=Number(m[5])*60+Number(m[6]);
    check(Number.isSafeInteger(epoch) && minutes<=14*60 && Number(m[6])<60);
    const date=new Date((epoch+(m[4]==='+'?1:-1)*minutes*60)*1000).toISOString().slice(0,19)+m[4]+m[5]+':'+m[6];
    return {name:m[1],email:m[2],date};
  }
  const message=text.slice(split+2);check(message && message.endsWith('\n'));
  return {message,tree:headers[0].slice(5),parents:[headers[1].slice(7)],
    author:identity(headers[2],'author'),committer:identity(headers[3],'committer')};
}
const objectOperation=(kind,expected,body)=>({kind,method:'POST',path:`${ROOT}/git/${{blob:'blobs',tree:'trees',commit:'commits'}[kind]}`,
  body,readPath:`${ROOT}/git/${{blob:'blobs',tree:'trees',commit:'commits'}[kind]}/${expected}`,expected});

/** Read only Git object qualification; never executes candidate code/hooks/filter.
 * Inject readObject/readChangedFile only in trusted tests. Production uses fixed
 * cat-file types+SHAs, no arbitrary revision, command, executable or shell.
 */
export async function qualifyCandidate(c,{readObject,readChangedFile,branchHead}) {
  const b=c.binding;
  check(branchHead===b.head && exact(c.plan,['operations','changedFiles']) &&
    Array.isArray(c.plan.operations) && c.plan.operations.length<=128);
  const object=async(type,id)=>{
    check(['commit','tree','blob'].includes(type)&&hex(id,40));
    const raw=await readObject(type,id);check(Buffer.isBuffer(raw)&&raw.length<=LIMIT&&objectHash(type,raw)===id);return raw;
  };
  const commit=parseCommit(await object('commit',b.head));
  check(commit.tree===b.tree && same(commit.parents,[b.base]));
  // Base headers can be signed/merge commits; only its immutable tree is needed.
  const baseRaw=await object('commit',b.base);
  const baseTree=/^tree ([0-9a-f]{40})\n/.exec(baseRaw.toString('utf8'))?.[1];check(baseTree);
  const operations=[],changedFiles={},seen=new Set();
  const add=operation=>{if(!seen.has(operation.expected)){seen.add(operation.expected);operations.push(operation);}};
  async function trees(head,base,prefix='',depth=0) {
    check(depth<32);if(head===base) return;
    const entries=parseTree(await object('tree',head));
    const previous=base ? parseTree(await object('tree',base)) : [];
    const old=new Map(previous.map(e=>[e.path,e]));
    // Deletions and mode/type changes have no regular changed-file bytes: hold.
    check(previous.every(e=>entries.some(n=>n.path===e.path && n.mode===e.mode && n.type===e.type)));
    for(const entry of entries) {
      const prior=old.get(entry.path);if(prior?.sha===entry.sha) continue;
      const path=prefix+entry.path;check(pathOK(path));
      if(entry.type==='tree') await trees(entry.sha,prior?.sha,path+'/',depth+1);
      else {
        const raw=await object('blob',entry.sha),local=await readChangedFile(path);
        check(Buffer.isBuffer(local) && local.equals(raw));changedFiles[path]=hash(raw);
        add(objectOperation('blob',entry.sha,{content:raw.toString('base64'),encoding:'base64'}));
      }
    }
    add(objectOperation('tree',head,{tree:entries}));
  }
  await trees(commit.tree,baseTree);
  check(Object.keys(changedFiles).length>0 && same(changedFiles,c.plan.changedFiles) &&
    Object.entries(b.outputs).every(([p,h])=>changedFiles[p]===h));
  operations.push(objectOperation('commit',b.head,commit));
  const tail=c.plan.operations.slice(operations.length);
  check(tail.length>=2 && tail.length<=3 && tail[0].kind==='ref' && tail[1].kind==='create-pr' &&
    (tail.length===2 || (tail[2].kind==='update-pr' &&
      tail[2].path===`${ROOT}/pulls/{canonical}` && tail[2].readPath===tail[2].path)));
  // Full exact operation validation also runs in the API adapter before the key.
  check(same(operations,c.plan.operations.slice(0,operations.length)) &&
    c.binding.publication.plan_sha256===fingerprint(c.plan));
  bytesJSON(c.plan);
  return c.plan;
}

function canonicalObject(operation,result) {
  if(!result || result.sha!==operation.expected) return false;
  if(operation.kind==='blob') {
    if(result.encoding!=='base64' || typeof result.content!=='string') return false;
    const raw=Buffer.from(result.content.replace(/\n/g,''),'base64');
    return objectHash('blob',raw)===operation.expected && raw.toString('base64')===operation.body.content;
  }
  if(operation.kind==='tree') {
    if(result.truncated!==false || !Array.isArray(result.tree)) return false;
    return same(result.tree.map(e=>({path:e.path,mode:e.mode,type:e.type,sha:e.sha})),operation.body.tree);
  }
  // Verify exact author/committer identity and raw-object SHA returned by GitHub.
  return result.tree?.sha===operation.body.tree &&
    same(result.parents?.map(p=>p.sha),operation.body.parents) && typeof result.message==='string' &&
    result.message.replace(/\n?$/, '\n')===operation.body.message.replace(/\n?$/, '\n') &&
    ['author','committer'].every(role=>result[role]?.name===operation.body[role].name &&
      result[role]?.email===operation.body[role].email &&
      Date.parse(result[role]?.date)===Date.parse(operation.body[role].date));
}
export function canonicalPublication(operation,result,binding,number) {
  if(['blob','tree','commit'].includes(operation.kind)) return canonicalObject(operation,result);
  if(operation.kind==='ref') return result?.ref===`refs/heads/${binding.head_branch}` &&
    result.object?.type==='commit' && result.object.sha===binding.head;
  const list=operation.kind==='create-pr'?result:[result];
  if(!Array.isArray(list)||list.length!==1) return false;
  const p=list[0];
  return positive(p?.number) && (number===null || number===undefined || p.number===number) &&
    p.base?.repo?.id===1416253963 && p.base.repo.full_name==='maldous/offmenu' &&
    p.head?.repo?.id===1416253963 && p.head.repo.full_name==='maldous/offmenu' &&
    p.base.ref==='develop' && p.base.sha===binding.base && p.head.ref===binding.head_branch &&
    p.head.sha===binding.head && p.title===operation.body.title && p.body===operation.body.body &&
    p.state==='open' && p.draft===false && p.merged_at===null;
}

/** Execute at most one typed mutation per invocation. Unknown effects are GET
 * only on every restart. Root can invoke again after canonical verification.
 * `controller` is the fixed Python bridge in normal use, never a JSON callback.
 */
export async function publicationStep({config:c,controller,adapterFactory,qualify,readOnly=false}) {
  await qualify();
  let state=await controller(readOnly?'observe':'prepare');
  const pub=state.publication;check(pub && pub.next<c.plan.operations.length);
  if(readOnly && pub.effect==='ready') return {status:state.status};
  let operation=structuredClone(c.plan.operations[pub.next]); const index=pub.next;
  if(operation.kind==='update-pr') {
    check(positive(pub.pr_number) && operation.path===`${ROOT}/pulls/{canonical}` &&
      operation.readPath===operation.path);
    operation.path=operation.readPath=`${ROOT}/pulls/${pub.pr_number}`;
  }
  check(operation.kind!=='update-pr' || positive(pub.pr_number));
  // The admitted metadata template acquires its exact URL only from the frozen PR.
  const adapter=await adapterFactory({operation,index,number:pub.pr_number});
  let result=await adapter.readPublication(0);
  if(canonicalPublication(operation,result,c.binding,pub.pr_number)) {
    if(pub.effect==='ready') state=await controller('intent',{index,action:operation});
  } else {
    if(readOnly || pub.effect!=='ready') return {status:'publication-reconciliation-required'};
    // Immutable objects and create-ref/PR can proceed only on authoritative
    // absence. Ref updates require exactly the admitted old commit; no force.
    if(operation.kind==='ref' && operation.expected!==null) {
      check(result?.ref===`refs/heads/${c.binding.head_branch}` && result.object?.type==='commit' &&
        result.object.sha===operation.expected);
    } else if(operation.kind==='create-pr') check(Array.isArray(result)&&result.length===0);
    else if(operation.kind==='update-pr') {
      check(result?.number===pub.pr_number && result.head?.sha===c.binding.head &&
        result.base?.sha===c.binding.base && result.base?.ref==='develop' &&
        result.head?.ref===c.binding.head_branch && result.head?.repo?.id===1416253963 &&
        result.base?.repo?.id===1416253963 && result.state==='open' && result.draft===false);
    } else check(result===null);
    state=await controller('intent',{index,action:operation});
    // Durable consume happens in adapter authorizeIntent immediately before HTTP.
    await adapter.mutatePublication(0);
    result=await adapter.readPublication(0);
    if(!canonicalPublication(operation,result,c.binding,pub.pr_number))
      return {status:'publication-reconciliation-required'};
  }
  if(operation.kind==='create-pr') await controller('freeze-pr',{index,action:operation,number:result[0].number});
  state=await controller('reconcile',{index,action:operation,canonical:fingerprint(operation),
    final:index===c.plan.operations.length-1});
  return {status:state.status};
}

/** Post-publication uses the existing gateway and original Controller merge flow.
 * The tracker writer remains separate; this helper never supplies Linear auth.
 * Root-admitted exact review facts must still match fresh canonical API facts.
 */
export async function integrationStep({config:c,controller,adapterFactory,advanceIntegration,readOnly=false}) {
  const state=await controller(readOnly?'observe':'status');
  const number=state.publication?.pr_number;
  check(state.publication?.effect==='verified' && positive(number));
  const b=c.binding;
  const action={kind:'merge-pr',repository:b.repository,pr_number:number,
    expected_head_sha:b.head,expected_head_branch:b.head_branch,expected_base_sha:b.base,
    merge_method:'merge',bypass_protection:false,
    operation_key:fingerprint({binding:fingerprint(b),action:'merge'})};
  const github=await adapterFactory({
    config:{appId:c.appId,installationId:c.installationId,repositoryId:c.repositoryId,publisherUid:c.publisherUid},
    binding:{repository:b.repository,prNumber:number,headSha:b.head,baseSha:b.base,
      headBranch:b.head_branch,intentSha256:fingerprint(action)},
    authorizeIntent:async intent=>(await controller('consume',{intent})).authorized===true});
  async function observe() {
    const p=await github.getPullRequest(b.repository,number);
    const snapshot={...structuredClone(c.snapshot),observed_at:Date.now()/1000,
      github:{repository:b.repository,number,merged:p.merged,state:p.merged?'closed':'open',
        head:p.head_sha,base:p.base_sha,head_branch:p.head,base_branch:p.base,
        draft:p.draft,mergeable:p.mergeable}};
    // No whole-issue completion is synthesized by this GitHub-only helper.
    delete snapshot.linear;delete snapshot.full_issue_acceptance;
    if(p.merged) {
      check(hex(p.merge_commit_sha,40));
      const facts=await github.readCanonicalFacts(p.merge_commit_sha);
      snapshot.github.merge_commit_sha=p.merge_commit_sha;
      snapshot.merge_commit=facts.merge_commit;
      snapshot.develop_contains_merge=facts.develop_contains_merge;
    } else {
      const facts=await github.readExactHeadReviewFacts();
      check(hex(c.snapshot.github_review_facts_sha256) &&
        fingerprint(facts)===c.snapshot.github_review_facts_sha256);
    }
    return snapshot;
  }
  if(readOnly) return await controller('step',{observation:await observe()});
  const result=await advanceIntegration({
    controller:{step:observation=>controller('step',{observation}),
      outcome:(kind,outcome)=>controller('outcome',{kind,outcome})},github,observe,
    linear:{completeIssue:async()=>fail()}});
  return {status:result.status};
}

/** Existing fixed credential invocation, separately admitted frozen release. */
export async function releaseStep({config:c,controller,adapterFactory,advanceRelease,readOnly=false}) {
  check(c.version===2 && c.binding.version===3);
  const b=c.binding,s=b.candidate.source;
  // Python constructor validates candidate/policy and immutable authority before auth.
  await controller(readOnly?'observe':'status');
  const github=await adapterFactory({
    config:{appId:c.appId,installationId:c.installationId,repositoryId:c.repositoryId,publisherUid:c.publisherUid},
    binding:{repository:b.repository,prNumber:b.pr_number,headSha:s.head,baseSha:b.main_base,
      headBranch:`release/candidate-${fingerprint(b.candidate)}`,intentSha256:fingerprint(b.authority)},
    release:{candidateSha256:fingerprint(b.candidate),authoritySha256:fingerprint(b.authority),tag:b.tag},
    authorizeIntent:async intent=>(await controller('consume',{intent})).authorized===true});
  async function observe() {
    const p=await github.getPullRequest(b.repository,b.pr_number);
    const observation={...structuredClone(c.snapshot),observed_at:Date.now()/1000,
      github:{repository:b.repository,number:b.pr_number,merged:p.merged,state:p.merged?'closed':'open',
        head:p.head_sha,base:p.base_sha,head_branch:p.head,base_branch:p.base,
        draft:p.draft,mergeable:p.mergeable},tag:await github.readReleaseTag()};
    if(p.merged) {
      const facts=await github.readCanonicalFacts(p.merge_commit_sha);
      observation.github.merge_commit_sha=p.merge_commit_sha;
      observation.merge_commit=facts.merge_commit;
      observation.main_contains_merge=facts.main_contains_merge;
    } else {
      const facts=await github.readExactHeadReviewFacts();
      check(hex(c.snapshot.github_review_facts_sha256) &&
        fingerprint(facts)===c.snapshot.github_review_facts_sha256);
    }
    return observation;
  }
  if(readOnly) return await controller('step',{observation:await observe()});
  return await advanceRelease({controller:{step:observation=>controller('step',{observation})},github,observe});
}

const nativeKeys=['version','mode','operation_id','issue_id','project_id','owner',
  'unit_sha256','packet_sha256','source_sha256'];
export function parseNativeRequest(raw) {
  check(typeof raw==='string' && Buffer.byteLength(raw)<=16384);
  // Requests are flat JSON scalars. Decode every lexical key before checking
  // duplicates, including escaped spellings; no last-key-wins authority.
  const keys=[...raw.matchAll(/("(?:[^"\\]|\\.)*")\s*:/g)].map(m=>JSON.parse(m[1]));
  check(keys.length===nativeKeys.length && new Set(keys).size===keys.length);
  const request=JSON.parse(raw);reviewWireBytes(request);
  check(exact(request,nativeKeys) && request.version===1 && ['observe','step'].includes(request.mode));
  return request;
}
export function qualifyNativeRequest(c,request) {
  reviewWireBytes(request);check(exact(request,nativeKeys) && request.version===1 &&
    ['observe','step'].includes(request.mode));
  const n=c.snapshot.native_runtime,b=c.binding,s=n?.source;
  check(exact(n,['issue_id','project_id','owner','unit_sha256','packet_sha256','source']) &&
    hex(n.unit_sha256) && hex(n.packet_sha256) &&
    n.owner===c.logicalOwner && n.owner===b.owner && n.issue_id===b.issue_id &&
    (!b.project_id || n.project_id===b.project_id) &&
    [n.issue_id,n.project_id].every(v=>typeof v==='string' &&
      /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/.test(v)) &&
    s && s.repository===b.repository &&
    (c.version===2 ? same(s,b.candidate.source) && s.branch==='develop' && s.target==='main' :
      s.branch===b.head_branch && s.base===b.base && s.head===b.head && s.tree===b.tree && s.target==='develop'));
  const identity={operation_id:fingerprint(b),issue_id:n.issue_id,project_id:n.project_id,owner:n.owner,
    unit_sha256:n.unit_sha256,packet_sha256:n.packet_sha256,source_sha256:fingerprint(s)};
  check(Object.entries(identity).every(([key,value])=>request[key]===value));
  return {...identity,phase:c.version===2?'release':'integration'};
}
export function nativeJournalStatus(view,release=false) {
  check(exact(view,['state','claim_current','claim_available']) &&
    typeof view.claim_current==='boolean' && typeof view.claim_available==='boolean');
  const s=view.state;check(s && typeof s.status==='string');
  if(!view.claim_available || ['authority-refused','quarantined','disabled','cancelled','stale-candidate'].includes(s.status)) return 'denied';
  if(['repair-required','metadata-repair-required','release-readback-mismatch','immutable-tag-conflict'].includes(s.status)) return 'failed';
  if(release) {
    if(s.status==='release-verified' && s.release_effect==='verified' && s.tag_effect==='verified') return 'verified';
    if(s.tag_effect==='unknown' || s.release_effect==='unknown') return 'unknown';
    if(s.tag_effect==='pending') return s.action?.kind==='create-release-tag' &&
      same(s.action,s.tag_intent)?'ready':'pending';
    if(s.release_effect==='pending') return 'pending';
  } else {
    if(s.status==='merge-verified' && s.merge_effect==='verified') return 'verified';
    if(s.merge_effect==='unknown' || s.publication?.effect==='unknown') return 'unknown';
    if(s.merge_effect==='pending') return s.helper_consumed?'unknown':'pending';
    if(s.publication?.effect==='pending') return 'pending';
  }
  return ['prepared','publication-ready','publication-verified','release-tag-intent'].includes(s.status)?'ready':'pending';
}

/** Fixed installed entry, no packet-selected executable/config/key/callback.
 * Trusted injection below is only for in-process synthetic tests. Normal main
 * supplies the fixed Python bridge, Git reader and repository App adapter.
 */
export async function nativePublisherRequest({config:c,request,controller,adapterFactory,qualify}) {
  const identity=qualifyNativeRequest(c,request);
  const release=c.version===2;
  let view=await controller('observe');
  let status=nativeJournalStatus(view,release);
  const reconcile=request.mode==='observe' || status!=='ready';
  async function controlled(op,data) {
    if(op==='observe') return (await controller('observe')).state;
    if(!reconcile) return controller(op,data);
    check(view.claim_current && ['step','reconcile','freeze-pr'].includes(op));
    return controller('observe-'+op,data);
  }
  const factory=async options=>{
    const adapter=await adapterFactory({...options,...(reconcile?{authorizeIntent:async()=>false}:{})});
    if(!reconcile) return adapter;
    const refused=async()=>fail();
    return {...adapter,mergePullRequest:refused,createReleaseTag:refused,mutatePublication:refused};
  };
  const publicationFactory=({operation,number})=>factory({
    config:{appId:c.appId,installationId:c.installationId,repositoryId:c.repositoryId,publisherUid:c.publisherUid},
    binding:{repository:c.binding.repository,prNumber:number,headSha:c.binding.head,baseSha:c.binding.base,
      headBranch:c.binding.head_branch,intentSha256:fingerprint(operation)},publicationPlan:[operation],
    authorizeIntent:async intent=>(await controlled('consume',{intent})).authorized===true});
  if(!['denied','failed'].includes(status) && (!reconcile || view.claim_current)) {
    const {advanceIntegration,advanceRelease}=await import('./integration-gateway.mjs');
    if(release && (!reconcile || view.state.release_effect || view.state.tag_effect)) {
      if(!reconcile) await qualify();
      await releaseStep({config:c,controller:controlled,adapterFactory:factory,advanceRelease,readOnly:reconcile});
    } else if(!release && view.state.publication?.effect==='verified' &&
        (!reconcile || view.state.merge_effect)) {
      if(!reconcile) await qualify();
      await integrationStep({config:c,controller:controlled,adapterFactory:factory,advanceIntegration,readOnly:reconcile});
    } else if(!release && (!reconcile || ['pending','unknown'].includes(view.state.publication?.effect))) {
      await publicationStep({config:c,controller:controlled,adapterFactory:publicationFactory,
        qualify:reconcile?async()=>{}:qualify,readOnly:reconcile});
    }
    view=await controller('observe');status=nativeJournalStatus(view,release);
  }
  // Process cleanup is intentionally absent: the caller must wait/reap the
  // fixed child and establish that fact independently of this JSON response.
  return {version:1,kind:'native-publisher-response-v1',request_sha256:fingerprint(request),...identity,status};
}
function readNativeStdin() {
  const chunks=[];let size=0;
  while(true) {
    const chunk=Buffer.alloc(4096),used=fs.readSync(0,chunk,0,chunk.length,null);
    if(!used) break;
    size+=used;check(size<=16384);chunks.push(chunk.subarray(0,used));
  }
  const bytes=Buffer.concat(chunks),raw=bytes.toString('utf8');check(Buffer.from(raw).equals(bytes));
  return parseNativeRequest(raw);
}

async function fixedGit(c,args) {
  const {stdout}=await promisify(execFile)('/usr/bin/git',[
    '--no-optional-locks','-c',`safe.directory=${c.workspace}`,'-c','core.hooksPath=/dev/null',
    '-c','core.fsmonitor=false','-C',c.workspace,...args],{
    env:{PATH:'/usr/bin:/bin',LANG:'C.UTF-8',GIT_CONFIG_NOSYSTEM:'1',GIT_CONFIG_GLOBAL:'/dev/null',
      GIT_NO_REPLACE_OBJECTS:'1',GIT_TERMINAL_PROMPT:'0'},timeout:10000,maxBuffer:LIMIT,encoding:'buffer'});
  return stdout;
}
function checkedWorkspace(c) {
  check(fs.realpathSync(c.workspace)===c.workspace);
  for(let p=c.workspace;p!=='/';p=dirname(p)) check(fs.lstatSync(p).isDirectory()&&!fs.lstatSync(p).isSymbolicLink());
}
function checkedChangedFile(c,path) {
  check(pathOK(path));const full=join(c.workspace,path);check(fs.realpathSync(full)===full);
  const s=fs.lstatSync(full);check(s.isFile()&&s.nlink===1&&s.size<=LIMIT);
  const fd=fs.openSync(full,fs.constants.O_RDONLY|fs.constants.O_NOFOLLOW|fs.constants.O_NONBLOCK);
  try {const f=fs.fstatSync(fd);check(f.isFile()&&f.ino===s.ino&&f.dev===s.dev&&f.nlink===1&&f.size<=LIMIT);
    const b=fs.readFileSync(fd);check(b.length<=LIMIT);return b;} finally{fs.closeSync(fd);}
}
function installedTree(path,depth=0) {
  check(depth<24);const s=fs.lstatSync(path);
  check(s.uid===0 && (s.mode&0o022)===0 && !s.isSymbolicLink());
  if(s.isDirectory()) for(const name of fs.readdirSync(path)) installedTree(join(path,name),depth+1);
  else check(s.isFile()&&s.nlink===1);
}
async function fixedController(c,op,data={},native=false) {
  // Fixed program and isolated Python import path; no user site/cwd/environment.
  // Python's bridge independently reloads protected config and exact claim state.
  const code=`import sys; sys.path.insert(0, '${INSTALL}/src'); sys.path.insert(0, '${INSTALL}/tools/delivery'); from offmenu.delivery.integration import publisher_main; publisher_main()`;
  return await new Promise((resolve,reject)=>{
    const child=execFile(`${INSTALL}/venv/bin/python`,['-I','-B','-c',code],{
      cwd:INSTALL,env:{PATH:'/usr/bin:/bin',LANG:'C.UTF-8',LANGSMITH_TRACING:'false',LANGCHAIN_TRACING_V2:'false'},
      timeout:10000,maxBuffer:LIMIT,encoding:'utf8'},(error,stdout)=>{
      if(error) return reject(Error('publisher-held'));
      try {resolve(JSON.parse(stdout));}catch{reject(Error('publisher-held'));}
    });
    child.stdin.on('error',()=>{});child.stdin.end(bytesJSON({op,...data,...(native?{
      native_binding_sha256:fingerprint(c.binding),native_runtime_sha256:fingerprint(c.snapshot.native_runtime)}:{})}));
  });
}

export async function main() {
  const native=process.argv.length===3 && process.argv[2]==='--native-rpc';
  check((process.argv.length===2 || native) && fileURLToPath(import.meta.url)===`${INSTALL}/tools/delivery/github-app-publisher.mjs`);
  check(!process.env.NODE_OPTIONS && !process.env.NODE_PATH);
  process.umask(0o077);
  const request=native?readNativeStdin():null;
  const c=loadProtectedConfig();
  installedTree(INSTALL); // no writable code, Python packages, native extension or import path
  for(const [path,pin] of Object.entries(c.codePins))
    check(hash(protectedRead(`${INSTALL}/${path}`,{mode:0o444}))===pin);
  // Installed interpreter is canonical (no symlink interpreter selected by JSON).
  check(hash(protectedRead(`${INSTALL}/venv/bin/python`,{mode:0o555,max:32*LIMIT}))===c.pythonSha256);
  // Verify protected state custody before the Python bridge reads it.
  for(let path=dirname(CLAIM);;path=dirname(path)) {
    const s=fs.lstatSync(path);check(s.isDirectory()&&s.uid===0&&(s.mode&0o022)===0);
    if(path==='/') break;
  }
  for(const path of [CLAIM]) {
    check(fs.realpathSync(path)===path);const s=fs.lstatSync(path);
    check(s.isDirectory()&&s.uid===c.publisherUid&&s.gid===c.publisherGid&&(s.mode&0o7777)===0o700);
  }
  const {createRepositoryGitHubAppAdapter}=await import('./github-app-adapter.mjs');
  checkedWorkspace(c);
  if(native) {
    const qualify=async()=>{
      if(c.version===2) {
        const source=c.binding.candidate.source;
        const raw=await fixedGit(c,['cat-file','commit',source.head]);
        check(objectHash('commit',raw)===source.head && raw.toString().startsWith(`tree ${source.tree}\n`));
        return;
      }
      return qualifyCandidate(c,{
        branchHead:(await fixedGit(c,['rev-parse','--verify',`refs/heads/${c.binding.head_branch}`])).toString().trim(),
        readObject:(type,id)=>fixedGit(c,['cat-file',type,id]),
        readChangedFile:async path=>checkedChangedFile(c,path)});
    };
    return nativePublisherRequest({config:c,request,controller:(op,data)=>fixedController(c,op,data,true),qualify,
      adapterFactory:options=>createRepositoryGitHubAppAdapter({...options,loadPrivateKey:async()=>loadProtectedKey(c)})});
  }
  if(c.version===2) {
    const s=c.binding.candidate.source;
    const raw=await fixedGit(c,['cat-file','commit',s.head]);
    check(objectHash('commit',raw)===s.head && raw.toString().startsWith(`tree ${s.tree}\n`));
    const {advanceRelease}=await import('./integration-gateway.mjs');
    return releaseStep({config:c,controller:(op,data)=>fixedController(c,op,data),
      adapterFactory:options=>createRepositoryGitHubAppAdapter({...options,
        loadPrivateKey:async()=>loadProtectedKey(c)}),advanceRelease});
  }
  const qualify=async()=>qualifyCandidate(c,{
    branchHead:(await fixedGit(c,['rev-parse','--verify',`refs/heads/${c.binding.head_branch}`])).toString().trim(),
    readObject:(type,id)=>fixedGit(c,['cat-file',type,id]),
    readChangedFile:async path=>checkedChangedFile(c,path)});
  // No request/operation, source, PR or key selectors are accepted on stdin/argv.
  await qualify();
  const state=await fixedController(c,'prepare');
  if(state.publication.effect==='verified') {
    const {advanceIntegration}=await import('./integration-gateway.mjs');
    return integrationStep({config:c,controller:(op,data)=>fixedController(c,op,data),
      adapterFactory:options=>createRepositoryGitHubAppAdapter({...options,
        loadPrivateKey:async()=>loadProtectedKey(c)}),advanceIntegration});
  }
  return publicationStep({config:c,controller:(op,data)=>fixedController(c,op,data),qualify,
    adapterFactory:async({operation,number})=>createRepositoryGitHubAppAdapter({
      config:{appId:c.appId,installationId:c.installationId,repositoryId:c.repositoryId,publisherUid:c.publisherUid},
      binding:{repository:c.binding.repository,prNumber:number,headSha:c.binding.head,baseSha:c.binding.base,
        headBranch:c.binding.head_branch,intentSha256:fingerprint(operation)},publicationPlan:[operation],
      loadPrivateKey:async()=>loadProtectedKey(c),
      authorizeIntent:async action=>(await fixedController(c,'consume',{intent:action})).authorized===true})});
}
if(process.argv[1] && fileURLToPath(import.meta.url)===process.argv[1]) {
  main().then(result=>process.stdout.write(JSON.stringify(result)+'\n')).catch(()=>{
    process.stderr.write('publisher-held\n');process.exitCode=1;
  });
}
