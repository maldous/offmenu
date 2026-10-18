"""Focused regressions for reviewer38 R1/R2; authored metadata/cells only."""
from dataclasses import replace
from pathlib import Path
import unittest

from offmenu.refresh.core import RefreshError, sha
from offmenu.refresh.owner49_staging import (
    InputPin, MetadataBinding, assess_metadata, assess_portfolio, stage_authored_fixture,
)

NOW = '2026-10-18T00:00:00Z'


class Review38CorrectionTests(unittest.TestCase):
    def setUp(self):
        root = Path(__file__).parent / 'fixtures/owner49_staging'
        self.raw = (root / 'manifest.json').read_bytes()
        self.cells = (root / 'cells.json').read_bytes()
        self.binding = MetadataBinding(
            'owner49-authored-fixture', 'fixture-1', 'FI', 'reference', sha(self.raw),
            (InputPin('cells.json', sha(self.cells), len(self.cells)),),
            (('/data/amount', 'amount'), ('/data/unit', 'unit'),
             ('/data/basis', 'basis'), ('/data/unknown', 'unknown')),
            ('g',), 'authored-per-100g', fixture=True)
        self.envelope = (self.binding, self.raw, None)

    def test_r1_bad_envelope_and_mixed_names_preserve_valid_peer(self):
        for bad in [(), (self.binding,), 'abc', {'a': 1, 'b': 2, 'c': 3}]:
            with self.subTest(envelopeType=type(bad).__name__):
                result = assess_portfolio({'good': self.envelope, 'bad': bad}, validated_at=NOW)
                self.assertEqual(result['good']['status'], 'valid')
                self.assertEqual(result['bad']['code'], 'request-envelope-invalid')
        result = assess_portfolio({'good': self.envelope, 7: self.envelope,
                                   '__invalid_request_0': self.envelope}, validated_at=NOW)
        self.assertEqual(result['good']['status'], 'valid')
        self.assertEqual(result['__invalid_request_0']['status'], 'valid')
        self.assertEqual(result['__invalid_request_1']['code'], 'request-name-invalid')
        self.assertTrue(all(isinstance(key, str) for key in result))
        reversed_requests = dict(reversed(list({'good': self.envelope, 7: self.envelope,
                                              '__invalid_request_0': self.envelope}.items())))
        self.assertEqual(result, assess_portfolio(reversed_requests, validated_at=NOW))

    def test_r1_nonmapping_and_excess_size_have_fixed_public_errors(self):
        for value in [None, [], 'bad']:
            with self.assertRaisesRegex(RefreshError, '^portfolio-requests-invalid$'):
                assess_portfolio(value, validated_at=NOW)
        with self.assertRaisesRegex(RefreshError, '^portfolio-request-limit$'):
            assess_portfolio({str(i): self.envelope for i in range(17)}, validated_at=NOW)

    def test_r2_fixture_discriminator_requires_actual_boolean_before_cells(self):
        for value in ['false', 'true', 0, 1, None, [], {}]:
            with self.subTest(discriminatorType=type(value).__name__):
                binding = replace(self.binding, fixture=value)
                self.assertEqual(assess_metadata(binding, self.raw, validated_at=NOW)['status'],
                                 'malformed')
                with self.assertRaisesRegex(RefreshError, '^authored-fixture-required$'):
                    stage_authored_fixture(binding, self.raw, object(), validated_at=NOW)
        # Actual False is a valid metadata declaration but never a fixture grant.
        binding = replace(self.binding, fixture=False)
        self.assertEqual(assess_metadata(binding, self.raw, validated_at=NOW)['status'], 'valid')
        with self.assertRaisesRegex(RefreshError, '^authored-fixture-required$'):
            stage_authored_fixture(binding, self.raw, object(), validated_at=NOW)

    def test_r2_units_require_typed_tuple_and_reject_before_cells(self):
        for value in [None, 'g', ['g'], (None,), (1,), ('',)]:
            with self.subTest(unitContainerType=type(value).__name__):
                binding = replace(self.binding, native_units=value)
                self.assertEqual(assess_metadata(binding, self.raw, validated_at=NOW)['code'],
                                 'binding-invalid')
                with self.assertRaisesRegex(RefreshError, '^fixture-metadata-not-valid$'):
                    stage_authored_fixture(binding, self.raw, object(), validated_at=NOW)
        self.assertEqual(assess_metadata(replace(self.binding, native_units=()), self.raw,
                                        validated_at=NOW)['status'], 'valid')

    def test_unchanged_positive_fixture_hold_clock_and_replay_controls(self):
        first = assess_metadata(self.binding, self.raw, validated_at=NOW)
        self.assertEqual(first['status'], 'valid')
        self.assertEqual(assess_metadata(self.binding, self.raw, validated_at=NOW,
                                        previous_key=first['replayKey'])['status'], 'no-op')
        stale = assess_metadata(self.binding, self.raw, validated_at='2026-11-01T00:00:00Z',
                                previous_key=first['replayKey'])
        self.assertEqual(stale['status'], 'stale-input')
        self.assertEqual(stale['originalAcquiredAt'], first['originalAcquiredAt'])
        self.assertEqual(assess_metadata(replace(self.binding, holds=('held',)), self.raw,
                                        validated_at=NOW)['status'], 'held')
        self.assertTrue(stage_authored_fixture(self.binding, self.raw, self.cells, validated_at=NOW))


if __name__ == '__main__':
    unittest.main()
