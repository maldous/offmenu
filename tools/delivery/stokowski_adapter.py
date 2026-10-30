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
import math
import sqlite3
import os
import re
from pathlib import Path
import signal
import subprocess
import sys
import time
from uuid import UUID

from symphony_capacity import AdmissionError, digest
from symphony_tasks import load_manifest, runtime_lease_ids
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


def file_sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read_record(path):
    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise AdmissionError('duplicate_current_key')
            result[key] = value
        return result
    value = json.loads(Path(path).read_text(), object_pairs_hook=unique)
    if not isinstance(value, dict):
        raise AdmissionError('current_record_object_required')
    return value


class CurrentWork:
    """Caller-owned admission references, never a queue or a resource pool.

    current.json v1: owner (existing owner ID), runtime_root and catalog
    (canonical absolute paths),
    source_head, source_sha256 (repo-relative executable input hashes),
    workflow_sha256, policy_sha256, installation_sha256, version. catalog.json v1: version, entries;
    each entry: issue, issue_id, runtime, admission_sha256. Each task runtime's
    current-admission.json v1: version, owner, issue, issue_id, source (canonical
    Git checkout), manifest_sha256, request_sha256, policy_sha256,
    installation_sha256, inputs (canonical absolute file paths to SHA256).
    The approved request is requests/<issue>.json; it is never generated here.
    Only a trusted existing owner writes qualification/catalog records.
    """
    def __init__(self, runtime):
        self.runtime = runtime.resolve()
        self.config = read_record(runtime/'current.json')
        if set(self.config) != {'version', 'owner', 'runtime_root', 'catalog',
                               'source_head', 'source_sha256', 'workflow_sha256', 'policy_sha256', 'installation_sha256'}:
            raise AdmissionError('current_config_fields')
        self.root = Path(self.config['runtime_root'])
        if (self.root != self.root.resolve() or not self.root.is_dir()
            or self.root.name != 'stokowski' or self.root.parent.name != '.delivery'
            or not self.runtime.is_relative_to(self.root) or not self.config['owner']
            or type(self.config['version']) is not int or self.config['version'] != 1
            or not isinstance(self.config['owner'],str) or not self.config['owner'].strip()
            or not isinstance(self.config['source_sha256'],dict)
            or not re.fullmatch(r'[0-9a-f]{40}',self.config['source_head'])):
            raise AdmissionError('current_private_root')
        self.catalog = self.private(self.config['catalog'])
        self.config_sha = file_sha(runtime/'current.json')
        self.state_path = runtime/'current-owner.json'
        self.state = read_record(self.state_path) if self.state_path.exists() else {
            'owner': self.config['owner'], 'config_sha256': self.config_sha, 'bindings': {}, 'tasks': {}}
        if (self.state['owner'] != self.config['owner']
            or self.state['config_sha256'] != self.config_sha):
            raise AdmissionError('current_owner_binding_conflict')
        self.state.update(pid=os.getpid(), process_start=Path('/proc/self/stat').read_text().split()[21],
                          source_head=self.config['source_head'], runtime=str(self.runtime))
        self.entries = {}
        self.fatal = None
        self.stopping = False
        self.state['accepted_delivery'] = False
        self.refresh()

    def private(self, value):
        path = Path(value)
        if not path.is_absolute() or path != path.resolve() or not path.is_relative_to(self.root):
            raise AdmissionError('noncanonical_current_runtime')
        return path

    def save(self):
        checkpoint(self.state_path, self.state)

    def guard(self):
        c = self.config
        if (file_sha(self.runtime/'installation.json') != c['installation_sha256']):
            raise AdmissionError('current_installation_binding')
        verify_install(self.runtime)
        if file_sha(self.runtime/'current.json') != self.config_sha:
            raise AdmissionError('current_config_drift')
        head = subprocess.check_output(['git', '-C', str(SOURCE), 'rev-parse', 'HEAD'], text=True).strip()
        required = {'tools/delivery/stokowski_adapter.py', 'tools/delivery/stokowski_worker.py',
                    'tools/delivery/stokowski_prepare.py', 'tools/delivery/symphony_capacity.py',
                    'tools/delivery/symphony_tasks.py', 'tools/delivery/symphony_workspace.py',
                    'tools/delivery/symphony_codex.py', 'tools/delivery/symphony_protocol.py',
                    'tools/delivery/windmill_runner.py'}
        if head != c['source_head'] or not required.issubset(c['source_sha256']):
            raise AdmissionError('current_source_binding')
        for name, sha in c['source_sha256'].items():
            path = (SOURCE/name).resolve()
            if not path.is_relative_to(SOURCE) or file_sha(path) != sha:
                raise AdmissionError('current_source_drift')
            accepted = subprocess.check_output(['git','-C',str(SOURCE),'show',c['source_head']+':'+name])
            if hashlib.sha256(accepted).hexdigest() != sha:
                raise AdmissionError('current_source_not_reviewed_revision')
        if (file_sha(self.runtime/'workflow.yaml') != c['workflow_sha256']
            or file_sha(self.runtime/'capacity-policy.json') != c['policy_sha256']
            or file_sha(SOURCE/'tools/delivery/capacity-policy.json') != c['policy_sha256']):
            raise AdmissionError('current_policy_or_workflow_drift')
        accepted_policy = subprocess.check_output(['git','-C',str(SOURCE),'show',c['source_head']+':tools/delivery/capacity-policy.json'])
        if hashlib.sha256(accepted_policy).hexdigest() != c['policy_sha256']:
            raise AdmissionError('current_policy_not_reviewed_revision')

    def refresh(self):
        try:
            self.guard()
            catalog = read_record(self.catalog)
            if set(catalog) != {'version', 'entries'} or type(catalog['version']) is not int or catalog['version'] != 1 or not isinstance(catalog['entries'], list):
                raise AdmissionError('current_catalog_fields')
            entries, identities, runtimes = {}, set(), set()
            for entry in catalog['entries']:
                if set(entry) != {'issue', 'issue_id', 'runtime', 'admission_sha256'}:
                    raise AdmissionError('current_entry_fields')
                issue = entry['issue']
                if (not isinstance(issue,str) or not re.fullmatch(r'UIF-[1-9][0-9]*',issue)
                    or str(UUID(entry['issue_id'])) != entry['issue_id']
                    or not re.fullmatch(r'[0-9a-f]{64}',entry['admission_sha256'])):
                    raise AdmissionError('current_entry_identity')
                runtime = str(self.private(entry['runtime']))
                binding = digest(entry)
                previous = self.state['bindings'].get(issue)
                if (issue in entries or entry['issue_id'] in identities or runtime in runtimes
                    or previous is not None and previous != binding):
                    raise AdmissionError('current_identity_rebind')
                # Bind even deferred references: removing and readding cannot replace them.
                if any(v['issue_id'] == entry['issue_id'] or v['runtime'] == runtime
                       for k, v in self.state.get('references', {}).items() if k != issue):
                    raise AdmissionError('current_identity_rebind')
                self.state['bindings'][issue] = binding
                self.state.setdefault('references', {})[issue] = entry
                entries[issue] = entry
                identities.add(entry['issue_id'])
                runtimes.add(runtime)
            self.entries = entries
            self.state['catalog_sha256'] = file_sha(self.catalog)
            for issue in self.state.get('references', {}):
                self.observe(issue)
            self.save()
        except Exception as error:
            self.fatal = type(error).__name__ + ': ' + str(error)
            self.state['fatal'] = self.fatal
            self.save()
            raise AdmissionError('current_fatal_binding') from error

    def observe(self, issue):
        entry = self.state['references'][issue]
        directory = self.private(entry['runtime'])/'attempts'/issue
        task = self.state['tasks'].setdefault(issue, {})
        for name in ('dispatch-intent.json', 'intent.json', 'receipt.json'):
            path = directory/name
            if path.exists():
                task[name] = {'path': str(path), 'sha256': file_sha(path), 'record': read_record(path)}

    def defer(self, issue, reason):
        self.state['tasks'].setdefault(issue, {})['defer'] = reason
        self.save()

    def context(self, issue, *, review=False):
        self.guard()
        entry = self.entries[issue]
        runtime = self.private(entry['runtime'])
        for relative in ('current-admission.json','manifest.json','capacity-policy.json',
                         'installation.json','provider-proof.json','requests','attempts','workspaces'):
            path = runtime/relative
            if path != path.resolve():
                raise AdmissionError('current_symlink_runtime_input')
        admission_path = runtime/'current-admission.json'
        if file_sha(admission_path) != entry['admission_sha256']:
            raise AdmissionError('current_admission_drift')
        admission = read_record(admission_path)
        if (set(admission) != {'version','owner','issue','issue_id','source','manifest_sha256',
                               'request_sha256','policy_sha256','installation_sha256','inputs'}
            or type(admission['version']) is not int or admission['version'] != 1 or admission['owner'] != self.config['owner']
            or admission['issue'] != issue or admission['issue_id'] != entry['issue_id']):
            raise AdmissionError('current_qualification_identity')
        request = runtime/'requests'/(issue+'.json')
        if request != request.resolve() or runtime/'attempts'/issue != (runtime/'attempts'/issue).resolve():
            raise AdmissionError('current_symlink_task_input')
        for path, sha in ((runtime/'manifest.json', admission['manifest_sha256']),
                          (request, admission['request_sha256']),
                          (runtime/'capacity-policy.json', admission['policy_sha256']),
                          (runtime/'installation.json', admission['installation_sha256'])):
            if file_sha(path) != sha:
                raise AdmissionError('current_input_drift')
        if (admission['policy_sha256'] != self.config['policy_sha256']
            or admission['installation_sha256'] != self.config['installation_sha256']):
            raise AdmissionError('current_policy_drift')
        manifest = load_manifest(runtime/'manifest.json', expected_branch=None)
        if set(manifest['tasks']) != {issue} or manifest['tasks'][issue]['issue_id'] != entry['issue_id']:
            raise AdmissionError('current_manifest_identity')
        verify_install(runtime)
        source = Path(admission['source'])
        if not source.is_absolute() or source != source.resolve():
            raise AdmissionError('current_source_path')
        for args, expected in ((['rev-parse','HEAD'], manifest['base_revision']),
                               (['branch','--show-current'], manifest['branch'])):
            if subprocess.check_output(['git','-C',str(source),*args], text=True).strip() != expected:
                raise AdmissionError('current_task_source_drift')
        if not isinstance(admission['inputs'],dict):
            raise AdmissionError('current_declared_inputs_schema')
        for name, sha in admission['inputs'].items():
            path = Path(name)
            if not path.is_absolute() or path != path.resolve() or file_sha(path) != sha:
                raise AdmissionError('current_declared_input_unavailable')
        approved = read_record(request)
        if (set(approved) != {'prompt','timeout_seconds'} or not isinstance(approved['prompt'], str)
            or not approved['prompt'].strip() or type(approved['timeout_seconds']) is not int
            or not 1 <= approved['timeout_seconds'] <= 600):
            raise AdmissionError('current_request_invalid')
        proof = read_record(runtime/'provider-proof.json')
        checked = proof.get('checked_at')
        policy = read_record(runtime/'capacity-policy.json')
        if (proof.get('route') != 'codex-chatgpt' or proof.get('available') is not True
            or type(checked) not in (int,float) or not math.isfinite(checked)
            or checked > time.time()+5 or time.time()-checked > policy['symphony']['provider_proof_ttl_seconds']
            or type(proof.get('session_ceiling')) is not int or proof['session_ceiling'] < 1):
            raise AdmissionError('provider_unavailable_or_stale')
        if self.stopping or (self.runtime/'cancel.json').exists() or (runtime/'cancel.json').exists():
            raise AdmissionError('current_task_cancelled')
        self.observe(issue)
        if not review and any(k in self.state['tasks'][issue] for k in ('dispatch-intent.json','intent.json','receipt.json')):
            raise AdmissionError('current_retained_effect_requires_reconciliation')
        lease = runtime_lease_ids(runtime, manifest)[issue]
        database = Path(policy['symphony']['pool_path'])/'state.sqlite'
        if not review and database.exists():
            with sqlite3.connect(database.as_uri()+'?mode=ro', uri=True) as db:
                if db.execute('SELECT 1 FROM leases WHERE id=?', (lease,)).fetchone():
                    raise AdmissionError('current_retained_lease_requires_reconciliation')
        return runtime, manifest, source

    def gate_binding(self, issue):
        """Validate native evidence, never infer unit review from parent status.

        unit_gate in current-owner.json is the local pending record. Its binding
        must be retained unchanged by the owner when setting disposition to
        approved/rework. No Linear comment or status is a unit disposition.
        """
        entry = self.entries.get(issue.identifier)
        if not entry or issue.id != entry['issue_id']:
            raise AdmissionError('current_gate_identity')
        runtime, manifest, _ = self.context(issue.identifier, review=True)
        task = manifest['tasks'][issue.identifier]
        request = read_record(runtime/'requests'/(issue.identifier+'.json'))
        binding = dict(branch=manifest['branch'], head=manifest['base_revision'],
                       owner=task['owner'], write_roots=task['allowed_paths'],
                       resources=task['resources'],
                       task_sha256=digest(dict(runtime=str(runtime), manifest=manifest, request=request)))
        directory = runtime/'attempts'/issue.identifier
        intent = read_record(directory/'intent.json')
        dispatch = read_record(directory/'dispatch-intent.json')
        receipt = read_record(directory/'receipt.json')
        lease = runtime_lease_ids(runtime, manifest)[issue.identifier]
        if (intent.get('binding') != binding or intent.get('lease') != lease
            or dispatch.get('entry_sha256') != digest(entry)
            or dispatch.get('request_sha256') != file_sha(runtime/'requests'/(issue.identifier+'.json'))
            or dispatch.get('manifest_sha256') != file_sha(runtime/'manifest.json')
            or dispatch.get('expected_lease') != lease
            or dispatch.get('owner') != self.config['owner']
            or receipt.get('binding_sha256') != digest(binding)
            or receipt.get('lease') != lease or receipt.get('issue') != issue.identifier
            or receipt.get('status') != 'succeeded' or receipt.get('child_tree_gone') is not True
            or receipt.get('accepted_delivery') is not False):
            raise AdmissionError('current_gate_native_binding')
        return dict(project_id=manifest['project_id'], issue_id=issue.id,
                    admission_sha256=entry['admission_sha256'], operation_sha256=digest(binding),
                    request_sha256=file_sha(runtime/'requests'/(issue.identifier+'.json')),
                    native_receipt_sha256=file_sha(directory/'receipt.json'))

    async def candidates(self, client, issues):
        self.refresh()
        selected = []
        for issue in issues:
            entry = self.entries.get(issue.identifier)
            if not entry or issue.id != entry['issue_id'] or issue.state not in ('Todo','In Progress'):
                continue
            try:
                self.context(issue.identifier)
                data = await client._graphql('query($id: String!){ issue(id:$id){id identifier project{id} state{name}}}', {'id':issue.id})
                remote = data.get('issue') or {}
                if (remote.get('id') != issue.id or remote.get('identifier') != issue.identifier
                    or remote.get('project', {}).get('id') != PROJECT
                    or remote.get('state', {}).get('name') not in ('Todo','In Progress')):
                    raise AdmissionError('current_authoritative_identity_or_state')
                self.state['tasks'][issue.identifier].pop('defer', None)
                self.save()
                selected.append(issue)
            except Exception as error:
                reason = str(error) if isinstance(error, AdmissionError) else 'current_input_or_tracker_unavailable'
                self.defer(issue.identifier, type(error).__name__ + ': ' + reason)
        return selected


def install_adapters(runtime, manifest, key, current=None):
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
        try:
            issues = await original_fetch(client, project_slug, ['Todo','In Progress'] if current else states)
        except Exception as error:
            if not current:
                raise
            current.state['fetch_defer'] = type(error).__name__
            current.save()
            return []
        if current:
            return await current.candidates(client, issues)
        return [i for i in issues if i.identifier in manifest['tasks']
                and i.id == manifest['tasks'][i.identifier]['issue_id']]

    linear.LinearClient.fetch_candidate_issues = selected_candidates

    async def ensure_workspace(root, identifier, hooks):
        selected_runtime, selected_manifest, source = (current.context(identifier) if current
                                                       else (runtime, manifest, SOURCE))
        if identifier not in selected_manifest['tasks'] or root.resolve() != runtime/'workspaces':
            raise AdmissionError('Workspace outside selected manifest')
        path = selected_runtime/'workspaces'/identifier
        created = not path.exists()
        if created:
            path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
            subprocess.run(['git', 'clone', '--shared', '--single-branch', '--branch',
                            selected_manifest['branch'], str(source), str(path)], check=True,
                           capture_output=True, env=child_environment(os.environ))
        head = subprocess.check_output(['git', '-C', str(path), 'rev-parse', 'HEAD'], text=True).strip()
        branch = (subprocess.check_output(['git', '-C', str(path), 'branch', '--show-current'], text=True).strip()
                  if current else selected_manifest['branch'])
        if head != selected_manifest['base_revision'] or branch != selected_manifest['branch']:
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
    active_turns = set()
    original_tick = orchestration.Orchestrator._tick
    if current:
        async def current_tick(owner):
            current.refresh()  # Before upstream config reload can skip candidate fetching.
            return await original_tick(owner)
        orchestration.Orchestrator._tick = current_tick

    if current:
        async def unit_enter_gate(owner, issue, state_name):
            if state_name != 'evidence-pending':
                return
            try:
                binding = current.gate_binding(issue)
            except (AdmissionError, OSError, ValueError, KeyError):
                return  # Missing evidence is a hold, never historical recovery.
            task = current.state['tasks'][issue.identifier]
            task.setdefault('unit_gate', {'binding':binding, 'disposition':'waiting'})
            if task['unit_gate'].get('binding') != binding:
                return
            current.save()
            owner._pending_gates[issue.id] = state_name
            owner._issue_current_state[issue.id] = state_name
            owner.claimed.discard(issue.id)

        async def unit_gate_responses(owner):
            current.refresh()
            # Deliberately do not call the project-wide native status/comment
            # recovery path: those markers have no operation/admission binding.
            for identifier, entry in current.entries.items():
                from stokowski.models import Issue
                issue = Issue(id=entry['issue_id'], identifier=identifier, title='', state='In Review')
                task = current.state['tasks'].get(identifier, {})
                gate = task.get('unit_gate', {})
                if gate.get('handled') or gate.get('disposition') not in ('approved','rework'):
                    continue
                try:
                    binding = current.gate_binding(issue)
                except (AdmissionError, OSError, ValueError, KeyError):
                    continue
                if gate.get('binding') != binding:
                    continue
                # Persist the unit verdict before clearing transient tracking.
                # Rework requires fresh owner admission, never a coding retry.
                gate.update(handled=True, unit_review=gate['disposition'], accepted_delivery=False)
                current.save()
                owner._pending_gates.pop(issue.id, None)
                owner._issue_current_state.pop(issue.id, None)
                owner.claimed.discard(issue.id)

        async def unit_rebuild(owner):
            current.refresh()
            # Recovery is local and exact-bound; no Linear historical fallback.
            for identifier, entry in current.entries.items():
                from stokowski.models import Issue
                issue = Issue(id=entry['issue_id'], identifier=identifier, title='', state='In Review')
                gate = current.state['tasks'].get(identifier, {}).get('unit_gate', {})
                if not gate or gate.get('handled'):
                    continue
                try:
                    if gate.get('binding') != current.gate_binding(issue):
                        continue
                except (AdmissionError, OSError, ValueError, KeyError):
                    continue
                owner._pending_gates[issue.id] = 'evidence-pending'
                owner._issue_current_state[issue.id] = 'evidence-pending'

        async def unit_resolve(owner, issue):
            # Native comments cannot select a current unit's workflow or gate.
            current.context(issue.identifier)
            return 'implement', 1

        async def unit_transition(owner, issue, transition_name):
            # Independent guard: even a supplied terminal workflow cannot close
            # a parent. Native coding completion only creates a pending unit gate.
            if transition_name == 'complete':
                await unit_enter_gate(owner, issue, 'evidence-pending')

        orchestration.Orchestrator._enter_gate = unit_enter_gate
        orchestration.Orchestrator._transition = unit_transition
        orchestration.Orchestrator._handle_gate_responses = unit_gate_responses
        orchestration.Orchestrator._rebuild_gates_from_linear = unit_rebuild
        orchestration.Orchestrator._resolve_current_state = unit_resolve

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
            if current:
                current.refresh()

    async def safe_stop(owner):
        owner._running = False
        if hasattr(owner, '_stop_event'):
            owner._stop_event.set()
        for timer in owner._retry_timers.values():
            timer.cancel()
        tasks = list(set(owner._tasks.values()) | (active_turns if current else set()))
        for task in tasks:
            if not current or not task.cancelling():
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
        report_runtime = Path(current.state['references'][issue.identifier]['runtime']) if current else runtime
        path = report_runtime/'attempts'/issue.identifier/'receipt.json'
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

    async def owned_turn(runner_type, claude_cfg, hooks_cfg, prompt, workspace_path,
                       issue, attempt, on_event=None, on_pid=None, env=None):
        if runner_type != 'codex' or claude_cfg.model != MODEL:
            raise AdmissionError('Only the reviewed existing Codex session route is admitted')
        if any(vars(hooks_cfg).get(k) for k in ('before_run', 'after_run', 'on_stage_enter')):
            raise AdmissionError('Unenforced shell validation hook rejected')
        task_runtime = runtime
        if current:
            task_runtime, selected_manifest, _ = current.context(issue.identifier)
            if workspace_path.resolve() != task_runtime/'workspaces'/issue.identifier:
                raise AdmissionError('current_workspace_binding')
        request = {'prompt': prompt, 'timeout_seconds': min(600, claude_cfg.turn_timeout_ms//1000)}
        request_path = runtime/'requests'/(issue.identifier+'.json')
        if current:
            directory = task_runtime/'attempts'/issue.identifier
            directory.mkdir(parents=True, exist_ok=True, mode=0o700)
            intent = directory/'dispatch-intent.json'
            # Exclusive creation precedes the spawn window; even an exception
            # hereafter retains an unknown effect and can never mean absence.
            with intent.open('x') as stream:
                json.dump({'entry_sha256': digest(current.entries[issue.identifier]),
                           'request_sha256': file_sha(task_runtime/'requests'/(issue.identifier+'.json')),
                           'manifest_sha256': file_sha(task_runtime/'manifest.json'),
                           'provider_proof_sha256': file_sha(task_runtime/'provider-proof.json'),
                           'expected_lease': runtime_lease_ids(task_runtime, selected_manifest)[issue.identifier],
                           'owner': current.config['owner'], 'pid': os.getpid()}, stream)
                stream.flush()
                os.fsync(stream.fileno())
            current.observe(issue.identifier)
            current.save()
        else:
            if request_path.exists():
                raise AdmissionError('Attempt already requested; reconcile before retry')
            request_path.parent.mkdir(exist_ok=True, mode=0o700)
            checkpoint(request_path, request)
        process = await asyncio.create_subprocess_exec(
            sys.executable, str(SOURCE/'tools/delivery/stokowski_worker.py'),
            '--runtime', str(task_runtime), '--issue', issue.identifier,
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
        if current:
            current.refresh()
        receipt_path = task_runtime/'attempts'/issue.identifier/'receipt.json'
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

    async def run_turn(*args, **kwargs):
        task = asyncio.current_task()
        if current:
            active_turns.add(task)
        try:
            return await owned_turn(*args, **kwargs)
        finally:
            active_turns.discard(task)
            if current:
                for issue in current.state.get('references', {}):
                    current.observe(issue)
                current.save()

    orchestration.run_turn = run_turn
    return orchestration


async def run(runtime, duration, dry_run=False, current_mode=False):
    if not current_mode:
        return await _run(runtime, duration, dry_run)
    # One current coordinator for the caller's canonical private runtime root,
    # even when two callers point at different catalog/coordinator directories.
    config = read_record(runtime/'current.json')
    root = Path(config['runtime_root'])
    if (not root.is_absolute() or root != root.resolve() or root.name != 'stokowski'
        or root.parent.name != '.delivery' or not runtime.resolve().is_relative_to(root)):
        raise AdmissionError('current_private_root')
    with (root/'coordinator.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX|fcntl.LOCK_NB)
        return await _run(runtime, duration, dry_run, True)


async def _run(runtime, duration, dry_run=False, current_mode=False):
    verify_install(runtime)
    current = CurrentWork(runtime) if current_mode else None
    if current and (runtime/'cancel.json').exists():
        current.state.update(stopped=True, cancellation_requested=True)
        current.save()
        return
    manifest = None if current else load_manifest(runtime/'manifest.json',expected_branch=None)
    policy = json.loads((runtime/'capacity-policy.json').read_text())
    if policy != json.loads((SOURCE/'tools/delivery/capacity-policy.json').read_text()):
        raise AdmissionError('Runtime policy differs from reviewed source')
    key = credential()
    orchestration = install_adapters(runtime, manifest, key, current)
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
    if not current and {i.id for i in candidates} != {t['issue_id'] for t in manifest['tasks'].values()}:
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
    deadline = None if current else time.monotonic()+duration
    loop = asyncio.get_running_loop()
    cancelled = asyncio.Event()
    if current:
        def request_stop():
            current.stopping = True
            cancelled.set()
        for sig in (signal.SIGTERM, signal.SIGINT):
            loop.add_signal_handler(sig, request_stop)
    try:
        while deadline is None or time.monotonic() < deadline:
            if current and current.fatal:
                raise AdmissionError(current.fatal)
            if cancelled.is_set():
                break
            if service.done():
                service.result()
                break
            finished = not current and all((runtime/'attempts'/i/'receipt.json').exists() for i in manifest['tasks'])
            if (finished and not orchestration._offmenu_pending_control
                and all(not o.running and not o._tasks for o in coordinator.orchestrators.values())):
                break
            if (runtime/'cancel.json').exists():
                break
            await asyncio.sleep(.5)
    finally:
        if current:
            current.stopping = True
        await coordinator.stop()
        await asyncio.gather(service, return_exceptions=True)
        if current:
            for issue in current.state.get('references', {}):
                current.observe(issue)
            current.state['stopped'] = True
            current.state['child_cleanup_proven'] = all(
                task.get('receipt.json', {}).get('record', {}).get('child_tree_gone') is True
                for task in current.state['tasks'].values()
                if 'dispatch-intent.json' in task or 'intent.json' in task)
            current.save()
            for sig in (signal.SIGTERM, signal.SIGINT):
                loop.remove_signal_handler(sig)
        checkpoint(runtime/'coordinator-finished.json', dict(stopped=True, at=time.time(),
                   accepted_delivery=False, project_id=PROJECT))


async def reconcile_metadata(runtime):
    """Reconcile the already-ended attempt's tracker state; never run coding."""
    verify_install(runtime)
    manifest = load_manifest(runtime/'manifest.json',expected_branch=None)
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
    parser.add_argument('--current', action='store_true', help='Caller-owned native polling of current.json qualified catalog; no duration limit; cancel.json or TERM/INT stops. No owner-loss recovery.')
    parser.add_argument('--duration', type=int, default=240)
    parser.add_argument('--dry-run', action='store_true')
    parser.add_argument('--reconcile-metadata', action='store_true')
    parser.add_argument('--validation-stage', action='store_true')
    parser.add_argument('--preview-dispatch', action='store_true')
    args = parser.parse_args()
    if args.current and (args.validation_stage or args.reconcile_metadata):
        parser.error('--current is only for native coding coordination')
    if not 1 <= args.duration <= 900:
        raise SystemExit('Finite coordinator duration must be 1..900 seconds')
    runtime = args.runtime.resolve()
    with (runtime/'coordinator.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX|fcntl.LOCK_NB)
        try:
            if args.validation_stage:
                from stokowski_stage import continue_stage
                result = asyncio.run(continue_stage(runtime,args.duration,args.preview_dispatch))
                print(json.dumps(result))
            elif args.reconcile_metadata:
                asyncio.run(reconcile_metadata(runtime))
            else:
                asyncio.run(run(runtime, args.duration, args.dry_run, args.current))
        except (OSError, RuntimeError, ValueError, AdmissionError) as error:
            print(json.dumps({'status':'blocked','error_type':type(error).__name__,
                              'credential_exported':False}))
            raise SystemExit(2)
