"""Small authored fixtures; no original PDF/CSV/archive or network access."""
from dataclasses import replace
from pathlib import Path
import copy
import json
import tempfile
import unittest
from unittest.mock import patch

from offmenu.refresh import acceptance as q
from offmenu.refresh import portfolio28 as p
from offmenu.refresh.core import RefreshError, canonical, sha


class MetadataBindingTests(unittest.TestCase):
    def setUp(self):
        self.raw = canonical({'country': 'EG', 'extent': {'records': 2}})
        self.binding = p.MetadataBinding('fixture-metadata', 'EG', 'authored-1',
            '2026-01-01T00:00:00Z', (('manifest', sha(self.raw)),),
            (('manifest', '/country', 'EG'), ('manifest', '/extent/records', 2)))

    def assess(self, binding=None, metadata=None, **kwargs):
        return p.assess_binding(binding or self.binding,
            {'manifest': self.raw} if metadata is None else metadata,
            now=kwargs.pop('now', '2026-01-02T00:00:00Z'), **kwargs)

    def test_valid_metadata_is_not_source_or_gold_admission(self):
        r = self.assess()
        self.assertEqual(r['status'], 'bound-metadata-only')
        self.assertEqual(r['errors'], [])
        self.assertTrue(r['metadataInputsVerified'])
        for key in ('sourceProcessingEnabled', 'goldAdmitted', 'countryComplete'):
            self.assertFalse(r[key])
        self.assertEqual((r['networkRequests'], r['sourceBodyReads'], r['aiCalls']), (0, 0, 0))

    def test_missing_and_held_are_distinct(self):
        self.assertEqual(self.assess(metadata={})['status'], 'missing')
        r = self.assess(replace(self.binding, holds=('existing-source-hold',)))
        self.assertEqual(r['status'], 'held')
        self.assertEqual(r['holds'], ['existing-source-hold'])
        self.assertTrue(r['metadataInputsVerified'])

    def test_stale_pin_and_release_identity_cannot_be_repaired_by_metadata(self):
        changed = canonical({'country': 'EE', 'extent': {'records': 2}})
        r = self.assess(metadata={'manifest': changed})
        self.assertEqual(r['status'], 'stale-input')
        self.assertIn('metadata-input-stale-pin', r['errors'])
        self.assertIn('metadata-selector-mismatch', r['errors'])
        self.assertFalse(r['metadataInputsVerified'])

    def test_malformed_duplicate_nonfinite_and_nested_null(self):
        for raw in (b'{"country":"EG","country":"EE"}', b'{"x":NaN}',
                    b'{"x":1e10000}', b'[]', b'not json'):
            with self.subTest(raw=raw):
                b = replace(self.binding, manifests=(('manifest', sha(raw)),))
                self.assertEqual(self.assess(b, {'manifest': raw})['status'], 'malformed')
        raw = canonical({'country': 'EG', 'extent': None})
        b = replace(self.binding, manifests=(('manifest', sha(raw)),))
        self.assertIn('metadata-selector-missing', self.assess(b, {'manifest': raw})['errors'])

    def test_boolean_does_not_satisfy_integer_selector(self):
        raw = canonical({'country': 'EG', 'extent': {'records': True}})
        b = replace(self.binding, manifests=(('manifest', sha(raw)),))
        self.assertIn('metadata-selector-mismatch', self.assess(b, {'manifest': raw})['errors'])

    def test_bounded_metadata_and_foreign_inputs(self):
        self.assertEqual(self.assess(metadata={'manifest': b' ' * (p.MAX_METADATA_BYTES + 1)})['status'], 'malformed')
        self.assertIn('unexpected-metadata-input', self.assess(metadata={'manifest': self.raw, 'foreign': b'{}'})['errors'])

    def test_30_day_boundary_and_validation_does_not_rejuvenate(self):
        self.assertEqual(self.assess(now='2026-01-30T23:59:59Z')['status'], 'bound-metadata-only')
        r = self.assess(now='2026-01-31T00:00:00Z', validated_at='2026-01-30T23:59:59Z')
        self.assertEqual(r['status'], 'stale-review-required')
        self.assertEqual(r['acquisitionAgeSeconds'], p.MIN_TTL)
        self.assertEqual(r['validationAgeSeconds'], 1)
        self.assertFalse(r['validationResetsAcquisitionAge'])
        self.assertEqual(r['networkRequests'], 0)

    def test_invalid_clocks_and_missing_acquisition(self):
        for kwargs in ({'now': '2025-12-31T00:00:00Z'}, {'now': '2026-01-02'},
                       {'validated_at': '2026-01-03T00:00:00Z'},
                       {'validated_at': '2025-12-31T23:59:59Z'}):
            self.assertEqual(self.assess(**kwargs)['status'], 'malformed')
        r = self.assess(replace(self.binding, acquired_at=None))
        self.assertEqual(r['status'], 'missing')
        self.assertIsNone(r['acquisitionAgeSeconds'])

    def test_deterministic_nonmutation_and_noop_identity(self):
        metadata = {'manifest': self.raw}; before = copy.deepcopy(metadata)
        first = self.assess(metadata=metadata, validated_at='2026-01-01T01:00:00Z')
        second = self.assess(metadata=metadata, validated_at='2026-01-02T00:00:00Z', previous=first)
        self.assertEqual(first['bindingSha256'], second['bindingSha256'])
        self.assertEqual(second['replayAction'], 'no-op')
        self.assertEqual(metadata, before)
        self.assertEqual(canonical(self.assess()), canonical(self.assess()))
        self.assertNotEqual(self.assess(replace(self.binding, release='changed'))['bindingSha256'], first['bindingSha256'])

    def test_no_files_network_or_ai_are_used_by_preflight(self):
        with patch('builtins.open', side_effect=AssertionError('file read forbidden')), \
                patch('socket.create_connection', side_effect=AssertionError('network forbidden')):
            self.assertEqual(self.assess()['status'], 'bound-metadata-only')

    def test_changed_policy_invalidates_previous_noop(self):
        previous = self.assess()
        with patch.object(p, 'POLICY_VERSION', 'owner28-metadata-only/review-change'):
            result = self.assess(previous=previous)
        self.assertNotEqual(result['bindingSha256'], previous['bindingSha256'])
        self.assertEqual(result['replayAction'], 'metadata-report-only')

    def test_owned_config_scope_pins_and_closed_source_actions(self):
        config = p.portfolio_config()
        self.assertEqual(config['baseCommit'], 'abecb99ee1125730ccbc2824b6ec49ffc5cc4302')
        self.assertEqual({b.country for b in p.bindings()}, set(p.COUNTRIES))
        result = p.assess_portfolio({}, now='2026-10-18T00:00:00Z')
        self.assertEqual(len(result['bindings']), 6)
        self.assertEqual(result['acceptedCountryTypeCells'], 0)
        self.assertFalse(result['sourceProcessingEnabled'])
        self.assertTrue(all(b.manifests for b in p.bindings()))

    def test_outer_malformed_and_extra_metadata_have_fixed_diagnostics(self):
        r = p.assess_portfolio(None, now='2026-10-18T00:00:00Z')
        self.assertEqual(r['errors'], ['portfolio-metadata-malformed'])
        self.assertTrue(all(x['status'] == 'malformed' for x in r['bindings']))
        r = p.assess_portfolio({'foreign': b'private value'}, now='2026-10-18T00:00:00Z')
        self.assertEqual(r['errors'], ['unexpected-portfolio-metadata-input'])
        self.assertNotIn('private value', json.dumps(r))


class AuthoredStagingTests(unittest.TestCase):
    def setUp(self):
        self.payload = {'fixtureOnly': True, 'country': 'EG', 'observations': [
            {'id': 'SYN:28:0001', 'literal': 'Authored observation A', 'unit': None, 'basis': None},
            {'id': 'SYN:28:0002', 'literal': 'Authored observation B', 'unit': None, 'basis': None}]}
        self.raw = canonical(self.payload)
        self.tmp = tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name); self.bundle = self.root / 'bundle'; self.bundle.mkdir()
        self.assets = []
        for name, raw in [('fixture.json', self.raw),
                          ('rights.json', b'{"scope":"authored-fixture-only"}\n'),
                          ('scope.json', b'{"ids":["SYN:28:0001","SYN:28:0002"]}\n')]:
            (self.bundle / name).write_bytes(raw)
            self.assets.append(q.Asset(name, len(raw), sha(raw)))
        self.contract = p.authored_fixture_contract(self.raw, self.assets)
        candidate, self.manifest = p.authored_fixture_manifest(self.raw, self.assets)
        self.candidate = self.root / 'candidate.jsonl'; self.candidate.write_bytes(candidate)

    def qualify(self, contract=None):
        return q.qualify(contract or self.contract, self.bundle, self.candidate,
                         self.manifest, scratch_root=self.root)

    def test_real_shared_validator_accepts_authored_staging_only(self):
        r = self.qualify()
        self.assertTrue(r['qualified'], r['errors'])
        self.assertTrue(r['fixture'])
        self.assertEqual(r['normalizedRecords'], 2)
        self.assertNotIn('productionAccepted', r)
        rows = p.render_authored_fixture(self.raw)
        self.assertEqual(rows[0]['data']['unit'], None)
        self.assertEqual(rows[0]['data']['basis'], None)
        self.assertEqual(p.authored_fixture_manifest(self.raw, self.assets)[0], self.candidate.read_bytes())

    def test_shared_validator_collects_held_rights_and_pin_errors(self):
        (self.bundle / 'fixture.json').write_bytes(b'{}')
        r = self.qualify(replace(self.contract, holds=('actual-source-hold',),
                                 permitted_operations=frozenset(('retain',))))
        self.assertFalse(r['qualified'])
        for code in ['source-held', 'operation-rights-missing', 'input-custody-mismatch']:
            self.assertIn(code, r['errors'])

    def test_field_origin_and_value_tampering_fail_independently(self):
        rows = p.render_authored_fixture(self.raw)
        row = rows[0]; row['provenance']['fieldOrigins']['/data/unit']['inputSha256'] = '0' * 64
        row['data']['unit'] = 'invented'
        errors = self.contract.semantic_validator(row)
        self.assertIn('field-origin-input-pin-mismatch', errors)
        self.assertIn('authored-fixture-source-value-mismatch', errors)

    def test_null_nested_wrong_country_and_real_source_cannot_enter_fixture(self):
        for modify in [lambda d: d.update(fixtureOnly=False),
                       lambda d: d.update(country='EE'),
                       lambda d: d.update(observations=None),
                       lambda d: d['observations'].__setitem__(0, None),
                       lambda d: d['observations'][0].update(unit='g')]:
            value = copy.deepcopy(self.payload); modify(value)
            with self.assertRaisesRegex(RefreshError, 'authored-fixture-layout-invalid'):
                p.render_authored_fixture(canonical(value))

    def test_shared_candidate_hash_and_schema_failure_not_success(self):
        self.candidate.write_bytes(b'[null]\n')
        r = self.qualify()
        self.assertFalse(r['qualified'])
        self.assertIn('candidate-custody-mismatch', r['errors'])
        self.assertIn('record-invalid', r['errors'])
        self.assertIn('expected-record-count-mismatch', r['errors'])

    def test_missing_fixture_evidence_is_local_failure_without_other_fixture_damage(self):
        (self.bundle / 'rights.json').unlink()
        r = self.qualify()
        self.assertFalse(r['qualified'])
        self.assertIn('input-inventory-mismatch', r['errors'])
        self.assertIn('input-custody-mismatch', r['errors'])
        self.assertEqual(self.candidate.read_bytes(), p.authored_fixture_manifest(self.raw, self.assets)[0])


if __name__ == '__main__':
    unittest.main()
