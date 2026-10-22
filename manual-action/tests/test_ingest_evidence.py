"""Generated-only evidence fixtures: no host catalog, source dataset or live DB."""
import copy
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import ingest_evidence as evidence
from ingest_api import DOMAINS


def report():
    return {'status': 'running', 'workers': 2, 'elapsed_seconds': 1,
        'domains': {d: {'read': 0, 'written': 0, 'unchanged': 0, 'reused_rows': 0,
            'skipped': 0, 'errors': 0} for d in DOMAINS},
        'pending_work': {'status': 'available', 'domains': {d: {'failed': 0} for d in DOMAINS},
            'totals': {'files_remaining': 1}, 'awaiting_input_domains': []}}


class EvidenceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.config = {'state_dir': str(self.root), 'catalog_sha256': 'a' * 64,
            'evidence_max_seconds': .25, 'terminal_progress': False}

    def source(self, **changes):
        return {'id': 'generated-source', 'path': '/not-opened/private-file.json',
            'format': 'json', 'fields': ['name', 'ingredients', 'steps'],
            'domains': ['recipes', 'ingredients'], 'disposition': 'candidate', **changes}

    def test_pre_post_owned_counts_and_null_unsupported(self):
        collector = evidence.EvidenceCollector([self.source()], self.config)
        first = collector.capture('pre', report())
        evidence.validate_evidence(first)
        after = report()
        after['domains']['recipes'].update(read=7, written=3, unchanged=2, skipped=1, errors=1)
        after['pending_work']['domains']['recipes']['failed'] = 2
        last = collector.capture('post', after, results={'recipes': {'stored_records': 12}})
        metrics = dict(zip(last['metric_columns'], last['observations']['recipes']['current']))
        delta = dict(zip(last['metric_columns'], last['observations']['recipes']['delta']))
        self.assertEqual(metrics['written'], 3)
        self.assertEqual(metrics['failed_sources'], 2)
        self.assertEqual(metrics['stored_records'], 12)
        self.assertIsNone(metrics['accepted_rows'])
        self.assertIsNone(metrics['unresolved_references'])
        self.assertIsNone(metrics['deduplicated_records'])
        self.assertIsNone(delta['stored_records'])
        self.assertEqual(delta['written'], 3)
        self.assertIn('review_source_errors', last['next_actions'])

    def test_budget_and_unchanged_catalog_resume_are_lossless(self):
        sources = [self.source(id=str(i), format='unknown-untrusted-format') for i in range(7)]
        config = {**self.config, 'evidence_max_items': 2}
        collector = evidence.EvidenceCollector(sources, config)
        first = collector.capture('pre', report())
        self.assertEqual((first['catalog']['inspected'], first['catalog']['remaining']), (2, 5))
        self.assertIn('continue_evidence_scan', first['next_actions'])
        resumed = evidence.EvidenceCollector(sources, config)
        second = resumed.capture('pre', report())
        self.assertEqual(second['catalog']['inspected'], 4)
        resumed.capture('checkpoint', report())
        final = resumed.capture('post', report())
        self.assertEqual(final['catalog']['formats'], {'other': 7})
        self.assertEqual(final['catalog']['remaining'], 0)
        self.assertEqual(final['catalog']['domain_mappings']['recipes']['assignments'], 7)
        evidence.validate_evidence(final)
        changed = evidence.EvidenceCollector(sources, {**config, 'catalog_sha256': 'b' * 64})
        self.assertEqual(changed.capture('pre', report())['catalog']['inspected'], 2)

    def test_source_rows_paths_errors_and_households_never_publish(self):
        secret = 'DO-NOT-PUBLISH-Jane-42-PRIVATE'
        sources = [self.source(id=secret, path='/' + secret, provider=secret,
            fields=[secret, 'ingredients'], raw_rows=[secret], errors=[secret]),
            self.source(id=secret + '-household', domains=['inventory'], fields=[secret],
                metadata={'household_scope': True, 'user_supplied': True})]
        value = report()
        value['domains']['recipes']['error_codes'] = [secret]
        value['domains']['recipes']['error_message'] = secret
        collector = evidence.EvidenceCollector(sources, self.config)
        public = collector.capture('post', value)
        self.assertNotIn(secret, json.dumps(public))
        self.assertEqual(public['catalog']['field_presence']['other'], 1)
        self.assertEqual(public['catalog']['shapes']['private_redacted'], 1)
        private = json.loads((self.root / 'ingest-evidence.private.json').read_text())
        self.assertFalse(private['source_rows_collected'])
        self.assertEqual(len(private['descriptor_examples']), 1)
        self.assertEqual((self.root / 'ingest-evidence.private.json').stat().st_mode & 0o777, 0o600)

    def test_unknown_schema_private_artifact_and_finite_signals(self):
        private_field = 'customer-private-schema-column'
        collector = evidence.EvidenceCollector([self.source(fields=['name', private_field],
            field_types={'name': 'string', private_field: 'stolen-value'})], self.config)
        value = collector.capture('post', report())
        details = value['schema_details']
        data = (self.root / details['artifact']).read_bytes()
        self.assertEqual(hashlib.sha256(data).hexdigest(), details['artifact_sha256'])
        self.assertNotIn(private_field, json.dumps(value))
        self.assertIn(private_field, data.decode())
        self.assertEqual(value['catalog']['field_types'], {'string': 1, 'unknown': 1})
        self.assertEqual(details['unknown_shape_descriptors'], 1)
        self.assertEqual(details['representatives'], 1)

    def test_shape_hints_are_not_observed_parsed_acceptance(self):
        value = evidence.EvidenceCollector([self.source(schema_shape='recipe_structured')],
            self.config).capture('pre', report())
        self.assertEqual(value['catalog']['shape_bases'], {'reviewed_adapter_contract': 1})
        self.assertIsNone(value['observations']['recipes']['current'][evidence.METRICS.index('accepted_rows')])

    def test_cursor_sample_distinguishes_unknown_and_eof_errors(self):
        snapshot = {'sources': [
            {'domain': 'recipes', 'cursor': 3, 'written': 2, 'status': 'partial', 'read_complete': False},
            {'domain': 'recipes', 'cursor': 5, 'written': 4, 'status': 'partial', 'read_complete': True},
            {'domain': 'inventory', 'synthetic_requirement': True}]}
        collector = evidence.EvidenceCollector([], self.config)
        value = collector.capture('pre', report(), pending_private=snapshot)
        row = dict(zip(value['cursor_columns'], value['cursors']['domains']['recipes']))
        self.assertEqual(row['cursor_sum'], 8)
        self.assertEqual(row['read_complete'], 1)
        self.assertEqual(row['resumable'], 1)
        self.assertEqual(value['cursors']['detail_rows_total'], 3)
        self.assertEqual(value['cursors']['domains']['inventory'][0], 0)
        limited = evidence.EvidenceCollector([], {**self.config, 'evidence_max_items': 1})
        value = limited.capture('pre', report(), pending_private=snapshot)
        self.assertEqual(value['cursors']['status'], 'partial')
        self.assertEqual(value['cursors']['detail_rows_inspected'], 1)
        self.assertIn('checkpoint_sample_incomplete', value['quality_codes'])

    def test_collector_never_opens_source_or_sqlite(self):
        with mock.patch('sqlite3.connect', side_effect=AssertionError('no database reads')), \
                mock.patch('builtins.open', side_effect=AssertionError('no raw file reads')):
            collector = evidence.EvidenceCollector([self.source()], self.config)
            value = collector.capture('post', report())
        self.assertNotIn('collector_failed', value['quality_codes'])

    def test_failure_isolation_and_symlink_refusal(self):
        collector = evidence.EvidenceCollector([self.source()], self.config)
        with mock.patch.object(collector, '_scan', side_effect=RuntimeError('private exception text')):
            value = collector.capture('post', report())
        self.assertEqual(value['status'], 'unknown')
        evidence.validate_evidence(value)
        self.assertNotIn('private exception text', json.dumps(value))
        target = self.root / 'sensitive-generated-fixture'
        target.write_text('unchanged')
        (self.root / 'ingest-evidence.private.json').symlink_to(target)
        value = evidence.EvidenceCollector([], self.config).capture('post', report())
        self.assertIn('private_write_failed', value['quality_codes'])
        self.assertEqual(target.read_text(), 'unchanged')

    def test_strict_validation_rejects_unknown_fields_boolean_and_count_loss(self):
        value = evidence.EvidenceCollector([self.source()], self.config).capture('post', report())
        for mutate in (
                lambda x: x.update(path='/secret'),
                lambda x: x['catalog'].update(total=True),
                lambda x: x['catalog'].update(remaining=9),
                lambda x: x['resources'].update(workers=True),
                lambda x: x['observations']['recipes']['current'].__setitem__(0, True)):
            altered = copy.deepcopy(value)
            mutate(altered)
            with self.assertRaises(ValueError):
                evidence.validate_evidence(altered)

    def test_partial_catalog_and_binding_do_not_claim_final_completion(self):
        value = report()
        value.update(status='complete')
        value['pending_work']['totals'] = {'files_remaining': 0}
        collector = evidence.EvidenceCollector([], {**self.config, 'catalog_truncated': True})
        result = collector.capture('post', value)
        self.assertIn('resume_local_catalog', result['next_actions'])
        self.assertNotIn('retained_ingest_complete', result['next_actions'])
        collector = evidence.EvidenceCollector([], self.config)
        result = collector.capture('post', value)
        self.assertIn('verify_application_binding', result['next_actions'])
        self.assertIn('retained_ingest_complete', result['next_actions'])

    def test_compact_supplement_is_bounded(self):
        sources = [self.source(id=str(i), format=fmt, fields=list(evidence.FIELDS))
            for i, fmt in enumerate(sorted(evidence.FORMATS))]
        value = evidence.EvidenceCollector(sources, self.config).capture('post', report())
        self.assertLess(len(json.dumps(value, separators=(',', ':')).encode()), 64 * 1024)
        evidence.validate_evidence(value)

    def test_acquired_routes_access_failures_and_schema_reason_counts(self):
        sources = [self.source(acquired_adapter='fr_cnous_menus', disposition='unreadable',
            reason='read_permission_denied', fields=[])]
        result = {'recipes': {'sources': [{'diagnostics': {
            'reason_counts': {'acquired_menu_xml_no_menu_nodes': 3, '/private/unknown-reason': 2},
            'schema_needs': {'acquired_menu_xml_no_menu_nodes': 3}}}]}}
        value = evidence.EvidenceCollector(sources, self.config).capture('post', report(), results=result)
        routes = dict(zip(value['catalog']['adapter_route_columns'],
            value['catalog']['domain_mappings']['recipes']['adapter_routes']))
        self.assertEqual(routes['fr_cnous_menus'], 1)
        self.assertEqual(value['catalog']['reason_codes']['read_permission_denied'], 1)
        self.assertIn('restore_source_read_access', value['next_actions'])
        diagnostics = value['adapter_diagnostics']
        counts = dict(zip(diagnostics['reason_columns'], diagnostics['domains']['recipes']['reason_counts']))
        self.assertEqual(counts['acquired_menu_xml_no_menu_nodes'], 3)
        self.assertEqual(counts['other'], 2)
        self.assertNotIn('/private/unknown-reason', json.dumps(value))
        self.assertIn('review_unsupported_shapes', value['next_actions'])
        self.assertEqual(diagnostics['source_summaries_total'], 1)

    def test_private_fifo_checkpoint_does_not_block(self):
        import os
        os.mkfifo(self.root / 'ingest-evidence.private.json')
        collector = evidence.EvidenceCollector([], self.config)
        value = collector.capture('pre', report())
        self.assertNotIn('collector_failed', value['quality_codes'])

    def test_stale_private_schema_hash_is_not_presented_as_available(self):
        source = self.source(fields=['unrecognized_field'])
        first = evidence.EvidenceCollector([source], self.config).capture('pre', report())
        self.assertIsNotNone(first['schema_details']['artifact_sha256'])
        (self.root / 'ingest-schema.private.json').write_text('replaced locally')
        second = evidence.EvidenceCollector([source], self.config).capture('pre', report())
        self.assertIsNone(second['schema_details']['artifact_sha256'])
        self.assertEqual(second['schema_details']['status'], 'unavailable')

    def test_performance_projects_only_existing_timers_and_known_file_size(self):
        sample=report();sample['domains']['recipes']['timing']={'elapsed_ms':12,
            'active_source_elapsed_ms':9,'since_last_progress_ms':3,
            'active_source_bytes':108000000,'sources_timed':1,'completed_source_elapsed_ms':2,
            'private_path':'/private/unapproved'}
        value=evidence.EvidenceCollector([],self.config).capture('checkpoint',sample)
        self.assertEqual(value['performance']['domains']['recipes'],[12,9,3,108000000,1,2])
        self.assertTrue(all(x is None for x in value['performance']['domains']['inventory']))
        self.assertNotIn('/private/unapproved',json.dumps(value))
        self.assertEqual(value['performance']['byte_scope'],'active_source_catalog_file_size_not_processed_bytes')

    def test_worst_finite_enum_supplement_is_bounded_without_count_loss(self):
        value = evidence.sanitize_evidence({})
        cap = evidence.MAX_COUNT
        for domain in DOMAINS:
            value['performance']['domains'][domain] = [cap] * len(evidence.PERFORMANCE_FIELDS)
        for row in value['observations'].values():
            for field in row:
                row[field] = [-cap if field == 'delta' else cap] * len(evidence.METRICS)
        for domain in DOMAINS:
            value['cursors']['domains'][domain] = [cap] * len(evidence.CURSOR_FIELDS)
        value['catalog'].update(total=cap, inspected=cap, remaining=0)
        for name, enums in (('formats', evidence.FORMATS), ('shapes', evidence.SHAPES),
                ('shape_bases', evidence.SHAPE_BASES), ('eligibility', evidence.ELIGIBILITY),
                ('reason_codes', evidence.CATALOG_REASONS)):
            keys = sorted(enums)
            counts = {key: cap // len(keys) for key in keys}
            counts[keys[0]] += cap - sum(counts.values())
            value['catalog'][name] = counts
        for name, enums in (('field_presence', evidence.FIELDS), ('field_types', evidence.FIELD_TYPES)):
            value['catalog'][name] = {key: cap for key in enums}
        for row in value['catalog']['domain_mappings'].values():
            row['assignments'] = cap
            for name in ('eligibility', 'adapter_routes'):
                row[name] = [cap // len(row[name])] * len(row[name])
                row[name][0] += cap - sum(row[name])
        for row in value['adapter_diagnostics']['domains'].values():
            for name in row:
                columns = (evidence.ADAPTER_COUNT_COLUMNS if name == 'parser_counts' else
                    evidence.SCHEMA_NEED_COLUMNS if name == 'schema_need_counts' else evidence.ACQUIRED_REASON_COLUMNS)
                row[name] = [cap] * len(columns)
        value['next_actions'] = sorted(evidence.NEXT_ACTIONS)
        value['quality_codes'] = sorted(evidence.QUALITY_CODES)
        for key in value['resources']:
            value['resources'][key] = cap
        value['schema_details'].update(artifact_sha256='f' * 64,
            representatives=cap, unknown_shape_descriptors=cap)
        evidence.validate_evidence(value)
        # Main receipt carries a hash-bound fixed-schema readable supplemental;
        # large counters/enum histograms are retained rather than truncated.
        self.assertLess(len(json.dumps(value, indent=2).encode()), 64 * 1024)

    def test_reviewed_adapter_reason_enums_have_complete_public_coverage(self):
        from ingest_acquired_recipes import REASONS as recipe_reasons
        from ingest_acquired_menus import REASONS as menu_reasons
        self.assertEqual(evidence.RECIPE_REASONS, recipe_reasons)
        self.assertFalse(menu_reasons - evidence.ACQUIRED_REASONS)
        self.assertFalse(recipe_reasons - evidence.ACQUIRED_REASONS)


if __name__ == '__main__':
    unittest.main()
