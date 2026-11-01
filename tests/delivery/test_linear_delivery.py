"""Native metadata planning with the real shared contract and synthetic facts."""
import copy
import io
import json
from pathlib import Path
import tempfile
import unittest
from contextlib import redirect_stdout
from unittest.mock import patch

import linear_delivery as linear
import native_harness_contract as contract


ROOT = Path(__file__).resolve().parents[2]
ISSUE = '67ce7259-7dee-473c-88ed-26a409a25b44'
SECOND = '9e8f1660-a671-4c78-9f23-11c5866afffb'
PROJECT = 'ffb6c7d9-4eff-46eb-a805-99f0cc2edfa0'
OFFMENU = 'ce60c1ab-a732-4a71-8471-14c9dc393886'
TEAM = '53f584e7-70a1-4b1e-b982-b815210e47d4'


class LinearDeliveryTests(unittest.TestCase):
    def setUp(self):
        self.policy = contract.load_release_policy(ROOT / 'config/delivery-release-policy.json')
        ref = {'path': '.delivery/existing/receipt.json', 'sha256': 'a' * 64}
        self.handoff = dict(version=1, kind='delivery-handoff-v1', issue_id=ISSUE,
                            project_id=PROJECT, owner='component-owner',
                            origin={'kind': 'reviewed-source-v1', 'evidence': ref},
                            source=dict(repository='maldous/offmenu', branch='feature/component',
                                        base='b' * 40, head='c' * 40, tree='d' * 40,
                                        target='develop', policy_sha256=contract.fingerprint(self.policy)),
                            outputs=[], evidence=[ref])
        self.pr = dict(url='https://github.com/maldous/offmenu/pull/201', head='c' * 40,
                       tree='d' * 40, base='develop', merged=True, canonical_verified=True,
                       merge_commit='e' * 40)
        self.request = dict(version=1,
                            projects=[dict(id=PROJECT, name='UIF', team_id=TEAM),
                                      dict(id=OFFMENU, name='OffMenu', team_id=TEAM)],
                            outcomes=[self.issue()],
                            changes=[dict(handoff=self.handoff, pull_request=self.pr)],
                            dependencies=[], effects=[])

    def issue(self, issue_id=ISSUE, identifier='UIF-123'):
        return dict(id=issue_id, identifier=identifier, project_id=PROJECT, team_id=TEAM,
                    state_type='started', blocked_by=[], pr_urls=[], milestone_ids=[])

    def plan(self):
        return linear.plan_delivery(self.request, self.policy)

    def promotion(self, issue_ids=None):
        candidate = dict(version=1, kind='release-candidate-v1',
                         source={**self.handoff['source'], 'branch': 'develop', 'target': 'main'},
                         required_profiles=['unit', 'recovery'],
                         artifacts=[{'path': 'dist/artifact.tar.gz', 'sha256': 'f' * 64}])
        return dict(candidate=candidate, issue_ids=issue_ids or [ISSUE],
                    pull_request={**self.pr, 'base': 'main',
                                  'url': 'https://github.com/maldous/offmenu/pull/202'},
                    tag=dict(name='v1.2.3', commit='e' * 40, tree='d' * 40, immutable_verified=True))

    def test_exact_identity_ignores_legacy_project_binding(self):
        result = self.plan()
        self.assertTrue(result['actions'])
        self.assertEqual({a['project_id'] for a in result['actions']}, {PROJECT})
        self.handoff['project_id'] = OFFMENU
        with self.assertRaisesRegex(linear.LinearPlanError, 'project mismatch'):
            self.plan()

    def test_multiple_attempts_and_prs_share_one_outcome(self):
        second = copy.deepcopy(self.request['changes'][0])
        second['handoff']['source'].update(head='1' * 40, tree='2' * 40)
        second['pull_request'].update(url='https://github.com/maldous/offmenu/pull/203',
                                      head='1' * 40, tree='2' * 40, merge_commit='3' * 40)
        self.request['changes'] += [second, copy.deepcopy(second)]
        result = self.plan()
        self.assertEqual(len(result['actions']), 4)
        self.assertEqual({a['issue_id'] for a in result['actions']}, {ISSUE})
        self.assertEqual(len(result['dependencies']), 1)
        self.assertNotIn('attempt', self.handoff)

    def test_develop_merge_and_main_tag_never_close_product(self):
        self.request['promotion'] = self.promotion()
        result = self.plan()
        stages = {a['milestone']['stage'] for a in result['actions'] if 'milestone' in a}
        self.assertEqual(stages, {'source-integrated', 'source-released'})
        self.assertEqual(result['workflow_state_changes'], [])
        self.assertEqual(result['deployment_acceptance'], 'not-established')
        self.assertNotIn('Done', json.dumps(result))

    def test_promotion_keeps_every_canonical_issue_link(self):
        self.request['outcomes'].append(self.issue(SECOND, 'UIF-122'))
        change = copy.deepcopy(self.request['changes'][0])
        change['handoff']['issue_id'] = SECOND
        self.request['changes'].append(change)
        self.request['promotion'] = self.promotion([ISSUE, SECOND])
        result = self.plan()
        links = [a for a in result['actions'] if a['kind'] == 'linear-link-pr' and a['url'].endswith('/202')]
        self.assertEqual({a['issue_id'] for a in links}, {ISSUE, SECOND})
        for action in result['actions']:
            if action.get('milestone', {}).get('stage') == 'source-released':
                self.assertEqual(action['milestone']['issue_ids'], sorted([ISSUE, SECOND]))

    def test_native_readback_suppresses_noops(self):
        first = self.plan()
        for action in first['actions']:
            if action['kind'] == 'linear-link-pr':
                self.request['outcomes'][0]['pr_urls'].append(action['url'])
            else:
                self.request['outcomes'][0]['milestone_ids'].append(action['milestone_id'])
        self.assertEqual(self.plan()['actions'], [])

    def test_all_prior_effects_hold_until_owner_reconciliation(self):
        actions = self.plan()['actions']
        for status in ('pending', 'unknown', 'denied', 'succeeded', 'failed'):
            with self.subTest(status=status):
                self.request['effects'] = [dict(action_id=a['action_id'], status=status) for a in actions]
                result = self.plan()
                self.assertEqual(result['actions'], [])
                self.assertEqual({h['status'] for h in result['holds']}, {status})
                self.assertEqual(len(result['holds']), 2)

    def test_dependencies_are_native_and_desired_changes_need_readback(self):
        self.request['outcomes'].append(self.issue(SECOND, 'UIF-122'))
        relation = dict(issue_id=ISSUE, blocked_by_id=SECOND)
        self.request['dependencies'] = [relation, relation]
        result = self.plan()
        self.assertEqual(sum(a['kind'] == 'linear-ensure-dependency' for a in result['actions']), 1)
        self.assertFalse(next(d for d in result['dependencies'] if d['issue_id'] == ISSUE)['dependencies_satisfied'])
        self.request['outcomes'][0]['blocked_by'] = [dict(id=SECOND, state_type='completed')]
        result = self.plan()
        self.assertFalse(any(a['kind'] == 'linear-ensure-dependency' for a in result['actions']))
        self.assertTrue(next(d for d in result['dependencies'] if d['issue_id'] == ISSUE)['dependencies_satisfied'])
        self.request['outcomes'][0]['blocked_by'][0]['state_type'] = 'canceled'
        self.assertFalse(next(d for d in self.plan()['dependencies'] if d['issue_id'] == ISSUE)['dependencies_satisfied'])

    def test_unverified_or_unmerged_pr_cannot_claim_integration(self):
        self.pr['canonical_verified'] = False
        self.assertEqual([a['kind'] for a in self.plan()['actions']], ['linear-link-pr'])
        self.pr.update(merged=False, canonical_verified=True)
        del self.pr['merge_commit']
        self.assertEqual([a['kind'] for a in self.plan()['actions']], ['linear-link-pr'])

    def test_invalid_identities_sources_and_extra_fields_fail_closed(self):
        original = copy.deepcopy(self.request)
        mutations = [lambda: self.request.update(credentials='forbidden'),
                     lambda: self.handoff.update(issue_id='UIF-123'),
                     lambda: self.pr.update(head='1' * 40),
                     lambda: self.pr.update(base='main'),
                     lambda: self.pr.update(url='https://github.com/other/repo/pull/201'),
                     lambda: self.request['outcomes'].append(copy.deepcopy(self.issue())),
                     lambda: self.request['outcomes'][0].update(team_id=SECOND)]
        for mutation in mutations:
            self.request = copy.deepcopy(original)
            self.handoff = self.request['changes'][0]['handoff']
            self.pr = self.request['changes'][0]['pull_request']
            mutation()
            with self.assertRaises((linear.LinearPlanError, contract.ContractError)):
                self.plan()

    def test_promotion_rejects_missing_constituents_and_wrong_tree_or_tag(self):
        self.request['promotion'] = self.promotion()
        original = copy.deepcopy(self.request['promotion'])
        for mutate in (lambda p: p.update(issue_ids=[SECOND]),
                       lambda p: p['pull_request'].update(tree='1' * 40),
                       lambda p: p['tag'].update(commit='1' * 40)):
            self.request['promotion'] = copy.deepcopy(original)
            mutate(self.request['promotion'])
            with self.assertRaises(linear.LinearPlanError):
                self.plan()

    def test_determinism_detachment_and_no_evidence_reads(self):
        before = copy.deepcopy(self.request)
        with patch.object(Path, 'open', side_effect=AssertionError('No receipt reads')):
            first = self.plan()
            self.assertEqual(first, self.plan())
        self.assertEqual(before, self.request)
        first['actions'][0]['issue_id'] = SECOND
        self.assertEqual(before, self.request)

    def test_cli_uses_real_contract_and_rejects_duplicate_json(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'request.json'
            path.write_text(json.dumps(self.request))
            args = ['--request', str(path), '--policy', str(ROOT / 'config/delivery-release-policy.json')]
            output = io.StringIO()
            with redirect_stdout(output):
                self.assertEqual(linear.main(args), 0)
            self.assertEqual(json.loads(output.getvalue()), self.plan())
            path.write_text('{"version":1,"version":1}')
            output = io.StringIO()
            with redirect_stdout(output):
                self.assertEqual(linear.main(args), 2)
            self.assertEqual(json.loads(output.getvalue()), {'status': 'invalid-linear-request'})


if __name__ == '__main__':
    unittest.main()
