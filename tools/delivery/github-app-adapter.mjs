import {createPrivateKey, sign as rsaSign} from 'node:crypto';
import {isDeepStrictEqual} from 'node:util';

const REPOSITORY = 'maldous/offmenu';
const REPOSITORY_ID = 1416253963;
const PERMISSIONS = Object.freeze({contents:'write', pull_requests:'write', metadata:'read'});
const ROOT = '/repos/maldous/offmenu';
const HOST = 'https://api.github.com';
const LIMIT = 1024 * 1024;
const DEADLINE = 10000;
const positive = n => Number.isSafeInteger(n) && n > 0;
const sha = s => typeof s === 'string' && /^[0-9a-f]{40}$/.test(s);
const hash = s => typeof s === 'string' && /^[0-9a-f]{64}$/.test(s);
const exact = (o, keys) => o && Object.getPrototypeOf(o) === Object.prototype &&
  isDeepStrictEqual(Object.keys(o).sort(), [...keys].sort()) &&
  Reflect.ownKeys(o).length === keys.length &&
  keys.every(k => 'value' in Object.getOwnPropertyDescriptor(o,k));
const authoritativeRefusal = Symbol('authoritative-http-refusal');
const failure = (knownRefused=false) => Object.assign(Error('github_app_adapter_refused'), {knownRefused});
function signRS256(input, suppliedKey) {
  const key = suppliedKey?.type === 'private' ? suppliedKey : createPrivateKey(suppliedKey);
  requireFact(key.asymmetricKeyType === 'rsa');
  return rsaSign('RSA-SHA256', Buffer.from(input), key);
}
const requireFact = condition => { if (!condition) throw failure(); };
const repo = r => r?.id === REPOSITORY_ID && r.full_name === REPOSITORY;
const permissions = p => exact(p, Object.keys(PERMISSIONS)) && isDeepStrictEqual(p, PERMISSIONS);
const encode = o => Buffer.from(JSON.stringify(o)).toString('base64url');

/** Source-only seam, NOT a credential receiver or OS isolation proof.
 * Normal future wiring (inside the fixed publisher invocation only):
 *   github = await createRepositoryGitHubAppAdapter({config, binding,
 *     loadPrivateKey, authorizeIntent});
 *   advanceIntegration({controller, github, linear, observe});
 * config has NO defaults for appId/installationId/publisherUid. loadPrivateKey
 * is a trusted no-argument capability for the future fixed root:publisher 0440
 * /etc/offmenu-publisher/github-app-private-key.pem under root:publisher 0750.
 * This module never opens/stats a key, provisions identity, or accepts paths,
 * commands or callbacks from JSON. Trusted signer/HTTP/clock/UID injection is
 * for in-process offline fixtures; these capabilities must never be report data.
 * authorizeIntent must READ the existing Controller intent/claim, authenticate
 * publisher-owner association, and atomically refuse consumed/unknown/replayed
 * intents across invocations. It receives the exact fixed request below and
 * returns true only for that still-pending durable qualified intent. No new
 * journal is provided here; UID or a trusted-invoker claim is NOT task authority.
 * Controller owns outcomes/recovery; this adapter never invokes it itself.
 *
 * Adoption needs actual App/installation/UID/key association, fixed invocation,
 * and coding-descendant boundary proof preventing root/publisher acquisition
 * through native commands, no-new-privileges and approval paths. Retained host
 * sudo User user ALL/NOPASSWD means distinct UID/direct-key denial alone is
 * insufficient. workspace-write/approval-never and cleared env are source facts,
 * not that proof. No production readiness or observed OS isolation is claimed.
 *
 * Fixed publicationPlan also supports qualified Git Data/feature refs/PR metadata.
 * Review requests,
 * independent acceptance, thread-resolution qualification and owner workflow
 * remain unsupported. observe() must supply qualified review/validation and
 * canonical readback; read facts below do not certify acceptance. Head CAS does
 * NOT CAS base atomically: preserve Controller parents/tree/develop checks.
 */
export async function createRepositoryGitHubAppAdapter({config, binding, loadPrivateKey,
  authorizeIntent, publicationPlan, sign = signRS256,
  http = globalThis.fetch, getUid = () => process.getuid(), now = () => Date.now()} = {}) {
  try {
    requireFact(exact(config,['appId','installationId','repositoryId','publisherUid']));
    config = Object.freeze({...config});
    requireFact([config.appId,config.installationId,config.publisherUid].every(positive) &&
      config.repositoryId === REPOSITORY_ID && config.publisherUid !== 1000);
    requireFact(exact(binding,['repository','prNumber','headSha','baseSha','headBranch','intentSha256']));
    binding = Object.freeze({...binding});
    requireFact(binding.repository === REPOSITORY && (positive(binding.prNumber) ||
      (binding.prNumber === null && Array.isArray(publicationPlan) && publicationPlan.length > 0)) &&
      sha(binding.headSha) && sha(binding.baseSha) && hash(binding.intentSha256) &&
      typeof binding.headBranch === 'string' &&
      /^(?:feature|bugfix)\/[a-z0-9][a-z0-9/-]{0,159}$/.test(binding.headBranch) &&
      !binding.headBranch.endsWith('/') && !binding.headBranch.includes('//'));
    requireFact([loadPrivateKey,authorizeIntent,sign,http,getUid,now].every(f => typeof f === 'function'));
    const uidGate = () => requireFact(getUid() === config.publisherUid);
    const seconds = () => { const n=now(); requireFact(Number.isFinite(n) && n>0); return Math.floor(n/1000); };
    uidGate(); // before any key loading, signing or HTTP

    // Requests are generated only here: no caller-controlled URL/headers/query.
    const paths = new Set(['/app', `/app/installations/${config.installationId}`,
      `/app/installations/${config.installationId}/access_tokens`, '/installation/repositories',
      `${ROOT}/pulls/${binding.prNumber}`, `${ROOT}/pulls/${binding.prNumber}/merge`,
      `${ROOT}/pulls/${binding.prNumber}/reviews`, `${ROOT}/pulls/${binding.prNumber}/comments`,
      `${ROOT}/commits/${binding.headSha}`]);
    // Trusted fixed publisher builds these requests from reviewed Git objects.
    // Never populate this capability from unqualified caller JSON.
    const publicationRoutes = new Set();
    const operations = publicationPlan ? structuredClone(publicationPlan) : [];
    for (const operation of operations) {
      requireFact(exact(operation,['kind','method','path','body','readPath','expected']));
      const routes = {blob:['POST',`${ROOT}/git/blobs`],tree:['POST',`${ROOT}/git/trees`],
        commit:['POST',`${ROOT}/git/commits`],ref:[operation.expected === null ? 'POST':'PATCH',
          operation.expected === null ? `${ROOT}/git/refs` : `${ROOT}/git/refs/heads/${binding.headBranch}`],
        'create-pr':['POST',`${ROOT}/pulls`], 'update-pr':['PATCH',`${ROOT}/pulls/${binding.prNumber}`]};
      requireFact(routes[operation.kind] && operation.method === routes[operation.kind][0] &&
        operation.path === routes[operation.kind][1]);
      if (['blob','tree','commit'].includes(operation.kind)) {
        requireFact(sha(operation.expected) && operation.readPath ===
          `${ROOT}/git/${{blob:'blobs',tree:'trees',commit:'commits'}[operation.kind]}/${operation.expected}`);
      } else if (operation.kind === 'ref') {
        requireFact((operation.expected === null || sha(operation.expected)) &&
          operation.readPath === `${ROOT}/git/ref/heads/${binding.headBranch}` &&
          (operation.expected === null ? exact(operation.body,['ref','sha']) &&
            operation.body.ref === `refs/heads/${binding.headBranch}` :
            exact(operation.body,['sha','force']) && operation.body.force === false) &&
          operation.body.sha === binding.headSha);
      } else {
        requireFact(operation.body.base === 'develop' &&
          (operation.kind === 'create-pr' ? exact(operation.body,['title','body','base','head']) &&
            operation.body.head === binding.headBranch : exact(operation.body,['title','body','base'])) &&
          typeof operation.body.title === 'string' && typeof operation.body.body === 'string' &&
          operation.body.title.length > 0 && operation.body.title.length <= 256 &&
          operation.body.body.length <= 65536 && operation.expected === binding.headSha &&
          operation.readPath === (operation.kind === 'create-pr' ?
            `${ROOT}/pulls?state=all&head=maldous:${binding.headBranch}&base=develop` :
            `${ROOT}/pulls/${binding.prNumber}`));
      }
      publicationRoutes.add(`${operation.method} ${operation.path}`);
      publicationRoutes.add(`GET ${operation.readPath}`);
      paths.add(operation.path); paths.add(operation.readPath);
    }
    async function request(method,path,credential,body, allowAbsent=false) {
      uidGate();
      requireFact(paths.has(path) && (!path.includes('?') || publicationRoutes.has(`GET ${path}`)) &&
        (method === 'GET' || (method === 'POST' && path.endsWith('/access_tokens')) ||
          (method === 'PUT' && path === `${ROOT}/pulls/${binding.prNumber}/merge`) ||
          publicationRoutes.has(`${method} ${path}`)));
      const abort = new AbortController();
      let timer;
      try {
        return await Promise.race([
          (async () => {
            const headers = {Accept:'application/vnd.github+json', Authorization:`Bearer ${credential}`,
              'X-GitHub-Api-Version':'2022-11-28'};
            if (body !== undefined) headers['Content-Type']='application/json';
            const response = await http(HOST+path, {method, headers, redirect:'error',
              signal:abort.signal, ...(body === undefined ? {} : {body:JSON.stringify(body)})});
            requireFact(response && !response.redirected &&
              (!response.url || response.url === HOST+path) && Number.isInteger(response.status));
            if (allowAbsent && response.status === 404) return null;
            // Only documented merge/auth refusals establish authoritative nonexecution.
            if ([401,403,404,405,409,422].includes(response.status))
              throw Object.assign(failure(true), {[authoritativeRefusal]:true});
            requireFact(response.status === (method === 'POST' ? 201 : 200));
            requireFact(!response.headers.get('location') && !response.headers.get('link'));
            requireFact(/^application\/json(?:;|$)/i.test(response.headers.get('content-type') || ''));
            const reader=response.body?.getReader();
            requireFact(reader);
            let size=0; const chunks=[];
            try {
              while (true) {
                const {value,done}=await reader.read(); if (done) break;
                size+=value.byteLength; requireFact(size<=LIMIT); chunks.push(Buffer.from(value));
              }
            } finally { await reader.cancel().catch(()=>{}); }
            return JSON.parse(Buffer.concat(chunks).toString('utf8'));
          })(),
          new Promise((_,reject) => { timer=setTimeout(()=>{abort.abort(); reject(failure());},DEADLINE); })
        ]);
      } catch (error) { throw failure(error?.[authoritativeRefusal] === true); }
      finally { clearTimeout(timer); abort.abort(); }
    }
    const issued = seconds();
    let key = await loadPrivateKey();
    uidGate();
    const input = `${encode({alg:'RS256',typ:'JWT'})}.${encode({iat:issued-60,exp:issued+540,iss:config.appId})}`;
    let signature = await sign(input,key); key = undefined;
    requireFact(Buffer.isBuffer(signature) || signature instanceof Uint8Array);
    let jwt = `${input}.${Buffer.from(signature).toString('base64url')}`; signature=undefined;
    const app = await request('GET','/app',jwt);
    requireFact(app?.id === config.appId && permissions(app.permissions));
    const installation = await request('GET',`/app/installations/${config.installationId}`,jwt);
    requireFact(installation?.id === config.installationId && installation.app_id === config.appId &&
      installation.repository_selection === 'selected' && installation.suspended_at === null &&
      permissions(installation.permissions));
    const grant = await request('POST',`/app/installations/${config.installationId}/access_tokens`,jwt,
      {repository_ids:[REPOSITORY_ID],permissions:PERMISSIONS});
    jwt=undefined;
    requireFact(typeof grant?.token === 'string' && /^[\x21-\x7e]{1,4096}$/.test(grant.token) &&
      permissions(grant.permissions) && Array.isArray(grant.repositories) &&
      grant.repositories.length === 1 && repo(grant.repositories[0]));
    const expiry=Date.parse(grant.expires_at)/1000;
    requireFact(typeof grant.expires_at === 'string' && Number.isFinite(expiry) &&
      expiry > seconds()+60 && expiry <= issued+3660);
    const token=grant.token;
    const tokenGate = () => { uidGate(); requireFact(seconds()<expiry-30); };
    tokenGate();
    const installed = await request('GET','/installation/repositories',token);
    requireFact(installed?.total_count === 1 && Array.isArray(installed.repositories) &&
      installed.repositories.length === 1 && repo(installed.repositories[0]));
    let attempted=false, busy=false;
    const checkPR = (repository,number) => requireFact(repository === REPOSITORY && number === binding.prNumber);
    async function getPullRequest(repository,number) {
      try {
        checkPR(repository,number); tokenGate();
        const p=await request('GET',`${ROOT}/pulls/${number}`,token);
        requireFact(p?.number === number && repo(p.base?.repo) && repo(p.head?.repo) &&
          sha(p.head.sha) && sha(p.base.sha) && p.base.ref === 'develop' &&
          p.head.ref === binding.headBranch && typeof p.merged === 'boolean' &&
          typeof p.draft === 'boolean' && [true,false,null].includes(p.mergeable) &&
          ['open','closed'].includes(p.state));
        return {merged:p.merged, ...(p.merged && sha(p.merge_commit_sha) ? {merge_commit_sha:p.merge_commit_sha} : {}),
          head_sha:p.head.sha, base_sha:p.base.sha, base:p.base.ref,
          head:p.head.ref, draft:p.draft, mergeable:p.state === 'open' ? p.mergeable : false};
      } catch(error) { throw failure(error?.knownRefused === true); }
    }
    async function mergePullRequest(args) {
      // Fail closed even if a caller tries this capability outside the gateway.
      if (busy || attempted) return {merged:false,known_refused:true};
      busy=true;
      try {
        requireFact(exact(args,['repository_full_name','pr_number','expected_head_sha','merge_method']) &&
          args.repository_full_name === REPOSITORY && args.pr_number === binding.prNumber &&
          args.expected_head_sha === binding.headSha && args.merge_method === 'merge');
        tokenGate();
        const p=await getPullRequest(REPOSITORY,binding.prNumber);
        requireFact(!p.merged && p.head_sha === binding.headSha && p.base_sha === binding.baseSha &&
          !p.draft && p.mergeable === true);
        // Exact canonical request + immutable durable intent; never UID-only authority.
        const intent=Object.freeze({kind:'merge-pr',repository:REPOSITORY,pr_number:binding.prNumber,
          expected_head_sha:binding.headSha,expected_base_sha:binding.baseSha,
          expected_head_branch:binding.headBranch,merge_method:'merge',intent_sha256:binding.intentSha256});
        requireFact(await authorizeIntent(intent) === true);
        tokenGate();
        attempted=true; // no mutation retries, including timeout, malformed or 5xx reply
        const result=await request('PUT',`${ROOT}/pulls/${binding.prNumber}/merge`,token,
          {sha:binding.headSha,merge_method:'merge'});
        requireFact(result?.merged === true && sha(result.sha));
        return {merged:true,merge_commit_sha:result.sha};
      } catch(error) {
        return {merged:false,known_refused:!attempted || error?.knownRefused === true};
      } finally { busy=false; }
    }
    async function readCanonicalFacts(mergeSha) {
      try {
        requireFact(sha(mergeSha)); tokenGate();
        // Caller supplies only a SHA; all routes remain fixed to this repository.
        paths.add(`${ROOT}/commits/${mergeSha}`);
        paths.add(`${ROOT}/compare/${mergeSha}...develop`);
        const readCommit=async id => {
          const c=await request('GET',`${ROOT}/commits/${id}`,token);
          requireFact(c?.sha === id && sha(c.commit?.tree?.sha) && Array.isArray(c.parents) &&
            c.parents.length<=2 && c.parents.every(p=>sha(p.sha)));
          return {sha:c.sha,tree:c.commit.tree.sha,parents:c.parents.map(p=>p.sha)};
        };
        const source=await readCommit(binding.headSha), merge=await readCommit(mergeSha);
        const comparison=await request('GET',`${ROOT}/compare/${mergeSha}...develop`,token);
        requireFact(comparison?.base_commit?.sha === mergeSha &&
          sha(comparison.merge_base_commit?.sha) &&
          ['ahead','behind','identical','diverged'].includes(comparison.status));
        return {source_commit:source,merge_commit:merge,
          develop_contains_merge:comparison.merge_base_commit.sha === mergeSha &&
            ['ahead','identical'].includes(comparison.status)};
      } catch(error) { throw failure(error?.knownRefused === true); }
    }
    async function readExactHeadReviewFacts() {
      try {
        const p=await getPullRequest(REPOSITORY,binding.prNumber);
        requireFact(p.head_sha === binding.headSha && p.base_sha === binding.baseSha);
        const reviews=await request('GET',`${ROOT}/pulls/${binding.prNumber}/reviews`,token);
        const comments=await request('GET',`${ROOT}/pulls/${binding.prNumber}/comments`,token);
        requireFact(Array.isArray(reviews) && Array.isArray(comments));
        const selected=reviews.filter(r=>r.commit_id === binding.headSha);
        const findings=comments.filter(c=>c.commit_id === binding.headSha);
        requireFact(selected.every(r=>positive(r.id) && positive(r.user?.id) &&
          ['APPROVED','CHANGES_REQUESTED','COMMENTED','DISMISSED','PENDING'].includes(r.state)) &&
          findings.every(c=>positive(c.id) && positive(c.user?.id)));
        const after=await getPullRequest(REPOSITORY,binding.prNumber);
        requireFact(after.head_sha === binding.headSha && after.base_sha === binding.baseSha);
        return {head:binding.headSha,base:binding.baseSha,
          reviews:selected.map(r=>({id:r.id,reviewer_id:r.user.id,state:r.state,head:binding.headSha})),
          findings:findings.map(c=>({id:c.id,reviewer_id:c.user.id,head:binding.headSha})),
          qualification:'facts-only-requires-independent-owner-review-and-thread-resolution'};
      } catch(error) { throw failure(error?.knownRefused === true); }
    }
    let publicationAttempted = false;
    async function readPublication(index) {
      try {
        const operation=operations[index]; requireFact(operation); tokenGate();
        const result=await request('GET',operation.readPath,token,undefined,true);
        if(operation.kind === 'create-pr' && Array.isArray(result) && result.length === 1) {
          const p=result[0];
          requireFact(positive(p?.number) && repo(p.base?.repo) && repo(p.head?.repo) &&
            p.head.ref === binding.headBranch && p.head.sha === binding.headSha && p.base.ref === 'develop');
          const path=`${ROOT}/pulls/${p.number}`; paths.add(path); publicationRoutes.add(`GET ${path}`);
          return [await request('GET',path,token)];
        }
        return result;
      } catch { throw failure(); }
    }
    async function mutatePublication(index) {
      // Cross-process replay prevention is the fixed helper's Controller consume.
      // An instance also has a one-mutation bound, even on malformed replies.
      try {
        const operation=operations[index]; requireFact(operation && !publicationAttempted);
        tokenGate(); requireFact(await authorizeIntent(operation) === true);
        publicationAttempted=true;
        const reply=await request(operation.method,operation.path,token,operation.body);
        if (['blob','tree','commit'].includes(operation.kind)) requireFact(reply?.sha === operation.expected);
        return {status:'readback-required'};
      } catch { return {status:'readback-required'}; }
    }
    return Object.freeze({getPullRequest,mergePullRequest,readCanonicalFacts,readExactHeadReviewFacts,
      readPublication,mutatePublication,
      provenance:Object.freeze({kind:'github-app-installation',app_id:app.id,
        installation_id:installation.id,repository_id:installed.repositories[0].id,
        publisher_uid:config.publisherUid,os_isolation_verified:false})});
  } catch(error) { throw failure(error?.knownRefused === true); }
}
