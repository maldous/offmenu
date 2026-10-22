"""Generated fixtures only: no host sources, downloads or live runner actions."""
import copy
import json
from pathlib import Path
import sqlite3
import sys
import tempfile
import threading
import unittest
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from ingest_api import DOMAINS
from ingest_engine import run_ingest, sanitize_report
from ingest_errors import (ERROR_CLASSES, ERROR_REASONS, ORIGINS, classify_error,
                           collect_error_snapshot, sanitize_error_telemetry)
from ingest_recipes import UnsupportedSource, MalformedRecord
from ingest_store import DomainStore
import plan_runner


class ErrorTelemetryTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.state = self.root / 'state'
        self.path = self.root / 'generated.jsonl'
        self.path.write_text('{}\n')
        self.source = {'id': 'generated-private-source', 'path': str(self.path),
                       'format': 'jsonl', 'domain': 'recipes'}
        self.config = {'state_dir': str(self.state), 'reserve_bytes': 0,
                       'terminal_progress': False, 'batch_size': 1, 'report_interval': 1}

    def tearDown(self):
        self.tmp.cleanup()

    def test_exact_reason_tokens_and_unknown_class_never_copy_messages(self):
        self.assertEqual(classify_error(UnsupportedSource('unrecognized_recipe_or_lead_only')),
                         ('UnsupportedSource', 'unrecognized_recipe_or_lead_only'))
        self.assertEqual(classify_error(MalformedRecord('duplicate_json_key')),
                         ('MalformedRecord', 'duplicate_json_key'))
        for message in ('/private/SECRET', 'duplicate_json_key: SECRET', 'duplicate_json_key\nSECRET'):
            self.assertEqual(classify_error(ValueError(message)), ('ValueError', 'other_or_unavailable'))
        SecretClass = type('SECRET', (Exception,), {})
        self.assertEqual(classify_error(SecretClass('SECRET')), ('source_error', 'other_or_unavailable'))

    def test_public_telemetry_is_fixed_schema(self):
        value = {'status': 'available', 'class_counts': {'UnsupportedSource': 3, 'SECRET': 8, 'ValueError': True},
                 'origin_counts': {'adapter_callback': 3, 'SECRET': 8},
                 'reason_counts': {'unrecognized_recipe_or_lead_only': 3, '/private/SECRET': 8},
                 'source_key': 'SECRET', 'source_version': 'SECRET', 'path': 'SECRET', 'message': 'SECRET'}
        safe = sanitize_report({'domains': {'recipes': {'error_telemetry': value}}})
        self.assertNotIn('SECRET', json.dumps(safe))
        self.assertEqual(safe['domains']['recipes']['error_telemetry']['class_counts'], {'UnsupportedSource': 3})

    def test_readonly_snapshot_groups_durable_classes_without_payload_or_schema_changes(self):
        with DomainStore('recipes', self.state, self.config) as store:
            def rows():
                store.record_error(self.source, UnsupportedSource('SECRET'))
                yield {'id': 'bad', 'relations': [9], 'raw_source': 'SECRET'}
            first = store.ingest(self.source, rows())
            before = list(store.db.execute('SELECT source_key,version,cursor,written,errors,status FROM sources'))
            schema = list(store.db.execute('SELECT sql FROM sqlite_master ORDER BY name'))
            snapshot = collect_error_snapshot(self.state)
            self.assertEqual(before, list(store.db.execute('SELECT source_key,version,cursor,written,errors,status FROM sources')))
            self.assertEqual(schema, list(store.db.execute('SELECT sql FROM sqlite_master ORDER BY name')))
        telemetry = snapshot['summary']['recipes']
        self.assertEqual(telemetry['class_counts'], {'UnsupportedSource': 1, 'TypeError': 1})
        self.assertEqual(telemetry['origin_counts'], {'adapter_callback': 1, 'record_or_stream': 1})
        self.assertEqual(telemetry['reason_counts'], {})
        self.assertEqual(telemetry['historical_reasons'], 'not_recorded')
        self.assertNotIn('SECRET', json.dumps(snapshot))
        detail = snapshot['domains']['recipes']['sources']
        self.assertTrue(all(row['source_version'] == first['source_version'] for row in detail))
        self.assertTrue(all('source_key' in row for row in detail))
        self.assertNotIn('source_key', json.dumps(snapshot['summary']))
        self.assertEqual(snapshot['summary']['ingredients']['status'], 'not_created')

    def test_unowned_or_unreadable_metadata_is_unknown_not_zero_evidence(self):
        path = self.state / 'staging/recipes.sqlite3'
        path.parent.mkdir(parents=True)
        with sqlite3.connect(path) as db:
            db.execute('CREATE TABLE precious(value TEXT)')
        before = path.read_bytes()
        self.assertEqual(collect_error_snapshot(self.state)['summary']['recipes']['status'], 'unknown')
        self.assertEqual(path.read_bytes(), before)

    def test_completed_with_errors_has_classes_at_initial_checkpoint_without_reader_replay(self):
        self.path.write_text('\n'.join(json.dumps(row) for row in [
            {'lead': 'generated'}, {'lead': 'generated'}, {'lead': 'generated'},
            {'id': 'valid', 'name': 'Generated soup', 'ingredients': ['salt'], 'instructions': ['Mix']}]) + '\n')
        first = run_ingest([self.source], self.config)
        row = first['domains']['recipes']
        self.assertEqual((row['written'], row['errors'], row['status']), (1, 3, 'partial'))
        self.assertEqual(row['error_telemetry']['class_counts'], {'UnsupportedSource': 3})
        self.assertEqual(row['error_telemetry']['reason_counts'], {'unrecognized_recipe_or_lead_only': 3})
        checkpoints = []
        with mock.patch('ingest_recipes._read_rows', side_effect=AssertionError('completed source replayed')):
            second = run_ingest([self.source], self.config, checkpoints.append)
        self.assertEqual(second['domains']['recipes']['written'], 0)
        self.assertEqual(second['domains']['recipes']['errors'], 3)
        self.assertEqual(checkpoints[0]['domains']['recipes']['error_telemetry']['class_counts'], {'UnsupportedSource': 3})
        self.assertEqual(second['domains']['recipes']['error_telemetry']['reason_counts'], {})
        self.assertEqual(second['pending_work']['domains']['recipes']['partial'], 1)
        self.assertEqual(second['pending_work']['domains']['recipes']['failed'], 0)
        self.assertEqual(second['pending_work']['domains']['recipes']['files_remaining'], 0)
        private = self.state / 'source-errors.private.json'
        self.assertEqual(private.stat().st_mode & 0o777, 0o600)
        self.assertEqual(len(json.loads(private.read_text())['domains']['recipes']['sources']), 1)

    def test_running_checkpoint_exposes_reasons_before_domain_finishes(self):
        release = threading.Event()
        checkpoints = []
        def adapter(domain, sources, context):
            def rows(source):
                context.report_error(source, UnsupportedSource('unrecognized_recipe_or_lead_only'))
                if not release.wait(5):
                    raise AssertionError('running checkpoint missing')
                yield {'id': 'generated'}
            return {'status': 'complete', 'sources': [context.ingest(source, rows(source)) for source in sources]}
        def callback(report):
            checkpoints.append(report)
            row = report['domains']['recipes']
            if row['status'] == 'running' and row['error_telemetry']['reason_counts']:
                release.set()
        report = run_ingest([self.source], self.config, callback, {'recipes': adapter})
        self.assertTrue(release.is_set())
        self.assertEqual(report['domains']['recipes']['written'], 1)
        self.assertTrue(any(row['domains']['recipes']['status'] == 'running' and
                            row['domains']['recipes']['error_telemetry']['class_counts'] == {'UnsupportedSource': 1}
                            for row in checkpoints))
        encoded = json.dumps(checkpoints)
        for private in ('"source_key":', '"source_version":', str(self.root), 'generated-private-source'):
            self.assertNotIn(private, encoded)

    def test_aggregate_classes_are_not_lost_when_private_sample_rolls(self):
        def adapter(domain, sources, context):
            def rows(source):
                context.report_error(source, MalformedRecord('duplicate_json_key'))
                for _ in range(1001):
                    context.report_error(source, UnsupportedSource('unrecognized_recipe_or_lead_only'))
                yield {'id': 'generated'}
            return {'status': 'complete', 'sources': [context.ingest(source, rows(source)) for source in sources]}
        report = run_ingest([self.source], self.config, adapters={'recipes': adapter})
        row = report['domains']['recipes']
        self.assertIn('MalformedRecord', row['error_codes'])
        self.assertEqual(row['error_telemetry']['class_counts'], {'MalformedRecord': 1, 'UnsupportedSource': 1001})
        self.assertEqual(row['error_telemetry']['reason_counts']['duplicate_json_key'], 1)

    def test_resume_replays_callback_observations_but_deduplicates_durable_error_slots(self):
        # Characterization of the existing stream cursor, not a retry policy change.
        calls = []
        def rows(store):
            for n in range(3):
                calls.append(n)
                store.record_error(self.source, UnsupportedSource('unrecognized_recipe_or_lead_only'))
                yield {'id': str(n)}
        with DomainStore('recipes', self.state, {**self.config, 'max_rows_per_source': 1}) as store:
            first = store.ingest(self.source, rows(store))
            self.assertEqual(first['written'], 1)
        with DomainStore('recipes', self.state, self.config) as store:
            second = store.ingest(self.source, rows(store))
            self.assertEqual((second['resumed_from'], second['written'], second['errors']), (1, 2, 3))
        self.assertEqual(calls, [0, 1, 0, 1, 2])
        telemetry = collect_error_snapshot(self.state)['summary']['recipes']
        self.assertEqual(telemetry['class_counts'], {'UnsupportedSource': 3})

    def test_all_retained_versions_are_explicit_not_mislabelled_as_current_run(self):
        with DomainStore('recipes', self.state, self.config) as store:
            store.ingest(self.source, [None])
            self.path.write_text('{"changed": true}\n')
            store.ingest(self.source, [None])
        snapshot = collect_error_snapshot(self.state)
        self.assertEqual(snapshot['summary']['recipes']['durable_scope'], 'all_retained_source_versions')
        self.assertEqual(snapshot['summary']['recipes']['class_counts'], {'TypeError': 2})
        self.assertEqual(len({r['source_version'] for r in snapshot['domains']['recipes']['sources']}), 2)

    def test_optional_diagnostic_failure_does_not_stop_ingestion(self):
        def adapter(domain, sources, context):
            return {'status': 'complete', 'sources': [context.ingest(source, [{'id': 'generated'}]) for source in sources]}
        with mock.patch('ingest_engine.collect_error_snapshot', side_effect=RuntimeError('SECRET')):
            report = run_ingest([self.source], self.config, adapters={'recipes': adapter})
        self.assertEqual(report['domains']['recipes']['written'], 1)
        self.assertEqual(report['domains']['recipes']['error_telemetry']['status'], 'unknown')
        self.assertNotIn('SECRET', json.dumps(report))

    def test_finite_allowlist_fits_existing_receipt_and_spool_size_limit(self):
        runner = object.__new__(plan_runner.Runner)
        telemetry = sanitize_error_telemetry({'status': 'available',
            'class_counts': dict.fromkeys(ERROR_CLASSES, 10**15),
            'reason_counts': dict.fromkeys(ERROR_REASONS, 10**15),
            'origin_counts': dict.fromkeys(ORIGINS, 10**15)})
        report = {'domains': {d: {'status': 'awaiting_user_input', 'error_telemetry': telemetry,
                    'error_codes': sorted(plan_runner.ERROR_CODES),
                    **dict.fromkeys(('read', 'written', 'unchanged', 'errors', 'skipped', 'reused_rows', 'reused_stores', 'sources_total'), 10**15)}
                             for d in DOMAINS}}
        summary = runner.ingest_summary(report)
        # Conservatively fill every nullable/count slot, even combinations that
        # cannot coexist, to protect the existing bounded JSON transport.
        for row in [summary['pending_work']['totals'], *summary['pending_work']['domains'].values()]:
            for key in row:
                row[key] = 10**15
        receipt = {'schema': 'offmenu-run-receipt/2', 'job_id': 'retained-eight-domain-ingest',
            'job_version': 1000000, 'operation': 'retained_ingest_all', 'job_key': 'a'*64,
            'implementation_sha256': 'b'*64, 'input_sha256': 'c'*64,
            'observed_at': '2026-10-22T00:00:00Z', 'outcome': 'completed', 'ingest': summary}
        self.assertLessEqual(len(plan_runner.canonical({'sha256': 'd'*64, 'receipt': receipt})), 65536)

    def test_receipt_extension_is_strict_and_old_receipts_keep_their_digest(self):
        runner = object.__new__(plan_runner.Runner)
        summary = runner.ingest_summary({'domains': {}})
        receipt = {'schema': 'offmenu-run-receipt/2', 'job_id': 'retained-eight-domain-ingest',
            'job_version': 1, 'operation': 'retained_ingest_all', 'job_key': 'a'*64,
            'implementation_sha256': 'b'*64, 'input_sha256': 'c'*64,
            'observed_at': '2026-10-22T00:00:00Z', 'outcome': 'running', 'ingest': summary}
        before = plan_runner.canonical(receipt)
        plan_runner.validate_ingest_receipt(receipt)
        self.assertEqual(plan_runner.canonical(receipt), before)
        row = summary['domains']['recipes']
        row['error_telemetry'] = sanitize_error_telemetry({'status': 'available', 'class_counts': {'MalformedRecord': 1}})
        summary['progress_sha256'] = plan_runner.ingest_progress_digest(summary)
        plan_runner.validate_ingest_receipt(receipt)
        for mutate in (
                lambda t: t.update(source_key='SECRET'),
                lambda t: t['class_counts'].update(SECRET=1),
                lambda t: t['reason_counts'].update(SECRET=1),
                lambda t: t['origin_counts'].update(adapter_callback=False),
                lambda t: t.update(durable_scope='SECRET')):
            bad = copy.deepcopy(receipt)
            mutate(bad['ingest']['domains']['recipes']['error_telemetry'])
            bad['ingest']['progress_sha256'] = plan_runner.ingest_progress_digest(bad['ingest'])
            with self.assertRaises(plan_runner.Stop):
                plan_runner.validate_ingest_receipt(bad)


if __name__ == '__main__':
    unittest.main()
