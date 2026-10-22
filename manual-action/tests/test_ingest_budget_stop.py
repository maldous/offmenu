"""Generated-only global budget stops; no retained input, network, or live state."""
import copy
import json
from pathlib import Path
import sys
import tempfile
import threading
import time
from types import SimpleNamespace
import unittest
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from ingest_api import (BudgetExceeded, DOMAINS, GLOBAL_BUDGET_DEFAULTS,
                        sanitize_budget_stop)
from ingest_engine import IngestContext, _run_domain, run_ingest, sanitize_report
from ingest_evidence import EvidenceCollector, sanitize_evidence, validate_evidence
from ingest_pending import collect_pending_work
from ingest_store import DomainStore
import ingest_suppliers as suppliers


class BudgetStopTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.path = self.root / 'generated.jsonl'
        self.path.write_text(''.join(json.dumps({'id': str(i), 'name': 'Generated'}) + '\n'
                                     for i in range(5)))
        self.source = {'id': 'first', 'path': str(self.path), 'format': 'jsonl',
                       'domain': 'suppliers', 'disposition': 'candidate'}
        self.config = {'state_dir': str(self.root / 'state'), 'batch_size': 2,
                       'reserve_bytes': 100, 'terminal_progress': False}
        self.free = 1000
        self.disk = mock.patch('ingest_engine.shutil.disk_usage',
                               side_effect=lambda path: SimpleNamespace(free=self.free))
        self.disk.start()
        self.addCleanup(self.disk.stop)

    def context(self, state=None, **options):
        config = {**self.config, **options}
        if state:
            config['state_dir'] = str(state)
        return IngestContext('suppliers', config['state_dir'], config,
                             threading.Event(), lambda *args: None, time.monotonic())

    def sources(self, count=2000):
        return [{**self.source, 'id': 'generated-' + str(i)} for i in range(count)]

    def stop(self, context, reason):
        if reason == 'disk_reserve':
            self.free = 99
        elif reason == 'wall_time_cap':
            context.config['max_seconds'] = .5
            context.started = time.monotonic() - 1
        else:
            context.cancelled.set()

    def pending(self, sources, context, result):
        return collect_pending_work(sources, context.state_dir,
            results={'suppliers': result}, adapter_versions={'suppliers': suppliers.ADAPTER_VERSION})

    def test_preexhausted_disk_time_cancel_leave_entire_large_tail_unread(self):
        for reason in ('disk_reserve', 'wall_time_cap', 'cancelled'):
            with self.subTest(reason=reason):
                self.free = 1000
                context = self.context(self.root / reason)
                sources = self.sources()
                with DomainStore('suppliers', context.state_dir, context.config,
                                 context.check_budget, context.progress) as store:
                    context.store = store
                    self.stop(context, reason)
                    with mock.patch.object(suppliers, '_rows', side_effect=AssertionError('must not open')):
                        result = suppliers.run_domain('suppliers', sources, context)
                    self.assertEqual(result['status'], 'partial')
                    self.assertEqual(result['sources'], [])
                    self.assertEqual(result['errors'], 0)
                    self.assertEqual(store.db.execute('SELECT count(*) FROM sources').fetchone()[0], 0)
                    self.assertEqual(context.budget_stop['reason'], reason)
                    self.assertEqual(context.budget_stop['disk_free_bytes'], self.free)
                    pending = self.pending(sources, context, result)
                    self.assertEqual(pending['summary']['domains']['suppliers']['not_yet_read'], 2000)
                    self.assertEqual(context.adapter_errors, 0)

    def test_midbatch_global_stops_keep_committed_prefix_then_resume_exact_version(self):
        for reason in ('disk_reserve', 'wall_time_cap', 'cancelled'):
            with self.subTest(reason=reason):
                self.free = 1000
                context = self.context(self.root / reason)
                sources = self.sources()
                emitted = []

                def rows(source, maximum, error, check):
                    for i in range(5):
                        if i == 3:  # two committed, one buffered, then stop
                            self.stop(context, reason)
                        check()
                        emitted.append(i)
                        yield {'id': str(i), 'name': 'Generated'}, '$/' + str(i)

                with DomainStore('suppliers', context.state_dir, context.config,
                                 context.check_budget, context.progress) as store:
                    context.store = store
                    with mock.patch.object(suppliers, '_rows', side_effect=rows) as reader:
                        result = suppliers.run_domain('suppliers', sources, context)
                    self.assertEqual(reader.call_count, 1)
                    self.assertEqual(emitted, [0, 1, 2])
                    self.assertEqual((result['read'], result['written'], result['errors']), (2, 2, 0))
                    self.assertEqual(len(result['sources']), 1)
                    self.assertEqual(result['sources'][0]['reason'], 'resource_cap')
                    cursor, written, errors, version = store.db.execute(
                        'SELECT cursor,written,errors,version FROM sources').fetchone()
                    self.assertEqual((cursor, written, errors), (2, 2, 0))
                    self.assertEqual(store.db.execute('SELECT count(*) FROM sources').fetchone()[0], 1)
                    self.assertEqual(store.db.execute('SELECT count(*) FROM source_errors').fetchone()[0], 0)
                    pending = self.pending(sources, context, result)['summary']['domains']['suppliers']
                    self.assertEqual((pending['partial'], pending['not_yet_read']), (1, 1999))
                self.free = 1000
                resumed = self.context(context.state_dir)
                with DomainStore('suppliers', resumed.state_dir, resumed.config,
                                 resumed.check_budget, resumed.progress) as store:
                    resumed.store = store
                    result = suppliers.run_domain('suppliers', sources[:1], resumed)
                    self.assertEqual((result['written'], result['sources'][0]['resumed_from']), (3, 2))
                    self.assertEqual(result['sources'][0]['source_version'], version)
                    self.assertEqual(store.db.execute('SELECT count(*) FROM records').fetchone()[0], 5)
                    self.assertEqual(store.db.execute('SELECT count(*) FROM sources').fetchone()[0], 1)
                    self.assertIsNone(resumed.budget_stop)

    def test_source_local_cap_continues_later_sources_without_global_stop(self):
        context = self.context(max_rows_per_source=2)
        sources = self.sources(3)
        with DomainStore('suppliers', context.state_dir, context.config,
                         context.check_budget, context.progress) as store:
            context.store = store
            result = suppliers.run_domain('suppliers', sources, context)
            self.assertEqual((result['written'], result['errors']), (6, 0))
            self.assertEqual(len(result['sources']), 3)
            self.assertTrue(all(s['reason'] == 'resource_cap' for s in result['sources']))
            self.assertEqual(store.db.execute('SELECT count(*) FROM sources').fetchone()[0], 3)
            self.assertIsNone(context.budget_stop)

    def test_unrelated_source_error_still_reads_later_source_and_reuses_completed_errors(self):
        broken = self.root / 'broken.jsonl'
        broken.write_text('not-json\n{"id":"good","name":"Generated"}\n')
        context = self.context()
        sources = [{**self.source, 'id': 'broken', 'path': str(broken)}, self.source]
        with DomainStore('suppliers', context.state_dir, context.config,
                         context.check_budget, context.progress) as store:
            context.store = store
            first = suppliers.run_domain('suppliers', sources, context)
            self.assertEqual((first['written'], first['errors']), (6, 1))
            self.assertEqual([s['status'] for s in first['sources']], ['partial', 'complete'])
            repeat = suppliers.run_domain('suppliers', sources, context)
            self.assertEqual((repeat['written'], repeat['unchanged'], repeat['errors']), (0, 6, 1))
            self.assertTrue(repeat['sources'][0]['completed'])
            self.assertIsNone(context.budget_stop)

    def test_first_stop_is_latched_even_if_disk_recovers(self):
        context = self.context()
        self.stop(context, 'disk_reserve')
        with self.assertRaises(BudgetExceeded):
            context.check_budget()
        observation = copy.deepcopy(context.budget_stop)
        self.free = 1000
        with self.assertRaisesRegex(BudgetExceeded, '^disk_reserve$'):
            context.check_budget()
        self.assertEqual(context.budget_stop, observation)

    def test_time_and_cancel_observations_survive_unavailable_disk_stat(self):
        for reason in ('wall_time_cap', 'cancelled'):
            context = self.context()
            self.stop(context, reason)
            with mock.patch('ingest_engine.shutil.disk_usage', side_effect=OSError('PRIVATE')):
                with self.assertRaisesRegex(BudgetExceeded, '^' + reason + '$'):
                    context.check_budget()
            self.assertIsNone(context.budget_stop['disk_free_bytes'])
            self.assertEqual(context.adapter_errors, 0)

    def test_engine_report_and_evidence_keep_stop_separate_from_row_errors(self):
        self.free = 99
        result = run_ingest(self.sources(20), self.config)
        domain = result['domains']['suppliers']
        self.assertEqual(domain['status'], 'partial')
        self.assertEqual((domain['errors'], domain['sources_partial']), (0, 0))
        self.assertEqual(result['pending_work']['domains']['suppliers']['not_yet_read'], 20)
        self.assertEqual(domain['budget_stop']['reason'], 'disk_reserve')
        self.assertEqual(domain['budget_stop']['reserve_bytes'], 100)
        self.assertEqual(domain['error_telemetry']['reason_counts'], {})
        public = result['ingest_evidence']
        self.assertEqual(public['budget_stops']['domains']['suppliers'], domain['budget_stop'])
        self.assertIn('review_resource_limit', public['next_actions'])
        self.assertNotIn('review_source_errors', public['next_actions'])
        self.assertEqual(public['resources']['max_seconds'], 0)
        validate_evidence(public)
        self.assertEqual(sanitize_report(result), result)
        from plan_runner import build_supplement, reference_for_supplement, validate_supplement
        supplement = build_supplement(result)
        self.assertEqual(supplement['ingest_evidence']['budget_stops'], public['budget_stops'])
        self.assertEqual(validate_supplement(supplement), supplement)
        self.assertLessEqual(reference_for_supplement(supplement)['bytes'], 65536)

    def test_domain_boundary_budget_exception_does_not_invent_row_error(self):
        self.free = 99

        def adapter(domain, sources, context):
            context.check_budget()

        result = _run_domain('suppliers', self.sources(2), self.config,
            threading.Event(), lambda *args: None, time.monotonic(), {'suppliers': adapter})
        self.assertEqual((result['status'], result['errors']), ('partial', 0))
        self.assertEqual(result['budget_stop']['reason'], 'disk_reserve')
        self.assertEqual(result['sources'], [])

    def test_effective_defaults_fractional_caps_and_legacy_evidence_remain_valid(self):
        collector = EvidenceCollector([], {'state_dir': str(self.root)})
        defaults = collector.capture('pre', {})
        for key, value in GLOBAL_BUDGET_DEFAULTS.items():
            self.assertEqual(defaults['resources'][key], value)
        legacy = copy.deepcopy(defaults)
        legacy.pop('budget_stops')
        self.assertEqual(validate_evidence(legacy), legacy)
        collector.config['max_seconds'] = .125
        fractional = collector.capture('post', {})
        self.assertEqual(fractional['resources']['max_seconds'], .125)
        validate_evidence(fractional)
        context = self.context(reserve_bytes=100)
        context.config.pop('reserve_bytes')
        with self.assertRaises(BudgetExceeded):
            context.check_budget()
        self.assertEqual(context.budget_stop['reserve_bytes'], 2 * 1024**3)

    def test_stop_sanitization_rejects_arbitrary_text_and_invalid_numbers(self):
        secret = 'PRIVATE-PATH-OR-ROW'
        for reason in (secret, [], {}, 1, None):
            self.assertIsNone(sanitize_budget_stop({'reason': reason}))
        raw = {'reason': 'disk_reserve', 'elapsed_ms': True, 'disk_free_bytes': -1,
               'reserve_bytes': 10**16, 'max_seconds': float('nan'),
               'max_rows_per_source': secret, 'path': secret, 'row': secret}
        clean = sanitize_budget_stop(raw)
        self.assertEqual(clean, {'reason': 'disk_reserve', 'elapsed_ms': None,
            'disk_free_bytes': None, 'reserve_bytes': None, 'max_seconds': None,
            'max_rows_per_source': None})
        evidence = sanitize_evidence({'budget_stops': {'domains': {'suppliers': raw,
            secret: raw}, 'path': secret}})
        self.assertNotIn(secret, json.dumps(evidence))
        self.assertEqual(set(evidence['budget_stops']['domains']), set(DOMAINS))
        validate_evidence(evidence)


if __name__ == '__main__':
    unittest.main()
