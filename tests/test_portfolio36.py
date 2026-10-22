"""Authored metadata fixtures only. No historic payload is opened by these tests."""
import copy
import hashlib
import json
from pathlib import Path
import socket
import tempfile
import unittest
from unittest.mock import patch

from offmenu.refresh import portfolio36 as binding
from offmenu.refresh.acceptance import (Asset, SourceContract, canonical, fingerprint,
                                       ids_digest, qualify)
from offmenu.refresh.field_provenance import field_origin_errors

FIXTURE = Path(__file__).parent / 'fixtures/portfolio36/metadata.json'
ACQUIRED = '2026-01-01T00:00:00Z'
NOW = '2026-01-02T00:00:00Z'


def config(payload):
    return {'schemaVersion': 'offmenu-portfolio36/1', 'scope': 'metadata-only', 'sources': [{
        'country': 'SV', 'domain': 'prices/baskets', 'sourceId': 'authored-sv',
        'releaseId': 'authored-fixture-v1', 'originalAcquiredAt': ACQUIRED,
        'inputs': [{'path': 'metadata.json', 'bytes': len(payload),
                    'sha256': hashlib.sha256(payload).hexdigest()}],
        'fields': {'release': {'input': 'metadata.json', 'selector': '/release',
                              'expected': 'authored-fixture-v1'},
                   'currency': {'input': 'metadata.json', 'selector': '/currency'},
                   'basis': {'input': 'metadata.json', 'selector': '/basis'}},
        'holds': [], 'payloadBlockers': ['authored-no-payload-admission']}]}


class Portfolio36Tests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.bundle = self.root / 'metadata'
        self.bundle.mkdir()
        self.payload = FIXTURE.read_bytes()
        (self.bundle / 'metadata.json').write_bytes(self.payload)
        self.config = config(self.payload)
        self.workspace = self.root / 'output'

    def evaluate(self, **kwargs):
        return binding.evaluate(self.config, self.bundle, now=kwargs.get('now', NOW))

    def test_valid_deterministic_fields_and_null_origin(self):
        a, report = self.evaluate()
        b, _ = self.evaluate()
        self.assertEqual(a, b)
        self.assertEqual(report['sources'][0]['status'], 'metadata-ready')
        row = a['records'][0]
        self.assertIsNone(row['data']['basis'])
        self.assertEqual(row['provenance']['fieldOrigins']['/data/basis']['sourceField'], '/basis')
        self.assertEqual(field_origin_errors(row, {'metadata.json': hashlib.sha256(self.payload).hexdigest()}), [])
        self.assertEqual(a['acceptedRecords'], 0)
        self.assertFalse(report['payloadProcessing'])

    def test_shared_qualification_on_authored_metadata_only(self):
        manifest, _ = self.evaluate()
        row = manifest['records'][0]
        raw = canonical([row]) + b'\n'
        candidate = self.root / 'candidate.jsonl'
        candidate.write_bytes(raw)
        for name in ('rights.json', 'scope.json'):
            (self.bundle / name).write_text('{"scope":"authored-test-only"}\n')
        assets = tuple(Asset(p.name, p.stat().st_size, hashlib.sha256(p.read_bytes()).hexdigest())
                       for p in sorted(self.bundle.iterdir()))
        schema = {'type': 'object', 'required': ['id', 'kind', 'data', 'provenance'],
                  'properties': {'kind': {'const': 'sourceInputBinding'},
                                 'data': {'type': 'object', 'required': ['release', 'currency', 'basis'],
                                          'properties': {'currency': {'const': 'USD'},
                                                         'basis': {'type': 'null'}}}}}
        schemas = {'sourceInputBinding': schema}
        policy = fingerprint(self.config)
        contract = SourceContract('authored-sv', 'authored-fixture-v1', 'metadata-fixture-only',
            ACQUIRED, assets, 1, ids_digest([row['id']]), schemas, fingerprint(schemas),
            lambda r: field_origin_errors(r, {'metadata.json': hashlib.sha256(self.payload).hexdigest()}),
            policy, next(a for a in assets if a.path == 'rights.json'),
            next(a for a in assets if a.path == 'scope.json'),
            frozenset(('retain', 'parse', 'transform')), fixture=True)
        envelope = {'sourceId': contract.source_id, 'releaseId': contract.release_id,
                    'acquiredAt': ACQUIRED, 'normalizedRecords': 1,
                    'rightsEvidenceSha256': contract.rights_evidence.sha256,
                    'scopeEvidenceSha256': contract.scope_evidence.sha256,
                    'inputFiles': [vars(a) for a in assets],
                    'candidateSha256': hashlib.sha256(raw).hexdigest(), 'candidateBytes': len(raw)}
        result = qualify(contract, self.bundle, candidate, envelope)
        self.assertTrue(result['qualified'], result)
        self.assertTrue(result['fixture'])

    def test_missing_isolated_from_healthy_peer(self):
        missing = copy.deepcopy(self.config['sources'][0])
        missing['sourceId'] = 'authored-missing'
        missing['inputs'][0]['path'] = 'missing.json'
        for field in missing['fields'].values():
            field['input'] = 'missing.json'
        self.config['sources'].append(missing)
        manifest, report = self.evaluate()
        self.assertEqual([r['status'] for r in report['sources']], ['missing', 'metadata-ready'])
        self.assertEqual(len(manifest['records']), 1)

    def test_hold_prevents_even_metadata_reads(self):
        self.config['sources'][0]['holds'] = ['explicit-no-read']
        with patch.object(binding, 'verify', side_effect=AssertionError('read under hold')):
            manifest, report = self.evaluate()
        self.assertEqual(report['sources'][0]['status'], 'held')
        self.assertEqual(manifest['metadataRecords'], 0)

    def test_malformed_json_and_duplicate_keys_fail_closed(self):
        for raw in (b'{bad', b'{"release":1,"release":2}'):
            with self.subTest(raw=raw):
                (self.bundle / 'metadata.json').write_bytes(raw)
                self.config = config(raw)
                manifest, report = self.evaluate()
                self.assertEqual(report['sources'][0]['status'], 'malformed')
                self.assertEqual(manifest['metadataRecords'], 0)

    def test_missing_selector_and_literal_drift(self):
        self.config['sources'][0]['fields']['currency']['selector'] = '/missing'
        _, report = self.evaluate()
        self.assertEqual(report['sources'][0]['errors'], ['selector-missing'])
        self.config['sources'][0]['fields']['currency']['selector'] = '/currency'
        self.config['sources'][0]['fields']['release']['expected'] = 'other-release'
        _, report = self.evaluate()
        self.assertEqual(report['sources'][0]['errors'], ['metadata-field-literal-mismatch'])

    def test_pin_mismatch_future_clock_and_non_utc(self):
        (self.bundle / 'metadata.json').write_bytes(self.payload + b' ')
        _, report = self.evaluate()
        self.assertEqual(report['sources'][0]['errors'], ['asset-checksum-mismatch'])
        (self.bundle / 'metadata.json').write_bytes(self.payload)
        _, report = self.evaluate(now='2025-12-01T00:00:00Z')
        self.assertEqual(report['sources'][0]['errors'], ['acquisition-timestamp-in-future'])
        with self.assertRaises(ValueError):
            self.evaluate(now='2026-01-02T01:00:00+01:00')

    def test_thirty_day_boundary_no_network_or_validation_age_reset(self):
        self.config['sources'][0]['validationAt'] = '2026-01-31T00:00:00Z'
        with patch.object(socket, 'create_connection', side_effect=AssertionError('network')):
            _, before = self.evaluate(now='2026-01-30T23:59:59Z')
            _, at = self.evaluate(now='2026-01-31T00:00:00Z')
        self.assertEqual(before['sources'][0]['status'], 'metadata-ready')
        self.assertEqual(at['sources'][0]['status'], 'stale-input')
        self.assertEqual(at['sources'][0]['cache']['acquisitionAgeDays'], 30)
        self.assertEqual(at['sources'][0]['cache']['sharedPlannerCapability'],
                         'unsupported-source-family')
        self.assertEqual(at['sources'][0]['cache']['cacheEligibility'],
                         'not-evaluated-no-download')
        self.assertFalse(at['sources'][0]['cache']['validationResetsAcquisitionAge'])
        self.assertEqual(at['networkRequests'], 0)

    def test_noop_across_new_validation_time_and_no_old_manifest_overwrite(self):
        first = binding.replay(self.config, self.bundle, self.workspace, now=NOW)
        self.assertEqual(first['status'], 'metadata-bindings-written')
        path = self.workspace / 'binding-manifest.json'
        old = path.read_bytes()
        stat = path.stat().st_mtime_ns
        second = binding.replay(self.config, self.bundle, self.workspace,
                                now='2026-02-01T00:00:00Z')
        self.assertEqual(second['status'], 'verified-no-op')
        self.assertEqual(path.stat().st_mtime_ns, stat)
        self.assertEqual(path.read_bytes(), old)
        (self.bundle / 'metadata.json').unlink()
        failed = binding.replay(self.config, self.bundle, self.workspace, now=NOW)
        self.assertEqual(failed['status'], 'isolated-failures')
        self.assertEqual(path.read_bytes(), old)
        self.assertFalse(failed['manifestPublished'])

    def test_path_traversal_symlink_and_workspace_overlap(self):
        self.config['sources'][0]['inputs'][0]['path'] = '../metadata.json'
        with self.assertRaises(ValueError):
            self.evaluate()
        self.config = config(self.payload)
        (self.bundle / 'metadata.json').unlink()
        (self.bundle / 'metadata.json').symlink_to(FIXTURE.resolve())
        _, report = self.evaluate()
        self.assertEqual(report['sources'][0]['errors'], ['symlink-path-rejected'])
        with self.assertRaises(ValueError):
            binding.replay(self.config, self.bundle, self.bundle / 'output', now=NOW)

    def test_invalid_source_country_domain_and_unknown_grants_never_enabled(self):
        for key, value in [('country', 'DK'), ('domain', 'invented'), ('originalAcquiredAt', None)]:
            with self.subTest(key=key):
                self.config = config(self.payload)
                self.config['sources'][0][key] = value
                with self.assertRaises(ValueError):
                    self.evaluate()

    def test_overflowed_numeric_metadata_and_extra_country_do_not_admit(self):
        raw = b'{"release":"authored-fixture-v1","currency":1e999,"basis":null}'
        (self.bundle / 'metadata.json').write_bytes(raw)
        self.config = config(raw)
        manifest, report = self.evaluate()
        self.assertEqual(report['sources'][0]['status'], 'malformed')
        self.assertEqual(manifest['metadataRecords'], 0)
        self.assertEqual(report['countryCells']['requiredCountryDomainCells'], 24)
        self.assertEqual(report['countryCells']['acceptedCountryDomainCells'], 0)


if __name__ == '__main__':
    unittest.main()
