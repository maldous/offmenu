"""Authored metadata only: never load retained source bodies or use the network."""
import copy
import json
from pathlib import Path
import unittest
from unittest.mock import patch

from offmenu.refresh.core import canonical, sha
from offmenu.refresh.worker33_bindings import assess, assess_portfolio, MAX_METADATA_BYTES

NOW = '2026-10-18T00:00:00+00:00'


def fixture():
    raw = canonical({'country': 'GH', 'value': '12.30', 'unit': 'unknown'})
    pin = {'path': 'authored.json', 'sha256': sha(raw)}
    spec = {'id': 'gh-authored', 'country': 'GH', 'kind': 'price-coverage',
            'sourceId': 'authored-metadata-only', 'releaseId': 'synthetic-v1',
            'publisherRelease': None, 'input': pin, 'parentManifest': pin,
            'original': None, 'countrySelectors': ['/country'],
            'fields': {'amount': {'selector': '/value', 'type': 'string',
                                  'meaning': 'Authored lexical amount'},
                       'unit': {'selector': '/unit', 'type': 'string',
                                'meaning': 'Authored explicit unknown unit'}},
            'originalAcquiredAt': '2026-10-14T00:00:00+00:00',
            'acquisitionEvidence': pin, 'holds': [],
            'adapter': 'authored-metadata-only', 'unknowns': ['unit'],
            'retainedCounts': {'authoredRecords': 1}}
    return spec, raw


class Worker33BindingTests(unittest.TestCase):
    def test_valid_shared_stage_and_field_origin_contract(self):
        spec, raw = fixture()
        with patch('socket.socket', side_effect=AssertionError('network forbidden')), \
             patch.object(Path, 'open', side_effect=AssertionError('filesystem forbidden')):
            result = assess(spec, {spec['id']: raw}, now=NOW)
        self.assertEqual(result['stage']['status'], 'succeeded')
        self.assertEqual(result['fieldOriginCount'], 2)
        self.assertEqual(result['cacheIntent'], 'retain-no-refresh')
        self.assertEqual(result['originalAcquisitionAgeSeconds'], 4 * 86400)
        self.assertEqual(result['networkRequests'], 0)
        self.assertEqual(result['normalizedRecords'], 0)
        self.assertFalse(result['countryAccepted'])
        self.assertEqual(result['authorizedSourceOperations'], [])

    def test_missing_stale_held_and_malformed_are_distinct(self):
        spec, raw = fixture()
        self.assertEqual(assess(spec, {}, now=NOW)['metadataOutcome'], 'missing')
        stale = assess(spec, {spec['id']: raw + b' '}, now=NOW)
        self.assertEqual(stale['stage']['status'], 'quarantined')
        self.assertEqual(stale['metadataOutcome'], 'stale-input')
        spec['holds'] = ['private-inspection-only']
        held = assess(spec, {spec['id']: raw}, now=NOW)
        self.assertEqual(held['stage']['status'], 'held')
        self.assertEqual(held['metadataOutcome'], 'valid')
        malformed = b'{"country":"GH","value":NaN}'
        spec['input']['sha256'] = sha(malformed)
        failed = assess(spec, {spec['id']: malformed}, now=NOW)
        self.assertEqual(failed['stage']['status'], 'failed')
        self.assertNotIn('NaN', json.dumps(failed))

    def test_selectors_types_countries_and_duplicate_keys_fail_closed(self):
        for body in ({'country': 'GN', 'value': '12.30', 'unit': 'unknown'},
                     {'country': 'GH', 'value': 12.3, 'unit': 'unknown'},
                     {'country': 'GH', 'unit': 'unknown'}):
            spec, _ = fixture()
            raw = canonical(body)
            spec['input']['sha256'] = sha(raw)
            self.assertEqual(assess(spec, {spec['id']: raw}, now=NOW)['metadataOutcome'], 'malformed')
        spec, _ = fixture()
        raw = b'{"country":"GH","value":"1","value":"2","unit":"KG"}'
        spec['input']['sha256'] = sha(raw)
        self.assertEqual(assess(spec, {spec['id']: raw}, now=NOW)['metadataOutcome'], 'malformed')
        spec, raw = fixture()
        spec['fields']['amount']['selector'] = '/bad~2pointer'
        self.assertEqual(assess(spec, {spec['id']: raw}, now=NOW)['metadataOutcome'], 'malformed')

    def test_noop_still_revalidates_and_does_not_mutate_inputs(self):
        spec, raw = fixture()
        before = copy.deepcopy(spec)
        first = assess(spec, {spec['id']: raw}, now=NOW)
        second = assess(spec, {spec['id']: raw}, now='2026-10-19T00:00:00+00:00',
                        previous_key=first['buildKey'])
        self.assertEqual(first['buildKey'], second['buildKey'])
        self.assertEqual(second['replay'], 'no-op')
        self.assertEqual(second['stage']['status'], 'reused')
        stale = assess(spec, {spec['id']: b'changed'}, now=NOW, previous_key=first['buildKey'])
        self.assertEqual(stale['metadataOutcome'], 'stale-input')
        self.assertEqual(spec, before)

    def test_acquisition_age_unknown_old_and_future_no_refresh_override(self):
        spec, raw = fixture()
        spec['originalAcquiredAt'] = None
        spec['acquisitionEvidence'] = None
        unknown = assess(spec, {spec['id']: raw}, now=NOW)
        self.assertIsNone(unknown['originalAcquisitionAgeSeconds'])
        self.assertEqual(unknown['cacheIntent'], 'acquisition-age-unknown')
        spec, raw = fixture()
        old = assess(spec, {spec['id']: raw}, now='2026-11-14T00:00:00+00:00')
        self.assertEqual(old['cacheIntent'], 'refresh-review-required-no-network')
        self.assertFalse(old['refreshOverridesAvailable'])
        self.assertEqual(old['networkRequests'], 0)
        future = assess(spec, {spec['id']: raw}, now='2026-10-13T00:00:00+00:00')
        self.assertEqual(future['metadataOutcome'], 'malformed')

    def test_bounded_input_and_peer_diagnostic_isolation(self):
        spec, raw = fixture()
        result = assess_portfolio([None, {'id': 'bad'}, spec], {spec['id']: raw}, now=NOW)
        self.assertEqual([r['metadataOutcome'] for r in result], ['malformed', 'malformed', 'valid'])
        self.assertEqual(assess(spec, {spec['id']: b'x' * (MAX_METADATA_BYTES + 1)}, now=NOW)
                         ['metadataOutcome'], 'malformed')

    def test_retained_config_closed_scope_without_opening_data_paths(self):
        config = json.loads((Path(__file__).resolve().parents[1] /
                             'offmenu/refresh/worker33_portfolio.json').read_text())
        self.assertEqual(config['countries'], ['GH', 'GI', 'GM', 'GN'])
        self.assertEqual(len(config['bindings']), 5)
        for spec in config['bindings']:
            self.assertTrue(spec['holds'])
            self.assertEqual(assess(spec, {}, now=NOW)['metadataOutcome'], 'missing')
        self.assertEqual(sum(len(s['fields']) for s in config['bindings']), 85)

    def test_unhashable_binding_id_cannot_abort_valid_peer_replay(self):
        spec, raw = fixture()
        supplied = {spec['id']: raw}
        valid = assess(spec, supplied, now=NOW)
        for identity in ([], {}):
            for previous in (None, {}, {spec['id']: valid['buildKey']}):
                with self.subTest(identity=identity, previous=previous):
                    bad = copy.deepcopy(spec)
                    bad['id'] = identity
                    before = copy.deepcopy([bad, spec])
                    results = assess_portfolio([bad, spec], supplied, now=NOW,
                                               previous_keys=previous)
                    self.assertEqual(results[0]['metadataOutcome'], 'malformed')
                    self.assertEqual(results[0]['stage']['status'], 'failed')
                    self.assertEqual(results[1]['metadataOutcome'], 'valid')
                    self.assertEqual(results[1]['stage']['status'],
                                     'reused' if previous else 'succeeded')
                    self.assertEqual(results[1]['buildKey'], valid['buildKey'])
                    self.assertEqual([bad, spec], before)


if __name__ == '__main__':
    unittest.main()
