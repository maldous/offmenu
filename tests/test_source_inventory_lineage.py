import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).parents[1]
SPEC = importlib.util.spec_from_file_location(
    'reconcile_source_inventory_lineage', ROOT / 'scripts/reconcile-source-inventory-lineage.py')
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class InventoryLineageTests(unittest.TestCase):
    def test_url_release_match_with_changed_checksum_is_not_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            run = root / 'run.json'
            inventory = root / 'inventory.json'
            receipt = root / 'receipt.json'
            run.write_text(json.dumps({'schemaVersion': 'offmenu-source-parse-run/1',
                'assets': [{'sourceId': 'S', 'sourceRecordId': 'r', 'kind': 'recipe',
                    'inputPath': 'same.html', 'inputSHA256': 'a' * 64, 'status': 'complete'}]}))
            receipt.write_text(json.dumps({'files': [{'path': '/elsewhere/same.html',
                'sourceURL': 'https://example.org/recipe', 'release': 'edition-1',
                'sha256': 'a' * 64}]}))
            inventory.write_text(json.dumps({'schemaVersion': 'offmenu-origin-type-coverage-register/1',
                'assets': [{'assetId': 'asset-1', 'sourceURLs': ['https://example.org/recipe'],
                    'release': ['edition-1'], 'assetIdentity': {'contentHashes': ['b' * 64]},
                    'custody': {'retainedOriginals': [{'sha256': 'b' * 64}]}}]}))
            report = MODULE.reconcile(run, inventory, [receipt])
            item = report['assets'][0]
            self.assertEqual(item['inventoryRelation'], 'exact-source-url-and-release')
            self.assertFalse(item['exactURLCandidates'][0]['contentChecksumMatch'])
            self.assertEqual(report['counts']['exactURLAndReleaseMatches'], 1)

    def test_source_family_only_is_not_forced_to_asset_match(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            run = root / 'run.json'
            inventory = root / 'inventory.json'
            receipt = root / 'receipt.json'
            run.write_text(json.dumps({'schemaVersion': 'offmenu-source-parse-run/1',
                'assets': [{'sourceId': 'S', 'sourceRecordId': 'r', 'kind': 'recipe',
                    'inputPath': 'recipe.html', 'inputSHA256': 'c' * 64, 'status': 'complete'}]}))
            receipt.write_text(json.dumps({'files': [{'path': '/elsewhere/recipe.html',
                'sourceURL': 'https://www.eatforhealth.gov.au/eating-well/healthy-recipes/one',
                'release': 'mutable-2026', 'sha256': 'c' * 64}]}))
            inventory.write_text(json.dumps({'schemaVersion': 'offmenu-origin-type-coverage-register/1',
                'assets': [{'assetId': 'other-recipe',
                    'sourceURLs': ['https://www.eatforhealth.gov.au/eating-well/healthy-recipes/two'],
                    'release': ['mutable-2026'], 'assetIdentity': {'contentHashes': ['d' * 64]},
                    'custody': {'retainedOriginals': [{'sha256': 'd' * 64}]}}]}))
            report = MODULE.reconcile(run, inventory, [receipt])
            self.assertEqual(report['assets'][0]['inventoryRelation'], 'same-source-family-only-no-asset-match')
            self.assertEqual(report['counts']['sameFamilyOnly'], 1)
            self.assertEqual(report['counts']['exactURLAndReleaseMatches'], 0)


if __name__ == '__main__':
    unittest.main()
