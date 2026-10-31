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
            actions = [v for v in metadata['actions'] if v['issue_id'] == issue.id]
            if not actions:
                return {**result, 'status': 'idle'}
            context['action'] = actions[0]  # one finite native metadata transaction
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
