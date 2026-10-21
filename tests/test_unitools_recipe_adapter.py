"""Generated finite JSON only. Production source constants are patched in tests.

There is no fixture switch or alternate-source selection in the runtime API.
"""
import copy
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import patch

from offmenu.refresh import recipe_menu_store as store
from offmenu.refresh import unitools_recipe_adapter as adapter
from offmenu.refresh.core import canonical, RefreshError


def document(slugs=('fixture-a',)):
    return {'attribution': 'Generated fixture author',
        'licenseUrl': 'https://creativecommons.org/licenses/by-sa/4.0/',
        'homepage': 'https://example.invalid/fixture', 'extension/root~field': {'keep': None},
        'recipes': [{'slug': slug, 'name': {'en': 'Fixture soup', 'ru': 'Пример супа'},
            'nativeName': 'Native fixture', 'baseServings': 4,
            'country': 'ZZ', 'prepMinutes': None, 'cookMinutes': 17,
            'ingredients': [{'id': 'publisher-17', 'name': {'en': 'beans', 'ru': 'фасоль'},
                'quantity': 100, 'unit': 'g', 'scaling': {'mode': 'fixed'}, 'note': 'native note'},
                {'name': {'en': 'salt', 'ru': 'соль'}, 'quantity': None, 'unit': None}],
            'steps': [{'text': {'en': 'Mix gently.', 'ru': 'Перемешать.'}, 'time': {'native': 9}},
                      {'text': {'en': 'Serve.', 'ru': 'Подать.'}}],
            'unknown': {'nested': [True, None, 'retained']}}
            for slug in slugs]}


class UnitoolsAdapterTests(unittest.TestCase):
    def selected(self, data=None, *, raw=None, declared=None, bad_blob=False):
        if raw is None:
            raw = json.dumps(data or document(), ensure_ascii=False, indent=1).encode()
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        path = Path(directory.name) / 'generated.json'
        path.write_bytes(raw)
        blob = hashlib.sha1(b'blob ' + str(len(raw)).encode() + b'\0' + raw).hexdigest()
        count = len((data or document())['recipes']) if declared is None else declared
        changes = patch.multiple(adapter, INPUT_PATH=str(path), INPUT_BYTES=len(raw),
            IDENTITY=adapter.identity(path.stat()), BLOB_SHA1='0' * 40 if bad_blob else blob,
            BLOB_URL='https://example.invalid/blob/' + blob, DECLARED_COUNT=count)
        changes.start()
        self.addCleanup(changes.stop)
        selection = adapter.UnitoolsSelection(*[(str(path.parent / name), 'a' * 64)
            for name in ('source-use.json', 'custody.json', 'operation.json', 'coverage.json')],
            source_use_scope='generated fixture only; no actual source operation')
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
        try:
            verified = adapter.qualify_unitools_once(selection, fd)
            self.assertEqual(os.lseek(fd, 0, os.SEEK_CUR), len(raw))
        finally:
            os.close(fd)
        return verified

    def load(self, verified):
        assets = [adapter.asset_from_verified(verified)]
        manifest = store.prepare_recipe_menu(assets, accepted_source_adapter=verified)
        db = sqlite3.connect(':memory:')
        self.addCleanup(db.close)
        limits = store.StoreLimits(8 * 1024**2, 1, 1024, 16 * 1024**2, 5000, 5000,
                                   64 * 1024**2, 128 * 1024**2, 120)
        result = store.ingest_recipe_menu(db, assets, limits=limits, run_id='generated-unitools',
            input_manifest_sha256=hashlib.sha256(canonical(manifest)).hexdigest(),
            selection_receipt_sha256='b' * 64, accepted_source_adapter=verified)
        return db, result

    def test_lossless_projection_lexemes_nulls_languages_and_json_pointers(self):
        raw = json.dumps(document(), ensure_ascii=False, indent=1).encode()
        raw = raw.replace(b'"quantity": 100', b'"quantity": 1.00e+2').replace(b'"baseServings": 4', b'"baseServings": 4.00')
        verified = self.selected(raw=raw)
        records, receipt = adapter.project_unitools_source(verified)
        record, = records
        self.assertEqual(receipt['inputSHA256'], hashlib.sha256(raw).hexdigest())
        self.assertEqual(receipt['bodyPasses'], 1)
        self.assertTrue(receipt['EOFFullyVerified'])
        self.assertEqual(record['ingredientLines'][0]['quantity']['rawValueLexeme'], '1.00e+2')
        self.assertIsNone(record['ingredientLines'][1]['quantity']['rawValueLexeme'])
        self.assertIsNone(record['ingredientLines'][1]['quantity']['rawUnitLexeme'])
        self.assertEqual(record['yield']['rawText'], '4.00')
        self.assertIsNone(record['yield']['rawUnitLexeme'])
        self.assertIsNone(record['dictionaryVersion'])
        self.assertIsNone(record['mappingVersion'])
        self.assertIsNone(record['region'])
        native = next(x for x in record['sourceNotes'] if x['provenanceRole'] == 'rawNativeRecord')
        self.assertEqual(json.loads(native['originalText']), json.loads(raw)['recipes'][0])
        self.assertIn('Пример супа', native['originalText'])
        self.assertIn('Перемешать.', native['originalText'])
        self.assertEqual(native['originalExpressionRepresentation'], 'native-json-object')
        for item in [record] + record['ingredientLines'] + record['orderedSteps'] + record['sourceNotes'] + [record['yield']]:
            loc = item.get('location', item.get('sourceLocation'))
            start, end = loc['utf8ByteRange']
            self.assertEqual(loc['kind'], 'native-json')
            self.assertNotIn('page', loc)
            self.assertEqual(hashlib.sha256(raw[start:end]).hexdigest(), loc['sourceSpanSHA256'])
            current = json.loads(raw)
            for key in loc['jsonPointer'].split('/')[1:]:
                key = key.replace('~1', '/').replace('~0', '~')
                current = current[int(key)] if isinstance(current, list) else current[key]
            self.assertEqual(json.loads(raw[start:end]), current)
        ingredient = record['ingredientLines'][0]
        start, end = ingredient['location']['utf8ByteRange']
        self.assertEqual(ingredient['originalExpression'].encode(), raw[start:end])

    def test_one_buffer_has_no_source_reread_during_projection_or_import(self):
        verified = self.selected(document(('first', 'second')))
        with patch.object(adapter.os, 'read', side_effect=AssertionError('second source read')):
            records, _ = adapter.project_unitools_source(verified)
            db, result = self.load(verified)
        self.assertEqual(len(records), 2)
        self.assertEqual(result['tableCounts']['source_recipe_variant'], 2)
        self.assertEqual(db.execute('PRAGMA foreign_key_check').fetchall(), [])
        self.assertEqual(db.execute('SELECT DISTINCT dictionary_version,mapping_version,dish_concept_id FROM source_recipe_variant').fetchall(), [(None, None, None)])
        self.assertEqual(db.execute('SELECT count(*) FROM recipe_ingredient_line WHERE ingredient_concept_id IS NOT NULL').fetchone()[0], 0)

    def test_duplicate_slugs_preserve_occurrences_and_record_publication_hold(self):
        verified = self.selected(document(('repeat', 'repeat')))
        self.assertEqual(verified.receipt['observedArrayCount'], 2)
        self.assertEqual(verified.receipt['distinctNativeSlugs'], 1)
        db, result = self.load(verified)
        self.assertEqual(db.execute('SELECT native_record_id,source_ordinal FROM recipe_source_record ORDER BY source_ordinal').fetchall(), [('repeat', 1), ('repeat', 2)])
        self.assertEqual(db.execute('SELECT record_pointer FROM recipe_source_record ORDER BY source_ordinal').fetchall(), [('/recipes/0',), ('/recipes/1',)])
        self.assertEqual(result['tableCounts']['source_recipe_variant'], 2)
        self.assertEqual(result['publicationHoldReasons'], ['duplicate-native-slugs'])
        self.assertEqual(db.execute('SELECT reason_code,disposition FROM recipe_store_exception').fetchall(), [('duplicate-native-slug', 'held')])

    def test_selected_native_allows_exact_large_asset_html_cap_unchanged(self):
        data = document()
        data['padding'] = ''
        raw = json.dumps(data, ensure_ascii=False).encode()
        data['padding'] = 'x' * (2733812 - len(raw))
        verified = self.selected(data, raw=json.dumps(data, ensure_ascii=False).encode())
        self.assertEqual(len(verified.raw), 2733812)
        self.assertGreater(len(verified.raw), 2097152)
        assets = [adapter.asset_from_verified(verified)]
        with self.assertRaisesRegex(RefreshError, 'asset-binding'):
            store.prepare_recipe_menu(assets)
        manifest = store.prepare_recipe_menu(assets, accepted_source_adapter=verified)
        self.assertEqual(manifest['parserVersion'], adapter.VERSION)
        self.assertEqual(manifest['sourceAdapter']['gitBlobSHA1'], verified.git_blob_sha1)

    def test_count_mismatch_and_malformed_record_are_explicit_holds(self):
        verified = self.selected(document(), declared=501)
        self.assertEqual(verified.receipt['observedArrayCount'], 1)
        self.assertIn('declared-count-mismatch', verified.receipt['loadHoldReasons'])
        with self.assertRaisesRegex(adapter.UnitoolsError, 'load-held'):
            adapter.asset_from_verified(verified)
        data = document(('good', 'bad'))
        data['recipes'][1]['steps'] = []
        verified = self.selected(data)
        self.assertEqual(verified.receipt['heldOccurrences'], 1)
        self.assertEqual(verified.receipt['occurrences'][1]['pointer'], '/recipes/1')
        with self.assertRaisesRegex(adapter.UnitoolsError, 'load-held'):
            adapter.project_unitools_source(verified)

    def test_strict_json_rejects_duplicate_keys_nonfinite_and_trailing_bytes(self):
        for raw in (b'{"recipes":[],"recipes":[]}', b'{"x":NaN}', b'{"x":Infinity}',
                    b'{"x":-Infinity}', b'{}garbage', b'{"x":"\\ud800"}', b'\xff'):
            with self.subTest(raw=raw), self.assertRaises(adapter.UnitoolsError) as caught:
                self.selected(raw=raw)
            self.assertTrue(caught.exception.receipt['EOFFullyVerified'])

    def test_git_blob_mismatch_does_not_return_verified_input(self):
        with self.assertRaisesRegex(adapter.UnitoolsError, 'git-blob-mismatch') as caught:
            self.selected(bad_blob=True)
        self.assertEqual(caught.exception.receipt['bodyPasses'], 1)
        self.assertTrue(caught.exception.receipt['EOFFullyVerified'])

    def test_supplied_language_fallback_is_per_occurrence_and_missing_step_holds(self):
        data = document()
        data['recipes'][0]['name'].pop('en')
        verified = self.selected(data)
        record, = adapter.project_unitools_source(verified)[0]
        self.assertEqual(record['language'], 'ru')
        self.assertEqual(record['orderedSteps'][0]['originalText'], 'Перемешать.')
        data['recipes'][0]['steps'][0]['text'].pop('ru')
        verified = self.selected(data)
        with self.assertRaisesRegex(adapter.UnitoolsError, 'step-language-held') as caught:
            adapter.project_unitools_source(verified)
        self.assertEqual(caught.exception.receipt['projectionHold']['jsonPointer'], '/recipes/0/steps/0/text/ru')

    def test_native_profile_rejects_callback_asset_alias_and_foreign_code_pin(self):
        verified = self.selected()
        asset = adapter.asset_from_verified(verified)
        wrong = dict(asset, release='foreign')
        with self.assertRaisesRegex(RefreshError, 'unitools-asset-binding'):
            store.prepare_recipe_menu([wrong], accepted_source_adapter=verified)
        with patch.object(store, 'UNITOOLS_ADAPTER_SHA256', '0' * 64):
            with self.assertRaisesRegex(RefreshError, 'unitools-code-pin'):
                store.prepare_recipe_menu([asset], accepted_source_adapter=verified)
        db = sqlite3.connect(':memory:')
        try:
            with self.assertRaisesRegex(RefreshError, 'unitools-callback-unselected'):
                store.ingest_recipe_menu(db, [asset], parser_module=adapter, parse_asset_once=lambda *_: None,
                    limits=None, run_id='unselected', input_manifest_sha256='a'*64,
                    selection_receipt_sha256='b'*64, accepted_source_adapter=verified)
            self.assertEqual(db.execute('SELECT count(*) FROM sqlite_master').fetchone()[0], 0)
        finally:
            db.close()

    def test_missing_and_null_quantity_unit_remain_distinct_in_raw_payload(self):
        data = document()
        data['recipes'][0]['ingredients'][0].pop('quantity')
        data['recipes'][0]['ingredients'][0].pop('unit')
        verified = self.selected(data)
        record, = adapter.project_unitools_source(verified)[0]
        original = json.loads(record['sourceNotes'][0]['originalText'])['ingredients']
        self.assertNotIn('quantity', original[0])
        self.assertIsNone(original[1]['quantity'])
        self.assertNotIn('unit', original[0])
        self.assertIsNone(original[1]['unit'])

    def test_string_quantity_token_is_exact_and_uninterpreted(self):
        data = document()
        data['recipes'][0]['ingredients'][0]['quantity'] = '1/2'
        verified = self.selected(data)
        record, = adapter.project_unitools_source(verified)[0]
        q = record['ingredientLines'][0]['quantity']
        self.assertEqual(q['rawValueLexeme'], '"1/2"')
        self.assertIsNone(q['interpretedValue'])
        self.assertIsNone(q['interpretedUnit'])

    def test_fd_requires_readonly_nofollow_zero_offset_and_unchanged_identity(self):
        verified = self.selected()
        selection = verified.selection
        fd = os.open(adapter.INPUT_PATH, os.O_RDONLY)
        try:
            with self.assertRaisesRegex(adapter.UnitoolsError, 'input-custody'):
                adapter.qualify_unitools_once(selection, fd)
        finally:
            os.close(fd)
        fd = os.open(adapter.INPUT_PATH, os.O_RDONLY | os.O_NOFOLLOW)
        try:
            os.lseek(fd, 1, os.SEEK_SET)
            with self.assertRaisesRegex(adapter.UnitoolsError, 'input-custody'):
                adapter.qualify_unitools_once(selection, fd)
            os.lseek(fd, 0, os.SEEK_SET)
            real_read = os.read
            def altered(descriptor, extent):
                data = real_read(descriptor, extent)
                if data:
                    state = os.stat(adapter.INPUT_PATH)
                    os.utime(adapter.INPUT_PATH, ns=(state.st_atime_ns, state.st_mtime_ns + 1))
                return data
            with patch.object(adapter.os, 'read', side_effect=altered):
                with self.assertRaisesRegex(adapter.UnitoolsError, 'input-custody') as caught:
                    adapter.qualify_unitools_once(selection, fd)
            self.assertEqual(caught.exception.receipt['observedBytes'], len(verified.raw))
            self.assertFalse(caught.exception.receipt['custodyVerified'])
        finally:
            os.close(fd)


if __name__ == '__main__':
    unittest.main()
