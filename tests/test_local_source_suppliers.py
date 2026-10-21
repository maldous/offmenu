"""Generated fixtures ONLY. Never open retained suppliers, dictionaries or other corpora."""
import gzip
import hashlib
import importlib.util
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location('supplier_candidate', ROOT / 'offmenu/refresh/local_source_suppliers.py')
module = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(module)
SCHEMA = (ROOT / 'tests/fixtures/source_supplier_reference_v1.sql').read_bytes()


def fixture(index=1, extra=''):
    native = 'Q' + str(index)
    return {'schemaVersion': '1.0', 'kind': 'organization',
        'id': module.SOURCE_ID + ':organization:' + native, 'countries': ['ZZ'],
        'provenance': {'sourceId': module.SOURCE_ID, 'releaseId': module.RELEASE_ID,
            'recordId': native, 'license': 'CC0 1.0', 'visibility': 'public',
            'url': 'https://example.invalid/' + native, 'fetchedAt': None},
        'data': {'name': '  Generated Ω actor  ', 'roles': ['supermarket-chain'],
            'names': {'xx': 'Fixture only'}, 'identifiers': [{'system': 'Wikidata', 'value': native}],
            'countryBasis': 'Fixture assertion, not a location', 'unmapped': extra}}


class SourceSuppliersTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
    def tearDown(self):
        # Only this test's quiescent generated fixtures; no real-output deletion policy.
        self.tmp.cleanup()
    def source(self, records=None, raw=None):
        raw = raw if raw is not None else b''.join(
            json.dumps([x], ensure_ascii=False, separators=(',', ':')).encode() + b'\n'
            for x in (records or [fixture()]))
        path = self.root / 'generated.jsonl.gz'
        path.write_bytes(gzip.compress(raw))
        return path, raw
    def call(self, path, count=1, **overrides):
        args = {'schema_sql': SCHEMA, 'expected_identity': module._identity(path.stat()),
            'expected_records': count, 'expected_input_sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
            'hash_policy': 'independently-pinned', 'max_compressed_bytes': 1048576,
            'max_expanded_bytes': 8388608, 'max_line_bytes': 65536,
            'max_database_bytes': 16777216, 'max_output_bytes': 33619968,
            'checkpoint_rows': 2}
        args.update(overrides)
        return module.import_local_source_actors(path, self.root / 'output', **args)
    def stored_counts(self):
        with sqlite3.connect(self.root / 'output/suppliers.sqlite') as db:
            return (db.execute('SELECT count(*) FROM retained_reference_record').fetchone()[0],
                    db.execute('SELECT count(*) FROM supplier_source_actor').fetchone()[0])
    def failure(self, path, code=None, **kwargs):
        with self.assertRaises(module.SupplierImportError) as caught:
            self.call(path, **kwargs)
        if code:
            self.assertEqual(code, str(caught.exception))
        receipt = json.loads((self.root / 'output/progress.json').read_text())
        self.assertEqual('failed', receipt['state'])
        self.assertEqual(0, receipt['committed_reference_rows'])
        self.assertEqual(0, receipt['committed_actor_rows'])
        self.assertTrue(receipt['source_fd_closed'])
        self.assertTrue(receipt['database_closed'])
        self.assertEqual(receipt, caught.exception.receipt)
        return receipt
    def test_exact_source_and_unknowns_survive(self):
        path, raw = self.source([fixture(extra='unmapped source value')])
        out = self.call(path)
        self.assertEqual('completed-source-import', out['state'])
        self.assertTrue(out['crc_eof_verified'])
        self.assertTrue(out['source_identity_verified'])
        with sqlite3.connect(self.root / 'output/suppliers.sqlite') as db:
            reference = db.execute('SELECT source_payload_json,parsed_record_sha256,original_language,citation_id FROM retained_reference_record').fetchone()
            self.assertEqual(raw.decode(), reference[0])
            self.assertEqual(hashlib.sha256(raw).hexdigest(), reference[1])
            self.assertEqual(('und', None), reference[2:])
            actor = db.execute('SELECT original_name,source_role_lexeme,source_location_lexeme,canonical_organization_id,normalization_status FROM supplier_source_actor').fetchone()
            self.assertEqual(('  Generated Ω actor  ', '["supermarket-chain"]', None, None, 'pending'), actor)
            self.assertEqual([], db.execute('PRAGMA foreign_key_check').fetchall())
    def test_repeated_source_ids_are_retained(self):
        path, raw = self.source([fixture(), fixture()])
        out = self.call(path, count=2)
        self.assertEqual((2, 2), self.stored_counts())
        self.assertEqual(1, out['distinct_source_actor_ids'])
        self.assertEqual(1, out['repeated_source_actor_occurrences'])
    def test_generated_1505_records_exceed_old_3mib_and_fit_proposed_16mib(self):
        path, raw = self.source([fixture(i, 'x' * 4096) for i in range(1, 1506)])
        out = self.call(path, count=1505, checkpoint_rows=128)
        self.assertEqual((1505, 1505), self.stored_counts())
        self.assertEqual(1505, out['committed_actor_rows'])
        self.assertGreater((self.root / 'output/suppliers.sqlite').stat().st_size, 3145728)
    def test_storage_limit_retains_input_hash_and_exact_failure_counters(self):
        path, raw = self.source([fixture(i, 'x' * 4096) for i in range(1, 21)])
        receipt = self.failure(path, 'supplier-storage-bound', count=20,
            max_database_bytes=65536, max_output_bytes=196608)
        self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), receipt['observed_input_sha256'])
        self.assertGreater(receipt['read_records'], 0)
        self.assertEqual((0, 0), self.stored_counts())
    def test_late_crc_failure_rolls_back_and_keeps_durable_counters(self):
        path, raw = self.source([fixture(), fixture(2)])
        body = bytearray(path.read_bytes()); body[-8] ^= 1; path.write_bytes(body)
        receipt = self.failure(path, count=2)
        self.assertFalse(receipt['crc_eof_verified'])
        self.assertEqual((0, 0), self.stored_counts())
    def test_wrong_pin_stops_before_database_and_records_observed_hash(self):
        path, raw = self.source()
        receipt = self.failure(path, 'supplier-input-pin-or-identity', expected_input_sha256='0' * 64)
        self.assertIsNotNone(receipt['observed_input_sha256'])
        self.assertEqual(0, receipt['read_records'])
        self.assertFalse((self.root / 'output/suppliers.sqlite').exists())
    def test_scope_failure_never_logs_private_source_values(self):
        row = fixture(); row['provenance']['sourceId'] = 'PRIVATE_SOURCE_SENTINEL'
        path, raw = self.source([row])
        receipt = self.failure(path, 'supplier-record-scope')
        self.assertNotIn('PRIVATE_SOURCE_SENTINEL', json.dumps(receipt))
    def test_count_mismatch_is_incomplete(self):
        path, raw = self.source()
        self.failure(path, 'supplier-record-count', count=2)
        self.assertEqual((0, 0), self.stored_counts())
    def test_existing_output_is_never_overwritten(self):
        path, raw = self.source(); out = self.root / 'output'; out.mkdir()
        marker = out / 'owned-by-another-attempt'; marker.write_text('retain')
        with self.assertRaises(module.SupplierImportError) as caught:
            self.call(path)
        self.assertEqual('supplier-output-exists', str(caught.exception))
        self.assertEqual('retain', marker.read_text())
        self.assertEqual(0, caught.exception.receipt['compressed_bytes_read'])
    def test_observed_snapshot_is_explicit_and_not_acceptance(self):
        path, raw = self.source()
        out = self.call(path, expected_input_sha256=None, hash_policy='observe-selected-custody-snapshot')
        self.assertFalse(out['accepted'])
        self.assertEqual('observe-selected-custody-snapshot', out['input_hash_policy'])
    def test_over_bound_line_is_not_silently_truncated(self):
        path, raw = self.source([fixture(extra='x' * 2000)])
        self.failure(path, 'supplier-expanded-bound', max_line_bytes=100)
    def test_json_duplicate_keys_are_rejected(self):
        path, raw = self.source(raw=b'[{"kind":"organization","kind":"other"}]\n')
        self.failure(path, 'supplier-invalid-or-incomplete-input')
    def test_empty_roles_are_rejected(self):
        row = fixture(); row['data']['roles'] = []
        path, raw = self.source([row])
        self.failure(path, 'supplier-record-scope')
        self.assertEqual((0, 0), self.stored_counts())
    def test_unknown_roles_are_rejected(self):
        row = fixture(); row['data']['roles'] = ['restaurant']
        path, raw = self.source([row])
        receipt = self.failure(path, 'supplier-record-scope')
        self.assertNotIn('restaurant', json.dumps(receipt))
        self.assertEqual((0, 0), self.stored_counts())
    def test_late_unknown_role_rolls_back_prior_record(self):
        row = fixture(2); row['data']['roles'] = ['food-manufacturer', 'restaurant']
        path, raw = self.source([fixture(), row])
        receipt = self.failure(path, 'supplier-record-scope', count=2)
        self.assertEqual(2, receipt['read_records'])
        self.assertEqual(1, receipt['parsed_records'])
        self.assertEqual((0, 0), self.stored_counts())
    def test_all_exact_generator_roles_remain_source_faithful(self):
        row = fixture(); row['data']['roles'] = [
            'food-manufacturer', 'grocery-store-chain', 'supermarket-chain']
        path, raw = self.source([row])
        self.call(path)
        with sqlite3.connect(self.root / 'output/suppliers.sqlite') as db:
            roles = db.execute('SELECT source_role_lexeme FROM supplier_source_actor').fetchone()[0]
        self.assertEqual(row['data']['roles'], json.loads(roles))
    def language_after_import(self, name, names):
        row = fixture(); row['data']['name'] = name
        if names is None:
            row['data'].pop('names')
        else:
            row['data']['names'] = names
        path, raw = self.source([row]); self.call(path)
        with sqlite3.connect(self.root / 'output/suppliers.sqlite') as db:
            language, payload = db.execute(
                'SELECT original_language,source_payload_json FROM retained_reference_record').fetchone()
        self.assertEqual(raw.decode(), payload)
        return language
    def test_explicit_matching_primary_name_language_is_preserved(self):
        self.assertEqual('fr', self.language_after_import('Nom', {'fr': 'Nom'}))
    def test_exact_source_language_tag_and_name_are_preserved(self):
        self.assertEqual('fr-CA', self.language_after_import('  Nom Ω  ', {'fr-CA': '  Nom Ω  '}))
    def test_explicit_multilingual_source_tag_is_preserved(self):
        self.assertEqual('mul', self.language_after_import('Name', {'mul': 'Name'}))
    def test_missing_language_evidence_stays_und(self):
        self.assertEqual('und', self.language_after_import('Nom', None))
    def test_nonmatching_language_name_is_not_normalized_into_a_match(self):
        self.assertEqual('und', self.language_after_import('Nom', {'fr': 'nom'}))
    def test_ambiguous_matching_language_names_stay_und(self):
        self.assertEqual('und', self.language_after_import('Nom', {'fr': 'Nom', 'en': 'Nom'}))


if __name__ == '__main__':
    unittest.main()
