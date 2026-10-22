"""Generated local bare Git only; no network, active checkout or real data."""
import copy
import importlib.util
import json
import os
from pathlib import Path
import shutil
import sys
import unittest

PACKAGE=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(PACKAGE))
spec=importlib.util.spec_from_file_location('receipt_branch_fixture',PACKAGE/'tests/test_ingest_runner.py')
fixture=importlib.util.module_from_spec(spec);spec.loader.exec_module(fixture)
m=fixture.m
from receipt_branch import BRANCH as RECEIPT_BRANCH


class ReceiptBranchTests(unittest.TestCase):
    def setUp(self):
        self.case=fixture.IngestRunnerTests('test_ingest_runs_all_domain_and_completed_plan_is_idempotent')
        self.case.setUp()
        self.git=self.case.case.git_at
        self.root=self.case.case.root
        shutil.copy(PACKAGE/'receipt_branch.py',self.root/'manual-action/receipt_branch.py')
        plan=json.loads((self.root/'manual-action/plan.json').read_text())
        plan['receipt_transport']='isolated-branch-v1'
        plan['jobs'][0]['version']=2
        (self.root/'manual-action/plan.json').write_bytes(m.canonical(plan))
        self.git(self.root,'add','manual-action');self.git(self.root,'commit','-m','Generated isolated receipt plan')
        self.git(self.root,'push','origin',m.BRANCH)
    def tearDown(self):
        self.case.tearDown()
    def receipts(self):
        remote=self.case.case.remote
        paths=self.git(remote,'ls-tree','-r','--name-only','refs/heads/'+RECEIPT_BRANCH).splitlines()
        return [json.loads(self.git(remote,'show','refs/heads/'+RECEIPT_BRANCH+':'+path)) for path in paths]
    def test_code_advance_during_ingest_does_not_break_receipts_or_mutate_index(self):
        editor=self.case.case.editor()
        initial=self.case.case.head()
        protected=('refs/heads/integration/runner-control','refs/heads/integration/runner-results')
        for ref in protected:self.git(self.case.case.remote,'update-ref',ref,initial)
        runner=self.case.runner();engine=runner.ingest_engine()
        original=engine.run_prepared
        def run(prepared,report_callback):
            def checkpoint(report):
                report_callback(report)
                if report['status']=='running':
                    (editor/'code-release.txt').write_text('Generated new reviewed code release')
                    self.git(editor,'add','code-release.txt');self.git(editor,'commit','-m','Generated concurrent code publication')
                    self.git(editor,'push','origin',m.BRANCH)
            return original(prepared,checkpoint)
        engine.run_prepared=run;runner.ingest_engine=lambda:engine
        unrelated=self.root/'unrelated.txt';unrelated.write_text('Keep unrelated local changes')
        self.assertEqual(runner.run_plan(),0)
        self.assertEqual(self.case.case.head(),initial)
        self.assertNotEqual(self.case.case.head(self.case.case.remote),initial)
        self.assertEqual(self.git(self.root,'diff','--cached','--name-only'),'')
        self.assertEqual(unrelated.read_text(),'Keep unrelated local changes')
        self.assertEqual({v['outcome'] for v in self.receipts()},{'running','completed'})
        self.assertFalse(list((self.root/m.RETURN_DIR).glob('*.json')))
        self.case.case.close(runner)
        retry=self.case.runner();self.assertEqual(retry.run_plan(),0)
        self.assertEqual(self.case.calls,1)
        self.assertEqual(self.case.case.head(),self.case.case.head(self.case.case.remote))
        for ref in protected:self.assertEqual(self.git(self.case.case.remote,'rev-parse',ref),initial)
    def test_failed_push_preserves_isolated_commits_and_spool_then_retries_without_ingest(self):
        runner=self.case.runner();original=runner.git
        code_head=self.case.case.head()
        def fail(*args,**kwargs):
            if args[0]=='push':raise m.Stop('generated_push_failure_preserved')
            return original(*args,**kwargs)
        runner.git=fail
        self.assertEqual(runner.run_plan(),2)
        self.assertEqual(self.case.calls,1)
        receipt_head=self.git(self.root,'rev-parse','refs/heads/'+RECEIPT_BRANCH)
        self.assertEqual(self.case.case.head(),code_head)
        self.assertEqual(len(list((runner.state/'ingest-pending').glob('*.json'))),2)
        self.case.case.close(runner)
        retry=self.case.runner();self.assertEqual(retry.run_plan(),0)
        self.assertEqual(self.case.calls,1)
        self.assertEqual(list((retry.state/'ingest-pending').glob('*.json')),[])
        remote_head=self.git(self.case.case.remote,'rev-parse','refs/heads/'+RECEIPT_BRANCH)
        self.assertEqual(self.git(self.root,'merge-base',receipt_head,remote_head),receipt_head)
        self.assertEqual(self.case.case.head(),code_head)
    def test_remote_nonreceipt_tree_is_never_propagated(self):
        # A remote receipt branch containing arbitrary source data is rejected;
        # ingestion itself still finishes and the strict receipt spool survives.
        self.git(self.root,'push','origin','HEAD:refs/heads/'+RECEIPT_BRANCH)
        runner=self.case.runner();self.assertEqual(runner.run_plan(),2)
        self.assertEqual(self.case.calls,1)
        self.assertTrue((runner.state/'ingest-pending').is_dir())
        self.assertEqual(len(list((runner.state/'ingest-pending').glob('*.json'))),2)
        self.assertEqual(self.case.case.head(),self.case.case.head(self.case.case.remote))
    def with_evidence(self):
        from ingest_evidence import sanitize_evidence
        original=self.case.report
        self.case.report=lambda status: {**original(status), 'ingest_evidence':sanitize_evidence({'phase':'pre' if status=='running' else 'post'})}

    def test_readable_supplement_is_atomically_bound_and_never_in_code_index(self):
        self.with_evidence();runner=self.case.runner();self.assertEqual(runner.run_plan(),0)
        values=self.receipts();receipts=[v for v in values if v['schema']=='offmenu-run-receipt/2']
        supplements=[v for v in values if v['schema']=='offmenu-ingest-supplement/1']
        self.assertEqual(len(receipts),2);self.assertEqual(len(supplements),2)
        refs={v['ingest']['evidence_ref']['sha256'] for v in receipts}
        self.assertEqual(refs,{m.digest(m.canonical(v)) for v in supplements})
        branch='refs/heads/'+RECEIPT_BRANCH
        for commit in self.git(self.case.case.remote,'rev-list',branch).splitlines():
            paths=self.git(self.case.case.remote,'diff-tree','--root','--no-commit-id','--name-only','-r',commit).splitlines()
            self.assertEqual(len(paths),2)
        self.assertEqual(self.git(self.root,'diff','--cached','--name-only'),'')

    def test_missing_supplement_recovers_from_validated_local_receipt_commit(self):
        self.with_evidence();runner=self.case.runner();original=runner.git
        def fail(*args,**kwargs):
            if args[0]=='push':raise m.Stop('generated_push_failure_preserved')
            return original(*args,**kwargs)
        runner.git=fail;self.assertEqual(runner.run_plan(),2)
        # Only first checkpoint was committed; leave final supplement intact.
        first=next(json.loads(p.read_text()) for p in (runner.state/'ingest-pending').glob('*.json') if json.loads(p.read_text())['receipt']['outcome']=='running')
        ref=first['receipt']['ingest']['evidence_ref']
        path=runner.state/'ingest-evidence'/(ref['sha256']+'.json');path.unlink()
        self.case.case.close(runner)
        retry=self.case.runner();self.assertEqual(retry.run_plan(),0)
        self.assertTrue(path.is_file());self.assertEqual(self.case.calls,1)
        self.assertEqual(m.digest(path.read_bytes()),ref['sha256'])

    def test_tampered_supplement_preserved_and_never_published(self):
        self.with_evidence();runner=self.case.runner();original=runner.git
        def fail(*args,**kwargs):
            if args[0]=='push':raise m.Stop('generated_push_failure_preserved')
            return original(*args,**kwargs)
        runner.git=fail;self.assertEqual(runner.run_plan(),2)
        paths=list((runner.state/'ingest-evidence').glob('*.json'))
        paths[0].write_text('{"private":"Generated unapproved payload"}')
        bad=paths[0].read_bytes();self.case.case.close(runner)
        retry=self.case.runner();self.assertEqual(retry.run_plan(),2)
        self.assertEqual(self.case.calls,1);self.assertEqual(paths[0].read_bytes(),bad)
        self.assertTrue(list((retry.state/'ingest-pending').glob('*.json')))
        self.assertEqual(self.git(self.case.case.remote,'ls-remote','--heads',str(self.case.case.remote),'refs/heads/'+RECEIPT_BRANCH),'')

    def test_worst_finite_supplement_and_main_receipt_fit_existing_bounds(self):
        import ingest_evidence as evidence
        import ingest_errors as errors
        import ingest_relational_targets as targets
        import test_ingest_evidence as evidence_fixtures
        from unittest import mock
        captured=[];validate=evidence.validate_evidence
        def capture(value):
            result=validate(value);captured.append(copy.deepcopy(value));return result
        stress=evidence_fixtures.EvidenceTests('test_worst_finite_enum_supplement_is_bounded_without_count_loss')
        with mock.patch.object(evidence,'validate_evidence',capture):
            stress.test_worst_finite_enum_supplement_is_bounded_without_count_loss()
        relational=targets.sanitize_relational_summary({'blockers':sorted(targets.BLOCKERS)})
        for row in relational['domains'].values():
            row.update(status='materialized',records=2**63-1,typed_records=2**63-1,untyped_records=2**63-1)
        relational['relations']={key:2**63-1 for key in relational['relations']}
        report=self.case.report('partial')
        report.update(ingest_evidence=captured[-1],relational_targets=relational)
        supplement=m.build_supplement(report);reference=m.reference_for_supplement(supplement)
        self.assertLessEqual(reference['bytes'],65536)
        telemetry=errors.sanitize_error_telemetry({'status':'available',
            'class_counts':{key:10**15 for key in errors.ERROR_CLASSES},
            'reason_counts':{key:10**15 for key in errors.ERROR_REASONS},
            'origin_counts':{key:10**15 for key in errors.ORIGINS}})
        for row in report['domains'].values():
            row['error_telemetry']=telemetry;row['error_codes']=sorted(m.ERROR_CODES)
            for key in ('read','written','unchanged','errors','skipped','sources_total','reused_rows','reused_stores'):
                row[key]=10**15
        pending=report['pending_work']
        for row in pending['domains'].values():
            for key in m.PENDING_COUNTS: row[key]=10**12
            row['assignments_total']=sum(row[key] for key in m.PENDING_ASSIGNMENTS)
            for key in m.PENDING_NULLABLE: row[key]=10**15
        pending['totals']={key:sum(row[key] for row in pending['domains'].values()) for key in m.PENDING_COUNTS}
        pending['totals'].update({key:10**15 for key in m.PENDING_NULLABLE})
        pending['totals']['processed_bytes']=None
        summary=self.case.runner().ingest_summary(report)
        receipt={'schema':'offmenu-run-receipt/2','job_id':'retained-eight-domain-ingest',
            'job_version':2,'operation':'retained_ingest_all','job_key':'a'*64,
            'implementation_sha256':'b'*64,'input_sha256':'c'*64,
            'observed_at':'2026-10-22T00:00:00Z','outcome':'partial','ingest':summary}
        m.validate_ingest_receipt(receipt)
        self.assertEqual(summary['evidence_ref'],reference)

    def test_legacy_v2_spool_migrates_without_changing_code_branch(self):
        runner=self.case.runner();code_head=self.case.case.head()
        report=self.case.report('partial');summary=runner.ingest_summary(report)
        receipt={'schema':'offmenu-run-receipt/2','job_id':'retained-eight-domain-ingest',
            'job_version':1,'operation':'retained_ingest_all','job_key':'a'*64,
            'implementation_sha256':'b'*64,'input_sha256':'c'*64,'observed_at':'2026-10-22T00:00:00Z',
            'outcome':'partial','ingest':summary}
        spool=runner.state/'ingest-pending'/Path(m.receipt_relpath(receipt)).name
        runner.durable_local_json(spool,{'sha256':m.digest(m.canonical(receipt)),'receipt':receipt})
        self.assertEqual(runner.run_plan(),0)
        self.assertFalse(spool.exists())
        self.assertIn(receipt,self.receipts())
        self.assertEqual(self.case.case.head(),code_head)


if __name__=='__main__':unittest.main()
