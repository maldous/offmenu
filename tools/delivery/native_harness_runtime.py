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
        require(issue.id == binding.issue_id
                and current.entries[issue.identifier]['issue_id'] == issue.id
                and current.route['project_id'] == binding.project_id
                and current.config['owner'] == binding.owner, 'native_identity')
        # Preserve every existing manifest/admission/resource/provider/receipt gate.
        current.context(issue.identifier, review=True, observation=True)
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
            engine = await resolved(adapters.engine(binding))
            context['engine'] = engine_acceptance(engine, handoff, candidate)
            review = await resolved(adapters.review(current, issue, binding))
            require(current._check_unit_review(review) == unit, 'independent_review_binding')
            context['review'] = review_coverage(review, handoff, candidate)
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
        ref = current.config['native_harness_boundaries'][issue.identifier]
        actual = pinned_private(current, ref)
        require(fingerprint(actual) == fingerprint(selected)
                and set(actual) == {'binding', 'packet', 'context'}
                and actual['binding'] == asdict(binding), 'owner_selection_drift')
        context = actual['context']
        require(type(context) is dict and (set(context) in (
                    {'engine_root', 'engine_task', 'unit_review'},
                    {'engine_root', 'engine_task', 'unit_review', 'publisher_invocation'})
                or (binding.phase == 'linear' and context == {})),
                'owner_context_fields')
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
        return pinned_private(current, selected['context']['unit_review'])
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
    return OwnerAdapters(authorize, load, engine, review, observe, step)


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
        require(type(record) is dict and set(record) == {
            'version', 'binding', 'selection_sha256', 'capability', 'invocations'}
            and type(record['version']) is int and record['version'] == 1
            and record['binding'] == asdict(binding) and record['selection_sha256'] == selected_sha
            and record['capability'] == capability and type(record['invocations']) is list
            and 1 <= len(record['invocations']) <= 128, 'publisher_invocation_rebind')
        for old in record['invocations']:
            require(type(old) is dict and set(old) == {'envelope', 'last_request', 'status', 'result'}
                    and old['status'] in ('pending', 'unknown', 'complete'), 'publisher_invocation_record')
            original = module.request(module.wire(old['envelope']))
            require(original['mode'] == 'invoke'
                    and original['request'] == publisher_request(binding, packet, original['request']['mode']),
                    'publisher_invocation_original_request')
            last = module.request(module.wire(old['last_request']))
            require(last['invocation_id'] == original['invocation_id']
                    and last['request'] == original['request'], 'publisher_invocation_transport_request')
            if old['result'] is not None:
                validated = module.validate_result(old['result'], original, capability['closure_sha256'])
                if validated['receipt'] is not None:
                    require(validated['receipt']['body']['intent']['phase'] == binding.phase,
                            'publisher_invocation_phase')
                if validated['response'] is not None:
                    publisher_response(validated['response'], original['request'], binding.phase)
            if old['status'] == 'complete':
                require(old['result'] is not None and old['result']['status'] == 'complete',
                        'publisher_invocation_completion')
        require(all(old['status'] == 'complete' for old in record['invocations'][:-1]),
                'publisher_invocation_prior_unresolved')
        ids = [old['envelope']['invocation_id'] for old in record['invocations']]
        require(len(ids) == len(set(ids)), 'publisher_invocation_duplicate_identity')
    latest = record['invocations'][-1] if record else None
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
        if mode == 'step':
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
        envelope = dict(version=1, mode='invoke', invocation_id=str(uuid4()),
                        request=publisher_request(binding, packet, mode))
        module.request(module.wire(envelope))
        if record is None:
            record = dict(version=1, binding=asdict(binding), selection_sha256=selected_sha,
                          capability=capability, invocations=[])
            current.state.setdefault(INVOCATIONS, {})[binding.operation_id] = record
        require(len(record['invocations']) < 128, 'publisher_invocation_budget')
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
