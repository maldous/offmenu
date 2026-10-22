"""Authored metadata, not real acquisition times or source payload fixtures."""
from copy import deepcopy
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from offmenu.refresh import portfolio_w35 as w35

NOW = '2026-10-18T00:00:00Z'
FIXTURE = Path(__file__).parent / 'fixtures' / 'portfolio-w35' / 'valid-metadata.json'


def packet(binding_id='hn-ipc-table6'):
    spec = next(x for x in w35.bindings() if x['bindingId'] == binding_id)
    return {'schemaVersion': 'offmenu-w35-input-metadata/1',
            'bindingId': binding_id, 'sourceId': spec['sourceId'],
            'releaseId': spec['releaseId'], 'manifestPins': spec['manifestPins'],
            'originalAcquiredAt': '2026-10-01T00:00:00Z',
            'metadataValidatedAt': '2026-10-17T00:00:00Z',
            'inputSha256': spec['inputSha256'], 'fieldDeclarations': spec['fields']}


class PortfolioBindings(unittest.TestCase):
    def test_valid_authored_metadata_is_not_source_acceptance(self):
        p = json.loads(FIXTURE.read_text())[0]
        result = w35.assess(p, now=NOW)
        self.assertEqual(result['status'], 'metadata-ready')
        self.assertEqual(result['errors'], [])
        self.assertEqual(result['originalAcquisitionAgeSeconds'], 17 * 86400)
        self.assertEqual(result['metadataValidationAgeSeconds'], 86400)
        self.assertFalse(result['assetBytesVerified'])
        self.assertFalse(result['sourceProcessingAuthorized'])
        self.assertFalse(result['datasetAccepted'])
        self.assertEqual(w35.metadata_stage_result(result)['status'], 'succeeded')

    def test_identical_content_noop_is_clock_independent(self):
        p = packet()
        first = w35.assess(p, now=NOW)
        p['metadataValidatedAt'] = NOW
        result = w35.assess(p, now=NOW, previous_key=first['bindingKey'])
        self.assertEqual(result['status'], 'no-op')
        self.assertEqual(result['bindingKey'], first['bindingKey'])
        self.assertEqual(result['originalAcquisitionAgeSeconds'], 17 * 86400)
        self.assertEqual(w35.metadata_stage_result(result)['status'], 'reused')

    def test_missing_acquisition_time_cannot_use_http_or_validation_age(self):
        p = packet()
        p['originalAcquiredAt'] = None
        result = w35.assess(p, now=NOW)
        self.assertEqual(result['status'], 'missing-input')
        self.assertIn('original-acquisition-time-missing', result['errors'])
        self.assertIsNone(result['originalAcquisitionAgeSeconds'])

    def test_code_bound_holds_survive_well_formed_metadata(self):
        for binding in ('gy-retained-reference', 'hk-restaurant-licences',
                        'hk-cfs-reference', 'hk-cookbook-reference', 'hm-afma-reference'):
            with self.subTest(binding=binding):
                result = w35.assess(packet(binding), now=NOW)
                self.assertEqual(result['status'], 'held')
                self.assertTrue(result['holds'])
                self.assertFalse(result['sourceProcessingAuthorized'])

    def test_hold_cannot_be_cleared_by_input(self):
        p = packet('hk-cfs-reference')
        p['holds'] = []
        result = w35.assess(p, now=NOW)
        self.assertTrue(result['holds'])
        self.assertIn('metadata-shape-invalid', result['errors'])

    def test_stale_original_not_renewed_by_validation_or_noop_key(self):
        p = packet()
        p['originalAcquiredAt'] = '2026-09-18T00:00:00Z'
        p['metadataValidatedAt'] = NOW
        first = w35.assess(p, now=NOW)
        result = w35.assess(p, now=NOW, previous_key=first['bindingKey'])
        self.assertEqual(result['status'], 'stale-input')
        self.assertEqual(result['minimumReuseSeconds'], 30 * 86400)
        self.assertEqual(result['metadataValidationAgeSeconds'], 0)
        self.assertEqual(result['cacheDecision'], 'review-required-no-download')
        self.assertEqual(result['networkRequests'], 0)

    def test_under_30_day_window_never_downloads(self):
        p = packet()
        p['originalAcquiredAt'] = '2026-09-18T00:00:01Z'
        r = w35.assess(p, now=NOW)
        self.assertEqual(r['status'], 'metadata-ready')
        self.assertEqual(r['cacheDecision'], 'zero-download-reuse-window')
        self.assertEqual(r['networkRequests'], 0)

    def test_wrong_release_and_retained_pin_fail_closed(self):
        p = packet()
        p['releaseId'] = '2026-08'
        p['manifestPins'][0]['sha256'] = '0' * 64
        result = w35.assess(p, now=NOW)
        self.assertEqual(result['status'], 'malformed-input')
        self.assertIn('retained-manifest-pin-mismatch', result['errors'])
        self.assertIn('source-release-mismatch', result['errors'])

    def test_native_units_bases_and_selectors_cannot_be_guessed(self):
        p = packet()
        p['fieldDeclarations']['contribution_mom']['unit'] = 'percent'
        r = w35.assess(p, now=NOW)
        self.assertEqual(r['status'], 'malformed-input')
        self.assertIn('field-selector-contract-mismatch', r['errors'])

    def test_shared_origin_validator_is_used(self):
        with patch.object(w35, 'field_origin_errors', return_value=['field-origin-input-pin-mismatch']) as validate:
            result = w35.assess(packet(), now=NOW)
        validate.assert_called_once()
        self.assertIn('field-origin-input-pin-mismatch', result['errors'])

    def test_bad_peer_does_not_suppress_valid_packet(self):
        results = w35.diagnose(json.dumps([None, packet(), {'bindingId': 'foreign'}]).encode(), now=NOW)
        self.assertEqual([r['status'] for r in results],
                         ['malformed-input', 'metadata-ready', 'malformed-input'])

    def test_bad_json_utf8_size_and_duplicate_keys(self):
        for raw in (b'[', b'\xff', b'[{"bindingId":"a","bindingId":"b"}]',
                    b'x' * (w35.MAX_METADATA + 1), b'[NaN]'):
            self.assertEqual(w35.diagnose(raw, now=NOW)[0]['status'], 'malformed-input')

    def test_invalid_clock_order_is_not_fresh(self):
        for value in ('2026-10-19T00:00:00Z', '2026-10-01T00:00:00', 'invalid'):
            p = packet()
            p['metadataValidatedAt'] = value
            self.assertEqual(w35.assess(p, now=NOW)['status'], 'malformed-input')

    def test_no_errors_or_source_values_echoed_from_malformed_packet(self):
        secret = 'test-only-sensitive-value'
        result = w35.assess({'bindingId': secret * 100}, now=NOW)
        self.assertNotIn(secret, json.dumps(result))

    def test_cli_is_deterministic_and_offline(self):
        cmd = [sys.executable, '-B', '-m', 'offmenu.refresh.portfolio_w35',
               '--metadata', str(FIXTURE), '--now', NOW]
        a = subprocess.check_output(cmd)
        self.assertEqual(a, subprocess.check_output(cmd))
        self.assertEqual(json.loads(a)[0]['status'], 'metadata-ready')

    def test_portfolio_returns_independent_configuration(self):
        a = w35.bindings()
        a[0]['holds'].clear()
        self.assertTrue(w35.bindings()[0]['holds'])
        self.assertEqual({x['country'] for x in w35.bindings()}, {'GY', 'HK', 'HM', 'HN'})


class MetadataIngress(unittest.TestCase):
    def cli(self, path):
        result = subprocess.run(
            [sys.executable, '-B', '-m', 'offmenu.refresh.portfolio_w35',
             '--metadata', str(path), '--now', NOW],
            capture_output=True, timeout=2, check=True)
        self.assertEqual(result.stderr, b'')
        return json.loads(result.stdout)

    def test_fifo_without_writer_returns_typed_diagnostic(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'input.json'
            os.mkfifo(path)
            self.assertEqual(self.cli(path)[0]['status'], 'malformed-input')

    def test_directory_and_symlink_return_typed_diagnostic(self):
        with tempfile.TemporaryDirectory() as directory:
            self.assertEqual(self.cli(directory)[0]['status'], 'malformed-input')
            path = Path(directory) / 'input.json'
            path.symlink_to(FIXTURE.resolve())
            self.assertEqual(self.cli(path)[0]['status'], 'malformed-input')

    def test_read_uses_checked_descriptor_after_path_replacement(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'input.json'
            expected = FIXTURE.read_bytes()
            path.write_bytes(expected)
            actual_fstat = os.fstat

            def replace_after_check(descriptor):
                checked = actual_fstat(descriptor)
                path.unlink()
                os.mkfifo(path)
                return checked

            with patch.object(w35.os, 'fstat', side_effect=replace_after_check):
                self.assertEqual(w35.read_metadata(path), expected)

    def test_oversize_regular_file_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'input.json'
            path.write_bytes(b'x' * (w35.MAX_METADATA + 1))
            self.assertEqual(self.cli(path)[0]['status'], 'malformed-input')


if __name__ == '__main__':
    unittest.main()
