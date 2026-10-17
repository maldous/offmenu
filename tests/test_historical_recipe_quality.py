import gzip
import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


SCRIPT = ROOT / 'scripts/recover-historical-recipes-20261014.py'
SPEC = importlib.util.spec_from_file_location('historical_recipe_recovery', SCRIPT)
RECOVERY = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(RECOVERY)


class HistoricalRecipeQualityTest(unittest.TestCase):
    def test_recovery_is_bounded_cited_and_non_planning(self):
        # Synthetic OCR tests the output contract without claiming source admission.
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            source = directory / 'fixture_ocr.txt'
            acquisition = directory / 'acquisition.json'
            rights = directory / 'rights.json'
            lines = [''] * max(item['lines'][1] for item in RECOVERY.RECOVERIES)
            for item in RECOVERY.RECOVERIES:
                start, end = item['lines']
                excerpt = item['title'] + '\n' + '; '.join(item['ingredients'])
                if item.get('optionalClause'):
                    excerpt += '\n' + item['optionalClause']
                passage = excerpt.splitlines()
                self.assertLessEqual(len(passage), end - start + 1)
                lines[start - 1:start - 1 + len(passage)] = passage
            source.write_text('\n'.join(lines), encoding='utf8')
            acquisition.write_text(json.dumps({
                'archiveId': 'synthetic-test-only', 'title': 'Synthetic test OCR',
                'archiveLinks': ['https://example.invalid/archive'],
                'url': 'https://example.invalid/rights',
                'files': [{'url': 'https://example.invalid/fixture-ocr'}],
            }), encoding='utf8')
            rights.write_text(json.dumps({'fixture': True}), encoding='utf8')
            output = directory / 'recovery'
            with patch.object(RECOVERY, 'SOURCE', source), patch.object(RECOVERY, 'ACQUISITION', acquisition), patch.object(RECOVERY, 'RIGHTS', rights), patch.object(sys, 'argv', [str(SCRIPT), '--output', str(output)]):
                RECOVERY.main()
            self.assert_recovery(output)
            # A declared source boundary must contain its recipe title.
            source.write_text('unrelated OCR\n' * len(lines), encoding='utf8')
            with patch.object(RECOVERY, 'SOURCE', source), patch.object(RECOVERY, 'ACQUISITION', acquisition), patch.object(RECOVERY, 'RIGHTS', rights), patch.object(sys, 'argv', [str(SCRIPT), '--output', str(directory / 'rejected')]):
                with self.assertRaisesRegex(ValueError, 'recipe title not found'):
                    RECOVERY.main()

    @unittest.skipUnless(all(path.is_file() for path in (RECOVERY.SOURCE, RECOVERY.ACQUISITION, RECOVERY.RIGHTS)), 'retained local OCR archive and provenance are unavailable')
    def test_retained_source_recovery(self):
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / 'recovery'
            subprocess.run([sys.executable, str(ROOT / 'scripts/recover-historical-recipes-20261014.py'), '--output', str(output)], check=True)
            self.assert_recovery(output)

    def assert_recovery(self, output):
        manifest = json.loads((output / 'manifest.json').read_text())
        self.assertEqual(manifest['admissionMetrics']['admittedRecoveryVariants'], 5)
        self.assertEqual(manifest['admissionMetrics']['heldCandidates'], 251)
        self.assertTrue(manifest['complete'])
        self.assertEqual(manifest['expectedSourceRecords'], manifest['observedSourceRecords'])
        self.assertEqual(manifest['expectedCounts'], manifest['observedCounts'])
        self.assertEqual(manifest['partitionCoverage']['expectedPackets'], 5)
        self.assertEqual(manifest['partitionCoverage']['observedPackets'], 5)
        self.assertEqual(set(manifest['expectedCounts']), {'packets', 'resources', 'assertions', 'relations', 'translations'})
        with gzip.open(output / 'normalized.jsonl.gz', 'rt') as stream:
            rows = [json.loads(line) for line in stream]
        self.assertEqual(len(rows), 5)
        for row in rows:
            self.assertTrue(row['data']['ingredientExtractionComplete'])
            self.assertFalse(row['data']['automaticPlanningEligible'])
            self.assertIn('derivedFromOriginalHistoricalRecipeCandidate', row['data'])
            self.assertEqual(row['provenance']['license'], 'CC0-1.0')
        potato = next(row for row in rows if row['data']['name'] == 'Potato Salad')
        self.assertIn('2 tea- \nspoons mustard', [item['originalText'] for item in potato['data']['ingredients']])
        soup = next(row for row in rows if row['data']['name'] == 'Cream of Tomato Soup')
        optional = {item['name'] for item in soup['data']['ingredients'] if item['optional']}
        self.assertEqual(optional, {'finely chopped parsley', 'celery'})

if __name__ == '__main__':
    unittest.main()
