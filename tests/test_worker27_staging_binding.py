"""Authored metadata only: no retained bodies, HTTP or adapter execution."""
import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from offmenu.refresh import portfolio_worker27 as binding
from offmenu.refresh.core import RefreshError, canonical

NOW = '2026-10-18T05:00:00Z'
PIN = 'a' * 64


def synthetic():
    # Authored contract/observation, deliberately not a retained release assertion.
    contract = {
        'bindingId': 'DK:authored:fixture', 'country': 'DK',
        'sourceId': 'authored', 'releaseId': 'fixture',
        'manifest': {'path': '/not-read/fixture-manifest.json', 'sha256': PIN},
        'archiveSha256': 'b' * 64, 'types': ['nutrition'],
        'requiredRoles': ['products'], 'declaredFields': {'value': 'native_value'},
        'nativeSemantics': {'nativeUnits': 'authored g/100g', 'unknowns': []}, 'holds': [],
    }
    observation = {
        'bindingId': contract['bindingId'], 'country': 'DK', 'sourceId': 'authored',
        'releaseId': 'fixture', 'manifestSha256': PIN, 'archiveSha256': 'b' * 64,
        'originalAcquiredAt': '2026-10-17T05:00:00Z', 'checkedAt': NOW,
        'inputPins': {'authored.jsonl': PIN}, 'roles': {'products': 'authored.jsonl'},
        'countrySelector': {'path': 'country-policy.json', 'sha256': PIN},
        'rightsEvidence': {'path': 'fixture-rights.json', 'sha256': PIN},
        'originTemplate': {'data': {'value': 0}, 'provenance': {
            'sourceId': 'authored', 'releaseId': 'fixture', 'fieldOrigins': {
                '/data/value': {'kind': 'source', 'sourceId': 'authored',
                    'releaseId': 'fixture', 'inputPath': 'authored.jsonl',
                    'inputSha256': PIN, 'sourceRecordId': 'authored-1',
                    'sourceField': 'native_value'}}}},
    }
    return contract, observation, [{'sourceId': 'authored', 'releaseId': 'fixture'}]


class Worker27BindingsTests(unittest.TestCase):
    def check(self, c, o, adapters=None):
        return binding.assess_binding(c, o, NOW, adapters)

    def test_valid_is_metadata_only_and_null_zero_have_origins(self):
        c, o, a = synthetic()
        for value in (0, None):
            o['originTemplate']['data']['value'] = value
            r = self.check(c, o, a)
            self.assertEqual(r['status'], 'valid')
            self.assertFalse(r['sourceAdmission'])
            self.assertFalse(r['payloadBytesVerified'])
            self.assertFalse(r['normalizationExecuted'])
            self.assertEqual(r['networkRequests'], 0)
            self.assertEqual(r['cache']['policy'], 'reuse-only-zero-download')
        o['originTemplate']['provenance']['fieldOrigins'] = {}
        self.assertEqual(self.check(c, o, a)['status'], 'malformed')

    def test_missing_and_held_before_observation_or_adapter_lookup(self):
        c, o, a = synthetic()
        self.assertEqual(self.check(c, None, a)['status'], 'missing')
        c['holds'] = ['source-held']
        # An object that cannot be inspected demonstrates the gate order.
        with patch.object(binding, 'retained_adapters', side_effect=AssertionError('called')):
            self.assertEqual(self.check(c, object())['status'], 'held')

    def test_stale_boundary_and_revalidation_never_reset_age_or_identity(self):
        c, o, a = synthetic()
        fresh = self.check(c, o, a)
        o['originalAcquiredAt'] = '2026-09-18T05:00:00Z'  # exactly 30 days
        stale = self.check(c, o, a)
        self.assertEqual(stale['status'], 'stale')
        self.assertEqual(stale['cache']['ageSeconds'], binding.MIN_TTL)
        self.assertEqual(stale['cache']['policy'], 'stale-review-only-no-download')
        self.assertEqual(fresh['sourceIdentity'], stale['sourceIdentity'])
        o['checkedAt'] = '2026-10-18T04:59:59Z'
        self.assertEqual(self.check(c, o, a)['status'], 'stale')
        o['originalAcquiredAt'] = None
        self.assertEqual(self.check(c, o, a)['status'], 'missing')
        self.assertIsNone(self.check(c, o, a)['cache']['ageSeconds'])

    def test_identity_and_pin_mismatch_are_malformed(self):
        for key in ('bindingId', 'country', 'sourceId', 'releaseId', 'manifestSha256', 'archiveSha256'):
            c, o, a = synthetic()
            o[key] = 'wrong'
            self.assertEqual(self.check(c, o, a)['status'], 'malformed', key)

    def test_join_roles_and_native_origins_not_satisfied_by_a_manifest(self):
        c, o, a = synthetic()
        c['requiredRoles'] = ['prices', 'locations', 'proofs']
        self.assertIn('input-role-inventory-mismatch', self.check(c, o, a)['diagnostics'])
        c, o, a = synthetic()
        o['originTemplate']['provenance']['fieldOrigins']['/data/value']['inputSha256'] = 'c' * 64
        self.assertIn('field-origin-input-pin-mismatch', self.check(c, o, a)['diagnostics'])
        o.pop('countrySelector')
        self.assertIn('countrySelector-required', self.check(c, o, a)['diagnostics'])

    def test_bad_observation_shapes_are_isolated(self):
        for key, value in [('inputPins', []), ('roles', []), ('countrySelector', {'path': [], 'sha256': PIN}),
                           ('originTemplate', {'data': 2, 'provenance': {}}),
                           ('originalAcquiredAt', 2), ('checkedAt', '2026-10-18')]:
            c, o, a = synthetic()
            o[key] = value
            self.assertEqual(self.check(c, o, a)['status'], 'malformed', key)

    def test_no_future_or_naive_dates_or_traversal_pins(self):
        for key, value in [('originalAcquiredAt', '2026-10-19T05:00:00Z'),
                           ('originalAcquiredAt', '2026-10-17T05:00:00'),
                           ('checkedAt', '2026-10-16T05:00:00Z'),
                           ('inputPins', {'../source': PIN})]:
            c, o, a = synthetic()
            o[key] = value
            self.assertEqual(self.check(c, o, a)['status'], 'malformed', key)

    def test_isolation_preserves_other_binding_bytes_and_inputs(self):
        catalog = binding.read_metadata(binding.CATALOG)
        request = {'observations': []}
        before = binding.assess(catalog, request, NOW)
        untouched = copy.deepcopy(catalog)
        c = next(c for c in catalog['bindings'] if c['sourceId'] == 'off')
        request['observations'].append({'bindingId': c['bindingId'], 'country': 'wrong'})
        after = binding.assess(catalog, request, NOW)
        for old, new in zip(before['bindings'], after['bindings']):
            if old['bindingId'] != c['bindingId']:
                self.assertEqual(canonical(old), canonical(new))
        self.assertEqual(catalog, untouched)

    def test_retained_catalog_keeps_all_24_requirements_and_gates(self):
        catalog = binding.read_metadata(binding.CATALOG)
        request = binding.read_metadata(Path(__file__).parent / 'fixtures/worker27-staging/retained-metadata.json')
        # Neither assessor nor bindings follow any manifest/source references.
        with patch.object(Path, 'open', side_effect=AssertionError('unexpected body read')):
            r = binding.assess(catalog, request, NOW)
        self.assertEqual(len(r['bindings']), 13)
        self.assertEqual(len(r['countryRequirements']), 24)
        self.assertEqual({(x['country'], x['type']) for x in r['countryRequirements']},
                         {(cc, t) for cc in binding.COUNTRIES for t in binding.TYPES})
        self.assertEqual(sum(x['status'] == 'held' for x in r['bindings']), 1)
        self.assertTrue(all(x['status'] == 'missing' for x in r['bindings'] if x['sourceId'] != 'frida'))
        self.assertEqual(r['acceptedRecords'], 0)
        self.assertFalse(any(r['wholeCountryComplete'].values()))
        self.assertEqual(canonical(r), canonical(binding.assess(catalog, request, NOW)))

    def test_duplicate_unknown_id_and_untrusted_extra_fields(self):
        catalog = binding.read_metadata(binding.CATALOG)
        for observations in [[{'bindingId': 'unknown'}],
                             [{'bindingId': catalog['bindings'][0]['bindingId']}] * 2]:
            with self.assertRaises(RefreshError):
                binding.assess(catalog, {'observations': observations}, NOW)
        c, o, a = synthetic()
        o['holds'] = []
        self.assertIn('observation-unknown-fields', self.check(c, o, a)['diagnostics'])

    def test_strict_json_and_bounds(self):
        with tempfile.TemporaryDirectory() as directory:
            p = Path(directory) / 'metadata.json'
            for raw in (b'{"x":1,"x":2}', b'{"x":NaN}', b'{"x":1e999}', b'[]x', b'\xff'):
                p.write_bytes(raw)
                with self.assertRaises(RefreshError):
                    binding.read_metadata(p)
            p.write_bytes(b' ' * (binding.MAX_METADATA + 1))
            with self.assertRaises(RefreshError):
                binding.read_metadata(p)

    def test_exact_replay_and_collision_do_not_rewrite(self):
        with tempfile.TemporaryDirectory() as directory:
            p = Path(directory) / 'report.json'
            self.assertEqual(binding.write_report(p, {'a': 1}), 'created')
            mtime = p.stat().st_mtime_ns
            self.assertEqual(binding.write_report(p, {'a': 1}), 'no-op')
            self.assertEqual(p.stat().st_mtime_ns, mtime)
            with self.assertRaises(RefreshError):
                binding.write_report(p, {'a': 2})
            self.assertEqual(json.loads(p.read_bytes()), {'a': 1})
            link = Path(directory) / 'link.json'
            link.symlink_to(p)
            with self.assertRaises(RefreshError):
                binding.write_report(link, {'a': 1})

    def test_assessed_evidence_changes_prevent_false_noop(self):
        c, original, adapters = synthetic()
        original['inputPins']['other.jsonl'] = 'e' * 64
        first = self.check(c, original, adapters)
        variants = {}
        changed = copy.deepcopy(original)
        changed['inputPins']['authored.jsonl'] = 'c' * 64
        changed['originTemplate']['provenance']['fieldOrigins']['/data/value']['inputSha256'] = 'c' * 64
        variants['input-digest-and-matching-origin'] = changed
        for field in ('rightsEvidence', 'countrySelector'):
            changed = copy.deepcopy(original)
            changed[field]['sha256'] = 'd' * 64
            variants[field] = changed
        changed = copy.deepcopy(original)
        changed['roles']['products'] = 'other.jsonl'
        variants['role-mapping'] = changed
        changed = copy.deepcopy(original)
        changed['originTemplate']['provenance']['fieldOrigins']['/data/value']['sourceField'] = 'another-authored-selector'
        variants['origin-selector'] = changed
        with tempfile.TemporaryDirectory() as directory:
            p = Path(directory) / 'report.json'
            self.assertEqual(binding.write_report(p, first), 'created')
            stored = p.read_bytes()
            for label, observation in variants.items():
                with self.subTest(label=label):
                    report = self.check(c, observation, adapters)
                    self.assertEqual(report['status'], 'valid')
                    self.assertEqual(report['sourceIdentity'], first['sourceIdentity'])
                    self.assertNotEqual(report['observationEvidenceSha256'], first['observationEvidenceSha256'])
                    self.assertNotEqual(report['replayIdentity'], first['replayIdentity'])
                    with self.assertRaises(RefreshError):
                        binding.write_report(p, report)
                    self.assertEqual(p.read_bytes(), stored)
            self.assertEqual(binding.write_report(p, self.check(c, copy.deepcopy(original), adapters)), 'no-op')

    def test_evidence_identity_keeps_clocks_separate_and_holds_uninspected(self):
        c, o, a = synthetic()
        first = self.check(c, o, a)
        o['checkedAt'] = '2026-10-18T04:59:59Z'
        o['originalAcquiredAt'] = '2026-09-18T05:00:00Z'
        changed = self.check(c, o, a)
        self.assertEqual(changed['status'], 'stale')
        self.assertEqual(changed['observationEvidenceSha256'], first['observationEvidenceSha256'])
        self.assertEqual(changed['replayIdentity'], first['replayIdentity'])
        self.assertNotEqual(canonical(changed), canonical(first))
        c['holds'] = ['authored-hold']
        held = self.check(c, object(), a)
        self.assertEqual(held['status'], 'held')
        self.assertIsNone(held['observationEvidenceSha256'])
        self.assertIsNone(held['replayIdentity'])


if __name__ == '__main__':
    unittest.main()
