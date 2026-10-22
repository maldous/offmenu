"""Synthetic split migration/admission only; never opens retained state."""
from contextlib import closing
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

PACKAGE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PACKAGE))
import plan_runner
import normalization_engine as engine
from normalization_core import CompactNormalizationStore, canonical_json, digest, run_rules, artifact_digest
from ingest_store import SCHEMA, DomainStore
from ingest_pending import store_path
from ingest_storage_sizes import capture_storage_sizes
from ingest_catalog import discover_sources
from runner_paths import resolve_layout

PINS = ('OFFMENU_RUN_LAYOUT', 'OFFMENU_RUN_LEGACY_FIXTURE', 'OFFMENU_RUN_FD',
        'OFFMENU_RUN_LAYOUT_SHA256', 'OFFMENU_RUN_LAYOUT_BINDING_SHA256')


class InlineRules:
    def __init__(self, workers=1, **kwargs):
        self.actual_workers = 0
        self.check = kwargs['check_cancel']
    def __enter__(self): return self
    def __exit__(self, *args): pass
    def run_batch(self, records, versions=None):
        self.actual_workers = 1
        output = []
        for record in records:
            self.check()
            artifact = run_rules(record, versions=versions)
            sha = artifact_digest(artifact)
            del artifact['source_original']
            output.append({'source': {k: record[k] for k in ('domain', 'source_key', 'source_version', 'record_id', 'content_sha256')},
                           'artifact': artifact, 'artifact_sha256': sha, 'error_code': None})
        return output


class RunnerLayoutIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.environment = patch.dict(os.environ, {k: v for k, v in os.environ.items() if k not in PINS}, clear=True)
        self.environment.start()
        self.addCleanup(self.environment.stop)

    def directory(self, name):
        p = self.base / name
        p.mkdir(parents=True, mode=0o700)
        return p

    def configure(self):
        roots = {k: str(self.directory(k)) for k in ('runtime', 'public_staging', 'normalization', 'household')}
        roots.update(schema='offmenu-runner-layout/1', lock=str(self.base / 'singleton.lock'))
        path = self.base / 'layout.json'
        path.write_text(json.dumps(roots))
        path.chmod(0o600)
        os.environ['OFFMENU_RUN_LAYOUT'] = str(path)
        return path, roots

    def runner(self, name='checkout'):
        root = self.directory(name)
        (root / '.git').mkdir(mode=0o700)
        runner = plan_runner.Runner(root)
        runner.preconditions = lambda: None  # No real Git, remote or runner job.
        return runner

    def acquire(self, runner):
        runner.acquire()
        self.addCleanup(lambda: os.close(runner.lock))

    def test_missing_selector_refuses_runner_and_diagnostics_before_creation(self):
        root = self.directory('missing')
        (root / '.git').mkdir(mode=0o700)
        with self.assertRaises(plan_runner.Stop): plan_runner.Runner(root)
        from relational_readiness import build_report
        for operation in (lambda: capture_storage_sizes(root / 'ingest'),
                          lambda: DomainStore('ingredients', root / 'ingest'),
                          lambda: discover_sources({'roots': [str(root)], 'state_dir': str(root / 'ingest')}),
                          lambda: build_report(root / 'ingest')):
            with self.assertRaisesRegex(ValueError, 'runner_layout_required'): operation()
        self.assertEqual(list((root / '.git').iterdir()), [])
        self.assertFalse((root / 'ingest').exists())
        proc = subprocess.run([sys.executable, '-B', str(PACKAGE / 'plan_runner.py')],
                              env=dict(os.environ), capture_output=True, text=True, timeout=10)
        self.assertEqual(proc.returncode, 2)
        self.assertIn('runner_layout_required', proc.stdout)

    def test_shared_runner_lock_and_admission_reexec_binding(self):
        config, roots = self.configure()
        first = self.runner('one')
        self.acquire(first)
        admitted = json.loads((first.state / 'layout-admission.json').read_text())
        self.assertEqual(admitted['config_sha256'], first.layout.config_digest)
        self.assertEqual(admitted['singleton']['inode'], os.fstat(first.lock).st_ino)
        self.assertEqual(set(admitted['roots']), {'runtime', 'public_staging', 'normalization', 'household'})
        second = self.runner('two')
        with self.assertRaisesRegex(plan_runner.Stop, 'another_run_is_active'): second.acquire()
        first.textgit = lambda *args: '0' * 40
        first.remote_head = '1' * 40
        with patch.object(plan_runner.os, 'execve') as execute:
            first.reexec()
        passed = execute.call_args.args[2]
        self.assertEqual(passed['OFFMENU_RUN_LAYOUT_SHA256'], first.layout.config_digest)
        self.assertEqual(passed['OFFMENU_RUN_LAYOUT_BINDING_SHA256'], first.layout.admission_digest(first.lock))
        config.write_text(config.read_text() + '\n')
        with patch.object(plan_runner.os, 'execve') as execute:
            with self.assertRaises(ValueError): first.reexec()
            execute.assert_not_called()

    def test_changed_or_dropped_selector_cannot_create_checkpoint_or_old_lock(self):
        self.configure()
        runner = self.runner()
        self.acquire(runner)
        del os.environ['OFFMENU_RUN_LAYOUT']
        with self.assertRaises(ValueError): runner.checkpoint('checking')
        self.assertFalse((runner.state / 'checkpoint.json').exists())
        self.assertFalse((runner.gitdir / 'offmenu-runner').exists())
        self.assertFalse((runner.gitdir / 'offmenu-run.lock').exists())

    def test_consumers_share_split_paths_without_old_nested_creation(self):
        self.configure()
        runner = self.runner()
        self.acquire(runner)
        state = runner.state / 'ingest'
        with DomainStore('inventory', state) as store:
            self.assertEqual(store.path, runner.layout.household / 'staging/inventory.sqlite3')
        with DomainStore('ingredients', state) as store:
            self.assertEqual(store.path, runner.layout.public_staging / 'ingredients.sqlite3')
        with CompactNormalizationStore(state, 'ingredients') as store:
            self.assertEqual(store.path, runner.layout.normalization / 'compact-ingredients.sqlite3')
        from ingest_evidence import EvidenceCollector
        from ingest_errors import collect_error_snapshot
        from ingest_relational_targets import _store, relational_outputs_available
        self.assertEqual(EvidenceCollector([], {'state_dir': str(state)}).path,
                         state / 'ingest-evidence.private.json')
        self.assertEqual(_store(state, 'inventory'), runner.layout.household / 'staging/inventory.sqlite3')
        self.assertFalse(relational_outputs_available(state))
        self.assertIn('domains', capture_storage_sizes(state))
        self.assertIn('domains', collect_error_snapshot(state))
        self.assertFalse((state / 'private-household').exists())
        self.assertFalse((state / 'normalization-private').exists())
        self.assertFalse((state / 'staging').exists())

    def test_pending_receipt_recovery_keeps_original_canonical_identity(self):
        self.configure()
        runner = self.runner()
        self.acquire(runner)
        from normalization_api import Versions
        from normalization_receipts import DOMAINS, COUNTS, build_summary
        row = {'status': 'running', 'selected_rows': 1,
               **dict.fromkeys(COUNTS, 0), 'checkpoint_sha256': None}
        report = {'schema': 'offmenu-db-normalization-report/1', 'input_sha256': 'a' * 64,
                  'status': 'running', 'stop_reason': None, 'selection': 'all_retained_source_versions',
                  'source_originals': 'database_payload_only', 'selected_rows_scope': 'owned_metadata_counter',
                  'review_status': 'pending_approved_route', 'gold_status': 'blocked',
                  'versions': Versions().as_dict(), 'domains': {d: dict(row) for d in DOMAINS},
                  'resources': {'free_disk_bytes': 1024**3, 'elapsed_seconds': 1, 'workers': 1}}
        receipt = {'schema': 'offmenu-run-receipt/3', 'job_id': 'retained-six-domain-normalization',
                   'job_version': 1, 'operation': 'normalize_staged_databases', 'job_key': 'c' * 64,
                   'implementation_sha256': 'd' * 64, 'input_sha256': 'a' * 64,
                   'observed_at': '2026-10-22T16:00:00Z', 'outcome': 'running',
                   'normalization': build_summary(report)}
        raw = plan_runner.canonical(receipt)
        pending = runner.state / 'normalization-pending'
        pending.mkdir(mode=0o700)
        spool = pending / Path(plan_runner.receipt_relpath(receipt)).name
        spool.write_bytes(plan_runner.canonical({'sha256': plan_runner.digest(raw), 'receipt': receipt}))
        captured = []
        runner.materialize_ingest_receipts = lambda values: captured.extend(plan_runner.canonical(v) for v in values)
        runner.prepare_household_schema = lambda: {'status': 'synthetic'}
        class StopBeforeDatabase(Exception): pass
        class Engine:
            @staticmethod
            def prepare_default(*args): raise StopBeforeDatabase()
        runner.normalization_engine = lambda: Engine
        with self.assertRaises(StopBeforeDatabase):
            runner.run_normalization_plan({'max_parallel': 1}, {})
        self.assertEqual(captured, [raw])
        self.assertFalse(spool.exists())
        self.assertNotIn(b'layout', raw)
        self.assertEqual(json.loads(captured[0])['implementation_sha256'], 'd' * 64)

    def seed_source(self, directory):
        directory.mkdir(parents=True, mode=0o700)
        path = directory / 'ingredients.sqlite3'
        with sqlite3.connect(path) as db:
            db.executescript(SCHEMA)
            for key, value in {'domain': 'ingredients', 'binding': 'additive_staging_not_app_bound',
                               'schema_version': '1', 'database_id': 'synthetic', 'record_count': '2'}.items():
                db.execute('INSERT INTO ingest_meta VALUES(?,?)', (key, value))
            db.execute('INSERT INTO sources VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)',
                       ('fixture', 'v1', '/ABSENT-ORIGINAL-NEVER-OPEN', 'json', 'fixture', 'unverified', '{}', '{}', 'complete', 0, 2, 0, 1))
            for i in range(2):
                payload = {'name': 'Fixture' + str(i)}
                db.execute('INSERT INTO records VALUES(?,?,?,?,?,?,?)',
                           ('fixture', 'v1', str(i), i, digest(payload), canonical_json(payload), 1))
        path.chmod(0o600)
        return path

    def test_samefs_split_preserves_cache_cursor_and_new_wal_changes_epoch(self):
        old_runtime = self.directory('old-runtime')
        state = old_runtime / 'ingest'
        source = self.seed_source(state / 'staging')
        (state / 'private-household').mkdir(mode=0o700)
        os.environ['OFFMENU_RUN_LEGACY_FIXTURE'] = '1'
        options = {'workers': 1, 'disk_reserve_bytes': 0, 'batch_rows': 1, 'report_interval': .001}
        with patch('normalization_parallel.RulesExecutor', InlineRules):
            first = engine.run_normalization(state, {**options, 'max_rows': 1})
        old_prepared = engine.prepare_default(state, options)
        key = old_prepared['domains']['ingredients']['snapshot_key']
        cursor = CompactNormalizationStore.peek_checkpoint(state, 'ingredients', key)
        self.assertEqual(first['domains']['ingredients']['scanned'], 1)
        before = engine._identity(source)
        public, normalized, household, runtime = (self.base / name for name in ('public', 'normalized', 'household', 'runtime'))
        (state / 'staging').rename(public)
        (state / 'normalization-private').rename(normalized)
        (state / 'private-household').rename(household)
        old_runtime.rename(runtime)
        config = self.base / 'split.json'
        config.write_text(json.dumps({'schema': 'offmenu-runner-layout/1', 'runtime': str(runtime),
                                     'public_staging': str(public), 'normalization': str(normalized),
                                     'household': str(household), 'lock': str(self.base / 'singleton.lock')}))
        config.chmod(0o600)
        del os.environ['OFFMENU_RUN_LEGACY_FIXTURE']
        os.environ['OFFMENU_RUN_LAYOUT'] = str(config)
        runner = self.runner()
        self.acquire(runner)
        new_state = runtime / 'ingest'
        prepared = engine.prepare_default(new_state, options)
        self.assertEqual(before, engine._identity(public / source.name))
        self.assertEqual(old_prepared['input_sha256'], prepared['input_sha256'])
        self.assertEqual(cursor, CompactNormalizationStore.peek_checkpoint(new_state, 'ingredients', key))
        with patch('normalization_parallel.RulesExecutor', InlineRules):
            resumed = engine.run_prepared(prepared)
        self.assertEqual(resumed['domains']['ingredients']['scanned'], 2)
        with patch.object(InlineRules, 'run_batch', side_effect=AssertionError('completed rows replayed')):
            reused = engine.run_normalization(new_state, options)
        self.assertEqual(reused['domains'], resumed['domains'])
        self.assertEqual(store_path(new_state, 'ingredients'), public / 'ingredients.sqlite3')
        self.assertEqual(store_path(new_state, 'inventory'), household / 'staging/inventory.sqlite3')
        self.assertFalse((new_state / 'staging').exists())
        # A real tiny fixture WAL/content change starts a truthful new epoch.
        with closing(sqlite3.connect(public / source.name)) as db:
            db.execute('PRAGMA journal_mode=WAL')
            changed = {'name': 'Changed fixture'}
            db.execute('UPDATE records SET payload_json=?,content_sha256=? WHERE record_id=?',
                       (canonical_json(changed), digest(changed), '0'))
            db.commit()
            # Restore the fixture's quiescent journal mode after the WAL write;
            # admission must not race creation of read-only WAL sidecars.
            db.execute('PRAGMA journal_mode=DELETE').fetchone()
        changed_prepared = engine.prepare_default(new_state, options)
        self.assertNotEqual(changed_prepared['input_sha256'], prepared['input_sha256'])
        with patch('normalization_parallel.RulesExecutor', InlineRules):
            changed_report = engine.run_prepared(changed_prepared)
        self.assertEqual(changed_report['domains']['ingredients']['scanned'], 2)
        self.assertEqual(changed_report['domains']['ingredients']['rules_reused'], 1)
        self.assertEqual(changed_report['domains']['ingredients']['rules_new'], 1)
        self.assertEqual(changed_report['domains']['ingredients']['accepted'], 0)
        self.assertEqual(changed_report['gold_status'], 'blocked')


if __name__ == '__main__': unittest.main()
