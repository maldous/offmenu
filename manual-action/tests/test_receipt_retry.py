"""Receipt recovery proofs using fake clocks and generated local bare Git only."""
import contextlib
import copy
import importlib.util
import io
from pathlib import Path
import sys
import types
import unittest
from unittest import mock

PACKAGE=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(PACKAGE))
spec=importlib.util.spec_from_file_location('retry_batch_fixture',PACKAGE/'tests/test_receipt_batch.py')
fixture=importlib.util.module_from_spec(spec);spec.loader.exec_module(fixture)
m=fixture.m
import receipt_branch as branch
import receipt_retry as retry


class Clock:
    def __init__(self):self.now=0
    def __call__(self):return self.now
    def advance(self,seconds=60):self.now+=seconds


class RetryPolicyTests(unittest.TestCase):
    def test_monotonic_backoff_and_four_retry_ceiling(self):
        clock=Clock();policy=retry.ReceiptRetry(clock=clock);calls=[]
        def failed():calls.append(clock());raise RuntimeError('git_push_failed_local_work_preserved')
        for point in (0,59,60,179,180,419,420,899,900,10000):
            clock.now=point;policy.attempt(failed)
        self.assertEqual(calls,[0,60,180,420,900]);self.assertEqual(policy.retries,4);self.assertTrue(policy.pending)
    def test_success_never_resets_invocation_retry_budget(self):
        clock=Clock();policy=retry.ReceiptRetry(clock=clock,max_retries=1)
        fail=mock.Mock(side_effect=RuntimeError('git_fetch_failed_local_work_preserved'))
        policy.attempt(fail);clock.advance();self.assertTrue(policy.attempt(lambda:False))
        self.assertFalse(policy.pending);policy.attempt(fail);clock.advance(10000)
        self.assertFalse(policy.attempt(fail));self.assertEqual(fail.call_count,2);self.assertEqual(policy.retries,1)
    def test_nontransport_failure_latches_and_interrupt_propagates(self):
        for error in (RuntimeError('receipt_branch_diverged_local_commits_and_spool_preserved'),OSError('local I/O')):
            policy=retry.ReceiptRetry();operation=mock.Mock(side_effect=error)
            policy.attempt(operation);policy.attempt(operation);operation.assert_called_once();self.assertTrue(policy.blocked)
        policy=retry.ReceiptRetry();operation=mock.Mock(side_effect=KeyboardInterrupt)
        with self.assertRaises(KeyboardInterrupt):policy.attempt(operation)
        self.assertFalse(policy.retry_pending);self.assertFalse(policy.blocked);self.assertEqual(policy.retries,0)


class ReceiptRecoveryTests(unittest.TestCase):
    def setUp(self):
        self.case=fixture.ReceiptBatchTests('test_twenty_old_receipts_one_tree_commit_push_and_checkout_unchanged')
        self.case.setUp();self.runner=self.case.runner;self.runner.receipt_transport='isolated-branch-v1'
        self.clock=Clock();self.policy=retry.ReceiptRetry(clock=self.clock)
        self.directory=self.runner.state/'ingest-pending';self.head=self.case.original_git('rev-parse','HEAD')[1]
        self.index=(self.case.case.root/'.git/index').read_bytes()
    def tearDown(self):
        self.assertEqual(self.case.original_git('rev-parse','HEAD')[1],self.head)
        self.assertEqual((self.case.case.root/'.git/index').read_bytes(),self.index)
        self.case.tearDown()
    def spools(self,items):
        paths=[]
        for value,supplement in items:
            if supplement:
                ref=value['ingest']['evidence_ref'];self.runner.durable_local_json(self.runner.state/'ingest-evidence'/(ref['sha256']+'.json'),supplement)
            path=self.directory/Path(m.receipt_relpath(value)).name
            self.runner.durable_local_json(path,{'sha256':m.digest(m.canonical(value)),'receipt':value});paths.append(path)
        return paths
    def flush(self):
        with contextlib.redirect_stdout(io.StringIO()):
            return self.runner.flush_receipt_spools(self.policy,(self.directory,))
    def fail_one_push(self,*,succeeded=False,error=None):
        left=[True]
        def git(*args,**kwargs):
            if args[0]=='push' and left[0]:
                left[0]=False
                if succeeded:self.case.tracked_git(*args,**kwargs)
                else:self.case.calls.append(args)
                raise error or m.Stop('git_push_failed_local_work_preserved')
            return self.case.tracked_git(*args,**kwargs)
        self.runner.git=git
    def test_response_lost_after_success_exact_dedup_no_second_write(self):
        items=self.case.batch();paths=self.spools(items);before=[p.read_bytes() for p in paths]
        self.fail_one_push(succeeded=True);self.assertFalse(self.flush())
        self.assertEqual([p.read_bytes() for p in paths],before);local=self.case.original_git('rev-parse',branch.LOCAL_REF)[1]
        self.clock.advance();self.case.calls.clear();self.assertTrue(self.flush())
        self.assertTrue(all(not p.exists() for p in paths));self.assertEqual(self.case.count('push'),0);self.assertEqual(self.case.count('commit-tree'),0)
        self.assertEqual(self.case.count('ls-remote'),1);self.assertEqual(self.case.count('fetch'),1)
        self.assertEqual(self.case.original_git('rev-parse',branch.LOCAL_REF)[1],local);self.case.assert_exact_blobs(branch.LOCAL_REF,items)
    def test_nonwrite_failure_pushes_same_commit_after_fresh_absence_proof(self):
        items=self.case.batch();paths=self.spools(items);self.fail_one_push();self.flush()
        local=self.case.original_git('rev-parse',branch.LOCAL_REF)[1];self.clock.advance();self.case.calls.clear();self.assertTrue(self.flush())
        self.assertEqual(self.case.count('commit-tree'),0);self.assertEqual(self.case.count('push'),1)
        self.assertLess(next(i for i,c in enumerate(self.case.calls) if c[0]=='ls-remote'),next(i for i,c in enumerate(self.case.calls) if c[0]=='push'))
        self.assertEqual(self.case.original_git('rev-parse',branch.LOCAL_REF)[1],local);self.assertTrue(all(not p.exists() for p in paths))
    def other_publisher(self):
        editor=self.case.case.case.case.editor();other=type(self.runner)(editor)
        return branch.ReceiptBranchPublisher(other,validate=m.validate_runtime_receipt,relpath=m.receipt_relpath,
            canonical=m.canonical,fail=m.Stop,validate_supplement=m.validate_supplement,supplement_relpath=m.supplement_relpath)
    def test_remote_compatible_advance_fast_forwards_without_duplicate_push(self):
        items=[self.case.receipt(1,evidence=True)];paths=self.spools(items);self.fail_one_push(succeeded=True);self.flush()
        publisher=self.other_publisher();publisher.publish(*self.case.receipt(2))
        remote=self.case.case.git(self.case.case.case.case.remote,'rev-parse',branch.LOCAL_REF).encode()+b'\n'
        self.clock.advance();self.case.calls.clear();self.assertTrue(self.flush())
        self.assertEqual(self.case.original_git('rev-parse',branch.LOCAL_REF)[1],remote);self.assertFalse(paths[0].exists())
        self.assertEqual(self.case.count('push'),0);self.assertEqual(self.case.count('commit-tree'),0)
    def test_divergence_refused_with_commits_and_spools_preserved(self):
        seed=self.case.receipt(1);self.case.publisher().publish(*seed)
        items=[self.case.receipt(2)];paths=self.spools(items);self.fail_one_push();self.flush()
        local=self.case.original_git('rev-parse',branch.LOCAL_REF)[1];before=paths[0].read_bytes()
        self.other_publisher().publish(*self.case.receipt(3))
        self.clock.advance();self.case.calls.clear();self.assertFalse(self.flush())
        self.assertTrue(self.policy.blocked);self.assertEqual(self.case.count('push'),0)
        self.assertEqual(self.case.original_git('rev-parse',branch.LOCAL_REF)[1],local);self.assertEqual(paths[0].read_bytes(),before)
    def test_recovery_exact_timestamp_conflict_is_not_legacy_compatibility(self):
        item=self.case.receipt(1);self.case.publisher().publish(*item)
        altered=copy.deepcopy(item);altered[0]['observed_at']='2026-10-22T00:00:00Z';paths=self.spools([altered])
        before=paths[0].read_bytes();self.case.calls.clear();self.assertFalse(self.flush())
        self.assertTrue(self.policy.blocked);self.assertEqual(self.case.count('push'),0);self.assertEqual(paths[0].read_bytes(),before)
        self.case.assert_exact_blobs(branch.LOCAL_REF,[item])
        # The old single-receipt API deliberately keeps its original compatibility.
        self.case.publisher().publish(*altered);self.case.assert_exact_blobs(branch.LOCAL_REF,[item])
    def test_changed_local_canonical_cache_is_not_silently_discarded(self):
        original=self.case.receipt(1);self.runner.prepare_isolated_ingest_receipt(original[0])
        changed=copy.deepcopy(original);changed[0]['observed_at']='2026-10-22T00:00:00Z';paths=self.spools([changed])
        self.case.calls.clear();self.assertFalse(self.flush());self.assertTrue(self.policy.blocked)
        self.assertTrue(paths[0].exists());self.assertEqual(self.case.count('push'),0)
    def test_changed_payload_same_path_refused_before_new_spool_and_on_recovery(self):
        original=self.case.receipt(1);self.runner.prepare_isolated_ingest_receipt(original[0])
        self.case.publisher().publish(*original)
        changed=copy.deepcopy(original);changed[0]['implementation_sha256']='e'*64
        self.assertEqual(m.receipt_relpath(changed[0]),m.receipt_relpath(original[0]))
        with self.assertRaisesRegex(m.Stop,'exact_bytes_conflict'):
            self.runner.reuse_receipt_timestamp(changed[0])
        paths=self.spools([changed]);raw=paths[0].read_bytes();self.case.calls.clear()
        self.assertFalse(self.flush());self.assertTrue(self.policy.blocked)
        self.assertEqual(self.case.count('push'),0);self.assertEqual(paths[0].read_bytes(),raw)
        self.case.assert_exact_blobs(branch.LOCAL_REF,[original])
    def test_new_checkpoints_remain_durable_during_backoff_then_backlog_recovers(self):
        first=self.case.receipt(1);paths=self.spools([first]);self.fail_one_push();self.flush();calls=len(self.case.calls)
        paths+=self.spools([self.case.receipt(2)]);self.clock.advance(59);self.assertFalse(self.flush())
        self.assertEqual(len(self.case.calls),calls);self.assertTrue(all(p.exists() for p in paths))
        self.clock.advance(1);self.assertTrue(self.flush());self.assertFalse(self.policy.pending);self.assertTrue(all(not p.exists() for p in paths))
    def test_bounded_backlog_count_bytes_and_no_complete_spool_sort(self):
        items=[self.case.receipt(i) for i in range(7)];paths=self.spools(items)
        with mock.patch.object(retry,'MAX_BATCH_RECEIPTS',3):
            self.assertTrue(self.flush());self.assertTrue(self.policy.pending);self.assertEqual(sum(p.exists() for p in paths),4)
            self.assertTrue(self.flush());self.assertEqual(sum(p.exists() for p in paths),1)
            self.assertTrue(self.flush());self.assertFalse(self.policy.pending)
        paths=self.spools(items);limit=len(m.canonical(items[0][0]))*2
        with mock.patch.object(retry,'MAX_BATCH_BYTES',limit):
            self.assertTrue(self.flush());self.assertEqual(sum(p.exists() for p in paths),5);self.assertTrue(self.policy.pending)
    def test_retry_exhaustion_preserves_backlog_and_local_commit(self):
        paths=self.spools([self.case.receipt(1,evidence=True)])
        def git(*args,**kwargs):
            if args[0]=='push':
                self.case.calls.append(args);raise m.Stop('git_push_failed_local_work_preserved')
            return self.case.tracked_git(*args,**kwargs)
        self.runner.git=git
        for point in (0,60,180,420,900):self.clock.now=point;self.assertFalse(self.flush())
        local=self.case.original_git('rev-parse',branch.LOCAL_REF)[1];count=len(self.case.calls)
        paths+=self.spools([self.case.receipt(2)]);self.clock.now=100000;self.assertFalse(self.flush())
        self.assertEqual(len(self.case.calls),count);self.assertEqual(self.case.count('commit-tree'),1)
        self.assertEqual(self.case.count('push'),5);self.assertEqual(self.policy.retries,4)
        self.assertTrue(all(p.exists() for p in paths));self.assertEqual(self.case.original_git('rev-parse',branch.LOCAL_REF)[1],local)
    def test_failed_fresh_remote_proof_never_acknowledges_or_replays_write(self):
        paths=self.spools([self.case.receipt(1,evidence=True)]);self.fail_one_push(succeeded=True);self.flush()
        before=paths[0].read_bytes()
        def unreadable(*args,**kwargs):
            if args[0]=='ls-remote':
                self.case.calls.append(args);raise m.Stop('git_ls_remote_failed_local_work_preserved')
            return self.case.tracked_git(*args,**kwargs)
        self.runner.git=unreadable;self.clock.advance();self.case.calls.clear();self.assertFalse(self.flush())
        self.assertEqual(self.case.count('push'),0);self.assertEqual(paths[0].read_bytes(),before)
        self.runner.git=self.case.tracked_git;self.clock.advance(120);self.assertTrue(self.flush())
        self.assertEqual(self.case.count('push'),0);self.assertFalse(paths[0].exists())
    def test_interruption_keeps_local_commit_and_spools_without_retry(self):
        paths=self.spools([self.case.receipt(1,evidence=True)]);before=paths[0].read_bytes()
        self.fail_one_push(error=KeyboardInterrupt())
        with self.assertRaises(KeyboardInterrupt):self.flush()
        self.assertEqual(paths[0].read_bytes(),before);self.assertFalse(self.policy.retry_pending);self.assertEqual(self.policy.retries,0)
        self.assertEqual(self.case.count('commit-tree'),1)


class RunnerRecoveryTests(unittest.TestCase):
    def recover_stage(self,case,runner,engine_method,work_counter):
        clock=Clock();policy=retry.ReceiptRetry(clock=clock);runner.receipt_retry_policy=lambda:policy
        engine=getattr(runner,engine_method)();original_run=engine.run_prepared
        def run(prepared,report_callback):
            def checkpoint(report):
                if report['status']!='running':clock.advance()
                report_callback(report)
            return original_run(prepared,checkpoint)
        engine.run_prepared=run;setattr(runner,engine_method,lambda:engine)
        original_git=runner.git;failed=[False];pushes=[]
        def git(*args,**kwargs):
            if args[0]=='push':
                pushes.append(args)
                if not failed[0]:failed[0]=True;raise m.Stop('git_push_failed_local_work_preserved')
            return original_git(*args,**kwargs)
        runner.git=git;head=original_git('rev-parse','HEAD')[1]
        with contextlib.redirect_stdout(io.StringIO()):self.assertEqual(runner.run_plan(),0)
        self.assertEqual(work_counter(),1);self.assertEqual(policy.retries,1);self.assertFalse(policy.pending)
        self.assertEqual(len(pushes),2);self.assertEqual(original_git('rev-parse','HEAD')[1],head)
        for name in ('ingest-pending','normalization-pending','reconciliation-pending'):
            self.assertEqual(list((runner.state/name).glob('*.json')),[])
    def test_later_checkpoint_recovers_both_db_stages_without_rerunning_workers(self):
        for filename,classname,method in (
            ('test_normalization_runner.py','NormalizationRunnerTests','normalization_engine'),
            ('test_reconciliation_runner.py','ReconciliationRunnerTests','reconciliation_engine')):
            with self.subTest(stage=method):
                spec=importlib.util.spec_from_file_location('retry_'+method,PACKAGE/'tests'/filename)
                module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
                case=getattr(module,classname)();case.setUp()
                try:
                    case.install();runner=case.runner();self.recover_stage(case,runner,method,lambda:case.calls)
                finally:case.tearDown()
    def test_repeat_report_reuses_cached_timestamp_before_new_spool(self):
        spec=importlib.util.spec_from_file_location('retry_repeat_fixture',PACKAGE/'tests/test_normalization_runner.py')
        module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        case=module.NormalizationRunnerTests();case.setUp()
        class Timestamp(m.datetime.datetime):
            hour=19
            @classmethod
            def now(cls,tz=None):return cls(2026,10,22,cls.hour,0,tzinfo=tz)
        try:
            case.install();runner=case.runner()
            with mock.patch.object(m.datetime,'datetime',Timestamp),contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(runner.run_plan(),0)
                before=case.remote_receipts();first=runner.git('rev-parse',branch.LOCAL_REF)[1]
                case.case.case.close(runner);runner=case.runner();original=runner.git;calls=[]
                def git(*args,**kwargs):calls.append(args);return original(*args,**kwargs)
                runner.git=git;Timestamp.hour=20;self.assertEqual(runner.run_plan(),0)
            self.assertEqual(case.remote_receipts(),before)
            self.assertEqual(original('rev-parse',branch.LOCAL_REF)[1],first)
            self.assertEqual([c for c in calls if c[0] in ('push','commit-tree')],[])
            self.assertEqual(list((runner.state/'normalization-pending').glob('*.json')),[])
        finally:case.tearDown()
    def test_isolated_ingestion_uses_same_policy_without_source_replay(self):
        case=fixture.fixture.ReceiptBranchTests();case.setUp()
        try:self.recover_stage(case,case.case.runner(),'ingest_engine',lambda:case.case.calls)
        finally:case.tearDown()


if __name__=='__main__':unittest.main()
