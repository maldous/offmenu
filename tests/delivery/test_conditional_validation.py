"""Synthetic conditional-policy fixtures, never operational validation receipts."""
import copy
import json
from pathlib import Path
import tempfile
import time
import unittest

from offmenu.delivery.integration import Controller, DeliveryError, fingerprint

ROOT = Path(__file__).resolve().parents[2]


class ConditionalValidationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.policy = json.loads((ROOT/'tools/delivery/integration-policy-v2-candidate.json').read_text())
        self.binding = dict(version=4, repository='maldous/offmenu', pr_number=217,
            issue_id='8daac134-01ab-4a02-a4d2-c0c417d0bd32', owner='fixture-owner',
            head_branch='bugfix/fixture-cloud', head='a'*40, base='b'*40, tree='c'*40,
            policy_sha256=fingerprint(self.policy), capacity_policy_sha256='d'*64,
            validation_operation_key='e'*64, outputs={'src/offmenu/example.py':'f'*64})
        b = self.binding
        paths = ['src/offmenu/example.py', 'tests/test_example.py']
        self.adoption = dict(kind='integration-policy-adoption-v1', decision='adopted',
            owner=b['owner'], policy_sha256=b['policy_sha256'], policy_source_head='9'*40,
            independent_review_evidence_id='synthetic-policy-review',
            previous_policy_sha256='1'*64, verification=dict(kind='prior-policy',
                policy_sha256='1'*64, validation_receipt_sha256='2'*64))
        self.scope = dict(kind='foo-independence-review-v1', classification='foo-independent',
            repository=b['repository'], head=b['head'], base=b['base'], tree=b['tree'],
            source_paths=paths, independent=True, reviewer='fixture-scope-reviewer',
            provider='fixture-provider', requested_model='fixture-request', resolution_status='unknown',
            resolved_model=None, verdict='accept', findings=[], evidence_id='synthetic-scope',
            rationale='Synthetic pure source change; affected behavior has no Foo dependency.')
        self.receipt = dict(operation_key=b['validation_operation_key'], status='succeeded',
            head=b['head'], base=b['base'], tree=b['tree'], branch=b['head_branch'],
            repository=b['repository'], source_paths=paths, outputs=b['outputs'],
            policy_sha256=b['policy_sha256'], capacity_policy_sha256=b['capacity_policy_sha256'],
            route='independent-cloud', child_tree_gone=True, reconcile_required=False,
            validator_revision=b['base'], independent=True, executor_actor='fixture-validator',
            evidence_id='synthetic-validation', environment_sha256='3'*64, dependencies_sha256='4'*64,
            checks=[dict(id='behavior', argv=['python','-m','unittest'], required=True,
                         status='succeeded', exit_code=0, skipped=False, log_sha256='5'*64)])
        self.binding['validation_contract'] = dict(version=1, route='independent-cloud',
            implementation_actors=['fixture-author', 'fixture-provenance-owner'], source_paths=paths,
            scope_review_sha256=fingerprint(self.scope), receipt_sha256=fingerprint(self.receipt),
            policy_adoption_sha256=fingerprint(self.adoption))
        c = self.binding['validation_contract']
        self.snapshot = dict(observed_at=time.time(), publisher_owner=b['owner'],
            policy_sha256=b['policy_sha256'], capacity_policy_sha256=b['capacity_policy_sha256'],
            github=dict(repository=b['repository'], number=b['pr_number'], merged=False, state='open',
                draft=False, head=b['head'], base=b['base'], head_branch=b['head_branch'],
                base_branch='develop', mergeable=True),
            integration_policy=self.policy, policy_adoption=self.adoption,
            accepted_policy_at_base_sha256=b['policy_sha256'], changed_paths=paths,
            implementation_actors=c['implementation_actors'], scope_review=self.scope, validation=self.receipt,
            review=dict(head=b['head'], base=b['base'], independent=True, reviewer='fixture-semantic-reviewer',
                provider='fixture-provider', requested_model='fixture-request', resolution_status='unknown',
                resolved_model=None, verdict='accept', findings=[], evidence_id='synthetic-review',
                scope_review_sha256=c['scope_review_sha256'], validation_receipt_sha256=c['receipt_sha256']),
            source_tree=b['tree'], source_clean=True, publication_triggers_actions=False,
            unresolved_findings=[], automatic_integration_enabled=True)

    def controller(self):
        return Controller(self.root/'candidate', self.binding)

    def assert_held(self, snapshot=None):
        decision = self.controller().decide(snapshot or self.snapshot)
        self.assertNotEqual(decision['status'], 'merge-intent')
        self.assertIsNone(decision['action'])

    def repin(self):
        c = self.binding['validation_contract']
        c.update(receipt_sha256=fingerprint(self.receipt), scope_review_sha256=fingerprint(self.scope),
                 policy_adoption_sha256=fingerprint(self.adoption))
        self.snapshot['review'].update(scope_review_sha256=c['scope_review_sha256'],
                                      validation_receipt_sha256=c['receipt_sha256'])

    def test_cloud_exact_source_with_separate_independent_reviewers(self):
        decision = self.controller().run(self.snapshot)
        self.assertEqual(decision['status'], 'merge-intent')
        self.assertEqual(decision['action']['expected_head_sha'], self.binding['head'])
        self.assertEqual(decision['action']['expected_base_sha'], self.binding['base'])
        self.assertFalse(decision['action']['bypass_protection'])
        restarted = self.controller().run(self.snapshot)
        self.assertEqual(restarted['status'], 'reconciliation-required')
        self.assertIsNone(restarted['action'])

    def test_selected_policy_still_requires_separate_adoption(self):
        active = ROOT/'tools/delivery/integration-policy.json'
        reviewed = ROOT/'tools/delivery/integration-policy-v2-candidate.json'
        self.assertEqual(active.read_bytes(), reviewed.read_bytes())
        self.assertEqual(json.loads(active.read_text())['version'], 2)
        self.snapshot.pop('policy_adoption')
        self.assert_held()

    def test_missing_owner_evidence_holds(self):
        for key in ('integration_policy', 'policy_adoption', 'accepted_policy_at_base_sha256',
                    'changed_paths', 'implementation_actors', 'scope_review', 'validation', 'review'):
            with self.subTest(key=key):
                s = copy.deepcopy(self.snapshot)
                s.pop(key)
                self.assert_held(s)

    def test_stale_or_forged_receipt_rejected_even_if_rehashed(self):
        for key, value in [('head','0'*40), ('base','0'*40), ('tree','0'*40),
                ('repository','other/repo'), ('branch','bugfix/other'), ('outputs',{}),
                ('source_paths',['src/omitted.py']), ('policy_sha256','0'*64),
                ('capacity_policy_sha256','0'*64), ('operation_key','0'*64),
                ('validator_revision','a'*40), ('independent',False),
                ('executor_actor','fixture-author'), ('executor_actor','fixture-provenance-owner'),
                ('environment_sha256',None), ('dependencies_sha256','unknown'), ('evidence_id',''),
                ('child_tree_gone',False), ('reconcile_required',True), ('route','root-transport')]:
            with self.subTest(key=key,value=value):
                self.setUp()
                self.receipt[key] = value
                self.repin()
                self.assert_held()

    def test_missing_changed_rename_or_deletion_path_rejected(self):
        self.snapshot['changed_paths'] = self.snapshot['changed_paths'] + ['src/offmenu/old.py']
        self.assert_held()

    def test_scope_must_be_independent_explicit_and_exact(self):
        for key,value in [('classification','unknown'), ('classification','foo-dependent'),
                         ('head','0'*40), ('base','0'*40), ('tree','0'*40),
                         ('source_paths',['docs/only.md']), ('independent',False),
                         ('reviewer','fixture-author'), ('reviewer','fixture-provenance-owner'),
                         ('rationale',''), ('verdict','pending'), ('findings',['open']),
                         ('provider',''), ('resolved_model','invented')]:
            with self.subTest(key=key,value=value):
                self.setUp()
                self.scope[key] = value
                self.repin()
                self.assert_held()

    def test_semantic_review_is_separately_independent_and_bound(self):
        for key,value in [('head','0'*40), ('base','0'*40), ('independent',False),
                         ('reviewer','fixture-author'), ('reviewer','fixture-provenance-owner'),
                         ('scope_review_sha256','0'*64), ('validation_receipt_sha256','0'*64),
                         ('provider',''), ('resolution_status','assumed')]:
            with self.subTest(key=key,value=value):
                s = copy.deepcopy(self.snapshot)
                s['review'][key] = value
                self.assert_held(s)

    def test_candidate_cannot_adopt_its_own_policy(self):
        for key,value in [('policy_source_head',self.binding['head']), ('owner','candidate'),
                         ('decision','proposed'), ('verification',None),
                         ('independent_review_evidence_id','')]:
            with self.subTest(key=key,value=value):
                self.setUp()
                self.adoption[key] = value
                self.repin()
                self.assert_held()

    def bootstrap_exception(self):
        self.adoption['verification'] = dict(kind='one-time-cloud-bootstrap',
            exception_id='offmenu-conditional-validation-20261111',
            policy_sha256=self.binding['policy_sha256'], policy_source_head=self.adoption['policy_source_head'],
            authorization_evidence_sha256='6'*64, review_evidence_sha256='7'*64,
            cloud_validation_receipt_sha256='8'*64)
        self.repin()

    def test_one_time_bootstrap_is_distinct_from_prior_policy_validation(self):
        self.bootstrap_exception()
        self.assertEqual(self.controller().decide(self.snapshot)['status'], 'merge-intent')
        self.assertNotIn('previous_policy_validation_sha256', self.adoption)
        self.assertNotIn('validation_receipt_sha256', self.adoption['verification'])

    def test_bootstrap_cannot_change_scope_or_omit_original_evidence(self):
        for key,value in [('exception_id','future-exception'), ('policy_sha256','0'*64),
                         ('policy_source_head','0'*40), ('authorization_evidence_sha256',None),
                         ('review_evidence_sha256',None), ('cloud_validation_receipt_sha256',None)]:
            with self.subTest(key=key,value=value):
                self.setUp()
                self.bootstrap_exception()
                self.adoption['verification'][key] = value
                self.repin()
                self.assert_held()

    def test_bootstrap_does_not_authorize_future_policy_bytes(self):
        self.bootstrap_exception()
        self.policy['standard'] = '2.5.1'
        pin = fingerprint(self.policy)
        self.binding['policy_sha256'] = pin
        self.adoption['policy_sha256'] = pin
        self.adoption['verification']['policy_sha256'] = pin
        self.snapshot.update(policy_sha256=pin, accepted_policy_at_base_sha256=pin)
        self.receipt['policy_sha256'] = pin
        self.repin()
        self.assert_held()

    def test_required_checks_cannot_be_missing_skipped_or_failed(self):
        for change in [dict(status='failed',exit_code=1), dict(exit_code=True),
                       dict(status='skipped',exit_code=None,skipped=True), dict(required=False),
                       dict(argv=[]), dict(log_sha256=''), dict(skipped=True)]:
            with self.subTest(change=change):
                self.setUp()
                self.receipt['checks'][0].update(change)
                self.repin()
                self.assert_held()
        self.setUp()
        self.receipt['checks'] = []
        self.repin()
        self.assert_held()

    def test_optional_skipped_coverage_does_not_replace_required_pass(self):
        self.receipt['checks'].append(dict(id='optional-executor', argv=['python','optional.py'],
            required=False, status='skipped', exit_code=None, skipped=True, log_sha256='6'*64))
        self.repin()
        self.assertEqual(self.controller().decide(self.snapshot)['status'], 'merge-intent')

    def test_windmill_remains_available_for_dependent_or_unknown_scope(self):
        self.binding['validation_contract'].update(route='windmill', scope_review_sha256=None)
        self.snapshot.pop('scope_review')
        self.receipt.update(route='windmill', windmill_job_id='synthetic-job')
        pin = fingerprint(self.receipt)
        self.binding['validation_contract']['receipt_sha256'] = pin
        self.snapshot['review']['validation_receipt_sha256'] = pin
        self.assertEqual(self.controller().decide(self.snapshot)['status'], 'merge-intent')

    def test_cloud_cannot_be_relabelled_as_legacy_validation(self):
        for version in (1,2):
            b = {k:v for k,v in self.binding.items() if k != 'validation_contract'}
            b['version'] = version
            if version == 2:
                b.update(pr_number=None, publication=dict(plan_sha256='1'*64,qualification_sha256='2'*64))
            c = Controller(self.root/f'legacy-{version}', b)
            self.assertFalse(c.validation_qualified(self.snapshot))
            legacy = copy.deepcopy(self.snapshot)
            legacy['validation'].pop('route')
            self.assertTrue(c.validation_qualified(legacy))

    def test_invalid_binding_paths_routes_and_actor_sets(self):
        for key,value in [('source_paths',['../escape']), ('source_paths',[]),
                         ('source_paths',['x','x']), ('route','skip'),
                         ('implementation_actors',[]), ('implementation_actors',['a','a']),
                         ('receipt_sha256',''), ('scope_review_sha256',None)]:
            with self.subTest(key=key,value=value):
                b = copy.deepcopy(self.binding)
                b['validation_contract'][key] = value
                with self.assertRaises(DeliveryError):
                    Controller(self.root/'bad', b)

    def test_existing_owner_source_and_trigger_gates_still_apply(self):
        for key,value in [('publisher_owner','stranger'), ('source_clean',False),
                         ('publication_triggers_actions',True), ('automatic_integration_enabled',False),
                         ('cancel_requested',True), ('source_tree','0'*40)]:
            with self.subTest(key=key):
                s = copy.deepcopy(self.snapshot)
                s[key] = value
                self.assert_held(s)

    def test_v4_still_requires_canonical_merge_readback(self):
        c = self.controller()
        c.run(self.snapshot)
        c.record_api_outcome('merge','succeeded')
        s = copy.deepcopy(self.snapshot)
        s['github'].update(merged=True, state='closed', merge_commit_sha='8'*40)
        s['develop_contains_merge'] = True
        s['merge_commit'] = dict(sha='8'*40, parents=[self.binding['base'],self.binding['head']], tree='0'*40)
        result = c.run(s)
        self.assertEqual(result['reason'], 'merged-tree-or-parent-readback-mismatch')
        self.assertEqual(result['action']['kind'], 'prepare-corrective-candidate')


if __name__ == '__main__':
    unittest.main()
