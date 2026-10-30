import {spawn, execFile} from 'node:child_process';
import {promisify, isDeepStrictEqual} from 'node:util';
import {createHash, randomBytes} from 'node:crypto';
import {readFileSync, realpathSync} from 'node:fs';
import {fileURLToPath} from 'node:url';

const reviewSource = fileURLToPath(new URL('../../', import.meta.url)).replace(/\/$/, '');
const reviewPython = '/home/user/src/offmenu/.delivery/stokowski/venv/bin/python';
const reviewEntry = 'tools/delivery/stokowski_unit_review.py';
const reviewLimit = 1024 * 1024;
const sha = bytes => createHash('sha256').update(bytes).digest('hex');
// Wire v2: SHA256 of exact UTF-8 JSON strings, never canonical JSON hashes.
// JSON numbers permit finite fractions and safe integers; -0, nonfinite and
// unsafe integers are refused. Objects have plain string keys, no surrogates,
// undefined, cycles, sparse arrays or non-JSON types. Key order is immaterial
// to semantic matching, but the exact transmitted order is bound by the hash.
export function reviewWireBytes(value) {
  const seen = new Set();
  function check(v, depth=0) {
    if (depth >= 64) throw Error('local_review_refused');
    if (v === null || typeof v === 'boolean') return;
    if (typeof v === 'number') {
      if (!Number.isFinite(v) || Object.is(v,-0) ||
          (Number.isInteger(v) && !Number.isSafeInteger(v))) throw Error('local_review_refused');
      return;
    }
    if (typeof v === 'string') {
      if (!v.isWellFormed()) throw Error('local_review_refused');
      return;
    }
    if (typeof v !== 'object' || seen.has(v) ||
        (!Array.isArray(v) && Object.getPrototypeOf(v)!==Object.prototype)) throw Error('local_review_refused');
    seen.add(v);
    if (Reflect.ownKeys(v).some(k=>typeof k!=='string')) throw Error('local_review_refused');
    const keys=Object.keys(v);
    if (Array.isArray(v) && (keys.length!==v.length || keys.some((k,i)=>k!==String(i)))) throw Error('local_review_refused');
    if (Reflect.ownKeys(v).length!==keys.length+(Array.isArray(v)?1:0)) throw Error('local_review_refused');
    for (const k of keys) {
      check(k,depth+1);
      const d=Object.getOwnPropertyDescriptor(v,k);
      if (!d || !('value' in d)) throw Error('local_review_refused');
      check(d.value,depth+1);
    }
    seen.delete(v);
  }
  check(value);
  const bytes=JSON.stringify(value);
  if (Buffer.byteLength(bytes)>reviewLimit) throw Error('local_review_refused');
  return bytes;
}

/** Fixed local process, instantiated only inside the authenticated owner caller.
 * reviewedCurrentUnit is out-of-band reviewed configuration, never report data.
 * Timeout/lost reply is reconciled read-only after kill/reap; no second write.
 */
async function fixedUnitReviewWriter(context) {
  reviewWireBytes(context);
  context = structuredClone(context);
  if (sha(readFileSync(realpathSync(reviewPython))) !== context.python_sha256) throw Error('local_review_refused');
  const required = [reviewEntry, 'tools/delivery/integration-gateway.mjs',
    'stokowski_adapter','stokowski_worker','stokowski_prepare','stokowski_operations',
    'symphony_capacity','symphony_tasks','symphony_workspace','symphony_codex',
    'symphony_protocol','windmill_runner'].map(n=>n.includes('/')?n:`tools/delivery/${n}.py`);
  if (!/^[0-9a-f]{40}$/.test(context.source_head) ||
      required.some(n=>!context.source_sha256[n])) throw Error('local_review_refused');
  const git = async args => (await promisify(execFile)('/usr/bin/git', ['-C',reviewSource,...args], {
    env:{PATH:'/usr/bin:/bin',LANG:'C.UTF-8'},timeout:2000,maxBuffer:reviewLimit,encoding:'buffer'
  })).stdout;
  if ((await git(['rev-parse','HEAD'])).toString().trim()!==context.source_head) throw Error('local_review_refused');
  for (const [name,hash] of Object.entries(context.source_sha256)) {
    if (!/^(?:tools\/delivery|src\/offmenu\/delivery)\/[a-z0-9_./-]+$/.test(name) ||
        name.split('/').some(p=>p==='.' || p==='..') ||
        realpathSync(`${reviewSource}/${name}`)!==`${reviewSource}/${name}` ||
        sha(readFileSync(`${reviewSource}/${name}`))!==hash ||
        sha(await git(['show',`${context.source_head}:${name}`]))!==hash) throw Error('local_review_refused');
  }
  async function invoke(mode, payload, evidence) {
    const input = JSON.stringify({version:2,mode,payload,evidence});
    if (Buffer.byteLength(input) > reviewLimit) throw Error('local_review_refused');
    return await new Promise((resolve,reject)=>{
      const child = spawn(reviewPython, ['-B', `${reviewSource}/${reviewEntry}`], {
        cwd:reviewSource, shell:false, detached:true, env:{PATH:'/usr/bin:/bin', PYTHONPATH:`${reviewSource}/src`, LANG:'C.UTF-8'},
        stdio:['pipe','pipe','pipe']
      });
      let output=[], size=0, failed=false;
      const stop = () => { failed=true; try { process.kill(-child.pid,'SIGKILL'); } catch { child.kill('SIGKILL'); } };
      const timer=setTimeout(stop, 10000);
      child.stdout.on('data',chunk=>{size+=chunk.length;if(size>reviewLimit){stop();}else output.push(chunk);});
      // Drain bounded diagnostic-free child stderr without exposing it.
      child.stderr.on('data',chunk=>{size+=chunk.length;if(size>reviewLimit){stop();}});
      child.stdin.on('error',()=>{failed=true;});
      child.on('error',()=>{failed=true;});
      child.on('close',code=>{
        clearTimeout(timer);
        if(failed || code!==0) return reject(Error('local_review_uncertain'));
        try {resolve(JSON.parse(Buffer.concat(output).toString('utf8')));} catch {reject(Error('local_review_uncertain'));}
      });
      child.stdin.end(input);
    });
  }
  return async envelope => {
    const payload = reviewWireBytes({context,envelope});
    const request = sha(payload);
    const binding = JSON.parse(readFileSync(`${context.controller_directory}/binding.json`));
    const evidence = reviewWireBytes({issue:context.issue,unit_binding:context.unit_binding,
      integration_binding:binding,snapshot:envelope.snapshot,decision:envelope.decision,
      validation_receipt:context.validation_receipt});
    function verify(reply) {
      if (reply.version!==2 || reply.request_sha256!==request || reply.issue!==context.issue ||
          reply.operation_key!==envelope.snapshot.validation.operation_key ||
          reply.source_head!==context.source_head ||
          !isDeepStrictEqual(reply.unit_binding,context.unit_binding) ||
          reply.evidence_sha256!==sha(evidence)) throw Error('local_review_refused');
      return reply;
    }
    const prior=verify(await invoke('status',payload,evidence));
    if(prior.status==='retained') return prior;
    if(prior.status!=='absent') throw Error('local_review_refused');
    try {
      const reply=verify(await invoke('write',payload,evidence));
      if(reply.status!=='retained' || reply.evidence_sha256!==prior.evidence_sha256) throw Error('local_review_uncertain');
      return reply;
    } catch {
      // close fires only after the child has exited and pipes have closed.
      const reply=verify(await invoke('status',payload,evidence));
      if(reply.status!=='retained' || reply.evidence_sha256!==prior.evidence_sha256) throw Error('local_review_uncertain');
      return reply;
    }
  };
}

/** Finite authenticated connector-owner gateway; never a coding-child tool.
 * Existing authenticated adapters supply observations. Persisted controller
 * intent precedes mutations; canonical readback alone certifies their effects.
 */
export async function advanceIntegration({controller, github, linear, observe, unitReviewWriter, reviewedCurrentUnit}) {
  let snapshot = await observe();
  let decision = await controller.step(snapshot);
  // Only the fresh controller qualification may cross this seam; repair and
  // reconciliation decisions never become unit verdicts. Normal flow is unchanged.
  if ((reviewedCurrentUnit || unitReviewWriter) && decision.status === 'merge-intent' &&
      decision.action?.kind === 'merge-pr' && decision.merge_effect === 'pending' &&
      decision.qualification_sha256 && !snapshot.cancel_requested &&
      !snapshot.unresolved_findings?.length && snapshot.review?.verdict === 'accept' &&
      !snapshot.review?.findings?.length) {
    try {
      // Reviewed production context binds the actual fixed process directly.
      if (reviewedCurrentUnit) unitReviewWriter = await fixedUnitReviewWriter(reviewedCurrentUnit);
      await unitReviewWriter(structuredClone({snapshot, decision}));
    } catch (error) {
      // Publication can fail, but no GitHub mutation has been attempted.
      await controller.outcome('merge', 'not-issued');
      throw error;
    }
  }
  let mergeIssued = false;
  // At most one merge and the controller's three metadata attempts. Every
  // returned metadata action is consumed here, including slow-readback retries.
  for (let used = 0; used < 4 && decision.action; used++) {
    const action = decision.action;
    if (action.kind === 'merge-pr') {
      if (mergeIssued) return await controller.outcome('merge', 'not-issued');
      let pr;
      try {
        pr = await github.getPullRequest(action.repository, action.pr_number);
      } catch (error) {
        // No mutation has been invoked. A failed read cannot create an unknown
        // merge effect. Explicit permission refusals still stop for authority.
        return await controller.outcome('merge', error.knownRefused === true ? 'refused' : 'not-issued');
      }
      if (!pr || pr.merged || pr.head_sha !== action.expected_head_sha ||
          pr.base_sha !== action.expected_base_sha || pr.base !== 'develop' ||
          pr.head !== action.expected_head_branch ||
          pr.draft !== false || pr.mergeable !== true) {
        return await controller.outcome('merge', 'not-issued');
      }
      let outcome;
      mergeIssued = true;
      try {
        const response = await github.mergePullRequest({
          repository_full_name: action.repository, pr_number: action.pr_number,
          expected_head_sha: action.expected_head_sha, merge_method: 'merge'
        });
        outcome = response.merged === true ? 'succeeded' :
          response.known_refused === true ? 'refused' : 'uncertain';
      } catch (error) {
        outcome = error.knownRefused === true ? 'refused' : 'uncertain';
      }
      await controller.outcome('merge', outcome);
    } else if (action.kind === 'update-linear') {
      let outcome;
      try {
        await linear.completeIssue(action.issue_id, {
          merge_commit_sha: action.merge_commit_sha,
          validation_operation_key: action.validation_operation_key
        });
        outcome = 'succeeded';
      } catch (error) {
        outcome = error.knownRefused === true ? 'refused' : 'uncertain';
      }
      await controller.outcome('linear', outcome);
    } else {
      // Repairs are work packets, never report-supplied executable commands.
      return decision;
    }
    decision = await controller.step(await observe());
  }
  if (decision.action?.kind === 'update-linear') {
    // Defensive bound: do not strand a newly persisted but unconsumed intent.
    return await controller.outcome('linear', 'not-issued');
  }
  return decision;
}


/** One finite pre-execution publication by the authenticated connector owner.
 * github.getProfile is the owner's existing cloud github_get_profile adapter,
 * never a packet-supplied callback. reviewedPublication is out-of-band reviewed
 * current configuration. Local stdin provides no isolation from malicious UID peers.
 * This action is separate from post-review advanceIntegration and never dispatches.
 */
export async function prepareOwnerPublication({github, reviewedPublication}) {
  reviewWireBytes(reviewedPublication);
  const context = structuredClone(reviewedPublication);
  const limit = 65536;
  // Reviewed repository blobs are separate from the bounded publication wire.
  const sourceLimit = 1024 * 1024;
  const entry = 'tools/delivery/stokowski_publication.py';
  const required = [entry, 'tools/delivery/integration-gateway.mjs',
    ...['stokowski_prepare','symphony_launch','stokowski_adapter','stokowski_worker',
      'stokowski_operations','symphony_capacity','symphony_tasks','symphony_workspace',
      'symphony_codex','symphony_protocol','windmill_runner'].map(n=>`tools/delivery/${n}.py`)];
  if (sha(readFileSync(realpathSync(reviewPython))) !== context.python_sha256 ||
      !/^[0-9a-f]{40}$/.test(context.source_head)) throw Error('publication_bridge_refused');
  const git = async args => (await promisify(execFile)('/usr/bin/git', ['-C',reviewSource,...args], {
    env:{PATH:'/usr/bin:/bin',LANG:'C.UTF-8'}, timeout:2000,maxBuffer:sourceLimit,encoding:'buffer'
  })).stdout;
  if ((await git(['rev-parse','HEAD'])).toString().trim()!==context.source_head ||
      (await git(['branch','--show-current'])).toString().trim()!==context.source_branch ||
      required.some(name=>!context.source_sha256[name]))
    throw Error('publication_bridge_refused');
  for (const [name,hash] of Object.entries(context.source_sha256)) {
    if (!/^(?:tools\/delivery|src\/offmenu\/delivery)\/[a-z0-9_./-]+$/.test(name) ||
        name.split('/').some(p=>p==='.' || p==='..') ||
        realpathSync(`${reviewSource}/${name}`)!==`${reviewSource}/${name}` ||
        sha(readFileSync(`${reviewSource}/${name}`))!==hash ||
        sha(await git(['show',`${context.source_head}:${name}`]))!==hash) throw Error('publication_bridge_refused');
  }
  // No saved principal/report is consulted to produce this observation.
  const profile = await github.getProfile();
  if (!profile || !['string','number'].includes(typeof profile.id) ||
      typeof profile.login!=='string' || !profile.login ||
      !/^[0-9]+$/.test(String(profile.id))) throw Error('publication_bridge_refused');
  const payload = reviewWireBytes({context, nonce:randomBytes(32).toString('hex'),
    observed_at:Date.now()/1000,
    provenance:{service:'github',connector_tool:'mcp__codex_apps__github_get_profile',
      flow:'same-invocation-getProfile-to-fixed-stdin'},
    principal:{service:'github',principal_id:String(profile.id),login:profile.login}});
  const request = sha(payload);
  if (Buffer.byteLength(payload)>limit) throw Error('publication_bridge_refused');
  async function invoke(mode) {
    const input = JSON.stringify({version:1,mode,payload,request_sha256:request});
    if (Buffer.byteLength(input)>limit) throw Error('publication_bridge_refused');
    return await new Promise((resolve,reject)=>{
      const child = spawn(reviewPython, ['-B', `${reviewSource}/${entry}`], {
        cwd:reviewSource,shell:false,detached:true,
        env:{PATH:'/usr/bin:/bin',LANG:'C.UTF-8',PYTHONPATH:`${reviewSource}/src`},
        stdio:['pipe','pipe','pipe']
      });
      let output=[], size=0, failed=false;
      const stop=()=>{failed=true;try{process.kill(-child.pid,'SIGKILL');}catch{child.kill('SIGKILL');}};
      const timer=setTimeout(stop,60000);
      child.stdout.on('data',chunk=>{size+=chunk.length;if(size>limit)stop();else output.push(chunk);});
      child.stderr.on('data',chunk=>{size+=chunk.length;if(size>limit)stop();});
      child.stdin.on('error',()=>{failed=true;});
      child.on('error',()=>{failed=true;});
      child.on('close',code=>{
        clearTimeout(timer);
        if (failed || code!==0) return reject(Error('publication_bridge_uncertain'));
        try {
          const reply=JSON.parse(Buffer.concat(output).toString('utf8'));
          if(reply.version!==1 || sha(reply.response)!==reply.response_sha256) throw Error();
          const response=JSON.parse(reply.response);
          if(response.request_sha256!==request || response.nonce!==JSON.parse(payload).nonce ||
              response.result.dispatches!==0 ||
              !['published','duplicate','refused','uncertain'].includes(response.result.status)) throw Error();
          resolve(response.result);
        } catch {reject(Error('publication_bridge_uncertain'));}
      });
      child.stdin.end(input);
    });
  }
  try {return await invoke('prepare');}
  catch {
    // The original child is reaped. Only read the exact retained result; never
    // re-enter prepare_publication after lost transport or an unresolved intent.
    return await invoke('status');
  }
}
