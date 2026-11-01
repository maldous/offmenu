"""Pure native Linear metadata planning; only the root owner consumes actions.

No credentials, network, queue, receipt migration or workflow-state mutation.
Input observations must be freshly read/qualified by the root's native adapters.
"""
import argparse
import json
from pathlib import Path
import re
from uuid import UUID


class LinearPlanError(ValueError):
    pass


def _object(value, required, optional=()):
    if not isinstance(value, dict) or not set(required) <= set(value) or set(value) - set(required) - set(optional):
        raise LinearPlanError('Invalid Linear observation fields')
    return value


def _text(value):
    if not isinstance(value, str) or not value.strip() or len(value) > 2048 or any(ord(c) < 32 for c in value):
        raise LinearPlanError('Expected bounded nonempty text')
    return value


def _uuid(value):
    if not isinstance(value, str):
        raise LinearPlanError('Expected canonical UUID')
    try:
        if str(UUID(value)) != value or UUID(value).int == 0:
            raise ValueError()
    except ValueError:
        raise LinearPlanError('Expected canonical UUID') from None
    return value


def _hash(value, length=64):
    if not isinstance(value, str) or not re.fullmatch('[0-9a-f]{%d}' % length, value):
        raise LinearPlanError('Invalid immutable digest')
    return value


def _list(value):
    if not isinstance(value, list) or len(value) > 128:
        raise LinearPlanError('Expected bounded list')
    return value


def _unique(values):
    if len(values) != len(set(values)):
        raise LinearPlanError('Duplicate identity')
    return values


def resolve_outcome(value, projects):
    """Resolve normalized native observations, never historical slug/branch guesses."""
    _object(value, ('id', 'identifier', 'project_id', 'team_id', 'state_type',
                    'blocked_by', 'pr_urls', 'milestone_ids'))
    for field in ('id', 'project_id', 'team_id'):
        _uuid(value[field])
    if not re.fullmatch(r'UIF-[1-9][0-9]*', _text(value['identifier'])):
        raise LinearPlanError('Expected native UIF identifier')
    project = projects.get(value['project_id'])
    if not project or project['team_id'] != value['team_id']:
        raise LinearPlanError('Issue/project/team mismatch')
    if value['state_type'] not in ('backlog', 'unstarted', 'started', 'completed', 'canceled'):
        raise LinearPlanError('Unknown native workflow state type')
    blocked = []
    for dependency in _list(value['blocked_by']):
        _object(dependency, ('id', 'state_type'))
        _uuid(dependency['id'])
        if dependency['id'] == value['id'] or dependency['state_type'] not in ('backlog', 'unstarted', 'started', 'completed', 'canceled'):
            raise LinearPlanError('Invalid native dependency')
        blocked.append(dependency['id'])
    _unique(blocked)
    _unique([_text(url) for url in _list(value['pr_urls'])])
    _unique([_hash(key) for key in _list(value['milestone_ids'])])
    return json.loads(json.dumps(value))


def _pr(value, repository):
    _object(value, ('url', 'head', 'tree', 'base', 'merged', 'canonical_verified'), ('merge_commit',))
    if not re.fullmatch(r'https://github\.com/' + re.escape(repository) + r'/pull/[1-9][0-9]*', _text(value['url'])):
        raise LinearPlanError('PR must belong to the selected repository')
    _hash(value['head'], 40)
    _hash(value['tree'], 40)
    if value['base'] not in ('develop', 'main') or type(value['merged']) is not bool or type(value['canonical_verified']) is not bool:
        raise LinearPlanError('Invalid canonical PR observation')
    if value['merged']:
        _hash(value.get('merge_commit'), 40)
    elif 'merge_commit' in value:
        raise LinearPlanError('Unmerged PR cannot claim a merge commit')
    return value


def plan_delivery(request, policy):
    """Return finite desired metadata actions and native dependency observations.

    Root qualifies external GitHub facts; shared validators qualify handoffs and
    release candidate structure. Neither source fact establishes product Done.
    Pending/unknown/denied effects are supplied from existing custody, never a new
    local journal. Successful effects still require native metadata readback.
    """
    from native_harness_contract import fingerprint, validate_handoff, validate_release_candidate

    # Reuse the common bounded JSON traversal, then detach caller-owned inputs.
    fingerprint(request)
    request = json.loads(json.dumps(request, allow_nan=False))
    _object(request, ('version', 'projects', 'outcomes', 'changes', 'dependencies', 'effects'), ('promotion',))
    if type(request['version']) is not int or request['version'] != 1:
        raise LinearPlanError('Unsupported Linear request version')
    projects = {}
    for project in _list(request['projects']):
        _object(project, ('id', 'name', 'team_id'))
        _uuid(project['id'])
        _uuid(project['team_id'])
        if project['name'] not in ('UIF', 'OffMenu') or project['id'] in projects:
            raise LinearPlanError('Invalid selected native project')
        projects[project['id']] = project
    outcomes = {}
    identifiers = set()
    for value in _list(request['outcomes']):
        issue = resolve_outcome(value, projects)
        if issue['id'] in outcomes or issue['identifier'] in identifiers:
            raise LinearPlanError('Ambiguous native outcome')
        outcomes[issue['id']] = issue
        identifiers.add(issue['identifier'])
    effects = {}
    for effect in _list(request['effects']):
        _object(effect, ('action_id', 'status'))
        _hash(effect['action_id'])
        if effect['status'] not in ('pending', 'unknown', 'denied', 'succeeded', 'failed') or effect['action_id'] in effects:
            raise LinearPlanError('Invalid or conflicting metadata effect')
        effects[effect['action_id']] = effect['status']
    actions, holds = {}, {}

    def emit(kind, issue_id, payload):
        issue = outcomes[issue_id]
        body = {'version': 1, 'kind': kind, 'issue_id': issue_id,
                'project_id': issue['project_id'], **payload}
        action_id = fingerprint(body)
        # Failed effects require an explicit owner decision; success needs readback.
        if action_id in effects:
            holds[action_id] = {'action_id': action_id, 'status': effects[action_id],
                                'next_action': 'owner-reconcile-native-readback'}
        else:
            actions[action_id] = {'action_id': action_id, **body}

    source_issues = {}
    repository = policy['repository']
    for change in _list(request['changes']):
        _object(change, ('handoff', 'pull_request'))
        handoff = validate_handoff(change['handoff'], policy)
        issue_id = handoff['issue_id']
        if issue_id not in outcomes or handoff['project_id'] != outcomes[issue_id]['project_id']:
            raise LinearPlanError('Handoff outcome/project mismatch')
        pr = _pr(change['pull_request'], repository)
        source = handoff['source']
        if source['target'] != 'develop' or pr['base'] != 'develop' or source['head'] != pr['head'] or source['tree'] != pr['tree']:
            raise LinearPlanError('Develop PR does not match exact handoff source')
        source_issues.setdefault(issue_id, set()).add(source['head'])
        if pr['url'] not in outcomes[issue_id]['pr_urls']:
            emit('linear-link-pr', issue_id, {'url': pr['url']})
        if pr['merged'] and pr['canonical_verified']:
            milestone = {'stage': 'source-integrated', 'target': 'develop',
                         'source': source, 'pull_request': pr['url'],
                         'merge_commit': pr['merge_commit']}
            key = fingerprint(milestone)
            if key not in outcomes[issue_id]['milestone_ids']:
                emit('linear-record-source-milestone', issue_id,
                     {'milestone_id': key, 'milestone': milestone})

    for relation in _list(request['dependencies']):
        _object(relation, ('issue_id', 'blocked_by_id'))
        issue_id, blocker = relation['issue_id'], relation['blocked_by_id']
        _uuid(issue_id)
        _uuid(blocker)
        if issue_id not in outcomes or blocker not in outcomes or issue_id == blocker:
            raise LinearPlanError('Dependency requires two resolved distinct outcomes')
        if blocker not in {item['id'] for item in outcomes[issue_id]['blocked_by']}:
            emit('linear-ensure-dependency', issue_id, {'blocked_by_id': blocker})

    if 'promotion' in request:
        promotion = _object(request['promotion'], ('candidate', 'issue_ids', 'pull_request', 'tag'))
        candidate = validate_release_candidate(promotion['candidate'], policy)
        ids = _unique([_uuid(item) for item in _list(promotion['issue_ids'])])
        if not ids or any(item not in source_issues for item in ids):
            raise LinearPlanError('Promotion requires explicit constituent source outcomes')
        pr = _pr(promotion['pull_request'], repository)
        source = candidate['source']
        if pr['base'] != 'main' or pr['head'] != source['head'] or pr['tree'] != source['tree']:
            raise LinearPlanError('Promotion PR must match frozen candidate')
        tag = promotion['tag']
        if tag is not None:
            _object(tag, ('name', 'commit', 'tree', 'immutable_verified'))
            _text(tag['name'])
            _hash(tag['commit'], 40)
            _hash(tag['tree'], 40)
            if type(tag['immutable_verified']) is not bool:
                raise LinearPlanError('Invalid immutable tag observation')
            if not pr['merged'] or tag['commit'] != pr['merge_commit'] or tag['tree'] != source['tree']:
                raise LinearPlanError('Tag must match canonical release commit/tree')
        for issue_id in ids:
            if pr['url'] not in outcomes[issue_id]['pr_urls']:
                emit('linear-link-pr', issue_id, {'url': pr['url']})
            if pr['merged'] and pr['canonical_verified'] and tag and tag['immutable_verified']:
                milestone = {'stage': 'source-released', 'target': 'main',
                             'candidate_id': fingerprint(candidate), 'source': source,
                             'pull_request': pr['url'], 'tag': tag['name'],
                             'merge_commit': pr['merge_commit'], 'issue_ids': sorted(ids)}
                key = fingerprint(milestone)
                if key not in outcomes[issue_id]['milestone_ids']:
                    emit('linear-record-source-milestone', issue_id,
                         {'milestone_id': key, 'milestone': milestone})
    eligibility = []
    for issue_id, issue in sorted(outcomes.items()):
        unresolved = sorted(item['id'] for item in issue['blocked_by'] if item['state_type'] != 'completed')
        # Desired dependency changes cannot become eligibility before readback.
        unresolved += sorted({r['blocked_by_id'] for r in request['dependencies']
                              if r['issue_id'] == issue_id and r['blocked_by_id'] not in
                              {d['id'] for d in issue['blocked_by']}})
        eligibility.append({'issue_id': issue_id, 'unresolved_dependencies': sorted(set(unresolved)),
                            'dependencies_satisfied': not unresolved})
    return {'version': 1, 'actions': [actions[key] for key in sorted(actions)],
            'holds': [holds[key] for key in sorted(holds)], 'dependencies': eligibility,
            'workflow_state_changes': [], 'deployment_acceptance': 'not-established'}


def _pairs(pairs):
    value = {}
    for key, item in pairs:
        if key in value:
            raise LinearPlanError('Duplicate JSON field')
        value[key] = item
    return value


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--request', type=Path, required=True)
    parser.add_argument('--policy', type=Path, required=True)
    args = parser.parse_args(argv)
    from native_harness_contract import ContractError, load_release_policy
    try:
        with args.request.open('rb') as handle:
            raw = handle.read(1024 * 1024 + 1)
        if len(raw) > 1024 * 1024:
            raise LinearPlanError('Request exceeds 1 MiB')
        request = json.loads(raw, object_pairs_hook=_pairs,
                             parse_constant=lambda _: (_ for _ in ()).throw(LinearPlanError('Nonfinite JSON')))
        result = plan_delivery(request, load_release_policy(args.policy))
    except (LinearPlanError, ContractError, ValueError, TypeError, RecursionError, OSError):
        print(json.dumps({'status': 'invalid-linear-request'}))
        return 2
    print(json.dumps(result, sort_keys=True, separators=(',', ':'), allow_nan=False))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
