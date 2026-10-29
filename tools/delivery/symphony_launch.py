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
else:
    from symphony_protocol import BINARY, probe
    from symphony_codex import isolated_codex_environment

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


def prepare(runtime, model):
    facts = prerequisite()
    if facts['source_branch'] != BRANCH or not facts['tracked_source_clean'] or not facts['native_bundle_hash_matches'] or not facts['vendor_codex_exists']:
        raise RuntimeError('Source or native executable prerequisite failed')
    runtime.mkdir(parents=True, exist_ok=True, mode=0o700)
    hook = SOURCE/'tools/delivery/symphony_workspace.py'
    command = lambda action: shlex.join([sys.executable, str(hook), action, '--source', str(SOURCE), '--head', facts['source_head']])
    config = {'tracker': {'kind': 'linear', 'provider': {'project_slug': NATIVE_SLUG_ID, 'api_key': '$OFFMENU_LINEAR_API_KEY'}, 'required_labels': [LABEL], 'active_states': ['In Progress'], 'terminal_states': ['Done', 'Canceled', 'Duplicate']}, 'polling': {'interval_ms': 60000}, 'workspace': {'root': str(runtime/'workspaces')}, 'hooks': {'after_create': command('create'), 'before_run': command('admit'), 'after_run': command('finish'), 'timeout_ms': 60000}, 'agent': {'max_concurrent_agents': 1, 'max_turns': 1, 'max_retry_backoff_ms': 60000}, 'codex': {'command': shlex.join([BINARY, '-c', 'model='+json.dumps(model), '-c', 'model_reasoning_effort="medium"', 'app-server']), 'approval_policy': 'never', 'thread_sandbox': 'workspace-write', 'turn_sandbox_policy': {'type': 'workspaceWrite', 'networkAccess': False}, 'turn_timeout_ms': 600000, 'stall_timeout_ms': 120000, 'read_timeout_ms': 30000}}
    template = (SOURCE/'tools/delivery/symphony-workflow.md').read_text().split('---',2)[2]
    template = template.replace('This template is disabled. Do not start a session from it. Activation requires a\nseparately reviewed configuration selecting the OffMenu Linear project, accepted\nissue states/labels, dedicated workspace and existing eligible execution model.\nDo not alter this file to bypass a missing admission or permission decision.', 'This generated runtime configuration admits only UIF-90, the selected branch and\none coding session at a time. Work only its existing acceptance criteria.\nDo not push, merge, deploy, dispatch Actions, call external data sources or\nchange tracker status. Do not commit; leave concrete diff and test evidence for\nthe integration writer. Only implement meaningful missing CLI integration tests in tests/delivery/test_cli.py.\nAn optional minimal src/offmenu/delivery/__main__.py fix is allowed only when proven\nnecessary by those tests. Use the canonical project interpreter: /home/user/src/\noffmenu/.venv-delivery/bin/python (join this wrapped path). Run from this clone:\nPYTHONPATH=src /home/user/src/offmenu/.venv-delivery/bin/python -m unittest discover\n-s tests/delivery -v (join the wrapped command). Do not weaken tests or policy.')
    workflow = runtime/'WORKFLOW.md'
    workflow.write_text('---\n'+json.dumps(config,indent=2)+'\n---\n'+template)
    receipt = {**facts, 'workflow': str(workflow), 'model_requested': model, 'runtime': str(runtime), 'attempt_limit': 2, 'native_service_started': False}
    (runtime/'preflight.json').write_text(json.dumps(receipt,indent=2)+'\n')
    return workflow, receipt


def native_outcome(runtime):
    logs = list((Path(runtime)/'logs').rglob('symphony.log*'))
    text = '\n'.join(path.read_text(errors='replace') for path in logs if path.is_file())
    if 'Agent run failed for issue_id='+ISSUE_ID in text:
        return 'failed'
    if 'Completed agent run for issue_id='+ISSUE_ID in text:
        return 'normal_turn_completed'
    return 'unknown'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['preflight','prepare','run'])
    parser.add_argument('--runtime', type=Path)
    parser.add_argument('--model')
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
    if not args.runtime or not args.model:
        parser.error('prepare/run require --runtime and --model')
    runtime = args.runtime.resolve()
    if runtime == SOURCE or SOURCE in runtime.parents:
        parser.error('runtime must be outside the product checkout')
    workflow, receipt = prepare(runtime, args.model)
    subprocess.run([sys.executable, str(SOURCE/'tools/delivery/symphony_validate.py'), '--bundle', str(BUNDLE), '--workflow', str(workflow)], check=True)
    if args.action == 'prepare':
        print(json.dumps(receipt))
        return 0
    if not args.inference_authorized:
        parser.error('run requires the established inference authority flag')
    if not 1 <= args.duration_seconds <= 1800:
        parser.error('finite run duration must be between 1 and 1800 seconds')
    environment = os.environ.copy()
    receipt.update(tracker_preflight(environment))
    environment['ERL_ROOTDIR'] = str(BUNDLE/'otp')
    environment['ERL_FLAGS'] = '+S 2:2'
    environment['OFFMENU_SYMPHONY_PROJECT_ID'] = PROJECT_ID
    environment['OFFMENU_SYMPHONY_ISSUE_ID'] = ISSUE_ID
    command = [str(BUNDLE/'otp/bin/escript'), str(BUNDLE/'libexec/symphony'), '--i-understand-that-this-will-be-running-without-the-usual-guardrails', '--logs-root', str(runtime/'logs'), str(workflow)]
    finished = runtime/'workspaces/uif-90-run-finished.json'
    if finished.exists():
        raise RuntimeError('Runtime already has a completed attempt; use its receipt')
    with isolated_codex_environment(environment, runtime) as environment:
        with (runtime/'process.log').open('a') as logs:
            process = subprocess.Popen(command, env=environment, stdout=logs, stderr=subprocess.STDOUT, start_new_session=True)
            timed_out = False
            attempt_finished = False
            try:
                deadline = time.monotonic()+args.duration_seconds
                while process.poll() is None and time.monotonic()<deadline:
                    if finished.exists():
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
            outcome = native_outcome(runtime)
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
