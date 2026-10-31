"""Operation crash/restart tests with actual durable SQLite and faulted API edges."""
import asyncio
import ast
import copy
from contextlib import redirect_stderr
import hashlib
import io
import json
from pathlib import Path
import sys
import tempfile
import tarfile
import subprocess
import shlex
import unittest
from unittest.mock import patch

TOOLS = Path(__file__).resolve().parents[2]/'tools/delivery'
sys.path.insert(0,str(TOOLS))
import stokowski_operations as operations


class FaultedWindmill:
    def __init__(self):
        self.jobs = {}
        self.submissions = []
        self.lose_ack = False
        self.offline = False
        self.refused = False

    async def inspect(self,job_id):
        if self.offline:
            raise operations.TransportUnavailable('offline')
        return copy.deepcopy(self.jobs.get(job_id))

    async def submit(self,job_id,args):
        if self.refused:
            raise operations.RequestRefused('403')
        if job_id in self.jobs:
            raise RuntimeError('Duplicate UUID')
        self.submissions.append((job_id,copy.deepcopy(args)))
        self.jobs[job_id] = {'id':job_id,'workspace_id':'offmenu',
            'script_path':operations.BRIDGE,'args':copy.deepcopy(args),
            'type':'QueuedJob','running':True}
        if self.lose_ack:
            self.lose_ack = False
            raise TimeoutError('response lost after accepting the job')

    def complete(self,job_id,spec,status='succeeded',wrapper_success=True):
        args = operations.bridge_arguments(spec)
        receipt = {'job_id':args['job_id'],'status':status,'exit_code':0 if status == 'succeeded' else 1,
                   'child_tree_gone':True,'reconcile_required':False,
                   'capacity_policy_sha256':spec['policy_sha256'],
                   'runner_sha256':spec['runner_sha256'],
                   'command_sha256':hashlib.sha256(args['command'].encode()).hexdigest()}
        self.jobs[job_id].update(type='CompletedJob',running=False,success=wrapper_success,
            result={'job_id':args['job_id'],'job_succeeded':status=='succeeded','receipt':receipt})


class OperationRecoveryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.journal = operations.Journal(self.root)
        self.spec = {'version':1,'issue':'UIF-92','issue_id':'8daac134-01ab-4a02-a4d2-c0c417d0bd32',
                     'stage':'verify','owner':'integration-writer','head':'a'*40,'base':'b'*40,
                     'policy_sha256':hashlib.sha256(operations.POLICY.read_bytes()).hexdigest(),
                     'runner_sha256':hashlib.sha256((TOOLS/'windmill_runner.py').read_bytes()).hexdigest(),
                     'executor_sha256':hashlib.sha256(Path(operations.__file__).read_bytes()).hexdigest(),
                     'acceptance_sha256':'c'*64,'profile':'delivery-suite',
                     'outputs':{'tests/meaningful.py':'d'*64}}
        self.key = self.journal.prepare(self.spec)
        self.remote = FaultedWindmill()

    def tick(self):
        # Reopen the durable journal each time, as after a process restart.
        return asyncio.run(operations.Journal(self.root).tick(self.key,self.remote))

    def test_accepted_validator_cannot_be_replaced_by_weakened_candidate_test(self):
        root=self.root/'candidate';root.mkdir()
        (root/'tests/delivery').mkdir(parents=True)
        (root/'src').mkdir()
        validator=root/'tests/delivery/test_baseline.py'
        validator.write_text('import unittest, target\nclass Baseline(unittest.TestCase):\n def test_contract(self): self.assertEqual(target.answer,42)\n')
        (root/'src/target.py').write_text('answer=42\n')
        subprocess.run(['git','init','-q',str(root)],check=True)
        subprocess.run(['git','-C',str(root),'add','.'],check=True)
        subprocess.run(['git','-C',str(root),'-c','user.name=Fixture','-c','user.email=fixture@example.invalid','commit','-qm','accepted validators'],check=True)
        base=subprocess.check_output(['git','-C',str(root),'rev-parse','HEAD'],text=True).strip()
        validator.write_text('import unittest\nclass Weakened(unittest.TestCase):\n def test_empty(self): pass\n')
        (root/'src/target.py').write_text('answer=0\n')
        (root/'.venv-delivery/bin').mkdir(parents=True)
        (root/'.venv-delivery/bin/python').symlink_to(sys.executable)
        command=operations.trusted_validation_command(dict(self.spec,base=base))
        argv=shlex.split(command);argv[2]=argv[2].replace("pathlib.Path('/offmenu')",'pathlib.Path('+repr(str(root))+')')
        result=subprocess.run(argv,text=True,capture_output=True,timeout=20)
        self.assertNotEqual(result.returncode,0)
        self.assertIn('ACCEPTED_CONTROL_VALIDATORS '+base,result.stdout,result.stderr)
        self.assertIn('0 != 42',result.stderr)

    def test_product_branch_is_bound_to_operation_and_checked_on_foo(self):
        selected = dict(self.spec,branch='bugfix/scanner-facts-consumer')
        self.assertNotEqual(operations.operation_key(selected),self.key)
        command = operations.bridge_arguments(selected)['command']
        self.assertIn('= bugfix/scanner-facts-consumer',command)
        with self.assertRaises(operations.OperationError):
            operations.validated(dict(selected,branch='develop'))
        with self.assertRaises(operations.OperationError):
            operations.validated(dict(selected,branch='bugfix/x; false'))

    def test_lost_submit_response_is_reconciled_without_second_submission(self):
        self.remote.lose_ack = True
        self.assertEqual(self.tick()['status'],'unknown')
        self.assertEqual(len(self.remote.submissions),1)
        job_id = self.journal.read(self.key)[1]['windmill_job_id']
        self.remote.complete(job_id,self.spec)
        self.assertEqual(self.tick()['status'],'succeeded')
        self.assertEqual(len(self.remote.submissions),1)

    def test_unknown_missing_remote_job_is_not_blindly_resubmitted(self):
        self.remote.lose_ack = True
        self.tick()
        self.remote.jobs.clear()
        self.assertEqual(self.tick()['status'],'unknown')
        self.assertEqual(len(self.remote.submissions),1)

    def test_observation_outage_defers_prepared_work_without_claiming_submission(self):
        self.remote.offline = True
        result = self.tick()
        self.assertEqual(result['status'],'prepared')
        self.assertEqual(result['deferred'],'service-unavailable')
        self.assertEqual(self.remote.submissions,[])
        self.remote.offline = False
        self.assertEqual(self.tick()['status'],'submitted')

    def test_second_owner_cannot_create_duplicate_operation(self):
        other = dict(self.spec,owner='competing-worker')
        self.assertEqual(operations.operation_key(other),self.key)
        with self.assertRaisesRegex(operations.OperationError,'owner conflict'):
            self.journal.prepare(other)

    def test_claim_excludes_another_writer(self):
        with self.journal.claim(self.key):
            with self.assertRaisesRegex(operations.OperationError,'already owned'):
                self.tick()
        self.assertEqual(self.remote.submissions,[])

    def test_cancel_before_submission_does_not_start_a_job(self):
        self.journal.cancel(self.key)
        self.assertEqual(self.tick()['status'],'cancelled')
        self.assertEqual(self.remote.submissions,[])

    def test_cancel_targets_foo_backend_and_waits_for_termination(self):
        state = self.tick()
        self.journal.cancel(self.key)
        state = self.tick()
        self.assertEqual(state['status'],'cancel-requested')
        self.assertEqual(self.remote.submissions[-1][1],operations.bridge_arguments(self.spec,'cancel'))
        count = len(self.remote.submissions)
        self.tick()
        self.assertEqual(len(self.remote.submissions),count)
        self.remote.complete(state['windmill_job_id'],self.spec,'cancelled')
        self.assertEqual(self.tick()['status'],'cancelled')

    def test_foreign_remote_identity_is_quarantined(self):
        state = self.tick()
        self.remote.jobs[state['windmill_job_id']]['workspace_id'] = 'another-workspace'
        self.assertEqual(self.tick()['status'],'quarantined')

    def test_wrong_command_receipt_does_not_pass(self):
        state = self.tick()
        self.remote.complete(state['windmill_job_id'],self.spec)
        self.remote.jobs[state['windmill_job_id']]['result']['receipt']['command_sha256'] = '0'*64
        self.assertEqual(self.tick()['status'],'unknown')

    def test_authorization_refusal_does_not_choose_an_alternate_protocol(self):
        self.remote.refused = True
        self.assertEqual(self.tick()['status'],'refused')
        self.assertEqual(self.remote.submissions,[])
        self.remote.refused = False
        self.assertEqual(self.tick()['status'],'refused')
        self.assertEqual(self.remote.submissions,[])

    def test_failed_api_wrapper_recovers_business_failure_from_status_receipt(self):
        state = self.tick()
        job_id = state['windmill_job_id']
        self.remote.jobs[job_id].update(type='CompletedJob',success=False,result={'error':'business failed'})
        self.tick()
        observer_id,args = self.remote.submissions[-1]
        self.assertEqual(args,operations.bridge_arguments(self.spec,'status'))
        self.remote.complete(observer_id,self.spec,'failed')
        self.assertEqual(self.tick()['status'],'failed')
        self.assertEqual(len([a for _,a in self.remote.submissions if a['action']=='run']),1)

    def stale_observer(self):
        self.now = 1000
        self.clock = patch.object(operations.time, 'time', side_effect=lambda:self.now)
        self.clock.start()
        self.addCleanup(self.clock.stop)
        state = self.tick()
        self.tick()  # First actual running observation starts the durable grace.
        self.now += operations.WRAPPER_GRACE_SECONDS + 1
        stale = self.tick()
        self.assertTrue(stale['wrapper_stale'])
        observer_id,args = self.remote.submissions[-1]
        self.assertEqual(args, operations.bridge_arguments(self.spec,'status'))
        self.assertEqual(stale['windmill_job_id'], state['windmill_job_id'])
        return state['windmill_job_id'], observer_id

    def test_stale_running_wrapper_recovers_terminal_backend_without_computation_replay(self):
        original, observer = self.stale_observer()
        self.remote.complete(observer,self.spec)
        recovered = self.tick()
        self.assertEqual(recovered['status'],'succeeded')
        self.assertEqual(recovered['accepted_output_sha256'],self.spec['outputs'])
        self.assertEqual(self.remote.jobs[original]['type'],'QueuedJob')
        self.assertTrue(self.remote.jobs[original]['running'])
        self.assertEqual(len([a for _,a in self.remote.submissions if a['action']=='run']),1)
        self.assertEqual(len([a for _,a in self.remote.submissions if a['action']=='status']),1)
        before = copy.deepcopy(self.remote.submissions)
        self.assertEqual(self.tick(), recovered)
        self.assertEqual(self.remote.submissions,before)

    def test_grace_and_queue_never_authorize_early_backend_observation(self):
        state = self.tick()
        with patch.object(operations.time,'time',return_value=1000):
            self.tick()
        with patch.object(operations.time,'time',return_value=1000+operations.WRAPPER_GRACE_SECONDS-1):
            self.assertEqual(self.tick()['status'],'running')
        self.remote.jobs[state['windmill_job_id']]['running'] = False
        with patch.object(operations.time,'time',return_value=10000):
            self.assertEqual(self.tick()['status'],'queued')
        self.assertEqual(len(self.remote.submissions),1)

    def test_stale_backend_receipt_mismatch_or_incomplete_cleanup_stays_unknown(self):
        _,observer = self.stale_observer()
        self.remote.complete(observer,self.spec)
        valid = copy.deepcopy(self.remote.jobs[observer]['result'])
        for field,value in [('job_id','offmenu-'+'0'*48),('command_sha256','0'*64),('runner_sha256','0'*64),
                            ('capacity_policy_sha256','0'*64),('child_tree_gone',False),
                            ('reconcile_required',True)]:
            result = copy.deepcopy(valid)
            result['receipt'][field] = value
            self.remote.jobs[observer]['result'] = result
            state = self.tick()
            self.assertEqual(state['status'],'unknown',field)
            self.assertEqual(state['accepted_output_sha256'],{},field)
        self.assertEqual(len([a for _,a in self.remote.submissions if a['action']=='run']),1)

    def test_stale_observer_unavailable_or_missing_never_resubmits_computation(self):
        _,observer = self.stale_observer()
        before = copy.deepcopy(self.remote.submissions)
        self.remote.offline = True
        self.assertEqual(self.tick()['deferred'],'service-unavailable')
        self.remote.offline = False
        del self.remote.jobs[observer]
        self.assertEqual(self.tick()['status'],'unknown')
        self.assertEqual(self.remote.submissions,before)

    def test_live_backend_observation_rearms_grace_instead_of_poll_job_flood(self):
        _,observer = self.stale_observer()
        self.remote.complete(observer,self.spec)
        self.remote.jobs[observer]['result']['receipt']['status'] = 'running'
        self.assertEqual(self.tick()['status'],'running')
        before = copy.deepcopy(self.remote.submissions)
        self.now += 1
        self.tick()
        self.assertEqual(self.remote.submissions,before)
        self.now += operations.WRAPPER_GRACE_SECONDS
        self.tick()
        self.assertEqual(len(self.remote.submissions),len(before)+1)
        self.assertEqual(self.remote.submissions[-1][1]['action'],'status')

    def test_stale_cancel_keeps_original_cancel_and_accepts_only_stopped_backend(self):
        original,observer = self.stale_observer()
        self.journal.cancel(self.key)
        self.remote.complete(observer,self.spec,'cancelled')
        state = self.tick()
        self.assertEqual(state['status'],'cancelled')
        self.assertTrue(state['cancel_requested'])
        self.assertEqual(state['windmill_job_id'],original)
        self.assertEqual(len([a for _,a in self.remote.submissions if a['action']=='cancel']),1)
        self.assertEqual(len([a for _,a in self.remote.submissions if a['action']=='run']),1)

    def test_stale_status_submit_refusal_is_unknown_effect_not_approval(self):
        state = self.tick()
        with patch.object(operations.time,'time',return_value=1000):
            self.tick()
        self.remote.refused = True
        with patch.object(operations.time,'time',return_value=1000+operations.WRAPPER_GRACE_SECONDS+1):
            result = self.tick()
        self.assertEqual(result['status'],'unknown')
        self.assertNotIn('approval',result['status'])
        self.assertEqual(result['windmill_job_id'],state['windmill_job_id'])
        self.assertEqual(len(self.remote.submissions),1)

    def test_output_and_profile_schema_reject_private_paths_and_shell_commands(self):
        for outputs in ({'data/private.json':'a'*64},{'tests/../data/private.json':'a'*64}):
            with self.assertRaises(operations.OperationError):
                self.journal.prepare(dict(self.spec,outputs=outputs))
        with self.assertRaises(operations.OperationError):
            self.journal.prepare(dict(self.spec,profile='unreviewed shell command'))


    def compact_transport(self):
        from windmill_dispatcher import compact_job
        inspect = self.remote.inspect
        async def compact(job_id):
            value = await inspect(job_id)
            if value is None:
                return None
            value.setdefault('success',None)
            return compact_job(value)
        self.remote.inspect = compact

    def failed_compact_wrapper(self):
        self.compact_transport()
        state = self.tick()
        original = state['windmill_job_id']
        remote = self.remote.jobs[original]
        del remote['running']
        remote.update(type='CompletedJob',success=False,
                      result={'error':{'message':'SENSITIVE arbitrary wrapper error'}})
        from windmill_dispatcher import compact_job
        compact = compact_job(remote)
        self.assertEqual(compact['result'],{'classification':'no-authoritative-receipt'})
        self.assertTrue(operations.observation_matches(
            compact,original,operations.bridge_arguments(self.spec)))
        self.tick()
        observer,args = self.remote.submissions[-1]
        self.assertEqual(args,operations.bridge_arguments(self.spec,'status'))
        self.assertNotEqual(observer,original)
        return original,observer

    def test_compact_failed_completed_schema_recovers_original_terminal_receipt(self):
        original,observer = self.failed_compact_wrapper()
        self.remote.complete(observer,self.spec)
        del self.remote.jobs[observer]['running']
        state = self.tick()
        self.assertEqual(state['status'],'succeeded')
        self.assertEqual(state['windmill_job_id'],original)
        self.assertEqual(state.get('accepted_output_sha256',{}),self.spec['outputs'])
        self.assertEqual([a['action'] for _,a in self.remote.submissions],['run','status'])
        with self.journal.db() as db:
            events = str(db.execute('SELECT event FROM events').fetchall())
        self.assertNotIn('SENSITIVE',json.dumps(state)+events)

    def test_compact_error_recovery_preserves_backend_failure(self):
        _,observer = self.failed_compact_wrapper()
        self.remote.complete(observer,self.spec,'failed',wrapper_success=True)
        self.assertEqual(self.tick()['status'],'failed')
        self.assertEqual([a['action'] for _,a in self.remote.submissions],['run','status'])

    def test_compact_error_recovery_preserves_backend_cancellation(self):
        _,observer = self.failed_compact_wrapper()
        self.journal.cancel(self.key)
        self.remote.complete(observer,self.spec,'cancelled')
        state = self.tick()
        self.assertEqual(state['status'],'cancelled')
        self.assertTrue(state['cancel_requested'])
        self.assertEqual(state.get('accepted_output_sha256',{}),{})
        self.assertEqual([a['action'] for _,a in self.remote.submissions],['run','status'])

    def test_compact_malformed_claimed_receipt_cannot_trigger_status_recovery(self):
        self.compact_transport()
        state = self.tick()
        original = state['windmill_job_id']
        self.remote.complete(original,self.spec)
        valid = copy.deepcopy(self.remote.jobs[original]['result'])
        for receipt in (None, {'status':'succeeded'},
                        dict(valid['receipt'],job_id='offmenu-'+'0'*48),
                        dict(valid['receipt'],command_sha256='malformed')):
            self.remote.jobs[original]['result'] = dict(valid,receipt=receipt)
            state = self.tick()
            self.assertEqual(state['status'],'unknown')
            self.assertEqual(state.get('accepted_output_sha256',{}),{})
            self.assertEqual(len(self.remote.submissions),1)

    def test_compact_error_recovery_requires_bound_receipt_and_cleanup(self):
        _,observer = self.failed_compact_wrapper()
        self.remote.complete(observer,self.spec)
        valid = copy.deepcopy(self.remote.jobs[observer]['result'])
        for field,value in [('job_id','offmenu-'+'0'*48),('command_sha256','0'*64),
                            ('runner_sha256','0'*64),('capacity_policy_sha256','0'*64),
                            ('child_tree_gone',False),('reconcile_required',True)]:
            result = copy.deepcopy(valid)
            result['receipt'][field] = value
            self.remote.jobs[observer]['result'] = result
            state = self.tick()
            self.assertIn(state['status'],('unknown','quarantined'),field)
            self.assertEqual(state.get('accepted_output_sha256',{}),{},field)
        self.assertEqual([a['action'] for _,a in self.remote.submissions],['run','status'])

    def test_compact_error_recovery_unavailable_or_refused_never_resubmits(self):
        _,observer = self.failed_compact_wrapper()
        before = copy.deepcopy(self.remote.submissions)
        self.remote.offline = True
        self.assertEqual(self.tick()['deferred'],'service-unavailable')
        self.remote.offline = False
        inspect = self.remote.inspect
        async def refused(job_id):
            if job_id == observer:
                raise operations.RequestRefused('SENSITIVE refused')
            return await inspect(job_id)
        self.remote.inspect = refused
        state = self.tick()
        self.assertEqual(state['status'],'unknown')
        self.assertEqual(state.get('accepted_output_sha256',{}),{})
        self.assertEqual(self.remote.submissions,before)

    def test_compact_primary_observation_requires_original_persisted_args(self):
        self.compact_transport()
        state = self.tick()
        self.remote.complete(state['windmill_job_id'],self.spec)
        self.assertEqual(self.tick()['status'],'succeeded')
        self.assertEqual(len(self.remote.submissions),1)

    def test_compact_cancel_and_status_preserve_original_job_and_cleanup_gates(self):
        self.compact_transport()
        original, observer = self.stale_observer()
        self.journal.cancel(self.key)
        self.tick()  # Creates the original cancellation intent.
        self.tick()  # Binds the compact cancel observation without resubmission.
        self.remote.complete(observer,self.spec,'cancelled')
        self.remote.jobs[observer]['result']['receipt']['child_tree_gone'] = False
        self.assertEqual(self.tick()['status'],'unknown')
        self.remote.jobs[observer]['result']['receipt']['child_tree_gone'] = True
        self.assertEqual(self.tick()['status'],'cancelled')
        self.assertEqual(self.journal.read(self.key)[1]['windmill_job_id'],original)
        self.assertEqual([args['action'] for _,args in self.remote.submissions],['run','status','cancel'])

    def test_compact_binding_rejects_conflicts_and_missing_version_or_digest(self):
        from windmill_dispatcher import compact_job
        state = self.tick()
        self.remote.complete(state['windmill_job_id'],self.spec)
        remote = self.remote.jobs[state['windmill_job_id']]
        good = compact_job(remote)
        expected = operations.bridge_arguments(self.spec)
        self.assertTrue(operations.observation_matches(good,state['windmill_job_id'],expected))
        self.assertTrue(operations.observation_matches(remote,state['windmill_job_id'],expected))
        variants = [dict(good,args=expected),dict(good,args_sha256='0'*64),
            dict(good,args_sha256='a'*63),dict(good,inspect_version='offmenu-inspect/99'),
            dict(good,id=state['cancel_job_id']),dict(good,workspace_id='foreign'),
            dict(good,script_path='foreign'),dict(good,logs='SECRET'),
            dict(remote,args_sha256=good['args_sha256'])]
        for field in ('inspect_version','args_sha256'):
            value = dict(good);del value[field];variants.append(value)
        for value in variants:
            self.assertFalse(operations.observation_matches(value,state['windmill_job_id'],expected))
        async def conflict(job_id):
            return dict(good,args_sha256='0'*64)
        self.remote.inspect = conflict
        state = self.tick()
        self.assertEqual(state['status'],'quarantined')
        self.assertEqual(state['diagnosis'],{'stage':'observation-binding',
                                            'exception_class':'ObservationBindingError'})
        self.assertEqual(len(self.remote.submissions),1)

    def test_compact_status_and_cancel_conflicts_are_quarantined(self):
        from windmill_dispatcher import compact_job
        original,observer = self.stale_observer()
        self.remote.complete(observer,self.spec)
        inspect = self.remote.inspect
        async def conflict(job_id):
            value = await inspect(job_id)
            if value is not None:
                value.setdefault('success',None)
                value = compact_job(value)
                if job_id == observer:
                    value['args_sha256'] = operations.digest(operations.bridge_arguments(self.spec))
            return value
        self.remote.inspect = conflict
        self.assertEqual(self.tick()['status'],'quarantined')
        self.assertEqual(len([a for _,a in self.remote.submissions if a['action']=='run']),1)

    def test_compact_cancel_digest_conflict_does_not_replace_cancel_intent(self):
        from windmill_dispatcher import compact_job
        self.tick()
        self.journal.cancel(self.key)
        state = self.tick()
        before = copy.deepcopy(self.remote.submissions)
        inspect = self.remote.inspect
        async def conflict(job_id):
            value = await inspect(job_id)
            if value is not None:
                value.setdefault('success',None)
                value = compact_job(value)
                if job_id == state['cancel_job_id']:
                    value['args_sha256'] = '0'*64
            return value
        self.remote.inspect = conflict
        self.assertEqual(self.tick()['status'],'quarantined')
        self.assertEqual(self.remote.submissions,before)
        self.assertTrue(self.journal.read(self.key)[1]['cancel_intent'])

    def test_compact_wrapper_success_without_receipt_never_accepts(self):
        self.compact_transport()
        state = self.tick()
        self.remote.jobs[state['windmill_job_id']].update(type='CompletedJob',running=False,success=True)
        observed = self.tick()
        self.assertNotEqual(observed['status'],'succeeded')
        self.assertEqual(self.remote.submissions[-1][1]['action'],'status')
        self.assertEqual(len([a for _,a in self.remote.submissions if a['action']=='run']),1)

    def test_safe_diagnostics_survive_reopen_without_exception_text_or_arbitrary_class(self):
        class SecretError(RuntimeError):
            pass
        errors = [operations.RPCIdentityError,operations.ToolResultIncompleteError,
            operations.ToolResultTruncatedError,operations.ObservationBindingError,
            operations.TransportUnavailable,operations.RequestRefused,SecretError]
        for kind in errors:
            async def fail(job_id):
                raise kind('SECRET environment response credentials')
            self.remote.inspect = fail
            # Keep effects unknown, including refusals; do not admit fresh submission.
            _,state = self.journal.read(self.key)
            state['status'] = 'unknown'
            self.journal.save(self.key,state,'test-unknown')
            result = self.tick()
            saved = operations.Journal(self.root).read(self.key)[1]
            self.assertEqual(saved['diagnosis'],operations.safe_diagnosis(kind()))
            with self.journal.db() as db:
                events = str(db.execute('SELECT event FROM events').fetchall())
            self.assertNotIn('SECRET',json.dumps(saved)+events)
            self.assertNotIn('SecretError',json.dumps(saved)+events)
        self.assertEqual(self.remote.submissions,[])


class PublisherProfileTests(unittest.TestCase):
    def spec(self, **changes):
        outputs = {'tools/delivery/example.py':'a'*64}
        spec = dict(version=3,issue='UIF-119',
            issue_id='00000000-0000-5000-8000-000000000119',stage='validate',
            owner='synthetic-owner',branch='feature/synthetic-reviewed',
            head='b'*40,base='c'*40,policy_sha256='d'*64,
            acceptance_sha256='e'*64,runner_sha256='f'*64,executor_sha256='1'*64,
            control_sha256='2'*64,profile='protected-publisher-bootstrap',outputs=outputs,
            workspace='/offmenu/data/.offmenu-platform/workspaces/synthetic-reviewed-source',
            local_source_root='/synthetic/source',
            execution=dict(task_fit='deterministic reviewed source validation',
                requested_model=None,requested_effort=None,provider_route='none',
                resolved_model=None,resolution_status='not-applicable'),
            origin=dict(kind='reviewed-source-v1',admission_sha256='e'*64,
                review_sha256='3'*64,author='synthetic-author',authors=['synthetic-author'],
                provenance=[dict(path='/synthetic/provenance.json',sha256='4'*64,
                    author='synthetic-author',owner='synthetic-author',session='synthetic-session',
                    source_head='5'*40,contribution_head='6'*40,outputs=outputs,
                    path_mapping={name:name for name in outputs},derivation=None)]))
        return dict(spec,**changes)

    def oracle(self, spec):
        return shlex.split(operations.bridge_arguments(operations.validated(spec))['command'])[14]

    def test_fixed_enum_binds_identity_and_rejects_candidate_overrides(self):
        spec = self.spec()
        self.assertIs(operations.validated(spec),spec)
        current = dict(spec,profile='current-journal-focused')
        self.assertNotEqual(operations.operation_key(spec),operations.operation_key(current))
        self.assertNotEqual(operations.bridge_arguments(spec)['job_id'],
                            operations.bridge_arguments(current)['job_id'])
        for changes in ({'profile':'protected-publisher-bootstrap-other'},
                        {'profile':'protected-publisher-bootstrap.test_one'},
                        {'argv':['arbitrary']}, {'modules':['arbitrary']},
                        {'test_selectors':['test_protected_owner_install']},
                        {'environment':{'PYTHONPATH':'/tmp'}}):
            with self.subTest(changes=changes),self.assertRaises(operations.OperationError):
                operations.validated(dict(spec,**changes))

    def test_repaired_current_oracle_requires_new_executor_pin_for_new_operation(self):
        # Synthetic identities retain the spec-derived key, but the stricter
        # ancestry oracle changes command bytes. Real admission must bind the
        # updated executor hash; it may never reuse a historical operation.
        spec = self.spec(profile='current-journal-focused')
        self.assertEqual(operations.operation_key(spec),
                         '9c7dadcf419fae6ef68cf47ef0f64ab93445722fa3488f7aedfe05ccc662d4c8')
        self.assertEqual(hashlib.sha256(operations.bridge_arguments(spec)['command'].encode()).hexdigest(),
                         '4d7f1ffe68f20efea8d0a9793053873ece7ef124c3c4aa18c37c8b38b5cca8ab')
        changed = dict(spec,executor_sha256='9'*64)
        self.assertNotEqual(operations.operation_key(spec),operations.operation_key(changed))

    def test_control_archive_and_three_baseline_tests_are_identical(self):
        spec = self.spec()
        current = self.oracle(dict(spec,profile='current-journal-focused'))
        publisher = self.oracle(spec)
        # All archive selection, hash verification and materialization bytes
        # precede this loop and must remain exactly the current v3 contract.
        self.assertEqual(current.split(' for selected,modules in ')[0],
                         publisher.split(' for selected,modules in ')[0])
        loops = [next(node for node in ast.walk(ast.parse(body))
                      if isinstance(node,ast.For) and isinstance(node.target,ast.Tuple))
                 for body in (current,publisher)]
        baseline = [ast.literal_eval(loop.iter.elts[0].elts[1]) for loop in loops]
        expected = ['test_stokowski_operations.OperationRecoveryTests.'+name for name in (
            'test_unknown_missing_remote_job_is_not_blindly_resubmitted',
            'test_second_owner_cannot_create_duplicate_operation',
            'test_cancel_before_submission_does_not_start_a_job')]
        self.assertEqual(baseline,[expected,expected])
        candidate = loops[1].iter.elts[1].value
        self.assertEqual(ast.literal_eval(candidate.generators[0].iter),(
            'test_protected_owner_install','test_github_app_capture',
            'test_protected_publisher_install','test_stokowski_operations',
            'test_stokowski_dispatcher'))

    def test_each_candidate_suite_requires_positive_successful_unskipped_tests(self):
        # Execute only the generated oracle with synthetic tar/suite fixtures.
        # No candidate helper imports, actual validation job or transport runs.
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            archive = io.BytesIO()
            with tarfile.open(fileobj=archive,mode='w') as bundle:
                for module in operations.REVIEWED_TESTS:
                    member = tarfile.TarInfo('tests/delivery/'+module+'.py')
                    member.size = 0
                    bundle.addfile(member,io.BytesIO())
            archive = archive.getvalue()
            body = self.oracle(self.spec(workspace='/offmenu/data/.offmenu-platform/workspaces/synthetic-reviewed-source',
                control_sha256=hashlib.sha256(archive).hexdigest()))
            body = body.replace("root=pathlib.Path("+repr(self.spec()['workspace'])+")",
                                'root=pathlib.Path('+repr(str(root))+')')

            def passing(): pass
            def failing(): raise AssertionError('synthetic failure')
            def skipped(): raise unittest.SkipTest('synthetic skip')

            for bad_index,kind in [(None,'pass')]+[(index,kind) for index in range(1,6)
                                                  for kind in ('empty','failure','skip')]:
                loaded = []
                def load(names):
                    loaded.append(names)
                    selected = kind if len(loaded)-1 == bad_index else 'pass'
                    return unittest.TestSuite([] if selected == 'empty' else [
                        unittest.FunctionTestCase({'pass':passing,'failure':failing,'skip':skipped}[selected])])
                def run(argv, **kwargs):
                    self.assertEqual(argv[:2],[sys.executable,'-c'])
                    self.assertEqual(kwargs,dict(cwd=root,check=True))
                    previous = sys.path[:]
                    try:
                        exec(compile(argv[2],'<synthetic-suite>','exec'),{})
                    finally:
                        sys.path[:] = previous
                with self.subTest(bad_index=bad_index,kind=kind), \
                     patch('subprocess.check_output',return_value=archive) as control, \
                     patch('subprocess.run',side_effect=run), \
                     patch.object(unittest.TestLoader,'loadTestsFromNames',side_effect=load), \
                     redirect_stderr(io.StringIO()):
                    if bad_index is None:
                        exec(compile(body,'<synthetic-oracle>','exec'),{})
                        self.assertEqual(loaded[1:],[(name,) for name in operations.PUBLISHER_TESTS])
                    else:
                        with self.assertRaises(AssertionError):
                            exec(compile(body,'<synthetic-oracle>','exec'),{})
                        self.assertEqual(len(loaded),bad_index+1)
                    self.assertEqual(control.call_args.args[0],['git','-C',str(root),'archive',
                        'c'*40,'tests/delivery/test_stokowski_operations.py',
                        'tests/delivery/test_stokowski_current_dispatch.py'])


class DetachedContributionTests(unittest.TestCase):
    spec = PublisherProfileTests.spec
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        def git(*args):
            return subprocess.check_output(['git','-C',str(self.root),
                '-c','user.name=Synthetic','-c','user.email=synthetic@example.invalid',
                *args],stderr=subprocess.PIPE).decode().strip()
        self.git = git
        git('init','-b','feature/synthetic-reviewed')
        (self.root/'README').write_text('synthetic baseline\n')
        git('add','README'); git('commit','-m','base')
        self.base = git('rev-parse','HEAD')
        self.name = 'tools/delivery/example.py'
        path = self.root/self.name
        path.parent.mkdir(parents=True)
        path.write_text('value = 1\n')
        git('add',self.name); git('commit','-m','native contribution')
        self.contribution = git('rev-parse','HEAD')
        self.output = hashlib.sha256(path.read_bytes()).hexdigest()
        tree = git('rev-parse','HEAD^{tree}')
        self.detached = git('commit-tree',tree,'-p',self.base,'-m','reviewed squash')

    def selected(self, detached=True, transformed=False, derivation=True):
        head = self.detached if detached else self.contribution
        self.git('update-ref','refs/heads/feature/synthetic-reviewed',head)
        if transformed:
            (self.root/self.name).write_text('value = 2\n')
            self.git('add',self.name); self.git('commit','-m','reviewed correction')
            head = self.git('rev-parse','HEAD')
        outputs = {self.name:hashlib.sha256((self.root/self.name).read_bytes()).hexdigest()}
        spec = self.spec(head=head,base=self.base,outputs=outputs,local_source_root=str(self.root))
        ref = spec['origin']['provenance'][0]
        ref.update(source_head=self.base,contribution_head=self.contribution,
                   outputs={self.name:self.output})
        if derivation:
            ref['derivation'] = dict(owner=ref['owner'],contribution_head=self.contribution,
                path_mapping=ref['path_mapping'],head=head,outputs=outputs,
                review_sha256=spec['origin']['review_sha256'],reason='Independently reviewed squash or correction')
        return spec

    def run_check(self, spec, success):
        operations.validated(spec)
        result = subprocess.run([sys.executable,'-c',operations.reviewed_check_code(spec,self.root)],
                                capture_output=True,text=True)
        self.assertEqual(result.returncode == 0,success,result.stderr)

    def test_detached_identical_bytes_need_exact_derivation(self):
        self.run_check(self.selected(),True)
        self.run_check(self.selected(derivation=False),False)

    def test_attached_identical_bytes_reject_unnecessary_derivation(self):
        self.run_check(self.selected(detached=False,derivation=False),True)
        self.run_check(self.selected(detached=False),False)

    def test_attached_and_detached_changed_bytes_keep_review_requirement(self):
        for detached in (False,True):
            with self.subTest(detached=detached):
                self.run_check(self.selected(detached=detached,transformed=True),True)

    def test_detached_derivation_fields_are_exact(self):
        spec = self.selected()
        ref = spec['origin']['provenance'][0]
        for field,value in (('owner','other'),('head','1'*40),('contribution_head','1'*40),
                ('path_mapping',{self.name:'tools/other.py'}),('outputs',{self.name:'1'*64}),
                ('review_sha256','1'*64),('reason','')):
            changed = copy.deepcopy(spec)
            changed['origin']['provenance'][0]['derivation'][field] = value
            with self.subTest(field=field), self.assertRaises(operations.OperationError):
                operations.validated(changed)
        # Even structurally valid claims cannot replace historical source ancestry.
        ref['source_head'] = self.detached
        self.run_check(spec,False)


if __name__ == '__main__':
    unittest.main()
