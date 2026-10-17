"""Actual retained TBCA index regressions; no downloaded or mirrored fixtures."""
import copy
import importlib.util
from pathlib import Path
import unittest

MODULE = Path(__file__).resolve().parents[1] / 'scripts/global-data-validation/worker-50.py'
spec = importlib.util.spec_from_file_location('tbca_worker50', MODULE)
tbca = importlib.util.module_from_spec(spec)
spec.loader.exec_module(tbca)


class RetainedTBCARegression(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Required source is deliberately not skipped: reviewers must supply the
        # exact retained snapshot/sidecar or treat source validation as blocked.
        cls.rows, cls.context = tbca.read_index()
        cls.records = [tbca.normalize_identity(row, cls.context, i + 1)
                       for i, row in enumerate(cls.rows)]
        cls.by_id = {r['source_record_id']: r for r in cls.records}

    def test_snapshot_shape_and_bounded_record_set(self):
        self.assertEqual(len(self.records), 100)
        self.assertEqual(len(self.by_id), 100)
        rows, context = tbca.read_index(limit=5)
        self.assertEqual(len(rows), 5)
        self.assertEqual(context['excluded_rows'], 95)
        self.assertEqual(context['snapshot_bytes'], 82840)

    def test_original_diacritics_and_spacing_not_folded(self):
        self.assertEqual(sum(any(ord(c) > 127 for c in r['original_name'])
                             for r in self.records), 33)
        for source, result in zip(self.rows, self.records):
            self.assertEqual(result['original_name'], source[1]['text'])
            self.assertEqual(result['original_description_clauses'], source[1]['text'].split(','))
        # An actual retained name contains double internal spaces. Replacing
        # it by a search-normalized string would lose original evidence.
        self.assertIn('  ', self.by_id['BRC0019A']['original_name'])

    def test_raw_and_cooked_rice_remain_separate_source_identities(self):
        raw = self.by_id['BRC0001A']
        cooked = self.by_id['BRC0018A']
        self.assertIn('cru', raw['food_form_evidence'])
        self.assertIn('cozido', cooked['food_form_evidence'])
        self.assertNotEqual(raw['id'], cooked['id'])
        self.assertNotEqual(raw['provenance']['original_record_url'],
                            cooked['provenance']['original_record_url'])
        self.assertIsNone(raw['nutritional_equivalence'])
        self.assertIsNone(cooked['nutritional_equivalence'])

    def test_botanical_source_typo_not_silently_corrected(self):
        # One actual source row says Orysa; another says Oryza. Preserve both
        # assertions instead of treating them as reviewed botanical identity.
        self.assertNotEqual(self.by_id['BRC0018A']['scientific_name'],
                            self.by_id['BRC0001A']['scientific_name'])

    def test_index_never_becomes_composition_or_portion(self):
        for r in self.records:
            self.assertTrue(all(v is None for v in r['composition'].values()))
            self.assertIsNone(r['batch_origin'])
            self.assertIsNone(r['provenance']['release_id'])
            self.assertIsNone(r['provenance']['licence'])
            self.assertFalse(r['corpus_admitted'])
            self.assertFalse(r['provenance']['redistribution_verified'])

    def test_conflicting_source_link_is_rejected(self):
        row = copy.deepcopy(self.rows[0])
        row[1]['hrefs'] = ['int_composicao_estatistica.php?different=record']
        with self.assertRaisesRegex(ValueError, 'conflicting record links'):
            tbca.normalize_identity(row, self.context, 1)

    def test_missing_source_code_is_not_replaced_by_food_name(self):
        row = copy.deepcopy(self.rows[0])
        row[0]['text'] = ''
        with self.assertRaisesRegex(ValueError, 'identity'):
            tbca.normalize_identity(row, self.context, 1)

    def test_pinned_source_and_resource_bounds_fail_closed(self):
        with self.assertRaisesRegex(ValueError, 'digest mismatch'):
            tbca.read_index(expected_sha256='0' * 64)
        for invalid in [0, 1001]:
            with self.assertRaises(ValueError):
                tbca.read_index(limit=invalid)

    def test_audit_exports_only_aggregates(self):
        result = tbca.audit()
        self.assertEqual(result['records_exported'], 0)
        self.assertEqual(result['composition_rows_checked'], 0)
        self.assertTrue(result['source_unchanged'])
        self.assertNotIn('records', result)
        self.assertTrue(result['names_preserved_exactly'])


if __name__ == '__main__':
    unittest.main()
