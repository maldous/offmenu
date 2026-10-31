"""Real CurrentWork and finite component APIs; synthetic owner/external adapters."""
import asyncio
import copy
from dataclasses import replace
import json
from pathlib import Path
import subprocess
import unittest
from unittest.mock import Mock, patch

import native_harness_runtime as runtime
import native_harness_contract as contract
import test_stokowski_current_dispatch as current_fixture
import test_native_graph_harness as graph_fixture
import test_release_qualification as release_fixture
from offmenu.delivery.engine import DeliveryError, Engine, writer

ROOT = Path(__file__).resolve().parents[2]
TEAM = '53f584e7-70a1-4b1e-b982-b815210e47d4'
REAL_CHECK_OUTPUT = subprocess.check_output


class RuntimeBoundaryTests(unittest.TestCase):
    def setUp(self):
        self.fixture = current_fixture.CurrentDispatchTests(methodName='runTest')
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.issue, self.task_runtime, _, _ = self.fixture.bound_gate(221)
        self.current = self.fixture.current
        self.policy = contract.load_release_policy(ROOT / 'config/delivery-release-policy.json')
        ref = dict(path='.delivery/original.json', sha256='a'*64)
        self.handoff = dict(version=1, kind='delivery-handoff-v1',
            issue_id=self.issue.id, project_id=self.current.route['project_id'],
            owner=self.current.config['owner'], origin=dict(kind='reviewed-source-v1', evidence=ref),
            source=dict(repository='maldous/offmenu', branch='feature/test-current',
                        base='b'*40, head='c'*40, tree='f'*40, target='develop',
                        policy_sha256=contract.fingerprint(self.policy)), outputs=[], evidence=[ref])
        issue = dict(id=self.issue.id, identifier=self.issue.identifier,
                     project_id=self.current.route['project_id'], team_id=TEAM,
                     state_type='started', blocked_by=[], pr_urls=[], milestone_ids=[])
        pr = dict(url='https://github.com/maldous/offmenu/pull/201', head='c'*40,
                  tree='f'*40, base='develop', merged=False, canonical_verified=False)
        linear = dict(version=1, projects=[dict(id=issue['project_id'], name='OffMenu', team_id=TEAM)],
                      outcomes=[issue], changes=[dict(handoff=self.handoff,pull_request=pr)],
                      dependencies=[],effects=[])
        self.packet = dict(policy=self.policy,handoff=self.handoff,candidate=None,
                           linear=linear,release=None)
        action = runtime.plan_delivery(linear,self.policy)['actions'][0]
        self.effect = dict(operation_id=action['action_id'],status='ready',child_tree_gone=True)
        self.authorize = Mock(return_value=True)  # installation-owned custody check, not JSON
        self.step = Mock(side_effect=self.transaction)
        self.adapters = runtime.OwnerAdapters(self.authorize, lambda b:copy.deepcopy(self.packet),
            lambda b:None, lambda *args:None, lambda b:copy.deepcopy(self.effect), self.step)
        self.bind()

    def bind(self, phase='linear'):
        self.binding = runtime.OwnerBinding(self.issue.id,self.current.route['project_id'],
            self.current.config['owner'],contract.fingerprint(self.packet),
            self.effect['operation_id'],phase,
            contract.fingerprint(self.current.gate_binding(self.issue,observation=True)))

    def transaction(self, binding, context):
        # Fake external adapter consumes its EXISTING operation before returning.
        self.effect.update(status='verified')
        return copy.deepcopy(self.effect)

    def consume(self, binding=None, adapters=None):
        return asyncio.run(runtime.consume_boundary(self.current,self.issue,
            binding=binding or self.binding,adapters=adapters or self.adapters))

    def test_missing_binding_leaves_actual_current_state_unchanged(self):
        before=self.current.state_path.read_bytes()
        result=asyncio.run(runtime.consume_boundary(self.current,self.issue))
        self.assertEqual(result['status'],'legacy')
        self.assertEqual(self.current.state_path.read_bytes(),before)
        self.authorize.assert_not_called()

    def test_real_current_boundary_plans_one_action_and_reopen_only_observes(self):
        before=self.current.state_path.read_bytes()
        first=self.consume()
        self.assertEqual(first['status'],'advanced',first)
        self.assertEqual(self.step.call_args.args[1]['action']['kind'],'linear-link-pr')
        second=self.consume()
        self.assertEqual(second['effect']['status'],'verified')
        self.assertEqual(self.step.call_count,1)
        self.assertFalse(second['refill_eligible'])
        self.assertFalse(second['accepted_delivery'])
        self.assertEqual(self.current.state_path.read_bytes(),before)

    def test_unknown_and_pending_existing_operations_never_step(self):
        for status in ('unknown','pending','denied','failed','verified'):
            self.effect['status']=status
            result=self.consume()
            self.assertEqual(result['effect']['operation_id'],self.binding.operation_id)
            self.assertEqual(result['status'],'observed')
        self.step.assert_not_called()

    def test_unstopped_children_never_release_or_step(self):
        self.effect['child_tree_gone']=False
        result=self.consume()
        self.assertEqual(result['status'],'observed')
        self.assertFalse(result['refill_eligible'])
        self.step.assert_not_called()

    def test_lost_response_reconciles_same_operation_without_duplicate_effect(self):
        def lost(binding, context):
            self.effect.update(status='unknown')
            raise TimeoutError()
        self.step.side_effect=lost
        self.assertEqual(self.consume()['status'],'held')
        self.assertEqual(self.consume()['effect']['status'],'unknown')
        self.assertEqual(self.step.call_count,1)

    def test_original_native_receipt_gate_is_not_replaced_by_valid_handoff(self):
        path=self.task_runtime/'attempts'/self.issue.identifier/'receipt.json'
        value=json.loads(path.read_text());value['child_tree_gone']=False
        self.fixture.write(path,value)
        self.assertEqual(self.consume()['status'],'held')
        self.step.assert_not_called()

    def test_owner_authority_and_packet_drift_remain_held(self):
        self.authorize.side_effect=PermissionError()
        self.assertEqual(self.consume()['status'],'held')
        self.authorize.side_effect=None
        self.packet['handoff']['owner']='foreign-owner'
        self.assertEqual(self.consume()['status'],'held')
        self.step.assert_not_called()

    def test_false_authority_or_permission_loss_before_effect_is_held(self):
        self.authorize.return_value=False
        self.assertEqual(self.consume()['reason'],'owner_authority_missing')
        self.authorize.side_effect=[True,False]
        self.assertEqual(self.consume()['reason'],'owner_authority_missing')
        self.step.assert_not_called()

    def test_project_and_original_unit_rebinding_are_held(self):
        for binding in (replace(self.binding,project_id='11111111-1111-4111-8111-111111111111'),
                        replace(self.binding,unit_sha256='0'*64)):
            self.assertEqual(self.consume(binding)['status'],'held')
        self.step.assert_not_called()

    def test_json_cannot_select_callback_or_executable(self):
        self.packet['callback']='os.system'
        self.bind()
        self.assertEqual(self.consume()['status'],'held')
        self.step.assert_not_called()

    def test_dependency_and_metadata_effect_holds_are_consumed(self):
        self.packet['linear']['outcomes'][0]['blocked_by']=[dict(
            id='11111111-1111-4111-8111-111111111111',state_type='started')]
        self.bind()
        self.assertEqual(self.consume()['status'],'held')
        self.step.assert_not_called()

    def test_missing_actual_engine_blocks_publisher(self):
        self.bind('integration')
        self.assertEqual(self.consume()['status'],'held')
        self.step.assert_not_called()

    def publisher_fixture(self):
        import hashlib
        from stokowski_operations import bridge_arguments
        from symphony_capacity import digest
        def selected_git(args, **kw):
            if not Path(args[2]).is_relative_to(self.fixture.temp):
                return REAL_CHECK_OUTPUT(args, **kw)
            if (args[-2:] == ['rev-parse', 'HEAD'] and args[2] != str(self.fixture.source)):
                return getattr(self.fixture, 'task_head', 'b'*40) + '\n'
            return self.fixture.git_read(args, **kw)
        self.fixture.git.side_effect = selected_git
        graph=graph_fixture.NativeGraphTests(methodName='runTest');graph.setUp()
        self.addCleanup(graph.doCleanups)
        # Build the SAME source/output bytes for Engine and the original native
        # unit/Journal/reviewer readers; no unrelated accepted proofs are paired.
        graph.git('branch','-m','feature/test-current')
        (graph.root/'result.txt').unlink()
        target=graph.root/'tests/task222.py';target.parent.mkdir()
        target.write_text('independent immutable output\n')
        standard=json.loads((graph.root/'repository-standard.json').read_text())
        del standard['roots']['result.txt'];standard['roots']['tests']={}
        (graph.root/'repository-standard.json').write_text(json.dumps(standard))
        graph.git('add','.');graph.git('commit','-qm','Exact reviewed candidate')
        graph.task['base_revision']=graph.git('rev-parse','HEAD')
        graph.task['accepted_outputs']={'tests/task222.py':hashlib.sha256(target.read_bytes()).hexdigest()}
        self.fixture.task_head=graph.task['base_revision']
        issue, task_runtime, _, _, review, journal, old_key=self.fixture.review_fixture(222)
        handoff=graph.task['handoff']
        handoff.update(issue_id=issue.id,project_id=self.current.route['project_id'],
                       owner=self.current.config['owner'],
                       source=graph.source('feature/test-current'),outputs=graph.outputs())
        graph.task['owner']=handoff['owner']
        spec,_=journal.read(old_key)
        spec['head']=handoff['source']['head']
        key=journal.prepare(spec);_,state=journal.read(key)
        receipt=copy.deepcopy(review['validation_receipt'])
        receipt.update(job_id=state['logical_job_id'],command_sha256=hashlib.sha256(
            bridge_arguments(spec)['command'].encode()).hexdigest())
        state.update(status='succeeded',receipt_sha256=digest(receipt),
            accepted_output_sha256=spec['outputs'],acceptance_sha256=spec['acceptance_sha256'])
        journal.save(key,state,'exact-candidate-fixture')
        bindings=current_fixture.adapter.read_record(task_runtime/'validation-bindings.json')
        bindings['issues'][issue.identifier].update(operation_key=key,source_head=spec['head'])
        self.fixture.write(task_runtime/'validation-bindings.json',bindings)
        b=review['integration_binding'];b.update(head=spec['head'],tree=handoff['source']['tree'],
                                               validation_operation_key=key)
        snapshot=review['snapshot'];snapshot['source_tree']=b['tree']
        snapshot['review']['head']=b['head']
        evidence={k:v for k,v in snapshot['review'].items() if k!='evidence_sha256'}
        snapshot['review']['evidence_sha256']=digest(evidence)
        snapshot['validation'].update(head=b['head'],operation_key=key)
        review['validation_receipt']=receipt
        decision=review['decision'];decision['binding_sha256']=digest(b)
        decision['action']['expected_head_sha']=b['head']
        decision['qualification_sha256']=digest(dict(validation=snapshot['validation'],
            review=snapshot['review'],tree=b['tree'],policy=b['policy_sha256']))
        # This is still the actual original reader, not a fake verdict callback.
        self.assertEqual(self.current._check_unit_review(review),review['unit_binding'])
        self.issue=issue;self.packet['handoff']=handoff
        self.packet['linear']['outcomes'][0].update(id=issue.id,identifier=issue.identifier)
        change=self.packet['linear']['changes'][0];change['handoff']=handoff
        change['pull_request'].update(head=handoff['source']['head'],tree=handoff['source']['tree'])
        self.bind('integration')
        return graph,review

    def test_finite_publisher_boundary_consumes_same_engine_and_native_review(self):
        graph,review=self.publisher_fixture()
        with writer(graph.root) as state:
            engine=Engine(graph.root,state,graph.task)
            self.assertEqual(engine.run()['status'],'accepted')
            adapters=replace(self.adapters,engine=lambda b:engine,review=lambda *args:review)
            result=self.consume(adapters=adapters)
            self.assertEqual(result['status'],'advanced',result)
            self.assertEqual(result['action'],'integration')
            self.assertEqual(self.step.call_args.args[1]['review']['source_sha256'],
                             contract.fingerprint(self.packet['handoff']['source']))
            self.assertEqual((graph.root/'counter.txt').read_text(),'1')

    def test_unrelated_valid_native_review_cannot_cover_engine_candidate(self):
        graph,review=self.publisher_fixture()
        with writer(graph.root) as state:
            engine=Engine(graph.root,state,graph.task);engine.run()
            _,_,_,_,unrelated,_,_=self.fixture.review_fixture(223)
            # An accepted different unit is not this original native gate either.
            adapters=replace(self.adapters,engine=lambda b:engine,review=lambda *args:unrelated)
            self.assertEqual(self.consume(adapters=adapters)['status'],'held')
            self.step.assert_not_called()

    def mismatched_engine(self, change):
        import hashlib
        graph,review=self.publisher_fixture()
        handoff=self.packet['handoff']
        if change == 'head':
            graph.git('commit','--allow-empty','-qm','Different candidate head')
            graph.task['base_revision']=graph.git('rev-parse','HEAD')
            handoff['source']['head']=graph.task['base_revision']
            self.packet['linear']['changes'][0]['pull_request']['head']=graph.task['base_revision']
        else:
            path=graph.root/'tests/task222.py';path.write_text('different accepted output\n')
            sha=hashlib.sha256(path.read_bytes()).hexdigest()
            graph.task['accepted_outputs']['tests/task222.py']=sha
            handoff['outputs'][0]['sha256']=sha
        self.bind('integration')
        # The old SAME-unit review still passes its real original reader.
        self.assertEqual(self.current._check_unit_review(review),review['unit_binding'])
        with writer(graph.root) as state:
            engine=Engine(graph.root,state,graph.task);engine.run()
            adapters=replace(self.adapters,engine=lambda b:engine,review=lambda *args:review)
            result=self.consume(adapters=adapters)
            self.assertEqual(result['reason'],'review_candidate_coverage',result)
            self.step.assert_not_called()

    def test_valid_same_unit_review_cannot_cover_different_engine_head(self):
        self.mismatched_engine('head')

    def test_valid_same_unit_review_cannot_cover_different_engine_outputs(self):
        self.mismatched_engine('outputs')

    def test_review_head_tree_outputs_and_release_transition_need_exact_coverage(self):
        graph,review=self.publisher_fixture()
        # Original-reader qualification precedes the new cross-component check.
        # Prove this source/outputs comparison itself rejects every mismatch,
        # including a release candidate that moves to a different develop head.
        self.current._check_unit_review(review)
        handoff=self.packet['handoff']
        for key,value in [('head','1'*40),('base','2'*40),('tree','3'*40),
                          ('branch','feature/other')]:
            altered=copy.deepcopy(handoff);altered['source'][key]=value
            with self.subTest(key=key),self.assertRaises(runtime.RuntimeHold):
                runtime.review_coverage(review,altered,None)
        altered=copy.deepcopy(handoff);altered['outputs'][0]['sha256']='4'*64
        with self.assertRaises(runtime.RuntimeHold):runtime.review_coverage(review,altered,None)
        candidate=dict(source={**handoff['source'],'branch':'develop','head':'5'*40},
                       artifacts=handoff['outputs'])
        with self.assertRaises(runtime.RuntimeHold):runtime.review_coverage(review,handoff,candidate)
        with writer(graph.root) as state:
            engine=Engine(graph.root,state,graph.task);engine.run()
            for key,value in [('head','1'*40),('tree','2'*40),('outputs',{'other':'3'*64})]:
                wrong=copy.deepcopy(review);wrong['integration_binding'][key]=value
                adapters=replace(self.adapters,engine=lambda b:engine,review=lambda *args:wrong)
                self.assertEqual(self.consume(adapters=adapters)['status'],'held')
                self.step.assert_not_called()

    def test_original_unknown_validation_operation_never_becomes_new_job(self):
        self.handoff['operation']=dict(id='old-windmill-operation',backend='windmill',
            job_id='old-job',status='unknown',command_sha256='a'*64,runner_sha256='b'*64,
            policy_sha256='c'*64,receipt=self.handoff['origin']['evidence'])
        self.handoff['effect']=dict(operation_id='old-windmill-operation',status='unknown')
        self.bind()
        result=self.consume()
        self.assertEqual(result['status'],'held')
        self.assertEqual(self.handoff['operation']['job_id'],'old-job')
        self.step.assert_not_called()


class RuntimeEngineTests(unittest.TestCase):
    def test_actual_engine_receipts_reverify_without_command_replay(self):
        f=graph_fixture.NativeGraphTests(methodName='runTest');f.setUp()
        self.addCleanup(f.doCleanups)
        with writer(f.root) as state:
            engine=Engine(f.root,state,f.task)
            self.assertEqual(engine.run()['status'],'accepted')
            first=runtime.engine_acceptance(engine,f.task['handoff'],None)
            self.assertEqual(runtime.engine_acceptance(engine,f.task['handoff'],None),first)
            self.assertEqual((f.root/'counter.txt').read_text(),'1')
            (f.root/'result.txt').write_text('tampered')
            with self.assertRaises(DeliveryError):
                runtime.engine_acceptance(engine,f.task['handoff'],None)

    def test_actual_release_aggregation_retains_raw_receipt_and_full_profiles(self):
        f=release_fixture.ReleaseQualificationTests(methodName='runTest');f.setUp()
        self.addCleanup(f.doCleanups)
        import release_qualification as release
        results=[f.result(),f.result(1)]
        summary=f.aggregate(results)
        self.assertEqual(release.validate_qualification(summary,f.plan,results,
            f.policy,f.catalog,f.root)['status'],'qualified')
        (f.root/'receipt-0.json').write_text('{}')
        with self.assertRaises(contract.ContractError):
            release.validate_qualification(summary,f.plan,results,f.policy,f.catalog,f.root)
