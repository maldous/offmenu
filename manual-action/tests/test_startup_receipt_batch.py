"""Startup cancellation and bounded spool delivery; generated local Git only."""
import contextlib
import importlib.util
import io
from pathlib import Path
import subprocess
import unittest
from unittest import mock

PACKAGE=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('startup_batch_fixture',PACKAGE/'tests/test_receipt_batch.py')
fixture=importlib.util.module_from_spec(spec);spec.loader.exec_module(fixture)
m=fixture.m


class StartupBatchTests(unittest.TestCase):
    def setUp(self):
        self.case=fixture.ReceiptBatchTests('test_twenty_old_receipts_one_tree_commit_push_and_checkout_unchanged')
        self.case.setUp();self.runner=self.case.runner
    def tearDown(self):self.case.tearDown()
    def spools(self,count=20):
        result=[]
        for number in range(count):
            value,_=self.case.receipt(number,legacy=True)
            path=self.runner.state/'ingest-pending'/Path(m.receipt_relpath(value)).name
            self.runner.durable_local_json(path,{'sha256':m.digest(m.canonical(value)),'receipt':value})
            result.append((path,path.read_bytes()))
        return result
    def stop_before_ingest(self):
        engine=self.runner.ingest_engine()
        engine.prepare_default=mock.Mock(side_effect=m.Stop('generated_discovery_stop'))
        self.runner.ingest_engine=lambda:engine
        return engine
    def test_startup_twenty_spools_one_publish_then_discovery(self):
        spools=self.spools();engine=self.stop_before_ingest();batches=[]
        self.runner.materialize_ingest_receipts=lambda values:batches.append(values)
        output=io.StringIO()
        with contextlib.redirect_stdout(output),self.assertRaisesRegex(m.Stop,'generated_discovery_stop'):
            self.runner.run_plan()
        self.assertEqual([len(batch) for batch in batches],[20])
        self.assertTrue(all(not path.exists() for path,_ in spools))
        self.assertIn('20 preserved checkpoints in one batch',output.getvalue())
        engine.prepare_default.assert_called_once();self.assertEqual(self.case.case.case.calls,0)
    def test_startup_interrupt_keeps_all_spools_and_never_discovers(self):
        spools=self.spools();engine=self.stop_before_ingest()
        self.runner.materialize_ingest_receipts=mock.Mock(side_effect=KeyboardInterrupt)
        output=io.StringIO()
        with contextlib.redirect_stdout(output),self.assertRaises(KeyboardInterrupt):self.runner.run_plan()
        engine.prepare_default.assert_not_called()
        self.assertTrue(all(path.read_bytes()==raw for path,raw in spools))
        self.assertNotIn('Receipt sync paused',output.getvalue())
    def test_startup_transport_failure_preserves_all_spools(self):
        spools=self.spools();engine=self.stop_before_ingest()
        self.runner.materialize_ingest_receipts=mock.Mock(side_effect=m.Stop('generated_push_failure'))
        with contextlib.redirect_stdout(io.StringIO()),self.assertRaisesRegex(m.Stop,'generated_discovery_stop'):
            self.runner.run_plan()
        self.assertTrue(all(path.read_bytes()==raw for path,raw in spools))
        self.runner.materialize_ingest_receipts.assert_called_once()
        engine.prepare_default.assert_called_once()
    def test_git_interrupt_is_not_timeout(self):
        process=mock.Mock(pid=123);process.communicate.side_effect=[KeyboardInterrupt(),(b'',b'')]
        with mock.patch.object(m.subprocess,'Popen',return_value=process),mock.patch.object(m.os,'killpg') as kill:
            with self.assertRaises(KeyboardInterrupt):self.runner.git('status')
        kill.assert_called_once_with(123,m.signal.SIGKILL)
    def test_git_timeout_still_preserves_transport_failure(self):
        process=mock.Mock(pid=123);process.communicate.side_effect=[subprocess.TimeoutExpired('git',120),(b'',b'')]
        with mock.patch.object(m.subprocess,'Popen',return_value=process),mock.patch.object(m.os,'killpg'):
            with self.assertRaisesRegex(m.Stop,'git_timeout_local_work_preserved'):self.runner.git('status')
    def test_fallback_identity_resolved_and_announced_once(self):
        self.runner.git=mock.Mock(return_value=(1,b''))
        with mock.patch.dict(m.os.environ,{},clear=True),mock.patch.object(m,'announce') as announce:
            first=self.runner.commit_identity_env();calls=self.runner.git.call_count
            second=self.runner.commit_identity_env()
        self.assertEqual(first,second);self.assertEqual(len(first),4)
        self.assertEqual(self.runner.git.call_count,calls);announce.assert_called_once()


if __name__=='__main__':unittest.main()
