"""Finite all-domain protocol against generated local Git remotes only."""
import importlib.util
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
    def report(self,status):
        domains={d:{'status':'complete' if status!='running' else 'running','read':2,'written':2,'unchanged':0,'errors':0,'skipped':0,'sources_total':1,'reused_rows':0,'reused_stores':0,'error_codes':[]} for d in m.DOMAINS}
        for d in ('user_profiles','inventory'):domains[d].update(status='awaiting_user_input',read=0,written=0,sources_total=0)
        if self.fail_domain:domains['suppliers'].update(status='failed',errors=1,error_codes=['ValueError'])
        return {'status':status,'domains':domains}
    def runner(self):
        runner=self.case.new_runner()
        def prepare(state,options):return {'catalog_sha256':self.catalog,'config':options}
        def run(prepared,report_callback):
            self.calls+=1;report_callback(self.report('running'))
            (self.case.root/'.git/generated-ingest-completed').write_text('durable local data')
            final=self.report(self.final_status);report_callback(final);return final
        runner.ingest_engine=lambda:types.SimpleNamespace(prepare_default=prepare,run_prepared=run,completed_outputs_available=lambda prepared:True)
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

    def test_no_arbitrary_commands_or_extra_plan_fields(self):
        plan=json.loads((self.case.root/'manual-action/plan.json').read_text());plan['jobs'][0]['shell']='ls'
        with self.assertRaises(m.Stop):m.validate_plan(plan)
if __name__=='__main__':unittest.main()
