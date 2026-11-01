"""Real CurrentWork and finite component APIs; synthetic owner/external adapters."""
import asyncio
import copy
import importlib.util
from dataclasses import asdict, replace
import json
import os
import shutil
from contextlib import ExitStack
from pathlib import Path
import subprocess
import tempfile
import sys
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
        self.bind('integration')
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
            if (not Path(args[2]).is_relative_to(self.fixture.temp)
                    or Path(args[2]).name.startswith('offmenu-delivery-test-')):
                return REAL_CHECK_OUTPUT(args, **kw)
            if (args[-2:] == ['rev-parse', 'HEAD'] and args[2] != str(self.fixture.source)):
                return getattr(self.fixture, 'task_head', 'b'*40) + '\n'
            return self.fixture.git_read(args, **kw)
        self.fixture.git.side_effect = selected_git
        graph=graph_fixture.NativeGraphTests(methodName='runTest')
        with patch.object(tempfile, 'tempdir', str(self.current.root)
                          if getattr(self, 'graph_private', False) else tempfile.tempdir):
            graph.setUp()
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

    def factory_selection(self, graph=None, review=None, context=None):
        import hashlib
        import native_harness_contract, linear_delivery, release_qualification
        from offmenu.delivery import engine, status
        # Synthetic installation authority only; native admission/gate readers
        # remain real. No protected host files or live identity are changed.
        self.fixture.stack.enter_context(patch.object(self.current,'guard'))
        protected=current_fixture.adapter.PROTECTED_OWNER
        self.current.config_path=protected/'current.json'
        self.current.owner_custody=dict(schema='protected-current-owner-v1',runtime=str(self.current.runtime),
            config_sha256=self.current.config_sha,catalog_sha256='a'*64,
            source_root=str(current_fixture.adapter.SOURCE),python_sha256='b'*64)
        sources={'tools/delivery/native_harness_runtime.py':runtime.__file__,
                 'tools/delivery/native_harness_contract.py':native_harness_contract.__file__,
                 'contracts/schemas/delivery-handoff-v1.schema.json':
                     Path(native_harness_contract.__file__).resolve().parents[2]/
                     'contracts/schemas/delivery-handoff-v1.schema.json',
                 'tools/delivery/linear_delivery.py':linear_delivery.__file__,
                 'tools/delivery/release_qualification.py':release_qualification.__file__,
                 'src/offmenu/delivery/engine.py':engine.__file__,
                 'src/offmenu/delivery/status.py':status.__file__}
        try:
            import native_harness_linear
            sources['tools/delivery/native_harness_linear.py']=native_harness_linear.__file__
        except ImportError:
            pass  # Publisher/private-custody tests do not need a Linear route.
        self.current.config['source_sha256'].update({name:hashlib.sha256(Path(p).read_bytes()).hexdigest()
                                                     for name,p in sources.items()})
        def artifact(name,value):
            path=self.current.runtime/name;self.fixture.write(path,value)
            return dict(path=str(path),sha256=hashlib.sha256(path.read_bytes()).hexdigest())
        selection=dict(binding=asdict(self.binding),packet=artifact('native-packet.json',self.packet),
            context=context if context is not None else dict(engine_root=str(graph.root if graph else self.task_runtime),
                         engine_task=artifact('native-engine-task.json',graph.task if graph else {}),
                         unit_review=artifact('native-unit-review.json',review or {})))
        ref=artifact('native-selection.json',selection)
        self.current.config['native_harness_boundaries']={self.issue.identifier:ref}
        return selection

    def test_concrete_factory_reads_pinned_original_engine_and_review(self):
        self.graph_private=True
        graph,review=self.publisher_fixture()
        with writer(graph.root) as state:
            original=Engine(graph.root,state,graph.task);original.run()
        selection=self.factory_selection(graph,review)
        adapters=runtime.owner_adapters(self.current,self.issue,self.binding,selection)
        self.assertIs(adapters.authorize(self.current,self.issue,self.binding),True)
        self.assertEqual(adapters.load(self.binding),self.packet)
        with patch('offmenu.delivery.engine.atomic',side_effect=AssertionError('fresh Engine write')):
            loaded=adapters.engine(self.binding)
        runtime.engine_acceptance(loaded,self.packet['handoff'],None)
        self.assertEqual(adapters.review(self.current,self.issue,self.binding),review)
        self.assertEqual((graph.root/'counter.txt').read_text(),'1')
        (graph.root/'.delivery'/graph.task['id']/'accepted.json').unlink()
        with self.assertRaises(runtime.RuntimeHold):adapters.engine(self.binding)

    def test_factory_holds_missing_seal_source_or_changed_packet(self):
        selection=self.factory_selection()
        adapters=runtime.owner_adapters(self.current,self.issue,self.binding,selection)
        original_custody=copy.deepcopy(self.current.owner_custody)
        self.current.owner_custody=False
        with self.assertRaises(runtime.RuntimeHold):adapters.load(self.binding)
        self.current.owner_custody=original_custody
        Path(selection['packet']['path']).write_text('{}')
        with self.assertRaises(runtime.RuntimeHold):adapters.load(self.binding)
        self.current.config['source_sha256']['tools/delivery/native_harness_runtime.py']='0'*64
        with self.assertRaises(runtime.RuntimeHold):adapters.authorize(self.current,self.issue,self.binding)

    def check_factory_linear_client_and_journal(self, context=None):
        from stokowski.linear import LinearClient
        from unittest.mock import AsyncMock
        client=object.__new__(LinearClient)  # no token, HTTP client or network
        nodes=[];mutations=[]
        async def graphql(query,variables):
            if query.startswith('mutation'):
                disk=json.loads(self.current.state_path.read_text())
                record=disk['native_harness_linear'][self.binding.operation_id]
                self.assertEqual(record['status'],'pending')
                mutations.append(variables)
                nodes.append(dict(id='native-attachment',url=variables['input']['url']))
                return dict(attachmentCreate=dict(success=True))
            return dict(issue=dict(id=self.issue.id,project=dict(id=self.binding.project_id),
                attachments=dict(nodes=nodes,pageInfo=dict(hasNextPage=False,endCursor=None))))
        client._graphql=AsyncMock(side_effect=graphql)
        selection=self.factory_selection(context=context)
        adapters=runtime.owner_adapters(self.current,self.issue,self.binding,selection,linear_client=client)
        for call in (lambda:adapters.engine(self.binding),
                     lambda:adapters.review(self.current,self.issue,self.binding)):
            with self.assertRaisesRegex(runtime.RuntimeHold,'owner_phase'):
                call()
        self.assertEqual(self.consume(adapters=adapters)['status'],'advanced')
        self.assertEqual(self.consume(adapters=adapters)['effect']['status'],'verified')
        self.assertEqual(len(mutations),1)

    def test_concrete_factory_linear_uses_existing_client_and_current_journal(self):
        self.check_factory_linear_client_and_journal()

    def test_concrete_factory_empty_linear_context_preserves_intent_and_readback(self):
        self.check_factory_linear_client_and_journal(context={})

    def test_empty_context_never_admits_publisher_or_malformed_linear_context(self):
        for phase,context in (('integration',{}),('release',{}),('linear',[]),
                              ('linear',{'unit_review':{}})):
            with self.subTest(phase=phase,context=context):
                self.bind(phase)
                selection=self.factory_selection(context=context)
                adapters=runtime.owner_adapters(self.current,self.issue,self.binding,selection)
                result=self.consume(adapters=adapters)
                self.assertEqual(result['status'],'held',result)
                self.assertEqual(result['reason'],'owner_context_fields')
                self.step.assert_not_called()

    def test_empty_linear_context_still_requires_original_stopped_native_receipt(self):
        selection=self.factory_selection(context={})
        client=Mock()
        adapters=runtime.owner_adapters(self.current,self.issue,self.binding,selection,linear_client=client)
        path=self.task_runtime/'attempts'/self.issue.identifier/'receipt.json'
        receipt=json.loads(path.read_text());receipt['child_tree_gone']=False
        self.fixture.write(path,receipt)
        self.assertEqual(self.consume(adapters=adapters)['status'],'held')
        self.assertEqual(client.mock_calls,[])

    def test_real_missing_dependency_plan_executes_metadata_but_holds_source(self):
        from stokowski.linear import LinearClient
        from unittest.mock import AsyncMock
        blocker='11111111-1111-4111-8111-111111111111'
        outcome=copy.deepcopy(self.packet['linear']['outcomes'][0])
        outcome.update(id=blocker,identifier='UIF-999')
        self.packet['linear']['outcomes'].append(outcome)
        self.packet['linear']['dependencies']=[dict(issue_id=self.issue.id,blocked_by_id=blocker)]
        planned=runtime.plan_delivery(self.packet['linear'],self.policy)
        self.assertFalse(next(v for v in planned['dependencies'] if v['issue_id']==self.issue.id)
                         ['dependencies_satisfied'])
        action=next(v for v in planned['actions'] if v['kind']=='linear-ensure-dependency')
        self.effect['operation_id']=action['action_id'];self.bind()
        client=object.__new__(LinearClient);nodes=[];writes=[]
        async def graphql(query,variables):
            if query.startswith('mutation'):
                writes.append(variables)
                saved=json.loads(self.current.state_path.read_text())
                self.assertEqual(saved['native_harness_linear'][action['action_id']]['status'],'pending')
                self.assertEqual(variables['input'],dict(issueId=blocker,relatedIssueId=self.issue.id,type='blocks'))
                nodes.append(dict(id='native-relation',type='blocks',
                    issue=dict(id=blocker,state=dict(type='started')),relatedIssue=dict(id=self.issue.id)))
                return dict(issueRelationCreate=dict(success=True))
            return dict(issue=dict(id=self.issue.id,project=dict(id=self.binding.project_id),
                inverseRelations=dict(nodes=nodes,pageInfo=dict(hasNextPage=False,endCursor=None))))
        client._graphql=AsyncMock(side_effect=graphql)
        selection=self.factory_selection()
        adapters=runtime.owner_adapters(self.current,self.issue,self.binding,selection,linear_client=client)
        first=self.consume(adapters=adapters)
        self.assertEqual(first['effect']['status'],'verified',first)
        self.assertFalse(first['refill_eligible'])
        self.assertEqual(self.consume(adapters=adapters)['effect']['status'],'verified')
        self.assertEqual(len(writes),1)
        # Even after relation existence is verified, the blocking issue remains
        # started. Source phases keep their dependency hold, not a refill grant.
        self.bind('integration')
        self.assertEqual(self.consume()['reason'],'linear_dependencies_held')


class FixedPublisherTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.binding=runtime.OwnerBinding('11111111-1111-4111-8111-111111111111',
            '22222222-2222-4222-8222-222222222222','owner','a'*64,'b'*64,'integration','c'*64)
        self.packet={'handoff':{'source':{'head':'d'*40}}}

    async def invoke(self, suffix='', limit_output=False):
        import asyncio
        actual=asyncio.create_subprocess_exec
        processes=[]
        body=('import sys,json,hashlib; r=json.load(sys.stdin); '
              'v={k:v for k,v in r.items() if k != "mode"}; '
              'v.update(kind="native-publisher-response-v1",phase="integration",status="ready",'
              'request_sha256=hashlib.sha256(json.dumps(r,sort_keys=True,separators=(",",":"),ensure_ascii=True).encode()).hexdigest()); '
              + ('print("x"*70000)' if limit_output else 'print(json.dumps(v),flush=True)') + suffix)
        async def create(*argv,**kwargs):
            self.assertEqual(argv,runtime.PUBLISHER_ARGV)
            self.assertEqual(kwargs['env'],{'PATH':'/usr/bin:/bin','LANG':'C.UTF-8'})
            self.assertTrue(kwargs['start_new_session'])
            process=await actual(sys.executable,'-c',body,**kwargs)
            processes.append(process)
            return process
        with patch.object(runtime,'publisher_identity'),patch.object(asyncio,'create_subprocess_exec',side_effect=create):
            try:
                return await runtime.fixed_publisher_rpc(self.binding,self.packet,'observe')
            finally:
                self.assertEqual(len(processes),1)
                self.assertIsNotNone(processes[0].returncode)
                self.assertFalse(runtime.invocation_members(processes[0].pid))

    async def test_actual_fixed_child_is_reaped_and_bound_response_keeps_original_id(self):
        result=await self.invoke()
        self.assertEqual(result,dict(operation_id=self.binding.operation_id,status='ready',child_tree_gone=True))

    async def test_bounded_output_failure_reaps_actual_child(self):
        with self.assertRaises(runtime.RuntimeHold):await self.invoke(limit_output=True)

    async def test_cancellation_reaps_actual_fixed_child(self):
        import asyncio
        with self.assertRaises(TimeoutError):
            await asyncio.wait_for(self.invoke('; import time; time.sleep(10)'),.15)

    async def test_wrong_scope_response_and_self_reported_cleanup_are_rejected(self):
        request=runtime.publisher_request(self.binding,self.packet,'observe')
        value={k:v for k,v in request.items() if k!='mode'}
        value.update(kind='native-publisher-response-v1',phase='integration',status='ready',
                     request_sha256=contract.fingerprint(request))
        for changed in (dict(value,source_sha256='0'*64),dict(value,child_tree_gone=True)):
            with self.assertRaises(runtime.RuntimeHold):runtime.publisher_response(changed,request,'integration')

    async def test_ordinary_identity_holds_before_protected_config_read_or_spawn(self):
        with patch('os.getuid',return_value=1000),patch('os.geteuid',return_value=1000), \
             patch('stokowski_adapter.protected_owner_bytes',side_effect=AssertionError('protected retry')):
            with self.assertRaisesRegex(runtime.RuntimeHold,'publisher_owner_identity_required'):
                await runtime.fixed_publisher_rpc(self.binding,self.packet,'observe')


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


class SealedCurrentFactoryTests(unittest.TestCase):
    def setUp(self):
        import hashlib
        self.stack=ExitStack();self.addCleanup(self.stack.close)
        # The standalone component branch predates UIF124's accepted hook. A
        # bounded explicit SOURCE dependency may be selected for composition tests;
        # coherent checkouts use their actual adapter with no override.
        selected=Path(os.environ.get('OFFMENU_TEST_CURRENT_ADAPTER',
                                     str(ROOT/'tools/delivery/stokowski_adapter.py')))
        spec=importlib.util.spec_from_file_location('stokowski_adapter',selected)
        actual=importlib.util.module_from_spec(spec)
        self.stack.enter_context(patch.dict(sys.modules,stokowski_adapter=actual))
        spec.loader.exec_module(actual)
        self.stack.enter_context(patch.object(current_fixture,'adapter',actual))
        self.stack.enter_context(patch.object(current_fixture.prepare,'CurrentWork',actual.CurrentWork))
        self.f=RuntimeBoundaryTests(methodName='runTest');self.f.setUp()
        self.addCleanup(self.f.doCleanups)
        self.native=actual
        f=self.f;source=f.fixture.source
        import native_harness_contract,linear_delivery,release_qualification,native_harness_linear
        from offmenu.delivery import engine,status
        sources={'tools/delivery/native_harness_runtime.py':runtime.__file__,
            'tools/delivery/native_harness_contract.py':native_harness_contract.__file__,
            'contracts/schemas/delivery-handoff-v1.schema.json':
                Path(native_harness_contract.__file__).resolve().parents[2]/'contracts/schemas/delivery-handoff-v1.schema.json',
            'tools/delivery/linear_delivery.py':linear_delivery.__file__,
            'tools/delivery/release_qualification.py':release_qualification.__file__,
            'tools/delivery/native_harness_linear.py':native_harness_linear.__file__}
        for path in Path(engine.__file__).parent.glob('*.py'):
            sources['src/offmenu/delivery/'+path.name]=path
        try:
            import native_publisher_invocation
            sources['tools/delivery/native_publisher_invocation.py']=native_publisher_invocation.__file__
        except ImportError:
            pass  # The absent optional capability does not load its helper.
        sources['src/offmenu/__init__.py']=Path(engine.__file__).parent.parent/'__init__.py'
        for name,path in sources.items():
            target=source/name;target.parent.mkdir(parents=True,exist_ok=True)
            shutil.copyfile(path,target)
        installed=source/'tools/delivery/native_harness_runtime.py'
        module_spec=importlib.util.spec_from_file_location('native_harness_runtime',installed)
        module=importlib.util.module_from_spec(module_spec)
        self.stack.enter_context(patch.dict(sys.modules,native_harness_runtime=module))
        module_spec.loader.exec_module(module);self.module=module
        config=copy.deepcopy(f.current.config)
        config['source_sha256'].update({name:actual.file_sha(source/name) for name in sources})
        def artifact(name,value):
            path=f.current.runtime/name;f.fixture.write(path,value)
            return dict(path=str(path),sha256=actual.file_sha(path))
        context=dict(engine_root=str(f.task_runtime),engine_task=artifact('original-task.json',{}),
                     unit_review=artifact('original-review.json',{}))
        selection=dict(binding=asdict(f.binding),packet=artifact('native-packet.json',f.packet),context=context)
        config['native_harness_boundaries']={f.issue.identifier:artifact('native-selection.json',selection)}
        self.selection=selection
        self.selection_path=Path(config['native_harness_boundaries'][f.issue.identifier]['path'])
        self.protected=f.fixture.temp/'sealed-owner';self.protected.mkdir()
        (self.protected/'catalog.json').write_bytes(f.current.catalog.read_bytes())
        config['catalog']=str(self.protected/'catalog.json')
        # Original guard source checks now read a REAL synthetic Git commit,
        # rather than mocking guard or disguising missing copied dependencies.
        def git(*args):
            return REAL_CHECK_OUTPUT(['git','-C',str(source),*args],text=True).strip()
        git('init','-q','-b','feature/test-current');git('add','.')
        git('-c','user.name=Test','-c','user.email=test@example.invalid','commit','-qm','Qualified code fixture')
        config['source_head']=git('rev-parse','HEAD')
        f.fixture.git.side_effect=lambda args,**kw: (REAL_CHECK_OUTPUT(args,**kw)
            if args[2]==str(source) else f.fixture.git_read(args,**kw))
        f.fixture.write(self.protected/'current.json',config)
        python=b'synthetic kernel-qualified interpreter bytes'
        binding=dict(schema='protected-current-owner-v1',runtime=str(f.current.runtime),
            source_root=str(source),config_sha256=actual.file_sha(self.protected/'current.json'),
            catalog_sha256=actual.file_sha(self.protected/'catalog.json'),
            python_sha256=hashlib.sha256(python).hexdigest())
        f.fixture.write(self.protected/'binding.json',binding)
        state=copy.deepcopy(f.current.state);state['config_sha256']=binding['config_sha256']
        f.fixture.write(f.current.state_path,state)
        f.fixture.write(f.current.runtime/'current.json',{'untrusted':'ignored'})
        self.stack.enter_context(patch.object(actual,'PROTECTED_OWNER',self.protected))
        self.stack.enter_context(patch.object(actual,'protected_owner_bytes',side_effect=lambda path:
            python if Path(path)==Path(sys.executable) else Path(path).read_bytes()))
        self.stack.enter_context(patch.object(actual,'protected_owner_tree'))
        self.stack.enter_context(patch.object(actual,'_PROTECTED_CLOSURES',set()))
        self.stack.enter_context(patch.dict(os.environ,OFFMENU_PROTECTED_OWNER_REQUIRED='1'))
        # ACTUAL current_config and CurrentWork constructor/guard, with only
        # sealed-file/kernel ownership and immutable interpreter custody synthetic.
        self.current=actual.CurrentWork(f.current.runtime)
        self.assertIs(type(self.current.owner_custody),dict)
        self.assertEqual(self.current.owner_custody,binding)
        self.current.guard()
        for name in sources:self.assertEqual(config['source_sha256'][name],actual.file_sha(source/name))

    def check_real_sealed_current_factory_and_readback(self):
        import httpx
        from stokowski.linear import LinearClient
        f=self.f;nodes=[];writes=[]
        def transport(request):
            payload=json.loads(request.content);query=payload['query']
            if query.startswith('mutation'):
                state=json.loads(self.current.state_path.read_text())
                self.assertEqual(state['native_harness_linear'][f.binding.operation_id]['status'],'pending')
                writes.append(payload)
                nodes.append(dict(id='actual-attachment-readback',url=payload['variables']['input']['url']))
                data=dict(attachmentCreate=dict(success=True))
            else:
                data=dict(issue=dict(id=f.issue.id,project=dict(id=f.binding.project_id),
                    attachments=dict(nodes=nodes,pageInfo=dict(hasNextPage=False,endCursor=None))))
            return httpx.Response(200,json=dict(data=data))
        client=LinearClient(endpoint='https://linear.invalid/graphql',api_key='synthetic-offline-only')
        asyncio.run(client._client.aclose())
        client._client=httpx.AsyncClient(transport=httpx.MockTransport(transport))
        self.addCleanup(lambda:asyncio.run(client.close()))
        asyncio.run(self.current.continue_native_harness(linear_client=client))
        result=self.current.state['tasks'][f.issue.identifier]['native_harness']['projection']
        self.assertEqual(result['status'],'advanced',result)
        self.assertEqual(result['effect']['status'],'verified')
        reopened=self.native.CurrentWork(self.current.runtime)
        asyncio.run(reopened.continue_native_harness(linear_client=client))
        self.assertEqual(len(writes),1)
        self.assertFalse(reopened._native_harness_refill_allowed(f.issue.identifier))

    def test_real_sealed_current_default_factory_and_native_http_readback(self):
        self.check_real_sealed_current_factory_and_readback()

    def test_real_sealed_empty_linear_context_default_factory_and_readback(self):
        # Reseal only synthetic owner data; constructor, guard, selection reader,
        # native receipt gate, factory and durable-intent/readback remain real.
        self.selection['context']={}
        self.f.fixture.write(self.selection_path,self.selection)
        config=json.loads((self.protected/'current.json').read_text())
        config['native_harness_boundaries'][self.f.issue.identifier]['sha256']=self.native.file_sha(self.selection_path)
        self.f.fixture.write(self.protected/'current.json',config)
        custody=json.loads((self.protected/'binding.json').read_text())
        custody['config_sha256']=self.native.file_sha(self.protected/'current.json')
        self.f.fixture.write(self.protected/'binding.json',custody)
        state=json.loads(self.current.state_path.read_text());state['config_sha256']=custody['config_sha256']
        self.f.fixture.write(self.current.state_path,state)
        self.current=self.native.CurrentWork(self.current.runtime)
        self.assertEqual(self.current._native_harness_selection(self.f.issue.identifier)['context'],{})
        self.check_real_sealed_current_factory_and_readback()

    def test_boolean_truthy_or_malformed_custody_never_substitutes_for_binding(self):
        f=self.f
        selection=self.current._native_harness_selection(f.issue.identifier)
        binding=self.module.OwnerBinding(**selection['binding'])
        adapters=self.module.owner_adapters(self.current,f.issue,binding,selection)
        # The proper dictionary qualifies after the unmodified fresh guard.
        self.assertIs(adapters.authorize(self.current,f.issue,binding),True)
        for fake in (True,False,{'validated':'root'},dict(self.current.owner_custody,extra=True),
                     dict(self.current.owner_custody,config_sha256='0'*64)):
            self.current.owner_custody=fake
            with self.subTest(fake=fake),self.assertRaisesRegex(current_fixture.AdmissionError,'current_config_drift'):
                adapters.authorize(self.current,f.issue,binding)

    def test_changed_protected_binding_is_rejected_by_actual_guard(self):
        value=json.loads((self.protected/'binding.json').read_text())
        value['source_root']=str(self.protected/'foreign')
        self.f.fixture.write(self.protected/'binding.json',value)
        with self.assertRaisesRegex(current_fixture.AdmissionError,'protected_owner_binding'):self.current.guard()


class PublisherInvocationClientTests(SealedCurrentFactoryTests):
    # Reuse real constructor/guard/source/native-gate fixture, not injected
    # OwnerAdapters. Base assertions stay useful with the optional helper copied.
    def enable(self, prepared=True):
        import hashlib
        import native_publisher_invocation as helper
        f=self.f;source=f.packet['handoff']['source']
        publisher_binding=dict(repository=source['repository'],owner=f.binding.owner,
            issue_id=f.binding.issue_id,project_id=f.binding.project_id,head_branch=source['branch'],
            **{k:source[k] for k in ('base','head','tree')})
        bound=replace(f.binding,phase='integration',operation_id=helper.fingerprint(publisher_binding))
        self.binding=self.module.OwnerBinding(**asdict(bound))
        capability=dict(version=1,closure_sha256='1'*64,host_confirmation_sha256='2'*64)
        self.selection['binding']=asdict(self.binding)
        self.selection['context']['publisher_invocation']=capability
        f.fixture.write(self.selection_path,self.selection)
        config=json.loads((self.protected/'current.json').read_text())
        config['native_harness_boundaries'][f.issue.identifier]['sha256']=self.native.file_sha(self.selection_path)
        f.fixture.write(self.protected/'current.json',config)
        custody=json.loads((self.protected/'binding.json').read_text())
        custody['config_sha256']=self.native.file_sha(self.protected/'current.json')
        f.fixture.write(self.protected/'binding.json',custody)
        state=json.loads(self.current.state_path.read_text());state['config_sha256']=custody['config_sha256']
        f.fixture.write(self.current.state_path,state)
        self.current=self.native.CurrentWork(self.current.runtime)
        self.host_root=f.fixture.temp/'helper-host';self.host_root.mkdir()
        if prepared:
            transaction=self.host_root/'prepared-original-transaction';transaction.mkdir()
            (transaction/'binding.json').write_text('preexisting synthetic owner binding\n')
        config=dict(version=1,publisherUid=984,publisherGid=976,logicalOwner=bound.owner,
            binding=publisher_binding,snapshot=dict(native_runtime=dict(issue_id=bound.issue_id,
            project_id=bound.project_id,owner=bound.owner,unit_sha256=bound.unit_sha256,
            packet_sha256=bound.packet_sha256,source=source)))
        (self.host_root/'host-config.json').write_text(json.dumps(config))
        self.calls=[];self.lose=False;self.corrupt=False;self.scenario='normal'
        return helper

    def adapters(self):
        return self.module.owner_adapters(self.current,self.f.issue,self.binding,self.selection)

    async def transport(self,envelope):
        # This is the ONLY test replacement of the privileged route. It checks
        # persisted exact intent, then runs the ACTUAL helper supervisor in an
        # ordinary disposable process with real kernel-derived terminal proof.
        import native_publisher_invocation as helper
        self.calls.append(copy.deepcopy(envelope))
        state=json.loads(self.current.state_path.read_text())
        record=state[self.module.INVOCATIONS][self.binding.operation_id]['invocations'][-1]
        self.assertEqual(record['envelope']['invocation_id'],envelope['invocation_id'])
        self.assertEqual(record['envelope']['request'],envelope['request'])
        self.assertEqual(record['last_request'],envelope)
        self.assertEqual(record['status'],'pending')
        module_root=Path(helper.__file__).resolve().parents[2]
        script=('import sys,json,os;from pathlib import Path; '
            +'sys.path[:0]='+repr([str(module_root/'tools/delivery'),str(module_root/'tests/delivery')])+'; '
            +'import native_publisher_invocation as h;from test_native_publisher_invocation import SyntheticHost; '
            +'q=h.request(sys.stdin.buffer.read());host=SyntheticHost('+repr(str(self.host_root))+','+repr(self.scenario)+'); '
            +'host.config=json.loads((Path('+repr(str(self.host_root))+')/"host-config.json").read_text()); '
            + ('host._body=host._body.replace("status=\'ready\'","status=\'unknown\'"); ' if self.scenario=='native-unknown' else '')
            + ('host._body=host._body.replace("status=\'ready\'","status=\'verified\'"); ' if self.scenario=='native-verified' else '')
            +'h._echild=(lambda:(_ for _ in ()).throw(AssertionError("observer ECHILD"))) if q["mode"]=="observe" else h._echild; '
            + ('h._supervise=lambda *_:os._exit(99); ' if self.scenario=='crash' else '')
            +'sys.stdout.buffer.write(h.wire(h._invoke(h.wire(q),host)))')
        result=await asyncio.create_subprocess_exec(sys.executable,'-I','-B','-c',script,
            stdin=asyncio.subprocess.PIPE,stdout=asyncio.subprocess.PIPE,stderr=asyncio.subprocess.PIPE)
        stdout,stderr=await result.communicate(helper.wire(envelope))
        if result.returncode:
            raise self.module.RuntimeHold('synthetic_helper_refused')
        value=helper.decode(stdout)
        helper.validate_result(value,envelope,'1'*64)
        if self.lose:
            self.lose=False
            raise TimeoutError('lost only reply after original durable terminal')
        if self.corrupt:
            self.corrupt=False
            value['receipt']['body']['terminal']['waitpid_echild']=False
            value['receipt']['sha256']=helper.sha(helper.wire(value['receipt']['body']))
        return helper.wire(value)

    def test_same_uuid_lost_reply_recovery_does_not_infer_old_children(self):
        helper=self.enable()
        with patch.object(self.module,'fixed_invocation_wire',side_effect=self.transport):
            self.lose=True
            with self.assertRaises(TimeoutError):asyncio.run(self.adapters().observe(self.binding))
            first=self.calls[0]
            reopened=self.native.CurrentWork(self.current.runtime);self.current=reopened
            result=asyncio.run(self.adapters().observe(self.binding))
            self.assertEqual(result['status'],'ready')
            self.assertEqual(self.calls[1],{**first,'mode':'observe'})
            self.assertEqual((self.host_root/'computation-count').read_text().count('once'),1)

    def test_one_helper_call_per_boundary_and_original_step_recovery(self):
        self.enable()
        with patch.object(self.module,'fixed_invocation_wire',side_effect=self.transport):
            adapters=self.adapters()
            self.assertEqual(asyncio.run(adapters.observe(self.binding))['status'],'ready')
            with self.assertRaisesRegex(self.module.RuntimeHold,'publisher_next_boundary_required'):
                asyncio.run(adapters.step(self.binding,{}))
            self.assertEqual(len(self.calls),1)
            adapters=self.adapters()  # next existing finite boundary
            self.assertEqual(asyncio.run(adapters.observe(self.binding))['status'],'ready')
            self.lose=True
            with self.assertRaises(TimeoutError):asyncio.run(adapters.step(self.binding,{}))
            original=self.calls[-1]
            self.assertEqual(original['request']['mode'],'step')
            self.assertNotEqual(original['invocation_id'],self.calls[0]['invocation_id'])
            self.assertEqual(asyncio.run(self.adapters().observe(self.binding))['status'],'ready')
            self.assertEqual(self.calls[-1],{**original,'mode':'observe'})
            self.assertEqual((self.host_root/'computation-count').read_text().count('once'),2)

    def test_contradictory_kernel_receipt_and_capability_drift_are_held(self):
        self.enable()
        with patch.object(self.module,'fixed_invocation_wire',side_effect=self.transport):
            self.corrupt=True
            with self.assertRaises(Exception):asyncio.run(self.adapters().observe(self.binding))
            original=self.calls[0]
            self.assertEqual(asyncio.run(self.adapters().observe(self.binding))['status'],'ready')
            self.assertEqual(self.calls[-1],{**original,'mode':'observe'})
            selection=copy.deepcopy(self.selection)
            selection['context']['publisher_invocation']['closure_sha256']='3'*64
            with self.assertRaises(Exception):
                asyncio.run(self.module.owner_adapters(self.current,self.f.issue,self.binding,selection).observe(self.binding))
            self.assertEqual(len(self.calls),2)

    def test_absent_prepared_owner_transaction_does_not_initialize_or_retry(self):
        self.enable(prepared=False)
        with patch.object(self.module,'fixed_invocation_wire',side_effect=self.transport):
            with self.assertRaises(self.module.RuntimeHold):asyncio.run(self.adapters().observe(self.binding))
            original=self.calls[0]
            with self.assertRaises(self.module.RuntimeHold):asyncio.run(self.adapters().observe(self.binding))
            self.assertEqual(self.calls[-1],{**original,'mode':'observe'})
            self.assertFalse((self.host_root/'prepared-original-transaction').exists())

    def test_lifecycle_complete_error_is_not_native_success(self):
        self.enable();self.scenario='nonzero'
        with patch.object(self.module,'fixed_invocation_wire',side_effect=self.transport):
            with self.assertRaisesRegex(self.module.RuntimeHold,'native_outcome_held'):
                asyncio.run(self.adapters().observe(self.binding))
            # Only after the ORIGINAL terminal kernel proof may a later boundary
            # start a NEW READONLY inner observe for the SAME operation.
            self.scenario='normal'
            result=asyncio.run(self.adapters().observe(self.binding))
            self.assertEqual(result['status'],'ready')
            self.assertNotEqual(self.calls[0]['invocation_id'],self.calls[1]['invocation_id'])
            self.assertTrue(all(v['request']['mode']=='observe' for v in self.calls))
            self.assertEqual(self.calls[0]['request']['operation_id'],self.calls[1]['request']['operation_id'])

    def test_verified_readback_reauthenticates_same_protected_receipt_not_caller_cache(self):
        self.enable();self.scenario='native-verified'
        with patch.object(self.module,'fixed_invocation_wire',side_effect=self.transport):
            self.assertEqual(asyncio.run(self.adapters().observe(self.binding))['status'],'verified')
            original=self.calls[0]
            self.current=self.native.CurrentWork(self.current.runtime)
            self.assertEqual(asyncio.run(self.adapters().observe(self.binding))['status'],'verified')
            self.assertEqual(self.calls[-1],{**original,'mode':'observe'})
            self.assertEqual((self.host_root/'computation-count').read_text().count('once'),1)

    def test_missing_original_terminal_never_gets_new_uuid_or_observer_cleanup(self):
        self.enable();self.scenario='crash'
        with patch.object(self.module,'fixed_invocation_wire',side_effect=self.transport):
            with self.assertRaises(self.module.RuntimeHold):asyncio.run(self.adapters().observe(self.binding))
            original=self.calls[0]
            self.scenario='normal'
            for _ in range(2):
                with self.assertRaisesRegex(self.module.RuntimeHold,'publisher_invocation_unresolved'):
                    asyncio.run(self.adapters().observe(self.binding))
                self.assertEqual(self.calls[-1],{**original,'mode':'observe'})
            self.assertFalse((self.host_root/'computation-count').exists())
            record=self.current.state[self.module.INVOCATIONS][self.binding.operation_id]['invocations'][-1]
            self.assertEqual(record['status'],'unknown')
            self.assertIsNone(record['result']['receipt']['body']['terminal'])

    def test_complete_unknown_native_outcome_allows_later_readonly_not_step(self):
        self.enable();self.scenario='native-unknown'
        with patch.object(self.module,'fixed_invocation_wire',side_effect=self.transport), \
             patch.object(self.module,'publisher_identity',side_effect=AssertionError('protected publisher read')):
            with self.assertRaisesRegex(self.module.RuntimeHold,'publisher_native_outcome_held'):
                asyncio.run(self.adapters().observe(self.binding))
            original=self.calls[0]
            record=self.current.state[self.module.INVOCATIONS][self.binding.operation_id]['invocations'][-1]
            self.assertEqual(record['status'],'complete')  # lifecycle only
            self.assertEqual(record['result']['response']['status'],'unknown')
            self.scenario='normal'
            result=asyncio.run(self.adapters().observe(self.binding))
            self.assertEqual(result['status'],'ready')
            self.assertNotEqual(original['invocation_id'],self.calls[-1]['invocation_id'])
            self.assertTrue(all(call['request']['mode']=='observe' for call in self.calls))
            self.assertTrue(all(call['request']['operation_id']==self.binding.operation_id for call in self.calls))

    def test_resealed_changed_capability_cannot_rebind_retained_invocation(self):
        self.enable()
        with patch.object(self.module,'fixed_invocation_wire',side_effect=self.transport):
            asyncio.run(self.adapters().observe(self.binding))
            self.selection['context']['publisher_invocation']['closure_sha256']='3'*64
            self.f.fixture.write(self.selection_path,self.selection)
            config=json.loads((self.protected/'current.json').read_text())
            config['native_harness_boundaries'][self.f.issue.identifier]['sha256']=self.native.file_sha(self.selection_path)
            self.f.fixture.write(self.protected/'current.json',config)
            custody=json.loads((self.protected/'binding.json').read_text())
            custody['config_sha256']=self.native.file_sha(self.protected/'current.json')
            self.f.fixture.write(self.protected/'binding.json',custody)
            state=json.loads(self.current.state_path.read_text());state['config_sha256']=custody['config_sha256']
            self.f.fixture.write(self.current.state_path,state)
            self.current=self.native.CurrentWork(self.current.runtime)
            with self.assertRaisesRegex(self.module.RuntimeHold,'publisher_invocation_rebind'):
                asyncio.run(self.adapters().observe(self.binding))
            self.assertEqual(len(self.calls),1)

    def test_optional_capability_rejects_selectors_and_absence_keeps_direct_hold(self):
        with patch('os.getuid',return_value=1000),patch('os.geteuid',return_value=1000), \
             patch.object(self.module,'fixed_invocation_wire') as helper:
            original=self.current._native_harness_selection(self.f.issue.identifier)
            bound=self.module.OwnerBinding(**original['binding'])
            bound=replace(bound,phase='integration')
            # Pure direct route still has its early ordinary-UID hold. No cap is
            # minted from the host's read-only policy listing or user identity.
            with self.assertRaisesRegex(self.module.RuntimeHold,'publisher_owner_identity_required'):
                asyncio.run(self.module.fixed_publisher_rpc(bound,self.f.packet,'observe'))
            helper.assert_not_called()
        for bad in (True,{},dict(version=True,closure_sha256='1'*64,host_confirmation_sha256='2'*64),
                    dict(version=1,closure_sha256='1'*64,host_confirmation_sha256='2'*64,command='arbitrary')):
            with self.assertRaises(self.module.RuntimeHold):self.module.invocation_capability(bad)


class InvocationWireTests(unittest.IsolatedAsyncioTestCase):
    async def run_wire(self, body):
        actual=asyncio.create_subprocess_exec;children=[]
        envelope=dict(version=1,mode='observe',invocation_id='11111111-1111-4111-8111-111111111111',request={})
        async def launch(*args,**kwargs):
            self.assertEqual(args,runtime.PUBLISHER_HELPER_ARGV)
            self.assertEqual(kwargs['cwd'],'/')
            self.assertEqual(kwargs['env'],{'PATH':'/usr/bin:/bin','LANG':'C.UTF-8'})
            self.assertIs(kwargs['close_fds'],True)
            self.assertIs(kwargs['start_new_session'],True)
            child=await actual(sys.executable,'-I','-B','-c',body,**kwargs)
            children.append(child);return child
        with patch.object(asyncio,'create_subprocess_exec',side_effect=launch):
            try:return await runtime.fixed_invocation_wire(envelope)
            finally:
                self.assertEqual(len(children),1)
                self.assertIsNotNone(children[0].returncode)

    async def test_fixed_tuple_transport_reap_is_not_privileged_cleanup_proof(self):
        raw=await self.run_wire('import sys; sys.stdin.buffer.read(); print("{}")')
        self.assertEqual(json.loads(raw),{})  # Transport only, not a valid receipt.
        import native_publisher_invocation as helper
        with self.assertRaises(helper.InvocationHold):
            helper.validate_result({},dict(version=1,mode='observe',
                invocation_id='11111111-1111-4111-8111-111111111111',request={}), '1'*64)

    async def test_fixed_tuple_output_bound_and_cancel_reap_only_own_child(self):
        with self.assertRaises(runtime.RuntimeHold):
            await self.run_wire('import sys; sys.stdin.buffer.read(); print("x"*70000)')
        with self.assertRaises(TimeoutError):
            await asyncio.wait_for(self.run_wire('import time; time.sleep(20)'),.1)
