"""Authored metadata/candidate fixtures only; never read a retained source body."""
import copy
from dataclasses import replace
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from offmenu.refresh.acceptance import (Asset, SourceContract, canonical,
                                       fingerprint, ids_digest, qualify)
from offmenu.refresh.portfolio12 import literal_errors, portfolio_report, preflight
from offmenu.refresh.portfolio12_bindings import BINDINGS

NOW = '2026-10-18T00:00:00Z'


class Portfolio12Tests(unittest.TestCase):
    def setUp(self):
        self.body = b'{"authored":"fixture-only"}\n'
        self.binding = {
            'key': 'authored-mm-fixture', 'country': 'MM',
            'sourceId': 'authored-w12', 'releaseId': 'synthetic-1',
            'fixture': True, 'holds': [], 'unknowns': [],
            'cacheRights': 'fixture-only', 'types': ['prices/baskets'],
            'originalAcquiredAt': '2026-10-01T00:00:00Z',
            'validatedAt': '2026-10-17T00:00:00Z',
            'units': ['fixture-unit'], 'bases': ['fixture-basis'],
            'originPattern': 'fixture:row=2',
            'evidence': [{'path': 'authored.json',
                          'sha256': hashlib.sha256(self.body).hexdigest(),
                          'selectors': ['/authored']}],
        }
        self.observed = {'authored.json': self.body}

    def plan(self, **kwargs):
        return preflight(self.binding, now=NOW, observed=self.observed, **kwargs)

    def test_valid_deterministic_replay_noop_never_accepts(self):
        first = self.plan()
        self.assertEqual(first['status'], 'fixture-ready')
        self.assertEqual(first, self.plan())
        repeat = self.plan(previous_key=first['bindingKey'])
        self.assertEqual(repeat['replay'], 'no-op-metadata-plan')
        self.assertEqual(first['bindingKey'], repeat['bindingKey'])
        self.binding['validatedAt'] = NOW
        self.assertEqual(self.plan(previous_key=first['bindingKey'])['replay'], 'no-op-metadata-plan')
        self.assertFalse(first['assetBytesVerified'])
        self.assertFalse(first['productionAccepted'])

    def test_missing_held_malformed_and_stale_isolated(self):
        held = copy.deepcopy(self.binding); held['holds'] = ['no-body']
        stale = copy.deepcopy(self.binding)
        stale['originalAcquiredAt'] = '2026-09-01T00:00:00Z'
        malformed = copy.deepcopy(self.binding); malformed['evidence'][0]['sha256'] = 'bad'
        missing = copy.deepcopy(self.binding); missing['evidence'][0]['path'] = 'missing.json'
        report = portfolio_report(now=NOW, observed=self.observed,
                                  bindings=[held, missing, malformed, stale, self.binding])
        self.assertEqual([r['status'] for r in report['results']],
                         ['held', 'missing', 'malformed', 'held', 'fixture-ready'])
        self.assertIn('stale-input-review-required', report['results'][3]['diagnostics'])
        self.assertEqual(report['networkRequests'], 0)
        self.assertEqual(report['sourceBodiesRead'], 0)
        self.assertEqual(len(report['cells']), 24)
        self.assertFalse(any(c['accepted'] for c in report['cells']))
        malformed['types'] = 3
        self.assertEqual(portfolio_report(now=NOW, observed=self.observed,
            bindings=[malformed, self.binding])['results'][1]['status'], 'fixture-ready')

    def test_evidence_selector_checked_without_opening_source(self):
        self.binding['evidence'][0]['selectors'] = ['/missing']
        self.assertIn('metadata-evidence-selector-missing', self.plan()['diagnostics'])
        self.body = b'{"authored":1,"authored":2}'
        self.observed['authored.json'] = self.body
        self.binding['evidence'][0]['sha256'] = hashlib.sha256(self.body).hexdigest()
        self.assertEqual(self.plan()['status'], 'malformed')

    def test_unhashable_binding_keys_do_not_suppress_peer_or_cells(self):
        for malformed_key in ([], {}):
            with self.subTest(key=malformed_key):
                malformed = copy.deepcopy(self.binding)
                malformed['key'] = malformed_key
                report = portfolio_report(now=NOW, observed=self.observed,
                    bindings=[malformed, self.binding],
                    previous={self.binding['key']: self.plan()['bindingKey']})
                self.assertEqual([r['status'] for r in report['results']],
                                 ['malformed', 'fixture-ready'])
                self.assertIn('portfolio-metadata-malformed', report['results'][0]['diagnostics'])
                self.assertEqual(report['results'][1]['replay'], 'no-op-metadata-plan')
                self.assertEqual(len(report['cells']), 24)
                self.assertFalse(any(c['accepted'] for c in report['cells']))

    def test_validation_never_resets_acquisition_cache_clock(self):
        self.binding['originalAcquiredAt'] = '2026-09-18T00:00:00Z'
        self.binding['validatedAt'] = NOW
        result = self.plan()
        self.assertEqual(result['validationAgeSeconds'], 0)
        self.assertEqual(result['acquisitionAgeSeconds'], 30 * 86400)
        self.assertEqual(result['cacheDecision'], 'stale-input-review-no-download')
        self.binding['originalAcquiredAt'] = None
        self.assertIn('original-acquisition-time-unknown', self.plan()['diagnostics'])

    def test_bad_time_and_metadata_pin_never_replay_success(self):
        self.observed['authored.json'] = b'changed'
        self.assertIn('metadata-evidence-pin-mismatch', self.plan()['diagnostics'])
        for value in ['tomorrow', '2026-11-01T00:00:00Z', '2026-10-01T00:00:00']:
            self.binding['originalAcquiredAt'] = value
            self.assertEqual(self.plan()['status'], 'malformed')

    def test_real_portfolio_held_even_if_metadata_present(self):
        b = copy.deepcopy(self.binding); b['fixture'] = False
        self.assertIn('real-source-processing-not-selected',
                      preflight(b, now=NOW, observed=self.observed)['diagnostics'])
        report = portfolio_report(now=NOW)
        self.assertEqual({b['country'] for b in BINDINGS}, {'ML', 'MM', 'MN', 'MO'})
        self.assertTrue(all('real-source-processing-not-selected' in r['diagnostics']
                            for r in report['results']))
        self.assertEqual(len(report['cells']), 24)

    def test_shared_qualifier_uses_complete_authored_origin_fixture(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); bundle = root / 'bundle'; bundle.mkdir()
            assets = []
            for name, body in [('input.csv', b'id,value,unit,basis\nsynthetic,0,fixture-unit,fixture-basis\n'),
                               ('rights.json', b'authored fixture retain parse transform'),
                               ('scope.json', b'one authored record, not a real country')]:
                (bundle / name).write_bytes(body)
                assets.append(Asset(name, len(body), hashlib.sha256(body).hexdigest()))
            origin = {'kind': 'source', 'sourceId': 'authored-w12',
                      'releaseId': 'synthetic-1', 'inputPath': 'input.csv',
                      'inputSha256': assets[0].sha256,
                      'sourceRecordId': 'fixture:row=2', 'sourceField': 'value'}
            row = {'id': 'authored-1', 'kind': 'sourceLiteral', 'schemaVersion': '1.0',
                   'data': {'text': '0', 'unit': 'fixture-unit', 'basis': 'fixture-basis'},
                   'provenance': {'sourceId': 'authored-w12', 'releaseId': 'synthetic-1',
                                  'fetchedAt': self.binding['originalAcquiredAt'],
                                  'fieldOrigins': {'/data/' + key: dict(origin, sourceField=('value' if key == 'text' else key))
                                                   for key in ('text', 'unit', 'basis')}}}
            schema = {'sourceLiteral': {'type': 'object', 'additionalProperties': False,
                'required': ['id', 'kind', 'schemaVersion', 'data', 'provenance'],
                'properties': {'id': {'const': 'authored-1'}, 'kind': {'const': 'sourceLiteral'},
                  'schemaVersion': {'const': '1.0'}, 'data': {'type': 'object',
                    'additionalProperties': False, 'required': ['text', 'unit', 'basis'],
                    'properties': {k: {'type': 'string'} for k in ('text', 'unit', 'basis')}},
                  'provenance': {'type': 'object'}}}}
            pins = {'input.csv': assets[0].sha256}
            contract = SourceContract('authored-w12', 'synthetic-1', 'authored-literal-only',
                self.binding['originalAcquiredAt'], tuple(assets), 1, ids_digest(['authored-1']),
                schema, fingerprint(schema), lambda r: literal_errors(self.binding, r, pins),
                fingerprint({'policy': 'authored-w12'}), assets[1], assets[2],
                frozenset(('retain', 'parse', 'transform')), fixture=True)
            candidate = root / 'candidate.jsonl'

            def check(record, selected=contract):
                body = canonical([record]) + b'\n'; candidate.write_bytes(body)
                manifest = {'sourceId': 'authored-w12', 'releaseId': 'synthetic-1',
                    'acquiredAt': contract.acquired_at, 'normalizedRecords': 1,
                    'candidateSha256': hashlib.sha256(body).hexdigest(), 'candidateBytes': len(body),
                    'rightsEvidenceSha256': assets[1].sha256, 'scopeEvidenceSha256': assets[2].sha256,
                    'inputFiles': [vars(a) for a in assets]}
                return qualify(selected, bundle, candidate, manifest)

            good = check(row)
            self.assertTrue(good['qualified'], good)
            self.assertEqual(good, check(row))
            self.assertTrue(good['fixture'])
            held = check(row, replace(contract, holds=('no-body',)))
            self.assertIn('source-held', held['errors'])
            broken = copy.deepcopy(row)
            broken['provenance']['fieldOrigins']['/data/text']['inputSha256'] = '0' * 64
            broken['data']['unit'] = 'invented-unit'
            errors = check(broken)['errors']
            self.assertIn('field-origin-input-pin-mismatch', errors)
            self.assertIn('portfolio-native-unit-unreviewed', errors)
            broken = copy.deepcopy(row)
            del broken['provenance']['fieldOrigins']['/data/basis']
            self.assertIn('field-origin-inventory-mismatch', check(broken)['errors'])
            broken = copy.deepcopy(row)
            broken['provenance']['fieldOrigins']['/data/text']['sourceRecordId'] = 'guessed'
            self.assertIn('portfolio-selector-unbound', check(broken)['errors'])


if __name__ == '__main__':
    unittest.main()
