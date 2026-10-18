"""Authored metadata fixtures only. No historical source bodies or network."""
import copy
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from offmenu import portfolio_bm_lc_sc as portfolio
from offmenu.refresh.core import canonical, sha

FIXTURE = Path(__file__).parent / 'fixtures/bm-lc-sc/metadata.json'


class PortfolioBindingTests(unittest.TestCase):
    def setUp(self):
        self.raw = FIXTURE.read_bytes()
        self.binding = {'id': 'synthetic-lc', 'country': 'LC', 'sourceId': 'authored',
                        'releaseId': 'fixture-v1', 'scope': 'retained-metadata-only',
                        'holds': [], 'metadata': {'bytes': len(self.raw),
                                                 'sha256': sha(self.raw)},
                        'selectors': {'country': '/country', 'nativeBasis': '/nativeBasis',
                                      'unit': '/unknownUnit'},
                        'originalAcquiredAtSelector': '/completedAt'}
        self.now = '2026-10-02T00:00:00Z'

    def assess(self, binding=None, raw=None, **kwargs):
        return portfolio.assess(binding or self.binding,
                                self.raw if raw is None else raw,
                                now=kwargs.pop('now', self.now), **kwargs)

    def test_valid_deterministic_metadata_candidate_and_null_origins(self):
        before = copy.deepcopy(self.binding)
        result = self.assess()
        self.assertEqual(result['status'], 'ready-metadata-only')
        self.assertEqual(result['metadataCandidate']['data']['unit'], None)
        origin = result['metadataCandidate']['provenance']['fieldOrigins']['/data/unit']
        self.assertEqual(origin['sourceField'], '/unknownUnit')
        self.assertEqual(result['acceptedRecords'], 0)
        self.assertEqual(result['bodyProcessing'], False)
        self.assertEqual(canonical(result), canonical(self.assess()))
        self.assertEqual(self.binding, before)

    def test_missing_input_and_field_are_typed(self):
        result = portfolio.assess(self.binding, None, now=self.now)
        self.assertEqual(result['status'], 'missing')
        self.assertIn('metadata-missing', result['errors'])
        self.binding['selectors']['absent'] = '/does-not-exist'
        self.assertIn('declared-field-missing', self.assess()['errors'])
        self.assertIsNone(self.assess()['metadataCandidate'])

    def test_hold_retained_even_on_missing_input_and_no_candidate(self):
        self.binding['holds'] = ['source-use-not-cleared']
        result = self.assess()
        self.assertEqual(result['status'], 'held')
        self.assertIn('source-use-held', result['errors'])
        self.assertIsNone(result['metadataCandidate'])
        self.assertFalse(result['cache']['downloadAllowed'])
        self.assertIn('source-use-held', portfolio.assess(
            self.binding, None, now=self.now)['errors'])

    def test_corrupt_pin_invalid_json_duplicate_keys_nonfinite_and_selector(self):
        self.assertIn('metadata-pin-mismatch', self.assess(raw=b'bad')['errors'])
        for raw in (b'{', b'{"a":1,"a":2}', b'{"a":NaN}'):
            b = copy.deepcopy(self.binding)
            b['metadata'] = {'bytes': len(raw), 'sha256': sha(raw)}
            r = self.assess(b, raw)
            self.assertEqual(r['status'], 'malformed')
            self.assertEqual(r['errors'], ['binding-or-metadata-malformed'])
        for selector in ('../secret', '/country/~2', '/country/0'):
            self.binding['selectors']['country'] = selector
            self.assertEqual(self.assess()['status'], 'malformed')

    def test_absent_planner_unknown_at_all_ages_preserves_clock_and_replay(self):
        results = [self.assess(now=now) for now in
                   ('2026-10-30T23:59:59Z', '2026-10-31T00:00:00Z', '2027-01-01T00:00:00Z')]
        for r in results:
            self.assertEqual(r['status'], 'ready-metadata-only')
            self.assertEqual(r['cache']['plannerCapability'], 'unsupported')
            self.assertEqual(r['cache']['decision'], 'unknown-no-download')
            self.assertFalse(r['cache']['downloadAllowed'])
        self.assertEqual(len({r['contentKey'] for r in results}), 1)
        self.assertEqual(len({r['cache']['originalAcquiredAt'] for r in results}), 1)
        self.assertGreater(results[-1]['cache']['acquisitionAgeSeconds'],
                           results[0]['cache']['acquisitionAgeSeconds'])
        self.assertEqual(self.assess(now='2027-01-01T00:00:00Z',
            previous_key=results[0]['contentKey'])['replay'], 'unchanged-no-op')

    def test_nonblocking_fifo_rejection_allows_regular_metadata_peer(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); fifo = root / 'fifo'; os.mkfifo(fifo)
            good = root / 'metadata.json'; good.write_bytes(self.raw)
            b = copy.deepcopy(self.binding); b['metadata']['path'] = str(fifo)
            peer = copy.deepcopy(self.binding); peer['metadata']['path'] = str(good)
            program = ('import json; from offmenu.portfolio_bm_lc_sc import run; '
                       'print(json.dumps(run(' + repr([b, peer]) +
                       ',now="2026-10-02T00:00:00Z")))')
            p = subprocess.run([sys.executable, '-c', program], capture_output=True,
                               text=True, timeout=3, check=True)
            r = json.loads(p.stdout)
            self.assertEqual([x['status'] for x in r['bindings']],
                             ['malformed', 'ready-metadata-only'])
            self.assertEqual(r['bindings'][0]['errors'], ['metadata-read-failed'])

    def test_regular_reader_rejects_links_directories_and_cleans_descriptors(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); good = root / 'metadata.json'; good.write_bytes(self.raw)
            link = root / 'link'; link.symlink_to(good)
            for path in (link, root):
                with self.assertRaises((OSError, ValueError)):
                    portfolio.read_metadata({'path': str(path)})
            self.assertEqual(portfolio.read_metadata({'path': str(good)}), self.raw)
            count = lambda: len(list(Path('/proc/self/fd').iterdir()))
            before = count()
            with patch.object(portfolio.os, 'read', side_effect=OSError('private error')):
                with self.assertRaises(OSError):
                    portfolio.read_metadata({'path': str(good)})
            self.assertEqual(count(), before)

    def test_future_unknown_and_invalid_clocks_fail_closed(self):
        self.assertEqual(self.assess(now='2026-09-01T00:00:00Z')['status'], 'malformed')
        for clock in ('2026-10-02', 'bad', None):
            self.assertEqual(self.assess(now=clock)['status'], 'malformed')
        self.binding['originalAcquiredAtSelector'] = None
        self.assertIn('original-acquisition-time-missing', self.assess()['errors'])

    def test_replay_key_independent_of_validation_age_but_binds_policy_changes(self):
        a = self.assess()
        b = self.assess(now='2026-10-03T00:00:00Z', previous_key=a['contentKey'])
        self.assertEqual(b['replay'], 'unchanged-no-op')
        self.assertEqual(a['metadataCandidate'], b['metadataCandidate'])
        self.binding['holds'] = ['new-hold']
        c = self.assess(previous_key=a['contentKey'])
        self.assertNotEqual(c['contentKey'], a['contentKey'])
        self.assertEqual(c['replay'], 'not-ready')

    def test_isolated_failure_does_not_block_peer_or_echo_exception(self):
        bad = copy.deepcopy(self.binding)
        bad['id'] = 'bad'
        def reader(asset):
            if asset.get('path') == 'private':
                raise PermissionError('SECRET-CREDENTIAL')
            return self.raw
        bad['metadata']['path'] = 'private'
        result = portfolio.run([bad, self.binding], now=self.now, reader=reader)
        self.assertEqual([x['status'] for x in result['bindings']],
                         ['malformed', 'ready-metadata-only'])
        self.assertNotIn('SECRET-CREDENTIAL', json.dumps(result))

    def test_country_mismatch_cannot_borrow_another_portfolio_member(self):
        self.binding['country'] = 'BM'
        self.assertEqual(self.assess()['status'], 'malformed')

    def test_no_body_pointer_followed_and_no_network_dependency(self):
        with patch('socket.socket', side_effect=AssertionError('network forbidden')):
            self.assertEqual(self.assess()['networkRequests'], 0)
        self.binding['retainedBodyReferenceOnly'] = {'path': '/do-not-open'}
        with patch.object(Path, 'open', side_effect=AssertionError('body forbidden')):
            self.assertEqual(self.assess()['status'], 'ready-metadata-only')

    def test_fixed_portfolio_configuration_never_enables_real_body_processing(self):
        config = json.loads(portfolio.CONFIG.read_text())
        self.assertEqual(len(config['bindings']), 8)
        self.assertEqual(set(x['country'] for x in config['bindings']), {'BM', 'LC', 'SC'})
        for b in config['bindings']:
            self.assertTrue(b['holds'])
            self.assertIsNone(b['adapterBinding']['sourceContract'])
            self.assertFalse(b['applicability']['accepted'])


if __name__ == '__main__':
    unittest.main()
