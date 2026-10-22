"""Generated-only committed totals and active-domain diagnostics regressions."""
import json
from pathlib import Path
import sqlite3
import sys
import tempfile
import threading
import time
import unittest
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from ingest_api import DOMAINS
from ingest_engine import run_ingest, sanitize_report
from ingest_evidence import (ADAPTER_COUNT_COLUMNS, EvidenceCollector,
                             summarize_diagnostics, validate_evidence)
from ingest_store import DomainStore


class StoredTotalsTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.state = self.root / 'state'
        self.state.mkdir()
        self.path = self.root / 'generated.jsonl'
        self.path.write_text('{}\n')
        self.source = {'id': 'generated', 'path': str(self.path),
                       'domain': 'recipes', 'format': 'jsonl'}
        self.config = {'state_dir': str(self.state), 'reserve_bytes': 0,
                       'batch_size': 2, 'terminal_progress': False,
                       'report_interval': 1, 'workers': 8}

    def test_writer_counts_existing_rows_updates_replay_versions_without_scans(self):
        events = []
        with DomainStore('recipes', self.state, self.config) as store:
            store.ingest(self.source, [{'id': 'prior'}])
        statements = []
        with DomainStore('recipes', self.state, self.config,
                         progress=lambda **event: events.append(event)) as store:
            store.db.set_trace_callback(statements.append)
            self.assertEqual(store.stored_totals(), {'stored_records_before': 1, 'stored_records': 1})
            new = {**self.source, 'id': 'new-source'}
            result = store.ingest(new, [{'id': 'new', 'n': 1}, {'id': 'new', 'n': 2},
                {'id': 'new', 'n': 2}, {'id': 'bad', 'relations': 'invalid'}, {'id': 'another'}])
            self.assertEqual((result['written'], result['unchanged'], result['errors']), (3, 1, 1))
            self.assertEqual(store.stored_records, 3)
            reused = store.ingest(self.source, iter([{'id': 'never-read'}]))
            self.assertEqual(reused['unchanged'], 1)
            self.assertEqual(store.stored_records, 3)
            versioned = {**new, 'adapter_version': 2}
            store.ingest(versioned, [{'id': 'new'}])
            self.assertEqual(store.stored_records, 4)
            self.assertFalse(any('COUNT(' in query.upper() for query in statements))
            self.assertEqual(store.db.execute('SELECT COUNT(*) FROM records').fetchone()[0], 4)
            self.assertEqual(int(store.db.execute("SELECT value FROM ingest_meta WHERE key='record_count'").fetchone()[0]), 4)
        self.assertEqual(events[0]['event'], 'store_opened')
        self.assertEqual([e['stored_records'] for e in events if e['event'] == 'batch'], [2, 2, 3, 4])
        self.assertTrue(all(e['stored_records_before'] == 1 for e in events if 'stored_records' in e))

    def test_failed_commit_does_not_publish_or_advance_count(self):
        class FailCommit:
            def __init__(self, db): self.db = db
            def __getattr__(self, name): return getattr(self.db, name)
            def execute(self, sql, *args):
                if sql == 'COMMIT': raise sqlite3.OperationalError('generated commit failure')
                return self.db.execute(sql, *args)
        events = []
        with DomainStore('recipes', self.state, self.config,
                         progress=lambda **event: events.append(event)) as store:
            store.db = FailCommit(store.db)
            result = store.ingest(self.source, [{'id': 'not-committed'}])
            self.assertEqual(result['status'], 'failed')
            self.assertEqual(store.stored_records, 0)
            self.assertEqual(store.db.execute('SELECT COUNT(*) FROM records').fetchone()[0], 0)
            self.assertFalse(any(e['event'] == 'batch' for e in events))

    def test_live_checkpoint_is_committed_overall_not_writes_or_external_reuse(self):
        with DomainStore('recipes', self.state, self.config) as store:
            store.ingest(self.source, [{'id': 'prior'}])
        gate = threading.Event()
        saw = []
        caller = threading.get_ident()
        new = {**self.source, 'id': 'new'}
        def adapter(domain, sources, context):
            reused = context.ingest(sources[0], iter([{'id': 'never-read'}]))
            def rows():
                yield {'id': 'new', 'n': 1}
                yield {'id': 'new', 'n': 2}
                if not gate.wait(8): raise AssertionError('checkpoint did not arrive')
                yield {'id': 'new', 'n': 2}
                yield {'id': 'bad', 'relations': 'invalid'}
                yield {'id': 'another'}
            result = context.ingest(sources[1], rows())
            return {'sources': [reused, result], 'reused_rows': 700, 'reused_stores': 1}
        def callback(report):
            self.assertEqual(threading.get_ident(), caller)
            row = report['domains']['recipes']
            if row['status'] == 'running' and row['stored_records'] == 2:
                evidence = report['ingest_evidence']
                validate_evidence(evidence)
                i = evidence['metric_columns'].index('stored_records')
                counts = evidence['observations']['recipes']
                self.assertEqual((counts['before'][i], counts['current'][i], counts['delta'][i]), (1, 2, 1))
                self.assertEqual(row['written'], 2)  # one insert plus one update
                with sqlite3.connect(self.state / 'staging' / 'recipes.sqlite3') as db:
                    self.assertEqual(db.execute('SELECT COUNT(*) FROM records').fetchone()[0], 2)
                saw.append(report)
                gate.set()
        report = run_ingest([self.source, new], self.config, callback, {'recipes': adapter})
        self.assertTrue(saw)
        row = report['domains']['recipes']
        self.assertEqual((row['stored_records_before'], row['stored_records']), (1, 3))
        self.assertEqual((row['written'], row['unchanged'], row['reused_rows']), (3, 2, 700))
        self.assertEqual(report['stored_totals']['stored_records'], 3)
        self.assertEqual(report['stored_totals']['stored_records_before'], 1)
        self.assertEqual(report['stored_totals']['domains_known'], 8)
        self.assertNotIn(str(self.path), json.dumps(report))
        self.assertNotIn('never-read', json.dumps(report))

    def test_unopened_or_failed_writer_is_unknown_not_zero(self):
        initial = sanitize_report({'domains': {}})
        self.assertIsNone(initial['stored_totals']['stored_records'])
        self.assertEqual(initial['stored_totals']['domains_known'], 0)
        with DomainStore('recipes', self.state, self.config):
            report = run_ingest([], self.config)
        self.assertEqual(report['domains']['recipes']['status'], 'failed')
        self.assertIsNone(report['domains']['recipes']['stored_records'])
        self.assertIsNone(report['stored_totals']['stored_records'])
        self.assertEqual(report['stored_totals']['domains_known'], 7)
        bad = sanitize_report({'domains': {'recipes': {'stored_records': True,
                                                     'stored_records_before': -1}}})
        self.assertIsNone(bad['domains']['recipes']['stored_records'])

    def test_completed_parser_group_visible_before_retained_tail_without_double_count(self):
        gate = threading.Event()
        checkpoints = []
        acquired = {**self.source, 'id': 'acquired', 'acquired_source': True,
                    'acquired_adapter': 'foodista_common_pile'}
        row = {'source_key': 'private-generated-key', 'status': 'complete',
               'record_kinds': {'projected_recipes': 2},
               'diagnostics': {'reason_counts': {'private unknown reason': 1},
                               'raw_payload': 'PRIVATE-ROW-MUST-NOT-LEAK'}}
        def acquired_handler(*args): return {'sources': [row]}
        def retained_handler(*args):
            if not gate.wait(8): raise AssertionError('checkpoint did not arrive')
            return {'sources': [{'source_key': 'retained', 'status': 'complete'}]}
        def callback(report):
            evidence = report['ingest_evidence']
            parser = evidence['adapter_diagnostics']['domains']['recipes']['parser_counts']
            if report['domains']['recipes']['status'] == 'running' and parser[ADAPTER_COUNT_COLUMNS.index('projected_recipes')] == 2:
                validate_evidence(evidence)
                checkpoints.append(report)
                gate.set()
        with mock.patch('ingest_acquired_recipes.run_domain', side_effect=acquired_handler), \
             mock.patch('ingest_recipes.run_domain', side_effect=retained_handler):
            final = run_ingest([self.source, acquired], self.config, callback)
        self.assertTrue(checkpoints)
        diagnostic = final['ingest_evidence']['adapter_diagnostics']
        self.assertEqual(diagnostic['domains']['recipes']['parser_counts'][ADAPTER_COUNT_COLUMNS.index('projected_recipes')], 2)
        self.assertEqual(diagnostic['source_summaries_total'], 2)
        text = json.dumps([*checkpoints, final])
        self.assertNotIn('PRIVATE-ROW-MUST-NOT-LEAK', text)
        self.assertNotIn('private-generated-key', text)
        self.assertNotIn('private unknown reason', text)

    def test_parser_group_snapshot_is_bounded_and_replaced_not_added(self):
        rows = [{'record_kinds': {'projected_recipes': 1}} for _ in range(5)]
        snapshot = summarize_diagnostics({'recipes': {'sources': rows}}, 2, time.monotonic() + 1)
        self.assertEqual((snapshot['source_summaries_total'], snapshot['source_summaries_inspected'], snapshot['remaining']), (5, 2, 3))
        collector = EvidenceCollector([], self.config)
        report = sanitize_report({'domains': {}})
        live = collector.capture('checkpoint', report,
            results={'recipes': {'completed_group_diagnostics': (snapshot,)}})
        self.assertIn('checkpoint_sample_incomplete', live['quality_codes'])
        self.assertEqual(live['adapter_diagnostics']['source_summaries_inspected'], 2)
        terminal = collector.capture('post', report, results={'recipes': {'sources': rows}})
        self.assertEqual(terminal['adapter_diagnostics']['source_summaries_total'], 5)
        self.assertEqual(terminal['adapter_diagnostics']['domains']['recipes']['parser_counts'][ADAPTER_COUNT_COLUMNS.index('projected_recipes')], 5)
        validate_evidence(terminal)


if __name__ == '__main__':
    unittest.main()
