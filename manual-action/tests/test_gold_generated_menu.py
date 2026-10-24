"""Generated-only tests of snapshot-bound grouping and scope preservation."""
import copy
import hashlib
import json
from pathlib import Path
import sqlite3
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from gold_generated_menu import (GROUP_VERSION, GeneratedMenuError,
                                 query_snapshot, read_generated_menu)

EID, OTHER = '1' * 64, '2' * 64
DB_SHA, ADMISSION_SHA = 'a' * 64, 'b' * 64
RUN = 'recipe-actions:' + 'c' * 64


def group():
    return {'schemaVersion': GROUP_VERSION, 'id': 'application-menu:generated-example',
            'title': 'Generated recipe grouping', 'origin': 'APPLICATION_CREATED',
            'selectionOrigin': 'GENERATED',
            'snapshot': {'databaseSha256': DB_SHA, 'admissionSha256': ADMISSION_SHA},
            'members': [{'recipeEntityId': EID, 'nativeRunId': RUN}]}


def fixture(db):
    db.executescript('''
    CREATE TABLE gold_entities(entity_id TEXT PRIMARY KEY,resource_id TEXT,domain TEXT,entity_type TEXT,state TEXT,payload_json TEXT);
    CREATE TABLE gold_texts(text_id TEXT,source_text_id TEXT,entity_id TEXT,state TEXT,original_text TEXT,english_text TEXT);
    CREATE TABLE gold_occurrences(occurrence_id TEXT,source_key TEXT,source_version TEXT,record_id TEXT,content_sha256 TEXT,normalized_artifact_sha256 TEXT,state TEXT,payload_json TEXT);
    CREATE TABLE gold_entity_occurrences(entity_id TEXT,occurrence_id TEXT);
    CREATE TABLE gold_citations(citation_id TEXT,payload_json TEXT);
    CREATE TABLE gold_recipe_runs(run_id TEXT,recipe_entity_id TEXT,source_occurrence_id TEXT,target_language TEXT,status TEXT,gold_admission TEXT);
    CREATE TABLE gold_recipe_actions(run_id TEXT,sequence_index INTEGER,english_text TEXT,unknown_parameters_json TEXT);
    CREATE TABLE gold_holds(hold_id TEXT,target_kind TEXT,target_id TEXT,reason TEXT);
    ''')
    name = 'Generated crème source recipe'
    resource = {'id': 'generated:source:recipe', 'names': [{'id': 'name:1', 'value': name,
                'sourceTextSha256': hashlib.sha256(name.encode()).hexdigest()}],
                'citationIds': ['source:citation'], 'scope': {'visibility': 'local-restricted', 'reuseScope': 'Private attributed source only'}}
    db.execute('INSERT INTO gold_entities VALUES(?,?,?,?,?,?)',
               (EID, resource['id'], 'recipes', 'recipe', 'verified', json.dumps(resource)))
    db.execute('INSERT INTO gold_texts VALUES(?,?,?,?,?,?)', ('text:1', 'name:1', EID, 'verified', name, name))
    original = {'kind': 'recipe', 'data': {'directions': ['Original source alternatives retained.']},
                'provenance': {'sourceId': 'generated-test', 'revisionId': 7}}
    occurrence = {'resource_ids': [resource['id']], 'citation_ids': ['source:citation'], 'source_original': original}
    db.execute('INSERT INTO gold_occurrences VALUES(?,?,?,?,?,?,?,?)',
               ('occ:1', 'generated-test', 'revision:7', 'source:1', 'd' * 64, 'e' * 64, 'verified', json.dumps(occurrence)))
    db.execute('INSERT INTO gold_entity_occurrences VALUES(?,?)', (EID, 'occ:1'))
    db.execute('INSERT INTO gold_citations VALUES(?,?)', ('source:citation', json.dumps(
        {'id': 'source:citation', 'sourceId': 'generated-test', 'revisionId': 7, 'attribution': 'Generated source author',
         'scope': {'visibility': 'local-restricted'}})))
    db.execute('INSERT INTO gold_recipe_runs VALUES(?,?,?,?,?,?)', (RUN, EID, 'occ:1', 'en', 'ready-for-review', 'not-assigned'))
    db.executemany('INSERT INTO gold_recipe_actions VALUES(?,?,?,?)', [
        (RUN, 0, 'Combine the generated inputs.', '["yield-unqualified"]'),
        (RUN, 1, 'Knead until evenly incorporated.', '["physical-cooking-unobserved"]')])
    db.execute('INSERT INTO gold_holds VALUES(?,?,?,?)', ('hold:1', 'recipe-run', RUN, 'GENERATED preparation handoff only'))
    db.commit()
    db.execute('PRAGMA query_only=ON')


class GeneratedMenuTests(unittest.TestCase):
    def setUp(self):
        self.db = sqlite3.connect(':memory:')
        fixture(self.db)

    def tearDown(self):
        self.db.close()

    def resolve(self, value=None, **limits):
        return read_generated_menu(self.db, group() if value is None else value,
                                   database_sha256=DB_SHA, admission_sha256=ADMISSION_SHA, **limits)

    def edit(self, sql, values=()):
        self.db.execute('PRAGMA query_only=OFF')
        self.db.execute(sql, values)
        self.db.commit()
        self.db.execute('PRAGMA query_only=ON')

    def test_generated_group_preserves_english_instructions_citations_and_limits(self):
        original = group()
        result = self.resolve(original)
        self.assertEqual(original, group())
        self.assertEqual(result['origin'], 'APPLICATION_CREATED')
        self.assertEqual(result['selectionOrigin'], 'GENERATED')
        member = result['members'][0]
        self.assertEqual(member['englishNames'], ['Generated crème source recipe'])
        self.assertEqual(member['instructions'], ['Combine the generated inputs.', 'Knead until evenly incorporated.'])
        self.assertEqual(member['citations'][0]['revisionId'], 7)
        self.assertEqual(member['holds'][0]['reason'], 'GENERATED preparation handoff only')
        self.assertEqual(member['native']['actions'][0]['unknown_parameters_json'], '["yield-unqualified"]')
        self.assertEqual(member['sourceScope']['visibility'], 'local-restricted')
        for key in ['nutritionTotals', 'combinedNutrition', 'sourceMenuEvidence']:
            self.assertIsNone(result[key])
        self.assertFalse(result['actualUserSelection'])
        self.assertFalse(result['mealSuitabilityQualified'])
        self.assertFalse(result['automaticPlanning'])

    def test_source_menu_or_user_choice_cannot_be_requested(self):
        for key, value in [('origin', 'SOURCE_MENU'), ('selectionOrigin', 'USER_SELECTED')]:
            value_group = group(); value_group[key] = value
            with self.assertRaisesRegex(GeneratedMenuError, 'generated-origin-required'):
                self.resolve(value_group)
        value_group = group(); value_group['sourceMenuCitation'] = 'invented'
        with self.assertRaisesRegex(GeneratedMenuError, 'group-schema'):
            self.resolve(value_group)

    def test_duplicate_missing_and_product_references_rejected(self):
        value_group = group(); value_group['members'] *= 2
        with self.assertRaisesRegex(GeneratedMenuError, 'duplicate-recipe-reference'):
            self.resolve(value_group)
        value_group = group(); value_group['members'][0]['recipeEntityId'] = OTHER
        with self.assertRaisesRegex(GeneratedMenuError, 'missing-or-foreign-recipe-reference'):
            self.resolve(value_group)
        self.edit("UPDATE gold_entities SET domain='barcodes',entity_type='barcode-product'")
        with self.assertRaisesRegex(GeneratedMenuError, 'missing-or-foreign-recipe-reference'):
            self.resolve()

    def test_foreign_run_and_occurrence_binding_rejected(self):
        self.edit('UPDATE gold_recipe_runs SET recipe_entity_id=?', (OTHER,))
        with self.assertRaisesRegex(GeneratedMenuError, 'missing-or-foreign-native-run'):
            self.resolve()
        self.edit('UPDATE gold_recipe_runs SET recipe_entity_id=?,source_occurrence_id=?', (EID, 'foreign:occ'))
        with self.assertRaisesRegex(GeneratedMenuError, 'native-run-source-language-binding'):
            self.resolve()

    def test_no_implicit_run_choice_or_instruction_language_inference(self):
        value_group = group(); del value_group['members'][0]['nativeRunId']
        member = self.resolve(value_group)['members'][0]
        self.assertIsNone(member['native'])
        self.assertEqual(member['instructions'], [])
        self.assertEqual(member['instructionState'], 'unknown-no-run-selected')
        self.assertEqual(member['availableNativeRunIds'], [RUN])
        self.assertIn('Original source alternatives', member['sourceRecords'][0]['sourceOriginal']['data']['directions'][0])

    def test_snapshot_binding_and_unqualified_english_are_explicit(self):
        value_group = group(); value_group['snapshot']['databaseSha256'] = 'f' * 64
        with self.assertRaisesRegex(GeneratedMenuError, 'group-snapshot-mismatch'):
            self.resolve(value_group)
        self.edit('UPDATE gold_texts SET state=?', ('held',))
        self.assertEqual(self.resolve()['members'][0]['englishNameState'], 'unknown')

    def test_missing_citation_or_wrong_source_occurrence_cannot_be_grouped(self):
        self.edit('DELETE FROM gold_citations')
        with self.assertRaisesRegex(GeneratedMenuError, 'missing-recipe-citation'):
            self.resolve()

    def test_read_only_connection_required_and_unchanged(self):
        before = self.db.total_changes
        self.resolve()
        self.assertEqual(self.db.total_changes, before)
        self.assertEqual(self.db.execute('PRAGMA query_only').fetchone()[0], 1)
        self.db.execute('PRAGMA query_only=OFF')
        with self.assertRaisesRegex(GeneratedMenuError, 'read-only-connection-required'):
            self.resolve()

    def test_budgets_fail_without_partial_results(self):
        for limits, error in [({'max_rows': 1}, 'query-row-limit'),
                              ({'max_bytes': 1}, 'menu-output-limit')]:
            with self.assertRaisesRegex(GeneratedMenuError, error):
                self.resolve(**limits)
        value_group = group(); value_group['members'] = []
        with self.assertRaisesRegex(GeneratedMenuError, 'member-limit'):
            self.resolve(value_group)

    def test_nonfinite_bool_and_oversized_limits_rejected(self):
        for limits in [{'max_seconds': float('nan')}, {'max_seconds': float('inf')},
                       {'max_seconds': True}, {'max_rows': True}, {'max_members': 17}]:
            with self.assertRaisesRegex(GeneratedMenuError, 'invalid-limit'):
                self.resolve(**limits)

    def test_strict_reference_schema_and_input_bound(self):
        value_group = group(); value_group['members'][0]['nativeRunId'] = 'foreign:recipe'
        with self.assertRaisesRegex(GeneratedMenuError, 'native-run-id-required'):
            self.resolve(value_group)
        value_group = group(); value_group['title'] = 'x' * 70000
        with self.assertRaisesRegex(GeneratedMenuError, 'group-byte-limit'):
            self.resolve(value_group)

    def test_selected_snapshot_wrapper_checks_bytes_and_no_sidecars(self):
        with tempfile.TemporaryDirectory(prefix='generated-menu-test-') as directory:
            root = Path(directory); database = root / 'generated.sqlite3'
            db = sqlite3.connect(database); fixture(db); db.close()
            db_hash = hashlib.sha256(database.read_bytes()).hexdigest()
            receipt = root / 'admission.json'
            receipt.write_text(json.dumps({'state': 'ACCEPTED_GENERATED_TEST_FIXTURE_ONLY',
                'artifact': {'path': str(database), 'sha256': db_hash},
                'scopeLimits': {'publicRedistributionQualified': False}}))
            receipt_hash = hashlib.sha256(receipt.read_bytes()).hexdigest()
            value_group = group(); value_group['snapshot'] = {'databaseSha256': db_hash, 'admissionSha256': receipt_hash}
            before = database.read_bytes()
            result = query_snapshot(receipt, receipt_hash, value_group)
            self.assertEqual(result['admissionScopeLimits'], {'publicRedistributionQualified': False})
            self.assertEqual(database.read_bytes(), before)
            self.assertEqual(set(root.iterdir()), {database, receipt})
            with self.assertRaisesRegex(GeneratedMenuError, 'admission-hash-mismatch'):
                query_snapshot(receipt, '0' * 64, value_group)
            sidecar = Path(str(database) + '-journal'); sidecar.write_bytes(b'generated-only')
            with self.assertRaisesRegex(GeneratedMenuError, 'sealed-snapshot-required'):
                query_snapshot(receipt, receipt_hash, value_group)
            sidecar.unlink()
            database.write_bytes(before + b'changed')
            with self.assertRaisesRegex(GeneratedMenuError, 'database-hash-mismatch'):
                query_snapshot(receipt, receipt_hash, value_group)


if __name__ == '__main__':
    unittest.main()
