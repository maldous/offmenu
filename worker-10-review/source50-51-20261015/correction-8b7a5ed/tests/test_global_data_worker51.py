"""Actual pinned MEXT regressions; one bounded workbook pass per test run."""
import copy
import importlib.util
import json
import unittest
from pathlib import Path

SCRIPT = Path(__file__).parents[1] / 'scripts/global-data-validation/worker-51.py'
spec = importlib.util.spec_from_file_location('japan_worker51', SCRIPT)
adapter = importlib.util.module_from_spec(spec)
spec.loader.exec_module(adapter)


class JapanActualSourceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not adapter.WORKBOOK.exists():
            raise RuntimeError('Exact retained workbook required; no synthetic fixture or network fallback')
        cls.records = adapter.read_records()
        cls.by_code = {r['foodCode']: r for r in cls.records}

    def component(self, code, component):
        return next(c for c in self.by_code[code]['components'] if c['componentCode'] == component)

    def test_real_iodine_retinol_units_and_retinol_equivalent_are_separate(self):
        iodine = self.component('09001', 'ID')
        self.assertEqual((iodine['sourceCell'], iodine['valueDecimal'], iodine['unit']), ('AH13', '2200', 'µg'))
        self.assertEqual(iodine['unitHeaderCell'], 'AH11')
        self.assertIn('μg', iodine['unitHeaderLexical'])
        retinol = self.component('13001', 'RETOL')
        rae = self.component('13001', 'VITA_RAE')
        self.assertEqual((retinol['sourceCell'], retinol['valueDecimal'], retinol['unit']), ('AL13', '51', 'µg'))
        self.assertEqual((rae['sourceCell'], rae['valueDecimal'], rae['unit']), ('AQ13', '53', 'µg'))
        self.assertNotEqual(retinol['componentCode'], rae['componentCode'])

    def test_source_trace_parentheses_missing_and_zero_remain_distinct(self):
        self.assertEqual(self.component('01001', 'VITA_RAE')['qualifier'], 'trace')
        self.assertIsNone(self.component('01001', 'VITA_RAE')['valueDecimal'])
        self.assertEqual(self.component('01001', 'PROTCAA')['sourceLexical'], '(11.3)')
        self.assertIsNone(self.component('01001', 'PROTCAA')['valueDecimal'])
        self.assertEqual(self.component('06001', 'ID')['qualifier'], 'unknown')
        self.assertEqual(self.component('01006', 'ID')['valueDecimal'], '0')
        self.assertEqual(self.component('01006', 'ID')['qualifier'], 'source-reported')

    def test_original_labels_code_and_raw_cooked_forms_do_not_join(self):
        raw, cooked = self.by_code['06001'], self.by_code['06002']
        self.assertEqual(raw['labels'], {'ja': 'アーティチョーク\u3000花らい\u3000生'})
        self.assertEqual(cooked['labels'], {'ja': 'アーティチョーク\u3000花らい\u3000ゆで'})
        self.assertEqual(raw['form']['cookingStateTokensJapanese'], ['生'])
        self.assertEqual(cooked['form']['cookingStateTokensJapanese'], ['ゆで'])
        self.assertNotEqual(raw['foodCode'], cooked['foodCode'])
        self.assertIsNone(raw['form']['canonicalCookingState'])
        self.assertEqual(self.by_code['01001']['foodCode'], '01001')
        self.assertNotIn('en', raw['labels'])
        # Actual shared-string header has phonetic annotations; display must exclude them.
        header = self.component('01001', 'PROTCAA')['labelCellsJapanese']['I4']
        self.assertIn('たんぱく質', header)
        self.assertNotIn('サンソセイシツ', header)

    def test_whole_food_discard_basis_is_not_edible_nutrient_basis(self):
        refusal = self.component('06001', 'REFUSE')
        self.assertEqual(refusal['unit'], '%')
        self.assertIn('not edible portion nutrient', refusal['basis'])
        self.assertEqual(self.by_code['06001']['basis']['portion'], 'edible')
        self.assertEqual(self.by_code['06001']['basis']['amount'], 100)

    def test_script_json_roundtrip_all_actual_records(self):
        restored = json.loads(json.dumps(self.records, ensure_ascii=False))
        self.assertEqual(len(restored), 192)
        self.assertEqual(len({r['foodCode'] for r in restored}), 192)
        for record in restored:
            self.assertEqual(adapter.roundtrip(record), record['rawCellsForRoundtrip'])
            self.assertEqual(record['source']['workbookSha256'], adapter.SHA256)
        proof = adapter.proof(restored)
        self.assertFalse(proof['admitted'])
        self.assertEqual(proof['networkBytes'], 0)
        self.assertGreater(proof['qualifierCounts']['trace'], 0)
        self.assertGreater(proof['qualifierCounts']['unknown'], 0)

    def test_record_unit_qualifier_identity_and_translation_mutations_fail(self):
        cases = []
        r = copy.deepcopy(self.by_code['09001']);r['components'][0]['unit'] = 'g';cases.append(r)
        r = copy.deepcopy(self.by_code['01001']);r['components'][0]['valueDecimal'] = '999';cases.append(r)
        r = copy.deepcopy(self.by_code['01001']);r['foodCode'] = '99999';cases.append(r)
        r = copy.deepcopy(self.by_code['01001']);r['labels']['en'] = 'invented translation';cases.append(r)
        r = copy.deepcopy(self.by_code['01001']);r['components'].pop();cases.append(r)
        r = copy.deepcopy(self.by_code['01001']);r['basis']['amount'] = 1;cases.append(r)
        for record in cases:
            with self.assertRaises(ValueError):
                adapter.roundtrip(record)

    def test_cap_and_duplicate_sheet_fail_before_source_read(self):
        with self.assertRaises(ValueError):
            adapter.read_records(Path('/does-not-exist'), 167)
        with self.assertRaises(ValueError):
            adapter.read_records(Path('/does-not-exist'), 2, ('1穀類', '1穀類'))
        with self.assertRaises(ValueError):
            adapter.read_records(Path('/does-not-exist'), 0)

    def test_independent_review_five_conflicting_provenance_probes_reject(self):
        for field, value in [('release', 'unreviewed-other-release'), ('workbookSha256', '0' * 64),
                             ('memberSha256', '0' * 64), ('sheet', 'other-worksheet'),
                             ('url', 'https://example.invalid/other')]:
            with self.subTest(field=field):
                record = copy.deepcopy(self.records[0])
                record['source'][field] = value
                with self.assertRaises(ValueError):
                    adapter.proof([record])

    def test_actual_member_header_row_and_rehashed_source_cells_are_bound(self):
        for field, value in [('member', 'xl/worksheets/sheet99.xml'), ('basisHeaderLexical', '1g'),
                             ('componentSchemaSha256', '0' * 64), ('publisher', 'other publisher')]:
            with self.subTest(field=field):
                record = copy.deepcopy(self.records[0]);record['source'][field] = value
                with self.assertRaises(ValueError):
                    adapter.proof([record])
        # A valid different worksheet's metadata must not bless the original row.
        record = copy.deepcopy(self.records[0])
        other = self.by_code['06001']['source']
        for field in ('sheet', 'member', 'memberSha256', 'componentSchemaSha256', 'basisHeaderLexical'):
            record['source'][field] = other[field]
        with self.assertRaises(ValueError):
            adapter.proof([record])
        # Self-consistent rehashed lexical data is still checked against actual bytes.
        record = copy.deepcopy(self.records[0]);row = record['source']['row']
        record['rawCellsForRoundtrip']['D' + str(row)] = 'invented Japanese label'
        record['labels']['ja'] = record['form']['originalLabel'] = 'invented Japanese label'
        record['source']['recordCellsSha256'] = adapter.digest(adapter.canonical(record['rawCellsForRoundtrip']).encode())
        with self.assertRaises(ValueError):
            adapter.proof([record])
        with self.assertRaises(ValueError):
            adapter.proof([])


if __name__ == '__main__':
    unittest.main()
