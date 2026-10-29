"""Pinned Stokowski orchestration with OffMenu ownership and Codex execution.

No global monkeypatches persist: these reviewed adaptations apply only inside
this OffMenu coordinator process. Arbitrary upstream shell hooks are disabled.
"""
import argparse
import asyncio
import fcntl
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time

from symphony_capacity import AdmissionError
from symphony_tasks import load_manifest
from symphony_workspace import checkpoint
from stokowski_worker import child_environment, MODEL

SOURCE = Path(__file__).resolve().parents[2]
PIN = '339cbf4f3f6d9acdf808f9ba4c639d029cdd8e16'
PROJECT = 'ce60c1ab-a732-4a71-8471-14c9dc393886'
SLUG = 'ccd080f4f6f0'


def credential():
    """Existing approved key, in coordinator memory only; never print it."""
    value = os.environ.get('OFFMENU_LINEAR_API_KEY') or os.environ.get('LINEAR_API_KEY')
    if not value and os.environ.get('CREDENTIALS_DIRECTORY'):
        value = (Path(os.environ['CREDENTIALS_DIRECTORY'])/'linear-api-key').read_text().strip()
    if not value:
        raise RuntimeError('Existing coordinator credential was not injected')
    return value


def verify_install(runtime):
    record = json.loads((runtime/'installation.json').read_text())
    if record['source_revision'] != PIN or importlib.metadata.version('stokowski') != '1.1.0':
        raise RuntimeError('Unreviewed Stokowski installation')
    import stokowski
    installed = Path(stokowski.__file__).parent
    for relative, expected in record['installed_source_sha256'].items():
        if hashlib.sha256((installed/relative).read_bytes()).hexdigest() != expected:
            raise RuntimeError('Installed Stokowski source drift')


def install_adapters(runtime, manifest, key):
    import stokowski.config as config
    import stokowski.linear as linear
    import stokowski.orchestrator as orchestration
    import stokowski.workspace as workspace_module

    async def reject_hook(*args, **kwargs):
        raise RuntimeError('Arbitrary shell hooks are disabled by OffMenu adapter')

    config.ProjectConfig.agent_env = lambda self: child_environment(os.environ)
    config.ServiceConfig.agent_env = lambda self: child_environment(os.environ)
    config.ProjectConfig.resolved_api_key = lambda self: key
    config.ServiceConfig.resolved_api_key = lambda self: key
    workspace_module.run_hook = reject_hook

    original_fetch = linear.LinearClient.fetch_candidate_issues

    async def selected_candidates(client, project_slug, states):
        if project_slug != SLUG:
            raise AdmissionError('Wrong Linear project')
        issues = await original_fetch(client, project_slug, states)
        return [i for i in issues if i.identifier in manifest['tasks']
                and i.id == manifest['tasks'][i.identifier]['issue_id']]

    linear.LinearClient.fetch_candidate_issues = selected_candidates

    async def ensure_workspace(root, identifier, hooks):
        if identifier not in manifest['tasks'] or root.resolve() != runtime/'workspaces':
            raise AdmissionError('Workspace outside selected manifest')
        path = root/identifier
        created = not path.exists()
        if created:
            root.mkdir(parents=True, exist_ok=True, mode=0o700)
            subprocess.run(['git', 'clone', '--shared', '--single-branch', '--branch',
                            manifest['branch'], str(SOURCE), str(path)], check=True,
                           capture_output=True, env=child_environment(os.environ))
        head = subprocess.check_output(['git', '-C', str(path), 'rev-parse', 'HEAD'], text=True).strip()
        if head != manifest['base_revision']:
            raise AdmissionError('Workspace HEAD differs from selected source')
        return workspace_module.WorkspaceResult(path, identifier, created)

    async def retain_workspace(*args, **kwargs):
        # No upstream rmtree: accepted output and uncertainty survive restarts.
        return None

    orchestration.ensure_workspace = ensure_workspace
    orchestration.remove_workspace = retain_workspace
    workspace_module.ensure_workspace = ensure_workspace
    workspace_module.remove_workspace = retain_workspace

    pending_control = set()
    original_start = orchestration.Orchestrator.start
    original_transition = orchestration.Orchestrator._safe_transition

    async def tracked_start(owner):
        owner._offmenu_loop = asyncio.current_task()
        try:
            return await original_start(owner)
        finally:
            owner._offmenu_loop = None

    async def tracked_transition(owner, *args, **kwargs):
        task = asyncio.current_task()
        pending_control.add(task)
        try:
            return await original_transition(owner, *args, **kwargs)
        finally:
            pending_control.discard(task)

    async def safe_stop(owner):
        owner._running = False
        if hasattr(owner, '_stop_event'):
            owner._stop_event.set()
        for timer in owner._retry_timers.values():
            timer.cancel()
        tasks = list(owner._tasks.values())
        for task in tasks:
            task.cancel()
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
        # Upstream transitions run in separate tasks after worker removal. They
        # must settle before their HTTP client closes; otherwise a successful
        # coding task can lose its durable tracker state during finite shutdown.
        if pending_control:
            await asyncio.wait_for(asyncio.gather(
                *(asyncio.shield(t) for t in list(pending_control))), timeout=30)
        loop_task = getattr(owner, '_offmenu_loop', None)
        if loop_task and loop_task is not asyncio.current_task():
            try:
                await asyncio.wait_for(asyncio.shield(loop_task), timeout=30)
            except asyncio.TimeoutError:
                loop_task.cancel()
                await asyncio.gather(loop_task, return_exceptions=True)
        if owner._linear:
            await owner._linear.close()

    async def safe_report(owner, issue, attempt, workspace_path, state_name):
        path = runtime/'attempts'/issue.identifier/'receipt.json'
        if not path.exists():
            return
        result = json.loads(path.read_text())
        safe = {k: result.get(k) for k in ('status','source_head','session_id',
                'child_tree_gone','scope_violations','output_sha256','accepted_delivery')}
        owner.ledger.record_stage(project='offmenu', workflow='bounded-adapter-proof',
                                  issue_id=issue.id, issue=issue.identifier,
                                  title=issue.title, state=state_name, run=1,
                                  status=attempt.status, report=None,
                                  tokens=attempt.total_tokens, cost_usd=0,
                                  tool_calls=0, tool_errors=0, artifacts=0,
                                  model=MODEL, duration_s=None)
        client = owner._ensure_linear_client()
        await client.post_comment(issue.id, '[OffMenu Stokowski bounded attempt]\n\n'
                                 + json.dumps(safe, sort_keys=True))

    orchestration.Orchestrator.stop = safe_stop
    orchestration.Orchestrator.start = tracked_start
    orchestration.Orchestrator._safe_transition = tracked_transition
    orchestration._offmenu_pending_control = pending_control
    orchestration.Orchestrator._publish_run_report = safe_report

    async def run_turn(runner_type, claude_cfg, hooks_cfg, prompt, workspace_path,
                       issue, attempt, on_event=None, on_pid=None, env=None):
        if runner_type != 'codex' or claude_cfg.model != MODEL:
            raise AdmissionError('Only the reviewed existing Codex session route is admitted')
        if any(vars(hooks_cfg).get(k) for k in ('before_run', 'after_run', 'on_stage_enter')):
            raise AdmissionError('Unenforced shell validation hook rejected')
        request = {'prompt': prompt, 'timeout_seconds': min(600, claude_cfg.turn_timeout_ms//1000)}
        request_path = runtime/'requests'/(issue.identifier+'.json')
        if request_path.exists():
            raise AdmissionError('Attempt already requested; reconcile before retry')
        request_path.parent.mkdir(exist_ok=True, mode=0o700)
        checkpoint(request_path, request)
        process = await asyncio.create_subprocess_exec(
            sys.executable, str(SOURCE/'tools/delivery/stokowski_worker.py'),
            '--runtime', str(runtime), '--issue', issue.identifier,
            env=child_environment(os.environ), stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE, start_new_session=True)
        if on_pid:
            on_pid(process.pid, True)
        attempt.turn_count += 1
        try:
            await process.communicate()
        except asyncio.CancelledError:
            # The worker handles TERM, reaps only its descendants and retains
            # its lease if termination cannot be proven. Never SIGKILL the
            # supervisor before it has a chance to reconcile.
            try:
                process.send_signal(signal.SIGTERM)
            except ProcessLookupError:
                pass
            await asyncio.wait_for(asyncio.shield(process.wait()), timeout=10)
            raise
        finally:
            if on_pid and process.returncode is not None:
                on_pid(process.pid, False)
        receipt_path = runtime/'attempts'/issue.identifier/'receipt.json'
        result = json.loads(receipt_path.read_text()) if receipt_path.exists() else {'status': 'uncertain'}
        attempt.status = 'succeeded' if result['status'] == 'succeeded' else 'failed'
        attempt.session_id = result.get('session_id')
        attempt.model = MODEL
        usage = result.get('usage', {})
        attempt.input_tokens = usage.get('input_tokens', 0)
        attempt.output_tokens = usage.get('output_tokens', 0)
        attempt.total_tokens = attempt.input_tokens+attempt.output_tokens
        attempt.error = None if attempt.status == 'succeeded' else result['status']
        attempt.result_text = ('Coding attempt ended. Independent behavior/output '
                               'acceptance remains required; no application acceptance asserted.')
        return attempt

    orchestration.run_turn = run_turn
    return orchestration


async def run(runtime, duration, dry_run=False):
    verify_install(runtime)
    manifest = load_manifest(runtime/'manifest.json')
    policy = json.loads((runtime/'capacity-policy.json').read_text())
    if policy != json.loads((SOURCE/'tools/delivery/capacity-policy.json').read_text()):
        raise AdmissionError('Runtime policy differs from reviewed source')
    key = credential()
    orchestration = install_adapters(runtime, manifest, key)
    from stokowski.config import parse_workflow_file, validate_config
    definition = parse_workflow_file(runtime/'workflow.yaml')
    projects = definition.config.projects
    if (validate_config(definition.config) or len(projects) != 1
        or projects[0].tracker.project_slug != SLUG
        or definition.config.agent.max_concurrent_agents != policy['symphony']['max_concurrent_agents']
        or definition.config.server.port is not None
        or any(s.runner != 'codex' for s in projects[0].all_states().values() if s.type == 'agent')
        or any(vars(projects[0].hooks).get(k) for k in ('after_create','before_run','after_run','before_remove','on_stage_enter'))
        or any(s.hooks is not None for s in projects[0].all_states().values())):
        raise AdmissionError('Workflow violates selected OffMenu contract')
    from stokowski.linear import LinearClient
    client = LinearClient(endpoint='https://api.linear.app/graphql', api_key=key)
    try:
        candidates = await client.fetch_candidate_issues(SLUG, projects[0].active_linear_states())
    finally:
        await client.close()
    if {i.id for i in candidates} != {t['issue_id'] for t in manifest['tasks'].values()}:
        raise AdmissionError('Selected issues are not exactly the ready candidates')
    checkpoint(runtime/'admission.json', dict(project_id=PROJECT, selected=[i.identifier for i in candidates],
               max_concurrent_agents=definition.config.agent.max_concurrent_agents,
               upstream_revision=PIN, dry_run=dry_run, credential_exported=False))
    if dry_run:
        print(json.dumps({'status':'ready','candidates':[i.identifier for i in candidates],
                          'coding_ceiling':8,'credential_exported':False}))
        return
    coordinator = orchestration.MultiOrchestrator(runtime/'workflow.yaml')
    service = asyncio.create_task(coordinator.start())
    deadline = time.monotonic()+duration
    try:
        while time.monotonic() < deadline:
            if service.done():
                service.result()
                break
            finished = all((runtime/'attempts'/i/'receipt.json').exists() for i in manifest['tasks'])
            if (finished and not orchestration._offmenu_pending_control
                and all(not o.running and not o._tasks for o in coordinator.orchestrators.values())):
                break
            if (runtime/'cancel.json').exists():
                break
            await asyncio.sleep(.5)
    finally:
        await coordinator.stop()
        await asyncio.gather(service, return_exceptions=True)
        checkpoint(runtime/'coordinator-finished.json', dict(stopped=True, at=time.time(),
                   accepted_delivery=False, project_id=PROJECT))


async def reconcile_metadata(runtime):
    """Reconcile the already-ended attempt's tracker state; never run coding."""
    verify_install(runtime)
    manifest = load_manifest(runtime/'manifest.json')
    from stokowski.linear import LinearClient
    client = LinearClient(endpoint='https://api.linear.app/graphql', api_key=credential())
    results = []
    try:
        for issue, task in manifest['tasks'].items():
            receipt = json.loads((runtime/'attempts'/issue/'receipt.json').read_text())
            if (receipt.get('issue') != issue or receipt.get('source_head') != manifest['base_revision']
                or receipt.get('status') != 'succeeded' or not receipt.get('child_tree_gone')):
                raise AdmissionError('No safely ended selected coding attempt to reconcile')
            data = await client._graphql('query($id: String!){ issue(id:$id){id project{id} state{name}}}',
                                         {'id':task['issue_id']})
            remote = data.get('issue') or {}
            if remote.get('project',{}).get('id') != PROJECT:
                raise AdmissionError('Wrong issue project during reconciliation')
            before = remote.get('state',{}).get('name')
            if before not in ('In Progress','In Review'):
                raise AdmissionError('Tracker state needs a distinct accepted transition')
            if before != 'In Review' and not await client.update_issue_state(task['issue_id'],'In Review'):
                raise RuntimeError('Tracker transition not confirmed; read back before retry')
            after = await client.fetch_issue_states_by_ids([task['issue_id']])
            if after.get(task['issue_id']) != 'In Review':
                raise RuntimeError('Tracker readback not confirmed')
            results.append({'issue':issue,'state':'In Review','coding_replayed':False})
        checkpoint(runtime/'metadata-reconciliation.json',{'results':results,'accepted_delivery':False})
        print(json.dumps({'status':'reconciled','results':results,'credential_exported':False}))
    finally:
        await client.close()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--runtime', required=True, type=Path)
    parser.add_argument('--duration', type=int, default=240)
    parser.add_argument('--dry-run', action='store_true')
    parser.add_argument('--reconcile-metadata', action='store_true')
    args = parser.parse_args()
    if not 1 <= args.duration <= 900:
        raise SystemExit('Finite coordinator duration must be 1..900 seconds')
    runtime = args.runtime.resolve()
    with (runtime/'coordinator.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX|fcntl.LOCK_NB)
        try:
            if args.reconcile_metadata:
                asyncio.run(reconcile_metadata(runtime))
            else:
                asyncio.run(run(runtime, args.duration, args.dry_run))
        except (OSError, RuntimeError, ValueError, AdmissionError) as error:
            print(json.dumps({'status':'blocked','error_type':type(error).__name__,
                              'credential_exported':False}))
            raise SystemExit(2)
