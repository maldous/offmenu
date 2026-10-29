"""One finite Codex process tree per admitted Stokowski attempt.

Run as a separate supervisor process: descendant cleanup must never act on
sibling coding sessions in the Stokowski coordinator.
"""
import argparse
import ctypes
import hashlib
import json
import os
from pathlib import Path
import signal
import subprocess
import time

from symphony_capacity import Pool, AdmissionError, host_snapshot, digest
from symphony_codex import isolated_codex_environment
from symphony_protocol import BINARY
from symphony_tasks import load_manifest, runtime_lease_ids
from symphony_workspace import checkpoint
from windmill_runner import cleanup, capacity_usage

MODEL = 'gpt-6.1-sol'
SAFE_ENV = {'PATH', 'HOME', 'USER', 'LOGNAME', 'LANG', 'LC_ALL', 'TMPDIR',
            'CODEX_HOME', 'CODEX_SQLITE_HOME'}


def child_environment(environment):
    """An allowlist, not a blacklist: unknown provider credentials stay out."""
    result = {k: v for k, v in environment.items() if k in SAFE_ENV}
    result.update(LANGCHAIN_TRACING_V2='false', LANGSMITH_TRACING='false',
                  OTEL_SDK_DISABLED='true', GIT_CONFIG_COUNT='0')
    return result


def codex_command(workspace, final_message, model=MODEL):
    if model != MODEL:
        raise ValueError('Unreviewed provider/model route')
    return [BINARY, 'exec', '--json', '--ignore-user-config',
            '--sandbox', 'workspace-write', '-c', 'approval_policy="never"',
            '-c', 'model_reasoning_effort="medium"', '--model', model,
            '--cd', str(workspace), '--output-last-message', str(final_message), '-']


def git(workspace, *args):
    return subprocess.check_output(['git', '-C', str(workspace), *args],
                                   env=child_environment(os.environ), text=True).strip()


def changed_paths(workspace, base_revision='HEAD'):
    paths = subprocess.check_output(['git', '-C', str(workspace), 'diff',
                                     '--name-only', base_revision, '-z']).decode().split('\0')
    paths += subprocess.check_output(['git', '-C', str(workspace), 'ls-files',
                                      '--others', '--exclude-standard', '-z']).decode().split('\0')
    return sorted(set(p for p in paths if p))


def summarize_events(path):
    result = {'session_id': None, 'usage': {}, 'turn_completed': False}
    for line in path.read_text(errors='replace').splitlines():
        try:
            event = json.loads(line)
        except ValueError:
            continue
        if event.get('type') == 'thread.started':
            result['session_id'] = event.get('thread_id')
        if event.get('type') == 'turn.completed':
            result['turn_completed'] = True
            result['usage'] = event.get('usage', {})
    return result


def supervise(command, prompt, workspace, environment, directory, timeout, resources,
              process_ceiling=64):
    """Bounded execution with unconditional cleanup; no pool release here."""
    if not 1 <= timeout <= 600:
        raise ValueError('Invalid finite timeout')
    if (directory.parent.parent/'cancel.json').exists():
        return {'status':'cancelled','child_tree_gone':True,'exit_code':None}
    if ctypes.CDLL(None, use_errno=True).prctl(36, 1, 0, 0, 0) != 0:
        raise RuntimeError('Subreaper unavailable')
    result = {'status': 'failed', 'child_tree_gone': False, 'exit_code': None}
    proc = None
    stopping = False

    def stop(signum, frame):
        nonlocal stopping
        stopping = True

    previous = {s: signal.signal(s, stop) for s in (signal.SIGTERM, signal.SIGINT)}
    try:
        deadline = time.monotonic()+timeout
        with (directory/'stdout.jsonl').open('wb') as out, (directory/'stderr.log').open('wb') as err:
            proc = subprocess.Popen(command, cwd=workspace, env=environment,
                                    stdin=subprocess.PIPE, stdout=out, stderr=err,
                                    start_new_session=True, bufsize=0)
            os.set_blocking(proc.stdin.fileno(), False)
            remaining_prompt = memoryview(prompt.encode())
            while proc.poll() is None:
                usage = capacity_usage()
                reason = None
                if stopping or (directory.parent.parent/'cancel.json').exists():
                    reason = 'cancelled'
                elif time.monotonic() >= deadline:
                    reason = 'timed_out'
                elif usage['processes'] > process_ceiling:
                    reason = 'process_budget'
                elif usage['rss_bytes'] > resources['memory_bytes']:
                    reason = 'memory_budget'
                elif out.tell() + err.tell() > 1048576:
                    reason = 'log_budget'
                if reason:
                    result['status'] = reason
                    break
                if proc.stdin and not proc.stdin.closed:
                    if remaining_prompt:
                        try:
                            sent = os.write(proc.stdin.fileno(),remaining_prompt[:65536])
                            remaining_prompt = remaining_prompt[sent:]
                        except BlockingIOError:
                            pass
                        except BrokenPipeError:
                            proc.stdin.close()
                    else:
                        proc.stdin.close()
                time.sleep(.02)
            if proc.poll() is not None:
                result.update(exit_code=proc.returncode,
                              status='succeeded' if proc.returncode == 0 else 'failed')
    except BaseException as error:
        result['error_type'] = type(error).__name__
    finally:
        try:
            if proc is not None:
                if proc.stdin and not proc.stdin.closed:
                    proc.stdin.close()
                result['child_tree_gone'] = cleanup(proc)
                result['exit_code'] = proc.returncode
        finally:
            for s, handler in previous.items():
                signal.signal(s, handler)
    if not result['child_tree_gone']:
        result['status'] = 'uncertain'
    return result


def execute(runtime, issue, request):
    runtime = runtime.resolve()
    manifest = load_manifest(runtime/'manifest.json')
    task = manifest['tasks'][issue]
    policy = json.loads((runtime/'capacity-policy.json').read_text())
    workspace = runtime/'workspaces'/issue
    if git(workspace, 'rev-parse', 'HEAD') != manifest['base_revision'] or git(
            workspace, 'branch', '--show-current') != manifest['branch']:
        raise AdmissionError('Source identity changed')
    if changed_paths(workspace):
        raise AdmissionError('Unreconciled workspace changes')
    directory = runtime/'attempts'/issue
    directory.mkdir(parents=True, exist_ok=True, mode=0o700)
    binding = dict(branch=manifest['branch'], head=manifest['base_revision'],
                   owner=task['owner'], write_roots=task['allowed_paths'],
                   resources=task['resources'],
                   task_sha256=digest(dict(runtime=str(runtime), manifest=manifest, request=request)))
    receipt_path = directory/'receipt.json'
    if receipt_path.exists():
        raise AdmissionError('Completed or uncertain attempt requires reconciliation; no replay')
    intent_path = directory/'intent.json'
    if intent_path.exists():
        prior = json.loads(intent_path.read_text())
        if prior.get('binding') != binding:
            raise AdmissionError('immutable_binding_conflict')
        raise AdmissionError('Existing resource lease or retained intent: reconcile_or_new_task_required')
    if (runtime/'cancel.json').exists():
        raise AdmissionError('Runtime cancellation requested before admission')
    lease = runtime_lease_ids(runtime, manifest)[issue]
    pool = Pool(policy['symphony']['pool_path'], policy)
    proof = json.loads((runtime/'provider-proof.json').read_text())
    admitted = pool.admit(lease, binding, proof, host_snapshot(runtime))
    if admitted.get('reused'):
        raise AdmissionError('Existing resource lease requires reconciliation')
    checkpoint(directory/'intent.json', dict(lease=lease, binding=binding))
    result = {'status': 'uncertain', 'child_tree_gone': False}
    try:
        cpus = sorted(os.sched_getaffinity(0))
        first = policy['host']['cpu_reserve']
        width = (policy['symphony']['cpu_budget_millis']+999)//1000
        if len(cpus) <= first:
            raise AdmissionError('No admitted coding CPUs')
        os.sched_setaffinity(0, cpus[first:first+width])
        with isolated_codex_environment(child_environment(os.environ), directory) as env:
            result = supervise(codex_command(workspace, directory/'final-message.txt'),
                               request['prompt'], workspace, env, directory,
                               request['timeout_seconds'], task['resources'],
                               policy['windmill']['computation_subprocesses_per_job'])
        if (directory/'stdout.jsonl').exists():
            result.update(summarize_events(directory/'stdout.jsonl'))
        final_head = git(workspace,'rev-parse','HEAD')
        final_branch = git(workspace,'branch','--show-current')
        identity_changed = (final_head != manifest['base_revision']
                            or final_branch != manifest['branch'])
        paths = changed_paths(workspace, manifest['base_revision'])
        violations = [p for p in paths if not any(p == a or p.startswith(a+'/')
                                                 for a in task['allowed_paths'])]
        outputs = {p: hashlib.sha256((workspace/p).read_bytes()).hexdigest()
                   for p in paths if (workspace/p).is_file() and not (workspace/p).is_symlink()}
        result.update(issue=issue, lease=lease, binding_sha256=digest(binding),
                      source_head=manifest['base_revision'], scope_violations=violations,
                      final_head=final_head, final_branch=final_branch,
                      source_identity_changed=identity_changed,
                      output_sha256=outputs, accepted_delivery=False,
                      provider_route='codex-chatgpt', requested_model=MODEL,
                      credential_exported=False)
        if identity_changed or violations or not result.get('turn_completed'):
            result['status'] = 'failed'
    finally:
        # Retain admission whenever termination cannot be proven. A crash before
        # this block leaves intent + running lease, blocking blind replay.
        checkpoint(receipt_path, result)
        if result.get('child_tree_gone'):
            pool.finish(lease, True, 'succeeded' if result['status'] == 'succeeded'
                        else ('cancelled' if result['status'] == 'cancelled' else 'failed'))
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--runtime', required=True, type=Path)
    parser.add_argument('--issue', required=True)
    args = parser.parse_args()
    try:
        request = json.loads((args.runtime/'requests'/(args.issue+'.json')).read_text())
        result = execute(args.runtime, args.issue, request)
        print(json.dumps(result))
        raise SystemExit(0 if result['status'] == 'succeeded' else 2)
    except (ValueError, OSError, AdmissionError) as error:
        print(json.dumps({'status': 'blocked', 'error_type': type(error).__name__}))
        raise SystemExit(2)
