"""Pinned Stokowski orchestration with OffMenu ownership and Codex execution.

No global monkeypatches persist: these reviewed adaptations apply only inside
this OffMenu coordinator process. Arbitrary upstream shell hooks are disabled.
"""
import argparse
import asyncio
import errno
import fcntl
import hashlib
import importlib.metadata
import inspect
import json
import math
import sqlite3
import os
import re
import selectors
import stat
from pathlib import Path
import signal
import subprocess
import sys
import time
from uuid import UUID

from symphony_capacity import AdmissionError, digest
from symphony_tasks import (load_manifest, runtime_lease_ids, project_route,
                            validated_project_route)
from symphony_workspace import checkpoint
from stokowski_worker import child_environment, MODEL

SOURCE = Path(__file__).resolve().parents[2]
PIN = '339cbf4f3f6d9acdf808f9ba4c639d029cdd8e16'
PROJECT = 'ce60c1ab-a732-4a71-8471-14c9dc393886'
SLUG = 'ccd080f4f6f0'


PROTECTED_OWNER = Path('/etc/offmenu-stokowski-current')
_PROTECTED_CLOSURES = set()


def protected_owner_bytes(path):
    """Root-owned nonsecret input; no caller-selected root or secret read."""
    path = Path(path)
    if not path.is_absolute() or path != path.resolve():
        raise AdmissionError('protected_owner_path')
    for parent in path.parents:
        info = parent.lstat()
        if not stat.S_ISDIR(info.st_mode) or info.st_uid != 0 or info.st_mode & 0o022:
            raise AdmissionError('protected_owner_parent')
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    try:
        info = os.fstat(fd)
        if (not stat.S_ISREG(info.st_mode) or info.st_uid != 0 or info.st_nlink != 1
            or info.st_mode & 0o6022 or not 0 < info.st_size <= 8 * 1024 * 1024):
            raise AdmissionError('protected_owner_file')
        with os.fdopen(fd, 'rb', closefd=False) as stream:
            raw = stream.read(8 * 1024 * 1024 + 1)
        if len(raw) != info.st_size:
            raise AdmissionError('protected_owner_size')
        return raw
    finally:
        os.close(fd)


def protected_owner_tree(root):
    root = Path(root)
    for path in (root, *root.rglob('*')):
        info = path.lstat()
        if (info.st_uid != 0 or info.st_mode & 0o6022
            or not (stat.S_ISREG(info.st_mode) or stat.S_ISDIR(info.st_mode))
            or (stat.S_ISREG(info.st_mode) and info.st_nlink != 1)):
            raise AdmissionError('protected_owner_closure')
    for parent in root.parents:
        info = parent.lstat()
        if not stat.S_ISDIR(info.st_mode) or info.st_uid != 0 or info.st_mode & 0o022:
            raise AdmissionError('protected_owner_parent')


def protected_catalog_bytes(config, seed):
    """A sealed owner may grant a finite sequence of exact catalog snapshots.

    Only the private publication catalog is writable. The seed, grants and
    their digest remain root-owned; this grants no arbitrary catalog append.
    """
    versions = config.get('catalog_versions')
    if versions is None:
        if config.get('catalog') != str(PROTECTED_OWNER/'catalog.json'):
            raise AdmissionError('protected_owner_catalog')
        return seed
    root = Path(config['runtime_root'])
    path = Path(config['catalog'])
    coordinator = Path(json.loads(protected_owner_bytes(PROTECTED_OWNER/'binding.json'))['runtime'])
    if (root != root.resolve() or path != path.resolve() or not path.is_relative_to(root)
        or path.is_relative_to(coordinator) or not isinstance(versions, list)
        or not 1 <= len(versions) <= 32):
        raise AdmissionError('protected_owner_catalog_grants')
    previous = json.loads(seed)
    allowed = {hashlib.sha256(seed).hexdigest(): previous}
    for version in versions:
        if (not isinstance(version, dict) or set(version) != {'sha256','catalog'}
            or not isinstance(version['sha256'], str) or not re.fullmatch('[0-9a-f]{64}',version['sha256'])
            or version['sha256'] in allowed or not isinstance(version['catalog'], dict)
            or set(version['catalog']) != {'version','entries'} or version['catalog']['version'] != 1
            or not isinstance(version['catalog']['entries'],list)
            or len(version['catalog']['entries']) != len(previous['entries'])+1
            or version['catalog']['entries'][:-1] != previous['entries']):
            raise AdmissionError('protected_owner_catalog_grants')
        raw = (json.dumps(version['catalog'],sort_keys=True,indent=2)+'\n').encode()
        if hashlib.sha256(raw).hexdigest() != version['sha256']:
            raise AdmissionError('protected_owner_catalog_grants')
        allowed[version['sha256']] = version['catalog']
        previous = version['catalog']
    fd = os.open(path, os.O_RDONLY|os.O_NOFOLLOW)
    try:
        info = os.fstat(fd)
        if not stat.S_ISREG(info.st_mode) or info.st_size > 1048576:
            raise AdmissionError('protected_owner_catalog_snapshot')
        with os.fdopen(os.dup(fd),'rb') as stream:
            raw = stream.read(1048577)
    finally:
        os.close(fd)
    if len(raw)>1048576 or hashlib.sha256(raw).hexdigest() not in allowed:
        raise AdmissionError('protected_owner_catalog_snapshot')
    return raw


def current_config(runtime):
    """Select installed sealed owner inputs; legacy fixtures remain explicit.

    The service's root-owned unit sets OFFMENU_PROTECTED_OWNER_REQUIRED=1.
    Once the fixed binding exists, its matching runtime always uses it, including
    transport children which do not inherit that environment variable.
    """
    runtime = runtime.resolve()
    required = os.environ.get('OFFMENU_PROTECTED_OWNER_REQUIRED') == '1'
    binding_path = PROTECTED_OWNER/'binding.json'
    if not binding_path.exists():
        if required:
            raise AdmissionError('protected_owner_missing')
        return read_record(runtime/'current.json'), runtime/'current.json', None
    binding = json.loads(protected_owner_bytes(binding_path))
    if set(binding) != {'schema', 'runtime', 'config_sha256', 'catalog_sha256', 'source_root', 'python_sha256'}:
        raise AdmissionError('protected_owner_fields')
    if binding['runtime'] != str(runtime):
        if required:
            raise AdmissionError('protected_owner_runtime')
        return read_record(runtime/'current.json'), runtime/'current.json', None
    if (binding['schema'] != 'protected-current-owner-v1'
        or binding['source_root'] != str(SOURCE)
        or any(not isinstance(binding[key], str) or not re.fullmatch('[0-9a-f]{64}', binding[key])
               for key in ('config_sha256', 'catalog_sha256', 'python_sha256'))):
        raise AdmissionError('protected_owner_binding')
    config_path = PROTECTED_OWNER/'current.json'
    raw = protected_owner_bytes(config_path)
    catalog = protected_owner_bytes(PROTECTED_OWNER/'catalog.json')
    python = protected_owner_bytes(Path(sys.executable))
    if (hashlib.sha256(raw).hexdigest() != binding['config_sha256']
        or hashlib.sha256(catalog).hexdigest() != binding['catalog_sha256']
        or hashlib.sha256(python).hexdigest() != binding['python_sha256']):
        raise AdmissionError('protected_owner_digest')
    config = json.loads(raw)
    protected_catalog_bytes(config, catalog)
    closure = (str(SOURCE), sys.prefix, binding['python_sha256'])
    if closure not in _PROTECTED_CLOSURES:
        protected_owner_tree(SOURCE)
        protected_owner_tree(Path(sys.prefix))
        _PROTECTED_CLOSURES.add(closure)
    return config, config_path, binding


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
    optional project_route (exact reviewed project_id/project_slug pair; absent
    means legacy OffMenu), sealed project_routes (finite native routes with
    independent normal_intake pins), source_head, source_sha256 (repo-relative executable input hashes),
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
        self.config, self.config_path, self.owner_custody = current_config(runtime)
        if set(self.config) - {'qualified_successor', 'project_route', 'project_routes', 'completed_native_validations', 'normal_intake', 'native_review_policies', 'native_review_template', 'catalog_versions', 'native_harness_boundaries'} != {'version', 'owner', 'runtime_root', 'catalog',
                               'source_head', 'source_sha256', 'workflow_sha256', 'policy_sha256', 'installation_sha256'}:
            raise AdmissionError('current_config_fields')
        validated_project_route(self.config.get('project_route', project_route(PROJECT)))
        self.root = Path(self.config['runtime_root'])
        completed = self.config.get('completed_native_validations', {})
        native = self.config.get('native_review_policies', {})
        if not isinstance(native, dict):
            raise AdmissionError('current_native_review_fields')
        completed = dict(completed, **native) if isinstance(completed, dict) else completed
        if not isinstance(completed, dict):
            raise AdmissionError('current_completed_native_fields')
        for issue, ref in completed.items():
            if (not isinstance(issue, str) or not re.fullmatch(r'UIF-[1-9][0-9]*', issue)
                or not isinstance(ref, dict) or set(ref) != {'path', 'sha256'}
                or not isinstance(ref['path'], str) or not isinstance(ref['sha256'], str)
                or not re.fullmatch('[0-9a-f]{64}', ref['sha256'])):
                raise AdmissionError('current_completed_native_fields')
            self.private(ref['path'])
        if (self.root != self.root.resolve() or not self.root.is_dir()
            or self.root.name != 'stokowski' or self.root.parent.name != '.delivery'
            or not self.runtime.is_relative_to(self.root) or not self.config['owner']
            or type(self.config['version']) is not int or self.config['version'] != 1
            or not isinstance(self.config['owner'],str) or not self.config['owner'].strip()
            or not isinstance(self.config['source_sha256'],dict)
            or not re.fullmatch(r'[0-9a-f]{40}',self.config['source_head'])):
            raise AdmissionError('current_private_root')
        self._project_routes_config()
        self._native_harness_refill = None
        self._native_harness_config()
        if 'catalog_versions' in self.config and not self.owner_custody:
            raise AdmissionError('protected_owner_catalog_grants')
        self.catalog = Path(self.config['catalog']) if self.owner_custody else self.private(self.config['catalog'])
        self.config_sha = file_sha(self.config_path)
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
            catalog = self.catalog_record()
            if catalog.get('version') != 1 or not isinstance(catalog.get('entries'), list):
                raise AdmissionError('current_catalog_fields')
            for entry in self._active_catalog(catalog).values():
                issue = entry['issue']
                if (issue in self.entries or self.state['bindings'].get(issue) != digest(entry)
                    or self.state.get('references', {}).get(issue) != entry):
                    raise AdmissionError('current_identity_rebind')
                self.private(entry['runtime'])
                self.entries[issue] = entry
            if self.owner_custody and (not set(self.state.get('references', {})) <= set(self.entries)
                or not set(self.state.get('bindings', {})) <= set(self.entries)):
                raise AdmissionError('current_catalog_rollback')
        else:
            self.refresh()

    @property
    def route(self):
        return validated_project_route(self.config.get('project_route', project_route(PROJECT)))

    def _project_routes_config(self):
        """Only the sealed owner can admit additional native polling routes."""
        grants = self.config.get('project_routes')
        if 'project_routes' not in self.config:
            return
        if (not self.owner_custody or not isinstance(grants, list)
            or not 1 <= len(grants) <= 2 or 'normal_intake' in self.config):
            raise AdmissionError('current_project_routes_grant')
        seen = set()
        for grant in grants:
            if not isinstance(grant, dict) or set(grant) != {'project_id', 'project_slug', 'normal_intake'}:
                raise AdmissionError('current_project_routes_fields')
            route = validated_project_route({k: grant[k] for k in ('project_id', 'project_slug')})
            if route['project_id'] in seen:
                raise AdmissionError('current_project_routes_duplicate')
            seen.add(route['project_id'])
            ref = grant['normal_intake']
            if ref is not None:
                self._private_pin(ref)
        if self.route['project_id'] not in seen:
            raise AdmissionError('current_project_routes_primary')

    @property
    def routes(self):
        grants = self.config.get('project_routes')
        return ([self.route] if grants is None else
                [validated_project_route({k: g[k] for k in ('project_id', 'project_slug')}) for g in grants])

    def admitted_route(self, project_id):
        for route in self.routes:
            if route['project_id'] == project_id:
                return route
        raise AdmissionError('current_project_not_admitted')

    def _intake_ref(self, route):
        if self.config.get('project_routes') is None:
            return self.config.get('normal_intake')
        return next(g['normal_intake'] for g in self.config['project_routes']
                    if g['project_id'] == route['project_id'])

    def private(self, value):
        path = Path(value)
        if not path.is_absolute() or path != path.resolve() or not path.is_relative_to(self.root):
            raise AdmissionError('noncanonical_current_runtime')
        return path

    def save(self):
        if self.read_only:
            raise AdmissionError('current_read_only')
        checkpoint(self.state_path, self.state)

    def catalog_record(self):
        if not self.owner_custody:
            return read_record(self.catalog)
        raw = self.catalog_bytes()
        self._catalog_observed_sha256 = hashlib.sha256(raw).hexdigest()
        return json.loads(raw)

    def catalog_bytes(self):
        if not self.owner_custody:
            return self.catalog.read_bytes()
        return protected_catalog_bytes(self.config,protected_owner_bytes(PROTECTED_OWNER/'catalog.json'))

    def catalog_transition(self, before, after):
        """Authorize only the next root-granted edge before publication."""
        if not self.owner_custody:
            return
        self.guard()
        seed = protected_owner_bytes(PROTECTED_OWNER/'catalog.json')
        if protected_catalog_bytes(self.config,seed) != before:
            raise AdmissionError('protected_owner_catalog_transition')
        previous = hashlib.sha256(seed).hexdigest()
        selected = (hashlib.sha256(before).hexdigest(),hashlib.sha256(after).hexdigest())
        for version in self.config.get('catalog_versions', []):
            if selected == (previous,version['sha256']):
                return
            previous = version['sha256']
        raise AdmissionError('protected_owner_catalog_transition')

    def guard(self):
        c = self.config
        if (file_sha(self.runtime/'installation.json') != c['installation_sha256']):
            raise AdmissionError('current_installation_binding')
        verify_install(self.runtime)
        selected, path, custody = current_config(self.runtime)
        if (selected != self.config or path != self.config_path or custody != self.owner_custody
            or file_sha(path) != self.config_sha):
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

    def _replacement_witness(self, previous, entry, *, manifest=None, request_sha256=None):
        """A sealed append grants one new unit, never a retry of its old lease."""
        import stokowski_replacement as replacement
        module = 'tools/delivery/stokowski_replacement.py'
        if (not self.owner_custody or not self.config.get('catalog_versions')
            or self.config['source_sha256'].get(module) != file_sha(replacement.__file__)):
            raise AdmissionError('replacement_owner_grant_required')
        if (entry['issue'] != previous['issue'] or entry['issue_id'] != previous['issue_id']
            or entry['runtime'] == previous['runtime']):
            raise AdmissionError('replacement_identity')
        runtime = self.private(entry['runtime'])
        policy = read_record(SOURCE/'tools/delivery/capacity-policy.json')
        witness = replacement.refusal_witness(previous, entry['replacement_of'], root=self.root,
            owner=self.config['owner'], policy=policy, policy_sha256=self.config['policy_sha256'])
        if manifest is None:
            admission = replacement.record(runtime/'current-admission.json', self.root, entry['admission_sha256'])
            if (admission['owner'] != self.config['owner'] or admission['issue'] != entry['issue']
                or admission['issue_id'] != entry['issue_id']
                or admission['policy_sha256'] != self.config['policy_sha256']):
                raise AdmissionError('replacement_new_admission')
            manifest = replacement.record(runtime/'manifest.json', self.root, admission['manifest_sha256'])
            request_sha256 = admission['request_sha256']
            replacement.record(runtime/'requests'/(entry['issue']+'.json'), self.root, request_sha256)
        if (set(manifest['tasks']) != {entry['issue']}
            or manifest['tasks'][entry['issue']]['issue_id'] != entry['issue_id']
            or manifest['tasks'][entry['issue']]['owner'] != self.config['owner']
            or manifest['project_id'] != witness['project_id']
            or not any(r['project_id'] == manifest['project_id'] for r in self.routes)
            or request_sha256 == witness['request_sha256']
            or runtime_lease_ids(runtime, manifest)[entry['issue']] == witness['lease']):
            raise AdmissionError('replacement_new_identity')
        return witness

    def _active_catalog(self, catalog):
        """Keep the raw append history; derive one validated active issue view."""
        fields = {'issue','issue_id','runtime','admission_sha256'}
        for entry in catalog['entries']:
            if not isinstance(entry, dict) or set(entry) not in (fields, fields | {'replacement_of'}):
                raise AdmissionError('current_entry_fields')
            if (not isinstance(entry['issue'], str) or not re.fullmatch(r'UIF-[1-9][0-9]*',entry['issue'])
                or str(UUID(entry['issue_id'])) != entry['issue_id']
                or not re.fullmatch('[0-9a-f]{64}',entry['admission_sha256'])):
                raise AdmissionError('current_entry_identity')
            self.private(entry['runtime'])
        if not any('replacement_of' in entry for entry in catalog['entries']):
            entries, identities, runtimes = {}, set(), set()
            for entry in catalog['entries']:
                if entry['issue'] in entries or entry['issue_id'] in identities or entry['runtime'] in runtimes:
                    raise AdmissionError('current_identity_rebind')
                entries[entry['issue']] = entry
                identities.add(entry['issue_id'])
                runtimes.add(entry['runtime'])
            return entries
        import stokowski_replacement as replacement
        try:
            return replacement.active_entries(catalog, self._replacement_witness)
        except AdmissionError as error:
            if str(error) in ('replacement_identity_rebind','replacement_runtime_reuse','replacement_chain'):
                raise AdmissionError('current_identity_rebind') from error
            raise

    def _generation_transition(self, issue, entry):
        """Validate and capture a transition without mutating retained state."""
        previous = self.state.get('references', {}).get(issue)
        if (previous is None or 'replacement_of' not in entry
            or entry['replacement_of']['entry_sha256'] != digest(previous)):
            raise AdmissionError('current_identity_rebind')
        witness = self._replacement_witness(previous, entry)
        history = self.state.get('replacement_history', [])
        if any(item['entry_sha256'] == digest(previous) for item in history):
            raise AdmissionError('replacement_transition_repeated')
        # Retain this unit only; never copy Linear descriptions or chat history.
        return dict(issue=issue, entry=previous, entry_sha256=digest(previous),
            binding_sha256=self.state['bindings'][issue],
            task=json.loads(json.dumps(self.state['tasks'].get(issue, {}))),
            refusal=witness, replacement_entry_sha256=digest(entry))

    def refresh(self):
        try:
            self.guard()
            catalog = self.catalog_record()
            if set(catalog) != {'version', 'entries'} or type(catalog['version']) is not int or catalog['version'] != 1 or not isinstance(catalog['entries'], list):
                raise AdmissionError('current_catalog_fields')
            entries = self._active_catalog(catalog)
            # Validate the whole active view before changing any state binding.
            transitions = []
            for issue, entry in entries.items():
                previous = self.state['bindings'].get(issue)
                if previous is not None and previous != digest(entry):
                    transitions.append(self._generation_transition(issue, entry))
                if any(v['issue_id'] == entry['issue_id'] or v['runtime'] == entry['runtime']
                       for k, v in self.state.get('references', {}).items() if k != issue):
                    raise AdmissionError('current_identity_rebind')
            if self.owner_custody and (not set(self.state.get('references', {})) <= set(entries)
                or not set(self.state.get('bindings', {})) <= set(entries)):
                raise AdmissionError('current_catalog_rollback')
            for transition in transitions:
                self.state.setdefault('replacement_history', []).append(transition)
                self.state['tasks'][transition['issue']] = {}
            for issue, entry in entries.items():
                self.state['bindings'][issue] = digest(entry)
                self.state.setdefault('references', {})[issue] = entry
            self.entries = entries
            self.state['catalog_sha256'] = self._catalog_observed_sha256 if self.owner_custody else file_sha(self.catalog)
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

    def _intake_policy(self, route=None):
        route = self.admitted_route((route or self.route)['project_id'])
        ref = self._intake_ref(route)
        if ref is None:
            raise AdmissionError('intake_disabled: owner must pin normal_intake policy')
        policy = self._private_pin(ref)
        if (set(policy) != {'schema', 'enabled', 'owner', 'source_head', 'project_route',
                            'expires_at', 'references', 'resources', 'timeout_seconds'}
            or policy['schema'] != 'offmenu-normal-intake/1' or policy['enabled'] is not True
            or policy['owner'] != self.config['owner']
            or policy['source_head'] != self.config['source_head'] or policy['project_route'] != route
            or type(policy['expires_at']) not in (int, float)
            or not math.isfinite(policy['expires_at']) or policy['expires_at'] < time.time()
            or type(policy['timeout_seconds']) is not int or not 1 <= policy['timeout_seconds'] <= 60
            or not isinstance(policy['references'], dict) or not policy['references']):
            raise AdmissionError('intake_policy_binding')
        return policy

    def _private_pin(self, ref):
        if (not isinstance(ref, dict) or set(ref) != {'path', 'sha256'}
            or not isinstance(ref['sha256'], str) or not re.fullmatch('[0-9a-f]{64}', ref['sha256'])):
            raise AdmissionError('intake_reference_schema')
        path = self.private(ref['path'])
        if file_sha(path) != ref['sha256']:
            raise AdmissionError('intake_reference_drift')
        return read_record(path)

    def _intake_authority(self, reference, route=None):
        route = self.admitted_route((route or self.route)['project_id'])
        policy = self._intake_policy(route)
        authority = self._private_pin(policy['references'][reference])
        if (set(authority) - {'replacement_of'} != {'schema', 'owner', 'source_head', 'issue', 'issue_id', 'project_id',
                              'accepted_scope', 'acceptance', 'dependencies', 'decision', 'handoff',
                              'qualification'}
            or authority['schema'] != 'offmenu-intake-authority/1'
            or authority['owner'] != self.config['owner']
            or authority['source_head'] != self.config['source_head']
            or authority['project_id'] != route['project_id']
            or not isinstance(authority['accepted_scope'], list) or not authority['accepted_scope']
            or any(not isinstance(name, str) or not name.strip() for name in authority['accepted_scope'])
            or not isinstance(authority['acceptance'], list) or not authority['acceptance']
            or any(not isinstance(item, str) or not item.strip() for item in authority['acceptance'])
            or authority['decision'] not in ('owner-qualified', 'qualification-only')
            or ('replacement_of' in authority and (authority['decision'] != 'owner-qualified'
                or not isinstance(authority['replacement_of'], dict)))):
            raise AdmissionError('intake_owner_scope_or_decision')
        return policy, authority

    def _trusted_handoff(self, ref, packet):
        if self.config.get('qualified_successor') == ref:
            return True
        for record in self.state.get('intake', {}).values():
            if record.get('status') != 'qualified' or record.get('handoff') != ref:
                continue
            _, authority = self._intake_authority(record['reference'],
                self.admitted_route(record['authority']['project_id']))
            if (authority['decision'] == 'owner-qualified' and authority['handoff'] == ref
                and record['authority'] == authority and time.time() - record['checked_at'] <= 120
                and packet['execution_outcome'] == dict(identifier=authority['issue'],
                    uuid=authority['issue_id'], project_id=authority['project_id'])
                and packet['scope'] == authority['accepted_scope']
                and packet['acceptance'] == authority['acceptance']
                and packet['source']['base'] == authority['source_head']
                and ('replacement_of' in packet) == ('replacement_of' in authority)
                and packet.get('replacement_of') == authority.get('replacement_of')):
                return True
        return False

    async def _intake(self, client, issue, route=None):
        route = self.admitted_route((route or self.route)['project_id'])
        if not re.fullmatch(r'UIF-[1-9][0-9]*', issue.identifier):
            return
        records = self.state.setdefault('intake', {})
        record = records.setdefault(issue.identifier, dict(issue_id=issue.id))
        try:
            self.guard()
            if record['issue_id'] != issue.id:
                raise AdmissionError('intake_identity_drift')
            if self.stopping or (self.runtime/'cancel.json').exists():
                raise AdmissionError('intake_cancelled')
            self._intake_policy(route)
            remote = (await client._graphql(
                'query($id: String!){issue(id:$id){id identifier description project{id} state{name} '
                'inverseRelations{nodes{type issue{id state{name}}}}}}', {'id': issue.id})).get('issue') or {}
            if (remote.get('id') != issue.id or remote.get('identifier') != issue.identifier
                or remote.get('project', {}).get('id') != route['project_id']
                or remote.get('state', {}).get('name') not in ('Todo', 'In Progress')):
                raise AdmissionError('intake_authoritative_identity_or_state')
            matches = re.findall(r'```offmenu-intake\s*\n(.*?)\n```', remote.get('description') or '', re.S)
            if len(matches) != 1:
                raise AdmissionError('intake_reference_missing: qualified owner must supply offmenu-intake reference')
            def unique(pairs):
                value = {}
                for key, item in pairs:
                    if key in value:
                        raise AdmissionError('intake_duplicate_key')
                    value[key] = item
                return value
            supplied = json.loads(matches[0], object_pairs_hook=unique)
            if (not isinstance(supplied, dict) or set(supplied) != {'schema', 'reference'}
                or supplied['schema'] != 'offmenu-intake-reference/1'
                or not isinstance(supplied['reference'], str)):
                raise AdmissionError('intake_reference_schema')
            policy, authority = self._intake_authority(supplied['reference'], route)
            dependencies = sorted([dict(id=n['issue']['id'], state=n['issue']['state']['name'])
                for n in remote['inverseRelations']['nodes'] if n['type'] == 'blocks'], key=lambda n:n['id'])
            if (authority['issue'] != issue.identifier or authority['issue_id'] != issue.id
                or dependencies != authority['dependencies']
                or any(d['state'] != 'Done' for d in dependencies)):
                raise AdmissionError('intake_identity_or_dependency_drift')
            if record.get('authority') not in (None, authority):
                previous = record['authority']
                stable = set(authority) - {'decision', 'handoff', 'qualification'}
                result_ref = record.get('qualification_result', {})
                result = read_record(result_ref['path']) if result_ref else {}
                if (previous['decision'] == authority['decision'] == 'owner-qualified'
                    and 'replacement_of' in authority):
                    handoff = self._private_pin(authority['handoff'])
                    packet = self._private_pin(handoff['task_packet'])
                    if (packet.get('replacement_of') != authority['replacement_of']
                        or packet['owner_config'] != handoff['owner_config']):
                        raise AdmissionError('replacement_intake_binding')
                    _, _, witness = self._qualified_replacement(packet)
                    record.setdefault('replacement_history', []).append(dict(
                        reference=record['reference'], authority=previous,
                        handoff=record.get('handoff'), refusal=witness))
                else:
                    if (previous['decision'] != 'qualification-only' or authority['decision'] != 'owner-qualified'
                        or any(previous[k] != authority[k] for k in stable)
                        or not result_ref or file_sha(result_ref['path']) != result_ref['sha256']
                        or result.get('child_tree_gone') is not True or result.get('status') != 'succeeded'):
                        raise AdmissionError('intake_authority_drift: owner reconciliation required')
                    capacity = read_record(self.runtime/'capacity-policy.json')
                    database = Path(capacity['symphony']['pool_path'])/'state.sqlite'
                    with sqlite3.connect(database.as_uri()+'?mode=ro', uri=True) as db:
                        lease = db.execute('SELECT status,outcome FROM leases WHERE id=?', (result['lease'],)).fetchone()
                    if lease != ('finished', 'succeeded'):
                        raise AdmissionError('intake_qualification_lease_unreconciled')
                    record.setdefault('qualification_history', []).append(dict(authority=previous,
                        reference=record['reference'], result=result_ref, intent=record['qualification_intent']))
            record.update(reference=supplied['reference'], authority=authority, checked_at=time.time(),
                          authoritative=remote, required_actor=self.config['owner'])
            if authority['decision'] == 'qualification-only':
                self._qualification_boundary(record, policy, authority)
            else:
                handoff = self._private_pin(authority['handoff'])
                packet = self._private_pin(handoff['task_packet'])
                record.update(status='qualified', handoff=authority['handoff'])
                record.pop('reason', None)
                record.pop('required_input', None)
                if not self._trusted_handoff(authority['handoff'], packet):
                    raise AdmissionError('intake_handoff_scope_or_source_drift')
                self.state['intake_handoff'] = authority['handoff']
                self._successor_boundary()
                if self.state.get('successor_hold'):
                    record['reason'] = self.state['successor_hold']
                    # Waiting for the native consumer does not revoke the exact
                    # fresh owner authority it must recheck under that permit.
                    if record['reason'] != 'AdmissionError: native_harness_refill_readback_required':
                        record['status'] = 'held'
        except Exception as error:
            record.update(status='held', reason=str(error), required_actor=self.config['owner'],
                          required_input='fresh owner-qualified private authority and exact accepted scope/handoff')
        self.save()

    def _qualification_boundary(self, record, policy, authority):
        # One finite worker process, observed only at native poll boundaries.
        # Persist launch intent before Popen; an unknown launch is never retried.
        module = 'tools/delivery/symphony_launch.py'
        if self.config['source_sha256'].get(module) != file_sha(SOURCE/module):
            raise AdmissionError('qualification_provider_source_pin')
        qualification = authority['qualification']
        spec = self._private_pin(qualification)
        if (set(spec) != {'workspace', 'branch', 'head', 'prompt', 'resources', 'output'}
            or spec['resources'] != policy['resources'] or spec['head'] != authority['source_head']
            or spec['output'] != 'qualification-output.json'
            or not isinstance(spec['prompt'], str) or not spec['prompt'].strip()):
            raise AdmissionError('intake_qualification_spec')
        workspace = self.private(spec['workspace'])
        directory = workspace/'qualification-runtime'
        result_path = directory/'result.json'
        if record.get('qualification_intent'):
            child = getattr(self, '_qualification_children', {}).get(str(directory))
            if child is not None and child.poll() is not None:
                child.wait()
            if result_path.exists():
                result = read_record(result_path)
                record['qualification_result'] = dict(path=str(result_path), sha256=file_sha(result_path), record=result)
            raise AdmissionError('qualification_proposal_requires_owner_handoff; retained intent forbids replay')
        directory.mkdir(mode=0o700, parents=False, exist_ok=False)
        record['qualification_intent'] = dict(spec=qualification, directory=str(directory), at=time.time())
        self.save()
        # No credentials or JSON callbacks; child reopens pinned owner config.
        child = subprocess.Popen([sys.executable, str(SOURCE/'tools/delivery/stokowski_adapter.py'),
            '--runtime', str(self.runtime), '--qualification-reference', record['reference']],
            cwd=SOURCE, env=child_environment(os.environ), stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
        if not hasattr(self, '_qualification_children'):
            self._qualification_children = {}
        self._qualification_children[str(directory)] = child
        record['qualification_intent']['pid'] = child.pid
        raise AdmissionError('qualification_proposal_pending: owner handoff required before publication')

    def _scope_reusable(self, issue):
        # Only an archived published request may release its exact prior scope.
        for prior in self.state.get('successor_history', []):
            handoff = self._private_pin(prior['handoff'])
            packet = self._private_pin(handoff['task_packet'])
            if packet['execution_outcome']['identifier'] == issue:
                return self._reconciled_unit(issue)
        return False

    def _reconciled_unit(self, issue):
        try:
            if not self._native_harness_refill_allowed(issue):
                return False
            from types import SimpleNamespace
            entry = self.state['references'][issue]
            gate = self.state['tasks'][issue]['unit_gate']
            if (gate.get('handled') is not True or gate.get('unit_review') != 'approved'
                or gate.get('disposition') != 'approved'):
                return False
            runtime, manifest, _ = self.context(issue, review=True)
            task = manifest['tasks'][issue]
            operations = runtime/'operations'/'operations.sqlite'
            if operations.exists():
                with sqlite3.connect(operations.as_uri()+'?mode=ro', uri=True) as db:
                    effects = [json.loads(row[0]) for row in db.execute('SELECT state FROM operations')]
                if any(effect.get('status') not in ('succeeded', 'failed')
                       or effect.get('cancel_requested') or effect.get('reconcile_required')
                       or effect.get('observation_intent') for effect in effects):
                    return False
            if 'stage' not in task:
                lease = runtime_lease_ids(runtime, manifest)[issue]
                policy = read_record(runtime/'capacity-policy.json')
                database = Path(policy['symphony']['pool_path'])/'state.sqlite'
                with sqlite3.connect(database.as_uri()+'?mode=ro', uri=True) as db:
                    row = db.execute('SELECT status,outcome FROM leases WHERE id=?', (lease,)).fetchone()
                if row != ('finished', 'succeeded'):
                    return False
            review = read_record(self.runtime/('unit-review-' + issue + '.json'))
            return (digest(review) == gate['review_sha256']
                and self._check_unit_review(review) == gate['binding']
                and self.gate_binding(SimpleNamespace(identifier=issue, id=entry['issue_id']),
                                     observation=True) == gate['binding'])
        except Exception:
            return False

    def _check_published_native_request(self, pending):
        import stokowski_native_publication as native
        # Native custody has its own protected root, outside the coordinator
        # runtime. Select only the exact operation path; never widen private().
        ref = pending['publication_result']
        legacy_seal = SOURCE/'.delivery/native-ssh-publication'/(pending['handoff']['sha256']+'.json')
        if self.owner_custody and ref['path']==str(legacy_seal):
            # The installed migration sealed this exact historical record.
            raw=protected_owner_bytes(legacy_seal)
            expected=legacy_seal
        else:
            expected = native.custody_directory(SOURCE,pending['native_request']['context'])/(pending['handoff']['sha256']+'.json')
            raw=native.read(native.canonical(str(expected)))
        if ref['path'] != str(expected) or hashlib.sha256(raw).hexdigest() != ref['sha256']:
            raise AdmissionError('successor_prior_publication_unreconciled')
        custody = native.decode(raw)
        self._private_pin(pending['publication_journal'])
        if (custody.get('request') != pending['native_request']
            or custody.get('binding') != pending['native_binding']
            or custody.get('result', {}).get('status') not in ('published', 'duplicate')):
            raise AdmissionError('successor_prior_publication_unreconciled')

    def _rearm_successor(self, pending, replacement_packet=None):
        replacing = replacement_packet is not None
        if pending.get('status') not in (('published','duplicate','held') if replacing else ('published','duplicate')):
            raise AdmissionError('successor_request_rebind')
        if 'native_request' in pending:
            self._check_published_native_request(pending)
        handoff = self._private_pin(pending['handoff'])
        packet = self._private_pin(handoff['task_packet'])
        issue = packet['execution_outcome']['identifier']
        history = json.loads(json.dumps(pending))
        if replacing:
            previous, _, witness = self._qualified_replacement(replacement_packet)
            if ('native_request' not in pending or issue != previous['issue']
                or packet['execution_outcome']['uuid'] != previous['issue_id']
                or packet['selected_current']['task_runtime'] != previous['runtime']):
                raise AdmissionError('replacement_prior_publication')
            history['terminal_refusal'] = witness
            history['disposition'] = 'confirmed-prelaunch-refusal-retained'
        else:
            if not self._reconciled_unit(issue):
                raise AdmissionError('successor_prior_unit_unreconciled')
            review = self.runtime/('unit-review-' + issue + '.json')
            history['terminal_review'] = dict(path=str(review), sha256=file_sha(review))
            history['terminal_unit'] = self.state['tasks'][issue]['unit_gate']['binding']
        self.state.setdefault('successor_history', []).append(history)
        # History retains the immutable nonce/context/admission/result references.
        self.state.pop('successor_request')
        self.state.pop('successor_hold', None)
        self.save()

    def _successor_entry(self, packet):
        admission = dict(version=1, owner=self.config['owner'],
            issue=packet['execution_outcome']['identifier'], issue_id=packet['execution_outcome']['uuid'],
            source=packet['source']['source_checkout'], manifest_sha256=packet['manifest']['sha256'],
            request_sha256=packet['request']['sha256'], policy_sha256=self.config['policy_sha256'],
            installation_sha256=self.config['installation_sha256'],
            inputs={k:v for k,v in packet['inputs'].items() if k != str(self.catalog)})
        raw = (json.dumps(admission,sort_keys=True,indent=2)+'\n').encode()
        entry = dict(issue=admission['issue'], issue_id=admission['issue_id'],
            runtime=packet['selected_current']['task_runtime'], admission_sha256=hashlib.sha256(raw).hexdigest())
        if 'replacement_of' in packet:
            entry['replacement_of'] = packet['replacement_of']
        return entry

    def _qualified_replacement(self, packet):
        """Bind a new task to the exact next sealed edge before publication."""
        outcome = packet['execution_outcome']
        previous = self.state.get('references', {}).get(outcome['identifier'])
        if (previous is None or previous['issue_id'] != outcome['uuid']
            or self.state['bindings'].get(outcome['identifier']) != digest(previous)
            or self.entries.get(outcome['identifier'], previous) != previous):
            raise AdmissionError('replacement_previous_identity')
        entry = self._successor_entry(packet)
        manifest = self._private_pin(packet['manifest'])
        witness = self._replacement_witness(previous, entry, manifest=manifest,
                                            request_sha256=packet['request']['sha256'])
        if outcome['project_id'] != witness['project_id']:
            raise AdmissionError('replacement_project')
        before = self.catalog_bytes()
        catalog = json.loads(before)
        if self._active_catalog(catalog).get(outcome['identifier']) != previous:
            raise AdmissionError('replacement_previous_identity')
        after = (json.dumps(dict(version=1, entries=catalog['entries']+[entry]),
                            sort_keys=True,indent=2)+'\n').encode()
        self.catalog_transition(before, after)
        return previous, entry, witness

    def _successor_scope_reusable(self, entry, packet):
        if ('replacement_of' in packet
            and packet['replacement_of'].get('entry_sha256') == digest(entry)):
            previous, _, _ = self._qualified_replacement(packet)
            return previous == entry
        return self._scope_reusable(entry['issue'])

    def qualify_successor(self, handoff_ref, packet, owner_config):
        """Read-only qualification; current.json is trusted out of band.

        The exact handoff pin transitively allows source/config/owner/request/
        scope/resources. Packet assertions alone never grant this origin.
        """
        from types import SimpleNamespace
        self.guard()
        if (not self._trusted_handoff(handoff_ref, packet)
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
        catalog = self.catalog_record()
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
        replacement = 'replacement_of' in packet
        previous = self._qualified_replacement(packet)[0] if replacement else None
        if (not any(r['project_id'] == outcome['project_id'] for r in self.routes)
            or outcome['identifier'] == issue
            or outcome['uuid'] == entry['issue_id']
            or any((e['issue'] == outcome['identifier'] or e['issue_id'] == outcome['uuid']
                    or e['runtime'] == packet['selected_current']['task_runtime'])
                   and not (replacement and e == previous
                            and e['runtime'] != packet['selected_current']['task_runtime'])
                   for e in self.state.get('references', {}).values())):
            raise AdmissionError('successor_identity_collision')
        return digest(dict(handoff=handoff_ref, owner_config=packet['owner_config'], trigger=trigger))

    def _successor_task(self, packet, config):
        """Reuse the producer's staged owner/origin checks before any rearm."""
        pinned = self._private_pin(packet['manifest'])
        manifest = load_manifest(packet['manifest']['path'], expected_head=packet['source']['base'],
                                 expected_branch=packet['source']['branch'])
        issue = packet['execution_outcome']['identifier']
        if (manifest != pinned or set(manifest['tasks']) != {issue}
            or manifest['project_id'] != packet['execution_outcome']['project_id']):
            raise AdmissionError('successor_task_binding')
        task = manifest['tasks'][issue]
        staged = 'stage' in task
        if not staged and ('stage' in packet or 'stage_binding' in config):
            raise AdmissionError('successor_stage_binding')
        if (task['issue_id'] != packet['execution_outcome']['uuid']
            or (task['input_paths'] if staged else task['allowed_paths']) != packet['scope']
            or task['resources'] != packet['resources'] or task['owner'] != self.config['owner']
            or task['acceptance'] != packet['acceptance']):
            raise AdmissionError('successor_task_binding')
        if staged:
            if (task['allowed_paths'] != [] or config.get('stage_binding') != task['stage_binding']
                or packet.get('stage') != task['stage']
                or any(packet['inputs'].get(k) != v for k,v in task['stage_binding']['inputs'].items())):
                raise AdmissionError('successor_stage_binding')
            self.stage_origin(issue, task)
        return manifest, task

    def _successor_boundary(self):
        # This service has Linear credentials only. Authentication/publication
        # remains with the existing GitHub owner; no automatic association exists.
        ref = self.state.get('intake_handoff') or self.config.get('qualified_successor')
        if ref is None:
            self.state['intake_no_ready_reason'] = 'owner-qualified intake/reference required'
            return
        pending = self.state.get('successor_request')
        rearming = False
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
            if not self._native_harness_refill_allowed(packet['trigger']['issue']):
                raise AdmissionError('native_harness_refill_readback_required')
            identity = digest(dict(handoff=ref, owner_config=packet['owner_config'], trigger=packet['trigger']))
            rearming = pending is not None and pending.get('identity') != identity
            if rearming or pending is None:
                _, task = self._successor_task(packet, config)
                if 'stage' in task:
                    # Qualify the incoming unit before the old published request
                    # can be archived. Nothing here creates a coding admission.
                    self.qualify_successor(ref, packet, config)
                    for name, sha in packet['inputs'].items():
                        path = Path(name)
                        if not path.is_absolute() or path != path.resolve() or file_sha(path) != sha:
                            raise AdmissionError('successor_input_drift')
                    if 'native_publication' in config:
                        self._native_publication_context(ref, handoff, packet, config)
                    from stokowski_prepare import _publication_bytes
                    before = self.catalog_bytes()
                    catalog = read_record(self.catalog) if not self.owner_custody else json.loads(before)
                    after = dict(version=1, entries=catalog['entries']+[self._successor_entry(packet)])
                    self.catalog_transition(before, _publication_bytes(after))
            if rearming:
                if 'replacement_of' in packet:
                    self.qualify_successor(ref, packet, config)
                    self._rearm_successor(pending, replacement_packet=packet)
                else:
                    self._rearm_successor(pending)
                pending = None
                rearming = False
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
                    if (plan['identity'] != expected or self.catalog_record() != plan['catalog_after']
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
            manifest, task = self._successor_task(packet, config)
            from symphony_capacity import overlap
            for entry in self.state['references'].values():
                other = read_record(self.private(entry['runtime'])/'manifest.json')
                if self._successor_scope_reusable(entry, packet):
                    continue
                if any(overlap(a, b) for a in packet['scope']
                       for t in other['tasks'].values() for b in t['allowed_paths']):
                    raise AdmissionError('successor_scope_overlap')
            if pending is None:
                self.state['successor_request'] = dict(identity=identity, handoff=ref,
                    owner_config=packet['owner_config'], created_at=time.time(), status='pending')
            elif pending['status'] != 'pending':
                raise AdmissionError('successor_request_held')
        except Exception as error:
            terminal = pending is not None and pending.get('status') in ('published', 'duplicate')
            if terminal and 'native_request' in pending:
                try:
                    self._check_published_native_request(pending)
                except Exception:
                    terminal = False  # Tampered/unknown custody is never preserved as success.
            if pending is not None and not rearming and not terminal:
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

    def _native_publication_context(self, ref, handoff, packet, config):
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
        return context

    def _native_successor(self, ref, handoff, packet, config, identity, pending):
        import stokowski_native_publication as native
        context = self._native_publication_context(ref, handoff, packet, config)
        if self.stopping or (self.runtime/'cancel.json').exists():
            raise AdmissionError('successor_native_cancelled')
        if pending is None or 'native_request' not in pending:
            if pending is not None and pending['status'] != 'pending':
                raise AdmissionError('successor_request_held')
            self.qualify_successor(ref, packet, config)
            manifest, task = self._successor_task(packet, config)
            from symphony_capacity import overlap
            for entry in self.state['references'].values():
                other = read_record(self.private(entry['runtime'])/'manifest.json')
                if self._successor_scope_reusable(entry, packet):
                    continue
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
            custody_path = native.custody_directory(SOURCE,context)/(ref['sha256']+'.json')
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
                if 'replacement_of' in packet:
                    entry['replacement_of'] = packet['replacement_of']
                if (plan['identity'] != dict(handoff_sha256=ref['sha256'], packet=handoff['task_packet'],
                                            config=handoff['owner_config'])
                    or native.sha(plan['catalog_before_bytes'].encode()) != packet['inputs'][str(self.catalog)]
                    or json.loads(plan['catalog_before_bytes']) != plan['catalog_before']
                    or plan['catalog_after'] != dict(version=1, entries=plan['catalog_before']['entries']+[entry])
                    or self.catalog_record() != plan['catalog_after']
                    or result.get('runtime') != str(runtime)
                    or mode == 'status' and reply.get('journal_sha256') != file_sha(journal_path)
                    or read_record(runtime/'current-admission.json') != admission
                    or file_sha(runtime/'current-admission.json') != entry['admission_sha256']
                    or file_sha(runtime/'manifest.json') != packet['manifest']['sha256']
                    or file_sha(runtime/'requests'/(issue+'.json')) != packet['request']['sha256']):
                    raise AdmissionError('successor_native_publication_drift')
                pending['status'] = status
                pending['publication_result'] = dict(path=str(custody_path), sha256=file_sha(custody_path))
                pending['publication_journal'] = dict(path=str(journal_path), sha256=file_sha(journal_path))
                self.state.pop('successor_hold', None)
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

    def _check_task_control_source(self, issue, manifest, source, *, review=False, observation=False):
        """Completed evidence may precede its guarded protected controller.

        This never substitutes the controller's head for the original candidate
        identity, nor permits historical coding against a changed checkout.
        A native coding unit needs review mode and its genuine stopped success.
        context() has already run the sealed current-source guard.
        """
        head = subprocess.check_output(['git','-C',str(source),'rev-parse','HEAD'],text=True).strip()
        branch = subprocess.check_output(['git','-C',str(source),'branch','--show-current'],text=True).strip()
        if branch != manifest['branch']:
            raise AdmissionError('current_task_source_drift')
        if head == manifest['base_revision']:
            return
        task = manifest['tasks'][issue]
        if (('stage' not in task and not review) or not self.owner_custody or source != SOURCE or
            self.owner_custody.get('source_root') != str(source) or head != self.config['source_head']):
            raise AdmissionError('current_task_source_drift')
        try:
            subprocess.check_output(['git','-C',str(source),'merge-base','--is-ancestor',
                manifest['base_revision'],head],stderr=subprocess.DEVNULL)
        except subprocess.CalledProcessError as error:
            raise AdmissionError('current_stage_control_ancestry') from error
        # Requalify the actual original origin, with the existing limited
        # observation mode retained for source-drift recovery/cancellation.
        if 'stage' not in task:
            self._completed_native_evidence(issue,self.private(self.entries[issue]['runtime']),manifest)
        elif task['stage_binding']['entry'].get('origin') == 'reviewed-source-v1':
            self.reviewed_origin(issue,task,observation=observation)
        else:
            self.stage_origin(issue,task)

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
        self._check_task_control_source(issue,manifest,source,review=review,observation=observation)
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
            self._check_reviewed_terminal(spec, state, pins,
                                          receipt_path=runtime/'validation-receipt.json')
            admission = stage.qualify_reviewed_source(spec,selected['admission_path'])
        return runtime,spec,selected,state,admission

    def _check_reviewed_terminal(self, spec, state, pins, *, receipt_path=None):
        from stokowski_operations import bridge_arguments
        if (state.get('status') != 'succeeded' or state.get('cancel_requested') is not False
            or state.get('observation_intent') or state.get('reconcile_required')
            or state.get('accepted_output_sha256') != spec['outputs']
            or state.get('acceptance_sha256') != spec['acceptance_sha256']):
            raise AdmissionError('reviewed_source_terminal_required')
        # Frozen owner inputs or the original runtime's fixed receipt custody
        # can supply the body. The Journal commits to its entire content; a
        # status string or a packet supplied by a new reviewer cannot replace it.
        names = list(pins)
        if receipt_path is not None:
            path = self.private(str(receipt_path))
            if path.is_file():
                names.append(str(path))
        receipts = []
        for name in names:
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
        return receipt

    def retained_typed_review_packet(self, issue):
        """Requalify already-admitted review, not a new independent review.

        This separate origin preserves the typed review's actual metadata. It
        grants no merge permission and leaves the supplement reader unchanged.
        Every incoming byte is recomputed again by the normal unit consumer.
        """
        from types import SimpleNamespace
        _, manifest, _ = self.context(issue, review=True)
        task = manifest['tasks'][issue]
        if (task.get('stage') != 'validation' or
            task['stage_binding']['entry'].get('origin') != 'reviewed-source-v1'):
            raise AdmissionError('retained_typed_review_stage')
        runtime, spec, selected, state, admission = self.reviewed_origin(issue, task)
        receipt = self._check_reviewed_terminal(spec, state, task['stage_binding']['inputs'],
                                               receipt_path=runtime/'validation-receipt.json')
        tree = subprocess.check_output(['git','-C',spec['local_source_root'],
            'rev-parse',spec['head']+'^{tree}'], text=True).strip()
        unit = self.gate_binding(SimpleNamespace(identifier=issue,id=self.entries[issue]['issue_id']))
        binding = dict(owner=spec['owner'], issue_id=spec['issue_id'], project_id=unit['project_id'],
            head=spec['head'], base=spec['base'], tree=tree, outputs=spec['outputs'],
            head_branch=spec['branch'], capacity_policy_sha256=spec['policy_sha256'],
            validation_operation_key=selected['operation_key'],
            admission_sha256=spec['acceptance_sha256'], stage_identity=task['stage_binding']['identity'])
        snapshot = dict(review=admission['review'],
            validation=dict(operation_key=selected['operation_key'], status='succeeded',
                head=spec['head'], base=spec['base'], outputs=spec['outputs'],
                capacity_policy_sha256=spec['policy_sha256'], child_tree_gone=True,reconcile_required=False),
            inputs=task['stage_binding']['inputs'], source_tree=tree,
            publication_triggers_actions=False, accepted_delivery=False)
        decision = dict(version=1, kind='retained-typed-review-v1', status='validation-review-qualified',
            action=None, merge_effect='not-applicable', binding_sha256=digest(binding),
            qualification_sha256=digest(snapshot))
        return dict(origin='retained-typed-review-v1',issue=issue,unit_binding=unit,
            integration_binding=binding,snapshot=snapshot,decision=decision,validation_receipt=receipt)

    def continue_retained_typed_review(self, issue):
        # Already inside the normal coordinator lock. The same immutable writer
        # and normal consumer enforce conflicts/replay and own all gate updates.
        packet = self.retained_typed_review_packet(issue)
        self.unit_review_writer(lambda _: packet)(packet)
        self._consume_unit_reviews()

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
            return dict(project_id=manifest['project_id'],issue_id=issue.id,origin='reviewed-source-v1',
                origin_admission_sha256=spec['origin']['admission_sha256'],
                operation_key=selected['operation_key'],owner=spec['owner'],author=admission['author'],
                authors=admission['authors'],head=spec['head'],base=spec['base'],outputs=spec['outputs'])
        if 'stage' in task:
            view, _, _ = self.stage_origin(issue.identifier, task)
            return view.gate_binding(issue)
        return self._native_unit_binding(issue,entry,runtime,manifest)

    def _native_unit_binding(self, issue, entry, runtime, manifest):
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

    def _completed_native_evidence(self, identifier, runtime, manifest):
        """Original stopped success, immutable native identity and finished Pool row.

        This read-only proof does not create a validation binding or waive coding
        admission. It is used only for completed validation/review continuation.
        """
        from types import SimpleNamespace
        task = manifest['tasks'][identifier]
        if 'stage' in task or not self.owner_custody:
            raise AdmissionError('completed_native_owner_required')
        entry = self.entries[identifier]
        issue = SimpleNamespace(identifier=identifier,id=entry['issue_id'])
        self._native_unit_binding(issue,entry,runtime,manifest)
        directory = runtime/'attempts'/identifier
        for name in ('dispatch-intent.json','intent.json','receipt.json'):
            if directory/name != (directory/name).resolve():
                raise AdmissionError('completed_native_artifact_path')
        receipt = read_record(directory/'receipt.json')
        binding = read_record(directory/'intent.json')['binding']
        if (receipt.get('parent_binding') != binding or receipt.get('source_head') != manifest['base_revision']
            or receipt.get('final_head') != manifest['base_revision']
            or receipt.get('final_branch') != manifest['branch']
            or receipt.get('source_identity_changed') is not False
            or receipt.get('scope_violations') != [] or not receipt.get('session_id')
            or receipt.get('turn_completed') is not True
            or type(receipt.get('exit_code')) is not int or receipt['exit_code'] != 0
            or not receipt.get('output_sha256')):
            raise AdmissionError('completed_native_terminal_evidence')
        policy = read_record(runtime/'capacity-policy.json')
        database = Path(policy['symphony']['pool_path'])/'state.sqlite'
        if not database.is_file() or database != database.resolve():
            raise AdmissionError('completed_native_pool_missing')
        from contextlib import closing
        with closing(sqlite3.connect(database.as_uri()+'?mode=ro',uri=True)) as db:
            row = db.execute('SELECT binding,fingerprint,status,outcome FROM leases WHERE id=?',
                             (receipt['lease'],)).fetchone()
        if not row or json.loads(row[0]) != binding or row[1:] != (digest(binding),'finished','succeeded'):
            raise AdmissionError('completed_native_lease')
        workspace = runtime/'workspaces'/identifier
        if workspace != workspace.resolve():
            raise AdmissionError('completed_native_workspace')
        for args,expected in ((['rev-parse','HEAD'],manifest['base_revision']),
                              (['branch','--show-current'],manifest['branch'])):
            if subprocess.check_output(['git','-C',str(workspace),*args],text=True).strip() != expected:
                raise AdmissionError('completed_native_workspace')
        for name,expected in receipt['output_sha256'].items():
            path = workspace/name
            if (not path.resolve().is_relative_to(workspace) or path != path.resolve()
                or not any(name == allowed or name.startswith(allowed+'/') for allowed in task['allowed_paths'])
                or file_sha(path) != expected):
                raise AdmissionError('completed_native_output')
        from stokowski_worker import changed_paths
        if set(changed_paths(workspace,manifest['base_revision'])) != set(receipt['output_sha256']):
            raise AdmissionError('completed_native_output')
        return receipt

    def _native_contribution(self, issue, runtime, manifest, selected, spec):
        """The exact committed native bytes have their own candidate branch."""
        if (spec['profile'] != 'enrichment-resilience-focused' or spec['version'] != 1
            or spec['base'] != manifest['base_revision']):
            raise AdmissionError('native_contribution_profile')
        receipt = self._completed_native_evidence(issue,runtime,manifest)
        if type(selected['candidate_root']) is not str:
            raise AdmissionError('native_contribution_root')
        root = Path(selected['candidate_root'])
        if (not root.is_absolute() or str(root) != selected['candidate_root'] or root != root.resolve()
            or not root.is_dir() or any(p.is_symlink() for p in (root,*root.parents))):
            raise AdmissionError('native_contribution_root')
        def git(*args):
            return subprocess.check_output(['git','-C',str(root),*args],text=True).strip()
        if (git('rev-parse','--show-toplevel') != str(root) or git('rev-parse','HEAD') != spec['head']
            or git('branch','--show-current') != spec['branch']
            or git('status','--porcelain','--untracked-files=all')
            or git('rev-list','--parents','-n','1',spec['head']).split() != [spec['head'],manifest['base_revision']]
            or set(git('diff','--no-renames','--name-only',spec['base'],spec['head']).splitlines()) != set(spec['outputs'])
            or spec['outputs'] != receipt['output_sha256']):
            raise AdmissionError('native_contribution_source')
        for name,expected in spec['outputs'].items():
            path = root/name
            if (path != path.resolve() or not path.resolve().is_relative_to(root) or file_sha(path) != expected
                or git('ls-tree',spec['head'],'--',name).split()[:2] not in (['100644','blob'],['100755','blob'])):
                raise AdmissionError('native_contribution_output')
        return root

    def _native_review_branch(self, issue, entry, runtime, manifest, review_binding=None):
        selected = read_record(runtime/'validation-bindings.json')['issues'][issue]
        if 'candidate_root' not in selected:
            return manifest['branch']
        # A different branch is accepted only through the full original-native
        # and exact committed-contribution qualifier, never packet self-labeling.
        self.validation_binding(issue,entry)
        from contextlib import closing
        with closing(sqlite3.connect((runtime/'operations/operations.sqlite').as_uri()+'?mode=ro',uri=True)) as db:
            row = db.execute('SELECT spec FROM operations WHERE key=?',(selected['operation_key'],)).fetchone()
        spec = json.loads(row[0])
        if review_binding is not None:
            tree = subprocess.check_output(['git','-C',selected['candidate_root'],'rev-parse',
                                             spec['head']+'^{tree}'],text=True).strip()
            if (review_binding.get('tree') != tree or
                any(review_binding.get(k) != spec[k] for k in ('head','base','outputs'))):
                raise AdmissionError('native_contribution_review_source')
        return spec['branch']

    def _closed_failed_native_history(self, issue, runtime, bindings, selected, spec, unit):
        """Retained failed v1 attempts are history, never output acceptance.

        Historical commands are NOT regenerated with today's executor. Their
        original terminal body remains bound by the original Journal digest.
        """
        if not bindings['history']:
            return ()
        if spec['profile'] != 'enrichment-resilience-focused' or 'candidate_root' not in selected:
            raise AdmissionError('current_validation_schema')
        import stokowski_operations as operations
        from contextlib import closing
        from uuid import uuid5,NAMESPACE_URL
        def unique(pairs):
            result = {}
            for name,value in pairs:
                if name in result: raise AdmissionError('current_validation_duplicate')
                result[name] = value
            return result
        identities, seen = [], {selected['operation_key']}
        with closing(sqlite3.connect((runtime/'operations/operations.sqlite').as_uri()+'?mode=ro',uri=True)) as db:
            for index,prior in enumerate(bindings['history']):
                if (not isinstance(prior,dict) or set(prior) != set(selected) | {'issue'}
                    or prior['issue'] != issue
                    or any(prior[k] != v for k,v in selected.items() if k != 'operation_key')):
                    raise AdmissionError('native_failed_history_selection')
                key = prior['operation_key']
                if not isinstance(key,str) or not re.fullmatch('[0-9a-f]{64}',key) or key in seen:
                    raise AdmissionError('native_failed_history_key')
                seen.add(key)
                row = db.execute('SELECT spec,state FROM operations WHERE key=?',(key,)).fetchone()
                if row is None: raise AdmissionError('native_failed_history_journal')
                old,state = (json.loads(value,object_pairs_hook=unique) for value in row)
                operations.validated(old)
                if (row[0] != json.dumps(old,sort_keys=True) or operations.operation_key(old) != key
                    or {k:v for k,v in old.items() if k != 'executor_sha256'} !=
                       {k:v for k,v in spec.items() if k != 'executor_sha256'}
                    or state.get('status') != 'failed' or state.get('cancel_requested') is not False
                    or state.get('reconcile_required') or state.get('accepted_output_sha256') != {}
                    or state.get('acceptance_sha256') != old['acceptance_sha256']
                    or state.get('windmill_job_id') != str(uuid5(NAMESPACE_URL,'offmenu:run:'+key))
                    or state.get('cancel_job_id') != str(uuid5(NAMESPACE_URL,'offmenu:cancel:'+key))
                    or state.get('logical_job_id') != 'offmenu-'+key[:48]):
                    raise AdmissionError('native_failed_history_binding')
                path = runtime/('validation-receipt-'+key+'.json')
                if path != path.resolve() or not path.is_file():
                    raise AdmissionError('native_failed_history_receipt_missing')
                receipt = read_record(path)
                if (digest(receipt) != state.get('receipt_sha256')
                    or receipt.get('status') not in ('failed','timed_out')
                    or type(receipt.get('exit_code')) is not int or receipt['exit_code'] == 0
                    or receipt.get('child_tree_gone') is not True or receipt.get('reconcile_required') is not False
                    or receipt.get('job_id') != state['logical_job_id']
                    or receipt.get('mode') != 'read'
                    or receipt.get('runner_sha256') != old['runner_sha256']
                    or receipt.get('capacity_policy_sha256') != old['policy_sha256']
                    or any(not isinstance(receipt.get(k),str) or not re.fullmatch('[0-9a-f]{64}',receipt[k])
                           for k in ('command_sha256','request_sha256'))):
                    raise AdmissionError('native_failed_history_receipt')
                # A terminal backend observation resolves a sticky observation
                # intent/diagnosis. It does not accept outputs or replay work.
                old_selected = {k:v for k,v in prior.items() if k != 'issue'}
                predecessor = dict(version=1,issues={issue:old_selected},history=bindings['history'][:index])
                raw = (json.dumps(predecessor,indent=2)+'\n').encode()
                identities.append(digest(dict(unit=unit,selected=old_selected,spec=old,
                    bindings_sha256=hashlib.sha256(raw).hexdigest())))
        return tuple(identities)

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
            or set(bindings['issues']) != {issue} or not isinstance(bindings['history'], list)):
            raise AdmissionError('current_validation_schema')
        selected = bindings['issues'][issue]
        selection_fields = {
            'operation_key','source_head','native_receipt_sha256','native_output_sha256',
            'derivation','derivation_reason'}
        if (not isinstance(selected, dict) or set(selected) not in (selection_fields,selection_fields | {'candidate_root'})
            or selected['derivation'] != {}
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
            or ('candidate_root' not in selected and
                spec.get('branch','feature/langgraph-delivery-standardization') != manifest['branch'])
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
        candidate_repo = (self._native_contribution(issue,runtime,manifest,selected,spec)
                          if 'candidate_root' in selected else None)
        for repository in (() if candidate_repo is not None else dict.fromkeys((SOURCE, source))):
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
        predecessors = self._closed_failed_native_history(issue,runtime,bindings,selected,spec,unit)
        identity = digest(dict(unit=unit, selected=selected, spec=spec, bindings_sha256=file_sha(path)))
        self._qualified_failed_native_history = (issue,str(runtime),identity,predecessors)
        return runtime, identity

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
                if issue in self.config.get('completed_native_validations', {}):
                    from stokowski_completed import qualify
                    completed = qualify(self, issue)
                    task['validation'] = dict(status='succeeded', origin='completed-native-validation-v1',
                        operation_key=completed['snapshot']['validation']['operation_key'],
                        requested_model=None, requested_effort=None, provider=None)
                    self.save()
                    continue  # Completed evidence never invokes stage.tick or a submitter.
                runtime, identity = self.validation_binding(issue, entry)
                from types import SimpleNamespace
                unit = self.gate_binding(SimpleNamespace(identifier=issue, id=entry['issue_id']), observation=True)
                gate = task.setdefault('unit_gate', dict(binding=unit, disposition='waiting'))
                if gate.get('binding') != unit:
                    raise AdmissionError('stage_gate_rebind')
                prior = task.get('validation', {})
                if prior.get('identity', identity) != identity:
                    qualified = getattr(self,'_qualified_failed_native_history',None)
                    if (prior.get('status') != 'failed' or gate.get('disposition') != 'waiting'
                        or gate.get('handled') or gate.get('review_sha256') or gate.get('accepted_delivery')
                        or not qualified or qualified[:3] != (issue,str(runtime),identity)
                        or prior['identity'] not in qualified[3]):
                        raise AdmissionError('current_validation_rebind')
                retained = (selected_task.get('stage') == 'validation' and
                    selected_task['stage_binding']['entry'].get('origin') == 'reviewed-source-v1')
                if retained:
                    # A stopped original operation needs no transport, including
                    # when its executor predates this source correction.
                    _, _, _, state, _ = self.reviewed_origin(issue, selected_task)
                    if state.get('status') == 'succeeded':
                        task['validation'] = dict(identity=identity,status='succeeded',
                            requested_model=None,requested_effort=None,provider=None)
                        self.continue_retained_typed_review(issue)
                        self.save()
                        continue
                if selected_task.get('stage') == 'review':
                    task['validation'] = dict(identity=identity, status='awaiting-independent-review',
                        requested_model=None, requested_effort=None, provider=None)
                    self.save()
                    await self.continue_native_review(issue)
                    continue
                if 'stage' not in selected_task:
                    key = read_record(runtime/'validation-bindings.json')['issues'][issue]['operation_key']
                    with sqlite3.connect((runtime/'operations/operations.sqlite').as_uri()+'?mode=ro', uri=True) as db:
                        row = db.execute('SELECT state FROM operations WHERE key=?', (key,)).fetchone()
                    if row and json.loads(row[0]).get('status') == 'succeeded':
                        task['validation'] = dict(identity=identity, status='succeeded',
                            requested_model=None, requested_effort=None, provider=None)
                        self.save()
                        await self.continue_native_review(issue)
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
                if status == 'succeeded' and 'stage' not in selected_task:
                    await self.continue_native_review(issue)
                elif status == 'succeeded' and retained:
                    self.continue_retained_typed_review(issue)
            except asyncio.CancelledError:
                raise
            except Exception:
                # No raw protocol errors, credentials or remote logs in owner state.
                task.setdefault('validation', dict(requested_model=None,
                    requested_effort=None, provider=None))['status'] = 'held'
            self.save()

    def _native_harness_config(self):
        """Only the sealed owner may opt admitted units into the new boundary."""
        if 'native_harness_boundaries' not in self.config:
            return
        references = self.config['native_harness_boundaries']
        if (not self.owner_custody or not isinstance(references, dict)
            or not 1 <= len(references) <= 128):
            raise AdmissionError('native_harness_owner_config')
        required = {'tools/delivery/native_harness_runtime.py',
                    'tools/delivery/native_harness_contract.py', 'tools/delivery/linear_delivery.py',
                    'tools/delivery/release_qualification.py', 'src/offmenu/delivery/engine.py',
                    'src/offmenu/delivery/status.py'}
        if not required <= set(self.config['source_sha256']):
            raise AdmissionError('native_harness_source_pin')
        for identifier in references:
            if not isinstance(identifier, str) or not re.fullmatch(r'UIF-[1-9][0-9]*', identifier):
                raise AdmissionError('native_harness_issue')
            self._native_harness_selection(identifier)

    def _native_harness_selection(self, identifier):
        if not self.owner_custody:
            raise AdmissionError('native_harness_owner_config')
        reference = self.config['native_harness_boundaries'][identifier]
        if (not isinstance(reference, dict) or set(reference) != {'path', 'sha256'}
            or not isinstance(reference['path'], str)):
            raise AdmissionError('native_harness_reference')
        selection = self._private_pin(reference)
        if set(selection) != {'binding', 'packet', 'context'} or not isinstance(selection['binding'], dict):
            raise AdmissionError('native_harness_selection')
        binding = selection['binding']
        if (set(binding) != {'issue_id', 'project_id', 'owner', 'packet_sha256',
                             'operation_id', 'phase', 'unit_sha256'}
            or binding['owner'] != self.config['owner']
            or not any(r['project_id'] == binding['project_id'] for r in self.routes)
            or binding['phase'] not in ('linear', 'integration', 'release')
            or any(not isinstance(binding[k], str) or not re.fullmatch('[0-9a-f]{64}', binding[k])
                   for k in ('packet_sha256', 'operation_id', 'unit_sha256'))):
            raise AdmissionError('native_harness_binding')
        try:
            if any(str(UUID(binding[k])) != binding[k] or not UUID(binding[k]).int
                   for k in ('issue_id', 'project_id')):
                raise ValueError()
        except (ValueError, TypeError, AttributeError):
            raise AdmissionError('native_harness_binding') from None
        # File-byte pins retain their original meaning; packet identity is
        # independently checked with the shared fingerprint at consumption.
        if (not isinstance(selection['packet'], dict) or set(selection['packet']) != {'path', 'sha256'}
            or not isinstance(selection['packet']['path'], str)):
            raise AdmissionError('native_harness_reference')
        self._private_pin(selection['packet'])
        context = selection['context']
        if binding['phase'] == 'linear' and type(context) is dict and context == {}:
            # Linear still needs the original admitted native unit; it never
            # consumes Engine or independent-review context references.
            return selection
        if not isinstance(context, dict):
            raise AdmissionError('native_harness_context')
        keys = set(context) - {'publisher_invocation','publisher_continuation'}
        if binding['phase'] == 'integration' and keys == {'reviewed_runtime', 'unit_review'}:
            root_name, references = 'reviewed_runtime', ('unit_review',)
        elif (binding['phase'] == 'integration' and keys == {'native_runtime','pending_unit_review'}
              and 'publisher_invocation' in context):
            root_name, references = 'native_runtime', ()
            c=context['pending_unit_review']
            if (not isinstance(c,dict) or c.get('runtime') != str(self.runtime)
                or c.get('issue') != identifier or type(c.get('actor_uid')) is not int or c['actor_uid'] != 1000
                or c.get('source_head') != self.config['source_head']
                or c.get('source_sha256') != self.config['source_sha256']):
                raise AdmissionError('native_harness_pending_unit_context')
        elif keys == {'engine_root', 'engine_task', 'unit_review'}:
            root_name, references = 'engine_root', ('engine_task', 'unit_review')
        else:
            raise AdmissionError('native_harness_context')
        if not isinstance(context[root_name], str) or not self.private(context[root_name]).is_dir():
            raise AdmissionError('native_harness_context')
        if 'publisher_continuation' in context:
            if (binding['phase'] != 'integration' or root_name not in ('reviewed_runtime','native_runtime')
                or 'publisher_invocation' not in context):
                raise AdmissionError('native_harness_continuation_context')
            import native_publisher_invocation as helper
            name = 'tools/delivery/native_publisher_invocation.py'
            if (Path(helper.__file__).resolve() != SOURCE/name or
                self.config['source_sha256'].get(name) != file_sha(helper.__file__)):
                raise AdmissionError('native_harness_continuation_source')
            grant=helper.continuation(context['publisher_continuation'],binding)
            if ('pre_admission_refusal' in grant) != (root_name == 'native_runtime'):
                raise AdmissionError('native_harness_continuation_origin')
        if 'publisher_invocation' in context:
            invocation = context['publisher_invocation']
            if (not isinstance(invocation, dict)
                or set(invocation) != {'version', 'closure_sha256', 'host_confirmation_sha256'}
                or type(invocation['version']) is not int or invocation['version'] != 1
                or any(not isinstance(invocation[k], str) or not re.fullmatch('[0-9a-f]{64}', invocation[k])
                       for k in ('closure_sha256', 'host_confirmation_sha256'))):
                raise AdmissionError('native_harness_publisher_invocation')
            from native_harness_contract import fingerprint
            fingerprint(invocation)  # Included unchanged in the pinned selection identity.
        for name in references:
            ref = context[name]
            if not isinstance(ref, dict) or set(ref) != {'path', 'sha256'} or not isinstance(ref['path'], str):
                raise AdmissionError('native_harness_context')
            self._private_pin(ref)
        return selection

    def _native_harness_module(self):
        self.guard()
        self._native_harness_config()
        module = importlib.import_module('native_harness_runtime')
        if Path(module.__file__).resolve() != SOURCE/'tools/delivery/native_harness_runtime.py':
            raise AdmissionError('native_harness_module_path')
        return module

    def _native_harness_refill_allowed(self, identifier):
        if identifier not in self.config.get('native_harness_boundaries', {}):
            return True
        # Saved diagnostics never authorize refill. Only the immediate async
        # consumer can lend this permit to the existing synchronous boundary.
        if self.read_only or self.stopping or self._native_harness_refill is None:
            return False
        try:
            module = self._native_harness_module()
            selection = self._native_harness_selection(identifier)
            binding = selection['binding']
            from types import SimpleNamespace
            issue = SimpleNamespace(identifier=identifier, id=self.entries[identifier]['issue_id'])
            return (issue.id == binding['issue_id']
                and module.fingerprint(self.gate_binding(issue, observation=True)) == binding['unit_sha256']
                and self._native_harness_refill == (identifier, module.fingerprint(selection),
                                                    binding['operation_id'], binding['unit_sha256']))
        except Exception:
            return False

    async def continue_native_harness(self, adapters_factory=None, *, linear_client=None):
        """One finite owner-bound consumption in the existing locked poll."""
        if not self.config.get('native_harness_boundaries') or self.read_only or self.stopping:
            return
        eligible = [i for i in self.entries if i in self.config['native_harness_boundaries']]
        if not eligible:
            return
        cursor = self.state.get('native_harness_cursor')
        index = eligible.index(cursor) if cursor in eligible else 0
        identifier = eligible[index]
        self.state['native_harness_cursor'] = eligible[(index+1) % len(eligible)]
        task = self.state['tasks'].setdefault(identifier, {})
        state = task.setdefault('native_harness', {})
        self._native_harness_refill = None
        try:
            module = self._native_harness_module()
            selection = self._native_harness_selection(identifier)
            selected_sha = module.fingerprint(selection)
            binding = module.OwnerBinding(**selection['binding'])
            continuation = None
            if state.get('selection_sha256', selected_sha) != selected_sha:
                grant = selection['context'].get('publisher_continuation',{})
                if grant.get('previous_selection_sha256') != state['selection_sha256']:
                    raise AdmissionError('native_harness_selection_rebind')
                continuation = module.invocation_continuation_record(self,binding,
                    self._private_pin(selection['packet']),selection)
            from types import SimpleNamespace
            issue = SimpleNamespace(identifier=identifier, id=self.entries[identifier]['issue_id'])
            if issue.id != binding.issue_id:
                raise AdmissionError('native_harness_issue_binding')
            self.context(identifier, review=True, observation=True)
            if module.fingerprint(self.gate_binding(issue, observation=True)) != binding.unit_sha256:
                raise AdmissionError('native_harness_unit_drift')
            if continuation is not None:
                self.state[module.INVOCATIONS][binding.operation_id] = continuation
            state.update(selection_sha256=selected_sha, operation_id=binding.operation_id,
                         unit_sha256=binding.unit_sha256, status='pending')
            state.pop('reason', None)
            state.pop('projection', None)
            self.save()  # Before factory/transaction; existing journal owns effects.
            if adapters_factory is None:
                # Fixed reviewed installed code, never a name selected by JSON.
                adapters_factory = getattr(module, 'owner_adapters', None)
            if not callable(adapters_factory):
                raise AdmissionError('native_harness_adapters_unavailable')
            async def consume():
                adapters = adapters_factory(self, issue, binding, selection, linear_client=linear_client)
                if inspect.isawaitable(adapters):
                    adapters = await adapters
                if type(adapters) is not module.OwnerAdapters:
                    raise AdmissionError('native_harness_adapters_required')
                async def authorize(current, native_issue, admitted):
                    self.guard()
                    if (current is not self or admitted != binding
                        or self._native_harness_selection(identifier) != selection):
                        raise AdmissionError('native_harness_selection_drift')
                    self.context(identifier, review=True, observation=True)
                    if module.fingerprint(self.gate_binding(native_issue, observation=True)) != binding.unit_sha256:
                        raise AdmissionError('native_harness_unit_drift')
                    value = adapters.authorize(current, native_issue, admitted)
                    return (await value if inspect.isawaitable(value) else value) is True
                async def load(admitted):
                    packet = adapters.load(admitted)
                    if inspect.isawaitable(packet):
                        packet = await packet
                    pinned = self._private_pin(selection['packet'])
                    if packet != pinned or module.fingerprint(packet) != binding.packet_sha256:
                        raise AdmissionError('native_harness_packet_drift')
                    return packet
                acceptance = getattr(adapters, 'integration_acceptance', None)
                preparation = getattr(adapters, 'prepare_unit', None)
                trusted = module.OwnerAdapters(authorize, load, adapters.engine, adapters.review,
                    adapters.observe, adapters.step,
                    integration_acceptance=acceptance, prepare_unit=preparation)
                result = await module.consume_boundary(self, issue, binding=binding, adapters=trusted)
                return result, authorize
            result, authorize = await asyncio.wait_for(consume(), timeout=10)
            state.update(status=result['status'], projection=result)
            effect = result.get('effect', {})
            if (result.get('operation_id') == binding.operation_id
                and result.get('status') in ('observed', 'advanced')
                and result.get('next_action') == 'existing-unit-consumer'
                and effect.get('operation_id') == binding.operation_id
                and effect.get('status') == 'verified' and effect.get('child_tree_gone') is True):
                if await asyncio.wait_for(authorize(self, issue, binding), timeout=10) is not True:
                    raise AdmissionError('native_harness_owner_authority_missing')
                self._native_harness_refill = (identifier, selected_sha,
                                               binding.operation_id, binding.unit_sha256)
                self._successor_boundary()
        except asyncio.CancelledError:
            state.update(status='unknown', reason='owner-cancelled-reconcile-existing-operation')
            raise
        except Exception as error:
            state.update(status='held', reason=str(error) if isinstance(error, AdmissionError)
                         else type(error).__name__)
        finally:
            self._native_harness_refill = None
            self.save()

    def native_review_template_policy(self, issue, *, materialize=False):
        """Sole owner derives bytes; consumers only recompute from disk authority.

        The template contains no task/session/output/receipt digests. Its source
        root and receipt filename are static custody locations, never evidence.
        """
        import stokowski_worker as worker
        from types import SimpleNamespace
        if self.config.get('native_review_template') is None:
            raise AdmissionError('native_review_policy_unavailable: owner template required')
        if current_config(self.runtime)[0] != self.config:
            raise AdmissionError('native_review_config_override')
        self.guard()
        ref = self.config.get('native_review_template')
        if ref is None:
            raise AdmissionError('native_review_policy_unavailable: owner template required')
        self.private(ref['path'])
        template = worker.pinned_record(ref)
        static = {'schema','owner','reviewer_owner','project_id','source_head','source_sha256',
                  'installation_sha256','source_root','validation_receipt_name','provider','model',
                  'effort','resources','acceptance','timeout_seconds','require_stopped_child','role'}
        if (set(template) != static or template['schema'] != 'native-review-template-v1'
            or template['role'] != 'native-review-read-only'
            or any(template[k] != self.config[k] for k in
                   ('owner','source_head','source_sha256','installation_sha256'))):
            raise AdmissionError('native_review_template_binding')
        runtime, manifest, _ = self.context(issue, review=True, observation=True)
        task = manifest['tasks'][issue]
        if ((runtime/'cancel.json').exists() or (self.runtime/'cancel.json').exists()
            or (materialize and self.state['tasks'][issue].get('unit_gate',{}).get('disposition') == 'rework')):
            raise AdmissionError('native_review_template_terminal_hold')
        if ('stage' in task or template['project_id'] != manifest['project_id']
            or template['resources'] != task['resources'] or template['acceptance'] != task['acceptance']
            or template['reviewer_owner'] == task['owner']
            or (template['provider'],template['model'],template['effort']) != ('codex-chatgpt',worker.MODEL,'medium')
            or template['require_stopped_child'] is not True
            or type(template['timeout_seconds']) is not int or not 1 <= template['timeout_seconds'] <= 600):
            raise AdmissionError('native_review_template_scope')
        _, identity = self.validation_binding(issue, self.entries[issue])
        key = read_record(runtime/'validation-bindings.json')['issues'][issue]['operation_key']
        with sqlite3.connect((runtime/'operations/operations.sqlite').as_uri()+'?mode=ro',uri=True) as db:
            row = db.execute('SELECT spec,state FROM operations WHERE key=?',(key,)).fetchone()
        spec, state = (json.loads(v) for v in row)
        name = template['validation_receipt_name']
        if not isinstance(name,str) or Path(name).name != name:
            raise AdmissionError('native_review_template_receipt')
        receipt_path = self.private(str(runtime/name))
        validation = dict(path=str(receipt_path),sha256=file_sha(receipt_path))
        worker.pinned_record(validation)
        self._check_reviewed_terminal(spec,state,{validation['path']:validation['sha256']})
        author_path = runtime/'attempts'/issue/'receipt.json'
        author_ref = dict(path=str(author_path),sha256=file_sha(author_path))
        author = worker.pinned_record(author_ref)
        unit = self.gate_binding(SimpleNamespace(identifier=issue,id=self.entries[issue]['issue_id']))
        if (author.get('origin') != 'native-coding' or author.get('status') != 'succeeded'
            or author.get('child_tree_gone') is not True or not author.get('session_id')
            or author.get('output_sha256') != spec['outputs']):
            raise AdmissionError('native_review_template_author')
        capacity = read_record(runtime/'capacity-policy.json')
        database = Path(capacity['symphony']['pool_path'])/'state.sqlite'
        with sqlite3.connect(database.as_uri()+'?mode=ro',uri=True) as db:
            lease = db.execute('SELECT binding,fingerprint,status,outcome FROM leases WHERE id=?',
                               (author['lease'],)).fetchone()
        if (lease is None or lease[2:] != ('finished','succeeded')
            or json.loads(lease[0]) != author['parent_binding']
            or lease[1] != author['binding_sha256'] or lease[1] != unit['operation_sha256']
            or lease[1] != digest(author['parent_binding'])
            or author['parent_binding']['owner'] != task['owner']):
            raise AdmissionError('native_review_template_author_lease')
        root = Path(template['source_root'])
        source = dict(root=str(root),head=spec['head'],base=spec['base'],branch=spec['branch'],
            tree=worker.git(root,'rev-parse','HEAD^{tree}'),outputs=spec['outputs'],
            files_sha256=digest({n:file_sha(root/n) for n in worker.git(root,'ls-files','-z').split('\0') if n}))
        worker.review_source(source)
        changed = set(worker.git(root,'diff','--name-only',spec['base'],spec['head']).splitlines())
        if changed != set(spec['outputs']):
            raise AdmissionError('native_review_template_paths')
        policy = {k:template[k] for k in ('owner','reviewer_owner','project_id','provider','model','effort',
                  'resources','acceptance','timeout_seconds','require_stopped_child')}
        policy.update(schema=worker.REVIEW_ORIGIN,issue=issue,stage_identity=identity,
            unit_binding=unit,validation_identity=identity,source=source,author_receipts=[author_ref],
            excluded_sessions=[author['session_id']],excluded_owners=[author['parent_binding']['owner']],
            current_runtime=str(self.runtime),validation_receipt=validation)
        derivation = dict(template=ref,unit=unit,source=source,author_receipt=author_ref,
                          author_lease=author['lease'],validation_identity=identity,
                          validation_receipt=validation,operation_key=key)
        path = runtime/'native-review-derived-policy.json'
        # checkpoint's serialization is fixed; compare exact bytes as well as JSON.
        raw = (json.dumps(policy,sort_keys=True,indent=2)+'\n').encode()
        policy_ref = dict(path=str(path),sha256=hashlib.sha256(raw).hexdigest())
        pending = self.state['tasks'][issue].get('native_review',{})
        expected = dict(policy=policy_ref,derivation=derivation)
        # Rework may requalify retained bytes, but cannot materialize or launch.
        # Exact derivation checks here and native receipt qualification downstream
        # still apply; an existing file alone is never authority.
        if path.exists() or 'derivation' in pending:
            if (not path.is_file() or path.read_bytes() != raw
                or any(pending.get(k) != v for k,v in expected.items())):
                raise AdmissionError('native_review_template_derivation_drift')
        elif materialize and not self.read_only:
            with path.open('xb') as stream:
                os.fchmod(stream.fileno(),0o600)
                stream.write(raw)
                stream.flush()
                os.fsync(stream.fileno())
            directory = os.open(runtime,os.O_RDONLY | os.O_DIRECTORY)
            try:
                os.fsync(directory)
            finally:
                os.close(directory)
            self.state['tasks'][issue]['native_review'] = dict(expected,status='policy-bound')
            self.save()  # Artifact + derivation are durable before launch intent.
        else:
            raise AdmissionError('native_review_template_not_materialized')
        return policy_ref

    def native_review_binding(self, issue):
        """Owner-selected native policy; original validation must be terminal."""
        import stokowski_worker as worker
        ref = self.config.get('native_review_policies', {}).get(issue)
        if ref is None:
            ref = self.native_review_template_policy(issue)
        self.private(ref['path'])
        runtime, manifest, _ = self.context(issue, review=True, observation=True)
        task = manifest['tasks'][issue]
        staged = 'stage' in task
        if staged:
            if task['stage'] != 'review' or task['stage_binding']['entry'].get('origin') is not None:
                raise AdmissionError('native_review_stage_required')
            _, origin_runtime, _ = self.stage_origin(issue, task)
        else:
            origin_runtime = runtime
        _, identity = self.validation_binding(issue, self.entries[issue])
        key = read_record(origin_runtime/'validation-bindings.json')['issues'][issue]['operation_key']
        # Read-only SQLite: no Journal construction, dispatch or receipt repair.
        with sqlite3.connect((origin_runtime/'operations/operations.sqlite').as_uri()+'?mode=ro', uri=True) as db:
            row = db.execute('SELECT spec,state FROM operations WHERE key=?',(key,)).fetchone()
        spec, state = (json.loads(v) for v in row)
        policy = worker.pinned_record(ref)
        if staged:
            pins = task['stage_binding']['inputs']
        else:
            receipt_ref = policy.get('validation_receipt')
            worker.pinned_record(receipt_ref)
            self.private(receipt_ref['path'])
            if (policy.get('current_runtime') != str(self.runtime)
                or policy.get('stage_identity') != identity or policy.get('owner') != task['owner']):
                raise AdmissionError('native_review_current_binding')
            pins = {receipt_ref['path']:receipt_ref['sha256']}
        self._check_reviewed_terminal(spec,state,pins)
        request = dict(kind=worker.REVIEW_ORIGIN,policy=ref)
        from types import SimpleNamespace
        unit = self.gate_binding(SimpleNamespace(identifier=issue,id=self.entries[issue]['issue_id']))
        original_receipt = origin_runtime/'attempts'/issue/'receipt.json'
        if (policy['owner'] != self.config['owner'] or policy['unit_binding'] != unit
            or policy['validation_identity'] != identity
            or dict(path=str(original_receipt),sha256=file_sha(original_receipt)) not in policy['author_receipts']
            or policy['source']['outputs'] != spec['outputs']
            or policy['source']['head'] != spec['head'] or policy['source']['base'] != spec['base']
            or policy['source']['branch'] != spec['branch']):
            raise AdmissionError('native_review_owner_binding')
        return runtime, request, unit

    def native_review_context(self, issue):
        runtime, request, unit = self.native_review_binding(issue)
        import stokowski_worker as worker
        worker.review_contract(runtime, issue, request)
        return runtime, request, unit

    async def continue_native_review(self, issue):
        """One owned finite child; durable same-ID recovery never resubmits."""
        import stokowski_worker as worker
        task = self.state['tasks'][issue]
        try:
            if issue not in self.config.get('native_review_policies', {}):
                self.native_review_template_policy(issue, materialize=True)
            runtime, request, unit = self.native_review_context(issue)
            identity = digest(dict(runtime=str(runtime),request=request,unit=unit))
            pending = task.get('native_review')
            if pending is not None and pending.get('identity') not in (None,identity):
                raise AdmissionError('native_review_intent_rebind')
            if pending is not None and 'identity' not in pending:
                pending = None
            directory = runtime/'attempts'/('review-'+issue)
            retry_refusal = (pending is not None and pending.get('status') == 'deferred'
                             and worker.confirmed_review_refusal(runtime,issue,request))
            if pending is None or retry_refusal:
                task.setdefault('native_review', {}).update(identity=identity,status='launch-intent',request=request)
                self.save()  # Before actual subprocess or Pool effect.
                proc = None
                try:
                    proc = await asyncio.create_subprocess_exec(sys.executable,
                        str(Path(__file__).with_name('stokowski_worker.py')),
                        '--runtime',str(runtime),'--issue',issue,'--native-review-policy',request['policy']['path'],
                        '--native-review-policy-sha256',request['policy']['sha256'],
                        stdout=asyncio.subprocess.DEVNULL,stderr=asyncio.subprocess.DEVNULL,
                        env=worker.child_environment(os.environ))
                    timeout = min(600,worker.pinned_record(request['policy'])['timeout_seconds']+30)
                    await asyncio.wait_for(proc.wait(),timeout=timeout)
                except (asyncio.CancelledError,asyncio.TimeoutError):
                    task['native_review']['status'] = 'uncertain'
                    self.save()
                    if proc is not None and proc.returncode is None:
                        proc.terminate()
                        try:
                            await asyncio.wait_for(asyncio.shield(proc.wait()),timeout=5)
                        except asyncio.TimeoutError:
                            proc.kill()
                            await asyncio.wait_for(asyncio.shield(proc.wait()),timeout=5)
                    raise
            # A retained launch without a receipt is an actionable same-owner hold.
            if not (directory/'receipt.json').is_file():
                if (task['native_review']['status'] != 'uncertain'
                    and worker.confirmed_review_refusal(runtime,issue,request)):
                    task['native_review'].update(status='deferred',
                        hold='confirmed-pre-admission-refusal',
                        refusal_intent_sha256=file_sha(directory/'intent.json'))
                    self.save()
                    return
                raise AdmissionError('native_review_launch_unknown: reconcile retained intent; no retry')
            from stokowski_unit_review import qualify_native_review
            packet = qualify_native_review(self,issue)
            path = self.runtime/('unit-review-'+issue+'.json')
            if path.exists():
                if read_record(path) != packet:
                    raise AdmissionError('native_review_incoming_conflict')
            else:
                # Coordinator owns the existing root lock. No connector identity asserted.
                checkpoint(path,packet)
            task['native_review']['status'] = 'qualified'
            self._consume_unit_reviews()
        except asyncio.CancelledError:
            raise
        except Exception as error:
            task.setdefault('native_review', {})['status'] = 'held'
            task['native_review']['hold'] = str(error) if isinstance(error,AdmissionError) else type(error).__name__
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
        if packet.get('origin') == 'retained-typed-review-v1':
            if digest(packet) != digest(self.retained_typed_review_packet(issue)):
                raise AdmissionError('retained_typed_review_packet_mismatch')
            return unit
        if packet.get('origin') == 'native-readonly-review-v1':
            from stokowski_unit_review import qualify_native_review
            if packet != qualify_native_review(self,issue):
                raise AdmissionError('native_review_packet_mismatch')
            return unit
        if packet.get('decision', {}).get('kind') == 'completed-native-validation-v1':
            from stokowski_completed import qualify
            if packet != qualify(self, issue):
                raise AdmissionError('completed_native_review_packet')
            return unit
        runtime, manifest, _ = self.context(issue, review=True)
        task = manifest['tasks'][issue]
        reviewed = 'stage' in task and task['stage_binding']['entry'].get('origin') == 'reviewed-source-v1'
        if reviewed:
            runtime, origin_spec, _, _, admission = self.reviewed_origin(issue,task)
        elif 'stage' in task:
            view, _, _ = self.stage_origin(issue, task)
            return view._check_unit_review(packet)
        expected_branch = (origin_spec['branch'] if reviewed else
            self._native_review_branch(issue,entry,runtime,manifest,packet['integration_binding']))
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
        if (unit != packet['unit_binding'] or unit['project_id'] != manifest['project_id'] or
            b['issue_id'] != entry['issue_id'] or b['owner'] != self.config['owner'] or
            b['head_branch'] != expected_branch or snapshot.get('publisher_owner') != b['owner'] or
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
                disposition = ('rework' if packet.get('origin') == 'native-readonly-review-v1'
                               and packet.get('verdict') == 'rework' else 'approved')
                if (packet['issue'] != issue or gate.get('binding') != unit or
                    gate.get('review_sha256') not in (None, fingerprint) or
                    gate.get('disposition') not in ('waiting',disposition)):
                    raise AdmissionError('unit_review_gate_conflict')
                if gate.get('handled'):
                    continue
                gate.update(review_sha256=fingerprint, disposition=disposition, accepted_delivery=False)
                if self.state['tasks'][issue].get('defer') == 'unit_review_held':
                    self.state['tasks'][issue].pop('defer')
            except Exception:
                self._hold_unit_review(issue)

    async def candidates(self, client, issues, route=None):
        route = self.admitted_route((route or self.route)['project_id'])
        intake_route_args = (route,) if 'project_routes' in self.config else ()
        self.refresh()
        selected = []
        for issue in issues:
            entry = self.entries.get(issue.identifier)
            if not entry:
                await self._intake(client, issue, *intake_route_args)
                continue
            if issue.id != entry['issue_id'] or issue.state not in ('Todo','In Progress'):
                continue
            try:
                replacement_intake = False
                if self._intake_ref(route):
                    policy = self._intake_policy(route)
                    for reference in policy['references']:
                        _, authority = self._intake_authority(reference, route)
                        relation = authority.get('replacement_of')
                        if (authority['issue'] == issue.identifier and relation
                            and relation.get('entry_sha256') == digest(entry)):
                            # Tracker identity is unchanged; fresh owner authority
                            # selects a new unit rather than replaying this one.
                            await self._intake(client, issue, *intake_route_args)
                            replacement_intake = True
                            break
                if replacement_intake:
                    # The next refresh validates and adopts the published
                    # generation. This pass still holds the retired entry.
                    continue
                _, selected_manifest, _ = self.context(issue.identifier)
                if selected_manifest['project_id'] != route['project_id']:
                    raise AdmissionError('current_selected_project')
                if 'stage' in selected_manifest['tasks'][issue.identifier]:
                    self.stage_origin(issue.identifier, selected_manifest['tasks'][issue.identifier])
                    continue
                data = await client._graphql('query($id: String!){ issue(id:$id){id identifier project{id} state{name}}}', {'id':issue.id})
                remote = data.get('issue') or {}
                if (remote.get('id') != issue.id or remote.get('identifier') != issue.identifier
                    or remote.get('project', {}).get('id') != selected_manifest['project_id']
                    or remote.get('state', {}).get('name') not in ('Todo','In Progress')):
                    raise AdmissionError('current_authoritative_identity_or_state')
                self.state['tasks'][issue.identifier].pop('defer', None)
                self.save()
                selected.append(issue)
            except Exception as error:
                reason = str(error) if isinstance(error, AdmissionError) else 'current_input_or_tracker_unavailable'
                self.defer(issue.identifier, type(error).__name__ + ': ' + reason)
        return selected


def install_adapters(runtime, manifest, key, current=None, *, native_harness_adapter_factory=None):
    import stokowski.config as config
    import stokowski.linear as linear
    import stokowski.orchestrator as orchestration
    import stokowski.workspace as workspace_module

    async def reject_hook(*args, **kwargs):
        raise RuntimeError('Arbitrary shell hooks are disabled by OffMenu adapter')

    config.ProjectConfig.agent_env = lambda self: child_environment(os.environ)
    config.ProjectConfig.resolved_api_key = lambda self: key
    # Pinned ServiceConfig.projects retains native per-project routing.
    workspace_module.run_hook = reject_hook

    routes = current.routes if current else [project_route(manifest['project_id'])]
    original_fetch = linear.LinearClient.fetch_candidate_issues

    async def selected_candidates(client, project_slug, states):
        route = next((r for r in routes if r['project_slug'] == project_slug), None)
        if route is None:
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
            return await current.candidates(client, issues, route)
        selected = []
        for issue in issues:
            if issue.identifier not in manifest['tasks'] or issue.id != manifest['tasks'][issue.identifier]['issue_id']:
                continue
            remote = (await client._graphql(
                'query($id: String!){ issue(id:$id){id identifier project{id} state{name}}}',
                {'id':issue.id})).get('issue') or {}
            if (remote.get('id') != issue.id or remote.get('identifier') != issue.identifier
                or remote.get('project', {}).get('id') != route['project_id']
                or remote.get('state', {}).get('name') not in states):
                raise AdmissionError('finite_authoritative_identity_or_state')
            selected.append(issue)
        return selected

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
        # A default ACL can override the service umask during git clone. Close
        # the new root before exposing it to the coding confinement binder.
        # Retained workspaces require explicit owner reconciliation instead.
        fd = os.open(path, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        try:
            info = os.fstat(fd)
            if info.st_uid != os.getuid():
                raise AdmissionError('Workspace ownership or permissions')
            # Git may inherit defaults on source folders as well as the root.
            # Only new clones may be changed; retained contents stay refuse-only.
            for _, _, filenames, directory_fd in os.fwalk('.', dir_fd=fd, follow_symlinks=False):
                if os.fstat(directory_fd).st_uid != os.getuid():
                    raise AdmissionError('Workspace ownership or permissions')
                if created:
                    os.fchmod(directory_fd, 0o700)
                    try:
                        os.removexattr(directory_fd, 'system.posix_acl_default')
                    except OSError as error:
                        if error.errno != errno.ENODATA:
                            raise
                if os.fstat(directory_fd).st_mode & 0o022:
                    raise AdmissionError('Workspace ownership or permissions')
                try:
                    os.getxattr(directory_fd, 'system.posix_acl_default')
                except OSError as error:
                    if error.errno != errno.ENODATA:
                        raise
                else:
                    raise AdmissionError('Workspace inherited default ACL')
                for name in filenames:
                    info = os.stat(name, dir_fd=directory_fd, follow_symlinks=False)
                    if stat.S_ISLNK(info.st_mode):
                        continue
                    file_fd = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK,
                                      dir_fd=directory_fd)
                    try:
                        info = os.fstat(file_fd)
                        if (not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid()
                            or info.st_nlink != 1):
                            raise AdmissionError('Workspace ownership or permissions')
                        if created:
                            # Preserve user execute without inherited access ACLs.
                            os.fchmod(file_fd, stat.S_IMODE(info.st_mode) & 0o700)
                            os.fsync(file_fd)
                        if os.fstat(file_fd).st_mode & 0o022:
                            raise AdmissionError('Workspace ownership or permissions')
                    finally:
                        os.close(file_fd)
                if created:
                    os.fsync(directory_fd)
        finally:
            os.close(fd)
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
        tick_lock = asyncio.Lock()
        async def current_tick(owner):
            # Native project loops share this CurrentWork and its continuation
            # permits. Serialize admission ticks, never the coding children.
            async with tick_lock:
                return await current_project_tick(owner)
        async def current_project_tick(owner):
            current.refresh()  # Before upstream config reload can skip candidate fetching.
            await current.continue_validation()
            await current.continue_native_harness(native_harness_adapter_factory,
                                                 linear_client=getattr(owner, '_linear', None))
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
                'child_tree_gone','scope_violations','output_sha256','accepted_delivery',
                'requested_model','resolved_model','resolution_status')}
        owner.ledger.record_stage(project='offmenu', workflow='bounded-adapter-proof',
                                  issue_id=issue.id, issue=issue.identifier,
                                  title=issue.title, state=state_name, run=1,
                                  status=attempt.status, report=None,
                                  tokens=attempt.total_tokens, cost_usd=0,
                                  tool_calls=0, tool_errors=0, artifacts=0,
                                  model=attempt.model, duration_s=None)
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
        attempt.status = ('succeeded' if result['status'] == 'succeeded'
                          and result.get('child_tree_gone') is True else 'failed')
        attempt.session_id = result.get('session_id')
        observed_model = result.get('resolved_model')
        attempt.model = (observed_model if result.get('resolution_status') == 'observed'
                         and isinstance(observed_model, str) and observed_model.strip() else None)
        usage = result.get('usage', {})
        attempt.input_tokens = usage.get('input_tokens', 0)
        attempt.output_tokens = usage.get('output_tokens', 0)
        attempt.total_tokens = attempt.input_tokens+attempt.output_tokens
        attempt.error = (None if attempt.status == 'succeeded' else
                         ('child_termination_unverified' if result['status'] == 'succeeded'
                          else result['status']))
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
    config, _, _ = current_config(runtime)
    root = Path(config['runtime_root'])
    if (not root.is_absolute() or root != root.resolve() or root.name != 'stokowski'
        or root.parent.name != '.delivery' or not runtime.resolve().is_relative_to(root)):
        raise AdmissionError('current_private_root')
    with (root/'coordinator.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX|fcntl.LOCK_NB)
        return await _run(runtime, duration, dry_run, True)


def validate_project_workflow(config, policy, routes, errors):
    """Admit native project configs under one existing global agent ceiling."""
    projects = config.projects
    slugs = [p.tracker.project_slug for p in projects]
    if (errors or len(slugs) != len(routes) or len(set(slugs)) != len(slugs)
        or set(slugs) != {r['project_slug'] for r in routes}
        or config.agent.max_concurrent_agents != policy['symphony']['max_concurrent_agents']
        or config.server.port is not None
        or any(s.runner != 'codex' for p in projects for s in p.all_states().values() if s.type == 'agent')
        or any(vars(p.hooks).get(k) for p in projects
               for k in ('after_create','before_run','after_run','before_remove','on_stage_enter'))
        or any(s.hooks is not None for p in projects for s in p.all_states().values())):
        raise AdmissionError('Workflow violates selected OffMenu contract')


async def _run(runtime, duration, dry_run=False, current_mode=False):
    verify_install(runtime)
    current = CurrentWork(runtime) if current_mode else None
    if current and (runtime/'cancel.json').exists():
        current.state.update(stopped=True, cancellation_requested=True)
        current.save()
        return
    manifest = None if current else load_manifest(runtime/'manifest.json',expected_branch=None)
    route = current.route if current else project_route(manifest['project_id'])
    policy = json.loads((runtime/'capacity-policy.json').read_text())
    if policy != json.loads((SOURCE/'tools/delivery/capacity-policy.json').read_text()):
        raise AdmissionError('Runtime policy differs from reviewed source')
    key = credential()
    orchestration = install_adapters(runtime, manifest, key, current)
    from stokowski.config import parse_workflow_file, validate_config
    definition = parse_workflow_file(runtime/'workflow.yaml')
    projects = definition.config.projects
    routes = current.routes if current else [route]
    validate_project_workflow(definition.config, policy, routes, validate_config(definition.config))
    from stokowski.linear import LinearClient
    client = LinearClient(endpoint='https://api.linear.app/graphql', api_key=key)
    try:
        candidates = []
        for project in projects:
            candidates.extend(await client.fetch_candidate_issues(
                project.tracker.project_slug, project.active_linear_states()))
    finally:
        await client.close()
    if not current and {i.id for i in candidates} != {t['issue_id'] for t in manifest['tasks'].values()}:
        raise AdmissionError('Selected issues are not exactly the ready candidates')
    route_evidence = dict(project_routes=routes) if current and 'project_routes' in current.config else {}
    checkpoint(runtime/'admission.json', dict(project_id=route['project_id'], **route_evidence, selected=[i.identifier for i in candidates],
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
                   accepted_delivery=False, project_id=route['project_id'], **route_evidence))


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
            if remote.get('project',{}).get('id') != manifest['project_id']:
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


def qualification_child(runtime, reference):
    """Proposal only. Separate process keeps supervision signals off the owner loop."""
    from symphony_capacity import Pool, host_snapshot
    from symphony_codex import isolated_codex_environment
    from stokowski_worker import codex_command, supervise, summarize_events, git, changed_paths
    current = CurrentWork(runtime, read_only=True, qualification_only=True)
    policy, authority = current._intake_authority(reference)
    module = 'tools/delivery/symphony_launch.py'
    if current.config['source_sha256'].get(module) != file_sha(SOURCE/module):
        raise AdmissionError('qualification_provider_source_pin')
    if authority['decision'] != 'qualification-only':
        raise AdmissionError('qualification_only_required')
    spec = current._private_pin(authority['qualification'])
    workspace = current.private(spec['workspace'])
    directory = workspace/'qualification-runtime'
    if (git(workspace, 'rev-parse', 'HEAD') != spec['head']
        or git(workspace, 'branch', '--show-current') != spec['branch']):
        raise AdmissionError('qualification_source_drift')
    if (set(spec) != {'workspace', 'branch', 'head', 'prompt', 'resources', 'output'}
        or spec['output'] != 'qualification-output.json' or spec['resources'] != policy['resources']
        or spec['head'] != authority['source_head'] or not isinstance(spec['prompt'], str)
        or not spec['prompt'].strip() or workspace == SOURCE or SOURCE.is_relative_to(workspace)
        or not directory.is_dir() or (workspace/spec['output']).exists()
        or (runtime/'cancel.json').exists()):
        raise AdmissionError('qualification_spec_or_cancellation')
    parent_record = current.state.get('intake', {}).get(authority['issue'], {})
    if (parent_record.get('authority') != authority
        or parent_record.get('qualification_intent', {}).get('spec') != authority['qualification']):
        raise AdmissionError('qualification_owner_intent')
    before = changed_paths(workspace)
    if any(not name.startswith('qualification-runtime/') for name in before):
        raise AdmissionError('qualification_dirty_source')
    capacity = read_record(runtime/'capacity-policy.json')
    from symphony_launch import provider_proof
    proof = provider_proof(MODEL, capacity['symphony']['provider_session_ceiling'])
    binding = dict(branch=spec['branch'], head=spec['head'], owner=authority['owner'],
        write_roots=[spec['output']], resources=spec['resources'], task_sha256=digest(spec))
    lease = 'qualification-' + digest(dict(runtime=str(runtime), reference=reference))[:48]
    pool = Pool(capacity['symphony']['pool_path'], capacity)
    if pool.admit(lease, binding, proof, host_snapshot(workspace)).get('reused'):
        raise AdmissionError('qualification_retained_lease')
    result = dict(status='uncertain', child_tree_gone=False, origin='native-qualification', lease=lease,
        requested_model=MODEL, requested_effort='medium', provider_route='codex-chatgpt',
        resolved_model=None, resolution_status='unknown', accepted_delivery=False, authority='proposal-only')
    checkpoint(directory/'intent.json', dict(lease=lease, binding=binding, provider=proof))
    try:
        command = codex_command(workspace, workspace/spec['output'])
        command[command.index('--sandbox')+1] = 'read-only'
        with isolated_codex_environment(child_environment(os.environ), directory) as environment:
            result.update(supervise(command, spec['prompt'], workspace, environment, directory,
                policy['timeout_seconds'], spec['resources'], capacity['windmill']['computation_subprocesses_per_job']))
        if (directory/'stdout.jsonl').exists():
            result.update(summarize_events(directory/'stdout.jsonl'))
            if result.get('resolved_model') is None:
                result['resolution_status'] = 'unknown'
        output = read_record(workspace/spec['output'])
        if (set(output) != {'schema', 'proposal', 'missing_inputs'}
            or output['schema'] != 'offmenu-qualification-proposal/1'
            or not isinstance(output['proposal'], str) or not isinstance(output['missing_inputs'], list)
            or any(not isinstance(x, str) for x in output['missing_inputs'])):
            raise AdmissionError('qualification_output_schema')
        result['output_sha256'] = file_sha(workspace/spec['output'])
        result['proposal'] = output
        if (git(workspace, 'rev-parse', 'HEAD') != spec['head']
            or git(workspace, 'branch', '--show-current') != spec['branch']
            or any(name != spec['output'] and not name.startswith('qualification-runtime/')
                   for name in changed_paths(workspace))):
            raise AdmissionError('qualification_source_drift')
    except Exception as error:
        result.update(status='failed' if result['child_tree_gone'] else 'uncertain', reason=str(error))
    finally:
        checkpoint(directory/'result.json', result)
        if result['child_tree_gone'] is True and result['status'] != 'uncertain':
            pool.finish(lease, True, 'succeeded' if result['status'] == 'succeeded' else 'failed')
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--runtime', required=True, type=Path)
    parser.add_argument('--qualification-reference')
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
    if args.qualification_reference:
        qualification_child(runtime, args.qualification_reference)
        raise SystemExit(0)
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
