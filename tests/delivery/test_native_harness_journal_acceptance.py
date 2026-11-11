"""Integration Journal hook; reader122 is an explicit synthetic trust seam here.

Existing CurrentWork identity/owner factory and transaction boundary remain real.
The separate retained-typed reader must be verified after owner consolidation.
"""
import copy
from dataclasses import replace
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import unittest
from unittest.mock import Mock, patch

import native_harness_runtime as runtime
import test_native_harness_runtime as existing
from symphony_capacity import AdmissionError, digest as journal_digest


class JournalAcceptanceTests(unittest.TestCase):
    def setUp(self):
        self.f = existing.RuntimeBoundaryTests(methodName='runTest')
        self.addCleanup(self.f.doCleanups)
        self.f.setUp()
        self.current, self.issue = self.f.current, self.f.issue
        self.root = self.f.task_runtime
        h = self.f.handoff
        self.receipt = dict(status='succeeded', exit_code=0, child_tree_gone=True,
            reconcile_required=False, job_id='original-job', command_sha256='1'*64,
            runner_sha256='2'*64, capacity_policy_sha256='3'*64)
        path = self.root/'original-validation.json'
        path.write_text(json.dumps(self.receipt))
        self.ref = dict(path=str(path), sha256=hashlib.sha256(path.read_bytes()).hexdigest())
        h['operation'] = dict(id='original-operation', backend='windmill',
            job_id=self.receipt['job_id'], status='succeeded', receipt=self.ref,
            command_sha256='1'*64, runner_sha256='2'*64, policy_sha256='3'*64)
        h['effect'] = dict(operation_id='original-operation', status='verified')
        self.spec = dict(version=3, issue_id=self.issue.id, owner=h['owner'],
            head=h['source']['head'], base=h['source']['base'], branch=h['source']['branch'],
            outputs={}, policy_sha256='3'*64, runner_sha256='2'*64)
        self.state = dict(receipt_sha256=journal_digest(self.receipt), logical_job_id='original-job')
        self.task = dict(stage_binding=dict(inputs={self.ref['path']:self.ref['sha256']}))
        self.review = dict(origin='retained-typed-review-v1',
            integration_binding=dict(head=self.spec['head'], base=self.spec['base'],
                tree=h['source']['tree'], head_branch=self.spec['branch'], outputs={}),
            validation_receipt=self.receipt)
        self.f.bind('integration')
        self.unit = self.current.gate_binding(self.issue, observation=True)
        self.reader = Mock(return_value=self.unit)
        self.origin = Mock(return_value=(self.root,self.spec,dict(operation_key='original-operation'),
                                         self.state,{}))
        self.terminal = Mock(return_value=self.receipt)
        stack = self.f.fixture.stack
        # Synthetic reader122 contract: no production original-reader bypass.
        stack.enter_context(patch.object(self.current, '_check_unit_review', self.reader))
        stack.enter_context(patch.object(self.current, 'reviewed_origin', self.origin))
        stack.enter_context(patch.object(self.current, '_check_reviewed_terminal', self.terminal))
        original_context = self.current.context
        def context(*args, **kwargs):
            result = original_context(*args, **kwargs)
            if kwargs.get('review') and not kwargs.get('observation'):
                manifest = copy.deepcopy(result[1])
                manifest['tasks'][self.issue.identifier] = self.task
                return result[0], manifest, result[2]
            return result
        stack.enter_context(patch.object(self.current, 'context', side_effect=context))

    def adapters(self):
        selection = self.f.factory_selection(context=dict(reviewed_runtime=str(self.root),
            unit_review=self.f.handoff['origin']['evidence']))
        path = self.current.runtime/'journal-unit-review.json'
        self.f.fixture.write(path, self.review)
        selection['context']['unit_review'] = dict(path=str(path),
            sha256=hashlib.sha256(path.read_bytes()).hexdigest())
        self.f.fixture.write(Path(self.current.config['native_harness_boundaries'][self.issue.identifier]['path']), selection)
        ref = self.current.config['native_harness_boundaries'][self.issue.identifier]
        ref['sha256'] = hashlib.sha256(Path(ref['path']).read_bytes()).hexdigest()
        result = runtime.owner_adapters(self.current,self.issue,self.f.binding,selection)
        return replace(result, observe=lambda _:copy.deepcopy(self.f.effect), step=self.f.step,
                       engine=Mock(side_effect=AssertionError('must not load Engine')))

    def test_normal_factory_qualified_journal_advances_without_engine(self):
        adapters = self.adapters()
        result = self.f.consume(adapters=adapters)
        self.assertEqual(result['status'], 'advanced', result)
        context = self.f.step.call_args.args[1]
        self.assertNotIn('engine', context)
        self.assertEqual(context['validation']['origin'], 'reviewed-source-journal-v3')
        self.assertEqual(context['validation']['operation_id'], 'original-operation')
        self.reader.assert_called_once_with(self.review)
        self.terminal.assert_called_once_with(self.spec,self.state,self.task['stage_binding']['inputs'],
                                             receipt_path=self.root/'validation-receipt.json')
        adapters.engine.assert_not_called()
        self.assertFalse(result['accepted_delivery'])
        self.assertFalse(result['refill_eligible'])

    def test_original_reader_refusal_prevents_journal_and_publisher(self):
        adapters = self.adapters()
        self.reader.side_effect = ValueError('unqualified retained review')
        result = self.f.consume(adapters=adapters)
        self.assertEqual(result['status'], 'held')
        self.origin.assert_not_called()
        self.f.step.assert_not_called()

    def test_exact_operation_receipt_and_source_binding_refusals(self):
        # Each distinct authority edge is tested directly after synthetic reader qualification.
        cases = [('runtime', lambda:None, 'journal_owner_runtime'),
                 ('job', lambda:self.f.handoff['operation'].update(job_id='other'), 'journal_operation_binding'),
                 ('command', lambda:self.f.handoff['operation'].update(command_sha256='9'*64), 'journal_operation_binding'),
                 ('receipt', lambda:self.task['stage_binding']['inputs'].clear(), 'journal_receipt_pin'),
                 ('tree', lambda:self.f.handoff['source'].update(tree='9'*40), 'review_candidate_coverage')]
        original = copy.deepcopy((self.f.handoff,self.task))
        for name, change, reason in cases:
            with self.subTest(name=name):
                self.f.handoff.clear(); self.f.handoff.update(copy.deepcopy(original[0]))
                self.task.clear(); self.task.update(copy.deepcopy(original[1]))
                change()
                with self.assertRaisesRegex(runtime.RuntimeHold, reason):
                    runtime.journal_acceptance(self.current,self.issue,
                        str(self.root) if name != 'runtime' else str(self.root/'other'),
                        self.review,self.f.handoff,None)

    def test_terminal_reconciliation_refusal_prevents_publication(self):
        adapters = self.adapters()
        self.terminal.side_effect = ValueError('original Journal uncertain')
        self.assertEqual(self.f.consume(adapters=adapters)['status'], 'held')
        self.f.step.assert_not_called()

    def test_fixed_original_receipt_outside_frozen_six_inputs(self):
        fixed = self.root/'validation-receipt.json'
        fixed.write_bytes(Path(self.ref['path']).read_bytes())
        # Actual admission shape: six immutable pins, none for a later receipt.
        inputs = {str(self.root/('frozen-'+str(i)+'.json')):str(i)*64 for i in range(6)}
        self.task['stage_binding']['inputs'] = inputs
        self.ref['path'] = str(fixed)
        self.f.bind('integration')  # The sealed owner packet pins this fixed reference.
        before = copy.deepcopy(inputs)
        result = self.f.consume(adapters=self.adapters())
        self.assertEqual(result['status'], 'advanced', result)
        self.assertEqual(inputs, before)
        self.assertEqual(len(inputs), 6)
        self.assertNotIn(str(fixed), inputs)
        self.terminal.assert_called_once_with(self.spec,self.state,inputs,receipt_path=fixed)

    def test_unpinned_noncanonical_receipt_path_is_refused(self):
        # The bytes match, but only the fixed original path or frozen pins qualify.
        self.task['stage_binding']['inputs'] = {}
        result = self.f.consume(adapters=self.adapters())
        self.assertEqual(result['reason'], 'journal_receipt_pin', result)
        self.f.step.assert_not_called()

    def test_release_ignores_integration_hook_and_requires_original_engine(self):
        self.f.bind('release')
        acceptance = Mock(side_effect=AssertionError('release must not use Journal'))
        engine = Mock(return_value=None)
        adapters = replace(self.f.adapters, engine=engine, integration_acceptance=acceptance)
        result = self.f.consume(adapters=adapters)
        self.assertEqual(result['reason'], 'engine_evidence_missing', result)
        acceptance.assert_not_called()
        engine.assert_called_once()
        self.f.step.assert_not_called()

    def test_release_factory_refuses_journal_context(self):
        self.f.bind('release')
        adapters = self.adapters()
        with self.assertRaisesRegex(runtime.RuntimeHold, 'owner_context_fields'):
            adapters.authorize(self.current,self.issue,self.f.binding)


class RealTerminalDigestTests(unittest.TestCase):
    def setUp(self):
        self.f = JournalAcceptanceTests(methodName='runTest')
        self.addCleanup(self.f.doCleanups)
        self.f.setUp()
        # Default to the consolidated original reader. During separate-owner
        # development this explicit test-only pin loads the exact reader122 file.
        source = os.environ.get('OFFMENU_TEST_TERMINAL_READER_SOURCE')
        module = existing.current_fixture.adapter
        if source:
            spec = importlib.util.spec_from_file_location('qualified_terminal_reader122', source)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
        reader = module.CurrentWork._check_reviewed_terminal
        self.f.current._check_reviewed_terminal = reader.__get__(self.f.current)
        import test_stokowski_identity_profile as identity
        import stokowski_operations as operations
        f = self.f
        h = f.f.handoff
        spec = identity.IdentityProfileTests().spec(issue=f.issue.identifier,
            issue_id=f.issue.id, owner=h['owner'], head=h['source']['head'],
            base=h['source']['base'], branch=h['source']['branch'])
        f.spec.clear(); f.spec.update(spec)
        args = operations.bridge_arguments(f.spec)
        f.receipt.update(job_id=args['job_id'],
            command_sha256=hashlib.sha256(args['command'].encode()).hexdigest(),
            runner_sha256=spec['runner_sha256'], capacity_policy_sha256=spec['policy_sha256'])
        f.state.update(status='succeeded', cancel_requested=False, reconcile_required=False,
            accepted_output_sha256=spec['outputs'], acceptance_sha256=spec['acceptance_sha256'],
            receipt_sha256=journal_digest(f.receipt), logical_job_id=args['job_id'])
        self.assertNotEqual(journal_digest(f.receipt), runtime.digest(f.receipt))
        fixed = f.root/'validation-receipt.json'
        fixed.write_text(json.dumps(f.receipt))
        f.ref.update(path=str(fixed), sha256=hashlib.sha256(fixed.read_bytes()).hexdigest())
        pins = {}
        for i in range(6):
            path = f.root/('frozen-'+str(i)+'.json')
            path.write_text('{}')
            pins[str(path)] = hashlib.sha256(path.read_bytes()).hexdigest()
        f.task['stage_binding']['inputs'] = pins
        h['outputs'] = [dict(path=p,sha256=v) for p,v in spec['outputs'].items()]
        h['operation'].update(job_id=args['job_id'],command_sha256=f.receipt['command_sha256'],
            runner_sha256=spec['runner_sha256'],policy_sha256=spec['policy_sha256'])
        f.review['integration_binding']['outputs'] = spec['outputs']
        f.f.bind('integration')

    def test_real_terminal_compact_journal_receipt_advances(self):
        f = self.f
        result = f.f.consume(adapters=f.adapters())
        self.assertEqual(result['status'], 'advanced', result)
        self.assertNotIn(f.ref['path'], f.task['stage_binding']['inputs'])
        self.assertEqual(len(f.task['stage_binding']['inputs']), 6)

    def test_real_terminal_rejects_body_drift_and_sealed_hash_drift(self):
        f = self.f
        path = Path(f.ref['path'])
        original = path.read_bytes()
        # Original Journal digest rejects changed body, even if otherwise valid.
        body = dict(f.receipt, output_bytes={'stdout':1})
        path.write_text(json.dumps(body))
        with self.assertRaisesRegex(AdmissionError, 'reviewed_source_terminal_receipt_missing'):
            f.current._check_reviewed_terminal(f.spec,f.state,
                f.task['stage_binding']['inputs'],receipt_path=path)
        result = f.f.consume(adapters=f.adapters())
        self.assertEqual(result['status'], 'held', result)
        self.assertEqual(result['reason'], 'AdmissionError')
        f.f.step.assert_not_called()
        # Identical body with different serialization passes the real reader,
        # then fails the independently sealed handoff file-byte hash.
        path.write_text(json.dumps(f.receipt,indent=2))
        result = f.f.consume(adapters=f.adapters())
        self.assertEqual(result['reason'], 'private_artifact_drift', result)
        f.f.step.assert_not_called()
        path.write_bytes(original)


if __name__ == '__main__':
    unittest.main()
