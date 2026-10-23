"""Authored contracts only: no source network, corpus, HTML or PDF access."""
from copy import deepcopy
import json
from pathlib import Path
import unittest
from unittest.mock import patch

from offmenu.refresh.core import sha
from offmenu.refresh.field_provenance import field_origin_errors
from offmenu.refresh.owner20_binding import assess_country, assess_portfolio, bind_sb
from offmenu.refresh.serialization import encode_records

FIXTURE = Path(__file__).parent / 'fixtures/owner20-binding/authored-menu.json'
NOW = '2026-10-18T00:00:00Z'


class PortfolioBindingTests(unittest.TestCase):
    def setUp(self):
        self.raw = FIXTURE.read_bytes()
        self.binding = {'country': 'SB', 'state': 'derived-input-only',
                        'sourceId': 'authored-source', 'releaseId': 'authored-release',
                        'originalAcquiredAt': '2026-10-14T00:00:00Z',
                        'metadataValidatedAt': '2026-10-17T00:00:00Z',
                        'input': {'sha256': sha(self.raw)}, 'expectedItems': 2,
                        'expectedObservations': 2}

    def assess(self, raw=None, **kwargs):
        return assess_country(self.binding, now=NOW, candidate_bytes=self.raw if raw is None else raw, **kwargs)

    def test_valid_source_pointers_unknown_zero_missing_label_and_warning(self):
        rows = bind_sb(json.loads(self.raw), input_sha256=sha(self.raw), source_id='authored-source', release_id='authored-release')
        self.assertEqual(rows[0]['data']['amountDecimal'], '0.00')
        self.assertIsNone(rows[0]['data']['isoCurrency'])
        self.assertNotIn('variantLabel', rows[0]['data'])
        self.assertIsNone(rows[1]['data']['variantLabel'])
        self.assertEqual(rows[1]['data']['sourceWarnings'], ['Authored ambiguous doubled separator'])
        origin = rows[1]['provenance']['fieldOrigins']['/data/rawDisplay']
        self.assertEqual(origin['sourceField'], '/priceObservations/1/rawDisplay')
        self.assertEqual(field_origin_errors(rows[1], {'menu-normalized-candidate.json': sha(self.raw)}), [])
        self.assertEqual(encode_records(rows), encode_records(deepcopy(rows)))
        self.assertEqual(self.assess()['mappedObservations'], 2)
        self.assertEqual(self.assess()['acceptedRecords'], 0)

    def test_replay_noop_and_wrong_receipt_not_noop(self):
        first = self.assess()
        self.assertEqual(self.assess(previous=first['replay'])['decision'], 'no-op')
        self.assertEqual(self.assess(previous={'contentSha256': 'wrong'})['decision'], 'ready-for-independent-review')

    def test_missing_input(self):
        result = assess_country(self.binding, now=NOW)
        self.assertEqual(result['status'], 'missing')
        self.assertEqual(result['diagnostics'], ['derived-input-not-supplied'])

    def test_held_prevents_parse_and_other_country_keeps_running(self):
        held = {'country': 'PH', 'state': 'held', 'requirements': [{'kind': 'access-restriction', 'code': '403-no-retry'}]}
        results = assess_portfolio([held, self.binding], now=NOW, inputs={'PH': b'not-json', 'SB': self.raw})
        self.assertEqual([r['status'] for r in results], ['held', 'valid'])
        self.assertTrue(all(r['networkRequests'] == 0 for r in results))

    def test_stale_uses_acquisition_not_recent_validation_no_parse_or_fetch(self):
        self.binding['originalAcquiredAt'] = '2026-09-18T00:00:00Z'
        self.binding['metadataValidatedAt'] = NOW
        with patch('offmenu.refresh.owner20_binding.bind_sb', side_effect=AssertionError('must not parse')):
            result = self.assess()
        self.assertEqual(result['status'], 'stale-input')
        self.assertEqual(result['acquisitionAgeDays'], 30)
        self.assertEqual(result['metadataValidationAgeDays'], 0)
        self.assertEqual(result['nextOnlineStep'], 'none')

    def test_under_thirty_days_reuses_and_no_force_interface(self):
        self.binding['originalAcquiredAt'] = '2026-09-18T00:00:01Z'
        self.assertEqual(self.assess()['status'], 'valid')
        with self.assertRaises(TypeError):
            self.assess(force=True)

    def test_pin_mismatch_and_invalid_json_are_isolated(self):
        self.assertEqual(self.assess(b'{}')['diagnostics'], ['derived-input-pin-mismatch'])
        self.binding['input']['sha256'] = sha(b'{')
        self.assertEqual(self.assess(b'{')['status'], 'malformed')

    def test_duplicate_key_rejected(self):
        raw = b'{"country":"SB","country":"PA"}'
        self.binding['input']['sha256'] = sha(raw)
        self.assertEqual(self.assess(raw)['diagnostics'], ['duplicate-json-key'])

    def test_semantic_failures_not_promoted(self):
        for field, value, code in [('isoCurrency', 'SBD', 'unknown-marker-changed'),
                                   ('amountDecimal', 'NaN', 'display-decimal-invalid'),
                                   ('sourceItemId', 'absent', 'observation-item-unresolved'),
                                   ('sourceSelector', '', 'observation-source-coordinate-invalid')]:
            with self.subTest(field=field):
                candidate = json.loads(self.raw)
                candidate['priceObservations'][0][field] = value
                raw = json.dumps(candidate).encode()
                self.binding['input']['sha256'] = sha(raw)
                self.assertEqual(self.assess(raw)['diagnostics'], [code])

    def test_count_clock_and_code_identity(self):
        self.binding['expectedObservations'] = 120
        self.assertEqual(self.assess()['diagnostics'], ['inventory-count-mismatch'])
        self.binding['expectedObservations'] = 2
        self.binding['originalAcquiredAt'] = '2027-01-01T00:00:00Z'
        self.assertEqual(self.assess()['diagnostics'], ['evidence-chronology-invalid'])
        self.binding['originalAcquiredAt'] = '2026-10-14'
        self.assertEqual(self.assess()['diagnostics'], ['timestamp-invalid'])


if __name__ == '__main__':
    unittest.main()
