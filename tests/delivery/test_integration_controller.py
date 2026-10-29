"""Finite integration crash/reconciliation tests with real graph checkpoints."""
import copy
import json
from pathlib import Path
import tempfile
import time
import unittest
from unittest.mock import patch

from offmenu.delivery.integration import Controller, DeliveryError


class IntegrationControllerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.binding = {'version':1,'repository':'maldous/offmenu','pr_number':145,
            'issue_id':'8daac134-01ab-4a02-a4d2-c0c417d0bd32','owner':'cloud-github-owner',
            'head':'a'*40,'base':'b'*40,'tree':'c'*40,'policy_sha256':'d'*64,
            'capacity_policy_sha256':'e'*64,'validation_operation_key':'f'*64,
            'outputs':{'tests/behavior.py':'1'*64}}
        self.directory = self.root/'selected'
        self.controller = Controller(self.directory,self.binding)
        self.snapshot = {'observed_at':time.time(),'publisher_owner':'cloud-github-owner',
            'github':{'repository':'maldous/offmenu','number':145,'merged':False,
                'state':'open','draft':False,'head':'a'*40,'base':'b'*40,
                'head_branch':'feature/langgraph-delivery-standardization','base_branch':'develop','mergeable':True},
            'policy_sha256':'d'*64,'capacity_policy_sha256':'e'*64,
            'validation':{'operation_key':'f'*64,'status':'succeeded','head':'a'*40,'base':'b'*40,
                'capacity_policy_sha256':'e'*64,'outputs':self.binding['outputs'],
                'child_tree_gone':True,'reconcile_required':False},
            'review':{'head':'a'*40,'base':'b'*40,'independent':True,'evidence_id':'review-proof-1',
                'verdict':'accept','findings':[]},'unresolved_findings':[],
            'source_tree':'c'*40,'source_clean':True,'publication_triggers_actions':False,
            'automatic_integration_enabled':True}

    def step(self,snapshot=None):
        return Controller(self.directory,self.binding).run(snapshot or self.snapshot)

    def merged(self,done=False):
        value = copy.deepcopy(self.snapshot)
        value['github'].update(merged=True,state='closed',merge_commit_sha='2'*40)
        value['merge_commit'] = {'sha':'2'*40,'parents':['b'*40,'a'*40],'tree':'c'*40}
        value['develop_contains_merge'] = True
        value['linear'] = {'id':self.binding['issue_id'],
            'project_id':'ce60c1ab-a732-4a71-8471-14c9dc393886','state':'Done' if done else 'In Review'}
        return value

    def test_ready_action_is_exact_and_intent_is_persisted_before_return(self):
        result = self.step()
        self.assertEqual(result['status'],'merge-intent')
        self.assertEqual(result['action']['expected_head_sha'],'a'*40)
        self.assertEqual(result['action']['expected_base_sha'],'b'*40)
        self.assertFalse(result['action']['bypass_protection'])
        self.assertEqual(json.loads((self.directory/'state.json').read_text()),result)
        self.assertTrue((self.directory/'graph.sqlite').is_file())

    def test_restart_does_not_repeat_unknown_merge(self):
        self.step()
        self.controller.record_api_outcome('merge','uncertain')
        result = self.step()
        self.assertEqual(result['status'],'reconciliation-required')
        self.assertIsNone(result['action'])
        self.assertTrue(result['qualification_sha256'])

    def test_api_success_needs_canonical_merge_and_ref_readback(self):
        self.step()
        self.controller.record_api_outcome('merge','succeeded')
        self.assertNotEqual(self.controller.status()['status'],'accepted')
        result = self.step(self.merged())
        self.assertEqual(result['status'],'linear-intent')
        self.assertEqual(result['action']['kind'],'update-linear')

    def test_metadata_timeout_reconciles_done_without_another_merge(self):
        self.step()
        self.step(self.merged())
        self.controller.record_api_outcome('linear','uncertain')
        result = self.step(self.merged(done=True))
        self.assertEqual(result['status'],'accepted')
        self.assertIsNone(result['action'])

    def test_metadata_retry_is_bounded_and_only_after_fresh_readback_delay(self):
        self.step();self.step(self.merged())
        self.controller.record_api_outcome('linear','uncertain')
        result = self.step(self.merged())
        self.assertEqual(result['status'],'linear-reconciliation-required')
        with patch('offmenu.delivery.integration.time.time',return_value=time.time()+11):
            later = self.merged();later['observed_at'] = time.time()
            result = self.step(later)
        self.assertEqual(result['action']['kind'],'update-linear')
        self.assertEqual(result['linear_retry_count'],1)

    def test_exhausted_metadata_budget_stays_stopped(self):
        self.step();self.step(self.merged())
        current = self.controller.status()
        current.update(status='linear-unknown',linear_retry_count=2,linear_requested_at=time.time()-20)
        from offmenu.delivery.engine import atomic
        atomic(self.directory/'state.json',current)
        self.assertEqual(self.step(self.merged())['status'],'metadata-repair-required')
        self.assertEqual(self.step(self.merged())['status'],'metadata-repair-required')
        self.assertEqual(self.step(self.merged(done=True))['status'],'accepted')

    def test_refused_metadata_is_not_retried_as_ordinary_failure(self):
        self.step();self.step(self.merged())
        self.controller.record_api_outcome('linear','refused')
        self.assertEqual(self.step(self.merged())['status'],'authority-refused')

    def test_old_review_cannot_authorize_new_head(self):
        self.snapshot['review']['head'] = '9'*40
        self.assertEqual(self.step()['status'],'awaiting-independent-review')

    def test_stale_base_needs_new_validation(self):
        self.snapshot['github']['base'] = '9'*40
        self.assertEqual(self.step()['status'],'stale-candidate')

    def test_changed_output_or_unreconciled_children_cannot_authorize_merge(self):
        for field,value in [('outputs',{'tests/behavior.py':'0'*64}),('child_tree_gone',False)]:
            with self.subTest(field=field):
                observed = copy.deepcopy(self.snapshot)
                observed['validation'][field] = value
                self.assertEqual(self.step(observed)['status'],'awaiting-validation')

    def test_policy_drift_is_quarantined(self):
        self.snapshot['policy_sha256'] = '0'*64
        self.assertEqual(self.step()['status'],'quarantined')

    def test_workflow_trigger_effect_is_not_silently_enabled(self):
        self.snapshot['publication_triggers_actions'] = True
        self.assertEqual(self.step()['status'],'quarantined')

    def test_findings_route_to_repair_without_a_merge_action(self):
        self.snapshot['review']['findings'] = ['real finding']
        result = self.step()
        self.assertEqual(result['status'],'repair-required')
        self.assertEqual(result['action']['kind'],'repair')

    def test_review_repair_can_be_superseded_without_deadlocking_repository(self):
        self.snapshot['review']['findings'] = ['real finding']
        self.step()
        other = dict(self.binding,head='9'*40)
        controller = Controller(self.root/'corrected',other)
        observation = copy.deepcopy(self.snapshot)
        observation['github']['head'] = '9'*40
        result = controller.run(observation)
        self.assertNotEqual(result['status'],'merge-intent')

    def test_possible_merge_blocks_a_different_integration_owner(self):
        self.step()
        other = Controller(self.root/'other',dict(self.binding,head='9'*40))
        with self.assertRaisesRegex(DeliveryError,'must reconcile'):
            other.run(self.snapshot)

    def test_cancel_before_merge_emits_no_mutation(self):
        self.snapshot['cancel_requested'] = True
        result = self.step()
        self.assertEqual(result['status'],'cancelled')
        self.assertIsNone(result['action'])

    def test_cancel_after_merge_intent_requires_outcome_reconciliation(self):
        self.step()
        self.snapshot['cancel_requested'] = True
        self.assertEqual(self.step()['status'],'reconciliation-required')

    def test_repeated_cancel_cannot_erase_uncertain_merge_claim(self):
        self.step()
        self.snapshot['cancel_requested'] = True
        self.assertEqual(self.step()['status'],'reconciliation-required')
        self.assertEqual(self.step()['status'],'reconciliation-required')
        other = Controller(self.root/'other',dict(self.binding,head='9'*40))
        with self.assertRaises(DeliveryError):
            other.run(self.snapshot)

    def test_disabled_controller_does_not_emit_mutation(self):
        self.snapshot['automatic_integration_enabled'] = False
        self.assertEqual(self.step()['status'],'disabled')

    def test_refusal_cannot_be_retried_without_new_authority(self):
        self.step()
        self.controller.record_api_outcome('merge','refused')
        self.assertEqual(self.step()['status'],'authority-refused')
        self.controller.reauthorize_known_refusal('3'*64)
        self.assertEqual(self.step()['status'],'merge-intent')
        self.controller.record_api_outcome('merge','refused')
        with self.assertRaises(DeliveryError):
            self.controller.reauthorize_known_refusal('3'*64)

    def test_wrong_merge_tree_routes_corrective_candidate_without_history_rewrite(self):
        self.step()
        observed = self.merged();observed['merge_commit']['tree'] = '9'*40
        result = self.step(observed)
        self.assertEqual(result['status'],'repair-required')
        self.assertEqual(result['action']['kind'],'prepare-corrective-candidate')
        self.assertFalse(result['action']['force'])

    def test_unadmitted_external_merge_is_not_certified(self):
        result = self.step(self.merged(done=True))
        self.assertEqual(result['status'],'repair-required')

    def test_nonfinite_observation_time_is_rejected(self):
        self.snapshot['observed_at'] = float('nan')
        self.assertEqual(self.step()['status'],'awaiting-fresh-observation')


if __name__ == '__main__':
    unittest.main()
