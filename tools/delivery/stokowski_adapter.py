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
import selectors
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
    def __init__(self, runtime, *, read_only=False, qualification_only=False):
        if qualification_only and not read_only:
            raise AdmissionError('current_qualification_read_only_required')
        self.read_only = read_only
        self.runtime = runtime.resolve()
        self.config = read_record(runtime/'current.json')
        if set(self.config) - {'qualified_successor'} != {'version', 'owner', 'runtime_root', 'catalog',
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
        if read_only:
            # Incoming readers reuse all admission/native checks, without an
            # owner refresh, consumption, PID update on disk or journal writes.
            self.guard()
            if qualification_only:
                # Publication qualifies original evidence before catalog exposure;
                # it cannot consume reviews or mutate coordinator state.
                return
            catalog = read_record(self.catalog)
            if catalog.get('version') != 1 or not isinstance(catalog.get('entries'), list):
                raise AdmissionError('current_catalog_fields')
            for entry in catalog['entries']:
                issue = entry['issue']
                if (issue in self.entries or self.state['bindings'].get(issue) != digest(entry)
                    or self.state.get('references', {}).get(issue) != entry):
                    raise AdmissionError('current_identity_rebind')
                self.private(entry['runtime'])
                self.entries[issue] = entry
        else:
            self.refresh()

    def private(self, value):
        path = Path(value)
        if not path.is_absolute() or path != path.resolve() or not path.is_relative_to(self.root):
            raise AdmissionError('noncanonical_current_runtime')
        return path

    def save(self):
        if self.read_only:
            raise AdmissionError('current_read_only')
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
            self._consume_unit_reviews()
            self._successor_boundary()
            self.save()
        except Exception as error:
            self.fatal = type(error).__name__ + ': ' + str(error)
            self.state['fatal'] = self.fatal
            self.save()
            raise AdmissionError('current_fatal_binding') from error

    def qualify_successor(self, handoff_ref, packet, owner_config):
        """Read-only qualification; current.json is trusted out of band.

        The exact handoff pin transitively allows source/config/owner/request/
        scope/resources. Packet assertions alone never grant this origin.
        """
        from types import SimpleNamespace
        self.guard()
        if (self.config.get('qualified_successor') != handoff_ref
            or packet.get('origin') != 'qualified-successor-v1'
            or packet['owner'] != self.config['owner']
            or owner_config['owner'] != self.config['owner']
            or packet['selected_current']['coordinator_runtime'] != str(self.runtime)
            or packet['selected_current']['catalog_path'] != str(self.catalog)
            or packet['selected_current']['runtime_root'] != str(self.root)):
            raise AdmissionError('successor_owner_allowlist')
        expiry = packet.get('expires_at')
        if type(expiry) not in (int, float) or not math.isfinite(expiry) or time.time() > expiry:
            raise AdmissionError('successor_qualification_expired')
        trigger = packet['trigger']
        if set(trigger) != {'issue', 'entry', 'unit_binding', 'review_sha256'}:
            raise AdmissionError('successor_trigger_fields')
        issue = trigger['issue']
        entry = self.state.get('references', {}).get(issue)
        gate = self.state['tasks'].get(issue, {}).get('unit_gate', {})
        if (entry != trigger['entry'] or self.entries.get(issue, entry) != entry
            or gate.get('binding') != trigger['unit_binding']
            or gate.get('review_sha256') != trigger['review_sha256']
            or gate.get('disposition') != 'approved' or gate.get('handled') is not True
            or gate.get('unit_review') != 'approved'):
            raise AdmissionError('successor_terminal_gate')
        catalog = read_record(self.catalog)
        if entry not in catalog['entries'] or self.state['bindings'].get(issue) != digest(entry):
            raise AdmissionError('successor_original_entry_drift')
        import copy
        view = copy.copy(self)
        view.entries = {issue: entry}
        review = read_record(self.runtime/('unit-review-' + issue + '.json'))
        # This checks the actual journal status, cancellation/reconciliation,
        # immutable operation, native output and independent review evidence.
        if (digest(review) != trigger['review_sha256']
            or view._check_unit_review(review) != trigger['unit_binding']
            or view.gate_binding(SimpleNamespace(identifier=issue, id=entry['issue_id']),
                                 observation=True) != trigger['unit_binding']):
            raise AdmissionError('successor_trigger_drift')
        outcome = packet['execution_outcome']
        if (outcome['project_id'] != PROJECT or outcome['identifier'] == issue
            or outcome['uuid'] == entry['issue_id']
            or any(e['issue'] == outcome['identifier'] or e['issue_id'] == outcome['uuid']
                   or e['runtime'] == packet['selected_current']['task_runtime']
                   for e in self.state.get('references', {}).values())):
            # Once exposed, qualification is reconciled from the publication
            # journal at the boundary, never used to prepare another operation.
            raise AdmissionError('successor_identity_collision')
        return digest(dict(handoff=handoff_ref, owner_config=packet['owner_config'], trigger=trigger))

    def _successor_boundary(self):
        # This service has Linear credentials only. Authentication/publication
        # remains with the existing GitHub owner; no automatic association exists.
        ref = self.config.get('qualified_successor')
        if ref is None:
            return
        pending = self.state.get('successor_request')
        try:
            path = self.private(ref['path'])
            if file_sha(path) != ref['sha256']:
                raise AdmissionError('successor_handoff_drift')
            handoff = read_record(path)
            def pinned(reference):
                path = self.private(reference['path'])
                if file_sha(path) != reference['sha256']:
                    raise AdmissionError('successor_input_drift')
                return read_record(path)
            packet = pinned(handoff['task_packet'])
            config = pinned(handoff['owner_config'])
            if packet['owner_config'] != handoff['owner_config']:
                raise AdmissionError('successor_config_drift')
            identity = digest(dict(handoff=ref, owner_config=packet['owner_config'], trigger=packet['trigger']))
            if pending is not None and pending['identity'] != identity:
                raise AdmissionError('successor_request_rebind')
            if 'native_publication' in config or pending and 'native_request' in pending:
                self._native_successor(ref, handoff, packet, config, identity, pending)
                return
            # Publication owns the journal. Only this coordinator writes its
            # state, at its existing locked boundary; no gateway state callback.
            journal = self.root/('owner-bridge-' + ref['sha256'] + '.json')
            if pending is not None and journal.exists():
                result = read_record(journal)
                if (not re.fullmatch('[0-9a-f]{64}', result['nonce'])
                    or result['nonce'][12:] != identity[12:] or result['context']['handoff'] != ref
                    or result['context']['owner_config'] != packet['owner_config']):
                    raise AdmissionError('successor_result_binding')
                status = result.get('result', {}).get('status', 'uncertain')
                if status in ('published', 'duplicate'):
                    runtime = self.private(packet['selected_current']['task_runtime'])
                    plan = read_record(self.root/(runtime.name + '-publication.json'))
                    expected = dict(handoff_sha256=ref['sha256'], packet=handoff['task_packet'],
                                    config=handoff['owner_config'])
                    if (plan['identity'] != expected or read_record(self.catalog) != plan['catalog_after']
                        or result['result'].get('runtime') != str(runtime)
                        or file_sha(runtime/'current-admission.json') != plan['catalog_after']['entries'][-1]['admission_sha256']):
                        raise AdmissionError('successor_publication_drift')
                pending['status'] = status if status in ('published', 'duplicate', 'refused') else 'uncertain'
                return
            self.qualify_successor(ref, packet, config)
            for name, sha in packet['inputs'].items():
                path = Path(name)
                if not path.is_absolute() or path != path.resolve() or file_sha(path) != sha:
                    raise AdmissionError('successor_input_drift')
            manifest = load_manifest(packet['manifest']['path'], expected_head=packet['source']['base'],
                                     expected_branch=packet['source']['branch'])
            task = manifest['tasks'][packet['execution_outcome']['identifier']]
            if ('stage' in task or task['allowed_paths'] != packet['scope']
                or task['resources'] != packet['resources'] or task['owner'] != self.config['owner']):
                raise AdmissionError('successor_task_binding')
            from symphony_capacity import overlap
            for entry in self.state['references'].values():
                other = read_record(self.private(entry['runtime'])/'manifest.json')
                if any(overlap(a, b) for a in packet['scope']
                       for t in other['tasks'].values() for b in t['allowed_paths']):
                    raise AdmissionError('successor_scope_overlap')
            if pending is None:
                self.state['successor_request'] = dict(identity=identity, handoff=ref,
                    owner_config=packet['owner_config'], created_at=time.time(), status='pending')
            elif pending['status'] != 'pending':
                raise AdmissionError('successor_request_held')
        except Exception as error:
            if pending is not None:
                pending['status'] = 'held'
            self.state['successor_hold'] = type(error).__name__ + ': ' + str(error)

    def _native_publication_cli(self, data):
        """Fixed launch seam: no executable, environment or argv from a packet."""
        import stokowski_native_publication as native
        with subprocess.Popen([sys.executable, '-E', '-s',
                               str(SOURCE/'tools/delivery/stokowski_native_publication.py')],
                              cwd=SOURCE, env=dict(native.ENV), stdin=subprocess.PIPE,
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                              start_new_session=True) as child:
            streams = selectors.DefaultSelector()
            output = bytearray()
            deadline = time.monotonic() + 90
            try:
                os.set_blocking(child.stdin.fileno(), False)
                streams.register(child.stdin, selectors.EVENT_WRITE)
                remaining = memoryview(data)
                for stream in (child.stdout, child.stderr):
                    os.set_blocking(stream.fileno(), False)
                    streams.register(stream, selectors.EVENT_READ)
                total = 0
                while streams.get_map():
                    if time.monotonic() >= deadline:
                        raise AdmissionError('native_reply_timeout')
                    for key, _ in streams.select(0.1):
                        if key.fileobj is child.stdin:
                            remaining = remaining[os.write(key.fd, remaining):]
                            if not remaining:
                                streams.unregister(child.stdin)
                                child.stdin.close()
                            continue
                        chunk = os.read(key.fd, native.LIMIT + 1)
                        total += len(chunk)
                        if total > native.LIMIT:
                            raise AdmissionError('native_reply_size')
                        if not chunk:
                            streams.unregister(key.fileobj)
                        elif key.fileobj is child.stdout:
                            output.extend(chunk)
                if child.wait(timeout=max(0.001, deadline-time.monotonic())) != 0:
                    raise AdmissionError('native_reply_failed')
                return bytes(output)
            finally:
                streams.close()
                if child.poll() is None:
                    os.killpg(child.pid, signal.SIGKILL)
                    child.wait()

    def _native_successor(self, ref, handoff, packet, config, identity, pending):
        # Opt-in executable pins live in the already owner-qualified config.
        # The MCP owner bridge and its default packet are deliberately separate.
        self.guard()
        module = 'tools/delivery/stokowski_native_publication.py'
        if self.config['source_sha256'].get(module) != file_sha(SOURCE/module):
            raise AdmissionError('successor_native_module_pin')
        import stokowski_native_publication as native
        pins = config['native_publication']
        if (set(pins) != {'source_base', 'source_head', 'source_branch', 'source_sha256', 'python_sha256'}
            or pins['source_head'] != self.config['source_head']
            or not isinstance(pins['source_sha256'], dict)
            or any(self.config['source_sha256'].get(name) != sha for name, sha in pins['source_sha256'].items())
            or pins['python_sha256'] != file_sha(Path(sys.executable).resolve())
            or not {'tools/delivery/'+name+'.py' for name in native.MODULES} <= set(pins['source_sha256'])
            or config['caller_association']['native_route'] != native.ROUTE
            or handoff['native_route'] != native.ROUTE):
            raise AdmissionError('successor_native_configuration')
        context = dict(pins, handoff=ref, owner_config=handoff['owner_config'],
                       task_packet=handoff['task_packet'], owner=self.config['owner'],
                       claim={k: config['repository_claim'][k] for k in ('path', 'sha256')})
        # Only fixed local Git observations here; authentication belongs to CLI.
        native.validate(context, SOURCE, native.process)
        if self.stopping or (self.runtime/'cancel.json').exists():
            raise AdmissionError('successor_native_cancelled')
        if pending is None or 'native_request' not in pending:
            if pending is not None and pending['status'] != 'pending':
                raise AdmissionError('successor_request_held')
            self.qualify_successor(ref, packet, config)
            manifest = load_manifest(packet['manifest']['path'], expected_head=packet['source']['base'],
                                     expected_branch=packet['source']['branch'])
            task = manifest['tasks'][packet['execution_outcome']['identifier']]
            if ('stage' in task or task['allowed_paths'] != packet['scope']
                or task['resources'] != packet['resources'] or task['owner'] != self.config['owner']):
                raise AdmissionError('successor_task_binding')
            from symphony_capacity import overlap
            for entry in self.state['references'].values():
                other = read_record(self.private(entry['runtime'])/'manifest.json')
                if any(overlap(a, b) for a in packet['scope']
                       for t in other['tasks'].values() for b in t['allowed_paths']):
                    raise AdmissionError('successor_scope_overlap')
            request = dict(version=1, nonce=os.urandom(32).hex(), operation=ref['sha256'], context=context)
            pending = dict(identity=identity, handoff=ref, owner_config=packet['owner_config'],
                           created_at=time.time(), status='pending', native_request=request,
                           native_binding=native.sha(native.encode(request)))
            self.state['successor_request'] = pending
            self.save()  # Required before launching; publisher reads this pending intent.
            directory = os.open(self.runtime, os.O_RDONLY | os.O_DIRECTORY)
            try:
                os.fsync(directory)  # Make the checkpoint rename durable before any effect.
            finally:
                os.close(directory)
            mode = 'prepare'
        else:
            request = pending['native_request']
            if (set(request) != {'version', 'nonce', 'operation', 'context'}
                or request['version'] != 1 or request['operation'] != ref['sha256']
                or request['context'] != context
                or not re.fullmatch('[0-9a-f]{64}', request['nonce'])
                or native.sha(native.encode(request)) != pending['native_binding']):
                raise AdmissionError('successor_native_intent_drift')
            mode = 'status'  # Even a missing custody file never authorizes another prepare.
        try:
            reply = native.decode(self._native_publication_cli(native.encode(dict(request, mode=mode))))
            custody_path = SOURCE/'.delivery/native-ssh-publication'/(ref['sha256']+'.json')
            custody = native.decode(native.read(native.canonical(str(custody_path))))
            result = custody.get('result', dict(status='uncertain', dispatches=0))
            if (custody['request'] != request or custody['binding'] != pending['native_binding']
                or reply['binding'] != pending['native_binding'] or reply['result'] != result
                or reply['dispatches'] != 0 or result.get('dispatches') != 0):
                raise AdmissionError('successor_native_result_binding')
            status = result.get('status')
            if status in ('published', 'duplicate'):
                runtime = self.private(packet['selected_current']['task_runtime'])
                journal_path = self.root/(runtime.name+'-publication.json')
                plan = read_record(journal_path)
                issue = packet['execution_outcome']['identifier']
                admission = dict(version=1, owner=self.config['owner'], issue=issue,
                    issue_id=packet['execution_outcome']['uuid'], source=packet['source']['source_checkout'],
                    manifest_sha256=packet['manifest']['sha256'], request_sha256=packet['request']['sha256'],
                    policy_sha256=self.config['policy_sha256'], installation_sha256=self.config['installation_sha256'],
                    inputs={k:v for k,v in packet['inputs'].items() if k != str(self.catalog)})
                from stokowski_prepare import _publication_bytes
                entry = dict(issue=issue, issue_id=admission['issue_id'], runtime=str(runtime),
                             admission_sha256=native.sha(_publication_bytes(admission)))
                if (plan['identity'] != dict(handoff_sha256=ref['sha256'], packet=handoff['task_packet'],
                                            config=handoff['owner_config'])
                    or native.sha(plan['catalog_before_bytes'].encode()) != packet['inputs'][str(self.catalog)]
                    or json.loads(plan['catalog_before_bytes']) != plan['catalog_before']
                    or plan['catalog_after'] != dict(version=1, entries=plan['catalog_before']['entries']+[entry])
                    or read_record(self.catalog) != plan['catalog_after']
                    or result.get('runtime') != str(runtime)
                    or mode == 'status' and reply.get('journal_sha256') != file_sha(journal_path)
                    or read_record(runtime/'current-admission.json') != admission
                    or file_sha(runtime/'current-admission.json') != entry['admission_sha256']
                    or file_sha(runtime/'manifest.json') != packet['manifest']['sha256']
                    or file_sha(runtime/'requests'/(issue+'.json')) != packet['request']['sha256']):
                    raise AdmissionError('successor_native_publication_drift')
                pending['status'] = status
            else:
                pending['status'] = 'uncertain'
        except Exception:
            pending['status'] = 'uncertain'
            raise
        finally:
            self.save()

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

    def context(self, issue, *, review=False, observation=False):
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
        recovery_admission = None
        selected_task = manifest['tasks'][issue]
        if (observation and selected_task.get('stage') == 'validation'
            and selected_task['stage_binding']['entry'].get('origin') == 'reviewed-source-v1'):
            _, _, selected, _, _ = self.reviewed_origin(issue,selected_task,observation=True)
            recovery_admission = selected['admission_path']
        for name, sha in admission['inputs'].items():
            if name == recovery_admission:
                if sha != selected['admission_sha256']:
                    raise AdmissionError('reviewed_source_admission_pin')
                continue
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
        # Fresh provider capacity is a dispatch condition. Exact-bound completed
        # evidence remains reviewable after that admission proof expires.
        if (proof.get('route') != 'codex-chatgpt' or proof.get('available') is not True
            or type(checked) not in (int,float) or not math.isfinite(checked)
            or checked > time.time()+5
            or (not review and 'stage' not in manifest['tasks'][issue] and time.time()-checked > policy['symphony']['provider_proof_ttl_seconds'])
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

    def reviewed_origin(self, issue, task, *, observation=False):
        """Read the new validation operation under its separately selected runtime."""
        import stokowski_operations as operations
        import stokowski_stage as stage
        for module in (operations,stage):
            name='tools/delivery/'+Path(module.__file__).name
            accepted=subprocess.check_output(['git','-C',str(SOURCE),'show',self.config['source_head']+':'+name])
            if hashlib.sha256(accepted).hexdigest() != file_sha(module.__file__):
                raise AdmissionError('reviewed_source_executor_drift')
        binding = task['stage_binding']
        entry = binding['entry']
        if (set(entry) != {'issue','issue_id','runtime','admission_sha256','origin'}
            or entry['origin'] != 'reviewed-source-v1' or entry['issue'] != issue
            or entry['issue_id'] != task['issue_id'] or task['owner'] != self.config['owner']):
            raise AdmissionError('reviewed_source_identity')
        runtime = self.private(entry['runtime'])
        pins = binding['inputs']
        selected_path = runtime/'validation-bindings.json'
        if not isinstance(pins,dict) or str(selected_path) not in pins:
            raise AdmissionError('reviewed_source_input_coverage')
        bindings = read_record(selected_path)
        selected = bindings['issues'][issue]
        for name, sha in pins.items():
            path = Path(name)
            if not path.is_absolute() or any(p.is_symlink() for p in (path,*path.parents)) or path != path.resolve():
                raise AdmissionError('reviewed_source_input_drift')
            if observation and name == selected['admission_path']:
                continue
            if file_sha(path) != sha:
                raise AdmissionError('reviewed_source_input_drift')
        if bindings != dict(version=1,issues=bindings.get('issues'),history=[]) or set(bindings['issues']) != {issue}:
            raise AdmissionError('reviewed_source_selection')
        selected = bindings['issues'][issue]
        database = self.private(str(runtime/'operations/operations.sqlite'))
        with sqlite3.connect(database.as_uri()+'?mode=ro',uri=True) as db:
            row = db.execute('SELECT spec,state FROM operations WHERE key=?',(selected['operation_key'],)).fetchone()
        if row is None:
            raise AdmissionError('reviewed_source_journal_missing')
        spec,state = map(json.loads,row)
        operations.validated(spec)
        if (spec['version'] != 3 or operations.operation_key(spec) != selected['operation_key']
            or row[0] != json.dumps(spec,sort_keys=True) or spec['owner'] != self.config['owner']
            or spec['issue'] != issue or spec['issue_id'] != task['issue_id']
            or spec['origin']['admission_sha256'] != entry['admission_sha256']
            or selected != dict(operation_key=operations.operation_key(spec),source_head=spec['head'],
                origin='reviewed-source-v1',admission_path=selected['admission_path'],
                admission_sha256=spec['origin']['admission_sha256'],
                local_source_root=spec['local_source_root'],workspace=spec['workspace'])
            or spec['policy_sha256'] != self.config['policy_sha256']
            or spec['runner_sha256'] != file_sha(SOURCE/'tools/delivery/windmill_runner.py')
            or set(task['input_paths']) != set(spec['outputs'])):
            raise AdmissionError('reviewed_source_operation')
        if observation:
            # The owner-pinned binding commits to this exact spec and evidence
            # set. Recover review identity from those immutable pins, without
            # trusting the current admission file or inventing replacement facts.
            admission = dict(spec['origin'])
            reviews = []
            for name,sha in pins.items():
                if name in {selected['admission_path'],str(selected_path)}:
                    continue
                try:
                    review = dict(read_record(name),path=name,sha256=sha)
                except (ValueError,AdmissionError):
                    continue  # Other pinned inputs need not be JSON reviews.
                if digest(review) == spec['origin']['review_sha256']:
                    reviews.append(review)
            if len(reviews) != 1:
                raise AdmissionError('reviewed_source_review_binding')
            admission['review'] = reviews[0]
        else:
            admission = stage.qualify_reviewed_source(spec,selected['admission_path'])
        required = {selected['admission_path']:entry['admission_sha256'],
                    admission['review']['path']:admission['review']['sha256']}
        required.update({r['path']:r['sha256'] for r in admission['provenance']})
        if any(pins.get(k) != v for k,v in required.items()):
            raise AdmissionError('reviewed_source_evidence_coverage')
        from uuid import uuid5,NAMESPACE_URL
        if (state.get('windmill_job_id') != str(uuid5(NAMESPACE_URL,'offmenu:run:'+selected['operation_key']))
            or state.get('cancel_job_id') != str(uuid5(NAMESPACE_URL,'offmenu:cancel:'+selected['operation_key']))
            or state.get('logical_job_id') != operations.bridge_arguments(spec)['job_id']
            or type(state.get('cancel_requested')) is not bool):
            raise AdmissionError('reviewed_source_state')
        identity = digest(dict(entry=entry,selected=selected,spec=spec,inputs=pins))
        if identity != binding['identity']:
            raise AdmissionError('reviewed_source_binding')
        if spec['executor_sha256'] != file_sha(operations.__file__):
            # This qualifier cannot execute the historical module. Its hash stays
            # bound in the original spec/admission; only an authentic completed
            # command with presently qualified source can survive executor drift.
            # Apply in both modes: publication and fixed review also call the
            # default mode. Journal.tick retains strict fresh-execution admission.
            self._check_reviewed_terminal(spec, state, pins)
            admission = stage.qualify_reviewed_source(spec,selected['admission_path'])
        return runtime,spec,selected,state,admission

    def _check_reviewed_terminal(self, spec, state, pins):
        from stokowski_operations import bridge_arguments
        if (state.get('status') != 'succeeded' or state.get('cancel_requested') is not False
            or state.get('observation_intent') or state.get('reconcile_required')
            or state.get('accepted_output_sha256') != spec['outputs']
            or state.get('acceptance_sha256') != spec['acceptance_sha256']):
            raise AdmissionError('reviewed_source_terminal_required')
        # Only owner-selected regular input bytes (already hash checked above)
        # can supply the original receipt. A status string or a packet supplied
        # by a new reviewer is insufficient authority for this exemption.
        receipts = []
        for name in pins:
            try:
                receipt = read_record(name)
            except (ValueError,AdmissionError):
                continue
            if digest(receipt) == state.get('receipt_sha256'):
                receipts.append(receipt)
        if not receipts:
            raise AdmissionError('reviewed_source_terminal_receipt_missing')
        receipt = receipts[0]
        expected = bridge_arguments(spec)
        if (receipt.get('status') != 'succeeded' or type(receipt.get('exit_code')) is not int
            or receipt['exit_code'] != 0 or receipt.get('child_tree_gone') is not True
            or receipt.get('reconcile_required') is not False
            or receipt.get('job_id') != state['logical_job_id']
            or receipt.get('runner_sha256') != spec['runner_sha256']
            or receipt.get('capacity_policy_sha256') != spec['policy_sha256']
            or receipt.get('command_sha256') != hashlib.sha256(expected['command'].encode()).hexdigest()):
            raise AdmissionError('reviewed_source_terminal_receipt_binding')

    def stage_origin(self, issue, task):
        """Requalify the owner-pinned original; never manufacture stage receipts.

        Only an existing native v1 operation is supported. The original admission
        and its transitive immutable inputs remain authority, not a source path.
        Journal state stays mutable under its original operation lock.
        """
        import copy
        if task['stage_binding']['entry'].get('origin') == 'reviewed-source-v1':
            runtime, _, _, _, _ = self.reviewed_origin(issue,task,observation=True)
            return self, runtime, task['stage_binding']['identity']
        binding = task['stage_binding']
        entry = binding['entry']
        if (set(entry) != {'issue','issue_id','runtime','admission_sha256'}
            or entry['issue'] != issue or entry['issue_id'] != task['issue_id']
            or task['owner'] != self.config['owner']):
            raise AdmissionError('stage_original_identity')
        original = self.private(entry['runtime'])
        pins = binding['inputs']
        required = {str(original/name) for name in (
            'current-admission.json','manifest.json','requests/'+issue+'.json',
            'capacity-policy.json','installation.json','provider-proof.json',
            'validation-bindings.json','attempts/'+issue+'/dispatch-intent.json',
            'attempts/'+issue+'/intent.json','attempts/'+issue+'/receipt.json')}
        if not isinstance(pins, dict) or not required.issubset(pins):
            raise AdmissionError('stage_original_input_coverage')
        for name, sha in pins.items():
            path = Path(name)
            if not path.is_absolute() or path != path.resolve() or file_sha(path) != sha:
                raise AdmissionError('stage_original_input_drift')
        admission = read_record(original/'current-admission.json')
        if (pins[str(original/'current-admission.json')] != entry['admission_sha256']
            or any(pins.get(k) != v for k,v in admission['inputs'].items())):
            raise AdmissionError('stage_original_admission')
        manifest = load_manifest(original/'manifest.json', expected_branch=None)
        if 'stage' in manifest['tasks'][issue]:
            raise AdmissionError('stage_original_origin')
        # Reuse context, gate, continuation and review checks against the exact
        # original entry without rebinding the coordinator's durable catalog.
        view = copy.copy(self)
        view.read_only = True
        view.state = copy.deepcopy(self.state)
        view.entries = {issue: entry}
        view.state['references'] = {issue: entry}
        view.state['tasks'] = {issue: {}}
        runtime, identity = view.validation_binding(issue, entry)
        outputs = read_record(runtime/'attempts'/issue/'receipt.json')['output_sha256']
        if identity != binding['identity'] or set(task['input_paths']) != set(outputs):
            raise AdmissionError('stage_original_binding')
        return view, runtime, identity

    def gate_binding(self, issue, *, observation=False):
        """Validate native evidence, never infer unit review from parent status.

        unit_gate in current-owner.json is the local pending record. Its binding
        must be retained unchanged by the owner when setting disposition to
        approved/rework. No Linear comment or status is a unit disposition.
        """
        entry = self.entries.get(issue.identifier)
        if not entry or issue.id != entry['issue_id']:
            raise AdmissionError('current_gate_identity')
        runtime, manifest, _ = self.context(issue.identifier, review=True, observation=observation)
        task = manifest['tasks'][issue.identifier]
        if 'stage' in task and task['stage_binding']['entry'].get('origin') == 'reviewed-source-v1':
            _, spec, selected, _, admission = self.reviewed_origin(issue.identifier,task,observation=observation)
            return dict(project_id=PROJECT,issue_id=issue.id,origin='reviewed-source-v1',
                origin_admission_sha256=spec['origin']['admission_sha256'],
                operation_key=selected['operation_key'],owner=spec['owner'],author=admission['author'],
                authors=admission['authors'],head=spec['head'],base=spec['base'],outputs=spec['outputs'])
        if 'stage' in task:
            view, _, _ = self.stage_origin(issue.identifier, task)
            return view.gate_binding(issue)
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

    def validation_binding(self, issue, entry):
        """Qualify existing native v1 state without constructing a writable Journal.

        The owner-selected binding is authority; a coding receipt alone is not.
        Unsupported derivations/origins remain held for separate qualification.
        """
        from types import SimpleNamespace
        from contextlib import closing
        from uuid import uuid5, NAMESPACE_URL
        import stokowski_operations as operations
        import stokowski_stage as stage
        import stokowski_mcp as mcp
        runtime, manifest, source = self.context(issue, review=True, observation=True)
        task = manifest['tasks'][issue]
        if 'stage' in task:
            _, original, identity = self.stage_origin(issue, task)
            return original, digest(dict(stage=task, original_identity=identity))
        unit = self.gate_binding(SimpleNamespace(identifier=issue, id=entry['issue_id']))
        for module in (operations, stage, mcp):
            name = 'tools/delivery/'+Path(module.__file__).name
            accepted = subprocess.check_output(['git','-C',str(SOURCE),'show',
                                               self.config['source_head']+':'+name])
            if hashlib.sha256(accepted).hexdigest() != file_sha(module.__file__):
                raise AdmissionError('current_validation_executor_drift')
        path = runtime/'validation-bindings.json'
        database = runtime/'operations/operations.sqlite'
        for item in (path, database):
            if item != item.resolve() or not item.is_file():
                raise AdmissionError('current_validation_missing')
        bindings = read_record(path)
        if (set(bindings) != {'version','issues','history'} or type(bindings['version']) is not int
            or bindings['version'] != 1 or not isinstance(bindings['issues'], dict)
            or set(bindings['issues']) != {issue} or not isinstance(bindings['history'], list)
            or bindings['history']):
            raise AdmissionError('current_validation_schema')
        selected = bindings['issues'][issue]
        if (not isinstance(selected, dict) or set(selected) != {
            'operation_key','source_head','native_receipt_sha256','native_output_sha256',
            'derivation','derivation_reason'} or selected['derivation'] != {}
            or selected['derivation_reason'] is not None):
            raise AdmissionError('current_validation_origin')
        key = selected['operation_key']
        if not isinstance(key, str) or not re.fullmatch('[0-9a-f]{64}', key):
            raise AdmissionError('current_validation_key')
        with closing(sqlite3.connect(database.as_uri()+'?mode=ro', uri=True, timeout=1)) as db:
            row = db.execute('SELECT spec,state FROM operations WHERE key=?', (key,)).fetchone()
        if row is None:
            raise AdmissionError('current_validation_unbound')
        # Use the same duplicate-key rejecting reader semantics for stored JSON.
        def unique(pairs):
            result = {}
            for name, value in pairs:
                if name in result:
                    raise AdmissionError('current_validation_duplicate')
                result[name] = value
            return result
        spec, state = (json.loads(value, object_pairs_hook=unique) for value in row)
        operations.validated(spec)
        receipt = read_record(runtime/'attempts'/issue/'receipt.json')
        original = receipt.get('output_sha256')
        task = manifest['tasks'][issue]
        if (spec['version'] != 1 or operations.operation_key(spec) != key
            or row[0] != json.dumps(spec, sort_keys=True)
            or spec['issue'] != issue or spec['issue_id'] != entry['issue_id']
            or spec['owner'] != self.config['owner'] or task['owner'] != self.config['owner']
            or spec.get('branch','feature/langgraph-delivery-standardization') != manifest['branch']
            or selected['source_head'] != spec['head']
            or spec['base'] != manifest['base_revision']
            or spec['policy_sha256'] != self.config['policy_sha256']
            or spec['executor_sha256'] != file_sha(operations.__file__)
            or spec['runner_sha256'] != file_sha(SOURCE/'tools/delivery/windmill_runner.py')
            or receipt.get('scope_violations') != []
            or receipt.get('source_head') != manifest['base_revision']
            or not original or selected['native_output_sha256'] != original
            or selected['native_receipt_sha256'] != unit['native_receipt_sha256']
            or original != spec['outputs']
            or spec['acceptance_sha256'] != digest(dict(task=task,
                native_receipt_sha256=unit['native_receipt_sha256'], profile=spec['profile']))
            or not isinstance(state, dict)
            or state.get('windmill_job_id') != str(uuid5(NAMESPACE_URL, 'offmenu:run:'+key))
            or state.get('cancel_job_id') != str(uuid5(NAMESPACE_URL, 'offmenu:cancel:'+key))
            or state.get('logical_job_id') != operations.bridge_arguments(spec)['job_id']
            or type(state.get('cancel_requested')) is not bool
            or state.get('status') not in operations.TERMINAL | {
                'prepared','submit-intent','submitted','queued','running','unknown','cancel-requested'}):
            raise AdmissionError('current_validation_binding')
        workspace = runtime/'workspaces'/issue
        for args, expected in ((['rev-parse','HEAD'], manifest['base_revision']),
                               (['branch','--show-current'], manifest['branch'])):
            if subprocess.check_output(['git','-C',str(workspace),*args], text=True).strip() != expected:
                raise AdmissionError('current_validation_workspace')
        # Candidate objects belong to the task binding, independently of the
        # immutable coordinator checkout's branch, HEAD and working tree.
        candidate_repo = None
        for repository in dict.fromkeys((SOURCE, source)):
            try:
                subprocess.check_output(['git','-C',str(repository),'merge-base','--is-ancestor',
                                         spec['base'],spec['head']], stderr=subprocess.DEVNULL)
            except subprocess.CalledProcessError:
                continue
            candidate_repo = repository
            break
        if candidate_repo is None:
            raise AdmissionError('current_validation_candidate_ancestry')
        for name, sha in original.items():
            output = workspace/name
            if output != output.resolve() or file_sha(output) != sha:
                raise AdmissionError('current_validation_output')
            committed = subprocess.check_output(['git','-C',str(candidate_repo),'show',spec['head']+':'+name])
            if hashlib.sha256(committed).hexdigest() != sha:
                raise AdmissionError('current_validation_candidate_output')
        return runtime, digest(dict(unit=unit, selected=selected, spec=spec, bindings_sha256=file_sha(path)))

    async def continue_validation(self):
        """One bounded phase under the existing coordinator and operation locks."""
        import stokowski_stage as stage
        deadline = time.monotonic()+10
        entries = list(self.entries.items())
        cursor = self.state.get('validation_cursor')
        if cursor in self.entries:
            offset = next(i for i, (issue, _) in enumerate(entries) if issue == cursor)
            entries = entries[offset:]+entries[:offset]
        for index, (issue, entry) in enumerate(entries):
            if self.stopping or time.monotonic() >= deadline:
                return
            # Persist the next position before any effect, including a timeout
            # or cancellation, so a slow operation cannot monopolize reentry.
            self.state['validation_cursor'] = entries[(index+1) % len(entries)][0]
            self.save()
            task = self.state['tasks'].setdefault(issue, {})
            try:
                _, manifest, _ = self.context(issue, review=True, observation=True)
                selected_task = manifest['tasks'][issue]
                runtime, identity = self.validation_binding(issue, entry)
                if 'stage' in selected_task:
                    from types import SimpleNamespace
                    unit = self.gate_binding(SimpleNamespace(identifier=issue, id=entry['issue_id']), observation=True)
                    gate = task.setdefault('unit_gate', dict(binding=unit, disposition='waiting'))
                    if gate.get('binding') != unit:
                        raise AdmissionError('stage_gate_rebind')
                prior = task.get('validation', {})
                if prior.get('identity', identity) != identity:
                    raise AdmissionError('current_validation_rebind')
                if selected_task.get('stage') == 'review':
                    task['validation'] = dict(identity=identity, status='awaiting-independent-review',
                        requested_model=None, requested_effort=None, provider=None)
                    self.save()
                    continue
                task['validation'] = dict(identity=identity, status='pending',
                    requested_model=None, requested_effort=None, provider=None)
                self.save()  # Immutable selection survives owner loss before effects.
                projection = await asyncio.wait_for(stage.tick(runtime),
                                                    timeout=max(.001, deadline-time.monotonic()))
                status = projection['issues'][issue]['status']
                task['validation']['status'] = (status if status in {
                    'prepared','submit-intent','submitted','queued','running','unknown',
                    'cancel-requested','succeeded','failed','cancelled','refused','quarantined'} else 'held')
            except asyncio.CancelledError:
                raise
            except Exception:
                # No raw protocol errors, credentials or remote logs in owner state.
                task.setdefault('validation', dict(requested_model=None,
                    requested_effort=None, provider=None))['status'] = 'held'
            self.save()

    def unit_review_writer(self, trusted_transport=None):
        """Owner-only injected transport -> immutable local incoming observation.

        trusted_transport(envelope) must authenticate the existing integration
        owner's provenance and return its full packet (snapshot, decision,
        integration_binding, unit_binding, issue, validation_receipt). It is a
        deployment supplied trust boundary, NOT an authenticated:true assertion.
        The fixed stokowski_unit_review entrypoint supplies the local transport
        after checking retained controller qualification and kernel/file custody.
        Same-owner private OS/file custody is the trust boundary.
        This writer never takes coordinator.lock or writes current-owner.json.
        """
        if not callable(trusted_transport):
            raise AdmissionError('unit_review_trusted_transport_unsupported')

        def write(envelope):
            packet = trusted_transport(envelope)
            if (packet['snapshot'] != envelope['snapshot'] or
                packet['decision'] != envelope['decision']):
                raise AdmissionError('unit_review_transport_binding')
            self._check_unit_review(packet)
            path = self.runtime/('unit-review-' + packet['issue'] + '.json')
            raw = json.dumps(packet, sort_keys=True, separators=(',', ':')).encode()
            if path.exists():
                if path.is_symlink() or path.read_bytes() != raw:
                    raise AdmissionError('unit_review_conflicting_replay')
                return {'status':'retained', 'evidence_sha256':digest(packet)}
            # Atomic immutable publication: a crash before link leaves only a
            # private temp, after link leaves the complete durable intent. A
            # conflicting replay cannot overwrite it or any gate disposition.
            import tempfile
            fd, temporary = tempfile.mkstemp(prefix='.unit-review-', dir=self.runtime)
            try:
                os.fchmod(fd, 0o600)
                with os.fdopen(fd, 'wb') as stream:
                    stream.write(raw)
                    stream.flush()
                    os.fsync(stream.fileno())
                try:
                    os.link(temporary, path)
                except FileExistsError:
                    if path.is_symlink() or path.read_bytes() != raw:
                        raise AdmissionError('unit_review_conflicting_replay')
                directory = os.open(self.runtime, os.O_RDONLY | os.O_DIRECTORY)
                try:
                    os.fsync(directory)
                finally:
                    os.close(directory)
            finally:
                os.unlink(temporary)
            return {'status':'retained', 'evidence_sha256':digest(packet)}
        return write

    @staticmethod
    def _check_prior_review_provenance(review, admission, tree, pins):
        # Reuse only the exact admitted prior review. A packet's own hash
        # cannot qualify new reviewer identity or historical model metadata.
        prior = admission['review']
        pin = review.get('provenance_source')
        if (not isinstance(pin, dict) or set(pin) != {'path','sha256'} or
            pins.get(pin['path']) != pin['sha256']):
            raise AdmissionError('unit_review_provenance_unqualified')
        supplement = read_record(pin['path'])
        if file_sha(pin['path']) != pin['sha256']:
            raise AdmissionError('unit_review_provenance_drift')
        fields = ('reviewer','independent','verdict','findings','head','base','outputs',
                  'author','evidence_id','model','provider','requested_model',
                  'requested_provider','resolved_model','resolution_status')
        if (prior.get('decision') != 'accepted' or
            any(review.get(k) != prior.get(k) for k in ('reviewer','head','base','outputs')) or
            supplement.get('schema') != 'offmenu-independent-review-provenance-supplement/1' or
            supplement.get('retained_review') != dict(path=prior['path'],sha256=prior['sha256'],unchanged=True) or
            supplement.get('tree') != tree or supplement.get('authors') != admission['authors'] or
            any(k not in supplement or k not in review or supplement[k] != review[k] for k in fields) or
            any(not supplement.get(k) for k in ('reviewer_thread_id','review_turn_id','review_completed_at_utc'))):
            raise AdmissionError('unit_review_prior_review_provenance')

    def _check_unit_review(self, packet):
        from types import SimpleNamespace
        from stokowski_operations import operation_key, bridge_arguments
        issue = packet['issue']
        entry = self.entries[issue]
        unit = self.gate_binding(SimpleNamespace(identifier=issue, id=entry['issue_id']))
        runtime, manifest, _ = self.context(issue, review=True)
        task = manifest['tasks'][issue]
        reviewed = 'stage' in task and task['stage_binding']['entry'].get('origin') == 'reviewed-source-v1'
        if reviewed:
            runtime, origin_spec, _, _, admission = self.reviewed_origin(issue,task)
        elif 'stage' in task:
            view, _, _ = self.stage_origin(issue, task)
            return view._check_unit_review(packet)
        b, snapshot, decision = (packet[k] for k in ('integration_binding','snapshot','decision'))
        review, validation = snapshot['review'], snapshot['validation']
        action = decision.get('action') or {}
        standalone = decision.get('kind') == 'standalone-validation-review-v1'
        if standalone:
            # Explicit completed validation qualification, never Controller
            # history, a merge permission, or a replacement unit source identity.
            expected = dict(version=1, kind='standalone-validation-review-v1',
                status='standalone-validation-qualified', action=None, merge_effect='not-applicable',
                binding_sha256=digest(b), qualification_sha256=digest(dict(
                    validation=validation, review=review, tree=b['tree'], policy=b['policy_sha256'])))
            if (not reviewed or type(decision.get('version')) is not int or decision != expected or
                not review.get('requested_model') or not review.get('requested_provider') or
                review.get('resolution_status') not in ('observed','unknown') or
                (review['resolution_status'] == 'unknown' and review.get('resolved_model') is not None) or
                (review['resolution_status'] == 'observed' and not review.get('resolved_model'))):
                raise AdmissionError('unit_review_qualification')
            tree = subprocess.check_output(['git','-C',origin_spec['local_source_root'],
                'rev-parse',origin_spec['head']+'^{tree}'], text=True).strip()
            if tree != b['tree']:
                raise AdmissionError('unit_review_source_tree')
            self._check_prior_review_provenance(review, admission, tree, task['stage_binding']['inputs'])
        if (unit != packet['unit_binding'] or unit['project_id'] != PROJECT or
            b['issue_id'] != entry['issue_id'] or b['owner'] != self.config['owner'] or
            b['head_branch'] != (origin_spec['branch'] if reviewed else manifest['branch']) or snapshot.get('publisher_owner') != b['owner'] or
            decision.get('binding_sha256') != digest(b) or
            (not standalone and (decision.get('status') != 'merge-intent' or decision.get('merge_effect') != 'pending' or
            action.get('kind') != 'merge-pr' or action.get('expected_head_sha') != b['head'] or
            action.get('expected_base_sha') != b['base'])) or
            decision.get('qualification_sha256') != digest(dict(validation=validation, review=review,
                tree=b['tree'], policy=b['policy_sha256'])) or
            snapshot.get('cancel_requested') or snapshot.get('unresolved_findings') or
            snapshot.get('source_tree') != b['tree'] or snapshot.get('source_clean') is not True or
            snapshot.get('publication_triggers_actions') is not False or
            snapshot.get('policy_sha256') != b['policy_sha256'] or
            snapshot.get('capacity_policy_sha256') != b['capacity_policy_sha256'] or
            review.get('independent') is not True or review.get('verdict') != 'accept' or
            review.get('findings') or not review.get('evidence_id') or
            not review.get('reviewer') or not review.get('author') or
            review['reviewer'] == review['author'] or
            review['author'] != (admission['author'] if reviewed else manifest['tasks'][issue]['owner']) or
            (reviewed and (review['reviewer'] in admission['authors'] or
                          review['reviewer'] in {ref['owner'] for ref in admission['provenance']})) or
            not review.get('model') or not review.get('provider') or
            review.get('head') != b['head'] or review.get('base') != b['base'] or
            review.get('outputs') != b['outputs']):
            raise AdmissionError('unit_review_qualification')
        # Evidence hash covers immutable identity, reviewer/model and exact output.
        evidence = {k:v for k,v in review.items() if k != 'evidence_sha256'}
        if review.get('evidence_sha256') != digest(evidence):
            raise AdmissionError('unit_review_evidence')
        selected = read_record(runtime/'validation-bindings.json')['issues'][issue]
        key = b['validation_operation_key']
        database = self.private(str(runtime/'operations'/'operations.sqlite'))
        # Journal.__init__/db create/chmod: use the original schema read-only,
        # never prepare/save/reconcile an operation during review ingestion.
        with sqlite3.connect(database.as_uri()+'?mode=ro', uri=True) as db:
            row = db.execute('SELECT spec,state FROM operations WHERE key=?', (key,)).fetchone()
        if not row:
            raise AdmissionError('unit_review_journal_missing')
        spec, state = map(json.loads, row)
        if reviewed:
            receipt = packet['validation_receipt']
            expected = bridge_arguments(spec)
            if (spec != origin_spec or operation_key(spec) != key or spec['version'] != 3
                or any(spec[k] != b[k] for k in ('head','base','outputs','owner'))
                or spec['branch'] != b['head_branch'] or selected['operation_key'] != key
                or spec['policy_sha256'] != b['capacity_policy_sha256']
                or state.get('status') != 'succeeded' or state.get('cancel_requested') is not False
                or state.get('observation_intent') or state.get('reconcile_required')
                or state.get('accepted_output_sha256') != spec['outputs']
                or state.get('acceptance_sha256') != spec['acceptance_sha256']
                or state.get('receipt_sha256') != digest(receipt)
                or receipt.get('status') != 'succeeded' or receipt.get('exit_code') != 0
                or receipt.get('child_tree_gone') is not True or receipt.get('reconcile_required') is not False
                or receipt.get('job_id') != state['logical_job_id']
                or receipt.get('runner_sha256') != spec['runner_sha256']
                or receipt.get('capacity_policy_sha256') != spec['policy_sha256']
                or receipt.get('command_sha256') != hashlib.sha256(expected['command'].encode()).hexdigest()
                or validation != dict(operation_key=key,status='succeeded',head=spec['head'],base=spec['base'],
                    capacity_policy_sha256=spec['policy_sha256'],outputs=spec['outputs'],child_tree_gone=True,reconcile_required=False)):
                raise AdmissionError('unit_review_reviewed_source_validation')
            return unit
        native = read_record(runtime/'attempts'/issue/'receipt.json')
        expected_acceptance = digest(dict(task=manifest['tasks'][issue],
            native_receipt_sha256=unit['native_receipt_sha256'], profile=spec['profile']))
        receipt = packet['validation_receipt']
        expected = bridge_arguments(spec)
        if (operation_key(spec) != key or spec['version'] != 1 or
            spec['issue'] != issue or spec['issue_id'] != entry['issue_id'] or
            spec['owner'] != b['owner'] or spec.get('branch') != b['head_branch'] or
            any(spec[k] != b[k] for k in ('head','base','outputs')) or
            spec['policy_sha256'] != b['capacity_policy_sha256'] or
            spec['policy_sha256'] != self.config['policy_sha256'] or
            spec['acceptance_sha256'] != expected_acceptance or
            selected.get('operation_key') != key or selected.get('source_head') != b['head'] or
            selected.get('native_receipt_sha256') != unit['native_receipt_sha256'] or
            selected.get('native_output_sha256') != native.get('output_sha256') or
            selected.get('derivation') or native.get('scope_violations') or
            native.get('source_head') != manifest['base_revision'] or
            not native.get('output_sha256') or
            any(b['outputs'].get(k) != v for k,v in native['output_sha256'].items()) or
            state.get('status') != 'succeeded' or state.get('cancel_requested') is not False or
            state.get('reconcile_required') or state.get('observation_intent') or
            state.get('accepted_output_sha256') != b['outputs'] or
            state.get('acceptance_sha256') != expected_acceptance or
            state.get('receipt_sha256') != digest(receipt) or
            receipt.get('status') != 'succeeded' or receipt.get('exit_code') != 0 or
            receipt.get('child_tree_gone') is not True or receipt.get('reconcile_required') is not False or
            receipt.get('job_id') != state.get('logical_job_id') or
            receipt.get('runner_sha256') != spec['runner_sha256'] or
            receipt.get('capacity_policy_sha256') != spec['policy_sha256'] or
            receipt.get('command_sha256') != hashlib.sha256(expected['command'].encode()).hexdigest() or
            validation != dict(operation_key=key, status='succeeded', head=b['head'], base=b['base'],
                capacity_policy_sha256=spec['policy_sha256'], outputs=b['outputs'],
                child_tree_gone=True, reconcile_required=False)):
            raise AdmissionError('unit_review_validation_binding')
        workspace = runtime/'workspaces'/issue
        for name, sha in native['output_sha256'].items():
            target = (workspace/name).resolve()
            if not target.is_relative_to(workspace) or file_sha(target) != sha:
                raise AdmissionError('unit_review_native_output_drift')
        return unit

    def _hold_unit_review(self, issue):
        task = self.state['tasks'][issue]
        task['defer'] = 'unit_review_held'
        gate = task.get('unit_gate', {})
        if gate.get('review_sha256') and not gate.get('handled'):
            # Preserve the evidence identity for revalidation, but never leave
            # an unhandled evidence-derived approval actionable after a hold.
            gate.update(disposition='waiting', accepted_delivery=False)

    def _consume_unit_reviews(self):
        # Called by the normal current boundary under the coordinator's existing
        # exclusive root lock. Only this consumer updates current-owner.json;
        # the independent writer publishes immutable incoming evidence above.
        for issue in self.entries:
            path = self.runtime/('unit-review-' + issue + '.json')
            if not path.exists():
                if self.state['tasks'][issue].get('unit_gate', {}).get('review_sha256'):
                    self._hold_unit_review(issue)
                continue
            try:
                if path != path.resolve():
                    raise AdmissionError('unit_review_noncanonical_incoming')
                packet = read_record(path)
                unit = self._check_unit_review(packet)
                gate = self.state['tasks'][issue].get('unit_gate', {})
                fingerprint = digest(packet)
                if (packet['issue'] != issue or gate.get('binding') != unit or
                    gate.get('review_sha256') not in (None, fingerprint) or
                    gate.get('disposition') not in ('waiting','approved')):
                    raise AdmissionError('unit_review_gate_conflict')
                if gate.get('handled'):
                    continue
                gate.update(review_sha256=fingerprint, disposition='approved', accepted_delivery=False)
                if self.state['tasks'][issue].get('defer') == 'unit_review_held':
                    self.state['tasks'][issue].pop('defer')
            except Exception:
                self._hold_unit_review(issue)

    async def candidates(self, client, issues):
        self.refresh()
        selected = []
        for issue in issues:
            entry = self.entries.get(issue.identifier)
            if not entry or issue.id != entry['issue_id'] or issue.state not in ('Todo','In Progress'):
                continue
            try:
                _, selected_manifest, _ = self.context(issue.identifier)
                if 'stage' in selected_manifest['tasks'][issue.identifier]:
                    self.stage_origin(issue.identifier, selected_manifest['tasks'][issue.identifier])
                    continue
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
        if 'stage' in selected_manifest['tasks'][identifier]:
            raise AdmissionError('nonimplementation_workspace_refused')
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
            await current.continue_validation()
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
                current._successor_boundary()
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
                task = current.state['tasks'].get(identifier, {})
                if 'unit_gate' not in task:
                    # Receipt persistence can precede gate entry across owner loss.
                    # Reuse exact evidence checks and save before restoring memory.
                    await unit_enter_gate(owner, issue, 'evidence-pending')
                    continue
                gate = task['unit_gate']
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
            _, selected, _ = current.context(issue.identifier)
            task = selected['tasks'][issue.identifier]
            if 'stage' in task:
                current.stage_origin(issue.identifier, task)
                return 'evidence-pending', 1
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
        selected_runtime = (current.private(current.entries[issue.identifier]['runtime']) if current else runtime)
        selected = load_manifest(selected_runtime/'manifest.json', expected_branch=None)['tasks'][issue.identifier]
        if 'stage' in selected:
            raise AdmissionError('nonimplementation_worker_refused')
        if runner_type != 'codex' or claude_cfg.model != MODEL:
            raise AdmissionError('Only the reviewed existing Codex session route is admitted')
        if any(vars(hooks_cfg).get(k) for k in ('before_run', 'after_run', 'on_stage_enter')):
            raise AdmissionError('Unenforced shell validation hook rejected')
        task_runtime = runtime
        if current:
            task_runtime, selected_manifest, _ = current.context(issue.identifier)
            if workspace_path.resolve() != task_runtime/'workspaces'/issue.identifier:
                raise AdmissionError('current_workspace_binding')
        selected = (selected_manifest if current else manifest)['tasks'][issue.identifier]
        if 'stage' in selected:
            raise AdmissionError('nonimplementation_worker_refused')
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
