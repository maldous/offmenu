"""Offline merge-only transaction proof; never operational merge evidence."""
import copy
import json
import unittest

import test_conditional_validation as fixtures
from offmenu.delivery.integration import Controller, DeliveryError, fingerprint


class MergeOnlyIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.fixture = fixtures.ConditionalValidationTests()
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.root = self.fixture.root
        self.binding = copy.deepcopy(self.fixture.binding)
        self.binding.update(issue_id=None, integration_mode='merge-only')
        self.snapshot = copy.deepcopy(self.fixture.snapshot)

    def controller(self, name='merge-only', binding=None):
        return Controller(self.root/name, self.binding if binding is None else binding, self.root)

    def case_controller(self, name):
        # Independent negative cases; the dedicated contention/predecessor tests
        # below intentionally share one root instead.
        return Controller(self.root/name/'transaction', self.binding, self.root/name)

    def merged(self):
        snapshot = copy.deepcopy(self.snapshot)
        snapshot['github'].update(merged=True, state='closed', merge_commit_sha='8'*40)
        snapshot['merge_commit'] = dict(sha='8'*40,
            parents=[self.binding['base'], self.binding['head']], tree=self.binding['tree'])
        snapshot['develop_contains_merge'] = True
        return snapshot

    def test_terminal_flow_requires_readback_and_never_completes_linear(self):
        c = self.controller()
        original_adoption = copy.deepcopy(self.snapshot['policy_adoption'])
        intent = c.run(self.snapshot)
        self.assertEqual(intent['action']['kind'], 'merge-pr')
        self.assertFalse(intent['action']['bypass_protection'])
        self.assertEqual(c.record_api_outcome('merge', 'succeeded')['merge_effect'], 'unknown')
        self.assertEqual(c.run(self.snapshot)['status'], 'reconciliation-required')
        result = self.controller().run(self.merged())
        self.assertEqual(result['status'], 'merge-verified')
        self.assertEqual(result['reason'], 'merge-only-no-issue')
        self.assertIsNone(result['action'])
        self.assertNotIn('linear_effect', result)
        self.assertEqual(self.snapshot['policy_adoption'], original_adoption)
        with self.assertRaises(DeliveryError):
            c.record_api_outcome('linear', 'succeeded')

    def test_null_issue_requires_explicit_v4_mode(self):
        for version in (1, 2, 4):
            b = copy.deepcopy(self.fixture.binding)
            b.update(version=version, issue_id=None)
            with self.subTest(version=version), self.assertRaises(DeliveryError):
                self.controller('invalid-'+str(version), b)
        for change in ({'issue_id': self.fixture.binding['issue_id']},
                       {'integration_mode': 'issue-bound'}, {'integration_mode': 'unknown'}):
            b = dict(self.binding, **change)
            with self.subTest(change=change), self.assertRaises(DeliveryError):
                self.controller('invalid-mode', b)
        b = dict(self.binding)
        b.pop('issue_id')
        with self.assertRaises(DeliveryError):
            self.controller('absent-issue', b)

    def test_binding_rejects_all_optional_issue_acceptance_fields(self):
        for extra in ({'project_id': 'ce60c1ab-a732-4a71-8471-14c9dc393886'},
                      {'full_issue_acceptance_sha256': '9'*64},
                      {'project_id': 'ce60c1ab-a732-4a71-8471-14c9dc393886',
                       'full_issue_acceptance_sha256': '9'*64}):
            with self.subTest(extra=extra), self.assertRaises(DeliveryError):
                self.controller('invalid-acceptance', dict(self.binding, **extra))

    def test_linear_snapshot_fields_are_refused_before_merge_and_after_readback(self):
        for key in ('linear', 'full_issue_acceptance'):
            c = self.case_controller('metadata-'+key)
            snapshot = dict(self.snapshot, **{key: None})
            self.assertEqual(c.run(snapshot)['reason'], 'merge-only-linear-metadata')
            c.run(self.snapshot)
            snapshot = dict(self.merged(), **{key: {'state': 'Done'}})
            result = c.run(snapshot)
            self.assertEqual(result['status'], 'quarantined')
            self.assertIsNone(result['action'])

    def test_wrong_tree_or_parents_do_not_certify_merge(self):
        for key, value in (('tree', '0'*40), ('parents', ['0'*40, self.binding['head']])):
            c = self.controller('wrong-'+key)
            c.run(self.snapshot)
            snapshot = self.merged()
            snapshot['merge_commit'][key] = value
            result = c.run(snapshot)
            self.assertEqual(result['status'], 'repair-required')
            self.assertEqual(result['action']['kind'], 'prepare-corrective-candidate')

    def test_no_issue_keeps_owner_source_adoption_and_cancellation_guards(self):
        for key, value in (('publisher_owner', 'another-owner'), ('policy_adoption', {}),
                           ('source_tree', '0'*40), ('source_clean', False),
                           ('cancel_requested', True)):
            snapshot = copy.deepcopy(self.snapshot)
            snapshot[key] = value
            with self.subTest(key=key):
                result = self.case_controller('guard-'+key).run(snapshot)
                self.assertIsNone(result['action'])
                self.assertNotEqual(result['status'], 'merge-intent')
        snapshot = copy.deepcopy(self.snapshot)
        snapshot['github']['base'] = '0'*40
        self.assertEqual(self.case_controller('stale-base').run(snapshot)['status'], 'stale-candidate')

    def test_stored_linear_effect_or_done_state_is_not_resumed(self):
        for change in ({'status': 'accepted'}, {'linear_effect': 'pending'},
                       {'action': {'kind': 'update-linear', 'issue_id': None}}):
            c = self.case_controller('stored-'+str(len(list(self.root.iterdir()))))
            c.run(self.snapshot)
            path = c.directory/'state.json'
            state = json.loads(path.read_text())
            state.update(change)
            path.write_text(json.dumps(state))
            result = c.run(self.snapshot)
            self.assertEqual(result['reason'], 'merge-only-linear-metadata')
            self.assertIsNone(result['action'])

    def test_shared_lock_and_uncertain_predecessor_cannot_be_bypassed(self):
        import fcntl
        import os
        previous = self.controller('previous')
        previous.run(self.snapshot)
        active = self.root/'active-owner.json'
        before = active.read_bytes()
        successor = self.controller('successor', dict(self.binding, head='9'*40))
        with self.assertRaises(DeliveryError):
            successor.run(self.snapshot)
        self.assertEqual(active.read_bytes(), before)
        fd = os.open(self.root/'repository-owner.lock', os.O_RDWR)
        try:
            fcntl.flock(fd, fcntl.LOCK_EX|fcntl.LOCK_NB)
            with self.assertRaises(BlockingIOError):
                previous.run(self.snapshot)
        finally:
            os.close(fd)

    def test_verified_issue_bound_predecessor_preserves_immutable_records(self):
        original = Controller(self.root/'old', self.fixture.binding, self.root)
        original.run(self.fixture.snapshot)
        snapshot = self.merged()
        result = original.run(snapshot)
        self.assertEqual(result['merge_effect'], 'verified')
        old_files = {p: p.read_bytes() for p in (
            self.root/'repository-claim.json', self.root/'old'/'binding.json',
            self.root/'old'/'repository-claim.json', self.root/'old'/'state.json')}
        self.controller().run(self.snapshot)
        for p, before in old_files.items():
            self.assertEqual(p.read_bytes(), before)
        active = json.loads((self.root/'active-owner.json').read_text())
        self.assertEqual(active['binding_sha256'], fingerprint(self.binding))

    def test_issue_bound_fingerprint_and_pending_restart_remain_unchanged(self):
        # Captured using the accepted 349dbf9 Controller and unchanged fixture.
        expected = '3aab3c20f8b8912c152e7bd13698ad02440a9b3c3238a9014b652c56448946d2'
        self.assertEqual(fingerprint(self.fixture.binding), expected)
        c = Controller(self.root/'old', self.fixture.binding, self.root)
        c.run(self.fixture.snapshot)
        original_binding = (self.root/'old'/'binding.json').read_bytes()
        original_claim = (self.root/'old'/'repository-claim.json').read_bytes()
        restarted = Controller(self.root/'old', self.fixture.binding, self.root, _existing_only=True)
        self.assertEqual(restarted.run(self.fixture.snapshot)['status'], 'reconciliation-required')
        self.assertEqual((self.root/'old'/'binding.json').read_bytes(), original_binding)
        self.assertEqual((self.root/'old'/'repository-claim.json').read_bytes(), original_claim)


if __name__ == '__main__':
    unittest.main()
