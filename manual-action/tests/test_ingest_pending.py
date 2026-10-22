import hashlib
import io
import json
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from unittest import mock
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from ingest_api import DOMAINS
from ingest_engine import run_ingest, pending_snapshot, completed_outputs_available, sanitize_report
from ingest_pending import collect_pending_work, sanitize_pending_work, COUNTS, STATES
from ingest_store import DomainStore, _fingerprint, _json


class PendingTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.state = self.root / 'state'
        self.state.mkdir()
        self.config = {'state_dir': str(self.state), 'reserve_bytes': 0, 'batch_size': 1, 'terminal_progress': False}

    def tearDown(self):
        self.temp.cleanup()

    def source(self, name, domain='recipes', **fields):
        path = self.root / (name + '.jsonl')
        path.write_text('{}\n')
        return {'id': name, 'path': str(path), 'format': 'jsonl', 'domain': domain, 'provider': 'PRIVATE_PROVIDER_' + name, **fields}

    def snapshot(self, sources, **kw):
        return collect_pending_work(sources, self.state, **kw)

    def test_mixed_queue_and_assignment_totals(self):
        complete = self.source('complete')
        partial = self.source('partial')
        new = self.source('new')
        failed = self.source('failed')
        held = self.source('held', restricted=True)
        unsupported = self.source('unsupported', disposition='unsupported')
        unqualified = self.source('document', disposition='documentation')
        with DomainStore('recipes', self.state, self.config) as store:
            store.ingest(complete, [{'id': 'done'}])
            store.config['max_rows_per_source'] = 1
            store.ingest(partial, [{'id': 'first'}, {'id': 'next'}])
            def broken():
                raise ValueError('PRIVATE EXCEPTION CONTENT')
                yield
            store.ingest(failed, broken())
        report = self.snapshot([complete, partial, new, failed, held, unsupported, unqualified])
        summary = report['summary']
        recipes = summary['domains']['recipes']
        for state in ('completed', 'partial', 'not_yet_read', 'failed', 'held', 'unsupported', 'unqualified'):
            self.assertEqual(recipes[state], 1, state)
        self.assertEqual(recipes['files_remaining'], 4)
        self.assertEqual(recipes['assignments_total'], sum(recipes[k] for k in STATES))
        self.assertEqual(summary['awaiting_input_domains'], [])
        self.assertEqual(summary['domains']['inventory']['assignments_total'], 0)
        self.assertIsNone(summary['totals']['records_remaining'])
        self.assertIsNone(summary['totals']['records_to_write'])
        self.assertIsNone(summary['totals']['processed_bytes'])
        private = next(r for r in report['sources'] if r.get('path') == partial['path'])
        self.assertEqual((private['cursor'], private['next_reason']), (1, 'resume_from_cursor'))
        self.assertEqual(private['provider'], partial['provider'])
        encoded = json.dumps(summary)
        self.assertNotIn(str(self.root), encoded)
        self.assertNotIn('PRIVATE', encoded)
        self.assertNotIn('EXCEPTION', json.dumps(report))

    def test_reliable_expected_counts_zero_and_cursor_not_write_counts(self):
        partial = self.source('expected')
        zero = self.source('zero')
        historical = self.source('historical', metadata={'historical_rows': 999999})
        for source, expected in ((partial, 4), (zero, 0)):
            version = hashlib.sha256(_json(_fingerprint(source)).encode()).hexdigest()
            source['expected_records'] = {'reliable': True, 'unit': 'adapter_records', 'domain': 'recipes', 'source_version': version, 'count': expected}
        with DomainStore('recipes', self.state, {**self.config, 'max_rows_per_source': 1}) as store:
            store.ingest(partial, [{'id': 'one'}, {'id': 'two'}])
        report = self.snapshot([partial, zero, historical])
        rows = {row['path']: row for row in report['sources'] if row.get('path')}
        self.assertEqual(rows[partial['path']]['records_remaining'], 3)
        self.assertEqual(rows[zero['path']]['records_remaining'], 0)
        self.assertIsNone(rows[historical['path']]['records_remaining'])
        self.assertIsNone(rows[partial['path']]['records_to_write'])
        self.assertEqual(report['summary']['totals']['records_remaining_known'], 3)
        self.assertEqual(report['summary']['totals']['records_remaining_unknown'], 1)
        zero['expected_records']['unit'] = 'raw_source_rows'
        self.assertIsNone(self.snapshot([zero])['sources'][0]['records_remaining'])

    def test_changed_source_cannot_reuse_complete_or_expected_count(self):
        source = self.source('changed')
        with DomainStore('recipes', self.state, self.config) as store:
            result = store.ingest(source, [{'id': 'one'}])
        source['expected_records'] = {'reliable': True, 'unit': 'adapter_records', 'domain': 'recipes', 'source_version': result['source_version'], 'count': 1}
        Path(source['path']).write_text('{"changed":true}\n')
        detail = self.snapshot([source])['sources'][0]
        self.assertEqual(detail['status'], 'not_yet_read')
        self.assertEqual(detail['next_reason'], 'source_version_changed')
        self.assertIsNone(detail['cursor'])
        self.assertIsNone(detail['records_remaining'])

    def test_same_path_different_assignment_key_is_not_false_complete(self):
        source = self.source('assignment-key')
        with DomainStore('recipes', self.state, self.config) as store:
            store.ingest(source, [{'id': 'one'}])
        other = dict(source, id='different-logical-assignment')
        detail = self.snapshot([other])['sources'][0]
        self.assertEqual(detail['status'], 'not_yet_read')
        self.assertIsNone(detail['cursor'])

    def test_real_native_reference_reuse_and_source_mutation(self):
        path = self.root / 'native.sqlite'
        with sqlite3.connect(path) as db:
            db.executescript('CREATE TABLE code_keys(barcode TEXT PRIMARY KEY);INSERT INTO code_keys VALUES("001");')
        source = {'id': 'native', 'path': str(path), 'format': 'sqlite', 'domain': 'barcodes', 'provider': 'off', 'existing_store': True, 'loaded': True}
        report = run_ingest([source], self.config)
        self.assertEqual(report['pending_work']['domains']['barcodes']['reused'], 1)
        self.assertEqual(self.snapshot([source])['summary']['domains']['barcodes']['reused'], 1)
        with sqlite3.connect(path) as db:
            db.execute('INSERT INTO code_keys VALUES("002")')
        changed = self.snapshot([source])['summary']['domains']['barcodes']
        self.assertEqual(changed['reused'], 0)
        self.assertEqual(changed['not_yet_read'], 1)

    def test_loaded_claim_not_native_proof_and_unrecognized_native_schema(self):
        claim = self.source('claim', 'barcodes', loaded=True)
        self.assertEqual(self.snapshot([claim])['sources'][0]['next_reason'], 'catalog_loaded_claim_unverified')
        path = self.root / 'unrecognized.sqlite'
        with sqlite3.connect(path) as db:
            db.execute('CREATE TABLE unrelated(value TEXT)')
        source = {'id': 'unknown-db', 'path': str(path), 'format': 'sqlite', 'domain': 'barcodes', 'existing_store': True}
        run_ingest([source], self.config)
        report = self.snapshot([source])
        self.assertEqual(report['summary']['domains']['barcodes']['reused'], 0)
        self.assertEqual(report['summary']['domains']['barcodes']['unqualified'], 1)

    def test_private_is_app_managed_not_external_input(self):
        fake = self.source('private', 'user_profiles')
        summary = self.snapshot([fake])['summary']
        self.assertEqual(summary['domains']['user_profiles']['awaiting_input'], 0)
        self.assertEqual(summary['domains']['user_profiles']['assignments_total'], 0)
        self.assertEqual(summary['scope']['app_managed_assignments']['user_profiles'], 1)
        self.assertEqual(summary['domains']['inventory']['assignments_total'], 0)
        self.assertEqual(summary['awaiting_input_domains'], [])
        real = dict(fake, metadata={'user_supplied': True, 'household_scope': True})
        self.assertEqual(self.snapshot([real])['summary']['domains']['user_profiles']['not_yet_read'], 0)

    def test_truncated_catalog_and_unassigned_entries_not_claimed_complete(self):
        source = self.source('excluded', domains=[], disposition='excluded')
        report = self.snapshot([source], catalog_complete=False)
        self.assertEqual(report['summary']['unassigned_sources'], 1)
        self.assertFalse(report['summary']['catalog_complete'])
        self.assertIsNone(report['summary']['totals']['records_remaining'])
        self.assertIsNone(report['summary']['totals']['records_to_write'])
        self.assertEqual(report['summary']['totals']['assignments_total'], 0)
        self.assertEqual(report['sources'][-1]['path'], source['path'])

    def test_adapter_metadata_identity_and_no_recognized_result_survive_restart(self):
        source = self.source('not-recognized', 'dietary')
        report = run_ingest([source], self.config)
        self.assertEqual(report['pending_work']['domains']['dietary']['unsupported'], 1)
        prepared = {'sources': [source], 'config': self.config}
        summary = pending_snapshot(prepared)
        self.assertEqual(summary['domains']['dietary']['unsupported'], 1)
        self.assertEqual(summary['domains']['dietary']['completed'], 0)

    def test_missing_report_metadata_never_blocks_ingestion(self):
        source = self.source('works')
        def adapter(domain, sources, context):
            return {'status': 'complete', 'sources': [context.ingest(s, [{'id': 'safe'}]) for s in sources]}
        with mock.patch('ingest_engine.collect_pending_work', side_effect=ValueError('PRIVATE SECRET')):
            result = run_ingest([source], self.config, adapters={'recipes': adapter})
        self.assertEqual(result['domains']['recipes']['written'], 1)
        self.assertEqual(result['pending_work']['status'], 'unknown')
        self.assertNotIn('PRIVATE', json.dumps(result))

    def test_missing_reporting_module_import_never_blocks_ingestion(self):
        source = self.source('missing-helper')
        code = r"""
import builtins, json, sys
original = builtins.__import__
def block(name, *args, **kwargs):
    if name == 'ingest_pending':
        raise ImportError('fixture reporting module missing')
    return original(name, *args, **kwargs)
builtins.__import__ = block
from ingest_engine import run_ingest
source = json.loads(sys.argv[1])
config = json.loads(sys.argv[2])
def adapter(domain, sources, context):
    return {'status': 'complete', 'sources': [context.ingest(s, [{'id': 'still-loaded'}]) for s in sources]}
report = run_ingest([source], config, adapters={'recipes': adapter})
assert report['domains']['recipes']['written'] == 1, report
assert report['pending_work']['status'] == 'unknown', report
print('fixture loaded despite unavailable reporting helper')
"""
        result = subprocess.run([sys.executable, '-c', code, json.dumps(source), json.dumps(self.config)],
            cwd=Path(__file__).resolve().parents[1], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('fixture loaded despite', result.stdout)

    def test_snapshot_does_not_instantiate_writer_or_scan_source_payload(self):
        source = self.source('readonly')
        with DomainStore('recipes', self.state, self.config) as store:
            store.ingest(source, [{'id': 'one'}])
        queries = []
        real_connect = sqlite3.connect
        def connect(*args, **kwargs):
            self.assertIn('?mode=ro', args[0])
            db = real_connect(*args, **kwargs)
            db.set_trace_callback(queries.append)
            return db
        with mock.patch('ingest_pending.sqlite3.connect', side_effect=connect), mock.patch.object(DomainStore, '__init__', side_effect=AssertionError('writer forbidden')):
            report = self.snapshot([source])
        self.assertEqual(report['summary']['domains']['recipes']['completed'], 1)
        self.assertFalse(any('COUNT(' in q.upper() or 'FROM records' in q for q in queries))

    def test_output_guard_detects_same_database_id_count_but_mutated_file(self):
        source = self.source('guard')
        def adapter(domain, sources, context):
            return {'status': 'complete', 'sources': [context.ingest(s, [{'id': 'safe'}]) for s in sources]}
        config = {**self.config, 'catalog_sha256': 'a' * 64}
        run_ingest([{**source, 'domains': list(DOMAINS)}], config, adapters={d: adapter for d in DOMAINS})
        prepared = {'config': config, 'catalog_sha256': 'a' * 64}
        self.assertTrue(completed_outputs_available(prepared))
        path = self.state / 'staging' / 'recipes.sqlite3'
        with sqlite3.connect(path) as db:
            db.execute("UPDATE records SET payload_json='{}'")
        self.assertFalse(completed_outputs_available(prepared))

    def test_public_allowlist_and_startup_final_callback_dashboard(self):
        raw = {'status': 'available', 'path': 'SECRET', 'awaiting_input_domains': ['SECRET', 'inventory'], 'domains': {'recipes': {'completed': 2, 'provider': 'SECRET', 'records_remaining': 'SECRET'}}}
        safe = sanitize_pending_work(raw)
        self.assertNotIn('SECRET', json.dumps(safe))
        self.assertEqual(safe['awaiting_input_domains'], ['inventory'])
        source = self.source('callback')
        seen = []
        def adapter(domain, sources, context):
            return {'status': 'complete', 'sources': [context.ingest(s, [{'id': 'one'}]) for s in sources]}
        output = io.StringIO()
        with redirect_stdout(output):
            run_ingest([source], {**self.config, 'terminal_progress': True}, seen.append, {'recipes': adapter})
        self.assertEqual(seen[0]['pending_work']['domains']['recipes']['not_yet_read'], 1)
        self.assertEqual(seen[-1]['pending_work']['domains']['recipes']['completed'], 1)
        self.assertEqual(seen[0]['domains']['recipes']['sources_total'], 1)
        self.assertIn('files-to-read=', output.getvalue())
        self.assertNotIn(str(self.root), output.getvalue())
        for name in ('pending-work.json', 'pending-work.private.json'):
            self.assertTrue((self.state / name).is_file())
            self.assertEqual((self.state / name).stat().st_mode & 0o777, 0o600)
        self.assertNotIn('source_key', json.dumps(sanitize_report(seen[-1])['pending_work']))


if __name__ == '__main__':
    unittest.main()
