"""Product wrapper contracts using authored, offline CIQUAL fixtures only."""
import contextlib
import copy
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from offmenu.refresh import core, native_ciqual, survey
from offmenu.refresh.__main__ import main
from offmenu_ciqual import source_native as native
from test_ciqual_source_native import fixture


class NativeWrapperTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.blobs, cls.contract = fixture()

    def receipt(self):
        count = native.contract()['survey']['reconciliation']['intersection']
        return {
            'schemaVersion': native_ciqual.SCHEMA,
            'status': 'private-source-native-extracted',
            'buildKey': 'a' * 64,
            'inputBundleSha256': core.sha(core.canonical(native._pins())),
            'counts': {'raw': count, 'extracted': count, 'accepted': None,
                       'sourceColumns': 84, 'sourceQuantityColumns': 74,
                       'infoodsRows': 75, 'duplicates': 0, 'excluded': 0,
                       'quarantined': 0, 'qualifiers': {'numeric': count * 74}},
            'created': True,
            'artifacts': {name: {'bytes': 100, 'sha256': 'b' * 64}
                          for name in native.OUTPUT_FILES},
            'inputPinsVerified': True, 'readOnlyViewVerified': True,
            'sourceContentsUploaded': False, 'sourceCopies': 0,
            'downloads': 0, 'sourceWrites': 0, 'acceptance': 'not-performed',
            'publicExport': 'not-enabled', 'countryCoverageComplete': False,
            'freshness': 'unknown', 'originalAcquiredAt': None,
            'minimumReuseDays': 30,
        }

    def test_selected_output_is_stable_and_runtime_qualified(self):
        with patch.object(native_ciqual, 'runtime', return_value={'python': 'first'}):
            first = native_ciqual.selected_output('a' * 40)
            self.assertEqual(first, native_ciqual.selected_output('a' * 40))
        self.assertEqual(first.parent, survey.OUTPUT)
        self.assertRegex(first.name, r'^ciqual-source-native-a{40}-[0-9a-f]{16}$')
        with patch.object(native_ciqual, 'runtime', return_value={'python': 'different'}):
            self.assertNotEqual(first, native_ciqual.selected_output('a' * 40))
        self.assertNotEqual(first, native_ciqual.selected_output('b' * 40))

    def test_selected_output_rejects_unsafe_or_unpinned_names(self):
        for value in ('../private', '/tmp/private', 'A' * 40, 'a' * 39,
                      'a' * 40 + '\n', '', None, True, 123):
            with self.subTest(value=value):
                with self.assertRaisesRegex(core.RefreshError, '^trusted-code-sha-not-configured$'):
                    native_ciqual.selected_output(value)

    def test_closed_receipt_rejects_records_paths_and_false_claims(self):
        good = self.receipt()
        clean = native_ciqual.sanitize_receipt(good)
        self.assertEqual(clean, good)
        self.assertIsNot(clean, good)
        bad_values = []
        for key, value in (('foodRows', ['PRIVATE']), ('acceptance', 'accepted'),
                           ('sourceContentsUploaded', True),
                           ('inputBundleSha256', 'c' * 64), ('created', 1)):
            bad = copy.deepcopy(good)
            bad[key] = value
            bad_values.append(bad)
        bad = copy.deepcopy(good)
        bad['counts']['raw'] = True
        bad_values.append(bad)
        bad = copy.deepcopy(good)
        bad['counts']['qualifiers']['PRIVATE'] = 1
        bad_values.append(bad)
        bad = copy.deepcopy(good)
        bad['artifacts']['/tmp/private'] = {'bytes': 1, 'sha256': 'b' * 64}
        bad_values.append(bad)
        for index, bad in enumerate(bad_values):
            with self.subTest(case=index):
                with self.assertRaisesRegex(core.RefreshError, '^native-receipt-invalid$'):
                    native_ciqual.sanitize_receipt(bad)

    def test_cli_source_failures_emit_fixed_diagnostics(self):
        for message, expected in (
                ('selected-hash-mismatch', 'selected-hash-mismatch'),
                ('PRIVATE /tmp/source/path', 'operation-failed-inspect-local-state')):
            with self.subTest(message=message):
                with patch.object(native, 'build_selected', side_effect=survey.SurveyError(message)), \
                        contextlib.redirect_stdout(io.StringIO()) as out:
                    code = main(['candidate-ciqual-selected', '--output',
                                 str(survey.OUTPUT / 'ciqual-source-native-test')])
                self.assertEqual(code, 2)
                result = json.loads(out.getvalue())
                self.assertEqual(set(result), {'schemaVersion', 'status', 'errorCode', 'operationId'})
                self.assertEqual(result['schemaVersion'], 'offmenu-refresh-error/1')
                self.assertEqual(result['status'], 'failed')
                self.assertEqual(result['errorCode'], expected)
                self.assertNotIn('PRIVATE', out.getvalue())
                self.assertNotIn('/tmp/source/path', out.getvalue())

    def test_actual_fixture_cli_retry_is_private_and_identical(self):
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary)
            by_path = {entry[0]: self.blobs[name] for name, entry in survey.ASSETS.items()}

            def read(cache, relative, size, digest):
                self.assertEqual(cache, survey.CACHE)
                return by_path[relative]

            receipts = []
            with patch.object(native.os, 'geteuid', return_value=1000), \
                    patch.object(survey, 'OUTPUT', output), \
                    patch.object(survey, '_read_asset', side_effect=read) as reads, \
                    patch.object(native, 'contract', return_value=copy.deepcopy(self.contract)), \
                    patch.object(native, '_pins', return_value=copy.deepcopy(self.contract['inputPins'])):
                destination = native_ciqual.selected_output('a' * 40)
                for _ in range(2):
                    with contextlib.redirect_stdout(io.StringIO()) as out:
                        code = main(['candidate-ciqual-selected', '--output', str(destination)])
                    self.assertEqual(code, 0, out.getvalue())
                    receipts.append(json.loads(out.getvalue()))
                self.assertEqual(reads.call_count, 18)
            first, repeated = receipts
            self.assertTrue(first['created'])
            self.assertFalse(repeated['created'])
            self.assertEqual({**first, 'created': False}, repeated)
            self.assertEqual(first['counts']['extracted'], 2)
            self.assertEqual(first['acceptance'], 'not-performed')
            self.assertEqual(first['publicExport'], 'not-enabled')
            self.assertFalse(first['sourceContentsUploaded'])
            self.assertEqual(first['sourceCopies'], 0)
            self.assertFalse(first['countryCoverageComplete'])
            for marker in ('Authored food', 'Aliment invent', str(output)):
                self.assertNotIn(marker, json.dumps(receipts))
            self.assertEqual({path.name for path in output.iterdir()},
                             {destination.name, '.ciqual-source-native.lock'})
            self.assertEqual({path.name for path in destination.iterdir()}, set(native.OUTPUT_FILES))


if __name__ == '__main__':
    unittest.main()
