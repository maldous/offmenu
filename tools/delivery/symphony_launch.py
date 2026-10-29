"""Own OffMenu native Symphony launcher: explicit preflight/prepare/run.

No CIX launcher, credential copy, persistent service, push, merge or Actions.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shlex
import signal
import subprocess
import sys
import tempfile
import time
import urllib.request

if __package__:
    from .symphony_protocol import BINARY, probe
    from .symphony_codex import isolated_codex_environment
    from .symphony_tasks import load_manifest, manifest_digest
    from .symphony_capacity import Pool
    from .symphony_workspace import workspace_processes
    from .windmill_runner import cleanup as cleanup_owned_tree
else:
    from symphony_protocol import BINARY, probe
    from symphony_codex import isolated_codex_environment
    from symphony_tasks import load_manifest, manifest_digest
    from symphony_capacity import Pool
    from symphony_workspace import workspace_processes
    from windmill_runner import cleanup as cleanup_owned_tree

BUNDLE = Path('/home/user/.local/share/cix/symphony/0c01ff0975da80ded7044a5ad76a44ac87053670-d215a99ac5a44941')
BUNDLE_SHA = 'd215a99ac5a4494181389f9fe5b2cca5de9895003d2ce4977904590d416478b4'
SOURCE = Path(__file__).resolve().parents[2]
BRANCH = 'feature/langgraph-delivery-standardization'
PROJECT_ID = 'ce60c1ab-a732-4a71-8471-14c9dc393886'
NATIVE_SLUG_ID = 'ccd080f4f6f0'
ISSUE_ID = '37f82d6a-fb4a-470e-8bde-82e4796dd656'
LABEL = 'offmenu-uif-90'


def git(*args):
    return subprocess.check_output(['git', '-C', str(SOURCE), *args], text=True).strip()


def prerequisite():
    archive = BUNDLE/'libexec/symphony'
    return {'source_branch': git('branch', '--show-current'), 'source_head': git('rev-parse', 'HEAD'), 'tracked_source_clean': not bool(git('status', '--porcelain', '--untracked-files=no')), 'native_bundle_hash_matches': archive.is_file() and hashlib.sha256(archive.read_bytes()).hexdigest() == BUNDLE_SHA, 'vendor_codex_exists': Path(BINARY).is_file(), 'offmenu_credential_present': bool(os.environ.get('OFFMENU_LINEAR_API_KEY')), 'systemd_credential_directory_present': bool(os.environ.get('CREDENTIALS_DIRECTORY')), 'project_id': PROJECT_ID, 'native_project_slug_id': NATIVE_SLUG_ID, 'issue_id': ISSUE_ID, 'required_label': LABEL}


def credential(environment):
    if environment.get('OFFMENU_LINEAR_API_KEY'):
        return
    directory = environment.get('CREDENTIALS_DIRECTORY')
    if not directory:
        raise RuntimeError('No selected runtime tracker credential route')
    # The service manager injects an already authorized credential. Never read
    # /etc secret sources directly, persist it, log it, or create a replacement key.
    value = (Path(directory)/'linear-api-key').read_text().strip()
    if not value:
        raise RuntimeError('Injected tracker credential is empty')
    environment['OFFMENU_LINEAR_API_KEY'] = value


def tracker_preflight(environment):
    credential(environment)
    query = """query OffMenuAdmission($id: String!) {
      issue(id: $id) { id identifier project { id slugId } team { id }
        state { name } labels { nodes { name } } }
      issues(filter: {project: {id: {eq: "ce60c1ab-a732-4a71-8471-14c9dc393886"}}, state: {name: {eq: "In Progress"}}, labels: {some: {name: {eq: "offmenu-uif-90"}}}}, first: 2) { nodes { id } }
    }"""
    request = urllib.request.Request('https://api.linear.app/graphql', data=json.dumps({'query': query, 'variables': {'id': ISSUE_ID}}).encode(), headers={'Content-Type': 'application/json', 'Authorization': environment['OFFMENU_LINEAR_API_KEY']}, method='POST')
    with urllib.request.urlopen(request, timeout=25) as response:
        result = json.load(response)
    if result.get('errors'):
        raise RuntimeError('Tracker admission query rejected')
    issue = result.get('data', {}).get('issue') or {}
    candidates = result.get('data', {}).get('issues', {}).get('nodes', [])
    if (issue.get('id') != ISSUE_ID or issue.get('identifier') != 'UIF-90'
        or issue.get('project', {}).get('id') != PROJECT_ID
        or issue.get('project', {}).get('slugId') != NATIVE_SLUG_ID
        or issue.get('team', {}).get('id') != '53f584e7-70a1-4b1e-b982-b815210e47d4'
        or issue.get('state', {}).get('name') != 'In Progress'
        or LABEL not in [label.get('name') for label in issue.get('labels', {}).get('nodes', [])]
        or [entry.get('id') for entry in candidates] != [ISSUE_ID]):
        raise RuntimeError('Tracker admission does not select exactly UIF-90')
    return {'tracker_scope_verified': True, 'admitted_issue': 'UIF-90', 'candidate_count': 1}


def provider_proof(model, ceiling):
    """Existing session authentication/model metadata, never a coding turn."""
    login = subprocess.run([BINARY, 'login', 'status'], capture_output=True, text=True, timeout=20)
    facts = probe()
    available = (login.returncode == 0 and 'Logged in using ChatGPT' in login.stdout+login.stderr
                 and model in [m['id'] for m in facts.get('models', [])])
    return {'route': 'codex-chatgpt', 'available': available, 'checked_at': time.time(),
            'session_ceiling': ceiling, 'requested_model': model,
            'quota_metadata_available': bool(facts.get('quota_response_present')),
            'vendor_parallel_entitlement_claimed': False}


def default_manifest(head):
    policy = json.loads((SOURCE/'tools/delivery/capacity-policy.json').read_text())
    return {'version': 1, 'branch': BRANCH, 'base_revision': head, 'project_id': PROJECT_ID,
            'label': LABEL, 'tasks': {'UIF-90': {'issue_id': ISSUE_ID,
            'owner': 'offmenu-integration-writer', 'purpose': 'Reviewed CLI delivery regressions',
            'allowed_paths': ['tests/delivery/test_cli.py', 'src/offmenu/delivery/__main__.py'],
            'acceptance': ['Run the selected delivery tests and retain actual outcomes'],
            'resources': policy['symphony']['default_resources'], 'attempt_limit': 2}}}


def tracker_manifest_preflight(environment, manifest):
    credential(environment)
    query = """query OffMenuCapacityAdmission($project: ID!, $label: String!) {
      issues(filter: {project: {id: {eq: $project}}, state: {name: {eq: "In Progress"}},
        labels: {some: {name: {eq: $label}}}}, first: 257) {
        nodes {id identifier team {id} project {id slugId}} pageInfo {hasNextPage} }
    }"""
    request = urllib.request.Request('https://api.linear.app/graphql', data=json.dumps({'query': query,
        'variables': {'project': PROJECT_ID, 'label': manifest['label']}}).encode(),
        headers={'Content-Type': 'application/json', 'Authorization': environment['OFFMENU_LINEAR_API_KEY']}, method='POST')
    with urllib.request.urlopen(request, timeout=25) as response: result = json.load(response)
    page = result.get('data', {}).get('issues') or {}
    nodes = page.get('nodes', [])
    expected = {name: task['issue_id'] for name, task in manifest['tasks'].items()}
    if (result.get('errors') or page.get('pageInfo', {}).get('hasNextPage')
        or {i['identifier']: i['id'] for i in nodes} != expected
        or any(i.get('team', {}).get('id') != '53f584e7-70a1-4b1e-b982-b815210e47d4'
               or i.get('project', {}).get('id') != PROJECT_ID
               or i.get('project', {}).get('slugId') != NATIVE_SLUG_ID for i in nodes)):
        raise RuntimeError('Tracker candidates differ from the reviewed manifest')
    return {'tracker_scope_verified': True, 'admitted_issues': sorted(expected), 'candidate_count': len(nodes)}


def prepare(runtime, model, manifest_path=None):
    facts = prerequisite()
    if facts['source_branch'] != BRANCH or not facts['tracked_source_clean'] or not facts['native_bundle_hash_matches'] or not facts['vendor_codex_exists']:
        raise RuntimeError('Source or native executable prerequisite failed')
    policy = json.loads((SOURCE/'tools/delivery/capacity-policy.json').read_text())
    runtime.mkdir(parents=True, exist_ok=True, mode=0o700)
    if (runtime/'admission.json').exists():
        raise RuntimeError('Runtime already prepared; inspect/reconcile it instead of replacing immutable inputs')
    manifest = load_manifest(manifest_path, expected_head=facts['source_head']) if manifest_path else default_manifest(facts['source_head'])
    task_file = runtime/'tasks.json'
    task_file.write_text(json.dumps(manifest, indent=2)+'\n'); task_file.chmod(0o600)
    load_manifest(task_file, expected_head=facts['source_head'])
    (runtime/'capacity-policy.json').write_text(json.dumps(policy, indent=2)+'\n')
    hook = SOURCE/'tools/delivery/symphony_workspace.py'
    command = lambda action: shlex.join([sys.executable, str(hook), action, '--source', str(SOURCE),
        '--head', facts['source_head'], '--manifest', str(task_file), '--runtime', str(runtime)])
    config = {'tracker': {'kind': 'linear', 'provider': {'project_slug': NATIVE_SLUG_ID,
        'api_key': '$OFFMENU_LINEAR_API_KEY'}, 'required_labels': [manifest['label']],
        'active_states': ['In Progress'], 'terminal_states': ['Done', 'Canceled', 'Duplicate']},
        'polling': {'interval_ms': 60000}, 'workspace': {'root': str(runtime/'workspaces')},
        'hooks': {'after_create': command('create'), 'before_run': command('admit'),
                  'after_run': command('finish'), 'timeout_ms': 60000},
        'agent': {'max_concurrent_agents': policy['symphony']['max_concurrent_agents'],
                  'max_turns': policy['symphony']['max_turns'], 'max_retry_backoff_ms': 60000},
        'codex': {'command': shlex.join([sys.executable, str(SOURCE/'tools/delivery/symphony_executor.py'),
            '--runtime', str(runtime), '--model', model]), 'approval_policy': 'never',
            'thread_sandbox': 'workspace-write', 'turn_sandbox_policy': {'type': 'workspaceWrite', 'networkAccess': False},
            'turn_timeout_ms': 600000, 'stall_timeout_ms': 120000, 'read_timeout_ms': 30000}}
    prompt = (SOURCE/'tools/delivery/symphony-workflow.md').read_text().split('---', 2)[2]
    prompt = prompt.replace('This template is disabled. Do not start a session from it.',
        'This finite runtime selects only the reviewed manifest issues. Read '+str(runtime)+
        '/{{ issue.identifier }}-task.json for your owner, exact allowed paths, purpose and acceptance. '+
        'Other admitted sessions have disjoint logical write ownership in private clones. '+
        'Do not commit, push, merge or deploy. Leave actual source/test evidence for the integration writer.')
    workflow = runtime/'WORKFLOW.md'; workflow.write_text('---\n'+json.dumps(config,indent=2)+'\n---\n'+prompt)
    receipt = {**facts, 'workflow': str(workflow), 'model_requested': model, 'runtime': str(runtime),
        'native_service_started': False, 'manifest_sha256': manifest_digest(manifest),
        'admitted_issue_names': sorted(manifest['tasks']),
        'max_concurrent_agents': policy['symphony']['max_concurrent_agents'],
        'capacity_policy_sha256': hashlib.sha256((runtime/'capacity-policy.json').read_bytes()).hexdigest()}
    (runtime/'admission.json').write_text(json.dumps(receipt,indent=2)+'\n')
    return workflow, receipt


def native_outcome(runtime, issue_ids=None):
    logs = list((Path(runtime)/'logs').rglob('symphony.log*'))
    text = '\n'.join(path.read_text(errors='replace') for path in logs if path.is_file())
    issue_ids = issue_ids or [ISSUE_ID]
    if any('Agent run failed for issue_id='+issue in text for issue in issue_ids):
        return 'failed'
    if all('Completed agent run for issue_id='+issue in text for issue in issue_ids):
        return 'normal_turn_completed'
    return 'unknown'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['preflight','prepare','run','cancel'])
    parser.add_argument('--runtime', type=Path)
    parser.add_argument('--model')
    parser.add_argument('--manifest', type=Path)
    parser.add_argument('--probe', action='store_true')
    parser.add_argument('--inference-authorized', action='store_true', help='Record already established authority for this finite coding run')
    parser.add_argument('--duration-seconds', type=int, default=180)
    args = parser.parse_args()
    if args.action == 'preflight':
        result = prerequisite()
        if args.probe:
            result['native_protocol'] = probe()
        print(json.dumps(result))
        return 0
    if args.action == 'cancel':
        if not args.runtime: parser.error('cancel requires --runtime')
        runtime = args.runtime.resolve()
        if not (runtime/'admission.json').exists(): parser.error('Unknown runtime')
        (runtime/'cancel.json').write_text(json.dumps({'requested_at': time.time()})+'\n')
        policy = json.loads((runtime/'capacity-policy.json').read_text())
        pool = Pool(policy['symphony']['pool_path'], policy)
        for row in pool.status():
            if row['id'].startswith(runtime.name+'-') and row['status']=='running': pool.cancel(row['id'])
        print(json.dumps({'status':'cancellation_requested','runtime':str(runtime),'process_tree_gone':False}))
        return 0
    if not args.runtime or not args.model:
        parser.error('prepare/run require --runtime and --model')
    runtime = args.runtime.resolve()
    if runtime == SOURCE or SOURCE in runtime.parents:
        parser.error('runtime must be outside the product checkout')
    workflow, receipt = prepare(runtime, args.model, args.manifest)
    subprocess.run([sys.executable, str(SOURCE/'tools/delivery/symphony_validate.py'), '--bundle', str(BUNDLE), '--workflow', str(workflow)], check=True)
    if args.action == 'prepare':
        print(json.dumps(receipt))
        return 0
    if not args.inference_authorized:
        parser.error('run requires the established inference authority flag')
    if not 1 <= args.duration_seconds <= 1800:
        parser.error('finite run duration must be between 1 and 1800 seconds')
    environment = os.environ.copy()
    manifest = load_manifest(runtime/'tasks.json')
    policy = json.loads((runtime/'capacity-policy.json').read_text())
    receipt.update(tracker_manifest_preflight(environment, manifest))
    proof = provider_proof(args.model, policy['symphony']['provider_session_ceiling'])
    if not proof['available']: raise RuntimeError('Existing Codex session route/model unavailable')
    (runtime/'provider-proof.json').write_text(json.dumps(proof)+'\n')
    environment['ERL_ROOTDIR'] = str(BUNDLE/'otp')
    environment['ERL_FLAGS'] = '+S 2:2'
    environment['OFFMENU_SYMPHONY_PROJECT_ID'] = PROJECT_ID
    environment['OFFMENU_SYMPHONY_ISSUE_IDS'] = json.dumps([task['issue_id'] for task in manifest['tasks'].values()])
    command = [str(BUNDLE/'otp/bin/escript'), str(BUNDLE/'libexec/symphony'), '--i-understand-that-this-will-be-running-without-the-usual-guardrails', '--logs-root', str(runtime/'logs'), str(workflow)]
    finished = [runtime/'workspaces'/(name.lower()+'-run-finished.json') for name in manifest['tasks']]
    if any(p.exists() for p in finished):
        raise RuntimeError('Runtime already has a completed attempt; use its receipt')
    with isolated_codex_environment(environment, runtime) as environment:
        with (runtime/'process.log').open('a') as logs:
            if __import__('ctypes').CDLL(None,use_errno=True).prctl(36,1,0,0,0) != 0:
                raise RuntimeError('Owned process subreaper unavailable')
            process = subprocess.Popen(command, env=environment, stdout=logs, stderr=subprocess.STDOUT, start_new_session=True)
            timed_out = False
            attempt_finished = False
            try:
                deadline = time.monotonic()+args.duration_seconds
                refreshed = time.monotonic()
                while process.poll() is None and time.monotonic()<deadline:
                    if (runtime/'cancel.json').exists(): break
                    if time.monotonic()-refreshed > 60:
                        proof = provider_proof(args.model, policy['symphony']['provider_session_ceiling'])
                        (runtime/'provider-proof.json').write_text(json.dumps(proof)+'\n'); refreshed = time.monotonic()
                    if all(p.exists() for p in finished):
                        attempt_finished = True
                        break
                    time.sleep(0.5)
                if process.poll() is None:
                    raise subprocess.TimeoutExpired(command, args.duration_seconds)
                code = process.returncode
            except (subprocess.TimeoutExpired, KeyboardInterrupt):
                timed_out = not attempt_finished
                os.killpg(process.pid, signal.SIGTERM)
                try:
                    code = process.wait(timeout=15)
                except subprocess.TimeoutExpired:
                    os.killpg(process.pid, signal.SIGKILL)
                    code = process.wait(timeout=10)
            tree_gone = cleanup_owned_tree(process)
            receipt['owned_process_tree_gone'] = tree_gone
            pool = Pool(policy['symphony']['pool_path'], policy)
            unresolved = []
            for row in pool.status():
                if not row['id'].startswith(runtime.name+'-') or row['status'] in ('finished','failed'): continue
                name = row['id'][len(runtime.name)+1:]
                if tree_gone and not workspace_processes(runtime/'workspaces'/name):
                    pool.finish(row['id'], True, 'cancelled' if (runtime/'cancel.json').exists() else 'failed')
                else: unresolved.append(name)
            receipt['unresolved_resource_leases'] = unresolved
            outcome = native_outcome(runtime, [task['issue_id'] for task in manifest['tasks'].values()])
            receipt.update({'native_outcome': outcome, 'native_service_started': True, 'exit_code': code, 'finite_deadline_or_interrupt': timed_out, 'coding_attempt_ended': attempt_finished, 'accepted_delivery': False})
            (runtime/'process-receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
            print(json.dumps(receipt))
    return 0 if outcome == 'normal_turn_completed' and not timed_out else 2


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except (RuntimeError, OSError, subprocess.SubprocessError) as error:
        print(json.dumps({'error_type': type(error).__name__, 'message': 'OffMenu native launcher prerequisite/execution failed; reconcile runtime receipt', 'accepted_delivery': False}))
        raise SystemExit(2)
