"""Authored receipt fixtures only; historical dataset bodies are never opened."""
import copy
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from offmenu.refresh import portfolio48 as lane
from offmenu.refresh.acceptance import Asset, SourceContract, fingerprint, ids_digest, qualify
from offmenu.refresh.core import canonical, sha
from offmenu.refresh.field_provenance import field_origin_errors

FIXTURES = Path(__file__).parent / 'fixtures' / 'portfolio48'
NOW = datetime(2026, 9, 21, tzinfo=timezone.utc)


def authored_spec(raw=None):
    raw = raw if raw is not None else (FIXTURES / 'receipt.json').read_bytes()
    spec = copy.deepcopy(lane.registry()['sources'][0])
    spec.update(sourceId='authored-portfolio48', country='EC',
                releaseKey='AUTHORED-RECEIPT-1', sourceDataHolds=[],
                applicability={'status': 'authored-fixture-only'})
    spec['metadata'] = {'name': 'receipt.json', 'bytes': len(raw), 'sha256': sha(raw),
                        'custodyLocator': 'authored fixture; never a raw source'}
    spec['fields'] = {
        'releaseLabel': {'selector': '/release', 'expected': 'AUTHORED-RECEIPT-1'},
        'sourceStatus': {'selector': '/status'},
        'declaredAssetSha256': {'selector': '/asset/sha256'},
        'declaredAssetBytes': {'selector': '/asset/bytes'},
        'nativeUnit': {'selector': '/nativeUnit'},
        'nativeBasis': {'selector': '/nativeBasis'},
        'originalAcquiredAt': {'selector': '/acquiredAt'},
        'validationObservedAt': {'selector': '/validatedAt'},
        'zero': {'selector': '/zero'}, 'unknown': {'selector': '/unknown'},
        'notEstablished': {'selector': None, 'constant': None,
                           'reason': 'authored-explicit-unknown'}}
    return spec, raw


class Portfolio48Bindings(unittest.TestCase):
    def test_valid_authored_metadata_and_shared_stage_interface(self):
        spec, raw = authored_spec()
        result = lane._assess(spec, raw, now=NOW)
        self.assertEqual(result['status'], 'valid')
        self.assertEqual(result['dataRecords'], 0)
        self.assertFalse(result['sourceBodyAdmission'])
        self.assertEqual(lane.stage_result(result).receipt()['status'], 'succeeded')
        row = result['record']
        self.assertEqual(row['data']['zero'], 0)
        self.assertIsNone(row['data']['unknown'])
        self.assertEqual(row['data']['nativeUnit'], 'g')
        self.assertEqual(row['data']['nativeBasis'], 'per100g-authored-example')
        self.assertEqual(row['provenance']['fieldOrigins']['/data/zero']['sourceField'], '/zero')
        self.assertEqual(row['provenance']['fieldOrigins']['/data/notEstablished']['kind'], 'constant')
        self.assertEqual(field_origin_errors(row, {'receipt.json': sha(raw)},
                         policy_pins=(result['policySha256'],)), [])

    def test_missing_receipt(self):
        spec, _ = authored_spec()
        result = lane._assess(spec, None, now=NOW)
        self.assertEqual(result['status'], 'missing')
        self.assertIsNone(result['record'])

    def test_changed_receipt_is_stale_not_relabelled(self):
        spec, raw = authored_spec()
        result = lane._assess(spec, raw + b' ', now=NOW)
        self.assertEqual(result['status'], 'stale')
        self.assertEqual(result['diagnostics'], ['metadata-pin-mismatch'])

    def test_malformed_and_duplicate_json_isolated(self):
        for raw in [b'{', b'{"release":1,"release":2}', b'{"x":NaN}',
                    b'{"x":1e9999}', b'[]', b'\xff']:
            with self.subTest(raw=raw):
                spec, _ = authored_spec(raw)
                self.assertEqual(lane._assess(spec, raw, now=NOW)['status'], 'malformed')

    def test_missing_selector_and_identity_mismatch(self):
        spec, raw = authored_spec()
        spec['fields']['nativeUnit']['selector'] = '/absent'
        self.assertEqual(lane._assess(spec, raw, now=NOW)['status'], 'missing')
        spec, raw = authored_spec()
        spec['fields']['releaseLabel']['expected'] = 'wrong-release'
        self.assertEqual(lane._assess(spec, raw, now=NOW)['status'], 'malformed')

    def test_hold_never_overridden_by_valid_metadata(self):
        spec, raw = authored_spec()
        spec['sourceDataHolds'] = ['explicit-source-use-hold']
        result = lane._assess(spec, raw, now=NOW)
        self.assertEqual(result['status'], 'held')
        self.assertIsNotNone(result['record'])  # Only permitted receipt metadata.
        self.assertFalse(result['sourceBodyAdmission'])
        self.assertEqual(lane.stage_result(result).receipt()['status'], 'held')

    def test_metadata_hold_blocks_before_input_reader(self):
        spec, raw = authored_spec()
        spec['metadataReadAllowed'] = False
        self.assertEqual(lane._assess(spec, raw, now=NOW)['status'], 'held')
        with patch.object(lane, 'registry', return_value={'sources': [spec]}):
            with patch.object(lane, 'read_metadata', side_effect=AssertionError()) as reader:
                report = lane.assess_portfolio({'receipt.json': 'never-open.json'},
                                               now=NOW, reader=reader)
        reader.assert_not_called()
        self.assertEqual(report['sources'][0]['status'], 'held')

    def test_independent_peer_continues_on_bad_metadata(self):
        spec, raw = authored_spec()
        bad = copy.deepcopy(spec)
        bad['sourceId'] = 'authored-bad'
        bad['metadata']['name'] = 'bad.json'
        def reader(path):
            if path == 'bad.json':
                raise OSError('sensitive source detail must not escape')
            return raw
        with patch.object(lane, 'registry', return_value={'sources': [bad, spec]}):
            report = lane.assess_portfolio({'bad.json': 'bad.json', 'receipt.json': 'ok.json'},
                                           now=NOW, reader=reader)
        self.assertEqual([s['status'] for s in report['sources']], ['malformed', 'valid'])
        self.assertEqual(report['metadataRecords'], 1)
        self.assertNotIn('sensitive', canonical(report).decode())

    def test_acquisition_age_distinct_from_validation(self):
        spec, raw = authored_spec()
        result = lane._assess(spec, raw, now=NOW)
        cache = result['cache']
        self.assertEqual(cache['acquisitionAgeDays'], 20)
        self.assertEqual(cache['validationObservedAt'], '2026-09-20T00:00:00Z')
        self.assertFalse(cache['validationResetsAcquisitionAge'])
        self.assertFalse(cache['minimumReuseWindowElapsed'])
        self.assertEqual(cache['plannerCapability'], 'shared-pure-cache-planner-unavailable')
        self.assertEqual(cache['nextOnlineStep'], 'none')
        self.assertFalse(cache['sourceBytesVerified'])

    def test_minimum_thirty_day_boundary_is_diagnostic_not_online_plan(self):
        spec, raw = authored_spec()
        acquired = datetime(2026, 9, 1, tzinfo=timezone.utc)
        for delta, expected in [(timedelta(days=30, microseconds=-1), False),
                                (timedelta(days=30), True), (timedelta(days=50), True)]:
            cache = lane._assess(spec, raw, now=acquired + delta)['cache']
            self.assertEqual(cache['minimumReuseDays'], 30)
            self.assertEqual(cache['minimumReuseWindowElapsed'], expected)
            self.assertEqual(cache['networkRequests'], 0)
            self.assertEqual(cache['effectiveDecision'], 'not-enabled-no-source-cache-read')

    def test_validation_time_chain_is_checked_without_becoming_acquisition(self):
        _, raw = authored_spec()
        for value in ['not-a-time', '2026-09-30T00:00:00Z',
                      '2026-08-31T00:00:00Z', '2026-09-20T00:00:00']:
            document = json.loads(raw)
            document['validatedAt'] = value
            changed = canonical(document)
            spec, _ = authored_spec(changed)
            result = lane._assess(spec, changed, now=NOW)
            self.assertEqual(result['status'], 'malformed')
            self.assertEqual(result['diagnostics'], ['validation-time-invalid'])

    def test_future_or_naive_clock_fails_and_unknown_age_stays_null(self):
        spec, raw = authored_spec()
        for now in [datetime(2026, 8, 1, tzinfo=timezone.utc), datetime(2026, 9, 21), None]:
            self.assertEqual(lane._assess(spec, raw, now=now)['status'], 'malformed')
        spec['fields']['originalAcquiredAt'] = {'selector': None, 'constant': None,
                                               'reason': 'unknown-original-acquisition'}
        cache = lane._assess(spec, raw, now=NOW)['cache']
        self.assertIsNone(cache['acquisitionAgeDays'])
        self.assertIsNone(cache['minimumReuseWindowElapsed'])

    def test_pointer_escapes_missing_null_and_noncanonical_indices(self):
        self.assertIsNone(lane.pointer({'a/b': {'~c': [None]}}, '/a~1b/~0c/0'))
        for selector in ['/x/00', '/x/-1', '/x/+0', '/x/٠', '/bad~2']:
            with self.subTest(selector=selector), self.assertRaises((ValueError, KeyError)):
                lane.pointer({'x': [1]}, selector)

    def test_registry_complete_scope_and_no_admissions(self):
        config = lane.registry()
        self.assertEqual({s['country'] for s in config['sources']}, set(lane.COUNTRIES))
        self.assertEqual(len({s['sourceId'] for s in config['sources']}), 8)
        self.assertTrue(all(s['sourceDataHolds'] for s in config['sources']))
        for s in config['sources']:
            self.assertTrue(set(s['dataTypes']) <= set(lane.TYPES))
            self.assertEqual(s['fields']['nativeUnit']['constant'], None)
            self.assertEqual(s['fields']['nativeBasis']['constant'], None)
        self.assertIn('commercial-use-excluded', next(s for s in config['sources']
                      if s['sourceId'] == 'ec-composition-2021')['sourceDataHolds'])
        self.assertIn('failed-response-not-pdf', next(s for s in config['sources']
                      if s['sourceId'] == 'ec-cookbook-failed')['sourceDataHolds'])
        # Registry mutation cannot silently enable a static shipped source.
        config['sources'][0]['sourceDataHolds'] = []
        self.assertTrue(lane.registry()['sources'][0]['sourceDataHolds'])

    def test_no_default_custody_path_following_or_network(self):
        with patch('socket.create_connection', side_effect=AssertionError('network')):
            with patch.object(lane, 'read_metadata', side_effect=AssertionError()) as reader:
                report = lane.assess_portfolio(now=NOW, reader=reader)
        reader.assert_not_called()
        self.assertEqual(report['metadataRecords'], 0)
        self.assertEqual(len(report['coverage']), 24)
        self.assertTrue(all(s['status'] == 'missing' for s in report['sources']))
        self.assertEqual(report['dataRecords'], 0)

    def test_unknown_source_or_input_alias_rejected(self):
        with self.assertRaises(ValueError):
            lane.assess('unregistered', now=NOW)
        with self.assertRaises(ValueError):
            lane.assess_portfolio({'raw.pdf': '/not/read'}, now=NOW)
        with self.assertRaises(ValueError):
            lane.assess_portfolio([], now=NOW)

    def test_metadata_file_extension_size_symlink_and_duplicate_key(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            with self.assertRaises(ValueError):
                lane.read_metadata(root / 'original.pdf')
            link = root / 'link.json'
            link.symlink_to(FIXTURES / 'receipt.json')
            with self.assertRaises(ValueError):
                lane.read_metadata(link)
            large = root / 'large.json'
            large.write_bytes(b' ' * (lane.MAX_METADATA + 1))
            with self.assertRaises(ValueError):
                lane.read_metadata(large)

    def test_replay_is_deterministic_and_metadata_only(self):
        spec, raw = authored_spec()
        with patch.object(lane, 'registry', return_value={'sources': [spec]}):
            report = lane.assess_portfolio({'receipt.json': FIXTURES / 'receipt.json'}, now=NOW)
        first = lane.candidate_bytes(report)
        self.assertEqual(lane.replay(report)['action'], 'metadata-replayed')
        self.assertEqual(lane.replay(report, first)['action'], 'verified-no-op')
        self.assertEqual(lane.replay(report, first + b'\n')['action'], 'metadata-replayed')
        self.assertEqual(lane.replay(report)['candidateSha256'], sha(first))
        with self.assertRaises(ValueError):
            lane.replay(report, b'x' * (16 * lane.MAX_METADATA + 1))
        corrupt = copy.deepcopy(report)
        corrupt['metadataRecords'] = 999
        with self.assertRaises(ValueError):
            lane.replay(corrupt)

    def test_cli_rejects_existing_output_without_overwriting_it(self):
        with tempfile.TemporaryDirectory() as temp:
            output = Path(temp) / 'candidate.jsonl'
            output.write_bytes(b'preserve-me')
            process = subprocess.run([sys.executable, '-B', '-m',
                'offmenu.refresh.portfolio48', '--now', '2026-10-18T00:00:00Z',
                '--candidate-output', str(output)], capture_output=True)
            self.assertEqual(process.returncode, 2)
            self.assertEqual(output.read_bytes(), b'preserve-me')
            self.assertEqual(json.loads(process.stdout)['diagnostics'],
                             ['portfolio48-command-input-invalid'])

    def test_shared_qualification_accepts_authored_fixture_scope_only(self):
        spec, raw = authored_spec()
        result = lane._assess(spec, raw, now=NOW)
        row = result['record']
        assets = tuple(Asset(name, len((FIXTURES / name).read_bytes()),
                             sha((FIXTURES / name).read_bytes()))
                       for name in ['receipt.json', 'rights.json', 'scope.json'])
        schema = {'type': 'object', 'required': ['id', 'kind', 'data', 'provenance'],
                  'properties': {'kind': {'const': 'source-input-metadata'},
                                 'data': {'type': 'object', 'required': list(row['data']),
                                          'properties': {'nativeUnit': {'const': 'g'},
                                                         'nativeBasis': {'const': 'per100g-authored-example'}}}}}
        schemas = {'source-input-metadata': schema}
        contract = SourceContract('authored-portfolio48', 'AUTHORED-RECEIPT-1',
            'authored-metadata-only', '2026-09-01T00:00:00Z', assets, 1,
            ids_digest([row['id']]), schemas, fingerprint(schemas),
            lambda r: field_origin_errors(r, {'receipt.json': sha(raw)},
                                           policy_pins=(result['policySha256'],)),
            result['policySha256'], assets[1], assets[2],
            frozenset(('retain', 'parse', 'transform')), fixture=True)
        candidate = lane.candidate_bytes({'sources': [result]})
        manifest = {'sourceId': contract.source_id, 'releaseId': contract.release_id,
                    'acquiredAt': contract.acquired_at, 'rightsEvidenceSha256': assets[1].sha256,
                    'scopeEvidenceSha256': assets[2].sha256, 'normalizedRecords': 1,
                    'inputFiles': [vars(a) for a in assets],
                    'candidateSha256': sha(candidate), 'candidateBytes': len(candidate)}
        with tempfile.TemporaryDirectory() as temp:
            target = Path(temp) / 'metadata.jsonl'
            target.write_bytes(candidate)
            qualification = qualify(contract, FIXTURES, target, manifest)
            self.assertTrue(qualification['fixture'])
            self.assertTrue(qualification['qualified'], qualification['errors'])
            row['provenance']['fieldOrigins'].pop('/data/zero')
            bad = lane.candidate_bytes({'sources': [result]})
            target.write_bytes(bad)
            manifest.update(candidateSha256=sha(bad), candidateBytes=len(bad))
            failed = qualify(contract, FIXTURES, target, manifest)
            self.assertIn('field-origin-inventory-mismatch', failed['errors'])
            self.assertFalse(failed['qualified'])

    def test_cli_offline_missing_and_unsupported_force(self):
        # subprocess checks the installed module interface, not a shared CLI edit.
        for args in [[], ['--force-download']]:
            process = subprocess.run([sys.executable, '-B', '-m',
                'offmenu.refresh.portfolio48', '--now', '2026-10-18T00:00:00Z', *args],
                capture_output=True, check=False)
            self.assertEqual(process.returncode, 2)
            if not args:
                report = json.loads(process.stdout)
                self.assertEqual(report['metadataRecords'], 0)
                self.assertFalse(report['sourceBodyAdmission'])


if __name__ == '__main__':
    unittest.main()
