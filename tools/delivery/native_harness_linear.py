"""One native Linear metadata effect under the existing CurrentWork owner lock.

The admitted caller supplies a sealed OwnerBinding and an existing LinearClient.
No credentials, queue, workflow-state updates, transport retries or apply CLI.
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
