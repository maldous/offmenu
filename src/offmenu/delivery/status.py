"""Read-only evidence inspection; recorded acceptance is not current authority."""
import json

from .engine import DeliveryError, digest, output_state, validate_task
from .effect_observations import EffectContext, project_effect
from .standards import git


UNCERTAIN = {'running', 'uncertain', 'timed_out', 'cancelled'}


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
