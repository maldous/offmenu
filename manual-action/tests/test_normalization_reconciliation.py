"""Generated fixtures only. No corpus, private DB, source files, or network."""
import copy
import json
import os
from pathlib import Path
import sqlite3
import sys
import tempfile
import unittest
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import normalization_reconciliation as reconciliation
from normalization_api import NormalizationError, Versions
from normalization_core import CompactNormalizationStore, canonical_json, digest, run_rules
from ingest_store import SCHEMA


class ReconciliationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.registry = copy.deepcopy(reconciliation.DEFAULT_REGISTRY)
        self.registry['namespaces']['fixture:food'] = {
            'record_types': ['barcode', 'ingredient', 'dietary_assertion'],
            'kind': 'food_identifier', 'exclusive': True,
            'provenance': ['generated fixture contract: no production mapping asserted'],
        }
        self.store = reconciliation.ReconciliationStore(self.root / 'output' / 'links.sqlite3', self.registry)
        self.addCleanup(self.store.close)

    def artifact(self, domain='ingredients', payload=None, *, source='fixture', version='v1', rid='one', rules=None):
        if payload is None: payload = {'name': 'Salt', 'language': 'en'}
        record = {'domain': domain, 'source_key': source, 'source_version': version, 'record_id': rid,
                  'content_sha256': digest(payload), 'payload': payload,
                  'provenance': {'license': 'fixture', 'provider': 'generated', 'custody': {'fixture': True}, 'rights_status': 'unverified'}}
        return run_rules(record, versions=rules)

    def identity(self, value='42', name='Salt', **kw):
        return {'name': name, 'language': 'en', 'identifiers': [{'namespace': 'fixture:food', 'value': value}], **kw}

    def source_cache(self, artifact):
        domain, ref = artifact['domain'], artifact['source']
        path = self.root / 'staging' / (domain + '.sqlite3')
        path.parent.mkdir(exist_ok=True)
        with sqlite3.connect(path) as db:
            db.executescript(SCHEMA)
            for key, value in {'binding': 'additive_staging_not_app_bound', 'schema_version': '1', 'domain': domain}.items():
                db.execute('INSERT OR REPLACE INTO ingest_meta VALUES(?,?)', (key, value))
            db.execute('INSERT OR IGNORE INTO sources VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)',
                (ref['source_key'], ref['source_version'], '/MUST-NOT-OPEN-RAW-SOURCE', 'json', 'generated', 'fixture', '{"fixture":true}', '{}', 'complete', 0, 0, 0, 1))
            db.execute('INSERT OR REPLACE INTO records VALUES(?,?,?,?,?,?,?)',
                (ref['source_key'], ref['source_version'], ref['record_id'], 1, ref['content_sha256'], canonical_json(artifact['source_original']), 1))
        with CompactNormalizationStore(self.root, domain) as cache:
            cache.db.execute('INSERT OR IGNORE INTO rules_cache VALUES(?,?,?,?)', cache.encode(artifact)); cache.db.commit()
        return path

    def count(self, table): return self.store.db.execute('SELECT COUNT(*) FROM ' + table).fetchone()[0]

    def test_all_public_domains_compact_source_bound_and_no_network(self):
        payloads = {
            'barcodes': {'barcode': '036000291452', 'name': 'Fixture', 'language': 'en'},
            'ingredients': self.identity(aliases=['Table salt']),
            'recipes': {'id': 'r', 'kind': 'recipe', 'title': 'Soup', 'language': 'en', 'ingredients': [{'id': 'i', 'source_name_text': 'Salt', 'raw_text': '2 g salt', 'quantity': '2', 'unit': 'g'}], 'steps': []},
            'dietary': {'language': 'en', 'nutrient_id': 'N1', 'name': 'Sodium', 'value': '5', 'unit': 'mg', 'basis': 'per_100g'},
            'suppliers': {'type': 'organization', 'name': 'Shop', 'language': 'en', 'entity_id': 's1', 'namespace': 'fixture:supplier'},
            'citations': {'title': 'Reference', 'language': 'en', 'url': 'HTTPS://EXAMPLE.ORG/doc?x=1'},
        }
        before = {}
        artifacts = []
        for domain, payload in payloads.items():
            payload['never_projected'] = 'RAW-PAYLOAD-SENTINEL'
            artifact = self.artifact(domain, payload)
            artifacts.append(artifact)
            path = self.source_cache(artifact)
            before[path] = path.read_bytes()
        with patch('socket.socket', side_effect=AssertionError('network forbidden')):
            for artifact in artifacts:
                result = reconciliation.ingest_cache_keys(self.root, artifact['domain'], [artifact['cache_key']], self.store)
                self.assertEqual(result['new'], 1)
        self.assertEqual(self.count('artifacts'), 6)
        self.assertEqual(before, {p: p.read_bytes() for p in before})
        dump = '\n'.join(self.store.db.iterdump())
        self.assertNotIn('RAW-PAYLOAD-SENTINEL', dump)
        self.assertNotIn('source_original', dump)
        self.assertNotIn('MUST-NOT-OPEN', dump)
        report = self.store.report()
        self.assertEqual((report['gold_status'], report['entity_merges']), ('blocked', 0))
        self.assertNotIn('Salt', json.dumps(report))
        self.assertGreater(self.count('measures'), 0)
        self.assertEqual(os.stat(self.store.path).st_mode & 0o777, 0o600)

    def test_exact_cross_domain_identifier_candidate_without_merge(self):
        items = [self.artifact('ingredients', self.identity()), self.artifact('barcodes', self.identity(barcode='036000291452')),
                 self.artifact('dietary', self.identity(nutrient_id='1', amount='1', unit='g', basis='per_100g'))]
        self.store.ingest_artifacts(items)
        rows = self.store.db.execute("SELECT node_id,COUNT(DISTINCT domain) FROM effective_memberships WHERE role='asserts_identifier' AND effective_state='source_asserted_candidate' GROUP BY node_id HAVING COUNT(DISTINCT domain)>1").fetchall()
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0][1], 3)
        self.assertEqual(self.store.report()['entity_merges'], 0)

    def test_malformed_barcode_is_unresolved_without_rolling_back_companion(self):
        good = self.artifact('barcodes', {'barcode': '036000291452'}, rid='good')
        bad = self.artifact('barcodes', {'barcode': 'bad'}, rid='bad')
        result = self.store.ingest_artifacts([good, bad])
        self.assertEqual(result['new'], 2)
        self.assertEqual(self.count('artifacts'), 2)
        self.assertEqual(self.store.db.execute("SELECT COUNT(*) FROM nodes WHERE namespace='gs1:gtin14'").fetchone()[0], 1)
        self.assertEqual(self.store.db.execute('SELECT code FROM issues WHERE cache_key=? AND code=?', (bad['cache_key'], 'barcode_identifier_unresolved')).fetchone(), ('barcode_identifier_unresolved',))

    def test_gtin_upc_and_ean_alias_same_key_but_syntax_only(self):
        self.store.ingest_artifacts([self.artifact('barcodes', {'barcode': value}, rid=str(i)) for i, value in enumerate(('036000291452', '0036000291452', '00036000291452'))])
        rows = self.store.db.execute("SELECT DISTINCT node_id,effective_state FROM effective_memberships WHERE role='asserts_identifier'").fetchall()
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0][1], 'syntax_only_identifier_candidate')

    def test_conflicting_identifier_values_held_no_alias_shortcut(self):
        payload = self.identity()
        payload['identifiers'].append({'namespace': 'fixture:food', 'value': '43'})
        self.store.ingest_artifacts([self.artifact(payload=payload)])
        self.assertEqual(set(r[0] for r in self.store.db.execute("SELECT effective_state FROM effective_memberships WHERE role='asserts_identifier'")), {'held_identifier_conflict'})
        self.assertEqual(self.store.db.execute('SELECT n.kind FROM aliases a JOIN nodes n USING(node_id) LIMIT 1').fetchone(), ('source_occurrence',))

    def test_namespace_type_conflict_and_unknown_namespace_isolation(self):
        self.store.ingest_artifacts([self.artifact('suppliers', self.identity(type='organization'))])
        self.assertEqual(self.store.db.execute("SELECT effective_state FROM effective_memberships WHERE role='asserts_identifier'").fetchone(), ('held_namespace_record_type_conflict',))
        payload = {'name': 'Same', 'language': 'en', 'identifiers': [{'namespace': 'generic', 'value': '42'}]}
        self.store.ingest_artifacts([self.artifact('ingredients', payload, source='a'), self.artifact('ingredients', payload, source='b'), self.artifact('barcodes', payload, source='a')])
        self.assertEqual(self.store.db.execute("SELECT COUNT(DISTINCT node_id) FROM nodes WHERE namespace='generic'").fetchone()[0], 3)

    def test_order_independent_node_and_edge_ids(self):
        items = [self.artifact(payload=self.identity(), rid='food'), self.artifact('recipes', {'id': 'r', 'kind': 'menu', 'title': 'Menu', 'relations': [{'kind': 'contains', 'target_domain': 'ingredients', 'target_id': 'food'}]})]
        self.store.ingest_artifacts(items)
        with reconciliation.ReconciliationStore(self.root / 'other' / 'links.sqlite3', self.registry) as other:
            other.ingest_artifacts(list(reversed(items)))
            for table in ('artifacts', 'nodes', 'memberships', 'terms', 'aliases', 'relations', 'issues'):
                left = sorted(self.store.db.execute('SELECT * FROM ' + table).fetchall())
                right = sorted(other.db.execute('SELECT * FROM ' + table).fetchall())
                self.assertEqual(left, right, table)

    def test_incremental_idempotence_and_version_changed_sources(self):
        first = self.artifact(payload=self.identity())
        self.store.ingest_artifacts([first])
        counts = self.store.report()['counts']
        self.assertEqual(self.store.ingest_artifacts([first])['reused'], 1)
        self.assertEqual(self.store.report()['counts'], counts)
        second = self.artifact(payload=self.identity(), version='v2')
        changed_rules = self.artifact(payload=self.identity(), rules=Versions(rule_version='fixture-rules-v2'))
        self.store.ingest_artifacts([second, changed_rules])
        self.assertEqual(self.count('artifacts'), 3)
        self.assertEqual(self.store.db.execute('SELECT COUNT(DISTINCT occurrence_id) FROM artifacts').fetchone()[0], 2)
        self.assertEqual(self.store.report()['source_slot_conflicts'], 0)
        self.assertEqual(self.store.db.execute("SELECT COUNT(DISTINCT node_id) FROM memberships WHERE role='asserts_identifier'").fetchone()[0], 1)

    def test_same_source_version_content_change_holds_prior_and_new(self):
        self.store.ingest_artifacts([self.artifact(payload=self.identity()), self.artifact(payload=self.identity(name='Different'))])
        self.assertEqual(self.store.report()['source_slot_conflicts'], 1)
        self.assertEqual(set(r[0] for r in self.store.db.execute('SELECT effective_state FROM effective_memberships')), {'held_source_content_conflict'})
        scope = self.store.db.execute('SELECT scope FROM terms LIMIT 1').fetchone()[0]
        self.assertEqual(self.store.resolve_term('Salt', scope=scope, language='en', role='ingredient')['status'], 'held_source_content_conflict')

    def test_alias_registry_exact_language_scope_units_and_ambiguity(self):
        self.store.ingest_artifacts([self.artifact(payload=self.identity(aliases=['Table salt'])), self.artifact(payload=self.identity(value='43'), rid='other')])
        scope = self.store.db.execute('SELECT scope FROM terms LIMIT 1').fetchone()[0]
        self.assertEqual(self.store.resolve_term('Salt', scope=scope, language='en', role='ingredient')['status'], 'held_ambiguous_alias')
        self.assertEqual(self.store.resolve_term('Table salt', scope=scope, language='en', role='ingredient')['status'], 'source_asserted_candidate')
        for kwargs in ({'text': 'salt'}, {'language': 'fr'}, {'scope': 'other'}, {'unit': 'g'}):
            args = {'text': 'Table salt', 'scope': scope, 'language': 'en', 'role': 'ingredient', **kwargs}
            self.assertEqual(self.store.resolve_term(**args)['status'], 'unresolved')

    def test_large_alias_group_truncates_and_checks_conflicts_beyond_prefix(self):
        self.store.ingest_artifacts([self.artifact(rid=str(i)) for i in range(40)])
        scope = self.store.db.execute('SELECT scope FROM terms LIMIT 1').fetchone()[0]
        result = self.store.resolve_term('Salt', scope=scope, language='en', role='ingredient', candidate_limit=2)
        self.assertEqual(result['status'], 'held_truncated_candidates')
        self.assertTrue(result['candidate_truncated'])
        self.assertEqual(len(result['candidate_node_ids']), 2)
        # Mutate the source slot of a node outside the returned prefix. The
        # bounded result must still notice its source-content conflict.
        rid = self.store.db.execute('SELECT a.record_id FROM aliases x JOIN artifacts a USING(cache_key) ORDER BY x.node_id DESC LIMIT 1').fetchone()[0]
        self.store.ingest_artifacts([self.artifact(rid=rid, payload={'name': 'Changed', 'language': 'en'})])
        result = self.store.resolve_term('Salt', scope=scope, language='en', role='ingredient', candidate_limit=2)
        self.assertEqual(result['status'], 'held_source_content_conflict')
        self.assertTrue(result['source_conflict'])
        self.assertTrue(result['candidate_truncated'])
        self.assertEqual(len(result['candidate_node_ids']), 2)

    def test_nutrient_terms_not_collapsed_across_units_or_basis(self):
        self.store.ingest_artifacts([self.artifact('dietary', {'name': 'N', 'language': 'en', 'nutrient_id': '1', 'value': '1', 'unit': unit, 'basis': basis}, rid=str(i)) for i, (unit, basis) in enumerate((('g', 'per_100g'), ('mL', 'per_100mL'), ('g', 'per_serving')))])
        self.assertEqual(set(self.store.db.execute("SELECT DISTINCT unit FROM terms WHERE role='nutrient'")), {('g',), ('mL',)})
        self.assertEqual(set(self.store.db.execute('SELECT DISTINCT basis FROM measures')), {('per_100g',), ('per_100mL',), ('per_serving',)})

    def test_relationship_targets_arrive_incrementally_conflicts_stay_held(self):
        menu = self.artifact('recipes', {'id': 'm', 'kind': 'menu', 'title': 'M', 'relations': [{'kind': 'contains', 'target_domain': 'ingredients', 'target_id': 'food'}]})
        self.store.ingest_artifacts([menu])
        self.assertEqual(set(r[0] for r in self.store.db.execute('SELECT effective_state FROM effective_relations')), {'unresolved_target_not_present'})
        self.store.ingest_artifacts([self.artifact(rid='food')])
        self.assertEqual(set(r[0] for r in self.store.db.execute('SELECT effective_state FROM effective_relations')), {'exact_source_reference_candidate'})
        self.store.ingest_artifacts([self.artifact(rid='food', payload={'name': 'Changed'})])
        self.assertEqual(set(r[0] for r in self.store.db.execute('SELECT effective_state FROM effective_relations')), {'held_target_content_conflict'})

    def test_private_domains_rejected_before_open_or_write(self):
        for domain in ('inventory', 'user_profiles', '../secrets'):
            with self.assertRaisesRegex(NormalizationError, 'public_domain_required'):
                reconciliation.ingest_cache_keys(self.root, domain, [], self.store)
            with self.assertRaisesRegex(NormalizationError, 'public_domain_required'):
                reconciliation.backfill_page(self.root, domain)
        private = self.artifact()
        private['domain'] = 'inventory'
        with self.assertRaisesRegex(NormalizationError, 'public_domain_required'):
            self.store.ingest_artifacts([private])
        self.assertEqual(self.count('artifacts'), 0)

    def test_forged_projection_and_stale_db_source_are_rejected(self):
        artifact = self.artifact()
        forged = copy.deepcopy(artifact)
        forged['normalized']['fields']['identity_claims'] = [{'namespace': 'fixture:food', 'value': 'forged'}]
        with self.assertRaisesRegex(NormalizationError, 'projection_mismatch'):
            self.store.ingest_artifacts([forged])
        path = self.source_cache(artifact)
        with sqlite3.connect(path) as db:
            payload = {'name': 'Changed'}
            db.execute('UPDATE records SET payload_json=?,content_sha256=?', (canonical_json(payload), digest(payload)))
        with self.assertRaisesRegex(NormalizationError, 'stale_database'):
            reconciliation.ingest_cache_keys(self.root, 'ingredients', [artifact['cache_key']], self.store)
        self.assertEqual(self.count('artifacts'), 0)

    def test_oversized_custody_matches_published_engine_admission(self):
        original = self.artifact()
        provenance = {**original['provenance'], 'custody': None}
        artifact = run_rules({**original['source'], 'payload': original['source_original'], 'provenance': provenance})
        path = self.source_cache(artifact)
        with sqlite3.connect(path) as db:
            db.execute('UPDATE sources SET custody_json=?', (json.dumps({'large': 'x' * 65536}),))
        before = path.read_bytes()
        result = reconciliation.ingest_cache_keys(self.root, 'ingredients', [artifact['cache_key']], self.store)
        self.assertEqual(result['new'], 1)
        self.assertEqual(path.read_bytes(), before)
        self.assertEqual(self.store.db.execute('SELECT provenance_sha256 FROM artifacts').fetchone(), (digest(provenance),))

    def test_corrupt_cache_atomic_failure_and_policy_pin(self):
        first, second = self.artifact(rid='a'), self.artifact(rid='b')
        self.source_cache(first); self.source_cache(second)
        cache = self.root / 'normalization-private' / 'compact-ingredients.sqlite3'
        with sqlite3.connect(cache) as db: db.execute('UPDATE rules_cache SET compact_sha256=? WHERE cache_key=?', ('0'*64, second['cache_key']))
        with self.assertRaisesRegex(NormalizationError, 'compact_cache_corrupt'):
            reconciliation.ingest_cache_keys(self.root, 'ingredients', [first['cache_key'], second['cache_key']], self.store)
        self.assertEqual(self.count('artifacts'), 0)
        changed = copy.deepcopy(self.registry); changed['version'] = 'v2'
        with self.assertRaisesRegex(NormalizationError, 'policy_or_binding_mismatch'):
            reconciliation.ReconciliationStore(self.store.path, changed)

    def test_transaction_rollback_keeps_every_table_empty(self):
        self.store.db.execute("CREATE TRIGGER stop_membership BEFORE INSERT ON aliases BEGIN SELECT RAISE(ABORT,'fixture'); END")
        self.store.db.commit()
        with self.assertRaises(sqlite3.IntegrityError): self.store.ingest_artifacts([self.artifact()])
        for table in ('artifacts', 'nodes', 'memberships', 'terms', 'aliases', 'relations', 'issues'):
            self.assertEqual(self.count(table), 0)
        self.store.db.execute('DROP TRIGGER stop_membership'); self.store.db.commit()
        self.assertEqual(self.store.ingest_artifacts([self.artifact()])['new'], 1)

    def test_keyset_backfill_and_new_keys_restart_no_rowid_dependency(self):
        items = [self.artifact(rid=str(i)) for i in range(5)]
        for item in items: self.source_cache(item)
        keys, cursor = [], None
        while True:
            page = reconciliation.backfill_page(self.root, 'ingredients', after=cursor, limit=2)
            if not page: break
            keys.extend(page); reconciliation.ingest_cache_keys(self.root, 'ingredients', page, self.store); cursor = page[-1]
        self.assertEqual(keys, sorted(item['cache_key'] for item in items))
        self.assertEqual(self.count('artifacts'), 5)
        for item in items:
            self.assertEqual(reconciliation.ingest_cache_keys(self.root, 'ingredients', [item['cache_key']], self.store)['reused'], 1)
        with sqlite3.connect(self.root / 'normalization-private' / 'compact-ingredients.sqlite3') as db: db.execute('VACUUM')
        self.assertEqual(reconciliation.backfill_page(self.root, 'ingredients'), keys)

    def test_symlink_and_batch_boundaries_rejected(self):
        link = self.root / 'link'; link.symlink_to(self.store.path)
        with self.assertRaisesRegex(NormalizationError, 'symlink'):
            reconciliation.ReconciliationStore(link, self.registry)
        with self.assertRaisesRegex(NormalizationError, 'batch_cap'):
            self.store.ingest_artifacts([{}] * 129)
        with patch.object(reconciliation, 'MAX_BATCH_BYTES', 1):
            with self.assertRaisesRegex(NormalizationError, 'batch_bytes_cap'):
                self.store.ingest_artifacts([self.artifact()])
        self.assertEqual(self.count('artifacts'), 0)

    def test_forged_gtin_namespace_claim_cannot_bypass_syntax(self):
        artifact = self.artifact('barcodes', {'identifiers': [{'namespace': 'gs1:gtin14', 'value': 'not-a-gtin'}]})
        self.store.ingest_artifacts([artifact])
        state = self.store.db.execute("SELECT effective_state FROM effective_memberships WHERE role='asserts_identifier'").fetchone()[0]
        self.assertEqual(state, 'held_identifier_lexeme_invalid')

    def test_pending_key_receipts_and_reserve_stop_without_writes(self):
        artifact = self.artifact()
        self.assertEqual(self.store.pending_keys([artifact['cache_key']]), [artifact['cache_key']])
        self.store.ingest_artifacts([artifact])
        self.assertEqual(self.store.pending_keys([artifact['cache_key']]), [])
        before = self.store.report()['counts']
        with patch.object(reconciliation.shutil, 'disk_usage', return_value=type('Usage', (), {'free': 1})()):
            with self.assertRaisesRegex(NormalizationError, 'disk_reserve'):
                self.store.ingest_artifacts([self.artifact(rid='new')])
        self.assertEqual(self.store.report()['counts'], before)

    def test_relationship_and_term_lookups_use_slot_index_not_global_conflict_scan(self):
        self.store.ingest_artifacts([self.artifact()])
        plan = ' '.join(str(row) for row in self.store.db.execute('EXPLAIN QUERY PLAN SELECT * FROM effective_memberships WHERE cache_key=?', ('x',)))
        self.assertIn('artifacts_slot', plan)
        self.assertNotIn('MATERIALIZE source_slot_conflicts', plan)

    def test_unresolved_names_do_not_fuzzy_merge_or_promote(self):
        self.store.ingest_artifacts([self.artifact(payload={'name': name, 'language': language}, rid=str(i)) for i, (name, language) in enumerate((('Salt', 'en'), ('salt', 'en'), ('Salt', 'fr'), ('Salt', None)))])
        self.assertEqual(self.store.db.execute('SELECT COUNT(DISTINCT node_id) FROM aliases').fetchone()[0], 4)
        self.assertIn('term_language_unknown', self.store.report()['unresolved_reasons'])
        self.assertEqual(self.store.report()['review_status'], 'pendingreview')


if __name__ == '__main__': unittest.main()
