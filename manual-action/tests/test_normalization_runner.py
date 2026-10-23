"""Generated local Git only: DB-only dispatch and mixed receipt compatibility."""
import copy
import importlib.util
import json
from pathlib import Path
import shutil
import sqlite3
import subprocess
import hashlib
import sys
import types
import unittest

PACKAGE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PACKAGE))
spec = importlib.util.spec_from_file_location('normalization_ingest_fixture', PACKAGE/'tests/test_ingest_runner.py')
fixture = importlib.util.module_from_spec(spec); spec.loader.exec_module(fixture)
m = fixture.m
from normalization_api import Versions
from normalization_receipts import DOMAINS, COUNTS, build_summary, validate_report
from receipt_branch import BRANCH as RECEIPT_BRANCH


def report(status='rules_complete', identity='a'*64):
    active = status != 'running'
    row = {'status': 'rules_complete' if active else 'running', 'selected_rows': 1,
           **dict.fromkeys(COUNTS, 0), 'checkpoint_sha256': 'b'*64 if active else None}
    if active:
        row.update(scanned=1, rules_new=1, pendingreview=1, unresolved=1)
    return {'schema': 'offmenu-db-normalization-report/1', 'input_sha256': identity,
        'status': status, 'stop_reason': None, 'selection': 'all_retained_source_versions',
        'source_originals': 'database_payload_only', 'selected_rows_scope': 'owned_metadata_counter',
        'review_status': 'pending_approved_route', 'gold_status': 'blocked',
        'versions': Versions().as_dict(), 'domains': {d: dict(row) for d in DOMAINS},
        'resources': {'free_disk_bytes': 10*1024**3, 'elapsed_seconds': 1, 'workers': 16}}


class NormalizationReceiptTests(unittest.TestCase):
    def receipt(self):
        return {'schema': 'offmenu-run-receipt/3', 'job_id': 'retained-six-domain-normalization',
            'job_version': 1, 'operation': 'normalize_staged_databases', 'job_key': 'c'*64,
            'implementation_sha256': 'd'*64, 'input_sha256': 'a'*64,
            'observed_at': '2026-10-22T16:00:00Z', 'outcome': 'completed',
            'normalization': build_summary(report())}
    def test_valid_stage_is_not_ai_or_gold_completion(self):
        value = self.receipt(); m.validate_runtime_receipt(value)
        self.assertEqual(value['normalization']['report']['gold_status'], 'blocked')
        self.assertEqual(value['normalization']['report']['review_status'], 'pending_approved_route')
        self.assertTrue(m.receipt_relpath(value).endswith('-completed-'+value['normalization']['progress_sha256']+'.json'))
    def test_raw_private_or_actual_review_claim_is_rejected(self):
        for mutate in (
            lambda x: x.update(source_path='/private/data'),
            lambda x: x['domains']['recipes'].update(payload='private source'),
            lambda x: x['domains']['recipes'].update(accepted=1),
            lambda x: x['domains']['recipes'].update(scanned=True),
            lambda x: x.update(gold_status='ready'),
            lambda x: x['domains']['recipes'].update(status='pending'),
            lambda x: x.update(stop_reason='disk_reserve'),
            lambda x: x['domains']['recipes'].update(pendingreview=0),
            lambda x: x['domains']['recipes'].update(selected_rows=2),
            lambda x: x['domains'].update(inventory={})): 
            value = report(); mutate(value)
            with self.assertRaises(ValueError): validate_report(value)
    def test_digest_and_input_binding_are_checked(self):
        for mutate in (
            lambda x: x.update(input_sha256='f'*64),
            lambda x: x['normalization'].update(progress_sha256='f'*64),
            lambda x: x.update(outcome='partial')):
            value = self.receipt(); mutate(value)
            with self.assertRaises(m.Stop): m.validate_runtime_receipt(value)
    def test_plan_must_be_normalization_and_isolated(self):
        value = json.loads((PACKAGE/'plan.json').read_text())
        self.assertEqual(m.validate_plan(value)['operation'], 'normalize_staged_databases')
        value['receipt_transport'] = 'legacy-same-branch'
        with self.assertRaises(m.Stop): m.validate_plan(value)


class NormalizationRunnerTests(unittest.TestCase):
    def setUp(self):
        self.case = fixture.IngestRunnerTests('test_ingest_runs_all_domain_and_completed_plan_is_idempotent')
        self.case.setUp(); self.root = self.case.case.root
        self.git = self.case.case.git_at; self.calls = 0; self.identity = 'a'*64
        self.old_receipt = None
    def tearDown(self): self.case.tearDown()
    def install(self):
        for pattern in ('normalization_*.py', 'receipt_*.py'):
            for path in PACKAGE.glob(pattern): shutil.copy(path, self.root/'manual-action'/path.name)
        for name in ('normalize_recipes.py', 'ingest_storage_sizes.py', 'ingest_household_preparation.py', 'plan.json'):
            shutil.copy(PACKAGE/name, self.root/'manual-action'/name)
        self.git(self.root, 'add', 'manual-action'); self.git(self.root, 'commit', '-m', 'Reviewed generated DB normalization plan')
        self.git(self.root, 'push', 'origin', m.BRANCH)
    def runner(self, fail_run=False):
        runner = self.case.case.new_runner()
        def prepare(state, config):
            self.assertEqual(state, runner.state/'ingest')
            self.assertEqual(config['workers'], json.loads((self.root/'manual-action'/'plan.json').read_text())['max_parallel'])
            return {'input_sha256': self.identity, 'config': config}
        def run(prepared, report_callback):
            self.calls += 1
            if fail_run: raise AssertionError('must not start after cancelled startup')
            report_callback(report('running', self.identity))
            final = report(identity=self.identity); report_callback(final); return final
        runner.normalization_engine = lambda: types.SimpleNamespace(prepare_default=prepare, run_prepared=run)
        runner.ingest_engine = lambda: (_ for _ in ()).throw(AssertionError('ingest forbidden'))
        runner.inspector = lambda: (_ for _ in ()).throw(AssertionError('source inspection forbidden'))
        return runner
    def remote_receipts(self):
        remote = self.case.case.remote
        names = self.git(remote, 'ls-tree', '-r', '--name-only', 'refs/heads/'+RECEIPT_BRANCH).splitlines()
        return {name: self.git(remote, 'show', 'refs/heads/'+RECEIPT_BRANCH+':'+name) for name in names}
    def test_normalization_dispatch_preserves_code_and_public_custody(self):
        self.install(); initial = self.case.case.head(); runner = self.runner()
        self.assertEqual(runner.run_plan(), 0); self.assertEqual(self.calls, 1)
        self.assertEqual(self.case.case.head(), initial)
        values = [json.loads(v) for v in self.remote_receipts().values()]
        receipts = [v for v in values if v['schema'] == 'offmenu-run-receipt/3']
        self.assertEqual({v['outcome'] for v in receipts}, {'running', 'completed'})
        self.assertTrue(all(set(v['normalization']['report']['domains']) == set(DOMAINS) for v in receipts))
        self.assertEqual(self.git(self.root, 'diff', '--cached', '--name-only'), '')
        self.assertNotIn(str(self.root), json.dumps(values))
    def test_push_failure_retains_spool_then_batch_recovers_exact_bytes(self):
        self.install(); runner = self.runner(); original = runner.git
        def fail(*args, **kwargs):
            if args[0] == 'push': raise m.Stop('generated_push_failure_preserved')
            return original(*args, **kwargs)
        runner.git = fail
        self.assertEqual(runner.run_plan(), 2)
        spools = list((runner.state/'normalization-pending').glob('*.json'))
        self.assertEqual(len(spools), 2)
        old = {m.receipt_relpath(json.loads(p.read_text())['receipt']): m.canonical(json.loads(p.read_text())['receipt']).decode().strip() for p in spools}
        self.case.case.close(runner); retry = self.runner()
        self.assertEqual(retry.run_plan(), 0)
        self.assertEqual(list((retry.state/'normalization-pending').glob('*.json')), [])
        remote = self.remote_receipts()
        self.assertTrue(all(remote[name] == body for name, body in old.items()))
    def test_old_ingest_spool_and_branch_bytes_survive_normalization(self):
        # Real generated ingestion receipt is prepared under the old plan, but
        # its failed transport must not cause ingestion to execute next time.
        plan = json.loads((self.root/'manual-action/plan.json').read_text())
        plan['receipt_transport'] = 'isolated-branch-v1'
        (self.root/'manual-action/plan.json').write_bytes(m.canonical(plan))
        self.git(self.root, 'add', 'manual-action/plan.json'); self.git(self.root, 'commit', '-m', 'Generated old isolated plan')
        self.git(self.root, 'push', 'origin', m.BRANCH)
        oldrunner = self.case.runner(); original = oldrunner.git
        oldrunner.git = lambda *a, **k: (_ for _ in ()).throw(m.Stop('generated_pending')) if a[0] == 'push' else original(*a, **k)
        self.assertEqual(oldrunner.run_plan(), 2)
        oldvalues = [json.loads(p.read_text())['receipt'] for p in (oldrunner.state/'ingest-pending').glob('*.json')]
        self.case.case.close(oldrunner); self.install()
        runner = self.runner(); self.assertEqual(runner.run_plan(), 0)
        remote = self.remote_receipts()
        for value in oldvalues:
            self.assertEqual(remote[m.receipt_relpath(value)], m.canonical(value).decode().strip())
        self.assertEqual(self.case.calls, 1)
    def test_real_run_reads_only_databases_and_reuses_cached_completed_prefix(self):
        # Exercise the actual launcher/pull/reexec, process pool, SQLite cache,
        # independent receipt branch and second-run DB resume on generated data.
        from ingest_store import SCHEMA
        from normalization_core import canonical_json, digest
        self.install()
        for pattern in ('ingest_*.py', 'normalization_*.py', 'receipt_*.py'):
            for source in PACKAGE.glob(pattern):
                shutil.copy(source, self.root/'manual-action'/source.name)
        runner_path = self.root/'manual-action/plan_runner.py'
        runner_path.write_text(runner_path.read_text().replace('RETURN_DIR =',
            'REMOTE_URLS.add('+repr(str(self.case.case.remote))+')\nRETURN_DIR =', 1))
        self.git(self.root, 'add', 'manual-action'); self.git(self.root, 'commit', '-m', 'Generated DB-only launcher fixture')
        self.git(self.root, 'push', 'origin', m.BRANCH)
        state = self.root/'.git/offmenu-runner/ingest'
        directory = state/'staging'; directory.mkdir(parents=True, mode=0o700)
        for domain in DOMAINS:
            payload = {'id': 'one', 'name': 'GENERATED-PRIVATE-SOURCE', 'language': 'en'}
            if domain == 'recipes': payload.update(kind='recipe', ingredients=[], steps=[])
            with sqlite3.connect(directory/(domain+'.sqlite3')) as db:
                db.executescript(SCHEMA)
                for key, value in {'domain':domain, 'binding':'additive_staging_not_app_bound', 'schema_version':'1', 'database_id':domain, 'record_count':'1'}.items():
                    db.execute('INSERT INTO ingest_meta VALUES(?,?)',(key,value))
                db.execute('INSERT INTO sources VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)',
                    ('fixture','v1','/ABSENT-ORIGINAL-NEVER-OPEN','json','fixture','unverified','{}','{}','complete',0,0,0,1))
                db.execute('INSERT INTO records VALUES(?,?,?,?,?,?,?)',
                    ('fixture','v1','one',1,digest(payload),canonical_json(payload),1))
        before = {p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in directory.glob('*.sqlite3')}
        initial = self.case.case.head()
        first = subprocess.run(['./run'], cwd=self.root, capture_output=True, text=True, timeout=45)
        self.assertEqual(first.returncode, 0, first.stdout+first.stderr)
        self.assertIn('Normalizing retained database records only', first.stdout)
        self.assertIn('rules_complete', first.stdout)
        self.assertNotIn('Discovering retained', first.stdout)
        self.assertEqual(self.case.case.head(), initial)
        second = subprocess.run(['./run'], cwd=self.root, capture_output=True, text=True, timeout=45)
        self.assertEqual(second.returncode, 0, second.stdout+second.stderr)
        self.assertIn('workers=0', second.stdout)
        self.assertEqual(before, {p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in directory.glob('*.sqlite3')})
        values = self.remote_receipts()
        self.assertNotIn('GENERATED-PRIVATE-SOURCE', json.dumps(values))
        self.assertNotIn('ABSENT-ORIGINAL', json.dumps(values))
        complete = [json.loads(raw)['normalization']['report'] for raw in values.values()
                    if json.loads(raw).get('schema') == 'offmenu-run-receipt/3' and json.loads(raw)['outcome'] == 'completed']
        self.assertTrue(complete)
        self.assertTrue(all(sum(row['pendingreview'] for row in v['domains'].values()) == 6 for v in complete))

    def test_ctrl_c_during_startup_never_starts_normalization(self):
        self.install(); runner = self.runner()
        receipt = NormalizationReceiptTests().receipt()
        pending = runner.state/'normalization-pending'; pending.mkdir(mode=0o700, parents=True)
        spool = pending/Path(m.receipt_relpath(receipt)).name
        runner.durable_local_json(spool, {'sha256': m.digest(m.canonical(receipt)), 'receipt': receipt})
        runner.materialize_ingest_receipts = lambda values: (_ for _ in ()).throw(KeyboardInterrupt())
        with self.assertRaises(KeyboardInterrupt): runner.run_plan()
        self.assertEqual(self.calls, 0); self.assertTrue(spool.exists())


if __name__ == '__main__': unittest.main()
