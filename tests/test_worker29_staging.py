import copy
from dataclasses import replace
from pathlib import Path
import unittest
from unittest.mock import patch

from offmenu.refresh.core import canonical, sha
from offmenu.refresh.portfolios.worker29 import BINDINGS, Binding, stage_metadata

FIXTURE = Path(__file__).parent / 'fixtures/worker29/retained-metadata.json'
NOW = '2026-10-18T00:00:00+00:00'


class Worker29StagingTests(unittest.TestCase):
    def setUp(self):
        self.raw = FIXTURE.read_bytes()
        self.binding = Binding('authored-fixture', 'FO', 'metadata-test', 'fixture-source',
            'fixture-release', 'authored-fixture.json', sha(self.raw), None,
            (('slots', '/counts/slots'), ('zero', '/counts/zero'),
             ('unknown', '/counts/unknown'), ('selector', '/selector')),
            '2026-09-01T00:00:00+00:00')

    def stage(self, raw='fixture', **kwargs):
        return stage_metadata(self.binding, self.raw if raw == 'fixture' else raw,
                              now=NOW, **kwargs)

    def test_valid_exact_metadata_and_origins_preserve_zero_null(self):
        result = self.stage()
        self.assertEqual(result['status'], 'ready-metadata')
        data = result['projection']['data']
        self.assertEqual(data, {'slots': 3, 'zero': 0, 'unknown': None,
                               'selector': 'table:nth-of-type(1) > tr:nth-of-type(2)'})
        origins = result['projection']['provenance']['fieldOrigins']
        self.assertEqual(origins['/data/unknown']['sourceField'], '/counts/unknown')
        self.assertEqual(result['admittedRecords'], 0)

    def test_missing(self):
        self.assertEqual(self.stage(None)['diagnostics'], ['metadata-missing'])

    def test_held_has_no_projection_even_valid_input(self):
        self.assertEqual(self.stage(holds=('source-use-hold',))['status'], 'held')
        self.assertIsNone(self.stage(holds=('source-use-hold',))['projection'])
        self.binding = replace(self.binding, stage_holds=('permission-denied',))
        self.assertEqual(self.stage()['stageHolds'], ['permission-denied'])

    def test_malformed_duplicate_and_nonfinite(self):
        for raw in (b'{', b'{"x":1,"x":2}', b'{"x":NaN}', b'\xff'):
            with self.subTest(raw=raw):
                self.assertIn('malformed-metadata', self.stage(raw)['diagnostics'])
                self.assertIsNone(self.stage(raw)['projection'])

    def test_stale_pin_never_partial_projection(self):
        result = self.stage(self.raw + b' ')
        self.assertEqual(result['diagnostics'], ['stale-input-pin-mismatch'])
        self.assertIsNone(result['projection'])

    def test_missing_selector_fails_whole_projection(self):
        self.binding = replace(self.binding, selectors=self.binding.selectors + (('missing', '/missing'),))
        self.assertEqual(self.stage()['diagnostics'], ['metadata-selector-missing'])
        self.assertIsNone(self.stage()['projection'])

    def test_changed_selector_changes_replay_identity(self):
        first = self.stage()
        self.assertEqual(self.stage(previous_receipt=first['receiptSha256'])['status'], 'no-op')
        self.binding = replace(self.binding, selectors=(('zero', '/counts/zero'),))
        self.assertEqual(self.stage(previous_receipt=first['receiptSha256'])['status'], 'ready-metadata')

    def test_recent_validation_cannot_reset_original_age_or_fingerprint(self):
        first = self.stage()
        newer = self.stage(validation_at=NOW, previous_receipt=first['receiptSha256'])
        self.assertEqual(newer['status'], 'no-op')
        self.assertEqual(newer['acquisitionAgeSeconds'], 47 * 86400)
        self.assertEqual(newer['validationAgeSeconds'], 0)
        self.assertEqual(newer['cacheDecision'], 'shared-pure-planner-required')

    def test_unknown_original_time_stays_unknown(self):
        self.binding = replace(self.binding, original_acquired_at=None)
        self.assertIsNone(self.stage(validation_at=NOW)['acquisitionAgeSeconds'])

    def test_time_errors_block(self):
        for value in ('bad', '2026-10-19T00:00:00Z', '2026-01-01T00:00:00Z'):
            self.assertEqual(self.stage(validation_at=value)['status'], 'invalid')
        self.binding = replace(self.binding, original_acquired_at='2027-01-01T00:00:00Z')
        self.assertIn('acquisition-in-future', self.stage()['diagnostics'])

    def test_size_and_type_bounds(self):
        for raw in (b' ' * (1024 * 1024 + 1), {}, 1):
            self.assertIn('metadata-invalid-or-too-large', self.stage(raw)['diagnostics'])

    def test_shared_origin_validator_failure_is_not_ignored(self):
        with patch('offmenu.refresh.portfolios.worker29.field_origin_errors', return_value=['origin-test-error']):
            self.assertEqual(self.stage()['diagnostics'], ['origin-test-error'])

    def test_deterministic_no_input_mutation_no_io(self):
        original = copy.deepcopy(self.binding)
        # Public function receives bytes and has no path-opening interface.
        with patch('builtins.open', side_effect=AssertionError('unexpected file access')):
            self.assertEqual(canonical(self.stage()), canonical(self.stage()))
        self.assertEqual(self.binding, original)

    def test_portfolio_has_exact_four_countries_and_independent_pins(self):
        self.assertEqual({b.country for b in BINDINGS.values()}, {'FO', 'ET', 'FK', 'FM'})
        self.assertEqual(len({b.manifest_sha256 for b in BINDINGS.values()}), 4)
        self.assertTrue(all(b.downstream_holds for b in BINDINGS.values()))


if __name__ == '__main__':
    unittest.main()
