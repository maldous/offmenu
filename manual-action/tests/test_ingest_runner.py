"""Finite all-domain protocol against generated local Git remotes only."""
import importlib.util
import copy
import contextlib
import io
import json
from pathlib import Path
import types
import shutil
import sqlite3
import subprocess
import unittest
PACKAGE=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('legacy_fixture',PACKAGE/'tests/test_plan_runner.py')
legacy=importlib.util.module_from_spec(spec);spec.loader.exec_module(legacy)
m=legacy.m

class IngestRunnerTests(unittest.TestCase):
    def setUp(self):
        self.case=legacy.RunnerTests('test_success_commit_push_idempotent_and_unrelated_dirty_preserved')
        self.case.setUp();self.calls=0;self.catalog='a'*64;self.final_status='complete';self.fail_domain=False
        self.install_plan()
    def tearDown(self):self.case.tearDown()
    def install_plan(self,editor=None):
        root=editor or self.case.root
        (root/'manual-action/plan.json').write_bytes(m.canonical({'schema':'offmenu-run-plan/2','max_parallel':8,'jobs':[{'id':'retained-eight-domain-ingest','version':1,'operation':'retained_ingest_all','depends_on':[]}]}))
        self.case.git_at(root,'add','manual-action/plan.json');self.case.git_at(root,'commit','-m','Reviewed generated ingest plan')
        self.case.git_at(root,'push','origin',m.BRANCH)
    def pending(self,status):
        summary=m.unknown_pending_work()
        summary.update(status='available',catalog_complete=True,catalog_sources=6,
                       awaiting_input_domains=['user_profiles','inventory'])
        for domain,row in summary['domains'].items():
            if domain not in ('user_profiles','inventory'):
                row['assignments_total']=1
                row['not_yet_read' if status=='running' else 'completed']=1
                row['files_remaining']=int(status=='running')
                row['records_remaining_known']=2 if status=='running' else 0
            row['records_remaining']=row['records_remaining_known']
            row['records_to_write']=None if row['files_remaining'] else 0
        summary['totals']={key:sum(row[key] for row in summary['domains'].values()) for key in m.PENDING_COUNTS}
        summary['totals'].update(records_remaining=12 if status=='running' else 0,
                                 records_to_write=None if status=='running' else 0,processed_bytes=None)
        return summary
    def report(self,status):
        domains={d:{'status':'complete' if status!='running' else 'running','read':2,'written':2,'unchanged':0,'errors':0,'skipped':0,'sources_total':1,'reused_rows':0,'reused_stores':0,'error_codes':[]} for d in m.DOMAINS}
        for d in ('user_profiles','inventory'):domains[d].update(status='awaiting_user_input',read=0,written=0,sources_total=0)
        if self.fail_domain:domains['suppliers'].update(status='failed',errors=1,error_codes=['ValueError'])
        return {'status':status,'domains':domains,'pending_work':self.pending(status)}
    def runner(self):
        runner=self.case.new_runner()
        def prepare(state,options):return {'catalog_sha256':self.catalog,'config':options}
        def run(prepared,report_callback):
            self.calls+=1;report_callback(self.report('running'))
            (self.case.root/'.git/generated-ingest-completed').write_text('durable local data')
            final=self.report(self.final_status);report_callback(final);return final
        runner.ingest_engine=lambda:types.SimpleNamespace(prepare_default=prepare,run_prepared=run,completed_outputs_available=lambda prepared:True,pending_snapshot=lambda prepared:self.pending('running'))
        return runner
    def test_ingest_runs_all_domain_and_completed_plan_is_idempotent(self):
        r=self.runner();self.assertEqual(r.run_plan(),0);self.assertEqual(self.calls,1)
        values=[json.loads(p.read_text()) for p in self.case.receipts()]
        self.assertEqual({v['outcome'] for v in values},{'running','completed'})
        self.assertEqual(set(values[-1]['ingest']['domains']),set(m.DOMAINS));self.case.close(r)
        again=self.runner();self.assertEqual(again.run_plan(),0);self.assertEqual(self.calls,1)
    def test_push_failure_does_not_stop_ingest_or_final_local_summary(self):
        r=self.runner();original=r.git
        def fail(*args,**kwargs):
            if args[0]=='push':raise m.Stop('git_push_failed_local_work_preserved')
            return original(*args,**kwargs)
        r.git=fail;self.assertEqual(r.run_plan(),2)
        self.assertTrue((self.case.root/'.git/generated-ingest-completed').exists())
        spools=list((r.state/'ingest-pending').glob('*.json'));self.assertEqual(len(spools),2)
        self.assertIn('completed',{json.loads(p.read_text())['receipt']['outcome'] for p in spools})
        self.case.close(r);retry=self.runner();self.assertEqual(retry.run_plan(),0)
        self.assertEqual(self.calls,1);self.assertEqual(list((retry.state/'ingest-pending').glob('*.json')),[])
        self.assertEqual(self.case.head(),self.case.head(self.case.remote))
    def test_spool_owns_receipt_if_crash_precedes_recovery_checkpoint(self):
        r=self.runner()
        def crash(value):
            relative=m.receipt_relpath(value);path=self.case.root/relative
            path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(m.canonical(value))
            raise m.Stop('generated_crash_before_checkpoint')
        r.materialize_ingest_receipt=crash
        self.assertEqual(r.run_plan(),2);self.assertEqual(self.calls,1)
        self.assertFalse((r.state/'checkpoint.json').exists());self.case.close(r)
        retry=self.runner();self.assertEqual(retry.run_plan(),0);self.assertEqual(self.calls,1)
        self.assertEqual(self.case.head(),self.case.head(self.case.remote))

    def test_failed_source_is_reported_without_hiding_other_domains(self):
        self.final_status='partial';self.fail_domain=True;r=self.runner();self.assertEqual(r.run_plan(),2)
        final=[json.loads(p.read_text()) for p in self.case.receipts() if 'partial-' in p.name][0]
        self.assertEqual(final['ingest']['domains']['suppliers']['error_codes'],['ValueError'])
        self.assertEqual(final['ingest']['domains']['recipes']['written'],2)
    def test_catalog_change_runs_new_identity(self):
        r=self.runner();self.assertEqual(r.run_plan(),0);self.case.close(r)
        self.catalog='b'*64;r=self.runner();self.assertEqual(r.run_plan(),0);self.assertEqual(self.calls,2)
    def test_legacy_blocked_receipt_does_not_block_new_ingest(self):
        # Make a historical terminal supplier receipt owned/published by runner.
        r=self.runner();foo=r.inspector();value={'schema':m.RECEIPT_SCHEMA,'job_id':'supplier-source-inspection','job_version':2,'operation':'supplier_inspect','job_key':'c'*64,'implementation_sha256':'d'*64,'input_sha256':None,'observed_at':foo.stamp(),'outcome':'blocked','supplier':{'status':'blocked','reason':'json_rows_refused','member_count':0,'transfer':'NOT_UPLOADED'},'data_loads':'not_implemented','source_review':'manual_review_required','source_upload':'NOT_UPLOADED'}
        relative=m.receipt_relpath(value);path=self.case.root/relative;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(m.canonical(value));r.checkpoint('receipt_ready',value['job_key'],relative,m.digest(m.canonical(value)))
        self.assertEqual(r.run_plan(),0);self.assertEqual(self.calls,1)
    def test_strict_ingest_receipt_rejects_path_error_and_extra_fields(self):
        r=self.runner();self.assertEqual(r.run_plan(),0)
        value=json.loads(self.case.receipts()[0].read_text());value['ingest']['domains']['recipes']['error_codes']=['/private/source']
        value['ingest']['progress_sha256']=m.digest(m.canonical(value['ingest']['domains']))
        with self.assertRaises(m.Stop):m.validate_receipt(value)
    def test_root_run_real_catalog_engine_adapters_and_local_push(self):
        # Fixed generated fixtures only: exercise actual ./run pull/reexec/API,
        # all registered adapters, staging, failure isolation, strict receipt push.
        source_root=self.case.base/'retained-data';source_root.mkdir()
        payloads={
            'off-2026-10-12-lf/products.jsonl':'{"code":"000123","product_name":"Generated fixture","nutriments":{"energy":1},"license":"CC0","url":"https://example.invalid/generated"}\n',
            'world-recipes-common-input-20261014/recipes.jsonl':'{"id":"generated-recipe","name":"Generated fixture","ingredients":["1 g generated ingredient"],"instructions":["Generated instruction"],"url":"https://example.invalid/generated"}\n{malformed\n',
            'wikidata-businesses-20261013-native/organizations.jsonl':'{"id":"Q123","name":"Generated organization","country":"ZZ","url":"https://example.invalid/generated"}\n',
            'dietary-guidelines-20261013/guidelines.jsonl':'{"id":"generated-guideline","title":"Generated guideline","sourceId":"dietary-guidelines","url":"https://example.invalid/generated"}\n'}
        for relative,body in payloads.items():
            path=source_root/relative;path.parent.mkdir(parents=True,exist_ok=True);path.write_text(body)
        identifier=source_root/'barcode-identifiers-worker57-full-retained-v1/identifiers.sqlite';identifier.parent.mkdir()
        db=sqlite3.connect(identifier);db.execute('CREATE TABLE code_keys(barcode TEXT PRIMARY KEY)');db.execute('INSERT INTO code_keys VALUES (?)',('000123',));db.commit();db.close()
        for source in PACKAGE.glob('ingest_*.py'):shutil.copy(source,self.case.root/'manual-action'/source.name)
        catalog=self.case.root/'manual-action/ingest_catalog.py'
        catalog.write_text(catalog.read_text().replace("DEFAULT_ROOT = '/home/user/src/offmenu-data'",'DEFAULT_ROOT = '+repr(str(source_root))).replace("'/home/user/Documents/Codex/2026-10-22/worker56-recipe-retention-audit/TERMINAL-HANDOFF.json'",repr(str(self.case.base/'absent-generated-report.json'))))
        runner=self.case.root/'manual-action/plan_runner.py'
        runner.write_text(runner.read_text().replace('RETURN_DIR =',f'REMOTE_URLS.add({str(self.case.remote)!r})\nRETURN_DIR =',1))
        self.case.git_at(self.case.root,'add','manual-action');self.case.git_at(self.case.root,'commit','-m','Generated fixture-only retained source bindings')
        self.case.git_at(self.case.root,'push','origin',m.BRANCH)
        proc=subprocess.run(['./run'],cwd=self.case.root,capture_output=True,text=True,timeout=90)
        self.assertEqual(proc.returncode,2,proc.stdout+proc.stderr)
        self.assertEqual(proc.stdout.count('[1/4]'),1)
        for domain in m.DOMAINS:self.assertIn(domain+':',proc.stdout)
        self.assertIn('Final domain summary',proc.stdout)
        state=self.case.root/'.git/offmenu-runner/ingest'
        report=json.loads((state/'last-report.json').read_text())
        self.assertEqual(report['status'],'partial')
        self.assertGreater(report['domains']['recipes']['errors'],0)
        for domain in ('ingredients','recipes','dietary','suppliers','citations'):
            self.assertGreater(report['domains'][domain]['written'],0,report)
        self.assertGreaterEqual(report['domains']['barcodes']['reused_stores'],1)
        self.assertEqual(report['domains']['user_profiles']['status'],'awaiting_user_input')
        self.assertEqual(self.case.head(),self.case.head(self.case.remote))
        receipts=[json.loads(p.read_text()) for p in self.case.receipts()]
        self.assertEqual({v['outcome'] for v in receipts},{'running','partial'})
        serialized=json.dumps(receipts)
        self.assertNotIn(str(source_root),serialized);self.assertNotIn('Generated fixture',serialized)
        self.assertNotIn('000123',serialized)

        # Real startup callback is delivered before any worker is started, not
        # merely generated after the final result. Pending counts then decrease.
        self.assertLess(proc.stdout.index('[pending] Before ingest'),proc.stdout.index('Final domain summary'))
        before=next(v['ingest']['pending_work'] for v in receipts if v['outcome']=='running')
        after=next(v['ingest']['pending_work'] for v in receipts if v['outcome']=='partial')
        self.assertEqual(before['status'],'available');self.assertEqual(after['status'],'available')
        self.assertGreater(before['totals']['files_remaining'],after['totals']['files_remaining'])
        self.assertGreater(after['totals']['completed']+after['totals']['reused'],0)
        self.assertGreaterEqual(after['domains']['recipes']['partial'],1)
        self.assertEqual(after['awaiting_input_domains'],['user_profiles','inventory'])
        self.assertTrue((state/'pending-work.private.json').is_file())
        self.assertTrue((state/'pending-work.json').is_file())

        def durable_rows():
            result={}
            for domain in m.DOMAINS:
                path=state/('private-household' if domain in ('user_profiles','inventory') else '.')/'staging'/(domain+'.sqlite3')
                with sqlite3.connect(path.as_uri()+'?mode=ro',uri=True) as db:
                    result[domain]=db.execute('SELECT source_key,source_version,record_id,content_sha256,updated_at FROM records ORDER BY source_key,source_version,record_id').fetchall()
            return result
        stored=durable_rows();prior_jobs={v['job_key'] for v in receipts}
        # Reporting-only implementation changes do not bump plan/adapter source
        # versions or replay completed source records, including error-complete
        # source prefixes. Only generated local Git state is touched here.
        runner.write_text(runner.read_text()+'\n# Generated reporting-only revision fixture.\n')
        self.case.git_at(self.case.root,'add','manual-action/plan_runner.py')
        self.case.git_at(self.case.root,'commit','-m','Generated reporting-only revision')
        self.case.git_at(self.case.root,'push','origin',m.BRANCH)
        again=subprocess.run(['./run'],cwd=self.case.root,capture_output=True,text=True,timeout=90)
        self.assertEqual(again.returncode,2,again.stdout+again.stderr)
        self.assertEqual(stored,durable_rows())
        newer=[json.loads(p.read_text()) for p in self.case.receipts() if json.loads(p.read_text())['job_key'] not in prior_jobs]
        self.assertTrue(newer)
        final=next(v for v in newer if v['outcome']=='partial')
        self.assertTrue(all(row['written']==0 for row in final['ingest']['domains'].values()))
        self.assertEqual(self.case.head(),self.case.head(self.case.remote))

        # Optional reporting must remain optional even when the module itself
        # is absent, not just when an already imported helper raises an error.
        self.case.git_at(self.case.root,'rm','manual-action/ingest_pending.py')
        self.case.git_at(self.case.root,'commit','-m','Generated unavailable reporter fixture')
        self.case.git_at(self.case.root,'push','origin',m.BRANCH)
        without_helper=subprocess.run(['./run'],cwd=self.case.root,capture_output=True,text=True,timeout=90)
        self.assertEqual(without_helper.returncode,2,without_helper.stdout+without_helper.stderr)
        self.assertIn('Final domain summary',without_helper.stdout)
        self.assertIn('Remaining assignments, files and records are unknown (not zero)',without_helper.stdout)
        self.assertEqual(stored,durable_rows())
        no_helper_report=json.loads((state/'last-report.json').read_text())
        self.assertEqual(no_helper_report['pending_work']['status'],'unknown')
        self.assertTrue(all(row['written']==0 for row in no_helper_report['domains'].values()))
        self.assertEqual(self.case.head(),self.case.head(self.case.remote))

    def test_pending_work_is_strict_and_binds_progress_digest(self):
        r=self.runner();self.assertEqual(r.run_plan(),0)
        values=[json.loads(p.read_text()) for p in self.case.receipts()]
        running=next(value for value in values if value['outcome']=='running')
        completed=next(value for value in values if value['outcome']=='completed')
        self.assertEqual(running['ingest']['pending_work']['totals']['files_remaining'],6)
        self.assertEqual(completed['ingest']['pending_work']['totals']['files_remaining'],0)
        for field,bad in (('provider','private provider name'),('files_remaining',True),
                          ('records_remaining',-1),('processed_bytes',12)):
            with self.subTest(field=field):
                value=copy.deepcopy(running)
                value['ingest']['pending_work']['domains']['recipes'][field]=bad
                value['ingest']['progress_sha256']=m.ingest_progress_digest(value['ingest'])
                with self.assertRaises(m.Stop):m.validate_receipt(value)
        value=copy.deepcopy(running)
        value['ingest']['pending_work']['awaiting_input_domains']=['/private/path']
        value['ingest']['progress_sha256']=m.ingest_progress_digest(value['ingest'])
        with self.assertRaises(m.Stop):m.validate_receipt(value)
        changed=copy.deepcopy(running['ingest'])
        changed['pending_work']['domains']['recipes']['records_remaining_known']+=1
        self.assertNotEqual(m.ingest_progress_digest(changed),running['ingest']['progress_sha256'])

    def test_legacy_v2_receipt_spool_and_push_recovery_remain_valid(self):
        r=self.runner();original_summary=r.ingest_summary;original_git=r.git
        def legacy_summary(report):
            summary=original_summary(report)
            del summary['pending_work']
            summary['progress_sha256']=m.digest(m.canonical(summary['domains']))
            return summary
        r.ingest_summary=legacy_summary
        # Keep the final console summary independent from optional old fields.
        def fail_push(*args,**kwargs):
            if args[0]=='push':raise m.Stop('git_push_failed_local_work_preserved')
            return original_git(*args,**kwargs)
        r.git=fail_push
        # Delivery errors preserve both v2 spools; the final console still runs.
        self.assertEqual(r.run_plan(),2)
        spools=list((r.state/'ingest-pending').glob('*.json'))
        self.assertEqual(len(spools),2)
        for spool in spools:
            value=json.loads(spool.read_text())['receipt']
            self.assertNotIn('pending_work',value['ingest']);m.validate_receipt(value)
        self.case.close(r)
        retry=self.runner();self.assertEqual(retry.run_plan(),0);self.assertEqual(self.calls,1)
        self.assertEqual(self.case.head(),self.case.head(self.case.remote))
        self.assertFalse(list((retry.state/'ingest-pending').glob('*.json')))

    def test_pending_helper_failure_and_untrusted_fields_do_not_gate_ingest(self):
        r=self.runner();engine=r.ingest_engine()
        def fail_snapshot(prepared):raise RuntimeError('/private/provider/secret')
        engine.pending_snapshot=fail_snapshot;r.ingest_engine=lambda:engine
        original_report=self.report
        def invalid_report(status):
            report=original_report(status)
            report['pending_work']['provider']='/private/provider/secret'
            return report
        self.report=invalid_report
        output=io.StringIO()
        with contextlib.redirect_stdout(output):self.assertEqual(r.run_plan(),0)
        self.assertEqual(self.calls,1);self.assertNotIn('/private/provider/secret',output.getvalue())
        self.assertIn('Remaining assignments, files and records are unknown (not zero)',output.getvalue())
        self.assertLess(output.getvalue().index('Before ingest'),output.getvalue().index('Final domain summary'))
        for path in self.case.receipts():
            value=json.loads(path.read_text())
            self.assertEqual(value['ingest']['pending_work']['status'],'unknown')
            self.assertNotIn('/private/provider/secret',path.read_text())

    def test_no_arbitrary_commands_or_extra_plan_fields(self):
        plan=json.loads((self.case.root/'manual-action/plan.json').read_text());plan['jobs'][0]['shell']='ls'
        with self.assertRaises(m.Stop):m.validate_plan(plan)
if __name__=='__main__':unittest.main()
