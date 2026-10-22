"""Synthetic-only offline evidence tests. Never discover or inspect Foo/user data."""
import contextlib
import copy
import fcntl
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from ingest_api import DOMAINS, source_key
from ingest_store import SCHEMA as STORE_SCHEMA
import relational_readiness as rr

FIXTURE = Path(__file__).parent / 'fixtures' / 'relational-readiness.synthetic.json'


class SyntheticState:
    def __init__(self, root, payloads=None):
        self.root = Path(root)
        self.payloads = copy.deepcopy(payloads or json.loads(FIXTURE.read_text())['records'])
        self.catalog = {'complete': True, 'truncated': False, 'sources': []}
        self.receipt = {'report': {'schema': 'offmenu-ingest-report/1', 'run_id': 'synthetic-run',
                                  'status': 'complete', 'catalog_truncated': False},
                        'domains': {}, 'output_identities': {}}
        self.source_for = {}
        for domain in DOMAINS:
            if domain in rr.PRIVATE and not self.payloads[domain]:
                continue
            if domain == 'ingredients':
                descriptor = {'id': 'synthetic-recipe-source', 'path': '/SYNTHETIC/NOT/READ/recipe.json',
                              'domains': ['recipes', 'ingredients'], 'provider': 'synthetic-provider'}
            elif domain == 'recipes':
                descriptor = {'id': 'synthetic-recipe-source', 'path': '/SYNTHETIC/NOT/READ/recipe.json',
                              'domains': ['recipes', 'ingredients'], 'provider': 'synthetic-provider'}
            else:
                descriptor = {'id': 'synthetic-' + domain, 'path': '/SYNTHETIC/NOT/READ/' + domain + '.json',
                              'domains': [domain], 'provider': 'synthetic-provider'}
            if descriptor not in self.catalog['sources']:
                self.catalog['sources'].append(descriptor)
            self.source_for[domain] = source_key(descriptor)
        for domain in DOMAINS:
            path = rr.store_path(self.root, domain)
            path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
            path.with_suffix('.writer.lock').touch(mode=0o600)
            db = sqlite3.connect(path)
            db.executescript(STORE_SCHEMA)
            for key, value in {'domain': domain, 'binding': rr.BINDING, 'schema_version': '1',
                               'database_id': 'synthetic-db-' + domain, 'record_count': str(len(self.payloads[domain]))}.items():
                db.execute('INSERT INTO ingest_meta VALUES (?,?)', (key, value))
            source = self.source_for.get(domain)
            if source:
                self.insert_source(db, source, 'v1')
                for i, payload in enumerate(self.payloads[domain]):
                    self.insert_record(db, source, 'v1', payload, i)
            db.commit()
            db.close()
            self.receipt['domains'][domain] = {'status': 'complete' if source else 'awaiting_user_input',
                'stored_records': len(self.payloads[domain]), 'database_id': 'synthetic-db-' + domain,
                'sources': [{'source_key': source, 'source_version': 'v1', 'status': 'complete', 'errors': 0}] if source else []}
        self.refresh_receipt()

    @staticmethod
    def insert_source(db, sk, version, provider='synthetic-provider', status='complete'):
        db.execute('INSERT OR IGNORE INTO sources(source_key,version,path,format,provider,fingerprint_json,status,updated_at) VALUES(?,?,?,?,?,?,?,?)',
                   (sk, version, '/SYNTHETIC/NOT/READ', 'json', provider, '{}', status, 0))

    @staticmethod
    def insert_record(db, sk, version, payload, number=0):
        db.execute('INSERT INTO records VALUES(?,?,?,?,?,?,?)',
                   (sk, version, str(payload['id']), number, rr.digest(payload), rr.canonical(payload), 0))
        for ordinal, edge in enumerate(payload.get('relations', [])):
            db.execute('INSERT INTO relations VALUES(?,?,?,?,?,?,?,?)',
                       (sk, version, str(payload['id']), ordinal, edge.get('kind', 'related'), edge.get('target_domain'),
                        str(edge['target_id']) if edge.get('target_id') is not None else None, rr.canonical(edge)))

    @contextlib.contextmanager
    def db(self, domain):
        db = sqlite3.connect(rr.store_path(self.root, domain))
        try:
            yield db
            db.commit()
        finally:
            db.close()

    def refresh_receipt(self):
        for domain in DOMAINS:
            path = rr.store_path(self.root, domain)
            self.receipt['output_identities'][domain] = rr.database_identity(path)
        self.receipt['report']['catalog_sha256'] = hashlib.sha256(json.dumps(self.catalog['sources'], sort_keys=True, ensure_ascii=True, separators=(',', ':')).encode()).hexdigest()
        for name, value in (('catalog.private.json', self.catalog), ('last-run.private.json', self.receipt), ('last-report.json', self.receipt['report'])):
            (self.root / name).write_text(json.dumps(value))

    def reseal_counts(self, domain):
        with self.db(domain) as db:
            count = db.execute('SELECT count(*) FROM records').fetchone()[0]
            db.execute("UPDATE ingest_meta SET value=? WHERE key='record_count'", (str(count),))
        self.receipt['domains'][domain]['stored_records'] = count
        self.refresh_receipt()


class ReadinessTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.state = SyntheticState(Path(self.temp.name) / 'state')

    def report(self, **kwargs):
        return rr.build_report(self.state.root, **kwargs)

    def test_all_eight_scoped_edges_and_no_app_readiness(self):
        report = self.report()
        self.assertEqual(set(report['domains']), set(DOMAINS))
        self.assertEqual(report['snapshot']['status'], 'stable_terminal_observation')
        self.assertEqual(report['evidence_status'], 'complete_for_supported_staging_contracts')
        self.assertEqual(report['counts']['resolved'], 4)
        self.assertEqual(report['counts']['reciprocal_mismatches'], 0)
        self.assertEqual(report['domains']['user_profiles']['status'], 'schema_only_app_managed')
        legacy = {'domains': {'user_profiles': {'status': 'schema_only_awaiting_user_input'}}}
        self.assertEqual(rr.sanitized_summary(legacy)['domains']['user_profiles']['status'], 'schema_only_awaiting_user_input')
        self.assertEqual(report['domains']['inventory']['scope'], 'not_exercised_no_input')
        self.assertEqual(report['status'], 'blocked')
        self.assertEqual(report['fetch_status'], 'disabled')
        self.assertEqual(report['app_binding_status'], 'app_binding_unknown')
        supplier = next(x for x in report['relation_resolutions'] if x['join_contract_id'] == 'supplier_entities')
        self.assertEqual(supplier['targets'][0]['record_id'], 'hashed-occurrence-b')
        self.assertEqual(supplier['lookup_key']['source_native_id_lexical'], '002')
        self.assertIsNone(supplier['canonical_entity_id'])

    def test_report_does_not_mutate_source_files_or_create_missing_state(self):
        def snapshot():
            return {str(p): (rr.file_identity(p), hashlib.sha256(p.read_bytes()).hexdigest())
                    for p in self.state.root.rglob('*') if p.is_file()}
        before = snapshot()
        self.report()
        self.assertEqual(before, snapshot())
        missing = Path(self.temp.name) / 'does-not-exist'
        report = rr.build_report(missing)
        self.assertFalse(missing.exists())
        self.assertEqual(report['evidence_status'], 'incomplete')
        self.assertIsNone(rr.sanitized_summary(report)['domains']['recipes']['stored_records'])

    def test_no_network_or_subprocess_or_store_constructor(self):
        with patch('socket.socket', side_effect=AssertionError('network forbidden')), \
             patch('subprocess.Popen', side_effect=AssertionError('subprocess forbidden')), \
             patch('ingest_store.DomainStore', side_effect=AssertionError('write store forbidden')):
            self.assertEqual(self.report()['counts']['resolved'], 4)

    def test_cross_source_same_name_or_identifier_never_matches(self):
        with self.state.db('suppliers') as db:
            db.execute("DELETE FROM records WHERE record_id='hashed-occurrence-b'")
            other = 'different-source'
            self.state.insert_source(db, other, 'v1')
            self.state.insert_record(db, other, 'v1', {'id': 'other', 'entity_id': '002', 'name': 'SYNTHETIC B', 'provider': 'synthetic-provider', 'type': 'organization'})
        # Extra unselected history does not enter the same-source lookup.
        self.state.reseal_counts('suppliers')
        report = self.report()
        edge = next(x for x in report['relation_resolutions'] if x['join_contract_id'] == 'supplier_entities')
        self.assertEqual(edge['disposition'], 'missing')
        self.assertEqual(edge['targets'], [])
        self.assertEqual(report['domains']['suppliers']['historical_records'], 1)

    def test_supplier_multiple_occurrences_are_ambiguous_not_deduplicated(self):
        with self.state.db('suppliers') as db:
            row = copy.deepcopy(self.state.payloads['suppliers'][1])
            row['id'] = 'hashed-occurrence-c'
            self.state.insert_record(db, self.state.source_for['suppliers'], 'v1', row)
        self.state.reseal_counts('suppliers')
        edge = next(x for x in self.report()['relation_resolutions'] if x['join_contract_id'] == 'supplier_entities')
        self.assertEqual(edge['disposition'], 'ambiguous')
        self.assertEqual(len(edge['targets']), 2)

    def test_supplier_leading_zeros_and_value_types_are_not_erased(self):
        with self.state.db('suppliers') as db:
            db.execute("DELETE FROM records WHERE record_id='hashed-occurrence-b'")
            self.state.insert_record(db, self.state.source_for['suppliers'], 'v1', {'id': 'numeric', 'entity_id': 2, 'provider': 'synthetic-provider', 'type': 'organization'})
        self.state.reseal_counts('suppliers')
        edge = next(x for x in self.report()['relation_resolutions'] if x['join_contract_id'] == 'supplier_entities')
        self.assertEqual(edge['disposition'], 'missing')

    def test_ownership_occurrence_is_not_target_organization(self):
        with self.state.db('suppliers') as db:
            db.execute("DELETE FROM records WHERE record_id='hashed-occurrence-b'")
            self.state.insert_record(db, self.state.source_for['suppliers'], 'v1', {'id': 'edge-occurrence', 'entity_id': '002', 'provider': 'synthetic-provider', 'type': 'company_ownership'})
        self.state.reseal_counts('suppliers')
        edge = next(x for x in self.report()['relation_resolutions'] if x['join_contract_id'] == 'supplier_entities')
        self.assertEqual(edge['disposition'], 'missing')

    def test_product_hash_never_matches_barcode_wrapper(self):
        with self.state.db('ingredients') as db:
            self.state.insert_record(db, self.state.source_for['ingredients'], 'v1', {'id': 'product-mention', 'kind': 'ingredient_mention',
                'relations': [{'kind': 'ingredient_of_product', 'target_domain': 'barcodes', 'target_id': '000123', 'source_native_product_id': '000123'}]})
        self.state.reseal_counts('ingredients')
        edge = next(x for x in self.report()['relation_resolutions'] if x['relation_kind'] == 'ingredient_of_product')
        self.assertEqual(edge['disposition'], 'unsupported')
        self.assertIsNone(edge['lookup_key'])
        self.assertEqual(edge['targets'], [])

    def test_source_version_selection_excludes_historical_target(self):
        with self.state.db('ingredients') as db:
            db.execute('DELETE FROM relations')
            db.execute('DELETE FROM records')
            self.state.insert_source(db, self.state.source_for['ingredients'], 'v0')
            self.state.insert_record(db, self.state.source_for['ingredients'], 'v0', self.state.payloads['ingredients'][0])
        self.state.reseal_counts('ingredients')
        edge = next(x for x in self.report()['relation_resolutions'] if x['join_contract_id'] == 'recipe_mentions')
        self.assertEqual(edge['disposition'], 'missing')

    def test_missing_reciprocal_reported(self):
        with self.state.db('ingredients') as db:
            db.execute('DELETE FROM relations')
            payload = copy.deepcopy(self.state.payloads['ingredients'][0])
            payload['relations'] = []
            db.execute('UPDATE records SET payload_json=?, content_sha256=?', (rr.canonical(payload), rr.digest(payload)))
        self.state.refresh_receipt()
        report = self.report()
        self.assertEqual(report['counts']['reciprocal_mismatches'], 1)

    def test_tampered_relation_detail_is_not_resolved(self):
        with self.state.db('recipes') as db:
            db.execute("UPDATE relations SET target_id='menu-child' WHERE kind='has_ingredient_mention'")
        self.state.refresh_receipt()
        edge = next(x for x in self.report()['relation_resolutions'] if x['join_contract_id'] == 'recipe_mentions')
        self.assertEqual(edge['disposition'], 'unsupported')
        self.assertEqual(edge['reason_code'], 'relation_payload_disagrees')

    def test_hash_mismatch_makes_target_coverage_unknown(self):
        with self.state.db('ingredients') as db:
            db.execute("UPDATE records SET content_sha256='not-the-hash'")
        self.state.refresh_receipt()
        report = self.report()
        self.assertEqual(report['domains']['ingredients']['payload_hash_mismatches'], 1)
        edge = next(x for x in report['relation_resolutions'] if x['join_contract_id'] == 'recipe_mentions')
        self.assertEqual(edge['disposition'], 'unsupported')
        self.assertEqual(edge['reason_code'], 'target_snapshot_coverage_incomplete')

    def test_budget_never_turns_unscanned_targets_into_missing(self):
        report = self.report(limits=rr.Limits(max_records=1))
        self.assertEqual(report['evidence_status'], 'incomplete')
        self.assertEqual(report['counts']['scanned_records'], 1)
        self.assertEqual(report['counts']['missing'], 0)
        self.assertIn('resource_budget_exhausted', report['domains']['ingredients']['diagnostics'])

    def test_active_writer_stops_snapshot_claim(self):
        path = rr.store_path(self.state.root, 'ingredients').with_suffix('.writer.lock')
        fd = os.open(path, os.O_RDONLY)
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            report = self.report()
        finally:
            os.close(fd)
        self.assertEqual(report['snapshot']['status'], 'unstable_or_unknown')
        self.assertEqual(report['domains']['ingredients']['scanned_records'], 0)
        self.assertEqual(report['counts']['resolved'], 0)

    def test_missing_lock_never_claims_coordinated_snapshot(self):
        rr.store_path(self.state.root, 'recipes').with_suffix('.writer.lock').unlink()
        report = self.report()
        self.assertEqual(report['snapshot']['status'], 'unstable_or_unknown')
        self.assertEqual(report['counts']['resolved'], 0)

    def test_changed_database_invalidates_receipt(self):
        with self.state.db('barcodes') as db:
            db.execute("UPDATE ingest_meta SET value='replacement' WHERE key='database_id'")
        report = self.report()
        self.assertEqual(report['domains']['barcodes']['coverage'], 'incomplete')
        self.assertIn('quiescent_terminal_snapshot_not_established', report['domains']['barcodes']['diagnostics'])

    def test_unknown_source_version_not_inferred_from_latest_timestamp(self):
        del self.state.receipt['domains']['recipes']['sources'][0]['source_version']
        self.state.refresh_receipt()
        report = self.report()
        self.assertEqual(report['domains']['recipes']['source_selection'], 'unknown')
        self.assertEqual(report['domains']['recipes']['scanned_records'], 0)
        self.assertEqual(report['evidence_status'], 'incomplete')

    def test_partial_and_error_source_not_complete(self):
        with self.state.db('ingredients') as db:
            db.execute("UPDATE sources SET status='complete_with_errors', errors=1")
        self.state.refresh_receipt()
        report = self.report()
        self.assertEqual(report['domains']['ingredients']['coverage'], 'incomplete')
        self.assertIn('selected_source_not_complete', report['domains']['ingredients']['diagnostics'])

    def test_owner_fk_violation_is_detected(self):
        with self.state.db('barcodes') as db:
            db.execute("INSERT INTO relations VALUES('missing-source','v1','absent',0,'related','recipes','recipe-a','{}')")
        self.state.refresh_receipt()
        report = self.report()
        self.assertEqual(report['domains']['barcodes']['foreign_keys'], 'failed')

    def test_private_scope_missing_and_cross_user_attempt_never_resolves(self):
        payloads = copy.deepcopy(self.state.payloads)
        payloads['user_profiles'] = [{'id': 'profile-a', 'household_namespace': 'synthetic', 'household_id': 'H1', 'user_id': 'U1'}]
        payloads['inventory'] = [{'id': 'item-a', 'household_namespace': 'synthetic', 'household_id': 'H1', 'user_id': 'U1',
            'relations': [{'kind': 'belongs_to', 'target_domain': 'user_profiles', 'target_id': 'profile-a',
                           'household_namespace': 'synthetic', 'household_id': 'H2', 'user_id': 'U2'}]}, {'id': 'item-b'}]
        state = SyntheticState(Path(self.temp.name) / 'private-synthetic', payloads)
        report = rr.build_report(state.root)
        self.assertEqual(report['domains']['inventory']['cross_scope_attempts'], 1)
        self.assertEqual(report['domains']['inventory']['missing_scope_fields'], 3)
        edge = next(x for x in report['relation_resolutions'] if x['relation_kind'] == 'belongs_to')
        self.assertEqual(edge['disposition'], 'unsupported')
        self.assertEqual(edge['reason_code'], 'cross_household_or_user_scope_attempt')

    def test_summary_whitelist_drops_identifiers_and_hostile_labels(self):
        report = self.report()
        secret = 'SYNTHETIC-PRIVATE-SENTINEL'
        report['snapshot']['snapshot_id'] = secret
        report['domains']['user_profiles']['status'] = secret
        report['domains']['recipes']['normalization']['status'] = secret
        report['counts']['resolved'] = secret
        report['domains'][secret] = {'status': secret}
        report['relation_resolutions'][0]['relation_kind'] = secret
        safe = rr.sanitized_summary(report)
        rendered = rr.canonical(safe)
        for forbidden in (secret, 'source_key', 'record_id', 'recipe-a', 'synthetic-provider', '/SYNTHETIC', 'snapshot_id'):
            self.assertNotIn(forbidden, rendered)
        self.assertEqual(safe['domains']['user_profiles']['status'], 'unknown')
        self.assertIsNone(safe['counts']['resolved'])

    def test_reports_private_and_exclusive_no_overwrite(self):
        report = self.report()
        out = Path(self.temp.name) / 'reports'
        paths = rr.write_reports(out, report)
        self.assertEqual(out.stat().st_mode & 0o777, 0o700)
        self.assertTrue(all(p.stat().st_mode & 0o777 == 0o600 for p in paths))
        with self.assertRaises(FileExistsError):
            rr.write_reports(out, report)
        self.assertNotIn('source_key', paths[1].read_text())

    def test_symlinks_and_wal_without_shm_refused(self):
        path = rr.store_path(self.state.root, 'barcodes')
        backup = path.with_name('original.sqlite3')
        path.rename(backup)
        path.symlink_to(backup)
        report = self.report()
        self.assertIn('symlink_path_refused', report['domains']['barcodes']['diagnostics'])
        path.unlink()
        backup.rename(path)
        Path(str(path) + '-wal').write_bytes(b'SYNTHETIC NOT REAL WAL')
        report = self.report()
        self.assertIn('wal_present_read_deferred_without_copy_or_source_mutation', report['domains']['barcodes']['diagnostics'])
        self.assertFalse(Path(str(path) + '-shm').exists())

    def test_duplicate_json_keys_and_invalid_budgets_refused(self):
        with self.assertRaises(rr.ReadinessError):
            rr.Budget(rr.Limits()).parse('{"id":"a","id":"b"}')
        for kwargs in ({'max_records': 0}, {'max_relations': True}, {'max_json_bytes': 1.5}, {'max_seconds': float('nan')}, {'max_seconds': float('inf')}):
            with self.assertRaises(rr.ReadinessError):
                rr.Limits(**kwargs)

    def test_readonly_connection_rejects_mutation(self):
        db = rr.open_readonly(rr.store_path(self.state.root, 'recipes'), rr.Budget(rr.Limits()), quiescent=True)
        try:
            with self.assertRaises(sqlite3.OperationalError):
                db.execute('DELETE FROM records')
            self.assertEqual(db.execute('PRAGMA query_only').fetchone(), (1,))
            self.assertEqual(db.execute('PRAGMA trusted_schema').fetchone(), (0,))
        finally:
            db.close()

    def test_normalization_absence_is_explicit_not_success(self):
        report = self.report()
        self.assertEqual(report['normalization']['status'], 'absent')
        self.assertEqual(report['domains']['recipes']['normalization']['no_artifact'], 3)
        self.assertEqual(report['domains']['recipes']['normalization']['gold_unknown'], 3)

    def test_never_acquires_writer_lock_even_temporarily(self):
        with patch('fcntl.flock', side_effect=AssertionError('report must not lock writer')):
            self.assertEqual(self.report()['counts']['resolved'], 4)

    def test_live_receipt_does_not_open_any_staging_database(self):
        path = self.state.root / 'last-report.json'
        value = json.loads(path.read_text())
        value['status'] = 'running'
        path.write_text(json.dumps(value))
        with patch('relational_readiness.sqlite3.connect', side_effect=AssertionError('live DB inspection forbidden')):
            report = self.report()
        self.assertEqual(report['counts']['scanned_records'], 0)
        self.assertEqual(report['snapshot']['status'], 'unstable_or_unknown')

    def test_quiescent_wal_format_with_no_wal_creates_no_sidecars(self):
        path = rr.store_path(self.state.root, 'barcodes')
        with self.state.db('barcodes') as db:
            self.assertEqual(db.execute('PRAGMA journal_mode=WAL').fetchone(), ('wal',))
        self.assertEqual(path.read_bytes()[18:20], b'\x02\x02')
        self.assertFalse(Path(str(path) + '-wal').exists())
        self.state.refresh_receipt()
        before = {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in self.state.root.rglob('*') if p.is_file()}
        report = self.report()
        after = {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in self.state.root.rglob('*') if p.is_file()}
        self.assertEqual(before, after)
        self.assertEqual(report['domains']['barcodes']['coverage'], 'complete')
        self.assertEqual(report['snapshot']['atomic_cross_database_snapshot'], 'not_established')

    def test_rules_only_normalization_and_stale_artifacts_are_distinct(self):
        from normalization_core import NormalizationStore, run_rules
        payload = self.state.payloads['barcodes'][0]
        record = {'domain': 'barcodes', 'source_key': self.state.source_for['barcodes'],
                  'source_version': 'v1', 'record_id': payload['id'],
                  'content_sha256': rr.digest(payload), 'payload': payload}
        with NormalizationStore(self.state.root) as store:
            run_rules(record, store=store)
            stale = {**record, 'source_version': 'historical'}
            run_rules(stale, store=store)
        before = {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in self.state.root.rglob('*') if p.is_file()}
        report = self.report()
        after = {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in self.state.root.rglob('*') if p.is_file()}
        self.assertEqual(before, after)
        self.assertEqual(report['normalization']['orphan_or_stale_artifacts'], 1)
        self.assertEqual(report['domains']['barcodes']['normalization']['rules_only'], 1)
        self.assertEqual(report['domains']['barcodes']['normalization']['review_pending'], 1)
        self.assertEqual(report['domains']['barcodes']['normalization']['gold_blocked'], 1)

    def test_invalid_reciprocal_is_not_counted_as_matched(self):
        with self.state.db('ingredients') as db:
            db.execute("UPDATE relations SET detail_json='{}'")
        self.state.refresh_receipt()
        report = self.report()
        self.assertEqual(report['counts']['reciprocal_mismatches'], 1)

    def test_different_selected_recipe_version_is_explicit(self):
        with self.state.db('ingredients') as db:
            db.execute('DELETE FROM relations')
            db.execute('DELETE FROM records')
            self.state.insert_source(db, self.state.source_for['ingredients'], 'v2')
            self.state.insert_record(db, self.state.source_for['ingredients'], 'v2', self.state.payloads['ingredients'][0])
        self.state.receipt['domains']['ingredients']['sources'][0]['source_version'] = 'v2'
        self.state.reseal_counts('ingredients')
        edge = next(x for x in self.report()['relation_resolutions'] if x['join_contract_id'] == 'recipe_mentions')
        self.assertEqual(edge['disposition'], 'missing')
        self.assertEqual(edge['reason_code'], 'target_source_version_mismatch')

    def test_snapshot_id_changes_with_content_and_versions(self):
        before = self.report()['snapshot']['snapshot_id']
        self.state.receipt['report']['run_id'] = 'different-synthetic-run'
        self.state.refresh_receipt()
        self.assertNotEqual(before, self.report()['snapshot']['snapshot_id'])


if __name__ == '__main__':
    unittest.main()
