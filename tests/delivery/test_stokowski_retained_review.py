"""Automatic retained review, using synthetic source and real local Journal checks."""
import asyncio
import copy
import json
from pathlib import Path
import sys
import subprocess
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent))
import test_stokowski_nonimplementation_stage as fixtures
import stokowski_adapter as adapter
import stokowski_operations as operations
import stokowski_stage as stage
from symphony_capacity import AdmissionError, digest
from test_stokowski_operations import FaultedWindmill


@unittest.skipUnless(fixtures.importlib.util.find_spec('stokowski'), 'Use pinned Stokowski environment')
class RetainedReviewTests(unittest.TestCase):
    # Reuse evidence builders without duplicating the inherited regression suite.
    copy_fixture_source = staticmethod(fixtures.ReviewedSourceTests.copy_fixture_source)
    ref = staticmethod(fixtures.ReviewedSourceTests.ref)
    for _name in ('setUp','write','git_read','prepare_current','qualify','publish','adapted',
                  'client','select','bound_gate','review_fixture','continuation_fixture','turn',
                  'stage_fixture','publish_stage','new_fixture','retained_terminal','rebind_terminal'):
        locals()[_name] = getattr(fixtures.ReviewedSourceTests, _name)

    def test_protected_stage_control_can_advance_only_with_exact_origin(self):
        issue, _, _, _, _, _, _, _ = self.new_fixture()
        control = self.root/'synthetic-protected-control'
        control.mkdir()
        def git(*args):
            return subprocess.run(['git','-C',str(control),*args],check=True,capture_output=True,text=True).stdout.strip()
        git('init','-b','feature/test-current')
        (control/'source').write_text('old control\n');git('add','.')
        def commit():
            git('-c','user.name=Synthetic','-c','user.email=synthetic@example.invalid',
                '-c','commit.gpgsign=false','commit','-m','synthetic control')
            return git('rev-parse','HEAD')
        old = commit()
        (control/'source').write_text('new control\n');git('add','.')
        head = commit()
        manifest = copy.deepcopy(self.stage_manifest);manifest['base_revision']=old
        self.current.config['source_head']=head
        self.current.owner_custody={'source_root':str(control)}
        # Real ancestry and branch inspection; origin qualification remains the
        # actual previously built source/admission/provenance reader.
        with patch.object(adapter,'SOURCE',control), patch.object(adapter.subprocess,'check_output',
                side_effect=lambda *a,**kw: subprocess.run(*a,check=True,stdout=subprocess.PIPE,**kw).stdout), \
                patch.object(self.current,'reviewed_origin',wraps=self.current.reviewed_origin) as origin:
            # reviewed_origin checks the accepted module blobs; this test is
            # about control identity and uses the existing pinned fixture source
            # for that distinct origin check.
            def original_origin(*a,**kw):
                with patch.object(adapter,'SOURCE',self.source), patch.object(adapter.subprocess,'check_output',side_effect=self.git_read), patch.dict(self.current.config,source_head='a'*40):
                    return type(self.current).reviewed_origin(self.current,*a,**kw)
            origin.side_effect=original_origin
            self.current._check_task_control_source(issue.identifier,manifest,control)
            origin.assert_called_once()
            for change in ('coding','unprotected','foreign_path','unaccepted_head','branch','nonancestor','origin_drift'):
                selected=copy.deepcopy(manifest)
                self.current.owner_custody={'source_root':str(control)}
                self.current.config['source_head']=head
                path=control
                if change=='coding': selected['tasks'][issue.identifier].pop('stage')
                if change=='unprotected': self.current.owner_custody=None
                if change=='foreign_path': path=self.source
                if change=='unaccepted_head': self.current.config['source_head']=old
                if change=='branch': selected['branch']='feature/foreign'
                if change=='nonancestor': selected['base_revision']='f'*40
                if change=='origin_drift': origin.side_effect=AdmissionError('SYNTHETIC origin drift')
                with self.subTest(change=change), self.assertRaises((AdmissionError,subprocess.CalledProcessError)):
                    self.current._check_task_control_source(issue.identifier,selected,path)

    def terminal_fixture(self):
        values = self.new_fixture(executor_sha256='e'*64)
        issue, runtime, _, journal, key, spec, _, _ = values
        path, receipt = self.retained_terminal(issue, runtime, journal, key, spec)
        # This is the original body, not a new frozen stage input/admission.
        del self.stage_task['stage_binding']['inputs'][str(path)]
        path.rename(runtime/'validation-receipt.json')
        self.rebind_terminal(runtime, spec)
        self.publish_stage()
        return values, receipt

    def test_retained_terminal_consumed_and_restart_does_not_dispatch(self):
        values, receipt = self.terminal_fixture()
        issue, runtime, _, journal, key, spec, remote, _ = values
        frozen = copy.deepcopy(self.stage_task['stage_binding'])
        with patch.object(self.current, 'continue_native_review', side_effect=AssertionError('new reviewer')):
            asyncio.run(self.current.continue_validation())
        incoming = self.runtime/('unit-review-'+issue.identifier+'.json')
        self.assertTrue(incoming.exists())
        raw = incoming.read_bytes()
        packet = json.loads(raw)
        self.assertEqual(packet['origin'], 'retained-typed-review-v1')
        self.assertEqual(packet['validation_receipt'], receipt)
        self.assertIsNone(packet['decision']['action'])
        self.assertNotIn('model', packet['snapshot']['review'])
        self.assertEqual(self.current._check_unit_review(packet), packet['unit_binding'])
        self.current.refresh()
        gate = self.current.state['tasks'][issue.identifier]['unit_gate']
        self.assertEqual(gate['disposition'], 'approved')
        self.assertFalse(gate['accepted_delivery'])
        self.current = adapter.CurrentWork(self.runtime)
        asyncio.run(self.current.continue_validation())
        self.assertEqual(incoming.read_bytes(), raw)
        self.assertEqual(self.stage_task['stage_binding'], frozen)
        self.assertEqual(journal.read(key)[1]['status'], 'succeeded')
        remote.inspect.assert_not_awaited()
        remote.submit.assert_not_awaited()

    def test_normal_observation_retains_original_body_and_enters_consumer(self):
        issue, runtime, _, journal, key, spec, _, _ = self.new_fixture()
        self.publish_stage()
        remote = FaultedWindmill()
        async def close(): pass
        remote.close = close
        with patch.object(stage, 'WindmillMCP', return_value=remote):
            asyncio.run(self.current.continue_validation())
            self.assertEqual(len(remote.submissions), 1)
            self.assertFalse((self.runtime/('unit-review-'+issue.identifier+'.json')).exists())
            state = journal.read(key)[1]
            remote.complete(state['windmill_job_id'], spec)
            original = remote.jobs[state['windmill_job_id']]['result']['receipt']
            original['duration_seconds'] = 7.65  # Preserve the actual parsed body, including floats.
            asyncio.run(self.current.continue_validation())
            retained = adapter.read_record(runtime/'validation-receipt.json')
            self.assertEqual(retained, original)
            self.assertEqual(digest(retained), journal.read(key)[1]['receipt_sha256'])
            self.current.refresh()
            self.assertEqual(self.current.state['tasks'][issue.identifier]['unit_gate']['disposition'], 'approved')
            asyncio.run(self.current.continue_validation())
        self.assertEqual(len(remote.submissions), 1)

    def test_pending_cancel_unknown_and_receipt_binding_hold(self):
        values, original_receipt = self.terminal_fixture()
        issue, runtime, _, journal, key, spec, _, _ = values
        original_state = journal.read(key)[1]
        path = runtime/'validation-receipt.json'
        cases = [('state', 'status', value) for value in ('prepared','running','unknown','cancelled')]
        cases += [('state', name, value) for name, value in (
            ('cancel_requested', True), ('observation_intent', True), ('reconcile_required', True),
            ('accepted_output_sha256', {}), ('receipt_sha256', '0'*64))]
        cases += [('receipt', name, value) for name, value in (
            ('job_id', 'foreign'), ('command_sha256', '0'*64), ('runner_sha256', '0'*64),
            ('capacity_policy_sha256', '0'*64), ('child_tree_gone', False), ('exit_code', False))]
        for kind, name, value in cases:
            state = copy.deepcopy(original_state)
            receipt = copy.deepcopy(original_receipt)
            if kind == 'state': state[name] = value
            else:
                receipt[name] = value
                state['receipt_sha256'] = digest(receipt)
            self.write(path, receipt)
            journal.save(key, state, 'SYNTHETIC mutation')
            with self.subTest(kind=kind, name=name, value=value), self.assertRaises(AdmissionError):
                self.current.retained_typed_review_packet(issue.identifier)
        journal.save(key, original_state, 'SYNTHETIC restore')
        # The complete backend body is not interchangeable with the exact
        # original public projection committed by the Journal.
        self.write(path, dict(original_receipt, resources={'synthetic':'backend-only'}))
        with self.assertRaises(AdmissionError): self.current.retained_typed_review_packet(issue.identifier)
        path.unlink()
        with self.assertRaises(AdmissionError): self.current.retained_typed_review_packet(issue.identifier)

    def test_receipt_custody_conflict_preserves_terminal_job_and_holds(self):
        issue, runtime, _, journal, key, spec, _, _ = self.new_fixture()
        self.publish_stage()
        self.write(runtime/'validation-receipt.json', {'foreign':'receipt'})
        remote = FaultedWindmill()
        async def close(): pass
        remote.close = close
        with patch.object(stage, 'WindmillMCP', return_value=remote):
            asyncio.run(self.current.continue_validation())
            remote.complete(journal.read(key)[1]['windmill_job_id'], spec)
            asyncio.run(self.current.continue_validation())
            self.assertEqual(journal.read(key)[1]['status'], 'succeeded')
            asyncio.run(self.current.continue_validation())
        self.assertEqual(len(remote.submissions), 1)
        self.assertFalse((self.runtime/('unit-review-'+issue.identifier+'.json')).exists())
        self.assertEqual(adapter.read_record(runtime/'validation-receipt.json'), {'foreign':'receipt'})

    def test_pinned_review_and_packet_substitution_or_conflict_hold(self):
        values, _ = self.terminal_fixture()
        issue = values[0]
        packet = self.current.retained_typed_review_packet(issue.identifier)
        for section, name, value in (
            ('snapshot', 'review', {'reviewer':'substitute','decision':'accepted'}),
            ('decision', 'version', True),
            ('decision', 'action', {'kind':'merge-pr'}),
            ('integration_binding', 'head', 'a'*40)):
            altered = copy.deepcopy(packet); altered[section][name] = value
            with self.subTest(section=section), self.assertRaises(AdmissionError):
                self.current._check_unit_review(altered)
        review_path = Path(packet['snapshot']['review']['path'])
        raw = review_path.read_bytes(); review_path.write_bytes(raw+b' ')
        with self.assertRaises(AdmissionError): self.current._check_unit_review(packet)
        review_path.write_bytes(raw)
        incoming = self.runtime/('unit-review-'+issue.identifier+'.json')
        incoming.write_text('{}')
        asyncio.run(self.current.continue_validation())
        self.assertEqual(incoming.read_text(), '{}')
        self.assertNotEqual(self.current.state['tasks'][issue.identifier]['unit_gate']['disposition'], 'approved')
