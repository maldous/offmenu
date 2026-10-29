import copy
import json
from pathlib import Path
import unittest

from offmenu.refresh.portfolio55 import assess, assess_portfolio, proposed_origin_errors

ROOT = Path(__file__).resolve().parents[1]
BINDINGS = json.loads((ROOT / 'src/offmenu/refresh/portfolio55.json').read_text())['bindings']
FIXTURES = ROOT / 'tests/fixtures/portfolio55'
REQUEST = json.loads((FIXTURES / 'valid-metadata.json').read_text())
MY = BINDINGS[-1]


class Portfolio55Tests(unittest.TestCase):
    def check_observed(self, observed, **kwargs):
        return assess(MY, observed, now=kwargs.pop('now', REQUEST['now']), **kwargs)

    def test_valid_and_replay_ignore_validation_age(self):
        observed = copy.deepcopy(REQUEST['observations']['MY'])
        first = self.check_observed(observed)
        self.assertEqual(first['status'], 'valid-metadata')
        self.assertEqual(first['refresh'], 'reuse-under-30-days')
        observed['validatedAt'] = REQUEST['now']
        again = self.check_observed(observed, previous_key=first['bindingKey'])
        self.assertEqual(again['replay'], 'no-op')
        self.assertEqual(first['notBefore'], again['notBefore'])
        self.assertEqual(again['acceptedRecords'], 0)
        self.assertTrue(again['metadataIntentOnly'])
        self.assertEqual(again['realSourceAdapter'], 'unsupported-pending-reviewed-caller')

    def test_missing_malformed_held_isolated(self):
        for value, expected in [(None, 'missing'), ([], 'invalid'), ({}, 'invalid')]:
            self.assertEqual(self.check_observed(value)['status'], expected)
        result = assess_portfolio(BINDINGS, REQUEST['observations'], now=REQUEST['now'])
        self.assertEqual([x['status'] for x in result], ['held'] * 3 + ['valid-metadata'])
        self.assertTrue(all(x['sourceBodiesRead'] == 0 for x in result))

    def test_release_pin_acquisition_changes_are_stale(self):
        for key in ['releaseId', 'sourceId', 'pins', 'originalAcquiredAt']:
            observed = copy.deepcopy(REQUEST['observations']['MY'])
            observed[key] = 'wrong'
            self.assertEqual(self.check_observed(observed)['status'], 'stale-input')

    def test_clock_boundaries_and_future_validation(self):
        observed = copy.deepcopy(REQUEST['observations']['MY'])
        before = self.check_observed(observed, now='2026-11-13T22:13:28.105749+00:00')
        boundary = self.check_observed(observed, now='2026-11-13T22:13:28.105750+00:00')
        self.assertEqual(before['refresh'], 'reuse-under-30-days')
        self.assertEqual(boundary['refresh'], 'conditional-refresh-requires-custodian-qualification')
        for clock in ['2026-10-18', 'not-a-time', '2026-10-13T00:00:00+00:00',
                      '2026-10-18T12:00:00+11:00', None]:
            self.assertEqual(self.check_observed(observed, now=clock)['status'], 'invalid')
        observed['validatedAt'] = '2027-01-01T00:00:00+00:00'
        self.assertEqual(self.check_observed(observed)['status'], 'invalid')

    def test_shared_origins_and_exact_selectors(self):
        row = json.loads((FIXTURES / 'authored-envelope.json').read_text())['row']
        self.assertEqual(proposed_origin_errors(MY, row), [])
        row['data']['sourceIndexLexeme'] = None
        self.assertEqual(proposed_origin_errors(MY, row), [])  # no null->zero conversion
        row['provenance']['fieldOrigins']['/data/sourceIndexLexeme']['sourceField'] = 'division'
        self.assertIn('binding-selector-mismatch', proposed_origin_errors(MY, row))
        row['provenance']['fieldOrigins']['/data/sourceIndexLexeme']['inputSha256'] = '0' * 64
        self.assertIn('field-origin-input-pin-mismatch', proposed_origin_errors(MY, row))
        self.assertEqual(proposed_origin_errors(BINDINGS[0], row), ['binding-held'])

    def test_no_legacy_record_implicitly_converted(self):
        self.assertTrue(proposed_origin_errors(MY, {'kind': 'StatisticalIndexObservation'}))
        self.assertEqual(proposed_origin_errors(MY, None), ['candidate-malformed'])
        self.assertEqual(proposed_origin_errors(MY, {'provenance': []}), ['candidate-malformed'])


if __name__ == '__main__':
    unittest.main()
