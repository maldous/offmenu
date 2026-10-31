"""Read-only evidence inspection; recorded acceptance is not current authority."""
import json

from .engine import DeliveryError, digest, output_state, validate_task
from .effect_observations import EffectContext, project_effect
from .standards import git


UNCERTAIN = {'running', 'uncertain', 'timed_out', 'cancelled'}


def project_native_handoff(handoff, policy, *, native_receipt_bytes=None):
    """Project owner-selected v1 references, never qualify their external truth.

    Requires tools/delivery on PYTHONPATH. Only an explicitly supplied original
    native coding receipt is read; referenced files are never followed. Its exact
    bytes must match the origin pin and original attempt/lease/source identity.
    No imported execution, resource-pool or transport module is constructed.
    """
    import hashlib
    from native_harness_contract import fingerprint, validate_handoff
    from stokowski_performance import project_observation

    value = validate_handoff(handoff, policy)
    execution = project_observation({})
    if native_receipt_bytes is not None:
        if (type(native_receipt_bytes) is not bytes or len(native_receipt_bytes) > 262144
                or value['origin']['kind'] != 'native-coding-v1'
                or 'attempt' not in value
                or hashlib.sha256(native_receipt_bytes).hexdigest()
                != value['origin']['evidence']['sha256']):
            raise DeliveryError('Native observation receipt pin mismatch')
        try:
            receipt = json.loads(native_receipt_bytes)
        except (ValueError, RecursionError):
            raise DeliveryError('Native observation receipt JSON invalid') from None
        if (type(receipt) is not dict or receipt.get('origin') != 'native-coding'
                or receipt.get('attempt') != value['attempt']['id']
                or receipt.get('lease') != value['attempt']['lease_id']
                or receipt.get('source_head') != value['source']['base']):
            raise DeliveryError('Native observation receipt identity mismatch')
        execution = project_observation(receipt)
        # A requested model or completed turn alone cannot resolve the provider.
        if receipt.get('resolution_status') != 'observed':
            execution['observed']['model'] = None
    operation = value.get('operation')
    effect = value.get('effect')
    return {
        'schema_version': 1, 'kind': 'offmenu-native-observation',
        'authority': 'observation_only',
        'handoff_sha256': fingerprint(value),
        'references_verified': False,
        'issue_id': value['issue_id'], 'project_id': value['project_id'],
        'owner': value['owner'], 'source': value['source'],
        'origin': value['origin'], 'attempt': value.get('attempt'),
        'operation': operation,
        'source_acceptance': {
            'recorded_review': value.get('review'),
            'integration': 'unknown', 'release': 'unknown',
        },
        'effect': effect if effect is not None else {'status': 'unknown'},
        'execution': {key: execution[key] for key in (
            'requested', 'observed', 'declared_resources', 'sampled_resources')},
        'cost_usd': None, 'runtime_readback': 'unknown',
        'next_pickup': {'status': 'unknown', 'owner_record': value['origin']['evidence']},
        'recovery': {
            'reconciliation_required': bool(operation and (
                operation['status'] in ('submitted', 'running', 'unknown')
                or effect is None or effect['status'] in ('pending', 'unknown'))),
            'operation_id': operation['id'] if operation else None,
            'owner_record': operation['receipt'] if operation else value['origin']['evidence'],
        },
        'evidence': value['evidence'],
    }


def inspect_task(root, task, *, effect_observation=None,
                 effect_context: EffectContext | None = None, effect_phases=()):
    """Inspect without constructing an Engine, opening a saver or taking ownership.

    This observes separate files, not an atomic snapshot of an active writer.
    Source/check/log validation remains the runner's responsibility.
    Optional external metadata requires separate owner-provided trust context,
    bound to this task's immutable request/owner/source. It never changes local
    receipt acceptance or supplies execution verification. No CLI trust flag.
    """
    root = root.resolve()
    validate_task(task)
    effect = None
    if effect_observation is not None or effect_context is not None or effect_phases:
        if (type(effect_context) is not EffectContext
                or effect_context.expected.request_id != task['id']
                or effect_context.expected.owner != task['owner']
                or effect_context.expected.source_commit != task['base_revision']):
            raise DeliveryError('Effect context task binding mismatch')
        try:
            effect = project_effect(effect_observation, effect_context, effect_phases)
        except ValueError as error:
            raise DeliveryError(str(error)) from error
    directory = root / '.delivery' / task['id']

    def read(name):
        path = directory / name
        if not path.resolve().is_relative_to(root):
            raise DeliveryError('Evidence outside checkout: ' + name)
        if not path.is_file():
            return None
        record = json.loads(path.read_text())
        if not isinstance(record, dict):
            raise DeliveryError('Evidence must be an object: ' + name)
        return record

    result = {
        'schema_version': 1,
        'kind': 'offmenu-delivery-evidence',
        'task_id': task['id'],
        'recorded_status': 'not_found',
        'acceptance_record_present': False,
        'identity_matches': False,
        'outputs_match': False,
        'outputs': {},
        'checks': [],
        'reconciliation_required': [],
        'cancellation_requested': False,
        'checkpoint_available': False,
        'source_and_execution_evidence_verified': False,
        'authority': 'observation_only',
        'reasons': [],
    }
    binding = read('binding.json')
    if effect is not None:
        result['external_effect'] = effect
    if binding is None:
        result['reasons'].append('binding_not_found')
        return result
    expected = {'task_sha256': digest(task), 'root': str(root), 'owner': task['owner']}
    if any(binding.get(key) != value for key, value in expected.items()):
        raise DeliveryError('Task binding mismatch')
    branch = git(root, 'branch', '--show-current')
    revision = git(root, 'rev-parse', 'HEAD')
    result['identity_matches'] = (
        branch == binding.get('branch') and revision == task['base_revision']
        and branch.startswith(('feature/', 'bugfix/'))
        and task.get('branch', branch) == branch)
    if not result['identity_matches']:
        if effect is not None:
            raise DeliveryError('Effect context current task binding mismatch')
        result['reasons'].append('revision_or_branch_changed')
    actual = output_state(root, task)
    result['outputs'] = {name: {'expected': expected, 'actual': actual[name],
                              'matches': actual[name] == expected}
                         for name, expected in task['accepted_outputs'].items()}
    result['outputs_match'] = all(item['matches'] for item in result['outputs'].values())
    if not result['outputs_match']:
        result['reasons'].append('output_drift')
    accepted = read('accepted.json')
    if accepted is not None:
        if (accepted.get('task_sha256') != digest(task)
                or accepted.get('revision') != task['base_revision']
                or accepted.get('owner') != task['owner']
                or accepted.get('branch') != binding.get('branch')
                or accepted.get('outputs') != task['accepted_outputs']
                or accepted.get('status') != 'accepted'):
            raise DeliveryError('Acceptance record binding mismatch')
        result['acceptance_record_present'] = True
        result['recorded_status'] = 'accepted'
    else:
        result['recorded_status'] = 'not_accepted'
    for step in task['checks']:
        record = read(step['id'] + '.json')
        state = {'id': step['id'], 'status': record.get('status') if record else 'not_started'}
        if record:
            state.update({key: record[key] for key in ('attempt', 'returncode') if key in record})
            if record.get('status') in UNCERTAIN:
                result['reconciliation_required'].append(step['id'])
        result['checks'].append(state)
    if result['reconciliation_required']:
        result['reasons'].append('command_requires_reconciliation')
    result['cancellation_requested'] = read('cancel.json') is not None
    checkpoint = directory / 'graph.sqlite'
    if not checkpoint.resolve().is_relative_to(root):
        raise DeliveryError('Checkpoint outside checkout')
    result['checkpoint_available'] = checkpoint.is_file()
    return result
