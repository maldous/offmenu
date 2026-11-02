"""One native Linear metadata effect under the existing CurrentWork owner lock.

The admitted caller supplies a sealed OwnerBinding and an existing LinearClient.
No credentials, queue, transport retries or apply CLI. Legacy metadata methods
never change workflow state; the opt-in source-only tail below requires its
own sealed class authority and original acceptance proofs.
"""
from dataclasses import asdict, is_dataclass
import copy
import json
import re
from uuid import UUID

import httpx

from native_harness_contract import fingerprint


class LinearEffectHold(ValueError):
    """Fixed codes only; never retain upstream errors or raw comment bodies."""


STORE = 'native_harness_linear'
BINDING_FIELDS = {'issue_id', 'project_id', 'owner', 'packet_sha256',
                  'operation_id', 'phase', 'unit_sha256'}
PAYLOADS = {'linear-link-pr': {'url'},
            'linear-ensure-dependency': {'blocked_by_id'},
            'linear-record-source-milestone': {'milestone_id', 'milestone'}}
CONNECTIONS = {
    'linear-link-pr': ('attachments', 'id url'),
    'linear-ensure-dependency': ('inverseRelations',
                                'id type issue { id state { type } } relatedIssue { id }'),
    'linear-record-source-milestone': ('comments', 'id body'),
}
MUTATIONS = {
    'linear-link-pr': ('attachmentCreate', 'AttachmentCreateInput!'),
    'linear-ensure-dependency': ('issueRelationCreate', 'IssueRelationCreateInput!'),
    'linear-record-source-milestone': ('commentCreate', 'CommentCreateInput!'),
}
MAX_PAGES = 20
PAGE_SIZE = 50


def require(ok, code):
    if not ok:
        raise LinearEffectHold(code)


def uuid(value):
    try:
        require(type(value) is str and str(UUID(value)) == value and UUID(value).int != 0,
                'linear_uuid')
    except (ValueError, TypeError, AttributeError):
        raise LinearEffectHold('linear_uuid') from None


def milestone_body(action):
    """Exact source-only marker AND content; marker-only comments never qualify."""
    return ('[OffMenu source milestone; no workflow-state change]\n'
            'native-source-milestone:' + action['milestone_id'] + '\n\n'
            + json.dumps(action['milestone'], sort_keys=True, separators=(',', ':'),
                         ensure_ascii=True, allow_nan=False))


class NativeLinearAdapter:
    def __init__(self, client):
        from stokowski.linear import LinearClient
        require(isinstance(client, LinearClient), 'linear_native_client_required')
        self.client = client

    def _validate(self, current, binding, action):
        require(is_dataclass(binding) and not isinstance(binding, type)
                and binding.__dataclass_params__.frozen, 'linear_owner_binding')
        bound = asdict(binding)
        fingerprint(bound)
        fingerprint(action)
        require(set(bound) == BINDING_FIELDS and bound['phase'] == 'linear', 'linear_owner_binding')
        for key in ('issue_id', 'project_id'):
            uuid(bound[key])
        for key in ('packet_sha256', 'unit_sha256', 'operation_id'):
            require(type(bound[key]) is str and re.fullmatch('[0-9a-f]{64}', bound[key]),
                    'linear_owner_binding')
        require(type(action) is dict and action.get('kind') in PAYLOADS, 'linear_action_kind')
        require(set(action) == {'version', 'kind', 'action_id', 'issue_id', 'project_id'}
                | PAYLOADS[action['kind']] and type(action['version']) is int
                and action['version'] == 1, 'linear_action_fields')
        require(action['action_id'] == fingerprint({k: v for k, v in action.items() if k != 'action_id'})
                == bound['operation_id'], 'linear_action_identity')
        require(action['issue_id'] == bound['issue_id'] and action['project_id'] == bound['project_id'],
                'linear_action_scope')
        require(not current.read_only and not current.stopping, 'linear_owner_stopped')
        current.guard()
        require(current.config['owner'] == current.state['owner'] == bound['owner']
                and current.route['project_id'] == bound['project_id'], 'linear_owner_scope')
        require(any(entry.get('issue_id') == bound['issue_id'] for entry in current.entries.values()),
                'linear_current_issue_scope')
        if action['kind'] == 'linear-link-pr':
            require(type(action['url']) is str and re.fullmatch(
                r'https://github\.com/maldous/offmenu/pull/[1-9][0-9]*', action['url']), 'linear_pr_url')
        elif action['kind'] == 'linear-ensure-dependency':
            uuid(action['blocked_by_id'])
            require(action['blocked_by_id'] != bound['issue_id'], 'linear_dependency_self')
        else:
            milestone = action['milestone']
            require(type(milestone) is dict and action['milestone_id'] == fingerprint(milestone),
                    'linear_milestone_identity')
            stage = milestone.get('stage')
            require((stage == 'source-integrated' and milestone.get('target') == 'develop')
                    or (stage == 'source-released' and milestone.get('target') == 'main'),
                    'linear_source_milestone_only')
        return copy.deepcopy(bound), copy.deepcopy(action)

    def _record(self, current, bound, action):
        records = current.state.get(STORE, {})
        require(type(records) is dict, 'linear_custody_shape')
        record = records.get(bound['operation_id'])
        if record is not None:
            require(type(record) is dict and set(record) == {
                        'version', 'binding', 'action', 'status', 'evidence'}
                    and record.get('binding') == bound and record.get('action') == action
                    and type(record.get('version')) is int and record['version'] == 1
                    and record.get('status') in {'pending', 'unknown', 'verified', 'denied', 'failed'},
                    'linear_custody_conflict')
        return record

    def _save(self, current, bound, action, status, evidence=None):
        self._record(current, bound, action)
        current.state.setdefault(STORE, {})[bound['operation_id']] = {
            'version': 1, 'binding': bound, 'action': action, 'status': status,
            'evidence': evidence,
        }
        current.save()

    @staticmethod
    def _result(bound, status):
        # This metadata adapter starts no subprocess. This flag says nothing
        # about a coding/validation child; those retain their original owners.
        return {'operation_id': bound['operation_id'], 'status': status, 'child_tree_gone': True}

    async def _readback(self, bound, action):
        field, selection = CONNECTIONS[action['kind']]
        query = (f'query NativeMetadataRead($issueId: String!, $after: String) {{ '
                 f'issue(id: $issueId) {{ id project {{ id }} '
                 f'{field}(first: {PAGE_SIZE}, after: $after) {{ '
                 f'nodes {{ {selection} }} pageInfo {{ hasNextPage endCursor }} }} }} }}')
        cursor, cursors, matches = None, set(), []
        dependency_state = None
        for _ in range(MAX_PAGES):
            data = await self.client._graphql(query, {'issueId': bound['issue_id'], 'after': cursor})
            issue = data.get('issue') if type(data) is dict else None
            require(type(issue) is dict and issue.get('id') == bound['issue_id']
                    and issue.get('project', {}).get('id') == bound['project_id'], 'linear_readback_scope')
            connection = issue.get(field)
            require(type(connection) is dict and type(connection.get('nodes')) is list
                    and len(connection['nodes']) <= PAGE_SIZE, 'linear_readback_shape')
            for node in connection['nodes']:
                require(type(node) is dict and type(node.get('id')) is str and 0 < len(node['id']) <= 128,
                        'linear_readback_node')
                if field == 'attachments':
                    require(type(node.get('url')) is str, 'linear_readback_node')
                    matched = node['url'] == action['url']
                elif field == 'comments':
                    require(type(node.get('body')) is str and len(node['body']) <= 262144,
                            'linear_readback_node')
                    marker = 'native-source-milestone:' + action['milestone_id']
                    matched = node['body'] == milestone_body(action)
                    require(marker not in node['body'] or matched, 'linear_milestone_content_conflict')
                else:
                    require(type(node.get('issue')) is dict and type(node.get('relatedIssue')) is dict
                            and type(node.get('type')) is str, 'linear_readback_node')
                    matched = (node['type'] == 'blocks' and node['issue'].get('id') == action['blocked_by_id']
                               and node['relatedIssue'].get('id') == bound['issue_id'])
                    if matched:
                        dependency_state = node['issue'].get('state', {}).get('type')
                        require(dependency_state in ('triage', 'backlog', 'unstarted', 'started',
                                                     'completed', 'canceled'), 'linear_dependency_state')
                if matched:
                    matches.append(node['id'])
            info = connection.get('pageInfo')
            require(type(info) is dict and type(info.get('hasNextPage')) is bool, 'linear_pagination_shape')
            if info['hasNextPage'] is False:
                require(len(matches) <= 1, 'linear_duplicate_readback')
                return {'native_ids': matches, 'connection_complete': True,
                        'blocker_state_type': dependency_state}
            cursor = info.get('endCursor')
            require(type(cursor) is str and 0 < len(cursor) <= 2048 and cursor not in cursors,
                    'linear_pagination_cursor')
            cursors.add(cursor)
        raise LinearEffectHold('linear_readback_page_limit')

    async def observe(self, current, binding, action):
        """Fresh native reads only; retained absent/unknown effects never get a write."""
        bound, action = self._validate(current, binding, action)
        previous = self._record(current, bound, action)
        try:
            evidence = await self._readback(bound, action)
        except Exception:
            status = (previous['status'] if previous and previous['status'] in ('denied', 'failed')
                      else 'unknown')
            if previous is not None:
                self._save(current, bound, action, status)
            return self._result(bound, status)
        self._validate(current, binding, action)
        if evidence['native_ids']:
            self._save(current, bound, action, 'verified', evidence)
            return self._result(bound, 'verified')
        if previous is not None:
            status = previous['status'] if previous['status'] in ('denied', 'failed') else 'unknown'
            self._save(current, bound, action, status, evidence)
            return self._result(bound, status)
        return self._result(bound, 'ready')

    async def step(self, current, binding, action):
        """Persist intent, send at most once, then require exact native readback."""
        bound, action = self._validate(current, binding, action)
        prior = self._record(current, bound, action)
        observed = await self.observe(current, binding, action)
        if prior is not None or observed['status'] != 'ready':
            return observed
        self._validate(current, binding, action)
        require(self._record(current, bound, action) is None, 'linear_concurrent_intent')
        self._save(current, bound, action, 'pending')
        # A save failure prevents the call. Cancellation/process loss afterwards
        # retains pending intent, and all reentry is read-only reconciliation.
        if action['kind'] == 'linear-link-pr':
            payload = {'issueId': bound['issue_id'], 'url': action['url'], 'title': 'OffMenu source PR'}
        elif action['kind'] == 'linear-ensure-dependency':
            payload = {'issueId': action['blocked_by_id'], 'relatedIssueId': bound['issue_id'], 'type': 'blocks'}
        else:
            payload = {'issueId': bound['issue_id'], 'body': milestone_body(action)}
        field, input_type = MUTATIONS[action['kind']]
        query = f'mutation NativeMetadataWrite($input: {input_type}) {{ {field}(input: $input) {{ success }} }}'
        try:
            result = await self.client._graphql(query, {'input': payload})
            success = result.get(field, {}).get('success') if type(result) is dict else None
            if success is False:
                self._save(current, bound, action, 'failed')
            elif success is not True:
                self._save(current, bound, action, 'unknown')
        except httpx.HTTPStatusError as error:
            status = 'denied' if error.response.status_code in (401, 403) else 'unknown'
            self._save(current, bound, action, status)
        except Exception:
            self._save(current, bound, action, 'unknown')
        return await self.observe(current, binding, action)


# Opt-in source-only outcomes. These helpers consume the existing sealed owner
# policy and CurrentWork custody; they are not a queue or a general status API.
SOURCE_OUTCOMES = 'native_source_outcomes'
ACCEPTED_SOURCE = 'accepted_project_source'
SOURCE_REPOSITORY = '/home/user/src/offmenu'
PUBLISHER_SOURCE_ROOT = '/var/lib/offmenu-publisher/accepted-sources'
PUBLISHER_UID = 984


def _sha(value, length=64):
    require(type(value) is str and re.fullmatch('[0-9a-f]{%d}' % length, value),
            'source_outcome_digest')
    return value


def _source_policy(current):
    from stokowski_adapter import CurrentWork
    require(type(current) is CurrentWork, 'source_outcome_current_required')
    current.guard()
    require(type(current.owner_custody) is dict and not current.stopping
            and not (current.runtime / 'cancel.json').exists(), 'source_outcome_owner_required')
    require(type(current.config.get('owner_intake_policy')) is dict, 'source_outcome_disabled')
    from stokowski_prepare import owner_intake_policy
    policy = owner_intake_policy(current.config)
    require(policy['owner'] == current.config['owner']
            and policy['coordinator_runtime'] == str(current.runtime), 'source_outcome_policy_owner')
    return policy


def _project_source_config(policy):
    from pathlib import Path
    config = policy['project_source']
    require(set(config) == {'repository', 'branch', 'origin', 'source_repository', 'seed', 'accepted_facts_path'}
            and config['repository'] == 'maldous/offmenu' and config['branch'] == 'develop'
            and config['origin'] == 'git@github.com:maldous/offmenu.git'
            and config['source_repository'] == SOURCE_REPOSITORY
            and config['accepted_facts_path'] == str(Path(PUBLISHER_SOURCE_ROOT) / 'latest.json'),
            'accepted_source_repository')
    require(set(config['seed']) == {'head', 'tree'}, 'accepted_source_seed')
    _sha(config['seed']['head'], 40); _sha(config['seed']['tree'], 40)
    require(Path(config['source_repository']).is_dir(), 'accepted_source_repository_missing')
    return config


def _publisher_record(path, *, expected=None, optional=False):
    """Fixed UID984 metadata custody; no keys, private bodies or privilege helper."""
    import hashlib
    import os
    from pathlib import Path
    import stat
    root, path = Path(PUBLISHER_SOURCE_ROOT), Path(path)
    valid_path = (path == root / 'latest.json'
        or path.parent == root / 'by-commit' and re.fullmatch(r'[0-9a-f]{40}\.json', path.name)
        or path.parent == root / 'by-operation' and re.fullmatch(r'[0-9a-f]{64}\.json', path.name))
    require(root == root.resolve() and path.parent == path.parent.resolve() and valid_path,
            'accepted_source_fixed_path')
    for directory_path in {root, path.parent}:
        try:
            directory = directory_path.lstat()
        except OSError:
            raise LinearEffectHold('accepted_source_directory_custody') from None
        require(stat.S_ISDIR(directory.st_mode) and directory.st_uid == PUBLISHER_UID
                and stat.S_IMODE(directory.st_mode) == 0o755, 'accepted_source_directory_custody')
    try:
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    except FileNotFoundError:
        require(optional, 'accepted_source_fact_missing')
        return None
    except OSError:
        raise LinearEffectHold('accepted_source_file_custody') from None
    try:
        before = os.fstat(fd)
        require(stat.S_ISREG(before.st_mode) and before.st_uid == PUBLISHER_UID
                and before.st_nlink == 1 and stat.S_IMODE(before.st_mode) == 0o444
                and 0 < before.st_size <= 262144, 'accepted_source_file_custody')
        raw = os.read(fd, 262145)
        after = os.fstat(fd)
        require((before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns, before.st_ctime_ns)
                == (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns, after.st_ctime_ns)
                and len(raw) == before.st_size, 'accepted_source_read_changed')
    finally:
        os.close(fd)
    digest = hashlib.sha256(raw).hexdigest()
    require(expected is None or digest == expected, 'accepted_source_fact_digest')
    def unique(pairs):
        result = {}
        for key, value in pairs:
            require(key not in result, 'accepted_source_duplicate_key')
            result[key] = value
        return result
    value = json.loads(raw, object_pairs_hook=unique)
    fingerprint(value)
    return value, {'path': str(path), 'sha256': digest}


def _git_environment():
    import os
    return {**os.environ, 'GIT_NO_LAZY_FETCH': '1', 'GIT_OPTIONAL_LOCKS': '0', 'GIT_TERMINAL_PROMPT': '0'}


def _source_git(config, *args):
    import subprocess
    try:
        return subprocess.check_output(['git', '-C', config['source_repository'], *args],
            timeout=10, stderr=subprocess.DEVNULL, env=_git_environment()).decode().strip()
    except (subprocess.SubprocessError, OSError, UnicodeError):
        raise LinearEffectHold('accepted_source_git_read') from None


def _corroborate_git(config, fact):
    import subprocess
    # Acquisition129 may still need to fetch THIS accepted object. Absence is
    # not acceptance of any remote tip; the protected chain remains authority.
    present = subprocess.run(['git', '-C', config['source_repository'], 'cat-file', '-e',
                              fact['head'] + '^{commit}'], timeout=10,
                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, env=_git_environment())
    if present.returncode != 0:
        return
    require(_source_git(config, 'rev-parse', fact['head'] + '^{tree}') == fact['tree']
            and _source_git(config, 'show', '-s', '--format=%P', fact['head']).split() == fact['parents'],
            'accepted_source_git_identity')


def _fact(config, ref):
    from pathlib import Path
    require(type(ref) is dict and set(ref) == {'path', 'sha256'}, 'accepted_source_reference')
    _sha(ref['sha256'])
    fact, actual = _publisher_record(ref['path'], expected=ref['sha256'])
    require(set(fact) == {'schema', 'repository', 'branch', 'head', 'tree', 'parents',
                         'base', 'candidate_head', 'operation_id', 'unit_sha256', 'packet_sha256',
                         'policy_sha256', 'pr_url', 'helper_receipt', 'previous', 'observed_at'}
            and fact['schema'] == 'offmenu-accepted-project-source/1'
            and fact['repository'] == 'maldous/offmenu' and fact['branch'] == 'develop',
            'accepted_source_fact_schema')
    for key in ('head', 'tree', 'base', 'candidate_head'):
        _sha(fact[key], 40)
    for key in ('operation_id', 'unit_sha256', 'packet_sha256', 'policy_sha256'):
        _sha(fact[key])
    require(actual['path'] in {
                str(Path(PUBLISHER_SOURCE_ROOT) / 'by-commit' / (fact['head'] + '.json')),
                str(Path(PUBLISHER_SOURCE_ROOT) / 'by-operation' / (fact['operation_id'] + '.json'))}
            and fact['parents'] == [fact['base'], fact['candidate_head']]
            and type(fact['pr_url']) is str and re.fullmatch(
                r'https://github\.com/maldous/offmenu/pull/[1-9][0-9]*', fact['pr_url']),
            'accepted_source_canonical_binding')
    helper = fact['helper_receipt']
    require(type(helper) is dict and set(helper) == {'path', 'sha256'}
            and type(helper['path']) is str and helper['path'].startswith('/var/lib/offmenu-publisher/')
            and len(helper['path']) <= 4096 and '..' not in Path(helper['path']).parts,
            'accepted_source_helper_reference')
    _sha(helper['sha256'])
    require(type(fact['observed_at']) is int and fact['observed_at'] > 0,
            'accepted_source_observed_at')
    _corroborate_git(config, fact)
    return fact, actual


def _source_chain(config, fact, *, required_ancestor=None):
    """Immutable previous references, with Git ancestry as a bounded anchor."""
    cursor, visited, found = fact, set(), required_ancestor is None
    for _ in range(128):
        require(cursor['head'] not in visited, 'accepted_source_chain_cycle')
        visited.add(cursor['head'])
        found = found or cursor['head'] == required_ancestor or cursor['base'] == required_ancestor
        previous = cursor['previous']
        if previous == {'schema': 'offmenu-accepted-project-source-seed/1',
                        **config['seed'], 'policy_sha256': fingerprint(config)}:
            require(cursor['base'] == config['seed']['head'] and found, 'accepted_source_seed_chain')
            return
        previous_fact, _ = _fact(config, previous)
        require(previous_fact['head'] == cursor['base'], 'accepted_source_previous_binding')
        if found:
            try:
                anchored = (_source_git(config, 'merge-base', config['seed']['head'], previous_fact['head'])
                            == config['seed']['head'])
            except LinearEffectHold:
                anchored = False
            if anchored:
                return
        cursor = previous_fact
    raise LinearEffectHold('accepted_source_chain_bound')


def accepted_project_source(current, project_id):
    """Read application M from publisher984 custody, never control H/raw tip."""
    policy = _source_policy(current)
    projects = {c['project_id'] for c in policy['contracts'].values()}
    projects.update(policy.get('workclass', {}).get('project_ids', []))
    require(project_id in projects, 'accepted_source_project')
    config = _project_source_config(policy)
    prior = current.state.get(ACCEPTED_SOURCE)
    pointer = _publisher_record(config['accepted_facts_path'], optional=True)
    if pointer is None:
        require(prior is None, 'accepted_source_missing_facts')
        source, evidence = config['seed'], copy.deepcopy(current.config['owner_intake_policy'])
        require(_source_git(config, 'rev-parse', source['head'] + '^{tree}') == source['tree'],
                'accepted_source_seed_git')
    else:
        wrapper, _ = pointer
        require(type(wrapper) is dict and set(wrapper) == {'schema', 'latest'}
                and wrapper['schema'] == 'offmenu-accepted-project-source-pointer/1',
                'accepted_source_pointer_schema')
        source, evidence = _fact(config, wrapper['latest'])
        _source_chain(config, source, required_ancestor=prior['head'] if prior else None)
    return {'repository': config['repository'], 'branch': 'develop', 'head': source['head'],
            'tree': source['tree'], 'evidence': evidence}


def _pin(current, ref):
    value = current._private_pin(ref)
    fingerprint(value)
    return value


def _canonical_source(current, policy, binding, handoff, ref):
    config = _project_source_config(policy)
    canonical, evidence = _fact(config, ref)
    _source_chain(config, canonical)
    require(canonical['operation_id'] == binding.operation_id
            and canonical['unit_sha256'] == binding.unit_sha256
            and canonical['packet_sha256'] == binding.packet_sha256
            and canonical['candidate_head'] == handoff['source']['head'], 'canonical_source_binding')
    return canonical, evidence


def _project_source_projection(current, source):
    # This state is a convenience projection, never proof of publisher custody.
    current.state[ACCEPTED_SOURCE] = copy.deepcopy(source)
    current.save()


def _source_grant(current, policy, issue, manifest):
    # The existing compiler/qualifier owns contract construction and provenance.
    from stokowski_prepare import owner_policy_contract
    issued = owner_policy_contract(current.config, policy, issue.identifier)
    outcome = issued.get('source_outcome')
    require(type(outcome) is dict and set(outcome) == {
        'full_issue_contract', 'team_id', 'description_sha256', 'done_state_id'},
        'source_outcome_grant')
    grant = {'issue_id': issued['issue_id'], 'project_id': issued['project_id'],
             'team_id': outcome['team_id'], 'assignee_id': issued['assignee_id'],
             'delegate_id': None, 'description_sha256': outcome['description_sha256'],
             'contract': {'acceptance': issued['acceptance'], 'allowed_paths': issued['scope']},
             'close_issue': outcome['full_issue_contract'], 'done_state_id': outcome['done_state_id'],
             'dependencies': issued['dependencies'],
             'selection_label': (policy.get('workclass', {}).get('selection_label')
                                 if issue.identifier not in policy['contracts'] else None)}
    require(grant['issue_id'] == issue.id, 'source_outcome_grant_identity')
    task = manifest['tasks'][issue.identifier]
    require(type(grant['close_issue']) is bool and grant['contract'] == {
        'acceptance': task['acceptance'], 'allowed_paths': task['allowed_paths']},
        'source_outcome_full_contract')
    require(grant['contract']['acceptance'] and grant['contract']['allowed_paths']
            and type(grant['contract']['acceptance']) is list, 'source_outcome_empty_contract')
    for key in ('issue_id', 'project_id', 'team_id'):
        uuid(grant[key])
    for key in ('assignee_id', 'done_state_id'):
        if grant[key] is not None:
            uuid(grant[key])
    require(not grant['close_issue'] or (grant['done_state_id'] is not None
            and issue.identifier not in ('UIF-102', 'UIF-130')), 'source_outcome_done_state')
    _sha(grant['description_sha256'])
    return grant


def source_outcome_id(outcome):
    return fingerprint({'issue_id': outcome['issue_id'], 'unit_sha256': outcome['unit_sha256'],
                        'operation_id': outcome['canonical']['operation_id']})


def source_outcome_body(outcome):
    return ('[OffMenu bounded source outcome; no product/runtime acceptance]\n'
            'native-source-outcome:' + source_outcome_id(outcome) + '\n\n'
            + json.dumps(outcome, sort_keys=True, separators=(',', ':'), ensure_ascii=True, allow_nan=False))


class _SourceOutcomeMetadata(NativeLinearAdapter):
    """Only the sealed class-authorized source contract can select issueUpdate."""
    async def read(self, current, issue, grant, outcome=None):
        import hashlib
        # Pages include the same fresh identity/rights/dependency context; a
        # changed issue on any page fails before a write or acceptance.
        query = (f'query NativeSourceOutcome($issueId: String!, $after: String) {{ issue(id:$issueId) {{ '
                 'id identifier description project { id } team { id states { nodes { id type } } } '
                 'assignee { id } delegate { id } state { id type } '
                 'labels(first:100) { nodes { name } pageInfo { hasNextPage } } '
                 'inverseRelations { nodes { type issue { id state { type } } } pageInfo { hasNextPage } } '
                 f'comments(first:{PAGE_SIZE},after:$after) {{ nodes {{ id body }} '
                 'pageInfo { hasNextPage endCursor } } } }')
        cursor, cursors, matches = None, set(), []
        for _ in range(MAX_PAGES):
            data = await self.client._graphql(query, {'issueId': issue.id, 'after': cursor})
            remote = data.get('issue') if type(data) is dict else None
            require(type(remote) is dict and remote['id'] == issue.id
                    and remote['identifier'] == issue.identifier
                    and remote['project']['id'] == grant['project_id']
                    and remote['team']['id'] == grant['team_id']
                    and (remote.get('assignee') or {}).get('id') == grant['assignee_id']
                    and (remote.get('delegate') or {}).get('id') == grant['delegate_id']
                    and hashlib.sha256((remote['description'] or '').encode()).hexdigest()
                    == grant['description_sha256'], 'source_outcome_fresh_identity')
            if grant['selection_label']:
                require(remote['labels']['pageInfo']['hasNextPage'] is False
                        and grant['selection_label'] in [v['name'] for v in remote['labels']['nodes']],
                        'source_outcome_class_rights_changed')
            require(remote['state']['type'] in ('backlog', 'unstarted', 'started', 'completed'),
                    'source_outcome_cancelled_or_unknown')
            relations = remote['inverseRelations']
            require(relations['pageInfo']['hasNextPage'] is False
                    and type(relations['nodes']) is list and len(relations['nodes']) <= 128,
                    'source_outcome_dependencies_incomplete')
            require(sorted(row['issue']['id'] for row in relations['nodes'] if row['type'] == 'blocks')
                    == sorted(grant['dependencies']), 'source_outcome_dependency_drift')
            for entry in current.entries.values():
                if entry['issue_id'] in grant['dependencies']:
                    require(current._reconciled_unit(entry['issue']), 'source_outcome_dependency_native_hold')
            require(all(row['issue']['state']['type'] == 'completed'
                        for row in relations['nodes'] if row['type'] == 'blocks'),
                    'source_outcome_dependencies_held')
            if grant['close_issue']:
                states = remote['team']['states']['nodes']
                require(len([s for s in states if s['id'] == grant['done_state_id']
                             and s['type'] == 'completed']) == 1, 'source_outcome_done_state')
            connection = remote['comments']
            require(type(connection['nodes']) is list and len(connection['nodes']) <= PAGE_SIZE,
                    'source_outcome_comments_shape')
            for node in connection['nodes']:
                if outcome is None:
                    continue
                body = node['body']
                require(type(body) is str and len(body) <= 262144, 'source_outcome_comment_shape')
                marker = 'native-source-outcome:' + source_outcome_id(outcome)
                require(marker not in body or body == source_outcome_body(outcome),
                        'source_outcome_comment_conflict')
                if body == source_outcome_body(outcome):
                    matches.append(node['id'])
            info = connection['pageInfo']
            if info['hasNextPage'] is False:
                require(len(matches) <= 1, 'source_outcome_duplicate_evidence')
                return {'comment_ids': matches, 'state_id': remote['state']['id'],
                        'state_type': remote['state']['type']}
            require(info['hasNextPage'] is True and type(info.get('endCursor')) is str
                    and info['endCursor'] and info['endCursor'] not in cursors,
                    'source_outcome_comment_cursor')
            cursor = info['endCursor']
            cursors.add(cursor)
        raise LinearEffectHold('source_outcome_page_limit')

    async def apply(self, current, issue, grant, outcome, authorize):
        key = source_outcome_id(outcome)
        record = current.state.setdefault(SOURCE_OUTCOMES, {}).get(key)
        if record is None:
            record = {'outcome': outcome, 'comment': None, 'completion': None}
            current.state[SOURCE_OUTCOMES][key] = record
            current.save()
        require(record['outcome'] == outcome, 'source_outcome_custody_conflict')
        # A pending/unknown mutation is reconciled only, never sent again.
        for stage in ('comment', 'completion'):
            if stage == 'completion' and not grant['close_issue']:
                return {'status': 'verified', 'outcome_id': key, 'closed': False}
            authorize()
            observed = await self.read(current, issue, grant, outcome)
            authorize()
            found = (bool(observed['comment_ids']) if stage == 'comment' else
                     observed['state_id'] == grant['done_state_id'] and observed['state_type'] == 'completed')
            if record[stage] == 'denied':
                return {'status': 'denied', 'outcome_id': key, 'closed': False}
            if found:
                record[stage] = 'verified'
                current.save()
                continue
            if record[stage] is not None:
                record[stage] = 'failed' if record[stage] == 'failed' else 'unknown'
                current.save()
                return {'status': record[stage], 'outcome_id': key, 'closed': False}
            # Do not overwrite an unrelated completed status.
            if stage == 'completion':
                require(observed['state_type'] != 'completed', 'source_outcome_already_completed_elsewhere')
            import time
            require(time.time() < _source_policy(current)['expires_at'], 'source_outcome_policy_expired')
            record[stage] = 'pending'
            current.save()
            authorize()
            if stage == 'comment':
                query = 'mutation NativeSourceEvidence($input: CommentCreateInput!) { commentCreate(input:$input) { success } }'
                variables = {'input': {'issueId': issue.id, 'body': source_outcome_body(outcome)}}
            else:
                query = ('mutation NativeSourceComplete($id: String!, $input: IssueUpdateInput!) '
                         '{ issueUpdate(id:$id,input:$input) { success } }')
                variables = {'id': issue.id, 'input': {'stateId': grant['done_state_id']}}
            try:
                reply = await self.client._graphql(query, variables)
                mutation = 'commentCreate' if stage == 'comment' else 'issueUpdate'
                if reply.get(mutation, {}).get('success') is False:
                    record[stage] = 'failed'
                    current.save()
            except httpx.HTTPStatusError as error:
                record[stage] = 'denied' if error.response.status_code in (401, 403) else 'unknown'
                current.save()
            except Exception:
                record[stage] = 'unknown'
                current.save()
            authorize()
            observed = await self.read(current, issue, grant, outcome)
            authorize()
            found = (bool(observed['comment_ids']) if stage == 'comment' else
                     observed['state_id'] == grant['done_state_id'] and observed['state_type'] == 'completed')
            if record[stage] == 'denied':
                return {'status': 'denied', 'outcome_id': key, 'closed': False}
            record[stage] = 'verified' if found else ('failed' if record[stage] == 'failed' else 'unknown')
            current.save()
            if not found:
                return {'status': record[stage], 'outcome_id': key, 'closed': False}
        return {'status': 'verified', 'outcome_id': key, 'closed': True}


async def finalize_source_outcome(current, issue, binding, *, policy, outcome, linear_client):
    """Fixed adapter callback AFTER verified integration, before refill.

    No merge/computation callable is accepted. Reentry may only re-read original
    proofs and reconcile the two exact metadata effects in CurrentWork custody.
    """
    from native_harness_runtime import native_journal_acceptance, review_coverage
    result = {'accepted_delivery': False, 'refill_eligible': False}
    try:
        require(not current.read_only, 'source_outcome_read_only')
        require(policy == _source_policy(current), 'source_outcome_policy_drift')
        require(binding.phase == 'integration' and binding.owner == policy['owner']
                and binding.issue_id == issue.id,
                'source_outcome_binding')
        runtime, manifest, _ = current.context(issue.identifier, review=True, observation=True)
        grant = _source_grant(current, policy, issue, manifest)
        require(binding.project_id == grant['project_id'], 'source_outcome_project')
        unit = current.gate_binding(issue, observation=True)
        require(fingerprint(unit) == binding.unit_sha256, 'source_outcome_unit_drift')
        effect = outcome['effect']
        require(effect == {'operation_id': binding.operation_id, 'status': 'verified', 'child_tree_gone': True},
                'source_outcome_unverified_effect')
        from dataclasses import asdict
        selected = current._native_harness_selection(issue.identifier)
        require(selected['binding'] == asdict(binding), 'source_outcome_selected_binding')
        packet = _pin(current, selected['packet'])
        require(fingerprint(packet) == binding.packet_sha256
                and packet['handoff'] == outcome['handoff'] and packet['candidate'] is None,
                'source_outcome_selected_packet')
        from native_harness_contract import validate_handoff
        handoff = validate_handoff(packet['handoff'], packet['policy'])
        review = _pin(current, outcome['review'])
        require(current._check_unit_review(review) == unit, 'source_outcome_review_binding')
        review_coverage(review, handoff, None)
        # Existing original native receipt/Pool gate and successful Journal reader.
        current._completed_native_evidence(issue.identifier, runtime, manifest)
        validation = native_journal_acceptance(current, issue, str(runtime), handoff)
        import native_harness_runtime as runtime_module
        from stokowski_adapter import SOURCE, file_sha
        from pathlib import Path
        module_path = 'tools/delivery/native_harness_runtime.py'
        require(Path(runtime_module.__file__).resolve() == SOURCE / module_path
                and current.config['source_sha256'].get(module_path) == file_sha(runtime_module.__file__),
                'source_outcome_canonical_reader_pin')
        reader = getattr(runtime_module, 'verified_canonical_source', None)
        require(callable(reader), 'source_outcome_canonical_reader_missing')
        verified = await reader(current, issue, binding)
        require(type(verified) is dict and set(verified) == {'fact', 'evidence'}
                and verified['evidence'] == outcome['canonical'], 'source_outcome_canonical_reader_binding')
        canonical, canonical_ref = _canonical_source(current, policy, binding, handoff, verified['evidence'])
        require(canonical == verified['fact'], 'source_outcome_canonical_reader_binding')
        def authorize():
            require(policy == _source_policy(current) and not current.stopping,
                    'source_outcome_authority_changed')
            require(fingerprint(current.gate_binding(issue, observation=True)) == binding.unit_sha256,
                    'source_outcome_unit_drift')
            _canonical_source(current, policy, binding, handoff, canonical_ref)
        authorize()
        metadata_adapter = _SourceOutcomeMetadata(linear_client)
        await metadata_adapter.read(current, issue, grant)
        authorize()
        latest = accepted_project_source(current, binding.project_id)
        _project_source_projection(current, latest)
        payload = {'version': 1, 'issue_id': issue.id, 'project_id': binding.project_id,
                   'owner': binding.owner, 'unit_sha256': binding.unit_sha256,
                   'contract': grant['contract'], 'original_request': {
                       'path': str(runtime / 'requests' / (issue.identifier + '.json')),
                       'sha256': __import__('hashlib').sha256(
                           (runtime / 'requests' / (issue.identifier + '.json')).read_bytes()).hexdigest()},
                   'native_validation': validation, 'review': outcome['review'],
                   'canonical': canonical, 'canonical_evidence': canonical_ref, 'source_only': True,
                   'full_issue_contract': grant['close_issue'], 'accepted_delivery': False}
        metadata = await metadata_adapter.apply(current, issue, grant, payload, authorize)
        return {**result, **metadata, 'refill_eligible': metadata['status'] == 'verified'}
    except Exception as error:
        return {**result, 'status': 'held', 'reason': str(error) if isinstance(error, LinearEffectHold)
                else type(error).__name__}
