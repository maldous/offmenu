"""Owned catalogue transport checks only; no actual source metadata reads."""
import ast
from dataclasses import asdict
from pathlib import Path
import unittest
from unittest.mock import patch

from offmenu.refresh.core import canonical, sha, strict_json
from offmenu.refresh.portfolio16_binding import load_profile
from offmenu.refresh.portfolio16_catalogue import CATALOGUE

ROOT = Path(__file__).resolve().parents[1]
MIRROR_SHA256 = '60c9a77cd425355c0342328e1ef5c28ee25758c3f0f71f11d5176f06cd3cdb8c'


class CatalogueTransportTests(unittest.TestCase):
    def test_inert_literal_exactly_matches_unchanged_json_mirror(self):
        raw = (ROOT / 'config/source-bindings/portfolio16.json').read_bytes()
        self.assertEqual(sha(raw), MIRROR_SHA256)
        expected = strict_json(raw)
        module = ast.parse((ROOT / 'offmenu/refresh/portfolio16_catalogue.py').read_text())
        self.assertEqual(len(module.body), 2)
        self.assertIsInstance(module.body[0], ast.Expr)
        assignment = module.body[1]
        self.assertIsInstance(assignment, ast.Assign)
        self.assertEqual(assignment.targets[0].id, 'CATALOGUE')
        self.assertEqual(ast.literal_eval(assignment.value), expected)
        self.assertEqual(CATALOGUE, expected)
        bindings, fingerprint = load_profile()
        self.assertEqual([asdict(b) for b in bindings], expected['bindings'])
        self.assertEqual(fingerprint, sha(canonical(expected)))

    def test_each_default_load_deepcopies_nested_values(self):
        original = canonical(CATALOGUE)
        bindings, expected_key = load_profile()
        bindings[0].holds.clear()
        bindings[0].declarations['nativeUnitDeclaration'] = 'test-only-mutation'
        bindings[0].evidence['retainedStagedAsset']['sha256'] = '0' * 64
        bindings[0].evidence['countryTypeApplicability']['ingredients']['accepted'] = True
        again, actual_key = load_profile()
        self.assertEqual(canonical(CATALOGUE), original)
        self.assertEqual(actual_key, expected_key)
        self.assertEqual([asdict(b) for b in again], CATALOGUE['bindings'])

    def test_default_loader_needs_no_file_or_source_metadata_io(self):
        with patch.object(Path, 'read_bytes', side_effect=AssertionError('file read forbidden')), \
             patch.object(Path, 'open', side_effect=AssertionError('file open forbidden')), \
             patch('builtins.open', side_effect=AssertionError('file open forbidden')):
            bindings, key = load_profile()
        self.assertEqual(len(bindings), 7)
        self.assertTrue(all(b.holds for b in bindings))
        self.assertEqual(len(key), 64)


if __name__ == '__main__':
    unittest.main()
