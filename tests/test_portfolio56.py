"""Small authored metadata only. No retained data or shared core suites replayed."""
from copy import deepcopy
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
import unittest

from offmenu.refresh.core import RefreshError, canonical, sha, strict_json
from offmenu.refresh.portfolio56 import assess, plan, read_metadata, write_plan

NOW = '2026-10-18T00:00:00Z'


class Portfolio56Tests(unittest.TestCase):
    def fixture(self, **overrides):
        document = {'acquired': '2026-10-10T00:00:00Z', 'validated': NOW,
                    'unit': 'mg/d', 'basis': None, 'amount': 0, 'label': 'Authored µg fixture'}
        document.update(overrides)
        raw = canonical(document)
        binding = {'sourceId': 'authored-fixture', 'releaseId': 'fixture-1',
                   'countries': ['TK'], 'domains': ['nutrition'],
                   'metadata': {'path': '/authored/metadata.json', 'sha256': sha(raw)},
                   'acquiredAtSelector': '/acquired',
                   'fields': {'unit': '/unit', 'basis': '/basis', 'amount': '/amount', 'label': '/label'},
                   'unknowns': [], 'holds': [],
                   'adapter': None}
        return binding, raw

    def test_valid_is_metadata_only_with_exact_origins_and_unknowns(self):
        b, raw = self.fixture()
        result = assess(b, raw, now=NOW)
        self.assertEqual(result['status'], 'ready-metadata-candidate')
        self.assertFalse(result['stageExecutionAuthorized'])
        self.assertFalse(result['countryAccepted'])
        self.assertEqual(result['record']['data']['basis'], None)
        self.assertEqual(result['record']['data']['unit'], 'mg/d')
        self.assertEqual(result['record']['data']['amount'], 0)
        self.assertEqual(result['record']['provenance']['fieldOrigins']['/data/unit']['sourceField'], '/unit')

    def test_missing_held_malformed_stale(self):
        b, raw = self.fixture()
        self.assertEqual(assess(b, None, now=NOW)['status'], 'missing')
        held = deepcopy(b); held['holds'] = ['source-body-no-read']
        self.assertEqual(assess(held, raw, now=NOW)['status'], 'held')
        self.assertIsNone(assess(held, raw, now=NOW)['record'])
        self.assertEqual(assess(b, raw + b' ', now=NOW)['status'], 'stale-input')
        bad = b'{"duplicate":0,"duplicate":1}'
        b['metadata']['sha256'] = sha(bad)
        self.assertEqual(assess(b, bad, now=NOW)['status'], 'malformed')

    def test_missing_and_nested_selectors_fail_closed(self):
        b, raw = self.fixture()
        b['fields']['unit'] = '/missing'
        self.assertEqual(assess(b, raw, now=NOW)['status'], 'malformed')
        b['fields']['unit'] = '/'
        self.assertEqual(assess(b, raw, now=NOW)['status'], 'malformed')
        b, raw = self.fixture(unit={'unreviewed': 'object'})
        self.assertEqual(assess(b, raw, now=NOW)['status'], 'malformed')

    def test_unsupported_adapter_and_unknown_are_not_ready(self):
        b, raw = self.fixture(); b['adapter'] = {'sourceId': 'wikibooks', 'releaseId': 'wrong'}
        self.assertEqual(assess(b, raw, now=NOW)['status'], 'missing')
        b, raw = self.fixture(); b['unknowns'] = ['basis']
        self.assertEqual(assess(b, raw, now=NOW)['status'], 'missing')

    def test_exact_30_day_boundary_and_validation_does_not_reset_age(self):
        b, raw = self.fixture(acquired='2026-09-18T00:00:00Z', validated=NOW)
        result = assess(b, raw, now=NOW)
        self.assertEqual(result['status'], 'stale-input')
        self.assertEqual(result['acquisitionAgeDays'], 30)
        self.assertEqual(result['refreshDecision'], 'conditional-review-required-no-download')
        self.assertEqual(assess(b, raw, now='2026-10-17T23:59:59Z')['refreshDecision'], 'reuse-retained-no-download')

    def test_future_and_non_utc_acquisition_and_clock_rejected(self):
        for kwargs in ({'acquired': '2027-01-01T00:00:00Z'}, {'acquired': '2026-10-10T10:00:00+11:00'}):
            b, raw = self.fixture(**kwargs)
            self.assertEqual(assess(b, raw, now=NOW)['status'], 'malformed')
        b, raw = self.fixture()
        self.assertEqual(assess(b, raw, now='yesterday')['status'], 'malformed')

    def test_isolated_failure_does_not_hide_valid_and_inputs_unchanged(self):
        b, raw = self.fixture(); bad = deepcopy(b); bad['sourceId'] = 'missing'
        held = deepcopy(b); held['sourceId'] = 'held'; held['holds'] = ['no-read']
        before = deepcopy([bad, held, b])
        def reader(item):
            if item['sourceId'] == 'missing': raise FileNotFoundError()
            return raw
        report, encoded = plan([bad, held, b], now=NOW, reader=reader)
        self.assertEqual([z['status'] for z in report['results']], ['missing', 'held', 'ready-metadata-candidate'])
        self.assertEqual(report['metadataCandidates'], 1)
        self.assertEqual(report['datasetRecords'], 0)
        self.assertEqual([bad, held, b], before)
        self.assertEqual(len(strict_json(encoded)[0]['provenance']['fieldOrigins']), 4)

    def test_repeatable_noop_and_changed_time_preserves_acquisition_key(self):
        b, raw = self.fixture()
        a, data = plan([b], now=NOW, reader=lambda _: raw)
        again, again_data = plan([b], now='2026-10-19T00:00:00Z', reader=lambda _: raw)
        self.assertEqual(a['buildKey'], again['buildKey'])
        self.assertEqual(data, again_data)
        with TemporaryDirectory() as t:
            out = Path(t) / 'result'
            self.assertEqual(write_plan(a, data, out), 'written-isolated-metadata-plan')
            snapshot = (out / 'plan.json').read_bytes()
            self.assertEqual(write_plan(again, again_data, out), 'no-op-verified-metadata-cache')
            self.assertEqual((out / 'plan.json').read_bytes(), snapshot)
            (out / 'metadata-candidates.jsonl').write_bytes(b'corrupt')
            with self.assertRaises(RefreshError): write_plan(again, again_data, out)

    def test_stale_gate_changes_build_key_and_cannot_reuse_old_output(self):
        b, raw = self.fixture()
        fresh, data = plan([b], now=NOW, reader=lambda _: raw)
        stale, stale_data = plan([b], now='2026-11-10T00:00:00Z', reader=lambda _: raw)
        self.assertNotEqual(fresh['buildKey'], stale['buildKey'])
        self.assertEqual(stale_data, b'')
        with TemporaryDirectory() as t:
            out = Path(t) / 'result'; write_plan(fresh, data, out)
            with self.assertRaises(RefreshError): write_plan(stale, stale_data, out)

    def test_reader_rejects_body_before_io_and_symlink_metadata(self):
        b, raw = self.fixture(); b['metadata']['path'] = '/held/original.response'
        with patch.object(Path, 'stat', side_effect=AssertionError('body-stat-forbidden')):
            with self.assertRaises(RefreshError): read_metadata(b)
        with TemporaryDirectory() as t:
            target = Path(t) / 'safe.json'; target.write_bytes(raw)
            link = Path(t) / 'link.json'; link.symlink_to(target)
            b['metadata']['path'] = str(link)
            with self.assertRaises(RefreshError): read_metadata(b)
            b['metadata']['path'] = str(target)
            self.assertEqual(read_metadata(b), raw)

    def test_nonfinite_missing_keys_and_bad_applicability(self):
        b, raw = self.fixture()
        for key in list(b):
            modified = deepcopy(b); del modified[key]
            self.assertEqual(assess(modified, raw, now=NOW)['status'], 'malformed')
        b['countries'] = ['FI']
        self.assertEqual(assess(b, raw, now=NOW)['status'], 'malformed')
        b, raw = self.fixture(); b['metadata']['sha256'] = sha(b'{"x":NaN}')
        self.assertEqual(assess(b, b'{"x":NaN}', now=NOW)['status'], 'malformed')

    def test_duplicate_identity_rejected_and_bad_identity_isolated(self):
        b, raw = self.fixture()
        with self.assertRaises(RefreshError): plan([b, deepcopy(b)], now=NOW, reader=lambda _: raw)
        bad = deepcopy(b); bad['sourceId'] = []
        report, _ = plan([bad, b], now=NOW, reader=lambda _: raw)
        self.assertEqual([v['status'] for v in report['results']], ['malformed', 'ready-metadata-candidate'])


    def test_plan_tampering_cannot_pass_replay(self):
        b, raw = self.fixture()
        report, data = plan([b], now=NOW, reader=lambda _: raw)
        with TemporaryDirectory() as t:
            out = Path(t) / 'result'; write_plan(report, data, out)
            corrupted = strict_json((out / 'plan.json').read_bytes())
            corrupted['stageExecutionAuthorized'] = True
            (out / 'plan.json').write_bytes(canonical(corrupted))
            with self.assertRaises(RefreshError): write_plan(report, data, out)

    def test_exponent_overflow_isolated_and_binding_limit(self):
        b, raw = self.fixture()
        malformed = raw.replace(b'"amount":0', b'"amount":1e999')
        bad = deepcopy(b); bad['sourceId'] = 'malformed'; bad['metadata']['sha256'] = sha(malformed)
        report, data = plan([bad, b], now=NOW,
                            reader=lambda item: malformed if item['sourceId'] == 'malformed' else raw)
        self.assertEqual([r['status'] for r in report['results']], ['malformed', 'ready-metadata-candidate'])
        with self.assertRaises(RefreshError): plan([], now=NOW)
        with self.assertRaises(RefreshError): plan([b] * 65, now=NOW)


    def test_adapter_cannot_borrow_another_source_identity(self):
        b, raw = self.fixture()
        b['adapter'] = {'sourceId': 'wikibooks', 'releaseId': '2026-10-13-live'}
        result = assess(b, raw, now=NOW)
        self.assertIn('adapter-identity-mismatch', result['diagnostics'])
        self.assertEqual(result['status'], 'missing')

    def test_authored_metadata_uses_shared_sourcecontract_qualification(self):
        from dataclasses import replace
        from offmenu.refresh.acceptance import Asset, SourceContract, qualify, fingerprint, ids_digest
        from offmenu.refresh.field_provenance import field_origin_errors
        b, raw = self.fixture()
        report, body = plan([b], now=NOW, reader=lambda _: raw)
        record = report['results'][0]['record']
        self.assertEqual(report['results'][0]['realSourceCapability'], 'unsupported-unselected')
        with TemporaryDirectory() as t:
            root = Path(t); bundle = root / 'bundle'; bundle.mkdir()
            authored = [('metadata.json', raw), ('rights.json', b'Authored fixture only; retain parse transform.'),
                        ('scope.json', b'Independent authored one-row scope; no country acceptance.')]
            assets = []
            for name, payload in authored:
                (bundle / name).write_bytes(payload)
                assets.append(Asset(name, len(payload), sha(payload)))
            schema = {'type': 'object', 'additionalProperties': False,
                      'required': ['id', 'kind', 'schemaVersion', 'countries', 'data', 'provenance'],
                      'properties': {'id': {'const': record['id']},
                          'kind': {'const': 'source-input-metadata'},
                          'schemaVersion': {'const': record['schemaVersion']},
                          'countries': {'const': ['TK']}, 'provenance': {'type': 'object'},
                          'data': {'type': 'object', 'additionalProperties': False,
                              'required': ['unit', 'basis', 'amount', 'label'],
                              'properties': {'unit': {'const': 'mg/d'}, 'basis': {'type': 'null'},
                                             'amount': {'const': 0}, 'label': {'const': 'Authored µg fixture'}}}}}
            schemas = {'source-input-metadata': schema}
            def semantics(row):
                return field_origin_errors(row, {'metadata.json': sha(raw)})
            contract = SourceContract(b['sourceId'], b['releaseId'], 'authored-metadata-only',
                record['provenance']['fetchedAt'], tuple(assets), 1, ids_digest([record['id']]),
                schemas, fingerprint(schemas), semantics, 'a' * 64, assets[1], assets[2],
                frozenset(('retain', 'parse', 'transform')), fixture=True,
                max_input_bytes=10000, max_output_bytes=10000, max_records=10)
            candidate = root / 'candidate.jsonl'; candidate.write_bytes(body)
            manifest = {'sourceId': b['sourceId'], 'releaseId': b['releaseId'],
                'acquiredAt': contract.acquired_at, 'normalizedRecords': 1,
                'candidateSha256': sha(body), 'candidateBytes': len(body),
                'rightsEvidenceSha256': assets[1].sha256, 'scopeEvidenceSha256': assets[2].sha256,
                'inputFiles': [vars(a) for a in assets]}
            result = qualify(contract, bundle, candidate, manifest, scratch_root=root)
            self.assertTrue(result['qualified'], result['errors'])
            self.assertTrue(result['fixture'])
            held = qualify(replace(contract, holds=('authored-hold-control',)), bundle,
                           candidate, manifest, scratch_root=root)
            self.assertFalse(held['qualified'])
            self.assertIn('source-held', held['errors'])


if __name__ == '__main__':
    unittest.main()
