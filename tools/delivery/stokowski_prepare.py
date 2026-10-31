"""Prepare one immutable OffMenu Stokowski execution manifest, without dispatch."""
import argparse
import fcntl
import hashlib
import math
import os
import tempfile
import time
import json
from pathlib import Path
import shutil
import subprocess

from symphony_workspace import checkpoint
from stokowski_adapter import SOURCE, PROJECT, MODEL, file_sha, CurrentWork
from symphony_tasks import project_route, PROJECT_ROUTES


def _publication_origin_claim(view, trigger, review, original):
    """Lock a live Journal or requalify the distinct completed-native origin.

    Completed Engine evidence has no operations Journal. It must retain its
    own exact proof instead of creating an empty database as a substitute.
    """
    from contextlib import nullcontext
    from types import SimpleNamespace
    from symphony_capacity import AdmissionError, digest
    from stokowski_completed import KIND, qualify
    from stokowski_operations import Journal

    if digest(review) != trigger['review_sha256']:
        raise AdmissionError('publication_successor_review_drift')
    if review.get('decision', {}).get('kind') == KIND:
        if qualify(view, trigger['issue']) != review:
            raise AdmissionError('publication_successor_completed_evidence_drift')
        return nullcontext()
    operation_root = original/'operations'
    if (operation_root != operation_root.resolve()
        or not (operation_root/'operations.sqlite').is_file()):
        raise AdmissionError('publication_successor_journal_missing')
    return Journal.claim(SimpleNamespace(root=operation_root),
                         review['integration_binding']['validation_operation_key'])


def prepare_publication(handoff_path, *, handoff_sha256, authenticated_caller,
                        provider_proof):
    """Publish only metadata through an existing trusted owner's invocation.

    Both callbacks are capabilities supplied by that invocation, never decoded
    from JSON or exposed as CLI arguments. ``provider_proof(model, ceiling)``
    reuses the launcher proof contract through an independently trusted adapter;
    this function never probes a provider. Subsequent execution still requires
    fresh provider/resource/ownership admission. A pinned file is authorization
    mapping, not authentication. The caller must trust the adapter implementation.
    """
    from symphony_capacity import AdmissionError, digest, overlap
    from symphony_tasks import load_manifest

    def require(condition, reason):
        if not condition:
            raise AdmissionError('publication_' + reason)

    def canonical(value):
        path = Path(value)
        require(path.is_absolute() and path == path.resolve(), 'canonical_path')
        return path

    def read(path):
        def unique(pairs):
            result = {}
            for key, value in pairs:
                require(key not in result, 'duplicate_key')
                result[key] = value
            return result
        return json.loads(path.read_bytes(), object_pairs_hook=unique)

    def pinned(ref):
        path = canonical(ref['path'])
        require(file_sha(path) == ref['sha256'], 'pin')
        return read(path)

    require(callable(authenticated_caller) and callable(provider_proof), 'trusted_adapters_required')
    handoff_path = canonical(handoff_path)
    handoff = pinned(dict(path=str(handoff_path), sha256=handoff_sha256))
    require(canonical(handoff['directory']) == handoff_path.parent, 'handoff_directory')
    packet = pinned(handoff['task_packet'])
    config = pinned(handoff['owner_config'])
    require(packet['owner_config'] == handoff['owner_config'], 'config_binding')
    require(packet['schema'] == 'offmenu-owner-bound-preexecution-task/1'
            and config['schema'] == 'offmenu-source-owner-publication-config/1', 'schema')
    owner = config['owner']
    require(packet['owner'] == owner and config['repository'] == packet['source']['repository'], 'owner')
    association = config['caller_association']
    # Do not pass packet/config to the adapter: it observes its authenticated
    # session independently. Stored observations never satisfy this comparison.
    observed = authenticated_caller()
    require(observed == {k: association[k] for k in ('service', 'principal_id', 'login')}, 'caller')
    require(handoff['authenticated_principal'] ==
            dict(id=association['principal_id'], login=association['login']), 'caller_mapping')
    pinned(association['authenticated_observation'])
    require(config['publication_authority']['automatic_start'] is False
            and config['publication_authority']['historical_workers_resume'] is False
            and config['publication_authority']['require_normal_execution_admission'] is True, 'authority')
    require(packet['selected_current'] == config['selected_current'], 'current_binding')
    for key in ('source_issue', 'execution_outcome'):
        require(packet[key] == handoff[key], 'issue_binding')
    successor = packet.get('origin') == 'qualified-successor-v1'
    require(packet.get('origin') in (None, 'qualified-successor-v1'), 'origin')
    if not successor:
        require(packet['source_issue']['identifier'] == 'UIF-119'
                and packet['execution_outcome']['identifier'] == 'UIF-106'
                and packet['source_issue']['project_id'] != packet['execution_outcome']['project_id'], 'issue_relationship')
    require(packet['source']['base'] == handoff['source_base'], 'source_binding')
    claim_ref = config['repository_claim']
    claim = pinned(claim_ref)
    binding = pinned(dict(path=claim_ref['binding_path'], sha256=claim_ref['binding_sha256']))
    require(claim == dict(owner=owner, directory=str(Path(claim_ref['binding_path']).parent),
                          binding_sha256=claim_ref['binding_identity_sha256'])
            and digest(binding) == claim_ref['binding_identity_sha256']
            and binding['owner'] == owner and binding['repository'] == config['repository']
            and binding['issue_id'] == packet['execution_outcome']['uuid'], 'claim')
    source = canonical(packet['source']['source_checkout'])
    for argv, expected in ((['rev-parse', 'HEAD'], packet['source']['base']),
                           (['branch', '--show-current'], packet['source']['branch'])):
        require(subprocess.check_output(['git', '-C', str(source), *argv], text=True).strip() == expected,
                'source_drift')
    for key in ('manifest', 'request'):
        require(packet[key] == handoff[key], 'input_binding')
    manifest = pinned(packet['manifest'])
    request = pinned(packet['request'])
    load_manifest(canonical(packet['manifest']['path']), expected_head=packet['source']['base'],
                  expected_branch=packet['source']['branch'])
    issue = packet['execution_outcome']['identifier']
    require(set(manifest['tasks']) == {issue}
            and manifest['project_id'] == packet['execution_outcome']['project_id']
            and manifest['label'] == packet['unit_id'], 'manifest_issue')
    task = manifest['tasks'][issue]
    staged = 'stage' in task
    require(task['owner'] == owner and task['issue_id'] == packet['execution_outcome']['uuid']
            and (task['input_paths'] if staged else task['allowed_paths']) == packet['scope'] and task['acceptance'] == packet['acceptance']
            and task['resources'] == packet['resources']
            and (staged or successor or packet['scope'] == ['tools/delivery/stokowski_prepare.py',
                                    'tests/delivery/test_stokowski_prepare_publication.py']), 'task_binding')
    require(set(request) == {'prompt', 'timeout_seconds'} and isinstance(request['prompt'], str)
            and request['prompt'].strip() and type(request['timeout_seconds']) is int
            and 1 <= request['timeout_seconds'] <= 600, 'request')
    selected = packet['selected_current']
    root, runtime, coordinator, catalog = (canonical(selected[k]) for k in
        ('runtime_root', 'task_runtime', 'coordinator_runtime', 'catalog_path'))
    require(root.is_dir() and root.name == 'stokowski' and root.parent.name == '.delivery'
            and runtime.parent == root and coordinator.parent == root and runtime != coordinator
            and catalog.is_relative_to(root) and not catalog.is_relative_to(runtime)
            and not catalog.is_relative_to(coordinator), 'private_paths')
    if staged:
        require(config.get('stage_binding') == task['stage_binding']
                and packet.get('stage') == task['stage'], 'stage_owner_binding')
        require(all(packet['inputs'].get(k) == v
                    for k,v in task['stage_binding']['inputs'].items()), 'stage_input_coverage')
        original = canonical(task['stage_binding']['entry']['runtime'])
        require(original not in (runtime, coordinator), 'stage_original_runtime')
        # The existing coordinator's owner/config/source gates and continuation
        # qualifier are the authority. No native evidence is copied to runtime.
        consumer = CurrentWork(coordinator, read_only=True, qualification_only=True)
        require(consumer.config['owner'] == owner and consumer.root == root
                and consumer.catalog == catalog, 'stage_coordinator')
        consumer.stage_origin(issue, task)
        if task['stage_binding']['entry'].get('origin') == 'reviewed-source-v1':
            require(original.is_relative_to(root) and original.is_dir(), 'reviewed_validation_runtime')
    # This is the sole publication lock across catalogs in the selected root.
    lock = canonical(root/'publication.lock')
    fd = os.open(lock, os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        journal_path = canonical(root/(runtime.name + '-publication.json'))
        identity = dict(handoff_sha256=handoff_sha256, packet=handoff['task_packet'],
                        config=handoff['owner_config'])
        prior = read(journal_path) if journal_path.exists() else None
        require(prior is None or prior['identity'] == identity, 'immutable_binding_conflict')
        publication_owner = CurrentWork(coordinator,read_only=True,qualification_only=True) if successor else None
        if prior is None and publication_owner and publication_owner.owner_custody:
            before_bytes = publication_owner.catalog_bytes()
            require(hashlib.sha256(before_bytes).hexdigest()==packet['inputs'][str(catalog)],'catalog_drift')
            baseline = json.loads(before_bytes)
        else:
            baseline = pinned(dict(path=str(catalog), sha256=packet['inputs'][str(catalog)])) if prior is None else prior['catalog_before']
        require(set(baseline) == {'version', 'entries'} and baseline['version'] == 1
                and isinstance(baseline['entries'], list), 'catalog')
        # Validate every original input, except the catalog's own publication
        # mutation, whose exact before/after bytes are reconciled below.
        for name, sha in packet['inputs'].items():
            if name != str(catalog):
                require(file_sha(canonical(name)) == sha, 'input_pin')
        for ref in (packet['manifest'], packet['request'], packet['owner_config'],
                    packet['provider_requirements'], packet['installation']):
            name = ref.get('path', ref.get('manifest_path'))
            sha = ref.get('sha256', ref.get('manifest_sha256'))
            require(packet['inputs'].get(name) == sha, 'input_coverage')
        for ref in (claim_ref, association['authenticated_observation']):
            require(packet['inputs'].get(ref['path']) == ref['sha256'], 'input_coverage')
        require(packet['inputs'].get(claim_ref['binding_path']) == claim_ref['binding_sha256'], 'input_coverage')
        policy_path = canonical(source/'tools/delivery/capacity-policy.json')
        require(packet['inputs'].get(str(policy_path)) == file_sha(policy_path), 'policy_pin')
        installation_record = pinned(dict(path=packet['installation']['manifest_path'],
                                          sha256=packet['installation']['manifest_sha256']))
        require(installation_record['source_revision'] == packet['installation']['source_revision']
                and len(installation_record['installed_source_sha256']) ==
                packet['installation']['installed_files_verified_statically'], 'installation_binding')
        active = publication_owner._active_catalog(baseline) if successor else {
            str(index): value for index, value in enumerate(baseline['entries'])}
        replacing = 'replacement_of' in packet
        previous = None
        if replacing:
            require(successor and publication_owner.owner_custody, 'replacement_owner_grant')
            if prior is None:
                previous, _, _ = publication_owner._qualified_replacement(packet)
            else:
                previous = active.get(issue)
                require(previous is not None and digest(previous) == packet['replacement_of']['entry_sha256'],
                        'replacement_previous')
                # Recovery requalifies the original refusal and projected new
                # unit, rather than treating the retained journal as authority.
                publication_owner._replacement_witness(previous,
                    publication_owner._successor_entry(packet), manifest=manifest,
                    request_sha256=packet['request']['sha256'])
        for entry in active.values():
            replaced = replacing and entry == previous
            other_runtime = canonical(entry['runtime'])
            require(other_runtime.is_relative_to(root) and other_runtime not in (runtime, coordinator)
                    and (replaced or (entry['issue'] != issue and entry['issue_id'] != task['issue_id'])), 'catalog_conflict')
            other_admission = pinned(dict(path=str(other_runtime/'current-admission.json'),
                                          sha256=entry['admission_sha256']))
            other_manifest = pinned(dict(path=str(other_runtime/'manifest.json'),
                                         sha256=other_admission['manifest_sha256']))
            if not staged:
                reusable = False
                if successor:
                    consumer = CurrentWork(coordinator, read_only=True, qualification_only=True)
                    consumer.entries = active
                    if replaced:
                        consumer._replacement_witness(entry, consumer._successor_entry(packet),
                            manifest=manifest, request_sha256=packet['request']['sha256'])
                        reusable = True
                    else:
                        reusable = consumer._scope_reusable(entry['issue'])
                require(reusable or not any(overlap(a, b) for a in packet['scope']
                                for t in other_manifest['tasks'].values() for b in t['allowed_paths']), 'scope_overlap')
        policy = policy_path.read_bytes()
        installation = canonical(packet['installation']['manifest_path']).read_bytes()
        admission = dict(version=1, owner=owner, issue=issue, issue_id=task['issue_id'], source=str(source),
                         manifest_sha256=packet['manifest']['sha256'], request_sha256=packet['request']['sha256'],
                         policy_sha256=hashlib.sha256(policy).hexdigest(),
                         installation_sha256=hashlib.sha256(installation).hexdigest(),
                         inputs={k: v for k, v in packet['inputs'].items() if k != str(catalog)})
        entry = dict(issue=issue, issue_id=task['issue_id'], runtime=str(runtime),
                     admission_sha256=hashlib.sha256(_publication_bytes(admission)).hexdigest())
        if 'replacement_of' in packet:
            require(successor, 'replacement_origin')
            entry['replacement_of'] = packet['replacement_of']
        if prior is None:
            requirements = pinned(packet['provider_requirements'])
            proof = provider_proof(requirements['requested_model'], requirements['session_ceiling'])
            checked = proof.get('checked_at')
            require(proof.get('route') == requirements['route'] and proof.get('available') is True
                    and proof.get('requested_model') == requirements['requested_model']
                    and type(checked) in (int, float) and math.isfinite(checked)
                    and checked <= time.time() + requirements['checked_at_max_future_skew_seconds']
                    and time.time() - checked <= requirements['max_age_seconds']
                    and type(proof.get('session_ceiling')) is int
                    and 1 <= proof['session_ceiling'] <= requirements['session_ceiling'], 'provider_proof')
            blobs = {'manifest.json': canonical(packet['manifest']['path']).read_bytes(),
                     'requests/'+issue+'.json': canonical(packet['request']['path']).read_bytes(),
                     'capacity-policy.json': policy, 'installation.json': installation,
                     'provider-proof.json': _publication_bytes(proof)}
            blobs['current-admission.json'] = _publication_bytes(admission)
            # Coordinator preparation remains the existing separate finite CLI
            # operation. Never create/overwrite its state or acquire its locks.
            captured = before_bytes.decode('utf-8') if publication_owner and publication_owner.owner_custody else catalog.read_text()
            if publication_owner and publication_owner.owner_custody:
                require(publication_owner.catalog_bytes()==before_bytes,'catalog_drift')
            prior = dict(identity=identity, catalog_before=baseline,
                         catalog_before_bytes=captured,
                         catalog_after=dict(version=1, entries=baseline['entries']+[entry]),
                         files={k: v.decode() for k, v in blobs.items()},
                         requested=dict(model=requirements['requested_model'], effort=requirements['requested_effort'],
                                        provider=requirements['route'], resources=packet['resources']),
                         observed=dict(resolved_model=None, resources=None, resolution_status='unobserved'),
                         execution_admission='required-before-execution')
            require(not runtime.exists(), 'runtime_exists')
            _publication_write(journal_path, _publication_bytes(prior))
        # Recovery consumes the same immutable plan, never new task bytes or
        # arbitrary paths from a damaged journal. The private journal is trusted
        # durable state, not an authentication or execution receipt.
        require(hashlib.sha256(prior['catalog_before_bytes'].encode()).hexdigest() ==
                packet['inputs'][str(catalog)]
                and json.loads(prior['catalog_before_bytes']) == baseline
                and prior['catalog_after'] == dict(version=1, entries=baseline['entries']+[entry]),
                'journal_catalog_binding')
        expected_hashes = {'manifest.json': packet['manifest']['sha256'],
                           'requests/'+issue+'.json': packet['request']['sha256'],
                           'capacity-policy.json': admission['policy_sha256'],
                           'installation.json': admission['installation_sha256'],
                           'current-admission.json': entry['admission_sha256']}
        require(set(prior['files']) == set(expected_hashes) | {'provider-proof.json'}
                and all(hashlib.sha256(prior['files'][name].encode()).hexdigest() == sha
                        for name, sha in expected_hashes.items()), 'journal_file_binding')
        after = _publication_bytes(prior['catalog_after'])
        current = publication_owner.catalog_bytes() if publication_owner and publication_owner.owner_custody else catalog.read_bytes()
        # Original formatting is allowed only for the pinned original catalog.
        require(current == after or hashlib.sha256(current).hexdigest() == packet['inputs'][str(catalog)],
                'catalog_drift')
        require(current != after or runtime.is_dir(), 'exposed_runtime_missing_reconcile')
        if successor and current != after:
            consumer = CurrentWork(coordinator,read_only=True,qualification_only=True)
            if replacing:
                qualified_previous, qualified_entry, _ = consumer._qualified_replacement(packet)
                require(qualified_previous == previous and qualified_entry == entry,
                        'replacement_recovery_binding')
            consumer.catalog_transition(current,after)
        if not runtime.exists():
            stage = Path(tempfile.mkdtemp(prefix='.'+runtime.name+'-', dir=root))
            for name in ('requests', 'attempts', 'workspaces'):
                (stage/name).mkdir(mode=0o700)
            for name, content in prior['files'].items():
                _publication_write(stage/name, content.encode())
            _publication_sync(stage)
            os.rename(stage, runtime)
        for name, content in prior['files'].items():
            require(canonical(runtime/name).read_bytes() == content.encode(), 'runtime_drift')
        require({p.relative_to(runtime).as_posix() for p in runtime.rglob('*') if p.is_file()}
                == set(prior['files']), 'retained_effect_requires_reconciliation')
        # Visible rename/replace bytes do not establish parent durability after
        # an earlier fsync failure. Recovery must retry both barriers as needed.
        _publication_sync(root)
        if current == after:
            _publication_sync(catalog.parent)
            return dict(status='duplicate', runtime=str(runtime), dispatches=0)
        if successor:
            trigger = packet['trigger']
            # Resolve the authoritative validation runtime through the existing
            # origin contract (a stage entry may refer to another runtime).
            view = CurrentWork(coordinator, read_only=True, qualification_only=True)
            view.entries = {trigger['issue']: trigger['entry']}
            original, original_manifest, _ = view.context(trigger['issue'], review=True)
            original_task = original_manifest['tasks'][trigger['issue']]
            if 'stage' in original_task:
                _, original, _ = view.stage_origin(trigger['issue'], original_task)
            original = canonical(original)
            require(original.is_relative_to(root) and original not in (runtime, coordinator),
                    'successor_original_runtime')
            review = read(coordinator/('unit-review-' + trigger['issue'] + '.json'))
            # Lock order remains publication -> original Journal for that
            # origin. Completed-native evidence is requalified without a fake
            # Journal; qualify_successor repeats its proof at the write boundary.
            with _publication_origin_claim(view, trigger, review, original):
                consumer = CurrentWork(canonical(packet['selected_current']['coordinator_runtime']),
                                       read_only=True, qualification_only=True)
                identity = consumer.qualify_successor(dict(path=str(handoff_path), sha256=handoff_sha256), packet, config)
                pending = consumer.state.get('successor_request', {})
                require(pending.get('identity') == identity and pending.get('status') == 'pending'
                        and pending.get('handoff') == dict(path=str(handoff_path), sha256=handoff_sha256)
                        and pending.get('owner_config') == handoff['owner_config'], 'successor_pending')
                consumer.catalog_transition(current,after)
                _publication_write(catalog, after)
        else:
            _publication_write(catalog, after)
        return dict(status='published', runtime=str(runtime), dispatches=0)
    finally:
        os.close(fd)


def _publication_bytes(value):
    return (json.dumps(value, sort_keys=True, indent=2) + '\n').encode()


def _publication_sync(directory):
    fd = os.open(directory, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def _publication_write(path, content):
    """Durable replacement under the publication lock, including parent fsync."""
    fd, temporary = tempfile.mkstemp(prefix='.'+path.name+'-', dir=path.parent)
    try:
        with os.fdopen(fd, 'wb') as stream:
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
        _publication_sync(path.parent)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--runtime', required=True, type=Path)
    parser.add_argument('--current', action='store_true', help='Prepare caller-owned current polling root; never starts a process. Example: --current --runtime /repo/.delivery/stokowski/current --runtime-root /repo/.delivery/stokowski --catalog /repo/.delivery/stokowski/catalog.json --owner existing-owner')
    parser.add_argument('--runtime-root', type=Path, help='Existing canonical private .delivery/stokowski root')
    parser.add_argument('--catalog', type=Path, help='Existing owner-qualified v1 catalog; see CurrentWork schema')
    parser.add_argument('--owner')
    parser.add_argument('--project-id', choices=tuple(PROJECT_ROUTES),
                        help='Exact selected project UUID; current mode defaults to legacy OffMenu')
    parser.add_argument('--manifest', type=Path)
    parser.add_argument('--prompt', type=Path)
    args = parser.parse_args()
    if args.current:
        if not args.runtime_root or not args.catalog or not args.owner or args.manifest or args.prompt:
            parser.error('--current requires --runtime-root, --catalog, --owner; task manifest/request stay in qualified task runtimes')
        root = args.runtime_root
        if (root != root.resolve() or not root.is_dir() or root.name != 'stokowski'
            or root.parent.name != '.delivery' or args.catalog != args.catalog.resolve()
            or not args.catalog.is_relative_to(root) or not args.catalog.is_file()):
            parser.error('Current references must be canonical under existing private Stokowski root')
    elif not args.manifest or not args.prompt:
        parser.error('Finite mode requires --manifest and --prompt')
    from symphony_tasks import load_manifest
    head = subprocess.check_output(['git','-C',str(SOURCE),'rev-parse','HEAD'],text=True).strip()
    manifest = None if args.current else load_manifest(args.manifest, expected_head=head,expected_branch=None)
    selected_project = (args.project_id or PROJECT) if args.current else manifest['project_id']
    if not args.current and args.project_id and args.project_id != selected_project:
        parser.error('--project-id must equal the immutable manifest project')
    route = project_route(selected_project)
    runtime = args.runtime.resolve()
    root = args.runtime_root if args.current else SOURCE/'.delivery/stokowski'
    if not runtime.is_relative_to(root) or runtime == root or runtime.exists() or (args.current and args.runtime != runtime):
        raise SystemExit('Select a new private Stokowski runtime directory')
    runtime.mkdir(parents=True, mode=0o700)
    for name in ('workspaces','requests','attempts'):
        (runtime/name).mkdir(mode=0o700)
    if not args.current:
        checkpoint(runtime/'manifest.json',manifest)
    shutil.copyfile(SOURCE/'tools/delivery/capacity-policy.json',runtime/'capacity-policy.json')
    shutil.copyfile((root if args.current else SOURCE/'.delivery/stokowski')/'installation.json',
                    runtime/'installation.json')
    (runtime/'task.md').write_text('Qualified immutable request is supplied by the existing owner.\n' if args.current else args.prompt.read_text())
    workflow = {
        'tracker':{'kind':'linear','project_slug':route['project_slug'],'api_key':'$OFFMENU_LINEAR_API_KEY'},
        'workspace':{'root':str(runtime/'workspaces')},
        'polling':{'interval_ms':5000}, 'agent':{'max_concurrent_agents':8,'max_retry_backoff_ms':10000},
        'claude':{'model':MODEL,'turn_timeout_ms':180000,'stall_timeout_ms':90000},
        'linear_states':{'todo':'Todo','active':'In Progress','review':'In Review',
                         'gate_approved':'OffMenu Verified','rework':'OffMenu Rework',
                         'terminal':['Done','Canceled','Duplicate']},
        'states':{
            'implement':{'type':'agent','runner':'codex','model':MODEL,'prompt':'task.md',
                         'linear_state':'active','transitions':{'complete':'evidence-pending'}},
            'evidence-pending':{'type':'gate','linear_state':'review','rework_to':'implement',
                                'transitions':{'approve':'accepted'}},
            'accepted':{'type':'terminal','linear_state':'terminal'}},
        'server':{'host':'127.0.0.1'}
    }
    if args.current:
        # A qualified unit is only part of its parent outcome. Parent acceptance
        # remains with the existing integration/full-parent contract.
        workflow['states']['evidence-pending']['transitions'] = {'approve':'evidence-pending'}
        # The pinned schema requires a terminal definition; it is unreachable
        # in current mode, and the adapter independently blocks terminal effects.
    # JSON is a YAML subset, avoiding an unpinned dependency in this preparer.
    (runtime/'workflow.yaml').write_text(json.dumps(workflow,indent=2)+'\n')
    if args.current:
        names = ('stokowski_adapter.py','stokowski_worker.py','stokowski_prepare.py',
                 'symphony_capacity.py','symphony_tasks.py','symphony_workspace.py',
                 'symphony_codex.py','symphony_protocol.py','windmill_runner.py',
                 'stokowski_operations.py','stokowski_stage.py','stokowski_unit_review.py',
                 'integration-gateway.mjs')
        paths = ['tools/delivery/'+name for name in names] + ['src/offmenu/delivery/integration.py']
        checkpoint(runtime/'current.json', {
            'version':1, 'owner':args.owner, 'runtime_root':str(root),
            **({'project_route':route} if args.project_id else {}),
            'catalog':str(args.catalog), 'source_head':head,
            'source_sha256':{name:file_sha(SOURCE/name) for name in paths},
            'workflow_sha256':file_sha(runtime/'workflow.yaml'),
            'installation_sha256':file_sha(runtime/'installation.json'),
            'policy_sha256':file_sha(runtime/'capacity-policy.json')})
        CurrentWork(runtime)
    print(json.dumps({'status':'prepared','source_head':head,'project_id':route['project_id'],
                      'runtime':str(runtime),'coding_ceiling':8,'model_calls':False}))


if __name__ == '__main__':
    main()
