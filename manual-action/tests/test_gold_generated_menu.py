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
    CREATE TABLE gold_texts(text_id TEXT,source_text_id TEXT,entity_id TEXT,state TEXT,original_text TEXT,english_text TEXT,language TEXT,evidence_json TEXT);
    CREATE TABLE gold_support(support_id TEXT,target_kind TEXT,target_id TEXT,citation_id TEXT,support_scope TEXT,evidence_sha256 TEXT);
    CREATE TABLE gold_occurrences(occurrence_id TEXT,source_key TEXT,source_version TEXT,record_id TEXT,content_sha256 TEXT,normalized_artifact_sha256 TEXT,state TEXT,payload_json TEXT);
    CREATE TABLE gold_entity_occurrences(entity_id TEXT,occurrence_id TEXT);
    CREATE TABLE gold_citations(citation_id TEXT,payload_json TEXT);
    CREATE TABLE gold_recipe_runs(run_id TEXT,recipe_entity_id TEXT,source_occurrence_id TEXT,target_language TEXT,status TEXT,gold_admission TEXT,native_source_pin TEXT,native_modules_json TEXT,rules_artifact_sha256 TEXT,semantic_review_sha256 TEXT,translation_receipts_sha256 TEXT,connection_sha256 TEXT,source_original_sha256 TEXT);
    CREATE TABLE gold_recipe_actions(run_id TEXT,sequence_index INTEGER,english_text TEXT,unknown_parameters_json TEXT,action_id TEXT,source_order INTEGER,original_text TEXT,evidence_json TEXT);
    CREATE TABLE gold_recipe_action_support(run_id TEXT,action_id TEXT,citation_id TEXT,evidence_json TEXT);
    CREATE TABLE gold_holds(hold_id TEXT,target_kind TEXT,target_id TEXT,reason TEXT);
    ''')
    name = 'Generated crème source recipe'
    resource = {'id': 'generated:source:recipe', 'names': [{'id': 'name:1', 'value': name, 'language': 'en', 'citationIds': ['source:citation'],
                'sourceTextSha256': hashlib.sha256(name.encode()).hexdigest()}],
                'citationIds': ['source:citation'], 'scope': {'visibility': 'local-restricted', 'reuseScope': 'Private attributed source only'}}
    db.execute('INSERT INTO gold_entities VALUES(?,?,?,?,?,?)',
               (EID, resource['id'], 'recipes', 'recipe', 'verified', json.dumps(resource)))
    db.execute('INSERT INTO gold_texts VALUES(?,?,?,?,?,?,?,?)', ('text:1', 'name:1', EID, 'verified', name, name, 'en', 'null'))
    db.execute('INSERT INTO gold_support VALUES(?,?,?,?,?,?)', ('support:name:1', 'text', 'name:1', 'source:citation', 'field', 'a' * 64))
    original = {'kind': 'recipe', 'data': {'directions': ['Original source alternatives retained.']},
                'provenance': {'sourceId': 'generated-test', 'revisionId': 7}}
    occurrence = {'resource_ids': [resource['id']], 'citation_ids': ['source:citation'], 'source_original': original}
    db.execute('INSERT INTO gold_occurrences VALUES(?,?,?,?,?,?,?,?)',
               ('occ:1', 'generated-test', 'revision:7', 'source:1', 'd' * 64, 'e' * 64, 'verified', json.dumps(occurrence)))
    db.execute('INSERT INTO gold_entity_occurrences VALUES(?,?)', (EID, 'occ:1'))
    db.execute('INSERT INTO gold_citations VALUES(?,?)', ('source:citation', json.dumps(
        {'id': 'source:citation', 'sourceId': 'generated-test', 'revisionId': 7, 'attribution': 'Generated source author', 'license': 'Generated fixture license',
         'scope': {'visibility': 'local-restricted'}})))
    db.execute('INSERT INTO gold_recipe_runs VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)',
               (RUN, EID, 'occ:1', 'en', 'ready-for-review', 'not-assigned', 'd' * 40,
                json.dumps({'generated.py': 'e' * 64}), *(['f' * 64] * 5)))
    for index, (text, unknown) in enumerate([
            ('Combine the generated inputs.', '["yield-unqualified"]'),
            ('Knead until evenly incorporated.', '["physical-cooking-unobserved"]')]):
        evidence = json.dumps([{'pointer': f'/steps/{index}/raw_text', 'start': 0,
                               'end': len(text), 'text': text, 'offset_unit': 'unicode_codepoint'}])
        db.execute('INSERT INTO gold_recipe_actions VALUES(?,?,?,?,?,?,?,?)',
                   (RUN, index, text, unknown, f'action:{index}', index, text, evidence))
        db.execute('INSERT INTO gold_recipe_action_support VALUES(?,?,?,?)',
                   (RUN, f'action:{index}', 'source:citation', evidence))
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

    def distinct_name(self, *, translated=False):
        self.db.execute('PRAGMA query_only=OFF')
        payload = json.loads(self.db.execute('SELECT payload_json FROM gold_entities WHERE entity_id=?', (EID,)).fetchone()[0])
        original = 'Recette de crème' if translated else 'Generated crème source recipe'
        english = 'Cream recipe' if translated else original
        name = payload['names'][0]
        name.update(value=original, language='fr' if translated else 'en', citationIds=['name:separate'],
                    sourceTextSha256=hashlib.sha256(original.encode()).hexdigest())
        self.db.execute('UPDATE gold_entities SET payload_json=? WHERE entity_id=?', (json.dumps(payload), EID))
        evidence = {'kind': 'generated-translation-evidence', 'sourceLanguage': 'fr', 'targetLanguage': 'en'} if translated else None
        self.db.execute('UPDATE gold_texts SET original_text=?,english_text=?,language=?,evidence_json=? WHERE entity_id=?',
                        (original, english, name['language'], json.dumps(evidence), EID))
        self.db.execute('UPDATE gold_support SET citation_id=? WHERE target_id=?', ('name:separate', 'name:1'))
        citation = {'id': 'name:separate', 'license': 'Independent name license', 'attribution': 'Independent name author',
                    'scope': {'visibility': 'local-restricted'}}
        self.db.execute('INSERT INTO gold_citations VALUES(?,?)', ('name:separate', json.dumps(citation)))
        self.db.commit(); self.db.execute('PRAGMA query_only=ON')
        return original, english, evidence, citation

    def test_name_provenance_distinct_citation_and_original_text_retained(self):
        original, english, evidence, citation = self.distinct_name()
        member = self.resolve()['members'][0]
        self.assertEqual(member['englishNames'], [english])
        self.assertIn(citation, member['citations'])
        record = member['nameRecords'][0]
        self.assertEqual(record['status'], 'qualified')
        self.assertEqual(record['textRecord']['original_text'], original)
        self.assertEqual(record['textRecord']['language'], 'en')
        self.assertIsNone(record['evidence'])
        self.assertEqual(record['sourceName']['citationIds'], ['name:separate'])
        self.assertEqual(record['citations'], [citation])
        self.assertEqual(record['supportRecords'][0]['target_id'], 'name:1')

    def test_name_provenance_translated_text_keeps_original_language_and_evidence(self):
        original, english, evidence, citation = self.distinct_name(translated=True)
        member = self.resolve()['members'][0]
        self.assertEqual(member['englishNames'], [english])
        record = member['nameRecords'][0]
        self.assertEqual(record['textRecord']['original_text'], original)
        self.assertEqual(record['textRecord']['language'], 'fr')
        self.assertEqual(record['evidence'], evidence)
        self.assertEqual(json.loads(record['textRecord']['evidence_json']), evidence)
        self.assertEqual(record['citations'], [citation])

    def test_name_provenance_missing_name_citation_holds_only_that_name(self):
        self.distinct_name()
        self.edit('DELETE FROM gold_citations WHERE citation_id=?', ('name:separate',))
        member = self.resolve()['members'][0]
        self.assertEqual(member['englishNames'], [])
        self.assertEqual(member['englishNameState'], 'unknown')
        self.assertEqual(member['nameRecords'][0]['status'], 'held')
        self.assertTrue(member['nameRecords'][0]['holdReasons'])
        self.assertTrue(member['instructions'])

    def test_name_provenance_missing_or_invalid_support_is_explicitly_held(self):
        self.distinct_name()
        for update, values in [
            ('UPDATE gold_support SET evidence_sha256=?', ('invalid',)),
            ('UPDATE gold_support SET evidence_sha256=?,support_scope=?', ('a' * 64, 'record')),
            ('UPDATE gold_support SET support_scope=?,target_id=?', ('field', 'foreign:text')),
            ('DELETE FROM gold_support', ())]:
            with self.subTest(update=update):
                self.edit(update, values)
                member = self.resolve()['members'][0]
                self.assertEqual(member['englishNames'], [])
                self.assertEqual(member['nameRecords'][0]['status'], 'held')
                self.assertIn('name-support-missing-or-invalid', member['nameRecords'][0]['holdReasons'])

    def test_name_provenance_unknown_rights_holds_name(self):
        self.distinct_name()
        self.edit('UPDATE gold_citations SET payload_json=? WHERE citation_id=?',
                  (json.dumps({'id': 'name:separate', 'attribution': 'Author, no license supplied'}), 'name:separate'))
        member = self.resolve()['members'][0]
        self.assertEqual(member['englishNames'], [])
        self.assertIn('name-citation-rights-unknown', member['nameRecords'][0]['holdReasons'])

    def add_member_sibling(self):
        self.db.execute('PRAGMA query_only=OFF')
        payload = json.loads(self.db.execute('SELECT payload_json FROM gold_entities WHERE entity_id=?', (EID,)).fetchone()[0])
        payload['id'] = 'generated:second:recipe'
        payload['names'][0].update(id='name:second', citationIds=['source:citation'])
        self.db.execute('INSERT INTO gold_entities VALUES(?,?,?,?,?,?)',
                        (OTHER, payload['id'], 'recipes', 'recipe', 'verified', json.dumps(payload)))
        self.db.execute('INSERT INTO gold_texts SELECT ?,?, ?,state,original_text,english_text,language,evidence_json FROM gold_texts WHERE entity_id=?',
                        ('text:second', 'name:second', OTHER, EID))
        occurrence = json.loads(self.db.execute('SELECT payload_json FROM gold_occurrences WHERE occurrence_id=?', ('occ:1',)).fetchone()[0])
        occurrence['resource_ids'] = [payload['id']]
        self.db.execute('INSERT INTO gold_occurrences SELECT ?,source_key,source_version,record_id,content_sha256,normalized_artifact_sha256,state,? FROM gold_occurrences WHERE occurrence_id=?',
                        ('occ:second', json.dumps(occurrence), 'occ:1'))
        self.db.execute('INSERT INTO gold_entity_occurrences VALUES(?,?)', (OTHER, 'occ:second'))
        self.db.execute('INSERT INTO gold_support VALUES(?,?,?,?,?,?)',
                        ('support:second', 'text', 'name:second', 'source:citation', 'field', 'a' * 64))
        self.db.commit(); self.db.execute('PRAGMA query_only=ON')
        request = group(); request['members'].append({'recipeEntityId': OTHER})
        return request

    def test_name_provenance_bad_name_does_not_drop_valid_member_sibling(self):
        self.distinct_name()
        request = self.add_member_sibling()
        self.edit('DELETE FROM gold_support WHERE target_id=?', ('name:1',))
        result = self.resolve(request)
        self.assertEqual(len(result['members']), 2)
        self.assertEqual(result['members'][0]['englishNameState'], 'unknown')
        self.assertTrue(result['members'][1]['englishNames'])
        self.assertEqual(result['members'][1]['nameRecords'][0]['status'], 'qualified')

    def distinct_action(self):
        citation = {'id': 'action:separate', 'license': 'Action-only license',
                    'attribution': 'Action-only author', 'scope': {'visibility': 'local-restricted'}}
        self.edit('INSERT INTO gold_citations VALUES(?,?)', (citation['id'], json.dumps(citation)))
        self.edit('UPDATE gold_recipe_action_support SET citation_id=?', (citation['id'],))
        return citation

    def test_action_provenance_distinct_citation_support_and_rights_retained(self):
        citation = self.distinct_action()
        member = self.resolve()['members'][0]
        self.assertIn(citation, member['citations'])
        for record in member['instructionRecords']:
            self.assertEqual(record['status'], 'qualified')
            self.assertEqual(record['citations'], [citation])
            self.assertEqual(record['supportRecords'][0]['action_id'], record['actionRecord']['action_id'])
            self.assertEqual(record['supportEvidence'][0], record['evidence'])
        self.assertEqual(len(member['instructions']), 2)

    def test_action_provenance_missing_invalid_or_foreign_support_holds_sequence(self):
        for sql, args in [
                ('DELETE FROM gold_recipe_action_support WHERE action_id=?', ('action:0',)),
                ('UPDATE gold_recipe_action_support SET action_id=?', ('foreign:action',)),
                ('UPDATE gold_recipe_action_support SET run_id=?', ('recipe-actions:' + 'd' * 64,)),
                ('UPDATE gold_recipe_action_support SET evidence_json=?', ('invalid',)),
                ('UPDATE gold_recipe_action_support SET evidence_json=?', ('[]',)),
                ('UPDATE gold_recipe_action_support SET evidence_json=(SELECT evidence_json FROM gold_recipe_actions WHERE action_id=?) WHERE action_id=?', ('action:1', 'action:0')),
                ('UPDATE gold_recipe_actions SET evidence_json=? WHERE action_id=?', ('invalid', 'action:0')),
                ('UPDATE gold_recipe_action_support SET evidence_json=?',
                 (json.dumps([{'pointer': '/steps/99/raw_text', 'start': 0, 'end': 1,
                               'text': 'x', 'offset_unit': 'unicode_codepoint'}]),))]:
            with self.subTest(sql=sql, args=args):
                db = sqlite3.connect(':memory:'); fixture(db)
                db.execute('PRAGMA query_only=OFF'); db.execute(sql, args); db.commit()
                db.execute('PRAGMA query_only=ON')
                try:
                    member = read_generated_menu(db, group(), database_sha256=DB_SHA,
                                                 admission_sha256=ADMISSION_SHA)['members'][0]
                    self.assertEqual(member['instructions'], [])
                    self.assertEqual(member['instructionState'], 'held-action-provenance')
                    self.assertTrue(member['englishNames'])
                    self.assertTrue(any(r['holdReasons'] for r in member['instructionRecords']))
                finally:
                    db.close()

    def test_action_provenance_bad_pins_and_missing_invalid_rights_hold(self):
        cases = [
            ('UPDATE gold_recipe_runs SET native_source_pin=?', ('unset',)),
            ('UPDATE gold_recipe_runs SET native_modules_json=?', ('{}',)),
            ('UPDATE gold_recipe_runs SET native_modules_json=?', ('{"module.py":"invalid"}',)),
            ('DELETE FROM gold_citations WHERE citation_id=?', ('action:separate',)),
            ('UPDATE gold_citations SET payload_json=? WHERE citation_id=?',
             (json.dumps({'id': 'wrong', 'license': 'L', 'attribution': 'A'}), 'action:separate')),
            ('UPDATE gold_citations SET payload_json=? WHERE citation_id=?', ('invalid', 'action:separate')),
            ('UPDATE gold_citations SET payload_json=? WHERE citation_id=?',
             (json.dumps({'id': 'action:separate', 'license': 'L'}), 'action:separate'))]
        cases.extend((f'UPDATE gold_recipe_runs SET {field}=?', ('missing',)) for field in [
            'rules_artifact_sha256', 'semantic_review_sha256', 'translation_receipts_sha256',
            'connection_sha256', 'source_original_sha256'])
        for sql, args in cases:
            with self.subTest(sql=sql, args=args):
                original_db = self.db
                self.db = sqlite3.connect(':memory:'); fixture(self.db)
                try:
                    self.distinct_action()
                    self.edit(sql, args)
                    member = self.resolve()['members'][0]
                    self.assertEqual(member['instructions'], [])
                    self.assertEqual(member['instructionState'], 'held-action-provenance')
                    self.assertTrue(member['englishNames'])
                finally:
                    self.db.close(); self.db = original_db

    def test_action_provenance_held_sequence_keeps_healthy_member_sibling(self):
        request = self.add_member_sibling()
        # A second independently selected run remains healthy while the first is held.
        second_run = 'recipe-actions:' + 'd' * 64
        self.db.execute('PRAGMA query_only=OFF')
        self.db.execute('INSERT INTO gold_recipe_runs SELECT ?,?, ?,target_language,status,gold_admission,'
                        'native_source_pin,native_modules_json,rules_artifact_sha256,semantic_review_sha256,'
                        'translation_receipts_sha256,connection_sha256,source_original_sha256 '
                        'FROM gold_recipe_runs WHERE run_id=?', (second_run, OTHER, 'occ:second', RUN))
        self.db.execute('INSERT INTO gold_recipe_actions SELECT ?,sequence_index,english_text,'
                        'unknown_parameters_json,action_id,source_order,original_text,evidence_json '
                        'FROM gold_recipe_actions WHERE run_id=?', (second_run, RUN))
        self.db.execute('INSERT INTO gold_recipe_action_support SELECT ?,action_id,citation_id,evidence_json '
                        'FROM gold_recipe_action_support WHERE run_id=?', (second_run, RUN))
        self.db.commit(); self.db.execute('PRAGMA query_only=ON')
        self.edit('DELETE FROM gold_recipe_action_support WHERE run_id=? AND action_id=?', (RUN, 'action:0'))
        request['members'][1]['nativeRunId'] = second_run
        first, second = self.resolve(request)['members']
        self.assertEqual(first['instructions'], [])
        self.assertEqual(first['instructionState'], 'held-action-provenance')
        self.assertEqual(len(second['instructions']), 2)
        self.assertEqual(second['instructionState'], 'selected-native-run')
        self.assertTrue(second['englishNames'])

    def test_receipt_limits_projection_preserves_both_fields_and_marks_unknown(self):
        with tempfile.TemporaryDirectory(prefix='generated-menu-limits-') as directory:
            root = Path(directory); database = root / 'generated.sqlite3'
            db = sqlite3.connect(database); fixture(db); db.close()
            db_hash = hashlib.sha256(database.read_bytes()).hexdigest()
            receipt = root / 'admission.json'
            for schema, fields, status in [
                    ('offmenu.private-incremental-source-data-admission/1',
                     {'scopeLimits': {'oldRights': False}, 'sourceAndConsumerLimits':
                      {'heldNumericContexts': 142, 'recipeNutritionTransferOrTotals': False}}, 'present'),
                    ('offmenu.private-incremental-source-data-admission/1',
                     {'sourceAndConsumerLimits': {'purpose': 'PRIVATE_ONLY', 'heldNumericContexts': 142,
                                                 'recipeNutritionTransferOrTotals': False}}, 'present'),
                    ('future/2', {'sourceAndConsumerLimits': {'rights': 'unknown'}}, 'held'),
                    ('offmenu.private-incremental-source-data-admission/1', {}, 'held'),
                    ('offmenu.private-incremental-source-data-admission/1', {'scopeLimits': []}, 'held')]:
                data = {'schemaVersion': schema, 'state': 'ACCEPTED_GENERATED_FIXTURE_ONLY',
                        'artifact': {'path': str(database), 'sha256': db_hash}, **fields}
                receipt.write_text(json.dumps(data)); sha = hashlib.sha256(receipt.read_bytes()).hexdigest()
                request = group(); request['snapshot'] = {'databaseSha256': db_hash, 'admissionSha256': sha}
                result = query_snapshot(receipt, sha, request)
                self.assertEqual(result['admissionLimits']['status'], status)
                self.assertEqual(result['admissionLimits']['sourceFields'], fields)
                self.assertEqual(result['admissionLimits']['receiptSchemaVersion'], schema)
                if status == 'held':
                    self.assertTrue(result['admissionLimits']['holdReasons'])
                    self.assertIsNone(result['admissionScopeLimits'])
                else:
                    self.assertEqual(result['admissionSourceAndConsumerLimits'], fields['sourceAndConsumerLimits'])
                    self.assertEqual(result['admissionScopeLimits'], fields.get('scopeLimits'))

    def test_selected_snapshot_wrapper_checks_bytes_and_no_sidecars(self):
        with tempfile.TemporaryDirectory(prefix='generated-menu-test-') as directory:
            root = Path(directory); database = root / 'generated.sqlite3'
            db = sqlite3.connect(database); fixture(db); db.close()
            db_hash = hashlib.sha256(database.read_bytes()).hexdigest()
            receipt = root / 'admission.json'
            receipt.write_text(json.dumps({'schemaVersion': 'offmenu.private-incremental-source-data-admission/1', 'state': 'ACCEPTED_GENERATED_TEST_FIXTURE_ONLY',
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
