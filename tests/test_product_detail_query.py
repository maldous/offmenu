"""Generated SQL fixtures only; no writer/scanner/mixed-module dependency."""
import copy
from dataclasses import replace
import hashlib
import json
from pathlib import Path
import sqlite3
import subprocess
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from offmenu.refresh import product_detail_query as query, acceptance, core
from offmenu.refresh.core import RefreshError

DETAIL_SCHEMA = """-- SOURCE CONTRACT ONLY, not executed.5tables/1view;26owns implementation.
CREATE TABLE retained_reference_record(
 reference_record_id TEXT PRIMARY KEY NOT NULL,
 source_id TEXT NOT NULL, release_id TEXT NOT NULL,
 asset_id TEXT NOT NULL, asset_sha256 TEXT NOT NULL,
 source_ordinal INTEGER NOT NULL CHECK(source_ordinal>=1),
 native_record_id TEXT, source_pointer TEXT NOT NULL,
 original_language TEXT NOT NULL, source_payload_json TEXT NOT NULL,
 parsed_record_sha256 TEXT NOT NULL,
 citation_id TEXT, citation_binding_status TEXT NOT NULL,
 parse_engine_id TEXT NOT NULL, parse_engine_version TEXT NOT NULL,
 processing_status TEXT NOT NULL,
 UNIQUE(asset_id,asset_sha256,source_ordinal)
);
-- NEW separate private product-detail generation only. Reference-record table reused exactly.
-- No validated identifier DB mutation, scanner11986 change or source body access by13.
CREATE TABLE product_detail_generation(
 generation_id TEXT PRIMARY KEY NOT NULL,
 input_manifest_sha256 TEXT NOT NULL,
 schema_version TEXT NOT NULL,
 projection_version TEXT NOT NULL,
 operation_selection_sha256 TEXT NOT NULL,
 state TEXT NOT NULL CHECK(state IN ('loading','incomplete','completed','failed')),
 coverage_scope_json TEXT NOT NULL,
 expected_asset_count INTEGER CHECK(expected_asset_count>=0),
 processed_asset_count INTEGER CHECK(processed_asset_count>=0),
 product_records INTEGER CHECK(product_records>=0),
 profile_records INTEGER CHECK(profile_records>=0),
 exceptions_json TEXT NOT NULL,
 created_at TEXT NOT NULL, modified_at TEXT, removed_at TEXT, created_by TEXT,
 owner_actor_reference TEXT, access_policy_reference TEXT
);
CREATE TABLE product_detail_projection(
 reference_record_id TEXT PRIMARY KEY NOT NULL REFERENCES retained_reference_record(reference_record_id),
 generation_id TEXT NOT NULL REFERENCES product_detail_generation(generation_id),
 record_kind TEXT NOT NULL CHECK(record_kind IN ('product','nutrientProfile')),
 paired_profile_reference TEXT REFERENCES retained_reference_record(reference_record_id),
 source_binding_json TEXT NOT NULL,
 fields_json TEXT,
 projection_limitations_json TEXT NOT NULL,
 canonical_ingredient_id TEXT,
 semantic_mapping_status TEXT NOT NULL,
 record_disposition TEXT NOT NULL
);
CREATE TABLE product_detail_identifier(
 reference_record_id TEXT NOT NULL REFERENCES retained_reference_record(reference_record_id),
 identifier_ordinal INTEGER NOT NULL CHECK(identifier_ordinal>=1),
 namespace TEXT COLLATE BINARY,
 lexical_value TEXT COLLATE BINARY,
 disposition TEXT NOT NULL,
 source_pointer TEXT NOT NULL,
 PRIMARY KEY(reference_record_id,identifier_ordinal)
);
CREATE TABLE product_detail_observation_bridge(
 bridge_id TEXT PRIMARY KEY NOT NULL,
 identifier_database_sha256 TEXT NOT NULL,
 identifier_run_id TEXT NOT NULL,
 identifier_input_id TEXT NOT NULL,
 identifier_record_ordinal INTEGER NOT NULL CHECK(identifier_record_ordinal>=1),
 identifier_assertion_id INTEGER NOT NULL CHECK(identifier_assertion_id>=1),
 reference_record_id TEXT REFERENCES retained_reference_record(reference_record_id),
 bridge_state TEXT NOT NULL CHECK(bridge_state IN ('matched','not-loaded','ambiguous','restricted')),
 exact_link_evidence_json TEXT NOT NULL,
 CHECK(bridge_state<>'matched' OR reference_record_id IS NOT NULL)
);
CREATE INDEX product_detail_key_lookup ON product_detail_identifier(namespace,lexical_value,reference_record_id);
CREATE INDEX product_detail_generation_records ON product_detail_projection(generation_id,record_kind,reference_record_id);
CREATE INDEX product_detail_exact_observation ON product_detail_observation_bridge(identifier_database_sha256,identifier_run_id,identifier_input_id,identifier_record_ordinal,identifier_assertion_id,bridge_id);
CREATE INDEX product_detail_source ON retained_reference_record(source_id,release_id,native_record_id,source_ordinal);
CREATE VIEW v_source_product_details AS
SELECT p.generation_id,r.reference_record_id,r.source_id,r.release_id,r.native_record_id,
 r.asset_id,r.asset_sha256,r.source_ordinal,r.source_pointer,r.parsed_record_sha256,
 r.original_language,r.citation_id,r.citation_binding_status,
 p.record_kind,p.paired_profile_reference,p.source_binding_json,p.fields_json,
 p.projection_limitations_json,p.canonical_ingredient_id,p.semantic_mapping_status,p.record_disposition
FROM retained_reference_record r JOIN product_detail_projection p USING(reference_record_id);
"""

# Persisted identifier-view fixture: same selected columns and PK joins as the
# accepted inspection contract, without importing its loader/old display module.
IDENTIFIER_SCHEMA = """
CREATE TABLE fetch_asset(asset_id TEXT PRIMARY KEY);
CREATE TABLE identifier_load(run_id TEXT PRIMARY KEY,state TEXT NOT NULL);
CREATE TABLE identifier_input(run_id TEXT,input_id TEXT,source_id TEXT,release_id TEXT,
 artifact_sha256 TEXT,asset_id TEXT,PRIMARY KEY(run_id,input_id));
CREATE TABLE identifier_source_record(run_id TEXT,input_id TEXT,record_ordinal INTEGER,
 source_record_id TEXT,native_record_id TEXT,PRIMARY KEY(run_id,input_id,record_ordinal));
CREATE TABLE identifier_assertion(assertion_id INTEGER PRIMARY KEY,run_id TEXT,input_id TEXT,
 record_ordinal INTEGER,namespace TEXT COLLATE BINARY,lexical_value TEXT COLLATE BINARY,disposition TEXT);
CREATE VIEW barcode_identifier_inspection AS
SELECT a.run_id,a.assertion_id,a.disposition,a.input_id,a.record_ordinal,a.namespace,a.lexical_value,
 i.source_id,i.release_id,i.artifact_sha256,r.native_record_id,r.source_record_id,l.state AS load_state
FROM identifier_assertion a JOIN identifier_source_record r
 ON r.run_id=a.run_id AND r.input_id=a.input_id AND r.record_ordinal=a.record_ordinal
JOIN identifier_input i ON i.run_id=a.run_id AND i.input_id=a.input_id
JOIN identifier_load l ON l.run_id=a.run_id JOIN fetch_asset fa ON fa.asset_id=i.asset_id;
"""


class ProductDetailQueryTests(unittest.TestCase):
    def test_malformed_completed_asset_counts_fail_typed_before_data_queries_and_clear_handlers(self):
        cases = ((None, None), (None, 1), (1, None), ('bad', 'bad'), (1.5, 1.5),
                 (b'bad', b'bad'), (-1, -1), (-1, 1), (1, -1), (2, 1))
        for expected, processed in cases:
            with self.subTest(expected=repr(expected), processed=repr(processed)):
                f = self.fixture()
                negative = any(type(n) is int and n < 0 for n in (expected, processed))
                # Simulate corrupted/legacy values only in the generated store;
                # the actual thirteen-owner schema and its CHECKs are unchanged.
                if negative: self.edit(f.db, 'PRAGMA ignore_check_constraints=ON')
                self.edit(f.db, 'UPDATE product_detail_generation SET expected_asset_count=?,processed_asset_count=?', (expected, processed))
                if negative: self.edit(f.db, 'PRAGMA ignore_check_constraints=OFF')
                detail_sql = []; index_sql = []
                f.db.set_trace_callback(detail_sql.append); f.index.set_trace_callback(index_sql.append)
                with patch.object(query.time, 'monotonic', return_value=100.0) as clock:
                    with self.assertRaisesRegex(RefreshError, 'query-unselected-generation'):
                        self.call(f)
                    self.assertEqual(index_sql, [])
                    self.assertFalse(any('retained_reference_record' in sql or 'product_detail_identifier' in sql for sql in detail_sql))
                    f.db.set_trace_callback(None); f.index.set_trace_callback(None)
                    clock.return_value = 1000.0
                    self.assert_handlers_cleared(f)

    def test_boolean_generation_counts_are_not_integer_accounting(self):
        f = self.fixture()
        def boolean_counts(cursor, row):
            names = [c[0] for c in cursor.description]
            if names[4:6] == ['expected_asset_count', 'processed_asset_count']:
                values = list(row); values[4:6] = [True, True]; return tuple(values)
            return row
        # A caller row adapter must not turn bools into valid count evidence.
        f.db.row_factory = boolean_counts
        with patch.object(query.time, 'monotonic', return_value=100.0) as clock:
            with self.assertRaisesRegex(RefreshError, 'query-unselected-generation'): self.call(f)
            clock.return_value = 1000.0; self.assert_handlers_cleared(f)

    def test_valid_completed_integer_counts_including_empty_generation(self):
        for count in (0, 1, 2):
            with self.subTest(count=count):
                f = self.fixture()
                if count == 0:
                    for statement in ('DELETE FROM product_detail_identifier', 'DELETE FROM product_detail_projection',
                                      'DELETE FROM retained_reference_record',
                                      'UPDATE product_detail_generation SET expected_asset_count=0,processed_asset_count=0,product_records=0,profile_records=0'):
                        self.edit(f.db, statement)
                if count == 2: self.add_projection(f, 'usda-reviewed-lookup-products-json', False, 'two')
                result = self.call(f)
                self.assertEqual(result['coverage']['expectedAssets'], count)
                self.assertEqual(result['coverage']['processedAssets'], count)
                self.assertIs(type(result['coverage']['expectedAssets']), int)
                self.assertIs(type(result['coverage']['processedAssets']), int)
                self.assertEqual(len(result['sourceProducts']), count)

    def setUp(self):
        self.assertEqual(hashlib.sha256(DETAIL_SCHEMA.encode()).hexdigest(),
            'f85e1696fa46d3c1b268d4969fa0569534ccaa8ade209c1c523c09bbd0046632')

    def fixture(self, representation='usda-native-jsonl', profile=True, metadata=''):
        db = sqlite3.connect(':memory:'); index = sqlite3.connect(':memory:')
        self.addCleanup(db.close); self.addCleanup(index.close)
        db.execute('PRAGMA foreign_keys=ON'); db.executescript(DETAIL_SCHEMA); index.executescript(IDENTIFIER_SCHEMA)
        source = 'off' if representation.startswith('off-') else 'usda-files'
        ordinal = 7 if source == 'off' else 1
        native = 'off:sourceOccurrence:'+'d'*64+':7' if source == 'off' else 'usda-files:product:fixture-fdc'
        source_record = '7' if source == 'off' else 'fixture-fdc'
        obs = {'run_id': 'fixture-run', 'assertion_id': 11, 'disposition': 'source-asserted',
            'input_id': 'fixture-input', 'record_ordinal': ordinal, 'namespace': 'barcode', 'lexical_value': '00012345',
            'source_id': source, 'release_id': 'fixture-r1', 'artifact_sha256': 'f'*64,
            'native_record_id': native, 'source_record_id': source_record}
        other = dict(obs, assertion_id=12, record_ordinal=ordinal+2, lexical_value='99999',
            native_record_id=native+'-other', source_record_id=source_record+'-other')
        index.execute('INSERT INTO fetch_asset VALUES(?)', ('fixture-identifier-asset',))
        index.execute('INSERT INTO identifier_load VALUES(?,?)', ('fixture-run', 'completed'))
        index.execute('INSERT INTO identifier_input VALUES(?,?,?,?,?,?)',
            ('fixture-run', 'fixture-input', source, 'fixture-r1', 'f'*64, 'fixture-identifier-asset'))
        for row in (obs, other):
            index.execute('INSERT INTO identifier_source_record VALUES(?,?,?,?,?)',
                (row['run_id'], row['input_id'], row['record_ordinal'], row['source_record_id'], row['native_record_id']))
            index.execute('INSERT INTO identifier_assertion VALUES(?,?,?,?,?,?,?)',
                (row['assertion_id'], row['run_id'], row['input_id'], row['record_ordinal'], row['namespace'], row['lexical_value'], row['disposition']))
        coverage = {'identifierDatabaseSha256': 'c'*64, 'scope': 'generated partial source coverage',
                    'assets': [], 'metadataNote': metadata}
        db.execute('INSERT INTO product_detail_generation(generation_id,input_manifest_sha256,schema_version,projection_version,operation_selection_sha256,state,coverage_scope_json,expected_asset_count,processed_asset_count,product_records,profile_records,exceptions_json,created_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)',
            ('fixture-gen', 'a'*64, 'fixture-schema', 'source-native-full-payload/1', 'b'*64, 'completed',
             core.canonical(coverage).decode(), 0, 0, 0, 0, '[]', 'fixture'))
        data = {'name': 'Fixture 豆', 'identifiers': [{'system': 'barcode', 'value': '00012345'}],
            'brand': None, 'ingredientsText': '  milk, 豆  ', 'nutritionId': source+':nutrientProfile:fixture-fdc'}
        if source == 'off':
            data.update(names={'de': 'Fixture 豆'}, pack={'value': 1.5, 'unit': 'g'}, categories=[], allergens=[],
                traces=[], labels=[], origins=[], manufacturingPlaces=[], rawNutriments={}, nutritionSourceBasis=None)
        else:
            data.update(dataType='fixture', marketCountry=None, serving={'amount': 1.5, 'unit': 'g', 'label': '1,50 source serving'})
        product = {'schemaVersion': '1.0', 'kind': 'product', 'id': source+':product:fixture-fdc',
            'countries': ['US'] if source == 'usda-files' else ['DE'], 'provenance': {
                'sourceId': source, 'releaseId': 'fixture-r1', 'recordId': source_record, 'fetchedAt': None}, 'data': data}
        nutrient = copy.deepcopy(product); nutrient['kind'] = 'nutrientProfile'; nutrient['id'] = data['nutritionId']
        nutrient['data'] = {'basis': {'amount': 100, 'unit': 'g'},
            'nutrients': {'sodium': {'value': 0.1, 'sourceAmount': '0.10', 'sourceUnit': 'mg'}}}
        f = SimpleNamespace(db=db, index=index, obs=obs, other=other, product=product, nutrient=nutrient,
            selection=query.ProductDetailQuerySelection('fixture-gen', 'a'*64, 'b'*64, 'c'*64),
            evidence=query.CurrentIdentifierEvidence(index, 'fixture-run', 'c'*64))
        self.add_projection(f, representation, profile, 'one')
        index.commit(); index.execute('PRAGMA query_only=ON')
        return f

    def add_projection(self, f, representation, profile, suffix):
        db = f.db; db.execute('PRAGMA query_only=OFF')
        records = [copy.deepcopy(f.product)] + ([copy.deepcopy(f.nutrient)] if profile else [])
        refs = [suffix+'-product'] + ([suffix+'-profile'] if profile else [])
        pointers = (['jsonl:line:1/0', 'jsonl:line:2/0'] if representation == 'usda-native-jsonl' else
            ['jsonl:packet:1/0', 'jsonl:packet:1/1'] if representation == 'off-legacy-paired-gzip' else
            ['/records/0', '/records/1'] if representation == 'off-cached-qualified-pair' else ['/lookup/matches/0/record'])[:len(records)]
        binding = {'sourceId': f.obs['source_id'], 'releaseId': f.obs['release_id'],
            'identifierInputId': f.obs['input_id'], 'identifierAssetSha256': f.obs['artifact_sha256'],
            'identifierRecordOrdinal': f.obs['record_ordinal'], 'identifierNativeRecordId': f.obs['native_record_id'],
            'identifierSourceRecordId': f.obs['source_record_id'], 'inputAssetSha256': 'e'*64,
            'originalSha256': 'd'*64, 'recordSha256': hashlib.sha256(acceptance.canonical(records)).hexdigest(),
            'recordPointers': pointers, 'representation': representation, 'projectionVersion': 'fixture/1',
            'rightsReceiptSha256': 'd'*64, 'custodyReceiptSha256': 'e'*64,
            'operationReceiptSha256': 'b'*64, 'citationId': None}
        for n, (row, ref, pointer) in enumerate(zip(records, refs, pointers), 1):
            db.execute('INSERT INTO retained_reference_record VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)',
                (ref, f.obs['source_id'], f.obs['release_id'], 'asset-'+suffix, 'e'*64, n, row['id'], pointer,
                 'und', core.canonical(row).decode(), hashlib.sha256(core.canonical(row)).hexdigest(),
                 None, 'generated-only', 'fixture', 'fixture/1', 'processed'))
        for n in reversed(range(len(records))):
            db.execute('INSERT INTO product_detail_projection VALUES(?,?,?,?,?,?,?,?,?,?)',
                (refs[n], 'fixture-gen', records[n]['kind'], refs[1] if n == 0 and profile else None,
                 core.canonical(dict(binding, recordPointer=pointers[n])).decode(), None, '[]', None, 'pending', 'source-assertion'))
        db.execute('INSERT INTO product_detail_identifier VALUES(?,?,?,?,?,?)',
            (refs[0], 1, 'barcode', '00012345', 'source-asserted', '/data/identifiers/0'))
        db.execute('UPDATE product_detail_generation SET expected_asset_count=expected_asset_count+1,processed_asset_count=processed_asset_count+1,product_records=product_records+1,profile_records=profile_records+?', (int(profile),))
        db.commit(); db.execute('PRAGMA query_only=ON')

    def edit(self, db, statement, parameters=()):
        # Counterfactual changes are confined to generated fixture connections.
        db.execute('PRAGMA query_only=OFF'); db.execute(statement, parameters); db.commit(); db.execute('PRAGMA query_only=ON')

    def call(self, f, observations=None, **kwargs):
        args = {'selection': f.selection, 'identifier_evidence': f.evidence}; args.update(kwargs)
        return query.read_product_details(f.db, [f.obs] if observations is None else observations, **args)

    def assert_handlers_cleared(self, f):
        for db in (f.db, f.index):
            self.assertEqual(db.execute('WITH RECURSIVE n(x) AS (VALUES(1) UNION ALL SELECT x+1 FROM n WHERE x<2000) SELECT sum(x) FROM n').fetchone()[0], 2001000)

    def test_clean_namespace_and_distinct_canonical_aliases(self):
        code = """import sys
from offmenu.refresh import product_detail_query as q,acceptance,core
assert q.readers is acceptance and q.readers.canonical is acceptance.canonical
assert q.canonical is core.canonical
assert q.readers.canonical([]) == b'[]' and q.canonical([]) == b'[]\\n'
for name in ('product_detail_import','product_detail_import_readers','product_detail_store','native_barcode_lookup','product_label_sections','identifier_database'):
    assert 'offmenu.refresh.'+name not in sys.modules
for name in ('DDL','VERSION','ingest_product_details','scan_cached_product_detail_asset'):
    assert not hasattr(q,name)
assert q.CurrentIdentifierEvidence.__module__ == 'offmenu.refresh.product_detail_query'
"""
        subprocess.run([sys.executable, '-c', code], cwd=Path(__file__).resolve().parents[1], check=True)
        f = self.fixture(); result = self.call(f); item = result['sourceProducts'][0]
        self.assertEqual(item['sourceBinding']['recordSha256'], hashlib.sha256(acceptance.canonical(item['records'])).hexdigest())
        self.assertNotEqual(item['sourceBinding']['recordSha256'], hashlib.sha256(core.canonical(item['records'])).hexdigest())

    def test_readonly_exact_assertion_source_payloads_and_resolvable_field_pointers(self):
        f = self.fixture(); before = (f.db.total_changes, f.index.total_changes)
        result = self.call(f); item = result['sourceProducts'][0]
        self.assertEqual(result['productDetailAvailability'][0]['state'], 'loaded')
        self.assertEqual(item['records'], [f.product, f.nutrient])
        self.assertEqual(item['exactObservationBridge']['assertionEvidence']['assertion_id'], 11)
        self.assertEqual(item['sourceBinding']['recordPointers'], ['jsonl:line:1/0', 'jsonl:line:2/0'])
        for field in item['fields'].values():
            if field['fieldPointer'] is None: continue
            value = item['records']
            for bit in field['fieldPointer'].lstrip('/').split('/'):
                value = value[int(bit)] if isinstance(value, list) else value[bit]
            self.assertEqual(value, field['value'])
        self.assertIsNone(item['canonicalIngredient']['conceptId']); self.assertFalse(result['accepted'])
        self.assertEqual((f.db.total_changes, f.index.total_changes), before)
        for db in (f.db, f.index):
            self.assertEqual(db.execute('PRAGMA query_only').fetchone()[0], 1)
            with self.assertRaises(sqlite3.OperationalError): db.execute('CREATE TABLE forbidden(x)')

    def test_every_persisted_assertion_field_is_bound_without_fallback(self):
        f = self.fixture()
        for name in query.CURRENT_OBSERVATION_COLUMNS:
            changed = dict(f.obs)
            changed[name] = 999 if isinstance(changed[name], int) else '9'*64 if name == 'artifact_sha256' else 'wrong'
            with self.subTest(field=name):
                result = self.call(f, [changed])
                self.assertEqual(result['sourceProducts'], [])
                self.assertEqual(result['productDetailAvailability'][0]['reasonCode'], 'no-current-identifier-assertion')

    def test_independent_context_disposition_load_and_generation_negatives(self):
        f = self.fixture()
        for context in (None, SimpleNamespace(db=f.index, run_id='fixture-run', database_sha256='c'*64),
                        replace(f.evidence, database_sha256='9'*64)):
            with self.subTest(context=type(context).__name__), self.assertRaisesRegex(RefreshError, 'identifier-evidence'):
                self.call(f, identifier_evidence=context)
        with self.assertRaisesRegex(RefreshError, 'selection-or-bound'):
            self.call(f, selection=SimpleNamespace(**vars(f.selection)))
        with self.assertRaisesRegex(RefreshError, 'unselected-generation'):
            self.call(f, selection=replace(f.selection, input_manifest_sha256='9'*64))
        self.edit(f.index, "UPDATE identifier_assertion SET disposition='invalid' WHERE assertion_id=11")
        self.assertEqual(self.call(f)['sourceProducts'], [])
        self.edit(f.index, "UPDATE identifier_assertion SET disposition='source-asserted' WHERE assertion_id=11")
        self.edit(f.index, "UPDATE identifier_load SET state='incomplete'")
        self.assertEqual(self.call(f)['sourceProducts'], [])
        self.edit(f.index, "UPDATE identifier_load SET state='completed-with-exceptions'")
        self.assertEqual(self.call(f)['productDetailAvailability'][0]['state'], 'loaded')
        self.assertEqual(self.call(f, identifier_evidence=replace(f.evidence, run_id='other-run'))['sourceProducts'], [])

    def test_capabilities_missing_null_empty_and_profile_availability(self):
        for representation in ('usda-native-jsonl', 'usda-reviewed-lookup-products-json', 'off-legacy-paired-gzip', 'off-cached-qualified-pair'):
            with self.subTest(representation=representation):
                f = self.fixture(representation, profile=not representation.startswith('usda-reviewed'))
                fields = self.call(f)['sourceProducts'][0]['fields']
                self.assertEqual(fields['brand']['state'], 'null')
                unsupported = 'packageQuantity' if representation.startswith('usda-') else 'servingQuantity'
                self.assertEqual(fields[unsupported]['state'], 'not-loaded'); self.assertIsNone(fields[unsupported]['evidenceSha256'])
                self.assertEqual(fields['imageUrlReferences']['state'], 'not-loaded')
                if representation == 'usda-reviewed-lookup-products-json': self.assertEqual(fields['nutrientProfile']['state'], 'not-loaded')
                product = copy.deepcopy(f.product)
                product['data'].pop('ingredientsText'); missing = query._fields([product], representation)['ingredientDeclaration']
                self.assertEqual(missing['state'], 'missing'); self.assertIsNone(missing['fieldPointer'])
                self.assertIsNotNone(missing['evidenceSha256']); self.assertEqual(missing['sourceFieldState'], 'unknown')
                for value, state in ((None, 'null'), ('', 'present'), ('  source 豆  ', 'present')):
                    product['data']['ingredientsText'] = value
                    field = query._fields([product], representation)['ingredientDeclaration']
                    self.assertEqual(field['state'], state); self.assertEqual(field['value'], value)

    def test_variants_are_ambiguous_and_candidate_limits_are_errors(self):
        f = self.fixture(); self.add_projection(f, 'usda-reviewed-lookup-products-json', False, 'two')
        result = self.call(f, max_candidates=2)
        self.assertEqual(len(result['sourceProducts']), 2)
        self.assertEqual(result['productDetailAvailability'][0]['state'], 'ambiguous')
        self.assertEqual({x['sourceBinding']['representation'] for x in result['sourceProducts']}, {'usda-native-jsonl', 'usda-reviewed-lookup-products-json'})
        with self.assertRaisesRegex(RefreshError, 'candidate-bound'): self.call(f, max_candidates=1)
        self.assert_handlers_cleared(f)

    def test_assertion_and_detail_key_plans_use_search_without_scan(self):
        f = self.fixture()
        plans = [f.index.execute('EXPLAIN QUERY PLAN '+query.CURRENT_OBSERVATION_SQL, (11, 'fixture-run')).fetchall(),
            f.db.execute('EXPLAIN QUERY PLAN SELECT i.reference_record_id FROM product_detail_identifier i INDEXED BY product_detail_key_lookup CROSS JOIN product_detail_projection p ON p.reference_record_id=i.reference_record_id WHERE i.namespace=? AND i.lexical_value=? AND p.generation_id=?', ('barcode', '00012345', 'fixture-gen')).fetchall()]
        self.assertTrue(any('SEARCH a USING INTEGER PRIMARY KEY' in p[3] for p in plans[0]), plans)
        self.assertTrue(any('SEARCH i USING' in p[3] and 'product_detail_key_lookup' in p[3] for p in plans[1]), plans)
        self.assertFalse(any('SCAN ' in row[3] for plan in plans for row in plan), plans)

    def test_complete_response_exact_cap_and_one_byte_oversize_including_no_match_metadata(self):
        for mode in ('match', 'no-match', 'no-observations'):
            with self.subTest(mode=mode):
                f = self.fixture(metadata='metadata 豆 '*150)
                observations = [f.obs] if mode == 'match' else [f.other] if mode == 'no-match' else []
                result = self.call(f, observations); exact = len(core.canonical(result))
                self.assertEqual(self.call(f, observations, max_result_bytes=exact), result)
                with self.assertRaisesRegex(RefreshError, 'query-result-bound'):
                    self.call(f, observations, max_result_bytes=exact-1)
                if mode != 'match': self.assertEqual(result['sourceProducts'], [])
                self.assert_handlers_cleared(f)

    def test_payload_oversize_is_not_truncated_or_silently_empty(self):
        f = self.fixture(); changed = copy.deepcopy(f.product); changed['data']['ingredientsText'] = 'x'*262144
        self.edit(f.db, 'UPDATE retained_reference_record SET source_payload_json=? WHERE reference_record_id=?',
            (core.canonical(changed).decode(), 'one-product'))
        with self.assertRaisesRegex(RefreshError, 'query-result-bound'): self.call(f)
        self.assert_handlers_cleared(f)

    def test_hard_complete_response_cap_includes_match_no_match_and_empty_metadata(self):
        for mode in ('match', 'no-match', 'no-observations'):
            with self.subTest(mode=mode):
                f = self.fixture()
                observations = [f.obs] if mode == 'match' else [f.other] if mode == 'no-match' else []
                base = len(core.canonical(self.call(f, observations)))
                coverage = json.loads(f.db.execute('SELECT coverage_scope_json FROM product_detail_generation').fetchone()[0])
                coverage['metadataNote'] = 'm'*(262144-base)
                self.edit(f.db, 'UPDATE product_detail_generation SET coverage_scope_json=?', (core.canonical(coverage).decode(),))
                result = self.call(f, observations)
                self.assertEqual(len(core.canonical(result)), 262144)
                coverage['metadataNote'] += 'm'
                self.edit(f.db, 'UPDATE product_detail_generation SET coverage_scope_json=?', (core.canonical(coverage).decode(),))
                with self.assertRaisesRegex(RefreshError, 'query-result-bound'): self.call(f, observations)
                self.assert_handlers_cleared(f)
        with self.assertRaisesRegex(RefreshError, 'selection-or-bound'):
            self.call(f, [], max_result_bytes=262145)

    def test_source_coordinates_and_pair_digest_cannot_be_substituted(self):
        f = self.fixture(); encoded = f.db.execute("SELECT source_binding_json FROM product_detail_projection WHERE reference_record_id='one-product'").fetchone()[0]
        binding = json.loads(encoded); wrong = dict(binding, identifierRecordOrdinal=999)
        self.edit(f.db, "UPDATE product_detail_projection SET source_binding_json=? WHERE reference_record_id='one-product'", (core.canonical(wrong).decode(),))
        result = self.call(f); self.assertEqual(result['sourceProducts'], [])
        self.assertEqual(result['productDetailAvailability'][0]['reasonCode'], 'no-exact-source-observation-bridge')
        wrong = dict(binding, recordSha256='9'*64)
        self.edit(f.db, "UPDATE product_detail_projection SET source_binding_json=? WHERE reference_record_id='one-product'", (core.canonical(wrong).decode(),))
        with self.assertRaisesRegex(RefreshError, 'query-record-binding'): self.call(f)
        self.assert_handlers_cleared(f)

    def test_step_and_time_failures_clear_both_handlers(self):
        f = self.fixture()
        with self.assertRaises(sqlite3.OperationalError): self.call(f, [f.obs]*3, max_steps=1)
        self.assert_handlers_cleared(f)
        fields = query._fields
        with patch.object(query.time, 'monotonic', return_value=100.0) as clock:
            def slow(*args):
                result = fields(*args); clock.return_value = 1000.0; return result
            with patch.object(query, '_fields', side_effect=slow):
                with self.assertRaisesRegex(RefreshError, 'query-time-bound'): self.call(f)
        self.assert_handlers_cleared(f)


if __name__ == '__main__': unittest.main()
