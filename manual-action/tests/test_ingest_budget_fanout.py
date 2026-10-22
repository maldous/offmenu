"""Coordinator global-stop regressions: generated sources and temporary stores only."""
import importlib
import json
from pathlib import Path
import sqlite3
import sys
import tempfile
import threading
import time
from types import SimpleNamespace
import unittest
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import ingest_engine as engine
import ingest_store
from ingest_api import BudgetExceeded, source_key
from ingest_pending import collect_pending_work, store_path
from ingest_store import DomainStore


class BudgetFanoutTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.free = 1000
        self.disk = mock.patch.object(engine.shutil, 'disk_usage',
            side_effect=lambda path: SimpleNamespace(free=self.free))
        self.disk.start()
        self.addCleanup(self.disk.stop)

    def fixture(self, domain, count=1000):
        module = importlib.import_module(engine.ADAPTERS[domain])
        path = self.root / (domain + '.jsonl')
        rows = [{'id': str(i), 'kind': 'NutrientProfile', 'name': 'Generated',
                 'url': 'https://example.invalid/' + str(i), 'sourceId': 'generated-' + str(i)} for i in range(5)]
        path.write_text(''.join(json.dumps(row) + '\n' for row in rows))
        sources = [{'id': domain + '-' + str(i), 'path': str(path), 'format': 'jsonl',
                    'domains': [domain], 'adapter_version': getattr(module, 'ADAPTER_VERSION', 1),
                    'disposition': 'candidate'} for i in range(count)]
        config = {'state_dir': str(self.root / domain), 'batch_size': 2,
                  'reserve_bytes': 100, 'terminal_progress': False}
        return sources, config

    def run_domain(self, domain, sources, config, progress=lambda *args: None, adapters=None):
        return engine._run_domain(domain, sources, config, threading.Event(), progress,
                                  time.monotonic(), adapters)

    def test_real_affected_adapters_keep_partial_prefix_without_failing_unread_tail(self):
        for domain in ('barcodes', 'citations', 'dietary'):
            with self.subTest(domain=domain):
                self.free = 1000
                sources, config = self.fixture(domain)
                events = []
                def progress(name, event):
                    events.append(event)
                    if event.get('event') == 'batch':
                        self.free = 99
                result = self.run_domain(domain, sources, config, progress)
                self.assertEqual((result['status'], result['written'], result['errors']), ('partial', 2, 0))
                self.assertEqual((result['sources_complete'], result['sources_partial']), (0, 1))
                self.assertEqual(len(result['sources']), 1)
                self.assertEqual(result['budget_stop']['reason'], 'disk_reserve')
                self.assertFalse(any(event.get('event') == 'adapter_error' for event in events))
                with sqlite3.connect(store_path(config['state_dir'], domain)) as db:
                    row = db.execute('SELECT cursor,written,errors,status,version FROM sources').fetchone()
                    self.assertEqual(row[:4], (2, 2, 0, 'partial'))
                    self.assertEqual(db.execute('SELECT count(*) FROM sources').fetchone()[0], 1)
                    self.assertEqual(db.execute('SELECT count(*) FROM source_errors').fetchone()[0], 0)
                pending = collect_pending_work(sources, config['state_dir'], results={domain: result},
                    adapter_versions={domain: sources[0]['adapter_version']})['summary']['domains'][domain]
                self.assertEqual((pending['partial'], pending['failed'], pending['not_yet_read']), (1, 0, 999))
                self.free = 1000
                resumed = self.run_domain(domain, sources[:1], config)
                self.assertEqual((resumed['written'], resumed['errors']), (3, 0))
                self.assertEqual(resumed['sources'][0]['resumed_from'], 2)
                self.assertEqual(resumed['sources'][0]['source_version'], row[4])

    def test_completed_prefix_and_untouched_historical_failure_are_preserved(self):
        sources, config = self.fixture('barcodes', 3)
        history = sources[2]
        with DomainStore('barcodes', config['state_dir'], config) as store:
            store.ingest(history, [{'id': 'historical', 'name': 'Generated'}])
            store.record_error(history, ValueError('Generated historical error'))
            before_source = store.db.execute('SELECT * FROM sources WHERE source_key=?', (source_key(history),)).fetchall()
            before_errors = store.db.execute('SELECT * FROM source_errors').fetchall()
        def progress(domain, event):
            if event.get('event') == 'source_timed':
                self.free = 99
        result = self.run_domain('barcodes', sources, config, progress)
        self.assertEqual((result['sources_complete'], result['sources_partial'], result['errors']), (1, 0, 0))
        self.assertEqual(len(result['sources']), 1)
        self.assertEqual(result['stored_records'], 6)
        with sqlite3.connect(store_path(config['state_dir'], 'barcodes')) as db:
            self.assertEqual(db.execute('SELECT * FROM sources WHERE source_key=?', (source_key(history),)).fetchall(), before_source)
            self.assertEqual(db.execute('SELECT * FROM source_errors').fetchall(), before_errors)
            self.assertIsNone(db.execute('SELECT 1 FROM sources WHERE source_key=?', (source_key(sources[1]),)).fetchone())

    def test_global_stop_precedes_missing_descriptor_bookkeeping_and_dispatch(self):
        sources, config = self.fixture('barcodes', 1000)
        sources = [{**source, 'acquired_source': True, 'acquired_adapter': 'foodista_common_pile',
                    'disposition': 'missing'} for source in sources]
        def progress(domain, event):
            if event.get('event') == 'store_opened':
                self.free = 99
        with mock.patch.object(engine.IngestContext, 'report_error') as errors, \
             mock.patch.object(engine.importlib, 'import_module') as dispatch:
            result = self.run_domain('barcodes', sources, config, progress)
        errors.assert_not_called()
        dispatch.assert_not_called()
        self.assertEqual((result['status'], result['errors'], result['sources']), ('partial', 0, []))

    def test_budget_stop_ends_later_groups_but_nonbudget_failures_remain_isolated(self):
        sources, config = self.fixture('recipes', 1)
        acquired = {**sources[0], 'id': 'acquired', 'acquired_source': True,
                    'acquired_adapter': 'foodista_common_pile'}
        def stop(domain, selected, context):
            context.ingest(selected[0], [{'id': 'accepted', 'name': 'Generated'}])
            self.free = 99
            context.check_budget()
        import ingest_acquired_recipes
        import ingest_recipes
        with mock.patch.object(ingest_acquired_recipes, 'run_domain', side_effect=stop), \
             mock.patch.object(ingest_recipes, 'run_domain') as retained:
            result = self.run_domain('recipes', [acquired, *sources], config)
        retained.assert_not_called()
        self.assertEqual((result['written'], result['errors'], len(result['sources'])), (1, 0, 1))
        self.free = 1000
        with mock.patch.object(ingest_acquired_recipes, 'run_domain', side_effect=ValueError('Generated format failure')), \
             mock.patch.object(ingest_recipes, 'run_domain', return_value={'sources': []}) as retained:
            result = self.run_domain('recipes', [acquired, *sources], config)
        retained.assert_called_once()
        self.assertEqual(result['errors'], 1)
        self.assertNotIn('budget_stop', result)

    def test_custom_handler_boundary_prevents_next_source_fingerprint_after_global_stop(self):
        sources, config = self.fixture('barcodes', 1000)
        def handler(domain, selected, context):
            results = []
            for source in selected:
                results.append(context.ingest(source, [{'id': 'generated'}]))
                self.free = 99  # Deliberately no handler-owned check at next iteration.
            return {'sources': results}
        with mock.patch.object(ingest_store, '_fingerprint', wraps=ingest_store._fingerprint) as fingerprints:
            result = self.run_domain('barcodes', sources, config, adapters={'barcodes': handler})
        self.assertEqual((result['status'], result['sources_complete'], result['errors']), ('partial', 1, 0))
        self.assertTrue(all(call.args[0]['id'] == sources[0]['id'] for call in fingerprints.call_args_list))
        self.assertEqual(len(result['sources']), 1)

    def test_real_row_caps_continue_next_sources_without_global_stop(self):
        for domain in ('barcodes', 'citations', 'dietary'):
            with self.subTest(domain=domain):
                sources, config = self.fixture(domain, 3)
                result = self.run_domain(domain, sources, {**config, 'max_rows_per_source': 2})
                self.assertEqual((result['written'], result['errors'], len(result['sources'])), (6, 0, 3))
                self.assertNotIn('budget_stop', result)
                self.assertTrue(all(source['reason'] == 'resource_cap' for source in result['sources']))

    def test_time_and_cancellation_stop_at_coordinator_group_boundary(self):
        for reason in ('wall_time_cap', 'cancelled'):
            sources, config = self.fixture('barcodes', 1000)
            config['state_dir'] += '-' + reason
            cancelled = threading.Event()
            def handler(domain, selected, context):
                context.ingest(selected[0], [{'id': 'accepted'}])
                if reason == 'wall_time_cap':
                    context.config['max_seconds'] = .001
                    context.started = time.monotonic() - 1
                else:
                    cancelled.set()
                context.check_budget()
            import ingest_existing
            with mock.patch.object(ingest_existing, 'run_domain', side_effect=handler):
                result = engine._run_domain('barcodes', sources, config, cancelled, lambda *args: None, time.monotonic())
            self.assertEqual((result['errors'], len(result['sources'])), (0, 1))
            self.assertEqual(result['budget_stop']['reason'], reason)


if __name__ == '__main__':
    unittest.main()
