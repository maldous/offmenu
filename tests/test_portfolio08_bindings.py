import contextlib
import copy
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from offmenu.refresh import portfolio08_bindings as binding
from offmenu.refresh.core import canonical, sha


class Portfolio08BindingsTest(unittest.TestCase):
    NOW = '2026-10-18T00:00:00Z'

    def setUp(self):
        f = json.loads((Path(__file__).parent / 'fixtures/portfolio08-bindings/synthetic.json').read_text())
        self.policy, self.manifest, self.metadata = f['policy'], f['manifest'], f['metadata']

    def assess(self, **kwargs):
        return binding.assess(self.policy, self.manifest, metadata=self.metadata,
                              now=kwargs.pop('now', self.NOW), **kwargs)

    def replace_unit(self, value):
        # Author a different exact fixture, not an unpinned runtime repair.
        path = self.policy['inputs'][0]['path']
        raw = canonical({'observation': {'value': '12.00', 'unit': value, 'basis': 'per person-day'}})
        self.metadata[path] = raw.decode()
        pin = {'path': path, 'sha256': sha(raw), 'bytes': len(raw)}
        self.policy['inputs'] = [pin]
        self.manifest['inputs'] = [pin]
        self.policy['nativeUnit'] = self.manifest['data']['unit'] = value
        for key in self.policy['selectors']:
            self.policy['selectors'][key]['inputSha256'] = sha(raw)
            self.manifest['fieldOrigins']['/data/' + key]['inputSha256'] = sha(raw)
        self.manifest['cacheEvidence']['inputBundleSha256'] = sha(canonical({
            'sourceId': 'synthetic-owner08', 'releaseId': 'authored-v1', 'inputs': [pin]}))

    def test_valid_fixture_preserves_lexical_value_and_shared_origins(self):
        r = self.assess()
        self.assertEqual(r['status'], 'valid')
        self.assertTrue(r['inputBytesVerified'])
        self.assertEqual(r['candidate']['row']['data'],
                         {'value': '12.00', 'unit': 'kg', 'basis': 'per person-day'})
        self.assertEqual(r['sourceBodiesRead'], 0)
        self.assertEqual(r['refreshPlanner']['status'], 'unsupported-shared-interface')
        self.assertFalse(r['cacheMetadata']['operationalReuseOrRefreshQualified'])
        self.assertFalse(r['sourceAdmission'])
        self.assertFalse(r['candidate']['bodyProcessingAuthorized'])

    def test_missing_manifest_has_typed_outcome(self):
        r = binding.assess(self.policy, None, now=self.NOW)
        self.assertEqual((r['status'], r['diagnostics']),
                         ('missing', ['input-manifest-not-supplied']))

    def test_missing_metadata_bytes_does_not_claim_verified_inputs(self):
        r = binding.assess(self.policy, self.manifest, now=self.NOW)
        self.assertEqual(r['status'], 'missing')
        self.assertFalse(r['inputBytesVerified'])

    def test_missing_fields_remain_missing(self):
        del self.manifest['cacheEvidence']
        self.assertEqual(self.assess()['diagnostics'], ['missing-cacheEvidence'])

    def test_hold_wins_before_manifest_capture(self):
        self.policy['holds'] = ['HTTP403-no-retry']
        r = binding.assess(self.policy, object(), now=self.NOW, metadata=object())
        self.assertEqual(r['status'], 'held')
        self.assertEqual(r['diagnostics'], ['HTTP403-no-retry'])

    def test_real_sources_are_held_no_body_or_cache_access(self):
        with patch('socket.socket', side_effect=AssertionError('network forbidden')):
            with patch('offmenu.refresh.acquisition.CachedAcquirer.__init__',
                       side_effect=AssertionError('operational acquirer forbidden')):
                policies = binding.policies()
            results = binding.assess_many([(p, None, None) for p in policies], now=self.NOW)
        self.assertEqual(len(results), 10)
        self.assertEqual({c for p in policies for c in p['countries']}, {'AW', 'AX', 'AZ', 'BA'})
        self.assertTrue(all(r['status'] == 'held' and r['candidate'] is None for r in results))
        self.assertTrue(all(r['networkRequests'] == r['sourceBodiesRead'] == 0 for r in results))

    def test_real_binding_source_identity_distinguishes_denials(self):
        policies = binding.policies()
        roles = [p['sourceRepresentation']['evidenceRole'] for p in policies]
        self.assertEqual(roles.count('access-barrier-body'), 2)
        for p in policies:
            declaration = p['sourceRepresentation']
            self.assertEqual(len(declaration['sha256']), 64)
            self.assertGreater(declaration['bytes'], 0)
            self.assertTrue(declaration['receiptJSONPointer'].startswith('/'))
            self.assertFalse(declaration['bodyReadOrVerifiedByThisTask'])
            self.assertFalse(p['enabled'])

    def test_manifest_permission_flag_is_not_authority(self):
        self.manifest['rightsApproved'] = True
        self.assertEqual(self.assess()['status'], 'malformed')

    def test_closed_operation_is_not_opened_by_enabled_flag(self):
        self.policy['operations'] = ['extract-source-body']
        self.assertEqual(self.assess()['diagnostics'], ['metadata-operation-not-qualified'])

    def test_scope_release_country_and_type_are_exact(self):
        original = copy.deepcopy(self.manifest)
        for field, value in [('releaseId', 'other'), ('sourceId', 'other'),
                             ('countries', ['BA']), ('dataType', 'nutrition')]:
            with self.subTest(field=field):
                self.manifest = {**original, field: value}
                self.assertEqual(self.assess()['diagnostics'], ['source-release-scope-mismatch'])

    def test_unsafe_and_duplicate_metadata_pin_contract(self):
        for path in ['../raw.json', '/raw.json', 'a//b.json', 'a\\b.json']:
            with self.subTest(path=path):
                self.policy['inputs'][0]['path'] = path
                self.assertEqual(self.assess()['diagnostics'], ['binding-input-pin-contract-invalid'])

    def test_declared_input_digest_cannot_change(self):
        self.manifest['inputs'] = copy.deepcopy(self.manifest['inputs'])
        self.manifest['inputs'][0]['sha256'] = 'b' * 64
        self.assertEqual(self.assess()['diagnostics'], ['retained-manifest-pin-mismatch'])

    def test_metadata_hash_size_and_set_verified(self):
        path = next(iter(self.metadata))
        self.metadata[path] += ' '
        self.assertEqual(self.assess()['diagnostics'], ['metadata-input-bytes-mismatch'])
        self.metadata['undeclared.json'] = '{}'
        self.assertEqual(self.assess()['diagnostics'], ['metadata-input-set-mismatch'])

    def test_shared_origin_inventory_validation_is_used(self):
        del self.manifest['fieldOrigins']['/data/unit']
        r = self.assess()
        self.assertIn('field-origin-inventory-mismatch', r['diagnostics'])
        self.assertIsNone(r['candidate'])

    def test_well_formed_but_wrong_selector_is_rejected(self):
        self.manifest['fieldOrigins']['/data/value']['sourceField'] = '/another'
        self.assertEqual(self.assess()['diagnostics'], ['field-selector-mismatch:value'])

    def test_value_compared_with_pinned_metadata_not_only_origin_label(self):
        self.manifest['data']['value'] = '13.00'
        self.assertEqual(self.assess()['diagnostics'], ['metadata-field-value-mismatch:value'])

    def test_units_are_not_converted_or_guessed(self):
        self.manifest['data']['unit'] = 'g'
        self.assertEqual(self.assess()['diagnostics'], ['native-unit-or-basis-mismatch'])

    def test_explicit_unknown_unit_survives_without_admission(self):
        self.replace_unit(None)
        r = self.assess()
        self.assertEqual(r['status'], 'valid')
        self.assertIsNone(r['candidate']['row']['data']['unit'])
        self.assertEqual(r['diagnostics'], ['explicit-unknown-unit'])
        self.assertFalse(r['candidate']['goldAdmission'])

    def test_exact_thirty_day_boundary_is_stale_and_never_downloads(self):
        self.assertEqual(self.assess(now='2026-10-30T23:59:59Z')['status'], 'valid')
        r = self.assess(now='2026-10-31T00:00:00Z')
        self.assertEqual(r['status'], 'stale')
        self.assertEqual(r['cacheMetadata']['metadataAge'], '30-days-or-older')
        self.assertEqual(r['networkRequests'], 0)

    def test_validation_age_distinct_from_original_acquisition(self):
        self.manifest['cacheEvidence']['originalAcquiredAt'] = '2026-09-01T00:00:00Z'
        self.manifest['cacheEvidence']['checkedAt'] = '2026-10-17T00:00:00Z'
        r = self.assess()
        self.assertEqual(r['status'], 'valid')
        self.assertEqual(r['cacheMetadata']['acquisitionAgeSeconds'], 47 * 86400)
        self.assertEqual(r['cacheMetadata']['validationAgeSeconds'], 86400)
        self.assertFalse(r['cacheMetadata']['revalidationResetsOriginalAcquisition'])

    def test_invalid_future_and_unzoned_clocks_fail_closed(self):
        for field, value in [('checkedAt', '2026-10-19T00:00:00Z'),
                             ('originalAcquiredAt', '2026-10-19T00:00:00Z'),
                             ('checkedAt', '2026-10-01')]:
            old = copy.deepcopy(self.manifest['cacheEvidence'])
            self.manifest['cacheEvidence'][field] = value
            self.assertEqual(self.assess()['status'], 'malformed')
            self.manifest['cacheEvidence'] = old

    def test_cache_bundle_mismatch(self):
        self.manifest['cacheEvidence']['inputBundleSha256'] = 'b' * 64
        self.assertEqual(self.assess()['diagnostics'], ['cache-bundle-identity-mismatch'])

    def test_content_key_excludes_validation_age(self):
        a = self.assess()['candidate']
        self.manifest['cacheEvidence']['checkedAt'] = '2026-10-17T00:00:00Z'
        b = self.assess()['candidate']
        self.assertEqual(a, b)

    def test_duplicate_json_nonfinite_and_oversized_inputs(self):
        self.manifest['data']['value'] = 'x' * 65537
        self.assertEqual(self.assess()['status'], 'malformed')
        self.setUp()
        self.manifest['cacheEvidence']['checkedAt'] = float('nan')
        self.assertEqual(self.assess()['status'], 'malformed')
        self.setUp()
        raw = '{"observation":{"value":"12.00","value":"13.00"}}\n'
        p = self.policy['inputs'][0]
        p.update(bytes=len(raw), sha256=sha(raw.encode()))
        self.manifest['inputs'] = copy.deepcopy(self.policy['inputs'])
        self.metadata[p['path']] = raw
        self.assertEqual(self.assess()['status'], 'malformed')

    def test_one_bad_source_does_not_abort_other_diagnostics(self):
        held = {**self.policy, 'holds': ['private-no-read']}
        malformed = {**self.manifest, 'countries': ['XX']}
        stale = copy.deepcopy(self.manifest)
        stale['cacheEvidence']['originalAcquiredAt'] = '2026-09-01T00:00:00Z'
        stale['cacheEvidence']['checkedAt'] = '2026-09-01T00:00:00Z'
        r = binding.assess_many([(held, object(), object()), (self.policy, None, None),
                                (self.policy, malformed, self.metadata),
                                (self.policy, stale, self.metadata),
                                (self.policy, self.manifest, self.metadata)], now=self.NOW)
        self.assertEqual([x['status'] for x in r], ['held', 'missing', 'malformed', 'stale', 'valid'])

    def test_deterministic_replay_is_actual_file_noop(self):
        with tempfile.TemporaryDirectory() as t:
            p = Path(t) / 'candidate.json'
            self.assertEqual(binding.write_candidate(p, self.assess()), 'written')
            before = p.read_bytes(), p.stat().st_mtime_ns, p.stat().st_ino
            self.assertEqual(binding.write_candidate(p, self.assess()), 'no-op')
            self.assertEqual(before, (p.read_bytes(), p.stat().st_mtime_ns, p.stat().st_ino))
            self.assertEqual(binding.write_candidate(p, {'status': 'held'}), 'withheld')

    def test_existing_unrelated_output_is_preserved(self):
        with tempfile.TemporaryDirectory() as t:
            p = Path(t) / 'other.json'
            p.write_text('{}')
            with self.assertRaises(ValueError):
                binding.write_candidate(p, self.assess())
            self.assertEqual(p.read_text(), '{}')

    def test_cli_fixture_and_held_portfolio_with_no_socket(self):
        with patch('socket.socket', side_effect=AssertionError('network forbidden')):
            with contextlib.redirect_stdout(io.StringIO()) as output:
                self.assertEqual(binding.main(['--fixture', '--now', self.NOW]), 0)
            self.assertEqual(json.loads(output.getvalue())['results'][0]['status'], 'valid')
            with contextlib.redirect_stdout(io.StringIO()) as output:
                self.assertEqual(binding.main(['--now', self.NOW]), 2)
            self.assertTrue(all(x['status'] == 'held' for x in json.loads(output.getvalue())['results']))


if __name__ == '__main__':
    unittest.main()
