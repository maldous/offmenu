"""Authored declarations only: no source input, cache or transport operations."""
import copy
import unittest
from unittest.mock import patch

from offmenu.refresh.acquisition import MIN_TTL
from offmenu.refresh.core import RefreshError
from offmenu.refresh.retained_policy import plan_retained_input


class RetainedInputPolicyTests(unittest.TestCase):
    def setUp(self):
        self.arguments = {
            'source_id': 'et-authored-source', 'release_id': 'authored-release',
            'input_pins': {'retained/response.json': {'sha256': 'a' * 64, 'bytes': 123}},
            'policy_sha256': 'b' * 64, 'scope_sha256': 'c' * 64,
            'original_acquired_at': '2026-10-14T22:19:12.836552Z',
            'now': '2026-10-18T00:00:00Z'}

    def plan(self, **changes):
        return plan_retained_input(**{**self.arguments, **changes})

    def test_actual_source_identity_and_minimum_window_are_preserved(self):
        plan = self.plan()
        self.assertEqual(plan['identity']['sourceId'], 'et-authored-source')
        self.assertEqual(plan['identity']['releaseId'], 'authored-release')
        self.assertEqual(plan['identity']['ttlSeconds'], MIN_TTL)
        self.assertGreaterEqual(MIN_TTL, 30 * 86400)
        self.assertEqual(plan['cacheDecision'], 'reuse-retained')
        self.assertEqual(plan['replayDecision'], 'first-plan')
        self.assertGreater(plan['acquisitionAgeSeconds'], 3 * 86400)

    def test_later_validation_and_clock_do_not_reset_original_or_noop(self):
        first = self.plan()
        later = self.plan(now='2026-12-18T00:00:00Z',
                          validated_at='2026-12-18T00:00:00Z', previous_key=first['key'])
        self.assertEqual(first['key'], later['key'])
        self.assertEqual(later['replayDecision'], 'unchanged-no-op')
        self.assertEqual(later['cacheDecision'], 'revalidation-required')
        self.assertGreater(later['acquisitionAgeSeconds'], 60 * 86400)
        self.assertEqual(later['validationAgeSeconds'], 0)
        self.assertEqual(later['identity']['originalAcquiredAt'],
                         '2026-10-14T22:19:12.836552+00:00')

    def test_unknown_original_is_not_filled_from_validation(self):
        plan = self.plan(original_acquired_at=None, validated_at=self.arguments['now'])
        self.assertIsNone(plan['identity']['originalAcquiredAt'])
        self.assertIsNone(plan['acquisitionAgeSeconds'])
        self.assertEqual(plan['cacheDecision'], 'original-acquisition-time-missing')
        self.assertFalse(plan['networkAllowed'])

    def test_exact_thirty_day_boundary_and_longer_ttl(self):
        changes = {'original_acquired_at': '2026-09-18T00:00:00Z'}
        before = self.plan(**changes, now='2026-10-17T23:59:59Z')
        at = self.plan(**changes, previous_key=before['key'])
        self.assertEqual(before['cacheDecision'], 'reuse-retained')
        self.assertEqual(at['cacheDecision'], 'revalidation-required')
        self.assertEqual(at['replayDecision'], 'unchanged-no-op')
        self.assertEqual(self.plan(**changes, ttl_seconds=31 * 86400)['cacheDecision'],
                         'reuse-retained')
        for ttl in (MIN_TTL - 1, True, 30.0, None):
            with self.subTest(ttl=ttl), self.assertRaises(RefreshError):
                self.plan(ttl_seconds=ttl)

    def test_source_release_content_and_contract_changes_invalidate_noop(self):
        first = self.plan()
        changes = [
            {'source_id': 'nl-authored-source'}, {'release_id': 'other-release'},
            {'input_pins': {'retained/response.json': {'sha256': 'd' * 64, 'bytes': 123}}},
            {'input_pins': {'retained/response.json': {'sha256': 'a' * 64, 'bytes': 124}}},
            {'input_pins': {'other-logical-role': {'sha256': 'a' * 64, 'bytes': 123}}},
            {'policy_sha256': 'd' * 64}, {'scope_sha256': 'd' * 64},
            {'original_acquired_at': '2026-10-13T00:00:00Z'},
            {'ttl_seconds': MIN_TTL + 1}]
        for change in changes:
            with self.subTest(change=change):
                plan = self.plan(**change, previous_key=first['key'])
                self.assertNotEqual(plan['key'], first['key'])
                self.assertEqual(plan['replayDecision'], 'changed')

    def test_holds_remain_effective_even_with_matching_key(self):
        first = self.plan(holds=['source-use-held'])
        second = self.plan(holds=['source-use-held'], previous_key=first['key'])
        self.assertEqual(second['cacheDecision'], 'held')
        self.assertEqual(second['replayDecision'], 'held')
        self.assertFalse(second['networkAllowed'])
        self.assertFalse(second['dataAdmissionAllowed'])
        self.assertNotEqual(first['key'], self.plan()['key'])

    def test_canonical_order_and_equivalent_utc_spellings_preserve_key(self):
        pins = {**self.arguments['input_pins'], 'other-role': {'sha256': 'd' * 64, 'bytes': 1}}
        first = self.plan(input_pins=pins, holds=['second', 'first'])
        second = self.plan(input_pins=dict(reversed(list(pins.items()))),
                           holds=['first', 'second', 'first'],
                           original_acquired_at='2026-10-14T22:19:12.836552+00:00')
        self.assertEqual(first['key'], second['key'])

    def test_bad_declarations_fail_closed(self):
        changes = [{'source_id': ''}, {'release_id': None}, {'policy_sha256': 'bad'},
                   {'scope_sha256': None}, {'previous_key': 'bad'}, {'holds': 'held'},
                   {'holds': ['']}, {'input_pins': {}},
                   {'input_pins': {'role': {'sha256': 'a' * 64, 'bytes': True}}},
                   {'input_pins': {'role': {'sha256': 'a' * 64, 'bytes': 0}}},
                   {'input_pins': {'role': {'sha256': 'bad', 'bytes': 1}}},
                   {'input_pins': {'role': {'sha256': 'a' * 64, 'bytes': 1, 'extra': 1}}}]
        for change in changes:
            with self.subTest(change=change), self.assertRaises(RefreshError):
                self.plan(**change)

    def test_clocks_fail_closed_and_fixed_errors_do_not_echo_values(self):
        changes = [{'now': 'bad-private-value'}, {'now': '2026-10-18'},
                   {'now': '2026-10-18T00:00:00+01:00'},
                   {'original_acquired_at': '2027-01-01T00:00:00Z'},
                   {'validated_at': '2027-01-01T00:00:00Z'},
                   {'validated_at': '2026-01-01T00:00:00Z'}]
        for change in changes:
            with self.subTest(change=change), self.assertRaises(RefreshError) as error:
                self.plan(**change)
            self.assertNotIn('bad-private-value', str(error.exception))

    def test_no_io_no_admission_and_no_argument_mutation(self):
        before = copy.deepcopy(self.arguments)
        with patch('builtins.open', side_effect=AssertionError('file access')), \
             patch('os.open', side_effect=AssertionError('descriptor access')), \
             patch('socket.socket', side_effect=AssertionError('network access')):
            plan = self.plan()
        self.assertEqual(self.arguments, before)
        self.assertTrue(plan['requiresInputVerification'])
        self.assertFalse(plan['networkAllowed'])
        self.assertFalse(plan['dataAdmissionAllowed'])
        plan['identity']['inputPins']['retained/response.json']['bytes'] = 999
        self.assertEqual(self.arguments, before)


if __name__ == '__main__':
    unittest.main()
