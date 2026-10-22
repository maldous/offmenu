"""Generated local fixtures only: private app domains are not external inputs."""
import copy
from contextlib import redirect_stdout
import io
import json
from pathlib import Path
import sqlite3
import sys
import tempfile
import unittest
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from ingest_api import APP_MANAGED_DOMAINS, DOMAINS
import ingest_engine as engine
import ingest_evidence as evidence
import ingest_pending as pending
from ingest_store import DomainStore
import plan_runner as runner


class AppManagedScopeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.state = self.root / 'state'
        self.state.mkdir()
        self.config = {'state_dir': str(self.state), 'reserve_bytes': 0,
            'terminal_progress': False, 'batch_size': 1, 'workers': 2,
            'evidence_max_items': 1000, 'evidence_max_seconds': .25,
            'materialize_relational_targets': False, 'catalog_sha256': 'a' * 64}

    def tearDown(self):
        self.temp.cleanup()

    def private_sources(self):
        return [{'id': 'historical-' + str(i), 'path': '/never-read/generated-' + str(i),
                 'domains': [APP_MANAGED_DOMAINS[i % 2]], 'format': 'jsonl',
                 'disposition': 'missing', 'reason': 'source_missing',
                 'metadata': {'user_supplied': True, 'household_scope': True}}
                for i in range(91)]

    def external_source(self):
        path = self.root / 'external.jsonl'
        path.write_text('{"id":"generated"}\n')
        return {'id': 'external', 'path': str(path), 'domain': 'recipes', 'format': 'jsonl'}

    def test_91_assignments_retained_without_missing_inputs_or_source_access(self):
        sources = self.private_sources()
        before = copy.deepcopy(sources)
        read_store = pending._read_store
        def public_only(path, domain, selected):
            self.assertNotIn(domain, APP_MANAGED_DOMAINS)
            return read_store(path, domain, selected)
        with mock.patch.object(pending, '_fingerprint', side_effect=AssertionError('private source read')), \
             mock.patch.object(pending, '_read_store', side_effect=public_only):
            snapshot = pending.collect_pending_work(sources, self.state)
        self.assertEqual(sources, before)
        self.assertEqual(len(snapshot['sources']), 91)
        self.assertTrue(all(row['excluded_from_pending'] and row['scope'] == 'app_managed' for row in snapshot['sources']))
        self.assertEqual({r['source_key'] for r in snapshot['sources']}, {pending.source_key(s) for s in sources})
        summary = snapshot['summary']
        self.assertEqual(summary['catalog_sources'], 91)
        self.assertEqual(summary['unassigned_sources'], 0)
        self.assertEqual(summary['scope']['app_managed_assignments'], {'user_profiles': 46, 'inventory': 45})
        self.assertEqual(summary['awaiting_input_domains'], [])
        self.assertEqual(summary['totals']['assignments_total'], 0)
        self.assertEqual(summary['totals']['awaiting_input'], 0)
        self.assertEqual(summary['totals']['records_remaining_unknown'], 0)
        self.assertEqual(summary['totals']['records_remaining'], 0)
        self.assertEqual(summary['totals']['records_to_write'], 0)
        runner.validate_pending_work(summary)
        self.assertNotIn('/never-read', json.dumps(summary))

    def test_direct_private_adapter_never_reads_even_legacy_scoped_sources(self):
        import ingest_existing
        context = mock.Mock()
        with mock.patch.object(ingest_existing, 'records', side_effect=AssertionError('source opened')), \
             mock.patch.object(ingest_existing, 'inspect_existing', side_effect=AssertionError('source opened')):
            for domain in APP_MANAGED_DOMAINS:
                result = ingest_existing.run_domain(domain, self.private_sources(), context)
                self.assertEqual(result['status'], 'schema_only')
                self.assertEqual(result['scope'], 'app_managed')
                self.assertIsNone(result['reason'])
                self.assertEqual(result['written'], 0)
                self.assertEqual(result['errors'], 0)
        self.assertEqual(context.mock_calls, [])

    def test_mixed_assignment_retains_external_side_and_catalog_identity(self):
        shared = self.external_source()
        shared.pop('domain')
        shared['domains'] = ['recipes', 'inventory']
        snapshot = pending.collect_pending_work([shared], self.state)
        self.assertEqual(snapshot['summary']['domains']['recipes']['not_yet_read'], 1)
        self.assertEqual(snapshot['summary']['scope']['app_managed_assignments']['inventory'], 1)
        self.assertEqual(snapshot['summary']['totals']['assignments_total'], 1)
        self.assertEqual(snapshot['summary']['catalog_sources'], 1)
        self.assertEqual(len(snapshot['sources']), 2)

    def test_engine_keeps_existing_private_rows_and_reports_real_totals_including_zero(self):
        seed = self.external_source()
        with DomainStore('user_profiles', self.state, self.config) as store:
            store.ingest(seed, [{'id': 'existing-a'}, {'id': 'existing-b'}])
            records_before = store.db.execute('SELECT * FROM records ORDER BY record_id').fetchall()
            sources_before = store.db.execute('SELECT * FROM sources').fetchall()
        called = []
        def adapter(domain, sources, context):
            self.assertNotIn(domain, APP_MANAGED_DOMAINS)
            called.append(domain)
            return {'status': 'complete', 'sources': [context.ingest(s, [{'id': 'external-output'}]) for s in sources]}
        report = engine.run_ingest([*self.private_sources(), seed], self.config,
            adapters={d: adapter for d in DOMAINS})
        self.assertEqual(called, ['recipes'])
        self.assertEqual(set(report['domains']), set(DOMAINS))
        for domain, count in (('user_profiles', 2), ('inventory', 0)):
            self.assertEqual(report['domains'][domain]['status'], 'schema_only')
            self.assertEqual(report['domains'][domain]['scope'], 'app_managed')
            self.assertEqual(report['domains'][domain]['stored_records'], count)
            self.assertEqual(report['domains'][domain]['stored_records_before'], count)
            self.assertEqual(report['domains'][domain]['written'], 0)
            self.assertEqual(report['domains'][domain]['errors'], 0)
        with sqlite3.connect(pending.store_path(self.state, 'user_profiles')) as db:
            self.assertEqual(db.execute('SELECT * FROM records ORDER BY record_id').fetchall(), records_before)
            self.assertEqual(db.execute('SELECT * FROM sources').fetchall(), sources_before)
        self.assertEqual(report['stored_totals']['domains_known'], 8)
        self.assertNotIn('provide_private_input', report['ingest_evidence']['next_actions'])
        summary = runner.Runner.__new__(runner.Runner).ingest_summary(report)
        value = {'schema': 'offmenu-run-receipt/2', 'job_id': 'retained-eight-domain-ingest',
            'job_version': 2, 'operation': 'retained_ingest_all', 'job_key': 'b' * 64,
            'implementation_sha256': 'c' * 64, 'input_sha256': 'd' * 64,
            'observed_at': '2026-10-22T00:00:00Z', 'outcome': 'partial', 'ingest': summary}
        runner.validate_ingest_receipt(value)
        runner.validate_supplement(runner.build_supplement(report))

    def test_evidence_retains_all_assignments_without_private_input_or_missing_access_action(self):
        sources = self.private_sources()
        snapshot = pending.collect_pending_work(sources, self.state)
        collector = evidence.EvidenceCollector(sources, self.config)
        report = {'status': 'complete', 'domains': {}, 'pending_work': snapshot['summary']}
        value = collector.capture('post', report, pending_private=snapshot)
        evidence.validate_evidence(value)
        self.assertEqual(value['domain_scope'], dict.fromkeys(APP_MANAGED_DOMAINS, 'app_managed'))
        self.assertEqual(sum(value['catalog']['domain_mappings'][d]['assignments'] for d in APP_MANAGED_DOMAINS), 91)
        for domain in APP_MANAGED_DOMAINS:
            self.assertEqual(value['catalog']['domain_mappings'][domain]['eligibility'][evidence.ELIGIBILITY_COLUMNS.index('awaiting_input')], 0)
            self.assertEqual(value['cursors']['domains'][domain][0], 0)
        self.assertNotIn('provide_private_input', value['next_actions'])
        self.assertNotIn('restore_source_read_access', value['next_actions'])
        self.assertNotIn('continue_current_ingest', value['next_actions'])
        self.assertNotIn('/never-read', json.dumps(value))

    def test_old_pending_and_evidence_canonical_bytes_remain_valid_and_unmodified(self):
        old = runner.unknown_pending_work()
        old['awaiting_input_domains'] = list(APP_MANAGED_DOMAINS)
        raw = runner.canonical(old)
        runner.validate_pending_work(old)
        self.assertEqual(runner.canonical(old), raw)
        old_evidence = evidence.sanitize_evidence({'phase': 'pre', 'next_actions': ['provide_private_input']})
        raw_evidence = runner.canonical(old_evidence)
        evidence.validate_evidence(old_evidence)
        self.assertEqual(runner.canonical(old_evidence), raw_evidence)
        self.assertNotIn('domain_scope', old_evidence)
        self.assertNotIn('scope', old)

    def test_optional_scope_is_strict_not_an_unvalidated_escape_hatch(self):
        summary = pending.collect_pending_work([], self.state)['summary']
        for mutate in (lambda s: s['scope'].update(extra='private'),
                       lambda s: s['scope']['app_managed_assignments'].update(inventory=True),
                       lambda s: s['scope'].update(policy='arbitrary'),
                       lambda s: s['awaiting_input_domains'].append('inventory'),
                       lambda s: s['domains']['inventory'].update(awaiting_input=1, assignments_total=1)):
            bad = copy.deepcopy(summary)
            mutate(bad)
            with self.assertRaises(runner.Stop):
                runner.validate_pending_work(bad)
        value = evidence.sanitize_evidence({'domain_scope': {}})
        value['domain_scope']['inventory'] = 'awaiting_input'
        with self.assertRaises(ValueError):
            evidence.validate_evidence(value)

    def test_cached_old_scope_is_recounted_not_reused_as_current_blockers(self):
        sources = self.private_sources()
        collector = evidence.EvidenceCollector(sources, self.config)
        collector.capture('pre', {'status': 'running'})
        path = self.state / 'ingest-evidence.private.json'
        old = json.loads(path.read_text())
        old['summary'].pop('domain_scope')
        path.write_text(json.dumps(old))
        recovered = evidence.EvidenceCollector(sources, self.config)
        self.assertEqual(recovered.catalog['inspected'], 0)
        self.assertEqual(len(recovered.sources), 91)

    def test_console_never_solicits_private_inputs_even_for_legacy_snapshot(self):
        old = runner.unknown_pending_work()
        old['status'] = 'available'
        old['awaiting_input_domains'] = list(APP_MANAGED_DOMAINS)
        out = io.StringIO()
        with redirect_stdout(out):
            runner.Runner.__new__(runner.Runner).announce_remaining(old, 'Generated')
        self.assertIn('app_managed', out.getvalue())
        self.assertIn('external-ingest requirement=none', out.getvalue())
        self.assertNotIn('Awaiting explicitly supplied', out.getvalue())
        self.assertNotIn('awaiting_input=1', out.getvalue())


if __name__ == '__main__':
    unittest.main()
