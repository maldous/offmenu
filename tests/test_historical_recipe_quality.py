import gzip
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class HistoricalRecipeQualityTest(unittest.TestCase):
    def test_recovery_is_bounded_cited_and_non_planning(self):
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / 'recovery'
            subprocess.run([sys.executable, str(ROOT / 'scripts/recover-historical-recipes-20261014.py'), '--output', str(output)], check=True)
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
