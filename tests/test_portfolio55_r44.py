"""Narrow authored regressions for W55-R44-01/02; no retained source I/O."""
import copy
import json
from pathlib import Path
import subprocess
import sys
import unittest

from offmenu.refresh.portfolio55 import assess_portfolio, proposed_origin_errors

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / 'tests/fixtures/portfolio55'
BINDINGS = json.loads((ROOT / 'src/offmenu/refresh/portfolio55.json').read_text())['bindings']
REQUEST = json.loads((FIXTURES / 'valid-metadata.json').read_text())
ROW = json.loads((FIXTURES / 'authored-envelope.json').read_text())['row']


class Reviewer44Corrections(unittest.TestCase):
    def cli(self, request):
        run = subprocess.run([sys.executable, '-B', '-m', 'offmenu.refresh.portfolio55'],
                             input=json.dumps(request), text=True, capture_output=True,
                             cwd=ROOT, timeout=5)
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertNotIn('Traceback', run.stderr)
        result = json.loads(run.stdout)
        self.assertEqual(len(result), 4)
        self.assertTrue(all(x['acceptedRecords'] == 0 for x in result))
        return result

    def test_cli_malformed_request_containers(self):
        cases = [([], 'request-malformed'), (None, 'request-malformed')]
        for value in [[], None]:
            cases.append((dict(REQUEST, observations=value), 'request-observations-malformed'))
        for value in [['bad'], None]:
            cases.append((dict(REQUEST, previousKeys=value), 'request-previous-keys-malformed'))
        cases.append(({'now': REQUEST['now']}, 'request-observations-malformed'))
        cases.append(({'observations': REQUEST['observations']}, 'request-now-required'))
        for request, code in cases:
            with self.subTest(code=code):
                self.assertTrue(all(code in x['errors'] for x in self.cli(request)))

    def test_public_container_guard_and_country_isolation(self):
        for observations in [[], None]:
            result = assess_portfolio(BINDINGS, observations, now=REQUEST['now'])
            self.assertEqual(len(result), 4)
            self.assertIn('request-observations-malformed', result[-1]['errors'])
        result = assess_portfolio(BINDINGS, REQUEST['observations'],
                                 now=REQUEST['now'], previous_keys=['bad'])
        self.assertIn('request-previous-keys-malformed', result[-1]['errors'])
        observations = copy.deepcopy(REQUEST['observations'])
        observations['MY'] = []
        result = assess_portfolio(BINDINGS, observations, now=REQUEST['now'])
        self.assertEqual([x['status'] for x in result], ['held'] * 3 + ['invalid'])
        valid = self.cli(REQUEST)
        self.assertEqual([x['status'] for x in valid], ['held'] * 3 + ['valid-metadata'])

    def test_cli_malformed_json(self):
        run = subprocess.run([sys.executable, '-B', '-m', 'offmenu.refresh.portfolio55'],
                             input='{"now":', text=True, capture_output=True,
                             cwd=ROOT, timeout=5)
        self.assertEqual(run.returncode, 0)
        self.assertNotIn('Traceback', run.stderr)
        result = json.loads(run.stdout)
        self.assertEqual(len(result), 4)
        self.assertTrue(all('request-malformed' in x['errors'] for x in result))

    def test_physical_row_identity_and_positive_controls(self):
        self.assertEqual(proposed_origin_errors(BINDINGS[-1], ROW), [])
        for field in ['sourceDate', 'sourceDivision', 'sourceIndexLexeme']:
            row = copy.deepcopy(ROW)
            row['provenance']['fieldOrigins']['/data/' + field]['sourceRecordId'] = 'authored-fixture-row-2'
            self.assertIn('binding-source-row-mismatch', proposed_origin_errors(BINDINGS[-1], row))
        row = copy.deepcopy(ROW)
        origin = row['provenance']['fieldOrigins']['/data/sourceIndexLexeme']
        origin['sourceField'] = 'division'
        self.assertIn('binding-selector-mismatch', proposed_origin_errors(BINDINGS[-1], row))
        origin['inputSha256'] = '0' * 64
        self.assertIn('field-origin-input-pin-mismatch', proposed_origin_errors(BINDINGS[-1], row))


if __name__ == '__main__':
    unittest.main()
