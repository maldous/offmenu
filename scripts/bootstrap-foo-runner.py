#!/usr/bin/env python3
"""One user-operated setup batch. Without --apply, only diagnostics run."""
from __future__ import annotations
import argparse
import contextlib
import importlib.util
import io
import json
import os
from pathlib import Path
import pwd
import re
import shutil
import subprocess
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]
def module(name, filename):
    spec = importlib.util.spec_from_file_location(name, ROOT / 'scripts' / filename)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result
host = module('foo_host_setup', 'runner_host_setup.py')
batch = module('foo_setup_batch', 'check-foo-setup.py')
SOURCE = Path('/srv/offmenu-bootstrap-input')
HELPER = '/usr/local/lib/offmenu-runner/runner_host_setup.py'
WORKFLOW = '.github/workflows/foo-runner.yml'
AGREEMENT = 'https://github.com/customer-terms'

class Blocked(Exception):
    pass

class CommandFailed(Exception):
    def __init__(self, code):
        self.code = code

def blocked(code):
    raise Blocked(code)

def runner_command(*args):
    return ['sudo', '-n', '-u', host.RUNNER_USER, 'env', '-i',
            'HOME=' + str(host.RUNNER_HOME), 'USER=' + host.RUNNER_USER,
            'LOGNAME=' + host.RUNNER_USER, 'PATH=/usr/bin:/bin',
            'LANG=C.UTF-8', 'PYTHONDONTWRITEBYTECODE=1', 'python3', '-B', *args]

def tty_command(command, log_dir, timeout):
    # Original terminal only. In particular, config.sh token input/output is
    # never piped, captured, copied, or placed in any diagnostic file.
    if not sys.stdin.isatty() or not sys.stdout.isatty():
        blocked('interactive-terminal-required')
    result = subprocess.run(command, env=batch.environment(log_dir), timeout=timeout)
    if result.returncode:
        raise CommandFailed(result.returncode)
    return {'exitCode': result.returncode}

def captured(name, command, log_dir, timeout=240):
    result = batch.run_step(name, command, log_dir, timeout=timeout, preserve_session=True)
    if result['status'] != 'passed':
        return result
    return result

def gh_json(endpoint, query, log_dir):
    gh = shutil.which('gh')
    if not gh:
        blocked('existing-gh-cli-required')
    # GET only. The fixed jq filters bound returned metadata; no logs or secrets.
    result = subprocess.run([gh, 'api', '--hostname', 'github.com', '--method', 'GET',
                             endpoint, '--jq', query], env=batch.environment(log_dir, for_github=True),
                            stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, timeout=25)
    if result.returncode or len(result.stdout) > 32768:
        blocked('github-read-failed')
    try:
        return json.loads(result.stdout)
    except (ValueError, UnicodeError):
        blocked('github-response-invalid')

def check_request(args, log_dir):
    if not args.expected_head_sha or not args.expected_job_id:
        blocked('queued-job-identity-required')
    # Check immutable manifest content and the exact workflow run, not latest.
    import base64
    value = gh_json(f'repos/{host.REPO}/contents/.github/offmenu-runner/request.json?ref={args.expected_head_sha}',
                    '{encoding,content}', log_dir)
    if not isinstance(value, dict) or value.get('encoding') != 'base64' or not isinstance(value.get('content'), str):
        blocked('queued-request-invalid')
    try:
        request = json.loads(base64.b64decode(value['content'], validate=False))
    except (ValueError, TypeError):
        blocked('queued-request-invalid')
    if request != {'schemaVersion': 1, 'jobId': args.expected_job_id, 'profile': 'smoke'}:
        blocked('queued-request-identity-mismatch')
    runs = gh_json(f'repos/{host.REPO}/actions/workflows/foo-runner.yml/runs?head_sha={args.expected_head_sha}&per_page=20',
                   '[.workflow_runs[] | {id,head_sha,head_branch,event,path,run_attempt}]', log_dir)
    if not isinstance(runs, list):
        blocked('queued-run-response-invalid')
    matches = [r for r in runs if isinstance(r, dict) and r.get('head_sha') == args.expected_head_sha
               and r.get('head_branch') == 'offmenu-runner-jobs' and r.get('event') == 'push'
               and r.get('path') == WORKFLOW and type(r.get('id')) is int
               and (args.expected_run_id is None or r['id'] == args.expected_run_id)]
    if len(matches) != 1:
        blocked('queued-run-missing-or-ambiguous')
    args.expected_run_id = matches[0]['id']
    return {'runId': args.expected_run_id, 'requestIdentityVerified': True}

REGISTRATION_DIAGNOSTIC_KEYS = (
    'filePresent', 'regularFile', 'boundedSize', 'utf8Bom', 'jsonObject',
    'gitHubUrlPresent', 'gitHubUrlIsString', 'repositoryMatches',
    'agentNamePresent', 'agentNameIsString', 'runnerNameMatches',
    'workFolderPresent', 'workFolderIsString', 'workFolderMatches',
    'agentIdPresent', 'agentIdIsPositiveInteger',
)

# Official runner v2.337 IOUtil.SaveObject uses Encoding.UTF8 (with BOM).
# This program runs only as the dedicated user. It reads no credential files
# and emits only booleans plus the numeric ID of a fully matched registration.
REGISTRATION_PROBE_CODE = """import json,os,pathlib,stat,sys
p=pathlib.Path('/srv/offmenu-runner/actions-runner/.runner')
d={}
def finish(registered, valid=False, runner_id=None):
    result={'registered':registered,'identityValid':valid,'diagnostics':d}
    if valid: result['runnerId']=runner_id
    print(json.dumps(result))
    sys.exit(0)
try:
    fd=os.open(p,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK)
except FileNotFoundError:
    d['filePresent']=p.is_symlink()
    finish(p.is_symlink())
except OSError:
    d['filePresent']=True
    finish(True)
d['filePresent']=True
with os.fdopen(fd,'rb') as f:
    info=os.fstat(f.fileno())
    d['regularFile']=stat.S_ISREG(info.st_mode)
    d['boundedSize']=0 < info.st_size <= 65536
    if not d['regularFile'] or not d['boundedSize']: finish(True)
    raw=f.read(65537)
if len(raw)>65536: finish(True)
d['utf8Bom']=raw.startswith(bytes((239,187,191)))
try:
    v=json.loads(raw.decode('utf-8-sig'))
except (ValueError,UnicodeError):
    d['jsonObject']=False
    finish(True)
d['jsonObject']=isinstance(v,dict)
if not d['jsonObject']: finish(True)
for key in ('gitHubUrl','agentName','workFolder','agentId'):
    d[key+'Present']=key in v
for key in ('gitHubUrl','agentName','workFolder'):
    d[key+'IsString']=isinstance(v.get(key),str)
d['repositoryMatches']=d['gitHubUrlIsString'] and v['gitHubUrl'].rstrip('/').lower()=='https://github.com/maldous/offmenu'
d['runnerNameMatches']=v.get('agentName')=='foo-offmenu'
d['workFolderMatches']=v.get('workFolder')=='_work'
d['agentIdIsPositiveInteger']=type(v.get('agentId')) is int and 0 < v['agentId'] < 2**64
valid=all(d[key] for key in ('repositoryMatches','runnerNameMatches','workFolderMatches','agentIdIsPositiveInteger'))
finish(True,valid,v.get('agentId'))
"""

class RegistrationProbeError(Blocked):
    def __init__(self, diagnostics, exit_code):
        super().__init__('existing-registration-identity-invalid')
        self.diagnostics = diagnostics
        self.exit_code = exit_code

def registration_probe(log_dir):
    name = 'registration-identity-probe'
    # Unique files preserve private local evidence, containing only the safe
    # program output. No .runner values or credential bytes are logged.
    probe_dir = Path(tempfile.mkdtemp(prefix='probe-', dir=log_dir))
    result = captured(name, runner_command('-c', REGISTRATION_PROBE_CODE), probe_dir)
    diagnostics = {}
    try:
        value = json.loads((probe_dir / (name + '.stdout')).read_bytes())
        if not isinstance(value, dict):
            raise ValueError()
        raw = value.get('diagnostics', {})
        diagnostics = {key: raw[key] for key in REGISTRATION_DIAGNOSTIC_KEYS
                       if isinstance(raw, dict) and type(raw.get(key)) is bool}
    except (ValueError, OSError, TypeError):
        raise RegistrationProbeError(diagnostics, result.get('exitCode'))
    if result['status'] != 'passed' or type(value.get('registered')) is not bool:
        raise RegistrationProbeError(diagnostics, result.get('exitCode'))
    if value['registered']:
        expected = ('repositoryMatches', 'runnerNameMatches', 'workFolderMatches', 'agentIdIsPositiveInteger')
        if value.get('identityValid') is not True or not all(diagnostics.get(k) is True for k in expected) or type(value.get('runnerId')) is not int or not 0 < value['runnerId'] < 2**64:
            raise RegistrationProbeError(diagnostics, result.get('exitCode'))
        return {'registered': True, 'runnerId': value['runnerId'], 'registrationDiagnostics': diagnostics}
    if diagnostics.get('filePresent') is not False:
        raise RegistrationProbeError(diagnostics, result.get('exitCode'))
    return {'registered': False, 'registrationDiagnostics': diagnostics}

def validate_source():
    host.validate_privileged_destination(SOURCE, directory=True, mode=0o755)
    if SOURCE.exists() and any(SOURCE.iterdir()):
        blocked('bootstrap-input-must-remain-empty')

def prepare_source(log_dir):
    validate_source()
    if SOURCE.exists():
        return {'reusedExisting': True, 'bootstrapSourceEmpty': True}
    return captured('create-bootstrap-input', ['sudo', '-n', 'install', '-d', '-o', 'root', '-g', 'root', '-m', '0755', str(SOURCE)], log_dir)

def apply_plan(log_dir):
    validate_source()
    output = io.StringIO()
    with contextlib.redirect_stdout(output):
        host.admin_plan(str(SOURCE))
    # Only reviewed helper-generated commands are executed; no user shell text.
    plan = output.getvalue().replace('sudo ', 'sudo -n ')
    plan_path = log_dir / 'administrative-plan.sh'
    plan_path.write_text(plan)
    os.chmod(plan_path, 0o600)
    return captured('apply-administrative-plan', ['bash', str(plan_path)], log_dir)

def verify_service(log_dir):
    # Installation/token entry can outlast the sudo timestamp. Renew through
    # the original terminal if necessary; never log a sudo password prompt.
    tty_command(['sudo', '-v'], log_dir, 300)
    check = captured('verify-systemd-unit', ['sudo', '-n', 'systemd-analyze', 'verify', '/etc/systemd/system/' + host.SERVICE], log_dir)
    if check['status'] != 'passed':
        return check
    command = ['systemctl', 'show', host.SERVICE, '--property=User,Group,NoNewPrivileges,ProtectSystem,ProtectHome,PrivateTmp,PrivateDevices,CapabilityBoundingSet,AmbientCapabilities,BindReadOnlyPaths,BindPaths,ReadWritePaths,FragmentPath,DropInPaths']
    result = captured('verify-systemd-properties', command, log_dir)
    if result['status'] != 'passed':
        return result
    values = dict(line.split('=', 1) for line in (log_dir / 'verify-systemd-properties.stdout').read_text().splitlines() if '=' in line)
    required = {'User': host.RUNNER_USER, 'Group': host.RUNNER_USER, 'NoNewPrivileges': 'yes',
                'ProtectSystem': 'strict', 'ProtectHome': 'tmpfs', 'PrivateTmp': 'yes', 'PrivateDevices': 'yes',
                'CapabilityBoundingSet': '', 'AmbientCapabilities': '', 'DropInPaths': '', 'BindPaths': '',
                'FragmentPath': '/etc/systemd/system/' + host.SERVICE,
                'BindReadOnlyPaths': str(SOURCE) + ':' + str(host.CACHE_VIEW),
                'ReadWritePaths': str(host.RUNNER_HOME) + ' ' + str(host.OUTPUT_ROOT)}
    # systemd 255 renders its default recursive bind with an explicit suffix.
    # Normalize only that exact suffix; source/destination and read-only property
    # must still match, and no writable BindPaths may exist.
    if values.get('BindReadOnlyPaths', '').endswith(':rbind'):
        values['BindReadOnlyPaths'] = values['BindReadOnlyPaths'][:-6]
    if any(values.get(k) != v for k, v in required.items()):
        blocked('effective-service-sandbox-mismatch')
    return {'effectiveSandboxVerified': True}

def wait_job(args, log_dir, runner_id):
    deadline = time.monotonic() + args.wait_seconds
    seen_online = False
    while time.monotonic() < deadline:
        try:
            runner = gh_json(f'repos/{host.REPO}/actions/runners/{runner_id}', '{id,name,status}', log_dir)
            if not isinstance(runner, dict) or runner.get('id') != runner_id or runner.get('name') != 'foo-offmenu':
                blocked('github-runner-identity-mismatch')
            seen_online = seen_online or runner.get('status') == 'online'
            run = gh_json(f'repos/{host.REPO}/actions/runs/{args.expected_run_id}',
                          '{id,head_sha,head_branch,event,path,status,conclusion}', log_dir)
            if not isinstance(run, dict) or run.get('id') != args.expected_run_id or run.get('head_sha') != args.expected_head_sha or run.get('path') != WORKFLOW or run.get('head_branch') != 'offmenu-runner-jobs' or run.get('event') != 'push':
                blocked('github-run-identity-mismatch')
            if run.get('status') == 'completed':
                jobs = gh_json(f'repos/{host.REPO}/actions/runs/{args.expected_run_id}/jobs?per_page=30',
                               '[.jobs[] | {id,name,runner_id,conclusion}]', log_dir)
                matched = [j for j in jobs if isinstance(j, dict) and j.get('name') == 'run' and j.get('runner_id') == runner_id] if isinstance(jobs, list) else []
                if run.get('conclusion') != 'success' or len(matched) != 1 or matched[0].get('conclusion') != 'success':
                    blocked('queued-smoke-failed-or-wrong-runner')
                return {'runId': args.expected_run_id, 'jobId': args.expected_job_id,
                        'runnerOnlineObserved': seen_online, 'queuedSmokeSucceeded': True,
                        'runUrl': f'https://github.com/{host.REPO}/actions/runs/{args.expected_run_id}'}
        except Blocked as exc:
            if str(exc) != 'github-read-failed':
                raise
        time.sleep(min(10, max(0, deadline - time.monotonic())))
    blocked('queued-smoke-wait-timeout')

def run_all(args, log_dir):
    report = batch.run_batch(log_dir)
    report.update(reportKind='offmenu-runner-bootstrap', applyRequested=args.apply,
                  githubAgreementAccepted=args.accept_github_agreement, githubAgreementUrl=AGREEMENT, actualDatasetConfigured=False,
                  serviceBootEnableRequested=False, expectedJobId=args.expected_job_id,
                  expectedHeadSha=args.expected_head_sha)
    steps = report['steps']
    def stage(name, action, dependencies=()):
        start = time.monotonic()
        if any(next((s['status'] for s in steps if s['stepId'] == dep), 'failed') != 'passed' for dep in dependencies):
            value = {'status': 'skipped', 'skipReason': 'prerequisite-failed'}
        elif not args.apply:
            value = {'status': 'skipped', 'skipReason': 'apply-not-requested'}
        else:
            try:
                value = action() or {}
                value.setdefault('status', 'passed')
                value.setdefault('exitCode', 0)
            except KeyboardInterrupt:
                value = {'status': 'cancelled', 'errorCode': 'operator-cancelled', 'exitCode': 130}
            except RegistrationProbeError as exc:
                value = {'status': 'failed', 'errorCode': str(exc), 'exitCode': exc.exit_code,
                         'registrationDiagnostics': exc.diagnostics}
            except (Blocked, host.SetupError) as exc:
                code = str(exc)
                value = {'status': 'timeout' if code.endswith('timeout') else 'failed',
                         'errorCode': code if re.fullmatch(r'[a-z0-9-]{1,100}', code) else 'setup-stage-failed', 'exitCode': 1}
            except CommandFailed as exc:
                value = {'status': 'failed', 'errorCode': 'interactive-command-failed', 'exitCode': exc.code}
            except subprocess.TimeoutExpired:
                value = {'status': 'timeout', 'errorCode': 'setup-stage-timeout', 'exitCode': None}
            except Exception:
                value = {'status': 'failed', 'errorCode': 'setup-stage-failed-review-private-local-diagnostics', 'exitCode': None}
        value.update(stepId=name, durationSeconds=round(time.monotonic()-start, 3))
        value.setdefault('exitCode', None)
        steps.append(value)
        print(name + ': ' + value['status'], flush=True)
        return value
    prerequisites = ('preflight', 'runner-unit-tests', 'refresh-unit-tests')
    def local_requirements():
        host.require_host()
        if not args.accept_github_agreement:
            blocked('github-agreement-acceptance-required')
        if not sys.stdin.isatty() or not sys.stdout.isatty():
            blocked('interactive-terminal-required')
        if not shutil.which('sudo') or not shutil.which('gh'):
            blocked('sudo-and-existing-gh-required')
        validate_source()
        return {'requirementsVerified': True}
    stage('setup-requirements', local_requirements, prerequisites)
    # This read-only check fails before mutation if the exact root-queued job is absent.
    stage('queued-job-identity', lambda: check_request(args, log_dir), ('setup-requirements',))
    stage('sudo-authorization', lambda: tty_command(['sudo', '-v'], log_dir, 300), ('queued-job-identity',))
    def source_action():
        report['adminActionsPerformed'] = True
        return prepare_source(log_dir)
    stage('bootstrap-input', source_action, ('sudo-authorization',))
    stage('administrative-setup', lambda: apply_plan(log_dir), ('bootstrap-input',))
    stage('runner-install', lambda: captured('install-runner-package', runner_command(HELPER, 'install'), log_dir, 1900), ('administrative-setup',))
    def register():
        tty_command(['sudo', '-v'], log_dir, 300)
        state = registration_probe(log_dir)
        if state['registered']:
            return {'registrationReused': True, 'runnerId': state['runnerId'],
                    'registrationDiagnostics': state['registrationDiagnostics']}
        report['registrationAttempted'] = True
        print('Use a FRESH registration token from the GitHub runner setup page, only in the local prompt.', flush=True)
        tty_command(runner_command(HELPER, 'register'), log_dir, 900)
        tty_command(['sudo', '-v'], log_dir, 300)
        state = registration_probe(log_dir)
        if not state['registered']:
            blocked('registration-not-established')
        return {'registrationReused': False, 'runnerId': state['runnerId'],
                'registrationDiagnostics': state['registrationDiagnostics']}
    registration = stage('runner-registration', register, ('runner-install',))
    stage('service-verification', lambda: verify_service(log_dir), ('runner-registration',))
    stage('service-start', lambda: captured('start-runner-service', ['sudo', '-n', 'systemctl', 'start', host.SERVICE], log_dir, 120), ('service-verification',))
    live = stage('queued-smoke', lambda: wait_job(args, log_dir, registration['runnerId']), ('service-start',))
    report['liveRunnerOrServiceVerified'] = live.get('queuedSmokeSucceeded') is True
    report['status'] = 'passed' if all(s['status'] == 'passed' or (not args.apply and s['status'] == 'skipped') for s in steps) else 'failed'
    return report

def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--apply', action='store_true')
    parser.add_argument('--publish', action='store_true')
    parser.add_argument('--issue', type=int, default=30)
    parser.add_argument('--accept-github-agreement', action='store_true', help='Acknowledge the already-reviewed agreement: ' + AGREEMENT)
    parser.add_argument('--expected-head-sha')
    parser.add_argument('--expected-job-id')
    parser.add_argument('--expected-run-id', type=int)
    parser.add_argument('--wait-seconds', type=int, default=1200)
    args = parser.parse_args(argv)
    if args.issue < 1 or not 30 <= args.wait_seconds <= 1800 or (args.expected_run_id is not None and args.expected_run_id < 1):
        parser.error('invalid positive issue/run ID or wait interval (30..1800 seconds)')
    if args.expected_head_sha and not re.fullmatch('[0-9a-f]{40}', args.expected_head_sha):
        parser.error('expected head SHA must be exactly 40 lowercase hexadecimal characters')
    if args.expected_job_id and not re.fullmatch('[a-zA-Z0-9][a-zA-Z0-9_.-]{0,79}', args.expected_job_id):
        parser.error('invalid bounded job ID')
    if os.getuid() == 0 or os.geteuid() == 0 or pwd.getpwuid(os.getuid()).pw_name == host.RUNNER_USER:
        print('Run as your ordinary owner account, without sudo.', file=sys.stderr)
        return 2
    os.umask(0o077)
    log_dir = Path(tempfile.mkdtemp(prefix='offmenu-bootstrap-'))
    try:
        report = run_all(args, log_dir)
    except BaseException as exc:
        report = {'schemaVersion': 1, 'reportKind': 'offmenu-runner-bootstrap', 'repository': host.REPO,
                  'status': 'cancelled' if isinstance(exc, KeyboardInterrupt) else 'failed',
                  'errorCode': 'bootstrap-interrupted-or-failed', 'rawLogsUploaded': False, 'datasetContentsUploaded': False}
    raw = batch.report_bytes(report)
    (log_dir / 'report.json').write_bytes(raw + b'\n')
    print(raw.decode())
    print('Private local diagnostics: ' + str(log_dir), file=sys.stderr)
    try:
        publication = batch.publish_once(report, args.issue, log_dir) if args.publish else 'not-requested'
    except Exception:
        publication = 'post-not-verified-check-github-before-retrying'
    print('GitHub report publication: ' + publication)
    return 0 if report['status'] == 'passed' and publication in {'posted', 'not-requested'} else 1

if __name__ == '__main__':
    raise SystemExit(main())
