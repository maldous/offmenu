"""Generated local Git and SQLite only; no Foo, credentials, or corpus input."""
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import sqlite3
import subprocess
import sys
import types
import unittest

PACKAGE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PACKAGE))
spec = importlib.util.spec_from_file_location('reconciliation_normalization_fixture', PACKAGE/'tests/test_normalization_runner.py')
fixture = importlib.util.module_from_spec(spec); spec.loader.exec_module(fixture)
m = fixture.m
from normalization_reconciliation_receipts import DOMAINS, COUNTS, build_summary, validate_report
from receipt_branch import BRANCH as RECEIPT_BRANCH


def report(status='cache_complete', identity='a'*64):
    done = status == 'cache_complete'
    row = {'status': 'cache_complete' if done else 'running', 'selected_keys': None,
           **dict.fromkeys(COUNTS, 0), 'exhausted': done,
           'checkpoint_sha256': 'b'*64 if done else None}
    if done: row.update(scanned=1, indexed_new=1)
    return {'schema': 'offmenu-db-reconciliation-report/1', 'input_sha256': identity,
        'policy_sha256': 'e'*64, 'status': status, 'stop_reason': None,
        'selection': 'committed_compact_cache_keys',
        'integrity_reads': 'fixed_staging_database_payload_and_projection_validation',
        'review_status': 'pending_approved_route', 'gold_status': 'blocked', 'entity_merges': 0,
        'domains': {d: dict(row) for d in DOMAINS},
        'resources': {'free_disk_bytes': 10*1024**3, 'elapsed_seconds': 1, 'workers': 1,
            'invocation_rows': 6 if done else 0, 'output_logical_bytes': 65536 if done else 0},
        'capacity': {'status': 'admitted' if done else 'sampling', 'sample_rows': 6 if done else 0,
            'sample_output_bytes': 65536 if done else 0,
            'bytes_per_row_ceiling': 10923 if done else None, 'admitted_rows': 50000 if done else 0,
            'max_rows': 50000, 'max_output_bytes': 128*1024**2}}


class ReconciliationReceiptTests(unittest.TestCase):
    def receipt(self):
        return {'schema': 'offmenu-run-receipt/4', 'job_id': 'retained-six-domain-reconciliation',
            'job_version': 1, 'operation': 'reconcile_normalized_cache', 'job_key': 'c'*64,
            'implementation_sha256': 'd'*64, 'input_sha256': 'a'*64,
            'observed_at': '2026-10-22T17:00:00Z', 'outcome': 'completed',
            'reconciliation': build_summary(report())}
    def test_valid_candidates_are_not_ai_gold_or_verified_merges(self):
        value = self.receipt(); m.validate_runtime_receipt(value)
        self.assertEqual(value['reconciliation']['report']['entity_merges'], 0)
        self.assertEqual(value['reconciliation']['report']['gold_status'], 'blocked')
        self.assertTrue(m.receipt_relpath(value).endswith('-completed-'+value['reconciliation']['progress_sha256']+'.json'))
    def test_private_text_false_completion_and_unbounded_claims_rejected(self):
        mutations = [
            lambda x: x.update(source_path='/private/raw'),
            lambda x: x['domains']['recipes'].update(payload='private text'),
            lambda x: x.update(entity_merges=1), lambda x: x.update(entity_merges=False),
            lambda x: x.update(gold_status='ready'), lambda x: x.update(review_status='accepted'),
            lambda x: x['domains']['recipes'].update(selected_keys=0),
            lambda x: x['domains']['recipes'].update(exhausted=False),
            lambda x: x['domains']['recipes'].update(scanned=True),
            lambda x: x['domains']['recipes'].update(indexed_reused=1),
            lambda x: x['domains']['recipes'].update(quarantine_retries=2),
            lambda x: x.update(stop_reason='disk_reserve'),
            lambda x: x['resources'].update(workers=16),
            lambda x: x['capacity'].update(admitted_rows=50001),
            lambda x: x['capacity'].update(sample_rows=7),
            lambda x: x['domains'].update(inventory={}),
        ]
        for mutate in mutations:
            value = report(); mutate(value)
            with self.assertRaises(ValueError): validate_report(value)
    def test_receipt_digest_binding_and_outcome_are_checked(self):
        for mutate in (
            lambda x: x.update(input_sha256='f'*64),
            lambda x: x['reconciliation'].update(progress_sha256='f'*64),
            lambda x: x.update(outcome='partial'),
            lambda x: x.update(operation='normalize_staged_databases')):
            value = self.receipt(); mutate(value)
            with self.assertRaises(m.Stop): m.validate_runtime_receipt(value)
    def test_plan_is_separate_bounded_single_writer_stage(self):
        value = json.loads((PACKAGE/'plan.json').read_text())
        self.assertEqual(m.validate_plan(value)['operation'], 'reconcile_normalized_cache')
        for change in ({'max_parallel': 16}, {'receipt_transport': 'legacy-same-branch'}):
            bad = copy.deepcopy(value); bad.update(change)
            with self.assertRaises(m.Stop): m.validate_plan(bad)


class ReconciliationRunnerTests(unittest.TestCase):
    setUp = fixture.NormalizationRunnerTests.setUp
    tearDown = fixture.NormalizationRunnerTests.tearDown
    remote_receipts = fixture.NormalizationRunnerTests.remote_receipts
    def install(self):
        for pattern in ('normalization_*.py', 'receipt_*.py', 'ingest_*.py'):
            for source in PACKAGE.glob(pattern): shutil.copy(source, self.root/'manual-action'/source.name)
        for name in ('normalize_recipes.py', 'plan.json'):
            shutil.copy(PACKAGE/name, self.root/'manual-action'/name)
        self.git(self.root, 'add', 'manual-action'); self.git(self.root, 'commit', '-m', 'Generated bounded reconciliation stage')
        self.git(self.root, 'push', 'origin', m.BRANCH)
    def runner(self):
        runner = self.case.case.new_runner()
        def prepare(state, config):
            self.assertEqual(state, runner.state/'ingest')
            self.assertEqual(config['max_rows'], 50000)
            self.assertEqual(config['sample_rows'], 32)
            self.assertEqual(config['max_output_bytes'], 128*1024**2)
            self.assertNotIn('workers', config)
            return {'input_sha256': self.identity}
        def run(prepared, report_callback):
            self.calls += 1
            report_callback(report('running', self.identity))
            final = report(identity=self.identity); report_callback(final); return final
        runner.reconciliation_engine = lambda: types.SimpleNamespace(prepare_default=prepare, run_prepared=run)
        runner.normalization_engine = lambda: (_ for _ in ()).throw(AssertionError('new rules stage forbidden'))
        runner.ingest_engine = lambda: (_ for _ in ()).throw(AssertionError('ingestion forbidden'))
        runner.inspector = lambda: (_ for _ in ()).throw(AssertionError('raw source inspection forbidden'))
        return runner
    def test_dispatch_preserves_code_and_sanitized_custody(self):
        self.install(); initial = self.case.case.head(); runner = self.runner()
        self.assertEqual(runner.run_plan(), 0); self.assertEqual(self.calls, 1)
        self.assertEqual(self.case.case.head(), initial)
        self.assertEqual(self.git(self.root, 'diff', '--cached', '--name-only'), '')
        values = [json.loads(v) for v in self.remote_receipts().values()]
        receipts = [v for v in values if v['schema'] == 'offmenu-run-receipt/4']
        self.assertEqual({v['outcome'] for v in receipts}, {'running', 'completed'})
        self.assertNotIn(str(self.root), json.dumps(values))
    def test_v3_and_v4_spool_recovery_preserves_canonical_bytes(self):
        self.install(); runner = self.runner(); original = runner.git
        old = fixture.NormalizationReceiptTests().receipt()
        pending = runner.state/'normalization-pending'; pending.mkdir(mode=0o700, parents=True)
        path = pending/Path(m.receipt_relpath(old)).name
        runner.durable_local_json(path, {'sha256': m.digest(m.canonical(old)), 'receipt': old})
        runner.git = lambda *a, **k: (_ for _ in ()).throw(m.Stop('generated_push_failure')) if a[0] == 'push' else original(*a, **k)
        self.assertEqual(runner.run_plan(), 2)
        spools = list((runner.state/'reconciliation-pending').glob('*.json'))
        self.assertEqual(len(spools), 2); self.assertTrue(path.exists())
        expected = {m.receipt_relpath(old): m.canonical(old).decode().strip()}
        for spool in spools:
            value = json.loads(spool.read_text())['receipt']
            expected[m.receipt_relpath(value)] = m.canonical(value).decode().strip()
        self.case.case.close(runner); retry = self.runner()
        self.assertEqual(retry.run_plan(), 0)
        actual = self.remote_receipts()
        self.assertTrue(all(actual[name] == raw for name, raw in expected.items()))
        self.assertFalse(path.exists())
        self.assertFalse(list((runner.state/'reconciliation-pending').glob('*.json')))
    def test_ctrl_c_during_spool_recovery_never_starts_followon(self):
        self.install(); runner = self.runner()
        value = ReconciliationReceiptTests().receipt()
        pending = runner.state/'reconciliation-pending'; pending.mkdir(mode=0o700, parents=True)
        spool = pending/Path(m.receipt_relpath(value)).name
        runner.durable_local_json(spool, {'sha256': m.digest(m.canonical(value)), 'receipt': value})
        runner.materialize_ingest_receipts = lambda values: (_ for _ in ()).throw(KeyboardInterrupt())
        with self.assertRaises(KeyboardInterrupt): runner.run_plan()
        self.assertEqual(self.calls, 0); self.assertTrue(spool.exists())


class ReconciliationLauncherTests(unittest.TestCase):
    setUp = ReconciliationRunnerTests.setUp
    tearDown = ReconciliationRunnerTests.tearDown
    install = ReconciliationRunnerTests.install
    remote_receipts = ReconciliationRunnerTests.remote_receipts
    def test_real_run_reuses_cache_without_raw_files_or_second_graph(self):
        from ingest_store import SCHEMA
        from normalization_core import CompactNormalizationStore, canonical_json, digest, run_rules
        self.install()
        runner_path = self.root/'manual-action/plan_runner.py'
        runner_path.write_text(runner_path.read_text().replace('RETURN_DIR =',
            'REMOTE_URLS.add('+repr(str(self.case.case.remote))+')\nRETURN_DIR =', 1))
        self.git(self.root, 'add', 'manual-action'); self.git(self.root, 'commit', '-m', 'Generated reconciliation launcher')
        self.git(self.root, 'push', 'origin', m.BRANCH)
        state = self.root/'.git/offmenu-runner/ingest'
        directory = state/'staging'; directory.mkdir(parents=True, mode=0o700)
        for domain in DOMAINS:
            payload = {'id': 'one', 'name': 'PRIVATE-RECONCILIATION-NAME', 'language': 'en', 'unused': 'RAW-NOT-COPIED-SENTINEL'}
            if domain == 'recipes': payload.update(kind='recipe', ingredients=[], steps=[])
            if domain == 'barcodes': payload.update(barcode='036000291452')
            provenance = {'license': 'fixture', 'provider': 'generated', 'custody': {'fixture': True}, 'rights_status': 'unverified'}
            artifact = run_rules({'domain': domain, 'source_key': 'fixture', 'source_version': 'v1', 'record_id': 'one',
                'content_sha256': digest(payload), 'payload': payload, 'provenance': provenance})
            with sqlite3.connect(directory/(domain+'.sqlite3')) as db:
                db.executescript(SCHEMA)
                for key, value in {'domain':domain, 'binding':'additive_staging_not_app_bound', 'schema_version':'1'}.items():
                    db.execute('INSERT INTO ingest_meta VALUES(?,?)',(key,value))
                db.execute('INSERT INTO sources VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)',
                    ('fixture','v1','/ABSENT-RAW-NEVER-READ','json','generated','fixture','{"fixture":true}','{}','complete',0,0,0,1))
                db.execute('INSERT INTO records VALUES(?,?,?,?,?,?,?)',
                    ('fixture','v1','one',1,digest(payload),canonical_json(payload),1))
            with CompactNormalizationStore(state, domain) as cache:
                cache.db.execute('INSERT INTO rules_cache VALUES(?,?,?,?)', cache.encode(artifact)); cache.db.commit()
        originals = list(directory.glob('*.sqlite3')) + list((state/'normalization-private').glob('compact-*.sqlite3'))
        before = {str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in originals}
        initial = self.case.case.head()
        first = subprocess.run(['./run'], cwd=self.root, capture_output=True, text=True, timeout=45)
        self.assertEqual(first.returncode, 0, first.stdout+first.stderr)
        self.assertIn('Reconciling committed normalization cache only', first.stdout)
        self.assertNotIn('Normalizing retained database records only', first.stdout)
        self.assertNotIn('Discovering retained', first.stdout)
        self.assertEqual(self.case.case.head(), initial)
        outputs = set(state.rglob('*.sqlite3')) - set(originals)
        self.assertEqual(len(outputs), 1)
        graph = outputs.pop()
        with sqlite3.connect(graph.as_uri()+'?mode=ro', uri=True) as db:
            self.assertEqual(db.execute('SELECT COUNT(*) FROM artifacts').fetchone()[0], 6)
            self.assertNotIn('RAW-NOT-COPIED-SENTINEL', '\n'.join(db.iterdump()))
        second = subprocess.run(['./run'], cwd=self.root, capture_output=True, text=True, timeout=45)
        self.assertEqual(second.returncode, 0, second.stdout+second.stderr)
        self.assertEqual(set(state.rglob('*.sqlite3')) - set(originals), {graph})
        self.assertEqual(before, {str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in originals})
        values = self.remote_receipts()
        self.assertNotIn('PRIVATE-RECONCILIATION-NAME', json.dumps(values))
        self.assertNotIn('RAW-NOT-COPIED-SENTINEL', json.dumps(values))
        self.assertNotIn('ABSENT-RAW', json.dumps(values))
        self.assertEqual(self.git(self.root, 'diff', '--cached', '--name-only'), '')


if __name__ == '__main__': unittest.main()
