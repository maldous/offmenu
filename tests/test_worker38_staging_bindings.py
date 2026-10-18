"""Authored metadata only: no real source payloads or network fixtures."""
import copy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from offmenu.refresh.portfolios.worker38 import diagnose as _diagnose, run as _run, REGISTRY
from offmenu.refresh.acceptance import Asset, SourceContract, fingerprint, ids_digest, qualify
from offmenu.refresh.field_provenance import field_origin_errors


def fixture_cache_planner(acquired, digest, *, now):
    # Fixed authored protocol responses, NOT a planner implementation or source spoof.
    age, decision = {
        '2026-10-18': (4, 'reuse-verified-cache'),
        '2026-10-19': (5, 'reuse-verified-cache'),
        '2026-11-13': (30, 'conditional-revalidation-required'),
        '2026-11-17': (34, 'conditional-revalidation-required'),
    }[now.date().isoformat()]
    return {'minimumReuseDays': 30, 'acquisitionAgeDays': age, 'decision': decision,
            'mtimeUsedForFreshness': False, 'assetBytesVerifiedByThisPlan': False,
            'networkRequests': 0}


def diagnose(*args, **kwargs):
    kwargs.setdefault("cache_planner", fixture_cache_planner)
    return _diagnose(*args, **kwargs)


def run(*args, **kwargs):
    kwargs.setdefault("cache_planner", fixture_cache_planner)
    return _run(*args, **kwargs)


NOW = '2026-10-18T00:00:00Z'


def fixture():
    raw = (Path(__file__).parent / 'fixtures/worker38/receipt.json').read_bytes()
    return {
        'sourceId': 'pt-authored', 'country': 'PT',
        'releaseId': 'authored-only-v1', 'role': 'synthetic-metadata',
        'types': ['nutrition'],
        'metadata': {'path': 'never-followed-in-pure-check',
                     'sha256': hashlib.sha256(raw).hexdigest()},
        'fields': {'country': '/country', 'literalZero': '/zero',
                   'unknownUnit': '/unit', 'label': '/label'},
        'originalAcquiredAtSelector': '/capturedAt', 'holds': [],
        'rawManifest': None, 'rawSelector': None, 'nativeUnit': None,
        'nativeBasis': None, 'scopeAcceptance': None, 'sourceUseDecision': None,
    }, raw


class Worker38Bindings(unittest.TestCase):
    def test_valid_metadata_uses_shared_origin_contract_and_preserves_literals(self):
        e, raw = fixture()
        result = diagnose(e, raw, now=NOW)
        self.assertEqual(result['status'], 'metadata-proposal-ready')
        self.assertEqual(result['errors'], [])
        self.assertEqual(result['candidate']['data'], {
            'country': 'PT', 'literalZero': 0, 'unknownUnit': None,
            'label': ' authored label  '})
        self.assertIn('nativeUnit', result['unknowns'])
        self.assertFalse(result['sourceAccepted'])
        self.assertFalse(result['countryComplete'])

    def test_exact_input_pin_required(self):
        e, raw = fixture()
        result = diagnose(e, raw + b' ', now=NOW)
        self.assertIn('metadata-pin-mismatch', result['errors'])
        self.assertIsNone(result['candidate'])
        self.assertIsNone(result['metadataCandidate'])

    def test_missing_selector_is_not_fabricated(self):
        e, raw = fixture()
        e['fields']['table'] = '/not-supplied'
        result = diagnose(e, raw, now=NOW)
        self.assertIn('metadata-selector-missing', result['errors'])
        self.assertIsNone(result['candidate'])

    def test_hold_is_not_cleared_by_fresh_cache(self):
        e, raw = fixture()
        e['holds'] = ['source-specific-no-body']
        result = diagnose(e, raw, now=NOW)
        self.assertIn('source-processing-held', result['errors'])
        self.assertEqual(result['action'], 'withheld')
        self.assertEqual(result['cache']['decision'], 'reuse-verified-cache')
        self.assertIsNone(result['candidate'])
        self.assertIsNotNone(result['metadataCandidate'])

    def test_stale_after_thirty_days_never_downloads(self):
        e, raw = fixture()
        result = diagnose(e, raw, now='2026-11-17T00:00:00Z')
        self.assertIn('stale-input-review-required', result['errors'])
        self.assertEqual(result['cache']['acquisitionAgeDays'], 34)
        self.assertEqual(result['networkRequests'], 0)
        self.assertIsNone(result['candidate'])

    def test_exact_thirty_day_boundary_is_stale(self):
        e, raw = fixture()
        result = diagnose(e, raw, now='2026-11-13T00:00:00Z')
        self.assertIn('stale-input-review-required', result['errors'])

    def test_validation_age_does_not_reset_acquisition_or_key(self):
        e, raw = fixture()
        first = diagnose(e, raw, now=NOW)
        later = diagnose(e, raw, now='2026-10-19T00:00:00Z',
                         previous_key=first['buildKey'])
        self.assertEqual(later['action'], 'no-op')
        self.assertEqual(first['buildKey'], later['buildKey'])
        self.assertEqual(later['cache']['acquisitionAgeDays'], 5)
        self.assertFalse(later['cache']['validationResetsAcquisitionAge'])
        self.assertEqual(first['candidate'], later['candidate'])
        self.assertNotIn('wikibooks', json.dumps(later))

    def test_changed_scope_or_bytes_cannot_be_noop(self):
        e, raw = fixture()
        first = diagnose(e, raw, now=NOW)
        e['role'] = 'different-metadata-purpose'
        later = diagnose(e, raw, now=NOW, previous_key=first['buildKey'])
        self.assertNotEqual(first['buildKey'], later['buildKey'])
        self.assertEqual(later['action'], 'stage-metadata-proposal')

    def test_malformed_duplicate_and_nonfinite_are_isolated(self):
        e, _ = fixture()
        for raw in [b'{', b'[]', b'{"x":1,"x":2}', b'{"x":NaN}', b'{"x":1e999}']:
            with self.subTest(raw=raw):
                e['metadata']['sha256'] = hashlib.sha256(raw).hexdigest()
                result = diagnose(e, raw, now=NOW)
                self.assertIn('malformed-input', result['errors'])
                self.assertIsNone(result['candidate'])

    def test_wrong_country_and_future_capture_are_explicit(self):
        e, raw = fixture()
        e['country'] = 'SX'
        result = diagnose(e, raw, now='2026-10-13T00:00:00Z')
        self.assertIn('country-binding-mismatch', result['errors'])
        self.assertIn('acquisition-time-invalid', result['errors'])

    def test_missing_acquisition_age_is_not_validation_time(self):
        e, raw = fixture()
        e['originalAcquiredAtSelector'] = None
        result = diagnose(e, raw, now=NOW)
        self.assertIsNone(result['cache'])
        self.assertIn('original-acquisition-time-unknown', result['errors'])

    def test_missing_file_does_not_hide_valid_peer(self):
        e, raw = fixture()
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'receipt.json'
            path.write_bytes(raw)
            good = copy.deepcopy(e)
            good['metadata']['path'] = str(path)
            bad = copy.deepcopy(e)
            bad['sourceId'] = 'missing-peer'
            bad['metadata']['path'] = str(path.parent / 'absent')
            registry = {'entries': [bad, good], 'countries': ['PT'],
                        'types': ['nutrition', 'recipes']}
            # Network is not a fallback, even when one input is missing.
            with patch('socket.socket', side_effect=AssertionError('network forbidden')):
                result = run(registry, now=NOW)
            self.assertEqual(result['results'][0]['errors'], ['metadata-unavailable'])
            self.assertEqual(result['results'][1]['status'], 'metadata-proposal-ready')
            self.assertEqual(result['cells'][1]['sources'], [])
            self.assertFalse(result['cells'][1]['accepted'])

    def test_symlink_rejected_before_read(self):
        e, raw = fixture()
        with tempfile.TemporaryDirectory() as directory:
            original = Path(directory) / 'receipt.json'
            original.write_bytes(raw)
            link = original.parent / 'link.json'
            link.symlink_to(original)
            e['metadata']['path'] = str(link)
            result = run({'entries': [e], 'countries': ['PT'], 'types': ['nutrition']}, now=NOW)
            self.assertEqual(result['results'][0]['errors'], ['metadata-unavailable'])

    def test_registry_preserves_all_real_holds_and_twentyfour_cells(self):
        registry = REGISTRY
        self.assertEqual(registry['countries'], ['PT', 'SX', 'TR', 'VC'])
        self.assertEqual(len(registry['types']), 6)
        self.assertEqual(len(registry['entries']), 5)
        for entry in registry['entries']:
            self.assertTrue(entry['holds'])
            self.assertIsNone(entry['sourceUseDecision'])
            self.assertIsNone(entry['rawSelector'])

    def test_no_shared_planner_means_no_pilot_source_substitution(self):
        e, raw = fixture()
        result = _diagnose(e, raw, now=NOW)
        self.assertIn('shared-cache-planner-unavailable', result['errors'])
        self.assertIsNone(result['candidate'])
        self.assertFalse(result['cache']['rawCacheReuseQualified'])
        self.assertIsNotNone(result['metadataCandidate'])

    def test_callback_failure_is_fixed_diagnostic_not_private_exception(self):
        e, raw = fixture()
        def failed(*args, **kwargs):
            raise RuntimeError('private details must not escape')
        result = _diagnose(e, raw, now=NOW, cache_planner=failed)
        self.assertIn('cache-planner-failed', result['errors'])
        self.assertNotIn('private details', json.dumps(result))

    def test_unsafe_cache_protocol_is_rejected(self):
        e, raw = fixture()
        def unsafe(*args, **kwargs):
            return {'minimumReuseDays': 0, 'networkRequests': 1}
        result = _diagnose(e, raw, now=NOW, cache_planner=unsafe)
        self.assertIn('cache-planner-contract-invalid', result['errors'])
        self.assertIsNone(result['candidate'])

    def test_authored_fixture_qualifies_through_shared_source_contract(self):
        e, raw = fixture()
        row = diagnose(e, raw, now=NOW)['candidate']
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            bundle = root / 'bundle'
            (bundle / 'metadata').mkdir(parents=True)
            metadata_name = 'metadata/pt-authored.json'
            (bundle / metadata_name).write_bytes(raw)
            (bundle / 'rights.json').write_text('{"scope":"authored-test-only"}')
            (bundle / 'scope.json').write_text('{"ids":["pt-authored:metadata"]}')
            assets = tuple(Asset(name, len((bundle / name).read_bytes()),
                                 hashlib.sha256((bundle / name).read_bytes()).hexdigest())
                           for name in [metadata_name, 'rights.json', 'scope.json'])
            schemas = {'sourceMetadata': {
                'type': 'object', 'required': ['id', 'kind', 'schemaVersion', 'data', 'provenance'],
                'additionalProperties': False,
                'properties': {'id': {'const': row['id']}, 'kind': {'const': 'sourceMetadata'},
                    'schemaVersion': {'const': '1.0'}, 'data': {'const': row['data']},
                    'provenance': {'const': row['provenance']}}}}
            contract = SourceContract(
                source_id=e['sourceId'], release_id=e['releaseId'],
                scope_id='authored-worker38-metadata-only',
                acquired_at='2026-10-14T00:00:00Z', inputs=assets,
                expected_records=1, expected_ids_sha256=ids_digest([row['id']]),
                schemas=schemas, schemas_sha256=fingerprint(schemas),
                semantic_validator=lambda value: field_origin_errors(
                    value, {metadata_name: assets[0].sha256}),
                policy_sha256=fingerprint({'scope': 'authored-field-origins'}),
                rights_evidence=assets[1], scope_evidence=assets[2],
                permitted_operations=frozenset(('retain', 'parse', 'transform')),
                fixture=True, max_records=2, max_input_bytes=65536, max_output_bytes=65536)
            candidate = root / 'candidate.jsonl'
            candidate.write_bytes((json.dumps([row]) + '\n').encode())
            manifest = {'sourceId': e['sourceId'], 'releaseId': e['releaseId'],
                'acquiredAt': contract.acquired_at, 'normalizedRecords': 1,
                'rightsEvidenceSha256': assets[1].sha256,
                'scopeEvidenceSha256': assets[2].sha256,
                'inputFiles': [vars(a) for a in assets],
                'candidateBytes': candidate.stat().st_size,
                'candidateSha256': hashlib.sha256(candidate.read_bytes()).hexdigest()}
            result = qualify(contract, bundle, candidate, manifest, scratch_root=root)
            self.assertEqual(result['errors'], [])
            self.assertTrue(result['qualified'])
            self.assertTrue(result['fixture'])
            candidate.write_text('[{"id":"corrupt"}]\n')
            corrupt = qualify(contract, bundle, candidate, manifest, scratch_root=root)
            self.assertFalse(corrupt['qualified'])
            self.assertIn('candidate-custody-mismatch', corrupt['errors'])


if __name__ == '__main__':
    unittest.main()
