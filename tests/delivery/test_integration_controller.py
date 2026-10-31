"""Finite integration crash/reconciliation tests with real graph checkpoints."""
import copy
import hashlib
import json
from pathlib import Path
import tempfile
import time
import unittest
from unittest.mock import patch

from offmenu.delivery.integration import Controller, DeliveryError, fingerprint


class IntegrationControllerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.binding = {'version':1,'repository':'maldous/offmenu','pr_number':145,
            'issue_id':'8daac134-01ab-4a02-a4d2-c0c417d0bd32','owner':'cloud-github-owner',
            'head_branch':'feature/langgraph-delivery-standardization','head':'a'*40,'base':'b'*40,'tree':'c'*40,'policy_sha256':'d'*64,
            'capacity_policy_sha256':'e'*64,'validation_operation_key':'f'*64,
            'outputs':{'tests/behavior.py':'1'*64}}
        self.acceptance = dict(version=1, issue_id=self.binding['issue_id'],
            project_id='ce60c1ab-a732-4a71-8471-14c9dc393886', owner=self.binding['owner'],
            decision='accepted', scope='full-issue', evidence_id='owner-full-issue-evidence')
        self.binding.update(project_id=self.acceptance['project_id'],
                            full_issue_acceptance_sha256=fingerprint(self.acceptance))
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
        value['full_issue_acceptance'] = copy.deepcopy(self.acceptance)
        value['linear'] = {'id':self.binding['issue_id'],
            'project_id':'ce60c1ab-a732-4a71-8471-14c9dc393886','state':'Done' if done else 'In Review'}
        return value

    def test_partial_or_changed_acceptance_never_completes_issue(self):
        self.step()
        for change in ({'scope':'unit'}, {'issue_id':'00000000-0000-4000-8000-000000000123'},
                       {'project_id':'ffb6c7d9-4eff-46eb-a805-99f0cc2edfa0'},
                       {'owner':'foreign-owner'}, {'decision':'pending'}, {'evidence_id':'other'}):
            observed = self.merged()
            observed['full_issue_acceptance'].update(change)
            with self.subTest(change=change):
                result = self.step(observed)
                self.assertEqual(result['reason'],'full-issue-acceptance-unqualified')
                self.assertIsNone(result['action'])
        observed = self.merged()
        observed.pop('full_issue_acceptance')
        self.assertEqual(self.step(observed)['reason'],'full-issue-acceptance-unqualified')

    def test_legacy_binding_never_infers_issue_completion(self):
        legacy = dict(self.binding)
        legacy.pop('project_id')
        legacy.pop('full_issue_acceptance_sha256')
        self.controller = Controller(self.root/'legacy',legacy)
        self.directory = self.root/'legacy'
        self.binding = legacy
        self.step()
        result = self.step(self.merged())
        self.assertEqual(result['reason'],'full-issue-project-and-acceptance-unbound')
        self.assertIsNone(result['action'])

    def test_bound_uif_project_and_foreign_readback(self):
        self.acceptance['project_id']='ffb6c7d9-4eff-46eb-a805-99f0cc2edfa0'
        self.binding.update(project_id=self.acceptance['project_id'],
                            full_issue_acceptance_sha256=fingerprint(self.acceptance))
        self.directory = self.root/'uif'
        self.controller = Controller(self.directory,self.binding)
        self.step()
        observed=self.merged()
        self.assertEqual(self.step(observed)['reason'],'awaiting-linear-readback')
        observed['linear']['project_id']=self.acceptance['project_id']
        result=self.step(observed)
        self.assertEqual(result['status'],'linear-intent')
        self.assertEqual(result['action']['issue_id'], self.binding['issue_id'])

    def test_legitimate_successor_preserves_published_claim_hash(self):
        # Valid legacy published ownership includes durable prepared state.
        # A claim whose historical state is missing is tested as a hold below.
        (self.directory/'state.json').write_text(json.dumps(dict(status='prepared',action=None)))
        legacy = self.root/'repository-claim.json'
        legacy.write_text(json.dumps(dict(binding_sha256=self.controller.key,
            directory=str(self.directory), owner=self.binding['owner']))+'\n')
        self.snapshot['automatic_integration_enabled'] = False
        self.step()
        before = hashlib.sha256(legacy.read_bytes()).hexdigest()
        other = Controller(self.root/'successor',dict(self.binding,head='9'*40))
        other.run(self.snapshot)
        self.assertEqual(hashlib.sha256(legacy.read_bytes()).hexdigest(),before)

    def test_successor_preserves_controller_evidence_and_shared_bytes(self):
        self.snapshot['automatic_integration_enabled'] = False
        self.step()
        paths = (self.root/'repository-claim.json',self.directory/'repository-claim.json')
        frozen = {p:p.read_bytes() for p in paths}
        other = Controller(self.root/'successor',dict(self.binding,head='9'*40))
        other.run(self.snapshot)
        evidence = other.directory/'repository-claim.json'
        raw = evidence.read_bytes()
        other.run(self.snapshot)
        self.assertEqual(evidence.read_bytes(),raw)
        self.assertEqual(json.loads((self.root/'active-owner.json').read_text()),json.loads(raw))
        for path, original in frozen.items():
            self.assertEqual(path.read_bytes(),original)

    def test_legacy_bootstrap_retains_pending_and_unknown_predecessor_holds(self):
        self.step()
        active = self.root/'active-owner.json'
        other = Controller(self.root/'successor',dict(self.binding,head='9'*40))
        from offmenu.delivery.engine import atomic
        for effect in ('pending','unknown'):
            for legacy in (False,True):
                if legacy and active.exists():
                    active.unlink()
                state = self.controller.status()
                atomic(self.directory/'state.json',dict(state,merge_effect=effect))
                with self.subTest(effect=effect,legacy=legacy), self.assertRaisesRegex(DeliveryError,'must reconcile'):
                    other.run(self.snapshot)
                self.assertFalse((other.directory/'repository-claim.json').exists())

    def test_global_lock_excludes_second_controller(self):
        other = Controller(self.root/'successor',dict(self.binding,head='9'*40))
        with self.controller.ownership():
            with self.assertRaises(BlockingIOError):
                with other.ownership():
                    self.fail('second repository owner acquired lock')
        self.assertFalse((other.directory/'repository-claim.json').exists())

    def assert_same_binding_successor_blocked(self,effect):
        self.assertEqual(self.step()['status'],'merge-intent')
        if effect == 'unknown':
            self.controller.record_api_outcome('merge','uncertain')
        self.assertEqual(self.controller.status()['merge_effect'],effect)
        other = Controller(self.root/'same-binding',self.binding)
        paths = (self.root/'active-owner.json',self.root/'repository-claim.json',
                 self.directory/'repository-claim.json',self.directory/'state.json',
                 self.directory/'graph.sqlite')
        frozen = {p:p.read_bytes() for p in paths}
        with self.assertRaisesRegex(DeliveryError,'must reconcile'):
            result = other.run(self.snapshot)
            self.fail('same-binding successor returned '+result['status'])
        for path, original in frozen.items():
            self.assertEqual(path.read_bytes(),original)
        for name in ('repository-claim.json','state.json','graph.sqlite'):
            self.assertFalse((other.directory/name).exists())
        # The original directory can still recover its own immutable operation.
        result = self.step()
        self.assertEqual(result['status'],'reconciliation-required')
        self.assertIsNone(result['action'])
        self.assertEqual(result['merge_effect'],effect)

    def test_same_binding_other_directory_cannot_replace_pending_owner(self):
        self.assert_same_binding_successor_blocked('pending')

    def test_same_binding_other_directory_cannot_replace_unknown_owner(self):
        self.assert_same_binding_successor_blocked('unknown')

    def test_invalid_active_pointer_and_snapshot_fail_closed(self):
        self.snapshot['automatic_integration_enabled'] = False
        self.step()
        active = self.root/'active-owner.json'
        evidence = self.directory/'repository-claim.json'
        legacy = self.root/'repository-claim.json'
        old = legacy.read_bytes()
        for path in (active,evidence):
            raw = path.read_bytes()
            for value in (b'{}',b'null',b'{',json.dumps(dict(binding_sha256='0'*64,
                    directory=str(self.directory),owner=self.binding['owner'])).encode()):
                path.write_bytes(value)
                with self.subTest(path=path.name,value=value), self.assertRaises(DeliveryError):
                    self.step()
                self.assertEqual(legacy.read_bytes(),old)
            path.unlink()
            path.symlink_to(legacy)
            with self.assertRaises(DeliveryError):
                self.step()
            path.unlink()
            path.symlink_to(self.root/'absent')
            with self.assertRaises(DeliveryError):
                self.step()
            path.unlink()
            path.write_bytes(raw)

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
        current.update(status='linear-unknown',linear_effect='unknown',linear_retry_count=2,linear_requested_at=time.time()-20)
        from offmenu.delivery.engine import atomic
        atomic(self.directory/'state.json',current)
        self.assertEqual(self.step(self.merged())['status'],'metadata-repair-required')
        self.assertEqual(self.step(self.merged())['status'],'metadata-repair-required')
        self.assertEqual(self.step(self.merged(done=True))['status'],'accepted')

    def test_refused_metadata_is_not_retried_as_ordinary_failure(self):
        self.step();self.step(self.merged())
        self.controller.record_api_outcome('linear','refused')
        self.assertEqual(self.step(self.merged())['status'],'authority-refused')

    def test_new_product_bugfix_has_exact_separate_branch_binding(self):
        branch = 'bugfix/scanner-facts-consumer'
        binding = dict(self.binding,head_branch=branch)
        controller = Controller(self.root/'product',binding)
        snapshot = copy.deepcopy(self.snapshot);snapshot['github']['head_branch'] = branch
        self.assertEqual(controller.run(snapshot)['action']['expected_head_branch'],branch)
        snapshot['github']['head_branch'] = 'bugfix/another'
        # An outstanding action must reconcile, never be retargeted at another branch.
        self.assertEqual(controller.run(snapshot)['status'],'reconciliation-required')

    def test_other_branch_at_same_head_is_not_an_admitted_candidate(self):
        self.snapshot['github']['head_branch'] = 'bugfix/other'
        self.assertEqual(self.step()['status'],'stale-candidate')

    def test_stale_observation_cannot_erase_uncertain_merge_or_release_owner(self):
        self.step();self.controller.record_api_outcome('merge','uncertain')
        stale = copy.deepcopy(self.snapshot);stale['observed_at'] -= 120
        self.assertEqual(self.step(stale)['status'],'awaiting-fresh-observation')
        self.assertEqual(self.step()['status'],'reconciliation-required')
        other = Controller(self.root/'other',dict(self.binding,head='9'*40))
        with self.assertRaises(DeliveryError):other.run(self.snapshot)

    def test_missing_linear_readback_cannot_clear_refusal_or_exhaustion(self):
        self.step();self.step(self.merged())
        self.controller.record_api_outcome('linear','refused')
        missing = self.merged();missing.pop('linear')
        self.assertEqual(self.step(missing)['status'],'merge-verified')
        self.assertEqual(self.step(self.merged())['status'],'authority-refused')
        current = self.controller.status();current.update(linear_effect='unknown',linear_exhausted=True)
        from offmenu.delivery.engine import atomic
        atomic(self.directory/'state.json',current)
        self.step(missing)
        self.assertEqual(self.step(self.merged())['status'],'metadata-repair-required')

    def test_persistent_cancel_allows_completed_merge_reconciliation(self):
        self.step()
        observed=self.merged(done=True);observed['cancel_requested']=True
        self.assertEqual(self.step(observed)['status'],'accepted')

    def test_cancelled_completed_merge_does_not_emit_new_metadata_mutation(self):
        self.step()
        observed=self.merged();observed['cancel_requested']=True
        result=self.step(observed)
        self.assertEqual(result['status'],'merge-verified');self.assertIsNone(result['action'])
        self.assertEqual(result['merge_effect'],'verified')

    def test_stale_observation_during_api_call_does_not_erase_matching_intent(self):
        self.step()
        stale=copy.deepcopy(self.snapshot);stale['observed_at']-=120
        self.step(stale)
        self.assertEqual(self.controller.record_api_outcome('merge','uncertain')['merge_effect'],'unknown')

    def test_known_preflight_nonexecution_releases_intent_for_new_candidate(self):
        self.step()
        state=self.controller.record_api_outcome('merge','not-issued')
        self.assertEqual(state['merge_effect'],'not-issued')
        other=Controller(self.root/'new-base',dict(self.binding,base='9'*40))
        snapshot=copy.deepcopy(self.snapshot);snapshot['github']['base']='9'*40
        self.assertEqual(other.run(snapshot)['status'],'awaiting-validation')

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

    def test_verified_bad_merge_allows_corrective_candidate_without_rewrite(self):
        self.step()
        observed = self.merged();observed['merge_commit']['tree'] = '9'*40
        result = self.step(observed)
        self.assertTrue(result['canonical_effect_verified'])
        other = Controller(self.root/'correction',dict(self.binding,head='9'*40))
        corrected = copy.deepcopy(self.snapshot);corrected['github']['head'] = '9'*40
        self.assertEqual(other.run(corrected)['status'],'awaiting-validation')

    def test_missing_develop_ancestry_is_unknown_not_permission_to_repair(self):
        self.step()
        observed = self.merged();observed['develop_contains_merge'] = False
        self.assertEqual(self.step(observed)['status'],'merged-unverified')
        other = Controller(self.root/'other',dict(self.binding,head='9'*40))
        with self.assertRaises(DeliveryError):
            other.run(self.snapshot)

    def test_unadmitted_external_merge_is_not_certified(self):
        result = self.step(self.merged(done=True))
        self.assertEqual(result['status'],'repair-required')

    def test_historical_current_resumes_exact_binding_without_rebinding(self):
        from offmenu.delivery.integration import publisher_directory
        legacy = self.root/'current';legacy.mkdir()
        path = legacy/'binding.json';path.write_text(json.dumps(self.binding))
        original = path.read_bytes()
        self.assertEqual(publisher_directory(self.root,self.binding),legacy)
        successor = dict(self.binding,head='8'*40)
        self.assertEqual(publisher_directory(self.root,successor).name,'transaction-'+fingerprint(successor))
        self.assertEqual(path.read_bytes(),original)
        path.unlink();path.symlink_to(self.directory/'binding.json')
        with self.assertRaisesRegex(DeliveryError,'Symlink historical'):
            publisher_directory(self.root,self.binding)

    def test_status_claim_durably_prepares_before_candidate_rotation(self):
        # Exercise the ownership/status entry used before protected adapter auth.
        from offmenu.delivery.engine import atomic
        state_path = self.directory/'state.json'
        def persist(path, value):
            if path.name in ('repository-claim.json','active-owner.json'):
                self.assertTrue(state_path.is_file(),'prepared must precede claim publication')
            return atomic(path,value)
        with patch('offmenu.delivery.integration.atomic',side_effect=persist):
            with self.controller.ownership():
                self.assertEqual(self.controller.status()['status'],'prepared')
        self.assertEqual(json.loads(state_path.read_text())['status'],'prepared')
        original = state_path.read_bytes()
        other = Controller(self.root/'after-preflight',dict(self.binding,head='8'*40),self.root)
        with other.ownership():
            self.assertEqual(other.status()['status'],'prepared')
        self.assertEqual(state_path.read_bytes(),original)

    def test_missing_claimed_historical_state_cannot_become_prepared(self):
        with self.controller.ownership():
            pass
        state_path = self.directory/'state.json'
        state_path.unlink(missing_ok=True)
        other = Controller(self.root/'missing-history',dict(self.binding,head='8'*40),self.root)
        with self.assertRaises(DeliveryError):
            with other.ownership():
                self.fail('missing historical state acquired')
        with self.assertRaises(DeliveryError):
            with self.controller.ownership():
                self.fail('missing own claimed state silently initialized')
        self.assertFalse(state_path.exists())

    def test_fresh_transaction_directory_retains_legacy_and_blocks_replay(self):
        from offmenu.delivery.integration import publisher_directory
        first_dir = publisher_directory(self.root,self.binding)
        self.assertEqual(first_dir.name,'transaction-'+fingerprint(self.binding))
        self.snapshot['automatic_integration_enabled'] = False
        first = Controller(first_dir,self.binding,self.root)
        first.run(self.snapshot)
        original = (first_dir/'binding.json').read_bytes()
        next_binding = dict(self.binding, head='8'*40)
        second_dir = publisher_directory(self.root,next_binding)
        self.assertNotEqual(first_dir,second_dir)
        Controller(second_dir,next_binding,self.root).run(self.snapshot)
        self.assertEqual((first_dir/'binding.json').read_bytes(),original)
        with self.assertRaisesRegex(DeliveryError,'Superseded'):
            first.run(self.snapshot)

    def test_publisher_observe_never_initializes_claim_or_transaction(self):
        from offmenu.delivery.integration import publisher_observe,publisher_directory,_publisher_transaction_request
        config = dict(binding=self.binding,logicalOwner=self.binding['owner'])
        before = {str(p):p.read_bytes() for p in self.root.rglob('*') if p.is_file()}
        view = publisher_observe(config,self.root)
        self.assertEqual(view['state']['status'],'prepared')
        self.assertFalse(view['claim_current']);self.assertTrue(view['claim_available'])
        self.assertFalse(publisher_directory(self.root,self.binding).exists())
        self.assertEqual({str(p):p.read_bytes() for p in self.root.rglob('*') if p.is_file()},before)
        for request in ({'op':'observe','extra':True},{'op':'observe-consume'}):
            with self.assertRaises(DeliveryError):
                _publisher_transaction_request(config,request,self.root)
        self.assertFalse(publisher_directory(self.root,self.binding).exists())

    def test_publisher_observe_preserves_unknown_owner_and_missing_history_holds(self):
        from offmenu.delivery.integration import publisher_observe,publisher_directory
        from offmenu.delivery.engine import atomic
        directory = publisher_directory(self.root,self.binding)
        first = Controller(directory,self.binding,self.root)
        first.run(self.snapshot)
        state = first.status();state['merge_effect'] = 'unknown';atomic(directory/'state.json',state)
        config = dict(binding=self.binding,logicalOwner=self.binding['owner'])
        before = {str(p):p.read_bytes() for p in self.root.rglob('*') if p.is_file()}
        view = publisher_observe(config,self.root)
        self.assertTrue(view['claim_current']);self.assertEqual(view['state']['merge_effect'],'unknown')
        changed = dict(self.binding,head='8'*40)
        other = publisher_observe(dict(binding=changed,logicalOwner=changed['owner']),self.root)
        self.assertFalse(other['claim_available']);self.assertFalse(other['claim_current'])
        self.assertEqual({str(p):p.read_bytes() for p in self.root.rglob('*') if p.is_file()},before)
        (directory/'state.json').unlink()
        with self.assertRaises(DeliveryError):
            publisher_observe(config,self.root)
        self.assertFalse((directory/'state.json').exists())

    def test_readonly_reconciliation_cannot_reacquire_or_write_claims(self):
        self.snapshot['automatic_integration_enabled'] = False
        self.step()
        self.controller.require_current_claim = True
        claim = self.root/'active-owner.json'
        original = claim.read_bytes()
        from offmenu.delivery.engine import atomic
        def persist(path,value):
            self.assertNotIn(path.name,('active-owner.json','repository-claim.json'))
            return atomic(path,value)
        with patch('offmenu.delivery.integration.atomic',side_effect=persist):
            self.controller.run(self.snapshot)
        self.assertEqual(claim.read_bytes(),original)
        other = Controller(self.root/'readonly-successor',dict(self.binding,head='8'*40),self.root)
        other.run(self.snapshot)
        successor = claim.read_bytes()
        with self.assertRaisesRegex(DeliveryError,'Read-only reconciliation'):
            self.controller.run(self.snapshot)
        self.assertEqual(claim.read_bytes(),successor)

    def test_native_rpc_admission_drift_and_missing_checkpoint_never_initialize(self):
        from offmenu.delivery.integration import _publisher_transaction_request,publisher_directory
        config = dict(binding=self.binding,logicalOwner=self.binding['owner'],snapshot={'native_runtime':{'unit_sha256':'1'*64}})
        for pins in ({'native_binding_sha256':'0'*64,'native_runtime_sha256':fingerprint(config['snapshot']['native_runtime'])},
                     {'native_binding_sha256':fingerprint(self.binding),'native_runtime_sha256':'0'*64},
                     {'native_binding_sha256':fingerprint(self.binding)}):
            with self.assertRaisesRegex(DeliveryError,'admission changed'):
                _publisher_transaction_request(config,dict(op='observe',**pins),self.root)
        directory = publisher_directory(self.root,self.binding)
        self.assertFalse(directory.exists())
        with self.assertRaises(DeliveryError):
            Controller(directory,self.binding,self.root,_existing_only=True)
        self.assertFalse(directory.exists())
        first = Controller(directory,self.binding,self.root)
        with first.ownership():
            pass  # Prepared claim has no graph/effect checkpoint yet.
        before = {str(p):p.read_bytes() for p in self.root.rglob('*') if p.is_file()}
        with self.assertRaisesRegex(DeliveryError,'checkpoint'):
            _publisher_transaction_request(config,dict(op='observe-step',observation=self.snapshot),self.root)
        self.assertEqual({str(p):p.read_bytes() for p in self.root.rglob('*') if p.is_file()},before)

    def test_nonfinite_observation_time_is_rejected(self):
        self.snapshot['observed_at'] = float('nan')
        self.assertEqual(self.step()['status'],'awaiting-fresh-observation')


class NativeReleaseTests(unittest.TestCase):
    def setUp(self):
        from offmenu.delivery.integration import ReleaseController
        from native_harness_contract import load_release_policy
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        policy = load_release_policy(Path('config/delivery-release-policy.json'))
        self.candidate = dict(version=1, kind='release-candidate-v1', source=dict(
            repository='maldous/offmenu',branch='develop',base='b'*40,head='a'*40,
            tree='c'*40,target='main',policy_sha256=fingerprint(policy)),
            required_profiles=['release-behavior'],artifacts=[dict(path='dist/result.json',sha256='1'*64)])
        import release_qualification as release
        catalog = release.read_json(release.ROOT/'config/release-validation-profile.json')
        artifact = self.root/'dist/result.json'
        artifact.parent.mkdir();artifact.write_text('release artifact\n')
        self.candidate['artifacts'][0]['sha256'] = release.file_sha(artifact)
        self.candidate['required_profiles'] = ['release']
        plan = release.plan(self.candidate,policy,catalog,'4'*64,'5'*64)
        results = []
        for index, check in enumerate(plan['checks']):
            job = release.bridge_request(plan,check['key'],policy,catalog)['job_id']
            receipt = dict(job_id=job,status='succeeded',exit_code=0,child_tree_gone=True,
                           mode='write',timeout_seconds=check['timeout_seconds'],reconcile_required=False,
                           command_sha256=check['command_sha256'],runner_sha256='4'*64,
                           capacity_policy_sha256='5'*64,resources=check['resources'])
            # Original runner request digest uses historical default JSON spaces.
            spec = {key:receipt[key] for key in ('command_sha256','mode','timeout_seconds',
                    'runner_sha256','capacity_policy_sha256','resources')}
            receipt['request_sha256'] = hashlib.sha256(json.dumps(spec,sort_keys=True).encode()).hexdigest()
            receipt_path = self.root/('receipt-%d.json' % index)
            receipt_path.write_text(json.dumps(receipt))
            ref = dict(path=receipt_path.name,sha256=release.file_sha(receipt_path))
            handoff = dict(version=1,kind='delivery-handoff-v1',
                issue_id='8daac134-01ab-4a02-a4d2-c0c417d0bd32',
                project_id='ce60c1ab-a732-4a71-8471-14c9dc393886',owner='release-owner',
                origin=dict(kind='completed-native-validation-v1',evidence=ref),source=self.candidate['source'],
                outputs=self.candidate['artifacts'],evidence=[ref],operation=dict(id='release-check-%d' % index,
                backend='windmill',job_id=job,status='succeeded',command_sha256=check['command_sha256'],
                runner_sha256='4'*64,policy_sha256='5'*64,receipt=ref))
            results.append(dict(check=check['key'],plan_sha256=fingerprint(plan),coverage='complete',handoff=handoff))
        qualification = dict(summary=release.aggregate(plan,results,policy,catalog,self.root),
                             plan=plan,results=results,catalog=catalog,evidence_root=str(self.root))
        self.binding = dict(version=3,kind='release-promotion-v1',repository='maldous/offmenu',
            owner='release-owner',issue_id='8daac134-01ab-4a02-a4d2-c0c417d0bd32',
            project_id='ce60c1ab-a732-4a71-8471-14c9dc393886',candidate=self.candidate,policy=policy,qualification=qualification,
            pr_number=248,main_base='9'*40,tag='release/2026.11.01')
        self.binding['authority'] = dict(version=1,kind='release-promotion-authority-v1',owner='release-owner',
            issue_id=self.binding['issue_id'],project_id=self.binding['project_id'],
            candidate_sha256=fingerprint(self.candidate),qualification_sha256=fingerprint(qualification),
            pr_number=248,main_base='9'*40,tag='release/2026.11.01')
        self.controller = ReleaseController(self.root/'release',self.binding,self.root)
        self.snapshot = dict(observed_at=time.time(),publisher_owner='release-owner',
            qualification_sha256=fingerprint(qualification),publication_triggers_actions=False,
            unresolved_findings=[],tag=None,
            review=dict(verdict='accept',independent=True,head='a'*40,base='9'*40,
                        evidence_id='exact-release-review',findings=[]),
            github=dict(repository='maldous/offmenu',number=248,head='a'*40,base='9'*40,
                        head_branch='release/candidate-'+fingerprint(self.candidate),base_branch='main',merged=False,state='open',draft=False,mergeable=True))

    def merged(self):
        value = copy.deepcopy(self.snapshot)
        value['github'].update(merged=True,merge_commit_sha='2'*40)
        value.update(merge_commit=dict(sha='2'*40,tree='c'*40,parents=['9'*40,'a'*40]),main_contains_merge=True)
        return value

    def test_promotion_and_tag_unknown_reconcile_same_effect(self):
        action = self.controller.run(self.snapshot)['action']
        self.assertEqual(action['kind'],'promote-release')
        self.assertTrue(self.controller.consume_release_intent(action))
        with self.assertRaises(DeliveryError):
            self.controller.consume_release_intent(action)
        self.assertIsNone(self.controller.run(self.snapshot)['action'])
        tag = self.controller.run(self.merged())['action']
        self.assertEqual(tag['kind'],'create-release-tag')
        self.controller.consume_release_intent(tag)
        self.assertEqual(self.controller.run(self.merged())['status'],'tag-reconciliation-required')
        observed = self.merged()
        observed['tag'] = dict(ref='refs/tags/release/2026.11.01',object=dict(type='commit',sha='2'*40))
        self.assertEqual(self.controller.run(observed)['status'],'release-verified')
        self.assertIsNone(self.controller.run(self.snapshot)['action'])

    def test_frozen_identity_review_normal_protection_and_tag_conflicts(self):
        from offmenu.delivery.integration import ReleaseController
        changed = copy.deepcopy(self.binding)
        changed['candidate']['source']['head'] = '3'*40
        with self.assertRaisesRegex(DeliveryError,'authority'):
            ReleaseController(self.root/'changed',changed,self.root)
        self.snapshot['github']['head'] = '3'*40
        self.assertEqual(self.controller.run(self.snapshot)['status'],'stale-candidate')
        self.snapshot['github']['head'] = 'a'*40
        self.snapshot['review']['independent'] = False
        self.assertEqual(self.controller.run(self.snapshot)['status'],'release-held')
        self.snapshot['review']['independent'] = True
        action = self.controller.run(self.snapshot)['action']
        self.controller.consume_release_intent(action)
        bad = self.merged();bad['merge_commit']['parents'].reverse()
        self.assertEqual(self.controller.run(bad)['status'],'release-readback-mismatch')
        bad = self.merged();bad['tag'] = dict(ref='refs/tags/release/2026.11.01',object=dict(type='commit',sha='0'*40))
        self.assertEqual(self.controller.run(bad)['status'],'immutable-tag-conflict')
        self.assertIsNone(self.controller.status()['action'])

    def test_publisher_reaggregates_and_rejects_missing_or_changed_evidence(self):
        from offmenu.delivery.integration import ReleaseController
        from native_harness_contract import ContractError
        changed = copy.deepcopy(self.binding)
        changed['qualification']['results'].pop()
        changed['authority']['qualification_sha256'] = fingerprint(changed['qualification'])
        with self.assertRaises(ContractError):
            ReleaseController(self.root/'incomplete',changed,self.root)
        (self.root/'dist/result.json').write_text('changed output')
        with self.assertRaises(ContractError):
            ReleaseController(self.root/'changed-output',self.binding,self.root)

    def test_fixed_release_rpc_rejects_changed_admission_and_linear_effects(self):
        from offmenu.delivery.integration import _publisher_request
        config = dict(version=2,binding=self.binding,logicalOwner=self.binding['owner'],snapshot=self.snapshot)
        action = _publisher_request(self.controller,config,dict(op='step',observation=self.snapshot))['action']
        self.assertEqual(action['kind'],'promote-release')
        changed = copy.deepcopy(self.snapshot);changed['review']['evidence_id'] = 'other'
        with self.assertRaisesRegex(DeliveryError,'qualified observation'):
            _publisher_request(self.controller,config,dict(op='step',observation=changed))
        with self.assertRaisesRegex(DeliveryError,'Unsupported release'):
            _publisher_request(self.controller,config,dict(op='outcome',kind='linear',outcome='succeeded'))
        result = _publisher_request(self.controller,config,dict(op='consume',intent=action))
        self.assertTrue(result['authorized'])
        with self.assertRaises(DeliveryError):
            _publisher_request(self.controller,config,dict(op='consume',intent=action))

    def test_unconsumed_tag_intent_survives_repeated_observation_and_consumes_once(self):
        action = self.controller.run(self.snapshot)['action']
        self.controller.consume_release_intent(action)
        tag = self.controller.run(self.merged())['action']
        self.assertEqual(self.controller.run(self.merged())['action'],tag)
        # A transient readback failure cannot erase an unconsumed durable effect.
        stale = self.merged();stale['observed_at'] = 0
        self.controller.run(stale)
        self.assertEqual(self.controller.run(self.merged())['action'],tag)
        self.controller.consume_release_intent(tag)
        with self.assertRaises(DeliveryError):
            self.controller.consume_release_intent(tag)
        self.assertIsNone(self.controller.run(self.merged())['action'])

    def test_pending_release_blocks_another_candidate(self):
        self.controller.run(self.snapshot)
        from offmenu.delivery.integration import ReleaseController
        changed = copy.deepcopy(self.binding)
        changed['tag'] = 'release/next';changed['authority']['tag'] = changed['tag']
        other = ReleaseController(self.root/'next',changed,self.root)
        with self.assertRaisesRegex(DeliveryError,'must reconcile'):
            other.run(self.snapshot)


if __name__ == '__main__':
    unittest.main()
