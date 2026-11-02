"""One admitted CurrentWork boundary; no loop, queue, credentials or dispatch CLI.

Owner adapters are executable installation context, never fields from issue JSON.
The existing CurrentWork admission and transaction journal remain authoritative.
"""
from dataclasses import dataclass
import inspect
import json
from typing import Callable

from native_harness_contract import fingerprint, validate_handoff, validate_release_candidate
from linear_delivery import plan_delivery
from release_qualification import validate_qualification
from offmenu.delivery.engine import Engine, digest, verify_outputs
from offmenu.delivery.status import project_native_handoff


class RuntimeHold(ValueError):
    pass


def require(ok, code):
    if not ok:
        raise RuntimeHold(code)


@dataclass(frozen=True)
class OwnerBinding:
    """Selected by sealed owner config; authorize must verify that actual custody.

    packet_sha256 pins policy/handoff/candidate/Linear/release inputs together.
    operation_id is the EXISTING publisher/metadata transaction, not a new lease.
    """
    issue_id: str
    project_id: str
    owner: str
    packet_sha256: str
    operation_id: str
    phase: str
    unit_sha256: str


@dataclass(frozen=True)
class OwnerAdapters:
    """Trusted installed functions. No callback/module names are read from JSON.

    authorize(current, issue, binding): True only after sealed owner custody check.
    load(binding): return pinned JSON packet from existing private custody.
    engine(binding): existing admitted Engine instance, or None while incomplete.
    review(current, issue, binding): original packet for CurrentWork._check_unit_review.
    observe(binding): read existing transaction journal; never mutate/retry effects.
    step(binding, context): one existing scoped transaction with durable intent and
      readback in that SAME journal. Unknown effects use observe, never step.
    """
    authorize: Callable
    load: Callable
    engine: Callable
    review: Callable
    observe: Callable
    step: Callable
    # Integration-only alternative; never selected by a coding child or used
    # for release. Existing six-argument adapters retain the Engine contract.
    integration_acceptance: Callable | None = None
    # Original-native publication/review preparation, never a merge or Engine.
    prepare_unit: Callable | None = None


async def resolved(value):
    return await value if inspect.isawaitable(value) else value


def transaction(value, binding):
    fingerprint(value)
    require(isinstance(value, dict) and set(value) == {
        'operation_id', 'status', 'child_tree_gone'}, 'transaction_shape')
    require(value['operation_id'] == binding.operation_id, 'transaction_identity')
    require(value['status'] in ('ready', 'pending', 'unknown', 'verified', 'denied', 'failed'),
            'transaction_status')
    require(type(value['child_tree_gone']) is bool, 'transaction_cleanup')
    return json.loads(json.dumps(value))


def engine_acceptance(engine, handoff, candidate):
    """Reverify real Engine bytes without running or resetting any command."""
    require(type(engine) is Engine, 'engine_evidence_missing')
    require(engine.task.get('handoff') == handoff
            and engine.task.get('release_candidate') == candidate, 'engine_native_binding')
    engine.cancelled()
    engine.verify_source()
    require(engine.execution_evidence(allow_recheck=False), 'engine_execution_incomplete')
    outputs = verify_outputs(engine.root, engine.task)
    path = engine.directory / 'accepted.json'
    require(path.is_file() and not path.is_symlink(), 'engine_acceptance_missing')
    from release_qualification import read_json
    record = read_json(path)
    require(record.get('status') == 'accepted' and record.get('task_id') == engine.task['id']
            and record.get('owner') == handoff['owner']
            and record.get('revision') == handoff['source']['head']
            and record.get('task_sha256') == digest(engine.task)
            and record.get('branch') == engine.branch
            and record.get('native_harness') == engine.native_harness
            and record.get('outputs') == outputs, 'engine_acceptance_binding')
    return record


def review_coverage(review, handoff, candidate):
    """Bind an ORIGINAL-reader-qualified review to the actual Engine candidate.

    Call only after CurrentWork._check_unit_review. There is no implicit
    feature->develop/release equivalence: changed candidates need their own
    independently qualified exact-source coverage, through the original reader.
    """
    if review.get('origin') == 'native-readonly-review-v1':
        source = review['source']
        facts = {key: source[key] for key in ('head', 'base', 'tree', 'branch', 'outputs')}
        require(review['verdict'] == 'accept' and not review['findings'], 'review_not_accepted')
    else:
        original = review['integration_binding']
        facts = {key: original[key] for key in ('head', 'base', 'tree', 'outputs')}
        facts['branch'] = original['head_branch']
    selected = candidate['source'] if candidate else handoff['source']
    outputs = candidate['artifacts'] if candidate else handoff['outputs']
    expected = {key: selected[key] for key in ('head', 'base', 'tree', 'branch')}
    expected['outputs'] = {item['path']: item['sha256'] for item in outputs}
    require(fingerprint(facts) == fingerprint(expected), 'review_candidate_coverage')
    return {'source_sha256': fingerprint(selected), 'outputs_sha256': fingerprint(outputs),
            'review_sha256': fingerprint(review)}


def journal_acceptance(current, issue, reviewed_runtime, review, handoff, candidate):
    """Consume original-reader-qualified Journal v3 evidence, never Engine history.

    The caller has checked this exact review through _check_unit_review and
    review_coverage. Reopen its actual reviewed origin and terminal receipt;
    owner-selected context is an identity constraint, not an alternate reader.
    """
    from symphony_capacity import digest as journal_digest
    require(candidate is None and handoff['source']['target'] == 'develop',
            'journal_integration_only')
    if review.get('origin') == 'native-readonly-review-v1':
        current._check_unit_review(review)
        review_coverage(review,handoff,None)
        return native_journal_acceptance(current,issue,reviewed_runtime,handoff)
    if review.get('decision', {}).get('status') == 'merge-intent' and 'origin' not in review:
        return native_journal_acceptance(current,issue,reviewed_runtime,handoff,review=review)
    require(review.get('origin') == 'retained-typed-review-v1', 'journal_review_origin')
    _, manifest, _ = current.context(issue.identifier, review=True)
    task = manifest['tasks'][issue.identifier]
    runtime, spec, selected, state, _ = current.reviewed_origin(issue.identifier, task)
    require(str(runtime) == reviewed_runtime and spec['version'] == 3,
            'journal_owner_runtime')
    receipt_path = runtime / 'validation-receipt.json'
    terminal_receipt = current._check_reviewed_terminal(
        spec, state, task['stage_binding']['inputs'], receipt_path=receipt_path)
    source = handoff['source']
    outputs = {item['path']: item['sha256'] for item in handoff['outputs']}
    require(handoff['issue_id'] == issue.id == spec['issue_id']
            and handoff['project_id'] == manifest['project_id']
            and handoff['owner'] == spec['owner'] == current.config['owner']
            and all(source[key] == spec[key] for key in ('head', 'base', 'branch'))
            and outputs == spec['outputs'], 'journal_handoff_binding')
    # review_coverage binds the original reader's independently qualified tree,
    # branch and outputs to this handoff; the Journal binds the executed source.
    review_coverage(review, handoff, None)
    operation = handoff.get('operation')
    require(type(operation) is dict, 'journal_operation_missing')
    ref = operation['receipt']
    require(ref['path'] == str(receipt_path)
            or task['stage_binding']['inputs'].get(ref['path']) == ref['sha256'],
            'journal_receipt_pin')
    receipt = pinned_private(current, ref)
    require(receipt == terminal_receipt == review['validation_receipt']
            and journal_digest(receipt) == state['receipt_sha256']
            and operation['id'] == selected['operation_key']
            and operation['job_id'] == state['logical_job_id'] == receipt['job_id']
            and operation['policy_sha256'] == spec['policy_sha256']
            and operation['runner_sha256'] == spec['runner_sha256'] == receipt['runner_sha256']
            and operation['command_sha256'] == receipt['command_sha256']
            and operation['status'] == 'succeeded', 'journal_operation_binding')
    return {'origin': 'reviewed-source-journal-v3',
            'runtime': reviewed_runtime, 'operation_id': selected['operation_key'],
            'job_id': receipt['job_id'], 'receipt': ref,
            'source_sha256': fingerprint(source), 'outputs_sha256': fingerprint(outputs)}


def native_journal_acceptance(current, issue, native_runtime, handoff, *, review=None):
    """Original native-v1 reader; no Engine/retained-origin substitution."""
    import hashlib
    import sqlite3
    from symphony_capacity import digest as journal_digest
    from stokowski_adapter import read_record
    from stokowski_operations import bridge_arguments
    runtime,manifest,_=current.context(issue.identifier,review=True,observation=True)
    require('stage' not in manifest['tasks'][issue.identifier] and str(runtime) == native_runtime
            and handoff['source']['target'] == 'develop', 'native_journal_origin')
    qualified,_=current.validation_binding(issue.identifier,current.entries[issue.identifier])
    require(qualified == runtime, 'native_journal_runtime')
    selected=read_record(runtime/'validation-bindings.json')['issues'][issue.identifier]
    with sqlite3.connect((runtime/'operations/operations.sqlite').as_uri()+'?mode=ro',uri=True) as db:
        row=db.execute('SELECT spec,state FROM operations WHERE key=?',(selected['operation_key'],)).fetchone()
    require(row is not None, 'native_journal_missing')
    spec,state=map(json.loads,row)
    operation=handoff.get('operation');require(type(operation) is dict,'native_journal_operation')
    ref=operation['receipt']
    require(ref['path'] == str(runtime/'validation-receipt.json'), 'native_journal_receipt_path')
    receipt=pinned_private(current,ref)
    outputs={v['path']:v['sha256'] for v in handoff['outputs']};source=handoff['source']
    require(spec['version'] == 1 and spec['profile'] in ('enrichment-resilience-focused','delivery-unit-focused')
        and handoff['issue_id'] == issue.id == spec['issue_id'] and handoff['project_id'] == manifest['project_id']
        and handoff['owner'] == spec['owner'] == current.config['owner']
        and all(source[k] == spec[k] for k in ('head','base','branch')) and outputs == spec['outputs']
        and state.get('status') == 'succeeded' and state.get('cancel_requested') is False
        and not state.get('observation_intent') and not state.get('reconcile_required')
        and state.get('accepted_output_sha256') == outputs
        and state.get('acceptance_sha256') == spec['acceptance_sha256']
        and state.get('receipt_sha256') == journal_digest(receipt)
        and receipt.get('status') == 'succeeded' and receipt.get('exit_code') == 0
        and receipt.get('child_tree_gone') is True and receipt.get('reconcile_required') is False
        and receipt.get('job_id') == state['logical_job_id'] == operation['job_id']
        and receipt.get('runner_sha256') == spec['runner_sha256'] == operation['runner_sha256']
        and receipt.get('capacity_policy_sha256') == spec['policy_sha256'] == operation['policy_sha256']
        and receipt.get('command_sha256') == operation['command_sha256']
        == hashlib.sha256(bridge_arguments(spec)['command'].encode()).hexdigest()
        and operation['id'] == selected['operation_key'] and operation['status'] == 'succeeded',
        'native_journal_terminal_binding')
    if review is not None:
        require(review['validation_receipt'] == receipt,'native_journal_review_receipt')
        review_coverage(review,handoff,None)
    return dict(origin='native-journal-v1',runtime=native_runtime,operation_id=selected['operation_key'],
        job_id=receipt['job_id'],receipt=ref,source_sha256=fingerprint(source),outputs_sha256=fingerprint(outputs))


async def consume_boundary(current, issue, *, binding=None, adapters=None):
    """Call under CurrentWork's existing exclusive lock, at most ONE transaction.

    Missing optional binding leaves legacy v1 untouched. Binding/adapter objects
    come from reviewed owner configuration, not candidate fields or issue body.
    Exceptions retain a hold; nothing creates a replacement operation or lease.
    """
    base = {'version': 1, 'kind': 'native-harness-boundary-v1',
            'accepted_delivery': False, 'refill_eligible': False}
    if binding is None:
        return {**base, 'status': 'legacy', 'action': None}
    require(type(binding) is OwnerBinding and type(adapters) is OwnerAdapters,
            'owner_binding_required')
    result = {**base, 'operation_id': binding.operation_id, 'action': None}
    try:
        from stokowski_adapter import CurrentWork
        require(type(current) is CurrentWork, 'current_owner_required')
        require(binding.phase in ('linear', 'integration', 'release'), 'owner_phase')
        require(not current.read_only and not current.stopping, 'current_not_writable')
        current.guard()
        require(await resolved(adapters.authorize(current, issue, binding)) is True,
                'owner_authority_missing')
        _, original_manifest, _ = current.context(issue.identifier, review=True, observation=True)
        require(issue.id == binding.issue_id
                and current.entries[issue.identifier]['issue_id'] == issue.id
                and original_manifest['project_id'] == binding.project_id
                and current.config['owner'] == binding.owner, 'native_identity')
        # Preserve every existing manifest/admission/resource/provider/receipt gate.
        unit = current.gate_binding(issue, observation=True)
        require(unit['issue_id'] == binding.issue_id
                and unit['project_id'] == binding.project_id
                and fingerprint(unit) == binding.unit_sha256, 'native_gate_identity')
        packet = await resolved(adapters.load(binding))
        require(fingerprint(packet) == binding.packet_sha256, 'owner_packet_drift')
        require(isinstance(packet, dict) and set(packet) == {
            'policy', 'handoff', 'candidate', 'linear', 'release'}, 'owner_packet_shape')
        policy = packet['policy']
        handoff = validate_handoff(packet['handoff'], policy)
        require(handoff['issue_id'] == binding.issue_id
                and handoff['project_id'] == binding.project_id
                and handoff['owner'] == binding.owner, 'handoff_identity')
        candidate = (validate_release_candidate(packet['candidate'], policy)
                     if packet['candidate'] is not None else None)
        require(candidate is None or candidate['source'] == handoff['source'], 'candidate_source')
        projection = project_native_handoff(handoff, policy)
        operation = handoff.get('operation')
        require(not projection['recovery']['reconciliation_required']
                and (operation is None or operation['status'] == 'succeeded'),
                'validation_reconciliation_required')
        metadata = plan_delivery(packet['linear'], policy)
        outcomes = [v for v in packet['linear']['outcomes'] if v['id'] == issue.id]
        require(len(outcomes) == 1 and outcomes[0]['project_id'] == binding.project_id,
                'linear_outcome_identity')
        dependency = next(v for v in metadata['dependencies'] if v['issue_id'] == issue.id)
        # Metadata can create the very relation whose readback is still missing.
        # It never grants coding/publication eligibility or refill.
        if binding.phase != 'linear':
            require(dependency['dependencies_satisfied'], 'linear_dependencies_held')
            require(not metadata['holds'], 'linear_effect_reconciliation_required')
        if adapters.prepare_unit is not None:
            require(binding.phase == 'integration' and candidate is None,'native_preparation_phase')
            preparation=await resolved(adapters.prepare_unit(binding,handoff))
            if preparation is not None:
                return {**result,'status':'preparing-unit','effect':transaction(preparation,binding),
                        'next_action':'existing-native-publication-and-review'}
        # Observe BEFORE requesting any next transaction. Readback is authoritative.
        observed = transaction(await resolved(adapters.observe(binding)), binding)
        context = {'handoff': handoff, 'candidate': candidate, 'linear': metadata,
                   'observation': projection, 'unit_binding': unit}
        if observed['status'] != 'ready' or not observed['child_tree_gone']:
            return {**result, 'status': 'observed', 'effect': observed,
                    'next_action': 'owner-readback' if (observed['status'] != 'verified'
                                                      or not observed['child_tree_gone'])
                                   else 'existing-unit-consumer'}
        if binding.phase == 'linear':
            actions = [v for v in metadata['actions'] if v['issue_id'] == issue.id
                       and v['action_id'] == binding.operation_id]
            if not actions:
                return {**result, 'status': 'idle'}
            context['action'] = actions[0]  # one exact owner-bound metadata transaction
            require(binding.operation_id == actions[0]['action_id'], 'linear_transaction_identity')
        else:
            journal = binding.phase == 'integration' and adapters.integration_acceptance is not None
            if not journal:
                engine = await resolved(adapters.engine(binding))
                context['engine'] = engine_acceptance(engine, handoff, candidate)
            review = await resolved(adapters.review(current, issue, binding))
            require(current._check_unit_review(review) == unit, 'independent_review_binding')
            context['review'] = review_coverage(review, handoff, candidate)
            if journal:
                context['validation'] = await resolved(
                    adapters.integration_acceptance(binding, review, handoff, candidate))
            if binding.phase == 'release':
                require(candidate is not None and packet['release'] is not None, 'release_evidence_missing')
                release = packet['release']
                require(set(release) == {'summary', 'plan', 'results', 'catalog', 'evidence_root'},
                        'release_fields')
                require(release['plan']['candidate'] == candidate, 'release_candidate_identity')
                context['qualification'] = validate_qualification(
                    release['summary'], release['plan'], release['results'], policy,
                    release['catalog'], release['evidence_root'])
            else:
                require(candidate is None and handoff['source']['target'] == 'develop',
                        'integration_target')
        current.guard()
        require(not current.read_only and not current.stopping, 'current_not_writable')
        require(await resolved(adapters.authorize(current, issue, binding)) is True,
                'owner_authority_missing')
        require(fingerprint(current.gate_binding(issue, observation=True)) == binding.unit_sha256,
                'native_gate_drift')
        # Adapter is the existing sole owner, with its original durable intent,
        # exact-source/review/command/permission gates and canonical readback.
        effect = transaction(await resolved(adapters.step(binding, context)), binding)
        return {**result, 'status': 'advanced', 'action': binding.phase, 'effect': effect,
                'next_action': 'existing-unit-consumer' if (effect['status'] == 'verified'
                                                          and effect['child_tree_gone'])
                               else 'owner-readback'}
    except Exception as error:
        # A raised step may already have effected its transaction. Never retry it
        # in this invocation; the existing journal must be observed on reentry.
        return {**result, 'status': 'held',
                'reason': str(error) if isinstance(error, RuntimeHold) else type(error).__name__,
                'next_action': 'owner-reconcile-existing-operation'}


# Fixed normal-runtime routes. These constants are never selected by packet JSON.
PUBLISHER_ARGV = ('/usr/bin/node', '/opt/offmenu-publisher/tools/delivery/github-app-publisher.mjs',
                  '--native-rpc')
PUBLISHER_CONFIG = '/etc/offmenu-publisher/config.json'


def pinned_private(current, ref):
    """Read one original private artifact selected by the sealed owner grant."""
    import hashlib
    import os
    import stat
    from protected_owner_install import record
    require(type(ref) is dict and set(ref) == {'path', 'sha256'}, 'private_reference')
    path = current.private(ref['path'])
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    try:
        info = os.fstat(fd)
        require(stat.S_ISREG(info.st_mode) and info.st_nlink == 1
                and 0 < info.st_size <= 1024 * 1024, 'private_artifact')
        with os.fdopen(fd, 'rb', closefd=False) as stream:
            raw = stream.read(1024 * 1024 + 1)
        require(len(raw) == info.st_size and hashlib.sha256(raw).hexdigest() == ref['sha256'],
                'private_artifact_drift')
    finally:
        os.close(fd)
    value = record(raw)
    fingerprint(value)
    return value


def publisher_request(binding, packet, mode):
    return dict(version=1, mode=mode, operation_id=binding.operation_id,
                issue_id=binding.issue_id, project_id=binding.project_id, owner=binding.owner,
                unit_sha256=binding.unit_sha256, packet_sha256=binding.packet_sha256,
                source_sha256=fingerprint(packet['handoff']['source']))


def publisher_identity(request, phase):
    """No privilege transfer: an ordinary coordinator user stays held here."""
    import os
    from pathlib import Path
    from protected_owner_install import record
    from stokowski_adapter import protected_owner_bytes
    # Refuse ordinary/root users BEFORE attempting protected config access.
    require(os.getuid() not in (0, 1000) and os.geteuid() == os.getuid(),
            'publisher_owner_identity_required')
    config = record(protected_owner_bytes(Path(PUBLISHER_CONFIG)))
    require((os.getuid(), os.geteuid(), os.getgid(), os.getegid()) ==
            (config['publisherUid'], config['publisherUid'], config['publisherGid'], config['publisherGid']),
            'publisher_owner_identity_required')
    association = config['snapshot']['native_runtime']
    require(all(association[key] == request[key] for key in
                ('issue_id', 'project_id', 'owner', 'unit_sha256', 'packet_sha256'))
            and fingerprint(association['source']) == request['source_sha256']
            and fingerprint(config['binding']) == request['operation_id']
            and ('release' if config['version'] == 2 else 'integration') == phase,
            'publisher_sealed_association')


def publisher_response(value, request, phase):
    fields = {'version', 'kind', 'request_sha256', 'operation_id', 'issue_id', 'project_id',
              'owner', 'unit_sha256', 'packet_sha256', 'source_sha256', 'phase', 'status'}
    require(type(value) is dict and set(value) == fields and type(value['version']) is int
            and value['version'] == 1 and value['kind'] == 'native-publisher-response-v1'
            and value['request_sha256'] == fingerprint(request) and value['phase'] == phase,
            'publisher_response')
    require(all(value[key] == request[key] for key in
                ('operation_id', 'issue_id', 'project_id', 'owner', 'unit_sha256',
                 'packet_sha256', 'source_sha256')), 'publisher_response_identity')
    require(value['status'] in ('ready', 'pending', 'unknown', 'verified', 'denied', 'failed'),
            'publisher_response_status')
    return value


def invocation_members(group):
    import errno
    from pathlib import Path
    members = set()
    for item in Path('/proc').iterdir():
        if not item.name.isdigit():
            continue
        try:
            stat = (item / 'stat').read_text()
            if int(stat[stat.rfind(')') + 2:].split()[2]) == group:
                members.add(int(item.name))
        except OSError as error:
            if error.errno not in (errno.ENOENT, errno.ESRCH):
                raise
    return members


async def fixed_publisher_rpc(binding, packet, mode):
    """Bounded fixed child; reap actual invocation, never trust child cleanup JSON."""
    import asyncio
    import os
    import signal
    from protected_owner_install import record
    request = publisher_request(binding, packet, mode)
    publisher_identity(request, binding.phase)
    payload = json.dumps(request, sort_keys=True, ensure_ascii=True, allow_nan=False).encode()
    require(len(payload) <= 16384, 'publisher_request_bound')
    # Do not inherit Node injection, Python import paths or coordinator credentials.
    process = await asyncio.create_subprocess_exec(
        *PUBLISHER_ARGV, stdin=asyncio.subprocess.PIPE, stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE, start_new_session=True,
        env={'PATH': '/usr/bin:/bin', 'LANG': 'C.UTF-8'})
    tasks = []
    async def read(stream):
        raw = bytearray()
        while True:
            chunk = await stream.read(4096)
            if not chunk:
                return bytes(raw)
            raw.extend(chunk)
            require(len(raw) <= 65536, 'publisher_response_bound')
    try:
        process.stdin.write(payload)
        tasks = [asyncio.create_task(read(process.stdout)), asyncio.create_task(read(process.stderr)),
                 asyncio.create_task(process.wait())]
        await process.stdin.drain()
        process.stdin.close()
        stdout, _, code = await asyncio.wait_for(asyncio.gather(*tasks), timeout=25)
        require(code == 0, 'publisher_invocation_unknown')
        response = publisher_response(record(stdout), request, binding.phase)
    finally:
        # Fixed publisher/Python children retain this fresh process group. No
        # unrelated CurrentWork children, environment or command lines are read.
        if process.returncode is None or invocation_members(process.pid):
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
        await asyncio.wait_for(process.wait(), timeout=3)
        for task in tasks:
            if not task.done():
                task.cancel()
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
    # Even successful child JSON cannot assert descendant termination.
    deadline = asyncio.get_running_loop().time() + 1
    while invocation_members(process.pid) and asyncio.get_running_loop().time() < deadline:
        await asyncio.sleep(.02)
    require(not invocation_members(process.pid), 'publisher_invocation_cleanup_unverified')
    return dict(operation_id=binding.operation_id, status=response['status'], child_tree_gone=True)


async def prepare_native_unit(current, identifier, *, linear_client=None):
    """Derive normal publication data from original receipts under Root policy.

    This is called by the existing locked owner poll. The protected publisher
    owns preparation admission and effects; no per-item owner config is created
    by this process, and neither this packet nor source exit marks outcome Done.
    """
    from pathlib import Path
    from types import SimpleNamespace
    import hashlib
    import sqlite3
    from stokowski_adapter import read_record, file_sha, SOURCE
    from stokowski_unit_review import qualify_native_review
    from symphony_workspace import checkpoint
    from native_harness_contract import load_release_policy
    import native_publisher_invocation as publisher
    current.guard()
    require(not current.read_only and not current.stopping, 'native_prepare_owner_hold')
    current.postcoding_template(identifier)
    _,contract,_ = current.postcoding_contract(identifier)
    issue = SimpleNamespace(identifier=identifier,id=current.entries[identifier]['issue_id'])
    original,manifest,_ = current.context(identifier,review=True,observation=True)
    require(not (original/'cancel.json').exists() and not (current.runtime/'cancel.json').exists(), 'native_prepare_cancelled')
    unit = current.gate_binding(issue,observation=True)
    current.validation_binding(identifier,current.entries[identifier])
    selected = read_record(original/'validation-bindings.json')['issues'][identifier]
    with sqlite3.connect((original/'operations/operations.sqlite').as_uri()+'?mode=ro',uri=True) as db:
        row=db.execute('SELECT spec,state FROM operations WHERE key=?',(selected['operation_key'],)).fetchone()
    spec,state=map(json.loads,row)
    native=current._completed_native_evidence(identifier,original,manifest)
    review=qualify_native_review(current,identifier)
    require(review == read_record(current.runtime/('unit-review-'+identifier+'.json'))
            and review['unit_binding']==unit and review['verdict']=='accept' and not review['findings'], 'native_prepare_independent_review')
    policy=load_release_policy(SOURCE/'config/delivery-release-policy.json')
    def ref(path):
        current.private(str(path))
        return dict(path=str(path),sha256=file_sha(path))
    author=ref(original/'attempts'/identifier/'receipt.json')
    source=dict(repository=policy['repository'],target='develop',policy_sha256=fingerprint(policy),
        **{k:review['source'][k] for k in ('head','base','tree','branch')})
    handoff=dict(version=1,kind='delivery-handoff-v1',issue_id=issue.id,project_id=manifest['project_id'],
        owner=current.config['owner'],origin=dict(kind='native-coding-v1',evidence=author),source=source,
        outputs=[dict(path=n,sha256=h) for n,h in sorted(spec['outputs'].items())],
        evidence=[author,ref(current.runtime/('unit-review-'+identifier+'.json'))],
        attempt=dict(id=native['session_id'],lease_id=native['lease'],admission=ref(original/'current-admission.json')),
        operation=dict(id=selected['operation_key'],backend='windmill',job_id=state['logical_job_id'],status='succeeded',
            command_sha256=read_record(original/'validation-receipt.json')['command_sha256'],
            runner_sha256=spec['runner_sha256'],policy_sha256=spec['policy_sha256'],receipt=ref(original/'validation-receipt.json')))
    validate_handoff(handoff,policy)
    native_journal_acceptance(current,issue,str(original),handoff)
    review_coverage(review,handoff,None)
    path=original/'native-publication-packet.json'
    if path.exists():
        packet=read_record(current.private(str(path)))
        require(packet['handoff']==handoff and packet['policy']==policy, 'native_prepare_packet_drift')
    else:
        require(linear_client is not None, 'native_prepare_linear_reader_required')
        data=await linear_client._graphql(
            'query($id:String!){issue(id:$id){id identifier team{id} project{id name} state{type} '
            'inverseRelations(first:100){nodes{type issue{id state{type}}} pageInfo{hasNextPage}} '
            'attachments(first:100){nodes{url} pageInfo{hasNextPage}}}}', {'id':issue.id})
        remote=data.get('issue') or {}
        require(remote.get('id')==issue.id and remote.get('identifier')==identifier
            and remote.get('project',{}).get('id')==manifest['project_id'], 'native_prepare_linear_identity')
        relations=remote['inverseRelations'];attachments=remote['attachments']
        require(not relations['pageInfo']['hasNextPage'] and not attachments['pageInfo']['hasNextPage'], 'native_prepare_linear_pagination_required')
        blockers=[dict(id=v['issue']['id'],state_type=v['issue']['state']['type']) for v in relations['nodes'] if v['type']=='blocks']
        require(set(v['id'] for v in blockers)==set(contract['dependencies']), 'native_prepare_dependency_contract')
        outcome=dict(id=issue.id,identifier=identifier,project_id=manifest['project_id'],team_id=remote['team']['id'],
            state_type=remote['state']['type'],blocked_by=blockers,
            pr_urls=sorted({v['url'] for v in attachments['nodes'] if v['url'].startswith('https://github.com/maldous/offmenu/pull/')}),milestone_ids=[])
        linear=dict(version=1,projects=[dict(id=manifest['project_id'],name=remote['project']['name'],team_id=remote['team']['id'])],
            outcomes=[outcome],changes=[],dependencies=[],effects=[])
        require(plan_delivery(linear,policy)['dependencies'][0]['dependencies_satisfied'], 'native_prepare_dependencies_held')
        packet=dict(policy=policy,handoff=handoff,candidate=None,linear=linear,release=None)
        checkpoint(path,packet)
    pending=current.state['tasks'][identifier].setdefault('native_publication',{})
    identity=dict(unit_sha256=fingerprint(unit),packet_sha256=fingerprint(packet),packet=ref(path))
    require(pending.get('intent',identity)==identity,'native_prepare_intent_drift')
    pending.update(intent=identity,status='preparing')
    current.save()  # Before invoking the protected admission boundary.
    require(current.config['source_sha256'].get('tools/delivery/native_publisher_invocation.py')==file_sha(publisher.__file__), 'native_prepare_publisher_source')
    selection=await produce_native_publication(current,issue,packet)
    require(set(selection)=={'binding','packet','context'} and selection['packet']==ref(path)
        and selection['binding']['unit_sha256']==fingerprint(unit)
        and selection['binding']['packet_sha256']==fingerprint(packet), 'native_prepare_selection_binding')
    target=current.runtime/('native-publication-'+identifier+'-selection.json')
    if target.exists():
        require(read_record(current.private(str(target)))==selection,'native_prepare_selection_drift')
    else: checkpoint(target,selection)
    pending.update(selection=ref(target),status='prepared')
    current.save()
    return current._native_harness_selection(identifier)


def owner_adapters(current, issue, binding, selection, *, linear_client=None):
    """Concrete normal factory; selection is DATA from the protected owner map.

    Caller supplies its EXISTING admitted LinearClient. No token lookup/client
    construction, callback name, executable selector or privilege helper exists.
    Missing custody/identity/actual evidence raises a hold before any effect.
    """
    from dataclasses import asdict
    from pathlib import Path
    import hashlib
    selected = json.loads(json.dumps(selection, allow_nan=False))
    helper_calls = [0]
    def authorize(owner, native_issue, bound):
        require(owner is current and native_issue.id == issue.id and bound == binding,
                'owner_factory_binding')
        current.guard()
        # current.guard above freshly requalifies the EXISTING protected binding
        # dictionary via current_config, including config/catalog/Python bytes.
        # A Boolean or a truthy arbitrary dictionary is never that authority.
        from stokowski_adapter import PROTECTED_OWNER, SOURCE
        import re
        custody = current.owner_custody
        require(type(custody) is dict and set(custody) == {
                    'schema', 'runtime', 'config_sha256', 'catalog_sha256',
                    'source_root', 'python_sha256'}
                and custody['schema'] == 'protected-current-owner-v1'
                and custody['runtime'] == str(current.runtime)
                and custody['source_root'] == str(SOURCE)
                and custody['config_sha256'] == current.config_sha
                and current.config_path == PROTECTED_OWNER / 'current.json'
                and all(type(custody[key]) is str and re.fullmatch('[0-9a-f]{64}', custody[key])
                        for key in ('config_sha256', 'catalog_sha256', 'python_sha256'))
                and not current.read_only and not current.stopping, 'owner_sealed_context_required')
        import native_harness_contract
        import linear_delivery
        import release_qualification
        from offmenu.delivery import engine as engine_module, status as status_module
        paths = {'tools/delivery/native_harness_runtime.py': __file__,
                 'tools/delivery/native_harness_contract.py': native_harness_contract.__file__,
                 'contracts/schemas/delivery-handoff-v1.schema.json':
                     Path(native_harness_contract.__file__).resolve().parents[2] /
                     'contracts/schemas/delivery-handoff-v1.schema.json',
                 'tools/delivery/linear_delivery.py': linear_delivery.__file__,
                 'tools/delivery/release_qualification.py': release_qualification.__file__,
                 'src/offmenu/delivery/engine.py': engine_module.__file__,
                 'src/offmenu/delivery/status.py': status_module.__file__}
        require(all(current.config['source_sha256'].get(name) ==
                    hashlib.sha256(Path(path).read_bytes()).hexdigest()
                    for name, path in paths.items()), 'owner_factory_source_pin')
        actual = current._native_harness_selection(issue.identifier)
        require(fingerprint(actual) == fingerprint(selected)
                and set(actual) == {'binding', 'packet', 'context'}
                and actual['binding'] == asdict(binding), 'owner_selection_drift')
        context = actual['context']
        journal_context = (binding.phase == 'integration' and type(context) is dict
                           and set(context) - {'publisher_invocation','publisher_continuation'} ==
                           {'reviewed_runtime', 'unit_review'})
        native_context = (binding.phase == 'integration' and type(context) is dict
                          and set(context) - {'publisher_continuation'} ==
                          {'native_runtime','pending_unit_review','publisher_invocation'})
        require(type(context) is dict and (set(context) in (
                    {'engine_root', 'engine_task', 'unit_review'},
                    {'engine_root', 'engine_task', 'unit_review', 'publisher_invocation'})
                or journal_context or native_context or (binding.phase == 'linear' and context == {})),
                'owner_context_fields')
        if journal_context:
            require(type(context['reviewed_runtime']) is str
                    and current.private(context['reviewed_runtime']).is_dir(),
                    'journal_owner_runtime')
        if native_context:
            import stokowski_unit_review as writer
            require(current.config['source_sha256'].get('tools/delivery/stokowski_unit_review.py') ==
                    hashlib.sha256(Path(writer.__file__).read_bytes()).hexdigest(), 'native_review_writer_pin')
            c=context['pending_unit_review']
            original_runtime,_,_=current.context(issue.identifier,review=True,observation=True)
            require(context['native_runtime'] == str(original_runtime) and c['runtime'] == str(current.runtime)
                    and c['issue'] == issue.identifier and c['actor_uid'] == 1000
                    and c['source_head'] == current.config['source_head']
                    and c['source_sha256'] == current.config['source_sha256']
                    and c['unit_binding'] == current.gate_binding(issue,observation=True)
                    and c['publisher_review']['request'] == publisher_request(binding,pinned_private(current,actual['packet']), 'observe')
                    and fingerprint(c['publisher_review_binding']) == bound.operation_id,
                    'native_review_owner_context')
        if 'publisher_continuation' in context:
            require((journal_context or native_context) and 'publisher_invocation' in context,
                    'publisher_continuation_context')
            import native_publisher_invocation as helper
            grant=helper.continuation(context['publisher_continuation'],asdict(binding))
            require('pre_admission_refusal' not in grant or native_context,'publisher_continuation_origin')
            if native_context and 'pre_admission_refusal' not in grant:
                completed_native_continuation(current,issue,binding,
                    pinned_private(current,actual['packet']),actual)
        if 'publisher_invocation' in actual['context']:
            require(binding.phase in ('integration', 'release'), 'publisher_invocation_phase')
            invocation_capability(actual['context']['publisher_invocation'])
        return True
    def load(bound):
        authorize(current, issue, bound)
        packet = pinned_private(current, selected['packet'])
        require(fingerprint(packet) == bound.packet_sha256, 'owner_packet_drift')
        return packet
    def engine(bound):
        packet = load(bound)
        require(bound.phase in ('integration', 'release'), 'engine_owner_phase')
        context = selected['context']
        root = current.private(context['engine_root'])
        task = pinned_private(current, context['engine_task'])
        # Construction may only reuse EXISTING immutable binding/acceptance.
        # It never creates an admission, runs a graph, or takes another lease.
        directory = root / '.delivery' / task['id']
        for name in ('binding.json', 'accepted.json'):
            path = current.private(str(directory / name))
            require(path.is_file(), 'engine_original_evidence_missing')
        require(task.get('handoff') == packet['handoff']
                and task.get('release_candidate') == packet['candidate'], 'engine_owner_binding')
        # Existing non-writing original-binding loader: never let a disappeared
        # binding race turn an observation into fresh Engine admission. This
        # does not reconcile failure; immediately restore ALL native/source gates.
        loaded = Engine(root, root / '.delivery', task, failed_reconciliation=True)
        loaded.native_harness = loaded.native_facts()
        loaded.verify_source()
        return loaded
    def review(owner, native_issue, bound):
        authorize(owner, native_issue, bound)
        require(bound.phase in ('integration', 'release'), 'review_owner_phase')
        if 'native_runtime' in selected['context']:
            from stokowski_adapter import read_record
            return read_record(current.private(str(current.runtime/('unit-review-'+issue.identifier+'.json'))))
        return pinned_private(current, selected['context']['unit_review'])
    def integration_acceptance(bound, review_packet, handoff, candidate):
        authorize(current, issue, bound)
        require(bound.phase == 'integration', 'journal_integration_only')
        runtime=selected['context'].get('native_runtime',selected['context'].get('reviewed_runtime'))
        return journal_acceptance(current, issue, runtime,
                                  review_packet, handoff, candidate)
    def linear(bound, context=None):
        packet = load(bound)
        actions = plan_delivery(packet['linear'], packet['policy'])['actions']
        found = [action for action in actions if action['action_id'] == bound.operation_id]
        if not found:
            previous = current.state.get('native_harness_linear', {}).get(bound.operation_id)
            if previous is not None:
                require(previous.get('binding') == asdict(bound), 'linear_retained_binding')
                action = previous.get('action')
                require(type(action) is dict and action.get('action_id') == bound.operation_id
                        and fingerprint({k: v for k, v in action.items() if k != 'action_id'}) ==
                        bound.operation_id, 'linear_retained_action')
                found = [action]
        require(len(found) == 1, 'linear_selected_action_missing')
        if context is not None:
            require(context['action'] == found[0], 'linear_context_action')
        import native_harness_linear
        require(current.config['source_sha256'].get('tools/delivery/native_harness_linear.py') ==
                hashlib.sha256(Path(native_harness_linear.__file__).read_bytes()).hexdigest(),
                'linear_adapter_source_pin')
        return native_harness_linear.NativeLinearAdapter(linear_client), found[0]
    async def observe(bound):
        if bound.phase == 'linear':
            adapter, action = linear(bound)
            return await adapter.observe(current, bound, action)
        if 'publisher_invocation' in selected['context']:
            return await invocation_transaction(current, bound, load(bound), selected, 'observe',
                                                helper_calls, helper_authorize)
        return await fixed_publisher_rpc(bound, load(bound), 'observe')
    async def step(bound, context):
        if bound.phase == 'linear':
            adapter, action = linear(bound, context)
            return await adapter.step(current, bound, action)
        if 'publisher_invocation' in selected['context']:
            return await invocation_transaction(current, bound, load(bound), selected, 'step',
                                                helper_calls, helper_authorize)
        return await fixed_publisher_rpc(bound, load(bound), 'step')
    def helper_authorize(owner, bound):
        require(authorize(owner, issue, bound) is True, 'publisher_invocation_authority')
        require(fingerprint(current.gate_binding(issue, observation=True)) == bound.unit_sha256,
                'publisher_invocation_unit_drift')
        return True
    async def prepare_unit(bound,handoff):
        authorize(current,issue,bound)
        context=selected['context']
        native_journal_acceptance(current,issue,context['native_runtime'],handoff)
        incoming=current.runtime/('unit-review-'+issue.identifier+'.json')
        if incoming.exists():
            packet=review(current,issue,bound)
            require(current._check_unit_review(packet) == current.gate_binding(issue,observation=True),
                    'native_prepared_review_binding')
            current._consume_unit_reviews()  # Original normal gate consumer only.
            gate=current.state['tasks'][issue.identifier].get('unit_gate',{})
            require(gate.get('disposition') == 'approved' and not gate.get('accepted_delivery'),
                    'native_unit_gate_unapproved')
            return None
        # One supervised publisher invocation per normal boundary. Alternate
        # fresh observe and publication-only requests using original receipts.
        record=current.state.get(INVOCATIONS,{}).get(bound.operation_id,{})
        invocations=record.get('invocations',[])
        latest=invocations[-1] if invocations else None
        mode='observe'
        if (latest and latest.get('status') == 'complete' and latest.get('result')
            and latest['envelope']['request']['mode'] == 'observe'
            and (latest['result'].get('response') or {}).get('status') == 'ready'):
            mode='publish'
        effect=await invocation_transaction(current,bound,load(bound),selected,mode,
                                            helper_calls,helper_authorize)
        if mode == 'publish' and effect['status'] == 'ready' and effect['child_tree_gone']:
            from symphony_capacity import AdmissionError
            import stokowski_unit_review as writer
            try:
                writer.publish_protected_pending(context['pending_unit_review'])
            except AdmissionError as error:
                if str(error) != 'local_review_pending':
                    raise
            else:
                current._consume_unit_reviews()
        return effect  # Never merge in the preparation boundary.
    journal_context = (binding.phase == 'integration' and
                       set(selected['context']) - {'publisher_invocation','publisher_continuation'} ==
                       {'reviewed_runtime', 'unit_review'})
    native_context=(binding.phase == 'integration' and set(selected['context']) - {'publisher_continuation'} ==
                    {'native_runtime','pending_unit_review','publisher_invocation'})
    return OwnerAdapters(authorize, load, engine, review, observe, step,
                         integration_acceptance if journal_context or native_context else None,
                         prepare_unit if native_context else None)


# Optional existing-host capability. No selector or identity comes from JSON.
PUBLISHER_HELPER_ARGV = ('/usr/bin/sudo', '-n', '-u', '#984', '-g', '#976', '--',
    '/opt/offmenu-publisher/venv/bin/python', '-I', '-B',
    '/opt/offmenu-publisher/tools/delivery/native_publisher_invocation.py')
INVOCATIONS = 'native_harness_publisher_invocations'


def invocation_capability(value):
    import re
    require(type(value) is dict and set(value) == {
        'version', 'closure_sha256', 'host_confirmation_sha256'}
        and type(value['version']) is int and value['version'] == 1
        and all(type(value[key]) is str and re.fullmatch('[0-9a-f]{64}', value[key])
                for key in ('closure_sha256', 'host_confirmation_sha256')),
        'publisher_invocation_capability')
    return json.loads(json.dumps(value))


async def fixed_invocation_wire(envelope):
    """Only own sudo is reaped here; privileged descendants need helper proof."""
    import asyncio
    payload = json.dumps(envelope, sort_keys=True, ensure_ascii=True, allow_nan=False).encode()
    require(len(payload) <= 16384, 'publisher_invocation_request_bound')
    process = await asyncio.create_subprocess_exec(*PUBLISHER_HELPER_ARGV,
        cwd='/', env={'PATH': '/usr/bin:/bin', 'LANG': 'C.UTF-8'}, close_fds=True,
        start_new_session=True, stdin=asyncio.subprocess.PIPE, stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE)
    async def read(stream):
        raw = bytearray()
        while True:
            chunk = await stream.read(4096)
            if not chunk:
                return bytes(raw)
            raw.extend(chunk)
            require(len(raw) <= 65536, 'publisher_invocation_response_bound')
    tasks = []
    try:
        process.stdin.write(payload)
        tasks = [asyncio.create_task(read(process.stdout)), asyncio.create_task(read(process.stderr)),
                 asyncio.create_task(process.wait())]
        await process.stdin.drain()
        process.stdin.close()
        stdout, _, code = await asyncio.wait_for(asyncio.gather(*tasks), timeout=25)
        require(code == 0, 'publisher_invocation_transport_unknown')
        return stdout
    finally:
        if process.returncode is None:
            try:
                process.kill()  # This caller owns sudo, NOT the privileged child tree.
            except (ProcessLookupError, PermissionError):
                pass
        await asyncio.wait_for(process.wait(), timeout=3)
        for task in tasks:
            if not task.done():
                task.cancel()
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)


def invocation_projection(module, value, envelope, capability, phase):
    # The real pinned helper validates its ORIGINAL durable same-supervisor
    # terminal proof. No caller ECHILD, census or sudo wait substitutes for it.
    value = module.validate_result(value, envelope, capability['closure_sha256'])
    require(value['status'] == 'complete' and value['receipt'] is not None,
            'publisher_invocation_unresolved')
    terminal = value['receipt']['body']['terminal']
    require(terminal['outcome'] == 'succeeded' and terminal['child_tree_gone'] is True
            and value['response'] is not None, 'publisher_invocation_native_outcome_held')
    response = publisher_response(value['response'], envelope['request'], phase)
    require(response['status'] not in ('pending', 'unknown'), 'publisher_native_outcome_held')
    return dict(operation_id=envelope['request']['operation_id'], status=response['status'],
                child_tree_gone=True)


def pre_admission_history(module, grant, record, binding, packet):
    """Exact first observation refused before privileged admission, never success."""
    from dataclasses import asdict
    require(binding.phase == 'integration' and record.get('version') == 1
        and set(record) == {'version','binding','selection_sha256','capability','invocations'}
        and record['binding'] == asdict(binding) and len(record['invocations']) == 1,
        'pre_admission_original_record')
    old=record['invocations'][0];ref=grant['pre_admission_refusal']
    require(set(old) == {'envelope','last_request','status','result'}
        and old['status'] == 'unknown' and old['result'] is None,'pre_admission_unknown_only')
    original=module.request(module.wire(old['envelope']))
    last=module.request(module.wire(old['last_request']))
    require(original['mode'] == 'invoke' and original['request'] == publisher_request(binding,packet,'observe')
        and original['invocation_id'] == ref['invocation_id'] == last['invocation_id']
        and last['request'] == original['request'] and last['mode'] in ('invoke','observe')
        and module.fingerprint(original['request']) == ref['request_sha256'],
        'pre_admission_original_observe')
    return original


def recovery_observation(module, epoch, binding, packet):
    original=pre_admission_history(module,epoch['continuation'],epoch['history'][0],binding,packet)
    observed=epoch['recovery_observation']
    if observed is None:
        return original,False
    require(type(observed) is dict and set(observed) == {'envelope','result'}
        and observed['envelope'] == {**original,'mode':'observe'},'pre_admission_observation')
    if observed['result'] is None:
        return original,False
    value=module.validate_result(observed['result'],observed['envelope'],epoch['capability']['closure_sha256'])
    require(value['status'] == 'not-found' and value['receipt'] is None and value['response'] is None,
            'pre_admission_privileged_record_exists')
    return original,True


def invocation_epochs(module, record, binding, packet, *, complete=False):
    """Validate retained epochs with EACH original capability, never today's pin."""
    from dataclasses import asdict
    epochs, cursor, refused_history, recovered_ids = [], record, set(), set()
    fields = {'version','binding','selection_sha256','capability','invocations'}
    while True:
        pre=(type(cursor) is dict and cursor.get('version') == 2
             and 'pre_admission_refusal' in cursor.get('continuation',{}))
        require(type(cursor) is dict and type(cursor.get('version')) is int
            and cursor['version'] in (1,2) and set(cursor) == (fields if cursor['version'] == 1
                else fields | {'history','continuation'} | ({'recovery_observation'} if pre else set())), 'publisher_invocation_record')
        require(cursor['binding'] == asdict(binding) and type(cursor['invocations']) is list
            and len(cursor['invocations']) <= 128, 'publisher_invocation_binding')
        invocation_capability(cursor['capability'])
        epochs.append(cursor)
        require(len(epochs) <= 8, 'publisher_continuation_bound')
        if cursor['version'] == 1:
            break
        require(type(cursor['history']) is list and len(cursor['history']) == 1,
                'publisher_continuation_history')
        previous = cursor['history'][0]
        grant = module.continuation(cursor['continuation'], asdict(binding))
        require(module.fingerprint(previous) == grant['previous_record_sha256']
            and previous['selection_sha256'] == grant['previous_selection_sha256']
            and previous['capability'] == grant['previous_capability'], 'publisher_continuation_history_pin')
        if pre:
            original,absent=recovery_observation(module,cursor,binding,packet)
            require(not cursor['invocations'] or absent,'pre_admission_absence_required')
            if cursor['invocations']:
                require(cursor['invocations'][0]['envelope'] == original,'pre_admission_same_uuid')
            refused_history.add(id(previous));recovered_ids.add(original['invocation_id'])
        cursor = previous
    refs, ids = [], []
    for epoch in reversed(epochs):
        historical = epoch is not record
        refused=id(epoch) in refused_history
        require(epoch['invocations'] or (epoch['version'] == 2 and not historical),
                'publisher_invocation_empty_history')
        for old in epoch['invocations']:
            require(type(old) is dict and set(old) == {'envelope','last_request','status','result'}
                and old['status'] in ('pending','unknown','complete'), 'publisher_invocation_record')
            original = module.request(module.wire(old['envelope']))
            require(original['mode'] == 'invoke' and original['request'] ==
                publisher_request(binding,packet,original['request']['mode']), 'publisher_invocation_original_request')
            last = module.request(module.wire(old['last_request']))
            require(last['invocation_id'] == original['invocation_id'] and last['request'] == original['request'],
                    'publisher_invocation_transport_request')
            ids.append(original['invocation_id'])
            value = (module.validate_result(old['result'],original,epoch['capability']['closure_sha256'])
                     if old['result'] is not None else None)
            if value and value['receipt'] is not None:
                require(value['receipt']['body']['intent']['phase'] == binding.phase, 'publisher_invocation_phase')
                refs.append(dict(invocation_id=original['invocation_id'],
                    closure_sha256=epoch['capability']['closure_sha256'],receipt_sha256=value['receipt']['sha256']))
            if value and value['response'] is not None:
                publisher_response(value['response'],original['request'],binding.phase)
            if old['status'] == 'complete' or ((historical or complete) and not refused):
                require(old['status'] == 'complete' and value is not None and value['status'] == 'complete',
                        'publisher_invocation_completion')
            if (historical or complete) and not refused:
                terminal = value['receipt']['body']['terminal']
                require(terminal['child_tree_gone'] is True and
                    ((terminal['response'] is None and original['request']['mode'] == 'observe') or
                     (terminal['response'] is not None and terminal['response']['status'] not in ('pending','unknown'))),
                    'publisher_continuation_unknown_effect')
        require(all(old['status'] == 'complete' for old in epoch['invocations'][:-1]),
                'publisher_invocation_prior_unresolved')
    require(len(ids) <= 128 and all(ids.count(v) == 1 or (v in recovered_ids and ids.count(v) == 2)
                                   for v in set(ids)), 'publisher_invocation_duplicate_identity')
    # Every historical grant remains checkable after restart, with no history rewrite.
    for epoch in epochs[:-1]:
        if 'pre_admission_refusal' in epoch['continuation']:
            continue  # The pinned old unknown has no privileged receipt at all.
        allowed = {r['invocation_id']:r for r in epoch['continuation']['receipts']}
        prior_ids = set()
        previous = epoch['history'][0]
        while True:
            prior_ids.update(v['envelope']['invocation_id'] for v in previous['invocations'])
            if previous['version'] == 1: break
            previous = previous['history'][0]
        actual = {r['invocation_id']:r for r in refs if r['invocation_id'] in prior_ids}
        require(actual == allowed, 'publisher_continuation_history_receipts')
    return refs


def completed_native_continuation(current, issue, binding, packet, selection):
    """Requalify an already merged ORIGINAL native unit without changing it."""
    import native_publisher_invocation as module
    from dataclasses import asdict
    from stokowski_adapter import read_record, digest as original_digest
    context=selection['context']
    runtime,manifest,_=current.context(issue.identifier,review=True,observation=True)
    require('stage' not in manifest['tasks'][issue.identifier]
            and str(runtime) == context['native_runtime'], 'completed_native_origin')
    unit=current.gate_binding(issue,observation=True)
    require(fingerprint(unit) == binding.unit_sha256
            and context['pending_unit_review']['unit_binding'] == unit,
            'completed_native_unit')
    review=read_record(current.private(str(current.runtime/('unit-review-'+issue.identifier+'.json'))))
    gate=current.state['tasks'][issue.identifier].get('unit_gate',{})
    require(gate.get('binding') == unit and gate.get('disposition') == 'approved'
            and gate.get('handled') is True and gate.get('unit_review') == 'approved'
            and gate.get('review_sha256') == original_digest(review), 'completed_native_gate')
    require(current._check_unit_review(review) == unit, 'completed_native_review')
    require(fingerprint(packet) == binding.packet_sha256, 'completed_native_packet')
    native_journal_acceptance(current,issue,str(runtime),packet['handoff'],review=review)
    grant=module.continuation(context['publisher_continuation'],asdict(binding))
    require('pre_admission_refusal' not in grant, 'completed_native_continuation')
    record=current.state.get(INVOCATIONS,{}).get(binding.operation_id)
    if record is not None and record.get('selection_sha256') == fingerprint(selection):
        # Normal consumption may already have installed the new empty epoch.
        # Retain and validate its original predecessor, including recovery history.
        require(record.get('version') == 2 and record.get('continuation') == grant
                and record.get('capability') == invocation_capability(context['publisher_invocation'])
                and len(record.get('history',[])) == 1, 'completed_native_history')
        invocation_epochs(module,record,binding,packet)
        record=record['history'][0]
    require(record is not None and module.fingerprint(record) == grant['previous_record_sha256']
            and record['selection_sha256'] == grant['previous_selection_sha256']
            and record['capability'] == grant['previous_capability'], 'publisher_continuation_record_pin')
    require(invocation_capability(context['publisher_invocation'])['closure_sha256'] !=
            record['capability']['closure_sha256'], 'publisher_continuation_new_closure')
    complete_continuation_history(module,record,binding,packet,grant)
    require(record['invocations'], 'completed_native_terminal')
    latest=record['invocations'][-1]
    value=module.validate_result(latest['result'],latest['envelope'],record['capability']['closure_sha256'])
    # The fixed integration publisher maps only merge-verified + verified
    # merge_effect to this authenticated terminal protocol status.
    require(value['response'] is not None and value['response']['status'] == 'verified'
            and value['receipt']['body']['terminal']['response'] == value['response'],
            'completed_native_merge_unverified')


def complete_continuation_history(module, record, binding, packet, grant):
    refs = invocation_epochs(module,record,binding,packet,complete=True)
    require({r['invocation_id']:r for r in refs} == {r['invocation_id']:r for r in grant['receipts']},
            'publisher_continuation_receipt_pins')
    depth, cursor = 1, record
    while cursor['version'] == 2:
        depth += 1
        cursor = cursor['history'][0]
    require(depth < 8 and len(refs) < 128, 'publisher_continuation_bound')


def invocation_continuation_record(current, binding, packet, selection):
    """Propose one atomic normal-owner state transition from a sealed grant."""
    import native_publisher_invocation as module
    from dataclasses import asdict
    require(current.owner_custody and binding.phase == 'integration', 'publisher_continuation_owner')
    grant = module.continuation(selection['context'].get('publisher_continuation'),asdict(binding))
    record = current.state.get(INVOCATIONS,{}).get(binding.operation_id)
    require(record is not None and module.fingerprint(record) == grant['previous_record_sha256']
        and record['selection_sha256'] == grant['previous_selection_sha256']
        and record['capability'] == grant['previous_capability'], 'publisher_continuation_record_pin')
    capability = invocation_capability(selection['context']['publisher_invocation'])
    require(capability['closure_sha256'] != record['capability']['closure_sha256'],
            'publisher_continuation_new_closure')
    if 'pre_admission_refusal' in grant:
        pre_admission_history(module,grant,record,binding,packet)
        return dict(version=2,binding=asdict(binding),selection_sha256=fingerprint(selection),
            capability=capability,invocations=[],history=[json.loads(json.dumps(record))],
            continuation=json.loads(json.dumps(grant)),recovery_observation=None)
    complete_continuation_history(module,record,binding,packet,grant)
    return dict(version=2,binding=asdict(binding),selection_sha256=fingerprint(selection),
        capability=capability,invocations=[],history=[json.loads(json.dumps(record))],
        continuation=json.loads(json.dumps(grant)))


async def invocation_transaction(current, binding, packet, selection, mode, calls, authorize):
    """One helper call per constructed finite boundary; same-UUID recovery only."""
    from dataclasses import asdict
    from pathlib import Path
    from uuid import uuid4
    import hashlib
    import native_publisher_invocation as module
    require(current.config['source_sha256'].get('tools/delivery/native_publisher_invocation.py') ==
            hashlib.sha256(Path(module.__file__).read_bytes()).hexdigest(), 'publisher_invocation_source_pin')
    capability = invocation_capability(selection['context']['publisher_invocation'])
    require(authorize(current, binding) is True, 'publisher_invocation_authority')
    selected_sha = fingerprint(selection)
    records = current.state.get(INVOCATIONS, {})
    require(type(records) is dict, 'publisher_invocation_custody')
    record = records.get(binding.operation_id)
    if record is not None:
        require(record['selection_sha256'] == selected_sha
            and record['capability'] == capability and type(record['invocations']) is list
            and len(record['invocations']) <= 128, 'publisher_invocation_rebind')
        invocation_epochs(module,record,binding,packet)
    recovered_original=None
    if (record and record['version'] == 2 and not record['invocations']
        and 'pre_admission_refusal' in record['continuation']):
        recovered_original,absent=recovery_observation(module,record,binding,packet)
        require(mode == 'observe','pre_admission_observe_only')
        if not absent:
            require(not calls[0],'publisher_next_boundary_required')
            envelope={**recovered_original,'mode':'observe'}
            record['recovery_observation']=dict(envelope=envelope,result=None)
            current.save()  # Read intent, never a manufactured complete receipt.
            calls[0]+=1
            raw=await fixed_invocation_wire(envelope)
            value=module.validate_result(module.decode(raw),envelope,capability['closure_sha256'])
            record['recovery_observation']['result']=value
            current.save()  # Retain an existing/unknown receipt too, then hold.
            recovery_observation(module,record,binding,packet)
            return dict(operation_id=binding.operation_id,status='pending',child_tree_gone=False)
    latest = record['invocations'][-1] if record and record['invocations'] else None
    reobserve = False
    if mode == 'observe' and latest and latest['status'] == 'complete':
        try:
            prior = invocation_projection(module, latest['result'], latest['envelope'], capability, binding.phase)
        except RuntimeHold as error:
            require(str(error) in ('publisher_invocation_native_outcome_held',
                                   'publisher_native_outcome_held'), 'publisher_invocation_contradiction')
            prior = None
        # Readiness alone grants no refill: ONE later step goes back through the
        # privileged helper's fresh prior-receipt/Controller gates. Verified
        # effects are instead re-read from their protected original receipt;
        # caller-cached JSON alone must not authorize final-unit/refill progress.
        if prior and prior['status'] == 'ready' and latest['envelope']['request']['mode'] == 'observe':
            return prior
        reobserve = bool(prior and prior['status'] in ('verified', 'denied', 'failed'))
    if calls[0]:
        raise RuntimeHold('publisher_next_boundary_required')
    if latest and (latest['status'] != 'complete' or reobserve):
        # A lost/malformed/absent reply is not proof that invoke never executed.
        # Observe this UUID with the ORIGINAL inner request, even if it was step.
        envelope = {**latest['envelope'], 'mode': 'observe'}
    else:
        if mode in ('step','publish'):
            require(latest is not None and latest['envelope']['request']['mode'] == 'observe'
                    and invocation_projection(module, latest['result'], latest['envelope'],
                                              capability, binding.phase)['status'] == 'ready',
                    'publisher_readiness_required')
        elif latest is not None:
            # Only the ORIGINAL durable kernel-stopped proof permits a fresh
            # supervised READONLY reconciliation. Native null/pending/unknown is
            # never verified and cannot authorize another step/action replay.
            proven = module.validate_result(latest['result'], latest['envelope'], capability['closure_sha256'])
            require(proven['status'] == 'complete', 'publisher_invocation_unresolved')
        envelope = (recovered_original if recovered_original is not None else
                    dict(version=1, mode='invoke', invocation_id=str(uuid4()),
                         request=publisher_request(binding, packet, mode)))
        module.request(module.wire(envelope))
        if record is None:
            record = dict(version=1, binding=asdict(binding), selection_sha256=selected_sha,
                          capability=capability, invocations=[])
            current.state.setdefault(INVOCATIONS, {})[binding.operation_id] = record
        total, cursor = 0, record
        while True:
            total += len(cursor['invocations'])
            if cursor['version'] == 1: break
            cursor = cursor['history'][0]
        require(total < 128, 'publisher_invocation_budget')
        latest = dict(envelope=json.loads(json.dumps(envelope)),
                      last_request=json.loads(json.dumps(envelope)), status='pending', result=None)
        record['invocations'].append(latest)
    latest['last_request'] = json.loads(json.dumps(envelope))
    latest['status'] = 'pending'
    current.save()  # EXACT current outer+inner intent, before EVERY helper call.
    calls[0] += 1
    try:
        raw = await fixed_invocation_wire(envelope)
        value = module.validate_result(module.decode(raw), envelope, capability['closure_sha256'])
        latest.update(status='complete' if value['status'] == 'complete' else 'unknown', result=value)
        current.save()
    except BaseException:
        latest['status'] = 'unknown'
        current.save()
        raise
    return invocation_projection(module, value, envelope, capability, binding.phase)


async def produce_native_publication(current, issue, packet):
    """Normal owner caller; return the existing selection, no Root config write."""
    from stokowski_adapter import file_sha, read_record
    from native_publisher_invocation import prepare_request, decode, hex64, exact
    import native_publisher_invocation
    from dataclasses import asdict
    current.guard()
    require(current.owner_custody and not current.read_only and not current.stopping,'native_prepare_owner')
    require(current.config['source_sha256'].get('tools/delivery/native_publisher_invocation.py') ==
        file_sha(native_publisher_invocation.__file__),'native_prepare_source_pin')
    runtime,_,_=current.context(issue.identifier,review=True,observation=True)
    path=runtime/'native-publication-packet.json'
    require(read_record(current.private(str(path))) == packet,'native_prepare_packet_file')
    unit=current.gate_binding(issue,observation=True);handoff=packet['handoff']
    envelope=dict(version=1,mode='prepare',issue=issue.identifier,issue_id=issue.id,
        project_id=handoff['project_id'],owner=current.config['owner'],unit_sha256=fingerprint(unit),
        packet_sha256=fingerprint(packet))
    prepare_request(envelope)
    reply=decode(await fixed_invocation_wire(envelope),1048576)
    require(exact(reply,{'version','kind','operation_id','unit_sha256','packet_sha256','source_sha256',
        'integration_binding','closure_sha256','host_confirmation_sha256'}) and type(reply['version']) is int
        and reply['version'] == 1 and reply['kind'] == 'native-publisher-prepared-v1'
        and all(hex64(reply[k]) for k in ('operation_id','unit_sha256','packet_sha256','source_sha256',
            'closure_sha256','host_confirmation_sha256'))
        and reply['operation_id'] == fingerprint(reply['integration_binding'])
        and all(reply[k] == envelope[k] for k in ('unit_sha256','packet_sha256'))
        and reply['source_sha256'] == fingerprint(handoff['source']), 'native_prepare_reply')
    b=reply['integration_binding'];source=handoff['source']
    require(b['issue_id'] == issue.id and b['owner'] == envelope['owner'] and b['repository'] == 'maldous/offmenu'
        and b['version'] == 2 and b['pr_number'] is None and 'source_projection' not in b
        and all(b[k] == source[k] for k in ('head','base','tree')) and b['head_branch'] == source['branch']
        and b['outputs'] == {v['path']:v['sha256'] for v in handoff['outputs']},'native_prepare_reply_source')
    binding=OwnerBinding(issue.id,envelope['project_id'],envelope['owner'],envelope['packet_sha256'],
        reply['operation_id'],'integration',envelope['unit_sha256'])
    request=dict(version=1,mode='review',invocation_id=None,request=publisher_request(binding,packet,'observe'))
    pending=dict(runtime=str(current.runtime),issue=issue.identifier,actor_uid=1000,
        source_head=current.config['source_head'],source_sha256=current.config['source_sha256'],
        unit_binding=unit,publisher_review_binding=b,publisher_review=request)
    # A normal UUID is part of the existing read-only review transport identity.
    from uuid import uuid5, NAMESPACE_URL
    request['invocation_id']=str(uuid5(NAMESPACE_URL,'offmenu:native-review:'+binding.operation_id))
    return dict(binding=asdict(binding),packet=dict(path=str(path),sha256=file_sha(path)),context=dict(
        native_runtime=str(runtime),pending_unit_review=pending,publisher_invocation=dict(version=1,
            closure_sha256=reply['closure_sha256'],host_confirmation_sha256=reply['host_confirmation_sha256'])))


async def verified_canonical_source(current, issue, binding):
    """Correlate the authenticated publisher fact; no HTTP or merge replay."""
    from dataclasses import asdict
    import native_publisher_invocation as helper
    from stokowski_adapter import file_sha
    current.guard()
    require(type(binding) is OwnerBinding and binding.phase == 'integration' and current.owner_custody
        and issue.id == binding.issue_id,'accepted_source_owner')
    require(current.config['source_sha256'].get('tools/delivery/native_publisher_invocation.py') ==
        file_sha(helper.__file__),'accepted_source_reader_pin')
    selection=current._native_harness_selection(issue.identifier)
    require(selection['binding'] == asdict(binding)
        and fingerprint(current.gate_binding(issue,observation=True)) == binding.unit_sha256,
        'accepted_source_unit')
    packet=pinned_private(current,selection['packet'])
    require(fingerprint(packet) == binding.packet_sha256,'accepted_source_packet')
    source=packet['handoff']['source'];context=selection['context']
    integration=context.get('pending_unit_review',{}).get('publisher_review_binding',{})
    require(integration.get('version') == 2 and 'source_projection' not in integration
        and fingerprint(integration) == binding.operation_id,'accepted_source_native_selection')
    from pathlib import Path
    policy_module=Path(__file__).resolve().with_name('stokowski_prepare.py')
    require(current.config['source_sha256'].get('tools/delivery/stokowski_prepare.py') ==
        file_sha(policy_module),'accepted_source_policy_reader_pin')
    import stokowski_prepare
    require(Path(stokowski_prepare.__file__).resolve() == policy_module,'accepted_source_policy_reader_path')
    policy=stokowski_prepare.owner_intake_policy(current.config)
    descriptor=helper.project_source(policy.get('project_source'))
    path=helper.ACCEPTED/'by-operation'/(binding.operation_id+'.json')
    raw=helper._read(path,984,0o444)
    reference=dict(path=str(path),sha256=helper.sha(raw))
    fact=helper.read_accepted_fact(reference,descriptor)
    require(all(fact[k] == getattr(binding,k) for k in ('operation_id','unit_sha256','packet_sha256'))
        and fact['base'] == source['base'] and fact['candidate_head'] == source['head']
        and fact['tree'] == source['tree'] and fact['policy_sha256'] == integration['policy_sha256'],
        'accepted_source_selection_mismatch')
    return dict(fact=fact,evidence=reference)
